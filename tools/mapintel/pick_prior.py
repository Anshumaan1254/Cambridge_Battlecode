#!/usr/bin/env python3
"""The strong teams' pick prior as the default draft signal (the user's change 4 of Oct 24). LEARNED.

    python3 -I tools/mapintel/pick_prior.py [--out experiments/results/mapintel/draft_model/pick_prior.json]

Known maps: the table (known_maps.h `pick_strong`) holds each map's own rates (maps/catalog/draft_prior.json: the share of the top-20
teams' team-sides on that map that drafted the champion, current-patch ranked games). Unknown maps: a model of those rates from the
19 runtime z-features (model_weights.h zfeat()), per champion either the pooled rate (a constant) or a ridge over z, whichever has
the lower squared error on held-out maps (5 archetype-stratified folds; maps weighted by their strong team-sides); the ridge's alpha by
inner folds. Also the first-pick share (round 1 of the draft) the same way. model_weights.h pick_prior(z, rate, first) evaluates it:
v = intercept + coef . z (index order), clamped to [0, 1] (p4model's pattern). Writes the json and report.md next to it."""
import argparse, json, math, os, sys

import numpy as np
from sklearn.linear_model import Ridge

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_headers as EH  # noqa: E402
import features as FT  # noqa: E402
import mapdata  # noqa: E402
from engine import PICK_NAMES  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ALPHAS = [1, 3, 10, 30, 100, 300, 1e3, 1e4]


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/draft_model/pick_prior.json"))
	a = ap.parse_args()
	prior = json.load(open(os.path.join(ROOT, "maps/catalog/draft_prior.json")))
	arche = json.load(open(os.path.join(ROOT, "maps/catalog/archetypes.json")))
	folds = json.load(open(os.path.join(ROOT, "maps/catalog/splits.json")))["folds"]
	fold_of = {n: k for k, f in enumerate(folds) for n in f}
	maps = [m for m in mapdata.official_names() if prior["maps"].get(m, {}).get("strong_team_sides", 0) > 0]
	Z = np.array([EH.zfeat_py(FT.compute(mapdata.load(m), 0), arche) for m in maps])
	W = np.array([prior["maps"][m]["strong_team_sides"] for m in maps], float)
	targets = {}
	for c in range(12):
		ch = [x for x in prior["maps"][maps[0]]["champions"] if x["champion"] == PICK_NAMES[c]]
		assert ch, PICK_NAMES[c]
		rate = np.array([next(x for x in prior["maps"][m]["champions"] if x["champion"] == PICK_NAMES[c])["pick_rate_strong"] for m in maps])
		first = []
		for m in maps:
			x = next(x for x in prior["maps"][m]["champions"] if x["champion"] == PICK_NAMES[c])
			first.append(x["by_round"][0] / max(1, prior["maps"][m]["team_sides"]))
		targets[("rate", c)] = rate
		targets[("first", c)] = np.array(first)
	fold = np.array([fold_of[m] for m in maps])

	def cv_err(y, alpha):
		"""Held-out weighted squared error of the constant (alpha None) or the ridge."""
		err = 0.0
		for k in range(5):
			te, tr = fold == k, fold != k
			if alpha is None:
				p = np.full(te.sum(), np.average(y[tr], weights=W[tr]))
			else:
				p = Ridge(alpha=alpha).fit(Z[tr], y[tr], sample_weight=W[tr]).predict(Z[te])
			err += float((W[te] * (np.clip(p, 0, 1) - y[te]) ** 2).sum())
		return err / W.sum()

	out = {"origin": "LEARNED (current-patch ranked games, top-20 teams; tools/mapintel/pick_prior.py)", "zfeatures": arche["features"],
		   "rate": [], "first": []}
	L = ["# Pick prior for unknown maps: the strong teams' pick rate (and first-pick share) from the runtime features\n",
		 f"{len(maps)} maps, weighted by their strong team-sides. Held-out weighted squared error (5 archetype folds): pooled constant vs ridge.\n",
		 "| champion | pick rate: constant | ridge | used | first pick: constant | ridge | used |", "|---|---|---|---|---|---|---|"]
	for c in range(12):
		row = []
		for kind in ("rate", "first"):
			y = targets[(kind, c)]
			e0 = cv_err(y, None)
			best_a, e1 = min(((al, cv_err(y, al)) for al in ALPHAS), key=lambda t: t[1])
			use = "ridge" if e1 < e0 else "constant"
			if use == "ridge":
				m_ = Ridge(alpha=best_a).fit(Z, y, sample_weight=W)
				ent = {"use": use, "alpha": best_a, "intercept": float(m_.intercept_), "coef": [float(v) for v in m_.coef_]}
			else:
				ent = {"use": use, "intercept": float(np.average(y, weights=W)), "coef": [0.0] * Z.shape[1]}
			ent.update(cv_constant=e0, cv_ridge=e1)
			out[kind].append(ent)
			row += [f"{e0:.4f}", f"{e1:.4f}", use]
		L.append(f"| {PICK_NAMES[c]} | " + " | ".join(row) + " |")
	json.dump(out, open(a.out, "w"), indent=1)
	open(os.path.join(os.path.dirname(a.out), "pick_prior_report.md"), "w").write("\n".join(L) + "\n")
	print("\n".join(L))


def pick_prior_py(z, P):
	"""(rate[12], first[12]) for the runtime z-vector: model_weights.h pick_prior()."""
	out = []
	for kind in ("rate", "first"):
		v_ = []
		for e in P[kind]:
			v = e["intercept"]
			for i in range(len(z)):
				v += e["coef"][i] * z[i]
			v_.append(min(1.0, max(0.0, v)))
		out.append(v_)
	return out


if __name__ == "__main__":
	main()
