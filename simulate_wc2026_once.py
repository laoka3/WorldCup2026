import json
import random
import re
from collections import defaultdict

from ai_engine import (
    build_team_data,
    calculate_match_result_prob,
    calculate_strength_score,
    get_h2h,
    get_schedule_data,
)

SEED = 2026
rng = random.Random(SEED)

schedule = get_schedule_data()
matches = schedule["matches"]
group_matches = [m for m in matches if m.get("group") != "淘汰赛"]
knockout_matches = sorted(
    [m for m in matches if m.get("group") == "淘汰赛"],
    key=lambda m: int(str(m["match_no"]).replace("M", ""))
)

team_cache = {}

def team(name):
    if name not in team_cache:
        team_cache[name] = build_team_data(name)
    return team_cache[name]


def probs(home, away):
    return calculate_match_result_prob(team(home), team(away), get_h2h(home, away))


def pick_result(home, away, allow_draw=True):
    p = probs(home, away)
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


standings = defaultdict(lambda: defaultdict(lambda: {"team": "", "pts": 0, "gf": 0, "ga": 0, "gd": 0, "w": 0, "d": 0, "l": 0}))
group_results = []

for match in group_matches:
    group = match["group"]
    home = match["home_team"]
    away = match["away_team"]
    standings[group][home]["team"] = home
    standings[group][away]["team"] = away
    result, p = pick_result(home, away, allow_draw=True)
    hg, ag = score_for_result(result, home, away)

    hrow = standings[group][home]
    arow = standings[group][away]
    hrow["gf"] += hg; hrow["ga"] += ag; hrow["gd"] += hg - ag
    arow["gf"] += ag; arow["ga"] += hg; arow["gd"] += ag - hg
    if hg > ag:
        hrow["pts"] += 3; hrow["w"] += 1; arow["l"] += 1
    elif hg < ag:
        arow["pts"] += 3; arow["w"] += 1; hrow["l"] += 1
    else:
        hrow["pts"] += 1; arow["pts"] += 1; hrow["d"] += 1; arow["d"] += 1

    group_results.append({"match": match["match_no"], "group": group, "home": home, "away": away, "score": f"{hg}-{ag}", "prob": p})


def sort_rows(rows):
    return sorted(
        rows,
        key=lambda r: (r["pts"], r["gd"], r["gf"], calculate_strength_score(team(r["team"]))),
        reverse=True,
    )

group_tables = {g: sort_rows(list(rows.values())) for g, rows in standings.items()}
thirds = sort_rows([rows[2] for rows in group_tables.values() if len(rows) >= 3])[:8]
third_by_group = {g: group_tables[g][2]["team"] for g in group_tables if group_tables[g][2] in thirds}
used_thirds = set()


def resolve_slot(slot):
    slot = str(slot)
    match_group_pos = re.match(r"([A-L])组第([123])", slot)
    if match_group_pos:
        group, pos = match_group_pos.group(1), int(match_group_pos.group(2))
        return group_tables[group][pos - 1]["team"]

    best_third = re.match(r"最佳第3名\((.*?)\)", slot)
    if best_third:
        candidate_groups = best_third.group(1).split("/")
        candidates = [g for g in candidate_groups if g in third_by_group and g not in used_thirds]
        if not candidates:
            candidates = [g for g in third_by_group if g not in used_thirds]
        chosen = max(candidates, key=lambda g: group_tables[g][2]["pts"] * 100 + group_tables[g][2]["gd"] * 10 + group_tables[g][2]["gf"])
        used_thirds.add(chosen)
        return third_by_group[chosen]

    match_winner = re.match(r"M(\d+)胜者", slot)
    if match_winner:
        return winners[f"M{match_winner.group(1)}"]

    return slot

winners = {}
knockout_results = []

for match in knockout_matches:
    home = resolve_slot(match["home_team"])
    away = resolve_slot(match["away_team"])
    result, p = pick_result(home, away, allow_draw=False)
    winner = home if result == "home" else away
    winners[match["match_no"]] = winner
    knockout_results.append({
        "match": match["match_no"],
        "stage": match["stage"],
        "home": home,
        "away": away,
        "winner": winner,
        "home_win": p["home_win"],
        "away_win": p["away_win"],
    })

champion = knockout_results[-1]["winner"]
runner_up = knockout_results[-1]["away"] if knockout_results[-1]["winner"] == knockout_results[-1]["home"] else knockout_results[-1]["home"]
semi_losers = []
for r in knockout_results:
    if "半决赛" in r["stage"]:
        semi_losers.append(r["away"] if r["winner"] == r["home"] else r["home"])

output = {
    "seed": SEED,
    "champion": champion,
    "runner_up": runner_up,
    "semi_losers": semi_losers,
    "group_tables": group_tables,
    "third_qualified": thirds,
    "knockout_results": knockout_results,
}

print(json.dumps(output, ensure_ascii=False, indent=2))
