"""
routes/policy.py — Policy version endpoints.

GET  /policy/current              current active version of both doc types
GET  /policy/versions/{doc_type}  full version history for one doc type
POST /policy/versions             create a new version (supersedes the prior active one)

A material edit never updates a policy_versions row in place — it inserts a
new row and sets superseded_at on the one it replaces. Every write here also
writes a POLICY_VERSION_CREATED audit_log row.
"""

from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from observability.audit import write_audit
except ImportError:
    from backend.observability.audit import write_audit

router = APIRouter()

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_DIR / "db" / "procureops.db"

DOC_TYPES = ("procurement_policy_manual", "doa_matrix")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_active_version(conn: sqlite3.Connection, doc_type: str) -> sqlite3.Row | None:
    """Return the currently active (superseded_at IS NULL) row for doc_type, or None."""
    return conn.execute(
        "SELECT * FROM policy_versions WHERE doc_type=? AND superseded_at IS NULL "
        "ORDER BY effective_at DESC LIMIT 1",
        (doc_type,),
    ).fetchone()


class PolicyVersionCreate(BaseModel):
    doc_type: str = Field(..., description="'procurement_policy_manual' or 'doa_matrix'")
    version: str
    content: str
    created_by: str


@router.get("/policy/current")
def get_current_policy():
    conn = _connect()
    try:
        result = {}
        for doc_type in DOC_TYPES:
            row = get_active_version(conn, doc_type)
            result[doc_type] = dict(row) if row else None
        return result
    finally:
        conn.close()


@router.get("/policy/versions/{doc_type}")
def list_versions(doc_type: str):
    if doc_type not in DOC_TYPES:
        raise HTTPException(422, f"doc_type must be one of {DOC_TYPES}")
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, doc_type, version, effective_at, superseded_at, created_by, created_at "
            "FROM policy_versions WHERE doc_type=? ORDER BY effective_at DESC",
            (doc_type,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/policy/versions", status_code=201)
def create_version(body: PolicyVersionCreate):
    if body.doc_type not in DOC_TYPES:
        raise HTTPException(422, f"doc_type must be one of {DOC_TYPES}")

    conn = _connect()
    try:
        now = _now()
        new_id = str(uuid.uuid4())
        with conn:
            prior = get_active_version(conn, body.doc_type)
            if prior is not None:
                conn.execute(
                    "UPDATE policy_versions SET superseded_at=? WHERE id=?",
                    (now, prior["id"]),
                )
            conn.execute(
                "INSERT INTO policy_versions (id, doc_type, version, content, effective_at, "
                "superseded_at, created_by, created_at) VALUES (?,?,?,?,?,NULL,?,?)",
                (new_id, body.doc_type, body.version, body.content, now, body.created_by, now),
            )
        write_audit(
            actor=body.created_by, action="POLICY_VERSION_CREATED",
            payload={"doc_type": body.doc_type, "version": body.version,
                     "new_version_id": new_id, "superseded_version_id": prior["id"] if prior else None},
        )
        return {"id": new_id, "doc_type": body.doc_type, "version": body.version, "effective_at": now}
    finally:
        conn.close()
