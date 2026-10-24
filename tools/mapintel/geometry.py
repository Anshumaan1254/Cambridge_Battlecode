#!/usr/bin/env python3
"""Exact map geometry for tools/mapintel (MAPAnalysis.md 5.3 b, e, h). COMPUTED: engine rules as probed on 3.0.5
(experiments/results/mapintel/probe_rules/, MAPAnalysis.md 7.6):
  * movement: one king step a round; walls, holes, altars, living camps' tiles and the other team's spawn region cannot be entered;
    a dead camp's tile can (standing on it holds that group's respawn while occupied);
  * every range is Chebyshev (basic attacks, spells, area radius, camp attacks, tribute range 1, crystal range 3);
  * dash (Vesper, Vendetta, Issac, Ren, Heart of Ruin; range 2 from the engine's designs, cooldown 8): a path of at most two king steps
    whose intermediate tile is not a wall and not occupied (a hole, an altar or a bush is fine), landing on a free non-hole tile (a dead
    camp's tile is fine); usable in the same turn as the ordinary step (walking-compatible);
  * teleport crystal: Chebyshev 3 ignoring terrain, landing on a free non-hole, non-wall, non-altar tile; a 3-turn channel (it lands at
    the start of the 4th turn); bought on spawn (10 gold), one carried at a time; an altar or a living camp's tile cannot be a landing.
Arrays are [y, x]. Distances are in rounds (int32, -1 = unreachable)."""
import numpy as np

INF = 1 << 30


def shift(a, dx, dy, fill=False):
	"""out[y, x] = a[y - dy, x - dx] (the value from the tile (-dx, -dy) away)."""
	H, W = a.shape
	out = np.full_like(a, fill)
	ys, yd = (slice(0, H - dy), slice(dy, H)) if dy >= 0 else (slice(-dy, H), slice(0, H + dy))
	xs, xd = (slice(0, W - dx), slice(dx, W)) if dx >= 0 else (slice(-dx, W), slice(0, W + dx))
	out[yd, xd] = a[ys, xs]
	return out


KING = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx, dy) != (0, 0)]


def dilate(mask, passable):
	"""Tiles one king step from mask, inside passable (mask itself included)."""
	out = mask.copy()
	for dx, dy in KING:
		out |= shift(mask, dx, dy)
	return out & (passable | mask)


def bfs(passable, sources, max_steps=100000):
	"""Walking distance (king steps) from any source tile through passable tiles; sources count as distance 0 even if not passable."""
	H, W = passable.shape
	dist = np.full((H, W), -1, np.int32)
	front = sources.copy()
	dist[front] = 0
	seen = front.copy()
	d = 0
	while front.any() and d < max_steps:
		d += 1
		nxt = dilate(front, passable) & ~seen
		dist[nxt] = d
		seen |= nxt
		front = nxt
	return dist


def team_passable(M, team, camps_block=True):
	"""Tiles a body of `team` may stand on: not wall / hole / altar / the other team's spawn, and (camps_block) no camp tile
	(every camp is alive at the start; a cleared group's tiles are free until it respawns)."""
	p = ~(M.walls | M.holes | M.altars | M.spawn[1 - team])
	if camps_block:
		p &= ~M.camps
	return p


def king_union(mask):
	out = np.zeros_like(mask)
	for dx, dy in KING:
		out |= shift(mask, dx, dy)
	return out


def dash_step(mask, land_ok, through_ok, rng=2):
	"""Tiles one dash (at most `rng` king steps; intermediate tiles must be through_ok, the landing land_ok) can reach from mask."""
	out = np.zeros_like(mask)
	reach = mask
	for k in range(rng):
		reach = king_union(reach)
		out |= reach & land_ok
		reach = reach & through_ok
	return out


def dash_bfs(passable, through_ok, sources, cooldown=8, rng=2, max_rounds=4000):
	"""Earliest round each tile can be reached by a body that walks one step a round and may also dash (range rng, ready at round 0,
	then every `cooldown` rounds), in either order within a round. State = (tile, rounds until the dash is ready)."""
	H, W = passable.shape
	K = cooldown
	first = np.full((H, W), -1, np.int32)
	# layer[c] = tiles reachable at the current round with the dash ready in c rounds (c = 0..K-1); keep only non-dominated states
	layer = [np.zeros((H, W), bool) for _ in range(K)]
	layer[0] = sources.copy()
	best_cd = np.full((H, W), K + 1, np.int32)  # lowest cooldown seen at any earlier round (a state with a higher one is dominated)
	best_cd[sources] = 0
	first[sources] = 0
	t = 0
	while t < max_rounds:
		t += 1
		new = [np.zeros((H, W), bool) for _ in range(K)]
		for c in range(K):
			if not layer[c].any():
				continue
			walked = dilate(layer[c], passable)
			new[max(c - 1, 0)] |= walked
			if c == 0:
				# dash this round: before or after the step; the dash is ready again in K - 1 rounds after this one
				d1 = dash_step(layer[0], passable, through_ok, rng)
				d2 = dash_step(walked, passable, through_ok, rng)
				d3 = dilate(d1, passable)
				new[K - 1] |= d1 | d2 | d3
		changed = False
		for c in range(K):
			nm = new[c] & (best_cd > c)
			if nm.any():
				changed = True
				best_cd[nm] = c
				f = nm & (first < 0)
				first[f] = t
			new[c] = nm
		# carry forward the states that still matter: a tile already held with a lower cooldown needs no copy
		layer = new
		if not changed:
			break
	return first


def crystal_reach(from_mask, land_ok, rng=3):
	"""Tiles a teleport crystal can land on from any tile of from_mask (Chebyshev rng, terrain ignored)."""
	out = np.zeros_like(from_mask)
	for dy in range(-rng, rng + 1):
		for dx in range(-rng, rng + 1):
			if (dx, dy) != (0, 0):
				out |= shift(from_mask, dx, dy)
	return out & land_ok


def chebyshev_disk(mask, r):
	out = mask.copy()
	for dy in range(-r, r + 1):
		for dx in range(-r, r + 1):
			if (dx, dy) != (0, 0):
				out |= shift(mask, dx, dy)
	return out


def components(passable):
	"""8-connected components of passable tiles: label array (-1 = not passable) and sizes."""
	H, W = passable.shape
	lab = np.full((H, W), -1, np.int32)
	sizes = []
	ys, xs = np.nonzero(passable)
	for y, x in zip(ys, xs):
		if lab[y, x] >= 0:
			continue
		src = np.zeros((H, W), bool)
		src[y, x] = True
		d = bfs(passable, src)
		comp = d >= 0
		lab[comp] = len(sizes)
		sizes.append(int(comp.sum()))
	return lab, sizes
