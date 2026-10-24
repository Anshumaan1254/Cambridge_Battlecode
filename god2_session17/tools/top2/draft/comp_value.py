#!/usr/bin/env python3
"""Value of compositions on the ladder, controlling for rating: logit P(side a wins) = b0 + k * (r_a - r_b) / 100 + w . (F(draft a) - F(draft b)).
Feature sets: champion indicators (sum-to-zero centred effects with SEs), engine-derived role counts, team-core indicators, pair synergies.
Also: team fixed effects (Bradley-Terry) instead of ratings, and grouped 5-fold CV log loss of each model against rating-only.
Data: experiments/live/lists/wr/*.jsonl (top-50 teams' newest 150 ranked games, Oct 23 09:50-15:00), ratings C:/battlecode/cache/ladder_now.json.
  python tools/top2/draft/comp_value.py [--since ISO] [--which wr|all] [--min-rating R]"""
import collections, json, math, sys
import numpy as np
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import common as C

RANGED = {1, 4, 5, 7, 10}          # Vesper, Stellar, Prism, Willow, Tavi (+ Cassi of C&I)
STUN = {0, 3, 5, 6, 8, 10, 11}     # Ryth aoe, Cassi, Prism, Marcella enhanced, Ren, Tavi, HoR dash
DASH = {1, 2, 3, 8, 11}            # Vesper, Vendetta, Issac, Ren, HoR
GOLD = {1, 6}                      # Vesper +33% gold, Marcella 2 gold per tributed gem
SHIELD = {9, 11}                   # Varg, HoR self-shields
AREA = {0, 4, 5, 6, 11}            # Ryth stun aoe, Stellar aoe, Prism aoe, Marcella? (no) -> fixed below
AREA = {0, 4, 5, 9, 11}            # Ryth aoe stun, Stellar aoe, Prism aoe, Varg splash, HoR dash landing


def role_feats(d, ENG):
	"""Engine-derived counts for one draft (list of draft ids)."""
	hp = st = 0.0
	n_r = n_m = 0
	for x in d:
		for t in C.ENGINE_TYPES[x]:
			c = ENG[t]
			hp += c['hp']
			st += c['st']
			if c['rng'] > 1:
				n_r += 1
			else:
				n_m += 1
	return dict(ranged=n_r, melee=n_m, stun=sum(x in STUN for x in d), dash=sum(x in DASH for x in d), gold=sum(x in GOLD for x in d),
		shield=sum(x in SHIELD for x in d), area=sum(x in AREA for x in d), heal=int(7 in d), bodies=len(d) + int(3 in d),
		hp=hp / 1000.0, strength=st / 100.0)


CORES = {
	'PrVeMa': lambda s: {5, 1, 6} <= s,
	'VeVdHo': lambda s: {1, 2, 11} <= s,
	'PrVe': lambda s: {5, 1} <= s,
	'VeHo': lambda s: {1, 11} <= s,
	'PrHo': lambda s: {5, 11} <= s,
	'VdHo': lambda s: {2, 11} <= s,
	'VeVd': lambda s: {1, 2} <= s,
	'MaHo': lambda s: {6, 11} <= s,
}


def load(which, since, minr):
	R = C.ratings()
	ms = [m for m in C.matches(which, since=since) if m['a'] in R and m['b'] in R]
	ms = [m for m in ms if min(R[m['a']]['rating'], R[m['b']]['rating']) >= minr]
	return ms, R


def logloss(y, p):
	p = np.clip(p, 1e-6, 1 - 1e-6)
	return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def cv(X, y, groups, C_=1.0, k=5):
	"""Grouped CV log loss of an L2 logistic model (C_ = inverse penalty)."""
	gkf = GroupKFold(n_splits=k)
	p = np.zeros(len(y))
	for tr, te in gkf.split(X, y, groups):
		m = LogisticRegression(C=C_, max_iter=2000)
		m.fit(X[tr], y[tr])
		p[te] = m.predict_proba(X[te])[:, 1]
	return logloss(y, p)


def centred(res, idx, names):
	"""Sum-to-zero champion effects from a fit with a reference column dropped. idx: param index for each name (None = reference)."""
	params = res.params
	cov = res.cov_params()
	k = len(names)
	# effect vector e_c = w_c (0 for ref); centred = e - mean(e)
	A = np.zeros((k, len(params)))
	for i, j in enumerate(idx):
		if j is not None:
			A[i, j] += 1
	A = A - A.mean(axis=0, keepdims=True)
	est = A @ params
	se = np.sqrt(np.einsum('ij,jk,ik->i', A, cov, A))
	return est, se


def main():
	a = sys.argv[1:]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	since = opt('--since', '2026-10-23T09:00')
	which = opt('--which', 'wr')
	minr = float(opt('--min-rating', '0'))
	ENG = C.engine()
	ms, R = load(which, since, minr)
	y = np.array([m['awin'] for m in ms], float)
	rd = np.array([(R[m['a']]['rating'] - R[m['b']]['rating']) / 100.0 for m in ms])
	groups = np.array([hash(m['group'] or m['id']) % 10 ** 9 for m in ms])
	print(f'games {len(ms)} ({which}, since {since}, min rating {minr}); side a wins {y.mean():.3f}; teams '
		f'{len(set([m["a"] for m in ms] + [m["b"] for m in ms]))}')
	# champion pick rates and raw win rates
	cnt = collections.Counter()
	wins = collections.Counter()
	for m in ms:
		for d, w in ((m['da'], m['awin']), (m['db'], 1 - m['awin'])):
			for x in set(d):
				cnt[x] += 1
				wins[x] += w
	print('pick rate / raw win rate per champion (team-games):')
	print('  ' + ', '.join(f'{C.NAMES[x]} {cnt[x] / (2 * len(ms)):.2f}/{wins[x] / max(1, cnt[x]):.3f}' for x in range(12)))

	# M0: rating only
	X0 = rd.reshape(-1, 1)
	r0 = sm.Logit(y, sm.add_constant(X0)).fit(disp=0)
	print(f'\nM0 rating only: const {r0.params[0]:+.3f}, per 100 rating {r0.params[1]:+.3f} (se {r0.bse[1]:.3f}); '
		f'in-sample LL {r0.llf:.1f}; CV logloss {cv(X0, y, groups, 1e6):.4f}')

	# M1: champion indicators (diff), reference Ryth dropped for the unpenalised fit
	D = np.array([[int(x in m['da']) - int(x in m['db']) for x in range(12)] for m in ms], float)
	ref = 0
	cols = [c for c in range(12) if c != ref]
	X1 = np.column_stack([rd, D[:, cols]])
	r1 = sm.Logit(y, sm.add_constant(X1)).fit(disp=0)
	idx = [None if c == ref else 2 + cols.index(c) for c in range(12)]
	est, se = centred(r1, idx, C.NAMES)
	lr = 2 * (r1.llf - r0.llf)
	from scipy.stats import chi2
	print(f'\nM1 rating + champion picks: per 100 rating {r1.params[1]:+.3f}; LR test vs M0 chi2={lr:.1f} df=11 p={chi2.sf(lr, 11):.4f}; '
		f'CV logloss (L2 C=1) {cv(np.column_stack([rd, D]), y, groups, 1.0):.4f}, (C=0.1) {cv(np.column_stack([rd, D]), y, groups, 0.1):.4f}')
	print('  champion effect (logit, centred on the average champion) +- se:')
	order = np.argsort(-est)
	print('  ' + ', '.join(f'{C.NAMES[i]} {est[i]:+.2f}+-{se[i]:.2f}' for i in order))

	# M2: role features (engine-derived)
	RF = ['ranged', 'stun', 'dash', 'gold', 'shield', 'area', 'heal', 'bodies', 'hp', 'strength']
	FA = [role_feats(m['da'], ENG) for m in ms]
	FB = [role_feats(m['db'], ENG) for m in ms]
	X2f = np.array([[fa[k] - fb[k] for k in RF] for fa, fb in zip(FA, FB)], float)
	X2 = np.column_stack([rd, X2f])
	r2 = sm.Logit(y, sm.add_constant(X2)).fit(disp=0)
	lr2 = 2 * (r2.llf - r0.llf)
	print(f'\nM2 rating + role counts: LR vs M0 chi2={lr2:.1f} df={len(RF)} p={chi2.sf(lr2, len(RF)):.4f}; CV logloss {cv(X2, y, groups, 1.0):.4f}')
	print('  ' + ', '.join(f'{k} {r2.params[2 + i]:+.3f}+-{r2.bse[2 + i]:.3f}' for i, k in enumerate(RF)))

	# M3: cores
	KC = list(CORES)
	X3f = np.array([[int(CORES[k](set(m['da']))) - int(CORES[k](set(m['db']))) for k in KC] for m in ms], float)
	for k_i, k in enumerate(KC):
		Xk = np.column_stack([rd, X3f[:, k_i]])
		rk = sm.Logit(y, sm.add_constant(Xk)).fit(disp=0)
		n1 = int(np.sum(X3f[:, k_i] != 0))
		print(f'  core {k:7s}: games where exactly one side has it {n1:4d}; effect {rk.params[2]:+.3f}+-{rk.bse[2]:.3f} (z {rk.params[2] / rk.bse[2]:+.1f})')

	# M4: team fixed effects (Bradley-Terry) + champion picks: within-team (map-dependent) draft variation only
	teams = sorted(set([m['a'] for m in ms] + [m['b'] for m in ms]))
	ti = {t: i for i, t in enumerate(teams)}
	T = np.zeros((len(ms), len(teams)))
	for i, m in enumerate(ms):
		T[i, ti[m['a']]] += 1
		T[i, ti[m['b']]] -= 1
	XT = np.column_stack([T, D])
	mfe = LogisticRegression(C=10.0, max_iter=5000, fit_intercept=True)
	mfe.fit(XT, y)
	w = mfe.coef_[0][len(teams):]
	w = w - w.mean()
	print('\nM4 team fixed effects (L2 C=10) + champion picks, centred (within-team variation only):')
	print('  ' + ', '.join(f'{C.NAMES[i]} {w[i]:+.2f}' for i in np.argsort(-w)))
	print(f'  CV logloss: teams only {cv(T, y, groups, 10.0):.4f}, teams + picks {cv(XT, y, groups, 10.0):.4f}')

	# per team size subsets
	for size in (3, 4, 5):
		sel = np.array([len(m['da']) == size for m in ms])
		if sel.sum() < 100:
			continue
		Xs = np.column_stack([rd[sel], D[sel][:, cols]])
		try:
			rs = sm.Logit(y[sel], sm.add_constant(Xs)).fit(disp=0)
			e, s = centred(rs, idx, C.NAMES)
			print(f'\nsize {size}: {sel.sum()} games; rating per 100 {rs.params[1]:+.3f}; champion effects:')
			print('  ' + ', '.join(f'{C.NAMES[i]} {e[i]:+.2f}+-{s[i]:.2f}' for i in np.argsort(-e) if abs(s[i]) < 5))
		except Exception as ex:
			print('size', size, 'fit failed', ex)


if __name__ == '__main__':
	main()
