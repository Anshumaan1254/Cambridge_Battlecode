#!/usr/bin/env python3
"""Orphaned rewards: groups our team (and theirs) killed in rounds 1-300 whose reward nobody of the killer team stepped on within 8
rounds. For each: the killing hit (attack or spell, attacker, distance to the camp), what the killer did next, the delay until the
capture and who took it.  python3 -I map_fail/orphan_kills.py [map ...] > map_fail/out/orphan_kills.txt"""
import json, sys
from collections import Counter, defaultdict
BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
sys.path.insert(0, f'{BASE}/map_fail')
from mapgroups import full_groups
from analyze import select
LIM = 14
MAPS = sys.argv[1:] or ['00crater', '00gemfight', '01elk_arena', '00gem_fields', '00quarry']
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
tot = defaultdict(Counter)
lines = defaultdict(list)
for g in select(MAPS):
    mid, we = g['mid'], g['we']
    d = json.load(open(f'{BASE}/dec/{mid}.json')); mj = json.load(open(f'{BASE}/mj/{mid}.json'))
    G = full_groups(g['map'], d['meta'], mj['sym'])
    team = {b['index']: b['team'] for b in d['meta']['bodies']}
    types = {b['index']: b['type'] for b in d['meta']['bodies']}
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    tile_group = {t: gg['id'] for gg in G for t in gg['tiles']}
    hits = defaultdict(list)
    caps = defaultdict(list)
    for e in d['events']:
        if e['r'] > 420:
            break
        if e.get('who') is not None and e['k'] in ('Attack', 'Cast ability') and 'to' in e and e.get('ability') != 6:
            P = tuple(e['to'])
            rad = 1 if e.get('ability') == 3 else 0
            for q, gid in tile_group.items():
                if cheb(q, P) <= rad:
                    pc = S.get(e['r'] - 1, {}).get(e['who'])
                    dist = cheb((pc[3], pc[4]), q) if pc else None
                    hits[gid].append((e['r'], e['team'], e['who'], 'spell' if e['k'] == 'Cast ability' else 'atk', dist))
        elif e['k'] in ('CaptureGems', 'CaptureGold'):
            caps[tile_group.get(tuple(e['at']))].append((e['r'], e['team'], e['who']))
    for gg in G:
        prev = False
        for r in range(1, 301):
            rr = R.get(r)
            if rr is None:
                continue
            dead = all(rr['campHp'][i] == 0 for i in gg['idx'])
            if dead and not prev:
                hs = [h for h in hits[gg['id']] if r - 1 <= h[0] <= r]
                if hs:
                    last = hs[-1]
                    kt = last[1]
                    side = 'we' if kt == we else 'they'
                    cs = [c for c in caps[gg['id']] if c[0] >= r]
                    c0 = cs[0] if cs else None
                    delay = (c0[0] - 6 - r) if c0 else 999
                    tot[(g['map'], side)]['kills'] += 1
                    if delay > 8:
                        tot[(g['map'], side)]['orphan'] += 1
                        tot[(g['map'], side)]['orphan_rounds'] += min(delay, 300)
                        tot[(g['map'], side)]['orphan_gems'] += gg['gems']
                        tot[(g['map'], side)][f'orphan_by_{last[3]}{"4+" if (last[4] or 0) >= 4 else ""}'] += 1
                        if c0 is None or c0[1] != kt:
                            tot[(g['map'], side)]['lost_to_other_or_never'] += 1
                        if side == 'we':
                            lines[g['map']].append(f"{mid[:8]} G{gg['id']} ({gg['gems']}g/{gg['gold']}$, {len(gg['tiles'])} camp) killed r{r} by b{last[2]} {types[last[2]][:4]} {last[3]} from d{last[4]}"
                                                   f" -> step-on +{delay if delay < 999 else 'never'}" + (f" by {'us' if c0[1] == we else 'THEM'} b{c0[2]}" if c0 else ''))
            prev = dead
print(__doc__)
for m in MAPS:
    print(f'== {m}')
    for side in ('we', 'they'):
        t = tot[(m, side)]
        print(f"  {side:4} kills {t['kills']:3}  orphaned (no step-on within 8) {t['orphan']:3} ({100 * t['orphan'] / max(1, t['kills']):.0f}%)  their gems {t['orphan_gems']:4}  frozen rounds {t['orphan_rounds']:5}"
              f"  never/other team {t['lost_to_other_or_never']:3} | killing hit: spell from 4+ {t['orphan_by_spell4+']:3}, spell closer {t['orphan_by_spell']:3}, attack {t['orphan_by_atk'] + t['orphan_by_atk4+']:3}")
    for l in lines[m][:LIM]:
        print('     ', l)
