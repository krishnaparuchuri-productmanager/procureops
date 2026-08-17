"""
agents/common.py — Shared constants and helpers for all 5 ProcureOps agents.

Reason codes are the fixed enum defined in Procurement Policy Manual Section 11.
Every specialist's tool schema constrains reason_code to this list so the
value written to decision_reviews.reason_code and audit_log.reason_code is
always one of these, never free text.
"""

from __future__ import annotations

from typing import Any

REASON_CODES = [
    "WITHIN_DOA_THRESHOLD",
    "EXCEEDS_DOA_THRESHOLD",
    "VENDOR_CERT_EXPIRED",
    "VENDOR_NOT_APPROVED",
    "QTY_MISMATCH",
    "PRICE_MISMATCH",
    "UNAUTHORIZED_VENDOR",
    "DUPLICATE_INVOICE_SUSPECTED",
    "SPLIT_PO_PATTERN",
    "WITHIN_TOLERANCE",
    "MANUAL_OVERRIDE",
    "INSUFFICIENT_INFORMATION",
]

AGENT_IDS = {
    "router":              "procureops-router",
    "requisition_intake":  "procureops-requisition-intake",
    "sourcing":            "procureops-sourcing",
    "invoice_verification": "procureops-invoice-verification",
    "inventory_management": "procureops-inventory-management",
}

# Decision types that are ALWAYS human-gated — no auto_cleared path exists
# anywhere in the code for these two, regardless of confidence or dollar value.
PROD_CRITICAL_DECISION_TYPES = {"vendor_selection", "invoice_verdict"}


def format_chunks(chunks: list[dict], label: str) -> str:
    """Render retrieved RAG chunks as a labelled context block for the user turn."""
    if not chunks:
        return f"## {label}\n(No relevant sections retrieved.)\n"
    lines = [f"## {label}"]
    for c in chunks:
        lines.append(f"\n### [{c['chunk_id']}] {c['section_title']} (source: {c['source_file']})")
        lines.append(c["text"])
    return "\n".join(lines)


def safe_escalate_fallback(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Conservative fallback shared by every specialist: escalate, low confidence,
    INSUFFICIENT_INFORMATION. Never auto-approve on a system failure."""
    base = {
        "action": "escalate",
        "reason_code": "INSUFFICIENT_INFORMATION",
        "confidence": "Low",
        "rationale": (
            "The agent encountered an error and could not produce a reliable "
            "assessment. All failed or uncertain runs escalate by default and "
            "require manual review."
        ),
    }
    if extra:
        base.update(extra)
    return base
