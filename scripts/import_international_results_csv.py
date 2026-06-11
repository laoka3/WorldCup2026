"""
Import local/public international football results CSV into model caches.

Input: data/imports/international_results.csv
Supported columns:
date, home_team, away_team, home_score, away_score, tournament, city, country, neutral

No rows are fabricated. Missing CSV produces empty caches with warnings.
"""

import csv
import json
import os
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
IMPORT_PATH = os.path.join(BASE_DIR, "data", "imports", "international_results.csv")
SOURCE_PROVIDER = "martj42/international_results"
SOURCE_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
DOWNLOAD_FAILURE_WARNING = "No local CSV found and automatic download failed. Please place international_results.csv under data/imports/."
RECENT_COVERAGE_WARNING = "The public CSV does not cover recent 2025/2026 friendlies or qualifiers. Recent form cache may be incomplete."

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


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(name, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(os.path.join(CACHE_DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[import-results] wrote {name}")


def download_csv_if_missing():
    if os.path.exists(IMPORT_PATH):
        return None, ""
    os.makedirs(os.path.dirname(IMPORT_PATH), exist_ok=True)
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "WorldCup2026DataImporter/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
        with open(IMPORT_PATH, "wb") as f:
            f.write(content)
        downloaded_at = datetime.now(timezone.utc).isoformat()
        print(f"[import-results] downloaded {SOURCE_URL} -> {IMPORT_PATH}")
        return downloaded_at, ""
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return None, f"{DOWNLOAD_FAILURE_WARNING} Detail: {exc}"


def parse_date(value):
    try:
        return datetime.fromisoformat((value or "").strip()[:10]).date()
    except ValueError:
        return None


def wc_team_names():
    names = set()
    canonical = set()
    teams_data = load_json(os.path.join(BASE_DIR, "data", "teams.json"), {}) or {}
    for team in teams_data.get("teams", []):
        if team.get("name"):
            names.add(team["name"])
            names.add(CN_TO_EN.get(team["name"], team["name"]))
    schedule = load_json(os.path.join(CACHE_DIR, "wc2026_schedule.json"), {}) or {}
    for group_teams in (schedule.get("groups") or {}).values():
        for name in group_teams:
            canonical.add(name)
            names.add(name)
            names.add(CN_TO_EN.get(name, name))
    return names, len(canonical) or len(names)


def is_qualification(tournament):
    text = (tournament or "").lower()
    return ("world cup" in text or "fifa world cup" in text) and any(k in text for k in ["qualification", "qualifier", "qualifying"])


def is_friendly(tournament):
    text = (tournament or "").lower()
    return any(k in text for k in ["friendly", "friendlies", "international friendly", "international friendlies"])


def to_match(row, imported_at, source_file):
    home_goals = int(row["home_score"])
    away_goals = int(row["away_score"])
    return {
        "id": f"local_csv:{row['date']}:{row['home_team']}:{row['away_team']}",
        "date": row["date"],
        "league_id": None,
        "league_name": row.get("tournament", ""),
        "season": row["date"][:4],
        "round": "",
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "home_id": None,
        "away_id": None,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "status": "Match Finished",
        "status_short": "FT",
        "venue": row.get("city", ""),
        "venue_city": row.get("city", ""),
        "country": row.get("country", ""),
        "neutral": row.get("neutral", ""),
        "source": "local_csv",
        "source_file": source_file,
        "imported_at": imported_at,
        "source_provider": SOURCE_PROVIDER,
        "source_endpoint": source_file,
        "source_url": SOURCE_URL,
    }


def has_final_score(row):
    try:
        int(row.get("home_score", ""))
        int(row.get("away_score", ""))
        return True
    except (TypeError, ValueError):
        return False


def result_for(goals_for, goals_against):
    if goals_for > goals_against:
        return "W"
    if goals_for == goals_against:
        return "D"
    return "L"


def build_profiles(matches):
    teams = {}
    for match in matches:
        for side, other in (("home", "away"), ("away", "home")):
            name = match[f"{side}_team"]
            goals_for = match[f"{side}_goals"]
            goals_against = match[f"{other}_goals"]
            item = teams.setdefault(name, {
                "name": name, "games": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0, "form": [], "competitions": set(),
            })
            item["games"] += 1
            item["goals_for"] += goals_for
            item["goals_against"] += goals_against
            item["competitions"].add(match["league_name"])
            result = result_for(goals_for, goals_against)
            item["form"].append(result)
            if result == "W":
                item["wins"] += 1
            elif result == "D":
                item["draws"] += 1
            else:
                item["losses"] += 1

    profiles = []
    for item in teams.values():
        games = item["games"]
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
            "competitions": sorted(item["competitions"]),
            "attack_rating": min(95, round(40 + avg_gf * 18 + win_rate * 0.25)),
            "defense_rating": min(95, round(55 + (3 - avg_ga) * 12)),
            "midfield_rating": min(95, round(50 + win_rate * 0.3)),
            "source_provider": SOURCE_PROVIDER,
            "source_endpoint": "data/imports/international_results.csv",
            "source_url": SOURCE_URL,
        })
    profiles.sort(key=lambda row: (row["games"], row["win_rate"]), reverse=True)
    return profiles


def build_friendlies_cache(friendlies, teams, imported_at, warning, meta):
    by_team = defaultdict(lambda: {
        "matches": [],
        "summary": {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "form_score": 0.0, "elo_delta": 0.0, "confidence": "none"},
    })
    for match in friendlies:
        for side, other in (("home", "away"), ("away", "home")):
            team = match[f"{side}_team"]
            if team not in teams:
                continue
            gf = match[f"{side}_goals"]
            ga = match[f"{other}_goals"]
            result = result_for(gf, ga)
            row = by_team[team]
            row["matches"].append({
                "fixture_id": match["id"],
                "date": match["date"],
                "competition": match["league_name"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "team_side": side,
                "opponent": match[f"{other}_team"],
                "goals_for": gf,
                "goals_against": ga,
                "result": result,
                "goal_diff": gf - ga,
                "opponent_elo": None,
                "venue": match.get("venue"),
                "status": "FT",
                "source": "local_csv",
                "source_file": IMPORT_PATH,
                "imported_at": imported_at,
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
            s["confidence"] = "csv"
    return {
        "meta": {
            "source": SOURCE_PROVIDER if friendlies else "empty",
            "source_provider": SOURCE_PROVIDER,
            "source_endpoint": IMPORT_PATH,
            "source_url": SOURCE_URL,
            "generated_at": imported_at,
            "downloaded_at": meta.get("downloaded_at"),
            "csv_min_date": meta.get("csv_min_date"),
            "csv_max_date": meta.get("csv_max_date"),
            "total_rows": meta.get("total_rows", 0),
            "matched_worldcup_teams": meta.get("matched_worldcup_teams", 0),
            "qualification_matches_count": meta.get("qualification_matches_count", 0),
            "friendlies_matches_count": meta.get("friendlies_matches_count", 0),
            "coverage_warning": meta.get("coverage_warning", ""),
            "date_from": "2025-01-01",
            "date_to": "match_day",
            "teams_count": meta.get("teams_count", len(teams)),
            "warning": warning,
        },
        "teams": by_team,
    }


def write_empty(imported_at, warning):
    meta = {
        "source": "empty",
        "source_provider": SOURCE_PROVIDER,
        "source_endpoint": IMPORT_PATH,
        "source_url": SOURCE_URL,
        "generated_at": imported_at,
        "downloaded_at": None,
        "csv_min_date": None,
        "csv_max_date": None,
        "total_rows": 0,
        "matched_worldcup_teams": 0,
        "qualification_matches_count": 0,
        "friendlies_matches_count": 0,
        "coverage_warning": "",
        "warning": warning,
    }
    save_cache("qualification_matches.json", {"meta": meta, "matches": []})
    save_cache("qualification_friendlies_matches.json", [])
    save_cache("qualification_friendlies_team_profiles.json", [])
    save_cache("qualification_friendlies_meta.json", meta)
    save_cache("recent_friendlies_2025_2026.json", {"meta": meta, "teams": {}})


def main():
    imported_at = datetime.now(timezone.utc).isoformat()
    teams, teams_count = wc_team_names()
    downloaded_at, download_warning = download_csv_if_missing()
    if not os.path.exists(IMPORT_PATH):
        write_empty(imported_at, download_warning or DOWNLOAD_FAILURE_WARNING)
        return

    qualification = []
    friendlies = []
    combined = []
    total_rows = 0
    matched_teams = set()
    csv_dates = []
    min_qual_date = date(2023, 1, 1)
    min_friendly_date = date(2025, 1, 1)
    with open(IMPORT_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                total_rows += 1
                match_date = parse_date(row.get("date"))
                if match_date:
                    csv_dates.append(match_date)
                home_in_scope = row.get("home_team") in teams
                away_in_scope = row.get("away_team") in teams
                if home_in_scope:
                    matched_teams.add(row.get("home_team"))
                if away_in_scope:
                    matched_teams.add(row.get("away_team"))
                if not match_date or not (home_in_scope or away_in_scope):
                    continue
                if not has_final_score(row):
                    continue
                match = to_match(row, imported_at, IMPORT_PATH)
                if is_qualification(row.get("tournament")) and match_date >= min_qual_date:
                    qualification.append(match)
                    combined.append(match)
                elif is_friendly(row.get("tournament")) and match_date >= min_friendly_date:
                    friendlies.append(match)
                    combined.append(match)
            except (KeyError, ValueError) as exc:
                print(f"[import-results] skipped row: {exc}")

    csv_min = min(csv_dates).isoformat() if csv_dates else None
    csv_max = max(csv_dates).isoformat() if csv_dates else None
    coverage_warning = ""
    if not csv_dates or max(csv_dates) < min_friendly_date:
        coverage_warning = RECENT_COVERAGE_WARNING
    warning = "" if combined else "CSV imported, but no World Cup qualification or recent friendly rows matched WC2026 teams."
    if coverage_warning:
        warning = f"{warning} {coverage_warning}".strip()
    meta = {
        "source": SOURCE_PROVIDER,
        "source_provider": SOURCE_PROVIDER,
        "source_endpoint": IMPORT_PATH,
        "source_file": "results.csv",
        "source_url": SOURCE_URL,
        "generated_at": imported_at,
        "downloaded_at": downloaded_at,
        "csv_min_date": csv_min,
        "csv_max_date": csv_max,
        "total_rows": total_rows,
        "matched_worldcup_teams": len(matched_teams),
        "qualification_matches_count": len(qualification),
        "friendlies_matches_count": len(friendlies),
        "coverage_warning": coverage_warning,
        "warning": warning,
    }
    save_cache("qualification_matches.json", {
        "meta": meta,
        "matches": qualification,
    })
    save_cache("qualification_friendlies_matches.json", combined)
    save_cache("qualification_friendlies_team_profiles.json", build_profiles(combined))
    meta["teams_count"] = teams_count
    save_cache("recent_friendlies_2025_2026.json", build_friendlies_cache(friendlies, teams, imported_at, warning, meta))
    save_cache("qualification_friendlies_meta.json", meta)
    print(f"[import-results] qualification={len(qualification)} friendlies={len(friendlies)} profiles={len(build_profiles(combined))}")


if __name__ == "__main__":
    main()
