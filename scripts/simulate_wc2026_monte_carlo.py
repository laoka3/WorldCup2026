import json
import os
import random
import re
import sys
from collections import defaultdict, Counter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_engine import (
    _dixon_coles_adjustment,
    _poisson_probability,
    build_team_data,
    calculate_match_result_prob,
    calculate_strength_score,
    estimate_expected_goals,
    get_h2h,
    get_model_calibration,
    get_schedule_data,
)

RUNS = 100000
BASE_SEED = 2026

schedule = get_schedule_data()
matches = schedule["matches"]
group_matches = [m for m in matches if m.get("group") != "淘汰赛"]
knockout_matches = sorted(
    [m for m in matches if m.get("group") == "淘汰赛"],
    key=lambda m: int(str(m["match_no"]).replace("M", ""))
)

group_order = [chr(ord("A") + i) for i in range(12)]
team_cache = {}
prob_cache = {}


def team(name):
    if name not in team_cache:
        team_cache[name] = build_team_data(name)
    return team_cache[name]


def match_probs(home, away):
    key = (home, away)
    if key not in prob_cache:
        prob_cache[key] = calculate_match_result_prob(team(home), team(away), get_h2h(home, away))
    return prob_cache[key]


def pick_result(rng, home, away, allow_draw=True):
    p = match_probs(home, away)
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


score_cache = {}


def poisson_score_distribution(home, away, outcome):
    key = (home, away, outcome)
    if key in score_cache:
        return score_cache[key]
    prob = match_probs(home, away)
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
            p = _poisson_probability(expected["home_xg"], hg) * _poisson_probability(expected["away_xg"], ag)
            p *= max(0.2, _dixon_coles_adjustment(hg, ag, expected["home_xg"], expected["away_xg"], rho))
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


def score_for_result(rng, result, home, away):
    dist = poisson_score_distribution(home, away, result)
    roll = rng.random()
    for hg, ag, cumulative in dist:
        if roll <= cumulative:
            return hg, ag
    return dist[-1][0], dist[-1][1]


def penalty_winner(rng, home, away):
    strength_diff = calculate_strength_score(team(home)) - calculate_strength_score(team(away))
    home_prob = max(0.42, min(0.58, 0.5 + strength_diff * 0.004))
    return home if rng.random() <= home_prob else away


def sort_rows(rows):
    return sorted(
        rows,
        key=lambda r: (r["pts"], r["gd"], r["gf"], calculate_strength_score(team(r["team"]))),
        reverse=True,
    )


champions = Counter()
runner_ups = Counter()
semi_losers = Counter()
finals = Counter()
stage_reach_stats = {
    "round_of_32": Counter(),
    "round_of_16": Counter(),
    "quarter_final": Counter(),
    "semi_final": Counter(),
    "final": Counter(),
    "champion": Counter(),
}

group_top_stats = {g: Counter() for g in group_order}
group_rank_stats = {g: defaultdict(Counter) for g in group_order}
group_points_totals = {g: defaultdict(float) for g in group_order}
group_gd_totals = {g: defaultdict(float) for g in group_order}
last_simulation = None

for run_index in range(RUNS):
    rng = random.Random(BASE_SEED + run_index)
    standings = defaultdict(lambda: defaultdict(lambda: {"team": "", "pts": 0, "gf": 0, "ga": 0, "gd": 0, "w": 0, "d": 0, "l": 0}))

    for match in group_matches:
        group = match["group"]
        home = match["home_team"]
        away = match["away_team"]
        standings[group][home]["team"] = home
        standings[group][away]["team"] = away
        result, _ = pick_result(rng, home, away, allow_draw=True)
        hg, ag = score_for_result(rng, result, home, away)

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
    round_of_32_teams = set()
    for g in group_order:
        round_of_32_teams.add(group_tables[g][0]["team"])
        round_of_32_teams.add(group_tables[g][1]["team"])
    round_of_32_teams.update(top_third_teams)
    for team_name in round_of_32_teams:
        stage_reach_stats["round_of_32"][team_name] += 1
    used_third_groups = set()

    for g in group_order:
        group_top_stats[g][group_tables[g][0]["team"]] += 1
        for rank_index, row in enumerate(group_tables[g], start=1):
            group_rank_stats[g][row["team"]][rank_index] += 1
            group_points_totals[g][row["team"]] += row["pts"]
            group_gd_totals[g][row["team"]] += row["gd"]

    winners = {}

    def resolve_slot(slot):
        slot = str(slot)
        match_group_pos = re.match(r"([A-L])组第([123])", slot)
        if match_group_pos:
            group, pos = match_group_pos.group(1), int(match_group_pos.group(2))
            return group_tables[group][pos - 1]["team"]

        best_third = re.match(r"最佳第3名\((.*?)\)", slot)
        if best_third:
            candidate_groups = best_third.group(1).split("/")
            candidates = [g for g in candidate_groups if g not in used_third_groups and group_tables[g][2]["team"] in top_third_teams]
            if not candidates:
                candidates = [g for g in candidate_groups if g not in used_third_groups]
            if not candidates:
                candidates = [g for g in group_order if g not in used_third_groups and group_tables[g][2]["team"] in top_third_teams]
            chosen_group = candidates[0]
            used_third_groups.add(chosen_group)
            return group_tables[chosen_group][2]["team"]

        match_winner = re.match(r"M(\d+)胜者", slot)
        if match_winner:
            return winners[f"M{match_winner.group(1)}"]

        return slot

    knockout_results = []
    for match in knockout_matches:
        home = resolve_slot(match["home_team"])
        away = resolve_slot(match["away_team"])
        result, _ = pick_result(rng, home, away, allow_draw=True)
        if result == "draw":
            winner = penalty_winner(rng, home, away)
            resolution = "extra_time_or_penalties"
        else:
            winner = home if result == "home" else away
            resolution = "90_minutes"
        winners[match["match_no"]] = winner
        if match["stage"] == "1/16决赛":
            stage_reach_stats["round_of_16"][winner] += 1
        elif match["stage"] == "1/8决赛":
            stage_reach_stats["quarter_final"][winner] += 1
        elif match["stage"] == "1/4决赛":
            stage_reach_stats["semi_final"][winner] += 1
        elif match["stage"] == "半决赛":
            stage_reach_stats["final"][winner] += 1
        elif match["stage"] == "决赛":
            stage_reach_stats["champion"][winner] += 1
        knockout_results.append({
            "match": match["match_no"],
            "stage": match["stage"],
            "home": home,
            "away": away,
            "winner": winner,
            "ninety_minute_result": result,
            "resolution": resolution,
        })

    final = knockout_results[-1]
    champion = final["winner"]
    runner_up = final["away"] if champion == final["home"] else final["home"]
    champs_in_semi = []
    for r in knockout_results:
        if "半决赛" in r["stage"]:
            loser = r["away"] if r["winner"] == r["home"] else r["home"]
            champs_in_semi.append(loser)

    champions[champion] += 1
    runner_ups[runner_up] += 1
    for loser in champs_in_semi:
        semi_losers[loser] += 1
    finals[(final["home"], final["away"])] += 1
    if run_index == RUNS - 1:
        last_simulation = {
            "seed": BASE_SEED + run_index,
            "champion": champion,
            "runner_up": runner_up,
            "semi_losers": champs_in_semi,
            "group_tables": group_tables,
            "third_qualified": top_thirds,
            "knockout_results": knockout_results,
        }


average_group_rankings = {}
for group in group_order:
    rows = []
    for team_name, counter in group_rank_stats[group].items():
        average_rank = sum(rank * count for rank, count in counter.items()) / RUNS
        rank_probabilities = {
            str(rank): round(counter.get(rank, 0) / RUNS * 100, 1)
            for rank in range(1, 5)
        }
        rows.append({
            "team": team_name,
            "average_rank": round(average_rank, 2),
            "average_points": round(group_points_totals[group][team_name] / RUNS, 2),
            "average_goal_difference": round(group_gd_totals[group][team_name] / RUNS, 2),
            "rank_probabilities": rank_probabilities,
            "qualification_probability": round(sum(counter.get(rank, 0) for rank in (1, 2)) / RUNS * 100, 1),
            "top_three_probability": round(sum(counter.get(rank, 0) for rank in (1, 2, 3)) / RUNS * 100, 1),
        })
    rows.sort(key=lambda row: (row["average_rank"], -row["average_points"], -row["average_goal_difference"]))
    average_group_rankings[group] = rows

results = {
    "runs": RUNS,
    "model_notes": {
        "score_model": "xG-based Poisson constrained to sampled W/D/L result",
        "knockout_draw_handling": "90-minute draw resolved by extra-time/penalty proxy with small strength tilt",
        "third_place_mapping": "approximate deterministic candidate order; official complete mapping not encoded",
    },
    "champion_probabilities": {team: round(count / RUNS * 100, 1) for team, count in champions.most_common()},
    "runner_up_probabilities": {team: round(count / RUNS * 100, 1) for team, count in runner_ups.most_common()},
    "semi_final_loss_probabilities": {team: round(count / RUNS * 100, 1) for team, count in semi_losers.most_common()},
    "stage_reach_probabilities": {
        stage: {team: round(count / RUNS * 100, 1) for team, count in counter.most_common()}
        for stage, counter in stage_reach_stats.items()
    },
    "group_winner_probabilities": {
        group: {team: round(count / RUNS * 100, 1) for team, count in counter.most_common()}
        for group, counter in group_top_stats.items()
    },
    "average_group_rankings": average_group_rankings,
    "last_simulation": last_simulation,
}

output_dir = os.path.join(PROJECT_ROOT, "outputs")
os.makedirs(output_dir, exist_ok=True)
out_path = os.path.join(output_dir, "simulate_wc2026_monte_carlo_out.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(json.dumps(results, ensure_ascii=False, indent=2))
