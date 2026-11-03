#!/bin/bash
# Download + decode the ranked replays listed in map_fail/to_download.txt (read-only CLI), exactly as decode_all.sh decodes.
cd /home/claude/cambridge_battlecode/experiments/ladder_nov2
for id in $(cat map_fail/to_download.txt); do
  [ -s replays/$id.repl26a ] || timeout 120 cambc matches download $id -o replays/$id.repl26a >/dev/null 2>&1 || echo "DL FAIL $id"
  [ -s dec/$id.json ] || nice -n 19 node ../../tools/replay/decode.mjs replays/$id.repl26a --gold-captures --out dec/$id.json 2>/dev/null || echo "DEC FAIL $id"
done
python3 - <<'PY'
import json, os, shutil
rows=[json.loads(l) for l in open('matches_me.jsonl')]
info={m['matchId']:m for m in rows}
for mid in open('map_fail/to_download.txt').read().split():
    m=info[mid]
    src='/home/claude/data/mapjson_pool/'+m['map']+'.json'
    if os.path.exists(src):
        if not os.path.exists('mj/'+mid+'.json'): shutil.copy(src, 'mj/'+mid+'.json')
    else: print('no mapjson', m['map'])
PY
echo DONE $(ls dec | wc -l)
