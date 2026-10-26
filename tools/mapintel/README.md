# tools/mapintel: map analysis, map model and the exact-match map table

The plan and the progress log are in `MAPAnalysis.md` (repository root). This file says how to run things and how a bot uses the outputs.
Every output is marked by origin: **COMPUTED** (engine and map alone), **LEARNED** (current-patch real games), **SIMULATED** (games of
your new bot, from the batteries below).

## Before you start: three limits

- **The repository path must not contain spaces.** `cambc run-batch` (used by `run_battery.sh`) splits its manifest lines on spaces, so
  a path like `C:\Users\Your Name\Cambridge_Battlecode` breaks it; `battery.py` stops with an error before playing. On Windows, any of:
  - clone into a path without spaces (Git Bash): `mkdir -p /c/cambc && cd /c/cambc && git clone https://github.com/Akshayg005/Cambridge_Battlecode.git`;
  - keep your folder and give it a drive letter (Command Prompt, until the next reboot): `subst X: "C:\Users\Your Name\Cambridge_Battlecode"`,
    then in Git Bash `cd /x/` and run the scripts there (`subst X: /D` removes it);
  - or a junction (Command Prompt): `mklink /J C:\cb "C:\Users\Your Name\Cambridge_Battlecode"`, then run from `/c/cb` in Git Bash.
- **Fuel of the first draft turn (10,000,000 since patch 2.0.0, 100x a draft turn; 1,000,000 before):** the library takes at most
  **735,414** on the worst official map (big-world: `load_view`, `fingerprint`, `compute_features`, plans 2-4 and the first pick's
  rows), plus at most **85,540** if `first_scores()` (the opening ranking) runs on the same turn: **777,699** in all on the worst map
  (`test_library.py` measures it; measured on the 40 official maps with cambc 3.0.5); leave room for your bot's own first-turn work.
  Later draft turns (100,000): `row()` <= 13.5k per pick; the plan-1 turn (the remaining picks' rows, `plan1(picks, P, rank)` <= 43k,
  the block's pack and write) leaves at least 28k.
- **Your bot's own draft memory must stay below offset 512.** The mapintel block lives at 512-863 (352 bytes, checksummed); a shorter
  write of your bytes from offset 0 keeps it (tested). With draft memory version 2 (`dmem2.h`, next section) the whole 1,024 bytes have
  one layout (`docs/DRAFT_MEMORY.md`): the bot's blocks at 0-435, the free bytes 436-511, mapintel at 512, its DL outputs at 864.

## Laptop scripts (run on your machine; upload the archive they print)

Patch 2.0.0 (Sprint 3): **cambc 4.0.0** (engine 2.0.0) and the **70-map pool of `maps/s3`** (the 40 maps of `maps/official` + 30 new;
platform names use `_` where some files use `-`). The scripts install cambc 4.0.0 when needed and use the 70 maps without extra flags.
The whole refresh step by step (what to run, what to upload, what we do with it): `docs/strategy_v2/26_MAP_REFRESH_RUNBOOK.md`.

### 1. Ladder data now: `fetch_ladder.sh`
```bash
cd Cambridge_Battlecode
git pull --no-rebase origin main
pip install cambc==4.0.0                     # the script also installs it when cambc is missing or older
cambc login                                  # you, once (the script never handles credentials)
bash tools/mapintel/fetch_ladder.sh          # Linux, macOS, Windows Git Bash
```
- Fetches the ladder, the recent ranked matches of the top 50 teams, keeps the matches where **both** teams ran engine >= **2.0.0** (the
  platform's `engineVersion` is `1.0.3` for the old patch and `2.0.0` now, so only current-patch games pass) on the **70 maps of
  `maps/s3`**, and downloads up to 15 replays per map (strong vs strong first, then strong vs anyone; strong = the 20 best ratings),
  round-robin over the maps so a `--max-mb` cut keeps every map covered.
- Output: `mapintel_ladder_<UTC stamp>.tar.gz` (ladder, every team's list, the filtered matches = the draft dataset, team strengths, the
  selection, the replays). About 40-45 MB for 70 x 15 = 1,050 replays (`--max-mb 60` caps the replays); over 20 MB it is also cut into
  `.part00`, `.part01`, ... (upload all parts). Runtime about 10-25 minutes (platform rate limits). A cut run resumes.
- Options: `--top N --strong N --per-map K --max-mb M --min-engine 2.0.0 --kinds ranked[,unranked] --maps-dir maps/s3`, `--no-fetch`
  (reuse the lists), `--dry-run --ladder FILE LIST.jsonl...` (no platform calls). Step 5 prints the replays per map: if new maps get
  few, add `--kinds ranked,unranked` (match groups count too).

### 2. Simulation batteries later, for your bot: `run_battery.sh --bot NAME`
Prerequisite in your bot (`bots/NAME`): copy `tools/mapintel/cpp/mapintel/` into `bots/NAME/src/mapintel/` and make this the first thing
of the draft pick:
```cpp
#include "mapintel/force_roster.h"
...
if (const int p = mapintel::forced_pick(); p >= 0) { cambc::draft::pick(static_cast<cambc::champion_draft>(p)); return; }
```
In a normal build (no generated `mi_roster.h`) `forced_pick()` returns -1 at once and costs nothing. If your draft writes draft memory
after its pick, put the call where the pick is made so that work still runs for the forced roster. For a GOD bot, `--from god18 --bot
_mi_v18` makes the copy `bots/_mi_v18` itself (`prepare_bot.py`: the call goes first into `play_draft_pick()` and picks through
`note_pick()`, so `play_draft()` still writes v18's draft memory; `bots/god18` is not changed).
```bash
git pull --no-rebase origin main
bash tools/mapintel/run_battery.sh --from god18 --bot _mi_v18 --quick   # ~3-6 minutes: function test (00elkring, 01hooks, 02arena; 2 roster slots, idle opponent)
bash tools/mapintel/run_battery.sh --from god18 --bot _mi_v18          # the batteries (your own bot: --bot NAME)
```
- **Outcome battery**: your bot (its own draft) against `--opps self,idle,starter` (itself, an idle bot = your unopposed pace, the cambc
  4.0.0 starter; any bot folder name also works) on the 70 maps x 2 sides: 420 games.
- **Roster battery**: both teams' rosters forced, your bot playing both teams. Per map 8 candidate rosters
  (`tools/mapintel/data/battery_rosters.json`): on the 40 old maps 4 LEARNED (what strong teams drafted there, engine 1.0.3 games) + 4
  COMPUTED (balanced over the four kit classes); on the 30 new maps 8 COMPUTED (no ladder data of them yet: `meta.computed_only`). Every
  pair of candidates on every map and both sides: 28 x 70 x 2 = 3,920 games. The script checks every game's engine draft against the
  forced rosters and stops with an error if your bot ignores them.
- Runtime on 18 cores (17 jobs): about 20-35 minutes: 4,340 games (GOD v18: ~3.5 s a game per core, measured on 2 busy cores) and 9
  builds of the bot (~1-1.5 minutes each). Output: `mapintel_battery_<NAME>_<UTC stamp>.tar.gz` (ledger rows, `games.csv`, compact
  statistics, replays): about 100 MB with the replays (~22 KB a game; cut into 20 MB parts: upload all), about 5 MB with `--no-replays`
  (enough for the draft values and the DL data; the replays are for behaviour analysis).
- Options: `--opps`, `--maps` (comma list of globs; default `maps/s3/*.map26a`), `--jobs` (default: CPUs - 1), `--per-map C`,
  `--skip-outcome`, `--skip-roster`, `--no-replays`, `--from SRC`. It also compares `maps/s3` with the platform's current pool (from
  `cambc init`) and warns when they differ.
- The repository path must not contain spaces (`cambc run-batch` manifests are split on spaces): see "Before you start" for the Windows workaround.

### 3. Deep learning (step 7) on your GPU: `dl/run_dl.sh`
```bash
git pull --no-rebase origin main
bash tools/mapintel/dl/run_dl.sh --quick    # ~5 minutes: installs numpy + torch (CUDA 12.8) into mapintel_work/dlvenv, a few epochs
bash tools/mapintel/dl/run_dl.sh            # the run: 4 tasks x 3 seeds, leave-maps-out (20-60 minutes on an RTX-class GPU)
```
- Needs a 64-bit Python 3.10-3.13 and pip access (no cambc, no compiler), an NVIDIA driver 570 or newer (RTX 50-series need it) and
  about 6 GB of disk for torch. The script installs a CUDA build of torch (12.8, else 12.9, else 13.0), runs a test computation on the
  GPU and **stops with an error if the GPU does not work** (it never falls back to the CPU silently). `--cpu` = no GPU (hours).
  `PYTHON="py -3.12" bash ...` picks the interpreter.
- Input: `experiments/results/mapintel/dl_data/dataset.npz` (committed; rebuilt by `dl/make_dataset.py` from the ladder summaries,
  the battery's `games.csv` and the map dumps of all 70 maps: a new map gets the archetype a bot computes for it and an
  archetype-stratified fold, `pool.py`; `make_dataset.py --check` builds it without writing). The script first prints the dataset's
  sizes (`dataset: {...}`): after a refresh, run it once the rebuilt dataset is pushed (`"maps": 70`, your battery's `t2`). Output: `mapintel_dl_<UTC
  stamp>.tar.gz` (report, metrics, weights, out-of-fold heat maps; ~2-5 MB). Upload it.
- What it trains (each against the step-6 model on the same held-out maps): T1a opening targets, T1b a body's next target (behaviour
  cloning of the top teams), T2 champion values per map (on the roster battery), T3 heat maps (where the top teams farm, fight, capture,
  die: a U-Net, research only). Small MLPs are exported to `cpp/mapintel/dl_weights.h` only when they beat the step-6 bar
  (`dl/dl_export.py`; `test_library.py --dl-weights` checks them in the engine: rankings equal Python exactly, fuel measured).
- Options: `--tasks t1a,t1b,t2,t3`, `--seeds N`, `--hidden H` (exported MLP width: fuel grows with it), `--cpu`.

## The C++ library (`cpp/mapintel/`): how a bot uses it

Header-only C++20 on the SDK alone; copy `cpp/mapintel/` into your bot's `src/` (so `src/mapintel/*.h`) and include what you use.
Regenerate the data headers after a new ladder download or catalog: `python3 -I tools/mapintel/draft_learn.py && python3 -I
tools/mapintel/hazards.py --write-catalog && python3 -I tools/mapintel/dl/dl_tables.py && python3 -I tools/mapintel/export_headers.py`
(a rebuilt catalog drops the NAV and DL entries; the two scripts restore them in about 30 s); after a battery of your bot (its archive has `battery/games.csv`), make the draft values yours:
`python3 -I tools/mapintel/draft_learn.py --battery-only --battery <unpacked archive>/battery/games.csv --battery-label NAME && python3
-I tools/mapintel/export_headers.py`. Then run the tests: `python3 -I tools/mapintel/test_library.py` (all 40 maps x 2 teams in the engine).

| header | what | origin |
|---|---|---|
| `features.h` | `load_view(team_size)` (the map, groups and BFS fields), `compute_features(view)` (47 runtime features), `fingerprint(view)` | COMPUTED |
| `fingerprint.h` | `fingerprint()`: the exact-match key (FNV-1a 64); prefer `fingerprint(view)` (same value, no second `camp_groups()`) | COMPUTED |
| `plans.h` | `Compact` (per-group tables; its work uses the fitted economy constants of `model_weights.h` `econ_constants()`), `base_plans()` (plans 2-4; plan 2 by the walk, one BFS per candidate altar: 0.98 of the groups get the catalog's altar), `Compact::row(type)` and `plan1(picks, P, rank)` (plan 1: the first_scores() ranking's top groups assigned to the bodies by walk + work; held out it matches the top teams' first groups 0.696 vs 0.605 for the greedy without a ranking, body accuracy 0.177 vs 0.155) for unknown maps | COMPUTED + LEARNED |
| `dmem.h` | `dmem_pack()` / `dmem_put()` (the draft-memory block at offset 512) and `dmem_get()` / `Block` (read it in the game) | - |
| `known_maps.h` | generated: the table of the 40 official maps, `find_known(fp)`, `known_team(view, entry)` | COMPUTED + LEARNED |
| `model_weights.h` | generated: `zfeat()`, `archetype_of()`, `pick_prior()` (the default draft signal on unknown maps, < 3k fuel), `champion_values()` (secondary), `first_scores()` (opening score: a logistic on the group features, <= 86k fuel), `p4_thresholds()`, `econ_constants()` (the compact work's heal-trip share and camp damage scale) | COMPUTED + LEARNED + SIMULATED |
| `force_roster.h` | `forced_pick()` for the roster battery only (inert without a generated `mi_roster.h`) | - |
| `dl_weights.h` | generated by `dl/dl_export.py` (models the run marked for export, or `--force`d at your request): `dl_inputs()` (61.7k), `dl_opening_scores()` (91.4k), `dl_next_scores(..., &candidates)` (40.2k on 16 candidates); now: the 17:22 run's opening and next-target MLPs, forced (MAPAnalysis.md 7.2, 18:55) | LEARNED |
| `dmem2.h` | draft memory version 2 (`docs/DRAFT_MEMORY.md`): `Draft2` (the image, the fuel guard, the write), every block builder, `Reader`, `OwnRecompute` (the in-game OWN table, resumable) | COMPUTED + LEARNED |
| `hazards.h` | the NAV block: `nav_resume()` (resumable over draft turns), `nav_block()`, `nav_compute()`; `known_maps.h` carries it for the 40 maps | COMPUTED |

A draft that uses it (fuel measured by `test_library.py`, worst map; keep `view`, `F`, `C` alive across draft turns):

```cpp
#include "mapintel/dmem.h"          // includes plans.h and features.h
#include "mapintel/known_maps.h"
#include "mapintel/model_weights.h"
// first draft turn (1M fuel): <= 609k for all of this on the largest official map (lanes)
static std::optional<mapintel::MapView> view; static std::optional<mapintel::Features> F; static std::optional<mapintel::Compact> C;
view.emplace(mapintel::load_view());                      // ~160-300k
const auto fp = mapintel::fingerprint(*view);             // ~40-70k
F.emplace(mapintel::compute_features(*view));             // ~50-240k
C.emplace(*view, *F);
auto P = mapintel::base_plans(*C, *view, *F);             // plans 2-4, ~50-255k
const int e = mapintel::find_known(fp);                   // >= 0: KNOWN[e] has the catalog's plans and the ladder's draft data
double z[mapintel::MW_NF], value[12];
mapintel::zfeat(*F, z);
const int arch = mapintel::archetype_of(z);              // unknown maps: the archetype from the features
// the draft signal. DEFAULT (LEARNED, current-patch ranked games): the strong teams' pick prior, per champion (champion_draft ids):
//   known map:   KNOWN[e].pick_strong[c] / 200.0                 (that map's own top-20-team pick rate)
//   unknown map: pick_prior(z, rate, first)                      (rate and first-pick share predicted from the map's features)
// SECONDARY (SIMULATED v10, flagged: GOD v10's roster battery, until a battery of your bot replaces it with run_battery.sh):
//   KNOWN[e].value[c] / 1000.0, or champion_values(z, value)     (log-odds per champion)
double rate[12], first[12];
mapintel::pick_prior(z, rate, first);
mapintel::champion_values(z, value);
const auto sc = mapintel::first_scores(*C, *view, *F);  // <= 86k: the LEARNED opening ranking; keep the 6-16 best groups:
std::vector<int> rank;                                    // reached groups by score, best first (ties to the lower index)
// each later draft turn: C->row(type) for the bodies of the champion you just picked (<= 13k each)
// the turn the roster is complete: C->plan1(our_picks, P, rank) (<= 40k; without rank the older greedy plan 1, <= 25k), then write
// your own bytes and the block together:
std::vector<std::uint8_t> mem(1024, 0);                   // your data at 0..511
mapintel::dmem_put(mem, mapintel::dmem_pack(P, fp, view->team, e >= 0, arch));
cambc::draft_memory = mem;                                // a later shorter write of your prefix keeps the block (tested)
// in the game, any champion: mapintel::Block B; if (mapintel::dmem_get(B)) { B.plan(slot, k), B.bank_altar(g), B.con(k), ... }
```

### Draft memory version 2 (`dmem2.h`): how a draft writes it and a champion reads it

The layout is `docs/DRAFT_MEMORY.md`. The reference integration is the test bot `cpp/test2/main.cpp` (copy its `draft_turn()` order);
`python3 -I tools/mapintel/test_dmem2.py` checks it against the Python twins (`dmem2.py`, `hazards.py`) and measures the fuel. Copy
`cpp/mapintel/` and `tools/teamplan/cpp/teamplan/` into your bot's `src/` (`dmem2.h` includes `../teamplan/*.h`). Keep the state in
static storage: the wasm stack is small, and an overflow corrupts static data without a trap.

```cpp
#include "mapintel/dmem2.h"     // + known_maps.h, model_weights.h, dl_weights.h when present
static mapintel::Draft2 D;      // the image, the guard; keep across draft turns with view, F, C, P (above)
// EVERY draft turn: D.begin(); pick FIRST; then the work below; then D.write(final_turn, minimal). A turn that runs out of fuel
// continues in the next turn's budget and loses that turn's pick (the engine then draws the rest at random): every optional block
// runs through D.run(block, builder, estimate), which skips it unless the fuel left exceeds 1.25 x its last cost + 10,000.
// turn 1 (after mapintel's turn-1 work, <= 779k):
auto K = mapintel::kits13_from_sdk();                                  // 35.2k: kits + danger features of the 13 designs
int bank_ord[8]; const int nbo = mapintel::bank_order(C, P, bank_ord);  // + rally tiles: <= 38.2k, once (roster-free)
int rally[8]; const int nr = mapintel::rally_tiles(C, view, P, bank_ord, nbo, rally);
D.img.put(mapintel::BK_MAP, mapintel::dmem_pack(P, fp, ts, known, arch)); // mapintel's block at 512 (7.4k)
// NAV: known map -> D.img.put(BK_NAV, nav_from_table(KNOWN[e].nav + 64 * team)); unknown -> nav_resume(work, view, C, in) every
// turn down to a floor (<= 236k in all), then D.img.put(BK_NAV, nav_block(work, view, C, in))
// OWN (guarded, estimate OWN_EST): build_own(own_groups(C, view, K.p), types, n, K); TEAM: build_team(P, types, n, &own, capture_mode);
// CODE: build_code(rally, nr, &own, bank_ord, nbo); ENEMY (guarded): build_enemy(Compact(C, 1), bankbox, K, enemy_picks, ne)
// later turns: row(), OWN, TEAM, CODE, ENEMY, NAV resumed; the last turn: plan1, the M block again, BODY (build_body), CONT
// (build_cont), the L block (build_dl, from known_maps.h's DL tables), then OWN / ENEMY only under the guard; D.write(true, false).
```

In the game, any champion (all reads are bounds- and checksum-checked; a missing or invalid block returns null: fall back):

```cpp
mapintel::Reader r; r.load();                                // the snapshot every champion got at startup
const std::uint8_t* team = r.block('T', 1);                  // TEAM: bytes 4-9 = the body types by slot (= teamplan live slots)
const int slot = team ? mapintel::team_slot(team, my_type) : -1;
const std::uint8_t* own = r.block('O', 1);                   // owner / next owner of group g: own_owner(own, g), own_next(own, g)
const std::uint8_t* body = r.block('B', 1);                  // body + 16 * slot: role, build, route, bank bag, retreat health
const std::uint8_t* code = r.block('K', 1);                  // rally tiles, zone anchors, altar ids: the live bytes' places
const std::uint8_t* nav = r.block('N', 1), *enemy = r.block('E', 1), *dl = r.block('L', 1);
// OWN for the full roster when TEAM byte 11 < the roster size: static mapintel::OwnRecompute orc; each game turn from turn 2 on,
// orc.step(r, floor) until it returns true (154.8k in all on the worst map: 2 game turns with a 20k floor), then use orc.out.b
// known map (mapintel::find_known(fingerprint from the M block)): mapintel::known_dl_next(KNOWN[e], known_team_game(KNOWN[e]),
// round, my_type, captured_group) -> the step-7 model's two best next groups, zero fuel
```

Fuel facts the library follows (measured in this engine): ~50-175 fuel per step of a simple loop (a 144-tile loop with a few reads
cost 25k); memory growth costs 8 fuel a page and a zeroed 200 KB vector 6 (bulk memory); `bitboard::positions_into` returns the
engine's chunk order, not tile order (`hazards.h` reads set bits from the linear export instead); a zero-initialised buffer costs ~1.2
fuel per byte (use trivial types / uninitialised buffers); `map::camp_groups()` builds every camp object (call it once); `camp::base_stats()`
is a host call; stdout costs ~90 fuel per byte.

## Files

| path | what | origin |
|---|---|---|
| `fetch_ladder.sh`, `ladder_fetch.py` | ladder download (laptop): engine >= 2.0.0, the 70 maps of `maps/s3` | - |
| `run_battery.sh`, `battery.py`, `prepare_bot.py` | simulation batteries for any bot (laptop; 70 maps); a battery-ready copy of a bot (`--from`) | - |
| `battery_rosters.py`, `data/battery_rosters.json` | candidate rosters per map for the roster battery (70 maps; the 30 new maps COMPUTED only, `meta.computed_only`) | LEARNED + COMPUTED |
| `pool.py` | the 70-map pool for the leave-maps-out learners: a map outside the catalog gets its runtime z, `archetype_of()` and an archetype-stratified fold (`make_dataset.py`, `draft_learn.py`) | COMPUTED |
| `dump_maps.py` | runtime dump of maps through the probe bot (`cpp/probe`) | COMPUTED |
| `engine.py` | engine facts parsed from the engine probe's output (`experiments/results/probe_v3_0_5/engine_3_0_5.txt`) | COMPUTED |
| `cpp/mapintel/` | the header-only C++ library a bot includes (section above) | - |
| `cpp/test/main.cpp`, `test_library.py` | the library's test bot and test driver (features, plans, block, table, weights, fuel) | - |
| `cpp/test2/main.cpp`, `test_dmem2.py` | draft memory v2's test bot (the reference draft integration) and test driver: round trip, prefix rule, fuel, coexistence, fallback, the in-game OWN recompute | - |
| `dmem2.py`, `hazards.py` | Python twins of `dmem2.h` and `hazards.h` (bit-equal); `hazards.py --write-catalog` stores NAV in the catalog for `export_headers.py` | COMPUTED |
| `dl/dl_tables.py` | the step-7 opening and next-target models as tables per official map and team into the catalog (`known_maps.h` `dl_open`, `dl_next`, `known_dl_next()`) | LEARNED |
| `compact.py` | Python twin of `plans.h` and `dmem.h` (bit-equal) | COMPUTED |
| `features.py` | Python twin of `features.h` | COMPUTED |
| `draft_learn.py` | step 6, draft: per-map prior (`maps/catalog/draft_prior.json`), the draft win models on the ladder (no signal over rating) and on a roster battery (`--battery`) | LEARNED / SIMULATED |
| `first_targets.py` | step 6, opening: which groups the top teams capture first (logistic and boosted forest, leave-maps-out) | LEARNED |
| `validate_ladder.py` | 3C: the model against the top teams (pace, first targets, bank altars); `maps/catalog/behaviour.json` | LEARNED |
| `export_headers.py` | generates `known_maps.h` and `model_weights.h` (with `group_features()`, the 22 per-group inputs of the step-6 / step-7 models) | - |
| `dl/make_dataset.py` | step 7 data: map tensors, group features, opening / next-target / roster / heat samples, the step-6 baselines (`dl_data/`) | COMPUTED + LEARNED + SIMULATED |
| `dl/dl_train.py`, `dl/run_dl.sh` | step 7 training (torch; laptop GPU): MLP, group-graph attention, distillation, U-Net; leave-maps-out | LEARNED / SIMULATED |
| `dl/dl_ref.py`, `dl/dl_export.py` | the exported models' Python reference (same evaluation order as the C++) and the header generator | - |
| `battery_games.py` | a battery archive -> `games.csv` (rosters from the kept statistics) for `draft_learn.py --battery` | SIMULATED |
| `replays.py` | ladder replays -> per-game summaries (captures, banks, deaths, standing tiles); maps matched among all 70 dumps | LEARNED |
| `replay_tracks.py` | ladder replays -> per-game tracks (positions, health, bags, gold, camp health per round, events; `mapintel_work/tracks/`) | LEARNED |
| `econ_learn.py` | the economy model's constants (retreat, heal, bank bag, shop gold, gold weight, damage scale, opposition share) measured / fitted on the replays; `economy.econ()` reads `experiments/results/mapintel/economy/constants.json` | LEARNED |
| `plan1_learn.py` | plan 1 against the top teams' openings per kit class (held out); writes the table's first targets (`experiments/results/mapintel/plan1/table_first.json`) | LEARNED |
| `heat_features.py` | the U-Net's out-of-fold heat maps -> per-group / per-bank-route fight and death densities; tested on plans 3 and 4 (no gain: not in the table) | LEARNED |
| `plan4_learn.py`, `p4model.py` | plan 4's thresholds from the top teams' decisions (abandon, regroup, bank abort, respawn wait); `p4model.py` = `model_weights.h` `p4_thresholds()` | LEARNED |
| `cpp/probe/`, `cpp/idle/` | probe bot and idle opponent sources (fresh, from the 3.0.5 starter) | - |
| `../../experiments/results/mapintel/dump/` | `<map>.txt` runtime dumps, `fingerprints.txt` (the 40 official maps: `mapdata.official_names()`) and `fingerprints_s3_new.txt` (the 30 new maps; all 70: `mapdata.pool_names()`) | COMPUTED |
