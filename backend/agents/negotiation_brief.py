"""
agents/negotiation_brief.py — Negotiation Brief specialist (Sonnet).

Pure decision support, not a decision. Given a vendor and a negotiation
context (a renewal coming up, a high-value sourcing event), produces a
strategy briefing for whichever human runs the actual negotiation, grounded
in real negotiation theory rather than generic advice:

  - BATNA (Best Alternative to a Negotiated Agreement) and a reservation price
  - a ZOPA estimate (Zone of Possible Agreement) reasoned from the vendor's
    own performance/tenure data, since we don't have their actual numbers
  - an integrative/"win-win" trade menu: non-price issues ranked by likely
    relative priority to each side, so the negotiator can trade something
    cheap for us for something valuable to them instead of pure price haggling
  - leverage factors drawn from the vendor's performance history and contract
    timing
  - target KPIs to carry into the room

Does NOT include a numeric win-probability/odds figure — that requires real
historical negotiation outcomes to be honest (see the synthetic negotiation
history dataset and odds layer built after this). Showing a precise-sounding
percentage without that data behind it would be exactly the kind of
ungrounded output this platform's governance thesis argues against.

Not gated through decision_reviews — there's no decision being proposed here,
just a briefing a human takes into a room they're going to run themselves.
Still traced (see routes/negotiation.py) for Agent Activity visibility.
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

SYSTEM_PROMPT = """You are the ProcureOps Negotiation Brief specialist. You prepare a strategy \
briefing for the human who will actually run a supplier negotiation — you never negotiate \
yourself and never propose a final number to accept. Ground your brief explicitly in negotiation \
theory, not generic advice:

## BATNA and reservation price
- batna: state our organization's realistic fallback if this negotiation fails or stalls — a \
named comparable vendor from the supplied context, the cost of a short-term extension, or the \
cost of switching. Never say "we have no alternative" without checking the supplied context first.
- reservation_price_usd: our walk-away point, if it can be reasoned from the supplied context \
(e.g. a comparable vendor's pricing, or a stated budget ceiling). Null if there's no basis for one.

## ZOPA (Zone of Possible Agreement)
- We don't have the vendor's actual cost structure, so reason an ESTIMATE from what's supplied: \
their tenure, performance trend, and how replaceable they appear to be. State this as a reasoned \
estimate, not a fact.

## Integrative ("win-win") trade menu — this is the most important section
- Propose 3-5 non-price issues (payment terms, contract length, SLA commitments, volume \
commitments, warranty) and for each, estimate OUR priority and the VENDOR's likely priority as \
High/Medium/Low, with a specific trade idea. The goal is finding issues where the two sides' \
priorities diverge — something low-cost for us to give that's high-value to them, in exchange for \
something we actually want. Do not just restate "negotiate a lower price" as a trade idea.

## Leverage factors
- Draw explicitly from the vendor's performance history and contract timing in the supplied \
context (e.g. a vendor with a declining performance trend, or one nearing contract expiry, has \
more reason to concede than a top performer with leverage of their own).

## What you must NOT do
- Do not state a numeric win-probability or "success rate" for any negotiation move — there is no \
historical data behind such a number yet, and inventing one would be worse than omitting it.
- Do not recommend a specific final price to accept — that's the negotiator's call, informed by \
this brief.

Call submit_negotiation_brief with your structured output. Do not call any other tool."""

NEGOTIATION_BRIEF_TOOL: dict[str, Any] = {
    "name": "submit_negotiation_brief",
    "description": "Submit a structured negotiation strategy brief.",
    "input_schema": {
        "type": "object",
        "properties": {
            "batna": {"type": "string"},
            "reservation_price_usd": {"type": ["number", "null"]},
            "zopa_estimate": {"type": "string"},
            "trade_menu": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue": {"type": "string"},
                        "our_priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                        "their_likely_priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                        "trade_idea": {"type": "string"},
                    },
                    "required": ["issue", "our_priority", "their_likely_priority", "trade_idea"],
                },
            },
            "leverage_factors": {"type": "array", "items": {"type": "string"}},
            "target_kpis": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"kpi": {"type": "string"}, "target": {"type": "string"}},
                    "required": ["kpi", "target"],
                },
            },
            "risk_notes": {"type": "string"},
            "rationale": {"type": "string"},
            "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
        },
        "required": ["batna", "reservation_price_usd", "zopa_estimate", "trade_menu",
                      "leverage_factors", "target_kpis", "risk_notes", "rationale", "confidence"],
    },
}


def assess_negotiation_brief(
    vendor_id: str, category: str, context_description: str, current_annual_value_usd: float | None = None,
) -> tuple[dict[str, Any], list[dict], dict[str, Any]]:
    """Returns (brief_dict, retrieved_chunks, usage)."""
    vendor_chunks = vendor_profile_chunks(vendor_id, known_id=True)
    terms_chunks = search_docs("payment terms warranty termination renewal", top_k=3, corpus="contract_terms")
    policy_chunks = search_docs(f"{category} vendor qualification competitive bidding", top_k=2, corpus="procurement_policy_manual")
    chunks = vendor_chunks + terms_chunks + policy_chunks

    context = "\n\n".join([
        format_chunks(vendor_chunks, "Vendor Master — this vendor's full profile"),
        format_chunks(terms_chunks, "Standard Contract Terms — relevant sections"),
        format_chunks(policy_chunks, "Procurement Policy Manual — relevant sections"),
    ])
    value_line = f"Current annual value: ${current_annual_value_usd:,.2f}\n" if current_annual_value_usd is not None else ""
    user_message = (
        f"## Negotiation Context\nVendor: {vendor_id}\nCategory: {category}\n{value_line}"
        f"Situation: {context_description}\n\n{context}"
    )

    response = call_sonnet(
        system_prompt=SYSTEM_PROMPT, user_message=user_message, max_tokens=1600,
        tools=[NEGOTIATION_BRIEF_TOOL],
        tool_choice={"type": "tool", "name": "submit_negotiation_brief"},
    )

    if not response.success:
        return safe_escalate_fallback({
            "batna": "N/A - system error", "reservation_price_usd": None,
            "zopa_estimate": "N/A - system error", "trade_menu": [], "leverage_factors": [],
            "target_kpis": [], "risk_notes": "System error - manual negotiation prep required.",
        }), chunks, usage_dict(SONNET_MODEL, response)

    return response.parsed(), chunks, usage_dict(SONNET_MODEL, response)
