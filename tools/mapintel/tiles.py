#!/usr/bin/env python3
"""Per-champion tile analysis by kit class (MAPAnalysis.md 1.7 prompt, step 3). COMPUTED.

Every champion moves 1 and sees 8; per tile what differs is attack range, spell reach and dash. The classes are read from the engine's
designs at run time (engine.py kit_class: range 1 / 3 x dash or not). Layers per map (all [y, x]):
  dist_walk[team], dist_dash[team]      rounds from that team's spawn region, walking / walking + dash (range and cooldown from the designs)
  dist_altar[a]                         walking rounds to a legal approach tile of altar a (per team, team A's passability)
  threat                                sum of the strengths of camps whose own range covers the tile (the same for every champion)
  bush                                  bush tiles
  hit[R][g]                             tiles a body with reach R hits group g from (R = 1 melee, 3 ranged basic attacks, 4 single-target
                                        spells; line of sight from the engine's vision table), and R = 5 for area spells (ground target
                                        within 4, radius 1; no line of sight needed: probed, MAPAnalysis 7.6)
  safe[R][g]                            hit[R][g] tiles with no living camp of ANY group in range (threat 0)
Per (champion, group): whether safe attack tiles exist, how many, the one nearest to each team's spawn; the solo kill time, damage
taken and heal trips from the best standing tile (economy.fight). These numbers feed the economy model, plan 1 and the table."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as EC  # noqa: E402
import geometry as G  # noqa: E402

REACHES = (1, 3, 4, 5)


def classes():
	E = EC.engine()
	out = {}
	for b in E.champs:
		out.setdefault(E.kit_class(b), []).append(b)
	return out


def body_reaches(b):
	"""The reaches a body hits camps with: its basic attack range and its damaging spells (4 single target, 5 area)."""
	E = EC.engine()
	r = {E.attack_range(b)}
	for s in E.spells(b):
		if s["kind"] in ("damage", "cc") and s.get("mod", 0) > 0:
			r.add(4)
		if s["kind"] == "aoe":
			r.add(5)
	return sorted(r)


def threat_layer(M):
	t = np.zeros((M.H, M.W), np.float32)
	for (x, y), ct in M.camp_type.items():
		hp, st, rg = EC.camp_stats(ct)
		if st <= 0:
			continue
		y0, y1, x0, x1 = max(0, y - rg), min(M.H, y + rg + 1), max(0, x - rg), min(M.W, x + rg + 1)
		t[y0:y1, x0:x1] += st
	return t


def hit_layers(M, team=0):
	"""hit[R] = bool [G, H, W]: standable tiles (team's passability, every camp alive) from which reach R hits a camp of group g."""
	Gn = len(M.groups)
	stand = G.team_passable(M, team, camps_block=True)
	out = {R: np.zeros((Gn, M.H, M.W), bool) for R in REACHES}
	for gi, g in enumerate(M.groups):
		for (_, cx, cy) in g["camps"]:
			for R in REACHES:
				rr = 4 if R == 5 else R
				for dy in range(-R, R + 1):
					y = cy + dy
					if not 0 <= y < M.H:
						continue
					for dx in range(-R, R + 1):
						x = cx + dx
						if not 0 <= x < M.W or not stand[y, x] or out[R][gi, y, x]:
							continue
						if R == 5:
							# area spell: a ground target within 4 of the tile with the camp within radius 1 of it -> Chebyshev <= 5
							if max(abs(dx), abs(dy)) > rr + 1:
								continue
						if R == 5 or EC.sees(M, (x, y), (cx, cy)):  # probed: an area spell at an unseen ground tile hits (no sight needed)
							out[R][gi, y, x] = True
	return out


def build(M, sim=True):
	E = EC.engine()
	L = {}
	L["bush"] = M.bushes.copy()
	L["threat"] = threat_layer(M)
	dash_rng = int(next(a for b in E.champs for a in E.champs[b]["abilities"] if a["kind"] == "dash")["range"])
	dash_cd = int(next(a for b in E.champs for a in E.champs[b]["abilities"] if a["kind"] == "dash")["cd"])
	for team in (0, 1):
		p = G.team_passable(M, team, camps_block=True)
		through = ~(M.walls | M.camps | M.spawn[1 - team])  # probed: a dash passes over holes, altars and bushes, not walls or living camps
		L[f"dist_walk_{team}"] = G.bfs(p, M.spawn[team])
		L[f"dist_dash_{team}"] = G.dash_bfs(p, through, M.spawn[team], cooldown=dash_cd, rng=dash_rng)
	hit = hit_layers(M, 0)
	safe_mask = L["threat"] <= 0
	for R in REACHES:
		L[f"hit_{R}"] = hit[R]
		L[f"safe_{R}"] = hit[R] & safe_mask[None, :, :]
	# per (champion, group) summary
	per = []
	home = [G.bfs(G.team_passable(M, t, camps_block=False), M.spawn[t]) for t in (0, 1)]
	for gi, g in enumerate(M.groups):
		row = {"group": g["id"], "bodies": {}}
		for b in E.champs:
			rs = body_reaches(b)
			best = max(rs)
			safe_tiles = np.argwhere(L[f"safe_{best}"][gi])
			info = {"reaches": rs, "safe_tiles": int(len(safe_tiles))}
			for team in (0, 1):
				if len(safe_tiles):
					d = L[f"dist_walk_{team}"][safe_tiles[:, 0], safe_tiles[:, 1]]
					ok = d >= 0
					if ok.any():
						k = int(np.argmin(np.where(ok, d, 1 << 30)))
						info[f"safe_nearest_{team}"] = [int(safe_tiles[k, 1]), int(safe_tiles[k, 0]), int(d[k])]
			if sim:
				r = EC.fight(M, 0, [EC.Champ(b)], g, home[0])
				info.update({"solo_rounds": r.rounds, "solo_damage": int(sum(r.damage)), "solo_trips": int(sum(r.trips)),
							 "solo_cleared": bool(r.cleared), "solo_tile": list(r.tiles[0]) if r.tiles[0] else None})
			row["bodies"][E.champs[b]["name"]] = info
		per.append(row)
	return L, per
