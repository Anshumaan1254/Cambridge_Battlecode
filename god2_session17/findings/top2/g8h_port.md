# g8h = g8 (god.zip, GOD v8 + opponent model, git 28d7340) + later GOD bug fixes, ported by hand

Session 17, Oct 23 2026. `bots/g8h` started as a byte copy of `bots/g8/src` (line endings normalised to LF: same text as
`git show 28d7340:bots/god/src/*`). Every behaviour change sits behind a `struct Params` switch in `bots/g8h/src/params.h`
(block "g8h (session 17)", lines 747-762, all ON by default). With every new switch OFF (`hop_score_start=0 hop_score_floor=0
pocket_fix=0 pocket_guard=0 cap_timeout=0 osc_fix=0 real_channel=0 draft_guard=0 watchdog=0 init_resume=0`) the code paths are
g8's, except the fuel cuts of (a), which have no switch (same results, less fuel).
Build: `cambc build g8h --release` OK (warnings only: the constant `&&`/`||` warnings g8 already had, plus one of the same kind at
nav.cpp:369). 0 bot faults in every release bench below (960 games of g8h builds and ablation variants).

## Gate (release, 40 maps x 2 sides, deterministic)

`python tools/live/localbench.py g8h g8 --jobs 6 --tag g8h_vs_g8` (final build; re-running gives identical results)

| | g8h | g8 |
|---|---|---|
| wins | 31/80 (38.8%) | 49/80 (61.2%) |
| banked gems / game | 589 | 796 |
| deaths / game | 18.7 | 17.0 |
| bot faults | 0 | 0 |
| fuel-outs total (per game) | 149 (1.86) | 1,362 (17.02) |
| fuel-outs rounds < 10 (init) | 146 (1.82) | 788 (9.85) |
| fuel-outs rounds >= 10 | 3 (0.04) | 574 (7.17) |
| fuel-outs by round | r1 48, r2 54, r3 40, r5 4, 3 later | r1 358, r2 212, r3 94, r4 44, r5-7 80, then 4-84 per 100-round bucket to r1900 |
| top fuel-out maps | starfish 16, ambush 15, expanse 12, lanes 12, boss_battle 12, islands 12, yellow_brick_road 12, corners 8 | road_of_riches 255, fracture 254, yellow_brick_road 119, lanes 84, islands 82, shortcut 75, big_world 45, expanse 36 |
| stand-stills >= 40 rounds (`longstand.mjs 40`) | 5 (0.06/game), 218 body-rounds, longest 50, none >= 100, none on a camp tile | 24 (0.30/game), 1,625 body-rounds, longest 218 (islands Ren), 3 >= 100, 12 on camp tiles (yellow_brick_road 8) |
| A-B-A rounds per body per game (`oscillate.mjs`) | 53.0, longest run 37 | 54.8, longest run 45 |

Reference, g8 in `C:/battlecode/cache/bench/g8_vs_b54`: 26/80, fuel-outs 12.96/game (init 8.25, later 4.71; road_of_riches 278,
fracture 87, yellow_brick_road 76, lanes 70, islands 67), 31 stand-stills >= 40 (0.39/game, 2,000 body-rounds, longest 238 on
islands, 4 >= 100, boss_battle 6 / yellow_brick_road 6 / islands 4).
Third party: `localbench g8h _b54 --tag g8h_vs_b54` 22/80 (27.5%), gems 526-890, fuel-outs 1.7-1.8, vs g8's 26/80 (32.5%),
gems 539-804, fuel-outs 13.0-1.8.

Intermediate build (all of a-h, before the resumable init; bench kept as `g8h_v1_vs_g8`): 32/80, gems 663-774, fuel-outs 5.35/game
(init 5.22: r1 282, r2 104, r3 24, r4 8; later 0.12), 11 stand-stills >= 40 (longest 46).

**Verdict.** The ported fixes do what they were written for: lost turns 17.0 -> 1.9 a game (later-game fuel-outs 7.2 -> 0.04,
init 9.9 -> 1.8), long stand-stills 24 -> 5 per 80 games (none >= 100 rounds, none on a camp tile), 0 faults. They do NOT make the
bot stronger locally: g8h wins 38.8% of the mirror vs g8 and 27.5% vs _b54 (g8 32.5%). Local own-build games are known not to
predict the ladder (AGENTS.md section 7) and these switches target ladder problems (top-team stuck/oscillation, recall spammers,
capture deadlocks); the ladder (unranked groups vs the target teams) has to judge. Not submitted.

### Leave-one-out ablation vs g8 (80 games each; `experiments/top2/g8h_tools/vbench.py`, tags `g8hv_<name>_vs_g8`)

| variant | wins | gems | deaths | fuel-outs/game |
|---|---|---|---|---|
| g8h (all on) | 31 (38.8%) | 589-796 | 18.7-17.0 | 1.9 |
| osc_fix 0 | 35 (43.8%) | 665-759 | 21.1-17.7 | 1.9 |
| cap_timeout 0 | 32 (40.0%) | 591-788 | 18.7-17.1 | 1.9 |
| real_channel 0 | 38 (47.5%) | 652-762 | 18.3-18.1 | 1.9 |
| real_channel 0 + osc_fix 0 | 32 (40.0%) | 642-770 | 21.6-17.4 | 1.9 |
| pocket_fix 0 + pocket_guard 0 | 32 (40.0%) | 595-802 | 19.0-16.8 | 1.9 |
| hop_score_start/floor 0 | 31 (38.8%) | 606-813 | 20.4-17.2 | 7.4 |
| init_resume 0 | 34 (42.5%) | 669-749 | 18.6-19.5 | 5.7 |
| every switch off (= g8 + fuel cuts a) | 37 (46.2%) | 719-764 | 20.6-19.8 | 12.2 |

One 80-game run has a standard error of about 5.5 points and per-map outcomes are chaotic (the fuel cuts alone move 46.2% off 50%),
so no single switch is significant and the effects are not additive (rc 0 + osc 0 is below either alone). The largest is
real_channel (+7 games when off): g8 recalls for real, and the switch ignores a genuine recall on its first sighting, so our bodies
react one round later to every real recall (the switch only pays against recall spammers such as Pantheon and :3). The rest of the
gap to 50% is spread over the switches together (all off: 37/80).

## Ported hunks

| fix | source | target in bots/g8h/src | switch | notes |
|---|---|---|---|---|
| a1 per-kind camp stats cache | f0c0c9c world.cpp | `World::init_static_groups` (world.cpp 153-269; cache at the camp loop) + `World::KindStats`/`is_kind` (world.h 188-198) | none | one `base_stats()` host call per camp kind instead of per camp; same values |
| a2 neighbour masks | f0c0c9c world.cpp/.h | `Group::nb` (world.h 40); masks built per group (world.cpp 217-235); fast path at the top of `Group::update_cluster` (world.cpp 427-442) | none | same cluster value as the pairwise loop (groups up to 32 camps; larger groups use the old loop) |
| a3 altar-approach bit test | f0c0c9c world.cpp | `World::init_static_finish` (world.cpp 277) | none | `camp_tiles.is_set(t)` before scanning every camp |
| a4 golem flag | f0c0c9c | skipped | - | v8 has no `Group::golem` |
| b hop fuel guards | ff8514f brain.cpp/params.h | `Brain::farm` island comparison (brain.cpp 5930) and crystal-hop loop (5957-5969) | `hop_score_start 55000`, `hop_score_floor 45000` | commit values; 0/0 = g8 |
| c1 pocket_dash | 14f1bc8 brain.cpp/.h | `Brain::pocket_dash` (brain.cpp 1908-1948, brain.h 292) | `pocket_fix 3` (bits 1+2, HEAD's value) | dash to the landing tile with the shortest walk home |
| c2 calls | 14f1bc8 | `Brain::turn` after combat (brain.cpp 916-919, bit 2), `go_home_step` (1953), `go_home` dash-else-recall (3760-3774) | `pocket_fix` | |
| c3 step_field fallback | 14f1bc8 nav.cpp | `Nav::step_field` dynamic-search fallback (nav.cpp 445-448) | `pocket_fix` | no walking search from a tile the field cannot reach or from a pocket |
| c4 pocket guard | bots/bb4 brain.cpp | top of `Brain::unstick` (brain.cpp 1430-1456); `!(P.pocket_guard && W.dist_home(pos) >= BIG)` on both `dash_off_until` sites (1472, 1507) | `pocket_guard 1`, `pocket_idle 12` | in a pocket hole crossings stay on; 12 idle rounds -> dash out, else recall |
| c5 FUEL_STATE trace (`debug_state`) | 14f1bc8 | skipped | - | trace-only; replaced by the compiled-out G8H_INIT_TRACE probe (common.h 18-30) |
| d capture-deadlock timeout | cfe377c brain.cpp/.h | `Brain::capture_group` (brain.cpp 6200-6222), state `cap_stand_*` (brain.h 358) | `cap_timeout 1` (HEAD: inside SV.osc_fix) | 15 rounds (capture_time + 10) on a reward without it landing -> blacklist 40 rounds, step off |
| e1 danger-detour hold | 9618135 nav.cpp | `Nav::step_field` danger detour (nav.cpp 361-375) | `osc_fix 1` | keeps the detour (stuck_detour / detour_hold) |
| e2 A-B-A(-B) breaker | 9618135 brain.cpp | `Brain::turn` after perceive (brain.cpp 777-787); `step()` (1853) and `go_group()` (1889) drop danger avoidance until `osc_break_until`; state brain.h 354-355 | `osc_fix` | `osc_break_until` stays -1000 when off |
| e3 no-progress detector | 9618135 brain.cpp | `Brain::unstick` (brain.cpp 1458-1484), state brain.h 356 | `osc_fix` | 15 rounds without getting closer -> dash kit routes without hole crossings (never in a pocket), else blacklist; the SV.convoy line is dropped (no convoy in v8) |
| e4 ml2_hold 4 | 1d5510c brain.cpp | `Brain::combat` ml2 block (brain.cpp 3321-3322) | `osc_fix` (4, else P.ml2_hold 0) | |
| e5 post-flee target skip | 1d5510c brain.cpp/.h | `post_danger` records `flee_pos/flee_round` (brain.cpp 3496); `group_score` skips groups within 8 for 15 rounds, WHY 15 (5512-5514); brain.h 357 | `osc_fix` | |
| f watchdog | existing g8 param | params.h 745 | `watchdog 1` | g8 already had main.cpp's watchdog + `Brain::safe_fallback` |
| g real_channel | bots/bb4 world.h/.cpp | `Enemy::recall_streak` (world.h 96); `World::perceive` (world.cpp 505-522) | `real_channel 1` | recalling counts from the 2nd consecutive sighting on one tile |
| h draft_guard | fc05b5d draft.cpp | `note_pick` (draft.cpp 28-58) | `draft_guard 1` | applied cleanly |
| i resumable map init | 15ed961 world.cpp/.h, brain.cpp/.h, params.h (subset) | `World::init_static_step` / `init_static_stage0` / `init_static_groups` / `init_static_finish` (world.cpp 21-295; `init_static()` = loop of steps with floor 0); `Brain::init` split + `init_after_static` (brain.cpp 524-675); `pre_init_move` (676-689); early return in `turn` (727-739); `init_phase` (brain.h 41-43) | `init_resume 1`, `init_fuel_floor 30000`, `init_turn_floor 60000` | ported because init fuel-outs were 5.22/game after a-h; the body is split into stages instead of re-indented as in 15ed961 |

Not ported from 15ed961: hysteresis 1.3 (a tuning change), golem_team (v8 has no golem team plan), blob/squad farming code (off in
HEAD, measured slower and weaker). Not ported from the osc_fix line: the flee hold of 65b212f (moved to its own SV.flee_hold, local
47.5%, off in HEAD), SV.convoy hooks. Not ported from fc05b5d: watchdog9 / fallback_turn (only the existing `watchdog` was asked).

## Init fuel (why the resumable init, and what is left)

Probe: `#define G8H_INIT_TRACE 1` at the top of a copy of common.h (debug build, `cambc run COPY g8 --map M --rounds 6`), lines
`IT r=<round> <tag> <fuel left>` in team-a.stdout of the replay bundle. Fuel per body before the port of 15ed961:

| map | stage 0 (altars + fields) | camp-group loop | finish + units + nav/learner | groups / camps | total |
|---|---|---|---|---|---|
| 01islands | 86k | 206k | 59k | 46 / 118 | ~390k |
| 00road-of-riches | 80k | 222k | 56k | 51 / 132 | ~400k |
| 01boss-battle | 64k | 204k | 49k | 31 / 158 | ~360k |
| 00lanes | 90k | 168k | 60k | 42 / 84 | ~360k |
| 01big-world | 113k | 140k | 46k | 24 / 92 | ~340k |
| 00collision | 40k | 96k | 28k | 20 / 56 | ~205k |

(+ ~40k before init: main loop and build list; first game turn 200k, later turns 100k). A dash kit adds the hole-crossing scan to
stage 0: islands ~177k (878 holes), big_world ~110k, fracture ~107k. The first full turn after init costs ~50-60k.
With the resumable init the group loop yields below 30k and the body steps toward the centre (`move_towards`, 5-12k, ~21k on
big_world); init fuel-outs 5.22 -> 1.82 a game. The rest come from (1) the dash-kit hole scan in stage 0 (not resumable), (2) the
finish + `init_after_static` (~35-60k) when the loop ends just above the floor (lanes, boss_battle: one fuel-out in round 3), (3)
`move_towards` started near its 20k guard on 100x100 maps. Each is a few lines (resumable hole scan; defer the finish below
floor + 60k; a cheaper step) if the last ~1.8 lost turns a game matter.

## Reproduce

```
cambc build g8h --release
python tools/live/localbench.py g8h g8 --jobs 6 --tag g8h_vs_g8
python experiments/top2/g8h_tools/fuelsplit.py g8h_vs_g8 g8h g8          # fuel-outs < 10 / >= 10, maps, champions
python tools/live/par.py 6 ls.jsonl tools/live/longstand.mjs 40 -- C:/battlecode/cache/bench/g8h_vs_g8/*.repl26a
python experiments/top2/g8h_tools/lsagg.py ls.jsonl g8h g8
python experiments/top2/g8h_tools/vbench.py no_rc real_channel=0         # ablations (copies in C:/battlecode/cache/g8h_vars)
```
Bench folders: `g8h_vs_g8` (final), `g8h_v1_vs_g8` (before the resumable init), `g8h_ri1_vs_g8` (= final), `g8h_vs_b54`,
`g8hv_{off,no_osc,no_cap,no_rc,no_rc_osc,no_pocket,no_hop,no_init}_vs_g8`.
