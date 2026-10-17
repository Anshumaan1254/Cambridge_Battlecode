# Cambridge Battlecode 2026a — `legend`

A complete, tested C++ bot for CAMBC 2026a, plus the tooling to verify engine rules, generate maps,
benchmark against sparring archetypes, tune by self-play and analyse ladder matches.

| Read this | For |
|---|---|
| [AGENTS.md](AGENTS.md) | **handoff context for AI agents**: status, everything done and measured, setbacks, open work, next steps |
| [docs/STRATEGY.md](docs/STRATEGY.md) | how the game is won, hidden techniques, traps, the meta and its counters, the final strategy |
| [docs/ENGINE_FACTS.md](docs/ENGINE_FACTS.md) | every rule we verified on the real engine (with evidence) and fuel costs |
| [docs/HLD.md](docs/HLD.md) | architecture: modules, turn pipeline, data model, navigation, comms, fuel budget |
| [docs/FEEDBACK_LOOP.md](docs/FEEDBACK_LOOP.md) | how to play the top teams, decode the replays and re-tune |
| [docs/LEARNING.md](docs/LEARNING.md) | reward/punishment learning: offline evolution-strategies training and the in-match learners |

## Results (local, 39 maps × both sides = 78 games per row)

The 39 maps are the 12 real ladder maps extracted from our ladder replays (`maps/ladder/`) plus 27
generated ones. "Hunter" opponents are aggressive archetypes built on the current code with the drafts the
top ladder teams use; the old bot (v5, what was on the ladder) loses most games to them, as it did on
the ladder (17 of 20 scrims lost).

| Opponent | old bot (v5) | `legend` now |
|---|---|---|
| starter bot (`bots/starter-cpp`) | 88% | **100%** |
| old bot v5 (`tools/snapshot.sh _base 6bb913e`) | — | **81%** |
| pack-opening hunter (`_hunt`) | 42% | **87%** |
| aggressive Cassi & Issac hunter (`_hunt2`) | 28% | **82%** |
| current code with a Stellar/C&I draft (`_devci`) | 14% | **55%** |
| unopposed: rounds to 1,000 gems | 574 | **500** |

What changed and why: [docs/STRATEGY.md](docs/STRATEGY.md) §1. How the bot learns:
[docs/LEARNING.md](docs/LEARNING.md).

## Ready-to-submit ZIP

[`submissions/legend.zip`](submissions/legend.zip) is `cambc bundle legend` output (the bot's `src/` only).
Upload it on the platform's Submissions page, or submit from the CLI with `cambc login && cambc submit legend`.
Rebuild it after changing the bot: `cambc bundle legend --output submissions/legend.zip` (delete the old file first).
Every recommended build, with its commit and measured results, is logged in
[`submissions/BUILDS.md`](submissions/BUILDS.md); previous zips are kept in `submissions/history/`.

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

Sparring opponents are generated, not committed. `tools/make_sparring.sh` rebuilds the whole current panel
(`_base`, `_v6`, `_r2`, `_hunt`, `_hunt2`, `_devci`) from commits, identical to the bots behind the result tables.
The individual recipes:

```bash
tools/snapshot.sh _base 6bb913e                    # old bot (v5), what was on the ladder on Oct 16
SRC=bots/legend tools/variant.sh _hunt learn_enabled=0 fight_margin=0.95f fight_back_margin=0.6f enemy_half_penalty=0.f \
    deny_bonus=1.5f steal_hp_frac=0.3f deathball_until=110 deficit_defend=99 deficit_escort=99 --define "LEGEND_DRAFT 8,4,3,0,9"
SRC=bots/legend tools/variant.sh _hunt2 learn_enabled=0 fight_margin=0.9f fight_back_margin=0.6f enemy_half_penalty=2.f \
    deny_bonus=1.2f steal_hp_frac=0.4f isolated_fight_adv=1.0f deficit_defend=99 deficit_escort=99 --define "LEGEND_DRAFT 3,2,9,0,4"
SRC=bots/legend tools/variant.sh _devci learn_enabled=0 --define "LEGEND_DRAFT 4,3,9,10,8"
tools/panel.sh legend 'maps/*.map26a,maps/ladder/*.map26a' _base _hunt _hunt2 _devci starter-cpp idle
```

The second map pool (40 maps) is reproducible: `node tools/mapgen/gen.mjs maps 40 991 s2_`.
Island maps (camps behind walls, teleport-crystal test): `node tools/mapgen/island.mjs maps`.
Real competition maps: `cambc maps pull` (needs network access to the platform).

### Train the bot yourself

`tools/rl/train_local.sh` trains the parameters on your own machine with one command. It sets up the SDK,
the sparring panel and a frozen copy of the bot, runs the evolution-strategies training, validates the result
on every map and packs it into `rl_results_<date>_<commit>.tar.gz` to send back. Linux and macOS (WSL on
Windows). A default run plays 864 games per generation and takes about 1 to 3 hours on 4 cores (less with more cores).

```bash
tools/rl/train_local.sh          # 16 generations; --gens, --jobs, --resume and --validate-only are described in the link
```

Steps, options, cost and how the results are used: [docs/LEARNING.md](docs/LEARNING.md#training-on-your-own-machine-toolsrltrain_localsh).

## Layout

```
bots/legend/        the bot (C++20 → wasm). Tunables in src/params.h
bots/starter-cpp/   official starter bot (baseline)
bots/idle/          does nothing: measures unopposed farming pace
bots/probe-rules/   scripted rule probe for maps/zz_test (capture/tribute/recall timing, stuns, sleep, dash)
bots/probe-fuel/    fuel cost of SDK helpers
maps/               generated test maps (gen*), zz_test probe map
maps/ladder/        12 real ladder maps rebuilt from replays (tools/replay/extract_map.mjs)
maps/comp/          6 official competition maps (SDK 2.1.6 map pool; the ones not already in maps/ladder)
tools/replay/       replay decoder, readable match report, map extractor, ASCII map view, map features
tools/rl/           offline RL: evolution-strategies trainer (es_train.py), search space, apply_params.py
tools/rl/train_local.sh  one-command training on your own machine (see docs/LEARNING.md, section 1)
tools/draft_tournament.py  composition round robins (forced drafts, same code) -> draft table
tools/draft_model.py       map-aware draft model from a tournament (nearest training maps) -> draft_table.h
tools/panel.sh      one summary line per sparring opponent
tools/bench.py      parallel A-vs-B benchmark with summary (comma-separated map globs)
tools/suite.sh      bench against the sparring panel
tools/tune.py       self-play parameter tuner
tools/variant.sh    build a parameter/define variant of legend
tools/make_sparring.sh  recreate the sparring panel from commits
tools/analysis/     item-value model, spell usage, decision-formula audit, bag/recall risk, route time use
experiments/patches/  unmerged prototypes as patches (economy, spells), see AGENTS.md
tools/snapshot.sh   freeze a past commit of legend as an opponent
tools/analyze_match.py  report from a match statistics JSON (local or ladder)
tools/trace_stats.py    task-time breakdown from LEGEND_TRACE builds
tools/mapgen/       symmetric map generator using the engine's MapBuilder
```

## How it plays, in one paragraph

Draft **Ren → Stellar → Cassi & Issac → Ryth → Varg** (Varg before Ryth on pack-heavy 4-champion maps),
the composition that won our 780-game tournament and the one the strongest ladder team uses. Every
champion scores every camp group by gems-and-gold per round of travel, kill time (Varg splash, area
spells, Ren retaliation), capture and heal trips, and claims it in shared memory; a second body joins
packs that are heavy for one. Recall is transport: recall while capturing (the reward lands with the
teleport), after banking far away, to shop, and bank via the altar next to spawn. In fights it counts
allies and their spells, fights back against chasers it cannot outrun, retreats early when alone, plays
defensively when outnumbered, never trades with enemies healing on their spawn, acts first through
dynamic `set_priority`, and converges on enemy tributes. A team stance bandit, a pain map and per-champion
fight calibration learn from rewards and punishments during each match; the parameters themselves are
trained offline by evolution strategies.
