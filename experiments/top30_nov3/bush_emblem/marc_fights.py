#!/usr/bin/env python3
"""Exchanges with a Marcella taking part: her side's win share by her build stat (first 20 shard-equivalents: focus-major or not),
MH risk difference within strata (participant shard gap bin x body-count gap) -- TOP (both top-30 sides), OPP (our opponents), US."""
import json
from collections import defaultdict, Counter
E = '/home/claude/cambridge_battlecode/experiments/top30_nov3/economy'
F = '/home/claude/cambridge_battlecode/experiments/top30_nov3/fights/out'
ST = ['str', 'foc', 'hp']
build = {}
for fn in ('rows_top30', 'rows_ours'):
    for l in open(f'{E}/{fn}.jsonl'):
        if '"error"' in l[:40]:
            continue
        r = json.loads(l)
        key = r['mid'].split('_')[-1][:8]
        for b, bd in r['builds'].items():
            if bd['champ'] != 'Marcella':
                continue
            stc, n = Counter(), 0
            for (rr, f, s, e, q) in bd['seq']:
                if n >= 20:
                    break
                w = q * (5 if e else 1)
                stc[ST[s]] += w
                n += w
            if n >= 5:
                build[(key, int(b))] = stc['foc'] > n / 2
for ds in ('top', 'our'):
    games = {json.loads(l)['mid']: json.loads(l) for l in open(f'{F}/{ds}_games.jsonl')}
    S = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
    for l in open(f'{F}/{ds}_fights.jsonl'):
        f = json.loads(l)
        if not f['exchange'] or f['win'] is None:
            continue
        g = games.get(f['mid'])
        if not g:
            continue
        for t in ('0', '1'):
            ms = [int(x.split(':')[0]) for x in f['part_bodies'].get(t, []) if x.endswith('Marcella')]
            if not ms:
                continue
            k = build.get((f['mid'][:8], ms[0]))
            if k is None:
                continue
            o = '1' if t == '0' else '0'
            grp = 'TOP' if g['we'] is None else ('US' if int(t) == g['we'] else 'OPP')
            gap = f['shards'][t] - f['shards'][o]
            gb = -2 if gap <= -8 else -1 if gap <= -3 else 0 if gap <= 2 else 1 if gap <= 7 else 2
            nb = max(-1, min(1, f['num'][t] - f['num'][o]))
            c = S[grp][(gb, nb)]
            w = f['win'] == int(t)
            if k:
                c[0] += 1; c[1] += w
            else:
                c[2] += 1; c[3] += w
    for grp, SS in S.items():
        num = den = 0; n1 = n0 = w1 = w0 = 0
        for c in SS.values():
            n1 += c[0]; n0 += c[2]; w1 += c[1]; w0 += c[3]
            if c[0] and c[2]:
                wt = c[0] * c[2] / (c[0] + c[2]); num += wt * (c[1] / c[0] - c[3] / c[2]); den += wt
        print(f"{ds} {grp:4s} focus-Marcella exchanges n={n1} win {100 * w1 / max(1, n1):.1f}% | str/hp-Marcella n={n0} win {100 * w0 / max(1, n0):.1f}% | "
              f"stratified diff {100 * num / den if den else float('nan'):+.1f} pts")
