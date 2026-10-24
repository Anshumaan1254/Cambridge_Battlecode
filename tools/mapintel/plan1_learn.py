#!/usr/bin/env python3
"""Plan 1 (the opening) against the top teams' replays, per kit class (the user's change 3 of Oct 24). LEARNED validation.

    python3 -I tools/mapintel/plan1_learn.py [--summaries experiments/results/mapintel/ladder_20261024] [--out .../plan1] [--jobs 4]

For every decoded ladder team-game: the team's real roster (its draft), its first-n captured groups (n = bodies) and each body's first
captured group. Variants of plan 1 (team-relative; the first_scores() forest is refitted per archetype fold, so a map is scored by a
forest that never saw it: held out):
  compact          the current runtime plan 1 (plans.h = compact.plan1: greedy (body, group) pairs by first-target rate)
  nearest          each body in slot order takes the free group with the shortest walk to attack range
  fs_compact       the n groups first_scores() ranks highest, assigned to the bodies by the compact economy (Hungarian on eta + work:
                   walk to attack range + kill + heal trips + capture), the runtime-feasible version
  fs_catalog       the same n groups, assigned by the catalog's economy (economy.fight: solo kill rounds with the fitted constants +
                   the walk; a group a body cannot clear alone costs 10,000)
  fs_walk          the same n groups, assigned by the walk only
Scores: set share = |planned first targets & real first-n| / n; body accuracy = the share of bodies whose planned first target is the
group that body captured first (bodies that captured nothing are left out), overall and per kit class (engine.kit_class).
Writes report.md and results.json."""
import argparse, concurrent.futures as cf, glob, json, math, os, sys
from collections import defaultdict

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.ensemble import HistGradientBoostingClassifier

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compact as CP  # noqa: E402
import economy as EC  # noqa: E402
import first_targets as FTG  # noqa: E402
import mapdata  # noqa: E402
import replay_tracks as RT  # noqa: E402
from engine import pick_bodies  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
VARIANTS = ["compact", "nearest", "fs_compact", "fs_catalog", "fs_walk"]


def assign(cost):
	"""Hungarian on a bodies x groups cost matrix; returns the group column per body (ties: scipy's deterministic order)."""
	r, c = linear_sum_assignment(np.array(cost, float))
	out = [None] * len(cost)
	for i, j in zip(r, c):
		out[i] = j
	return out


def plans_for(job):
	"""All variants for the team-games of one map: job = (map, [(game key, team, picks)], first_scores per team {group: score})."""
	mp, items, fs = job
	import plans as P
	M = mapdata.load(mp)
	ctx = P.Ctx(M)
	C = [CP.Compact(M, t) for t in (0, 1)]
	E = EC.engine()
	solo = {}
	out = {}
	for key, t, picks in items:
		bodies = [b for p in picks for b in pick_bodies(p)][:CP.NSLOT]
		n = len(bodies)
		c = C[t]
		reach = [g for g in range(len(M.groups)) if c.dU[g] >= 0]
		eta = lambda b, g: max(0, c.dU[g] - E.attack_range(b))  # noqa: E731
		res = {}
		_, pl = c.plan1(picks)
		res["compact"] = [p[0][0] if p else None for p in pl]
		used, near = set(), []
		for b in bodies:
			g = min((g for g in reach if g not in used), key=lambda g: (eta(b, g), g), default=None)
			near.append(g)
			if g is not None:
				used.add(g)
		res["nearest"] = near
		top = sorted(fs[t], key=lambda g: (-fs[t][g], g))[:n]
		if len(top) < n:
			top += [g for g in sorted(reach, key=lambda g: (c.dU[g], g)) if g not in top][:n - len(top)]
		res["fs_compact"] = [top[j] for j in assign([[eta(b, g) + c.work(b, g) for g in top] for b in bodies])]
		res["fs_walk"] = [top[j] for j in assign([[eta(b, g) for g in top] for b in bodies])]
		cc = []
		for b in bodies:
			row = []
			for g in top:
				if (t, b, g) not in solo:
					r = EC.fight(M, t, [EC.Champ(b)], M.groups[g], ctx.home(t))
					tr = P.min_on(ctx.walk[t], ctx.hit[t][1 if E.attack_range(b) <= 1 else 3][g])
					solo[(t, b, g)] = (tr if tr >= 0 else 999) + (r.rounds if r.cleared else 10000)
				row.append(solo[(t, b, g)])
			cc.append(row)
		res["fs_catalog"] = [top[j] for j in assign(cc)]
		out[(key, t)] = (bodies, res)
	return mp, out


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--summaries", default=os.path.join(ROOT, "experiments/results/mapintel/ladder_20261024"))
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/plan1"))
	ap.add_argument("--jobs", type=int, default=4)
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)
	folds = json.load(open(os.path.join(ROOT, "maps/catalog/splits.json")))["folds"]
	fold_of = {n: k for k, f in enumerate(folds) for n in f}
	games = defaultdict(list)
	for f in sorted(glob.glob(os.path.join(a.summaries, "*.json"))):
		S = json.load(open(f))
		if S.get("map") and not S.get("error"):
			games[S["map"]].append(S)
	tables = {mp: [FTG.group_table(mapdata.load(mp), t) for t in (0, 1)] for mp in games}
	# truth per team-game
	truth = {}
	for mp, gs in games.items():
		for S in gs:
			for t in (0, 1):
				picks = [p for p in S["drafts"][t] if isinstance(p, int)]
				n = len([b for p in picks for b in pick_bodies(p)])
				caps = sorted([c for c in S["captures"] if c[1] == t and c[3] is not None], key=lambda c: c[0])
				first_n, body_first = [], {}
				for c in caps:
					if c[3] not in first_n:
						first_n.append(c[3])
					bt = RT.body_type(c[2])
					body_first.setdefault(bt, c[3])
				if len(first_n) >= n and picks:
					truth[(S["replay"], t)] = (mp, picks, set(first_n[:n]), body_first)
	# out-of-fold first_scores per map-team (the forest of first_targets.py, refitted without the map's fold)
	samples = defaultdict(list)
	for (key, t), (mp, picks, fset, _) in truth.items():
		samples[mp].append((t, fset))
	fs = {}
	for k in range(5):
		trm = [m for m in games if fold_of[m] != k]
		X, y = [], []
		for m in trm:
			for t, fset in samples[m]:
				for g, x in tables[m][t].items():
					X.append(x)
					y.append(1 if g in fset else 0)
		gm = HistGradientBoostingClassifier(max_depth=FTG.GBM_DEPTH, learning_rate=FTG.GBM_LR, max_iter=FTG.GBM_TREES, early_stopping=False,
											random_state=0).fit(np.array(X, float), np.array(y))
		for m in games:
			if fold_of[m] == k:
				fs[m] = []
				for t in (0, 1):
					gs_ = list(tables[m][t])
					sc = gm.decision_function(np.array([tables[m][t][g] for g in gs_], float)) if gs_ else []
					fs[m].append({g: float(s) for g, s in zip(gs_, sc)})
	jobs = []
	for mp in sorted(games):
		items = [(key, t, picks) for (key, t), (m, picks, _, _) in truth.items() if m == mp]
		jobs.append((mp, items, fs[mp]))
	with cf.ProcessPoolExecutor(a.jobs) as ex:
		res = dict(ex.map(plans_for, jobs))
	E = EC.engine()
	agg = {v: {"set": [], "body": [], "cls": defaultdict(list), "maptype": defaultdict(list)} for v in VARIANTS}
	for (key, t), (mp, picks, fset, bfirst) in truth.items():
		bodies, r = res[mp][(key, t)]
		n = len(bodies)
		for v in VARIANTS:
			plan = r[v]
			agg[v]["set"].append(len({g for g in plan if g is not None} & fset) / n)
			for b, g in zip(bodies, plan):
				if b in bfirst:
					hit = 1.0 if g == bfirst[b] else 0.0
					agg[v]["body"].append(hit)
					agg[v]["cls"][E.kit_class(b)].append(hit)
	R = {v: {"set_share": float(np.mean(d["set"])), "body_accuracy": float(np.mean(d["body"])), "bodies": len(d["body"]),
			 "per_class": {c: [float(np.mean(x)), len(x)] for c, x in sorted(d["cls"].items())}} for v, d in agg.items()}
	R["_team_games"] = len(truth)
	json.dump(R, open(os.path.join(a.out, "results.json"), "w"), indent=1)
	cls = sorted({c for v in VARIANTS for c in R[v]["per_class"]})
	L = ["# Plan 1 against the top teams' openings (held out: first_scores refitted per archetype fold)\n",
		 f"{len(truth)} team-games on {len(games)} maps, each with its real roster. Set share = planned first targets among the team's first n "
		 "captured groups; body accuracy = planned first target = the group that body captured first.\n",
		 "| variant | set share | body accuracy | " + " | ".join(cls) + " |", "|---|---|---|" + "---|" * len(cls)]
	for v in VARIANTS:
		L.append(f"| {v} | {R[v]['set_share']:.3f} | {R[v]['body_accuracy']:.3f} | " + " | ".join(
			f"{R[v]['per_class'].get(c, [float('nan'), 0])[0]:.3f} ({R[v]['per_class'].get(c, [0, 0])[1]})" for c in cls) + " |")
	open(os.path.join(a.out, "report.md"), "w").write("\n".join(L) + "\n")
	print("\n".join(L))


if __name__ == "__main__":
	main()
