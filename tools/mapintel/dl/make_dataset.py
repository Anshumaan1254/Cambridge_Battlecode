#!/usr/bin/env python3
"""Step 7 (MAPAnalysis.md 5.7), the data: one file the laptop's deep-learning run needs (numpy + torch only there).

    python3 -I tools/mapintel/dl/make_dataset.py [--out experiments/results/mapintel/dl_data] [--summaries DIR] [--battery GAMES.CSV]
                                                 [--battery-label NAME] [--check]

Inputs (all committed): the runtime dumps of every map of the pool (mapdata.pool_names(): the 70 maps of patch 2.0.0, maps/s3), the
catalog's archetypes and folds (maps/catalog: the 40 official maps; a map outside the catalog gets the archetype a bot computes for it and
an archetype-stratified fold: tools/mapintel/pool.py), the decoded ladder games (--summaries, replays.py's output; default
experiments/results/mapintel/ladder_20261024, engine 1.0.3: LEARNED) and a roster battery (--battery: run_battery.sh's games.csv, any
maps of the pool; default GOD v10's, experiments/results/mapintel/sim_v10/games.csv: SIMULATED). Everything is team-relative: index
mt = 2 x map + team (team 0 = A). --check: build every array and print the sizes, without the baselines and without writing.

dataset.npz
  maps          [M] names (sorted); fold [M] (the 5 archetype-stratified folds of splits.json, extended by pool.py); arch [M]
  grid          [2M, C, 100, 100] float32 map tensors, padded: 0 valid, 1 wall, 2 hole, 3 bush, 4 altar, 5 own spawn, 6 enemy spawn,
                7-12 camp type one-hot (wolf, elk, gem cluster, gold cluster, monolith, golem), 13 group gems / 100 on its camps,
                14 group gold / 100, 15 camp health / 5000, 16 our walk / 100 (BFS fc; 1.5 = not reached), 17 their walk / 100
  z             [2M, 19] the standardised runtime features of model_weights.h (zfeat: what a bot computes at draft time)
  gfeat         [2M, 64, FG] group features (first_targets.group_table's 14, then 6 camp-type counts, respawn / 100, max camp strength
                / 100); gmask [2M, 64] reached groups; gdist [2M, 64, 64] Chebyshev distance between group boxes / 100
  t1a_mt, t1a_n, t1a_first [S1, 64]   opening: the first n groups the team captured (n = its bodies), 963-ish team-games
  t1b_mt, t1b_prev, t1b_champ, t1b_round, t1b_target, t1b_avail [S2, 64]   next target of a body: given the body's previous capture,
                its champion (body type), the round, and the groups not captured within their respawn time, the group it captured next
  t2_map, t2_side, t2_diff [S3, 12], t2_win, t2_us, t2_them [S3, 12]   roster battery: champion difference (ours - theirs, draft
                ids), side (+1 = A), win, both rosters (multi-hot)
  heat          [2M, 4, 100, 100] float32: per game, where the team's bodies hit camps, hit champions, captured, died (ladder)
  heat_games    [2M] games behind each heat map
meta.json       feature names, channel names, sizes, origins, and the step-6 baselines on the same samples and folds (the bar the
                deep models must clear): t1a nearest / logistic / boosted forest top-n share; t1b nearest-to-previous / boosted forest
                top-1 and top-3; t2 side-only and M1 log loss; t3 camp-blur heat correlation."""
import argparse, csv, glob, json, math, os, sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import compact as CP  # noqa: E402
import pool as PL  # noqa: E402
import economy as EC  # noqa: E402
import export_headers as EH  # noqa: E402
import features as FT  # noqa: E402
import first_targets as FTG  # noqa: E402
import mapdata  # noqa: E402
from engine import BODY_NAMES, PICK_NAMES  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
GMAX, SZ = 64, 100
CHANNELS = ["valid", "wall", "hole", "bush", "altar", "own_spawn", "enemy_spawn", "wolf", "elk", "gem_cluster", "gold_cluster", "monolith",
			"golem", "gems", "gold", "camp_hp", "walk_us", "walk_them"]
GFEATS = FTG.FEATS + ["n_wolf", "n_elk", "n_gem", "n_gold", "n_mono", "n_golem", "respawn", "max_str"]
DECODE_BODY = {n.replace(" ", "").replace("&", "And"): i for i, n in enumerate(BODY_NAMES)}


def body_index(name):
	n = name.replace(" ", "")
	if n in DECODE_BODY:
		return DECODE_BODY[n]
	for i, b in enumerate(BODY_NAMES):
		if b.replace(" ", "").lower() == n.lower():
			return i
	raise SystemExit(f"unknown champion name in a replay summary: {name}")


def map_tensors(M, team, arche):
	C, fc, fb, fn = FT.fields(M, team)
	g = np.zeros((len(CHANNELS), SZ, SZ), np.float32)
	H, W = M.H, M.W
	g[0, :H, :W] = 1
	g[1, :H, :W] = M.walls
	g[2, :H, :W] = M.holes
	g[3, :H, :W] = M.bushes
	g[4, :H, :W] = M.altars
	g[5, :H, :W] = M.spawn[team]
	g[6, :H, :W] = M.spawn[1 - team]
	for grp in M.groups:
		for c in grp["camps"]:
			t, x, y = c
			g[7 + t, y, x] = 1
			g[13, y, x] = grp["gems"] / 100.0
			g[14, y, x] = grp["gold"] / 100.0
			g[15, y, x] = EC.camp_stats(t)[0] / 5000.0
	for ch, f in ((16, fc[team]), (17, fc[1 - team])):
		v = f.astype(np.float32) / 100.0
		v[f < 0] = 1.5
		g[ch, :H, :W] = v
	z = EH.zfeat_py(FT.compute(M, team), arche)
	return g, z


def group_arrays(M, team):
	tab = FTG.group_table(M, team)
	gf = np.zeros((GMAX, len(GFEATS)), np.float32)
	gm = np.zeros(GMAX, np.float32)
	boxes = [CP.group_box(grp) for grp in M.groups]
	gd = np.zeros((GMAX, GMAX), np.float32)
	for i in range(len(M.groups)):
		for j in range(len(M.groups)):
			gd[i, j] = CP.box_dist(boxes[i], boxes[j]) / 100.0
	for gi, grp in enumerate(M.groups):
		if gi not in tab:
			continue
		cnt = [0] * 6
		for c in grp["camps"]:
			cnt[c[0]] += 1
		gf[gi] = tab[gi] + cnt + [grp["respawn"] / 100.0, max(EC.camp_stats(c[0])[1] for c in grp["camps"]) / 100.0]
		gm[gi] = 1
	return gf, gm, gd


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/dl_data"))
	ap.add_argument("--summaries", default=os.path.join(ROOT, "experiments/results/mapintel/ladder_20261024"))
	ap.add_argument("--battery", default=os.path.join(ROOT, "experiments/results/mapintel/sim_v10/games.csv"))
	ap.add_argument("--battery-label", default="GOD v10")
	ap.add_argument("--check", action="store_true", help="build the arrays and print the sizes; no baselines, nothing written")
	a = ap.parse_args()
	names = mapdata.pool_names()
	idx = {n: i for i, n in enumerate(names)}
	arche = json.load(open(os.path.join(ROOT, "maps/catalog/archetypes.json")))
	P = PL.extend(arche, json.load(open(os.path.join(ROOT, "maps/catalog/splits.json")))["folds"], names)
	fold = np.array([P.fold_of[n] for n in names], np.int64)
	MM = {n: mapdata.load(n) for n in names}
	NM = len(names)
	grid = np.zeros((2 * NM, len(CHANNELS), SZ, SZ), np.float32)
	z = np.zeros((2 * NM, len(arche["features"])), np.float32)
	gfeat = np.zeros((2 * NM, GMAX, len(GFEATS)), np.float32)
	gmask = np.zeros((2 * NM, GMAX), np.float32)
	gdist = np.zeros((2 * NM, GMAX, GMAX), np.float32)
	for n in names:
		M = MM[n]
		if M.W > SZ or M.H > SZ or len(M.groups) > GMAX:
			sys.exit(f"{n}: larger than the {SZ} x {SZ} / {GMAX}-group padding")
		for t in (0, 1):
			mt = 2 * idx[n] + t
			grid[mt], z[mt] = map_tensors(M, t, arche)
			gfeat[mt], gmask[mt], gdist[mt] = group_arrays(M, t)
	# ladder games: opening sets, per-body next targets, heat
	t1a, t1b = [], []
	heat = np.zeros((2 * NM, 4, SZ, SZ), np.float32)
	heat_games = np.zeros(2 * NM, np.float32)
	kinds = {"hit_camp": 0, "hit_champ": 1, "capture": 2, "death": 3}
	ngames = 0
	for f in sorted(glob.glob(os.path.join(a.summaries, "*.json"))):
		S = json.load(open(f))
		if not S.get("map") or S.get("error") or S["map"] not in idx:
			continue
		ngames += 1
		mi = idx[S["map"]]
		M = MM[S["map"]]
		fc = defaultdict(dict)
		for t, g, r in S["first_capture"]:
			fc[t][g] = r
		for t in (0, 1):
			mt = 2 * mi + t
			heat_games[mt] += 1
			n = len(S["drafts"][t]) + (1 if 3 in S["drafts"][t] else 0)
			first = [g for g, _ in sorted(fc[t].items(), key=lambda kv: (kv[1], kv[0]))][:n]
			if len(first) == n and all(gmask[mt, g] for g in first):
				mask = np.zeros(GMAX, np.float32)
				mask[first] = 1
				t1a.append((mt, n, mask))
		for t, ch, kind, cells in S["heat"]:
			for x, y, c in cells:
				heat[2 * mi + t, kinds[kind], y, x] += c
		# per body: its captures in order; the next one given the previous (groups captured by anyone within their respawn are unavailable)
		caps = sorted(S["captures"], key=lambda c: c[0])
		last_cap = {}
		by_body = defaultdict(list)
		for c in caps:
			by_body[(c[1], c[2])].append(c)
		for (t, ch), seq in by_body.items():
			mt = 2 * mi + t
			for k in range(1, len(seq)):
				r, g, prev = seq[k][0], seq[k][3], seq[k - 1][3]
				if g == prev or not gmask[mt, g]:
					continue
				avail = gmask[mt].copy()
				for c in caps:
					if c[0] >= r:
						break
					if r - c[0] < M.groups[c[3]]["respawn"]:
						avail[c[3]] = 0
				avail[g] = 1
				t1b.append((mt, prev, body_index(ch), r / 2000.0, g, avail))
	heat /= np.maximum(heat_games, 1)[:, None, None, None]
	# roster battery
	t2 = []
	nm = {nn: i for i, nn in enumerate(PICK_NAMES)}
	skip = defaultdict(int)
	for r in csv.DictReader(open(a.battery)):
		if r["battery"] != "roster":
			continue
		if r["map"] not in idx:
			skip["map not in the pool: " + r["map"]] += 1
			continue
		if not r["roster_bot"] or not r["roster_opp"]:
			skip["no kept statistics (empty rosters)"] += 1
			continue
		us, them = np.zeros(12, np.float32), np.zeros(12, np.float32)
		for nn in r["roster_bot"].split("/"):
			us[nm[nn]] = 1
		for nn in r["roster_opp"].split("/"):
			them[nm[nn]] = 1
		t2.append((idx[r["map"]], 1.0 if r["side"] == "A" else -1.0, us - them, int(r["win"]), us, them))
	arrays = dict(
		maps=np.array(names), fold=fold, arch=np.array([P.labels[n] for n in names], np.int64), grid=grid, z=z, gfeat=gfeat,
		gmask=gmask, gdist=gdist,
		t1a_mt=np.array([s[0] for s in t1a], np.int64), t1a_n=np.array([s[1] for s in t1a], np.int64), t1a_first=np.array([s[2] for s in t1a]),
		t1b_mt=np.array([s[0] for s in t1b], np.int64), t1b_prev=np.array([s[1] for s in t1b], np.int64),
		t1b_champ=np.array([s[2] for s in t1b], np.int64), t1b_round=np.array([s[3] for s in t1b], np.float32),
		t1b_target=np.array([s[4] for s in t1b], np.int64), t1b_avail=np.array([s[5] for s in t1b]),
		t2_map=np.array([s[0] for s in t2], np.int64), t2_side=np.array([s[1] for s in t2], np.float32), t2_diff=np.array([s[2] for s in t2]),
		t2_win=np.array([s[3] for s in t2], np.float32), t2_us=np.array([s[4] for s in t2]), t2_them=np.array([s[5] for s in t2]),
		heat=heat, heat_games=heat_games)
	sizes = {"maps": NM, "maps_outside_catalog": len(P.added), "t1a": len(t1a), "t1b": len(t1b), "t2": len(t2), "games": ngames,
			 "maps_with_games": int((heat_games[::2] > 0).sum()), "maps_with_t2": len(set(s[0] for s in t2))}
	if skip:
		print("t2 rows skipped: " + "; ".join(f"{k}: {v}" for k, v in sorted(skip.items())))
	if a.check:
		print("check (nothing written):", json.dumps(sizes), "| grid", grid.shape, "| folds", np.bincount(fold).tolist(),
			  "| archetypes", np.bincount(arrays["arch"]).tolist())
		return
	os.makedirs(a.out, exist_ok=True)
	np.savez_compressed(os.path.join(a.out, "dataset.npz"), **arrays)
	base = baselines(arrays)
	meta = {"origin": {"grid, z, gfeat, gdist": "COMPUTED (runtime dumps, catalog; maps outside the catalog: pool.py)",
					   "t1a, t1b, heat": f"LEARNED ({ngames} ladder games: {os.path.relpath(a.summaries, ROOT)})",
					   "t2": f"SIMULATED ({a.battery_label} roster battery, both rosters forced: {os.path.relpath(a.battery, ROOT)})"},
			"maps_outside_catalog": {n: {"archetype": int(P.labels[n]), "fold": P.fold_of[n]} for n in P.added},
			"channels": CHANNELS, "gfeats": GFEATS, "zfeats": arche["features"], "body_names": BODY_NAMES, "pick_names": PICK_NAMES,
			"sizes": sizes, "baselines": base}
	json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"), indent=1)
	print(json.dumps(meta["sizes"]), json.dumps(base, indent=1))


def baselines(A):
	"""The step-6 bar on the same samples and folds (leave-maps-out)."""
	from sklearn.ensemble import HistGradientBoostingClassifier
	from sklearn.linear_model import LogisticRegression
	from sklearn.metrics import log_loss
	fold = A["fold"]
	out = {}
	# T1a
	mt, n, first = A["t1a_mt"], A["t1a_n"], A["t1a_first"]
	gf, gm = A["gfeat"], A["gmask"]
	nf = len(FTG.FEATS)

	def rows(sel):
		X, y = [], []
		for s in sel:
			for g in np.nonzero(gm[mt[s]])[0]:
				X.append(gf[mt[s], g, :nf])
				y.append(first[s, g])
		return np.array(X), np.array(y)

	sh = {"nearest": [], "forest": []}
	for k in range(5):
		tr = [s for s in range(len(mt)) if fold[mt[s] // 2] != k]
		te = [s for s in range(len(mt)) if fold[mt[s] // 2] == k]
		X, y = rows(tr)
		m = HistGradientBoostingClassifier(max_depth=FTG.GBM_DEPTH, learning_rate=FTG.GBM_LR, max_iter=FTG.GBM_TREES, early_stopping=False,
										   random_state=0).fit(X, y)
		for s in te:
			gs = np.nonzero(gm[mt[s]])[0]
			p = m.decision_function(gf[mt[s], gs, :nf])
			top = gs[np.lexsort((gs, -p))[:n[s]]]
			sh["forest"].append(first[s, top].sum() / n[s])
			near = gs[np.lexsort((gs, gf[mt[s], gs, 0]))[:n[s]]]
			sh["nearest"].append(first[s, near].sum() / n[s])
	out["t1a_topn_share"] = {k: round(float(np.mean(v)), 4) for k, v in sh.items()}
	# T1b
	mt2, prev, tgt, av = A["t1b_mt"], A["t1b_prev"], A["t1b_target"], A["t1b_avail"]
	gd = A["gdist"]

	def feats_b(s, gs):
		return np.concatenate([gf[mt2[s], gs], gd[mt2[s], prev[s], gs][:, None], np.full((len(gs), 1), A["t1b_round"][s])], 1)

	acc = {"nearest_prev": [[], []], "forest": [[], []]}
	for k in range(5):
		tr = [s for s in range(len(mt2)) if fold[mt2[s] // 2] != k]
		te = [s for s in range(len(mt2)) if fold[mt2[s] // 2] == k]
		rng = np.random.default_rng(k)
		trs = rng.choice(tr, min(len(tr), 6000), replace=False) if tr else []
		X, y = [], []
		for s in trs:
			gs = np.nonzero(av[s])[0]
			X.append(feats_b(s, gs))
			y.append((gs == tgt[s]).astype(int))
		m = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.1, max_iter=100, early_stopping=False, random_state=0).fit(np.concatenate(X), np.concatenate(y))
		for s in te:
			gs = np.nonzero(av[s])[0]
			p = m.decision_function(feats_b(s, gs))
			order = gs[np.lexsort((gs, -p))]
			acc["forest"][0].append(order[0] == tgt[s])
			acc["forest"][1].append(tgt[s] in order[:3])
			order = gs[np.lexsort((gs, gf[mt2[s], gs, 0], gd[mt2[s], prev[s], gs]))]
			acc["nearest_prev"][0].append(order[0] == tgt[s])
			acc["nearest_prev"][1].append(tgt[s] in order[:3])
	out["t1b_top1_top3"] = {k: [round(float(np.mean(v[0])), 4), round(float(np.mean(v[1])), 4)] for k, v in acc.items()}
	# T2
	mp, side, diff, win = A["t2_map"], A["t2_side"], A["t2_diff"], A["t2_win"]
	ll = {}
	for name, X in (("side_only", side[:, None]), ("M1_constant_values", np.concatenate([side[:, None], diff], 1))):
		pred = np.zeros(len(win))
		for k in range(5):
			tr, te = fold[mp] != k, fold[mp] == k
			m = LogisticRegression(C=0.03, max_iter=4000).fit(X[tr], win[tr])
			pred[te] = m.predict_proba(X[te])[:, 1]
		ll[name] = round(float(log_loss(win, pred)), 4)
	out["t2_logloss"] = ll
	# T3: camp-blur baseline correlation per map-team (no training)
	from scipy.ndimage import gaussian_filter
	cors = []
	for mt3 in range(A["grid"].shape[0]):
		camps = A["grid"][mt3, 7:13].sum(0)
		valid = A["grid"][mt3, 0] > 0
		b = gaussian_filter(camps, 2.0)
		for ch in range(4):
			h = A["heat"][mt3, ch]
			if h[valid].std() > 0 and b[valid].std() > 0:
				cors.append(np.corrcoef(b[valid], h[valid])[0, 1])
	out["t3_camp_blur_pearson"] = round(float(np.mean(cors)), 4)
	return out


if __name__ == "__main__":
	main()
