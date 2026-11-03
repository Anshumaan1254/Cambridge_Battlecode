#!/usr/bin/env python3
"""Bag behaviour per side: long carries (>= 20 gems for >= 150 consecutive alive rounds without a submit, map_fail 'bag' episode),
walking away from the nearest altar while carrying >= 40 (share of moving body-rounds; Chebyshev to the nearest altar tile),
gems carried at the end; and r2000 losses where banked + carried beat the winner (X2). v95 (this folder) vs v88 (ladder_nov2/dec,
execution-stream v88 list). Decoded rounds[].ch = [index, team, type, x, y, hp, maxhp, alive, gems, gold, ?, items].
Usage: python3 -I bags.py"""
import json, glob, os
from collections import defaultdict
ROOT = '/home/claude/cambridge_battlecode'
V95 = f'{ROOT}/experiments/deep_research_nov3/v95'
L2 = f'{ROOT}/experiments/ladder_nov2'
T30 = f'{ROOT}/experiments/top30_nov3'


def game(dec, mjp, we, res):
    d = json.load(open(dec))
    mj = json.load(open(mjp))
    rows = mj['rows']
    altars = [(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == 'A']
    subr = defaultdict(set)
    for e in d['events']:
        if e['k'] == 'Submit gems' and e.get('who') is not None:
            subr[e['who']].add(e['r'])
    team = {b['index']: b['team'] for b in d['meta']['bodies']}
    out = {}
    for t in (0, 1):
        run = defaultdict(int)
        eps = 0
        away = moves40 = 0
        prev = {}
        last = None
        for rr in d['rounds'][1:]:
            r = rr['r']
            for c in rr['ch']:
                b = c[0]
                if team.get(b) != t:
                    continue
                alive, gems, pos = c[7], c[8], (c[3], c[4])
                if alive and gems >= 20 and r not in subr[b]:
                    run[b] += 1
                    if run[b] == 150:
                        eps += 1
                else:
                    run[b] = 0
                if alive and gems >= 40 and b in prev and prev[b] != pos and altars:
                    da = min(max(abs(pos[0] - a[0]), abs(pos[1] - a[1])) for a in altars)
                    db = min(max(abs(prev[b][0] - a[0]), abs(prev[b][1] - a[1])) for a in altars)
                    moves40 += 1
                    away += da > db
                prev[b] = pos
            last = rr
        carried = sum(c[8] for c in last['ch'] if team.get(c[0]) == t and c[7]) if last else 0
        out[t] = {'eps': eps, 'away': away, 'moves40': moves40, 'carried': carried}
    sub = d['meta']['submitted']
    final = d['meta']['finalRound']
    x2 = res == 'L' and final >= 1999 and sub[we] + out[we]['carried'] > sub[1 - we]
    return out, final >= 1999, x2


def run(items, label):
    A = defaultdict(lambda: [0, 0, 0, 0, 0])
    n2000 = nx2 = nl = 0
    for dec, mjp, we, res in items:
        try:
            o, at2000, x2 = game(dec, mjp, we, res)
        except (OSError, KeyError, ValueError, IndexError):
            continue
        if res == 'L':
            nl += 1
            n2000 += at2000
            nx2 += x2
        for who, t in (('we', we), ('opp', 1 - we)):
            for k in (who, f'{who}|{res}'):
                a = A[k]
                a[0] += 1
                a[1] += o[t]['eps']
                a[2] += o[t]['away']
                a[3] += o[t]['moves40']
                a[4] += o[t]['carried']
    for k in sorted(A):
        g, e, aw, mv, ca = A[k]
        print(f'{label} {k:8s} games {g:4d}  long carries (>=20 gems, 150+ r)/g {e / g:.2f}  away-from-altar share of bag>=40 moves {aw / max(1, mv):.2f} (n {mv})  carried at end {ca / g:.0f}')
    print(f'{label} losses {nl}: reached r2000 {n2000} ({n2000 / max(1, nl):.0%}); banked+carried > winner {nx2}')


v95 = []
for p in glob.glob(f'{V95}/out/g/*.json'):
    gi = json.load(open(p))['info']
    if gi['ver'] == 'v95':
        v95.append((f"{V95}/dec/{gi['mid']}.json", f"{V95}/mj/{gi['mid']}.json", gi['we'], gi['res']))
v88 = []
for p in glob.glob(f'{T30}/execution/out/met/*.json'):
    m = json.load(open(p))
    if m['tag'] == 'v88' and os.path.exists(f"{L2}/dec/{m['mid']}.json") and os.path.exists(f"{L2}/mj/{m['mid']}.json"):
        v88.append((f"{L2}/dec/{m['mid']}.json", f"{L2}/mj/{m['mid']}.json", m['we'], 'W' if m['winner'] == m['we'] else 'L'))
run(v95, 'v95')
run(v88, 'v88')
