"""When does each side first show a pack (3+ bodies within 3 tiles of one body) within 12 tiles of the other side's bodies (seen)?
    python3 -I epack.py INDEX [sets]"""
import sys, os, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icx
sets = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
F = collections.defaultdict(list); n = 0; share = collections.defaultdict(list)
for g in icx.games(sys.argv[1], sets):
    n += 1
    first = {}
    cnt = collections.Counter()
    for r in g.rounds:
        if r > 400: break
        s = g.R[r]
        for t in (0, 1):
            mine = [(c[3], c[4]) for c in s['ch'] if c[1] == t and c[7]]
            oth = [(c[3], c[4]) for c in s['ch'] if c[1] != t and c[7]]
            pk = any(sum(1 for q in mine if icx.cheb(p, q) <= 3) >= 3 and any(icx.cheb(p, o) <= 12 for o in oth) for p in mine)
            if pk:
                cnt[t] += 1
                first.setdefault(t, r)
    for t in (0, 1):
        s = icx.who_side(g, t)
        F[(s, g.res)].append(first.get(t, 999))
        share[(s, g.res)].append(cnt[t] / 400)
for k in sorted(F):
    v = F[k]
    print(k, 'games', len(v), 'first seen pack median', st.median(v), 'never', sum(1 for x in v if x == 999), 'share of r<400 rounds', round(st.mean(share[k]), 3))
