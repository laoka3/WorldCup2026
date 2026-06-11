# Monte Carlo Anomaly Diagnosis

Generated at: 2026-06-11T15:54:37.909595+00:00

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
- Mexico vs South Africa: local Mexico vs South Africa; API Mexico vs South Africa; swapped=False; alias=False; odds={'home': 1.411, 'draw': 4.52, 'away': 8.579}; implied={'home': 0.6772, 'draw': 0.2114, 'away': 0.1114}; weight=0.2; warning=None
- Japan vs Netherlands: local Netherlands vs Japan; API Netherlands vs Japan; swapped=False; alias=False; odds={'home': 2.034, 'draw': 3.498, 'away': 3.676}; implied={'home': 0.4684, 'draw': 0.2724, 'away': 0.2592}; weight=0.2; warning=None
- Japan vs Sweden: local Japan vs Sweden; API Japan vs Sweden; swapped=False; alias=False; odds={'home': 2.057, 'draw': 3.36, 'away': 3.518}; implied={'home': 0.4552, 'draw': 0.2787, 'away': 0.2661}; weight=0.1; warning=None
- Japan vs Tunisia: local Tunisia vs Japan; API Tunisia vs Japan; swapped=False; alias=False; odds={'home': 5.229, 'draw': 3.538, 'away': 1.71}; implied={'home': 0.1806, 'draw': 0.267, 'away': 0.5524}; weight=0.1; warning=None
- Ivory Coast vs Germany: local Germany vs Ivory Coast; API Germany vs Ivory Coast; swapped=False; alias=False; odds={'home': 1.536, 'draw': 4.25, 'away': 5.724}; implied={'home': 0.6136, 'draw': 0.2218, 'away': 0.1647}; weight=0.1; warning=None
- Ivory Coast vs Ecuador: local Ivory Coast vs Ecuador; API Ivory Coast vs Ecuador; swapped=False; alias=False; odds={'home': 3.565, 'draw': 2.816, 'away': 2.411}; implied={'home': 0.267, 'draw': 0.3381, 'away': 0.3949}; weight=0.2; warning=None
- Ivory Coast vs Curaçao: local Curaçao vs Ivory Coast; API Curaçao vs Ivory Coast; swapped=False; alias=False; odds={'home': 12.934, 'draw': 6.026, 'away': 1.215}; implied={'home': 0.0725, 'draw': 0.1556, 'away': 0.7719}; weight=0.1; warning=None
- Argentina vs Algeria: local Argentina vs Algeria; API Argentina vs Algeria; swapped=False; alias=False; odds={'home': 1.382, 'draw': 4.634, 'away': 9.002}; implied={'home': 0.6888, 'draw': 0.2054, 'away': 0.1057}; weight=0.2; warning=None
- Argentina vs Austria: local Argentina vs Austria; API Argentina vs Austria; swapped=False; alias=False; odds={'home': 1.644, 'draw': 3.798, 'away': 5.364}; implied={'home': 0.5749, 'draw': 0.2489, 'away': 0.1762}; weight=0.1; warning=None
- Jordan vs Argentina: local Jordan vs Argentina; API Jordan vs Argentina; swapped=False; alias=False; odds={'home': 13.95, 'draw': 6.638, 'away': 1.186}; implied={'home': 0.0673, 'draw': 0.1414, 'away': 0.7913}; weight=0.1; warning=None
- France vs Senegal: local France vs Senegal; API France vs Senegal; swapped=False; alias=False; odds={'home': 1.459, 'draw': 4.399, 'away': 7.277}; implied={'home': 0.6527, 'draw': 0.2165, 'away': 0.1309}; weight=0.2; warning=None
- France vs Iraq: local France vs Iraq; API France vs Iraq; swapped=False; alias=False; odds={'home': 1.115, 'draw': 8.706, 'away': 23.108}; implied={'home': 0.8501, 'draw': 0.1089, 'away': 0.041}; weight=0.1; warning=None
- Norway vs France: local Norway vs France; API Norway vs France; swapped=False; alias=False; odds={'home': 4.228, 'draw': 3.552, 'away': 1.808}; implied={'home': 0.2208, 'draw': 0.2628, 'away': 0.5164}; weight=0.1; warning=None
- Spain vs Cabo Verde: local Spain vs Cabo Verde; API Spain vs Cape Verde; swapped=False; alias=True; odds={'home': 1.089, 'draw': 11.288, 'away': 25.904}; implied={'home': 0.8783, 'draw': 0.0847, 'away': 0.0369}; weight=0.2; warning=None
- Spain vs Saudi Arabia: local Spain vs Saudi Arabia; API Spain vs Saudi Arabia; swapped=False; alias=False; odds={'home': 1.105, 'draw': 9.555, 'away': 23.624}; implied={'home': 0.8603, 'draw': 0.0995, 'away': 0.0402}; weight=0.1; warning=None
- Uruguay vs Spain: local Uruguay vs Spain; API Uruguay vs Spain; swapped=False; alias=False; odds={'home': 5.242, 'draw': 3.818, 'away': 1.62}; implied={'home': 0.1783, 'draw': 0.2448, 'away': 0.5769}; weight=0.1; warning=None
- Brazil vs Morocco: local Brazil vs Morocco; API Brazil vs Morocco; swapped=False; alias=False; odds={'home': 1.653, 'draw': 3.772, 'away': 5.47}; implied={'home': 0.5746, 'draw': 0.2518, 'away': 0.1736}; weight=0.2; warning=None
- Brazil vs Haiti: local Brazil vs Haiti; API Brazil vs Haiti; swapped=False; alias=False; odds={'home': 1.074, 'draw': 11.901, 'away': 28.625}; implied={'home': 0.8867, 'draw': 0.08, 'away': 0.0333}; weight=0.1; warning=None
- Scotland vs Brazil: local Scotland vs Brazil; API Scotland vs Brazil; swapped=False; alias=False; odds={'home': 6.733, 'draw': 4.412, 'away': 1.445}; implied={'home': 0.1392, 'draw': 0.2124, 'away': 0.6485}; weight=0.1; warning=None

## 4. Home Advantage
- Current calibration fixed home_advantage: 60.
- Diagnosis: applying this to every listed home team in a neutral World Cup bracket is a model bug. Neutral listed-home advantage should be 0; host-country venue effects should remain in venue_context_adjustment.
- Mexico vs South Africa: original=60, neutral_fixed=0, context={'home_elo_delta': 32.0, 'away_elo_delta': -6.0, 'confidence': 0.65}, venue=Mexico City Stadium (Estadio Azteca)
- Germany vs Curaçao: original=60, neutral_fixed=0, context={'home_elo_delta': 0.0, 'away_elo_delta': 0.0, 'confidence': 0.65}, venue=Houston Stadium (NRG)
- Netherlands vs Japan: original=60, neutral_fixed=0, context={'home_elo_delta': 0.0, 'away_elo_delta': 0.0, 'confidence': 0.65}, venue=Dallas Stadium (AT&T)
- France vs Senegal: original=60, neutral_fixed=0, context={'home_elo_delta': 0.0, 'away_elo_delta': 0.0, 'confidence': 0.65}, venue=New York New Jersey Stadium (MetLife)

## 5. Team Profiles
- data/teams.json profiles: 24
- schedule teams: 48
- missing_team_profiles: ['南非', '捷克', '波黑', '卡塔尔', '瑞士', '海地', '苏格兰', '巴拉圭', '土耳其', '库拉索', '科特迪瓦', '厄瓜多尔', '瑞典', '突尼斯', '新西兰', '佛得角', '沙特阿拉伯', '伊拉克', '挪威', '阿尔及利亚', '奥地利', '约旦', '刚果民主共和国', '乌兹别克斯坦', '加纳', '巴拿马']
- Japan: fifa_rank=None, attack=95, defense=88, midfield=72, estimated_elo=1668.5, recent_form=['W', 'D', 'L', 'W', 'W', 'W'], market_value=None, data_source=2022-2024 20场比赛, elo_source=historical_cache, warning=
- Ivory Coast: fifa_rank=None, attack=95, defense=89, midfield=74, estimated_elo=1640.1, recent_form=['W', 'L', 'W', 'W', 'W', 'W'], market_value=None, data_source=2022-2024 15场比赛, elo_source=historical_cache, warning=
- Morocco: fifa_rank=None, attack=95, defense=88, midfield=77, estimated_elo=1650.9, recent_form=['W', 'D', 'W', 'W', 'W', 'D'], market_value=None, data_source=2022-2024 18场比赛, elo_source=historical_cache, warning=
- South Korea: fifa_rank=None, attack=94, defense=82, midfield=70, estimated_elo=1649.3, recent_form=['W', 'W', 'L', 'L', 'W', 'W'], market_value=None, data_source=2022-2024 26场比赛, elo_source=historical_cache, warning=
- Germany: fifa_rank=None, attack=95, defense=81, midfield=77, estimated_elo=1606.4, recent_form=['W', 'W', 'W', 'W', 'W', 'W'], market_value=None, data_source=2022-2024 10场比赛, elo_source=historical_cache, warning=
- Argentina: fifa_rank=None, attack=95, defense=86, midfield=73, estimated_elo=1632.3, recent_form=['W', 'W', 'W', 'W', 'W', 'W'], market_value=None, data_source=2022-2024 25场比赛, elo_source=historical_cache, warning=
- France: fifa_rank=None, attack=95, defense=80, midfield=74, estimated_elo=1592.7, recent_form=['W', 'W', 'W', 'W', 'L', 'W'], market_value=None, data_source=2022-2024 10场比赛, elo_source=historical_cache, warning=
- Spain: fifa_rank=None, attack=95, defense=86, midfield=71, estimated_elo=1591.4, recent_form=['W', 'D', 'W', 'D', 'D', 'W'], market_value=None, data_source=2022-2024 10场比赛, elo_source=historical_cache, warning=
- Brazil: fifa_rank=None, attack=85, defense=79, midfield=66, estimated_elo=1576.2, recent_form=['W', 'D', 'L', 'W', 'W', 'W'], market_value=None, data_source=2022-2024 25场比赛, elo_source=historical_cache, warning=
- England: fifa_rank=None, attack=95, defense=87, midfield=74, estimated_elo=1598.2, recent_form=['W', 'W', 'D', 'L', 'W', 'W'], market_value=None, data_source=2022-2024 14场比赛, elo_source=historical_cache, warning=

## 6. Score And Knockout Logic
- Group score_for_result is fixed: home win is 2-1 or 3-1, away win is 1-2 or 1-3, draw is always 1-1. This is not realistic and can distort goal difference, goals for, third-place ranking, and group ordering.
- Current knockout logic uses allow_draw=False, which drops draw probability and renormalizes home/away. Recommended: sample 90-minute W/D/L, then resolve draws by extra time/penalties with a small strength tilt.
- Current best-third resolve_slot uses greedy strongest eligible group within each slot, not an official third-place mapping table. This is a path approximation and can bias bracket paths.

## 7. Ablation Experiments
- A_original_home_advantage_60_market_on: Top10 日本 8.8%, 科特迪瓦 7.3%, 摩洛哥 6.8%, 韩国 6.7%, 德国 5.6%, 阿根廷 5.4%, 阿尔及利亚 4.4%, 伊朗 3.9%, 挪威 3.7%, 比利时 3.6%
  Focus: {'日本': 8.8, '科特迪瓦': 7.3, '摩洛哥': 6.8, '韩国': 6.7, '阿根廷': 5.4, '法国': 2.9, '西班牙': 3.3, '巴西': 1.2, '英格兰': 2.6, '德国': 5.6}
- B_market_weight_0: Top10 日本 9.2%, 科特迪瓦 7.5%, 摩洛哥 7.0%, 韩国 6.8%, 阿根廷 5.0%, 德国 4.9%, 阿尔及利亚 4.7%, 伊朗 4.0%, 挪威 3.5%, 比利时 3.4%
  Focus: {'日本': 9.2, '科特迪瓦': 7.5, '摩洛哥': 7.0, '韩国': 6.8, '阿根廷': 5.0, '法国': 2.6, '西班牙': 3.3, '巴西': 1.0, '英格兰': 2.4, '德国': 4.9}
- C_neutral_home_advantage_0: Top10 日本 8.4%, 摩洛哥 6.0%, 韩国 5.9%, 阿根廷 5.7%, 科特迪瓦 5.5%, 阿尔及利亚 5.4%, 伊朗 5.2%, 比利时 4.9%, 德国 3.9%, 奥地利 3.7%
  Focus: {'日本': 8.4, '科特迪瓦': 5.5, '摩洛哥': 6.0, '韩国': 5.9, '阿根廷': 5.7, '法国': 2.6, '西班牙': 3.3, '巴西': 1.0, '英格兰': 3.0, '德国': 3.9}
- D_market0_neutral0: Top10 日本 8.6%, 摩洛哥 6.1%, 韩国 5.8%, 阿尔及利亚 5.7%, 科特迪瓦 5.7%, 伊朗 5.3%, 阿根廷 5.3%, 比利时 4.7%, 奥地利 3.7%, 德国 3.6%
  Focus: {'日本': 8.6, '科特迪瓦': 5.7, '摩洛哥': 6.1, '韩国': 5.8, '阿根廷': 5.3, '法国': 2.2, '西班牙': 3.3, '巴西': 0.9, '英格兰': 2.9, '德国': 3.6}
- E_poisson_scores: Top10 日本 8.6%, 科特迪瓦 6.8%, 摩洛哥 6.5%, 韩国 6.5%, 德国 5.4%, 阿根廷 5.0%, 阿尔及利亚 4.7%, 比利时 4.0%, 挪威 3.7%, 伊朗 3.6%
  Focus: {'日本': 8.6, '科特迪瓦': 6.8, '摩洛哥': 6.5, '韩国': 6.5, '阿根廷': 5.0, '法国': 2.9, '西班牙': 3.3, '巴西': 1.2, '英格兰': 2.6, '德国': 5.4}
- F_knockout_draw_handling: Top10 日本 7.5%, 韩国 6.2%, 科特迪瓦 6.0%, 摩洛哥 5.8%, 阿根廷 4.9%, 阿尔及利亚 4.6%, 德国 4.6%, 伊朗 3.9%, 挪威 3.6%, 比利时 3.6%
  Focus: {'日本': 7.5, '科特迪瓦': 6.0, '摩洛哥': 5.8, '韩国': 6.2, '阿根廷': 4.9, '法国': 2.8, '西班牙': 3.2, '巴西': 1.6, '英格兰': 2.5, '德国': 4.6}
- G_candidate_order_third_place_approx: Top10 日本 8.7%, 科特迪瓦 7.8%, 韩国 7.2%, 摩洛哥 7.1%, 德国 5.9%, 阿根廷 5.3%, 阿尔及利亚 4.4%, 挪威 3.6%, 伊朗 3.6%, 西班牙 3.3%
  Focus: {'日本': 8.7, '科特迪瓦': 7.8, '摩洛哥': 7.1, '韩国': 7.2, '阿根廷': 5.3, '法国': 2.7, '西班牙': 3.3, '巴西': 1.3, '英格兰': 2.6, '德国': 5.9}

Post-fix 100000-run main simulation after neutral fixed home_advantage=0:
日本 8.8%, 韩国 5.9%, 摩洛哥 5.8%, 阿尔及利亚 5.6%, 阿根廷 5.5%, 伊朗 5.5%, 科特迪瓦 5.4%, 比利时 4.9%, 德国 3.8%, 奥地利 3.8%.

## 8. Third-Place Slot Statistics
- M74: {'C': 25.5, 'F': 21.9, 'A': 19.8, 'D': 17.9, 'B': 15.0}
- M77: {'G': 40.4, 'H': 20.2, 'C': 13.4, 'D': 13.1, 'F': 12.8}
- M79: {'E': 39.1, 'I': 37.7, 'H': 9.4, 'F': 7.2, 'C': 6.6}
- M80: {'J': 39.9, 'K': 35.9, 'I': 10.3, 'E': 8.4, 'H': 5.5}
- M81: {'B': 39.0, 'J': 17.3, 'E': 15.3, 'F': 15.2, 'I': 13.2}
- M82: {'A': 48.4, 'H': 18.9, 'J': 12.2, 'I': 10.1, 'E': 9.9, 'L': 0.2, 'K': 0.1, 'G': 0.1, 'D': 0.1, 'B': 0.0, 'C': 0.0, 'F': 0.0}
- M85: {'G': 40.8, 'F': 21.5, 'J': 12.2, 'E': 11.1, 'I': 10.3, 'L': 1.6, 'K': 0.9, 'D': 0.6, 'C': 0.6, 'B': 0.2, 'A': 0.1, 'H': 0.0}
- M87: {'L': 70.8, 'D': 24.6, 'I': 1.8, 'J': 1.6, 'E': 1.1, 'K': 0.0, 'C': 0.0, 'B': 0.0, 'A': 0.0, 'H': 0.0}

## 9. Diagnosis
1. For Japan, the strongest evidence points to data/profile strength plus path/knockout mechanics: Japan has one of the highest generated Elo/profile ratings, remains high when market_weight=0, and drops most in the knockout draw-handling ablation.
2. For Ivory Coast, the fixed +60 listed-home advantage and generated profile both matter: neutral home_advantage=0 reduces Ivory Coast materially, while market_weight=0 does not reduce it.
3. Market odds are not the main source of the anomaly in this run. They cover 72 group matches only, no knockout/outright champion market, and the market_weight=0 ablation keeps Japan/Ivory/Morocco/Korea broadly high.
4. Team profile coverage is incomplete. data/teams.json has 24 static profiles for 48 scheduled teams; missing teams rely on generated qualification/friendly profiles or defaults, which can over/under-rate teams unevenly.
5. Fixed group-score logic distorts GD/GF and best-third ranking; this directly affects a 48-team format with eight third-place qualifiers.
6. Knockout draw probability is discarded instead of being resolved through extra time/penalties; the ablation reduces Japan from the high band, so this is a likely model issue.
7. Best-third slot assignment is approximate greedy logic, not official mapping; path advantages should not be trusted until this is fixed.

## 10. Recommended Fix Order
1. Complete and audit team profile sources for all 48 teams, especially generated Elo/profile values for Japan, Ivory Coast, Morocco, South Korea, Brazil, France, Spain, and England.
2. Keep neutral fixed home_advantage at 0 and use venue_context_adjustment only for USA/Mexico/Canada true home venues.
3. Replace knockout allow_draw=False with 90-minute draw plus ET/penalty resolution.
4. Replace fixed group scores with conditional Poisson score sampling.
5. Add or verify official best-third mapping for the 48-team bracket.
6. Treat market odds as match-level calibration only; do not infer champion probabilities without an explicit outright market.

No model improvement is claimed here; the evidence is structural diagnosis plus ablation output, not a backtest proving predictive lift.
