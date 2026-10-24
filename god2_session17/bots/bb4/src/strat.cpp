#include "strat.h"
#include "common.h"
#include "params.h"
#include <cstdio>

std::uint32_t strat_hash(std::uint32_t w, std::uint32_t h, std::uint32_t camps, std::uint32_t side, std::uint32_t enemy_mask)
{
	// FNV-1a over five words, then a finaliser (the same arithmetic in tools/live/variant_of.py)
	std::uint32_t x = 2166136261u;
	const std::uint32_t words[5] = { w, h, camps, side, enemy_mask };
	for (std::uint32_t v : words)
	{
		x ^= v;
		x *= 16777619u;
	}
	x ^= x >> 15;
	x *= 0x2c1b3c6du;
	x ^= x >> 12;
	x *= 0x297a2d39u;
	x ^= x >> 15;
	return x;
}

// Variant v -> strategy bits: (v << P.ab_shift) | P.ab_base. Bit 0 middle control, bit 1 boldness, bit 2 attackers first,
// bit 3 chase discipline, bit 4 Durability-first build, bit 5 gold routing, bit 6 oscillation fix, bit 7 convoy,
// bit 8 grouped stance always, bit 9 team danger alerts (alert_radius 6), bit 10 strike first (A6 bits 1+2),
// bit 11 enemies on their spawn are no threat to camps.
void strat_apply(int v)
{
	SV = Strat{};
	SV.variant = v;
	const long long vb = ((v & 1) ? P.ab_b0 : 0LL) | ((v & 2) ? P.ab_b1 : 0LL) | ((v & 4) ? P.ab_b2 : 0LL) | ((v & 8) ? P.ab_b3 : 0LL) |
		((v & 16) ? P.ab_b4 : 0LL);
	const long long bits = (vb << P.ab_shift) | P.ab_base;
	SV.bits = bits;
	if (bits & 1)
	{
		SV.mc_value = 0.6f;
		SV.mc_threat = 1.0f;
		SV.half_grade = 0.3f;
	}
	if (bits & 2)
	{
		SV.threat_adv = 1.1f;
		SV.ml2_leave = 0.3f;
		SV.ml2_flee = 0.3f;
		SV.half_penalty = 6.f;
	}
	if (bits & 4)
		SV.atk_first = true;
	if (bits & 8)
		SV.chase_max = 4;
	if (bits & 16)
		SV.build_style = 17;
	if (bits & 32)
		SV.route_gold_d = 4;
	if (bits & 64)
		SV.osc_fix = true;
	if (bits & 128)
		SV.convoy = true;
	if (bits & 256)
		SV.force_grouped = true;
	if (bits & 512)
		SV.alert_radius = 6;
	if (bits & 1024)
		SV.strike_first = 3;
	if (bits & 2048)
		SV.spawn_threat_off = true;
	if (bits & 4096)
		SV.squad = 2; // with bit 7 (convoy): pairs
	if (bits & 8192)
		SV.squad = 3; // with bit 7 (convoy): trios
	if (bits & 16384)
		SV.bb_draft = 1;
	if (bits & 32768)
		SV.bb_off = 1;
	if (bits & 65536)
		SV.open = true;
	if (bits & 131072)
		SV.mid_risk = 20.f;
	if (bits & 262144)
		SV.farm_thru = true;
	if (bits & 524288)
		SV.stand = true;
	if (bits & 1048576)
		SV.farm_hold = true;
	if (bits & 2097152)
		SV.stepin_shot = true;
	if (bits & 4194304)
		SV.no_stepin = true;
	if (bits & 8388608)
		SV.convert = true;
	if (bits & 16777216)
		SV.smart_flee = true;
	if (bits & 33554432)
		SV.melee_combo = true;
	if (bits & 67108864)
		SV.early_shield = true;
	if (bits & 134217728)
		SV.safe_rally = true;
	if (bits & 268435456)
		SV.mid_hold = true;
	if (bits & 536870912)
		SV.bank_more = true;
	if (bits & 1073741824)
		SV.kite = true;
	if (bits & (1LL << 31))
		SV.contest = true;
	if (bits & (1LL << 32))
		SV.real_channel = true;
	if (bits & (1LL << 33))
		SV.no_chase = true;
}

int strat_pick()
{
	if (P.ab_variants <= 0)
		return P.ab_force;
	std::uint32_t camps = 0, emask = 0, side = 0;
	try
	{
		for (const auto& g : bc::map::camp_groups())
			camps += static_cast<std::uint32_t>(g.camps().size());
		side = bc::detail::sdk_my_team() == 0 ? 0u : 1u;
		for (const auto& c : bc::champions(team::enemy))
		{
			const int t = static_cast<int>(c.champion_name()); // champion_type: cassi 3, issac 4, the rest shift by one after issac
			if (t == 4)
				continue;
			const int d = t <= 3 ? t : t - 1; // champion_draft id
			if (d >= 0 && d < 32)
				emask |= 1u << d;
		}
	}
	catch (...)
	{
	}
	if (P.ab_nomask)
		emask = 0; // the variant must be the same in the draft (enemy picks unknown) and in the game
	const std::uint32_t x = strat_hash(static_cast<std::uint32_t>(bc::map::width()), static_cast<std::uint32_t>(bc::map::height()), camps, side, emask);
	const int v = static_cast<int>(x % static_cast<std::uint32_t>(P.ab_variants));
#ifdef LEGEND_TRACE
	debug_block({ std::printf("AB v=%d w=%d h=%d camps=%u side=%u emask=%u hash=%u\n", v, bc::map::width(), bc::map::height(), camps, side, emask, x); });
#endif
	return v;
}
