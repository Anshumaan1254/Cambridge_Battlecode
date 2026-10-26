"""Index of our decoded ranked replays (engine 2.0.0) for icx.games(): {path: {map, ours, res, opp, set, match}}.
   set = the live version at match creation: v17 (v73), v18i (v74), v18 (v75), v19 (v76).
    python3 -I rk_index.py ranked_me.jsonl /tmp/claude-0/rk/dec OUT.json"""
import json, os, sys, gzip
DRAFT = ['Ryth', 'VesperVale', 'Vendetta', 'CassiAndIssac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']


def ver(t):
    if t < '2026-10-26T10:41': return 'v17'
    if t < '2026-10-26T11:41': return 'v18i'
    if t < '2026-10-26T12:00': return 'v18'
    return 'v19'


idx = {}
bad = 0
for l in open(sys.argv[1]):
    m = json.loads(l)
    me = [t for t in m['teams'] if t['name'] == 'HouseOfCoders'][0]
    op = [t for t in m['teams'] if t['name'] != 'HouseOfCoders'][0]
    if me.get('engineVersion') != '2.0.0':
        continue
    p = os.path.join(sys.argv[2], m['matchId'] + '.json.gz')
    if not os.path.exists(p):
        continue
    ours = 0 if me['side'] == 'a' else 1
    res = [None, None]
    res[ours] = me['result']; res[1 - ours] = op['result']
    idx[p] = {'map': m['map'], 'ours': ours, 'res': res, 'opp': op['name'], 'set': ver(m['createdAt']), 'match': m['matchId'],
              'our_draft': [DRAFT[int(c)] for c in me['draftPicks']], 'opp_draft': [DRAFT[int(c)] for c in op['draftPicks']]}
json.dump(idx, open(sys.argv[3], 'w'))
print(len(idx), 'games')
