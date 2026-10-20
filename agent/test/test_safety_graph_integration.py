import asyncio
import sys
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

AGENT_ROOT = str(Path(__file__).resolve().parents[1])
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from core.workflow.graph_manager import AgentGraphManager


class FakeOrchestrator:
    async def route(self, state):
        return {
            "next_agent": "differential_diagnosis",
            "metadata": state.get("metadata", {}),
        }


class FakeNode:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    async def __call__(self, state):
        self.calls.append(self.name)
        return {"messages": [AIMessage(content=f"{self.name} completed")]}


def make_manager(calls):
    manager = AgentGraphManager.__new__(AgentGraphManager)
    manager.orchestrator = FakeOrchestrator()
    manager.diagnosis_node = FakeNode("differential_diagnosis", calls)
    manager.treatment_node = FakeNode("treatment_recommend", calls)
    manager.drug_review_node = FakeNode("drug_interaction", calls)
    return manager


def make_state(messages):
    return {
        "messages": messages,
        "user_id": "safety_test_user",
        "session_id": "safety_test_session",
        "memory_context": "",
        "next_agent": "",
        "metadata": {},
    }


def test_high_risk_message_bypasses_orchestrator_and_clinical_agents():
    calls = []
    manager = make_manager(calls)
    graph = manager.build_graph()

    result = asyncio.run(
        graph.ainvoke(make_state([HumanMessage(content="我准备自杀")]))
    )

    assert calls == []
    assert "急救" in result["messages"][-1].content
    assert "信任的人" in result["messages"][-1].content


def test_safety_gate_checks_latest_user_message_not_old_history():
    calls = []
    manager = make_manager(calls)
    graph = manager.build_graph()

    messages = [
        HumanMessage(content="我想自杀"),
        AIMessage(content="此前的对话"),
        HumanMessage(content="我没有自杀想法，只想了解睡眠卫生"),
    ]

    result = asyncio.run(graph.ainvoke(make_state(messages)))

    assert calls == ["treatment_recommend"]
    assert result["messages"][-1].content == "treatment_recommend completed"

def test_safety_gate_precedes_history_compression_with_checkpointer():
    from langgraph.checkpoint.memory import MemorySaver

    calls = []
    manager = make_manager(calls)
    compression_calls = []

    async def forbidden_compression(state):
        compression_calls.append(True)
        raise AssertionError(
            "高风险请求不应进入历史压缩节点"
        )

    manager._compress_history = forbidden_compression
    graph = manager.build_graph(checkpointer=MemorySaver())

    result = asyncio.run(
        graph.ainvoke(
            make_state([HumanMessage(content="我准备自杀")]),
            config={"configurable": {"thread_id": "safety-order-test"}},
        )
    )

    assert compression_calls == []
    assert calls == []
    assert "急救" in result["messages"][-1].content
