"""
main.py — FastAPI application entry point for ProcureOps.

Run with:
    uvicorn backend.main:app --reload          # from project root
    uvicorn main:app --reload --port 8000      # from backend/
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.init_db import init_db
from seed.demo_seed import seed_demo_data

from routes.decisions import router as decisions_router
from routes.policy import router as policy_router

try:
    from agents.router import route as route_request
    from observability.audit import get_recent_audit
except ImportError:
    from backend.agents.router import route as route_request
    from backend.observability.audit import get_recent_audit

import json
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent / "db" / "procureops.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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


@app.get("/health", tags=["System"])
def health_check() -> dict:
    return {"status": "ok", "service": "ProcureOps", "version": "1.0.0"}


@app.get("/", tags=["System"])
def root() -> dict:
    return {"message": "ProcureOps API — synthetic procurement governance demo", "docs": "/docs", "health": "/health"}
