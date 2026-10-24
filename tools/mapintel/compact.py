#!/usr/bin/env python3
"""The compact runtime plans: the exact Python twin of tools/mapintel/cpp/mapintel/plans.h (MAPAnalysis.md 5.8), for maps the table does not
know. COMPUTED. A bot computes them during the draft (plans 2-4 and the per-group tables on the first draft turn, plan 1 when its roster
is complete); the offline catalog (catalog.py: the detailed fight simulation and the planner) is the reference these approximate.

Inputs: the runtime map view (features.fields: fc / fb per team, the groups and their camps' designs), the roster (draft picks, expanded
to bodies: Cassi & Issac = 2), the engine's champion designs.
Model (per body type b and group g; all in rounds, doubles, the same operation order in both implementations):
  dps_b(g)   = basic + spells: strength x (1 + 1/8 if it has an attack reset) x (1 + adj(g) for Varg's splash)
               + sum of damaging abilities' mod x focus / cooldown (an area spell or a damaging dash landing x (1 + adj(g)))
               adj(g) = mean over g's camps of the number of other camps of g within Chebyshev 1
  kill_b(g)  = sum hp / dps;  damage_b(g) = S(g) / dps, S(g) = sum over the camps in kill order (strength / hp descending) of
               strength x (cumulative hp killed up to and including it)   (a solo body tanks every striking camp; S, adj and the total
               health are computed once per group)
  trips_b(g) = max(0, ceil(damage / (0.7 x hp)) - 1);  trip = min(dU(g), recall 5 + 1) + 1 + dU(g)
  eta_b(g)   = max(0, dU(g) - attack range)   (dU = our fc distance to the group's nearest camp tile)
  work       = kill + trips x trip + capture 6 (computed once per body and group); cycle = travel + work;
               rate = value / cycle, value = gems + 0.1 x gold
Plan 1: each body type's candidate list = its 12 best reached groups by first-target rate; first targets: with a first_scores()
ranking (plan1(picks, rank)), the first n ranked reached groups assigned to the n bodies by the cheapest total of walk + work
(assign_dp); without one, a greedy assignment over
(body, group) pairs by rate (each body and group once: repeatedly the best free pair, ties to the lower body slot, then the lower group
index; equal to a scan of all groups since at most 5 groups are taken before any body's turn), then 3 more targets per body in slot
order from its candidate list by rate from its last group (travel = the Chebyshev distance between the groups' bounding boxes), then one 2-opt
pass (swap two consecutive targets when the body's finishing round drops). Output per body slot: 4 x (group index, planned arrival).
Plan 2: per group the bank altar = argmin over altars of min(Chebyshev distance from the group's box to an approach tile, 6 + fc of that
approach tile); bankable flags from the features' bank modes. Plan 3: contested groups = both reached and |dU - dE| <= band (band =
max(3, round(0.1 x spawn_dist))); up to 16 by value x exp(-|dU - dE| / band), with (index, dU, dE). Plan 4: the threshold formulas, with
the LEARNED ones (plan4_learn.py, p4model.py = model_weights.h p4_thresholds()) written over them where the fit beat the formula.
Draft memory (dmem.h, block at offset 512, MAPAnalysis 5.8): pack() below = the C++ block byte for byte (checked by test_library.py).
Not modelled here (the catalog's fight simulation has them): Ryth's health-scaled strength, Heart of Ruin's missing-health bonus, Prism's
focus per carried gem, shields and heals, allies tanking for each other, shopping."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as EC  # noqa: E402
import features as FT  # noqa: E402
from engine import pick_bodies  # noqa: E402

NSLOT, NTGT, NCON, NGRP, NTOP = 6, 4, 16, 64, 12
VARG = 10                  # body type of Varg (SDK champion_type::varg): his basic attack splashes (engine setting varg_splash 1)
TEST_PICKS = [8, 4, 3, 0, 9]  # the test roster (Ren, Stellar, Cassi & Issac, Ryth, Varg), cut to the team size: test_library.py only
DMEM_OFFSET, DMEM_MAGIC, DMEM_VERSION, DMEM_SIZE = 512, 0xA7, 1, 352


def group_box(g):
	xs = [c[1] for c in g["camps"]]
	ys = [c[2] for c in g["camps"]]
	return min(xs), min(ys), max(xs), max(ys)


def box_dist(a, b):
	dx = max(0, max(a[0], b[0]) - min(a[2], b[2]))
	dy = max(0, max(a[1], b[1]) - min(a[3], b[3]))
	return max(dx, dy)


def adjacency(g):
	"""Mean over the group's camps of the number of other camps of the group within Chebyshev 1 (pairs counted once, times 2)."""
	cs = [(c[1], c[2]) for c in g["camps"]]
	tot = 0
	for i in range(len(cs)):
		for j in range(i + 1, len(cs)):
			if max(abs(cs[i][0] - cs[j][0]), abs(cs[i][1] - cs[j][1])) <= 1:
				tot += 1
	return (2 * tot) / len(cs)


def group_prep(g):
	"""Per group, once: (adjacency, total health, S) with S = sum over camps in kill order (strength / health descending, ties by camp
	index) of strength x the cumulative health killed up to and including that camp."""
	order = sorted(range(len(g["camps"])), key=lambda i: (-EC.camp_stats(g["camps"][i][0])[1] / EC.camp_stats(g["camps"][i][0])[0], i))
	cum, S = 0.0, 0.0
	for i in order:
		hp, st, _ = EC.camp_stats(g["camps"][i][0])
		cum += hp
		S += st * cum
	return adjacency(g), cum, S


def body_model(b, g, prep=None):
	"""(kill rounds, damage taken) for one body of type b solo on group g (the closed form above): (total health / dps, S / dps)."""
	E = EC.engine()
	d = E.champs[b]
	adj, tot, S = prep if prep is not None else group_prep(g)
	reset = any(a["kind"] == "reset" for a in d["abilities"])
	basic = d["str"] * (1.0 + (1.0 / 8.0 if reset else 0.0)) * (1.0 + (adj if b == VARG else 0.0))
	single, area = 0.0, 0.0  # in slot order; the same grouping as plans.h (bit-equal sums)
	for a in d["abilities"]:
		m = a.get("mod", 0.0)
		if m <= 0:
			continue
		if a["kind"] in ("damage", "cc"):
			single += m * d["foc"] / a["cd"]
		elif a["kind"] in ("aoe", "dash"):
			area += m * d["foc"] / a["cd"]
	dps = basic + single + area * (1.0 + adj)
	return tot / dps, S / dps


class Compact:
	def __init__(self, M, team=0):
		self.M, self.t = M, team
		self.C, self.fc, self.fb, self.fn = FT.fields(M, team)
		self.F = FT.compute(M, team)
		e = 1 - team
		self.dU = [self._dmin(self.fc[team], g) for g in M.groups]
		self.dE = [self._dmin(self.fc[e], g) for g in M.groups]
		self.val = [g["gems"] + 0.1 * g["gold"] for g in M.groups]
		self.box = [group_box(g) for g in M.groups]
		self.prep = [group_prep(g) for g in M.groups]
		self._bm = {}

	@staticmethod
	def _dmin(field, g):
		best = -1
		for c in g["camps"]:
			v = int(field[c[2], c[1]])
			if v >= 0 and (best < 0 or v < best):
				best = v
		return best

	def work(self, b, g):
		"""Rounds at group g after arriving: kill + heal trips + capture (the cycle without the travel): kill + trips x trip + 6."""
		E = EC.engine()
		if (b, g) not in self._bm:
			kill, dmg = body_model(b, self.M.groups[g], self.prep[g])
			hp = E.champs[b]["hp"]
			trips = max(0, math.ceil(dmg / (0.7 * hp)) - 1)
			d = self.dU[g]
			trip = min(d, 6) + 1 + d
			self._bm[b, g] = kill + trips * trip + 6.0
		return self._bm[b, g]

	def cycle(self, b, g, travel):
		return travel + self.work(b, g)

	def row(self, b):
		"""Body type b's candidate list: its NTOP best reached groups by first-target rate (value / (walk to attack range + work)),
		ordered by rate descending, then group index; with the rates. NTOP >= NSLOT, so the greedy below equals a full scan."""
		if ("row", b) not in self._bm:
			E = EC.engine()
			rng = E.attack_range(b)
			rate = {g: self.val[g] / (max(0, self.dU[g] - rng) + self.work(b, g)) for g in range(len(self.M.groups)) if self.dU[g] >= 0}
			self._bm["row", b] = (sorted(rate, key=lambda g: (-rate[g], g))[:NTOP], rate)
		return self._bm["row", b]

	def plan1(self, picks, rank=None):
		"""Plan 1. rank = the groups by first_scores() (best first; export_headers.first_rank_py): the first n reached groups of it are
		assigned to the n bodies by the cheapest total of walk to attack range + work (assign_dp; plans.h the same); without it the greedy
		(body, group) pairs by first-target rate. Then 3 more targets per body from its candidate list, one 2-opt pass."""
		E = EC.engine()
		bodies = [b for p in picks for b in pick_bodies(p)][:NSLOT]
		rng = [E.attack_range(b) for b in bodies]
		rows = [self.row(b) for b in bodies]
		plan, done, used = [[] for _ in bodies], set(), set()
		if rank is not None:
			top = [g for g in rank if 0 <= g < len(self.M.groups) and self.dU[g] >= 0][:len(bodies)]
			cost = [[max(0, self.dU[g] - rng[i]) + self.work(b, g) for g in top] for i, b in enumerate(bodies)]
			asg = assign_dp(cost) if top else [None] * len(bodies)
			for i, j in enumerate(asg):
				done.add(i)
				if j is None:
					continue
				g = top[j]
				eta = max(0, self.dU[g] - rng[i])
				plan[i].append([g, eta, eta + self.work(bodies[i], g)])
				used.add(g)
		# greedy first targets: repeatedly the best free (body, group) pair by rate; ties to the lower slot, then the lower group (each
		# body's best free group is the first free entry of its candidate list)
		while True:
			best = None
			for i in range(len(bodies)):
				if i in done:
					continue
				top, rate = rows[i]
				g = next((g for g in top if g not in used), None)
				if g is not None and (best is None or rate[g] > best[0]):
					best = (rate[g], i, g)
			if best is None:
				break
			_, i, g = best
			eta = max(0, self.dU[g] - rng[i])
			plan[i].append([g, eta, eta + self.work(bodies[i], g)])
			used.add(g)
			done.add(i)
		# 3 more targets per body, in slot order, from its candidate list by rate from its last group
		for _ in range(NTGT - 1):
			for i, b in enumerate(bodies):
				if not plan[i]:
					continue
				h, _, end = plan[i][-1]
				best = None
				for g in rows[i][0]:
					if g in used:
						continue
					tr = box_dist(self.box[h], self.box[g])
					r = self.val[g] / (tr + self.work(b, g))
					if best is None or r > best[0]:
						best = (r, g, tr)
				if best:
					g, tr = best[1], best[2]
					plan[i].append([g, end + tr, end + (tr + self.work(b, g))])
					used.add(g)
		# one 2-opt pass: swap consecutive targets k, k+1 (k >= 1) when the body finishes sooner
		for i, b in enumerate(bodies):
			for k in range(1, len(plan[i]) - 1):
				seq = [p[0] for p in plan[i]]
				alt = seq[:k] + [seq[k + 1], seq[k]] + seq[k + 2:]
				ta = self.timeline(b, alt)
				if ta[-1][2] < plan[i][-1][2]:
					plan[i] = ta
		return bodies, plan

	def timeline(self, b, seq):
		E = EC.engine()
		out, t, prev = [], 0.0, None
		for g in seq:
			tr = max(0, self.dU[g] - E.attack_range(b)) if prev is None else box_dist(self.box[prev], self.box[g])
			c = tr + self.work(b, g)
			out.append([g, t + tr, t + c])
			t += c
			prev = g
		return out

	def bank_altars(self):
		M, t = self.M, self.t
		out = []
		for g in range(len(M.groups)):
			best = (None, 1 << 30)
			for a, (ax, ay) in enumerate(M.altar_tiles):
				for dy in (-1, 0, 1):
					for dx in (-1, 0, 1):
						x, y = ax + dx, ay + dy
						if (dx, dy) == (0, 0) or not (0 <= x < M.W and 0 <= y < M.H) or not self.C[t][y, x]:
							continue
						walk = box_dist(self.box[g], (x, y, x, y))
						f = int(self.fc[t][y, x])
						c = min(walk, 6 + f) if f >= 0 else walk
						if c < best[1]:
							best = (a, c)
			out.append(best[0] if best[0] is not None else 255)
		return out

	def contested(self):
		sd = self.F[FT.NAMES.index("spawn_dist")]
		band = max(3, int(math.floor(0.1 * (sd if sd > 0 else max(self.M.W, self.M.H)) + 0.5)))
		rows = []
		for g in range(len(self.M.groups)):
			a, b = self.dU[g], self.dE[g]
			if a >= 0 and b >= 0 and abs(a - b) <= band:
				rows.append((self.val[g] * math.exp(-abs(a - b) / band), g, a, b))
		rows.sort(key=lambda r: (-r[0], r[1]))
		return band, [[g, a, b] for _, g, a, b in rows[:NCON]]

	def tiebreak_mode(self):
		"""0 both teams can bank, 1 neither (gold earned, then kills), 2 only the enemy, 3 only us (bank_mode features: 2 = cannot)."""
		us = self.F[FT.NAMES.index("bank_mode")] < 2
		them = self.F[FT.NAMES.index("bank_mode_enemy")] < 2
		return 0 if us and them else 1 if not us and not them else 2 if them else 3

	def formula_thresholds(self):
		"""Plan 4's formulas on the runtime spawn distance (plans.h p4_formula()): k_abandon, p (percent), d_regroup, r_enemies, bank
		margin, w_max, 0, 0."""
		sd = self.F[FT.NAMES.index("spawn_dist")]
		d = sd if sd > 0 else max(self.M.W, self.M.H)
		return [max(3, int(math.floor(0.12 * d + 0.5))), 80, max(5, int(math.floor(0.2 * d + 0.5))), 8, 3, 30, 0, 0]  # p in percent

	def thresholds(self):
		"""Plan 4: the formulas, with the LEARNED thresholds of plan4_learn.py written over them where the fit beat the formula
		(p4model.py = model_weights.h p4_thresholds())."""
		import p4model
		return p4model.apply(self.F, self.formula_thresholds())


def assign_dp(cost):
	"""The cheapest assignment of rows (bodies, in slot order) to distinct columns (groups) of a cost matrix (at most 6 x 6): a dynamic
	program over the sets of used columns, masks in increasing order, columns in increasing order, a strictly cheaper sum wins (plans.h
	detail::assign_dp: the same sums in the same order). With fewer columns than rows, the last rows get None."""
	n, m = len(cost), len(cost[0]) if cost else 0
	k = min(n, m)
	INF = float("inf")
	dp = [INF] * (1 << m)
	par = [-1] * (1 << m)
	dp[0] = 0.0
	for mask in range(1 << m):
		i = bin(mask).count("1")
		if dp[mask] == INF or i >= k:
			continue
		for j in range(m):
			if not mask >> j & 1:
				v = dp[mask] + cost[i][j]
				if v < dp[mask | 1 << j]:
					dp[mask | 1 << j], par[mask | 1 << j] = v, j
	best = None
	for mask in range(1 << m):
		if bin(mask).count("1") == k and dp[mask] < INF and (best is None or dp[mask] < dp[best]):
			best = mask
	out = [None] * n
	mask, i = best if best is not None else 0, k - 1
	while mask:
		j = par[mask]
		out[i] = j
		mask ^= 1 << j
		i -= 1
	return out


def assign_greedy(cost):
	"""Rows (bodies) to distinct columns (groups): repeatedly the cheapest free (row, column) pair, ties to the lower row, then the lower
	column (plans.h detail::assign_greedy). Rows beyond the columns get None."""
	n, m = len(cost), len(cost[0]) if cost else 0
	out, used = [None] * n, set()
	for _ in range(min(n, m)):
		best = None
		for i in range(n):
			if out[i] is not None:
				continue
			for j in range(m):
				if j not in used and (best is None or cost[i][j] < best[0]):
					best = (cost[i][j], i, j)
		out[best[1]] = best[2]
		used.add(best[2])
	return out


def r16(x):
	return max(0, min(65535, int(math.floor(x + 0.5))))


def pack(C, fingerprint, picks=None, known=False, archetype=255, rank=None):
	"""The draft-memory block (DMEM_SIZE bytes, written at DMEM_OFFSET), layout of dmem.h:
	  0 magic 0xA7, 1 version, 2-9 fingerprint (little endian), 10 flags (bit 0 known map, bit 1 we can bank, bit 2 they can bank, bits 3-4
	  tiebreak mode, bit 5 plan 1 present), 11 archetype (255 = none), 12 team size, 13 groups (<= 64), 14 contested band, 15 contested
	  count, 16 bodies, 17-22 body types (255 = none), 23-86 bank altar per group (255 = none), 87-150 dU per group, 151-214 dE per group
	  (255 = not reached or >= 255), 215-262 16 x (group, dU, dE), 263-278 8 thresholds (uint16), 279-350 plan 1: 6 slots x 4 x (group,
	  arrival round uint16), 351 checksum (sum of bytes 0-350 mod 256)."""
	b = bytearray(DMEM_SIZE)
	b[0], b[1] = DMEM_MAGIC, DMEM_VERSION
	for k in range(8):
		b[2 + k] = (fingerprint >> (8 * k)) & 0xFF
	mode = C.tiebreak_mode()
	us = C.F[FT.NAMES.index("bank_mode")] < 2
	them = C.F[FT.NAMES.index("bank_mode_enemy")] < 2
	b[10] = (1 if known else 0) | (2 if us else 0) | (4 if them else 0) | (mode << 3) | (32 if picks else 0)
	b[11] = archetype & 0xFF
	b[12] = max(0, C.M.team_size) & 0xFF
	G = min(len(C.M.groups), NGRP)
	b[13] = G
	band, con = C.contested()
	b[14], b[15] = min(255, band), len(con)
	bank = C.bank_altars()
	cl = lambda v: 255 if v < 0 or v > 254 else v  # noqa: E731
	for g in range(NGRP):
		b[23 + g] = bank[g] if g < G else 255
		b[87 + g] = cl(C.dU[g]) if g < G else 255
		b[151 + g] = cl(C.dE[g]) if g < G else 255
	for k in range(NCON):
		if k < len(con):
			b[215 + 3 * k], b[216 + 3 * k], b[217 + 3 * k] = con[k][0], cl(con[k][1]), cl(con[k][2])
		else:
			b[215 + 3 * k] = b[216 + 3 * k] = b[217 + 3 * k] = 255
	for k, v in enumerate(C.thresholds()):
		b[263 + 2 * k], b[264 + 2 * k] = v & 0xFF, (v >> 8) & 0xFF
	bodies, plan = C.plan1(picks, rank) if picks else ([], [])
	b[16] = len(bodies)
	for s in range(NSLOT):
		b[17 + s] = bodies[s] if s < len(bodies) else 255
		for k in range(NTGT):
			o = 279 + 12 * s + 3 * k
			if s < len(plan) and k < len(plan[s]):
				a = r16(plan[s][k][1])
				b[o], b[o + 1], b[o + 2] = plan[s][k][0], a & 0xFF, a >> 8
			else:
				b[o], b[o + 1], b[o + 2] = 255, 255, 255
	b[351] = sum(b[:351]) & 0xFF
	return bytes(b)
