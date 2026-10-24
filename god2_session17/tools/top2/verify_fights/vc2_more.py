# Verify C2 follow-ups: share of banked gems (several bases), per-episode completion when contested, loaded-Prism death rate
# stratified by max health and within game-phase (Mantel-Haenszel).   python vc2_more.py DIR
import json, glob, sys, collections
import numpy as np, pandas as pd
D = sys.argv[1]
games, T, PR = [], [], []
for f in sorted(glob.glob(D + '/econ_?.jsonl')):
    for l in open(f):
        g = json.loads(l); gi = len(games)
        games.append({'gi': gi, 'key': g['key'], 'swon': g['swon'], 'subS': g['sub'][0], 'subO': g['sub'][1]})
        for t in g['trib']: t = dict(t); t['gi'] = gi; t['key'] = g['key']; T.append(t)
        for p in g['prism']: PR.append([gi, g['key']] + p)
GM = pd.DataFrame(games); T = pd.DataFrame(T)
PR = pd.DataFrame(PR, columns=['gi', 'key', 's', 'r', 'bag', 'hpf', 'mhp', 'dmg', 'died', 'lratio', 'near'])
TS = T[T.s == 1]
for k in ['pbg', 'pantheon', 'nyx']:
    tot_final = GM[GM.key == k].subS.sum()
    done = TS[(TS.key == k) & (TS.out == 'done')]
    p100 = done[(done.ty == 'Prism') & (done.bag >= 100)]
    gws = p100.gi.unique()
    in_g = done[done.gi.isin(gws)]
    print('%-9s final S score sum %d; done-tribute bags sum %d; Prism100 done %d (%.0f%% of all; %.0f%% within the %d games where one completed);'
          ' Prism100 incl. attempts %d (%.0f%%)' % (k, tot_final, done.bag.sum(), p100.bag.sum(), 100 * p100.bag.sum() / done.bag.sum(),
          100 * p100.bag.sum() / in_g.bag.sum(), len(gws), TS[(TS.key == k) & (TS.ty == 'Prism') & (TS.bag >= 100)].bag.sum(),
          100 * TS[(TS.key == k) & (TS.ty == 'Prism') & (TS.bag >= 100)].bag.sum() / done.bag.sum()))
# per-episode completion when contested (Prism 100+ by S): episode = attempts by the same body with the next start within 12 rounds
x = TS[(TS.ty == 'Prism') & (TS.bag >= 100)].sort_values(['gi', 'who', 'q'])
ep = []
for (gi, who), y in x.groupby(['gi', 'who']):
    cur = None
    for _, t in y.iterrows():
        if cur is not None and t.r - cur['r1'] <= 12:
            cur['n'] += 1; cur['r1'] = t.r1; cur['done'] |= (t.out == 'done'); cur['outs'].append(t.out); cur['near'] = min(cur['near'], t.near0)
        else:
            if cur: ep.append(cur)
            cur = {'gi': gi, 'key': t.key, 'r': t.r, 'r1': t.r1, 'bag': t.bag, 'n': 1, 'done': t.out == 'done', 'outs': [t.out], 'near0': t.near0, 'near': t.near0}
    if cur: ep.append(cur)
ep = pd.DataFrame(ep)
print('\nS Prism 100+ carry episodes n=%d, attempts per episode mean %.1f, done %.0f%%' % (len(ep), ep.n.mean(), 100 * ep.done.mean()))
print('   enemy within 8 at the first attempt: done %.0f%% (n=%d); not: done %.0f%% (n=%d)' % (100 * ep[ep.near0 <= 8].done.mean(), (ep.near0 <= 8).sum(), 100 * ep[ep.near0 > 8].done.mean(), (ep.near0 > 8).sum()))
fail = ep[~ep.done]
last = collections.Counter(o[-1] for o in fail.outs)
print('   failed episodes: last outcome', dict(last), ' episodes with any stun/lock/kill: %.0f%%' % (100 * np.mean([any(o in ('stunned', 'locked', 'killed') for o in os_) for os_ in fail.outs])))
for k, y in ep.groupby('key'): print('   %-9s episodes %d done %.0f%%' % (k, len(y), 100 * y.done.mean()))
# loaded Prism death rate: stratify by max health
print('\nPrism samples (S, enemy within 6): died within 10 rounds by max-health bin and bag')
PR['bagb'] = pd.cut(PR.bag, [-1, 49, 149, 1e9], labels=['<50', '50-149', '150+'])
S = PR[PR.s == 1]
for lo, hi in [(0, 1000), (1000, 1600), (1600, 2400), (2400, 99999)]:
    a = S[(S.mhp >= lo) & (S.mhp < hi)]
    print('   maxHp %5d-%5d: <50 n=%5d died %.1f%% dmg %3.0f | 150+ n=%5d died %.1f%% dmg %3.0f' % (lo, hi, (a.bagb == '<50').sum(), 100 * a[a.bagb == '<50'].died.mean(), a[a.bagb == '<50'].dmg.mean(),
          (a.bagb == '150+').sum(), 100 * a[a.bagb == '150+'].died.mean(), a[a.bagb == '150+'].dmg.mean()))
# Mantel-Haenszel risk ratio over game x 200-round phase strata
num = den = 0.0; nstr = 0; n1 = n0 = 0
for (gi, ph), y in S.assign(ph=S.r // 200).groupby(['gi', 'ph']):
    a = y[y.bagb == '150+']; b = y[y.bagb == '<50']
    if len(a) == 0 or len(b) == 0: continue
    N = len(a) + len(b); nstr += 1; n1 += len(a); n0 += len(b)
    num += a.died.sum() * len(b) / N; den += b.died.sum() * len(a) / N
print('   Mantel-Haenszel risk ratio (150+ vs <50), strata = game x 200-round window: %.2f (strata %d, n %d / %d)' % (num / den if den else float('nan'), nstr, n1, n0))
# same for damage: mean within-stratum difference weighted
diffs = []
for (gi, ph), y in S.assign(ph=S.r // 200).groupby(['gi', 'ph']):
    a = y[y.bagb == '150+']; b = y[y.bagb == '<50']
    if len(a) and len(b): diffs.append((a.dmg.mean(), b.dmg.mean(), min(len(a), len(b))))
d = np.array(diffs)
print('   within-stratum damage: 150+ %.0f vs <50 %.0f (weighted ratio %.2f)' % (np.average(d[:, 0], weights=d[:, 2]), np.average(d[:, 1], weights=d[:, 2]), np.average(d[:, 0], weights=d[:, 2]) / np.average(d[:, 1], weights=d[:, 2])))
