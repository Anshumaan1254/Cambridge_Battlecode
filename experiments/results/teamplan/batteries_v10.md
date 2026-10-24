# Batteries of the teamplan switches on the GOD v10 test copy (SIMULATED (v10); tools/teamplan/batteries.py)

Maps `maps/official/*.map26a`, both sides, release mode, cambc engine of `tools/ledger.py`. Columns: wins [95% Wilson interval] | maps won from both sides / split / lost from both sides | sign test on 2-0 vs 0-2 | mean gem margin per map [bootstrap 95%] | deaths ours-theirs.

## Family 1: head-to-head against GOD v10

| Variant | Switch | Result |
|---|---|---|
| `_tp_foc` | kill-value targeting (focus.h) | 41/80 = 51.2% [40.5, 61.9] | 4 / 33 / 3 | p 1.000 | +16.7 [-66.0, +98.5] | 1109-1173 |
| `_tp_bag` | fight bar rises with the bag (bag.h) | 44/80 = 55.0% [44.1, 65.4] | 6 / 32 / 2 | p 0.289 | +37.5 [-43.2, +114.1] | 1168-1155 |
| `_tp_tim` | step into reach only when we act first (timing.h) | 38/80 = 47.5% [36.9, 58.3] | 4 / 30 / 6 | p 0.754 | -7.7 [-101.0, +94.1] | 1107-1119 |
| `_tp_tb` | tiebreak mode, cap 60 (tiebreak.h) | 35/80 = 43.8% [33.4, 54.7] | 1 / 33 / 6 | p 0.125 | -45.8 [-120.8, +23.9] | 1157-1164 |
| `_tp_tb150` | tiebreak mode, cap 150 | 37/80 = 46.2% [35.7, 57.1] | 3 / 31 / 6 | p 0.508 | -18.9 [-100.9, +64.9] | 1106-1180 |
| `_tp_own` | soft group ownership via draft memory (assign.h) | 44/80 = 55.0% [44.1, 65.4] | 13 / 18 / 9 | p 0.523 | +19.0 [-122.3, +158.6] | 1261-1083 |
| `_tp_all` | all five | 39/80 = 48.8% [38.1, 59.5] | 8 / 23 / 9 | p 1.000 | -3.5 [-109.2, +111.3] | 1057-1124 |

## Family 2: against v10 forced to the strong teams' roster per map

GOD v10 itself against it: 37/80 = 46.2% [35.7, 57.1] | 8 / 21 / 11 | p 0.648 | -50.6 [-181.5, +76.7] | 1167-1149

| Variant | Result | Paired margin vs v10's games [95%] | Wins variant / v10 on the same games | Games turned: wins / losses |
|---|---|---|---|---|
| `_tp_foc` | 41/80 = 51.2% [40.5, 61.9] | 11 / 19 / 10 | p 1.000 | -3.1 [-140.8, +130.8] | 1154-1211 | +47.5 [-32.1, +135.2] | 41 / 37 of 80 | 8 / 4, p 0.388 |
| `_tp_bag` | 43/80 = 53.8% [42.9, 64.3] | 13 / 17 / 10 | p 0.678 | +34.8 [-101.6, +171.4] | 1156-1207 | +85.4 [-4.8, +182.2] | 43 / 37 of 80 | 9 / 3, p 0.146 |
| `_tp_tim` | 35/80 = 43.8% [33.4, 54.7] | 10 / 15 / 15 | p 0.424 | -111.3 [-269.5, +42.2] | 1188-1035 | -60.7 [-236.8, +120.3] | 35 / 37 of 80 | 15 / 17, p 0.860 |
| `_tp_tb` | 38/80 = 47.5% [36.9, 58.3] | 11 / 16 / 13 | p 0.839 | -42.1 [-186.3, +95.9] | 1202-1134 | +8.5 [-71.0, +83.6] | 38 / 37 of 80 | 5 / 4, p 1.000 |
| `_tp_tb150` | 40/80 = 50.0% [39.3, 60.7] | 12 / 16 / 12 | p 1.000 | -44.8 [-191.5, +92.8] | 1188-1150 | +5.8 [-98.9, +103.1] | 40 / 37 of 80 | 7 / 4, p 0.549 |
| `_tp_own` | 43/80 = 53.8% [42.9, 64.3] | 11 / 21 / 8 | p 0.648 | +70.2 [-69.7, +226.6] | 1077-1263 | +120.8 [-53.4, +327.3] | 43 / 37 of 80 | 18 / 12, p 0.362 |
| `_tp_all` | 34/80 = 42.5% [32.3, 53.4] | 7 / 20 / 13 | p 0.263 | -128.5 [-263.1, -2.3] | 1235-1048 | -77.9 [-232.5, +69.8] | 34 / 37 of 80 | 17 / 20, p 0.743 |
