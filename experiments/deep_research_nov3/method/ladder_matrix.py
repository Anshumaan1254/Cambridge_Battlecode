#!/usr/bin/env python3
"""Merge every paired ladder plan into one game x version result matrix and measure the noise of the paired test.

    nice -n 19 python3 experiments/deep_research_nov3/method/ladder_matrix.py > experiments/deep_research_nov3/method/out_ladder_matrix.txt

Read-only: uses experiments/ladder_nov2/*.json and the matches_me.jsonl cache (no network: group_games budget 0).
Outputs: per-version totals, pairwise flip / net / sign-test table, flip rate vs code distance, per-game consensus,
a beta-binomial estimate of the per-game latent win probability spread (what pairing removes), and opponent rating bands.
"""
import itertools
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
LN = os.path.abspath(os.path.join(HERE, '..', '..', 'ladder_nov2'))
sys.path.insert(0, LN)
import ladder_loop as L  # noqa: E402

PLAN_NEW = {  # plan file -> version that played its new_group (loop_log.md)
    'paired_v84_to_v85.json': 'v85',
    'paired_cand_shared30.json': 'v86',
    'paired_cand_rest71.json': 'v86',
    'paired_c2.json': 'v87',
    'paired_c3.json': 'v88',
    'paired_c4.json': 'v89',
    'paired_c5.json': 'v90',
    'paired_c6.json': 'v91',
    'paired_c7.json': 'v92',
    'paired_c8.json': None,
    'paired_c9.json': 'v94',
    'paired_c10.json': 'v95',
}
VERS = ['v84', 'v85', 'v86', 'v87', 'v88', 'v89', 'v90', 'v91', 'v92', 'v94', 'v95']


def sign_p(a, b):
    n = a + b
    if n == 0:
        return 1.0
    k = min(a, b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def main():
    index = defaultdict(list)
    for m in L.load_local_matches().values():
        index[m.get('groupId')].append(m)
    # game key = (sourceGroup, position in plan) ; value = dict version -> 'win'/'loss'
    res = defaultdict(dict)
    meta = {}
    conflicts = 0
    for pf, newv in PLAN_NEW.items():
        p = os.path.join(LN, pf)
        if not os.path.exists(p):
            continue
        plan = json.load(open(p))
        for g in plan:
            sg = g['sourceGroup']
            for i, (mp, sd) in enumerate(zip(g['maps'], g['sides'])):
                meta[(sg, i)] = (g.get('opp'), g.get('oppId'), mp, sd)
            cols = {'v84': g['old']}
            for k, v in g.items():
                if k.startswith('v') and k[1:].isdigit() and isinstance(v, list):
                    cols[k] = v
            for ver, col in cols.items():
                for i, r in enumerate(col):
                    if r in ('win', 'loss'):
                        prev = res[(sg, i)].get(ver)
                        if prev and prev != r:
                            conflicts += 1
                        res[(sg, i)][ver] = r
            gid = g.get('new_group')
            if newv and gid and not str(gid).startswith('?'):
                games = L.group_games(gid, index, [0])
                if any(x['opp'] != g['oppId'] for x in games):
                    continue
                for i, (mp, sd, old, new) in enumerate(L.pair_group(g, games)):
                    if new in ('win', 'loss'):
                        prev = res[(sg, i)].get(newv)
                        if prev and prev != new:
                            conflicts += 1
                        res[(sg, i)][newv] = new
    print(f'games (sourceGroup x position) with any result: {len(res)}; conflicting duplicate cells: {conflicts}')

    # opponent ratings (ladder snapshot Nov 3)
    lad = json.load(open(os.path.join(LN, '..', 'top30_nov3', 'ladder.json')))
    rating = {t['teamId']: t.get('rating') for t in lad['teams']}

    print('\n== per version: games, wins, win% (on the paired panel; the panels differ by version)')
    for v in VERS:
        n = sum(1 for r in res.values() if v in r)
        w = sum(1 for r in res.values() if r.get(v) == 'win')
        if n:
            print(f'  {v}: {w}/{n} = {100 * w / n:.1f}%')

    print('\n== pairwise on common games: n, discordant d (flip rate d/n), net (row - col wins), sign p')
    pair = {}
    for a, b in itertools.combinations(VERS, 2):
        common = [r for r in res.values() if a in r and b in r]
        n = len(common)
        if n < 25:
            continue
        ab = sum(1 for r in common if r[a] == 'win' and r[b] == 'loss')
        ba = sum(1 for r in common if r[a] == 'loss' and r[b] == 'win')
        pair[(a, b)] = (n, ab, ba)
        print(f'  {a} vs {b}: n {n:4d}  d {ab + ba:3d} ({100 * (ab + ba) / n:4.1f}%)  {a}-only {ab:3d} {b}-only {ba:3d}  '
              f'net({b}-{a}) {ba - ab:+4d} = {100 * (ba - ab) / n:+5.1f}pp  p {sign_p(ab, ba):.2f}')
    fr = [p[1] + p[2] for p in pair.values()]
    nn = [p[0] for p in pair.values()]
    print(f'  pooled flip rate over {len(pair)} version pairs: {100 * sum(fr) / sum(nn):.1f}%')

    # Is the spread of net results larger than chaos alone? If all versions were equal, net ~ N(0, d).
    print('\n== z of net vs the champion columns (z = net / sqrt(d)); |z| > 2 would be a real difference')
    for ref in ('v84', 'v88'):
        for v in VERS:
            if v == ref:
                continue
            key = (ref, v) if (ref, v) in pair else (v, ref) if (v, ref) in pair else None
            if not key:
                continue
            n, ab, ba = pair[key]
            net = (ba - ab) if key[0] == ref else (ab - ba)
            d = ab + ba
            print(f'  {v} - {ref}: net {net:+d} of n {n}, d {d}, z {net / math.sqrt(d) if d else 0:+.2f}')

    print('\n== per-game consensus over games with >= 6 version results')
    rows6 = [r for r in res.values() if len(r) >= 6]
    allw = sum(1 for r in rows6 if all(x == 'win' for x in r.values()))
    alll = sum(1 for r in rows6 if all(x == 'loss' for x in r.values()))
    print(f'  games {len(rows6)}: always won {allw} ({100 * allw / len(rows6):.0f}%), always lost {alll} '
          f'({100 * alll / len(rows6):.0f}%), mixed {len(rows6) - allw - alll} ({100 * (len(rows6) - allw - alll) / len(rows6):.0f}%)')
    # distribution of win fraction per game
    hist = defaultdict(int)
    for r in rows6:
        k = sum(1 for x in r.values() if x == 'win')
        hist[(k, len(r))] += 1
    print('  (wins, versions): games ->', dict(sorted(hist.items())))

    # Beta-binomial: E[p(1-p)] from within-game agreement (unbiased: for a game with m results and k wins,
    # k(m-k)/(m(m-1)) is unbiased for p(1-p) when the m results are iid Bernoulli(p)).
    num, den = 0.0, 0
    for r in res.values():
        m = len(r)
        if m >= 2:
            k = sum(1 for x in r.values() if x == 'win')
            num += k * (m - k) / (m * (m - 1))
            den += 1
    epq = num / den
    pbar = sum(sum(1 for x in r.values() if x == 'win') / len(r) for r in res.values()) / len(res)
    print(f'\n== latent per-game win probability: E[p(1-p)] = {epq:.3f} (coin: 0.25); implied flip rate between two '
          f'independent-chaos versions 2E[p(1-p)] = {2 * epq:.3f}; mean p {pbar:.3f}; Var(p) = {pbar * (1 - pbar) - epq:.3f}')
    print(f'   -> paired variance per game {2 * epq:.3f} vs unpaired 2*pbar(1-pbar) = {2 * pbar * (1 - pbar):.3f}: '
          f'pairing saves {100 * (1 - epq / (pbar * (1 - pbar))):.0f}% of the games')

    # group-level correlation: games of one 5-game group share the opponent -> design effect for the group as unit
    print('\n== design effect of the 5-game group (net flips correlated within a group?)')
    for a, b in (('v84', 'v88'), ('v88', 'v95'), ('v88', 'v94'), ('v84', 'v87'), ('v88', 'v89'), ('v88', 'v90'), ('v88', 'v92')):
        groups = defaultdict(list)
        for (sg, i), r in res.items():
            if a in r and b in r:
                groups[sg].append((r[b] == 'win') - (r[a] == 'win'))
        gs = [x for x in groups.values() if len(x) == 5]
        if len(gs) < 10:
            continue
        nets = [sum(x) for x in gs]
        n = len(gs) * 5
        d = sum(abs(y) for x in gs for y in x)
        var_group = sum((s - sum(nets) / len(nets)) ** 2 for s in nets) / (len(nets) - 1) * len(nets)
        var_iid = d - (sum(nets) ** 2) / n
        print(f'  {b} - {a}: {len(gs)} full groups, net {sum(nets):+d}, Var(net) by groups {var_group:.1f} vs iid games {var_iid:.1f}'
              f' -> design effect {var_group / var_iid if var_iid > 0 else float("nan"):.2f}')

    # opponent rating of the paired panel
    print('\n== paired panel by opponent rating (Nov 3 ladder): games and v88 win%')
    bands = defaultdict(lambda: [0, 0, 0])
    for (sg, i), r in res.items():
        opp, oid, mp, sd = meta[(sg, i)]
        rt = rating.get(oid)
        b = 'unrated' if rt is None else f'{int(rt // 50 * 50)}'
        bands[b][0] += 1
        if 'v88' in r:
            bands[b][1] += 1
            bands[b][2] += r['v88'] == 'win'
    for b in sorted(bands):
        t, n88, w88 = bands[b]
        print(f'  {b}: {t} games; v88 {w88}/{n88}' + (f' = {100 * w88 / n88:.0f}%' if n88 else ''))
    rts = [rating.get(meta[k][1]) for k in res if rating.get(meta[k][1])]
    print(f'  mean opp rating {sum(rts) / len(rts):.0f}; share >= 2050: {100 * sum(1 for x in rts if x >= 2050) / len(rts):.0f}%;'
          f' distinct opponents {len(set(meta[k][1] for k in res))}; distinct maps {len(set(meta[k][2] for k in res))}')
    json.dump({f'{k[0]}|{k[1]}': {'res': v, 'meta': meta[k]} for k, v in res.items()},
              open(os.path.join(HERE, 'ladder_matrix.json'), 'w'))


if __name__ == '__main__':
    main()
