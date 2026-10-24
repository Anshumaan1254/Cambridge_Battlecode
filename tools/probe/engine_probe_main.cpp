// Probe: prints the engine's game settings, every camp design and every champion design (base stats and ability payloads), then idles.
// Diff two engines' output to see what a package release changed:
//   mkdir -p bots/_eprobe/src && cp tools/probe/engine_probe_main.cpp bots/_eprobe/src/main.cpp
//   cambc run _eprobe idle --map <any map> --rounds 2 -o DIR      (team-a.stdout inside the replay bundle; tools/strategy_v2/s13/stdout.mjs)
#include <cambc.h>
#include <cstdio>
#include <type_traits>
#include <variant>
namespace bc = cambc;

static void settings()
{
	namespace k = bc::constants;
	std::printf("SET capture_time %d camp_sleep_time %d respawn_time %d recall_time %d\n", k::capture_time, k::camp_sleep_time, k::respawn_time,
				k::recall_time);
	std::printf("SET submit_mult %.4f submit_base %d submit_min %d submit_range %d\n", k::submit_gem_duration_multiplier,
				k::submit_gem_base_duration, k::submit_gem_minimum_duration, k::submit_gems_range);
	std::printf("SET max_rounds %u winning_gems %u kill_gold %u assist_gold %u passive_gold %u spawn_healing %.4f\n", k::max_rounds,
				k::winning_gems, k::kill_gold, k::assist_gold, k::passive_gold, static_cast<double>(k::spawn_healing));
	std::printf("SET active_wards %u ward_cooldown %d ward_lifetime %d ward_vision %.2f ward_place %.2f altar_lock_hits %u tp_crystal_time %d\n",
				k::active_wards, k::ward_cooldown, k::ward_lifetime, static_cast<double>(k::ward_vision_radius),
				static_cast<double>(k::ward_placement_radius), k::altar_lock_hits, k::tp_crystal_time);
	std::printf("SET shared_memory %u draft_memory %u tile_reveal %u\n", k::shared_memory_bytes, k::draft_memory_bytes, k::tile_reveal_rounds);
	namespace p = bc::constants::passive_abilities;
	std::printf("SET prism_focus_per_gem %.3f varg_splash %.2f vesper_gold %u marcella_gold %u ryth_ratio %.4f ren_ret %.3f hor_bonus %.3f\n",
				static_cast<double>(p::prism_focus_per_gem), static_cast<double>(p::varg_splash_radius), p::vesper_vale_bonus_gold_percent,
				p::marcella_tribute_gold_per_gem, static_cast<double>(p::ryth_health_strength_ratio), static_cast<double>(p::ren_retaliation_focus_ratio),
				static_cast<double>(p::heart_of_ruin_missing_health_damage_max_bonus));
}

static void camps()
{
	for (int t = 0; t < 6; ++t)
	{
		bc::detail::camp_design d{};
		if (bc::detail::sdk_camp_design(t, &d) != 0)
		{
			std::printf("CAMP %d none\n", t);
			continue;
		}
		const auto& s = d.base_stats;
		std::printf("CAMP %d %s hp %.2f +%.2f str %.2f +%.2f foc %.2f +%.2f range %d vision %.2f move %d\n", t,
					bc::to_string(static_cast<bc::camp_type>(t)).c_str(), static_cast<double>(s.base_health), static_cast<double>(s.health_growth),
					static_cast<double>(s.base_strength), static_cast<double>(s.strength_growth), static_cast<double>(s.base_focus),
					static_cast<double>(s.focus_growth), s.base_attack_range, static_cast<double>(s.vision_radius), s.base_move_speed);
	}
}

static void champions()
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
			const int sl = static_cast<int>(a.slot());
			if (!inf)
			{
				std::printf("  AB slot %d none\n", sl);
				continue;
			}
			std::visit(
				[&](const auto& v) {
					using T = std::decay_t<decltype(v)>;
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
					else
						std::printf("  AB slot %d other\n", sl);
				},
				*inf);
		}
	}
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
				{
					settings(), camps(), champions(), done = true;
					std::fflush(stdout);
				}
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
