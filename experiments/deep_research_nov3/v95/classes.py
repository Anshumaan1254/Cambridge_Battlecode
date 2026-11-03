#!/usr/bin/env python3
"""v95 vs v88 / v94 / v84 on the same paired games (out/paired_rows.json) split by map class (execution/out/map_table.tsv:
scarce = gems/champs <= 92, bushy = bush_frac >= 0.06, worst10 = the 10 worst ranked maps of god24_plan, small = passable < 1600).
Usage: python3 -I classes.py"""
import json, csv
from collections import defaultdict
ROOT = '/home/claude/cambridge_battlecode'
V95 = f'{ROOT}/experiments/deep_research_nov3/v95'
T = {r['map']: r for r in csv.DictReader(open(f'{ROOT}/experiments/top30_nov3/execution/out/map_table.tsv'), delimiter='\t')}
WORST = {'00crater', '01elk_arena', '03ambush_field', '00gemfight', '00oasis', '01islands', '00rushbait_v2', '00quarry', '00elkring', '00gem_fields'}
rows = json.load(open(f'{V95}/out/paired_rows.json'))


def classes(m):
    t = T.get(m)
    if not t:
        return ['unknown']
    out = ['scarce' if float(t['gems']) / float(t['champs']) <= 92 else 'rich', 'bushy' if float(t['bush_frac']) >= 0.06 else 'not-bushy',
           'small' if float(t['passable']) < 1600 else 'not-small', ('mono' if int(t['monoliths']) > 0 else 'no-mono')]
    if m in WORST:
        out.append('worst10')
    return out


agg = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for r in rows:
    for c in classes(r['map']) + ['all']:
        for v in ('v95', 'v88', 'v94', 'old'):
            if r.get(v) in ('win', 'loss'):
                agg[c][v][0] += 1
                agg[c][v][1] += r[v] == 'win'
print('class        ' + ''.join(f'{v:>14s}' for v in ('v95', 'v88', 'v94', 'v84(old)')))
for c in ('all', 'scarce', 'rich', 'worst10', 'small', 'not-small', 'bushy', 'not-bushy', 'mono', 'no-mono', 'unknown'):
    if c not in agg:
        continue
    print(f'{c:12s} ' + ''.join(f"{agg[c][v][1]:5d}/{agg[c][v][0]:<4d}{100 * agg[c][v][1] / max(1, agg[c][v][0]):3.0f}%" for v in ('v95', 'v88', 'v94', 'old')))
