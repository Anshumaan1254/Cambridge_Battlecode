// mapintel/force_roster.h: forced draft rosters for tools/mapintel/run_battery.sh (the roster battery plays both teams' rosters
// forced). A bot under test supports it with one call at the top of its draft turn:
//     if (const int p = mapintel::forced_pick(); p >= 0) { cambc::draft::pick(static_cast<cambc::champion_draft>(p)); return; }
// Without the generated mi_roster.h beside this header (normal builds) forced_pick() returns -1 at once and costs nothing.
// The battery writes mi_roster.h into each variant copy: MI_ROSTER_ENTRIES = { fingerprint, n, { picks in order } }, ...
#pragma once
#include <cambc.h>
#include <cstdint>
#if __has_include("mi_roster.h")
#include "mi_roster.h"
#include "fingerprint.h"
#define MAPINTEL_FORCED_ROSTER 1
#endif

namespace mapintel
{
struct ForcedRoster
{
	std::uint64_t fp;
	int n;
	int picks[5];
};

// The next pick of the forced roster for this map, or -1 (no table, map not in the table, or roster complete).
inline int forced_pick()
{
#ifdef MAPINTEL_FORCED_ROSTER
	static const ForcedRoster table[] = { MI_ROSTER_ENTRIES };
	static std::uint64_t fp = 0;
	static bool have = false;
	if (!have)
	{
		fp = fingerprint();
		have = true;
	}
	const auto done = static_cast<int>(cambc::draft::current_draft(cambc::team::ally).size());
	for (const auto& e : table)
		if (e.fp == fp && done < e.n)
			return e.picks[done];
#endif
	return -1;
}
} // namespace mapintel
