"""
Sync The Odds API market expectation signals into the local cache.

The script reads THE_ODDS_API_KEY from .env, requests real market data from
The Odds API v4, and writes data/cache/market_odds.json. It never fabricates
odds: empty responses, unsupported plans, and unmatched events all degrade to
an empty cache with a clear warning.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
ENV_PATH = os.path.join(BASE_DIR, ".env")
SPORT_KEY = "soccer_fifa_world_cup"
BASE_URL = "https://api.the-odds-api.com/v4"
SOURCE_ENDPOINT = f"/v4/sports/{SPORT_KEY}/odds"
REGIONS = ["eu", "uk"]
MARKETS = ["h2h", "spreads", "totals"]
ODDS_FORMAT = "decimal"
EMPTY_WARNING = f"No odds returned by The Odds API for {SPORT_KEY}. Market odds signal disabled."

CN_TO_EN = {
    "墨西哥": "Mexico",
    "南非": "South Africa",
    "韩国": "South Korea",
    "捷克": "Czechia",
    "加拿大": "Canada",
    "波黑": "Bosnia and Herzegovina",
    "美国": "USA",
    "巴拉圭": "Paraguay",
    "卡塔尔": "Qatar",
    "瑞士": "Switzerland",
    "巴西": "Brazil",
    "摩洛哥": "Morocco",
    "海地": "Haiti",
    "苏格兰": "Scotland",
    "澳大利亚": "Australia",
    "土耳其": "Turkey",
    "德国": "Germany",
    "库拉索": "Curaçao",
    "荷兰": "Netherlands",
    "日本": "Japan",
    "科特迪瓦": "Ivory Coast",
    "厄瓜多尔": "Ecuador",
    "瑞典": "Sweden",
    "突尼斯": "Tunisia",
    "西班牙": "Spain",
    "佛得角": "Cabo Verde",
    "比利时": "Belgium",
    "埃及": "Egypt",
    "沙特阿拉伯": "Saudi Arabia",
    "乌拉圭": "Uruguay",
    "伊朗": "Iran",
    "新西兰": "New Zealand",
    "法国": "France",
    "塞内加尔": "Senegal",
    "伊拉克": "Iraq",
    "挪威": "Norway",
    "阿根廷": "Argentina",
    "阿尔及利亚": "Algeria",
    "奥地利": "Austria",
    "约旦": "Jordan",
    "葡萄牙": "Portugal",
    "刚果民主共和国": "DR Congo",
    "乌兹别克斯坦": "Uzbekistan",
    "哥伦比亚": "Colombia",
    "英格兰": "England",
    "克罗地亚": "Croatia",
    "加纳": "Ghana",
    "巴拿马": "Panama",
}

ALIASES = {
    "bosnia": "bosnia and herzegovina",
    "bosnia-herzegovina": "bosnia and herzegovina",
    "bosnia & herzegovina": "bosnia and herzegovina",
    "cape verde": "cabo verde",
    "congo dr": "dr congo",
    "congo democratic republic": "dr congo",
    "democratic republic of congo": "dr congo",
    "cote d ivoire": "ivory coast",
    "côte d ivoire": "ivory coast",
    "curacao": "curaçao",
    "czech republic": "czechia",
    "iran islamic republic": "iran",
    "korea republic": "south korea",
    "republic of korea": "south korea",
    "south korea republic": "south korea",
    "turkiye": "turkey",
    "türkiye": "turkey",
    "united states": "usa",
    "united states of america": "usa",
    "us": "usa",
}


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, "market_odds.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[market_odds] wrote {path}")


def normalize_team_name(name):
    text = CN_TO_EN.get(str(name or "").strip(), str(name or "").strip())
    text = " ".join(text.lower().replace(".", "").replace(",", "").split())
    text = text.replace("'", "").replace("’", "")
    return ALIASES.get(text, text)


def display_team_name(name):
    return CN_TO_EN.get(str(name or "").strip(), str(name or "").strip())


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.fromisoformat(str(value)[:10]).date()
        except ValueError:
            return None


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def base_cache(generated_at, warning=None):
    return {
        "meta": {
            "source": "the_odds_api",
            "source_provider": "The Odds API",
            "source_endpoint": SOURCE_ENDPOINT,
            "generated_at": generated_at,
            "sport_key": SPORT_KEY,
            "regions": REGIONS,
            "markets": MARKETS,
            "odds_format": ODDS_FORMAT,
            "events_returned": 0,
            "matched_matches": 0,
            "unmatched_events": [],
            "requests_remaining": None,
            "requests_used": None,
            "warning": warning,
            "disclaimer": "盘口数据仅用于概率校准和市场预期参考，不构成投注建议。",
        },
        "matches": {},
    }


def schedule_candidates(match):
    dates = []
    for key in ("source_date_et", "date", "kickoff_bj"):
        parsed = parse_date(match.get(key))
        if parsed:
            dates.append(parsed)
    return dates


def load_schedule_index():
    schedule = load_json(os.path.join(CACHE_DIR, "wc2026_schedule.json"), {}) or {}
    entries = []
    for match in schedule.get("matches", []):
        home = display_team_name(match.get("home_team"))
        away = display_team_name(match.get("away_team"))
        entries.append({
            "home_team": home,
            "away_team": away,
            "home_norm": normalize_team_name(home),
            "away_norm": normalize_team_name(away),
            "dates": schedule_candidates(match),
            "match": match,
        })
    return entries


def find_schedule_match(event, schedule_entries):
    event_home = normalize_team_name(event.get("home_team"))
    event_away = normalize_team_name(event.get("away_team"))
    event_date = parse_date(event.get("commence_time"))
    if not event_home or not event_away or not event_date:
        return None

    best = None
    best_score = 99
    for entry in schedule_entries:
        same_order = entry["home_norm"] == event_home and entry["away_norm"] == event_away
        reversed_order = entry["home_norm"] == event_away and entry["away_norm"] == event_home
        if not (same_order or reversed_order):
            continue
        deltas = [abs((candidate - event_date).days) for candidate in entry["dates"]]
        if not deltas:
            continue
        score = min(deltas)
        if score <= 1 and score < best_score:
            best = dict(entry)
            best["reversed_order"] = reversed_order
            best_score = score
    return best


def request_the_odds_api(api_key):
    query = urllib.parse.urlencode({
        "apiKey": api_key,
        "regions": ",".join(REGIONS),
        "markets": ",".join(MARKETS),
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": "iso",
    })
    url = f"{BASE_URL}/sports/{SPORT_KEY}/odds?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "WorldCup2026MarketOddsSync/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        payload = json.loads(response.read().decode("utf-8"))
    return payload, headers


def market_by_key(bookmaker, key):
    for market in bookmaker.get("markets", []) or []:
        if market.get("key") == key:
            return market
    return None


def outcome_price(outcomes, name):
    target = normalize_team_name(name)
    for outcome in outcomes or []:
        if normalize_team_name(outcome.get("name")) == target:
            return outcome.get("price")
    return None


def parse_h2h(event, bookmaker, home_team, away_team):
    market = market_by_key(bookmaker, "h2h")
    if not market:
        return None
    outcomes = market.get("outcomes") or []
    home = outcome_price(outcomes, home_team)
    away = outcome_price(outcomes, away_team)
    draw = None
    for outcome in outcomes:
        if normalize_team_name(outcome.get("name")) == "draw":
            draw = outcome.get("price")
            break
    if home is None or draw is None or away is None:
        return None
    return {
        "name": bookmaker.get("title") or bookmaker.get("key") or "unknown",
        "home": float(home),
        "draw": float(draw),
        "away": float(away),
        "last_update": bookmaker.get("last_update"),
    }


def parse_spreads(bookmaker, home_team, away_team):
    market = market_by_key(bookmaker, "spreads")
    if not market:
        return None
    outcomes = market.get("outcomes") or []
    home = next((o for o in outcomes if normalize_team_name(o.get("name")) == normalize_team_name(home_team)), None)
    away = next((o for o in outcomes if normalize_team_name(o.get("name")) == normalize_team_name(away_team)), None)
    if not home or not away:
        return None
    return {
        "line": home.get("point"),
        "home_odds": home.get("price"),
        "away_odds": away.get("price"),
    }


def parse_totals(bookmaker):
    market = market_by_key(bookmaker, "totals")
    if not market:
        return None
    grouped = {}
    for outcome in market.get("outcomes") or []:
        point = outcome.get("point")
        if point is None:
            continue
        item = grouped.setdefault(float(point), {})
        name = str(outcome.get("name") or "").lower()
        if name == "over":
            item["over"] = outcome.get("price")
        elif name == "under":
            item["under"] = outcome.get("price")
    complete = [(line, prices) for line, prices in grouped.items() if "over" in prices and "under" in prices]
    if not complete:
        return None
    line, prices = min(complete, key=lambda item: abs(item[0] - 2.5))
    return {"line": line, "over": prices["over"], "under": prices["under"]}


def average_h2h(bookmakers):
    return {
        "home": round(sum(book["home"] for book in bookmakers) / len(bookmakers), 3),
        "draw": round(sum(book["draw"] for book in bookmakers) / len(bookmakers), 3),
        "away": round(sum(book["away"] for book in bookmakers) / len(bookmakers), 3),
    }


def event_to_cache_entry(event, schedule_match, fetched_at):
    home_team = schedule_match["home_team"]
    away_team = schedule_match["away_team"]
    h2h_books = []
    spread = None
    total = None
    for bookmaker in event.get("bookmakers", []) or []:
        h2h = parse_h2h(event, bookmaker, home_team, away_team)
        if h2h:
            h2h_books.append(h2h)
        if spread is None:
            spread = parse_spreads(bookmaker, home_team, away_team)
        if total is None:
            total = parse_totals(bookmaker)

    if not h2h_books:
        return None

    event_date = str(event.get("commence_time") or "")[:10]
    markets = {
        "1x2": {
            "average": average_h2h(h2h_books),
            "bookmakers": h2h_books,
        }
    }
    if spread:
        markets["asian_handicap"] = spread
    if total:
        markets["over_under"] = total

    return {
        "key": f"{home_team}|{away_team}|{event_date}",
        "value": {
            "source": "the_odds_api",
            "event_id": event.get("id"),
            "event_home_team": event.get("home_team"),
            "event_away_team": event.get("away_team"),
            "home_team": home_team,
            "away_team": away_team,
            "date": event_date,
            "commence_time": event.get("commence_time"),
            "fetched_at": fetched_at,
            "bookmaker_count": len(h2h_books),
            "swapped_from_api": bool(schedule_match.get("reversed_order")),
            "match_diagnostics": {
                "local_home_normalized": normalize_team_name(home_team),
                "local_away_normalized": normalize_team_name(away_team),
                "event_home_normalized": normalize_team_name(event.get("home_team")),
                "event_away_normalized": normalize_team_name(event.get("away_team")),
                "alias_mapping_used": (
                    normalize_team_name(home_team) != str(home_team).strip().lower()
                    or normalize_team_name(away_team) != str(away_team).strip().lower()
                    or normalize_team_name(event.get("home_team")) != str(event.get("home_team") or "").strip().lower()
                    or normalize_team_name(event.get("away_team")) != str(event.get("away_team") or "").strip().lower()
                ),
            },
            "markets": markets,
        },
    }


def main():
    generated_at = iso_now()
    load_dotenv(ENV_PATH)
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        save_cache(base_cache(generated_at, "THE_ODDS_API_KEY is not set. Market odds signal disabled."))
        return

    schedule_entries = load_schedule_index()
    if not schedule_entries:
        save_cache(base_cache(generated_at, "World Cup schedule cache missing or empty. Market odds signal disabled."))
        return

    data = base_cache(generated_at)
    try:
        events, headers = request_the_odds_api(api_key)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        data["meta"]["warning"] = f"The Odds API request failed. Market odds signal disabled. Detail: {exc}"
        save_cache(data)
        return

    if not isinstance(events, list):
        data["meta"]["warning"] = "The Odds API returned an unexpected response. Market odds signal disabled."
        save_cache(data)
        return

    data["meta"]["events_returned"] = len(events)
    data["meta"]["requests_remaining"] = headers.get("x-requests-remaining")
    data["meta"]["requests_used"] = headers.get("x-requests-used")

    unmatched = []
    for event in events:
        schedule_match = find_schedule_match(event, schedule_entries)
        if not schedule_match:
            unmatched.append({
                "event_id": event.get("id"),
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "commence_time": event.get("commence_time"),
                "reason": "No matching local WC2026 schedule fixture found.",
            })
            continue
        entry = event_to_cache_entry(event, schedule_match, generated_at)
        if not entry:
            unmatched.append({
                "event_id": event.get("id"),
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "commence_time": event.get("commence_time"),
                "reason": "Matched schedule, but no complete h2h market was available.",
            })
            continue
        data["matches"][entry["key"]] = entry["value"]

    data["meta"]["matched_matches"] = len(data["matches"])
    data["meta"]["unmatched_events"] = unmatched[:50]
    if not events:
        data["meta"]["warning"] = EMPTY_WARNING
    elif not data["matches"]:
        data["meta"]["warning"] = "No The Odds API events matched the local WC2026 schedule. Market odds signal disabled."
    else:
        data["meta"]["warning"] = None

    save_cache(data)
    print(f"[market_odds] events={len(events)} matched={len(data['matches'])} unmatched={len(unmatched)}")


if __name__ == "__main__":
    main()
