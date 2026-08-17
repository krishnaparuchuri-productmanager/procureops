"""
seed/demo_seed.py — Bootstrap data for ProcureOps.

Idempotent: safe to call on every startup (checks for existing rows first).
Loads:
  1. The Approved Vendor Master (data/cases/vendors.json) into the vendors table.
  2. Initial policy_versions rows for the Procurement Policy Manual and DOA
     Matrix, sourced from the markdown files under data/policy/ — these are
     the SAME files retrieval.py indexes for RAG, so the policy snapshot a
     decision cites and the text an agent was actually grounded in are
     guaranteed to match at seed time.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_DIR / "db" / "procureops.db"
_DATA_DIR = _BACKEND_DIR / "data"

SEEDED_BY = "Krishna Paruchuri"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def seed_vendors(conn: sqlite3.Connection) -> int:
    existing = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
    if existing > 0:
        return 0

    vendors_path = _DATA_DIR / "cases" / "vendors.json"
    vendors = json.loads(vendors_path.read_text(encoding="utf-8"))
    for v in vendors:
        conn.execute(
            "INSERT INTO vendors (vendor_id, name, category, approval_status, certifications, "
            "on_time_pct, defect_rate_pct, note) VALUES (?,?,?,?,?,?,?,?)",
            (v["vendor_id"], v["name"], v["category"], v["approval_status"],
             json.dumps(v.get("certifications", [])), v.get("on_time_pct"),
             v.get("defect_rate_pct"), v.get("note")),
        )
    return len(vendors)


def seed_policy_versions(conn: sqlite3.Connection) -> int:
    existing = conn.execute("SELECT COUNT(*) FROM policy_versions").fetchone()[0]
    if existing > 0:
        return 0

    docs = [
        ("procurement_policy_manual", "data/policy/procurement_policy_manual.md", "2026-06-01"),
        ("doa_matrix",                "data/policy/doa_matrix.md",                "2026-06-01"),
    ]
    now = _now()
    count = 0
    for doc_type, rel_path, version in docs:
        content = (_BACKEND_DIR / rel_path).read_text(encoding="utf-8")
        conn.execute(
            "INSERT INTO policy_versions (id, doc_type, version, content, effective_at, "
            "superseded_at, created_by, created_at) VALUES (?,?,?,?,?,NULL,?,?)",
            (str(uuid.uuid4()), doc_type, version, content, now, SEEDED_BY, now),
        )
        count += 1
    return count


def seed_negotiation_history(conn: sqlite3.Connection) -> int:
    existing = conn.execute("SELECT COUNT(*) FROM negotiation_history").fetchone()[0]
    if existing > 0:
        return 0

    path = _DATA_DIR / "cases" / "negotiation_history.json"
    records = json.loads(path.read_text(encoding="utf-8"))["records"]
    for r in records:
        conn.execute(
            "INSERT INTO negotiation_history (negotiation_id, vendor_id, category, date, "
            "ask_type, ask_details, outcome, notes) VALUES (?,?,?,?,?,?,?,?)",
            (r["negotiation_id"], r["vendor_id"], r["category"], r["date"],
             r["ask_type"], r["ask_details"], r["outcome"], r.get("notes")),
        )
    return len(records)



# Default bounded-autonomy bands per category -- deliberately "tail spend"
# sized, well below what a Department Head would need to approve under the
# DOA matrix (see backend/data/policy/doa_matrix.md). A company tunes these
# via PUT /api/autonomy-policy/{category}; every change is audited.
_DEFAULT_AUTONOMY_POLICY = {
    "IT Hardware & Software":            {"max_renewal_value_usd": 15000, "min_vendor_on_time_pct": 95, "max_vendor_defect_rate_pct": 1.0, "max_price_increase_pct": 3},
    "Office Supplies & Equipment":       {"max_renewal_value_usd": 10000, "min_vendor_on_time_pct": 95, "max_vendor_defect_rate_pct": 1.0, "max_price_increase_pct": 5},
    "Professional Services":             {"max_renewal_value_usd": 20000, "min_vendor_on_time_pct": 90, "max_vendor_defect_rate_pct": 100, "max_price_increase_pct": 4},
    "Raw Materials / Production Inputs": {"max_renewal_value_usd": 25000, "min_vendor_on_time_pct": 93, "max_vendor_defect_rate_pct": 1.5, "max_price_increase_pct": 4},
    "Facilities & Maintenance":          {"max_renewal_value_usd": 15000, "min_vendor_on_time_pct": 93, "max_vendor_defect_rate_pct": 100, "max_price_increase_pct": 5},
    "Logistics & Freight":               {"max_renewal_value_usd": 15000, "min_vendor_on_time_pct": 94, "max_vendor_defect_rate_pct": 1.0, "max_price_increase_pct": 4},
}


def seed_autonomy_policy(conn: sqlite3.Connection) -> int:
    existing = conn.execute("SELECT COUNT(*) FROM autonomy_policy").fetchone()[0]
    if existing > 0:
        return 0

    now = _now()
    for category, bands in _DEFAULT_AUTONOMY_POLICY.items():
        conn.execute(
            "INSERT INTO autonomy_policy (category, max_renewal_value_usd, min_vendor_on_time_pct, "
            "max_vendor_defect_rate_pct, max_price_increase_pct, updated_by, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (category, bands["max_renewal_value_usd"], bands["min_vendor_on_time_pct"],
             bands["max_vendor_defect_rate_pct"], bands["max_price_increase_pct"], SEEDED_BY, now),
        )
    return len(_DEFAULT_AUTONOMY_POLICY)


def seed_vendor_quote_history(conn: sqlite3.Connection) -> int:
    existing = conn.execute("SELECT COUNT(*) FROM vendor_quote_history").fetchone()[0]
    if existing > 0:
        return 0

    path = _DATA_DIR / "cases" / "vendor_quote_history.json"
    records = json.loads(path.read_text(encoding="utf-8"))["records"]
    for r in records:
        conn.execute(
            "INSERT INTO vendor_quote_history (quote_id, vendor_id, category, date, unit_price, qty, notes) "
            "VALUES (?,?,?,?,?,?,?)",
            (r["quote_id"], r["vendor_id"], r["category"], r["date"], r["unit_price"], r["qty"], r.get("notes")),
        )
    return len(records)


def seed_demo_data() -> None:
    conn = _connect()
    try:
        with conn:
            vendor_count = seed_vendors(conn)
            policy_count = seed_policy_versions(conn)
            negotiation_count = seed_negotiation_history(conn)
            autonomy_count = seed_autonomy_policy(conn)
            quote_history_count = seed_vendor_quote_history(conn)
        if vendor_count or policy_count or negotiation_count or autonomy_count or quote_history_count:
            print(f"[seed] Loaded {vendor_count} vendors, {policy_count} policy_versions rows, "
                  f"{negotiation_count} negotiation_history rows, {autonomy_count} autonomy_policy rows, "
                  f"{quote_history_count} vendor_quote_history rows.")
        else:
            print("[seed] Data already present — skipping.")
    finally:
        conn.close()


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.path.insert(0, str(_BACKEND_DIR))
    from db.init_db import init_db
    init_db()
    seed_demo_data()
