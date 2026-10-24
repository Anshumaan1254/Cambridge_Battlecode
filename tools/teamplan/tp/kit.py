"""Twin of kit.h."""
AB_NONE, AB_RESET, AB_DAMAGE, AB_AOE, AB_CC, AB_HEAL, AB_DASH, AB_SHIELD = range(8)
PS_NONE, PS_BONUS_GOLD, PS_REMOTE_SHOP, PS_GEM_FOCUS, PS_SPLASH, PS_HEALTH_STRENGTH, PS_RESET_ON_KILL, PS_RETALIATION, PS_STUN_IMMUNE = range(9)
PS_MISSING_HEALTH = 10

FIELDS = ["melee", "has_dash", "stun_immune", "splash", "remote_shop", "reset_on_kill", "hp", "resets", "basic", "spell", "spell_mod", "area",
		  "area_mod", "stun", "shield", "heal", "dash_range", "reach", "gold_mult", "tribute_gold", "focus_per_gem", "retaliation", "mhp_bonus",
		  "str_per_hp", "dps", "camp_dps", "ehp", "dmg_str_shard", "dmg_foc_shard", "dmg_hp_shard", "w_gold", "exposure", "front"]


class Kit:
	def __init__(self):
		for f in FIELDS:
			setattr(self, f, 0.0)
		self.melee = self.has_dash = self.stun_immune = self.splash = self.remote_shop = self.reset_on_kill = 0
		self.gold_mult = 1.0
		self.exposure = 1.0

	def values(self):
		return [getattr(self, f) for f in FIELDS]


def kmax(a, b):
	return a if a > b else b


def compute_kit(d, c, p):
	k = Kit()
	k.hp = d.hp
	k.melee = 1 if d.range <= 1 else 0
	k.reach = float(d.range)
	for a in d.ab:
		cd = float(a.cd) if a.cd > 0 else 1.0
		if a.kind == AB_RESET:
			k.resets += (1.0 + (p.enhanced_extra if a.enhanced else 0.0)) / cd
			if a.enhanced:
				k.stun += p.enhanced_stun / cd
		elif a.kind == AB_DAMAGE:
			k.spell += a.mod * d.foc / cd
			k.spell_mod += a.mod / cd
			k.reach = kmax(k.reach, a.range)
		elif a.kind == AB_AOE:
			k.spell += a.mod * d.foc / cd
			k.spell_mod += a.mod / cd
			k.area += a.mod * d.foc / cd
			k.area_mod += a.mod / cd
			if a.dur > 0:
				k.stun += a.dur / cd
			k.reach = kmax(k.reach, a.range + a.radius)
		elif a.kind == AB_CC:
			k.spell += a.mod * d.foc / cd
			k.spell_mod += a.mod / cd
			if a.dur > 0:
				k.stun += a.dur / cd
			k.reach = kmax(k.reach, a.range)
		elif a.kind == AB_HEAL:
			k.heal += a.mod * d.foc / cd
		elif a.kind == AB_DASH:
			k.has_dash = 1
			k.dash_range = kmax(k.dash_range, a.range)
			if a.mod > 0:
				k.spell += a.mod * d.foc / cd
				k.spell_mod += a.mod / cd
				if a.radius > 0:
					k.area += a.mod * d.foc / cd
					k.area_mod += a.mod / cd
				k.reach = kmax(k.reach, a.range + a.radius)
			if a.dur > 0:
				k.stun += a.dur / cd
		elif a.kind == AB_SHIELD:
			k.shield += a.mod * d.foc / cd
	k.basic = d.str * (1.0 + k.resets)
	k.gold_mult = 1.0 + (c.bonus_gold_pct / 100.0 if d.passive == PS_BONUS_GOLD else 0.0)
	k.stun_immune = 1 if d.passive == PS_STUN_IMMUNE else 0
	k.tribute_gold = c.tribute_gold_per_gem if d.passive == PS_STUN_IMMUNE else 0.0
	k.focus_per_gem = c.focus_per_gem if d.passive == PS_GEM_FOCUS else 0.0
	k.splash = 1 if d.passive == PS_SPLASH else 0
	k.remote_shop = 1 if d.passive == PS_REMOTE_SHOP else 0
	k.reset_on_kill = 1 if d.passive == PS_RESET_ON_KILL else 0
	k.retaliation = c.retaliation_ratio * d.foc if d.passive == PS_RETALIATION else 0.0
	k.mhp_bonus = c.missing_health_bonus if d.passive == PS_MISSING_HEALTH else 0.0
	k.str_per_hp = c.health_strength_ratio if d.passive == PS_HEALTH_STRENGTH else 0.0

	hit = 1.0 + k.mhp_bonus * p.missing_hp_avg
	k.dps = (k.basic + k.spell) * hit + k.retaliation * p.hits_taken + (k.basic * p.splash_targets if k.splash else 0.0) + k.area * p.area_targets
	k.camp_dps = (k.basic + k.spell) * d.campmul
	k.ehp = d.hp * (1.0 + (p.immune_ehp if k.stun_immune else 0.0)) + p.fight_rounds * (k.shield + k.heal)

	per_basic = (1.0 + k.resets) * (1.0 + (p.splash_targets if k.splash else 0.0)) * hit
	k.dmg_str_shard = d.str_g * per_basic
	k.dmg_foc_shard = d.foc_g * (k.spell_mod * hit + k.area_mod * p.area_targets) + \
		(c.retaliation_ratio * d.foc_g * p.hits_taken if d.passive == PS_RETALIATION else 0.0)
	k.dmg_hp_shard = k.str_per_hp * d.hp_g * per_basic
	if k.dps > 0 and k.ehp > 0 and c.shard_cost > 0:
		best = kmax(k.dmg_str_shard / k.dps, k.dmg_foc_shard / k.dps)
		best = kmax(best, d.hp_g / k.ehp + k.dmg_hp_shard / k.dps)
		k.w_gold = best / c.shard_cost

	e = 1.0 if k.melee else 1.0 - p.reach_escape * (d.range - 1)
	if k.has_dash:
		e = e * (1.0 - p.dash_escape)
	k.exposure = 0.3 if e < 0.3 else e
	k.front = k.ehp * (1.0 if k.melee else p.ranged_front)
	return k


def gold_weight(k, items, p):
	return k.w_gold / (1.0 + items / p.items_half)


def front_order(kits):
	n = len(kits)
	return sorted(range(n), key=lambda i: (-kits[i].front, i))


def can_swap(a, b, tol):
	if a.melee == b.melee:
		return True
	hi = kmax(a.front, b.front)
	lo = a.front if a.front < b.front else b.front
	return hi > 0 and (hi - lo) / hi < tol
