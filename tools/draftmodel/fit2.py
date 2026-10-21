#!/usr/bin/env python3
"""tools/draftmodel/fit2.py GAMES.jsonl PROBE.txt MAPFEAT.json [--l2 X] [--no-counter] [--export]

The draft-value model with counter terms. logit P(win) = side + w . (F(ours) - F(theirs)) + sum_k c_k (I_k(ours, theirs) - I_k(theirs, ours)),
F = the sum of the picks' features (feats.py, map interactions included), I_k(A, B) = (sum over A of feature x_k) x (sum over B of feature
y_k): our range against their melee basic damage, our stuns against their melee basic damage, our health against their burst (spell +
area damage), our dashes against their range. Base stat weights >= 0, interactions and counters free. Prints the weights and the
5-fold leave-maps-out log loss / accuracy (with and without the counters); --export prints the params.h lines."""
import json, sys
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import feats as FT

COUNTERS = [('ranged', 'melee_basic'), ('stun', 'melee_basic'), ('hp', 'burst'), ('dash', 'ranged')]
CNAMES = ['cw_ranged_melee', 'cw_stun_melee', 'cw_hp_burst', 'cw_dash_ranged']


def aggs(ch, names):
	a = {'melee_basic': 0.0, 'burst': 0.0, 'ranged': 0.0}
	t = {k: 0.0 for k in ('ranged', 'stun', 'hp', 'dash')}
	for n in names:
		f = FT.pick(ch, n)
		melee_share = (f['bodies'] - f['ranged']) / f['bodies']
		a['melee_basic'] += f['basic'] * melee_share
		a['burst'] += f['spell'] + f['area']
		a['ranged'] += f['ranged']
		for k in t:
			t[k] += f[k]
	return a, t


def main():
	a = sys.argv[1:]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	l2 = float(opt('--l2', '1'))
	counter = '--no-counter' not in a
	games = [json.loads(l) for l in open(a[0])]
	ch = FT.parse(a[1])
	mfs = json.load(open(a[2]))
	use = [x for x in FT.FEATS if x not in opt('--drop', '').split(',')]
	X, y, maps = [], [], []
	for g in games:
		mf = mfs.get(g['map'])
		if mf is None:
			continue
		fo, ft = FT.team(ch, g['ours'], mf), FT.team(ch, g['theirs'], mf)
		row = [1.0 if g['side'] == 'A' else -1.0] + [fo[k] - ft[k] for k in use]
		if counter:
			ao, to = aggs(ch, g['ours'])
			at, tt = aggs(ch, g['theirs'])
			for (x, yk) in COUNTERS:
				row.append(to[x] * at[yk] - tt[x] * ao[yk])
		X.append(row)
		y.append(1.0 if g['win'] else 0.0)
		maps.append(g['map'])
	X, y = np.array(X), np.array(y)
	names = ['side'] + use + (CNAMES if counter else [])
	free = set(['side', 'bodies'] + FT.INTER + CNAMES)
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
	um = sorted(set(maps))
	rng = np.random.default_rng(1)
	rng.shuffle(um)
	folds = [set(um[i::5]) for i in range(5)]
	L = A = 0.0
	for fo in folds:
		m = np.array([x not in fo for x in maps])
		wc = fit(X[m], y[m])
		l, acc = loss(wc, X[~m], y[~m])
		L += l / 5
		A += acc / 5
	print(f'5-fold leave-maps-out: log loss {L:.4f}, accuracy {A:.3f}')
	if '--export' in a:
		pn = {'hp': 'pd_w_hp', 'basic': 'pd_w_basic', 'splash': 'pd_w_splash', 'spell': 'pd_w_spell', 'area': 'pd_w_area', 'stun': 'pd_w_stun',
			'dash': 'pd_w_dash', 'ranged': 'pd_w_ranged', 'gold': 'pd_w_gold', 'ret': 'pd_w_ret', 'bodies': 'pd_w_bodies', 'area_x_pack': 'pd_w_area_pack',
			'stun_x_elk': 'pd_w_stun_elk', 'gold_x_gold': 'pd_w_gold_gold', 'bodies_x_small': 'pd_w_bodies_small', 'dash_x_dist': 'pd_w_dash_dist',
			'ranged_x_mono': 'pd_w_ranged_mono', 'hp_x_mono': 'pd_w_hp_mono', 'basic_x_mono': 'pd_w_basic_mono', 'spell_x_mono': 'pd_w_spell_mono',
			'area_x_mono': 'pd_w_area_mono', 'cw_ranged_melee': 'pd_cw_ranged_melee', 'cw_stun_melee': 'pd_cw_stun_melee', 'cw_hp_burst': 'pd_cw_hp_burst',
			'cw_dash_ranged': 'pd_cw_dash_ranged'}
		print(' '.join(f'{pn[k]}={v:.4f}f' for k, v in zip(names, w) if k in pn))


if __name__ == '__main__':
	main()
