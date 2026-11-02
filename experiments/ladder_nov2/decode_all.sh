#!/bin/bash
cd /home/claude/cambridge_battlecode/experiments/ladder_nov2
python3 - <<'PY'
import json
ME='5a103c90-b00b-4d46-8ace-6a3bb058dc72'
rows=[json.loads(l) for l in open('matches_me.jsonl')]
info={m['matchId']:m for m in rows}
sides={}
import os
for f in os.listdir('replays'):
    mid=f[:-8]; m=info.get(mid)
    if not m: continue
    me=[t for t in m['teams'] if t['teamId']==ME][0]
    sides[mid]=0 if me['side']=='a' else 1
json.dump(sides, open('sides.json','w'))
PY
for f in replays/*.repl26a; do b=$(basename $f .repl26a); [ -s dec/$b.json ] || node ../../tools/replay/decode.mjs $f --gold-captures --out dec/$b.json 2>/dev/null; done
python3 - <<'PY'
import json, os, shutil
rows=[json.loads(l) for l in open('matches_me.jsonl')]
info={m['matchId']:m for m in rows}
for f in os.listdir('dec'):
    mid=f[:-5]; m=info.get(mid)
    if not m: continue
    src='/home/claude/data/mapjson_pool/'+m['map']+'.json'
    if os.path.exists(src): shutil.copy(src, 'mj/'+f)
    else: print('no mapjson', m['map'])
PY
echo DECODED $(ls dec | wc -l)
