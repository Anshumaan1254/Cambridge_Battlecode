# How the CAMBC 2026a top 30 lose, and a counter for each

Data used (all local, nothing run on the engine):
- 6,795 ranked matches of 45 teams on the 86-map pool, engine 2.0.0, played 2026-11-02 17:20 to 2026-11-03 06:30 UTC (each top-30 team's last 400). Source: `experiments/top30_nov3/matches_current.jsonl`.
- 999 of the 1,201 decoded top-30 vs top-30 replays. All 83-91 decoded games of every top-10 team are included. Ranks 11-30 are partial: 293 games for ranks 11-20 and 106 for ranks 21-30 against teams outside their own cluster.
- Scripts and outputs are in `experiments/deep_research_nov3/counters/`: `h2h.py`, `dec_extract.py`, `losses.py`, `draft_fam.py`, `fingerprint.py` and `out/`.

Definitions:
- **BT** is a Bradley-Terry rating fitted on the 6,795 games and put on the ladder scale. **E** is the BT-expected number of wins; resid = W - E.
- **Decisive round**: the first round from which the loser stays 150 or more gems behind on banked+carried gems until the end. "close" means the game never reached that gap.
- **Fight swing**: the team lost at least 2 more champions than the opponent in the 150 rounds before the decisive round.
- **Kills** count enemy champion deaths credited to a champion, not to camps.
- Bags at death and in cancelled tributes are capped at 300 gems, because boss maps produce 1,000+ gem bags.
- **raids** and **cyc** (contested big-group respawn cycles, 30+ gems) come from another agent's objectives extraction, `objectives/out/games_top.jsonl`. It covers only about 300 of the games, so those numbers are a subset.

## 1. What do head-to-head results among the top 30 show (win matrix, Elo residuals, cycles, maps, sides, drafts)?

### Takeaway
- The top 5 (Mite, Intercontinental Fish, Univardisty of Shingtonwash, Ad Astra, newer team) are a tight cluster, BT 2489-2555, and each has one opponent that beats it well above expectation:
  - Ad Astra beats Mite.
  - Univardisty of Shingtonwash beats Intercontinental Fish.
  - NEETCoders beats Univardisty of Shingtonwash.
  - Sponge beats Ad Astra.
  - Intercontinental Fish beats newer team.
- The largest effects that hold up statistically are map-class weaknesses (n ≥ 60), one side effect (test4 on side a) and a draft-family effect: Willow rosters beat the standard Marcella/Vesper/Vendetta/Ryth/HoR roster.

### Cited Findings
**Strength and schedule**
- Ladder vs BT rating and record over 400 games:

  | Team | Ladder | BT | Record |
  |---|---|---|---|
  | Mite | 2583 | 2555 | 254/400 |
  | Intercontinental Fish (IC) | 2562 | 2548 | 251/400 |
  | Univardisty of Shingtonwash (UoS) | 2524 | 2496 | 223/400 |
  | Ad Astra (AdA) | 2516 | 2489 | 219/400 |
  | newer team | 2481 | 2495 | 220/400 |
  | NEETCoders (NEET) | 2443 | 2423 | 192/400 |
  | BattleCats | 2381 | 2343 | 200/400 |
  | test4 | 2366 | 2380 | 174/400 |
  | print dont int (pdi) | 2366 | 2343 | 180/400 |
  | Sponge(Albert and Bob) | 2362 | 2356 | 181/400 |

  Mite played 385 of its 400 games against other top-10 teams (240 wins) — [h2h.txt §1](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/h2h.txt)

**Nemesis pairs**: teams that beat a top-10 team above BT expectation (W/N, E):
- Mite: Ad Astra 34/65 (E 26.3, +7.7); NEET 15/40 (+2.2).
- IC: UoS 34/60 (E 25.5, +8.5); AdA 25/55 (+2.2).
- UoS: NEET 25/50 (E 19.9, +5.1); BattleCats 8/15 (+3.6); T1 7/15 (+2.6).
- AdA: Sponge 19/40 (E 12.7, +6.3); NEET 20/40 (+3.7).
- newer team: IC 41/60 (E 34.5, +6.5); AdA 31/55 (+4.0); UoS 31/55 (+3.4).
- NEET: newer team 35/45 (E 27.1, +7.9); pdi 14/25 (+4.4).
- BattleCats: Trzy Kwaterki 21/35 (+4.6); T1 18/30 (+3.1); Mite 10/10.
- test4: Mite 37/45 (+4.0); UoS 36/50 (+3.0).
- pdi: IC 18/20 (+2.7); Mite 14/15 (+2.4).
- Sponge: BattleCats 16/20 (E 9.6, +6.4); policy wonk 12/20 (+3.3).
- Source: [h2h.txt §5](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/h2h.txt)

**Largest negative pair residuals** among the top 30 (n ≥ 6):
- Sponge vs BattleCats 4/20 (E 10.4, z -2.86).
- NEET vs newer team 10/45 (E 17.9, z -2.41).
- IC vs UoS 26/60 (E 34.5, z -2.21).
- AdA vs Sponge 21/40 (E 27.3, z -2.13).
- Mite vs AdA 31/65 (E 38.7, z -1.93).
- Source: [h2h.txt §3](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/h2h.txt)

**Non-transitive triples** (each edge ≥ 60% wins, n ≥ 5): 29 cycles in 151 dominance edges. Only one involves two top-10 teams: Sponge > Supaswag (3/5) > BattleCats (4/5) > Sponge (16/20). At the very top the structure is near-transitive with pairwise splits of 45-60% — [h2h.txt §4](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/h2h.txt)

**Map-class residuals (n ≥ 60):**
- UoS:
  - Weak: maps with 3+ altars 68/164 (E 92.4, -24.4); 15+ camp groups 107/243 (E 135.5, -28.5); gold-rich 143/291 (E 160.6).
  - Strong: ≤ 8 groups 31/31 (E 17.5); 1 altar 65/91 (E 52.1).
- pdi: far spawns (≥ 90 tiles apart) 14/74 (E 32.8, -18.8); near spawns 93/171 (E 77.1, +15.9).
- Trzy Kwaterki: 4v4 maps 26/95 (E 44.5, -18.5); near spawns 72/189 (E 90.5); 5v5 133/229 (E 111.3, +21.7).
- :3: near spawns 76/192 (E 103.0, -27.0); far spawns 55/72 (E 38.0).
- prism best girl: 15+ groups 93/246 (E 117.4); 3v3 20/71 (E 33.7).
- German Empire: 5v5 90/238 (E 109.4, -19.4).
- JukeFall: 9-14 groups 49/143 (E 70.5, -21.5).
- IC: far spawns 30/65 (E 40.6, -10.6).
- Mite: 9-14 groups 71/127 (E 80.9, -9.9); gold-poor 55/99 (E 62.7).
- Source: [h2h.txt §7](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/h2h.txt)

**Worst single maps per top-10 team** (W/N vs E):
- Mite: 00rows 1/8 (4.7), 02arena 0/5 (2.8), 02cuts 1/5 (3.2), 02fields 3/8 (5.2), 00quarry 2/6, 01islands 3/8.
- IC: 03ultrastarvation 1/10 (5.9), 01concentrated_wealth 1/8 (5.0), 00reverse_spiral 1/7, 01the_farm 2/7, 01fracture 2/7.
- UoS: 00lanes 0/10 (5.8), 01gold_rush 1/10 (5.5), 03riverbed 0/7, 03the_front 0/6, 00great_wall 1/8, 03homonoliths 0/6.
- AdA: 00split 0/7 (3.8), 01islands 1/8 (4.4), 00the_line 2/10 (5.3), 02tangle 0/5, 03twisty 0/5.
- newer team: 00contest 0/7 (3.7), 00collision 1/9 (4.6), 00quarry 1/6, 00anvil 0/5.
- NEET: adgato_gemcombat3/2/5 0/5, 0/4, 0/5; 00crater 1/7; 00lost_world 0/5.
- BattleCats: 00eight 1/7, 01elk_arena 1/6, 02fields 1/7, 01broken_curve 1/7.
- test4: 01shortcut 0/5, 01yellow_brick_road 0/6, 02arena 0/5, adgato_gemcombat5 0/6.
- pdi: 01shortcut 1/10 (4.4), 00road_of_riches 0/8 (3.4), 03the_front 1/8, 03honeycomb 0/6.
- Sponge: 00quadrants 2/12 (5.2), 03shrines 1/9 (4.0), 02harvest 2/8 (4.1).
- Source: [h2h.txt §6](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/h2h.txt)

**Sides**
- Side a wins 3,445/6,795 (50.7%); 5v5 2,092/4,119.
- test4 on side a 48/140 (E 60.4, -12.4) vs side b 126/260 (+12.8), the largest side effect.
- Moderate effects:
  - NEET: a -7.3 (n 250), b +7.7 (n 150).
  - IC: a +7.6 (n 180), b -6.9 (n 220).
  - SSSA: a +9.4, b -9.5.
  - new team(4): a +9.7, b -9.7.
- Round-2000 tiebreaks: 291 games; side b won 134 of them.
- Source: [h2h.txt §8](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/h2h.txt)

**Draft families**, top-30 vs top-30, BT-adjusted. Each team's roster goes to the first family that matches, in the order C&I, Willow, Prism, Varg, Tavi/Ren, no-Marcella, Std. "Std" = Marcella with only Vesper/Vendetta/Ryth/HoR.
- Willow beats Std 425/760 (+39.5 over BT).
- Family totals: Std 1,037/2,266 (-46.5); Willow 822/1,562 (+54.8); Prism 376/741 (+12.9); no-Marcella 148/254 (+16.0); C&I 780/1,415 (+2.0); Varg 291/599 (-12.0); Tavi/Ren 238/547 (-27.3).
- C&I beats Varg (+11.5/136) and Tavi/Ren (+9.2/109), but loses to Willow (-10.3/362) and Prism (-9.0/153).
- Source: [draft_fam.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/draft_fam.txt)

**Champion picked by one side only** (top-30 vs top-30): Willow +55.1 (1,046/2,009); Prism +37.0 (569/1,059); Marcella -27.7 (348/822); Ryth -26.2 (998/2,144) — [h2h.txt §11](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/h2h.txt)

**Opponent-champion sensitivity** (residual per game, with vs without that champion on the opponent's side):
- Mite: Prism -0.11 (35/66, E 40.7); Willow -0.10 (70/122, E 78.2).
- IC: C&I -0.15 (92/179, E 106.8).
- UoS: Varg -0.32 (6/26, E 13.8); Vesper -0.18 (125/251, E 141.3).
- BattleCats: Vendetta -0.20 (110/250, E 128.2).
- NEET: Prism -0.14 (18/55); Willow -0.13 (49/123).
- test4: Prism -0.11 (15/52).
- pdi: Varg -0.12 (18/56).
- Sponge: Prism -0.14 (9/31).
- newer team: C&I -0.07; Willow -0.07.
- AdA: Tavi/Ren -0.07 (small).
- Source: [h2h.txt §10](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/h2h.txt)

**Rosters (main 5v5 roster per team, W/N vs E)**
- Mite: Vesper+Vendetta+C&I+Marcella+HoR 136/216 (E 137.2).
- IC: Vendetta+C&I+Marcella+Willow+HoR 76/117 (E 74.0).
- UoS: Ryth+C&I+Willow+Varg+HoR 54/81 (E 44.2); its other 5v5, Ryth+Vendetta+Marcella+Varg+HoR, 13/52 (E 29.0).
- NEET: Std 44/120 (E 56.4).
- test4: Vesper+C&I+Marcella+Willow+HoR 116/240 (E 104.1).
- newer team: Vendetta+C&I+Prism+Varg+HoR 29/38 (E 21.0); C&I+Prism+Marcella+Willow+HoR 7/29 (E 15.4).
- German Empire: Vesper+Vendetta+Marcella+Ren+Tavi 68/182 (E 84.7).
- Trzy Kwaterki 4v4: Vesper+Vendetta+Marcella+HoR 21/82 (E 38.5).
- Source: [h2h.txt §9](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/h2h.txt)

**Altar locks per game** (teams' decoded games):
- 0: Mite (20), UoS (22), AdA (24), Supaswag, JukeFall, prism best girl, Rogue Lock Pickers.
- Heavy users: T1 6.74, newer team 5.94, new team(4) 5.48, German Empire 5.45, IC 4.60.
- pdi places 0.52 per game, and 12 of its 12 locks hit an enemy tribute.
- Across the top 30, only 8.0% of 1,187 locks hit a tribute.
- Source: [tables.txt B6](file:///home/claude/cambridge_battlecode/experiments/top30_nov3/draft_bank/out/tables.txt)

**Our record** against the top 30: 23/270 games (mostly unranked groups). Mite 1/95, IC 4/65, AdA 1/10, newer team 0/10, prism best girl 3/60, EE 8/15, MFF1 6/10 — [matches_me.jsonl](file:///home/claude/cambridge_battlecode/experiments/ladder_nov2/matches_me.jsonl)

### Inferences
- Single-map residuals with n = 4-10 are partly noise: about 86 maps × 30 teams produce several 0/5-type cells by chance. Plan map play on the class-level results (n ≥ 60) and use single maps as tie-breakers:
  - UoS: many altars / many groups.
  - pdi: far spawns.
  - Trzy Kwaterki: 4v4.
  - German Empire: 5v5.
  - :3: near spawns.
  - JukeFall: 9-14 groups.
- The bot cannot choose maps or sides. Map-class knowledge is used by switching behaviour once the map and the opponent are known.
- Several top teams have a distinctive roster and can be fingerprinted from the enemy draft. Below, "of all uses" is P(team | roster): the team's share of every team-game, across all 45 teams, that used that exact roster ([fingerprint.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/fingerprint.txt)).
  - Unique or nearly unique (P ≥ 0.96):

    | Team | Roster | Team-games of all uses (P) | Team's own games |
    |---|---|---|---|
    | UoS | Ryth+C&I+Willow+Varg+HoR | 81 of 81 (1.00) | 81 of 400 |
    | AdA | Vesper+C&I+Marcella+HoR | 61 of 61 (1.00) | — |
    | newer team | Vendetta+C&I+Prism+Varg+HoR | 38 of 38 (1.00) | — |
    | test4 | Vesper+C&I+Marcella+Willow+HoR | 240 of 251 (0.96) | 240 of 400 |
    | test4 | C&I+Marcella+Willow+HoR | 93 of 93 (1.00) | — |
    | BattleCats | Ryth+Vendetta+Prism+Marcella+HoR | 59 of 61 (0.97) | — |
    | policy wonk | Marcella+Willow+Ren+Tavi+HoR | 81 of 81 (1.00) | — |
    | Noobot | Ryth+Vesper+Marcella+Willow+HoR | 266 of 273 (0.97) | 266 of 400 |
    | German Empire | Vesper+Vendetta+Marcella+Ren+Tavi | 182 of 182 (1.00) | — |
    | new team(4) | Vendetta+Marcella+Varg+Tavi+HoR | 83 of 84 (0.99) | — |
    | Rogue Lock Pickers | Vesper+Vendetta+Marcella+Willow+Tavi | 244 of 244 (1.00) | — |
    | MFF1 | Vesper+Vendetta+C&I+Marcella+Willow | 245 of 245 (1.00) | — |

  - Ambiguous:

    | Team | Roster | Team-games of all uses (P) | Note |
    |---|---|---|---|
    | Mite | Vesper+Vendetta+C&I+Marcella+HoR | 216 of 389 (0.56) | — |
    | IC | Vendetta+C&I+Marcella+Willow+HoR | 117 of 426 (0.27) | Olympus 217 of the 426 |
    | IC | Vesper+Vendetta+C&I+Varg+HoR | 54 of 84 (0.64) | — |
    | pdi | Ryth+Vendetta+Marcella+Willow+HoR | 250 of 416 (0.60) | — |
    | Sponge | Ryth+Vesper+C&I+Marcella+HoR | 77 of 93 (0.83) | — |

  - The Std 5v5 roster Ryth+Vesper+Vendetta+Marcella+HoR covers 2,443 team-games. For each of its users (NEET, BattleCats, Sponge, Trzy Kwaterki, T1, caterpillow, Nyx, JukeFall, conqueror_of_openai, EE, procless) P ≤ 0.10, so these teams need generic counters.
- Draft families are BT-adjusted but map-confounded: teams pick rosters per map. The Willow-over-Std effect (+39.5 over 760 games, about +5 points of win rate) is the most robust draft signal. It is consistent with Willow hurting Mite, NEET and newer team.

### Gaps
- Whether our bot sees the enemy picks before its own picks depends on the draft order, which I did not verify. At the latest, it knows the enemy roster at round 1.
- The data spans about 13 hours. Teams may update their bots before Nov 18.

## 2. How and when does each top-10 team lose (decoded losses)?

### Takeaway
- Every top-10 team loses mainly through deaths: its deaths in losses are 1.8-3.6 times those in its wins.
- The middle game (r301-1000) decides most losses.
- They differ in timing:
  - Ad Astra and NEETCoders are decided early (median decisive round 362-364).
  - Univardisty of Shingtonwash and print dont int are decided in the middle (median 450-502).
  - Mite, Intercontinental Fish, newer team and Sponge are decided late (604-737), often after leading.
- The teams that beat them out-fight them and out-farm them in r301-800.

### Cited Findings
**When losses are decided** (decided-phase counts, quartiles of the decisive round, blown leads where the team had led by ≥ 100, fight swing and capture gap of ≥ 60 in the 150 rounds before the decisive round):

| Team | Losses / decoded | ≤ r300 | r301-600 | r601-1000 | > r1000 | close | quartiles | blown leads | fight swing | capture gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Mite | 27/85 | 4 | 5 | 10 | 3 | 5 | 534/638/888 | 6/27 | 16/22 | 12/22 |
| IC | 33/85 | 6 | 6 | 11 | 3 | 7 | 307/737/941 | 9/33 | 13/26 | 15/26 |
| UoS | 40/91 | 8 | 16 | 10 | 2 | 4 | 333/502/737 | 13/40 | 18/36 | 29/36 |
| AdA | 34/84 | 11 | 12 | 6 | 1 | 4 | 230/364/548 | 5/34 | 12/30 | 17/30 |
| newer team | 43/83 | 4 | 15 | 13 | 7 | 4 | 457/604/894 | 12/43 | 21/39 | 21/39 |
| NEET | 44/85 | 14 | 13 | 8 | 1 | 8 | 243/362/603 | 13/44 | 14/36 | 24/36 |
| BattleCats | 44/84 | 10 | 15 | 14 | 2 | 3 | 321/518/680 | 8/44 | 13/41 | 25/41 |
| test4 | 51/83 | 10 | 12 | 14 | 4 | 11 | 305/544/758 | 10/51 | 24/40 | 30/40 |
| pdi | 43/90 | 5 | 17 | 11 | 2 | 8 | 364/450/669 | 8/43 | 10/35 | 30/35 |
| Sponge | 50/91 | 9 | 12 | 14 | 8 | 7 | 331/623/928 | 11/50 | 21/43 | 28/43 |

- Extra notes from the same data:
  - NEET's median round of its maximum lead in blown leads is r288.
  - Sponge's median round of its maximum lead in blown leads is r802.
- Source: [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**Close losses where the team had banked 850 or more and still lost the race:**
- test4: 10 of 11 close losses (its mean final bank in close losses is 858).
- NEET: 7 of 8 (854).
- pdi: 7 of 8 (814).
- Sponge: 5.
- UoS: 4 (932).
- Mite: 3.
- Source: [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**Own per-game means in losses vs wins**: deaths L/W; kills L/W; gems captured by r300 L/W; gems captured r301-800 L/W.

| Team | Deaths L/W | Kills L/W | Captured ≤ r300 L/W | Captured r301-800 L/W |
|---|---|---|---|---|
| Mite | 20.4 / 5.7 | 6.3 / 11.5 | 208 / 235 | 419 / 563 |
| IC | 20.5 / 6.3 | 7.3 / 10.7 | 140 / 287 | 227 / 538 |
| UoS | 13.6 / 4.5 | 6.1 / 21.5 | 175 / 266 | 212 / 481 |
| AdA | 13.5 / 7.9 | 5.2 / 13.8 | 145 / 196 | 284 / 524 |
| newer team | 15.5 / 4.3 | 3.7 / 8.4 | 195 / 244 | 367 / 545 |
| NEET | 10.9 / 6.2 | 4.1 / 11.8 | 208 / 266 | 298 / 505 |
| BattleCats | 11.6 / 4.7 | 5.2 / 14.3 | 150 / 280 | 278 / 532 |
| test4 | 16.2 / 5.2 | 5.2 / 12.9 | 152 / 259 | 273 / 546 |
| pdi | 8.6 / 4.8 | 4.3 / 13.9 | 188 / 222 | 293 / 439 |
| Sponge | 13.0 / 7.0 | 5.8 / 14.7 | 177 / 201 | 316 / 490 |

- Additional details in the same tables:
  - Mite's late captures: 179 in losses vs 241 in wins.
  - NEET's late captures: 86 in losses vs 425 in wins.
  - UoS dies to camps 2.85 times per game in losses vs 0.98 in wins.
- Source: [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**Who kills them in their losses** (deaths per game by killer):
- Mite: Vesper 4.37, Marcella 4.22, HoR 4.07, Prism 2.48.
- IC: HoR 6.00, Marcella 5.76.
- AdA: Marcella 5.50.
- newer team: Marcella 4.93, Vesper 3.74.
- Sponge: Marcella 4.76.
- pdi: Marcella 4.12.
- BattleCats: Marcella 3.91.
- test4: Marcella 3.61, HoR 3.35, Vesper 3.29.
- UoS: Marcella 3.45, camps 2.85.
- NEET: Marcella 3.45.
- Source: [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**What the winners did differently** (the opponent's numbers in the team's losses vs the opponent's numbers in the team's wins):
- Mite's conquerors:
  - Captured 557 gems in r301-800 vs 300.
  - Captured 360 late vs 68.
  - Banked 34 times vs 18.8.
  - Placed fewer locks: 0.8 vs 2.7.
- IC's conquerors banked bigger bags: 89.8 gems per bank vs 34.8.
- UoS's conquerors:
  - Captured 594 in r301-800 vs 172.
  - Captured 6,987 gold vs 1,816.
  - Had 34.9 vs 17.5 items at r600.
  - Took 13.1 vs 1.5 contested cycles (objectives subset).
- AdA's conquerors had 293 vs 190 gems (banked+carried) at r300.
- NEET's conquerors had 311 vs 172 gems at r300.
- BattleCats' conquerors:
  - 21.4 vs 5.0 raids (objectives subset).
  - BattleCats itself banks 32.5-gem bags in losses vs 101 in wins.
- test4's conquerors took 8.6 vs 1.4 contested cycles.
- Source: [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**Nemesis pairs in the decoded games** (nemesis/victim means in the nemesis wins):
- Ad Astra vs Mite: AdA won 9 of 14.
  - Kills 13.2/6.3; deaths 6.6/14.1.
  - Captures by r300 244/263 (Mite slightly ahead).
  - Captures r301-800 660/499; late 254/122.
  - No locks on either side.
  - 4 of the 9 were decided in r601-1000.
- UoS vs IC: UoS won 9 of 15.
  - Kills 26.9/4.4; deaths 5.6/27.6.
  - Captures by r300 200/115; r301-800 478/166.
  - Locks 0/2.1.
- IC vs newer team: IC won 10 of 12. Kills 14.6/4.6; raids 25.2/1.0; items at r600 29.9/17.7.
- Mite vs test4: Mite won 9 of 9. Kills 21.0/6.9; raids 37/3.5; late captures 461/50.
- BattleCats vs Sponge: BattleCats won 8 of 8. Kills 10.6/2.5; gems per bank 99.6/31.6.
- newer team vs NEET: newer team won 6 of 8. Captures by r300 295/182; locks 5.0/0.2; 3 of the 6 decided by r300.
- NEET vs UoS: NEET won 6 of 14. Captures r301-800 526/173; gold 11,214/3,555.
- Source: [losses.txt, NEMESIS PAIRS](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**Trzy Kwaterki vs BattleCats**: TK won 4 of 6; 3 of those 4 were close games — [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

### Inferences
- **Mite** loses late and through fights. In its 27 losses it dies 20.4 times per game, and 16 of the 22 decided losses had a fight swing.
  - Its opening holds even in losses (208 gems by r300 vs 235 in wins), so rushing it is not the counter.
  - Winning the r300-1000 fights is.
- **IC** has two loss modes:
  - An opening loss: 140 gems captured by r300 vs 287 in wins; 6 of 33 losses decided by r300.
  - A late fight collapse: deaths 20.5, killed by HoR 6.0 and Marcella 5.76 per game.
- **UoS** is out-farmed in the middle: 29 of 36 pre-decisive windows show a capture gap of 60+. It banks tiny bags (about 19 gems) very often and dies to camps.
- **Ad Astra** and **NEET** lose in the opening. The opponent is about 120-140 gems ahead at r300 (AdA 129 vs the opponent's 293; NEET 175 vs 311).
- **print dont int** rarely loses fights (8.6 deaths in losses, the lowest of the top 10; fight swing in only 10 of 35). It loses on economy: capture gap of 60+ in 30 of 35 windows.
- **test4, NEET and pdi** often lose the final race with 850+ gems already banked.

### Gaps
- Steals and wards were not separated per team in this pass.
- The objectives subset (contested cycles, raids) covers only about 1/3 of the decoded games, and per-team n for it was not tabulated.
- The "cancelled tribute" counts include Mite's style artefacts: about 5 per game in both wins and losses.

## 3. What are the common failure modes of strong teams, and which opponent styles do they struggle against?

### Takeaway
Across the 999 decoded top-30 games:
- Kills and deaths decide 86% of games.
- Captures in r301-800 decide 83%.
- Captures before r300 are much weaker (68%), and locks are useless as a predictor (51%).
- 26% of games are won by a team that had trailed by 100+.
- Strong teams struggle against Willow and Prism rosters (sustained fights) and against teams that raid them in the middle game.

### Cited Findings
**Side with more X wins** (all 999 games / 164 upsets where the winner's BT was ≥ 40 lower):

| Feature | All games | Upsets |
|---|---|---|
| More kills | 784/915 (0.86) | 127/150 (0.85) |
| More deaths | 134/937 (0.14) | 22/161 |
| More captures r301-800 | 813/977 (0.83) | 131/162 (0.81) |
| More late captures | 599/701 (0.85) | — |
| More captures by r300 | 641/946 (0.68) | 98/160 (0.61) |
| More items at r600 | 674/860 (0.78) | 107/144 |
| More banks | 821/982 (0.84) | — |
| More locks | 355/695 (0.51) | 53/109 (0.49) |
| Higher Marcella capture share | 504/971 (0.52) | — |
| More contested cycles taken | 146/181 (0.81) | — |
| More raids | 168/231 (0.73) | — |

Source: [losses.txt UNIVERSAL](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**Upset winners vs losers** (per-game means, n = 164 upsets):
- Kills 14.3 vs 5.6; deaths 6.2 vs 15.4.
- Captures r301-800 526 vs 307.
- Gems per bank 64.7 vs 31.2.
- Source: [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**Decisive phase**
- All 999 games: close 178; ≤ r300 157; r301-600 303; r601-1000 260; > r1000 101.
- 164 upsets: close 34; ≤ r300 25; r301-600 44; r601-1000 43; > r1000 18.
- Source: [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**Leads are not safe**
- A lead of ≥ 30 gems wins:
  - at r300: 546/710 (77%);
  - at r600: 651/780 (83%);
  - at r1000: 388/436 (89%).
- Blown leads of ≥ 100: 259/999 games, and 55/164 upsets.
- Source: [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**Ranks 11-20 against teams outside their cluster** (293 games, 152 losses):
- Deaths 12.9 in losses vs 4.9 in wins.
- Captures r301-800 307 vs 538.
- Fight swing in 60/122 losses; lost the race with ≥ 850 banked in 20 losses.
- Beaten by pdi 36, Sponge 30, test4 13.
- Source: [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**Ranks 21-30** (106 games, 69 losses):
- Deaths 11.7 vs 6.3.
- Captures r301-800 336 vs 511.
- Beaten by JukeFall 23, conqueror_of_openai 12.
- Source: [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt)

**Behaviour in the last 200 rounds** (top-30 decoded games):
- Losers are dead 22.2% of body-rounds vs winners 7.6% (n = 305 each).
- Losers stay in their own half 65.0% vs 47.0%.
- Source: [tables.txt E2](file:///home/claude/cambridge_battlecode/experiments/top30_nov3/draft_bank/out/tables.txt)

**Tribute mechanics**: a tribute is cancelled by a stun, an enemy altar lock or death, not by damage. A lock is placed within Chebyshev 2 and costs 10 gold. The win registers when the tribute lands — [ENGINE_FACTS.md](file:///home/claude/cambridge_battlecode/docs/ENGINE_FACTS.md)

### Inferences
- **Common failure mode 1, deaths in the middle game.** In every top-10 team's losses deaths jump 1.8-3.6×, mostly to Marcella (and HoR or Vesper for Mite and IC). Its "fight swing" precedes the decisive round in about half of all losses.
- **Common failure mode 2, the middle economy stalls.** Captures in r301-800 in losses are 40-58% of those in wins for every top-10 team.
- **Common failure mode 3, the endgame race.** Close losses with 850+ gems banked: test4 10, NEET 7, pdi 7, ranks 11-20: 20. Stunning or locking the final tributer converts those.
- **Styles they struggle against:**
  - Sustained teamfight rosters: Willow (+39.5 vs Std), Prism (Mite, NEET, test4, Sponge), Varg (UoS, pdi), C&I (IC).
  - Teams that raid their half in the middle: IC's 25 raids vs 1 against newer team; Mite's 37 vs 3.5 against test4.
- **Locks are not a lever** against the top 3 bots (Mite, UoS, AdA place none and win). Use locks only reactively, on an enemy tribute (pdi: 12/12 hit).

### Gaps
- Causality is not established. Kills and captures are partly consequences of being ahead.
- The upset comparison (164 games) is the closest available control.

## 4. What is the concrete counter for each team, and what are the universal counters?

### Takeaway
- **Universal**: win the middle-game fights without feeding deaths, keep farming r301-800 and take contested respawn cycles. Draft Willow (and Prism) into the Marcella core. Hold an endgame tribute-denial rule. Do not spend on locks except on a live enemy tribute.
- **Per team**: switch map-class plans and the opening by the identified opponent (from its draft fingerprint) and the map class, as listed below.

### Cited Findings
Each counter below combines the numbers of sections 1-3. Sources: [h2h.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/h2h.txt), [losses.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/losses.txt), [draft_fam.txt](file:///home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out/draft_fam.txt), [tables.txt](file:///home/claude/cambridge_battlecode/experiments/top30_nov3/draft_bank/out/tables.txt).

**#1 Mite** (fingerprint: Vesper+Vendetta+C&I+Marcella+HoR; 0 locks)
- **Evidence**:
  - Ad Astra 34/65 (+7.7).
  - Weak with 9-14 groups 71/127 (-9.9), gold-poor 55/99, 4v4 39/69 (E 44.4).
  - Against Prism 35/66 (E 40.7); against Willow 70/122 (E 78.2).
  - Losses are late (quartiles 534/638/888); 20.4 deaths per loss.
- **Counter**:
  - Draft: Marcella + Willow + Prism core.
  - Opening: do not force a race. Mite's r300 total is about the same in its wins and losses.
  - Middle (r300-1000): fight only with local numbers ≥ its numbers and focus its Vesper/HoR/Marcella carriers. Ad Astra's winning pattern was kills 13.2 vs 6.3 and middle captures 660 vs 499.
  - Keep farming the middle groups through contact.
  - On 9-14-group and gold-poor maps, contest the mid groups.
- **Expect**: a close game. Mite is 58-27 in the decoded games.

**#2 Intercontinental Fish** (fingerprint: Vendetta+C&I+Marcella+Willow+HoR; locks 4.6 per game)
- **Evidence**:
  - UoS 34/60 (+8.5): kills 26.9 vs 4.4 and captures by r300 200 vs 115 in UoS wins.
  - Against opponents with C&I 92/179 (E 106.8).
  - Far spawns 30/65 (-10.6); ≤ 8 groups 15/35.
  - Captures by r300 halve in its losses (140 vs 287).
- **Counter**:
  - Draft: UoS-like sustain — C&I + Willow (+ Varg).
  - Contest the opening groups hard; 6 of 33 IC losses were decided by r300.
  - Avoid open fights against its HoR/Marcella burst (6.0 and 5.76 deaths per game in its losses come from them). Engage only when its HoR spell is on cooldown; cooldowns are readable.
  - Its conquerors bank big bags (89.8 per bank): bank when safe rather than often.
  - On far-spawn maps, out-farm it.

**#3 Univardisty of Shingtonwash** (fingerprint: Ryth+C&I+Willow+Varg+HoR; 0 locks)
- **Evidence**:
  - 3+ altars 68/164 (-24.4); 15+ groups 107/243 (-28.5).
  - Against Varg 6/26; against Vesper 125/251 (E 141.3).
  - NEET 25/50 (+5.1): middle captures 526 vs 173.
  - Losses decided r301-600 (16/40); capture gap in 29 of 36 windows.
- **Counter**:
  - Draft: Vesper + Varg.
  - Spread out and farm many groups on multi-altar maps. Do not deathball into its sustain comp.
  - Take the contested respawn cycles (its conquerors took 13.1 vs 1.5).
  - Its 1-altar / ≤ 8-group strength (31/31) means only fight for the central big group on those maps if numbers allow.
  - Bait it into camp damage; it dies to camps 2.85 times per game in its losses.

**#4 Ad Astra** (Vesper+Vendetta+C&I+Ren+HoR or Vesper+Marcella+Willow+Ren+HoR; 0 locks)
- **Evidence**:
  - Earliest-decided losses (quartiles 230/364/548; 11 of 34 by r300).
  - Opponent 293 vs 129 gems at r300.
  - Spawn-altar maps 4/12; mixed altars 4/15.
  - Sponge 19/40 (+6.3).
- **Counter**:
  - Fast opening: take the nearest big groups by r300 and contest its first big-group cycle.
  - Fight early with the Marcella burst; Marcella kills 5.5 of its champions per game in its losses.
  - On spawn-altar maps, bank early and often.
  - Avoid long passive games on far-spawn maps (it is 49/73 there).

**#5 newer team** (Vendetta+C&I+Prism+Varg+HoR or 3v3 Vendetta+Marcella+HoR; locks 5.9 per game)
- **Evidence**:
  - IC 41/60 (+6.5): raids 25.2 vs 1.0 and kills 14.6 vs 4.6 in IC wins.
  - ≤ 8 groups 13/33; monolith maps 9/19; 1 altar 40/81.
  - Blown leads 12/43; losses decided r301-1000.
- **Counter**:
  - Raid its half in r300-800 with 2+ bodies when it is split.
  - Expect its locks: it places 6.0 per game in its losses. Bank at altars it is not near, and break locks with Vendetta's reset (3 hits).
  - Draft C&I/Willow.
  - On 1-altar and few-group maps, hold the centre.

**#6 NEETCoders** (Std or Vendetta+Marcella+Willow+HoR; locks 0.8 per game)
- **Evidence**:
  - newer team 35/45 (+7.9): captures by r300 295 vs 182.
  - Losses decided early (243/362/603).
  - Blown leads 13/44, with a median maximum lead at r288.
  - Monolith maps 2/12; spawn-altar maps 4/14.
  - Against Prism 18/55; against Willow 49/123.
  - Its Std 5v5 roster: 44/120 (E 56.4).
  - Lost 7 races with 850+ banked.
- **Counter**:
  - Draft Prism/Willow.
  - Out-farm its opening.
  - Keep pressure after its early peak.
  - Endgame: stun or lock its last tribute.

**#7 BattleCats** (Std or Ryth+Vendetta+Prism+Marcella+HoR; locks 2.7 per game)
- **Evidence**:
  - Against Vendetta 110/250 (E 128.2).
  - ≤ 8 groups 16/40; strong on monolith maps 15/17.
  - Captures by r300 150 vs 280 in losses.
  - Its conquerors raid 21.4 vs 5.0.
- **Counter**:
  - Draft Vendetta.
  - Early aggression and raids.
  - Contest its opening.
  - Avoid long monolith games.
  - It banks 101-gem bags in wins: stun its carriers.

**#8 test4** (Vesper+C&I+Marcella+Willow+HoR; locks 0.3 per game)
- **Evidence**:
  - Side a 48/140 (-12.4).
  - Spawn-altar maps 4/14; 3v3 23/67.
  - Mite 9-0 in the decoded games (raids 37 vs 3.5).
  - Lost 10 races with 850+ banked.
  - Against Prism 15/52.
- **Counter**:
  - Draft Prism/Vendetta.
  - Raid its half in the middle game.
  - Endgame: tribute denial with a stun or lock on its final bank.
  - Push harder when it is side a.

**#9 print dont int** (Ryth+Vendetta+Marcella+Willow+HoR; 0.5 locks per game, 12/12 on live tributes)
- **Evidence**:
  - Far spawns 14/74 (-18.8); near spawns 93/171 (+15.9).
  - Loses on economy: capture gap in 30 of 35 windows; 8.6 deaths per loss.
  - Against Varg 18/56.
  - Lost 7 races with 850+ banked.
- **Counter**:
  - On far-spawn / big maps, pure farming tempo; don't fight.
  - On near-spawn maps, avoid early contact.
  - Never tribute within 2 tiles of its bodies (reactive locks).
  - Draft Varg.

**#10 Sponge** (Std or Ryth+Vesper+Marcella+HoR; 3.1 locks per game)
- **Evidence**:
  - BattleCats 16/20 (+6.4): kills 10.6 vs 2.5 and 99.6-gem banks.
  - ≤ 8 groups 7/29.
  - Against Prism 9/31.
  - Losses late (331/623/928; 8 decided after r1000); blown leads with a median maximum lead at r802.
- **Counter**:
  - Draft Prism.
  - Keep contesting through r800-1200; it loses leads late.
  - Fight in the middle with numbers.
  - On ≤ 8-group maps, contest every cycle.

**Ranks 11-20 cluster** (mostly the Std roster; generic counters):
- **Trzy Kwaterki**:
  - 4v4 26/95 and near spawns 72/189 (both -18.5).
  - Its 4v4 roster Vesper+Vendetta+Marcella+HoR: 21/82 (E 38.5).
  - Counter: aggression on 4v4 and near-spawn maps.
- **T1**:
  - Monolith maps 2/14; 3v3 23/67 (E 32.6).
  - Heaviest locker (6.7 per game).
  - Counter: bank away from it.
- **policy wonk**: monolith maps 5/20; 3+ altars 68/155 (E 78.2).
- **caterpillow**: 1 altar 33/87 (E 45.3); ≤ 8 groups 14/43.
- **Noobot**: near spawns 80/181 (E 91.6); 3v3 29/69.
- **German Empire**:
  - 5v5 90/238 (-19.4); its 5v5 roster Vesper+Vendetta+Marcella+Ren+Tavi 68/182 (E 84.7).
  - Far spawns 24/72.
  - Locks 5.5 per game.
- **JukeFall**: 9-14 groups 49/143 (-21.5).
- **Supaswag**: gold-poor 38/90.
- **Nyx**: 1 altar 34/84.
- **Cluster loss pattern**: decisive quartiles 348/510/721; 12.9 deaths per loss; fight swing in 60 of 122 losses; 20 race losses with 850+ banked.

**Ranks 21-30 cluster**:
- **:3**: near spawns 76/192 (-27.0); spawn-altar maps 1/12.
- **prism best girl**: 15+ groups 93/246 (-24.4); 3v3 20/71 (-13.7).
- **EE**: monolith maps 6/25; gold-poor 36/96.
- **MFF1**: gold-poor 42/104 (-12.4).
- **Olympus**: monolith maps 5/23.
- **jazz**: 4v4 29/77.
- **SSSA** and **new team(4)**: side b -9.5 and -9.7.
- **Cluster loss pattern**: 11.7 deaths per loss vs 6.3 in wins; middle captures 336 vs 511.

### Inferences
**Universal counters**, in priority order:
1. **No feeding.** Avoid even trades at a numbers disadvantage. The team with fewer deaths wins 86% of games.
   - Engage on readable enemy cooldowns: Marcella's range-4 2.0× spell and HoR's.
   - Focus enemy carriers.
2. **Middle-game tempo.** Keep farming through contact in r301-800 and take contested respawn cycles. Winning sides capture about 1.7× more in r301-800.
3. **Draft.** Add Willow to the Marcella core (Willow +39.5 vs Std over 760 games). Add Prism against Mite, NEET, test4 and Sponge; Varg against UoS and pdi; Vendetta against BattleCats; C&I against IC.
4. **Endgame tribute denial.** When the enemy has ≥ 850 banked and is tributing, stun it, kill it or lock (lock only then). Close race losses are 10-20% of strong teams' losses.
5. **Do not stop after a lead.** 26% of games are won from 100+ behind.
6. **Map-class switches** per opponent, as listed above.

**Caveat on draft changes**: earlier local tests found Ren / Varg / C&I swaps level or worse on our bot's decision logic (AGENTS.md history). A Willow or Prism swap must be screened the same way before it ships.

### Gaps
- No engine test of any counter was run (forbidden this session). All counters are inferred from the ladder data.
- The objectives-based numbers (cycles, raids) are a subset with smaller n.
