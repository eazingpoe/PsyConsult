import sys
from pathlib import Path

AGENT_ROOT = str(Path(__file__).resolve().parents[1])
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from agents.treatment_agent import TreatmentAgentNode


def build_prompt(memory_context=""):
    node = TreatmentAgentNode.__new__(TreatmentAgentNode)
    return node._build_system_prompt(memory_context)


def test_prompt_defines_community_mental_health_scope():
    prompt = build_prompt()

    assert "心理健康科普" in prompt
    assert "不得根据聊天内容作出精神障碍确诊" in prompt
    assert "不得提供个体化处方" in prompt


def test_prompt_requires_real_evidence_and_source_traceability():
    prompt = build_prompt()

    assert "不得编造文献、指南名称、页码、章节或链接" in prompt
    assert "当前知识库未检索到足够证据" in prompt
    assert "本次未获得可核实的检索来源" in prompt


def test_prompt_preserves_memory_context():
    context = "用户偏好：使用简明中文解释"
    prompt = build_prompt(context)

    assert context in prompt


def test_prompt_distinguishes_local_titles_and_official_sources():
    prompt=build_prompt()
    assert 'source_title 和 source_urls' in prompt
    assert '本地知识库的整理标题' in prompt
    assert '非 PHQ-9 专属算法' in prompt
