# x_ml2: fight / danger model learned from real ladder games (agent ml2, session 13)

Baseline `bots/_ch2` (legend_m14_commit). Copy `bots/_x_ml2` (switches default off), patch `experiments/wip/x_ml2.patch`
(includes the new file `src/ml2_model.h`). Rebuild: `SRC=bots/_ch2 tools/variant.sh _x_ml2 && (cd bots/_x_ml2 && patch -p1
--no-backup-if-mismatch < ../../experiments/wip/x_ml2.patch)`, then `SRC=bots/_x_ml2 tools/variant.sh _mlXX key=val`.
Stacked on the coordinator's `_cand2`: `bots/_x_ml2c` = `_cand2` src + the patch (`experiments/wip/x_ml2_on_cand2.patch` = its diff to
`_cand2`; rebuild `SRC=bots/_cand2 tools/variant.sh _x_ml2c && (cd bots/_x_ml2c && patch -p1 < ../../experiments/wip/x_ml2_on_cand2.patch)`).
**Ship candidate (coordinator, 00:05): `_mlkc40` = `SRC=bots/_x_ml2c tools/variant.sh _mlkc40 ml2_leave=0.4f ml2_flee=0.4f ml2_cornered=1`.**

Scripts (tools/ml/): `ml2_decode.py` (decode replay folders), `ml2_dataset.py` (contact dataset), `ml2_train.py` (models, CV, export of
the logistic weights and of the boosted trees as `ml2_model.h` arrays), `ml2_diag.py` (where the bot's estimate is wrong), `ml2_parity.py`
(in-game features of a `--define "ML2_DEBUG 1"` build vs the dataset's on the same game), `ml2_sum.py` (pooled proxy wins + deaths +
identical games + h2h). sklearn: `pip install scikit-learn --break-system-packages`; run it with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`
(multithreaded BLAS under the shared load stalled for 10 minutes).
Reproduce the model: `python3 tools/ml/ml2_decode.py DEC set=dir ...` (sets below), `python3 -I tools/ml/ml2_dataset.py DEC all.npz`,
`python3 -I tools/ml/ml2_train.py all.npz --label die8 --feats <all but bush4> --only-lr --export w_die8.h --export-gb gb_die8.h` (same for kill8
without --export-gb), then `ml2_model.h` = header + `ML2_NF = 58` + the three files.

## State (update at every step; container clock)
- 00:20: official 34 on the stack: `_mlkc30` 142/170 (h2h vs `_cand2` 17/34), `_mlka40` (adapt) 146/170 (20/34): `_mlkc40` (149, 19/34)
  stays the pick. Queue continues with ablations on `_ch2`: `_mlc40` (no flee), `_mlca40`, `_mlgc40` (boosted trees).
- 00:13: wide validation of `_mlkc40` done: 67 maps vs the 5 proxies 475/670 (`_ch2` 452), our deaths -13%, h2h vs `_cand2` 77/134,
  vs `_ch2` 71/134. Queue (`$S/ml2/queue9.sh`): `_mlkc30` and `_mlka40` (official, vs `_cand2` + proxies + `_ch2`), then `_mlc40`,
  `_mlca40`, `_mlgc40` on `_ch2`.
- 00:05: coordinator: `_mlkc40` is the ship candidate. Running (`$S/ml2/queue8.sh`, log `$S/ml2/screen5.log`): wide validation of
  `_mlkc40` (`$S/ml2/wide2.sh`: maps/*.map26a + maps/pad17 + maps/gen2 vs `_cand2`, `_ch2` and the 5 proxies; the coordinator runs `_cand2` /
  `_ch2` vs the proxies on the same pools), then `_mlka40` (stacked + adapt) vs `_cand2` + proxies + `_ch2`, then `_mlc40`, `_mlca40`,
  `_mlgc40`, `_mlc30` on `_ch2`. `_mlcf40`'s 88-map run skipped (coordinator). Summaries: `BASE=_cand2 python3 tools/ml/ml2_sum.py --maps
  'maps/*.map26a,maps/pad17/*.map26a,maps/gen2/*.map26a' _cand2 _mlkc40` and `OPPS=_ch2 ...`.
- 00:01: health-only ablation `_mlhp45`: 133/170 (model 141).
- 23:57: stacked `_mlkc40`: 149/170 vs `_cand2` 141, h2h 19/34 vs `_cand2`, 22/34 vs `_ch2`. Rollovers clean (below).
- 23:51: `_mlcf40` (leave 0.4, flee 0.4, cornered) on `_ch2`: 141/170 vs 129, h2h 20/34 (deaths 299-407), our deaths -19%.
- 23:30: model trained, ported (features, logistic, boosted trees), parity checked; control `_ml0` 34/34 identical to `_ch2` vs `_mite`.

## Data (187 replays decoded, 179 distinct; 160 games with contact rows after dropping 8 duplicates and the censored ends)
- Sets: ladder_oct19b (50, our side from index.json), ladder_oct18 (17, us = team 0, legend_st), sneaky_oct18 (17, us = team 0,
  legend_m8/m10), interwin_oct19 (45, IC vs others), interwin_oct18 (13, Mite vs ifish), ladder_top3 (15, from `repl/`), intercon_oct18 (30).
  Duplicates (same game in two sets, fingerprint of drafts + final round + round-100 state) dropped: 8.
- Row = alive body with an alive enemy champion within 7 (true positions): 222,407 rows (43,164 of our bot's bodies).
- Features (58, `ml2_dataset.FEATURES`; `bush4` not used): own health / max / fraction, strength, focus, damage per round as combat()
  counts it, burst of ready spells, ranged, Cassi/Issac, bag, own spell / dash ready, walking distance home, own spawn, enemy half /
  neutral band, round, in a bush, type flags; visible enemies (Chebyshev <= 8, a bush hides unless we stand in a bush within 2): counts
  within 3/5/7, health and damage sums within 5/7, ready burst within 5, ready stuns / areas within 5, nearest distance and its health
  fraction, lowest health within 5, a kill this turn, melee/dash chasers within 3, Varg within 2, Ren within 4, enemies alive, an enemy
  on its spawn within 7; visible allies within 3/5/7, their health, damage within 6, allies alive, allies below 30% within 5; damaged
  live camps within 3; a re-implementation of combat()'s estimate (log advantage, in reach, incoming, can escape, isolated).
  Spell readiness from the cast events (cooldown 8: a slot cast in round t is ready at t + 8; checked: min gap 8).
- Labels: die4, die8 (this body, Cassi/Issac die together), kill8 (an enemy champion within 6 dies within 8), net3/taken3/dealt3.
- Base rates in contact: our bodies die within 8 rounds 13.1% (other teams' bodies 7.7%); kill8 10.9% vs 16.0%.

## Model results (5-fold GroupKFold by game; "us" = held-out rows of our bot's bodies)
| model (die8) | AUC all | AUC us | Brier us |
|---|---|---|---|
| bot's own estimate (log advantage, re-implemented) | 0.660 | **0.601** | - |
| logistic, 57 features | 0.830 | 0.806 | 0.0937 |
| logistic + "our bot" flag (**exported, used**) | 0.834 | 0.806 | 0.0925 |
| tree depth 5 | 0.779 | 0.754 | 0.0985 |
| boosted trees (sklearn HistGB, 200 x 15 leaves; exported as `ml2_gb`) | 0.856 | 0.830 | 0.0888 |
| logistic on our bodies only | - | 0.807 | 0.0934 |
| logistic without contest games | 0.839 | 0.812 | 0.0773 |
| logistic without the round feature | 0.827 | 0.797 | 0.0928 |
| kill8: bot estimate / logistic + flag / boosted | 0.64 / 0.838 / 0.876 | 0.70 / 0.882 / 0.908 | - / 0.0683 / 0.0634 |
- Calibration of the logistic on our held-out bodies: predicted 0.034 / 0.072 / 0.140 / 0.243 / 0.382 / 0.668 vs real 0.035 / 0.073 /
  0.144 / 0.251 / 0.388 / 0.602 in the bins [.02,.05) [.05,.1) [.1,.2) [.2,.3) [.3,.5) [.5,1].
- The "our bot" flag: +0.21 standardized (about x1.7 odds): in the same visible state our bodies die more often than the other teams'.
- Largest standardized coefficients: own health -0.55, round +0.5, allies alive -0.29, enemies within 3 +0.27, ally health within 7
  -0.26, health fraction -0.26, the bot's log advantage -0.21, lowest enemy health within 5 -0.19, enemy health within 5 +0.17
  (a collinear set: single signs are not causal; without contest health -0.99, enemy damage within 7 +0.32).

## Where combat() is wrong against real opponents (`ml2_diag.py`, held-out predictions, our bodies; `$S/ml2/diag_final.txt`)
- combat() estimate says fight (adv >= 1.3): with model P 0.3-0.5 the body died 47% (493 rows), P >= 0.5 70% (168 rows); in reach
  and P >= 0.3: 554 rows, 56% died (with P < 0.1: 2,071 rows, 4% died).
- Profile of those "bot: winning, model: deadly" states vs the safe ones: own health 37% vs 82% (374 vs 1,266), Cassi/Issac 56% vs 17%
  (Issac 39%), enemies within 3: 1.5 vs 0.7, allies within 5: 2.1 vs 1.7 (the team estimate pools the allies' health, so a low body in
  a winning team fight stays and is focused), can_escape (bot heuristic) 32% vs 64%, killable 5% vs 18%.
- High-risk rows (P >= 0.3), what the body did next: hit a champion 20% -> died 60% (kill8 22%); moved away 30% -> 26% (6%);
  neither 53% -> 55% (of these: moved closer or sideways 2,073 rows 55%, stood 434 53%, hit a camp 71, recalled 44 75%).
  The other teams: 51% / 28% / 55%.
- In reach, no kill: stepping away halves deaths even where combat() says we cannot escape: P 0.3-0.5, can_escape 0: hit 416 rows
  died 51% (kill8 20%), away 309 died 29% (10%); P >= 0.5: 74% vs 38%. can_escape 1: 52% vs 23%, 70% vs 35%. Other teams 43% vs 24%,
  71% vs 48%. (Observational; it is the basis of `ml2_cornered`.)
- Is P a good signal for *leaving*? A two-action logistic (in reach, no kill, rows where the body either hit a champion or stepped
  away next round, all teams, 20,000 rows, action x feature interactions, games kept whole) ranks the benefit of stepping away almost
  exactly like P: by quartile of P, deaths hit vs away 2% / 1%, 8% / 4%, 21% / 10%, 56% / 27%, kill8 51% / 19%, 41% / 19%, 36% / 15%,
  25% / 12%. Leaving pays only in the top quartile (P >= ~0.26: -0.29 deaths for -0.13 kills); below it, it costs kills for little
  safety. So a threshold on P (0.3-0.4) is the right decision rule; 0.4 is on the safe side.
- 841 of our death events: 75% had P >= 0.3 in the 8 rounds before (86% >= 0.2); 655 started at >= 60% health, 473 of them flagged;
  the first flag comes a median 3 rounds before. Thresholds on our contact rows: >= 0.3 flags 11.4% (died 48%), >= 0.4 7.2% (55%),
  >= 0.5 4.8% (60%).

## Calibration on local games (the proxies are weaker killers than the ladder teams)
- 6 local games of `_ch2` play vs `_px9` (eight, fragment, swirl, collision, interlock, packs; 4,836 rows of our bodies): the model
  predicts 13.9% deaths within 8, real 9.1%. Real rate by bin, local vs ladder: P 0.1-0.2 6.8% vs 14.3%; 0.2-0.3 13.0% vs 25.5%;
  0.3-0.5 25.8% vs 39.9%; >= 0.5 61.4% vs 61.2%. Locally our bodies die about half as often in the same state (except in clearly lost
  states): a ladder-calibrated threshold is 1.5-2x too cautious locally, so local screens understate the ladder effect.

## Bot integration (`bots/_x_ml2`, all switches 0 = `_ch2`)
- `ml2_features()` (brain.cpp) computes the 58 features in the dataset order from what the body sees; `ml2_logit()` / `ml2_gb_die8()`
  return the logit; weights / trees in `ml2_model.h`. Computed in combat() only when a visible enemy is within 7.
- Switches (params.h), applied after every existing rule of combat() (commit, burst_exit, px targeting):
  `ml2_leave` T: drop a fight with no kill this turn (ours, or the px team kill) when P(die8) >= T and we can escape;
  `ml2_cornered` 1: also when combat() thinks a chaser cannot be outrun (the cornered rule would trade);
  `ml2_flee` T: not in reach, not fighting: walk home when P(die8) >= T and an enemy is within flee_dist (not while capturing);
  `ml2_hold` N: no proactive re-entry for N rounds after a model exit; `ml2_enter` T + `ml2_enter_die`: fight when P(kill8) >= T and
  P(die8) small; `ml2_gb` 1: the boosted trees instead of the logistic (arrays checked against sklearn: max |diff| 0.0);
  `ml2_adapt` lr (+ `ml2_adapt_min/max`): in-match recalibration of a per-body logit offset (every evaluation waits 8 rounds for its
  label; on our first dead turn those within 8 rounds are 1). Debug game vs `_px9` (fragment, lr 0.05): final offsets -0.17, -0.24,
  -0.48, -0.87 (the proxy kills less than the ladder teams). `ml2_hp_rule` H: ablation, the same veto from health < H alone.
- Parity (`ml2_parity.py`, eight vs `_mite`, 685 matched rows): self features exact; enemy/ally counts 77-94% exact (the replay snapshot
  is the end of the previous round, the bot acts mid-round); log advantage mean -0.56 (dataset) vs -0.45 (bot).
  Vision probe (`_ml2vis`): own vision is a Chebyshev square of radius 8 (walls block), the visible-tile mask is the team's union.
- How often it acts (`_mlcf40` settings, 6 debug games vs `_px9`, 2,933 evaluations): 35 vetoes, every one with can_escape 0 and in reach;
  9 flees. Without `ml2_cornered` the veto almost never fires (that is why `_mll40` / `_mlf40` changed little).
- Fuel: negligible (one pass over <= 10 bodies and the camp groups near us; 58 multiply-adds or 200 short tree walks). `_mlkc40` release
  games: gen16_98x99 vs `_mite` both sides 8 rollovers per team, all in rounds 1-3 (= `_cand2`); contest and eight vs `_fA` (48 and 14 of
  our deaths: the model runs every contact turn) 0 rollovers (= `_cand2`).

## Screen on `_ch2` (official 34 vs `_ch2` + `_mite _ifish _px9 _snk _fA`; `_ch2` pooled 129/170)
| variant | switches | pooled | per proxy (`_mite _ifish _px9 _snk _fA`) | h2h vs `_ch2` (deaths) | our deaths | their deaths |
|---|---|---|---|---|---|---|
| `_ch2` | baseline | 129/170 75.9 | 27 25 26 26 25 | - | 1,490 | 2,052 |
| `_ml0` | control | 34/34 games identical vs `_mite` | | | | |
| `_mll40` | leave 0.4 | 130/170 76.5 | 27 26 25 25 27 | 16/34 (328-329) | 1,437 | 2,063 |
| `_mlf40` | leave 0.4, flee 0.4 | 130/170 76.5 | 27 26 25 25 27 | 16/34 (328-329) | 1,441 | 2,050 |
| **`_mlcf40`** | **leave 0.4, flee 0.4, cornered** | **141/170 82.9** | 31 24 27 27 32 | **20/34 (299-407)** | **1,209** | 1,987 |
| `_mlhp45` | ablation: cornered veto from health < 45% | 133/170 78.2 | 29 27 24 25 28 | 20/34 (248-348) | 1,072 | 1,909 |
- The health-only rule cuts our deaths even more but wins 8 games fewer than the model: the model chooses better which low-health
  fights to drop (it keeps the ones the team wins; their deaths 1,987 vs 1,909).

## Stacked on `_cand2` (official 34; `_cand2` 141/170, deaths 1,315-2,063; control `_mlk0` 34/34 identical to `_cand2` vs `_mite`)
| variant | pooled 5 proxies | per proxy (`_mite _ifish _px9 _snk _fA`) | h2h vs `_cand2` | h2h vs `_ch2` | our deaths |
|---|---|---|---|---|---|
| `_cand2` | 141/170 82.9 | 29 24 27 31 30 | - | 20/34 | 1,315 |
| **`_mlkc40`** (leave 0.4, flee 0.4, cornered) | **149/170 87.6** | 28 27 29 32 33 | **19/34 (309-340)** | 22/34 (313-432) | 1,180 |
| `_mlkc30` (same at 0.3) | 142/170 83.5 | 30 24 28 30 30 | 17/34 (272-363) | 23/34 (259-392) | 1,154 |
| `_mlka40` (`_mlkc40` + ml2_adapt 0.05) | 146/170 85.9 | 27 27 28 31 33 | 20/34 (367-380) | 24/34 (287-386) | 1,157 |
- 0.3 drops more fights and loses some (the local proxies kill less than the ladder teams: a lower bar is too cautious here).
- The in-match recalibration is level with the fixed model locally (146 vs 149, h2h 20 vs 19): against ladder teams its offset should
  stay near 0, so it would behave like `_mlkc40` there; it is insurance if the final map pool or opponents differ. Not needed to ship.

## Wide validation of `_mlkc40` (generated 27 + pad17 16 + gen2 24 = 67 maps, 134 games per cell)
| pool (games per proxy) | `_ch2` vs 5 proxies | `_mlkc40` vs 5 proxies | per proxy `_mite _ifish _px9 _snk _fA` (`_ch2`) | h2h `_mlkc40` vs `_cand2` |
|---|---|---|---|---|
| generated maps/*.map26a (54) | 181/270 67.0 | 182/270 67.4 | 42 34 32 39 35 (38 34 36 36 37) | 28/54 |
| pad17 (32) | 118/160 73.8 | **128/160 80.0** | 27 23 25 25 28 (25 20 20 26 27) | 16/32 |
| gen2 (48) | 153/240 63.8 | **165/240 68.8** | 31 31 33 31 39 (25 29 29 34 36) | 27/48 |
| all 67 maps (134) | 452/670 67.5 (deaths 4,297-5,373) | **475/670 70.9** (deaths **3,725**-5,407) | 100 88 90 95 102 (88 83 85 96 100) | **77/134 57.5** (767-1,031) |
- h2h vs `_ch2` on the 67 maps: 71/134 (53.0%). `_cand2`'s own proxy cells on these pools: the coordinator's run (not in the ledger yet
  at 00:13; its partial h2h vs `_ch2`: 22/48 generated, 25/48 gen2).
- Weak spots: generated maps vs `_px9` (32 vs 36) and `_fA` (35 vs 37), `_snk` on gen2 (31 vs 34).

## Next
- Wide results; `_mlka40` (adapt) vs `_mlkc40`; thresholds 0.3 / 0.5 on the stack if CPU allows.
- Ideas not built: a decision model P(die | state, step away) vs P(die | state, hit) (two-model / T-learner on the action labels);
  danger-aware routing from the model (the high-risk rows where the bot walked closer); export of the kill8 trees for `ml2_enter`.
