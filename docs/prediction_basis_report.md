# Prediction Basis Report

Generated for the first-stage WorldCup2026 refactor.

## Current Win/Draw/Loss Probability Basis

The production probability path is `run_full_analysis()` -> `build_team_data()` -> `calculate_match_result_prob()`.

Current preferred modules:

- Elo/team baseline from `qualification_friendlies_team_profiles.json` when API-Football 2026 qualification/friendlies data is available.
- Local static team profile fallback from `data/teams.json`.
- H2H adjustment from `historical_h2h.json` when available and sample size reaches the configured threshold.
- TheStatsAPI enrichment from `thestats_team_enrichment.json` when available. This is optional only; the base model does not require it.
- Dixon-Coles score-model blending if enabled by calibration params.
- Local pre-match context agent from `wc2026_schedule.json` and built-in venue/altitude table.
- New first-stage recent friendlies agent from `recent_friendlies_2025_2026.json`.
- New first-stage market expectation signal from `market_odds.json`.

If historical cache files are missing, the current model falls back to defaults such as Elo `1450`, attack/defense/midfield `70`, xG `1.0`, xGA `1.0`, and generic goal rates. These defaults are placeholders, not real team strength.

## Current Score Distribution Basis

`calculate_possible_scores()` uses `estimate_expected_goals()` and a Dixon-Coles adjusted Poisson distribution.

Main inputs:

- xG/xGA from TheStatsAPI enrichment when available.
- Historical average goals for/against and attack/defense ratings when available.
- Default xG, xGA, and default attack/defense ratings when caches are missing.
- The final win/draw/loss probabilities are used to calibrate score outcome buckets.

The score distribution is a probability surface, not a deterministic score forecast.

## Current Local Cache Health

Checked files:

- `data/cache/wc2026_schedule.json`: available, 104 matches.
- `data/cache/qualification_friendlies_matches.json`: present but empty because the current API-Football plan does not expose 2025/2026 fixtures.
- `data/cache/qualification_friendlies_team_profiles.json`: present but empty for the same API-plan reason.
- `data/cache/historical_h2h.json`: available after API-Football H2H sync for Mexico vs South Africa.
- `data/cache/thestats_team_enrichment.json`: missing.
- `outputs/model_calibration_v4_4_thestats_out.json`: available.

Current warning:

The preferred qualification/friendlies cache is empty because the current API-Football plan reports that 2025/2026 fixture seasons are not available. The model therefore uses local static team profiles where available and explicit default placeholders otherwise. TheStats is optional and does not need to be obtained for the base model.

## Data Source Strategy

### Recent Friendlies / International Friendlies

Priority:

1. Local/public CSV import: `data/imports/international_results.csv`. If absent, the importer tries to download `martj42/international_results` `results.csv`.
2. API-Football / API-Sports when the active plan exposes target seasons.
3. Compliant scraper adapter, disabled by default.
4. Manual JSON/CSV import.

CSV import:

- Script: `scripts/import_international_results_csv.py`
- Auto download source provider: `martj42/international_results`
- Auto download source URL: `https://raw.githubusercontent.com/martj42/international_results/master/results.csv`
- Input fields: `date`, `home_team`, `away_team`, `home_score`, `away_score`, `tournament`, `city`, `country`, `neutral`
- Qualification range: `2023-01-01` to match day
- Recent friendlies range: `2025-01-01` to match day
- Output caches: `qualification_matches.json`, `recent_friendlies_2025_2026.json`, `qualification_friendlies_team_profiles.json`

API source:

- Source provider: API-Football / API-Sports
- Source endpoint: `fixtures`
- Target competition: International Friendlies / Friendlies
- Target range: `2025-01-01` to match day

Required fields:

- `fixture.id`
- `fixture.date`
- `league.name`
- `league.id`
- `teams.home.name`
- `teams.away.name`
- `goals.home`
- `goals.away`
- `score.fulltime.home`
- `score.fulltime.away`
- `venue.name`
- `venue.city`
- `fixture.status.short`

Fallback sources reserved for later:

- TheSportsDB
- football-data.org

First-stage behavior: no web scraping and no fabricated match results. If the cache is empty or missing, the recent friendlies agent returns `elo_delta = 0`, `confidence = "none"`, and a warning.
If the public CSV maximum date is earlier than `2025-01-01`, cache meta includes: `The public CSV does not cover recent 2025/2026 friendlies or qualifiers. Recent form cache may be incomplete.`

### Market Expectation Signal

Primary source:

- The Odds API v4
- Sport key: `soccer_fifa_world_cup`
- Endpoint: `/v4/sports/soccer_fifa_world_cup/odds`
- Markets: `h2h`, `spreads`, `totals`
- `oddsFormat`: decimal
- `regions`: eu or uk
- Output cache: `data/cache/market_odds.json`
- Empty response, unsupported plan, request failure, or no local schedule match: disabled market signal, `market_weight = 0`

Fallback/source priority:

- A. The Odds API
- B. API-Football odds if the active plan supports odds
- C. TheStatsAPI odds if available
- D. Compliance-first web scraper adapter, disabled by default
- E. Manual CSV/JSON import

Manual import fallback: `scripts/import_market_odds_csv.py` can still import `data/imports/market_odds.csv`. If that CSV is missing, it writes an empty `market_odds.json` with warning `No market_odds.csv found. Market odds signal disabled.` The market expectation signal returns `market_weight = 0` and does not alter probabilities.

Market data wording rule:

盘口数据仅用于概率校准和市场预期参考，不构成投注建议。

## New First-Stage Interfaces

- `check_prediction_data_health()`: reports cache availability and warnings.
- `load_recent_friendlies()`: loads `data/cache/recent_friendlies_2025_2026.json`.
- `calculate_recent_friendlies_adjustment(team_name, match_date=None)`: converts real cached friendly results into a bounded Elo delta.
- `load_market_odds()`: loads `data/cache/market_odds.json`.
- `calculate_market_odds_signal(home_team, away_team, match_date=None)`: converts 1X2 decimal odds into de-vigged implied probabilities and a bounded market weight.

## First-Stage Cache Files

- `data/cache/recent_friendlies_2025_2026.sample.json`: schema example only.
- `data/cache/recent_friendlies_2025_2026.json`: real cache placeholder with empty teams and warning.
- `data/cache/market_odds.sample.json`: schema example only.
- `data/cache/market_odds.json`: real cache placeholder with empty matches and warning.

## First-Stage Scripts

- `scripts/import_international_results_csv.py`: preferred local CSV importer for qualification and recent friendlies.
- `scripts/import_market_odds_csv.py`: preferred manual/exported market expectation signal importer.
- `scripts/sync_recent_friendlies.py`: reads `.env`, reads the 48 teams from `wc2026_schedule.json`, and writes an empty cache with TODO/source metadata.
- `scripts/sync_qualification_friendlies.py`: API-Football adapter with read-through fallback and plan-limit warnings.
- `scripts/sync_h2h_api_football.py`: structured API-Football H2H sync.
- `scripts/sync_market_odds.py`: reads `.env`, reads the 104 scheduled matches, and writes an empty market cache with TODO/source metadata.
- `scripts/backtest_with_market_and_friendlies.py`: writes a skeleton comparison report. If coverage is low, it reports `coverage insufficient` and does not claim model improvement.
