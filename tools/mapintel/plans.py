#!/usr/bin/env python3
"""The four per-map plans of MAPAnalysis.md 5.3 (d-g) and the unopposed pace, on top of geometry.py / economy.py / tiles.py. COMPUTED.

  Ctx(M)                      distance fields per team: walking with every camp alive (start of the game), walking after clearing
                              (camp tiles passable), walking + dash; fields from every altar's approach tiles and every group's tiles.
  plan2(ctx)                  legal altar approach tiles; per team and per altar the access (walk / walk after clearing groups X /
                              dash / crystal / none) and its round; bank route per group (walk to an approach tile, or recall + walk
                              from spawn, + tribute); the altar's side; the per-team banking cases and the tiebreak rule that follows.
  plan3(ctx)                  per group and team: first arrival at a tile it can be hit from (melee 1 / ranged 3, walking and with a
                              dash), the gap, value, deny value, contested flag and priority; the first-contact round on the route.
  Planner(ctx, team, picks)   unopposed multi-body farming (exclusive claims: two bodies never take one group unless a joint fight pays
                              more than both solo cycles; heal trips inside the fights; shopping at every spawn visit; banking by route
                              choice): run(until=R0) gives plan 1 (per body slot: groups with arrival, capture and bank rounds) and
                              run(to 1,000 gems) the unopposed pace.
  plan1(ctx, team, picks)     the planner's opening with a search over every body's first target (its 3 best first targets each,
                              all combinations) for the most value by round R0 (banked + 0.5 x carried).
  plan4(ctx)                  abandon / regroup / bank-abort / drop thresholds as functions of the map's features (default formulas;
                              their values are fitted in step 6 from real games, then simulations)."""
import itertools
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as EC  # noqa: E402
import geometry as G  # noqa: E402
import tiles as T  # noqa: E402
from engine import pick_bodies  # noqa: E402

CRYSTAL_RANGE = 3  # probed (MAPAnalysis 7.6): distance 3 lands, 4 is "Teleport out of range"; the engine's settings do not list it
GOLD_W = 0.1  # value = gems + GOLD_W x gold (unfitted default; step 6 fits it from the top teams' choices)


def cheb(a, b):
	return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def mask_of(M, tiles):
	m = np.zeros((M.H, M.W), bool)
	for x, y in tiles:
		m[y, x] = True
	return m


def min_on(field, mask):
	v = field[mask]
	v = v[v >= 0]
	return int(v.min()) if len(v) else -1


def dist_to_tiles(field, tiles):
	"""Rounds to stand on any of tiles: the field there, or one step from a reached neighbour (a camp's tile is entered once the camp
	is dead, so the field, which treats living camps as walls, does not reach it)."""
	H, W = field.shape
	best = -1
	for x, y in tiles:
		d = int(field[y, x])
		if d < 0:
			for dx, dy in G.KING:
				X, Y = x + dx, y + dy
				if 0 <= X < W and 0 <= Y < H and field[Y, X] >= 0 and (d < 0 or field[Y, X] + 1 < d):
					d = int(field[Y, X]) + 1
		if d >= 0 and (best < 0 or d < best):
			best = d
	return best


class Ctx:
	def __init__(self, M):
		self.M = M
		E = EC.engine()
		self.dash_rng = int(next(a for b in E.champs for a in E.champs[b]["abilities"] if a["kind"] == "dash")["range"])
		self.dash_cd = int(next(a for b in E.champs for a in E.champs[b]["abilities"] if a["kind"] == "dash")["cd"])
		self.block, self.clear, self.through, self.through_clear = [], [], [], []
		self.walk, self.walk_clear, self.dash, self.dash_clear = [], [], [], []
		for t in (0, 1):
			self.block.append(G.team_passable(M, t, True))
			self.clear.append(G.team_passable(M, t, False))
			self.through.append(~(M.walls | M.camps | M.spawn[1 - t]))
			self.through_clear.append(~(M.walls | M.spawn[1 - t]))
			self.walk.append(G.bfs(self.block[t], M.spawn[t]))
			self.walk_clear.append(G.bfs(self.clear[t], M.spawn[t]))
			self.dash.append(G.dash_bfs(self.block[t], self.through[t], M.spawn[t], self.dash_cd, self.dash_rng))
			self.dash_clear.append(G.dash_bfs(self.clear[t], self.through_clear[t], M.spawn[t], self.dash_cd, self.dash_rng))
		self.hit = [T.hit_layers(M, t) for t in (0, 1)]
		self.gtiles = [[(c[1], c[2]) for c in g["camps"]] for g in M.groups]
		self.gmask = [mask_of(M, ts) for ts in self.gtiles]
		self.value = [g["gems"] + GOLD_W * g["gold"] for g in M.groups]
		# approach tiles: Chebyshev 1 of the altar, standable (a camp's tile counts, flagged: usable once that camp is dead)
		self.approach = []
		for (ax, ay) in M.altar_tiles:
			ts = []
			for dy in (-1, 0, 1):
				for dx in (-1, 0, 1):
					x, y = ax + dx, ay + dy
					if (dx, dy) == (0, 0) or not (0 <= x < M.W and 0 <= y < M.H):
						continue
					if M.walls[y, x] or M.holes[y, x] or M.altars[y, x]:
						continue
					ts.append((x, y))
			self.approach.append(ts)
		self._fields = {}
		# the mirror image of each group (the engine builds the other half of the map by its symmetry): team B's plans are team A's
		# plans with every group replaced by its mirror (the planner does not model turn order, the only asymmetry)
		mir = {0: lambda x, y: (M.W - 1 - x, y), 1: lambda x, y: (x, M.H - 1 - y), 2: lambda x, y: (M.W - 1 - x, M.H - 1 - y)}[M.sym]
		self.mirror_group = []
		for g in M.groups:
			x, y = g["camps"][0][1], g["camps"][0][2]
			self.mirror_group.append(M.camp_group.get(mir(x, y)))

	def field(self, key, sources, team, clear=False):
		"""Walking distance field to a source set (moves are symmetric, so it is also the distance from the set). clear=False: every
		other camp alive (its tiles block), the source tiles themselves passable; clear=True: every camp tile passable."""
		k = (key, team, clear)
		if k not in self._fields:
			self._fields[k] = G.bfs(self.clear[team] if clear else (self.block[team] | sources), sources)
		return self._fields[k]

	def approach_ok(self, a, team):
		return [q for q in self.approach[a] if not self.M.spawn[1 - team][q[1], q[0]]]

	def altar_field(self, a, team):
		return self.field(("altar", a), mask_of(self.M, self.approach_ok(a, team)), team)

	def gates(self, a, team):
		"""Groups that must be dead for team to tribute at altar a: when every approach tile is a camp's tile, those camps' groups
		(standing on such a tile also holds that group's respawn); else none."""
		ok = self.approach_ok(a, team)
		if any(q not in self.M.camp_type for q in ok):
			return set()
		return {self.M.camp_group[q] for q in ok}

	def loc_field(self, loc, team):
		"""Walking field from a location: 'spawn', ('group', g) (its dead tiles, where the capturer stands) or ('altar', a) (its
		approach tiles); every other camp alive."""
		if loc == "spawn":
			return self.walk[team]
		if loc[0] == "group":
			return self.field(("group", loc[1]), self.gmask[loc[1]], team)
		return self.field(("altar", loc[1]), mask_of(self.M, self.approach_ok(loc[1], team)), team)

	def home(self, team):
		return self.walk_clear[team]


# ---------------------------------------------------------------------------------------------------------------------------------
# plan 2: approach tiles, access per team, bank routes, tiebreak cases

def plan2(ctx):
	M = ctx.M
	altars = []
	for a, (ax, ay) in enumerate(M.altar_tiles):
		ent = {"altar": [ax, ay], "approach": [], "teams": []}
		for q in ctx.approach[a]:
			ent["approach"].append({"tile": list(q), "camp_group": M.camp_group.get(q), "spawn_of": [t for t in (0, 1) if M.spawn[t][q[1], q[0]]]})
		for t in (0, 1):
			ok = ctx.approach_ok(a, t)
			free = [q for q in ok if q not in M.camp_type]
			campq = [q for q in ok if q in M.camp_type]
			acc = {"team": t}
			mf, mfree = mask_of(M, free), mask_of(M, ok)
			acc["walk"] = min_on(ctx.walk[t], mf) if free else -1
			acc["walk_clear"] = min_on(ctx.walk_clear[t], mfree) if ok else -1
			acc["dash"] = min_on(ctx.dash[t], mf) if free else -1
			acc["dash_clear"] = min_on(ctx.dash_clear[t], mfree) if ok else -1
			# crystal: one hop (range 3, terrain ignored) from ground the team reaches (after clearing), landing on a free tile;
			# then walking from the landing (the hop's region); counted only when the approach is not already reachable
			land_ok = ctx.block[t]
			reach = ctx.walk_clear[t] >= 0
			land = G.crystal_reach(reach, land_ok, CRYSTAL_RANGE) & ~reach
			acc["crystal"] = -1
			if land.any() and ok:
				after = G.bfs(ctx.clear[t], land)
				d = min_on(after, mfree)
				if d >= 0:
					acc["crystal"] = d  # rounds walked after the landing (+ a spawn visit for the crystal, + its 3-turn channel)
			if acc["walk"] < 0 and acc["walk_clear"] >= 0:
				# which groups must die first: those owning every approach tile, plus the camps on the shortest route after clearing
				blockers = set(ctx.gates(a, t))
				for (x, y) in shortest_path(ctx.walk_clear[t], mfree, M.spawn[t], ctx.clear[t]):
					if (x, y) in M.camp_group:
						blockers.add(M.camp_group[(x, y)])
				acc["gate_groups"] = sorted(blockers)
			if acc["walk"] >= 0:
				acc["mode"] = "walk"
			elif acc["walk_clear"] >= 0:
				acc["mode"] = "walk_after_clearing"
			elif acc["dash"] >= 0 or acc["dash_clear"] >= 0:
				acc["mode"] = "dash"
			elif acc["crystal"] >= 0:
				acc["mode"] = "crystal"
			else:
				acc["mode"] = "none"
			acc["camp_tile_only"] = bool(ok) and not free
			ent["teams"].append(acc)
		# side of the altar: walking distance from each spawn to its approach tiles (after clearing)
		da, db = ent["teams"][0]["walk_clear"], ent["teams"][1]["walk_clear"]
		ent["side_A"] = "own" if da >= 0 and (db < 0 or da + 6 < db) else "enemy" if db >= 0 and (da < 0 or db + 6 < da) else "middle"
		altars.append(ent)

	def bankable(t, modes):
		return any(e["teams"][t]["mode"] in modes for e in altars)

	cases = {}
	for cfg, modes in (("walk", {"walk", "walk_after_clearing"}), ("dash", {"walk", "walk_after_clearing", "dash"}),
					   ("crystal", {"walk", "walk_after_clearing", "dash", "crystal"})):
		ca, cb = bankable(0, modes), bankable(1, modes)
		cases[cfg] = {"A_can_bank": ca, "B_can_bank": cb, "rule_for_A": tiebreak_rule(ca, cb), "rule_for_B": tiebreak_rule(cb, ca)}
	# bank route per group and team: the cheaper of walking from the group to an approach tile and recall + walking from spawn
	routes = []
	rec = EC.recall_rounds()
	for g, grp in enumerate(M.groups):
		row = {"group": grp["id"], "teams": []}
		for t in (0, 1):
			best = None
			for a in range(len(M.altar_tiles)):
				if not ctx.approach_ok(a, t):
					continue
				ok = ctx.approach_ok(a, t)
				dw = dist_to_tiles(ctx.loc_field(("group", g), t), ok)
				dr = dist_to_tiles(ctx.walk[t], ok)
				opts = []
				if dw >= 0:
					opts.append(("walk", dw))
				if dr >= 0:
					opts.append(("recall", rec + dr))
				for how, c in opts:
					if best is None or c < best[2]:
						best = (a, how, c)
			if best is None:
				row["teams"].append({"team": t, "altar": None})
				continue
			a, how, c = best
			bag = grp["gems"]
			row["teams"].append({"team": t, "altar": a, "how": how, "rounds": c, "tribute": EC.tribute_turns(bag),
								 "eta": c + EC.tribute_turns(bag), "side": altars[a]["side_A"] if t == 0 else
								 {"own": "enemy", "enemy": "own", "middle": "middle"}[altars[a]["side_A"]]})
		routes.append(row)
	return {"altars": altars, "cases": cases, "bank_routes": routes}


def tiebreak_rule(us, them):
	"""The plan's tiebreak cases (MAPAnalysis 5.3e; rules: tributed gems, then lifetime gold earned, then kills, then team B)."""
	if not us and not them:
		return "neither can bank: play for gold earned, then kills"
	if them and not us:
		return "only the enemy can bank: stop their tributes (stun / kill / a new altar lock cancels one) and find our own dash / crystal route; gold does not help"
	if us and not them:
		return "only we can bank: bank early; any banked gem wins the tiebreak"
	return "both can bank: normal play"


# ---------------------------------------------------------------------------------------------------------------------------------
# plan 3: contested groups and arrival times

def plan3(ctx, k_contest=None, band=None):
	"""Contested = |ETA gap| <= k_contest rounds or |d_us - d_them| <= band tiles; both default to max(3, 0.1 x the spawn-to-spawn walking
	distance) so they scale with the map (a fixed 10 marks every group of a 30 x 30 map)."""
	M = ctx.M
	out = []
	if k_contest is None or band is None:
		fn = G.bfs(~(M.walls | M.holes | M.altars), M.spawn[0])
		sd = min_on(fn, M.spawn[1])
		scale = max(3, round(0.1 * (sd if sd > 0 else max(M.W, M.H))))
		k_contest = scale if k_contest is None else k_contest
		band = scale if band is None else band
	# earliest round an enemy body can be within 4 (spell reach) of each tile: min filter of their walking field
	near = []
	for t in (0, 1):
		f = ctx.walk[t].astype(np.int64)
		f[f < 0] = 1 << 20
		m = f.copy()
		for dy in range(-4, 5):
			for dx in range(-4, 5):
				m = np.minimum(m, G.shift(f, dx, dy, fill=1 << 20))
		near.append(m)
	for g, grp in enumerate(M.groups):
		row = {"group": grp["id"], "gems": grp["gems"], "gold": grp["gold"], "value": round(ctx.value[g], 1), "teams": []}
		for t in (0, 1):
			e = {}
			for R in (1, 3):
				e[f"walk_{R}"] = min_on(ctx.walk[t], ctx.hit[t][R][g])
				e[f"dash_{R}"] = min_on(ctx.dash[t], ctx.hit[t][R][g])
				e[f"walk_clear_{R}"] = min_on(ctx.walk_clear[t], ctx.hit[t][R][g])
			e["dist"] = min_on(ctx.walk_clear[t], ctx.gmask[g])
			row["teams"].append(e)
		# arrival ETA = the faster of melee and ranged walking (after clearing when the group is walled in by camps)
		eta = []
		for t in (0, 1):
			e = row["teams"][t]
			c = [v for v in (e["walk_1"], e["walk_3"]) if v >= 0] or [v for v in (e["walk_clear_1"], e["walk_clear_3"]) if v >= 0]
			eta.append(min(c) if c else -1)
		row["eta"] = eta
		gap = (eta[1] - eta[0]) if eta[0] >= 0 and eta[1] >= 0 else None
		row["gap_A"] = gap  # > 0: team A arrives first
		da, db = row["teams"][0]["dist"], row["teams"][1]["dist"]
		row["middle_band"] = da >= 0 and db >= 0 and abs(da - db) <= band
		row["contested"] = bool(row["middle_band"] or (gap is not None and abs(gap) <= k_contest))
		row["deny_value"] = round(ctx.value[g], 1)  # what the other team loses if we take it (its value to them)
		row["priority"] = round(ctx.value[g] * (math.exp(-abs(gap) / k_contest) if gap is not None else 0.0), 2)
		row["race_winner"] = None if gap is None else ("A" if gap > 0 else "B" if gap < 0 else "tie")
		# first contact on team A's route: the earliest round an enemy could be within 4 of our body on the shortest walk to the group
		for t in (0, 1):
			path = shortest_path(ctx.walk_clear[t], ctx.hit[t][3][g] | ctx.hit[t][1][g], M.spawn[t], ctx.clear[t])
			fc = None
			for i, (x, y) in enumerate(path):
				ours = int(ctx.walk_clear[t][y, x])
				theirs = int(near[1 - t][y, x])
				c = max(ours, theirs)
				if fc is None or c < fc[0]:
					fc = (c, [x, y])
			row["teams"][t]["first_contact"] = fc[0] if fc and fc[0] < (1 << 19) else None
			row["teams"][t]["first_contact_tile"] = fc[1] if fc and fc[0] < (1 << 19) else None
		out.append(row)
	# the map's first-contact point: where the two fronts meet (earliest max(t_A, t_B within 4) over all tiles)
	both = np.maximum(np.where(ctx.walk[0] >= 0, ctx.walk[0], 1 << 20), near[1])
	y, x = np.unravel_index(int(np.argmin(both)), both.shape)
	return {"groups": out, "first_contact": {"round": int(both[y, x]) if both[y, x] < (1 << 19) else None, "tile": [int(x), int(y)]},
			"k_contest": k_contest, "band": band}


def shortest_path(dist_from_spawn, goal_mask, spawn_mask, passable):
	"""A shortest walking path from the spawn to the goal set (reconstructed backwards along the spawn distance field)."""
	v = np.where(goal_mask & (dist_from_spawn >= 0), dist_from_spawn, 1 << 30)
	if v.min() >= 1 << 30:
		return []
	y, x = np.unravel_index(int(np.argmin(v)), v.shape)
	path = [(int(x), int(y))]
	d = int(dist_from_spawn[y, x])
	H, W = dist_from_spawn.shape
	while d > 0:
		nxt = None
		for dx, dy in G.KING:
			X, Y = x + dx, y + dy
			if 0 <= X < W and 0 <= Y < H and dist_from_spawn[Y, X] == d - 1:
				nxt = (X, Y)
				break
		if nxt is None:
			break
		x, y = nxt
		d -= 1
		path.append((x, y))
	return path[::-1]


# ---------------------------------------------------------------------------------------------------------------------------------
# the planner: unopposed multi-body farming (plan 1 and the pace)

BUILD = ("monster", "jungle", "power")  # model build per body: Monster in its damage stat, Jungle in health, then Power damage forever


def damage_stat(ch):
	"""The stat whose shard adds the most camp damage a round: strength (basic attacks, + resets, Varg's splash) or focus (spells)."""
	d = ch.d()
	reset = sum(1 for a in ch.abilities() if a["kind"] == "reset") / 8.0
	s = d["str_growth"] * (1 + reset) * (2.0 if ch.body == 10 else 1.0)
	f = d["foc_growth"] * sum(a.get("mod", 0) for a in ch.abilities() if a["kind"] in ("damage", "aoe", "cc") or (a["kind"] == "dash" and a.get("mod", 0) > 0)) / 8.0
	return "foc" if f > s else "str"


def shop(ch, gold):
	"""Spend gold on shards (30 each) by the model build; returns the gold left."""
	cost = 30
	while gold >= cost:
		n = sum(ch.shards.values())
		stage = 0 if n < 5 else 1 if n < 10 else 2
		fam = BUILD[stage]
		stat = "hp" if fam == "jungle" else damage_stat(ch)
		ch.shards[stat] += 1
		gold -= cost
		if n + 1 == 5:
			ch.emblems.add("monster")
		elif n + 1 == 10:
			ch.emblems.add("jungle")
		elif n + 1 > 10 and (n + 1 - 10) % 5 == 0:
			ch.shards[stat] += 1  # a Power emblem counts six shards
	return gold


def contest_share(ctx, team, coef):
	"""Per group the team's expected share of its reward against an opponent: 1 / (1 + exp(-(a + b x gap))), gap = (their walk - ours)
	/ the contested band (compact.py's dU, dE and band; 9 when they cannot reach it); all 1 without coefficients (the unopposed model)."""
	G = len(ctx.M.groups)
	if not coef:
		return [1.0] * G
	key = ("share", team, coef["a"], coef["b"])
	cache = ctx.__dict__.setdefault("_share_cache", {})
	if key not in cache:
		import compact as CP
		C = CP.Compact(ctx.M, team)
		band, _ = C.contested()
		out = []
		for g in range(G):
			gap = 9.0 if C.dE[g] < 0 else max(-9.0, min(9.0, (C.dE[g] - C.dU[g]) / band))
			out.append(1.0 / (1.0 + math.exp(-(coef["a"] + coef["b"] * gap))))
		cache[key] = out
	return cache[key]


class Planner:
	def __init__(self, ctx, team, picks, bank_bag=None, retreat=None, heal_frac=None, join=True, gold_w=None, max_wait=30):
		E = EC.econ()  # the economy constants (LEARNED by econ_learn.py when fitted)
		bank_bag = E["bank_bag"] if bank_bag is None else bank_bag
		retreat = E["retreat"] if retreat is None else retreat
		heal_frac = E["heal_frac"] if heal_frac is None else heal_frac
		gold_w = E["gold_w"] if gold_w is None else gold_w
		self.ctx, self.team, self.picks = ctx, team, list(picks)
		self.share = contest_share(ctx, team, E.get("contest"))  # the expected share of each group's reward (1 = unopposed)
		self.value = [(g["gems"] + gold_w * g["gold"]) * self.share[i] for i, g in enumerate(ctx.M.groups)]
		self.max_wait = max_wait  # plan 4's drop rule: never commit to a respawn wait longer than this (do something else first)
		self.shop_gold = E["shop_gold"]  # recall home to shop when this much gold is unspent and the bag is empty
		self.bodies = [b for p in picks for b in pick_bodies(p)]
		self.bank_bag, self.retreat, self.heal_frac, self.join = bank_bag, retreat, heal_frac, join
		self._cache = {}

	def kill(self, g, bodies_chs, delays, hp_left=None, golds=None):
		"""A fight (cached). golds = each body's unspent gold: spent on shards (the model build) at every heal trip of the fight."""
		golds = list(golds) if golds is not None else [0] * len(bodies_chs)
		key = (g, tuple((c.body, tuple(sorted(c.shards.items())), tuple(sorted(c.emblems)), int(c.hp // 50)) for c in bodies_chs), tuple(delays),
			   None if hp_left is None else tuple(sorted(hp_left.items())), tuple(min(x // 30, 40) for x in golds))
		if key not in self._cache:
			chs = [EC.Champ(c.body, dict(c.shards), set(c.emblems), c.hp) for c in bodies_chs]
			left = list(golds)

			def shop_fn(j):
				left[j] = shop(chs[j], left[j])
			r = EC.fight(self.ctx.M, self.team, chs, self.ctx.M.groups[g], self.ctx.home(self.team), self.retreat, delays=delays,
						 hp_left=hp_left, shop_fn=shop_fn)
			r.shards = [(dict(c.shards), set(c.emblems)) for c in chs]
			r.gold_left = left
			self._cache[key] = r
		return self._cache[key]

	def travel(self, loc, g, body):
		"""Rounds from a location ('spawn', ('group', h), ('altar', a)) to a tile hitting group g with this body's reach."""
		ctx, t = self.ctx, self.team
		R = 1 if EC.engine().attack_range(body) <= 1 else 3
		return min_on(ctx.loc_field(loc, t), ctx.hit[t][R][g])

	def bank_cost(self, loc, bag, dead=None):
		"""Cheapest bank trip from loc: walk to an approach tile, or recall (5) + walk from spawn; + tribute turns. (rounds, altar).
		dead = groups dead now (an altar whose approach tiles are all camp tiles is usable only while those groups are dead)."""
		ctx, t = self.ctx, self.team
		best = None
		rec = EC.recall_rounds()
		for a in range(len(ctx.M.altar_tiles)):
			if not ctx.approach_ok(a, t):
				continue
			if dead is not None and not ctx.gates(a, t) <= dead:
				continue
			ok = ctx.approach_ok(a, t)
			dw = dist_to_tiles(ctx.loc_field(loc, t), ok)
			dr = dist_to_tiles(ctx.walk[t], ok)
			for c in ([dw] if dw >= 0 else []) + ([rec + dr] if dr >= 0 and loc != "spawn" else []):
				if best is None or c < best[0]:
					best = (c, a)
		if best is None:
			return None
		return best[0] + EC.tribute_turns(bag), best[1]

	def run(self, until=2000, target=1000, first=None, log=False):
		ctx, M, t = self.ctx, self.ctx.M, self.team
		E = EC.engine()
		n = len(self.bodies)
		chs = [EC.Champ(b) for b in self.bodies]
		free = [1] * n  # round each body is free
		loc = ["spawn"] * n
		bag = [0] * n
		gold = [0] * n
		claim = {}  # group -> body
		respawn_at = {g: 0 for g in range(len(M.groups))}  # round the group is alive again (0 = alive now)
		hp_left = {}  # group -> camp health left after an abandoned fight
		banked, gold_earned = 0, 0
		plan = [[] for _ in range(n)]
		first = list(first) if first else [None] * n
		reached = None
		guard = 0
		self.solo_rate = []
		for k in range(n):
			rates = [0.0]
			for g in range(len(M.groups)):
				tr = self.travel("spawn", g, chs[k].body)
				if tr < 0:
					continue
				r = self.kill(g, [EC.Champ(chs[k].body)], [0])
				if r.cleared:
					rates.append(self.value[g] / (2 * tr + r.rounds + EC.capture_rounds()))
			self.solo_rate.append(max(rates))
		gate_value = {}
		for a in range(len(M.altar_tiles)):
			for g in ctx.gates(a, t):
				gate_value[g] = 200.0
		while guard < 20000:
			guard += 1
			i = min(range(n), key=lambda k: (free[k], k))
			now = free[i]
			if now > until or (target and banked >= target):
				break
			ch = chs[i]
			# 1. heal and shop at spawn when low (heal trips inside fights already returned the body full)
			if ch.hp >= 0 and ch.hp < self.heal_frac * ch.max_hp() and loc[i] != "spawn":
				d = min_on(ctx.loc_field(loc[i], t), M.spawn[t])
				back = min(d if d >= 0 else 999, EC.recall_rounds() + 2)
				free[i] = now + back + 1
				loc[i] = "spawn"
				ch.hp = -1
				gold[i] = shop(ch, gold[i])
				plan[i].append({"do": "heal", "round": free[i]})
				continue
			if loc[i] == "spawn":
				ch.hp = -1
				gold[i] = shop(ch, gold[i])
			elif gold[i] >= self.shop_gold and bag[i] == 0:
				# rich: recall home to shop (and heal) before the next job
				free[i] = now + EC.recall_rounds() + 1
				loc[i] = "spawn"
				ch.hp = -1
				gold[i] = shop(ch, gold[i])
				plan[i].append({"do": "shop", "round": free[i]})
				continue
			# 2. bank when the bag is big, near the end, or when the bag wins the game
			dead = {g for g in range(len(M.groups)) if respawn_at[g] > now}
			if bag[i] > 0 and (bag[i] >= self.bank_bag or banked + bag[i] >= target or now > until - 60):
				bc = self.bank_cost(loc[i], bag[i], dead)
				if bc is not None:
					c, a = bc
					free[i] = now + c
					banked += bag[i]
					if M.altar_tiles:
						plan[i].append({"do": "bank", "altar": a, "gems": bag[i], "round": free[i]})
					if t is not None and banked >= target and reached is None:
						reached = free[i]
					bag[i] = 0
					loc[i] = ("altar", a)
					if ch.body == 7:  # Marcella: gold per tributed gem
						gold[i] += int(EC.settings()["marcella_gold"] * plan[i][-1]["gems"])
					continue
			# 3. next group. Options: solo (rate = value / (travel + respawn wait + kill + capture)) or a coalition with the m - 1
			# other bodies that can be at the group soonest (free within 40 rounds); a coalition's gain = (value - the others'
			# opportunity cost: their best solo rate on any OTHER group x the rounds the coalition takes from them) / body i's rounds.
			# (Interference: one body or coalition per group and respawn; the reward is not split twice.)
			def solo_options(k, at_round):
				out = []
				for g in range(len(M.groups)):
					if first[k] is not None and g != first[k]:
						continue
					tr = self.travel(loc[k], g, chs[k].body)
					if tr < 0:
						continue
					wait = max(0, respawn_at[g] - (at_round + tr))
					if wait > self.max_wait:
						continue
					r = self.kill(g, [chs[k]], [0], hp_left.get(g), [gold[k]])
					if not r.cleared:
						continue
					val = self.value[g]
					if g in gate_value and self.bank_cost(loc[k], max(1, bag[k]), dead) is None:
						val += gate_value[g]  # no altar usable now: the groups that open one carry the bags' value
					out.append((val / max(1, tr + wait + r.rounds + EC.capture_rounds()), g, tr, wait, r))
				return out

			opts = solo_options(i, now)
			best = None
			for rate, g, tr, wait, r in opts:
				if best is None or rate > best[0]:
					best = (rate, g, tr, wait, r, [i])
			if self.join and n > 1:
				alt = {}
				for k in range(n):
					if k != i and free[k] <= now + 40:
						alt[k] = sorted(((o[0], o[1]) for o in solo_options(k, free[k])), reverse=True)[:3]
				heavy = []
				for rate, g, tr, wait, r in opts:
					if sum(r.trips) or r.rounds >= 25:
						heavy.append((self.value[g], g, tr, wait))
				for g in range(len(M.groups)):  # groups no single body clears at all
					if all(o[1] != g for o in opts) and (first[i] is None or g == first[i]):
						tr = self.travel(loc[i], g, ch.body)
						if tr >= 0 and respawn_at[g] - (now + tr) <= self.max_wait:
							heavy.append((self.value[g], g, tr, max(0, respawn_at[g] - (now + tr))))
				heavy.sort(reverse=True)
				for val0, g, tr, wait in heavy[:6]:
					start = now + tr + wait
					others = []
					for k in alt:
						trk = self.travel(loc[k], g, chs[k].body)
						if trk >= 0:
							others.append((free[k] + trk, k))
					others.sort()
					val = val0 + (gate_value.get(g, 0.0) if self.bank_cost(loc[i], max(1, bag[i]), dead) is None else 0.0)
					for m in range(1, len(others) + 1):
						who = [i] + [k for _, k in others[:m]]
						delays = [0] + [max(0, int(5 * round((t_k - start) / 5))) for t_k, _ in others[:m]]
						rr = self.kill(g, [chs[k] for k in who], delays, hp_left.get(g), [gold[k] for k in who])
						if not rr.cleared:
							continue
						cap = start + rr.rounds + EC.capture_rounds()
						cost = 0.0
						for k in who[1:]:
							ak = next((x[0] for x in alt[k] if x[1] != g), 0.0)
							cost += ak * max(0, cap - free[k])
						gain = (val - cost) / max(1, cap - now)
						if best is None or gain > best[0]:
							best = (gain, g, tr, wait, rr, who)
			first[i] = None
			if best is None:
				free[i] = now + 10  # nothing to do: wait for a respawn
				continue
			rate, g, tr, wait, r, who = best
			first[i] = None
			start = now + tr + wait
			end = start + r.rounds
			cap = end + EC.capture_rounds()
			for j, k in enumerate(who):
				free[k] = cap
				loc[k] = ("group", g)
				chs[k].hp = r.hp_end[j] if r.hp_end else -1
				if getattr(r, "shards", None):
					chs[k].shards, chs[k].emblems = dict(r.shards[j][0]), set(r.shards[j][1])
					gold[k] = r.gold_left[j]
				claim[g] = k
			# the capturer (first body) takes the reward; the group respawns after its timer
			gm = M.groups[g]
			bag[i] += gm["gems"] * self.share[g]  # expected gems: the opponent takes the rest (economy.econ()["contest"]; 1 = unopposed)
			gold_gain = int(gm["gold"] * ch.gold_mult() * self.share[g])
			gold[i] += gold_gain
			gold_earned += gold_gain
			respawn_at[g] = cap + gm["respawn"]
			hp_left.pop(g, None)
			for k in who:
				plan[k].append({"do": "farm", "group": gm["id"], "arrive": now + tr, "start": start, "cleared": end, "captured": cap,
								"with": [x for x in who if x != k]})
			claim.pop(g, None)
		return {"banked": banked, "pace": reached, "gold_earned": gold_earned, "carried": sum(bag), "plan": plan,
				"rounds": min(max(free), until)}


def mirror_plan(ctx, plan):
	"""Team B's plan from team A's (or back): every group id replaced by its mirror group."""
	if plan is None:
		return None
	mg = {ctx.M.groups[g]["id"]: ctx.M.groups[ctx.mirror_group[g]]["id"] for g in range(len(ctx.M.groups)) if ctx.mirror_group[g] is not None}
	out = dict(plan)
	out["first_targets"] = [mg.get(g, g) for g in plan["first_targets"]]
	out["plan"] = [[dict(s, group=mg.get(s["group"], s["group"])) if "group" in s else dict(s) for s in body] for body in plan["plan"]]
	out["mirrored_from"] = "A"
	return out


def plan1(ctx, team, picks, R0=150, top=None, evaluate=40):
	"""The opening (plan 1): every body's first target is searched over its best `top` first targets (by solo rate from spawn; default
	team size + 1); the combinations with distinct groups are ranked by their summed solo rates and the best `evaluate` are each played
	by the planner to round R0 (coalitions allowed after the first targets); objective = banked + 0.5 x carried value at R0."""
	base = Planner(ctx, team, picks)
	n = len(base.bodies)
	top = top or n + 1
	cands = []
	for i, b in enumerate(base.bodies):
		ch = EC.Champ(b)
		rates = []
		for g in range(len(ctx.M.groups)):
			tr = base.travel("spawn", g, b)
			if tr < 0:
				continue
			r = base.kill(g, [ch], [0])
			if not r.cleared:
				continue
			rates.append((base.value[g] / (tr + r.rounds + EC.capture_rounds()), g))
		rates.sort(reverse=True)
		cands.append(rates[:top] or [(0.0, None)])
	combos = []
	for combo in itertools.product(*cands):
		gs = [g for _, g in combo if g is not None]
		if len(set(gs)) < len(gs):
			continue
		combos.append((sum(r for r, _ in combo), [g for _, g in combo]))
		if len(combos) > 20000:
			break
	if not combos:  # fewer groups than bodies: let the bodies share (the planner forms coalitions)
		combos = [(0.0, [c[0][1] for c in cands])]
	combos.sort(key=lambda c: -c[0])
	best = None
	for _, combo in combos[:evaluate]:
		P_ = Planner(ctx, team, picks)
		P_._cache = base._cache
		res = P_.run(until=R0, target=0, first=list(combo))
		val = res["banked"] + 0.5 * res["carried"]
		if best is None or val > best[0]:
			best = (val, combo, res)
	val, combo, res = best
	return {"R0": R0, "value": round(val, 1), "banked": res["banked"], "carried": res["carried"], "first_targets": [
		None if g is None else ctx.M.groups[g]["id"] for g in combo], "bodies": base.bodies, "plan": res["plan"]}


PACE_GOLD_W = 0.02  # default of economy.econ()["pace_gold_w"]: the pace counts gems; gold only buys items


def pace(ctx, team, picks):
	P = Planner(ctx, team, picks, gold_w=EC.econ()["pace_gold_w"])
	res = P.run(until=2000, target=int(EC.settings()["winning_gems"]))
	return {"pace": res["pace"], "banked": res["banked"], "gold_earned": res["gold_earned"]}


# ---------------------------------------------------------------------------------------------------------------------------------
# plan 4: thresholds as functions of the map (values fitted in step 6)

def plan4(ctx, p3):
	M = ctx.M
	d = min_on(ctx.walk_clear[0], M.spawn[1]) if (ctx.walk_clear[0][M.spawn[1]] >= 0).any() else None
	if d is None:
		# spawns not connected on foot: use the spawn-to-spawn distance through the map's bounding box
		d = max(M.W, M.H)
	contested = [g for g in p3["groups"] if g["contested"]]
	import features as FT
	import p4model
	if p4model.model():
		# LEARNED (plan4_learn.py) where the fit beat the formula on held-out maps; per team from its runtime features
		out = {"origin": "LEARNED where plan4_learn.py beat the formula (" + ", ".join(sorted(p4model.model())) + "), else COMPUTED formulas",
			   "spawn_distance": d, "r_enemies": 8, "contested_groups": len(contested)}
		base = [max(3, round(0.12 * d)), 80, max(5, round(0.2 * d)), 8, 3, 30, 0, 0]
		per = [p4model.apply(FT.compute(M, t), base) for t in (0, 1)]
		out.update(k_abandon=per[0][0], p_power=per[0][1] / 100.0, d_regroup=per[0][2], bank_margin=per[0][4], w_max=per[0][5],
				   per_team=[{"k_abandon": v[0], "p_power": v[1] / 100.0, "d_regroup": v[2], "bank_margin": v[4], "w_max": v[5]} for v in per])
		return out
	return {
		"origin": "COMPUTED default formulas; values fitted in step 6 (LEARNED, then SIMULATED)",
		"spawn_distance": d,
		"k_abandon": max(3, round(0.12 * d)),        # abandon a target when ETA_us > ETA_them + k_abandon ...
		"p_power": 0.8,                              # ... and the local power ratio is below p_power
		"d_regroup": max(5, round(0.2 * d)),          # regroup when a body on a contested route is farther than this from an ally
		"r_enemies": 8,                              # ... or 2+ enemies are seen within r_enemies (vision radius)
		"bank_margin": 3,                            # abort a bank trip when our arrival >= their interception - margin
		"contested_groups": len(contested),
		"w_max_rule": "drop a group whose respawn wait exceeds value / (next best group's rate)",
	}
