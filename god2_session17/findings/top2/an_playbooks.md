# Playbooks of the six study teams (top2 study, Oct 23)

How each of the six strongest teams plays a whole game, from round 1 to the end, on each map type. What each team does that the
others do not. How each one holds its rating. What all six share, which is probably what it takes to win at this level. Every
number comes from replays of the teams' **current** bots: ranked games of Oct 23, ~07:00-15:00 UTC.

Notation:
- **[M]** = measured directly from the replays. **[I]** = inferred, i.e. an interpretation or a causal reading of a measured
  association.
- **S|O** = study team | its opponents in the same games. Most opponents are other top-50 teams; pbg, IFish and Pantheon also
  play each other.
- Replay references are `<key>/<file>` + round. The replay is `C:/battlecode/cache/t2/<key>/<file>.repl26a` and the dump is
  `C:/battlecode/cache/t2dump/<key>/<file>.json.gz`.

## 0. Data, method, definitions

| key | team | ladder (rating) | sample games | W-L | 150 newest ranked: won / Elo-expected | most frequent opponents in the sample |
|---|---|---|---|---|---|---|
| pbg | prism best girl | #1 (2269) | 116 | 71-45 | 63% / 64% | Pantheon 11-10, IFish 10-9, procless 12-7, :3 11-4 |
| ifish | Intercontinental Fish | #2 (2235) | 110 | 66-44 | 57% / 58% | pbg 9-11, :3 10-8, procless 12-5, policy wonk 10-6 |
| pantheon | Pantheon | #6 (2160) | 105 | 52-53 | 52% / 49% | :3 10-9, pbg 7-10, IFish 8-9 |
| coo | conqueror_of_openai | #18 (2014) | 101 | 55-46 | 59% / 55% | Mite 7-5, hello 5-5, NTU 6-3, EMPEROR Tung 6-3 |
| cm | Claudus Maximus | #19 (2012) | 106 | 58-48 | 53% / 53% | NTU 6-8, the ruliad 9-4, caterpillow 8-3, coo 6-3 |
| nyx | Nyx | #31 (1955) | 100 | 49-51 | 52% / 49% | EggsAfter11AM 9-6, AlphaSlop 4-5, Ad Astra 3-6 |

**Games** [M]
- 638 games on all 40 maps, both sides. One file is one platform match; sides and results come from `t2/<key>/index.jsonl`.
- Seven games are deterministic rematches: same bots, map and side give an identical replay.
  - They are removed from the paired, map-class and rule analyses (`pb_common.py`, `pb_class.py`, `pb_rules_agg.py`).
  - The descriptive tables (`pb_tables.py`, ≤3 per team) and the narratives keep them.
- The "150 newest ranked" column comes from `experiments/live/lists/wr/<teamId8>.jsonl` and is scored with the current ratings
  (`ladder_now.json`).
- Win-rate denominators per map class always come from the sample unless "150 games" is stated.

**Tools** (new, `tools/top2/playbooks/`; outputs in `C:/battlecode/cache/top2_playbooks/`)
- `pb_extract.mjs`: per-game, per-team features from the fight dumps, using the walking-distance map geometry in
  `C:/battlecode/cache/an_strategy/mapgeo2.jsonl`. That geometry matches every t2 map exactly (0 missing / 0 extra camps,
  checked by `geocheck.mjs`).
- `pb_flat.py` → `flat.pkl`; `pb_tables.py`: phase / opening / economy / fights / objective / endgame tables and the
  distinctiveness ranking.
- `pb_class.py`: map classes. `pb_common.py`: paired in-game S−O differences against the result.
- `pb_roles.py`: champion roles. `pb_ladder.py`: rating bands and map classes over 150 ranked games. `pb_items.py`: final builds
  from the compact summaries.
- `pb_rules.mjs` + `pb_rules_agg.py`: tribute, objective, lead and carry contexts.
- `pb_parked.mjs` / `pb_holds.mjs` + `pb_parked_agg.py`: bodies that stand still for long periods.
- `pb_story.mjs`: a dump-based phase story of one game. `pb_moment.mjs`: a key-moment viewer.
- `pb_select.py`: picks the 72 narrated games and writes `stories/<key>/<file>.txt` (pb_story + `tools/live/narrate.mjs`).
- `pb_digest.py`: a 5-line digest of each narrated game.

**Definitions**
- **Zone**: by the walking-distance share f = d_own / (d_own + d_enemy), using BFS from both spawns. Own < 0.4, mid 0.4-0.6,
  their > 0.6.
- **Phases**: r1-100, r101-300, r301-600, r601-1000, r1001+.
- **Activity** of a living body-round:
  - bank = in a tribute channel;
  - fight = dealt champion damage;
  - farm = damaged a camp;
  - walk = moved;
  - home = standing on its own spawn;
  - idle = anything else.
- **Cluster**: the largest set of living off-spawn bodies connected within Chebyshev 6. "≥3 together" = share of rounds with a
  cluster of 3 or more.
- **Captures**: CaptureGems events, mapped to the camp group (cardinally connected camps) and classed mono > golem > elk > wolf >
  cluster.
- **Max HP**: the sum of the team's max health, i.e. item power. "Score" = banked gems.
- **Locks**: guard = own tribute at that altar within ±4 rounds; offense = enemy tribute running; other = neither.
- **Parked**: ≥60 rounds within 1 tile, off spawn, with no capture or bank (attacks allowed).
- **Hold**: ≥10 rounds with no move and no action.

## 1. Headline

1. **Six behaviours are common to all six teams, and in the same game the side that does more of them wins** [M]. Evidence:
   paired S−O differences in 631 games (§2.1).
   - Walking less. When the study team walks more than its opponent it wins 7-51%; when it walks less, 65-86%.
   - Holding the middle after r100.
   - Taking most of its gems in the middle. Mid-gem share above the opponent's → 68-82% wins; below → 19-40%.
   - Staying in a group of three or more.
   - Out-buying the opponent in max health. Max-HP lead at r600 → 67-94% wins; behind → 21-51%.
   - Dying less. Fewer deaths per 1000 rounds → 71-93% wins; more → 10-35%.
2. **Two macro archetypes split the six** [M]:
   - **Carry-and-cash**: pbg, Nyx, Pantheon. All three draft Prism in every game.
     - The team's largest bag is 100+ at 30-43% of the r≥300 checkpoints, and the Prism holds it 77-94% of those times.
     - The game is closed by one big tribute: the median last bank in wins is 239 gems for pbg and 182 for Nyx.
   - **Steady bankers**: IFish, cm, coo. Median tribute 22-28 gems. The largest bag is ≥100 at only 4-12% of the checkpoints.
     The median last bank in wins is 34-71 gems.
   - The archetype decides how to beat them: deny one channel, or out-race them (§4).
3. **pbg (#1) wins with item power plus one game-ending tribute, and it comes back from behind** [M].
   - Items: max HP r600 9765|8286, r1000 13936|10941. Deaths 7.4|10.8 per game, kills 10.1|6.2.
   - It banks slowly: score at r300 85|100, 16.3 banks a game of 62 gems.
   - Its big tributes (≥150 gems) start at a median own score of 520 and a max-HP ratio of 1.5-1.6.
   - Behind by >100 at r600, it still wins 44% (others 6-18%). When the opponent reaches 500 first it wins 35% (others 14-22%).
   - It is weak on large maps (48% over 150 games) and on 3-player maps (44%). It never places an altar lock.
4. **IFish (#2) is the blob racer** [M].
   - Largest cluster 4.26 in r1-100 and 3.41 in r101-300; others 3.18 and 2.53.
   - Highest gold income: 7608|5636. Its Vesper is a hyper-carry (96% Strength, 21.6 Power items a game).
   - Banks early and steadily: score r300 132|89. It reaches 500 first in 74% of its games.
   - It wins 69% on maps without heavy camps and 46% on objective maps (150 games). It wins 31% of games that go past r1500.
   - Its C&I pair is 56% of its body deaths.
5. **Pantheon wins without items** [M].
   - Max HP r600 6334|8769; gold income 4422|6342.
   - It dies least (5.1 per 1000 rounds), banks most often (26.8 a game, 33 gems each) and spams recall (112 Recall events per
     completed recall).
   - It locks early, takes golems early (success 83%), and carries a Prism bag.
   - In 20% of its games a body is parked ≥150 rounds, usually the Prism. That is 219 parked rounds a game in losses.
6. **coo, cm and Nyx hold their ratings with economy, not fights** [M].
   - coo dies 13.3|8.1 and cm 12.7|11.1 and both still win 54-55%. coo makes 2.4x the purchases of the others; cm places 3.4x the
     wards and 3.6 guard locks a game; Nyx recalls the most (12.2 per body per 1000 rounds) and never locks.
   - All three win mostly against teams ranked 11-47.
7. **Objectives are won by committing bodies, never solo** [M].
   - Successful monolith / golem efforts average 1.8-4.7 hitters (≥2.1 except Nyx's golems); failed ones 1.0-2.9. Every
     team's successes have more hitters than its failures.
   - The team max-HP ratio at the first hit is a median 0.76-1.89 in successes and 0.73-1.16 in failures. Successes are ≥1.0 for
     every team except Pantheon, which takes golems while behind (0.76).
   - Golem success 50-88%; monolith 36-45%. pbg takes 2.38 objectives a game on objective maps vs its opponents' 0.58.
8. **The carry tribute is the most exploitable moment at this level** [M].
   - Per attempt, 400+ gem tributes complete only 4-50%: pbg 22%, IFish 4%, Pantheon 50% (n 24), coo 25%, Nyx 50% (n 10).
     200-400 gem tributes complete 30-76%.
   - Completion falls further with an enemy within 8: pbg 14% (≥400), Nyx 22% (200-400), IFish 6% (≥400).
   - pbg and Nyx never lock, so they cannot guard the channel.
   - On the single-altar map (boss_battle) whole games become bag ping-pong. IFish's Vesper carried 1941-2899 gems that were
     never banked (`pantheon/01boss_battle_e8e1f817` r1657-1731).

## 2. Cross-team comparison

### 2.0 One table [M]

| metric (S\|O) | pbg | ifish | pantheon | coo | cm | nyx |
|---|---|---|---|---|---|---|
| core draft (first pick) | **Prism**, Vesper, Marcella, HoR (+Ryth/Vendetta) | **Vesper**, Vendetta, HoR, C&I (+Ryth/Varg) | **Prism**, Vesper, Marcella, HoR, Willow | **HoR**, Vesper, Varg, Vendetta, Ryth | **Vesper**, Vendetta, HoR, Tavi, Marcella | **HoR**, Vesper, Prism, Marcella, Vendetta |
| largest cluster r1-100 / r101-300 | 3.52\|3.22 / 2.94\|2.59 | **4.26**\|3.23 / **3.41**\|2.45 | 2.92\|3.39 / 2.39\|2.67 | 3.26\|3.36 / 2.47\|2.73 | 3.15\|3.28 / 2.44\|2.63 | 3.01\|3.45 / 2.35\|2.66 |
| ≥3 together r101-300 | 0.61\|0.45 | **0.70**\|0.42 | 0.39\|0.48 | 0.42\|0.54 | 0.42\|0.47 | 0.39\|0.51 |
| mid presence r101-300 / r301-600 | 0.31\|0.30 / 0.35\|0.32 | 0.36\|0.29 / 0.37\|0.32 | 0.32\|0.30 / 0.33\|0.32 | 0.31\|0.32 / 0.36\|0.32 | 0.34\|0.28 / 0.34\|0.31 | 0.29\|0.31 / 0.31\|0.32 |
| enemy-zone presence (all game) | 0.04\|0.02 | 0.04\|0.02 | 0.02\|0.03 | 0.02\|0.04 | **0.07**\|0.04 | 0.04\|0.03 |
| first camp hit (median body) / hitters of the first group | r20 / 3.6 | r19 / **3.9** | r19 / 2.7 | **r41** / 2.2 | r21 / 3.7 | r21 / 2.5 |
| first capture / first mid capture | 80\|55 / 245\|200 | 73\|65 / 193\|235 | 70\|90 / 188\|264 | 84\|89 / 230\|307 | 109\|100 / 270\|303 | 97\|83 / 271\|284 |
| score r300 / r600 (r600 deduplicated) | 85\|100 / 280\|287 | **132**\|89 / **383**\|265 | 112\|83 / 302\|252 | 84\|97 / 273\|292 | 103\|86 / 301\|248 | 79\|79 / 249\|250 |
| captured gems per 1000 rounds | 898\|761 | **929**\|785 | 858\|777 | 773\|726 | 770\|703 | 769\|712 |
| gems per capture / mid-gem share | **32.6**\|21.2 / **0.60**\|0.44 | **33.2**\|22.7 / 0.59\|0.47 | 24.2\|28.5 / 0.48\|0.52 | 25.3\|27.2 / 0.51\|0.47 | 29.0\|28.1 / 0.53\|0.48 | 26.8\|27.0 / 0.52\|0.52 |
| elk / monolith share of captured gems | 0.64 / 0.10 | 0.63 / 0.09 | 0.56 / 0.02 | 0.53 / 0.04 | 0.55 / 0.09 | 0.54 / 0.04 |
| banks a game / gems per bank | 16.3 / **62** | 21.9 / 52 | **26.8** / 33 | 20.1 / 46 | 24.9 / 40 | 19.6 / 47 |
| mean largest bag of the game (holder) | **349** (Prism) | 193 (Vesper) | 288 (Prism) | 128 (Vesper) | 118 (Vendetta) | 181 (Prism) |
| largest bag ≥100 at r≥300 checkpoints | **43%** | 12% | 37% | 5% | 4% | 30% |
| median last bank in wins | **239** | 56 | 40 | 34 | 71 | 182 |
| deaths / kills per 1000 rounds | 6.2\|9.0 / **8.4**\|5.1 | 10.0\|9.5 / 8.8\|8.0 | **5.1**\|9.0 / 8.2\|4.8 | **11.1**\|6.3 / 5.1\|9.9 | 10.1\|9.1 / 8.1\|9.1 | 6.5\|7.7 / 6.4\|5.1 |
| max HP r300 / r600 / r1000 | 6567\|5991 / **9765**\|8286 / **13936**\|10941 | 6660\|5946 / 8371\|8495 / 10124\|11718 | 4932\|6276 / **6334**\|8769 / 8056\|11768 | 5289\|6384 / 7245\|8737 / 9427\|11804 | 5881\|6173 / 8208\|8872 / 12045\|12451 | 6032\|6118 / 8539\|8352 / 11932\|11137 |
| gold earned a game | 6957\|5611 | **7608**\|5636 | 4422\|6342 | 5836\|6849 | 6967\|7152 | 5008\|6523 |
| completed recalls per body per 1000 r | 9.8 | 9.5 | 8.8 | 6.0 | 8.1 | **12.2** |
| Recall events per completed recall | 1.2 | 1.2 | **112** (spam) | 1.2 | 1.1 | 1.2 |
| purchases per body per 1000 r | 15.2 | 15.6 | 14.9 | **37.1** | 16.4 | 14.3 |
| wards per 1000 r | 127 | 141 | 71 | 109 | **364** | 79 |
| altar locks a game (guard) | **0** | 2.87 (1.53) | 4.22 (1.97) | 1.13 (0.88) | **5.56 (3.64)** | 0.03 |
| objective captures a game on objective maps | **2.38**\|0.58 | 1.94\|0.86 | 0.89\|1.46 | 0.92\|1.35 | 1.62\|1.23 | 0.67\|1.28 |
| parked rounds a game (≥60-round parks) | 69 | **6** | **151** | **159** | 11 | 63 |
| hold rounds a game (≥10 still): near a camp / an altar | 101: 72% / 51% | 43: 63% / 56% | 158: 39% / 24% | **376**: 56% / 16% | 50: 81% / 43% | 139: 65% / 35% |
| first to 500: share of games / win% when not first | 45% / **35%** | **74%** / 14% | 47% / 20% | 50% / 22% | 61% / 15% | 41% / 17% |
| win% games < r800 / ≥ r1500 | 69% / 58% | 64% / **31%** | 59% / 43% | 50% / 41% | 62% / 45% | 55% / 54% |

**Map-class records over the 150 newest ranked games** [M]:

| | 3p | 4p | 5p | small | medium | large | objective | no objective | side a / b |
|---|---|---|---|---|---|---|---|---|---|
| pbg | **44%** | 72% | 66% | 66% | 69% | **48%** | 66% | 61% | 71% / 58% |
| ifish | 42% | 64% | 60% | 50% | 58% | 66% | **46%** | **69%** | 60% / 55% |
| pantheon | 41% | 66% | 50% | 58% | 46% | 50% | 54% | 51% | 61% / **38%** |
| coo | 60% | 44% | 62% | 54% | 58% | 67% | 66% | 51% | 54% / 64% |
| cm | 52% | 52% | 53% | 49% | 45% | **76%** | 63% | 45% | 60% / 46% |
| nyx | 50% | **39%** | 57% | 54% | 49% | 53% | 53% | 51% | 52% / 51% |

Map sizes: small = area ≤ 41x41 (17 maps), medium ≤ 3000 tiles (14), large > 3000 (9). Objective = a monolith or golem on the
map.

### 2.1 What is common to all six (likely essential at this level)

Method [M]:
- For each feature, d = S − O in the same game.
- Win% when d > 0 vs when d < 0, per team: `pb_common.py`, output `t_common.txt`.
- A feature counts as common when the sign agrees for all six teams and the gap is large.
- These are associations: some features (banks, gold) are partly outcomes of winning. The **controllable behaviours** are listed
  first.

| behaviour (S − O in the same game) | pbg | ifish | pantheon | coo | cm | nyx |
|---|---|---|---|---|---|---|
| walks more (share of alive rounds walking) | 51% vs 81% | 50% vs 86% | 35% vs 65% | **7% vs 73%** | 17% vs 74% | 24% vs 70% |
| more mid presence r301-600 | 72% vs 51% | 76% vs 32% | 62% vs 37% | 66% vs 42% | 70% vs 40% | 62% vs 37% |
| larger cluster r101-300 | 68% vs 50% | 64% vs 40% | 70% vs 35% | 61% vs 51% | 62% vs 49% | 57% vs 45% |
| more farming r301-600 | 68% vs 57% | 64% vs 56% | 63% vs 40% | 71% vs 37% | 70% vs 38% | 65% vs 27% |
| more captures by r300 | 79% vs 54% | 78% vs 43% | 65% vs 32% | 67% vs 36% | 79% vs 31% | 55% vs 29% |
| higher mid-gem share | 76% vs 40% | 81% vs 37% | 68% vs 24% | 71% vs 32% | 74% vs 30% | 82% vs 19% |
| later first mid capture (worse) | 50% vs 67% | 34% vs 72% | 41% vs 57% | 44% vs 62% | 36% vs 70% | 39% vs 57% |
| later first kill (worse) | 48% vs 70% | 41% vs 71% | 28% vs 67% | 42% vs 74% | 43% vs 68% | 35% vs 64% |
| more max HP at r600 | 73% vs 33% | 67% vs 51% | 94% vs 40% | 85% vs 44% | 90% vs 31% | 68% vs 21% |
| more deaths per 1000 r | 31% vs 79% | 33% vs 88% | 10% vs 71% | 35% vs 93% | 18% vs 92% | 20% vs 84% |
| more purchases per body | 83% vs 42% | 91% vs 37% | 76% vs 30% | 66% vs 20% | 88% vs 26% | 78% vs 38% |
| more completed recalls per body | 72% vs 42% | 64% vs 56% | 62% vs 39% | 69% vs 49% | 81% vs 24% | 52% vs 35% |
| larger share of gems banked at mid altars | 77% vs 44% | 83% vs 17% | 85% vs 29% | 89% vs 54% | 63% vs 33% | 79% vs 15% |
| more objective captures (objective maps) | 78% vs 20% | 52% vs 29% | 67% vs 19% | 89% vs 60% | 86% vs 27% | 100% vs 35% |
| *not common: bodies near the capture* | 64/48 | 62/45 | 56/48 | 49/60 | 49/62 | 71/46 |
| *not common: contested captures* | 65/48 | 58/47 | 53/45 | 50/57 | 54/55 | 44/49 |

Reading [I]. What all six do, and what decides games between them:
1. **Stay on camps in the middle band and keep working them.** Walking share is the strongest single behavioural predictor.
   Within each team the losses have more walking: the win−loss difference is −0.18 to −0.81 SD for all six.
2. **Keep three or more bodies together from r100 to r600.**
3. **Get the first middle capture and the first kill.**
4. **Turn income into max health continuously.** Purchases and recalls to the shop are higher in wins for all six.
5. **Bank at the middle altars.** 61-74% of all banked gems for every team go to altars in the middle band (`bankMidShare`).
6. **Do not die more than the opponent.**

Not common [M]: how many bodies stand at a capture, how contested the captures are, the banking rhythm, locks, wards, recall
style, and the draft beyond Vesper + HoR. Vesper is drafted in 91-100% of every team's games. HoR is drafted in 77-100%.

### 2.2 Team-specific style

Distinctiveness = team mean vs the mean of the other five, in SDs of the pooled distribution (`t_distinct.txt`). Top items [M]:

| team | most distinctive (z) |
|---|---|
| pbg | max HP r600-r1000 (+0.86..+0.96); final-bank size (+0.94); **no locks** (−0.86); cohesion r101-600 (+0.6); bag carried r400-1000 (+0.5..+0.65); low idle (−0.56) |
| ifish | **cluster size every phase** (+0.8..+1.18); gold income r101-600 (+0.85); early max HP r100-200 (+0.8); bodies at captures (+0.76); objective hitters (+0.64); no recall spam |
| pantheon | **recall spam** (+2.5); low max HP all game (−0.6..−0.91); few wards (−0.7..−0.8); early locks r1-300 (+0.8..+0.9); early objective captures (−0.72 on the round); spread (squads +0.64) |
| coo | **purchases** (+1.5..+1.7); holds / idle (+1.0..+1.7); few recalls (−1.0); late first camp hit (+0.58); small first group (−0.68); low max HP (−0.5) |
| cm | **wards** (+1.9..+2.2); guard locks (+1.3); forward presence r1-600 (+0.6..+0.8); tiny bags (−0.5..−0.6); few objective hitters (−0.58) |
| nyx | **recalls** (+0.9..+1.1); no locks (−0.82); few wards (−0.7); solo captures (bodies near −0.87); late objectives (+0.71); low gold (−0.5..−0.67) |

### 2.3 How each holds its rating [M]

- **All six play at their Elo expectation** (actual vs expected over 150 games: 63/64, 57/58, 52/49, 59/55, 53/53, 52/49).
  Ratings have converged. None of them farms weak teams far above expectation, and none collapses against a band.
- **pbg** holds #1 by winning every series against ranks 3-10 (Univardisty 9-1, :3 18-7, procless 16-9, policy wonk 13-7) and
  splitting with IFish (13-12) and Pantheon (10-10). Its losses concentrate on large maps and 3p maps.
- **IFish** splits with pbg and :3 and beats procless, Univardisty and policy wonk. Its expected-score shortfall sits in the
  −100..−200 band: 53% won where 69% was expected.
- **Pantheon** plays mostly higher-rated teams (90 of 150 games against equal or better) and wins 50% of those. Side b is 38%.
- **coo, cm, Nyx** play ranks 11-47. They gain on lower-rated opponents (coo 75% in the −100..−200 band) and lose to
  fight-strong teams (cm vs Zarzorki 1-4, Nyx vs BBL 3-7).

## 3. Playbooks

Each playbook covers:
- **Typical game**: phases with numbers.
- **By map type**: table rows are S|O means; source `t_class.txt`.
- **Distinctive**.
- **Rules**: decision thresholds.
- **Narratives**: wins and losses.
- **Exploit**.

### 3.1 prism best girl (#1) — "items, a carried bag, and the closing tribute"

**Identity** [M]
- Draft: Prism is the first pick in 113 of 116 games. Vesper 94%, Marcella 87%, HoR 77%, Ryth 51%, Vendetta 39%.
- Builds (116 compact summaries):
  - Prism is a health tank-carrier: Bruiser/Durability, 76% Health, 1231 gold.
  - Vesper takes 12.4 Power items (Strength 53% / Health 47%) for 2817 gold.
  - Marcella takes 14 Bruiser items, split Strength / Health / Focus.
- Roles:
  - The team's largest bag is ≥100 at 43% of checkpoints after r300; the Prism holds it 77% of those times (340 of 443).
  - The Prism's mean largest bag is 304. Vesper and Marcella each bank about 30% of the team's gems. HoR, Ryth and Vendetta take 23-29% of the team's deaths each; the Prism takes 17%.

**Typical game** (all maps) [M]
- **r1-100: move as a pack to a big group.**
  - Largest cluster 3.52|3.22, ≥3 together 77% of rounds.
  - First group hit by 3.6 bodies, usually an elk group. First capture r80, later than the opponent's r55: pbg starts on bigger
    groups. 26% mid presence.
- **r101-300: farm big groups and do not bank.**
  - Cluster 2.94|2.59, ≥3 together 61%. Gems per capture 32.6|21.2: elk 64% and monoliths 10% of its gems.
  - First bank r204. Score r300 85|100: behind on score.
  - Max HP already ahead: 6567|5991. The Prism starts carrying.
- **r301-600: win fights with items.**
  - Kills 0.74 vs deaths 0.62 per 100 rounds; the opponent 0.51 / 0.80.
  - Max HP 9765|8286 at r600. 52% of captured gems come from the middle.
- **r601-end: cash in.**
  - Kills 0.97-1.21 per 100 rounds vs 0.53-0.79.
  - Banking jumps from about 100 to **232 gems per 100 rounds after r1000** (opponent 107).
  - Big tributes (≥150; 130 of 210 attempts by the Prism) start at a median r1156, own score 520, max-HP ratio 1.5-1.6, with 2-3
    allies within 8. In 56% of them score + bag ≥ 1000.
  - In wins the last bank is a median 239 gems; the Prism made 45 of 71 last banks.
- Teammates bank their own small bags **at the same altar during the Prism's channel**, as a guard
  (`pbg/00great_wall_7ff33f2f` r928-952).

**By map type** [M]

| class (games) | win | what changes |
|---|---|---|
| 5p small (17) | 76% | fast (r840); 1018 gems / 1000 r; kills 9.4\|4.8; max bag 237 |
| 5p medium (33) | 67% | the carry class: max bag 580, last bank 357, 93 gems a bank; first capture r151 (contest / stampede delay it); mid-gem share 0.70; kills 15\|8 |
| 5p large (26) | 50% | races: kills only 7.2\|6.0, max bag 134, last bank 89, 22 banks; max-HP lead +1600 not converted into kills |
| 4p small (16) | 69% | bloodbath (13 deaths, 13 kills), mid-gem share 0.81 |
| 3p small (14) | 57% | carry (last bank 261), deaths 3.3\|7.9; first mid capture late (r479) |
| 3p medium (the_farm, 3) | 0% | Pantheon x2, procless |
| objective maps (53) | 60% | 2.38\|0.58 objective captures a game |

- Golem efforts succeed 62% (3.8 hitters, first hit r448).
- Monolith efforts succeed 43%: 3.2 hitters in successes vs 1.5 in failures, first hit r900, team max-HP ratio 1.66 vs 1.16.
  pbg takes monoliths late and only with an item edge.

**Distinctive** [M]: the item lead, the big final bank, no locks, cohesion, low idle. pbg is also the best comeback team:
- behind by >100 at r600 → 44% wins (n 32);
- the opponent first to 500 → 35% wins;
- maxHp ahead but score behind at r600 → 61% (n 41).

**Rules (thresholds)** [M] → [I]:
- Do not bank small. pbg's tributes have a median bag of 33; 14% are ≥100 (opponents 4%). Teammates do bank 30-70 gem bags
  near the altar.
- The carrier tributes when score + bag ≥ ~1000, or when the max-HP ratio is ~1.5 and 2-3 allies are within 8.
- Take monoliths only when ahead in max HP (≥1.5x) and with 3+ bodies.

**How it loses** [M]:
- Races on big maps against steady bankers: IFish won big_world, expanse and islands while pbg led max HP by 4.5-9k.
- The opponent controls the only altar or the middle (contest, hooks).
- The Prism dies with the bag: 53 gems lost a game, 68 in losses. In losses the Prism banks 0% of the team's gems.
- No locks: one enemy lock cancels the carry.

**Narratives — wins**
1. `pbg/00gem_fields_3fc2330b` (5p medium, vs Pantheon, 1313-361, r681).
   - Four bodies open on the middle elk: first capture r33 (71 gems), first kill r37.
   - 63% of r101-300 body-rounds are in the middle; 1253 of 1292 captured gems come from the middle.
   - The Prism carries 214 by r150 and 704 by r483. It tributes at an altar on the enemy side and is killed r517 by Pantheon's
     Vesper, which takes 711.
   - pbg's Marcella kills that Vesper r560 (711 stolen back) and tributes 747 at r606-681.
   - Max HP +4560 at r600.
2. `pbg/01starfish_47358525` (5p medium, vs IFish, 1143-202, r1049).
   - Score 8-182 at r400: pbg did not bank for 500 rounds. Max HP +900 at r300 and +4160 at r600.
   - Kills 40-7 over the game, 20-2 after r600.
   - Tributes: Marcella 169 (r505-522), 118 (r698-710), 146 (r929-944); Prism 343 (r1014-1049).
   - IFish's six locks (r138-r962) only delayed it.
3. `pbg/00road_of_riches_77554456` (5p small, golem + monolith, vs IFish, 1238-136, r710).
   - 837 middle gems vs 42; kills 26-3.
   - The Prism carries 486 and starts tributes r622 and r661; the second completes r710.
   - IFish placed 7 locks (r54-r464), none during that channel.
4. `pbg/00great_wall_7ff33f2f` (5p medium, vs policy wonk, 1293-574, r959).
   - No kill until r729: both teams farm their own side (1027 vs 977 own-side gems). Max HP +1400 at r300, +2745 at r600.
   - r820: the Prism starts a 359 tribute at (17,19); r830 policy wonk's Marcella locks the altar and cancels it.
   - r846: the Prism kills that Marcella.
   - Vesper, HoR and Marcella bank 14/59/15/80 at the adjacent altar (17,20) while the Prism, now carrying 483, channels from
     r910 to r959 with 2-3 allies at the altar.
5. `pbg/00ambush_3001d3f1` (5p large, vs policy wonk, 1005-815, r1124).
   - A pure race on 100x100: first kill r497, 20 banks of ~40.
   - Prism finish of 168 at r1107-1124.
6. `pbg/01shortcut_8712e41c` (4p small, monolith, vs Pantheon, 1216-208, r1137).
   - Score 102-158 at r600 but max HP +3890. Kills 13-2.
   - Monoliths at r912 and r1113 (235 gems each, 3 hitters).
   - Banks: HoR 128, Vendetta 172, Prism 203, final Prism 235.
   - The Prism died with 291 at r507, killed by the monolith: it carried near the monolith.
7. `pbg/00fragment_e1ff7810` (3p small, vs IFish, 1001-204, r1668).
   - Slow 3v3. pbg took 458 gems on the enemy half. Kills 29-3, 23-1 after r600, with max HP +7960 at r900.
8. `pbg/01boss_battle_4b1716d2` (5p medium, single altar next to the monolith, vs IFish, 1021-151, r1898).
   - A bag war: pbg made five monolith reward captures (r1076 x2, r1277, r1515, r1736); IFish locked eight times.
   - IFish's Vesper reached 1902 gems and was killed at r1508.

**Narratives — losses**
1. `pbg/00contest_52dbafca` (vs IFish, 0-1000, r1113; the map has only monoliths and gold).
   - pbg won the opening fight (4 kills r35-50), then chased into IFish's half (f 0.79 at r100) and lost 3 bodies r108-121.
   - pbg never captured anything. IFish took the monoliths six times: 4-5 hitters, 200 gems each (r545-1055).
2. `pbg/01hooks_86848f49` (4p small, vs Pantheon, 66-1012).
   - The Prism died r43 in the first fight.
   - Pantheon's Prism camped the central elk with four bodies, carried 121→473 and tributed r1026-1074.
   - pbg died 16 times after r600.
3. `pbg/01concentrated_wealth_83e86a76` (5p large, vs IFish, 287-1007).
   - IFish banked 36 times (762 middle gems). pbg's max HP fell behind (−2640 at r300) and its carry never formed (largest bag 71).
4. `pbg/01the_farm_7f9cccb2` (3p medium, vs Pantheon, 345-1025).
   - pbg led max HP all game (+5280 at r900) but trailed on score (45-283 at r600).
   - Pantheon's Prism banked 528 at r899; pbg's Prism ended with 360 unbanked.
- Parked bodies, measured separately:
  - pbg's Vesper parked 1289 rounds at (34,12) in `pbg/01yellow_brick_road_75c19376` (a win).
  - pbg's Prism parked 1103 rounds at (21,13) with 132 gems (`pbg/01boss_battle_1dc255e3`, a 0-806 loss at r2000).

**Exploit** [I] (from the measured weak spots):
- On large and race maps, bank steadily and avoid the big fight: pbg does not chase across big maps.
- Never let the Prism channel. Stun, lock or kill it at the altar: 200-400 tributes complete 76%, but ≥400 only 22% per attempt
  (14% with an enemy within 8).
- A lock is a 10-gold answer that pbg cannot pre-empt, because it never locks.
- Contest the middle early on 3p and 4p maps (hooks, the_farm).

### 3.2 Intercontinental Fish (#2) — "the blob racer"

**Identity** [M]
- Draft: Vesper is the first pick in every game. Vendetta 100%, HoR 100%, C&I 83%, Ryth 53%, Varg 16%.
- Builds (108 summaries):
  - Vesper is a hyper-carry: 21.6 Power items, 96% Strength, 3474 gold (≈47% of the team's spend).
  - Vendetta: Bruiser, Strength 81%. HoR: Bruiser Health / Focus.
  - Team max HP is therefore low (r1000 10124|11718) even though gold income is the highest (7608|5636).
- Roles: Vesper captures 43% and banks 41% of the team's gems, makes 37% of its kills and only 14% of its deaths.
  C&I's two bodies are 56% of the team's deaths.

**Typical game** [M]
- **r1-100: the blob.**
  - Largest cluster 4.26|3.23 (z +1.18), ≥3 together 83%. The first group is hit by 3.9 bodies, usually elk.
  - First capture r73. First mid capture r193 (Pantheon r188 is the only earlier team).
- **r101-600: farm and bank in the middle, together.**
  - Cluster 3.41 / 3.14, ≥3 together 70% / 63%.
  - Mid presence 0.36-0.37, the highest; mid-gem share 0.59; 33.2 gems per capture.
  - Score r200 72|49 and r300 132|89: the fastest early banking of the six.
  - 21.9 banks a game of 52 gems. Guard locks 1.53 a game, mostly on mid altars.
  - Few holds: 43 rounds a game; the blob keeps moving.
- **r601-end.**
  - Strong r601-1000: 122 banked gems per 100 rounds vs 92.
  - Weak after r1000: 91 vs 140. 31% wins in games past r1500. It reaches 500 first in 74% of games.
  - The Vesper makes most big tributes: 88 of 128 attempts ≥150, completing 48% at 200-400 and 4% at ≥400.

**By map type** [M]

| class (games) | win | what changes |
|---|---|---|
| 5p large (26) | 65% | its best class (150 games: 66%); first capture r53, max bag only 111, 28 banks of 37: pure racing |
| 5p medium (29) | 66% | bigger carry (max bag 365, last bank 112) |
| 5p small (16) | 56% | fastest games (r761); 1072 gems / 1000 r |
| 4p small (14) | 64% | bloody (19 deaths, 14 kills) |
| 3p small (13) | 46% | 3p is its weakest size (150 games: 42%) |
| objective maps (49) | 49% | 1.98\|0.88 objective captures, but golem-only maps 0/4 (quadrants 0/3) |

- Golem efforts succeed 59% with **4.7 hitters** (the blob); monolith 38% with 3.5 hitters.

**Distinctive** [M]: cohesion (biggest effect of any team), gold income, early score lead, bodies at each capture (2.39), no
recall spam, no parking.

**Rules** [M] → [I]:
- Move as one, 4-6 bodies.
- Bank 30-50 gem bags at the nearest mid altar (median tribute 28) behind a guard lock (1.5 a game).
- Contest a monolith or golem with everybody (4.7 hitters on golems).
- When ahead on score, keep racing. It wins 76% of games where it is first to 500.

**How it loses** [M]:
- To item-heavy teams that force fights: pbg, `starfish_47358525` (40 IFish deaths, max HP −10k by r900).
- On golem maps: Pantheon and new team(4) on quadrants.
- In long games, and on single-altar maps where its Vesper's bag is locked out (`pantheon/01boss_battle_e8e1f817`).

**Narratives — wins**
1. `ifish/00contest_52dbafca` (vs pbg, 1000-0).
   - Cluster 4.8 in r101-300; offensive locks r140 and r150.
   - Fights r445-490 kill pbg's Prism (r452), Marcella (r456) and Ryth (r486); pbg's Vesper died to a camp at r490.
   - Then Vesper + Vendetta + Ryth burn the monolith at (17,31) while HoR screens at (30,22); capture 200 at r545.
   - Monoliths taken six times; kills 40-15.
2. `ifish/01big_world_0561a53d` (5p large, vs pbg, 1004-791, r969).
   - No kill by IFish all game; one death at r893. 25 banks.
   - IFish won the race with max HP −8300 at r900.
3. `ifish/00expanse_bc3ff3f2` (5p large, vs pbg, 1004-802, r906).
   - Race again: 29 banks vs 28, max HP −9120 at r900.
4. `ifish/01islands_ace73814` (5p large, vs pbg, 1043-991, r841).
   - Zero IFish kills, 26 banks; won by 52 gems.
5. `ifish/00rushbait_v2_08bc9833` (4p medium, adjacent spawns, altars at the map ends; vs pbg, 1012-376).
   - Guard locks r309, r479, r844. pbg's Prism finished holding 305 unbanked.
6. `ifish/00corners_8ccd80fa` (5p large, vs Pantheon, 1000-261).
   - 66 banks of ~15 gems; 808 middle gems; 3 guard locks. Pantheon's Prism finished holding 578.
7. `ifish/00packs_6e6a3d0d` (3p small, vs pbg, 1010-384).
   - First kill r41; 260-40 at r300; middle gems 834-518.
8. `ifish/00monolith_a05ae120` (5p medium, monolith, vs Pantheon, 1017-393).
   - Ten locks (seven guard), monolith at r816, Vesper's final bank 256.

**Narratives — losses**
1. `ifish/00quadrants_69638af3` (golem, vs Pantheon, 702-1027, r545).
   - IFish takes the first golem at r174 with five hitters.
   - Pantheon takes the middle wolves (169 gems in r401-500) and the second golem (r441), and its Prism banks 255 at r497-523.
2. `ifish/01starfish_47358525` (vs pbg).
   - IFish led 162-8 at r300. pbg's item lead then killed 40 IFish bodies.
3. `ifish/00road_of_riches_77554456` (vs pbg).
   - IFish lost the middle (42 vs 837 gems); its seven locks did not stop pbg's Prism.
4. `ifish/01boss_battle_e8e1f817` (single altar, vs Pantheon, 305-1007, r1938).
   - IFish started 17 tributes. Pantheon placed 10 of the game's 15 locks on the altar (25,20).
   - IFish's carriers died with 477 (r496, to a camp), 1941 (r1657, killed by the Prism) and 2001 (r1731).

**Exploit** [I]:
- Do not fight the blob head-on and do not race it on large maps without heavy camps.
- Take the golems and the monolith. IFish wins 46% of objective maps.
- Pick off C&I (56% of its deaths).
- Drag games long: IFish wins 31% past r1500.
- On single-altar maps, lock the altar during its Vesper's channel.

### 3.3 Pantheon (#6) — "spread, small banks, recall spam, Prism finish"

**Identity** [M]
- Draft: Prism is the first pick in every game. Vesper 100%, Marcella 85%, HoR 80%, Willow 62%.
- Builds (27 summaries): Power family on everyone. Prism Focus 65%. Total spend low.
- Gold earned 4422|6342. Max HP behind all game: r300 4932|6276, r600 6334|8769, r1000 8056|11768.

**Typical game** [M]
- **r1-100: spread.**
  - Largest cluster 2.92|3.39, 2.10 squads. First capture r70; first mid capture r188, the earliest of the six.
  - Banks immediately: 1.12 banks per 100 rounds, first bank r141.
  - Locks mid altars from the start: 0.40 locks per 100 rounds in r1-100, about 5x the others.
  - Recall spam begins at r1: about 4200 Recall events a game, 112 per completed recall.
- **r101-600: avoid deaths, bank small, take golems early.**
  - Deaths 0.33 per 100 rounds (opponent 0.77), kills 0.65 (opponent 0.31).
  - 26.8 banks a game of 33 gems; median tribute bag 15.
  - Golem efforts succeed 83%, with the first objective capture at a median r441. They succeed even at a max-HP ratio of 0.76.
- **r601-end: the Prism finish.**
  - The Prism carries. The team's largest bag is ≥100 at 37% of checkpoints and the Prism holds it 94% of those times. Its mean
    largest bag is 268.
  - Big tributes start at a median r904 at own score 606. The Prism is 62 of 86.
  - Banking after r1000: 205 gems per 100 rounds vs 112.

**By map type** [M]

| class (games) | win | what changes |
|---|---|---|
| 5p small (13) | 69% | 38 banks of 26; 1366 gems / 1000 r; kills 12\|5 |
| 4p small (15) | 67% | |
| 3p medium (the_farm, 3) | 100% | |
| 5p large (26) | 46% | |
| 5p medium (27) | 41% | |
| 3p small (13) | **23%** | its worst class (150 games: 3p 41%) |

- Golem-only maps 4/5. Side b over 150 games: 38%.

**Distinctive** [M]: recall spam, low max HP, few wards (71 per 1000 rounds), early locks, earliest objective captures, spread,
many tiny banks, fewest deaths.

**Parking** [M]:
- 20% of games have a body parked ≥150 rounds, usually the Prism.
- Parked rounds: 219 a game in losses vs 82 in wins.
- `pbg/00gem_fields_3fc2330b`: Pantheon's Prism stood at (10,3) from r216 to r681, holding 64 gems, casting every 7-8 rounds at
  a wolf pair at (6,3)/(6,4) that it never killed.
- `pbg/01big_world_95eb8349` and `pantheon/01big_world_28046592`: the Prism parked at (64,47) for ~1000 rounds from r158.

**Rules** [M] → [I]:
- Recall-cancel every turn, so the body is always one turn from home. The capture-recall combo is used on 42% of captures
  (an_fights).
- Bank every bag (median 15 gems).
- Lock mid altars early: 2.0 guard and 1.9 other locks a game, mostly on mid altars.
- Start golems early, whatever the max-HP ratio.
- The Prism tributes what it carries once own score is ~600.

**How it loses** [M]:
- Item deficit: it is behind on max HP at r600 in 81 of 97 games and wins only 37% of those.
- Its Prism dies loaded: 132 gems lost a game.
- It loses the middle to blobs: stampede 0-1120 and corners 261-1000, both vs IFish.

**Narratives — wins**
1. `pantheon/01hooks_86848f49` (4p small, vs pbg, 1012-66). See §3.1: central elk camp, Prism 473 at r1026-1074.
2. `pantheon/01fracture_35246d93` (5p large, vs pbg, 1018-201).
   - 42 banks of ~24, five locks, kills 13-1.
   - Pantheon's Prism was parked 825 rounds with 30 gems; pbg's Marcella was parked 562 rounds.
3. `pantheon/00quadrants_69638af3` (vs IFish, 1027-702, r545). See §3.2.
4. `pantheon/01boss_battle_e8e1f817` (vs IFish, 1007-305, r1938).
   - Altar lock control: locks r548, r972, r1063, r1182, r1257, r1483, r1503, r1607, r1662, r1897.
   - r1657: the Prism kills IFish's Vesper and takes its 1941 gems. r1662: Vesper locks the altar, cancelling IFish HoR's 434
     tribute. r1671: the Prism starts a 2001-gem tribute (201 turns) and is killed r1729.
   - Pantheon wins with small banks.
5. `pantheon/01the_farm_7f9cccb2` (3p medium, vs pbg, 1025-345). The Prism banks 528 at r899.
6. `pantheon/00lost_world_b74302c8` (5p small, vs pbg, 1001-0, r489).
   - 49 banks, 994 middle gems; kills 12-3 in r1-300.
7. `pantheon/00pilgrimage_8806e3e0` (5p large, vs pbg, 1000-430).
   - Max HP −3720 at r900, yet kills 12-0 after r600. Prism final 339.
8. `pantheon/00swirl_5cd065e4` (4p small, vs IFish, 1066-676).
   - The Prism lost 685 at r911. Pantheon killed IFish's Vesper carrying 700 at r1100 and banked 715 at r1176.

**Narratives — losses**
1. `pantheon/00gem_fields_3fc2330b` (vs pbg, 361-1313). Pantheon's Vesper stole pbg's 704 bag (r517) and lost it again (r560).
2. `pantheon/00stampede_62094520` (vs IFish, 0-1120). The map's 160-gem middle elk was IFish's from r467 on; Pantheon never
   captured anything.
3. `pantheon/00corners_8ccd80fa` (vs IFish, 261-1000). The Prism ended with 578 unbanked; IFish banked 66 times.
4. `pantheon/01shortcut_8712e41c` (vs pbg, 208-1216). Two Prism bags lost (107 at r432, 171 at r1015); pbg took both monoliths.

**Exploit** [I]:
- Win fights by item power: it is behind on max HP in 84% of its games.
- Kill the loaded Prism.
- Treat its "recalling" flag as noise.
- Push side-b games (38%) and 3p maps (23-41%).

### 3.4 conqueror_of_openai (#18) — "slow, idle, heavy buyer, economy"

**Identity** [M]
- Draft: HoR is the first pick in 88 games, Ren in 13. Vesper 91%, Varg 78%, Vendetta 78%, Ryth 67%; Tavi, Ren or Prism
  occasionally.
- Builds: only 5 summaries, so treat this with caution. Power family, Strength 68-74%.
- Purchase events: **37.1 per body per 1000 rounds** vs 14-16 for the others. Each spawn visit buys 3-10 items and leaves under
  30 gold (`coo/01boss_battle_0a537740`).

**Typical game** [M]
- **r1-100.**
  - Late start: the median body's first camp hit is r41 (others r19-21). 20% idle (others 9-15%). 2.2 purchases per body per
    100 rounds.
  - First group hit by 2.2 bodies, the fewest. First capture r84.
- **r101-600.**
  - Farms its own side and the middle. 24% idle; 376 hold rounds a game in 16 runs, 56% next to a camp and 60% in the middle.
    It waits next to camps.
  - Weak fights: deaths 0.96|0.51 per 100 rounds in r101-300; first kill r392 (opponent r305).
  - Max HP behind: r300 5289|6384, r600 7245|8737.
- **r601-end.**
  - Steady banking: 20.1 a game of 46 gems; largest bag ≥100 at only 5% of checkpoints.
  - Wins the race at a median r1131.

**By map type** [M]:
- 5p large 58%, 5p medium 59%, 3p small 58%, 4p small 50%.
- **Objective maps 65% vs 44% without.** Without heavy camps it dies 17 a game vs 10 for the opponent.
- 150 games: large 67%, 4p 44%.

**Distinctive** [M]: purchases, holds and idle, the fewest recalls (6.0 per body per 1000 rounds), late first hit, small first
group, many parked rounds (159 a game, typically 1.2 parks a game).

**Rules** [M] → [I]:
- Shop first, then open with 2 bodies per group (first hit r41).
- Wait next to camps for the respawn: 56% of hold rounds are next to a camp, and 15% of those end with a capture.
- Spend gold below 30 at every spawn visit (3-10 purchases a visit).
- Bank median 28-gem bags, 71% at mid altars.
- Carry only late and rarely: big tributes start at a median r975 at own score 400.

**Narratives — wins**
1. `coo/01boss_battle_0a537740` (single altar + monolith, vs cm, 1082-0, r1099).
   - Own-side elk only; every body hoards: Vendetta 586, Vesper 642 at r1000. Max HP +8850 at r900.
   - Monolith (400) at r943.
   - Vesper tributes 642 (r948-1013) with all five coo bodies within 2 tiles of the single altar (25,20).
   - r1028: Vendetta guard-locks the altar. Varg's 351 completes the game at r1099. cm never banked.
2. `coo/01elk_arena_7521bf78` (vs cm, 1008-0, r1652). All 1008 gems from the middle elk; kills 75-10. cm placed eleven
   offensive locks on coo's channels; coo still banked 34 times.
3. `coo/00great_wall_ae60b5e2` (vs NTU, 1392-838).
   - Own-side farming only (1152 gems). Max HP −3500 at r900.
   - Killed NTU's Vesper carrying 408 (r1013) and tributed 408 itself at r1028-1077.
4. `coo/01big_world_39dc4971` (vs Mite, 1027-877). No kill for 1060 rounds; 36 banks.
5. `coo/00road_of_riches_de452e4d` (vs hello, 1019-0, r585). Race, 26 banks.
6. `coo/01shortcut_e10a1122` (4p, vs EMPEROR Tung, 1017-758). Kills 6-10; won on 680 middle gems vs 281.
7. `coo/01broken_curve_3119b59f` (3p, vs EMPEROR Tung, 1002-991). 26 banks; won by 11 gems.
8. `coo/00expanse_bb4dbd1d` (vs NTU, 1036-536). One kill all game; 30 banks.

**Narratives — losses**
1. `coo/00gemfight_c80d2b6c` (vs cm, 114-1061). Kills 0-15.
2. `coo/00eight_d55c5832` (vs cm, 30-1004). Kills 1-27; cm stood in coo's half (f 0.6-0.7) from r300.
3. `coo/01fracture_74a08ae7` (vs EMPEROR Tung, 346-1029). Max HP −7600 at r900; 15 deaths.
4. `coo/00quadrants_86748521` (vs EggsAfter11AM, 487-1003). Both golems went to the opponent (r409, r509).

**Exploit** [I]:
- Pressure it early: it is idle and buying in r1-100, and its first kill comes at r392.
- Fight it anywhere. It loses 13.3|8.1 bodies a game, and cm beat it 6-3.

### 3.5 Claudus Maximus (#19) — "wards, guard locks, forward, tiny banks"

**Identity** [M]
- Draft: Vesper is the first pick in every game. Vendetta 100%, HoR 100%, Tavi 82%, Marcella 66%.
- Builds (106 summaries): Bruiser on everyone (Vendetta 11.4, Vesper 10.5, HoR 8.2), plus one Treasure and one Jungle item.

**Typical game** [M]
- **r1-100: forward and violent.**
  - The furthest forward at r20 (f 0.32, others 0.23-0.26). 6% of body-rounds in the enemy zone (others 1-3%).
  - The most damage both ways (1444 dealt / 1508 taken per 100 rounds). Deaths 0.73, kills 0.61 per 100 rounds.
  - First capture r109, the latest.
- **Wards, all game.** Every body places a ward each time the 10-round cooldown ends: 434 wards a game, 364 per 1000 rounds.
  In `cm/00great_wall_78b3c219` all five bodies ward every 10 rounds.
- **Guard locks.** 3.64 a game, including on 14-gem tributes: r320 lock, r321 tribute of 14 (`cm/00great_wall_78b3c219`).
- **Banking.** Steady and tiny: 24.9 a game of 40 gems. The largest bag is ≥100 at 4% of checkpoints.
- **Fights.** Keeps farming under pressure (67.5% keep farming when an enemy arrives; an_fights).
- **Objectives.** Taken late (first capture r788) with few hitters (2.4). Golems succeed 88% when attempted (2.5 hitters, score
  lead +345).

**By map type** [M]:
- **5p large 73%** (16/22; 150 games: 76%). Objective maps 65%.
- 3p small 40%, 4p medium 20%, 5p small 47%, 5p medium 50%.
- No-objective maps 47%, with 17 deaths a game.

**Distinctive** [M]: wards, guard locks, early forward presence, tiny bags, few objective hitters, almost never parked
(11 rounds a game).

**Rules** [M] → [I]:
- Every body wards on cooldown.
- Lock the altar before every tribute, even of 14 gems. Median tribute bag 22, 74% of banked gems at mid altars.
- Push forward early and fight for camps on the enemy side (6% of r1-100 body-rounds in the enemy zone).
- Keep farming when an enemy arrives.
- Start golems only when far ahead: successes begin at a score lead of +345.

**Narratives — wins**
1. `cm/00gemfight_c80d2b6c` (4p small, vs coo, 1061-114). Kills 15-0; 43 banks; 3 locks.
2. `cm/00eight_d55c5832` (5p small, vs coo, 1004-30). Holds coo's half from r300 (f 0.6-0.7); kills 27-1.
3. `cm/01fracture_4fc1aa39` (5p large, vs coo, 1017-543). Ten locks (six guard), 31 banks.
4. `cm/01big_world_769dd3c7` (5p large, vs Zarzorki #10, 1005-729). Zero kills by either side; 35 banks; 3 guard locks.
5. `cm/00great_wall_78b3c219` (vs Tartarus #14, 1011-793). Eleven guard locks, 20 banks, own-side farming.
6. `cm/01concentrated_wealth_0eb750bf` (vs Tartarus, 1008-211). 47 banks of ~21; 778 middle gems; kills 22-6.
7. `cm/01the_farm_a9036fb9` (3p, vs hello, 1073-818). 24 banks, 8 locks.
8. `cm/00reverse_spiral_53b13761` (4p golem, vs the ruliad, 1060-156). Six golem captures (r675-1128) and 373 gems from the
   enemy half.

**Narratives — losses**
1. `cm/01boss_battle_0a537740` (vs coo, 0-1082). Never banked at the single altar.
2. `cm/01starfish_2b0b9811` (vs Tartarus, 96-1099). 38 deaths; Tartarus took 979 middle gems.
3. `cm/01elk_arena_221310ac` (vs Zarzorki, 216-1008). 54 deaths, 42 of them after r600.
4. `cm/00fragment_28f9bafa` (3p, vs Zarzorki, 44-1020). Kills 0-38; Zarzorki took 440 gems on cm's half.

**Exploit** [I]:
- Stand just outside its reach and strike first. It walks into fights: 40.5% of its deaths had no hit in the previous 8 rounds
  (an_fights).
- Out-fight it on maps without heavy camps (17 deaths a game there).
- A 10-gold lock does not stop its banking. Kill the banker instead: bags are tiny but frequent.

### 3.6 Nyx (#31) — "spread, recall-capture, late Prism cash-in"

**Identity** [M]
- Draft: HoR is the first pick in every game. Vesper 100%, Prism 100%, Marcella 88%, Vendetta 64%.
- Builds: one summary only. Vesper Power, HoR Bruiser Focus, Prism Health.
- Gold earned is low (5008|6523), but max HP equals or passes the opponent's from r600: 8539|8352; r1000 11932|11137.

**Typical game** [M]
- **r1-100: spread solo farming.**
  - 2.06 squads; 3.3 captures by r100 (opponent 2.3) with 1.33 bodies near each capture, the lowest.
  - The capture-recall combo: kill the camp, step on the reward, start the recall, and the capture lands as the body teleports
    home (`nyx/00ambush_c325017c` r623-631: +33 gems, three purchases).
  - 54% of captures (an_fights).
- **r101-600.**
  - Vesper captures 43% and banks 46% of the team's gems.
  - The Prism carries. The team's largest bag is ≥100 at 30% of checkpoints and the Prism holds it 90% of those times.
  - The most recalls of the six: 12.2 per body per 1000 rounds.
- **r601-end.**
  - Slow games: median r1240 in wins.
  - Big tributes start at a median r1064 at own score 721; score + bag ≥ 1000 in 55%; the Prism is 105 of 139.
  - 200-400 bags complete 30% per attempt, 22% with an enemy within 8.
  - Last bank in wins: 182; the Prism makes 30 of 49.

**By map type** [M]:
- 5p small 71% (10/14), 3p small 56%, 5p medium 50%, 5p large 48%, **4p small 33%** (6/18; 150 games: 4p 39%).
- Objective maps: 0.67|1.28 captures. Golem success 50%, with the first hit at r1024 in successes.

**Distinctive** [M]: recalls, no locks, few wards (79 per 1000 rounds), solo captures, late objectives, low gold.

**Rules** [M] → [I]:
- Farm solo or in pairs.
- Recall on the reward tile during the 5-round capture timer, then shop and walk back.
- Bank median 28-gem bags.
- The Prism keeps 100-450 and tributes once own score is ~700 (median 721); 55% of these tributes would end the game.
- No locks and few wards.
- Objectives only late and when stronger: golem successes have their first hit at r1024 with a max-HP ratio of 1.60.

**Narratives — wins**
1. `nyx/00interlock_424705d2` (4p, vs coo, 1096-636, r1511).
   - Behind 104-234 at r600. The Prism carries 105→403; kills 19-7.
   - Prism tribute of 403 at r1444/1470 wins through four coo guard locks.
2. `nyx/00quadrants_b98ef586` (golem, vs EMPEROR Tung, 1167-519, r530). Both golems (r407, r476); the Prism's 458 tribute at
   r484-530.
3. `nyx/00lost_world_ca07a39c` (5p small, vs FürFortnite, 1227-45, r538). 56 banks, 1219 middle gems.
4. `nyx/01fracture_05679ec9` (5p large, vs Valenki, 1054-722). Race: first kill r916, max HP +4880 at r900.
5. `nyx/00ambush_c325017c` (5p large, vs Nameless, 1053-609, r1465). Slow; Prism final 198.
6. `nyx/00collision_efd4fd81` (3p, vs Ad Astra, 1073-154). The opponent banked only 3 times; Nyx stole bags of 118 and 200.
7. `nyx/00contest_744bba5a` (monolith, vs the ruliad, 1000-200, r1700). Four monolith captures r1132-1657; kills 33-6.
8. `nyx/00swirl_61899d8f` (4p, vs EMPEROR Tung, 1017-15). Kills 43-7, 42 banks, max HP +11940 at r900.

**Narratives — losses**
1. `nyx/01starfish_9ab30d7c` (vs coo, 583-1041). coo took 1102 middle gems and placed five locks (four guard); the Prism's 190
   came too late.
2. `nyx/01broken_curve_a895e2b5` (3p, vs cm, 533-1159). The Prism died with 148 (r810); cm placed 5 locks.
3. `nyx/00gem_fields_83048666` (vs AlphaSlop, 827-1021). A close race lost.
4. `nyx/01elk_arena_70b595d0` (vs EMPEROR Tung, 72-1008). Lost the central elk; 30 deaths.

**Exploit** [I]:
- A Nyx capturer standing still is mid-recall: one hit cancels the recall, and can deny the capture.
- Lock or stun the Prism tribute: no guard locks, and 22% completion with an enemy near.
- Contest objectives: it takes 0.67 a game against its opponents' 1.28.
- Push 4p maps (39%).

## 4. How to beat each archetype (synthesis) [I, from §2-3]

| opponent | its engine | what beats it (evidence) |
|---|---|---|
| carry teams (pbg, Nyx, Pantheon) | one Prism bag + a closing tribute; pbg adds an item lead | (1) Never let the big channel finish: stun / lock / kill. ≥400 tributes complete 22% (pbg) with no help, 14% with an enemy within 8; Nyx 200-400 bags 22% with an enemy near. (2) Bank steadily so the closing tribute arrives too late: first to 500 wins 76-94% for every team. (3) Kill the loaded Prism: Pantheon loses 132 gems a game to that, Nyx 73, pbg 53. |
| blob racer (IFish) | 4-6 bodies together, early banking, Vesper hyper-carry, guard locks | (1) Do not fight the blob; take what it leaves: objectives (IFish 46% on objective maps) and the far side of large maps. (2) Pick off C&I stragglers (56% of IFish deaths). (3) Stretch the game: 31% after r1500. (4) Item lead: IFish's max HP falls behind by r1000 (10.1k vs 11.7k). |
| economy teams (coo, cm) | steady small banks, many purchases / wards / locks, weak fights | (1) Fight them: coo dies 13.3 a game, cm 12.7; their wins come from the race. (2) Hold just outside reach. cm walks in; coo idles next to camps (376 hold rounds a game). |

## 5. Rules for god2

Each rule is a runtime rule over observable state, with its thresholds and the evidence behind it. None is a table per map or
team.

**A. Positioning and tempo** (all six teams; §2.1)

**A1. Middle anchor**
- From r100 to r600, keep more body-rounds in the middle band than the opponent: walking-distance share f in [0.4, 0.6].
  - The six spend 0.29-0.37 of living body-rounds there; their opponents 0.28-0.32.
  - In practice: 2 of 5 bodies on middle groups, or 1-2 of 3-4.
- Prefer camp groups there. Every team takes 48-60% of its gems in the middle, and the side with the higher middle share wins
  68-82% vs 19-40%.
- Score middle groups higher when no enemy cluster of more than our local max HP is within 8.

**A2. Walk budget**
- A body should not walk to a target that is more than about 1.5x farther than the nearest workable group, unless the target is
  ≥2x the value.
- Pick the next target among groups adjacent to the current one.
- Measured: the side that walks more wins 7-51% vs 65-86%. Walking share 0.53-0.60 for the six; their losses walk more by
  0.2-0.8 SD.

**A3. Cohesion floor**
- Keep a group of three or more together (Chebyshev 6) in r100-600 on 4-5-player maps.
- Splits are allowed for one or two bodies to farm adjacent groups, never more than one group apart.
- The more cohesive side wins 57-70% vs 35-51%. IFish's blob (largest cluster 3.4-4.3) is the extreme.

**A4. First middle capture and first kill**
- Send the opening group (3+ bodies, as IFish, pbg and cm do with 3.6-3.9 hitters) to the best middle-band group within reach.
- Fight for the first kill when the local max-HP ratio is ≥1.
- An earlier first middle capture wins 57-72% vs 34-50%. An earlier first kill wins 64-74% vs 28-48%.

**B. Items** (universal)

**B1. Convert gold every time a body is at spawn**
- Recall home to shop when holding ≥ the price of the next stat item and no channel or fight is pending.
- More purchases per body → 66-91% wins vs 20-42%. Max-HP lead at r600 → 67-94% vs 21-51%.

**B2. Health on carriers and frontline**
- pbg's Prism buys 76% Health and its HoR 73%. pbg's max HP leads its opponents' on average from r300 (6567|5991) to r1000
  (13936|10941).
- If god2 drafts a carrier, its build is Health-first. Damage goes to the ranged carry: IFish's Vesper is 96% Strength.

**C. Banking: choose the archetype by state, not by table**

**C1. Steady banking (default)**
- Tribute when the bag ≥ ~30-50 gems and a middle altar is within the current route.
- Median tribute bag: 15-33 for all six (Pantheon 15, pbg 33). The p90 is 44-90, except pbg's 161.
- Use a guard lock (10 gold) before any channel ≥ ~10 turns (bag ≥100) when an enemy is within 12. cm, IFish and Pantheon place
  1.5-3.6 guard locks a game. Completion of 100-200 bags with an enemy near is 50-92%.

**C2. Carry-and-cash (only with an item edge)**
- Let one durable body (health build) hold the bag when:
  - team max HP ≥ 1.3x the enemy's;
  - our score + bag ≥ ~900-1000, or the bag ≥ 200;
  - 2+ allies can stand within 8 of the altar.
- pbg's big tributes start at a median max-HP ratio of 1.5-1.6 with 2-3 allies within 8. They complete 76% for 200-400 bags and
  22% for ≥400.
- Never start a ≥400 channel with an enemy within 8 unless they are stunned. pbg completes 14% of those.
- Allies bank their own small bags at the same altar and guard it (`pbg/00great_wall_7ff33f2f` r910-959).

**C3. Race rule**
- If we are first to 500 on score, keep banking and avoid fights. First to 500 wins 76-94% for all six.
- If behind on score but ahead on max HP by ≥15%, fight and carry.
  - pbg wins 61% of those games (n 41) because it converts items into kills and a closing tribute.
  - Teams that do not convert win far less: IFish 15% (n 13), Nyx 38% (n 24).
- If behind on score at r600, take the highest-variance plan: objective + carry. The six win only 18-47% of games in which they
  trail on score at r600.

**D. Denial (the most exploitable moment)**

**D1. Punish every enemy channel ≥10 turns (bag ≥100)**
- Within 8 of an altar where an enemy tributes ≥100 gems: place a lock (10 gold, within 2 tiles) or stun.
- Damage alone does not cancel it. Locks and stuns stop 92-97% (an_fights).
- Prioritise carry teams: Prism holders, i.e. Prism drafted and bag ≥150.
- 400+ tribute attempts complete 4-60% per team (pbg 22%, IFish 4%; Pantheon, cm and Nyx have only 5-24 attempts each), and
  less with an enemy near.

**D2. Carry a lock**
- Always carry one lock (one at a time, 10 gold).
- Refill on each shop visit after r300 if the enemy has a bag ≥150. pbg and Nyx never lock, so their channels are free targets.

**D3. Single-altar maps**
- When the map has one reachable altar, hold it with an own lock and bank small and often.
- A 200-turn channel (2000 gems) is never safe. `pantheon/01boss_battle_e8e1f817` r1657-1731: three 2000-gem bags changed hands
  in 75 rounds.

**E. Objectives**

**E1. Golem / monolith commit**
- Start only with ≥3 bodies (golems ≥3-4) and team max HP ≥ ~1.0x the enemy's (≥1.3x for monoliths), with no enemy cluster
  within 8.
- Successes average 1.8-4.7 hitters vs 1.0-2.9 in failures. The max-HP ratio is 0.76-1.89 in successes vs 0.73-1.16 in
  failures; monolith successes are 1.0-1.9.
- Golems first: they succeed 50-88% vs monoliths 36-45%. Start them by r300-450 (pbg r448, IFish r376, Pantheon r391 for
  successes).

**E2. After a won fight near a heavy camp, convert immediately**
- `ifish/00contest_52dbafca` r445-545: three kills (plus a fourth enemy death to a camp), then three bodies burn the monolith
  while one screens; capture at r545.

**F. Fights (team-agnostic thresholds; an_fights covers the details)**

**F1. Deaths**
- Avoid trades that cost more deaths than the opponent's: fewer deaths per 1000 rounds wins 71-93%.
- No chases into the enemy zone after r100 unless the target is below 35% health. Enemy-zone presence for the six is
  0.02-0.07; cm's 0.07 comes with 12.7 deaths a game.

**F2. Never park**
- If a body has not moved more than 1 tile in 30 rounds without a capture or bank, re-target. Do not keep poking a camp it cannot
  kill (Pantheon's Prism parked for 465 rounds).
- Parked rounds are 2.7x higher in Pantheon's losses than in its wins.
- IFish and cm park 6-11 rounds a game.

**G. Opponent-specific (inferred from the opponent's draft and behaviour at runtime, not from its name)**

| signal | rule |
|---|---|
| Enemy Prism + the enemy carries ≥150 | Shadow the carrier with one body plus a lock; contest the altar it walks to (D1/D2). |
| Enemy cluster ≥4 for 50+ rounds (blob) | Do not engage it unless the local max-HP ratio ≥1.3. Farm the groups farthest from it; take heavy camps it is not near; pick stragglers. |
| Enemy forward presence ≥5% of body-rounds in our zone before r300 | Hold outside its reach at our camps and strike first. Do not chase into its half. |
| Enemy max HP ≤0.8x ours at r300 | Force fights in the middle. Pantheon-like teams win only 37% when behind on items at r600. |
| Enemy "recall" every turn | Ignore it as a target bonus. Hit it only if the channel has survived a full round (an_fights). |

## 6. Caveats

- **Sample size.** About 100 games per team, about 3 per map. Map-class win rates for small classes (3-6 games) are noisy; the
  150-game ranked lists are the better guide.
- **Builds.** Item builds for coo and Nyx come from 5 and 1 compact summaries only. Pantheon's come from 27.
- **Associations, not causes.** The paired S−O comparisons (§2.1) are associations. Banks, gold and max HP are partly
  consequences of winning. Walking, mid presence, cohesion, first mid capture and deaths are closer to decisions, but are still
  confounded by local strength.
- **Tribute counts.** Tribute "attempts" include restarts after a lock, stun or self-cancel, so per-attempt completion
  understates per-bag completion.
- **Hold and park detection.** These count bodies that stand still while recall-spamming (Pantheon) as holding.
- **Zones on two maps.** Zones use walking distance. On maps where the spawns touch (reverse_spiral, rushbait) "middle" means
  equidistant, not central.

## 7. Reproduce

```
node tools/top2/playbooks/geocheck.mjs
bash tools/top2/playbooks/run_extract.sh                      # pb_extract.mjs over all dumps -> pb_<key>.jsonl
python tools/top2/playbooks/pb_flat.py                        # -> flat.pkl
python tools/top2/playbooks/pb_tables.py [overview phase opening econ fights obj end distinct classes]
python tools/top2/playbooks/pb_class.py; python tools/top2/playbooks/pb_common.py
python tools/top2/playbooks/pb_roles.py; python tools/top2/playbooks/pb_ladder.py; python tools/top2/playbooks/pb_items.py
for k in pbg ifish cm pantheon coo nyx; do python tools/live/par.py 3 C:/battlecode/cache/top2_playbooks/rules_$k.jsonl tools/top2/playbooks/pb_rules.mjs -- C:/battlecode/cache/t2dump/$k/*.json.gz; done
python tools/top2/playbooks/pb_rules_agg.py
(same loop for pb_parked.mjs -> parked_<key>.jsonl and pb_holds.mjs -> holds_<key>.jsonl); python tools/top2/playbooks/pb_parked_agg.py parked|holds
python tools/top2/playbooks/pb_select.py --run; python tools/top2/playbooks/pb_digest.py [key]
node tools/top2/playbooks/pb_story.mjs DUMP TEAM [K1 K2]; node tools/top2/playbooks/pb_moment.mjs DUMP A B S [X Y D]
```

All outputs (tables `t_*.txt`, stories) are in `C:/battlecode/cache/top2_playbooks/`.
