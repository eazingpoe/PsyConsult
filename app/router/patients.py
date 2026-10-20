"""Patient archive API: metadata, assessments, saved chat history and report files."""
from __future__ import annotations

import hashlib
import io
import logging
import re
import uuid
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.router.chat import require_chat_identity
from app.schemas.assessment import AssessmentScoreRequest
from app.schemas.patients import PatientCreate, PatientUpdate
from app.service import patient_store
from app.service.assessment_service import calculate_assessment_result

logger = logging.getLogger("clinical_cds.patient_archive")
router = APIRouter()
MAX_REPORT_BYTES = 20 * 1024 * 1024
ALLOWED_REPORTS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
HEX_ID = re.compile(r"^[a-f0-9]{32}$", re.IGNORECASE)


def _require_patient(user_id: str, patient_id: str) -> dict:
    patient = patient_store.get_patient(user_id, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="患者不存在或无权访问")
    return patient


def _validate_uuid(value: str, resource_name: str) -> None:
    if not HEX_ID.fullmatch(value):
        raise HTTPException(status_code=404, detail=f"{resource_name}不存在")


def _safe_filename(filename: str | None) -> str:
    raw = (filename or "report").replace("\\", "/").split("/")[-1]
    cleaned = "".join(ch for ch in raw if ch.isprintable() and ch not in "\r\n\x00")
    return (cleaned or "report")[:255]


def _verify_report_content(extension: str, content: bytes) -> None:
    if extension in {".png", ".jpg", ".jpeg"}:
        if extension == ".png":
            valid_image = content.startswith(b"\x89PNG\r\n\x1a\n")
        else:
            valid_image = content.startswith(b"\xff\xd8\xff")
        if not valid_image:
            raise HTTPException(status_code=415, detail="图片内容与文件扩展名不匹配")
        return

    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=415, detail="文件内容不是有效的 PDF 文件")
        return

    if extension == ".docx":
        if not content.startswith(b"PK"):
            raise HTTPException(status_code=415, detail="文件内容不是有效的 DOCX 文件")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise HTTPException(status_code=415, detail="DOCX 文件缺少正文内容")
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=415, detail="DOCX 文件结构无效") from exc
        return

    raise HTTPException(status_code=415, detail="仅支持 PDF 和 DOCX 报告")


@router.get("/patients")
def get_patients(
    user_id: Annotated[str, Depends(require_chat_identity)],
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    items, total = patient_store.list_patients(user_id, search, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/patients", status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    user_id: Annotated[str, Depends(require_chat_identity)],
) -> dict:
    try:
        patient = patient_store.create_patient(user_id, payload.model_dump())
    except Exception as exc:
        # Do not expose raw database errors to the client.
        if "UNIQUE constraint failed" in str(exc):
            raise HTTPException(status_code=409, detail="该患者编号已存在") from exc
        logger.exception("patient_create_failed user_id=%s", user_id)
        raise HTTPException(status_code=500, detail="患者档案创建失败") from exc
    return patient


@router.get("/patients/{patient_id}")
def get_patient(
    patient_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    return _require_patient(user_id, patient_id)


@router.patch("/patients/{patient_id}")
def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    user_id: Annotated[str, Depends(require_chat_identity)],
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    _require_patient(user_id, patient_id)
    try:
        patient = patient_store.update_patient(
            user_id, patient_id, payload.model_dump(exclude_unset=True)
        )
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise HTTPException(status_code=409, detail="该患者编号已存在") from exc
        logger.exception("patient_update_failed user_id=%s patient_id=%s", user_id, patient_id)
        raise HTTPException(status_code=500, detail="患者档案更新失败") from exc
    if patient is None:
        raise HTTPException(status_code=404, detail="患者不存在或无权访问")
    return patient


@router.delete("/patients/{patient_id}")
def archive_patient(
    patient_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    if not patient_store.archive_patient(user_id, patient_id):
        raise HTTPException(status_code=404, detail="患者不存在或无权访问")
    return {"status": "success", "archived": True}


@router.get("/patients/{patient_id}/assessments")
def get_assessments(
    patient_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    _require_patient(user_id, patient_id)
    return {"items": patient_store.list_assessments(user_id, patient_id, limit)}


@router.post("/patients/{patient_id}/assessments", status_code=status.HTTP_201_CREATED)
def save_patient_assessment(
    patient_id: str,
    payload: AssessmentScoreRequest,
    user_id: Annotated[str, Depends(require_chat_identity)],
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    _require_patient(user_id, patient_id)
    try:
        result = calculate_assessment_result(payload.scale_type, payload.answers)
        record = patient_store.save_assessment(
            user_id=user_id,
            patient_id=patient_id,
            scale_type=result["scale_type"],
            answers=payload.answers,
            total=result["total"],
            severity_band=result["severity_band"],
            safety_alert=result["safety_alert"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("assessment_save_failed user_id=%s patient_id=%s", user_id, patient_id)
        raise HTTPException(status_code=500, detail="量表结果保存失败") from exc

    result.update(
        {
            "answers_stored": True,
            "record_id": record["id"],
            "created_at": record["created_at"],
        }
    )
    return result


@router.get("/patients/{patient_id}/history")
def get_patient_history(
    patient_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    _require_patient(user_id, patient_id)
    return {"items": patient_store.list_history(user_id, patient_id, limit)}


@router.get("/patients/{patient_id}/history/{session_id}")
def get_patient_history_session(
    patient_id: str,
    session_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    _require_patient(user_id, patient_id)
    session = patient_store.get_history_session(user_id, patient_id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="历史会话不存在")
    return session


@router.get("/patients/{patient_id}/reports")
def get_patient_reports(
    patient_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    _require_patient(user_id, patient_id)
    return {"items": patient_store.list_reports(user_id, patient_id, limit)}


@router.post("/patients/{patient_id}/reports", status_code=status.HTTP_201_CREATED)
async def upload_patient_report(
    patient_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
    file: UploadFile = File(...),
) -> dict:
    try:
        _validate_uuid(patient_id, "患者档案")
        _require_patient(user_id, patient_id)

        filename = _safe_filename(file.filename)
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_REPORTS:
            raise HTTPException(status_code=415, detail="仅支持 PDF、DOCX、PNG 或 JPG 报告")

        content = await file.read(MAX_REPORT_BYTES + 1)
        if len(content) > MAX_REPORT_BYTES:
            raise HTTPException(status_code=413, detail="报告文件不能超过 20 MB")
        _verify_report_content(extension, content)

        storage_key = uuid.uuid4().hex
        target_dir = patient_store.upload_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / storage_key
        digest = hashlib.sha256(content).hexdigest()
        content_type = ALLOWED_REPORTS[extension]

        try:
            target_path.write_bytes(content)
            return patient_store.create_report(
                user_id=user_id,
                patient_id=patient_id,
                original_filename=filename,
                content_type=content_type,
                size_bytes=len(content),
                storage_key=storage_key,
                sha256=digest,
            )
        except Exception as exc:
            target_path.unlink(missing_ok=True)
            logger.exception("report_upload_failed user_id=%s patient_id=%s", user_id, patient_id)
            raise HTTPException(status_code=500, detail="报告上传失败") from exc
    finally:
        await file.close()


@router.get("/patients/{patient_id}/reports/{report_id}/download")
def download_patient_report(
    patient_id: str,
    report_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
):
    _validate_uuid(patient_id, "患者档案")
    _validate_uuid(report_id, "报告")
    _require_patient(user_id, patient_id)
    report = patient_store.get_report(user_id, patient_id, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在或无权访问")

    if not HEX_ID.fullmatch(report["storage_key"]):
        logger.error("report_storage_key_invalid report_id=%s", report_id)
        raise HTTPException(status_code=500, detail="报告存储标识无效")
    path = patient_store.upload_dir() / report["storage_key"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="报告文件不存在")
    return FileResponse(
        path,
        media_type=report["content_type"],
        filename=report["original_filename"],
    )


@router.delete("/patients/{patient_id}/reports/{report_id}")
def archive_patient_report(
    patient_id: str,
    report_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    _validate_uuid(report_id, "报告")
    _require_patient(user_id, patient_id)
    if not patient_store.archive_report(user_id, patient_id, report_id):
        raise HTTPException(status_code=404, detail="报告不存在或无权访问")
    return {"status": "success", "archived": True}
