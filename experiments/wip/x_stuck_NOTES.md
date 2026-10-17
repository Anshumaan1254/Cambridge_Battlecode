# x_stuck: champions stuck between walls (agent `stuck`, 2026-10-17)

Work in progress; updated as results come in. Bot copy: `bots/_x_stuck` (git-ignored). Patch: `experiments/wip/x_stuck.patch`.

## Tools

- `tools/analysis/stuck.mjs`: stuck detector on replay bundles (local `cambc run` zips or raw ladder replays).
  - `node tools/analysis/stuck.mjs [--team A|B|both] [--worst N] [--json out] [--quiet] FILES_OR_DIRS...`
  - bench.py naming: `NAME_B.repl26a` = our bot on team B. With a `LEGEND_TRACE` build it also reads the task and target.
  - An "eligible" round: alive, off its spawn, not channelling (recall, tribute, crystal, standing on a reward it
    captures), no enemy champion within 5 tiles (this round or last), no fight/flee task, no attack or targeted cast.
    Waiting next to a respawning group is counted apart.
  - Episodes over consecutive eligible rounds: `frozen` (2x2 box 6+ rounds, at most one move), `jiggle` (2x2 box,
    moving), `osc` (3x3 box 8+ rounds, moving most rounds), `noprog` (trace only: 10+ rounds, same task and target,
    moving, walking distance to the goal never below its start).
  - Also counts engine "Movement blocked" events and turn rollovers. Prints per map, per champion and the worst
    episodes with a 9x9 view (`#` wall, `o` hole, `"` bush, `A` altar, `T`/`t` target camp live/dead, `C`/`x` other
    camps, `a` ally, `e` enemy, `@` the body, `S`/`E` spawns).
- `tools/mapgen/stuck_maps.mjs`: 8 symmetric stress maps in `maps/stuck/` (1-tile corridors with camps standing in them,
  dead ends, walled pockets with 1-tile doors around camps and altars, combs of dead-end pockets, hole lines with
  single bridges, bushes in corridors, camps hugging walls). `node tools/mapgen/stuck_maps.mjs maps/stuck 8 7`.

## Session-2 rebase (from 14:00 UTC)

- Bot copy is now `bots/_x_stuck2` = current legend (maths + route merged, `dash_holes`, `finish_camp`,
  `capture_before_retreat`; frozen as `_f1`) + the fixes below. `x_stuck.patch` is cut against current `bots/legend/src`.
- Detector fixes after the rebase: it reads the bot's own group table from the route trace's `G` lines (the engine
  fuses touching groups, so map-file group ids were wrong on some maps: the old "walk-away" cause on `lad_50x65` was
  this artifact, the bodies were making progress); dash kits (Ren, Issac, Vendetta, Vesper) get hole-crossing walking
  distances; a flip needs 3+ switches back and forth (a single re-plan is not a flip).

## Root causes found (with evidence)

1. **Fuel starvation on big maps** (98x99 gen16, 100x100 official maps): scoring all groups took ~53k per turn and left
   ~35k; a target's field needs 45k to build and the dynamic-search fallback needs 30k, so bodies walked on per-turn
   searches and stood still whenever those were skipped. On `lanes` (90x30, ~40 groups mostly within 20 tiles) the
   near-group scoring alone took 70-85k after the maths merge, and turns spilled into the next round every other round.
2. **Goal next to a dead camp**: without the group field, `go_group`'s fallback goal was "within range of any group
   tile", dead camps included. A melee body next to a dead wolf, or a ranged one 3 tiles from it, counted as arrived
   while the live partner was out of reach: frozen 30-78 rounds (gen16: Ryth 78, Stellar 47, Ren 37; gen05/gen15/packs
   ranged bodies 48-66 rounds at walking distance 3-4).
3. **Hopeless danger-avoiding search**: inside a camp's or enemy's reach every neighbour is an avoid tile; the avoiding
   search could not succeed but still expanded the whole map (~30k fuel), then the plain search was skipped under 25k:
   Issac froze next to an awake camp, losing 560 -> 220 HP.
4. **Detours undone by the static field**: a camp or ally on the field's next step made the dynamic search step around
   it; on the next tile the static field (which ignores units) pointed straight back (A-B-A-B).
5. **Target flips**: switching to a group and back within a few rounds (scores swing with claims, enemy sightings,
   fields becoming ready).
6. Nothing catches a body that simply does not progress: the old give-up rule fires after `2*eta + 60` rounds.
- Not causes here: home-edge flip-flops (fixed in legend by the route patch's `home_edge_fix`), hop walks
  ("walk-away" was a detector artifact).

## Fixes (all in `params.h`, default on)

| Param | What |
|---|---|
| `stuck_live_goal` | farming a live group without its field: goal = tiles in range of live camps; the in-range direct search also counts unseen camps believed alive |
| `stuck_avoid_skip` | `step_to` skips the avoiding search when every neighbour is blocked or avoided |
| `target_field_fuel` 32000 | the current target's field (group or altar) is built from 32k fuel (others 45k) |
| `stuck_detour`, `detour_hold` 12 | after a unit forced a detour, keep the dynamic search until the field value drops below where it started |
| `stuck_reach` | an island group is BIG (not a straight-line estimate) from anywhere our spawn reaches |
| `score_near_floor` 38000, `score_far_floor` 55000 | scoring stops at these fuel levels (near / far groups); the start rotates every turn so every group is still scored every few turns |
| `flip_window` 12, `flip_margin` 1.5 | going back to a target left less than 12 rounds ago needs 1.5x the score (on top of hysteresis) |
| `unstick_rounds` 10, `unstick_blacklist` 30 | last resort: a farm/capture body that stays in a 3x3 box without attacking for 10 rounds drops that target for 30 rounds |
