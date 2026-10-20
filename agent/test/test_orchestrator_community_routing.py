import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage

AGENT_ROOT = str(Path(__file__).resolve().parents[1])
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

import agents.orchestrator as orchestrator_module
from agents.orchestrator import OrchestratorAgent


PUBLIC_INTENTS = [
    "mental_health_education",
    "scale_explanation",
    "resource_navigation",
    "emotional_support",
    "medication_safety_education",
    "general_support",
]


class FakeLLM:
    def __init__(self, content):
        self.content = content
        self.received_messages = None

    async def ainvoke(self, messages):
        self.received_messages = messages
        return SimpleNamespace(content=self.content)


@pytest.fixture(autouse=True)
def mock_stream_writer(monkeypatch):
    monkeypatch.setattr(
        orchestrator_module,
        "get_stream_writer",
        lambda: lambda event: None,
    )


def make_agent(output):
    agent = OrchestratorAgent.__new__(OrchestratorAgent)
    agent.llm = FakeLLM(output)
    return agent


def make_state(messages):
    return {
        "messages": messages,
        "user_id": "test_user",
        "session_id": "test_session",
        "memory_context": "",
        "next_agent": "",
        "metadata": {},
    }


@pytest.mark.parametrize("intent", PUBLIC_INTENTS)
def test_public_intents_route_to_community_agent(intent):
    agent = make_agent(intent)
    state = make_state([
        HumanMessage(content="我想了解心理健康相关信息")
    ])

    result = asyncio.run(agent.route(state))

    assert result["next_agent"] == "treatment_recommend"
    assert result["metadata"]["service_intent"] == intent


def test_invalid_model_output_never_routes_to_clinical_agent():
    agent = make_agent("differential_diagnosis")
    state = make_state([
        HumanMessage(content="我最近睡眠不好")
    ])

    result = asyncio.run(agent.route(state))

    assert result["next_agent"] == "treatment_recommend"
    assert result["metadata"]["service_intent"] == "general_support"


def test_router_uses_latest_user_message_not_trailing_assistant_message():
    agent = make_agent("emotional_support")
    state = make_state([
        HumanMessage(content="旧问题：请帮我诊断"),
        AIMessage(content="旧回答"),
        HumanMessage(content="最新问题：最近睡眠不好"),
        AIMessage(content="历史末尾的助手消息"),
    ])

    asyncio.run(agent.route(state))

    assert (
        agent.llm.received_messages[1].content
        == "最新问题：最近睡眠不好"
    )


def test_router_prompt_uses_community_service_scope():
    agent = make_agent("mental_health_education")
    state = make_state([
        HumanMessage(content="什么是心理健康科普？")
    ])

    asyncio.run(agent.route(state))

    prompt = agent.llm.received_messages[0].content
    assert "心晴社区" in prompt
    assert "mental_health_education" in prompt
    assert "不进行精神障碍诊断" in prompt
