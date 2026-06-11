"""
2026 世界杯官方赛程构建器
数据字段来源: FIFA 官方赛程页面 / 赛程表公开信息
时间展示: 北京时间 UTC+8
说明: 原始开球时间按 ET(北美东部夏令时)录入，统一 +12 小时换算为北京时间。
"""

import json
import os
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_ROOT, "data", "cache")

TEAM_CN = {
    "Mexico": "墨西哥", "South Africa": "南非", "South Korea": "韩国", "Korea Republic": "韩国", "Czechia": "捷克",
    "Canada": "加拿大", "Bosnia and Herzegovina": "波黑", "USA": "美国", "Paraguay": "巴拉圭",
    "Qatar": "卡塔尔", "Switzerland": "瑞士", "Brazil": "巴西", "Morocco": "摩洛哥", "Haiti": "海地", "Scotland": "苏格兰",
    "Australia": "澳大利亚", "Türkiye": "土耳其", "Turkey": "土耳其", "Germany": "德国", "Curaçao": "库拉索", "Curacao": "库拉索",
    "Netherlands": "荷兰", "Japan": "日本", "Ivory Coast": "科特迪瓦", "Côte d'Ivoire": "科特迪瓦", "Ecuador": "厄瓜多尔",
    "Sweden": "瑞典", "Tunisia": "突尼斯", "Spain": "西班牙", "Cabo Verde": "佛得角", "Cape Verde": "佛得角",
    "Belgium": "比利时", "Egypt": "埃及", "Saudi Arabia": "沙特阿拉伯", "Uruguay": "乌拉圭", "Iran": "伊朗", "IR Iran": "伊朗",
    "New Zealand": "新西兰", "France": "法国", "Senegal": "塞内加尔", "Iraq": "伊拉克", "Norway": "挪威",
    "Argentina": "阿根廷", "Algeria": "阿尔及利亚", "Austria": "奥地利", "Jordan": "约旦", "Portugal": "葡萄牙",
    "DR Congo": "刚果民主共和国", "Uzbekistan": "乌兹别克斯坦", "Colombia": "哥伦比亚", "England": "英格兰", "Croatia": "克罗地亚",
    "Ghana": "加纳", "Panama": "巴拿马",
    "2nd Group A": "A组第2", "2nd Group B": "B组第2", "1st Group C": "C组第1", "2nd Group F": "F组第2",
    "1st Group E": "E组第1", "Best 3rd (A/B/C/D/F)": "最佳第3名(A/B/C/D/F)", "1st Group F": "F组第1", "2nd Group C": "C组第2",
    "2nd Group E": "E组第2", "2nd Group I": "I组第2", "1st Group I": "I组第1", "Best 3rd (C/D/F/G/H)": "最佳第3名(C/D/F/G/H)",
    "1st Group A": "A组第1", "Best 3rd (C/E/F/H/I)": "最佳第3名(C/E/F/H/I)", "1st Group L": "L组第1", "Best 3rd (E/H/I/J/K)": "最佳第3名(E/H/I/J/K)",
    "1st Group G": "G组第1", "Best 3rd (A/E/H/I/J)": "最佳第3名(A/E/H/I/J)", "1st Group D": "D组第1", "Best 3rd (B/E/F/I/J)": "最佳第3名(B/E/F/I/J)",
    "1st Group H": "H组第1", "2nd Group J": "J组第2", "2nd Group K": "K组第2", "2nd Group L": "L组第2", "1st Group B": "B组第1",
    "Best 3rd (E/F/G/I/J)": "最佳第3名(E/F/G/I/J)", "2nd Group D": "D组第2", "2nd Group G": "G组第2", "1st Group J": "J组第1", "2nd Group H": "H组第2",
    "1st Group K": "K组第1", "Best 3rd (D/E/I/J/L)": "最佳第3名(D/E/I/J/L)",
    "Winner M73": "M73胜者", "Winner M74": "M74胜者", "Winner M75": "M75胜者", "Winner M76": "M76胜者", "Winner M77": "M77胜者", "Winner M78": "M78胜者",
    "Winner M79": "M79胜者", "Winner M80": "M80胜者", "Winner M81": "M81胜者", "Winner M82": "M82胜者", "Winner M83": "M83胜者", "Winner M84": "M84胜者",
    "Winner M85": "M85胜者", "Winner M86": "M86胜者", "Winner M87": "M87胜者", "Winner M88": "M88胜者", "Winner M89": "M89胜者", "Winner M90": "M90胜者",
    "Winner M91": "M91胜者", "Winner M92": "M92胜者", "Winner M93": "M93胜者", "Winner M94": "M94胜者", "Winner M95": "M95胜者", "Winner M96": "M96胜者",
    "Winner M97": "M97胜者", "Winner M98": "M98胜者", "Winner M99": "M99胜者", "Winner M100": "M100胜者", "Winner M101": "M101胜者", "Winner M102": "M102胜者",
    "Loser M101": "M101负者", "Loser M102": "M102负者",
}

FLAGS = {
    "墨西哥": "🇲🇽", "南非": "🇿🇦", "韩国": "🇰🇷", "捷克": "🇨🇿", "加拿大": "🇨🇦", "波黑": "🇧🇦", "美国": "🇺🇸", "巴拉圭": "🇵🇾",
    "卡塔尔": "🇶🇦", "瑞士": "🇨🇭", "巴西": "🇧🇷", "摩洛哥": "🇲🇦", "海地": "🇭🇹", "苏格兰": "🏴", "澳大利亚": "🇦🇺", "土耳其": "🇹🇷",
    "德国": "🇩🇪", "库拉索": "🇨🇼", "荷兰": "🇳🇱", "日本": "🇯🇵", "科特迪瓦": "🇨🇮", "厄瓜多尔": "🇪🇨", "瑞典": "🇸🇪", "突尼斯": "🇹🇳",
    "西班牙": "🇪🇸", "佛得角": "🇨🇻", "比利时": "🇧🇪", "埃及": "🇪🇬", "沙特阿拉伯": "🇸🇦", "乌拉圭": "🇺🇾", "伊朗": "🇮🇷", "新西兰": "🇳🇿",
    "法国": "🇫🇷", "塞内加尔": "🇸🇳", "伊拉克": "🇮🇶", "挪威": "🇳🇴", "阿根廷": "🇦🇷", "阿尔及利亚": "🇩🇿", "奥地利": "🇦🇹", "约旦": "🇯🇴",
    "葡萄牙": "🇵🇹", "刚果民主共和国": "🇨🇩", "乌兹别克斯坦": "🇺🇿", "哥伦比亚": "🇨🇴", "英格兰": "🏴", "克罗地亚": "🇭🇷", "加纳": "🇬🇭", "巴拿马": "🇵🇦",
}

GROUP_ROWS = [
    (1,"2026-06-11","A","Mexico","South Africa","3:00 PM","Mexico City Stadium (Estadio Azteca)"),
    (2,"2026-06-11","A","South Korea","Czechia","10:00 PM","Guadalajara Stadium (Estadio Akron), Zapopan"),
    (3,"2026-06-12","B","Canada","Bosnia and Herzegovina","3:00 PM","Toronto Stadium (BMO Field)"),
    (4,"2026-06-12","D","USA","Paraguay","9:00 PM","Los Angeles Stadium (SoFi)"),
    (5,"2026-06-13","B","Qatar","Switzerland","3:00 PM","San Francisco Bay Area Stadium (Levi’s)"),
    (6,"2026-06-13","C","Brazil","Morocco","6:00 PM","New York New Jersey Stadium (MetLife)"),
    (7,"2026-06-13","C","Haiti","Scotland","9:00 PM","Boston Stadium (Gillette)"),
    (8,"2026-06-14","D","Australia","Türkiye","12:00 AM","BC Place, Vancouver"),
    (9,"2026-06-14","E","Germany","Curaçao","1:00 PM","Houston Stadium (NRG)"),
    (10,"2026-06-14","F","Netherlands","Japan","4:00 PM","Dallas Stadium (AT&T)"),
    (11,"2026-06-14","E","Ivory Coast","Ecuador","7:00 PM","Philadelphia Stadium (Lincoln Financial)"),
    (12,"2026-06-14","F","Sweden","Tunisia","10:00 PM","Monterrey Stadium (Estadio BBVA), Guadalupe"),
    (13,"2026-06-15","H","Spain","Cabo Verde","12:00 PM","Atlanta Stadium (Mercedes-Benz)"),
    (14,"2026-06-15","G","Belgium","Egypt","3:00 PM","Seattle Stadium (Lumen Field)"),
    (15,"2026-06-15","H","Saudi Arabia","Uruguay","6:00 PM","Miami Stadium (Hard Rock)"),
    (16,"2026-06-15","G","Iran","New Zealand","9:00 PM","Los Angeles Stadium (SoFi)"),
    (17,"2026-06-16","I","France","Senegal","3:00 PM","New York New Jersey Stadium (MetLife)"),
    (18,"2026-06-16","I","Iraq","Norway","6:00 PM","Boston Stadium (Gillette)"),
    (19,"2026-06-16","J","Argentina","Algeria","9:00 PM","Kansas City Stadium (Arrowhead)"),
    (20,"2026-06-17","J","Austria","Jordan","12:00 AM","San Francisco Bay Area Stadium (Levi’s)"),
    (21,"2026-06-17","K","Portugal","DR Congo","1:00 PM","Houston Stadium (NRG)"),
    (22,"2026-06-17","L","England","Croatia","4:00 PM","Dallas Stadium (AT&T)"),
    (23,"2026-06-17","L","Ghana","Panama","7:00 PM","Toronto Stadium (BMO Field)"),
    (24,"2026-06-17","K","Uzbekistan","Colombia","10:00 PM","Mexico City Stadium (Estadio Azteca)"),
    (25,"2026-06-18","A","Czechia","South Africa","12:00 PM","Atlanta Stadium (Mercedes-Benz)"),
    (26,"2026-06-18","B","Switzerland","Bosnia and Herzegovina","3:00 PM","Los Angeles Stadium (SoFi)"),
    (27,"2026-06-18","B","Canada","Qatar","6:00 PM","BC Place, Vancouver"),
    (28,"2026-06-18","A","Mexico","South Korea","9:00 PM","Guadalajara Stadium (Estadio Akron), Zapopan"),
    (29,"2026-06-19","D","Türkiye","Paraguay","12:00 AM","San Francisco Bay Area Stadium (Levi’s)"),
    (30,"2026-06-19","D","USA","Australia","3:00 PM","Seattle Stadium (Lumen Field)"),
    (31,"2026-06-19","C","Scotland","Morocco","6:00 PM","Boston Stadium (Gillette)"),
    (32,"2026-06-19","C","Brazil","Haiti","8:30 PM","Philadelphia Stadium (Lincoln Financial)"),
    (33,"2026-06-20","F","Netherlands","Sweden","1:00 PM","Houston Stadium (NRG)"),
    (34,"2026-06-20","E","Germany","Ivory Coast","4:00 PM","Toronto Stadium (BMO Field)"),
    (35,"2026-06-20","E","Ecuador","Curaçao","8:00 PM","Kansas City Stadium (Arrowhead)"),
    (36,"2026-06-21","F","Tunisia","Japan","12:00 AM","Monterrey Stadium (Estadio BBVA), Guadalupe"),
    (37,"2026-06-21","H","Spain","Saudi Arabia","12:00 PM","Atlanta Stadium (Mercedes-Benz)"),
    (38,"2026-06-21","G","Belgium","Iran","3:00 PM","Los Angeles Stadium (SoFi)"),
    (39,"2026-06-21","H","Uruguay","Cabo Verde","6:00 PM","Miami Stadium (Hard Rock)"),
    (40,"2026-06-21","G","New Zealand","Egypt","9:00 PM","BC Place, Vancouver"),
    (41,"2026-06-22","J","Argentina","Austria","1:00 PM","Dallas Stadium (AT&T)"),
    (42,"2026-06-22","I","France","Iraq","5:00 PM","Philadelphia Stadium (Lincoln Financial)"),
    (43,"2026-06-22","I","Norway","Senegal","8:00 PM","New York New Jersey Stadium (MetLife)"),
    (44,"2026-06-22","J","Jordan","Algeria","11:00 PM","San Francisco Bay Area Stadium (Levi’s)"),
    (45,"2026-06-23","K","Portugal","Uzbekistan","1:00 PM","Houston Stadium (NRG)"),
    (46,"2026-06-23","L","England","Ghana","4:00 PM","Boston Stadium (Gillette)"),
    (47,"2026-06-23","L","Panama","Croatia","7:00 PM","Toronto Stadium (BMO Field)"),
    (48,"2026-06-23","K","Colombia","DR Congo","10:00 PM","Guadalajara Stadium (Estadio Akron), Zapopan"),
    (49,"2026-06-24","B","Switzerland","Canada","3:00 PM","BC Place, Vancouver"),
    (50,"2026-06-24","B","Bosnia and Herzegovina","Qatar","3:00 PM","Seattle Stadium (Lumen Field)"),
    (51,"2026-06-24","C","Scotland","Brazil","6:00 PM","Miami Stadium (Hard Rock)"),
    (52,"2026-06-24","C","Morocco","Haiti","6:00 PM","Atlanta Stadium (Mercedes-Benz)"),
    (53,"2026-06-24","A","Czechia","Mexico","9:00 PM","Mexico City Stadium (Estadio Azteca)"),
    (54,"2026-06-24","A","South Africa","South Korea","9:00 PM","Monterrey Stadium (Estadio BBVA), Guadalupe"),
    (55,"2026-06-25","E","Curaçao","Ivory Coast","4:00 PM","Philadelphia Stadium (Lincoln Financial)"),
    (56,"2026-06-25","E","Ecuador","Germany","4:00 PM","New York New Jersey Stadium (MetLife)"),
    (57,"2026-06-25","F","Japan","Sweden","7:00 PM","Dallas Stadium (AT&T)"),
    (58,"2026-06-25","F","Tunisia","Netherlands","7:00 PM","Kansas City Stadium (Arrowhead)"),
    (59,"2026-06-25","D","Türkiye","USA","10:00 PM","Los Angeles Stadium (SoFi)"),
    (60,"2026-06-25","D","Paraguay","Australia","10:00 PM","San Francisco Bay Area Stadium (Levi’s)"),
    (61,"2026-06-26","I","Norway","France","3:00 PM","Boston Stadium (Gillette)"),
    (62,"2026-06-26","I","Senegal","Iraq","3:00 PM","Toronto Stadium (BMO Field)"),
    (63,"2026-06-26","H","Cabo Verde","Saudi Arabia","8:00 PM","Houston Stadium (NRG)"),
    (64,"2026-06-26","H","Uruguay","Spain","8:00 PM","Guadalajara Stadium (Estadio Akron), Zapopan"),
    (65,"2026-06-26","G","Egypt","Iran","11:00 PM","Seattle Stadium (Lumen Field)"),
    (66,"2026-06-26","G","New Zealand","Belgium","11:00 PM","BC Place, Vancouver"),
    (67,"2026-06-27","L","Panama","England","5:00 PM","New York New Jersey Stadium (MetLife)"),
    (68,"2026-06-27","L","Croatia","Ghana","5:00 PM","Philadelphia Stadium (Lincoln Financial)"),
    (69,"2026-06-27","K","Colombia","Portugal","7:30 PM","Miami Stadium (Hard Rock)"),
    (70,"2026-06-27","K","DR Congo","Uzbekistan","7:30 PM","Atlanta Stadium (Mercedes-Benz)"),
    (71,"2026-06-27","J","Algeria","Austria","10:00 PM","Kansas City Stadium (Arrowhead)"),
    (72,"2026-06-27","J","Jordan","Argentina","10:00 PM","Dallas Stadium (AT&T)"),
]

KO_ROWS = [
    (73,"2026-06-28","1/16决赛","2nd Group A","2nd Group B","3:00 PM","Los Angeles Stadium (SoFi)"),
    (76,"2026-06-29","1/16决赛","1st Group C","2nd Group F","1:00 PM","Houston Stadium (NRG)"),
    (74,"2026-06-29","1/16决赛","1st Group E","Best 3rd (A/B/C/D/F)","4:30 PM","Boston Stadium (Gillette)"),
    (75,"2026-06-29","1/16决赛","1st Group F","2nd Group C","9:00 PM","Monterrey Stadium (Estadio BBVA), Guadalupe"),
    (78,"2026-06-30","1/16决赛","2nd Group E","2nd Group I","1:00 PM","Dallas Stadium (AT&T)"),
    (77,"2026-06-30","1/16决赛","1st Group I","Best 3rd (C/D/F/G/H)","5:00 PM","New York New Jersey Stadium (MetLife)"),
    (79,"2026-06-30","1/16决赛","1st Group A","Best 3rd (C/E/F/H/I)","9:00 PM","Mexico City Stadium (Estadio Azteca)"),
    (80,"2026-07-01","1/16决赛","1st Group L","Best 3rd (E/H/I/J/K)","12:00 PM","Atlanta Stadium (Mercedes-Benz)"),
    (82,"2026-07-01","1/16决赛","1st Group G","Best 3rd (A/E/H/I/J)","4:00 PM","Seattle Stadium (Lumen Field)"),
    (81,"2026-07-01","1/16决赛","1st Group D","Best 3rd (B/E/F/I/J)","8:00 PM","San Francisco Bay Area Stadium (Levi’s)"),
    (84,"2026-07-02","1/16决赛","1st Group H","2nd Group J","3:00 PM","Los Angeles Stadium (SoFi)"),
    (83,"2026-07-02","1/16决赛","2nd Group K","2nd Group L","7:00 PM","Toronto Stadium (BMO Field)"),
    (85,"2026-07-02","1/16决赛","1st Group B","Best 3rd (E/F/G/I/J)","11:00 PM","BC Place, Vancouver"),
    (88,"2026-07-03","1/16决赛","2nd Group D","2nd Group G","2:00 PM","Dallas Stadium (AT&T)"),
    (86,"2026-07-03","1/16决赛","1st Group J","2nd Group H","6:00 PM","Miami Stadium (Hard Rock)"),
    (87,"2026-07-03","1/16决赛","1st Group K","Best 3rd (D/E/I/J/L)","9:30 PM","Kansas City Stadium (Arrowhead)"),
    (90,"2026-07-04","1/8决赛","Winner M73","Winner M75","1:00 PM","Houston Stadium (NRG)"),
    (89,"2026-07-04","1/8决赛","Winner M74","Winner M77","5:00 PM","Philadelphia Stadium (Lincoln Financial)"),
    (91,"2026-07-05","1/8决赛","Winner M76","Winner M78","4:00 PM","New York New Jersey Stadium (MetLife)"),
    (92,"2026-07-05","1/8决赛","Winner M79","Winner M80","8:00 PM","Mexico City Stadium (Estadio Azteca)"),
    (93,"2026-07-06","1/8决赛","Winner M83","Winner M84","3:00 PM","Dallas Stadium (AT&T)"),
    (94,"2026-07-06","1/8决赛","Winner M81","Winner M82","8:00 PM","Seattle Stadium (Lumen Field)"),
    (95,"2026-07-07","1/8决赛","Winner M86","Winner M88","12:00 PM","Atlanta Stadium (Mercedes-Benz)"),
    (96,"2026-07-07","1/8决赛","Winner M85","Winner M87","4:00 PM","BC Place, Vancouver"),
    (97,"2026-07-09","1/4决赛","Winner M89","Winner M90","4:00 PM","Boston Stadium (Gillette)"),
    (98,"2026-07-10","1/4决赛","Winner M93","Winner M94","3:00 PM","Los Angeles Stadium (SoFi)"),
    (99,"2026-07-11","1/4决赛","Winner M91","Winner M92","5:00 PM","Miami Stadium (Hard Rock)"),
    (100,"2026-07-11","1/4决赛","Winner M95","Winner M96","9:00 PM","Kansas City Stadium (Arrowhead)"),
    (101,"2026-07-14","半决赛","Winner M97","Winner M98","3:00 PM","Dallas Stadium (AT&T)"),
    (102,"2026-07-15","半决赛","Winner M99","Winner M100","3:00 PM","Atlanta Stadium (Mercedes-Benz)"),
    (103,"2026-07-18","季军赛","Loser M101","Loser M102","5:00 PM","Miami Stadium (Hard Rock)"),
    (104,"2026-07-19","决赛","Winner M101","Winner M102","3:00 PM","New York New Jersey Stadium (MetLife)"),
]


def cn(name):
    return TEAM_CN.get(name, name)


def flag(name):
    return FLAGS.get(name, "⚽")


def et_to_bjt(date_str, time_str):
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M %p")
    bj = dt + timedelta(hours=12)
    return bj.strftime("%Y-%m-%d"), bj.strftime("%H:%M"), bj.isoformat()


def match_stage(match_no, group):
    if match_no <= 24:
        return "小组赛 第1轮"
    if match_no <= 48:
        return "小组赛 第2轮"
    return "小组赛 第3轮"


def make_match(match_no, et_date, group, home, away, et_time, venue, stage=None):
    bj_date, bj_time, bj_iso = et_to_bjt(et_date, et_time)
    h = cn(home)
    a = cn(away)
    return {
        "id": 2026000 + match_no,
        "match_no": f"M{match_no}",
        "group": group,
        "stage": stage or match_stage(match_no, group),
        "home_team": h,
        "away_team": a,
        "home_flag": flag(h),
        "away_flag": flag(a),
        "date": bj_date,
        "time": bj_time,
        "timezone": "北京时间 UTC+8",
        "kickoff_bj": bj_iso,
        "source_date_et": et_date,
        "source_time_et": et_time,
        "source_timezone": "ET/北美东部时间",
        "venue": venue,
        "status": "upcoming",
        "home_score": None,
        "away_score": None,
        "source": "FIFA World Cup 2026 official schedule / public fixture table",
    }


def build():
    matches = []
    for row in GROUP_ROWS:
        match_no, et_date, group, home, away, et_time, venue = row
        matches.append(make_match(match_no, et_date, group, home, away, et_time, venue))

    for row in KO_ROWS:
        match_no, et_date, stage, home, away, et_time, venue = row
        matches.append(make_match(match_no, et_date, "淘汰赛", home, away, et_time, venue, stage=stage))

    matches.sort(key=lambda m: (m["kickoff_bj"], int(m["match_no"][1:])))

    groups = {}
    for m in matches:
        if m["group"] == "淘汰赛":
            continue
        groups.setdefault(m["group"], [])
        for team in (m["home_team"], m["away_team"]):
            if team not in groups[m["group"]]:
                groups[m["group"]].append(team)

    groups = {g: groups[g] for g in sorted(groups)}
    venues = sorted({m["venue"] for m in matches})

    return {
        "tournament": "2026 FIFA World Cup",
        "hosts": ["美国", "加拿大", "墨西哥"],
        "format": "48支球队 · 12个小组 · 104场比赛",
        "time_display": "北京时间 UTC+8",
        "source_timezone": "ET/北美东部时间",
        "conversion_rule": "北京时间 = ET + 12小时（2026年6-7月北美东部夏令时）",
        "data_source": "FIFA World Cup 2026 official schedule / public fixture table",
        "total_matches": len(matches),
        "venues": venues,
        "matches": matches,
        "groups": groups,
    }


def save():
    schedule = build()
    path = os.path.join(CACHE_DIR, "wc2026_schedule.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

    group_count = sum(1 for m in schedule["matches"] if m["group"] != "淘汰赛")
    ko_count = sum(1 for m in schedule["matches"] if m["group"] == "淘汰赛")
    print(f"2026 官方赛程: {len(schedule['matches'])} 场 (小组赛 {group_count} + 淘汰赛 {ko_count})")
    print(f"时间显示: {schedule['time_display']}")
    print(f"首场: {schedule['matches'][0]['home_team']} vs {schedule['matches'][0]['away_team']} {schedule['matches'][0]['date']} {schedule['matches'][0]['time']}")
    print(f"决赛: {schedule['matches'][-1]['home_team']} vs {schedule['matches'][-1]['away_team']} {schedule['matches'][-1]['date']} {schedule['matches'][-1]['time']}")


if __name__ == "__main__":
    save()
