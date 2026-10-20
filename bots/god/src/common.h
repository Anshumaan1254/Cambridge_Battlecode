// Shared includes, aliases and tiny helpers used by every module.
#pragma once
#include <cambc.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <optional>
#include <vector>

namespace bc = cambc;
using bc::team;
using bc::vec2;

constexpr std::uint16_t UNREACH = bc::distance_field::unreachable;
constexpr int BIG = 1 << 20;

inline int cheb(vec2 a, vec2 b)
{
	const int dx = a.x > b.x ? a.x - b.x : b.x - a.x;
	const int dy = a.y > b.y ? a.y - b.y : b.y - a.y;
	return dx > dy ? dx : dy;
}

inline std::uint32_t handle_of(const bc::champion& c) { return static_cast<std::uint32_t>(static_cast<bc::handle_champion_t>(c)); }
inline std::uint32_t handle_of(const bc::camp& c) { return static_cast<std::uint32_t>(static_cast<bc::handle_camp_t>(c)); }

// One engine call returning a champion's live record; false when hidden.
inline bool read_champion(std::uint32_t handle, bc::detail::champion_info& out)
{
	return bc::detail::sdk_champion(handle, &out) == 0 && out.x >= 0 && out.y >= 0;
}

inline bool flag(std::int32_t state, bc::champion_state f) { return (static_cast<std::uint32_t>(state) & f.bits()) == f.bits(); }

// A cached distance field; BIG marks unreachable tiles.
struct Field
{
	bc::distance_field f;
	bool ready = false;
	int get(vec2 p) const
	{
		const auto d = f.get(p);
		return d == UNREACH ? BIG : d;
	}
};

// Ranged/melee and kit facts derived from the engine design, never hard-coded.
struct Kit
{
	int reset = -1, dash = -1, dmg = -1, cc = -1, aoe = -1, heal = -1, shield = -1;
	float dmg_range = 0, dmg_mod = 0, cc_range = 0, cc_mod = 0, aoe_range = 0, aoe_mod = 0, aoe_radius = 1, heal_range = 0, heal_mod = 0;
	float dash_range = 0, shield_mod = 0;
	float dash_mod = 0, dash_radius = 0; // patch 3.0: Heart of Ruin's dash lands for focus x dash_mod and stuns within dash_radius
	bool dmg_excl = false, cc_excl = false, aoe_excl = false, aoe_stuns = false, enhanced_reset = false;
	bool ranged = false;
	int attack_range = 1;
};

inline Kit kit_of(const bc::champion& c)
{
	Kit k;
	const auto s = c.base_stats();
	k.attack_range = s.base_attack_range;
	k.ranged = s.base_attack_range > 1;
	for (const auto& a : c.abilities())
	{
		const auto& inf = a.info();
		if (!inf)
			continue;
		const int slot = static_cast<int>(a.slot());
		std::visit(
			[&](const auto& v) {
				using T = std::decay_t<decltype(v)>;
				if constexpr (std::is_same_v<T, bc::ability_attack_reset>)
				{
					k.reset = slot;
					k.enhanced_reset = v.enhanced_attack;
				}
				else if constexpr (std::is_same_v<T, bc::ability_dash>)
				{
					k.dash = slot;
					k.dash_range = v.range;
					k.dash_mod = v.modifier;
					k.dash_radius = v.radius;
				}
				else if constexpr (std::is_same_v<T, bc::ability_damage>)
				{
					k.dmg = slot;
					k.dmg_range = v.range;
					k.dmg_mod = v.modifier;
					k.dmg_excl = v.exclusive_with_movement;
				}
				else if constexpr (std::is_same_v<T, bc::ability_cc>)
				{
					k.cc = slot;
					k.cc_range = v.range;
					k.cc_mod = v.modifier;
					k.cc_excl = v.exclusive_with_movement;
				}
				else if constexpr (std::is_same_v<T, bc::ability_aoe_damage>)
				{
					k.aoe = slot;
					k.aoe_range = v.range;
					k.aoe_mod = v.modifier;
					k.aoe_radius = v.radius;
					k.aoe_excl = v.exclusive_with_movement;
					k.aoe_stuns = v.duration > 0;
				}
				else if constexpr (std::is_same_v<T, bc::ability_heal>)
				{
					k.heal = slot;
					k.heal_range = v.range;
					k.heal_mod = v.modifier;
				}
				else if constexpr (std::is_same_v<T, bc::ability_shield>)
				{
					k.shield = slot;
					k.shield_mod = v.modifier;
				}
			},
			*inf);
	}
	return k;
}
