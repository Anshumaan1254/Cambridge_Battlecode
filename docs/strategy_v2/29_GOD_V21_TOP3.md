# GOD v21: the top 3 on every map, and steadiness (Oct 27, patch 2.0.0)

The user (Oct 27 00:45 IST): put v20 (the `_v20d` switches) on the website as "GPTA AWAKEN" and play IC on every map. 00:58 IST: "make a new
bot combining v18 and v20; there is stuttering in v20, recalls without need on high health, and back-and-forth when an enemy is in range;
learn the strategy of the top 3 teams, play them on each map, combine their strategy, draft mixture, learning and weaknesses".

## 1. Data

- **Website v77 = GOD v20** (`submissions/history/god_v20_20261027.zip`, byte-identical to the `_v20d` candidate), live from Oct 27 00:50 IST.
- **Unranked groups, all 70 maps, v20 against each of the top 3**: IC (pinned to the version of the v18 / v19 runs) **7/70**
  (v18 8/70, v19 5/70; paired margin v20 - v18 -23 [-108, +67]); **Mite 5/70**; **Trzy Kwaterki 7/70**. Show files:
  `experiments/ic_oct26_v18/v20/`, `experiments/top3_oct27/groups/{mite,tk}/`.
- **Ranked games of the top 3 on engine 2.0.0** (Oct 26 00:24 - Oct 27, 580 each): `experiments/top3_oct27/{ic,mite,tk}_ranked.jsonl`
  (`fetch_ranked.py`). IC 71.6%, Mite 56.6%, Trzy Kwaterki 51.9%.
- Scripts (`experiments/top3_oct27/`): `drafts.py` (draft tables), `mapdrafts.py` (per map), `econ.py` (economy per game), `osc.py`
  (A-B-A walking), `steal.py` (who hit the camps of a capture), `recalls.py` (real recalls and their context). Trace reasons:
  `experiments/god21/aba_reasons.py` on `G20_TRACE` stdout (the `PT` line carries the turn-start tile, decision path and engage code).

## 2. Why all three beat us (v20, 70 maps each)

| per game | IC | us vs IC | Mite | us vs Mite | TK | us vs TK |
|---|---|---|---|---|---|---|
| final gems | 993 | 399 | 971 | 380 | 978 | 375 |
| captured gems (r<300 / r300-800 / later) | 238 / 533 / 275 | 121 / 217 / 125 | 244 / 512 / 282 | 112 / 214 / 106 | 228 / 521 / 292 | 113 / 209 / 103 |
| captures | 43.4 | 22.5 | 52.4 | 21.2 | 46.1 | 21.0 |
| first capture (round, mean) | 66 | 195 | 88 | 154 | 58 | 173 |
| deaths / kills | 9.2 / 11.7 | 11.7 / 9.2 | 4.9 / 10.2 | 10.2 / 4.9 | 4.8 / 9.7 | 9.7 / 4.8 |

- **Farming volume, not stealing**: captures they took from groups we had mostly hit (< 30% of the hits theirs) are 2-4% of their gems.
- **Time budget vs Mite**: they hit camps 15.2% of body-rounds (we 10.4%), are dead 6.3% (we 13.5%), walk with an enemy within 8 14.2%
  (we 19.2%), stand with an enemy within 8 5.4% (we 2.1%).
- **Items**: both buy focus (spell damage) items (r800 36 / 25 shard-equivalents, ours 5); Mite opens Treasure (10.4 at r150, ours 1.3);
  TK builds health (66 at r800, ours 29); both keep 300-400 gold unspent at r800 (we 60): they do not go home to shop small purses.
- **Drafts are not the gap**: TK drafts what we draft (Marcella, Vendetta, Ryth, Vesper, Heart of Ruin) and beat v20 63-7. IC: Vesper,
  Vendetta, Heart of Ruin, Cassi & Issac, Marcella (six bodies); Mite: Vesper, Vendetta, Heart of Ruin, Tavi, Marcella. Same draft on
  every map (only the size changes). On our brain the IC and C&I drafts lost before (doc 25: `_dr_ic17` -55, `_ciV` -140).
- **Opening fights**: lost_world vs Mite: four of ours die at r22-32 at the midpoint; first capture r197 (Mite r30).

## 3. The user's three complaints, measured

**Back and forth (A-B-A steps per 1000 alive body-rounds)**:

| | enemy within 6 | no enemy within 6 |
|---|---|---|
| v20 vs IC: us / IC | 94.5 / 50.1 | 22.1 / 14.0 |
| v20 vs Mite: us / Mite | 98.7 / 62.3 | 22.9 / 9.4 |
| v20 vs TK: us / TK | 82.1 / 44.8 | 23.8 / 12.8 |
| v18 vs IC: us / IC | 94.7 / 49.5 | 22.7 / 13.2 |

Same in v18 and v20. Traced (8 local games vs the IC clone, `G20_TRACE`): near an enemy the cycle is a flee step (combat's in-reach flee,
or the isolated / outmatched flee) and then a non-fight step straight back (the alert response, the bank walk to the nearest altar, the farm
walk, or combat walking back into the fight). Far from enemies it is mostly two farm walks (target switches and back).

**Recalls at high health**: 36 real recalls a game (the body lands on spawn) at mean health 0.60; 12.8 a game from >= 80% health. They are
capture-recalls (`capture_group`): any capture leaving >= 60 gold (`cap_recall_gold` 60) sends the body home to shop. IC recalls the same
number of times but to heal / shop / bank (none without a reason), and the top three hold 300+ gold.

**Stutter**: our bodies also end every free turn recalling and cancel it the next (`g17_bait`, Mite's bait trick from v17); the viewer
shows a recall every turn. Mite and TK do the same; IC does not.

## 4. GOD v21 switches (`bots/god21`, v20 + switches)

- `g21_lock` N: for N rounds after combat fled, no non-fight step may end nearer a visible enemy (within `g21_lock_r` 8) than we stand
  (a per-turn veto bitboard in `Nav::blocked_now`, `g_veto`), and combat does not walk back into a non-kill fight.
- `g21_noback` 1: no non-fight step onto the tile we stood on at the start of last turn (a walk in place needs a combat decision for its
  return step).
- Recalls: `cap_recall_gold` 250 (shop recall only for a real purse) or `chain_farm` 1 (existing: recall only when hurt or when the trip
  home beats the next target).
- `g17_bait` 0: no end-of-turn recall bait.

- `g21_fort` R: from round R, a body within 15 steps of spawn that sees more invaders (enemies nearer our spawn than theirs) within 8 than
  it has allies within 6 goes home and fights from the spawn tiles (full heal each round there); 30-round holds, 20-round cooldown.
- Whole-game adaptive pack: `g20_pack_until` 400 -> 2000 (our ranked losses die after r500, 8.2 deaths a game there).

## 5. More data (user, 02:20 IST: "study more teams, our ranked losses on v18 and v20, try strategies, exploits, tricks, baits")

- **Ladder record by live version** (vs teams of the same rating, 1922-1930): **v20 39/65 = 60%**, v18 100/210 = 47.6%. We are 49th
  (1,947). v20 stays live.
- **Ranks 4-12** (620 ranked games each, `ranked_rNN.jsonl`): every team drafts Heart of Ruin + Marcella plus three of Vesper, Vendetta,
  Ryth, Prism, Willow, Tavi, Varg; ours is the most common draft. 48-52% each.
- **Our 254 decoded v18 / v20 ranked games** (`loss_classes.py`, rows `ranked_us_v18v20_rows.json`):

| per game | deaths us / them | captured gems us / them | items r300 us / them | gold earned < r300 us / them |
|---|---|---|---|---|
| wins (120) | 4.3 / 19.6 | 990 / 682 | 43 / 25 | 868 / 623 |
| losses (134) | 11.5 / 8.7 | 513 / 1046 | 26 / 32 | 571 / 678 |

  Losses: outfought 54, outfarmed 38, bag lost 19, close 15, opening wipe 10 (a game can be in two classes). 8.2 of the 11.5 deaths come
  after r500; 62% of them start above 70% health 8 rounds before (burst), 62% with 2+ enemies within 8 already, 69% with an ally near,
  52% within 15 tiles of our spawn; killers: Vesper 3.1, Marcella 2.8 a game.
- **Tricks the top teams use**: turn-order changes every round (TK 4,018 set_priority a game, Mite 823; we alternate fighters' priority
  already), item selling to swap a full slot set (Mite 6.8 a game), altar locks 3-4 a game (we 1), the end-of-turn recall bait (Mite, TK).

## 6. Results (local, release, paired per-map margin against the unchanged build; s3 + var17 + gen2 = 145 maps vs v18, s3 70 vs the IC clone)

| candidate | vs v18 | vs IC clone `_icc2` |
|---|---|---|
| unchanged (`god21` / `_w21base`) | 152 / 155 of 290 | 93 / 93 of 140 |
| v20 (`_v20d`, the same play: the null control) | 150, -17 [-58, +19] | 91, -41 [-94, +6] |
| `g21_lock` 3 + `g21_noback` | 139, -52 [-127, +26] | 77, **-126 [-248, -12]** |
| `g21_lock` 3 | 142, -38 | 84, -89 |
| `g21_noback` | 125, -74 [-151, +4] | 75, **-167 [-278, -63]** |
| `cap_recall_gold` 250 | 134, -54 | 80, -75 |
| `chain_farm` 1 | 123, **-94 [-159, -30]** | 76, **-118 [-216, -25]** |
| `g17_bait` 0 | 141, -64 | 83, -78 |
| `build_stat` 1 | 144, -29 | 92, -49 |
| `build_kit` 1 | 151, +8 | 87, -42 |
| `gold_value` 0.7 / 0.35 | 146, -30 / 154, +12 | 80, -72 / 82, -53 |
| whole-game pack (`g20_pack_until` 2000) | 152, +9 (to v20) | 88, -4 (to v20) |
| ... with `g20_adapt_mem` 60 | 133, **-56 [-110, -1]** | 85, -42 |
| `g21_fort` 400 / 1 | 142, -24 / 141, -34 | 88, -48 / 86, -33 |
| whole-game pack + `g21_fort` 400 | 156, +11 [-40, +60] | 91, -33 [-111, +42] |

- The user's three complaints are, on our brain, part of what works: the back-and-forth near enemies is largely kiting (step in, hit,
  step out) and the flee / bank / farm cycle; vetoing it loses up to 167 gems a game against the IC clone. The capture-recalls (heal and
  shop at once) and the recall bait are worth keeping: every way of cutting them lost.
- The null control (v20 vs the same play rebuilt) moves by up to 41 gems: nothing within about +-50 is distinguishable locally. The
  fort never triggered in two traced games against the IC clone (it does not invade late), so only the ladder can judge it.

**GOD v21 candidate** = `bots/god21` with `g20_pack_until` 2000 (all g21 switches off): `submissions/candidates/god21_wholepack_20261027.zip`.
Confirmation of the exact build (`god21`, source with all switches): vs v18 158/290 = 54.5%, +4 [-35, +45] paired to the unchanged build; vs the IC clone 92/140, -19 [-87, +46]; 0 faults in 430 games. Locally level with v20; it extends to the whole game the one v20 mechanism the ladder seems to reward (v20 60% vs v18 48%).
