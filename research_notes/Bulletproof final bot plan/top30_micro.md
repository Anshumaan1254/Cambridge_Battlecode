# Fight and micro fingerprints of the CAMBC 2026a top 30 (local replays, Nov 3 2026)

Data and method (applies to every number below). Script `extract3.py` = `experiments/top30_nov3/fights/extract2.py` plus new
fields: target choice per hit, spell and dash casts, contact decisions, objective distance and bush retreats. It ran on **509 of
the 1,201 decoded top-30 vs top-30 games**. I capped the run at 509 games for time. The games are spread evenly: 16-42 per team,
355 team-games for ranks 1-10 and 326 for ranks 20-30. It also ran on **380 of our decoded ladder games: v84 = 261 and v88 = 119**.
The v88 games are all losses (the paired losses), so like with like is: US84 vs OPP84 and US88 vs OPP88 (the opponents in the same
games), plus TOPl (the losing top-30 sides, n = 509 sides). Our opponents are about 2000-rated, not top-30. The fight, exchange and
win definitions are unchanged from the fights stream (exchange = both sides hit; win = more deaths, else at least 1.3x the damage
and at least 150). Local power R = (hp x dps within 6) own / enemy. The item gap is shards per participant, own minus enemy.
Contact = the nearest enemy comes within 5 after 3 or more rounds with none within 6. "Fight" means the body lands a hit within 6
rounds; "leave" means no hit and more than 6 tiles away 6 rounds later. Correlations: Spearman rho across the 30 teams vs rating,
permutation p (1,000 perms), n = 30 teams. Sources:
[tables_micro.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/micro/tables_micro.txt) (drafts, all
columns, correlations, z-scores),
[fingerprint_tables.md](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/micro/fingerprint_tables.md),
[feats.json](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/micro/feats.json) (every feature with n),
scripts `extract3.py`, `patch3.py`, `analyze_micro.py`, `mdtable.py` in the same folder, rows in `micro/out/`.

## Q0. Per-team fingerprint table (30 teams) and the top-10 styles

### Takeaway
Every top-30 team runs a similar core: HoR, Marcella and Vendetta or Vesper, about 18 exchanges a game, about 50% of exchanges
opened, and opening at a median local R of about 2. The top 10 differ in a few rules: when they open, what they hit, and how they
leave. Each top-10 team has one or two clear outliers (below). Cell format: value (n).

### Cited Findings
**Table A. Engagement, exchanges, deaths** (n in parentheses = exchanges or contacts; per-game columns n = games; source [fingerprint_tables.md](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/micro/fingerprint_tables.md))

| # | team | rating | games | exch/g | open% (exch) | open R med | open at R<0.67 % | contact: fight% R<0.67 (n) | contact: fight% R>1.5 (n) | exch win% (n) | win% R 0.67-1.5, gap<=3 (n) | K/g | D/g | D walk-in/g | D caught/g | D <=40r after respawn/g |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Mite | 2583 | 41 | 19.0 | 49 (777) | 3.32 | 13 | 37 (100) | 45 (517) | 51 (777) | 46 (60) | 10.0 | 11.8 | 5.0 | 3.5 | 1.5 |
| 2 | Intercontinental Fish | 2562 | 33 | 19.0 | 44 (627) | 2.37 | 23 | 43 (68) | 37 (519) | 56 (627) | 50 (41) | 12.8 | 10.0 | 2.8 | 3.6 | 1.2 |
| 3 | Univardisty of Shingto | 2524 | 32 | 17.3 | 50 (554) | 3.08 | 16 | 50 (34) | 40 (479) | 67 (554) | 69 (55) | 13.4 | 7.8 | 2.8 | 1.2 | 0.9 |
| 4 | Ad Astra | 2516 | 35 | 19.3 | 55 (676) | 1.75 | 24 | 28 (109) | 50 (392) | 48 (676) | 29 (49) | 10.8 | 12.8 | 5.7 | 3.1 | 2.8 |
| 5 | newer team | 2481 | 33 | 19.1 | 58 (629) | 1.25 | 28 | 34 (99) | 39 (321) | 53 (629) | 54 (62) | 6.5 | 7.9 | 3.0 | 2.9 | 1.0 |
| 6 | NEETCoders | 2443 | 33 | 18.5 | 47 (609) | 2.69 | 12 | 25 (84) | 38 (410) | 43 (609) | 33 (50) | 9.1 | 9.4 | 3.5 | 3.9 | 0.8 |
| 7 | BattleCats | 2381 | 39 | 16.7 | 48 (652) | 1.64 | 21 | 30 (101) | 48 (376) | 47 (652) | 56 (48) | 8.0 | 10.7 | 4.6 | 3.4 | 1.7 |
| 8 | test4 | 2366 | 40 | 18.4 | 52 (736) | 1.95 | 18 | 37 (126) | 48 (572) | 48 (736) | 52 (57) | 8.4 | 11.8 | 4.0 | 4.5 | 1.1 |
| 9 | print dont int | 2366 | 35 | 18.6 | 51 (650) | 2.13 | 19 | 39 (83) | 52 (398) | 55 (650) | 57 (54) | 11.5 | 7.8 | 3.9 | 2.3 | 0.6 |
| 10 | Sponge(Albert and Bob) | 2362 | 34 | 20.9 | 56 (711) | 1.88 | 19 | 24 (79) | 52 (382) | 57 (711) | 55 (59) | 10.5 | 8.3 | 2.9 | 3.6 | 0.6 |
| 11 | Trzy Kwaterki | 2346 | 38 | 18.4 | 45 (698) | 2.51 | 13 | 24 (84) | 43 (474) | 43 (698) | 46 (69) | 7.0 | 10.9 | 5.1 | 3.5 | 1.0 |
| 12 | T1 | 2344 | 35 | 21.5 | 48 (751) | 2.33 | 17 | 26 (68) | 45 (382) | 56 (751) | 51 (73) | 9.3 | 7.3 | 2.3 | 3.4 | 0.6 |
| 13 | policy wonk | 2335 | 31 | 23.2 | 47 (719) | 1.66 | 24 | 41 (95) | 56 (431) | 46 (719) | 58 (58) | 10.5 | 12.9 | 4.7 | 4.5 | 2.0 |
| 14 | subscribe to caterpill | 2307 | 33 | 22.0 | 47 (723) | 1.21 | 35 | 37 (117) | 48 (326) | 50 (723) | 51 (44) | 7.4 | 9.8 | 4.2 | 4.1 | 0.7 |
| 15 | Noobot | 2304 | 42 | 20.2 | 56 (848) | 2.33 | 23 | 48 (87) | 53 (584) | 53 (848) | 56 (56) | 9.6 | 9.5 | 3.2 | 3.7 | 1.5 |
| 16 | German Empire | 2289 | 39 | 20.7 | 53 (806) | 1.58 | 26 | 29 (136) | 53 (453) | 39 (806) | 39 (90) | 5.4 | 8.3 | 2.9 | 3.6 | 0.6 |
| 17 | Supaswag | 2282 | 41 | 18.7 | 51 (766) | 1.60 | 25 | 26 (100) | 39 (392) | 49 (766) | 53 (84) | 8.2 | 8.1 | 3.0 | 2.8 | 0.9 |
| 18 | Nyx | 2271 | 37 | 20.8 | 44 (771) | 1.90 | 24 | 29 (119) | 45 (398) | 43 (771) | 37 (47) | 5.5 | 8.6 | 3.2 | 3.5 | 1.1 |
| 19 | JukeFall | 2250 | 41 | 19.1 | 50 (784) | 1.66 | 22 | 38 (100) | 45 (366) | 50 (784) | 51 (73) | 7.8 | 6.4 | 2.6 | 1.9 | 0.5 |
| 20 | conqueror_of_openai | 2234 | 39 | 14.8 | 53 (576) | 2.55 | 14 | 13 (111) | 35 (380) | 50 (576) | 39 (52) | 6.6 | 7.1 | 2.6 | 2.7 | 0.3 |
| 21 | SSSA | 2233 | 35 | 15.2 | 53 (530) | 2.10 | 17 | 22 (83) | 45 (370) | 57 (530) | 53 (47) | 7.9 | 9.7 | 3.7 | 3.8 | 0.8 |
| 22 | :3 | 2231 | 33 | 14.1 | 57 (463) | 2.50 | 17 | 24 (100) | 42 (335) | 56 (463) | 57 (36) | 7.4 | 6.8 | 3.5 | 1.8 | 0.7 |
| 23 | new team(4) | 2231 | 37 | 18.4 | 37 (681) | 1.45 | 31 | 32 (98) | 41 (311) | 51 (681) | 53 (58) | 6.2 | 8.0 | 2.5 | 4.0 | 0.6 |
| 24 | Rogue Lock Pickers | 2215 | 36 | 15.4 | 53 (554) | 1.99 | 21 | 53 (58) | 40 (352) | 55 (554) | 68 (50) | 6.7 | 6.5 | 1.8 | 2.4 | 0.7 |
| 25 | prism best girl | 2207 | 41 | 16.1 | 56 (661) | 1.75 | 25 | 58 (128) | 44 (433) | 51 (661) | 63 (35) | 8.2 | 8.1 | 2.6 | 3.0 | 0.6 |
| 26 | EE | 2203 | 30 | 17.4 | 44 (523) | 1.61 | 26 | 27 (104) | 39 (354) | 43 (523) | 32 (40) | 8.2 | 8.6 | 3.5 | 3.5 | 0.5 |
| 27 | procless | 2201 | 16 | 16.5 | 55 (264) | 1.45 | 30 | 59 (32) | 46 (140) | 40 (264) | 48 (30) | 5.7 | 5.4 | 2.5 | 1.7 | 0.2 |
| 28 | jazz | 2200 | 18 | 15.9 | 52 (286) | 1.78 | 22 | 34 (44) | 41 (187) | 52 (286) | 44 (16) | 8.0 | 9.1 | 2.3 | 4.3 | 0.7 |
| 29 | MFF1 | 2196 | 24 | 16.7 | 48 (401) | 2.40 | 15 | 22 (46) | 54 (221) | 43 (401) | 22 (23) | 4.9 | 7.9 | 3.7 | 2.0 | 0.9 |
| 30 | Olympus | 2192 | 17 | 17.6 | 41 (300) | 2.33 | 20 | 25 (56) | 43 (166) | 51 (300) | 69 (27) | 5.9 | 11.9 | 3.9 | 4.2 | 0.6 |
| | **ranks 1-10** | | 355 | 18.7 | 51 (6621) | 2.08 | 19 | 34 (883) | 45 (4366) | 52 (6621) | 50 (535) | 10.0 | 9.9 | 3.9 | 3.2 | 1.2 |
| | **ranks 20-30** | | 326 | 16.1 | 50 (5239) | 1.93 | 21 | 32 (860) | 42 (3249) | 50 (5239) | 51 (414) | 7.0 | 8.0 | 2.9 | 3.0 | 0.6 |
| | **top-30 losing sides** | | 509 | 18.4 | 48 (9363) | 1.50 | 28 | 32 (1827) | 46 (4927) | 36 (9363) | 44 (772) | 4.7 | 12.7 | 4.9 | 4.4 | 1.6 |
| | **US v84** | | 261 | 22.9 | 53 (5970) | 2.41 | 13 | 24 (873) | 39 (4182) | 55 (5970) | 53 (573) | 9.7 | 8.0 | 3.5 | 2.2 | 0.6 |
| | **OPP v84 (same games)** | | 261 | 22.9 | 47 (5970) | 1.71 | 24 | 35 (924) | 43 (3982) | 45 (5970) | 48 (571) | 7.1 | 10.8 | 3.1 | 4.7 | 1.2 |
| | **US v88 (all losses)** | | 119 | 19.6 | 50 (2328) | 1.89 | 22 | 25 (413) | 41 (1392) | 41 (2328) | 46 (211) | 5.4 | 10.4 | 4.4 | 3.0 | 1.4 |
| | **OPP v88 (same games)** | | 119 | 19.6 | 50 (2328) | 1.91 | 20 | 36 (315) | 43 (1691) | 59 (2328) | 54 (212) | 9.7 | 6.3 | 1.7 | 3.0 | 0.3 |

**Table B. Retreat, targeting, champion micro** (lifts = P(chosen) - 1/n_candidates; same source)

| # | team | rating | games | retreat dash% (n) | HoR retreat dash% (n) | retreat caught% (n) | focus% (hits) | low-hp lift (n) | carrier lift (n) | spell from 4 % (n) | stun followed% (n) | alone% (parts) | HoR dash in% (n) | HoR dash hits% (n) | Marc enh on champ% (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Mite | 2583 | 41 | 88 (346) | 89 (83) | 19 (1729) | 50 (8692) | +0.26 (1196) | +0.01 (484) | 62 (1229) | 53 (948) | 18 (1544) | 42 (973) | 57 (410) | 90 (257) |
| 2 | Intercontinental Fish | 2562 | 33 | 39 (426) | 44 (129) | 14 (1369) | 51 (6320) | +0.28 (805) | +0.11 (364) | 63 (1136) | 52 (584) | 21 (1202) | 60 (515) | 37 (308) | 91 (195) |
| 3 | Univardisty of Shingto | 2524 | 32 | 49 (338) | 56 (242) | 11 (1171) | 58 (6963) | +0.32 (757) | +0.09 (225) | 73 (1429) | 44 (1439) | 11 (1191) | 66 (726) | 94 (478) | 83 (152) |
| 4 | Ad Astra | 2516 | 35 | 80 (356) | 82 (130) | 17 (1417) | 54 (8436) | +0.32 (1229) | -0.02 (538) | 61 (1409) | 51 (924) | 18 (1368) | 41 (824) | 53 (341) | 89 (209) |
| 5 | newer team | 2481 | 33 | 92 (184) | 98 (84) | 15 (1243) | 47 (7785) | +0.25 (1020) | +0.27 (632) | 59 (1545) | 42 (1097) | 29 (1075) | 51 (722) | 83 (368) | 96 (270) |
| 6 | NEETCoders | 2443 | 33 | 63 (428) | 44 (145) | 18 (1339) | 46 (6999) | +0.33 (1101) | +0.22 (487) | 56 (663) | 42 (635) | 21 (1106) | 46 (574) | 74 (266) | 86 (189) |
| 7 | BattleCats | 2381 | 39 | 63 (314) | 67 (109) | 23 (1394) | 52 (7582) | +0.23 (897) | +0.05 (358) | 58 (1576) | 45 (1178) | 20 (1240) | 49 (569) | 85 (278) | 89 (275) |
| 8 | test4 | 2366 | 40 | 82 (409) | 84 (95) | 17 (1710) | 58 (9197) | +0.31 (1235) | +0.18 (372) | 62 (1441) | 51 (897) | 15 (1566) | 40 (755) | 88 (300) | 93 (273) |
| 9 | print dont int | 2366 | 35 | 82 (301) | 79 (157) | 13 (1579) | 54 (8821) | +0.37 (962) | -0.06 (412) | 55 (890) | 50 (896) | 16 (1273) | 50 (819) | 79 (409) | 85 (338) |
| 10 | Sponge(Albert and Bob) | 2362 | 34 | 95 (196) | 93 (73) | 14 (1450) | 44 (7840) | +0.27 (774) | +0.04 (268) | 62 (1445) | 45 (999) | 24 (1322) | 40 (843) | 82 (333) | 94 (237) |
| 11 | Trzy Kwaterki | 2346 | 38 | 66 (362) | 49 (157) | 21 (1457) | 51 (9037) | +0.26 (1422) | +0.12 (617) | 49 (701) | 50 (599) | 20 (1295) | 51 (697) | 80 (356) | 89 (335) |
| 12 | T1 | 2344 | 35 | 66 (353) | 62 (148) | 13 (1663) | 49 (8977) | +0.33 (1151) | +0.16 (521) | 58 (1600) | 44 (1318) | 22 (1370) | 48 (788) | 78 (379) | 92 (297) |
| 13 | policy wonk | 2335 | 31 | 74 (536) | 52 (234) | 15 (2097) | 56 (11802) | +0.30 (2262) | -0.00 (852) | 50 (2061) | 49 (1822) | 21 (1431) | 50 (805) | 74 (399) | 85 (475) |
| 14 | subscribe to caterpill | 2307 | 33 | 76 (366) | 87 (89) | 20 (1441) | 28 (8029) | +0.32 (807) | -0.00 (404) | 48 (934) | 24 (841) | 38 (1153) | 47 (642) | 83 (301) | 91 (225) |
| 15 | Noobot | 2304 | 42 | 68 (298) | 65 (120) | 19 (1686) | 54 (11591) | +0.31 (1429) | -0.01 (624) | 56 (1807) | 52 (1367) | 20 (1792) | 53 (509) | 95 (270) | 90 (385) |
| 16 | German Empire | 2289 | 39 | 81 (436) | 59 (17) | 14 (1710) | 43 (8174) | +0.28 (943) | -0.00 (445) | 55 (1199) | 41 (792) | 31 (1402) | 38 (90) | 35 (34) | 81 (272) |
| 17 | Supaswag | 2282 | 41 | 82 (359) | 76 (80) | 20 (1296) | 42 (7585) | +0.25 (708) | +0.03 (296) | 49 (589) | 33 (443) | 33 (1199) | 56 (490) | 77 (273) | 87 (220) |
| 18 | Nyx | 2271 | 37 | 92 (355) | 95 (111) | 18 (1613) | 36 (6599) | +0.25 (498) | -0.03 (209) | 60 (695) | 33 (600) | 36 (1214) | 47 (840) | 63 (392) | 83 (155) |
| 19 | JukeFall | 2250 | 41 | 86 (397) | 87 (159) | 13 (1527) | 36 (8187) | +0.34 (969) | -0.03 (384) | 54 (978) | 34 (726) | 30 (1320) | 41 (784) | 71 (321) | 80 (256) |
| 20 | conqueror_of_openai | 2234 | 39 | 78 (285) | 78 (90) | 18 (1105) | 41 (6054) | +0.33 (613) | +0.10 (321) | 61 (743) | 42 (566) | 21 (995) | 46 (797) | 50 (363) | 85 (142) |
| 21 | SSSA | 2233 | 35 | 75 (263) | 69 (71) | 22 (1005) | 51 (6324) | +0.35 (765) | -0.13 (333) | 53 (683) | 52 (447) | 22 (953) | 51 (411) | 73 (209) | 92 (226) |
| 22 | :3 | 2231 | 33 | 88 (240) | 93 (58) | 16 (921) | 54 (6066) | +0.23 (640) | -0.02 (319) | 64 (1266) | 57 (670) | 19 (908) | 44 (509) | 52 (224) | 92 (118) |
| 23 | new team(4) | 2231 | 37 | 89 (232) | 89 (114) | 20 (1288) | 44 (6415) | +0.26 (598) | -0.04 (202) | 52 (1164) | 38 (623) | 30 (1142) | 34 (674) | 62 (229) | 78 (286) |
| 24 | Rogue Lock Pickers | 2215 | 36 | 62 (201) | - | 16 (993) | 43 (5248) | +0.31 (829) | +0.06 (301) | 55 (1139) | 40 (566) | 26 (980) | - | - | 87 (132) |
| 25 | prism best girl | 2207 | 41 | 72 (204) | 74 (107) | 19 (1158) | 44 (7833) | +0.26 (1061) | +0.01 (469) | 64 (2045) | 44 (1152) | 24 (1289) | 52 (665) | 32 (345) | 90 (234) |
| 26 | EE | 2203 | 30 | 80 (277) | 78 (85) | 21 (1169) | 45 (5321) | +0.39 (462) | +0.00 (200) | 61 (591) | 47 (422) | 28 (917) | 32 (699) | 41 (221) | 88 (152) |
| 27 | procless | 2201 | 16 | 91 (129) | 98 (50) | 12 (614) | 28 (3161) | +0.31 (300) | -0.00 (217) | 69 (379) | 31 (375) | 36 (455) | 41 (307) | 78 (126) | 97 (92) |
| 28 | jazz | 2200 | 18 | 82 (111) | 60 (48) | 25 (599) | 37 (3337) | +0.29 (472) | +0.15 (191) | 56 (513) | 36 (345) | 23 (534) | 66 (200) | 83 (132) | 89 (101) |
| 29 | MFF1 | 2196 | 24 | 86 (143) | 14 (7) | 19 (647) | 42 (4032) | +0.19 (398) | +0.25 (137) | 64 (334) | 44 (165) | 30 (679) | 70 (20) | 79 (14) | 85 (147) |
| 30 | Olympus | 2192 | 17 | 80 (125) | 80 (40) | 18 (717) | 41 (3461) | +0.22 (249) | +0.05 (104) | 63 (633) | 40 (371) | 20 (568) | 50 (421) | 42 (209) | 92 (118) |
| | **ranks 1-10** | | 355 | 71 (3298) | 69 (1247) | 16 (14401) | 51 (78635) | +0.30 (9976) | +0.10 (4140) | 62 (12763) | 47 (9597) | 19 (12887) | 48 (7320) | 74 (3491) | 90 (2395) |
| | **ranks 20-30** | | 326 | 80 (2210) | 79 (670) | 19 (10216) | 44 (57252) | +0.29 (6387) | +0.02 (2794) | 60 (9490) | 44 (5702) | 25 (9420) | 44 (4703) | 53 (2072) | 88 (1748) |
| | **top-30 losing sides** | | 509 | 77 (4949) | 72 (1516) | 22 (21335) | 47 (104455) | +0.27 (13243) | +0.05 (5934) | 57 (16313) | 45 (11504) | 24 (17178) | 42 (8280) | 66 (3486) | 90 (3481) |
| | **US v84** | | 261 | 39 (3110) | 13 (1579) | 14 (11871) | 51 (76115) | +0.31 (6921) | +0.06 (2454) | 51 (8973) | 48 (9535) | 21 (11298) | 76 (4147) | 93 (3133) | 90 (1784) |
| | **OPP v84 (same games)** | | 261 | 72 (3283) | 72 (927) | 18 (12394) | 45 (71132) | +0.26 (10298) | +0.07 (3266) | 49 (10426) | 42 (8232) | 25 (10923) | 44 (4595) | 67 (2005) | 86 (2401) |
| | **US v88 (all losses)** | | 119 | 38 (1407) | 12 (722) | 20 (5167) | 54 (30872) | +0.29 (2995) | +0.02 (1212) | 47 (3371) | 50 (3563) | 22 (4382) | 72 (1583) | 90 (1141) | 96 (737) |
| | **OPP v88 (same games)** | | 119 | 73 (1285) | 71 (358) | 12 (4660) | 46 (31180) | +0.25 (4910) | +0.05 (1743) | 49 (4151) | 44 (3326) | 26 (4273) | 44 (2211) | 67 (968) | 87 (911) |


Top-10 styles (z = distance from the 30-team mean, features with n >= 15 —
[tables_micro.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/micro/tables_micro.txt) "TOP-10 DISTINCTIVE"):
- **#1 Mite (2583; HoR 100%, Vendetta 98%, Marcella 83%, Vesper 78%, Cassi&Issac 78%, n 41 games). Overwhelming-force opener.** It
  opens only at a big local edge: median R 3.32 (30-team mean 2.03, z +2.5, n 375 openings), and only 13% of openings at R < 0.67
  (z -1.5). It bursts: 29% of spell hits land in the same round as an ally's hit on the same target (n 1,690, z +1.4), and 60% of
  Marcella's spells hit from range 4 (n 521). It escapes with the dash: 88% of retreats with a dash ready use it (n 346; HoR 89%,
  n 83). It still trades bodies: 11.8 deaths vs 10.0 kills a game, 5.0 walk-in deaths a game (z +1.7). Exchange win 51% (n 777);
  at equal power and items 46% (n 60). It wins on economy and tempo, not on exchange efficiency.
- **#2 Intercontinental Fish (2562; Cassi&Issac 100%, HoR 85%, Vendetta 73%, Marcella 70%). Kill-hungry diver.** Most kills per
  game in the top 5 (12.8, z +2.1, n 33). Vendetta's dashes go in (63% engage, n 319, z +1.9). It rarely dashes out: 39% of
  retreats with a dash ready (n 426, z -2.9; HoR 44%, n 129). Its HoR dash lands a hit only 37% of the time (n 308, z -1.6). It
  avoids hitting Marcella (lift -0.22, n 330). Exchange win 56% (n 627). It dies to camps 1.21 times a game.
- **#3 Univardisty of Shingtonwash (2524; HoR 100%, Varg 72%, Marcella 69%, Ryth 62%). Range-4 spell opener plus HoR stun
  follow-up, the most efficient fighter.** Best exchange win in the top 30: 67% (n 554, z +2.8), and 69% at equal power and items
  (n 55). 86% of its openings are spells (n 279, z +2.7), 73% of its spell hits come from range 4 (n 1,429, z +2.5). Its HoR dash is
  offensive only: 66% engage, 12% escape (n 726, z -2.2), and 94% of HoR dashes hit (n 478). Highest focus (58% of 6,963 hits),
  lowest share of lone participations (11% of 1,191). 13.4 kills vs 7.8 deaths a game; caught after a retreat only 1.2 a game
  (z -2.3). Weak spot: camp deaths 2.28 a game (z +3.7).
- **#4 Ad Astra (2516; HoR 89%, Vesper 89%, Marcella 69%, Cassi 57%, Ren 49%). Relentless re-engager.** Most deaths within 40
  rounds of respawn: 2.8 a game (z +3.4). Walk-in deaths 5.7 a game (z +2.4), 12.8 deaths a game. 24% of openings at R < 0.67;
  equal-power, equal-item exchanges won only 29% (n 49). Retreat dash 80% (n 356).
- **#5 newer team (2481; HoR 91%, Marcella 88%, Vendetta 58%, Prism 55%). Opportunistic carrier hunter.** Opens most often: 58% of
  629 exchanges, at the lowest median R in the top 10 (1.25; 28% at R < 0.67). Strongest carrier preference: carrier lift +0.27
  (n 632, z +2.3). Marcella's enhanced attack lands on a champion 96% of the time when one is near (n 270). Clean escapes: HoR
  retreat dash 98% (n 84). Only 7.9 deaths a game.
- **#6 NEETCoders (2443; HoR 94%, Vendetta 91%, Vesper 82%, Marcella 76%). Item-lead fighter.** Opens with a +18.6 shards per
  participant lead (n 284, z +2.6), +12.3 over all its exchanges (n 609, z +2.2). Only 12% of openings at R < 0.67. Wins only 31% of
  par-power exchanges (n 152, z -2.4): it does not win even fights, it avoids them. Carrier lift +0.22 (n 487). HoR retreat dash 44%
  (n 145).
- **#7 BattleCats (2381; HoR 100%, Marcella 100%, Vendetta 90%, Ryth 64%, Prism 36%). Brawler, careless with bags.** Most deaths
  while carrying 10+ gems: 3.56 a game (z +2.5). Its ranged champions attack from range 3 only 55% of the time (n 613, z -2.2).
  Caught on 23% of retreats (n 1,394), on 40% at hp < 50% (n 474). 69% of its openings are spells.
- **#8 test4 (2366; Marcella 100%, Cassi&Issac 100%, HoR 88%, Willow 88%, Vesper 78%). Willow-sustained deathball.** Has more
  bodies than the enemy in 37% of its exchanges (n 736, z +1.8). High focus (58% of 9,197 hits), few lone participations (15% of
  1,566). Vesper's dashes are escapes (69%, n 543, z +1.9). Pays for it with 11.85 deaths a game and 4.5 caught a game.
- **#9 print dont int (2366; HoR 100%, Marcella 100%, Willow 77%, Vendetta 77%, Ryth 60%). Finisher.** Strongest low-hp lift
  (+0.37, n 962, z +1.6). It is the only top-10 team that prefers Marcella as a target (lift +0.07, n 423, z +1.8). It fights at
  contact more than average: 59% at par (n 58) and 52% at R > 1.5 (n 398). 11.5 kills vs 7.8 deaths a game; caught on only 13% of
  1,579 retreats.
- **#10 Sponge (2362; HoR 100%, Marcella 100%, Vesper 97%, Ryth 88%, Cassi 47%). Disciplined skirmisher.** Retreat dash 95% (n 196),
  HoR dash used to escape 49% (n 843, z +1.3), retreats toward allies 56% (n 1,450, z +1.6), dies on only 6% of dives (n 264,
  z -1.8). Exchange win 57% (n 711), 60% at par (n 170, z +1.3).

### Inferences
- There are three families: (a) edge-only openers that escape with the dash (Mite, NEET, Sponge, newer team), (b) burst-and-follow-up
  spell teams (UW, partly Mite), (c) high-tempo trade-bodies teams (Fish, Ad Astra, BattleCats, test4). All three reach the top 10.
  So no single micro rule explains rank; the shared traits are the ones in Q7.
- Rank 1 Mite loses more bodies than it kills (11.8 vs 10.0 a game, n 41). Elite micro is not "never die". It is "die cheap" (see
  bags in Q2) and "fight only with an edge".

### Gaps
- 692 of the 1,201 top-30 games were not extracted (time cap). Teams 27-30 have only 16-24 games. Per-team rates with n < 100 (the
  contact bands, equal-item par exchanges) carry ±10-15 point noise.
- Shard, power and item data come from replays, so causal claims about a team's code are inferences from behaviour.

## Q1. Engagement: who opens, at what power and item gap, walk-ins, fight vs leave at contact, objectives

### Takeaway
Top teams open about half the exchanges, at a median R of about 2. Only about 20% of openings come at R < 0.67. This barely
separates ranks 1-10 from 20-30. What does separate them: top teams open less often from a static position or alone, and they hit
first at contact. Compared with our opponents, **we hit first at contact less often, fight less at par and when strong, and answer a
received opener late**.

### Cited Findings
- Open share of exchanges: ranks 1-10 51% (n 6,621), ranks 20-30 50% (n 5,239). Median opener R 2.08 vs 1.93. Openings at R < 0.67:
  19% vs 21% — [tables_micro.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/micro/tables_micro.txt).
- Openers with no ally within 6: 33% (ranks 1-10, n 3,375) vs 37% (20-30, n 2,612); rho -0.39, p 0.043, n 30. Static openings
  (already in reach 6 rounds before): 25% vs 29%; rho -0.42, p 0.018. Spell openings 58% vs 50% (n 3,375 / 2,612) — same source.
- Walk-in openings (the opener closed the gap): 29% vs 26%; rho +0.31, p 0.10 (not significant) — same source.
- Contact decisions (fight% / leave%): at R < 0.67, ranks 1-10 fight 34% and leave 20% (n 883); 20-30 fight 32%, leave 20%
  (n 860). At par: 46% (n 804) vs 44% (n 704). At R > 1.5: 45% (n 4,366) vs 42% (n 3,249). The share of contacts where the body
  hits first is 69% (n 3,207) vs 67% (n 2,472) — [feats.json](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/micro/feats.json).
- **Us vs our opponents, same games.** We hit first at contact 61% (US84, n 2,828) and 59% (US88, n 1,083), vs 70% (OPP84, n 2,900)
  and 71% (OPP88, n 1,140). We fight at par 37% (US84 n 911, US88 n 404) vs 41-42% (OPP n 965 / 341). We fight at R > 1.5 39% / 41%
  (n 4,182 / 1,392) vs 43% / 43%. We fight while carrying 10+ gems 32% / 33% (n 1,237 / 531) vs 39% / 41% (OPP) and 43-44% (top).
  At R < 0.67 we fight less (24% / 25% vs 35% / 36%) and leave more (28% / 26% vs 24% / 23%), yet US88 dies within 10 rounds of
  14% of weak contacts vs OPP88 7% (n 413 / 315) — feats.json.
- Answering a received opener within 1 round: US84 50% (n 2,777), US88 48% (n 1,166) vs OPP84 59% (n 3,193), OPP88 60% (n 1,162);
  top 54% (ranks 1-10, n 3,246) — feats.json.
- Steps toward the nearest enemy at R < 0.67 with equal or more bodies, per game: US88 31 vs OPP88 13 (n 119 games); ranks 1-10 19,
  20-30 18, TOPl 27 — feats.json (matches S2 of the fights stream).
- Fights near an objective (within 4 of an altar or 3 of a camp): 77% of exchanges for every group (ranks 1-10 77%, n 6,621; 20-30
  79%; US 76-77%). Not a separator — feats.json.

### Inferences
- Top teams do not hold back more at bad odds than ranks 20-30. They open with company and from movement, and they get the first
  hit. Our deficit is at the moment of contact: we lose the first hit about 10 points more often than the same-rated opponents. And
  when we do engage at bad odds, the engagement is a walk-in, which costs about double the death rate.
- Fighting less often at par and at R > 1.5 while carrying is consistent with our hp and odds gates being stricter than our
  opponents', on exactly the contacts where they win most (Q2).

### Gaps
- Contact episodes do not separate "chose to leave" from "was not in reach". Leave rates are an upper bound on deliberate
  disengagement.

## Q2. Exchange outcomes and deaths by context

### Takeaway
Exchange win share is decided by the item gap: about 25% when 3+ shards behind and about 75% when 3+ ahead, in every group. At
equal power and items, ranks 1-10 (50%) do not beat ranks 20-30 (51%). Top teams fight more, kill more and die more, but **lose
fewer gems when they die**. We like-for-like match our opponents at equal items (US84 55% vs OPP84 45%). We lose bodies to walk-ins
and enemy-woken camps.

### Cited Findings
- Exchange win share by item gap (< -3 / ±3 / > +3 shards per participant): ranks 1-10 28% / 52% / 75% (n 2,251 / 2,008 / 2,362);
  ranks 20-30 27% / 51% / 74%; TOPl 22% / 43% / 62%; US84 29% / 55% / 77%; OPP84 23% / 45% / 71% — feats.json.
- Par power with the item gap within ±3: ranks 1-10 50% (n 535), ranks 20-30 51% (n 414), US84 53% (n 573) vs OPP84 48% (n 571),
  US88 46% (n 211) vs OPP88 54% (n 212) — fingerprint_tables.md Table A.
- Kills per game: ranks 1-10 10.0 vs ranks 20-30 7.0 (n 355 / 326 team-games); rho +0.65, p 0.002. Exchanges per game 18.7 vs 16.1;
  rho +0.48, p 0.014. Deaths per game 9.9 vs 8.0; rho +0.34, p 0.04 — tables_micro.txt.
- Gems lost in bags per game: ranks 1-10 87 vs ranks 20-30 140 (n 355 / 326); rho -0.39, p 0.034. Deaths carrying 10+ gems: 2.15 vs
  1.86 a game. US84 59, US88 74 gems a game vs OPP 86 / 39 — feats.json.
- Deaths within 40 rounds of respawn: ranks 1-10 1.2 vs 20-30 0.6 a game; rho +0.55, p 0.002 (Ad Astra 2.8). US88 1.4 vs OPP88 0.3
  — Table A.
- Death context per game (exclusive classes): walk-in deaths, ranks 1-10 3.9 vs 20-30 2.9 vs TOPl 4.9; US84 3.5 vs OPP84 3.1; US88
  4.4 vs OPP88 1.7. Caught after a retreat: 3.2 vs 3.0 vs 4.4; US 2.2 / 3.0 vs OPP 4.7 / 3.0 — Table A.
- **Deaths with hits from a camp the enemy woke: US84 0.86 and US88 0.82 a game vs OPP84 0.34 and OPP88 0.11; ranks 1-10 0.28,
  20-30 0.29, TOPl 0.41 (n 261 / 119 / 355 / 326 / 509 games).** Pure camp deaths: US 0.52 / 0.30 vs OPP 0.82 / 0.66 — feats.json.
- Stunned in the last 3 rounds before death: US 40% / 38% vs OPP 42% / 36%; top 27-30% (n 2,098 / 1,243 / 2,820 / 744 / 3,527 /
  2,606 deaths) — feats.json.

### Inferences
- The micro ceiling at equal items is the same across the top 30. Rating differences inside the top 30 come mostly from the item
  gap and from volume (more exchanges and kills), not from winning more even fights.
- The bag rule: ranks 1-10 die more often but carry less when they die. They bank before they fight, or fight without a bag. That
  is worth about 50 gems a game against ranks 20-30.
- Our enemy-woken-camp death rate is 2.5-7 times the comparison groups (0.82-0.86 vs 0.11-0.41 a game). That is the largest
  like-with-like death gap in this table (known S4).

### Gaps
- The item gap is an economy outcome (economy stream). This analysis cannot say how much of a team's gap comes from fighting
  itself (kills drop bags and gold).

## Q3. Retreats, dashes out, bushes, chases and lures

### Takeaway
Dashing out of a retreat is standard (about 70-80% in every group) except in our HoR (12-13%). Retreats without the dash are caught
twice as often among the top 10. Retreating into a bush and retreating toward allies are near-universal habits at about the same
rates. Chases almost never get the chaser killed (1-2%).

### Cited Findings
- Retreat with the own dash ready, dash used within 2 rounds: ranks 1-10 71% (n 3,298), 20-30 80% (n 2,210), TOPl 77%, OPP84 72%
  (n 3,283), OPP88 73%; **US84 39% (n 3,110), US88 38% (n 1,407); our HoR 13% (n 1,579) and 12% (n 722) vs OPP HoR 72% / 71%** —
  Table B.
- Caught (dead within 8 rounds) on a retreat without the dash: ranks 1-10 9% (n 971) vs 20-30 16% (n 451); rho -0.35, p 0.06, n 29 teams.
  US84 23% (n 1,897), US88 28% (n 877) vs OPP 16% / 14%. With the dash: US 8% / 13% vs OPP 14% / 8% — feats.json.
- Exceptions in the top 10: Intercontinental Fish 39% (n 426) and UW 49% (n 338) rarely dash out. They compensate with low catch
  rates (14% and 11% of retreats) — Table B.
- Retreat into a bush (bush within 3, not already in one): 25-29% in every group (ranks 1-10 28%, n 7,385; US84 25%, n 6,393).
  Retreat toward allies: ranks 1-10 52%, 20-30 48%, US 49% — feats.json. (The bush stream measured -7 to -12 points of death within
  8 rounds for bush retreats.)
- Stun used to cover a retreat: ranks 1-10 14% vs 20-30 9% (n 14,401 / 10,216); rho +0.33, p 0.085. US 10% / 9% vs OPP 13% / 13% —
  feats.json.
- Chases (3+ steps after a retreating enemy): the chaser dies within 10 rounds 1-2% of the time in every group; lured (killed by
  someone other than the chased target) at most 2%. Chases that end with more enemies near: ranks 1-10 37% vs 20-30 31%; rho +0.67,
  p 0.001 (top teams keep chasing into the enemy group, at no measured cost). Dives at R < 0.67: died within 8 rounds 12% vs 11%,
  US88 17% (n 1,453) vs OPP88 6% (n 772) — feats.json.

### Inferences
- The fix for our dash-out bug is known (S1, `g24_flee_dash`). These numbers confirm it is the one retreat rule where we are far
  out of distribution. Every other group is at 70-80% and their no-dash retreats are caught at 9-16% vs our 23-28%.
- Covering a retreat with a stun (Ryth area stun, Marcella's enhanced attack) is a top-10 habit we use less (10% vs 13-14%).

### Gaps
- Bush retreats were not stratified by hp and power here (the bush stream did that). I found no per-team difference large enough
  to call.

## Q4. Target priority, focus fire, spells, kiting

### Takeaway
Everyone prefers low-hp targets (+0.29 to +0.31 lift over a random pick in range). Focus fire (+0.58 rho) and carrier preference
(ranks 1-10 +0.10 vs 20-30 +0.02) separate the strong teams, and we already focus like the top 10. Our two targeting gaps: Ryth's
stun is not cast from range 4, and we have no carrier preference.

### Cited Findings
- Focus (another ally hits the same target within ±2 rounds): ranks 1-10 51% (n 78,635 hits) vs 20-30 44% (n 57,252); rho +0.58,
  p 0.003. US84 51%, US88 54% vs OPP 45-46% — Table B, tables_micro.txt.
- Low-hp target lift (P(hit the lowest-hp candidate) minus 1/n_candidates, hits with 2+ enemies in reach): ranks 1-10 +0.30
  (n 9,976), 20-30 +0.29, US84 +0.31, US88 +0.29, OPP +0.25-0.26 — Table B.
- Carrier lift (candidates carrying 5+ gems): ranks 1-10 +0.10 (n 4,140) vs 20-30 +0.02 (n 2,794); US84 +0.06, US88 +0.02 vs OPP
  +0.07 / +0.05. Strongest: newer team +0.27, MFF1 +0.25, NEET +0.22, test4 +0.18 — Table B.
- Marcella as a target, when she is a candidate: everyone avoids her (lift -0.06 to -0.12); only print dont int is positive
  (+0.07, n 423) — feats.json.
- Spell hits from range 4: ranks 1-10 62% (n 12,763), 20-30 60%, US 51% / 47% vs OPP 49%. **Ryth's area stun from range 4: ranks
  1-10 64% (n 1,997), 20-30 67%, TOPl 59% vs US84 51% (n 4,567), US88 47% (n 1,645), OPP 48-51%.** Marcella's spell from range 4:
  55% top, US 53% / 49%, OPP 46% / 45% — feats.json.
- A stun followed by an ally hit on the stunned target within 2 rounds: ranks 1-10 47% (n 9,597) vs 20-30 44%; rho +0.44, p 0.015;
  US 48-50% vs OPP 42-44% — Table B.
- Spell burst (a spell lands in the same round as an ally's hit on the same target): ranks 1-10 24% vs 20-30 21%; rho +0.32, p 0.07.
  US 27-28% vs OPP 23-24% — feats.json.
- Kiting (a ranged basic attack on a melee target from range 3 / range 1): ranks 1-10 68% / 11% (n 14,875) vs 20-30 65% / 14%; the
  range-1 share has rho -0.35, p 0.06. US84 63% / 13%, US88 59% / 15% vs OPP 60-62% / 15-17% — feats.json.

### Inferences
- Target choice is not where we lose: low-hp lift, focus and stun follow-up are at or above our opponents and the top 10. The
  addable rules are (1) prefer the bag carrier when two targets are in reach (the top 10 do, at +0.10), (2) cast Ryth's stun from
  range 4 instead of after closing, and (3) keep ranged bodies at range 3 against melee (59-63% vs 68% for the top 10).

### Gaps
- Candidate sets use positions at the moment of the hit and 'in reach' only. A pick that needs a step to reach is not counted.

## Q5. Champion-specific micro

### Takeaway
The HoR dash is offensive for the strong teams, but they also use it to escape (35-49%). Ours is offensive only (escape 7%). The
best teams land the HoR dash on a target far more often (top-10 74% vs 20-30 53%), as does UW (94%). Marcella's enhanced (stun)
attack is spent on champions about 90% of the time when one is near, in every group. Vendetta's dash goes in more often in the top
10.

### Cited Findings
- HoR dash with an enemy within 6, engage / escape share: ranks 1-10 48% / 35% (n 7,320), 20-30 44% / 40% (n 4,703), OPP 44% /
  36-40%, **US 76% / 7% (n 4,147), US88 72% / 7% (n 1,583)**. Engaging HoR dashes that hit an enemy: ranks 1-10 74% (n 3,491) vs
  20-30 53% (n 2,072); rho +0.29, p 0.135 (not significant); UW 94%, Noobot 95%; US 93% / 90% — Table B, feats.json.
- Vesper dash engage / escape: ranks 1-10 51% / 45% (n 4,327), 20-30 52% / 42%; test4 escapes 69% (n 543). US 42% / 50%, OPP 38-43%
  / 49-56% — feats.json.
- Vendetta dash engage: ranks 1-10 47% (n 3,027) vs 20-30 40% (n 3,391); rho +0.28, p 0.15. Fish 63%, Ad Astra 62%, Sponge 22%.
  US84 50%, OPP84 39% — feats.json.
- Marcella's enhanced attack lands on a champion (not a camp) when an enemy is within 4: 86-96% in every group (ranks 1-10 90%, n
  2,395; US88 96%). Over all of her enhanced attacks, the share on champions correlates with rating (rho +0.59, p 0.002; 23% vs 17%),
  i.e. strong teams' Marcellas spend more of their enhanced attacks in fights than on camps — tables_micro.txt.
- Ryth: the area stun hits a champion on 92-99% of casts with an enemy within 5 (all groups); the gap is range (Q4) — feats.json.

### Inferences
- The HoR rule set that matches the top 10: dash in only when the landing tile hits a target (they are selective: 48% engage share
  but 74% land), and keep the dash for the exit otherwise (35% escapes). Ours dashes in almost every time and never out.

### Gaps
- Varg shields, Willow heals, and Cassi's stun (no damage) are not covered by the hit model. Their teams' (UW, test4, print dont
  int) sustain is not measured.

## Q6. Rescue, regroup and stacking

### Takeaway
Stronger teams fight with more company: fewer lone participations (rho -0.48) and more allies within 6 at the first hit (rho
+0.44). Late joining (rescue) is common everywhere (about 70% of non-opener participations) and does not separate groups.

### Cited Findings
- Participation with no ally within 6 at the first own hit: ranks 1-10 19% (n 12,887) vs 20-30 25% (n 9,420); rho -0.48, p 0.011.
  Allies within 6: 1.71 vs 1.41; rho +0.44, p 0.015. UW 11%, test4 15% vs subscribe to caterpillow 38%, Nyx 36%, procless 36%. US
  21-22% vs OPP 25-26% — Table B, tables_micro.txt.
- Late joiners (first own hit 2+ rounds after the fight starts, non-openers): ranks 1-10 72% (n 9,517), 20-30 70%, US 73% vs OPP
  67-68% — feats.json.
- More bodies than the enemy in the exchange: ranks 1-10 29% vs 20-30 28%; US 29-30% vs OPP 22-23% (n 5,970 / 2,328 each) —
  feats.json.

### Inferences
- We already stack and join as often as the top 10. Our numbers problem is not joining. It is joining against a stronger group
  (S2: 31 steps a game at R < 0.67 with equal or more bodies vs 13 for OPP88).

### Gaps
- Late joins do not distinguish a rescue (an ally being hit) from a planned second wave.

## Q7. What separates the strongest teams, what separates us, and rules to beat each style

### Takeaway
Across the 30 teams, rating goes with volume and coordination, not with caution: kills a game (+0.65), focus (+0.58), Marcella
spending her enhanced attack in fights (+0.59), exchanges a game (+0.48), and not fighting alone (-0.48). It also goes with dying
with a small bag (-0.39). Like with like, our out-of-distribution traits are: the HoR dash never used to escape (12-13% vs about
70%), deaths to enemy-woken camps (0.82-0.86 vs 0.11-0.41 a game), the first hit at contact (59-61% vs 70-71%), a late answer
(48-50% vs 59-60%), walk-ins at bad odds (31 vs 13 steps a game), and Ryth's stun not cast from range 4 (47-51% vs 64-67%).

### Cited Findings
- Spearman with rating, n = 30 teams (tables_micro.txt): chases that end among more enemies +0.67 (p 0.001); kills a game +0.65
  (p 0.002); Marcella's enhanced attacks on champions +0.59 (p 0.002); focus +0.58 (p 0.003); deaths within 40 rounds of respawn
  +0.55 (p 0.002); exchanges a game +0.48 (p 0.014); lone participations -0.48 (p 0.011); stun follow-up +0.44 (p 0.015); static
  openings -0.42 (p 0.018); lone openings -0.39 (p 0.043); bag lost a game -0.39 (p 0.034); no-dash retreats caught -0.35 (p 0.06, n 29).
  Not related to rating (|rho| < 0.3): retreat dash use, contact fight rates by band, spells from range 4, bush retreats, fights near
  objectives, low-hp targeting.
- Like-with-like gaps (US vs OPP, same games; numbers in Q1-Q5): the HoR retreat dash 13% / 12% vs 72% / 71%; deaths to enemy-woken
  camps 0.86 / 0.82 vs 0.34 / 0.11 a game; the first hit at contact 61% / 59% vs 70% / 71%; an answer within 1 round 50% / 48% vs
  59% / 60%; weak steps toward the enemy with equal or more bodies 31 vs 13 a game (v88); Ryth's stun from range 4 51% / 47% vs
  48-51% OPP but 64-67% top; ranged attacks from range 3 63% / 59% vs 68% top.
- Where we already match or beat our opponents: focus (51-54% vs 45-46%), low-hp lift, stun follow-up (48-50% vs 42-44%), equal-item
  exchange win (US84 55% vs 45%), and bag lost a game (59-74 vs 86 / 39).

### Inferences
Rules a bot needs, per style (each tied to the numbers above):
- **vs edge-only openers (Mite, NEETCoders, Sponge):** they open at a median R of 2.7-3.3, rarely at R < 0.67 (12-13%), and win only
  31-46% of par exchanges (NEET n 152, Mite n 60). Rule: never give them the edge. Do not split within 6 tiles of their group. Accept
  par fights against them (they decline or lose them) and fight back at par instead of leaving. Against NEET's item lead, avoid
  exchanges when 3+ shards behind (about 25% win share in every group).
- **vs range-4 spell openers (UW, Mite; Ryth / Marcella / Cassi):** 73% of UW's spell hits come from range 4, then the HoR dash-stun
  (94% land). Rule: treat an enemy Ryth, Marcella or Cassi within 5 with its spell ready as being in reach. Either step out of range
  4 or close and answer in the same round (our 48-50% within 1 round vs 59-60%). Stand off their HoR's dash-landing tiles (2 + 1)
  when the HoR dash is ready.
- **vs carrier hunters (newer team, NEET, test4, MFF1; carrier lift +0.18 to +0.27):** bank before contact. Do not path a carrier
  within 6 of their group. Their pick-offs come at a low R (newer team opens at a median 1.25), so a carrier escorted by one ally
  flips the trade.
- **vs divers and re-engagers (Fish, Ad Astra, BattleCats):** they die after respawn (Ad Astra 2.8 a game) and walk in (5.7 a
  game), and Fish does not dash out (39%). Rule: hold a short retreat, regroup, and counter-hit the over-extended body. Chasing a
  retreating Fish body pays: chase deaths are 1-2% everywhere.
- **vs deathballs (test4, UW; more bodies in 37% of test4's exchanges, 11-15% lone participations):** never take a contact alone
  (stronger teams fight alone 19% vs 25%). Wait for a second body before the first hit.
- **Our own fixes, ranked by like-with-like gap:** (1) dash out of retreats with HoR (S1, `g24_flee_dash`); (2) the lure veto for
  enemy-woken camps (S4, `g24_lure`); (3) get the first hit at contact: hit when in reach at par or better instead of holding, and
  answer when hit (S6, `g24_hit_is_fight`); (4) no steps toward a stronger group (S2, `g24_abandon_r` / `g24_rescue_pw`); (5) cast
  Ryth's stun at range 4, and keep Vesper at range 3 against melee; (6) carrier-first target tie-break; (7) bank before fighting:
  top-10 bag loss is 87 vs 140 gems a game for ranks 20-30.

### Gaps
- No v95 (live) games were in the decoded set, so all "us" numbers are v84/v88. Our opponents are about 2000-rated, not top-30.
  Top-30 behaviour against weaker opponents is not measured.
- Correlations across 30 teams are confounded with economy (kills and exchanges rise with items) and with the draft (spell range,
  HoR dash). Values with p > 0.05 are leads, not findings. The 2-3 strongest per-team claims rest on 30-60 games per team.
