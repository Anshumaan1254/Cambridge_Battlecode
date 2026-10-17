# x_contest6: contest-like maps (agent contest6, session 6)

Bot copy `bots/_x_contest6` (local), patch `experiments/wip/x_contest6.patch` against `bots/_b6/src`
(`cd bots/_x_NAME && patch -p1 < ../../experiments/wip/x_contest6.patch`).
Status: **small, safe win; recommended: merge `cm_obj` only (default 1). Everything else is built but off (measured: no effect).**
The map cannot be "won" against a strong opponent by a strategy switch: the opening fights decide it (below).

## Detector (`World::detect_contest`, `cm_mode`)
Gem groups are counted in `init_static`'s group loop: `cm_lone` = a monolith that is a single camp, `cm_other` = any other group
with gems. `cm_mode = cm_lone >= 2 && cm_other == 0` (every gem comes from lone monoliths; the rest is gold). Fires on `contest`,
its ladder copy `lad_50x50_R_c5_65bb75` and the 12 `maps/gold/gold_mono_*` + `maps/gold2/gold_mono_*` maps (14 maps, 13 distinct).
Does **not** fire on any other map of the 56-map pool (monolith, rows, elkring have wolves / elks / gem clusters) nor on the other held-out
maps (`gold_monoE*`, `gold_monoelk*`, `gold_monowolf*` have fused or elk/wolf gem groups; `obj/*`).

## What is merged-worthy: `cm_obj` = 1
On `cm_mode` the lone monoliths become objective groups (`obj_mode`, `Group::objective`): the pace agent's `obj_min_attackers=1`
effect, but only where the detector fires (the pace agent measured it neutral-to-negative on the other lone-monolith maps, so it was
kept off globally).
- Unopposed pace (vs idle, both sides): contest 1074 -> 936 (c6a with the raw param: 905); 13-map pool mean 1040 -> 957
  (gold_mono_64x64 1002 -> 821, 48x48 1089 -> 1004, 30x30 1179 -> 1160). First monolith hit r493, captures r548, 645, 727, 819, 900 (both
  monoliths alternate: the other one is simply the next best group while ours respawns 150 rounds).
- 17 official maps vs idle: 576.2 -> 568.9; only contest moves meaningfully (expanse +23, lanes -9 are fuel-shift noise from the extra
  init code, 2 games each).
- Head-to-head vs `_b6`, 56 maps: 55/112 = 49.1 (official 17/34 = 50.0), 0 faults.
- Contest-like pool (13 maps + contest, both sides, 14 maps x 2) vs `_ST _L0 _es2 _c3 _v6 _devci` (168 games): `_b6` 112 (66.7%), `cm_obj` 117 (69.6%).
  Vs the four strong ones (112 games): 61 -> 66 (noise is +-5). Deaths 3730-4059 -> 3643-3747.
- Contest alone vs `_ST _L0 _es2 _c3 _v6 _r2 _devci _hunt2`, both sides: 11/16 (loses both sides to `_ST`, side B to `_L0 _c3 _v6`).

## Why nothing else helps (the real lesson)
- **The opening decides the game.** Kill difference in rounds 1-150 (60 pool games, tools in `/tmp/contest6/open.mjs`): ahead -> 29/40 wins
  (72%), level -> 7/19, behind -> 12/53 (23%). We are behind in 47% of the games, ahead in 36%, against sparring bots of our own family.
  Typical loss (contest, `_b6` vs `_ST`): by r21 our Cassi/Issac/Ren/Varg each reach the contested central gold triples one by one
  (Issac 565/900 HP alone at (23,27)), the enemy Ryth+Stellar+... arrive together; Cassi & Issac die at r30 to one Ryth cast, the other
  two by r53, then waves of respawned bodies (60 rounds) walk back into the same pack: 77 deaths vs 24 over 1,859 rounds, each body lives ~59
  rounds. Deaths by last task (421 deaths, 4 games): flee 237, fight 116, farm 35, home 11, wait 11, capture 11, i.e. 56% of deaths are bodies
  that are already losing a fight and walk home with chasers; the gold camps (dps 0) kill nobody.
- The monolith is 27 steps from our spawn and 28 from theirs (contest): there is no safe monolith.
- Tried on the 14-map pool vs `_ST _L0 _es2 _c3` (112 games; baseline `_b6` 61, `cm_obj` 66; sigma ~5 games), all built behind switches:
  | change | wins | note |
  |---|---|---|
  | `deathball_until` 200 (existing) | 39 | much worse |
  | skip contested gold (`obj_open_rounds` 200 / 500 + margin 6, i.e. stay on our half) | 8/22 and 50 | worse: the enemy owns the centre, deaths 1237-872 |
  | skip only enemy-half gold (`obj_open_margin` 1, whole game) | 59 | neutral |
  | `cm_rush_until` 60 / 150 (all bodies converge on our richest gold group, others x0.25) | 65 / 66 | early kills 2.57 vs 2.36 per game with 60, still noise |
  | `cm_buddy_pen` 0.3 / 0.6 (contested gold without a claiming or visible ally x0.3 / 0.6) | 61 / 67 | neutral |
  | `fight_margin` 1.6 / 1.05, `retreat_hp` 0.4, `threat_memory` 10, `target_threat_adv` 1.8 | 71 / 71 / 69 / 70 / 63 | all inside the noise of 66 |
  | `start_round` 3, `camp_in_fight` 0, `race_mode` 0, `danger_detour` 0 (contest only, 16 games) | 9, 11, 10, 9 of 16 | baseline 10 of 16 |
- `_ST` (the shipped build) beats every newer build on contest both sides (`_ST` 15/18 vs the panel; `_b6` 10/16; a variant with every session-4..6
  switch turned off still loses to `_ST` 0/2), but the same builds lose to `_ST` only 13/28 on the pool, so the contest cell is a deterministic
  coin: one cell has +-5 points of chaos; do not tune on it.

## Switches (params.h, all `cm_*`)
- `cm_mode` 1: detector. `cm_obj` 1: lone monoliths = objective groups (**recommended**).
- Off, measured neutral: `cm_rush_until` 0 (+ `cm_rush_bonus` 3, `cm_rush_pen` 0.25), `cm_buddy_pen` 1 (+ `cm_buddy_margin` 6, `cm_buddy_r` 8).

## Not done / ideas
- The real ladder opponent (Stellar, Tavi, Prism, C&I, Ren) kills 63 bodies for 3; no sparring bot reproduces that, so no number here says
  the ladder result changes. What `cm_obj` does for the ladder game: the team goes for the monolith from ~r490 instead of ~r600+
  (our shipped build never hit it), if it survives that long.
- A real fix for the opening needs better fight selection (56% of deaths happen while fleeing; `can_escape` ignores enemies that join during a
  20-step walk home) or a pack-arrival protocol; both are general (not contest-only) and were out of scope.
- 200-gem bags must be banked at the two central altars (20 turn tribute): not measured to matter here (lost games: 100 gems lost per game).

## Reproduce
```
SRC=bots/_b6 tools/variant.sh _x_contest6 && (cd bots/_x_contest6 && patch -p1 < ../../experiments/wip/x_contest6.patch) && cambc build _x_contest6
python3 tools/bench.py _x_contest6 idle --maps maps/comp/contest.map26a --jobs 2 --out /tmp/contest6/p --quiet   # 936 rounds
```
Pool = `maps/comp/contest`, `maps/ladder/lad_50x50_R_c5_65bb75`, `maps/gold/gold_mono_*`, `maps/gold2/gold_mono_*`.
