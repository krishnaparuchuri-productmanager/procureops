"""
routes/decisions.py — Maker-checker API for ProcureOps domain decisions.

This is the mechanism the ProcureOps architecture note calls out as new
relative to the AgentOps precedent: AgentOps' approval_requests table gates
*agent lifecycle* transitions; this table gates *domain decisions* (a specific
vendor recommendation, invoice verdict, or reorder proposal). See
docs/ARCHITECTURE.md.

Enforcement of proposed_by != reviewed_by happens in decide_review() below —
explicitly, by checking reviewed_by against the fixed AGENT_IDS set, not just
by assuming agent-id and human-identity namespaces never collide. This closes
a real gap found in agentops/backend/main.py's decide_approval(), which
claims (DECISIONS.md D-02) but never actually checks proposer != reviewer.

Vendor Selection and Invoice Verdict decisions are ALWAYS created with
decision=NULL (pending) and auto_cleared=0 — every code path for those two
decision_type values sets auto_cleared=0 unconditionally. Requisition Intake
and Reorder Action may auto-clear based on the specialist's own action field.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

try:
    from agents.requisition_intake import assess_requisition
    from agents.sourcing import assess_sourcing
    from agents.sourcing_strategy import assess_sourcing_strategy
    from agents.invoice_verification import assess_invoice
    from agents.inventory_management import assess_inventory
    from agents.contract_renewal import assess_contract_renewal
    from agents.autonomy_rules import evaluate_renewal
    from agents.winners_curse import flag_winners_curse
    from agents.common import AGENT_IDS, PROD_CRITICAL_DECISION_TYPES
    from observability.audit import write_audit
    from routes.policy import get_active_version, _connect as _policy_connect
    from retrieval import get_chunk_by_id
except ImportError:
    from backend.agents.requisition_intake import assess_requisition
    from backend.agents.sourcing import assess_sourcing
    from backend.agents.sourcing_strategy import assess_sourcing_strategy
    from backend.agents.invoice_verification import assess_invoice
    from backend.agents.inventory_management import assess_inventory
    from backend.agents.contract_renewal import assess_contract_renewal
    from backend.agents.autonomy_rules import evaluate_renewal
    from backend.agents.winners_curse import flag_winners_curse
    from backend.agents.common import AGENT_IDS, PROD_CRITICAL_DECISION_TYPES
    from backend.observability.audit import write_audit
    from backend.routes.policy import get_active_version, _connect as _policy_connect
    from backend.retrieval import get_chunk_by_id

router = APIRouter()

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_DIR / "db" / "procureops.db"

_HUMAN_REQUIRED_ACTIONS = {"escalate", "flag_missing_field", "flag_before_reorder",
                            "flag_reorder_quantity", "flag_ambiguous_data"}
_AUTO_CLEARABLE_ACTIONS = {"auto_clear", "no_action", "propose_reorder"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _log_trace(conn: sqlite3.Connection, agent_id: str, user_input: str, chunks: list[dict],
               model_output: dict, usage: dict) -> str:
    trace_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO traces (id, agent_id, timestamp, user_input, retrieved_chunks, "
        "prompt_version, model_output, latency_ms, input_tokens, output_tokens, error) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (trace_id, agent_id, _now(), user_input,
         json.dumps([c.get("chunk_id") for c in chunks]), "v1",
         json.dumps(model_output), usage.get("latency_ms"),
         usage.get("input_tokens"), usage.get("output_tokens"), None),
    )
    return trace_id


def _active_policy_ids(conn: sqlite3.Connection) -> tuple[str, str]:
    """Return (policy_version_id, doa_version_id) for the currently active versions.
    Raises 500 if either is missing — a decision can never be recorded without a
    policy snapshot to pin it to."""
    policy_row = get_active_version(conn, "procurement_policy_manual")
    doa_row = get_active_version(conn, "doa_matrix")
    if policy_row is None or doa_row is None:
        raise HTTPException(500, "No active policy_versions rows found — run the seed script first.")
    return policy_row["id"], doa_row["id"]


def _create_decision(
    conn: sqlite3.Connection, decision_type: str, entity_ref: str, proposed_by: str,
    proposal: dict, reason_code: str, auto_cleared: bool, trace_id: str,
) -> str:
    decision_id = str(uuid.uuid4())
    now = _now()
    policy_version_id, doa_version_id = _active_policy_ids(conn)

    # Structural guarantee: vendor_selection and invoice_verdict NEVER auto-clear,
    # regardless of what the caller passes in.
    if decision_type in PROD_CRITICAL_DECISION_TYPES:
        auto_cleared = False

    decision = "approved" if auto_cleared else None
    reviewed_by = "system:auto_clear" if auto_cleared else None
    reviewed_at = now if auto_cleared else None

    conn.execute(
        "INSERT INTO decision_reviews (id, decision_type, entity_ref, proposed_by, proposed_at, "
        "proposal, reason_code, policy_version_id, doa_version_id, auto_cleared, reviewed_by, "
        "reviewed_at, decision, checker_reason, trace_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (decision_id, decision_type, entity_ref, proposed_by, now, json.dumps(proposal),
         reason_code, policy_version_id, doa_version_id, int(auto_cleared), reviewed_by,
         reviewed_at, decision, None, trace_id),
    )

    write_audit(
        actor=proposed_by, action="DECISION_AUTO_CLEARED" if auto_cleared else "DECISION_PROPOSED",
        reason_code=reason_code, conn=conn,
        payload={"decision_id": decision_id, "decision_type": decision_type, "entity_ref": entity_ref,
                 "policy_version_id": policy_version_id, "doa_version_id": doa_version_id},
    )
    return decision_id


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class RequisitionRequest(BaseModel):
    raw_text: str
    requisition_id: Optional[str] = None


class SourcingRequest(BaseModel):
    sourcing_case_id: str
    description: str
    category: str
    quotes: list[dict]


class SourcingStrategyRequest(BaseModel):
    category: str
    spend_description: str
    budget_hint_usd: Optional[float] = None


class InvoiceRequest(BaseModel):
    match_id: str
    po: dict
    grn: dict
    invoice: dict
    prior_invoices: Optional[list[dict]] = None


class InventoryRequest(BaseModel):
    sku_record: dict


class ContractRenewalRequest(BaseModel):
    vendor_id: str
    category: str
    current_annual_value_usd: float
    proposed_annual_value_usd: float
    context_description: str
    renewal_id: Optional[str] = None


class ReviewDecision(BaseModel):
    reviewed_by: str
    decision: str  # "approved" | "rejected"
    checker_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# POST endpoints — run a specialist, create a decision_reviews row
# ---------------------------------------------------------------------------

@router.post("/decisions/requisition", status_code=201)
def propose_requisition(body: RequisitionRequest):
    assessment, chunks, usage = assess_requisition(body.raw_text)

    agent_id = AGENT_IDS["requisition_intake"]
    conn = _connect()
    try:
        with conn:
            trace_id = _log_trace(conn, agent_id, body.raw_text, chunks, assessment, usage)
            auto_cleared = assessment.get("action") == "auto_clear"
            decision_id = _create_decision(
                conn, "requisition_intake", body.requisition_id or str(uuid.uuid4()),
                agent_id, assessment, assessment.get("reason_code", "INSUFFICIENT_INFORMATION"),
                auto_cleared, trace_id,
            )
        return {"decision_id": decision_id, "assessment": assessment, "sources": chunks,
                "usage": usage, "agent_id": agent_id}
    finally:
        conn.close()


@router.post("/decisions/sourcing", status_code=201)
def propose_sourcing(body: SourcingRequest):
    # Computed FIRST, handed to the LLM as ground truth — same pattern as
    # contract_renewal's rule_result. Never something the model asserts on its own.
    winners_curse_flags = [
        flag_winners_curse(q["vendor_id"], body.category, q["unit_price"]) for q in body.quotes
    ]
    assessment, chunks, usage = assess_sourcing(body.description, body.category, body.quotes, winners_curse_flags)
    proposal = {**assessment, "winners_curse_flags": winners_curse_flags}

    agent_id = AGENT_IDS["sourcing"]
    conn = _connect()
    try:
        with conn:
            trace_id = _log_trace(conn, agent_id, body.description, chunks, proposal, usage)
            # auto_cleared is always False here — enforced again inside _create_decision
            # for decision_type='vendor_selection' regardless of what's passed.
            decision_id = _create_decision(
                conn, "vendor_selection", body.sourcing_case_id, agent_id, proposal,
                proposal.get("reason_code", "INSUFFICIENT_INFORMATION"), False, trace_id,
            )
        return {"decision_id": decision_id, "assessment": proposal, "sources": chunks,
                "usage": usage, "agent_id": agent_id}
    finally:
        conn.close()


@router.post("/decisions/sourcing-strategy", status_code=201)
def propose_sourcing_strategy(body: SourcingStrategyRequest):
    agent_id = AGENT_IDS["sourcing_strategy"]
    conn = _connect()
    try:
        # Candidate vendors come from a direct, deterministic DB query — not
        # RAG top-k — so the shortlist the agent reasons over is the complete
        # set of approved vendors in this category, never a lossy slice.
        candidates = [dict(r) for r in conn.execute(
            "SELECT vendor_id, name FROM vendors WHERE category=? AND approval_status='approved' "
            "ORDER BY vendor_id", (body.category,),
        ).fetchall()]

        assessment, chunks, usage = assess_sourcing_strategy(
            body.category, body.spend_description, candidates, body.budget_hint_usd,
        )

        category_slug = re.sub(r"[^A-Za-z0-9]+", "-", body.category).strip("-")[:20]
        entity_ref = f"STRAT-{category_slug}-{uuid.uuid4().hex[:8]}"
        with conn:
            trace_id = _log_trace(conn, agent_id, body.spend_description, chunks, assessment, usage)
            decision_id = _create_decision(
                conn, "sourcing_strategy", entity_ref, agent_id, assessment,
                assessment.get("reason_code", "INSUFFICIENT_INFORMATION"), False, trace_id,
            )
        return {"decision_id": decision_id, "assessment": assessment, "sources": chunks,
                "usage": usage, "agent_id": agent_id, "candidate_count": len(candidates)}
    finally:
        conn.close()


@router.post("/decisions/invoice", status_code=201)
def propose_invoice(body: InvoiceRequest):
    assessment, chunks, usage = assess_invoice(body.po, body.grn, body.invoice, body.prior_invoices)

    agent_id = AGENT_IDS["invoice_verification"]
    conn = _connect()
    try:
        with conn:
            trace_id = _log_trace(conn, agent_id, json.dumps(body.invoice), chunks, assessment, usage)
            decision_id = _create_decision(
                conn, "invoice_verdict", body.match_id, agent_id, assessment,
                assessment.get("reason_code", "INSUFFICIENT_INFORMATION"), False, trace_id,
            )
        return {"decision_id": decision_id, "assessment": assessment, "sources": chunks,
                "usage": usage, "agent_id": agent_id}
    finally:
        conn.close()


@router.post("/decisions/inventory", status_code=201)
def propose_inventory(body: InventoryRequest):
    assessment, chunks, usage = assess_inventory(body.sku_record)

    agent_id = AGENT_IDS["inventory_management"]
    sku = body.sku_record.get("sku", str(uuid.uuid4()))
    conn = _connect()
    try:
        with conn:
            trace_id = _log_trace(conn, agent_id, json.dumps(body.sku_record), chunks, assessment, usage)
            auto_cleared = assessment.get("action") in _AUTO_CLEARABLE_ACTIONS
            decision_id = _create_decision(
                conn, "reorder_action", sku, agent_id, assessment,
                assessment.get("reason_code", "INSUFFICIENT_INFORMATION"), auto_cleared, trace_id,
            )
        return {"decision_id": decision_id, "assessment": assessment, "sources": chunks,
                "usage": usage, "agent_id": agent_id}
    finally:
        conn.close()


@router.post("/decisions/contract-renewal", status_code=201)
def propose_contract_renewal(body: ContractRenewalRequest):
    agent_id = AGENT_IDS["contract_renewal"]
    conn = _connect()
    try:
        vendor_row = conn.execute(
            "SELECT * FROM vendors WHERE vendor_id=?", (body.vendor_id,)
        ).fetchone()
        if not vendor_row:
            raise HTTPException(404, f"Vendor '{body.vendor_id}' not found")
        vendor = dict(vendor_row)

        # The rule engine runs FIRST and is the sole source of auto_cleared —
        # the LLM below is handed this result so its commentary can reference
        # it, never the other way around. See agents/autonomy_rules.py.
        rule_result = evaluate_renewal(
            body.category, vendor, body.current_annual_value_usd, body.proposed_annual_value_usd,
        )
        assessment, chunks, usage = assess_contract_renewal(
            body.vendor_id, body.category, body.current_annual_value_usd,
            body.proposed_annual_value_usd, body.context_description, rule_result,
        )

        proposal = {**assessment, "rule_check": rule_result,
                    "current_annual_value_usd": body.current_annual_value_usd,
                    "proposed_annual_value_usd": body.proposed_annual_value_usd,
                    "vendor_id": body.vendor_id}
        entity_ref = body.renewal_id or f"RENEW-{body.vendor_id}-{uuid.uuid4().hex[:8]}"

        with conn:
            trace_id = _log_trace(conn, agent_id, body.context_description, chunks, proposal, usage)
            # auto_cleared comes exclusively from the rule engine's verdict —
            # never from anything the LLM specialist said about itself.
            decision_id = _create_decision(
                conn, "contract_renewal", entity_ref, agent_id, proposal,
                rule_result["reason_code"], rule_result["passed"], trace_id,
            )
        return {"decision_id": decision_id, "assessment": proposal, "sources": chunks,
                "usage": usage, "agent_id": agent_id}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET / review endpoints
# ---------------------------------------------------------------------------

@router.get("/decisions")
def list_decisions(pending_only: bool = Query(False), decision_type: Optional[str] = Query(None), limit: int = Query(100)):
    conn = _connect()
    try:
        clauses, params = [], []
        if pending_only:
            clauses.append("decision IS NULL")
        if decision_type:
            clauses.append("decision_type=?")
            params.append(decision_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM decision_reviews {where} ORDER BY proposed_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: str):
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM decision_reviews WHERE id=?", (decision_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Decision not found")
        result = dict(row)

        trace = None
        sources = []
        if row["trace_id"]:
            trace_row = conn.execute("SELECT * FROM traces WHERE id=?", (row["trace_id"],)).fetchone()
            if trace_row:
                trace = dict(trace_row)
                chunk_ids = json.loads(trace["retrieved_chunks"] or "[]")
                sources = [c for c in (get_chunk_by_id(cid) for cid in chunk_ids) if c is not None]

        result["trace"] = trace
        result["sources"] = sources
        return result
    finally:
        conn.close()


@router.post("/decisions/{decision_id}/review")
def decide_review(decision_id: str, body: ReviewDecision):
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(422, "decision must be 'approved' or 'rejected'")

    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM decision_reviews WHERE id=?", (decision_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Decision not found")
        if row["decision"] is not None:
            raise HTTPException(409, f"Decision already reviewed: {row['decision']}")
        if row["auto_cleared"]:
            raise HTTPException(409, "This decision auto-cleared and has no pending review to decide")

        # Real maker-checker enforcement: reviewed_by must be a human identity,
        # never one of the fixed agent ids, and never equal to the proposer.
        if body.reviewed_by in set(AGENT_IDS.values()) or body.reviewed_by == row["proposed_by"]:
            raise HTTPException(
                409,
                "reviewed_by must be a human identity distinct from the proposing agent — "
                "an agent cannot be its own checker.",
            )

        now = _now()
        with conn:
            conn.execute(
                "UPDATE decision_reviews SET decision=?, reviewed_by=?, reviewed_at=?, checker_reason=? WHERE id=?",
                (body.decision, body.reviewed_by, now, body.checker_reason, decision_id),
            )
        write_audit(
            actor=body.reviewed_by, action="DECISION_REVIEWED",
            payload={"decision_id": decision_id, "decision": body.decision,
                     "checker_reason": body.checker_reason, "proposed_by": row["proposed_by"]},
        )
        return {"decision_id": decision_id, "decision": body.decision}
    finally:
        conn.close()


@router.get("/decisions/{decision_id}/drift")
def check_drift(decision_id: str):
    """Compare this decision's cited policy/DOA versions against the currently
    active ones. Query-time computed flag — never mutates the decision row."""
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM decision_reviews WHERE id=?", (decision_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Decision not found")

        current_policy_id, current_doa_id = _active_policy_ids(conn)
        flags = []
        if row["policy_version_id"] != current_policy_id:
            flags.append({"doc_type": "procurement_policy_manual",
                          "cited_version_id": row["policy_version_id"], "current_version_id": current_policy_id})
        if row["doa_version_id"] != current_doa_id:
            flags.append({"doc_type": "doa_matrix",
                          "cited_version_id": row["doa_version_id"], "current_version_id": current_doa_id})

        if flags:
            now = _now()
            with conn:
                for f in flags:
                    conn.execute(
                        "INSERT INTO policy_drift_flags (id, decision_id, doc_type, cited_version_id, "
                        "current_version_id, detected_at) VALUES (?,?,?,?,?,?)",
                        (str(uuid.uuid4()), decision_id, f["doc_type"], f["cited_version_id"],
                         f["current_version_id"], now),
                    )
        return {"decision_id": decision_id, "drifted": bool(flags), "flags": flags}
    finally:
        conn.close()
