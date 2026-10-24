// teamplan/kit.h: what a champion's kit is worth, computed from the engine's design (base stats, growths, the two abilities, the
// passive tag and the SDK constant behind it). No champion names: a patch that changes a number, or a new champion, changes the
// result by itself. Python twin: tools/teamplan/kit.py (bit-equal; tools/teamplan/test_teamplan.py).
//
// All arithmetic is double on the engine's float values, in a fixed order, with + - * / and comparisons only, so the twin is exact.
#pragma once
#include <cstdint>

#include "params.h"

namespace teamplan
{
// Ability tags (our own; sdk_bridge.h maps the SDK's ability payloads to them).
enum : std::uint8_t
{
	AB_NONE = 0,
	AB_RESET,
	AB_DAMAGE,
	AB_AOE,
	AB_CC,
	AB_HEAL,
	AB_DASH,
	AB_SHIELD
};
// Passive tags: the SDK's passive_type values.
enum : std::uint8_t
{
	PS_NONE = 0,
	PS_BONUS_GOLD = 1,
	PS_REMOTE_SHOP = 2,
	PS_GEM_FOCUS = 3,
	PS_SPLASH = 4,
	PS_HEALTH_STRENGTH = 5,
	PS_RESET_ON_KILL = 6,
	PS_RETALIATION = 7,
	PS_STUN_IMMUNE = 8,
	PS_MISSING_HEALTH = 10
};

struct Ability
{
	std::uint8_t kind = AB_NONE, enhanced = 0;
	double range = 0, mod = 0, radius = 0;
	int dur = 0, cd = 0;
};

struct Design
{
	double hp = 0, hp_g = 0, str = 0, str_g = 0, foc = 0, foc_g = 0, campmul = 1;
	int range = 1, move = 1, vision = 8;
	std::uint8_t passive = PS_NONE;
	Ability ab[2];
};

// Engine constants the kit needs (sdk_bridge.h fills them from the SDK; the passive constants belong to their passive tag).
struct Consts
{
	double bonus_gold_pct = 0, focus_per_gem = 0, health_strength_ratio = 0, retaliation_ratio = 0, missing_health_bonus = 0;
	double tribute_gold_per_gem = 0, shard_cost = 30;
	int respawn_time = 60, capture_time = 5, max_rounds = 2000, winning_gems = 1000, kill_gold = 100;
};

struct Kit
{
	std::uint8_t melee = 0, has_dash = 0, stun_immune = 0, splash = 0, remote_shop = 0, reset_on_kill = 0;
	double hp = 0, resets = 0, basic = 0, spell = 0, spell_mod = 0, area = 0, area_mod = 0, stun = 0, shield = 0, heal = 0;
	double dash_range = 0, reach = 0, gold_mult = 1, tribute_gold = 0, focus_per_gem = 0, retaliation = 0, mhp_bonus = 0, str_per_hp = 0;
	double dps = 0, camp_dps = 0, ehp = 0;
	double dmg_str_shard = 0, dmg_foc_shard = 0, dmg_hp_shard = 0, w_gold = 0;
	double exposure = 1, front = 0;
};

inline double kmax(double a, double b) { return a > b ? a : b; }

// The kit of one design. Units: damage per round (basic attacks and spells per cooldown), health points, gold.
inline Kit compute_kit(const Design& d, const Consts& c, const Params& p)
{
	Kit k;
	k.hp = d.hp;
	k.melee = d.range <= 1 ? 1 : 0;
	k.reach = d.range;
	for (int s = 0; s < 2; ++s)
	{
		const Ability& a = d.ab[s];
		const double cd = a.cd > 0 ? static_cast<double>(a.cd) : 1.0;
		switch (a.kind)
		{
		case AB_RESET:
			k.resets += (1.0 + (a.enhanced ? p.enhanced_extra : 0.0)) / cd;
			if (a.enhanced)
				k.stun += p.enhanced_stun / cd;
			break;
		case AB_DAMAGE:
			k.spell += a.mod * d.foc / cd;
			k.spell_mod += a.mod / cd;
			k.reach = kmax(k.reach, a.range);
			break;
		case AB_AOE:
			k.spell += a.mod * d.foc / cd;
			k.spell_mod += a.mod / cd;
			k.area += a.mod * d.foc / cd;
			k.area_mod += a.mod / cd;
			if (a.dur > 0)
				k.stun += a.dur / cd;
			k.reach = kmax(k.reach, a.range + a.radius);
			break;
		case AB_CC:
			k.spell += a.mod * d.foc / cd;
			k.spell_mod += a.mod / cd;
			if (a.dur > 0)
				k.stun += a.dur / cd;
			k.reach = kmax(k.reach, a.range);
			break;
		case AB_HEAL:
			k.heal += a.mod * d.foc / cd;
			break;
		case AB_DASH:
			k.has_dash = 1;
			k.dash_range = kmax(k.dash_range, a.range);
			if (a.mod > 0)
			{
				k.spell += a.mod * d.foc / cd;
				k.spell_mod += a.mod / cd;
				if (a.radius > 0)
				{
					k.area += a.mod * d.foc / cd;
					k.area_mod += a.mod / cd;
				}
				k.reach = kmax(k.reach, a.range + a.radius);
			}
			if (a.dur > 0)
				k.stun += a.dur / cd;
			break;
		case AB_SHIELD:
			k.shield += a.mod * d.foc / cd;
			break;
		default:
			break;
		}
	}
	k.basic = d.str * (1.0 + k.resets);
	k.gold_mult = 1.0 + (d.passive == PS_BONUS_GOLD ? c.bonus_gold_pct / 100.0 : 0.0);
	k.stun_immune = d.passive == PS_STUN_IMMUNE ? 1 : 0;
	k.tribute_gold = d.passive == PS_STUN_IMMUNE ? c.tribute_gold_per_gem : 0.0;
	k.focus_per_gem = d.passive == PS_GEM_FOCUS ? c.focus_per_gem : 0.0;
	k.splash = d.passive == PS_SPLASH ? 1 : 0;
	k.remote_shop = d.passive == PS_REMOTE_SHOP ? 1 : 0;
	k.reset_on_kill = d.passive == PS_RESET_ON_KILL ? 1 : 0;
	k.retaliation = d.passive == PS_RETALIATION ? c.retaliation_ratio * d.foc : 0.0;
	k.mhp_bonus = d.passive == PS_MISSING_HEALTH ? c.missing_health_bonus : 0.0;
	k.str_per_hp = d.passive == PS_HEALTH_STRENGTH ? c.health_strength_ratio : 0.0;

	const double hit = 1.0 + k.mhp_bonus * p.missing_hp_avg;
	k.dps = (k.basic + k.spell) * hit + k.retaliation * p.hits_taken + (k.splash ? k.basic * p.splash_targets : 0.0) + k.area * p.area_targets;
	k.camp_dps = (k.basic + k.spell) * d.campmul;
	k.ehp = d.hp * (1.0 + (k.stun_immune ? p.immune_ehp : 0.0)) + p.fight_rounds * (k.shield + k.heal);

	// one shard = one point of its stat (the stat's growth)
	const double per_basic = (1.0 + k.resets) * (1.0 + (k.splash ? p.splash_targets : 0.0)) * hit;
	k.dmg_str_shard = d.str_g * per_basic;
	k.dmg_foc_shard = d.foc_g * (k.spell_mod * hit + k.area_mod * p.area_targets) +
					  (d.passive == PS_RETALIATION ? c.retaliation_ratio * d.foc_g * p.hits_taken : 0.0);
	k.dmg_hp_shard = k.str_per_hp * d.hp_g * per_basic;
	if (k.dps > 0 && k.ehp > 0 && c.shard_cost > 0)
	{
		double best = kmax(k.dmg_str_shard / k.dps, k.dmg_foc_shard / k.dps);
		best = kmax(best, d.hp_g / k.ehp + k.dmg_hp_shard / k.dps);
		k.w_gold = best / c.shard_cost;
	}

	double e = k.melee ? 1.0 : 1.0 - p.reach_escape * (d.range - 1);
	if (k.has_dash)
		e = e * (1.0 - p.dash_escape);
	k.exposure = e < 0.3 ? 0.3 : e;
	k.front = k.ehp * (k.melee ? 1.0 : p.ranged_front);
	return k;
}

// Value of one more gold to a body that owns `items` items (diminishing returns), in relative-power units per gold.
inline double gold_weight(const Kit& k, int items, const Params& p) { return p.items_half > 0 ? k.w_gold / (1.0 + items / p.items_half) : k.w_gold; }

// The team's front order: body slots sorted by Kit::front, highest first (ties: lower slot). Returns the count written.
inline int front_order(const Kit* kits, int n, std::uint8_t* out)
{
	for (int i = 0; i < n; ++i)
		out[i] = static_cast<std::uint8_t>(i);
	for (int i = 1; i < n; ++i)
		for (int j = i; j > 0; --j)
		{
			const Kit &a = kits[out[j - 1]], &b = kits[out[j]];
			if (b.front > a.front || (b.front == a.front && out[j] < out[j - 1]))
			{
				const std::uint8_t t = out[j];
				out[j] = out[j - 1];
				out[j - 1] = t;
			}
			else
				break;
		}
	return n;
}

// Two bodies may swap jobs when they are the same kit class (melee or not), or their front scores are within `tol` of each other.
inline bool can_swap(const Kit& a, const Kit& b, double tol)
{
	if (a.melee == b.melee)
		return true;
	const double hi = kmax(a.front, b.front), lo = a.front < b.front ? a.front : b.front;
	return hi > 0 && (hi - lo) / hi < tol;
}
} // namespace teamplan
