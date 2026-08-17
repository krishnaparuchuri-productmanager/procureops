"""
agents/invoice_verification.py — Invoice Verification specialist (Sonnet).

Performs a three-way match (PO vs GRN vs Invoice), classifies discrepancies
by type since each routes to a different resolution path, and produces a
verdict. Like sourcing.py, every proposal here becomes a decision_reviews row
of type "invoice_verdict" with decision=NULL — prod-critical, human-gated,
no auto-clear path.
"""

from __future__ import annotations

from typing import Any

try:
    from llm_client import call_sonnet, SONNET_MODEL
    from retrieval import search_docs
    from agents.common import REASON_CODES, format_chunks, safe_escalate_fallback, vendor_profile_chunks, usage_dict
except ImportError:
    from backend.llm_client import call_sonnet, SONNET_MODEL
    from backend.retrieval import search_docs
    from backend.agents.common import REASON_CODES, format_chunks, safe_escalate_fallback, vendor_profile_chunks, usage_dict

SYSTEM_PROMPT = f"""You are the ProcureOps Invoice Verification specialist. You perform a \
three-way match between a Purchase Order, a Goods Receipt Note, and an Invoice, and produce a \
VERDICT — you never approve payment yourself; every verdict you produce goes to a human checker.

## Rules
- Reconciliation tolerance is 2% on unit price and quantity, per the supplied policy context. A \
variance within 2% is discrepancy_type="none" and action="approve" — do not escalate within-tolerance \
variance; over-escalating is scored against you exactly like under-escalating a real discrepancy.
- Classify any out-of-tolerance discrepancy into exactly ONE of: "quantity_mismatch" (received/invoiced \
qty differs from PO qty beyond tolerance — state whether it's under- or over-delivery), \
"price_mismatch" (invoiced unit price, or an unexplained additional charge like freight not on the \
original PO, differs from the PO beyond tolerance), or "unauthorized_vendor" (the invoicing vendor \
does not match the PO vendor, or is not on the Approved Vendor Master). Misclassifying the type is a \
control failure, not a minor error, because it sends the case down the wrong resolution path.
- Separately, check for duplicate_invoice_suspected: same PO number, vendor, and amount (within 1%) \
appearing more than once. This can co-occur with a clean three-way match on the individual invoice \
— check it independently, don't skip it just because the match itself is clean.
- action is always "escalate" for any discrepancy or suspected duplicate; only a fully clean, \
within-tolerance match gets action="approve".
- resolution_next_steps must give concrete next steps appropriate to the discrepancy type (who to \
contact, what to verify) — a generic "investigate further" is not acceptable.
- reason_code must be exactly one of: {", ".join(REASON_CODES)}.

Call submit_invoice_verdict with your structured output. Do not call any other tool."""

INVOICE_TOOL: dict[str, Any] = {
    "name": "submit_invoice_verdict",
    "description": "Submit a structured three-way match verdict.",
    "input_schema": {
        "type": "object",
        "properties": {
            "discrepancy_type": {
                "type": "string",
                "enum": ["none", "quantity_mismatch", "price_mismatch", "unauthorized_vendor"],
            },
            "variance_pct": {"type": ["number", "null"], "description": "Computed variance percentage, if applicable."},
            "duplicate_invoice_suspected": {"type": "boolean"},
            "action": {"type": "string", "enum": ["approve", "escalate"]},
            "reason_code": {"type": "string", "enum": REASON_CODES},
            "resolution_next_steps": {"type": "string", "description": "Concrete next steps for the discrepancy type found."},
            "rationale": {"type": "string"},
            "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
        },
        "required": ["discrepancy_type", "variance_pct", "duplicate_invoice_suspected",
                      "action", "reason_code", "resolution_next_steps", "rationale", "confidence"],
    },
}


def assess_invoice(po: dict, grn: dict, invoice: dict, prior_invoices: list[dict] | None = None) -> tuple[dict[str, Any], list[dict]]:
    """Run the Invoice Verification pipeline. Returns (verdict_dict, retrieved_chunks). Never auto-clears."""
    policy_chunks = search_docs("three-way match tolerance duplicate invoice unauthorized vendor", top_k=3, corpus="procurement_policy_manual")
    # Full profile for both the PO's vendor and the invoice's vendor (known
    # vendor_ids) — these can legitimately differ, which is exactly the
    # unauthorized_vendor case this specialist has to catch, so both need
    # full grounding, not a single top-k chunk each.
    vendor_ids = {v for v in (invoice.get("vendor_id"), po.get("vendor_id")) if v}
    vendor_chunks = []
    for vid in vendor_ids:
        vendor_chunks += vendor_profile_chunks(vid, known_id=True)
    chunks = policy_chunks + vendor_chunks

    context = "\n\n".join([
        format_chunks(policy_chunks, "Procurement Policy Manual — relevant sections"),
        format_chunks(vendor_chunks, "Vendor Master — PO and invoice vendor profiles"),
    ])
    prior_block = f"\n\n## Prior Invoices Against This PO\n{prior_invoices}" if prior_invoices else ""
    user_message = (
        f"## Purchase Order\n{po}\n\n## Goods Receipt Note\n{grn}\n\n## Invoice\n{invoice}"
        f"{prior_block}\n\n{context}"
    )

    response = call_sonnet(
        system_prompt=SYSTEM_PROMPT, user_message=user_message, max_tokens=900,
        tools=[INVOICE_TOOL],
        tool_choice={"type": "tool", "name": "submit_invoice_verdict"},
    )

    if not response.success:
        return safe_escalate_fallback({
            "discrepancy_type": "unauthorized_vendor", "variance_pct": None,
            "duplicate_invoice_suspected": False,
            "resolution_next_steps": "Manual review required due to a system error.",
        }), chunks, usage_dict(SONNET_MODEL, response)

    return response.parsed(), chunks, usage_dict(SONNET_MODEL, response)
