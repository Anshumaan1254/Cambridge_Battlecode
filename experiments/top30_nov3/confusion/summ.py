#!/usr/bin/env python3
"""Summaries of confusion/out/fl/*.json.  python3 -I confusion/summ.py > confusion/out/summary.txt"""
import json, os, glob
from collections import Counter, defaultdict

OUT = '/home/claude/cambridge_battlecode/experiments/top30_nov3/confusion/out'
CL = ['ENEMY6', 'ENEMY12', 'CAMPAGGRO', 'RECALL', 'BAG', 'LOWHP', 'SPAWN', 'DEADGRP', 'LIVEGRP', 'OPEN', 'FIGHT']
ACT = ['dead', 'walk', 'walk_bag', 'camp', 'fight', 'capture', 'bank', 'recall', 'spawn', 'wait']
TYPES = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']

rows = [json.load(open(f)) for f in glob.glob(f'{OUT}/fl/*.json')]
groups = defaultdict(list)   # name -> [(row, side)]
for o in rows:
    if o['tag'] == 'top':
        if o['winner'] is None:
            continue
        groups['top_W'].append((o, str(o['winner'])))
        groups['top_L'].append((o, str(1 - o['winner'])))
    else:
        we = o['we']
        tag = 'v88' if o['tag'] == 'v88' else 'old'
        res = 'W' if o['winner'] == we else 'L'
        groups[f'we_{tag}'].append((o, str(we)))
        groups[f'opp_{tag}'].append((o, str(1 - we)))
        groups[f'we_{tag}_{res}'].append((o, str(we)))
ORDER = ['we_v88', 'we_v88_L', 'opp_v88', 'top_W', 'top_L', 'we_old', 'opp_old']
print('n side-games:', {k: len(groups[k]) for k in ORDER})
print('\nWASTED ROUNDS per game (rounds inside non-productive return loops), by class at the loop start; [per 1000 alive body-rounds]')
print(f"{'class':10s}" + ''.join(f'{k:>20s}' for k in ORDER))
tot = {}
for cl in CL + ['ALL_noFIGHT']:
    line = f'{cl:10s}'
    for k in ORDER:
        G = groups[k]
        if not G:
            line += f"{'-':>20s}"
            continue
        al = sum(o['sides'][s]['alive'] for o, s in G)
        if cl == 'ALL_noFIGHT':
            v = sum(sum(x for c, x in o['sides'][s]['lost'].items() if c != 'FIGHT') for o, s in G)
        else:
            v = sum(o['sides'][s]['lost'].get(cl, 0) for o, s in G)
        line += f'{v / len(G):11.1f} [{1000 * v / max(1, al):5.1f}]'
    print(line)
print('\nEPISODES per game by class')
for cl in CL:
    line = f'{cl:10s}'
    for k in ORDER:
        G = groups[k]
        v = sum(o['sides'][s]['ep'].get(cl, 0) for o, s in G)
        line += f'{v / max(1, len(G)):20.1f}'
    print(line)
print('\nalive body-rounds per game: ' + '  '.join(f"{k} {sum(o['sides'][s]['alive'] for o, s in groups[k]) / max(1, len(groups[k])):.0f}" for k in ORDER))
print('held recalls cancelled per game: ' + '  '.join(f"{k} {sum(o['sides'][s]['held_cancel'] for o, s in groups[k]) / max(1, len(groups[k])):.1f}" for k in ORDER))

# map-matched: v88 vs top on the same maps (per map mean, then mean over maps present in both)
print('\nMAP-MATCHED (maps with >=1 we_v88 game and >=2 top sides): wasted rounds per 1000 alive body-rounds, mean over maps')
bym = defaultdict(lambda: defaultdict(list))
for k in ('we_v88', 'opp_v88', 'top_W', 'top_L'):
    for o, s in groups[k]:
        bym[o['map']][k].append((o, s))
maps = [m for m in bym if bym[m]['we_v88'] and len(bym[m]['top_W']) + len(bym[m]['top_L']) >= 2]
print('maps:', len(maps))
for cl in CL + ['ALL_noFIGHT']:
    line = f'{cl:10s}'
    for k in ('we_v88', 'opp_v88', 'top_W', 'top_L'):
        vals = []
        for m in maps:
            G = bym[m][k]
            if not G:
                continue
            al = sum(o['sides'][s]['alive'] for o, s in G)
            if cl == 'ALL_noFIGHT':
                v = sum(sum(x for c, x in o['sides'][s]['lost'].items() if c != 'FIGHT') for o, s in G)
            else:
                v = sum(o['sides'][s]['lost'].get(cl, 0) for o, s in G)
            vals.append(1000 * v / max(1, al))
        line += f'{k:>9s} {sum(vals) / max(1, len(vals)):6.1f}'
    print(line)

# per champion
print('\nPER CHAMPION TIME BUDGET: share of all body-rounds (incl. dead) by activity; n = body-games')
CMP = ['we_v88', 'we_old', 'top_W', 'top_L']
for ty in TYPES:
    print(f'-- {ty}')
    for k in CMP:
        acc = Counter()
        n = 0
        for o, s in groups[k]:
            a = o['sides'][s]['act'].get(ty)
            if a:
                acc.update(a)
                n += o['sides'][s]['types'].get(ty, 1)
        if n == 0:
            continue
        T = sum(acc.values())
        print(f'   {k:7s} n={n:4d} ' + ' '.join(f'{a}={100 * acc[a] / T:4.1f}' for a in ACT))
print('\nPER CHAMPION CAMP HITS: share of its camp hits on big(>40) / mid / small(<=12) / gold / contested (enemy hit within 30) / solo (no ally hit within 8); hits per game')
for ty in TYPES:
    print(f'-- {ty}')
    for k in CMP:
        acc = Counter()
        n = 0
        for o, s in groups[k]:
            a = o['sides'][s]['gh'].get(ty)
            if o['sides'][s]['types'].get(ty):
                n += o['sides'][s]['types'][ty]
            if a:
                acc.update(a)
        if n == 0:
            continue
        T = max(1, acc['all'])
        print(f'   {k:7s} n={n:4d} hits/g={acc["all"] / n:6.1f} ' + ' '.join(f'{a}={100 * acc[a] / T:4.1f}' for a in ('big', 'mid', 'small', 'gold', 'contested', 'solo')))
print('\nPER CHAMPION CAPTURES / BANKS / OPENS / DEATHS: share of team captured gems, captures/g, share of team banked gems, banks/g, opener of a '
      'fight /g, opened on /g, deaths /g')
for ty in TYPES:
    print(f'-- {ty}')
    for k in CMP:
        cg = tg = bg = tb = cn = bn = op = opd = de = 0
        n = 0
        for o, s in groups[k]:
            sd = o['sides'][s]
            if not sd['types'].get(ty):
                continue
            n += 1
            cg += sd['cap'].get(ty, {}).get('gems', 0)
            cn += sd['cap'].get(ty, {}).get('n', 0)
            tg += sd['cap'].get('_team', {}).get('gems', 0)
            bg += sd['bank'].get(ty, {}).get('gems', 0)
            bn += sd['bank'].get(ty, {}).get('n', 0)
            tb += sd['bank'].get('_team', {}).get('gems', 0)
            op += sd['open'].get(ty, 0)
            opd += sd['opened'].get(ty, 0)
            de += sd['deaths'].get(ty, 0)
        if n == 0:
            continue
        print(f'   {k:7s} n={n:4d} capshare={100 * cg / max(1, tg):4.1f}% caps/g={cn / n:4.1f} capgems/g={cg / n:5.1f} bankshare={100 * bg / max(1, tb):4.1f}% '
              f'banks/g={bn / n:4.1f} bank/g={bg / n:5.1f} open/g={op / n:4.2f} opened/g={opd / n:4.2f} deaths/g={de / n:4.2f}')
