# Verify C5 (tribute punishment by bag size, guard locks) from vc_econ.mjs output.   python vc5_agg.py DIR
import json, glob, sys, collections
import numpy as np, pandas as pd
D = sys.argv[1]
games, T, L = [], [], []
for f in sorted(glob.glob(D + '/econ_?.jsonl')):
    for l in open(f):
        g = json.loads(l); gi = len(games)
        games.append({'gi': gi, 'key': g['key'], 'match': g['match'], 'map': g['map'], 'swon': g['swon']})
        for t in g['trib']: t = dict(t); t['gi'] = gi; t['key'] = g['key']; T.append(t)
        for x in g['locks']: x = dict(x); x['gi'] = gi; x['key'] = g['key']; L.append(x)
GM = pd.DataFrame(games); T = pd.DataFrame(T); L = pd.DataFrame(L)
ng = GM.groupby('key').size()
T['hit'] = T.hits > 0; T['stun'] = T.stuns > 0; T['lock'] = T.lockOpp > 0; T['fail'] = T.out != 'done'
T['bagb'] = pd.cut(T.bag, [-1, 99, 199, 1e9], labels=['<100', '100-199', '>=200'])
# enemy (O) tributes with a study-team body within 8 during the channel; responses are the study team's
E8 = T[(T.s == 0) & (T.minD <= 8)]
print('Enemy tributes with an S body within 8 during the channel (S responses):')
for b in ['<100', '100-199', '>=200']:
    x = E8[E8.bagb == b]
    print('   %-8s n=%5d hit %.1f%% stun %.1f%% lock %.1f%% failed %.1f%%  | median channel %d turns, median rounds with S within 4: %d' % (
        b, len(x), 100 * x.hit.mean(), 100 * x.stun.mean(), 100 * x.lock.mean(), 100 * x.fail.mean(), x.dur.median(), x.r4.median()))
# Exposure control 1: tributes with an S body within 4 at the start; hit within the first 3 rounds of the channel
print('Exposure control: S body within 4 already at the start; S hit within the first 3 rounds (r..r+2):')
x0 = T[(T.s == 0) & (T.near0 <= 4)].copy()
x0['hit3'] = (x0.firstHitR >= 0) & (x0.firstHitR <= x0.r + 2)
for b in ['<100', '100-199', '>=200']:
    x = x0[x0.bagb == b]
    print('   %-8s n=%4d hit in first 3 rounds %.1f%%  hit at all %.1f%%' % (b, len(x), 100 * x.hit3.mean(), 100 * x.hit.mean()))
# Exposure control 2: hit probability by rounds with an S body within 4 (r4) and bag
print('Hit probability by rounds with an S body within 4 during the channel (r4) and bag:')
xx = T[(T.s == 0) & (T.minD <= 8)].copy()
xx['r4b'] = pd.cut(xx.r4, [-1, 0, 2, 5, 10, 1e9], labels=['0', '1-2', '3-5', '6-10', '11+'])
print(xx.pivot_table(index='r4b', columns='bagb', values='hit', aggfunc=lambda v: '%.0f%% (%d)' % (100 * np.mean(v), len(v)), observed=False))
# own tributes: per game and completion
S_t = T[T.s == 1]
print('\nS tribute channels per game %.1f, completed %.1f%%, median bag %d, p90 %d' % (len(S_t) / len(GM), 100 * (S_t.out == 'done').mean(), S_t.bag.median(), S_t.bag.quantile(0.9)))
for k, x in S_t.groupby('key'):
    print('   %-9s per game %.1f completed %.1f%%' % (k, len(x) / ng[k], 100 * (x.out == 'done').mean()))
# locks per game per S team
print('\nAltar locks per game (S): total / guard (own tribute at that altar within 3 rounds after) / counter (cancelled a running enemy tribute) / other')
Ls = L[L.s == 1]
for k in ['cm', 'pantheon', 'ifish', 'coo', 'pbg', 'nyx']:
    x = Ls[Ls.key == k]
    print('   %-9s %.2f / %.2f / %.2f / %.2f   (n=%d)' % (k, len(x) / ng[k], x.guard.sum() / ng[k], x.counter.sum() / ng[k], ((x.guard == 0) & (x.counter == 0)).sum() / ng[k], len(x)))
Lo = L[L.s == 0]
print('   opponents %.2f per game' % (len(Lo) / len(GM)))
# share of guarded own tributes by bag
print('\nOwn S tributes preceded by own lock at that altar within 3 rounds (guard), by bag:')
for b in ['<100', '100-199', '>=200']:
    x = S_t[S_t.bagb == b]
    print('   %-8s guard %.1f%% (n=%d); done with guard %.0f%% vs without %.0f%%' % (b, 100 * x.guard.mean(), len(x), 100 * (x[x.guard == 1].out == 'done').mean() if x.guard.sum() else float('nan'), 100 * (x[x.guard == 0].out == 'done').mean()))
for k in ['cm', 'pantheon', 'ifish', 'coo']:
    x = S_t[S_t.key == k]
    print('   %-9s guarded share of its tributes %.1f%%; by bag <100 %.1f%%, 100+ %.1f%%' % (k, 100 * x.guard.mean(), 100 * x[x.bag < 100].guard.mean(), 100 * x[x.bag >= 100].guard.mean()))
# guard-lock and enemy counter-lock: were guarded own tributes ever locked by the enemy?
g1 = S_t[S_t.guard == 1]; g0 = S_t[S_t.guard == 0]
print('   enemy lock on a guarded own tribute: %d of %d (%.1f%%); on unguarded: %d of %d (%.1f%%)' % (g1.lock.sum(), len(g1), 100 * g1.lock.mean(), g0.lock.sum(), len(g0), 100 * g0.lock.mean()))
# IFish / Pantheon lock share of enemy tributes of 150+ (S within 8)
print('\nEnemy tributes of 150+ with an S body within 8: S locked / stunned / hit')
for k in ['ifish', 'pantheon', 'cm', 'nyx', 'pbg', 'coo']:
    x = E8[(E8.key == k) & (E8.bag >= 150)]
    print('   %-9s n=%3d lock %.0f%% stun %.0f%% hit %.0f%% failed %.0f%%' % (k, len(x), 100 * x.lock.mean(), 100 * x.stun.mean(), 100 * x.hit.mean(), 100 * x.fail.mean()))
# example
x = L[(L.gi.isin(GM[(GM.key == 'cm') & (GM.match.str.startswith('1586d15b'))].gi)) & (L.r >= 1420) & (L.r <= 1450)]
print('\nExample cm/00ambush_1586d15b locks r1420-1450:', x[['s', 'ty', 'r', 'alt', 'guard', 'counter']].to_dict('records'))
y = T[(T.gi.isin(x.gi)) & (T.r >= 1430) & (T.r <= 1445)]
print('   tributes r1430-1445:', y[['s', 'ty', 'r', 'bag', 'alt', 'out', 'guard']].to_dict('records'))
