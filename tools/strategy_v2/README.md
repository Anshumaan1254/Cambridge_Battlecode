# tools/strategy_v2

Scripts behind `docs/strategy_v2/`. They read replays (ours and the ladder's), measure what the strategy docs cite,
and give the tests in `docs/strategy_v2/05_TEST_AND_SHIP_PLAN.md`.

Requirements: `node` (22+), `python3` with `numpy` and `scikit-learn` (only `fight_model.py` needs them), and the
engine wasm that `cambc view` unpacks once into `~/.cache/cambc/assets/` (run `cambc view some_replay.repl26a` and
stop it with Ctrl-C). Run everything from the repo root.

## From downloaded match groups to the report (one command)

```bash
python3 tools/strategy_v2/run_all.py /tmp/top3 match-group-*.zip
# -> /tmp/top3/report.md (KPI tables), /tmp/top3/out/*.csv, /tmp/top3/dmg/*.json, /tmp/top3/replays/
```

Input: the website's match-group zips (a zip of five match zips), single match zips, folders of them, or `.repl26a`
files. Each replay is named `<group>_<NN>_<official map>` (the map is found by comparing the replay's map with
`maps/comp/`). Team 0 must be our bot (side A), which is how our downloads come.

## The scripts

| Script | What it does |
|---|---|
| `decode_dmg.mjs` | `tools/replay/decode.mjs` plus a `dmg` list: every health change of every champion and camp at every step, tied to who did it. `node tools/strategy_v2/decode_dmg.mjs R.repl26a --out R.json --rollovers` |
| `analyze.py` | tables per team, body, fight, death, recall, bank, capture and camp-group kill. `python3 -I tools/strategy_v2/analyze.py DMG_DIR mapgeo.json OUT_DIR` (`run_all.py` writes `mapgeo.json`) |
| `report.py` | the markdown report: results, camp-gem decomposition, items, per champion, farming, respawn wait, fights, hit-back, deaths, KPIs. `python3 -I tools/strategy_v2/report.py OUT_DIR/analysis.json DMG_DIR [mapgeo.json]` |
| `trace.py` | round-by-round view of a window: positions, health, actions, damage. `python3 -I tools/strategy_v2/trace.py DMG.json R0 R1 [X Y RADIUS]` |
| `fight_model.py` | how well start-of-fight numbers predict the outcome (AUC, logistic regression, small tree, grouped by match) |
| `map_plan.py` | the draft-time planner prototype: groups, map type, k-medoids zones, DBSCAN hubs, champion assignment, circuits, draft-memory size. Input: map dumps from `node tools/replay/mapinfo.mjs maps/comp/X.map26a > X.txt` |
| `pacesum.py` | summary of unopposed pace runs (`bench.py BOT idle`): mean rounds to 1,000 per map, per-champion gold and gems |
| `h2hsum.py` | head-to-head summary counting each distinct game once (skips `maps/ladder` copies) |

## Definitions (same as in the docs)

- Fight: champion-on-champion hits within 3 rounds and 8 tiles of each other, joined (single-linkage clustering);
  only fights with 4+ hits are counted.
- Home / neutral / enemy side: by walking distance from the two spawns, with a 3-tile neutral band.
- Activity label per body-round, first match wins: dead, recalling, banking, any champion damage dealt or taken
  ("fight"), any camp damage dealt or taken ("camp"), standing on a dead camp tile, on spawn, moved, idle.
- Gold earned: every increase of gold plus what was spent on items between two round snapshots.
- Damage stat: strength for Varg, Issac, Ryth, Vendetta, Marcella, Vesper; focus for the others.
