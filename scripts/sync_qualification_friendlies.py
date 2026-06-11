"""
Sync the model's preferred first-layer data:
- World Cup Qualification
- Recent Friendlies / International Friendlies

source provider: API-Football / API-Sports
source endpoint: fixtures

No fixture is fabricated. If the API plan or league/season combination returns
no rows, the script writes empty caches with an explicit warning.
"""

import json
import os
import time
from collections import defaultdict
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
    "海地": "Haiti", "苏格兰": "Scotland", "澳大利亚": "Australia", "土耳其": "Turkey",
    "德国": "Germany", "库拉索": "Curaçao", "荷兰": "Netherlands", "日本": "Japan",
    "科特迪瓦": "Ivory Coast", "厄瓜多尔": "Ecuador", "瑞典": "Sweden", "突尼斯": "Tunisia",
    "西班牙": "Spain", "佛得角": "Cabo Verde", "比利时": "Belgium", "埃及": "Egypt",
    "沙特阿拉伯": "Saudi Arabia", "乌拉圭": "Uruguay", "伊朗": "Iran", "新西兰": "New Zealand",
    "法国": "France", "塞内加尔": "Senegal", "伊拉克": "Iraq", "挪威": "Norway",
    "阿根廷": "Argentina", "阿尔及利亚": "Algeria", "奥地利": "Austria", "约旦": "Jordan",
    "葡萄牙": "Portugal", "刚果民主共和国": "DR Congo", "乌兹别克斯坦": "Uzbekistan",
    "哥伦比亚": "Colombia", "英格兰": "England", "克罗地亚": "Croatia", "加纳": "Ghana", "巴拿马": "Panama",
}

LEAGUE_SEASONS = [
    {"id": 32, "name": "World Cup - Qualification", "seasons": [2026]},
    {"id": 10, "name": "Friendlies", "seasons": [2025, 2026]},
]


def clean_api_warning(value):
    text = str(value)
    if "Free plans do not have access to this season" in text:
        return "当前 API-Football plan 不开放该赛季 fixtures"
    return text


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
    print(f"[sync] wrote {name}")


def wc_team_names():
    schedule = load_cache("wc2026_schedule.json", {}) or {}
    names = set()
    for teams in (schedule.get("groups") or {}).values():
        for name in teams:
            names.add(CN_TO_EN.get(name, name))
    return names


def api_get(endpoint, params, api_key):
    resp = requests.get(
        f"{API_BASE_URL}/{endpoint}",
        headers={"x-apisports-key": api_key},
        params=params,
        timeout=30,
        verify=False,
    )
    if resp.status_code == 429:
        raise RuntimeError("API-Football rate limit reached")
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        print(f"[sync] API warning for {endpoint} {params}: {data['errors']}")
        data["_warning"] = str(data["errors"])
    return data


def extract_fixture(row):
    fixture = row.get("fixture") or {}
    league = row.get("league") or {}
    teams = row.get("teams") or {}
    goals = row.get("goals") or {}
    status = fixture.get("status") or {}
    venue = fixture.get("venue") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    return {
        "id": fixture.get("id"),
        "date": fixture.get("date"),
        "league_id": league.get("id"),
        "league_name": league.get("name"),
        "season": league.get("season"),
        "round": league.get("round"),
        "home_team": home.get("name"),
        "away_team": away.get("name"),
        "home_id": home.get("id"),
        "away_id": away.get("id"),
        "home_goals": goals.get("home"),
        "away_goals": goals.get("away"),
        "status": status.get("long"),
        "status_short": status.get("short"),
        "venue": venue.get("name"),
        "venue_city": venue.get("city"),
        "source_provider": "API-Football",
        "source_endpoint": "fixtures",
    }


def fetch_priority_matches(api_key, teams):
    matches = []
    warnings = []
    for league in LEAGUE_SEASONS:
        for season in league["seasons"]:
            print(f"[sync] fetching league={league['id']} season={season}")
            try:
                data = api_get("fixtures", {"league": league["id"], "season": season}, api_key)
            except Exception as exc:
                warnings.append(f"{league['name']} {season}: {exc}")
                continue
            if data.get("_warning"):
                warnings.append(f"{league['name']} {season}: {clean_api_warning(data['_warning'])}")
            for row in data.get("response", []) or []:
                match = extract_fixture(row)
                if match["home_team"] in teams or match["away_team"] in teams:
                    matches.append(match)
            time.sleep(1.2)
    return matches, warnings


def result_for(goals_for, goals_against):
    if goals_for > goals_against:
        return "W"
    if goals_for == goals_against:
        return "D"
    return "L"


def build_profiles(matches):
    teams = {}
    for match in matches:
        if match.get("home_goals") is None or match.get("away_goals") is None:
            continue
        if match.get("status_short") not in {"FT", "AET", "PEN"} and match.get("status") != "Match Finished":
            continue
        for side, other in (("home", "away"), ("away", "home")):
            name = match.get(f"{side}_team")
            if not name:
                continue
            goals_for = match.get(f"{side}_goals") or 0
            goals_against = match.get(f"{other}_goals") or 0
            item = teams.setdefault(name, {
                "name": name,
                "games": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "form": [],
                "competitions": set(),
            })
            item["games"] += 1
            item["goals_for"] += goals_for
            item["goals_against"] += goals_against
            item["competitions"].add(match.get("league_name"))
            r = result_for(goals_for, goals_against)
            item["form"].append(r)
            if r == "W":
                item["wins"] += 1
            elif r == "D":
                item["draws"] += 1
            else:
                item["losses"] += 1

    profiles = []
    for item in teams.values():
        games = item["games"]
        if games <= 0:
            continue
        win_rate = item["wins"] / games * 100
        avg_gf = item["goals_for"] / games
        avg_ga = item["goals_against"] / games
        profiles.append({
            "name": item["name"],
            "games": games,
            "wins": item["wins"],
            "draws": item["draws"],
            "losses": item["losses"],
            "win_rate": round(win_rate, 1),
            "goals_for": item["goals_for"],
            "goals_against": item["goals_against"],
            "avg_goals_for": round(avg_gf, 2),
            "avg_goals_against": round(avg_ga, 2),
            "recent_form": "".join(item["form"][-6:]),
            "competitions": sorted(c for c in item["competitions"] if c),
            "attack_rating": min(95, round(40 + avg_gf * 18 + win_rate * 0.25)),
            "defense_rating": min(95, round(55 + (3 - avg_ga) * 12)),
            "midfield_rating": min(95, round(50 + win_rate * 0.3)),
            "source_provider": "API-Football",
            "source_endpoint": "fixtures",
        })
    profiles.sort(key=lambda row: (row["games"], row["win_rate"]), reverse=True)
    return profiles


def build_recent_friendlies_cache(matches, teams, warning):
    friendlies = [m for m in matches if m.get("league_id") == 10]
    by_team = defaultdict(lambda: {
        "matches": [],
        "summary": {
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "form_score": 0.0,
            "elo_delta": 0.0,
            "confidence": "none",
        }
    })
    for match in friendlies:
        if match.get("home_goals") is None or match.get("away_goals") is None:
            continue
        if match.get("status_short") not in {"FT", "AET", "PEN"} and match.get("status") != "Match Finished":
            continue
        for side, other in (("home", "away"), ("away", "home")):
            team = match.get(f"{side}_team")
            if team not in teams:
                continue
            gf = match.get(f"{side}_goals") or 0
            ga = match.get(f"{other}_goals") or 0
            result = result_for(gf, ga)
            row = by_team[team]
            row["matches"].append({
                "fixture_id": match.get("id"),
                "date": match.get("date"),
                "competition": match.get("league_name"),
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "team_side": side,
                "opponent": match.get(f"{other}_team"),
                "goals_for": gf,
                "goals_against": ga,
                "result": result,
                "goal_diff": gf - ga,
                "opponent_elo": None,
                "venue": match.get("venue") or match.get("venue_city"),
                "status": match.get("status_short"),
                "source": "API-Football",
            })
            s = row["summary"]
            s["matches"] += 1
            s["goals_for"] += gf
            s["goals_against"] += ga
            if result == "W":
                s["wins"] += 1
            elif result == "D":
                s["draws"] += 1
            else:
                s["losses"] += 1

    return {
        "meta": {
            "source": "API-Football" if friendlies else "empty",
            "source_provider": "API-Football",
            "source_endpoint": "fixtures",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "date_from": "2025-01-01",
            "date_to": "match_day",
            "teams_count": len(teams),
            "warning": warning or ("No 2025/2026 friendlies returned by API-Football for the current API plan." if not friendlies else ""),
        },
        "teams": by_team,
    }


def main():
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    api_key = os.getenv("APIFOOTBALL_API_KEY")
    force_sync = os.getenv("FORCE_APIFOOTBALL_SYNC", "").lower() == "true"
    teams = wc_team_names()
    existing_meta = load_cache("qualification_friendlies_meta.json", {}) or {}
    existing_matches = load_cache("qualification_friendlies_matches.json", []) or []
    if not force_sync and existing_meta.get("source_provider") == "local_csv" and existing_matches:
        print("[sync] local CSV qualification/friendlies cache exists; keeping it. Set FORCE_APIFOOTBALL_SYNC=true to override.")
        return
    if not force_sync and "不开放该赛季 fixtures" in str(existing_meta.get("warning", "")):
        print("[sync] current API-Football plan was already recorded as unavailable for target seasons; skipping. Set FORCE_APIFOOTBALL_SYNC=true to retry.")
        return
    meta = {
        "source_provider": "API-Football",
        "source_endpoint": "fixtures",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "leagues": LEAGUE_SEASONS,
        "teams_count": len(teams),
        "warning": "",
    }
    if not api_key:
        meta["warning"] = "APIFOOTBALL_API_KEY missing; wrote empty qualification/friendlies caches."
        save_cache("qualification_friendlies_matches.json", [])
        save_cache("qualification_friendlies_team_profiles.json", [])
        save_cache("qualification_friendlies_meta.json", meta)
        return

    matches, warnings = fetch_priority_matches(api_key, teams)
    profiles = build_profiles(matches)
    if warnings:
        meta["warning"] = " | ".join(warnings)
    if not matches:
        meta["warning"] = (meta["warning"] + "；" if meta["warning"] else "") + "API-Football 未返回可用的预选赛/热身赛 fixtures。"
        if existing_matches:
            print("[sync] API-Football returned no rows; preserving existing local cache.")
            meta["read_through_fallback"] = "preserved_existing_cache"
            save_cache("qualification_friendlies_meta.json", meta)
            return
    save_cache("qualification_friendlies_matches.json", matches)
    save_cache("qualification_friendlies_team_profiles.json", profiles)
    save_cache("qualification_friendlies_meta.json", meta)
    save_cache("recent_friendlies_2025_2026.json", build_recent_friendlies_cache(matches, teams, meta.get("warning", "")))
    print(f"[sync] matches={len(matches)} profiles={len(profiles)}")


if __name__ == "__main__":
    main()
