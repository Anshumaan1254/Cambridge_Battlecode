#!/usr/bin/env python3
"""What our (and their) bodies near a big group do in the 12 rounds after it respawns.
   python3 -I map_fail/respawn_react.py [map ...]   (needs out/cycles.jsonl)
Per cycle with >= 1 of our bodies within 4 at the respawn: for each such body: camp hits, champion hits given/taken, distance to the
group after 6 and 12 rounds, alive, hp at start; and the cycle outcome."""
import json, sys
from collections import Counter, defaultdict
BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
sys.path.insert(0, f'{BASE}/map_fail')
from mapgroups import full_groups
from analyze import select, MAPS
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
maps = sys.argv[1:] or MAPS
cyc = [json.loads(l) for l in open(f'{BASE}/map_fail/out/cycles.jsonl')]
games = {g['mid']: g for g in select(maps)}
summary = defaultdict(Counter)
examples = defaultdict(list)
for mid, g in games.items():
    cs = [c for c in cyc if c['mid'] == mid]
    if not cs:
        continue
    d = json.load(open(f'{BASE}/dec/{mid}.json')); mj = json.load(open(f'{BASE}/mj/{mid}.json'))
    G = full_groups(g['map'], d['meta'], mj['sym'])
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    camp_at = {(c['x'], c['y']) for c in d['meta']['camps']}
    team = {b['index']: b['team'] for b in d['meta']['bodies']}
    types = {b['index']: b['type'] for b in d['meta']['bodies']}
    ev = defaultdict(list)
    for e in d['events']:
        ev[e['r']].append(e)
    we = g['we']
    for c in cs:
        tiles = G[c['gid']]['tiles']
        r0 = c['start']
        s0 = S.get(r0, {})
        near = [b for b, x in s0.items() if x[7] and team[b] == we and min(cheb((x[3], x[4]), t) for t in tiles) <= 4]
        en0 = [b for b, x in s0.items() if x[7] and team[b] != we and min(cheb((x[3], x[4]), t) for t in tiles) <= 6]
        if not near:
            continue
        for b in near:
            ch = cg = ct = 0
            for r in range(r0 + 1, r0 + 13):
                for e in ev.get(r, []):
                    if e.get('who') == b and e['k'] == 'Attack':
                        if tuple(e['to']) in camp_at:
                            ch += 1
                        else:
                            cg += 1
            def dist(r):
                x = S.get(r, {}).get(b)
                if not x or not x[7]:
                    return None
                return min(cheb((x[3], x[4]), t) for t in tiles)
            d6, d12 = dist(r0 + 6), dist(r0 + 12)
            hp = s0[b][5] / max(1, s0[b][6])
            # enemies within 6 of the group at r0+3
            s3 = S.get(r0 + 3, {})
            en3 = sum(1 for bb, x in s3.items() if x[7] and team[bb] != we and min(cheb((x[3], x[4]), t) for t in tiles) <= 6)
            al3 = sum(1 for bb, x in s3.items() if x[7] and team[bb] == we and min(cheb((x[3], x[4]), t) for t in tiles) <= 6)
            beh = ('died' if d12 is None and dist(r0 + 1) is not None and any(e['k'] == 'Death' and e.get('who') == b for r in range(r0, r0 + 13) for e in ev.get(r, [])) else
                   'farmed' if ch >= 3 else 'fought' if cg >= 2 else 'left' if (d12 is None or d12 > 5) else 'stayed-noattack' if ch == 0 else 'farm-little')
            key = (g["map"], c["res"], str(c["by"]))
            summary[key][beh] += 1
            if beh in ('left', 'stayed-noattack') and c['by'] == 'they':
                examples[(g['map'], beh)].append((mid[:8], c['gid'], r0, b, types[b][:4], round(hp, 2), len(en0), en3, al3, d6, d12))
for k in sorted(summary):
    print(k, dict(summary[k]))
for k, v in examples.items():
    print(k, len(v), v[:8])
