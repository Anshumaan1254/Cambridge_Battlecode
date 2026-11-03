#!/usr/bin/env python3
"""Per top-10 team: own and opponent features in its losses vs wins, from draft_bank/out/teams.jsonl (610 top-30 games, other agent's
extraction). Usage: nice -n 19 python3 -I db_teams.py -> out/db_teams.txt"""
import json
from collections import defaultdict, Counter
BASE = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
OUT = '/home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out'
lad = json.load(open(f'{BASE}/ladder.json'))['teams']
rank = {t['name']: t['rank'] for t in lad}
rows = [json.loads(l) for l in open(f'{BASE}/draft_bank/out/teams.jsonl')]
rows = [r for r in rows if r['set'] == 'top30']
by = defaultdict(dict)
for r in rows:
    by[r['mid']][r['team']] = r
games = [v for v in by.values() if len(v) == 2]
out = [f'top30 games with both sides: {len(games)}']
K = ['deaths', 'kills', 'gems_lost', 'deaths_bag20', 'captured', 'gold', 'locks', 'locks_hit', 'n_cancel', 'n_banked', 'bag_mean', 'carried_mean',
     'marc_share', 'carried_end', 'sub']
def b200(r, k):
    b = r.get('beh200') or {}
    s = sum(b.values()) or 1
    return b.get(k, 0) / s
def h200(r, k):
    b = r.get('half200') or {}
    s = sum(b.values()) or 1
    return b.get(k, 0) / s
def feats(r):
    f = {k: r.get(k) for k in K}
    for k in ('walk', 'fight', 'farm', 'still', 'dead'):
        f['b200_' + k] = b200(r, k)
    for k in ('own', 'mid', 'their'):
        f['h200_' + k] = h200(r, k)
    return f
def m(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return f'{sum(xs) / len(xs):7.2f}' if xs else '    n/a'
names = [t['name'] for t in lad if t['rank'] <= 10]
for nm in names + ['__11-20', '__21-30']:
    L, W = [], []
    for g in games:
        for t in (0, 1):
            me, op = g[t], g[1 - t]
            if nm.startswith('__'):
                lo, hi = (11, 20) if nm == '__11-20' else (21, 30)
                if not (lo <= rank.get(me['name'], 99) <= hi) or lo <= rank.get(op['name'], 99) <= hi:
                    continue
            elif me['name'] != nm:
                continue
            (W if me['res'] == 'win' else L).append((me, op))
    if not L:
        continue
    out.append(f'\n## {nm}: games {len(L) + len(W)} (L {len(L)}, W {len(W)})')
    out.append(f"  {'feature':16} {'own L':>8} {'own W':>8} | {'opp in L':>8} {'opp in W':>8}")
    F = list(feats(L[0][0]).keys())
    for k in F:
        out.append(f'  {k:16} {m([feats(a)[k] for a, b in L])} {m([feats(a)[k] for a, b in W])} | {m([feats(b)[k] for a, b in L])} {m([feats(b)[k] for a, b in W])}')
    out.append('  opp drafts in losses: ' + '; '.join(f"{'+'.join(sorted(d))} {c}" for d, c in Counter(tuple(b['draft']) for a, b in L).most_common(3)))
open(f'{OUT}/db_teams.txt', 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
