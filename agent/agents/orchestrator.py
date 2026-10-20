"""临床路由节点 — 分析用户意图并分发给对应的领域 Agent。"""
import os
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.config import get_stream_writer

from core.workflow.state import AgentState

class OrchestratorAgent:
    """
    中心路由节点 (Orchestrator/Router)
    负责分析用户意图，并将请求分发给相应的专门 Agent。
    """
    def __init__(self):
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        load_dotenv(dotenv_path)
        from config import get_settings
        self.llm = ChatOpenAI(**get_settings().get_model_config(), temperature=0.1)

    async def route(self, state: AgentState) -> Dict[str, Any]:
        """分类公众服务意图，并路由至社区科普 Agent。"""
        writer = get_stream_writer()
        writer({"agent": "orchestrator", "event": "start"})

        # 从历史消息中找到最近一条用户消息。
        messages = state.get("messages", [])
        last_message = ""

        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                content = message.content
                last_message = (
                    content if isinstance(content, str) else str(content)
                )
                break

            if (
                isinstance(message, tuple)
                and len(message) == 2
                and str(message[0]).lower() in {"user", "human"}
            ):
                last_message = str(message[1])
                break

        allowed_intents = {
            "mental_health_education",
            "scale_explanation",
            "resource_navigation",
            "emotional_support",
            "medication_safety_education",
            "general_support",
        }

        # 空消息不调用模型，直接使用安全的普通服务路由。
        if not last_message.strip():
            decision = "general_support"
        else:
            memory_context = str(
                state.get("memory_context") or ""
            ).strip()

            memory_block = (
                f"\n【仅用于消歧的历史上下文】\n{memory_context}"
                if memory_context else ""
            )

            system_prompt = f"""你是“心晴社区”的服务意图分类器，
不是精神科临床诊断路由器。

请根据最新一条用户消息，选择且只选择以下一个标签：

1. mental_health_education
   心理健康知识、情绪、睡眠、压力等一般科普。

2. scale_explanation
   PHQ-9、GAD-7 等量表的用途，或已有分数的非诊断性解释。
   实际量表计分由独立评分接口处理，不要自行计算总分。

3. resource_navigation
   如何寻找心理咨询、医疗服务或其他求助资源。

4. emotional_support
   用户表达难过、焦虑、压力等情绪，需要倾听或一般应对建议。

5. medication_safety_education
   一般性药物安全知识，不涉及个体化处方、剂量、
   停药或换药指令。

6. general_support
   意图不明确或不属于以上类别的请求。

分类约束：
- 不进行精神障碍诊断。
- 不生成临床鉴别诊断或个体化治疗处方。
- 不把一般科普描述成已经核实的临床结论。
- 只根据最新用户消息分类；历史上下文仅用于消除指代歧义。
- 仅输出一个标签的精确拼写，不输出其他解释。

{memory_block}"""

            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=last_message),
            ])

            raw_decision = str(response.content).strip().lower()
            decision = (
                raw_decision.splitlines()[0].strip("`'\" ")
                if raw_decision else ""
            )

            if decision not in allowed_intents:
                decision = "general_support"

        # 当前阶段所有普通公众请求统一交给社区科普 Agent。
        # 不再依据模型文本将公众请求分发至临床诊断或药物审查节点。
        metadata = dict(state.get("metadata") or {})
        metadata["service_intent"] = decision

        return {
            "next_agent": "treatment_recommend",
            "metadata": metadata,
        }
