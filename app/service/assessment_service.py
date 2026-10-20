"""Shared deterministic PHQ-9/GAD-7 scoring adapter for API endpoints."""
import json

from agent.mcp_servers.clinical_tools import calculate_scale_score


def calculate_assessment_result(scale_type: str, answers: list[int]) -> dict:
    raw_result = calculate_scale_score(
        scale_type,
        ",".join(str(answer) for answer in answers),
    )
    result = json.loads(raw_result)
    if result.get("status") != "success":
        raise ValueError(result.get("message", "量表评分失败"))

    data = result["data"]
    item9_positive = scale_type == "PHQ-9" and answers[8] > 0
    safety_alert = None
    if item9_positive:
        safety_alert = (
            "你在与死亡或自伤想法相关的条目上选择了非零分值。"
            "量表本身不能判断当前危险程度，建议尽快联系专业人员进一步评估。"
            "如果你此刻可能伤害自己或无法保证自身安全，请立即联系所在地急救服务"
            "或前往最近急诊，并联系可信任的人陪伴。"
        )

    return {
        "status": "success",
        "scale_type": data["scale_type"],
        "item_count": len(data["scores"]),
        "total": data["total"],
        "severity_band": data["severity"],
        "screening_only": True,
        "calculation_method": "deterministic_python",
        "answers_stored": False,
        "interpretation_note": (
            "该结果仅用于心理健康筛查，不构成临床诊断。"
            "应结合个人情况理解，必要时寻求专业评估。"
        ),
        "safety_alert": safety_alert,
    }
