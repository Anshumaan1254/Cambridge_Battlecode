#!/bin/bash
# decode replays as they arrive (idempotent); map JSON copied next to each decode
cd /home/claude/cambridge_battlecode/experiments/top30_nov3
python3 - <<'PY'
import json
rows=[json.loads(l) for l in open('matches_current.jsonl')]
json.dump({m['matchId']: m['map'] for m in rows}, open('id2map.json','w'))
PY
while true; do
  n=0
  for f in replays/*.repl26a; do
    [ -e "$f" ] || continue
    b=$(basename $f .repl26a)
    if [ ! -s dec/$b.json ]; then
      node ../../tools/replay/decode.mjs $f --gold-captures --out dec/$b.json 2>/dev/null && n=$((n+1))
      m=$(python3 -c "import json;print(json.load(open('id2map.json')).get('$b',''))")
      [ -n "$m" ] && [ -f /home/claude/data/mapjson_pool/$m.json ] && cp /home/claude/data/mapjson_pool/$m.json mj/$b.json
    fi
  done
  echo "$(date -u +%H:%M) decoded $n new; total $(ls dec | wc -l)"
  if ! pgrep -f "ladder_fetch.py" >/dev/null && [ $n -eq 0 ]; then echo DECODE_DONE; break; fi
  sleep 30
done
