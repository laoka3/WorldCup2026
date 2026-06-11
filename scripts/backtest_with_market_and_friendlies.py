"""
First-stage backtest skeleton for market expectation and recent friendlies signals.

Compares:
- baseline
- baseline + recent_friendlies
- baseline + market_odds
- baseline + both

If coverage is insufficient, the output explicitly says so and does not claim
model improvement.
"""

import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")


def load_cache(name, default=None):
    path = os.path.join(CACHE_DIR, name)
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def coverage_count(data, key):
    if not isinstance(data, dict):
        return 0
    value = data.get(key, {})
    return len(value) if isinstance(value, dict) else 0


def empty_metrics(friendlies_coverage, market_coverage):
    warning = "coverage insufficient; do not claim model improvement."
    return {
        "accuracy": None,
        "log_loss": None,
        "brier_score": None,
        "draw_recall": None,
        "market_coverage": market_coverage,
        "friendlies_coverage": friendlies_coverage,
        "warning": warning,
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    friendlies = load_cache("recent_friendlies_2025_2026.json", {}) or {}
    odds = load_cache("market_odds.json", {}) or {}
    friendlies_coverage = coverage_count(friendlies, "teams")
    market_coverage = coverage_count(odds, "matches")
    report = {
        "name": "First-stage backtest skeleton with market expectation and recent friendlies",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coverage_note": "coverage insufficient; do not claim model improvement.",
        "variants": {
            "baseline": empty_metrics(friendlies_coverage, market_coverage),
            "baseline_plus_recent_friendlies": empty_metrics(friendlies_coverage, market_coverage),
            "baseline_plus_market_odds": empty_metrics(friendlies_coverage, market_coverage),
            "baseline_plus_both": empty_metrics(friendlies_coverage, market_coverage),
        },
    }
    path = os.path.join(OUTPUT_DIR, "backtest_with_market_and_friendlies_out.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[backtest] wrote skeleton report: {path}")


if __name__ == "__main__":
    main()
