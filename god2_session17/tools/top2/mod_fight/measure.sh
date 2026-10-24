#!/usr/bin/env bash
# mod_fight: behaviour measurement of a local bench (tools/live/localbench.py A B --tag TAG): fight dumps, then the gap_g8 dump scripts
# (nearbehav: actions with an enemy within 8 and arrivals at farmers; fightan: engagements, deaths by mode), then agg.py.
#   bash tools/top2/mod_fight/measure.sh TAG A B      (3 node workers; outputs in C:/battlecode/cache/modfight/TAG/)
set -e
cd /c/battlecode/Cambridge_Battlecode
export PYTHONIOENCODING=utf-8
export CAMBC_CACHE="C:/Users/Anjali Gupta/AppData/Local/cambc/assets"
TAG=$1; A=$2; B=$3
BEN=C:/battlecode/cache/bench/$TAG
O=C:/battlecode/cache/modfight/$TAG
mkdir -p $O/dump
python tools/top2/mod_fight/sides_bench.py $BEN $O/sides.json $A $B
python tools/live/par.py 3 $O/dump.jsonl tools/live/fightdump.mjs $O/dump -- $BEN/*.repl26a
rm -f $O/nearbehav.jsonl
python tools/live/par.py 3 $O/nearbehav.jsonl tools/top2/gap/nearbehav.mjs -- $O/dump/*.json.gz
python tools/live/par.py 3 $O/fightan.jsonl tools/live/fightan.mjs $O/sides.json -- $O/dump/*.json.gz
python tools/top2/mod_fight/agg.py $O
