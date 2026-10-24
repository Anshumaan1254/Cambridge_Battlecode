#!/usr/bin/env bash
# gap_g8: print every aggregate table used in experiments/top2/gap_g8.md into C:/battlecode/cache/gap_g8/*.txt (python only, ~1 min).
#   bash tools/top2/gap/tables.sh
set -e
cd /c/battlecode/Cambridge_Battlecode
export PYTHONIOENCODING=utf-8
C=C:/battlecode/cache/gap_g8
python tools/top2/gap/compact_agg.py > $C/compact_agg.txt
python tools/top2/gap/gapx_agg.py $C/gapx.jsonl > $C/gapx_agg.txt
python tools/top2/gap/fight_agg.py $C/fightan.jsonl > $C/fight_agg.txt
python tools/top2/gap/killers_agg.py $C/killers.jsonl > $C/killers_agg.txt
python tools/top2/gap/ff_agg.py $C/ff.jsonl $C/idleallies.jsonl > $C/ff_agg.txt
python tools/top2/gap/chan_near_agg.py $C/chanpunish.jsonl $C/nearbehav.jsonl > $C/chan_near_agg.txt
python tools/top2/gap/lifetimes_agg.py $C/lifetimes.jsonl > $C/lifetimes_agg.txt
python tools/top2/gap/extra_agg.py > $C/extra_agg.txt
echo TABLES_DONE
