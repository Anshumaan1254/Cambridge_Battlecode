# How and why g8 (god.zip) loses to the top three: S0, 239 real games, phase by phase

Session 17 gap study (Oct 23). g8 = `bots/g8` (GOD v8 + opponent model, = god.zip), team HouseOfCoders, against prism best girl
(PBG, 1-79), Intercontinental Fish (IFish, 5-75) and Claudus Maximus (CM, 7-72): **13-226 over 239 unranked games, 40 maps x both
sides** (label S0). Every number below is a per-game mean (us / them) over the 239 games unless a column says otherwise. "Them" is
always the opponent in the same games. Findings, ranked by cost, are in section 8.

## 0. Data, tools, definitions

- Replays `C:/battlecode/cache/t2/s0/*.repl26a`, fight dumps `C:/battlecode/cache/t2dump/s0/*.json.gz` (exact per-step damage
  attribution), platform summaries `experiments/live/compact/<matchId>.json` (purchases, kills, clears, fuel-outs).
- New scripts, all in `tools/top2/gap/` (pipeline `run_all.sh` + `run2.sh`, tables `tables.sh`; outputs and printed tables in
  `C:/battlecode/cache/gap_g8/`):
  - `sides.py` (game table), `deccache.mjs` (decode each replay once, cached), `lib.mjs` (zones, camp groups);
  - `gapx.mjs`: one record per game with checkpoints, opening, time budget with and without an enemy near, walks, captures by
    zone and group kind, farming cycles, camp efforts, movement pathologies, recalls, banking, deaths with context;
  - dump-based: `killers.mjs` (killing blows, damage sources), `campdps.mjs` (camp damage per farm round), `nearbehav.mjs` (action
    with an enemy within 8, arrivals at farmers), `chanpunish.mjs` (tributes and recalls and whether they are punished),
    `lifetimes.mjs` (life length before a death);
  - existing tools rerun on S0: `tools/live/fightan.mjs`, `fightfirst.mjs`, `idleallies.mjs`, `strat_bank.mjs`;
  - aggregators: `compact_agg.py`, `gapx_agg.py`, `fight_agg.py`, `killers_agg.py`, `ff_agg.py`, `chan_near_agg.py`,
    `lifetimes_agg.py`, `extra_agg.py`.
- **Definitions**:
  - Phases: r1-299, r300-599, r600-999, r1000+.
  - Zones are relative to the team: O own half, M middle band (|d_own - d_their| <= 4, Chebyshev to the spawn centres), T their half.
  - Farm round: the body damaged a camp that round (exact `cdmg`). dpf: camp damage per farm round.
  - Engagement: champion-vs-champion damage clustered with gaps of 6 rounds or less, within 10 tiles, with 3 or more hits or a
    death. Starter: the side whose damage lands first. Local power: the max-health sum within 8 of the first hit.
  - Contact: opposing bodies within 4 in a quiet area.
  - "Near enemy": an enemy champion alive within 8 and not on its own spawn.
  - Death modes are fightan's: fighting, fleeing, approaching (walked toward the enemy without hitting), camp, walking, recalling...
- The index holds 239 games (79 vs CM). The 13-227 quoted for S0 counts 240; one CM game is missing from the index.
- Caveats: fuel-outs are only in the platform summaries (not in replays). Gem and gold costs are estimates at our own yield
  (0.104 camp gems per alive body-round, 0.72 per farm round, 6.9 gems per 1,000 camp damage), so they are conservative. Costs of
  different findings overlap (the same lost round can be counted under "near an enemy" and "middle").

## 1. Headline

| per game | us | them | PBG games us/them | IFish | CM |
|---|---|---|---|---|---|
| banked gems | **323** | **1,025** | 310 / 1,071 | 297 / 1,015 | 363 / 987 |
| camp gems captured | 414 | 1,055 | 402 / 1,091 | 420 / 1,041 | 420 / 1,032 |
| camp damage dealt | 59.9k | 134.9k | 61.3k / 134.1k | 58.1k / 134.7k | 60.4k / 135.7k |
| gold earned | 3,232 | 8,502 | 3,028 / 7,846 | 2,993 / 8,980 | 3,680 / 8,681 |
| deaths | **14.9** | **6.1** | 16.8 / 3.4 | 14.3 / 7.2 | 13.7 / 7.7 |
| kills | 4.1 | 11.8 | 2.1 / 11.6 | 3.7 / 12.1 | 6.6 / 11.6 |
| camp clears | 30.7 | 56.3 | 32.6 / 52.3 | 28.8 / 54.5 | 30.7 / 62.1 |
| max health per body r300 / r600 / r1000 | 1,132 / 1,360 / 1,733 | 1,360 / 2,068 / 3,122 | r1000 1,587 / 3,788 | 1,700 / 2,330 | 1,889 / 3,119 |
| middle-band gems | 126 | 594 | 103 / 622 | 133 / 584 | 141 / 576 |
| share of body-time dead | 17.9% | 7.4% | | | |

**The camp-gem gap (641 a game) splits multiplicatively** (`extra_agg.py`, `campdps.mjs`; log shares):

| factor | us | them | share of the gap | gems |
|---|---|---|---|---|
| farm share of alive time | 0.143 | 0.209 | 41% | ~263 |
| camp damage per farm round (dpf) | 105 | 141 | 31% | ~202 |
| alive body-rounds (dead time, and body count) | 3,991 | 4,557 | 14% | ~91 |
| gems per 1,000 camp damage (target value) | 6.9 | 7.8 | 13% | ~85 |

- **Farm share.** About half of the farm-share loss happens with an enemy near. There we farm 4.4% of rounds; they farm 15.9%. The
  other half happens with nobody near: we farm 18.7%, they farm 23.0%.
- **dpf.** Equal early (76 vs 82 at r<300), then it falls behind with items: 106 vs 133, 132 vs 196, 182 vs 249.
- **Where the gap is.** The middle band: 126 vs 594 gems, which is 73% of the camp-gem gap. By group kind: elks 244 vs 647,
  monoliths 20 vs 131, golems 4 vs 31.
- **Bags.** We lose 109 gems a game in bags at death, 86 of them to their champions. They lose 79, 63 of them to us.

**Snowball.** The gap opens early and widens every phase:

| | r100 | r300 | r600 | r1000 |
|---|---|---|---|---|
| camp gems captured | 27 / 48 | 102 / 192 | 222 / 457 | 338 / 772 |
| banked gems | 12 / 21 | 63 / 125 | 158 / 353 | 262 / 614 |
| max health (team) | 4,639 / 4,967 | 5,305 / 6,389 | 6,349 / 9,490 | 8,061 / 13,956 |
| item shard equivalents | 6 / 9 | 25 / 46 | 58 / 126 | 103 / 230 |

**What decides it.**
- When we lead in max health per body at r200 we win 7 of 61 games; when we trail, 6 of 178.
- When we lead in captured gems at r300 we win 8 of 57; when we trail, 5 of 182.
- When they get the first kill we win 6 of 168; when we get it, 7 of 60.
- Across maps our gem share correlates −0.71 with the share of our alive time spent near an enemy, and −0.71 with our deaths.

## 2. Opening (r1-300)

| | us | them |
|---|---|---|
| first body's first camp hit (team, median) | r12 | r11 |
| body first move (mean) | r3.9 | r1.8 |
| median body's first camp hit / bodies with no hit by r50 | r29.6 / 17% | r20.4 / 8% |
| first-hit distance from start | 15.0 | 15.0 |
| team first capture (median) / by r100 | r50 / 79% | r43 / 88% |
| team first bank (median) | r133 | r114 |
| team first middle capture (median) / by r300 | r391 / 46% | r134 / 67% |
| captures r100 / r200 / r300 | 1.8 / 3.8 / 6.0 | 2.4 / 5.6 / 9.3 |
| captured gems r100 / r200 / r300 | 27 / 62 / 102 | 48 / 113 / 192 |
| captured gold r300 | 574 | 1,066 |
| gold held r300 (they bank gold for emblems) | 57 | 262 |
| max health per body r100 / r200 / r300 | 988 / 1,070 / 1,132 | 1,045 / 1,195 / 1,360 |
| deaths r<300 (to camps) | 3.65 (1.07) | 2.00 (0.64) |
| bodies dead at least once before r300 | 53% | 33% |
| engagements r<300 | 4.15 a game: we start 47%, our deaths 0.77 per engagement, theirs 0.42, at a median local max-health ratio of 0.87 | |
| first kill of the game | by them in 168 of 228 games (74%; we then win 3.6%) | |

- **Late start.** Our first move comes at r3.9 against r1.8; rounds 1-3 go to init fuel. The summaries count 10.9 fuel-outs a game
  for us, 2.3 of them after r10; they have none.
- **Late farming.** The median body hits its first camp 9 rounds later at the same distance. Some bodies hit no camp for hundreds
  of rounds (Varg mean first hit r54; `01starfish_84c84f01` Ren r508, see 3.4).
- **The opening is lost at near-equal items.** In r<300 engagements our deaths are 0.77 per engagement against their 0.42, at a
  median local max-health ratio of 0.87. Killers in r<300: camps 1.07, Vesper 0.56, HoR 0.53, Vendetta 0.47, Marcella 0.36.
- **First kills.**
  - Their first kills hit Ren 56, Stellar 35, HoR 22, Varg 20, Ryth 18 and Cassi 16 times.
  - The victim was fighting in 99 and moving in 50. It was alone within 6 in 30% and outnumbered in 37%. Its max health was 0.90x
    the enemies near it.

## 3. Deaths (14.9 vs 6.1; PBG 16.8 vs 3.4)

### 3.1 When, where, how

| per game | us | them |
|---|---|---|
| deaths r<300 / 300-600 / 600-1000 / 1000+ | 3.6 / 4.3 / 4.8 / 2.3 | 2.0 / 1.6 / 1.6 / 0.9 |
| deaths in own half / middle / their half | 7.6 / 4.5 / 1.6 | 2.3 / 2.1 / 1.1 |
| fightan mode: fighting | 5.92 | 2.21 |
| approaching (walked toward the enemy without hitting) | **2.46** | 0.42 |
| fleeing | 2.53 | 1.22 |
| camp | 2.37 | 1.56 |
| walking | 0.77 | 0.21 |
| recalling / stunned / farming | 0.36 / 0.26 / 0.17 | 0.26 / 0.08 / 0.10 |
| champion-kill victims: isolated (alone within 6) / outnumbered within 6 | 32% / 33% | 46% / 53% |
| victim max health / mean attacker max health | **0.63** (median 0.57) | 1.02 |
| local max health within 8 at r-1 (victim side / other) | 0.81 | 0.98 |
| health share 3 rounds before death | 0.51 | 0.28 |
| victim dealt no champion damage in its last 10 rounds | 36% (PBG 48%) | 21% (PBG 8%) |
| in engagements the other side started | 71% | 62% |
| bag lost at death (to champions) | 109 (86) | 79 (62) |

**Victims and killers.**
- Our victims per game: Stellar 3.59, Ren 3.15, HoR 2.11, Ryth 2.07, Varg 2.05, Cassi + Issac 0.95.
- Killing blows on us per game: Vesper attack 3.83, Vendetta attack 2.42, camps 2.37, HoR dash-stun 1.32, HoR attack 1.14,
  Marcella spell 0.82, Marcella attack 0.71, Prism stun 0.41, Prism area 0.38.
- Damage on our dying bodies in their last 10 rounds: Vesper attack 31%, Vendetta attack 21%, HoR dash 12%. Auto-attack carries do
  half of it. 32% of our dead were stunned in their last 5 rounds (stuns over all 239 games: HoR 477, Ryth 227, Marcella 184,
  Tavi 140).

**Our damage is the opposite mix.** Champion damage per game is 13.8k for us and 23.6k for them. Ours is spells first: HoR dash
2.1k, Varg 1.8k, Ryth 1.5k, Ren stun 1.5k, Stellar 1.4k + 1.3k. Theirs: Vesper attack 6.5k, Vendetta attack 4.4k, HoR dash 3.2k.

**How we die (approach, flee, feed).**
- `ff_agg.py` lead-up to kills: our victims made 2.65 closing moves and 2.35 away moves toward their killer in the last 8 rounds.
  Theirs made 1.79 closing and 3.09 away.
- Our bodies die 14 tiles from their own spawn (median); theirs die 18 tiles from theirs.
- **Feeding.**
  - 3.32 of our champion deaths a game (28%) end a life in which the body never damaged a camp; for them 0.48 (12%).
  - 2.22 a game end a life that was also shorter than 60 rounds (them 0.38).
  - Life length before death: median 116 rounds for us, 155 for them (`lifetimes_agg.py`).

### 3.2 Fights we start vs fights they start (`fight_agg.py`, `ff_agg.py`)

| per game | started by us | started by them |
|---|---|---|
| ALL: engagements | 6.7 | **10.0** |
| our deaths / their deaths per engagement | 0.61 / 0.46 | **0.95 / 0.20** |
| PBG | 4.4 (0.80 / 0.23) | 10.6 (1.10 / 0.14) |
| IFish | 6.7 (0.63 / 0.56) | 9.0 (0.97 / 0.20) |
| CM | 9.1 (0.51 / 0.50) | 10.4 (0.77 / 0.26) |

**Who strikes first.**
- In fresh contacts (21.9 a game) we strike first 25%, they 41%, nobody 34%. They are stronger at 60% of contacts; there they
  strike first 44%, we 19%.
- **They strike us first 12.5 times a game.** In the 3 rounds before, our victim had closed the distance in 77% of cases. It already
  had them in reach in 42%, with a spell ready 93% of the time. It was farming in only 7%.
- When we strike first (8.9 a game), their victim was farming 24% of the time.

**In the fight.**
- Our share of first-3-round damage is 0.39. When we win those 3 rounds, deaths are 0.61 / 0.49; when we lose them, 0.94 / 0.20.
- Focus is not the problem: ours 0.85, theirs 0.78. Attackers per engagement are equal (1.81 each).
- **No conversion.** After an engagement our survivors farm 3-4% of the next 15 rounds and make 0.03-0.05 captures within 20.
  Theirs farm 13-16% and make 0.15-0.29 captures, even after engagements we started.
- Idle allies: within 8 of each of our deaths stand 0.87 allies that deal no champion damage in r-5..r (theirs 0.74). 40% of them
  walk toward home and 37% have an enemy within 4 themselves.

### 3.3 Engagements by local max-health ratio (ours / theirs within 8 at the first hit)

| ratio | engagements per game | we start | our deaths / engagement | theirs | kill ratio |
|---|---|---|---|---|---|
| < 0.67 | **7.0** | 33% | 0.94 | 0.17 | 0.18 |
| 0.67-0.87 | 2.2 | 45% | 0.84 | 0.26 | 0.32 |
| 0.87-1.15 | 2.4 | 43% | 0.83 | 0.37 | 0.45 |
| 1.15-1.5 | 1.6 | 50% | 0.67 | 0.45 | 0.68 |
| > 1.5 | 3.3 | 48% | 0.57 | 0.52 | 0.91 |

- 42% of all engagements happen at below 0.67 of their local max health, and 33% of those we start ourselves.
- **Even at parity (0.87-1.15) we lose 2.2 bodies for each of theirs.** Even when we are 1.5x stronger we only trade evenly.
- Vs CM we break even from 1.15 (kill ratio 1.05-1.26). Vs PBG we never do (0.44 at > 1.5).
- Body counts matter little: with 3 more bodies than them, our deaths are 1.16 per engagement.

### 3.4 Replay references

- **Feeding (`01starfish_84c84f01`, vs CM, side a).**
  - From about r30 CM sits on G0, the group next to our spawn.
  - Our bodies walk out and die one at a time: Ren r58, r137, r274, r403; Varg r43, r167, r289, r404; Stellar r36, r170, r277.
  - Ren's four lives deal no camp damage at all (`tools/live/bodylog.mjs FILE 0 1 520`, `lifetimes.mjs`).
- **Farmer walks into an enemy (`00corners_18e7780b`, vs CM, r672-684).**
  - Ren is farming at 982/1,500 health with a 15-gem bag. It walks toward CM's HoR (3,600 max health) and dies at r684; the bag
    goes to HoR.
  - Max health at that point: ours 650-1,500 per body, theirs 1,275-4,100.
- **Other arrivals that ended in a death.**
  - `00monolith_5530cad3` r475-490: Cassi + Issac walk toward Vesper and both die.
  - `01corridors_e0d60e05` r734: Ren walks toward Prism and dies at r740.
  - `00eight_03312e5b` r445: Ryth walks toward Prism and is killed by Vendetta at r458.
- **Approach deaths.**
  - `01starvation_ebe3fe3f` r1431: Stellar, with 650 max health at r1431, walks 7 rounds into a 3,700-health Vendetta.
  - `01hooks_c2560d42` r927: Cassi walks into Prism.
  - `00gemfight_b60b1834` r447: HoR walks into Vesper.

## 4. Economy (camp clears 30.7 vs 56.3)

### 4.1 Time budget (share of all body-rounds; `gapx_agg.py` TIME BUDGET)

| | us r<300 | them r<300 | us r600-999 | them r600-999 | us whole game (rounds per body) | them |
|---|---|---|---|---|---|---|
| dead | 14.5% | 8.0% | 20.8% | 6.0% | 190 | 75 |
| farm (hit a camp) | 16.5% | 23.8% | 9.9% | 18.8% | 125 | 207 |
| fight (hit a champion) | 2.9% | 3.2% | 2.8% | 2.7% | 30 | 30 |
| on a camp tile, still (capture, waiting for respawn) | 2.0% | 5.5% | 1.7% | 7.5% | 20 | 71 |
| tribute / recall channel | 4.6% | 6.6% | 4.6% | 10.2% | 49 | 85 |
| walk | 55.1% | 50.4% | 55.3% | 52.3% | 575 | 540 |
| idle off spawn / on spawn | 3.3% / 1.1% | 2.2% / 0.4% | 3.6% / 1.3% | 2.4% / 0.2% | 36 / 12 | 26 / 3 |

**With and without an enemy near** (share of alive body-rounds; `extra_agg.py` E, `nearbehav.mjs`):

| | us | them |
|---|---|---|
| alive time with an enemy within 8 | 29.8% (r<300 26.8% → r1000+ 34.1%) | 25.9% |
| no enemy near: farm / walk / on camp | 18.7% / 66.0% / 3.0% | 23.0% / 59.1% / 7.4% |
| enemy near: farm / walk / fight / on camp | **4.4% / 73.8%** / 11.3% / 0.8% | **15.9% / 51.7%** / 11.7% / 5.9% |
| enemy near, moving toward / away / sideways from the nearest enemy | 32% / 30% / 13% | 23% / 22% / 9% |
| enemy near, locally stronger (> 1.5x max health within 8) | 34% of those rounds; we still farm 4%, walk toward 42% | 65%; they farm 18% |

**Arrivals.** An enemy comes within 8 of a body that hit a camp in its last 3 rounds.

| | us | them |
|---|---|---|
| arrivals per game (they farm with us around 3x as often) | 10.5 | 34.8 |
| keeps farming (2+ of the next 5 rounds) | **27%** (dies within 20: 11%, captures within 20: 24%) | **53%** (dies 3%, captures 32%) |
| walks toward the enemy | **22%** (dies within 20: 23%) | 9% (dies 5%) |
| holds | 20% | 13% |
| leaves | 11% | 11% |
| recalls | 9% | 8% |
| fights | 9% (dies within 20: 27%) | 6% |

Fighting is the same 11-12% of near-enemy rounds for both sides. The difference is that we stop farming and walk: toward the enemy
(chasing out of reach) or away from it, then back. An enemy within 8 costs us the camp; it does not cost them theirs.

The parallel study of the top teams' own games (`experiments/top2/an_fights.md`, headline points 3, 7 and 8) shows the same rules.
They keep farming when an enemy arrives (58%), leave only below about 35% own health, and chase only wounded targets.

### 4.2 Farming power (`campdps.mjs`, `extra_agg.py` D)

| camp damage per farm round | r<300 | 300-600 | 600-1000 | 1000+ |
|---|---|---|---|---|
| us | 76 | 106 | 132 | 182 |
| them | 82 | 133 | 196 | 249 |
| farm rounds / alive rounds, us | 0.19 | 0.15 | 0.12 | 0.08 |
| farm rounds / alive rounds, them | 0.25 | 0.22 | 0.19 | 0.14 |

**dpf by champion, r<300 → r1000+.**
- Ours: Ren 46 → 82, HoR 62 → 156, Cassi 56 → 82, Issac 54 → 101, Ryth 84 → 193, Stellar 97 → 240, Varg 109 → 372.
- Theirs: Vesper 89 → 325 (IFish 101 → 485), Vendetta 96 → 347, Prism 96 → 387, Marcella 91 → 243, HoR 67 → 162.

**Camp damage per body per game** (platform summaries): ours 10-18k, theirs 19-46k.
- IFish's Vesper does 46k, earns 4,347 gold and collects 548 gems.
- Our best body, Ren, earns 898 gold and collects 135 gems; Stellar earns 513 gold.

**Farming cycles of the groups a team captured** (`grp_cycles` logic, medians):

| | respawn → first hit | first hit → all dead | → captured |
|---|---|---|---|
| own half, us | 37 | 22 | 7 |
| own half, them | 28 | 15 | 6 |
| middle, us | 49 | 21 | 7 |
| middle, them | 28 | 17 | 6 |
| elk groups (kill time), us / them | | 27 / 19 | |
| golem groups (kill time), us / them | | 275 (13 cycles) / 49 (83) | |

**Camp efforts.**
- A camp effort is a run of 3 or more hits on one group with gaps of 15 rounds or less.
- Per game: we start 34.8 and capture 18.4; they start 55.5 and capture 36.1. Our captured share is 50%, theirs 68%.
- They abandon more efforts than we do (19.1 vs 14.9) and still capture twice as many. They simply start and finish twice as many.

**Low-contact games** (both sides 4 deaths or fewer: 29 games, mostly rows, big_world, ambush, expanse, quadrants).
- Camp gems per round: us 0.82, them 1.20. We lost 28 of the 29.
- Farm share is 20.5% vs 24.8%, walk 61% vs 56%, dpf 110 vs 132.
- Monoliths 24 vs 146 gems a game, golems 13 vs 70.
- So even uncontested, our farming engine is about 30% slower than theirs (`extra_agg.py` H).

### 4.3 Where: middle and objectives (`gapx_agg.py` ZONES / KINDS)

| per game | us captures / gems | them |
|---|---|---|
| own half | 14.9 / 273 | 20.4 / 403 |
| middle band | **4.8 / 126** | **16.0 / 594** |
| their half | 0.8 / 15 | 3.1 / 58 |
| elk groups | 8.0 / 244 | 18.3 / 647 |
| wolf | 9.4 / 106 | 15.2 / 162 |
| clusters | 3.1 / 41 | 5.1 / 84 |
| golems (6 golem maps: per game there) | 0.42 caps, first r401 | 2.64 caps, first r221 |
| monoliths (16 monolith maps) | 0.14 caps | 1.39 caps |

**Time in the middle band.** Ours is 17% of body-time against their 24-33%. Farming in the middle is 2.5-3.3% of body-time against
7%. The middle share of their gems grows by phase: 91 → 151 → 232 gems per phase window, against our 26 → 33 → 38.

**Objectives.**
- 00contest: the 2 monoliths are the only gem source (gold clusters otherwise). We hit them 0 times in 6 games; they capture 5-8
  monoliths a game.
- 00quadrants golems: they capture 2-6 a game, we capture 0 (hits 17-78 vs 168-329).
- 00split golems: 1-3 for us vs 5-6 for them.

### 4.4 Banking cadence and bags (`strat_bank.mjs`, `chanpunish.mjs`)

| per game | us | them |
|---|---|---|
| banks (tributes completed) | 11.7 | 25.2 |
| mean gems per bank | 35 | 62 (PBG 86) |
| tributes under 50 gems (mean bag) | 10.4 (19) | 20.0 (20) |
| tributes of 50-99 / 100-199 / 200+ | 1.24 / 0.15 / 0.13 | 4.28 / 0.77 / 0.98 |
| our 200+ tributes | done 40%, killed 17%, locked 20% (vs IFish: 35% locked; 54% of those with an IFish body within 8) | done 66% |
| max bag carried | 84 | 229 (PBG 376) |
| body-rounds carrying 150+ gems | 37 | 145 (PBG 326) |
| bags lost at death | 109 | 79 |
| gems carried at the game's end | 45 | 36 |
| altar locks placed | 0.1 | 2.0 (CM 4.2, PBG 0.0) |

**Maps where we almost never bank.** All of them have contested altars:

| map | banks per game | first bank (mean) | bags lost per game |
|---|---|---|---|
| 00road_of_riches | 0.7 | r1471 | 230 gems (206 to them; captures there 332 gems) |
| 01hooks | 0.5 | r1383 | |
| 01elk_arena | 0.2 | r1703 | |
| 00stampede | 0.5 | r1906 | |
| 01shortcut | 2.5 | | 343 |

- **00road_of_riches.** Its two altars sit in the walled centre box between both roads (`tools/replay/mapinfo.mjs
  maps/00road-of-riches.map26a`). g8's `altar_unsafe()` refuses an altar where an enemy was seen recently unless an ally stands
  within 5. `bag_needs_escort()` holds bags of 60+ for 2 escorts, and `bank_min()` raises the threshold with trip length. So bags
  ride around until they die.
  - In `00road_of_riches_993a47ff` (vs CM): 1 bank (70 gems) in 739 rounds, against 34 banks for CM. Our bags of 22-78 die in the
    middle (`tools/live/narrate.mjs FILE 0`).

### 4.5 Gold, items, max health (`extra_agg.py` A-C, G)

**Gold income.** Ours: 3,232 = captures 2,354 + kills 413 + other 465. Theirs: 8,502 = 5,734 + 1,177 + 1,591. "Other" covers
Marcella's 2 gold per tributed gem and similar. Their kills alone pay for 26 shards a game more than ours.

| item spend | us | them |
|---|---|---|
| by stat | Focus 39-47%, Health 33-36%, Strength 19-25% | PBG Health 51% / Strength 34%; IFish Strength 73% (Power 53%); CM Strength 51% / Health 34% |
| by family | Bruiser 42-51%, Monster 14-20%, Jungle 13-15%, Treasure 11-13%, Durability 9-13% | PBG Bruiser 80%; IFish Power 53%, Bruiser 30%; CM Bruiser 74% |
| first purchase | Jungle Shard of Health (576 bodies), Monster Shard of Focus (258), Monster Shard of Strength (207) | Treasure Shard (health or strength) on 262 IFish bodies and 302 CM bodies; PBG: Jungle Shard of Strength 141, Durability Shard of Health 76, Bruiser Shard of Strength 67 |

**Max health per body type, r100 → r300 → r600 → r1000** (dumps):

| | r100 | r300 | r600 | r1000 |
|---|---|---|---|---|
| our Stellar | 654 | 662 | 725 | 927 |
| their Prism (same caster class) | 747 | 960 | 1,555 | 2,457 |
| our Ren | 1,040 | 1,267 | 1,585 | 2,087 |
| our HoR | 1,117 | 1,341 | 1,573 | 2,051 |
| their HoR | 1,079 | 1,448 | 2,267 | 3,670 |
| their Vesper | 1,043 | 1,470 | 2,340 | 3,617 |
| their Vendetta | 1,161 | 1,533 | 2,292 | 3,360 |
| their Marcella | 1,236 | 1,656 | 2,571 | 3,561 |

Our Stellar buys focus and is our most killed body (3.6 deaths a game).

## 5. Movement pathologies (`gapx.mjs` mv, per body per game)

| per body per game | us | them |
|---|---|---|
| A-B-A rounds (back where it was 2 rounds ago) | **36.1** (23.7 with an enemy within 8) | 16.9 (10.0) |
| loops (8 moving rounds, net displacement ≤ 2) | **45.2** (27.0 with an enemy near) | 15.0 (7.5) |
| idle runs ≥ 4 rounds off spawn, not ending in a capture | 30.5 | 29.8 |
| stand-stills ≥ 40 rounds off spawn | 0.05 | 0.09 |
| idle on own spawn beyond 3 rounds | 5.4 | 2.5 |

**Walk rounds by the next action** (r<1000, per body; `walks` logic):

| next action | us | them |
|---|---|---|
| farm | 263 | 308 |
| **fight** | **119** | **61** |
| died | 20 | 4 |
| recall | 33 | 23 |
| bank | 40 | 42 |
| capture | 6 | 13 |

- **The pathology is the dance near enemies, not getting stuck.** The long stand-stills of earlier versions (capture deadlocks,
  pockets) are rare in S0.
- **Oscillation.** 2/3 of our A-B-A and loop rounds have an enemy within 8. We walk to fights twice as much and walk to our own
  death 5x as much.
- **Recalls.** We recall less than they do (34 vs 49 a game) and rarely under pressure: 1.2 a game within 5 tiles of an enemy,
  against their 5.6.
- **Fuel-outs** (summaries only): 10.9 a game, 2.3 of them after r10. The worst maps are road_of_riches 53.8, fracture 44.0,
  islands 41.2, lanes 38.0 and yellow_brick_road 33.8.

## 6. Per map and map type (`extra_agg.py` I)

| map | our gem share | wins | deaths us/them | alive time near an enemy | their middle-gem share | gem rate | banks us |
|---|---|---|---|---|---|---|---|
| 01boss_battle | 0.63 | 4 | 8.0 / 19.7 | 0.19 | 0.24 | 16.7 | 3.7 |
| 00rows | 0.44 | 1 | 1.8 / 1.0 | 0.03 | 0.31 | 6.7 | 35.2 |
| 01yellow_brick_road | 0.42 | 2 | 16.8 / 10.5 | 0.34 | 0.17 | 9.2 | 27.0 |
| 00expanse | 0.41 | 1 | 4.0 / 3.8 | 0.06 | 0.21 | 6.7 | 38.0 |
| 00quadrants | 0.41 | 0 | 3.5 / 2.5 | 0.19 | 0.55 | 14.8 | 15.8 |
| ... (full table in `extra_agg.txt`) | | | | | | | |
| 00gemfight | 0.03 | 0 | 14.7 / 1.8 | 0.56 | 0.83 | 4.0 | 2.3 |
| 00road_of_riches | 0.02 | 0 | 12.3 / 2.0 | 0.38 | 0.68 | 17.1 | **0.7** |
| 01hooks | 0.01 | 0 | 34.5 / 6.5 | 0.64 | 0.58 | 1.6 | 0.5 |
| 01elk_arena | 0.00 | 0 | 37.8 / 10.5 | 0.71 | 0.87 | 1.3 | 0.2 |
| 00contest | 0.00 | 0 | 31.8 / 8.8 | 0.49 | 1.00 | 2.7 | 0.0 |

**Correlations of our gem share across the 40 maps:**

| feature | r |
|---|---|
| alive time near an enemy | **−0.71** |
| our deaths | **−0.71** |
| their middle-gem share | −0.55 |
| gem rate | +0.48 |
| gold rate | +0.62 |
| camp health on the map | +0.56 |
| their deaths | 0.00 |

| map group | our share | alive time near an enemy | deaths us / them | their middle share |
|---|---|---|---|---|
| closest 8 maps | 0.42 | 13% | 6.6 / 5.2 | 30% |
| worst 12 maps | 0.04 | 49% | 23.3 / 6.8 | 71% |

The worst 12 are contest, elk_arena, hooks, road_of_riches, gemfight, starfish, fragment, starvation, eight, shortcut, gem_fields
and stampede.

**Map classes.**
- Gem rate < 4 (12 small or scarce maps): our share 0.11, 1 win.
- Area < 1,000 tiles (7 maps): share 0.10, 0 wins.
- Gem rate ≥ 11 (11 rich maps): share 0.30, 6 wins.

We are closest where the map lets both teams farm apart. We collapse wherever gems must be taken next to the enemy.

**Our 13 wins** (`extra_agg.py` J). Most come from opponent failures or from fights we won:
- **boss_battle x4.** CM banked 0 gems twice (9 of their deaths to the boss camps, `01boss_battle_193b7288`). Two were huge bag
  swings vs IFish: 1,673 and 5,677 gems lost in bags.
- **Fights won vs CM and IFish:** `00collision_74eb3ba7` (kills 25-4), `01yellow_brick_road_139d7c6e` (29-2),
  `00lost_world_232f53c7` vs IFish (46-10).
- **PBG's Prism never banked** 539 gems on `01yellow_brick_road_8f721512`.
- **One pure farm-race win:** `00rows_e7a32f52` vs IFish, 1005-760.

Low-contact farm-race losses for comparison: `00rows_1c7779de` vs PBG, 810-1185 with 1 death; `00expanse_eaef6866` vs IFish,
585-1037 with 0 deaths.

## 7. Per opponent

**prism best girl (1-79): out-itemed and out-tributed.**
- **Draft.** Prism 80, Vesper 74, Marcella 70, HoR 64, Ryth 42, Vendetta 30.
- **Build.** Bruiser 80% of spend (health 51%). First buys Jungle strength / Durability health / Bruiser strength; never Treasure.
- **Items.** Max health per body 2,402 vs our 1,286 at r600 and 3,788 vs 1,587 at r1000. In 72% of their near-enemy rounds they
  are locally 1.5x stronger.
- **Deaths.** Ours 16.8 a game, theirs 3.4; only 2.1 of theirs are kills by us.
- **Killers.** Vesper attack 3.9, Marcella 3.3 (spell 2.1), Prism 2.8 (stun 1.2, area 1.1), HoR 2.4, camps 2.8.
- **Fights.** They start 10.6 engagements a game, costing us 1.10 bodies each against their 0.14. They strike first at 48% of
  contacts, we at 20%. Our victim max health is 0.51 of its attackers'. 8.9 of our 16.8 deaths are in our own half.
- **Tributes.** PBG banks small bags early (first bank r131). Then the Prism carries: max bag 376, 326 body-rounds a game with
  150+ gems.
  - 200+ tributes: 1.3 a game, mean 442 gems, 36 turns, 72% completed.
  - We are within 8 during 76% of them, yet hit 6%, stun 6% and lock 1%. Stun or lock cancels a tribute; damage does not.
  - Examples: `01corridors_420276a6` r770 (Prism, 652 gems, our Ren within 3: done); `00quadrants_b3b5d540` r545 (367 gems, our
    HoR within 4: done).
  - On `00contest_46992da6` and `00contest_b57c49e6` our Ren did stun the 800-1,000-gem Prism tributes, which delayed them about
    50-220 rounds.

**Intercontinental Fish (5-75): a Vesper hyper-carry with Power strength.**
- **Draft.** Vesper, Vendetta and HoR always; C&I 66, Ryth 42, Varg 12.
- **Build.** Treasure first (262 bodies), then Power (53% of spend, strength 73%).
- **Vesper.** Earns 4,347 gold, collects 548 gems, deals 46k camp damage and gets 4.95 kills a game.
- **Killers.** Vesper attack 4.94 and Vendetta attack 3.59: 44% and 31% of the damage on our dying bodies.
- **Bag swings.** Bags lost: ours 169, theirs 124. They lock 54% of our 200+ tributes.
- **We do kill them.** Their deaths are 7.2 a game; their C&I die 2.32 times each.
- **Recalls under pressure.** 7.7 a game within 5 tiles of us, 59-73% completed; we hit 9-22% of them.
- **Fights.** When we start an engagement we trade nearly evenly (0.63 / 0.56). When they start, 0.97 / 0.20.

**Claudus Maximus (7-72): the most contact, our best matchup.**
- **Draft.** Vesper, Vendetta and HoR always; Tavi 67, Marcella 51.
- **Build.** Treasure first, Bruiser 74%, strength 51%.
- **Contact.** The most of the three: 25.4 contacts and 19.5 engagements a game.
- **Fights we start are even** (0.51 / 0.50). Above a 1.15 local ratio we win (kill ratio 1.05-1.26). Our kills vs CM are 6.6 a
  game, mostly by HoR (2.39).
- **Killers.** HoR 3.13 (dash-stun 1.94), Vendetta 2.99, Vesper 2.67, Tavi 1.48.
- **Banking.** CM banks 31.3 times a game, almost all under 50 gems, and places 4.2 guard locks a game.
- **Our 7 wins** are CM failures (boss_battle 0-gem games) and fight wins.

## 8. Findings, ranked by cost

Costs are estimates per game and they overlap (see section 0). "At our yield" means 0.72 gems per farm round or 6.9 gems per 1,000
camp damage.

1. **Contact reflex: an enemy within 8 stops our farming.**
   - With an enemy near (30% of our alive time) we farm 4.4% vs 15.9% and walk 74% vs 52% (toward 32%, away 30%).
   - Even 1.5x locally stronger we farm 4% and walk toward the enemy 42%.
   - Arrivals at farmers: we keep farming 27% vs 53%. 22% of our farmers walk toward the enemy, and 23% of those die within 20
     rounds.
   - **Cost:** about 100-150 gems a game (136 farm rounds at 0.72-1.11 gems) and about 2 deaths a game ("approaching" deaths 2.46
     vs 0.42).
   - **Why:** `combat()` takes the turn as soon as an enemy is perceived. It chases out of reach or flees (fight_back_margin 0.873,
     outmatch_flee_adv 0.8, ml2 leave/flee 0.2), and `group_score`'s threat veto (target_threat_adv 1.49) drops the group.
2. **Item gap from a third of their gold, spent on focus.**
   - Gold: 3,232 vs 8,502 (captures 2,354 vs 5,734, kills 413 vs 1,177).
   - Items: 25 vs 46 shard equivalents at r300, 58 vs 126 at r600. Max health per body 1,360 vs 2,068 at r600 and 1,733 vs 3,122 at
     r1000.
   - Our spend is 39-47% focus. Stellar stays at 650-927 health all game.
   - 42% of engagements start below 0.67 of their local max health: 7.0 a game, 0.94 of our deaths each.
   - dpf falls behind after r300: 132 vs 196 at r600-1000.
   - **Cost:** about 110-120 gems a game from dpf alone (their dpf on our farm rounds: +117 gems), plus most of the 6.6 deaths a game
     in low-power engagements.
3. **Excess deaths.**
   - 14.9 vs 6.1 a game. Dead 17.9% vs 7.4% of body-time.
   - Mode excess per game: fighting +3.7, approaching +2.0, fleeing +1.3, camps +0.8, walking +0.6.
   - Victims average 0.63x their attackers' max health. 36% deal no damage in their last 10 rounds.
   - **Cost:** about 55-90 gems a game of lost alive time (528 extra dead body-rounds), 86 bag gems handed to them, and about 760
     gold of kill money to them (1,177 vs 413).
4. **They open the fights, and we do not answer or convert.**
   - They start 10.0 engagements a game vs our 6.7. Their openers cost us 0.95 bodies each against their 0.20.
   - At even local power we still lose 0.83 vs 0.37.
   - In 77% of their openers our body had walked into range; in 42% it could have struck first.
   - After engagements we farm 3-4% and capture 0.03-0.05; they farm 13-16% and capture 0.15-0.29.
   - **Cost:** about 3.4 of our deaths and about 2.6 of their deaths a game, if their openers went like ours.
5. **Uncontested farming is about 30% slower.**
   - With no enemy near: farm 18.7% vs 23.0%, walk 66% vs 59%.
   - Respawn → first hit 37 vs 28 rounds; kill time 22 vs 15 (elk 27 vs 19); on-camp holding 3% vs 7%.
   - Captured share of camp efforts 50% vs 68%. Init fuel delays the first move to r3.9.
   - Low-contact games: 0.82 vs 1.20 camp gems a round; we lost 28 of 29.
   - **Cost:** about 100 gems a game.
6. **The middle and the objectives are surrendered.**
   - Middle band 126 vs 594 gems a game. First middle capture r391 vs r134. Middle time 17% vs 24-33%.
   - Monoliths 0.14 vs 1.39 captures a game on 16 maps; 00contest: 0 monolith hits in 6 games.
   - Golems 0.42 vs 2.64 on golem maps; golem kill time 275 vs 49 rounds.
   - **Cost:** −468 gems a game is where findings 1-3 bite. The independent part is objectives (−138) plus target value (−85: 6.9 vs
     7.8 gems per 1,000 damage).
7. **Bags die instead of being banked.**
   - We lose 109 gems a game in bags (86 to their champions). We bank 11.7 times at 35 gems against 25.2 times at 62.
   - Contested-altar maps never bank: road_of_riches 0.7 banks a game, first bank r1471, 230 gems lost; hooks 0.5; elk_arena 0.2;
     stampede 0.5; shortcut loses 343.
   - Our 200+ tributes fail 60% (IFish locks 35% of them).
   - **Cost:** about 110 gems a game (86 of them become theirs). It is near-total on those maps.
   - **Why:** `altar_unsafe()`, `bag_needs_escort()` and `bank_min()`.
8. **Draft and build make glass bodies and weak farmers.**
   - Ren and Stellar are in every game. They are our top victims: Stellar 3.6 deaths a game, Ren 3.2. C&I die 4.75 each when
     drafted.
   - Ren's dpf is 46-82 (their carries 89-485). Stellar has 650-927 health all game.
   - Their kills come from auto-attack carries (Vesper and Vendetta do 52% of the damage on our dying bodies); our damage is spell
     bursts.
   - Ren/Stellar were nerfed in 3.0.4. The champion logit on 4,300 ranked games puts Ren −0.13 and Stellar −0.11, Prism +0.26 and
     Vesper +0.19.
   - **Cost:** about 1.5-2 deaths a game, plus part of finding 2's dpf gap.
9. **Feeding after respawn.**
   - 3.32 champion deaths a game end a life with no camp damage (28%; them 12%). 2.22 a game also end within 60 rounds of the
     respawn (them 0.38).
   - We die 14 tiles from our spawn; they die 18 tiles from theirs. 7.6 of our deaths a game are in our own half.
   - Example: `01starfish_84c84f01`, where 4 consecutive Ren lives, with no camp damage, end at the group next to our spawn that
     CM holds.
   - **Cost:** about 1.8-2 deaths a game (about 200 gold to them).
10. **The opening is lost before items differ.**
    - Equal first hits (r12 vs r11); first capture r50 vs r43.
    - But by r300: 6.0 vs 9.3 captures, 102 vs 192 camp gems, 574 vs 1,066 captured gold, and 3.65 vs 2.0 deaths (camps 1.07 vs
      0.64).
    - Opening engagements: 0.77 vs 0.42 deaths each at a median ratio of 0.87.
    - The first kill is theirs in 74% of games, and we then win 3.6%.
    - **Cost:** −90 camp gems and about −490 captured gold by r300. Everything later compounds on it.
11. **Their channels go unpunished.**
    - PBG's 200+ tributes (1.3 a game, 442 gems, 36 turns) complete 72%. We are within 8 for 76% of them but stun or lock 7%.
    - We place 0.1 altar locks a game; they place 2.0.
    - Their recalls within 5 of us: 5.6 a game, 67-71% complete; we hit 12-29%.
    - **Cost:** about 300 PBG gems a game banked in 200+ tributes with our bodies within 8 and no stun or lock. That is delay value
      only: a cancelled tribute keeps the bag.
12. **Dancing near enemies.**
    - A-B-A 36 vs 17 rounds per body per game, loops 45 vs 15, with 2/3 of both near enemies.
    - Walk-to-fight 119 vs 61 rounds per body (r<1000); walk-to-death 20 vs 4.
    - Long stand-stills are rare (0.05 per body).
    - **Cost:** about 50 body-rounds per body per game (about 25 gems), mostly inside finding 1.
13. **The collapse is map-driven by forced contact.**
    - Our share correlates −0.71 with near-enemy time and −0.71 with our deaths (0.00 with theirs).
    - Worst 12 maps: 49% contact, 23.3 vs 6.8 deaths, share 0.04. Closest 8: 13% contact, share 0.42.
    - Most of our 13 wins are opponent failures (boss_battle, PBG's unbanked 539-gem Prism) or fight wins vs CM/IFish.
    - **Cost:** no separate cost; it shows where findings 1-4 dominate.

## 9. Reproduce

```
python tools/top2/gap/sides.py
python tools/top2/gap/compact_agg.py
bash tools/top2/gap/run_all.sh      # decode cache (~20 min, 3 workers) + gapx, killers, fightan, strat_bank, idleallies, fightfirst
bash tools/top2/gap/run2.sh         # gapx (re-run), campdps, chanpunish, nearbehav, lifetimes
bash tools/top2/gap/tables.sh       # every table above -> C:/battlecode/cache/gap_g8/*.txt
```
