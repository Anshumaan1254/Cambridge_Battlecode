# an_economy: economy and objectives of the strongest teams over the whole game (Oct 23, current bot versions)

Question: how the six study teams make and keep gems and gold over a whole game (captures by zone, farming cycles, idle groups,
re-taking respawning middle groups, walking, banking, bag sizes and who carries, gems lost on death, banked curves, golems /
monoliths / elk, gold income and spend), plus two special questions: prism best girl's Prism bag and Intercontinental Fish's Vesper
carry. Everything is turned into rules over observable state for god2 (last section). Read-only analysis; nothing under `bots/` changed.

## 0. Data, definitions, tools

- **Replays**: 638 ranked games, Oct 23 ~07:00-15:00 UTC, current bot versions: prism best girl (pbg, #1) 116, Intercontinental Fish
  (ifish, #2) 110, Pantheon (#6) 105, conqueror_of_openai (coo, #18) 101, Claudus Maximus (cm, #19) 106, Nyx (#31) 100 =
  **584 distinct matches** (games between two study teams appear in both sets). Win rates in this sample: pbg 61%, ifish 60%,
  cm 55%, coo 54%, Pantheon 50%, Nyx 49%. pbg / ifish / Pantheon mostly play the top 10; coo / cm / Nyx mostly play lower-ranked
  teams.
- **S** = the study team, **O** = its opponents in the same games (same maps, same sides). **W / L** = winner / loser of each
  distinct match, pooled and team-agnostic (584 matches). **P(w > l)** = share of matches where the winner's value is higher (0.5 =
  no signal).
- **Zones** (as an_strategy): walking distance (8-connected BFS; walls, holes, altars blocked) from each spawn,
  f = d_own / (d_own + d_enemy); **own < 0.4, mid 0.4-0.6, enemy > 0.6**. A group's f uses its nearest camp tile.
- **Capture** = every gold / gem gain of one team on one camp group in one engine Capture step (gold-only captures included).
  **Bag** = gems carried. **Tribute start** = `Submit gems`; its end is classified as done (gems banked), own cancel (`Cancel
  channel`), stun, lock (enemy lock placed on that altar), death, restart, or open at game end. **Finisher** = a tribute start with
  team banked + bag >= 1000 (completion ends the game).
- **Farming cycle** per group: full -> first champion hit (wait) -> every camp dead (kill) -> capture (cap) -> full again.
  **Holding** = bodies within 4 (Chebyshev) of the group's nearest camp tile at the round it respawns.
- **Objective attempt** = one team's hits on one golem / monolith / elk group with gaps <= 30 rounds; **won** = that team captured the
  group within 40 rounds of its last hit, **stolen** = the other team did.
- Everything below is **MEASURED** from replays unless marked **INFERRED** (a reading of why a team does something).
- **Tools** (new, `tools/top2/economy/`):
  - `econ_dump.mjs`: engine timeline decode with exact per-step gold / gem attribution (capture, kill, Marcella bank gold, shop),
    per-round camp health, deaths with bags and killers, stuns, champion and camp damage
    -> `C:/battlecode/cache/t2econ/<key>/*.json.gz` (638 files).
  - `econ_game.py KEY...`: per-game facts (captures, cycles, tributes with context, bank decisions, objective attempts with context,
    walking budget) -> `games_<key>.jsonl`.
  - `econ_agg.py` -> `agg.txt` (all tables of sections 1-8).
  - `econ_special.py` -> `special.txt` (Prism, finishers, bag chains, Vesper, locks).
  - `econ_hold.py` (what holders of respawning middle groups do).
  - Map geometry comes from the cached `C:/battlecode/cache/an_strategy/mapgeo2.jsonl` (tools/live/strat_mapgeo.mjs +
    strat_mapgroups.mjs). Re-run: `bash C:/battlecode/cache/t2econ/run_all.sh`, then the three python scripts.

## 1. What separates winners from losers (584 matches, pooled)

| metric (per team-game) | winner mean | loser mean | winner median | loser median | P(w > l) |
|---|---|---|---|---|---|
| captured gems | 1,043 | 639 | 1,012 | 684 | 0.89 |
| **mid-zone gems** | **617** | **281** | 629 | 216 | **0.82** |
| own-zone gems | 398 | 351 | 385 | 315 | 0.58 |
| enemy-zone gems | 28 | 7 | 0 | 0 | 0.59 |
| elk-group gems | 645 | 379 | 723 | 334 | 0.80 |
| gold earned per 100 rounds | 753 | 465 | 741 | 455 | 0.85 |
| gold earned by r300 | 1,506 | 1,155 | 1,460 | 1,089 | 0.71 |
| kill gold | 1,468 | 585 | 1,059 | 360 | 0.77 |
| deaths | 6.2 | 13.8 | 4 | 10 | 0.24 |
| gems lost on death | 100 | 160 | 21 | 75 | 0.31 |
| gems stolen by kills | 140 | 85 | 63 | 11 | 0.68 |
| tribute starts / completed | 28.2 / 26.5 | 16.6 / 15.1 | 26 / 25 | 14 / 13 | 0.80 / 0.82 |
| median bag banked | 42.7 | 34.6 | 32 | 28 | 0.57 |
| biggest bag carried | 218 | 142 | 138 | 88 | 0.73 |
| banked at r300 | 112 | 76 | 93 | 60 | 0.64 |
| first capture / first mid capture / first bank (round) | 37 / 148 / 193 | 42 / 172 / 211 | 31 / 74 / 111 | 31 / 92 / 121 | 0.48 / 0.45 / 0.42 |
| altar locks placed | 2.3 | 2.3 | 1 | 1 | 0.52 |
| gold-cluster captures | 17.5 | 13.7 | 6 | 6 | 0.54 |
| time: farming / dead / walking (share of body-rounds) | 18.6% / 6.3% / 50.1% | 15.5% / 14.6% / 48.6% | | | 0.71 / 0.25 / 0.56 |
| team max HP r300 / r600 | 6,259 / 9,063 | 5,867 / 7,856 | | | 0.63 / 0.68 |

- **The middle is where the gem gap is made**: winners take 2.2x the loser's mid-zone gems (P 0.82); own-zone gems differ by 13%
  (P 0.58). This re-confirms an_strategy (older versions) on the current versions of every study team.
- **Volume, not first-event timing**: first capture, first mid capture and first bank barely differ (P 0.42-0.48). What differs is
  income by r300 (P 0.71), tributes completed (P 0.82) and deaths (P 0.24).
- Walking share is the same (50% vs 49%); winners farm more (18.6% vs 15.5%) and are dead less than half as often (6.3% vs 14.6%).
- Gold sources over all 638 replays (1,276 team-games): captures 81%, kills 14.5%, Marcella's tribute gold 4% (no passive gold).
  Every team spends 88-95% of what it earns.

## 2. Team profiles: S vs O in the same games

### 2.1 Overview, gold, captures

| team | S win | banked r300 S / O (median) | r600 | gold / 100 r S / O | gold by r300 S / O | kill gold by r300 S / O | captures S / O | captured gems S / O | gems own / mid / enemy S | O | mid share S / O | first elk capture S / O (median r) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pbg | 61% | 74 / 76 | 241 / 259 | 634 / 597 | 1,451 / 1,356 | 170 / 123 | 45.4 / 55.4 | 970 / 801 | 370 / 578 / 22 | 397 / 395 / 10 | 0.60 / 0.48 | 55 / 68 |
| ifish | 60% | **121 / 73** | 358 / 234 | **726 / 614** | **1,658 / 1,359** | 226 / 151 | 50.2 / 51.0 | 943 / 796 | 369 / 564 / 11 | 380 / 404 / 12 | 0.60 / 0.49 | 46 / 65 |
| Pantheon | 50% | 89 / 60 | 240 / 222 | 599 / 613 | 1,355 / 1,356 | 193 / 102 | 56.6 / 52.2 | 866 / 825 | 393 / 466 / 7 | 373 / 435 / 17 | 0.51 / 0.54 | 64 / 60 |
| coo | 54% | 72 / 69 | 234 / 246 | 516 / 634 | 1,135 / 1,357 | 104 / 220 | 47.8 / 54.2 | 842 / 795 | 382 / 444 / 16 | 382 / 394 / 20 | 0.54 / 0.48 | 94 / 76 |
| cm | 55% | 89 / 64 | 299 / 221 | 627 / 625 | 1,256 / 1,327 | 196 / 231 | 53.1 / 50.6 | 847 / 791 | 333 / 477 / 37 | 355 / 413 / 22 | 0.56 / 0.49 | 64 / 79 |
| Nyx | 49% | 57 / 61 | 197 / 224 | 561 / 556 | 1,231 / 1,146 | 123 / 117 | 67.2 / 44.2 | 858 / 816 | 400 / 432 / 26 | 390 / 409 / 17 | 0.52 / 0.53 | 87 / 62 |

**Captures by camp class** (per game: captures / gems / gold):

| team | elk groups | wolf groups | gem clusters | gold clusters | golem | monolith |
|---|---|---|---|---|---|---|
| pbg S | 16.8 / 613 / 3,328 | 12.6 / 134 / 1,276 | 3.2 / 58 / 46 | 11.9 / 0 / 801 | 0.4 / 32 / 90 | 0.5 / 133 / 211 |
| pbg O | 14.9 / 484 / 3,006 | 17.3 / 184 / 1,688 | 6.6 / 94 / 61 | 16.4 / 0 / 922 | 0.1 / 9 / 29 | 0.1 / 30 / 61 |
| ifish S | 17.1 / 598 / 3,771 | 13.9 / 148 / 1,581 | 3.8 / 64 / 49 | 14.8 / 0 / 885 | 0.3 / 23 / 75 | 0.4 / 112 / 230 |
| ifish O | 14.8 / 493 / 3,001 | 15.9 / 168 / 1,582 | 5.1 / 79 / 60 | 14.9 / 0 / 805 | 0.2 / 15 / 43 | 0.1 / 41 / 71 |

- **The two best teams make fewer captures but bigger ones**: pbg makes 45 captures a game against its opponents' 55 and still
  takes 21% more gems. It skips small groups (gem clusters 3.2 vs 6.6, gold clusters 11.9 vs 16.4, wolves 12.6 vs 17.3) and takes
  more elk groups, golems and monoliths. ifish follows the same pattern. Their extra gems are all middle gems (+183 / +160 a game);
  own-zone gems are equal or lower.
- **Gold**: ifish earns 18% more than its opponents (726 vs 614 per 100 rounds), pbg 6% more. coo is the weak economy (516 vs 634)
  and still wins 54% against weaker opposition.

### 2.2 Gem flow and deaths

| team | captured | stolen by kills | banked (final) | lost on death | of which to camps | carried at end | deaths / game | big-bag (>= 100) deaths / game | who dies with >= 100 |
|---|---|---|---|---|---|---|---|---|---|
| pbg S / O | 970 / 801 | 125 / 85 | 840 / 691 | 117 / 130 | 32 / 5 | 139 / 64 | 7.4 / 10.8 | 0.24 / 0.14 | Prism 16, Vesper 5, Marcella 4 |
| ifish S / O | 943 / 796 | 150 / 131 | 860 / 672 | 153 / 167 | 22 / 17 | 80 / 89 | 12.2 / 10.9 | 0.17 / 0.17 | Vesper 13, Vendetta 2, HoR 2 |
| Pantheon S / O | 866 / 825 | 176 / 227 | 742 / 741 | **237** / 196 | 10 / 20 | 63 / 116 | 6.3 / 10.2 | **0.45** / 0.26 | **Prism 33**, Marcella 8, Vesper 4 |
| coo S / O | 842 / 795 | 92 / 156 | 734 / 769 | 168 / 105 | 12 / 14 | 31 / 77 | **13.3** / 8.1 | 0.21 / 0.19 | Vendetta 7, Vesper 6, HoR 5 |
| cm S / O | 847 / 791 | 85 / 80 | 785 / 721 | 100 / 102 | 20 / 17 | 47 / 48 | 12.7 / 11.1 | 0.08 / 0.15 | Vendetta 3, HoR 3 |
| Nyx S / O | 858 / 816 | 77 / 94 | 760 / 729 | 133 / 99 | 40 / 21 | 42 / 82 | 8.2 / 9.8 | 0.34 / 0.20 | Prism 24, Vesper 5, Marcella 5 |

- **Bag chains** (`special.txt` (2); every death with a bag >= 50 to a champion, followed through further kills): the killer's team
  banks the bag in **61-83%** of cases. The victim's team gets it back in 0-12%. The rest are still carried at the end, mostly on
  boss_battle, where the only altar is camp-gated. When the study team kills a big-bag carrier, it banks the bag 50-82% of the time.
  **A big-bag death is a transfer, not a loss.**

| team | S big-bag deaths / game (n) | banked by the killer's team | recovered and banked by S | carried at the end | S kills O big-bag carriers / game (n) | S banks them |
|---|---|---|---|---|---|---|
| pbg | 0.27 (31) | 61% | 10% | 29% | 0.51 (59) | 71% |
| ifish | 0.29 (32) | 69% | 0% | 25% | 0.44 (48) | 62% |
| Pantheon | 0.66 (69) | 61% | 12% | 26% | 0.41 (43) | 60% |
| coo | 0.63 (64) | 69% | 6% | 20% | 0.30 (30) | 50% |
| cm | 0.46 (49) | 80% | 8% | 10% | 0.48 (51) | 82% |
| Nyx | 0.46 (46) | 83% | 4% | 11% | 0.34 (34) | 76% |

- **Carrying is not what gets bodies killed.** Champion-kill deaths per 1,000 body-rounds, by bag (all 584 matches, 10-round steps):
  empty 2.09, 1-49 gems 1.45, 50-149 gems 1.02, 150-399 gems 0.82, 400+ gems 1.19. Carriers are the careful or strong bodies. Bag
  risk is the size of the swing when a carrier does die, not a higher death rate.

## 3. Banking

### 3.1 Cadence, bag sizes, altar choice, safety

| team | tribute starts / completed per game | first bank (median r) | bag median / mean / p90 | banked gems in bags >= 100 | altar nearest the last capture | last capture -> altar walk (median) | altar zone own / mid / enemy | ally within 4 at start | enemy within 6 during the channel | failed starts (causes) |
|---|---|---|---|---|---|---|---|---|---|---|
| pbg S | 17.6 / 16.3 | 121 | 30 / 51 / 90 | **40%** | 73% | 13 | 36 / 63 / 1% | 44% | 27% | 6% (own cancel 100, stun 14, lock 13, death 5) |
| pbg O | 22.1 / 21.2 | 104 | 22 / 33 / 67 | 16% | 77% | 12 | 39 / 60 / 2% | 41% | 26% | 4% |
| ifish S | **23.2 / 21.9** | 106 | 28 / 39 / 81 | 23% | 78% | **11** | 32 / 67 / 1% | **51%** | 26% | 5% (own cancel 61, stun 50, lock 8, death 7) |
| ifish O | 17.7 / 16.5 | 144 | 28 / 41 / 74 | 22% | 75% | 13 | 37 / 62 / 1% | 40% | 26% | 6% |
| Pantheon S | **27.7 / 26.8** | **80** | 21 / 28 / 44 | 22% | 74% | 12 | 42 / 56 / 2% | 41% | 23% | 3% |
| coo S | 21.2 / 20.1 | 123 | 28 / 36 / 73 | 14% | 78% | 13 | 35 / 62 / 2% | 42% | 29% | 5% (lock 40, stun 36) |
| cm S | 26.2 / 24.9 | 91 | 22 / 32 / 66 | 16% | **82%** | **10** | 31 / 66 / 3% | 38% | 26% | 4% (lock 56, stun 41, death 27; 0 own cancels) |
| Nyx S | 22.3 / 19.6 | 126 | 26 / 39 / 71 | 23% | 70% | 13 | 34 / 65 / 1% | 39% | 33% | 11% (own cancel 208) |

- **Everyone banks at the altar nearest the capture** (70-82% of completed tributes), 10-13 walking tiles from the capture, mostly at
  mid-band altars (56-67%). Those altars sit a median 22-26 walking tiles from the team's spawn.
- **Two styles**:
  - **Bank-often** (ifish, cm, Pantheon's non-Prism bodies): 22-27 completed tributes a game with ~20-30-gem bags. ifish banks a median
    121 by r300 against its opponents' 73, and its wins end at a median r969.
  - **Carry** (pbg, Nyx, Pantheon's Prism): pbg banks 40% of its gems in bags of 100 or more; a single Prism tribute often ends the
    game (section 4).
- **Tributes almost never fail**: 3-11% of the study teams' starts. The failure that matters is the big one (section 4).

### 3.2 The bank decision: after a capture, does the body start a tribute before its next capture?

Share of captures (bag > 0 afterwards) followed by a tribute start before the body's next capture, by bag after the capture
(rows) x walking distance from the capture spot to the nearest altar (columns). n is in brackets.

| bag | ifish S: altar 0-5 | 6-10 | 11-20 | 21+ | cm S: 0-5 | 6-10 | 11-20 | 21+ | pbg S: 0-5 | 6-10 | 11-20 | 21+ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1-19 | 71% (520) | 41% (302) | 32% (489) | 30% (286) | 98% (463) | 70% (464) | 48% (522) | 26% (447) | 60% (412) | 34% (272) | 37% (397) | 24% (240) |
| 20-39 | **81%** (414) | 56% (276) | 52% (417) | 40% (373) | 88% (244) | 60% (278) | 49% (405) | 16% (383) | 58% (282) | 43% (264) | 49% (376) | 44% (361) |
| 40-79 | 79% (166) | **70%** (122) | 56% (268) | 46% (304) | 96% (143) | 78% (115) | **90%** (228) | **91%** (232) | 56% (232) | 44% (143) | 43% (269) | 43% (290) |
| 80-149 | 82% (51) | 63% (19) | 70% (84) | 61% (127) | 100% (15) | 75% (4) | 80% (15) | 93% (28) | 47% (93) | 12% (67) | 34% (144) | 39% (135) |
| 150+ | 59% (27) | 58% (19) | 36% (58) | 73% (37) | 100% (13) | 100% (11) | 90% (10) | 85% (13) | **20%** (146) | **15%** (135) | **15%** (185) | 25% (137) |

- Median time from the capture to the tribute start is 8-16 rounds for bags under 80 (all teams), 13-28 rounds for bigger bags.
- **ifish's rule (INFERRED from the table)**:
  - bank a bag of >= 20 when an altar is within 5;
  - bank >= 40 within 10;
  - bank >= 80 at almost any distance.
- **cm** banks almost every bag of >= 40 at any distance.
- **pbg** does not bank its bags of 150+ (15-25%). Those are the Prism's bags.
- **Pantheon** is a split team: its non-Prism bodies bank 1-39-gem bags 55-84% of the time, but bags of 80+ only 1-22%.

### 3.3 Channel safety: when tributes are given up

| team | tribute starts | own cancels | enemy distance at the cancel (median / p90) | closest enemy in completed channels (median) | cancel rate if the closest enemy came within <= 4 | 5-6 | 7-8 | > 8 | cancels followed by a hit on a champion within 5 rounds |
|---|---|---|---|---|---|---|---|---|---|
| pbg S | 2,043 | 100 | **6** / 7 | 11 | 10% | **23%** | 3% | 0% | 49% |
| ifish S | 2,548 | 61 | 6 / 9 | 11 | 8% | 6% | 4% | 0% | 34% |
| Pantheon S | 2,904 | 24 | 4 / 7 | 12 | 7% | 1% | 0% | 0% | 71% |
| cm S | 2,776 | **0** | - | 12 | 0% | 0% | 0% | 0% | - |
| Nyx S | 2,227 | 208 | 5 / 7 | 10 | 36% | 25% | 1% | 0% | 43% |

- Completed channels had their closest enemy at a median 10-12 tiles. Nobody cancels with no enemy within 8.
- Bags of 20 or less take at most 2 turns and damage does not interrupt them, so the bank-often teams just finish. cm never cancels.
- **INFERRED**: the Prism teams cancel because the Prism is their fighter. Its basic attack reaches 3 and its spells 4, with a
  1.5x-Focus stun and an area spell; Focus grows 1.5 per carried gem.
- The Prism teams (pbg, Nyx) cancel when an enemy comes within ~6.

## 4. Finisher tributes and the Prism bag (special question 1)

### 4.1 prism best girl's Prism (116 games; Prism drafted in all 116)

| round | 100 | 200 | 300 | 400 | 500 | 600 | 800 | 1000 | 1200 |
|---|---|---|---|---|---|---|---|---|---|
| Prism bag median (games still running) | 0 | 8 | 22 | 33 | 37 | 48 | 81 | 94 | 90 |
| Prism bag p75 | 11 | 44 | 58 | 87 | 107 | 111 | 190 | 256 | 280 |

**Size and share.**
- Max bag per game: median **179**, p75 **469**, max 3,884 (boss_battle).
- The bag reaches 200 or more in 47% of games and 400 or more in 31%.
- The Prism takes 28% of the team's captured gems but banks only 17% of the team's gems.
- It completes 0.6 tributes a game (team: 16.3).
- **INFERRED**: the bag is a weapon. Prism gains 1.5 Focus per carried gem, so 400 gems = +600 Focus.

**When and where it banks (93 tribute episodes with a bag of 100 or more).**
- Start round: median **r1089**. Bag at the start: median 486.
- Altar: mid-band altar 78%, own 19%, enemy 2%. Altar walk from spawn: median 26.
- Escort: an ally within 4 at the start 55%, but in **every** round of the channel only 19%.

**It banks to finish.**
- **73% of its big tribute starts are finishers** (team banked + bag >= 1000; median banked + bag = 1,044).
- pbg makes 1.21 finisher starts a game (50% of games). Finisher bag median: 521.
- **73% of pbg's wins on gems end with a tribute of 100 gems or more.** The game-ending tribute bag: median 239.
- Example, `C:/battlecode/cache/t2/pbg/00quadrants_46848e89.repl26a`: the Prism starts a tribute with 796 gems at r401 (team banked 248).
  The channel takes 80 turns and nobody comes. It completes at r481 and ends the game 1,180-802 against :3.

**How its big tributes end (pbg Prism, bag of 100 or more; outcome by the closest enemy during the channel).**
- No enemy within 8: **done 23 / 25 (92%)**.
- Closest enemy 7-8: done 14 / 22.
- Closest enemy 5-6: **cancel 49**, done 7, stun 1, death 1 (58 starts).
- Closest enemy 4 or less: cancel 15, stun 5, lock 5, done 5, death 2.
- Enemy distance at the moment of the cancel: 6 (30 times), 7 (19), 5 (10), 4 or less (9).
- **INFERRED rule: the Prism aborts a big tribute when an enemy comes within ~6-7 and turns to fight** (49% of pbg cancels are followed
  by a hit on a champion within 5 rounds).
- Example, `C:/battlecode/cache/t2/pbg/01gold_rush_2376a4f9.repl26a`:
  - The Prism (3,460 max HP, 521 gems) starts at (21,15) at r1273. Pantheon's Vesper and HoR walk to 6 tiles and the Prism cancels at
    r1290. Its HoR banks 165 elsewhere at r1289.
  - Ten restarts follow (r1309-r1520): nine end in an own cancel, one (r1334) in a Pantheon lock.
  - The Prism never banks its 521-532 gems. pbg wins 1,007-308 at r1582 through its other bodies' banks.

**What opponents do to it.**
- Over 138 big-bag Prism starts, opponents stunned it 6 times, locked it 5 and killed it 3.
- They place **2.16 altar locks a game against pbg, but only 5% of those locks cancel a pbg tribute.** pbg itself places **0** locks in
  116 games.

**Deaths with the bag.**
- 178 Prism deaths (1.53 a game), 53 gems lost a game.
- **16 deaths with 100 or more gems (0.14 a game, 4,267 gems).** Only 3 of them happened during a tribute.
- Killers: **camps 7** (it fights heavy camps with the bag), Marcella 5, Vesper 3, HoR 1.
- Bags of 50 or more lost to champions: the enemy banked 15 (1,756 gems), pbg recovered 3 (855).
- Examples:
  - `t2/pbg/00gem_fields_3fc2330b.repl26a`, the full chain:
    - the Prism starts 704 gems at the enemy-side altar (32,10) at r483;
    - Pantheon's Vesper kills it at r517 and inherits 711;
    - the Vesper's own tribute is stunned at r558, and it is killed at r560;
    - pbg's Marcella then carries 747 and banks it r606-681 (75 turns: she is stun-immune), and pbg wins.
  - `t2/pbg/00great_wall_3a46ed8d.repl26a`:
    - the Prism's 623-bag tribute is cancelled (r988), stunned (r1069) and then ends in death (r1104, to a camp);
    - pbg loses.

**Games by Prism bag** (association only: winning teams collect more): max bag of 300 or more: 31/39 won; 100-299: 16/23; under 100:
15/39; lost a bag of 100 or more: 9/15.

### 4.2 Every Prism in the data (the bag style is shared by Pantheon and Nyx)

| team | Prism games | max bag median / p75 | share of team captured / banked gems | deaths / game | big-bag deaths / game | Prism gems lost / game | big-bag killers |
|---|---|---|---|---|---|---|---|
| pbg S | 116 | 179 / 469 | 28% / 17% | 1.53 | 0.14 | 53 | camp 7, Marcella 5, Vesper 3 |
| Pantheon S | 105 | 200 / 339 | 29% / 13% | 1.32 | **0.31** | **132** | **Marcella 11, Vesper 10, HoR 6**, camp 3 |
| Nyx S | 100 | 139 / 222 | 20% / 11% | 1.98 | 0.24 | 73 | Marcella 8, Vesper 4, camp 4, HoR 3 |
| opponents' Prisms (ifish O / pbg O / Pantheon O) | 49 / 38 / 36 | 204 / 142 / 205 | 26-29% / 12-19% | 1.74-1.92 | 0.14-0.20 | 59-106 | Vesper, HoR, Marcella |

- Pantheon's Prism dies with 300 or more gems in 11 games. Examples: `t2/pantheon/00gemfight_a59c04f3` r1038 (611 gems, Marcella),
  `00swirl_5cd065e4` r911 (685, Vesper), `00collision_12104416` r1223 (504, Vendetta), `00elkring_429899a3` r664 (440, Marcella). 7
  of the 11 are losses.

### 4.3 Finisher tributes of every team

| team | finisher starts / game (games with one) | bag median | done | own cancel | stunned | locked | killed | game-ending tribute bag (median) | wins ended by a bag >= 100 |
|---|---|---|---|---|---|---|---|---|---|
| pbg S | **1.21** (50%) | **521** | 36% | 51% | 3% | 2% | 1% | **239** | **73%** |
| Nyx S | 1.08 (38%) | 260 | 33% | 55% | 1% | 2% | 1% | 190 | 67% |
| ifish S | 0.89 (55%) | 99 | 57% | 27% | 7% | 1% | 1% | 56 | 23% |
| Pantheon S | 0.61 (40%) | 44 | 59% | 0% | 8% | 3% | 14% | 37 | 33% |
| cm S | 0.58 (51%) | 71 | 84% | 0% | 3% | 2% | 0% | 71 | 25% |
| coo S | 0.52 (44%) | 44 | 83% | 8% | 4% | 2% | 0% | 36 | 12% |

## 5. Intercontinental Fish's Vesper carry (special question 2), against every Vesper in the data

| team | Vesper games | share of team gold | Vesper gold / game | share of capture / kill gold | captures taken | gems taken | solo captures | its gems by class | by zone | tributes / game | bag median | rounds between banks | deaths / game | gems lost / game |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **ifish S** | 110 | **46%** | **3,743** | 46% / 47% | 37% | **43%** | 90% | elk 61%, **monolith 19%**, wolf 14% | **mid 64%**, own 34% | 7.0 | 36 | 82 | 1.74 | **105** |
| ifish O | 105 | 35% | 2,507 | 37% / 32% | 30% | 30% | 91% | elk 69%, wolf 20% | own 49%, mid 48% | 5.0 | 36 | 102 | 1.88 | 64 |
| pbg S | 109 | 38% | 2,919 | 40% / 39% | 35% | 30% | 87% | elk 70%, wolf 17%, monolith 9% | mid 54% | 5.8 | 36 | 95 | 1.28 | 33 |
| Nyx S | 100 | 39% | 2,899 | 43% / 25% | 30% | 43% | 95% | elk 63%, wolf 23% | mid 52% | 9.1 | 29 | 69 | 1.02 | 23 |
| Pantheon S | 105 | 31% | 1,993 | 32% / 31% | 22% | 23% | 95% | elk 65%, wolf 21% | mid 59% | 8.5 | 21 | 74 | 1.27 | 62 |
| coo S / cm S | 92 / 106 | 35% / 26% | 2,322 / 2,066 | 34% / 35% ; 27% / 22% | 32% / 22% | 29% / 24% | 87% / 98% | | | 6.0 / 5.7 | 29 / 22 | 75 / 99 | 3.03 / 2.89 | 60 / 19 |

**Share of ifish's captures taken by its Vesper, by round window** (`special.txt` 3b):

| round window | elk | wolf | gold clusters | gem clusters | golem | monolith |
|---|---|---|---|---|---|---|
| r0-200 | 51% | 46% | 30% | 24% | 5 / 5 | - |
| r200-500 | 48% | 44% | 19% | 22% | 40% | 1 / 1 |
| r500-1000 | 40% | 43% | 11% | 14% | 50% | **26 / 34 (76%)** |
| r1000+ | 45% | 33% | 15% | 17% | 2 / 2 | 7 / 12 |

**Captures: the Vesper takes the gold-heavy rewards alone.**
- It takes the gold-heavy rewards (elk 90 gold each, golem 160, monolith 300) and leaves gold clusters and gem clusters to the others.
- 90% of its captures are solo, so the reward is not split.
- With its +33% gold (+53% with Treasure) it earns **46% of ifish's gold**: 1.3-1.9x the gold of every other Vesper in the data
  (2,000-2,900 a game).
- Example, `C:/battlecode/cache/t2/ifish/00contest_16309139.repl26a`: ifish (vs procless) takes the 200-gem monolith six times. Its
  Vesper captures five of them (r511, r644, r749, r841, r971; 200 gems + 459 gold each); Vendetta takes r1034 (360 gold).

**Banking cadence.**
- Its banks come every ~82 rounds with 36-gem bags (7 tributes a game). This is ifish's bank-often style; the Vesper is not a holder.
- Example, `t2/ifish/00interlock_c440041c.repl26a` (ifish beat Univardisty 1,001-356): the Vesper earns 73% of the team's gold. It banks
  12 times between r170 and r1174 (bags of 15-100, 37-191 rounds apart); its 15-gem bank at r1174 ends the game.

**Cost.**
- The carry is exposed: it dies 1.74 times a game and loses **105 gems a game**, the most of any Vesper.
- 13 of ifish's 18 big-bag deaths are its Vesper.

## 6. Farming cycles, idle groups and the respawning middle

### 6.1 Cycle phases (captured groups, respawn cycles only; medians in rounds: wait / kill / capture)

| team | own zone | mid | enemy zone | mid captures the enemy also hit / hit first |
|---|---|---|---|---|
| pbg S / O | 22 / 13 / 7 ; 23 / 8 / 7 | **17** / 13 / 7 ; 23 / 9 / 7 | 15 / 10 / 8 ; 27 / 11 / 7 | 20% / 13% ; 15% / 11% |
| ifish S / O | 24 / 10 / 7 ; 24 / 10 / 7 | **20** / 10 / 7 ; 26 / 9 / 7 | 10 / 6 / 8 ; 23 / 10 / 7 | 17% / 11% ; 15% / 9% |
| Pantheon S / O | 26 / 8 / 8 ; 22 / 9 / 7 | 20 / 9 / 8 ; 23 / 10 / 7 | 14 / 6 / 7 ; 30 / 9 / 7 | 16% / 11% ; 20% / 15% |
| coo S / O | 28 / 10 / 7 ; 22 / 8 / 7 | 28 / 13 / 7 ; 23 / 8 / 7 | | 18% / 12% |
| cm S / O | 23 / 8 / 7 ; 21 / 8 / 7 | 23 / 9 / 7 ; 23 / 11 / 7 | | 16% / 11% ; 26% / 18% |
| Nyx S / O | 20 / 8 / 7 ; 26 / 11 / 7 | 23 / 8 / 7 ; 23 / 14 / 7 | | 16% / 11% ; 28% / 20% |

- Kill time (8-13 rounds) and capture time (7 rounds = the 5-round timer + 2 steps) are the same for everyone.
- The difference is the **wait before the first hit on a respawned middle group**: pbg 17 and ifish 20 rounds against 23-26 for their
  opponents.
- Only 15-28% of middle captures are contested (the enemy also hit the group).

**Idle groups.**
- Groups stand full and untouched 44-55% of the game in each team's own zone and 54-61% in the middle (weighted by gem rate).
- Idle share does not separate the teams: every team leaves about half the map's capacity idle. The gap is which groups are taken.

### 6.2 Who re-takes a respawning middle group (15,091 consecutive cycles, all 584 matches)

| bodies within 4 at the respawn round | cycles | previous capturer takes it again | re-hit wait after respawn (median / p25) |
|---|---|---|---|
| capturer only | 3,548 | **86%** | **10 / 3** |
| both teams | 1,593 | 68% | 8 / 3 |
| other team only | 1,470 | **52%** | 14 / 5 |
| nobody | 8,480 | 79% | **37 / 15** |

- Retention by the capturer's holders at the respawn round: 0 -> 75%, 1 -> 78%, 2 -> 81%, 3+ -> 88%.
- Per team, when only S holds, S takes the next cycle 65-83%; when only O holds, 16-38%.
- **Middle groups are sticky** (79% stay with the last capturer even when nobody waits). **Holding buys tempo**: the group is re-hit in
  10 rounds instead of 37. On an elk group that is ~87 instead of ~114 rounds per cycle (60 respawn + wait + ~10 kill + 7 capture),
  ~30% more throughput. An enemy holder makes a group a coin flip (52%).
- **How they hold** (`econ_hold.py`; held cycles of the study teams, 349-690 per team, 1.45-1.88 holder bodies per cycle):
  - holders stand at a median distance of 4 tiles and almost never on the group's tiles (1-2%), since an occupied tile delays the
    respawn;
  - in the last 20 rounds before the respawn they are away (> 6 tiles) 23-32% of the rounds, moving 29-36%, hitting another camp
    14-17%, standing still 13-23% and fighting 4-6%;
  - the re-hit comes a median 7 (pbg, Nyx) to 13 (cm) rounds after the respawn.
- **INFERRED**: a timed return (work a neighbouring group, come back for the respawn), not camping.
- Example, `C:/battlecode/cache/t2/ifish/00ambush_136e5ed5.repl26a` (ifish = team B): the 51-gem middle elk group (respawn 60) is
  taken by ifish six times in a row (r228, 379, 541, 633, 757, 840).
  - While nobody holds it, the re-hits come 63 and 76 rounds after the respawn (r288 -> 351, r439 -> 515).
  - Once a body holds it (r601, 693, 817), the re-hit comes 1 round after the respawn: r601 -> 602, r693 -> 694, r817 -> 818. At r601,
    ifish's Cassi walked in at r600 to (40,60), 4 tiles from the group at (42-45, 64-65), and hit it at r602.

## 7. Walking budget

| team | dead % | walk % | farm % | fight % | on a camp tile % | still off-camp % | walk steps per captured gem |
|---|---|---|---|---|---|---|---|
| pbg S / O | **8.1** / 11.3 | 53.3 / 49.1 | 18.1 / 17.3 | 3.1 / 2.7 | 7.3 / 7.5 | 8.7 / 10.9 | **2.90** / 3.34 |
| ifish S / O | 10.9 / 12.2 | 51.0 / 47.3 | 18.5 / 18.4 | 2.6 / 3.0 | 6.3 / 6.5 | 9.4 / 11.2 | 3.24 / 3.02 |
| Pantheon S / O | **6.6** / 11.4 | 53.7 / 50.4 | 17.1 / 17.3 | 3.0 / 2.2 | 6.5 / 6.3 | 12.0 / 11.1 | 3.19 / 3.28 |
| coo S / O | 14.2 / 7.9 | 42.5 / 52.3 | 15.2 / 16.4 | 2.9 / 3.0 | 7.0 / 6.6 | 17.0 / 12.6 | 2.80 / 3.71 |
| cm S / O | 13.2 / 11.6 | 46.0 / 50.8 | 17.4 / 15.0 | 3.4 / 3.7 | 6.7 / 6.3 | 12.3 / 11.2 | 2.98 / 3.60 |
| Nyx S / O | 8.4 / 9.8 | 50.0 / 51.3 | 16.1 / 15.6 | 3.5 / 3.0 | 8.3 / 6.3 | 12.2 / 12.7 | 3.34 / 3.64 |

- Every team walks about half of its body-time. The best teams do not walk less; they walk to better groups (pbg: 2.9 steps per
  captured gem) and are dead less.

## 8. Objectives: golems, monoliths, elk

### 8.1 Per team (on maps that have the camp class)

| team | class (games) | attempts / game | bodies per attempt / per won attempt | won | captures / game | first capture (median r) | games with a capture | won attempts: first hit -> capture, hitters |
|---|---|---|---|---|---|---|---|---|
| pbg S / O | golem (17) | 5.6 / 2.5 | 2.54 / **3.53** ; 2.12 / 2.87 | 47% / 36% | **2.6** / 0.9 | **143** / 308 | 53% / 35% | 31 rounds, 4 hitters |
| ifish S / O | golem (16) | 3.8 / 2.5 | 3.56 / **4.56** ; 2.33 / 2.86 | 56% / 55% | **2.1** / 1.4 | **202** / 303 | 62% / 50% | 35 rounds, 5 hitters |
| pbg S / O | monolith (47) | 3.6 / 0.9 | 2.07 / 3.16 ; 2.09 / 3.17 | 34% / 27% | **1.3** / 0.3 | 834 / 698 | **60%** / 15% | 57 rounds, 3 hitters |
| ifish S / O | monolith (46) | 3.2 / 1.3 | 2.07 / 3.52 ; 1.98 / 3.00 | 32% / 28% | **1.0** / 0.3 | 755 / 990 | **50%** / 15% | 44 rounds, 3 hitters |
| pbg S / O | elk (107) | 24.2 / 22.4 | **2.52** / 2.84 ; 2.07 / 2.30 | 74% / 71% | 18.2 / 16.1 | 55 / 68 | 96% / 91% | |
| ifish S / O | elk (103) | 23.8 / 22.0 | **2.86** / 3.23 ; 2.07 / 2.31 | 76% / 71% | 18.2 / 15.8 | **46** / 65 | 97% / 94% | |

- The other four teams (`agg.txt`): Pantheon 0.3, coo 0.3, cm 0.9, Nyx 0.4 monoliths a game. Golems: cm 2.5 a game with 2.2 hitters;
  the others 0.9-1.6. Elk attempts: 1.8-1.9 hitters.
- pbg and ifish attack elk groups with 2.5-2.9 bodies against 2.07 for their opponents.
- pbg also takes golems in the **enemy** zone (7 of its 45 won golem attempts).
- Golem openings with five bodies:
  - `t2/pbg/00split_c5346c81` r23 -> r89 and `00split_35ad7d10` r23 -> r91 (own-zone golem);
  - `t2/pbg/00quadrants_46848e89` r67 -> r111 (mid golem).

### 8.2 What makes an attempt succeed (all 584 matches, pooled)

| class | 1 hitter | 2 | 3 | 4 | 5+ |
|---|---|---|---|---|---|
| golem | 16% (192) | 56% (139) | **73%** (96) | **85%** (62) | 90% (71) |
| monolith | 7% (441) | 33% (194) | **65%** (143) | 65% (65) | 75% (60) |
| elk group | 53% (9,555) | **80%** (6,863) | 87% (4,332) | 91% (2,007) | 94% (1,350) |

| class | result | attempts | hitters | alive bodies own - enemy | max-HP ratio own / enemy (median) | enemy within 8 at the start | start round (median) |
|---|---|---|---|---|---|---|---|
| golem | won | 296 | 3.19 | +0.31 | 1.12 | **15%** | 520 |
| golem | not taken | 245 | 1.65 | +0.23 | 1.05 | **41%** | 411 |
| golem | stolen | 19 | 1.53 | 0.00 | 1.09 | 84% | 398 |
| monolith | won | 277 | 3.04 | **+0.82** | **1.46** | 48% | 964 |
| monolith | not taken | 558 | 1.49 | +0.23 | 1.02 | 55% | 724 |
| monolith | stolen | 68 | 2.31 | +0.16 | 0.93 | 84% | 1,031 |

- **Golem**: committed bodies and no enemy nearby at the start.
- **Monolith**: committed bodies and an item / numbers advantage (alive max-HP sum ~1.4x the enemy's).
- Most failed monolith attempts are one-body pokes (441 attempts at 7%), which is wasted body-time.

## 9. Altar locks

| team | locks placed / game S / O | S locks that cancelled a channel | O locks that cancelled an S channel | S tributes lost to locks / game |
|---|---|---|---|---|
| pbg | **0.00** / 2.16 | - | 5% | 0.11 |
| ifish | 2.87 / 1.31 | 4% | 6% | 0.07 |
| Pantheon | 4.22 / 1.80 | 3% | 8% | 0.14 |
| coo | 1.13 / 2.76 | 19% | 14% | 0.40 |
| cm | 5.56 / 3.58 | 2% | 15% | 0.53 |
| Nyx | 0.03 / 1.90 | 3 of 3 | 9% | 0.17 |

- Locks do not separate winners and losers (2.3 vs 2.3 a game, P 0.52). 81-98% of locks are placed pre-emptively, and pre-emptive
  locks do nothing measurable.
- A lock placed on an altar while an enemy is channelling there cancels the channel by rule. That is the only use with a measured effect
  (coo: 19% of its locks).

## 10. Weak spots to exploit (per team; MEASURED unless marked)

- **prism best girl**:
  - **The Prism holds the game's gems.** Max bag: median 179, p75 469.
  - Its finishers start late (median r1089) with nobody guarding the whole channel (19%), and it **aborts when anyone comes within ~6**
    (cancel rate 84% when an enemy came within 5-6; 0% and 92% done when no enemy came within 8).
  - It dies with 100 or more gems 0.14 times a game, 7 of 16 times to camps while fighting heavy camps with the bag.
  - pbg never places altar locks, so our channels are only threatened by its stuns and kills.
  - Against ifish's bank-often tempo pbg is 10-9. In all 9 of its losses ifish completed more tributes (median 25 vs 9; e.g.
    `t2/pbg/01concentrated_wealth_83e86a76` 36 vs 9, `00packs_6e6a3d0d` 26 vs 9, `00rushbait_v2_08bc9833` 20 vs 8). In 9 of its
    10 wins pbg completed more.
- **Intercontinental Fish**:
  - Banks small and often, so denying its tributes gains little (median bag 28).
  - Its economy is the Vesper: **46% of the gold**, 76% of its monolith rewards.
  - The Vesper dies 1.74 times a game and loses 105 gems a game. ifish is also the most death-prone top team (12.2 deaths a game, more
    than its opponents' 10.9).
- **Pantheon**:
  - **Prism big-bag deaths 0.31 a game** (33 in 105; Marcella 11 and Vesper 10 as killers); 132 Prism gems lost a game.
  - Its non-Prism bodies bank tiny bags (median 21) very often. Pantheon earns no more gold than its opponents (599 vs 613 per 100
    rounds).
- **Nyx**: the pbg-like Prism style (finisher bag median 260, 55% own cancels; big-bag Prism deaths 0.24 a game).
- **coo**: dies 13.3 times a game (opponents 8.1), earns 516 gold per 100 rounds (opponents 634), and loses 0.40 tributes a game to
  locks.
- **Claudus Maximus**: banks everything at once (0 own cancels, 25 tributes a game). It loses 0.53 tributes a game to locks, the most:
  a lock on its next altar works. Its elk attempts use only 1.8 hitters.

## Rules for god2

All rules use runtime state only:
- groups from the camp list, with gem / gold value, `max_respawn_timer`, and state / timer when in vision;
- walking distances to both spawns (zone f);
- visible enemies' `gem_count()`, `is_submitting_gems()` and items;
- `global_submitted_gems()` for both teams;
- altar positions and `has_altar_lock()`.

The thresholds are the measured ones; tune them on the ladder.

1. **Middle tempo: timed return to respawning middle groups.**
   - When our team captures a group with 0.4 <= f <= 0.6, store `respawn_at = capture_round + max_respawn_timer`.
   - From `respawn_at - 20`, the nearest healthy non-carrier (hp >= 50%, bag < 100) works any group within 6 of it, then stands within 4
     of the group (never on its tiles) by `respawn_at - 2`.
   - It hits the group the round it is alive, unless a stronger enemy is within 8 (stronger = higher max-HP sum within 8).
   - Do the same for a middle group the enemy just took when our local max-HP sum within 8 >= theirs. An enemy-only holder keeps the
     group just 52% of the time.
   - Target: re-hit within 10 rounds of the respawn (holders: median 10; nobody: 37).
2. **Bank-often for every body except a Prism.** Right after a capture, go to the altar nearest the capture spot (walking distance) and
   start a tribute when:
   - **bag >= 20 and altar <= 5**, or **bag >= 40 and altar <= 10**, or **bag >= 80 at any distance** (ifish 61-82%, cm 75-100%);
   - also bank at the end of every capture chain when no reachable group is ready within ~10 rounds.
   - Evidence: tributes completed W 26.5 vs L 15.1 (P 0.82); banked by r300 W 112 vs L 76; ifish 121 vs 73.
3. **Channel safety.**
   - Start a tribute of more than 2 turns (bag > 20) only when no enemy is within 7. Completed channels had their closest enemy at a median
     10-12 tiles.
   - Bags of 20 or less: start and finish regardless of nearby enemies (2 turns at most; damage does not interrupt).
   - During a long channel, if an enemy comes within 6 and our max-HP sum within 6 is lower than theirs, cancel and act (fight or leave).
     Otherwise keep channelling.
   - Prefer **Marcella** as the big-bag banker: she is stun-immune, so only a death or a new lock stops her. pbg's Marcella completed a
     747-gem, 75-turn tribute.
4. **Enemy bag watch: kill or stop the big bags.**
   - Per visible enemy, track `gem_count()` and whether it is channelling.
   - **Bag >= 100**: priority kill target when our local max-HP sum >= theirs. The killer's team banks 61-83% of such bags, and the victim's
     team recovers only 0-12%.
   - **Finisher alarm**: when `global_submitted_gems(enemy)` + a channelling enemy's bag >= 1000, the game ends in ceil(bag / 10) turns.
     Every body that can arrive in time converges:
     - the first body to arrive stands within 6 of the carrier: pbg's and Nyx's Prisms cancel 84% / 88% of big tributes with an enemy at
       5-6;
     - a stun or a **new altar lock on that altar** cancels the channel outright; carry one lock (10 gold) on two roaming bodies for this;
     - kill it if the fight is even or better.
   - pbg makes 1.21 finisher starts a game and 73% of its wins end that way.
   - Low-cost version: whenever a visible enemy with bag >= 100 is channelling, keep one body at 6 tiles from it. Prism's basic attack
     reaches 3 and its spells 4 (5 with the radius-1 area spell), and casting excludes walking, so 6 is outside its reach that turn.
5. **Heavy objectives with enough bodies.**
   - **Golem**: start only with >= 3 committed hitters (success 73%; 4 -> 85%; 5+ -> 90%; 1 -> 16%) and no enemy within 8 of the golem
     (won attempts 15% vs failed 41%).
   - On maps with an own or mid golem, open on it with 4-5 bodies. pbg does this at r23 (split) and r67 (quadrants) with 5 bodies. First
     golem: pbg r143, ifish r202, their opponents r303-308.
   - **Monolith**: start only with >= 3 hitters (65% vs 33% with 2, 7% solo) and when our alive max-HP sum >= ~1.4x the enemy's, or we
     have more bodies alive (won attempts: median ratio 1.46, +0.82 bodies). Typically after r700 (won median r964).
   - No solo pokes on golems or monoliths.
   - Never hit a golem or monolith with a body carrying >= 100 gems: camps killed pbg's Prism 7 times with big bags. Bank first or hand
     the hits to others.
6. **Carry routing.** The gold-bonus body (Vesper: +33%, +53% with a Treasure emblem) captures the gold-heavy rewards alone (monolith
   300, golem 160, elk groups 90 per elk):
   - when a group is dead and the Vesper is alive within 4 of it, the other bodies leave its tiles (rewards are split among allies
     present) and go for the next group;
   - other bodies take gold and gem clusters.
   - Evidence: ifish's Vesper earns 46% of the team's gold (3,743 a game vs 2,507 for its opponents' Vespers), takes 76% of the monolith
     rewards in r500-1000, 90% solo.
   - Pair it with rule 4 defensively: our carry is the enemy's best target too (ifish's Vesper loses 105 gems a game).
7. **Take elk groups with 2-3 bodies; skip the far small groups.**
   - Elk-group attempts succeed 53% with 1 hitter, 80% with 2, 87% with 3.
   - pbg and ifish use 2.5-2.9 hitters (opponents 2.1) and take their first elk at r46-55 (opponents r65-68).
   - Value groups by gems + gold per body-round including the walk. 120-HP gem and gold clusters far from the current position lose to
     elk groups (W elk gems 645 vs L 379, P 0.80; gold-cluster captures P 0.54).
8. **If we draft Prism: a bounded holder, not pbg's unbounded one.**
   - Let it keep its bag (1.5 Focus per gem) while it fights near allies.
   - It banks as a **finisher** (banked + bag >= 1000) only with no enemy within 8 (done 92% in that case).
   - Untested proposal: otherwise it banks at a mid / own altar when the bag >= ~250 and no enemy is within 8. pbg's Prism rarely banks
     below finisher size: 0.6 completed tributes a game, 17% of the team's banked gems.
   - It never fights heavy camps while carrying >= 100.
   - Untested proposal: it stays within 4 of an ally whenever the bag is >= 200.
   - Pantheon's Prism dies with 100 or more gems 0.31 times a game and loses 132 gems a game (killers: Marcella, Vesper); pbg's
     Prism 0.14 and 53.
9. **Locks: reactive only.** Pre-emptive locks show no effect (W 2.3 vs L 2.3, P 0.52; 2-19% cancel anything). Spend the 10 gold for a
   lock to cancel a channelling enemy bag (rule 4), or to block the next altar of a team that banks every capture (cm-type: 0.53
   tributes a game lost to locks).
10. **Measure the economy by volume, not first events.** Gates and A/B readouts for god2 should be: gold by r300 (W 1,506 vs L 1,155),
    middle gems (W 617 vs L 281), tributes completed (W 26.5 vs L 15.1) and deaths (W 6.2 vs L 13.8). First capture, first mid capture
    and first bank do not separate winners from losers (P 0.42-0.48).

**Caveats.**
- These are correlations from ladder replays. Winners also fight better, so mid gems and tributes are partly outcomes.
- The rules above are mechanisms the top teams use, with thresholds read off their behaviour; each needs a ladder A/B.
- The "INFERRED" readings (Prism focus as the reason for carrying, distance-6 abort, timed return) are interpretations of measured
  patterns, not of their code.
- Per-team samples are 100-116 games.
- Monolith / golem rows rest on 14-47 games with those camps per team.
