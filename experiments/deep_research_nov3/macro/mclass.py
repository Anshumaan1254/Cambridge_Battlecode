#!/usr/bin/env python3
"""Macro features by map class (gem-scarce <=92 group gems per champion vs rich; size; monolith; islands; bushy; altars) for
T5 (ranks 1-5 sides), T20 (ranks 20-30 sides), ME (us v84-v88) and OPP (our opponents, same games). Pooled side means (n sides).
   nice -n 19 python3 -I mclass.py -> mclass_out.txt"""
import json, csv
from collections import defaultdict
T = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
M = '/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro'
lad = {t['teamId']: t['rank'] for t in json.load(open(f'{T}/ladder.json'))['teams']}
MF = {r['map']: r for r in csv.DictReader(open(f'{T}/draft_bank/out/map_features.csv'))}
EX = {}
for l in open(f'{M}/ext/obj_games.jsonl'):
    o = json.loads(l)
    EX.setdefault(o['map'], o['mapcls'])


def cls(m):
    f, e = MF[m], EX.get(m, {})
    return {'scarce': 'scarce' if float(f['gems']) / float(f['champs']) <= 92 else 'rich', 'size': f['size_class'],
            'mono': 'mono' if int(f['mono']) > 0 else 'nomono', 'altars': 'alt1' if int(f['altars']) == 1 else 'alt2+',
            'islands': 'isl' if (e.get('islands') or 0) > 0 else 'noisl', 'bush': 'bushy' if (e.get('bush_frac') or 0) >= 0.15 else 'open'}


S = [json.loads(l) for l in open(f'{M}/fp_sides.jsonl')]
F = ['g300_r', 'pace2_r', 'st_walk', 'c_recall', 'c_fight', 'c_hit', 'b_n_sub', 'big_both_won', 'win']
acc = defaultdict(lambda: defaultdict(list))
for s in S:
    if s['map'] not in MF:
        continue
    g = s['grp']
    if g == 'top':
        r = lad.get(s['tid'], 99)
        g = 'T5' if r <= 5 else 'T20' if r >= 20 else None
    if g is None:
        continue
    for key, v in cls(s['map']).items():
        for k in F:
            x = s['f'].get(k)
            if x is not None:
                acc[(key, v, g)][k].append(x)
with open(f'{M}/mclass_out.txt', 'w') as f:
    print('class value group | ' + ' '.join(f'{k:>12}' for k in F) + '   (mean, n sides)', file=f)
    for (key, v, g) in sorted(acc):
        d = acc[(key, v, g)]
        print(f'{key:7} {v:7} {g:4} | ' + ' '.join(f'{sum(d[k]) / len(d[k]):7.3f}({len(d[k]):3d})' if d[k] else f'{"-":>12}' for k in F), file=f)
print('ok')
