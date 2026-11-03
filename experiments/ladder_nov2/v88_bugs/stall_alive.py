#!/usr/bin/env python3
"""Stalls (map_fail/stall.py, from out/det) classified by the nearest camp group within 5 at the stall start: alive (a live camp the
body never hits) / respawning / none; and enemy within 6.   python3 v88_bugs/stall_alive.py [v88L|old_L]"""
import json, glob, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h88, mapgroups  # noqa: E402,E401
which = sys.argv[1] if len(sys.argv) > 1 else 'v88L'
rows = [json.load(open(f)) for f in glob.glob(f'{h88.V}/out/det/*.json')]
if which == 'v88L':
    rows = [r for r in rows if r['ver'] == 'v88' and r['res'] == 'L']
else:
    rows = [r for r in rows if r['kind'] == 'ranked' and r['ver'] != 'v88' and r['res'] == 'L']
agg = Counter()
ex = []
for r in rows:
    if not r['stall']:
        continue
    d = json.load(open(f"{h88.BASE}/dec/{r['mid']}.json"))
    mj = json.load(open(f"{h88.BASE}/mj/{r['mid']}.json"))
    G = mapgroups.full_groups(r['map'], d['meta'], mj['sym'])
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    for s in r['stall']:
        p = tuple(s['at'])
        best = None
        for gg in G:
            dd = min(max(abs(p[0] - t[0]), abs(p[1] - t[1])) for t in gg['tiles'])
            if dd <= 5 and (best is None or dd < best[0]):
                best = (dd, gg)
        rr = R.get(s['r'])
        if best is None or rr is None:
            st = 'none'
        else:
            hp = sum(rr['campHp'][i] for i in best[1]['idx'])
            st = 'alive' if hp > 0 else ('reward' if rr['gr'][best[1]['id']] else 'resp')
        en = 'enemy<=6' if (s['enemy_d'] or 99) <= 6 else 'free'
        agg[(s['side'], st, en)] += s['len']
        if s['side'] == 'we' and st == 'alive' and en == 'free':
            ex.append((s['len'], r['mid'][:8], r['map'], s['b'], s['champ'], s['r'], p, best[0], ''.join(t[0] for t in best[1]['types']), best[1]['gems'], best[1]['gold']))
n = len(rows)
print(which, n, 'games; stalled body-rounds per game by nearest group state / enemy')
for side in ('we', 'they'):
    print(' ', side, {f'{k[1]}/{k[2]}': round(v / n, 1) for k, v in sorted(agg.items()) if k[0] == side})
print('  ours next to a live group, no enemy within 6 (len, mid, map, body, champ, r, at, dist, types, gems, gold):')
for x in sorted(ex, reverse=True)[:25]:
    print('   ', x)
