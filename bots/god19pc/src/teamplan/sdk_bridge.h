// teamplan/sdk_bridge.h: fills teamplan's plain structs from the CAMBC SDK (the only teamplan header that includes cambc.h).
// The passive constants are read per passive tag: the SDK names them after the one champion that has each passive today; if a patch
// gives a passive to another champion, the tag still finds the constant.
#pragma once
#include <cambc.h>

#include <type_traits>
#include <variant>

#include "kit.h"

namespace teamplan
{
inline Ability ability_of(const cambc::ability& a)
{
	Ability out;
	const auto& inf = a.info();
	if (!inf)
		return out;
	std::visit(
		[&](const auto& v) {
			using T = std::decay_t<decltype(v)>;
			out.cd = v.max_cooldown;
			if constexpr (std::is_same_v<T, cambc::ability_attack_reset>)
			{
				out.kind = AB_RESET;
				out.enhanced = v.enhanced_attack ? 1 : 0;
			}
			else if constexpr (std::is_same_v<T, cambc::ability_damage>)
			{
				out.kind = AB_DAMAGE;
				out.range = v.range, out.mod = v.modifier;
			}
			else if constexpr (std::is_same_v<T, cambc::ability_aoe_damage>)
			{
				out.kind = AB_AOE;
				out.range = v.range, out.mod = v.modifier, out.radius = v.radius, out.dur = v.duration;
			}
			else if constexpr (std::is_same_v<T, cambc::ability_cc>)
			{
				out.kind = AB_CC;
				out.range = v.range, out.mod = v.modifier, out.dur = v.duration;
			}
			else if constexpr (std::is_same_v<T, cambc::ability_heal>)
			{
				out.kind = AB_HEAL;
				out.range = v.range, out.mod = v.modifier;
			}
			else if constexpr (std::is_same_v<T, cambc::ability_dash>)
			{
				out.kind = AB_DASH;
				out.range = v.range, out.mod = v.modifier, out.radius = v.radius, out.dur = v.duration;
			}
			else if constexpr (std::is_same_v<T, cambc::ability_shield>)
			{
				out.kind = AB_SHIELD;
				out.range = v.range, out.mod = v.modifier, out.dur = v.duration;
			}
		},
		*inf);
	return out;
}

// Body type t (0-12, the SDK's champion_type order).
inline Design design_of(int t)
{
	Design d;
	const auto& c = cambc::champion_designs[static_cast<std::size_t>(t)];
	const auto s = c.base_stats();
	d.hp = s.base_health, d.hp_g = s.health_growth, d.str = s.base_strength, d.str_g = s.strength_growth;
	d.foc = s.base_focus, d.foc_g = s.focus_growth, d.campmul = s.camp_damage_multiplier;
	d.range = s.base_attack_range, d.move = s.base_move_speed, d.vision = s.vision_radius;
	d.passive = static_cast<std::uint8_t>(c.passive());
	const auto abs = c.abilities();
	for (int i = 0; i < 2; ++i)
		d.ab[i] = ability_of(abs[static_cast<std::size_t>(i)]);
	return d;
}

inline Consts consts_from_sdk()
{
	namespace k = cambc::constants;
	namespace pa = cambc::constants::passive_abilities;
	Consts c;
	c.bonus_gold_pct = pa::vesper_vale_bonus_gold_percent;		  // passive bonus_gold
	c.focus_per_gem = pa::prism_focus_per_gem;					  // passive gem_focus
	c.health_strength_ratio = pa::ryth_health_strength_ratio;	  // passive health_strength
	c.retaliation_ratio = pa::ren_retaliation_focus_ratio;		  // passive retaliation
	c.missing_health_bonus = pa::heart_of_ruin_missing_health_damage_max_bonus; // passive missing_health_damage
	c.tribute_gold_per_gem = pa::marcella_tribute_gold_per_gem;	  // passive stun_immunity (gold per gem tributed)
	c.shard_cost = cambc::item_type(cambc::item_type::enum_type::power_shard_of_strength).cost();
	c.respawn_time = k::respawn_time, c.capture_time = k::capture_time;
	c.max_rounds = static_cast<int>(k::max_rounds), c.winning_gems = static_cast<int>(k::winning_gems), c.kill_gold = static_cast<int>(k::kill_gold);
	return c;
}
} // namespace teamplan
