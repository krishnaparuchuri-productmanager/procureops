"""
agents/sourcing_strategy.py — Sourcing Strategy specialist (Sonnet).

Sits upstream of agents/sourcing.py: that agent compares quotes that already
exist, this one helps produce the RFP in the first place — takes a vague
spend question and a category, and proposes a vendor shortlist, weighted
evaluation criteria, and a single- vs multi-source recommendation. Like
sourcing.py, this is a RECOMMENDATION only; it never selects a vendor or
commits spend, and every proposal it produces is human-gated (see
agents/common.py PROD_CRITICAL_DECISION_TYPES) even though it's one step
further from money actually leaving the company.
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

SYSTEM_PROMPT = f"""You are the ProcureOps Sourcing Strategy specialist. You take a category and a \
description of a spend need — often vague, before any quotes exist — and propose a sourcing \
strategy. You RECOMMEND; you never select a vendor or commit spend. Every proposal you produce goes \
to a human before an actual RFP is issued.

## Rules
- shortlist must be drawn ONLY from the candidate vendors supplied in the context below — never \
invent a vendor. If a supplied candidate has a compliance issue (expired certification, not \
approved) per the vendor master context, you may still list them but must set a risk flag \
explaining why, rather than silently omitting or silently including them.
- evaluation_criteria must be weighted percentages that sum to 100, appropriate to the category — \
e.g. total landed cost typically dominates for commoditized categories, while lead time and \
quality history matter more for specialized or capital-intensive categories.
- sourcing_approach: recommend "single_source" only when there's a clear reason (e.g. only one \
qualified candidate, or a strong incumbent-performance case) — otherwise "multi_source" is the \
default for anything meeting the competitive-bidding threshold in the supplied policy context.
- competitive_bidding_required: true if the estimated spend is at or above the policy's competitive \
bidding threshold; if no estimate was supplied, say so explicitly in the rationale rather than \
guessing a number.

## Auction mechanism (only when sourcing_approach is "multi_source" — set mechanism to \
"not_applicable" with a one-line rationale for single_source)
Recommend how the bidding event itself should be structured, from three real mechanisms:
- sealed_bid: every vendor submits one confidential bid; simplest, preserves vendor relationships \
(no public price war), and is the safer default when quality/differentiation matters as much as \
price. Its weakness: bidders have to guess how aggressive to be, which is exactly what invites a \
winner's-curse-style lowball (see the separate, code-computed check on actual submitted quotes).
- english_reverse: an open, live descending-price auction where vendors see the current best bid \
and can undercut it. Drives price down hardest and works well for commoditized, well-specified \
categories (e.g. raw materials, freight, standardized supplies) with enough qualified bidders (3+) \
for real competitive pressure — but the public price-war dynamic can strain vendor relationships and \
tends to increase winner's-curse risk (bidders chase the number in the moment, not their true cost).
- vickrey: sealed second-price auction — every vendor bids privately, but the winner pays what the \
second-best bidder offered. This is the mechanism most resistant to winner's curse: a bidder's best \
strategy is to bid their true cost rather than guess how low they need to go, because underbidding \
doesn't change what they'd pay if they win. Best suited to higher-stakes awards where getting an \
honest cost signal matters more than the simplicity of sealed_bid or the price pressure of \
english_reverse — and least familiar to vendors, so expect some pushback on Vickrey.
Base the recommendation on what's actually in front of you: how many qualified candidates exist \
(too few makes english_reverse pointless — there's no real competitive pressure), whether the \
category reads as commoditized/standardized vs. specialized/relationship-sensitive, and the deal's \
stakes. Every mechanism has a real tradeoff versus the other two — state it, don't just pick one.
- reason_code must be exactly one of: {", ".join(REASON_CODES)}.

Call submit_sourcing_strategy with your structured output. Do not call any other tool."""

SOURCING_STRATEGY_TOOL: dict[str, Any] = {
    "name": "submit_sourcing_strategy",
    "description": "Submit a structured sourcing strategy recommendation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "shortlist": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "vendor_id": {"type": "string"},
                        "rationale": {"type": "string"},
                        "risk_flags": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["vendor_id", "rationale", "risk_flags"],
                },
            },
            "evaluation_criteria": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "criterion": {"type": "string"},
                        "weight_pct": {"type": "number"},
                    },
                    "required": ["criterion", "weight_pct"],
                },
            },
            "sourcing_approach": {"type": "string", "enum": ["single_source", "multi_source"]},
            "approach_rationale": {"type": "string"},
            "competitive_bidding_required": {"type": "boolean"},
            "auction_recommendation": {
                "type": "object",
                "properties": {
                    "mechanism": {"type": "string", "enum": ["sealed_bid", "english_reverse", "vickrey", "not_applicable"]},
                    "rationale": {"type": "string"},
                    "tradeoffs": {
                        "type": "array", "items": {"type": "string"},
                        "description": "What's given up by not choosing each of the other two mechanisms.",
                    },
                },
                "required": ["mechanism", "rationale", "tradeoffs"],
            },
            "reason_code": {"type": "string", "enum": REASON_CODES},
            "rationale": {"type": "string"},
            "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
        },
        "required": ["shortlist", "evaluation_criteria", "sourcing_approach", "approach_rationale",
                      "competitive_bidding_required", "auction_recommendation",
                      "reason_code", "rationale", "confidence"],
    },
}


def assess_sourcing_strategy(
    category: str, spend_description: str, candidate_vendors: list[dict], budget_hint_usd: float | None = None,
) -> tuple[dict[str, Any], list[dict], dict[str, Any]]:
    """Run the Sourcing Strategy pipeline. candidate_vendors is the structured
    vendor-master shortlist for this category, queried by the route handler
    (not the agent itself — agents stay DB-free, routes own persistence).
    Returns (strategy_dict, retrieved_chunks, usage). Never auto-clears."""
    policy_chunks = search_docs(
        f"{category} competitive bidding vendor qualification threshold", top_k=3,
        corpus="procurement_policy_manual",
    )
    vendor_chunks = []
    for v in candidate_vendors:
        vendor_chunks += vendor_profile_chunks(v["vendor_id"], known_id=True)
    chunks = policy_chunks + vendor_chunks

    context = "\n\n".join([
        format_chunks(policy_chunks, "Procurement Policy Manual — relevant sections"),
        format_chunks(vendor_chunks, "Vendor Master — candidate vendor profiles"),
    ])
    budget_line = f"Estimated budget: ${budget_hint_usd:,.2f}\n" if budget_hint_usd is not None else "Estimated budget: not provided\n"
    candidate_lines = "\n".join(f"- vendor_id: {v['vendor_id']}  (name: {v['name']})" for v in candidate_vendors)
    user_message = (
        f"## Sourcing Strategy Request\nCategory: {category}\n{budget_line}"
        f"Spend description: {spend_description}\n\n"
        f"## Candidate Vendors (from Approved Vendor Master, category={category})\n"
        f"{len(candidate_vendors)} qualified candidate(s) available for this category.\n"
        f"IMPORTANT: when you reference a vendor, use only the exact vendor_id value shown below "
        f"(e.g. \"V-001\"), never the name or a combined string.\n{candidate_lines}\n\n{context}"
    )

    response = call_sonnet(
        system_prompt=SYSTEM_PROMPT, user_message=user_message, max_tokens=1600,
        tools=[SOURCING_STRATEGY_TOOL],
        tool_choice={"type": "tool", "name": "submit_sourcing_strategy"},
    )

    if not response.success:
        return safe_escalate_fallback({
            "shortlist": [], "evaluation_criteria": [], "sourcing_approach": "multi_source",
            "approach_rationale": "N/A - system error", "competitive_bidding_required": True,
            "auction_recommendation": {"mechanism": "not_applicable", "rationale": "N/A - system error", "tradeoffs": []},
        }), chunks, usage_dict(SONNET_MODEL, response)

    return response.parsed(), chunks, usage_dict(SONNET_MODEL, response)
