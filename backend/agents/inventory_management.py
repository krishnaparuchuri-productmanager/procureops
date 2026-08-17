"""
agents/inventory_management.py — Inventory Management specialist (Haiku).

Monitors stock levels and proposes reorder points/quantities. This is a
threshold-based-escalation specialist (like requisition_intake), not
human-gated-every-time — but it must still surface vendor qualification
issues and reorder-quantity anomalies rather than blindly computing EOQ.
Recommendations are just that: Section 10 of the policy manual is explicit
that no agent may generate or transmit an actual PO from an inventory
proposal without going through the standard requisition/DOA workflow.
"""

from __future__ import annotations

from typing import Any

try:
    from llm_client import call_haiku
    from retrieval import search_docs
    from agents.common import REASON_CODES, format_chunks, safe_escalate_fallback
except ImportError:
    from backend.llm_client import call_haiku
    from backend.retrieval import search_docs
    from backend.agents.common import REASON_CODES, format_chunks, safe_escalate_fallback

SYSTEM_PROMPT = f"""You are the ProcureOps Inventory Management specialist. You monitor stock \
levels and PROPOSE reorder points and quantities. You never generate or transmit an actual \
purchase order — proposals only, which route through the standard requisition workflow.

## Rules
- action = "no_action" when current_stock is at or above reorder_point.
- action = "propose_reorder" when current_stock is below reorder_point, the preferred vendor is \
approved status with no expired certification, and the natural reorder quantity (covering \
lead-time demand plus reasonable safety stock) does not exceed 3x the trailing 90-day average \
consumption.
- action = "flag_before_reorder" when current_stock is below reorder_point but the preferred \
vendor's approval_status is not "approved" or a relevant certification (per the supplied vendor \
context) is expired — state the vendor issue explicitly before any quantity is proposed.
- action = "flag_reorder_quantity" when a specific requested_reorder_qty is supplied and it \
exceeds 3x the trailing 90-day average consumption without a stated rationale (e.g. known demand \
spike, supplier minimum order quantity) in the input — cite the exact multiple you computed.
- action = "flag_ambiguous_data" when avg_daily_usage is not a single clean number (e.g. a series \
with missing days or an unexplained outlier) — do not silently average over gaps or outliers.
- reason_code must be exactly one of: {", ".join(REASON_CODES)}.

Call submit_inventory_assessment with your structured output. Do not call any other tool."""

INVENTORY_TOOL: dict[str, Any] = {
    "name": "submit_inventory_assessment",
    "description": "Submit a structured inventory reorder assessment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["no_action", "propose_reorder", "flag_before_reorder", "flag_reorder_quantity", "flag_ambiguous_data"],
            },
            "proposed_reorder_qty": {"type": ["number", "null"]},
            "reason_code": {"type": "string", "enum": REASON_CODES},
            "rationale": {"type": "string"},
            "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
        },
        "required": ["action", "proposed_reorder_qty", "reason_code", "rationale", "confidence"],
    },
}


def assess_inventory(sku_record: dict, current_date: str = "2026-08-17") -> tuple[dict[str, Any], list[dict]]:
    """Run the Inventory Management pipeline. Returns (assessment_dict, retrieved_chunks)."""
    vendor_id = sku_record.get("preferred_vendor_id", "")
    vendor_chunks = search_docs(vendor_id, top_k=1, corpus="vendor_master")
    policy_chunks = search_docs("reorder quantity inventory policy", top_k=2, corpus="procurement_policy_manual")
    chunks = vendor_chunks + policy_chunks

    context = "\n\n".join([
        format_chunks(policy_chunks, "Procurement Policy Manual — relevant sections"),
        format_chunks(vendor_chunks, "Vendor Master — preferred vendor profile"),
    ])
    user_message = f"## SKU Record\nCurrent date: {current_date}\n{sku_record}\n\n{context}"

    response = call_haiku(
        system_prompt=SYSTEM_PROMPT, user_message=user_message, max_tokens=600,
        tools=[INVENTORY_TOOL],
        tool_choice={"type": "tool", "name": "submit_inventory_assessment"},
    )

    if not response.success:
        return safe_escalate_fallback({
            "action": "flag_ambiguous_data", "proposed_reorder_qty": None,
        }), chunks

    return response.parsed(), chunks
