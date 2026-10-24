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
| `_tp_own` (soft group ownership) | GOD v10, head-to-head | 44/80 (40) | +19.0 [-122.3, +158.6] | maps 13 won twice / 9 lost twice, p 0.523 |
| | slot 0 (LEARNED) | 43 (37) | +120.8 [-53.4, +327.3] | 18 / 12, p 0.362 |
| | slot 1 (LEARNED) | 47 (43) | +16.4 [-196.3, +225.8] | 18 / 14, p 0.597 |
| | slot 2 (LEARNED) | 51 (47) | +67.2 [-113.9, +255.2] | 16 / 12, p 0.572 |
| | slot 3 (LEARNED) | 43 (45) | -57.2 [-210.7, +103.7] | 14 / 16, p 0.856 |
| | slot 4 (COMPUTED) | 48 (51) | -94.5 [-241.0, +38.1] | 14 / 17, p 0.720 |
| | slot 5 (COMPUTED) | 60 (70) | -123.2 [-277.4, +20.5] | 5 / 15, p 0.041 |
| | slot 6 (COMPUTED) | 54 (56) | -52.1 [-204.3, +112.4] | 12 / 14, p 0.845 |
| | slot 7 (COMPUTED) | 64 (65) | -17.3 [-132.9, +94.2] | 9 / 10, p 1.000 |
| | **pooled, slots 0,1,2,3** | | +36.8 [-50.4, +131.9] over 160 | **66 / 54, p 0.315** |
| | **pooled, slots 4,5,6,7** | | -71.8 [-144.4, -2.8] over 160 | **40 / 56, p 0.125** |
| | **pooled, slots 0,1,2,3,4,5,6,7** | | -17.5 [-75.6, +40.2] over 320 | **106 / 110, p 0.838** |
| `_tp_bo` (both) | GOD v10, head-to-head | 39/80 (40) | +29.1 [-111.5, +162.3] | maps 9 won twice / 10 lost twice, p 1.000 |
| | slot 0 (LEARNED) | 45 (37) | +168.7 [+9.8, +356.3] | 20 / 12, p 0.215 |
| | slot 1 (LEARNED) | 43 (43) | -79.0 [-275.1, +138.4] | 16 / 16, p 1.000 |
| | slot 2 (LEARNED) | 51 (47) | +98.2 [-114.3, +306.2] | 18 / 14, p 0.597 |
| | slot 3 (LEARNED) | 47 (45) | +19.7 [-140.4, +178.9] | 14 / 12, p 0.845 |
| | slot 4 (COMPUTED) | 49 (51) | -42.0 [-188.0, +98.5] | 17 / 19, p 0.868 |
| | slot 5 (COMPUTED) | 62 (70) | -104.2 [-228.8, +19.8] | 5 / 13, p 0.096 |
| | slot 6 (COMPUTED) | 52 (56) | -96.2 [-248.1, +70.7] | 10 / 14, p 0.541 |
| | slot 7 (COMPUTED) | 65 (65) | -27.8 [-153.2, +103.9] | 10 / 10, p 1.000 |
| | **pooled, slots 0,1,2,3** | | +51.9 [-37.3, +149.2] over 160 | **68 / 54, p 0.239** |
| | **pooled, slots 4,5,6,7** | | -67.6 [-133.7, -0.3] over 160 | **42 / 56, p 0.189** |
| | **pooled, slots 0,1,2,3,4,5,6,7** | | -7.8 [-64.8, +49.2] over 320 | **110 / 110, p 1.000** |
