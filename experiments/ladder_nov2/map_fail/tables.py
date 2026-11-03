#!/usr/bin/env python3
"""Markdown tables for REPORT.md from out/games.jsonl, deaths.jsonl, passive.jsonl, cycles.jsonl.  python3 -I map_fail/tables.py"""
import json
from collections import Counter, defaultdict
B = '/home/claude/cambridge_battlecode/experiments/ladder_nov2/map_fail/out'
G = [json.loads(l) for l in open(f'{B}/games.jsonl')]
D = [json.loads(l) for l in open(f'{B}/deaths.jsonl')]
P = [json.loads(l) for l in open(f'{B}/passive.jsonl')]
C = [json.loads(l) for l in open(f'{B}/cycles.jsonl')]
maps = ['00crater', '00gem_fields', '00gemfight', '01elk_arena', '01islands', '00quarry', '00oasis', '01corridors']
mean = lambda xs: sum(xs) / len(xs) if xs else float('nan')
print('| map | games (W-L) | banked we/they r200 | r400 | r600 | r800 | final | collected | lost on death | decided (loser 150+ behind for good) |')
print('|---|---|---|---|---|---|---|---|---|---|')
for m in maps:
    gs = [g for g in G if g['map'] == m]
    L = [g for g in gs if g['res'] == 'L']
    w = len(gs) - len(L)
    f = lambda key, r: f"{mean([g['tl'][r][key + '_we'] for g in L]):.0f}/{mean([g['tl'][r][key + '_they'] for g in L]):.0f}"
    print(f"| {m} | {len(gs)} ({w}-{len(L)}) | {f('bank', '200')} | {f('bank', '400')} | {f('bank', '600')} | {f('bank', '800')} | {f('bank', 'final')} | {f('col', 'final')} | {f('lost', 'final')} | r{mean([g['behind150'] for g in L]):.0f} (min r{min(g['behind150'] for g in L)}) |")
print()
print('| map | deaths/game we/they | by camp | champion kill with camp hits in last 5 | ctx (ours): fight / caught / farm-jumped / camp | where (own/mid/their) | most deaths near | passive camp dmg/game we/they | big-group cycles we opened -> they took |')
print('|---|---|---|---|---|---|---|---|---|')
for m in maps:
    gs = [g for g in G if g['map'] == m]
    n = len(gs)
    dw = [d for d in D if d['map'] == m and d['side'] == 'we']
    dt = [d for d in D if d['map'] == m and d['side'] == 'they']
    ctx = Counter(d['ctx'] for d in dw)
    band = Counter(d['band'] for d in dw)
    grp = Counter(d['group'] for d in dw if d['group'] is not None).most_common(1)
    gg = {x['id']: x for x in gs[0]['groups']}
    near = f"G{grp[0][0]} ({gg[grp[0][0]]['gems']}g {gg[grp[0][0]]['types']}) {grp[0][1]}" if grp else '-'
    pw = sum(p['dmg'] for p in P if p['map'] == m and p['side'] == 'we') / n
    pt = sum(p['dmg'] for p in P if p['map'] == m and p['side'] == 'they') / n
    cs = [c for c in C if c['map'] == m and c['first_hit'] == 'we']
    print(f"| {m} | {len(dw) / n:.1f}/{len(dt) / n:.1f} | {sum(1 for d in dw if d['killer'] == 'camp') / n:.1f}/{sum(1 for d in dt if d['killer'] == 'camp') / n:.1f} "
          f"| {sum(1 for d in dw if d['killer'] != 'camp' and d['camp_hits5'] > 0) / n:.1f}/{sum(1 for d in dt if d['killer'] != 'camp' and d['camp_hits5'] > 0) / n:.1f} "
          f"| {ctx['fight'] + ctx['farm+fight']} / {ctx['caught']} / {ctx['farm->jumped']} / {ctx['camp']} | {band['own']}/{band['mid']}/{band['their']} | {near} "
          f"| {pw:.0f}/{pt:.0f} | {sum(1 for c in cs if c['by'] == 'they')}/{len(cs)} |")
