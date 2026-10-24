"""v_meta.py (verify_draft): window = wr/*.jsonl lists (top-50 teams' newest ranked games). Pick rates, rating slope,
champion-pick LR test and CV.  Usage: python v_meta.py [--all] [--since ISO] [--dedup]"""
import sys, glob, collections, numpy as np
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/top2/verify_draft')
from vcommon import *
from vlogit import *
args = sys.argv[1:]
since = args[args.index('--since') + 1] if '--since' in args else '2026-10-22T07:00:00Z'
files = None if '--all' in args else glob.glob(f'{ROOT}/experiments/live/lists/wr/*.jsonl')
M = load_matches(since=since, files=files)
R, NM, RK = ratings()
rows = []
for m in M.values():
    a, b = side_teams(m)
    if a['teamId'] not in R or b['teamId'] not in R: continue
    rows.append((m, a, b))
print('matches', len(M), 'with both rated', len(rows), 'time', min(m['createdAt'] for m, a, b in rows), max(m['createdAt'] for m, a, b in rows))
if '--dedup' in args:
    seen = set(); kept = []
    for m, a, b in sorted(rows, key=lambda x: x[0]['createdAt']):
        sig = (m['map'], a['teamId'], b['teamId'], tuple(picks(a)), tuple(picks(b)))
        if sig in seen: continue
        seen.add(sig); kept.append((m, a, b))
    print('dedup (map, teams+sides, drafts):', len(kept), 'of', len(rows)); rows = kept
# pick rates over team-drafts
cnt = collections.Counter(); nt = 0
for m, a, b in rows:
    for t in (a, b):
        nt += 1
        for p in set(picks(t)): cnt[p] += 1
print('pick rate per team-draft:', ', '.join(f'{NAMES[p]} {cnt[p]/nt:.2f}' for p, _ in cnt.most_common()))
y = np.array([1.0 if a['result'] == 'win' else 0.0 for m, a, b in rows])
dr = np.array([(R[a['teamId']] - R[b['teamId']]) / 100 for m, a, b in rows])
print('side a win rate', y.mean().round(3))
X0 = np.column_stack([np.ones(len(y)), dr])
w0, se0, ll0 = fit(X0, y)
print(f'M0: b0 {w0[0]:+.3f}±{se0[0]:.3f}  k {w0[1]:+.3f}±{se0[1]:.3f} per 100; logLik {ll0:.1f}; CV {cv_logloss(X0, y)}')
C = np.zeros((len(y), 12))
for i, (m, a, b) in enumerate(rows):
    for p in picks(a): C[i, p] += 1
    for p in picks(b): C[i, p] -= 1
# drop one champion column (sum of diffs = 0) -> use 11 columns, report effects centred
keep = list(range(11))  # drop Ho (11) as reference
X1 = np.column_stack([X0, C[:, keep]])
w1, se1, ll1 = fit(X1, y)
chi, p = lr_test(ll0, ll1, len(keep))
print(f'M1: k {w1[1]:+.3f}±{se1[1]:.3f}; LR chi2 {chi:.1f} df {len(keep)} p {p:.4f}; CV {cv_logloss(X1, y)}')
# centred effects: effect_j = w_j - mean(w over 12 incl ref 0)
full = np.zeros(12); full[keep] = w1[2:]; cen = full - full.mean()
# SE of centred effect via covariance
cov = np.linalg.inv((X1 * ((1/(1+np.exp(-(X1@w1))))*(1-1/(1+np.exp(-(X1@w1)))))[:, None]).T @ X1)
Cm = np.zeros((12, X1.shape[1]))
for j in range(12):
    for kk, jj in enumerate(keep): Cm[j, 2 + kk] = (1 if jj == j else 0) - 1/12
    if j == 11: pass
sec = np.sqrt(np.diag(Cm @ cov @ Cm.T))
print('M1 centred effects:', ', '.join(f'{NAMES[j]} {cen[j]:+.2f}±{sec[j]:.2f}' for j in np.argsort(-cen)))
# per team size
for s in (3, 4, 5):
    idx = [i for i, (m, a, b) in enumerate(rows) if len(picks(a)) == s]
    if len(idx) < 50: continue
    ws, ss, _ = fit(X0[idx], y[idx])
    fav = [i for i in idx if abs(dr[i]) >= 0.5]
    fw = np.mean([(y[i] == 1) == (dr[i] > 0) for i in fav])
    print(f'size {s}: n {len(idx)} k {ws[1]:+.3f}±{ss[1]:.3f}; favourite (>=50 pts) wins {fw:.3f} (n {len(fav)})')
