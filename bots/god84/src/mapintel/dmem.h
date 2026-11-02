// mapintel/dmem.h: the draft-memory block of mapintel (MAPAnalysis.md 5.8): the draft computes the plans once and the champions read
// them in the game. Layout version 1 (the Python twin is compact.pack; test_library.py checks the bytes are equal):
//   block at DMEM_OFFSET 512 of the 1024 draft-memory bytes, DMEM_SIZE 352 bytes (offsets inside the block):
//     0 magic 0xA7, 1 version 1, 2-9 map fingerprint (little endian), 10 flags (bit 0 known map, bit 1 we can bank, bit 2 they can bank,
//     bits 3-4 tiebreak mode (0 both bank, 1 neither, 2 only them, 3 only us), bit 5 plan 1 present), 11 archetype (255 = none),
//     12 team size, 13 groups (<= 64), 14 contested band, 15 contested count, 16 bodies, 17-22 body types (255 = none),
//     23-86 bank altar per group (row-major altar index, 255 = none), 87-150 our walk to each group, 151-214 theirs (255 = not reached
//     or >= 255), 215-262 16 x (group, dU, dE), 263-278 8 thresholds (uint16 LE), 279-350 plan 1: 6 slots x 4 x (group, arrival round
//     uint16 LE; group 255 = none), 351 checksum (sum of bytes 0-350 mod 256).
// Coexistence: the bot's own draft data lives below offset 512 (GOD v10 writes 4 bytes from offset 0). The SDK's write always starts
// at offset 0 and leaves the bytes after a shorter input unchanged, and its read is a snapshot taken when the process starts: so keep one
// buffer of your own (prefix + this block), write it whole, and re-write it whole whenever you change your prefix.
//     std::vector<std::uint8_t> mem(1024, 0);              // your bytes at 0-511
//     mapintel::dmem_put(mem, mapintel::dmem_pack(P, fp, view.team, known, archetype));
//     cambc::draft_memory = mem;
// In the game (any champion, any turn): mapintel::Block B; if (mapintel::dmem_get(B)) { ... B.plan(slot, k) ... }
#pragma once
#include <cambc.h>
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>
#include "plans.h"

namespace mapintel
{
inline constexpr int DMEM_OFFSET = 512, DMEM_SIZE = 352;
inline constexpr std::uint8_t DMEM_MAGIC = 0xA7, DMEM_VERSION = 1;

inline std::array<std::uint8_t, DMEM_SIZE> dmem_pack(const Plans& P, std::uint64_t fingerprint, int team_size, bool known = false, int archetype = 255)
{
	std::array<std::uint8_t, DMEM_SIZE> b{};
	auto cl = [](int v) { return static_cast<std::uint8_t>(v < 0 || v > 254 ? 255 : v); };
	b[0] = DMEM_MAGIC, b[1] = DMEM_VERSION;
	for (int k = 0; k < 8; ++k)
		b[static_cast<std::size_t>(2 + k)] = static_cast<std::uint8_t>((fingerprint >> (8 * k)) & 0xFF);
	b[10] = static_cast<std::uint8_t>((known ? 1 : 0) | (P.us_bank ? 2 : 0) | (P.them_bank ? 4 : 0) | (P.mode << 3) | (P.nbody > 0 ? 32 : 0));
	b[11] = static_cast<std::uint8_t>(archetype & 0xFF);
	b[12] = static_cast<std::uint8_t>(std::max(0, team_size) & 0xFF);
	const int G = std::min(P.ngroups, NGRP);
	b[13] = static_cast<std::uint8_t>(G);
	b[14] = static_cast<std::uint8_t>(std::min(255, P.band));
	b[15] = static_cast<std::uint8_t>(P.ncon);
	for (int g = 0; g < NGRP; ++g)
	{
		const auto u = static_cast<std::size_t>(g);
		b[23 + u] = g < G ? static_cast<std::uint8_t>(P.bank[u]) : 255;
		b[87 + u] = g < G ? cl(P.dU[u]) : 255;
		b[151 + u] = g < G ? cl(P.dE[u]) : 255;
	}
	for (int k = 0; k < NCON; ++k)
	{
		const auto o = static_cast<std::size_t>(215 + 3 * k);
		if (k < P.ncon)
			b[o] = static_cast<std::uint8_t>(P.con[k][0]), b[o + 1] = cl(P.con[k][1]), b[o + 2] = cl(P.con[k][2]);
		else
			b[o] = b[o + 1] = b[o + 2] = 255;
	}
	for (int k = 0; k < 8; ++k)
		b[static_cast<std::size_t>(263 + 2 * k)] = static_cast<std::uint8_t>(P.thr[k] & 0xFF), b[static_cast<std::size_t>(264 + 2 * k)] = static_cast<std::uint8_t>((P.thr[k] >> 8) & 0xFF);
	b[16] = static_cast<std::uint8_t>(P.nbody);
	for (int s = 0; s < NSLOT; ++s)
	{
		b[static_cast<std::size_t>(17 + s)] = s < P.nbody ? static_cast<std::uint8_t>(P.body[s]) : 255;
		for (int k = 0; k < NTGT; ++k)
		{
			const auto o = static_cast<std::size_t>(279 + 12 * s + 3 * k);
			if (s < P.nbody && k < P.ntgt[s])
			{
				const int a = std::max(0, std::min(65535, static_cast<int>(std::floor(P.tgt[s][k].arrive + 0.5))));
				b[o] = static_cast<std::uint8_t>(P.tgt[s][k].g), b[o + 1] = static_cast<std::uint8_t>(a & 0xFF), b[o + 2] = static_cast<std::uint8_t>(a >> 8);
			}
			else
				b[o] = b[o + 1] = b[o + 2] = 255;
		}
	}
	unsigned sum = 0;
	for (int k = 0; k < DMEM_SIZE - 1; ++k)
		sum += b[static_cast<std::size_t>(k)];
	b[DMEM_SIZE - 1] = static_cast<std::uint8_t>(sum & 0xFF);
	return b;
}

// Put the block into the bot's own draft-memory buffer (grown to DMEM_OFFSET + DMEM_SIZE; the bytes below DMEM_OFFSET are kept).
inline void dmem_put(std::vector<std::uint8_t>& mem, const std::array<std::uint8_t, DMEM_SIZE>& block)
{
	if (mem.size() < static_cast<std::size_t>(DMEM_OFFSET + DMEM_SIZE))
		mem.resize(static_cast<std::size_t>(DMEM_OFFSET + DMEM_SIZE), 0);
	for (int k = 0; k < DMEM_SIZE; ++k)
		mem[static_cast<std::size_t>(DMEM_OFFSET + k)] = block[static_cast<std::size_t>(k)];
}

// The block as the game reads it.
struct Block
{
	std::array<std::uint8_t, DMEM_SIZE> b{};
	std::uint64_t fingerprint() const
	{
		std::uint64_t v = 0;
		for (int k = 7; k >= 0; --k)
			v = (v << 8) | b[static_cast<std::size_t>(2 + k)];
		return v;
	}
	bool known() const { return b[10] & 1; }
	bool us_bank() const { return b[10] & 2; }
	bool them_bank() const { return b[10] & 4; }
	int mode() const { return (b[10] >> 3) & 3; }
	bool has_plan1() const { return b[10] & 32; }
	int archetype() const { return b[11] == 255 ? -1 : b[11]; }
	int team_size() const { return b[12]; }
	int groups() const { return b[13]; }
	int band() const { return b[14]; }
	int ncon() const { return b[15]; }
	int nbody() const { return b[16]; }
	int body(int s) const { return b[static_cast<std::size_t>(17 + s)] == 255 ? -1 : b[static_cast<std::size_t>(17 + s)]; }
	int bank_altar(int g) const { return g < 0 || g >= NGRP || b[static_cast<std::size_t>(23 + g)] == 255 ? -1 : b[static_cast<std::size_t>(23 + g)]; }
	int dU(int g) const { return g < 0 || g >= NGRP || b[static_cast<std::size_t>(87 + g)] == 255 ? -1 : b[static_cast<std::size_t>(87 + g)]; }
	int dE(int g) const { return g < 0 || g >= NGRP || b[static_cast<std::size_t>(151 + g)] == 255 ? -1 : b[static_cast<std::size_t>(151 + g)]; }
	std::array<int, 3> con(int k) const
	{
		const auto o = static_cast<std::size_t>(215 + 3 * k);
		auto v = [&](std::size_t i) { return b[i] == 255 ? -1 : static_cast<int>(b[i]); };
		return { v(o), v(o + 1), v(o + 2) };
	}
	int threshold(int k) const { return b[static_cast<std::size_t>(263 + 2 * k)] | (b[static_cast<std::size_t>(264 + 2 * k)] << 8); }
	// target k (0-3) of body slot s: (group, planned arrival round), group -1 = none
	std::pair<int, int> plan(int s, int k) const
	{
		const auto o = static_cast<std::size_t>(279 + 12 * s + 3 * k);
		if (b[o] == 255)
			return { -1, 0 };
		return { b[o], b[o + 1] | (b[o + 2] << 8) };
	}
};

// Check and copy a block (DMEM_SIZE bytes from p).
inline bool dmem_parse_block(const std::uint8_t* p, Block& out)
{
	if (p[0] != DMEM_MAGIC || p[1] != DMEM_VERSION)
		return false;
	unsigned sum = 0;
	for (int k = 0; k < DMEM_SIZE - 1; ++k)
		sum += p[k];
	if ((sum & 0xFF) != p[DMEM_SIZE - 1])
		return false;
	for (int k = 0; k < DMEM_SIZE; ++k)
		out.b[static_cast<std::size_t>(k)] = p[k];
	return true;
}

// Find the block in a whole draft-memory buffer (n >= DMEM_OFFSET + DMEM_SIZE).
inline bool dmem_parse(const std::uint8_t* data, std::size_t n, Block& out)
{
	return n >= static_cast<std::size_t>(DMEM_OFFSET + DMEM_SIZE) && dmem_parse_block(data + DMEM_OFFSET, out);
}

// Read the block from the engine's draft-memory snapshot (in the game, or in a later draft turn of a new process).
inline bool dmem_get(Block& out)
{
	try
	{
		if (cambc::draft_memory.size() < static_cast<std::size_t>(DMEM_OFFSET + DMEM_SIZE))
			return false;
		std::array<std::uint8_t, DMEM_SIZE> tmp{};
		for (int k = 0; k < DMEM_SIZE; ++k)
			tmp[static_cast<std::size_t>(k)] = std::to_integer<std::uint8_t>(cambc::draft_memory[static_cast<std::size_t>(DMEM_OFFSET + k)]);
		return dmem_parse_block(tmp.data(), out);
	}
	catch (...)
	{
		return false;
	}
}
} // namespace mapintel
