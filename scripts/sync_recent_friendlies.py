"""
Create the first-stage recent friendlies cache.

source provider: API-Football / API-Sports
source endpoint: fixtures
target competition: Friendlies / International Friendlies
target date range: 2025-01-01 to match day

First-stage note:
This script intentionally does not guess endpoint parameters or fabricate match
results. It creates an empty cache with explicit meta.warning until a verified
API-Football fixtures sync is implemented.
"""

import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")


def load_cache(name, default=None):
    path = os.path.join(CACHE_DIR, name)
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(name, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_wc2026_teams():
    schedule = load_cache("wc2026_schedule.json", {}) or {}
    teams = set()
    for group_teams in (schedule.get("groups") or {}).values():
        teams.update(group_teams)
    return sorted(teams)


def main():
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    api_key = os.getenv("APIFOOTBALL_API_KEY", "")
    teams = get_wc2026_teams()

    # TODO: Implement verified API-Football fixtures requests.
    # Required fields:
    # fixture.id, fixture.date, league.name, league.id, teams.home.name,
    # teams.away.name, goals.home, goals.away, score.fulltime.home,
    # score.fulltime.away, venue.name, venue.city, fixture.status.short.
    data = {
        "meta": {
            "source": "empty",
            "source_provider": "API-Football",
            "source_endpoint": "fixtures",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "date_from": "2025-01-01",
            "date_to": "match_day",
            "teams_count": len(teams),
            "api_key_set": bool(api_key),
            "warning": "Real API-Football friendlies sync is not implemented yet. No match results were fabricated.",
        },
        "teams": {},
    }
    save_cache("recent_friendlies_2025_2026.json", data)
    print(f"[recent_friendlies] wrote empty cache for {len(teams)} teams")


if __name__ == "__main__":
    main()
