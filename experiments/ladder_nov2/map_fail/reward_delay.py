#!/usr/bin/env python3
"""Kill -> capture delay of groups killed by each team (kill = the round all camps of the group are dead; killer team = the team whose
bodies hit the group in the 3 rounds before). Capture = the CaptureGems/CaptureGold event (gems arrive 6 rounds after stepping on).
Rounds 1-300 kills.   python3 -I map_fail/reward_delay.py [map ...] > map_fail/out/reward_delay.txt"""
import json, sys
from collections import Counter, defaultdict
BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
sys.path.insert(0, f'{BASE}/map_fail')
from mapgroups import full_groups
from analyze import select
MAPS = sys.argv[1:] or ['00crater', '00gemfight', '01elk_arena', '00gem_fields', '00quarry']
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
agg = defaultdict(list)
ex = defaultdict(list)
for g in select(MAPS):
    mid, we = g['mid'], g['we']
    d = json.load(open(f'{BASE}/dec/{mid}.json')); mj = json.load(open(f'{BASE}/mj/{mid}.json'))
    G = full_groups(g['map'], d['meta'], mj['sym'])
    team = {b['index']: b['team'] for b in d['meta']['bodies']}
    types = {b['index']: b['type'] for b in d['meta']['bodies']}
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    tile_group = {t: gg['id'] for gg in G for t in gg['tiles']}
    camp_at = {(c['x'], c['y']) for c in d['meta']['camps']}
    hits = defaultdict(list)
    caps = defaultdict(list)
    for e in d['events']:
        if e['r'] > 420:
            break
        if e['k'] == 'Attack' and e.get('who') is not None and tuple(e['to']) in tile_group:
            hits[tile_group[tuple(e['to'])]].append((e['r'], e['team'], e['who']))
        elif e['k'] == 'Cast ability' and e.get('who') is not None and 'to' in e and e.get('ability') != 6:
            P = tuple(e['to'])
            for q in camp_at:
                if cheb(q, P) <= (1 if e.get('ability') == 3 else 0) and q in tile_group:
                    hits[tile_group[q]].append((e['r'], e['team'], e['who']))
        elif e['k'] in ('CaptureGems', 'CaptureGold'):
            caps[tile_group.get(tuple(e['at']))].append((e['r'], e['team'], e['who'], e['gems'], e['gold']))
    for gg in G:
        prev = False
        for r in range(1, 301):
            rr = R.get(r)
            if rr is None:
                continue
            dead = all(rr['campHp'][i] == 0 for i in gg['idx'])
            if dead and not prev:
                hs = [h for h in hits[gg['id']] if r - 3 <= h[0] <= r]
                if hs:
                    kt = Counter(h[1] for h in hs).most_common(1)[0][0]
                    killers = sorted({h[2] for h in hs if h[1] == kt})
                    cs = [c for c in caps[gg['id']] if c[0] >= r]
                    c0 = cs[0] if cs else None
                    delay = (c0[0] - 6 - r) if c0 else None
                    side = 'we' if kt == we else 'they'
                    by = None if c0 is None else ('same' if c0[1] == kt else 'other')
                    # bodies of the killer team within 5 of the group at kill + 3
                    s3 = S.get(r + 3, {})
                    near = sorted(i for i, c in s3.items() if c[7] and team[i] == kt and min(cheb((c[3], c[4]), t) for t in gg['tiles']) <= 5)
                    agg[(g['map'], side)].append((delay, by, gg['gems'] + gg['gold']))
                    if side == 'we' and (delay is None or delay > 8):
                        ex[g['map']].append(f"{mid[:8]} G{gg['id']}({gg['gems']}g/{gg['gold']}$) killed r{r} by {[(k, types[k][:4]) for k in killers]} -> captured "
                                            + (f"r{c0[0]} by {'us' if c0[1] == we else 'THEM'} b{c0[2]} {types[c0[2]][:4]} (step-on delay {delay})" if c0 else 'never (by r420)')
                                            + f" | our bodies within 5 at kill+3: {[(k, types[k][:4]) for k in near]}")
            prev = dead
for m in MAPS:
    print(f'== {m}')
    for side in ('we', 'they'):
        xs = agg[(m, side)]
        if not xs:
            continue
        dl = [x[0] for x in xs if x[0] is not None]
        print(f"  {side:4} kills {len(xs):3}  step-on delay: <=1 {sum(1 for x in dl if x <= 1):3}  2-8 {sum(1 for x in dl if 2 <= x <= 8):3}  9-30 {sum(1 for x in dl if 9 <= x <= 30):3}  >30 {sum(1 for x in dl if x > 30):3}"
              f"  never {sum(1 for x in xs if x[0] is None):3} | captured by the other team {sum(1 for x in xs if x[1] == 'other'):3} | mean delay {sum(dl) / max(1, len(dl)):.1f}")
    for line in ex[m][:12]:
        print('     ', line)
