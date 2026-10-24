# Verification analyses of experiments/top2/an_opening.md claims C1-C7 on the records of vo_extract.py.
# Usage: python tools/top2/verify_opening/vo_an.py VO.jsonl FINGERPRINTS.json SECTION...   (sections: base c1 c2 c3 c4 c5 c6 c7)
import json, sys, math, statistics as stt
from collections import defaultdict, Counter
import numpy as np

CACHE = 'C:/battlecode/cache'
STUDY = {'pbg': 'prism best girl', 'ifish': 'Intercontinental Fish', 'pantheon': 'Pantheon', 'coo': 'conqueror_of_openai',
         'cm': 'Claudus Maximus', 'nyx': 'Nyx'}
KEYS = list(STUDY)


def load(path, fpp):
    G = [json.loads(l) for l in open(path, encoding='utf-8')]
    fps = {b: hf for b, k, h, hf in json.load(open(fpp))}
    for g in G:
        g['fp'] = fps[g['file']]
    return G


def pooled(G, by='fp'):
    seen, out = set(), []
    for g in G:
        k = g[by]
        if k in seen:
            continue
        seen.add(k)
        out.append(g)
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def pct(k, n):
    if n == 0:
        return '  -  (0)'
    lo, hi = wilson(k, n)
    return f'{100 * k / n:4.0f}% (n {n}; CI {100 * lo:.0f}-{100 * hi:.0f})'


def pwl(pairs):
    """pairs of (winner value, loser value); share winner > loser, ties 0.5; skips None"""
    s, n = 0.0, 0
    for w, l in pairs:
        if w is None or l is None:
            continue
        n += 1
        s += 1 if w > l else (0.5 if w == l else 0)
    return (s / n if n else float('nan')), n


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')


def med(xs):
    xs = [x for x in xs if x is not None]
    return stt.median(xs) if xs else float('nan')


def ts(g, t, c, k):
    return g['ts'][t][str(c)].get(k)


def spearman(x, y):
    from scipy.stats import spearmanr
    r, p = spearmanr(x, y)
    return r, p


def wl_series(P, fn):
    W, L = [], []
    for g in P:
        if g['winner'] < 0:
            continue
        w = g['winner']
        W.append(fn(g, w)); L.append(fn(g, 1 - w))
    return W, L


def report_wl(P, label, fn):
    W, L = wl_series(P, fn)
    p, n = pwl(zip(W, L))
    print(f'  {label:42s} W {mean(W):8.1f}  L {mean(L):8.1f}  medW {med(W):7.1f} medL {med(L):7.1f}  P(W>L) {p:.3f} (n {n})')


def bucket_rate(P, fn, edges, label):
    """team-0 difference buckets -> team 0 win rate; edges: list of (lo, hi, name) with lo < d <= hi"""
    print(f'  {label}')
    for lo, hi, name in edges:
        k = n = 0
        for g in P:
            if g['winner'] < 0:
                continue
            d = fn(g)
            if d is None:
                continue
            if lo < d <= hi:
                n += 1
                k += 1 if g['winner'] == 0 else 0
        print(f'    {name:>14s}: team0 wins {pct(k, n)}')


def lead_rate(P, fn, thr, label):
    """symmetric: games where |diff| > thr (or >= thr); share won by the leader"""
    k = n = 0
    for g in P:
        if g['winner'] < 0:
            continue
        d = fn(g)
        if d is None or abs(d) <= thr:
            continue
        n += 1
        lead = 0 if d > 0 else 1
        k += 1 if g['winner'] == lead else 0
    print(f'  {label}: leader wins {pct(k, n)}')
    return k, n


# --------------------------------------------------------------------------------------------------------------------
def sec_base(G, P):
    print('== base ==')
    print('dumps', len(G), 'unique match ids', len({g['mid'] for g in G}), 'unique contents', len(P))
    print('draft mismatches', sum(1 for g in G if not g['draftok']), 'result mismatches', sum(1 for g in G if not g['resok']),
          'spawn mismatches', sum(1 for g in G if not g['spawnok']))
    cm = [0, 0]
    for g in G:
        cm[0] += g['capmatch'][0]; cm[1] += g['capmatch'][1]
    print('capture steps mapped to a group', cm[0], 'whose summed gems equal the group gems', cm[1])
    print('games ending by r300', sum(1 for g in P if g['final'] <= 300), 'by r350', sum(1 for g in P if g['final'] <= 350),
          'final round median', med([g['final'] for g in P]))
    print('size classes', Counter(g['size'] for g in P))
    print('team-0 win share', mean([1 if g['winner'] == 0 else 0 for g in P]))
    for key in KEYS:
        mine = [g for g in G if g['key'] == key]
        w = sum(1 for g in mine if g['winner'] == g['study'])
        nbs = mean([g['nb'][g['study']] for g in mine])
        print(f'  {key:9s} games {len(mine)} W-L {w}-{len(mine) - w} ({100 * w / len(mine):.0f}%) mean bodies {nbs:.2f}')
    # gold estimator against the official platform earnedGold
    for c in (50, 100, 200, 300):
        diffs = []
        for g in G:
            if not g['has_off']:
                continue
            for t in (0, 1):
                diffs.append(ts(g, t, c, 'gold_est') - ts(g, t, c, 'gold_off'))
        ad = [abs(x) for x in diffs]
        print(f'  gold est - official r{c}: n {len(diffs)} mean {mean(diffs):.1f} mean|d| {mean(ad):.1f} exact {sum(1 for x in ad if x < 1) / len(ad):.2f} '
              f'within10 {sum(1 for x in ad if x <= 10) / len(ad):.2f}')


# --------------------------------------------------------------------------------------------------------------------
def logit_cv(X, y, names, label, reps=5):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    X = np.array(X, float); y = np.array(y)
    accs = []
    for s in range(reps):
        cv = StratifiedKFold(10, shuffle=True, random_state=s)
        m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
        accs.append(cross_val_score(m, X, y, cv=cv, scoring='accuracy').mean())
    m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)).fit(X, y)
    co = m[-1].coef_[0]
    order = np.argsort(-np.abs(co))
    print(f'  {label:34s} n {len(y)} cv-acc {np.mean(accs):.3f} (+-{np.std(accs):.3f})  coefs: ' +
          ', '.join(f'{names[i]} {co[i]:+.2f}' for i in order[:6]))
    return np.mean(accs)


def route_vals(g, t):
    r = g['route'][t]
    return r


def sec_c1(G, P):
    print('== C1 yield vs route ==')
    for c in (50, 100, 200, 300):
        report_wl(P, f'gold earned (est) r{c}', lambda g, t, c=c: ts(g, t, c, 'gold_est'))
    PO = [g for g in P if g['has_off']]
    for c in (50, 100, 200, 300):
        report_wl(PO, f'gold earned OFFICIAL r{c} (compact subset)', lambda g, t, c=c: ts(g, t, c, 'gold_off'))
    for c in (100, 200, 300):
        report_wl(P, f'captured gems r{c}', lambda g, t, c=c: ts(g, t, c, 'capgems'))
    report_wl(P, 'mid gems r100', lambda g, t: ts(g, t, 100, 'gems_mid'))
    print(' -- gap decomposition r100 (W-L means) --')
    for k in ('gold_est', 'capgold', 'killgold'):
        W, L = wl_series(P, lambda g, t, k=k: ts(g, t, 100, k))
        print(f'   {k:10s} W {mean(W):7.1f} L {mean(L):7.1f} gap {mean(W) - mean(L):6.1f}')
    W, L = wl_series(P, lambda g, t: ts(g, t, 100, 'gold_est') - ts(g, t, 100, 'capgold') - ts(g, t, 100, 'killgold'))
    print(f'   other(Marcella bank, est. error)  W {mean(W):7.1f} L {mean(L):7.1f}')
    edges200 = [(-1e9, -300, '< -300'), (-300, -150, '-300..-150'), (-150, -50, '-150..-50'), (-50, 50, '+-50'),
                (50, 150, '50..150'), (150, 300, '150..300'), (300, 1e9, '> 300')]
    bucket_rate(P, lambda g: ts(g, 0, 200, 'gold_est') - ts(g, 1, 200, 'gold_est'), edges200, 'gold diff r200 (team0-team1), est')
    lead_rate(P, lambda g: ts(g, 0, 200, 'gold_est') - ts(g, 1, 200, 'gold_est'), 300, 'gold lead > 300 at r200 (pooled symmetric)')
    lead_rate(P, lambda g: ts(g, 0, 300, 'gold_est') - ts(g, 1, 300, 'gold_est'), 0, 'gold ahead at r300')
    edgesg = [(-1e9, -60, '< -60'), (-60, -30, '-60..-30'), (-30, -10, '-30..-10'), (-10, 10, '+-10'), (10, 30, '10..30'),
              (30, 60, '30..60'), (60, 1e9, '> 60')]
    bucket_rate(P, lambda g: ts(g, 0, 200, 'capgems') - ts(g, 1, 200, 'capgems'), edgesg, 'captured gems diff r200')
    lead_rate(P, lambda g: ts(g, 0, 200, 'capgems') - ts(g, 1, 200, 'capgems'), 60, 'captured-gem lead > 60 at r200')
    # games long enough
    Plong = [g for g in P if g['final'] > 400]
    print(' -- games lasting beyond r400 only (n %d) --' % len(Plong))
    report_wl(Plong, 'gold earned r200', lambda g, t: ts(g, t, 200, 'gold_est'))
    lead_rate(Plong, lambda g: ts(g, 0, 200, 'gold_est') - ts(g, 1, 200, 'gold_est'), 300, 'gold lead > 300 at r200')
    print(' -- route features (W vs L) --')
    feats = [('first_move_team', 'first move round (team)'), ('first_move_med', 'first move round (median body)'),
             ('moved_r1', 'share moving in r1'), ('first_hit_team', 'first camp hit (team)'), ('first_hit_med', 'first camp hit (median body)'),
             ('main_walk', 'walk to main first group'), ('walk_med_body', 'walk to first group (median body)'),
             ('main_nearest', 'main group is nearest'), ('share_nearest', 'share of bodies on nearest'),
             ('main_elk', 'main group is elk group'), ('share_elk', 'share of bodies on elk'), ('squads', 'number of squads'),
             ('squad_share', 'main squad share'), ('first_cap', 'first capture round')]
    for k, lab in feats:
        report_wl(P, lab, lambda g, t, k=k: g['route'][t].get(k))
    report_wl(P, 'cohesion r51-100', lambda g, t: g['win'][t]['coh_51_100'])
    report_wl(P, 'cohesion r1-50', lambda g, t: g['win'][t]['coh_1_50'])
    report_wl(P, 'bodies in mid band r1-50', lambda g, t: g['win'][t]['mid_1_50'])
    report_wl(P, 'bodies in mid band r51-100', lambda g, t: g['win'][t]['mid_51_100'])
    # route -> yield: within-game Spearman of team-0-minus-team-1 differences
    print(' -- within-game Spearman, route diff vs gold r100 diff / gold r300 diff / won --')
    for k, lab in feats + [('coh', 'cohesion r51-100'), ('mid150', 'mid bodies r1-50'), ('mid100', 'mid bodies r51-100')]:
        xs, y1, y2, y3 = [], [], [], []
        for g in P:
            def v(t):
                if k == 'coh':
                    return g['win'][t]['coh_51_100']
                if k == 'mid150':
                    return g['win'][t]['mid_1_50']
                if k == 'mid100':
                    return g['win'][t]['mid_51_100']
                return g['route'][t].get(k)
            a, b = v(0), v(1)
            if a is None or b is None:
                continue
            xs.append(a - b)
            y1.append(ts(g, 0, 100, 'gold_est') - ts(g, 1, 100, 'gold_est'))
            y2.append(ts(g, 0, 300, 'gold_est') - ts(g, 1, 300, 'gold_est'))
            y3.append(1 if g['winner'] == 0 else -1)
        r1, p1 = spearman(xs, y1); r2, p2 = spearman(xs, y2); r3, p3 = spearman(xs, y3)
        print(f'   {lab:34s} n {len(xs)}  gold100 {r1:+.2f} (p {p1:.3f})  gold300 {r2:+.2f} (p {p2:.3f})  won {r3:+.2f} (p {p3:.3f})')
    # logistic models
    print(' -- 10-fold CV logistic (5 repeats), team-0 minus team-1 differences --')
    def diffrow(g, fns):
        row = []
        for fn in fns:
            a, b = fn(g, 0), fn(g, 1)
            if a is None or b is None:
                return None
            row.append(a - b)
        return row
    choice_fns = {
        'squad_share': lambda g, t: g['route'][t].get('squad_share'),
        'nearest': lambda g, t: g['route'][t].get('share_nearest'),
        'elk': lambda g, t: g['route'][t].get('share_elk'),
        'first_cap': lambda g, t: g['route'][t].get('first_cap') or 300,
        'mid1_50': lambda g, t: g['win'][t]['mid_1_50'],
        'first_move': lambda g, t: g['route'][t].get('first_move_med'),
        'first_hit': lambda g, t: g['route'][t].get('first_hit_med'),
        'walk': lambda g, t: g['route'][t].get('main_walk'),
        'squads': lambda g, t: g['route'][t].get('squads'),
        'coh51_100': lambda g, t: g['win'][t]['coh_51_100'],
    }
    state100 = {'gold': lambda g, t: ts(g, t, 100, 'gold_est'), 'deaths': lambda g, t: ts(g, t, 100, 'deaths'),
                'kills': lambda g, t: ts(g, t, 100, 'kills'), 'midgems': lambda g, t: ts(g, t, 100, 'gems_mid'),
                'capgems': lambda g, t: ts(g, t, 100, 'capgems'), 'banked': lambda g, t: ts(g, t, 100, 'banked'),
                'hpbought': lambda g, t: ts(g, t, 100, 'hpbought')}
    state300 = {k: (lambda g, t, f=f: f(g, t)) for k, f in [('gold', lambda g, t: ts(g, t, 300, 'gold_est')), ('deaths', lambda g, t: ts(g, t, 300, 'deaths')),
                                                         ('kills', lambda g, t: ts(g, t, 300, 'kills')), ('midgems', lambda g, t: ts(g, t, 300, 'gems_mid')),
                                                         ('banked', lambda g, t: ts(g, t, 300, 'banked')), ('carried', lambda g, t: ts(g, t, 300, 'carried')),
                                                         ('hpbought', lambda g, t: ts(g, t, 300, 'hpbought'))]}
    for label, fns, PP in [('choices r1-100', choice_fns, P), ('state r100', state100, P), ('state r300', state300, P),
                           ('state r300, games > r400', state300, [g for g in P if g['final'] > 400]),
                           ('gold r100 only', {'gold': state100['gold']}, P), ('gold r200 only', {'gold': lambda g, t: ts(g, t, 200, 'gold_est')}, P)]:
        X, y = [], []
        for g in PP:
            row = diffrow(g, list(fns.values()))
            if row is None or g['winner'] < 0:
                continue
            X.append(row); y.append(1 if g['winner'] == 0 else 0)
        logit_cv(X, y, list(fns.keys()), label)
    # strength control: ladder rating difference
    lad = json.load(open(CACHE + '/ladder_now.json', encoding='utf-8'))['teams']
    rating = {t['name']: t['rating'] for t in lad}
    X, y, X2 = [], [], []
    for g in P:
        a, b = rating.get(g['names'][0]), rating.get(g['names'][1])
        if a is None or b is None:
            continue
        X.append([a - b]); X2.append([a - b, ts(g, 0, 100, 'gold_est') - ts(g, 1, 100, 'gold_est'), ts(g, 0, 200, 'gold_est') - ts(g, 1, 200, 'gold_est')])
        y.append(1 if g['winner'] == 0 else 0)
    print(f'  games with both ladder ratings: {len(y)}')
    logit_cv(X, y, ['rating_diff'], 'rating diff only')
    logit_cv(X2, y, ['rating_diff', 'gold100', 'gold200'], 'rating diff + gold r100 + r200')
    X3 = [[x[0]] + diffrow(g, list(choice_fns.values())) for x, g in zip(X, [g for g in P if rating.get(g['names'][0]) is not None and rating.get(g['names'][1]) is not None])
          if diffrow(g, list(choice_fns.values())) is not None]
    # rating diff vs gold r100 diff correlation
    gg = [g for g in P if rating.get(g['names'][0]) is not None and rating.get(g['names'][1]) is not None]
    r_, p_ = spearman([rating[g['names'][0]] - rating[g['names'][1]] for g in gg], [ts(g, 0, 100, 'gold_est') - ts(g, 1, 100, 'gold_est') for g in gg])
    print(f'  Spearman rating diff vs gold r100 diff: {r_:+.2f} (p {p_:.4f})')


# --------------------------------------------------------------------------------------------------------------------
def first_kill(g, rmax=300):
    ks = [d for d in g['deaths'] if d['champ'] and d['r'] <= rmax]
    if not ks:
        return None
    ks.sort(key=lambda d: d['q'])
    return ks[0]['kt'], ks[0]['r']


def sec_c2(G, P):
    print('== C2 early deaths / first kill ==')
    edges = [(-99, -1.5, '<= -2'), (-1.5, -0.5, '-1'), (-0.5, 0.5, '0'), (0.5, 1.5, '+1'), (1.5, 99, '>= +2')]
    for k in ('deaths', 'death_events', 'deaths_champ'):
        bucket_rate(P, lambda g, k=k: ts(g, 0, 100, k) - ts(g, 1, 100, k), edges, f'{k} by r100, team0 minus team1')
    # symmetric pooled version
    for thr_lo, lab in ((1, 'exactly 1 fewer'), (2, '2+ fewer')):
        k = n = 0
        for g in P:
            d = ts(g, 0, 100, 'deaths') - ts(g, 1, 100, 'deaths')
            if (thr_lo == 1 and abs(d) == 1) or (thr_lo == 2 and abs(d) >= 2):
                n += 1
                fewer = 0 if d < 0 else 1
                k += 1 if g['winner'] == fewer else 0
        print(f'  pooled: team with {lab} body deaths by r100 wins {pct(k, n)}')
    for size in ('S', 'M', 'L', None):
        k = n = 0
        for g in P:
            if size and g['size'] != size:
                continue
            fk = first_kill(g)
            if fk is None:
                continue
            n += 1
            k += 1 if g['winner'] == fk[0] else 0
        print(f'  first champion kill by r300 -> killer team wins ({size or "all"}): {pct(k, n)}')
    k = n = 0
    for g in P:
        fk = first_kill(g, 100)
        if fk is None:
            continue
        n += 1; k += 1 if g['winner'] == fk[0] else 0
    print(f'  first kill by r100 -> killer team wins: {pct(k, n)}')
    for c in ('deaths', 'deaths_champ', 'deaths_camp', 'death_events', 'kills'):
        report_wl(P, f'{c} by r100', lambda g, t, c=c: ts(g, t, 100, c))
    report_wl(P, 'deaths by r300', lambda g, t: ts(g, t, 300, 'deaths'))
    # study-team specifics
    for key in KEYS:
        mine = [g for g in G if g['key'] == key]
        k = n = 0
        for g in mine:
            s = g['study']
            if ts(g, s, 100, 'deaths') > ts(g, 1 - s, 100, 'deaths'):
                n += 1; k += 1 if g['winner'] == s else 0
        k2 = n2 = 0
        for g in mine:
            s = g['study']
            if ts(g, s, 100, 'death_events') > ts(g, 1 - s, 100, 'death_events'):
                n2 += 1; k2 += 1 if g['winner'] == s else 0
        losses = [g for g in mine if g['winner'] != g['study']]
        kl = mean([ts(g, g['study'], 100, 'kills') for g in losses]); ko = mean([ts(g, 1 - g['study'], 100, 'kills') for g in losses])
        print(f'  {key:9s} wins when it has more body deaths by r100: {pct(k, n)}; more death events: {pct(k2, n2)};'
              f' in losses kills r100 own {kl:.2f} vs opp {ko:.2f}')
    # generic: team with more body deaths by r100 wins
    k = n = 0
    for g in P:
        d = ts(g, 0, 100, 'deaths') - ts(g, 1, 100, 'deaths')
        if d == 0:
            continue
        n += 1; more = 0 if d > 0 else 1
        k += 1 if g['winner'] == more else 0
    print(f'  generic: team with more body deaths by r100 wins {pct(k, n)}')


# --------------------------------------------------------------------------------------------------------------------
def eng_out(e, mode='bodies'):
    a, b = (e['dead_s'], e['dead_v']) if mode == 'bodies' else (e['kev_s'], e['kev_v'])
    return 'W' if a < b else ('L' if a > b else 'T')


def sec_c3(G, P):
    print('== C3 fights ==')
    E = []
    for g in P:
        for e in g['engs']:
            if e['r'] <= 300 and (e['dead_s'] + e['dead_v']) > 0:
                E.append((g, e))
    for mode in ('bodies', 'events'):
        c = Counter(eng_out(e, mode) for g, e in E)
        n = len(E)
        print(f'  kill-engagements r<=300: n {n}; striker W {c["W"] / n:.2f} L {c["L"] / n:.2f} T {c["T"] / n:.2f}  ({mode})')
    def tab(keyfn, bins, label, field='ln'):
        print(f'  {label}')
        for lo, hi, name in bins:
            sub = [(g, e) for g, e in E if lo <= keyfn(e) <= hi]
            n = len(sub)
            if not n:
                continue
            c = Counter(eng_out(e) for g, e in sub)
            lo_, hi_ = wilson(c['W'], n)
            print(f'    {name:>10s}: W {c["W"] / n:.2f} L {c["L"] / n:.2f} (n {n}; W CI {lo_:.2f}-{hi_:.2f})')
    nb = [(-99, -2, '<= -2'), (-1, -1, '-1'), (0, 0, '0'), (1, 1, '+1'), (2, 99, '>= +2')]
    tab(lambda e: e['ln_s'] - e['ln_v'], nb, 'local numbers (Chebyshev 8, one round before)')
    tab(lambda e: e['le_s'] - e['le_v'], nb, 'local numbers (Euclidean 8)')
    hb = [(-1e9, -1500.01, '< -1500'), (-1500, -500.01, '-1500..-500'), (-500, 500, '+-500'), (500.01, 1500, '500..1500'), (1500.01, 1e9, '> 1500')]
    tab(lambda e: e['lh_s'] - e['lh_v'], hb, 'local current-HP difference')
    # does the striker edge at even numbers depend on HP?
    sub = [(g, e) for g, e in E if e['ln_s'] == e['ln_v']]
    print('  even numbers, split by HP diff sign:')
    for lab, f in (('striker HP ahead', lambda e: e['lh_s'] > e['lh_v']), ('striker HP behind/equal', lambda e: e['lh_s'] <= e['lh_v'])):
        ss = [(g, e) for g, e in sub if f(e)]
        c = Counter(eng_out(e) for g, e in ss)
        print(f'    {lab}: W {c["W"] / max(1, len(ss)):.2f} L {c["L"] / max(1, len(ss)):.2f} n {len(ss)}')
    # victim side perspective: all kill-engagements by local-number advantage of either side (striker-agnostic)
    print('  side-agnostic: side with more local bodies wins (fewer deaths):')
    k = n = t_ = 0
    for g, e in E:
        d = e['ln_s'] - e['ln_v']
        if d == 0:
            continue
        o = eng_out(e)
        n += 1
        if o == 'T':
            t_ += 1
        elif (d > 0 and o == 'W') or (d < 0 and o == 'L'):
            k += 1
    print(f'    {pct(k, n)}, ties {t_}')
    # per study team (own folders)
    print('  per study team (own folder, r<=300 kill-engagements): opened W rate / received W rate / share opened / mean local diff opened, received')
    for key in KEYS:
        o = r = 0; ow = rw = 0; ldo, ldr = [], []
        allE = 0; opened_all = 0
        for g in G:
            if g['key'] != key:
                continue
            s = g['study']
            for e in g['engs']:
                if e['r'] > 300:
                    continue
                allE += 1
                if e['s'] == s:
                    opened_all += 1
                if e['dead_s'] + e['dead_v'] == 0:
                    continue
                out = eng_out(e)
                if e['s'] == s:
                    o += 1; ow += out == 'W'; ldo.append(e['ln_s'] - e['ln_v'])
                else:
                    r += 1; rw += out == 'L'; ldr.append(e['ln_v'] - e['ln_s'])
        print(f'    {key:9s} opened {pct(ow, o)} | received {pct(rw, r)} | share opened (all eng) {opened_all / max(1, allE):.2f} | local diff {mean(ldo):+.2f} / {mean(ldr):+.2f}')
    # first fight striker -> game
    k = n = 0; k2 = n2 = 0
    for g in P:
        es = sorted(g['engs'], key=lambda e: e['r'])
        if not es or es[0]['r'] > 300:
            continue
        n += 1; k += 1 if g['winner'] == es[0]['s'] else 0
        e = es[0]
        if e['dead_s'] != e['dead_v']:
            n2 += 1
            wside = e['s'] if e['dead_s'] < e['dead_v'] else 1 - e['s']
            k2 += 1 if g['winner'] == wside else 0
    print(f'  first fight (r<=300) striker wins the game {pct(k, n)}; winner of the first fight (fewer deaths) wins the game {pct(k2, n2)}')


# --------------------------------------------------------------------------------------------------------------------
def sec_c4(G, P):
    print('== C4 middle ==')
    for z in ('own', 'mid', 'enemy', 'x'):
        report_wl(P, f'captures r<=300 zone {z}', lambda g, t, z=z: ts(g, t, 300, 'ncap_' + z))
    for z in ('own', 'mid', 'enemy'):
        for c in (100, 300):
            report_wl(P, f'gems zone {z} r{c}', lambda g, t, z=z, c=c: ts(g, t, c, 'gems_' + z))
    edgesg = [(-1e9, -60, '< -60'), (-60, -30, '-60..-30'), (-30, -10, '-30..-10'), (-10, 10, '+-10'), (10, 30, '10..30'),
              (30, 60, '30..60'), (60, 1e9, '> 60')]
    bucket_rate(P, lambda g: ts(g, 0, 300, 'gems_mid') - ts(g, 1, 300, 'gems_mid'), edgesg, 'mid gems diff r300 (team0-team1)')
    lead_rate(P, lambda g: ts(g, 0, 300, 'gems_mid') - ts(g, 1, 300, 'gems_mid'), 29.5, 'mid-gem lead >= 30 at r300')
    lead_rate(P, lambda g: ts(g, 0, 300, 'gems_own') - ts(g, 1, 300, 'gems_own'), 29.5, 'own-zone-gem lead >= 30 at r300')
    lead_rate(P, lambda g: ts(g, 0, 300, 'capgems') - ts(g, 1, 300, 'capgems'), 29.5, 'total captured-gem lead >= 30 at r300')
    lead_rate(P, lambda g: (ts(g, 0, 300, 'capgems') - ts(g, 0, 300, 'gems_mid')) - (ts(g, 1, 300, 'capgems') - ts(g, 1, 300, 'gems_mid')), 29.5,
              'NON-mid captured-gem lead >= 30 at r300')
    # within-game Spearman
    print(' -- within-game Spearman (team0 - team1) --')
    for w in ('1_50', '51_100', '101_150', '151_200', '201_300'):
        xs, ym, yw, yg = [], [], [], []
        for g in P:
            a, b = g['win'][0]['mid_' + w], g['win'][1]['mid_' + w]
            if a is None or b is None:
                continue
            xs.append(a - b); ym.append(ts(g, 0, 300, 'gems_mid') - ts(g, 1, 300, 'gems_mid')); yw.append(1 if g['winner'] == 0 else -1)
            yg.append(ts(g, 0, 300, 'gold_est') - ts(g, 1, 300, 'gold_est'))
        r1, p1 = spearman(xs, ym); r2, p2 = spearman(xs, yw); r3, p3 = spearman(xs, yg)
        print(f'   mid bodies r{w:8s} vs mid gems r300 {r1:+.2f} (p {p1:.3g}) | won {r2:+.2f} (p {p2:.3g}) | gold r300 {r3:+.2f} (n {len(xs)})')
    # partial: does mid presence r51-100 predict winning beyond gold r100? logistic with both
    # midShare maps
    geo = {json.loads(l)['map']: json.loads(l) for l in open(CACHE + '/an_strategy/mapgeo2.jsonl', encoding='utf-8')}
    for lab, sel in (('mapgeo midShare > 0.75', lambda g: geo[g['map']]['feat']['midShare'] > 0.75),
                     ('my midShare > 0.75', lambda g: g['midshare'] > 0.75),
                     ('mapgeo midShare <= 0.75', lambda g: geo[g['map']]['feat']['midShare'] <= 0.75)):
        PP = [g for g in P if sel(g)]
        print(f'  {lab}: games {len(PP)}, maps {len({g["map"] for g in PP})}')
        report_wl(PP, '   first mid capture (no capture = 301)', lambda g, t: g['route'][t]['first_midcap'] or 301)
        report_wl(PP, '   first mid capture (only games with both)', lambda g, t: g['route'][t]['first_midcap'] if (g['route'][0]['first_midcap'] and g['route'][1]['first_midcap']) else None)
        report_wl(PP, '   first capture', lambda g, t: g['route'][t]['first_cap'] or 301)
        report_wl(PP, '   mid gems r300', lambda g, t: ts(g, t, 300, 'gems_mid'))
        report_wl(PP, '   own gems r300', lambda g, t: ts(g, t, 300, 'gems_own'))
    print('  my midShare per map:', sorted({(g['map'], round(g['midshare'], 2), round(geo[g['map']]['feat']['midShare'], 2)) for g in P}, key=lambda x: -x[1]))


# --------------------------------------------------------------------------------------------------------------------
def sec_c5(G, P):
    print('== C5 exploits ==')
    conds = {
        'opp first kill (r<=300)': lambda g, s: (first_kill(g) is not None and first_kill(g)[0] == 1 - s),
        'opp strikes first in first fight': lambda g, s: (lambda es: bool(es) and es[0]['r'] <= 300 and es[0]['s'] == 1 - s)(sorted(g['engs'], key=lambda e: e['r'])),
        'study more body deaths r100': lambda g, s: ts(g, s, 100, 'deaths') > ts(g, 1 - s, 100, 'deaths'),
        'opp +100 gold r100': lambda g, s: ts(g, 1 - s, 100, 'gold_est') - ts(g, s, 100, 'gold_est') >= 100,
        'opp +30 mid gems r300': lambda g, s: ts(g, 1 - s, 300, 'gems_mid') - ts(g, s, 300, 'gems_mid') >= 30,
        'opp +300 HP bought r200': lambda g, s: ts(g, 1 - s, 200, 'hpbought') - ts(g, s, 200, 'hpbought') >= 300,
        'opp +1 mid bodies r51-150': lambda g, s: ((g['win'][1 - s]['mid_51_100'] + g['win'][1 - s]['mid_101_150']) - (g['win'][s]['mid_51_100'] + g['win'][s]['mid_101_150'])) / 2 >= 1,
    }
    # generic rates: any team (both sides of every pooled game) in the same situation
    print('  condition: generic (any team, pooled both sides) | per study team: rate (n) [drop vs own baseline]')
    for cname, cf in conds.items():
        k = n = 0
        for g in P:
            for s in (0, 1):
                if cf(g, s):
                    n += 1; k += 1 if g['winner'] == s else 0
        line = f'  {cname:34s} generic {100 * k / max(1, n):.0f}% (n {n}) |'
        for key in KEYS:
            mine = [g for g in G if g['key'] == key]
            base = sum(1 for g in mine if g['winner'] == g['study']) / len(mine)
            sub = [g for g in mine if cf(g, g['study'])]
            kk = sum(1 for g in sub if g['winner'] == g['study'])
            lo, hi = wilson(kk, len(sub))
            line += f' {key} {100 * kk / max(1, len(sub)):.0f}% ({len(sub)}; {100 * lo:.0f}-{100 * hi:.0f}) [{100 * (kk / max(1, len(sub)) - base):+.0f}] |'
        print(line)
    for key in KEYS:
        mine = [g for g in G if g['key'] == key]
        base = sum(1 for g in mine if g['winner'] == g['study'])
        print(f'  {key:9s} baseline {pct(base, len(mine))}; base HP {mean([g["base_hp"][g["study"]] for g in mine]):.0f} vs opp {mean([g["base_hp"][1 - g["study"]] for g in mine]):.0f};'
              f' HP bought r200 {mean([ts(g, g["study"], 200, "hpbought") for g in mine]):.0f} vs {mean([ts(g, 1 - g["study"], 200, "hpbought") for g in mine]):.0f};'
              f' carried r300 {mean([ts(g, g["study"], 300, "carried") for g in mine]):.1f} vs {mean([ts(g, 1 - g["study"], 300, "carried") for g in mine]):.1f}')
    # generic: when do teams win after being 100 gold behind at r100 / opponent first kill: compare per-team drops to the generic drop
    # Opponent strength confound: opponents' ladder rating when the condition holds vs not
    lad = json.load(open(CACHE + '/ladder_now.json', encoding='utf-8'))['teams']
    rating = {t['name']: t['rating'] for t in lad}
    print('  opponent ladder rating when condition holds vs not (study team folders):')
    for cname, cf in conds.items():
        line = f'   {cname:34s}'
        for key in KEYS:
            mine = [g for g in G if g['key'] == key]
            a = [rating.get(g['names'][1 - g['study']]) for g in mine if cf(g, g['study'])]
            b = [rating.get(g['names'][1 - g['study']]) for g in mine if not cf(g, g['study'])]
            line += f' {key} {mean(a):.0f}/{mean(b):.0f} |'
        print(line)


# --------------------------------------------------------------------------------------------------------------------
def clogit_fit(sets, feats, ridge=0.01):
    from scipy.optimize import minimize
    Xs, ys = [], []
    for s in sets:
        X = np.array([[f(c) for f in feats.values()] for c in s['set']], float)
        y = np.array([1 if c['g'] == s['chosen'] else 0 for c in s['set']])
        if y.sum() != 1 or len(y) < 2:
            continue
        Xs.append(X); ys.append(y)
    k = len(feats)
    def nll(b):
        tot = 0.0; grad = np.zeros(k)
        for X, y in zip(Xs, ys):
            u = X @ b
            m = u.max()
            e = np.exp(u - m)
            p = e / e.sum()
            tot -= (u[y == 1][0] - m - math.log(e.sum()))
            grad -= X[y == 1][0] - p @ X
        tot += ridge * (b @ b); grad += 2 * ridge * b
        return tot, grad
    res = minimize(nll, np.zeros(k), jac=True, method='L-BFGS-B')
    b = res.x
    hit = np.mean([1 if np.argmax(X @ b) == np.argmax(y) else 0 for X, y in zip(Xs, ys)])
    return b, hit, len(Xs)


def rule_hit(sets, U):
    h = n = 0
    for s in sets:
        if not s['set']:
            continue
        best = max(s['set'], key=U)
        n += 1; h += 1 if best['g'] == s['chosen'] else 0
    return h / max(1, n), n


def sec_c6(G, P):
    print('== C6 squad and target ==')
    rows = defaultdict(list)
    for key in KEYS:
        for g in G:
            if g['key'] != key:
                continue
            s = g['study']
            rows[key].append(g['route'][s])
    opp = []
    for g in P:  # opponents of study teams: in pooled games, the non-study side(s)
        pass
    for g in G:
        opp.append(g['route'][1 - g['study']])
    def summ(lst, lab):
        sh = mean([r.get('squad_share') for r in lst]); elk = mean([r.get('main_elk') for r in lst]); near = mean([r.get('main_nearest') for r in lst])
        top3 = mean([1 if (r.get('main_rank') or 99) <= 3 else 0 for r in lst if r.get('main_rank')])
        mz = mean([1 if r.get('main_zone') == 'mid' else 0 for r in lst if r.get('main_zone')])
        ez = mean([1 if r.get('main_zone') == 'enemy' else 0 for r in lst if r.get('main_zone')])
        print(f'  {lab:10s} n {len(lst)} squad share {sh:.2f} | elk {elk:.2f} | nearest {near:.2f} | top3 {top3:.2f} | mid {mz:.2f} | enemy {ez:.2f} | walk med {med([r.get("main_walk") for r in lst])}')
    for key in KEYS:
        summ(rows[key], key)
    summ(opp, 'opponents')
    print(' -- winners vs losers (pooled) --')
    for k in ('main_nearest', 'main_elk', 'squad_share', 'share_nearest', 'share_elk'):
        report_wl(P, k, lambda g, t, k=k: g['route'][t].get(k))
    xs, ys = [], []
    for g in P:
        a, b = g['route'][0].get('squad_share'), g['route'][1].get('squad_share')
        if a is None or b is None:
            continue
        xs.append(a - b); ys.append(ts(g, 0, 300, 'gold_est') - ts(g, 1, 300, 'gold_est'))
    r_, p_ = spearman(xs, ys)
    print(f'  within-game Spearman squad share diff vs gold r300 diff: {r_:+.2f} (p {p_:.4f}, n {len(xs)})')
    # conditional logit
    feats = {'ln_walk': lambda c: math.log(1 + c['walk']), 'ln_gems': lambda c: math.log(1 + c['gems']), 'ln_gold': lambda c: math.log(1 + c['gold']),
             'mid': lambda c: 1.0 if c['zone'] == 'mid' else 0.0, 'enemy': lambda c: 1.0 if c['zone'] == 'enemy' else 0.0,
             'elk': lambda c: 1.0 if c['cls'] == 'elk' else 0.0, 'golem': lambda c: 1.0 if c['cls'] == 'golem' else 0.0,
             'wolf': lambda c: 1.0 if c['cls'] == 'wolf' else 0.0}
    for key in KEYS + ['opp']:
        if key == 'opp':
            sets = [g['choice'][1 - g['study']] for g in G if g['choice'][1 - g['study']]]
        else:
            sets = [g['choice'][g['study']] for g in G if g['key'] == key and g['choice'][g['study']]]
        b, hit, n = clogit_fit(sets, feats)
        U = lambda c: 1.0 * math.log(1 + c['gold']) + 0.5 * (c['cls'] == 'elk') - 2.0 * math.log(1 + c['walk']) - 1.6 * (c['zone'] == 'enemy')
        rh, rn = rule_hit(sets, U)
        nh, _ = rule_hit(sets, lambda c: -c['walk'] + 1e-6 * c['gold'])
        sh, _ = rule_hit(sets, lambda c: (c['gems'] + c['gold'] / 10) / (c['walk'] + 5))
        print(f'  clogit {key:9s} n {n} in-sample hit {hit:.2f} | ' + ' '.join(f'{k} {v:+.2f}' for k, v in zip(feats, b)) +
              f' || god2 U-rule hit {rh:.2f}, nearest-rule {nh:.2f}, (gems+gold/10)/(d+5) {sh:.2f}')
    # out-of-sample (leave-one-out by halves) for pbg + ifish pooled
    sets = [g['choice'][g['study']] for g in G if g['key'] in ('pbg', 'ifish') and g['choice'][g['study']]]
    import random
    random.seed(1)
    idx = list(range(len(sets))); random.shuffle(idx)
    half = len(idx) // 2
    A = [sets[i] for i in idx[:half]]; B = [sets[i] for i in idx[half:]]
    bA, _, _ = clogit_fit(A, feats); bB, _, _ = clogit_fit(B, feats)
    def hit_with(b, S):
        hs = []
        for s in S:
            X = np.array([[f(c) for f in feats.values()] for c in s['set']], float)
            ch = [i for i, c in enumerate(s['set']) if c['g'] == s['chosen']]
            if not ch:
                continue
            hs.append(1 if int(np.argmax(X @ b)) == ch[0] else 0)
        return mean(hs)
    print(f'  pbg+ifish split-half out-of-sample hit: {hit_with(bA, B):.2f} / {hit_with(bB, A):.2f}')


# --------------------------------------------------------------------------------------------------------------------
def sec_c7(G, P):
    print('== C7 bodies per group ==')
    C = []
    for g in P:
        for c in g['caps']:
            if c['r'] <= 300 and c.get('first_own') is not None and c.get('g') is not None:
                C.append((g, c))
    print(f'  captures r<=300 with own hits: {len(C)}; uncontested {sum(1 for g, c in C if c["opp_hits"] == 0)}')
    for cls in ('elk', 'wolf', 'gem', 'gold', 'golem'):
        sub = [(g, c) for g, c in C if c['cls'] == cls and c['opp_hits'] == 0]
        line = f'  {cls:6s}'
        for h in (1, 2, 3, 4, 5, 6):
            ss = [c['r'] - c['first_own'] for g, c in sub if (c['hitters'] == h if h < 6 else c['hitters'] >= 6)]
            if ss:
                line += f' | {h}{"+" if h == 6 else ""}: med {med(ss):.0f} mean {mean(ss):.1f} (n {len(ss)})'
        print(line)
    # confounder: group HP vs hitters for elk groups
    sub = [(g, c) for g, c in C if c['cls'] == 'elk' and c['opp_hits'] == 0]
    print('  elk groups: mean group HP by hitters:', {h: round(mean([c['ghp'] for g, c in sub if min(c['hitters'], 6) == h])) for h in range(1, 7)})
    print('  elk groups: mean #elks by hitters:', {h: round(mean([c['gnelk'] for g, c in sub if min(c['hitters'], 6) == h]), 2) for h in range(1, 7)})
    # stratify by number of elks in the group (1 elk vs 2 elks vs 3+)
    for ne in (1, 2, 3):
        ss = [(g, c) for g, c in sub if (c['gnelk'] == ne if ne < 3 else c['gnelk'] >= 3)]
        line = f'  elk groups with {ne}{"+" if ne == 3 else ""} elk(s):'
        for h in (1, 2, 3, 4, 5, 6):
            v = [c['r'] - c['first_own'] for g, c in ss if min(c['hitters'], 6) == h]
            if len(v) >= 10:
                line += f' {h}{"+" if h == 6 else ""}h med {med(v):.0f} (n {len(v)});'
        print(line)
    # regression: time ~ hitters + group HP (elk, uncontested)
    X = np.array([[1, c['hitters'], c['ghp'] / 1000] for g, c in sub], float)
    y = np.array([c['r'] - c['first_own'] for g, c in sub], float)
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    print(f'  OLS elk time = {b[0]:.1f} + {b[1]:+.2f}*hitters + {b[2]:+.2f}*groupHP(k)  (n {len(y)})')
    X = np.array([[1, math.log(c['hitters']), math.log(c['ghp'])] for g, c in sub], float)
    yl = np.log(np.maximum(1, y))
    b = np.linalg.lstsq(X, yl, rcond=None)[0]
    print(f'  log-log elk: elasticity wrt hitters {b[1]:+.2f}, wrt group HP {b[2]:+.2f}')
    # per-hitter damage throughput: time from first hit to capture minus 6 capture rounds, HP per hitter-round
    # rewards split
    print('  mean capturers per capture step (r<=300):', round(mean([c['ncap'] for g, c in C]), 2),
          '| elk groups:', round(mean([c['ncap'] for g, c in C if c['cls'] == 'elk']), 2))
    for key in KEYS:
        caps = [c for g in G if g['key'] == key for c in g['caps'] if c['t'] == g['study'] and c['r'] <= 300]
        big = [c for c in caps if c['gems'] >= 15]
        vs = sum(1 for c in big if 'VesperVale' in c['whot'])
        vg = sum(gm for c in big for w, gm in zip(c['whot'], c['whogems']) if w == 'VesperVale')
        tg = sum(c['gems'] for c in big)
        has_v = sum(1 for g in G if g['key'] == key and 'VesperVale' in g['types'][g['study']])
        elk = [c for c in caps if c.get('cls') == 'elk']
        ngames = sum(1 for g in G if g['key'] == key)
        print(f'  {key:9s} large rewards {len(big)}: Vesper among capturers {vs / max(1, len(big)):.2f}, Vesper gem share {vg / max(1, tg):.2f} (Vesper drafted in {has_v}/{ngames});'
              f' elk captures/game {len(elk) / ngames:.2f}, hitters per elk capture {mean([c["hitters"] for c in elk]):.2f}, ncap {mean([c["ncap"] for c in caps]):.2f}')
    caps = [c for g in G for c in g['caps'] if c['t'] == 1 - g['study'] and c['r'] <= 300]
    elk = [c for c in caps if c.get('cls') == 'elk']
    print(f'  opponents: elk captures/game {len(elk) / len(G):.2f}, hitters per elk capture {mean([c["hitters"] for c in elk]):.2f}')


if __name__ == '__main__':
    G = load(sys.argv[1], sys.argv[2])
    P = pooled(G)
    for s in sys.argv[3:]:
        globals()['sec_' + s](G, P)
