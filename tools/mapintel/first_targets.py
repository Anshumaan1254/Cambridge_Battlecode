#!/usr/bin/env python3
"""Step 6 (MAPAnalysis.md 5.6), opening part: which groups the current-patch top teams capture first. LEARNED.

    python3 -I tools/mapintel/first_targets.py [--summaries experiments/results/mapintel/ladder_20261024] [--out .../first_targets]

Label: for each decoded game and team, the first n distinct groups it captured (n = its bodies). Features of a (map, team, group), all of
them available at draft time from the library (features.h / plans.h: so model_weights.h can score groups at run time): the walk from our
spawn dU and from theirs dE (BFS fields fc), their difference, the rank of dU among the reached groups, gems, gold, value, total camp
health, the kill-order damage sum S (plans.h GroupPrep), camp count, a monolith / golem flag, the contested flag of plans.h, and the share
of the group's value in the map's total. A pooled logistic regression on standardised features ranks the groups of each (game, team);
the score is the share of the true first-n among the n best ranked (the same measure as validate_ladder.py), on held-out maps
(the 5 archetype-stratified folds of maps/catalog/splits.json). Baselines: nearest by dU, compact plan 1 (validate_ladder.py's 0.53).
A small boosted forest on the raw features (GBM_*: 20 trees of depth 2: about 40 comparisons a group at run time) is compared the
same way; it is exported when it scores higher (Oct 24: logistic 0.653, forest 0.717, nearest 0.608 on held-out maps).
Writes report.md and weights.json (logistic: feature names, mean, std, coefficients; forest: baseline and trees) for model_weights.h."""
import argparse, glob, json, math, os, sys
from collections import defaultdict

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compact as CP  # noqa: E402
import economy as EC  # noqa: E402
import mapdata  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
GBM_DEPTH, GBM_TREES, GBM_LR = 2, 20, 0.3
FEATS = ["dU", "dE", "dU_minus_dE", "rank_dU", "gems", "gold", "value", "hp", "S", "ncamps", "heavy", "contested", "value_share", "log_dU"]


def group_table(M, team):
	"""Per group the feature vector (FEATS order) for one team, from compact.Compact (= plans.h): None for unreached groups."""
	C = CP.Compact(M, team)
	band, _ = C.contested()
	reach = [g for g in range(len(M.groups)) if C.dU[g] >= 0]
	order = sorted(reach, key=lambda g: (C.dU[g], g))
	rank = {g: k for k, g in enumerate(order)}
	total = sum(C.val[g] for g in reach) or 1.0
	out = {}
	for g in reach:
		grp = M.groups[g]
		adj, tot, S = C.prep[g]
		dE = C.dE[g] if C.dE[g] >= 0 else 999
		heavy = 1.0 if any(c[0] in (4, 5) for c in grp["camps"]) else 0.0
		out[g] = [C.dU[g], dE, C.dU[g] - dE, rank[g], grp["gems"], grp["gold"], C.val[g], tot, S, len(grp["camps"]), heavy,
				  1.0 if C.dE[g] >= 0 and abs(C.dU[g] - C.dE[g]) <= band else 0.0, C.val[g] / total, math.log1p(C.dU[g])]
	return out


def export_forest(m):
	"""The fitted forest as plain arrays: per tree its nodes (feature, threshold, left, right, leaf, value); score = baseline + sum of the
	leaf values reached (x[feature] <= threshold goes left: sklearn's rule for numeric features without missing values)."""
	trees = []
	for pred in m._predictors:
		nodes = pred[0].nodes
		trees.append([[int(n["feature_idx"]), float(n["num_threshold"]), int(n["left"]), int(n["right"]), int(n["is_leaf"]), float(n["value"])] for n in nodes])
	return {"baseline": float(np.ravel(m._baseline_prediction)[0]), "trees": trees}


def forest_score(F, X):
	"""The forest's raw score for each row (the C++ first_scores() does the same walk)."""
	out = np.full(len(X), F["baseline"])
	for i, x in enumerate(X):
		v = F["baseline"]
		for tree in F["trees"]:
			k = 0
			while not tree[k][4]:
				k = tree[k][2] if x[tree[k][0]] <= tree[k][1] else tree[k][3]
			v += tree[k][5]
		out[i] = v
	return out


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--summaries", default=os.path.join(ROOT, "experiments/results/mapintel/ladder_20261024"))
	ap.add_argument("--catalog", default=os.path.join(ROOT, "maps/catalog"))
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/first_targets"))
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)
	tables = {}
	samples = []  # (map, team, [groups], set(first_n))
	for f in sorted(glob.glob(os.path.join(a.summaries, "*.json"))):
		S = json.load(open(f))
		if not S.get("map") or S.get("error"):
			continue
		mp = S["map"]
		if mp not in tables:
			M = mapdata.load(mp)
			tables[mp] = [group_table(M, 0), group_table(M, 1)]
		fc = defaultdict(dict)
		for t, g, r in S["first_capture"]:
			fc[t][g] = r
		for t in (0, 1):
			n = len(S["drafts"][t]) + (1 if 3 in S["drafts"][t] else 0)
			first = [g for g, _ in sorted(fc[t].items(), key=lambda kv: (kv[1], kv[0]))][:n]
			if len(first) < n:
				continue
			samples.append((mp, t, n, set(first)))
	folds = json.load(open(os.path.join(a.catalog, "splits.json")))["folds"]

	def rows(sel):
		X, y = [], []
		for mp, t, n, first in sel:
			for g, x in tables[mp][t].items():
				X.append(x)
				y.append(1 if g in first else 0)
		return np.array(X, dtype=float), np.array(y)

	def score(model, mu, sd, sel, key=None):
		s = []
		for mp, t, n, first in sel:
			gs = list(tables[mp][t])
			X = (np.array([tables[mp][t][g] for g in gs], dtype=float) - mu) / sd
			if key is None:
				p = model.decision_function(X)
				top = [gs[i] for i in np.lexsort((np.array(gs), -p))[:n]]
			else:
				top = sorted(gs, key=lambda g: (tables[mp][t][g][key], g))[:n]
			s.append(len(set(top) & first) / n)
		return float(np.mean(s))

	res = {}
	for C in (0.01, 0.1, 1.0):
		sc, base = [], []
		for test in folds:
			tr = [x for x in samples if x[0] not in test]
			te = [x for x in samples if x[0] in test]
			X, y = rows(tr)
			mu, sd = X.mean(0), X.std(0)
			sd[sd == 0] = 1
			m = LogisticRegression(C=C, max_iter=3000).fit((X - mu) / sd, y)
			sc.append((score(m, mu, sd, te), len(te)))
			base.append((score(None, mu, sd, te, key=0), len(te)))
		res[C] = (sum(s * n for s, n in sc) / sum(n for _, n in sc), sum(s * n for s, n in base) / sum(n for _, n in base))
		print(f"C {C}: learned {res[C][0]:.3f}  nearest {res[C][1]:.3f}", flush=True)
	# the boosted forest, the same folds
	def gbm_fit(sel):
		X, y = rows(sel)
		return HistGradientBoostingClassifier(max_depth=GBM_DEPTH, learning_rate=GBM_LR, max_iter=GBM_TREES, early_stopping=False, random_state=0).fit(X, y)

	gsc = []
	for test in folds:
		tr = [x for x in samples if x[0] not in test]
		te = [x for x in samples if x[0] in test]
		gm = gbm_fit(tr)
		for mp, t, n, first in te:
			gs = list(tables[mp][t])
			p = forest_score(export_forest(gm), np.array([tables[mp][t][g] for g in gs], dtype=float))
			top = [gs[i] for i in np.lexsort((np.array(gs), -p))[:n]]
			gsc.append(len(set(top) & first) / n)
	gbm_share = float(np.mean(gsc))
	print(f"forest (depth {GBM_DEPTH}, {GBM_TREES} trees): {gbm_share:.3f}", flush=True)
	Cb = max(res, key=lambda c: res[c][0])
	X, y = rows(samples)
	mu, sd = X.mean(0), X.std(0)
	sd[sd == 0] = 1
	m = LogisticRegression(C=Cb, max_iter=3000).fit((X - mu) / sd, y)
	json.dump({"origin": "LEARNED (first-n captures of current-patch top-team games)", "features": FEATS, "mean": mu.round(6).tolist(),
			   "std": sd.round(6).tolist(), "coef": m.coef_[0].round(6).tolist(), "intercept": float(m.intercept_[0]), "C": Cb,
			   "cv_share": round(res[Cb][0], 4), "nearest_share": round(res[Cb][1], 4), "samples": len(samples),
			   "forest": dict(export_forest(gbm_fit(samples)), cv_share=round(gbm_share, 4), depth=GBM_DEPTH, n_trees=GBM_TREES, lr=GBM_LR),
			   "use": "forest" if gbm_share > res[Cb][0] else "logistic"},
			  open(os.path.join(a.out, "weights.json"), "w"), indent=1)
	L = ["# First targets: which groups the top teams capture first (leave-maps-out)\n",
		 f"{len(samples)} team-games on {len(tables)} maps. Share of the true first-n groups among the n best ranked, on held-out maps:\n",
		 "| ranking | share |", "|---|---|", f"| nearest by walk (dU) | {res[Cb][1]:.3f} |", "| compact plan 1 (validate_ladder.py, in-sample maps) | 0.532 |"]
	for C, (s, b) in sorted(res.items()):
		L.append(f"| learned logistic, C = {C} | {s:.3f} |")
	L.append(f"| boosted forest, depth {GBM_DEPTH}, {GBM_TREES} trees, learning rate {GBM_LR} | {gbm_share:.3f} |")
	L += ["", f"Chosen C = {Cb}; coefficients on standardised features (positive = captured earlier):"]
	for f_, c in sorted(zip(FEATS, m.coef_[0]), key=lambda t: -abs(t[1])):
		L.append(f"- {f_}: {c:+.3f}")
	open(os.path.join(a.out, "report.md"), "w").write("\n".join(L) + "\n")
	print("\n".join(L))


if __name__ == "__main__":
	main()
