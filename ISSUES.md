# ISSUES: hardcoded choices that may hurt when the map pool changes

The user's rule (session 12): derive parameters from the map and the game wherever possible; anything hardcoded is listed here.
Scope: the shipped bot (`bots/legend/src`, `submissions/legend.zip`). Sparring-proxy code (Mite / ifish / sneaky / IC tables) is
listed at the end: it is hardcoded on purpose and switched off in the shipped bot.

Severity: **high** = can pick the wrong plan on a new map; **medium** = a threshold fit on the 17 official maps; **low** = tuning
or engineering limits.

## Map identity or map size in live code

| # | Where | What is hardcoded | Why it matters | Severity | Fix |
|---|---|---|---|---|---|
| 1 | `brain.cpp` ring plan, `o2_ring` 3 (`(W.W == 60 && W.H == 50)` in the condition) | the caster ring fires on **any 60x50 objective map**, whatever our draft. `o2_ring` 3 was meant to replace the size test with "our team has Prism or Tavi and 5 champions", but the size term is still OR-ed in | a new 60x50 objective map with 4 champions or no casters would ring with melee bodies (the ring lost 14/30 vs 20/30 on the 4-champion objective maps, session 11) | high | drop the size term when `o2_ring` is 3 (one-line change; checked in session 12: official games unchanged, since stampede drafts the casters anyway) |
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

## Proxy-only hardcoding (off in the shipped bot)

`draft.cpp` `official_map()` (recognises the 17 official maps by size and camp mix) and the per-map tables `MITE`, `IFISH`, `OURS`
(`mapdraft` 1-3), the sneaky-bush mask `md_sneaky` (`mapdraft` 4), `build_style` 9 (Mite), 10 (ifish), and the IC proxy settings of
session 12. They exist to imitate other teams' fixed per-map tables; the shipped bot uses `mapdraft` 6 (parameter draft) and
`build_style` 2, so none of it runs. `md_stampede` only acts with `mapdraft` 3.
