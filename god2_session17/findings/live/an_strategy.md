# an_strategy: strategy per map, team movement and getting stuck (2026-10-23)

Question: how the top 10 play each map (especially maps built to force fights: shared rich central camps, monoliths, narrow
lanes, contested altars), where and why we lose per map, and whether our champions get stuck. Read-only analysis; nothing under
`bots/` was changed.

## 0. Data, definitions, tools

- **Samples**: 392 of our games vs the top 10 (`rp_bb4D` 200 = bb4 v50 A/B, `rp_ft52D` 192 = v52; 45 wins = 11.5%) and **219
  top-vs-top ranked games** (`rp_top`), all 611 replays (read from the compact dumps in `C:/battlecode/cache/an_fights/dec`,
  same engine path as `tools/replay/decode.mjs`; verified identical to a direct decode on a test replay). Sides from
  `groups_matches.jsonl` / `top_vs_top.jsonl`. Per-map samples are small (ours 6-14, top-vs-top 1-10 per map): read per-map
  numbers as directions, the pooled numbers as the evidence.
- **Zones** use walking distance (BFS, 8 directions, walls / holes / altars / the enemy spawn blocked) from each spawn:
  f = d_own / (d_own + d_enemy); **own < 0.4, mid 0.4-0.6, enemy > 0.6**. Camp **groups** = cardinally connected camps on both
  sides (note: a replay loaded with `Game_FromReplayFileBytes` lists only one copy of each mirrored group; the groups here are
  rebuilt from the decoded camp list). A capture = all CaptureGems events of one team on one group in one round.
- **Fight index** = deaths per 1000 rounds (both teams) in the top-vs-top games on the map (ours if < 2 top games). Terciles:
  **fight >= 16.4**, mixed 9.9-16.4, **farm < 9.9**.
- **Stuck** (per body per game, rounds): *idle* = runs >= 4 rounds alive, off spawn, no move and no action, not ending in a
  capture (tribute channels and completed recalls count as actions; the old `stuck.mjs` counted tributes as idle); *A-B-A*;
  *loop* = 8 moving rounds with net displacement <= 2; *camp stand-still* = >= 8 rounds on a camp tile without a capture;
  *spawn wait* = >= 3 rounds standing on our spawn at full health.
- **P(w>l)** = share of games where the winner's value is higher than the loser's (ties 0.5): 0.5 = no signal.
- New tools (all in `tools/live/`): `strat_mapgeo.mjs` (terrain, spawns, BFS distances, lane min-cut), `strat_mapgroups.mjs`
  (both-side groups), `strat_extract.mjs` (per game: curves, captures by zone/class with bodies near and hitters, heavy-objective
  attempts, deaths by zone, presence, cohesion within 6, contact, stuck metrics + episode lists; reads `.repl26a` or the dumps),
  `strat_agg.py` (tables), `strat_deep.py` (fight-map lines, stand-still / loop classification, contest score), `strat_bank.mjs`
  (banking profile), `strat_case.mjs` (replay window viewer around a tile, for reproducing an episode), `strat_iso.mjs` (isolated
  deaths), `strat_bagtrace.mjs` (one game's banking story), `strat_rollovers.mjs` (fuel rollovers + actions in a window).
  Pipeline: strat_mapgeo -> strat_mapgroups (mapgeo2.jsonl) -> strat_extract (one node process per chunk of dumps is ~50x faster
  than one process per file under load) -> strat_agg.py / strat_deep.py.
  Outputs: `C:/battlecode/cache/an_strategy/` (`ext2_all.jsonl`, `agg.txt`, `deep.txt`, `bank_all.jsonl`, `mapgeo2.jsonl`,
  `maptable.md`, `case_*.txt`).

## 1. Per map: results, gem curves, fight vs farm maps, where the gems are made

### 1.1 By map type (full per-map table in the appendix)

| type (maps) | our W / n | banked median r400 us / them | r600 us / them | gems own-mid-enemy per game, us | them | top-vs-top winner | loser |
|---|---|---|---|---|---|---|---|
| fight (14) | **10 / 131 (8%)** | 19 / 130 | 32 / 269 | 191 - **154** - 1 | 249 - **816** - 22 | 276 - **880** - 13 | 201 - 288 - 2 |
| mixed (13) | 8 / 127 (6%) | 55 / 172 | 93 / 340 | 284 - **114** - 4 | 364 - **585** - 53 | 349 - **630** - 33 | 351 - 196 - 9 |
| farm (13) | 27 / 134 (20%) | 135 / 176 | 269 / 355 | 453 - 233 - 5 | 583 - 407 - 22 | 580 - 425 - 20 | 554 - 249 - 9 |

- Fight maps: elk_arena, lost_world, swirl, contest, gem_fields, hooks, starfish, corridors, boss_battle, yellow_brick_road,
  starvation, eight, fracture, stampede. Farm maps: ambush, collision, expanse, great_wall, lanes, quadrants, rows, rushbait_v2,
  split, big_world, broken_curve, islands, the_farm. Mixed: the rest.
- **Own-half farming is not the gap anywhere.** Own-zone gems are about equal for winners and losers (top-vs-top r<300: 95 vs 92,
  P 0.49) and close between us and them. **The middle is the gap on every map type**: mid gems per game us 168 vs them 601
  (P(us>them) 0.13); top-vs-top winner 657 vs loser 246 (**P 0.87**; fight maps 880 vs 288, P 0.91; farm maps 425 vs 249, P 0.79).
  Already before r300: mid gems us 24 vs them 77; winner 97 vs loser 52 (P 0.68). Nobody invades deep: enemy-zone gems 3-32 per
  game, enemy-zone time 2-5% of body-rounds for every team.
- **Our win rate follows our share of the middle's gems** (392 games): share < 0.2 in 211 games -> **0 wins**; 0.2-0.4 (87) 8%;
  0.4-0.6 (42) 33%; >= 0.6 (27) **81%**. Deaths: games where we died more often than them (267) 2% wins; died less or equal (125) 31%.
- Gem curves: on fight maps we bank a median 19 by r400 vs their 130 (top-vs-top winner 127, loser 58). On farm maps we are
  close (135 vs 176). We are competitive only on rows (10/10), ambush (6/14), collision (4/10), starvation (3/8), the_farm (3/10).
- **Altar-gated maps** (contest, boss_battle, stampede, elk_arena early): both teams bank 0 until r600+ because the altars are
  reachable only through a camp tile (boss_battle: the only altar (25,20) is reachable only from the monolith tile (24,20)) or a
  walled box; whoever controls the altar approach banks. Tribute takes ceil(bag / 10) turns, so big bags cannot be banked there
  (see 3.4 case 2). Top winners place 2.1 altar locks per game, losers 2.5, them vs us 1.5, **us 0.3**.
- Banking profile (`strat_bank.mjs`): top winners bank 24.5 times a game (56 gems per bank, first bank median r106); losers 14.2
  (37, r128); **us 12.7 (38, r140; on fight maps r281)**; them 25.8 (54, r119). Winners carry *bigger* bags (max bag median 121 vs
  82): they bank more because they capture more, not because they bank small.
- Static map features predict fight intensity only weakly: Spearman with the fight index: 1/(spawn-to-spawn walk) +0.36, share
  of gem rate in the middle band +0.34, total gem rate -0.25, lane min-cut -0.16; the best simple score z(1/s2s) + z(-gemRate) +
  z(midShare) reaches +0.40. **Fight intensity is mostly made by the teams, not the map**, so runtime detection should combine a
  static prior (midShare, own-half supply) with what happens (enemies seen in the mid band, first mid capture, kill balance).

### 1.2 The "built to force fights" maps (top-vs-top winner W vs loser L, us U vs them O; per game)

| map | key structure | W mid gems / kills / deaths | L | U | O | our W/n |
|---|---|---|---|---|---|---|
| elk_arena | **all 72 gems in ONE central group** (2 elk + 6 gem) between two altars; s2s 19 | 1104 / 41 / 13 | 144 / 13 / 42 | **12** / 8.5 / 29 (0.2 elk caps) | 1008 / 27 / 10 | 0/6 |
| contest | all 400 gems = 2 monoliths in the middle, altars in a walled box | 1067 / 23 / 12 (5.3 monolith caps) | 0 / 11 / 23 | **0** / 9 / 20 (never captured) | 1025 / 19 / 9 (5.1 mono caps) | 0/8 |
| hooks | all 88 gems in 10 mid groups, 1 altar | 984 / 24 / 8 | 145 / 6 / 25 | **7** / 3 / 25 | 1027 / 24 / 5 | 0/12 |
| stampede | 160 gems, all mid, bush-heavy | 1152 / 18 / 10 | 32 / 10 / 18 | 112 / 17 / 21 | 944 / 20 / 18 | 1/10 |
| swirl | 638 gems all mid, 18 heavy mid groups, s2s 13 | 1021 / 24 / 7 | 307 / 6 / 25 | 103 / 5 / 22 | 1046 / 21 / 5 | 0/6 |
| gem_fields | 80% of the gem rate in the mid band, 6 heavy mid groups | 884 / 13 / 4 | 401 / 4 / 13 | 129 / 9 / 13 | 926 / 12 / 10 | 0/8 |
| corridors | 1 row of 12 fused mid groups + monolith | 1244 / 12 / 14 | 709 / 10 / 16 | 225 / 1.4 / 10 | 1078 / 8 / 3 | 0/12 |
| lost_world | 34 mid groups, monolith + golem, lane min-cut 3 | 968 / 15 / 9 | 627 / 7 / 18 | 260 / 12 / 19 | 1043 / 15 / 16 | 1/10 |
| boss_battle | 1 altar behind the 400-gem monolith pair, cut 2 | 686 / 20 / 12 (1.7 mono caps) | 457 / 10 / 22 | 550 / 11 / 8 (1.4) | 500 / 6 / 11 | 2/8 |

On elk_arena, contest, hooks and stampede our **median first capture is "never"** (2001): we never take the contested gem
source. On elk_arena, contest, hooks, swirl and corridors the opponent kills 2-7x more than we do. Elk_arena replay (3.4 case 3): from r1195 all five of our
bodies stood at full health beside our spawn while :3 held the centre with four bodies and banked 714-0.

## 2. How the top teams play (219 top-vs-top games)

### 2.1 Winner vs loser (means; P(w>l))

| metric | all: W / L (P) | fight maps (79) | farm maps (68) | us / them (392) |
|---|---|---|---|---|
| mid gems per game | 657 / 246 (**0.87**) | 880 / 288 (0.91) | 425 / 249 (0.79) | 168 / 601 (0.13) |
| mid gems r<300 | 97 / 52 (0.68) | 115 / 67 (0.66) | 80 / 52 (0.62) | 24 / 77 (0.31) |
| own gems r<300 | 95 / 92 (0.49) | 55 / 45 (0.55) | 143 / 141 (0.47) | 80 / 91 (0.40) |
| kills / deaths | 11.0 / 4.2 (0.83); deaths 5.2 / 12.0 | 18.4 / 6.9; 8.7 / 20.3 (0.11) | 2.8 / 1.2; 1.6 / 3.3 | kills 5.6 / 9.8; deaths 11.0 / 6.5 |
| largest cluster within 6, r1-150 | 3.38 / 3.14 (0.60) | 3.70 / 3.34 (**0.68**) | 3.17 / 3.05 (0.50) | 2.92 / 3.18 (0.35) |
| >= 3 bodies together, r150-400 | 0.54 / 0.45 (0.62) | 0.67 / 0.55 (0.67) | 0.42 / 0.39 (0.48) | 0.45 / 0.49 (0.43) |
| mid-zone time r150-400 | 0.39 / 0.30 (**0.73**) | 0.45 / 0.37 (0.72) | 0.27 / 0.20 (0.68) | 0.24 / 0.35 (0.25) |
| enemy-zone time r400-800 | 0.05 / 0.02 (0.64) | 0.05 / 0.02 (0.69) | 0.03 / 0.01 (0.62) | 0.05 / 0.05 |
| max hp r400-800 | 2117 / 1787 (0.69) | 2254 / 1684 (0.81) | 1968 / 1994 (0.53) | 1737 / 2142 (0.30) |
| contested captures (enemy hit the group first) | 7.0 / 3.8 (0.75) | 9.3 / 4.4 (0.82) | 3.6 / 2.6 (0.63) | 1.6 / 5.5 (0.15) |
| banks per game | 24.5 / 14.3 (0.81) | 23.6 / 10.0 (0.91) | 23.3 / 17.8 (0.72) | 12.7 / 25.9 (0.17) |
| heavy caps (monolith/golem) | 0.70 / 0.26 (0.58) | 0.46 / 0.15 | 0.81 / 0.50 | 0.19 / 0.61 |
| loop rounds per body | 20 / 30 (0.37) | 24 / 40 (0.30) | 13 / 13 | **52 / 21** (0.93) |

- **The first mid capture predicts the winner**: the top-vs-top winner made the game's first mid-band capture in 135/209 games
  (65%; 37/52 = 71% on maps whose gem rate is all in the middle; median round 49 there, 2.9 bodies of the team near it). In our
  games we made it in 124/367 (34%) and won 21% of those, vs 7% when they did. Bodies in the mid band (all-mid maps): r1-150
  winner 2.24, loser 1.94, **us 1.48**, them 2.09; r150-400 winner 2.50, loser 1.78, **us 1.48**, them 2.23. On maps with 60-90%
  of the gem rate in the middle: r1-150 winner 1.14, **us 0.59**, them 0.97.
- **Cohesion matters on fight maps only and is a style, not a requirement.** Team styles (all sampled games; largest cluster within
  6 in r1-150 / r150-400; share of rounds with >= 3 together in r150-400; win%): Intercontinental Fish 4.09 / 3.43, 0.72 (W 76%:
  the blob); prism best girl 3.46 / 3.02, 0.63 (76%); policy wonk 3.46 / 2.72, 0.52 (64%); Univardisty 3.24 / 2.65, 0.50 (66%);
  :3 3.14 / 2.63, 0.50 (67%); Trzy Kwaterki 3.03 / 2.55, 0.45 (76%); Pantheon 2.91 / 2.37, 0.37 (61%); procless 2.88 / 2.29, 0.34
  (64%); new team(4) 2.84 / 2.40, 0.40 (61%); EMPEROR Tung 2.76 / 2.29, 0.36 (81%); **us 2.92 / 2.50, 0.45 (11%)**. Spread-out
  teams (procless, EMPEROR, Pantheon, new team(4)) win 61-81% with less cohesion than ours; every top team has a **mid-gem share
  of 0.53-0.70; ours is 0.23**. What all of them do: put more bodies in the middle band earlier, win the fights there (kills
  6-12 vs our 5.6, deaths 6.5-10.3 vs our 11.0) and keep it.
- **They hold the middle instead of roaming.** Long stand-stills (>= 10 rounds, no action) of top winners: 3.6 episodes / 75 rounds
  a game; 63% of those rounds in the mid zone (71% on fight maps), 70% next to a camp group, 23% next to an altar (29% on fight
  maps), and 17% end with the team re-taking that group on respawn (35% on farm maps). Ours: 0.62 episodes / 12 rounds a game,
  34% *on* a camp tile (which blocks the respawn). We do not idle; we loop (52 loop rounds per body vs 20 for top winners).
- **Big objectives** (when, with how many):
  - Elk groups are the main gem source: winner 21.1 captures / 718 gems a game, half of them in the middle (2,141 mid vs 2,039
    own across 204 games); loser 13.0 / 390 (826 mid); **us 10.0 / 307, 79% on our own half** (2,861 own / 747 mid); them 20.1 /
    696 (3,413 mid). First elk capture ~r56-65 for everyone: the gap is volume and location, not the opening.
  - Golems (35 top-vs-top games, 65 ours on golem maps): winner 2.14 captures a game, first at a median r287; loser 1.26, r344;
    **us 0.42, r666 (only 15/65 games)**; them 1.63, r349. Attempts (hit episodes): ours 2.0 a game with **1.64 bodies, 20% end in
    our capture**; theirs 3.0 a game with 2.54 bodies, 53%; winners' successful attempts use 3.1 bodies.
  - Monoliths (80 top-vs-top games, 161 ours on monolith maps): winner 0.99 captures a game (took one in 35/80 games, median first
    r842, 3.2 hitters, 2.4 bodies near); loser 0.16 (9/80). **Us 0.29 (34/161, r1040)**; them 0.83 (55/161, r818). 81% of our
    monolith hit episodes end without any capture (won 15%), theirs 63% (won 36%). Contest: the winner kills the monoliths 5.3
    times a game; we never did (0/8).
- **Winner vs loser on the same map** (same structure, 2.1 table): the winner gets the first mid capture, has ~0.3-0.7 more bodies
  in the middle, wins the contested captures (P 0.75), dies half as often, banks twice as often and pulls ahead in items after
  r400 (max hp P 0.69). Cohesion and invasion differences are small; own-half farming is equal.
- Isolated deaths are *not* our main problem: on fight maps 24% of our champion-kill deaths had no ally within 6 (theirs 40%,
  top winners 36%); 39% were outnumbered by 2+ (theirs 49%). We die in group fights we lose (item power and numbers at the point
  of contact; see the fights / items analyses), mostly in the middle.
- Recall spam: Pantheon, :3 and EMPEROR Tung emit ~3,500-3,800 Recall events per 1000 rounds (start + cancel almost every turn;
  starts with > 6-round gaps are a normal 30-52). Any replay metric that counts Recall events as actions mis-scores them
  (handled in `strat_extract.mjs`); the purpose was not investigated.

## 3. Stuck: ours vs top teams

### 3.1 Totals (rounds per body per game; in brackets: with an enemy within 8)

| side | idle | A-B-A | loop | camp stand-still | spawn wait |
|---|---|---|---|---|---|
| **us** (392) | 30.5 | **38.1** (26.4) | **52.4** (32.8) | 1.9 | 3.2 |
| them, vs us (392) | 54.2 | 21.3 (12.7) | 20.7 (10.0) | 4.1 | 1.3 |
| top-vs-top winners (219) | 48.8 | 23.0 (16.6) | 20.2 (12.2) | 5.0 | 1.1 |
| top-vs-top losers (219) | 42.5 | 29.1 (22.5) | 30.0 (21.1) | 2.1 | 3.2 |

- Episodes per game: our loops (>= 16 rounds) 5.2 episodes / **103 rounds**, A-B-A runs (>= 6) 3.0 / 25 rounds; top teams
  2.5 / 55 and 1.6 / 18 (top winners 1.7 / 39 and 1.3 / 15). Losers loop more than winners in top-vs-top too (P 0.37).
- 63% of our loop rounds and 69% of our A-B-A rounds have an enemy within 8 (the in-out combat dance); the rest happen with
  nobody near (19.6 loop rounds per body vs 8-10 for top teams): routing / target flips.
- Holes are not the cause in general (30% of our loop rounds start within 2 of a hole, theirs 32%); walls within 1: 27% vs 19%.
- By champion (loop + A-B-A episode rounds per body-game, us vs top teams): **Heart of Ruin 37 vs 16** (392 bodies), Ryth 28 vs
  12, Prism 31 vs 12, Vesper 22 vs 13, Vendetta 18 vs 13, Marcella 25 vs 19, Varg 63 vs 42, Tavi 33 vs 22, Willow 45 vs 43.
- Worst maps (our loop rounds per body vs theirs): fragment 162 vs 26, reverse_spiral 130 vs 36, starfish 91 vs 24, hooks 83
  vs 12, collision 82 vs 31, corridors 81 vs 25, rushbait_v2 74 vs 22, boss_battle 74 vs 39, eight 67 vs 10, gemfight 61 vs 21,
  lost_world 60 vs 12, great_wall 58 vs 68. Our camp stand-stills concentrate on islands (24 rounds per body, them 0.9) and
  boss_battle (22 vs 21); spawn waits on elk_arena (30.5 vs 2.2), swirl (11.1) and gold_rush (11.3).

### 3.2 Reproducible cases (replay, our side, rounds, tile)

1. **Dead-camp stand (respawn blocked), islands** - `C:/battlecode/cache/rp_ft52D/01islands_cda33abb.repl26a` (us = A vs Trzy
   Kwaterki): our Vesper stands **r670-826 on (23,17)**, a tile of the dead wolf+gold group (wolf 23,17, gold 24,17), hp 466/1600,
   no enemy within 8, no capture, no recall; the group respawns at r830 right after it leaves (an occupied spawn tile delays the
   respawn). `rp_ft52D/01islands_b429522c.repl26a` (A vs Pantheon): our Vesper on the gold row (32-34,12) six times: r81 (38
   rounds), r338 (37), r723 (39), r978 (40), r1043 (42), **r1108 (121, hp 480/1000)**. Islands has 67 of our 244 idle episodes and
   14 of 31 camp stand-stills. `wait_group()` steps off the tiles, so it is another path (low health: home / recall decision?);
   needs a LEGEND_TRACE run on 01islands. View: `node tools/live/strat_case.mjs <replay> 23 17 5 660 830 10`.
2. **Unbankable bag at a camp-gated altar, boss_battle** - `rp_bb4D/01boss_battle_6e52de7d.repl26a` (us = B vs EMPEROR Tung): the
   only altar (25,20) is reachable only from the monolith tile (24,20). Our Heart of Ruin holds (24,20) **r1014-1144 carrying 2,926
   gems**; tribute starts at r1013 / 1388 / 1428 / 1495 / 1691 / 1777 / 1804 never complete (a tribute takes ceil(bag / 10) = 293
   turns; altar locks by both sides at r898 / r954), it dies on the tile at r1144 and the bag is lost; the game ended 49-0 at
   r2000 (we won the tiebreak). Same pattern in `rp_ft52D/01boss_battle_d421e914.repl26a` (HoR r1771, 115 rounds; Vesper r1132, 70).
3. **Shut out at spawn, elk_arena** - `rp_bb4D/01elk_arena_36f90f77.repl26a` (A vs :3): r1195-1270 all five of ours stand at
   full health at (15-17, 23-26) next to our spawn while :3's Prism (5,560 hp), Ryth (5,300), Marcella (4,200) and HoR hold the
   centre (24.5,24.5), kill the 72-gem group every ~65 rounds, capture it four at a time (18 gems each, r1201, r1268) and bank at
   the adjacent altars: 0-714. Our max hp 1,500-3,000 (no gold for items since we never captured the gem group).
4. **Loops / A-B-A** (episode start; enemy within 8 = E):
   `rp_ft52D/01corridors_cd60489c` (B vs policy wonk) Ryth loop r167 66 rounds at (21,21), then A-B-A r177 56 rounds at (22,23) E;
   `rp_bb4D/01corridors_2faec242` (A vs new team(4)) Varg loop r611 69 at (22,14);
   `rp_bb4D/01boss_battle_8bd9612b` (A vs policy wonk) Varg loop r1086 65 at (30,13) + A-B-A r1091 60 at (31,11);
   `rp_ft52D/01starfish_320f1895` (A vs Univardisty) HoR loop r1362 58 + Varg r1364 52 at (14,14);
   `rp_bb4D/00rushbait_v2_dd6841ea` (B vs prism best girl) HoR loop r716 51 + A-B-A r720 35 at (18,38) E;
   `rp_ft52D/00lanes_2420f9dd` (A vs :3) Marcella loop r1058 62 at (42,7);
   no enemy near: `rp_bb4D/00great_wall_db395b4b` Willow A-B-A r131 33 at (40,7); `rp_bb4D/00lost_world_42dccbb0` Willow r514 29 at
   (6,9); `rp_bb4D/00ambush_22a79a99` Prism r434 26 at (71,59). Full lists: `C:/battlecode/cache/an_strategy/agg.txt` ("worst
   episodes").

## 4. Proposals (ranked by expected impact; runtime detection from map features and game state, no map names)

1. **Contest the middle with the team, from the opening** (largest lever; addresses the 0.23 vs 0.53-0.70 mid-gem share).
   *Detect*: at init, the share of the map's gem rate (gems / respawn) in groups with 0.4 < d_ally / (d_ally + d_enemy) < 0.6
   (midShare) and the own-half supply; World already has d_ally / d_enemy per group, `obj_share`, `mono_share`, `contested()`.
   midShare >= 0.6 on 23 of 40 maps, = 1.0 on 8 (no own-half gems at all: elk_arena, hooks, contest, stampede, swirl, lost_world,
   corridors, starvation; starfish 0.95). *Do*: on those maps send 3-4 bodies together to the richest mid group by ~r50 (gather point,
   then go), keep >= 2 bodies in the mid band through r400 (top winners 2.2-2.5 on all-mid maps; we 1.5), and score mid groups
   with the team's strength: in `group_score` the threat veto (brain.cpp:6301-6326, `target_threat_adv` 1.49, allies within 8)
   should count every ally within ~12 for mid / objective groups (the `big_reward` / `big_reward_r` path exists but is off:
   `big_reward 0`), the enemy-half cost should not start at the midline (brain.cpp:6286-6296, `half_grade` 0), and the join limit
   (brain.cpp:6024, `max_join`) should not apply to mid heavy groups. Gate it by state, not only by map: keep the plan while the
   first mid fights go our way (kills >= deaths), fall back to farming (with the bodies together) when they do not.
   *Expected*: the team that made the first mid capture won 65% of top-vs-top games; our win rate goes 0% -> 33% -> 81% as our
   mid-gem share goes < 0.2 -> 0.4-0.6 -> >= 0.6. Even +100-150 mid gems a game (of a 433 gap) moves many losses to the 8-33%
   band. Risk: the whole-game blob lost (1-44); restrict grouping to the opening and to mid heavy groups (procless / EMPEROR win
   spread out).
2. **Hold what we take: wait next to mid groups and contested altars instead of roaming.** Top winners stand still 75 rounds a game,
   two thirds of it in the middle next to camp groups or altars, and re-take groups as they respawn; we loop 103 rounds a game.
   *Do*: in `group_score`'s ST_RESPAWN branch (brain.cpp:6002-6010; `max_wait` / `obj_max_wait` 18) allow longer waits for mid
   groups when no stronger enemy was seen within 8 recently, with `wait_group()` (brain.cpp:7307: next to, never on, the tiles);
   one body per held group, the others on the next mid group. *Detect*: group f in the mid band + respawn timer. *Expected*: more
   mid captures and fewer walk-ins; also removes much of the no-enemy looping.
3. **Heavy objectives with 3+ committed bodies** (golems, monoliths, fused heavy mid groups). Our golem attempts bring 1.64 bodies
   and succeed 20% (theirs 2.54, 53%; winners' wins 3.1 bodies); our first golem r666 vs their r349. 81% of our monolith hit
   episodes give nothing. *Do*: `golem_team` is 0 (params.h:660); plan golems and lone monoliths only with >= 3 claims and the
   kill time from `obj_team_ready()` (brain.cpp:5528), start after the team gathers, and commit (no leaving at half health of the
   camp). *Detect*: `g.golem` / `g.monolith` from engine camp stats; mid band for the team plan. *Expected*: +1.2 golem captures a
   game on the golem maps (their 128 vs our 27 gems a game from golem groups: ~ +100 gems); monoliths +0.5 a game on monolith maps
   (their 188 vs our 91 gems a game: ~ +100).
4. **Stuck fixes** (3.2 cases): (a) combat loops / A-B-A (52 + 38 rounds per body vs 21 + 21; HoR 2.3x the top teams' rate):
   a per-body 8-round position window with net displacement <= 2 and no damage dealt -> commit (fight) or leave for >= 10 rounds;
   the osc_fix pieces (unstick() brain.cpp:1779, flee re-entry skip brain.cpp:6328) cover walks, not the combat dance. (b) Dead-camp
   stand: a body on a dead camp tile with no capture for > 10 rounds steps off whatever its task (the capture timeout in
   `capture_group()` brain.cpp:7361 only covers capture). (c) Camp-gated / contested altars (World `altar_block_g`, `contested()`):
   bank at <= ~60-100 gems (tribute = ceil(bag / 10) turns), escort the tributing body, use and clear altar locks (us 0.3 a game vs
   1.5-2.5). *Expected*: ~10-15% of body-time back on loop-heavy maps; boss_battle-type games decided by the altar.
5. **Never sit at spawn when everything is contested**: on elk_arena all five bodies idled at spawn (spawn wait 30.5 rounds per
   body vs 2.2) because every gem group was vetoed by the threat check. When no group scores > 0 and the map's gems are all in the
   middle, regroup as five and contest (or farm gold together for items) instead of waiting. *Detect*: all positive-value groups
   vetoed for > N rounds + own-half supply ~0.

Caveats: correlations from ladder replays (the strong teams also have better items and fight logic); per-map samples are small;
every proposal needs the in-bot ladder A/B (local mirror games did not predict the ladder in session 16).

## Appendix: per map (sorted by fight index)

Columns: fight index = deaths per 1000 rounds, top-vs-top / ours; banked medians; mid-gem share = our share of all mid gems
captured in our games / the top-vs-top winner's share; gems own-mid-enemy per game; s2s = spawn-to-spawn walk; midShare = share of
the map's gem rate in the mid band (walking distance); mono / golem = groups on the map; altars (in the mid band).

| map | type | fight idx (TvT/ours) | our W/n | banked r400 us / them | r600 us / them | TvT r400 W / L | mid-gem share us / TvT winner | deaths us / them | gems own-mid-enemy us | gems own-mid-enemy them | s2s | midShare | mono / golem | altars (mid) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01elk_arena | fight | 36 / 31 | 0/6 | 0 / 144 | 0 / 342 | 144 / 72 | 0.01 / 0.91 | 29 / 10 | 0-12-0 | 0-1008-0 | 19 | 1 | 0 / 0 | 2 (0) |
| 00lost_world | fight | 35 / 45 | 1/10 | 122 / 234 | 130 / 655 | 360 / 324 | 0.18 / 0.60 | 19 / 16 | 0-260-0 | 0-1043-0 | 26 | 1 | 1 / 1 | 3 (3) |
| 00swirl | fight | 30 / 33 | 0/6 | 38 / 139 | 60 / 380 | 122 / 62 | 0.08 / 0.79 | 22 / 5 | 0-103-0 | 0-1046-0 | 13 | 1 | 0 / 0 | 2 (0) |
| 00contest | fight | 29 / 22 | 0/8 | 0 / 0 | 0 / 0 | 0 / 0 | 0.00 / 1.00 | 20 / 9 | 0-0-0 | 0-1025-0 | 39 | 1 | 2 / 0 | 2 (2) |
| 00gem_fields | fight | 28 / 27 | 0/8 | 144 / 382 | 200 / 647 | 460 / 120 | 0.12 / 0.72 | 13 / 10 | 128-129-0 | 150-926-2 | 41 | 0.8 | 0 / 0 | 4 (2) |
| 01hooks | fight | 27 / 26 | 0/12 | 0 / 154 | 0 / 358 | 132 / 77 | 0.01 / 0.88 | 25 / 5 | 0-7-0 | 0-1027-0 | 34 | 1 | 0 / 0 | 1 (1) |
| 01starfish | fight | 25 / 37 | 2/12 | 52 / 76 | 94 / 120 | 103 / 39 | 0.20 / 0.85 | 29 / 22 | 60-235-1 | 117-893-21 | 41 | 0.95 | 0 / 0 | 2 (2) |
| 01corridors | fight | 23 / 12 | 0/12 | 16 / 102 | 32 / 290 | 45 / 49 | 0.16 / 0.66 | 10 / 3 | 0-225-0 | 0-1078-0 | 35 | 1 | 1 / 0 | 2 (2) |
| 01boss_battle | fight | 20 / 12 | 2/8 | 0 / 0 | 0 / 0 | 0 / 0 | 0.50 / 0.60 | 8 / 11 | 1541-550-6 | 1697-500-19 | 38 | 0.17 | 1 / 0 | 1 (1) |
| 01yellow_brick_road | fight | 20 / 22 | 0/9 | 145 / 243 | 191 / 551 | 226 / 142 | 0.11 / 0.84 | 16 / 9 | 334-47-0 | 552-405-61 | 29 | 0.36 | 0 / 0 | 10 (2) |
| 01starvation | fight | 20 / 18 | 3/8 | 8 / 87 | 26 / 160 | 64 / 56 | 0.30 / 0.72 | 14 / 19 | 0-327-0 | 0-796-0 | 183 | 1 | 2 / 0 | 2 (2) |
| 00eight | fight | 20 / 18 | 0/10 | 59 / 178 | 87 / 482 | 137 / 60 | 0.05 / 0.36 | 13 / 4 | 183-5-0 | 706-92-186 | 46 | 0.08 | 0 / 0 | 1 (1) |
| 01fracture | fight | 18 / 10 | 1/12 | 54 / 131 | 167 / 262 | 190 / 123 | 0.14 / 0.71 | 5 / 7 | 504-138-6 | 372-686-0 | 160 | 0.65 | 2 / 0 | 3 (3) |
| 00stampede | fight | 16 / 20 | 1/10 | 0 / 0 | 0 / 0 | 0 / 0 | 0.16 / 0.98 | 21 / 18 | 0-112-0 | 0-944-0 | 55 | 1 | 0 / 0 | 2 (2) |
| 00elkring | mixed | 16 / 19 | 2/10 | 154 / 337 | 242 / 586 | 319 / 330 | 0.20 / 0.57 | 10 / 6 | 453-86-0 | 581-348-11 | 31 | 0.4 | 0 / 0 | 2 (2) |
| 01concentrated_wealth | mixed | 16 / 15 | 0/7 | 60 / 191 | 80 / 405 | 256 / 56 | 0.07 / 0.92 | 13 / 5 | 207-62-2 | 258-758-15 | 177 | 0.42 | 0 / 0 | 2 (2) |
| 01shortcut | mixed | 16 / 12 | 1/12 | 44 / 142 | 108 / 297 | 116 / 76 | 0.24 / 0.75 | 7 / 7 | 539-186-0 | 422-590-0 | 101 | 0.67 | 2 / 0 | 2 (2) |
| 01gold_rush | mixed | 16 / 19 | 2/11 | 55 / 11 | 77 / 110 | 33 / 66 | 0.20 / 1.00 | 22 / 6 | 272-109-18 | 297-582-62 | 56 | 0.5 | 1 / 0 | 4 (2) |
| 00interlock | mixed | 15 / 14 | 0/6 | 68 / 97 | 118 / 252 | 119 / 157 | 0.14 / 0.74 | 12 / 6 | 100-161-0 | 104-890-8 | 41 | 0.77 | 0 / 0 | 4 (4) |
| 00fragment | mixed | 14 / 16 | 0/10 | 4 / 144 | 16 / 246 | 90 / 98 | - / - | 21 / 3 | 96-0-3 | 576-0-397 | 23 | 0 | 0 / 0 | 2 (2) |
| 00gemfight | mixed | 14 / 23 | 1/12 | 26 / 378 | 44 / 632 | 239 / 142 | 0.08 / 0.83 | 15 / 2 | 132-66-5 | 216-652-61 | 46 | 0.48 | 0 / 0 | 2 (2) |
| 00pilgrimage | mixed | 13 / 10 | 0/8 | 38 / 30 | 96 / 88 | 60 / 48 | 0.24 / 0.74 | 7 / 9 | 276-260-0 | 274-830-8 | 123 | 0.81 | 0 / 0 | 4 (4) |
| 00reverse_spiral | mixed | 13 / 16 | 0/7 | 43 / 71 | 87 / 115 | 77 / 58 | 0.22 / 0.63 | 14 / 12 | 140-176-19 | 438-569-72 | 1 | 0.44 | 0 / 2 | 2 (2) |
| 00monolith | mixed | 12 / 14 | 1/7 | 175 / 232 | 365 / 346 | 246 / 232 | 0.19 / 0.88 | 7 / 8 | 576-87-5 | 694-397-35 | 49 | 0.58 | 2 / 0 | 6 (6) |
| 00corners | mixed | 10 / 20 | 1/13 | 115 / 209 | 141 / 401 | 159 / 172 | 0.17 / 0.66 | 12 / 9 | 318-139-1 | 322-613-11 | 40 | 0.6 | 0 / 0 | 5 (1) |
| 00packs | mixed | 10 / 12 | 0/12 | 48 / 269 | 64 / 473 | 256 / 96 | 0.06 / 0.73 | 10 / 2 | 62-58-0 | 97-927-7 | 26 | 0.77 | 0 / 0 | 6 (2) |
| 00road_of_riches | mixed | 10 / 10 | 0/12 | 113 / 320 | 141 / 610 | 542 / 42 | 0.20 / 0.89 | 5 / 2 | 444-133-2 | 484-532-1 | 243 | 0.22 | 2 / 2 | 2 (2) |
| 00rushbait_v2 | farm | 9 / 10 | 0/10 | 43 / 158 | 145 / 360 | 119 / 117 | 0.32 / 0.43 | 8 / 2 | 343-3-13 | 879-9-71 | 1 | 0 | 0 / 0 | 2 (2) |
| 00quadrants | farm | 8 / 7 | 0/12 | 451 / 596 | 612 / 1018 | 519 / 512 | 0.27 / 0.58 | 3 / 2 | 402-265-5 | 408-692-0 | 50 | 0.76 | 0 / 2 | 4 (0) |
| 00split | farm | 7 / 13 | 1/10 | 218 / 264 | 374 / 532 | 343 / 246 | 0.45 / 0.70 | 6 / 6 | 352-294-3 | 632-385-47 | 84 | 0.28 | 2 / 2 | 3 (1) |
| 00collision | farm | 7 / 9 | 4/10 | 56 / 80 | 78 / 144 | 134 / 53 | 0.34 / 0.74 | 4 / 9 | 304-271-12 | 336-514-22 | 34 | 0.59 | 0 / 0 | 2 (2) |
| 00great_wall | farm | 7 / 8 | 1/14 | 11 / 157 | 139 / 344 | 191 / 204 | - / - | 6 / 2 | 617-0-5 | 998-0-43 | 85 | 0.61 | 2 / 1 | 4 (4) |
| 01broken_curve | farm | 7 / 6 | 0/6 | 168 / 203 | 316 / 386 | 326 / 126 | 0.34 / 0.93 | 3 / 3 | 462-250-15 | 617-475-25 | 35 | 0.56 | 2 / 0 | 4 (2) |
| 00expanse | farm | 5 / 6 | 0/10 | 172 / 168 | 326 / 306 | 205 / 174 | 0.38 / 0.69 | 3 / 4 | 344-383-2 | 452-603-5 | 85 | 0.7 | 0 / 0 | 10 (2) |
| 00ambush | farm | 4 / 5 | 6/14 | 68 / 86 | 229 / 180 | 51 / 70 | 0.32 / 0.55 | 3 / 3 | 624-202-0 | 545-416-2 | 123 | 0.49 | 0 / 0 | 4 (2) |
| 00lanes | farm | 4 / 14 | 0/6 | 149 / 200 | 214 / 408 | 282 / 221 | 0.27 / 0.55 | 12 / 3 | 79-264-0 | 325-718-58 | 81 | 0.67 | 0 / 0 | 18 (0) |
| 01islands | farm | 4 / 7 | 0/11 | 134 / 238 | 203 / 472 | 318 / 161 | 0.26 / 0.64 | 3 / 3 | 267-247-5 | 371-642-30 | 63 | 0.81 | 0 / 0 | 10 (6) |
| 01the_farm | farm | 4 / 7 | 3/10 | 138 / 186 | 372 / 270 | 236 / 208 | 0.31 / 0.69 | 4 / 3 | 624-201-4 | 495-454-0 | 41 | 0.72 | 2 / 0 | 6 (6) |
| 01big_world | farm | 2 / 2 | 2/11 | 150 / 164 | 282 / 341 | 131 / 181 | 0.34 / 0.66 | 1 / 1 | 522-289-0 | 558-548-3 | 139 | 0.72 | 2 / 0 | 6 (2) |
| 00rows | farm | 1 / 1 | 10/10 | 188 / 145 | 338 / 292 | 146 / 146 | 0.95 / 1.00 | 0 / 1 | 690-470-0 | 784-47-0 | 73 | 0.58 | 1 / 0 | 2 (0) |
