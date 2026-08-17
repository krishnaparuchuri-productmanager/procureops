"""
agents/sourcing.py — Sourcing / Quote Comparison specialist (Sonnet).

Compares competing vendor quotes on total landed cost (unit price + tax +
freight + duty — never headline price alone), applies the same evaluation
criteria to every vendor, and RECOMMENDS but never selects. Every proposal
this specialist produces becomes a decision_reviews row of type
"vendor_selection" with decision=NULL — prod-critical, human-gated, no
auto-clear path exists in this module at all.
"""

from __future__ import annotations

from typing import Any

try:
    from llm_client import call_sonnet, SONNET_MODEL
    from retrieval import search_docs
    from agents.common import REASON_CODES, format_chunks, safe_escalate_fallback, vendor_profile_chunks, full_doa_matrix_chunks, usage_dict
except ImportError:
    from backend.llm_client import call_sonnet, SONNET_MODEL
    from backend.retrieval import search_docs
    from backend.agents.common import REASON_CODES, format_chunks, safe_escalate_fallback, vendor_profile_chunks, full_doa_matrix_chunks, usage_dict

SYSTEM_PROMPT = f"""You are the ProcureOps Sourcing / Quote Comparison specialist. You compare \
competing vendor quotes and RECOMMEND a vendor — you never select or approve one; every \
recommendation you produce goes to a human checker before any PO can be issued.

## Rules
- Compute total landed cost per vendor = (unit_price * qty) + tax + freight + duty. Rank on total \
landed cost, never on unit price alone.
- Before ranking, exclude any vendor whose approval_status is not "approved" or whose relevant \
certification (per the vendor master context) is expired as of the current date. State clearly \
which vendors were excluded and why — do not silently omit them.
- Apply IDENTICAL evaluation logic to every vendor in the comparison set. If you recommend a \
vendor that is not the lowest total landed cost among qualified vendors, you MUST state an \
explicit justification (e.g. lead time, quality history) in vendor_neutrality_note. Silent \
deviation from lowest qualified total landed cost is a policy violation you must never commit.
- If historical usage patterns are mentioned in the input and you notice the recommended vendor \
matches a vendor used repeatedly in prior cases despite not having the lowest total landed cost, \
explicitly call that out in vendor_neutrality_note rather than ignoring it.
- If the requisition's estimated total is at or above $10,000 and fewer than 3 quotes were \
supplied, set competitive_bidding_gap=true — this must be flagged, not treated as compliant.
- doa_escalation_needed / doa_tier: state whether the winning total exceeds the category's VP \
threshold from the supplied DOA context, requiring CFO/CEO approval — this is a SEPARATE finding \
from which vendor is recommended.
- You are given a Winner's-Curse Price Check per quote, ALREADY COMPUTED (each vendor's current \
unit price vs THAT SAME vendor's own historical average for this category — never compared across \
vendors). Do not recompute or second-guess it. If ANY quote is flagged, pricing_risk_notes MUST \
name which vendor(s) and explain what a flagged quote means for a reviewer: not disqualifying by \
itself, but a bid unusually far below what this vendor has historically charged can mean a pricing \
error, a loss-leader that gets renegotiated upward once work starts, or corner-cutting to hit the \
number — worth a direct conversation with the vendor before award, especially if you're \
recommending that vendor. If nothing was flagged, say so plainly rather than a generic "no concerns."
- reason_code must be exactly one of: {", ".join(REASON_CODES)}.

Call submit_sourcing_recommendation with your structured output. Do not call any other tool."""

SOURCING_TOOL: dict[str, Any] = {
    "name": "submit_sourcing_recommendation",
    "description": "Submit a structured vendor sourcing recommendation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "landed_costs": {
                "type": "array",
                "description": "Total landed cost computed for every quoted vendor, including excluded ones.",
                "items": {
                    "type": "object",
                    "properties": {
                        "vendor_id": {"type": "string"},
                        "total_landed_cost": {"type": "number"},
                        "excluded": {"type": "boolean"},
                        "exclusion_reason": {"type": ["string", "null"]},
                    },
                    "required": ["vendor_id", "total_landed_cost", "excluded", "exclusion_reason"],
                },
            },
            "recommended_vendor_id": {"type": ["string", "null"]},
            "vendor_neutrality_note": {
                "type": "string",
                "description": "Explicit justification if the recommendation isn't the lowest qualified total landed cost, or a statement that neutrality criteria were applied uniformly.",
            },
            "competitive_bidding_gap": {"type": "boolean"},
            "doa_escalation_needed": {"type": "boolean"},
            "doa_tier": {"type": ["string", "null"], "description": "e.g. 'VP' or 'CFO/CEO' if escalation is needed."},
            "pricing_risk_notes": {
                "type": "string",
                "description": "Address any winner's-curse-flagged quotes by vendor, or state plainly that none were flagged.",
            },
            "reason_code": {"type": "string", "enum": REASON_CODES},
            "rationale": {"type": "string"},
            "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
        },
        "required": ["landed_costs", "recommended_vendor_id", "vendor_neutrality_note",
                      "competitive_bidding_gap", "doa_escalation_needed", "doa_tier",
                      "pricing_risk_notes", "reason_code", "rationale", "confidence"],
    },
}


def assess_sourcing(
    description: str, category: str, quotes: list[dict], winners_curse_flags: list[dict],
    current_date: str = "2026-08-17",
) -> tuple[dict[str, Any], list[dict], dict[str, Any]]:
    """Run the Sourcing pipeline. winners_curse_flags is computed by the route
    handler BEFORE this runs (see agents/winners_curse.py) and handed in as
    ground truth, same pattern as agents/contract_renewal.py's rule_result.
    Returns (recommendation_dict, retrieved_chunks, usage). Never auto-clears."""
    policy_chunks = search_docs(f"{category} competitive bidding vendor neutrality", top_k=2, corpus="procurement_policy_manual")
    doa_chunks = full_doa_matrix_chunks()
    terms_chunks = search_docs("freight duty incoterms", top_k=2, corpus="contract_terms")
    vendor_ids = [q["vendor_id"] for q in quotes]
    vendor_chunks = []
    for vid in vendor_ids:
        # Full profile per quoted vendor (known vendor_id -> direct doc match),
        # not a single top-k chunk that can miss the Certifications section.
        vendor_chunks += vendor_profile_chunks(vid, known_id=True)
    chunks = policy_chunks + doa_chunks + terms_chunks + vendor_chunks

    context = "\n\n".join([
        format_chunks(policy_chunks, "Procurement Policy Manual — relevant sections"),
        format_chunks(doa_chunks, "DOA Matrix — full document"),
        format_chunks(terms_chunks, "Standard Contract Terms — relevant sections"),
        format_chunks(vendor_chunks, "Vendor Master — full profiles of every quoted vendor"),
    ])
    flag_lines = "\n".join(
        f"- {f['vendor_id']}: quoted ${f['quoted_unit_price']:,.2f}/unit vs this vendor's own "
        f"historical average ${f['historical_avg_unit_price']:,.2f}/unit "
        f"(n={f['sample_size']}{', low confidence' if f['low_confidence'] else ''}) "
        f"— {f['deviation_pct']}% deviation — {'FLAGGED' if f['flagged'] else 'not flagged'}"
        if f["historical_avg_unit_price"] is not None
        else f"- {f['vendor_id']}: no quote history on file for this category — nothing to compare against."
        for f in winners_curse_flags
    )
    user_message = (
        f"## Sourcing Case\nCategory: {category}\nDescription: {description}\n"
        f"Current date: {current_date}\n\n## Competing Quotes\n{quotes}\n\n"
        f"## Winner's-Curse Price Check (already computed — do not recompute)\n{flag_lines}\n\n{context}"
    )

    response = call_sonnet(
        system_prompt=SYSTEM_PROMPT, user_message=user_message, max_tokens=1200,
        tools=[SOURCING_TOOL],
        tool_choice={"type": "tool", "name": "submit_sourcing_recommendation"},
    )

    if not response.success:
        return safe_escalate_fallback({
            "landed_costs": [], "recommended_vendor_id": None,
            "vendor_neutrality_note": "N/A - system error", "competitive_bidding_gap": True,
            "doa_escalation_needed": True, "doa_tier": "CFO/CEO", "pricing_risk_notes": "N/A - system error",
        }), chunks, usage_dict(SONNET_MODEL, response)

    return response.parsed(), chunks, usage_dict(SONNET_MODEL, response)
