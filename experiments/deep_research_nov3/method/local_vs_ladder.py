#!/usr/bin/env python3
"""Local panel noise and its (non-)relation to the ladder.

    nice -n 19 python3 experiments/deep_research_nov3/method/local_vs_ladder.py > experiments/deep_research_nov3/method/out_local_vs_ladder.txt

Inputs: experiments/ab2/*/rows.jsonl (local games), ladder_matrix.json (written by ladder_matrix.py).
"""
import glob
import itertools
import json
import math
import os
import random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
AB = os.path.abspath(os.path.join(HERE, '..', '..', 'ab2'))
random.seed(7)


def load(tag):
    p = os.path.join(AB, tag, 'rows.jsonl')
    if not os.path.exists(p):
        return None
    out = {}
    for line in open(p):
        line = line.strip()
        if line:
            r = json.loads(line)
            out[(r['map'], r['side'])] = r
    return out


def summ(rows):
    n = len(rows)
    w = sum(r['win'] for r in rows.values())
    mar = [r['me']['banked'] - r['them']['banked'] for r in rows.values()]
    m = sum(mar) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in mar) / (n - 1))
    # map-pair cluster SE (both sides of one map are correlated)
    pairs = defaultdict(list)
    for (mp, sd_), r in rows.items():
        pairs[mp].append(r['me']['banked'] - r['them']['banked'])
    pm = [sum(v) for v in pairs.values()]
    k = len(pm)
    mu = sum(pm) / k
    se_cl = math.sqrt(sum((x - mu) ** 2 for x in pm) / (k - 1) * k) / n
    d1 = sum(r['me']['deaths'] for r in rows.values()) / n
    d2 = sum(r['them']['deaths'] for r in rows.values()) / n
    return dict(n=n, w=w, wp=100 * w / n, m=m, sd=sd, se=sd / math.sqrt(n), se_cl=se_cl, d1=d1, d2=d2)


def mirror_breaks(rows):
    """Map pairs that are not an exact mirror (margins of the two sides do not cancel / results not complementary)."""
    by = defaultdict(dict)
    for (mp, sd), r in rows.items():
        by[mp][sd] = r
    nb, nres = 0, 0
    for mp, s in by.items():
        if 'a' in s and 'b' in s:
            ma = s['a']['me']['banked'] - s['a']['them']['banked']
            mb = s['b']['me']['banked'] - s['b']['them']['banked']
            if abs(ma + mb) > 1e-6:
                nb += 1
            if s['a']['win'] == s['b']['win']:
                nres += 1
    return nb, nres, len(by)


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else float('nan')


def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def perm_p(x, y, f, reps=20000):
    obs = f(x, y)
    c = 0
    yy = list(y)
    for _ in range(reps):
        random.shuffle(yy)
        if abs(f(x, yy)) >= abs(obs) - 1e-12:
            c += 1
    return obs, c / reps


def main():
    print('== 1. Local panel summaries (vs god84 = v84 on maps/s4, 172 games unless noted)')
    tags = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(AB, '*', 'rows.jsonl')))
    S = {}
    for t in tags:
        r = load(t)
        if r and len(r) >= 100:
            S[t] = (r, summ(r))
    sds, wps, ms = [], [], []
    for t, (r, s) in S.items():
        if t.endswith('_vs_god84') and s['n'] == 172:
            sds.append(s['sd'])
            wps.append(s['wp'])
            ms.append(s['m'])
    print(f'  {len(sds)} variants vs god84 on s4: per-game SD of the gem margin median {sorted(sds)[len(sds) // 2]:.0f} '
          f'(range {min(sds):.0f}-{max(sds):.0f}); SE of a 172-game margin {sorted(sds)[len(sds) // 2] / math.sqrt(172):.0f}; '
          f'SE of a 172-game win% {100 * math.sqrt(0.25 / 172):.1f}pp')
    b = pearson(ms, wps)
    # slope win% per 100 gems of margin across variants
    mx, my = sum(ms) / len(ms), sum(wps) / len(wps)
    slope = sum((a - mx) * (c - my) for a, c in zip(ms, wps)) / sum((a - mx) ** 2 for a in ms)
    print(f'  across variants: corr(margin, win%) {b:.2f}; slope {100 * slope:.1f} pp of win% per 100 gems of margin;'
          f' intercept at margin 0: {my - slope * mx:.1f}%')
    print(f'  spread of variant margins vs god84: SD {math.sqrt(sum((a - mx) ** 2 for a in ms) / (len(ms) - 1)):.0f} gems '
          f'(sampling SE of one variant ~{sorted(sds)[len(sds) // 2] / math.sqrt(172):.0f}) ; win% SD '
          f'{math.sqrt(sum((a - my) ** 2 for a in wps) / (len(wps) - 1)):.1f}pp (sampling SE 3.8pp)')

    print('\n== 2. Chaos: mirror breaks of null / inert controls (exact mirror = every map pair cancels)')
    for t in ('_85null_vs_god84', '_hs_vs_god84', '_rcfh_vs_god84', 'god29_vs_god84'):
        if t in S:
            r, s = S[t]
            nb, nres, k = mirror_breaks(r)
            print(f'  {t}: {s["w"]}/{s["n"]} margin {s["m"]:+.0f} (SE {s["se"]:.0f}); map pairs not mirrored {nb}/{k}; '
                  f'pairs won or lost on both sides {nres}/{k}')

    print('\n== 3. Local flip rates between variants on the same 172 games vs god84 (paired local comparison)')
    s4 = {t: S[t][0] for t in S if t.endswith('_vs_god84') and S[t][1]['n'] == 172}
    keys = sorted(s4)
    flips = []
    for a, b2 in itertools.combinations(keys, 2):
        ra, rb = s4[a], s4[b2]
        common = set(ra) & set(rb)
        d = sum(ra[k]['win'] != rb[k]['win'] for k in common)
        same_games = sum(ra[k]['me']['banked'] == rb[k]['me']['banked'] and ra[k]['rounds'] == rb[k]['rounds'] for k in common)
        flips.append((d / len(common), a, b2, same_games))
    fl = sorted(x[0] for x in flips)
    print(f'  {len(flips)} variant pairs: flip rate median {100 * fl[len(fl) // 2]:.1f}%, 10th pct {100 * fl[len(fl) // 10]:.1f}%, '
          f'90th pct {100 * fl[9 * len(fl) // 10]:.1f}%')
    ident = [x for x in flips if x[3] == 172]
    print(f'  identical game sets (switch no-ops): {[(x[1], x[2]) for x in ident][:8]}')
    lows = sorted(flips)[:8]
    print('  lowest flip pairs:', [(x[1], x[2], f'{100 * x[0]:.1f}%') for x in lows])
    for a, b2 in (('_rcf_vs_god84', '_rsf3_vs_god84'), ('_rcf_vs_god84', '_rbuild_vs_god84'), ('_rcf_vs_god84', '_ros_vs_god84'),
                  ('g23r_vs_god84', 'g23rc_vs_god84'), ('_rcf_vs_god84', 'g23r_vs_god84'), ('_rcf_vs_god84', '_hs_vs_god84')):
        if a in s4 and b2 in s4:
            ra, rb = s4[a], s4[b2]
            ab = sum(ra[k]['win'] and not rb[k]['win'] for k in ra)
            ba = sum(rb[k]['win'] and not ra[k]['win'] for k in ra)
            print(f'  {b2} - {a}: flips {ab + ba} ({100 * (ab + ba) / 172:.0f}%), net {ba - ab:+d} ({100 * (ba - ab) / 172:+.1f}pp)')

    print('\n== 4. Local vs ladder by deployed version')
    M = json.load(open(os.path.join(HERE, 'ladder_matrix.json')))
    res = [v['res'] for v in M.values()]

    def ladder_net(v, ref):
        c = [r for r in res if v in r and ref in r]
        n = len(c)
        if not n:
            return None
        ab = sum(r[v] == 'win' and r[ref] == 'loss' for r in c)
        ba = sum(r[v] == 'loss' and r[ref] == 'win' for r in c)
        return n, ab - ba, ab + ba

    vers = {  # version: (local tag vs god84 s4, held-out tag)
        'v85': ('god29_vs_god84', None),
        'v86': ('g23rc_vs_god84', 'g23rc_vs_god84_heldout'),
        'v87': ('g23r_vs_god84', 'g23r_vs_god84_heldout'),
        'v88': ('_rcf_vs_god84', '_rcf_vs_god84_heldout'),
        'v89': ('_rbuild_vs_god84', '_rbuild_vs_god84_heldout'),
        'v90': ('_rsf3_vs_god84', '_rsf3_vs_god84_heldout'),
        'v91': ('_ros_vs_god84', '_ros_vs_god84_heldout'),
        'v92': ('g29rcf_vs_god84', 'g29rcf_vs_god84_heldout'),
    }
    X1, X2, Y1, Yz, names = [], [], [], [], []
    print(f'  {"ver":4} {"local s4 vs v84":>22} {"held-out vs v84":>22} {"ladder vs v84 (net/n, pp, z)":>32}')
    for v, (t1, t2) in vers.items():
        s1 = S[t1][1] if t1 in S else None
        s2 = S[t2][1] if t2 and t2 in S else None
        ln = ladder_net(v, 'v84')
        if not s1 or not ln:
            continue
        n, net, d = ln
        pp = 100 * net / n
        z = net / math.sqrt(d) if d else 0
        print(f'  {v:4} {s1["w"]:3d}/172 {s1["m"]:+5.0f} ({s1["wp"] - 50:+5.1f}pp)  '
              + (f'{s2["w"]:3d}/206 {s2["m"]:+5.0f} ({s2["wp"] - 50:+5.1f}pp)' if s2 else ' ' * 23)
              + f'   {net:+3d}/{n:3d} {pp:+5.1f}pp z {z:+.2f}')
        X1.append(s1['m'])
        X2.append(s1['m'] + (s2['m'] if s2 else s1['m']))
        Y1.append(pp)
        Yz.append(z)
        names.append(v)
    r1, p1 = perm_p(X1, Y1, pearson)
    rs, ps = perm_p(rank(X1), rank(Y1), pearson)
    r2, p2 = perm_p(X2, Y1, pearson)
    print(f'  n = {len(X1)} versions: Pearson(local s4 margin, ladder pp vs v84) = {r1:+.2f} (perm p {p1:.2f}); '
          f'Spearman {rs:+.2f} (p {ps:.2f}); Pearson(s4 + held-out margin, ladder) {r2:+.2f} (p {p2:.2f})')
    # how much of the ladder spread is real? method-of-moments between-version variance
    ses = []
    for v in names:
        n, net, d = ladder_net(v, 'v84')
        ses.append(100 * math.sqrt(d) / n)
    my = sum(Y1) / len(Y1)
    vy = sum((y - my) ** 2 for y in Y1) / (len(Y1) - 1)
    ms2 = sum(s * s for s in ses) / len(ses)
    print(f'  ladder effects vs v84: mean {my:+.1f}pp, SD across versions {math.sqrt(vy):.1f}pp, mean sampling SE {math.sqrt(ms2):.1f}pp'
          f' -> between-version true SD^2 = {vy - ms2:+.1f} (<= 0: the spread is all noise)')
    # paired local comparison vs v88 on god84 games vs ladder vs v88
    print('\n  local paired vs v88 (both vs god84 on the same 172 games; win flips) and ladder vs v88:')
    for v, (t1, t2) in vers.items():
        if v == 'v88' or t1 not in s4:
            continue
        ra, rb = s4['_rcf_vs_god84'], s4[t1]
        ab = sum(rb[k]['win'] and not ra[k]['win'] for k in ra)
        ba = sum(ra[k]['win'] and not rb[k]['win'] for k in ra)
        dm = S[t1][1]['m'] - S['_rcf_vs_god84'][1]['m']
        ln = ladder_net(v, 'v88')
        lt = f'{ln[1]:+d}/{ln[0]} ({100 * ln[1] / ln[0]:+.1f}pp)' if ln else 'n/a'
        print(f'   {v}: local net flips {ab - ba:+d}/172 ({100 * (ab - ba) / 172:+.1f}pp), margin diff {dm:+.0f}; ladder vs v88 {lt}')
    for t, ref in (('_g24allmc_vs_g23rcf', 'v95'), ('_g24allmc_vs_g23rcf_heldout', 'v95')):
        if t in S:
            s = S[t][1]
            ln = ladder_net('v95', 'v88')
            print(f'   v95 local {t}: {s["w"]}/{s["n"]} ({s["wp"] - 50:+.1f}pp) margin {s["m"]:+.0f}, deaths {s["d1"]:.1f} vs {s["d2"]:.1f};'
                  f' ladder vs v88 {ln[1]:+d}/{ln[0]} ({100 * ln[1] / ln[0]:+.1f}pp)')

    print('\n== 5. Non-transitivity in the local panels (same variant, two references)')
    for a, b2 in (('_rcf_vs_god84', '_rcf_vs_gpta75'), ('_rsf3_vs_god84', '_rsf3_vs_gpta75'), ('g23r_vs_god84', 'g23r_vs_gpta75'),
                  ('_g24all_vs_g23rcf', '_g24all_vs_gpta94')):
        if a in S and b2 in S:
            print(f'  {a}: {S[a][1]["w"]}/{S[a][1]["n"]} {S[a][1]["m"]:+.0f} | {b2}: {S[b2][1]["w"]}/{S[b2][1]["n"]} {S[b2][1]["m"]:+.0f}')
    if 'god84_vs_gpta75' in S:
        print(f'  baseline god84_vs_gpta75: {S["god84_vs_gpta75"][1]["w"]}/172 {S["god84_vs_gpta75"][1]["m"]:+.0f}')

    print('\n== 6. s4 vs held-out agreement (same variant): does the held-out pool replicate the s4 margin?')
    xs, ys = [], []
    for t in S:
        if t.endswith('_heldout'):
            base = t[:-len('_heldout')]
            if base in S:
                xs.append(S[base][1]['m'])
                ys.append(S[t][1]['m'])
                print(f'  {base:28} s4 {S[base][1]["m"]:+5.0f}  held-out {S[t][1]["m"]:+5.0f}')
    r, p = perm_p(xs, ys, pearson)
    print(f'  n {len(xs)}: Pearson {r:+.2f} (perm p {p:.2f}); mean s4 {sum(xs) / len(xs):+.0f}, mean held-out {sum(ys) / len(ys):+.0f}'
          f' (regression to the mean of the selected variants)')


if __name__ == '__main__':
    main()
