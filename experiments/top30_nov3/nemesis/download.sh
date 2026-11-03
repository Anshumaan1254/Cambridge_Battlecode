#!/bin/bash
# download + decode the selected games (ours vs nemesis / easy teams) into ladder_nov2/replays + dec + mj.
# The platform rate-limits downloads (HTTP 429) and the top-30 fetcher runs in parallel: poll every 0.5 s, up to 150 tries.
cd /home/claude/cambridge_battlecode/experiments
LIST=${1:-top30_nov3/nemesis/selection.json}
python3 -I -c "
import json
for s in json.load(open('$LIST')):
    print(s['mid'], s['map'])
" | while read mid map; do
  f=ladder_nov2/replays/$mid.repl26a
  for try in $(seq 1 150); do
    [ -s $f ] && break
    cambc matches download $mid -o $f >/dev/null 2>&1 || { rm -f $f; sleep 0.5; }
  done
  [ -s $f ] || echo "FAIL $mid"
  if [ -s $f ] && [ ! -s ladder_nov2/dec/$mid.json ]; then
    node ../tools/replay/decode.mjs $f --gold-captures --out ladder_nov2/dec/$mid.json 2>/dev/null
    [ -f /home/claude/data/mapjson_pool/$map.json ] && cp /home/claude/data/mapjson_pool/$map.json ladder_nov2/mj/$mid.json
    echo "OK $mid $(date -u +%H:%M:%S)"
  fi
done
echo DL_DONE $(ls ladder_nov2/dec | wc -l)
