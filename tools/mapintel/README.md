# tools/mapintel: map analysis, map model and the exact-match map table

The plan and the progress log are in `MAPAnalysis.md` (repository root). This file says how to run things and how a bot uses the outputs.
Every output is marked by origin: **COMPUTED** (engine and map alone), **LEARNED** (current-patch real games), **SIMULATED** (games of
your new bot, from the batteries below).

## Laptop scripts (run on your machine; upload the archive they print)

### 1. Ladder data now: `fetch_ladder.sh`
```bash
cd Cambridge_Battlecode
git pull --no-rebase origin main
pip install cambc==3.0.5
cambc login                                  # you, once (the script never handles credentials)
bash tools/mapintel/fetch_ladder.sh          # Linux, macOS, Windows Git Bash
```
- Fetches the ladder, the recent ranked matches of the top 50 teams, keeps the matches where **both** teams ran engine >= 1.0.3 on the 40
  official maps, and downloads up to 15 replays per map (strong vs strong first, then strong vs anyone; strong = the 20 best ratings).
- Output: `mapintel_ladder_<UTC stamp>.tar.gz` (ladder, every team's list, the filtered matches = the draft dataset, team strengths, the
  selection, the replays). About 20-25 MB (`--max-mb 60` caps it). Runtime about 5-15 minutes (platform rate limits). A cut run resumes.
- Options: `--top N --strong N --per-map K --max-mb M --min-engine 1.0.3 --kinds ranked[,unranked]`, `--no-fetch` (reuse the lists),
  `--dry-run --ladder FILE LIST.jsonl...` (no platform calls).

### 2. Simulation batteries later, for your bot: `run_battery.sh --bot NAME`
Prerequisite in your bot (`bots/NAME`): copy `tools/mapintel/cpp/mapintel/` into `bots/NAME/src/mapintel/` and make this the first thing
of the draft turn:
```cpp
#include "mapintel/force_roster.h"
...
if (const int p = mapintel::forced_pick(); p >= 0) { cambc::draft::pick(static_cast<cambc::champion_draft>(p)); return; }
```
In a normal build (no generated `mi_roster.h`) `forced_pick()` returns -1 at once and costs nothing.
```bash
git pull --no-rebase origin main
bash tools/mapintel/run_battery.sh --bot NAME --quick   # ~1 minute: function test (3 maps, 2 roster slots, idle opponent)
bash tools/mapintel/run_battery.sh --bot NAME           # the batteries
```
- **Outcome battery**: your bot (its own draft) against `--opps self,idle,starter` (itself, an idle bot = your unopposed pace, the cambc
  3.0.5 starter; any bot folder name also works) on the 40 official maps x 2 sides: 240 games.
- **Roster battery**: both teams' rosters forced, your bot playing both teams. Per map 8 candidate rosters
  (`tools/mapintel/data/battery_rosters.json`: the rosters strong teams drafted there in current-patch games = LEARNED, and rosters
  balanced over the four kit classes = COMPUTED); every pair of candidates on every map and both sides: 28 x 80 = 2,240 games. The script
  checks every game's engine draft against the forced rosters and stops with an error if your bot ignores them.
- Runtime on 18 cores: about 10-15 minutes for 2,480 games (depends on your bot's speed). Output:
  `mapintel_battery_<NAME>_<UTC stamp>.tar.gz` (ledger rows, compact statistics, replays; ~25 KB a game, `--no-replays` to drop them).
- Options: `--opps`, `--maps`, `--jobs` (default: CPUs - 1), `--per-map C`, `--skip-outcome`, `--skip-roster`, `--no-replays`.
- The repository path must not contain spaces (`cambc run-batch` manifests are split on spaces).

## The C++ library (`cpp/mapintel/`): how a bot uses it

Header-only C++20 on the SDK alone; copy `cpp/mapintel/` into your bot's `src/` (so `src/mapintel/*.h`) and include what you use.
Regenerate the data headers after a new ladder download or catalog: `python3 -I tools/mapintel/draft_learn.py && python3 -I
tools/mapintel/export_headers.py`; then run the tests: `python3 -I tools/mapintel/test_library.py` (all 40 maps x 2 teams in the engine).

| header | what | origin |
|---|---|---|
| `features.h` | `load_view(team_size)` (the map, groups and BFS fields), `compute_features(view)` (47 runtime features), `fingerprint(view)` | COMPUTED |
| `fingerprint.h` | `fingerprint()`: the exact-match key (FNV-1a 64); prefer `fingerprint(view)` (same value, no second `camp_groups()`) | COMPUTED |
| `plans.h` | `Compact` (per-group tables), `base_plans()` (plans 2-4), `Compact::row(type)` and `plan1(picks, P)` (plan 1) for unknown maps | COMPUTED |
| `dmem.h` | `dmem_pack()` / `dmem_put()` (the draft-memory block at offset 512) and `dmem_get()` / `Block` (read it in the game) | - |
| `known_maps.h` | generated: the table of the 40 official maps, `find_known(fp)`, `known_team(view, entry)` | COMPUTED + LEARNED |
| `model_weights.h` | generated: `zfeat()`, `archetype_of()`, `champion_values()` (the fallback for unknown maps) | COMPUTED + LEARNED |
| `force_roster.h` | `forced_pick()` for the roster battery only (inert without a generated `mi_roster.h`) | - |

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
auto P = mapintel::base_plans(*C, *view, *F);             // plans 2-4, ~50-160k
const int e = mapintel::find_known(fp);                   // >= 0: KNOWN[e] has the catalog's plans and the ladder's draft data
double z[mapintel::MW_NF], value[12];
mapintel::zfeat(*F, z);
const int arch = mapintel::archetype_of(z);              // unknown maps: archetype and LEARNED champion values from the features
mapintel::champion_values(z, value);
// each later draft turn: C->row(type) for the bodies of the champion you just picked (<= 13k each)
// the turn the roster is complete: C->plan1(our_picks, P) (<= 25k), then write your own bytes and the block together:
std::vector<std::uint8_t> mem(1024, 0);                   // your data at 0..511
mapintel::dmem_put(mem, mapintel::dmem_pack(P, fp, view->team, e >= 0, arch));
cambc::draft_memory = mem;                                // a later shorter write of your prefix keeps the block (tested)
// in the game, any champion: mapintel::Block B; if (mapintel::dmem_get(B)) { B.plan(slot, k), B.bank_altar(g), B.con(k), ... }
```

Fuel facts the library follows (measured in this engine): ~50-75 fuel per step of a simple loop; a zero-initialised buffer costs ~1.2
fuel per byte (use trivial types / uninitialised buffers); `map::camp_groups()` builds every camp object (call it once); `camp::base_stats()`
is a host call; stdout costs ~90 fuel per byte.

## Files

| path | what | origin |
|---|---|---|
| `fetch_ladder.sh`, `ladder_fetch.py` | ladder download (laptop) | - |
| `run_battery.sh`, `battery.py` | simulation batteries for any bot (laptop) | - |
| `battery_rosters.py`, `data/battery_rosters.json` | candidate rosters per map for the roster battery | LEARNED + COMPUTED |
| `dump_maps.py` | runtime dump of maps through the probe bot (`cpp/probe`) | COMPUTED |
| `engine.py` | engine facts parsed from the engine probe's output (`experiments/results/probe_v3_0_5/engine_3_0_5.txt`) | COMPUTED |
| `cpp/mapintel/` | the header-only C++ library a bot includes (section above) | - |
| `cpp/test/main.cpp`, `test_library.py` | the library's test bot and test driver (features, plans, block, table, weights, fuel) | - |
| `compact.py` | Python twin of `plans.h` and `dmem.h` (bit-equal) | COMPUTED |
| `features.py` | Python twin of `features.h` | COMPUTED |
| `draft_learn.py` | step 6, draft: per-map prior (`maps/catalog/draft_prior.json`) and the draft win models (leave-maps-out) | LEARNED |
| `export_headers.py` | generates `known_maps.h` and `model_weights.h` | - |
| `replays.py` | ladder replays -> per-game summaries (captures, banks, deaths, standing tiles) | LEARNED |
| `cpp/probe/`, `cpp/idle/` | probe bot and idle opponent sources (fresh, from the 3.0.5 starter) | - |
| `../../experiments/results/mapintel/dump/` | `<map>.txt` runtime dumps and `fingerprints.txt` | COMPUTED |
