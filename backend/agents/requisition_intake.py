"""
agents/requisition_intake.py — Requisition Intake specialist (Haiku).

Parses a free-text purchase request, validates it against the DOA matrix and
vendor qualification requirements, and either auto-clears it (threshold-based
escalation, not maker-checker-gated) or flags it for human review. This is one
of the two specialists that MAY auto-clear — see agents/common.py
PROD_CRITICAL_DECISION_TYPES, which requisition_intake is deliberately not in.
"""

from __future__ import annotations

from typing import Any

try:
    from llm_client import call_haiku
    from retrieval import search_docs
    from agents.common import REASON_CODES, format_chunks, safe_escalate_fallback, vendor_profile_chunks, full_doa_matrix_chunks
except ImportError:
    from backend.llm_client import call_haiku
    from backend.retrieval import search_docs
    from backend.agents.common import REASON_CODES, format_chunks, safe_escalate_fallback, vendor_profile_chunks, full_doa_matrix_chunks

SYSTEM_PROMPT = f"""You are the ProcureOps Requisition Intake specialist. You parse a free-text \
purchase request and validate it against the DOA Matrix and vendor qualification rules supplied \
in the context below. You do NOT approve or reject requisitions yourself — you classify what \
action is needed next.

## Rules
- Use ONLY the DOA thresholds, categories, and vendor status shown in the supplied context. Do \
not invent a threshold that is not explicitly present.
- action = "auto_clear" only when: the requisition amount is within the REQUESTER's own DOA \
ceiling for its category, the named vendor is "approved" status with no expired certification, \
and no required field (cost center, category, vendor) is missing.
- action = "escalate" when the amount exceeds the requester's own ceiling (cite the exact tier \
and threshold that applies), when the vendor is not approved or has an expired certification, or \
when the request matches a split-PO pattern (multiple recent requisitions to the same vendor \
whose combined total crosses a threshold).
- action = "flag_missing_field" when a required field (cost center, category, or vendor) cannot \
be determined from the request text.
- reason_code must be exactly one of: {", ".join(REASON_CODES)}.
- Never auto-clear a requisition to a vendor whose approval_status is not "approved", regardless \
of dollar amount.

Call submit_requisition_assessment with your structured output. Do not call any other tool."""

REQUISITION_TOOL: dict[str, Any] = {
    "name": "submit_requisition_assessment",
    "description": "Submit a structured requisition intake assessment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "Procurement category as named in the DOA Matrix."},
            "estimated_total_usd": {"type": "number", "description": "Parsed total dollar value of the requisition."},
            "vendor_id": {"type": ["string", "null"], "description": "Vendor ID if identifiable, else null."},
            "cost_center": {"type": ["string", "null"], "description": "Cost center / budget code if present, else null."},
            "action": {"type": "string", "enum": ["auto_clear", "escalate", "flag_missing_field"]},
            "doa_citation": {
                "type": "string",
                "description": "The exact DOA tier and threshold cited from the supplied context, e.g. 'IT Hardware & Software, Requester ceiling $1,000'.",
            },
            "reason_code": {"type": "string", "enum": REASON_CODES},
            "rationale": {"type": "string", "description": "2-3 sentences explaining the action."},
            "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
        },
        "required": ["category", "estimated_total_usd", "vendor_id", "cost_center",
                      "action", "doa_citation", "reason_code", "rationale", "confidence"],
    },
}


def assess_requisition(raw_text: str) -> tuple[dict[str, Any], list[dict]]:
    """Run the Requisition Intake pipeline. Returns (assessment_dict, retrieved_chunks)."""
    # DOA Matrix is fetched whole (see full_doa_matrix_chunks docstring) rather
    # than top-k'd against raw_text, which loses the right category section
    # when a requisition's wording (e.g. "laptops") shares no vocabulary with
    # the DOA table's category headers and dollar thresholds.
    doa_chunks = full_doa_matrix_chunks()
    policy_chunks = search_docs(raw_text, top_k=2, corpus="procurement_policy_manual")
    # Full vendor profile for whichever vendor the free text most resembles,
    # not a top-k slice that can lose the Certifications section to a
    # different vendor's Preamble competing in the same global ranking.
    vendor_chunks = vendor_profile_chunks(raw_text, known_id=False)
    chunks = doa_chunks + policy_chunks + vendor_chunks

    context = "\n\n".join([
        format_chunks(doa_chunks, "DOA Matrix — full document"),
        format_chunks(policy_chunks, "Procurement Policy Manual — relevant sections"),
        format_chunks(vendor_chunks, "Vendor Master — full profile of the most likely vendor mentioned"),
    ])
    user_message = f"## Requisition Request\n{raw_text}\n\n{context}"

    response = call_haiku(
        system_prompt=SYSTEM_PROMPT, user_message=user_message, max_tokens=700,
        tools=[REQUISITION_TOOL],
        tool_choice={"type": "tool", "name": "submit_requisition_assessment"},
    )

    if not response.success:
        return safe_escalate_fallback({
            "category": None, "estimated_total_usd": None, "vendor_id": None, "cost_center": None,
            "doa_citation": "N/A - system error",
        }), chunks

    return response.parsed(), chunks
