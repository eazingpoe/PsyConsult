"""心理量表计分的确定性单元测试。"""
import json

import pytest

from agent.mcp_servers.clinical_tools import calculate_scale_score


def score(scale_type, answers):
    return json.loads(calculate_scale_score(scale_type, answers))


def test_valid_phq9_score():
    result = score("PHQ-9", "2,2,1,0,2,1,2,0,1")
    assert result["status"] == "success"
    assert result["data"]["total"] == 11
    assert result["data"]["severity"] == "中度抑郁症状"


def test_valid_gad7_score():
    result = score("GAD-7", "1,1,1,1,0,0,0")
    assert result["status"] == "success"
    assert result["data"]["total"] == 4
    assert result["data"]["severity"] == "极轻或无明显焦虑症状"


def test_incomplete_answers_are_rejected():
    result = score("PHQ-9", "1,1,1")
    assert result["status"] == "error"
    assert "total" not in result


@pytest.mark.parametrize(
    "answers",
    [
        "4,0,0,0,0,0,0,0,0",
        "-1,0,0,0,0,0,0,0,0",
        "1,,0,0,0,0,0,0,0",
        "1.5,0,0,0,0,0,0,0,0",
    ],
)
def test_invalid_answers_are_rejected(answers):
    result = score("PHQ-9", answers)
    assert result["status"] == "error"
    assert "total" not in result


def test_unsupported_scale_is_rejected():
    result = score("UNKNOWN", "0,0,0")
    assert result["status"] == "error"
    assert "total" not in result
