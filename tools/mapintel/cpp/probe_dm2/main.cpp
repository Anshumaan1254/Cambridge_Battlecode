// Fuel probe for draft memory v2 (MAPAnalysis.md 7.2): costs of the building blocks the NAV / OWN builders could use, on draft turn 1.
// Built as the git-ignored bots/_mi_probe2 by hand; prints one line: MI PRB <name> <fuel> ...
#include <cambc.h>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
#include "mapintel/features.h"
namespace bc = cambc;

static void line(const std::string& s)
{
	const std::string t = s + "\n";
	std::fputs(t.c_str(), stdout);
	std::fflush(stdout);
}

int main()
{
	bool done = false;
	while (true)
	{
		try
		{
			if (bc::is_draft() && !done)
			{
				done = true;
				auto f0 = bc::fuel_remaining();
				const auto V = mapintel::load_view(-1);
				auto f1 = bc::fuel_remaining();
				std::string out = "MI PRB view " + std::to_string(f0 - f1);
				const int area = V.W * V.H;
				// 1: a plain scan over two exported fields (shortest-path level counts spawn to spawn)
				f0 = bc::fuel_remaining();
				int D = 1 << 30;
				for (int i = 0; i < area; ++i)
				{
					const int a = V.fc[0][i], b = V.fc[1][i];
					if (a >= 0 && b >= 0 && a + b < D)
						D = a + b;
				}
				std::vector<std::uint16_t> cnt(static_cast<std::size_t>(D + 1), 0);
				for (int i = 0; i < area; ++i)
				{
					const int a = V.fc[0][i], b = V.fc[1][i];
					if (a >= 0 && b >= 0 && a + b == D)
						++cnt[static_cast<std::size_t>(a)];
				}
				int uniq = 0;
				for (int k = 0; k <= D; ++k)
					uniq += cnt[static_cast<std::size_t>(k)] == 1 ? 1 : 0;
				f1 = bc::fuel_remaining();
				out += " scan2 " + std::to_string(f0 - f1) + " area " + std::to_string(area) + " D " + std::to_string(D) + " uniq " + std::to_string(uniq);
				// 2: bitboard ops
				f0 = bc::fuel_remaining();
				bc::bitboard a = V.blocked[0], b;
				for (int k = 0; k < 100; ++k)
				{
					a.shift_right_into(1, b);
					a |= b;
				}
				f1 = bc::fuel_remaining();
				out += " bb200 " + std::to_string(f0 - f1);
				f0 = bc::fuel_remaining();
				unsigned c = 0;
				for (int k = 0; k < 100; ++k)
					c += a.count();
				f1 = bc::fuel_remaining();
				out += " count100 " + std::to_string(f0 - f1) + " (" + std::to_string(c & 1) + ")";
				// 3: one full host field (compute) and a max-distance field
				f0 = bc::fuel_remaining();
				bc::distance_field df;
				bc::bitboard vis;
				df.compute(V.blocked[0], bc::map::spawn_region(bc::team::ally), vis);
				f1 = bc::fuel_remaining();
				out += " field " + std::to_string(f0 - f1);
				f0 = bc::fuel_remaining();
				bc::bitboard vis2;
				df.compute(V.blocked[0], bc::map::spawn_region(bc::team::ally), vis2, 10);
				f1 = bc::fuel_remaining();
				out += " field10 " + std::to_string(f0 - f1);
				// 4: trace a path from the enemy's nearest spawn tile back to ours on fc[0] (8 reads a step) with the local-cut test
				f0 = bc::fuel_remaining();
				int best = -1, bd = 1 << 30;
				for (const int t : V.spawn_tiles[1])
				{
					// the enemy spawn tiles are blocked in fc[0]: take the passable neighbour with the least fc0
					const int x = t % V.W, y = t / V.W;
					for (int dy = -1; dy <= 1; ++dy)
						for (int dx = -1; dx <= 1; ++dx)
						{
							const int nx = x + dx, ny = y + dy;
							if (!V.in(nx, ny))
								continue;
							const int v = V.fc[0][V.at(nx, ny)];
							if (v >= 0 && v < bd)
								bd = v, best = V.at(nx, ny);
						}
				}
				int steps = 0, cuts = 0, cur = best;
				while (cur >= 0 && V.fc[0][cur] > 0 && steps < 400)
				{
					const int x = cur % V.W, y = cur / V.W, d = V.fc[0][cur];
					int nxt = -1;
					int ring = 0;
					static const int RX[8] = { 0, 1, 1, 1, 0, -1, -1, -1 }, RY[8] = { -1, -1, 0, 1, 1, 1, 0, -1 };
					for (int k = 0; k < 8; ++k)
					{
						const int nx = x + RX[k], ny = y + RY[k];
						if (!V.in(nx, ny))
							continue;
						const int i = V.at(nx, ny);
						if (V.pass(0, nx, ny))
							ring |= 1 << k;
						if (nxt < 0 && V.fc[0][i] == d - 1)
							nxt = i;
					}
					// local cut: the passable ring cells split into 2+ components (orthogonal cells k even link to k+-1 and k+-2)
					int seen = 0, comps = 0;
					for (int k = 0; k < 8; ++k)
					{
						if (!(ring >> k & 1) || (seen >> k & 1))
							continue;
						++comps;
						int st[8], sp = 0;
						st[sp++] = k, seen |= 1 << k;
						while (sp > 0)
						{
							const int u = st[--sp];
							const int nb[4] = { (u + 1) & 7, (u + 7) & 7, (u + 2) & 7, (u + 6) & 7 };
							const int nn = (u & 1) ? 2 : 4;
							for (int j = 0; j < nn; ++j)
								if ((ring >> nb[j] & 1) && !(seen >> nb[j] & 1))
									seen |= 1 << nb[j], st[sp++] = nb[j];
						}
					}
					cuts += comps >= 2 ? 1 : 0;
					cur = nxt;
					++steps;
				}
				f1 = bc::fuel_remaining();
				out += " trace " + std::to_string(f0 - f1) + " steps " + std::to_string(steps) + " cuts " + std::to_string(cuts);
				// 5: 1024-byte image assembly + submit
				f0 = bc::fuel_remaining();
				std::vector<std::uint8_t> mem(1024, 0);
				for (int k = 0; k < 1024; ++k)
					mem[static_cast<std::size_t>(k)] = static_cast<std::uint8_t>(k * 7);
				unsigned s = 0;
				for (int k = 4; k < 100; ++k)
					s += mem[static_cast<std::size_t>(k)];
				mem[3] = static_cast<std::uint8_t>(s);
				bc::draft_memory = mem;
				f1 = bc::fuel_remaining();
				out += " image_write " + std::to_string(f0 - f1);
				line(out);
			}
			if (bc::is_draft())
			{
				const auto chosen = bc::draft::current_draft(bc::team::ally);
				bc::draft::pick(static_cast<bc::champion_draft>(static_cast<int>(chosen.size())));
			}
		}
		catch (const std::exception& e)
		{
			line(std::string("MI E ") + e.what());
		}
		bc::end_turn();
	}
}
