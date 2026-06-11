# Monte Carlo Anomaly Diagnosis

Generated at: 2026-06-11T16:53:28.804607+00:00

## 1. Model Path
- scripts/simulate_wc2026_monte_carlo.py imports calculate_match_result_prob, build_team_data, get_h2h, get_schedule_data.
- calculate_match_result_prob includes qualification_form_delta, recent_friendlies_delta, h2h_adjustment, venue_context_adjustment, optional advanced adjustment, score_model_blend, and market_odds_agent.
- match_probs() caches each team-pair probability in prob_cache, so expensive model features are computed once per unique pair.
- Each Monte Carlo run then samples outcomes and updates standings/bracket; it does not call The Odds API or an LLM.
- 100000 runs can finish quickly because probabilities are cached, no external API is called per run, no LLM is called, and each run only samples 104 scheduled matches plus standings/bracket logic. This is normal for this implementation.

## 2. Market Odds Coverage
- events_returned: 72
- matched_matches: 72
- total_cache_matches: 72
- is_72_group_stage_matches: True
- group_stage_matches: 72
- knockout_matches: 32
- knockout_odds_present: False
- market_keys_present: {'1x2': 72, 'asian_handicap': 72, 'over_under': 72}
- bookmaker_count_min: 27
- bookmaker_count_max: 41
- outright_or_champion_market_present: False
- warning: None
- Interpretation: 72 matched odds entries means the cache covers group-stage match 1X2 markets, not an outright/champion market. Do not interpret group-stage 1X2 odds as champion probability.

## 3. Market Direction Samples
- Mexico vs South Africa: local Mexico vs South Africa; API Mexico vs South Africa; swapped=False; alias=False; odds={'home': 1.411, 'draw': 4.52, 'away': 8.579}; implied={'home': 0.6772, 'draw': 0.2114, 'away': 0.1114}; weight=0.3; warning=None
- Japan vs Netherlands: local Netherlands vs Japan; API Netherlands vs Japan; swapped=False; alias=False; odds={'home': 2.034, 'draw': 3.498, 'away': 3.676}; implied={'home': 0.4684, 'draw': 0.2724, 'away': 0.2592}; weight=0.3; warning=None
- Japan vs Sweden: local Japan vs Sweden; API Japan vs Sweden; swapped=False; alias=False; odds={'home': 2.057, 'draw': 3.36, 'away': 3.518}; implied={'home': 0.4552, 'draw': 0.2787, 'away': 0.2661}; weight=0.3; warning=None
- Japan vs Tunisia: local Tunisia vs Japan; API Tunisia vs Japan; swapped=False; alias=False; odds={'home': 5.229, 'draw': 3.538, 'away': 1.71}; implied={'home': 0.1806, 'draw': 0.267, 'away': 0.5524}; weight=0.3; warning=None
- Ivory Coast vs Germany: local Germany vs Ivory Coast; API Germany vs Ivory Coast; swapped=False; alias=False; odds={'home': 1.536, 'draw': 4.25, 'away': 5.724}; implied={'home': 0.6136, 'draw': 0.2218, 'away': 0.1647}; weight=0.3; warning=None
- Ivory Coast vs Ecuador: local Ivory Coast vs Ecuador; API Ivory Coast vs Ecuador; swapped=False; alias=False; odds={'home': 3.565, 'draw': 2.816, 'away': 2.411}; implied={'home': 0.267, 'draw': 0.3381, 'away': 0.3949}; weight=0.3; warning=None
- Ivory Coast vs Curaçao: local Curaçao vs Ivory Coast; API Curaçao vs Ivory Coast; swapped=False; alias=False; odds={'home': 12.934, 'draw': 6.026, 'away': 1.215}; implied={'home': 0.0725, 'draw': 0.1556, 'away': 0.7719}; weight=0.3; warning=None
- Argentina vs Algeria: local Argentina vs Algeria; API Argentina vs Algeria; swapped=False; alias=False; odds={'home': 1.382, 'draw': 4.634, 'away': 9.002}; implied={'home': 0.6888, 'draw': 0.2054, 'away': 0.1057}; weight=0.3; warning=None
- Argentina vs Austria: local Argentina vs Austria; API Argentina vs Austria; swapped=False; alias=False; odds={'home': 1.644, 'draw': 3.798, 'away': 5.364}; implied={'home': 0.5749, 'draw': 0.2489, 'away': 0.1762}; weight=0.3; warning=None
- Jordan vs Argentina: local Jordan vs Argentina; API Jordan vs Argentina; swapped=False; alias=False; odds={'home': 13.95, 'draw': 6.638, 'away': 1.186}; implied={'home': 0.0673, 'draw': 0.1414, 'away': 0.7913}; weight=0.3; warning=None
- France vs Senegal: local France vs Senegal; API France vs Senegal; swapped=False; alias=False; odds={'home': 1.459, 'draw': 4.399, 'away': 7.277}; implied={'home': 0.6527, 'draw': 0.2165, 'away': 0.1309}; weight=0.3; warning=None
- France vs Iraq: local France vs Iraq; API France vs Iraq; swapped=False; alias=False; odds={'home': 1.115, 'draw': 8.706, 'away': 23.108}; implied={'home': 0.8501, 'draw': 0.1089, 'away': 0.041}; weight=0.3; warning=None
- Norway vs France: local Norway vs France; API Norway vs France; swapped=False; alias=False; odds={'home': 4.228, 'draw': 3.552, 'away': 1.808}; implied={'home': 0.2208, 'draw': 0.2628, 'away': 0.5164}; weight=0.3; warning=None
- Spain vs Cabo Verde: local Spain vs Cabo Verde; API Spain vs Cape Verde; swapped=False; alias=True; odds={'home': 1.089, 'draw': 11.288, 'away': 25.904}; implied={'home': 0.8783, 'draw': 0.0847, 'away': 0.0369}; weight=0.3; warning=None
- Spain vs Saudi Arabia: local Spain vs Saudi Arabia; API Spain vs Saudi Arabia; swapped=False; alias=False; odds={'home': 1.105, 'draw': 9.555, 'away': 23.624}; implied={'home': 0.8603, 'draw': 0.0995, 'away': 0.0402}; weight=0.3; warning=None
- Uruguay vs Spain: local Uruguay vs Spain; API Uruguay vs Spain; swapped=False; alias=False; odds={'home': 5.242, 'draw': 3.818, 'away': 1.62}; implied={'home': 0.1783, 'draw': 0.2448, 'away': 0.5769}; weight=0.3; warning=None
- Brazil vs Morocco: local Brazil vs Morocco; API Brazil vs Morocco; swapped=False; alias=False; odds={'home': 1.653, 'draw': 3.772, 'away': 5.47}; implied={'home': 0.5746, 'draw': 0.2518, 'away': 0.1736}; weight=0.3; warning=None
- Brazil vs Haiti: local Brazil vs Haiti; API Brazil vs Haiti; swapped=False; alias=False; odds={'home': 1.074, 'draw': 11.901, 'away': 28.625}; implied={'home': 0.8867, 'draw': 0.08, 'away': 0.0333}; weight=0.3; warning=None
- Scotland vs Brazil: local Scotland vs Brazil; API Scotland vs Brazil; swapped=False; alias=False; odds={'home': 6.733, 'draw': 4.412, 'away': 1.445}; implied={'home': 0.1392, 'draw': 0.2124, 'away': 0.6485}; weight=0.3; warning=None

## 4. Home Advantage
- Current calibration fixed home_advantage: 60.
- Diagnosis: applying this to every listed home team in a neutral World Cup bracket is a model bug. Neutral listed-home advantage should be 0; host-country venue effects should remain in venue_context_adjustment.
- Mexico vs South Africa: original=60, neutral_fixed=0, context={'home_elo_delta': 32.0, 'away_elo_delta': -6.0, 'confidence': 0.65}, venue=Mexico City Stadium (Estadio Azteca)
- Germany vs Curaçao: original=60, neutral_fixed=0, context={'home_elo_delta': 0.0, 'away_elo_delta': 0.0, 'confidence': 0.65}, venue=Houston Stadium (NRG)
- Netherlands vs Japan: original=60, neutral_fixed=0, context={'home_elo_delta': 0.0, 'away_elo_delta': 0.0, 'confidence': 0.65}, venue=Dallas Stadium (AT&T)
- France vs Senegal: original=60, neutral_fixed=0, context={'home_elo_delta': 0.0, 'away_elo_delta': 0.0, 'confidence': 0.65}, venue=New York New Jersey Stadium (MetLife)

## 5. Team Profiles
- data/teams.json profiles: 50
- schedule teams: 48
- missing_team_profiles: []
- Japan: fifa_rank=15, attack=84, defense=82, midfield=79, estimated_elo=1644.3, recent_form=['W', 'D', 'L', 'W', 'W', 'W'], market_value=3.5, data_source=本地静态球队画像(data/teams.json) + CSV近期状态30%融合, elo_source=historical_static_anchor_blend, warning=
- Ivory Coast: fifa_rank=34, attack=87, defense=84, midfield=80, estimated_elo=1594.6, recent_form=['W', 'L', 'W', 'W', 'W', 'W'], market_value=5.22, data_source=本地静态球队画像(data/teams.json) + CSV近期状态30%融合, elo_source=historical_static_anchor_blend, warning=
- Morocco: fifa_rank=16, attack=82, defense=85, midfield=78, estimated_elo=1632.5, recent_form=['W', 'D', 'W', 'W', 'W', 'D'], market_value=3.6, data_source=本地静态球队画像(data/teams.json) + CSV近期状态30%融合, elo_source=historical_static_anchor_blend, warning=
- South Korea: fifa_rank=22, attack=83, defense=77, midfield=74, estimated_elo=1615.6, recent_form=['W', 'W', 'L', 'L', 'W', 'W'], market_value=2.8, data_source=本地静态球队画像(data/teams.json) + CSV近期状态30%融合, elo_source=historical_static_anchor_blend, warning=
- Germany: fifa_rank=7, attack=88, defense=83, midfield=84, estimated_elo=1647.7, recent_form=['W', 'W', 'W', 'W', 'W', 'W'], market_value=9.2, data_source=本地静态球队画像(data/teams.json) + CSV近期状态30%融合, elo_source=historical_static_anchor_blend, warning=
- Argentina: fifa_rank=1, attack=93, defense=85, midfield=84, estimated_elo=1688.7, recent_form=['W', 'W', 'W', 'W', 'W', 'W'], market_value=9.8, data_source=本地静态球队画像(data/teams.json) + CSV近期状态30%融合, elo_source=historical_static_anchor_blend, warning=
- France: fifa_rank=2, attack=92, defense=86, midfield=82, estimated_elo=1671.3, recent_form=['W', 'W', 'W', 'W', 'L', 'W'], market_value=14.8, data_source=本地静态球队画像(data/teams.json) + CSV近期状态30%融合, elo_source=historical_static_anchor_blend, warning=
- Spain: fifa_rank=5, attack=89, defense=85, midfield=85, estimated_elo=1655.7, recent_form=['W', 'D', 'W', 'D', 'D', 'W'], market_value=10.5, data_source=本地静态球队画像(data/teams.json) + CSV近期状态30%融合, elo_source=historical_static_anchor_blend, warning=
- Brazil: fifa_rank=3, attack=91, defense=81, midfield=79, estimated_elo=1658.1, recent_form=['W', 'D', 'L', 'W', 'W', 'W'], market_value=13.5, data_source=本地静态球队画像(data/teams.json) + CSV近期状态30%融合, elo_source=historical_static_anchor_blend, warning=
- England: fifa_rank=4, attack=90, defense=86, midfield=85, estimated_elo=1664.1, recent_form=['W', 'W', 'D', 'L', 'W', 'W'], market_value=15.2, data_source=本地静态球队画像(data/teams.json) + CSV近期状态30%融合, elo_source=historical_static_anchor_blend, warning=

## 6. Score And Knockout Logic
- Formal Monte Carlo now uses xG-based Poisson score sampling constrained to the sampled W/D/L outcome, replacing fixed 2-1/1-1 score templates.
- Formal knockout simulation now samples 90-minute W/D/L first; draws are resolved by an extra-time/penalty proxy with a small strength tilt.
- Formal best-third resolve_slot now uses deterministic candidate order instead of greedy strongest group. It is still an approximate mapping until an official complete third-place table is encoded.

## 7. Ablation Experiments
- A_original_home_advantage_60_market_on: Top10 阿根廷 10.4%, 法国 8.6%, 德国 8.4%, 西班牙 5.8%, 英格兰 5.8%, 巴西 5.4%, 日本 5.2%, 荷兰 4.5%, 比利时 4.2%, 摩洛哥 3.9%
  Focus: {'日本': 5.2, '科特迪瓦': 2.8, '摩洛哥': 3.9, '韩国': 3.2, '阿根廷': 10.4, '法国': 8.6, '西班牙': 5.8, '巴西': 5.4, '英格兰': 5.8, '德国': 8.4}
- B_market_weight_0: Top10 阿根廷 10.1%, 法国 8.1%, 德国 7.9%, 英格兰 5.8%, 西班牙 5.8%, 日本 5.6%, 巴西 5.0%, 荷兰 4.5%, 摩洛哥 4.1%, 比利时 3.9%
  Focus: {'日本': 5.6, '科特迪瓦': 3.3, '摩洛哥': 4.1, '韩国': 3.5, '阿根廷': 10.1, '法国': 8.1, '西班牙': 5.8, '巴西': 5.0, '英格兰': 5.8, '德国': 7.9}
- C_neutral_home_advantage_0: Top10 阿根廷 10.9%, 法国 7.4%, 英格兰 6.9%, 西班牙 6.0%, 比利时 5.7%, 德国 5.7%, 日本 4.9%, 巴西 4.5%, 荷兰 4.2%, 葡萄牙 4.1%
  Focus: {'日本': 4.9, '科特迪瓦': 2.7, '摩洛哥': 3.8, '韩国': 2.7, '阿根廷': 10.9, '法国': 7.4, '西班牙': 6.0, '巴西': 4.5, '英格兰': 6.9, '德国': 5.7}
- D_market0_neutral0: Top10 阿根廷 10.7%, 法国 7.1%, 英格兰 6.9%, 西班牙 5.9%, 比利时 5.3%, 日本 5.3%, 德国 5.3%, 巴西 4.4%, 荷兰 4.2%, 葡萄牙 4.0%
  Focus: {'日本': 5.3, '科特迪瓦': 2.6, '摩洛哥': 3.9, '韩国': 2.9, '阿根廷': 10.7, '法国': 7.1, '西班牙': 5.9, '巴西': 4.4, '英格兰': 6.9, '德国': 5.3}
- E_poisson_scores: Top10 阿根廷 9.8%, 法国 8.2%, 德国 7.8%, 西班牙 6.1%, 英格兰 5.9%, 日本 5.2%, 巴西 5.2%, 荷兰 4.5%, 比利时 4.3%, 摩洛哥 3.9%
  Focus: {'日本': 5.2, '科特迪瓦': 3.1, '摩洛哥': 3.9, '韩国': 3.3, '阿根廷': 9.8, '法国': 8.2, '西班牙': 6.1, '巴西': 5.2, '英格兰': 5.9, '德国': 7.8}
- F_knockout_draw_handling: Top10 阿根廷 9.3%, 法国 7.3%, 德国 6.9%, 巴西 5.4%, 英格兰 5.3%, 西班牙 5.2%, 日本 4.9%, 比利时 4.4%, 荷兰 4.2%, 摩洛哥 3.9%
  Focus: {'日本': 4.9, '科特迪瓦': 2.9, '摩洛哥': 3.9, '韩国': 3.3, '阿根廷': 9.3, '法国': 7.3, '西班牙': 5.2, '巴西': 5.4, '英格兰': 5.3, '德国': 6.9}
- G_candidate_order_third_place_approx: Top10 阿根廷 10.3%, 德国 8.7%, 法国 8.7%, 西班牙 5.8%, 英格兰 5.8%, 巴西 5.6%, 日本 5.1%, 荷兰 4.4%, 摩洛哥 4.1%, 比利时 4.0%
  Focus: {'日本': 5.1, '科特迪瓦': 3.0, '摩洛哥': 4.1, '韩国': 3.6, '阿根廷': 10.3, '法国': 8.7, '西班牙': 5.8, '巴西': 5.6, '英格兰': 5.8, '德国': 8.7}

## 8. Third-Place Slot Statistics
- M74: {'F': 26.2, 'C': 22.7, 'D': 18.1, 'A': 17.9, 'B': 15.1}
- M77: {'G': 38.6, 'H': 21.2, 'D': 15.4, 'F': 13.0, 'C': 11.9}
- M79: {'E': 41.3, 'I': 36.6, 'H': 7.9, 'C': 7.3, 'F': 6.9}
- M80: {'J': 39.6, 'K': 34.2, 'I': 11.3, 'E': 9.6, 'H': 5.2}
- M81: {'B': 37.9, 'J': 19.1, 'F': 15.4, 'I': 14.4, 'E': 13.2}
- M82: {'A': 53.5, 'H': 17.3, 'J': 10.4, 'I': 9.1, 'E': 9.1, 'L': 0.2, 'G': 0.1, 'K': 0.1, 'D': 0.1, 'F': 0.1, 'B': 0.0, 'C': 0.0}
- M85: {'G': 45.9, 'F': 18.6, 'J': 11.3, 'I': 10.1, 'E': 9.7, 'L': 1.9, 'K': 0.8, 'D': 0.8, 'C': 0.5, 'B': 0.3, 'H': 0.1, 'A': 0.0}
- M87: {'L': 68.4, 'D': 25.8, 'J': 1.9, 'E': 1.9, 'I': 1.9, 'C': 0.0, 'K': 0.0, 'B': 0.0, 'H': 0.0}

## 9. Diagnosis
1. Static anchoring now pulls Argentina, France, Spain, England, Brazil, Germany, and Portugal back toward the top band while preserving CSV recent-form information as a partial adjustment.
2. Japan, South Korea, Morocco, Iran and similar teams remain competitive, but their generated qualification/friendly profile no longer fully overrides static rank/value anchors when those anchors exist.
3. Ivory Coast and Algeria remain higher-risk estimates because they still lack static profiles and are marked generated_csv_profile_only; profile completion remains the most important residual risk.
4. Market odds cover 72 group-stage 1X2 matches only, not knockout or outright champion markets; they are used as match-level calibration and should not be interpreted as champion odds.
5. Formal score and knockout mechanics have been updated, but best-third mapping remains approximate deterministic candidate order until an official complete mapping table is added.

## 10. Recommended Fix Order
1. Complete and audit team profile sources for all 48 teams, especially generated_csv_profile_only teams such as Ivory Coast, Algeria, Norway, Austria, Ecuador, Switzerland, and Turkey.
2. Add or verify official best-third mapping for the 48-team bracket.
3. Keep treating market odds as match-level calibration only; do not infer champion probabilities without an explicit outright market.
4. Re-run backtests before claiming predictive lift from these structural fixes.

No model improvement is claimed here; the evidence is structural diagnosis plus ablation output, not a backtest proving predictive lift.
