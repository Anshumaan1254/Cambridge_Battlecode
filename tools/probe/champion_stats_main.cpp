// Probe: prints every champion design's base stats and ability payloads as the engine reports them, then idles.
#include <cambc.h>
#include <cstdio>
#include <type_traits>
#include <variant>
namespace bc = cambc;

static void dump()
{
	for (std::size_t i = 0; i < bc::champion_designs.size(); ++i)
	{
		const auto& c = bc::champion_designs[i];
		const auto s = c.base_stats();
		std::printf("CH %zu hp %.2f +%.2f str %.2f +%.2f foc %.2f +%.2f range %d vision %d move %d campmul %.3f\n", i, s.base_health,
					s.health_growth, s.base_strength, s.strength_growth, s.base_focus, s.focus_growth, s.base_attack_range, s.vision_radius,
					s.base_move_speed, s.camp_damage_multiplier);
		for (const auto& a : c.abilities())
		{
			const auto& inf = a.info();
			if (!inf)
			{
				std::printf("  AB slot %d none\n", static_cast<int>(a.slot()));
				continue;
			}
			std::visit(
				[&](const auto& v) {
					using T = std::decay_t<decltype(v)>;
					const int sl = static_cast<int>(a.slot());
					if constexpr (std::is_same_v<T, bc::ability_attack_reset>)
						std::printf("  AB slot %d reset enhanced %d cd %d excl %d\n", sl, v.enhanced_attack, v.max_cooldown, v.exclusive_with_movement);
					else if constexpr (std::is_same_v<T, bc::ability_damage>)
						std::printf("  AB slot %d damage range %.2f mod %.3f cd %d excl %d\n", sl, v.range, v.modifier, v.max_cooldown, v.exclusive_with_movement);
					else if constexpr (std::is_same_v<T, bc::ability_aoe_damage>)
						std::printf("  AB slot %d aoe range %.2f mod %.3f radius %.2f dur %d cd %d excl %d\n", sl, v.range, v.modifier, v.radius, v.duration,
									v.max_cooldown, v.exclusive_with_movement);
					else if constexpr (std::is_same_v<T, bc::ability_cc>)
						std::printf("  AB slot %d cc range %.2f mod %.3f dur %d cd %d excl %d\n", sl, v.range, v.modifier, v.duration, v.max_cooldown,
									v.exclusive_with_movement);
					else if constexpr (std::is_same_v<T, bc::ability_heal>)
						std::printf("  AB slot %d heal range %.2f mod %.3f cd %d\n", sl, v.range, v.modifier, v.max_cooldown);
					else if constexpr (std::is_same_v<T, bc::ability_dash>)
						std::printf("  AB slot %d dash range %.2f radius %.2f mod %.3f dur %d cd %d\n", sl, v.range, v.radius, v.modifier, v.duration,
									v.max_cooldown);
					else if constexpr (std::is_same_v<T, bc::ability_shield>)
						std::printf("  AB slot %d shield range %.2f mod %.3f dur %d cd %d\n", sl, v.range, v.modifier, v.duration, v.max_cooldown);
				},
				*inf);
		}
	}
	std::printf("PRISM_FOCUS_PER_GEM %.3f\n", static_cast<double>(bc::constants::passive_abilities::prism_focus_per_gem));
	std::fflush(stdout);
}

int main()
{
	bool done = false;
	int n = 0;
	while (true)
	{
		try
		{
			if (bc::is_draft())
			{
				if (!done)
					dump(), done = true;
				const auto chosen = bc::draft::current_draft(bc::team::ally);
				for (int i = 0; i < 12; ++i)
				{
					const auto p = static_cast<bc::champion_draft>((i + n) % 12);
					bool have = false;
					for (const auto c : chosen)
						have |= c == p;
					if (!have)
					{
						bc::draft::pick(p);
						break;
					}
				}
				++n;
			}
		}
		catch (...)
		{
		}
		bc::end_turn();
	}
}
