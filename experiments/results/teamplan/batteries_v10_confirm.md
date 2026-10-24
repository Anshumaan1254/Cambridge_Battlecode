# Confirmation battery of the two leads (SIMULATED (v10); tools/teamplan/batteries.py --confirm)

Maps `maps/official/*.map26a`, both sides, release mode. Opponents: GOD v10 (head-to-head) and v10 forced to roster slot k of `tools/mapintel/data/battery_rosters.json` (`_tp_v10F` for slot 0, `_tp_v10F<k>` otherwise; slots 0-3 are real strong-team rosters on all 40 maps, slots 4-7 COMPUTED, balanced over kit classes). Paired = against v10's own games with the same opponent, map and side: the gem margin difference averaged per map [bootstrap 95%], and the games turned into wins / losses (sign test).

| Variant | Opponent | Wins (v10's) | Paired margin [95%] | Games turned: wins / losses |
|---|---|---|---|---|
| `_tp_bag` (fight bar rises with the bag) | GOD v10, head-to-head | 44/80 (40) | +37.5 [-43.2, +114.1] | maps 6 won twice / 2 lost twice, p 0.289 |
| | slot 0 (LEARNED) | 43 (37) | +85.4 [-4.8, +182.2] | 9 / 3, p 0.146 |
| | slot 1 (LEARNED) | 44 (43) | -0.0 [-111.1, +110.8] | 7 / 6, p 1.000 |
| | slot 2 (LEARNED) | 45 (47) | -59.9 [-207.6, +77.4] | 7 / 9, p 0.804 |
| | **pooled, slots 0,1,2** | | +8.5 [-60.5, +77.8] over 120 | **23 / 18, p 0.533** |
| `_tp_own` (soft group ownership) | GOD v10, head-to-head | 44/80 (40) | +19.0 [-122.3, +158.6] | maps 13 won twice / 9 lost twice, p 0.523 |
| | slot 0 (LEARNED) | 43 (37) | +120.8 [-53.4, +327.3] | 18 / 12, p 0.362 |
| | slot 1 (LEARNED) | 47 (43) | +16.4 [-196.3, +225.8] | 18 / 14, p 0.597 |
| | slot 2 (LEARNED) | 51 (47) | +67.2 [-113.9, +255.2] | 16 / 12, p 0.572 |
| | **pooled, slots 0,1,2** | | +68.1 [-41.5, +180.6] over 120 | **52 / 38, p 0.170** |
| `_tp_bo` (both) | GOD v10, head-to-head | 39/80 (40) | +29.1 [-111.5, +162.3] | maps 9 won twice / 10 lost twice, p 1.000 |
| | slot 0 (LEARNED) | 45 (37) | +168.7 [+9.8, +356.3] | 20 / 12, p 0.215 |
| | slot 1 (LEARNED) | 43 (43) | -79.0 [-275.1, +138.4] | 16 / 16, p 1.000 |
| | slot 2 (LEARNED) | 51 (47) | +98.2 [-114.3, +306.2] | 18 / 14, p 0.597 |
| | **pooled, slots 0,1,2** | | +62.6 [-50.1, +178.8] over 120 | **54 / 42, p 0.261** |
