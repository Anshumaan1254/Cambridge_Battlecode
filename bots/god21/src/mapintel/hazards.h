// mapintel/hazards.h: the static navigation hazards of the NAV draft-memory block (docs/DRAFT_MEMORY.md 5.7) for a map the table does
// not know. COMPUTED (the map and our spawn). Python twin: tools/mapintel/hazards.py (bit-equal; tools/mapintel/test_dmem2.py).
// Known maps carry the same block in known_maps.h (`KnownMap::nav`), computed offline by the twin.
//
// Why so few loops: in this engine a wasm loop step costs ~50 fuel, so a scan of every tile of a 100x100 map is ~500k (measured,
// MAPAnalysis.md 7.2); a bitboard operation of the SDK costs ~36 and a host distance field 5-31k. So the hazards are bitboard formulas
// over the whole map, and loops run only over short lists (traced paths, candidate positions).
//
// Definitions (tiles as y * W + x; "passable" = not a wall, hole, altar or the enemy's spawn, as plans.h's fc[0]):
//   cut tile        a passable tile whose passable 8-neighbours split into two or more king-connected parts: a one-tile-wide crossing.
//                   The ring's parts: the passable orthogonal neighbours in runs around N, E, S, W (two consecutive ones touch
//                   diagonally), plus every passable diagonal neighbour whose two orthogonal neighbours are blocked.
//   traced path     from a destination tile towards our spawn: each step to the first neighbour, in the order N, NE, E, SE, S, SW, W,
//                   NW, whose walk from our spawn (fc[0]) is one less; it ends on our spawn (walk 0).
//                   Path 0: spawn to spawn, from the tile next to the enemy's spawn with the least walk (ties: the lower tile index).
//                   Paths 1-3: to the first three anchor groups, from their camp tile nearest our spawn (Compact::near_tile).
//   chokepoints     (bytes 0-15, up to 8) the cut tiles on the traced paths, path 0 first, each path from its destination; one per run
//                   of consecutive cut tiles on a path (the first), no duplicates.
//   pocket entries  (bytes 16-23, up to 4) passable tiles that walking from our spawn does not reach but a dash (range 2) does: within
//                   Chebyshev 2 of a reached tile. Entries within Chebyshev 3 of a camp in such a pocket first, then the rest, each in
//                   tile order; an entry is kept when it is at least 5 (Chebyshev) from every kept one.
//   hole tiles      (bytes 24-39, up to 8) holes with passable tiles on both sides in a line (horizontal, vertical or diagonal): a dash
//                   crosses them. Saving = |walk to one side - walk to the other| (255 when only one side is reached; no saving when
//                   neither is), the best of the four lines; kept when the saving is at least 3, the largest first (ties: tile order).
//                   Candidates: the first NAV_HOLE_CAND holes of that kind in tile order (the SDK lists set bits in its chunk order:
//                   detail::nav_tiles_in_order reads them in tile order).
//   field anchors   (bytes 40-55, up to 8) the tiles worth a cached field: our spawn tile where path 0 ends (else our lowest spawn tile),
//                   the first three altars of the bank order (dmem2.h bank_order), the near tiles of the first four anchor groups.
//   counts          bytes 56-59: chokepoints, pocket entries, hole tiles, anchors; byte 60: the parts computed (bit 0 path 0, bits 1-3
//                   paths 1-3, bit 4 pockets, bit 5 hole tiles; a computed block is written only when complete: 63);
//                   byte 61: the source (1 computed in this draft, 2 copied from known_maps.h); 62-63 zero.
// uint16 fields are little-endian; 0xFFFF = none. Anchor groups: model_weights.h first_scores() ranking when the bot has it, else the
// reached groups nearest our spawn (dmem2.h nav_anchor_groups).
#pragma once
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <memory>
#include <span>
#include <vector>
#include "plans.h"

namespace mapintel
{
inline constexpr int NAV_SIZE = 64, NAV_CHOKE = 8, NAV_POCKET = 4, NAV_HOLE = 8, NAV_ANCHOR = 8, NAV_GROUP_PATHS = 3;
inline constexpr int NAV_HOLE_CAND = 128, NAV_POCKET_CAND = 256, NAV_HOLE_MIN_SAVING = 3, NAV_POCKET_SPACING = 5;
inline constexpr std::uint8_t NAV_PART_POCKET = 16, NAV_PART_HOLE = 32, NAV_ALL_PARTS = 63, NAV_SRC_DRAFT = 1, NAV_SRC_TABLE = 2;
// estimated fuel per unit of work, for the floor checks (measured on the 40 official maps by test_dmem2.py; generous on purpose)
inline constexpr long long NAV_FUEL_STEP = 300, NAV_FUEL_HOLE = 400, NAV_FUEL_POCKET = 6000, NAV_FUEL_BASE = 8000;
inline constexpr int NAV_DX[8] = { 0, 1, 1, 1, 0, -1, -1, -1 }, NAV_DY[8] = { -1, -1, 0, 1, 1, 1, 0, -1 }; // N NE E SE S SW W NW

namespace detail
{
// out (x, y) = b (x + dx, y + dy), outside the map = 0 (SDK: shift_right(+1) moves a bit to x + 1, shift_up(+1) to y + 1)
inline void nav_neighbour(const cambc::bitboard& b, int dx, int dy, cambc::bitboard& out, cambc::bitboard& tmp)
{
	if (dx != 0 && dy != 0)
	{
		b.shift_right_into(-dx, tmp);
		tmp.shift_up_into(-dy, out);
	}
	else if (dx != 0)
		b.shift_right_into(-dx, out);
	else
		b.shift_up_into(-dy, out);
}

// Chebyshev-r dilation in place (r king steps: the x and y passes are separable)
inline void nav_dilate(cambc::bitboard& b, int r, cambc::bitboard& t1, cambc::bitboard& t2)
{
	for (int k = 0; k < r; ++k)
	{
		b.shift_right_into(1, t1);
		b.shift_right_into(-1, t2);
		b |= t1;
		b |= t2;
		b.shift_up_into(1, t1);
		b.shift_up_into(-1, t2);
		b |= t1;
		b |= t2;
	}
}

// a = a & ~b, in place (the SDK's operator~ allocates)
inline void nav_andnot(cambc::bitboard& a, const cambc::bitboard& b, cambc::bitboard& tmp)
{
	tmp = a;
	tmp &= b;
	a ^= tmp;
}

// the set tiles of b in tile order (y * W + x ascending), at most cap: the linear export read 64 bits at a time (the SDK's positions_into
// returns the engine's chunk order, not tile order; this costs ~50 fuel a word, ~8k on a 100 x 100 map)
inline int nav_tiles_in_order(const cambc::bitboard& b, int area, std::vector<std::uint64_t>& buf, int* out, int cap)
{
	const std::size_t nbytes = (static_cast<std::size_t>(area) + 7) / 8, nw = (nbytes + 7) / 8;
	buf.assign(nw, 0);
	b.export_linear_buffer(std::span<std::uint8_t>(reinterpret_cast<std::uint8_t*>(buf.data()), nbytes));
	int n = 0;
	for (std::size_t w = 0; w < nw && n < cap; ++w)
		for (std::uint64_t x = buf[w]; x != 0 && n < cap; x &= x - 1)
			out[n++] = static_cast<int>(64 * w) + __builtin_ctzll(x);
	return n;
}

inline bool nav_bit(const std::vector<std::uint8_t>& v, int i) { return (v[static_cast<std::size_t>(i) >> 3] >> (i & 7)) & 1; }

inline void nav_put16(std::uint8_t* b, int k, int v)
{
	b[2 * k] = static_cast<std::uint8_t>(v & 0xFF), b[2 * k + 1] = static_cast<std::uint8_t>((v >> 8) & 0xFF);
}
} // namespace detail

// The cut tiles of the passable set P (definitions above), as a bitboard.
inline cambc::bitboard nav_cut_tiles(const cambc::bitboard& P)
{
	cambc::bitboard n[8], tmp, term, one, two;
	for (int k = 0; k < 8; ++k)
		detail::nav_neighbour(P, NAV_DX[k], NAV_DY[k], n[k], tmp);
	auto add = [&](const cambc::bitboard& t) {
		tmp = one;
		tmp &= t;
		two |= tmp;
		one |= t;
	};
	// run starts: an orthogonal neighbour whose predecessor in N -> E -> S -> W -> N is blocked (N = 0, E = 2, S = 4, W = 6)
	for (int k = 0; k < 8; k += 2)
	{
		term = n[k];
		detail::nav_andnot(term, n[(k + 6) & 7], tmp);
		add(term);
	}
	// isolated diagonals (NE = 1, SE = 3, SW = 5, NW = 7): both orthogonal neighbours blocked
	for (int k = 1; k < 8; k += 2)
	{
		cambc::bitboard both = n[k - 1];
		both |= n[(k + 1) & 7];
		term = n[k];
		detail::nav_andnot(term, both, tmp);
		add(term);
	}
	two &= P;
	return two;
}

struct NavInput
{
	int anchor_groups[4] = { -1, -1, -1, -1 };	// groups for paths 1-3 and anchors 4-7 (-1 = none)
	int altars[3] = { -1, -1, -1 };				// altar indices (row-major) of the bank order
	long long floor = 0;						// nav_resume stops when the fuel left falls to this (0 = run to the end)
};

// The NAV computation as resumable work: nav_resume() runs it in the definitions' order and stops at the fuel floor; the next call
// (a later draft turn: keep the NavWork in RAM) continues where it stopped, so the block equals one uninterrupted run whatever the
// floors. Stages: 0 init (the cut tiles, exported), 1 path 0, 2-4 paths 1-3, 5 pockets, 6 hole candidates, 7 hole savings, 8 done.
struct NavWork
{
	int stage = 0;
	std::vector<std::uint8_t> cutb, pb;
	// the trace in progress
	bool tracing = false, prev = false;
	int cur = -1, x = 0, y = 0, steps = 0, end = -1;
	int nchoke = 0, spawn_end = -1;
	std::uint16_t choke[NAV_CHOKE]{};
	int npocket = 0;
	std::uint16_t pocket[NAV_POCKET]{};
	std::vector<int> holes;
	std::uint32_t hi = 0;
	int nhole = 0, ht[NAV_HOLE]{}, hs[NAV_HOLE]{};
	bool done() const { return stage >= 8; }
};

// Continues the work; returns true when the block is complete. C = our Compact (side 0).
inline bool nav_resume(NavWork& w, const MapView& m, const Compact& C, const NavInput& in)
{
	namespace bc = cambc;
	const int W = m.W, H = m.H, area = W * H;
	const std::uint16_t* f = m.fc[0].v.get();
	auto ok = [&](long long need) { return in.floor <= 0 || static_cast<long long>(bc::fuel_remaining()) > need + in.floor; };
	if (w.stage == 0)
	{
		if (!ok(NAV_FUEL_BASE))
			return false;
		bc::bitboard P = ~m.blocked[0];
		const bc::bitboard cut = nav_cut_tiles(P);
		w.cutb.assign((static_cast<std::size_t>(area) + 7) / 8, 0);
		w.pb.assign(w.cutb.size(), 0);
		cut.export_linear_buffer(std::span<std::uint8_t>(w.cutb.data(), w.cutb.size()));
		P.export_linear_buffer(std::span<std::uint8_t>(w.pb.data(), w.pb.size()));
		w.stage = 1;
	}
	// one trace (a path), resumable step by step; returns true when the path is finished
	auto trace = [&]() {
		while (w.steps <= area)
		{
			if ((w.steps & 7) == 0 && !ok(8 * NAV_FUEL_STEP))
				return false;
			++w.steps;
			const int d = f[w.cur];
			if (d == 65535)
				return true;
			const bool c = detail::nav_bit(w.cutb, w.cur);
			if (c && !w.prev && w.nchoke < NAV_CHOKE)
			{
				bool dup = false;
				for (int i = 0; i < w.nchoke; ++i)
					dup |= w.choke[i] == w.cur;
				if (!dup)
					w.choke[w.nchoke++] = static_cast<std::uint16_t>(w.cur);
			}
			w.prev = c;
			if (d == 0)
			{
				w.end = w.cur;
				return true;
			}
			int nxt = -1;
			for (int k = 0; k < 8; ++k)
			{
				const int nx = w.x + NAV_DX[k], ny = w.y + NAV_DY[k];
				if (nx < 0 || ny < 0 || nx >= W || ny >= H)
					continue;
				const int i = ny * W + nx;
				if (f[i] == d - 1)
				{
					nxt = i, w.x = nx, w.y = ny;
					break;
				}
			}
			if (nxt < 0)
				return true;
			w.cur = nxt;
		}
		return true;
	};
	auto start_trace = [&](int t) { w.tracing = true, w.prev = false, w.cur = t, w.x = t % W, w.y = t / W, w.steps = 0, w.end = -1; };
	// path 0: from the tile next to the enemy's spawn with the least walk
	if (w.stage == 1)
	{
		if (!w.tracing)
		{
			int start = -1, bd = 1 << 30;
			for (const int t : m.spawn_tiles[1])
			{
				const int x = t % W, y = t / W;
				for (int k = 0; k < 8; ++k)
				{
					const int nx = x + NAV_DX[k], ny = y + NAV_DY[k];
					if (nx < 0 || ny < 0 || nx >= W || ny >= H)
						continue;
					const int i = ny * W + nx, v = f[i];
					if (v != 65535 && (v < bd || (v == bd && i < start)))
						bd = v, start = i;
				}
			}
			if (start < 0)
				w.stage = 2; // nothing to trace (no walk to the enemy)
			else
				start_trace(start);
		}
		if (w.stage == 1)
		{
			if (!trace())
				return false;
			w.spawn_end = w.end, w.tracing = false, w.stage = 2;
		}
	}
	// paths 1-3: to the first three anchor groups
	while (w.stage >= 2 && w.stage <= 4)
	{
		const int p = w.stage - 2;
		if (!w.tracing)
		{
			const int g = in.anchor_groups[p];
			const int t = g >= 0 ? C.near_tile(g) : -1;
			if (t < 0 || f[t] == 65535)
			{
				++w.stage;
				continue;
			}
			start_trace(t);
		}
		if (!trace())
			return false;
		w.tracing = false, ++w.stage;
	}
	// pockets: passable, not reached by walking, within dash range 2 of a reached tile
	if (w.stage == 5)
	{
		if (!ok(NAV_FUEL_POCKET))
			return false;
		bc::bitboard t1, t2, tmp;
		bc::bitboard pocket = ~m.blocked[0];
		detail::nav_andnot(pocket, m.reach0, tmp);
		bc::bitboard entry = m.reach0;
		detail::nav_dilate(entry, 2, t1, t2);
		entry &= pocket;
		bc::bitboard near = m.camps_bb;
		near &= pocket;
		detail::nav_dilate(near, 3, t1, t2);
		bc::bitboard e1 = entry;
		e1 &= near;
		bc::bitboard e2 = entry;
		detail::nav_andnot(e2, near, tmp);
		std::vector<std::uint64_t> buf;
		std::vector<int> pos(NAV_POCKET_CAND);
		int kept[NAV_POCKET][2];
		for (const bc::bitboard* e : { &e1, &e2 })
		{
			if (w.npocket >= NAV_POCKET)
				break;
			const int cnt = detail::nav_tiles_in_order(*e, area, buf, pos.data(), NAV_POCKET_CAND);
			for (int i = 0; i < cnt && w.npocket < NAV_POCKET; ++i)
			{
				const int x = pos[static_cast<std::size_t>(i)] % W, y = pos[static_cast<std::size_t>(i)] / W;
				bool keep = true;
				for (int k = 0; k < w.npocket && keep; ++k)
					keep = std::max(std::abs(x - kept[k][0]), std::abs(y - kept[k][1])) >= NAV_POCKET_SPACING;
				if (!keep)
					continue;
				kept[w.npocket][0] = x, kept[w.npocket][1] = y;
				w.pocket[w.npocket++] = static_cast<std::uint16_t>(y * W + x);
			}
		}
		w.stage = 6;
	}
	// dash-crossable hole tiles: the candidates (bitboards), then their savings, resumable per candidate
	static const int OX[4] = { 1, 0, 1, 1 }, OY[4] = { 0, 1, 1, -1 };
	if (w.stage == 6)
	{
		if (!ok(NAV_FUEL_POCKET))
			return false;
		bc::bitboard P = ~m.blocked[0];
		const bc::bitboard holes = bc::map::holes();
		bc::bitboard any, line, nb1, nb2, tmp;
		for (int o = 0; o < 4; ++o)
		{
			detail::nav_neighbour(P, OX[o], OY[o], nb1, tmp);
			detail::nav_neighbour(P, -OX[o], -OY[o], nb2, tmp);
			line = holes;
			line &= nb1;
			line &= nb2;
			any |= line;
		}
		std::vector<std::uint64_t> buf;
		w.holes.resize(NAV_HOLE_CAND);
		w.holes.resize(static_cast<std::size_t>(detail::nav_tiles_in_order(any, area, buf, w.holes.data(), NAV_HOLE_CAND)));
		w.hi = 0, w.stage = 7;
	}
	if (w.stage == 7)
	{
		for (; w.hi < w.holes.size(); ++w.hi)
		{
			if ((w.hi & 7) == 0 && !ok(8 * NAV_FUEL_HOLE))
				return false;
			const int x = w.holes[w.hi] % W, y = w.holes[w.hi] / W;
			int best = -1;
			for (int o = 0; o < 4; ++o)
			{
				const int ax = x + OX[o], ay = y + OY[o], bx = x - OX[o], by = y - OY[o];
				if (ax < 0 || ay < 0 || ax >= W || ay >= H || bx < 0 || by < 0 || bx >= W || by >= H)
					continue;
				const int ia = ay * W + ax, ib = by * W + bx;
				if (!detail::nav_bit(w.pb, ia) || !detail::nav_bit(w.pb, ib))
					continue;
				const int fa = f[ia], fb = f[ib];
				int sv;
				if (fa != 65535 && fb != 65535)
					sv = fa > fb ? fa - fb : fb - fa;
				else if (fa != 65535 || fb != 65535)
					sv = 255;
				else
					continue;
				best = std::max(best, std::min(sv, 255));
			}
			if (best < NAV_HOLE_MIN_SAVING)
				continue;
			const int t = y * W + x;
			// insert into the top list (saving descending, tile ascending)
			int j = w.nhole < NAV_HOLE ? w.nhole++ : NAV_HOLE;
			if (j == NAV_HOLE)
			{
				if (!(best > w.hs[NAV_HOLE - 1]))
					continue;
				j = NAV_HOLE - 1;
			}
			while (j > 0 && w.hs[j - 1] < best)
				w.ht[j] = w.ht[j - 1], w.hs[j] = w.hs[j - 1], --j;
			w.ht[j] = t, w.hs[j] = best;
		}
		w.stage = 8;
		w.cutb.clear(), w.cutb.shrink_to_fit(), w.pb.clear(), w.pb.shrink_to_fit(), w.holes.clear(), w.holes.shrink_to_fit();
	}
	return w.done();
}

// The block of a finished NavWork (bytes 0-61; byte 60 = all parts, 61 = computed in this draft).
inline std::array<std::uint8_t, NAV_SIZE> nav_block(const NavWork& w, const MapView& m, const Compact& C, const NavInput& in)
{
	std::array<std::uint8_t, NAV_SIZE> b{};
	for (int k = 0; k < 28; ++k)
		detail::nav_put16(b.data(), k, 0xFFFF);
	const int W = m.W;
	for (int i = 0; i < w.nchoke; ++i)
		detail::nav_put16(b.data(), i, w.choke[i]);
	for (int i = 0; i < w.npocket; ++i)
		detail::nav_put16(b.data(), 8 + i, w.pocket[i]);
	for (int i = 0; i < w.nhole; ++i)
		detail::nav_put16(b.data(), 12 + i, w.ht[i]);
	int nanchor = 0, sp = w.spawn_end;
	if (sp < 0)
		for (const int t : m.spawn_tiles[0])
			if (sp < 0 || t < sp)
				sp = t;
	if (sp >= 0)
		detail::nav_put16(b.data(), 20 + nanchor++, sp);
	for (int k = 0; k < 3; ++k)
		if (in.altars[k] >= 0 && in.altars[k] < static_cast<int>(m.altar_tiles.size()))
		{
			const auto a = m.altar_tiles[static_cast<std::size_t>(in.altars[k])];
			detail::nav_put16(b.data(), 20 + nanchor++, a.y * W + a.x);
		}
	for (int k = 0; k < 4 && nanchor < NAV_ANCHOR; ++k)
	{
		const int t = in.anchor_groups[k] >= 0 ? C.near_tile(in.anchor_groups[k]) : -1;
		if (t >= 0)
			detail::nav_put16(b.data(), 20 + nanchor++, t);
	}
	b[56] = static_cast<std::uint8_t>(w.nchoke), b[57] = static_cast<std::uint8_t>(w.npocket), b[58] = static_cast<std::uint8_t>(w.nhole);
	b[59] = static_cast<std::uint8_t>(nanchor), b[60] = NAV_ALL_PARTS, b[61] = NAV_SRC_DRAFT;
	return b;
}

// One uninterrupted run (in.floor ignored): the block.
inline std::array<std::uint8_t, NAV_SIZE> nav_compute(const MapView& m, const Compact& C, NavInput in)
{
	in.floor = 0;
	NavWork w;
	nav_resume(w, m, C, in);
	return nav_block(w, m, C, in);
}
} // namespace mapintel
