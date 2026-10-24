# Verify C1: aggregate vc1_eng.mjs output. Engagement logit, starter win rates at even power, net by ratio x starter,
# start shares, game-level "bad starts" (share of own starts at local max-health ratio < 0.67) with confounder checks,
# fresh-contact first strikes.   python vc1_agg.py DIR [variant: all|x]
import json, sys, glob, math
import numpy as np, pandas as pd
import statsmodels.api as sm

D = sys.argv[1]
VAR = sys.argv[2] if len(sys.argv) > 2 else 'x'
rows, games, cont = [], [], []
for f in sorted(glob.glob(D + '/c1_?.jsonl')):
    for l in open(f):
        g = json.loads(l)
        gi = len(games)
        games.append({'gi': gi, 'key': g['key'], 'match': g['match'], 'map': g['map'], 'swon': int(g['swon']), 'size': g['ssize'] + g['osize'], 'final': g['final']})
        for e in g['engs']:
            e = dict(e); e['gi'] = gi; e['key'] = g['key']; e['swon'] = int(g['swon']); rows.append(e)
        for c in g['contacts']:
            cont.append({'gi': gi, 'key': g['key'], 'r': c[0], 'first': c[1], 'ratio': c[2]})
E = pd.DataFrame(rows); GM = pd.DataFrame(games); C = pd.DataFrame(cont)
sfx = 'x' if VAR == 'x' else ''
E['mS_'] = E['mS' + sfx]; E['mO_'] = E['mO' + sfx]; E['hS_'] = E['hS' + sfx]; E['hO_'] = E['hO' + sfx]; E['nS_'] = E['nS' + sfx]; E['nO_'] = E['nO' + sfx]
E = E[(E.mS_ > 0) & (E.mO_ > 0)].copy()
E['ratio'] = E.mS_ / E.mO_
E['lr'] = np.log(E.ratio)
E['hf'] = E.hS_ / E.mS_ - E.hO_ / E.mO_
E['dn'] = E.nS_ - E.nO_
E['net'] = E.dO - E.dS
E['dec'] = (E.dS != E.dO).astype(int)
E['win'] = (E.dS < E.dO).astype(int)
print('variant', VAR, 'games', len(GM), 'engagements', len(E), 'decisive', E.dec.sum(), 'per game', round(len(E) / len(GM), 1))
Dd = E[E.dec == 1].copy()

def logit(df, cols, label):
    X = df[cols].astype(float)
    Xs = (X - X.mean()) / X.std()
    Xs = sm.add_constant(Xs)
    m = sm.Logit(df['win'].astype(float), Xs).fit(disp=0)
    print(label, 'n', len(df), 'pseudoR2', round(m.prsquared, 3))
    for c in cols:
        print('   %-6s coef %+.2f  z %+.1f' % (c, m.params[c], m.tvalues[c]))
    return m

logit(Dd, ['lr', 'hf', 'st', 'dn'], 'pre-fight logit (lr, hf, st, dn)')
logit(Dd, ['lr', 'hf', 'st'], 'pre-fight logit without body count')
logit(Dd, ['st'], 'starter only')
# dedupe matches (54 matches appear in two folders): keep the first copy
first_gi = GM.drop_duplicates('match').gi
logit(Dd[Dd.gi.isin(first_gi)], ['lr', 'hf', 'st', 'dn'], 'dedup pre-fight logit')

ev = Dd[np.abs(Dd.lr) < 0.15]
print('\nEven power |log ratio|<0.15: S starts -> S win %.1f%% (n=%d); O starts -> S win %.1f%% (n=%d)' % (
    100 * ev[ev.st == 1].win.mean(), (ev.st == 1).sum(), 100 * ev[ev.st == 0].win.mean(), (ev.st == 0).sum()))
# same with health fraction also even
ev2 = ev[np.abs(ev.hf) < 0.1]
print('Even power AND |health-fraction diff|<0.1: S starts -> %.1f%% (n=%d); O starts -> %.1f%% (n=%d)' % (
    100 * ev2[ev2.st == 1].win.mean(), (ev2.st == 1).sum(), 100 * ev2[ev2.st == 0].win.mean(), (ev2.st == 0).sum()))

bins = [0, 0.67, 0.87, 1.15, 1.5, 1e9]
labs = ['<0.67', '0.67-0.87', '0.87-1.15', '1.15-1.5', '>=1.5']
E['rb'] = pd.cut(E.ratio, bins, labels=labs, right=False)
print('\nNet bodies per engagement (all engagements) by S/O ratio and starter:')
print('%-10s %6s %8s %8s %8s %8s %8s' % ('ratio', 'n', 'Swin%dec', 'net', 'netSst', 'netOst', 'shareS'))
for b in labs:
    x = E[E.rb == b]
    print('%-10s %6d %8.1f %+8.2f %+8.2f %+8.2f %8.2f' % (b, len(x), 100 * x[x.dec == 1].win.mean(), x.net.mean(), x[x.st == 1].net.mean(), x[x.st == 0].net.mean(), x.st.mean()))
# net per start controlling health fraction: within ratio bin, split by hf sign
print('\nNet per engagement by starter within ratio bins, S health fraction >= O (hf>=0) vs < 0:')
for b in labs:
    x = E[E.rb == b]
    a = x[x.hf >= 0]; c = x[x.hf < 0]
    print('%-10s hf>=0: Sst %+.2f (n=%d) Ost %+.2f (n=%d) | hf<0: Sst %+.2f (n=%d) Ost %+.2f (n=%d)' % (
        b, a[a.st == 1].net.mean(), (a.st == 1).sum(), a[a.st == 0].net.mean(), (a.st == 0).sum(),
        c[c.st == 1].net.mean(), (c.st == 1).sum(), c[c.st == 0].net.mean(), (c.st == 0).sum()))

print('\nStart share and decisive win rate per team:')
for k, x in E.groupby('key'):
    print('  %-9s eng/game %.1f  S starts %.1f%%  S wins(dec) %.1f%%  net/S start %+.2f  net/O start %+.2f' % (
        k, len(x) / (GM.key == k).sum(), 100 * x.st.mean(), 100 * x[x.dec == 1].win.mean(), x[x.st == 1].net.mean(), x[x.st == 0].net.mean()))
print('  ALL       S starts %.1f%%  net/S start %+.2f  net/O start %+.2f' % (100 * E.st.mean(), E[E.st == 1].net.mean(), E[E.st == 0].net.mean()))

# ---------- game level
gl = []
for gi, x in E.groupby('gi'):
    s = x[x.st == 1]; o = x[x.st == 0]
    gl.append({'gi': gi, 'sbad': (s.ratio < 0.67).mean() if len(s) else np.nan, 'obad': (1 / o.ratio < 0.67).mean() if len(o) else np.nan,
               'sweak_all': (x.ratio < 0.67).mean(), 'oweak_all': (1 / x.ratio < 0.67).mean(),
               'p_sstart_weak': s[s.ratio < 0.67].shape[0] / max(1, (x.ratio < 0.67).sum()) if (x.ratio < 0.67).sum() else np.nan,
               'p_ostart_weak': o[1 / o.ratio < 0.67].shape[0] / max(1, (1 / x.ratio < 0.67).sum()) if (1 / x.ratio < 0.67).sum() else np.nan,
               'ns': len(s), 'no': len(o), 'mean_lr': x.lr.mean()})
GL = pd.DataFrame(gl).merge(GM, on='gi')
GL['dbad'] = GL.sbad - GL.obad
GL['dweak'] = GL.sweak_all - GL.oweak_all
GL['dpw'] = GL.p_sstart_weak - GL.p_ostart_weak
print('\nGame level (n=%d games with engagements):' % len(GL))
print('  S bad-start share: wins %.3f  losses %.3f' % (GL[GL.swon == 1].sbad.mean(), GL[GL.swon == 0].sbad.mean()))
print('  O bad-start share: S wins %.3f  S losses %.3f' % (GL[GL.swon == 1].obad.mean(), GL[GL.swon == 0].obad.mean()))
ok = GL.dropna(subset=['dbad'])
print('  corr(S-O bad-start share, S won) = %.3f (n=%d)' % (np.corrcoef(ok.dbad, ok.swon)[0, 1], len(ok)))
print('  corr(S bad-start share, S won)   = %.3f' % np.corrcoef(GL.dropna(subset=['sbad']).sbad, GL.dropna(subset=['sbad']).swon)[0, 1])
print('  corr(S-O share of ALL engagements fought weaker (state), S won) = %.3f' % np.corrcoef(GL.dweak, GL.swon)[0, 1])
print('  corr(mean log ratio over engagements, S won) = %.3f' % np.corrcoef(GL.mean_lr, GL.swon)[0, 1])
ok2 = GL.dropna(subset=['dpw'])
print('  corr(S-O P(start | weaker) (decision), S won) = %.3f (n=%d)' % (np.corrcoef(ok2.dpw, ok2.swon)[0, 1], len(ok2)))
print('  P(S starts | S weaker): wins %.3f losses %.3f' % (GL[GL.swon == 1].p_sstart_weak.mean(), GL[GL.swon == 0].p_sstart_weak.mean()))
for k, x in GL.groupby('key'):
    y = x.dropna(subset=['dbad']); y2 = x.dropna(subset=['dpw'])
    print('  %-9s corr(dbad,win) %+.2f  corr(dweak,win) %+.2f  corr(dP(start|weak),win) %+.2f  S bad share W %.2f L %.2f' % (
        k, np.corrcoef(y.dbad, y.swon)[0, 1], np.corrcoef(x.dweak, x.swon)[0, 1], np.corrcoef(y2.dpw, y2.swon)[0, 1],
        x[x.swon == 1].sbad.mean(), x[x.swon == 0].sbad.mean()))
# logit with state + decision
ok3 = GL.dropna(subset=['dbad', 'dpw']).copy()
for cols in (['dbad'], ['dweak'], ['dbad', 'dweak'], ['dpw', 'dweak']):
    X = ok3[cols]; X = (X - X.mean()) / X.std(); X = sm.add_constant(X)
    m = sm.Logit(ok3.swon.astype(float), X).fit(disp=0)
    print('  game logit', cols, ' '.join('%s %+.2f (z %+.1f)' % (c, m.params[c], m.tvalues[c]) for c in cols), 'n', len(ok3))

# ---------- fresh contacts
print('\nFresh contacts per team (S first / O first / nobody), and when S weaker (ratio<0.67):')
for k, x in C.groupby('key'):
    w = x[x.ratio < 0.67]
    print('  %-9s n/game %.1f  S %.1f%%  O %.1f%%  none %.1f%% | S weaker: S first %.1f%% O first %.1f%% (n=%d)' % (
        k, len(x) / (GM.key == k).sum(), 100 * (x['first'] == 1).mean(), 100 * (x['first'] == 0).mean(), 100 * (x['first'] == -1).mean(),
        100 * (w['first'] == 1).mean(), 100 * (w['first'] == 0).mean(), len(w)))
