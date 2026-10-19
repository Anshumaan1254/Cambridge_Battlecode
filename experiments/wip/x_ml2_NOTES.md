# x_ml2: fight / danger model learned from real ladder games (agent ml2, session 13)

Baseline `bots/_ch2` (legend_m14_commit). Copy `bots/_x_ml2` (switches default off), patch `experiments/wip/x_ml2.patch`
(includes the new file `src/ml2_model.h`). Rebuild: `SRC=bots/_ch2 tools/variant.sh _x_ml2 && (cd bots/_x_ml2 && patch -p1
--no-backup-if-mismatch < ../../experiments/wip/x_ml2.patch)`, then `SRC=bots/_x_ml2 tools/variant.sh _mlXX key=val`.
Scripts (tools/ml/): `ml2_sum.py` (pooled proxy wins + deaths + identical games + h2h), `ml2_decode.py` (decode replay folders), `ml2_dataset.py` (contact dataset), `ml2_train.py` (models, CV, export
of the logistic weights as `ml2_model.h` arrays), `ml2_diag.py` (where the bot's estimate is wrong), `ml2_parity.py` (in-game features
of a `--define "ML2_DEBUG 1"` build vs the dataset's on the same game). sklearn installed with `pip install scikit-learn --break-system-packages`;
run sklearn with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1` (multithreaded BLAS under the shared load stalled for 10 minutes).

## State (update at every step)
- 23:45 UTC: model trained, ported to C++ (`ml2_features`, `ml2_logit` in brain.cpp; weights `ml2_model.h`), parity checked, control
  `_ml0` = 34/34 games identical to `_ch2` vs `_mite`. Screen running (`$S/ml2/screen.sh`, official 34 vs `_ch2` + 5 proxies):
  `_mll40`, `_mlf40`, `_mll30`, `_mll50`, `_mle50`. Results: `BASE=_ch2 python3 tools/screensum.py _mll40 _mlf40 _mll30 _mll50 _mle50`.

## Data (187 replays decoded, 179 distinct; 160 games with contact rows after dropping 8 duplicates and the censored ends)
- Sets: ladder_oct19b (50, our side from index.json), ladder_oct18 (17, us = team 0, legend_st), sneaky_oct18 (17, us = team 0,
  legend_m8/m10), interwin_oct19 (45, IC vs others), interwin_oct18 (13, Mite vs ifish), ladder_top3 (15), intercon_oct18 (30).
  Duplicates (same game in two sets, by a fingerprint of drafts + final round + round-100 state) dropped: 8.
- Row = alive body with an alive enemy champion within 7 (true positions): 222,407 rows (43,164 of our bot's bodies).
- Features (58, `ml2_dataset.FEATURES`): own health / max / fraction, strength, focus, damage per round as combat() counts it, burst of
  ready spells, ranged, Cassi/Issac, bag, own spell / dash ready, walking distance home, own spawn, enemy half / neutral band, round,
  in a bush, type flags; visible enemies (Chebyshev <= 8, a bush hides unless we stand in a bush within 2): counts within 3/5/7,
  health and damage sums within 5/7, ready burst within 5, ready stuns / areas within 5, nearest distance and its health fraction,
  lowest health within 5, a kill this turn, melee/dash chasers within 3, Varg within 2, Ren within 4, enemies alive, an enemy on its
  spawn within 7; visible allies within 3/5/7, their health, damage within 6, allies alive, allies below 30% within 5; damaged live
  camps within 3; a re-implementation of combat()'s estimate (log advantage, in reach, incoming, can escape, isolated).
  Spell readiness from the cast events (cooldown 8: a slot cast in round t is ready at t + 8; checked: min gap 8).
- Labels: die4, die8 (this body, Cassi/Issac die together), kill8 (an enemy champion within 6 dies within 8), net3/taken3/dealt3.
- Base rates in contact: our bodies die within 8 rounds 13.1% (other teams' bodies 7.7%); kill8 10.9% vs 16.0%.

## Model results (5-fold GroupKFold by game; "us" = held-out rows of our bot's bodies)
| model (die8) | AUC all | AUC us | Brier us |
|---|---|---|---|
| bot's own estimate (log advantage, re-implemented) | 0.660 | **0.601** | - |
| (final dataset: Chebyshev-8 own vision; numbers below are from it) | | | |
| logistic, 57 features | 0.830 | 0.806 | 0.0937 |
| logistic + "our bot" flag (exported) | 0.834 | 0.806 | 0.0925 |
| tree depth 5 | 0.780 | 0.742 | 0.0988 |
| boosted trees (sklearn HistGB, 200 x 15 leaves; exported as `ml2_gb`) | 0.856 | 0.830 | 0.0888 |
| logistic on our bodies only | - | 0.807 | 0.0932 |
| logistic without contest games | 0.839 | 0.812 | 0.0773 |
| kill8, logistic + flag | 0.838 | 0.883 | 0.0683 |
- Calibration of the logistic on our bodies is good: predicted 0.034 / 0.072 / 0.140 / 0.243 / 0.384 / 0.668 vs real 0.035 / 0.073 /
  0.143 / 0.256 / 0.385 / 0.607 in the bins [.02,.05) ... [.5,1].
- The "our bot" flag: +0.21 standardized (about x1.7 odds): in the same visible state our bodies die more often than the other teams'.
- Largest standardized coefficients (with contest): own health -0.60, round +0.51, allies alive -0.29, enemies within 3 +0.27,
  ally health within 7 -0.26, health fraction -0.26, the bot's log advantage -0.21, lowest enemy health within 5 -0.19, enemy health
  within 5 +0.17 (collinear set: individual signs are not causal). Without contest: health -0.99, enemy damage within 7 +0.32.

## Where combat() is wrong against real opponents (`ml2_diag.py`, held-out predictions, our bodies)
- The bot's estimate says fight (adv >= 1.3) in 12,264 + 2,536 + 806 + 453 + 154 contact rows; where the model gives P(die8) 0.3-0.5
  the body died 45% of the time, >= 0.5: 71% (kill8 there 26% / 33%). In reach with adv >= 1.3 and P >= 0.3: 516 rows, 48-71% died.
- High-risk rows (P >= 0.3), what the body did next round: hit a champion 21% -> died 59% (kill8 21%); moved away 30% -> died 26%;
  neither 53% -> died 55%. The other teams: 51% / 28% / 55%. (Observational: moving away was possible in those rows.)
- 841 of our death events: 74% had P >= 0.3 in the 8 rounds before (85% >= 0.2); 655 started at >= 60% health, 469 of them flagged.
  The first flag comes a median 3 rounds before the last contact row.
- Thresholds on our contact rows: P >= 0.3 flags 11.5% of rows (died 48%, covers 42% of the death rows), >= 0.4 7.3% (55%, 31%),
  >= 0.5 4.8% (61%, 22%).

## States combat() calls winning that kill us (our ladder rows, in reach, bot adv >= 1.3, model P >= 0.3: 554 rows, 56% died;
## same with P < 0.1: 2,071 rows, 4% died)
- Profile (deadly vs safe): own health 37% vs 82% (374 vs 1,266), Cassi/Issac 56% vs 17% (Issac 39%), enemies within 3: 1.5 vs 0.7,
  allies within 5: 2.1 vs 1.7 (the team estimate pools the allies' health, so a low body in a winning team fight still stays and is
  focused), can_escape (bot heuristic) 32% vs 64%, killable 5% vs 18%.
- In reach, no kill (our rows): stepping away halves deaths even where combat() says we cannot escape: P 0.3-0.5, can_escape 0:
  hit 416 rows died 51% (kill8 20%), away 309 died 29% (10%); P >= 0.5: hit 74%, away 38%. With can_escape 1: 52% vs 23%, 70% vs 35%.
  The other teams show the same (43% vs 24%; 71% vs 48%). Hence the switch `ml2_cornered` (the model veto also applies there).

## Calibration on local games (the proxies are weaker killers than the ladder teams)
- 6 local games `_ch2` play vs `_px9` (eight, fragment, swirl, collision, interlock, packs; decoded with the same pipeline, 4,836 rows of
  our bodies): the exported logistic predicts 13.9% deaths within 8, real 9.1%. By bin (local vs ladder real rate): P 0.1-0.2: 6.8% vs
  14.3%; 0.2-0.3: 13.0% vs 25.5%; 0.3-0.5: 25.8% vs 39.9%; >= 0.5: 61.4% vs 61.2%. In the same visible state our bodies die about half
  as often against `_px9` as against ladder teams (except in the clearly lost states): a ladder-calibrated threshold is about 1.5-2x too
  cautious locally, so local screens understate what the switch does on the ladder.

## Bot integration (`bots/_x_ml2`, all switches 0 = `_ch2`)
- `ml2_features()` computes the 58 features in the dataset order from what the body sees; `ml2_logit()`; weights `ml2_model.h`.
- `ml2_cornered` 1: `ml2_leave` also when combat() thinks a chaser cannot be outrun. `ml2_gb` 1: P from the exported boosted trees
  (200 trees, 5,800 nodes, `ml2_gb_die8()`; arrays checked against sklearn: max |diff| 0.0; rollovers on gen16_98x99 unchanged, 8 / team).
- In combat(), after every existing rule (commit, burst_exit, px targeting): `ml2_leave` T: drop a fight we can escape with no kill
  this turn (ours or the px team kill) when P(die8) >= T; `ml2_hold` N: no proactive re-entry for N rounds after a model exit;
  `ml2_enter` T (+ `ml2_enter_die`): fight when P(kill8) >= T and P(die8) < ml2_enter_die (target within reach + 1, not at their spawn);
  `ml2_flee` T: not in reach and not fighting, walk home when P(die8) >= T and an enemy is within flee_dist (not while capturing).
- Parity (`ml2_parity.py`, eight vs `_mite`, 685 matched rows): self features exact; enemy/ally counts 77-94% exact (the replay
  snapshot is the end of the previous round, the bot acts mid-round); log advantage mean -0.56 (dataset) vs -0.45 (bot).
  Vision probe: own vision is a Chebyshev square of radius 8 (walls block), the visible-tile mask is the team's union.
- Fuel: one pass over <= 10 bodies and the camp groups near us, then 58 multiply-adds: negligible.

## Screen (official 34 vs `_ch2` + `_mite _ifish _px9 _snk _fA`; `_ch2` pooled 129/170)
| variant | switches | pooled | h2h vs `_ch2` | our deaths (5 proxies) | their deaths | games changed |
|---|---|---|---|---|---|---|
| `_ml0` | control | (34/34 identical vs `_mite`) | | | | 0 |
| `_ch2` | baseline | 129/170 75.9 | - | 1,490 | 2,052 | - |
| `_mll40` | ml2_leave 0.4 | 130/170 76.5 | 16/34 (deaths 328-329) | 1,437 | 2,063 | 50 of 170 |
- In local games vs `_px9` (6 official maps, debug build) the model's P is >= 0.3 in 14.6% of contact evaluations (ladder rows: 11.5%):
  the proxies do produce the states the model flags; the veto only acts on the subset where we fight, have no kill and can escape.
- What the high-risk rows of our ladder games did next (`hit` / `moved away` / `neither`) broken down for `neither` (P >= 0.3, 2,623 rows):
  moved closer or sideways 2,073 (died 55%), stood 434 (53%), hit a camp 71 (52%), recalled 44 (75%). The bot walks toward or along
  the enemy in most high-risk states it does not fight in: that is what `ml2_flee` targets.

## Next
Screen results; then pick the best threshold, run the 88 distinct maps and the rollover check.
