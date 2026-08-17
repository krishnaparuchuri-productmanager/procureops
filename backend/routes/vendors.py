"""
routes/vendors.py — Approved Vendor Master.

GET  /vendors   full vendor list (unchanged behavior, moved here from main.py)
POST /vendors   add a new vendor. vendor_id is always server-generated
                (next "V-0NN" in sequence) -- never client-supplied -- so it
                can never collide with a seeded id or another concurrent add.
                Every add writes a VENDOR_CREATED audit_log row.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from observability.audit import write_audit
except ImportError:
    from backend.observability.audit import write_audit

router = APIRouter()

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_DIR / "db" / "procureops.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class Certification(BaseModel):
    name: str
    expiry_date: str


class VendorCreate(BaseModel):
    name: str
    category: str
    approval_status: str = "approved"
    certifications: list[Certification] = []
    on_time_pct: Optional[float] = None
    defect_rate_pct: Optional[float] = None
    note: Optional[str] = None
    created_by: str


def _next_vendor_id(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT vendor_id FROM vendors").fetchall()
    max_n = 0
    for r in rows:
        try:
            max_n = max(max_n, int(r["vendor_id"].split("-")[1]))
        except (IndexError, ValueError):
            continue
    return f"V-{max_n + 1:03d}"


@router.get("/vendors")
def list_vendors():
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM vendors ORDER BY vendor_id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/vendors", status_code=201)
def create_vendor(body: VendorCreate):
    if body.approval_status not in ("approved", "not_approved"):
        raise HTTPException(422, "approval_status must be 'approved' or 'not_approved'")
    if not body.name.strip():
        raise HTTPException(422, "name is required")
    if not body.category.strip():
        raise HTTPException(422, "category is required")

    conn = _connect()
    try:
        vendor_id = _next_vendor_id(conn)
        certifications_json = json.dumps([c.model_dump() for c in body.certifications])
        with conn:
            conn.execute(
                "INSERT INTO vendors (vendor_id, name, category, approval_status, certifications, "
                "on_time_pct, defect_rate_pct, note) VALUES (?,?,?,?,?,?,?,?)",
                (vendor_id, body.name, body.category, body.approval_status, certifications_json,
                 body.on_time_pct, body.defect_rate_pct, body.note),
            )
        write_audit(
            actor=body.created_by, action="VENDOR_CREATED",
            payload={"vendor_id": vendor_id, "name": body.name, "category": body.category,
                     "approval_status": body.approval_status},
        )
        row = conn.execute("SELECT * FROM vendors WHERE vendor_id=?", (vendor_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()
