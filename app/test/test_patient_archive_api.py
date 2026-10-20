import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.router import chat as chat_router
from app.router import patients as patients_router
from app.router.chat import require_chat_identity
from app.service import patient_store


@pytest.fixture
def archive_client(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCONSULT_DATABASE_PATH", str(tmp_path / "archive.sqlite3"))
    monkeypatch.setenv("PSYCONSULT_UPLOAD_DIR", str(tmp_path / "uploads"))
    current_user = {"id": "doctor_001"}

    app = FastAPI()
    app.include_router(patients_router.router, prefix="/api")
    app.include_router(chat_router.router, prefix="/api")
    app.dependency_overrides[require_chat_identity] = lambda: current_user["id"]

    with TestClient(app) as client:
        yield client, current_user


def create_patient(client):
    response = client.post(
        "/api/patients",
        json={
            "patient_code": "DEMO-001",
            "display_name": "测试化名",
            "sex": "unknown",
            "birth_date": "2000-01-01",
            "notes": "仅用于自动化测试",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_patient_crud_and_owner_isolation(archive_client):
    client, current_user = archive_client
    patient = create_patient(client)

    assert client.get("/api/patients").json()["total"] == 1
    assert client.get(f"/api/patients/{patient['id']}").status_code == 200

    duplicate = client.post(
        "/api/patients",
        json={"patient_code": "DEMO-001", "display_name": "重复编号"},
    )
    assert duplicate.status_code == 409

    updated = client.patch(
        f"/api/patients/{patient['id']}",
        json={"display_name": "更新后的化名"},
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "更新后的化名"

    current_user["id"] = "doctor_002"
    assert client.get(f"/api/patients/{patient['id']}").status_code == 404
    assert client.get("/api/patients").json()["total"] == 0


def test_assessment_is_recalculated_and_persisted(archive_client):
    client, _ = archive_client
    patient = create_patient(client)
    response = client.post(
        f"/api/patients/{patient['id']}/assessments",
        json={"scale_type": "PHQ-9", "answers": [1, 1, 1, 1, 0, 0, 0, 0, 1]},
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["total"] == 5
    assert result["answers_stored"] is True
    assert result["safety_alert"]
    assert result["record_id"]

    history = client.get(f"/api/patients/{patient['id']}/assessments")
    assert history.status_code == 200
    assert len(history.json()["items"]) == 1
    assert history.json()["items"][0]["answers"] == [1, 1, 1, 1, 0, 0, 0, 0, 1]


def test_report_upload_download_and_archive(archive_client):
    client, _ = archive_client
    patient = create_patient(client)

    upload = client.post(
        f"/api/patients/{patient['id']}/reports",
        files={"file": ("demo.pdf", b"%PDF-1.4\nsynthetic test document", "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    report = upload.json()
    assert report["original_filename"] == "demo.pdf"

    download = client.get(
        f"/api/patients/{patient['id']}/reports/{report['id']}/download"
    )
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF-1.4")

    archived = client.delete(f"/api/patients/{patient['id']}/reports/{report['id']}")
    assert archived.status_code == 200
    assert client.get(f"/api/patients/{patient['id']}/reports").json()["items"] == []


def test_saved_chat_preserves_sse_and_persists_messages(archive_client, monkeypatch):
    client, _ = archive_client
    patient = create_patient(client)

    async def fake_stream_chat(query: str, user_id: str, session_id: str):
        yield 'data: {"status":"accepted","content":"accepted"}\n\n'
        yield 'data: {"agent":"safety_support","content":"请联系当地急救服务。"}\n\n'
        yield 'data: {"done":true}\n\n'

    monkeypatch.setattr(chat_router, "stream_chat", fake_stream_chat)
    response = client.post(
        "/api/chat",
        headers={"X-User-Id": "ignored-by-test-override"},
        json={
            "query": "我现在可能会伤害自己。",
            "session_id": "session_saved_test",
            "patient_id": patient["id"],
            "save_to_history": True,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'data: {"agent":"safety_support","content":"请联系当地急救服务。"}\n\n' in response.text

    history = client.get(f"/api/patients/{patient['id']}/history")
    assert history.status_code == 200
    assert len(history.json()["items"]) == 1
    detail = client.get(
        f"/api/patients/{patient['id']}/history/session_saved_test"
    )
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "我现在可能会伤害自己。"
    assert messages[1]["content"] == "请联系当地急救服务。"


def test_chat_does_not_persist_without_explicit_opt_in(archive_client, monkeypatch):
    client, _ = archive_client
    patient = create_patient(client)

    async def fake_stream_chat(query: str, user_id: str, session_id: str):
        yield 'data: {"agent":"assistant","content":"普通回复"}\n\n'
        yield 'data: {"done":true}\n\n'

    monkeypatch.setattr(chat_router, "stream_chat", fake_stream_chat)
    response = client.post(
        "/api/chat",
        json={
            "query": "请介绍睡眠卫生。",
            "session_id": "session_not_saved",
            "patient_id": patient["id"],
            "save_to_history": False,
        },
    )
    assert response.status_code == 200
    assert client.get(f"/api/patients/{patient['id']}/history").json()["items"] == []
