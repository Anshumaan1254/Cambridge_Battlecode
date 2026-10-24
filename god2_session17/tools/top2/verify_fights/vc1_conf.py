# Verify C1 confounders: starter edge by engagement size / two-sidedness at even power; per-team "starting vs started on" from the
# opponent's view (does letting Pantheon / Nyx start pay?).   python vc1_conf.py DIR
import json, glob, sys
import numpy as np, pandas as pd
D = sys.argv[1]
rows = []
for f in sorted(glob.glob(D + '/c1_?.jsonl')):
    for l in open(f):
        g = json.loads(l)
        for e in g['engs']:
            e['key'] = g['key']; e['match'] = g['match']; rows.append(e)
E = pd.DataFrame(rows)
E = E[(E.mSx > 0) & (E.mOx > 0)].copy()
E['lr'] = np.log(E.mSx / E.mOx); E['dec'] = E.dS != E.dO; E['win'] = E.dS < E.dO; E['net'] = E.dO - E.dS
E['two'] = (E.dtS > 0) & (E.dtO > 0)
E['startwin'] = np.where(E.st == 1, E.win, ~E.win)
d = E[E.dec]
ev = d[np.abs(d.lr) < 0.15]
print('Even power decisive: starter wins %.1f%% (n=%d)' % (100 * ev.startwin.mean(), len(ev)))
for lab, m in [('<=5 hits', ev.n <= 5), ('6-20 hits', (ev.n > 5) & (ev.n <= 20)), ('>20 hits', ev.n > 20), ('both sides dealt damage', ev.two), ('one-sided', ~ev.two)]:
    x = ev[m]; print('   %-24s starter wins %.1f%% (n=%d)' % (lab, 100 * x.startwin.mean(), len(x)))
print('All decisive, both sides dealt damage: starter wins %.1f%% (n=%d); one-sided %.1f%% (n=%d); share one-sided %.1f%%' % (
    100 * d[d.two].startwin.mean(), d.two.sum(), 100 * d[~d.two].startwin.mean(), (~d.two).sum(), 100 * (~d.two).mean()))
print('\nFrom the opponent view: net for the OPPONENT per engagement when the opponent starts vs when the study team starts')
for k, x in E.groupby('key'):
    print('  vs %-9s opp starts: opp net %+.2f (n=%d) | %s starts: opp net %+.2f (n=%d)' % (k, -x[x.st == 0].net.mean(), (x.st == 0).sum(), k, -x[x.st == 1].net.mean(), (x.st == 1).sum()))
# same restricted to even-or-better power for the opponent (S/O ratio <= 1.15)
print('  (opponent at even-or-better power, S/O ratio <= 1.15)')
for k, x in E[np.exp(E.lr) <= 1.15].groupby('key'):
    print('  vs %-9s opp starts: opp net %+.2f (n=%d) | %s starts: opp net %+.2f (n=%d)' % (k, -x[x.st == 0].net.mean(), (x.st == 0).sum(), k, -x[x.st == 1].net.mean(), (x.st == 1).sum()))
