"""
routes/autonomy.py — Bounded-autonomy threshold configuration.

GET /autonomy-policy              every category's current auto-approval bands
PUT /autonomy-policy/{category}   update one category's bands

These are the exact numbers agents/autonomy_rules.py evaluates against to
decide whether a contract renewal auto-clears — see that module's docstring.
Mutable by design (a company tunes these occasionally, this is not an
immutable snapshot like policy_versions), but every change still writes an
audit_log row with the full before/after, so who-changed-what-when stays
traceable.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from observability.audit import write_audit
except ImportError:
    from backend.observability.audit import write_audit

router = APIRouter()

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_DIR / "db" / "procureops.db"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


class AutonomyPolicyUpdate(BaseModel):
    max_renewal_value_usd: float
    min_vendor_on_time_pct: float
    max_vendor_defect_rate_pct: float
    max_price_increase_pct: float
    updated_by: str


@router.get("/autonomy-policy")
def list_autonomy_policy():
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM autonomy_policy ORDER BY category").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/autonomy-policy/{category}")
def get_autonomy_policy_for_category(category: str):
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM autonomy_policy WHERE category=?", (category,)).fetchone()
        if not row:
            raise HTTPException(404, f"No autonomy policy configured for category '{category}'")
        return dict(row)
    finally:
        conn.close()


@router.put("/autonomy-policy/{category}")
def update_autonomy_policy(category: str, body: AutonomyPolicyUpdate):
    if body.max_renewal_value_usd <= 0:
        raise HTTPException(422, "max_renewal_value_usd must be positive")
    if not (0 <= body.min_vendor_on_time_pct <= 100):
        raise HTTPException(422, "min_vendor_on_time_pct must be between 0 and 100")
    if not (0 <= body.max_vendor_defect_rate_pct <= 100):
        raise HTTPException(422, "max_vendor_defect_rate_pct must be between 0 and 100")
    if body.max_price_increase_pct < 0:
        raise HTTPException(422, "max_price_increase_pct cannot be negative")

    conn = _connect()
    try:
        before = conn.execute("SELECT * FROM autonomy_policy WHERE category=?", (category,)).fetchone()
        if not before:
            raise HTTPException(404, f"No autonomy policy configured for category '{category}'")

        now = _now()
        with conn:
            conn.execute(
                "UPDATE autonomy_policy SET max_renewal_value_usd=?, min_vendor_on_time_pct=?, "
                "max_vendor_defect_rate_pct=?, max_price_increase_pct=?, updated_by=?, updated_at=? "
                "WHERE category=?",
                (body.max_renewal_value_usd, body.min_vendor_on_time_pct, body.max_vendor_defect_rate_pct,
                 body.max_price_increase_pct, body.updated_by, now, category),
            )
        write_audit(
            actor=body.updated_by, action="AUTONOMY_POLICY_UPDATED",
            payload={"category": category, "before": dict(before),
                     "after": {"max_renewal_value_usd": body.max_renewal_value_usd,
                               "min_vendor_on_time_pct": body.min_vendor_on_time_pct,
                               "max_vendor_defect_rate_pct": body.max_vendor_defect_rate_pct,
                               "max_price_increase_pct": body.max_price_increase_pct}},
        )
        row = conn.execute("SELECT * FROM autonomy_policy WHERE category=?", (category,)).fetchone()
        return dict(row)
    finally:
        conn.close()
