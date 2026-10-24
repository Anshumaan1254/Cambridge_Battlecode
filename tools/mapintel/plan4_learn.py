#!/usr/bin/env python3
"""Plan 4 (MAPAnalysis.md 5.3g) LEARNED from the top teams' replays (the user's change 1 of Oct 24).

    python3 -I tools/mapintel/plan4_learn.py [--tracks mapintel_work/tracks] [--out experiments/results/mapintel/plan4]
    (tracks: tools/mapintel/replay_tracks.py)

Decision moments and labels, per game, team-relative (fields: BFS on the team's passable tiles, features.fields):
  abandon   rounds where a body hits a camp of a living group with an enemy within 12 tiles. An engagement ends when the body stops hitting
            the group for 3 rounds; it is an ABANDON when the group still lives, the body does not hit it again within 30 rounds, gets
            5+ tiles away and is alive 5 rounds later (deaths are left out); the last 3 hitting rounds of an abandon are label 1, every
            other engaged round 0. Features: ETA gap = (remaining camp health / the group's health drop over the last 5 rounds, or the
            body's strength) - (the nearest enemy's walk to the group - its attack range), and the local power ratio (percent) =
            sum of health x strength of our bodies within 8 / the enemy's within 8. Rule: abandon iff gap > k and power < p.
  regroup   every 5 rounds, a body in the middle band (|dU - dE| <= band of the tile), more than 3 steps from its spawn, not recalling,
            4+ tiles (Chebyshev) from its nearest ally, that moves 3+ tiles in the next 5 rounds: label 1 when it ends 3+ tiles closer
            to where that ally stood, 0 when it ends no closer (in between: left out). Rule: regroup iff distance > d.
  bank      rounds where a body carrying 20+ gems, 4+ steps from its spawn, walks toward an altar (its walk to the nearest altar's
            approach tiles fell by 2+ in 3 rounds). A trip ABORTS when the body turns away (that walk rises 3+ within 10 rounds) or
            recalls, and does not bank within 40 rounds; it completes when it banks within the walk + 15 rounds; deaths are left out.
            Label 1 = the last 3 heading rounds of an aborted trip. Feature: our walk to the approach tiles - the nearest enemy's walk
            to the same altar's approach tiles. Rule: abort iff that > -margin.
  wait      the first round a body stands within 2 of a dead group (after its own capture of it, if any): label 1 when it stays within
            4 until the group respawns, 0 when it walks 7+ away first (deaths left out). Feature: rounds until the respawn (observed).
            Rule: wait iff rounds <= w.
Per map the best threshold (balanced accuracy over its moments; ties: the median of the best) is the ridge target over the 19 runtime
z-features (model_weights.h zfeat(), per team); the alpha by inner leave-folds-out. Held out (the 5 archetype-stratified map folds): the
pooled balanced accuracy of the rule with (a) the current formula (compact.thresholds), (b) the training folds' best constant, (c) the
ridge. A threshold uses the ridge only when (c) beats (a) on held-out maps (and (b), else the constant). Writes report.md, samples.npz,
weights.json (read by export_headers.py -> model_weights.h p4_thresholds(), and by compact.thresholds)."""
import argparse, glob, json, math, os, sys
from collections import defaultdict

import numpy as np
from sklearn.linear_model import Ridge

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compact as CP  # noqa: E402
import economy as EC  # noqa: E402
import export_headers as EH  # noqa: E402
import features as FT  # noqa: E402
import geometry as G  # noqa: E402
import mapdata  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ALPHAS = [0.3, 1, 3, 10, 30, 100, 1e3, 1e5]
GRID = {"k": list(range(0, 121, 2)), "p": [25, 50, 75, 100, 125, 150, 200, 300, 500, 1000, 65535], "d": list(range(4, 41)),
		"m": list(range(0, 61)), "w": list(range(0, 201, 2))}
INDEX = {"k": 0, "p": 1, "d": 2, "m": 4, "w": 5}  # positions in the 8 plan-4 thresholds (3 = r_enemies stays the formula)
NAMES = {"k": "ETA gap k_abandon (rounds)", "p": "local power p (percent)", "d": "regroup distance d (tiles)",
		 "m": "bank-interception margin (rounds)", "w": "respawn wait w_max (rounds)"}


class MapCtx:
	def __init__(self, name, arche):
		self.M = M = mapdata.load(name)
		self.C, self.fc, _, _ = FT.fields(M, 0)
		sd = FT.compute(M, 0)[FT.NAMES.index("spawn_dist")]
		self.band = max(3, int(math.floor(0.1 * sd + 0.5)))
		self.gmask = []
		for g in M.groups:
			m = np.zeros_like(M.walls)
			for c in g["camps"]:
				m[c[2], c[1]] = True
			self.gmask.append(m)
		self._gf = {}
		self.af = [[], []]
		ok = ~(M.walls | M.holes | M.altars)
		for (ax, ay) in M.altar_tiles:
			m = np.zeros_like(M.walls)
			m[max(0, ay - 1):ay + 2, max(0, ax - 1):ax + 2] = True
			m &= ok
			for t in (0, 1):
				self.af[t].append(G.bfs(self.C[t], m & self.C[t]))
		self.z = [EH.zfeat_py(FT.compute(M, t), arche) for t in (0, 1)]
		self.formula = [CP.Compact(M, t).formula_thresholds() for t in (0, 1)]

	def gf(self, t, g):
		if (t, g) not in self._gf:
			self._gf[(t, g)] = G.bfs(self.C[t], self.gmask[g])
		return self._gf[(t, g)]


def cheb(a, b):
	return max(abs(int(a[0]) - int(b[0])), abs(int(a[1]) - int(b[1])))


def extract(T, X):
	"""The four sample sets of one game: rows (team, features..., context..., label): A (team, gap, power, group, y), R (team, distance,
	x, y, label), K (team, margin feature, x, y, altar, label), W (team, rounds to respawn, group, label)."""
	M = X.M
	pos, alive, hp, bag, chp = T["pos"], T["alive"], T["hp"], T["bag"], T["chp"]
	bteam, btype, cgroup = T["bteam"], T["btype"], T["cgroup"]
	R, B = alive.shape
	E = EC.engine().champs
	strn = np.array([E[int(t)]["str"] for t in btype], float)
	rng = np.array([E[int(t)]["range"] for t in btype], float)
	at = lambda f, p: int(f[p[1], p[0]])  # noqa: E731
	gcamps = defaultdict(list)
	for ci, g in enumerate(cgroup):
		if g >= 0:
			gcamps[int(g)].append(ci)
	ghp = {g: chp[:, cs].sum(1) for g, cs in gcamps.items()}
	recall_r = defaultdict(set)
	for r, b in T["ev_recall"]:
		recall_r[int(b)].add(int(r))
	hits = defaultdict(list)  # body -> [(round, group)]
	camp_at = {(int(x), int(y)): int(g) for x, y, g in zip(T["cx"], T["cy"], cgroup) if g >= 0}
	for row in list(T["ev_attack"]) + [r_[:4] for r_ in T["ev_cast"]]:
		g = camp_at.get((int(row[2]), int(row[3])))
		if g is not None:
			hits[int(row[1])].append((int(row[0]), g))
	out = {"A": [], "R": [], "K": [], "W": [], "other_abandon": []}

	def enemies(t, r):
		return [e for e in range(B) if bteam[e] != t and alive[r, e]]

	def power(b, r):
		t = bteam[b]
		ours = theirs = 0.0
		for e in range(B):
			if alive[r, e] and cheb(pos[r, e], pos[r, b]) <= 8:
				if bteam[e] == t:
					ours += float(hp[r, e]) * strn[e]
				else:
					theirs += float(hp[r, e]) * strn[e]
		return 1000.0 if theirs <= 0 else 100.0 * ours / theirs

	# abandon
	for b, hl in hits.items():
		t = int(bteam[b])
		hl.sort()
		eps = []
		for r, g in hl:
			if eps and eps[-1][0] == g and r - eps[-1][2] <= 3:
				eps[-1][2] = r
				eps[-1][3].add(r)
			else:
				eps.append([g, r, r, {r}])
		for g, r0, r1, rounds in eps:
			if r1 + 31 >= R or g not in ghp:
				continue
			living = ghp[g][r1 + 1] > 0
			kind = "keep"
			if living:
				again = any(g2 == g and r1 < r2 <= r1 + 30 for r2, g2 in hl)
				if again:
					kind = "keep"
				elif not alive[r1 + 1:r1 + 6, b].all():
					continue
				else:
					f = X.gf(t, g)
					far = max(at(f, pos[r, b]) for r in range(r1 + 1, r1 + 31))
					if far < 5:
						continue
					threat = any(cheb(pos[r, e], pos[r, b]) <= 12 for r in range(max(1, r1 - 2), r1 + 1) for e in enemies(t, r))
					kind = "abandon" if threat else "other"
			if kind == "other":
				out["other_abandon"].append((t, r1, float(hp[r1, b]) / max(1, T["maxhp"][r1, b])))
				continue
			for r in sorted(rounds):
				if r < 6:
					continue
				ens = [e for e in enemies(t, r) if cheb(pos[r, e], pos[r, b]) <= 12]
				if not ens:
					continue
				drop = (ghp[g][r - 5] - ghp[g][r]) / 5.0
				rate = drop if drop > 0 else strn[b]
				eta_us = min(300.0, ghp[g][r] / rate)
				ef = X.gf(1 - t, g)
				et = [max(0.0, at(ef, pos[r, e]) - rng[e]) for e in enemies(t, r) if at(ef, pos[r, e]) >= 0]
				eta_them = min(et) if et else 300.0
				y = 1 if kind == "abandon" and r >= r1 - 2 else 0
				out["A"].append((t, eta_us - eta_them, power(b, r), g, y))
	# regroup
	band = X.band
	for r in range(10, R - 5, 5):
		for b in range(B):
			if not (alive[r, b] and alive[r + 5, b]):
				continue
			t = int(bteam[b])
			p = pos[r, b]
			du, de = at(X.fc[t], p), at(X.fc[1 - t], p)
			if du <= 3 or de < 0 or abs(du - de) > band:
				continue
			if any(rr in recall_r[b] for rr in range(r - 5, r + 6)):
				continue
			al = [(cheb(pos[r, a], p), a) for a in range(B) if a != b and bteam[a] == t and alive[r, a]]
			if not al:
				continue
			D, a = min(al)
			if D < 4 or cheb(pos[r + 5, b], p) < 3:
				continue
			after = cheb(pos[r + 5, b], pos[r, a])
			if after <= D - 3:
				out["R"].append((t, D, int(p[0]), int(p[1]), 1))
			elif after >= D:
				out["R"].append((t, D, int(p[0]), int(p[1]), 0))
	# bank
	banks = defaultdict(list)
	for r, b, gems, alt in T["ev_bank"]:
		banks[int(b)].append(int(r))
	for b in range(B):
		t = int(bteam[b])
		na = len(X.af[t])
		if na == 0:
			continue
		px, py = pos[:, b, 0].astype(int), pos[:, b, 1].astype(int)
		Dk = np.stack([X.af[t][k][py, px] for k in range(na)]).astype(float)
		Dk[Dk < 0] = 1e9
		ai = Dk.argmin(0)
		A = Dk.min(0)
		A[(A >= 1e9) | (alive[:, b] == 0)] = -1
		A = A.astype(int)
		fcb = X.fc[t][py, px]
		head = np.zeros(R, bool)
		head[4:] = (alive[4:, b] > 0) & (bag[4:, b] >= 20) & (A[4:] >= 0) & (A[1:R - 3] >= 0) & (A[1:R - 3] - A[4:] >= 2) & (fcb[4:] > 3)
		r = 4
		while r < R:
			if not head[r]:
				r += 1
				continue
			rs = r
			while r + 1 < R and (head[r + 1] or (r + 2 < R and head[r + 2]) or (r + 3 < R and head[r + 3])):
				r += 1
			re = r
			r += 1
			bk = [x for x in banks[b] if rs <= x <= re + A[re] + 15]
			if bk:
				kind = 0
			elif not alive[rs:min(R, re + 11), b].all():
				continue
			else:
				turned = any(A[x] >= 0 and A[x] - A[re] >= 3 for x in range(re + 1, min(R, re + 11))) or any(x in recall_r[b] for x in range(re, re + 11))
				if not turned or any(re < x <= re + 40 for x in banks[b]):
					continue
				kind = 1
			for x in range(rs, re + 1):
				if not head[x]:
					continue
				k = ai[x]
				ie = [at(X.af[1 - t][k], pos[x, e]) for e in enemies(t, x)]
				ie = [v for v in ie if v >= 0]
				inter = min(ie) if ie else 300
				out["K"].append((t, float(A[x] - inter), int(pos[x, b, 0]), int(pos[x, b, 1]), int(k), 1 if kind == 1 and x >= re - 2 else 0))
	# wait
	caps = defaultdict(list)
	for r, b, g, gems in T["ev_capture"]:
		caps[(int(b), int(g))].append(int(r))
	fvec = {}
	for g in ghp:
		for b in range(B):
			t = int(bteam[b])
			fvec[(t, g, b)] = X.gf(t, g)[pos[:, b, 1].astype(int), pos[:, b, 0].astype(int)]
	for g, h in ghp.items():
		dead = h <= 0
		r = 1
		while r < R:
			if not dead[r]:
				r += 1
				continue
			rd = r
			while r < R and dead[r]:
				r += 1
			rsp = r  # first alive round (R = never)
			if rsp >= R:
				break
			for b in range(B):
				t = int(bteam[b])
				fv = fvec[(t, g, b)]
				near = np.nonzero((alive[rd:rsp, b] > 0) & (fv[rd:rsp] >= 0) & (fv[rd:rsp] <= 2))[0]
				start = None
				for x in near + rd:
					if not any(x <= c <= x + 6 for c in caps[(b, g)]):
						start = int(x)
						break
				if start is None or rsp - start > 200:
					continue
				if not alive[start:rsp + 1, b].all():
					continue
				ds = fv[start:rsp]
				if max(ds) <= 4:
					out["W"].append((t, float(rsp - start), g, 1))
				elif any(d >= 7 for d in ds):
					out["W"].append((t, float(rsp - start), g, 0))
	return out


def bacc(pred, y):
	pred, y = np.asarray(pred, bool), np.asarray(y, bool)
	if y.all() or (~y).all():
		return float("nan")
	return 0.5 * ((pred & y).sum() / y.sum() + (~pred & ~y).sum() / (~y).sum())


def rule(key, s, th):
	"""Predicted label of samples s (rows: team, features..., y) under thresholds th (dict key -> value per row)."""
	if key == "k":
		return (s[:, 1] > th["k"]) & (s[:, 2] < th["p"])
	if key == "d":
		return s[:, 1] > th["d"]
	if key == "m":
		return s[:, 1] > -th["m"]
	if key == "w":
		return s[:, 1] <= th["w"]


def best(key, s):
	"""The threshold(s) maximising balanced accuracy on s; ties: the median. For k the pair (k, p)."""
	y = s[:, -1]
	if key == "k":
		sc = [(bacc(rule("k", s, {"k": k, "p": p}), y), k, p) for k in GRID["k"] for p in GRID["p"]]
		top = max(v for v, _, _ in sc)
		if math.isnan(top):
			return None
		cand = [(k, p) for v, k, p in sc if v >= top - 1e-12]
		cand.sort()
		return cand[len(cand) // 2]
	sc = [(bacc(rule(key, s, {key: v}), y), v) for v in GRID[key]]
	top = max(v for v, _ in sc)
	if math.isnan(top):
		return None
	cand = sorted(v for b_, v in sc if b_ >= top - 1e-12)
	return (cand[len(cand) // 2],)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--tracks", default=os.path.join(ROOT, "mapintel_work/tracks"))
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/plan4"))
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)
	arche = json.load(open(os.path.join(ROOT, "maps/catalog/archetypes.json")))
	folds = json.load(open(os.path.join(ROOT, "maps/catalog/splits.json")))["folds"]
	fold_of = {n: k for k, f in enumerate(folds) for n in f}
	ctx, S = {}, defaultdict(lambda: defaultdict(list))
	files = sorted(glob.glob(os.path.join(a.tracks, "*.npz")))
	other = []
	for i, f in enumerate(files):
		T = dict(np.load(f))
		mp = str(T["map"])
		if mp not in ctx:
			ctx[mp] = MapCtx(mp, arche)
		o = extract(T, ctx[mp])
		for k in "ARKW":
			S[mp][k] += o[k]
		other += o["other_abandon"]
		if (i + 1) % 100 == 0:
			print(f"{i + 1} / {len(files)} games", flush=True)
	maps = sorted(S)
	arr = {mp: {k: np.array(S[mp][k], float).reshape(-1, {"A": 5, "R": 5, "K": 6, "W": 4}[k]) for k in "ARKW"} for mp in maps}
	np.savez_compressed(os.path.join(a.out, "samples.npz"), **{f"{mp}__{k}": v for mp, d in arr.items() for k, v in d.items()})
	src = {"k": "A", "d": "R", "m": "K", "w": "W"}
	keys_of = {"k": ["k", "p"], "d": ["d"], "m": ["m"], "w": ["w"]}
	res, model = {}, {}

	def th_rows(key, s, mp, values):
		"""Per-row threshold dict for samples s of map mp from per-team values {key: [team0, team1]}."""
		return {kk: np.where(s[:, 0] == 0, v[0], v[1]) for kk, v in values.items()}

	def fit_ridge(train_maps, kk, key, alpha):
		X, y, w = [], [], []
		for mp in train_maps:
			s = arr[mp][src[key]]
			bt = best(key, s) if len(s) else None
			if bt is None:
				continue
			sup = min(s[:, -1].sum(), (1 - s[:, -1]).sum())
			for t in (0, 1):
				X.append(ctx[mp].z[t])
				y.append(bt[keys_of[key].index(kk)])
				w.append(math.sqrt(sup))
		if len(X) < 4:
			return None
		return Ridge(alpha=alpha).fit(np.array(X), np.array(y, float), sample_weight=np.array(w))

	def clamp(kk, v):
		g = GRID[kk]
		return float(min(max(math.floor(v + 0.5), g[0]), g[-1]))

	def predict(models, mp, key):
		vals = {}
		for kk in keys_of[key]:
			m = models[kk]
			vals[kk] = [clamp(kk, m.predict(np.array([ctx[mp].z[t]]))[0]) for t in (0, 1)]
		return vals

	def const_best(train_maps, key):
		s = np.concatenate([arr[mp][src[key]] for mp in train_maps if len(arr[mp][src[key]])])
		return best(key, s)

	def pooled(key, maps_, thfn):
		ss, pp = [], []
		for mp in maps_:
			s = arr[mp][src[key]]
			if not len(s):
				continue
			th = th_rows(key, s, mp, thfn(mp))
			ss.append(s[:, -1])
			pp.append(rule(key, s, th))
		return bacc(np.concatenate(pp), np.concatenate(ss)) if ss else float("nan")

	def choose_alpha(train_maps, key):
		best_a, best_v = ALPHAS[-1], -1
		tf = sorted({fold_of[m] for m in train_maps})
		for al in ALPHAS:
			ps, ys = [], []
			for k in tf:
				tr = [m for m in train_maps if fold_of[m] != k]
				te = [m for m in train_maps if fold_of[m] == k]
				models = {kk: fit_ridge(tr, kk, key, al) for kk in keys_of[key]}
				if any(v is None for v in models.values()):
					continue
				for mp in te:
					s = arr[mp][src[key]]
					if len(s):
						ps.append(rule(key, s, th_rows(key, s, mp, predict(models, mp, key))))
						ys.append(s[:, -1])
			v = bacc(np.concatenate(ps), np.concatenate(ys)) if ps else -1
			if v > best_v + 1e-9:
				best_a, best_v = al, v
		return best_a

	for key in ("k", "d", "m", "w"):
		allm = [mp for mp in maps if len(arr[mp][src[key]])]
		npos = int(sum(arr[mp][src[key]][:, -1].sum() for mp in allm))
		ntot = int(sum(len(arr[mp][src[key]]) for mp in allm))
		pred_r, pred_c = {}, {}
		alphas = []
		for k in range(5):
			te = [m for m in allm if fold_of[m] == k]
			tr = [m for m in allm if fold_of[m] != k]
			al = choose_alpha(tr, key)
			alphas.append(al)
			models = {kk: fit_ridge(tr, kk, key, al) for kk in keys_of[key]}
			cb = const_best(tr, key)
			for mp in te:
				pred_r[mp] = predict(models, mp, key)
				pred_c[mp] = {kk: [cb[i], cb[i]] for i, kk in enumerate(keys_of[key])}
		formula = lambda mp: {kk: [ctx[mp].formula[t][INDEX[kk]] for t in (0, 1)] for kk in keys_of[key]}  # noqa: E731
		va = {"formula": pooled(key, allm, formula), "constant": pooled(key, allm, lambda mp: pred_c[mp]),
			  "ridge": pooled(key, allm, lambda mp: pred_r[mp])}
		alpha = choose_alpha(allm, key)
		final = {kk: fit_ridge(allm, kk, key, alpha) for kk in keys_of[key]}
		cb = const_best(allm, key)
		use = "ridge" if va["ridge"] > va["formula"] and va["ridge"] >= va["constant"] else (
			"constant" if va["constant"] > va["formula"] else "formula")
		per_map = {mp: best(key, arr[mp][src[key]]) for mp in allm}
		res[key] = {"samples": ntot, "positives": npos, "maps": len(allm), "held_out_bacc": va, "alpha_folds": alphas, "alpha": alpha,
					"use": use, "constant": list(cb), "per_map_best": {mp: (list(v) if v else None) for mp, v in per_map.items()}}
		for i, kk in enumerate(keys_of[key]):
			m = final[kk]
			model[kk] = {"index": INDEX[kk], "use": use, "lo": GRID[kk][0], "hi": GRID[kk][-1],
						 "intercept": float(m.intercept_) if use == "ridge" else float(cb[i]),
						 "coef": [float(c) for c in m.coef_] if use == "ridge" else [0.0] * len(ctx[allm[0]].z[0])}
		print(f"{key}: {ntot} moments ({npos} label 1) on {len(allm)} maps; held-out balanced accuracy formula {va['formula']:.3f}, "
			  f"constant {va['constant']:.3f}, ridge {va['ridge']:.3f} -> {use}", flush=True)
	J = {"origin": "LEARNED (decision moments of 599 current-patch top-team replays; tools/mapintel/plan4_learn.py)",
		 "zfeatures": arche["features"], "thresholds": {kk: v for kk, v in model.items() if v["use"] != "formula"}, "results": res,
		 "names": NAMES}
	json.dump(J, open(os.path.join(a.out, "weights.json"), "w"), indent=1)
	hpf = np.array([x[2] for x in other]) if other else np.zeros(0)
	L = ["# Plan 4 thresholds learned from the top teams' replays (leave-maps-out, archetype folds)\n",
		 f"{len(files)} games on {len(maps)} maps. Pooled balanced accuracy of each rule on held-out maps (the threshold from the current "
		 "formula, the training folds' best constant, or the ridge over the 19 runtime map features); the winner goes into model_weights.h.\n",
		 "| threshold | moments (label 1) | maps | formula | constant | ridge | used | final value / intercept |", "|---|---|---|---|---|---|---|---|"]
	for key in ("k", "d", "m", "w"):
		r_ = res[key]
		va = r_["held_out_bacc"]
		fin = ", ".join(f"{kk} {model[kk]['intercept']:.1f}" for kk in keys_of[key])
		L.append(f"| {', '.join(NAMES[kk] for kk in keys_of[key])} | {r_['samples']} ({r_['positives']}) | {r_['maps']} | {va['formula']:.3f} | "
				 f"{va['constant']:.3f} | {va['ridge']:.3f} | {r_['use']} | {fin} |")
	L += ["", f"Abandons with no enemy within 12 tiles (not plan 4: heal / other reasons): {len(other)}, health at the moment median "
		  f"{np.median(hpf) if len(hpf) else float('nan'):.2f} (the economy model's retreat line, change 2).", "",
		  "Per-map best thresholds (balanced accuracy on that map alone): `results.<key>.per_map_best` in weights.json."]
	open(os.path.join(a.out, "report.md"), "w").write("\n".join(L) + "\n")
	print("\n".join(L))


if __name__ == "__main__":
	main()
