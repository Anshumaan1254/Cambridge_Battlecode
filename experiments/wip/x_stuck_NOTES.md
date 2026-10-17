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
