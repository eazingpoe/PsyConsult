import asyncio
import json

from langchain_core.messages import AIMessage

from app.service import chat_service


SAFETY_TEXT = (
    "如果你现在可能马上伤害自己，请立即联系当地急救服务或前往急诊。"
    "如果可以，请联系可信任的人陪伴，并远离可能用于自伤的物品。"
)


class FakeCache:
    available = True

    async def get_cache(self, *args, **kwargs):
        raise AssertionError("高风险请求不应查询语义缓存")

    async def set_cache(self, *args, **kwargs):
        raise AssertionError("高风险回复不应写入语义缓存")


class FakeGraph:
    async def astream(self, state, config, stream_mode):
        assert state["memory_context"] == ""
        yield "updates", {"safety_gate": {}}
        yield "updates", {
            "safety_support": {
                "messages": [AIMessage(content=SAFETY_TEXT)]
            }
        }


def test_high_risk_response_reaches_sse_and_bypasses_cache(monkeypatch):
    async def forbidden_memory_lookup(*args, **kwargs):
        raise AssertionError("高风险请求不应检索长期记忆")

    monkeypatch.setattr(chat_service, "graph", FakeGraph())
    monkeypatch.setattr(chat_service, "semantic_cache", FakeCache())
    monkeypatch.setattr(
        chat_service,
        "_extract_long_term_context",
        forbidden_memory_lookup,
    )
    monkeypatch.setattr(chat_service, "memory", None)
    monkeypatch.setattr(chat_service, "extraction_llm", None)

    async def collect_events():
        events = []
        async for line in chat_service.stream_chat(
            query="我现在可能会伤害自己。",
            user_id="safety_test_user",
            session_id="safety_test_session",
        ):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        return events

    events = asyncio.run(collect_events())

    safety_events = [
        event
        for event in events
        if event.get("agent") == "safety_support"
        and event.get("content") == SAFETY_TEXT
    ]
    assert len(safety_events) == 1
    assert any(event.get("done") is True for event in events)
    assert any(event.get("status") == "safety_check" for event in events)
    assert not any(
        event.get("status") == "semantic_cache_check"
        for event in events
    )
    assert not any(
        event.get("status") == "memory_context_extract"
        for event in events
    )
