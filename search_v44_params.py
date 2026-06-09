import json
import math
import os
from collections import Counter

from backtest_thestats_2025_2026 import collect_matches, actual_result
from ai_engine import (
    build_team_data,
    calculate_advanced_elo_adjustment,
    get_h2h,
    _normalize_name,
    _predict_probs_from_elo,
    _blend_score_model_probs,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(BASE_DIR, "model_calibration_v4_4_thestats_out.json")


def normalize_h2h(h2h_data, home_name, away_name):
    if not h2h_data:
        return None
    is_home_is_a = _normalize_name(h2h_data.get("team_a", "")) == _normalize_name(home_name)
    return {
        "total": h2h_data.get("total", 0),
        "home_wins": h2h_data.get("a_wins", 0) if is_home_is_a else h2h_data.get("b_wins", 0),
        "draws": h2h_data.get("draws", 0),
        "away_wins": h2h_data.get("b_wins", 0) if is_home_is_a else h2h_data.get("a_wins", 0),
    }


def build_dataset():
    rows = []
    for match in collect_matches():
        home = (match.get("home_team") or {}).get("name")
        away = (match.get("away_team") or {}).get("name")
        if not home or not away:
            continue
        home_team = build_team_data(home)
        away_team = build_team_data(away)
        home_adv = calculate_advanced_elo_adjustment(home_team)
        away_adv = calculate_advanced_elo_adjustment(away_team)
        rows.append({
            "id": match.get("id"),
            "date": match.get("utc_date"),
            "competition_id": match.get("competition_id"),
            "home": home,
            "away": away,
            "home_team": home_team,
            "away_team": away_team,
            "actual": actual_result(match).replace("_win", ""),
            "home_elo": home_team.get("elo_rating", 1450) + home_adv["elo_delta"],
            "away_elo": away_team.get("elo_rating", 1450) + away_adv["elo_delta"],
            "h2h": normalize_h2h(get_h2h(home, away), home, away),
        })
    return rows


def predict_row(row, params):
    probs = _predict_probs_from_elo(row["home_elo"], row["away_elo"], row["h2h"], params)
    probs = _blend_score_model_probs(row["home_team"], row["away_team"], probs, params)
    home_prob = round(probs["home"] * 100, 1)
    draw_prob = round(probs["draw"] * 100, 1)
    away_prob = round(100 - home_prob - draw_prob, 1)
    if away_prob < 0:
        away_prob = 0.0
        total = home_prob + draw_prob
        home_prob = round(home_prob / total * 100, 1)
        draw_prob = round(100 - home_prob, 1)
    return {"home": home_prob / 100, "draw": draw_prob / 100, "away": away_prob / 100}


def evaluate(rows, params):
    log_loss = 0.0
    brier = 0.0
    correct = 0
    actual_counter = Counter()
    predicted_counter = Counter()
    draw_correct = 0

    for row in rows:
        probs = predict_row(row, params)
        actual = row["actual"]
        predicted = max(probs, key=probs.get)
        correct += int(predicted == actual)
        draw_correct += int(actual == "draw" and predicted == "draw")
        actual_counter[actual] += 1
        predicted_counter[predicted] += 1
        log_loss -= math.log(max(1e-6, probs[actual]))
        brier += sum((probs[k] - (1.0 if k == actual else 0.0)) ** 2 for k in ("home", "draw", "away"))

    n = len(rows)
    draw_recall = draw_correct / actual_counter["draw"] * 100 if actual_counter["draw"] else 0.0
    actual_home_ratio = actual_counter["home"] / n if n else 0
    pred_home_ratio = predicted_counter["home"] / n if n else 0
    distribution_penalty = abs(pred_home_ratio - actual_home_ratio)

    return {
        "matches": n,
        "accuracy": round(correct / n * 100, 2),
        "log_loss": round(log_loss / n, 4),
        "brier_score": round(brier / n, 4),
        "draw_recall": round(draw_recall, 2),
        "actual_distribution": dict(actual_counter),
        "predicted_distribution": dict(predicted_counter),
        "distribution_penalty": round(distribution_penalty, 4),
    }


def objective(metrics):
    return metrics["log_loss"] + 0.25 * metrics["brier_score"] + 0.20 * metrics["distribution_penalty"] - 0.002 * metrics["accuracy"]


def main():
    rows = build_dataset()
    candidates = []
    for home_advantage in [30, 40, 45, 50, 60]:
        for elo_scale in [325, 350, 375, 400, 450]:
            for draw_base in [0.24, 0.27, 0.30, 0.33, 0.36]:
                for draw_width in [550, 650, 850, 1050, 1250]:
                    for h2h_max_weight in [0.0, 0.05, 0.1, 0.15]:
                        for score_model_weight in [0.0, 0.08, 0.15, 0.22]:
                            for rho in [-0.12, -0.08, -0.05, -0.03, 0.0]:
                                if score_model_weight == 0.0 and rho != -0.05:
                                    continue
                                params = {
                                    "home_advantage": home_advantage,
                                    "elo_scale": elo_scale,
                                    "draw_base": draw_base,
                                    "draw_width": draw_width,
                                    "h2h_max_weight": h2h_max_weight,
                                    "h2h_min_matches": 3,
                                    "score_model_weight": score_model_weight,
                                    "dixon_coles_rho": rho,
                                }
                                metrics = evaluate(rows, params)
                                candidates.append({"params": params, "metrics": metrics, "objective": round(objective(metrics), 6)})

    candidates_by_objective = sorted(candidates, key=lambda x: x["objective"])
    candidates_by_accuracy = sorted(candidates, key=lambda x: (-x["metrics"]["accuracy"], x["metrics"]["log_loss"]))
    current_params = {
        "home_advantage": 45,
        "elo_scale": 350,
        "draw_base": 0.30,
        "draw_width": 650,
        "h2h_max_weight": 0.15,
        "h2h_min_matches": 3,
        "score_model_weight": 0.0,
        "dixon_coles_rho": -0.05,
    }
    current_metrics = evaluate(rows, current_params)

    report = {
        "version": "v4.5 TheStatsAPI quality + Dixon-Coles parameter search",
        "dataset": "TheStatsAPI 2025-2026 finished matches excluding comp_29967 friendlies",
        "matches": len(rows),
        "objective": "log_loss + 0.25*brier + 0.20*home_prediction_distribution_penalty - 0.002*accuracy",
        "current": {"params": current_params, "metrics": current_metrics, "objective": round(objective(current_metrics), 6)},
        "best_balanced": candidates_by_objective[0],
        "best_accuracy": candidates_by_accuracy[0],
        "top_balanced": candidates_by_objective[:20],
        "top_accuracy": candidates_by_accuracy[:20],
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "matches": report["matches"],
        "current": report["current"],
        "best_balanced": report["best_balanced"],
        "best_accuracy": report["best_accuracy"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
