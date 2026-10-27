// mapintel/fingerprint.h: the exact-match key of a map (MAPAnalysis.md 5.8).
// FNV-1a 64 over, in this order:
//   width, height, team size (3 x int32 little endian);
//   the wall, hole, bush and altar bitboards as the SDK exports them (packed row-major, least significant bit first,
//   bitboard::linear_buffer_size() bytes each);
//   the runtime camps (every camp of every group, both halves) as int32 (type, x, y) triples, sorted lexicographically.
// Nothing team-relative goes in, so both teams compute the same value. The table in known_maps.h is produced by this same function
// run inside the engine (tools/mapintel/cpp/probe), never by a re-implementation. Cost: fingerprint() = 4 exports + hashing ~4 x W*H/8
// bytes + one camp_groups() call (camp_groups() builds every camp object: ~80-140k fuel on the large official maps); features.h's
// fingerprint(const MapView&) gives the same value from the view's own exports (hashing only, ~5-11k): use that one in a bot.
#pragma once
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <vector>

namespace mapintel
{
struct Fnv64
{
	std::uint64_t h = 0xcbf29ce484222325ull;
	void byte(std::uint8_t b)
	{
		h ^= b;
		h *= 0x100000001b3ull;
	}
	void i32(std::int32_t v)
	{
		const auto u = static_cast<std::uint32_t>(v);
		byte(static_cast<std::uint8_t>(u));
		byte(static_cast<std::uint8_t>(u >> 8));
		byte(static_cast<std::uint8_t>(u >> 16));
		byte(static_cast<std::uint8_t>(u >> 24));
	}
	void bytes(const std::vector<std::uint8_t>& v)
	{
		for (const auto b : v)
			byte(b);
	}
};

// Team size: the draft's number of rounds (works in the draft; outside it the SDK may refuse, so the caller can pass it in).
inline std::int32_t team_size_now()
{
	try
	{
		return static_cast<std::int32_t>(cambc::draft::team_size());
	}
	catch (...)
	{
		return -1;
	}
}

// The runtime camps as sorted (type, x, y) triples.
inline std::vector<std::array<std::int32_t, 3>> sorted_camps()
{
	std::vector<std::array<std::int32_t, 3>> camps;
	for (const auto& g : cambc::map::camp_groups())
		for (const auto& c : g.camps())
			camps.push_back({ static_cast<std::int32_t>(c.kind()), c.spawn_position().x, c.spawn_position().y });
	std::sort(camps.begin(), camps.end());
	return camps;
}

// team_size < 0: read it from the draft (team_size_now()).
inline std::uint64_t fingerprint(std::int32_t team_size = -1)
{
	if (team_size < 0)
		team_size = team_size_now();
	Fnv64 f;
	f.i32(cambc::map::width());
	f.i32(cambc::map::height());
	f.i32(team_size);
	f.bytes(cambc::map::walls().export_linear_buffer());
	f.bytes(cambc::map::holes().export_linear_buffer());
	f.bytes(cambc::map::bushes().export_linear_buffer());
	f.bytes(cambc::map::altars().export_linear_buffer());
	for (const auto& c : sorted_camps())
	{
		f.i32(c[0]);
		f.i32(c[1]);
		f.i32(c[2]);
	}
	return f.h;
}
} // namespace mapintel
