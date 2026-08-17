"""
agents/odds.py — Win-probability / odds layer. Not an LLM agent — deliberately
pure SQL aggregation, no model call. This is the same principle already used
for auto-approval thresholds elsewhere in the platform: a number a negotiator
might rely on should be code-computed and auditable, not an LLM's guess.

Computes, per ask_type, how often that kind of ask has actually succeeded in
the past — vendor-specific when this vendor has enough history to be
meaningful, general-market (all vendors) otherwise, and always labeled which
one it is so a thin sample never masquerades as a confident number. This is
what agents/negotiation_brief.py explicitly declines to do on its own: that
module's LLM output never states a percentage, because until this table
existed there was no real data to ground one in.

accept_rate treats a "partial" outcome as half credit — a partial concession
is a real, if smaller, win for the ask, not a loss.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_DIR / "db" / "procureops.db"

# Below this many vendor-specific records, the vendor-level rate is shown
# but flagged low-confidence rather than presented as a solid number.
_MIN_CONFIDENT_SAMPLE = 3


def _rate(rows: list[sqlite3.Row]) -> tuple[float, int]:
    if not rows:
        return 0.0, 0
    weight = {"accepted": 1.0, "partial": 0.5, "rejected": 0.0}
    total = sum(weight[r["outcome"]] for r in rows)
    return round(total / len(rows) * 100, 1), len(rows)


def compute_odds(vendor_id: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Returns one entry per ask_type that has ANY historical data (vendor-
    specific or general-market), each with both rates so the negotiator can
    see how this vendor compares to the market, not just a single number."""
    conn = sqlite3.connect(db_path or _DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        ask_types = [r["ask_type"] for r in conn.execute(
            "SELECT DISTINCT ask_type FROM negotiation_history ORDER BY ask_type"
        ).fetchall()]

        result = []
        for ask_type in ask_types:
            vendor_rows = conn.execute(
                "SELECT outcome FROM negotiation_history WHERE vendor_id=? AND ask_type=?",
                (vendor_id, ask_type),
            ).fetchall()
            market_rows = conn.execute(
                "SELECT outcome FROM negotiation_history WHERE ask_type=?", (ask_type,)
            ).fetchall()

            vendor_rate, vendor_n = _rate(vendor_rows)
            market_rate, market_n = _rate(market_rows)

            if vendor_n == 0:
                continue  # nothing to say about this ask_type for this vendor at all

            result.append({
                "ask_type": ask_type,
                "vendor_accept_rate_pct": vendor_rate,
                "vendor_sample_size": vendor_n,
                "vendor_low_confidence": vendor_n < _MIN_CONFIDENT_SAMPLE,
                "market_accept_rate_pct": market_rate,
                "market_sample_size": market_n,
            })
        return result
    finally:
        conn.close()
