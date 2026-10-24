#!/usr/bin/env python3
"""Step-7 heat maps (the U-Net's out-of-fold predictions, the user's GPU run) -> per-group and per-bank-route features of the 40 official
maps, and whether they improve plan 3 and the LEARNED plan-4 thresholds on held-out maps (the user's request of Oct 24). LEARNED.

    python3 -I tools/mapintel/heat_features.py [--heat experiments/results/mapintel/dl_model_20261024_1014/heat_pred.npz]
                                               [--out experiments/results/mapintel/heat_features]

Heat: per map-team (team-relative: own spawn = team) and channel (hit camps, hit champions, capture, die) a distribution over the valid
tiles, predicted by a U-Net that never saw that map's games (out of fold). Density = heat / the map's mean heat (1 = average tile).
Features per team and group: the mean fight (hit champions) and death density over the tiles within Chebyshev 3 of the group's camps;
per team and group's bank route (catalog plan 2: the altar it banks at): the mean fight and death density along the walk from the group
to that altar's approach tiles (steepest descent on the BFS field, ties to the lower (y, x) neighbour order).
Tests (5 archetype-stratified map folds; every heat value is out of fold already):
  plan 3   truth per group = the share of a map's ladder games in which both teams captured it (replays.py summaries). Predictors: the
           catalog's plan-3 priority and contested flag, the runtime closeness exp(-|dU - dE| / band); logistic on (closeness, log value)
           vs (closeness, log value, fight, death); per-map Spearman with the truth (mean over maps) and pooled AUC of share >= 0.25.
  plan 4   the decision moments of plan4_learn.py (samples.npz: groups and tiles kept): the learned constant vs a threshold shifted by the
           local heat (abandon: k0 + k1 log fight density at the group; regroup: d0 + d1 log fight density around the body (7 x 7);
           bank: margin m0 + m1 log death density around the body; wait: w0 + w1 log death density at the group), the two numbers by
           grid search on the training folds; pooled balanced accuracy held out.
Writes report.md and features.json (per map, team and group: fight, death, route_fight, route_death)."""
import argparse, glob, json, math, os, sys
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compact as CP  # noqa: E402
import features as FT  # noqa: E402
import geometry as G  # noqa: E402
import mapdata  # noqa: E402
import plan4_learn as PL  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CH = {"camp": 0, "fight": 1, "capture": 2, "death": 3}


def box_mean(a, valid, r=3):
	"""Mean of a over the valid tiles of the (2r + 1)^2 box around every tile."""
	def bs(x):
		c = np.pad(x, ((r + 1, r), (r + 1, r))).cumsum(0).cumsum(1)
		return c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:] - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1]
	n = bs(valid.astype(float))
	return np.where(n > 0, bs(a * valid) / np.maximum(n, 1), 0.0)


def route(f, start_mask):
	"""Tiles of the steepest descent on the BFS field f from the start mask's nearest tile to a tile with f == 0."""
	ys, xs = np.nonzero(start_mask & (f >= 0))
	if not len(ys):
		return []
	k = int(np.argmin(f[ys, xs] * 100000 + ys * 1000 + xs))
	y, x = int(ys[k]), int(xs[k])
	H, W = f.shape
	path = [(x, y)]
	while f[y, x] > 0 and len(path) < 400:
		best = None
		for dy in (-1, 0, 1):
			for dx in (-1, 0, 1):
				yy, xx = y + dy, x + dx
				if (dx or dy) and 0 <= yy < H and 0 <= xx < W and 0 <= f[yy, xx] < f[y, x]:
					if best is None or (f[yy, xx], yy, xx) < best:
						best = (f[yy, xx], yy, xx)
		if best is None:
			break
		_, y, x = best
		path.append((x, y))
	return path


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--heat", default=os.path.join(ROOT, "experiments/results/mapintel/dl_model_20261024_1014/heat_pred.npz"))
	ap.add_argument("--summaries", default=os.path.join(ROOT, "experiments/results/mapintel/ladder_20261024"))
	ap.add_argument("--samples", default=os.path.join(ROOT, "experiments/results/mapintel/plan4/samples.npz"))
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/heat_features"))
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)
	P = np.load(a.heat)
	pred, hmaps = P["pred"].astype(np.float64), [str(m) for m in P["maps"]]
	D = np.load(os.path.join(ROOT, "experiments/results/mapintel/dl_data/dataset.npz"))
	grid = D["grid"]
	folds = json.load(open(os.path.join(ROOT, "maps/catalog/splits.json")))["folds"]
	fold_of = {n: k for k, f in enumerate(folds) for n in f}
	feats, dens, loc = {}, {}, {}
	for mi, mp in enumerate(hmaps):
		M = mapdata.load(mp)
		Cm, fc, _, _ = FT.fields(M, 0)
		cat = json.load(open(os.path.join(ROOT, "maps/catalog", mp + ".json")))
		altar_of = defaultdict(dict)
		for r in cat["bank_routes"]:
			for t in r["teams"]:
				if t.get("altar") is not None:
					altar_of[t["team"]][r["group"]] = t["altar"]
		ok = ~(M.walls | M.holes | M.altars)
		feats[mp] = []
		for t in (0, 1):
			mt = 2 * mi + t
			valid = grid[mt, 0, :M.H, :M.W] > 0.5
			dd = {}
			for name, c in CH.items():
				h = pred[mt, c, :M.H, :M.W]
				mu = h[valid].mean()
				dd[name] = np.where(valid, h / mu if mu > 0 else 0.0, 0.0)
			dens[(mp, t)] = dd
			loc[(mp, t)] = {n: box_mean(v, valid) for n, v in dd.items()}
			af = {}
			rows = []
			for gi, grp in enumerate(M.groups):
				gm = np.zeros_like(M.walls)
				for c in grp["camps"]:
					gm[c[2], c[1]] = True
				near = G.chebyshev_disk(gm, 3) & valid
				row = {"group": gi, "fight": float(dd["fight"][near].mean()) if near.any() else 1.0,
					   "death": float(dd["death"][near].mean()) if near.any() else 1.0}
				alt = altar_of[t].get(grp["id"])
				row["route_fight"] = row["route_death"] = None
				if alt is not None and alt < len(M.altar_tiles):
					if alt not in af:
						ax, ay = M.altar_tiles[alt]
						m = np.zeros_like(M.walls)
						m[max(0, ay - 1):ay + 2, max(0, ax - 1):ax + 2] = True
						af[alt] = G.bfs(Cm[t], m & ok & Cm[t])
					pth = route(af[alt], G.chebyshev_disk(gm, 1))
					if pth:
						row["route_fight"] = float(np.mean([dd["fight"][y, x] for x, y in pth]))
						row["route_death"] = float(np.mean([dd["death"][y, x] for x, y in pth]))
				rows.append(row)
			feats[mp].append(rows)
	json.dump({"origin": "LEARNED (U-Net heat of the current-patch ladder, out of fold; tools/mapintel/heat_features.py)", "maps": feats},
			  open(os.path.join(a.out, "features.json"), "w"))
	# ---- plan 3: which groups do both teams capture?
	games = defaultdict(list)
	for f in sorted(glob.glob(os.path.join(a.summaries, "*.json"))):
		S = json.load(open(f))
		if S.get("map") and not S.get("error"):
			games[S["map"]].append(S)
	rows = []
	for mp in hmaps:
		M = mapdata.load(mp)
		cat = json.load(open(os.path.join(ROOT, "maps/catalog", mp + ".json")))
		pr = {g["group"]: g for g in cat["groups"]}
		C = CP.Compact(M, 0)
		band, _ = C.contested()
		both = defaultdict(int)
		for S in games[mp]:
			who = defaultdict(set)
			for c in S["captures"]:
				if c[3] is not None:
					who[c[3]].add(c[1])
			for g, ts in who.items():
				if len(ts) == 2:
					both[g] += 1
		n = max(1, len(games[mp]))
		for gi, grp in enumerate(M.groups):
			if C.dU[gi] < 0 or C.dE[gi] < 0:
				continue
			hf = feats[mp][0][gi]
			rows.append({"map": mp, "share": both[grp["id"]] / n, "priority": pr[grp["id"]].get("priority", 0.0),
						 "contested": 1.0 if pr[grp["id"]].get("contested") else 0.0, "close": math.exp(-abs(C.dU[gi] - C.dE[gi]) / band),
						 "logv": math.log1p(C.val[gi]), "fight": math.log(max(hf["fight"], 0.05)), "death": math.log(max(hf["death"], 0.05)),
						 "logp": math.log1p(max(0.0, pr[grp["id"]].get("priority", 0.0)))})
	share = np.array([r["share"] for r in rows])
	lab = (share >= 0.25).astype(int)
	mapsr = np.array([r["map"] for r in rows])

	def map_spears(score):
		v = {}
		for mp in hmaps:
			i = mapsr == mp
			if i.sum() >= 4 and share[i].std() > 0 and np.std(score[i]) > 0:
				v[mp] = spearmanr(score[i], share[i])[0]
		return v

	def per_map_spear(score):
		return float(np.mean(list(map_spears(score).values())))

	def cv_logit(cols):
		X = np.array([[r[c] for c in cols] for r in rows])
		out = np.zeros(len(rows))
		for k in range(5):
			te = np.array([fold_of[m] == k for m in mapsr])
			mu, sd = X[~te].mean(0), X[~te].std(0) + 1e-9
			m = LogisticRegression(C=1.0, max_iter=2000).fit((X[~te] - mu) / sd, lab[~te])
			out[te] = m.decision_function((X[te] - mu) / sd)
		return out
	p3 = {}
	for name, sc in (("catalog priority", np.array([r["priority"] for r in rows])), ("catalog contested flag", np.array([r["contested"] for r in rows])),
					 ("runtime closeness", np.array([r["close"] for r in rows])), ("heat: fight", np.array([r["fight"] for r in rows])),
					 ("heat: death", np.array([r["death"] for r in rows])), ("logistic: closeness + value", cv_logit(["close", "logv"])),
					 ("logistic: closeness + value + heat", cv_logit(["close", "logv", "fight", "death"])), ("logistic: heat + value", cv_logit(["logv", "fight", "death"])),
					 ("logistic: catalog priority", cv_logit(["logp"])), ("logistic: catalog priority + heat", cv_logit(["logp", "fight", "death"]))):
		p3[name] = {"spearman_per_map": per_map_spear(sc), "auc": float(roc_auc_score(lab, sc)) if 0 < lab.sum() < len(lab) else None, "_score": sc}
	pairs = {}
	rng = np.random.default_rng(0)
	for base_, with_ in (("logistic: closeness + value", "logistic: closeness + value + heat"), ("logistic: catalog priority", "logistic: catalog priority + heat")):
		a_, b_ = map_spears(p3[base_]["_score"]), map_spears(p3[with_]["_score"])
		ms = sorted(set(a_) & set(b_))
		d = np.array([b_[m] - a_[m] for m in ms])
		boot = [rng.choice(d, len(d)).mean() for _ in range(2000)]
		pairs[with_] = {"vs": base_, "maps": len(ms), "mean_diff": float(d.mean()), "ci95": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))],
						"maps_better": int((d > 0).sum()), "maps_worse": int((d < 0).sum())}
	for v in p3.values():
		v.pop("_score")
	# ---- plan 4: heat-shifted thresholds
	Sm = np.load(a.samples)
	keyset = {"k": "A", "d": "R", "m": "K", "w": "W"}
	J4 = json.load(open(os.path.join(ROOT, "experiments/results/mapintel/plan4/weights.json")))
	p4 = {}
	for key, src in keyset.items():
		per = {}
		for mp in hmaps:
			k_ = f"{mp}__{src}"
			if k_ not in Sm.files or not len(Sm[k_]):
				continue
			s = Sm[k_]
			h = np.zeros(len(s))
			for t in (0, 1):
				i = s[:, 0] == t
				if not i.any():
					continue
				if src in ("A", "W"):
					fe = feats[mp][t]
					h[i] = [math.log(max(fe[int(g)]["fight" if src == "A" else "death"], 0.05)) for g in s[i, 3 if src == "A" else 2]]
				else:
					L = loc[(mp, t)]["fight" if src == "R" else "death"]
					h[i] = [math.log(max(L[int(y), int(x)], 0.05)) for x, y in s[i][:, 2:4]]
			per[mp] = (s, h)
		if not per:
			continue
		grid0 = {"k": range(0, 41, 2), "d": range(4, 31), "m": range(0, 31), "w": range(0, 81, 2)}[key]
		grid1 = [x * 0.5 for x in range(-20, 21)] if key != "w" else [x * 2.0 for x in range(-15, 16)]
		pgrid = [500, 1000, 65535] if key == "k" else [None]

		def pred(s, h, c0, c1, pp):
			th = c0 + c1 * h
			if key == "k":
				return (s[:, 1] > th) & (s[:, 2] < pp)
			if key == "d":
				return s[:, 1] > th
			if key == "m":
				return s[:, 1] > -th
			return s[:, 1] <= th

		def fitbest(ms, slope):
			ss = np.concatenate([per[m][0] for m in ms])
			hh = np.concatenate([per[m][1] for m in ms])
			y = ss[:, -1] > 0.5
			best = (-1, None)
			for pp in pgrid:
				for c1 in (grid1 if slope else [0.0]):
					for c0 in grid0:
						v = PL.bacc(pred(ss, hh, c0, c1, pp), y)
						if v > best[0]:
							best = (v, (c0, c1, pp))
			return best[1]
		res = {}
		for slope in (False, True):
			ps, ys = [], []
			for k in range(5):
				tr = [m for m in per if fold_of[m] != k]
				te = [m for m in per if fold_of[m] == k]
				c0, c1, pp = fitbest(tr, slope)
				for m in te:
					s, h = per[m]
					ps.append(pred(s, h, c0, c1, pp))
					ys.append(s[:, -1] > 0.5)
			res["heat-shifted" if slope else "constant"] = PL.bacc(np.concatenate(ps), np.concatenate(ys))
		res["fit_all"] = list(fitbest(list(per), True))
		p4[key] = res
		print(key, res, flush=True)
	J = {"plan3": p3, "plan3_paired": pairs, "plan4": p4, "groups_rows": len(rows), "label_share": float(lab.mean())}
	json.dump(J, open(os.path.join(a.out, "results.json"), "w"), indent=1)
	L = ["# Heat-map features (U-Net, out of fold) for plan 3 and plan 4, held out\n",
		 f"Plan 3: {len(rows)} groups reached by both teams on 40 maps; truth = the share of the map's ladder games in which both teams captured the "
		 f"group (label share >= 0.25: {lab.mean():.2f} of the groups).\n", "| predictor | Spearman per map (mean) | AUC |", "|---|---|---|"]
	for n, v in p3.items():
		L.append(f"| {n} | {v['spearman_per_map']:.3f} | {v['auc']:.3f} |")
	L += ["", "Paired per map (the same maps; bootstrap over maps, 2,000 draws):"]
	for w_, v in pairs.items():
		L.append(f"- {w_} vs {v['vs']}: Spearman {v['mean_diff']:+.3f} (95% {v['ci95'][0]:+.3f} .. {v['ci95'][1]:+.3f}), better on {v['maps_better']} "
				 f"of {v['maps']} maps, worse on {v['maps_worse']}")
	L += ["", "Plan 4: pooled balanced accuracy on held-out maps, the learned constant vs the heat-shifted threshold:\n",
		  "| threshold | constant | heat-shifted |", "|---|---|---|"]
	for key, v in p4.items():
		L.append(f"| {PL.NAMES[key]} | {v['constant']:.3f} | {v['heat-shifted']:.3f} |")
	open(os.path.join(a.out, "report.md"), "w").write("\n".join(L) + "\n")
	print("\n".join(L))


if __name__ == "__main__":
	main()
