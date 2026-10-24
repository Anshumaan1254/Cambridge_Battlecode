You are taking over the map-analysis work for our Cambridge Battlecode 2026a (CAMBC) bot. The C++ bot is compiled to wasm. The repository
is Cambridge_Battlecode, single branch `main`.

YOUR JOB: carry out the plan in `MAPAnalysis.md` exactly as written, from where it stopped (its section 7). The plan was agreed with
me. Do not change it:
- add no steps, drop none, reorder none, and swap none of its methods for your own ideas;
- keep its decisions as they are (the exact-match table with model fallback, the four per-map plans, the full-cycle economy model,
  banking checked per team, and the tiebreak cases).

Inside each step:
- You may fix bugs and build the tooling needed to carry the step out.
- Where a detail is not specified, pick the option closest to the plan's text and write the decision into `MAPAnalysis.md` section 7.
- If something cannot be done, write down why in section 7 and move to the next item. Do not invent a replacement.

==================================================================================================================================
1. READ FIRST, IN THIS ORDER
==================================================================================================================================
1. `MAPAnalysis.md`: the whole file. It is the source of truth for this work:
   - section 1: my requests, and my two chat corrections, quoted;
   - section 2: background;
   - section 3: measured facts: the patch timeline, cambc 3.0.5 = 3.0.4 in play, the engine constant / camp / champion tables, and how
     map files store camps;
   - section 4: the 40 official maps;
   - section 5: the plan, steps 1-9;
   - section 6: the files added;
   - section 7: where we left off.
2. The top bullet of `AGENTS.md`, which points back to `MAPAnalysis.md`. The rest of `AGENTS.md` is long history: search it, do not read
   it all.
3. `god2_session17/README.md`: the latest ladder study (Oct 23-24).
   - The shipped bot lost 13-227 to the top three on the 40 maps.
   - The gap is farming: ~420 vs 1,050-1,090 camp gems a game, 73% of it in the middle band.
   - Details: `god2_session17/findings/top2/gap_g8.md` and `an_*.md`.
4. The test protocol and tools of the current bot: `docs/strategy_v2/17_PATCH_3_0_4.md`, `docs/strategy_v2/18_V9_AND_PLAN.md`,
   `docs/TESTING.md`, `experiments/pools/README.md`, `README.md` (current build GOD v10).
5. The rules and API, only when you need them: `docs/sprint/GameRules.md`, `docs/sprint/BotAPICpp.md`, the SDK header
   `sdk/cpp/cambc.h` (3.0.5), `docs/ENGINE_FACTS.md`, `docs/COMMS.md` (shared memory and the draft-memory layout).

==================================================================================================================================
2. SETUP (new container)
==================================================================================================================================
- `cd Cambridge_Battlecode && git pull --no-rebase origin main`
- `tools/setup_session.sh` does everything:
  - installs cambc 3.0.5 and the wasm toolchain;
  - copies the SDK in from a scratch `cambc init`;
  - refreshes `maps/official/` from the platform (the environment allows 2026a.battlecode.co.uk; no login needed);
  - rebuilds every sparring bot and checks their source hashes.
- If the toolchain download fails TLS, use `curl --cacert /root/.ccr/ca-bundle.crt` (the script already does).
- Engines 3.0.4 and 3.0.5 play identically (MAPAnalysis section 3.2). `tools/ledger.py` stores both in
  `experiments/results/ledger_v3_0_4/`, so no game is ever replayed.
- Throughput: here (4 CPUs) about 1.3 games a second with `--jobs 4`. On my laptop (18 cores) about 4-5 a second.
  The engine runs on CPU only; a GPU helps model training only.

==================================================================================================================================
3. WHAT TO DO: section 5 of MAPAnalysis.md, steps 3 to 9, in order
==================================================================================================================================
STEP 3: exact map geometry and the per-map plans, in `tools/mapintel/` (Python 3, run with `python3 -I`).

Data source:
- Use the runtime dump as ground truth: extend `tools/probe/groups_probe_main.cpp` to also print the spawn regions, altar tiles and the
  wall / hole / bush bitboards.
- Facts about the dump:
  - each body is its own process, so the same lines print up to 5 times: keep one per group index;
  - heavy maps need `--rounds 8`;
  - pipe stdout through `tr -d '\000'`;
  - the extractor is `node tools/strategy_v2/s13/stdout.mjs REPLAY team-a.stdout`.
- A map file stores one copy of each mirrored camp. The mirror rule is in MAPAnalysis section 3.4.

Compute everything in section 5.3:
- (a) basics;
- (b) walking BFS, dash-augmented BFS per dash kit, crystal hops. Verify dash legality with an engine probe; the bot's current rule is
  `World::dash_walls` in `bots/god/src/world.cpp`;
- (c) the FULL-CYCLE economy model with every term I asked for:
  - champion-specific clearing (kit from the engine, `camp_damage_multiplier`, splash / area, Heart of Ruin's bonus);
  - damage taken;
  - healing and shopping trips;
  - tribute time max(1, ceil(0.1 × gems)) on a legal approach tile;
  - getting home as a choice between walking, recall and a nearby altar (recall is NOT mandatory);
  - respawn waits;
  - interference between teammates;
- (d) plan 1, initial champion-to-camp assignments;
- (e) plan 2, legal altar approach tiles and bank routes:
  - reachability for EACH TEAM SEPARATELY, by walking, by that team's legal dash, and by teleport crystal;
  - the tiebreak cases exactly as written: gold matters ONLY when tribute totals tie;
- (f) plan 3, contested groups with ETAs for both teams and the first-contact round;
- (g) plan 4, abandon / regroup conditions with thresholds;
- (h) conflict geometry;
- (i) objectives.

Outputs:
- `maps/catalog/maps.csv`, `maps/catalog/<map>.json`, `maps/catalog/<map>.npz`.

Checks:
- the Python features equal the bot's draft-time features (`bots/god/src/draft.cpp` `analyse()`, FEAT lines with
  `--define "LEGEND_FEATURES 1"`) on every map;
- the unopposed pace estimate correlates with measured idle pace (Spearman ≥ 0.8). Measure it with
  `python3 tools/ledger.py run god idle --maps "$(ls maps/official/*.map26a | paste -sd,)" --jobs 4`.

STEP 4: map archetypes.
- Standardise, PCA, then k-means (k by silhouette) and HDBSCAN.
- Reuse ideas from `tools/strategy_v2/map_plan.py`.
- Outputs: stratified pools, centroids and scaling for the bot's nearest-archetype fallback, and a loss analysis per archetype.

STEP 5: simulation labels.
- Write `tools/mapintel/run_battery.sh` for my laptop, in the pattern of `tools/rl/train_local.sh`. One command must:
  - install cambc 3.0.5 and build the bots;
  - run the outcome, draft and parameter batteries of section 5.5 with `tools/ledger.py run ... --keep KEEP`;
  - write one archive that I upload.
- Add `experiments/pools/official40.csv` (the 40 paths under `maps/official/`).
- While I run the laptop part, run the official-map outcome battery here.

STEP 6: models.
- Logistic / ridge with interactions as the baseline (`tools/draftmodel/fit.py`, `fit2.py`, `dataset.py`, `feats.py`).
- Gradient-boosted trees with SHAP, distilled into a linear model or ≤ 32 trees of depth ≤ 4.
- The parameter policy θ(map) = θ0 + W·φ(map): ridge first, then contextual ES with `tools/rl/es_train.py` (`ES_SRC`, `ES_OUT`,
  `ES_PREFIX`).
- Select with leave-maps-out cross-validation grouped by archetype.

STEP 7: deep learning and generative methods, ONLY where step 6 plateaus:
- CNN / U-Net on map tensors and a GNN on the group graph, trained on battery replays (decode them with `tools/replay/decode.mjs`), then
  distilled;
- a map generator calibrated to the official pool by a genetic algorithm (`tools/mapgen/gen.mjs`);
- adversarial map search (GA / MAP-Elites);
- behaviour cloning of top-team target choice from replays (tooling in `god2_session17/tools/live/`, `tools/top2/`). This feeds
  `group_score` in `bots/god/src/brain.cpp`.

STEP 8: generated headers in the bot's `src/mapintel/`, regenerated by `tools/mapintel/export_headers.py`:
- `features.h`;
- `model_weights.h`;
- `known_maps.h`: the approved exact-match table. FNV-1a 64 fingerprint over width, height, team size, the wall / hole / bush / altar
  bitboards and the sorted runtime camps. The table's fingerprints are produced by the SAME C++ function run inside the engine; never
  re-implement it in Python.
- `plans.h`: plans 1-4 computed at draft time and packed into draft memory, about 400 bytes. Extend `bots/god/src/dmplan.{h,cpp}`
  (magic 0xC8, versioned).

Tests:
- features equal on all maps;
- no new lost turns (`tools/fueltrace.py`);
- 0 exceptions (`tools/tracecount.py` with the `EXC_TRACE` build);
- builds on SDK 3.0.5 and 3.0.4.

Integration: into GOD v10 (`bots/god`) behind switches `mi_table`, `mi_model`, `mi_plans`. All off must replay v10's games exactly; check
with `tools/samegames.py`.

STEP 9: measure and ship.
- A/B against GOD v10 on `experiments/pools/test152.csv` and the 40 official maps, both sides, plus the third-party panel, pace, faults
  and fuel. Tools: `tools/abstat.py`, `tools/abmargin.py`, `tools/abconfirm.sh`, `tools/finalcheck.sh`.
- Table guard: keep an entry only if its gain holds against at least two opponent families.
- Ship only if measured better (`tools/ship_god.sh`: zip first, then `README.md` / `submissions/BUILDS.md` / `AGENTS.md` /
  `SUGGESTIONS.md` / `ISSUES.md`).

==================================================================================================================================
4. WHERE EVERYTHING IS
==================================================================================================================================
Maps and map data:
- `maps/official/*.map26a`: the 40 official maps.
- `maps/official/summary.csv`, built by `tools/mapintel/official_summary.py`.
- `experiments/results/mapintel/groups_runtime_official40.txt`: runtime groups, 836.
- `maps/comp30/`, `maps/nyx_new/`, `maps/loss_oct20/`: our replay copies. 21 of them equal official maps (mapping in MAPAnalysis
  section 4).
- `experiments/pools/*.csv`: test pools all308, train156, test152, train78a, train78b.

Engine facts:
- `experiments/results/probe_v3_0_5/engine_3_0_5.txt` (settings, camps, champions), from `tools/probe/engine_probe_main.cpp`.
- Runtime groups probe: `tools/probe/groups_probe_main.cpp`.
- Loaders: `tools/mapgen/engine.mjs` (engine wasm loader, MapBuilder), `tools/replay/mapinfo.mjs` (ASCII map view),
  `tools/replay/decode.mjs` (replay decoder), `tools/replay/extract_map.mjs` (map from a replay).

The current bot, GOD v10 (`bots/god/src`, `submissions/god.zip`):
- `draft.cpp`: `analyse()`, the dynamic draft, `pd_*` params.
- `brain.cpp`: `group_score`, `combat()`, banking, recall.
- `world.cpp`: groups, `dash_walls`.
- `nav.cpp`: distance fields.
- `dmplan.{h,cpp}`: draft memory.
- `params.h`: every switch, with its result in comments.

Testing:
- `tools/ledger.py` (run / table / `--keep`; per-engine ledger; refuses duplicate map names);
- `tools/abstat.py`, `tools/abmargin.py`, `tools/abconfirm.sh`, `tools/samegames.py`, `tools/screensum.py`, `tools/variant.sh`
  (`SRC=bots/X tools/variant.sh NAME key=val`);
- `tools/fueltrace.py`, `tools/tracecount.py`, `tools/finalcheck.sh`, `tools/ship_god.sh`.

Learning:
- `tools/draftmodel/*` (draft-value fit);
- `tools/rl/es_train.py` (ES), `tools/rl/train_local.sh` (laptop runner pattern), `tools/ml/` (danger model).

Analysis:
- `tools/strategy_v2/s13/*` (trace and replay readers; README there);
- `tools/strategy_v2/map_plan.py`;
- `god2_session17/tools/{live,top2}` (ladder study, replay downloads with login, path traces).

Docs to keep updated:
- `MAPAnalysis.md` section 7 (checkpoint log);
- the top bullet of `AGENTS.md`;
- `SUGGESTIONS.md` (ideas that did not measure better);
- `ISSUES.md` (anything hardcoded).

==================================================================================================================================
5. RULES (all from me)
==================================================================================================================================
- Pace: after EACH step, report to me in a few lines (what was done, the key numbers, the files, what is next), push, and keep going
  without waiting for my reply.
- Git: commit and push to `main` at every step. Run `git pull --no-rebase origin main` before each push; never force-push. No pull request.
  Update `MAPAnalysis.md` section 7 at every step.
- Subagents: few, and few parallel background jobs. Fable subagents for the main / heavy tasks, Opus for the tasks below that, then
  Sonnet; Haiku only for the smallest (docs, file moves). Do the core reasoning yourself.
- No hardcoded map strategy, apart from the approved exact-match table of the official maps (with the model as fallback). Everything else
  is derived at runtime from the map and the engine. List anything hardcoded in `ISSUES.md`.
- Ship a bot only when it is measured better, and push the zip first.
- Never `pkill -f` or `killall`: kill by PID. Never handle my credentials; if a login is needed, I run `cambc login` myself.
- Never use or commit the personal PDFs from session 13.
- Map file names must be unique under `maps/`: the ledger keys rows by file name and refuses clashes.
- Fuel limits in the bot: 1M on the first draft turn, 200k on a champion's first turn, 100k per later turn. A distance field costs
  13-19k. Every in-bot computation of the plans must stay inside these.
