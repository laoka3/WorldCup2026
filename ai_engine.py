"""
世界杯足球数据分析Agent - AI分析引擎 v4.0
数据基础:
  - 2022-2024 全部国际赛事 ~1805 场国家队比赛 (已排除俱乐部赛事)
  - Elo 评分系统 — 对手强度归一化
  - 赛事加权 (世界杯 > 洲际杯 > 友谊赛)
  - 时间衰减 (2024 > 2023 > 2022)
  - 299 支球队历史画像 + 1906 条 H2H 记录
  - 2026 世界杯 48 队 104 场赛程

算法优化 v4.0:
  1. Elo 评分: 基于 1805 场国家队比赛逐场迭代, 考虑对手强度
  2. 赛事权重: World Cup 1.5x / Euro&Copa 1.3x / AFCON&Asian 1.1x / Nations 1.0x / Friendly 0.5x
  3. 时间衰减: 2024 1.0x / 2023 0.85x / 2022 0.7x
  4. 综合实力分: 60% Elo + 20% 攻防统计 + 20% 近期状态
  5. 排除俱乐部赛事 (Champions League / Europa League)

合规声明:
1. 本模块仅做赛事数据分析
2. 只输出概率、数据对比、战术分析
3. 不输出任何精准比分
4. 不提供任何购彩相关内容
5. 所有结果为概率性分析，仅供参考
"""

import json
import math
import random
import os
import html
import re
import urllib.error
import urllib.parse
import urllib.request
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from collections import defaultdict

random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")

LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
LLM_BASE_URL = (os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.mirrorworkforce.cn/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or os.getenv("DEEPSEEK_MODEL") or "gpt-5.5"
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "20"))
LLM_LAST_ERROR = ""
NEWS_PROVIDER = "bing"
BING_NEWS_API_KEY = os.getenv("BING_NEWS_API_KEY") or os.getenv("RAPIDAPI_KEY") or ""
BING_NEWS_API_HOST = os.getenv("BING_NEWS_API_HOST") or "bing-news-search1.p.rapidapi.com"
BING_NEWS_API_URL = os.getenv("BING_NEWS_API_URL") or "https://bing-news-search1.p.rapidapi.com/news/search"
BING_NEWS_QUERY = os.getenv("BING_NEWS_QUERY") or "2026 世界杯 OR 国际足联世界杯 OR 世界杯赛程"
BING_NEWS_MARKET = os.getenv("BING_NEWS_MARKET") or "zh-CN"
BING_NEWS_FRESHNESS = os.getenv("BING_NEWS_FRESHNESS") or "Day"
NEWS_MAX_RESULTS = int(os.getenv("NEWS_MAX_RESULTS", "12"))
NEWS_RSS_FEEDS = [
    os.getenv("GOOGLE_NEWS_RSS_URL") or "https://news.google.com/rss/search?q=2026%E4%B8%96%E7%95%8C%E6%9D%AF%20OR%20FIFA%20World%20Cup%202026&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
]


def get_llm_config():
    return {
        "enabled": bool(LLM_API_KEY),
        "base_url": LLM_BASE_URL,
        "model": LLM_MODEL,
        "timeout": LLM_TIMEOUT,
        "api_key_set": bool(LLM_API_KEY),
        "api_key_masked": "***" if LLM_API_KEY else "",
    }


def update_llm_config(base_url=None, model=None, api_key=None, timeout=None):
    global LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT
    if base_url is not None and str(base_url).strip():
        LLM_BASE_URL = str(base_url).strip().rstrip("/")
    if model is not None and str(model).strip():
        LLM_MODEL = str(model).strip()
    if api_key is not None and str(api_key).strip():
        LLM_API_KEY = str(api_key).strip()
    if timeout is not None:
        LLM_TIMEOUT = max(5, min(120, int(timeout)))
    return get_llm_config()


CN_TO_EN = {
    "美国": "USA", "英格兰": "England", "墨西哥": "Mexico", "加拿大": "Canada",
    "巴西": "Brazil", "阿根廷": "Argentina", "法国": "France", "西班牙": "Spain",
    "南非": "South Africa", "捷克": "Czechia", "波黑": "Bosnia and Herzegovina", "海地": "Haiti",
    "库拉索": "Curaçao", "佛得角": "Cabo Verde", "刚果民主共和国": "DR Congo",
    "意大利": "Italy", "葡萄牙": "Portugal", "德国": "Germany", "荷兰": "Netherlands",
    "克罗地亚": "Croatia", "比利时": "Belgium", "乌拉圭": "Uruguay", "丹麦": "Denmark",
    "塞内加尔": "Senegal", "摩洛哥": "Morocco", "日本": "Japan", "伊朗": "Iran",
    "韩国": "South Korea", "澳大利亚": "Australia", "沙特阿拉伯": "Saudi Arabia",
    "卡塔尔": "Qatar", "突尼斯": "Tunisia", "埃及": "Egypt", "加纳": "Ghana",
    "喀麦隆": "Cameroon", "科特迪瓦": "Ivory Coast", "阿尔及利亚": "Algeria",
    "尼日利亚": "Nigeria", "塞尔维亚": "Serbia", "瑞士": "Switzerland",
    "波兰": "Poland", "瑞典": "Sweden", "希腊": "Greece", "奥地利": "Austria",
    "威尔士": "Wales", "苏格兰": "Scotland", "乌克兰": "Ukraine", "秘鲁": "Peru",
    "智利": "Chile", "哥伦比亚": "Colombia", "哥斯达黎加": "Costa Rica",
    "厄瓜多尔": "Ecuador", "委内瑞拉": "Venezuela", "伊拉克": "Iraq",
    "约旦": "Jordan", "乌兹别克斯坦": "Uzbekistan", "马里": "Mali",
    "布基纳法索": "Burkina Faso", "几内亚": "Guinea", "刚果民主共和国": "DR Congo",
    "南非": "South Africa", "捷克": "Czechia", "匈牙利": "Hungary",
    "挪威": "Norway", "芬兰": "Finland", "斯洛伐克": "Slovakia",
    "罗马尼亚": "Romania", "土耳其": "Turkey", "俄罗斯": "Russia",
    "爱尔兰": "Republic of Ireland", "冰岛": "Iceland", "巴拉圭": "Paraguay",
    "玻利维亚": "Bolivia", "巴拿马": "Panama", "牙买加": "Jamaica",
    "洪都拉斯": "Honduras", "萨尔瓦多": "El Salvador",
    "新西兰": "New Zealand",
}

NAME_ALIASES = {
    "Czechia": ["Czech Republic"],
    "Czech Republic": ["Czechia"],
    "USA": ["United States"],
    "United States": ["USA"],
    "South Korea": ["Korea Republic"],
    "Korea Republic": ["South Korea"],
    "DR Congo": ["Congo DR", "Democratic Republic of the Congo"],
    "Congo DR": ["DR Congo", "Democratic Republic of the Congo"],
    "Ivory Coast": ["Côte d'Ivoire", "Cote d'Ivoire"],
    "Côte d'Ivoire": ["Ivory Coast", "Cote d'Ivoire"],
    "Cabo Verde": ["Cape Verde"],
    "Cape Verde": ["Cabo Verde"],
}

COMPETITION_WEIGHTS = {
    "World Cup": 1.5,
    "Euro Championship": 1.3,
    "Copa America": 1.3,
    "Africa Cup of Nations": 1.1,
    "Asian Cup": 1.1,
    "UEFA Nations League": 1.0,
    "Friendlies": 0.5,
    "CONCACAF Gold Cup": 1.0,
    "WC Qualification": 1.0,
    "World Cup - Qualification": 1.0,
}

CLUB_COMPETITIONS = {
    "UEFA Champions League", "UEFA Europa League",
}

SEASON_WEIGHTS = {2024: 1.0, 2023: 0.85, 2022: 0.70}

_elo_ratings = None
_team_profiles = None
_h2h_data = None
_wc2022_teams = None
_static_teams = None
_wc2026_schedule = None
_all_matches = None
_thestats_team_enrichment = None
_model_calibration = None
_recent_friendlies_cache = None
_qualification_matches_cache = None
_market_odds_cache = None

DEFAULT_MODEL_PARAMS = {
    "home_advantage": 45,
    "elo_scale": 400,
    "draw_base": 0.27,
    "draw_width": 700,
    "h2h_max_weight": 0.15,
    "h2h_min_matches": 3,
    "dixon_coles_rho": -0.05,
    "score_model_weight": 0.0,
}


def _normalize_name(name):
    return CN_TO_EN.get(name, name)


def _name_variants(name):
    normalized = _normalize_name(name)
    variants = []
    for value in (name, normalized, *NAME_ALIASES.get(normalized, []), *NAME_ALIASES.get(name, [])):
        if value and value not in variants:
            variants.append(value)
    return variants


def _same_team_name(left, right):
    return bool(set(_name_variants(left)) & set(_name_variants(right)))


def load_cache(name):
    path = os.path.join(CACHE_DIR, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _cache_count(data):
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        if isinstance(data.get("teams"), dict):
            return len(data["teams"])
        if isinstance(data.get("matches"), dict):
            return len(data["matches"])
        if isinstance(data.get("matches"), list):
            return len(data["matches"])
        return len(data)
    return 0


def check_prediction_data_health():
    """检查预测数据完整性，避免把默认值误呈现为真实球队数据。"""
    priority_matches = load_cache("qualification_friendlies_matches.json") or []
    priority_profiles = load_cache("qualification_friendlies_team_profiles.json") or []
    priority_meta = load_cache("qualification_friendlies_meta.json") or {}
    qualification_cache = load_cache("qualification_matches.json") or {}
    recent_friendlies_cache = load_cache("recent_friendlies_2025_2026.json") or {}
    market_odds_cache = load_cache("market_odds.json") or {}
    historical_matches = load_cache("all_historical_matches.json") or []
    team_profiles = load_cache("historical_team_profiles.json") or []
    h2h = load_cache("historical_h2h.json") or {}
    thestats = load_cache("thestats_team_enrichment.json") or {}
    schedule = load_cache("wc2026_schedule.json") or {}
    static_teams = _load_static_teams()
    schedule_matches = schedule.get("matches", []) if isinstance(schedule, dict) else []

    health = {
        "qualification_matches": {"available": bool((qualification_cache or {}).get("matches")), "count": _cache_count((qualification_cache or {}).get("matches", [])), "warning": (qualification_cache or {}).get("meta", {}).get("warning", "")},
        "recent_friendlies": {"available": bool((recent_friendlies_cache or {}).get("teams")), "count": _cache_count((recent_friendlies_cache or {}).get("teams", {})), "warning": (recent_friendlies_cache or {}).get("meta", {}).get("warning", "")},
        "market_odds": {"available": bool((market_odds_cache or {}).get("matches")), "count": _cache_count((market_odds_cache or {}).get("matches", {})), "warning": (market_odds_cache or {}).get("meta", {}).get("warning", "")},
        "qualification_friendlies_matches": {"available": bool(priority_matches), "count": _cache_count(priority_matches)},
        "qualification_friendlies_profiles": {"available": bool(priority_profiles), "count": _cache_count(priority_profiles)},
        "historical_matches": {"available": bool(historical_matches), "count": _cache_count(historical_matches)},
        "team_profiles": {"available": bool(team_profiles), "count": _cache_count(team_profiles)},
        "static_team_profiles": {"available": bool(static_teams), "count": len(static_teams), "source": "data/teams.json"},
        "h2h": {"available": bool(h2h), "count": _cache_count(h2h)},
        "thestats_enrichment": {"available": bool(thestats), "count": _cache_count(thestats)},
        "schedule": {"available": len(schedule_matches) == 104, "matches": len(schedule_matches)},
        "warning": "",
    }
    warnings = []
    if not health["qualification_friendlies_matches"]["available"] or not health["qualification_friendlies_profiles"]["available"]:
        if priority_meta.get("warning"):
            warnings.append(f"世界杯预选赛/近期热身赛暂不可用：{priority_meta['warning']} 当前使用本地静态球队画像或默认占位。")
        else:
            warnings.append("世界杯预选赛/近期热身赛缓存尚未同步；当前使用本地静态球队画像或默认占位。")
    elif health["qualification_friendlies_profiles"]["count"] < 32:
        warnings.append("世界杯预选赛/近期热身赛画像覆盖不足；缺失球队会回退到本地静态画像或默认占位。")
    if not health["qualification_friendlies_profiles"]["available"] and not health["static_team_profiles"]["available"]:
        warnings.append("球队画像缓存缺失；部分球队会回退到默认 Elo 1450 和默认能力值。")
    if not health["h2h"]["available"]:
        warnings.append("两队交锋缓存缺失；H2H 修正暂未启用。")
    if not health["thestats_enrichment"]["available"]:
        health["thestats_enrichment"]["optional_warning"] = "TheStats 高级数据未同步；xG/player/lineup 只作为可选增强，不影响基础模型运行。"
    if not health["schedule"]["available"]:
        warnings.append("World Cup schedule cache is incomplete; venue/context matching may be degraded.")
    health["warning"] = " ".join(warnings)
    return health


def _load_all_matches():
    global _all_matches
    if _all_matches is None:
        raw = load_cache("qualification_friendlies_matches.json") or load_cache("all_historical_matches.json") or []
        _all_matches = [m for m in raw
                        if m.get("league_name") not in CLUB_COMPETITIONS
                        and m.get("home_goals") is not None
                        and m.get("away_goals") is not None
                        and m.get("status") == "Match Finished"]
        _all_matches.sort(key=lambda m: m.get("date", ""))
    return _all_matches


def _load_team_profiles():
    global _team_profiles
    if _team_profiles is None:
        _team_profiles = load_cache("qualification_friendlies_team_profiles.json") or load_cache("historical_team_profiles.json") or []
    return _team_profiles


def _load_h2h():
    global _h2h_data
    if _h2h_data is None:
        _h2h_data = load_cache("historical_h2h.json") or {}
    return _h2h_data


def _load_wc2022_teams():
    global _wc2022_teams
    if _wc2022_teams is None:
        _wc2022_teams = load_cache("wc_team_list.json") or []
    return _wc2022_teams


def _load_static_teams():
    global _static_teams
    if _static_teams is None:
        path = os.path.join(BASE_DIR, "data", "teams.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                _static_teams = raw.get("teams", []) if isinstance(raw, dict) else []
            except (OSError, json.JSONDecodeError):
                _static_teams = []
        else:
            _static_teams = []
    return _static_teams


def _load_wc2026_schedule():
    global _wc2026_schedule
    if _wc2026_schedule is None:
        _wc2026_schedule = load_cache("wc2026_schedule.json")
    return _wc2026_schedule


def get_elo_ratings():
    """基于 ~1805 场国家队比赛构建 Elo 评分系统"""
    global _elo_ratings
    if _elo_ratings is not None:
        return _elo_ratings

    matches = _load_all_matches()
    elo = defaultdict(lambda: 1500.0)
    match_count = defaultdict(int)
    home_advantage = 65

    for m in matches:
        home = m["home_team"]
        away = m["away_team"]
        hg = m["home_goals"]
        ag = m["away_goals"]

        comp_weight = COMPETITION_WEIGHTS.get(m.get("league_name", ""), 0.6)
        try:
            year = int(str(m.get("season", 2023))[:4])
        except (ValueError, TypeError):
            year = 2023
        time_weight = SEASON_WEIGHTS.get(year, 0.7)

        K = 32 * comp_weight * time_weight

        goal_diff = abs(hg - ag)
        if goal_diff > 0:
            K *= 1.0 + 0.2 * math.log(1 + goal_diff)

        r_home = elo[home] + home_advantage
        r_away = elo[away]
        expected_home = 1.0 / (1.0 + 10 ** ((r_away - r_home) / 400.0))
        expected_away = 1.0 - expected_home

        if hg > ag:
            actual_home, actual_away = 1.0, 0.0
        elif hg < ag:
            actual_home, actual_away = 0.0, 1.0
        else:
            actual_home, actual_away = 0.5, 0.5

        if match_count[home] < 30:
            k_factor = K * (1 + max(0, (30 - match_count[home]) / 30))
        else:
            k_factor = K
        if match_count[away] < 30:
            k_factor_away = K * (1 + max(0, (30 - match_count[away]) / 30))
        else:
            k_factor_away = K

        elo[home] += k_factor * (actual_home - expected_home)
        elo[away] += k_factor_away * (actual_away - expected_away)

        match_count[home] += 1
        match_count[away] += 1

    _elo_ratings = dict(elo)
    return _elo_ratings


def elo_to_score(elo_rating):
    """将 Elo 分映射到 0-100 实力分"""
    return round(min(100, max(0, (elo_rating - 1000) / 10.0)), 2)


def get_team_profile(team_name):
    variants = set(_name_variants(team_name))
    profiles = _load_team_profiles()
    for p in profiles:
        if p.get("name") in variants:
            return p
    return None


def get_wc2022_team(team_name):
    teams = _load_wc2022_teams()
    for t in teams:
        if t.get("name") == team_name:
            return t
    return None


def get_static_team(team_name):
    for team in _load_static_teams():
        if _same_team_name(team.get("name", ""), team_name):
            return team
    return None


def calculate_static_elo_anchor(static_team):
    """Static prior from FIFA rank plus a small squad market-value correction."""
    if not static_team:
        return None

    rank = _safe_float(static_team.get("fifa_rank"))
    if rank is None:
        static_avg = (
            _safe_float(static_team.get("attack_rating")) or 70
        ) * 0.4 + (
            _safe_float(static_team.get("defense_rating")) or 70
        ) * 0.3 + (
            _safe_float(static_team.get("midfield_rating")) or 70
        ) * 0.3
        rank_anchor = 1200 + static_avg * 5
    else:
        rank_points = [
            (1, 1720),
            (5, 1680),
            (10, 1640),
            (20, 1580),
            (40, 1500),
            (80, 1420),
            (120, 1360),
            (180, 1300),
        ]
        if rank <= rank_points[0][0]:
            rank_anchor = rank_points[0][1]
        else:
            rank_anchor = rank_points[-1][1]
            for (r1, e1), (r2, e2) in zip(rank_points, rank_points[1:]):
                if r1 <= rank <= r2:
                    ratio = (rank - r1) / (r2 - r1)
                    rank_anchor = e1 + (e2 - e1) * ratio
                    break

    market_value = _safe_float(static_team.get("market_value"))
    if market_value is None:
        market_delta = 0
    elif market_value >= 10:
        market_delta = 40
    elif market_value >= 5:
        market_delta = 25
    elif market_value >= 2:
        market_delta = 10
    else:
        market_delta = -10

    return round(rank_anchor + market_delta, 1)


def get_h2h(home_team, away_team):
    h2h = _load_h2h()
    home_en = _normalize_name(home_team)
    away_en = _normalize_name(away_team)

    def _try_key(key):
        if key in h2h:
            d = h2h[key]
            return dict(d) if _same_team_name(d.get("team_a", ""), home_team) else _swap_h2h(d, home_team, away_team)
        return None

    def _swap_h2h(data, ht, at):
        d = dict(data)
        a_wins = d["a_wins"]
        b_wins = d["b_wins"]
        d["a_wins"] = b_wins
        d["b_wins"] = a_wins
        d["team_a"] = ht
        d["team_b"] = at
        return d

    for home_variant in _name_variants(home_team):
        for away_variant in _name_variants(away_team):
            result = _try_key(f"{home_variant} vs {away_variant}")
            if result:
                return result
            result = _try_key(f"{away_variant} vs {home_variant}")
            if result:
                return result
    for d in h2h.values():
        if not isinstance(d, dict):
            continue
        team_a = d.get("team_a", "")
        team_b = d.get("team_b", "")
        if _same_team_name(team_a, home_team) and _same_team_name(team_b, away_team):
            return dict(d)
        if _same_team_name(team_a, away_team) and _same_team_name(team_b, home_team):
            return _swap_h2h(d, home_team, away_team)
    return None


def _load_thestats_team_enrichment():
    global _thestats_team_enrichment
    if _thestats_team_enrichment is None:
        _thestats_team_enrichment = load_cache("thestats_team_enrichment.json") or {}
    return _thestats_team_enrichment


def get_thestats_enrichment(team_name):
    data = _load_thestats_team_enrichment()
    if not data:
        return None
    return data.get(team_name) or data.get(_normalize_name(team_name)) or data.get(team_name.lower())


def _first_present(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _valid_metric_count(rows, key):
    count = 0
    for row in rows or []:
        if isinstance(row, dict) and row.get(key) is not None:
            count += 1
    return count


def _advanced_sample_confidence(sample_count):
    sample = _safe_float(sample_count) or 0
    if sample <= 0:
        return 0.0
    if sample < 3:
        return 0.2
    if sample < 6:
        return 0.5
    return 1.0


def _thestats_quality_score(thestats):
    """只基于 TheStatsAPI 可用字段评估高级数据可信度。"""
    if not thestats:
        return 0.0
    metrics_sample = _safe_float(thestats.get("metrics_sample_matches")) or 0
    xg_sample = _safe_float(thestats.get("xg_sample_matches")) or 0
    xga_sample = _safe_float(thestats.get("xga_sample_matches")) or 0
    source = thestats.get("xg_source_quality") or {}
    direct = _safe_float(source.get("direct_xg_matches")) or 0
    proxy = _safe_float(source.get("proxy_npxg_matches")) or 0

    sample_score = min(1.0, metrics_sample / 8.0)
    xg_sample_score = min(1.0, min(xg_sample, xga_sample) / 6.0) if min(xg_sample, xga_sample) > 0 else 0.0
    direct_ratio = direct / max(1.0, direct + proxy)
    direct_score = 0.45 + direct_ratio * 0.55 if direct + proxy > 0 else 0.35
    competition_score = 1.0 if thestats.get("primary_competition_id") == "comp_6107" else 0.85

    score = sample_score * 0.35 + xg_sample_score * 0.35 + direct_score * 0.20 + competition_score * 0.10
    return round(max(0.0, min(1.0, score)), 2)


def _xg_source_confidence(adv):
    source = adv.get("xg_source_quality") or {}
    direct = _safe_float(source.get("direct_xg_matches")) or 0
    proxy = _safe_float(source.get("proxy_npxg_matches")) or 0
    if direct + proxy <= 0:
        return 0.65
    return max(0.45, min(1.0, 0.55 + 0.45 * direct / (direct + proxy)))


def _clean_xg_metric(value, sample_count, proxy_value=None):
    numeric = _safe_float(value)
    proxy = _safe_float(proxy_value)
    sample = _safe_float(sample_count) or 0
    if numeric is not None and numeric > 0:
        return numeric, "direct"
    if proxy is not None and proxy > 0:
        return proxy, "npxg_proxy"
    if numeric == 0 and sample >= 5:
        return 0.0, "direct_zero"
    return None, "missing_or_invalid_zero"


def build_team_data(team_name):
    """合并所有数据源构建球队画像：静态画像为 base，CSV 画像仅作状态/统计修正。"""
    profile = get_team_profile(team_name)
    thestats = get_thestats_enrichment(team_name)
    wc2022 = get_wc2022_team(team_name)
    static_team = get_static_team(team_name)
    elo_ratings = get_elo_ratings()
    en_name = _normalize_name(team_name)
    historical_elo = elo_ratings.get(en_name, elo_ratings.get(team_name, 1450))
    static_anchor_elo = calculate_static_elo_anchor(static_team)
    if static_team and static_anchor_elo is not None:
        elo = historical_elo * 0.50 + static_anchor_elo * 0.50
        elo_source = "historical_static_anchor_blend"
    else:
        elo = historical_elo
        elo_source = "historical_cache" if historical_elo != 1450 else "default_placeholder"
    elo_score = elo_to_score(elo)

    result = {
        "name": team_name,
        "flag": team_name,
        "logo": "",
        "fifa_rank": None,
        "confederation": "",
        "attack_rating": 70,
        "defense_rating": 70,
        "midfield_rating": 70,
        "avg_goals_scored": 1.2,
        "avg_goals_conceded": 1.1,
        "xG_per_match": 1.0,
        "xGA_per_match": 1.0,
        "avg_possession": 48,
        "recent_form": [],
        "style": "均衡",
        "market_value": None,
        "injuries": [],
        "games_analyzed": 0,
        "elo_rating": round(elo, 1),
        "elo_score": elo_score,
        "historical_elo": round(historical_elo, 1),
        "static_anchor_elo": static_anchor_elo,
        "elo_source": elo_source,
        "wc2022_data": None,
        "data_source": "无历史数据",
        "profile_warning": "",
        "advanced_inputs": {
            "xg": None,
            "xga": None,
            "xg_sample_matches": 0,
            "xga_sample_matches": 0,
            "metrics_sample_matches": 0,
            "lineup_strength": None,
            "injury_count": None,
            "player_form": None,
            "source": None,
        },
    }

    if static_team:
        result.update({
            "flag": static_team.get("flag", result["flag"]),
            "fifa_rank": static_team.get("fifa_rank"),
            "confederation": static_team.get("confederation", ""),
            "attack_rating": static_team.get("attack_rating", 70),
            "defense_rating": static_team.get("defense_rating", 70),
            "midfield_rating": static_team.get("midfield_rating", 70),
            "avg_goals_scored": static_team.get("avg_goals_scored", 1.2),
            "avg_goals_conceded": static_team.get("avg_goals_conceded", 1.1),
            "xG_per_match": static_team.get("xG_per_match", 1.0),
            "xGA_per_match": static_team.get("xGA_per_match", 1.0),
            "avg_possession": static_team.get("avg_possession", 48),
            "recent_form": static_team.get("recent_form", []),
            "style": static_team.get("style", "均衡"),
            "market_value": static_team.get("market_value"),
            "coach": static_team.get("coach"),
            "key_player": static_team.get("key_player"),
            "injuries": static_team.get("injuries", []),
            "games_analyzed": len(static_team.get("recent_form", [])),
            "data_source": "本地静态球队画像(data/teams.json)",
        })

    if profile:
        csv_attack = profile.get("attack_rating", 70)
        csv_defense = profile.get("defense_rating", 70)
        csv_midfield = profile.get("midfield_rating", 70)
        csv_avg_for = profile.get("avg_goals_for", 1.2)
        csv_avg_against = profile.get("avg_goals_against", 1.1)
        csv_xg = round(csv_avg_for * 0.88, 2)
        csv_xga = round(csv_avg_against * 1.1, 2)

        if static_team:
            result["attack_rating"] = round(result["attack_rating"] * 0.70 + csv_attack * 0.30)
            result["defense_rating"] = round(result["defense_rating"] * 0.70 + csv_defense * 0.30)
            result["midfield_rating"] = round(result["midfield_rating"] * 0.70 + csv_midfield * 0.30)
            result["avg_goals_scored"] = round(result["avg_goals_scored"] * 0.60 + csv_avg_for * 0.40, 2)
            result["avg_goals_conceded"] = round(result["avg_goals_conceded"] * 0.60 + csv_avg_against * 0.40, 2)
            result["xG_per_match"] = round(result["xG_per_match"] * 0.60 + csv_xg * 0.40, 2)
            result["xGA_per_match"] = round(result["xGA_per_match"] * 0.60 + csv_xga * 0.40, 2)
            result["avg_possession"] = round(result["avg_possession"] * 0.70 + (45 + profile.get("win_rate", 50) * 0.15) * 0.30, 1)
            result["data_source"] = f"{result['data_source']} + CSV近期状态30%融合"
        else:
            result["attack_rating"] = csv_attack
            result["defense_rating"] = csv_defense
            result["midfield_rating"] = csv_midfield
            result["avg_goals_scored"] = csv_avg_for
            result["avg_goals_conceded"] = csv_avg_against
            result["xG_per_match"] = csv_xg
            result["xGA_per_match"] = csv_xga
            result["avg_possession"] = round(45 + profile.get("win_rate", 50) * 0.15, 1)
            result["data_source"] = "generated_csv_profile_only"
            result["profile_warning"] = "No static team anchor."

        result["recent_form"] = list(profile.get("recent_form", "")[-6:])
        result["games_analyzed"] = profile.get("games", 0)

        gf = profile.get("avg_goals_for", 1.2)
        ga = profile.get("avg_goals_against", 1.1)
        wr = profile.get("win_rate", 50)
        if not static_team:
            if gf > 2.2 and wr > 60:
                result["style"] = "控球进攻"
            elif gf > 1.8 and ga < 1.0:
                result["style"] = "高位压迫"
            elif ga < 0.8:
                result["style"] = "防守反击"
            elif wr > 70:
                result["style"] = "传控渗透"
            else:
                result["style"] = "均衡"

    if wc2022:
        if not static_team:
            result["fifa_rank"] = wc2022.get("fifa_rank")
            result["confederation"] = wc2022.get("confederation", "")
        result["logo"] = wc2022.get("logo", "")
        result["wc2022_data"] = wc2022.get("wc2022_data")
        if not profile and not static_team:
            result["attack_rating"] = wc2022.get("attack_rating", 70)
            result["defense_rating"] = wc2022.get("defense_rating", 70)
            result["midfield_rating"] = wc2022.get("midfield_rating", 70)
            result["avg_goals_scored"] = wc2022.get("avg_goals_scored", 1.2)
            result["avg_goals_conceded"] = wc2022.get("avg_goals_conceded", 1.1)
            result["xG_per_match"] = wc2022.get("xG_per_match", 1.0)
            result["xGA_per_match"] = wc2022.get("xGA_per_match", 1.0)
            result["recent_form"] = wc2022.get("recent_form", [])
            result["style"] = wc2022.get("style", "均衡")
            result["data_source"] = "2022世界杯数据"

    if thestats:
        xg = _first_present(thestats.get("xg_per_match"), thestats.get("xG_per_match"), thestats.get("xg"))
        xga = _first_present(thestats.get("xga_per_match"), thestats.get("xGA_per_match"), thestats.get("xga"))
        npxg = thestats.get("npxg_per_match")
        lineup_strength = thestats.get("lineup_strength")
        injury_count = thestats.get("injury_count")
        player_form = thestats.get("player_form")
        avg_player_rating = thestats.get("avg_player_rating")
        avg_starter_rating = thestats.get("avg_starter_rating")
        avg_attacker_rating = thestats.get("avg_attacker_rating")
        avg_midfielder_rating = thestats.get("avg_midfielder_rating")
        avg_defender_rating = thestats.get("avg_defender_rating")
        confirmed_lineups_count = thestats.get("confirmed_lineups_count")
        known_starters_count = thestats.get("known_starters_count")
        recent_formations = thestats.get("recent_formations")
        shots_per_match = thestats.get("shots_per_match")
        shots_on_target_per_match = thestats.get("shots_on_target_per_match")
        final_third_entries = thestats.get("final_third_entries_per_match")
        touches_in_box = thestats.get("touches_in_box_per_match")
        metrics_sample_matches = thestats.get("metrics_sample_matches") or 0
        metric_rows = thestats.get("metric_rows") or []
        xg_sample_matches = thestats.get("xg_sample_matches")
        xga_sample_matches = thestats.get("xga_sample_matches")
        if xg_sample_matches is None:
            xg_sample_matches = _valid_metric_count(metric_rows, "xg")
        if xga_sample_matches is None:
            xga_sample_matches = _valid_metric_count(metric_rows, "xga")
        if not metric_rows and xg is not None:
            xg_sample_matches = metrics_sample_matches
        if not metric_rows and xga is not None:
            xga_sample_matches = metrics_sample_matches
        xg, xg_quality = _clean_xg_metric(xg, xg_sample_matches, npxg)
        xga, xga_quality = _clean_xg_metric(xga, xga_sample_matches)

        if xg is not None:
            xg_value = float(xg)
            result["xG_per_match"] = round(xg_value, 2)
            result["attack_rating"] = round(result["attack_rating"] * 0.75 + min(95, 45 + xg_value * 22) * 0.25)
        if xga is not None:
            xga_value = float(xga)
            result["xGA_per_match"] = round(xga_value, 2)
            result["defense_rating"] = round(result["defense_rating"] * 0.75 + max(45, 95 - xga_value * 24) * 0.25)
        if lineup_strength is not None:
            result["midfield_rating"] = round(result["midfield_rating"] * 0.85 + float(lineup_strength) * 0.15)
        elif final_third_entries is not None:
            result["midfield_rating"] = round(result["midfield_rating"] * 0.9 + min(95, 45 + float(final_third_entries) * 0.8) * 0.1)
        if avg_attacker_rating is not None:
            result["attack_rating"] = round(result["attack_rating"] * 0.9 + min(95, float(avg_attacker_rating) * 12.5) * 0.1)
        if avg_midfielder_rating is not None:
            result["midfield_rating"] = round(result["midfield_rating"] * 0.9 + min(95, float(avg_midfielder_rating) * 12.5) * 0.1)
        if avg_defender_rating is not None:
            result["defense_rating"] = round(result["defense_rating"] * 0.9 + min(95, float(avg_defender_rating) * 12.5) * 0.1)
        if thestats.get("avg_possession") is not None:
            result["avg_possession"] = round(float(thestats.get("avg_possession")), 1)
        if injury_count is not None:
            penalty = min(8, float(injury_count) * 1.5)
            result["attack_rating"] = max(45, round(result["attack_rating"] - penalty))
            result["defense_rating"] = max(45, round(result["defense_rating"] - penalty * 0.8))

        quality_score = _thestats_quality_score(thestats)
        result["advanced_inputs"] = {
            "xg": xg,
            "xga": xga,
            "xg_quality": xg_quality,
            "xga_quality": xga_quality,
            "xg_source_quality": thestats.get("xg_source_quality"),
            "data_quality_score": quality_score,
            "xg_sample_matches": xg_sample_matches,
            "xga_sample_matches": xga_sample_matches,
            "lineup_strength": lineup_strength,
            "injury_count": injury_count,
            "player_form": player_form,
            "avg_player_rating": avg_player_rating,
            "avg_starter_rating": avg_starter_rating,
            "avg_attacker_rating": avg_attacker_rating,
            "avg_midfielder_rating": avg_midfielder_rating,
            "avg_defender_rating": avg_defender_rating,
            "confirmed_lineups_count": confirmed_lineups_count,
            "known_starters_count": known_starters_count,
            "recent_formations": recent_formations,
            "shots_per_match": shots_per_match,
            "shots_on_target_per_match": shots_on_target_per_match,
            "final_third_entries_per_match": final_third_entries,
            "touches_in_box_per_match": touches_in_box,
            "metrics_sample_matches": metrics_sample_matches,
            "avg_possession": thestats.get("avg_possession"),
            "source": "TheStatsAPI",
        }
        result["data_source"] = f"{result['data_source']} + TheStatsAPI扩展数据" if result["data_source"] != "无历史数据" else "TheStatsAPI扩展数据"

    return result


def get_all_team_names():
    schedule = _load_wc2026_schedule()
    if schedule and schedule.get("groups"):
        teams = set()
        for g_name, team_list in schedule["groups"].items():
            for t in team_list:
                teams.add(t)
        return sorted(teams)
    profiles = _load_team_profiles()
    return sorted([p["name"] for p in profiles if p.get("games", 0) >= 10])


def get_schedule_data():
    schedule = _load_wc2026_schedule()
    if schedule:
        return schedule
    return {"tournament": "2026 FIFA World Cup", "hosts": [], "matches": [], "groups": {}}


def save_cache(name, data):
    path = os.path.join(CACHE_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _today_news_cache_name():
    return f"live_news_{NEWS_PROVIDER}_{datetime.now().strftime('%Y%m%d')}.json"


def _news_category(title, description):
    text = f"{title} {description}".lower()
    if any(k in text for k in ["schedule", "fixture", "赛程", "开球", "赛历"]):
        return "赛程"
    if any(k in text for k in ["team", "squad", "player", "injury", "球队", "阵容", "球员", "伤病"]):
        return "球队"
    if any(k in text for k in ["data", "ai", "technology", "数据", "科技", "模型"]):
        return "数据"
    return "赛事"


def _has_chinese_text(value):
    return any("\u4e00" <= char <= "\u9fff" for char in value or "")


def _is_relevant_football_news(article):
    title = (article.get("title") or "").lower()
    description = (article.get("description") or article.get("content") or "").lower()
    title_terms = ["fifa", "world cup", "worldcup", "世界杯", "足球", "国际足联", "世预赛", "预选赛", "国家队", "football", "soccer", "usmnt", "qualification", "qualifier", "national team"]
    context_terms = ["2026", "fifa", "world cup", "世界杯", "足球", "国际足联", "世预赛", "预选赛", "国家队", "football", "soccer"]
    blocked_terms = ["odds", "bets", "betting", "picks", "wager", "prediction", "predictions", "赔率", "投注", "下注", "竞猜", "cricket", "t20", "icc", "rugby"]
    combined = f"{title} {description}"
    return _has_chinese_text(article.get("title") or "") and not any(term in combined for term in blocked_terms) and any(term in title for term in title_terms) and any(term in combined for term in context_terms)


def _dedupe_news_articles(articles):
    seen = set()
    result = []
    for article in articles:
        title_key = " ".join((article.get("title") or "").lower().split())
        if not title_key or title_key in seen:
            continue
        seen.add(title_key)
        result.append(article)
    return result


def _normalize_bing_news_article(article, index):
    title = article.get("name") or "未命名新闻"
    description = article.get("description") or ""
    provider = article.get("provider") or []
    source = provider[0].get("name") if provider and isinstance(provider[0], dict) else "Bing News"
    published_at = article.get("datePublished") or ""
    date_text = published_at[:10] if published_at else datetime.now().strftime("%Y-%m-%d")
    return {
        "id": f"bing-{date_text}-{index}",
        "title": title,
        "summary": description[:220] if description else "暂无摘要，请点击原文查看详情。",
        "image": "/static/img/news-placeholder.svg",
        "original_image": article.get("image", {}).get("thumbnail", {}).get("contentUrl", "") if isinstance(article.get("image"), dict) else "",
        "source": source,
        "date": date_text,
        "published_at": published_at,
        "category": _news_category(title, description),
        "url": article.get("url") or "",
        "is_live": True,
    }


def _local_news_fallback():
    path = os.path.join(BASE_DIR, "data", "news.json")
    if not os.path.exists(path):
        return {"provider": "local", "query": BING_NEWS_QUERY, "news": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"provider": "local", "query": BING_NEWS_QUERY, "news": []}
    news = data.get("news", []) if isinstance(data, dict) else []
    return {
        "provider": "local",
        "query": BING_NEWS_QUERY,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "news": news[:NEWS_MAX_RESULTS],
    }


def _strip_google_news_source(title):
    if " - " not in title:
        return title, ""
    headline, source = title.rsplit(" - ", 1)
    return headline.strip(), source.strip()


def _clean_news_summary(value):
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())
    return text


def _normalize_rss_news_item(item, index):
    raw_title = item.findtext("title") or "未命名新闻"
    title, source_from_title = _strip_google_news_source(raw_title)
    description = item.findtext("description") or ""
    link = item.findtext("link") or ""
    published_at = item.findtext("pubDate") or ""
    date_text = datetime.now().strftime("%Y-%m-%d")
    if published_at:
        try:
            parsed = datetime.strptime(published_at[:25], "%a, %d %b %Y %H:%M:%S")
            date_text = parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass
    source = item.findtext("source") or source_from_title or "RSS"
    summary = _clean_news_summary(description)
    return {
        "id": f"rss-{date_text}-{index}",
        "title": title,
        "summary": summary[:220] if summary else "暂无摘要，请点击原文查看详情。",
        "image": "/static/img/news-placeholder.svg",
        "original_image": "",
        "source": source,
        "date": date_text,
        "published_at": published_at,
        "category": _news_category(title, summary),
        "url": link,
        "is_live": True,
    }


def _fetch_rss_news_articles():
    articles = []
    for feed_url in NEWS_RSS_FEEDS:
        if not feed_url:
            continue
        request = urllib.request.Request(feed_url, headers={
            "User-Agent": "WorldSoccerAI/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml",
        })
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
            root = ET.fromstring(raw)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ET.ParseError):
            continue

        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else root.findall(".//item")
        for item in items:
            normalized = _normalize_rss_news_item(item, len(articles) + 1)
            if _is_relevant_football_news(normalized):
                articles.append(normalized)
            if len(articles) >= NEWS_MAX_RESULTS:
                break
        if len(articles) >= NEWS_MAX_RESULTS:
            break

    articles = _dedupe_news_articles(articles)
    if not articles:
        return None

    return {
        "provider": "google-news-rss",
        "query": BING_NEWS_QUERY,
        "language": BING_NEWS_MARKET,
        "country": BING_NEWS_MARKET,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "news": articles[:NEWS_MAX_RESULTS],
    }


def _fetch_bing_news_articles():
    if not BING_NEWS_API_KEY:
        return None

    params = {
        "q": BING_NEWS_QUERY,
        "mkt": BING_NEWS_MARKET,
        "freshness": BING_NEWS_FRESHNESS,
        "count": NEWS_MAX_RESULTS,
        "textFormat": "Raw",
        "safeSearch": "Strict",
    }
    url = BING_NEWS_API_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={
        "X-BingApis-SDK": "true",
        "X-RapidAPI-Key": BING_NEWS_API_KEY,
        "X-RapidAPI-Host": BING_NEWS_API_HOST,
        "User-Agent": "WorldSoccerAI/1.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        return None

    articles = []
    for item in raw.get("value", []):
        normalized = _normalize_bing_news_article(item, len(articles) + 1)
        if _is_relevant_football_news(normalized):
            articles.append(normalized)
        if len(articles) >= NEWS_MAX_RESULTS:
            break

    articles = _dedupe_news_articles(articles)
    if not articles:
        return None

    return {
        "provider": "bing-news-search",
        "query": BING_NEWS_QUERY,
        "language": BING_NEWS_MARKET,
        "country": BING_NEWS_MARKET,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "news": articles[:NEWS_MAX_RESULTS],
    }


def get_news_data():
    today_cache = _today_news_cache_name()
    cached_today = load_cache(today_cache)
    if cached_today:
        return cached_today

    live_news = _fetch_bing_news_articles()
    if live_news:
        save_cache(today_cache, live_news)
        save_cache("live_news_latest.json", live_news)
        return live_news

    rss_news = _fetch_rss_news_articles()
    if rss_news:
        save_cache(today_cache, rss_news)
        save_cache("live_news_latest.json", rss_news)
        return rss_news

    return _local_news_fallback()


def normalize_form(form_list):
    points = 0
    for result in form_list:
        if result == "W":
            points += 3
        elif result == "D":
            points += 1
    max_points = len(form_list) * 3
    return points / max_points if max_points > 0 else 0


def calculate_strength_score(team):
    """v4 综合实力分: 60% Elo + 20% 攻防统计 + 20% 近期状态"""
    elo_score = team.get("elo_score", 50)
    attack = team.get("attack_rating", 70)
    defense = team.get("defense_rating", 70)
    midfield = team.get("midfield_rating", 70)
    games = team.get("games_analyzed", 0)

    stats_score = (attack * 0.4 + defense * 0.3 + midfield * 0.3)

    form_norm = normalize_form(team.get("recent_form", []))
    confidence = min(1.0, games / 15)
    form_score = form_norm * 100

    score = (elo_score * 0.60 +
             stats_score * 0.20 +
             form_score * confidence * 0.20)
    return round(score, 2)


def _predict_probs_from_elo(home_elo, away_elo, h2h_data=None, params=None):
    params = params or get_model_calibration()["params"]
    home_advantage = params["home_advantage"]
    elo_scale = params["elo_scale"]
    draw_base = params["draw_base"]
    draw_width = params["draw_width"]

    elo_diff = (home_elo + home_advantage) - away_elo
    home_vs_away = 1.0 / (1.0 + 10 ** (-elo_diff / elo_scale))
    draw_prob = max(0.08, min(0.32, draw_base * (1 - min(abs(elo_diff), draw_width) / draw_width)))
    decisive_pool = 1.0 - draw_prob
    home_prob = home_vs_away * decisive_pool
    away_prob = (1.0 - home_vs_away) * decisive_pool

    if h2h_data and h2h_data.get("total", 0) >= params["h2h_min_matches"]:
        total = h2h_data["total"]
        h2h_weight = min(params["h2h_max_weight"], total / 30.0)
        h2h_dates = []
        for match in h2h_data.get("all_matches") or h2h_data.get("last_5") or []:
            parsed = _parse_date(match.get("date"))
            if parsed:
                h2h_dates.append(parsed)
        if h2h_dates:
            age_years = max(0, (datetime.now().date() - max(h2h_dates)).days / 365.25)
            if age_years > 10:
                h2h_weight = min(h2h_weight, 0.02)
            elif age_years > 5:
                h2h_weight *= max(0.25, 1 - (age_years - 5) / 5 * 0.75)
        h2h_home = h2h_data.get("home_wins", 0) / total
        h2h_draw = h2h_data.get("draws", 0) / total
        h2h_away = h2h_data.get("away_wins", 0) / total
        home_prob = home_prob * (1 - h2h_weight) + h2h_home * h2h_weight
        draw_prob = draw_prob * (1 - h2h_weight) + h2h_draw * h2h_weight
        away_prob = away_prob * (1 - h2h_weight) + h2h_away * h2h_weight

    total = home_prob + draw_prob + away_prob
    return {
        "home": max(0.01, min(0.98, home_prob / total)),
        "draw": max(0.01, min(0.98, draw_prob / total)),
        "away": max(0.01, min(0.98, away_prob / total)),
    }


def _match_actual_result(match):
    if match["home_goals"] > match["away_goals"]:
        return "home"
    if match["home_goals"] < match["away_goals"]:
        return "away"
    return "draw"


def _season_of(match):
    try:
        return int(str(match.get("season", 0))[:4])
    except (ValueError, TypeError):
        return 0


def _update_elo_pair(elo, match_count, match, params):
    home = match["home_team"]
    away = match["away_team"]
    hg = match["home_goals"]
    ag = match["away_goals"]

    comp_weight = COMPETITION_WEIGHTS.get(match.get("league_name", ""), 0.6)
    time_weight = SEASON_WEIGHTS.get(_season_of(match), 0.7)
    k_value = 32 * comp_weight * time_weight
    goal_diff = abs(hg - ag)
    if goal_diff > 0:
        k_value *= 1.0 + 0.2 * math.log(1 + goal_diff)

    expected_home = 1.0 / (1.0 + 10 ** (((elo[away]) - (elo[home] + params["home_advantage"])) / params["elo_scale"]))
    if hg > ag:
        actual_home = 1.0
    elif hg < ag:
        actual_home = 0.0
    else:
        actual_home = 0.5

    k_home = k_value * (1 + max(0, (30 - match_count[home]) / 30)) if match_count[home] < 30 else k_value
    k_away = k_value * (1 + max(0, (30 - match_count[away]) / 30)) if match_count[away] < 30 else k_value
    elo[home] += k_home * (actual_home - expected_home)
    elo[away] += k_away * ((1 - actual_home) - (1 - expected_home))
    match_count[home] += 1
    match_count[away] += 1


def _h2h_key(home, away):
    return " || ".join(sorted([home, away]))


def _get_rolling_h2h(h2h_store, home, away):
    data = h2h_store.get(_h2h_key(home, away))
    if not data:
        return None
    home_wins = data.get(home, 0)
    away_wins = data.get(away, 0)
    return {
        "total": data["total"],
        "home_wins": home_wins,
        "draws": data["draws"],
        "away_wins": away_wins,
    }


def _update_rolling_h2h(h2h_store, match):
    home = match["home_team"]
    away = match["away_team"]
    key = _h2h_key(home, away)
    if key not in h2h_store:
        h2h_store[key] = {"total": 0, "draws": 0, home: 0, away: 0}
    h2h_store[key]["total"] += 1
    h2h_store[key].setdefault(home, 0)
    h2h_store[key].setdefault(away, 0)
    if match["home_goals"] > match["away_goals"]:
        h2h_store[key][home] += 1
    elif match["home_goals"] < match["away_goals"]:
        h2h_store[key][away] += 1
    else:
        h2h_store[key]["draws"] += 1


def _evaluate_params(matches, params):
    elo = defaultdict(lambda: 1500.0)
    match_count = defaultdict(int)
    h2h_store = {}

    train_matches = [m for m in matches if _season_of(m) < 2024]
    test_matches = [m for m in matches if _season_of(m) == 2024]

    for m in train_matches:
        _update_elo_pair(elo, match_count, m, params)
        _update_rolling_h2h(h2h_store, m)

    log_loss = 0.0
    brier = 0.0
    correct = 0
    tested = 0

    for m in test_matches:
        probs = _predict_probs_from_elo(elo[m["home_team"]], elo[m["away_team"]], _get_rolling_h2h(h2h_store, m["home_team"], m["away_team"]), params)
        actual = _match_actual_result(m)
        log_loss -= math.log(max(0.01, probs[actual]))
        brier += sum((probs[k] - (1.0 if k == actual else 0.0)) ** 2 for k in ["home", "draw", "away"])
        if max(probs, key=probs.get) == actual:
            correct += 1
        tested += 1
        _update_elo_pair(elo, match_count, m, params)
        _update_rolling_h2h(h2h_store, m)

    if tested == 0:
        return {"log_loss": 99, "brier_score": 99, "accuracy": 0, "matches": 0}
    return {
        "log_loss": round(log_loss / tested, 4),
        "brier_score": round(brier / tested, 4),
        "accuracy": round(correct / tested * 100, 1),
        "matches": tested,
    }


def get_model_calibration():
    """优先使用 TheStatsAPI 2025-2026 非友谊赛搜索出的最新参数；没有文件时回退到2024回测搜索。"""
    global _model_calibration
    if _model_calibration is not None:
        return _model_calibration

    v44_path = os.path.join(BASE_DIR, "outputs", "model_calibration_v4_4_thestats_out.json")
    if os.path.exists(v44_path):
        try:
            with open(v44_path, "r", encoding="utf-8") as f:
                v44 = json.load(f)
            chosen = v44.get("best_accuracy") or v44.get("best_balanced")
            if chosen and chosen.get("params") and chosen.get("metrics"):
                _model_calibration = {
                    "version": "v4.5 TheStatsAPI quality + Dixon-Coles calibration",
                    "method": "使用2025-2026 TheStatsAPI非友谊赛回测集搜索最高Accuracy参数，包含数据质量降权与Dixon-Coles比分模型融合",
                    "params": chosen["params"],
                    "metrics": chosen["metrics"],
                    "baseline_metrics": (v44.get("current") or {}).get("metrics", {}),
                }
                return _model_calibration
        except (OSError, json.JSONDecodeError):
            pass

    matches = _load_all_matches()
    candidate_params = []
    for home_advantage in [35, 45, 55, 65]:
        for draw_base in [0.24, 0.27, 0.30]:
            for draw_width in [650, 750, 850]:
                for h2h_max_weight in [0.10, 0.15, 0.20]:
                    p = dict(DEFAULT_MODEL_PARAMS)
                    p.update({
                        "home_advantage": home_advantage,
                        "draw_base": draw_base,
                        "draw_width": draw_width,
                        "h2h_max_weight": h2h_max_weight,
                    })
                    candidate_params.append(p)

    best_params = dict(DEFAULT_MODEL_PARAMS)
    best_metrics = _evaluate_params(matches, best_params)
    for params in candidate_params:
        metrics = _evaluate_params(matches, params)
        if metrics["log_loss"] < best_metrics["log_loss"]:
            best_params = params
            best_metrics = metrics

    baseline = _evaluate_params(matches, DEFAULT_MODEL_PARAMS)
    _model_calibration = {
        "version": "v4.2 backtested calibration",
        "method": "2022-2023训练，2024验证，按Log Loss选择概率参数",
        "params": best_params,
        "metrics": best_metrics,
        "baseline_metrics": baseline,
    }
    return _model_calibration


def _safe_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _clamp(value, low, high):
    return max(low, min(high, value))


def _parse_date(value):
    if not value:
        return None
    text = str(value).strip()
    for candidate in (text, text[:10]):
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    return None


def load_recent_friendlies():
    """source provider: API-Football; source endpoint: fixtures; target competition: Friendlies/International Friendlies."""
    global _recent_friendlies_cache
    if _recent_friendlies_cache is None:
        _recent_friendlies_cache = load_cache("recent_friendlies_2025_2026.json") or {}
    return _recent_friendlies_cache


def load_qualification_matches():
    """source provider: local_csv/API-Football; source endpoint: qualification_matches.json / fixtures."""
    global _qualification_matches_cache
    if _qualification_matches_cache is None:
        raw = load_cache("qualification_matches.json") or {}
        if isinstance(raw, dict):
            _qualification_matches_cache = raw
        elif isinstance(raw, list):
            _qualification_matches_cache = {"meta": {"source": "legacy_list"}, "matches": raw}
        else:
            _qualification_matches_cache = {}
    return _qualification_matches_cache


def _empty_friendlies_agent(team_name, warning):
    return {
        "team": team_name,
        "elo_delta": 0.0,
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
        },
        "confidence": "none",
        "warning": warning,
        "adjustment_cap": 12,
        "opponent_strength_adjusted": False,
        "warning_if_many_matches_vs_low_strength_opponents": "",
        "source": None,
    }


def _empty_qualification_agent(team_name, warning):
    return {
        "team": team_name,
        "elo_delta": 0.0,
        "summary": {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "confidence": "none"},
        "confidence": "none",
        "warning": warning,
        "adjustment_cap": 25,
        "opponent_strength_adjusted": False,
        "warning_if_many_matches_vs_low_strength_opponents": "",
        "source": None,
    }


def _opponent_strength_for_adjustment(match, team_name):
    home = match.get("home_team", "")
    away = match.get("away_team", "")
    opponent = away if _same_team_name(home, team_name) else home
    opponent_elo = _safe_float(match.get("opponent_elo"))
    if opponent_elo is None:
        static_opponent = get_static_team(opponent)
        opponent_elo = calculate_static_elo_anchor(static_opponent) if static_opponent else None
    if opponent_elo is None:
        opponent_elo = 1450
    return opponent, opponent_elo


def _strength_factor_from_elo(opponent_elo):
    return _clamp((opponent_elo - 1320) / 360, 0.45, 1.20)


def calculate_qualification_adjustment(team_name, match_date=None):
    cache = load_qualification_matches()
    meta = cache.get("meta", {}) if isinstance(cache, dict) else {}
    matches = cache.get("matches", []) if isinstance(cache, dict) else []
    if not matches:
        return _empty_qualification_agent(team_name, meta.get("warning") or "No qualification cache available.")

    anchor_date = _parse_date(match_date) or datetime.now().date()
    summary = {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "confidence": "none"}
    total_score = 0.0
    used = []
    low_strength_matches = 0
    for match in matches:
        home = match.get("home_team", "")
        away = match.get("away_team", "")
        if not (_same_team_name(home, team_name) or _same_team_name(away, team_name)):
            continue
        hg = _safe_float(match.get("home_goals"))
        ag = _safe_float(match.get("away_goals"))
        if hg is None or ag is None:
            continue
        is_home = _same_team_name(home, team_name)
        gf = hg if is_home else ag
        ga = ag if is_home else hg
        result = "W" if gf > ga else "D" if gf == ga else "L"
        result_score = 1 if result == "W" else 0 if result == "D" else -1
        opponent, opponent_elo = _opponent_strength_for_adjustment(match, team_name)
        opponent_factor = _strength_factor_from_elo(opponent_elo)
        if opponent_elo < 1450:
            low_strength_matches += 1
        raw_goal_bonus = (gf - ga) * 0.16
        goal_bonus_limit = 0.3 if opponent_elo < 1450 and raw_goal_bonus > 0 else 0.65
        goal_bonus = _clamp(raw_goal_bonus, -0.65, goal_bonus_limit)
        played_at = _parse_date(match.get("date"))
        if played_at and anchor_date:
            days_ago = max(0, (anchor_date - played_at).days)
            time_decay = _clamp(1.0 - days_ago / 900.0, 0.45, 1.0)
        else:
            time_decay = 0.45
        score = (result_score + goal_bonus) * opponent_factor * time_decay
        total_score += score
        summary["matches"] += 1
        summary["goals_for"] += int(gf)
        summary["goals_against"] += int(ga)
        if result == "W":
            summary["wins"] += 1
        elif result == "D":
            summary["draws"] += 1
        else:
            summary["losses"] += 1
        used.append({
            **match,
            "team_result": result,
            "match_score": round(score, 3),
            "time_decay": round(time_decay, 2),
            "opponent": opponent,
            "opponent_elo_used": round(opponent_elo, 1),
            "opponent_strength_factor": round(opponent_factor, 2),
            "goal_bonus": round(goal_bonus, 2),
        })

    if not used:
        return _empty_qualification_agent(team_name, meta.get("warning") or "No qualification matches for this team.")
    summary["confidence"] = "low" if len(used) < 3 else "medium" if len(used) < 8 else "high"
    elo_delta = round(_clamp(total_score * 7, -25, 25), 1)
    summary["elo_delta"] = elo_delta
    low_strength_warning = ""
    if used and low_strength_matches / len(used) >= 0.5:
        low_strength_warning = "Many qualification matches were against low-strength opponents; positive adjustments were strength-discounted."
    return {
        "team": team_name,
        "elo_delta": elo_delta,
        "summary": summary,
        "matches": used[-10:],
        "confidence": summary["confidence"],
        "warning": meta.get("warning", ""),
        "adjustment_cap": 25,
        "opponent_strength_adjusted": True,
        "warning_if_many_matches_vs_low_strength_opponents": low_strength_warning,
        "source": {
            "source_provider": meta.get("source_provider"),
            "source_endpoint": meta.get("source_endpoint"),
        },
    }


def calculate_recent_friendlies_adjustment(team_name, match_date=None):
    cache = load_recent_friendlies()
    warning = "No recent friendlies cache available."
    if not cache:
        return _empty_friendlies_agent(team_name, warning)

    meta = cache.get("meta", {}) if isinstance(cache, dict) else {}
    teams = cache.get("teams", {}) if isinstance(cache, dict) else {}
    team_key = next((variant for variant in _name_variants(team_name) if variant in teams), None)
    team_data = teams.get(team_key) if team_key else None
    if not team_data:
        return _empty_friendlies_agent(team_name, meta.get("warning") or "No recent friendlies data for this team.")

    anchor_date = _parse_date(match_date) or datetime.now().date()
    total_score = 0.0
    used_matches = []
    low_strength_matches = 0
    for match in team_data.get("matches", []) or []:
        match_status = (match.get("status") or "").upper()
        if match_status and match_status not in {"FT", "AET", "PEN", "MATCH FINISHED"}:
            continue
        result = (match.get("result") or "").upper()
        result_score = 1 if result == "W" else 0 if result == "D" else -1 if result == "L" else 0
        goal_diff = _safe_float(match.get("goal_diff"))
        if goal_diff is None:
            goal_diff = (_safe_float(match.get("goals_for")) or 0) - (_safe_float(match.get("goals_against")) or 0)
        opponent_name = _normalize_name(match.get("opponent", "") or match.get("opponent_team", ""))
        opponent_elo = _safe_float(match.get("opponent_elo"))
        if opponent_elo is None:
            static_opponent = get_static_team(opponent_name)
            opponent_elo = calculate_static_elo_anchor(static_opponent) if static_opponent else None
        if opponent_elo is None:
            opponent_elo = 1450
        opponent_factor = _strength_factor_from_elo(opponent_elo)
        if opponent_elo < 1450:
            low_strength_matches += 1
        raw_goal_bonus = goal_diff * 0.12
        goal_bonus_limit = 0.3 if opponent_elo < 1450 and raw_goal_bonus > 0 else 0.45
        goal_bonus = _clamp(raw_goal_bonus, -0.45, goal_bonus_limit)
        played_at = _parse_date(match.get("date"))
        if played_at and anchor_date:
            days_ago = max(0, (anchor_date - played_at).days)
            time_decay = _clamp(1.0 - days_ago / 540.0, 0.4, 1.0)
        else:
            time_decay = 0.4
        match_score = (result_score + goal_bonus) * opponent_factor * time_decay
        total_score += match_score
        used_matches.append({
            **match,
            "match_score": round(match_score, 3),
            "time_decay": round(time_decay, 2),
            "opponent_elo_used": round(opponent_elo, 1),
            "opponent_strength_factor": round(opponent_factor, 2),
            "goal_bonus": round(goal_bonus, 2),
        })

    elo_delta = round(_clamp(total_score * 4, -12, 12), 1)
    summary = dict(team_data.get("summary") or {})
    summary.update({
        "matches": len(used_matches),
        "elo_delta": elo_delta,
        "confidence": summary.get("confidence") or ("low" if len(used_matches) < 3 else "medium"),
    })
    if not used_matches:
        summary["confidence"] = "none"
        return _empty_friendlies_agent(team_name, meta.get("warning") or "No finished recent friendlies for this team.")

    return {
        "team": team_name,
        "elo_delta": elo_delta,
        "summary": summary,
        "matches": used_matches[:10],
        "confidence": summary.get("confidence"),
        "warning": meta.get("warning", ""),
        "adjustment_cap": 12,
        "opponent_strength_adjusted": True,
        "warning_if_many_matches_vs_low_strength_opponents": "Many recent friendlies were against low-strength opponents; positive adjustments were strength-discounted." if used_matches and low_strength_matches / len(used_matches) >= 0.5 else "",
        "source": {
            "source_provider": meta.get("source_provider", "API-Football"),
            "source_endpoint": meta.get("source_endpoint", "fixtures"),
            "date_from": meta.get("date_from"),
            "date_to": meta.get("date_to"),
        },
    }


def load_market_odds():
    """source provider: API-Football/TheStatsAPI/The Odds API; source endpoint: odds."""
    global _market_odds_cache
    if _market_odds_cache is None:
        _market_odds_cache = load_cache("market_odds.json") or {}
    return _market_odds_cache


def _empty_market_odds_signal(warning):
    return {
        "available": False,
        "source": None,
        "bookmaker_count": 0,
        "raw_odds": None,
        "normalized_implied_probabilities": None,
        "market_weight": 0.0,
        "warning": warning,
        "disclaimer": "盘口数据仅用于概率校准和市场预期参考，不构成投注建议。",
    }


def _match_market_key(home_team, away_team, match_date=None):
    date_text = str(match_date or "")[:10]
    return f"{_normalize_name(home_team)}|{_normalize_name(away_team)}|{date_text}"


def _market_key_variants(home_team, away_team, match_date=None):
    date_text = str(match_date or "")[:10]
    keys = []
    for home in _name_variants(home_team):
        for away in _name_variants(away_team):
            key = f"{home}|{away}|{date_text}"
            if key not in keys:
                keys.append(key)
    return keys


def _find_market_odds_entry(cache, home_team, away_team, match_date=None):
    matches = cache.get("matches", {}) if isinstance(cache, dict) else {}
    if not isinstance(matches, dict) or not matches:
        return None
    keys = _market_key_variants(home_team, away_team, match_date) + _market_key_variants(away_team, home_team, match_date)
    for key in keys:
        if key in matches:
            entry = dict(matches[key])
            if any(key.startswith(f"{away_variant}|") for away_variant in _name_variants(away_team)):
                entry["swapped"] = True
            return entry
    for entry in matches.values():
        if not isinstance(entry, dict):
            continue
        eh = entry.get("home_team", "")
        ea = entry.get("away_team", "")
        entry_day = _parse_date(entry.get("date"))
        requested_day = _parse_date(match_date)
        same_date = not match_date or str(entry.get("date", ""))[:10] == str(match_date)[:10]
        if not same_date and entry_day and requested_day:
            # The Odds API commence_time may be UTC/venue-local while the local
            # schedule page displays Beijing date, so adjacent dates can refer
            # to the same kickoff.
            same_date = abs((entry_day - requested_day).days) <= 1
        if same_date and _same_team_name(eh, home_team) and _same_team_name(ea, away_team):
            return entry
        if same_date and _same_team_name(eh, away_team) and _same_team_name(ea, home_team):
            swapped = dict(entry)
            swapped["swapped"] = True
            return swapped
    return None


def calculate_market_odds_signal(home_team, away_team, match_date=None):
    cache = load_market_odds()
    if not cache:
        return _empty_market_odds_signal("No market odds cache available.")

    meta = cache.get("meta", {}) if isinstance(cache, dict) else {}
    entry = _find_market_odds_entry(cache, home_team, away_team, match_date)
    if not entry:
        return _empty_market_odds_signal(meta.get("warning") or "No market odds for this match.")

    one_x_two = ((entry.get("markets") or {}).get("1x2") or {})
    average = dict(one_x_two.get("average") or {})
    if entry.get("swapped"):
        average["home"], average["away"] = average.get("away"), average.get("home")

    home_odds = _safe_float(average.get("home"))
    draw_odds = _safe_float(average.get("draw"))
    away_odds = _safe_float(average.get("away"))
    if not home_odds or not draw_odds or not away_odds:
        return _empty_market_odds_signal(meta.get("warning") or "Market odds cache has no valid 1X2 average odds.")

    raw_home = 1 / home_odds
    raw_draw = 1 / draw_odds
    raw_away = 1 / away_odds
    total = raw_home + raw_draw + raw_away
    implied = {
        "home": round(raw_home / total, 4),
        "draw": round(raw_draw / total, 4),
        "away": round(raw_away / total, 4),
    }
    bookmaker_count = int(_safe_float(entry.get("bookmaker_count")) or len(one_x_two.get("bookmakers") or []))
    days_to_match = None
    fetched_at = _parse_date(entry.get("fetched_at"))
    match_day = _parse_date(entry.get("date") or match_date)
    if fetched_at and match_day:
        days_to_match = abs((match_day - fetched_at).days)

    if bookmaker_count >= 20:
        market_weight = 0.30
    elif bookmaker_count >= 10:
        market_weight = 0.25
    elif bookmaker_count >= 5:
        market_weight = 0.20
    elif bookmaker_count >= 2:
        market_weight = 0.10
    else:
        market_weight = 0.0

    return {
        "available": True,
        "source": {
            "source_provider": meta.get("source_provider"),
            "source_endpoint": meta.get("source_endpoint", "odds"),
            "odds_format": meta.get("odds_format", "decimal"),
            "markets": meta.get("markets", ["1X2"]),
        },
        "bookmaker_count": bookmaker_count,
        "raw_odds": {"home": home_odds, "draw": draw_odds, "away": away_odds},
        "normalized_implied_probabilities": implied,
        "market_weight": market_weight,
        "base_market_weight": market_weight,
        "warning": meta.get("warning", ""),
        "disclaimer": "盘口数据仅用于概率校准和市场预期参考，不构成投注建议。",
    }


def calculate_advanced_elo_adjustment(team):
    """将 TheStatsAPI 高级特征折算为小幅 Elo 修正，避免覆盖历史 Elo 主模型。"""
    adv = team.get("advanced_inputs", {}) or {}
    adjustment = 0.0
    factors = []
    data_quality = _safe_float(adv.get("data_quality_score"))
    if data_quality is None:
        data_quality = _advanced_sample_confidence(adv.get("metrics_sample_matches"))

    xg = _safe_float(adv.get("xg"))
    xga = _safe_float(adv.get("xga"))
    xg_confidence = min(_advanced_sample_confidence(adv.get("xg_sample_matches")), _advanced_sample_confidence(adv.get("xga_sample_matches")))
    xg_confidence *= data_quality * _xg_source_confidence(adv)
    if adv.get("xg_quality") == "npxg_proxy" or adv.get("xga_quality") == "npxg_proxy":
        xg_confidence *= 0.65
    if xg is not None and xga is not None and xg_confidence > 0:
        xg_edge = max(-1.2, min(1.2, xg - xga))
        delta = xg_edge * 18 * xg_confidence
        adjustment += delta
        factors.append({"factor": "xG净值", "value": round(xg - xga, 2), "elo_delta": round(delta, 1), "confidence": round(xg_confidence, 2), "data_quality": round(data_quality, 2)})

    starter = _safe_float(adv.get("avg_starter_rating"))
    if starter is not None:
        delta = max(-18, min(18, (starter - 6.7) * 22)) * data_quality
        adjustment += delta
        factors.append({"factor": "首发评分", "value": round(starter, 2), "elo_delta": round(delta, 1), "data_quality": round(data_quality, 2)})

    player_form = _safe_float(adv.get("avg_player_rating") or adv.get("player_form"))
    if player_form is not None:
        delta = max(-12, min(12, (player_form - 6.6) * 16)) * data_quality
        adjustment += delta
        factors.append({"factor": "球员状态", "value": round(player_form, 2), "elo_delta": round(delta, 1), "data_quality": round(data_quality, 2)})

    shots = _safe_float(adv.get("shots_per_match"))
    if shots is not None:
        delta = max(-10, min(10, (shots - 11.0) * 1.4)) * data_quality
        adjustment += delta
        factors.append({"factor": "场均射门", "value": round(shots, 1), "elo_delta": round(delta, 1), "data_quality": round(data_quality, 2)})

    touches = _safe_float(adv.get("touches_in_box_per_match"))
    if touches is not None:
        delta = max(-8, min(8, (touches - 18.0) * 0.6)) * data_quality
        adjustment += delta
        factors.append({"factor": "禁区触球", "value": round(touches, 1), "elo_delta": round(delta, 1), "data_quality": round(data_quality, 2)})

    sample = _safe_float(adv.get("metrics_sample_matches")) or 0
    confidence = _advanced_sample_confidence(sample)
    final_adjustment = max(-55, min(55, adjustment * confidence))

    return {
        "elo_delta": round(final_adjustment, 1),
        "confidence": round(confidence, 2),
        "factors": factors,
    }


def _load_schedule_matches():
    schedule = _load_wc2026_schedule() or {}
    matches = schedule.get("matches", []) if isinstance(schedule, dict) else []
    if matches:
        return matches
    path = os.path.join(BASE_DIR, "data", "schedule.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("matches", []) if isinstance(data, dict) else []


HOST_TEAM_COUNTRIES = {
    "美国": "USA",
    "加拿大": "Canada",
    "墨西哥": "Mexico",
}

VENUE_CONTEXTS = [
    {"keys": ["阿兹特克", "墨西哥城", "Azteca"], "stadium": "阿兹特克体育场", "city": "墨西哥城", "country": "Mexico", "altitude_m": 2240, "climate_note": "高海拔，对不适应球队的体能和恢复有额外压力。"},
    {"keys": ["AT&T", "阿灵顿", "Dallas"], "stadium": "AT&T Stadium", "city": "阿灵顿", "country": "USA", "altitude_m": 184, "climate_note": "可控屋顶环境，天气直接影响较低。"},
    {"keys": ["玫瑰碗", "洛杉矶", "Rose Bowl"], "stadium": "玫瑰碗", "city": "洛杉矶", "country": "USA", "altitude_m": 263, "climate_note": "温暖干燥环境，天气影响通常中低。"},
    {"keys": ["吉列", "波士顿", "Gillette"], "stadium": "吉列体育场", "city": "波士顿", "country": "USA", "altitude_m": 88, "climate_note": "东北部气候，需关注临近天气。"},
    {"keys": ["大都会", "纽约", "新泽西", "MetLife"], "stadium": "大都会体育场", "city": "纽约/新泽西", "country": "USA", "altitude_m": 2, "climate_note": "低海拔露天环境，需关注降雨和风。"},
    {"keys": ["李维斯", "旧金山", "Levi"], "stadium": "李维斯体育场", "city": "旧金山湾区", "country": "USA", "altitude_m": 2, "climate_note": "低海拔，温和气候。"},
    {"keys": ["BC体育场", "温哥华", "BC Place"], "stadium": "BC体育场", "city": "温哥华", "country": "Canada", "altitude_m": 70, "climate_note": "可控屋顶环境，天气直接影响较低。"},
    {"keys": ["BMO", "多伦多"], "stadium": "BMO体育场", "city": "多伦多", "country": "Canada", "altitude_m": 76, "climate_note": "低海拔，需关注临近天气。"},
    {"keys": ["费城", "林肯"], "stadium": "林肯金融体育场", "city": "费城", "country": "USA", "altitude_m": 12, "climate_note": "低海拔露天环境。"},
    {"keys": ["休斯顿", "NRG"], "stadium": "NRG体育场", "city": "休斯顿", "country": "USA", "altitude_m": 13, "climate_note": "湿热风险较高，但屋顶可降低天气影响。"},
    {"keys": ["亚特兰大", "梅赛德斯"], "stadium": "梅赛德斯-奔驰体育场", "city": "亚特兰大", "country": "USA", "altitude_m": 320, "climate_note": "可控屋顶环境，天气直接影响较低。"},
    {"keys": ["迈阿密", "硬石"], "stadium": "硬石体育场", "city": "迈阿密", "country": "USA", "altitude_m": 2, "climate_note": "湿热风险较高，体能消耗可能增加。"},
]


def _venue_context(venue):
    text = venue or ""
    for item in VENUE_CONTEXTS:
        if any(key.lower() in text.lower() for key in item["keys"]):
            return {k: v for k, v in item.items() if k != "keys"}
    return {"stadium": venue or "未知场地", "city": "未知", "country": "Unknown", "altitude_m": None, "climate_note": "暂无稳定场地资料。"}


def _find_scheduled_match(home_name, away_name):
    for match in _load_schedule_matches():
        mh = match.get("home_team", "")
        ma = match.get("away_team", "")
        if _same_team_name(mh, home_name) and _same_team_name(ma, away_name):
            return match
        if _same_team_name(mh, away_name) and _same_team_name(ma, home_name):
            swapped = dict(match)
            swapped["home_team"], swapped["away_team"] = match.get("away_team"), match.get("home_team")
            swapped["home_flag"], swapped["away_flag"] = match.get("away_flag"), match.get("home_flag")
            swapped["swapped_from_schedule"] = True
            return swapped
    return None


def search_match_context(home_team, away_team):
    """赛前情境 Agent：使用本地赛程、场地气候表和本地伤停备注补充预测。"""
    home_name = home_team.get("name", "")
    away_name = away_team.get("name", "")
    match = _find_scheduled_match(home_name, away_name)
    venue = _venue_context(match.get("venue") if match else "")
    home_country = HOST_TEAM_COUNTRIES.get(home_name)
    away_country = HOST_TEAM_COUNTRIES.get(away_name)
    home_delta = 0.0
    away_delta = 0.0
    factors = []

    if match:
        factors.append({"factor": "赛程匹配", "value": f"{match.get('date', '未知日期')} · {match.get('venue', '未知场地')}", "home_elo_delta": 0, "away_elo_delta": 0})
    else:
        factors.append({"factor": "赛程匹配", "value": "未在本地2026赛程中找到完全匹配，按中立/未知场地处理", "home_elo_delta": 0, "away_elo_delta": 0})

    if home_country and venue.get("country") == home_country:
        home_delta += 20
        factors.append({"factor": "东道主真实主场", "value": f"{home_name}在{venue.get('city')}比赛", "home_elo_delta": 20, "away_elo_delta": 0})
    if away_country and venue.get("country") == away_country:
        away_delta += 20
        factors.append({"factor": "东道主真实主场", "value": f"{away_name}在{venue.get('city')}比赛", "home_elo_delta": 0, "away_elo_delta": 20})

    altitude = venue.get("altitude_m")
    if altitude and altitude >= 1500:
        if home_country and venue.get("country") == home_country:
            home_delta += 12
            away_delta -= 6
            factors.append({"factor": "高海拔适应", "value": f"{venue.get('city')}约{altitude}米", "home_elo_delta": 12, "away_elo_delta": -6})
        elif away_country and venue.get("country") == away_country:
            away_delta += 12
            home_delta -= 6
            factors.append({"factor": "高海拔适应", "value": f"{venue.get('city')}约{altitude}米", "home_elo_delta": -6, "away_elo_delta": 12})
        else:
            factors.append({"factor": "高海拔场地", "value": f"{venue.get('city')}约{altitude}米，双方均按中性影响处理", "home_elo_delta": 0, "away_elo_delta": 0})

    if venue.get("city") in {"迈阿密", "休斯顿"}:
        factors.append({"factor": "湿热风险", "value": venue.get("climate_note"), "home_elo_delta": 0, "away_elo_delta": 0})

    home_injuries = home_team.get("injuries") or []
    away_injuries = away_team.get("injuries") or []
    if home_injuries:
        factors.append({"factor": f"{home_name}本地伤停备注", "value": "；".join(home_injuries), "home_elo_delta": 0, "away_elo_delta": 0})
    if away_injuries:
        factors.append({"factor": f"{away_name}本地伤停备注", "value": "；".join(away_injuries), "home_elo_delta": 0, "away_elo_delta": 0})

    home_delta = max(-35, min(35, home_delta))
    away_delta = max(-35, min(35, away_delta))
    confidence = 0.65 if match else 0.25
    if not match:
        confidence = 0.2

    return {
        "enabled": True,
        "status": "local_context_agent",
        "match_found": bool(match),
        "match": match,
        "venue": venue,
        "weather": {
            "status": "local_climate_reference",
            "note": venue.get("climate_note") or "暂无本地场地气候备注。",
            "source_provider": "local_static_venue_context",
            "source_endpoint": "ai_engine.VENUE_CONTEXTS",
            "affects_probability": False,
        },
        "team_news": {
            "status": "local_static_notes",
            "note": f"{home_name}: {'；'.join(home_injuries) if home_injuries else '本地表暂无伤停备注'}；{away_name}: {'；'.join(away_injuries) if away_injuries else '本地表暂无伤停备注'}",
            "source_provider": "local_static_team_profiles",
            "source_endpoint": "data/teams.json injuries",
            "affects_probability": False,
        },
        "adjustment": {
            "home_elo_delta": round(home_delta, 1),
            "away_elo_delta": round(away_delta, 1),
            "confidence": confidence,
        },
        "factors": factors,
        "sources": ["data/cache/wc2026_schedule.json", "内置2026世界杯场地城市/海拔表", "data/teams.json injuries"],
        "note": "当前使用本地赛程、场地气候和本地伤停备注；天气和伤停备注只作为解释信息，未自动修正概率。",
    }


def get_effective_home_advantage(home_team, away_team, match_context):
    """Return fixed home advantage for the Elo probability layer.

    World Cup 2026 matches are treated as neutral for the fixed home slot.
    Real host-country venue effects are handled separately by
    search_match_context().adjustment so they do not get double counted.
    """
    match_context = match_context or {}
    match = match_context.get("match") or {}
    if match:
        return 0.0
    return 0.0


def calculate_match_result_prob(home_team, away_team, h2h_data=None):
    """v4.5 胜平负概率: base profile + qualification + friendlies + H2H + venue + optional TheStats + score blend + market blend"""
    home_base_elo = home_team.get("elo_rating", 1450)
    away_base_elo = away_team.get("elo_rating", 1450)
    home_adv = calculate_advanced_elo_adjustment(home_team)
    away_adv = calculate_advanced_elo_adjustment(away_team)
    context_agent = search_match_context(home_team, away_team)
    match = context_agent.get("match") or {}
    match_date = match.get("date")
    home_qualification = calculate_qualification_adjustment(home_team["name"], match_date)
    away_qualification = calculate_qualification_adjustment(away_team["name"], match_date)
    home_friendlies = calculate_recent_friendlies_adjustment(home_team["name"], match_date)
    away_friendlies = calculate_recent_friendlies_adjustment(away_team["name"], match_date)
    context_adj = context_agent.get("adjustment", {})
    home_elo = home_base_elo + home_qualification["elo_delta"] + home_friendlies["elo_delta"] + context_adj.get("home_elo_delta", 0) + home_adv["elo_delta"]
    away_elo = away_base_elo + away_qualification["elo_delta"] + away_friendlies["elo_delta"] + context_adj.get("away_elo_delta", 0) + away_adv["elo_delta"]
    params = dict(get_model_calibration()["params"])
    original_home_advantage = params.get("home_advantage", 0)
    params["home_advantage"] = get_effective_home_advantage(home_team, away_team, context_agent)
    params["h2h_min_matches"] = 3

    normalized_h2h = None
    h2h_applied = False
    if h2h_data and h2h_data.get("total", 0) >= params["h2h_min_matches"]:
        is_home_is_a = _same_team_name(h2h_data.get("team_a", ""), home_team["name"])
        normalized_h2h = {
            "total": h2h_data["total"],
            "home_wins": h2h_data["a_wins"] if is_home_is_a else h2h_data["b_wins"],
            "draws": h2h_data["draws"],
            "away_wins": h2h_data["b_wins"] if is_home_is_a else h2h_data["a_wins"],
            "all_matches": h2h_data.get("all_matches") or h2h_data.get("last_5") or [],
        }
        h2h_applied = True

    probs = _predict_probs_from_elo(home_elo, away_elo, normalized_h2h, params)
    probs = _blend_score_model_probs(home_team, away_team, probs, params)
    market_signal = calculate_market_odds_signal(home_team["name"], away_team["name"], match_date)
    if market_signal.get("market_weight", 0) > 0 and market_signal.get("normalized_implied_probabilities"):
        weight = market_signal["market_weight"]
        implied = market_signal["normalized_implied_probabilities"]
        model_top = max(probs, key=probs.get)
        market_top = max(implied, key=implied.get)
        conflict_delta = max(abs(probs[key] - implied[key]) for key in ("home", "draw", "away"))
        if model_top != market_top and conflict_delta > 0.20:
            weight = min(0.45, weight + 0.10)
            market_signal["market_conflict_adjustment"] = 0.10
        else:
            market_signal["market_conflict_adjustment"] = 0.0
        market_signal["effective_market_weight"] = weight
        market_signal["model_top_before_market"] = model_top
        market_signal["market_top"] = market_top
        market_signal["model_market_max_delta"] = round(conflict_delta, 4)
        probs = {
            "home": probs["home"] * (1 - weight) + implied["home"] * weight,
            "draw": probs["draw"] * (1 - weight) + implied["draw"] * weight,
            "away": probs["away"] * (1 - weight) + implied["away"] * weight,
        }
        total_prob = sum(probs.values())
        probs = {key: probs[key] / total_prob for key in probs}
    home_prob = round(probs["home"] * 100, 1)
    draw_prob = round(probs["draw"] * 100, 1)
    away_prob = round(100 - home_prob - draw_prob, 1)

    if away_prob < 0:
        away_prob = 0.0
        total = home_prob + draw_prob
        home_prob = round(home_prob / total * 100, 1)
        draw_prob = round(100 - home_prob, 1)

    return {
        "home_win": home_prob,
        "draw": draw_prob,
        "away_win": away_prob,
        "probability_sum": round(home_prob + draw_prob + away_prob, 1),
        "qualification_agent": {
            "home_team_delta": home_qualification["elo_delta"],
            "away_team_delta": away_qualification["elo_delta"],
            "home_summary": home_qualification.get("summary"),
            "away_summary": away_qualification.get("summary"),
            "home_warning": home_qualification.get("warning"),
            "away_warning": away_qualification.get("warning"),
            "confidence": {
                "home": home_qualification.get("confidence"),
                "away": away_qualification.get("confidence"),
            },
            "warning": home_qualification.get("warning") or away_qualification.get("warning") or "",
            "source": home_qualification.get("source") or away_qualification.get("source"),
        },
        "recent_friendlies_agent": {
            "home_team_delta": home_friendlies["elo_delta"],
            "away_team_delta": away_friendlies["elo_delta"],
            "home_summary": home_friendlies.get("summary"),
            "away_summary": away_friendlies.get("summary"),
            "home_warning": home_friendlies.get("warning"),
            "away_warning": away_friendlies.get("warning"),
            "confidence": {
                "home": home_friendlies.get("confidence"),
                "away": away_friendlies.get("confidence"),
            },
            "warning": home_friendlies.get("warning") or away_friendlies.get("warning") or "",
            "source": home_friendlies.get("source") or away_friendlies.get("source"),
        },
        "market_odds_agent": market_signal,
        "advanced_adjustment": {
            "home": home_adv,
            "away": away_adv,
            "context_agent": context_agent,
            "home_adjusted_elo": round(home_elo, 1),
            "away_adjusted_elo": round(away_elo, 1),
            "home_base_elo": round(home_base_elo, 1),
            "away_base_elo": round(away_base_elo, 1),
            "original_home_advantage": original_home_advantage,
            "effective_home_advantage": params["home_advantage"],
            "h2h_applied_to_probability": h2h_applied,
            "h2h_min_matches": params["h2h_min_matches"],
        }
    }


def calculate_goal_range(home_team, away_team):
    home_xg = home_team.get("xG_per_match", 1.5)
    away_xg = away_team.get("xG_per_match", 1.2)
    ha = home_team.get("attack_rating", 70) / 100
    aa = away_team.get("attack_rating", 70) / 100
    hd = home_team.get("defense_rating", 70) / 100
    ad = away_team.get("defense_rating", 70) / 100

    eg_home = (home_xg * ad + ha * 1.2) / 2
    eg_away = (away_xg * hd + aa * 1.0) / 2
    te = eg_home + eg_away

    r01 = round(max(0, min(40, (3.0 - te) * 15)), 1)
    r23 = round(max(0, min(50, 30 - abs(te - 2.5) * 10)), 1)
    r4p = round(max(0, min(35, (te - 2.0) * 12)), 1)

    total = r01 + r23 + r4p
    if total > 0:
        r01 = round(r01 / total * 100, 1)
        r23 = round(r23 / total * 100, 1)
        r4p = round(100 - r01 - r23, 1)

    return {"0-1球": r01, "2-3球": r23, "4球及以上": r4p, "预期总进球": round(te, 1)}


def analyze_tactical_style(home_team, away_team):
    home_style = home_team.get("style", "均衡")
    away_style = away_team.get("style", "均衡")
    hp = home_team.get("avg_possession", 48)
    ap = away_team.get("avg_possession", 48)

    styles = {
        "控球进攻": "以控球为核心，通过短传渗透和中场组织构建进攻体系。",
        "快速反击": "防守时保持紧凑阵型，夺回球权后利用速度快速推进。",
        "技术渗透": "依靠球员个人技术和小范围配合，打法灵活多变。",
        "高位压迫": "从前场开始高强度压迫，迫使对方失误。",
        "防守反击": "以稳固防守为基础，发动高效反击。",
        "传控渗透": "通过精准传球和耐心传导渗透防线，强调控制力。",
        "均衡": "攻守平衡，根据比赛局势灵活调整战术重心。",
    }

    if hp > ap + 8:
        pos_tip = f"数据表明{home_team['name']}更擅长控球，预计控球率{hp}%对{100-hp}%"
    elif ap > hp + 8:
        pos_tip = f"数据表明{away_team['name']}更擅长控球，预计控球率{ap}%对{100-ap}%"
    else:
        pos_tip = f"双方控球能力接近，预计各占50%左右"

    return {
        "home_team": home_team["name"], "home_style": home_style,
        "home_style_analysis": styles.get(home_style, "打法多样灵活。"),
        "away_team": away_team["name"], "away_style": away_style,
        "away_style_analysis": styles.get(away_style, "打法多样灵活。"),
        "possession_analysis": pos_tip,
        "style_conflict_analysis": _analyze_style_clash(home_team, away_team),
    }


def _analyze_style_clash(home_team, away_team):
    hs = home_team.get("style", "")
    a_s = away_team.get("style", "")
    h = home_team["name"]
    a = away_team["name"]

    if hs == "高位压迫" and a_s == "防守反击":
        return f"{h}的高位压迫 vs {a}的防守反击，两队战术风格形成鲜明对比，比赛节奏控制将是关键。"
    elif a_s == "高位压迫" and hs == "防守反击":
        return f"{a}的高位压迫 vs {h}的防守反击，比赛节奏控制将是关键。"
    elif hs == a_s and hs in ["控球进攻", "传控渗透"]:
        return f"双方都为控球型打法，中场争夺将异常激烈。"
    else:
        return f"{hs}与{a_s}的对碰将使比赛充满战术看点。"


def compare_teams_strength(home_team, away_team):
    h_data = home_team.get("wc2022_data") or {}
    a_data = away_team.get("wc2022_data") or {}
    h_games = home_team.get("games_analyzed", 0)
    a_games = away_team.get("games_analyzed", 0)

    dims = {
        "Elo评分": {"home": round(home_team.get("elo_rating", 1500), 1), "away": round(away_team.get("elo_rating", 1500), 1)},
        "进攻能力": {"home": home_team.get("attack_rating", 70), "away": away_team.get("attack_rating", 70)},
        "防守能力": {"home": home_team.get("defense_rating", 70), "away": away_team.get("defense_rating", 70)},
        "中场控制": {"home": home_team.get("midfield_rating", 70), "away": away_team.get("midfield_rating", 70)},
        "场均进球(历史)": {"home": round(home_team.get("avg_goals_scored", 0), 1), "away": round(away_team.get("avg_goals_scored", 0), 1)},
        "场均失球(历史)": {"home": round(home_team.get("avg_goals_conceded", 0), 1), "away": round(away_team.get("avg_goals_conceded", 0), 1)},
        "近期状态指数": {"home": round(normalize_form(home_team.get("recent_form", [])) * 100, 1), "away": round(normalize_form(away_team.get("recent_form", [])) * 100, 1)},
    }

    home_adv = home_team.get("advanced_inputs", {}) or {}
    away_adv = away_team.get("advanced_inputs", {}) or {}
    if home_adv.get("metrics_sample_matches") or away_adv.get("metrics_sample_matches"):
        dims.update({
            "xG(近况)": {"home": home_adv.get("xg"), "away": away_adv.get("xg")},
            "xG有效样本数": {"home": home_adv.get("xg_sample_matches", 0), "away": away_adv.get("xg_sample_matches", 0)},
            "xGA(近况)": {"home": home_adv.get("xga"), "away": away_adv.get("xga")},
            "xGA有效样本数": {"home": home_adv.get("xga_sample_matches", 0), "away": away_adv.get("xga_sample_matches", 0)},
            "场均射门(TheStats)": {"home": home_adv.get("shots_per_match"), "away": away_adv.get("shots_per_match")},
            "控球率(TheStats)": {"home": home_adv.get("avg_possession"), "away": away_adv.get("avg_possession")},
            "禁区触球(TheStats)": {"home": home_adv.get("touches_in_box_per_match"), "away": away_adv.get("touches_in_box_per_match")},
            "高级指标样本": {"home": home_adv.get("metrics_sample_matches"), "away": away_adv.get("metrics_sample_matches")},
            "TheStats数据质量": {"home": home_adv.get("data_quality_score"), "away": away_adv.get("data_quality_score")},
            "首发评分(TheStats)": {"home": home_adv.get("avg_starter_rating"), "away": away_adv.get("avg_starter_rating")},
            "球员状态评分": {"home": home_adv.get("avg_player_rating"), "away": away_adv.get("avg_player_rating")},
            "前锋评分": {"home": home_adv.get("avg_attacker_rating"), "away": away_adv.get("avg_attacker_rating")},
            "中场评分": {"home": home_adv.get("avg_midfielder_rating"), "away": away_adv.get("avg_midfielder_rating")},
            "后卫评分": {"home": home_adv.get("avg_defender_rating"), "away": away_adv.get("avg_defender_rating")},
            "已确认阵容样本": {"home": home_adv.get("confirmed_lineups_count"), "away": away_adv.get("confirmed_lineups_count")},
        })

    h_s = calculate_strength_score(home_team)
    a_s = calculate_strength_score(away_team)

    return {
        "home_team": home_team["name"], "away_team": away_team["name"],
        "home_overall_score": h_s, "away_overall_score": a_s,
        "score_gap": round(h_s - a_s, 2),
        "dimensions": dims,
        "home_data_source": home_team.get("data_source", ""),
        "away_data_source": away_team.get("data_source", ""),
        "home_elo": home_team.get("elo_rating"),
        "away_elo": away_team.get("elo_rating"),
        "wc2022_home": h_data, "wc2022_away": a_data,
        "conclusion": _conclusion(home_team, away_team, h_s, a_s, h_games, a_games),
    }


def _conclusion(home_team, away_team, h_s, a_s, hg, ag):
    h = home_team["name"]
    a = away_team["name"]
    gap = h_s - a_s

    if gap > 15:
        return f"{h}在综合数据(Elo+统计)上占优。分析仅供参考。"
    elif gap > 5:
        return f"{h}略占上风，{a}同样具备竞争力。"
    elif gap > -5:
        return f"两队实力接近，胜负难料。"
    elif gap > -15:
        return f"{a}略占上风，{h}仍具备竞争力。"
    else:
        return f"{a}在综合数据(Elo+统计)上占优。分析仅供参考。"


def _poisson_probability(lam, goals):
    lam = max(0.05, min(4.5, lam))
    return math.exp(-lam) * (lam ** goals) / math.factorial(goals)


def _dixon_coles_adjustment(home_goals, away_goals, home_lambda, away_lambda, rho):
    if home_goals == 0 and away_goals == 0:
        return 1 - home_lambda * away_lambda * rho
    if home_goals == 0 and away_goals == 1:
        return 1 + home_lambda * rho
    if home_goals == 1 and away_goals == 0:
        return 1 + away_lambda * rho
    if home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0


def _score_outcome_probs(home_lambda, away_lambda, rho=-0.05, max_goals=7):
    totals = {"home": 0.0, "draw": 0.0, "away": 0.0}
    total_probability = 0.0
    for hg in range(0, max_goals + 1):
        for ag in range(0, max_goals + 1):
            probability = _poisson_probability(home_lambda, hg) * _poisson_probability(away_lambda, ag)
            probability *= max(0.2, _dixon_coles_adjustment(hg, ag, home_lambda, away_lambda, rho))
            total_probability += probability
            if hg > ag:
                totals["home"] += probability
            elif hg == ag:
                totals["draw"] += probability
            else:
                totals["away"] += probability
    if total_probability <= 0:
        return {"home": 0.33, "draw": 0.34, "away": 0.33}
    return {key: value / total_probability for key, value in totals.items()}


def _blend_score_model_probs(home_team, away_team, elo_probs, params):
    weight = _safe_float(params.get("score_model_weight")) or 0.0
    if weight <= 0:
        return elo_probs
    proxy_result = {
        "home_win": elo_probs["home"] * 100,
        "draw": elo_probs["draw"] * 100,
        "away_win": elo_probs["away"] * 100,
    }
    expected = estimate_expected_goals(home_team, away_team, proxy_result)
    score_probs = _score_outcome_probs(expected["home_xg"], expected["away_xg"], params.get("dixon_coles_rho", -0.05))
    blended = {key: elo_probs[key] * (1 - weight) + score_probs[key] * weight for key in ("home", "draw", "away")}
    total = sum(blended.values())
    return {key: max(0.01, min(0.98, blended[key] / total)) for key in blended}


def estimate_expected_goals(home_team, away_team, result_prob):
    home_adv = home_team.get("advanced_inputs", {}) or {}
    away_adv = away_team.get("advanced_inputs", {}) or {}
    home_xg = _safe_float(home_adv.get("xg"))
    away_xg = _safe_float(away_adv.get("xg"))
    home_xga = _safe_float(home_adv.get("xga"))
    away_xga = _safe_float(away_adv.get("xga"))
    if home_xg is None:
        home_xg = home_team.get("xG_per_match", 1.45)
    if away_xg is None:
        away_xg = away_team.get("xG_per_match", 1.20)
    if home_xga is None:
        home_xga = home_team.get("avg_goals_conceded", 1.15)
    if away_xga is None:
        away_xga = away_team.get("avg_goals_conceded", 1.15)

    home_attack = home_team.get("attack_rating", 70) / 75
    away_attack = away_team.get("attack_rating", 70) / 75
    home_defense = home_team.get("defense_rating", 70) / 75
    away_defense = away_team.get("defense_rating", 70) / 75

    home_lambda = (home_xg * 0.48 + away_xga * 0.28 + home_attack * 1.15 * 0.16 + (2 - away_defense) * 0.55 * 0.08)
    away_lambda = (away_xg * 0.48 + home_xga * 0.28 + away_attack * 1.05 * 0.16 + (2 - home_defense) * 0.55 * 0.08)

    prob_gap = (result_prob.get("home_win", 33.3) - result_prob.get("away_win", 33.3)) / 100
    home_lambda += prob_gap * 0.35
    away_lambda -= prob_gap * 0.25

    return {
        "home_xg": round(max(0.2, min(3.8, home_lambda)), 2),
        "away_xg": round(max(0.2, min(3.8, away_lambda)), 2),
    }


def calculate_possible_scores(home_team, away_team, result_prob):
    expected = estimate_expected_goals(home_team, away_team, result_prob)
    home_lambda = expected["home_xg"]
    away_lambda = expected["away_xg"]
    score_probs = []

    params = get_model_calibration()["params"]
    rho = params.get("dixon_coles_rho", -0.05)
    for hg in range(0, 6):
        for ag in range(0, 6):
            probability = _poisson_probability(home_lambda, hg) * _poisson_probability(away_lambda, ag)
            probability *= max(0.2, _dixon_coles_adjustment(hg, ag, home_lambda, away_lambda, rho))
            if hg > ag:
                outcome = "主胜"
            elif hg == ag:
                outcome = "平局"
            else:
                outcome = "客胜"
            score_probs.append({
                "score": f"{hg}-{ag}",
                "home_goals": hg,
                "away_goals": ag,
                "outcome": outcome,
                "probability": probability,
            })

    outcome_targets = {
        "主胜": result_prob.get("home_win", 0) / 100,
        "平局": result_prob.get("draw", 0) / 100,
        "客胜": result_prob.get("away_win", 0) / 100,
    }
    outcome_totals = defaultdict(float)
    for item in score_probs:
        outcome_totals[item["outcome"]] += item["probability"]
    for item in score_probs:
        total = outcome_totals[item["outcome"]]
        if total > 0:
            item["probability"] = item["probability"] / total * outcome_targets[item["outcome"]]

    score_probs.sort(key=lambda x: x["probability"], reverse=True)

    def format_score(item):
        return {
            "score": item["score"],
            "home_goals": item["home_goals"],
            "away_goals": item["away_goals"],
            "outcome": item["outcome"],
            "probability": round(item["probability"] * 100, 1),
        }

    top_scores = [format_score(item) for item in score_probs[:6]]

    likely_outcome_key = max(
        [("主胜", result_prob.get("home_win", 0)), ("平局", result_prob.get("draw", 0)), ("客胜", result_prob.get("away_win", 0))],
        key=lambda item: item[1]
    )[0]
    outcome_scores = [format_score(s) for s in score_probs if s["outcome"] == likely_outcome_key][:3]

    return {
        "expected_goals": expected,
        "likely_outcome": likely_outcome_key,
        "top_scores": top_scores,
        "likely_outcome_scores": outcome_scores,
        "method": "Dixon-Coles修正Poisson比分分布 + v4.5胜平负概率校准",
        "note": "比分为概率分布中的高可能区间，不代表确定赛果。",
    }


def _fallback_llm_analysis(home_team, away_team, result_prob, possible_scores, strength_comp):
    likely = possible_scores["likely_outcome"]
    top = possible_scores["top_scores"][:3]
    top_text = "、".join([f"{s['score']}({s['probability']}%)" for s in top])
    if likely == "主胜":
        side = home_team["name"]
    elif likely == "客胜":
        side = away_team["name"]
    else:
        side = "双方战平"

    if LLM_API_KEY:
        provider = "local-fallback-after-llm-error"
        model = f"local-template（LLM调用失败：{LLM_LAST_ERROR or '未知错误'}）"
        config_note = f"已配置大模型，但本次调用失败，已回退本地模板。失败原因：{LLM_LAST_ERROR or '未知错误'}。"
    else:
        provider = "local-fallback"
        model = "local-template"
        config_note = "大模型未配置时使用本地模板解释；配置 API Key 后会自动启用大模型解读。"

    return {
        "enabled": False,
        "provider": provider,
        "model": model,
        "error": LLM_LAST_ERROR if LLM_API_KEY else "",
        "summary": f"v4.5模型倾向：{likely}，主胜{result_prob['home_win']}%、平局{result_prob['draw']}%、客胜{result_prob['away_win']}%。综合判断更接近{side}。",
        "score_view": f"可能比分区间优先关注：{top_text}。这些比分来自预期进球和泊松分布，不是确定比分。",
        "key_factors": [
            strength_comp.get("conclusion", "两队实力对比接近。"),
            f"预期进球：{home_team['name']} {possible_scores['expected_goals']['home_xg']}，{away_team['name']} {possible_scores['expected_goals']['away_xg']}。",
            config_note,
        ],
        "risk_note": "足球比赛受阵容、伤停、天气、裁判和临场状态影响，结果仅供数据分析参考。",
    }


def _extract_json_object(text):
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    if text.startswith("{"):
        return json.loads(text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError("LLM响应不是JSON")


def _llm_text(value, default=""):
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "；".join(_llm_text(item) for item in value if item is not None)
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            text = _llm_text(item)
            if text:
                parts.append(f"{key}：{text}")
        return "；".join(parts) if parts else default
    return str(value)


def _llm_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [_llm_text(item) for item in value if _llm_text(item)]
    if isinstance(value, dict):
        return [f"{key}：{_llm_text(item)}" for key, item in value.items() if _llm_text(item)]
    text = _llm_text(value)
    return [text] if text else []


def _mask_api_key(api_key):
    if not api_key:
        return "not set"
    if len(api_key) <= 10:
        return f"{api_key[:2]}***{api_key[-2:]}"
    return f"{api_key[:6]}...{api_key[-4:]}"


def _log_llm_debug(message):
    print(f"[LLM Debug] {message}")


def _call_openai_compatible_llm(payload):
    global LLM_LAST_ERROR
    LLM_LAST_ERROR = ""
    if not LLM_API_KEY:
        return None

    messages = [
        {
            "role": "system",
            "content": "你是专业足球数据分析师。只基于用户提供的v4.5模型结果解读，不得编造新数据。优先输出JSON，字段为summary、score_view、key_factors、risk_note；如果无法输出JSON，也可以直接输出一段中文解读。不要涉及市场交易相关建议。"
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False)
        }
    ]

    body_data = {
        "model": LLM_MODEL,
        "temperature": 0.3,
        "max_tokens": 700,
        "messages": messages,
    }
    request_url = f"{LLM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    _log_llm_debug(f"base_url={LLM_BASE_URL}")
    _log_llm_debug(f"request_url={request_url}")
    _log_llm_debug(f"model={LLM_MODEL}")
    _log_llm_debug(f"api_key={_mask_api_key(LLM_API_KEY)}")

    try:
        response = requests.post(
            request_url,
            headers=headers,
            json=body_data,
            timeout=LLM_TIMEOUT,
        )
        response_text = response.text.strip()
        _log_llm_debug(f"status_code={response.status_code}")
        if response.status_code >= 400:
            _log_llm_debug(f"error_body={response_text[:500]}")
            LLM_LAST_ERROR = f"HTTP {response.status_code} {response_text[:300]}".strip()
            return None
        if not response_text:
            LLM_LAST_ERROR = "大模型接口返回空响应"
            return None
        raw = json.loads(response_text)
        content = (raw.get("choices") or [{}])[0].get("message", {}).get("content")
        if content is None:
            content = (raw.get("choices") or [{}])[0].get("text")
        content = (content or "").strip()
        if not content:
            LLM_LAST_ERROR = "大模型返回内容为空"
            return None
        try:
            parsed = _extract_json_object(content)
            summary = _llm_text(parsed.get("summary"))
            score_view = _llm_text(parsed.get("score_view"))
            key_factors = _llm_list(parsed.get("key_factors"))
            risk_note = _llm_text(parsed.get("risk_note"))
        except (ValueError, json.JSONDecodeError):
            summary = content
            score_view = "大模型以自然语言方式完成了解读。"
            key_factors = []
            risk_note = "足球比赛受阵容、伤停、天气、裁判和临场状态影响，结果仅供数据分析参考。"
        return {
            "enabled": True,
            "provider": LLM_BASE_URL,
            "model": LLM_MODEL,
            "summary": summary,
            "score_view": score_view,
            "key_factors": key_factors,
            "risk_note": risk_note,
        }
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="ignore")[:300]
        except Exception:
            detail = ""
        LLM_LAST_ERROR = f"HTTP {exc.code} {detail}".strip()
    except urllib.error.URLError as exc:
        LLM_LAST_ERROR = f"网络错误：{exc.reason}"
    except requests.Timeout:
        LLM_LAST_ERROR = "请求超时"
    except requests.RequestException as exc:
        status_code = exc.response.status_code if exc.response is not None else "N/A"
        error_body = exc.response.text[:500] if exc.response is not None else str(exc)
        _log_llm_debug(f"status_code={status_code}")
        _log_llm_debug(f"error_body={error_body}")
        LLM_LAST_ERROR = f"请求失败：{exc}"
    except TimeoutError:
        LLM_LAST_ERROR = "请求超时"
    except json.JSONDecodeError as exc:
        LLM_LAST_ERROR = f"响应不是有效JSON：{exc.msg}"
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        LLM_LAST_ERROR = f"响应解析失败：{exc}"
    return None


def generate_llm_match_analysis(home_team, away_team, result_prob, possible_scores, tactical, strength_comp, h2h_summary, calibration, context_agent=None):
    raw_dimensions = strength_comp.get("dimensions") or []
    if isinstance(raw_dimensions, dict):
        compact_dimensions = list(raw_dimensions.values())[:12]
    else:
        compact_dimensions = raw_dimensions[:12]
    compact_scores = {
        "likely_outcome": possible_scores.get("likely_outcome"),
        "expected_goals": possible_scores.get("expected_goals"),
        "top_scores": (possible_scores.get("top_scores") or [])[:6],
        "likely_outcome_scores": (possible_scores.get("likely_outcome_scores") or [])[:3],
        "method": possible_scores.get("method"),
    }
    compact_h2h = None
    if h2h_summary:
        compact_h2h = {
            "total_matches": h2h_summary.get("total_matches"),
            "draws": h2h_summary.get("平局"),
            "avg_goals": h2h_summary.get("avg_goals"),
        }
    compact_context = None
    if context_agent:
        compact_context = {
            "match_found": context_agent.get("match_found"),
            "venue": context_agent.get("venue"),
            "adjustment": context_agent.get("adjustment"),
            "factors": context_agent.get("factors"),
            "weather_note": (context_agent.get("weather") or {}).get("note"),
            "team_news_note": (context_agent.get("team_news") or {}).get("note"),
        }
    payload = {
        "match": {"home_team": home_team["name"], "away_team": away_team["name"]},
        "v4_5_result_probability": {
            "home_win": result_prob["home_win"],
            "draw": result_prob["draw"],
            "away_win": result_prob["away_win"],
        },
        "possible_scores": compact_scores,
        "strength_comparison": {
            "home_score": strength_comp["home_overall_score"],
            "away_score": strength_comp["away_overall_score"],
            "score_gap": strength_comp["score_gap"],
            "conclusion": strength_comp["conclusion"],
            "dimensions": compact_dimensions,
        },
        "tactical_analysis": tactical,
        "pre_match_context_agent": compact_context,
        "h2h_history": compact_h2h,
        "model_calibration": {
            "version": calibration.get("version"),
            "accuracy": calibration.get("accuracy"),
            "log_loss": calibration.get("log_loss"),
        },
        "instruction": "用简洁中文说明胜平负倾向、可能比分和关键原因。不要使用投注术语。"
    }
    llm_result = _call_openai_compatible_llm(payload)
    if llm_result:
        return llm_result
    return _fallback_llm_analysis(home_team, away_team, result_prob, possible_scores, strength_comp)


def run_full_analysis(home_team_name, away_team_name):
    home_team = build_team_data(home_team_name)
    away_team = build_team_data(away_team_name)

    if not home_team:
        return {"error": f"未找到球队数据: {home_team_name}"}
    if not away_team:
        return {"error": f"未找到球队数据: {away_team_name}"}

    h2h = get_h2h(home_team_name, away_team_name)

    result_prob = calculate_match_result_prob(home_team, away_team, h2h)
    context_agent = (result_prob.get("advanced_adjustment") or {}).get("context_agent")
    goal_range = calculate_goal_range(home_team, away_team)
    possible_scores = calculate_possible_scores(home_team, away_team, result_prob)
    tactical = analyze_tactical_style(home_team, away_team)
    strength_comp = compare_teams_strength(home_team, away_team)

    h2h_summary = None
    if h2h:
        h2h_summary = {
            "total_matches": h2h["total"],
            f"{home_team_name}胜": h2h["a_wins"],
            "平局": h2h["draws"],
            f"{away_team_name}胜": h2h["b_wins"],
            "avg_goals": h2h["avg_goals"],
            "last_matches": h2h.get("last_5", []),
        }

    match_count = len(_load_all_matches())
    calibration = get_model_calibration()
    data_health = check_prediction_data_health()
    calibration_summary = {
        "version": calibration["version"],
        "method": calibration["method"],
        "validation_matches": calibration["metrics"]["matches"],
        "log_loss": calibration["metrics"]["log_loss"],
        "brier_score": calibration["metrics"]["brier_score"],
        "accuracy": calibration["metrics"]["accuracy"],
        "params": calibration["params"],
    }
    llm_analysis = generate_llm_match_analysis(home_team, away_team, result_prob, possible_scores, tactical, strength_comp, h2h_summary, calibration_summary, context_agent)

    return {
        "match": {"home_team": home_team_name, "away_team": away_team_name,
                   "home_flag": home_team.get("flag", ""), "away_flag": away_team.get("flag", ""),
                   "home_rank": home_team.get("fifa_rank") or "N/A",
                   "away_rank": away_team.get("fifa_rank") or "N/A"},
        "result_probability": result_prob,
        "possible_scores": possible_scores,
        "llm_analysis": llm_analysis,
        "goal_range_analysis": goal_range,
        "tactical_analysis": tactical,
        "strength_comparison": strength_comp,
        "h2h_history": h2h_summary,
        "model_calibration": calibration_summary,
        "context_agent": context_agent,
        "data_health": data_health,
        "data_warning": data_health.get("warning", ""),
        "data_source": f"API-Football预选赛/热身赛缓存 | 本地球队画像 | H2H缓存 | 最近热身赛缓存 | 市场预期信号缓存 | 赛前情境Agent | 当前优先比赛缓存 {match_count}场 | Elo评分 + 回测校准 | 2026 预测",
        "disclaimer": f"本分析优先基于世界杯预选赛、最近热身赛、本地球队画像、H2H、赛前情境和市场预期信号；TheStats 仅作为可选高级增强，缺失时不影响基础模型运行。缺少真实缓存时会明确降级到本地画像或默认占位。回测指标: Log Loss {calibration['metrics']['log_loss']}、Brier {calibration['metrics']['brier_score']}、样本 {calibration['metrics']['matches']} 场。结果为概率性分析，仅供参考。",
    }


def handle_invalid_request(text):
    blocked_keywords = [
        "比分预测", "精准比分", "买球", "下注", "投注",
        "赌球", "赔率", "竞猜", "推荐", "稳胆",
        "必赢", "必杀", "内幕", "内部消息",
        "bet", "gamble", "odds", "betting", "wager"
    ]
    text_lower = text.lower()
    for keyword in blocked_keywords:
        if keyword in text_lower:
            return {"error": True, "message": "我们仅提供合规的足球赛事数据分析与资讯服务，不涉及任何预测、投注相关内容。"}
    return None
