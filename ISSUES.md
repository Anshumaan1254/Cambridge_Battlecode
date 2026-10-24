# ISSUES: hardcoded choices that may hurt when the map pool changes

The user's rule (session 12): derive parameters from the map and the game wherever possible; anything hardcoded is listed here.
Scope: the shipped bot (`bots/legend/src`, `submissions/legend.zip`). Sparring-proxy code (Mite / ifish / sneaky / IC tables) is
listed at the end: it is hardcoded on purpose and switched off in the shipped bot.

Severity: **high** = can pick the wrong plan on a new map; **medium** = a threshold fit on the 17 official maps; **low** = tuning
or engineering limits.

## Map identity or map size in live code

| # | Where | What is hardcoded | Why it matters | Severity | Fix |
|---|---|---|---|---|---|
| 1 | `brain.cpp` ring plan, `o2_ring` 3 (`(W.W == 60 && W.H == 50)` in the condition) | the caster ring fires on **any 60x50 objective map**, whatever our draft. `o2_ring` 3 was meant to replace the size test with "our team has Prism or Tavi and 5 champions", but the size term is still OR-ed in | a new 60x50 objective map with 4 champions or no casters would ring with melee bodies (the ring lost 14/30 vs 20/30 on the 4-champion objective maps, session 11) | ~~high~~ **fixed in `legend_m15`** | `o2_ring_size` 0 drops the size term (official games unchanged; session 13 screen 130/170 vs 129, same games) |
| 2 | `brain.cpp` `init`: `comms().bag_on = team_bank && groups <= 62` | the team gem sum in shared memory only on maps with at most 62 camp groups (the claim bytes need the other bits) | on a map with 63+ groups the banking-to-win rule loses the team sum (every body only counts its own bag) | low | none needed now (largest official map: 48 groups); repack comms if a bigger map appears |
| 3 | `world.cpp` respawn bookkeeping: `ready_round = seen_round + 6 + respawn` (and `+ 6.f` capture rounds in `group_score`) | the capture time is a literal: 6 = `capture_time` (5) + 1 (the reward lands the round after the 5 capture phases) | wrong if the engine changes `capture_time` | low | use `bc::constants::capture_time + 1` (session 12 first tried `capture_time` alone: respawn predictions one round early, 3 games fewer of 170: the +1 matters) |

## Thresholds fit on the official pool (derived from map features, but the cut-offs were chosen on these 17 maps)

| # | Param (`params.h`) | Value | Fit on | Risk on a new pool | Severity |
|---|---|---|---|---|---|
| 4 | `pd_open_area`, `pd_open_dist` (draft: open 3-champion map -> C&I, Stellar, Varg) | 5000 tiles, 30 steps | only expanse (80x80) qualifies; the first cut (4000 / 30) lost to ifish and sneaky | a large 3-champion map just below the cut drafts Ren, Stellar, C&I | medium |
| 5 | `pd_pack`, `pd_elk` (draft: Ryth or Varg as 4th / 5th pick) | 0.5, 0.3 | interlock 0.33 elk, rushbait-v2 0.44; the generated size-4 maps with elk share <= 0.22 lost 16/72 with Ryth | maps near the cut flip the pick | medium |
| 6 | draft priors and map-fit bonuses (`draft.cpp` `prior()`, `pd_score()`) | Ren 1.0, Stellar 0.95, C&I 0.9, Varg 0.62, Ryth 0.6, Prism 0.36, Tavi 0.33 ...; objective +0.75 Prism / Tavi | the 8-draft x 45-map tournament and sessions 6-11 | new champions or a meta shift; no in-match update | medium |
| 7 | objective-map detector: `obj_min_hp` 4500, `obj_share` 0.7, `obj_max_groups` 8, `obj_min_attackers` 2 | see comments | ambush (6 groups) in, eight (0.67) out, contest (2) and stampede (1) in | a map with a 4,000-HP heavy group or 9+ heavy groups gets no team plan | medium |
| 8 | lone-monolith (contest) detector: `mono_share` 0.9, `mono_center` 0.45 | contest 0.50; the generated gold_mono maps 0.38-0.42 (where the plan lost) | a contest-like map with monoliths at 0.40-0.45 of the walk gets no contest plan | medium |
| 9 | `pd_obj_multi` (objective draft only when the lone gem group is multi-camp) | 1 | excludes the gold_elk test maps | a single-camp objective (one huge camp) drafts normally | low |
| 10 | economy thresholds: `tribute_min` 54, `early_tribute_min` 22, `cap_recall_hp` 0.61, `cap_recall_gold` 60, `max_wait` 18, `max_join` 3, `join_reach` 1.2 | the A100 ES run and agent screens on the official + generated maps | values, not structure: they scale with nothing on the map (e.g. bank size does not scale with altar distance beyond `bank_trip_w`) | low | 
| 11 | fight thresholds: `fight_margin`, `outmatch_flee_adv` 0.8, `isolated_fight_adv` 1.23, `cornered_margin` 0.74, `target_threat_adv` 1.49, `threat_memory` 7 | ES and agent screens vs our own code family | tuned against our proxies, not the real top teams | low |
| 12 | fuel limits: `danger_detour_fuel` 40000, `defer_islands`, scoring fuel floors | measured on maps up to 100x100 | a bigger map (e.g. 120x120) can lose turns to fuel rollovers | medium |

## Fixed per-champion policies (not map dependent)

| # | What | Note |
|---|---|---|
| 13 | build orders (`build_for`, `build_style` 2): Ren Jungle health > Treasure > Monster > Bruiser...; Stellar Monster > Treasure > Bruiser; C&I Monster > Durability; Varg Monster > Treasure > Jungle; Ryth Jungle > Monster > Durability | chosen by the item-value model and A/B tests; no map input. The top team (IC) buys Power first and Home second (doc 12): tested in session 12, see SUGGESTIONS.md |
| 14 | champion kits (`kit_of`): attack ranges, spell reaches, dash | read from the SDK where possible; spell reach assumptions (area spells reach 5) are literals |
| 15 | **ladder-trained danger model** (`ml2_model.h`: logistic weights for P(die within 8 rounds), 58 features) and its cut-offs `ml2_leave` / `ml2_flee` 0.4 | trained on 160 decoded ladder games of Oct 19 (our bodies and the top teams'); the 0.4 cut-offs were chosen against the local proxies (0.3 was worse). Not map dependent, but **fixed to the opponents of Oct 19**: if the ladder teams change their play, the model is stale. `ml2_adapt` (in-match offset from our own deaths, level locally) is in the code, off. Retrain with `tools/ml/ml2_dataset.py` + `ml2_train.py` on new replays |
| 16 | `aoe_reach5` 2: an enemy whose cooldowns we have not seen counts its area spell as ready, reach 5 | idle / passive enemies that stand at their spawn block the groups within 5 of it: unopposed rushbait-v2 699 rounds vs 606 (the only official map that changes). Real opponents move, so the cost should be small; derived from the kit, not the map. **Held-out cost**: on the 78 gem-scarce / objective test maps (`maps/gold*`, `maps/obj`) it loses 32 of 468 games vs the proxies (`legend_m15` 355, without it 387), while it wins 12 of 170 on the official maps and is level on 67 other maps. No map-feature gate found (it helps on elkring and monolith, both heavy-gem maps). Fallback zip: `submissions/candidates/legend_m15_noreach5_20261020.zip` |

## Session 14 (GOD v3 / v4, patch 3.0)

| # | Where | What | Risk | Severity |
|---|---|---|---|---|
| 17 | `world.cpp` `altar_no_camp` 2 | an altar whose only approach tile is a camp's spawn tile opens when that camp is dead; the rule looks only at the 8 neighbours of the altar (Chebyshev 1, the tribute range) and at camp tiles; an altar walled off in any other way (holes on every side, a wall box with no gap) is "no altar" and the map is played for gold earned | a map where a teleport crystal could reach the altar's side is not handled (ISSUES #18) | low |
| 18 | `tribute()` / `no_altar_gold` | on a map with no usable altar the bot never tributes and values gems at 0; it does not try teleport crystals to reach a walled-off altar | if the final pool has an altar reachable only by crystal, we never bank there | medium |
| 19 | `stall_guard` 10, `stall_dash_off` 150, `dash_gain1` | literals: a stalled walking task is dropped after 10 rounds, hole routing is off for 150 rounds | tuned on nx61x71 / nx60x60 only | low |
| 20 | `pd_obj_heavy` uses `obj_min_hp` 4500 at draft time | same thresholds as the brain's objective mode (ISSUES #7) | a heavy objective just under 4,500 health gets no caster draft | medium |
| 21 | `draft.cpp` objective draft (`MP.objective`, Prism first, the caster ring) | fires on any map whose only gem group is heavy, including one midway between the spawns (nx50x50: 2 elks + 6 gems, two altars next to it, 27 gold clusters per side); the ring lost it 72-1008 twice on the ladder (Nyx, f8a4f886) with 37 deaths: both teams meet there every respawn | the caster team dies to Power-stacked melee on a contested centre; `pd_obj_side` (objective nearer to us than to them by `pd_obj_mid` 2 steps) under test | high |
| 22 | `gold_rank_of()` (brain.cpp, `gold_rank`) | a fixed ranking of champion types for who collects a landed reward (Stellar, Prism > Tavi, Cassi, Willow, Vesper > Issac, Marcella, Vendetta > Varg, Ryth > Ren, Heart of Ruin); not map dependent, but it encodes the patch-3.0 value of gold per champion (Power in the damage stat) | a future patch that changes the stat growth per shard changes the right order | low |

## Session 15 (sprint documents: `docs/sprint/RULES_DIFF.md`)

| # | Where | What is hardcoded | Why it matters | Severity |
|---|---|---|---|---|
| 23 | GOD v5 source (`brain.cpp`, `draft.cpp`, `common.h`) | `champion_type::heart_of_ruin`, `champion_draft::heart_of_ruin`, `camp_type::golem`, `ability_dash::modifier / radius` named directly | the sprint's API page (BotAPICpp.md, = SDK 2.2.5 enums) has none of them: **the zip fails to compile there** and the team leaves matchmaking. Fixed in `experiments/wip/x_sdkcompat.patch` (`bots/_god_c`, `_god_d`) | **high** |
| 24 | `brain.cpp` nearest-altar choice: `d += 6; // three hits to clear it` | an enemy-locked altar costs 6 steps (3 hits) | 3 hits in the sprint docs, 5 since patch 3.0; `bc::constants::altar_lock_hits` has the engine's value (not changed yet: it would change GOD v5's games) | low |
| 25 | `_god_d` `params.h`: `gold_value`, `burst_retreat` follow `SDK_HAS_HOR` | the tuning is chosen by the ruleset the engine compiles us with (Heart of Ruin present = patch 3.0) | a future engine with Heart of Ruin but the old economy (or the reverse) gets the wrong pair; a map-derived gold value (gold rate / gem rate of the map) would be the principled form | medium |
| 26 | ward rhythm: `round - ward_round < 10` (brain.cpp) | a new ward at most every 10 rounds | the sprint docs allow a ward move every round (patch 3.0: cooldown 10), so under the old rules we ward less than we could | low |

## Session 14, GOD v8 (from the Oct 20 code review, `docs/strategy_v2/GOD_IMPROVEMENT_PLAN.md` §3; v8 switches in `bots/_x_v8`)

| # | Where | What | Risk | Severity | v8 switch |
|---|---|---|---|---|---|
| 27 | `engage()` contact branch | Heart of Ruin's strike dash only on approach (B2) | the strongest spell unused once adjacent | high | `hor_strike` 2 |
| 28 | `support_spells()` | the shield spends the turn's one cast before `combat()` can strike (B3) | strike lost on contact turns | medium | `hor_strike` 2 |
| 29 | `mob_dash()` `strike_dash_hold` 9 (literal radius) | travel dashes spend the strike (B4) | dash on cooldown when the fight starts | medium | `strike_dash_hold` |
| 30 | `spells_on_camp()` | no damaging dash on camps (B5) | slower farming with Heart of Ruin | medium | `hor_camp` |
| 31 | `post_danger()` / one alert slot | DANGER never posted; a RALLY replaces a fresh OPPORTUNITY (B9) | the cheapest kill (an enemy tribute) lost to a skirmish | medium | `alert_prio` |
| 32 | `combat()` backup | unseen allies count as backup by their claim's centre, even walking home hurt (B10) | phantom support, lone deaths | high | `sup_mode` 2 |
| 33 | `ml2_model.h` | the danger model gives nearby allies no net credit (B11) | one-by-one retreats | high | `sup_mode` 8 |
| 34 | `build_for()` focus lists (`CT_HOR` and the casters typed in) and the "+15 focus" comments | the damage stat of the endless tail is a typed list; the 3.0.2 hotfix cut Heart of Ruin's focus growth 20% and nothing noticed (B17) | a weekly patch re-values a stat | medium | `hor_build`; P1-7 open |
| 35 | `brain.cpp` HoR passive 0.5 in `fm_mode` 1 | the engine constant `heart_of_ruin_missing_health_damage_max_bonus` exists only in the 3.0 SDK, so the value is typed (gated by `CT_HOR`, which never matches on 2.2.x) | a patch to the passive | low | `fm_mode` |
| 36 | `gv_map` reference (`gv_rho_ref` 6.3, `gv_exp` 0.5) | the map-derived gold value is anchored at the median gold / gem rate ratio of the 21-map pool (4.4-9.6, elk-arena 20.5) | a new pool with a different economy | low | `gv_map` |

## Patch 3.0.4 (Oct 21 balance: Stellar, Heart of Ruin, Ren nerfs; Vesper, Vendetta, Tavi, Prism buffs)

The engine probe (`experiments/results/probe_v3_0_4/`) confirms the patch numbers. GOD reads stats and ability modifiers from the
engine for its own body (`kit_of`, `base_stats()`), so its own fight / kill-time / burst arithmetic follows the patch. These parts do
not (champion knowledge typed into the code; none is map dependent):

| # | Where | What is typed in | Why it matters after 3.0.4 | Severity |
|---|---|---|---|---|
| 37 | `draft.cpp` `prior()` (**fixed by `pd_stat` 3**: no per-champion value; the model of §4 of doc 17 reads the designs and the map) | one constant per champion (Ren 1.0, Stellar 0.95, C&I 0.9, Varg 0.62, Ryth 0.6, Prism 0.36, Tavi 0.33, Vendetta 0.3, Marcella 0.2, Vesper 0.12, Willow 0.1, HoR 0.4); most date from pre-3.0 screens, only HoR / C&I were re-tuned on 3.0.x | the patch nerfs the two top priors (Stellar -22% Lanchester power hp x dps, Ren -9%) and buffs three low ones (Tavi +23%, Vesper +22%, Vendetta +25%): the draft cannot see it | **high** |
| 38 | `draft.cpp` `pd_score` (**fixed by `pd_stat` 3**: roles from attack range, first pick by value, map types as kit terms) | Stellar-only "one ranged carry" +0.2, Ren-first opening pick (`first = ... D::ren`), HoR +1.2 at team size 3 (`pd_hor3`), objective ring casters by name (Prism / Tavi +0.75), `is_caster` / `is_front` by name | same: roles and bonuses follow names, not kits | **high** |
| 39 | `brain.cpp` `ally_dps_on()` | an ally's spell damage = base focus x 3.4 (Stellar), 2.0 (Cassi) or 1.5 (everyone else) per 8 rounds | Ren's stun damage is now 0.75 x focus (1.25 before): his helping damage is over-counted 2x in group scoring; allies' real kits are known (`World` keeps `kit_of` per ally) | medium |
| 40 | `brain.cpp` `gold_rank_of()`, `ally_melee()`, `build_for()` focus flags | champion lists by name (who converts gold best, who is melee, which stat the build stacks) | `ally_melee` / the focus flag are kit facts (attack range, spell modifiers) and could be read; the gold rank is a measured order | low |
| 41 | `draft.cpp` `body_feats` (pd_stat 3) | three passives are tied to the champion that has them (Varg's splash, Vesper's gold bonus, Ren's retaliation): the SDK exposes them only as named constants (`varg_splash_radius`, `vesper_vale_bonus_gold_percent`, `ren_retaliation_focus_ratio`); their values come from the engine | a new champion with a splash / gold / retaliation passive is not seen as having it | low |
| 42 | `draft.cpp` `pd_score_model` | v8's two map-type rules, re-expressed on kit features with v8's measured magnitudes (objective ring +0.75 x range-4 spell share, melee -0.6, melee area stun +0.4; open small maps retaliation -0.5, splash +0.45) | 10 + 6 of the 308 maps use them: too few to fit; the values are v8's measurements | low |
| 43 | `params.h` `pd_w_*` | the model's weights: since GOD v10 a logistic fit of 17,004 games of the 156 tuning maps on engine 3.0.4 (v8, our round robins and screens; GOD v8 / the dynamic draft used a fit of 7,520 games) | a different opponent population or a large patch can move the weights: refit with `tools/draftmodel/fit.py` on new games (minutes) and check on held-out maps (the refit with the lower log loss measured only +3 points alone) | medium |
| 44 | `brain.cpp` `build_for()` | build lists per champion (style 2), measured in earlier sessions | `build_kit` (kit-derived lists) and `build_stat` (kit-derived stat) are in the code, being measured on the dynamic draft | medium |
| 45 | `draft.cpp` `note_pick()` (`draft_guard`, GOD v10) | a fixed fallback order of champions, used only when the chosen pick throws | it runs only after an SDK or roster surprise (never in our games); without it the engine picks at random | low |
| 46 | `params.h` `pd_sub_from` / `pd_sub_to` (v11, `experiments/wip/x_v11.patch`) | the user's request "draft Prism instead of Vesper Vale": a fixed champion substitution (draft ids 1 -> 5) on top of the dynamic draft | it overrides the model for one champion whatever the map or the enemy picks; measured 37.2% vs GOD v10 (156 games), so it is **not** in the shipped bot, only in the candidate zip the user asked for | high if shipped |
| 47 | `brain.cpp` `smart_ward()` (v11 `ward_smart`) | score weights 15 per tile ahead, x0.25 map value, bush +10 / x1.3, corridor +20, altar +30, x0.35 near an ally ward | hand-set, not fitted; the terms read map features at runtime (groups, altars, spawn fields, bushes), no map identity | low |

## Proxy-only hardcoding (off in the shipped bot)

`draft.cpp` `official_map()` (recognises the 17 official maps by size and camp mix) and the per-map tables `MITE`, `IFISH`, `OURS`
(`mapdraft` 1-3), the sneaky-bush mask `md_sneaky` (`mapdraft` 4), `build_style` 9 (Mite), 10 (ifish), and the IC proxy settings of
session 12. They exist to imitate other teams' fixed per-map tables; the shipped bot uses `mapdraft` 6 (parameter draft) and
`build_style` 2, so none of it runs. `md_stampede` only acts with `mapdraft` 3.

## mapintel (session 18b, MAPAnalysis.md; `tools/mapintel/`, library `tools/mapintel/cpp/mapintel/`)

Hardcoded on purpose or measured on the current pool / patch; each may need a refresh when the map pool, the patch or the bot changes.
- **The exact-match table** `known_maps.h` (approved by the user): the 40 official maps by fingerprint, with the catalog's plans and the
  ladder's draft data. A changed map does not match (8 of 8 perturbed copies took the fallback in the test). Regenerate with
  `draft_learn.py` + `export_headers.py` after a new `cambc init` map pull, a new ladder download or a patch.
- **Fitted on the current data, not derived**: the archetype scaling, PCA basis and centroids (40 official maps), the draft values
  (`model_weights.h`: GOD v10's roster battery, SIMULATED v10: values for v10's play, not for a new bot; rerun `run_battery.sh --bot
  NAME`), the opening score `first_scores()` (599 ladder games of the current patch), the strong-team pick rates (top 20 ratings on Oct 24).
- **The ladder draft model has no signal**: on 8,455 ranked games no champion model beats team rating alone out of sample, so the
  table's `value` comes from the battery; the ladder pick rates are an imitation prior, not a measured value.
- **Compact plan constants** (`compact.py` = `plans.h`): capture 6 rounds, heal-trip rule (a trip per heal_use x health of damage taken
  solo; heal_use = 1 - the fitted retreat line = 0.48 and the camp damage scale 1.3 are LEARNED (`econ_learn.py`, through
  `model_weights.h` `econ_constants()`; 0.7 and 1.0 without it), since the user's change 5), recall 5 + 1 rounds, value = gems + 0.1 x
  gold, the candidate row of 12 groups, the attack-reset bonus 1 / 8, Varg's splash as the only basic-attack splash
  (`champion_type::varg`), contested band max(3, 0.1 x spawn distance), plan-4 threshold formulas (0.12 d, 80, 0.2 d, 8, 3, 30). Not modelled: Ryth's health-scaled strength, Heart of Ruin's missing-health bonus, Prism's focus per gem, shields,
  heals, allies tanking, shopping (the catalog's fight simulation has them). Change 5 (`fallback_gap.py`) measured the missing
  mechanics one at a time against the catalog's plan 1 (bodies with the catalog's first target, 0.408 before): the fitted economy
  constants 0.454 on 34 changed map-teams (adopted); shields 0.386, Heart of Ruin's bonus 0.314, stuns 0.408 on 18 changed map-teams,
  Ren's retaliation changed none: not added. Plan 2 is now by the walk (one BFS per candidate altar: 0.98 of the groups get the
  catalog's altar, 0.81 by the box distance), at up to ~95k more fuel on the first draft turn. Plan 1's first targets match the top
  teams' first captures no better than "nearest groups" (validate_ladder.py: 0.53 vs 0.54); use `first_scores()` (0.65 held out) for
  the opening.
- **Plan 4 thresholds** (`experiments/results/mapintel/plan4/weights.json`, LEARNED from 599 current-patch replays): learned constants
  (k_abandon 0, p 1000%, d_regroup 6, bank margin 7) replaced the formulas, which they beat on held-out maps; no map feature moved them
  (the ridge chose the strongest regularization), so they are one value for every map. w_max stays the formula (30), r_enemies 8 is
  not fitted. The event definitions (30-round abandon window, 12-tile threat radius, 8-tile power radius, the bank-trip and wait rules)
  are choices of `plan4_learn.py`.
- **Economy model constants** (`economy.econ()`, `experiments/results/mapintel/economy/constants.json`, LEARNED from 599 replays):
  retreat 0.52 and shop gold 115 and gold weight 0.167 (gold per gem, with the gold-only captures) measured, bank bag 20, heal threshold 0.9 and damage scale 1.3 fitted to the
  real bank sizes, the pace and kill times; the opposition share logistic (slope about 0.62 per band of walk gap). Still unfitted: the model
  build (Monster in the damage stat, Jungle health, Power). Plan 3 keeps the gold weight 0.1 (not refitted, the user's choice).
- **Engine facts typed in after a probe** (re-probe after a patch): crystal hop range 3 (`CRYSTAL_RANGE`), the dash legality rules, the
  pick -> body mapping (picks 0-2 = bodies 0-2, pick 3 = bodies 3 and 4, picks 4-11 = bodies 5-12, the SDK enum order).
- **Draft-memory layout**: the mapintel block at offsets 512-863 (version 1, magic 0xA7). A bot's own data must stay below 512 (GOD
  v10 writes 4 bytes at 0: tested to coexist). The test bot also uses 8-511 and 864-999 for its own prints (test only).
- **Step 7 (`tools/mapintel/dl/`)**: `dl_weights.h` exists only when a deep model beat the step-6 model by the margin in `dl_train.py`
  (`MARGIN`: +0.01 top-n share / top-1, -0.003 log loss) on held-out maps; its weights are fitted on the current pool and ladder
  (T1a / T1b: 599 ladder games; T2: GOD v10's roster battery, SIMULATED v10). The next-target model is meant for a candidate list
  (the test uses the 16 groups nearest the previous capture): all 64 groups cost about 107k fuel, more than a game turn.

## teamplan (session 18c, TEAMPLAN.md; `tools/teamplan/`, library `tools/teamplan/cpp/teamplan/`)

Typed-in values and engine assumptions of the team-play library. Each may need a refresh when the patch, the map pool or the bot
changes. No champion name or map identity is in the logic: champions enter through their designs, `passive_type` and the SDK constants.

- **ASSUMED values in `params.h`** (starting values; only some were exercised by the batteries, TEAMPLAN.md 11):
  - `kit.h`: `enhanced_extra` 1.0, `missing_hp_avg` 0.5, `hits_taken` 1.0, `splash_targets` 1.0, `area_targets` 1.0, `fight_rounds` 8,
    `ranged_front` 0.5, `immune_ehp` 0.15, `dash_escape` 0.2, `reach_escape` 0.05;
  - economy: `danger_hazard` 0.02; `items_half` 0 (off: the value 12 was contradicted by the top teams' capture choices);
  - `bag.h`: `bag_fight` 30, `bag_fight_scale` 60 (the `tp_bag` switch on v10 used 60), `hunt_bag` 25, `hunt_bonus` 0.5;
  - `focus.h`: `kv_ref` 40;
  - `tiebreak.h`: `tb_period` 25, `tb_enter` 150, `tb_leave` 50, `tb_min_round` 600, `tb_defer_cap` 60 (150 also tried), `tb_safe_dist` 9,
    `tb_final_margin` 30, `tb_denial_rounds` 60;
  - `assign.h`: `own_bonus` 0.25 (the v10 test's x 1.25), `gemfree_front` 0.5;
  - `swap.h`: `swap_period` 50, `swap_hold` 150, `swap_margin` 0.25, `lag_ratio` 0.6. Never run in a game: v10's live bytes have no room
    for the per-body progress codes.
- **LEARNED on the current patch** (refit after a patch, commands in `tools/teamplan/README.md`):
  - `gold_gems` 0.02 (mapintel `econ_learn.py`);
  - `team_rate` 0.94 and `hazard` 0.0016 (599 ladder games, `roles_ladder.md`);
  - `capture_mode` 1 (25 raw replays, `capture_check.py`).
- **Engine-structure assumptions** (re-probe after a patch):
  - **Pick to body**: the SDK enum order. Picks 0-2 are bodies 0-2, pick 3 is bodies 3 and 4 (two bodies that die together), and picks
    4-11 are bodies 5-12. This is the v10 adapter's `pick_of_type`, the same mapping mapintel uses.
  - **Passive to constant** (`sdk_bridge.h` `consts_from_sdk`): the SDK names each passive's constant after the one champion that has the
    passive today. `kit.h` applies a constant by the design's passive tag, so a passive moved to another champion still works. Two
    limits:
    - a new passive tag gets no constant (its kit term is 0);
    - two champions sharing a tag with different numbers would both get the one constant.
  - **The team index** comes from `cambc::detail::sdk_my_team()`, a `detail` function that can change without notice.
  - **Turn order** (`timing.h`), measured on one decoded top-team replay, rounds 30-400:
    - turns alternate one body at a time;
    - team A starts odd rounds;
    - higher priority acts first, and ties act in body-type order.
  - **The enhanced attack reset stuns for one round** (`enhanced_stun`, COMPUTED from the rules text: the SDK payload has no duration).
  - **The engine test compares against `experiments/results/teamplan/designs_3_0_5.txt`**: after a patch, run `--dump-designs` first.
- **The v10 test copy** (`v10_adapter.patch`, cut against `bots/god` = GOD v10):
  - if `bots/god` changes, the patch stops applying (`prepare_v10.py` exits with a message);
  - the OWN prototype sits at draft memory offset 8 (magic 0x54, version 1). Its writer rewrites v10's bytes 0-3 as `B7 02 00 00`: v10's
    team and plan-choice bytes become 0. Nothing in v10 reads them while `dm_plan` is off (the default), and with every switch off the
    copy plays v10's games 80 of 80;
  - the final layout (`docs/DRAFT_MEMORY.md`) moves OWN to 84-147.
- **No fuel guard on the OWN write in the v10 test**. It leaves 24.2k of 100k at worst on the 40 official maps (road-of-riches, 5 bodies).
  A map with a longer group list could run out after the pick. The final layout adds the guard (`docs/DRAFT_MEMORY.md` 7).
- **Roster battery opponents** (`tools/mapintel/data/battery_rosters.json`, mapintel's): slots 0-2 are real strong-team rosters (LEARNED)
  on all 40 official maps, from one ladder snapshot (Oct 24). A new ladder changes them.
