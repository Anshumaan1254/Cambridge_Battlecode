#!/usr/bin/env python3
"""Runtime map features, version 1: the exact Python twin of tools/mapintel/cpp/mapintel/features.h (MAPAnalysis.md 5.8). COMPUTED.

Every feature is defined so that a bot computes it during the draft from the SDK alone (host BFS distance fields, bitboards, the camp
groups), and both implementations give the same numbers (checked by the test bot on all 40 official maps and perturbed copies:
tools/mapintel/test_library.py). Team-relative: `team` is the team whose view is taken (the bot uses its own; maps.csv uses team A).

Fields (king-move BFS = the SDK's distance_field::compute, checked equal on all 40 maps):
  fc[t] from spawn t through C_t = not (wall | hole | altar | spawn of the other team)        (camp tiles passable: "after clearing")
  fb[t] from spawn t through B_t = C_t and not a camp tile                                 (every camp alive)
  fn    from spawn A through N   = not (wall | hole | altar)                               (spawns passable: the spawn-to-spawn distance)
Per group g: gems, gold, respawn (the runtime groups), hp = sum of its camps' health (engine designs), dU(g) / dE(g) = the least fc of
our / their team over g's camp tiles (-1 if none is reached); value v = gems + 0.1 x gold.
FEATURES lists (name, definition); compute() returns them in that order as floats."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as EC  # noqa: E402
import geometry as G  # noqa: E402

VERSION = 1
FEATURES = [
	("w", "map width"), ("h", "map height"), ("area", "w x h"), ("sym", "symmetry: 0 horizontal, 1 vertical, 2 rotational180"),
	("team", "champions per team (draft rounds)"),
	("walk_share", "tiles that are not wall / hole / altar, / area"), ("wall_share", "walls / area"), ("hole_share", "holes / area"),
	("bush_share", "bushes / area"), ("altars", "altar tiles"), ("groups", "camp groups (both halves)"),
	("n_wolf", "wolves"), ("n_elk", "elks"), ("n_gem_cluster", "gem clusters"), ("n_gold_cluster", "gold clusters"),
	("n_monolith", "monoliths"), ("n_golem", "golems"),
	("gems", "sum of group gems"), ("gold", "sum of group gold"), ("gem_rate", "sum of gems / respawn"), ("gold_rate", "sum of gold / respawn"),
	("gold_per_gem", "gold / max(1, gems)"),
	("spawn_dist", "fn at the nearest tile of the other spawn (-1 if not reached)"),
	("gems_own_share", "2 x gems of groups with dU >= 0, dE >= 0, dU + 6 < dE, / gems"),
	("gems_mid_share", "gems of groups with |dU - dE| <= 6 (both reached), / gems"),
	("gold_mid_share", "gold of groups with |dU - dE| <= 6, / gold"),
	("wide_contested_value_share", "value of groups with |dU - dE| <= 12, / total value"),
	("dist_gem_weighted", "sum dU x gems/respawn / sum gems/respawn over reached groups with gems"),
	("dist_nearest_gem_group", "least dU over groups with gems > 0 (-1 if none)"),
	("hp_total", "sum of group hp"), ("gems_per_khp", "1000 x gems / hp_total"),
	("gems_heavy_share", "gems of groups with hp >= 4800, / gems"), ("n_heavy", "groups with hp >= 4800"),
	("mono_golem_gem_share", "gems of groups holding a monolith or a golem, / gems"),
	("cluster_only_gem_share", "gems of groups made only of gem / gold clusters, / gems"),
	("max_group_gems", "the largest group's gems"), ("mean_respawn_w", "sum respawn x gems / gems"),
	("dist_nearest_altar", "least fc over approach tiles (Chebyshev 1 of an altar, not wall / hole / altar / other spawn) (-1 none)"),
	("altars_walk", "altars with an approach tile that is no camp tile and reached by fb"),
	("altar_camp_gated", "1 if some altar's approach tiles are all camp tiles"),
	("bank_mode", "0: an approach tile without camp reached by fb; 1: an approach tile reached by fc; 2: neither"),
	("bank_mode_enemy", "the same for the other team"),
	("altars_own", "altars whose nearest approach tile has fc(us) + 6 < fc(them)"),
	("dist_nearest_altar_enemy", "the other team's least fc over its approach tiles (-1 none)"),
	("islands", "groups with dU = -1"),
	("safe_area_share", "groups with a striking camp having a tile within Chebyshev 5 of one of its camps that is in B_t and outside"
	 " every striking camp's range, / groups with a striking camp"),
	("reserved", "0 (keeps the C++ array size)"),
]
NAMES = [n for n, _ in FEATURES]


def fields(M, team):
	C = [~(M.walls | M.holes | M.altars | M.spawn[1 - t]) for t in (0, 1)]
	fc = [G.bfs(C[t], M.spawn[t]) for t in (0, 1)]
	fb = [G.bfs(C[t] & ~M.camps, M.spawn[t]) for t in (0, 1)]
	fn = G.bfs(~(M.walls | M.holes | M.altars), M.spawn[0])
	return C, fc, fb, fn


def compute(M, team=0):
	t, e = team, 1 - team
	C, fc, fb, fn = fields(M, team)
	area = M.W * M.H
	f = {}
	f["w"], f["h"], f["area"], f["sym"], f["team"] = M.W, M.H, area, M.sym, M.team_size
	f["walk_share"] = float((~(M.walls | M.holes | M.altars)).sum()) / area
	f["wall_share"] = float(M.walls.sum()) / area
	f["hole_share"] = float(M.holes.sum()) / area
	f["bush_share"] = float(M.bushes.sum()) / area
	f["altars"] = len(M.altar_tiles)
	f["groups"] = len(M.groups)
	cnt = [0] * 6
	for c in M.camp_list:
		cnt[c[0]] += 1
	for k, n in enumerate(["wolf", "elk", "gem_cluster", "gold_cluster", "monolith", "golem"]):
		f["n_" + n] = cnt[k]
	gems = [g["gems"] for g in M.groups]
	gold = [g["gold"] for g in M.groups]
	resp = [g["respawn"] for g in M.groups]
	hp = [sum(EC.camp_stats(c[0])[0] for c in g["camps"]) for g in M.groups]
	S_g, S_o = sum(gems), sum(gold)
	f["gems"], f["gold"] = S_g, S_o
	f["gem_rate"] = sum(a / r for a, r in zip(gems, resp))
	f["gold_rate"] = sum(a / r for a, r in zip(gold, resp))
	f["gold_per_gem"] = S_o / max(1, S_g)
	sp = fn[M.spawn[1]]
	sp = sp[sp >= 0]
	f["spawn_dist"] = int(sp.min()) if len(sp) else -1

	def dmin(field, g):
		best = -1
		for c in g["camps"]:
			v = int(field[c[2], c[1]])
			if v >= 0 and (best < 0 or v < best):
				best = v
		return best
	dU = [dmin(fc[t], g) for g in M.groups]
	dE = [dmin(fc[e], g) for g in M.groups]
	both = [a >= 0 and b >= 0 for a, b in zip(dU, dE)]
	own = sum(gm for gm, a, b, ok in zip(gems, dU, dE, both) if ok and a + 6 < b)
	mid = [ok and abs(a - b) <= 6 for a, b, ok in zip(dU, dE, both)]
	f["gems_own_share"] = 2.0 * own / max(1, S_g)
	f["gems_mid_share"] = sum(gm for gm, m in zip(gems, mid) if m) / max(1, S_g)
	f["gold_mid_share"] = sum(go for go, m in zip(gold, mid) if m) / max(1, S_o)
	val = [gm + 0.1 * go for gm, go in zip(gems, gold)]
	wide = [ok and abs(a - b) <= 12 for a, b, ok in zip(dU, dE, both)]
	f["wide_contested_value_share"] = sum(v for v, w in zip(val, wide) if w) / max(1e-9, sum(val))
	wsum = sum(gm / r for gm, r, a in zip(gems, resp, dU) if gm > 0 and a >= 0)
	f["dist_gem_weighted"] = sum(a * gm / r for gm, r, a in zip(gems, resp, dU) if gm > 0 and a >= 0) / wsum if wsum > 0 else -1.0
	near = [a for gm, a in zip(gems, dU) if gm > 0 and a >= 0]
	f["dist_nearest_gem_group"] = min(near) if near else -1
	f["hp_total"] = sum(hp)
	f["gems_per_khp"] = 1000.0 * S_g / max(1, sum(hp))
	f["gems_heavy_share"] = sum(gm for gm, h in zip(gems, hp) if h >= 4800) / max(1, S_g)
	f["n_heavy"] = sum(1 for h in hp if h >= 4800)
	f["mono_golem_gem_share"] = sum(g["gems"] for g in M.groups if any(c[0] in (4, 5) for c in g["camps"])) / max(1, S_g)
	f["cluster_only_gem_share"] = sum(g["gems"] for g in M.groups if all(c[0] in (2, 3) for c in g["camps"])) / max(1, S_g)
	f["max_group_gems"] = max(gems) if gems else 0
	f["mean_respawn_w"] = sum(r * gm for r, gm in zip(resp, gems)) / max(1, S_g)
	# altars
	best_alt, best_alt_e, walk_alt, gated, own_alt = -1, -1, 0, 0, 0
	mode = {t: 2, e: 2}
	for (ax, ay) in M.altar_tiles:
		app = {}
		for tt in (t, e):
			app[tt] = [(x, y) for dy in (-1, 0, 1) for dx in (-1, 0, 1) for x, y in [(ax + dx, ay + dy)]
					   if (dx, dy) != (0, 0) and 0 <= x < M.W and 0 <= y < M.H and C[tt][y, x]]
		if app[t] and all((x, y) in M.camp_type for x, y in app[t]):
			gated = 1
		du = [int(fc[t][y, x]) for x, y in app[t] if fc[t][y, x] >= 0]
		de = [int(fc[e][y, x]) for x, y in app[e] if fc[e][y, x] >= 0]
		if du and (best_alt < 0 or min(du) < best_alt):
			best_alt = min(du)
		if de and (best_alt_e < 0 or min(de) < best_alt_e):
			best_alt_e = min(de)
		if du and (not de or min(du) + 6 < min(de)):
			own_alt += 1
		if any((x, y) not in M.camp_type and fb[t][y, x] >= 0 for x, y in app[t]):
			walk_alt += 1
		for tt in (t, e):
			if any((x, y) not in M.camp_type and fb[tt][y, x] >= 0 for x, y in app[tt]):
				mode[tt] = 0
			elif mode[tt] > 1 and any(fc[tt][y, x] >= 0 for x, y in app[tt]):
				mode[tt] = 1
	f["dist_nearest_altar"] = best_alt
	f["altars_walk"] = walk_alt
	f["altar_camp_gated"] = gated
	f["bank_mode"] = mode[t]
	f["bank_mode_enemy"] = mode[e]
	f["altars_own"] = own_alt
	f["dist_nearest_altar_enemy"] = best_alt_e
	f["islands"] = sum(1 for a in dU if a < 0)
	# safe area-spell tiles (no sight needed: probed)
	threat = np.zeros((M.H, M.W), bool)
	for (x, y), ct in M.camp_type.items():
		_, st, rg = EC.camp_stats(ct)
		if st > 0:
			threat[max(0, y - rg):y + rg + 1, max(0, x - rg):x + rg + 1] = True
	stand = C[t] & ~M.camps
	nstrike, nsafe = 0, 0
	for g in M.groups:
		if not any(EC.camp_stats(c[0])[1] > 0 for c in g["camps"]):
			continue
		nstrike += 1
		near5 = np.zeros((M.H, M.W), bool)
		for c in g["camps"]:
			near5[max(0, c[2] - 5):c[2] + 6, max(0, c[1] - 5):c[1] + 6] = True
		if (near5 & stand & ~threat).any():
			nsafe += 1
	f["safe_area_share"] = nsafe / nstrike if nstrike else 1.0
	f["reserved"] = 0.0
	return [float(f[n]) for n in NAMES]


if __name__ == "__main__":
	import mapdata
	M = mapdata.load(sys.argv[1] if len(sys.argv) > 1 else "00elkring")
	for n, v in zip(NAMES, compute(M)):
		print(f"{n:28s} {v:.6g}")
