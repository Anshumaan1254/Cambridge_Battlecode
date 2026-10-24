# Sanity checks: index sides vs dump outcome, spawn tiles vs initial body positions, capture extraction on decoded games.
import sys, os
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
from vlib import *

idx = load_index()
geo = load_geo()
print('distinct matches', len(idx), 'multi-key', sum(1 for e in idx.values() if len(e['keys']) > 1))
bad = Counter()
n = 0
for b, e in sorted(idx.items()):
    g = Game(b, e, geo)
    n += 1
    out = g.fd['meta']['outcome']
    w = g.win
    if (out == 1 and w != 0) or (out == 2 and w != 1):
        bad['outcome'] += 1
    if g.geo is None:
        bad['nogeo:' + g.map] += 1
        continue
    s0 = g.R[min(g.R)]
    for body, st in s0.items():
        t = g.team[body]
        x, y = st[0], st[1]
        dmin = min(cheb((x, y), p) for p in g.geo['spawn'][t])
        if dmin > 1:
            bad['spawn_far'] += 1
    if g.vd is not None:
        caps = g.captures()
        tot = sum(sum(v[1] for v in c['gains'].values()) for c in caps)
        cg = sum(ev['gems'] for ev in g.fd['ev'] if ev['k'] == 'CaptureGems')
        if tot != cg:
            bad['capgems_mismatch'] += 1
        if any(c['team'] is None for c in caps):
            bad['cap_team_none'] += 1
        bad['vd_games'] += 1
    if n >= 120:
        break
print(n, dict(bad))
