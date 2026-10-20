from __future__ import annotations

import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.router import transcribe


def upload(data: bytes, filename: str = "voice.webm", mime: str = "audio/webm") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(data),
        headers=Headers({"content-type": mime}),
    )


def test_transcribe_returns_text_without_logging_or_storing_audio(monkeypatch):
    monkeypatch.setattr(transcribe.settings, "dashscope_api_key", "test-key")
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "我最近睡眠不太好。"}}]}

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers, json):
            captured.update(url=url, headers=headers, body=json)
            return FakeResponse()

    monkeypatch.setattr(transcribe.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(
        transcribe.transcribe_audio(user_id="doctor_001", file=upload(b"fake-webm-audio"))
    )

    assert result == {"text": "我最近睡眠不太好。"}
    assert captured["body"]["model"] == "qwen3-asr-flash"
    assert captured["body"]["messages"][0]["content"][0]["input_audio"]["data"].startswith(
        "data:audio/webm;base64,"
    )
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["client_kwargs"]["trust_env"] is False


def test_transcribe_rejects_unsupported_mime_type():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            transcribe.transcribe_audio(
                user_id="doctor_001",
                file=upload(b"audio", filename="voice.txt", mime="text/plain"),
            )
        )
    assert exc.value.status_code == 415


def test_transcribe_rejects_empty_audio():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            transcribe.transcribe_audio(
                user_id="doctor_001", file=upload(b"")
            )
        )
    assert exc.value.status_code == 400


def test_transcribe_rejects_audio_over_size_limit():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            transcribe.transcribe_audio(
                user_id="doctor_001",
                file=upload(b"x" * (transcribe.MAX_AUDIO_BYTES + 1)),
            )
        )
    assert exc.value.status_code == 413
