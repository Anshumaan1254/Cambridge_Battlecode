"""Which camp cluster does a body walk to? A conditional-logit model of the farm-target choice, fitted per team.

Episodes come from decoded replays (tools/replay/decode.mjs, `*.json.gz`): a body's run of camp hits on one cluster (consecutive hits with gaps <= GAP rounds);
the decision is taken where the body's previous episode ended (or where it respawned). Alternatives = clusters with a living camp at the episode's first
hit, within RADIUS tiles of that position. Features are what the body could have seen then. Compare the weights of two teams to see what one weighs more.

    python -I choice_model.py LABEL=SIDES.json[:TEAMFILTER] ... -- DECDIR     (SIDES.json: matchId -> {"ours": side index of the team to model})
    python -I choice_model.py --pairs FILE.json DECDIR                         (FILE.json: label -> [[matchId, side], ...])
"""
import collections
import gzip
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import minimize

GAP, RADIUS, LINK = 12, 45, 4
FEATS = ['dist/10', 'log hp', 'n camps/5', 'mid-ness', 'toward enemy', 'allies at', 'enemies at', 'has elk', 'has gold', 'has gem', 'big (>=15 camps)']
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def clusters_of(camps):
    n = len(camps)
    par = list(range(n))

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if cheb((camps[i]['x'], camps[i]['y']), (camps[j]['x'], camps[j]['y'])) <= LINK:
                par[f(i)] = f(j)
    ids = {}
    out = []
    for i in range(n):
        out.append(ids.setdefault(f(i), len(ids)))
    return out, len(ids)


def episodes(d, side):
    """[(body, cluster, first_hit_round, prev_end_round)] for one side's bodies."""
    camps = d['meta']['camps']
    cl, ncl = clusters_of(camps)
    cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
    team = {b['index']: b['team'] for b in d['meta']['bodies']}
    hits = collections.defaultdict(list)
    deaths = collections.defaultdict(list)
    for e in d['events']:
        if 'who' not in e:
            continue
        if e['k'] in ('Attack', 'Cast ability') and tuple(e.get('to', (0, 0))) in cpos and team.get(e['who']) == side:
            hits[e['who']].append((e['r'], cl[cpos[tuple(e['to'])]]))
        elif e['k'] == 'Death' and team.get(e['who']) == side:
            deaths[e['who']].append(e['r'])
    out = []
    for w, hs in hits.items():
        hs.sort()
        ep = []
        for r, c in hs:
            if ep and ep[-1]['c'] == c and r - ep[-1]['end'] <= GAP:
                ep[-1]['end'] = r
            else:
                ep.append({'c': c, 'start': r, 'end': r})
        prev_end = 1
        for e in ep:
            ds = [r for r in deaths[w] if prev_end <= r < e['start']]
            dep = max(ds) + 60 if ds else prev_end  # respawn ~ 60 rounds after a death: the body decides again there
            dep = min(dep, e['start'] - 1)
            out.append((w, e['c'], e['start'], dep))
            prev_end = e['end']
    return out, cl, ncl


def build(d, side, eps, cl, ncl):
    camps = d['meta']['camps']
    R = {s['r']: s for s in d['rounds']}
    rmin = min(R)
    s0 = R[rmin]
    sp = {0: [], 1: []}
    for c in s0['ch']:
        sp[c[1]].append((c[3], c[4]))
    cen = {t: (sum(p[0] for p in sp[t]) / len(sp[t]), sum(p[1] for p in sp[t]) / len(sp[t])) for t in (0, 1)}
    sep = max(1, cheb(cen[0], cen[1]))
    mem = collections.defaultdict(list)
    for i, c in enumerate(camps):
        mem[cl[i]].append(i)
    cc = {k: (sum(camps[i]['x'] for i in v) / len(v), sum(camps[i]['y'] for i in v) / len(v)) for k, v in mem.items()}
    rows = []
    for (w, c, r0, dep) in eps:
        sd = R.get(dep) or R.get(max(R))
        sa = R.get(r0)
        if sd is None or sa is None:
            continue
        me = [x for x in sd['ch'] if x[0] == w]
        if not me:
            continue
        pos = (me[0][3], me[0][4])
        alts = []
        chosen = None
        for k, v in mem.items():
            alive = [i for i in v if sa['campHp'][i] > 0]
            if not alive or cheb(pos, cc[k]) > RADIUS:
                continue
            ally = sum(1 for x in sd['ch'] if x[1] == side and x[7] and x[0] != w and cheb((x[3], x[4]), cc[k]) <= 8)
            enem = sum(1 for x in sd['ch'] if x[1] != side and x[7] and cheb((x[3], x[4]), cc[k]) <= 8)
            a, b = cheb(cc[k], cen[side]), cheb(cc[k], cen[1 - side])
            types = collections.Counter(camps[i]['type'] for i in alive)
            hp = sum(sa['campHp'][i] for i in alive)
            if k == c:
                chosen = len(alts)
            alts.append([cheb(pos, cc[k]) / 10.0, math.log(1 + hp), len(alive) / 5.0, 1.0 - min(1.0, abs(a - b) / (0.5 * sep)), (a - b) / sep,
                         ally, enem, 1.0 * (types['elk'] > 0), 1.0 * (types['gold'] > 0), 1.0 * (types['gem'] > 0), 1.0 * (len(alive) >= 15)])
        if chosen is not None and len(alts) >= 2:
            rows.append((np.array(alts), chosen))
    return rows


def nll(w, rows, l2):
    t = 0.0
    g = np.zeros_like(w)
    for X, ch in rows:
        z = X @ w
        z -= z.max()
        p = np.exp(z)
        p /= p.sum()
        t -= math.log(max(p[ch], 1e-12))
        g -= X[ch] - p @ X
    return t + l2 * (w @ w), g + 2 * l2 * w


def fit(rows, l2=0.5):
    k = rows[0][0].shape[1]
    r = minimize(nll, np.zeros(k), args=(rows, l2), jac=True, method='L-BFGS-B')
    w = r.x
    # standard errors from the numerical Hessian diagonal
    se = np.zeros(k)
    eps = 1e-3
    for i in range(k):
        e = np.zeros(k)
        e[i] = eps
        gp = nll(w + e, rows, l2)[1][i]
        gm = nll(w - e, rows, l2)[1][i]
        h = (gp - gm) / (2 * eps)
        se[i] = 1 / math.sqrt(max(h, 1e-9))
    top = sum(1 for X, ch in rows if int(np.argmax(X @ w)) == ch) / len(rows)
    base = sum(1 for X, ch in rows if int(np.argmin(X[:, 0])) == ch) / len(rows)
    return w, se, top, base


def main():
    args = sys.argv[1:]
    decdir = args[-1]
    specs = {}
    if args[0] == '--pairs':
        specs = json.load(open(args[1]))
    else:
        for a in args[:-1]:
            lab, rest = a.split('=', 1)
            S = json.load(open(rest))
            specs[lab] = [[k, v['ours']] for k, v in S.items()]
    for lab, games in specs.items():
        rows = []
        for mid, side in games:
            fn = os.path.join(decdir, mid + '.json.gz')
            if not os.path.exists(fn):
                continue
            d = json.load(gzip.open(fn))
            eps, cl, ncl = episodes(d, side)
            rows += build(d, side, eps, cl, ncl)
        if len(rows) < 50:
            print(lab, 'too few', len(rows))
            continue
        w, se, top, base = fit(rows)
        print('== %s: %d choices, %d games; model picks the choice %.0f%% (nearest-cluster rule %.0f%%)' % (lab, len(rows), len(games), 100 * top, 100 * base))
        for n, a, b in zip(FEATS, w, se):
            print('   %-18s %+6.2f  (se %.2f)' % (n, a, b))


if __name__ == '__main__':
    main()
