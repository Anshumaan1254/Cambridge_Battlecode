# Cambridge Battlecode 2026a — `legend`

A complete, tested C++ bot for CAMBC 2026a, plus the tooling to verify engine rules, generate maps,
benchmark against sparring archetypes, tune by self-play and analyse ladder matches.

| Read this | For |
|---|---|
| [AGENTS.md](AGENTS.md) | **handoff context for AI agents**: status, everything done and measured, setbacks, open work, next steps |
| [docs/strategy_v2/STRATEGY_V2.md](docs/strategy_v2/STRATEGY_V2.md) | **the new strategy (18 Oct)**: why we lose to the top 3 teams, the plan, the rules we miss, the implementation spec, ML/clustering, tests |
| [docs/STRATEGY.md](docs/STRATEGY.md) | how the game is won, hidden techniques, traps, the meta and its counters, the final strategy |
| [docs/ENGINE_FACTS.md](docs/ENGINE_FACTS.md) | every rule we verified on the real engine (with evidence) and fuel costs |
| [docs/HLD.md](docs/HLD.md) | architecture: modules, turn pipeline, data model, navigation, comms, fuel budget |
| [docs/FEEDBACK_LOOP.md](docs/FEEDBACK_LOOP.md) | how to play the top teams, decode the replays and re-tune |
| [docs/LEARNING.md](docs/LEARNING.md) | reward/punishment learning: offline evolution-strategies training and the in-match learners |

## Current build: `legend_m12` (session 7R, Oct 18): ready for the ladder

`legend_m12` plays `legend_m10`'s proven game everywhere, and on contest-type maps (gems only in lone monoliths) it opens as one group until
round 200 and wards the bushes. `legend_m11` warded bushes on every map: that beat our own older builds but lost to the top-team proxies (and,
per the user, on the top ladder); `legend_m12` keeps the warding only where it wins.

| Official 17 maps x 2 sides vs | `legend_m12` | `legend_m10` | `legend_m11` |
|---|---|---|---|
| Mite proxy (#2 team) | **85.3%** | 82.4% | 76.5% |
| ifish proxy (#1 team) | **79.4%** | 79.4% | 70.6% |
| `_px9` (ladder-calibrated) | 76.5% | 76.5% | 79.4% |
| sneaky-bush proxy | **67.6%** | 61.8% | 67.6% |
| `_fA` (pressure) | **88.2%** | 82.4% | 76.5% |
| contest pool, 68 games, vs `legend_m8` / Mite / sneaky | **88.2 / 95.6 / 97.1** | 50 / 60 / 38 (CT4/CT34 cells) | 88.2 / 95.6 / 97.1 |

Head-to-head vs `legend_m8` 52.3% (official 52.9%), vs `legend_m10` 51.1% (52.9%). Full numbers: `submissions/BUILDS.md`.

## Previous build: `legend_m11` (session 7R, Oct 18): ready for the ladder

`legend_m11` = `legend_m10` (= `legend_m8`'s play) + **bush warding** (a ward inside a bush reveals champions hiding there; we now ward a bush
tile within 2 when one is in reach, as the sneaky-bush ladder team does with every ward) + **a grouped opening on contest-type maps** (the bodies
farm together until round 200 instead of arriving one by one at the centre fight we lost in every ladder contest game).

| Opponent | `legend_m11` |
|---|---|
| `legend_m8` (previous best), 88 distinct games / official 34 | **52.3% / 67.6%** (deaths 593-712) |
| contest pool (68 games) vs `legend_m8` / Mite proxy / sneaky-bush proxy | **88.2% / 95.6% / 97.1%** (old play vs the sneaky proxy: 38.2%) |
| held-out maps (100 games, warding alone) vs Mite / `_px9` proxies | 87.0% / 74.0% (`legend_m10`: 79.0% / 66.0%) |

Previous: `legend_m10` (`submissions/history/legend_m10_20261018.zip`). Full numbers: `submissions/BUILDS.md`.

## Previous build: `legend_m10` (session 11): `legend_m8`'s play, ready for the ladder check

`submissions/legend.zip` = `legend_m10`. It plays exactly as `legend_m8` (the results table below applies: it takes the two top
teams' per-map draft choices where they beat ours and Mite's stampede plan). The 17 ideas from the repository's default branch
(`claude/lucid-pasteur-2jiojv`, the Oct 16 "round-2" bot) are in the code behind `mi_*` switches, all off: switched on together
(`legend_m9`, shipped briefly at the user's request) they lost to every sparring opponent (Mite proxy 63.6% vs 76.1%, ifish proxy
51.1% vs 69.3%, `_px9` 65.9% vs 78.4%). Per-idea numbers and what stays off: AGENTS.md §S11. Ladder feedback decides the next step.

## Results of `legend_m8` (session 10, Oct 18; 44 distinct maps × both sides = 88 games per row)

`legend_m8` = `legend_m7` + what the two top teams do against each other (13 games of Intercontinental Fish vs Mite,
`experiments/interwin_oct18/`): both draft from a fixed per-map table, and where their choice beat ours in our own brain we
take it: Ryth instead of Varg on rushbait-v2 and interlock, Cassi & Issac, Stellar, Varg on expanse, and on stampede Mite's
all-caster draft (Prism, Stellar, Cassi & Issac, Ryth, Tavi) clearing the 6-elk objective from distance 4 (the ring plan),
as Mite did to beat ifish 1080-0 and 1008-0. Everywhere else the bot is unchanged. Pace 503.8 rounds (`legend_m7` 520.9;
stampede 471/479 instead of 704/765). On those four maps it wins 44 of 48 games against six opponents (`legend_m7`: 26).
Sparring proxies of the two teams (their per-map drafts and builds, Mite's stampede plan) are `_mite` and `_ifish`.

| Opponent | `legend_m8` | deaths (ours-theirs) | `legend_m7` on the same games |
|---|---|---|---|
| `legend_m7` (previous ship) | **53.4%** (55.9); held-out maps 48.0% (the change does not act there: 85% of games identical) | 641-653 | - |
| `_mite` (Mite proxy) | **76.1%** (82.4) | 588-806 | 75.0% (73.5) |
| `_ifish` (ifish proxy) | **69.3%** (79.4) | 638-649 | 65.9% (67.6) |
| `_px9` ladder-calibrated proxy | **78.4%** (76.5) | 589-682 | 73.9% (67.6) |
| `_fA` pressure archetype | **73.9%** (82.4) | 687-920 | 70.5% (73.5) |
| `legend_m6` | **68.2%** (79.4) | 584-725 | 63.8% (70.6) |
| `legend_st` | **83.0%** (91.2) | 491-899 | 78.4% (82.4) |

### Options measured in session 10 and kept for future updates (not in `legend_m8`)

Every option below was A/B tested against the previous bot (`legend_m8`) and against the sparring panel; none was a better
trade, so they stay off. Code: `experiments/wip/x_s10_tests.patch` (switches on top of `legend_m8`'s sources).

| Option | How it works | Result vs `legend_m8` (88 distinct games / official 34) | Why kept off |
|---|---|---|---|
| **Counter-pick draft** (`last_pick`, `last_pick_size`) | Picks are simultaneous per round, but `bc::draft::current_draft(team::enemy)` returns the enemy's completed rounds, so our last pick sees their first 3-4 picks. Plan: commit the safe picks first (Ren, Stellar, Cassi & Issac: in every top-team draft), counter in the last round, fill by map features | 5th pick on 5-champion maps against Varg-first enemies (Mite, `_px9`) / Ren-first enemies (ifish, `_fA`): **Ryth (ours) 76% / 71%**, Marcella 59 / 65, Prism 58 / 63, Vendetta 58 / 62, Tavi 56 / 48. 4th pick on 4-champion maps: Varg (ours) 75 / 75, Ryth 58 / 58 | our current last picks are already the best answer to both enemy profiles; revisit when a new enemy profile appears (e.g. a different first pick on the ladder) |
| Shop when passing within 2-4 steps of spawn with 60-120 gold (`shop_near_dist`, `shop_near_gold`) | detour onto spawn to buy shards | 50.0 / 48.9 / 50.0 | changes 1-7 games in 88: walking home at 150 gold within 9 steps and recall-to-shop already cover it |
| Reward gold to the champion that uses it best (`gold_rank` 1: Stellar, Varg, Cassi, Issac, Ryth, Ren; 2: Stellar only) | when two of our bodies want one reward, the better gold user captures it instead of the lower index | 48.9 / 44.1; 47.7 / 47.1 | fewer deaths but slower farming |
| Camp-damage emblem first for Ren / Ryth (`dmg_first`) | Monster before the first health emblem (Stellar, Cassi, Issac and Varg already buy it first) | Ren 54.5 / 41.2; Ryth 53.4 / 52.9 but every third-party cell 2-6 points lower; both 46.6 / 41.2 | not a better trade |
| Hold for the spell before opening a fight (`strike_first=1`) | wait up to 2 rounds outside reach when a spell is about to come off cooldown | 59.1 / 61.8 head-to-head, but 50.0 over 188 games with the held-out maps, and lower against 6 of 7 other opponents (Mite proxy 69.3 vs 76.1) | beats only our own previous build |
| Mite's or ifish's whole per-map draft table | `mapdraft` 1 / 2 | no map better than ours beyond noise | `legend_m8` already takes their choices where they win |
| The default branch's 17 ideas (`mi_*` switches, `experiments/wip/x_mi.patch`; session 11) | the Oct 16 round-2 bot's fight record, learned enemy burst, lethal leave, danger slack, endgame banking, kiting, chip spells, flip guard, two-body cap, gem-only deny, relaxed rescoring, recall to shop, island bank, close-in, health emblem second | all on (`legend_m9`): 58.0 / 35.3 vs `legend_m8`; alone, the best are fight record 55.7 / 58.8, gem-only deny 54.5 / 61.8, flip guard 54.5 / 58.8, chip 54.5 / 50.0 | every one is worse than `legend_m8` against the outside opponents (fight record: `_px9` 65.9 vs 78.4; learned burst: `_px9` 64.8); all off in `legend_m10` |
| **Sneaky-bush team's per-map draft** (session 7R; their 17 ladder games vs `legend_m8`/`m10`, `experiments/sneaky_oct18/`) | `mapdraft` 4 = their table everywhere; `md_sneaky` = their choice on chosen official maps only (`experiments/wip/x_sn.patch`) | per-map screen on the 11 maps where they differ, 17 opponents x 2 sides: **256 vs 300 wins for ours**; worse on 8 maps (rows 20 vs 33, elkring 19 vs 27, monolith 19 vs 26). Only contest (+6) and collision (+3) gained, and both lost on side-swapped / transposed copies of those maps (contest 25 vs 36, collision 33 vs 37 over 54 games each) | our code plays Tavi, Willow and Vendetta worse than the champions they replace; the official-map gains were layout-specific. Their proxy `_snk` (their draft + Mite-style builds) stays in the sparring panel |
| ifish-style pressure on the enemy half (`enemy_half_penalty` 10 -> 6; `fight_margin` 1.30 -> 1.2) | farm and fight more on their side, take fights at a smaller margin | 51.1 / 47.1; 51.1 / 52.9 | penalty 6: Mite proxy 70.5 vs 76.1; margin 1.2: Mite proxy 77.3 (88.2 official) but ifish proxy 63.6 vs 69.3, `_px9` 70.5 vs 78.4 |

## Results of `legend_m7` (session 9, Oct 18; 44 distinct maps × both sides = 88 games per row)

`legend_m7` = `legend_m6` + two changes taken from 15 games of the top 3 teams playing **each other**
(`docs/strategy_v2/08_TOP3_VS_TOP3.md`): area spells (Stellar, Prism) are aimed so their radius catches enemies at
distance 5 (the top teams land 20-28% of their spell damage there, we landed 3-8%), and Cassi & Issac buy damage before
health (our Cassi had 70 focus at round 300, theirs 195-248). Pace 520.9 rounds (unopposed, 17 official maps).

| Opponent | `legend_m7` | deaths (ours-theirs) | `legend_m6` on the same games |
|---|---|---|---|
| `legend_m6` (previous ship) | **65.9%** (70.6); held-out maps 62.0% | 649-709 | - |
| `_px9` ladder-calibrated proxy | **73.9%** (67.6) | 602-675 | 58.0% (64.7) |
| `_f2q` proxy that casts its areas from 5 like the top teams | 53.4% (41.2) | 678-586 | 44.3% (41.2) |
| `_fA` pressure archetype | 70.5% (73.5) | 724-932 | 72.7% (82.4) |
| `legend_st` | 78.4% (82.4) | 520-916 | 73.9% (82.4) |

## Results of `legend_m6` (session 8, Oct 18 evening; 44 distinct maps × both sides = 88 games per row)

`legend_m6` = `legend_m5` + the top teams' targeting, learned from 60 ladder games of `legend_m5` against the top 3
(`docs/strategy_v2/07_LADDER_M5_18OCT.md`): hit the body we can hit this turn with the lowest health, take every kill the
team can finish this turn, stun the target first, and count an awake camp that is hitting an enemy as our damage. Tested
also against `_px9`, a sparring proxy calibrated on those ladder games (it beats `legend_m5` 64.7% on the official maps).

| Opponent | `legend_m6` | deaths (ours-theirs) | `legend_m5` on the same games |
|---|---|---|---|
| `legend_m5` (previous ship) | **52.3%** (61.8); held-out maps 59.0% | 580-710 | - |
| `_px9` ladder-calibrated proxy (official 17) | **64.7%** | 348-352 | 35.3% |
| `_fA` pressure archetype | 72.7% (82.4) | 561-1015 | 76.1% (79.4) |
| `legend_st` | 73.9% (82.4) | 465-909 | 73.9% (91.2) |
| `_eA` / `_eB` / `_eC` archetypes | 71.6% / 79.5% / 88.6% | | 68.2% / 77.3% / 87.5% |
| `legend_m4` | 53.4% (47.1) | 572-683 | 61.4% (58.8) |

## Results of `legend_m5` (session 8, Oct 18; 44 distinct maps × both sides = 88 games per row)

`legend_m5` = `legend_m4` + strategy-v2 fight execution (`experiments/wip/x_exec.patch`: hit what is in reach before
walking, melee swings before stepping away, keep fighting once committed) + the 16 parameters the A100 RL run moved
consistently (fight/flee thresholds, threat memory, bigger bags, defence of our half; `experiments/wip/rl_a100_m5a_args.txt`,
analysis in `experiments/rl_a100_20261018/`). Pace 523.4 rounds to 1000 gems (unopposed, 17 official maps). The 44 maps are
the 17 official ones plus the 27 generated ones (no `maps/ladder/` copies, which replay official maps). Official-map rates
in brackets. Every game is in `experiments/results/ledger/` (`python3 tools/ledger_sum.py --pool 'maps/*.map26a,maps/comp/*.map26a' _m5a`).

| Opponent | `legend_m5` | deaths (ours-theirs) | `legend_m4` on the same games |
|---|---|---|---|
| `legend_m4` (previous ship) | **61.4%** (58.8) | 565-673 | - |
| `_fA` pressure archetype on `legend_m4` code | **76.1%** (79.4) | 611-956 | 63.6% (64.7) |
| `legend_st` (on the ladder Oct 18: 1 win in 17) | 73.9% (91.2) | 526-849 | 73.9% (70.6) |
| `legend_rm` | 65.9% (76.5) | 521-862 | 63.6% (79.4) |
| `legend_m2` | 53.4% (55.9) | 603-595 | 56.8% (58.8) |
| `_eA` Ren-first pressure archetype | 68.2% (76.5) | 710-1109 | 70.5% (94.1) |
| `_eB` C&I-first farming archetype | 77.3% (94.1) | 534-976 | 79.5% (94.1) |
| `_eC` caster objective archetype | 87.5% (88.2) | 516-1043 | 81.8% (91.2) |

## Results of `legend_m4` (session 7, Oct 18; 56 maps × both sides = 112 games per row)

`legend_m4` = `legend_rm` + the `survive` agent's early retreat from outmatched groups (and from one stronger enemy;
Cassi & Issac leave earlier; Ren's retaliation counted) + the `farm` agent's farming fixes (no split rewards, the
first body on a reward keeps it, up to 3 bodies on a heavy group only when they arrive in time, Varg's splash position,
objective focus) + a fixed farm give-up clock (bodies no longer drop a group after 60 rounds on it). Unopposed it banks
1000 gems in 524.5 rounds on the 17 official maps (`legend_rm` 579). Official-map rates (`maps/comp/`, the real ladder
pool) in brackets. Every game is in `experiments/results/ledger/` (`python3 tools/ledger_sum.py _m4`).

| Opponent | `legend_m4` | deaths (ours-theirs) |
|---|---|---|
| `legend_m2` (previous ship) | **58.0%** (58.8) | 770-732 |
| `legend_rm` | **67.0%** (79.4) | 902-1187 |
| `legend_st` (on the ladder Oct 18: 1 win in 17) | **73.2%** (70.6) | 958-1114 |
| `_eA` Ren-first pressure archetype | 75.0% (94.1) | 840-1710 |
| `_eB` C&I-first farming archetype | 82.1% (94.1) | 675-1559 |
| `_eC` caster objective archetype | 83.9% (91.2) | 686-1319 |

## Results (local, 56 maps × both sides = 112 games per row; session 3, Oct 17)

The 56 maps are the 17 official ladder maps (`maps/comp/`, the real pool), 12 real ladder maps rebuilt from replays
(`maps/ladder/`) and 27 generated ones. Opponents are frozen past versions of this bot and aggressive archetypes with
the top ladder teams' drafts (`tools/make_sparring.sh`). Official-map-only rates in brackets.

| Opponent | `legend` (submitted on the ladder Oct 17, `_L0`) | `legend` now (`legend_c3`) |
|---|---|---|
| the Oct 17 ladder build (`_L0`) | — | **60.7%** (61.8) |
| `_r2` (commit 4a3920d) | 60.0% | **79.5%** (73.5) |
| `_v6` (first rewrite) | 73.3% | **91.1%** (97.1) |
| aggressive Stellar/C&I draft (`_devci`) | 76.7% | **90.2%** (91.2) |
| aggressive C&I hunter (`_hunt2`) | 95.6% | **99.1%** (100) |

These opponents are all our own code family. The user's audit of 40 real ladder games of `_L0` (5 wins) found we
collect half the gems of the top teams and die twice as often; the session-3 changes target exactly that (deaths
against `_devci` fell from 1,784 to 796 per 112 games). Build-by-build numbers: [`submissions/BUILDS.md`](submissions/BUILDS.md).

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
tools/ledger.py     resumable per-game results ledger (experiments/results/ledger): play only missing games, import cut-off runs
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
