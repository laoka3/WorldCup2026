# Static Profile Sources

Generated: 2026-06-11T18:52:25

## Sources

- FIFA ranking / points / total market values: https://www.transfermarkt.com/wettbewerbe/fifa
- World Cup 2026 participant squad market values: https://www.transfermarkt.com/weltmeisterschaft/teilnehmer/pokalwettbewerb/FIWC/saison_id/2025

## Method

- `fifa_rank`, `confederation`, `market_value`, and `fifa_points` are parsed from Transfermarkt pages.
- `attack_rating`, `defense_rating`, `midfield_rating`, possession, xG and xGA are conservative model seed fields derived from rank/value plus local CSV goal rates where available.
- `coach` and `key_player` are intentionally left null unless separately verified.

## Added Profiles

- 南非 (South Africa): rank 60, points 1430.0, confederation CAF, market €0.0493bn
- 捷克 (Czechia): rank 41, points 1501.0, confederation UEFA, market €0.1882bn
- 波黑 (Bosnia-Herzegovina): rank 65, points 1386.0, confederation UEFA, market €0.1516bn
- 卡塔尔 (Qatar): rank 55, points 1455.0, confederation AFC, market €0.0199bn
- 瑞士 (Switzerland): rank 19, points 1649.0, confederation UEFA, market €0.3325bn
- 海地 (Haiti): rank 83, points 1292.0, confederation CONCACAF, market €0.0559bn
- 苏格兰 (Scotland): rank 43, points 1498.0, confederation UEFA, market €0.1703bn
- 巴拉圭 (Paraguay): rank 40, points 1504.0, confederation CONMEBOL, market €0.1537bn
- 土耳其 (Turkiye): rank 22, points 1599.0, confederation UEFA, market €0.4737bn
- 库拉索 (Curaçao): rank 82, points 1295.0, confederation CONCACAF, market €0.0258bn
- 科特迪瓦 (Ivory Coast): rank 34, points 1533.0, confederation CAF, market €0.5221bn
- 厄瓜多尔 (Ecuador): rank 23, points 1595.0, confederation CONMEBOL, market €0.3687bn
- 瑞典 (Sweden): rank 38, points 1515.0, confederation UEFA, market €0.4061bn
- 突尼斯 (Tunisia): rank 44, points 1483.0, confederation CAF, market €0.0699bn
- 新西兰 (New Zealand): rank 85, points 1282.0, confederation OFC, market €0.0343bn
- 佛得角 (Cape Verde): rank 69, points 1366.0, confederation CAF, market €0.0545bn
- 沙特阿拉伯 (Saudi Arabia): rank 61, points 1421.0, confederation AFC, market €0.0407bn
- 伊拉克 (Iraq): rank 57, points 1447.0, confederation AFC, market €0.0212bn
- 挪威 (Norway): rank 31, points 1551.0, confederation UEFA, market €0.5899bn
- 阿尔及利亚 (Algeria): rank 28, points 1564.0, confederation CAF, market €0.2569bn
- 奥地利 (Austria): rank 24, points 1593.0, confederation UEFA, market €0.2452bn
- 约旦 (Jordan): rank 63, points 1391.0, confederation AFC, market €0.0203bn
- 刚果民主共和国 (Democratic Republic of the Congo): rank 46, points 1478.0, confederation CAF, market €0.1439bn
- 乌兹别克斯坦 (Uzbekistan): rank 50, points 1465.0, confederation AFC, market €0.0853bn
- 加纳 (Ghana): rank 74, points 1346.0, confederation CAF, market €0.2346bn
- 巴拿马 (Panama): rank 33, points 1541.0, confederation CONCACAF, market €0.0345bn
