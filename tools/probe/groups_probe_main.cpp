// Probe: prints the runtime camp groups as a bot sees them (bc::map::camp_groups(): gold, gems, respawn, members with type and
// spawn tile), the spawn regions and the altars, on the first game turn of team A's first body. A map file stores one copy of each
// mirrored camp; this shows how the engine pairs the copies into groups at runtime (the ground truth for tools/mapintel).
//   mkdir -p bots/_gprobe/src && cp tools/probe/groups_probe_main.cpp bots/_gprobe/src/main.cpp
//   cambc run _gprobe idle --map MAP --rounds 2 -o DIR      (team-a.stdout in the bundle: tools/strategy_v2/s13/stdout.mjs)
#include <cambc.h>
#include <cstdio>
#include <string>
namespace bc = cambc;

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
			else if (!done)
			{
				done = true;
				// Every body is its own process writing to the same team stdout: each line goes out in one write so lines never
				// interleave (the parser keeps one copy of each).
				const auto groups = bc::map::camp_groups();
				std::string all = "GROUPS " + std::to_string(groups.size()) + "\n";
				int gi = 0;
				for (const auto& g : groups)
				{
					std::string line = "G " + std::to_string(gi++) + " gems " + std::to_string(g.gem_value()) + " gold " + std::to_string(g.gold_value()) +
						" respawn " + std::to_string(g.max_respawn_timer()) + " n " + std::to_string(g.camps().size());
					for (const auto& c : g.camps())
					{
						const auto p = c.spawn_position();
						line += " | " + bc::to_string(c.kind()) + " " + std::to_string(p.x) + "," + std::to_string(p.y);
					}
					all += line + "\n";
				}
				std::fputs(all.c_str(), stdout);
				std::fflush(stdout);
			}
		}
		catch (...)
		{
		}
		bc::end_turn();
	}
}
