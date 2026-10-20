"""临床诊断 Agent（症状提取 + 鉴别诊断合并）。
第一步完成口语→术语映射和量表推断，第二步做 ICD-11 鉴别诊断。
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, AIMessageChunk, SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from langgraph.config import get_stream_writer
from typing import Dict, Any
from core.workflow.state import AgentState
from tools.vector_tool import query_vector_db
from tools.graph_tool import query_knowledge_graph
from tools.synonym_tool import query_synonyms


class DiagnosisAgentNode:
    def __init__(self):
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        load_dotenv(dotenv_path)
        from config import get_settings
        self.llm = ChatOpenAI(**get_settings().get_model_config(), temperature=0.1)
        self.tools = [query_synonyms, query_knowledge_graph, query_vector_db]
        self.inner_agent = create_react_agent(self.llm, self.tools)

    def _build_system_prompt(self, memory_context: str) -> str:
        memory_block = f"\n## 历史对话 / 用户偏好\n{memory_context}" if memory_context else ""
        return f"""你是一个精神科临床诊断专家 Agent。请从对话记录中读取患者的症状描述，完成两步任务。

**第一步：症状提取**
- 用 query_synonyms 将口语表达（如"睡不着"）映射为标准术语（如"失眠"）
- 严禁根据自由症状描述推断 PHQ-9 条目的标准分值。
- 用户描述的症状可以作为症状证据记录，但不能直接换算成 PHQ-9 答案。
- 只有用户明确完成标准 PHQ-9 的全部 9 个条目作答后，才允许报告完整量表分数；本节点不得自行估算或计算总分。
- 未完成标准量表作答时，必须注明“未完成标准量表评估”，不得把未提及的症状记为 0 分。
- 不得将症状强度或持续时间擅自转换成量表要求的发生频率。

**第二步：鉴别诊断**
- 用 query_knowledge_graph 一次性搜索与症状匹配的疾病
- 用 query_vector_db 检索前 2 个候选的 ICD-11 诊断标准
- 逐条对照，用 ✅/❌/⚠ 标注

输出格式：
```
## 症状清单
| 症状 | 原文引用 | 量表状态 |
|------|---------|---------|
| [症状名称] | [用户原文中的直接引用] | 未评估 / 待补充标准条目答案 |

> PHQ-9：未完成标准量表评估时，不得输出推断总分。

## 鉴别诊断

候选 1: [疾病名] (ICD-11: [编码])
  ✅ [标准条目] — "[原文引用]"
  ❌ [标准条目] — 未提及
  满足 M/N 条 → [结论]

候选 2: [疾病名] (ICD-11: [编码])
  ...
```

约束：
- 每项症状必须有 evidence 引用对话原文
- 只输出前 2 个最可能候选，每个不超过 5 行对照
- ⚠️ 你最多调用 2 次工具，之后必须输出最终结果
- 不要编造未提及的症状
{memory_block}"""

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        writer = get_stream_writer()
        writer({"agent": "differential_diagnosis", "event": "start"})

        system_prompt = self._build_system_prompt(state.get("memory_context", ""))
        messages = [SystemMessage(content=system_prompt)] + list(state["messages"])

        full_content = ""
        buffer = ""
        async for msg, metadata in self.inner_agent.astream(
            {"messages": messages}, stream_mode="messages",
        ):
            if isinstance(msg, AIMessageChunk):
                if msg.content:
                    full_content += msg.content
                    buffer += msg.content
                    if len(buffer) >= 20 or "\n" in buffer:
                        writer({"agent": "differential_diagnosis", "chunk": buffer})
                        buffer = ""
                elif hasattr(msg, "tool_calls") and msg.tool_calls:
                    if buffer:
                        writer({"agent": "differential_diagnosis", "chunk": buffer})
                        buffer = ""
                    for tc in msg.tool_calls:
                        writer({"agent": "differential_diagnosis", "event": "tool_call", "tool": tc.get("name", "")})
            elif isinstance(msg, ToolMessage):
                if buffer:
                    writer({"agent": "differential_diagnosis", "chunk": buffer})
                    buffer = ""
                writer({"agent": "differential_diagnosis", "event": "tool_done"})
        if buffer:
            writer({"agent": "differential_diagnosis", "chunk": buffer})

        return {"messages": [AIMessage(content=full_content)]}
