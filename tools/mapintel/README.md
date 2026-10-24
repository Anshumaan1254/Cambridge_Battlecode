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
- **Fuel of the first draft turn (1,000,000):** the library takes at most **735,414** on the worst official map (big-world:
  `load_view`, `fingerprint`, `compute_features`, plans 2-4 and the first pick's rows), plus at most **85,540** if `first_scores()`
  (the opening ranking) runs on the same turn: **777,699** in all on the worst map (`test_library.py` measures it); leave room for
  your bot's own first-turn work. Later draft turns (100,000): `row()` <= 13.5k per pick; the plan-1 turn (the remaining picks' rows,
  `plan1(picks, P, rank)` <= 43k, the block's pack and write) leaves at least 28k.
- **Your bot's own draft memory must stay below offset 512.** The mapintel block lives at 512-863 (352 bytes, checksummed); a shorter
  write of your bytes from offset 0 keeps it (tested). Bytes 864-1023 are not used by the library.

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
  the battery's `games.csv` and the map dumps). Output: `mapintel_dl_<UTC stamp>.tar.gz` (report, metrics, weights, out-of-fold heat
  maps; ~2-5 MB). Upload it.
- What it trains (each against the step-6 model on the same held-out maps): T1a opening targets, T1b a body's next target (behaviour
  cloning of the top teams), T2 champion values per map (on the roster battery), T3 heat maps (where the top teams farm, fight, capture,
  die: a U-Net, research only). Small MLPs are exported to `cpp/mapintel/dl_weights.h` only when they beat the step-6 bar
  (`dl/dl_export.py`; `test_library.py --dl-weights` checks them in the engine: rankings equal Python exactly, fuel measured).
- Options: `--tasks t1a,t1b,t2,t3`, `--seeds N`, `--hidden H` (exported MLP width: fuel grows with it), `--cpu`.

## The C++ library (`cpp/mapintel/`): how a bot uses it

Header-only C++20 on the SDK alone; copy `cpp/mapintel/` into your bot's `src/` (so `src/mapintel/*.h`) and include what you use.
Regenerate the data headers after a new ladder download or catalog: `python3 -I tools/mapintel/draft_learn.py && python3 -I
tools/mapintel/export_headers.py`; after a battery of your bot (its archive has `battery/games.csv`), make the draft values yours:
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
| `dl_weights.h` | generated by `dl/dl_export.py` only when a step-7 model beats step 6: `dl_inputs()`, `dl_opening_scores()`, `dl_next_scores(..., &candidates)` (about 1,600 fuel a group: score a candidate list in game turns), `dl_champion_values()` | LEARNED / SIMULATED |

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
| `draft_learn.py` | step 6, draft: per-map prior (`maps/catalog/draft_prior.json`), the draft win models on the ladder (no signal over rating) and on a roster battery (`--battery`) | LEARNED / SIMULATED |
| `first_targets.py` | step 6, opening: which groups the top teams capture first (logistic and boosted forest, leave-maps-out) | LEARNED |
| `validate_ladder.py` | 3C: the model against the top teams (pace, first targets, bank altars); `maps/catalog/behaviour.json` | LEARNED |
| `export_headers.py` | generates `known_maps.h` and `model_weights.h` (with `group_features()`, the 22 per-group inputs of the step-6 / step-7 models) | - |
| `dl/make_dataset.py` | step 7 data: map tensors, group features, opening / next-target / roster / heat samples, the step-6 baselines (`dl_data/`) | COMPUTED + LEARNED + SIMULATED |
| `dl/dl_train.py`, `dl/run_dl.sh` | step 7 training (torch; laptop GPU): MLP, group-graph attention, distillation, U-Net; leave-maps-out | LEARNED / SIMULATED |
| `dl/dl_ref.py`, `dl/dl_export.py` | the exported models' Python reference (same evaluation order as the C++) and the header generator | - |
| `battery_games.py` | a battery archive -> `games.csv` (rosters from the kept statistics) for `draft_learn.py --battery` | SIMULATED |
| `replays.py` | ladder replays -> per-game summaries (captures, banks, deaths, standing tiles) | LEARNED |
| `replay_tracks.py` | ladder replays -> per-game tracks (positions, health, bags, gold, camp health per round, events; `mapintel_work/tracks/`) | LEARNED |
| `econ_learn.py` | the economy model's constants (retreat, heal, bank bag, shop gold, gold weight, damage scale, opposition share) measured / fitted on the replays; `economy.econ()` reads `experiments/results/mapintel/economy/constants.json` | LEARNED |
| `plan1_learn.py` | plan 1 against the top teams' openings per kit class (held out); writes the table's first targets (`experiments/results/mapintel/plan1/table_first.json`) | LEARNED |
| `heat_features.py` | the U-Net's out-of-fold heat maps -> per-group / per-bank-route fight and death densities; tested on plans 3 and 4 (no gain: not in the table) | LEARNED |
| `plan4_learn.py`, `p4model.py` | plan 4's thresholds from the top teams' decisions (abandon, regroup, bank abort, respawn wait); `p4model.py` = `model_weights.h` `p4_thresholds()` | LEARNED |
| `cpp/probe/`, `cpp/idle/` | probe bot and idle opponent sources (fresh, from the 3.0.5 starter) | - |
| `../../experiments/results/mapintel/dump/` | `<map>.txt` runtime dumps and `fingerprints.txt` | COMPUTED |
