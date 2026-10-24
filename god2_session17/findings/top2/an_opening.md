# The opening (rounds 1-300) of the six study teams (top2 study, 2026-10-23)

The question: how prism best girl (pbg), Intercontinental Fish (ifish), Pantheon, conqueror_of_openai (coo), Claudus Maximus (cm)
and Nyx play rounds 1-300, compared with their opponents in the same games. This covers:
- first moves and first camp hits;
- squads and bodies per group, and cohesion over time;
- first captures and banks, and the first entry into the middle;
- gold and max HP at r100 / r200 / r300;
- the first fight;
- how all of this changes with map size, team size and camp mix;
- which opening choices separate wins from losses.

It ends with runtime rules for god2.

Notation:
- **[M]** = measured directly from the replays.
- **[I]** = inferred (an interpretation or a causal reading of a measured association).
- S = the study team; O = its opponents in the same games; W / L = winner / loser.
- P(W>L) = the share of games in which the winner's value is higher (ties count 0.5); 0.5 means no signal.

## 0. Data, definitions, tools

| key | team | ladder | games | W-L | win% | mean bodies (C&I = 2) | most frequent opponents |
|---|---|---|---|---|---|---|---|
| pbg | prism best girl | #1 | 116 | 71-45 | 61% | 4.50 | Pantheon 21, ifish 19, procless 19, :3 15 |
| ifish | Intercontinental Fish | #2 | 110 | 66-44 | 60% | 5.35 | pbg 20, :3 18, procless 17, policy wonk 16 |
| pantheon | Pantheon | #6 | 105 | 52-53 | 50% | 4.50 | :3 19, ifish 17, pbg 17, Univardisty 11 |
| coo | conqueror_of_openai | #18 | 101 | 55-46 | 54% | 4.54 | Mite 12, hello 10, NTU 9, EMPEROR Tung 9 |
| cm | Claudus Maximus | #19 | 106 | 58-48 | 55% | 4.48 | NTU 14, the ruliad 13, caterpillow 11, coo 9 |
| nyx | Nyx | #31 | 100 | 49-51 | 49% | 4.52 | EggsAfter11AM, AlphaSlop, Ad Astra |

**Sample**:
- 638 fight dumps (`C:/battlecode/cache/t2dump/<key>/`, all complete), which make 584 unique games. Some games sit in two
  folders (for example pbg vs Pantheon).
- Per-team tables use each team's own folder. Pooled winner-vs-loser tables count each game once.
- Sides and results come from `C:/battlecode/cache/t2/<key>/index.jsonl`. The draft of side `a` was checked against dump team 0
  in every game (0 mismatches).
- pbg, ifish and Pantheon play mostly each other and the other top-10 teams. coo, cm and Nyx play teams ranked about 10-50.

**Definitions**:
- **Zones** use walking distance from both spawns: BFS over the map grid of `C:/battlecode/cache/an_strategy/mapgeo2.jsonl`,
  with walls, holes, altars and the enemy spawn blocked.
  - f = d_own / (d_own + d_enemy). Zones: own **O** f < 0.4, middle **M** 0.4-0.6, enemy **T** > 0.6.
  - A group's zone uses its nearest camp tile.
  - "In the mid band" means a body stands on a tile with f in [0.4, 0.6].
- **Group** = cardinally connected camps. Its class is the strongest camp it contains: mono > golem > elk > wolf > gem > gold.
- **Main squad** = the bodies whose first camp hit is on the most-hit first group. Squad share = squad size / bodies.
- **Cohesion (lcf)** = the largest cluster of living bodies (linked within Chebyshev 5), as a share of the living bodies.
  Dispersion = the mean Chebyshev distance from the bodies to the team centroid.
- **Gold earned** = for each body and round, the larger of:
  - the positive gold delta;
  - the event income: capture gold (exact), 100 per kill, and Marcella's 2 gold per banked gem.

  The event income is needed because Pantheon and Nyx often capture, land home by recall and shop in the same round. A plain
  gold delta under-counts their income by about 300 gold by r300.
- **Max HP bought** = the team's max-HP sum minus the base sum of its draft.
- **Engagement** = champion-vs-champion damage in clusters: gaps of 6 rounds or less, within 10 tiles of the previous hit.
  - Striker = the side that dealt the first damage.
  - Local numbers / local HP = the living bodies (or their current-HP sum) of each side within 8 tiles of the first victim,
    one round before.
  - An engagement is won by the side that lost fewer bodies in it.
- **Home arrival** = a living body jumps from more than 2 tiles away onto its own spawn (recall or crystal).
- **Capture-recall overlap** = the capturer lands home in the same round as the capture.
- **Map strata**:
  - Size: S = 1400 tiles or fewer (30x30 .. 45x30), M = 1401-2600, L = more than 2600.
  - Picks per team is a property of the map, not a choice:
    - 3 picks: collision, fragment, packs, broken_curve, gold_rush, the_farm.
    - 4 picks: gemfight, interlock, reverse_spiral, rows, rushbait_v2, swirl, hooks, shortcut.
    - 5 picks: the other 26 maps.
  - Six-body teams are five-pick drafts that include Cassi & Issac.

**Tools** (all new, in `tools/top2/opening/`):

| script | what it does |
|---|---|
| `open_extract.mjs` | per-game opening record from a dump plus the map geometry |
| `open_flat.py` | the CSV tables (teamgame, bodies, caps, decisions, banktrips, eng, ts) |
| `open_an.py` | all tables below, by section: `teams wl pooled lead strata choices ts buckets exploit caps bank fight firsts` |
| `open_target.py` | the first-target choice model |
| `open_story.mjs` | one game's opening as text, used for the replay references |
| `open_homes.mjs` | home trips |
| `open_caprecall.mjs` | capture-recall timing; the 733 / 643 / 490 counts come from `nyx/0*.json.gz` |

Outputs are in `C:/battlecode/cache/top2_opening/`: `a|b|c.jsonl`, `flat/*.csv`, `out_<section>.txt` and `out_target.txt`. To
reproduce:

```
node tools/top2/opening/open_extract.mjs C:/battlecode/cache/an_strategy/mapgeo2.jsonl 300 <dumps> > X.jsonl
python tools/top2/opening/open_flat.py FLAT X.jsonl...
python tools/top2/opening/open_an.py FLAT <section>
```

**Caveats**:
- Everything here is an association, not an experiment.
- Winners and losers are both strong teams.
- Per-map samples are 1-3 games per team. Only the pooled and stratified numbers are evidence.

## 1. Summary (most important first)

1. **[M] The opening route does not decide games; the opening yield does.**
   - These route features are flat between winners and losers (P(W>L) 0.48-0.55): first-move round, first camp hit (r13 for
     the team, r21 for the median body), distance to the first group, nearest-or-not, elk-first, number of squads, cohesion,
     first-capture round.
   - A 10-fold cross-validated logistic model that uses only the r1-100 choices predicts the winner 54% of the time. The state
     at r100 predicts 63%, and the state at r300 predicts 71%.
   - The gap in yield opens at once:

     | | winners | losers |
     |---|---|---|
     | gold r50 | 168 | 138 |
     | gold r100 | 400 | 323 |
     | gold r200 | 905 | 706 |
     | gold r300 | 1484 | 1135 |
     | captured gems r100 | 47 | 38 |
     | mid-zone gems r100 | 19.5 | 11.3 |

   - The team ahead in gold at r300 wins 71% (n = 584). A gold lead of more than 300 at r200 wins 83% (n = 125); a deficit of
     more than 300 wins 21% (n = 132).
2. **[M] Early deaths and the first kill.**
   - Deaths by r100, own minus enemy, against the win rate:

     | death difference by r100 | 2 or more fewer | 1 fewer | equal | 1 more | 2 or more more |
     |---|---|---|---|---|---|
     | win rate | 84% (n 49) | 58% | 51% | 42% | 24% (n 51) |

   - The team that makes the first kill (by r300) wins 64-68% on every map size (n = 409).
   - Winners lose 0.39 bodies by r100 against losers' 0.70. Most early deaths come from champions (0.55 of losers' 0.70), not
     camps.
3. **[M] Fights in the opening are won by local superiority, and the striker has an edge.**
   - Over 1,210 engagements with a kill (r ≤ 300), the striker wins 59% and loses 35%.
   - By local numbers: +1 wins 68%, +2 or more wins 81%, -2 or fewer wins 40%.
   - By local current-HP difference: more than +500 wins 74%, more than +1500 wins 84%, less than -1500 wins 29%.
   - pbg wins 69% of the kill-engagements it opens and Pantheon 72%. coo wins 43% of those it opens and 16% of those it receives.
4. **[M] The middle is where the yield margin comes from.**
   - Captures by r300: winners make 3.44 mid-zone captures a game against losers' 2.15. Own-zone captures are equal (5.88 vs 5.71).
   - Mid gems at r300: winners 78.7, losers 45.1.
   - A mid-gem lead of 30 or more at r300 wins 77-80% (n = 132). A deficit of 30 or more wins 21-41% (n = 150).
   - Within games, more bodies in the mid band in r51-100 goes with more mid gems (ρ +0.40) and with winning (ρ +0.12, p < 0.01).
   - On maps whose gem rate is mostly in the middle (midShare > 0.75), winners make their first mid capture at r72 and losers
     at r94.
5. **[M] Each study team has a measurable opening weak spot.** See section 6. In short, the study team's win rate when the
   opponent does the following:

   | opponent's opening event | pbg | ifish | Pantheon | coo | cm | Nyx |
   |---|---|---|---|---|---|---|
   | takes the first kill | 50% | 39% | 29% | 34% | 40% | 39% |
   | strikes first | | | 34% | | | |
   | gets 30 or more extra mid gems by r300 | 47% | 18% | | | 15% | |
   | is 100+ gold ahead at r100 | | | | | 17% | 25% |
   | makes coo die more by r100 | | | | 18% | | |

6. **[M] The strongest two teams send a big squad to a gold-rich elk group, often not the nearest.**
   - Main-squad share: pbg 0.81, ifish 0.83, cm 0.85. Their opponents: 0.72.
   - The first target is an elk group in 58-62% of pbg's and ifish's games (opponents 45%), and the nearest group in only 40-43%
     (opponents 52%).
   - Fitted choice weights for pbg and ifish: ln(1 + walk distance) -2.0, ln(1 + gold) +0.9 / +1.2, elk +0.45 / +1.2, enemy
     zone -1.6.
   - In the choices-only model, a bigger main squad (+0.28) and not going to the nearest group (-0.27) are the two largest
     coefficients.
7. **[M] Bodies per group: diminishing returns above 3-4 on an elk group, and one capturer.**
   - Time from the first hit to the capture of an elk group: 29 rounds with 1-2 hitters, 27 with 3, 24 with 4, 22 with 5 or more.
   - Wolf groups: 27 rounds with 1 hitter, 24 with 2. Gem clusters: 9 rounds with 1 hitter.
   - Rewards are split among 1.0-1.2 bodies: one body captures and the others leave.
   - Vesper Vale takes 34-44% of the large rewards for pbg, ifish and Nyx.
8. **[M] The timing depends on map size; three-pick maps are the top teams' weak spot.**
   - First engagement (median): r32 on S maps, r66 on M, r85 on L. Engagements by r300: 10.1 / 6.1 / 5.2.
   - Walk to the first target (median): 9 / 13 / 26 tiles.
   - On three-pick maps pbg wins 44%, ifish 38% and Pantheon 38%. There, own-zone gems decide (winners 98.7 vs losers 75.2),
     not the middle.
9. **[M] Banking is driven by the walking distance to an altar.**
   - After a capture, the share that banks next falls with the altar's walking distance, for bags of 50 or less:

     | altar distance | 5 or less | 6-10 | 11-20 | more than 20 |
     |---|---|---|---|---|
     | banks next | 54-58% | 21-35% | 18-26% | 9-13% |

   - cm banks 83-94% of the time when an altar is 5 or less away. ifish banks 59% at 6-10 tiles once the bag is 31-50.
   - Winners bank 4.2 times by r300 (losers 3.1) and hold 112 banked gems (losers 76).
   - The bank-next shares are the same for winners and losers, so the policy is common; the volume differs.
10. **[M] Blob or spread is a style, not a cause.**
    - pbg and ifish blob: cohesion 0.73-0.75 in r51-100, against 0.64-0.65 for their opponents.
    - Pantheon and Nyx spread: 0.57-0.58.
    - Pooled, cohesion has no signal (P(W>L) 0.48-0.52; the team ahead on cohesion wins 48-50%).
11. **[M] Capture-recall overlap is a free saving of time.**
    - A recall started on the turn after arriving on a capture tile lands in the same round as the capture (arrival + 6).
    - Nyx uses it in 74% of its capture-then-home trips and Pantheon in 68%. pbg 18%, ifish 15%, coo 3%, cm 1%.
    - It saves a walk of 17-26 tiles (8-19 rounds). It is not associated with winning.

## 2. What separates winners from losers (584 unique games)

### 2.1 Time course (winner / loser means)

| round | gold earned | captured gems | mid-zone gems | banked | kills | deaths | max HP bought | bodies in mid band | alive |
|---|---|---|---|---|---|---|---|---|---|
| 20 | 18 / 16 | 1.9 / 1.8 | 0.0 / 0.1 | 0 / 0 | 0.0 / 0.0 | 0.0 / 0.0 | 2 / 1 | 0.8 / 0.7 | 4.6 / 4.6 |
| 50 | 168 / 138 | 18.1 / 15.7 | 5.7 / 3.4 | 3.6 / 1.8 | 0.2 / 0.1 | 0.1 / 0.3 | 54 / 49 | 1.2 / 1.2 | 4.5 / 4.3 |
| 100 | 400 / 323 | 46.8 / 37.9 | 19.5 / 11.3 | 18.6 / 13.2 | 0.5 / 0.3 | 0.4 / 0.7 | 262 / 235 | 1.4 / 1.2 | 4.4 / 4.1 |
| 150 | 646 / 508 | 73.9 / 59.0 | 30.4 / 18.6 | 38.1 / 26.1 | 0.9 / 0.5 | 0.7 / 1.2 | 571 / 449 | 1.4 / 1.1 | 4.3 / 4.1 |
| 200 | 905 / 706 | 106 / 83 | 46.6 / 26.5 | 59.9 / 40.9 | 1.2 / 0.6 | 0.9 / 1.6 | 891 / 680 | 1.3 / 1.1 | 4.4 / 4.1 |
| 300 | 1484 / 1135 | 174 / 133 | 78.7 / 45.1 | 112 / 76 | 2.0 / 1.0 | 1.4 / 2.4 | 1627 / 1236 | 1.5 / 1.3 | 4.3 / 4.1 |

[M] The relative gap in mid gems (+73% at r100) is far larger than the gap in total gems (+23%). The gap in gold opens by r50.

[M] Where the gold gap comes from:
- At r100 the gap is 77 gold: capture gold accounts for 40 (257 vs 217) and kill gold for 26.
- At r300, winners capture more elk groups (3.24 vs 2.56 a game, 96 vs 71 gems) and more wolf groups (4.43 vs 3.90).

### 2.2 Win rate of the team that is ahead (team 0 minus team 1, pooled)

| difference | far behind | behind | slightly behind | about level | slightly ahead | ahead | far ahead |
|---|---|---|---|---|---|---|---|
| gold earned r100 (< -200 / -200..-100 / -100..-30 / ±30 / 30..100 / 100..200 / > 200) | 26% (106) | 48% (75) | 39% (71) | 49% (76) | 54% (83) | 63% (93) | 80% (80) |
| gold earned r200 (< -300 / -300..-150 / -150..-50 / ±50 / 50..150 / 150..300 / > 300) | 21% (132) | 41% (78) | 44% (59) | 45% (51) | 56% (64) | 64% (75) | 83% (125) |
| captured gems r200 (< -60 / -60..-30 / -30..-10 / ±10 / 10..30 / 30..60 / > 60) | 22% (89) | 29% (68) | 44% (78) | 60% (151) | 57% (60) | 59% (70) | 84% (68) |
| mid-zone gems r300 (same bins as gems) | 21% (96) | 41% (54) | 66% (32) | 48% (219) | 51% (51) | 80% (41) | 77% (91) |
| bodies in mid band r51-150 (< -1 / -1..-0.5 / -0.5..-0.15 / ±0.15 / 0.15..0.5 / 0.5..1 / > 1) | 40% (92) | 46% (80) | 48% (82) | 57% (99) | 51% (77) | 58% (64) | 58% (89) |

[M] Kills by r300: the team ahead wins 69% (n = 373). Deaths by r300: the team with fewer wins 67% (n = 429). First kill:
64% on L maps (n = 96), 64% on M (n = 169), 68% on S (n = 144).

### 2.3 Models and within-game correlations

**Logistic models of the winner** (10-fold cross-validation, standardized differences team 0 minus team 1) [M]:

| inputs | accuracy | largest coefficients |
|---|---|---|
| opening choices r1-100 | 0.54 | main-squad share +0.28; nearest-first -0.27; first-capture round -0.24; bodies in mid r1-50 +0.22 |
| state at r100 | 0.63 | gold +0.58; deaths -0.30; mid gems +0.27 |
| state at r300 | 0.71 | banked +0.85; gold +0.81; carried +0.51; kills +0.14 |

**Within-game Spearman ρ** of each choice difference with the outcome difference (* = p < 0.01, n = 584) [M]:

| choice (team 0 minus team 1) | mid gems r300 | gold r300 | kills minus deaths r300 | won |
|---|---|---|---|---|
| first hit on an elk group (share of bodies) | +0.11* | +0.09 | +0.08 | +0.05 |
| main-squad share | +0.12* | +0.14* | +0.07 | +0.10 |
| first hit on the nearest group (share) | -0.09 | -0.02 | -0.11* | -0.06 |
| cohesion r51-100 | +0.06 | -0.01 | +0.01 | -0.02 |
| bodies in mid band r1-50 | +0.22* | +0.08 | -0.00 | +0.10 |
| bodies in mid band r51-100 | +0.40* | +0.22* | +0.17* | +0.12* |
| bodies in mid band r201-300 | +0.47* | +0.37* | +0.42* | +0.19* |
| first-capture round | -0.12* | -0.17* | -0.01 | -0.07 |
| banks by r300 | +0.46* | +0.21* | +0.32* | +0.21* |
| home arrivals by r300 | +0.17* | +0.41* | +0.38* | +0.21* |
| max HP bought r200 | +0.22* | +0.52* | +0.31* | +0.27* |
| share of engagements opened | +0.06 | +0.15* | +0.23* | +0.14* |
| struck first in the first fight | -0.02 | -0.02 | +0.02 | +0.05 |

[I] Mid presence, banking volume and HP bought are both causes and symptoms of a good opening. The route choices (target,
cohesion) have small effects. The opening is won by converting time into gold and gems in the middle without losing bodies.

## 3. Team profiles (S / O means in the same games, with P(S > O))

| metric | pbg | ifish | Pantheon | coo | cm | Nyx |
|---|---|---|---|---|---|---|
| bodies moving in round 1 (O 49%) | 81% | 65% | 84% | 31% | 0% | 53% |
| first camp hit, median body (round) | 19.6 / 19.4 | 17.8 / 17.3 | 18.4 / 20.5 | 30.8 / 23.2 | 20.4 / 22.7 | 20.3 / 21.9 |
| walk to the first group (tiles) | 20.7 / 18.7 | 21.2 / 17.4 | 18.6 / 18.7 | 21.9 / 20.8 | 28.6 / 19.7 | 19.2 / 20.6 |
| first hit in the mid zone | 0.29 / 0.28 | 0.30 / 0.27 | 0.27 / 0.28 | 0.27 / 0.32 | **0.48 / 0.27** | 0.30 / 0.33 |
| opening squads | 1.7 / 2.2 | 1.7 / 1.9 | 2.4 / 2.0 | 2.7 / 2.1 | 1.6 / 2.0 | 2.7 / 1.8 |
| main-squad share | **0.81 / 0.70** (0.63) | **0.83 / 0.74** (0.69) | 0.66 / 0.72 | 0.56 / 0.73 | 0.85 / 0.73 | 0.60 / 0.77 |
| cohesion r1-50 / r51-100 / r201-300 | 0.89 / 0.73 / 0.68 vs 0.83 / 0.64 / 0.59 | 0.91 / 0.75 / 0.68 vs 0.84 / 0.65 / 0.58 | 0.78 / 0.58 / 0.53 vs 0.83 / 0.67 / 0.62 | 0.81 / 0.66 / 0.60 vs 0.84 / 0.67 / 0.60 | 0.87 / 0.64 / 0.61 vs 0.84 / 0.68 / 0.61 | 0.79 / 0.57 / 0.55 vs 0.87 / 0.71 / 0.61 |
| first capture (round, gems) | 52.7, 28.7 / 47.8, 18.7 | 42.3, 24.8 / 50.1, 22.0 | 41.4, 18.0 / 46.2, 19.3 | 44.7, 15.4 / 48.2, 20.0 | 58.6, 25.1 / 46.2, 16.9 | 46.7, 17.4 / 54.7, 20.9 |
| first body / 2 bodies / 3 bodies in the mid band (median round; O 37 / 43 / 47) | 35 / 39 / 50 | 41 / 44 / 48 | 31 / 40 / 71 | 49 / 61 / 65 | **25 / 20 / 22** | 41 / 53 / 55 |
| first mid-zone capture | 105 / 121 | 98 / 113 | 96 / 111 | 122 / 101 | 94 / 119 | 98 / 116 |
| first bank (round, gems) | **129, 39** / 116, 30 | 102, 37 / 133, 38 | **93, 19** / 117, 34 | 120, 28 / 117, 27 | 106, 28 / 126, 29 | 113, 31 / 116, 29 |
| banks by r300 | 2.8 / 4.2 | 4.3 / 3.2 | **6.0 / 2.8** | 3.3 / 3.8 | 4.9 / 3.3 | 2.9 / 2.9 |
| carried at r300 | **88.6 / 55.9** | 54.3 / 64.9 | 69.3 / 59.0 | 48.3 / 49.4 | 25.0 / 40.3 | **84.5 / 46.7** |
| captures r300 (all; elk) | 7.9 / 9.7; elk 3.6 | 8.9 / 9.4; elk 3.9 | 10.6 / 8.7; elk 2.9 | 8.8 / 8.8; elk 2.4 | 8.2 / 7.8; elk 2.4 | 10.7 / 7.2; elk 2.8 |
| mid-zone gems r300 | 79.5 / 59.2 (0.62) | 81.1 / 60.9 (0.63) | 76.0 / 53.9 | 49.9 / 55.3 | 60.5 / 43.0 (0.61) | 72.2 / 50.9 |
| gold earned r100 / r200 / r300 | 394 / 902 / 1460 vs 357 / 823 / 1321 | **455 / 996 / 1657** vs 384 / 841 / 1371 | 365 / 761 / 1271 vs 367 / 811 / 1330 | 322 / 702 / 1113 vs 338 / 809 / 1340 | 375 / 777 / 1227 vs 335 / 797 / 1321 | 334 / 732 / 1186 vs 315 / 716 / 1139 |
| base max HP of the draft | 4473 / 4605 | 5037 / 4520 | **4204 / 4635** | 4622 / 4748 | 4531 / 4749 | 4396 / 4766 |
| max HP bought r100 / r200 / r300 | **324 / 1171 / 2093** vs 229 / 761 / 1386 | 367 / 1010 / 1622 vs 220 / 807 / 1426 | **106 / 354 / 728** vs 305 / 908 / 1641 | **46 / 269 / 667** vs 274 / 870 / 1636 | 392 / 855 / 1350 vs 175 / 756 / 1424 | 233 / 856 / 1636 vs 234 / 701 / 1352 |
| home arrivals by r300 | 13.2 / 11.7 | 14.5 / 11.0 | 12.4 / 11.0 | 8.4 / 10.7 | 9.3 / 10.1 | 14.6 / 10.7 |
| first fight (mean round); share struck first | 80; 0.60 | 89; **0.38** | 70; 0.64 | 86; 0.55 | 70; 0.47 | 68; 0.59 |
| first kill r≤300 is theirs | 0.61 | 0.63 | 0.56 | 0.40 | 0.45 | 0.54 |
| kills / deaths by r300 | 1.7 / 1.5 vs 1.1 / 2.0 | 2.0 / 2.4 vs 1.8 / 2.3 | 1.8 / 1.0 vs 0.9 / 2.1 | 0.95 / 2.4 vs 1.9 / 1.5 | 1.8 / 2.5 vs 2.0 / 2.2 | 1.2 / 1.5 vs 1.0 / 1.9 |

**Drafts** (share of games) [M]:

| team | champions |
|---|---|
| pbg | Prism 1.0, Vesper 0.94, Marcella 0.87, Heart of Ruin 0.77, Ryth 0.51, Vendetta 0.39 |
| ifish | Heart of Ruin, Vesper, Vendetta 1.0; Cassi & Issac 0.83; Ryth 0.53 |
| Pantheon | Prism, Vesper 1.0; Marcella 0.85; Heart of Ruin 0.80; Willow 0.62 |
| coo | Heart of Ruin 1.0, Vesper 0.91, Vendetta 0.78, Varg 0.78, Ryth 0.67 |
| cm | Heart of Ruin, Vendetta, Vesper 1.0; Tavi 0.82; Marcella 0.66 |
| Nyx | Heart of Ruin, Prism, Vesper 1.0; Marcella 0.88; Vendetta 0.64 |

**First purchases** by r300 [M] (from the compact summaries, where they exist):
- pbg (116 games): Power Strength, Durability Health and Bruiser Strength first; never Treasure; 1245 gold spent.
- ifish (108 games) and cm (106 games): Treasure Health or Strength first.
- Pantheon (27 games): a mix of Treasure Strength, Monster Focus, Jungle Focus and Jungle Strength.

### Style per team

- **pbg: the carrier blob.**
  - [M] 81% of bodies move in round 1. A squad of 81% of the bodies goes to an elk group 15 tiles away (median).
  - [M] One body takes the nearest gem cluster on its way. Example: Prism hits the gem at (14,15) in r2 of
    `00gem_fields_3fc2330b`.
  - [M] A single body captures, and pbg banks late: the first bank is at r129 (r152 on S maps), with 39 gems. It makes 2.8 banks
    by r300 and carries 89 gems at r300.
  - [M] It buys the most HP of any team (+1171 by r200) and opens 60% of engagements.
  - [M] Wins against losses:

    | | in wins | in losses |
    |---|---|---|
    | mid gems r300 | 98 | 50 |
    | first 2 bodies in mid (round) | 48 | 68 |
    | kills r300 | 2.0 | 1.2 |
    | deaths r300 | 1.2 | 2.1 |

- **ifish: the six-body blob that wins with numbers.**
  - [M] Its cohesion is the highest (0.91 / 0.75), with 1.7-1.9 bodies in the mid band from r50 (opponents 1.1-1.2).
  - [M] It captures first (r42), banks early (r102) and buys Treasure first. Its gold is the highest: 996 at r200.
  - [M] It strikes first in only 38% of first fights, yet it has local superiority whether opening (+0.54 bodies) or receiving
    (+0.81). It wins 62% of the kill-engagements it opens and 49% of those it receives.
  - [M] In losses: kills by r100 0.20 against the opponent's 0.66, deaths by r300 3.1 against 1.5.
- **Pantheon: the spread, low-HP, bank-often team.**
  - [M] 2.4 squads; it hits the nearest group with 57% of first targets.
  - [M] It takes the most gem clusters (2.9 a game) and makes 10.6 captures by r300. It makes 6.0 small banks by r300 (median
    15 gems), the first at r93 with 19 gems.
  - [M] It starts a Recall and a Cancel channel every turn: 954 cancels by r300. :3, EggsAfter11AM, EMPEROR Tung, Noobot and
    NEETCoders do the same. When the body stands still on a capture tile, that recall completes in the capture round.
  - [M] Its draft is low-HP and it buys little HP: +354 by r200 against 908.
  - [M] It opens 63% of engagements and wins 72% of the kill-engagements it opens.
  - [M] In losses it is out-itemed: HP bought 254 vs 1002, gold 1025 vs 1471.
- **coo: slow start, damage items.**
  - [M] Only 31% of bodies move in round 1, and the median body's first camp hit is at r31.
  - [M] It spreads: 2.7 squads, main-squad share 0.56. Its first 2 bodies reach the mid band at r61.
  - [M] It buys almost no HP (+269 by r200; Jungle and Treasure Strength).
  - [M] It wins 27% of kill-engagements. In losses: deaths by r300 3.5 against the opponent's 1.1.
- **cm: the early mid rush.**
  - [M] It waits 1-2 rounds, then walks 28.6 tiles. 48% of its first hits are in the mid zone. Its first 2 bodies reach the mid
    band at r20, the earliest of all teams.
  - [M] It banks often and early: 4.9 banks by r300; with an altar 5 or less away it banks 83-94% of the time. It carries 25 gems
    at r300.
  - [M] Its win rate is 71% on L maps against 47-50% on S and M maps. In losses it has 1.06 deaths by r100; in wins 0.45.
- **Nyx: spread gem-cluster farming with clean capture-recall.**
  - [M] It makes 3.3 gem-cluster captures and 10.7 captures by r300.
  - [M] 74% of its capture-then-home trips use the overlap, with no Recall spam.
  - [M] It carries big bags (84.5 at r300).
  - [M] In losses its gold at r100 is 275 against the opponent's 330.

## 4. The opening step by step

### 4.1 First moves and first camp hits (per body, medians)

| team | moves in r1 | first camp hit (round) | walk to its group | group in own / mid zone | first capture by the body (round; none by r300) | first bank | first in mid band | first home | died by r300 |
|---|---|---|---|---|---|---|---|---|---|
| pbg | 81% | 14 | 17 | 68% / 30% | 97; 29% | 141 | 45 | 77 | 27% |
| ifish | 65% | 16 | 17 | 68% / 32% | 79; 35% | 144 | 48 | 89 | 34% |
| Pantheon | 84% | 12 | 13 | 71% / 27% | 76; 18% | 121 | 51 | 77 | 20% |
| coo | 31% | 20 | 14 | 68% / 25% | 62; 24% | 130 | 60 | 97 | 39% |
| cm | 0% | 18 | 17.5 | 50% / 47% | 94; 25% | 120 | 29 | 89 | 41% |
| Nyx | 53% | 15 | 13 | 69% / 30% | 66; 25% | 130 | 51 | 71 | 29% |
| opponents | 49% | 14 | 13 | 70% / 29% | 79; 30% | 147 | 49 | 86 | 34% |

[M] No team ever opens in the enemy zone: 0-2% of first hits.

[M] The walk to the first group depends on map size (all teams):

| map size | 25th percentile | median | 75th percentile |
|---|---|---|---|
| S | 5 | 9 | 16 |
| M | 7 | 13 | 21 |
| L | 17 | 26 | 45 |

### 4.2 First target and squads

**Main-squad first target** [M]:

| team | n | squad share | walk | nearest group | top-3 nearest | elk group | gem cluster | wolf | mid zone | a richer group was as close |
|---|---|---|---|---|---|---|---|---|---|---|
| pbg | 116 | 0.81 | 15 | 0.43 | 0.71 | 0.58 | 0.01 | 0.19 | 0.32 | 0.23 |
| ifish | 110 | 0.83 | 15 | 0.40 | 0.71 | 0.62 | 0.00 | 0.21 | 0.31 | 0.39 |
| Pantheon | 105 | 0.66 | 11 | 0.57 | 0.88 | 0.46 | 0.10 | 0.28 | 0.24 | 0.27 |
| coo | 101 | 0.56 | 13 | 0.48 | 0.82 | 0.36 | 0.10 | 0.42 | 0.23 | 0.35 |
| cm | 106 | 0.85 | 17.5 | 0.28 | 0.58 | 0.52 | 0.05 | 0.27 | 0.50 | 0.66 |
| Nyx | 100 | 0.60 | 11 | 0.52 | 0.86 | 0.39 | 0.13 | 0.29 | 0.25 | 0.38 |
| opponents | 530 | 0.72 | 13 | 0.52 | 0.80 | 0.45 | 0.05 | 0.29 | 0.28 | 0.49 |

**Conditional-logit utility of the chosen first group** among all reachable groups (monoliths excluded; small ridge) [M].
"hit" = the share of games in which the utility's argmax is the group actually chosen.

| team | hit | ln(1 + walk) | ln(1 + gems) | ln(1 + gold) | mid | enemy zone | elk | golem | wolf |
|---|---|---|---|---|---|---|---|---|---|
| pbg | 0.46 | -2.09 | +0.14 | +0.89 | -0.60 | -1.64 | +0.45 | +0.47 | -0.65 |
| ifish | 0.47 | -1.99 | -0.19 | +1.22 | -0.52 | -1.67 | +1.21 | -0.08 | +0.03 |
| Pantheon | 0.54 | -4.77 | +0.40 | -0.26 | +0.60 | -0.47 | +1.43 | -0.21 | -0.23 |
| cm | 0.19 | -1.52 | +0.19 | +0.68 | +0.65 | -1.12 | -0.03 | -1.10 | -0.16 |
| opponents | 0.51 | -2.66 | +0.06 | +0.46 | -0.16 | -1.98 | +0.78 | -0.72 | +0.11 |

**Simple rules, as the share of games in which the rule picks the first target** [M]:

| team | nearest | (gems + gold/10) / (d + 5) | gold / (d + 10) |
|---|---|---|---|
| pbg | 0.41 | **0.47** | 0.45 |
| ifish | 0.40 | 0.42 | **0.45** |
| Pantheon | **0.50** | | |
| Nyx | **0.49** | | |
| opponents | 0.49 | 0.32 | 0.35 |

- [M] Winners and losers choose the same kind of target: nearest 0.45 / 0.51, elk 0.48 / 0.46, main-squad share 0.73 / 0.71.
- [I] The target choice is a weak lever. pbg and ifish trade 1-2 extra rounds of walking for a gold-rich elk group taken with
  4 bodies, and that pays mostly in gold (squad share against gold at r300: ρ +0.14*).

### 4.3 Bodies per group and the capture pipeline

**Rounds from the first own hit to the capture**, uncontested captures, r ≤ 300, unique games [M]:

| hitters | elk group (n) | wolf group | gem cluster |
|---|---|---|---|
| 1 | 29 (160) | 27 (1554) | 9 (1512) |
| 2 | 29 (687) | 24 (1548) | 12 (319) |
| 3 | 27 (951) | 22 (885) | 12 (66) |
| 4 | 24 (666) | 21 (445) | |
| 5 | 22 (562) | 18 (193) | |
| 6 | 22 (161) | | |

Golem groups take 41-48 rounds with 3-5 hitters (n = 45; rare in the opening, 0.04-0.10 a game).

**Captures by r300 per game** [M]:

| team | elk-group captures | hitters per elk group | gems per elk capture |
|---|---|---|---|
| pbg | 3.59 | 3.71 | 32 |
| ifish | 3.85 | 4.35 | 31 |
| Pantheon | 2.87 | 2.86 | |
| coo | 2.37 | | |
| cm | 2.36 | | |
| Nyx | 2.78 | | |
| opponents | 2.81 | 3.33 | 29 |

| team | gem-cluster captures | wolf-group captures |
|---|---|---|
| Nyx | 3.33 | 4.62 |
| Pantheon | 2.87 | 4.77 |
| pbg | 0.85 | 3.34 |
| ifish | 1.08 | 3.85 |

- [M] Rewards are split among 1.0-1.2 bodies (elk 1.04-1.33): one body captures while the hitters move on.
- [M] Who captures the large rewards (15 gems or more):

  | team | Vesper | Marcella | Prism | Vendetta |
  |---|---|---|---|---|
  | pbg | 34% | 25% | 24% | |
  | ifish | 44% | | | 24% |
  | Nyx | 42% | | 24% | |
  | cm | | | | 36% |
  | coo | | | | 33% |

- [M] Contested captures (the enemy hit the group first) are rare in the opening: 4-8% of captures.
  - Per game: winners 0.52, losers 0.33; pbg 0.56, the most.
  - Pure steals (the enemy did all the hitting) happen 0.06-0.13 times a game. pbg steals the most gems this way: 3.4 a game.

**Capture-recall overlap** [M]:
- Measured on the 733 captures in Nyx's games (both teams) after which the capturer was home in the capture round.
- In 643 of the 733, the capture came 6 rounds after the body arrived on the tile.
- In 490 of the 733, the recall was started on the turn after arrival. In the others it was re-issued later, as in Pantheon's
  every-turn recall spam.
- Example: Nyx `00expanse_6c45c86b`, Prism arrives r33, recalls r34, captures and lands home r39; Vesper r40 → r41 → r46;
  Vendetta r68 → r69 → r74.
- Share of capture-then-home trips that overlap: Nyx 74%, Pantheon 68%, opponents 45%, pbg 18%, ifish 15%, coo 3%, cm 1%.
- The saving is a walk of 17-26 tiles, or 8-19 rounds compared with the non-overlapped home trips.
- Win rate by the share of a team's captures that overlap: 0 → 48%, 0-0.2 → 56%, 0.2-0.5 → 53%, more than 0.5 → 47%. It is a
  time saving, not a separator.

**Home trips** [M]:
- Recalls in the opening are mostly heals: median HP share at the trip 0.34-0.50, and 49-78% below half HP.
- Median gold held on arrival is 10-77, so shopping happens along the way or while dead.

### 4.4 Cohesion over time (largest-cluster share; dispersion in tiles)

[M] The opening starts grouped for every team: 0.78-0.91 in r1-50. It loosens by r51-100:

| team | r51-100 | r201-300 | dispersion r51-100 |
|---|---|---|---|
| pbg | 0.73 | 0.68 | 5.6 |
| ifish | 0.75 | 0.68 | 5.6 |
| coo | 0.66 | 0.60 | 6.9 |
| cm | 0.64 | 0.61 | 7.4 |
| Pantheon | 0.58 | 0.53 | 8.6 |
| Nyx | 0.57 | 0.55 | 8.0 |
| opponents | 0.64-0.71 | 0.58-0.62 | |

[M] Pooled, cohesion does not separate winners from losers. P(W>L) is 0.48-0.52 in every window, and within-game ρ with winning
is -0.04 to +0.01.

[M] On S maps everyone is grouped: 0.75 at r51-100. Elsewhere 0.60-0.65.

[I] Cohesion is the means pbg and ifish use to win fights (their local-numbers edge, section 4.8). Spread teams win by capture
volume. Neither is required.

### 4.5 Middle entry and presence

- [M] First body / 2 bodies / 3 bodies in the mid band (median round): winners 35 / 40 / 47, losers 39 / 44 / 47.
- [M] By map size, the first body in the middle arrives at r29-35 on S maps and r58-72 on M and L maps.
- [M] On maps with midShare > 0.75 the first mid entry is at r25-28, and winners make the first mid capture at r72 (losers r94;
  P(W>L) 0.37, lower is better).
- [M] Bodies in the mid band, winners against losers: 1.2 / 1.2 at r50, 1.4 / 1.2 at r100, 1.4 / 1.1 at r150, 1.5 / 1.3 at r300.
- [M] ifish has the most presence (1.7-1.9 from r51). cm enters first (2 bodies at r20).
- [M] A deficit of more than 1 body in the mid band in r51-150 → 40% win (n = 92); level → 57%.

### 4.6 First captures, first banks, bank decisions

- [M] Team first capture: winners r46, losers r52 (P(W>L) 0.49). First capture gems: 22 / 19.
- [M] Team first bank: winners r114 with 32.5 gems; losers r119 with 29.3 gems.
- [M] Banks by r300: winners 4.2 (36% via a home visit), losers 3.1 (38%). Median gems per bank: 22 vs 19.

**Next action after a capture** (r ≤ 300) [M]. "home" includes a recall landing in the capture round.

| team | bank | another capture | home | death |
|---|---|---|---|---|
| cm | 0.52 | 0.20 | 0.22 | 0.05 |
| Pantheon | 0.29 | 0.18 | 0.50 | 0.02 |
| ifish | 0.30 | 0.24 | 0.44 | 0.02 |
| pbg | 0.22 | 0.29 | 0.47 | 0.03 |
| coo | 0.22 | 0.26 | 0.46 | 0.06 |
| Nyx | 0.14 | 0.25 | 0.59 | 0.03 |
| winners / losers | 0.28 / 0.24 | 0.25 / 0.25 | 0.45 / 0.45 | 0.02 / 0.05 |

**P(bank next) by carried bag and walking distance to the nearest altar**, all teams, n = 12,243 [M]:

| bag | altar 5 or less | 6-10 | 11-20 | more than 20 |
|---|---|---|---|---|
| 1-15 | 0.54 (1250) | 0.27 (1190) | 0.18 (1697) | 0.11 (1139) |
| 16-30 | 0.58 (779) | 0.21 (631) | 0.18 (1139) | 0.09 (960) |
| 31-50 | 0.54 (327) | 0.35 (290) | 0.26 (729) | 0.13 (581) |
| 51-80 | 0.42 (180) | 0.28 (136) | 0.27 (263) | 0.20 (461) |
| 81+ | 0.13 (127) | 0.13 (75) | 0.18 (179) | 0.21 (102) |

Per team [M]:
- cm banks 0.83-0.94 at 5 or less, and 0.50-0.67 at 6-10.
- ifish: 0.59-0.60 at 5 or less; 0.59 at 6-10 for 31-50-gem bags; 0.43 at 11-20 for 51-80.
- pbg: 0.38-0.51 at 5 or less for bags of 50 or less; 0.47 at 6-10 for 31-80; 0.00-0.17 for 81+ (it carries).
- Pantheon banks small bags even at 11-20 tiles (0.35), and big bags almost never (0.00-0.10 for 51+).
- The table is nearly identical for winners and losers: within ±0.08 in every cell except 16-30-gem bags at 5 or less
  (0.65 vs 0.49).

[I] Banking policy is not where games are won. Banking volume follows capture volume. Bags of 81 or more are left unbanked by
everyone, and they are what pbg and Nyx carry.

### 4.7 Gold and max HP at r100 / r200 / r300

- [M] Pooled winners against losers:
  - Gold earned: 400 / 905 / 1484 against 323 / 706 / 1135. P(W>L) 0.64 / 0.68 / 0.71.
  - Max HP bought: 262 / 891 / 1627 against 235 / 680 / 1236. P(W>L) 0.54 / 0.62 / 0.66.
  - The base max HP of the drafts is identical: 4632 / 4631.
  - The team ahead in HP bought at r200 wins 63%, at r300 66%.
- [M] Gold spent tracks gold earned: 750 vs 573 at r200. Unspent gold at r300 is 152-186.
- [M] Per team: see the section 3 table. pbg buys the most HP and ifish earns the most gold. Pantheon and coo buy very little HP:
  - Pantheon wins 83% when it is nonetheless ahead on HP bought at r200 (n = 23) and 41% when it is behind (n = 78).
  - coo: 79% ahead (n = 14), 47% behind (n = 78).

### 4.8 The first fight

**First engagement per game by map size** [M]:

| size | games | 25th percentile | median | 75th percentile | contains a kill | in the striker's mid zone |
|---|---|---|---|---|---|---|
| S | 154 | r19 | r32 | r51 | 44% | 57% |
| M | 213 | r25 | r66 | r134 | 45% | 74% |
| L | 121 | r68 | r85 | r131 | 40% | 85% |

- [M] 96 of 584 games have no champion damage at all by r300.
- [M] Striker types: Vesper 128, Ryth 83, Marcella 79, Heart of Ruin 59, Prism 50, Vendetta 42.

**All engagements with a kill, r ≤ 300** (n = 1,210), from the striker's side [M]:

| local numbers | -2 or fewer | -1 | 0 | +1 | +2 or more |
|---|---|---|---|---|---|
| striker wins / loses | 0.40 / 0.55 (192) | 0.53 / 0.38 (231) | 0.55 / 0.37 (373) | 0.68 / 0.25 (248) | 0.81 / 0.14 (166) |

| local current-HP difference | < -1500 | -1500..-500 | ±500 | 500..1500 | > 1500 |
|---|---|---|---|---|---|
| striker wins / loses | 0.29 / 0.65 (171) | 0.45 / 0.45 (257) | 0.56 / 0.38 (306) | 0.74 / 0.20 (247) | 0.84 / 0.11 (229) |

**Per team** [M]:

| team | engagements by r300 (per game with any) | opened | win rate of opened kill-engagements | of received ones | local numbers when opening / when hit |
|---|---|---|---|---|---|
| pbg | 7.4 | 58% | 0.69 | 0.46 | +0.06 / +0.20 |
| ifish | 7.4 | 46% | 0.62 | 0.49 | +0.54 / +0.81 |
| Pantheon | 8.5 | 63% | 0.72 | 0.42 | -0.09 / -0.18 |
| Nyx | 9.4 | 60% | 0.57 | 0.38 | -0.31 / -0.31 |
| cm | 8.1 | 42% | 0.55 | 0.34 | +0.01 / -0.12 |
| coo | 7.6 | 45% | 0.43 | 0.16 | -0.39 / -0.13 |

- [M] Striking first in the very first fight does not predict the game by itself: within-game ρ +0.05, and the first striker
  wins the game 53%.
- [M] Winning that first fight (deaths) predicts 56%. The first kill predicts 65%.

[I] What matters is entering fights with local superiority and not losing bodies, not opening blindly.

## 5. By map size, team size, camp mix (pooled winner / loser, P(W>L))

| metric | S maps (154 games) | M maps (263) | L maps (167) |
|---|---|---|---|
| first camp hit (team) | 8.1 / 8.7 | 9.7 / 10.1 | 23.7 / 24.9 |
| main-squad share | 0.74 / 0.73 | 0.77 / 0.74 | 0.68 / 0.64 (0.59) |
| first capture | 40 / 53 | 41 / 46 | 60 / 59 |
| first mid entry | 35 / 29 | 58 / 64 | 65 / 64 |
| first mid capture | 81 / 98 | 111 / 121 | 124 / 119 |
| captured gems r300 | 180 / 116 (0.71) | 200 / 161 (0.67) | 128 / 107 (0.60) |
| mid gems r300 | 104 / 53 (0.64) | 83 / 50 (0.62) | 49 / 31 (0.59) |
| gold r300 | 1566 / 1022 (**0.79**) | 1512 / 1231 (0.67) | 1362 / 1087 (0.71) |
| kills r300 | 3.3 / 1.6 (0.71) | 1.7 / 0.95 | 1.2 / 0.65 |
| first fight, mean round | 39 | 89 | 106 |
| engagements r300 | 10.1 | 6.1 | 5.2 |
| cohesion r51-100 | 0.75 / 0.74 | 0.65 / 0.66 | 0.60 / 0.59 |

### Team size

[M] Picks per team is fixed by the map. Win rates by own vs opponent bodies:

| own vs opponent bodies | win rate | n |
|---|---|---|
| 5 vs 4 | 67% | 21 |
| 4 vs 5 | 33% | 21 |
| 5 vs 6 | 46% | 109 |
| 6 vs 5 | 54% | 109 |

So Cassi & Issac's second body is worth about +4-17 points.

[M] On three-pick maps the economy is own-side:

| metric (three-pick maps) | winners | losers |
|---|---|---|
| own gems r300 | 98.7 | 75.2 |
| mid gems r300 | 40 | 33 |
| gold r300 | 1449 | 1065 |
| kills r300 | 1.3 | 0.7 |
| deaths r300 | 0.8 | 1.7 |
| engagements by r300 | 5.1 | |

[M] The study teams on three-pick maps: pbg 44% (n = 18), ifish 38% (16), Pantheon 38% (16), coo 54%, cm 50%, Nyx 50%.

[M] On four-pick maps the first fight comes early (mean r38) and engagements are many (8.8 by r300). Six-body teams
(ifish-like) have the most mid presence: 2.4 bodies in r51-100 in wins.

### Camp mix

| metric | elk/wolf-only maps (318) | golem maps (30) | monolith maps (236) |
|---|---|---|---|
| first fight (mean round) | 63 | 48 | 108 |
| first mid capture W / L | 103 / 107 | 99 / 114 | 111 / 121 (0.38) |
| gold r300 W / L | 1559 / 1134 (0.75) | 983 / 695 (0.77) | 1445 / 1192 (0.66) |
| mid gems r300 W / L | 78 / 46 | 178 / 116 | 67 / 35 |

- [M] Golem groups (5000 HP) are taken 0.04-0.10 times a game by r300.
- [M] Monoliths are never taken in the opening.

### midShare classes (share of the map's gem rate in the mid band)

| metric | below 0.45 (148) | 0.45-0.75 (217) | above 0.75 (219) |
|---|---|---|---|
| first mid entry | 72 / 71 | 70 / 72 | 25 / 28 |
| first mid capture W / L | 126 / 128 | 131 / 126 | **72 / 94 (0.37)** |
| first capture W / L | 43 / 44 | 45 / 47 | **50 / 64 (0.42)** |
| first fight (mean round) | 73 | 120 | 50 |
| engagements by r300 | 7.6 | 3.6 | 9.7 |
| mid gems r300 W / L | 60 / 31 | 42 / 26 | 127 / 74 |

[I] On mid-heavy maps the opening is a race to the middle: the first capture and the first mid capture matter there, and
nowhere else.

### By study team and map size [M]

| team | S | M | L |
|---|---|---|---|
| pbg | 68% | 64% | 50% |
| ifish | 54% | 56% | **72%** |
| Pantheon | **62%** | 48% | 42% |
| coo | 44% | 62% | 52% |
| cm | 47% | 50% | **71%** |
| Nyx | 54% | 49% | 44% |

On L maps, ifish keeps 2.3 bodies in the mid band in r51-100, and cm 1.8.

## 6. Weak spots to exploit (study-team win rate (n) when the opponent does X in the opening)

| event | pbg | ifish | Pantheon | coo | cm | Nyx |
|---|---|---|---|---|---|---|
| baseline | 0.61 (116) | 0.60 (110) | 0.50 (105) | 0.54 (101) | 0.55 (106) | 0.49 (100) |
| opponent makes the first kill | 0.50 (30) | **0.39 (28)** | **0.29 (35)** | **0.34 (41)** | 0.40 (45) | 0.39 (31) |
| opponent strikes first in the first fight | 0.61 (38) | 0.59 (56) | **0.34 (32)** | 0.49 (35) | 0.53 (49) | 0.50 (36) |
| study team has more deaths by r100 | 0.50 (18) | 0.45 (20) | 0.53 (15) | **0.18 (17)** | 0.34 (29) | 0.37 (19) |
| opponent 100+ gold ahead at r100 | 0.52 (29) | 0.32 (19) | 0.44 (36) | 0.39 (31) | **0.17 (29)** | **0.25 (24)** |
| opponent leads mid presence by 1+ (r51-150) | 0.54 (28) | 0.38 (13) | 0.60 (25) | 0.49 (37) | 0.35 (17) | 0.41 (27) |
| opponent leads mid gems by 30+ at r300 | 0.47 (17) | **0.18 (17)** | 0.30 (20) | 0.35 (23) | **0.15 (13)** | 0.25 (24) |
| opponent leads HP bought at r200 by 300+ | 0.50 (24) | 0.45 (29) | 0.43 (67) | 0.43 (69) | **0.19 (31)** | 0.30 (27) |

### pbg

- [M] pbg is the hardest to break: it still wins about 50% in every adverse case.
- [M] Its loss pattern: it is late to the middle (first 2 bodies there at r68, against r48 in wins) and the opponent collects
  75 mid gems to pbg's 50.
- [M] It banks late and carries big bags: 89 gems at r300, a first bank at r152 on S maps. Prism kept 71-178 gems from r33 to
  r140 in `00gem_fields_3fc2330b`.
- [M] Its split openings can be punished. In `00lost_world_b74302c8` Pantheon struck at r16 with 5 against 3 and pbg lost 4
  bodies by r100; it lost 0-1001.
- [I] Exploit: contest pbg's middle early, catch the carrier when bags are visible, and punish split bodies on small maps.

### ifish

- [M] ifish wins with numbers. Against an even fight its blob has a +0.5-0.8 local edge.
- [M] It collapses when it loses the middle (0.18) or the first kill (0.39).
- [I] Exploit: don't fight the blob even-handed. Take the other half of the middle with a squad, avoid its blob, and pick off
  stragglers.

### Pantheon

- [M] Its draft is low-HP, it buys little HP and it is spread out. It wins 72% when it opens a fight, but only 34% when the
  opponent strikes first and 29% when the opponent gets the first kill.
- [M] Its bodies channel a recall on capture tiles. Any damage cancels the recall, and an enemy entering the region resets the
  capture.
- [I] Exploit: strike Pantheon's isolated bodies first with local numbers of 0 or better, and harass its capture tiles.

### coo

- [M] coo is slow, buys almost no HP, and wins only 16% of the fights it receives.
- [I] Exploit: fight early. coo wins 18% when it dies more by r100.

### cm

- [M] cm rushes the middle with 2 bodies by r20, but dies early in its losses (1.06 deaths by r100).
- [I] Exploit: meet that squad with numbers, then out-farm cm. It wins 17% when the opponent is 100 gold ahead at r100, and 15%
  when the opponent has 30 more mid gems.

### Nyx

- [M] Nyx is spread, has a low gold rate and carries bags (84.5).
- [I] Exploit: out-farm Nyx early (0.25 when 100 gold behind at r100) and contest the middle (0.25).

## 7. Rules for god2

All quantities are observable or computable at runtime: walking distances by BFS from both spawns at init; group value from
camp types; local counts from what the body sees within 8; the own bag and the altar distance. Thresholds come from the tables
above; each rule says which part is measured and which is inferred.

1. **Opening objective** [M thresholds; I use].
   - Plan r1-200 to maximize gold plus gems captured per round, with no early deaths.
   - Track the own team's KPIs. For a 5-body team, the winners' means are 168 gold at r50, 400 at r100 and 905 at r200, with
     19.5 mid gems at r100 and 0 deaths by r100. Losers' means are 138 / 323 / 706 gold and 11.3 mid gems.
   - If the team is below the losers' curve at r100, prefer safe farming over contesting.
2. **Leave and target** [M weights; I rule].
   - Every body moves in round 1 (81-84% of pbg and Pantheon bodies do).
   - The main squad is all bodies but one (squad share at least 0.75; 0.65 on L maps). It goes to the group that maximizes
     U = 1.0·ln(1 + gold) + 0.5·[elk] − 2.0·ln(1 + walk) − 1.6·[enemy zone]. These are pbg's and ifish's logit weights; for
     a fixed formula, (gems + gold/10) / (walk + 5) matches pbg's choice 47% of the time.
   - Never open on an enemy-zone group (f > 0.6).
   - The remaining body takes the nearest gem or gold cluster on its way and then joins.
3. **Bodies per group** [M times].
   - Elk group: 3-4 hitters (27 → 24 rounds). A 5th body only if it has nothing else within 10 tiles (22 rounds).
   - Wolf group: 2 hitters (24 rounds).
   - Gem or gold cluster: 1 hitter (9 rounds).
   - When the last camp dies, exactly one body stays to capture (Vesper if present, for the gold bonus). The others go at once
     to the next target, which is the same U computed from their current position.
4. **Capture-recall overlap** [M timing; I gate].
   - If the capturer's next stop is spawn (HP below 50%, or a shopping or altar trip), start Recall on the turn after it
     arrives on the capture tile. The capture completes 6 rounds after arrival, in the same round as the recall.
   - Do it only with no enemy within 8 tiles, because damage cancels the recall.
   - It saves 8-19 rounds per trip.
5. **The middle** [M thresholds; I rule].
   - From r40, keep at least 2 bodies in the mid band (f 0.4-0.6) whenever 4 or more are alive.
   - After the first capture, rank mid-zone groups first among equal-U targets.
   - On maps with midShare > 0.75: take the first mid capture by about r70 (winners r72, losers r94), and make the first
     capture itself in the middle.
   - Use as a KPI a mid-gem lead of 30 or more by r300 (77-80% win).
6. **Fight gate, r1-300** [M].
   - Open a fight only if local numbers are +1 or better, or the local current-HP sum is at least 500 above the enemy's (win
     68-84%).
   - At -2 bodies or -1500 HP, disengage: walk away from the fight toward allies or spawn.
   - Prioritize the first kill (64-68% game win).
   - Do not count on striking first alone: the edge at even numbers is only 55 / 37.
7. **Early death budget** [M; I rule].
   - Target 0 deaths by r100: each extra death costs 9-27 points of win rate.
   - Recall below 50% HP when no local superiority holds (top teams recall at a median 0.34-0.50 HP).
8. **Bank rule after a capture** [M shares; I thresholds].

   | walking distance to the altar | bank when |
   |---|---|
   | 5 or less | now, any bag (cm 83-94%, ifish 59%) |
   | 6-10 | the bag is 31 or more (ifish 59%, pbg 47%) |
   | 11-20 | the bag is 51 or more (ifish 43%) |
   | more than 20 | only on the way home |

   Never let a bag pass about 80 gems away from an altar: everyone leaves 81+ bags unbanked, and that is the carrier target.
9. **Items** [M; I].
   - Spend gold on max HP on every spawn visit in the opening. HP bought at r200: winners 891, losers 680; the team ahead wins
     63%.
   - pbg's HP-first build reaches +1171 by r200. Low-HP drafts that skip this (Pantheon, coo) lose when they fall behind
     (41-47% when behind).
10. **Map-size and picks adaptation** [M; I].
    - S maps: keep one blob (cluster share 0.75 or more) through r100 and be fight-ready from r20 (first fight median r32).
      Kills decide (3.3 vs 1.6), so the fight gate (rule 6) matters most.
    - L maps: walk 25-45 tiles to the first target; two squads are acceptable; enter the middle by about r65.
    - Three-pick maps: farm the own side fully (own gems decide; 5 engagements by r300). Do not rush the middle.
11. **Counter-rules** [M rates; I actions].
    - Against a blob with a +1 local edge (ifish-like): do not engage. Take the other mid groups and hit stragglers.
    - Against a spread, low-HP team (Pantheon-like; observable max HP and spread): strike first at local numbers of 0 or better,
      and hit bodies standing still on capture tiles.
    - Against a carrier (enemy bag 80+, if visible; pbg and Nyx): focus that body when the fight gate allows.
    - Against an early mid rusher (cm-like: 2 enemy bodies in the mid band before r25): meet them with 3 or more bodies, or
      farm elsewhere and out-gold them.

## Appendix: replay references

All paths are `C:/battlecode/cache/t2/<key>/<file>.repl26a`; the dumps are `C:/battlecode/cache/t2dump/<key>/<file>.json.gz`.
View with `node tools/top2/opening/open_story.mjs C:/battlecode/cache/an_strategy/mapgeo2.jsonl <dump> 150 20`.

- **pbg/00gem_fields_3fc2330b**: pbg (team 0) beat Pantheon 1313-361 at r681.
  - r2: Prism hits the nearest gem cluster.
  - r5-16: Vesper, Heart of Ruin and Ryth hit the central elk group (1 elk + 8 gem).
  - r33: Prism captures 71 gems alone and keeps them (107 gems at r100, 178 at r140).
  - r32-52: first fight. Pantheon's Vesper strikes at (29,23) with 5 against 4 locally; deaths are 1-1 (r37, r38).
  - r50: Marcella and Ryth capture the elk group Pantheon's squad had opened on and killed (pbg hit it 0 times; 36 + 35
    gems), right after the 1-1 fight, and bank them at r66 / r69.
  - r129-140: pbg wins the second fight 2-0.
- **pantheon/01concentrated_wealth_29f48ace**: Pantheon (team 0) beat Trzy Kwaterki 1011-95.
  - r26-33: Vesper, Vendetta and Heart of Ruin hit the central group (1 elk, 8 gem, 12 gold).
  - r59: capture of 36 + 35 gems and 219 + 165 gold. Recalls were spammed r50-54, the last one landed both capturers on
    spawn in the capture round, and they walk off spawn at r60.
  - r79: altar lock. r84 / r85: banks.
  - Trzy Kwaterki opened on its own wolf group (r23-36) and lost the middle.
- **ifish/00stampede_c122d239**: ifish (team 0) against :3.
  - By r30 all 6 bodies are in the mid band.
  - r29: Vendetta strikes :3's Marcella with 6 against 2 locally.
  - Kills r40, r45 and r58, with 0 ifish losses (damage 3520 vs 1040).
- **pbg/00lost_world_b74302c8**: pbg (team 0) lost to Pantheon 0-1001 at r489.
  - pbg split: Vesper and Heart of Ruin went east.
  - r16: Pantheon's Marcella strikes Prism with 5 against 3; Prism dies r21 and Ryth r26.
  - r41-72: Pantheon takes all mid gem clusters, with an altar lock at r59.
  - pbg has 4 deaths by r100.
- **nyx/00expanse_6c45c86b**: Nyx won. Capture-recall overlap: Prism arrives r33, recalls r34, captures and lands home r39.
  The same pattern repeats r40-46 and r68-74.
- **Early-death losses**: coo/00lost_world_fd178d7f (4 deaths and 2 kills by r100 against Mite, after coo struck first at
  r13); cm/01elk_arena_221310ac (3 deaths and 0 kills by r100 against Zarzorki; Zarzorki struck first at r12).
- **Late-middle losses of pbg**: pbg/01big_world_e0233124 (first mid entry r265); pbg/00great_wall_3a46ed8d (first capture r164,
  against ifish).
