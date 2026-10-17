# `legend` bot — high-level design

C++20 compiled to WASI wasm by `cambc build`. One binary runs as many isolated instances: one draft
instance per team, then one instance per champion body (Cassi and Issac are two bodies). Instances
share nothing except the team's 8-byte shared memory and the 1,024-byte draft memory.

```
bots/legend/src/
  main.cpp     loop: draft or turn, swallow every exception, always end_turn()
  draft.cpp    map analysis + champion scoring + pick (+ LEGEND_DRAFT override for experiments)
  params.h     every tunable constant (the tuner rewrites this file in variants)
  common.h     aliases, Field (cached distance field), Kit (abilities derived from engine designs)
  world.*      static map model + per-turn perception + memory (camp groups, enemies, allies)
  nav.*        lazy target-rooted distance fields, field stepping, dash, dynamic fallback search
  comms.*      8-byte shared-memory protocol (claims, team stance bits, one team alert)
  learn.*      in-match learning: team stance bandit, pain map, fight calibration (docs/LEARNING.md)
  brain.*      decision pipeline and action execution for one champion
```

## Turn pipeline (one champion)

```mermaid
flowchart TD
  A[turn start] --> B{first turn?}
  B -- yes --> I[init: static map, camp groups, home/away fields, ally handles, kit]
  B -- no --> C
  I --> C[read self: one sdk_champion record + cooldowns + gems + gold]
  C --> LU[learner team update: deaths both sides, banking rates]
  LU --> D{dead?}
  D -- yes --> S0[shop while dead] --> Z
  D -- no --> P[perceive: vision masks, enemies/allies, raw group states, camp HP]
  P --> L[learner tick: deaths, stance (body 0 broadcasts), pain; post enemy tributes]
  L --> Q[build danger masks: enemy reach, awake camp range]
  Q --> R{channelling?}
  R -- yes --> RC[cancel recall/tribute if a threat makes it pointless] --> R2{still channelling?}
  R2 -- yes --> Z
  R2 -- no --> SH
  R -- no --> SH[shop on spawn / Tavi anywhere]
  SH --> SP[support spells: heal ally, self-shield] --> LK[altar locks]
  LK --> ES{respawn escort: down 2+, wait on spawn?} -- yes --> W
  ES -- no --> F{combat?}
  F -- fight / flee --> W
  F -- no --> SF{safety: low HP?}
  SF -- retreat --> W
  SF -- no --> T{tribute? (contested-altar check, recall-bank via spawn)}
  T -- yes --> W
  T -- no --> HT{home trip: heal/shop/after bank (recall)?} -- yes --> W
  HT -- no --> ST{shop trip?} -- yes --> W
  ST -- no --> AL{answer rally / opportunity?} -- yes --> W
  AL -- no --> FM[farm: score groups (+islands, crystal hops), claim best, farm / capture (recall-overlap) / wait]
  FM --> W[ward, set priority for next round, hop scan + prebuild fields with spare fuel]
  W --> Z[write claim; end turn]
```

Every decision step either uses the turn (returns true) or falls through, so the order is the priority:
**fight/flee > survive > bank > heal/shop > help allies > farm**.

## Data model

| Structure | Lifetime | Contents |
|---|---|---|
| `World` (static) | built on turn 1 | walls mask (terrain ∪ altars ∪ enemy spawn), spawns, altars and their free neighbours, `home`/`away` fields, camp groups |
| `Group` | static + memory | handle, camps (type, tile, max HP, strength), tile mask, range-3 mask, gems/gold/respawn, our-half flag; memory: state (alive / reward / respawning), ready round, last-seen HP per camp, awake flag, last enemy sighting |
| `Enemy` | memory | lazy champion object (built on first sight), kit (from design), alive (global), last position/HP/strength/focus/gems, channel flags, seen round, death round |
| `Ally` | per turn | alive, visible position/HP/strength/focus, kit, last death round |
| `Hop` | lazy | crystal shortcut to a group: launch/land tiles, cost from spawn |
| `Learner` | match | stance values and plays, window counters, pain map (6x6 cells), fight bias |
| `Nav` | lazy cache | one `Field` per camp group (roots = its tiles) and per altar (roots = free neighbours) |
| `Island` | static | groups unreachable on foot, launch/landing tiles for a crystal, field to the launch tile |
| `Brain` | per champion | identity, kit, abilities, build order, current task/target, progress clock, blacklist, last HP, calibration sample |
| `Learner` | per instance | team deaths, banking rates, calibration sums, per-enemy burst |

## Navigation

- **Reverse fields.** A field rooted at a target's tiles gives the walking distance to that target
  from anywhere. Distances for scoring are one lookup; stepping is "move to the neighbour with a lower
  value that no visible unit blocks".
- **Lazy, budgeted building.** At most 3 fields per turn and only while > 45k fuel remains; spare fuel
  at the end of a turn pre-builds fields for the nearest unmapped groups. Unbuilt targets use a
  Chebyshev × 1.25 estimate.
- **Avoidance with detours.** Enemy reach and awake-camp range are avoid masks. When every shortest
  step enters one, a search treating it as walls looks for a detour at most 6 steps longer; only
  without one do we step in. Enemy spells with one round of cooldown left count as ready, and spells
  usable after a step reach 5.
- **Dash** when it saves ≥ 2 steps (walls cannot be crossed, holes can).
- **Fallback.** When visible units block every improving step, a dynamic `compute_to` search from the
  goal set routes around them (only with > 30k fuel left).
- **Group-field caveat.** Group fields are rooted at every spawn tile, dead camps included; when the
  field says "in range" but no live camp is, the bot closes the gap with a direct search.

## Shared memory protocol (8 bytes)

| Bytes | Content |
|---|---|
| 0–5 | one per body (index = position in the engine's ally list): bits 0–6 = claimed group id + 1 (0 = none); bit 7 of bytes 0 and 1 = team stance (written only by body 0; everyone else preserves bit 7) |
| 6–7 | team alert: bits 0–13 tile index `y·W + x`, bits 14–15 kind (1 danger, 2 rally, 3 opportunity) |

Writes land immediately, so allies acting later in the same round see them. Readers remember when an
alert value first appeared and treat it as fresh for a few rounds.

## Draft memory (1,024 bytes)

A 4-byte header (`0xB7`, version 2, team size, chosen composition index). Champions recompute
everything on their 200k first turn, so draft memory is reserved for future opening routes.

## Fuel budget (100×100 worst case, per champion turn)

| Phase | Typical | Notes |
|---|---|---|
| first turn init | ~170k of 200k | two full fields, camp groups, ally handles; on maps with 20+ groups it overruns and the engine resumes it next round (one round lost) |
| perception | 3–4k | masks + raw group states + nearby camp HP |
| danger masks | ~1.5k | |
| decision + movement | 10–45k | field builds dominate; capped |
| safety margins | ≥ 20k left | below 22k, movement falls back to `move_towards` |

## Failure handling

- Every engine action is wrapped in `try/catch`; a failed action never ends the turn early.
- The main loop catches everything and still calls `end_turn()`.
- Hidden-unit collisions (`move` returns false) try the next best step.
- Draft analysis failure → fixed fallback list, so a pick is always submitted.
- Release mode (the platform) and debug mode produce identical games in our tests.

## Test and tuning infrastructure

| Tool | Purpose |
|---|---|
| `tools/mapgen/gen.mjs` | symmetric, connectivity-checked map generator built on the engine's own `MapBuilder` (wasm) |
| `tools/bench.py A B` | every map, both sides, in parallel; win rate, gems, deaths, kills, gold, average win round |
| `tools/suite.sh` | bench against the sparring panel (starter, v1, aggressive, passive, deathball, idle) |
| `tools/variant.sh` / `snapshot.sh` | build parameter variants / freeze a past commit as an opponent |
| `tools/tune.py` | self-play coordinate-descent tuner with a regression panel |
| `tools/analyze_match.py` | pasteable report from any statistics JSON (local or ladder) |
| `tools/trace_stats.py` | task-time breakdown from `LEGEND_TRACE` builds |
| `bots/probe-rules`, `bots/probe-fuel` | re-verify engine rules and fuel costs after patches |
