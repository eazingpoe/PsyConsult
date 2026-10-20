import secrets
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from app.app_config.settings import settings
from app.schemas.assessment import AssessmentScoreRequest
from app.service.assessment_service import calculate_assessment_result


router = APIRouter()


def _check_optional_auth(authorization: str | None) -> None:
    """如果配置了 API_AUTH_TOKEN，则要求有效的 Bearer Token。"""
    expected = settings.api_auth_token
    if not expected:
        return

    scheme, _, token = (authorization or "").partition(" ")
    if (
        scheme.lower() != "bearer"
        or not token
        or not secrets.compare_digest(token, expected)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/assessment/score")
def score_assessment(
    request: AssessmentScoreRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """确定性计算心理量表分数；本接口不持久化答案。"""
    _check_optional_auth(authorization)
    try:
        return calculate_assessment_result(request.scale_type, request.answers)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
