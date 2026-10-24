"""verify_items C4: cast share of ready slots on camp turns under two definitions:
   A) the body damaged a camp this turn (any action, the cast itself included)   B) it damaged a camp in the previous 2 rounds.
   python tools/top2/verify_items/vcamp.py KEY   (study team KEY, S bodies only, fight / enemy-near turns excluded)"""
import json, gzip, sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from vlib import groups

KIT = {'Ryth': (0,), 'Marcella': (1,), 'Prism': (0, 1), 'Cassi': (0,), 'Tavi': (1,), 'VesperVale': (0,), 'HeartOfRuin': (1,)}
key = sys.argv[1]
G = groups()
cnt = collections.defaultdict(lambda: [0, 0, 0, 0])
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
for x in G[key]:
    p = f'C:/battlecode/cache/t2dump/{key}/{x["base"]}.json.gz'
    if not os.path.exists(p): continue
    d = json.load(gzip.open(p))
    team = {b['index']: b['team'] for b in d['meta']['bodies']}; typ = {b['index']: b['type'] for b in d['meta']['bodies']}
    R = {}
    for row in d['R']: R[row[0]] = {c[0]: c for c in row[3]}
    camp = collections.defaultdict(set)
    for q, r, a, ci, amt in d['cdmg']: camp[a].add(r)
    fight = collections.defaultdict(set)
    for q, r, a, v, amt, kind, slot in d['dmg']:
        if a >= 0 and team.get(a) != team.get(v): fight[a].add(r); fight[v].add(r)
    casts = collections.defaultdict(dict)
    for e in d['ev']:
        if e['k'] == 'Cast ability': casts[e['who']].setdefault((e['r'], e['slot']), 1)
    for b in team:
        if team[b] != x['S'] or typ[b] not in KIT: continue
        for s in KIT[typ[b]]:
            last = -99
            for r in range(2, d['meta']['finalRound'] + 1):
                cp, cn = R.get(r - 1, {}).get(b), R.get(r, {}).get(b)
                if not cp or not cn or not cp[5]:
                    last = -99; continue
                did = (r, s) in casts[b]
                ready = r - last >= 8 and not cp[9]
                if did: last = r
                if not ready: continue
                if fight[b] & {r - 2, r - 1, r}: continue
                if any(team[o] != team[b] and c[5] and cheb((cp[1], cp[2]), (c[1], c[2])) <= 5 for o, c in R[r - 1].items()): continue
                k = (typ[b], s)
                if r in camp[b]: cnt[k][0] += 1; cnt[k][1] += did
                if camp[b] & {r - 1, r - 2}: cnt[k][2] += 1; cnt[k][3] += did
for k, v in sorted(cnt.items()):
    print(f"{key} {k}: A camp damage this turn: {v[1]}/{v[0]} = {100*v[1]/max(1,v[0]):.0f}% | B camp damage in r-1/r-2: {v[3]}/{v[2]} = {100*v[3]/max(1,v[2]):.0f}%")
