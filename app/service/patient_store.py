"""SQLite-backed patient archive storage.

The archive is an opt-in, local prototype feature. Do not use it for real patient
records until real authentication, authorization, encryption, backups, and retention
controls have been implemented and reviewed.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INITIALIZED_PATHS: set[str] = set()
_INIT_LOCK = threading.Lock()


def data_dir() -> Path:
    return Path(os.getenv("PSYCONSULT_DATA_DIR", str(PROJECT_ROOT / "data"))).expanduser().resolve()


def database_path() -> Path:
    configured = os.getenv("PSYCONSULT_DATABASE_PATH")
    return Path(configured).expanduser().resolve() if configured else data_dir() / "psyconsult.sqlite3"


def upload_dir() -> Path:
    configured = os.getenv("PSYCONSULT_UPLOAD_DIR")
    return Path(configured).expanduser().resolve() if configured else data_dir() / "uploads"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _raw_connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _ensure_schema(path: Path) -> None:
    key = str(path)
    if key in _INITIALIZED_PATHS:
        return
    with _INIT_LOCK:
        if key in _INITIALIZED_PATHS:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = _raw_connect(path)
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    patient_code TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    sex TEXT,
                    birth_date TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived_at TEXT,
                    UNIQUE(user_id, patient_code)
                );

                CREATE INDEX IF NOT EXISTS idx_patients_owner_updated
                    ON patients(user_id, archived_at, updated_at DESC);

                CREATE TABLE IF NOT EXISTS consultation_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    patient_id TEXT NOT NULL REFERENCES patients(id),
                    session_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived_at TEXT,
                    UNIQUE(user_id, session_id)
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_patient_updated
                    ON consultation_sessions(user_id, patient_id, archived_at, updated_at DESC);

                CREATE TABLE IF NOT EXISTS consultation_messages (
                    id TEXT PRIMARY KEY,
                    session_record_id TEXT NOT NULL REFERENCES consultation_sessions(id),
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session_created
                    ON consultation_messages(session_record_id, created_at);

                CREATE TABLE IF NOT EXISTS assessment_results (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    patient_id TEXT NOT NULL REFERENCES patients(id),
                    scale_type TEXT NOT NULL CHECK(scale_type IN ('PHQ-9', 'GAD-7')),
                    answers_json TEXT NOT NULL,
                    total INTEGER NOT NULL,
                    severity_band TEXT NOT NULL,
                    safety_alert TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_assessments_patient_created
                    ON assessment_results(user_id, patient_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    patient_id TEXT NOT NULL REFERENCES patients(id),
                    original_filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    storage_key TEXT NOT NULL UNIQUE,
                    sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    archived_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_reports_patient_created
                    ON reports(user_id, patient_id, archived_at, created_at DESC);

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_audit_owner_created
                    ON audit_logs(user_id, created_at DESC);
                """
            )
            conn.commit()
            _INITIALIZED_PATHS.add(key)
        finally:
            conn.close()


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    path = database_path()
    _ensure_schema(path)
    conn = _raw_connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database() -> None:
    """Initialize schema explicitly during application startup."""
    _ensure_schema(database_path())


def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _audit(
    conn: sqlite3.Connection,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    # Never place patient names, message text, answers, or report content in audit metadata.
    conn.execute(
        """
        INSERT INTO audit_logs
            (id, user_id, action, resource_type, resource_id, created_at, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uuid.uuid4().hex,
            user_id,
            action,
            resource_type,
            resource_id,
            utc_now(),
            json.dumps(metadata or {}, ensure_ascii=False),
        ),
    )


def list_patients(user_id: str, search: str = "", limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    where = "user_id = ? AND archived_at IS NULL"
    params: list[Any] = [user_id]
    if search.strip():
        where += " AND (patient_code LIKE ? OR display_name LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term])
    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM patients WHERE {where}", params).fetchone()[0]
        rows = conn.execute(
            f"""SELECT id, patient_code, display_name, sex, birth_date, notes,
                       created_at, updated_at
                FROM patients WHERE {where}
                ORDER BY updated_at DESC LIMIT ? OFFSET ?""",
            [*params, limit, offset],
        ).fetchall()
    return [dict(row) for row in rows], int(total)


def get_patient(user_id: str, patient_id: str) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            """SELECT id, patient_code, display_name, sex, birth_date, notes,
                      created_at, updated_at
               FROM patients
               WHERE id = ? AND user_id = ? AND archived_at IS NULL""",
            (patient_id, user_id),
        ).fetchone()
    return _dict(row)


def create_patient(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    patient_id = uuid.uuid4().hex
    now = utc_now()
    birth_date = payload.get("birth_date")
    if isinstance(birth_date, date):
        birth_date = birth_date.isoformat()
    with db() as conn:
        conn.execute(
            """INSERT INTO patients
               (id, user_id, patient_code, display_name, sex, birth_date, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                patient_id, user_id, payload["patient_code"], payload["display_name"],
                payload.get("sex"), birth_date, payload.get("notes"), now, now,
            ),
        )
        _audit(conn, user_id, "create", "patient", patient_id)
    result = get_patient(user_id, patient_id)
    assert result is not None
    return result


def update_patient(user_id: str, patient_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"patient_code", "display_name", "sex", "birth_date", "notes"}
    values = {key: value for key, value in payload.items() if key in allowed}
    if not values:
        return get_patient(user_id, patient_id)
    if isinstance(values.get("birth_date"), date):
        values["birth_date"] = values["birth_date"].isoformat()
    values["updated_at"] = utc_now()
    assignments = ", ".join(f"{key} = ?" for key in values)
    with db() as conn:
        owned = conn.execute(
            "SELECT id FROM patients WHERE id = ? AND user_id = ? AND archived_at IS NULL",
            (patient_id, user_id),
        ).fetchone()
        if owned is None:
            return None
        conn.execute(
            f"UPDATE patients SET {assignments} WHERE id = ? AND user_id = ? AND archived_at IS NULL",
            [*values.values(), patient_id, user_id],
        )
        _audit(conn, user_id, "update", "patient", patient_id, {"fields": sorted(values)})
    return get_patient(user_id, patient_id)


def archive_patient(user_id: str, patient_id: str) -> bool:
    now = utc_now()
    with db() as conn:
        cursor = conn.execute(
            "UPDATE patients SET archived_at = ?, updated_at = ? WHERE id = ? AND user_id = ? AND archived_at IS NULL",
            (now, now, patient_id, user_id),
        )
        if cursor.rowcount:
            _audit(conn, user_id, "archive", "patient", patient_id)
        return cursor.rowcount > 0


def save_assessment(
    user_id: str,
    patient_id: str,
    scale_type: str,
    answers: list[int],
    total: int,
    severity_band: str,
    safety_alert: str | None,
) -> dict[str, Any]:
    record_id = uuid.uuid4().hex
    now = utc_now()
    with db() as conn:
        conn.execute(
            """INSERT INTO assessment_results
               (id, user_id, patient_id, scale_type, answers_json, total, severity_band, safety_alert, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record_id, user_id, patient_id, scale_type,
                json.dumps(answers, ensure_ascii=False), total, severity_band, safety_alert, now,
            ),
        )
        _audit(conn, user_id, "create", "assessment", record_id, {"scale_type": scale_type})
    return {
        "id": record_id,
        "patient_id": patient_id,
        "scale_type": scale_type,
        "answers": answers,
        "total": total,
        "severity_band": severity_band,
        "safety_alert": safety_alert,
        "created_at": now,
    }


def list_assessments(user_id: str, patient_id: str, limit: int = 100) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """SELECT id, patient_id, scale_type, answers_json, total, severity_band, safety_alert, created_at
               FROM assessment_results
               WHERE user_id = ? AND patient_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, patient_id, limit),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "patient_id": row["patient_id"],
            "scale_type": row["scale_type"],
            "answers": json.loads(row["answers_json"]),
            "total": row["total"],
            "severity_band": row["severity_band"],
            "safety_alert": row["safety_alert"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def create_report(
    user_id: str,
    patient_id: str,
    original_filename: str,
    content_type: str,
    size_bytes: int,
    storage_key: str,
    sha256: str,
) -> dict[str, Any]:
    report_id = uuid.uuid4().hex
    now = utc_now()
    with db() as conn:
        conn.execute(
            """INSERT INTO reports
               (id, user_id, patient_id, original_filename, content_type, size_bytes,
                storage_key, sha256, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report_id, user_id, patient_id, original_filename, content_type,
                size_bytes, storage_key, sha256, now,
            ),
        )
        _audit(conn, user_id, "upload", "report", report_id, {"size_bytes": size_bytes, "content_type": content_type})
    return {
        "id": report_id,
        "patient_id": patient_id,
        "original_filename": original_filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "created_at": now,
    }


def list_reports(user_id: str, patient_id: str, limit: int = 100) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """SELECT id, patient_id, original_filename, content_type, size_bytes, sha256, created_at
               FROM reports
               WHERE user_id = ? AND patient_id = ? AND archived_at IS NULL
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, patient_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_report(user_id: str, patient_id: str, report_id: str) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            """SELECT id, user_id, patient_id, original_filename, content_type, size_bytes,
                      storage_key, sha256, created_at
               FROM reports
               WHERE id = ? AND user_id = ? AND patient_id = ? AND archived_at IS NULL""",
            (report_id, user_id, patient_id),
        ).fetchone()
    return _dict(row)


def archive_report(user_id: str, patient_id: str, report_id: str) -> bool:
    with db() as conn:
        cursor = conn.execute(
            """UPDATE reports SET archived_at = ?
               WHERE id = ? AND user_id = ? AND patient_id = ? AND archived_at IS NULL""",
            (utc_now(), report_id, user_id, patient_id),
        )
        if cursor.rowcount:
            _audit(conn, user_id, "archive", "report", report_id)
        return cursor.rowcount > 0


def begin_saved_chat(user_id: str, patient_id: str, session_id: str, query: str) -> str:
    """Persist a user turn and return the internal session-record ID."""
    now = utc_now()
    with db() as conn:
        session = conn.execute(
            """SELECT id, patient_id FROM consultation_sessions
               WHERE user_id = ? AND session_id = ? AND archived_at IS NULL""",
            (user_id, session_id),
        ).fetchone()
        if session is not None:
            if session["patient_id"] != patient_id:
                raise ValueError("session_id 已关联到其他患者，不能跨患者复用")
            session_record_id = session["id"]
            conn.execute(
                "UPDATE consultation_sessions SET updated_at = ? WHERE id = ?",
                (now, session_record_id),
            )
        else:
            session_record_id = uuid.uuid4().hex
            conn.execute(
                """INSERT INTO consultation_sessions
                   (id, user_id, patient_id, session_id, title, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_record_id, user_id, patient_id, session_id, query[:80], now, now),
            )
        conn.execute(
            """INSERT INTO consultation_messages (id, session_record_id, role, content, created_at)
               VALUES (?, ?, 'user', ?, ?)""",
            (uuid.uuid4().hex, session_record_id, query, now),
        )
        _audit(conn, user_id, "append_message", "consultation_session", session_record_id)
    return session_record_id


def finish_saved_chat(user_id: str, session_record_id: str, assistant_text: str) -> None:
    if not assistant_text.strip():
        return
    now = utc_now()
    with db() as conn:
        owned = conn.execute(
            "SELECT id FROM consultation_sessions WHERE id = ? AND user_id = ? AND archived_at IS NULL",
            (session_record_id, user_id),
        ).fetchone()
        if owned is None:
            return
        conn.execute(
            """INSERT INTO consultation_messages (id, session_record_id, role, content, created_at)
               VALUES (?, ?, 'assistant', ?, ?)""",
            (uuid.uuid4().hex, session_record_id, assistant_text, now),
        )
        conn.execute(
            "UPDATE consultation_sessions SET updated_at = ? WHERE id = ?",
            (now, session_record_id),
        )


def list_history(user_id: str, patient_id: str, limit: int = 100) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """SELECT s.session_id, s.title, s.created_at, s.updated_at,
                      COUNT(m.id) AS message_count,
                      (SELECT m2.content FROM consultation_messages m2
                       WHERE m2.session_record_id = s.id
                       ORDER BY m2.rowid DESC LIMIT 1) AS last_message
               FROM consultation_sessions s
               LEFT JOIN consultation_messages m ON m.session_record_id = s.id
               WHERE s.user_id = ? AND s.patient_id = ? AND s.archived_at IS NULL
               GROUP BY s.id
               ORDER BY s.updated_at DESC LIMIT ?""",
            (user_id, patient_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_history_session(user_id: str, patient_id: str, session_id: str) -> dict[str, Any] | None:
    with db() as conn:
        session = conn.execute(
            """SELECT id, session_id, title, created_at, updated_at
               FROM consultation_sessions
               WHERE user_id = ? AND patient_id = ? AND session_id = ? AND archived_at IS NULL""",
            (user_id, patient_id, session_id),
        ).fetchone()
        if session is None:
            return None
        rows = conn.execute(
            """SELECT role, content, created_at FROM consultation_messages
               WHERE session_record_id = ? ORDER BY created_at ASC, rowid ASC""",
            (session["id"],),
        ).fetchall()
    return {
        "session_id": session["session_id"],
        "title": session["title"],
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "messages": [dict(row) for row in rows],
    }
