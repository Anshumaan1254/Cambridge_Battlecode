# The draft-model refit of GOD v10 (Oct 21, engine 3.0.4)

- `games_tr2.jsonl.xz`: 17,004 games, one per line (`cell`, `map`, `side`, `ours`, `theirs` = the two rosters, `win`, `rounds`), every kept
  game of the 156 tuning maps (`experiments/pools/train156.csv`): v8, the dynamic-draft screens and round robins (`tools/draftmodel/dataset.py
  OUT --pool experiments/pools/train156.csv KEEP_DIRS...`). No game of the 152 held-out maps is in it.
- `mapfeat.json`: the map features the draft reads (FEAT lines of a `LEGEND_FEATURES` build, one 1-round game per map).

Reproduce GOD v10's `pd_w_*` exactly:

```bash
xz -dk experiments/results/draftfit_v10/games_tr2.jsonl.xz
python3 -I tools/draftmodel/fit2.py experiments/results/draftfit_v10/games_tr2.jsonl experiments/results/probe_v3_0_4/champions_engine_3_0_4.txt \
  experiments/results/draftfit_v10/mapfeat.json --no-counter --drop hp_x_mono,basic_x_mono,spell_x_mono,area_x_mono --export
# -> 5-fold leave-maps-out log loss 0.6283, accuracy 0.642; the pd_w_* line in bots/god/src/params.h
```
