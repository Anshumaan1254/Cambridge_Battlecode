# The map model against the current-patch ladder (3C)

599 decoded games on 40 maps (strong vs strong first).

- **Pace**: Spearman(model pace, real finish round) over 40 maps **0.856**; Spearman(model pace, -banked at r400) **0.713**; median real finish / model pace 0.89 (the model plays against the LEARNED opposition share of economy.econ()['contest']; without it the ratio was 1.20).
- **First targets**: over 1197 team-games, the share of the model's plan-1 first targets among the groups the team captured first is **0.540** (baseline: the nearest groups by walk, 0.613).
- **Bank altars**: 0.972 of 24945 bank events are at an altar plan 2 names for some group; the share at the altar nearest to the team's spawn is 0.612 (median over map-teams).

| map | games | model pace | real finish (median) | banked at r400 (median) | ended by gems |
|---|---|---|---|---|---|
| 00ambush | 15 | 1265 | 1119 | 88.0 | 15 |
| 00collision | 15 | 1039 | 1171 | 109.0 | 15 |
| 00contest | 15 | 2000 | 1512 | 0.0 | 15 |
| 00corners | 15 | 819 | 966 | 150.0 | 15 |
| 00eight | 15 | 976 | 993 | 113.0 | 15 |
| 00elkring | 15 | 872 | 885 | 302.5 | 15 |
| 00expanse | 15 | 1088 | 972 | 177.0 | 15 |
| 00fragment | 15 | 2000 | 1557 | 80.5 | 15 |
| 00gem-fields | 15 | 614 | 694 | 358.5 | 15 |
| 00gemfight | 15 | 949 | 769 | 178.5 | 15 |
| 00great-wall | 15 | 1104 | 1007 | 160.0 | 15 |
| 00interlock | 15 | 1258 | 1187 | 116.5 | 15 |
| 00lanes | 15 | 1177 | 1021 | 234.5 | 15 |
| 00lost-world | 14 | 569 | 686.5 | 332.5 | 14 |
| 00monolith | 15 | 1070 | 1050 | 179.5 | 15 |
| 00packs | 15 | 1225 | 1161 | 186.0 | 15 |
| 00pilgrimage | 15 | 2000 | 1538 | 45.0 | 14 |
| 00quadrants | 15 | 621 | 507 | 528.0 | 15 |
| 00reverse-spiral | 15 | 1231 | 1376 | 74.0 | 14 |
| 00road-of-riches | 15 | 930 | 708 | 197.5 | 15 |
| 00rows | 15 | 1316 | 1101 | 122.5 | 15 |
| 00rushbait-v2 | 15 | 1143 | 1087 | 125.0 | 15 |
| 00split | 15 | 909 | 789 | 284.5 | 15 |
| 00stampede | 15 | 2000 | 1802 | 0.0 | 10 |
| 00swirl | 15 | 1051 | 1148 | 125.0 | 15 |
| 01big-world | 15 | 1030 | 1062 | 153.5 | 15 |
| 01boss-battle | 15 | 835 | 1082 | 0.0 | 14 |
| 01broken-curve | 15 | 993 | 847 | 253.0 | 15 |
| 01concentrated-wealth | 15 | 1648 | 1124 | 114.5 | 15 |
| 01corridors | 15 | 1840 | 1142 | 58.0 | 15 |
| 01elk-arena | 15 | 2000 | 1358 | 114.0 | 14 |
| 01fracture | 15 | 1253 | 1083 | 118.0 | 15 |
| 01gold-rush | 15 | 1825 | 1404 | 33.0 | 14 |
| 01hooks | 15 | 1810 | 1194 | 88.0 | 15 |
| 01islands | 15 | 956 | 937 | 218.5 | 15 |
| 01shortcut | 15 | 1674 | 1005 | 113.0 | 15 |
| 01starfish | 15 | 1183 | 1156 | 69.0 | 14 |
| 01starvation | 15 | 2000 | 1741 | 62.0 | 10 |
| 01the-farm | 15 | 1136 | 967 | 159.5 | 15 |
| 01yellow-brick-road | 15 | 587 | 967 | 136.0 | 15 |
