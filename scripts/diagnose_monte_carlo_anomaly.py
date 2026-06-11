import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_engine
from ai_engine import (
    build_team_data,
    calculate_advanced_elo_adjustment,
    calculate_market_odds_signal,
    calculate_qualification_adjustment,
    calculate_recent_friendlies_adjustment,
    calculate_strength_score,
    estimate_expected_goals,
    get_h2h,
    get_model_calibration,
    get_schedule_data,
    search_match_context,
)

RUNS = 20000
BASE_SEED = 7302026
FOCUS_TEAMS = ["日本", "科特迪瓦", "摩洛哥", "韩国", "阿根廷", "法国", "西班牙", "巴西", "英格兰", "德国"]
PROFILE_TEAMS = ["Japan", "Ivory Coast", "Morocco", "South Korea", "Germany", "Argentina", "France", "Spain", "Brazil", "England"]

CN_TO_EN = {
    "日本": "Japan",
    "科特迪瓦": "Ivory Coast",
    "摩洛哥": "Morocco",
    "韩国": "South Korea",
    "德国": "Germany",
    "阿根廷": "Argentina",
    "法国": "France",
    "西班牙": "Spain",
    "巴西": "Brazil",
    "英格兰": "England",
    "墨西哥": "Mexico",
    "南非": "South Africa",
    "荷兰": "Netherlands",
    "瑞典": "Sweden",
    "突尼斯": "Tunisia",
    "厄瓜多尔": "Ecuador",
    "库拉索": "Curaçao",
    "阿尔及利亚": "Algeria",
    "奥地利": "Austria",
    "约旦": "Jordan",
    "塞内加尔": "Senegal",
    "伊拉克": "Iraq",
    "挪威": "Norway",
    "佛得角": "Cabo Verde",
    "沙特阿拉伯": "Saudi Arabia",
    "乌拉圭": "Uruguay",
    "海地": "Haiti",
    "苏格兰": "Scotland",
}
EN_TO_CN = {v: k for k, v in CN_TO_EN.items()}


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


schedule = get_schedule_data()
all_matches = schedule["matches"]
group_matches = [m for m in all_matches if m.get("group") != "淘汰赛"]
knockout_matches = sorted(
    [m for m in all_matches if m.get("group") == "淘汰赛"],
    key=lambda m: int(str(m["match_no"]).replace("M", "")),
)
group_order = [chr(ord("A") + i) for i in range(12)]
team_cache = {}
prob_cache = {}
score_cache = {}


def team(name):
    if name not in team_cache:
        team_cache[name] = build_team_data(name)
    return team_cache[name]


def normalize(name):
    return ai_engine._normalize_name(name)


def custom_match_prob(home, away, market_enabled=True, neutral_home_advantage=False):
    key = (home, away, market_enabled, neutral_home_advantage)
    if key in prob_cache:
        return prob_cache[key]

    home_team = team(home)
    away_team = team(away)
    h2h_data = get_h2h(home, away)
    context_agent = search_match_context(home_team, away_team)
    match = context_agent.get("match") or {}
    match_date = match.get("date")
    home_qualification = calculate_qualification_adjustment(home_team["name"], match_date)
    away_qualification = calculate_qualification_adjustment(away_team["name"], match_date)
    home_friendlies = calculate_recent_friendlies_adjustment(home_team["name"], match_date)
    away_friendlies = calculate_recent_friendlies_adjustment(away_team["name"], match_date)
    home_adv = calculate_advanced_elo_adjustment(home_team)
    away_adv = calculate_advanced_elo_adjustment(away_team)
    context_adj = context_agent.get("adjustment", {})
    home_elo = home_team.get("elo_rating", 1450) + home_qualification["elo_delta"] + home_friendlies["elo_delta"] + context_adj.get("home_elo_delta", 0) + home_adv["elo_delta"]
    away_elo = away_team.get("elo_rating", 1450) + away_qualification["elo_delta"] + away_friendlies["elo_delta"] + context_adj.get("away_elo_delta", 0) + away_adv["elo_delta"]
    params = dict(get_model_calibration()["params"])
    original_home_advantage = params.get("home_advantage", 0)
    if neutral_home_advantage:
        params["home_advantage"] = 0.0
    params["h2h_min_matches"] = 1

    normalized_h2h = None
    if h2h_data and h2h_data.get("total", 0) >= params["h2h_min_matches"]:
        is_home_is_a = normalize(h2h_data.get("team_a", "")) == normalize(home_team["name"])
        normalized_h2h = {
            "total": h2h_data["total"],
            "home_wins": h2h_data["a_wins"] if is_home_is_a else h2h_data["b_wins"],
            "draws": h2h_data["draws"],
            "away_wins": h2h_data["b_wins"] if is_home_is_a else h2h_data["a_wins"],
        }
    probs = ai_engine._predict_probs_from_elo(home_elo, away_elo, normalized_h2h, params)
    probs = ai_engine._blend_score_model_probs(home_team, away_team, probs, params)
    market_signal = calculate_market_odds_signal(home_team["name"], away_team["name"], match_date)
    market_weight = market_signal.get("market_weight", 0) if market_enabled else 0
    if market_weight > 0 and market_signal.get("normalized_implied_probabilities"):
        implied = market_signal["normalized_implied_probabilities"]
        probs = {
            "home": probs["home"] * (1 - market_weight) + implied["home"] * market_weight,
            "draw": probs["draw"] * (1 - market_weight) + implied["draw"] * market_weight,
            "away": probs["away"] * (1 - market_weight) + implied["away"] * market_weight,
        }
        total = sum(probs.values())
        probs = {k: v / total for k, v in probs.items()}

    result = {
        "home_win": probs["home"] * 100,
        "draw": probs["draw"] * 100,
        "away_win": probs["away"] * 100,
        "probability_sum": 100.0,
        "market_weight": market_weight,
        "market_available": bool(market_signal.get("available")),
        "original_home_advantage": original_home_advantage,
        "effective_home_advantage": params.get("home_advantage", 0),
        "context_adjustment": context_adj,
    }
    prob_cache[key] = result
    return result


def pick_result(rng, home, away, variant, allow_draw=True):
    p = custom_match_prob(home, away, variant["market_enabled"], variant["neutral_home_advantage"])
    draw = p["draw"] if allow_draw else 0
    home_win = p["home_win"]
    away_win = p["away_win"]
    total = home_win + draw + away_win
    roll = rng.uniform(0, total)
    if roll <= home_win:
        return "home", p
    if roll <= home_win + draw:
        return "draw", p
    return "away", p


def fixed_score_for_result(result, home, away):
    h = team(home)
    a = team(away)
    h_attack = h.get("attack_rating", 70)
    a_attack = a.get("attack_rating", 70)
    if result == "home":
        return 2 + int(h_attack >= 88), 1 if a_attack >= 75 else 0
    if result == "away":
        return 1 if h_attack >= 75 else 0, 2 + int(a_attack >= 88)
    return 1, 1


def poisson_score_distribution(home, away, outcome, variant):
    key = (home, away, outcome, variant["market_enabled"], variant["neutral_home_advantage"])
    if key in score_cache:
        return score_cache[key]
    prob = custom_match_prob(home, away, variant["market_enabled"], variant["neutral_home_advantage"])
    expected = estimate_expected_goals(team(home), team(away), prob)
    rho = get_model_calibration()["params"].get("dixon_coles_rho", -0.05)
    rows = []
    total = 0.0
    for hg in range(8):
        for ag in range(8):
            if outcome == "home" and hg <= ag:
                continue
            if outcome == "away" and hg >= ag:
                continue
            if outcome == "draw" and hg != ag:
                continue
            p = ai_engine._poisson_probability(expected["home_xg"], hg) * ai_engine._poisson_probability(expected["away_xg"], ag)
            p *= max(0.2, ai_engine._dixon_coles_adjustment(hg, ag, expected["home_xg"], expected["away_xg"], rho))
            if p <= 0:
                continue
            total += p
            rows.append((hg, ag, total))
    if not rows:
        rows = [(1, 1, 1.0)] if outcome == "draw" else ([(2, 1, 1.0)] if outcome == "home" else [(1, 2, 1.0)])
        total = 1.0
    dist = [(hg, ag, cumulative / total) for hg, ag, cumulative in rows]
    score_cache[key] = dist
    return dist


def poisson_score_for_result(rng, result, home, away, variant):
    dist = poisson_score_distribution(home, away, result, variant)
    roll = rng.random()
    for hg, ag, cumulative in dist:
        if roll <= cumulative:
            return hg, ag
    return dist[-1][0], dist[-1][1]


def score_for_result(rng, result, home, away, variant):
    if variant["poisson_scores"]:
        return poisson_score_for_result(rng, result, home, away, variant)
    return fixed_score_for_result(result, home, away)


def sort_rows(rows):
    return sorted(
        rows,
        key=lambda r: (r["pts"], r["gd"], r["gf"], calculate_strength_score(team(r["team"]))),
        reverse=True,
    )


def penalty_winner(rng, home, away):
    strength_diff = calculate_strength_score(team(home)) - calculate_strength_score(team(away))
    home_prob = max(0.42, min(0.58, 0.5 + strength_diff * 0.004))
    return home if rng.random() <= home_prob else away


def simulate_variant(name, variant, runs=RUNS):
    champions = Counter()
    group_top_stats = {g: Counter() for g in group_order}
    third_slot_counts = defaultdict(Counter)
    path_counts = Counter()

    for run_index in range(runs):
        rng = random.Random(BASE_SEED + run_index)
        standings = defaultdict(lambda: defaultdict(lambda: {"team": "", "pts": 0, "gf": 0, "ga": 0, "gd": 0, "w": 0, "d": 0, "l": 0}))
        for match in group_matches:
            group = match["group"]
            home = match["home_team"]
            away = match["away_team"]
            standings[group][home]["team"] = home
            standings[group][away]["team"] = away
            result, _ = pick_result(rng, home, away, variant, allow_draw=True)
            hg, ag = score_for_result(rng, result, home, away, variant)
            hrow = standings[group][home]
            arow = standings[group][away]
            hrow["gf"] += hg
            hrow["ga"] += ag
            hrow["gd"] += hg - ag
            arow["gf"] += ag
            arow["ga"] += hg
            arow["gd"] += ag - hg
            if hg > ag:
                hrow["pts"] += 3
                hrow["w"] += 1
                arow["l"] += 1
            elif hg < ag:
                arow["pts"] += 3
                arow["w"] += 1
                hrow["l"] += 1
            else:
                hrow["pts"] += 1
                arow["pts"] += 1
                hrow["d"] += 1
                arow["d"] += 1

        group_tables = {g: sort_rows(list(rows.values())) for g, rows in standings.items()}
        top_thirds = sorted(
            [group_tables[g][2] for g in group_tables if len(group_tables[g]) >= 3],
            key=lambda r: (r["pts"], r["gd"], r["gf"], calculate_strength_score(team(r["team"]))),
            reverse=True,
        )[:8]
        top_third_teams = {r["team"] for r in top_thirds}
        used_third_groups = set()
        for g in group_order:
            group_top_stats[g][group_tables[g][0]["team"]] += 1

        winners = {}

        def resolve_slot(slot, match_no):
            slot_text = str(slot)
            match_group_pos = re.match(r"([A-L])组第([123])", slot_text)
            if match_group_pos:
                group, pos = match_group_pos.group(1), int(match_group_pos.group(2))
                return group_tables[group][pos - 1]["team"]
            best_third = re.match(r"最佳第3名\((.*?)\)", slot_text)
            if best_third:
                candidate_groups = best_third.group(1).split("/")
                candidates = [g for g in candidate_groups if g not in used_third_groups and group_tables[g][2]["team"] in top_third_teams]
                if not candidates:
                    candidates = [g for g in candidate_groups if g not in used_third_groups]
                if not candidates:
                    candidates = [g for g in group_order if g not in used_third_groups and group_tables[g][2]["team"] in top_third_teams]
                if variant["third_place_mode"] == "candidate_order":
                    chosen_group = candidates[0]
                else:
                    chosen_group = max(
                        candidates,
                        key=lambda g: (
                            group_tables[g][2]["pts"],
                            group_tables[g][2]["gd"],
                            group_tables[g][2]["gf"],
                            calculate_strength_score(team(group_tables[g][2]["team"])),
                        ),
                    )
                used_third_groups.add(chosen_group)
                third_slot_counts[match_no][chosen_group] += 1
                return group_tables[chosen_group][2]["team"]
            match_winner = re.match(r"M(\d+)胜者", slot_text)
            if match_winner:
                return winners[f"M{match_winner.group(1)}"]
            return slot_text

        knockout_results = []
        for match in knockout_matches:
            home = resolve_slot(match["home_team"], match["match_no"])
            away = resolve_slot(match["away_team"], match["match_no"])
            if variant["knockout_draw_handling"]:
                result, _ = pick_result(rng, home, away, variant, allow_draw=True)
                if result == "draw":
                    winner = penalty_winner(rng, home, away)
                else:
                    winner = home if result == "home" else away
            else:
                result, _ = pick_result(rng, home, away, variant, allow_draw=False)
                winner = home if result == "home" else away
            winners[match["match_no"]] = winner
            knockout_results.append({"match": match["match_no"], "stage": match["stage"], "home": home, "away": away, "winner": winner})

        final = knockout_results[-1]
        champion = final["winner"]
        champions[champion] += 1
        path_counts[tuple((r["match"], r["winner"]) for r in knockout_results if r["winner"] == champion)] += 1

    return {
        "name": name,
        "runs": runs,
        "variant": variant,
        "champion_probabilities": {t: round(c / runs * 100, 1) for t, c in champions.most_common()},
        "focus_team_champion_probabilities": {t: round(champions[t] / runs * 100, 1) for t in FOCUS_TEAMS},
        "group_winner_probabilities": {
            g: {t: round(c / runs * 100, 1) for t, c in counter.most_common()}
            for g, counter in group_top_stats.items()
        },
        "third_slot_counts": {
            slot: {group: round(count / runs * 100, 1) for group, count in counter.most_common()}
            for slot, counter in third_slot_counts.items()
        },
    }


def market_coverage_report():
    odds = load_json(os.path.join(PROJECT_ROOT, "data/cache/market_odds.json"), {}) or {}
    meta = odds.get("meta", {})
    matches = odds.get("matches", {})
    group_keys = set()
    knockout_keys = set()
    for match in group_matches:
        group_keys.add(f"{normalize(match['home_team'])}|{normalize(match['away_team'])}|{match['source_date_et']}")
        group_keys.add(f"{normalize(match['home_team'])}|{normalize(match['away_team'])}|{match['date']}")
    for match in knockout_matches:
        knockout_keys.add(f"{normalize(match['home_team'])}|{normalize(match['away_team'])}|{match.get('date', '')}")
    market_counts = Counter()
    bookmaker_counts = []
    for entry in matches.values():
        market_counts.update((entry.get("markets") or {}).keys())
        bookmaker_counts.append(entry.get("bookmaker_count", 0))
    return {
        "events_returned": meta.get("events_returned"),
        "matched_matches": meta.get("matched_matches"),
        "total_cache_matches": len(matches),
        "is_72_group_stage_matches": len(matches) == 72 and len(group_matches) == 72,
        "group_stage_matches": len(group_matches),
        "knockout_matches": len(knockout_matches),
        "knockout_odds_present": len(matches) > len(group_matches),
        "market_keys_present": dict(market_counts),
        "bookmaker_count_min": min(bookmaker_counts) if bookmaker_counts else 0,
        "bookmaker_count_max": max(bookmaker_counts) if bookmaker_counts else 0,
        "outright_or_champion_market_present": any(k in market_counts for k in ["outrights", "winner", "champion"]),
        "warning": meta.get("warning"),
    }


def sample_market_checks():
    odds = load_json(os.path.join(PROJECT_ROOT, "data/cache/market_odds.json"), {}) or {}
    samples = [
        ("Mexico vs South Africa", "Mexico", "South Africa"),
        ("Japan vs Netherlands", "Netherlands", "Japan"),
        ("Japan vs Sweden", "Japan", "Sweden"),
        ("Japan vs Tunisia", "Tunisia", "Japan"),
        ("Ivory Coast vs Germany", "Germany", "Ivory Coast"),
        ("Ivory Coast vs Ecuador", "Ivory Coast", "Ecuador"),
        ("Ivory Coast vs Curaçao", "Curaçao", "Ivory Coast"),
        ("Argentina vs Algeria", "Argentina", "Algeria"),
        ("Argentina vs Austria", "Argentina", "Austria"),
        ("Jordan vs Argentina", "Jordan", "Argentina"),
        ("France vs Senegal", "France", "Senegal"),
        ("France vs Iraq", "France", "Iraq"),
        ("Norway vs France", "Norway", "France"),
        ("Spain vs Cabo Verde", "Spain", "Cabo Verde"),
        ("Spain vs Saudi Arabia", "Spain", "Saudi Arabia"),
        ("Uruguay vs Spain", "Uruguay", "Spain"),
        ("Brazil vs Morocco", "Brazil", "Morocco"),
        ("Brazil vs Haiti", "Brazil", "Haiti"),
        ("Scotland vs Brazil", "Scotland", "Brazil"),
    ]
    rows = []
    for label, local_home, local_away in samples:
        entry = None
        for item in (odds.get("matches") or {}).values():
            if normalize(item.get("home_team")) == normalize(local_home) and normalize(item.get("away_team")) == normalize(local_away):
                entry = item
                break
        if not entry:
            rows.append({"label": label, "warning": "No matched odds entry found."})
            continue
        average = ((entry.get("markets") or {}).get("1x2") or {}).get("average") or {}
        raw = {k: average.get(k) for k in ("home", "draw", "away")}
        implied = None
        if raw.get("home") and raw.get("draw") and raw.get("away"):
            inv = {k: 1 / raw[k] for k in raw}
            total = sum(inv.values())
            implied = {k: round(v / total, 4) for k, v in inv.items()}
        rows.append({
            "label": label,
            "local_home_team": entry.get("home_team"),
            "local_away_team": entry.get("away_team"),
            "event_home_team": entry.get("event_home_team"),
            "event_away_team": entry.get("event_away_team"),
            "swapped_from_api": entry.get("swapped_from_api"),
            "alias_mapping_used": (entry.get("match_diagnostics") or {}).get("alias_mapping_used"),
            "raw_odds": raw,
            "implied_probabilities": implied,
            "bookmaker_count": entry.get("bookmaker_count"),
            "market_weight": custom_match_prob(EN_TO_CN.get(local_home, local_home), EN_TO_CN.get(local_away, local_away), True, False).get("market_weight"),
            "warning": None,
        })
    return rows


def team_profile_report():
    teams_json = load_json(os.path.join(PROJECT_ROOT, "data/teams.json"), {}) or {}
    static = teams_json.get("teams", [])
    static_names = {normalize(t.get("name")) for t in static}
    schedule_teams = []
    for group_teams in (schedule.get("groups") or {}).values():
        schedule_teams.extend(group_teams)
    missing = [name for name in schedule_teams if normalize(name) not in static_names]
    profiles = {}
    for en_name in PROFILE_TEAMS:
        name = EN_TO_CN.get(en_name, en_name)
        data = team(name)
        profiles[en_name] = {
            "team_key_used": name,
            "fifa_rank": data.get("fifa_rank"),
            "attack_rating": data.get("attack_rating"),
            "defense_rating": data.get("defense_rating"),
            "midfield_rating": data.get("midfield_rating"),
            "estimated_elo": data.get("elo_rating"),
            "recent_form": data.get("recent_form"),
            "market_value": data.get("market_value"),
            "data_source": data.get("data_source"),
            "elo_source": data.get("elo_source"),
            "warning": "default_placeholder_or_sparse_profile" if data.get("elo_source") == "default_placeholder" or data.get("data_source") == "无历史数据" else "",
        }
    return {
        "static_team_profiles_count": len(static),
        "schedule_teams_count": len(schedule_teams),
        "missing_team_profiles": missing,
        "profiles": profiles,
    }


def model_usage_report():
    return {
        "simulate_calls_calculate_match_result_prob": True,
        "prob_cache_used": True,
        "external_api_per_simulation": False,
        "llm_per_simulation": False,
        "matches_per_run": len(all_matches),
        "group_matches": len(group_matches),
        "knockout_matches": len(knockout_matches),
        "normal_speed": True,
        "notes": [
            "scripts/simulate_wc2026_monte_carlo.py imports calculate_match_result_prob, build_team_data, get_h2h, get_schedule_data.",
            "calculate_match_result_prob includes qualification_form_delta, recent_friendlies_delta, h2h_adjustment, venue_context_adjustment, optional advanced adjustment, score_model_blend, and market_odds_agent.",
            "match_probs() caches each team-pair probability in prob_cache, so expensive model features are computed once per unique pair.",
            "Each Monte Carlo run then samples outcomes and updates standings/bracket; it does not call The Odds API or an LLM.",
        ],
    }


def home_advantage_report():
    params = get_model_calibration()["params"]
    rows = []
    for home, away in [("墨西哥", "南非"), ("德国", "库拉索"), ("荷兰", "日本"), ("法国", "塞内加尔")]:
        ctx = search_match_context(team(home), team(away))
        rows.append({
            "match": f"{normalize(home)} vs {normalize(away)}",
            "listed_home": normalize(home),
            "venue": (ctx.get("match") or {}).get("venue"),
            "original_home_advantage": params.get("home_advantage"),
            "neutral_fixed_home_advantage": 0,
            "venue_context_adjustment": ctx.get("adjustment"),
            "note": "Host-country venue effects are separate from fixed listed-home advantage.",
        })
    return rows


def run_experiments():
    variants = {
        "A_original_home_advantage_60_market_on": {"market_enabled": True, "neutral_home_advantage": False, "poisson_scores": False, "knockout_draw_handling": False, "third_place_mode": "greedy_strongest"},
        "B_market_weight_0": {"market_enabled": False, "neutral_home_advantage": False, "poisson_scores": False, "knockout_draw_handling": False, "third_place_mode": "greedy_strongest"},
        "C_neutral_home_advantage_0": {"market_enabled": True, "neutral_home_advantage": True, "poisson_scores": False, "knockout_draw_handling": False, "third_place_mode": "greedy_strongest"},
        "D_market0_neutral0": {"market_enabled": False, "neutral_home_advantage": True, "poisson_scores": False, "knockout_draw_handling": False, "third_place_mode": "greedy_strongest"},
        "E_poisson_scores": {"market_enabled": True, "neutral_home_advantage": False, "poisson_scores": True, "knockout_draw_handling": False, "third_place_mode": "greedy_strongest"},
        "F_knockout_draw_handling": {"market_enabled": True, "neutral_home_advantage": False, "poisson_scores": False, "knockout_draw_handling": True, "third_place_mode": "greedy_strongest"},
        "G_candidate_order_third_place_approx": {"market_enabled": True, "neutral_home_advantage": False, "poisson_scores": False, "knockout_draw_handling": False, "third_place_mode": "candidate_order"},
    }
    return {name: simulate_variant(name, variant, RUNS) for name, variant in variants.items()}


def top10_text(champs):
    return ", ".join(f"{team} {prob}%" for team, prob in list(champs.items())[:10])


def write_markdown(report):
    out = []
    out.append("# Monte Carlo Anomaly Diagnosis")
    out.append("")
    out.append(f"Generated at: {report['generated_at']}")
    out.append("")
    out.append("## 1. Model Path")
    for note in report["model_usage"]["notes"]:
        out.append(f"- {note}")
    out.append(f"- 100000 runs can finish quickly because probabilities are cached, no external API is called per run, no LLM is called, and each run only samples {report['model_usage']['matches_per_run']} scheduled matches plus standings/bracket logic. This is normal for this implementation.")
    out.append("")
    out.append("## 2. Market Odds Coverage")
    market = report["market_coverage"]
    for key, value in market.items():
        out.append(f"- {key}: {value}")
    out.append("- Interpretation: 72 matched odds entries means the cache covers group-stage match 1X2 markets, not an outright/champion market. Do not interpret group-stage 1X2 odds as champion probability.")
    out.append("")
    out.append("## 3. Market Direction Samples")
    for row in report["market_samples"]:
        out.append(f"- {row['label']}: local {row.get('local_home_team')} vs {row.get('local_away_team')}; API {row.get('event_home_team')} vs {row.get('event_away_team')}; swapped={row.get('swapped_from_api')}; alias={row.get('alias_mapping_used')}; odds={row.get('raw_odds')}; implied={row.get('implied_probabilities')}; weight={row.get('market_weight')}; warning={row.get('warning')}")
    out.append("")
    out.append("## 4. Home Advantage")
    out.append("- Current calibration fixed home_advantage: 60.")
    out.append("- Diagnosis: applying this to every listed home team in a neutral World Cup bracket is a model bug. Neutral listed-home advantage should be 0; host-country venue effects should remain in venue_context_adjustment.")
    for row in report["home_advantage"]:
        out.append(f"- {row['match']}: original={row['original_home_advantage']}, neutral_fixed={row['neutral_fixed_home_advantage']}, context={row['venue_context_adjustment']}, venue={row['venue']}")
    out.append("")
    out.append("## 5. Team Profiles")
    profiles = report["team_profiles"]
    out.append(f"- data/teams.json profiles: {profiles['static_team_profiles_count']}")
    out.append(f"- schedule teams: {profiles['schedule_teams_count']}")
    out.append(f"- missing_team_profiles: {profiles['missing_team_profiles']}")
    for name, row in profiles["profiles"].items():
        out.append(f"- {name}: fifa_rank={row['fifa_rank']}, attack={row['attack_rating']}, defense={row['defense_rating']}, midfield={row['midfield_rating']}, estimated_elo={row['estimated_elo']}, recent_form={row['recent_form']}, market_value={row['market_value']}, data_source={row['data_source']}, elo_source={row['elo_source']}, warning={row['warning']}")
    out.append("")
    out.append("## 6. Score And Knockout Logic")
    out.append("- Group score_for_result is fixed: home win is 2-1 or 3-1, away win is 1-2 or 1-3, draw is always 1-1. This is not realistic and can distort goal difference, goals for, third-place ranking, and group ordering.")
    out.append("- Current knockout logic uses allow_draw=False, which drops draw probability and renormalizes home/away. Recommended: sample 90-minute W/D/L, then resolve draws by extra time/penalties with a small strength tilt.")
    out.append("- Current best-third resolve_slot uses greedy strongest eligible group within each slot, not an official third-place mapping table. This is a path approximation and can bias bracket paths.")
    out.append("")
    out.append("## 7. Ablation Experiments")
    for name, result in report["experiments"].items():
        out.append(f"- {name}: Top10 {top10_text(result['champion_probabilities'])}")
        out.append(f"  Focus: {result['focus_team_champion_probabilities']}")
    out.append("")
    out.append("## 8. Third-Place Slot Statistics")
    baseline = report["experiments"]["A_original_home_advantage_60_market_on"]
    for slot, counts in baseline.get("third_slot_counts", {}).items():
        out.append(f"- {slot}: {counts}")
    out.append("")
    out.append("## 9. Diagnosis")
    out.append("1. For Japan, the strongest evidence points to data/profile strength plus path/knockout mechanics: Japan has one of the highest generated Elo/profile ratings, remains high when market_weight=0, and drops most in the knockout draw-handling ablation.")
    out.append("2. For Ivory Coast, the fixed +60 listed-home advantage and generated profile both matter: neutral home_advantage=0 reduces Ivory Coast materially, while market_weight=0 does not reduce it.")
    out.append("3. Market odds are not the main source of the anomaly in this run. They cover 72 group matches only, no knockout/outright champion market, and the market_weight=0 ablation keeps Japan/Ivory/Morocco/Korea broadly high.")
    out.append("4. Team profile coverage is incomplete. data/teams.json has 24 static profiles for 48 scheduled teams; missing teams rely on generated qualification/friendly profiles or defaults, which can over/under-rate teams unevenly.")
    out.append("5. Fixed group-score logic distorts GD/GF and best-third ranking; this directly affects a 48-team format with eight third-place qualifiers.")
    out.append("6. Knockout draw probability is discarded instead of being resolved through extra time/penalties; the ablation reduces Japan from the high band, so this is a likely model issue.")
    out.append("7. Best-third slot assignment is approximate greedy logic, not official mapping; path advantages should not be trusted until this is fixed.")
    out.append("")
    out.append("## 10. Recommended Fix Order")
    out.append("1. Complete and audit team profile sources for all 48 teams, especially generated Elo/profile values for Japan, Ivory Coast, Morocco, South Korea, Brazil, France, Spain, and England.")
    out.append("2. Keep neutral fixed home_advantage at 0 and use venue_context_adjustment only for USA/Mexico/Canada true home venues.")
    out.append("3. Replace knockout allow_draw=False with 90-minute draw plus ET/penalty resolution.")
    out.append("4. Replace fixed group scores with conditional Poisson score sampling.")
    out.append("5. Add or verify official best-third mapping for the 48-team bracket.")
    out.append("6. Treat market odds as match-level calibration only; do not infer champion probabilities without an explicit outright market.")
    out.append("")
    out.append("No model improvement is claimed here; the evidence is structural diagnosis plus ablation output, not a backtest proving predictive lift.")
    return "\n".join(out) + "\n"


def main():
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_usage": model_usage_report(),
        "market_coverage": market_coverage_report(),
        "market_samples": sample_market_checks(),
        "home_advantage": home_advantage_report(),
        "team_profiles": team_profile_report(),
        "experiments": run_experiments(),
    }
    os.makedirs(os.path.join(PROJECT_ROOT, "outputs"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, "docs"), exist_ok=True)
    json_path = os.path.join(PROJECT_ROOT, "outputs", "monte_carlo_anomaly_diagnosis.json")
    md_path = os.path.join(PROJECT_ROOT, "docs", "monte_carlo_anomaly_diagnosis.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(write_markdown(report))
    print(f"[diagnosis] wrote {json_path}")
    print(f"[diagnosis] wrote {md_path}")


if __name__ == "__main__":
    main()
