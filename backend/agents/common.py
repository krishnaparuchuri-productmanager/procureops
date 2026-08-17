"""
agents/common.py — Shared constants and helpers for all 5 ProcureOps agents.

Reason codes are the fixed enum defined in Procurement Policy Manual Section 11.
Every specialist's tool schema constrains reason_code to this list so the
value written to decision_reviews.reason_code and audit_log.reason_code is
always one of these, never free text.
"""

from __future__ import annotations

from typing import Any

try:
    from retrieval import search_docs, get_doc_chunks
except ImportError:
    from backend.retrieval import search_docs, get_doc_chunks

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
    "sourcing_strategy":   "procureops-sourcing-strategy",
    "invoice_verification": "procureops-invoice-verification",
    "inventory_management": "procureops-inventory-management",
    "negotiation_brief":   "procureops-negotiation-brief",
}

# All valid decision_reviews.decision_type values — validated here (Pydantic
# Literal at the API layer) rather than a DB CHECK constraint, since new
# specialists keep adding types and a CHECK would need a schema migration
# every time. See db/init_db.py::migrate_db for the one-time cleanup of the
# CHECK this replaced.
DECISION_TYPES = [
    "requisition_intake", "vendor_selection", "invoice_verdict",
    "reorder_action", "sourcing_strategy",
]

# Decision types that are ALWAYS human-gated — no auto_cleared path exists
# anywhere in the code for these, regardless of confidence or dollar value.
# sourcing_strategy joins vendor_selection/invoice_verdict here: it doesn't
# commit a specific vendor or dollar amount, but it directly shapes a real
# RFP a human will run, so the same no-autonomous-approval rule applies.
PROD_CRITICAL_DECISION_TYPES = {"vendor_selection", "invoice_verdict", "sourcing_strategy"}


def format_chunks(chunks: list[dict], label: str) -> str:
    """Render retrieved RAG chunks as a labelled context block for the user turn."""
    if not chunks:
        return f"## {label}\n(No relevant sections retrieved.)\n"
    lines = [f"## {label}"]
    for c in chunks:
        lines.append(f"\n### [{c['chunk_id']}] {c['section_title']} (source: {c['source_file']})")
        lines.append(c["text"])
    return "\n".join(lines)


def usage_dict(model: str, response: Any) -> dict[str, Any]:
    """Build the {model, input_tokens, output_tokens, latency_ms} shape stored
    alongside a trace, from an LLMResponse. Used for the Agent Activity view —
    a failed call still reports its (zeroed) usage rather than silently
    omitting it, since the point is showing what actually happened."""
    return {
        "model": model,
        "input_tokens": getattr(response, "input_tokens", 0),
        "output_tokens": getattr(response, "output_tokens", 0),
        "latency_ms": getattr(response, "latency_ms", 0),
    }


def vendor_profile_chunks(vendor_ref: str, known_id: bool = False) -> list[dict]:
    """Return the FULL profile (all sections) for one vendor, never a partial
    top-k slice. If known_id=True, vendor_ref is treated as an exact vendor_id
    prefix (e.g. "V-001") and matched directly. Otherwise vendor_ref is free
    text (e.g. a vendor name mentioned in a requisition) — the top TF-IDF hit
    identifies which vendor doc to fetch in full."""
    if known_id:
        chunks = get_doc_chunks(vendor_ref, corpus="vendor_master")
        if chunks:
            return chunks
    hits = search_docs(vendor_ref, top_k=1, corpus="vendor_master")
    if not hits:
        return []
    return get_doc_chunks(hits[0]["doc_id"], corpus="vendor_master")


def full_doa_matrix_chunks() -> list[dict]:
    """The DOA Matrix is short (~9 sections) and always relevant regardless of
    a requisition's wording — TF-IDF top-k against it was losing the exact
    category section to unrelated sections when the requisition's free text
    didn't share vocabulary with the category header. Returning the whole
    document sidesteps that instead of trying to out-guess the query."""
    return get_doc_chunks("doa_matrix", corpus="doa_matrix")


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
