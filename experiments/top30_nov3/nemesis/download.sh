#!/bin/bash
# download + decode the selected games (ours vs nemesis / easy teams) into ladder_nov2/replays + dec + mj.
# The platform rate-limits downloads (HTTP 429, "retry after N seconds") and the top-30 fetcher runs in parallel with 3 jobs:
# honour the named wait (+1 s), up to 60 tries per file. Order = selection_ordered.json (nemesis losses first, round robin).
cd /home/claude/cambridge_battlecode/experiments
LIST=${1:-top30_nov3/nemesis/selection_ordered.json}
python3 -I -c "
import json
for s in json.load(open('$LIST')):
    print(s['mid'], s['map'])
" | while read mid map; do
  f=ladder_nov2/replays/$mid.repl26a
  for try in $(seq 1 60); do
    [ -s $f ] && break
    out=$(cambc matches download $mid -o $f 2>&1) && break
    rm -f $f
    w=$(echo "$out" | grep -o "after [0-9]* seconds" | grep -o "[0-9]*")
    sleep $(( ${w:-1} + 1 ))
  done
  [ -s $f ] || echo "FAIL $mid"
  if [ -s $f ] && [ ! -s ladder_nov2/dec/$mid.json ]; then
    node ../tools/replay/decode.mjs $f --gold-captures --out ladder_nov2/dec/$mid.json 2>/dev/null
    [ -f /home/claude/data/mapjson_pool/$map.json ] && cp /home/claude/data/mapjson_pool/$map.json ladder_nov2/mj/$mid.json
    echo "OK $mid $(date -u +%H:%M:%S)"
  fi
done
echo DL_DONE $(ls ladder_nov2/dec | wc -l)
