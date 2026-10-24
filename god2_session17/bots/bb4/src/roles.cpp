#include "roles.h"
#include "params.h"
#include <cmath>
#include <variant>

namespace
{
struct BodyF
{
	float hp = 0, dmg = 0, stun = 0, heal = 0, mob = 0, reset = 0, shield = 0, shop = 0;
	bool ranged = false, valid = false;
};

BodyF feats(bc::champion_type t)
{
	BodyF f;
	const auto ti = static_cast<std::size_t>(t);
	if (ti >= bc::champion_designs.size())
		return f;
	const auto& ch = bc::champion_designs[ti];
	const auto s = ch.base_stats();
	const float foc = s.base_focus;
	float spell = 0, area = 0;
	for (const auto& a : ch.abilities())
	{
		const auto& inf = a.info();
		if (!inf)
			continue;
		std::visit(
			[&](const auto& v) {
				using T = std::decay_t<decltype(v)>;
				if constexpr (std::is_same_v<T, bc::ability_attack_reset>)
				{
					f.reset = 1;
					f.stun += v.enhanced_attack ? 1.f : 0.f;
				}
				else if constexpr (std::is_same_v<T, bc::ability_damage>)
					spell += v.modifier * foc;
				else if constexpr (std::is_same_v<T, bc::ability_cc>)
					spell += v.modifier * foc, f.stun += 1.f;
				else if constexpr (std::is_same_v<T, bc::ability_aoe_damage>)
					area += v.modifier * foc, f.stun += v.duration > 0 ? 1.f : 0.f;
				else if constexpr (std::is_same_v<T, bc::ability_heal>)
					f.heal += v.modifier * foc;
				else if constexpr (std::is_same_v<T, bc::ability_shield>)
					f.shield += v.modifier * foc;
				else if constexpr (std::is_same_v<T, bc::ability_dash>)
				{
					f.mob = 1;
					if constexpr (requires { v.modifier; v.duration; })
						area += v.modifier * foc, f.stun += v.duration > 0 ? 1.f : 0.f;
				}
			},
			*inf);
	}
	f.hp = s.base_health + f.shield;
	f.dmg = s.base_strength * (f.reset > 0 ? 1.125f : 1.f) + (spell + area) / 8.f;
	f.ranged = s.base_attack_range > 1;
	try
	{
		f.shop = ch.passive() == bc::passive_type::remote_shop ? 1.f : 0.f;
	}
	catch (...)
	{
	}
	f.valid = true;
	return f;
}

std::array<RoleInfo, 16> g_roles{};
bool g_roles_ready = false;

void build_roles()
{
	std::array<BodyF, 16> fs{};
	int n = 0;
	float m_hp = 0, m_dmg = 0, m_stun = 0, m_heal = 0;
	for (std::size_t i = 0; i < bc::champion_designs.size() && i < fs.size(); ++i)
	{
		fs[i] = feats(static_cast<bc::champion_type>(i));
		if (!fs[i].valid)
			continue;
		++n;
		m_hp += fs[i].hp, m_dmg += fs[i].dmg, m_stun += fs[i].stun, m_heal += fs[i].heal;
	}
	if (n == 0)
		return;
	m_hp /= n, m_dmg /= n, m_stun /= n, m_heal /= n;
	float s_hp = 0, s_dmg = 0, s_stun = 0, s_heal = 0;
	for (const auto& f : fs)
		if (f.valid)
			s_hp += (f.hp - m_hp) * (f.hp - m_hp), s_dmg += (f.dmg - m_dmg) * (f.dmg - m_dmg), s_stun += (f.stun - m_stun) * (f.stun - m_stun),
				s_heal += (f.heal - m_heal) * (f.heal - m_heal);
	auto sd = [&](float v) { return std::max(1e-3f, std::sqrt(v / n)); };
	s_hp = sd(s_hp), s_dmg = sd(s_dmg), s_stun = sd(s_stun), s_heal = sd(s_heal);
	for (std::size_t i = 0; i < fs.size(); ++i)
	{
		const auto& f = fs[i];
		if (!f.valid)
			continue;
		const float zh = (f.hp - m_hp) / s_hp, zd = (f.dmg - m_dmg) / s_dmg, zs = (f.stun - m_stun) / s_stun, zl = (f.heal - m_heal) / s_heal;
		RoleInfo r;
		r.ranged = f.ranged;
		const float melee = f.ranged ? 0.f : 1.f;
		r.score[R_FRONT] = melee > 0 ? zh + 0.5f * zs + (f.shield > 0 ? 0.3f : 0.f) : -9.f;
		r.score[R_ASSASSIN] = melee > 0 ? zd + 0.7f * f.mob + 0.3f * f.reset : -9.f;
		r.score[R_RANGED] = f.ranged ? zd + 0.3f * zs : -9.f;
		r.score[R_SUPPORT] = 1.5f * zl + (f.ranged ? 0.5f * zs : 0.f) + 0.6f * f.shop - 0.5f;
		int best = 0;
		for (int k = 1; k < R_COUNT; ++k)
			if (r.score[static_cast<std::size_t>(k)] > r.score[static_cast<std::size_t>(best)])
				best = k;
		r.primary = static_cast<Role>(best);
		g_roles[i] = r;
	}
	g_roles_ready = true;
}

Terrain g_terrain;
bool g_terrain_ready = false;
} // namespace

const RoleInfo& role_of(bc::champion_type t)
{
	if (!g_roles_ready)
		build_roles();
	static const RoleInfo none{};
	const auto i = static_cast<std::size_t>(t);
	return i < g_roles.size() ? g_roles[i] : none;
}

const char* role_name(Role r)
{
	switch (r)
	{
	case R_FRONT: return "front";
	case R_ASSASSIN: return "assassin";
	case R_RANGED: return "ranged";
	case R_SUPPORT: return "support";
	default: return "?";
	}
}

const Terrain& terrain()
{
	if (g_terrain_ready)
		return g_terrain;
	g_terrain_ready = true;
	try
	{
		const float area = static_cast<float>(bc::map::width() * bc::map::height());
		g_terrain.wall = static_cast<float>(bc::map::walls().count()) / area;
		g_terrain.bush = static_cast<float>(bc::map::bushes().count()) / area;
		g_terrain.hole = static_cast<float>(bc::map::holes().count()) / area;
		g_terrain.compact = g_terrain.wall + g_terrain.bush - g_terrain.hole;
		g_terrain.cls = g_terrain.compact >= P.bb_compact ? MC_COMPACT : g_terrain.compact <= P.bb_open ? MC_OPEN : MC_BALANCED;
	}
	catch (...)
	{
	}
	return g_terrain;
}
