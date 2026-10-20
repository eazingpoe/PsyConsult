import asyncio
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage

# 项目内部模块使用 agent 目录作为导入根路径。
AGENT_ROOT = str(Path(__file__).resolve().parents[1])
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from core.workflow.graph_manager import AgentGraphManager


class FakeOrchestrator:
    def __init__(self, route, calls):
        self.route_target = route
        self.calls = calls

    async def route(self, state):
        self.calls.append("orchestrator")
        return {
            "next_agent": self.route_target,
            "metadata": state.get("metadata", {}),
        }


class FakeNode:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    async def __call__(self, state):
        self.calls.append(self.name)
        return {
            "messages": [AIMessage(content=f"{self.name} completed")]
        }


def make_manager(route, calls):
    # 不调用真实构造函数，避免初始化真实模型或外部服务。
    manager = AgentGraphManager.__new__(AgentGraphManager)
    manager.orchestrator = FakeOrchestrator(route, calls)
    manager.diagnosis_node = FakeNode("differential_diagnosis", calls)
    manager.treatment_node = FakeNode("treatment_recommend", calls)
    manager.drug_review_node = FakeNode("drug_interaction", calls)
    return manager


def make_state():
    return {
        "messages": [HumanMessage(content="测试请求")],
        "user_id": "test_user",
        "session_id": "test_route",
        "memory_context": "",
        "next_agent": "",
        "metadata": {},
    }


@pytest.mark.parametrize(
    "orchestrator_route",
    [
        "differential_diagnosis",
        "treatment_recommend",
        "drug_interaction",
        "unknown_node",
        "",
        None,
    ],
)
def test_public_chat_only_runs_community_agent(orchestrator_route):
    calls = []
    manager = make_manager(orchestrator_route, calls)
    graph = manager.build_graph()

    result = asyncio.run(graph.ainvoke(make_state()))

    assert calls == ["orchestrator", "treatment_recommend"]
    assert (
        result["messages"][-1].content
        == "treatment_recommend completed"
    )
