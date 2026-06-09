import json
import math
import os
import glob
from collections import Counter, defaultdict

from api_client import load_cache, extract_thestats_data
from ai_engine import build_team_data, calculate_match_result_prob, get_h2h

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(BASE_DIR, "thestats_2025_2026_backtest_report.json")
EXCLUDED_COMPETITION_IDS = {"comp_29967"}
EXCLUDED_COMPETITION_NOTE = "排除 International Friendly Games / 友谊赛"


def actual_result(match):
    score = match.get("score") or {}
    home = score.get("home")
    away = score.get("away")
    if home is None or away is None:
        return None
    if home > away:
        return "home_win"
    if home < away:
        return "away_win"
    return "draw"


def safe_prob(value):
    return max(1e-6, min(0.999999, float(value) / 100.0))


def empty_metrics():
    return {"matches": 0, "correct": 0, "log_loss_sum": 0.0, "brier_sum": 0.0, "actual": Counter(), "predicted": Counter()}


def add_metric(bucket, actual, predicted, probs):
    bucket["matches"] += 1
    bucket["correct"] += int(actual == predicted)
    bucket["actual"][actual] += 1
    bucket["predicted"][predicted] += 1
    p_actual = safe_prob(probs[actual])
    bucket["log_loss_sum"] += -math.log(p_actual)
    bucket["brier_sum"] += sum((safe_prob(probs[k]) - (1.0 if k == actual else 0.0)) ** 2 for k in ("home_win", "draw", "away_win"))


def finalize(bucket):
    n = bucket["matches"]
    if not n:
        return {"matches": 0}
    return {
        "matches": n,
        "accuracy": round(bucket["correct"] / n * 100, 2),
        "log_loss": round(bucket["log_loss_sum"] / n, 4),
        "brier_score": round(bucket["brier_sum"] / n, 4),
        "actual_distribution": dict(bucket["actual"]),
        "predicted_distribution": dict(bucket["predicted"]),
    }


def elo_bucket(home_elo, away_elo):
    gap = abs(home_elo - away_elo)
    if gap < 75:
        return "Elo差<75"
    if gap < 150:
        return "Elo差75-150"
    if gap < 250:
        return "Elo差150-250"
    return "Elo差>=250"


def collect_matches():
    unique = {}
    files = glob.glob(os.path.join(BASE_DIR, "data", "cache", "thestats_matches_2024-01-01_2026-06-01_all_*.json"))
    for path in files:
        rows = extract_thestats_data(load_cache(os.path.basename(path), {}) or {})
        for match in rows:
            date = str(match.get("utc_date") or "")
            if not date.startswith(("2025", "2026")):
                continue
            if match.get("status") != "finished":
                continue
            if actual_result(match) is None:
                continue
            if match.get("competition_id") in EXCLUDED_COMPETITION_IDS:
                continue
            match_id = match.get("id")
            if match_id:
                unique[match_id] = match
    return sorted(unique.values(), key=lambda m: m.get("utc_date", ""))


def main():
    matches = collect_matches()
    overall = empty_metrics()
    by_year = defaultdict(empty_metrics)
    by_competition = defaultdict(empty_metrics)
    by_actual = defaultdict(empty_metrics)
    by_elo_gap = defaultdict(empty_metrics)
    samples = []
    skipped = []

    for match in matches:
        home = (match.get("home_team") or {}).get("name")
        away = (match.get("away_team") or {}).get("name")
        if not home or not away:
            skipped.append({"id": match.get("id"), "reason": "missing_team"})
            continue

        try:
            home_team = build_team_data(home)
            away_team = build_team_data(away)
            result = calculate_match_result_prob(home_team, away_team, get_h2h(home, away))
        except Exception as exc:
            skipped.append({"id": match.get("id"), "home": home, "away": away, "reason": str(exc)[:120]})
            continue

        probs = {
            "home_win": result["home_win"],
            "draw": result["draw"],
            "away_win": result["away_win"],
        }
        predicted = max(probs, key=probs.get)
        actual = actual_result(match)
        home_elo = home_team.get("elo_rating", 1450)
        away_elo = away_team.get("elo_rating", 1450)

        for bucket in (
            overall,
            by_year[str(match.get("utc_date", "")[:4])],
            by_competition[str(match.get("competition_id") or "unknown")],
            by_actual[actual],
            by_elo_gap[elo_bucket(home_elo, away_elo)],
        ):
            add_metric(bucket, actual, predicted, probs)

        if len(samples) < 40:
            score = match.get("score") or {}
            samples.append({
                "id": match.get("id"),
                "date": match.get("utc_date"),
                "competition_id": match.get("competition_id"),
                "home": home,
                "away": away,
                "score": f"{score.get('home')}-{score.get('away')}",
                "actual": actual,
                "predicted": predicted,
                "probabilities": probs,
                "home_elo": round(home_elo, 1),
                "away_elo": round(away_elo, 1),
            })

    report = {
        "name": "TheStatsAPI 2025-2026 independent backtest",
        "data_window": "2025-01-01 to 2026-06-01",
        "source": "local TheStatsAPI match cache",
        "excluded_competitions": sorted(EXCLUDED_COMPETITION_IDS),
        "excluded_note": EXCLUDED_COMPETITION_NOTE,
        "method_note": "使用当前生产预测函数计算胜平负概率；TheStatsAPI高级球队特征来自当前缓存，可能包含测试窗口内比赛聚合，因此这是线上模型一致性回测，不是严格时间滚动前瞻回测。",
        "raw_unique_finished_matches": len(matches),
        "evaluated_matches": overall["matches"],
        "skipped_matches": len(skipped),
        "overall": finalize(overall),
        "by_year": {k: finalize(v) for k, v in sorted(by_year.items())},
        "by_competition": {k: finalize(v) for k, v in sorted(by_competition.items())},
        "by_actual_result": {k: finalize(v) for k, v in sorted(by_actual.items())},
        "by_elo_gap": {k: finalize(v) for k, v in sorted(by_elo_gap.items())},
        "sample_predictions": samples,
        "skipped_sample": skipped[:30],
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "evaluated_matches": report["evaluated_matches"],
        "skipped_matches": report["skipped_matches"],
        "overall": report["overall"],
        "by_year": report["by_year"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
