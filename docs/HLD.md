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
  comms.*      8-byte shared-memory protocol (claims, help bit, one team alert)
  brain.*      decision pipeline and action execution for one champion
```

## Turn pipeline (one champion)

```mermaid
flowchart TD
  A[turn start] --> B{first turn?}
  B -- yes --> I[init: static map, camp groups, home/away fields, ally handles, kit]
  B -- no --> C
  I --> C[read self: one sdk_champion record + cooldowns + gems + gold]
  C --> D{dead?}
  D -- yes --> S0[shop while dead] --> Z
  D -- no --> P[perceive: vision masks, enemies/allies, raw group states, camp HP]
  P --> Q[build danger masks: enemy reach, awake camp range]
  Q --> R{channelling?}
  R -- yes --> RC[maybe cancel tribute vs lethal stunner] --> Z
  R -- no --> SH[shop on spawn / Tavi anywhere]
  SH --> SP[support spells: heal ally, self-shield] --> LK[altar locks]
  LK --> F{combat?}
  F -- fight / flee --> W
  F -- no --> SF{safety: low HP?}
  SF -- retreat --> W
  SF -- no --> T{tribute?}
  T -- yes --> W
  T -- no --> ST{shop trip?} -- yes --> W
  ST -- no --> AL{answer rally?} -- yes --> W
  AL -- no --> FM[farm: score groups, claim best, farm / capture / wait]
  FM --> W[ward, prebuild 1-2 fields with spare fuel]
  W --> Z[write claim + help bit; end turn]
```

Every decision step either uses the turn (returns true) or falls through, so the order is the priority:
**fight/flee > survive > bank > shop > help allies > farm**.

## Data model

| Structure | Lifetime | Contents |
|---|---|---|
| `World` (static) | built on turn 1 | walls mask (terrain ∪ altars ∪ enemy spawn), spawns, altars and their free neighbours, `home`/`away` fields, camp groups |
| `Group` | static + memory | handle, camps (type, tile, max HP, strength), tile mask, range-3 mask, gems/gold/respawn, our-half flag; memory: state (alive / reward / respawning), ready round, last-seen HP per camp, awake flag, last enemy sighting |
| `Enemy` | memory | lazy champion object (built on first sight), kit (from design), alive (global), last position/HP/strength/focus/gems, channel flags, seen round, death round |
| `Ally` | per turn | alive, visible position/HP |
| `Nav` | lazy cache | one `Field` per camp group (roots = its tiles) and per altar (roots = free neighbours) |
| `Island` | static | groups unreachable on foot, launch/landing tiles for a crystal, field to the launch tile |
| `Brain` | per champion | identity, kit, abilities, build order, current task/target, blacklist, last HP |

## Navigation

- **Reverse fields.** A field rooted at a target's tiles gives the walking distance to that target
  from anywhere. Distances for scoring are one lookup; stepping is "move to the neighbour with a lower
  value that no visible unit blocks".
- **Lazy, budgeted building.** At most 3 fields per turn and only while > 45k fuel remains; spare fuel
  at the end of a turn pre-builds fields for the nearest unmapped groups. Unbuilt targets use a
  Chebyshev × 1.25 estimate.
- **Soft avoidance.** Enemy reach and awake-camp range are avoid masks: a step through them is taken only
  if no other improving step exists.
- **Dash** when it saves ≥ 2 steps (walls cannot be crossed, holes can).
- **Fallback.** When visible units block every improving step, a dynamic `compute_to` search from the
  goal set routes around them (only with > 30k fuel left).
- **Group-field caveat.** Group fields are rooted at every spawn tile, dead camps included; when the
  field says "in range" but no live camp is, the bot closes the gap with a direct search.

## Shared memory protocol (8 bytes)

| Bytes | Content |
|---|---|
| 0–5 | one per body (index = position in the engine's ally list): bit 7 = needs help, bits 0–6 = claimed group id + 1 (0 = none) |
| 6–7 | team alert: bits 0–13 tile index `y·W + x`, bits 14–15 kind (1 danger, 2 rally, 3 opportunity) |

Writes land immediately, so allies acting later in the same round see them. Readers remember when an
alert value first appeared and treat it as fresh for a few rounds.

## Draft memory (1,024 bytes)

Currently a 4-byte header (`0xB7`, version, team size, flags). Champions recompute everything on their
200k first turn, so draft memory is reserved for future opening routes.

## Fuel budget (100×100 worst case, per champion turn)

| Phase | Typical | Notes |
|---|---|---|
| first turn init | ~170k of 200k | two full fields, camp groups, ally handles |
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
