"""v_sizefx.py (verify_draft): champion effects (M1: rating diff + pick-count diffs) per team size; excess wins of comps vs
rating expectation (k fitted per size).  Usage: python v_sizefx.py [--window] [--dedup] [--comps SIZE]"""
import sys, glob, collections, math, numpy as np
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/top2/verify_draft')
from vcommon import *
from vlogit import *
args = sys.argv[1:]
files = glob.glob(f'{ROOT}/experiments/live/lists/wr/*.jsonl') if '--window' in args else None
M = load_matches(files=files); R, NM, RK = ratings()
rows = []
for m in M.values():
    a, b = side_teams(m)
    if a['teamId'] in R and b['teamId'] in R: rows.append((m, a, b))
if '--dedup' in args:
    seen = set(); kept = []
    for m, a, b in sorted(rows, key=lambda x: x[0]['createdAt']):
        sig = (m['map'], a['teamId'], b['teamId'], tuple(picks(a)), tuple(picks(b)))
        if sig not in seen: seen.add(sig); kept.append((m, a, b))
    rows = kept
for s in (3, 4, 5):
    rs = [r for r in rows if len(picks(r[1])) == s]
    y = np.array([1.0 if a['result'] == 'win' else 0.0 for m, a, b in rs])
    dr = np.array([(R[a['teamId']] - R[b['teamId']]) / 100 for m, a, b in rs])
    C = np.zeros((len(rs), 12))
    for i, (m, a, b) in enumerate(rs):
        for p in picks(a): C[i, p] += 1
        for p in picks(b): C[i, p] -= 1
    used = [j for j in range(12) if np.abs(C[:, j]).sum() > 0]
    ref = used[-1]; keep = [j for j in used if j != ref]
    X0 = np.column_stack([np.ones(len(y)), dr]); X1 = np.column_stack([X0, C[:, keep]])
    w0, s0, l0 = fit(X0, y); w1, s1, l1 = fit(X1, y, l2=1e-6)
    chi, p = lr_test(l0, l1, len(keep))
    full = np.zeros(12); full[keep] = w1[2:]
    cen = {j: full[j] - np.mean([full[u] for u in used]) for j in used}
    mu = 1 / (1 + np.exp(-(X1 @ w1))); cov = np.linalg.inv((X1 * (mu * (1 - mu))[:, None]).T @ X1 + 1e-6 * np.eye(X1.shape[1]))
    Cm = np.zeros((len(used), X1.shape[1]))
    for r_, j in enumerate(used):
        for kk, jj in enumerate(keep): Cm[r_, 2 + kk] = (1 if jj == j else 0) - 1 / len(used)
    sec = dict(zip(used, np.sqrt(np.diag(Cm @ cov @ Cm.T))))
    print(f'size {s}: n {len(y)} k0 {w0[1]:+.2f}±{s0[1]:.2f}; picks LR chi2 {chi:.1f} df {len(keep)} p {p:.4f}')
    print('    ', ', '.join(f'{NAMES[j]} {cen[j]:+.2f}±{sec[j]:.2f}' for j in sorted(used, key=lambda j: -cen[j])))
    if '--comps' in args and int(args[args.index('--comps') + 1]) == s:
        k = w0[1]; b0 = w0[0]
        ex = collections.defaultdict(lambda: [0.0, 0.0, 0, collections.Counter()])
        for i, (m, a, b) in enumerate(rs):
            pa = 1 / (1 + math.exp(-(b0 + k * dr[i])))
            for t, pw, yy in ((a, pa, y[i]), (b, 1 - pa, 1 - y[i])):
                key = '/'.join(sorted(NAMES[p] for p in picks(t)))
                e = ex[key]; e[0] += yy - pw; e[1] += pw * (1 - pw); e[2] += 1; e[3][t['name']] += 1
        for key, e in sorted(ex.items(), key=lambda kv: -kv[1][2])[:25]:
            print(f'     {key:18s} n {e[2]:5d} excess {e[0]:+6.1f} z {e[0]/math.sqrt(max(e[1],1e-9)):+.1f}  teams {dict(e[3].most_common(4))}')
