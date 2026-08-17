"""
agents/winners_curse.py — Winner's-curse price check for Sourcing / Quote
Comparison. Not an LLM agent — same principle as agents/odds.py and
agents/autonomy_rules.py: a number that flags a quote as suspicious should be
code-computed from real history, never an LLM's impression that a price
"looks low."

The winner's curse: in competitive bidding, the winning bid is disproportion-
ately likely to be the one that most underestimated true cost — through
optimism, an error, or a strategic lowball that isn't sustainable once the
work starts (corner-cutting, mid-contract renegotiation, missed SLAs). The
check here is narrow and deliberately apples-to-apples: a vendor's CURRENT
quoted unit price compared only against THAT SAME vendor's own trailing
quotes for the same category (agents/data/cases/vendor_quote_history.json) —
never against a competing vendor's price, since unit-price scale differs
entirely by category and comparing across vendors would just be "vendor B is
cheaper than vendor A," not an anomaly signal.
"""

from __future__ import annotations

import sqlite3
import statistics
from pathlib import Path
from typing import Any

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_DIR / "db" / "procureops.db"

# Below this many historical quotes for this vendor+category, there isn't
# enough of a track record to call anything an anomaly.
_MIN_CONFIDENT_SAMPLE = 2

# A quote this far below the vendor's own historical average unit price is
# flagged for review — not disqualified, just surfaced.
_FLAG_THRESHOLD_PCT = -15.0


def flag_winners_curse(vendor_id: str, category: str, quoted_unit_price: float, db_path: Path | None = None) -> dict[str, Any]:
    conn = sqlite3.connect(db_path or _DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT unit_price FROM vendor_quote_history WHERE vendor_id=? AND category=?",
            (vendor_id, category),
        ).fetchall()
    finally:
        conn.close()

    sample_size = len(rows)
    if sample_size == 0:
        return {
            "vendor_id": vendor_id, "quoted_unit_price": quoted_unit_price,
            "historical_avg_unit_price": None, "sample_size": 0,
            "deviation_pct": None, "flagged": False, "low_confidence": True,
        }

    prices = [r["unit_price"] for r in rows]
    historical_avg = statistics.mean(prices)
    deviation_pct = round((quoted_unit_price - historical_avg) / historical_avg * 100, 1)
    low_confidence = sample_size < _MIN_CONFIDENT_SAMPLE
    flagged = (not low_confidence) and deviation_pct <= _FLAG_THRESHOLD_PCT

    return {
        "vendor_id": vendor_id, "quoted_unit_price": quoted_unit_price,
        "historical_avg_unit_price": round(historical_avg, 2), "sample_size": sample_size,
        "deviation_pct": deviation_pct, "flagged": flagged, "low_confidence": low_confidence,
    }
