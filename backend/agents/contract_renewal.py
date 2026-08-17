"""
agents/contract_renewal.py — Contract Renewal specialist (Sonnet).

Reviews a proposed renewal (a vendor, a category, the current and proposed
annual value) and writes the human-readable assessment: what changed, what
it means for this vendor's track record, and what a reviewer should look at
if the renewal does NOT auto-clear. It explains and contextualizes.

It does NOT decide whether the renewal auto-clears. That is exclusively
agents/autonomy_rules.py's job — plain code checked against the company's
own configured thresholds — and this module is handed that rule-engine
result as input so its commentary stays consistent with the actual outcome,
rather than the two disagreeing about the same renewal. The route handler
(routes/decisions.py) always writes decision_reviews.auto_cleared and
decision_reviews.reason_code from the rule engine's verdict, never from
anything in this module's output.
"""

from __future__ import annotations

from typing import Any

try:
    from llm_client import call_sonnet, SONNET_MODEL
    from retrieval import search_docs
    from agents.common import format_chunks, safe_escalate_fallback, vendor_profile_chunks, usage_dict
except ImportError:
    from backend.llm_client import call_sonnet, SONNET_MODEL
    from backend.retrieval import search_docs
    from backend.agents.common import format_chunks, safe_escalate_fallback, vendor_profile_chunks, usage_dict

SYSTEM_PROMPT = """You are the ProcureOps Contract Renewal specialist. You review a proposed vendor \
renewal — a category, a vendor, the current annual value, and the proposed new annual value — and \
write the assessment a human reviewer (or an audit trail, for renewals that auto-clear) will read.

You are given the outcome of a separate, deterministic rule check (bounded-autonomy thresholds this \
company has configured for this category) ALREADY COMPUTED before you run. Do not recompute or \
second-guess whether it passed or failed — treat it as ground truth about this specific renewal, and \
write your assessment around it:
- If it passed, explain WHY it's a low-risk renewal in plain terms (grounded in this vendor's actual \
performance figures and the terms context supplied) — this becomes the audit record for an \
auto-cleared decision, so it must stand on its own without a human's added narrative.
- If it failed, explain what specifically a human reviewer should focus on, referencing the failed \
check(s) directly rather than restating generic caution.

## Rules
- key_terms_assessment: comment on the proposed value change itself and any notable terms in the \
supplied Standard Contract Terms context relevant to a renewal (auto-renewal clauses, termination \
notice periods, price-escalation caps) — only what's grounded in the supplied context.
- risk_notes: vendor-specific risks drawn from the supplied performance data and rule-check detail, \
never generic boilerplate like "monitor performance."
- recommended_negotiation_points: 1-4 concrete points worth raising before signing, whether or not \
this auto-clears (e.g. even an auto-cleared renewal may be worth flagging a minor point for next cycle).
- Never state that a renewal is "approved" or "auto-approved" yourself — that determination has \
already been made by the rule check and is not yours to announce; describe it, don't decide it.

Call submit_contract_renewal_assessment with your structured output. Do not call any other tool."""

CONTRACT_RENEWAL_TOOL: dict[str, Any] = {
    "name": "submit_contract_renewal_assessment",
    "description": "Submit a structured contract renewal assessment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "key_terms_assessment": {"type": "string"},
            "risk_notes": {"type": "string"},
            "recommended_negotiation_points": {"type": "array", "items": {"type": "string"}},
            "rationale": {"type": "string"},
            "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
        },
        "required": ["key_terms_assessment", "risk_notes", "recommended_negotiation_points",
                      "rationale", "confidence"],
    },
}


def assess_contract_renewal(
    vendor_id: str, category: str, current_annual_value_usd: float, proposed_annual_value_usd: float,
    context_description: str, rule_result: dict[str, Any],
) -> tuple[dict[str, Any], list[dict], dict[str, Any]]:
    """Returns (assessment_dict, retrieved_chunks, usage). rule_result is the
    dict returned by agents.autonomy_rules.evaluate_renewal — already computed
    by the route handler before this runs."""
    vendor_chunks = vendor_profile_chunks(vendor_id, known_id=True)
    terms_chunks = search_docs("auto-renewal termination notice price escalation cap", top_k=3, corpus="contract_terms")
    chunks = vendor_chunks + terms_chunks

    context = "\n\n".join([
        format_chunks(vendor_chunks, "Vendor Master — this vendor's full profile"),
        format_chunks(terms_chunks, "Standard Contract Terms — relevant sections"),
    ])

    checks_lines = "\n".join(
        f"- {c['name']}: {c['result'].upper()} — {c['detail']}" for c in rule_result["checks"]
    )
    price_increase_pct = (
        (proposed_annual_value_usd - current_annual_value_usd) / current_annual_value_usd * 100
        if current_annual_value_usd else None
    )
    increase_line = f"{price_increase_pct:.1f}%" if price_increase_pct is not None else "n/a"

    user_message = (
        f"## Renewal Under Review\nVendor: {vendor_id}\nCategory: {category}\n"
        f"Current annual value: ${current_annual_value_usd:,.2f}\n"
        f"Proposed annual value: ${proposed_annual_value_usd:,.2f}  (change: {increase_line})\n"
        f"Context: {context_description}\n\n"
        f"## Bounded-Autonomy Rule Check Result (already computed — do not recompute)\n"
        f"Overall: {'PASSED — eligible for auto-clear' if rule_result['passed'] else 'FAILED — requires human review'}\n"
        f"{checks_lines}\n\n{context}"
    )

    response = call_sonnet(
        system_prompt=SYSTEM_PROMPT, user_message=user_message, max_tokens=1200,
        tools=[CONTRACT_RENEWAL_TOOL],
        tool_choice={"type": "tool", "name": "submit_contract_renewal_assessment"},
    )

    if not response.success:
        return safe_escalate_fallback({
            "key_terms_assessment": "N/A - system error", "risk_notes": "System error - manual review required.",
            "recommended_negotiation_points": [],
        }), chunks, usage_dict(SONNET_MODEL, response)

    return response.parsed(), chunks, usage_dict(SONNET_MODEL, response)
