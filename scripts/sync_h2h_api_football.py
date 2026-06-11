"""
Sync head-to-head records from API-Football for one pair.

source provider: API-Football / API-Sports
source endpoints:
- teams?search=<team>
- fixtures/headtohead?h2h=<home_id>-<away_id>

This is a structured API sync, not a web scraper. No H2H match is fabricated.
"""

import argparse
import json
import os
from datetime import datetime, timezone

import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
API_BASE_URL = "https://v3.football.api-sports.io"

CN_TO_EN = {
    "墨西哥": "Mexico", "南非": "South Africa", "韩国": "South Korea", "捷克": "Czechia",
    "加拿大": "Canada", "波黑": "Bosnia and Herzegovina", "美国": "USA", "巴拉圭": "Paraguay",
    "卡塔尔": "Qatar", "瑞士": "Switzerland", "巴西": "Brazil", "摩洛哥": "Morocco",
    "德国": "Germany", "法国": "France", "阿根廷": "Argentina", "英格兰": "England",
}


def normalize(name):
    return CN_TO_EN.get(name, name)


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
    print(f"[h2h] wrote {name}")


def api_get(endpoint, params, api_key):
    resp = requests.get(
        f"{API_BASE_URL}/{endpoint}",
        headers={"x-apisports-key": api_key},
        params=params,
        timeout=30,
        verify=False,
    )
    resp.raise_for_status()
    return resp.json()


def find_team_id(name, api_key):
    data = api_get("teams", {"search": normalize(name)}, api_key)
    rows = data.get("response", []) or []
    if not rows:
        return None
    exact = [row for row in rows if (row.get("team") or {}).get("name", "").lower() == normalize(name).lower()]
    picked = exact[0] if exact else rows[0]
    team = picked.get("team") or {}
    return {"id": team.get("id"), "name": team.get("name")}


def score_for_pair(row, team_a, team_b):
    teams = row.get("teams") or {}
    goals = row.get("goals") or {}
    home = (teams.get("home") or {}).get("name")
    away = (teams.get("away") or {}).get("name")
    hg = goals.get("home")
    ag = goals.get("away")
    if hg is None or ag is None:
        return None
    if home == team_a and away == team_b:
        return f"{hg}-{ag}"
    if home == team_b and away == team_a:
        return f"{ag}-{hg}"
    return None


def build_h2h_summary(home_name, away_name, rows):
    team_a = normalize(home_name)
    team_b = normalize(away_name)
    matches = []
    for row in rows:
        fixture = row.get("fixture") or {}
        league = row.get("league") or {}
        score = score_for_pair(row, team_a, team_b)
        if not score:
            continue
        matches.append({
            "date": fixture.get("date"),
            "competition": league.get("name"),
            "team_a": team_a,
            "team_b": team_b,
            "score_a_b": score,
            "source_provider": "API-Football",
            "source_endpoint": "fixtures/headtohead",
        })
    matches.sort(key=lambda item: item.get("date") or "")
    a_wins = draws = b_wins = total_goals = 0
    for match in matches:
        a_goals, b_goals = [int(x) for x in match["score_a_b"].split("-")]
        total_goals += a_goals + b_goals
        if a_goals > b_goals:
            a_wins += 1
        elif a_goals < b_goals:
            b_wins += 1
        else:
            draws += 1
    total = len(matches)
    return {
        "team_a": team_a,
        "team_b": team_b,
        "total": total,
        "a_wins": a_wins,
        "draws": draws,
        "b_wins": b_wins,
        "avg_goals": round(total_goals / total, 2) if total else 0,
        "last_5": matches[-5:],
        "all_matches": matches,
        "source_provider": "API-Football",
        "source_endpoint": "fixtures/headtohead",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    args = parser.parse_args()

    load_dotenv(os.path.join(BASE_DIR, ".env"))
    api_key = os.getenv("APIFOOTBALL_API_KEY")
    if not api_key:
        raise SystemExit("APIFOOTBALL_API_KEY is missing")

    home = find_team_id(args.home, api_key)
    away = find_team_id(args.away, api_key)
    if not home or not away or not home.get("id") or not away.get("id"):
        raise SystemExit(f"Could not resolve team ids: {args.home}={home}, {args.away}={away}")

    data = api_get("fixtures/headtohead", {"h2h": f"{home['id']}-{away['id']}"}, api_key)
    summary = build_h2h_summary(args.home, args.away, data.get("response", []) or [])
    h2h = load_cache("historical_h2h.json", {}) or {}
    h2h[f"{summary['team_a']} vs {summary['team_b']}"] = summary
    save_cache("historical_h2h.json", h2h)
    print(f"[h2h] {summary['team_a']} vs {summary['team_b']}: {summary['total']} matches")


if __name__ == "__main__":
    main()
