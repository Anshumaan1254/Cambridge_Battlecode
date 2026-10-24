// Distance-field probe for tools/mapintel: checks that the SDK's host BFS (distance_field::compute) is the king-move BFS the Python side
// uses (geometry.bfs). On the first draft turn of team A: the field from team A's spawn region with walls = walls | holes | altars |
// team B's spawn (camps passable), exported row-major as uint16 (65535 = unreachable): its FNV-1a 64 over the little-endian bytes (the
// full hex costs more than the 1M fuel of the draft turn on 100x100 maps), the reached tile count, the largest distance, and the fuel
// of compute() alone.
//   MI field <fuel> <fnv hex> <reached> <max>
#include <cambc.h>
#include <cstdio>
#include <algorithm>
#include <cstdint>
#include <string>
namespace bc = cambc;

int main()
{
	bool done = false;
	while (true)
	{
		try
		{
			if (bc::is_draft())
			{
				if (!done && bc::map::spawn_region(bc::team::ally).is_set(bc::map::spawn_region(bc::team::ally).positions().front()))
				{
					done = true;
					const auto f0 = bc::fuel_remaining();
					const auto walls = bc::map::walls() | bc::map::holes() | bc::map::altars() | bc::map::spawn_region(bc::team::enemy);
					bc::distance_field f;
					bc::bitboard visited;
					f.compute(walls, bc::map::spawn_region(bc::team::ally), visited);
					const auto f1 = bc::fuel_remaining();
					const auto v = f.export_linear_buffer();
					std::uint64_t h = 0xcbf29ce484222325ull;
					int reached = 0, mx = 0;
					for (auto x : v)
					{
						for (int k = 0; k < 2; ++k)
						{
							h ^= (x >> (8 * k)) & 255;
							h *= 0x100000001b3ull;
						}
						if (x != 65535)
						{
							++reached;
							mx = std::max(mx, static_cast<int>(x));
						}
					}
					std::printf("MI field %llu %016llx %d %d\n", static_cast<unsigned long long>(f0 - f1), static_cast<unsigned long long>(h), reached, mx);
					std::fflush(stdout);
				}
				const auto chosen = bc::draft::current_draft(bc::team::ally);
				bc::draft::pick(static_cast<bc::champion_draft>(static_cast<int>(chosen.size())));
			}
		}
		catch (const std::exception& e)
		{
			std::printf("MI ERR %s\n", e.what());
			std::fflush(stdout);
		}
		bc::end_turn();
	}
}
