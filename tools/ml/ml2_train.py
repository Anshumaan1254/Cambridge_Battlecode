#!/usr/bin/env python3
"""Fit and compare fight / danger models on the contact dataset (agent ml2, session 13).

usage: python3 -I tools/ml/ml2_train.py DATA.npz [--label die8] [--skip contest] [--export OUT.h] [--feats a,b,...]

Cross-validation keeps games whole (GroupKFold, 5 folds). Reports, for every model, the AUC, Brier score and log loss over
all held-out rows and over our bot's bodies only (the rows the bot would use the model on), a reliability table, the
bot's own estimate (log_adv) as a baseline, and standardized logistic coefficients. --export writes the final logistic
model (fit on all rows) as constexpr arrays for the bot (raw-feature weights: the standardization is folded in).
"""
import json
import math
import sys

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.tree import DecisionTreeClassifier


def load(path, skip):
	d = np.load(path)
	X, Y, M = d['X'], d['Y'], d['M']
	F = list(d['features'])
	L = list(d['labels'])
	G = json.loads(str(d['games']))
	keep = np.array([G[g]['map'] not in skip and not G[g].get('dup') for g in M[:, 0]])
	return X[keep], Y[keep], M[keep], F, L, G


def cv_predict(make, X, y, groups, folds=5):
	p = np.zeros(len(y))
	for tr, te in GroupKFold(n_splits=folds).split(X, y, groups):
		m = make()
		m.fit(X[tr], y[tr])
		p[te] = m.predict_proba(X[te])[:, 1]
	return p


def report(name, y, p, us):
	out = [name]
	for sel, tag in ((np.ones(len(y), bool), 'all'), (us, 'us')):
		if sel.sum() == 0 or y[sel].min() == y[sel].max():
			continue
		pp = np.clip(p[sel], 1e-4, 1 - 1e-4)
		out.append(f'{tag}: auc {roc_auc_score(y[sel], pp):.3f} brier {brier_score_loss(y[sel], pp):.4f} ll {log_loss(y[sel], pp):.4f}')
	print('  '.join(out))


def reliability(y, p, bins=(0, .02, .05, .1, .2, .3, .5, 1.01)):
	rows = []
	for a, b in zip(bins[:-1], bins[1:]):
		s = (p >= a) & (p < b)
		if s.sum():
			rows.append(f'[{a:.2f},{b:.2f}) n={s.sum():6d} pred {p[s].mean():.3f} real {y[s].mean():.3f}')
	return rows


class Std:
	def __init__(self, X):
		self.mu = X.mean(0)
		self.sd = X.std(0) + 1e-6

	def __call__(self, X):
		return (X - self.mu) / self.sd


def main():
	a = sys.argv[1:]
	label, skip, export, feats = 'die8', [], None, None
	only_lr = '--only-lr' in a
	if only_lr:
		a.remove('--only-lr')
	for k in ('--label', '--skip', '--export', '--feats'):
		if k in a:
			i = a.index(k)
			v = a[i + 1]
			del a[i:i + 2]
			if k == '--label':
				label = v
			elif k == '--skip':
				skip = v.split(',')
			elif k == '--export':
				export = v
			else:
				feats = v.split(',')
	X, Y, M, F, L, G = load(a[0], skip)
	y = Y[:, L.index(label)]
	if label in ('net3', 'taken3', 'dealt3'):
		sys.exit('regression labels: use ml2_reg.py')
	cens = Y[:, L.index('censored')] > 0
	X, Y, M, y = X[~cens], Y[~cens], M[~cens], y[~cens]
	us = M[:, 3] == 1
	groups = M[:, 0]
	cols = [F.index(f) for f in (feats or F)]
	names = [F[c] for c in cols]
	Xf = X[:, cols]
	Xu = np.hstack([Xf, us[:, None].astype(np.float32)])
	print(f'label {label}: rows {len(y)} (us {us.sum()}), positives {y.mean():.3f} (us {y[us].mean():.3f}, them {y[~us].mean():.3f}), games {len(set(groups))}')
	ia = F.index('log_adv')
	report('bot log_adv (minus)', y, -X[:, ia], us)

	def lr(C=1.0):
		class M_:
			def fit(s, X_, y_):
				s.st = Std(X_)
				s.m = LogisticRegression(C=C, max_iter=2000)
				s.m.fit(s.st(X_), y_)
				return s

			def predict_proba(s, X_):
				return s.m.predict_proba(s.st(X_))
		return M_()

	p_lr = cv_predict(lambda: lr(1.0), Xf, y, groups)
	report('logistic', y, p_lr, us)
	p_lru = cv_predict(lambda: lr(1.0), Xu, y, groups)
	report('logistic + us flag', y, p_lru, us)
	if only_lr:
		p_gb = p_lru
	else:
		p_tree = cv_predict(lambda: DecisionTreeClassifier(max_depth=5, min_samples_leaf=200), Xu, y, groups)
		report('tree depth 5 + us', y, p_tree, us)
		p_gb = cv_predict(lambda: HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=100), Xu, y, groups)
		report('boosted trees + us', y, p_gb, us)
	# our bodies only
	if us.sum() > 1000 and not only_lr:
		gu = groups[us]
		p_only = cv_predict(lambda: lr(1.0), Xf[us], y[us], gu)
		pp = np.clip(p_only, 1e-4, 1 - 1e-4)
		print(f'logistic on our bodies only: us auc {roc_auc_score(y[us], pp):.3f} brier {brier_score_loss(y[us], pp):.4f} ll {log_loss(y[us], pp):.4f}')
	print('reliability, logistic + us, our bodies:')
	for r in reliability(y[us], p_lru[us]):
		print('  ' + r)
	print('reliability, boosted, our bodies:')
	for r in reliability(y[us], p_gb[us]):
		print('  ' + r)
	# final logistic on all rows: standardized coefficients
	m = lr(1.0).fit(Xu, y)
	coef = m.m.coef_[0]
	order = np.argsort(-np.abs(coef))
	print('standardized coefficients (logistic + us):')
	for i in order:
		nm = names[i] if i < len(names) else 'us'
		print(f'  {nm:14s} {coef[i]:+.3f}')
	np.save(a[0].replace('.npz', f'_p_{label}{"_lr" if only_lr else ""}.npy'), np.vstack([p_lru, p_gb, y, us, groups]))
	if export:
		w = coef / m.st.sd
		b = m.m.intercept_[0] - float((coef * m.st.mu / m.st.sd).sum())
		full = np.zeros(len(F))
		for j, c in enumerate(cols):
			full[c] = w[j]
		with open(export, 'w') as fo:
			fo.write(f'// generated by tools/ml/ml2_train.py ({label}, {len(y)} rows, {len(set(groups))} games, skip {skip}); weights on raw features\n')
			fo.write(f'// (dataset order, 0 = not in the model): ' + ', '.join(F) + '\n')
			fo.write(f'constexpr float ML2_B_{label.upper()} = {b + w[-1]:.6f}f; // bias, includes the us = 1 term\n')
			fo.write(f'constexpr float ML2_W_{label.upper()}[{len(F)}] = {{ ' + ', '.join(f'{x:.6e}f' for x in full) + ' };\n')
		print('exported', export)


if __name__ == '__main__':
	main()
