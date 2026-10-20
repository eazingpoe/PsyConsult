# SQLite persistence for report analysis history.
from __future__ import annotations

import uuid
from typing import Any

from app.service import patient_store


def _ensure_table(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS report_analyses ("
        "id TEXT PRIMARY KEY, user_id TEXT NOT NULL, "
        "patient_id TEXT NOT NULL REFERENCES patients(id), "
        "report_id TEXT NOT NULL REFERENCES reports(id), "
        "extracted_text TEXT NOT NULL, analysis_markdown TEXT NOT NULL, "
        "extraction_method TEXT NOT NULL, model_name TEXT NOT NULL, "
        "created_at TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_analyses_history "
        "ON report_analyses(user_id, patient_id, report_id, created_at DESC)"
    )


def create_analysis(
    *, user_id: str, patient_id: str, report_id: str,
    extracted_text: str, analysis_markdown: str,
    extraction_method: str, model_name: str,
) -> dict[str, Any]:
    analysis_id = uuid.uuid4().hex
    created_at = patient_store.utc_now()
    with patient_store.db() as conn:
        _ensure_table(conn)
        conn.execute(
            "INSERT INTO report_analyses "
            "(id, user_id, patient_id, report_id, extracted_text, "
            "analysis_markdown, extraction_method, model_name, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (analysis_id, user_id, patient_id, report_id, extracted_text,
             analysis_markdown, extraction_method, model_name, created_at),
        )
        row = conn.execute(
            "SELECT id, user_id, patient_id, report_id, extracted_text, "
            "analysis_markdown, extraction_method, model_name, created_at "
            "FROM report_analyses WHERE id = ?", (analysis_id,)
        ).fetchone()
    return dict(row)


def list_analyses(
    user_id: str, patient_id: str, report_id: str, limit: int = 50
) -> list[dict[str, Any]]:
    with patient_store.db() as conn:
        _ensure_table(conn)
        rows = conn.execute(
            "SELECT id, patient_id, report_id, extraction_method, model_name, "
            "created_at, substr(analysis_markdown, 1, 260) AS preview "
            "FROM report_analyses WHERE user_id = ? AND patient_id = ? AND report_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, patient_id, report_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_analysis(
    user_id: str, patient_id: str, report_id: str, analysis_id: str
) -> dict[str, Any] | None:
    with patient_store.db() as conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT id, user_id, patient_id, report_id, extracted_text, "
            "analysis_markdown, extraction_method, model_name, created_at "
            "FROM report_analyses "
            "WHERE id = ? AND user_id = ? AND patient_id = ? AND report_id = ?",
            (analysis_id, user_id, patient_id, report_id),
        ).fetchone()
    return dict(row) if row else None
