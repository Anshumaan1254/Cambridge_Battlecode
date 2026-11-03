#!/usr/bin/env python3
"""v95's paired games (12:45-12:46 groups) matched to experiments/ladder_nov2/paired_c10.json rows (same opponent, maps, sides):
results of v95 vs the v84 ('old'), v85 ... v94 columns on the same games; flips and a sign test; per-map-class split.
Usage: python3 -I paired.py"""
import json, math
from collections import defaultdict, Counter
ROOT = '/home/claude/cambridge_battlecode'
V95 = f'{ROOT}/experiments/deep_research_nov3/v95'
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
plan = json.load(open(f'{ROOT}/experiments/ladder_nov2/paired_c10.json'))
ms = [json.loads(l) for l in open(f'{V95}/all_recent.jsonl')]
ms = [m for m in ms if '2026-11-03T12:45:05' <= m['createdAt'] < '2026-11-03T12:46:30' and m['kind'] == 'unranked']
groups = defaultdict(list)
for m in ms:
    groups[m['groupId']].append(m)


def binom_p(k, n):
    """two-sided sign test"""
    if n == 0:
        return 1.0
    c = [math.comb(n, i) / 2 ** n for i in range(n + 1)]
    pk = c[k]
    return min(1.0, sum(x for x in c if x <= pk + 1e-12))


cols = ['old', 'v85', 'v86', 'v87', 'v88', 'v89', 'v90', 'v91', 'v92', 'v94']
rows = []
used = set()
for gid, gm in groups.items():
    opp = [t for t in gm[0]['teams'] if t['teamId'] != ME][0]
    gm.sort(key=lambda m: m['position'])
    maps = [m['map'] for m in gm]
    best = None
    for i, p in enumerate(plan):
        if i in used or p['oppId'] != opp['teamId']:
            continue
        if sorted(p['maps']) == sorted(maps):
            best = i
            break
    if best is None:
        print('unmatched group', gid[:8], opp['name'], maps)
        continue
    used.add(best)
    p = plan[best]
    for m in gm:
        us = [t for t in m['teams'] if t['teamId'] == ME][0]
        k = p['maps'].index(m['map'])
        side_ok = (p['sides'][k] == us['side'])
        r = {'opp': opp['name'], 'map': m['map'], 'side_ok': side_ok, 'v95': us['result']}
        for c in cols:
            if p.get(c) and len(p[c]) > k:
                r[c] = p[c][k]
        rows.append(r)
print('paired games matched:', len(rows), 'groups', len(used), 'side mismatches', sum(1 for r in rows if not r['side_ok']))
print(f"v95 wins {sum(r['v95'] == 'win' for r in rows)}/{len(rows)}")
for c in cols:
    rr = [r for r in rows if r.get(c) in ('win', 'loss')]
    if not rr:
        continue
    lw = sum(1 for r in rr if r[c] == 'loss' and r['v95'] == 'win')
    wl = sum(1 for r in rr if r[c] == 'win' and r['v95'] == 'loss')
    print(f"vs {c:4s}: n {len(rr):3d}  {c} {sum(r[c] == 'win' for r in rr):3d} wins, v95 {sum(r['v95'] == 'win' for r in rr):3d}; flips L->W {lw:2d} W->L {wl:2d} net {lw - wl:+d} p {binom_p(min(lw, wl), lw + wl):.2f}")
# per map class (gems per champion <= 92 = scarce) using the map JSON pool
pool = '/home/claude/data/mapjson_pool'
gpc = {}
for r in rows:
    if r['map'] in gpc:
        continue
    try:
        mj = json.load(open(f"{pool}/{r['map']}.json"))
        gpc[r['map']] = mj
    except OSError:
        gpc[r['map']] = None
print('\nby opponent (v95 vs v88 vs v94 wins on the same games):')
by = defaultdict(lambda: [0, 0, 0, 0])
for r in rows:
    b = by[r['opp']]
    b[0] += 1
    b[1] += r['v95'] == 'win'
    b[2] += r.get('v88') == 'win'
    b[3] += r.get('v94') == 'win'
for k, b in sorted(by.items(), key=lambda kv: kv[1][1] - kv[1][2]):
    print(f'  {k:24s} n {b[0]:2d}  v95 {b[1]}  v88 {b[2]}  v94 {b[3]}')
json.dump(rows, open(f'{V95}/out/paired_rows.json', 'w'))
