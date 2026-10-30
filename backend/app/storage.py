import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def database_path() -> Path:
    configured = os.getenv("RUN_DB_PATH", "data/run_state.sqlite3")
    path = Path(configured)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(database_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                proposal_json TEXT NOT NULL,
                result_json TEXT NOT NULL DEFAULT '{}',
                correlation_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS quarantine (
                quarantine_id TEXT PRIMARY KEY,
                payload_sha256 TEXT NOT NULL,
                field_errors_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                satisfactory INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(run_id)
            );
            """
        )


def create_run(run_id: str, proposal: dict[str, Any], correlation_id: str) -> None:
    now = utc_now()
    initialize()
    with connect() as conn:
        conn.execute(
            """INSERT INTO runs
            (run_id, status, proposal_json, result_json, correlation_id, created_at, updated_at)
            VALUES (?, 'pending', ?, '{}', ?, ?, ?)""",
            (run_id, json.dumps(proposal, sort_keys=True), correlation_id, now, now),
        )


def update_run(run_id: str, status: str, result: dict[str, Any]) -> None:
    initialize()
    with connect() as conn:
        conn.execute(
            "UPDATE runs SET status=?, result_json=?, updated_at=? WHERE run_id=?",
            (status, json.dumps(result, ensure_ascii=False), utc_now(), run_id),
        )


def get_run(run_id: str) -> dict[str, Any] | None:
    initialize()
    with connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
    if row is None:
        return None
    result = json.loads(row["result_json"])
    return {
        "run_id": row["run_id"],
        "status": row["status"],
        "building_details": json.loads(row["proposal_json"]),
        "correlation_id": row["correlation_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        **result,
    }


def quarantine_rejection(payload: bytes, errors: list[dict[str, Any]]) -> str:
    import hashlib

    quarantine_id = str(uuid4())
    initialize()
    with connect() as conn:
        conn.execute(
            """INSERT INTO quarantine
            (quarantine_id, payload_sha256, field_errors_json, created_at)
            VALUES (?, ?, ?, ?)""",
            (
                quarantine_id,
                hashlib.sha256(payload).hexdigest(),
                json.dumps(errors, ensure_ascii=False),
                utc_now(),
            ),
        )
    return quarantine_id


def get_quarantine(quarantine_id: str) -> dict[str, Any] | None:
    initialize()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM quarantine WHERE quarantine_id=?", (quarantine_id,)
        ).fetchone()
    if row is None:
        return None
    return {
        "quarantine_id": row["quarantine_id"],
        "payload_sha256": row["payload_sha256"],
        "field_errors": json.loads(row["field_errors_json"]),
        "created_at": row["created_at"],
    }


def save_feedback(run_id: str, satisfactory: bool, reason: str) -> dict[str, Any]:
    feedback_id = str(uuid4())
    initialize()
    with connect() as conn:
        if conn.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone() is None:
            raise KeyError(run_id)
        conn.execute(
            """INSERT INTO feedback
            (feedback_id, run_id, satisfactory, reason, created_at)
            VALUES (?, ?, ?, ?, ?)""",
            (feedback_id, run_id, int(satisfactory), reason, utc_now()),
        )
    return {
        "feedback_id": feedback_id,
        "run_id": run_id,
        "satisfactory": satisfactory,
        "reason": reason,
    }


def feedback_summary() -> dict[str, int | float]:
    initialize()
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(satisfactory), 0) AS positive FROM feedback"
        ).fetchone()
    total = int(row["total"])
    positive = int(row["positive"])
    return {
        "total": total,
        "satisfactory": positive,
        "unsatisfactory": total - positive,
        "satisfaction_rate": positive / total if total else 0.0,
    }
