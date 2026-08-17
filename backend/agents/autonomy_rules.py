"""
agents/autonomy_rules.py — Deterministic auto-approval rule engine for
Contract Renewal. Not an LLM agent, and deliberately so: this is the one
place in the platform where a decision genuinely auto-clears with real money
attached, so the yes/no has to be code, evaluated against numbers a company
set on purpose (agents/autonomy_policy table), not a model's judgment call
about whether an outcome "seems fine."

agents/contract_renewal.py (the LLM specialist) explains and contextualizes
a proposed renewal. This module decides, separately and afterward, whether
that renewal qualifies for auto-clear. The two are never the same function
call, and the route wiring them together (routes/decisions.py) always uses
THIS module's verdict for decision_reviews.auto_cleared -- never the LLM's
own opinion of itself.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_DIR / "db" / "procureops.db"


def get_autonomy_policy(category: str, db_path: Path | None = None) -> dict[str, Any] | None:
    conn = sqlite3.connect(db_path or _DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM autonomy_policy WHERE category=?", (category,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def evaluate_renewal(
    category: str, vendor_row: dict[str, Any], current_annual_value_usd: float,
    proposed_annual_value_usd: float, db_path: Path | None = None,
) -> dict[str, Any]:
    """Returns {passed: bool, checks: [...], reason_code, policy: {...} | None}.

    Every check runs and is reported, even after one fails -- a human
    reviewing a rejected auto-clear should see the full picture, not just
    the first thing that tripped it. A check is marked "not_applicable"
    (never "passed") when the vendor's data model doesn't carry that metric
    for its category (e.g. professional-services vendors have no
    defect_rate_pct) -- that's a structural gap in what's tracked, not
    evidence the renewal is safe, and it never counts toward "passed"."""
    policy = get_autonomy_policy(category, db_path)
    checks: list[dict[str, Any]] = []

    if policy is None:
        return {
            "passed": False, "reason_code": "INSUFFICIENT_INFORMATION", "policy": None,
            "checks": [{"name": "autonomy_policy_configured", "result": "failed",
                        "detail": f"No autonomy policy configured for category '{category}'."}],
        }

    price_increase_pct = (
        ((proposed_annual_value_usd - current_annual_value_usd) / current_annual_value_usd * 100)
        if current_annual_value_usd else None
    )

    def add(name: str, result: str, detail: str) -> None:
        checks.append({"name": name, "result": result, "detail": detail})

    # 1. Vendor approval status -- never configurable, never skippable.
    if vendor_row.get("approval_status") == "approved":
        add("vendor_approved", "passed", "Vendor is on the Approved Vendor Master.")
    else:
        add("vendor_approved", "failed", "Vendor is not on the Approved Vendor Master.")

    # 2. Renewal value ceiling.
    if proposed_annual_value_usd <= policy["max_renewal_value_usd"]:
        add("value_within_ceiling", "passed",
            f"${proposed_annual_value_usd:,.0f} <= ${policy['max_renewal_value_usd']:,.0f} ceiling.")
    else:
        add("value_within_ceiling", "failed",
            f"${proposed_annual_value_usd:,.0f} exceeds the ${policy['max_renewal_value_usd']:,.0f} ceiling.")

    # 3. Vendor service-quality threshold (skipped, not failed, if this
    # vendor's category never tracks on_time_pct).
    on_time = vendor_row.get("on_time_pct")
    if on_time is None:
        add("on_time_threshold", "not_applicable", "Vendor has no on_time_pct tracked.")
    elif on_time >= policy["min_vendor_on_time_pct"]:
        add("on_time_threshold", "passed", f"{on_time}% >= {policy['min_vendor_on_time_pct']}% required.")
    else:
        add("on_time_threshold", "failed", f"{on_time}% is below the {policy['min_vendor_on_time_pct']}% required.")

    # 4. Vendor quality-of-goods threshold (skipped if not tracked).
    defect = vendor_row.get("defect_rate_pct")
    if defect is None:
        add("defect_rate_threshold", "not_applicable", "Vendor has no defect_rate_pct tracked.")
    elif defect <= policy["max_vendor_defect_rate_pct"]:
        add("defect_rate_threshold", "passed", f"{defect}% <= {policy['max_vendor_defect_rate_pct']}% allowed.")
    else:
        add("defect_rate_threshold", "failed", f"{defect}% exceeds the {policy['max_vendor_defect_rate_pct']}% allowed.")

    # 5. Price increase ceiling.
    if price_increase_pct is None:
        add("price_increase_threshold", "failed", "Current contract value was not supplied -- cannot verify.")
    elif price_increase_pct <= policy["max_price_increase_pct"]:
        add("price_increase_threshold", "passed",
            f"{price_increase_pct:.1f}% <= {policy['max_price_increase_pct']}% allowed.")
    else:
        add("price_increase_threshold", "failed",
            f"{price_increase_pct:.1f}% exceeds the {policy['max_price_increase_pct']}% allowed.")

    passed = all(c["result"] != "failed" for c in checks)
    return {
        "passed": passed,
        "reason_code": "WITHIN_AUTO_APPROVAL_BAND" if passed else "EXCEEDS_AUTO_APPROVAL_BAND",
        "policy": policy,
        "checks": checks,
    }
