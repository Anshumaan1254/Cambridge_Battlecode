#!/usr/bin/env python3
"""The map catalog of MAPAnalysis.md 5.3 (step 3 output). COMPUTED (engine + map); the pace columns are the economy model's estimates.

    python3 -I tools/mapintel/catalog.py [--maps NAME,NAME|all] [--out maps/catalog] [--no-pace]

Per map:
  maps/catalog/<map>.json   basics, altars with approach tiles and per-team access (plan 2), banking cases and the tiebreak rule, bank
                            routes per group, groups with values / ETAs per team / contested flags / priority / first contact (plan 3),
                            objectives (monoliths, golems: ring tiles, safe tiles, coalition kill time), conflict geometry (lanes,
                            chokepoints, corridor width, route load, ambush bushes, first-contact point), plan 1 per reference roster
                            (opening assignments by body slot), the unopposed pace per reference roster, plan-4 thresholds,
                            per (champion, group): safe attack tiles and solo kill time / damage / heal trips
  maps/catalog/<map>.npz    per-tile layers ([y, x]): terrain, spawns, distance fields per team (walk, after clearing, dash), camp threat,
                            route load, corridor width, the per-reach hit and safe layers per group (hit_R / safe_R: [G, H, W])
  maps/catalog/maps.csv     one row per map: the features (core = computable at runtime by features.h, ext = offline only)
Reference rosters: the LEARNED rosters strong teams drafted on that map (tools/mapintel/data/battery_rosters.json; up to 2) and one COMPUTED
balanced roster for its team size."""
import argparse
import csv
import json
import math
import os
import sys
import time

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as EC  # noqa: E402
import geometry as G  # noqa: E402
import mapdata  # noqa: E402
import plans as P  # noqa: E402
import tiles as T  # noqa: E402
from engine import PICK_NAMES, pick_bodies  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CAMP_NAMES = ["wolf", "elk", "gem_cluster", "gold_cluster", "monolith", "golem"]


def conflict(ctx):
	"""Lanes (vertex-disjoint paths between the spawns), chokepoints (articulation points on routes), corridor width (distance to the
	nearest blocked tile, Chebyshev), route load (value-weighted count of spawn-to-group shortest paths through each tile, both teams),
	bushes next to loaded tiles (ambush risk)."""
	import networkx as nx
	M = ctx.M
	walk = ctx.clear[0] | ctx.clear[1] | M.spawn[0] | M.spawn[1]
	H, W = M.H, M.W
	width = ndimage.distance_transform_cdt(walk, metric="chessboard").astype(np.int16)
	# route load
	load = np.zeros((H, W), np.float32)
	for t in (0, 1):
		ds = ctx.walk_clear[t]
		for g in range(len(M.groups)):
			f = ctx.loc_field(("group", g), t)
			D = P.dist_to_tiles(ds, ctx.gtiles[g])
			if D < 0:
				continue
			on = (ds >= 0) & (f >= 0) & (ds + f <= D + 1)
			load[on] += ctx.value[g] / max(1, on.sum()) * 10
	# lanes and chokepoints on the walking graph (both spawns' tiles included)
	Gr = nx.Graph()
	idx = lambda x, y: y * W + x  # noqa: E731
	ys, xs = np.nonzero(walk)
	for y, x in zip(ys, xs):
		for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
			X, Y = x + dx, y + dy
			if 0 <= X < W and 0 <= Y < H and walk[Y, X]:
				Gr.add_edge(idx(x, y), idx(X, Y))
	art = set(nx.articulation_points(Gr)) if Gr.number_of_nodes() else set()
	on_route = load > 0
	chokes = [[int(n % W), int(n // W)] for n in art if on_route[n // W, n % W] and not M.spawn[0][n // W, n % W] and not M.spawn[1][n // W, n % W]]
	# vertex-disjoint paths between the spawn regions (node splitting), capped at 64
	lanes = None
	try:
		D = nx.DiGraph()
		for u, v in Gr.edges():
			D.add_edge((u, "o"), (v, "i"), capacity=1)
			D.add_edge((v, "o"), (u, "i"), capacity=1)
		for u in Gr.nodes():
			D.add_edge((u, "i"), (u, "o"), capacity=1)
		for y, x in zip(*np.nonzero(M.spawn[0])):
			D.add_edge("S", (idx(x, y), "i"), capacity=64)
		for y, x in zip(*np.nonzero(M.spawn[1])):
			D.add_edge((idx(x, y), "o"), "T", capacity=64)
		lanes = int(min(64, nx.maximum_flow_value(D, "S", "T")))
	except Exception:
		lanes = None
	# ambush: bushes within 2 of a loaded route tile
	busy = G.chebyshev_disk(load >= np.percentile(load[load > 0], 75) if (load > 0).any() else load > 0, 2)
	ambush = M.bushes & busy
	return {"lanes": lanes, "chokepoints": sorted(chokes), "corridor_width_mean": round(float(width[on_route].mean()) if on_route.any() else 0.0, 2),
			"corridor_width_min_on_routes": int(width[on_route].min()) if on_route.any() else 0, "ambush_bushes": int(ambush.sum())}, width, load


def objectives(ctx, roster_bodies, team=0):
	M = ctx.M
	out = []
	for g, grp in enumerate(M.groups):
		types = [c[0] for c in grp["camps"]]
		if not any(t in (4, 5) for t in types):
			continue
		rng = max(EC.camp_stats(t)[2] for t in types)
		ring = []
		for (x, y) in ctx.gtiles[g]:
			for dy in range(-(rng + 1), rng + 2):
				for dx in range(-(rng + 1), rng + 2):
					if max(abs(dx), abs(dy)) == rng + 1 and EC.standable(M, team, x + dx, y + dy):
						ring.append((x + dx, y + dy))
		ring = sorted(set(ring))
		r = EC.fight(M, team, [EC.Champ(b) for b in roster_bodies], grp, ctx.home(team))
		out.append({"group": grp["id"], "kinds": sorted({CAMP_NAMES[t] for t in types}), "gems": grp["gems"], "gold": grp["gold"],
					"range": rng, "ring_tiles": len(ring), "safe_area_tiles": int(ctx.hit[team][5][g].sum()),
					"team_kill_rounds": r.rounds if r.cleared else None, "team_kill_trips": int(sum(r.trips)),
					"dist": [P.min_on(ctx.walk_clear[t], ctx.gmask[g]) for t in (0, 1)]})
	return out


def reference_rosters(name, team_size, R):
	ent = R["maps"].get(name, {}).get("rosters", [])
	learned = [r for r in ent if r["origin"] == "LEARNED"][:2]
	comp = [r for r in ent if r["origin"] == "COMPUTED"][:1]
	return [{"picks": r["picks"], "names": r["names"], "origin": r["origin"]} for r in learned + comp]


def build_map(name, R, do_pace=True, outdir=None):
	t0 = time.time()
	M = mapdata.load(name)
	ctx = P.Ctx(M)
	E = EC.engine()
	L, per = T.build(M)
	p2 = P.plan2(ctx)
	p3 = P.plan3(ctx)
	p4 = P.plan4(ctx, p3)
	cf, width, load = conflict(ctx)
	refs = reference_rosters(name, M.team_size, R)
	obj = objectives(ctx, [b for p in refs[0]["picks"] for b in pick_bodies(p)] if refs else [0, 2, 12])
	ropen, rpace = [], []
	for ref in refs:
		for t in (0, 1):
			pl = P.plan1(ctx, t, ref["picks"])
			ropen.append({"team": t, "roster": ref["names"], "origin": ref["origin"], "plan1": pl})
			if do_pace:
				pc = P.pace(ctx, t, ref["picks"])
				rpace.append({"team": t, "roster": ref["names"], "origin": ref["origin"], **pc})
	J = {
		"map": name, "origin": "COMPUTED", "fingerprint": M.fingerprint, "W": M.W, "H": M.H, "sym": ["horizontal", "vertical", "rotational180"][M.sym],
		"team_size": M.team_size, "spawn": [M.spawn_box["ally"][:4], M.spawn_box["enemy"][:4]],
		"altars": p2["altars"], "banking_cases": p2["cases"], "bank_routes": p2["bank_routes"],
		"groups": [dict(g, camps=[[CAMP_NAMES[c[0]], c[1], c[2]] for c in M.groups[i]["camps"]], respawn=M.groups[i]["respawn"]) for i, g in enumerate(p3["groups"])],
		"first_contact": p3["first_contact"], "objectives": obj, "conflict": cf, "plan4": p4,
		"reference_rosters": refs, "plan1": ropen, "pace": rpace, "per_champion_group": per,
	}
	feats = features(M, ctx, L, p2, p3, cf, obj, rpace, width, load)
	if outdir:
		os.makedirs(outdir, exist_ok=True)
		json.dump(J, open(os.path.join(outdir, name + ".json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else sorted(o) if isinstance(o, set) else str(o))
		lay = {"walls": M.walls, "holes": M.holes, "bushes": M.bushes, "altars": M.altars, "spawn_A": M.spawn[0], "spawn_B": M.spawn[1],
			   "camps": M.camps, "threat": L["threat"], "route_load": load, "corridor_width": width}
		for t in (0, 1):
			lay[f"walk_{t}"] = ctx.walk[t]
			lay[f"walk_clear_{t}"] = ctx.walk_clear[t]
			lay[f"dash_{t}"] = ctx.dash[t]
		for R_ in T.REACHES:
			lay[f"hit_{R_}"] = L[f"hit_{R_}"]
			lay[f"safe_{R_}"] = L[f"safe_{R_}"]
		np.savez_compressed(os.path.join(outdir, name + ".npz"), **lay)
	print(f"{name:22s} {time.time() - t0:5.1f}s", flush=True)
	return J, feats


def features(M, ctx, L, p2, p3, cf, obj, rpace, width, load):
	"""~80 features. 'core_*' are computable at runtime from the SDK (features.h has the same definitions); 'ext_*' are offline only."""
	f = {"map": M.name}
	area = M.W * M.H
	walk = ~(M.walls | M.holes | M.altars)
	f.update(core_w=M.W, core_h=M.H, core_area=area, core_sym=M.sym, core_team=M.team_size, core_walk_share=round(walk.mean(), 4),
			 core_wall_share=round(M.walls.mean(), 4), core_hole_share=round(M.holes.mean(), 4), core_bush_share=round(M.bushes.mean(), 4),
			 core_altars=len(M.altar_tiles), core_groups=len(M.groups))
	ct = np.zeros(6, int)
	for c in M.camp_list:
		ct[c[0]] += 1
	for k in range(6):
		f[f"core_n_{CAMP_NAMES[k]}"] = int(ct[k])
	gems = np.array([g["gems"] for g in M.groups], float)
	gold = np.array([g["gold"] for g in M.groups], float)
	resp = np.array([g["respawn"] for g in M.groups], float)
	f.update(core_gems=int(gems.sum()), core_gold=int(gold.sum()), core_gem_rate=round(float((gems / resp).sum()), 3),
			 core_gold_rate=round(float((gold / resp).sum()), 3), core_gold_per_gem=round(float(gold.sum() / max(1, gems.sum())), 3))
	dA = np.array([P.min_on(ctx.walk_clear[0], ctx.gmask[g]) for g in range(len(M.groups))], float)
	dB = np.array([P.min_on(ctx.walk_clear[1], ctx.gmask[g]) for g in range(len(M.groups))], float)
	ok = (dA >= 0) & (dB >= 0)
	ss = P.min_on(ctx.walk_clear[0], M.spawn[1]) if (ctx.walk_clear[0][M.spawn[1]] >= 0).any() else -1
	f["core_spawn_dist"] = ss
	own = ok & (dA + 6 < dB)
	mid = ok & (np.abs(dA - dB) <= 6)
	f["core_gems_own_share"] = round(float(gems[own].sum() / max(1, gems.sum())) * 2, 4)  # x2: one side's share of its half
	f["core_gems_mid_share"] = round(float(gems[mid].sum() / max(1, gems.sum())), 4)
	f["core_gold_mid_share"] = round(float(gold[mid].sum() / max(1, gold.sum())), 4)
	wv = gems / resp
	f["core_dist_gem_weighted"] = round(float((dA[ok] * wv[ok]).sum() / max(1e-9, wv[ok].sum())), 2) if ok.any() else -1
	f["core_dist_nearest_gem_group"] = int(dA[(gems > 0) & (dA >= 0)].min()) if ((gems > 0) & (dA >= 0)).any() else -1
	heavy = np.array([sum(EC.camp_stats(c[0])[0] for c in g["camps"]) for g in M.groups], float)
	f["core_hp_total"] = int(heavy.sum())
	f["core_gems_per_khp"] = round(float(gems.sum() / max(1, heavy.sum()) * 1000), 3)
	big = heavy >= 4800
	f["core_gems_heavy_share"] = round(float(gems[big].sum() / max(1, gems.sum())), 4)
	f["core_n_heavy_groups"] = int(big.sum())
	f["core_mono_golem_gem_share"] = round(float(sum(g["gems"] for g in M.groups if any(c[0] in (4, 5) for c in g["camps"])) / max(1, gems.sum())), 4)
	f["core_max_group_gems"] = int(gems.max()) if len(gems) else 0
	f["core_mean_respawn_w"] = round(float((resp * gems).sum() / max(1, gems.sum())), 2)
	da = [a["teams"][0]["walk_clear"] for a in p2["altars"] if a["teams"][0]["walk_clear"] >= 0]
	f["core_dist_nearest_altar"] = min(da) if da else -1
	f["core_altars_reachable_walk"] = sum(1 for a in p2["altars"] if a["teams"][0]["mode"] == "walk")
	f["core_altar_camp_gated"] = int(any(a["teams"][0]["camp_tile_only"] for a in p2["altars"]))
	f["core_bank_mode_A"] = min((["walk", "walk_after_clearing", "dash", "crystal", "none"].index(a["teams"][0]["mode"]) for a in p2["altars"]), default=4)
	f["core_bank_mode_B"] = min((["walk", "walk_after_clearing", "dash", "crystal", "none"].index(a["teams"][1]["mode"]) for a in p2["altars"]), default=4)
	f["core_contested_groups"] = sum(1 for g in p3["groups"] if g["contested"])
	f["core_contested_value_share"] = round(sum(g["value"] for g in p3["groups"] if g["contested"]) / max(1e-9, sum(g["value"] for g in p3["groups"])), 4)
	f["core_first_contact"] = p3["first_contact"]["round"] if p3["first_contact"]["round"] is not None else -1
	f["core_dash_gain"] = round(float(np.mean([(ctx.walk[0][y, x] - ctx.dash[0][y, x]) for (x, y) in [(c[1], c[2]) for c in M.camp_list]
												 if 0 <= ctx.walk[0][y, x] and 0 <= ctx.dash[0][y, x]] or [0])), 3)
	f["core_islands"] = int(sum(1 for g in range(len(M.groups)) if P.min_on(ctx.walk_clear[0], ctx.gmask[g]) < 0 and P.dist_to_tiles(ctx.walk_clear[0], ctx.gtiles[g]) < 0))
	for R_ in (1, 3, 4, 5):
		h = L[f"hit_{R_}"].any(axis=(1, 2))
		sfe = L[f"safe_{R_}"].any(axis=(1, 2))
		f[f"core_safe_groups_r{R_}"] = round(float(sfe.sum() / max(1, h.sum())), 4)
	f["ext_lanes"] = cf["lanes"] if cf["lanes"] is not None else -1
	f["ext_chokepoints"] = len(cf["chokepoints"])
	f["ext_corridor_width"] = cf["corridor_width_mean"]
	f["ext_corridor_min"] = cf["corridor_width_min_on_routes"]
	f["ext_ambush_bushes"] = cf["ambush_bushes"]
	f["ext_route_load_max"] = round(float(load.max()), 2)
	f["ext_objectives"] = len(obj)
	f["ext_objective_kill"] = min((o["team_kill_rounds"] for o in obj if o["team_kill_rounds"]), default=-1)
	paces = [p["pace"] for p in rpace if p.get("pace")]
	f["ext_pace_model_min"] = min(paces) if paces else 2000
	f["ext_pace_model_mean"] = round(float(np.mean([p.get("pace") or 2000 for p in rpace])), 1) if rpace else -1
	return f


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--maps", default="all")
	ap.add_argument("--out", default=os.path.join(ROOT, "maps/catalog"))
	ap.add_argument("--no-pace", action="store_true")
	a = ap.parse_args()
	names = mapdata.official_names() if a.maps == "all" else a.maps.split(",")
	R = json.load(open(os.path.join(ROOT, "tools/mapintel/data/battery_rosters.json")))
	rows = []
	for n in names:
		_, feats = build_map(n, R, not a.no_pace, a.out)
		rows.append(feats)
	if a.maps == "all":
		with open(os.path.join(a.out, "maps.csv"), "w", newline="") as f:
			w = csv.DictWriter(f, fieldnames=list(rows[0]))
			w.writeheader()
			w.writerows(rows)
		print(f"maps.csv: {len(rows)} maps, {len(rows[0]) - 1} features")


if __name__ == "__main__":
	main()
