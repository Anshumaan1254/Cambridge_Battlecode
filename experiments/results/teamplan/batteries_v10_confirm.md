# Confirmation battery of the two leads (SIMULATED (v10); tools/teamplan/batteries.py --confirm)

Maps `maps/official/*.map26a`, both sides, release mode. Opponents: GOD v10 (head-to-head) and v10 forced to roster slot k of `tools/mapintel/data/battery_rosters.json` (`_tp_v10F` for slot 0, `_tp_v10F<k>` otherwise; slots 0-3 are real strong-team rosters on all 40 maps, slots 4-7 COMPUTED, balanced over kit classes). Paired = against v10's own games with the same opponent, map and side: the gem margin difference averaged per map [bootstrap 95%], and the games turned into wins / losses (sign test).

| Variant | Opponent | Wins (v10's) | Paired margin [95%] | Games turned: wins / losses |
|---|---|---|---|---|
| `_tp_bag` (fight bar rises with the bag) | GOD v10, head-to-head | 44/80 (40) | +37.5 [-43.2, +114.1] | maps 6 won twice / 2 lost twice, p 0.289 |
| | slot 0 (LEARNED) | 43 (37) | +85.4 [-4.8, +182.2] | 9 / 3, p 0.146 |
| | slot 1 (LEARNED) | 44 (43) | -0.0 [-111.1, +110.8] | 7 / 6, p 1.000 |
| | slot 2 (LEARNED) | 45 (47) | -59.9 [-207.6, +77.4] | 7 / 9, p 0.804 |
| | slot 3 (LEARNED) | 50 (45) | +16.9 [-70.7, +102.7] | 8 / 3, p 0.227 |
| | slot 4 (COMPUTED) | 50 (51) | -65.9 [-140.7, +5.7] | 2 / 3, p 1.000 |
| | slot 5 (COMPUTED) | 68 (70) | -85.5 [-196.3, +4.2] | 5 / 7, p 0.774 |
| | slot 6 (COMPUTED) | 52 (56) | -94.7 [-218.9, -0.4] | 4 / 8, p 0.388 |
| | slot 7 (COMPUTED) | 62 (65) | -72.9 [-171.6, +21.1] | 3 / 6, p 0.508 |
| | **pooled, slots 0,1,2,3** | | +10.6 [-46.3, +66.3] over 160 | **31 / 21, p 0.212** |
| | **pooled, slots 4,5,6,7** | | -79.7 [-131.8, -35.4] over 160 | **14 / 24, p 0.143** |
| | **pooled, slots 0,1,2,3,4,5,6,7** | | -34.6 [-72.9, +2.4] over 320 | **45 / 45, p 1.000** |
