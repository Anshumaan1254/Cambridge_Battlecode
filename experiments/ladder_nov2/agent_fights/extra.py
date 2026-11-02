#!/usr/bin/env python3
"""Supplementary numbers cited in REPORT.md (run after extract.py).

Usage: nice -n 19 python3 -I extra.py > extra_tables.txt
  1. item / economy level per body at r200..800 (W vs L games)
  2. held recalls by distance to the nearest enemy (fake-recall spam and stunned turns excluded)
  3. A-B-A oscillation in the last 8 rounds before deaths (camp-involved or not)
  4. map feature for the enemy-camp pattern: share of combat camps in the contested middle band
  5. no-retreat deaths that were already below 50% hp 5 rounds before
"""
import json, os, sys
from collections import Counter, defaultdict
from statistics import mean, median

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extract import BASE, shards, dps, bfs  # noqa: E402

load = lambda n: [json.loads(l) for l in open(os.path.join(HERE, n + '.jsonl'))]
D, G, RC = load('deaths'), load('games'), load('recalls')
GM = {g['mid']: g for g in G}
ng = Counter(g['res'] for g in G)

print('1. per-body shards / max hp / dps / unspent gold / banked, means (we vs they)')
acc = defaultdict(list)
for g in G:
    d = json.load(open(f'{BASE}/dec/{g["mid"]}.json'))
    we = g['we']
    types = {b['index']: b['type'] for b in d['meta']['bodies']}
    S = {rr['r']: rr for rr in d['rounds'][1:]}
    for R in (200, 400, 600, 800):
        if R not in S:
            continue
        sh, mh, dp, gold = [0, 0], [0, 0], [0, 0], [0, 0]
        for c in S[R]['ch']:
            t = c[1]
            sh[t] += shards(c[11])
            mh[t] += c[6]
            dp[t] += dps(types[c[0]], c[11])
            gold[t] += c[9]
        n = g['champs']
        acc[(g['res'], R)].append((sh[we] / n, sh[1 - we] / n, mh[we] / n, mh[1 - we] / n, dp[we] / n, dp[1 - we] / n,
                                   gold[we], gold[1 - we], S[R]['sub'][we], S[R]['sub'][1 - we]))
for k in sorted(acc):
    m = [mean(x[i] for x in acc[k]) for i in range(10)]
    print(f'  {k}: n={len(acc[k])} shards/body {m[0]:.1f} vs {m[1]:.1f} | max hp/body {m[2]:.0f} vs {m[3]:.0f} | dps/body {m[4]:.0f} vs {m[5]:.0f}'
          f' | unspent gold {m[6]:.0f} vs {m[7]:.0f} | banked {m[8]:.0f} vs {m[9]:.0f}')

print('\n2. held recalls (channel kept through the next round) per game, by nearest enemy distance at the start')
for side in ('we', 'they'):
    for res in 'LW':
        R = [r for r in RC if r['side'] == side and r['res'] == res]
        parts = []
        for lo, hi in ((0, 4), (4, 6), (6, 8), (8, 999)):
            S = [r for r in R if lo <= r['dmin'] < hi]
            parts.append(f'{lo}-{hi - 1 if hi < 999 else "+"}: {len(S) / ng[res]:.2f}/game, completed {sum(r["done"] is not None for r in S) / max(1, len(S)):.0%}, '
                         f'died<=8r {sum(r["died8"] for r in S) / max(1, len(S)):.0%}')
        print(f'  {side}-{res}: ' + ' | '.join(parts))

print('\n3. immediate move reversals (A->B->A) in the last 8 rounds before a death')
bym = defaultdict(list)
for d in D:
    bym[d['mid']].append(d)
osc = defaultdict(list)
for mid, ds in bym.items():
    dd = json.load(open(f'{BASE}/dec/{mid}.json'))
    mv = defaultdict(list)
    for e in dd['events']:
        if e['k'] == 'Move' or (e['k'] == 'Cast ability' and e.get('ability') == 6 and tuple(e['from']) != (0, 0)):
            mv[e['who']].append((e['r'], tuple(e['from']), tuple(e['to'])))
    for d in ds:
        m = [x for x in mv[d['body']] if d['r'] - 8 <= x[0] <= d['r']]
        osc[(d['side'], d['res'], 'camp-involved' if d['camp_hits5'] > 0 else 'no camp')].append(sum(1 for a, b in zip(m, m[1:]) if b[2] == a[1]))
for k, v in sorted(osc.items()):
    print(f'  {k}: n={len(v)}, >=2 reversals {sum(x >= 2 for x in v) / len(v):.0%}')

print('\n4. enemy-camp deaths (ours) per 1000 rounds vs share of combat camps in the middle band')
rng = {'wolf': 3, 'elk': 4, 'golem': 4, 'monolith': 5}
rows = []
for g in G:
    mid = g['mid']
    mp = json.load(open(f'{BASE}/mj/{mid}.json'))
    meta = json.load(open(f'{BASE}/dec/{mid}.json'))['meta']
    w, h, rws = mp['width'], mp['height'], mp['rows']
    dA = bfs(rws, [tuple(p) for p in mp['spawnA']], w, h)
    dB = bfs(rws, [tuple(p) for p in mp['spawnB']], w, h)
    tot = midc = 0
    for c in meta['camps']:
        if c['type'] not in rng:
            continue
        a, b = dA[c['y']][c['x']], dB[c['y']][c['x']]
        if a < 0 or b < 0:
            continue
        tot += 1
        midc += abs(a - b) <= max(6, 0.25 * max(a, b))
    share = midc / max(1, tot)
    rate = sum(1 for d in D if d['mid'] == mid and d['side'] == 'we' and d['camp_waker'] in ('enemy', 'both')) * 1000 / g['final']
    rows.append((share, rate, g['champs']))
t = median(r[0] for r in rows)
print(f'  middle-band share < {t:.2f}: {mean(r[1] for r in rows if r[0] < t):.2f} (n={sum(1 for r in rows if r[0] < t)}) vs >= {t:.2f}: '
      f'{mean(r[1] for r in rows if r[0] >= t):.2f} (n={sum(1 for r in rows if r[0] >= t)})')
print(f'  5 champions: {mean(r[1] for r in rows if r[2] == 5):.2f} (n={sum(1 for r in rows if r[2] == 5)}) vs 3-4: {mean(r[1] for r in rows if r[2] < 5):.2f}')

print('\n5. champion-kill deaths with no retreat step in the last 10 rounds and hp < 50% five rounds before')
for side in ('we', 'they'):
    for res in 'LW':
        R = [d for d in D if d['side'] == side and d['res'] == res and d['killer'] != 'camp' and d['ret_r'] is None]
        low = [d for d in R if d['hp5'] is not None and d['hp5'] < 0.5]
        print(f'  {side}-{res}: {len(low) / ng[res]:.2f}/game ({len(low) / max(1, len(R)):.0%} of no-retreat deaths)')
