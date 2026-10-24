# Sides file for the fights study (tools/top2/fights): for every study team key, map each dump name <map>_<matchId8> to the study
# team's index (0 = side a), its result, the opponent's name, both drafts. Also writes a small map geometry file (altars, spawns,
# walking distances from both spawns, terrain grid) from the an_strategy map geometry dump.
#   python tools/top2/fights/mk_sides.py OUTDIR
import json, os, sys

KEYS = {'pbg': 'prism best girl', 'ifish': 'Intercontinental Fish', 'cm': 'Claudus Maximus', 'pantheon': 'Pantheon',
        'coo': 'conqueror_of_openai', 'nyx': 'Nyx'}
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
sides = {}
for k, name in KEYS.items():
    p = f'C:/battlecode/cache/t2/{k}/index.jsonl'
    if not os.path.exists(p):
        continue
    for l in open(p, encoding='utf-8'):
        d = json.loads(l)
        me = [t for t in d['teams'] if t['name'] == name]
        ot = [t for t in d['teams'] if t['name'] != name]
        if not me or not ot:
            continue
        me, ot = me[0], ot[0]
        fn = f"{d['map']}_{d['matchId'][:8]}"
        sides.setdefault(k, {})[fn] = {
            'st': 0 if me['side'] == 'a' else 1, 'win': 1 if me['result'] == 'win' else 0, 'opp': ot['name'], 'map': d['map'],
            'match': d['matchId'], 'at': d['createdAt'], 'draft': [me['draftPicks'], ot['draftPicks']], 'end': d.get('endReason')}
json.dump(sides, open(os.path.join(out, 'sides.json'), 'w', encoding='utf-8'))
geo = {}
for l in open('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', encoding='utf-8'):
    d = json.loads(l)
    geo[d['map']] = {k: d[k] for k in ('W', 'H', 'grid', 'spawnA', 'spawnB', 'dA', 'dB', 'altars')}
json.dump(geo, open(os.path.join(out, 'geo.json'), 'w', encoding='utf-8'))
print({k: len(v) for k, v in sides.items()}, len(geo))
