"""
agents/router.py — Procurement Router.

Classifies incoming free-text requests by task_type and hands off to the
matching specialist, mirroring MediAssist's Router + Specialists pattern
(agentops/README.md "MediAssist Router Logic"). Runs on Haiku — classification
is a cheap, low-ambiguity task; the reasoning happens downstream in the
specialist the router delegates to.

    task_type                 -> specialist agent id                  model
    ────────────────────────────────────────────────────────────────────────
    "requisition"             -> procureops-requisition-intake        haiku-4-5
    "sourcing_strategy"       -> procureops-sourcing-strategy         sonnet-4-6
    "sourcing" / "quote"      -> procureops-sourcing                  sonnet-4-6
    "invoice"                 -> procureops-invoice-verification      sonnet-4-6
    "inventory" / "reorder"   -> procureops-inventory-management      haiku-4-5
    (ambiguous)               -> escalate=true, no specialist called
"""

from __future__ import annotations

from typing import Any

try:
    from llm_client import call_haiku
    from agents.common import AGENT_IDS
except ImportError:
    from backend.llm_client import call_haiku
    from backend.agents.common import AGENT_IDS

SYSTEM_PROMPT = """You are the ProcureOps Router. Your only job is to classify an incoming \
procurement request into exactly one task_type so it can be routed to the correct specialist.

Task types:
  - "requisition"        — a new purchase request that needs DOA / budget validation before a PO exists
  - "sourcing_strategy"  — a vague spend question with NO quotes yet ("what should we do about X costs",
                           "we need a plan for renewing Y") — needs a shortlist and evaluation approach
                           before any RFP is even issued
  - "sourcing"           — quotes already exist and need to be compared to choose a vendor
  - "invoice"            — reconciling a Purchase Order, Goods Receipt Note, and Invoice (three-way match)
  - "inventory"          — monitoring stock levels, proposing reorder points/quantities

The distinction between "sourcing_strategy" and "sourcing" matters: if the request mentions specific \
prices or numbered quotes from named vendors, it's "sourcing". If it's a question about a category \
or spend pattern with no quotes yet, it's "sourcing_strategy".

If the request does not clearly fit one of these five, set ambiguous=true and leave task_type null \
rather than guessing. Never invent a task_type outside this list."""

ROUTER_TOOL: dict[str, Any] = {
    "name": "route_request",
    "description": "Classify a procurement request into a task_type for routing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_type": {
                "type": ["string", "null"],
                "enum": ["requisition", "sourcing_strategy", "sourcing", "invoice", "inventory", None],
                "description": "The specialist queue this request belongs to, or null if ambiguous.",
            },
            "ambiguous": {
                "type": "boolean",
                "description": "True if the request does not clearly match one task_type.",
            },
            "rationale": {"type": "string", "description": "1 sentence explaining the classification."},
        },
        "required": ["task_type", "ambiguous", "rationale"],
    },
}

_SPECIALIST_BY_TASK_TYPE = {
    "requisition":       AGENT_IDS["requisition_intake"],
    "sourcing_strategy": AGENT_IDS["sourcing_strategy"],
    "sourcing":          AGENT_IDS["sourcing"],
    "invoice":           AGENT_IDS["invoice_verification"],
    "inventory":         AGENT_IDS["inventory_management"],
}


def route(user_input: str) -> dict[str, Any]:
    """Classify user_input and return {task_type, specialist_agent_id, ambiguous, rationale}."""
    response = call_haiku(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_input,
        max_tokens=300,
        tools=[ROUTER_TOOL],
        tool_choice={"type": "tool", "name": "route_request"},
    )

    if not response.success:
        return {
            "task_type": None, "specialist_agent_id": None, "ambiguous": True,
            "rationale": f"Router call failed: {response.error}",
        }

    parsed = response.parsed()
    task_type = parsed.get("task_type")
    return {
        "task_type": task_type,
        "specialist_agent_id": _SPECIALIST_BY_TASK_TYPE.get(task_type),
        "ambiguous": bool(parsed.get("ambiguous", task_type is None)),
        "rationale": parsed.get("rationale", ""),
    }
