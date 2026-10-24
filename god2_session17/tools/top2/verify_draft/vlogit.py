"""vlogit.py (verify_draft): minimal logistic regression (Newton) with SEs, LR test, K-fold CV log loss."""
import numpy as np, math
from scipy import stats

def fit(X, y, l2=0.0, iters=50):
    n, p = X.shape; w = np.zeros(p)
    for _ in range(iters):
        z = X @ w; mu = 1 / (1 + np.exp(-z))
        g = X.T @ (y - mu) - l2 * w
        H = (X * (mu * (1 - mu))[:, None]).T @ X + l2 * np.eye(p)
        step = np.linalg.solve(H, g); w += step
        if np.max(np.abs(step)) < 1e-9: break
    z = X @ w; mu = np.clip(1 / (1 + np.exp(-z)), 1e-12, 1 - 1e-12)
    ll = float(np.sum(y * np.log(mu) + (1 - y) * np.log(1 - mu)))
    H = (X * (mu * (1 - mu))[:, None]).T @ X + l2 * np.eye(p)
    try: se = np.sqrt(np.diag(np.linalg.inv(H)))
    except Exception: se = np.full(p, np.nan)
    return w, se, ll

def lr_test(ll0, ll1, df):
    chi = 2 * (ll1 - ll0); return chi, float(stats.chi2.sf(chi, df))

def cv_logloss(X, y, k=10, seeds=(1, 2, 3, 4, 5), l2=0.0):
    out = []
    n = len(y)
    for s in seeds:
        rng = np.random.default_rng(s); idx = rng.permutation(n); folds = np.array_split(idx, k); tot = 0.0
        for f in folds:
            tr = np.setdiff1d(idx, f); w, _, _ = fit(X[tr], y[tr], l2=l2)
            mu = np.clip(1 / (1 + np.exp(-(X[f] @ w))), 1e-12, 1 - 1e-12)
            tot += -np.sum(y[f] * np.log(mu) + (1 - y[f]) * np.log(1 - mu))
        out.append(tot / n)
    return float(np.mean(out)), float(np.std(out))
