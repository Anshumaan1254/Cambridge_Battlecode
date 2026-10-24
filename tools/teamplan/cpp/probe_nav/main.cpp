// Navigation fuel probe for tools/teamplan (TEAMPLAN.md section 6): what a host distance field costs against a local search written in
// wasm, looped and unrolled. Built fresh from the 3.0.5 starter's loop (nothing from bots/). In the game, on its 3rd turn (after the
// 200k first turn), every body prints one line per measurement (fuel spent):
//   TP nav <map W>x<H> walls_export <f> field_full <f> field_r3 <f> field_to <f> gets49 <f> units_walls <f> field_units <f>
//      bfs7_loop <f> bfs7_unrolled <f> agree <0|1>
//   python3 -I tools/teamplan/probe_nav.py [--maps GLOB]   (builds bots/_tp_navprobe, plays 4 rounds per map, prints a table)
#include <cambc.h>
#include <array>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
namespace bc = cambc;

static void line(const std::string& s)
{
	const std::string t = s + "\n";
	std::fputs(t.c_str(), stdout);
	std::fflush(stdout);
}

// packed walls (bit i = y * W + x, least significant bit first), read without host calls
struct Packed
{
	int W = 0, H = 0;
	std::vector<std::uint8_t> b;
	bool blocked(int x, int y) const
	{
		if (x < 0 || y < 0 || x >= W || y >= H)
			return true;
		const int i = y * W + x;
		return (b[static_cast<std::size_t>(i >> 3)] >> (i & 7)) & 1;
	}
};

// 7x7 window BFS around (cx, cy): dist[49] (255 = unreached), 8-neighbour moves, walls from the packed map plus the unit list.
template <bool Unroll>
static void bfs7(const Packed& P, int cx, int cy, const std::array<int, 16>& ux, const std::array<int, 16>& uy, int nu, std::uint8_t dist[49])
{
	bool blk[49];
	if constexpr (Unroll)
	{
#pragma clang loop unroll(full)
		for (int k = 0; k < 49; ++k)
			blk[k] = P.blocked(cx - 3 + k % 7, cy - 3 + k / 7);
	}
	else
	{
#pragma clang loop unroll(disable)
		for (int k = 0; k < 49; ++k)
			blk[k] = P.blocked(cx - 3 + k % 7, cy - 3 + k / 7);
	}
	for (int u = 0; u < nu; ++u)
	{
		const int dx = ux[static_cast<std::size_t>(u)] - cx + 3, dy = uy[static_cast<std::size_t>(u)] - cy + 3;
		if (dx >= 0 && dx < 7 && dy >= 0 && dy < 7)
			blk[dy * 7 + dx] = true;
	}
	std::uint8_t q[49];
	int qh = 0, qt = 0;
	for (int k = 0; k < 49; ++k)
		dist[k] = 255;
	dist[24] = 0;
	q[qt++] = 24;
	while (qh < qt)
	{
		const int c = q[qh++];
		const int x = c % 7, y = c / 7;
		if constexpr (Unroll)
		{
#pragma clang loop unroll(full)
			for (int d = 0; d < 8; ++d)
			{
				static constexpr int DX[8] = { 1, 1, 0, -1, -1, -1, 0, 1 }, DY[8] = { 0, 1, 1, 1, 0, -1, -1, -1 };
				const int nx = x + DX[d], ny = y + DY[d];
				if (nx < 0 || ny < 0 || nx > 6 || ny > 6)
					continue;
				const int n = ny * 7 + nx;
				if (blk[n] || dist[n] != 255)
					continue;
				dist[n] = static_cast<std::uint8_t>(dist[c] + 1);
				q[qt++] = static_cast<std::uint8_t>(n);
			}
		}
		else
		{
#pragma clang loop unroll(disable)
			for (int d = 0; d < 8; ++d)
			{
				static constexpr int DX[8] = { 1, 1, 0, -1, -1, -1, 0, 1 }, DY[8] = { 0, 1, 1, 1, 0, -1, -1, -1 };
				const int nx = x + DX[d], ny = y + DY[d];
				if (nx < 0 || ny < 0 || nx > 6 || ny > 6)
					continue;
				const int n = ny * 7 + nx;
				if (blk[n] || dist[n] != 255)
					continue;
				dist[n] = static_cast<std::uint8_t>(dist[c] + 1);
				q[qt++] = static_cast<std::uint8_t>(n);
			}
		}
	}
}

static void measure()
{
	const auto me = bc::self().position();
	const int W = bc::map::width(), H = bc::map::height();
	auto f = [] { return static_cast<long long>(bc::fuel_remaining()); };
	long long t0 = f();
	const bc::bitboard walls = bc::map::walls() | bc::map::holes();
	Packed P;
	P.W = W, P.H = H;
	P.b.resize(static_cast<std::size_t>((W * H + 7) / 8));
	walls.export_linear_buffer(std::span<std::uint8_t>(P.b.data(), P.b.size()));
	long long t1 = f();
	bc::bitboard roots, visited;
	roots.set(me);
	bc::distance_field full;
	full.compute(walls, roots, visited);
	long long t2 = f();
	bc::distance_field r3;
	r3.compute(walls, roots, visited, 3);
	long long t3 = f();
	bc::bitboard dest;
	const auto es = bc::map::spawn_region(bc::team::enemy).positions();
	if (!es.empty())
		dest.set(es.front());
	bc::distance_field to;
	to.compute_to(walls, roots, dest, visited);
	long long t4 = f();
	unsigned sum = 0;
	for (int dy = -3; dy <= 3; ++dy)
		for (int dx = -3; dx <= 3; ++dx)
		{
			const bc::vec2 p{ me.x + dx, me.y + dy };
			if (p.x >= 0 && p.y >= 0 && p.x < W && p.y < H)
				sum += full.get(p);
		}
	long long t5 = f();
	// ten unit tiles around us (allies / enemies / living camps stand-ins) added to the walls with host set() calls
	std::array<int, 16> ux{}, uy{};
	int nu = 0;
	bc::bitboard uw = walls;
	for (int k = 0; k < 10; ++k)
	{
		const bc::vec2 p{ me.x + (k % 5) - 2, me.y + (k / 5) * 2 - 1 };
		if (p.x < 0 || p.y < 0 || p.x >= W || p.y >= H || (p.x == me.x && p.y == me.y))
			continue;
		uw.set(p);
		ux[static_cast<std::size_t>(nu)] = p.x, uy[static_cast<std::size_t>(nu)] = p.y, ++nu;
	}
	long long t6 = f();
	bc::distance_field fu;
	fu.compute(uw, roots, visited);
	long long t7 = f();
	std::uint8_t d1[49], d2[49];
	bfs7<false>(P, me.x, me.y, ux, uy, nu, d1);
	long long t8 = f();
	bfs7<true>(P, me.x, me.y, ux, uy, nu, d2);
	long long t9 = f();
	int agree = 1;
	for (int k = 0; k < 49; ++k)
		agree &= d1[k] == d2[k];
	char buf[320];
	std::snprintf(buf, sizeof buf,
		"TP nav %dx%d walls_export %lld field_full %lld field_r3 %lld field_to %lld gets49 %lld units_walls %lld field_units %lld bfs7_loop %lld "
		"bfs7_unrolled %lld agree %d sum %u",
		W, H, t0 - t1, t1 - t2, t2 - t3, t3 - t4, t4 - t5, t5 - t6, t6 - t7, t7 - t8, t8 - t9, agree, sum);
	line(buf);
}

int main()
{
	int game_turn = 0;
	while (true)
	{
		try
		{
			if (bc::is_draft())
			{
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
			else
			{
				++game_turn;
				if (game_turn == 3)
					measure();
			}
		}
		catch (const std::exception& e)
		{
			line(std::string("TP ERR ") + e.what());
		}
		catch (...)
		{
			line("TP ERR unknown");
		}
		bc::end_turn();
	}
}
