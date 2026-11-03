#!/usr/bin/env python3
"""Ward placement per side: wards a game, share on a bush tile ('"' in the map JSON rows), share within Chebyshev 8 of the side's own
spawn tiles; v95 games (this folder) vs v88 games (ladder_nov2/dec, the execution stream's v88 list). Usage: python3 -I wards.py"""
import json, glob, os
from collections import defaultdict
ROOT = '/home/claude/cambridge_battlecode'
V95 = f'{ROOT}/experiments/deep_research_nov3/v95'
L2 = f'{ROOT}/experiments/ladder_nov2'
T30 = f'{ROOT}/experiments/top30_nov3'


def side_stats(dec, mjp, t):
    d = json.load(open(dec))
    mj = json.load(open(mjp))
    rows = mj['rows']
    sp = [tuple(p) for p in (mj['spawnA'] if t == 0 else mj['spawnB'])]
    passable = sum(1 for r in rows for c in r if c not in '#o')
    bush = sum(1 for r in rows for c in r if c == '"')
    n = nb = ns = 0
    for e in d['events']:
        if e['k'] != 'Place ward' or e.get('team') != t:
            continue
        x, y = e['to']
        n += 1
        nb += rows[y][x] == '"'
        ns += min(max(abs(x - a), abs(y - b)) for a, b in sp) <= 8
    return n, nb, ns, bush / max(1, passable)


def run(items, label):
    agg = defaultdict(lambda: [0, 0, 0, 0])
    for dec, mjp, we, res in items:
        try:
            for who, t in (('we', we), ('opp', 1 - we)):
                n, nb, ns, bf = side_stats(dec, mjp, t)
                for k in (who, f'{who}|{"bushy" if bf >= 0.06 else "other"}', f'{who}|{res}'):
                    a = agg[k]
                    a[0] += 1
                    a[1] += n
                    a[2] += nb
                    a[3] += ns
        except (OSError, KeyError, IndexError, ValueError):
            continue
    for k in sorted(agg):
        g, n, nb, ns = agg[k]
        print(f'{label:4s} {k:12s} games {g:4d}  wards/g {n / g:6.1f}  on bush {nb / max(1, n):.2f}  near own spawn (cheb<=8) {ns / max(1, n):.2f}')


v95 = []
for p in glob.glob(f'{V95}/out/g/*.json'):
    r = json.load(open(p))
    gi = r['info']
    if gi['ver'] != 'v95':
        continue
    v95.append((f"{V95}/dec/{gi['mid']}.json", f"{V95}/mj/{gi['mid']}.json", gi['we'], gi['res']))
v88 = []
for p in glob.glob(f'{T30}/execution/out/met/*.json'):
    m = json.load(open(p))
    if m['tag'] != 'v88':
        continue
    mid = m['mid']
    if os.path.exists(f'{L2}/dec/{mid}.json') and os.path.exists(f'{L2}/mj/{mid}.json'):
        v88.append((f'{L2}/dec/{mid}.json', f'{L2}/mj/{mid}.json', m['we'], 'W' if m['winner'] == m['we'] else 'L'))
run(v95, 'v95')
run(v88, 'v88')
