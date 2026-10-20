"""社区心理健康服务的高风险表达识别规则。

这是一个保守的规则式安全闸门，不替代专业危机评估。
明确的当前危险表达应优先进入安全支持流程。
"""

import re


# 明确表达当前自伤、自杀风险的规则。
URGENT_PATTERNS = [
    r"不想活了",
    r"活不下去了?",
    r"(?:准备|打算|计划)(?:马上|现在)?自杀",
    r"马上(?:就)?自杀",
    r"想结束(?:自己的)?生命",
    r"(?:可能|也许|怕自己会|担心自己会).{0,10}"
    r"(?:马上|现在|立即).{0,8}"
    r"(?:伤害自己|自伤|自残|自杀)",
    r"(?:现在|马上|立即).{0,8}"
    r"(?:可能会|可能|要|准备|打算).{0,8}"
    r"(?:伤害自己|自伤|自残|自杀)",
    r"(?:我|本人).{0,8}"
    r"(?:准备|打算|已经决定).{0,8}"
    r"(?:伤害自己|自伤|自残|自杀)",
    r"\bi want to kill myself\b",
    r"\bi want to end my life\b",
    r"\bi plan to kill myself\b",
    r"\bi am going to kill myself\b",
    r"\bi might hurt myself\b",
    r"\bi may hurt myself\b",
    r"\bi am going to hurt myself\b",
    r"\bi might kill myself\b",
    r"\bi may kill myself\b",
]

# 明确的自伤、自杀相关表达。
RISK_PATTERNS = [
    r"(?:我|本人|朋友|家人|他|她).{0,8}"
    r"(?:想自杀|想死|想轻生|想伤害自己|想自残|"
    r"会伤害自己|要伤害自己|准备伤害自己|打算伤害自己)",
    r"(?:我|本人).{0,8}(?:伤害自己|自残|自杀)",
    r"\bi want to die\b",
    r"\bi want to hurt myself\b",
    r"\bi might hurt myself\b",
    r"\bi may hurt myself\b",
    r"\bsuicidal intent\b",
    r"\bself-harm plan\b",
]

# 明确否认表达。只有在没有同时出现独立风险表达时，
# 才将其作为排除触发的依据。
NEGATED_PATTERNS = [
    r"(?:我|本人)?(?:没有|并没有|没|并不|不想|不打算|不会|从未)"
    r".{0,8}(?:自杀|轻生|自残|伤害自己|想死|结束生命)",
    r"\bi am not suicidal\b",
    r"\bi don't want to die\b",
    r"\bi do not want to die\b",
    r"\bi don't want to kill myself\b",
    r"\bi do not want to kill myself\b",
    r"\bi won't hurt myself\b",
    r"\bi will not hurt myself\b",
]


def is_high_risk_self_harm_message(message: str) -> bool:
    """识别明确的自伤、自杀风险表达；不替代专业危机评估。"""
    text = " ".join(str(message or "").lower().split())

    if not text:
        return False

    # 将转折前后的表达分开处理，避免否认语句掩盖后续风险。
    clauses = re.split(
        r"[，,。；;！？!?]|但是|然而|不过|可是|但|but|however",
        text,
        flags=re.IGNORECASE,
    )

    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue

        # 优先排除单个分句内的明确否认。
        # 补充“不准备自杀”和“不想死”等常见表达。
        negated = (
            any(re.search(p, clause) for p in NEGATED_PATTERNS)
            or bool(
                re.search(
                    r"(?:^|[\s，,])(?:我|本人)?不想死(?:了)?$",
                    clause.strip(),
                )
            )
            or bool(
                re.search(
                    r"(?:我|本人)?(?:不准备|不打算|不会|没有|"
                    r"并没有|不想|并不|从未)"
                    r".{0,8}(?:自杀|轻生|自残|伤害自己|想死|结束生命)",
                    clause,
                )
            )
        )

        if negated:
            continue

        urgent = any(
            re.search(p, clause) for p in URGENT_PATTERNS
        )
        risk = any(
            re.search(p, clause) for p in RISK_PATTERNS
        )

        if urgent or risk:
            return True

    return False
