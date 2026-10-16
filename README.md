# Cambridge Battlecode 2026a — `legend`

A complete, tested C++ bot for CAMBC 2026a, plus the tooling to verify engine rules, generate maps,
benchmark against sparring archetypes, tune by self-play and analyse ladder matches.

| Read this | For |
|---|---|
| [docs/STRATEGY.md](docs/STRATEGY.md) | how the game is won, hidden techniques, traps, the meta and its counters, the final strategy |
| [docs/ENGINE_FACTS.md](docs/ENGINE_FACTS.md) | every rule we verified on the real engine (with evidence) and fuel costs |
| [docs/HLD.md](docs/HLD.md) | architecture: modules, turn pipeline, data model, navigation, comms, fuel budget |
| [docs/FEEDBACK_LOOP.md](docs/FEEDBACK_LOOP.md) | how to play the top teams and paste results back so the bot can be re-tuned |
| [docs/LADDER_LOSSES.md](docs/LADDER_LOSSES.md) | round 1 of that loop: why we lost five ladder matches, the opponent's playbook, every fix and its measured effect |

## Results (local)

Round 2 (after the ladder-loss analysis, [docs/LADDER_LOSSES.md](docs/LADDER_LOSSES.md)); 219 maps × both
sides = 438 games per row unless noted. `_oppR` is a replica of the ladder opponent that beat us.

| Opponent | Win rate |
|---|---|
| round-1 `legend` (what lost on the ladder) | 73% (75% on official-style maps) |
| `_oppR`, ladder-opponent replica | 60% (round-1 `legend` only manages 37% against it) |
| `_opp2`, our logic with the opponent's draft | 68% |
| teleport-island maps vs round-1 `legend` (6 games) | 5 / 6 |
| unopposed, official-style maps | 1,000 gems in ~345 rounds (round 1: ~452) |

Round 1 (67 maps × both sides): 100% vs the starter bot and the deathball archetype, 85–88% vs rush,
aggressive and passive archetypes.

Matches are deterministic; release and debug builds give identical games.

## Ready-to-submit ZIP

[`submissions/legend.zip`](submissions/legend.zip) is `cambc bundle legend` output (the bot's `src/` only).
Upload it on the platform's Submissions page, or submit from the CLI with `cambc login && cambc submit legend`.
Rebuild it after changing the bot: `cambc bundle legend --output submissions/legend.zip` (delete the old file first).

## Quick start

```bash
pip install cambc
cambc init .            # adds the C++ SDK (sdk/, cmake/; git-ignored). Choose C++.
cambc build legend
cambc run legend starter-cpp --map gen10_62x66_R_c4 --view
python3 tools/bench.py legend starter-cpp          # all maps, both sides
tools/suite.sh legend                              # vs the sparring panel (build it first, below)
cambc submit legend                                # needs `cambc login`
```

Sparring opponents are generated, not committed:

```bash
tools/snapshot.sh _v1 7928cfe                      # first version
SRC=bots/_v1 tools/variant.sh _v1aggro fight_margin=0.85f enemy_half_penalty=0.f deny_bonus=1.2f steal_hp_frac=0.35f
SRC=bots/_v1 tools/variant.sh _v1passive fight_margin=99.f tribute_risky=1
tools/variant.sh _deathball style=1
tools/variant.sh _rush deathball_until=160 deny_bonus=2.f enemy_half_penalty=0.f fight_margin=0.9f steal_hp_frac=0.3f
tools/snapshot.sh _v4 25b39d0                      # previous release, for A/B
```

The second map pool (40 maps) is reproducible: `node tools/mapgen/gen.mjs maps 40 991 s2_`.
Official-style pools (3-wolf lines, elk groups with gem/gold clusters, gold columns; shaped by the ladder
maps): `node tools/mapgen/gen.mjs maps 30 4242 o_ official` and `node tools/mapgen/gen.mjs maps 120 7777 o2_ official`.
Ladder-opponent replica: `tools/variant.sh _oppR tribute_min=66 kite_min_ratio=0.f kite_max_kill=300.f --define "LEGEND_DRAFT 9,3,10,4,2"`.
Island maps (camps behind walls, teleport-crystal test): `node tools/mapgen/island.mjs maps`.
Real competition maps: `cambc maps pull` (needs network access to the platform).

## Layout

```
bots/legend/        the bot (C++20 → wasm). Tunables in src/params.h
bots/starter-cpp/   official starter bot (baseline)
bots/idle/          does nothing: measures unopposed farming pace
bots/probe-rules/   scripted rule probe for maps/zz_test (capture/tribute/recall timing, stuns, sleep, dash)
bots/probe-fuel/    fuel cost of SDK helpers
bots/probe-designs/ dumps every champion's stats, growth and abilities (range, modifier, cooldown)
matches/ladder1/    the five lost ladder summaries (raw + converted)
maps/               generated test maps (gen*), zz_test probe map
tools/bench.py      parallel A-vs-B benchmark with summary
tools/suite.sh      bench against the sparring panel
tools/tune.py       self-play parameter tuner
tools/variant.sh    build a parameter/define variant of legend
tools/snapshot.sh   freeze a past commit of legend as an opponent
tools/analyze_match.py  report from a match statistics JSON (local or ladder)
tools/raw_summary.py    convert a website-downloaded summary (numeric ids) into the named JSON
tools/stall_audit.py    list bench games where we stalled (low score, clock run out, no gold)
tools/mapgen/replica.mjs  approximate rebuilds of ladder maps from summary coordinates
tools/trace_stats.py    task-time breakdown from LEGEND_TRACE builds
tools/mapgen/       symmetric map generator using the engine's MapBuilder
```

## How it plays, in one paragraph

Draft the durable core **Varg → Tavi → Stellar → Ren → Ryth** (chosen by composition tournaments).
Every champion scores every camp group each turn by gems-and-gold per round of travel, waiting,
killing, capturing and *heal trips* (camps never heal, so strong groups are farmed over several trips),
claims its target in shared memory so allies spread out, banks gems on the way or at 34+, retreats
before camps or enemies can kill it and never recalls under fire. In fights it estimates a local
advantage from visible allies and enemies, fights back when already engaged unless clearly outmatched,
never tries to outrun same-speed melee, focus-fires a team-consistent target, stuns channellers, and
avoids diving the enemy spawn. It reads visible enemies' cooldowns, plays the scoreboard (safer when
ahead, riskier when the enemy is close to winning) and teleports into walled-off camp islands.
