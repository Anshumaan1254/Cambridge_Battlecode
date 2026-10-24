#!/usr/bin/env bash
# Narrate selected losses (an_weak) with tools/live/narrate.mjs; args: KEY FILE_STEM... (stem = <map>_<mid8>); output to cache/an_weak/narr/
# Study team index from the replay's index.jsonl (side a = 0). Runs 3 at a time.
export CAMBC_CACHE="C:/Users/Anjali Gupta/AppData/Local/cambc/assets"
key=$1; shift
for stem in "$@"; do
  mid=${stem##*_}
  side=$(grep "\"matchId\": \"$mid" C:/battlecode/cache/t2/$key/index.jsonl | python -c "import sys,json; r=json.loads(sys.stdin.read()); print([t['side'] for t in r['teams'] if t['teamId'].startswith({'pbg':'38e6d8c4','ifish':'1890540d','cm':'ad5474c2','pantheon':'547efb5b','coo':'1570a113','nyx':'6f7fd199'}['$key'])][0])")
  us=0; [ "$side" = "b" ] && us=1
  ( node tools/live/narrate.mjs C:/battlecode/cache/t2/$key/$stem.repl26a $us 100 > C:/battlecode/cache/an_weak/narr/${key}_$stem.txt 2>&1 ) &
  while [ $(jobs -r | wc -l) -ge 3 ]; do sleep 1; done
done
wait
