# 26: Map refresh for patch 2.0.0: what you run, what you upload, what we do with it

The map model (`tools/mapintel`, `MAPAnalysis.md`) learned from engine-1.0.3 ladder games on the 40 old maps and from GOD v10's roster
battery. Patch 2.0.0 changed the engine (cambc 4.0.0), the champions' numbers and the pool (70 maps in `maps/s3`: the 40 old + 30 new).
This refresh replaces both data sources: current-patch ladder games (LEARNED) and GOD v18's batteries on all 70 maps (SIMULATED), then
the deep-learning run on them. Details of every script: `tools/mapintel/README.md`, section "Laptop scripts".

Before you start:
- The repository path must not contain spaces (Windows: clone into `/c/cambc`, or `subst` / junction: README "Before you start").
- Windows: run everything in **Git Bash**; the scripts find `python3`, `python` or `py -3` themselves. If `cambc` is not found right
  after a pip install, open a new Git Bash window.
- Nothing here submits a bot or changes the team's platform state. Only `cambc login` touches your account, and you type it yourself:
  the scripts never see a password or token. They only read (ladder, match lists, replays).

| step | where | time | upload |
|---|---|---|---|
| (a) update | any machine | 1 min | - |
| (b) ladder | any machine, logged in | 10-25 min | `mapintel_ladder_<stamp>.tar.gz` (+ `.partNN`) |
| (c) batteries for `god18` | the 18-core machine | 20-35 min | `mapintel_battery__mi_v18_<stamp>.tar.gz` (+ `.partNN`) |
| (d) deep learning | the RTX machine, **after our push** | 20-60 min | `mapintel_dl_<stamp>.tar.gz` |

Archives are written to the repository root. Over 20 MB a script also cuts them into `.part00`, `.part01`, ...: upload all the parts.

## (a) Update

```bash
cd /c/cambc/Cambridge_Battlecode        # your clone (a path without spaces)
git pull --no-rebase origin main
python -m pip install cambc==4.0.0      # (b) and (c) also install it when needed
cambc --version                         # cambc 4.0.0
```

## (b) Ladder data of the current patch

```bash
cambc login                             # you, once (the session lasts 7 days)
bash tools/mapintel/fetch_ladder.sh
```

Check the printout:
- at the start: `map pool maps/s3: 70 maps; engine >= 2.0.0; kinds ranked` and `cambc 4.0.0`;
- step 3: `kept N current-patch matches on 70 of the 70 pool maps`;
- step 5: replays per map (up to 15 each, about 1,050 in all). If it names maps with none, or most maps have fewer than 5, run
  `bash tools/mapintel/fetch_ladder.sh --kinds ranked,unranked` (adds match-group games; the lists merge, downloaded replays are
  reused) and upload only the newest archive;
- the last line: `ARCHIVE mapintel_ladder_<stamp>.tar.gz` (about 40-45 MB, so 3 parts). A cut run resumes: run it again.

## (c) Batteries for GOD v18

```bash
bash tools/mapintel/run_battery.sh --from god18 --bot _mi_v18 --quick    # 3-6 min function test
bash tools/mapintel/run_battery.sh --from god18 --bot _mi_v18            # the batteries: 4,340 games
```

- `--from god18` makes `bots/_mi_v18`, a copy of `bots/god18` with the forced-roster call (`bots/god18` is not changed). The quick test
  must print `roster check passed on 6 games` and an `ARCHIVE` line. Do not upload the quick archive.
- The full run plays the **outcome battery** (v18 against itself, an idle bot and the cambc 4.0.0 starter: 70 maps x 2 sides x 3 = 420
  games) and the **roster battery** (8 rosters per map, both teams forced, v18 playing both: 28 pairs x 70 maps x 2 sides = 3,920 games).
  On the 30 new maps all 8 rosters are COMPUTED (balanced over the kit classes) because nobody has ladder data on them yet. On the 40
  old maps 4 rosters are LEARNED (old-patch strong-team drafts) and 4 are COMPUTED.
- 20-35 minutes with 17 jobs. A cut run resumes: run the same command again. The archive is about 100 MB with replays (5 parts). If
  that is too much to upload, run the same command again with `--no-replays`. Every game is reused; only the bot copies (~10 min) and
  the archive are rebuilt, and the archive is about 5 MB. That is enough for (e) and the DL data.
- A `WARNING: the platform's map pool ... differs from maps/s3` line means the pool changed again. Upload anyway and tell us.

## (d) Deep learning on the RTX GPU (after we push the rebuilt dataset)

Today's `dataset.npz` is still the old 40-map one. Run this step after we have rebuilt it from your (b) and (c) uploads and told you it
is pushed:

```bash
git pull --no-rebase origin main
bash tools/mapintel/dl/run_dl.sh --quick    # ~5 min: installs torch (CUDA) once, checks the GPU
bash tools/mapintel/dl/run_dl.sh            # 20-60 min
```

The script first prints `dataset: {...}`. `"maps": 70`, `"t2"` near 3,920 and `GOD v18` mean it is the refreshed dataset; today's line
shows `"maps": 40` and GOD v10. Upload `mapintel_dl_<stamp>.tar.gz`. If the GPU check fails, the script names the fix (driver 570+, `PYTHON="py -3.12" bash ...`).

## (e) What we do with the uploads

| upload | we run | gives |
|---|---|---|
| ladder | join the parts (`cat *.part* > x.tar.gz`), unpack; decode the replays (`tools/replay/decode.mjs` reads the 2.0.0 snapshots) into summaries with `replays.py` (all 70 maps); `draft_learn.py --matches ladder/matches_current.jsonl --teams ladder/teams.json --battery ''` (per-map pick prior, `maps/catalog/draft_prior.json`; the ladder win models); `battery_rosters.py ladder/matches_current.jsonl --teams ladder/teams.json` (LEARNED rosters on all 70 maps for the next battery) | the strong teams' current-patch drafts and openings |
| battery | unpack; `python3 -I tools/mapintel/draft_learn.py --battery-only --battery battery/games.csv --battery-label "GOD v18"` (v18's champion values on 70 maps, leave-maps-out, `weights_sim.json`); `python3 -I tools/mapintel/export_headers.py` (`model_weights.h` `champion_values()`, `known_maps.h`); `python3 -I tools/mapintel/test_library.py` (the library in the engine: values, fuel, both teams) | the draft values from v18's own games on the current engine |
| ladder + battery | `python3 -I tools/mapintel/dl/make_dataset.py --summaries <new summaries> --battery battery/games.csv --battery-label "GOD v18"`, commit `dataset.npz`, tell you to run (d) | the 70-map DL dataset |
| DL | read the report; `dl/dl_export.py` only for models that beat the step-6 bar, `dl/dl_tables.py`, `export_headers.py`, `test_library.py --dl-weights` | DL weights in the library, or the report that they do not help |

`known_maps.h` keeps its exact-match table of the 40 catalog maps. The 30 new maps use the library's unknown-map path (`pick_prior()`,
`champion_values()` from the features) until the catalog is rebuilt over the whole pool. That rebuild is a separate step.
