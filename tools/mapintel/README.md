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

## Files

| path | what | origin |
|---|---|---|
| `fetch_ladder.sh`, `ladder_fetch.py` | ladder download (laptop) | - |
| `run_battery.sh`, `battery.py` | simulation batteries for any bot (laptop) | - |
| `battery_rosters.py`, `data/battery_rosters.json` | candidate rosters per map for the roster battery | LEARNED + COMPUTED |
| `dump_maps.py` | runtime dump of maps through the probe bot (`cpp/probe`) | COMPUTED |
| `engine.py` | engine facts parsed from the engine probe's output (`experiments/results/probe_v3_0_5/engine_3_0_5.txt`) | COMPUTED |
| `cpp/mapintel/` | the header-only C++ library a bot includes (`fingerprint.h`, `force_roster.h`; more in step 8) | - |
| `cpp/probe/`, `cpp/idle/` | probe bot and idle opponent sources (fresh, from the 3.0.5 starter) | - |
| `../../experiments/results/mapintel/dump/` | `<map>.txt` runtime dumps and `fingerprints.txt` | COMPUTED |
