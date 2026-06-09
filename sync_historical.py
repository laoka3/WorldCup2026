"""
世界杯足球数据分析Agent - 历史数据同步脚本
拉取 2022-2024 全部国际赛事比赛数据，建立历史对战数据库
用于 2026 世界杯 AI 分析的数据基础
"""

import json
import os
import time
import requests
import urllib3

urllib3.disable_warnings()

API_KEY = os.getenv("APIFOOTBALL_API_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cache")

os.makedirs(CACHE_DIR, exist_ok=True)

REQUEST_COUNT = [0]


def api_get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(3):
        REQUEST_COUNT[0] += 1
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30, verify=False)
            if resp.status_code == 429:
                wait = 70
                print(f"  [Rate Limit] waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            if data.get("errors"):
                err = str(data["errors"])
                if "rate" in err.lower() or "limit" in err.lower():
                    time.sleep(70)
                    continue
                print(f"  [API Warning] {err[:100]}")
            return data
        except Exception as e:
            print(f"  [Req Error] {e}")
            time.sleep(5)
    return None


def load_cache(name):
    path = os.path.join(CACHE_DIR, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_cache(name, data):
    path = os.path.join(CACHE_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {name} ({len(data) if isinstance(data, list) else 'dict'} items)")


# ============================================================
# 国际赛事配置 - 用于拉取历史对战数据
# ============================================================
INTERNATIONAL_LEAGUES = [
    {"id": 1, "name": "World Cup", "seasons": [2022]},
    {"id": 4, "name": "Euro Championship", "seasons": [2024]},
    {"id": 5, "name": "UEFA Nations League", "seasons": [2022, 2024]},
    {"id": 6, "name": "Africa Cup of Nations", "seasons": [2023]},
    {"id": 7, "name": "Asian Cup", "seasons": [2023]},
    {"id": 9, "name": "Copa America", "seasons": [2024]},
    {"id": 10, "name": "Friendlies", "seasons": [2022, 2023, 2024]},
    {"id": 2, "name": "UEFA Champions League", "seasons": [2023, 2024]},
    {"id": 3, "name": "UEFA Europa League", "seasons": [2023, 2024]},
]


def extract_match_info(f):
    """从API返回的fixture中提取关键信息"""
    return {
        "id": f["fixture"]["id"],
        "date": f["fixture"]["date"],
        "league_id": f["league"]["id"],
        "league_name": f["league"]["name"],
        "season": f["league"]["season"],
        "round": f["league"]["round"],
        "home_team": f["teams"]["home"]["name"],
        "away_team": f["teams"]["away"]["name"],
        "home_id": f["teams"]["home"]["id"],
        "away_id": f["teams"]["away"]["id"],
        "home_logo": f["teams"]["home"]["logo"],
        "away_logo": f["teams"]["away"]["logo"],
        "home_goals": f["goals"]["home"],
        "away_goals": f["goals"]["away"],
        "status": f["fixture"]["status"]["long"],
        "venue": f["fixture"]["venue"].get("name", "N/A") if f["fixture"]["venue"] else "N/A",
    }


def fetch_league_fixtures(league_id, season):
    cache_name = f"league_{league_id}_{season}.json"
    cached = load_cache(cache_name)
    if cached:
        return cached

    print(f"  Fetching league={league_id} ({season})...", end=" ")
    result = api_get("fixtures", {"league": league_id, "season": season})
    if result and result.get("response"):
        matches = [extract_match_info(f) for f in result["response"]]
        save_cache(cache_name, matches)
        print(f"{len(matches)} matches")
        return matches
    print("empty")
    return []


def build_all_historical_data():
    print("=" * 60)
    print("[HistorySync] 拉取 2022-2024 国际赛事历史数据")
    print("=" * 60)

    all_matches = []

    for league_conf in INTERNATIONAL_LEAGUES:
        for season in league_conf["seasons"]:
            matches = fetch_league_fixtures(league_conf["id"], season)
            all_matches.extend(matches)
            time.sleep(7)

    save_cache("all_historical_matches.json", all_matches)
    print(f"\n总计: {len(all_matches)} 场历史比赛")

    return all_matches


def build_team_profiles(all_matches):
    """从历史比赛数据构建球队画像"""
    print("\n[TeamProfile] 构建球队画像...")

    teams = {}
    for m in all_matches:
        if m["home_goals"] is None:
            continue
        for side, opp_side in [("home", "away"), ("away", "home")]:
            name = m[f"{side}_team"]
            tid = m[f"{side}_id"]
            opp = m[f"{opp_side}_team"]
            goals_for = m[f"{side}_goals"] or 0
            goals_against = m[f"{opp_side}_goals"] or 0

            if tid not in teams:
                teams[tid] = {
                    "id": tid, "name": name, "games": 0, "wins": 0,
                    "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0,
                    "opponents": {}, "form": [], "competitions": set()
                }

            t = teams[tid]
            t["games"] += 1
            t["goals_for"] += goals_for
            t["goals_against"] += goals_against
            t["competitions"].add(m["league_name"])

            if goals_for > goals_against:
                t["wins"] += 1
                t["form"].append("W")
            elif goals_for == goals_against:
                t["draws"] += 1
                t["form"].append("D")
            else:
                t["losses"] += 1
                t["form"].append("L")

            if opp not in t["opponents"]:
                t["opponents"][opp] = {"games": 0, "wins": 0, "draws": 0, "losses": 0,
                                        "goals_for": 0, "goals_against": 0}
            h2h = t["opponents"][opp]
            h2h["games"] += 1
            h2h["goals_for"] += goals_for
            h2h["goals_against"] += goals_against
            if goals_for > goals_against:
                h2h["wins"] += 1
            elif goals_for == goals_against:
                h2h["draws"] += 1
            else:
                h2h["losses"] += 1

    # 转换为列表并计算统计
    team_list = []
    for tid, t in teams.items():
        g = t["games"]
        if g < 5:
            continue
        win_rate = t["wins"] / g * 100 if g > 0 else 0
        avg_gf = t["goals_for"] / g
        avg_ga = t["goals_against"] / g
        recent = t["form"][-10:]
        recent_str = "".join(recent)
        team_list.append({
            "id": t["id"], "name": t["name"], "games": g,
            "wins": t["wins"], "draws": t["draws"], "losses": t["losses"],
            "win_rate": round(win_rate, 1),
            "goals_for": t["goals_for"], "goals_against": t["goals_against"],
            "avg_goals_for": round(avg_gf, 2),
            "avg_goals_against": round(avg_ga, 2),
            "recent_form": recent_str[-6:],
            "competitions": sorted(t["competitions"]),
            "opponents": t["opponents"],
            "attack_rating": min(95, round(40 + avg_gf * 18 + win_rate * 0.25)),
            "defense_rating": min(95, round(55 + (3 - avg_ga) * 12)),
            "midfield_rating": min(95, round(50 + win_rate * 0.3)),
        })

    team_list.sort(key=lambda x: x["win_rate"], reverse=True)
    save_cache("historical_team_profiles.json", team_list)
    print(f"  Generated {len(team_list)} team profiles")

    return team_list


def build_h2h_database(all_matches):
    """构建球队间历史对战数据库"""
    print("\n[H2H] 构建历史对战数据库...")

    h2h = {}
    for m in all_matches:
        if m["home_goals"] is None:
            continue
        pair = tuple(sorted([m["home_team"], m["away_team"]]))
        if pair not in h2h:
            h2h[pair] = []

        is_home = m["home_team"] == pair[0]
        h2h[pair].append({
            "date": m["date"],
            "competition": m["league_name"],
            "team_a": pair[0], "team_b": pair[1],
            "score_a_b": f"{m['home_goals']}-{m['away_goals']}" if is_home else f"{m['away_goals']}-{m['home_goals']}"
        })

    h2h_summary = {}
    for pair, matches in h2h.items():
        a_wins, draws, b_wins = 0, 0, 0
        total_goals = 0
        for m in matches:
            score = m["score_a_b"].split("-")
            ga, gb = int(score[0]), int(score[1])
            total_goals += ga + gb
            if ga > gb:
                a_wins += 1
            elif ga < gb:
                b_wins += 1
            else:
                draws += 1

        total = len(matches)
        h2h_summary[f"{pair[0]} vs {pair[1]}"] = {
            "team_a": pair[0], "team_b": pair[1],
            "total": total,
            "a_wins": a_wins, "draws": draws, "b_wins": b_wins,
            "avg_goals": round(total_goals / total, 2) if total > 0 else 0,
            "last_5": matches[-5:],
            "all_matches": matches
        }

    save_cache("historical_h2h.json", h2h_summary)
    print(f"  Generated {len(h2h_summary)} H2H records")
    return h2h_summary


def run_full_sync():
    all_matches = build_all_historical_data()
    build_team_profiles(all_matches)
    build_h2h_database(all_matches)

    print(f"\n{'='*60}")
    print(f"[HistorySync] 完成! API 请求数: {REQUEST_COUNT[0]}")
    print(f"[HistorySync] 总计 {len(all_matches)} 场历史比赛")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_full_sync()
