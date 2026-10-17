# x_obj: objective maps (agent `obj`, session 3, 2026-10-17)

Bot copy: `bots/_x_obj` (local). Patch: `experiments/wip/x_obj.patch` (against `bots/_k1/src`; applies with
`cd bots/X && patch -p1 < ../../experiments/wip/x_obj.patch`). Benchmarked frozen copy: `bots/_x_obj4m` (same logic;
`_x_obj` only moved the detector into init_static's group loop afterwards, fuel-only change).
Status: **done; recommended for merge** (all `obj_*` switches as in the patch). Clear gains on maps whose gems sit in a
heavy multi-camp group (stampede); no change on contest and monolith-only maps (detector off there).

## Why we lose objective maps (measured)
- Tools (new): `tools/analysis/obj_audit.mjs REPLAY [--win N]` (per gem-source cluster: damage share per team,
  first hits, captures, deaths near / far, bodies near it, hits, deaths and banks per window),
  `tools/analysis/obj_timeline.mjs REPLAY cx cy from to [R]` (bodies near a tile per round with health, the
  cluster's health, deaths / captures / recalls). Map generator `tools/mapgen/objmaps.mjs` (below).
- `stampede` (60x50, V): the only gems are one fused group at (56-58, 23-26): 6 gem clusters + 6 elks, 17,400 HP,
  6 x 60 = 360 elk damage a round, pays 360 gems / 960 gold, respawn 60. Everything else is gold (70-140 per group).
  Altars are central (31, 23/26); spawns in the left corners, 56 steps from the group.
- `_k1` vs `_v6` on stampede (A, lost 720-720 on gold at r2000): **nobody touched the group before r905** (both bots).
  Then one or two of our bodies at a time chipped it (Cassi r905-921, Stellar + Cassi r1096-1142) and left it at
  1,707 HP for 130 rounds; `_v6`'s Ren walked in at r1264 and took 360. Damage share 58,637 ours vs 14,198 theirs,
  captures 2-2.
- Causes in the code:
  - `group_score` plans per body (plus claimers): no body can solo 6 elks within 5 heal trips, so the group scores
    -1 until late; the join cap is 2 bodies on a non-monolith group.
  - `safety()` retreats at 4 rounds of the raw damage of every camp in reach: 6 x 60 x 4 = 1,440, more than
    Stellar's whole 975 HP at r540, so ranged bodies stepped in and out of range without a shot (traced: T_FLEE /
    T_FARM alternating every round, health dropping 60 per 2 rounds).
  - Farming hits the lowest-health camp in reach first: the outer gem clusters (500 HP, harmless) died first while
    all six elks kept hitting.
  - Bodies walked in hurt (Ren 831/2100, Varg 614/1300) and were the first to leave; the 60-round give-up timer
    blacklisted the target mid-kill.
- `contest` vs `_r2` (A, lost 0-1000, deaths 87-19): decided in the opening: both teams walk to the gold triples
  next to the central bush box (r20-30); we lost 4 bodies there by r59 and kept losing ~10 per 200 rounds. The mirror
  (B) wins 1000-0. A fight problem more than an objective problem (we never hit the monolith; `_r2` captured 5x).
- Monolith-only maps (`gold_mono*`, `contest`): `_k1`'s per-body plan already farms a lone monolith (one body passes
  the plan with heal trips; first capture ~r650-1000). The two monoliths sit 8-13 tiles apart on several maps:
  traced `gold_mono_48` vs `_k1`: 20 of our 33 deaths next to our monolith, they took 2 of our 3 kills.

## Changes (all behind `params.h` switches, `obj_*`; only active when the detector fires)
- `obj_plan` (detector, init, folded into `World::init_static`'s group loop + `detect_objective`): heavy groups
  (`obj_min_hp` 6,000, at least `obj_min_attackers` 2 camps that hit back) holding >= `obj_share` 0.6 of the map's
  gem rate (gems / respawn). Fires on: `stampede`, `maps/gold/gold_monoE*` / `gold_monoEE*` (fused monolith + elks,
  9 maps with gold2), `maps/obj/*` (12). Off on every other map of the 56-map pool, on `contest`, and on the
  monolith-only gold maps (with `obj_min_attackers` 1 it also fired on those 17 + contest + its ladder copy; that
  was neutral-to-negative, see Results).
- `obj_team`: when no body's own plan (with claimers) can clear an objective group, plan it with the whole living
  team (`obj_team_ready`: team damage from designs x growth; ready when the clear takes <= `obj_clear_max` 40 rounds
  and the camp damage, attackers dying first, is <= `obj_absorb` 0.6 of the team's usable health; >= `obj_min_bodies`
  3 alive, <= `obj_dead_max` 1 dead). Value share `obj_value_share` 0.5. No join cap on objective groups.
  Stampede vs `_v6`: ready at r~475 (team damage ~1,180, clear 15 rounds, camp damage 2,560 of a 6,450 pool).
- `obj_gather` 3 / `obj_gather_r` 6 / `obj_gather_max` 30 / `obj_solo_rounds` 8: on a team-plan target, wait just
  outside camp range until 3 bodies are there (or the group is awake, or we kill what is left alone in 8 rounds).
- `obj_go_hp` 0.8 / `obj_go_far` 12: heading for a team-plan target from afar below 80% HP: go home first.
- `obj_attackers_first`: on an objective group hit camps that hit back first (gem clusters last) and, when only a
  harmless camp is in reach, step into reach of one that hits back.
- `obj_shield` / `obj_shield_enemy_d` 8: in `safety()`, objective camps with a visible ally strictly nearer do not
  count, and the rest count after Jungle/Durability for the steps out of reach + 1 (not 4 rounds raw); only while no
  enemy is within 8 (otherwise the old line).
- `obj_commit` 200: the give-up timer on an objective target gets 200 more rounds.
- `obj_max_wait` (18 = unchanged; 60 tested, no gain), `obj_open_rounds` (0 = off; opening avoidance of contested
  gold, tested on contest only: 6/8 both ways).
- Effect on stampede vs `_v6` (A): first hit r513, first capture r548 (35 rounds), captures r548 / r663 / r792
  (each split 180 + 180 between two bodies, recalled home and banked at the central altar ~48 rounds later),
  **won 1080-0 at r846** (was 720-720 lost on gold at r2000).

## Test maps
- `maps/obj/` (new, `node tools/mapgen/objmaps.mjs maps/obj 7` + seeds 11, 23 with `_s11` / `_s23`): 12 maps
  where the only gems are one fused elk + gem-cluster pack per side (4-6 elks + 4-6 gem clusters, 11,600-17,400
  HP), gold everywhere else; 48-64 tiles, 4-5 champions. Detector fires on all 12.

## Results (bench.py, both sides, non-release like the /tmp/ev references; 0 faults in every run)
Pools: objective pool = `maps/comp/{stampede,contest,monolith,elkring,rows}` + `maps/gold/*` + `maps/gold2/*`
(43 maps, 86 games); MA = maps where the final detector fires (`stampede`, `gold_monoE*`, `gold_monoEE*`,
`maps/obj/*`: 22 maps, 44 games).

| Bot | MA vs `_k1` | MA vs `_v6` | obj pool vs `_k1` | vs `_v6` | vs `_r2` | vs `_es2` |
|---|---|---|---|---|---|---|
| `_k1` (baseline) | (mirror) | 38/44 (86.4) | (mirror) | 88.4 | 89.5 | 53.5 |
| v1: team plan for every objective (monoliths too) | | | 51.2 | 88.4 | 84.9 | 48.8 |
| v2: team plan only when the solo plan fails, attackers first, objective safety | | | 57.0 | 88.4 | | |
| v3: v2 + objective safety only without enemies near | **30/44 (68.2)** | **41/44 (93.2)** | 54.7 | 84.9 | 88.4 | 58.1 |
| v3 + `obj_absorb` 0.9 (earlier team plan) | 26/44 (59.1) | 39/44 (88.6) | | | | |
| v3 + `obj_max_wait` 60 | 29/44 (65.9) | 40/44 (90.9) | | | | |
| **v4m = v3 + `obj_min_attackers` 2 (final)** | 30/44 (same code there) | 41/44 | 51.2 | **89.5** | | |

MA totals for the final logic (stampede + gold_monoE/EE from the v3 runs, maps/obj from v3/v4m), 44 games each:
**vs `_k1` 30/44 (68.2%), `_v6` 41/44 (93.2%, base 38/44), `_r2` 44/44 (base 39/44), `_es2` 34/44 (77.3%, base 28/44)**.
Stampede alone: 7/8 vs `_v6 _r2 _es2 _k1` (base 4/6 vs the first three). `maps/obj`: vs `_r2` 24/24 (base 19/24),
`_es2` 17/24 (15/24), `_v6` 22/24 (20/24), `_k1` 16/24; average winning round ~800 vs ~1,000.
- Per family (v3/v4m on MA): stampede vs `_k1` 2/2, `_v6` 1/2 (base 0/2; B side loses the early fights vs `_v6`
  with or without the change: deaths 41-46 base, 47-15 now), `_r2` 2/2, `_es2` 2/2; `gold_monoEE*` vs `_k1` 10/12,
  `_es2` 11/12 (base 7/12); `gold_monoE*` vs `_k1` 2/6 (the two fused groups are 8 tiles apart; traced: we were
  never "ready", the losses are fights); `maps/obj` vs `_v6` 22/24 (base 20/24, win round 804 vs 951), vs `_k1` 16/24.
- Monolith-only maps (v3, detector on there): vs `_v6` 31/38 (base 35), `_r2` 34/38 (33), `_es2` 20/38 (20),
  `_k1` 20/38: no gain, so the final detector leaves them alone (v4m vs `_v6` 35/38 = base).
- `contest`: unchanged (v3: 6/8 over `_r2 _v6 _k1 _es2` both sides; `obj_open_rounds` 150: 6/8). Not fixed here.
- Fuel identity: with the detector off the code paths are the same, but extra instructions shift fuel-dependent
  decisions (scoring floor, resumable init work). `gen16_98x99_V_c5` vs `_v6`: lost turns 20 vs `_k1`'s 19 (body 0's
  init continues one more round, r6; with the detector compiled out it is 19 again but the game still differs from
  r~280). Byte-identical games on normal maps are not reachable; the 56-map panel below measures the effect.
- 56-map panel (v4m, 112 games each): vs `_r2` **65.2%** (comp 67.6) vs `_k1` 67.0 (comp 70.6); vs `_v6` **86.6%**
  (comp 85.3) vs `_k1` 86.6 (comp 82.4). Games that differ from `_k1`'s: 14 / 13 of 112, on the objective map
  (stampede) and on the same fuel-sensitive maps both times (gen02, gen03, gen16 98x99, isl_56x56, lanes,
  swirl / lad_45x30): net -2 and 0 games, within noise.
- Lost turns, `gen16_98x99_V_c5` vs `_v6` (`tools/analysis/rollovers.mjs`): 20 vs `_k1` 19 (one extra init round
  for body 0 at r6; all in rounds 1-6).

## Reproduce
```bash
SRC=bots/_k1 tools/variant.sh _x_obj && (cd bots/_x_obj && patch -p1 < ../../experiments/wip/x_obj.patch) && cambc build _x_obj
python3 tools/bench.py _x_obj _v6 --maps 'maps/comp/stampede.map26a,maps/gold/gold_monoE*.map26a,maps/gold2/gold_monoE*.map26a,maps/obj/*.map26a' --jobs 2 --out /tmp/x
node tools/analysis/obj_audit.mjs /tmp/x/*/stampede_A.repl26a
```
A `LEGEND_TRACE` build prints `O mode=..` at init, `OB r=..` (objective state, team readiness, score) every 25 rounds
per body, `GW` (gather waits) and `SF` (safety lines on objective maps).
