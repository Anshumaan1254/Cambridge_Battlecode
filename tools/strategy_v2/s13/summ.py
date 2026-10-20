import json, subprocess, hashlib, glob, os, sys
sys.path.insert(0, 'tools/strategy_v2')
import run_all
D = sys.argv[1]
off = run_all.official_maps()
idx = json.load(open(os.path.join(D, 'index.json')))
files = [os.path.join(D, r['file']) for r in idx]
OUT = '/tmp/claude-0/-home-user-Cambridge-Battlecode/814bb573-3b54-57d0-a5c4-7b41cf5c5bd2/scratchpad/meta.json'
subprocess.run(['node', '/tmp/claude-0/-home-user-Cambridge-Battlecode/814bb573-3b54-57d0-a5c4-7b41cf5c5bd2/scratchpad/meta.mjs'] + files, env=dict(os.environ, OUT=OUT), check=True, capture_output=True)
meta = {m['file']: m for m in json.load(open(OUT))}
rows = []
for r in idx:
    f = os.path.join(D, r['file'])
    dump = run_all.map_dump(f)
    h = hashlib.md5('\n'.join(dump.splitlines()[1:]).encode()).hexdigest()
    mp = off.get(h, 'unknown:' + dump.splitlines()[0][:30])
    m = meta[r['file']]
    us = 0 if r['side'] == 'A' else 1
    rows.append(dict(r, map=mp, rounds=m['r'], us_draft=m['drafts'][us], them_draft=m['drafts'][1-us], outcome=m['outcome']))
json.dump(rows, open(os.path.join(D, 'index.json'), 'w'), indent=1)
for x in rows: print(x['group'], x['nn'], x['side'], x['map'], x['rounds'], x['outcome'], 'US', ','.join(x['us_draft']), '| THEM', ','.join(x['them_draft']))
