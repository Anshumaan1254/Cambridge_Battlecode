# Confounder checks for the verification of an_opening.md (C1-C6), on the records of vo_extract.py.
# Usage: python tools/top2/verify_opening/vo_extra.py VO.jsonl FINGERPRINTS.json SECTION...  (x1 x2 x3 x4 x5)
import json, sys, math
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
from vo_an import load, pooled, pct, wilson, mean, med, ts, spearman, report_wl, first_kill, KEYS, CACHE, logit_cv, eng_out


def x1(G, P):
    print('== X1: are the C1 gold KPIs map-independent? ==')
    for lab, fn in (('size', lambda g, t: g['size']), ('picks', lambda g, t: g['picks'][t]), ('bodies', lambda g, t: g['nb'][t])):
        groups = defaultdict(lambda: [[], [], [], []])
        for g in P:
            w = g['winner']
            k = fn(g, w)
            if fn(g, 1 - w) != k:
                continue
            groups[k][0].append(ts(g, w, 100, 'gold_est')); groups[k][1].append(ts(g, 1 - w, 100, 'gold_est'))
            groups[k][2].append(ts(g, w, 200, 'gold_est')); groups[k][3].append(ts(g, 1 - w, 200, 'gold_est'))
        for k in sorted(groups):
            a = groups[k]
            print(f'  {lab} {k}: n {len(a[0])} gold r100 W {mean(a[0]):.0f} L {mean(a[1]):.0f} | r200 W {mean(a[2]):.0f} L {mean(a[3]):.0f}')
    # absolute threshold: how often do winners reach 400 / 900, and losers?
    W100 = [ts(g, g['winner'], 100, 'gold_est') for g in P]; L100 = [ts(g, 1 - g['winner'], 100, 'gold_est') for g in P]
    W200 = [ts(g, g['winner'], 200, 'gold_est') for g in P]; L200 = [ts(g, 1 - g['winner'], 200, 'gold_est') for g in P]
    print(f'  share reaching >=400 at r100: winners {np.mean([x >= 400 for x in W100]):.2f} losers {np.mean([x >= 400 for x in L100]):.2f}')
    print(f'  share reaching >=900 at r200: winners {np.mean([x >= 900 for x in W200]):.2f} losers {np.mean([x >= 900 for x in L200]):.2f}')
    # absolute-threshold win rate (team level, both sides)
    for thr in (323, 400):
        k = n = 0; k2 = n2 = 0
        for g in P:
            for t in (0, 1):
                if ts(g, t, 100, 'gold_est') >= thr:
                    n += 1; k += g['winner'] == t
                else:
                    n2 += 1; k2 += g['winner'] == t
        print(f'  team with gold r100 >= {thr}: wins {pct(k, n)}; below: {pct(k2, n2)}')
    # relative: ahead of the opponent at r100
    # "below 323 at r100 -> stop contesting": among teams below 323, win rate by mid presence r101-200 and by engagements opened r101-200
    print('  teams with gold r100 < 323: win rate by own mid presence r101-200 (mean bodies) and by engagements opened r101-200')
    rows = []
    for g in P:
        for t in (0, 1):
            if ts(g, t, 100, 'gold_est') < 323:
                midp = (g['win'][t]['mid_101_150'] + g['win'][t]['mid_151_200']) / 2
                opened = sum(1 for e in g['engs'] if 100 < e['r'] <= 200 and e['s'] == t)
                gap = ts(g, t, 100, 'gold_est') - ts(g, 1 - t, 100, 'gold_est')
                rows.append((midp, opened, g['winner'] == t, gap))
    for lo, hi in ((0, 0.75), (0.75, 1.5), (1.5, 9)):
        s = [r for r in rows if lo <= r[0] < hi]
        print(f'    mid presence {lo}-{hi}: {pct(sum(r[2] for r in s), len(s))} mean gap r100 {mean([r[3] for r in s]):.0f}')
    for lo, hi in ((0, 0), (1, 2), (3, 99)):
        s = [r for r in rows if lo <= r[1] <= hi]
        print(f'    engagements opened r101-200 {lo}-{hi}: {pct(sum(r[2] for r in s), len(s))} mean gap r100 {mean([r[3] for r in s]):.0f}')


def x2(G, P):
    print('== X2: first kill / early deaths confounders ==')
    # first kill when kills by r300 end level
    k = n = 0; kk = nn = 0
    for g in P:
        fk = first_kill(g)
        if fk is None:
            continue
        a, b = ts(g, 0, 300, 'kills'), ts(g, 1, 300, 'kills')
        if a == b:
            n += 1; k += g['winner'] == fk[0]
        else:
            nn += 1; lead = 0 if a > b else 1
            kk += g['winner'] == lead
    print(f'  first-kill team wins when kills by r300 are level: {pct(k, n)}; team ahead on kills by r300 wins: {pct(kk, nn)}')
    # first kill + rating
    lad = json.load(open(CACHE + '/ladder_now.json', encoding='utf-8'))['teams']
    rating = {t['name']: t['rating'] for t in lad}
    X, y = [], []
    for g in P:
        fk = first_kill(g)
        X.append([rating[g['names'][0]] - rating[g['names'][1]], 0 if fk is None else (1 if fk[0] == 0 else -1),
                  ts(g, 0, 100, 'deaths') - ts(g, 1, 100, 'deaths')])
        y.append(1 if g['winner'] == 0 else 0)
    logit_cv(X, y, ['rating', 'firstkill', 'deaths100'], 'rating + first kill + deaths r100')
    logit_cv([x[:1] for x in X], y, ['rating'], 'rating only')
    # ifish losses: opponent body kills (C&I counted twice) by r100
    loss = [g for g in G if g['key'] == 'ifish' and g['winner'] != g['study']]
    print(f'  ifish losses n {len(loss)}: opp kill events r100 {mean([ts(g, 1 - g["study"], 100, "kills") for g in loss]):.2f}, ifish body deaths r100 {mean([ts(g, g["study"], 100, "deaths") for g in loss]):.2f}, '
          f'ifish death events r100 {mean([ts(g, g["study"], 100, "death_events") for g in loss]):.2f}, ifish kills r100 {mean([ts(g, g["study"], 100, "kills") for g in loss]):.2f}')
    # effect sizes: Spearman with won (team0-team1) for deaths r100 vs best route features
    for lab, fn in (('deaths r100', lambda g, t: ts(g, t, 100, 'deaths')), ('kills r100', lambda g, t: ts(g, t, 100, 'kills')),
                    ('main squad share', lambda g, t: g['route'][t].get('squad_share')), ('main nearest', lambda g, t: g['route'][t].get('main_nearest'))):
        xs, ys = [], []
        for g in P:
            a, b = fn(g, 0), fn(g, 1)
            if a is None or b is None:
                continue
            xs.append(a - b); ys.append(1 if g['winner'] == 0 else -1)
        r, p = spearman(xs, ys)
        print(f'  within-game Spearman with won: {lab:18s} {r:+.3f} (p {p:.3g})')


def x3(G, P):
    print('== X3: fights - striker vs local numbers ==')
    E = [(g, e) for g in P for e in g['engs'] if e['r'] <= 300 and e['dead_s'] + e['dead_v'] > 0]
    print('  side with local advantage d: win rate (fewer deaths) when it strikes vs when it is struck')
    for d in (0, 1, 2):
        if d == 0:
            sub = [(g, e) for g, e in E if e['ln_s'] == e['ln_v']]
            c = Counter(eng_out(e) for g, e in sub)
            print(f'    even: striker W {c["W"]}/{len(sub)} = {c["W"] / len(sub):.2f}, struck side W {c["L"] / len(sub):.2f}')
            continue
        strike = [(g, e) for g, e in E if (e['ln_s'] - e['ln_v'] == d if d < 2 else e['ln_s'] - e['ln_v'] >= 2)]
        struck = [(g, e) for g, e in E if (e['ln_v'] - e['ln_s'] == d if d < 2 else e['ln_v'] - e['ln_s'] >= 2)]
        ws = sum(1 for g, e in strike if eng_out(e) == 'W'); wt = sum(1 for g, e in struck if eng_out(e) == 'L')
        ls = sum(1 for g, e in strike if eng_out(e) == 'L'); lt = sum(1 for g, e in struck if eng_out(e) == 'W')
        print(f'    +{d}{"+" if d == 2 else ""}: striking W {pct(ws, len(strike))} (L {ls / max(1, len(strike)):.2f}) | struck W {pct(wt, len(struck))} (L {lt / max(1, len(struck)):.2f}) | '
              f'pooled {pct(ws + wt, len(strike) + len(struck))}')
    # all engagements, with or without kills
    A = [(g, e) for g in P for e in g['engs'] if e['r'] <= 300]
    print(f'  all engagements r<=300 n {len(A)}; with a kill {sum(1 for g, e in A if e["dead_s"] + e["dead_v"] > 0)}')
    for lo, hi, nm in ((-99, -2, '<=-2'), (-1, -1, '-1'), (0, 0, '0'), (1, 1, '+1'), (2, 99, '>=+2')):
        sub = [e for g, e in A if lo <= e['ln_s'] - e['ln_v'] <= hi]
        kill = [e for e in sub if e['dead_s'] + e['dead_v'] > 0]
        net = mean([e['dead_v'] - e['dead_s'] for e in sub])
        dr = mean([e['dmg_s'] / max(1, e['dmg_s'] + e['dmg_v']) for e in sub])
        print(f'    striker local {nm:>5s}: n {len(sub)} kill share {len(kill) / max(1, len(sub)):.2f}, striker net kills/eng {net:+.3f}, striker damage share {dr:.2f}')
    # logistic on kill-engagements: striker win ~ local diff + hp diff
    X = [[e['ln_s'] - e['ln_v'], (e['lh_s'] - e['lh_v']) / 1000] for g, e in E if eng_out(e) != 'T']
    y = [1 if eng_out(e) == 'W' else 0 for g, e in E if eng_out(e) != 'T']
    from sklearn.linear_model import LogisticRegression
    m = LogisticRegression(max_iter=1000).fit(np.array(X), np.array(y))
    p0 = 1 / (1 + math.exp(-m.intercept_[0]))
    print(f'  logit striker-win (no ties) n {len(y)}: intercept {m.intercept_[0]:+.2f} (P at even numbers and HP {p0:.2f}), local diff {m.coef_[0][0]:+.2f}, HP diff/1000 {m.coef_[0][1]:+.2f}')


def x4(G, P):
    print('== X4: mid band rule ==')
    for w in ('mid_1_50', 'mid_51_100', 'mid_101_150'):
        Wv = [g['win'][g['winner']][w] for g in P]; Lv = [g['win'][1 - g['winner']][w] for g in P]
        print(f'  {w}: winners mean {mean(Wv):.2f} (share >= 2: {np.mean([x >= 2 for x in Wv]):.2f}) | losers {mean(Lv):.2f} (>= 2: {np.mean([x >= 2 for x in Lv]):.2f})')
    for key in KEYS:
        mine = [g for g in G if g['key'] == key]
        v = [g['win'][g['study']]['mid_51_100'] for g in mine]
        print(f'    {key:9s} mid bodies r51-100 mean {mean(v):.2f}, share of games >= 2: {np.mean([x >= 2 for x in v]):.2f}')
    print('  team-level win rate by mean bodies in the mid band r51-100 (both sides, pooled):')
    for lo, hi in ((0, 0.5), (0.5, 1), (1, 1.5), (1.5, 2), (2, 9)):
        k = n = 0
        for g in P:
            for t in (0, 1):
                v = g['win'][t]['mid_51_100']
                if lo <= v < hi:
                    n += 1; k += g['winner'] == t
        print(f'    {lo}-{hi}: {pct(k, n)}')
    # does mid presence add beyond gold at r100?
    X, y = [], []
    for g in P:
        X.append([ts(g, 0, 100, 'gold_est') - ts(g, 1, 100, 'gold_est'), g['win'][0]['mid_51_100'] - g['win'][1]['mid_51_100'],
                  ts(g, 0, 100, 'deaths') - ts(g, 1, 100, 'deaths')])
        y.append(1 if g['winner'] == 0 else 0)
    logit_cv(X, y, ['gold100', 'mid51_100', 'deaths100'], 'gold r100 + mid r51-100 + deaths')
    logit_cv([x[:1] for x in X], y, ['gold100'], 'gold r100')
    # midShare > 0.75 first mid capture definition check: median of first mid capture only among captures by r300
    geo = {json.loads(l)['map']: json.loads(l) for l in open(CACHE + '/an_strategy/mapgeo2.jsonl', encoding='utf-8')}
    PP = [g for g in P if geo[g['map']]['feat']['midShare'] > 0.75]
    W = [g['route'][g['winner']]['first_midcap'] for g in PP]; L = [g['route'][1 - g['winner']]['first_midcap'] for g in PP]
    W3 = [x for x in W if x is not None and x <= 300]; L3 = [x for x in L if x is not None and x <= 300]
    print(f'  midShare>0.75: first mid capture <= r300: winners n {len(W3)} mean {mean(W3):.0f} med {med(W3):.0f} | losers n {len(L3)} mean {mean(L3):.0f} med {med(L3):.0f}')
    W = [g['route'][g['winner']]['first_cap'] for g in PP]; L = [g['route'][1 - g['winner']]['first_cap'] for g in PP]
    W3 = [x for x in W if x is not None and x <= 300]; L3 = [x for x in L if x is not None and x <= 300]
    print(f'  midShare>0.75: first capture <= r300: winners n {len(W3)} mean {mean(W3):.0f} med {med(W3):.0f} | losers n {len(L3)} mean {mean(L3):.0f} med {med(L3):.0f}')
    late = Counter(g['map'] for g in PP for t in (0, 1) if (g['route'][t]['first_cap'] or 999) > 300)
    print('  midShare>0.75 team-games with no capture by r300, by map:', dict(late))


def x5(G, P):
    print('== X5: are the per-team weak spots team-specific? (uniform log-odds shift model) ==')
    from scipy.stats import binomtest
    conds = {
        'opp first kill (r<=300)': lambda g, s: (first_kill(g) is not None and first_kill(g)[0] == 1 - s),
        'opp strikes first in first fight': lambda g, s: (lambda es: bool(es) and es[0]['r'] <= 300 and es[0]['s'] == 1 - s)(sorted(g['engs'], key=lambda e: e['r'])),
        'study more body deaths r100': lambda g, s: ts(g, s, 100, 'deaths') > ts(g, 1 - s, 100, 'deaths'),
        'opp +100 gold r100': lambda g, s: ts(g, 1 - s, 100, 'gold_est') - ts(g, s, 100, 'gold_est') >= 100,
        'opp +30 mid gems r300': lambda g, s: ts(g, 1 - s, 300, 'gems_mid') - ts(g, s, 300, 'gems_mid') >= 30,
        'opp +300 HP bought r200': lambda g, s: ts(g, 1 - s, 200, 'hpbought') - ts(g, s, 200, 'hpbought') >= 300,
    }
    lg = lambda p: math.log(p / (1 - p)); ex = lambda z: 1 / (1 + math.exp(-z))
    for cname, cf in conds.items():
        k = n = 0
        for g in P:
            for s in (0, 1):
                if cf(g, s):
                    n += 1; k += g['winner'] == s
        shift = lg(k / n) - lg(0.5)
        line = f'  {cname:34s} generic {k / n:.2f} (shift {shift:+.2f}) |'
        for key in KEYS:
            mine = [g for g in G if g['key'] == key]
            base = sum(1 for g in mine if g['winner'] == g['study']) / len(mine)
            sub = [g for g in mine if cf(g, g['study'])]
            kk = sum(1 for g in sub if g['winner'] == g['study'])
            exp_ = ex(lg(base) + shift)
            p = binomtest(kk, len(sub), exp_).pvalue if sub else float('nan')
            line += f' {key} {kk}/{len(sub)} exp {exp_:.2f} p {p:.2f} |'
        print(line)


if __name__ == '__main__':
    G = load(sys.argv[1], sys.argv[2])
    P = pooled(G)
    for s in sys.argv[3:]:
        globals()[s](G, P)
