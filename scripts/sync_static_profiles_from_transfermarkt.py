import json
import math
import os
import re
import sys
from datetime import datetime
from html import unescape

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_engine import _normalize_name, get_team_profile


RANKING_URL = "https://www.transfermarkt.com/wettbewerbe/fifa"
PARTICIPANTS_URL = "https://www.transfermarkt.com/weltmeisterschaft/teilnehmer/pokalwettbewerb/FIWC/saison_id/2025"
USER_AGENT = "Mozilla/5.0"

TEAM_ALIASES = {
    "南非": "South Africa",
    "捷克": "Czechia",
    "波黑": "Bosnia-Herzegovina",
    "巴拉圭": "Paraguay",
    "卡塔尔": "Qatar",
    "瑞士": "Switzerland",
    "海地": "Haiti",
    "苏格兰": "Scotland",
    "土耳其": "Turkiye",
    "库拉索": "Curaçao",
    "科特迪瓦": "Ivory Coast",
    "厄瓜多尔": "Ecuador",
    "瑞典": "Sweden",
    "突尼斯": "Tunisia",
    "佛得角": "Cape Verde",
    "沙特阿拉伯": "Saudi Arabia",
    "新西兰": "New Zealand",
    "伊拉克": "Iraq",
    "挪威": "Norway",
    "阿尔及利亚": "Algeria",
    "奥地利": "Austria",
    "约旦": "Jordan",
    "刚果民主共和国": "Democratic Republic of the Congo",
    "加纳": "Ghana",
    "巴拿马": "Panama",
    "乌兹别克斯坦": "Uzbekistan",
}

FLAGS = {
    "南非": "🇿🇦",
    "捷克": "🇨🇿",
    "波黑": "🇧🇦",
    "巴拉圭": "🇵🇾",
    "卡塔尔": "🇶🇦",
    "瑞士": "🇨🇭",
    "海地": "🇭🇹",
    "苏格兰": "🏴",
    "土耳其": "🇹🇷",
    "库拉索": "🇨🇼",
    "科特迪瓦": "🇨🇮",
    "厄瓜多尔": "🇪🇨",
    "瑞典": "🇸🇪",
    "突尼斯": "🇹🇳",
    "佛得角": "🇨🇻",
    "沙特阿拉伯": "🇸🇦",
    "新西兰": "🇳🇿",
    "伊拉克": "🇮🇶",
    "挪威": "🇳🇴",
    "阿尔及利亚": "🇩🇿",
    "奥地利": "🇦🇹",
    "约旦": "🇯🇴",
    "刚果民主共和国": "🇨🇩",
    "加纳": "🇬🇭",
    "巴拿马": "🇵🇦",
    "乌兹别克斯坦": "🇺🇿",
}


def clean_html(value):
    return re.sub(r"\s+", " ", re.sub(r"<.*?>", "", value)).strip()


def parse_market_value_to_billion_eur(value):
    text = clean_html(value).replace("€", "").replace(",", "").strip()
    if not text or text == "-":
        return None
    if text.endswith("bn"):
        return round(float(text[:-2]), 4)
    if text.endswith("m"):
        return round(float(text[:-1]) / 1000, 4)
    if text.endswith("k"):
        return round(float(text[:-1]) / 1_000_000, 4)
    return None


def fetch_html(url):
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return response.text


def parse_ranking_rows():
    rows = {}
    for page in range(1, 10):
        html = fetch_html(f"{RANKING_URL}?page={page}")
        tbody = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
        if not tbody:
            continue
        found = 0
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tbody.group(1), re.S):
            tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            if len(tds) < 7:
                continue
            rank_match = re.search(r"\d+", clean_html(tds[0]))
            names = re.findall(r'<a title="([^"]+)"', tds[1])
            if not rank_match or not names:
                continue
            name = unescape(names[-1])
            rows[name] = {
                "fifa_rank": int(rank_match.group()),
                "market_value_billion_eur": parse_market_value_to_billion_eur(tds[4]),
                "confederation": clean_html(tds[5]),
                "fifa_points": float(clean_html(tds[6]).replace(",", "")),
                "ranking_source_url": RANKING_URL,
            }
            found += 1
        if found == 0:
            break
    return rows


def parse_participant_rows():
    html = fetch_html(PARTICIPANTS_URL)
    tbody = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
    rows = {}
    if not tbody:
        return rows
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tbody.group(1), re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) < 7:
            continue
        names = re.findall(r'<a title="([^"]+)"', tds[1])
        if not names:
            continue
        name = unescape(names[-1])
        rows[name] = {
            "participant_market_value_billion_eur": parse_market_value_to_billion_eur(tds[5]),
            "avg_age": clean_html(tds[3]),
            "world_cup_participations": clean_html(tds[4]),
            "participant_source_url": PARTICIPANTS_URL,
        }
    return rows


def clamp(value, low, high):
    return max(low, min(high, value))


def rating_from_rank_market(rank, market_billion_eur):
    rank_score = clamp(96 - max(0, rank - 1) * 0.48, 52, 94)
    market_million = max(1, (market_billion_eur or 0) * 1000)
    market_score = clamp(52 + math.log10(market_million) * 13, 52, 92)
    attack = round(clamp(rank_score * 0.58 + market_score * 0.42, 50, 94))
    defense = round(clamp(rank_score * 0.72 + market_score * 0.28, 50, 92))
    midfield = round(clamp(rank_score * 0.64 + market_score * 0.36, 50, 93))
    return attack, defense, midfield


def profile_goals(team_name, attack, defense):
    csv_profile = get_team_profile(team_name)
    if csv_profile:
        gf = float(csv_profile.get("avg_goals_for", 1.25))
        ga = float(csv_profile.get("avg_goals_against", 1.15))
        recent_form = list(str(csv_profile.get("recent_form", ""))[-6:])
    else:
        gf = 0.85 + (attack - 55) / 35 * 1.25
        ga = 1.75 - (defense - 55) / 35 * 0.95
        recent_form = []
    avg_goals_scored = round(clamp(gf, 0.75, 2.35), 2)
    avg_goals_conceded = round(clamp(ga, 0.55, 1.95), 2)
    xg = round(clamp(avg_goals_scored * 0.9, 0.65, 2.1), 2)
    xga = round(clamp(avg_goals_conceded * 1.05, 0.55, 2.05), 2)
    return avg_goals_scored, avg_goals_conceded, xg, xga, recent_form


def build_seed_profile(team_name, source):
    rank = source["fifa_rank"]
    market_billion = source.get("market_value_billion_eur")
    attack, defense, midfield = rating_from_rank_market(rank, market_billion)
    gf, ga, xg, xga, recent_form = profile_goals(team_name, attack, defense)
    return {
        "name": team_name,
        "flag": FLAGS.get(team_name, "⚽"),
        "fifa_rank": rank,
        "confederation": source.get("confederation", ""),
        "market_value": round((market_billion or 0) * 10, 2) if market_billion is not None else None,
        "market_value_unit": "亿欧元",
        "coach": None,
        "key_player": None,
        "style": "均衡",
        "recent_form": recent_form,
        "attack_rating": attack,
        "defense_rating": defense,
        "midfield_rating": midfield,
        "avg_possession": round(clamp(45 + (attack + midfield - 140) * 0.25, 40, 60), 1),
        "avg_goals_scored": gf,
        "avg_goals_conceded": ga,
        "xG_per_match": xg,
        "xGA_per_match": xga,
        "injuries": [],
        "profile_source": {
            "type": "seeded_static_anchor",
            "ranking_source": source.get("ranking_source_url"),
            "participant_source": source.get("participant_source_url"),
            "fifa_points": source.get("fifa_points"),
            "market_value_billion_eur": market_billion,
            "derived_fields": ["attack_rating", "defense_rating", "midfield_rating", "avg_possession", "xG_per_match", "xGA_per_match"],
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
    }


def main():
    schedule_path = os.path.join(PROJECT_ROOT, "data", "cache", "wc2026_schedule.json")
    teams_path = os.path.join(PROJECT_ROOT, "data", "teams.json")
    docs_path = os.path.join(PROJECT_ROOT, "docs", "static_profile_sources.md")

    schedule = json.load(open(schedule_path, encoding="utf-8"))
    teams_data = json.load(open(teams_path, encoding="utf-8"))
    teams = teams_data.get("teams", [])
    existing = {team["name"] for team in teams}
    schedule_teams = [team for group in sorted(schedule["groups"]) for team in schedule["groups"][group]]
    missing = [team for team in schedule_teams if team not in existing]

    ranking_rows = parse_ranking_rows()
    participant_rows = parse_participant_rows()
    added = []
    unresolved = []
    for team_name in missing:
        source_name = TEAM_ALIASES.get(team_name, _normalize_name(team_name))
        source = dict(ranking_rows.get(source_name) or {})
        participant = participant_rows.get(source_name) or {}
        if not source:
            unresolved.append(team_name)
            continue
        if participant.get("participant_market_value_billion_eur") is not None:
            source["market_value_billion_eur"] = participant["participant_market_value_billion_eur"]
        source.update(participant)
        profile = build_seed_profile(team_name, source)
        teams.append(profile)
        added.append((team_name, source_name, source))

    teams_data["teams"] = teams
    with open(teams_path, "w", encoding="utf-8") as f:
        json.dump(teams_data, f, ensure_ascii=False, indent=2)

    os.makedirs(os.path.dirname(docs_path), exist_ok=True)
    lines = [
        "# Static Profile Sources",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Sources",
        "",
        f"- FIFA ranking / points / total market values: {RANKING_URL}",
        f"- World Cup 2026 participant squad market values: {PARTICIPANTS_URL}",
        "",
        "## Method",
        "",
        "- `fifa_rank`, `confederation`, `market_value`, and `fifa_points` are parsed from Transfermarkt pages.",
        "- `attack_rating`, `defense_rating`, `midfield_rating`, possession, xG and xGA are conservative model seed fields derived from rank/value plus local CSV goal rates where available.",
        "- `coach` and `key_player` are intentionally left null unless separately verified.",
        "",
        "## Added Profiles",
        "",
    ]
    for team_name, source_name, source in added:
        lines.append(
            f"- {team_name} ({source_name}): rank {source.get('fifa_rank')}, "
            f"points {source.get('fifa_points')}, confederation {source.get('confederation')}, "
            f"market €{source.get('market_value_billion_eur')}bn"
        )
    if unresolved:
        lines.extend(["", "## Unresolved", ""])
        lines.extend(f"- {team}" for team in unresolved)
    with open(docs_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Added profiles: {len(added)}")
    print(f"Unresolved: {len(unresolved)}")
    if unresolved:
        print(", ".join(unresolved))


if __name__ == "__main__":
    main()
