#!/usr/bin/env bash
# gap_g8 pipeline over the 239 S0 games (3 node workers at a time; each step resumes: par.py skips files already in its OUT).
#   bash tools/top2/gap/run_all.sh
# 0) python tools/top2/gap/sides.py ; python tools/top2/gap/compact_agg.py      (platform summaries, no node)
# 1) decode cache:  par.py 3 deccache.jsonl tools/top2/gap/deccache.mjs DEC -- replays
# 2) per-game extractors on the cache / on the fight dumps, then the aggregators (python).
set -e
cd /c/battlecode/Cambridge_Battlecode
export PYTHONIOENCODING=utf-8
export CAMBC_CACHE="C:/Users/Anjali Gupta/AppData/Local/cambc/assets"
C=C:/battlecode/cache/gap_g8
python tools/live/par.py 3 $C/deccache.jsonl tools/top2/gap/deccache.mjs $C/dec -- C:/battlecode/cache/t2/s0/*.repl26a
python tools/live/par.py 3 $C/gapx.jsonl tools/top2/gap/gapx.mjs -- $C/dec/*.json.gz
python tools/live/par.py 3 $C/killers.jsonl tools/top2/gap/killers.mjs -- C:/battlecode/cache/t2dump/s0/*.json.gz
python tools/live/par.py 3 $C/fightan.jsonl tools/live/fightan.mjs $C/sides.json -- C:/battlecode/cache/t2dump/s0/*.json.gz
python tools/live/par.py 3 $C/bank.jsonl tools/live/strat_bank.mjs -- C:/battlecode/cache/t2dump/s0/*.json.gz
python tools/live/par.py 3 $C/idleallies.jsonl tools/live/idleallies.mjs $C/sides.json -- C:/battlecode/cache/t2dump/s0/*.json.gz
python tools/live/par.py 3 $C/ff.jsonl tools/live/fightfirst.mjs $C/sides.json -- C:/battlecode/cache/t2dump/s0/*.json.gz
echo ALL_DONE
