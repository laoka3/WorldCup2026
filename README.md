# 2026 世界杯蒙特卡洛预测系统

2026 世界杯蒙特卡洛预测系统是一个面向 2026 世界杯的足球数据分析与预测 Web 应用。项目基于 Flask，结合 Elo、TheStatsAPI 高级数据、Dixon-Coles 修正比分模型、回测校准和蒙特卡洛模拟，提供胜平负概率、可能比分、球队实力对比、赛程展示和冠军概率榜。

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

- Python 3.10+
- Flask
- Requests
- HTML / CSS / JavaScript
- Tailwind CDN / Font Awesome CDN

## 项目结构

```text
.
├── app.py                                      # Flask Web 应用入口，定义页面路由和 API 路由
├── ai_engine.py                                # 核心预测、模型校准、新闻与大模型解读逻辑
├── api_client.py                               # API-Football / TheStatsAPI 数据客户端与缓存逻辑
├── data/
│   ├── teams.json                              # 球队基础数据、中文名、能力值等
│   ├── schedule.json                           # 早期占位赛程数据
│   ├── news.json                               # 本地新闻兜底数据
│   └── cache/
│       └── wc2026_schedule.json                # 2026 世界杯官方赛程缓存，含 104 场、场地和北京时间
├── outputs/
│   ├── model_calibration_v4_3_out.json         # v4.3 校准输出
│   ├── model_calibration_v4_4_thestats_out.json # v4.4 TheStats 校准输出，应用启动时会读取
│   ├── thestats_2025_2026_backtest_report.json # TheStats 回测报告输出
│   ├── simulate_wc2026_once_out.json           # 单次模拟输出
│   └── simulate_wc2026_monte_carlo_out.json    # 蒙特卡洛模拟输出，首页冠军概率榜会读取
├── scripts/
│   ├── build_wc2026.py                         # 世界杯基础赛程、球队、场馆数据构建脚本
│   ├── sync_historical.py                      # 历史比赛数据同步脚本，需要 APIFOOTBALL_API_KEY
│   ├── backtest_thestats_2025_2026.py          # TheStatsAPI 2025-2026 非友谊赛回测脚本
│   ├── search_v44_params.py                    # v4.4/v4.5 参数搜索脚本
│   ├── simulate_wc2026_once.py                 # 单次世界杯赛程模拟脚本
│   └── simulate_wc2026_monte_carlo.py          # 多轮蒙特卡洛模拟脚本
├── templates/
│   ├── layout.html                             # 全站基础布局、导航和公共资源
│   ├── index.html                              # 首页
│   ├── analysis.html                           # 单场比赛分析页
│   ├── schedule.html                           # 赛程页
│   └── about.html                              # 项目说明页
├── static/
│   ├── css/
│   │   └── style.css                           # 自定义样式
│   ├── js/
│   │   └── main.js                             # 前端交互脚本
│   └── img/
│       └── news-placeholder.svg                # 新闻占位图
├── requirements.txt                            # Python 运行依赖
├── .gitignore                                  # 本地缓存、密钥和临时文件排除规则
└── README.md
```

## 目录与命名规则

为方便维护，项目按“应用核心、数据、脚本、输出、页面资源”分层：

- 根目录只放应用入口、核心模块和项目级配置：例如 `app.py`、`ai_engine.py`、`api_client.py`、`requirements.txt`。
- `data/` 放应用运行需要读取的数据，文件名使用小写英文和下划线，例如 `teams.json`、`schedule.json`。
- `data/cache/` 放 API 缓存和官方赛程缓存。除 `wc2026_schedule.json` 外，其他本地缓存默认不提交。
- `scripts/` 放一次性或离线任务脚本，命名使用动词开头或任务类型开头，例如 `sync_historical.py`、`simulate_wc2026_monte_carlo.py`。
- `outputs/` 放脚本生成的结果文件，统一使用 `_out.json` 或 `_report.json` 结尾，例如 `model_calibration_v4_4_thestats_out.json`。
- `templates/` 放 Flask/Jinja 页面模板，按页面命名，例如 `analysis.html`、`schedule.html`。
- `static/` 放前端静态资源，按类型拆成 `css/`、`js/`、`img/`。

新增文件时优先使用小写英文、数字和下划线，避免空格、中文文件名和大小写混用。脚本如果会生成文件，默认写入 `outputs/`；脚本如果会缓存 API 响应，默认写入 `data/cache/`。

## 第一次使用

项目可以在 macOS 和 Windows 上直接用 Python 虚拟环境运行。首次使用建议先确认 Python 版本：

```bash
python --version
```

如果系统里同时装了多个 Python 版本，macOS 通常使用 `python3`，Windows 通常使用 `py -3`。

### macOS 配置环境

1. 克隆仓库并进入目录：

```bash
git clone https://github.com/WJS-WEB/WorldCup.git
cd WorldCup
```

2. 创建并启用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. 升级 pip 并安装依赖：

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4. 按需配置环境变量：

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

5. 启动应用：

```bash
python app.py
```

浏览器访问：

```text
http://127.0.0.1:5000
```

### Windows 配置环境

以下命令在 PowerShell 中执行。

1. 克隆仓库并进入目录：

```powershell
git clone https://github.com/WJS-WEB/WorldCup.git
cd WorldCup
```

2. 创建并启用虚拟环境：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

如果 PowerShell 提示脚本执行策略限制，可以只对当前用户放开本地脚本执行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

3. 升级 pip 并安装依赖：

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4. 按需配置环境变量：

```powershell
$env:APIFOOTBALL_API_KEY="your_api_key"
$env:THESTATS_API_KEY="your_api_key"
$env:LLM_API_KEY="your_api_key"
$env:LLM_BASE_URL="https://api.mirrorworkforce.cn/v1"
$env:LLM_MODEL="gpt-5.5"
$env:LLM_TIMEOUT="90"
```

5. 启动应用：

```powershell
python app.py
```

浏览器访问：

```text
http://127.0.0.1:5000
```

### 环境变量说明

所有环境变量都是可选项，不配置也可以使用仓库内置数据启动页面和本地预测。需要刷新外部数据或启用大模型解读时再配置对应 Key。

| 变量名 | 是否必需 | 用途 |
| --- | --- | --- |
| `APIFOOTBALL_API_KEY` | 可选 | API-Football 历史比赛数据同步 |
| `THESTATS_API_KEY` | 可选 | TheStatsAPI 高级统计数据刷新 |
| `LLM_API_KEY` | 可选 | 大模型赛果解读 |
| `LLM_BASE_URL` | 可选 | 大模型接口地址，默认 `https://api.mirrorworkforce.cn/v1` |
| `LLM_MODEL` | 可选 | 大模型名称，默认 `gpt-5.5` |
| `LLM_TIMEOUT` | 可选 | 大模型请求超时时间，默认 `20` 秒 |
| `BING_NEWS_API_KEY` | 可选 | 新闻搜索接口 Key |
| `BING_NEWS_API_HOST` | 可选 | 新闻搜索接口 Host |
| `BING_NEWS_API_URL` | 可选 | 新闻搜索接口 URL |

### 常用命令

```bash
# 启动 Web 应用
python app.py

# 自动下载并导入公开国际赛果 CSV（预选赛 + 最近热身赛）
python scripts/import_international_results_csv.py

# 优先：从 The Odds API 同步市场预期信号；无返回时会写 warning 并禁用市场信号
python scripts/sync_market_odds.py

# 备用：导入手动/外部导出的市场预期信号 CSV；没有 CSV 时会禁用市场信号
python scripts/import_market_odds_csv.py

# 可选：尝试 API-Football 同步预选赛/热身赛；free plan 可能不开放 2025/2026 fixtures
python scripts/sync_qualification_friendlies.py

# 可选：同步指定对阵 H2H
python scripts/sync_h2h_api_football.py --home 墨西哥 --away 南非

# 运行 TheStatsAPI 回测
python scripts/backtest_thestats_2025_2026.py

# 搜索模型参数
python scripts/search_v44_params.py

# 运行蒙特卡洛模拟
python scripts/simulate_wc2026_monte_carlo.py
```

## 数据源优先级

当前主模型优先使用世界杯预选赛、最近热身赛/友谊赛、H2H、市场预期信号、本地球队画像和赛程/场地情境。TheStatsAPI 只作为可选高级增强，缺失时不影响基础模型运行。

预选赛和热身赛结果优先从 `data/imports/international_results.csv` 导入。如果文件不存在，`scripts/import_international_results_csv.py` 会尝试自动下载公开数据源 `martj42/international_results` 的 `results.csv`：`https://raw.githubusercontent.com/martj42/international_results/master/results.csv`。支持字段：`date`、`home_team`、`away_team`、`home_score`、`away_score`、`tournament`、`city`、`country`、`neutral`。

市场预期信号优先通过 `scripts/sync_market_odds.py` 从 The Odds API v4 同步 `soccer_fifa_world_cup` 的 `h2h`、`spreads`、`totals` 市场，并写入 `data/cache/market_odds.json`。如果 The Odds API 当前没有 upcoming odds、plan 不支持或没有匹配本地赛程，会生成空缓存和 warning，`market_weight = 0`，不会改变概率。`data/imports/market_odds.csv` 仍作为手动/外部导出的备用导入方式。后续可接 API-Football odds（如果 plan 支持）或 TheStatsAPI odds。盘口数据仅用于概率校准和市场预期参考，不构成投注建议。

### 数据准备顺序

```bash
# 1. 自动下载并导入国际比赛结果
python scripts/import_international_results_csv.py

# 2. 优先：同步 The Odds API 市场预期信号
python scripts/sync_market_odds.py

# 2b. 备用：导入市场预期信号 CSV
python scripts/import_market_odds_csv.py

# 3. 启动项目
python app.py
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
python scripts/backtest_thestats_2025_2026.py
```

输出文件：

```text
outputs/thestats_2025_2026_backtest_report.json
```

### 参数搜索

```bash
python scripts/search_v44_params.py
```

输出文件：

```text
outputs/model_calibration_v4_4_thestats_out.json
```

### 蒙特卡洛模拟

```bash
python scripts/simulate_wc2026_monte_carlo.py
```

输出文件：

```text
outputs/simulate_wc2026_monte_carlo_out.json
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
