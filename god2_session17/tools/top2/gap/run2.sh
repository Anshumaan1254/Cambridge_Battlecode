#!/usr/bin/env bash
# gap_g8 pipeline, second batch (after run_all.sh): re-extract gapx (team first-bank fix) and the dump-based behaviour scripts.
#   bash tools/top2/gap/run2.sh
set -e
cd /c/battlecode/Cambridge_Battlecode
export PYTHONIOENCODING=utf-8
C=C:/battlecode/cache/gap_g8
D=C:/battlecode/cache/t2dump/s0
rm -f $C/gapx.jsonl
python tools/live/par.py 3 $C/gapx.jsonl tools/top2/gap/gapx.mjs -- $C/dec/*.json.gz
python tools/live/par.py 3 $C/campdps.jsonl tools/top2/gap/campdps.mjs -- $D/*.json.gz
python tools/live/par.py 3 $C/chanpunish.jsonl tools/top2/gap/chanpunish.mjs -- $D/*.json.gz
python tools/live/par.py 3 $C/nearbehav.jsonl tools/top2/gap/nearbehav.mjs -- $D/*.json.gz
python tools/live/par.py 3 $C/lifetimes.jsonl tools/top2/gap/lifetimes.mjs -- $D/*.json.gz
echo RUN2_DONE
