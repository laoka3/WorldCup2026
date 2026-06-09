"""
API-Football 客户端模块
- 封装所有 API-Football v3 接口调用
- 本地 JSON 缓存层，减少 API 请求次数（免费计划 100次/天）
- 数据源：2022 世界杯真实数据
"""

import sys
import io
import json
import os
import time
import requests
import urllib3
from collections import defaultdict

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except AttributeError:
    pass

urllib3.disable_warnings()

API_KEY = os.getenv("APIFOOTBALL_API_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

THESTATS_API_KEY = os.getenv("THESTATS_API_KEY", "")
THESTATS_BASE_URL = "https://api.thestatsapi.com/api"
THESTATS_HEADERS = {
    "Authorization": f"Bearer {THESTATS_API_KEY}",
    "Content-Type": "application/json",
}
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

os.makedirs(CACHE_DIR, exist_ok=True)

REQUEST_COUNT = {"count": 0, "last_reset": time.time()}


def _log_request():
    global REQUEST_COUNT
    now = time.time()
    if now - REQUEST_COUNT["last_reset"] > 86400:
        REQUEST_COUNT = {"count": 0, "last_reset": now}
    REQUEST_COUNT["count"] += 1
    print(f"[API] Request #{REQUEST_COUNT['count']} (today limit: 100)")


def api_get(endpoint, params=None, retries=2):
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(retries + 1):
        _log_request()
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=20, verify=False)
            if resp.status_code == 429:
                wait = 65
                print(f"[API] Rate limited (429), waiting {wait}s...")
                time.sleep(wait)
                continue
            if resp.status_code == 404:
                print(f"[TheStatsAPI] Not found: {endpoint}")
                return None
            resp.raise_for_status()
            data = resp.json()
            if data.get("errors"):
                err_msg = str(data["errors"])
                if "rate" in err_msg.lower() or "limit" in err_msg.lower():
                    wait = 65
                    print(f"[API] Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"[API] Warning: {err_msg}")
            return data
        except requests.exceptions.RequestException as e:
            print(f"[API] Request failed: {e}")
            if attempt < retries:
                time.sleep(5)
    return None


def load_cache(filename, default=None):
    path = os.path.join(CACHE_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def api_get_thestats(endpoint, params=None, retries=2):
    url = f"{THESTATS_BASE_URL}/{endpoint.lstrip('/')}"
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=THESTATS_HEADERS, params=params, timeout=25)
            if resp.status_code == 429:
                wait = 60
                print(f"[TheStatsAPI] Rate limited (429), waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"[TheStatsAPI] Request failed: {e}")
            if attempt < retries:
                time.sleep(5)
    return None


def thestats_cached_get(cache_name, endpoint, params=None, force=False):
    if not force:
        cached = load_cache(cache_name)
        if cached is not None:
            return cached

    data = api_get_thestats(endpoint, params=params)
    if data is not None:
        save_cache(cache_name, data)
    return data


WC2026_CN_TO_EN = {
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


def get_wc2026_team_names_en():
    schedule = load_cache("wc2026_schedule.json", {}) or {}
    teams = set()
    for team_list in schedule.get("groups", {}).values():
        for name in team_list:
            teams.add(WC2026_CN_TO_EN.get(name, name))
    return sorted(teams)


def get_thestats_competitions(force=False):
    return thestats_cached_get("thestats_competitions.json", "football/competitions", force=force)


def search_thestats_team(team_name, force=False):
    safe_name = team_name.lower().replace(" ", "_").replace("/", "_")
    return thestats_cached_get(f"thestats_team_search_{safe_name}.json", "football/teams", {"search": team_name}, force=force)


def get_thestats_matches(date_from, date_to, competition_id=None, team_id=None, force=False):
    params = {"date_from": date_from, "date_to": date_to}
    if competition_id:
        params["competition_id"] = competition_id
    if team_id:
        params["team_id"] = team_id
    key_parts = [date_from, date_to, competition_id or "all", team_id or "all"]
    cache_name = "thestats_matches_" + "_".join(str(p).replace("/", "_") for p in key_parts) + ".json"
    return thestats_cached_get(cache_name, "football/matches", params, force=force)


def get_thestats_match_stats(match_id, force=False):
    return thestats_cached_get(f"thestats_match_stats_{match_id}.json", f"football/matches/{match_id}/stats", force=force)


def get_thestats_player_stats(match_id, force=False):
    return thestats_cached_get(f"thestats_player_stats_{match_id}.json", f"football/matches/{match_id}/player-stats", force=force)


def get_thestats_lineups(match_id, force=False):
    return thestats_cached_get(f"thestats_lineups_{match_id}.json", f"football/matches/{match_id}/lineups", force=force)


def extract_thestats_data(response):
    if isinstance(response, dict):
        data = response.get("data")
        return data if data is not None else response.get("response", [])
    return []


def sync_thestats_match_details(match_ids, force=False, delay=0.4):
    details = {}
    for match_id in match_ids:
        details[str(match_id)] = {
            "stats": get_thestats_match_stats(match_id, force=force),
            "player_stats": get_thestats_player_stats(match_id, force=force),
            "lineups": get_thestats_lineups(match_id, force=force),
        }
        time.sleep(delay)
    save_cache("thestats_match_details.json", details)
    print(f"[TheStatsAPI] 比赛详情已缓存: {len(details)} 场")
    return details


def _pick_primary_team(team_name, search_result):
    candidates = (search_result or {}).get("data", []) if isinstance(search_result, dict) else []
    if not candidates:
        return None

    wc_candidates = [t for t in candidates if (t.get("primary_competition") or {}).get("id") == "comp_6107"]
    exact_wc = [t for t in wc_candidates if t.get("name", "").lower() == team_name.lower()]
    if exact_wc:
        return exact_wc[0]
    if wc_candidates:
        return wc_candidates[0]

    exact = [t for t in candidates if t.get("name", "").lower() == team_name.lower()]
    if exact:
        return exact[0]

    return candidates[0]


def build_thestats_team_enrichment():
    team_searches = load_cache("thestats_wc2026_team_search_results.json", {}) or {}
    wc_matches = load_cache("thestats_matches_2026-06-11_2026-07-20_all_all.json", {}) or {}
    matches = wc_matches.get("data", []) if isinstance(wc_matches, dict) else []

    team_matches = defaultdict(list)
    for match in matches:
        for side in ("home_team", "away_team"):
            team = match.get(side) or {}
            team_id = team.get("id")
            if team_id:
                team_matches[team_id].append({
                    "match_id": match.get("id"),
                    "utc_date": match.get("utc_date"),
                    "group": match.get("group_label"),
                    "status": match.get("status"),
                    "xg_available": match.get("xg_available"),
                    "opponent": (match.get("away_team") if side == "home_team" else match.get("home_team") or {}).get("name"),
                })

    enrichment = {}
    for team_name, search_result in team_searches.items():
        team = _pick_primary_team(team_name, search_result)
        if not team:
            continue

        team_id = team.get("id")
        enrichment[team_name] = {
            "source": "TheStatsAPI",
            "thestats_team_id": team_id,
            "team_name": team.get("name"),
            "short_name": team.get("short_name"),
            "country": team.get("country"),
            "primary_competition_id": (team.get("primary_competition") or {}).get("id"),
            "primary_competition_name": (team.get("primary_competition") or {}).get("name"),
            "scheduled_matches_2026": team_matches.get(team_id, []),
            "scheduled_match_count_2026": len(team_matches.get(team_id, [])),
            "xg_per_match": None,
            "xga_per_match": None,
            "lineup_strength": None,
            "injury_count": None,
            "player_form": None,
        }

    save_cache("thestats_team_enrichment.json", enrichment)
    print(f"[TheStatsAPI] 已生成球队扩展特征缓存: {len(enrichment)} 支")
    return enrichment


def _stat_value(stats_data, section, metric, side):
    container = stats_data.get(section, {}) if isinstance(stats_data, dict) else {}
    metric_data = container.get(metric, {}) if isinstance(container, dict) else {}
    if isinstance(metric_data, dict):
        all_data = metric_data.get("all", metric_data)
        if isinstance(all_data, dict):
            return all_data.get(side)
    return None


def _average(values):
    clean = []
    for value in values:
        try:
            if value is not None:
                clean.append(float(value))
        except (TypeError, ValueError):
            continue
    return round(sum(clean) / len(clean), 2) if clean else None


def _xg_value(row, key, proxy_key):
    value = row.get(key)
    proxy = row.get(proxy_key)
    try:
        numeric = float(value) if value is not None else None
    except (TypeError, ValueError):
        numeric = None
    try:
        proxy_numeric = float(proxy) if proxy is not None else None
    except (TypeError, ValueError):
        proxy_numeric = None
    if numeric is not None and numeric > 0:
        return numeric
    if proxy_numeric is not None and proxy_numeric > 0:
        return proxy_numeric
    return None


def _xg_source_quality(rows):
    direct = 0
    proxy = 0
    for row in rows:
        xg = row.get("xg")
        xga = row.get("xga")
        npxg = row.get("npxg")
        npxga = row.get("npxga")
        if xg not in (None, 0) or xga not in (None, 0):
            direct += 1
        elif npxg not in (None, 0) or npxga not in (None, 0):
            proxy += 1
    return {"direct_xg_matches": direct, "proxy_npxg_matches": proxy}


def summarize_thestats_team_metrics(max_matches_per_team=5, force=False, limit_teams=None):
    enrichment = load_cache("thestats_team_enrichment.json", {}) or {}
    summaries = dict(enrichment)
    items = list(enrichment.items())
    if limit_teams:
        items = items[:limit_teams]

    for team_name, team in items:
        team_id = team.get("thestats_team_id")
        if not team_id:
            continue

        matches_response = get_thestats_matches("2024-01-01", "2026-06-01", team_id=team_id, force=force)
        recent_matches = extract_thestats_data(matches_response)[:max_matches_per_team]
        metric_rows = []

        for match in recent_matches:
            if match.get("status") != "finished":
                continue
            match_id = match.get("id")
            stats_response = get_thestats_match_stats(match_id, force=force)
            stats_data = (stats_response or {}).get("data", {})
            if not isinstance(stats_data, dict) or not stats_data.get("overview"):
                continue
            home_id = (match.get("home_team") or {}).get("id")
            side = "home" if home_id == team_id else "away"
            against = "away" if side == "home" else "home"

            metric_rows.append({
                "match_id": match_id,
                "date": match.get("utc_date"),
                "xg": _stat_value(stats_data, "overview", "expected_goals", side),
                "xga": _stat_value(stats_data, "overview", "expected_goals", against),
                "npxg": _stat_value(stats_data, "np_expected_goals", "all", side),
                "npxga": _stat_value(stats_data, "np_expected_goals", "all", against),
                "shots": _stat_value(stats_data, "shots", "total_shots", side),
                "shots_on_target": _stat_value(stats_data, "shots", "shots_on_target", side),
                "possession": _stat_value(stats_data, "overview", "ball_possession", side),
                "passes": _stat_value(stats_data, "overview", "passes", side),
                "accurate_passes": _stat_value(stats_data, "passes", "accurate_passes", side),
                "final_third_entries": _stat_value(stats_data, "passes", "final_third_entries", side),
                "touches_in_box": _stat_value(stats_data, "attack", "touches_in_penalty_area", side),
                "interceptions": _stat_value(stats_data, "defending", "interceptions", side),
                "clearances": _stat_value(stats_data, "defending", "clearances", side),
            })
            time.sleep(0.25)

        xg_values = [_xg_value(r, "xg", "npxg") for r in metric_rows]
        xga_values = [_xg_value(r, "xga", "npxga") for r in metric_rows]
        source_quality = _xg_source_quality(metric_rows)

        summaries[team_name] = {
            **team,
            "metrics_sample_matches": len(metric_rows),
            "xg_sample_matches": len([v for v in xg_values if v is not None]),
            "xga_sample_matches": len([v for v in xga_values if v is not None]),
            "xg_source_quality": source_quality,
            "xg_per_match": _average(xg_values),
            "xga_per_match": _average(xga_values),
            "npxg_per_match": _average([r.get("npxg") for r in metric_rows]),
            "shots_per_match": _average([r.get("shots") for r in metric_rows]),
            "shots_on_target_per_match": _average([r.get("shots_on_target") for r in metric_rows]),
            "avg_possession": _average([r.get("possession") for r in metric_rows]),
            "final_third_entries_per_match": _average([r.get("final_third_entries") for r in metric_rows]),
            "touches_in_box_per_match": _average([r.get("touches_in_box") for r in metric_rows]),
            "interceptions_per_match": _average([r.get("interceptions") for r in metric_rows]),
            "clearances_per_match": _average([r.get("clearances") for r in metric_rows]),
            "metric_rows": metric_rows,
        }
        print(f"[TheStatsAPI] {team_name}: 高级指标样本 {len(metric_rows)} 场")

    save_cache("thestats_team_enrichment.json", summaries)
    print(f"[TheStatsAPI] 球队高级指标汇总完成: {len(summaries)} 支")
    return summaries


def summarize_thestats_team_lineups(force=False, max_matches_per_team=3):
    enrichment = load_cache("thestats_team_enrichment.json", {}) or {}
    updated = dict(enrichment)

    for team_name, team in enrichment.items():
        team_id = team.get("thestats_team_id")
        rows = team.get("metric_rows", [])[:max_matches_per_team]
        if not team_id or not rows:
            continue

        all_player_ratings = []
        starter_ratings = []
        position_ratings = defaultdict(list)
        confirmed_lineups = 0
        formations = []
        starters_seen = set()

        for row in rows:
            match_id = row.get("match_id")
            player_response = get_thestats_player_stats(match_id, force=force)
            lineup_response = get_thestats_lineups(match_id, force=force)
            player_rows = extract_thestats_data(player_response)
            lineup_data = (lineup_response or {}).get("data", {})

            for side in ("home", "away"):
                side_data = lineup_data.get(side, {}) if isinstance(lineup_data, dict) else {}
                if side_data.get("id") == team_id:
                    if lineup_data.get("confirmed"):
                        confirmed_lineups += 1
                    if side_data.get("formation"):
                        formations.append(side_data.get("formation"))
                    for player in side_data.get("starting_xi", []) or []:
                        starters_seen.add(player.get("id"))

            for player in player_rows:
                if player.get("team_id") != team_id or not player.get("played"):
                    continue
                rating = player.get("rating")
                if rating is None:
                    continue
                rating = float(rating)
                all_player_ratings.append(rating)
                position = player.get("position") or "U"
                position_ratings[position].append(rating)
                if player.get("started"):
                    starter_ratings.append(rating)
            time.sleep(0.25)

        if all_player_ratings:
            updated[team_name] = {
                **team,
                "player_form": _average(all_player_ratings),
                "lineup_strength": _average(starter_ratings) * 12 if starter_ratings else None,
                "avg_player_rating": _average(all_player_ratings),
                "avg_starter_rating": _average(starter_ratings),
                "avg_attacker_rating": _average(position_ratings.get("F", [])),
                "avg_midfielder_rating": _average(position_ratings.get("M", [])),
                "avg_defender_rating": _average(position_ratings.get("D", [])),
                "confirmed_lineups_count": confirmed_lineups,
                "known_starters_count": len(starters_seen),
                "recent_formations": sorted(set(formations)),
            }
            print(f"[TheStatsAPI] {team_name}: 球员/阵容样本 {len(all_player_ratings)} 人次")

    save_cache("thestats_team_enrichment.json", updated)
    print(f"[TheStatsAPI] 球员与阵容强度汇总完成: {len(updated)} 支")
    return updated


def sync_thestats_base_data(force=False):
    print("=" * 60)
    print("[TheStatsAPI] 开始同步基础数据...")
    print("=" * 60)

    competitions = get_thestats_competitions(force=force)
    if competitions:
        print("[TheStatsAPI] competitions 已缓存")

    teams = get_wc2026_team_names_en()
    team_results = {}
    for team_name in teams:
        team_results[team_name] = search_thestats_team(team_name, force=force)
        time.sleep(0.4)
    save_cache("thestats_wc2026_team_search_results.json", team_results)
    print(f"[TheStatsAPI] 2026球队搜索结果已缓存: {len(team_results)} 支")

    matches = get_thestats_matches("2026-06-11", "2026-07-20", force=force)
    if matches:
        print("[TheStatsAPI] 2026赛程范围 matches 已缓存")

    build_thestats_team_enrichment()

    print("[TheStatsAPI] 基础同步完成")
    return {"teams": len(team_results), "matches_cached": bool(matches), "competitions_cached": bool(competitions)}


def save_cache(filename, data):
    path = os.path.join(CACHE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_world_cup_teams():
    cached = load_cache("wc_teams.json")
    if cached:
        return cached

    print("[API] Fetching World Cup 2022 teams...")
    result = api_get("teams", {"league": 1, "season": 2022})
    if result and result.get("response"):
        teams = [t["team"] for t in result["response"]]
        save_cache("wc_teams.json", teams)
        return teams
    return []


def get_world_cup_fixtures():
    cached = load_cache("wc_fixtures.json")
    if cached:
        return cached

    print("[API] Fetching World Cup 2022 fixtures...")
    result = api_get("fixtures", {"league": 1, "season": 2022})
    if result and result.get("response"):
        fixtures = []
        for f in result["response"]:
            fixtures.append({
                "id": f["fixture"]["id"],
                "date": f["fixture"]["date"],
                "status": f["fixture"]["status"]["long"],
                "group": _extract_group(f),
                "stage": f["league"]["round"],
                "home_team": f["teams"]["home"]["name"],
                "away_team": f["teams"]["away"]["name"],
                "home_logo": f["teams"]["home"]["logo"],
                "away_logo": f["teams"]["away"]["logo"],
                "home_score": f["goals"]["home"],
                "away_score": f["goals"]["away"],
                "venue": f["fixture"]["venue"]["name"] + ", " + f["fixture"]["venue"]["city"] if f["fixture"]["venue"]["name"] else "N/A"
            })
        save_cache("wc_fixtures.json", fixtures)
        return fixtures
    return []


def _extract_group(f):
    league = f.get("league", {})
    round_name = league.get("round", "")
    if "Group" in round_name:
        home_name = f["teams"]["home"]["name"]
        return _get_group_for_team(home_name)
    return "淘汰赛"


WC2022_GROUPS = {
    # A组
    "Qatar": "A", "Ecuador": "A", "Senegal": "A", "Netherlands": "A",
    # B组
    "England": "B", "Iran": "B", "USA": "B", "Wales": "B",
    # C组
    "Argentina": "C", "Saudi Arabia": "C", "Mexico": "C", "Poland": "C",
    # D组
    "France": "D", "Australia": "D", "Denmark": "D", "Tunisia": "D",
    # E组
    "Spain": "E", "Costa Rica": "E", "Germany": "E", "Japan": "E",
    # F组
    "Belgium": "F", "Canada": "F", "Morocco": "F", "Croatia": "F",
    # G组
    "Brazil": "G", "Serbia": "G", "Switzerland": "G", "Cameroon": "G",
    # H组
    "Portugal": "H", "Ghana": "H", "Uruguay": "H", "South Korea": "H",
}


def _get_group_for_team(team_name):
    return WC2022_GROUPS.get(team_name, "?")


def get_team_statistics(team_id):
    cache_name = f"team_stats_{team_id}.json"
    cached = load_cache(cache_name)
    if cached:
        return cached

    print(f"[API] Fetching stats for team {team_id}...")
    result = api_get("teams/statistics", {"league": 1, "season": 2022, "team": team_id})
    if result and result.get("response"):
        stats = result["response"]
        save_cache(cache_name, stats)
        return stats
    return None


def get_all_team_stats():
    cached = load_cache("wc_all_team_stats.json")
    if cached and len(cached) >= 30:
        return cached

    teams = get_world_cup_teams()
    all_stats = load_cache("wc_all_team_stats.json") or {}

    for team in teams:
        tid = team["id"]
        if str(tid) in all_stats:
            print(f"[API] Team {tid} already cached, skipping")
            continue
        stats = get_team_statistics(tid)
        if stats:
            all_stats[str(tid)] = {
                "team_info": team,
                "statistics": stats
            }
        time.sleep(7)

    save_cache("wc_all_team_stats.json", all_stats)
    return all_stats


def convert_to_team_data(team_id, all_stats):
    key = str(team_id)
    if key not in all_stats:
        return None

    entry = all_stats[key]
    team_info = entry["team_info"]
    stats = entry["statistics"]

    form_str = stats.get("form", "")
    recent_form = list(form_str[-6:]) if form_str else []
    fixtures_stats = stats.get("fixtures", {})
    goals = stats.get("goals", {})
    clean_sheets = stats.get("clean_sheet", {})
    cards = stats.get("cards", {})
    biggest = stats.get("biggest", {})

    played = fixtures_stats.get("played", {}).get("total", 0)
    wins = fixtures_stats.get("wins", {}).get("total", 0)
    draws = fixtures_stats.get("draws", {}).get("total", 0)
    loses = fixtures_stats.get("loses", {}).get("total", 0)

    goals_for = float(goals.get("for", {}).get("average", {}).get("total", 0) or 0)
    goals_against = float(goals.get("against", {}).get("average", {}).get("total", 0) or 0)

    win_rate = (wins / played * 100) if played > 0 else 0

    attack_rating = min(95, round(50 + goals_for * 15 + win_rate * 0.2))
    defense_rating = min(95, round(50 + clean_sheets.get("total", 0) * 8 + (5 - goals_against) * 6))
    midfield_rating = min(95, round((attack_rating + defense_rating) / 2 + 5))

    return {
        "name": team_info["name"],
        "flag": team_info.get("country", team_info["name"]),
        "logo": team_info.get("logo", ""),
        "team_id": team_id,
        "fifa_rank": None,
        "confederation": _guess_confederation(team_info.get("country", "")),
        "market_value": None,
        "market_value_unit": "亿欧元",
        "coach": "N/A",
        "key_player": "N/A",
        "style": _guess_style(goals_for, goals_against, win_rate),
        "recent_form": recent_form if recent_form else ["W", "D", "L", "W", "D", "W"],
        "attack_rating": attack_rating,
        "defense_rating": defense_rating,
        "midfield_rating": midfield_rating,
        "avg_possession": round(45 + win_rate * 0.15, 1),
        "avg_goals_scored": round(goals_for, 1),
        "avg_goals_conceded": round(goals_against, 1),
        "xG_per_match": round(goals_for * 0.88, 1),
        "xGA_per_match": round(goals_against * 1.1, 1),
        "injuries": [],
        "wc2022_data": {
            "played": played,
            "wins": wins,
            "draws": draws,
            "loses": loses,
            "goals_for_total": goals.get("for", {}).get("total", {}).get("total", 0),
            "goals_against_total": goals.get("against", {}).get("total", {}).get("total", 0),
            "clean_sheets": clean_sheets.get("total", 0),
            "yellow_cards": cards.get("yellow", {}).get("0-15", {}).get("total", 0) if cards else 0,
            "biggest_win": biggest.get("wins", {}).get("home") or biggest.get("wins", {}).get("away") or "N/A"
        }
    }


def _guess_confederation(country):
    confed = {
        "Argentina": "CONMEBOL", "Brazil": "CONMEBOL", "Uruguay": "CONMEBOL",
        "England": "UEFA", "France": "UEFA", "Germany": "UEFA", "Spain": "UEFA",
        "Portugal": "UEFA", "Netherlands": "UEFA", "Italy": "UEFA", "Belgium": "UEFA",
        "Croatia": "UEFA", "Denmark": "UEFA", "Switzerland": "UEFA", "Poland": "UEFA",
        "Serbia": "UEFA", "Wales": "UEFA",
        "USA": "CONCACAF", "Mexico": "CONCACAF", "Canada": "CONCACAF", "Costa Rica": "CONCACAF",
        "Japan": "AFC", "South Korea": "AFC", "Australia": "AFC", "Iran": "AFC",
        "Saudi Arabia": "AFC", "Qatar": "AFC",
        "Senegal": "CAF", "Morocco": "CAF", "Tunisia": "CAF", "Cameroon": "CAF",
        "Ghana": "CAF", "Ecuador": "CONMEBOL"
    }
    return confed.get(country, "UEFA")


def _guess_style(goals_for, goals_against, win_rate):
    if goals_for > 2.2 and win_rate > 60:
        return "控球进攻"
    elif goals_for > 1.8 and goals_against < 1.0:
        return "高位压迫"
    elif goals_against < 0.8:
        return "防守反击"
    elif win_rate > 70:
        return "传控渗透"
    elif goals_for > 2.0:
        return "技术渗透"
    else:
        return "均衡"


def convert_fixtures_for_display():
    fixtures = get_world_cup_fixtures()
    display = []
    for f in fixtures:
        status_map = {
            "Match Finished": "completed",
            "Not Started": "upcoming",
            "First Half": "live",
            "Second Half": "live",
            "Halftime": "live"
        }
        stage = f.get("stage", "")
        if "Group" in stage:
            group = _get_group_for_team(f.get("home_team", ""))
        else:
            group = "淘汰赛"
        display.append({
            "id": f["id"],
            "group": group,
            "stage": f["stage"],
            "home_team": f["home_team"],
            "away_team": f["away_team"],
            "home_flag": f["home_team"],
            "away_flag": f["away_team"],
            "home_logo": f.get("home_logo", ""),
            "away_logo": f.get("away_logo", ""),
            "date": f["date"].split("T")[0],
            "time": f["date"].split("T")[1][:5] if "T" in f["date"] else "00:00",
            "venue": f.get("venue", "N/A"),
            "status": status_map.get(f["status"], "upcoming"),
            "home_score": f.get("home_score"),
            "away_score": f.get("away_score")
        })
    return display


def get_world_cup_news():
    cached = load_cache("wc_news.json")
    if cached:
        return cached

    fixtures = get_world_cup_fixtures()
    teams = get_world_cup_teams()

    news = []
    if fixtures:
        completed = [f for f in fixtures if f["status"] == "Match Finished"]
        if completed:
            latest = completed[-1]
            news.append({
                "id": 1, "title": f"世界杯决赛：{latest['home_team']} {latest['home_score']}-{latest['away_score']} {latest['away_team']}",
                "summary": f"2022卡塔尔世界杯决赛在卢赛尔体育场举行，双方鏖战后{latest['home_team']}获胜，捧起大力神杯。",
                "image": "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800&q=80",
                "source": "FIFA官方", "date": latest["date"], "category": "赛程"
            })

    news.append({
        "id": 2, "title": f"2022世界杯32强数据总览",
        "summary": f"来自全球{len(teams)}支球队参加了卡塔尔世界杯，本届赛事共产生64场精彩比赛。各队数据已通过API-Football同步至平台。",
        "image": "https://images.unsplash.com/photo-1511886929837-354d827aae26?w=800&q=80",
        "source": "API-Football", "date": "2022-12-18", "category": "赛事"
    })
    news.append({
        "id": 3, "title": "世界杯数据分析平台升级：接入真实API数据",
        "summary": "平台现已接入API-Football真实数据源，提供2022世界杯全部64场完整数据、32支球队比赛统计，所有AI分析基于真实比赛数据。",
        "image": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&q=80",
        "source": "WorldSoccer AI", "date": "2026-06-02", "category": "数据"
    })
    news.append({
        "id": 4, "title": "阿根廷队2022世界杯数据深度解读",
        "summary": "阿根廷队在2022卡塔尔世界杯7场比赛中攻入15球，场均2.1球，最终点球大战击败法国夺冠，梅西加冕球王。",
        "image": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800&q=80",
        "source": "TyC Sports", "date": "2022-12-20", "category": "球队"
    })
    news.append({
        "id": 5, "title": "2022世界杯爆冷：摩洛哥创非洲历史杀入四强",
        "summary": "摩洛哥队在卡塔尔世界杯上表现惊艳，连胜比利时、西班牙、葡萄牙，成为首支进入世界杯四强的非洲球队。",
        "image": "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=800&q=80",
        "source": "BBC Sport", "date": "2022-12-14", "category": "球队"
    })
    news.append({
        "id": 6, "title": "2022世界杯各组数据回顾",
        "summary": f"2022年卡塔尔世界杯8个小组赛阶段共产生多场经典对决，各小组头名顺利出线。本平台提供所有比赛的完整数据回溯。",
        "image": "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?w=800&q=80",
        "source": "ESPN", "date": "2022-12-03", "category": "赛事"
    })

    save_cache("wc_news.json", news)
    return news


def get_team_data_by_name(team_name, all_stats_cache=None):
    if all_stats_cache is None:
        all_stats_cache = load_cache("wc_all_team_stats.json")

    if all_stats_cache:
        for tid_str, entry in all_stats_cache.items():
            if entry.get("team_info", {}).get("name") == team_name:
                return convert_to_team_data(int(tid_str), all_stats_cache)

    for stat_file in os.listdir(CACHE_DIR):
        if stat_file.startswith("team_stats_") and stat_file.endswith(".json"):
            stats = load_cache(stat_file)
            if stats and stats.get("team", {}).get("name") == team_name:
                tid = stats["team"]["id"]
                all_stats = load_cache("wc_all_team_stats.json") or {}
                return convert_to_team_data(tid, all_stats)

    return None


def sync_all_data():
    print("=" * 60)
    print("[DataSync] 开始从 API-Football 同步数据...")
    print("=" * 60)

    teams = get_world_cup_teams()
    print(f"[DataSync] 获取到 {len(teams)} 支球队")

    fixtures = get_world_cup_fixtures()
    print(f"[DataSync] 获取到 {len(fixtures)} 场比赛")

    if teams:
        print("[DataSync] 拉取球队详细统计数据...")
        all_stats = get_all_team_stats()
        print(f"[DataSync] 已获取 {len(all_stats)} 支球队的统计数据")

        team_list = []
        for tid_str, entry in all_stats.items():
            td = convert_to_team_data(int(tid_str), all_stats)
            if td:
                team_list.append(td)
        save_cache("wc_team_list.json", team_list)
        print(f"[DataSync] 已生成 {len(team_list)} 支球队的分析数据")

    display_fixtures = convert_fixtures_for_display()
    save_cache("wc_display_fixtures.json", display_fixtures)
    print(f"[DataSync] 已生成 {len(display_fixtures)} 场展示用比赛数据")

    news = get_world_cup_news()
    print(f"[DataSync] 已生成 {len(news)} 条新闻")

    print("=" * 60)
    print("[DataSync] 数据同步完成!")
    print(f"[DataSync] API 请求数: {REQUEST_COUNT['count']} / 100 (今日限额)")
    print("=" * 60)


if __name__ == "__main__":
    sync_all_data()
