# 18. The v9 upload and the improvement plan, measured on engine 3.0.4 (Oct 21)

Inputs from the user: `god_v9_adaptive.zip` ("an upgraded version of our current bot") and `GOD_Improvement_Plan.md` (1,373 lines,
now `docs/strategy_v2/GOD_Improvement_Plan_oct21.md`). Request: check whether the upgrade is really better, take over its better
parts, carry out the plan's tasks while testing that each one helps, and deliver the best bot as GOD v10.

Measurement protocol (doc 17, `experiments/pools/README.md`): engine 3.0.4, every map both sides, ledger `ledger_v3_0_4/`;
`tools/abstat.py` (win rate, 95% Wilson interval, per-map 2-0 / 1-1 / 0-2 and the sign test), `tools/abmargin.py` (the plan's INF-2:
mean gem margin per map with a bootstrap interval, and the paired design: two bots against the same opponent on the same map and
side). Tuning pools: `train156` (156 maps), its halves `train78a` / `train78b` (stage-1 screens use `train78a`), confirmation on the
held-out `test152`, then `all308` and the third-party proxies. Our reference is `_m1p3` (the dynamic draft + pocket fix, branch
`god-dynamic-draft-on`: 79.4% vs v8 on all 308 maps).

## 1. What the upload is

- `god_v9_adaptive/src` = the shipped GOD v8 (`submissions/history/god_v8_20261020.zip`) + `v9.patch` (+576 / -20 lines). Checked by
  reversing the patch: the result equals v8's sources byte for byte. Its README says it was compile-checked against a stub SDK and never
  played; it builds unchanged on the real SDK 3.0.4 (`bots/_v9up`).
- New: an opponent model (`opp.h/.cpp`: 30-round windows, contact share, CUSUM, trade balance, deaths on our half, race projection;
  plans FARM, DEFEND, PUNISH, HUNT, RACE, EVADE, DENY with a preset of threshold changes each; plan id in bit 7 of shared bytes 3-5,
  a contact bit in bit 7 of byte 2), `safety_range` (camps counted at their engine range in `safety()`), `enemy_comp_init` (enemy kits
  at start), `watchdog` (fallback turn after N throwing turns), `ring_reach` (objective ring: area reach = range + radius),
  `tavi_str` (Tavi builds strength), sparring personas `spar_*`.
- With every switch at its default it plays v8's games: 156/312 vs v8, every map 1-1 (4 large maps differ in detail with the same
  winners: unguarded per-turn instructions move fuel-floored scoring).

## 2. Is the upgrade better? (tuning half, 312 games each vs v8 `_v8k1`)

| Bot | Wins | 95% interval | Maps 2-0 / 1-1 / 0-2 | Sign p | Deaths ours-theirs |
|---|---|---|---|---|---|
| upload, defaults (`_v9x0`) | 156/312 | [44.5, 55.5] | 0 / 156 / 0 | 1.00 | 6,637-6,627 |
| **upload, every switch on (`_v9on`)** | **140/312 = 44.9%** | [39.4, 50.4] | 24 / 92 / 40 | 0.06 | 6,630-6,433 |
| opponent model + presets only (`_v9op`) | 140/312 = 44.9% | [39.4, 50.4] | 24 / 92 / 40 | 0.06 | 6,781-6,633 |
| `safety_range` only (`_v9sr`) | 160/312 = 51.3% | [45.8, 56.8] | 21 / 118 / 17 | 0.63 | 6,148-6,546 |
| `enemy_comp_init` only (`_v9ec`) | 156/312 = 50.0% | [44.5, 55.5] | 2 / 152 / 2 | 1.00 | 6,568-6,578 |
| `ring_reach` only (`_v9rr`) | 153/312 = 49.0% | [43.5, 54.6] | 0 / 153 / 3 | 0.25 | 6,692-6,633 |
| `tavi_str` only (`_v9ts`) | 157/312 = 50.3% | [44.8, 55.8] | 2 / 153 / 1 | 1.00 | 6,676-6,672 |
| our dynamic draft `_m1p3` (reference) | 257/312 = 82.4% | [77.8, 86.2] | 111 / 35 / 10 | <0.0001 | 3,472-6,867 |

Gem margin per map (`abmargin.py`): `_v9on` vs v8 -47.7 [-109, +7]; `_m1p3` vs v8 +476 [+409, +543].
**The upload against our 3.0.4 bot**: `_v9on` vs `_m1p3` 60/312 = 19.2% [15.2, 24.0], maps 9 / 42 / 105, deaths 6,650-3,806.
The port onto main is exact when off: `_yx0` (all off) vs v8 mirror-identical on 12 of 12 check maps (the 4 where the upload drifted
included); `_y0` (port + `pd_stat` 3 + `pocket_fix` 3) replays `_m1p3`'s games 24 of 24.

**Verdict: no.** With its features on, the upload loses to v8 (and it carries v8's pre-3.0.4 draft, which our 3.0.4 bot beats 79.4%).
The loss comes from the opponent model's presets.

## 3. Why the opponent model loses (the plan's ADP-1 dry run)

`_v9opd` = the upload with `opp_plan` 1, `opp_presets` 0 (plans computed and traced, not applied) and `OPP_TRACE`;
`tools/opptrace.py` on 12 maps x 2 sides per opponent:

| Opponent | Games that left FARM | Plan changes / game | Windows in DEFEND or PUNISH |
|---|---|---|---|
| v8 mirror (`_v8k1`) | 23 of 24 (96%) | 8.9 | 16-21% (r<400 / 400-700 / 700+) |
| mid-match invader persona (`_v9inv`: PUSH, enemy half x0.2, r400-700) | 23 of 24 | 8.2 | 16% / **47%** / 25% |
| our 3.0.4 bot (`_m1p3`) | 22 of 24 | 7.1 | 14% / 29% / 33% |

The plan's gate G2 asks for false alarms in under 10% of mirror games; the detector raises them in 96%. Real contact against an
ordinary farmer is far above the simulated 8% (mean 0.11-0.15 per window, 90th percentile 0.33-0.44), and deaths on our half happen
in ordinary play (the home-death fast path). The signal itself is real (DEFEND/PUNISH 47% of windows during the persona's raid vs
17% against the mirror), but the presets then play DEFEND (grouped, enemy half x2.5, smaller banks) against an even opponent for a
fifth of the game. Single-plan ablations (`opp_mask`) and a stricter detector (`_yopT`) are being screened on our 3.0.4 base.

Gate G3 (presets on: non-inferior on the normal pool, superior on the switcher pool) fails on both: normal pool 44.9% vs v8 (above);
**against the mid-match invader persona `_v9inv` it was built to counter (21-map pool, 42 games), model on `_v9op` 29/42, model off
`_v9x0` 32/42, paired margin -117.5 gems a map [-262.5, +33.1]**. Plain v8 already beats that invader 76%: in our code family raiding
is a weak strategy, so a counter-plan has little to gain and its false alarms cost farming.

**ADP-2's culprit search: each plan forced on for whole games** (`opp_force`, our 3.0.4 base, 21-map pool, 42 games each; FARM =
`_m1p3`, the plan's "perfect detector" case):

| Opponent (persona) | FARM | DEFEND | PUNISH | EVADE | HUNT |
|---|---|---|---|---|---|
| invader `_pnI` | **36** | 28 | 35 | 35 | 30 |
| v9 raider r400-700 `_pnV` | **28** | 27 | 22 | 28 | 22 |
| deathball `_pnD` | **41** | 39 | 39 | 40 | 39 |

No counter-plan beats plain farming even against the style it was written for; DEFEND (the answer to invaders) is the worst against
the invader. A better detector cannot make this layer pay: the presets themselves point the wrong way for our bot.

### 3b. Code review of the upload (what is right, what is fragile)

- It works: no compile error on the real SDK, no fault or exception in our games, every switch inert at its default (the guards
  reduce to v8's expressions), shared-memory bits consistent with v8's writers (`write_self` and the bag sum keep bit 7).
- The detector was tuned on synthetic contact streams (8% background); in real games against an ordinary farmer the contact share
  is 11-15% on average with a 90th percentile of 0.33-0.44 per window, so `hi_run` (>= 0.35 for 2 windows) is common.
- The home-death evidence counts every death of a body that held a claim on our half within 8 rounds, deaths to camps included
  (camp deaths are about a fifth of ours): ordinary farming deaths read as an invasion.
- The race plans stack on v8's own race mode (both add to `deny_bonus`, multiply `enemy_half_penalty`, lower `fight_margin`).
- Several per-turn additions were not behind their switch in the upload (`plan_now` / `rally_add` / `sparring_window()` in
  `update_mode()`, the radius sums in `respond_to_alert()`); fuel-floored group scoring then changes 4 of 156 maps' games even
  with every switch off. The port guards them (`experiments/wip/x_v10.patch`).
- `fallback_turn()` (the watchdog) uses only plain SDK calls inside `try`; with one body throwing on every turn after round 300 it
  keeps that body useful: 12/24 wins vs v8 against 10/24 without a watchdog (main's own `watchdog`: 13/24; no fault: 18/24).

## 4. The plan's work items: where each one stands

| Item | What it asks | Status here |
|---|---|---|
| INF-1 | adopt v9, real SDK, equivalence | done: builds on 3.0.4; defaults = v8's winners on 156/156 maps; the port onto main (`experiments/wip/x_v10.patch`) guards every line |
| INF-2 | paired runner, margins, CIs, verdicts | `tools/ledger.py` + `abstat.py` (Wilson, sign test) + new `abmargin.py` (paired margin, bootstrap, superior / non-inferior) |
| INF-3 | normal and switcher pools | normal: 8 ladder proxies + v8; switchers: `_v9inv` / `_v9rush` / `_v9late` (v9 personas on v8), `_px*` (session 14 personas); post-patch: `_pn*` (personas with the dynamic draft), `_k_fit`, `_k_ci`, `_q_s2v` |
| INF-4 | exceptions, fuel, plan traces | `EXC_TRACE` build + `tools/tracecount.py`; `FUEL_TRACE` / `tools/fueltrace.py`; `OPP_TRACE` / `tools/opptrace.py` |
| PAT-1 / FIX-6 | verify the patch numbers | done (doc 17): the 3.0.4 probe matches the notes; Heart of Ruin grows +12 focus, +3.5 strength, +100 health per shard (`experiments/results/probe_v3_0_4/`) |
| PAT-2 | re-derive draft priors | done and superseded: the dynamic draft (`pd_stat` 3) values every pick from engine stats x map features; refit on 17,004 games: no gain (log loss 0.6233 vs 0.6255), monolith-map terms no gain |
| PAT-3 | builds by evidence | `build_stat` margin 1.0 (`_m1b`) 250/312 vs v8 (reference 257), builds from the kit (`_m1g`) 249, `tavi_str` 49.7%, `tail_stat` 48.1%: no gain |
| PAT-4 | Prism bag | not applicable: the dynamic draft picks Prism in 3% of games |
| PAT-5 | re-calibrate ml2 | `ml2_gb` 41.7%, thresholds 0.15 / 0.30 49.4% / 45.5%, `ml2_adapt` 51.3% (stage 1): the shipped model stays |
| PAT-6 | post-patch sparring pool | built (see INF-3) |
| PAT-7 | re-tune thresholds | 20 single-parameter screens (5c); the leaders `isolated_fight_adv` 1.35 and `fight_margin` 1.4 are in v10 (alone on the held-out maps they were level: 5d) |
| FIX-1 | `safety_range` | v8 base 51.3%, our base 50.0% with fewer deaths: **in v10** |
| FIX-2 | watchdog | 0 exceptions in 72 traced games; with a body forced to throw every turn after r300 it keeps 12-13 of 24 wins (10 without): **main's `watchdog` is in v10** (v9's `watchdog9` stays off: same effect, one of them is enough) |
| FIX-3 | `enemy_comp_init` | 49.4%: changes almost no game, off |
| FIX-4 | `ring_reach` | 50.3%: the ring needs Prism or Tavi, which our draft rarely picks; off |
| FIX-5 | `tavi_str` | 49.7%: Tavi is in 2% of our drafts; off |
| FIX-7 | parameter hygiene | every new switch defaults to off and is listed with its result here and in `SUGGESTIONS.md`; v10's values are in section 6 |
| ADP-1 | dry run, detector tuning | done: fails gate G2 (section 3) |
| ADP-2 | presets on | fails gate G3 on the normal pool (44.9% vs v8); one plan at a time 47.4-52.6% on stage 1 (none significant); forced plans lose to plain farming (section 3) |
| ADP-3 / 4 / 5 / 6 / 7 | preset tuning, bandit reset, sharper evidence, classifier, bank cadence | depend on ADP-2 passing; ADP-6 is our `om_learned` classifier (session 14: not better) |
| UPG-1 / 2 | sightings + influence map | the influence part is our `threat_map`: 44.2% on our base (3.0.2: 124-129 vs v8's 140 over 4 cells); off |
| UPG-3 | carrier interception | our `gank`: 50.0% (session 14: not better); off |
| UPG-4 | wardens, locks, denial ramp | wardens = our `deny_altar` 46.2% (session 14: 12/32); `deny_ramp` (new) 50.0%: off |
| UPG-5 | fights from P(kill8), P(die8) | our `ml2_enter` 49.4% (session 13: ties); off |
| UPG-6 | two-sided frag map | our `death_learn` 47.4% (3.0.2: level); off |
| UPG-7 | scripted two-body plays | not built |
| DRF-1 / 2 / 3 | draft memory, zones, opening book | `dm_plan` (session 14: not better); zones closed in session 13 (bodies spread, fights lost); the opening book is replaced by the dynamic draft's map features |
| REL-1 / 2 / 3 | fuel, regression, release | done for v10 (`tools/finalcheck.sh`): section 5d |

### 4b. The second task file (`GOD_v9_Improvement_Tasks.md`, T01-T15; now `docs/strategy_v2/GOD_v9_Improvement_Tasks_oct21.md`)

Received at 15:30 UTC with the request to implement whatever it adds and deliver the best bot now. It is written against v8 for the
same balance patch (it calls it 3.1; it is our engine 3.0.4) and overlaps the first plan:

| Task | What it asks | Status here |
|---|---|---|
| T01 | count our own damaging dash (Heart of Ruin's landing) in `combat()`'s burst | **built** (`fix_my_dash`), stage 1 53.2% with our deaths 2,518 vs 2,667: **in v10** |
| T02 | re-tune the draft priors for the patch | superseded by the dynamic draft (`pd_stat` 3 has no per-champion prior); its ring-range gate concerns the objective draft our draft barely uses (Prism / Tavi in 2-3% of games) |
| T03 | flip 12 existing switches after A/B | screened: `ml2_adapt`, `ml2_gb`, `threat_map`, `mono_team` above / below; groups A (`fm_mode` 7, `hor_threat` 3, `mi_learn_burst` 1, `sup_mode` 7, `chan_keep` 2: `_t3A`) and B (`finish_race` 120, `mi_endgame_bank` 100: `_t3B`), `tail_stat` 1 (`_t3ts`) and the singles |
| T04-T07 | shared-memory v2, opponent model, plans, draft memory | the same design as the first plan's adaptive layer (sections 2-3: it loses, and its presets lose even when forced against their own target); our session-14 versions (`opp_model`, `dm_plan`) measured below v8 too |
| T08 | team influence map | our `threat_map` (screened: 44.2%) and `om_sight` (shared sightings, screened) |
| T09 | fight model: shields, stuns, hidden support, camp-damage calibration | **built**: `fm_buffs` (engine buff data: shield values and stuns of visible enemies and of us; both SDKs have the call) 48.1%, `farm_ema` (learned multiplier on the camp-damage model) 50.6%: both off; hidden support needs the plans (not built) |
| T10 | carrier interception, altar guard | our `gank` (50.0%) and `deny_altar` (46.2%) |
| T11 | non-stationary stance bandit | **built**: `bandit_discount` (off, not screened: the stance learner is neutral to begin with, and exploration measured -2 points in session 1; exploration and reset need the opponent model) |
| T12 | ward placement by information gain | not built (needs vision simulation per candidate tile; the plans' ward items measured nothing earlier) |
| T13 | watchdog, guaranteed draft pick, exception report | watchdog: exists (fault test above); **built** `draft_guard` (a pick that throws falls back to a legal pick); exceptions: `EXC_TRACE`, 0 in 72 games; **both in v10** (inert in normal play, insurance against a crash) |
| T14 | herding exploit, held spells, seeded tie-breaks, Prism bag, dead knobs | **built** a (`risky_persist`) 51.3% and b (`near_age_cap`) 49.4%: off; c (random tie-breaks against opponents who pre-position from our replays) cannot be measured locally; d not applicable (Prism 3%) |
| T15 | testing workflow | the ledger / abstat / abmargin protocol of this document |

## 5. Results of the re-screens on our 3.0.4 base

### 5a. The v9 switches on top of `_m1p3` (head-to-head vs `_m1p3`, tuning half, 312 games each)

| Variant | Wins | 95% interval | Maps 2-0 / 1-1 / 0-2 | Sign p | Margin per map (95%) | Deaths ours-theirs |
|---|---|---|---|---|---|---|
| every v9 switch (`_yall`) | 140/312 = 44.9% | [39.4, 50.4] | 18 / 104 / 34 | 0.04 | -65.4 [-123.7, -8.1] | 5,096-4,779 |
| opponent model + presets (`_yop`) | 143/312 = 45.8% | [40.4, 51.4] | 15 / 113 / 28 | 0.07 | -65.9 [-118.1, -18.8] | 5,324-4,874 |
| `safety_range` (`_ysr`) | 156/312 = 50.0% | [44.5, 55.5] | 19 / 118 / 19 | 1.00 | +18.8 [-22.6, +60.3] | 4,716-4,973 |
| `enemy_comp_init` (`_yec`) | 154/312 = 49.4% | [43.9, 54.9] | 3 / 148 / 5 | 0.73 | | 4,859-4,816 |
| `ring_reach` (`_yrr`) | 157/312 = 50.3% | [44.8, 55.8] | 2 / 153 / 1 | 1.00 | | 4,811-4,824 |
| `tavi_str` (`_yts`) | 155/312 = 49.7% | [44.2, 55.2] | 0 / 155 / 1 | 1.00 | | 4,840-4,806 |

The opponent model loses on our base as on v8's (about 66 gems a map, the interval below zero). `enemy_comp_init`, `ring_reach` and
`tavi_str` change almost no game (our draft has Tavi / Prism in 2-3% of games). `safety_range` is level with fewer deaths: a
candidate for the combined build, judged with the third parties.

### 5b. Our 3.0.4 bot against post-patch personas (the plan's INF-3 / PAT-6 pools; 21-map pool, 42 games each)

Personas = our 3.0.4 bot (dynamic draft) with a fixed style (`pxs_style`, session 14) or v9's `spar_*` raid window:

| Persona | `_m1p3` wins of 42 |
|---|---|
| farmer `_pnF` (stays home: enemy half x8, fight margin +0.6) | 24 |
| invader `_pnI` (raids: enemy-half groups x3) | 36 |
| deathball `_pnD` (one blob) | 41 |
| objective hunter `_pnO` (heavy groups and monoliths x3) | **22** |
| bush ambusher `_pnA` | 30 |
| altar denier `_pnL` | 28 |
| v9 mid-match invader `_pnV` (r400-700) | 28 |
| switcher `_pnS` (farmer, invader at 300, deathball at 800) | 34 |

Aggression loses to us; the economy styles (farming at home, taking the heavy groups) are the close match-ups, so the counters worth
building are economic, not reactive. A milder heavy-group bonus is in the screens (`heavy_value` 1.5 / 2 / 3).

### 5c. Stage 1: single switches on `_m1p3`, head-to-head vs `_m1p3` on `train78a` (78 maps x 2 sides = 156 games each)

A variant at >= 51% goes to stage 2 (the other 78 tuning maps). With 156 games one cell's standard deviation is about 4 points, so
stage 1 only removes clear losers.

| Variant (switch) | Plan item | Wins of 156 | Maps 2-0 / 1-1 / 0-2 | Deaths ours-theirs |
|---|---|---|---|---|
| `_yopD` v9 model, DEFEND only | ADP-2 ablation | 74 (47.4%) | 6 / 62 / 10 | 2,580-2,552 |
| `_yopP` PUNISH only | ADP-2 | 79 (50.6%) | 6 / 67 / 5 | 2,588-2,573 |
| `_yopH` HUNT only | ADP-2 | 81 (51.9%) | 9 / 63 / 6 | 2,558-2,561 |
| `_yopR` RACE only | ADP-2 | 82 (52.6%) | 4 / 74 / 0 | 2,526-2,563 |
| `_yopE` EVADE only | ADP-2 | 80 (51.3%) | 2 / 76 / 0 | 2,472-2,550 |
| `_yopN` DENY only | ADP-2 | 82 (52.6%) | 5 / 72 / 1 | 2,529-2,593 |
| `_yopT` all plans, stricter detector (contact 0.5 x 3 windows, 3 home deaths, depth 0.6, 3 losses) | ADP-1 | 81 (51.9%) | 12 / 57 / 9 | 2,638-2,578 |
| `_ydr` `deny_ramp` | UPG-4 | 78 (50.0%) | 0 / 78 / 0 | 2,543-2,547 |
| `_m2` draft weights refitted on 17,004 games | PAT-2 | 84 (53.8%) | 16 / 52 / 10 | 2,605-2,719 |
| `_m2c` refit + crowded-map terms | PAT-2 | 79 (50.6%) | 12 / 55 / 11 | 2,504-2,549 |
| `_zgb` `ml2_gb` (boosted trees) | PAT-5 / UPG-5 | 65 (41.7%) | 13 / 39 / 26 | 2,502-2,241 |
| `_zml15` `ml2_leave` = `ml2_flee` 0.15 | PAT-5 | 77 (49.4%) | 15 / 47 / 16 | 2,337-2,383 |
| `_zml30` ... 0.30 | PAT-5 | 71 (45.5%) | 13 / 45 / 20 | 2,837-2,415 |
| `_zma` `ml2_adapt` 0.02 | PAT-5 | 80 (51.3%) | 14 / 52 / 12 | 2,605-2,595 |
| `_zme` `ml2_enter` 0.4 (fight on P(kill8)) | UPG-5 | 77 (49.4%) | 11 / 55 / 12 | 2,670-2,652 |
| `_zad` `ally_defend` (new) | coordination audit | 79 (50.6%) | 5 / 69 / 4 | 2,550-2,508 |
| `_zad35` `ally_defend` with `ally_defend_hp` 0.35 | coordination audit | 75 (48.1%) | | |
| `_zfm12` / `_zfm14` / `_zfm15` `fight_margin` 1.2 / 1.4 / 1.5 | PAT-7 | 74 / 82 / 70 | 10/54/14, 11/60/7, 7/56/15 | |
| `_zfb80` / `_zfb95` `fight_back_margin` 0.80 / 0.95 | PAT-7 | 78 / 71 | 9/60/9, 4/63/11 | |
| `_zia11` / `_zia135` / `_zia15` `isolated_fight_adv` 1.10 / 1.35 / 1.50 | PAT-7 | 68 / **85** / 82 | 4/60/14, 15/55/8, 13/56/9 | 2,684 / 2,413 / 2,455 (vs 2,390 / 2,590 / 2,508) |
| `_zcau` isolated 1.35 + fight margin 1.4 | PAT-7 | 84 | 15 / 54 / 9 | |
| `_zcm65` / `_zcm85` `cornered_margin` | PAT-7 | 75 / 75 | | |
| `_ztm44` / `_ztm64` `tribute_min` | PAT-7 | 75 / 77 | | |
| `_zgv25` / `_zgv45` `gold_value` | PAT-7 | 80 / 82 | | |
| `_zbr10` / `_zbr14` `burst_retreat` | PAT-7 | 76 / 77 | | |
| `_zrh20` / `_zrh30` `retreat_hp` | PAT-7 | 75 / 80 | | |
| `_zbc30` / `_zbc55` `bag_caution` | PAT-7 | 76 / 78 | | |
| `_zgk` `gank` | UPG-3 | 78 | 1 / 76 / 1 | |
| `_zda` `deny_altar` | UPG-4 | 72 | | |
| `_ztmap` `threat_map` | UPG-2 / T08 | 69 (44.2%) | 10 / 49 / 19 | |
| `_zdl` `death_learn` | UPG-6 | 74 | 0 / 74 / 4 | |
| `_zcf` `chain_farm` | | 80 | | |
| `_zhv15` / `_zhv2` `heavy_value` 1.5 / 2 | objective persona | 76 / 75 | | |
| `_zmf0` no contest blob opening, `_zmt1` `mono_team` | contest | 74 / 74 | | |
| `_t01` `fix_my_dash` | T01 | 83 | 19 / 45 / 14 | 2,518 (vs 2,667) |
| `_t09b` / `_t09s` `fm_buffs` 3 / 1 | T09 | 75 / - | 13 / 49 / 16 | |
| `_t09f` `farm_ema` 0.05 | T09 | 79 | 12 / 55 / 11 | |
| `_t14a` `risky_persist` 2 | T14 | 80 | 4 / 72 / 2 | |
| `_t14b` `near_age_cap` 3 | T14 | 77 | 6 / 65 / 7 | |
| `_t3A` `fm_mode` 7 + `hor_threat` 3 + `mi_learn_burst` 1 + `sup_mode` 7 + `chan_keep` 2 | T03 group A | **59 (37.8%, p 0.005)** | 12 / 35 / 31 | 3,069 (vs 2,074) |
| `_t3B` `finish_race` 120 + `mi_endgame_bank` 100 | T03 group B | 78 | 1 / 76 / 1 | |
| `_t3ts` `tail_stat` 1 | T03 | 75 | 1 / 73 / 4 | |
| `_zeh20` `enemy_half_penalty` 20 | PAT-7 | 55 of 96 (cut when the queue moved to the held-out test) | | |

### 5d. The held-out test (the 152 maps of `test152`, both sides; no choice today used them)

Stage 1 can only remove losers: with 156 games one cell's standard deviation is about 4 points, and the best of 60 screens sits at
53-55% by chance alone. So every candidate went to the held-out maps against `_m1p3`:

| Build | What it adds to `_m1p3` | vs `_m1p3`, held-out (304 games) | Maps 2-0 / 1-1 / 0-2 | Sign p | Gem margin a map (95%) |
|---|---|---|---|---|---|
| `_v10a` | the principled stage-1 leaders: `watchdog` 1, `draft_guard` 1, `safety_range` 1, `fix_my_dash` 1, `isolated_fight_adv` 1.35, `fight_margin` 1.4 | 153 = 50.3% [44.7, 55.9] | 27 / 99 / 26 | 1.00 | +5.7 [-54.5, +65.6] |
| `_m2` | the draft weights refitted on 17,004 tuning-half games | 162 = 53.3% [47.7, 58.8] | 35 / 92 / 25 | 0.25 | |
| **`_v10b` = GOD v10** | both | **173 = 56.9% [51.3, 62.4]** | 50 / 73 / 29 | **0.024** | **+82.5 [+11.6, +149.3]: superior** |

The refit (`tools/draftmodel/fit.py` on every kept game of the 156 tuning maps: v8, the dynamic-draft round robins and the screens;
no held-out map is in it) had a log loss of 0.6233 against 0.6255 for the shipped weights, which is why the weights first stayed (13:17
checkpoint). Played on new maps the refit alone is +3.3 points (not significant) and with the brain fixes +6.9 (significant). What
moved: the gold bonus counts only where gold is a large share of the map (gold x gold share 0.19 -> 1.47, gold alone 0.74 -> 0.06), area
damage counts more on pack maps (0.24 -> 0.51), extra bodies cost more on small maps (-0.23 -> -0.40), a dash counts everywhere (0.06 ->
0.20) instead of by spawn distance (0.15 -> 0.00). On all 308 maps v10 drafts a different roster from `_m1p3` on 95 maps and wins 118
of those 190 games (62.1%, sign p 0.003); the swaps: Heart of Ruin for Ryth (40 of 56 games won), Vendetta for Ryth (23 of 32), Stellar
for Tavi (11 of 14), Varg for Marcella (20 of 40), Marcella or Varg for Ren (16 of 30), Vendetta for Heart of Ruin (3 of 12).

**Release checks of `_v10b`** (`tools/finalcheck.sh`, engine 3.0.4):

| Check | GOD v10 (`_v10b`) | `_m1p3` | v8 (`_v8k1`) |
|---|---|---|---|
| vs v8, held-out 152 maps | **243/304 = 79.9% [75.1, 84.1]**, maps 102 / 39 / 11, deaths 3,265-5,888 | 232/304 = 76.3% [71.2, 80.7], maps 92 / 48 / 12 | - |
| paired margin vs `_m1p3` (both against v8, same maps and sides) | +53.4 gems a map [-26.3, +132.8] (wide: the games against v8 are mostly large wins) | 0 | |
| head-to-head vs `_m1p3`, tuning 156 maps | 180/312 = 57.7% | - | |
| **head-to-head vs `_m1p3`, all 308 maps** | **353/616 = 57.3% [53.4, 61.2]**, maps 97 / 159 / 52, sign p 0.0003, gem margin +100.5 [+54.3, +149.3], deaths 8,736-10,517 | - | |
| 19 outside opponents, 21 official maps, 42 games each | **678/798** | 634/798 | |
| unopposed pace (rounds to 1,000 gems, 21 maps) | **978.8** | 1,030.8 | 1,099.8 |
| release mode, 6 heavy maps x 2 sides x 3 opponents | 0 faults; lost turns after round 3: 192 (opponents 166), all on the nx60x60 / nx100x100 mazes (154 / 38; opponents 135 / 31) | 0 faults; 223 | 0 faults; 167 |
| exceptions (`EXC_TRACE`, `tools/tracecount.py`) | (running: 126 games vs v8, `_pws`, `_q_s2v`) | 0 in 72 games | |
| SDK builds of the zip | 3.0.4, 3.0.2, 2.2.5 | 3.0.4, 2.2.5 | |

The 19 opponents, wins of 42 (`_v10b` / `_m1p3`): adapted-draft bots `_k_fit` 29 / 19, `_q_s2v` 26 / 22, `_k_ci` 31 / 23; personas farmer
`_pnF` 25 / 24, objective hunter `_pnO` 30 / 22, invader `_pnI` 38 / 36, deathball `_pnD` 41 / 41, bush ambusher `_pnA` 32 / 30, altar
denier `_pnL` 33 / 28, mid-match invader `_pnV` 30 / 28, switcher `_pnS` 34 / 34; ladder proxies `_pws` 39 / 40, `_pw` 41 / 41, `_pc` 41 / 41,
`_g4` 41 / 40, `_m15` 42 / 42, `_mite` 42 / 42, `_ifish` 42 / 41, `_px9` 41 / 40. Worse on one cell (`_pws` -1), level on six, better on twelve.

## 6. Decisions

- **GOD v10 = `_v10b`, shipped** (`submissions/god.zip` sha256 245c446c…, `submissions/history/god_v10_20261021.zip`, source hash
  e322f2410c3c, wasm byte-identical to the measured build): `pd_stat` 3, `pocket_fix` 3, the refitted `pd_w_*`, `watchdog` 1, `draft_guard` 1,
  `safety_range` 1, `fix_my_dash` 1, `isolated_fight_adv` 1.35, `fight_margin` 1.4. Every other switch of `x_v10.patch` stays at its off value
  (the code is in the build: the measured wasm contains it).
- **From the upload**: `safety_range` (FIX-1) is in. Not taken: the opponent model and its presets (every plan, single plans, a stricter
  detector, plans forced for whole games: all lose or tie, sections 2-3 and 5c), `enemy_comp_init`, `ring_reach`, `tavi_str` (they change
  almost no game with our draft), `watchdog9` (main's `watchdog` does the same), the sparring personas (kept as sparring tools only).
- **From the plan and the task file**: T01 (`fix_my_dash`), T13 (`draft_guard`, the watchdog), PAT-7's two fight thresholds and PAT-2's refit
  are in; everything else in sections 4 and 4b was built or re-screened and measured level or worse (SUGGESTIONS.md lists them).
- **Not unbeatable**: v10 still loses about a quarter of its games to the economic personas (farmer 25 of 42, objective hunter 30) and the
  adapted drafts (`_q_s2v` 26, `_k_fit` 29), and on the hooks map (nx31x31_c4) side A loses whichever bot plays it (mirror turn order).
  The close match-ups are economic, not reactive: no counter-plan measured here helped against them, and the next gains are most likely in
  the draft model (more opponent rosters in the fit) and in farming speed on the two maze maps, where most lost turns are.
- **Ladder test**: the branch pair `god-v10-on` (this build) / `god-v10-off` (the dynamic-draft build `_m1p3`, the zip of
  `god-dynamic-draft-on`), each with its own `submissions/god.zip`.
