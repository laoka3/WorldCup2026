"""
Import manual/exported market expectation signal data.

Primary input: data/imports/market_odds.csv
Optional JSON input: data/imports/market_odds.json

This module only prepares market expectation signals for probability
calibration. It does not provide advice.
"""

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
CSV_PATH = os.path.join(BASE_DIR, "data", "imports", "market_odds.csv")
JSON_PATH = os.path.join(BASE_DIR, "data", "imports", "market_odds.json")
MISSING_MARKET_WARNING = "No market_odds.csv found. Market odds signal disabled."


def save_cache(name, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(os.path.join(CACHE_DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[import-market] wrote {name}")


def safe_float(value):
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def match_key(row):
    return f"{row.get('home_team')}|{row.get('away_team')}|{str(row.get('match_date', ''))[:10]}"


def aggregate_rows(rows, source_provider, source_endpoint, warning=""):
    grouped = defaultdict(list)
    for row in rows:
        home = safe_float(row.get("home_odds"))
        draw = safe_float(row.get("draw_odds"))
        away = safe_float(row.get("away_odds"))
        if not row.get("home_team") or not row.get("away_team") or not row.get("match_date"):
            continue
        if not home or not draw or not away:
            continue
        grouped[match_key(row)].append({
            "name": row.get("bookmaker") or "unknown",
            "home": home,
            "draw": draw,
            "away": away,
            "market": row.get("market") or "1X2",
            "fetched_at": row.get("fetched_at"),
            "source_url": row.get("source_url"),
            "handicap_line": safe_float(row.get("handicap_line")),
            "handicap_home_odds": safe_float(row.get("handicap_home_odds")),
            "handicap_away_odds": safe_float(row.get("handicap_away_odds")),
            "over_under_line": safe_float(row.get("over_under_line")),
            "over_odds": safe_float(row.get("over_odds")),
            "under_odds": safe_float(row.get("under_odds")),
        })

    matches = {}
    for key, books in grouped.items():
        home_team, away_team, match_date = key.split("|", 2)
        avg_home = sum(b["home"] for b in books) / len(books)
        avg_draw = sum(b["draw"] for b in books) / len(books)
        avg_away = sum(b["away"] for b in books) / len(books)
        first = books[0]
        markets = {
            "1x2": {
                "average": {
                    "home": round(avg_home, 3),
                    "draw": round(avg_draw, 3),
                    "away": round(avg_away, 3),
                },
                "bookmakers": books,
            }
        }
        if first.get("handicap_line") is not None:
            markets["asian_handicap"] = {
                "line": first.get("handicap_line"),
                "home_odds": first.get("handicap_home_odds"),
                "away_odds": first.get("handicap_away_odds"),
            }
        if first.get("over_under_line") is not None:
            markets["over_under"] = {
                "line": first.get("over_under_line"),
                "over": first.get("over_odds"),
                "under": first.get("under_odds"),
            }
        matches[key] = {
            "fixture_id": None,
            "home_team": home_team,
            "away_team": away_team,
            "date": match_date,
            "fetched_at": first.get("fetched_at") or datetime.now(timezone.utc).isoformat(),
            "bookmaker_count": len(books),
            "source_provider": source_provider,
            "source_endpoint": source_endpoint,
            "markets": markets,
        }

    return {
        "meta": {
            "source": source_provider if matches else "empty",
            "source_provider": source_provider,
            "source_endpoint": source_endpoint,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "odds_format": "decimal",
            "markets": ["1X2", "Asian Handicap", "Over/Under"],
            "warning": warning if warning else ("" if matches else "No market expectation signal rows imported."),
            "enabled": bool(matches),
            "disclaimer": "盘口数据仅用于概率校准和市场预期参考，不构成投注建议。",
        },
        "matches": matches,
    }


def load_csv_rows():
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_json_rows():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    if isinstance(data, dict) and isinstance(data.get("matches"), dict):
        save_cache("market_odds.json", data)
        return None
    return []


def main():
    if os.path.exists(CSV_PATH):
        data = aggregate_rows(load_csv_rows(), "manual_csv", CSV_PATH)
    elif os.path.exists(JSON_PATH):
        rows = load_json_rows()
        if rows is None:
            print("[import-market] copied JSON cache to market_odds.json")
            return
        data = aggregate_rows(rows, "manual_json", JSON_PATH)
    else:
        data = aggregate_rows([], "manual_import", CSV_PATH, MISSING_MARKET_WARNING)
    save_cache("market_odds.json", data)


if __name__ == "__main__":
    main()
