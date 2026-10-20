from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.app_config.settings import settings
from app.router.assessment import router


assessment_test_app = FastAPI()
assessment_test_app.include_router(router, prefix="/api")
client = TestClient(assessment_test_app)

AUTH_HEADERS = (
    {"Authorization": f"Bearer {settings.api_auth_token}"}
    if settings.api_auth_token
    else {}
)


def post_score(scale_type, answers):
    return client.post(
        "/api/assessment/score",
        json={"scale_type": scale_type, "answers": answers},
        headers=AUTH_HEADERS,
    )


def test_phq9_valid_score():
    response = post_score("PHQ-9", [1, 1, 1, 1, 0, 0, 0, 0, 0])
    assert response.status_code == 200

    result = response.json()
    assert result["total"] == 4
    assert result["severity_band"] == "极轻或无明显抑郁症状"
    assert result["screening_only"] is True
    assert result["answers_stored"] is False
    assert result["safety_alert"] is None


def test_gad7_valid_score():
    response = post_score("GAD-7", [1, 1, 1, 1, 0, 0, 0])
    assert response.status_code == 200

    result = response.json()
    assert result["total"] == 4
    assert result["severity_band"] == "极轻或无明显焦虑症状"


def test_phq9_positive_item9_returns_safety_alert():
    response = post_score("PHQ-9", [0, 0, 0, 0, 0, 0, 0, 0, 1])
    assert response.status_code == 200
    assert response.json()["safety_alert"] is not None


def test_incomplete_answers_are_rejected():
    response = post_score("PHQ-9", [0] * 8)
    assert response.status_code == 422


def test_out_of_range_answers_are_rejected():
    response = post_score("PHQ-9", [4] + [0] * 8)
    assert response.status_code == 422


def test_unsupported_scale_is_rejected():
    response = post_score("UNKNOWN", [0] * 9)
    assert response.status_code == 422


def test_positive_item9_does_not_assign_high_risk():
    for value in [1, 2, 3]:
        result = post_score('PHQ-9', [0] * 8 + [value]).json()
        assert result['screening_only'] is True
        assert '量表本身不能判断当前危险程度' in result['safety_alert']
        assert '专业人员进一步评估' in result['safety_alert']
        assert 'risk_level' not in result
