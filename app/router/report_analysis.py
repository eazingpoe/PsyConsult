# API endpoints for analysis of reports in a patient archive.
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.router.chat import require_chat_identity
from app.router.patients import ALLOWED_REPORTS, MAX_REPORT_BYTES, _safe_filename, _verify_report_content
from starlette.concurrency import run_in_threadpool
from app.service import patient_store, report_analysis_store, report_analysis_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_uuid(value: str, label: str) -> None:
    try:
        uuid.UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail=f"{label} ID 格式无效") from exc


def _require_report(user_id: str, patient_id: str, report_id: str) -> dict:
    if not patient_store.get_patient(user_id, patient_id):
        raise HTTPException(status_code=404, detail="患者档案不存在")
    report = patient_store.get_report(user_id, patient_id, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在或已归档")
    return report


def _report_path(report: dict) -> Path:
    root = patient_store.upload_dir().resolve()
    path = (root / report["storage_key"]).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(status_code=404, detail="报告文件不存在")
    return path


@router.post("/patients/{patient_id}/reports/{report_id}/analyze")
def analyze_patient_report(
    patient_id: str,
    report_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    _validate_uuid(report_id, "报告")
    report = _require_report(user_id, patient_id, report_id)
    path = _report_path(report)
    try:
        extracted_text, extraction_method = report_analysis_service.extract_report_text(
            path, report["original_filename"]
        )
    except report_analysis_service.ReportExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        analysis_markdown, model_name = report_analysis_service.generate_report_analysis(
            extracted_text, report["original_filename"]
        )
    except Exception as exc:
        logger.exception(
            "report_analysis_model_failed user_id=%s patient_id=%s report_id=%s",
            user_id, patient_id, report_id,
        )
        raise HTTPException(
            status_code=502,
            detail="报告文本已提取，但模型分析失败。请检查后端模型配置和日志后重试。",
        ) from exc
    return report_analysis_store.create_analysis(
        user_id=user_id,
        patient_id=patient_id,
        report_id=report_id,
        extracted_text=extracted_text,
        analysis_markdown=analysis_markdown,
        extraction_method=extraction_method,
        model_name=model_name,
    )


@router.get("/patients/{patient_id}/reports/{report_id}/analyses")
def list_patient_report_analyses(
    patient_id: str,
    report_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
    limit: int = Query(default=50, ge=1, le=100),
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    _validate_uuid(report_id, "报告")
    _require_report(user_id, patient_id, report_id)
    return {
        "items": report_analysis_store.list_analyses(
            user_id, patient_id, report_id, limit
        )
    }


@router.get("/patients/{patient_id}/reports/{report_id}/analyses/{analysis_id}")
def get_patient_report_analysis(
    patient_id: str,
    report_id: str,
    analysis_id: str,
    user_id: Annotated[str, Depends(require_chat_identity)],
) -> dict:
    _validate_uuid(patient_id, "患者档案")
    _validate_uuid(report_id, "报告")
    _validate_uuid(analysis_id, "分析记录")
    _require_report(user_id, patient_id, report_id)
    item = report_analysis_store.get_analysis(
        user_id, patient_id, report_id, analysis_id
    )
    if not item:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    return item


@router.post("/chat/report-analysis")
async def analyze_uploaded_report(
    user_id: Annotated[str, Depends(require_chat_identity)],
    file: UploadFile = File(...),
) -> dict:
    # Analyze an uploaded report for chat without persisting the file.
    try:
        filename = _safe_filename(file.filename)
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_REPORTS:
            raise HTTPException(
                status_code=415,
                detail="仅支持 PDF、DOCX、PNG、JPG 或 JPEG 报告",
            )

        content = await file.read(MAX_REPORT_BYTES + 1)
        if len(content) > MAX_REPORT_BYTES:
            raise HTTPException(status_code=413, detail="报告文件不能超过 20 MB")
        if not content:
            raise HTTPException(status_code=400, detail="上传的报告文件为空")

        _verify_report_content(extension, content)

        with TemporaryDirectory(prefix="psyconsult-chat-report-") as temp_dir:
            temp_path = Path(temp_dir) / f"uploaded{extension}"
            temp_path.write_bytes(content)

            try:
                extracted_text, extraction_method = await run_in_threadpool(
                    report_analysis_service.extract_report_text,
                    temp_path,
                    filename,
                )
            except report_analysis_service.ReportExtractionError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

            try:
                analysis_markdown, model_name = await run_in_threadpool(
                    report_analysis_service.generate_report_analysis,
                    extracted_text,
                    filename,
                )
            except Exception as exc:
                logger.exception(
                    "chat_report_analysis_model_failed user_id=%s filename=%s",
                    user_id,
                    filename,
                )
                raise HTTPException(
                    status_code=502,
                    detail="报告文本已提取，但模型分析失败。请检查后端模型配置和日志后重试。",
                ) from exc

        return {
            "filename": filename,
            "analysis_markdown": analysis_markdown,
            "extraction_method": extraction_method,
            "model_name": model_name,
            "archived": False,
        }
    finally:
        await file.close()

