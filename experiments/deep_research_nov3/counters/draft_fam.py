#!/usr/bin/env python3
"""Roster-family matchup matrix, top-30 vs top-30 games in matches_current.jsonl, BT-adjusted (h2h.json).
Family = first match of: C&I, Willow, Prism, Varg, Tavi/Ren, no-Marcella, Std (Marcella + Vesper/Vendetta/Ryth/HoR only).
Usage: nice -n 19 python3 -I draft_fam.py -> out/draft_fam.txt"""
import json
from collections import defaultdict
BASE = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
OUT = '/home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out'
lad = json.load(open(f'{BASE}/ladder.json'))['teams']
rank = {t['teamId']: t['rank'] for t in lad}
bt = json.load(open(f'{OUT}/h2h.json'))['bt']
BT = {t['teamId']: bt.get(t['name'], t['rating']) for t in lad}
def fam(d):
    s = set(d)
    if 3 in s: return 'C&I'
    if 7 in s: return 'Willow'
    if 5 in s: return 'Prism'
    if 9 in s: return 'Varg'
    if 10 in s or 8 in s: return 'Tavi/Ren'
    if 6 not in s: return 'noMarc'
    return 'Std'
F = ['C&I', 'Willow', 'Prism', 'Varg', 'Tavi/Ren', 'noMarc', 'Std']
M = defaultdict(lambda: [0, 0, 0.0])
for l in open(f'{BASE}/matches_current.jsonl'):
    m = json.loads(l)
    a, b = m['teams']
    if rank.get(a['teamId'], 99) > 30 or rank.get(b['teamId'], 99) > 30 or a['result'] == b['result']:
        continue
    for x, y in ((a, b), (b, a)):
        e = 1 / (1 + 10 ** ((BT[y['teamId']] - BT[x['teamId']]) / 400))
        k = (fam(x['draftPicks']), fam(y['draftPicks']))
        M[k][0] += x['result'] == 'win'
        M[k][1] += 1
        M[k][2] += e
out = ['row family vs column family: W/N (wins - BT expected); cells n >= 15']
out.append(' ' * 10 + ''.join(f'{c:>20}' for c in F))
for r in F:
    cells = []
    for c in F:
        w, n, e = M[(r, c)]
        cells.append(f'{w:>5}/{n:<4}({w - e:+5.1f})' if n >= 15 and r != c else ' ' * 20 if r != c else f'{"mirror " + str(n):>20}')
    out.append(f'{r:10}' + ''.join(f'{x:>20}' for x in cells))
tot = defaultdict(lambda: [0, 0, 0.0])
for (r, c), (w, n, e) in M.items():
    if r != c:
        tot[r][0] += w; tot[r][1] += n; tot[r][2] += e
out.append('family totals (non-mirror): ' + '; '.join(f'{r} {w}/{n} ({w - e:+.1f})' for r, (w, n, e) in tot.items()))
open(f'{OUT}/draft_fam.txt', 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
