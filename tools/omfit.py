#!/usr/bin/env python3
"""tools/omfit.py [--train FILE] [--test FILE] [--lambda L] [--export bots/god/src/om_model.h] [--classes none,invader,...] [--merge a:b,...]

Fits the opponent model's window classifier from labelled traces (tools/omtrace.py) and reports how well it separates the styles.
- Features: the per-window signals the leader logs (OPP_TRACE), scaled as in OppModel::features(), then exponentially smoothed over the
  game's windows with forgetting L (the bot does the same, so the fitted weights apply to exactly what it computes).
- Model: multinomial logistic regression (sklearn), class-balanced, L2. 'farmer' is merged into 'none' (indistinguishable from GOD itself
  in every signal: docs/CHANGES.md F1).
- Report: per-window confusion matrix on the held-out maps (rounds >= om_start), per-class recall / precision.
- --export writes the weights as a C++ header (om_model.h) for OppModel.
"""
import json, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATS = ['inv_b', 'invs', 'ad', 'ed', 'multi', 'pack', 'vis', 'banks', 'gems', 'lump', 'ward_home', 'ward_altar', 'ward_bush', 'altar', 'bush', 'unseen', 'heavy']


def feat(w):
	# Must match OppModel::features() in opponent.cpp.
	B = max(1, w.get('bodies', 6))
	return [w['inv'] / B, w['invs'] / 20.0, w['ad'], w['ed'], w['multi'], w['pack'] / 3.0, w['vis'] / 3.0, w['banks'], w['gems'] / 50.0, w['lump'] / 100.0,
			w['ward_home'], w['ward_altar'], w['ward_bush'], w['altar'] / 5.0, w['bush'], w['unseen'], w['heavy']]


def games(path):
	g = {}
	for l in open(path):
		r = json.loads(l)
		if r.get('game'):
			continue
		g.setdefault((r['map'], r['side'], r['opp'], r['bot']), []).append(r)
	for k in g:
		g[k].sort(key=lambda r: r['round'])
	return g


def smoothed(G, lam, start, merge):
	X, y, meta = [], [], []
	for k, ws in G.items():
		s = None
		for w in ws:
			f = np.array(feat(w), dtype=float)
			s = f if s is None else lam * s + (1 - lam) * f
			if w['round'] < start:
				continue
			lab = merge.get(w['label'], w['label'])
			X.append(s.copy()), y.append(lab), meta.append((k, w['round']))
	return np.array(X), np.array(y), meta


def main():
	a = sys.argv[1:]
	opt = lambda k, d: (a.pop(a.index(k) + 1), a.remove(k))[0] if k in a else d
	train = opt('--train', os.path.join(ROOT, 'experiments/results/om/traces_train_v1.jsonl'))
	test = opt('--test', os.path.join(ROOT, 'experiments/results/om/traces_test_v1.jsonl'))
	lam = float(opt('--lambda', '0.6'))
	start = int(opt('--start', '100'))
	export = opt('--export', None)
	classes = opt('--classes', 'none,invader,deathball,objective,ambush,altar').split(',')
	merge = {'farmer': 'none'}
	for kv in opt('--merge', '').split(','):
		if ':' in kv:
			merge[kv.split(':')[0]] = kv.split(':')[1]
	from sklearn.linear_model import LogisticRegression
	Xtr, ytr, _ = smoothed(games(train), lam, start, merge)
	keep = np.isin(ytr, classes)
	Xtr, ytr = Xtr[keep], ytr[keep]
	mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
	clf = LogisticRegression(max_iter=2000, C=1.0, class_weight='balanced')
	clf.fit((Xtr - mu) / sd, ytr)
	print(f'train windows {len(ytr)}  classes {list(clf.classes_)}  lambda {lam}')
	for name, path in (('train', train), ('test', test)):
		if not os.path.exists(path):
			continue
		X, y, _ = smoothed(games(path), lam, start, merge)
		keep = np.isin(y, classes)
		X, y = X[keep], y[keep]
		p = clf.predict((X - mu) / sd)
		cl = list(clf.classes_)
		M = np.zeros((len(cl), len(cl)), dtype=int)
		for t, q in zip(y, p):
			M[cl.index(t), cl.index(q)] += 1
		print(f'\n{name}: {len(y)} windows, accuracy {np.mean(p == y):.3f}')
		print('true \\ pred  ' + ' '.join(c[:9].rjust(9) for c in cl) + '   recall')
		for i, c in enumerate(cl):
			print(c[:11].ljust(12) + ' '.join(str(v).rjust(9) for v in M[i]) + f'   {M[i, i] / max(1, M[i].sum()):.2f}')
		print('precision   ' + ' '.join(f'{M[i, i] / max(1, M[:, i].sum()):9.2f}' for i in range(len(cl))))
	if export:
		W = clf.coef_ / sd  # fold the standardisation into the weights: logit = W . f + b
		b = clf.intercept_ - (clf.coef_ * (mu / sd)).sum(1)
		with open(export, 'w') as f:
			f.write('// Opponent-model window classifier (P.opp_model): multinomial logistic regression fitted by tools/omfit.py on labelled\n')
			f.write(f'// sparring traces ({os.path.basename(train)}, forgetting {lam}); logit_k = W[k] . features + B[k], features as OppModel::features().\n')
			f.write('#pragma once\n\n')
			f.write(f'constexpr int OM_NF = {len(FEATS)};\nconstexpr int OM_NC = {len(clf.classes_)};\nconstexpr int OM_NROW = {W.shape[0]}; // 1 = binary: the row is the logit of the second class against the first\n')
			f.write('// classes, in order: ' + ', '.join(clf.classes_) + '\n')
			f.write('constexpr int OM_CLASS_ARC[OM_NC] = { ' + ', '.join({'none': '0', 'farmer': '1', 'invader': '2', 'raider': '2', 'deathball': '3', 'objective': '4', 'altar': '5', 'ambush': '6'}[c] for c in clf.classes_) + ' };\n')
			f.write('constexpr float OM_W[OM_NROW][OM_NF] = {\n')
			for row in W:
				f.write('\t{ ' + ', '.join(f'{v:.6e}f' for v in row) + ' },\n')
			f.write('};\nconstexpr float OM_B[OM_NROW] = { ' + ', '.join(f'{v:.6e}f' for v in b) + ' };\n')
		print('\nexported', export)


if __name__ == '__main__':
	main()
