"""
main.py — FastAPI application entry point for ProcureOps.

Run with:
    uvicorn backend.main:app --reload          # from project root
    uvicorn main:app --reload --port 8000      # from backend/
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.init_db import init_db, migrate_db
from seed.demo_seed import seed_demo_data

from routes.decisions import router as decisions_router
from routes.policy import router as policy_router

try:
    from agents.router import route as route_request
    from agents.extraction import extract_invoice_fields, extract_inventory_fields
    from observability.audit import get_recent_audit
    from routes.policy import get_active_version
except ImportError:
    from backend.agents.router import route as route_request
    from backend.agents.extraction import extract_invoice_fields, extract_inventory_fields
    from backend.observability.audit import get_recent_audit
    from backend.routes.policy import get_active_version

import json
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent / "db" / "procureops.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    migrate_db()
    seed_demo_data()
    yield


app = FastAPI(
    title="ProcureOps",
    description=(
        "A Procurement Router + 4 Specialists governance vertical: requisition intake, "
        "sourcing/quote comparison, invoice three-way match, and inventory management, "
        "with maker-checker enforcement, an INSERT-only audit log, and policy-snapshot-at-"
        "decision-time. All data is synthetic — no real ERP or payment integration."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "https://procureops.krishnaparuchuri.com",
    "https://procureops.krishna1parchuri.workers.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

app.include_router(decisions_router, prefix="/api", tags=["Decisions"])
app.include_router(policy_router, prefix="/api", tags=["Policy"])


@app.post("/api/route", tags=["Router"])
def classify_request(body: dict):
    """POST {"user_input": "..."} -> {task_type, specialist_agent_id, ambiguous, rationale}."""
    return route_request(body.get("user_input", ""))


@app.post("/api/extract", tags=["Router"])
def extract_fields(body: dict):
    """POST {"task_type": "invoice"|"inventory", "raw_text": "..."} -> best-effort structured
    fields, every one nullable. Never called for "sourcing" -- see agents/extraction.py docstring
    for why fabricating quote rows from a sentence isn't something this endpoint will do. Parsing
    only; the result is always shown to a human as an editable form before anything is submitted."""
    task_type = body.get("task_type")
    raw_text = body.get("raw_text", "")
    if task_type == "invoice":
        return {"fields": extract_invoice_fields(raw_text)}
    if task_type == "inventory":
        return {"fields": extract_inventory_fields(raw_text)}
    return {"fields": {}}


@app.get("/api/vendors", tags=["Vendors"])
def list_vendors():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM vendors ORDER BY vendor_id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/audit", tags=["Audit"])
def audit_log(limit: int = 50):
    return get_recent_audit(limit=limit)


@app.get("/api/traces", tags=["Traces"])
def list_traces(limit: int = 50):
    """Recent agent runs — the Agent Activity view. Model tier isn't stored per
    row (it's a fixed fact of which agent ran, not a per-call variable), so the
    frontend derives it from agent_id."""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT t.id, t.agent_id, t.timestamp, t.user_input, t.retrieved_chunks, t.latency_ms, "
            "t.input_tokens, t.output_tokens, t.error, d.id AS decision_id "
            "FROM traces t LEFT JOIN decision_reviews d ON d.trace_id = t.id "
            "ORDER BY t.timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["retrieved_chunk_count"] = len(json.loads(d["retrieved_chunks"] or "[]"))
            del d["retrieved_chunks"]
            result.append(d)
        return result
    finally:
        conn.close()


# Reason codes that warrant attention regardless of dollar value — matches
# Procurement Policy Manual Section 9's compliance/fraud indicators plus the
# vendor-qualification failures. Not in this map = "low" (routine escalations
# like a plain DOA threshold breach still need review, just aren't urgent).
_HIGH_SEVERITY_REASON_CODES = {
    "DUPLICATE_INVOICE_SUSPECTED", "SPLIT_PO_PATTERN",
    "VENDOR_NOT_APPROVED", "UNAUTHORIZED_VENDOR",
}
_MEDIUM_SEVERITY_REASON_CODES = {
    "EXCEEDS_DOA_THRESHOLD", "PRICE_MISMATCH", "QTY_MISMATCH", "VENDOR_CERT_EXPIRED",
}
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _severity(reason_code: str) -> str:
    if reason_code in _HIGH_SEVERITY_REASON_CODES:
        return "high"
    if reason_code in _MEDIUM_SEVERITY_REASON_CODES:
        return "medium"
    return "low"


@app.get("/api/notifications", tags=["Notifications"])
def get_notifications():
    """Aggregates what actually needs a human's attention: pending reviews
    (ranked by severity, not just recency) and any pending decision whose
    cited policy/DOA version has since been superseded. Read-only — computing
    drift here never writes a policy_drift_flags row; that stays an explicit
    action on the decision detail page."""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, decision_type, entity_ref, proposed_at, reason_code, "
            "policy_version_id, doa_version_id FROM decision_reviews "
            "WHERE decision IS NULL AND auto_cleared=0 ORDER BY proposed_at ASC"
        ).fetchall()

        policy_row = get_active_version(conn, "procurement_policy_manual")
        doa_row = get_active_version(conn, "doa_matrix")
        current_policy_id = policy_row["id"] if policy_row else None
        current_doa_id = doa_row["id"] if doa_row else None

        pending = []
        drifted_ids = []
        for r in rows:
            d = {
                "id": r["id"], "decision_type": r["decision_type"], "entity_ref": r["entity_ref"],
                "proposed_at": r["proposed_at"], "reason_code": r["reason_code"],
                "severity": _severity(r["reason_code"]),
            }
            pending.append(d)
            if r["policy_version_id"] != current_policy_id or r["doa_version_id"] != current_doa_id:
                drifted_ids.append(r["id"])

        pending.sort(key=lambda d: (_SEVERITY_ORDER[d["severity"]], d["proposed_at"]))

        return {
            "pending_count": len(pending),
            "high_severity_count": sum(1 for p in pending if p["severity"] == "high"),
            "pending": pending[:10],
            "drifted_decision_ids": drifted_ids,
        }
    finally:
        conn.close()


@app.get("/health", tags=["System"])
def health_check() -> dict:
    return {"status": "ok", "service": "ProcureOps", "version": "1.0.0"}


@app.get("/", tags=["System"])
def root() -> dict:
    return {"message": "ProcureOps API — synthetic procurement governance demo", "docs": "/docs", "health": "/health"}
