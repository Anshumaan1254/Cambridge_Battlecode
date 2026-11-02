#!/usr/bin/env python3
"""Tables for REPORT.md from the outputs of extract.py (deaths/fights/games/retreats/dives/chases.jsonl).

Usage: nice -n 19 python3 -I report.py > report_tables.txt
"""
import json, os, math
from collections import Counter, defaultdict
from statistics import mean, median

A = os.path.dirname(os.path.abspath(__file__)) + '/'
BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
load = lambda n: [json.loads(l) for l in open(A + n + '.jsonl')]
D, F, G, RT, DV, CH = load('deaths'), load('fights'), load('games'), load('retreats'), load('dives'), load('chases')
ng = Counter(g['res'] for g in G)
pct = lambda x: f'{100 * x:.0f}%'


def mean_or(xs, default=float('nan')):
    xs = [x for x in xs if x is not None]
    return mean(xs) if xs else default


# ------------------------------------------------------------------ Q1: deaths
def death_stats(rows, n_games):
    ck = [d for d in rows if d['killer'] != 'camp']
    v = [d for d in rows if d['al5'] is not None]
    st = [d for d in ck if d['started']]
    h = [d['hp5'] for d in rows if d['hp5'] is not None]
    pw = [d['pw5'] for d in ck if d['pw5'] is not None]
    return [
        ('deaths per game', f'{len(rows) / n_games:.1f}'),
        ('killed by a camp', pct(sum(d['killer'] == 'camp' for d in rows) / len(rows))),
        ('champion kills: fight started by the victim\'s team', pct(sum(d['started'] == 'own' for d in st) / len(st))),
        ('own side within 6 incl. self (mean of r-5..r-1)', f"{mean(d['al5'] + 1 for d in v):.2f}"),
        ('enemies within 6 (same rounds)', f"{mean(d['en5'] for d in v):.2f}"),
        ('outnumbered by >=0.5 body', pct(sum(d['en5'] - (d['al5'] + 1) >= 0.5 for d in v) / len(v))),
        ('no ally within 6', pct(sum(d['al5'] < 0.5 for d in v) / len(v))),
        ('local HP x DPS ratio at r-5 (median, champion kills)', f'{median(pw):.2f}'),
        ('>=2 own steps toward nearest enemy in last 8 r', pct(sum(d['tw8'] >= 2 for d in rows) / len(rows))),
        ('steps toward / away in last 8 r (mean)', f"{mean(d['tw8'] for d in rows):.1f} / {mean(d['aw8'] for d in rows):.1f}"),
        ('no retreat step at all in last 10 r (champion kills)', pct(sum(d['ret_r'] is None for d in ck) / len(ck))),
        ('hp 5 rounds before (mean)', pct(mean(h))),
        ('hp 5 rounds before < 50%', pct(sum(x < 0.5 for x in h) / len(h))),
        ('carrying gems', pct(sum(d['bag'] > 0 for d in rows) / len(rows))),
        ('gems lost per death', f"{mean(d['bag'] for d in rows):.1f}"),
        ('an awake camp hit it in last 5 r', pct(sum(d['camp_hits5'] > 0 for d in rows) / len(rows))),
        ('  ...a camp the ENEMY had woken', pct(sum(d['camp_waker'] in ('enemy', 'both') for d in rows) / len(rows))),
        ('lure: chased a target that kept its distance', pct(sum(d['lure'] for d in rows) / len(rows))),
        ('on the enemy half', pct(sum(d['enemy_half'] for d in rows) / len(rows))),
        ('stunned in last 3 r', pct(sum(d['stunned3'] for d in rows) / len(rows))),
        ('held a recall in last 6 r', pct(sum(d['recall6'] > 0 for d in rows) / len(rows))),
        ('was hitting a camp when first hit', pct(sum(d['farming'] for d in rows) / len(rows))),
    ]


print('## Q1 deaths (columns: side-result, n deaths)')
cols = {}
for side in ('we', 'they'):
    for res in 'WL':
        rows = [d for d in D if d['side'] == side and d['res'] == res]
        cols[f'{side}-{res} n={len(rows)}'] = death_stats(rows, ng[res])
names = [k for k, _ in next(iter(cols.values()))]
print('| | ' + ' | '.join(cols) + ' |')
print('|---' * (len(cols) + 1) + '|')
for i, n in enumerate(names):
    print(f'| {n} | ' + ' | '.join(c[i][1] for c in cols.values()) + ' |')

# ------------------------------------------------------------------ Q2: exchanges
X = [f for f in F if f['exchange']]


def wshare(rows):
    w = sum(f['win'] == 'we' for f in rows)
    l = sum(f['win'] == 'they' for f in rows)
    return w, l, len(rows) - w - l, (w / (w + l) if w + l else float('nan'))


def ratio(f):
    a, b = f['pw']['we'], f['pw']['they']
    return a / b if a > 0 and b > 0 else None


def sp15(f, s):
    j = [x for x in f['joins'][s] if x <= 15]
    return (max(j) - min(j)) if len(j) >= 2 else None


print('\n## Q2 exchanges (both teams landed a champion hit; fights = hits <=5 r apart and <=6 tiles apart)')
for res in 'WL':
    R = [f for f in X if f['res'] == res]
    w, l, dr, s = wshare(R)
    print(f'{res}: {len(R) / ng[res]:.1f} exchanges/game; we win {w}, lose {l}, draw {dr} -> our win share {s:.0%}')
    for lab, cond in (('we hit first', lambda f: f['first'] == 'we'), ('they hit first', lambda f: f['first'] == 'they'),
                      ('more bodies within 6 at contact', lambda f: f['num']['we'] > f['num']['they']),
                      ('equal bodies at contact', lambda f: f['num']['we'] == f['num']['they']),
                      ('fewer bodies at contact', lambda f: f['num']['we'] < f['num']['they']),
                      ('more participants', lambda f: f['parts']['we'] > f['parts']['they']),
                      ('fewer participants', lambda f: f['parts']['we'] < f['parts']['they'])):
        S = [f for f in R if cond(f)]
        print(f'   {lab}: {len(S) / len(R):.0%} of exchanges, our win share {wshare(S)[3]:.0%}')
    for lo, hi in ((0, 0.5), (0.5, 0.8), (0.8, 1.25), (1.25, 2), (2, 1e9)):
        S = [f for f in R if ratio(f) is not None and lo <= ratio(f) < hi]
        print(f'   power ratio (HPxDPS within 6 of contact, we/they) {lo}-{hi if hi < 1e9 else "inf"}: {len(S) / len(R):.0%}, our win share {wshare(S)[3]:.0%}')

print('\n winner vs loser (means per exchange)')
for res in 'WL':
    for who in ('we', 'they'):
        R = [f for f in X if f['res'] == res and f['win'] == who]
        loser = 'they' if who == 'we' else 'we'
        out = []
        for lab, fn in (('bodies within 6 at contact', lambda f, s: f['num'][s]),
                        ('participants', lambda f, s: f['parts'][s]),
                        ('arrival spread, first 15 r (>=2 bodies)', lambda f, s: sp15(f, s)),
                        ('focus: share of hits on top target (>=2 targets, >=3 hits)', lambda f, s: f['focus'][s] if f['targets_avail'][s] >= 2 else None),
                        ('stuns landed', lambda f, s: f['stuns'][s]),
                        ('stuns per hit', lambda f, s: f['stuns'][s] / f['hits'][s] if f['hits'][s] else None),
                        ('stunned targets killed within 3 r', lambda f, s: f['conv'][s]),
                        ('shards per participant', lambda f, s: f['shards'][s] / f['parts'][s]),
                        ('camp damage taken', lambda f, s: f['campdmg'][s])):
            out.append(f'{lab}: winner {mean_or(fn(f, who) for f in R):.2f} / loser {mean_or(fn(f, loser) for f in R):.2f}')
        lv = [sum(f['leave'][loser][0] for f in R), sum(f['leave'][loser][1] for f in R)]
        print(f' {res} games, {who} won (n={len(R)}): ' + '; '.join(out) +
              f'; loser bodies killed that had tried to leave {lv[0]}/{lv[1]} ({lv[0] / max(1, lv[1]):.0%}); winner hit first {sum(f["first"] == who for f in R) / len(R):.0%}')

print('\n retreat episodes (away step from an enemy within 5 right after taking a champion hit): caught = died within 8 r')
for side in ('we', 'they'):
    R = [r for r in RT if r['side'] == side]
    parts = []
    for lab, cond in (('hp<25%', lambda r: r['hp'] < 0.25), ('25-40%', lambda r: 0.25 <= r['hp'] < 0.4), ('40-60%', lambda r: 0.4 <= r['hp'] < 0.6),
                      ('>=60%', lambda r: r['hp'] >= 0.6),
                      ('hp<40% & enemy dash/stun ready in reach', lambda r: r['hp'] < 0.4 and (r['dash4'] or 0) + (r['stun5'] or 0) >= 1),
                      ('hp>=40% & none ready', lambda r: r['hp'] >= 0.4 and (r['dash4'] or 0) + (r['stun5'] or 0) == 0)):
        S = [r for r in R if cond(r)]
        parts.append(f'{lab} {sum(r["died8"] for r in S) / max(1, len(S)):.0%} (n={len(S)})')
    print(f' {side}: ' + '; '.join(parts))

# logistic regression on decisive exchanges
try:
    import numpy as np
    Xr = [f for f in X if f['win'] in ('we', 'they') and ratio(f)]
    names = ['log2 local power ratio', 'we hit first', 'bodies diff at contact', 'arrival spread diff', 'camp dmg diff/500', 'shards/participant diff/10', 'L game']
    M = np.array([[math.log2(ratio(f)), f['first'] == 'we', f['num']['we'] - f['num']['they'], (sp15(f, 'we') or 0) - (sp15(f, 'they') or 0),
                   (f['campdmg']['we'] - f['campdmg']['they']) / 500,
                   (f['shards']['we'] / f['parts']['we'] - f['shards']['they'] / f['parts']['they']) / 10, f['res'] == 'L'] for f in Xr], float)
    y = np.array([f['win'] == 'we' for f in Xr], float)
    Z = np.hstack([np.ones((len(M), 1)), (M - M.mean(0)) / M.std(0)])
    wv = np.zeros(Z.shape[1])
    for _ in range(100):
        p = 1 / (1 + np.exp(-Z @ wv))
        Hm = (Z.T * (p * (1 - p))) @ Z
        wv += np.linalg.solve(Hm, Z.T @ (y - p))
    se = np.sqrt(np.diag(np.linalg.inv(Hm)))
    print(f'\n logistic regression, decisive exchanges n={len(y)} (coef per SD, z):')
    print('   ' + '; '.join(f'{n} {b:+.2f} (z {b / s:+.1f})' for n, b, s in zip(names, wv[1:], se[1:])))
except Exception as e:  # numpy missing
    print('regression skipped', e)

# ------------------------------------------------------------------ Q3: patterns
print('\n## Q3 patterns (per game; L = our losses, W = our wins)')
for res in 'LW':
    for side in ('we', 'they'):
        R = [d for d in DV if d['res'] == res and d['side'] == side]
        dd = [d for d in R if d['died8']]
        print(f'P1 dives {res} {side}: {len(R) / ng[res]:.1f}/game, died within 8 r {len(dd) / max(1, len(R)):.0%} = {len(dd) / ng[res]:.2f} deaths/game, '
              f'gems lost {sum(d["bag"] for d in dd) / ng[res]:.1f}/game; hp at start {mean_or(d["hp"] for d in R):.2f}')
for res in 'LW':
    for side in ('we', 'they'):
        R = [d for d in D if d['res'] == res and d['side'] == side and d['killer'] != 'camp']
        aw = [d for d in R if d['tw8'] >= 2 and (d['pw5'] if d['pw5'] is not None else 9) < 0.67]
        nr = [d for d in R if d['ret_r'] is None]
        print(f'P1 deaths after >=2 steps toward while weaker {res} {side}: {len(aw) / ng[res]:.2f}/game ({len(aw) / len(R):.0%} of champion kills); '
              f'no retreat step {len(nr) / ng[res]:.2f}/game ({len(nr) / len(R):.0%}), of which approached {sum(d["tw8"] >= 2 for d in nr) / max(1, len(nr)):.0%}')
agg = defaultdict(Counter)
for g in G:
    for k, v in g['step_stats'].items():
        side, rb, dirn, m = k.split('|')
        agg[(g['res'], side, rb, dirn)][m] += v
for res in 'LW':
    for side in ('we', 'they'):
        parts = []
        for rb in ('weak', 'par', 'strong'):
            tot = sum(agg[(res, side, rb, d)]['n'] for d in ('toward', 'away', 'side'))
            tw = agg[(res, side, rb, 'toward')]
            parts.append(f'{rb}: {tot / ng[res]:.0f} steps/game, toward {tw["n"] / max(1, tot):.0%}, died<=6r after a toward step {tw["died6"] / max(1, tw["n"]):.1%}')
        eqm = sum(agg[(res, side, rb, d)]['n'] for rb in ('weak+neq', 'weak+nmore') for d in ('toward', 'away', 'side'))
        print(f'P1 steps within 6 of an enemy {res} {side}: ' + ' | '.join(parts) + f' | weak with equal/more bodies {eqm / ng[res]:.0f}/game')
for res in 'LW':
    for side in ('we', 'they'):
        R = [d for d in D if d['res'] == res and d['side'] == side]
        ec = [d for d in R if d['camp_waker'] in ('enemy', 'both')]
        print(f'P2 deaths hit by a camp the enemy woke {res} {side}: {len(ec) / ng[res]:.2f}/game ({len(ec) / len(R):.0%} of deaths); '
              f'all camp-involved {sum(d["camp_hits5"] > 0 for d in R) / ng[res]:.2f}/game')
for res in 'LW':
    for side in ('we', 'they'):
        R = [d for d in D if d['res'] == res and d['side'] == side]
        lu = [d for d in R if d['lure']]
        kt = sum(d['lure_info']['killer_is_target'] for d in lu)
        C = [c for c in CH if c['res'] == res and c['side'] == side]
        print(f'P3 lure deaths {res} {side}: {len(lu) / ng[res]:.2f}/game ({len(lu) / len(R):.0%}); killer = chased target {kt / max(1, len(lu)):.0%}; '
              f'chase episodes {len(C) / ng[res]:.1f}/game, died within 10 r {sum(c["died10"] for c in C) / max(1, len(C)):.1%}')
byb = defaultdict(list)
for d in D:
    byb[(d['mid'], d['body'])].append(d)
rep = Counter()
for k, ds in byb.items():
    ds.sort(key=lambda d: d['r'])
    for a, b in zip(ds, ds[1:]):
        if b['r'] - a['r'] <= 100:
            rep[(b['side'], b['res'])] += 1
print('P1b re-death within 40 r of respawn: ' + ', '.join(f'{s}-{r} {v / ng[r]:.2f}/game' for (s, r), v in sorted(rep.items())))
for res in 'LW':
    for side in ('we', 'they'):
        R = [d for d in D if d['res'] == res and d['side'] == side and d['bag'] >= 10]
        print(f'P1c deaths carrying >=10 gems {res} {side}: {len(R) / ng[res]:.2f}/game, {sum(d["bag"] for d in R) / ng[res]:.0f} gems/game, approached {sum(d["tw8"] >= 2 for d in R) / max(1, len(R)):.0%}')

# ------------------------------------------------------------------ map features
print('\n## map features vs our pattern rates (per 1000 rounds, all 128 games; Spearman rho)')
try:
    import numpy as np

    def rank(a):
        a = np.asarray(a, float)
        o = a.argsort()
        r = np.empty(len(a))
        r[o] = np.arange(len(a))
        return r
    feats = ['area', 'spawn_dist', 'altars', 'bush_frac', 'wall_frac', 'narrow_frac', 'champs']
    rate = {}
    for g in G:
        sc = 1000 / max(1, g['final'])
        mid = g['mid']
        rate[mid] = {'dives': sum(1 for x in DV if x['mid'] == mid and x['side'] == 'we') * sc,
                     'dive deaths': sum(1 for x in DV if x['mid'] == mid and x['side'] == 'we' and x['died8']) * sc,
                     'enemy-camp deaths': sum(1 for d in D if d['mid'] == mid and d['side'] == 'we' and d['camp_waker'] in ('enemy', 'both')) * sc,
                     'lure deaths': sum(1 for d in D if d['mid'] == mid and d['side'] == 'we' and d['lure']) * sc}
    mids = [g['mid'] for g in G]
    fv = {g['mid']: dict(g['mf'], champs=g['champs']) for g in G}
    print('| pattern | ' + ' | '.join(feats) + ' |')
    for p in ('dives', 'dive deaths', 'enemy-camp deaths', 'lure deaths'):
        y = rank([rate[m][p] for m in mids])
        print(f'| {p} | ' + ' | '.join(f'{np.corrcoef(rank([fv[m][f] for m in mids]), y)[0, 1]:+.2f}' for f in feats) + ' |')
    # splits
    for p, f, thr in (('dives', 'spawn_dist', None), ('dives', 'area', None), ('enemy-camp deaths', 'champs', 5), ('lure deaths', 'spawn_dist', None)):
        vals = [fv[m][f] for m in mids]
        t = thr if thr is not None else median(vals)
        lo = [rate[m][p] for m in mids if fv[m][f] < t]
        hi = [rate[m][p] for m in mids if fv[m][f] >= t]
        print(f'   {p}: {f} < {t}: {mean(lo):.2f} per 1000 r (n={len(lo)}) vs >= {t}: {mean(hi):.2f} (n={len(hi)})')
    mapr = defaultdict(list)
    for g in G:
        mapr[g['map']].append(g['mid'])
    for p in ('dives', 'enemy-camp deaths', 'lure deaths'):
        top = sorted(mapr, key=lambda mp: -mean(rate[m][p] for m in mapr[mp]))[:6]
        print(f'   top maps for {p}: ' + ', '.join(f'{mp} {mean(rate[m][p] for m in mapr[mp]):.1f} (n={len(mapr[mp])}, {fv[mapr[mp][0]]["w"]}x{fv[mapr[mp][0]]["h"]}, spawn dist {fv[mapr[mp][0]]["spawn_dist"]})' for mp in top))
except Exception as e:
    print('map analysis skipped', e)

# ------------------------------------------------------------------ examples
print('\n## examples (L games, ours)')
ex = sorted([d for d in DV if d['side'] == 'we' and d['res'] == 'L' and d['died8']], key=lambda d: d['ratio'])
seen = set()
for d in ex:
    if d['mid'] in seen:
        continue
    seen.add(d['mid'])
    print(f"P1 dive: {d['mid']} r{d['r']} body {d['body']} {d['champ']} hp {d['hp']:.0%} ratio {d['ratio']:.2f} {d['n_own']}v{d['n_en']} toward {d['target']} -> killed by {d['killer']}, bag {d['bag']}")
    if len(seen) >= 6:
        break
ex = sorted([d for d in D if d['side'] == 'we' and d['res'] == 'L' and d['camp_waker'] in ('enemy', 'both') and d['killer'] != 'camp'], key=lambda d: -d['camp_dmg5'])
seen = set()
for d in ex:
    if d['mid'] in seen:
        continue
    seen.add(d['mid'])
    print(f"P2 enemy camp: {d['mid']} r{d['r']} body {d['body']} {d['champ']} camp dmg 5r {d['camp_dmg5']} champion dmg {d['champ_dmg5']} killer {d['killer']} steps toward {d['tw8']}")
    if len(seen) >= 6:
        break
ex = [d for d in D if d['side'] == 'we' and d['res'] == 'L' and d['lure'] and not d['lure_info']['killer_is_target']]
ex.sort(key=lambda d: -d['lure_info']['steps'])
seen = set()
for d in ex:
    if d['mid'] in seen:
        continue
    seen.add(d['mid'])
    li = d['lure_info']
    print(f"P3 lure: {d['mid']} r{d['r']} body {d['body']} {d['champ']} chased {li['target']} {li['steps']} steps (gap {li['d0']}->{li['dend']}), killed by {d['killer']}")
    if len(seen) >= 6:
        break
