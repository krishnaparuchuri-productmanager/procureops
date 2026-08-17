"""
routes/negotiation.py — Negotiation Brief endpoint.

Separate from routes/decisions.py deliberately: a brief isn't a decision,
there's nothing to approve or reject, so it never touches decision_reviews
or the maker-checker flow. Still logs a trace (same traces table, same
agent_id pattern as every other specialist) so it shows up in Agent
Activity and is auditable, without pretending it's a governance decision.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

try:
    from agents.negotiation_brief import assess_negotiation_brief
    from agents.common import AGENT_IDS
    from agents.odds import compute_odds
except ImportError:
    from backend.agents.negotiation_brief import assess_negotiation_brief
    from backend.agents.common import AGENT_IDS
    from backend.agents.odds import compute_odds

router = APIRouter()

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_DIR / "db" / "procureops.db"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class NegotiationBriefRequest(BaseModel):
    vendor_id: str
    category: str
    context_description: str
    current_annual_value_usd: Optional[float] = None


@router.post("/negotiation-brief", status_code=201)
def propose_negotiation_brief(body: NegotiationBriefRequest):
    agent_id = AGENT_IDS["negotiation_brief"]
    brief, chunks, usage = assess_negotiation_brief(
        body.vendor_id, body.category, body.context_description, body.current_annual_value_usd,
    )
    # Real computed statistics, not part of the LLM's output — see agents/odds.py.
    odds = compute_odds(body.vendor_id)

    conn = sqlite3.connect(_DB_PATH)
    try:
        trace_id = str(uuid.uuid4())
        with conn:
            conn.execute(
                "INSERT INTO traces (id, agent_id, timestamp, user_input, retrieved_chunks, "
                "prompt_version, model_output, latency_ms, input_tokens, output_tokens, error) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (trace_id, agent_id, _now(), body.context_description,
                 json.dumps([c.get("chunk_id") for c in chunks]), "v1",
                 json.dumps(brief), usage.get("latency_ms"),
                 usage.get("input_tokens"), usage.get("output_tokens"), None),
            )
        return {"trace_id": trace_id, "brief": brief, "sources": chunks, "usage": usage,
                "agent_id": agent_id, "odds": odds}
    finally:
        conn.close()
