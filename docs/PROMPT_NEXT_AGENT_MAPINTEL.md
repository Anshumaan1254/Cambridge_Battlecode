# Prompt for the next agent: map analysis for the user's new bot (session 18b handoff, Oct 24 2026)

Paste everything below the line into a new session.

---

You continue the **map-analysis work** for Cambridge Battlecode 2026a (CAMBC; C++ bots compiled to wasm; engine cambc 3.0.5 = engine
v1.0.3). The user is writing **their own new bot**. Your job is the map analysis, the map model and the exact-match map table it will
use. You do not build or ship a bot. Read `MAPAnalysis.md` first (sections 1.7, 1.8, 5 and 7): it is the only record of this work.
Then read `tools/mapintel/README.md` (how to run everything and how a bot uses the library) and the "mapintel" section of `ISSUES.md`.
Everything else in `AGENTS.md` and the older docs predates the Oct 20-22 patches and is **not an input** (the source rule, 1.7).

## Rules (the user's, still in force)
- Report after each step in a few lines, write the step into `MAPAnalysis.md` (a checkpoint in 7.2 with the UTC time, and the status in
  7.1), commit and push, then keep going without waiting. The user answers slowly: decide, record the decision, continue.
- Git: commit and push to `main` at every step. Run `git pull --no-rebase origin main` before each push. Never force-push. No pull
  request. End commit messages with the session's attribution lines. No model identifier in any repository file.
- Do not modify anything under `bots/` (apart from your git-ignored test and probe bots) or `submissions/`, and do not ship any bot.
- No hardcoded map strategy, apart from the approved exact-match table of the official maps (with the model as fallback). List anything
  hardcoded in `ISSUES.md` (the mapintel section).
- Sources (1.7): the 3.0.5 engine and SDK, your own probes, the 40 official maps (`maps/official/`), the current rules
  (`docs/patch_notes/week2_*`, `week3_*`, `docs/sprint/v3_0_4/`), current-patch ladder data, `MAPAnalysis.md`. GOD v10 (`bots/god`,
  read-only) may stand in where a bot is needed (1.8); label its results **SIMULATED (v10)**. Mark every output **COMPUTED**,
  **LEARNED** or **SIMULATED**.
- Never `pkill -f` or `killall`: kill by PID. Never handle the user's credentials (they run `cambc login` themselves). Never use or commit
  the personal PDFs from session 13. Map file names must be unique under `maps/`.
- Fuel: 1,000,000 on the first draft turn, 200,000 on a champion's first turn, 100,000 on every other turn. Measure every new in-bot
  function in the engine (`tools/mapintel/test_library.py` prints the fuel).
- Few subagents; do the core reasoning yourself. Laptop scripts must run on Windows Git Bash / MSYS, Linux and macOS (no GNU `sed -i`,
  `--release` builds, fail loudly). Untrusted downloads go in their own directories; run Python on them with `-I`.

## What is done (all committed; numbers in `MAPAnalysis.md` 7.2)
1. **Steps 1-2**: patch and package check (3.0.5 plays exactly like 3.0.4); the 40 official maps (byte-identical to a fresh `cambc init`
   pull on Oct 24).
2. **Laptop scripts**: `tools/mapintel/fetch_ladder.sh` (ladder download, run by the user: the archive is in
   `experiments/ladder_oct24/mapintel_20261024_0836/`), `tools/mapintel/run_battery.sh --bot NAME` (outcome + roster batteries; run by the
   user with GOD v10: `experiments/results/mapintel/sim_v10_laptop/`, identical to this container's 2,480 games: the engine is
   deterministic across platforms), `tools/mapintel/dl/run_dl.sh` (step 7, below).
3. **Step 3** (COMPUTED): engine rule probes (ranges Chebyshev, dash and crystal legality, captures, respawn holds, line of sight),
   runtime dumps, geometry, the full-cycle economy model, plans 1-4, per-kit-class tile analysis, the catalog `maps/catalog/`.
4. **Step 4**: archetypes (k = 3) and 5 archetype-stratified leave-maps-out folds (`maps/catalog/splits.json`).
5. **Step 6** on the user's ladder archive (8,455 current-patch match rows, 599 decoded replays) and GOD v10's battery:
   - 3C validation: pace Spearman 0.758 against the top teams' real finishes (0.802 held out after change 2's fit, below); plan 2's
     bank altars hold 97% of 24,945 real banks;
   - opening score `first_scores()`: since the gold-only capture fix (below) a logistic on 22 group features, 0.696 top-n share on
     held-out maps (forest 0.689, nearest groups 0.648);
   - draft values: the ladder has no champion signal over team rating (log loss 0.6829 rating only vs 0.6847 with champions); the
     values come from GOD v10's roster battery (log loss 0.622 vs 0.662 side only): SIMULATED (v10), to be refitted on the user's bot;
   - per-map pick prior of the strong teams (`maps/catalog/draft_prior.json`), behaviour targets (`maps/catalog/behaviour.json`).
6. **Step 8**: the header-only C++ library `tools/mapintel/cpp/mapintel/` (features, fingerprint, plans, draft-memory block at offset
   512, forced rosters for the battery, the generated `known_maps.h` and `model_weights.h`), its test bot and `test_library.py`: features
   and plans bit-equal to Python on 40 maps x 2 teams, the table lookup, perturbed maps take the fallback, the block survives GOD v10's
   own write, fuel within limits (735k worst first draft turn, 778k with `first_scores()` on it); builds on SDK 3.0.5 and 3.0.4.
7. **Step 7 (built at the user's request on Oct 24; run on the user's RTX 5070 laptop GPU, nothing beat step 6)**: `tools/mapintel/dl/`:
   - `make_dataset.py` -> `experiments/results/mapintel/dl_data/` (committed: dataset.npz + meta.json with the step-6 bars);
   - `dl_train.py` (torch): T1a opening (MLP, group-graph attention with a learned distance bias, distillation), T1b next target (the
     same three: behaviour cloning of the top teams' target choice), T2 champion values per map (values MLP, deep set), T3 heat maps
     (U-Net, dihedral augmentation); leave-maps-out with inner early stopping, seeds; an MLP is marked "export" only when it beats the
     step-6 bar on held-out maps by `MARGIN`;
   - `dl_export.py` -> `cpp/mapintel/dl_weights.h`; `dl_ref.py` (its Python reference, the same evaluation order); `test_library.py
     --dl-weights` checks the header in the engine: tested with forced weights on 78 map-teams, rankings and values equal Python exactly;
     fuel: inputs 62k, opening 92k (draft turn), next target 40k a call on 16 candidates (all 64 groups 107k: too much for a game turn),
     values 4k. The forced test header was deleted (no `dl_weights.h` is committed until a real run beats step 6).
   - The user's GPU run (3 seeds, results in `experiments/results/mapintel/dl_model_20261024_1014/`, MAPAnalysis 7.2 at 10:40): T1a
     MLP 0.676 / graph 0.653 / distilled 0.672 against the forest's 0.723, T1b no gain, T2 0.668 against 0.622 but not by the margin,
     T3 heat maps 0.519 against 0.221 (research only). Nothing exported, no `dl_weights.h`. The run used the replays as decoded before
     the gold-only capture fix; a re-run is optional (the user's call).
8. **The user's changes of Oct 24 (after the first handoff), all done** (MAPAnalysis 7.2, 10:35 to 15:30):
   - the decoder missed gold-only captures (`CaptureGold`, `decode.mjs --gold-captures`): every capture-based result re-run;
   - change 1: plan 4 LEARNED (`plan4_learn.py`, `p4model.py`, `model_weights.h` `p4_thresholds()`): one value per map beats the formulas
     held out for k_abandon, p, d_regroup and the bank margin; no map feature moved them; w_max stays the formula;
   - change 2: the economy constants fitted to the top teams' replays (`econ_learn.py`, `experiments/results/mapintel/economy/`): pace
     Spearman 0.802 held out (0.758 before) with an opposition share term; the catalog rebuilt;
   - change 3: plan 1 = the `first_scores()` ranking's top groups assigned by walk + work (exact subset DP, `plan1(picks, P, rank)`),
     held-out body accuracy 0.177 (`plan1_learn.py`, per kit class); the table's `ref_first` from the catalog economy;
   - change 4: the strong teams' pick prior is the default draft signal (`pick_strong` in the table, `pick_prior()` for unknown maps),
     GOD v10's values flagged secondary;
   - change 5: the runtime fallback against the catalog (`fallback_gap.py`): the fitted economy constants (`econ_constants()`) and plan 2
     by the walk added; shields, stuns, Ren's retaliation, Heart of Ruin's bonus measured and not added;
   - change 6: the README's "Before you start: three limits" (first-turn fuel, draft memory below 512, no spaces in the repository path
     with the Windows workarounds);
   - the T3 heat maps as plan 3 / plan 4 features: tested, not adopted (`heat_features.py`).

## What is left (in order)
1. **Optional: a step-7 re-run on the fixed captures** (only if the user asks; rebuild the dataset with `make_dataset.py` first). The
   user runs it (`bash tools/mapintel/dl/run_dl.sh`, RTX 5070 laptop GPU, Windows Git Bash; GPU fixes: driver 570+, charger plugged in,
   high-performance GPU for python.exe, delete `mapintel_work/dlvenv`). Unpack the archive into
   `experiments/results/mapintel/dl_model_<stamp>/`; for each model marked "export": `dl_export.py --weights <dir>/dl_weights.json`, then
   `test_library.py --dl-weights <dir>/dl_weights.json` (all checks must pass); else record the numbers and keep the step-6 models.
   T3's heat maps (`heat_pred.npz`) are research output; as plan features they did not help (change list above).
2. **The user's new bot**: when it exists, `run_battery.sh --bot <copy> --from <their bot>`; then `draft_learn.py --battery-only
   --battery <archive>/battery/games.csv --battery-label NAME`, `export_headers.py`, `test_library.py`, and rebuild the step-7 dataset
   (`make_dataset.py --battery <that games.csv>`) so T2 refits on their play. The current draft values are GOD v10's (SIMULATED v10).
3. **Integration help**: the user plugs the headers into their bot (`tools/mapintel/README.md`, "how a bot uses it"); answer
   questions, keep the library's tests passing, keep the block at offset 512.
4. **Pace model calibration**: Spearman 0.802 held out against the top teams since change 2 (0.76 before); per map type in 7.2 (11:40).
   Improve the model's mechanics only if the user asks.
5. **Contextual ES of parameters** (5.6): deferred until the user's bot exists (it needs a bot with parameters).

## What was abandoned or dropped, and why
- **Step 5 with GOD v10 and the old panel**: dropped by the source rule (1.7: old bots and ledgers are not inputs); replaced by
  `run_battery.sh --bot NAME` for the user's bot (GOD v10 as the stand-in for now, 1.8). The **parameter battery** does not apply to a
  bot without GOD's knobs.
- **Step 7 adversarial map search** (GA / MAP-Elites): out of scope (1.7: no A/B, no bot hardening).
- **Step 7 map generator calibrated by a GA**: not built. Generated maps have no labels without the user's bot playing them, and the
  official pool (40 maps) is what the table and the model are fitted and checked on; revisit if the final sprint's map pool changes and
  the user's bot can run batteries on generated maps.
- **Behaviour cloning into GOD's `group_score`**: dropped (no bot integration, 1.7). The labels were produced instead (step 6
  `behaviour.json`) and step 7's T1b is the behaviour-cloning model, exported to the library when it wins.
- **Reference integration into GOD v10** (`mi_table`, `mi_model`, `mi_plans` switches) and **step 9** (A/B, ship): out of scope (1.7).
- **The check against GOD's draft-time features**: dropped (not an input); replaced by the engine test of the library.
- **Ladder-fitted champion values**: no signal over team rating out of sample (a converged meta and strength differences hide a
  champion's value); kept only as an imitation prior (pick rates), the values come from a battery.
- **Map-dependent draft terms** (champion x archetype, champion x features): did not beat constant values out of sample on the battery.
- **Plan 1 as the opening**: no better than the nearest groups against the top teams (0.53 vs 0.54); the learned `first_scores()` is
  the opening model instead.
- **"Meet" (the fronts' meeting round) as a runtime feature**: replaced by the enemy's nearest altar distance (two full-field exports
  cost too much fuel in the draft).
- **Step 7 was first judged unnecessary** (09:40: the forest closed the opening gap; the ladder values have no signal); the user then
  asked for it, so it was built as an offline run whose models reach the library only when they beat step 6.

## Gotchas
- The engine charges about 1,600 fuel per group for a 22-input, 8-hidden MLP, mostly loop overhead: `dl_export.py` emits fixed-size
  templates so the loops unroll. `camp_groups()` builds every camp object (call once), `camp::base_stats()` is a host call (once per
  camp type), stdout costs about 90 fuel a byte, zero-filled buffers about 1.2 fuel a byte.
- Draft memory: the SDK writes from offset 0 and a shorter write keeps the later bytes; the mapintel block is at 512-863; the test bot
  prints from 8-511 and 864-999 (test only).
- Python twins must stay bit-equal to the C++ (same operation order, no FMA in wasm): change both together and rerun the test.
- Resume in a new container: `MAPAnalysis.md` 7.7.
