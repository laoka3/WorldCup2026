import json
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_engine import _normalize_name


EXPECTED_MISSING_STAGE_ONE = [
    "南非", "捷克", "波黑", "巴拉圭", "卡塔尔", "瑞士", "海地", "苏格兰",
    "土耳其", "库拉索", "科特迪瓦", "厄瓜多尔", "瑞典", "突尼斯", "佛得角",
    "沙特阿拉伯", "新西兰", "伊拉克", "挪威", "阿尔及利亚", "奥地利",
    "约旦", "刚果民主共和国", "加纳", "巴拿马", "乌兹别克斯坦",
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    schedule_path = os.path.join(PROJECT_ROOT, "data", "cache", "wc2026_schedule.json")
    teams_path = os.path.join(PROJECT_ROOT, "data", "teams.json")
    docs_dir = os.path.join(PROJECT_ROOT, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    schedule = load_json(schedule_path)
    teams_data = load_json(teams_path)
    schedule_teams = []
    for group in sorted((schedule.get("groups") or {}).keys()):
        schedule_teams.extend(schedule["groups"][group])

    static_teams = teams_data.get("teams", []) if isinstance(teams_data, dict) else []
    static_names = {team.get("name") for team in static_teams}
    static_normalized = {_normalize_name(team.get("name", "")) for team in static_teams}

    missing = [
        team for team in schedule_teams
        if team not in static_names and _normalize_name(team) not in static_normalized
    ]
    covered = [team for team in schedule_teams if team not in missing]
    expected_missing_set = set(EXPECTED_MISSING_STAGE_ONE)
    missing_not_in_expected = [team for team in missing if team not in expected_missing_set]
    expected_not_missing = [team for team in EXPECTED_MISSING_STAGE_ONE if team not in missing]

    lines = [
        "# Team Profile Audit",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Summary",
        "",
        f"- Schedule teams: {len(schedule_teams)}",
        f"- Static profiles in data/teams.json: {len(static_teams)}",
        f"- Static profiles covered in schedule: {len(covered)}",
        f"- Missing static profiles: {len(missing)}",
        "- Severity: HIGH" if missing else "- Severity: OK",
        "",
        "## High Severity Warning",
        "",
    ]
    if missing:
        lines.extend([
            "The following World Cup 2026 schedule teams do not have a static profile in `data/teams.json`.",
            "They must not be treated as equally reliable as statically anchored teams; generated CSV profiles should be marked `generated_csv_profile_only` until reviewed.",
            "",
        ])
        lines.extend(f"- {team}" for team in missing)
    else:
        lines.append("All schedule teams have static profiles.")

    lines.extend([
        "",
        "## Covered Teams",
        "",
    ])
    lines.extend(f"- {team}" for team in covered)

    lines.extend([
        "",
        "## Expected Stage-One Missing List Check",
        "",
        "The user-specified first-stage missing list is compared against the current schedule audit.",
        "",
        f"- Expected list size: {len(EXPECTED_MISSING_STAGE_ONE)}",
        f"- Missing teams outside expected list: {', '.join(missing_not_in_expected) if missing_not_in_expected else 'None'}",
        f"- Expected teams now covered or absent from schedule missing set: {', '.join(expected_not_missing) if expected_not_missing else 'None'}",
        "",
        "## Notes",
        "",
        "- This script does not fabricate or auto-fill static football data.",
        "- Add reviewed profiles to `data/teams.json` before treating missing teams as statically anchored.",
    ])

    out_path = os.path.join(docs_dir, "team_profile_audit.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {out_path}")
    print(f"Missing static profiles: {len(missing)}")
    if missing:
        print(", ".join(missing))


if __name__ == "__main__":
    main()
