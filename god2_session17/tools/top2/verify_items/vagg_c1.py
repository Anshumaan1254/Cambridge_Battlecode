"""verify_items C1: does the health share of items (a build choice) predict winning once item spend (income) is held equal?
And do damage-heavy bodies die more (within champion type)?   python tools/top2/verify_items/vagg_c1.py"""
import collections, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from vlib import groups, vx, vd, pct

G = groups(); X = vx(); D = vd()
names = {}
for g in ('pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx'):
    for x in G[g]:
        names[(x['base'], x['S'])] = g


def team_stats(v, t, cp='600'):
    sp = 0; pts = [0, 0, 0]; hp = []; n = 0
    for b in v['bodies']:
        if b['team'] != t: continue
        c = b['cp'].get(cp) if cp != 'final' else b['cp']['final']
        if not c: return None
        n += 1; sp += c['spent']; hp.append(c['maxHp'])
        for s in range(3): pts[s] += c['pts'][s]
    tot = sum(pts) or 1
    return {'spent': sp / n, 'hpshare': pts[2] / tot, 'strshare': pts[0] / tot, 'maxhp': sum(hp) / n}


rows = []
for base, v in X.items():
    for t in (0, 1):
        a = team_stats(v, t); b = team_stats(v, 1 - t)
        if not a or not b: continue
        win = (v['outcome'] == 1 and t == 0) or (v['outcome'] == 2 and t == 1)
        rows.append({'base': base, 't': t, 'win': win, 'sr': (a['spent'] + 30) / (b['spent'] + 30), 'dh': a['hpshare'] - b['hpshare'],
                     'hr': a['maxhp'] / b['maxhp'], 'team': names.get((base, t), 'other')})
print(f'team-games with r600 reached: {len(rows)} (both sides of {len(rows)//2} games)')
print('\n=== win rate by item-spend ratio at r600 (income) and by health-share difference (build), all teams, both sides')
for lo, hi in ((0, 0.9), (0.9, 1.1), (1.1, 9)):
    sub = [r for r in rows if lo <= r['sr'] < hi]
    a = [r for r in sub if r['dh'] > 0.05]; b = [r for r in sub if r['dh'] < -0.05]; m = [r for r in sub if abs(r['dh']) <= 0.05]
    print(f"spend ratio {lo}-{hi}: n {len(sub)} win {pct(sum(r['win'] for r in sub), len(sub))} | health share higher by >5pt: {pct(sum(r['win'] for r in a), len(a))} ({len(a)}) "
          f"| within 5pt: {pct(sum(r['win'] for r in m), len(m))} ({len(m)}) | lower by >5pt: {pct(sum(r['win'] for r in b), len(b))} ({len(b)})")
# simple logistic regression win ~ log(spend ratio) + health-share diff (Newton steps)
def logit(rows, feats):
    w = [0.0] * (len(feats) + 1)
    for it in range(25):
        g = [0.0] * len(w); H = [[0.0] * len(w) for _ in w]
        for r in rows:
            x = [1.0] + [f(r) for f in feats]
            z = max(-30.0, min(30.0, sum(wi * xi for wi, xi in zip(w, x)))); p = 1 / (1 + math.exp(-z))
            for i in range(len(w)):
                g[i] += (r['win'] - p) * x[i]
                for j in range(len(w)): H[i][j] -= p * (1 - p) * x[i] * x[j]
        # solve H d = -g
        n = len(w); A = [H[i][:] + [-g[i]] for i in range(n)]
        for i in range(n):
            piv = max(range(i, n), key=lambda k: abs(A[k][i])); A[i], A[piv] = A[piv], A[i]
            for k in range(n):
                if k != i:
                    f = A[k][i] / A[i][i]
                    for j in range(i, n + 1): A[k][j] -= f * A[i][j]
        d = [A[i][n] / A[i][i] for i in range(n)]
        m = max(1.0, max(abs(di) for di in d))
        w = [wi + di / m for wi, di in zip(w, d)]
    se = [math.sqrt(-1 / H[i][i]) if H[i][i] < 0 else float('nan') for i in range(len(w))]
    return w, se
one = rows[::2] if False else [r for r in rows if r['t'] == 0]  # one row per game avoids duplicated mirror rows
w, se = logit(one, [lambda r: math.log(r['sr']), lambda r: 10 * r['dh']])
print(f"\nlogistic (team 0 rows, n {len(one)}): win ~ {w[0]:.2f} + {w[1]:.2f}*log(spend ratio) [se {se[1]:.2f}] + {w[2]:.2f}*(health share diff per 10 pt) [se {se[2]:.2f}]")
w, se = logit(one, [lambda r: 10 * r['dh']])
print(f"logistic without spend: health share diff per 10 pt coef {w[1]:.2f} [se {se[1]:.2f}]")
w, se = logit(one, [lambda r: math.log(r['hr'])])
print(f"logistic max-HP ratio only: coef {w[1]:.2f} [se {se[1]:.2f}]")
w, se = logit(one, [lambda r: math.log(r['sr']), lambda r: math.log(r['hr'])])
print(f"logistic spend + max-HP ratio: spend {w[1]:.2f} [se {se[1]:.2f}] maxHP {w[2]:.2f} [se {se[2]:.2f}]")

print('\n=== per study team: win rate by spend ratio at r600 (income) - the max-HP ratio buckets mostly track income')
for g in ('pbg', 'nyx', 'cm', 'ifish', 'pantheon', 'coo'):
    sub = [r for r in rows if r['team'] == g]
    cells = []
    for lo, hi in ((0, 0.9), (0.9, 1.1), (1.1, 9)):
        s = [r for r in sub if lo <= r['sr'] < hi]
        cells.append(f"spend {lo}-{hi}: {pct(sum(r['win'] for r in s), len(s))} ({len(s)})")
    hs = sorted(r['dh'] for r in sub)
    print(f"{g:9s} " + ' | '.join(cells) + f" | median health-share diff {hs[len(hs)//2]*100:+.0f} pt")

print('\n=== damage-heavy bodies vs deaths, within champion type (all teams, all games; final strength share of stat points)')
for T in ('VesperVale', 'Vendetta', 'HeartOfRuin', 'Marcella', 'Ryth', 'Prism'):
    bk = collections.defaultdict(lambda: [0, 0, 0])
    for base, v in X.items():
        d = D.get(base)
        if not d: continue
        for b in v['bodies']:
            if b['type'] != T: continue
            p = b['cp']['final']['pts']; tot = sum(p)
            if tot < 15: continue
            s = p[0] / tot if T != 'Prism' and T != 'HeartOfRuin' else (p[1] + p[0]) / tot
            k = '<40%' if s < 0.4 else '40-60%' if s < 0.6 else '>=60%'
            bk[k][0] += 1; bk[k][1] += sum(1 for de in d['deaths'] if de[1] == b['index']); bk[k][2] += d['alive'][str(b['index'])]
    print(f"{T:12s} " + ' | '.join(f"dmg share {k}: bodies {bk[k][0]} deaths/1000 alive {1000*bk[k][1]/max(1,bk[k][2]):.2f}" for k in ('<40%', '40-60%', '>=60%')))
