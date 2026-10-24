#!/usr/bin/env python3
"""Step 6 (MAPAnalysis.md 5.6), draft part: what the current-patch ladder says about champions per map. LEARNED.

    python3 -I tools/mapintel/draft_learn.py [--matches experiments/ladder_oct24/mapintel_20261024_0836/matches_current.jsonl]
                                             [--teams .../teams.json] [--out experiments/results/mapintel/draft_model]

Data: the ladder's current-patch ranked games on the 40 official maps (both teams on engine >= 1.0.3, so both sides are real teams'
drafts). The draft is simultaneous (both teams pick in each round, seeing the other's earlier rounds), champions unique within a team.

1. Per-map prior (for the exact-match table; maps/catalog/draft_prior.json): games, pick rate of every champion among all teams and
   among the strong teams (top 20 ratings), its rate per pick round, its win rate when picked (with a Wilson 95% interval) and the
   strong teams' most frequent rosters with their records. Sample sizes are kept: a table entry is used only with enough games.
2. Win models compared by leave-maps-out cross-validation (5 folds of maps, stratified by archetype: maps/catalog/splits.json), on the
   team-difference form  logit P(team a wins) = b0 + b_r x (rating_a - rating_b) / 100 + sum_c (x_ac - x_bc) x value_c(map)
   (x_tc = 1 when team t has champion c; unrated teams get the 50th rating minus 50). Team strength is in the model, so a champion's
   value is not "strong teams pick it". Models:
     M0  side + rating
     M1  + one value per champion
     M2  + a value per champion and archetype (k = 3)
     M3  + value_c(map) = w_c + v_c . z(map)  (z = the standardised runtime features of archetypes.py, i.e. what a bot computes at draft
         time: the map model's fallback for maps the table does not know)
     M4  M3 + the ally-pair terms of the 12 most frequent pairs (synergy)
   L2 strengths chosen inside the training folds. Reported: log loss and AUC on the held-out maps (out of sample for every map).
3. The chosen model's weights (experiments/results/mapintel/draft_model/weights.json) for model_weights.h: per champion w_c, v_c and
   the feature scaling, and per map the champion values it implies.
4. --battery GAMES.CSV (the roster battery of run_battery.sh: both rosters forced, the same bot on both sides, so strength is fixed by
   design): the same models with a side term instead of the rating, on the battery's games -> weights_sim.json (SIMULATED <bot>).
   Measured Oct 24: on the ladder no champion model beats rating alone out of sample (team strength and the converged meta hide
   champion value); on GOD v10's battery (2,240 games) M1 does (log loss 0.622 vs 0.662) and M2 / M3 do not beat M1: export_headers.py
   uses weights_sim.json when present."""
import argparse, csv, itertools, json, math, os, sys
from collections import Counter, defaultdict

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archetypes import CLUSTER_FEATURES, transform  # noqa: E402
from engine import PICK_NAMES  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LAD = os.path.join(ROOT, "experiments/ladder_oct24/mapintel_20261024_0836")
NC = len(PICK_NAMES)


def wilson(k, n, z=1.96):
	if n == 0:
		return [0.0, 1.0]
	p = k / n
	d = 1 + z * z / n
	c = (p + z * z / (2 * n)) / d
	h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
	return [round(c - h, 3), round(c + h, 3)]


def norm_map(name):
	return name.replace("_", "-")


def load(a):
	ms = [json.loads(l) for l in open(a.matches, encoding="utf-8") if l.strip()]
	T = json.load(open(a.teams, encoding="utf-8"))
	rating = {t["teamId"]: t["rating"] for t in T["teams"] if t.get("rating")}
	r50 = sorted(rating.values())[0] - 50.0
	strong = set(T["strong"])
	games, seen = [], set()
	for m in ms:
		if m["matchId"] in seen or len(m["teams"]) != 2:
			continue
		seen.add(m["matchId"])
		A = next(t for t in m["teams"] if t["side"] == "a")
		B = next(t for t in m["teams"] if t["side"] == "b")
		games.append({"map": norm_map(m.get("mapFile") or m["map"]), "a": A, "b": B, "win_a": A["result"] == "win",
					  "ra": rating.get(A["teamId"], r50), "rb": rating.get(B["teamId"], r50), "end": m.get("endReason", "")})
	return games, strong, rating


def prior(games, strong):
	out = {}
	by = defaultdict(list)
	for g in games:
		by[g["map"]].append(g)
	for mp, gs in sorted(by.items()):
		n_all = n_str = 0
		pick, pick_s, win, rounds = Counter(), Counter(), Counter(), defaultdict(Counter)
		rosters = Counter()
		rwins = Counter()
		for g in gs:
			for side in ("a", "b"):
				t = g[side]
				won = t["result"] == "win"
				n_all += 1
				for k, p in enumerate(t["draftPicks"]):
					pick[p] += 1
					win[p] += won
					rounds[p][k] += 1
				if t["teamId"] in strong:
					n_str += 1
					for p in t["draftPicks"]:
						pick_s[p] += 1
					key = tuple(sorted(t["draftPicks"]))
					rosters[key] += 1
					rwins[key] += won
		champs = []
		for p in range(NC):
			champs.append({"champion": PICK_NAMES[p], "pick_rate": round(pick[p] / max(1, n_all), 3),
						   "pick_rate_strong": round(pick_s[p] / max(1, n_str), 3), "picked": pick[p], "win_rate": round(win[p] / max(1, pick[p]), 3),
						   "win_ci95": wilson(win[p], pick[p]), "by_round": [rounds[p][k] for k in range(5)]})
		out[mp] = {"games": len(gs), "team_sides": n_all, "strong_team_sides": n_str, "champions": champs,
				   "strong_rosters": [{"picks": [PICK_NAMES[p] for p in key], "ids": list(key), "count": c, "wins": rwins[key]}
									  for key, c in rosters.most_common(6)]}
	return out


def map_z(catalog):
	rows = {r["map"]: r for r in csv.DictReader(open(os.path.join(catalog, "maps.csv")))}
	X = {m: np.array([transform(r[c], t) for c, t in CLUSTER_FEATURES]) for m, r in rows.items()}
	M = np.array(list(X.values()))
	mu, sd = M.mean(0), M.std(0)
	sd[sd == 0] = 1
	return {m: (x - mu) / sd for m, x in X.items()}, mu, sd


def design(games, model, Z, arch, pairs):
	"""Rows: the team-difference features of each game (both orientations are not needed: the side term absorbs side a)."""
	X, y = [], []
	nf = len(next(iter(Z.values())))
	for g in games:
		xa = np.zeros(NC)
		xb = np.zeros(NC)
		for p in g["a"]["draftPicks"]:
			xa[p] = 1
		for p in g["b"]["draftPicks"]:
			xb[p] = 1
		d = xa - xb
		row = [(g["ra"] - g["rb"]) / 100.0]
		if model >= 1:
			row += list(d)
		if model == 2:
			oh = np.zeros(3)
			oh[arch[g["map"]]] = 1
			row += list(np.outer(oh, d).ravel())
		if model >= 3:
			row += list(np.outer(d, Z[g["map"]]).ravel())
		if model >= 4:
			for (i, j) in pairs:
				row.append(xa[i] * xa[j] - xb[i] * xb[j])
		X.append(row)
		y.append(1 if g["win_a"] else 0)
	return np.array(X), np.array(y)


def fit(X, y, C):
	m = LogisticRegression(C=C, max_iter=4000)
	m.fit(X, y)
	return m


def cv(games, model, Z, arch, pairs, folds, Cs):
	"""Leave-maps-out: for each fold, choose C by an inner leave-maps-out split of the training maps, fit, predict the held-out maps."""
	pred = np.zeros(len(games))
	chosen = []
	for k, test in enumerate(folds):
		tr = [i for i, g in enumerate(games) if g["map"] not in test]
		te = [i for i, g in enumerate(games) if g["map"] in test]
		inner = [f for j, f in enumerate(folds) if j != k]
		best = None
		for C in Cs:
			ll = []
			for f in inner:
				itr = [i for i in tr if games[i]["map"] not in f]
				ite = [i for i in tr if games[i]["map"] in f]
				X, y = design([games[i] for i in itr], model, Z, arch, pairs)
				m = fit(X, y, C)
				Xt, yt = design([games[i] for i in ite], model, Z, arch, pairs)
				ll.append(log_loss(yt, m.predict_proba(Xt)[:, 1], labels=[0, 1]) * len(ite))
			s = sum(ll)
			if best is None or s < best[0]:
				best = (s, C)
		chosen.append(best[1])
		X, y = design([games[i] for i in tr], model, Z, arch, pairs)
		m = fit(X, y, best[1])
		Xt, _ = design([games[i] for i in te], model, Z, arch, pairs)
		pred[te] = m.predict_proba(Xt)[:, 1]
	yy = np.array([1 if g["win_a"] else 0 for g in games])
	return log_loss(yy, pred), roc_auc_score(yy, pred), chosen


def battery(path, Z, mu, sd, arch, folds, out, label):
	"""Section 4: the roster battery (games.csv of run_battery.sh / sim_v10): side + champion differences, leave-maps-out."""
	nm = {n: i for i, n in enumerate(PICK_NAMES)}
	G = []
	for r in csv.DictReader(open(path)):
		if r["battery"] != "roster":
			continue
		d = np.zeros(NC)
		for n in r["roster_bot"].split("/"):
			d[nm[n]] += 1
		for n in r["roster_opp"].split("/"):
			d[nm[n]] -= 1
		G.append((r["map"], 1.0 if r["side"] == "A" else -1.0, d, int(r["win"])))

	def X_(gs, model):
		X = []
		for mp, side, d, _ in gs:
			row = [side]
			if model >= 1:
				row += list(d)
			if model == 2:
				oh = np.zeros(3)
				oh[arch[mp]] = 1
				row += list(np.outer(oh, d).ravel())
			if model == 3:
				row += list(np.outer(d, Z[mp]).ravel())
			X.append(row)
		return np.array(X), np.array([g[3] for g in gs])

	yy = np.array([g[3] for g in G])
	res = {}
	for model in (0, 1, 2, 3):
		for C in (0.03, 0.1, 0.3, 1.0):
			pred = np.zeros(len(G))
			for test in folds:
				tr = [g for g in G if g[0] not in test]
				te = [i for i, g in enumerate(G) if g[0] in test]
				X, y = X_(tr, model)
				m = fit(X, y, C)
				Xt, _ = X_([G[i] for i in te], model)
				pred[te] = m.predict_proba(Xt)[:, 1]
			res[model, C] = (log_loss(yy, pred), roc_auc_score(yy, pred))
	best = min(res, key=lambda k: res[k][0])
	use = 1 if best[0] in (0, 1) or res[best][0] >= min(v[0] for k, v in res.items() if k[0] == 1) - 0.002 else best[0]
	C = min((k for k in res if k[0] == use), key=lambda k: res[k][0])[1]
	X, y = X_(G, use)
	m = fit(X, y, C)
	coef = m.coef_[0]
	w = {"origin": f"SIMULATED ({label}): roster battery, both rosters forced", "model": f"M{use}", "C": C, "intercept": float(m.intercept_[0]),
		 "side_A": float(coef[0]), "champions": PICK_NAMES, "features": [c for c, _ in CLUSTER_FEATURES], "transforms": [t for _, t in CLUSTER_FEATURES],
		 "mean": mu.round(6).tolist(), "std": sd.round(6).tolist(), "w": coef[1:1 + NC].round(5).tolist(), "games": len(G),
		 "cv": {f"M{k[0]} C {k[1]}": [round(v[0], 4), round(v[1], 4)] for k, v in sorted(res.items())}}
	if use == 3:
		w["v"] = coef[1 + NC:].reshape(NC, -1).round(5).tolist()
	vals = {}
	for mp, z in sorted(Z.items()):
		v = np.array(w["w"])
		if "v" in w:
			v = v + np.array(w["v"]) @ z
		if use == 2:
			v = v + coef[1 + NC + arch[mp] * NC:1 + NC + (arch[mp] + 1) * NC]
		vals[mp] = {PICK_NAMES[c]: round(float(v[c]), 4) for c in range(NC)}
	w["per_map_values"] = vals
	json.dump(w, open(os.path.join(out, "weights_sim.json"), "w"), indent=1)
	L = [f"\n## Roster battery ({label}, {len(G)} games, both rosters forced), leave-maps-out\n", "| model | C | log loss | AUC |", "|---|---|---|---|"]
	L += [f"| M{k[0]} | {k[1]} | {v[0]:.4f} | {v[1]:.4f} |" for k, v in sorted(res.items())]
	L += [f"\nUsed: M{use}, C = {C}. Champion values (log-odds per champion difference):"]
	L += [f"- {PICK_NAMES[c]}: {w['w'][c]:+.3f}" for c in np.argsort(-np.array(w["w"]))]
	return L


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--matches", default=os.path.join(LAD, "matches_current.jsonl"))
	ap.add_argument("--teams", default=os.path.join(LAD, "teams.json"))
	ap.add_argument("--catalog", default=os.path.join(ROOT, "maps/catalog"))
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/draft_model"))
	ap.add_argument("--models", default="0,1,2,3,4")
	ap.add_argument("--battery", default=os.path.join(ROOT, "experiments/results/mapintel/sim_v10/games.csv"), help="roster battery games.csv ('' = skip)")
	ap.add_argument("--battery-label", default="GOD v10")
	ap.add_argument("--battery-only", action="store_true", help="skip the ladder models (sections 2-3)")
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)
	games, strong, rating = load(a)
	P = prior(games, strong)
	json.dump({"origin": "LEARNED: current-patch ranked games (both teams engine >= 1.0.3) on the official maps",
			   "source": os.path.relpath(a.matches, ROOT), "strong": "top 20 ladder ratings", "maps": P},
			  open(os.path.join(a.catalog, "draft_prior.json"), "w"), indent=1)
	Z, mu, sd = map_z(a.catalog)
	arche = json.load(open(os.path.join(a.catalog, "archetypes.json")))
	arch = arche["labels"]
	folds = json.load(open(os.path.join(a.catalog, "splits.json")))["folds"]
	missing = sorted({g["map"] for g in games} - set(Z))
	if missing:
		sys.exit(f"maps not in the catalog: {missing}")
	pc = Counter()
	for g in games:
		for t in (g["a"], g["b"]):
			for i, j in itertools.combinations(sorted(t["draftPicks"]), 2):
				pc[i, j] += 1
	pairs = [p for p, _ in pc.most_common(12)]
	if a.battery_only:
		L = battery(a.battery, Z, mu, sd, arch, folds, a.out, a.battery_label)
		rp = os.path.join(a.out, "report.md")
		old = open(rp).read().split("\n## Roster battery")[0] if os.path.exists(rp) else ""
		open(rp, "w").write(old.rstrip("\n") + "\n" + "\n".join(L) + "\n")
		print("\n".join(L))
		return
	Cs = [0.01, 0.03, 0.1, 0.3, 1.0]
	res = {}
	lines = [f"# Draft win models, leave-maps-out (5 folds of maps stratified by archetype)\n",
			 f"{len(games)} games on {len({g['map'] for g in games})} maps; side a wins {np.mean([g['win_a'] for g in games]):.3f}; "
			 f"higher-rated team wins {np.mean([(g['ra'] > g['rb']) == g['win_a'] for g in games if g['ra'] != g['rb']]):.3f}\n",
			 "| model | log loss | AUC | C per fold |", "|---|---|---|---|"]
	for mdl in [int(x) for x in a.models.split(",")]:
		ll, auc, ch = cv(games, mdl, Z, arch, pairs, folds, Cs)
		res[mdl] = (ll, auc, ch)
		lines.append(f"| M{mdl} | {ll:.4f} | {auc:.4f} | {ch} |")
		print(lines[-1], flush=True)
	# the model a bot can use on unknown maps: M3 (or M4) when it beats M1 out of sample, else M1
	best = min(res, key=lambda k: res[k][0])
	use = best if best in (1, 3, 4) else (3 if 3 in res and res[3][0] <= res.get(1, (9,))[0] else 1)
	C = Counter(res[use][2]).most_common(1)[0][0]
	X, y = design(games, use, Z, arch, pairs)
	m = fit(X, y, C)
	coef = m.coef_[0]
	w = {"origin": "LEARNED", "model": f"M{use}", "C": C, "intercept": float(m.intercept_[0]), "rating_per_100": float(coef[0]),
		 "champions": PICK_NAMES, "features": [c for c, _ in CLUSTER_FEATURES], "transforms": [t for _, t in CLUSTER_FEATURES],
		 "mean": mu.round(6).tolist(), "std": sd.round(6).tolist()}
	k = 1
	w["w"] = coef[k:k + NC].round(5).tolist()
	k += NC
	if use >= 3:
		nf = len(CLUSTER_FEATURES)
		w["v"] = coef[k:k + NC * nf].reshape(NC, nf).round(5).tolist()
		k += NC * nf
	if use >= 4:
		w["pairs"] = [[int(i), int(j), round(float(coef[k + q]), 5)] for q, (i, j) in enumerate(pairs)]
	vals = {}
	for mp, z in sorted(Z.items()):
		v = np.array(w["w"])
		if "v" in w:
			v = v + np.array(w["v"]) @ z
		vals[mp] = {PICK_NAMES[c]: round(float(v[c]), 4) for c in range(NC)}
	w["per_map_values"] = vals
	json.dump(w, open(os.path.join(a.out, "weights.json"), "w"), indent=1)
	lines.append(f"\nChosen for the headers: M{use} (C = {C}); full-data fit weights in weights.json. Champion values (log-odds, rating held "
				 f"fixed; M1-style mean over maps):")
	mean_v = np.mean([[vals[mp][PICK_NAMES[c]] for c in range(NC)] for mp in vals], axis=0)
	for c in np.argsort(-mean_v):
		lines.append(f"- {PICK_NAMES[c]}: {mean_v[c]:+.3f} (range over maps {min(vals[mp][PICK_NAMES[c]] for mp in vals):+.3f} .. "
					 f"{max(vals[mp][PICK_NAMES[c]] for mp in vals):+.3f})")
	lines.append("\nOn the ladder no champion model beats M0 (rating alone) out of sample: the values above are not informative.")
	if a.battery and os.path.exists(a.battery):
		lines += battery(a.battery, Z, mu, sd, arch, folds, a.out, a.battery_label)
	open(os.path.join(a.out, "report.md"), "w").write("\n".join(lines) + "\n")
	print("\n".join(lines[-30:]))


if __name__ == "__main__":
	main()
