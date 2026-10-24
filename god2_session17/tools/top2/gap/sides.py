# gap_g8 step 0: game table for the S0 games (g8 = HouseOfCoders vs prism best girl / IFish / Claudus Maximus).
# Reads C:/battlecode/cache/t2/s0/index.jsonl, writes C:/battlecode/cache/gap_g8/sides.json:
#   { "<map>_<matchId8>": {set, names[side a, side b], ours (0|1 = engine team index), opp, res[a, b], map, match, draft[a, b], end} }
# The engine team index 0 = platform side 'a'.   python tools/top2/gap/sides.py
import json, os
SRC = 'C:/battlecode/cache/t2/s0/index.jsonl'
OUT = 'C:/battlecode/cache/gap_g8/sides.json'
US = 'HouseOfCoders'
out = {}
for l in open(SRC, encoding='utf-8'):
    r = json.loads(l)
    t = {x['side']: x for x in r['teams']}
    a, b = t['a'], t['b']
    ours = 0 if a['name'] == US else 1
    name = '%s_%s' % (r['map'], r['matchId'][:8])
    out[name] = {'set': 's0', 'names': [a['name'], b['name']], 'ours': ours, 'opp': (b if ours == 0 else a)['name'],
                 'res': [a['result'], b['result']], 'map': r['map'], 'match': r['matchId'],
                 'draft': [a['draftPicks'], b['draftPicks']], 'end': r['endReason']}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, 'w', encoding='utf-8'))
print(len(out), 'games ->', OUT)
