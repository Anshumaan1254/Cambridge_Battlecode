// teamplan/nav_sdk.h: a local detour on host distance fields (TEAMPLAN.md 6; Om Nom 2025: push a waypoint ahead, path back from it).
// Walls + unit tiles (allies, enemies, living camps) as obstacles, a field limited to `radius` around us, the waypoint = the reachable
// tile of that window with the lowest global (cached) distance to the target, then the first step toward it on a second small field.
// Fuel is printed by tools/teamplan/test_teamplan.py (TP NAV line).
#pragma once
#include <cambc.h>

namespace teamplan
{
// Returns the next tile toward the target of `global` around unit obstacles, or `from` when no tile of the window improves on it.
inline cambc::vec2 local_detour(const cambc::bitboard& walls, const cambc::vec2* units, int n_units, cambc::vec2 from, const cambc::distance_field& global,
								int radius)
{
	constexpr std::uint16_t U = cambc::distance_field::unreachable;
	const int W = cambc::map::width(), H = cambc::map::height();
	cambc::bitboard w = walls, roots, visited;
	for (int i = 0; i < n_units; ++i)
		if (!(units[i].x == from.x && units[i].y == from.y))
			w.set(units[i]);
	roots.set(from);
	cambc::distance_field local;
	local.compute(w, roots, visited, static_cast<std::uint16_t>(radius));
	cambc::vec2 best = from;
	std::uint16_t bd = global.get(from);
	for (int dy = -radius; dy <= radius; ++dy)
		for (int dx = -radius; dx <= radius; ++dx)
		{
			const cambc::vec2 t{ from.x + dx, from.y + dy };
			if ((dx == 0 && dy == 0) || t.x < 0 || t.y < 0 || t.x >= W || t.y >= H || !visited.is_set(t))
				continue;
			const std::uint16_t g = global.get(t);
			if (g != U && g < bd)
				bd = g, best = t;
		}
	if (best.x == from.x && best.y == from.y)
		return from;
	cambc::bitboard wr, vis2;
	wr.set(best);
	cambc::distance_field back;
	back.compute(w, wr, vis2, static_cast<std::uint16_t>(2 * radius + 1));
	cambc::vec2 step = from;
	std::uint16_t sd = back.get(from);
	for (int dy = -1; dy <= 1; ++dy)
		for (int dx = -1; dx <= 1; ++dx)
		{
			const cambc::vec2 t{ from.x + dx, from.y + dy };
			if ((dx == 0 && dy == 0) || t.x < 0 || t.y < 0 || t.x >= W || t.y >= H || !vis2.is_set(t))
				continue;
			const std::uint16_t d = back.get(t);
			if (d != U && d < sd)
				sd = d, step = t;
		}
	return step;
}
} // namespace teamplan
