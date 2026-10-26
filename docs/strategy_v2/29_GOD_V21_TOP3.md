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

## 5. Results

(pending)
