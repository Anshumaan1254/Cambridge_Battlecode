# Strategy-v2 report: the 3 top-team match groups of 18 Oct 2026 (15 games, us = team 0)

Group ids: X = b26d9db7, Y = 24706e13, Z = 8ba81317. Made with `python3 tools/strategy_v2/run_all.py OUT <the three zips>`.

## Results

| Match | Rounds | Banked us-them | Body deaths | Kills | Camp gems | Gold earned |
|---|---|---|---|---|---|---|
| 24706e13_01_expanse | 599 | 806-1016 | 1-0 | 0-1 | 806-1016 | 3466-4760 |
| 24706e13_02_ambush | 538 | 428-1024 | 3-2 | 1-2 | 428-1024 | 1120-3340 |
| 24706e13_03_stampede | 1268 | 900-1260 | 28-14 | 10-20 | 1080-1080 | 6649-10064 |
| 24706e13_04_eight | 436 | 22-1130 | 17-1 | 0-13 | 88-1130 | 360-5350 |
| 24706e13_05_corners | 446 | 320-1004 | 10-0 | 0-8 | 692-886 | 2952-4400 |
| 8ba81317_01_elkring | 439 | 288-1008 | 9-2 | 2-7 | 540-864 | 3210-5030 |
| 8ba81317_02_ambush | 720 | 1110-870 (win) | 0-3 | 1-0 | 1110-976 | 2549-3240 |
| 8ba81317_03_monolith | 392 | 724-1002 | 1-0 | 0-1 | 834-980 | 3552-4110 |
| 8ba81317_04_swirl | 498 | 670-1024 | 19-7 | 3-12 | 864-1024 | 3932-6180 |
| 8ba81317_05_fragment | 639 | 270-1056 | 16-5 | 5-10 | 300-1048 | 2035-5500 |
| b26d9db7_01_eight | 566 | 264-1008 | 13-6 | 4-10 | 264-1096 | 1280-4985 |
| b26d9db7_02_collision | 621 | 242-1002 | 15-5 | 3-10 | 336-1024 | 1663-4775 |
| b26d9db7_03_elkring | 486 | 360-1008 | 10-6 | 5-7 | 432-1044 | 2659-6005 |
| b26d9db7_04_swirl | 466 | 168-1016 | 18-13 | 3-10 | 124-1104 | 775-5460 |
| b26d9db7_05_packs | 609 | 1024-884 (win) | 6-8 | 5-4 | 864-1088 | 3708-3640 |

Total over 15 games: wins 2-13, banked 7596-15312, body deaths 166-72, kills 42-115, camp gems 8762-15384, gold 39910-76839, captures 202-355, recalls 383-476, banks 153-263

## Camp-gem decomposition

| | Us | Them | Ratio |
|---|---|---|---|
| Alive | 80.5% | 91.0% | 0.884 |
| Camp time (share of alive) | 18.4% | 21.2% | 0.865 |
| Camp damage per camp round | 84.3 | 118.5 | 0.711 |
| Gems per 1,000 camp damage | 15.1 | 14.4 | 1.047 |
| **Product** | | | **0.570** |

## Per match: alive, camp rounds, camp damage per camp round, gems per 1,000 camp damage (us / them)

| Match | Alive % | Camp rounds | Camp damage per camp round | Gems per 1k camp damage |
|---|---|---|---|---|
| 24706e13_01_expanse | 99 / 100 | 564 / 449 | 85 / 169 | 16.7 / 13.4 |
| 24706e13_02_ambush | 94 / 96 | 297 / 566 | 77 / 100 | 18.7 / 18.0 |
| 24706e13_03_stampede | 80 / 89 | 701 / 851 | 146 / 153 | 10.5 / 8.3 |
| 24706e13_04_eight | 61 / 98 | 228 / 589 | 43 / 115 | 9.0 / 16.7 |
| 24706e13_05_corners | 81 / 100 | 566 / 694 | 73 / 88 | 16.7 / 14.4 |
| 8ba81317_01_elkring | 79 / 95 | 575 / 681 | 72 / 102 | 13.0 / 12.4 |
| 8ba81317_02_ambush | 100 / 96 | 605 / 570 | 73 / 105 | 25.1 / 16.3 |
| 8ba81317_03_monolith | 99 / 100 | 638 / 585 | 85 / 103 | 15.3 / 16.3 |
| 8ba81317_04_swirl | 57 / 83 | 255 / 482 | 199 / 197 | 17.1 / 10.8 |
| 8ba81317_05_fragment | 64 / 88 | 422 / 483 | 60 / 151 | 11.8 / 14.3 |
| b26d9db7_01_eight | 81 / 90 | 376 / 656 | 51 / 99 | 13.7 / 16.8 |
| b26d9db7_02_collision | 68 / 88 | 378 / 605 | 61 / 99 | 14.6 / 17.1 |
| b26d9db7_03_elkring | 86 / 88 | 522 / 831 | 75 / 88 | 11.1 / 14.2 |
| b26d9db7_04_swirl | 56 / 72 | 238 / 424 | 74 / 162 | 7.0 / 16.0 |
| b26d9db7_05_packs | 85 / 80 | 512 / 523 | 78 / 93 | 21.8 / 22.3 |

## How bodies spend their time (% of body-rounds)

| Who | dead | recall | tribute | fight | camp | capture | spawn | walk | idle |
|---|---|---|---|---|---|---|---|---|---|
| us, all | 19.5 | 3.9 | 1.9 | 3.8 | 14.8 | 2.1 | 2.6 | 49.0 | 2.4 |
| them, all | 9.0 | 5.1 | 4.1 | 3.6 | 19.3 | 5.0 | 2.2 | 49.7 | 2.1 |
| us, Cassi | 24.5 | 3.0 | 1.1 | 3.1 | 14.8 | 1.8 | 2.8 | 47.3 | 1.8 |
| them, Cassi | 12.3 | 4.7 | 3.0 | 2.5 | 20.7 | 4.2 | 2.2 | 48.4 | 2.0 |
| us, Issac | 24.4 | 3.8 | 2.2 | 3.7 | 17.6 | 2.2 | 1.8 | 41.6 | 2.7 |
| them, Issac | 12.3 | 6.6 | 4.4 | 3.2 | 18.4 | 5.2 | 2.2 | 45.3 | 2.4 |
| them, Prism | 4.8 | 3.5 | 1.0 | 0.2 | 11.3 | 6.6 | 1.7 | 70.5 | 0.4 |
| us, Ren | 17.4 | 5.0 | 3.7 | 4.6 | 15.4 | 3.4 | 2.0 | 45.0 | 3.4 |
| them, Ren | 8.5 | 5.9 | 3.8 | 4.7 | 20.2 | 5.2 | 1.9 | 48.4 | 1.5 |
| us, Ryth | 14.5 | 3.2 | 0.9 | 4.0 | 12.3 | 1.2 | 2.4 | 59.1 | 2.3 |
| them, Ryth | 10.8 | 4.5 | 5.0 | 5.9 | 23.0 | 4.7 | 2.4 | 41.5 | 2.2 |
| us, Stellar | 16.7 | 4.6 | 1.3 | 3.1 | 15.1 | 1.6 | 3.8 | 50.8 | 3.1 |
| them, Stellar | 7.6 | 4.6 | 4.1 | 3.7 | 17.9 | 5.0 | 2.4 | 51.9 | 2.9 |
| them, Tavi | 4.3 | 2.5 | 0.3 | 1.5 | 22.7 | 3.3 | 1.6 | 61.9 | 1.9 |
| us, Varg | 16.7 | 3.6 | 1.9 | 4.3 | 11.6 | 1.9 | 3.2 | 55.9 | 0.9 |
| them, Varg | 3.8 | 5.4 | 7.0 | 4.8 | 17.5 | 5.9 | 2.2 | 51.7 | 1.6 |

## Items

| | Us | Them |
|---|---|---|
| Gold spent on shards and emblems | 37530 | 68370 |
| Damage-stat points | 775 | 2181 |
| Damage points per 1,000 gold | 20.7 | 31.9 |
| Health points per 1,000 gold | 14.8 | 5.7 |
| Emblems (us) | Bruiser-dmg 64, Monster-dmg 40, Durability-hp 39, Jungle-hp 34, Treasure-dmg 24, Bruiser-hp 17, Jungle-dmg 6 | |
| Emblems (them) | | Power-dmg 295, Durability-hp 38, Bruiser-hp 36, Durability-dmg 23, Jungle-dmg 21, Monster-dmg 4, Power-off 3, Durability-off 2, Jungle-off 2, Treasure-dmg 1 |

## Per champion (games where both teams had it)

| Champion | Games | Captures us/them | Gold earned | Deaths | Camp damage per camp round | First emblem (median) |
|---|---|---|---|---|---|---|
| Cassi | 15 | 2.1 / 3.3 | 306 / 697 | 2.7 / 1.3 | 48 / 81 | 189 / 215 |
| Issac | 15 | 2.5 / 5.5 | 420 / 1019 | 2.7 / 1.3 | 41 / 83 | 311 / 165 |
| Ren | 9 | 4.2 / 5.3 | 762 / 1094 | 1.6 / 0.9 | 56 / 69 | 125 / 118 |
| Ryth | 7 | 1.3 / 4.3 | 216 / 846 | 1.4 / 0.4 | 57 / 105 | 449 / 127 |
| Stellar | 15 | 2.3 / 4.6 | 577 / 1008 | 1.8 / 0.7 | 141 / 195 | 404 / 161 |
| Varg | 10 | 2.1 / 5.4 | 472 / 1339 | 1.5 / 0.2 | 138 / 219 | 232 / 88 |

## Gems captured per 100-round window (us / them)

| Match | r0-100 | r100-200 | r200-300 | r300-400 |
|---|---|---|---|---|
| 24706e13_01_expanse | 88 / 132 | 124 / 146 | 146 / 168 | 124 / 212 |
| 24706e13_02_ambush | 0 / 106 | 48 / 178 | 96 / 250 | 178 / 192 |
| 24706e13_03_stampede | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 24706e13_04_eight | 22 / 160 | 0 / 160 | 22 / 226 | 22 / 540 |
| 24706e13_05_corners | 204 / 196 | 102 / 160 | 116 / 174 | 248 / 290 |
| 8ba81317_01_elkring | 108 / 180 | 144 / 180 | 72 / 216 | 108 / 180 |
| 8ba81317_02_ambush | 0 / 72 | 48 / 226 | 48 / 72 | 226 / 178 |
| 8ba81317_03_monolith | 168 / 212 | 242 / 278 | 256 / 270 | 168 / 220 |
| 8ba81317_04_swirl | 0 / 72 | 124 / 36 | 198 / 292 | 304 / 304 |
| 8ba81317_05_fragment | 102 / 66 | 44 / 80 | 44 / 240 | 22 / 182 |
| b26d9db7_01_eight | 132 / 72 | 0 / 154 | 66 / 182 | 22 / 132 |
| b26d9db7_02_collision | 66 / 132 | 124 / 124 | 44 / 110 | 22 / 154 |
| b26d9db7_03_elkring | 108 / 180 | 108 / 288 | 72 / 216 | 72 / 180 |
| b26d9db7_04_swirl | 0 / 124 | 124 / 88 | 0 / 168 | 0 / 416 |
| b26d9db7_05_packs | 44 / 44 | 136 / 180 | 132 / 184 | 136 / 228 |

## Camp-group kills: count and median rounds from first hit to kill (us / them)

| Group | Kills | Rounds |
|---|---|---|
| 1wolf | 64 / 108 | 18.0 / 11.0 |
| 2gold | 32 / 66 | 19.0 / 9.0 |
| 2wolf | 32 / 51 | 21.0 / 14 |
| 1elk+1gold | 29 / 51 | 24 / 15 |
| 1elk | 17 / 29 | 24 / 11 |
| 1gold+1wolf | 11 / 17 | 35 / 6 |
| 2elk | 6 / 20 | 184.5 / 25.0 |
| 4gold | 6 / 13 | 19.5 / 16 |
| 1elk+3gold | 2 / 14 | 121.0 / 24.0 |
| 4wolf | 6 / 9 | 78.0 / 25 |
| 1elk+2gem+1wolf | 5 / 9 | 181 / 21 |
| 1elk+1wolf | 1 / 12 | 25 / 11.5 |
| 2gem+2gold | 2 / 10 | 27.0 / 17.0 |
| 2gem | 10 / 0 | 22.0 / - |

## Captures, recalls, banks (us / them)

| | Us | Them |
|---|---|---|
| Gem captures (home / neutral / enemy side) | 202 (162 / 36 / 4) | 355 (264 / 61 / 30) |
| Recalls (median health at start) | 383 (0.45) | 476 (0.58) |
| Recalls overlapping a capture | 100 | 174 |
| Banks (mean gems) | 153 (49.6) | 263 (58.2) |
| Banks at neutral altars | 67 | 160 |
| Split rewards (two of a team's bodies capture in the same round, not the pair) | 7 | 14 |

## Respawn wait: rounds a home group sits untouched after it respawns

- us: 125 cycles, median 21, mean 35.4
- them: 204 cycles, median 14.0, mean 28.6

## Fights (152 with 4+ champion hits)

Damage dealt us/them: 91160 / 192227 (ratio 0.47); deaths in fights 133 / 46

| Group | Fights | Deaths us/them | Damage us/them |
|---|---|---|---|
| they had more bodies | 28 | 21 / 0 | 8257 / 28921 |
| equal | 51 | 41 / 9 | 21557 / 55661 |
| we had more bodies | 73 | 71 / 37 | 61346 / 107645 |
| they hit first | 86 | 97 / 17 | 46174 / 134065 |
| we hit first | 66 | 36 / 29 | 44986 / 58162 |
| rounds 0-100 | 23 | 16 / 10 | 15592 / 24431 |
| rounds 100-200 | 31 | 24 / 14 | 19990 / 33223 |
| rounds 200-350 | 51 | 43 / 12 | 24463 / 63099 |
| rounds 350-end | 47 | 50 / 10 | 31115 / 71474 |

## Rounds hit without hitting back

| | Rounds hit | Hit nobody back | Share | Of those: walked |
|---|---|---|---|---|
| Us | 1331 | 985 | 74% | 633 |
| Them | 766 | 422 | 55% | 177 |

Where our walking bodies were, before the step:

- enemy in attack range, moved away: 204 (them: 74)
- enemy within 4, moved toward: 151 (them: 29)
- enemy within 4, moved away: 102 (them: 33)
- nothing in reach, moved toward: 100 (them: 15)
- enemy in attack range, moved toward: 74 (them: 25)
- nothing in reach, moved away: 2 (them: 1)

What the body did in its no-hit-back rounds (us / them):

- moved, above 50% health: 446 / 108
- moved, below 50% health: 186 / 69
- no action (stunned, channel or waiting): 163 / 170
- died that round: 135 / 49
- started a recall or bank: 29 / 5
- other: 21 / 8
- hit a camp instead: 5 / 13

## Death incidents (a Cassi & Issac double death counted once)

Us 126, them 53.

| Cause | Us | Them |
|---|---|---|
| 60+ camp damage taken in the last 5 rounds | 18% | 30% |
| Varg splash on victim + ally (last 5 rounds) | 14% | 6% |
| burst (above 60% health 4 rounds before) | 40% | 40% |
| failed escape (below 35% health, enemy within 6, 4 rounds before) | 25% | 28% |
| killed by a camp | 9% | 21% |
| killed by melee | 52% | 49% |
| killed by ranged | 39% | 30% |
| bag lost at death (gems, total) | 1294 | 832 |

Our killers: Stellar 35, Varg 25, Issac 19, Ren 12, Cassi 12, camp 11, Ryth 10, Prism 1, Tavi 1. Theirs: Stellar 15, Ren 13, camp 11, Ryth 5, Varg 4, Issac 4, Cassi 1.

## KPIs (targets: docs/strategy_v2/05_TEST_AND_SHIP_PLAN.md section 3)

| KPI | Us | Them |
|---|---|---|
| Wins | 2/15 | 13/15 |
| Body deaths per game | 11.1 | 4.8 |
| Share of hit rounds with no hit back | 0.74 | 0.55 |
| Fight damage ratio (ours / theirs) | 0.47 | |
| Damage points per 1,000 gold | 20.7 | 31.9 |
| Gold earned per game | 2661 | 5123 |
| Time alive | 80.5% | 91.0% |
| Time on camps (share of alive) | 18.4% | 21.2% |
| Camp damage per camp round | 84.3 | 118.5 |
| Gem captures per game | 13.5 | 23.7 |

