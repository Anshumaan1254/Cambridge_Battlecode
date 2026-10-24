# Verify C3 / C4 / C7 from vc_dec.mjs output.   python vc_dec_agg.py DIR
import json, glob, sys, collections
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
D = sys.argv[1]
games, DEC, LOW, REC, CH = [], [], [], [], []
for f in sorted(glob.glob(D + '/dec_?.jsonl')):
    for l in open(f):
        g = json.loads(l); gi = len(games)
        games.append({'gi': gi, 'key': g['key'], 'match': g['match'], 'map': g['map'], 'swon': int(g['swon'])})
        for d in g['dec']: DEC.append([gi, g['key']] + d)
        for d in g['low']: LOW.append([gi, g['key']] + d)
        for d in g['rec']: REC.append([gi, g['key']] + d)
        for d in g['chase']: CH.append([gi, g['key']] + d)
GM = pd.DataFrame(games)
DEC = pd.DataFrame(DEC, columns=['gi', 'key', 's', 'r', 'hpf', 'mhp', 'd0', 'mr', 'cr', 'weak', 'act', 'died', 'kills', 'lnet', 'recact'])
LOW = pd.DataFrame(LOW, columns=['gi', 'key', 's', 'r', 'd0', 'act', 'died15', 'mr', 'cr', 'hpf'])
REC = pd.DataFrame(REC, columns=['gi', 'key', 's', 'r', 'hpf', 'd0', 'out', 'hit', 'idle', 'death'])
CH = pd.DataFrame(CH, columns=['gi', 'key', 's', 'aty', 'vhp', 'len', 'kill', 'adied', 'ad10', 'r'])
pct = lambda m: 100 * np.mean(m)
print('================ C3: decision samples with an enemy within 4')
S = DEC[DEC.s == 1].copy(); O = DEC[DEC.s == 0].copy()
print('S samples n=%d (O n=%d)' % (len(S), len(O)))
S['lr'] = S.act.isin(['leave', 'recall'])
S['hb'] = pd.cut(S.hpf, [-1, 0.2, 0.35, 0.5, 0.7, 9], labels=['<20', '20-35', '35-50', '50-70', '70+'], right=False)
print('fight / leave+recall by own health (S):', '  '.join('%s %.0f/%.0f' % (b, pct(x.act == 'fight'), pct(x.lr)) for b, x in S.groupby('hb', observed=False)))
for col, lab in [('mr', 'max-health'), ('cr', 'current-health')]:
    x = S[S.hpf >= 0.35].copy()
    x['rb'] = pd.cut(x[col], [0, 0.45, 0.7, 1.0, 1.4, 1e9], labels=['<0.45', '0.45-0.7', '0.7-1', '1-1.4', '>=1.4'], right=False)
    print('own health >=35%%, by local %s ratio: %s' % (lab, '  '.join('%s %.0f/%.0f (n=%d)' % (b, pct(y.act == 'fight'), pct(y.lr), len(y)) for b, y in x.groupby('rb', observed=False))))
    if col == 'mr':
        for k, y in x.groupby('key'):
            lo = y[y.rb == '<0.45']; hi = y[y.rb == '>=1.4']
            print('     %-9s <0.45 %.0f/%.0f  >=1.4 %.0f/%.0f' % (k, pct(lo.act == 'fight'), pct(lo.lr), pct(hi.act == 'fight'), pct(hi.lr)))
# net per 100 by action and current-health ratio
for lab_, X in [('S', S), ('O', O)]:
    X = X.copy()
    X['crb'] = pd.cut(X.cr, [0, 0.6, 0.9, 1.2, 2, 1e9], labels=['<0.6', '0.6-0.9', '0.9-1.2', '1.2-2', '>=2'], right=False)
    X['pnet'] = X.kills - X.died
    print('%s net per 100 samples (local = enemy minus ally deaths within 10 tiles, 10 rounds | personal = own kills - own death):' % lab_)
    for b, y in X.groupby('crb', observed=False):
        print('   %-8s n=%6d  ' % (b, len(y)) + '  '.join('%s %+.1f/%+.1f (%d)' % (a, 100 * y[y.act == a].lnet.mean(), 100 * y[y.act == a].pnet.mean(), (y.act == a).sum()) for a in ['fight', 'leave', 'hold', 'recall']))
# selection check: regression of local net on action dummies with covariates, S, current ratio < 0.6
x = S[(S.cr < 0.6) & S.act.isin(['fight', 'leave', 'hold'])].copy()
x['lcr'] = np.log(x.cr.clip(0.05, 20)); x['lmr'] = np.log(x.mr.clip(0.05, 20))
m = smf.ols('lnet ~ C(act, Treatment("leave")) + hpf + lcr + lmr + d0 + np.log(mhp)', data=x).fit(cov_type='cluster', cov_kwds={'groups': x.gi})
print('S, current ratio <0.6: OLS local net ~ action + own hp + ratios + distance + max hp (clustered by game):')
for p_ in m.params.index:
    if 'act' in p_: print('   %s %+.3f (z %+.1f)' % (p_, m.params[p_], m.tvalues[p_]))
x = S[(S.cr >= 0.6) & (S.cr < 0.9) & S.act.isin(['fight', 'leave', 'hold'])].copy()
x['lcr'] = np.log(x.cr.clip(0.05, 20)); x['lmr'] = np.log(x.mr.clip(0.05, 20))
m = smf.ols('lnet ~ C(act, Treatment("leave")) + hpf + lcr + lmr + d0 + np.log(mhp)', data=x).fit(cov_type='cluster', cov_kwds={'groups': x.gi})
print('S, current ratio 0.6-0.9: same model:')
for p_ in m.params.index:
    if 'act' in p_: print('   %s %+.3f (z %+.1f)' % (p_, m.params[p_], m.tvalues[p_]))
# own death within 10 by action at <0.6 (personal risk)
y = S[S.cr < 0.6]
print('S, current ratio <0.6: own death within 10 rounds: ' + '  '.join('%s %.1f%%' % (a, pct(y[y.act == a].died)) for a in ['fight', 'leave', 'hold', 'recall']))
print('   median own hp: ' + '  '.join('%s %.2f' % (a, y[y.act == a].hpf.median()) for a in ['fight', 'leave', 'hold']) + '; median distance: ' + '  '.join('%s %.1f' % (a, y[y.act == a].d0.mean()) for a in ['fight', 'leave', 'hold']))

print('\n================ C4: recalls')
nonspam = ['pbg', 'ifish', 'coo', 'cm', 'nyx']
R = REC[(REC.s == 1) & REC.key.isin(nonspam)].copy()
R['db'] = pd.cut(R.d0, [-1, 3, 5, 8, 999], labels=['<=3', '4-5', '6-8', '>8'])
print('S non-spam recall attempts n=%d (per game: %s)' % (len(R), ', '.join('%s %.0f' % (k, len(R[R.key == k]) / (GM.key == k).sum()) for k in nonspam)))
print('   median health at start: ' + ', '.join('%s %.2f' % (k, R[R.key == k].hpf.median()) for k in nonspam))
for lab, X in [('all attempts', R), ('excluding own cancels', R[R.out != 'cancel'])]:
    print('   %s:' % lab)
    for b, y in X.groupby('db', observed=False):
        print('     nearest enemy %-4s n=%6d done %.1f%% interrupted(enemy) %.1f%% camp %.1f%% killed %.1f%% own-cancel %.1f%%' % (
            b, len(y), pct(y.out == 'done'), pct(y.out == 'interrupted'), pct(y.out == 'camp'), pct(y.out == 'killed'), pct(y.out == 'cancel')))
# opponents (spam-heavy): committed only = not own-cancelled
RO = REC[(REC.s == 0) & (REC.out != 'cancel')].copy(); RO['db'] = pd.cut(RO.d0, [-1, 3, 5, 8, 999], labels=['<=3', '4-5', '6-8', '>8'])
print('   O recalls not own-cancelled: ' + '  '.join('%s done %.0f%% killed %.1f%% (n=%d)' % (b, pct(y.out == 'done'), pct(y.out == 'killed'), len(y)) for b, y in RO.groupby('db', observed=False)))
ROi = REC[(REC.s == 0) & (REC.idle == 1)].copy(); ROi['db'] = pd.cut(ROi.d0, [-1, 3, 5, 8, 999], labels=['<=3', '4-5', '6-8', '>8'])
print('   O recalls with an idle next round: ' + '  '.join('%s done %.0f%% killed %.1f%% (n=%d)' % (b, pct(y.out == 'done'), pct(y.out == 'killed'), len(y)) for b, y in ROi.groupby('db', observed=False)))
# enemy recall within 4: hit -> fail
print('Recalls with an opposing body within 4 at the start:')
for lab, X in [('non-spam S recallers (punisher O)', R[R.d0 <= 4]),
               ('all recallers, own cancels excluded', REC[(REC.d0 <= 4) & (REC.out != 'cancel')]),
               ('all recallers, idle-next-round filter', REC[(REC.d0 <= 4) & (REC.idle == 1)])]:
    h = X[X.hit == 1]; nh = X[X.hit == 0]
    print('   %-40s n=%5d hit %.1f%% | hit: failed %.1f%% died %.1f%% (n=%d) | no hit: failed %.1f%% (n=%d)' % (
        lab, len(X), pct(X.hit), pct(h.out != 'done'), pct(h.death), len(h), pct(nh.out != 'done'), len(nh)))
for lab, X in [('S punishes O recalls (O not own-cancelled)', REC[(REC.s == 0) & (REC.d0 <= 4) & (REC.out != 'cancel')]),
               ('S punishes O recalls (idle filter)', REC[(REC.s == 0) & (REC.d0 <= 4) & (REC.idle == 1)]),
               ('O punishes S recalls (S non-spam)', R[R.d0 <= 4])]:
    print('   %-45s hit %.1f%% (n=%d)' % (lab, pct(X.hit), len(X)))
# low health crossings
L = LOW[(LOW.s == 1) & (LOW.d0 <= 8)].copy()
print('Low-health (<35%%) crossings with an enemy within 8, S: n=%d; actions %s' % (len(L), dict(L.act.value_counts(normalize=True).round(3))))
print('   died within 15 by action: ' + '  '.join('%s %.1f%% (n=%d, median d0 %.0f)' % (a, pct(L[L.act == a].died15), (L.act == a).sum(), L[L.act == a].d0.median()) for a in ['recall', 'leave', 'fight', 'hold', 'toward', 'farm']))
L['db'] = pd.cut(L.d0, [-1, 1, 3, 5, 8], labels=['1', '2-3', '4-5', '6-8'])
for b, y in L.groupby('db', observed=False):
    print('   nearest enemy %-4s: ' % b + '  '.join('%s %.1f%% (n=%d)' % (a, pct(y[y.act == a].died15), (y.act == a).sum()) for a in ['recall', 'leave', 'fight', 'hold']))
LO = LOW[(LOW.s == 0) & (LOW.d0 <= 8)]
print('   O: died within 15 by action: ' + '  '.join('%s %.1f%% (n=%d)' % (a, pct(LO[LO.act == a].died15), (LO.act == a).sum()) for a in ['recall', 'leave', 'fight', 'hold']))
# example pbg gem_fields r35
ex = REC[(REC.key == 'pbg') & (REC.gi.isin(GM[(GM.map == '00gem_fields') & GM.match.str.startswith('3fc2330b')].gi)) & (REC.r == 35) & (REC.s == 1)]
print('Example pbg/00gem_fields_3fc2330b r35:', ex[['hpf', 'd0', 'out', 'hit', 'death']].to_dict('records'))

print('\n================ C7: chases')
print('chases n=%d (S %d, O %d), per team-game %.1f' % (len(CH), (CH.s == 1).sum(), (CH.s == 0).sum(), len(CH) / len(GM) / 2))
C = CH[CH.s == 1].copy()
C['hb'] = pd.cut(C.vhp, [-1, 0.35, 0.7, 9], labels=['<35', '35-70', '>=70'], right=False)
for b, y in C.groupby('hb', observed=False):
    print('   target health %-6s n=%5d kill %.1f%%  chaser died during %.1f%%  chaser died within 10 after %.1f%%' % (b, len(y), pct(y.kill), pct(y.adied), pct(y.ad10)))
print('   length median %.0f, mean %.1f, p90 %.0f' % (C.len.median(), C.len.mean(), C.len.quantile(0.9)))
print('   kill rate by length: ' + '  '.join('%s %.0f%%' % (b, pct(y.kill)) for b, y in C.groupby(pd.cut(C.len, [0, 2, 5, 9, 999]), observed=False)))
print('   kill rate per S team: ' + ', '.join('%s %.1f%% (n=%d)' % (k, pct(y.kill), len(y)) for k, y in C.groupby('key')))
print('   O kill rate %.1f%%' % pct(CH[CH.s == 0].kill))
# net value per 100 chases by target health: kills - chaser deaths (during + 10 after)
for b, y in C.groupby('hb', observed=False):
    print('   per 100 chases, target %-6s kills %.1f, chaser deaths (during+10 after) %.1f, net %+.1f' % (b, 100 * y.kill.mean(), 100 * (y.adied | y.ad10).mean(), 100 * (y.kill.mean() - (y.adied | y.ad10).mean())))
# game level chase kill rate (S - O) vs win
gk = CH.groupby(['gi', 's']).kill.mean().unstack()
gk = gk.dropna().merge(GM, left_index=True, right_on='gi')
print('   game-level corr(S - O chase kill rate, S won) = %.3f (n=%d)' % (np.corrcoef(gk[1] - gk[0], gk.swon)[0, 1], len(gk)))
# enemy below 35% within 6 (decision samples, nearest enemy within 4)
y = S[S.weak < 0.35]
print('   decision samples with an enemy <35%% within 6 (S): fight %.0f%%, own kills per 100 (10 r) %.0f, own death %.1f%% (n=%d)' % (pct(y.act == 'fight'), 100 * y.kills.mean(), pct(y.died), len(y)))
# example
ex = CH[(CH.key == 'ifish') & (CH.gi.isin(GM[(GM.map == '00ambush') & GM.match.str.startswith('6b531f81')].gi)) & (CH.r >= 245) & (CH.r <= 256)]
print('   example ifish/00ambush_6b531f81 r245-256:', ex[['s', 'aty', 'vhp', 'len', 'kill', 'r']].to_dict('records'))
