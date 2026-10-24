# Verify C6 (bags lost on death, banking policy) from vc_econ.mjs (+ vc1_eng.mjs for game-level comparison).   python vc6_agg.py DIR
import json, glob, sys, collections
import numpy as np, pandas as pd
import statsmodels.api as sm
D = sys.argv[1]
games, CAP, DE = [], [], []
for f in sorted(glob.glob(D + '/econ_?.jsonl')):
    for l in open(f):
        g = json.loads(l); gi = len(games)
        dS = [d for d in g['deaths'] if d['s'] == 1]; dO = [d for d in g['deaths'] if d['s'] == 0]
        games.append({'gi': gi, 'key': g['key'], 'match': g['match'], 'swon': int(g['swon']), 'final': g['final'],
                      'lostS': sum(d['bag'] for d in dS), 'lostO': sum(d['bag'] for d in dO), 'deathsS': len(dS), 'deathsO': len(dO),
                      'champDeathsS': sum(d['champ'] for d in dS), 'champDeathsO': sum(d['champ'] for d in dO),
                      'lostS_champ': sum(d['bag'] for d in dS if d['champ']), 'lostO_champ': sum(d['bag'] for d in dO if d['champ']),
                      'bankS': sum(t['bag'] for t in g['trib'] if t['s'] == 1 and t['out'] == 'done'),
                      'bankO': sum(t['bag'] for t in g['trib'] if t['s'] == 0 and t['out'] == 'done')})
        for c in g['caps']: c = dict(c); c['gi'] = gi; c['key'] = g['key']; CAP.append(c)
GM = pd.DataFrame(games); CAP = pd.DataFrame(CAP)
ng = GM.groupby('key').size()
print('Gems lost on death per game S / O (all deaths; champion kills only):')
for k, x in GM.groupby('key'):
    print('   %-9s %.0f / %.0f   (%.0f / %.0f)   deaths S/O %.1f / %.1f' % (k, x.lostS.mean(), x.lostO.mean(), x.lostS_champ.mean(), x.lostO_champ.mean(), x.deathsS.mean(), x.deathsO.mean()))
GM['dlost'] = GM.lostS - GM.lostO; GM['ddeath'] = GM.deathsS - GM.deathsO; GM['dbank'] = GM.bankS - GM.bankO
c = lambda a, b: np.corrcoef(a, b)[0, 1]
print('\nPooled correlation with S won (n=%d): gems lost diff %.3f | deaths diff %.3f | champion-kill deaths diff %.3f' % (
    len(GM), c(GM.dlost, GM.swon), c(GM.ddeath, GM.swon), c(GM.champDeathsS - GM.champDeathsO, GM.swon)))
for k, x in GM.groupby('key'):
    print('   %-9s gems lost diff %+.2f | deaths diff %+.2f' % (k, c(x.dlost, x.swon), c(x.ddeath, x.swon)))
# join with C1 game-level features (bad-start share, state)
rows = []
for f in sorted(glob.glob(D + '/c1_?.jsonl')):
    for l in open(f):
        g = json.loads(l)
        E = pd.DataFrame(g['engs'])
        if len(E) == 0: continue
        E = E[(E.mSx > 0) & (E.mOx > 0)]
        ratio = E.mSx / E.mOx
        s = E.st == 1; o = E.st == 0
        rows.append({'key': g['key'], 'match': g['match'], 'sbad': (ratio[s] < 0.67).mean() if s.sum() else np.nan,
                     'obad': (1 / ratio[o] < 0.67).mean() if o.sum() else np.nan, 'dweak': (ratio < 0.67).mean() - (1 / ratio < 0.67).mean()})
C1 = pd.DataFrame(rows)
M = GM.merge(C1, on=['key', 'match'])
M['dbad'] = M.sbad - M.obad
M = M.dropna(subset=['dbad'])
print('\nGame-level (n=%d with both): corr with S won: dlost %.3f, dbad %.3f, dweak %.3f, ddeath %.3f' % (len(M), c(M.dlost, M.swon), c(M.dbad, M.swon), c(M.dweak, M.swon), c(M.ddeath, M.swon)))
for cols in (['dlost', 'dbad'], ['dlost', 'dbad', 'dweak'], ['dlost', 'ddeath', 'dbad', 'dweak'], ['ddeath', 'dweak']):
    X = M[cols]; X = (X - X.mean()) / X.std(); X = sm.add_constant(X)
    m = sm.Logit(M.swon.astype(float), X).fit(disp=0)
    print('   logit', ' '.join('%s %+.2f (z %+.1f)' % (cc, m.params[cc], m.tvalues[cc]) for cc in cols), ' pseudoR2 %.2f' % m.prsquared)
# bank before the next capture, by bag after the capture
S = CAP[CAP.s == 1].copy()
S['bagb'] = pd.cut(S.bag, [-1, 29, 59, 99, 199, 1e9], labels=['<30', '30-59', '60-99', '100-199', '200+'])
print('\nP(bank before the next capture | bag after capture), S:')
print('   %-9s %s' % ('team', '  '.join('%8s' % b for b in ['<30', '30-59', '60-99', '100-199', '200+'])))
for k in ['cm', 'ifish', 'pbg', 'pantheon', 'coo', 'nyx']:
    x = S[S.key == k]
    print('   %-9s %s' % (k, '  '.join('%3.0f%% %4d' % (100 * (x[x.bagb == b].next == 'bank').mean(), (x.bagb == b).sum()) for b in ['<30', '30-59', '60-99', '100-199', '200+'])))
    print('   %-9s caps/game %.1f, bank next %.1f%%, cap next %.1f%%, died with it %.1f%%' % ('', len(x) / ng[k], 100 * (x.next == 'bank').mean(), 100 * (x.next == 'cap').mean(), 100 * (x.next == 'death').mean()))
print('Altar walking distance (to a tribute tile), ALL S, bag <30 / 30-59: bank next')
for lo, hi in [(0, 5), (6, 12), (13, 25), (26, 999)]:
    a = S[(S.da >= lo) & (S.da <= hi)]
    print('   %3d-%3d tiles: <30 %.0f%% (n=%d) | 30-59 %.0f%% (n=%d)' % (lo, hi, 100 * (a[a.bag < 30].next == 'bank').mean(), (a.bag < 30).sum(), 100 * (a[(a.bag >= 30) & (a.bag < 60)].next == 'bank').mean(), ((a.bag >= 30) & (a.bag < 60)).sum()))
print('Enemy within 8 at the capture (ALL S): bank next %.1f%% vs %.1f%%; died with the bag next %.1f%% vs %.1f%% (n=%d / %d)' % (
    100 * (S[S.e8 == 1].next == 'bank').mean(), 100 * (S[S.e8 == 0].next == 'bank').mean(), 100 * (S[S.e8 == 1].next == 'death').mean(), 100 * (S[S.e8 == 0].next == 'death').mean(), (S.e8 == 1).sum(), (S.e8 == 0).sum()))
