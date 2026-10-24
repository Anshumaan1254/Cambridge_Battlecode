#!/usr/bin/env python3
"""The economy model's free constants fitted to the top teams' replays (MAPAnalysis.md 5.3c; the user's change 2 of Oct 24). LEARNED.

    python3 -I tools/mapintel/econ_learn.py measure [--tracks mapintel_work/tracks]          # step 1: what the top teams do
    python3 -I tools/mapintel/econ_learn.py evaluate NAME [k=v ...] [--jobs 4]                # the model with a constant set, on 40 maps
    python3 -I tools/mapintel/econ_learn.py fit [--jobs 4]                                    # step 2: the fit + the before / after report
Output: experiments/results/mapintel/economy/ (measured.json, eval_<NAME>.json, constants.json = the fitted set that economy.econ()
reads, report.md).

Measured from the tracks (replay_tracks.py; every rule team-relative, BFS fields of features.fields):
  retreat     the health fraction (hp / max hp) of a body when it breaks off hitting a living group with no enemy within 12 tiles, with
              less than 15 gems carried, is home (a spawn tile) or recalling within 20 rounds and hits the same group again within 80:
              a heal trip mid-fight. The model leaves a fight below
              retreat x max hp (economy.fight), so the median is the retreat line; the heal-trip rule follows (usable 1 - retreat).
  heal_frac   after a capture with less than 15 gems carried (no bank motive), the next action within 25 rounds: home / recall first
              (heal) or a hit on another group first (go on); a logistic P(heal | health fraction): the health where it is 0.5.
  shop_gold   the unspent gold before a shop visit that follows the body's recall (within 8 rounds) with an empty bag: the model recalls
              to shop at this much gold (median).
  bank sizes  every bank event's gems (the target of bank_bag, which the model fits: it banks at >= bank_bag, so its banks are larger).
  gold weight the top teams' choice of the next group: a logistic over (group, previous group) rows on gems, gold, the walk from the
              previous group, log walk, the group's total camp health and the heavy flag (the next-target samples of dl/make_dataset.py); the ratio of the gold to the gems coefficient.
  kill time   per group kill (living -> dead) with 1 or 2 attackers of one team: rounds from the first damage to the death.
Evaluated per constant set (plans.Planner via plans.pace, the catalog's reference rosters, team A): the unopposed pace vs the real
finish (Spearman over the 40 maps; per map type the median real / model ratio: objective = monolith + golem gem share >= 0.3,
many-cluster = 30+ groups, other), the model's first-capture round per group vs the real median (Spearman, pooled), the model's
bank sizes vs the real ones (median per map, log ratio), the model's solo / pair kill time vs the real one (median log ratio)."""
import argparse, concurrent.futures as cf, glob, json, math, os, statistics, sys
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as EC  # noqa: E402
import features as FT  # noqa: E402
import mapdata  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "experiments/results/mapintel/economy")
KEYS = ["retreat", "heal_frac", "bank_bag", "shop_gold", "gold_w", "pace_gold_w", "dmg_mult"]


def cheb(a, b):
	return max(abs(int(a[0]) - int(b[0])), abs(int(a[1]) - int(b[1])))


def measure_game(T, fc, ctx_spawn):
	pos, alive, hp, mx, bag, gold, chp = T["pos"], T["alive"], T["hp"], T["maxhp"], T["bag"], T["gold"], T["chp"]
	bteam, cgroup = T["bteam"], T["cgroup"]
	R, B = alive.shape
	out = {"retreat": [], "heal": [], "shop": [], "bank": [int(x) for x in T["ev_bank"][:, 2]], "kill": []}
	camp_at = {(int(x), int(y)): int(g) for x, y, g in zip(T["cx"], T["cy"], cgroup) if g >= 0}
	gcamps = defaultdict(list)
	for ci, g in enumerate(cgroup):
		if g >= 0:
			gcamps[int(g)].append(ci)
	ghp = {g: chp[:, cs].sum(1) for g, cs in gcamps.items()}
	gmax = {g: chp[0, cs].sum() for g, cs in gcamps.items()}
	recall = defaultdict(set)
	for r, b in T["ev_recall"]:
		recall[int(b)].add(int(r))
	hits = defaultdict(list)
	hits_g = defaultdict(lambda: defaultdict(set))  # group -> round -> bodies
	for row in list(T["ev_attack"]) + [r_[:4] for r_ in T["ev_cast"]]:
		g = camp_at.get((int(row[2]), int(row[3])))
		if g is not None:
			hits[int(row[1])].append((int(row[0]), g))
			hits_g[g][int(row[0])].add(int(row[1]))
	home = lambda b, r: fc[int(bteam[b])][int(pos[r, b, 1]), int(pos[r, b, 0])] == 0  # noqa: E731
	frac = lambda b, r: float(hp[r, b]) / max(1, float(mx[r, b]))  # noqa: E731

	def enemy_near(b, r, d=12):
		return any(alive[r, e] and bteam[e] != bteam[b] and cheb(pos[r, e], pos[r, b]) <= d for e in range(B))

	# retreat line: a heal trip mid-fight
	for b, hl in hits.items():
		hl.sort()
		eps = []
		for r, g in hl:
			if eps and eps[-1][0] == g and r - eps[-1][2] <= 3:
				eps[-1][2] = r
			else:
				eps.append([g, r, r])
		for g, r0, r1 in eps:
			if r1 + 21 >= R or ghp[g][r1 + 1] <= 0 or any(enemy_near(b, r) for r in range(max(1, r1 - 2), r1 + 1)):
				continue
			if any(g2 == g and r1 < r2 <= r1 + 5 for r2, g2 in hl):
				continue
			went = any(alive[r, b] and home(b, r) for r in range(r1 + 1, r1 + 21)) or any(x in recall[b] for x in range(r1, r1 + 21))
			back = any(g2 == g and r1 + 5 < r2 <= r1 + 80 for r2, g2 in hl)  # a heal trip: home, then the same group again
			if went and back and alive[r1 + 1:r1 + 21, b].all() and bag[r1, b] < 15:
				out["retreat"].append(frac(b, r1))
	# heal between jobs: after a capture with a small bag
	for r, b, g, gems in T["ev_capture"]:
		r, b = int(r), int(b)
		if r + 26 >= R or bag[r, b] >= 15 or not alive[r:r + 26, b].all():
			continue
		nxt = None
		for x in range(r + 1, r + 26):
			if x in recall[b] or home(b, x):
				nxt = 1
				break
			if any(x == r2 and g2 != g for r2, g2 in hits[b]):
				nxt = 0
				break
		if nxt is not None:
			out["heal"].append((frac(b, r), nxt))
	# shop gold after a recall with an empty bag
	seen = set()
	for r, b in T["ev_shop"]:
		r, b = int(r), int(b)
		if (r, b) in seen or r < 10:
			continue
		seen.add((r, b))
		if alive[r - 9:r, b].all() and any(x in recall[b] for x in range(r - 8, r)) and bag[r - 1, b] == 0:
			out["shop"].append(int(gold[r - 1, b]))
	# kill durations
	for g, h in ghp.items():
		dead = h <= 0
		damaged = h < gmax[g]
		r = 1
		while r < R:
			if dead[r] or not damaged[r]:
				r += 1
				continue
			r0 = r
			while r < R and not dead[r] and h[r] < gmax[g]:
				r += 1
			if r >= R or not dead[r]:
				continue
			bodies = set()
			for x in range(r0 - 1, r + 1):
				bodies |= hits_g[g].get(x, set())
			teams = {int(bteam[b]) for b in bodies}
			if 1 <= len(bodies) <= 2 and len(teams) == 1:
				out["kill"].append((g, int(teams.pop()), sorted(int(T["btype"][b]) for b in bodies), r - r0 + 1))
	return out


def measure(a):
	files = sorted(glob.glob(os.path.join(a.tracks, "*.npz")))
	fields = {}
	agg = {"retreat": [], "heal": [], "shop": [], "bank": [], "bank_map": defaultdict(list), "kill": defaultdict(list)}
	for i, f in enumerate(files):
		T = dict(np.load(f))
		mp = str(T["map"])
		if mp not in fields:
			M = mapdata.load(mp)
			fields[mp] = FT.fields(M, 0)[1]
		o = measure_game(T, fields[mp], None)
		agg["retreat"] += o["retreat"]
		agg["heal"] += o["heal"]
		agg["shop"] += o["shop"]
		agg["bank"] += o["bank"]
		agg["bank_map"][mp] += o["bank"]
		for g, t, types, d in o["kill"]:
			agg["kill"][f"{mp}|{g}|{t}|{','.join(map(str, types))}"].append(d)
		if (i + 1) % 100 == 0:
			print(f"{i + 1} / {len(files)} games", flush=True)
	from sklearn.linear_model import LogisticRegression
	h = np.array(agg["heal"], float)
	lr = LogisticRegression(C=100.0).fit(h[:, :1], h[:, 1])
	heal_frac = float(-lr.intercept_[0] / lr.coef_[0][0]) if lr.coef_[0][0] != 0 else float("nan")
	# gold weight from the next-target choices (dl/make_dataset.py's samples)
	D = np.load(os.path.join(ROOT, "experiments/results/mapintel/dl_data/dataset.npz"))
	gf, gd = D["gfeat"], D["gdist"]
	X, y = [], []
	rng = np.random.default_rng(0)
	for s in rng.choice(len(D["t1b_mt"]), min(12000, len(D["t1b_mt"])), replace=False):
		mt, pv, tg = D["t1b_mt"][s], D["t1b_prev"][s], D["t1b_target"][s]
		for g in np.nonzero(D["t1b_avail"][s])[0]:
			d = 100.0 * gd[mt, pv, g]
			X.append([gf[mt, g, 4], gf[mt, g, 5], d, math.log1p(d), gf[mt, g, 7], gf[mt, g, 10]])  # gems, gold, walk, log walk, health, heavy
			y.append(1 if g == tg else 0)
	X = np.array(X)
	cl = LogisticRegression(C=1.0, max_iter=3000).fit(X / X.std(0), np.array(y))
	coef = cl.coef_[0] / X.std(0)
	gold_w = float(coef[1] / coef[0]) if coef[0] > 0 else float("nan")
	ret = np.array(agg["retreat"])
	J = {"origin": "LEARNED (599 current-patch top-team replays)",
		 "retreat": {"n": len(ret), "median": float(np.median(ret)), "q25": float(np.quantile(ret, 0.25)), "q75": float(np.quantile(ret, 0.75))},
		 "heal_frac": {"n": len(h), "logistic_p50": heal_frac, "heal_share": float(h[:, 1].mean()),
					   "median_hp_heal": float(np.median(h[h[:, 1] == 1, 0])) if (h[:, 1] == 1).any() else None,
					   "median_hp_go_on": float(np.median(h[h[:, 1] == 0, 0])) if (h[:, 1] == 0).any() else None},
		 "shop_gold": {"n": len(agg["shop"]), "median": float(np.median(agg["shop"])), "q25": float(np.quantile(agg["shop"], 0.25)),
					   "q75": float(np.quantile(agg["shop"], 0.75))},
		 "bank": {"n": len(agg["bank"]), "median": float(np.median(agg["bank"])), "q25": float(np.quantile(agg["bank"], 0.25)),
				  "q75": float(np.quantile(agg["bank"], 0.75)), "per_map_median": {m: float(np.median(v)) for m, v in agg["bank_map"].items()}},
		 "gold_weight": {"choices": int(sum(y)), "coef_gems": float(coef[0]), "coef_gold": float(coef[1]), "gold_per_gem": gold_w},
		 "kill": {k: v for k, v in agg["kill"].items()}}
	os.makedirs(OUT, exist_ok=True)
	json.dump(J, open(os.path.join(OUT, "measured.json"), "w"), indent=1)
	print(json.dumps({k: v for k, v in J.items() if k not in ("kill", "bank")}, indent=1))
	print("bank", {k: v for k, v in J["bank"].items() if k != "per_map_median"}, "kill episodes", sum(len(v) for v in J["kill"].values()))


def map_type(M):
	F = dict(zip(FT.NAMES, FT.compute(M, 0)))
	if F["n_gem_cluster"] + F["n_gold_cluster"] >= 60:
		return "many-cluster"
	return "objective" if F["mono_golem_gem_share"] >= 0.3 else "other"


def _eval_map(job):
	mp, params, combos = job
	import catalog as CT
	import plans as P
	EC.econ().update(params)
	M = mapdata.load(mp)
	ctx = P.Ctx(M)
	R = json.load(open(os.path.join(ROOT, "tools/mapintel/data/battery_rosters.json")))
	out = {"map": mp, "type": map_type(M), "pace": [], "first": {}, "banks": [], "kill": {}}
	for ref in CT.reference_rosters(mp, M.team_size, R):
		Pl = P.Planner(ctx, 0, ref["picks"], gold_w=EC.econ()["pace_gold_w"])
		res = Pl.run(until=2000, target=int(EC.settings()["winning_gems"]))
		out["pace"].append(res["pace"] if res["pace"] is not None else 2000)
		for body in res["plan"]:
			for st in body:
				if st.get("do") == "farm":
					g = st["group"]
					out["first"][g] = min(out["first"].get(g, 10 ** 9), st["captured"])
				elif st.get("do") == "bank":
					out["banks"].append(st["gems"])
	for key in combos:
		_, g, t, types = key.split("|")
		r = EC.fight(M, int(t), [EC.Champ(int(b)) for b in types.split(",")], M.groups[int(g)], ctx.home(int(t)))
		out["kill"][key] = r.rounds if r.cleared else None
	return out


def contest_rows():
	"""Per map: (gap, own captures, their captures) per group and team from the ladder summaries (gap as in plans.contest_share)."""
	import compact as CP
	rows = defaultdict(list)
	for f in sorted(glob.glob(os.path.join(ROOT, "experiments/results/mapintel/ladder_20261024/*.json"))):
		S = json.load(open(f))
		if not S.get("map") or S.get("error"):
			continue
		rows[S["map"]].append(S)
	out = {}
	for mp, gs in rows.items():
		M = mapdata.load(mp)
		C = [CP.Compact(M, t) for t in (0, 1)]
		band, _ = C[0].contested()
		cnt = defaultdict(lambda: [0, 0])
		for S in gs:
			for c in S["captures"]:
				if c[3] is not None:
					cnt[c[3]][c[1]] += 1
		r = []
		for g in range(len(M.groups)):
			for t in (0, 1):
				if C[t].dU[g] < 0 or cnt[g][0] + cnt[g][1] == 0:
					continue
				gap = 9.0 if C[t].dE[g] < 0 else max(-9.0, min(9.0, (C[t].dE[g] - C[t].dU[g]) / band))
				r.append((gap, cnt[g][t], cnt[g][1 - t]))
		out[mp] = r
	return out


def contest_fit(rows, maps):
	from sklearn.linear_model import LogisticRegression
	X, y, w = [], [], []
	for m in maps:
		for gap, own, other in rows[m]:
			X += [[gap], [gap]]
			y += [1, 0]
			w += [own, other]
	m_ = LogisticRegression(C=1e6, max_iter=2000).fit(np.array(X), np.array(y), sample_weight=np.array(w, float))
	return {"a": float(m_.intercept_[0]), "b": float(m_.coef_[0][0])}


def evaluate(name, params, jobs, verbose=True):
	"""The model with this constant set (missing keys = economy.ECON_DEFAULT) against the real targets."""
	import validate_ladder as VL
	full = dict(EC.ECON_DEFAULT, **params)
	meas = json.load(open(os.path.join(OUT, "measured.json")))
	games = defaultdict(list)
	for f in sorted(glob.glob(os.path.join(ROOT, "experiments/results/mapintel/ladder_20261024/*.json"))):
		S = json.load(open(f))
		if S.get("map") and not S.get("error"):
			games[S["map"]].append(S)
	finish = {m: statistics.median([VL.finish_round(S) for S in gs]) for m, gs in games.items()}
	first_real = defaultdict(list)
	for m, gs in games.items():
		for S in gs:
			for t, g, r in S["first_capture"]:
				if t == 0:
					first_real[(m, g)].append(r)
	combos = defaultdict(list)
	for k, v in meas["kill"].items():
		if len(v) >= 3:
			combos[k.split("|")[0]].append((len(v), k))
	maps = mapdata.official_names()
	per_map = {m: dict(full) for m in maps}
	if full.get("contest") == "cv":  # out of fold: each map's coefficients fitted without its fold's maps
		folds = json.load(open(os.path.join(ROOT, "maps/catalog/splits.json")))["folds"]
		rows = contest_rows()
		for k, fm_ in enumerate(folds):
			co = contest_fit(rows, [m for m in rows if m not in fm_])
			for m in fm_:
				per_map[m]["contest"] = co
	jobs_ = [(m, per_map[m], [k for _, k in sorted(combos[m], reverse=True)[:60]]) for m in maps]
	with cf.ProcessPoolExecutor(jobs) as ex:
		res = list(ex.map(_eval_map, jobs_))
	mp_pace = {r["map"]: statistics.median(r["pace"]) if r["pace"] else 2000 for r in res}
	ok = [m for m in maps if m in finish]
	rho = spearmanr([mp_pace[m] for m in ok], [finish[m] for m in ok])[0]
	types = defaultdict(list)
	for r in res:
		if r["map"] in finish:
			types[r["type"]].append(finish[r["map"]] / max(1, mp_pace[r["map"]]))
	fm, fr = [], []
	per_map_fc = []
	for r in res:
		a_, b_ = [], []
		for g, rr in r["first"].items():
			if (r["map"], g) in first_real:
				a_.append(rr)
				b_.append(statistics.median(first_real[(r["map"], g)]))
		fm += a_
		fr += b_
		if len(a_) >= 4:
			per_map_fc.append(spearmanr(a_, b_)[0])
	bank_err = []
	for r in res:
		real = meas["bank"]["per_map_median"].get(r["map"])
		if real and r["banks"]:
			bank_err.append(math.log(statistics.median(r["banks"]) / real))
	kl = []
	for r in res:
		for k, v in r["kill"].items():
			if v:
				kl.append(math.log(v / statistics.median(meas["kill"][k])))
	ratio_all = statistics.median([finish[m] / max(1, mp_pace[m]) for m in ok])
	E = {"name": name, "constants": full, "pace_spearman": float(rho), "real_over_model_median": ratio_all,
		 "per_type": {t: {"maps": len(v), "real_over_model_median": float(np.median(v)),
						  "bias_vs_all": float(np.median(v) / ratio_all)} for t, v in sorted(types.items())},
		 "first_capture_spearman_pooled": float(spearmanr(fm, fr)[0]), "first_capture_spearman_per_map": float(np.mean(per_map_fc)),
		 "first_capture_groups": len(fm), "bank_log_ratio_median": float(np.median(bank_err)), "bank_abs_log_ratio_median": float(np.median(np.abs(bank_err))),
		 "kill_log_ratio_median": float(np.median(kl)), "kill_abs_log_ratio_median": float(np.median(np.abs(kl))), "kill_combos": len(kl),
		 "model_bank_median": float(np.median([b for r in res for b in r["banks"]])), "model_pace": mp_pace}
	os.makedirs(OUT, exist_ok=True)
	json.dump(E, open(os.path.join(OUT, f"eval_{name}.json"), "w"), indent=1)
	if verbose:
		print(f"{name}: pace Spearman {rho:.3f}; per type real / model " + ", ".join(f"{t} {v['real_over_model_median']:.2f}" for t, v in E["per_type"].items())
			  + f"; first capture Spearman {E['first_capture_spearman_pooled']:.3f} (per map {E['first_capture_spearman_per_map']:.3f}); bank log ratio "
			  f"{E['bank_log_ratio_median']:+.2f} (model median {E['model_bank_median']:.0f}); kill log ratio {E['kill_log_ratio_median']:+.2f}", flush=True)
	return E


CHOSEN = {"retreat": 0.52, "heal_frac": 0.9, "bank_bag": 20, "shop_gold": 115, "gold_w": 0.02, "pace_gold_w": 0.02, "dmg_mult": 1.3}
WHY = {"retreat": "measured: median health at a mid-fight heal trip (3,109 trips); also the best pace Spearman of the grid",
	   "heal_frac": "fitted (grid 0.3-0.95): the top teams go home after a capture 59% of the time at a median health of 0.93, so health does "
					"not separate the decision; 0.9 keeps the model going home after most jobs",
	   "bank_bag": "fitted to the real bank sizes (median 26 gems over 24,945 banks): bag 20 gives the model's median bank 28",
	   "shop_gold": "measured: median unspent gold at a shop visit after a recall with an empty bag (18,572 visits)",
	   "gold_w": "measured: the top teams' next-group choice (12,000 choices; gems, gold, walk, health, heavy) values 1 gold as 0.020 gems",
	   "pace_gold_w": "the same measurement (it equals the old default)",
	   "dmg_mult": "fitted to the real kill durations (1-2 attacker kills, 43,782 episodes): 1.3 makes the model's median kill time equal",
	   "contest": "LEARNED logistic of the team's capture share of a group on (their walk - ours) / band, all ladder captures; the pace check "
				  "uses out-of-fold coefficients"}


def fit(a):
	before = evaluate("before", {}, a.jobs)
	after = evaluate("after", dict(CHOSEN, contest="cv"), a.jobs)
	noopp = evaluate("after_unopposed", dict(CHOSEN), a.jobs)
	co = contest_fit(contest_rows(), mapdata.official_names())
	J = {"origin": "LEARNED (599 current-patch top-team replays; tools/mapintel/econ_learn.py)", "constants": dict(CHOSEN, contest=co),
		 "why": WHY, "check": {k: {kk: E[kk] for kk in ("pace_spearman", "per_type", "first_capture_spearman_pooled", "bank_log_ratio_median",
														   "kill_log_ratio_median")} for k, E in (("before", before), ("after", after), ("after_unopposed", noopp))}}
	json.dump(J, open(os.path.join(OUT, "constants.json"), "w"), indent=1)
	meas = json.load(open(os.path.join(OUT, "measured.json")))
	L = ["# Economy constants fitted to the top teams' replays\n",
		 "| constant | before | after | evidence |", "|---|---|---|---|"]
	for k in CHOSEN:
		L.append(f"| {k} | {EC.ECON_DEFAULT[k]} | {CHOSEN[k]} | {WHY[k]} |")
	L.append(f"| contest | none (unopposed) | a {co['a']:.3f}, b {co['b']:.3f} | {WHY['contest']} |")
	L += ["", "Checks (the catalog's pace model on the 40 maps, the reference rosters; real = 599 ladder games):\n",
		  "| set | pace Spearman | real / model: many-cluster | objective | other | first-capture Spearman | bank log ratio | kill log ratio |",
		  "|---|---|---|---|---|---|---|---|"]
	for name, E in (("before (defaults)", before), ("after, unopposed", noopp), ("after (+ contest, out of fold)", after)):
		pt = E["per_type"]
		L.append(f"| {name} | {E['pace_spearman']:.3f} | {pt['many-cluster']['real_over_model_median']:.2f} | {pt['objective']['real_over_model_median']:.2f} | "
				 f"{pt['other']['real_over_model_median']:.2f} | {E['first_capture_spearman_pooled']:.3f} | {E['bank_log_ratio_median']:+.2f} | {E['kill_log_ratio_median']:+.2f} |")
	L += ["", "Map types: many-cluster = 60+ gem and gold clusters (10 maps), objective = monolith + golem gem share >= 0.3 (18), other (12). "
		  "real / model = median over the type's maps of the real finish over the model's pace; a type is biased when it differs from the others.",
		  f"Measured: retreat median {meas['retreat']['median']:.2f} (q25 {meas['retreat']['q25']:.2f}, q75 {meas['retreat']['q75']:.2f}); after a capture "
		  f"home {100 * meas['heal_frac']['heal_share']:.0f}% (median health {meas['heal_frac']['median_hp_heal']:.2f} home, {meas['heal_frac']['median_hp_go_on']:.2f} on); "
		  f"shop gold median {meas['shop_gold']['median']:.0f}; bank size median {meas['bank']['median']:.0f} (q25 {meas['bank']['q25']:.0f}, q75 {meas['bank']['q75']:.0f}); "
		  f"gold per gem {meas['gold_weight']['gold_per_gem']:.3f}."]
	open(os.path.join(OUT, "report.md"), "w").write("\n".join(L) + "\n")
	print("\n".join(L))


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("cmd", choices=["measure", "evaluate", "fit"])
	ap.add_argument("rest", nargs="*")
	ap.add_argument("--tracks", default=os.path.join(ROOT, "mapintel_work/tracks"))
	ap.add_argument("--jobs", type=int, default=4)
	a = ap.parse_args()
	if a.cmd == "measure":
		measure(a)
	elif a.cmd == "fit":
		fit(a)
	elif a.cmd == "evaluate":
		name = a.rest[0]
		params = {}
		for kv in a.rest[1:]:
			k, v = kv.split("=")
			params[k] = v if k == "contest" else float(v) if k in ("retreat", "heal_frac", "gold_w", "pace_gold_w", "dmg_mult") else int(v)
		evaluate(name, params, a.jobs)


if __name__ == "__main__":
	main()
