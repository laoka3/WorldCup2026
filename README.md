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
├── build_wc2026.py                             # 世界杯基础赛程、球队、场馆数据构建脚本
├── sync_historical.py                          # 历史比赛数据同步脚本，需要 APIFOOTBALL_API_KEY
├── backtest_thestats_2025_2026.py              # TheStatsAPI 2025-2026 非友谊赛回测脚本
├── search_v44_params.py                        # v4.4/v4.5 参数搜索脚本
├── simulate_wc2026_once.py                     # 单次世界杯赛程模拟脚本
├── simulate_wc2026_monte_carlo.py              # 多轮蒙特卡洛模拟脚本
├── model_calibration_v4_3_out.json             # v4.3 校准输出
├── model_calibration_v4_4_thestats_out.json    # v4.4 TheStats 校准输出
├── thestats_2025_2026_backtest_report.json     # TheStats 回测报告输出
├── simulate_wc2026_once_out.json               # 单次模拟输出
├── simulate_wc2026_monte_carlo_out.json        # 蒙特卡洛模拟输出
├── data/
│   ├── teams.json                              # 球队基础数据、中文名、能力值等
│   ├── schedule.json                           # 早期占位赛程数据
│   ├── news.json                               # 本地新闻兜底数据
│   └── cache/
│       └── wc2026_schedule.json                # 2026 世界杯官方赛程缓存，含 104 场、场地和北京时间
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

# 运行 TheStatsAPI 回测
python backtest_thestats_2025_2026.py

# 搜索模型参数
python search_v44_params.py

# 运行蒙特卡洛模拟
python simulate_wc2026_monte_carlo.py
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
