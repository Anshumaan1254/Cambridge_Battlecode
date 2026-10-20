# x_ml4: the fight / danger model retrained on the patch-3.0 Nyx games (ml4, session 14)

Baseline `bots/_g5br` (= GOD v5: v4 + `burst_retreat` 1.2; the coordinator moved the base from `_x_g5` + the `_g5u` switches to
`_g5br` at 11:20 UTC). Copy `bots/_x_ml4` = `_g5br` with a new `src/ml2_model.h` (the only change); patch `experiments/wip/x_ml4.patch`
(= `diff -ruN bots/_g5br/src bots/_x_ml4/src`; rebuild: `cp -r bots/_g5br bots/_x_ml4 && rm -rf bots/_x_ml4/.cambc && (cd bots/_x_ml4 &&
patch -p1 < ../../experiments/wip/x_ml4.patch)`). Variants `_g5ml` = `SRC=bots/_x_ml4 tools/variant.sh _g5ml` (v5 switches, new model),
`_g5ml30` = + `ml2_leave=0.3f ml2_flee=0.3f`. Reference: `_g5br` 27/40 vs `_g4` on `maps/nyx_new` + `maps/comp30` (deaths 654-727);
earlier base `_g5u` (v3 switches + `altar_no_camp` 2) 25/40 (708-692).

Tools (tools/ml/): `ml2_decode.py` (now also names the maps of `maps/comp30` / `maps/nyx_new`, and falls back to the engine of an
older replay's format for the map dump: mapinfo.mjs only tries the newest engine), `ml2_dataset.py` (now per-patch base
stats and kits: `patch_of(set)` = 3 for sets named `nyx*` / `p3*` / `local3*`, else the Oct 18-19 stats; Tavi's stun 1.4 x focus,
Heart of Ruin shield / damaging dash counted like the bot's `best_mod()`; Prism's passive focus per gem; Nyx sets: we are team 0),
`ml4_train.py` (the comparison below and the header export). Reproduce: `python3 tools/ml/ml2_decode.py DEC nyx_new=experiments/nyx_oct20/new
nyx_old=experiments/nyx_oct20/old ladder_oct19b=experiments/ladder_oct19b ... intercon_oct18=experiments/intercon_oct18`,
`python3 -I tools/ml/ml2_dataset.py DEC nyx.npz --sets nyx_new,nyx_old`, `python3 -I tools/ml/ml2_dataset.py DEC old.npz --sets <the 7 old sets>`,
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python3 -I tools/ml/ml4_train.py old.npz nyx.npz [--export ml2_model.h --export-cfg old+nyx:4]`.

## Data
- Patch-3.0 sets (cambc 3.0.1 engine `v1_0_0`; we are side A = team 0 in every game; set names `nyx_new`, `nyx_old`, `losses_oct20`):
  the 20 Nyx games (`experiments/nyx_oct20/new`, `old`, GOD v2 vs Nyx) and the 25 ladder losses of GOD v3 vs five top teams
  (`experiments/losses_oct20/an/replays`, 5 wins, our deaths 121 to their 7 in fights they opened on our half). Contact rows (an
  alive body with an alive enemy champion within 7, censored rows within 8 rounds of the end dropped): Nyx 56,821 (ours 30,960, theirs
  25,861; die8 in contact **ours 5.9%, theirs 5.5%**; the Oct 18-19 ladder data: 13.1% / 7.7%), losses 54,557 (ours 27,994 at **12.7%**,
  theirs 26,563 at 4.9%). Per Nyx game (our rows / die8): nx50x41 4,264 / 0.007 (the GOD v2 altar stall: six bodies next to the sleeping
  monolith for 1,000+ rounds, enemies passing by; fixed in v3, so that game is skipped in the main evaluation), nx50x50 3,598 / 0.080,
  contest_v3 3,673 / 0.078, nx31x31_c4 2,915 / 0.108, eight_v3 2,171 / 0.046; nx60x60 146, nx100x100 59, expanse_v3 20 rows only.
- Old sets (the session-13 data re-decoded: ladder_oct19b, ladder_oct18, sneaky_oct18, interwin_oct19, interwin_oct18, ladder_top3,
  intercon_oct18): 241,372 rows, 187 games; 222,407 rows / 160 games after dropping 8 duplicate games and the censored rows (= the
  session-13 dataset exactly: the model refit on them alone reproduces the shipped header: same AUC and Brier to 3 decimals).
- The old replays decode with the engine of their format (the decoder falls back from `v1_0_0` to `v0_0_3`; Cassi 700 HP checked), the
  patch-3.0 replays with `v1_0_0`. `bush4` (feature 18) is not computed by the bot (`f[18]` stays 0): left out of every fit, exported as 0
  (the first export of this session had a 0.39 weight on it: caught before any game).

## Model comparison (die8; held-out by game: 5 folds over the 43 patch-3.0 games, the 160 old games always in the training fold;
## logistic regression C = 1 on standardized features + the 'us' flag; `+p3` = a patch-3.0 indicator column folded into the bias)
Rows of our bodies (us = 1) in the patch-3.0 games, nx50x41 (GOD v2 stall) skipped; `them` = the opponents' bodies:

| model | AUC us | Brier us | log loss us | AUC them | Brier them | per set AUC us (losses / nyx_new / nyx_old) | folds better than shipped | bootstrap dAUC us (95%) |
|---|---|---|---|---|---|---|---|---|
| **shipped header** (160 old games) | 0.796 | 0.0726 | 0.2569 | 0.902 | 0.0437 | 0.801 / 0.801 / 0.782 | - | - |
| old only (refit on the re-decoded old games) | 0.796 | 0.0726 | 0.2566 | 0.902 | 0.0378 | 0.802 / 0.801 / 0.782 | 5/5 (by 0.000-0.001) | +0.0004 [+0.0001, +0.0007] |
| (a) patch-3.0 games only (43 games) | 0.806 | 0.0638 | 0.2308 | 0.900 | 0.0365 | 0.811 / 0.816 / 0.783 | 3/5 | +0.0105 [+0.0008, +0.0210] |
| (b) old + patch-3.0, weight 1 | 0.800 | 0.0660 | 0.2369 | 0.903 | 0.0369 | 0.803 / 0.813 / 0.783 | 4/5 | +0.0041 [-0.0003, +0.0088] |
| (b) old + patch-3.0, weight 1, +p3 | 0.801 | 0.0645 | 0.2320 | 0.903 | 0.0374 | 0.806 / 0.807 / 0.787 | 5/5 | +0.0055 [+0.0020, +0.0090] |
| (b) old (other teams' bodies only) + patch-3.0, weight 1 | 0.798 | 0.0647 | 0.2334 | 0.904 | 0.0369 | 0.801 / 0.811 / 0.782 | 4/5 | +0.0022 [-0.0023, +0.0071] |
| (b) old + patch-3.0, weight 4 | 0.804 | 0.0643 | 0.2317 | 0.904 | 0.0365 | 0.808 / 0.819 / 0.785 | 5/5 | +0.0086 [+0.0017, +0.0160] |
| **(b) old + patch-3.0, weight 4, +p3 (exported)** | **0.805** | **0.0639** | **0.2303** | 0.903 | 0.0369 | **0.810 / 0.813 / 0.790** | **5/5** | **+0.0097 [+0.0037, +0.0163]** |
| (b) old (other teams only) + patch-3.0, weight 4 | 0.804 | 0.0640 | 0.2310 | 0.904 | 0.0364 | 0.807 / 0.818 / 0.785 | 4/5 | +0.0083 [+0.0016, +0.0157] |

- With the Nyx games alone as the evaluation set (before the 25 losses arrived; 19 games, nx50x41 skipped) every retrained model only
  tied the shipped one: AUC us 0.792 shipped vs 0.795 (w1+p3) / 0.797 (w4+p3), bootstrap +0.003 [-0.001, +0.006] / +0.006 [-0.003, +0.013];
  with the stall game included 0.812 vs 0.812 / 0.809. The 25 losses (our bodies 12.7% deaths in contact, Power-stacked killers) are
  what makes the refit a measurable gain: on them the shipped model scores 0.801, the exported one 0.810.
- Calibration: the shipped model over-predicts our deaths in the patch-3.0 games about 2x (predicted 0.34 / 0.45 / 0.59 / 0.82 vs real
  0.13 / 0.21 / 0.30 / 0.51 by bin on the Nyx rows; Brier 0.073 vs 0.064): longer games, thinner contact, and the bot already leaves at
  P >= 0.4 (the labels are under that policy). The retrained model's P >= 0.4 flags 3.4% of our rows (die 51%) where the shipped one flags
  7.7% (die 36%): **at the same threshold the new model exits about half as often, from the deadlier half of the old flags** (the shipped
  model's P >= 0.6 flags 2.9% of rows at 50%: the recalibration alone is worth about a threshold of 0.6 on the old weights; the ranking gain
  on top of it is the +0.010 AUC).
- Robustness: with the GOD-v2 stall game (nx50x41, 4,264 of our rows at 0.7% deaths) included in the evaluation the gain vanishes
  (AUC us shipped 0.808 vs w4+p3 0.808 / w1+p3 0.810; bootstrap +0.001 [-0.009, +0.009] / +0.002 [-0.003, +0.006]; the Brier gain stays,
  0.068 vs 0.060): one pathological game of a bot that no longer stalls decides between "tie" and "+0.010". Read the +0.010 as the gain
  on games like the 25 losses and the normal Nyx games, with a 95% interval that just clears 0.
- Nothing else changed: 58 features in the bot's order, kill8 refit the same way (unused: `ml2_enter` 0), the boosted-tree arrays copied
  from the old header unchanged (`ml2_gb` 0). Export self-check: the raw weights reproduce sklearn's predict_proba (max |diff| 1.4e-7).
- What changed in the weights (effect per sd of the feature on our Nyx rows; `$S/wdiff.py`): the mean logit on our Nyx rows falls from
  -2.76 to -3.33 (the calibration: bias -0.62 -> -1.54 with the patch-3.0 term), the two logits correlate 0.90. Largest moves: enemy damage
  within 7 (`dps_e7`) x3 (+0.15 -> +0.45 per sd: the Power-stacked killers), own `hp` more negative (-0.99 -> -1.29), `max_hp` less
  (-0.37 -> -0.10), `d_min` much less (+0.11 -> +0.03: distance matters less when the killers hit from 4-5), `round` a bit less (+0.60 -> +0.48),
  the ally block re-balanced (`hp_a5` -0.11 -> +0.60, `n_a5` +0.10 -> -0.24, `hp_a7` -0.43 -> -0.62, `n_a7` +0.08 -> +0.31: collinear, net
  about the same), `gems` -0.22 -> +0.09 (a carrier near enemies is a target now), `is_Stellar` +0.01 -> -0.06.

## Ledger (h2h vs `_g4`, both sides, --jobs 1; `_g5br` = GOD v5 27/40 on the 20 maps, deaths 654-727)
- Pool: `maps/nyx_new` + `maps/comp30` + `maps/loss_oct20` (21 maps, 42 games). Commands (resumable; rows land in
  `experiments/results/ledger_v3/_g5ml_vs__g4.jsonl`, `_g5ml30_vs__g4.jsonl`, and `_g5br_vs__g4.jsonl` for the new map):
  `python3 tools/ledger.py run _g5ml _g4 --maps 'maps/nyx_new/*.map26a,maps/comp30/*.map26a,maps/loss_oct20/*.map26a' --jobs 1`, the same for
  `_g5ml30`, then `python3 tools/ledger.py run _g5br _g4 --maps 'maps/loss_oct20/*.map26a' --jobs 1`;
  `python3 tools/ledger.py table _g5ml --opps _g4 --maps '...'`. Source hashes: `_g5br` 2b1f22387b05, `_g5ml` 36ae4426efe2, `_g5ml30` 58b6426f021b.
- (running since 11:37 UTC; results below when they land)
