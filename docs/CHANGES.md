# v11 requests (Oct 21 evening): Prism draft, Prism anchor, Heart of Ruin aggressor, three phases, losing-adapt, wards. **Not shipped: GOD v10 stays**

Request: draft Prism instead of Vesper Vale and let the bots play it out; Prism as the safe anchor (home-side groups, bags ~20 instead of
54, danger exit 0.1 instead of 0.2, never the enemy half, the killer holds the reward tile until the anchor steps on); Heart of Ruin as
the aggressor; three phases (0-666, 666-1332, 1332-2000); change strategy when losing; better ward placement from map analysis.
Code `experiments/wip/x_v11.patch` on GOD v10 (every switch off = v10's play), notes `experiments/wip/x_v11_NOTES.md`. Engine 3.0.4,
156 games per screen (train78a, both sides) head-to-head vs GOD v10.

| Change | Switch | Result vs GOD v10 |
|---|---|---|
| Prism for Vesper Vale | `pd_sub_from` 1, `pd_sub_to` 5 | 58/156 = 37.2% (sign p 0.004) |
| + Prism as the safe anchor with the hand-off | `anchors`, `anchor_prism`, `anchor_side` 0.45, `anchor_trib` 0.38, `anchor_ml2` 0.1, `handoff` | 37.2% (Vesper as the anchor: 41.0%) |
| Heart of Ruin aggressor | `hor_aggro` 1 (always) / 2 (fresh, dash up, ally near) | 51.3% / 48.1% (level); 29.5% on the Prism team |
| Three phases | `phases` 1 | 47.4% |
| Losing: press or regroup | `lose_adapt` 1 | 51.3% |
| Map-scored wards on our camps / altars | `ward_smart` 1 | 38.5% (deaths +620: loses the forward early warning) |
| **Scouting wards** (best tile ahead on the walk field toward their spawn; bushes, the corridor, contested groups) | `ward_smart` 2 | **58.3%** train78a, 53.9% held-out test152, **54.5% on all 308 maps** (sign p 0.0097, margin +43 [+3, +83]); vs v8 held-out 80.9% (v10 79.9%); **19 outside opponents 655/798 vs v10 678** (ambush persona 20 vs 32 of 42) |
| + a bush next to our target group first | `ward_smart` 3 | 51.9%, ambush persona 21/42 |
| Prism team with everything above | `_v11Pw2` / `_v11` | 24.4% / 17.9% |

Verdict: the Prism draft and every behaviour change except the scouting wards measure level or worse; the scouting wards beat v10
head-to-head but lose to the outside opponents (the non-transitive pattern the ship rule rejects), so `submissions/god.zip` stays GOD v10.
Two candidate zips for the ladder (`submissions/candidates/README.md`): `god_v11_scoutwards_20261021.zip` (`ward_smart` 2) and
`god_v11_prism_anchor_20261021.zip` (the requested Prism team; weaker). The first ward search cost ~65k fuel a call (every group
scored for 25 tiles) and lost a turn every 10 rounds per body: fixed before any measurement counted.

# GOD v10 (Oct 21): the dynamic draft refitted, plus what held up from the v9 upload and the two plans

Request: test the user's `god_v9_adaptive.zip`, take its better parts, carry out `GOD_Improvement_Plan.md` and `GOD_v9_Improvement_Tasks.md`
with measurement, deliver the best bot as GOD v10. Every number and the plan items one by one: `docs/strategy_v2/18_V9_AND_PLAN.md`.
Engine 3.0.4, every map both sides, ledger `experiments/results/ledger_v3_0_4/`; reference `_m1p3` (the dynamic draft, branch `god-dynamic-draft-on`).
Code: `experiments/wip/x_v10.patch` on GOD v8 (the upload ported behind switches, renamed `opp9` / `Opp9` / `plan9` / `watchdog9` so it lives
next to main's own opponent model, plus the task file's switches); every switch off = v8's play.

| Change | Switch (v10 value) | What it does | Result |
|---|---|---|---|
| Draft weights refitted | `pd_w_*` | logistic fit on 17,004 games of the 156 tuning maps (none of the held-out maps): the gold bonus counts on gold-heavy maps only, area damage more on pack maps, extra bodies cost more on small maps, a dash counts everywhere | alone 53.3% vs `_m1p3` on the held-out maps; on 95 of 308 maps v10 drafts differently and wins 62% of those games |
| Camps at their engine range | `safety_range` 1 (from the upload) | `safety()` counts a camp while we stand inside its real attack range (elk / golem 4, monolith 5) instead of 3 | level, fewer deaths |
| Our dash in the burst | `fix_my_dash` 1 (task T01) | combat()'s burst also counts our own ready damaging dash (Heart of Ruin's landing) | stage 1 53.2%, deaths 2,518 vs 2,667 |
| Stricter lone fights | `isolated_fight_adv` 1.35, `fight_margin` 1.4 | a body alone starts a fight only at a higher advantage | stage-1 leaders |
| Crash insurance | `watchdog` 1, `draft_guard` 1 (task T13) | a minimal safe turn after 3 throwing turns; a draft pick that throws falls back to a legal pick | inert in normal play (0 exceptions); a body forced to throw keeps 12-13 of 24 wins (10 without) |
| **GOD v10 = all of the above** | | | **vs `_m1p3`: held-out 56.9% (p 0.024, +82.5 gems a map, superior), all 308 maps 57.3% (p 0.0003); vs v8 held-out 79.9%; 19 outside opponents 678/798 (634); pace 978.8 (1030.8); 0 faults** |
| The upload's opponent model and presets | `opp_plan` (0) | evidence windows, CUSUM, seven plans with threshold presets | 44.9% vs v8, 19.2% vs `_m1p3`; false alarms in 96% of mirror games; plans forced for whole games lose to plain farming even against their own target: off |
| The upload's other switches | `enemy_comp_init`, `ring_reach`, `tavi_str`, `watchdog9` (0) | enemy kits at init, area reach in the ring, Tavi strength, its own watchdog | level (our draft rarely has Tavi / Prism; main's watchdog covers it): off |
| The task file's other switches | `fm_buffs`, `farm_ema`, `risky_persist`, `near_age_cap`, `bandit_discount`, `ally_defend`, `deny_ramp`, `heavy_value`, `opp_force` (0 / 1.0 / -1) | engine shields and stuns in fights, learned camp damage, herding guard, threat age cap, discounted bandit, defend allies, denial ramp, heavy groups, forced plans | level or worse on stage 1: off (SUGGESTIONS.md) |

Tools: `tools/abmargin.py` (gem margins, paired design, superior / non-inferior), `tools/tracecount.py` (trace-line counts, e.g. exceptions),
`tools/opptrace.py` (plan timelines), `tools/finalcheck.sh` (the release checks). Pools `experiments/pools/train78a.csv` / `train78b.csv`.

# Patch 3.0.4 GOD: the dynamic draft (Oct 21)

Request: "make the new bot according to these changes [the 3.0.4 balance patch] and compare them on these changes only", then "ensure
nothing is hardcoded and everything is decided dynamically according to the maps and the enemies moves and strategies". Full analysis
and every number: `docs/strategy_v2/17_PATCH_3_0_4.md`. All games on engine 3.0.4, both sides, ledger `experiments/results/ledger_v3_0_4/`.

| Change | Switch (off = v8) | What it does | Result vs v8 (tuning half, 312 games) |
|---|---|---|---|
| Draft-value model | `pd_stat` 3, weights `pd_w_*` | a pick's value = fitted weights x features read from the engine's designs (health, basic damage, splash, spells, area damage, stuns, dash, range, gold bonus, retaliation, bodies) and from this map's camps (pack / elk / gold shares, size, spread, monoliths); no per-champion number | **82.1% [77.4, 85.9]**, maps 110 / 36 / 10 |
| Hole-pocket escape | `pocket_fix` 3 | a body where no walk leads home dashes out (else recalls when going home); no walking fallback search from such tiles (a Vesper had burned every turn's fuel for 280 rounds) | 82.4% with the draft (lost turns back to v8's level) |
| **Shipped as the branch pair `god-dynamic-draft-on` / `-off`** | `pd_stat` 3 + `pocket_fix` 3 | | **all 308 maps 79.4% [76.0, 82.4]; held-out half 76.3% [71.2, 80.7]; 8 proxies 327/336 (v8 283)** |
| Counters to the enemy's picks | `pd_cw_*` (0) | our range / stuns vs their melee damage, health vs burst, dashes vs range | fitted on 12,114 games (82 enemy rosters): no held-out gain, kept 0 |
| v8's map types in kit terms | `pd_obj_*`, `pd_open_*` | objective ring by range-4 spell damage, open small maps by retaliation / splash | part of the model draft |
| Measurement switch | `pd_sub_from` / `pd_sub_to` (-1) | v8's draft with one champion swapped, every map rule intact | the 11 screens of doc 17 §2 |
| Stat-anchored priors | `pd_stat` 1 / 2, `pd_pri_*`, `pd_stat_k` | measured priors shifted by ln(stat power ratio) on a later patch | 72-79% (superseded by `pd_stat` 3) |
| Ally damage from its kit | `ally_kit` (0) | an ally's camp damage from its engine modifiers instead of typed 3.4 / 2.0 / 1.5 x focus | 68.9% vs 72.4% without (on `_r_v1`): off |
| Build stat from the kit | `build_stat` (0) | the build's focus / strength shards in the stat the kit pays most for | Tavi -3.5, Ren (margin 1.3) +2.0: not adopted yet |

# GOD upgrade (F1-F6): what changed, why, and what was measured

Base: GOD v8 (`bots/god/src` at commit db74b11; line numbers below are from that commit unless marked "now"). Request:
`opus_prompt_god_upgrade.md` (the opponent-adaptive upgrade). The field manual it cites (`GOD_Bot_Field_Manual.pdf`, chapters 15-17,
§16.2 presets, §16.4 draft-memory layout) was never uploaded: preset directions and the draft-memory layout come from the code and
from earlier measurements, cited where used.

Every feature is behind its own switch in `params.h`; with all of them at their off value the bot plays v8 exactly: the same replay
events and the same 8 shared-memory bytes after every turn (docs/TESTING.md §1). Both SDKs (3.0.x with Heart of Ruin and Golem, 2.2.5
without) compile every configuration.

**How the features are decided now.** On the user's instruction (Oct 20, 21:37 UTC), strength is no longer judged locally: a feature
judged viable goes to the ladder as a pair of branches that differ only in that feature; local testing checks only that both bots work
(build on both SDKs, games finish, no faults, no extra lost turns, the new per-turn code's fuel). The local numbers below were measured
before that rule and are the reason the other features were not proposed.

| Feature | Switch (default) | Local result (42 games each: h2h vs v8 / `_pws` / `_pw` / `_g4`; v8 21 / 33 / 39 / 35) | Status |
|---|---|---|---|
| F1 opponent model, fitted classifier | `opp_model` 0, `om_learned` 0 (`om_act` 1) | not measured (the oracle cells were stopped) | **branch pair** `god-opponent-model-on` / `-off` |
| F1 sightings in the alert slot | `om_sight` 0 | not measured | off |
| F2 draft-memory plan + F3 ward coordination | `dm_plan` 0, `ward_plan` 0, `ward_enemy` 0 | 20 / 31 / 42 / 22 | off (worse) |
| F4 anchors + reward hand-off | `anchors` 0, `handoff` 0 | 17 / 29 / 37 / 29 | off (worse) |
| F4 Prism banker | `prism_bank` 0 | not measured | off |
| F5 chain farming | `chain_farm` 0 | 20 / 28 / 36 / 26 | off (worse) |
| F6 carrier interception | `gank` 0 | 22 / 27 / 39 / 31 | off (worse vs the proxies) |
| F6 DENY-ALTAR role | `deny_altar` 0 | h2h 12 of 32 (stopped) | off (worse) |
| F6 watchdog | `watchdog` 0 | inert: no local game ever threw 3 turns in a row | off (safe to turn on) |

Pool: the 21 official patch-3.0 maps (`maps/comp30` + `maps/nyx_new` + `maps/loss_oct20`), both sides. One cell of 42 games has a
standard deviation of about 2.5-3 wins near 80%; mirror-family games are chaotic (one change flips about half the games either way), so
differences under ~5 wins in one cell are noise. Rows: `experiments/results/ledger_v3_0_2/<variant>_vs_<opponent>.jsonl`.

## F1. Opponent model and strategy state

**Problem.** v8 has no notion of what the enemy is doing. Its only team-level adaptation is the stance learner (`learn.cpp`, a bandit
over SPREAD / GROUPED / PUSH scored every 20 rounds), read at `brain.cpp:3416` (`stance = comms().stance`) in `update_mode()`
(`brain.cpp:3407`). Ladder data says the costliest situation is the enemy fighting on our half: in the 25 lost games of Oct 20, fights on
our half when they opened cost 121 of our bodies to their 7 (doc 15). Nothing in v8 recognises that pattern and changes the plan.

**Design** (`opponent.h/.cpp`, now; hooks in `brain.cpp` `turn()`, `om_tick()`, `om_observe()`, `update_mode()`):
- The leader (body 0) closes a window every `om_window` 20 rounds, also while dead (the dead path of `turn()` calls `om_tick()`).
- Signals per window (`OmWindow`): enemy bank events, gems and the biggest lump (deltas of `global_submitted_gems(enemy)`); ally and enemy
  deaths, multi-deaths (two of ours within 3 rounds) and deaths on our half; the shared invasion counter (bit 7 of bytes 3-5: each living
  body adds 1 once per window when it sees an enemy on our half); the largest visible enemy pack; the most enemies in view; enemies within
  3 of our altars; enemy locks on our altars; our cancelled tributes; enemy wards on our half, near our altars and on bushes (by owner,
  one per champion; by tile on SDK 2.2.5, which has no `ward::owner()`); hits taken with no visible attacker in reach and no camp within 5,
  and those next to a bush; heavy groups seen going from alive to taken while none of ours claimed them.
- Two classifiers, both with forgetting, a minimum duration (`om_min_windows` 3) and a two-sided CUSUM change detector on the contact
  level (sightings + deaths per body; `om_cus_k` 0.15, `om_cus_h` 0.6) that bypasses the minimum duration:
  - heuristic evidence for the six archetypes (FARMER, INVADER, DEATHBALL, OBJECTIVE, ALTAR, AMBUSH; `om_lambda`, `om_thresh`,
    `om_margin`, `om_drop`): used only when `om_learned` is 0;
  - **the fitted classifier** (`om_learned` 1; `om_model.h`, generated by `tools/omfit.py`): logistic regression of none vs raider on the 17
    window features smoothed with forgetting `om_feat_lambda` 0.8; hysteresis `om_p_on` 0.6 / `om_p_off` 0.4. Calibration showed that from
    the leader's signals only raiding separates from GOD's own play (see results); the other styles are indistinguishable, so the model
    has two classes.
- The leader broadcasts a 3-bit plan id in bit 7 of bytes 0-2 (`docs/COMMS.md`). Ids 0-2 are the learner's stances bit for bit, so "no
  archetype" writes exactly the v8 bytes; 3-7 are counter plans. While a counter plan is active the stance learner does not score its windows
  (`Learner::frozen`), so the counter plan's results do not train the bandit.
- Counter presets (`preset_of()` in `opponent.cpp`), applied in `update_mode()` after the stance block, scaled by `om_k_<plan>` (1). The
  deficit, fight-record and race modifiers still apply on top. With `om_learned` 1 only INVADER can be chosen:

| Plan | Stance | fight_margin | enemy_half_penalty | deny_bonus | tribute_min | isolated_fight_adv | escort_bag | group radius | other |
|---|---|---|---|---|---|---|---|---|---|
| INVADER | GROUPED | -0.1 | x1.5 | -0.2 | x0.8 | +0.1 | x0.67 | x0.75 | |
| DEATHBALL | GROUPED | +0.3 | | | x0.8 | +0.3 | | x0.75 | |
| OBJECTIVE | SPREAD | | x0.6 | +0.3 | | | | | |
| ALTAR | SPREAD | | | | x0.6 | | x0.67 | | guard role |
| AMBUSH | GROUPED | +0.15 | x1.2 | | | +0.2 | | x0.75 | bush-first wards |

  (GROUPED itself already doubles enemy_half_penalty, halves deny_bonus and adds 0.3 to isolated_fight_adv: `update_mode()`.)
- `om_sight` (separate switch): every body posts an enemy it sees on our half as DANGER in the alert slot when no RALLY / OPPORTUNITY /
  ESCORT younger than 6 rounds is there; readers use it as a scoring cost only (groups within 5 of a sighting younger than 8 rounds cost
  25 rounds), not as a routing wall (the old radius-8 alert zone in routing measured worse).
- `om_force` N (testing only): the leader broadcasts plan N from `om_start` on, the oracle that bounds what a perfect classifier could gain.
- Sparring proxies (`pxs_style` and friends, testing only, never shipped): 1 farmer, 2 invader (raid incentive x3), 3 deathball (blob +
  raid), 4 objective, 5 ambush (bush farming), 6 altar denier; switchers change style at given rounds (`pxs_switch`).

**Fuel** (`tools/fueltrace.py`, FUEL_TRACE builds, 36 games vs `_v8k1`, `_pxI`, `_pws` on six maps incl. 100x100). The first version spent
5.5-9.6k fuel per leader turn, mostly re-deriving each altar's side from distance reads. Fixed (now): altar sides cached once, one memoised
"enemy on our half" test per enemy per turn, the enemy loops skipped when no enemy is in view, the bitboard tests only on turns we lost
health. Now: **516 fuel per body-turn on average** (was 1,181-1,386), p99 5.4k (was 10.5-11.2k), max 14.4k (was 22k; a leader turn that
closes a window and scans wards). By body: the leader 1.9k (1.2k on odd rounds, 2.5k on the even rounds that scan enemy wards, 3.7k when it
closes a window), every other body 0.2k. On the 100x100 map: mean 440, p99 2.7k, max 9.9k. Lost turns after round 3 over the same 36 games:
145 with the model on (48 / 53 / 44 vs `_v8k1` / `_pxI` / `_pws`), 175 with it off (50 / 63 / 62; the first, unfixed version: 240); fuel
left at the end of a turn 68.3-70.0k on vs 68.2-70.6k off; 0 faults.

**Results.**
- Identity with the switch off: 12/12 games identical to v8 (events and shared memory), `tools/actiondiff.py`.
- Calibration (`experiments/results/om/`: 140 training games on `maps/comp30` vs the six proxy styles and v8, 154 held-out games on
  `maps/nyx_new` + `maps/loss_oct20`): leader-level window signals per style (rounds >= 100) separate only the raiding styles: invasion
  1.63 (invader) / 1.44 (deathball) vs 1.36 (v8 itself), pack 1.37 / 1.60 vs 1.10, enemy banks per window 0.13 / 0.03 vs 0.36. Farmer is
  indistinguishable from v8; objective, ambush and altar are indistinguishable from none.
- Fitted classifier: window accuracy 0.799 on the training maps, **0.697 on the held-out maps** (none + farmer vs invader + deathball).
  Decision replay with the shipped weights, hysteresis and minimum duration (`tools/omreport.py`, held-out): raiders spend 65% of their
  windows in the INVADER plan (invader 61%, deathball 68%), the rest 31% (farmer 28%, v8 33%, objective 31%, ambush 21%, altar 39%).
- Strength: not measured. The oracle cells (`om_force` 3 / 4 vs the matching proxy) and the switching-proxy detection-delay traces were
  queued and stopped by the rule above. **This is the feature the branch pair tests on the ladder.**

**Risks.**
- The classifier was fitted on our own code family. On the ladder the strong teams may look like "raiders" because several features
  are outcomes (our deaths, their banks): then the INVADER plan fires against strong teams in general, not only against invaders.
- 31% of non-raider windows still sit in the INVADER plan (false positives) and 35% of raider windows do not.
- Preset magnitudes are not fitted (`om_k_*` = 1). GROUPED as a fixed prior measured level-to-worse in earlier sessions (`_g_q05` level,
  blob openings 23/42, `gather_any` 22/42), but never as a reaction to detected invaders.
- The invasion counter loses a count when a body acts before the leader in a window's first round (the reset wipes it); with 6 bodies the
  3-bit counter still cannot saturate.

## F2. Draft-memory plan

**Problem.** On the default parameter-draft path (`mapdraft` 6) `param_pick()` returns at `draft.cpp:519-520`, before the only draft
memory write (`draft.cpp:603-604`, a 4-byte record): the game got no draft memory, and the draft turn's 10x fuel computed nothing for it.

**Design** (`dmplan.h/.cpp`, `draft.cpp` `dm_write()`, `Brain::init()`): a versioned layout (magic 0xC8, version 1, map size, group count,
checksum; byte table in `docs/COMMS.md`) written on every draft turn after our pick: our picks, the enemy picks seen so far (simultaneous
picks: their last one may be missing), map flags (objective, lone monoliths, no reachable altar, gold-heavy, islands), heavy and monolith
groups on our half, a zone owner per group, the anchor ranking and up to 32 ward spots (bushes within 3 of our groups and altars, approach
tiles of altars and heavy / midline groups, spaced >= 4, each with a responsible pick slot). The first draft turn computes the map part
once. `Brain::init()` accepts the plan only if every check passes; otherwise every user falls back to its in-game logic.

**Switch** `dm_plan` 0. Users: `ward_plan` (F3) and the opponent-model prior (`om_prior`, off). **Fuel**: draft turns only; the game pays
one decode in `init()`. **Results**: only through F3 (below). **Risks**: the zone table is informational (zone farming lost in session 13);
pick slots map to bodies by champion type, Cassi and Issac share their pick's slot.

## F3. Ward coordination

**Problem.** `place_ward()` (`brain.cpp:1781`) picks a spot per body with no coordination; bush warding is on only for lone-monolith maps
(`ward_bush_maps` 1, `brain.cpp:1783-1785`) because unconditional bush warding measured worse.

**Design** (`plan_ward()`, `enemy_wards_update()`, `near_enemy_ward()`, now): a ready ward goes to a draft-plan spot within reach that
watches our task group, capture tile or banking altar; no spot within 3 of an allied ward; two bodies on the same claim split roles (the
lower index takes the enemy-facing approach, the higher the bush); bush-first only under the AMBUSH plan, while standing still (capture,
tribute, farming), or on lone-monolith / objective maps. `ward_enemy`: enemy wards remembered by owner (one per champion); carriers with
>= `ward_avoid_bag` 30 gems pay `ward_avoid_cost` 8 per watched tile in group and altar choice.

**Switches** `ward_plan` 0, `ward_enemy` 0. **Results** (with `dm_plan`): 20 / 31 / 42 / 22 vs v8's 21 / 33 / 39 / 35. Against GOD v2 (`_g4`)
23 of 42 games changed result, 17 to losses (contest, eight, interlock, ambush and nx50x50 lost on both sides). Not viable as built.
`ward_enemy` alone: not measured. **Risks**: the cause of the `_g4` drop was not traced; one hypothesis (wards on approach tiles getting in
our own way) is untested.

## F4. Anchors, reward hand-off, Prism banker

**Problem.** Every body banks its own bags; there is no designated banker, and bags die with their carriers.

**Design** (`update_anchors()`, `capture_group()`, `group_score()`, `tribute()`, now): a deterministic ranking every body computes alike
(Vesper, Marcella, Prism, then the lowest base health); `anchors` 1 / 2 / 3 (3 = by team size: 1 at size 3, 2 at sizes 4-5); the next
body takes over on a death. Anchors: tribute threshold x0.6, bag caution 20, enemy-half penalty x3, ml2 leave threshold 0.1, a cost of 0.5
per step from their home altar, one altar each with two anchors. `handoff`: a non-anchor capturing with an anchor within 4 does not
capture-recall, holds the tile until the anchor stands on the group, then steps off (no split, no timer reset). `prism_bank`: Prism holds
its bag unless it wins, the endgame or health below 0.35. Engine check: Prism's live `focus` includes +1 per carried gem (4 gems -> 84,
22 gems -> 222).

**Switches** `anchors` 0, `handoff` 0, `prism_bank` 0. **Results**: anchors 3 + handoff 17 / 29 / 37 / 29: worse. `prism_bank`: not measured.

## F5. Chain farming

**Problem.** After a capture, `capture_group()` recalls when health is below `cap_recall_hp` 0.61, when gold after the capture reaches
`cap_recall_gold` 60 (`brain.cpp:5300-5301`), or when the bag is bankable: bodies recall after most captures.

**Design** (`chain_keep()`, now): recall only when hurt (`chain_hp` 0.5), or when the home trip (bank + shop: `chain_bank_w` x (bag +
gold value) / (recall + 1 + distance home)) beats the best of the 4 nearest groups within `chain_r` 12; the bag trigger is x`chain_bag` 1.5,
shopping waits for `chain_gold` 150. Anchors keep the v8 triggers.

**Switch** `chain_farm` 0. **Results**: 20 / 28 / 36 / 26: worse, mostly against GOD v2 (-9).

## F6. Smaller items

- **Carrier interception** (`gank`; `gank_bag` 25 at `params.h:591` was never read in v8): a healthy body (>= 0.6) intercepts a visible
  carrier with >= `gank_bag` gems within `gank_r` 10, predicting its path down the field to its spawn (up to 8 steps), with a power check.
  Results: 22 / 27 / 39 / 31: level head-to-head, worse against the proxies.
- **DENY-ALTAR role** (`deny_altar`): when the enemy has >= 850 banked or the race says they finish first, the lowest-index living
  non-anchor holds a lock within 2 of the enemy's most-used altar. Results: h2h 12 of 32 games before the run was stopped: worse.
- **Watchdog** (`watchdog`): v8's `main.cpp` swallows an exception and ends the turn (`main.cpp:13-16`), so a turn that throws every round
  idles forever. With the switch, after 3 caught exceptions in a row the body hits an adjacent enemy, else steps toward spawn (`safe_fallback()`).
  No local game had a fault, so it never acted; on, it plays v8's games.
- **A/B of existing switches** (`ml2_adapt` 0.02, `mi_learn_burst` 1, `finish_race` 120, `ml2_gb` 1, `big_reward_dive`): queued on v8, not run.
  Earlier sessions measured most of them on older bases: `finish_race` 70 / 150 rejected (session 13), `mi_learn_burst` alone beat its base
  but lost to third parties (session 11), `ml2_adapt` (`_mlka40`) 146 vs 149 of 170, `big_reward_dive` parked (slugfests at the objective).

## Tools added

`tools/actiondiff.py` (event-by-event and shared-memory diff of two builds), `tools/omtrace.py` (labelled opponent-model traces),
`tools/omfit.py` (classifier fit and export), `tools/omreport.py` (decision replay: confusion, time in plan, detection delay),
`tools/fueltrace.py` (functional and fuel check: faults, lost turns, fuel left, opponent-model fuel per body-turn), `SM_TRACE`,
`OPP_TRACE`, `FUEL_TRACE` defines (trace output inside `debug_block`, compiled only when defined).

## Self-review (for the reviewers)

**Least sure of.**
1. Whether the INVADER counter plan helps at all. Its directions follow the ladder evidence (we lose fights on our own half), its
   magnitudes (`om_k_invader` 1 and the preset numbers) were never fitted, and the oracle test that would bound its value (`om_force` 3) was
   stopped before it ran. The branch pair is that test, on real opponents.
2. Transfer of the classifier. It was fitted on our own code family; some features are outcomes (our deaths, their banks), so against a
   strong team it may read "raider" whatever that team does. Held-out accuracy (0.70) is on new maps, not on new opponents.
3. Change detection: the CUSUM constants (`om_cus_k` 0.15, `om_cus_h` 0.6) and the minimum duration (3 windows) were set from the contact
   levels in the calibration traces, not fitted; the detection delay on switching proxies was never measured (the traces were stopped).
4. The ward-plan loss against GOD v2 (17 of 23 changed games lost) was never traced to a cause.

**Edge cases.**
- Cassi & Issac are two bodies (six bodies at team size 5): every body index is 0-5, so the claims (bytes 0-5) and the leader (body 0)
  work unchanged; the invasion counter's features divide by the body count; the anchor ranking counts the pair as Cassi; the draft plan's
  pick slots give both bodies their pick's slot. A 3-bit counter with six bodies tops out at 6 per window, below its saturation at 7.
- Maps with more than 62 groups: claims take bits 0-6 and the team bag sum is off; bit 7 of every byte is still free, and the plan id /
  invasion counter writes keep bits 0-6 (`(old & 0x7F) | bit`).
- Dead leader: body 0 runs `om_tick()` while dead (closes windows, classifies, broadcasts), but its own view (`om_observe()`: pack, altar
  presence, unseen hits, wards, heavy groups) is missing while it is dead; the invasion counter and the global gem / death counts still arrive.
- Missing or foreign draft memory (`dm_plan`): `dm_decode()` fails on magic, version, structure or checksum, `Brain::init()` also checks map
  size and group count; `draft_plan().ok` stays false and ward placement falls back to v8's `place_ward()`. The opponent model never needs
  the draft memory (its prior, `om_prior`, is off and reads the visible enemy types).
- SDK without Heart of Ruin / Golem (2.2.5): `SDK_HAS_HOR`, `CT_HOR`, `CAMP_GOLEM` and `ward_owner()` (`common.h`, requires-expressions)
  compile on both; with no ward owner the enemy-ward count dedupes by tile. Every configuration in this document builds on both SDKs.
- `alert_refresh` (off in v8) shares byte 2's bit 7 with the plan id; the code disables the toggle when `opp_model` is on.

**What I would test next.** The ladder pair first. Locally, if allowed again: the oracle cells (`om_force` 3 vs `_pxI` and vs `_v8k1`);
detection delay on the switching proxies (`_pxS3`, `_pxS5`, `_pxS8`, `_pxSM`); a stricter `om_p_on` 0.8 (decision replay, off 0.4: raiders
44% of windows in the plan, others 18%); `om_sight` alone; a trace of the ward plan against GOD v2.
