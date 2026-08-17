"""
agents/extraction.py — Free-text field extraction for zero-form intake.

Extends Ask ProcureOps beyond Requisition Intake (whose real input already is
free text) to Invoice Verification and Inventory Management: pulls whatever
structured fields are EXPLICITLY present in a free-text message, so the
handoff form arrives pre-filled instead of blank.

Deliberately does NOT extend to Sourcing/Quote Comparison — a vague sentence
cannot responsibly be turned into a set of competing vendor quotes with
dollar amounts; there is nothing in the text to extract that isn't already
handled by prefilling the description field. Fabricating quote rows from a
sentence would be exactly the failure mode this module exists to avoid.

Every field in both tool schemas is nullable and the system prompts are
explicit: extract only what's unambiguously stated, leave everything else
null. This is parsing, not reasoning — it runs on Haiku, and its output is
ALWAYS shown to a human as an editable, clearly-marked-as-extracted form
before anything is submitted. Nothing this module returns is ever submitted
automatically.
"""

from __future__ import annotations

from typing import Any

try:
    from llm_client import call_haiku
except ImportError:
    from backend.llm_client import call_haiku

_EXTRACTION_RULE = (
    "Extract a field ONLY if it is explicitly and unambiguously stated in the text. "
    "Never infer, estimate, guess, or default a dollar amount, quantity, or ID that isn't "
    "directly present. If a field isn't clearly stated, set it to the JSON value null — not the "
    "string \"null\", not \"N/A\", not \"<UNKNOWN>\", not an empty string. Use the literal null "
    "type. A null field is the correct, honest answer far more often than a guessed one."
)

# Defense in depth: some models occasionally emit a placeholder string instead
# of JSON null even when told not to. Anything that looks like a sentinel
# gets normalized to real None before this ever reaches a form — the whole
# point of this module is that a missing field reads as missing, not as a
# fake-looking value a human could mistake for something real.
_PLACEHOLDER_VALUES = {"<unknown>", "unknown", "n/a", "na", "null", "none", "tbd", ""}


def _normalize(fields: dict) -> dict:
    return {
        k: (None if isinstance(v, str) and v.strip().lower() in _PLACEHOLDER_VALUES else v)
        for k, v in fields.items()
    }

INVOICE_EXTRACTION_TOOL: dict[str, Any] = {
    "name": "extract_invoice_fields",
    "description": "Extract whatever three-way-match fields are explicitly present in free text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "po_id": {"type": ["string", "null"]},
            "vendor_id": {"type": ["string", "null"], "description": "Only if an exact vendor_id like 'V-001' is stated, not a vendor name."},
            "sku": {"type": ["string", "null"]},
            "po_qty": {"type": ["number", "null"]},
            "po_unit_price": {"type": ["number", "null"]},
            "invoice_id": {"type": ["string", "null"]},
            "invoice_qty": {"type": ["number", "null"]},
            "invoice_unit_price": {"type": ["number", "null"]},
        },
        "required": ["po_id", "vendor_id", "sku", "po_qty", "po_unit_price",
                      "invoice_id", "invoice_qty", "invoice_unit_price"],
    },
}

INVENTORY_EXTRACTION_TOOL: dict[str, Any] = {
    "name": "extract_inventory_fields",
    "description": "Extract whatever inventory fields are explicitly present in free text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sku": {"type": ["string", "null"]},
            "description": {"type": ["string", "null"]},
            "current_stock": {"type": ["number", "null"]},
            "reorder_point": {"type": ["number", "null"]},
            "preferred_vendor_id": {"type": ["string", "null"], "description": "Only an exact vendor_id like 'V-007', not a vendor name."},
        },
        "required": ["sku", "description", "current_stock", "reorder_point", "preferred_vendor_id"],
    },
}


def _extract(tool: dict, raw_text: str) -> dict[str, Any]:
    system_prompt = (
        f"You extract structured fields from a free-text procurement message. {_EXTRACTION_RULE} "
        f"Call {tool['name']} with your result. Do not call any other tool."
    )
    response = call_haiku(
        system_prompt=system_prompt, user_message=raw_text, max_tokens=400,
        tools=[tool], tool_choice={"type": "tool", "name": tool["name"]},
    )
    if not response.success:
        return {}
    return _normalize(response.parsed())


def extract_invoice_fields(raw_text: str) -> dict[str, Any]:
    return _extract(INVOICE_EXTRACTION_TOOL, raw_text)


def extract_inventory_fields(raw_text: str) -> dict[str, Any]:
    return _extract(INVENTORY_EXTRACTION_TOOL, raw_text)
