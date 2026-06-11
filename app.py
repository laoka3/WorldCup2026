"""
世界杯足球数据分析Agent - Flask 后端 v4.1
数据来源: API-Football v3 (2022-2024 历史数据 → 2026预测)
核心算法: Elo评分(对手强度归一化) + 赛事加权 + 时间衰减

合规声明：本平台仅为足球赛事数据分析与资讯展示工具，
        不涉及任何彩票、投注、竞猜相关内容。
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from flask import Flask, render_template, jsonify, request
import json
import os
from ai_engine import (
    run_full_analysis, handle_invalid_request,
    get_schedule_data, get_all_team_names,
    build_team_data, calculate_strength_score,
    _load_all_matches, _load_h2h, get_elo_ratings, get_model_calibration,
    get_llm_config, update_llm_config
)

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_monte_carlo_champion_board(team_names, limit=6):
    path = os.path.join(BASE_DIR, "outputs", "simulate_wc2026_monte_carlo_out.json")
    if not os.path.exists(path):
        return None

    for encoding in ("utf-8", "utf-16"):
        try:
            with open(path, "r", encoding=encoding) as f:
                data = json.load(f)
            break
        except UnicodeDecodeError:
            continue
    else:
        return None

    champion_probs = data.get("champion_probabilities", {})
    if not champion_probs:
        return None

    team_set = set(team_names)
    board = []
    for name, probability in champion_probs.items():
        if name not in team_set:
            continue
        team = build_team_data(name)
        board.append({
            "name": name,
            "score": float(probability),
            "score_label": f"{float(probability):.1f}%",
            "bar_width": max(2, min(100, float(probability) * 4)),
            "elo": round(team.get("elo_rating", 1450)),
            "style": team.get("style", "均衡"),
            "games": team.get("games_analyzed", 0),
        })

    board.sort(key=lambda x: x["score"], reverse=True)
    return {
        "title": "v4.5 蒙特卡洛争冠概率榜",
        "subtitle": f"{data.get('runs', 0)}次全赛程模拟",
        "note": "夺冠概率",
        "teams": board[:limit],
        "source": "monte_carlo",
        "runs": data.get("runs", 0),
    }


def build_home_dashboard():
    schedule = get_schedule_data()
    matches = schedule.get("matches", [])
    team_names = get_all_team_names()
    historical_matches = _load_all_matches()
    h2h_data = _load_h2h()
    elo = get_elo_ratings()
    calibration = get_model_calibration()

    group_matches = [m for m in matches if "小组赛" in m.get("stage", "")]
    knockout_matches = [m for m in matches if "小组赛" not in m.get("stage", "")]
    first_matches = [m for m in group_matches if "待定" not in m.get("home_team", "") and "待定" not in m.get("away_team", "")][:8]

    champion_board = load_monte_carlo_champion_board(team_names)
    if champion_board:
        ranked = champion_board["teams"]
    else:
        ranked = []
        for name in team_names:
            team = build_team_data(name)
            score = calculate_strength_score(team)
            ranked.append({
                "name": name,
                "score": score,
                "score_label": f"{score:.2f}",
                "bar_width": score,
                "elo": round(team.get("elo_rating", 1450)),
                "attack": team.get("attack_rating", 70),
                "defense": team.get("defense_rating", 70),
                "style": team.get("style", "均衡"),
                "games": team.get("games_analyzed", 0)
            })
        ranked.sort(key=lambda x: x["score"], reverse=True)
        champion_board = {
            "title": "v4.5 综合实力热度榜",
            "subtitle": "真实历史数据计算",
            "note": "综合实力分",
            "teams": ranked[:6],
            "source": "strength_score",
            "runs": 0,
        }

    return {
        "stats": {
            "teams": len(team_names),
            "matches": len(matches),
            "groups": len(schedule.get("groups", {})),
            "venues": len(schedule.get("venues", [])),
            "historical_matches": len(historical_matches),
            "h2h_records": len(h2h_data),
            "group_matches": len(group_matches),
            "knockout_matches": len(knockout_matches),
            "elo_teams": len(elo),
            "validation_matches": calibration["metrics"]["matches"],
            "log_loss": calibration["metrics"]["log_loss"],
            "brier_score": calibration["metrics"]["brier_score"],
            "accuracy": calibration["metrics"]["accuracy"],
        },
        "top_teams": champion_board["teams"],
        "champion_board": champion_board,
        "first_matches": first_matches,
        "groups": schedule.get("groups", {}),
        "hosts": schedule.get("hosts", ["美国", "加拿大", "墨西哥"]),
        "data_note": f"FIFA 2026官方赛程(北京时间) · API-Football 2022-2024国家队比赛 {len(historical_matches)} 场 · H2H {len(h2h_data)} 条 · Elo球队 {len(elo)} 支"
    }


@app.route("/")
def index():
    schedule = get_schedule_data()
    dashboard = build_home_dashboard()
    return render_template("index.html",
                           matches=dashboard["first_matches"],
                           tournament=schedule.get("tournament", "FIFA World Cup"),
                           groups=dashboard["groups"],
                           dashboard=dashboard)


@app.route("/schedule")
def schedule_page():
    schedule = get_schedule_data()
    groups = {}
    for match in schedule.get("matches", []):
        group = match.get("group", "淘汰赛")
        if group not in groups:
            groups[group] = []
        groups[group].append(match)

    group_order = sorted([g for g in groups if g != "淘汰赛"]) + (["淘汰赛"] if "淘汰赛" in groups else [])
    sorted_groups = {g: groups[g] for g in group_order}

    return render_template("schedule.html",
                           groups=sorted_groups,
                           tournament=schedule.get("tournament", "FIFA World Cup"),
                           group_info=schedule.get("groups", {}),
                           stats={
                               "total_matches": len(schedule.get("matches", [])),
                               "groups": len(schedule.get("groups", {})),
                               "venues": len(schedule.get("venues", [])),
                               "hosts": " · ".join(schedule.get("hosts", ["美国", "加拿大", "墨西哥"])),
                           })


@app.route("/analysis")
def analysis_page():
    team_names = get_all_team_names()
    dashboard = build_home_dashboard()
    return render_template("analysis.html", team_names=team_names, top_teams=dashboard["top_teams"], stats=dashboard["stats"])


@app.route("/about")
def about_page():
    dashboard = build_home_dashboard()
    return render_template("about.html", stats=dashboard["stats"], data_note=dashboard["data_note"])


@app.route("/api/teams")
def api_teams():
    return jsonify([{"name": n} for n in get_all_team_names()])


@app.route("/api/schedule")
def api_schedule():
    return jsonify(get_schedule_data())


@app.route("/api/llm-config", methods=["GET", "POST"])
def api_llm_config():
    if request.method == "GET":
        return jsonify(get_llm_config())

    data = request.get_json() or {}
    try:
        config = update_llm_config(
            base_url=data.get("base_url"),
            model=data.get("model"),
            api_key=data.get("api_key"),
            timeout=data.get("timeout"),
        )
        return jsonify(config)
    except (TypeError, ValueError):
        return jsonify({"error": "大模型配置参数无效"}), 400


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json()
    if not data:
        return jsonify({"error": "请提供有效的请求数据"}), 400

    home_team = data.get("home_team", "").strip()
    away_team = data.get("away_team", "").strip()
    user_text = data.get("text", "")

    blocked = handle_invalid_request(user_text)
    if blocked:
        return jsonify(blocked), 400

    if not home_team or not away_team:
        return jsonify({"error": "请选择两支球队进行分析"}), 400

    if home_team == away_team:
        return jsonify({"error": "请选择两支不同的球队"}), 400

    result = run_full_analysis(home_team, away_team)
    if "error" in result:
        return jsonify(result), 400

    return jsonify(result)


if __name__ == "__main__":
    print("=" * 60)
    print("[WorldSoccer AI v4.1] 2026世界杯数据分析Agent 启动中...")
    print("[WorldSoccer AI] 数据源: API-Football 2022-2024 -> 2026 预测")
    print("[WorldSoccer AI] 算法: Elo评分 + 赛事加权 + 时间衰减 + 对手强度归一化")
    print("[WorldSoccer AI] 访问: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
