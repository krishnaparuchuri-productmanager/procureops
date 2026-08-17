"""
observability/audit.py — INSERT-only audit log writer for ProcureOps.

Same guarantee as agentops/backend/database.py's audit_log: no UPDATE or
DELETE statement anywhere in this codebase ever references this table.
write_audit() never raises to callers — a logging failure must never break
a live governance decision — but unlike tracer.py's log_trace(), a failure
here is worth knowing loudly since a missing audit row is a compliance gap,
not just a missing debug record, so it always prints to stderr on failure.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_DIR / "db" / "procureops.db"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_audit(actor: str, action: str, payload: dict[str, Any] | None = None,
                 reason_code: str | None = None, db_path: Path | None = None,
                 conn: sqlite3.Connection | None = None) -> str | None:
    """Insert one row into audit_log. Returns the new row's id, or None on failure.

    Pass `conn` when called from inside a caller's already-open transaction
    (e.g. routes/decisions.py's _create_decision, which writes the decision
    and its DECISION_PROPOSED audit row atomically). Opening a second SQLite
    connection while the first still holds an uncommitted write transaction
    raises "database is locked" — this bit ProcureOps itself during testing,
    caught only because write_audit's broad except swallowed it silently and
    the resulting missing audit row was visible in the UI. Reusing the
    caller's connection avoids the second writer entirely. When no conn is
    supplied (e.g. a standalone script, or a call made after the caller's own
    transaction already committed), a fresh connection is opened as before.
    """
    row_id = str(uuid.uuid4())
    target = db_path or _DB_PATH
    try:
        if conn is not None:
            conn.execute(
                "INSERT INTO audit_log (id, event_time, actor, action, reason_code, payload) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (row_id, _now(), actor, action, reason_code, json.dumps(payload or {})),
            )
            return row_id

        own_conn = sqlite3.connect(target)
        try:
            with own_conn:
                own_conn.execute(
                    "INSERT INTO audit_log (id, event_time, actor, action, reason_code, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (row_id, _now(), actor, action, reason_code, json.dumps(payload or {})),
                )
        finally:
            own_conn.close()
        return row_id
    except Exception as exc:  # noqa: BLE001
        print(f"[audit] ERROR: failed to write audit row (actor={actor}, action={action}): "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return None


def get_recent_audit(limit: int = 50, db_path: Path | None = None) -> list[dict[str, Any]]:
    target = db_path or _DB_PATH
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY event_time DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
