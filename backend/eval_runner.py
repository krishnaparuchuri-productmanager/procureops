"""
eval_runner.py — End-to-end evaluation pipeline for ProcureOps.

Adapted from sop-deviation-review/backend/eval_runner.py: loads golden cases,
runs each through the real agent pipeline, scores every output with an
LLM-as-judge call across 8 rubric dimensions (0-10 each), and runs a parallel
naive baseline for comparison.

The baseline here is "always_auto_approve" rather than GMP's "always_escalate" —
deliberately inverted, because the dangerous default in procurement is
approving everything (false negative = same-day money out the door), not
escalating everything (false positive = a paperwork delay). A baseline that
always says yes should score very low on escalation_behavior and
compliance_fraud_flag, which is exactly what demonstrates the real agent's value.

Rubric (0-10 per dimension, matching the AgentOps-level convention found in
agentops/backend/seed.py EVAL_DIMENSIONS, not the older 4-dim/0-2 convention
used inside sop-deviation-review's own runner):
    policy_doa_citation, discrepancy_severity_classification,
    exception_resolution_quality, compliance_fraud_flag, escalation_behavior,
    groundedness, output_structure_clarity, vendor_neutrality

Pass gate: avg_score >= 6.0 AND escalation_behavior >= 7.0 (independent floor).

Usage:
    cd procureops/backend
    python eval_runner.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND_DIR))

from agents.requisition_intake import assess_requisition
from agents.sourcing import assess_sourcing
from agents.invoice_verification import assess_invoice
from agents.inventory_management import assess_inventory
from llm_client import call_sonnet

_DB_PATH = _BACKEND_DIR / "db" / "procureops.db"
_DATA_DIR = _BACKEND_DIR / "data" / "cases"
_GOLDEN_PATH = _DATA_DIR / "eval_golden_set.json"

DIMENSIONS = [
    "policy_doa_citation", "discrepancy_severity_classification",
    "exception_resolution_quality", "compliance_fraud_flag", "escalation_behavior",
    "groundedness", "output_structure_clarity", "vendor_neutrality",
]

AVG_SCORE_THRESHOLD = 6.0
ESCALATION_FLOOR = 7.0

# ---------------------------------------------------------------------------
# "always_auto_approve" baseline — never flags anything, regardless of input.
# ---------------------------------------------------------------------------
_BASELINE_OUTPUT_BY_SPECIALIST = {
    "requisition_intake": {"action": "auto_clear", "reason_code": "WITHIN_DOA_THRESHOLD",
                            "rationale": "Auto-approved without review.", "confidence": "High",
                            "doa_citation": "N/A - baseline does not check DOA"},
    "sourcing": {"recommended_vendor_id": None, "landed_costs": [],
                 "vendor_neutrality_note": "N/A - baseline does not compare vendors",
                 "competitive_bidding_gap": False, "doa_escalation_needed": False, "doa_tier": None,
                 "reason_code": "WITHIN_DOA_THRESHOLD", "rationale": "Auto-approved without review.",
                 "confidence": "High"},
    "invoice_verification": {"discrepancy_type": "none", "variance_pct": None,
                              "duplicate_invoice_suspected": False, "action": "approve",
                              "reason_code": "WITHIN_TOLERANCE", "resolution_next_steps": "None.",
                              "rationale": "Auto-approved without review.", "confidence": "High"},
    "inventory_management": {"action": "no_action", "proposed_reorder_qty": None,
                              "reason_code": "WITHIN_DOA_THRESHOLD", "rationale": "Auto-approved without review.",
                              "confidence": "High"},
}

# ---------------------------------------------------------------------------
# LLM-as-judge tool schema
# ---------------------------------------------------------------------------
_JUDGE_SYSTEM = """You are an expert evaluator of procurement AI agent outputs. Compare an actual \
model response to a golden-case reference (which describes the correct action, reason code, and \
key facts) and score 0-10 on each of 8 rubric dimensions. Score dimensions that are not applicable \
to this case as 10 (nothing to fault) rather than 0. Be strict and consistent about the dimensions \
that ARE applicable, per the case's golden_note. Call submit_eval_scores with your 8 scores and a \
brief explanation."""

_JUDGE_TOOL: dict[str, Any] = {
    "name": "submit_eval_scores",
    "description": "Submit numeric evaluation scores (0-10) across 8 rubric dimensions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "policy_doa_citation": {"type": "integer", "description": "Did the agent cite the correct policy/DOA threshold, by name, for this case? 10 = exact correct citation, 0 = wrong or fabricated citation."},
            "discrepancy_severity_classification": {"type": "integer", "description": "For invoice cases: correct discrepancy type (quantity/price/vendor). For others: correct severity of the finding. 10 = exact match to golden, 0 = wrong classification."},
            "exception_resolution_quality": {"type": "integer", "description": "Quality of proposed next steps when something needs resolution. 10 = concrete, actionable, correctly scoped. 0 = generic or missing."},
            "compliance_fraud_flag": {"type": "integer", "description": "Did the agent correctly flag (or correctly NOT flag) fraud/compliance indicators (duplicate invoice, split-PO, unapproved vendor, expired cert)? 10 = correct, 0 = missed a real flag or raised a false one."},
            "escalation_behavior": {"type": "integer", "description": "Did the agent escalate/not-escalate correctly per the golden case? This is the non-negotiable floor dimension - score strictly. 10 = correct call, 0 = wrong call (especially a missed true escalation)."},
            "groundedness": {"type": "integer", "description": "Is the agent's reasoning grounded in the actual PO/GRN/Invoice/policy data supplied, not hallucinated? 10 = fully grounded, 0 = fabricated facts."},
            "output_structure_clarity": {"type": "integer", "description": "Is the output well-structured, clear, and complete? 10 = clear and complete, 0 = vague or malformed."},
            "vendor_neutrality": {"type": "integer", "description": "For sourcing cases: were consistent criteria applied across vendors with no unexplained favoritism? Score 10 for non-sourcing cases where not applicable."},
            "notes": {"type": "string", "description": "1-2 sentences explaining the key scoring decisions."},
        },
        "required": DIMENSIONS + ["notes"],
    },
}


@dataclass
class EvalResult:
    case_id: str
    run_id: str
    model_tag: str
    scores: dict[str, int]
    avg_score: float
    overall_pass: int
    notes: str
    created_at: str


# ---------------------------------------------------------------------------
# Case loading — cross-reference the golden set against its source data files
# ---------------------------------------------------------------------------
def _load_json(name: str) -> Any:
    return json.loads((_DATA_DIR / name).read_text(encoding="utf-8"))


def load_golden_cases() -> list[dict]:
    golden = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    return golden["cases"]


def _find_source(records: list[dict], id_field: str, source_id: str) -> dict:
    for r in records:
        if r.get(id_field) == source_id:
            return r
    raise KeyError(f"source case {source_id} not found (id_field={id_field})")


def run_actual(case: dict) -> dict:
    """Run the real specialist for this golden case."""
    specialist = case["specialist"]
    source_id = case["source_case_id"]

    if specialist == "requisition_intake":
        reqs = _load_json("requisitions.json")
        src = _find_source(reqs, "requisition_id", source_id)
        assessment, _ = assess_requisition(src["raw_text"])
        return assessment

    if specialist == "sourcing":
        quotes = _load_json("quotes.json")
        src = _find_source(quotes, "sourcing_case_id", source_id)
        assessment, _ = assess_sourcing(src["description"], src["category"], src["quotes"])
        return assessment

    if specialist == "invoice_verification":
        matches = _load_json("three_way_match.json")
        src = _find_source(matches, "match_id", source_id)
        assessment, _ = assess_invoice(src["po"], src["grn"], src["invoice"])
        return assessment

    if specialist == "inventory_management":
        inv = _load_json("inventory.json")
        src = _find_source(inv, "sku", source_id)
        assessment, _ = assess_inventory(src)
        return assessment

    raise ValueError(f"Unknown specialist: {specialist}")


def _golden_context(case: dict) -> str:
    """Build the golden-reference text block the judge compares against."""
    specialist = case["specialist"]
    source_id = case["source_case_id"]
    loaders = {
        "requisition_intake": ("requisitions.json", "requisition_id"),
        "sourcing": ("quotes.json", "sourcing_case_id"),
        "invoice_verification": ("three_way_match.json", "match_id"),
        "inventory_management": ("inventory.json", "sku"),
    }
    filename, id_field = loaders[specialist]
    src = _find_source(_load_json(filename), id_field, source_id)
    return (
        f"Case: {case['case_id']} ({specialist})\n"
        f"Golden note: {case['golden_note']}\n"
        f"Primary dimensions tested: {case['primary_dimensions']}\n"
        f"Source case data: {json.dumps(src, indent=2)}"
    )


def _score_with_judge(case: dict, actual: dict) -> tuple[dict[str, int], str]:
    golden_context = _golden_context(case)
    judge_prompt = (
        f"## Golden Reference\n{golden_context}\n\n"
        f"## Actual Model Response\n{json.dumps(actual, indent=2)}\n\n"
        "Score the actual response on all 8 rubric dimensions by calling submit_eval_scores."
    )

    response = call_sonnet(
        system_prompt=_JUDGE_SYSTEM, user_message=judge_prompt, max_tokens=600,
        tools=[_JUDGE_TOOL], tool_choice={"type": "tool", "name": "submit_eval_scores"},
    )

    if not response.success:
        return {d: 5 for d in DIMENSIONS}, f"Judge call failed: {response.error}"

    try:
        raw = json.loads(response.text)
        scores = {d: max(0, min(10, int(raw.get(d, 5)))) for d in DIMENSIONS}
        return scores, str(raw.get("notes", ""))
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        return {d: 5 for d in DIMENSIONS}, f"Judge parse error: {exc}"


def run_model_eval(cases: list[dict], run_id: str, model_tag: str, created_at: str, verbose: bool = True) -> list[EvalResult]:
    results: list[EvalResult] = []
    for i, case in enumerate(cases, 1):
        if verbose:
            print(f"  [{model_tag[:10]:10}] {i:>2}/{len(cases)}  {case['case_id']} ...", end="", flush=True)
        t0 = time.monotonic()

        if model_tag == "actual":
            try:
                actual = run_actual(case)
            except Exception as exc:  # noqa: BLE001
                actual = {"error": f"{type(exc).__name__}: {exc}"}
        else:
            actual = dict(_BASELINE_OUTPUT_BY_SPECIALIST[case["specialist"]])

        scores, notes = _score_with_judge(case, actual)
        avg_score = round(sum(scores.values()) / len(scores), 2)
        overall_pass = 1 if (avg_score >= AVG_SCORE_THRESHOLD and scores["escalation_behavior"] >= ESCALATION_FLOOR) else 0

        elapsed = time.monotonic() - t0
        if verbose:
            flag = "PASS" if overall_pass else "FAIL"
            print(f"  avg={avg_score}/10 esc={scores['escalation_behavior']} {flag}  ({elapsed:.1f}s)")

        results.append(EvalResult(
            case_id=case["case_id"], run_id=run_id, model_tag=model_tag, scores=scores,
            avg_score=avg_score, overall_pass=overall_pass, notes=notes, created_at=created_at,
        ))
    return results


def save_results(results: list[EvalResult], db_path: Path = _DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            for r in results:
                conn.execute(
                    f"""INSERT INTO eval_results
                        (id, case_id, run_id, model_tag, {", ".join(DIMENSIONS)}, avg_score, overall_pass, notes, created_at)
                        VALUES ({", ".join(["?"] * (4 + len(DIMENSIONS) + 3))})""",
                    (str(uuid.uuid4()), r.case_id, r.run_id, r.model_tag,
                     *[r.scores[d] for d in DIMENSIONS],
                     r.avg_score, r.overall_pass, r.notes, r.created_at),
                )
    finally:
        conn.close()


def compute_summary(results: list[EvalResult]) -> dict[str, Any]:
    def avg(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    pass_count = sum(r.overall_pass for r in results)
    summary = {
        "cases": len(results),
        "pass_count": pass_count,
        "pass_rate_pct": round(pass_count / len(results) * 100, 1) if results else 0.0,
        "avg_score": avg([r.avg_score for r in results]),
    }
    for d in DIMENSIONS:
        summary[f"avg_{d}"] = avg([r.scores[d] for r in results])
    return summary


def print_summary(actual_results: list[EvalResult], baseline_results: list[EvalResult]) -> dict[str, Any]:
    a = compute_summary(actual_results)
    b = compute_summary(baseline_results)

    W = 62
    print("\n" + "=" * W)
    print("  PROCUREOPS EVAL RESULTS SUMMARY")
    print("=" * W)
    print(f"  {'Metric':<38} {'Actual':>9}  {'Baseline':>9}")
    print("-" * W)
    print(f"  {'Pass rate (%)':<38} {str(a['pass_rate_pct']):>9}  {str(b['pass_rate_pct']):>9}")
    print(f"  {'Avg score (/10, 8 dims)':<38} {str(a['avg_score']):>9}  {str(b['avg_score']):>9}")
    for d in DIMENSIONS:
        print(f"  {'  ' + d:<38} {str(a[f'avg_{d}']):>9}  {str(b[f'avg_{d}']):>9}")
    print("=" * W)

    print("\n  Per-case breakdown (actual model):")
    for r in actual_results:
        flag = "PASS" if r.overall_pass else "FAIL"
        print(f"  [{flag}] {r.case_id}  avg={r.avg_score}/10  escalation_behavior={r.scores['escalation_behavior']}/10")
    print()

    print(f"  Gate: avg_score >= {AVG_SCORE_THRESHOLD} AND escalation_behavior >= {ESCALATION_FLOOR}")
    gate_met = a["avg_score"] >= AVG_SCORE_THRESHOLD and a["avg_escalation_behavior"] >= ESCALATION_FLOOR
    print(f"  Promotion gate: {'MET' if gate_met else 'NOT MET'}\n")

    return {"actual": a, "baseline": b, "gate_met": gate_met}


def run_full_eval(verbose: bool = True) -> dict[str, Any]:
    t_start = time.monotonic()
    run_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if verbose:
        print(f"\n[eval] Starting run {run_id[:8]}...")

    cases = load_golden_cases()
    if verbose:
        print(f"[eval] Loaded {len(cases)} cases from {_GOLDEN_PATH.name}\n")

    if verbose:
        print("[eval] -- Actual agents (retrieval + LLM) --")
    actual_results = run_model_eval(cases, run_id, "actual", created_at, verbose)

    if verbose:
        print("\n[eval] -- always_auto_approve baseline --")
    baseline_results = run_model_eval(cases, run_id, "baseline_always_auto_approve", created_at, verbose)

    all_results = actual_results + baseline_results
    save_results(all_results)
    if verbose:
        print(f"\n[eval] Saved {len(all_results)} rows to eval_results table.")

    summary = print_summary(actual_results, baseline_results)
    summary["run_id"] = run_id
    summary["duration_s"] = round(time.monotonic() - t_start, 1)
    summary["total_rows"] = len(all_results)
    return summary


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    run_full_eval()
