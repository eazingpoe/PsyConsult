"""治疗推荐 Agent。
根据鉴别诊断结果，检索中国精神科指南和药物知识图谱，
输出分级的治疗方案建议。
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


class TreatmentAgentNode:
    def __init__(self):
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        load_dotenv(dotenv_path)
        from config import get_settings
        self.llm = ChatOpenAI(**get_settings().get_model_config(), temperature=0.1)
        self.tools = [query_vector_db, query_knowledge_graph]
        self.inner_agent = create_react_agent(self.llm, self.tools)

    def _build_system_prompt(self, memory_context: str) -> str:
        memory_block = (
            f"\n## 历史对话参考\n{memory_context}"
            if memory_context else ""
        )

        return f"""你是“心晴社区”的循证心理健康科普与知识问答 Agent。

## 一、任务范围

为公众提供清晰、审慎、易理解的心理健康信息，包括：
- 常见心理困扰、情绪管理与睡眠健康科普。
- 心理健康知识解释及一般性应对方法。
- 何时考虑寻求专业帮助，以及如何寻找可靠服务资源。

你不是临床诊断或处方系统。不得根据聊天内容作出精神障碍确诊，
不得提供个体化处方、药物剂量、停药或换药指令。

## 二、证据检索规则

1. 回答涉及医学事实、心理健康知识或专业建议时，优先调用
   query_vector_db 检索相关资料。
2. 只有在确有必要时，才调用 query_knowledge_graph 补充相关信息。
3. 必须区分用户提供的信息、检索得到的证据和一般性解释。
4. 只允许引用工具实际返回的来源名称及元数据。
   不得编造文献、指南名称、页码、章节或链接。
   引用优先使用 source_title 和 source_urls 中逐个来源的 URL。
   title、section_path 是本地知识库的整理标题，不能写成 WHO 或卫健委发布的官方文献标题。
   遵守 source_scope 的来源分工和适用人群；多来源段落不得暗示各来源都支持全部结论。
   引用 NIMH 成人 ASQ 评估资料时，应说明它仅提供一般安全衔接参考，非 PHQ-9 专属算法。
5. 如果检索无结果、发生错误或证据不足，明确说明：
   “当前知识库未检索到足够证据，暂时无法提供有来源支持的结论。”
6. 不得把模型自身记忆描述成已经检索或核实的证据。
7. 不得仅凭检索相似度分数宣称结论具有某种确定的置信度。
8. 工具调用最多 2 次。证据不足时，不得为了生成完整答案而编造内容。

## 三、安全边界

- 不根据少量症状推断用户患有某种精神障碍。
- 不把 PHQ-9、GAD-7 的分数解释为确诊结论。
- 涉及诊断、个体化治疗或药物调整时，说明服务边界，
  建议咨询合适的医疗专业人员。
- 如果用户表达自伤、自杀意图或迫在眉睫的危险，
  优先回应其安全需求，鼓励立即联系当地急救服务、
  危机支持资源或可信任的人，不要继续普通科普流程。
- 不得虚构求助电话号码或声称未经核实的资源可用。

## 四、回答格式

### 简要回答
直接回应用户的问题，使用通俗、审慎的表达。

### 依据与适用边界
说明检索证据支持什么、不能支持什么。
若缺少足够证据，明确说明，不强行得出结论。

### 来源
仅列出工具实际返回且与回答内容相关的来源。
若没有可核实来源，明确写明“本次未获得可核实的检索来源”。

避免冗长的免责声明，不要将一般性心理健康科普包装成临床诊疗建议。

{memory_block}"""
    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        writer = get_stream_writer()
        writer({"agent": "treatment_recommend", "event": "start"})

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
                        writer({"agent": "treatment_recommend", "chunk": buffer})
                        buffer = ""
                elif hasattr(msg, "tool_calls") and msg.tool_calls:
                    if buffer:
                        writer({"agent": "treatment_recommend", "chunk": buffer})
                        buffer = ""
                    for tc in msg.tool_calls:
                        writer({"agent": "treatment_recommend", "event": "tool_call", "tool": tc.get("name", "")})
            elif isinstance(msg, ToolMessage):
                if buffer:
                    writer({"agent": "treatment_recommend", "chunk": buffer})
                    buffer = ""
                writer({"agent": "treatment_recommend", "event": "tool_done"})
        if buffer:
            writer({"agent": "treatment_recommend", "chunk": buffer})

        return {"messages": [AIMessage(content=full_content)]}
