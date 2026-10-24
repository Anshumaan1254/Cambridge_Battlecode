import sys, os
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
from vlib import *
idx = load_index(); geo = load_geo()
res = defaultdict(Counter)
for b, e in sorted(idx.items()):
    g = Game(b, e, geo)
    s0 = g.R[min(g.R)]
    for body, st in s0.items():
        t = g.team[body]
        d_own = min(cheb((st[0], st[1]), p) for p in g.geo['spawn'][t])
        d_oth = min(cheb((st[0], st[1]), p) for p in g.geo['spawn'][1 - t])
        res[g.map]['ok' if d_own <= 1 else ('swapped' if d_oth <= 1 else 'far')] += 1
    res[g.map]['r0=%d' % min(g.R)] += 1
for m, c in sorted(res.items()):
    if c['swapped'] or c['far']: print(m, dict(c))
print('maps', len(res))
