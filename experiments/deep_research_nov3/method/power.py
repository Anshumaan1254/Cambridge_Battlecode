#!/usr/bin/env python3
"""Power, sample sizes, SPRT and ranked-performance noise for the CAMBC ladder test protocol.

    nice -n 19 python3 experiments/deep_research_nov3/method/power.py > experiments/deep_research_nov3/method/out_power.txt

Inputs: ladder_matrix.json (ladder_matrix.py), experiments/ladder_nov2/matches_me.jsonl, experiments/top30_nov3/ladder.json,
experiments/ab2/*/rows.jsonl. Pure analysis, no network, numpy/scipy only.
"""
import datetime as dt
import glob
import itertools
import json
import math
import os

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
C = math.log(10) / 400  # logistic Elo slope


def elo_of_pp(pp, p0=0.5):
    p1 = p0 + pp / 100
    return 400 * math.log10(p1 / (1 - p1)) - 400 * math.log10(p0 / (1 - p0))


def sign_power(n, f, d, alpha=0.05, sided=1):
    """Exact power of the sign test on n paired games with discordant rate f and true win-rate gain d (fraction)."""
    q = 0.5 + d / (2 * f)  # P(a discordant pair favours the candidate)
    ks = np.arange(0, n + 1)
    pk = stats.binom.pmf(ks, n, f)
    pw = 0.0
    for k, w in zip(ks, pk):
        if w < 1e-12 or k == 0:
            continue
        a = alpha if sided == 1 else alpha / 2
        crit = stats.binom.isf(a, k, 0.5)  # reject if X > crit
        pw += w * stats.binom.sf(crit, k, q)
    return pw


def n_needed(f, d, power=0.8, alpha=0.05, sided=1):
    lo, hi = 10, 40000
    if sign_power(hi, f, d, alpha, sided) < power:
        return None
    while hi - lo > 5:
        mid = (lo + hi) // 2
        if sign_power(mid, f, d, alpha, sided) >= power:
            hi = mid
        else:
            lo = mid
    return hi


def sprt_sim(f, d_true, d1, alpha=0.05, beta=0.05, nmax=3000, reps=4000, block=5, seed=1):
    """Trinomial SPRT on paired games (+1 candidate-only win, -1 champion-only win, 0 same), H0 d=0 vs H1 d=d1.
    Looks at the LLR after every 5-game group; truncated at nmax games (then 'no decision' -> keep champion)."""
    rng = np.random.default_rng(seed)
    A, B = math.log((1 - beta) / alpha), math.log(beta / (1 - alpha))
    p0p, p0m = f / 2, f / 2
    p1p, p1m = f / 2 + d1 / 2, f / 2 - d1 / 2
    lp, lm = math.log(p1p / p0p), math.log(p1m / p0m)
    tp, tm = f / 2 + d_true / 2, f / 2 - d_true / 2
    u = rng.random((reps, nmax))
    x = np.where(u < tp, 1, np.where(u < tp + tm, -1, 0))
    llr = np.cumsum(np.where(x == 1, lp, np.where(x == -1, lm, 0.0)), axis=1)[:, block - 1::block]
    acc = np.full(reps, 0)
    nused = np.full(reps, nmax)
    done = np.zeros(reps, bool)
    for j in range(llr.shape[1]):
        hit1 = (~done) & (llr[:, j] >= A)
        hit0 = (~done) & (llr[:, j] <= B)
        acc[hit1] = 1
        acc[hit0] = -1
        nused[hit1 | hit0] = (j + 1) * block
        done |= hit1 | hit0
    return (acc == 1).mean(), (acc == -1).mean(), (acc == 0).mean(), nused.mean(), np.percentile(nused, 90)


def perf_rating(opp, wins):
    lo, hi = min(opp) - 800.0, max(opp) + 800.0
    if wins <= 0 or wins >= len(opp):
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if sum(1 / (1 + 10 ** ((r - mid) / 400)) for r in opp) < wins:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def parse(s):
    return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def main():
    print('== A. Win-rate points vs Elo at a 50% base: '
          + ', '.join(f'{pp}pp = {elo_of_pp(pp):.0f} Elo' for pp in (1, 2, 3, 5, 10)))
    print(f'   rank 30 (2192) - our rating (1979) = 213 Elo = {100 * (1 / (1 + 10 ** (-213 / 400)) - 0.5):.0f}pp more wins vs the same opponents')

    print('\n== B. Paired ladder test (exact sign test on flips), games n needed for 80% power')
    print('   f = flip (discordant) rate. Ladder: v86-v87 4.8% (near-identical), typical 25-35% (pooled 29.5%); local mirror panel 46%')
    for sided, alpha in ((1, 0.05), (2, 0.05), (1, 0.10)):
        print(f'   {sided}-sided alpha {alpha}:')
        for f in (0.10, 0.20, 0.29, 0.35, 0.46):
            row = []
            for d in (0.03, 0.05, 0.10):
                n = n_needed(f, d, 0.8, alpha, sided)
                row.append(f'{d * 100:.0f}pp: {n:5d} games = {math.ceil(n / 5):4d} groups = {n / 250:4.1f} quota-h' if n else f'{d * 100:.0f}pp: >40000')
            print(f'     f {f:.2f} | ' + ' | '.join(row))
    # unpaired comparison (two independent samples, e.g. ranked games of two versions), 80% power, 1-sided 0.05
    za, zb = stats.norm.isf(0.05), stats.norm.isf(0.2)
    for d in (0.03, 0.05, 0.10):
        n = (za + zb) ** 2 * 2 * 0.25 / d ** 2
        print(f'   unpaired (independent samples, p~0.5), {d * 100:.0f}pp: {n:.0f} games PER version')

    print('\n== C. What the current rule can and cannot see (KEEP if p < 0.2 two-sided, n = 250 paired, f = 0.295)')
    f = 0.295
    for d in (0.0, 0.03, 0.05, 0.10):
        # one direction of p < 0.2 two-sided = one-sided 0.10
        pw = sign_power(250, f, d, 0.10, 1)
        print(f'   true gain {d * 100:4.1f}pp: P(KEEP) = {pw:.2f}')
    print('   with 10 equal candidates each tested once at that rule: P(at least one false KEEP) = '
          f'{1 - (1 - sign_power(250, f, 0.0, 0.10, 1)) ** 10:.2f}')
    sd_net = math.sqrt(f * 250)
    print(f'   SD of the net flips at n 250: {sd_net:.1f} games = {100 * sd_net / 250:.1f}pp; 95% CI half-width {196 * sd_net / 250:.1f}pp')

    print('\n== D. SPRT on paired games (trinomial, LLR checked after every 5-game group, truncated at 3000 games)')
    for d1, a_, b_ in ((0.05, 0.05, 0.05), (0.05, 0.05, 0.20), (0.04, 0.05, 0.10), (0.03, 0.05, 0.10), (0.10, 0.05, 0.05)):
        print(f'   H0 0pp vs H1 {d1 * 100:.0f}pp, alpha {a_}, beta {b_} (LLR bounds {math.log(b_ / (1 - a_)):+.2f} / {math.log((1 - b_) / a_):+.2f}),'
              f' f 0.295:')
        for dt_ in (-0.03, 0.0, 0.02, 0.03, 0.05, 0.10):
            pa, pr, pn, asn, p90 = sprt_sim(0.295, dt_, d1, a_, b_)
            print(f'     true {dt_ * 100:+4.0f}pp: accept H1 {pa:.3f}, accept H0 {pr:.3f}, undecided {pn:.3f}; mean games {asn:6.0f} '
                  f'(90th pct {p90:5.0f}) = {asn / 250:4.1f} quota-hours')

    print('\n== E. Ranked performance tracking (matches_me.jsonl, opponent ratings = Nov 3 ladder snapshot)')
    lad = json.load(open(os.path.join(ROOT, 'top30_nov3', 'ladder.json')))
    rating = {t['teamId']: t['rating'] for t in lad['teams']}
    rows = []
    for line in open(os.path.join(ROOT, 'ladder_nov2', 'matches_me.jsonl')):
        m = json.loads(line)
        if m.get('kind') != 'ranked' or m.get('status') != 'finished':
            continue
        me = next((t for t in m['teams'] if t['teamId'] == ME), None)
        op = next((t for t in m['teams'] if t['teamId'] != ME), None)
        if not me or not op or me.get('result') not in ('win', 'loss'):
            continue
        rows.append((parse(m['createdAt']), me['result'] == 'win', rating.get(op['teamId'])))
    rows.sort()
    t0, t1 = rows[0][0], rows[-1][0]
    days = (t1 - t0).total_seconds() / 86400
    rated = [r for r in rows if r[2]]
    print(f'   ranked games {len(rows)} from {t0:%m-%d %H:%M} to {t1:%m-%d %H:%M} ({days:.2f} days) = {len(rows) / days:.0f}/day; '
          f'with a rated opponent {len(rated)}')
    R0 = 1979
    info_per_game = np.mean([C ** 2 * (e := 1 / (1 + 10 ** ((r - R0) / 400))) * (1 - e) for _, _, r in rated])
    for n in (100, 300, 720, 2160, 5000):
        print(f'   SE of a performance rating over {n:5d} ranked games: {1 / math.sqrt(n * info_per_game):5.1f} Elo '
              f'({1 / math.sqrt(n * info_per_game) * 0.1439:.1f}pp)')
    k = 4.6
    a = k * C * 0.25
    print(f'   displayed rating (K {k}): relaxation {1 / a:.0f} games = {1 / a / (len(rows) / days) * 24:.1f} h; '
          f'stationary SD around true strength {math.sqrt(k * k * 0.25 / (2 * a - a * a)):.0f} Elo')
    wins_by_version = {}
    windows = [('v84', '2026-11-02T00:00:00Z', '2026-11-02T21:15:46Z'), ('v85', '2026-11-02T21:15:46Z', '2026-11-03T01:00:56Z'),
               ('v86+v87', '2026-11-03T01:00:56Z', '2026-11-03T02:52:00Z'), ('v88', '2026-11-03T02:52:00Z', '2026-11-03T04:11:33Z'),
               ('v89', '2026-11-03T04:11:33Z', '2026-11-03T04:30:50Z'), ('v88b', '2026-11-03T04:30:50Z', '2026-11-03T04:52:07Z'),
               ('v90', '2026-11-03T04:52:07Z', '2026-11-03T05:30:53Z'), ('v88c', '2026-11-03T05:30:53Z', '2026-11-03T05:51:29Z'),
               ('v91', '2026-11-03T05:51:29Z', '2026-11-03T06:10:00Z'), ('v88d', '2026-11-03T06:10:00Z', '2026-11-03T10:26:00Z'),
               ('v94', '2026-11-03T10:26:00Z', '2026-11-03T12:50:00Z')]
    for name, a_, b_ in windows:
        ta, tb = parse(a_), parse(b_)
        g = [r for r in rated if ta <= r[0] < tb]
        if not g:
            print(f'   {name:8}: no ranked games in the cache')
            continue
        w = sum(r[1] for r in g)
        opp = [r[2] for r in g]
        pr = perf_rating(opp, w)
        se = 1 / math.sqrt(sum(C ** 2 * (e := 1 / (1 + 10 ** ((r - (pr or R0)) / 400))) * (1 - e) for r in opp))
        print(f'   {name:8}: {w:3d}/{len(g):3d} ranked, mean opp {np.mean(opp):.0f}, perf {pr if pr is None else round(pr)} +- {se:.0f} (1 SE)')
        wins_by_version[name] = (w, len(g))

    print('\n== F. Per-game measure: win flips vs gem margin (local, pairs of variants on the same 172 games vs god84)')
    AB = os.path.join(ROOT, 'ab2')
    data = {}
    for p in glob.glob(os.path.join(AB, '*_vs_god84', 'rows.jsonl')):
        t = os.path.basename(os.path.dirname(p))
        rr = {}
        for line in open(p):
            if line.strip():
                r = json.loads(line)
                rr[(r['map'], r['side'])] = (r['win'], r['me']['banked'] - r['them']['banked'])
        if len(rr) == 172:
            data[t] = rr
    zw, zm = [], []
    for a_, b_ in itertools.combinations(sorted(data), 2):
        A_, B_ = data[a_], data[b_]
        if all(A_[k] == B_[k] for k in A_):
            continue
        dw = [B_[k][0] - A_[k][0] for k in A_]
        dm = [B_[k][1] - A_[k][1] for k in A_]
        disc = sum(abs(x) for x in dw)
        zw.append(sum(dw) / math.sqrt(disc) if disc else 0)
        sd = np.std(dm, ddof=1)
        zm.append(np.mean(dm) / (sd / math.sqrt(len(dm))) if sd > 0 else 0)
    zw, zm = np.array(zw), np.array(zm)
    print(f'   {len(zw)} variant pairs: mean z^2 win flips {np.mean(zw ** 2):.2f}, gem margin {np.mean(zm ** 2):.2f} '
          f'(1.0 = pure noise; larger = more signal detected); corr(z_win, z_margin) {np.corrcoef(zw, zm)[0, 1]:.2f}')
    print('   (z^2 - 1) ratio margin/win = relative effective sample size of the margin: '
          f'{(np.mean(zm ** 2) - 1) / (np.mean(zw ** 2) - 1):.2f}x' if np.mean(zw ** 2) > 1 else '   win z^2 <= 1')

    print('\n== G. Transfer: ladder effect vs local paired effect (vs v88 / via god84), weighted regression')
    # (local net flips pp vs v88 via god84 games, ladder net pp vs v88, ladder SE pp)
    pts = [('v85', 0.0, -4.7, 4.8), ('v86', 1.7, -2.8, 3.5), ('v87', 6.4, -1.2, 3.4), ('v89', 2.3, -4.1, 3.4),
           ('v90', 8.7, -3.7, 3.2), ('v92', 4.1, -5.6, 4.3), ('v95', 8.1, -0.5, 3.9)]
    x = np.array([p[1] for p in pts])
    y = np.array([p[2] for p in pts])
    s = np.array([p[3] for p in pts])
    w = 1 / s ** 2
    X = np.vstack([np.ones_like(x), x]).T
    W = np.diag(w)
    cov = np.linalg.inv(X.T @ W @ X)
    beta = cov @ X.T @ W @ y
    print(f'   ladder_pp = {beta[0]:+.2f} + {beta[1]:+.2f} x local_pp ; slope SE {math.sqrt(cov[1, 1]):.2f} -> 95% CI '
          f'[{beta[1] - 1.96 * math.sqrt(cov[1, 1]):+.2f}, {beta[1] + 1.96 * math.sqrt(cov[1, 1]):+.2f}] (1 = full transfer, 0 = none)')
    # the local panel predicted on average:
    print(f'   mean local predicted gain {x.mean():+.1f}pp, mean ladder result {np.average(y, weights=w):+.1f}pp '
          f'(SE {1 / math.sqrt(w.sum()):.1f}pp): difference z {(x.mean() - np.average(y, weights=w)) / math.sqrt(1 / w.sum() + 3.8 ** 2 / len(x)):.1f}')


if __name__ == '__main__':
    main()
