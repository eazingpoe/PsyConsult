import json
import logging
import re
import secrets
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from app.app_config.settings import settings
from app.schemas.chat import ChatRequest
from app.service import patient_store
from app.service.chat_service import stream_chat

router = APIRouter()
logger = logging.getLogger("clinical_cds.chat")
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def require_chat_identity(
    authorization: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> str:
    if settings.api_auth_token:
        token = _extract_bearer_token(authorization)
        if token is None or not secrets.compare_digest(token, settings.api_auth_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-User-Id header",
        )

    user_id = x_user_id
    if not USER_ID_PATTERN.fullmatch(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-User-Id header",
        )
    return user_id


def _content_from_sse_chunk(chunk: str) -> list[str]:
    """Extract answer text for history storage without changing the SSE bytes sent to the UI."""
    pieces: list[str] = []
    for line in chunk.replace("\r\n", "\n").splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if event.get("status") or event.get("done"):
            continue
        content = event.get("content")
        if isinstance(content, str) and content:
            pieces.append(content)
    return pieces


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    user_id: Annotated[str, Depends(require_chat_identity)],
):
    """Return the existing SSE stream; optionally persist a patient-linked turn."""
    session_record_id: str | None = None
    persistence_failed = False

    if request.save_to_history:
        # The schema guarantees patient_id is present. Verify ownership before writing.
        # If the archive database is temporarily unavailable, do not block the existing
        # chat/SSE/safety flow; continue without persisting this turn.
        try:
            patient = patient_store.get_patient(user_id, request.patient_id or "")
            if patient is None:
                raise HTTPException(status_code=404, detail="患者不存在或无权访问")
            session_record_id = patient_store.begin_saved_chat(
                user_id=user_id,
                patient_id=request.patient_id or "",
                session_id=request.session_id,
                query=request.query,
            )
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception:
            logger.exception(
                "patient_history_write_start_failed user_id=%s session_id=%s",
                user_id,
                request.session_id,
            )
            persistence_failed = True

    async def stream_with_history() -> AsyncIterator[str]:
        answer_parts: list[str] = []
        if persistence_failed:
            yield (
                'data: {"status":"history_save_failed",'
                '"content":"本次回答仍会继续生成，但历史记录未能保存。"}\n\n'
            )
        try:
            async for chunk in stream_chat(request.query, user_id, request.session_id):
                answer_parts.extend(_content_from_sse_chunk(chunk))
                yield chunk
        finally:
            if session_record_id:
                try:
                    patient_store.finish_saved_chat(
                        user_id, session_record_id, "".join(answer_parts)
                    )
                except Exception:
                    # A database failure must never replace or suppress an SSE safety response.
                    logger.exception(
                        "patient_history_write_finish_failed user_id=%s session_id=%s",
                        user_id,
                        request.session_id,
                    )

    return StreamingResponse(
        stream_with_history(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
