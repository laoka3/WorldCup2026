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
    build_team_data,
    calculate_match_result_prob,
    calculate_strength_score,
    get_h2h,
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


def score_for_result(result, home, away):
    h = team(home)
    a = team(away)
    h_attack = h.get("attack_rating", 70)
    a_attack = a.get("attack_rating", 70)
    if result == "home":
        return 2 + int(h_attack >= 88), 1 if a_attack >= 75 else 0
    if result == "away":
        return 1 if h_attack >= 75 else 0, 2 + int(a_attack >= 88)
    return 1, 1


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

group_top_stats = {g: Counter() for g in group_order}

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
        hg, ag = score_for_result(result, home, away)

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
            chosen_group = max(
                candidates,
                key=lambda g: (group_tables[g][2]["pts"], group_tables[g][2]["gd"], group_tables[g][2]["gf"], calculate_strength_score(team(group_tables[g][2]["team"]))),
            )
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
        result, _ = pick_result(rng, home, away, allow_draw=False)
        winner = home if result == "home" else away
        winners[match["match_no"]] = winner
        knockout_results.append({
            "match": match["match_no"],
            "stage": match["stage"],
            "home": home,
            "away": away,
            "winner": winner,
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

results = {
    "runs": RUNS,
    "champion_probabilities": {team: round(count / RUNS * 100, 1) for team, count in champions.most_common()},
    "runner_up_probabilities": {team: round(count / RUNS * 100, 1) for team, count in runner_ups.most_common()},
    "semi_final_loss_probabilities": {team: round(count / RUNS * 100, 1) for team, count in semi_losers.most_common()},
    "group_winner_probabilities": {
        group: {team: round(count / RUNS * 100, 1) for team, count in counter.most_common()}
        for group, counter in group_top_stats.items()
    },
}

output_dir = os.path.join(PROJECT_ROOT, "outputs")
os.makedirs(output_dir, exist_ok=True)
out_path = os.path.join(output_dir, "simulate_wc2026_monte_carlo_out.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(json.dumps(results, ensure_ascii=False, indent=2))
