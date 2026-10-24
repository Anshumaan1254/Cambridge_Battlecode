#!/usr/bin/env python3
"""Full-cycle economy model of tools/mapintel (MAPAnalysis.md 5.3c, the user's correction 1.4). COMPUTED from the engine's designs
(engine.py) and the map (mapdata.py); the engine rules it relies on were probed on 3.0.5 (MAPAnalysis.md 7.6).

Pieces (each a function, so plans.py and the catalog can combine them):
  * Champ: a body's current stats (base + shards from the designs' growth), emblem passives (Monster +10% camp damage, Jungle -30% camp
    damage taken, Durability -10% damage taken, Treasure +20% gold), cooldowns.
  * fight(): a per-round simulation of bodies clearing one camp group, as the engine plays it: camps act first and each awake camp hits
    the NEAREST champion within its range (Chebyshev; probed: a wolf hit the nearer Vendetta, not its attacker Stellar); a group wakes when
    damaged and sleeps after 2 rounds with no champion in range, keeping its damage (probed: no regeneration); bodies stand on chosen tiles
    (attacks and spells need the caster's own line of sight: the engine's vision table M.los); basic attack once a round (+1 per attack
    reset, cooldown 8; Vendetta's resets come back on every kill), damaging spells when ready (single target range 4, areas range 4
    radius 1), Varg's splash (strength to every other camp within radius 1 of the target), Ren's retaliation (0.2 x focus to a camp that
    hits him), Heart of Ruin's missing-health bonus (up to +50%) and dash landing (1.5 x focus, radius 1, stun), stuns (a stunned camp
    skips its next attack), shields (Varg 2.5 x focus, Heart of Ruin 1.5 x focus, 5 turns), Willow's ally heal (3 x focus). A body below
    its retreat line leaves, goes home (the cheaper of walking and recall: 5 turns, safe once out of every camp's range) and comes back
    full: heal trips are part of the fight's length.
  * kill order: camps by strength / health descending (Smith's rule: least damage taken); clusters (strength 0) last.
  * capture: 6 rounds counting the arrival round (probed: on the tile in round r, reward at round r + 6); tribute max(1, ceil(bag / 10))
    turns at a legal approach tile (probed: 7 gems, one tick, banked the next turn); getting home is a choice (walk / recall / bank at a
    nearby altar on the way), never assumed; respawn timers from the runtime groups (an occupied spawn tile holds the respawn).
Interference between teammates and the multi-body pace come from plans.py (joint assignment over the groups)."""
import math
import os
import sys
from dataclasses import dataclass, field

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Engine, pick_bodies  # noqa: E402

_E = None


def engine():
	global _E
	if _E is None:
		_E = Engine()
	return _E


S = None  # game settings (engine().settings)


def settings():
	return engine().settings


@dataclass
class Champ:
	body: int
	shards: dict = field(default_factory=lambda: {"str": 0, "hp": 0, "foc": 0})
	emblems: set = field(default_factory=set)  # passives: 'monster', 'jungle', 'durability', 'treasure', 'home'
	hp: float = -1.0

	def d(self):
		return engine().champs[self.body]

	def max_hp(self):
		d = self.d()
		return d["hp"] + d["hp_growth"] * self.shards["hp"]

	def strength(self):
		d = self.d()
		s = d["str"] + d["str_growth"] * self.shards["str"]
		if self.body == 0:  # Ryth: + ryth_ratio x bonus health
			s += settings()["ryth_ratio"] * d["hp_growth"] * self.shards["hp"]
		return s

	def focus(self, bag=0):
		d = self.d()
		f = d["foc"] + d["foc_growth"] * self.shards["foc"]
		if self.body == 6:  # Prism: focus per carried gem
			f += settings()["prism_focus_per_gem"] * bag
		return f

	def abilities(self):
		return self.d()["abilities"]

	def attack_range(self):
		return int(self.d()["range"])

	def camp_mult(self):
		return float(self.d().get("campmul", 1.0)) * (1.1 if "monster" in self.emblems else 1.0)

	def taken_mult_camp(self):
		m = 1.0
		if "durability" in self.emblems:
			m *= 0.9
		if "jungle" in self.emblems:
			m *= 0.7
		return m

	def gold_mult(self):
		g = 1.0
		if self.body == 1:
			g += settings()["vesper_gold"] / 100.0
		if "treasure" in self.emblems:
			g += 0.2
		return g


def cheb(a, b):
	return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def camp_stats(ctype):
	c = engine().camps[ctype]
	return c["hp"], c["str"], int(c["range"])


# ---------------------------------------------------------------------------------------------------------------------------------
# standing tiles

def standable(M, team, x, y, dead=()):
	"""A body of `team` can stand on (x, y): in bounds, not wall / hole / altar / the other team's spawn, not a living camp's tile."""
	if not (0 <= x < M.W and 0 <= y < M.H):
		return False
	if M.walls[y, x] or M.holes[y, x] or M.altars[y, x] or M.spawn[1 - team][y, x]:
		return False
	if (x, y) in M.camp_type and (x, y) not in dead:
		return False
	return True


def sees(M, tile, camp):
	"""The engine's vision table: camp tile visible from tile (both within Chebyshev 5)."""
	s = M.los.get(tile)
	return s is not None and camp in s


def threat_at(M, tile, alive):
	"""Sum of the strengths of living camps whose own range covers tile (the same for every champion)."""
	t = 0.0
	for c in alive:
		hp, st, rg = camp_stats(M.camp_type[c])
		if st > 0 and cheb(tile, c) <= rg:
			t += st
	return t


def best_tile(M, team, ch, camps, alive, dead, prefer=None, spell_only=False):
	"""Standing tile for body ch against the group's camps: a tile from which it hits (basic attack range, or range 4 for spell-only
	casters) the most living camps it can see, with the least camp threat, nearest to `prefer` (a distance field) on ties."""
	rng = 4 if spell_only else ch.attack_range()
	cand = {}
	for (cx, cy) in camps:
		for dy in range(-rng, rng + 1):
			for dx in range(-rng, rng + 1):
				t = (cx + dx, cy + dy)
				if t in cand or not standable(M, team, t[0], t[1], dead):
					continue
				hits = sum(1 for c in alive if cheb(t, c) <= rng and sees(M, t, c))
				if hits == 0:
					continue
				thr = threat_at(M, t, alive)
				far = prefer[t[1], t[0]] if prefer is not None and prefer[t[1], t[0]] >= 0 else 9999
				cand[t] = (-hits, thr, far)
	if not cand:
		return None
	return min(cand, key=lambda t: cand[t])


# ---------------------------------------------------------------------------------------------------------------------------------
# the fight

@dataclass
class FightResult:
	rounds: int  # rounds from the first hit to the last camp's death (heal trips included)
	damage: list  # damage taken per body
	trips: list  # heal trips per body
	cleared: bool
	tiles: list  # standing tile per body (first)
	tank: int  # body index that took the most damage


def fight(M, team, champs, group, home_dist, retreat=0.3, max_rounds=1500, tiles=None):
	"""Simulate champs (list of Champ, full health unless ch.hp >= 0) clearing group (a dict of mapdata). home_dist: walking distance
	field to our spawn (for heal trips). Bodies start in place at their standing tiles (travel is counted by the caller)."""
	camps = [(c[1], c[2]) for c in group["camps"]]
	hp = {}
	for c in group["camps"]:
		hp[(c[1], c[2])] = camp_stats(c[0])[0]
	str_ = {(c[1], c[2]): camp_stats(c[0])[1] for c in group["camps"]}
	rng_ = {(c[1], c[2]): camp_stats(c[0])[2] for c in group["camps"]}
	order = sorted(camps, key=lambda c: (-(str_[c] / hp[c]), c))  # Smith's rule
	n = len(champs)
	cur = [ch.hp if ch.hp >= 0 else ch.max_hp() for ch in champs]
	shield = [0.0] * n
	shield_t = [0] * n
	cd = [[0, 0] for _ in champs]  # per ability slot: rounds until ready
	away = [0] * n  # rounds until back from a heal trip (0 = present)
	trips = [0] * n
	taken = [0.0] * n
	stunned = {}
	dead = set()
	pos = [None] * n
	spell_only = [False] * n
	for i, ch in enumerate(champs):
		# a ranged caster whose single-target spells reach 4 stands at 4 only if no basic-attack tile exists; else basic range
		pos[i] = tiles[i] if tiles and tiles[i] else best_tile(M, team, ch, camps, camps, dead, prefer=home_dist)
		if pos[i] is None:
			pos[i] = best_tile(M, team, ch, camps, camps, dead, prefer=home_dist, spell_only=True)
			spell_only[i] = True
	first_tiles = list(pos)
	if all(p is None for p in pos):
		return FightResult(0, taken, trips, False, first_tiles, -1)
	awake_quiet = 99
	awake = False
	t = 0
	while t < max_rounds:
		alive = [c for c in order if hp[c] > 0]
		if not alive:
			break
		t += 1
		present = [i for i in range(n) if away[i] == 0 and pos[i] is not None]
		# camps act first
		if awake:
			in_range_any = False
			for c in alive:
				if str_[c] <= 0:
					continue
				if stunned.get(c, 0) > 0:
					stunned[c] -= 1
					continue
				best, bd = None, 99
				for i in present:
					d = cheb(pos[i], c)
					if d <= rng_[c] and d < bd:
						best, bd = i, d
				if best is None:
					continue
				in_range_any = True
				dmg = str_[c] * champs[best].taken_mult_camp()
				if shield[best] > 0:
					a = min(shield[best], dmg)
					shield[best] -= a
					dmg -= a
				cur[best] -= dmg
				taken[best] += dmg
				if champs[best].body == 9:  # Ren retaliates
					hp[c] -= settings()["ren_ret"] * champs[best].focus() * champs[best].camp_mult()
			awake_quiet = 0 if in_range_any else awake_quiet + 1
			if awake_quiet >= int(settings()["camp_sleep_time"]):
				awake = False
		# bodies act
		for i in present:
			ch = champs[i]
			if cur[i] < retreat * ch.max_hp():
				continue
			alive = [c for c in order if hp[c] > 0]
			if not alive:
				break
			# melee: step toward the current target (one step, then attack in the same turn)
			tgt = alive[0]
			rng = 4 if spell_only[i] else ch.attack_range()
			if ch.attack_range() <= 1 and cheb(pos[i], tgt) > 1:
				nb = [(pos[i][0] + dx, pos[i][1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
				nb = [q for q in nb if standable(M, team, q[0], q[1], dead) and q not in pos]
				if nb:
					pos[i] = min(nb, key=lambda q: (cheb(q, tgt), threat_at(M, q, alive)))
			bonus = 1.0
			if ch.body == 12:  # Heart of Ruin: up to +50% at 0 health
				bonus += settings()["hor_bonus"] * max(0.0, 1.0 - cur[i] / ch.max_hp())
			mult = ch.camp_mult() * bonus
			hit_any = False
			# one successful cast a round: the first ready damaging / stun / shield / heal ability that applies
			cast = False
			for slot, ab in enumerate(ch.abilities()):
				if cast or cd[i][slot] > 0:
					continue
				k = ab["kind"]
				if k in ("damage", "cc"):
					tg = [c for c in alive if cheb(pos[i], c) <= ab["range"] and sees(M, pos[i], c)]
					if not tg:
						continue
					c = tgt if tgt in tg else max(tg, key=lambda q: str_[q])
					dmg = ab.get("mod", 0) * ch.focus() * mult
					if dmg > 0:
						hp[c] -= dmg
					if k == "cc":
						stunned[c] = stunned.get(c, 0) + int(ab.get("dur", 1))
					cd[i][slot] = int(ab["cd"])
					cast = hit_any = True
				elif k == "aoe":
					best, bn = None, 0
					for c in alive:
						for dx in (-1, 0, 1):
							for dy in (-1, 0, 1):
								g = (c[0] + dx, c[1] + dy)
								if cheb(pos[i], g) > ab["range"]:
									continue
								cov = [q for q in alive if cheb(g, q) <= ab.get("radius", 1)]
								if len(cov) > bn or (len(cov) == bn and best is not None and tgt in cov):
									best, bn = (g, cov), len(cov)
					if best is None:
						continue
					for q in best[1]:
						hp[q] -= ab.get("mod", 0) * ch.focus() * mult
						if ab.get("dur", 0) > 0:
							stunned[q] = stunned.get(q, 0) + int(ab["dur"])
					cd[i][slot] = int(ab["cd"])
					cast = hit_any = True
				elif k == "dash" and ab.get("mod", 0) > 0:  # Heart of Ruin's landing: a tile within 2 next to camps
					cov = [q for q in alive if cheb(pos[i], q) <= 1 + 1]
					if not cov:
						continue
					for q in [q for q in alive if cheb(pos[i], q) <= 1]:
						hp[q] -= ab["mod"] * ch.focus() * mult
						stunned[q] = stunned.get(q, 0) + int(ab.get("dur", 1))
					cd[i][slot] = int(ab["cd"])
					cast = hit_any = True
				elif k == "shield" and awake and taken[i] > 0:
					shield[i] = ab["mod"] * ch.focus()
					shield_t[i] = int(ab.get("dur", 5))
					cd[i][slot] = int(ab["cd"])
					cast = True
				elif k == "heal":
					low = [j for j in present if j != i and cur[j] < champs[j].max_hp() - ab["mod"] * ch.focus() and cheb(pos[i], pos[j]) <= ab["range"]]
					if low:
						j = min(low, key=lambda j: cur[j])
						cur[j] = min(champs[j].max_hp(), cur[j] + ab["mod"] * ch.focus())
						cd[i][slot] = int(ab["cd"])
						cast = True
			# basic attack(s): one, plus one when an attack reset is cast this round
			attacks = 1
			for slot, ab in enumerate(ch.abilities()):
				if ab["kind"] == "reset" and cd[i][slot] == 0 and not cast:
					attacks += 1
					cd[i][slot] = int(ab["cd"])
					cast = True
			for _ in range(attacks):
				alive = [c for c in order if hp[c] > 0]
				tg = [c for c in alive if cheb(pos[i], c) <= ch.attack_range() and sees(M, pos[i], c)]
				if not tg:
					break
				c = tgt if tgt in tg else tg[0]
				d = ch.strength() * mult
				hp[c] -= d
				hit_any = True
				if ch.body == 10:  # Varg's splash
					for q in alive:
						if q != c and cheb(q, c) <= settings()["varg_splash"]:
							hp[q] -= ch.strength() * mult
				if hp[c] <= 0 and ch.body == 2:  # Vendetta: a kill resets her cooldowns
					cd[i] = [0, 0]
			if hit_any:
				awake = True
				awake_quiet = 0
		for c in list(hp):
			if hp[c] <= 0:
				dead.add(c)
		# heal trips: a body below the retreat line leaves (out of range, then home and back)
		for i in range(n):
			if away[i] == 0 and pos[i] is not None and cur[i] < retreat * champs[i].max_hp():
				dist = int(home_dist[pos[i][1], pos[i][0]]) if home_dist[pos[i][1], pos[i][0]] >= 0 else 60
				recall = int(settings()["recall_time"]) + 3  # step out of range (~2), recall 5, heal turn
				away[i] = min(dist, recall) + 1 + dist  # home, heal on spawn, walk back
				trips[i] += 1
				cur[i] = champs[i].max_hp()
				shield[i] = 0
			elif away[i] > 0:
				away[i] -= 1
		for i in range(n):
			cd[i] = [max(0, v - 1) for v in cd[i]]
			if shield_t[i] > 0:
				shield_t[i] -= 1
				if shield_t[i] == 0:
					shield[i] = 0
	cleared = all(hp[c] <= 0 for c in camps)
	tank = int(np.argmax(taken)) if any(taken) else -1
	return FightResult(t, taken, trips, cleared, first_tiles, tank)


def tribute_turns(bag):
	s = settings()
	return max(int(s["submit_min"]), int(math.ceil(s["submit_mult"] * bag + s["submit_base"])))


CAPTURE_ROUNDS = None


def capture_rounds():
	"""Rounds a body spends from stepping onto a dead group's tile to holding the reward (probed: arrive r, reward r + 6)."""
	return int(settings()["capture_time"]) + 1


def recall_rounds(home_emblem=False):
	r = int(settings()["recall_time"])
	return int(math.ceil(r / 2)) if home_emblem else r
