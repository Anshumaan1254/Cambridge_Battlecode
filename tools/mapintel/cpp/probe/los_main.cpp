// Line-of-sight probe for tools/mapintel (fresh, from the cambc 3.0.5 starter's main loop). Attacks and spells need a target the caster
// sees itself (engine errors 42 / 30 in the rules probe), so the per-class "tiles that can hit a group" layers need the engine's vision.
// Hypothetical vision is refused in the draft, so over team A's first game turns one body (the first draft pick) walks the candidate
// standing tiles: every tile that is not a wall, hole or altar within Chebyshev 5 of a camp (camp tiles included: a dead camp's tile can
// be stood on). For each it calls self().visible_tiles_from(tile) (~1.1k fuel) and prints the camps within Chebyshev 5 it sees:
//   MI camps <n>                                  (camps in sorted (type, x, y) order, the fingerprint's order: index = position in it)
//   MI los <x> <y> <i> <i> ...                    (indices of the camps within Chebyshev 5 of (x, y) that are visible from it)
//   MI END
#include <cambc.h>
#include <cstdio>
#include <string>
#include "mapintel/fingerprint.h"
namespace bc = cambc;

static void line(const std::string& s)
{
	const std::string t = s + "\n";
	std::fputs(t.c_str(), stdout);
	std::fflush(stdout);
}

int main()
{
	bool started = false, finished = false;
	std::size_t k = 0;
	std::vector<bc::vec2> todo;
	std::vector<std::array<std::int32_t, 3>> camps;
	while (true)
	{
		try
		{
			if (bc::is_draft())
			{
				const auto chosen = bc::draft::current_draft(bc::team::ally);
				bc::draft::pick(static_cast<bc::champion_draft>(static_cast<int>(chosen.size())));
			}
			else if (!finished)
			{
				if (!started)
				{
					started = true;
					// both teams' first pick does it (the parser reads team A's stdout; no team test that could pick the wrong side)
					if (bc::self().champion_name() != bc::champion_type::ryth)
						finished = true;
					else
					{
						camps = mapintel::sorted_camps();
						line("MI camps " + std::to_string(camps.size()));
						bc::bitboard near_any;
						for (const auto& c : camps)
							near_any.draw_chebyshev({ c[1], c[2] }, 5.f);
						near_any &= ~(bc::map::walls() | bc::map::holes() | bc::map::altars());
						todo = near_any.positions();
					}
				}
				while (!finished && bc::fuel_remaining() > 30000)
				{
					if (k == todo.size())
					{
						line("MI END");
						finished = true;
						break;
					}
					const auto t = todo[k++];
					std::string s;
					const auto v = bc::self().visible_tiles_from(t);
					for (std::size_t i = 0; i < camps.size(); ++i)
					{
						const auto& c = camps[i];
						if (std::abs(c[1] - t.x) <= 5 && std::abs(c[2] - t.y) <= 5 && v.is_set({ c[1], c[2] }))
							s += " " + std::to_string(i);
					}
					line("MI los " + std::to_string(t.x) + " " + std::to_string(t.y) + s);
				}
			}
		}
		catch (const std::exception& e)
		{
			line(std::string("MI ERR ") + e.what());
		}
		bc::end_turn();
	}
}
