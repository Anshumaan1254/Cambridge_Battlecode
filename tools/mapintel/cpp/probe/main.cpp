// Map-dump probe for tools/mapintel (built fresh from the cambc 3.0.5 starter's main loop; nothing from bots/).
// On the first draft turn of each team it prints, one line per fact (each line in a single write: every process shares the stdout):
//   MI fp <16 hex> ts <team size> w <W> h <H> sym <0 horizontal | 1 vertical | 2 rotational180> fuel <fuel spent on the fingerprint>
//   MI spawn ally|enemy x0 y0 x1 y1 n          (bounding box, inclusive, and tile count of the spawn region, this team's view)
//   MI bb walls|holes|bushes|altars <hex>      (bitboard::export_linear_buffer(): packed row-major, least significant bit first)
//   MI G <index> gems <g> gold <g> respawn <r> n <k> | <type> <x> <y> | ...   (bc::map::camp_groups() in engine order)
//   MI END
// Then it picks the first champion not yet picked (ids 0..11) every draft round, and in the game it ends every turn at once.
//   mkdir -p bots/_mi_probe/src && cp tools/mapintel/cpp/probe/main.cpp bots/_mi_probe/src/ && cp -r tools/mapintel/cpp/mapintel bots/_mi_probe/src/
//   cambc run _mi_probe _mi_probe --map MAP --rounds 1 -o DIR ; node tools/strategy_v2/s13/stdout.mjs DIR/*.repl26a team-a.stdout | tr -d '\000'
#include <cambc.h>
#include <cstdio>
#include <string>
#include "mapintel/fingerprint.h"
namespace bc = cambc;

static std::string hex(const std::vector<std::uint8_t>& v)
{
	static const char* d = "0123456789abcdef";
	std::string s;
	s.reserve(v.size() * 2);
	for (auto b : v)
	{
		s += d[b >> 4];
		s += d[b & 15];
	}
	return s;
}

static void line(const std::string& s)
{
	const std::string t = s + "\n";
	std::fputs(t.c_str(), stdout);
	std::fflush(stdout);
}

static void dump()
{
	const auto f0 = bc::fuel_remaining();
	const auto ts = mapintel::team_size_now();
	const auto fp = mapintel::fingerprint(ts);
	const auto f1 = bc::fuel_remaining();
	char buf[160];
	std::snprintf(buf, sizeof buf, "MI fp %016llx ts %d w %d h %d sym %d fuel %llu", static_cast<unsigned long long>(fp), ts, bc::map::width(),
		bc::map::height(), static_cast<int>(bc::map::symmetry()), static_cast<unsigned long long>(f0 - f1));
	line(buf);
	for (const auto side : { bc::team::ally, bc::team::enemy })
	{
		const auto pos = bc::map::spawn_region(side).positions();
		int x0 = 1 << 20, y0 = 1 << 20, x1 = -1, y1 = -1;
		for (const auto p : pos)
		{
			x0 = std::min(x0, p.x);
			y0 = std::min(y0, p.y);
			x1 = std::max(x1, p.x);
			y1 = std::max(y1, p.y);
		}
		std::snprintf(buf, sizeof buf, "MI spawn %s %d %d %d %d %d", side == bc::team::ally ? "ally" : "enemy", x0, y0, x1, y1, static_cast<int>(pos.size()));
		line(buf);
	}
	line("MI bb walls " + hex(bc::map::walls().export_linear_buffer()));
	line("MI bb holes " + hex(bc::map::holes().export_linear_buffer()));
	line("MI bb bushes " + hex(bc::map::bushes().export_linear_buffer()));
	line("MI bb altars " + hex(bc::map::altars().export_linear_buffer()));
	int gi = 0;
	for (const auto& g : bc::map::camp_groups())
	{
		std::string s = "MI G " + std::to_string(gi++) + " gems " + std::to_string(g.gem_value()) + " gold " + std::to_string(g.gold_value()) +
			" respawn " + std::to_string(g.max_respawn_timer()) + " n " + std::to_string(g.camps().size());
		for (const auto& c : g.camps())
			s += " | " + std::to_string(static_cast<int>(c.kind())) + " " + std::to_string(c.spawn_position().x) + " " + std::to_string(c.spawn_position().y);
		line(s);
	}
	line("MI END");
}

int main()
{
	bool dumped = false;
	while (true)
	{
		try
		{
			if (bc::is_draft())
			{
				if (!dumped)
				{
					dumped = true;
					dump();
				}
				const auto chosen = bc::draft::current_draft(bc::team::ally);
				for (int i = 0; i < 12; ++i)
				{
					const auto p = static_cast<bc::champion_draft>(i);
					bool have = false;
					for (const auto c : chosen)
						have |= c == p;
					if (!have)
					{
						bc::draft::pick(p);
						break;
					}
				}
			}
		}
		catch (const std::exception& e)
		{
			line(std::string("MI ERR ") + e.what());
		}
		catch (...)
		{
			line("MI ERR unknown");
		}
		bc::end_turn();
	}
}
