#!/usr/bin/env python3
"""Retrain the fight / danger model on the patch-3.0 Nyx games and compare it with the shipped one (ml4, session 14).

usage: python3 -I tools/ml/ml4_train.py DATA.npz [DATA2.npz ...] [--label die8] [--header bots/_x_g5/src/ml2_model.h]
           [--nyx nyx_new,nyx_old,losses_oct20] [--weights 1,4,10] [--C 1.0] [--export OUT.h] [--export-cfg old+nyx:4+p3]
           [--skip MAP,...] [--drop bush4]
--nyx names the patch-3.0 sets (the evaluation games: the Nyx games and the Oct 20 ladder losses); 'nyx' below means them.

DATA.npz comes from tools/ml/ml2_dataset.py (every set: the old Oct 18-19 games and the Nyx sets). The evaluation rows are
the Nyx games' contact rows, held out by game (5 folds over the 20 Nyx games; the old games, when used, are always in the
training fold). Reported for our bodies (us = 1) and the enemy's bodies: AUC, Brier, log loss, and the death rate of the
rows the bot's rule would flag (P >= 0.3 / 0.4). Models: the header's weights (the shipped model), 'old' (fit on the old
games only: the shipped model's recipe on the re-decoded data), 'nyx' (the Nyx games only), 'old+nyx:W' (all games, the
Nyx rows weighted W), 'oldthem+nyx:W' (the old games' rows of the other teams' bodies only, plus the Nyx rows weighted W).
--export writes the chosen configuration (fit on every game) as the logistic part of ml2_model.h (die8 and kill8); the
boosted-tree arrays are copied from --header so the bot still compiles (it uses the logistic weights by default).
"""
import json
import os
import re
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ml2_train import Std, load  # noqa: E402


def load_many(paths, skip):
	"""Several ml2_dataset.py files (e.g. the old sets and the Nyx sets) as one dataset; game ids are offset."""
	Xs, Ys, Ms, Gs, F, L = [], [], [], [], None, None
	for path in paths:
		X, Y, M, F, L, G = load(path, skip)
		M = M.copy()
		M[:, 0] += len(Gs)
		Xs.append(X); Ys.append(Y); Ms.append(M); Gs += G
	return np.vstack(Xs), np.vstack(Ys), np.vstack(Ms), F, L, Gs


def read_header(path, label):
	s = open(path).read()
	w = re.search(r'ML2_W_%s\[(\d+)\] = \{([^}]*)\}' % label.upper(), s)
	b = re.search(r'ML2_B_%s = ([-0-9.e+]+)f' % label.upper(), s)
	W = np.array([float(x.strip().rstrip('f')) for x in w.group(2).split(',')])
	assert len(W) == int(w.group(1))
	return W, float(b.group(1))


def sig(z):
	return 1 / (1 + np.exp(-np.clip(z, -30, 30)))


class LR:
	def __init__(self, C=1.0):
		self.C = C

	def fit(self, X, y, sw=None):
		self.st = Std(X)
		self.m = LogisticRegression(C=self.C, max_iter=3000)
		self.m.fit(self.st(X), y, sample_weight=sw)
		return self

	def predict_proba(self, X):
		return self.m.predict_proba(self.st(X))[:, 1]

	def raw(self):
		"""Weights on the raw features and the bias (standardization folded in)."""
		coef = self.m.coef_[0]
		w = coef / self.st.sd
		b = self.m.intercept_[0] - float((coef * self.st.mu / self.st.sd).sum())
		return w, b


def metrics(y, p):
	if y.min() == y.max():
		return 'n/a'
	pp = np.clip(p, 1e-4, 1 - 1e-4)
	f3 = p >= 0.3
	f4 = p >= 0.4
	return (f'auc {roc_auc_score(y, pp):.3f} brier {brier_score_loss(y, pp):.4f} ll {log_loss(y, pp):.4f} | '
			f'P>=.3: {f3.mean() * 100:4.1f}% rows die {y[f3].mean() * 100 if f3.any() else 0:4.1f}% | '
			f'P>=.4: {f4.mean() * 100:4.1f}% rows die {y[f4].mean() * 100 if f4.any() else 0:4.1f}%')


def reliability(y, p, bins=(0, .05, .1, .2, .3, .4, .5, .7, 1.01)):
	out = []
	for a, b in zip(bins[:-1], bins[1:]):
		s = (p >= a) & (p < b)
		if s.sum():
			out.append(f'[{a:.2f},{b:.2f}) n={s.sum():6d} pred {p[s].mean():.3f} real {y[s].mean():.3f}')
	return out


def main():
	a = sys.argv[1:]
	opt = dict(label='die8', header=os.path.join(HERE, '..', '..', 'bots', '_x_g5', 'src', 'ml2_model.h'), nyx='nyx_new,nyx_old',
			   weights='1,4,10', C='1.0', export=None, export_cfg='old+nyx:4', skip='', drop='bush4')
	for k in list(opt):
		if '--' + k.replace('_', '-') in a:
			i = a.index('--' + k.replace('_', '-')); opt[k] = a[i + 1]; del a[i:i + 2]
	X, Y, M, F, L, G = load_many(a, opt['skip'].split(',') if opt['skip'] else [])
	label = opt['label']
	y = Y[:, L.index(label)]
	cens = Y[:, L.index('censored')] > 0
	X, Y, M, y = X[~cens], Y[~cens], M[~cens], y[~cens]
	us = M[:, 3] == 1
	groups = M[:, 0]
	nyx_sets = set(opt['nyx'].split(','))
	nyx = np.array([G[g]['set'] in nyx_sets for g in groups])
	# features the bot does not compute (bush4: f[18] stays 0 in Brain::ml2_features) are left out of the fit and exported as 0
	drop = [f for f in opt['drop'].split(',') if f]
	cols = [i for i, f in enumerate(F) if f not in drop]
	Xc = X[:, cols]
	Xu = np.hstack([Xc, us[:, None].astype(np.float32)])
	Xp = np.hstack([Xu, nyx[:, None].astype(np.float32)])  # + a patch-3.0 indicator (the model runs on patch 3.0 only: folded into the bias)
	C = float(opt['C'])
	print(f'label {label}: rows {len(y)}, games {len(set(groups))}; nyx rows {nyx.sum()} (us {(nyx & us).sum()}, them {(nyx & ~us).sum()}), '
		  f'games {len(set(groups[nyx]))}; old rows {(~nyx).sum()} (us {(~nyx & us).sum()}), games {len(set(groups[~nyx]))}')
	print(f'positives: nyx us {y[nyx & us].mean():.3f} them {y[nyx & ~us].mean():.3f}; old us {y[~nyx & us].mean() if (~nyx & us).any() else float("nan"):.3f} '
		  f'them {y[~nyx & ~us].mean() if (~nyx & ~us).any() else float("nan"):.3f}')
	results = {}
	# the shipped model
	if opt['header'] and os.path.exists(opt['header']):
		W, B = read_header(opt['header'], label)
		p = sig(X @ W + B)
		results['header (shipped)'] = p
	# folds over the nyx games
	nyx_ids = sorted(set(groups[nyx]))
	fold_of = {}
	gkf = GroupKFold(n_splits=min(5, len(nyx_ids)))
	for k, (tr, te) in enumerate(gkf.split(np.zeros(len(nyx_ids)), groups=nyx_ids)):
		for i in te:
			fold_of[nyx_ids[i]] = k
	fold = np.array([fold_of.get(g, -1) for g in groups])
	nf = max(fold) + 1

	def cv(train_mask_fn, weight_fn, name, XX=Xu):
		p = np.full(len(y), np.nan)
		for k in range(nf):
			te = nyx & (fold == k)
			tr = train_mask_fn(k)
			sw = weight_fn(tr)
			m = LR(C).fit(XX[tr], y[tr], sw)
			p[te] = m.predict_proba(XX[te])
		results[name] = p
		return p

	old = ~nyx
	if old.any():
		p = np.full(len(y), np.nan)
		m = LR(C).fit(Xu[old], y[old])
		p[nyx] = m.predict_proba(Xu[nyx])
		results['old only'] = p
	cv(lambda k: nyx & (fold != k), lambda tr: None, 'nyx only')
	if old.any():
		for w in [float(x) for x in opt['weights'].split(',')]:
			cv(lambda k: old | (nyx & (fold != k)), lambda tr: np.where(nyx[tr], w, 1.0), f'old+nyx:{w:g}')
			cv(lambda k: old | (nyx & (fold != k)), lambda tr: np.where(nyx[tr], w, 1.0), f'old+nyx:{w:g}+p3', Xp)
			cv(lambda k: (old & ~us) | (nyx & (fold != k)), lambda tr: np.where(nyx[tr], w, 1.0), f'oldthem+nyx:{w:g}')
	print(f'\nheld-out rows of the patch-3.0 games ({label}); our bodies (us = 1) / their bodies:')
	for name, p in results.items():
		for sel, tag in ((nyx & us, 'us  '), (nyx & ~us, 'them')):
			print(f'  {name:18s} {tag} n={sel.sum():6d}  {metrics(y[sel], p[sel])}')
	setname = np.array([G[g]['set'] for g in groups])
	if len(nyx_sets) > 1:
		print('\nthe same per set, our bodies (AUC / Brier):')
		for name, p in results.items():
			cells = []
			for sn in sorted(nyx_sets):
				sel = nyx & us & (setname == sn)
				if sel.sum() and y[sel].min() != y[sel].max():
					pp = np.clip(p[sel], 1e-4, 1 - 1e-4)
					cells.append(f'{sn} n={sel.sum()} auc {roc_auc_score(y[sel], pp):.3f} brier {brier_score_loss(y[sel], pp):.4f}')
			print(f'  {name:18s} ' + ' | '.join(cells))
	# per fold (4 games each): the AUC on our bodies of every model next to the shipped model's, to see whether a gain is consistent
	if 'header (shipped)' in results:
		print('\nAUC on our bodies per fold (vs the shipped model):')
		ph = results['header (shipped)']
		for name, p in results.items():
			cells, wins = [], 0
			for k in range(nf):
				sel = nyx & us & (fold == k)
				if sel.sum() < 50 or y[sel].min() == y[sel].max():
					cells.append('   -  '); continue
				a1 = roc_auc_score(y[sel], p[sel]); a0 = roc_auc_score(y[sel], ph[sel])
				wins += a1 > a0
				cells.append(f'{a1:.3f}{"+" if a1 > a0 else "-"}')
			print(f'  {name:18s} ' + ' '.join(cells) + f'  better in {wins}/{nf} folds')
	# the bot's rule thresholds P: share of our Nyx rows flagged and their death rate, per threshold (a calibration shift is
	# equivalent to a threshold shift on the shipped model: compare the rows along a column)
	print('\nour Nyx rows flagged (% of rows / die8 % of the flagged) at P >= T:')
	print('  ' + ' ' * 18 + ' '.join(f'   T={t:.2f}    ' for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8)))
	for name, p in results.items():
		sel = nyx & us
		cells = []
		for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
			f = sel & (p >= t)
			cells.append(f'{f.sum() / sel.sum() * 100:5.1f}% {y[f].mean() * 100 if f.any() else 0:4.0f}%')
		print(f'  {name:18s} ' + ' '.join(cells))
	# paired bootstrap over the Nyx games of the AUC difference (our bodies) vs the shipped model
	if 'header (shipped)' in results:
		print('\npaired bootstrap over the Nyx games (1000 resamples), AUC on our bodies minus the shipped model\'s:')
		rs = np.random.RandomState(1)
		gids = np.array(nyx_ids)
		rows_of = {g: np.flatnonzero(nyx & us & (groups == g)) for g in gids}
		ph = results['header (shipped)']
		draws = [rs.choice(len(gids), len(gids), replace=True) for _ in range(1000)]
		for name, p in results.items():
			if name == 'header (shipped)':
				continue
			diffs = []
			for dr in draws:
				idx = np.concatenate([rows_of[gids[i]] for i in dr])
				if y[idx].min() == y[idx].max():
					continue
				diffs.append(roc_auc_score(y[idx], p[idx]) - roc_auc_score(y[idx], ph[idx]))
			diffs = np.array(diffs)
			print(f'  {name:18s} mean {diffs.mean():+.4f}  95% [{np.percentile(diffs, 2.5):+.4f}, {np.percentile(diffs, 97.5):+.4f}]  P(>0) {np.mean(diffs > 0):.2f}')
	for name in ('header (shipped)', 'nyx only') + tuple(k for k in results if k.startswith('old+nyx')):
		if name in results:
			print(f'reliability on our Nyx rows, {name}:')
			for r in reliability(y[nyx & us], results[name][nyx & us]):
				print('   ' + r)
	if opt['export']:
		cfg = opt['export_cfg']
		p3 = cfg.endswith('+p3')
		XX = Xp if p3 else Xu
		if cfg == 'nyx':
			tr, sw = nyx, None
		else:
			kind, w = cfg.replace('+p3', '').split(':')
			w = float(w)
			tr = (old & ~us) | nyx if kind == 'oldthem+nyx' else old | nyx
			sw = np.where(nyx[tr], w, 1.0)
		hdr = open(opt['header']).read()
		out = ['// ml2 fight / danger model: logistic weights on the raw features of tools/ml/ml2_dataset.py (agent ml2, session 13),',
			   f'// retrained by tools/ml/ml4_train.py (ml4, session 14) on the patch-3.0 Nyx games ({cfg}; us = 1 folded into the bias).',
			   '#pragma once', f'constexpr int ML2_NF = {len(F)};']
		for lab in ('die8', 'kill8'):
			yy = Y[:, L.index(lab)]
			m = LR(C).fit(XX[tr], yy[tr], sw)
			w_raw, b_raw = m.raw()
			nc = len(cols)
			bias = b_raw + w_raw[nc] + (w_raw[nc + 1] if p3 else 0.0)
			full = np.zeros(len(F))
			full[cols] = w_raw[:nc]
			games = len(set(groups[tr]))
			out.append(f'// generated by tools/ml/ml4_train.py ({lab}, {tr.sum()} rows, {games} games, {cfg}, not in the model: {drop}); weights on raw features')
			out.append('// (dataset order, 0 = not in the model): ' + ', '.join(F))
			out.append(f'constexpr float ML2_B_{lab.upper()} = {bias:.6f}f; // bias, includes the us = 1 term' + (' and the patch-3.0 term' if p3 else ''))
			out.append(f'constexpr float ML2_W_{lab.upper()}[{len(F)}] = {{ ' + ', '.join(f'{x:.6e}f' for x in full) + ' };')
			# self-check: the raw weights reproduce predict_proba on Nyx rows (patch flag 1)
			idx = np.random.RandomState(0).choice(np.flatnonzero(nyx), 500, replace=False)
			pa = m.predict_proba(XX[idx])
			pb = sig(X[idx] @ full + bias - w_raw[nc] * (1 - us[idx]))
			print(f'export {lab}: max |raw - sklearn| {np.abs(pa - pb).max():.2e}')
		gb = hdr[hdr.index('// generated by tools/ml/ml2_train.py --export-gb'):]
		open(opt['export'], 'w').write('\n'.join(out) + '\n' + gb)
		print('exported', opt['export'])


if __name__ == '__main__':
	main()
