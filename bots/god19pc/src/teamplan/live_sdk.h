// teamplan/live_sdk.h: the live protocol of live.h on the SDK's 8 shared bytes (one read and one write per turn, both host calls).
// Use: live_init(L) on the first turn (at spawn, where every ally is in sight); then every turn, at its start,
//   live_observe(L, live_read(), round);  ... decide ... ;  live_write(live_compose(L, claim, status, flag, cursor, tiebreak));
// The engine test (tools/teamplan/test_teamplan.py, TP L lines) checks the chain of reads and writes, the twin and the stale detection.
#pragma once
#include <cambc.h>

#include <cstdint>
#include <span>

#include "live.h"

namespace teamplan
{
inline std::uint64_t live_read()
{
	std::uint8_t b[8] = {};
	cambc::shared_memory.read(0, std::span<std::uint8_t>{ b });
	return load64(b);
}

inline void live_write(std::uint64_t v)
{
	std::uint8_t b[8];
	store64(v, b);
	cambc::shared_memory.write(0, std::span<const std::uint8_t>{ b });
}

// Our slot from the allies' body types (every body computes the same order; the draft memory's TEAM block uses it too).
inline void live_init(LiveState& L)
{
	int types[16];
	int n = 0;
	for (const auto& c : cambc::champions(cambc::team::ally))
		try
		{
			if (n < 16)
				types[n++] = static_cast<int>(c.champion_name());
		}
		catch (...)
		{
		}
	L.n = n < 6 ? n : 6;
	L.slot = live_slot_of(types, n, static_cast<int>(cambc::self().champion_name()));
}
} // namespace teamplan
