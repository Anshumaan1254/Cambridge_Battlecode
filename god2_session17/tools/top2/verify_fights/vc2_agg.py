# Verify C2 (Prism carry) from vc_econ.mjs output.   python vc2_agg.py DIR
import json, glob, sys, collections
import numpy as np, pandas as pd

D = sys.argv[1]
G = json.load(open(D + '/games.json'))
gl = {g['match'] + g['key']: g for g in G}
games, T, CAP, DE, PR = [], [], [], [], []
for f in sorted(glob.glob(D + '/econ_?.jsonl')):
    for l in open(f):
        g = json.loads(l)
        gi = len(games)
        meta = gl[g['match'] + g['key']]
        games.append({'gi': gi, 'key': g['key'], 'match': g['match'], 'swon': int(g['swon']), 'final': g['final'], 'sPrism': g['sPrism'],
                      'sdraft': meta['sdraft'], 'odraft': meta['odraft']})
        for t in g['trib']: t = dict(t); t['gi'] = gi; t['key'] = g['key']; t['final'] = g['final']; T.append(t)
        for c in g['caps']: c = dict(c); c['gi'] = gi; c['key'] = g['key']; CAP.append(c)
        for d in g['deaths']: d = dict(d); d['gi'] = gi; d['key'] = g['key']; DE.append(d)
        for p in g['prism']: PR.append([gi, g['key']] + p)
GM = pd.DataFrame(games); T = pd.DataFrame(T); CAP = pd.DataFrame(CAP); DE = pd.DataFrame(DE)
PR = pd.DataFrame(PR, columns=['gi', 'key', 's', 'r', 'bag', 'hpf', 'mhp', 'dmg', 'died', 'lratio', 'ne'])
ng = GM.groupby('key').size()
print('(a) Prism (draft 5) in S draft:', {k: '%d/%d' % (sum(5 in d for d in x.sdraft), len(x)) for k, x in GM.groupby('key')})
# (b) carriers of 100+ bags (captures leaving the S capturer with >= 100 gems)
c100 = CAP[(CAP.s == 1) & (CAP.bag >= 100)]
print('(b) S captures leaving 100+ gems, carrier share:')
for k in ['pbg', 'pantheon', 'nyx', 'ifish', 'cm', 'coo']:
    x = c100[c100.key == k]; tot = (CAP[(CAP.s == 1) & (CAP.key == k)]).shape[0]
    vc = x.ty.value_counts(normalize=True)
    print('   %-9s %.1f%% of captures; %s' % (k, 100 * len(x) / tot, ', '.join('%s %.0f%%' % (a, 100 * b) for a, b in vc.head(3).items())))
# (c) Prism tributes of 100+ gems by S
TS = T[T.s == 1]
for k in ['pbg', 'pantheon', 'nyx']:
    x = TS[(TS.key == k) & (TS.ty == 'Prism') & (TS.bag >= 100)]
    end = (x.own + x.bag >= 1000)
    banked_all = TS[(TS.key == k) & (TS.out == 'done')].bag.sum()
    banked_p100 = x[x.out == 'done'].bag.sum()
    banked_p = TS[(TS.key == k) & (TS.out == 'done') & (TS.ty == 'Prism')].bag.sum()
    # episodes: consecutive attempts of the same body where the next starts within 12 rounds of the previous end
    ep = []
    for (gi, who), y in x.sort_values('q').groupby(['gi', 'who']):
        cur = None
        for _, t in y.iterrows():
            if cur is not None and t.r - cur['r1'] <= 12:
                cur['n'] += 1; cur['r1'] = t.r1; cur['done'] |= t.out == 'done'; cur['outs'].append(t.out)
            else:
                if cur: ep.append(cur)
                cur = {'gi': gi, 'r': t.r, 'r1': t.r1, 'bag': t.bag, 'n': 1, 'done': t.out == 'done', 'outs': [t.out], 'own': t.own}
        if cur: ep.append(cur)
    ep = pd.DataFrame(ep)
    print('(c) %-9s Prism 100+ tributes n=%d (%.2f/game) median bag %d median round %d; would end game %.0f%%; done/attempt %.0f%%; '
          'episodes %d done/episode %.0f%%; Prism 100+ share of banked gems %.0f%% (all Prism banks %.0f%%)' % (
              k, len(x), len(x) / ng[k], x.bag.median(), x.r.median(), 100 * end.mean(), 100 * (x.out == 'done').mean(), len(ep),
              100 * ep.done.mean() if len(ep) else 0, 100 * banked_p100 / banked_all, 100 * banked_p / banked_all))
    print('     outcomes per attempt:', dict(collections.Counter(x.out)))
# (d) Prism samples by phase and bag
print('(d) Prism with an enemy within 6 (every 3rd round), damage dealt in next 5 rounds / died within 10:')
PR['phase'] = pd.cut(PR.r, [0, 600, 1000, 3000], labels=['r<600', '600-1000', '>=1000'], right=False)
PR['bagb'] = pd.cut(PR.bag, [-1, 49, 149, 1e9], labels=['<50', '50-149', '150+'])
for s in [1, 0]:
    for ph in ['r<600', '600-1000', '>=1000']:
        out = []
        for bb in ['<50', '150+']:
            x = PR[(PR.s == s) & (PR.phase == ph) & (PR.bagb == bb)]
            out.append('%s n=%d dmg %.0f died %.1f%%' % (bb, len(x), x.dmg.mean(), 100 * x.died.mean()))
        print('   %s %-8s %s' % ('S' if s else 'O', ph, ' | '.join(out)))
# confounder: condition on hp fraction >= 0.7 and local ratio bins
print('   S, r600-1000, hp>=70%, by local max-health ratio within 8:')
x = PR[(PR.s == 1) & (PR.phase == '600-1000') & (PR.hpf >= 0.7)]
for lo, hi in [(0, 0.8), (0.8, 1.25), (1.25, 99)]:
    a = x[(x.lratio >= lo) & (x.lratio < hi)]
    print('     ratio %.2f-%.2f: <50 n=%d died %.1f%% dmg %.0f | 150+ n=%d died %.1f%% dmg %.0f' % (lo, hi,
          (a.bagb == '<50').sum(), 100 * a[a.bagb == '<50'].died.mean(), a[a.bagb == '<50'].dmg.mean(),
          (a.bagb == '150+').sum(), 100 * a[a.bagb == '150+'].died.mean(), a[a.bagb == '150+'].dmg.mean()))
print('   median local ratio: <50 %.2f  150+ %.2f; median max hp: <50 %d 150+ %d; median nearest enemy: <50 %.1f 150+ %.1f' % (
    PR[(PR.s == 1) & (PR.bagb == '<50')].lratio.median(), PR[(PR.s == 1) & (PR.bagb == '150+')].lratio.median(),
    PR[(PR.s == 1) & (PR.bagb == '<50')].mhp.median(), PR[(PR.s == 1) & (PR.bagb == '150+')].mhp.median(),
    PR[(PR.s == 1) & (PR.bagb == '<50')]['ne'].mean(), PR[(PR.s == 1) & (PR.bagb == '150+')]['ne'].mean()))
# within-game comparison: games where the same team's Prism has both <50 and 150+ samples in the same phase
w = []
for (gi, ph), x in PR[PR.s == 1].groupby(['gi', 'phase'], observed=True):
    a = x[x.bagb == '<50']; b = x[x.bagb == '150+']
    if len(a) >= 3 and len(b) >= 3: w.append((a.died.mean(), b.died.mean(), a.dmg.mean(), b.dmg.mean()))
w = np.array(w)
print('   within game-phase pairs n=%d: died <50 %.1f%% vs 150+ %.1f%%; dmg %.0f vs %.0f' % (len(w), 100 * w[:, 0].mean(), 100 * w[:, 1].mean(), w[:, 2].mean(), w[:, 3].mean()))
# (e) tributes of 400+
for s, lab in [(1, 'S'), (0, 'O')]:
    x = T[(T.s == s) & (T.bag >= 400)]
    print('(e) %s tributes 400+: n=%d done %.0f%% outcomes %s' % (lab, len(x), 100 * (x.out == 'done').mean(), dict(collections.Counter(x.out))))
# (f) Prism 100+ tributes by S with enemy within 8 at the start
x = TS[(TS.ty == 'Prism') & (TS.bag >= 100)]
print('(f) S Prism 100+ tributes: enemy within 8 at start done %.0f%% (n=%d); none within 8 done %.0f%% (n=%d)' % (
    100 * (x[x.near0 <= 8].out == 'done').mean(), (x.near0 <= 8).sum(), 100 * (x[x.near0 > 8].out == 'done').mean(), (x.near0 > 8).sum()))
print('    outcomes with enemy within 8:', dict(collections.Counter(x[x.near0 <= 8].out)))
# (g) responses to tributes with an opposing body within 4 during the channel (pooled, both directions)
def resp(t):
    if t.lockOpp > 0: return 'lock'
    if t.stuns > 0: return 'stun'
    if t.hits > 0: return 'damage'
    return 'none'
y = T[T.minD <= 4].copy(); y['resp'] = y.apply(resp, axis=1)
print('(g) tributes with an opposing body within 4 during the channel (pooled):')
for r_ in ['none', 'damage', 'stun', 'lock']:
    z = y[y.resp == r_]
    print('   %-7s n=%5d failed %.1f%% killed %.1f%% self-cancel %.1f%%' % (r_, len(z), 100 * (z.out != 'done').mean(), 100 * (z.out == 'killed').mean(), 100 * (z.out == 'cancel').mean()))
yd = y.drop_duplicates(subset=['gi', 'q'])
# dedup the 54 matches seen twice
first = GM.drop_duplicates('match').gi
y2 = y[y.gi.isin(first)]
print('   dedup matches:', {r_: '%d %.1f%%' % (len(y2[y2.resp == r_]), 100 * (y2[y2.resp == r_].out != 'done').mean()) for r_ in ['none', 'damage', 'stun', 'lock']})
# damage only: does damage stop it, or the kill?
z = y[y.resp == 'damage']
print('   damage only: failed but not killed %.1f%%; of which self-cancel %.1f%%' % (100 * ((z.out != 'done') & (z.out != 'killed')).mean(), 100 * (z.out == 'cancel').mean()))
# (h) loaded Prism deaths
for k in ['pbg', 'pantheon', 'nyx']:
    x = DE[(DE.key == k) & (DE.s == 1) & (DE.ty == 'Prism') & (DE.bag >= 100)]
    print('(h) %-9s loaded-Prism deaths %d, gems %d (%.0f a game)' % (k, len(x), x.bag.sum(), x.bag.sum() / ng[k]))
