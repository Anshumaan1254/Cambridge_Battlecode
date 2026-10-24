# Confirmation battery of the two leads (SIMULATED (v10); tools/teamplan/batteries.py --confirm)

Maps `maps/official/*.map26a`, both sides, release mode. Opponents: GOD v10 (head-to-head) and v10 forced to roster slot k of `tools/mapintel/data/battery_rosters.json` (`_tp_v10F` for slot 0, `_tp_v10F<k>` otherwise; slots 0-3 are real strong-team rosters on all 40 maps, slots 4-7 COMPUTED, balanced over kit classes). Paired = against v10's own games with the same opponent, map and side: the gem margin difference averaged per map [bootstrap 95%], and the games turned into wins / losses (sign test).

| Variant | Opponent | Wins (v10's) | Paired margin [95%] | Games turned: wins / losses |
|---|---|---|---|---|
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
