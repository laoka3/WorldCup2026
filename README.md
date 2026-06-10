# WorldCup

WorldCup 是一个面向 2026 世界杯的足球数据分析与预测 Web 应用。项目基于 Flask，结合 Elo、TheStatsAPI 高级数据、Dixon-Coles 修正比分模型、回测校准和蒙特卡洛模拟，提供胜平负概率、可能比分、球队实力对比、赛程展示和冠军概率榜。

## 功能特性

- 2026 世界杯赛程与球队数据展示
- 首页赛程卡片点击后直接进入单场分析并自动预测
- 单场比赛胜平负概率预测
- 赛前情境 Agent：根据真实赛程、场地、东道主和海拔做小幅概率修正
- Dixon-Coles 修正 Poisson 可能比分分布
- TheStatsAPI 高级数据质量评分与权重降级
- v4.5 模型校准与 2025-2026 非友谊赛回测报告
- 100000 次蒙特卡洛模拟冠军概率榜
- 可选大模型赛果解读，仅用于解释本地模型结果，不参与概率计算

## 技术栈

- Python 3
- Flask
- Requests
- HTML / CSS / JavaScript
- Tailwind CDN / Font Awesome CDN

## 项目结构

```text
.
├── app.py                                  # Flask 入口
├── ai_engine.py                            # 核心预测与解读引擎
├── api_client.py                           # API-Football / TheStatsAPI 客户端
├── sync_historical.py                      # 历史数据同步脚本
├── build_wc2026.py                         # 世界杯基础数据构建脚本
├── backtest_thestats_2025_2026.py          # TheStatsAPI 2025-2026 回测
├── search_v44_params.py                    # 参数搜索脚本
├── simulate_wc2026_monte_carlo.py          # 蒙特卡洛模拟脚本
├── simulate_wc2026_once.py                 # 单次世界杯模拟脚本
├── data/
│   ├── teams.json                          # 球队数据
│   ├── schedule.json                       # 早期占位赛程数据
│   ├── news.json                           # 新闻数据
│   └── cache/
│       └── wc2026_schedule.json            # 2026 世界杯官方赛程缓存，含 104 场、场地和北京时间
├── templates/                              # 页面模板
├── static/                                 # 静态资源
├── requirements.txt
└── .gitignore
```

## 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/WJS-WEB/WorldCup.git
cd WorldCup
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

项目不会在代码中保存 API Key。需要按需配置环境变量。

```bash
# API-Football，可选，用于同步历史数据
export APIFOOTBALL_API_KEY="your_api_key"

# TheStatsAPI，可选，用于刷新高级统计数据
export THESTATS_API_KEY="your_api_key"

# 大模型解读，可选，只影响自然语言解释，不影响预测概率，apikey可以在https://api.mirrorworkforce.cn站点申请
export LLM_API_KEY="your_api_key"
export LLM_BASE_URL="https://api.mirrorworkforce.cn/v1"
export LLM_MODEL="gpt-5.5"
export LLM_TIMEOUT="90"

```

Windows PowerShell 示例：

```powershell
$env:THESTATS_API_KEY="your_api_key"
$env:LLM_API_KEY="your_api_key"
$env:LLM_BASE_URL="https://api.mirrorworkforce.cn/v1"
$env:LLM_MODEL="gpt-5.5"
$env:LLM_TIMEOUT="90"
```

### 4. 启动应用

```bash
python app.py
```

浏览器访问：

```text
http://127.0.0.1:5000
```

## 主要页面

- `/`：首页，展示冠军概率榜、球队实力榜、新闻与项目说明
- `/analysis`：单场比赛分析，包含胜平负概率、可能比分、大模型解读、实力对比等
- `/schedule`：赛程页
- `/about`：项目说明页

## API 接口

```text
GET  /api/teams
GET  /api/schedule
GET  /api/llm-config
POST /api/llm-config
POST /api/analyze
```

`POST /api/analyze` 请求示例：

```json
{
  "home_team": "葡萄牙",
  "away_team": "西班牙",
  "text": ""
}
```

## 模型说明

当前核心模型为 v4.5，主要由以下部分组成：

```text
Elo 评分
+ TheStatsAPI 高级数据修正
+ TheStatsAPI 数据质量评分与权重降级
+ H2H 修正
+ 赛前情境 Agent 场地/东道主/海拔修正
+ Dixon-Coles 修正 Poisson 比分模型
+ 回测校准参数
+ 蒙特卡洛模拟
```

大模型只负责解释本地模型输出，不直接修改胜平负概率、预期进球或可能比分。

## 回测与模拟

### TheStatsAPI 2025-2026 非友谊赛回测

```bash
python backtest_thestats_2025_2026.py
```

输出文件：

```text
thestats_2025_2026_backtest_report.json
```

### 参数搜索

```bash
python search_v44_params.py
```

输出文件：

```text
model_calibration_v4_4_thestats_out.json
```

### 蒙特卡洛模拟

```bash
python simulate_wc2026_monte_carlo.py
```

输出文件：

```text
simulate_wc2026_monte_carlo_out.json
```

当前默认模拟次数为 100000 次。

## 数据与安全

- `data/cache/wc2026_schedule.json` 是随仓库提交的 2026 世界杯官方赛程缓存，用于首页赛程和赛前情境 Agent。
- 其他 `data/cache/` 本地 API 缓存默认通过 `.gitignore` 排除。
- `.env`、`.env.*` 已排除。
- 代码中不应提交任何真实 API Key。
- 大模型 API Key 不会在页面回显明文或片段。

## 免责声明

本项目仅用于足球赛事数据分析与模型研究。预测结果是概率性分析，不代表确定赛果，不构成投注、购彩或任何形式的金融建议。
