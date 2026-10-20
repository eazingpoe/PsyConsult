import sys
from pathlib import Path

import pytest

AGENT_ROOT = str(Path(__file__).resolve().parents[1])
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from core.workflow.safety import is_high_risk_self_harm_message


@pytest.mark.parametrize("message", [
    "我不想活了",
    "我想结束自己的生命",
    "我准备自杀",
    "我想自杀",
    "我想伤害自己",
    "I want to kill myself",
    "I want to end my life",
])
def test_explicit_high_risk_expression_is_detected(message):
    assert is_high_risk_self_harm_message(message) is True


@pytest.mark.parametrize("message", [
    "我最近睡眠不好，想了解如何改善",
    "我没有自杀想法",
    "我不想自杀，只是想了解 PHQ-9",
    "心理健康科普有哪些资源",
    "",
])
def test_ordinary_or_negated_expression_is_not_flagged(message):
    assert is_high_risk_self_harm_message(message) is False
