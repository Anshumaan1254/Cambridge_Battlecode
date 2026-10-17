# AGENTS.md: handoff context for AI agents (and humans)

Read this first. It records what has been done on this bot, what was measured, what failed, what is
running or unfinished, and what to do next, so a new agent can continue without the original chat.

- Last updated: 2026-10-17, ~10:15 UTC (session 2). Branch `claude/laughing-curie-3rq6hu` (do not open a PR unless the user asks).
- Competition: Cambridge Battlecode 2026a (CAMBC), 12 Oct to 18 Nov 2026. C++ bot compiled to wasm.
- The submitted bot cannot be changed after submission and keeps nothing between matches. All "learning"
  is either offline (training parameters before submission) or in-match (adapting inside one game).

---

## 0. Status right now (read this if nothing else)

| Item | State |
|---|---|
| Bot | `bots/legend/src` (C++). Ready-to-upload bundle: `submissions/legend.zip` (rebuild after every change, section 3) |
| Current legend | = `_r2` (fuel fixes, review fixes, reworked learner) + exploration off + refreshed draft values + **the economy and spells patches** (`experiments/patches/x_econ.patch`, `x_spell.patch`, merged Oct 17). Build log with every submitted zip: `submissions/BUILDS.md`; older zips in `submissions/history/` |
| Strength (45-map panel, 90 games per cell) | economy + spells on `_r2`: panel mean **85.2%** (vs `_r2` 77.6%), 57.8% head-to-head vs `_r2`. Promoted legend vs `_v6` (18 maps): 26/36, 0 faults, 2.6 lost turns per game. Full numbers in section 5 |
| Engine | **cambc 2.2.5** since session 2 (was 2.2.2). Legend re-measured on it: unchanged (§0b) |
| Tiebreakers (round 2000) | banked gems, then **gold earned**, then kills, then team B (read from the engine binary, §2) |
| In flight | see **§0b**: five subagents (gold/tiebreak economy, stuck navigation, team coordination, maths + route review, ML fight model). RL training now runs on the user's machine with `tools/rl/train_local.sh` |
| Next | Merge the prototypes that win one by one (panel after each), rebuild the zip, update README/STRATEGY tables, commit, push; apply the user's ES results when they arrive (§0b) |

---

## 0b. Work in progress (session 2, from 2026-10-17 09:45 UTC)

Everything below is **unfinished or unmerged** unless marked done. Patches in `experiments/wip/` are snapshots of local
bot copies (the copies are git-ignored); they may still change in the agent's copy.

**Session 2 started in a new container**: everything local from session 1 was gone (its ES run, all `bots/_*` copies,
`tune_out/`). Session 1's ES run had finished generations 0 and 1 only (mean-policy reward +0.831 and +0.864); nothing was
saved. Recreated in session 2:
- `pip install cambc` gave **2.2.5** (was 2.2.2); `cambc init` moved `cambc.toml` to 2.2.5. The wasm toolchain had to be
  fetched by hand again (TLS, §3 gotchas): wasi-sdk-33 into `/root/.cache/cambc/wasi-sdk-33`, cmake 3.31.8, ninja 1.12.1.
- `tools/make_sparring.sh` rebuilt the panel. **`bots/_L0`** = frozen copy of legend at 25bed8d: baseline of every A/B in
  session 2.
- Legend re-measured on engine 2.2.5 (45 maps, 90 games per cell): results match session 1, so the engine change does
  not affect us.

| Bot | `_r2` | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | Mean of the last five |
|---|---|---|---|---|---|---|---|
| legend (= `_L0`) on engine 2.2.5 | 60.0 | 73.3 | 91.1 | 95.6 | 76.7 | 88.9 | **85.1** |

**User requests in session 2** (also in §1, item 6):
- continue the work in the md files, using Opus subagents for major tasks, Sonnet for medium, Haiku for documentation;
- RL training moves to the user's machine: give an exact script; the user sends back the weights and every output;
- maps with only gold and gems only in very hard camps: the bot must understand them and favour gold, as the
  tiebreakers say;
- our champions lack coordination: a proper team strategy;
- champions sometimes get stuck between walls, which loses games;
- keep this file updated at every step, in the same style.

**Agents in flight** (rules every parallel agent follows: `experiments/wip/AGENT_RULES.md`):

| Agent (model) | Task | Bot copies | Deliverables |
|---|---|---|---|
| `mr` (Opus) | review, fix and panel the maths and route prototypes from session 1; combine the winners | `_x_math`, `_x_route`, `_x_mr` | refreshed `x_math.patch`, `x_route.patch`; `x_mr.patch`, `x_mr_NOTES.md` |
| `gold` (Opus) | gem-scarce maps: test maps, scarcity detection, tiebreak-aware economy (gold earned, gem lead, monolith, endgame) | `_x_gold` | `x_gold.patch`, `x_gold_NOTES.md`, `maps/gold/`, map generator |
| `stuck` (Opus) | champions stuck between walls: detector over replays, stress maps, root causes, nav fix | `_x_stuck` | `x_stuck.patch`, `x_stuck_NOTES.md`, `tools/analysis/stuck.mjs`, `maps/stuck/` |
| `coord` (Opus) | team coordination: measure the failures first (deaths alone, allies not joining, split damage), then fix the costly ones (focus fire, engage protocol, buddies, sectors) | `_x_coord` | `x_coord.patch`, `x_coord_NOTES.md`, `tools/analysis/coord_audit.mjs` |
| `ml` (Sonnet) | ML fight model: logging build, data, formula vs logistic / tree / boosted trees / MLP; export only if it clearly wins | `_x_ml`, `_x_ml_log` | `x_ml_NOTES.md` (+ `x_ml.patch` only if it wins) |
| `docs` (Haiku) | document `tools/rl/train_local.sh` in `docs/LEARNING.md` and `README.md` | none | docs |

**Merge plan** (coordinator): `mr` first, then `stuck`, `gold`, `coord`, `ml`. Each on top of the previous merge, a
45-map panel after each, kept only if it wins (§7.1 rule), then a `submissions/BUILDS.md` row and a new zip.

**Offline RL now runs on the user's machine** (session 2): `tools/rl/train_local.sh` does everything in one command
(prerequisites, SDK, `cambc maps pull`, sparring panel + `_self` = frozen copy of the bot being trained, build and smoke
test, ES training, validation panel of the learned parameters, results archive). Tested here end to end with a tiny run.
- The user sends back `rl_results_<date>_<commit>.tar.gz` (git-ignored): `meta.txt` (commit, cambc version, CPUs, args),
  `console.txt`, `log.txt`, `history.json`, `best_params.json`, `validation.txt` (learned parameters vs every opponent,
  every map, both sides) and any official maps the repo does not have yet (`cambc maps pull` on their machine works;
  it is blocked here).
- When it arrives: extract it into a scratch directory, read `validation.txt` and `meta.txt` (which commit it trained),
  apply `best_params.json` to a copy (`tools/variant.sh _es_user $(python3 -c "import json;print(' '.join(f'{k}={v}' for k,v in json.load(open('best_params.json')).items()))")`),
  panel it against the current legend, and bake it in only if it wins. Add new official maps to `maps/comp/`.
- Changes for it: `tools/variant.sh` and `es_train.py`'s variant builder no longer use GNU `sed -i` (macOS); the search
  space (`tools/rl/space.json`) dropped `ucb_c` and `prior_pull` (27 params): both are measured harmful and sit at their
  lower bound, where ES noise can only push them up.
- Other tooling changes: `tools/bench.py` rebuilds a bot only when its sources are newer than its wasm (parallel agents
  share the sparring bots); `tools/panel.sh` takes `PANEL_JOBS`.

**If you are a new agent and these runs are gone** (new machine or container restart: running processes,
`bots/_*` and `tune_out/` are local only), continue like this:

1. Set up: `pip install cambc && cambc init .` (choose C++); if the toolchain download fails TLS, fetch it by hand (above).
   Then `tools/make_sparring.sh` and freeze the baseline: `mkdir -p bots/_L0 && cp -r bots/legend/src bots/_L0/ && cp bots/legend/.gitignore bots/_L0/`.
2. Rebuild each prototype from its patch on top of the current legend:
   `for p in x_math x_route x_gold x_stuck x_coord; do mkdir -p bots/_$p && cp -r bots/legend/src bots/_$p/ && cp bots/legend/.gitignore bots/_$p/ && (cd bots/_$p && patch -p1 --no-backup-if-mismatch < ../../experiments/wip/$p.patch) && cambc build _$p; done`
   (session 2 patches are cut against legend at 25bed8d; read each `x_*_NOTES.md` for its state).
3. Panel each prototype (90 games per opponent):
   `tools/panel.sh _x_math 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' _L0 _r2 _v6 _hunt _hunt2 _devci _base`.
   Compare with the engine-2.2.5 legend row above (mean 85.1).
4. Merge winners onto `bots/legend` one at a time (merge plan above), panel after each.
5. For each new build: rebuild the zip (`rm -f submissions/legend.zip && cambc bundle legend --output submissions/legend.zip`),
   check that it holds only `src/*.cpp|*.h` (no `.orig` files), archive it in `submissions/history/`, add a row to
   `submissions/BUILDS.md`, update §0 and §5 here, commit and push.

### Findings from session 1's prototypes (still valid; the `mr` agent is reviewing and panelling them)

**Decision maths: findings and changes** (`_x_math`; tools `xm_audit.mjs`, `xm_paired.mjs`, `xm_fe_time.mjs`, `xm_fe_taken.mjs`, `xm_fr_split.mjs`, `xm_econ.mjs`)
- The bot does decide with explicit formulas; checked against 120 traced games:
  - camp score = value / time = long-run gem rate;
  - DPS model accurate solo (actual/predicted 0.85-1.12);
  - `combat()` advantage already behaves like Lanchester's square law;
  - tribute thresholds, recall safety and capture-recall timing hold up (512 of 518 capture-recalls got the reward).
- Measurably wrong:
  - **damage taken over a kill** was over-predicted 1.7-2.3x: it was assumed constant, but camps die one by one, and allies at the group tank;
  - **travel** was 2.2-2.5 rounds too long for ranged and dash champions;
  - the heal-trip HP budget did not match `safety()`'s retreat line;
  - **gold had no end-of-game discount**: 20% of gold is earned after a team passes 800 gems, and ~485 gold per team is never spent.
- Fixes, all switchable:
  - travel to attack range, with a dash pace;
  - sequential kill integral, with exposure 0.25 for a lone ranged champion and allies counted as tanks;
  - reserve aligned with `safety()`;
  - gold value scaled down over the last 500 rounds.
- Prediction errors on the same episodes: travel 3.08 → 1.74 rounds, damage 281 → 167 HP, episode time 10.5 → 6.8 rounds.
- Smoke tests (24 ladder games each): vs `_v6` 18-6 (`_r2` 17-7), vs `_r2` 15-9, vs `_hunt2` 23-1 (same as `_r2`). 13-28% fewer deaths.
- Weak spot: fight-free farming races are 3-7% slower; it lost 3 of 4 of them to `_r2`.
- The fight estimator over-states advantage x1.6-2.0, growing with body count, but the fights it picks are net positive in every bin. It was left unchanged, as was the double-counted spell DPS in `combat()` (it affects both sides; fixing it rescales every threshold).

**Routes: findings and changes** (`_x_route`; tools `route_stats.mjs`, `route_audit.mjs`, `bank_audit.mjs`, `bank_first.mjs`)
- **Optimal path, answered with data:**
  - camp ordering (two-step lookahead / TSP) would save only 0.2-0.7% of walking: 83% of captures end in a recall-while-capturing, so trips are star-shaped (spawn → camp → teleport home);
  - camp supply is not the bottleneck: ~440 gem-value of untouched live groups on our half;
  - target swaps between bodies are limited by the 8-byte shared memory.
- **Real waste:**
  - banking walks: 14.6% of body-rounds unopposed, 32% on the 30x80 map;
  - farm↔home flip-flops at the spawn edge: 15.3% of turns → 1.1%;
  - walks abandoned before arrival: ~37% of camp-walk steps.
- **Changes:**
  - `home_edge_fix` (home trips also from 1-2 steps away);
  - `claim_helpers` (a yielding ally's damage still counts in the kill plan);
  - **bank first** (when a capture fills the bag and the nearest altar plus a recall home beats banking from spawn, bank there, then recall);
  - a trip-aware bank threshold (+1 gem per step beyond 12, capped at 2x);
  - "bank before a risky fight" ignores enemies standing on their own spawn.
- **Results:**
  - unopposed pace 622 → 523 rounds to 1000 (−16%);
  - bank walking −30-35%, gems per bank 40 → 44;
  - head-to-head vs `_r2` 25-11 (69%);
  - vs `_v6` side A only, 13/18: not yet confirmed neutral.
- Rejected:
  - claim seniority: fewer target swaps, but slower pace;
  - lookahead ordering, as above;
  - camp scoring that includes the bank cost: not built.

**ML fight model** (`_x_ml`): session 1 built the pipeline (`tools/ml/`) but not the model; the `ml` agent continues it in
session 2. The plan:
- log the `combat()` features and the decision taken;
- label the outcome from replays (death within 12 rounds, kill within 12 rounds);
- compare the current formula, logistic regression, a decision tree, gradient-boosted trees (XGBoost if pip allows, else sklearn) and a tiny MLP, by AUC with a game-level split;
- export to C++ (< 3k fuel per call) only if the model clearly beats the formula, then A/B it.

The maths audit above already found the formula is biased but its chosen fights are net positive, so a learned model has to beat a reasonable baseline.

**All analysis tools** (`tools/analysis/`, `tools/ml/`):

| Tool | Measures |
|---|---|
| `item_value.py` | item value per champion (log utility over farming, kills, survival, heal trips), greedy build order |
| `spell_usage.mjs` (+ `spell_decode.mjs`) | per champion and ability slot: ready turns, casts, wasted cooldowns, stun timing, resets, shields, wards and locks |
| `xm_audit.mjs`, `xm_paired.mjs`, `xm_fe_time.mjs`, `xm_fe_taken.mjs`, `xm_fr_split.mjs` | predicted vs actual (kill time, damage, trips, fight advantage) from `XM_TRACE` builds |
| `xm_econ.mjs` | bags lost at death, bag-size histograms, recall reliability |
| `route_stats.mjs`, `route_audit.mjs` | time shares, walking per gem, oscillation, duplicate walks, ordering regret, coverage (`LEGEND_TRACE` builds) |
| `bank_audit.mjs`, `bank_first.mjs` | banking time split; capture-recall versus bank-first |
| `tools/ml/benchsum.py` | summary of bench.py output directories |
| `tools/ml/run_games.py` | runs a chosen list of single-side games (one at a time), bench.py naming |
| `tools/ml/parse_logs.mjs` | turns `XML_LOG` fight logs (one line per `combat()` evaluation) into a labelled CSV: did this body die / did an enemy within 6 die in the next 12 rounds |
| `tools/ml/train.py` | compares fight-outcome predictors (the formula vs learned models) with game-level cross-validation |
| `tools/ml/explore.py` | off-policy (contextual-bandit) analysis of `XML_EXPLORE` data: the logging bot multiplies its fight advantage by exp(u), u ~ U(-0.7, 0.7), to measure what bolder or more careful fighting would earn: epsilon-style exploration done offline, not in submitted games |

---

## 1. What the user asked for (all requests in this chat)

1. Learn the repo and keep looking for improvements. "We are winning, but when losing we lose by a little,
   rarely by a big margin." Problems the user named:
   - we do not use **recall** and lose too much time walking;
   - the **draft** does not pick strategic champions: analyse each map, then pick for it;
   - in fights there is **no backup**: everyone goes out, we all die and are locked out for a long time.
2. Make the learning better: **reinforcement learning** with a **reward/punishment** system that learns
   from mistakes, keeping in mind that the submitted bot cannot be updated.
3. Use the strategy plan (`CAMBC_2026a_Strategy_Plan_1.md`, uploaded by the user, not in the repo), other
   people's views, and the uploaded match results (4 zip match groups, 24 ladder losses). Analyse our moves
   and the enemies' moves, find out why we lost, and fix it. Search the internet for better strategies.
4. (Second message) **Use gold**: shards, emblems, "upgrade abilities". **Check the maths** in decisions.
   Use **decision trees, XGBoost, RL soft updates, epsilon-greedy, content-based filtering**, deep learning
   or RL concepts **only if they make the bot better**. Choose **optimal paths**, and work out **when to
   optimally use powers** and items.
5. (Third message) Write this context file and push it, top priority.
6. (Session 2, Oct 17) Continue the work in the md files with subagents: **Opus** for major tasks, **Sonnet** for medium
   ones, **Haiku** for documentation. **RL training moves to the user's machine**: give an exact script; the user returns
   the weights and all outputs. Some maps have **only gold, with gems only in very hard camps**: the bot must recognise
   them and favour gold, as the **tiebreakers** say (the attachment did not arrive; the rules were read from the engine,
   §2). Our champions **lack coordination**: build a proper team strategy. Champions sometimes **get stuck between
   walls**, which loses games. Keep this file updated at every step, in the same style.

---

## 2. Game and engine essentials (full evidence in `docs/ENGINE_FACTS.md`)

- First team to 1000 banked gems wins (round limit 2000). **Tiebreakers at round 2000** (strings in the engine binary
  `/usr/local/bin/cambc`, cambc 2.2.5): more banked gems; tied on gems → more **gold earned** (match statistics
  `earnedGold`); tied on gems and gold → more kills; tied on all three → team B wins. Lexicographic: one banked gem
  beats any amount of gold. Kill gold is 50, assists and passive income are 0.
- Champions farm camp groups (wolf, elk, gem and
  gold clusters, monolith), capture rewards (gems + gold), carry gems and **tribute** (bank) them at an
  altar. A tribute takes max(1, ceil(gems/10)) turns; damage does not cancel it, a stun or death does.
- **Recall**: 5 turn ends; *any* damage cancels it. Health is restored only after a turn ends on spawn.
  Recall while capturing: step on the reward tile in round T, start the recall at T+1 or later, and the
  reward lands with the teleport.
- **Respawn** takes 60 rounds. Cassi & Issac are one pick but two bodies, and they die together.
- **Turn order**: camps act first; team A leads odd rounds, team B even rounds. Within a team, higher
  `set_priority` acts first (it applies from the next round).
- **Fuel**: 100k per turn (200k on a champion's first turn, 1M on the first draft turn). A turn that runs out
  **continues in the next round, so that champion loses a whole round** (counted as "Turn rollover" in
  replays). Host calls (distance-field get, `bitboard::is_set`) cost ~50-60 fuel each; a full distance
  field costs 13-19k. **Bitboard exports are bit-packed** (LSB first); distance-field exports are uint16 per tile.
- **Shared memory**: 8 bytes for the whole team (bytes 0-5 hold claims plus 2 stance bits, bytes 6-7 one
  team alert). Draft memory is 1024 bytes.
- **Items**:
  - Every shard costs 30 gold and adds 1 point of its stat (growth per point: health +100, or +71/+75/+95
    for some champions; strength +5 (+4); focus +10 (Cassi +15)). Five shards of one family combine
    automatically into an emblem.
  - Emblem bonuses: Monster +10% camp damage, Jungle −30% camp damage taken, Durability −10% damage taken,
    Treasure +20% gold, Home faster recall. These passives do not stack within a family.
  - Power emblem = 6 points of one stat. Bruiser emblem = 5 points + 1 of each other stat.
  - Shopping only on spawn or while dead (Tavi anywhere). Consumables: teleport crystal (hops up to
    Chebyshev 3 over walls and holes), altar lock, ward.
  - **No item upgrades abilities directly**: focus is the ability stat (spell = modifier × focus, Ren's
    retaliation = 0.2 × focus per hit, Varg's shield = 2.5 × focus). Cooldowns are fixed at 8 rounds.
- Matches are **deterministic** for fixed bots and map: never repeat a game; variance comes only from
  more maps and opponents.

---

## 3. Repo map and how to run things

```bash
pip install cambc && cambc init .              # SDK into sdk/ (git-ignored); choose C++
tools/make_sparring.sh                         # recreate the git-ignored sparring panel (bots/_*), verified identical
cambc build legend
python3 tools/bench.py legend _v6 --maps 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a'   # 90 games, ~40 s on 4 CPUs
tools/panel.sh legend 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' _v6 _hunt _hunt2 _devci _base
rm -f submissions/legend.zip && cambc bundle legend --output submissions/legend.zip                # submission bundle
```

| Path | What |
|---|---|
| `bots/legend/src/` | the bot: `brain.*` decisions, `world.*` perception/memory, `nav.*` distance fields and stepping, `comms.*` shared memory, `learn.*` in-match learners, `draft.cpp` composition choice, `params.h` every tunable |
| `bots/_*` | **git-ignored** local bots: sparring opponents, prototypes, variants. Recreate the panel with `tools/make_sparring.sh` |
| `experiments/patches/` | the finished prototypes as patches against `_r2` (apply on legend: `cd bots/X && patch -p1 --no-backup-if-mismatch < ../../experiments/patches/x_econ.patch`) |
| `maps/*.map26a` | 27 generated maps. `maps/ladder/`: 12 real ladder maps rebuilt from replays. `maps/comp/`: 6 official maps (SDK 2.1.6 pool, from the public Tarot Club repo; the other 3 official maps duplicate ladder ones) |
| `tools/bench.py`, `tools/panel.sh` | A-vs-B on every map, both sides, in parallel; one summary line per opponent |
| `tools/variant.sh`, `tools/snapshot.sh` | build a param/define variant (`SRC=bots/X tools/variant.sh NAME key=val --define "M v"`); freeze a past commit as a bot |
| `tools/replay/decode.mjs` | replay decoder using the engine's own wasm: per-round state + events (`{rollovers: true}` keeps fuel rollovers); `report.py`, `extract_map.mjs`, `mapinfo.mjs`, `mapfeatures.mjs` |
| `tools/rl/es_train.py` | offline RL: evolution strategies over `tools/rl/space.json` (27 params since session 2), shaped reward, uses bots/legend's params.h as the start |
| `tools/rl/train_local.sh` | one-command ES training for the user's own machine: setup, training, validation panel, results archive (§0b) |
| `tools/draft_tournament.py`, `tools/draft_model.py` | composition round robin (per-map wins and gem margins); nearest-map draft model with leave-one-map-out validation (`--vs` scores against a chosen field) |
| `tools/analysis/` | item-value model (`item_value.py`), spell usage (`spell_usage.mjs`), decision-formula audit (`xm_audit.mjs`), bag/recall risk (`xm_econ.mjs`), route time use (`route_stats.mjs`) |
| `docs/` | `STRATEGY.md`, `ENGINE_FACTS.md`, `HLD.md` (architecture), `LEARNING.md` (RL), `FEEDBACK_LOOP.md` (ladder replay loop) |

**Sparring panel** (all from `tools/make_sparring.sh`):
- `_base`: old v5, what was on the ladder.
- `_v6`: commit 58c2fe4.
- `_r2`: commit 4a3920d.
- `_hunt`, `_hunt2`, `_devci`: aggressive archetypes on the 58c2fe4 code, using the drafts of the top ladder teams.
- Also available: `starter-cpp`, and `idle` (never moves; used to measure unopposed pace).
- `_r1` (review fixes without the fuel fixes) was a local intermediate and cannot be recreated exactly.

**Gotchas that cost us time:**
- **Never use `pkill -f` / `pgrep -f` / `killall` with patterns**: they matched and killed the agent's own shell
  several times. To wait for a background job, wait on that script's own PID
  (`ps -eo pid,args | grep "[s]cratch/x.sh" | grep -v "bash -c"`). The shell that launched it lingers, so
  pattern-waiting deadlocked once.
- Launch long jobs from a script file with `nohup script > log 2>&1 &`; container restarts kill them
  (the ES run died this way).
- **Noise**: one 90-game result has a standard deviation of about ±5 points, so judge changes on the
  average over 5-6 opponents, and treat gaps under ~4 points as noise. Identical code differing only in fuel
  use can move a result by ~3 points.
- `cambc` toolchain download fails TLS in **every new cloud container** (sessions 1 and 2): fetch wasi-sdk-33 (extract
  `wasi-sdk-33.0-x86_64-linux` and rename it to `wasi-sdk-33`), cmake-3.31.8-linux-x86_64 and ninja-1.12.1 (`ninja-linux.zip`
  into `ninja-1.12.1-linux-x86_64/`) by hand into `/root/.cache/cambc/` with `curl --cacert /root/.ccr/ca-bundle.crt`.
- The platform API (`2026a.battlecode.co.uk`) is blocked from the cloud container; the user must download
  ladder replays and match JSON themselves.
- Building and running other teams' bot code (the Tarot Club clones of the top teams) was blocked by the
  permission classifier as untrusted code; only their map files were used. The user can allow it if wanted.
- With 4 CPUs a Workflow runs only 2 agents at a time, and the account's session limit has cut workflows
  twice. Keep workflows small, and save findings to files as you go.

---

## 4. What has been implemented (chronological, with evidence)

**Commit 58c2fe4: first rewrite, built from 24 decoded ladder losses** (we had lost 17 of 20 scrims).
- **Farming of big packs.**
  - The camp score now counts Varg's splash, area spells, Ren's retaliation, allies, up to 5 heal trips,
    and lets a second body join heavy packs.
  - The 3-wolf-pack ladder map went from losing 132-1012 to the starter bot to winning.
- **Recall loop.**
  - Recall while capturing (the reward lands with the teleport), after banking far away, to shop, and to
    bank at the altar next to spawn.
  - Never recall when an enemy seen in the last 2 rounds is within 7 tiles; cancel when a threat closes in.
  - Unopposed pace improved from 574 to 500 rounds.
- **Fights (`combat()`).**
  - Advantage = (our HP / their DPS) / (their HP / our DPS), counting allies' spells.
  - Escape feasibility: fight back against chasers we cannot outrun; stun the chaser; melee champions
    swing after their step.
  - Never trade with enemies healing on their spawn.
  - Backup counting; early retreat when isolated; a higher fight bar with half the team dead.
  - Respawn escort: when down 2+ bodies, wait on spawn for the next ally instead of walking out alone.
- **Turn order:** dynamic `set_priority` (fighters act first).
- **Draft:**
  - Ren, Stellar, Cassi & Issac, Ryth, Varg ("meta"), chosen from a 780-game composition tournament;
  - the same draft the strongest ladder team uses.
- **Builds.**
  - Durability/Jungle health, then Monster, Treasure, Power.
  - Won 65% head-to-head against the old builds.
- **Crystal shortcuts** over hole mazes, and island camps.
- **Learning** (`docs/LEARNING.md`):
  - offline: ES trainer;
  - in-match: team stance bandit (SPREAD / GROUPED / PUSH), pain map of where we died, per-champion
    fight calibration.

**Commit 4a3920d: lost turns, review fixes, learner rework.**
- **Fuel.**
  - On the 98x99, 48-group map the team lost **566 of ~2,700 champion turns** to fuel rollovers; now **12**
    (just the two heavy opening turns per body).
  - Causes fixed:
    - emblem checks that recounted the build for every group, every turn;
    - all groups scored every turn: the loop now scores the current and nearby groups first, under a
      fuel floor;
    - the hop scan read bit-packed exports as bytes and checked fuel only per row: it now reads bits,
      resumes per tile, stops after a pause, and is skipped when no hop can pay;
    - splash clusters recomputed every turn: now only when a camp dies or respawns;
    - the pain map decayed every turn: now lazily, every 8 rounds.
- **Review fixes:**
  - the respawn escort now waits: allies that died while this body was dead get their real death round;
  - a dead group's reward is captured before any home or shop trip;
  - when the altar is unsafe, banking via recall and the spawn altar is tried before giving up;
  - a cancelled tribute is not restarted in the same turn;
  - a nearer claimer captures a reward even when a lower-index ally also claims it;
  - DANGER alerts no longer overwrite RALLY or OPPORTUNITY;
  - champions hold on spawn instead of bouncing on and off it;
  - the spawn-heal bonus counts only for fights on spawn;
  - capture-recall starts in the right round;
  - failed hops are dropped.
- **Ablation (leave-one-out, 78 games × 4 opponents):** priority alternation (double turns) and the
  "shielded camp" retreat rule each cost 7-17 points and are off by default. Rest-on-spawn is worth up to 17
  points; it stays, with sticky tributes and the claim tie-break.
- **Stance learner:**
  - rewards in gem units: kill +25, death −45, banks smoothed over two windows;
  - soft (EMA) update;
  - UCB exploration and a pull back to priors (both now off, see below);
  - death locations only from fresh sightings.
- **Draft model hook:**
  - `draft.cpp` reads an optional `draft_table.h` produced by `tools/draft_model.py`;
  - without it (the current state) the draft is unchanged.

**Commit aece821: draft values** from an 8-draft × 45-map tournament (2,520 games, section 5). At team size 4,
Varg as the 4th pick now beats Ryth.

**Commit 564785f: stance exploration off** (measured −2 points; section 5).

**Analysis tools** (commits 5cf8001 to e751b1b): `tools/analysis/*` (see section 3).

---

## 5. Measured results (latest first)

All on the 45-map pool (27 generated + 12 ladder + 6 official), both sides: 90 games per cell, win rate %.

**Round 3 (stance-learner A/B on `_r2`):**

| Bot | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | `_r1` | Mean |
|---|---|---|---|---|---|---|---|
| `_r2` (learner, UCB 0.3) | 74.4 | 88.9 | 94.4 | 63.3 | 87.8 | 56.7 | 77.6 |
| learner off | 78.9 | 82.2 | 93.3 | 66.7 | 93.3 | 62.2 | 79.4 |
| learner, no exploration (**now default**) | 77.8 | 90.0 | 96.7 | 66.7 | 86.7 | 62.2 | **80.0** |

**Round 2 (review fixes and retreat threshold):**

| Bot | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | Mean |
|---|---|---|---|---|---|---|
| `_m1` (before the review fixes) | 48.9 | 87.8 | 72.2 | 45.6 | 83.3 | 67.6 |
| `_c1` (`_m1` + the 2 harmful toggles off) | 54.4 | 83.3 | 85.6 | 50.0 | 82.2 | 71.1 |
| `_r1` (+ review fixes) | 60.0 | 86.7 | 90.0 | 64.4 | 83.3 | 76.9 |
| `_r1` + `retreat_hp` 0.40 | 64.4 | 82.2 | 88.9 | 67.8 | 83.3 | 77.3 |
| `_r1` + `retreat_hp` 0.50 | 67.8 | 85.6 | 84.4 | 65.6 | 84.4 | 77.6 (noise; left to ES, range up to 0.55) |
| `_r1` without the claim tie-break | 65.6 | 87.8 | 86.7 | 60.0 | 81.1 | 76.2 (noise; kept) |

**Draft tournament** (8 drafts, same code, mean win rate vs the field):

| Draft | Mean | Worst |
|---|---|---|
| `metaV` (Ren, Stellar, C&I, Varg, Ryth) | 0.590 | 0.489 |
| `meta` (Ren, Stellar, C&I, Ryth, Varg) | 0.581 | 0.500 |
| `vci` (Vendetta, C&I, Varg, Stellar, Ren) | 0.565 | 0.500 |
| `civr`, `ryt`, `tav` | 0.49-0.52 | |
| `ven2` (Tarot's Vendetta/C&I/Varg/Tavi/Vesper) | 0.421 | |
| `wil` (Willow-based) | 0.321 | |

- The **nearest-map draft model** (content-based: "maps like this one") beat the team-size choice by +2 to
  +4 points in leave-one-map-out validation against the whole field.
- Against only the strong drafts it gave no gain. With ~6 games per map per draft, per-map differences are
  noise: `meta` and `metaV` are identical at team size 5, yet scored 0.500 vs 0.467.
- So it is **not shipped**; the hook and the tool are ready for when more real maps and replays exist.

**Round 4 (prototypes vs the panel; same learner setting as `_r2`):**

| Bot | vs `_r2` | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | `_r1` | Mean (excluding `_r2`) |
|---|---|---|---|---|---|---|---|---|
| `_r2` (round 3) | — | 74.4 | 88.9 | 94.4 | 63.3 | 87.8 | 56.7 | 77.6 |
| `_x_econ` (economy patch) | **60.0** | 74.4 | 90.0 | 92.2 | 73.3 | 83.3 | 61.1 | **79.1** |
| `_x_spell` (spells patch) | **54.4** | 75.6 | 88.9 | 90.0 | 81.1 | 91.1 | 63.3 | **81.7** |
| `_x_combo` (econ + spells, **now legend**) | **57.8** | 77.8 | 94.4 | 98.9 | 75.6 | 90.0 | 74.4 | **85.2** (vs `_x_econ` 46.7%, vs `_x_spell` 55.6% head-to-head) |

**Earlier (39-map pool, the first rewrite):**
- The old bot (v5) won 88% vs the starter bot, 42% vs `_hunt`, 28% vs `_hunt2` and 14% vs `_devci`.
- The rewrite won 100%, 87%, 82% and 55% respectively.
- Unopposed pace: 574 → 500 rounds.

---

## 6. Analyses and findings (what the data said)

**Why we lost on the ladder** (24 decoded replays; `docs/STRATEGY.md` §1):
- Death cascades: 12.2 deaths per match vs their 4.0. Half came with no ally within 6 tiles; many came
  while fleeing same-speed chasers.
- Big packs went unfarmed.
- They recall as transport (at 58-73% HP, 22-49 times per game); we recalled only in emergencies.
- They act first in fights (`set_priority`).
- Every top team drafts Cassi & Issac.
- Spawns that touch caused a stalemate.
- Our HP builds were too low (they reach 1800-2000 HP).
- One opponent (group 8694af79) is the ladder team "ifish" (draft Ren, Stellar, C&I, Ryth, Varg).

**Web research** (public repos; the best source was Tarot Club, github.com/FHL-08/Tarot-Club-Cambc2026,
cloned read-only to `/home/user/fhl-08/tarot-club-cambc2026` in this container):
- **Top teams' habits:** ~220 casts per game; recall at ~0.46 HP and never under threat; camp parking
  (wait on a cleared camp until it respawns); spend all gold; a grouped opening, then split the map into
  sectors; a disable-chain to focus fire.
- **What failed for Tarot:**
  - pulling allies into a teammate's fight cost 17 to 401 gem margin;
  - forcing the whole team onto one camp won only 3 of 18 games;
  - a full kill-race rewrite won 0 of 18.
- **Deep RL** at Lux-AI scale cannot fit in 100k fuel. Feasible instead: SPSA/ES parameter tuning, and
  tiny MLP gates trained to imitate replays.

**Economy** (`_x_econ` agent; `tools/analysis/item_value.py`):
- Gold is not wasted: 91-97% is spent, and gold held away from spawn is small (12-45 per champion).
- What was wrong:
  - **no Bruiser** emblems (7 stat points vs Power's 6, at the same 150 gold);
  - the rich champions' build lists **ran out** (Ren once had 948 gold unspent);
  - Cassi & Issac are gold-poor (~580 gold per game) yet bought damage first, while dying together
    6 times a game;
  - Treasure came too late.
- The prototype fixes all four, and counts Monster's +10% in the kill-time estimate:
  - its own tests: 21/24 vs `_v6` (`_r2`: 17/24), 20% fewer deaths, +15% gold;
  - full panel so far: 60% head-to-head vs `_r2`;
  - its weak spot is pure farming races, ~20 rounds slower.

**Abilities** (`_x_spell` agent; `tools/analysis/spell_usage.mjs`):
- Spells are ready on 66-84% of turns but used on only 21-40%, mostly because there is no target in range
  or the champion is walking (damage spells cannot be cast in a turn that walks).
- Three fixable losses:
  1. Ryth's area stun was never cast from range: 5.6 stuns per game on champions despite ~36 fight turns
     with it ready.
  2. Fleeing champions never stunned a chaser that would hit them anyway.
  3. Spells on camps were held whenever an enemy was within 9 tiles, but a fight followed within the
     cooldown only 13% of the time at 7-9 tiles (51-63% at 5-6).
- Already fine: attack resets, Varg's shield timing, stun timing relative to the target's turn, wards,
  altar locks, crystals.
- Prototype: 55.6% vs `_r2` over 36 games, 13% fewer deaths, Ryth's champion stuns ×3; full panel pending.

**Maths of decisions** (`docs/STRATEGY.md` §3-4):
- The decisions are explicit models:
  - camp value per round = (gems + 0.22 × gold) / (travel + wait + kill time + 6 capture rounds + heal trips);
  - kill time from real DPS (splash, spells, retaliation);
  - damage taken from the nearest-champion rule and emblems;
  - fight advantage in the Lanchester style (HP over enemy DPS, counting allies and stuns).
- A calibration audit against replays (predicted vs actual kill time, damage, fight outcomes) was being
  built when the session limit hit (`tools/analysis/xm_audit.mjs`); it is being re-run now.

**Learning (RL)**:
- In-match stance learner: neutral (±2 points); exploration hurts (a game has only ~25 decision windows).
- Offline ES: the main learning path. Each generation samples 8 maps, so its "mean reward" moves with the
  map sample; judge it only on a fixed panel after training.

---

## 7. Unimplemented / open work (by priority)

1. **Done: the economy and spells prototypes are merged** into `bots/legend` and `bots/_dev` (panel mean
   85.2% vs 77.6%). Keep the rule for later prototypes: merge a change only if the 5-6-opponent mean improves
   by more than ~3 points, or the gem margin improves clearly with no regression.
2. **Maths, route and ML prototypes**: a Workflow is building them now (`bots/_x_math`, `bots/_x_route`,
   `bots/_x_ml`, local only). The workflow script is
   `.../workflows/scripts/legend-decision-upgrade-*.js` in the session dir; if it is lost, the brief for each
   is below.
   - *Maths*: log each formula's predictions (kill time, damage taken, trips, fight advantage) and compare
     with the replay outcome; refit the coefficients; fix unit errors; consider Lanchester N² for
     multi-body fights.
   - *Route*: measure time shares (walk, farm, capture, wait, bank, home); then two-step lookahead (pick a
     group by its value plus the best follow-up), team assignment of groups to avoid duplicate walks, wait
     on camps that respawn soon, danger-weighted paths. Must stay under the fuel budget.
   - *ML*:
     - log the `combat()` features and the decision taken;
     - label outcomes from replays (death within 12 rounds, kill within 12 rounds);
     - compare the current formula with logistic regression, a decision tree, gradient-boosted trees
       (XGBoost if installable, or sklearn) and a tiny MLP, by AUC with a game-level split;
     - export the winner to C++ (if/else trees or constexpr weights, < 3k fuel per call) only if it
       clearly wins.
3. **ES on the final code** (session 2: the user runs it on their machine with `tools/rl/train_local.sh`, §0b). In a
   container the equivalent is:
   ```bash
   python3 tools/rl/es_train.py --space tools/rl/space.json --opponents _v6,_hunt,_hunt2,_devci,_r2 \
     --maps 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' --gens 10 --pop 4 --maps-per-gen 8 --jobs 4
   ```
   Then apply `best_params.json` to a copy (§0b), validate on the panel, and keep the result only if it wins.
   ES reads its starting values from `bots/legend/src/params.h`.
4. **Ship**: sync `bots/_dev/src` into `bots/legend/src`; rebuild `submissions/legend.zip`; update the
   results tables in `README.md` and `docs/STRATEGY.md`; commit and push.
5. **Ideas not yet tried** (from research and analysis):
   - camp parking (hold a cleared camp until it respawns);
   - a grouped opening then map sectors (note: our earlier "deathball" opening lost);
   - a shared focus-fire target in comms (shared memory is full: it needs a redesign);
   - altar locks on enemy-side altars;
   - capture-overlap tribute (start a 1-tick tribute next to an altar as a capture lands);
   - the Home emblem for recall-heavy play;
   - sending captures to gold-poor champions;
   - imitation gates trained on top-team replays.
6. **Feedback loop with the real ladder**: the user downloads new ladder replays, then decode them, extract
   new maps into `maps/ladder/`, re-run the draft tournament and ES (`docs/FEEDBACK_LOOP.md`). Our sparring
   bots are archetypes of our own code, so real teams will differ.

---

## 8. Setbacks and things that did not work (do not repeat blindly)

| Idea | Result | Where |
|---|---|---|
| Priority alternation for double turns (+/-1000) | −8 to −17 points head-to-head | `prio_alternate = 0` |
| Retreat counting only "unshielded" camps | −10 points (champions stayed out at lower HP) | `safety_v2 = 0` |
| Pair plans (wait for a partner on heavy packs) | 24 rounds slower unopposed, no win-rate gain | `pair_plans = 0` |
| Early deathball opening | lost to spread farming | `deathball_until = 0` |
| First untuned online learners | −10 points until the combat model was fixed | — |
| UCB exploration in the stance bandit | −2 points over 540 games | `ucb_c = 0` |
| Nearest-map draft model | no gain against strong drafts (noise) | no table shipped |
| Treasure-first builds for Ren/Stellar | worse than Treasure second (19/24 vs 21/24) | `rich_treasure_first = 0` in the econ patch |
| Hop scan v1 | read bit-packed exports as bytes and overran fuel (bodies lost 13-14 of their first 40 turns) | fixed in 4a3920d |
| Process handling | `pkill -f` killed our shell; a pattern-based wait deadlocked; container restarts killed ES at generation 4; session limits cut two workflows | see the gotchas in §3 |

---

## 9. What we are thinking right now (next actions, in order)

Session 2 (10:15 UTC):
1. Wait for the five agents (§0b). Merge in order `mr` → `stuck` → `gold` → `coord` → `ml`, each on the previous
   merge, panel after each (45 maps, 90 games per opponent, plus the gold and stuck test maps), keep only winners.
2. Gem-scarce maps: the gold mode must leave normal maps untouched (flag off on all 45 maps) and win the tiebreak on
   `maps/gold/`; if the user sends the current official pool (from `train_local.sh`), test on the real gold maps too.
3. Rebuild the zip, `submissions/BUILDS.md` row, README/STRATEGY tables (Haiku agent), commit, push.
4. When the user's ES archive arrives: validate `best_params.json` on the merged build and bake it in only if it wins.
   Best is for the user to train the merged build: tell them when it is pushed.

---

## 10. Conventions

- Commit messages end with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01HwDbgTPDFYPU6J7emgx9Ev
  ```
  Push with `git push -u origin claude/laughing-curie-3rq6hu`. No PR unless asked.
- Code style:
  - tabs;
  - comments explain *why*, with the measured evidence;
  - every tunable lives in `params.h` with a comment;
  - every engine action is wrapped in try/catch;
  - every new loop is checked for fuel cost (count rollovers with `decode(..., {rollovers: true})` on
    `maps/gen16_98x99_V_c5.map26a`).
- Every behaviour change gets a switch in `params.h` and an A/B on the panel before it becomes the default.
  Record the result in the param's comment and in `docs/STRATEGY.md` §7.
- Work on copies (`bots/_dev`, `bots/_x_*`) and benchmark frozen copies; never rebuild a bot a running
  benchmark uses.
