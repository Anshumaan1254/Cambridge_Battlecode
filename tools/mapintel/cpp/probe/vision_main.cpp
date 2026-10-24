// Vision probe for tools/mapintel (fresh, from the cambc 3.0.5 starter's main loop): over team A's first game turns (hypothetical vision
// is refused in the draft: "Initialize the game before inspecting runtime state"), one body prints the engine's hypothetical vision
// (self().visible_tiles_from(p): symmetric shadowcasting, walls and bushes occlude, radius 8) from a
// deterministic sample of non-wall tiles, so the Python shadowcasting of tools/mapintel/geometry.py can be checked tile for tile.
//   MI visfuel <fuel of one call>
//   MI vis <x> <y> <hex of export_linear_buffer()>      (one line per sampled tile; sample: (7x + 13y) % STRIDE == 0, about 60 a map)
//   MI END
#include <cambc.h>
#include <cstdio>
#include <string>
namespace bc = cambc;

static void line(const std::string& s)
{
	const std::string t = s + "\n";
	std::fputs(t.c_str(), stdout);
	std::fflush(stdout);
}

int main()
{
	bool mine = false, started = false, finished = false;
	int x = 0, y = 0;
	static const char* hx = "0123456789abcdef";
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
					mine = bc::self().champion_name() == bc::champion_type::ryth;  // draft pick 0 = Ryth, on both teams: one body does it all
					if (!mine)
						finished = true;
				}
				const int W = bc::map::width(), H = bc::map::height();
				const int stride = std::max(7, W * H / 60);
				const auto& walls = bc::map::walls();
				bool first = x == 0 && y == 0;
				while (!finished && bc::fuel_remaining() > 40000)
				{
					if ((7 * x + 13 * y) % stride == 0 && !walls.is_set({ x, y }))
					{
						const auto f0 = bc::fuel_remaining();
						const auto v = bc::self().visible_tiles_from({ x, y }).export_linear_buffer();
						if (first)
						{
							line("MI visfuel " + std::to_string(f0 - bc::fuel_remaining()));
							first = false;
						}
						std::string s = "MI vis " + std::to_string(x) + " " + std::to_string(y) + " ";
						for (auto b : v)
						{
							s += hx[b >> 4];
							s += hx[b & 15];
						}
						line(s);
					}
					if (++x == W)
					{
						x = 0;
						if (++y == H)
						{
							line("MI END");
							finished = true;
						}
					}
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
