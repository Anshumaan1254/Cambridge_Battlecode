#!/usr/bin/env python3
"""tools/draftmodel/fit.py GAMES.jsonl PROBE.txt MAPFEAT.json [--l2 X] [--feats a,b,...] [--free a,b]

Logistic fit of win ~ side + w . (team features ours - theirs), features from the engine's numbers and the map (feats.py), on kept
games (dataset.py). Base stat weights are kept >= 0 (more of a stat never lowers a pick's value) except the --free ones (default:
side, bodies, and every map interaction). Prints the weights, the value of each pick on an average map, a leave-one-cell-out check
and a 5-fold leave-maps-out check (log loss and accuracy vs the side-only model)."""
import json, sys
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import feats as FT


def main():
	a = sys.argv[1:]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	l2 = float(opt('--l2', '1'))
	use = opt('--feats', ','.join(FT.FEATS)).split(',')
	free = set(['side', 'bodies'] + FT.INTER + [x for x in opt('--free', '').split(',') if x])
	games = [json.loads(l) for l in open(a[0])]
	ch = FT.parse(a[1])
	mfs = json.load(open(a[2]))
	X, y, cells, maps = [], [], [], []
	for g in games:
		mf = mfs.get(g['map'])
		if mf is None:
			continue
		fo, ft = FT.team(ch, g['ours'], mf), FT.team(ch, g['theirs'], mf)
		X.append([1.0 if g['side'] == 'A' else -1.0] + [fo[k] - ft[k] for k in use])
		y.append(1.0 if g['win'] else 0.0)
		cells.append(g['cell'])
		maps.append(g['map'])
	X, y = np.array(X), np.array(y)
	names = ['side'] + use
	lo = np.array([-np.inf if n in free else 0.0 for n in names])

	def fit(Xs, ys, lo=lo):
		w = np.zeros(Xs.shape[1])
		for _ in range(300):
			p = 1 / (1 + np.exp(-np.clip(Xs @ w, -30, 30)))
			g = Xs.T @ (p - ys) + l2 * w
			H = (Xs.T * (p * (1 - p))) @ Xs + l2 * np.eye(len(w))
			act = (w <= lo + 1e-12) & (g > 0)
			fr = ~act
			step = np.zeros_like(w)
			if fr.any():
				step[fr] = np.linalg.solve(H[np.ix_(fr, fr)], g[fr])
			w = np.maximum(lo, w - step)
		return w

	def loss(w, Xs, ys):
		p = np.clip(1 / (1 + np.exp(-np.clip(Xs @ w, -30, 30))), 1e-6, 1 - 1e-6)
		return float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p))), float(np.mean((p > 0.5) == (ys > 0.5)))

	w = fit(X, y)
	print(f'{len(y)} games; weights:', ' '.join(f'{k} {v:+.3f}' for k, v in zip(names, w)))
	avg = {k: float(np.mean([mfs[m][k] for m in set(maps)])) for k in mfs[maps[0]]}
	vals = {}
	for n in FT.PICK_TYPES:
		f = FT.pick(ch, n, avg)
		vals[n] = sum(w[1 + i] * f[k] for i, k in enumerate(use))
	base = vals['Stellar']
	print('pick values on an average map (Stellar = 0):', '  '.join(f'{n} {v - base:+.2f}' for n, v in sorted(vals.items(), key=lambda z: -z[1])))
	print('leave-one-cell-out (observed / predicted win rate):')
	for c in sorted(set(cells)):
		m = np.array([x != c for x in cells])
		wc = fit(X[m], y[m])
		p = 1 / (1 + np.exp(-X[~m] @ wc))
		print(f'  {c:22s} {y[~m].mean():.3f} / {p.mean():.3f}')
	um = sorted(set(maps))
	rng = np.random.default_rng(1)
	rng.shuffle(um)
	folds = [set(um[i::5]) for i in range(5)]
	L = A = L0 = A0 = 0.0
	for fo in folds:
		m = np.array([x not in fo for x in maps])
		wc = fit(X[m], y[m])
		l, acc = loss(wc, X[~m], y[~m])
		w0 = fit(X[m][:, :1], y[m], lo[:1])
		l0, acc0 = loss(w0, X[~m][:, :1], y[~m])
		L += l / 5; A += acc / 5; L0 += l0 / 5; A0 += acc0 / 5
	print(f'5-fold leave-maps-out: log loss {L:.4f} (side only {L0:.4f}), accuracy {A:.3f} (side only {A0:.3f})')


if __name__ == '__main__':
	main()
