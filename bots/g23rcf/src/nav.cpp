#include "nav.h"
#include <cstdio>
#include "params.h"

Nav& nav()
{
	static Nav n;
	return n;
}

namespace
{
constexpr std::array<vec2, 8> DIRS{ vec2::north, vec2::north_east, vec2::east, vec2::south_east,
									vec2::south, vec2::south_west, vec2::west, vec2::north_west };

bool can_build(int built, long long fuel_floor)
{
	// A 100x100 field costs ~13-19k fuel; keep room for the rest of the turn.
	return built < 3 && bc::fuel_remaining() > fuel_floor;
}

// Detour memory (one bot instance per body): a unit blocked the field's improving steps and the dynamic search
// walked around it. The static field ignores units, so on the next tile it points straight back at the blocker.
struct Detour
{
	const Field* field = nullptr;
	int until = -1;	  // last round of the detour
	int start_v = 0;  // field value where the detour started; below it we are past the blocker
};
Detour detour;
// GOD v18 g18_osc: A-B-A breaker. The tiles this body stood on one and two turns ago when it last stepped along a field, and the
// round until which the plain descent (no danger detour, no stuck detour, no sideways exit) is used.
struct OscState
{
	int round = -10;
	vec2 p1{ -1, -1 }, p2{ -1, -1 };
	int plain_until = -1;
};
OscState g_osc;
} // namespace

void Nav::init()
{
	auto& w = world();
	group_fields.assign(w.groups.size(), Field{});
	altar_fields.assign(w.altars.size(), Field{});
}

void Nav::reset_fields()
{
	// The routing walls changed (P.stall_guard switched hole crossings off or on): every cached field is stale.
	for (auto& f : group_fields)
		f = Field{};
	for (auto& f : altar_fields)
		f = Field{};
	detour.field = nullptr;
}

bool Nav::ensure_group(int id, long long fuel_floor)
{
	auto& fld = group_fields[static_cast<std::size_t>(id)];
	if (fld.ready)
		return true;
	if (!can_build(built_this_turn, fuel_floor))
		return false;
	auto& w = world();
	bc::bitboard visited;
	fld.f.compute(w.route_walls(), w.groups[static_cast<std::size_t>(id)].mask, visited);
	fld.ready = true;
	++built_this_turn;
	return true;
}

bool Nav::ensure_altar(int id, long long fuel_floor)
{
	auto& fld = altar_fields[static_cast<std::size_t>(id)];
	if (fld.ready)
		return true;
	if (!can_build(built_this_turn, fuel_floor))
		return false;
	auto& w = world();
	bc::bitboard roots, visited;
	for (auto t : w.altar_approach[static_cast<std::size_t>(id)])
		roots.set(t);
	fld.f.compute(w.route_walls(), roots, visited);
	fld.ready = true;
	++built_this_turn;
	return true;
}

void Nav::hop_scan_step(long long fuel_floor, int turn_round)
{
	auto& w = world();
	if (hop_scan == -2)
		return;
	const int W = w.W, H = w.H;
	if (hop_scan == -1)
	{
		if (bc::fuel_remaining() < fuel_floor + 25000)
			return;
		const bc::bitboard holes = bc::map::holes();
		// A hop saves at most the walk minus the straight-line (Chebyshev) distance: skip the scan when no
		// group is far enough out of the way on foot for a hop to save hop_min_save steps.
		bool worth = false;
		for (const auto& g : w.groups)
			if (g.d_ally < BIG &&
				g.d_ally - std::max(0, cheb(g.center, w.ally_spawn_c) - 3 - g.radius) - static_cast<int>(bc::constants::tp_crystal_time) - 1 >= P.hop_min_save)
				worth = true;
		if (holes.is_empty() || !worth)
		{
			hop_scan = -2;
			return;
		}
		// Bitboard exports are packed (one bit per tile, row-major, LSB first); distance fields are one
		// uint16 per tile. Walls and holes are already UNREACH in the home field; camp spawn tiles are not
		// valid landing tiles (a crystal cannot land on a camp).
		bc::bitboard camps;
		for (const auto& g : w.groups)
			camps |= g.mask;
		home_lin = w.home.f.export_linear_buffer();
		holes_lin = holes.export_linear_buffer();
		blocked_lin = camps.export_linear_buffer();
		hop_scan = 0;
		hop_x = 0;
	}
	auto at = [W](int x, int y) { return static_cast<std::size_t>(y * W + x); };
	auto bit = [](const std::vector<std::uint8_t>& v, std::size_t i) { return ((v[i >> 3] >> (i & 7)) & 1) != 0; };
	for (; hop_scan < H; ++hop_scan, hop_x = 0)
	{
		const int y = hop_scan;
		for (; hop_x < W; ++hop_x)
		{
			// Resumable per tile: one hole-edge tile costs ~1-2k fuel, a full row far more.
			if ((hop_x & 3) == 0 && (bc::fuel_remaining() < fuel_floor || static_cast<int>(bc::round_number()) != turn_round))
				return;
			const int x = hop_x;
			const std::size_t li = at(x, y);
			if (home_lin[li] == UNREACH)
				continue;
			bool edge = false;
			for (int dy = -1; dy <= 1 && !edge; ++dy)
				for (int dx = -1; dx <= 1; ++dx)
				{
					const int nx = x + dx, ny = y + dy;
					if (nx >= 0 && ny >= 0 && nx < W && ny < H && bit(holes_lin, at(nx, ny)))
					{
						edge = true;
						break;
					}
				}
			if (!edge)
				continue;
			const int hl = home_lin[li];
			int best_save = P.hop_min_save - 1;
			vec2 bt{ -1, -1 };
			for (int ty = std::max(0, y - 3); ty <= std::min(H - 1, y + 3); ++ty)
				for (int tx = std::max(0, x - 3); tx <= std::min(W - 1, x + 3); ++tx)
				{
					const std::size_t ti = at(tx, ty);
					// Walled-off pockets are islands (handled separately): only shortcuts between walkable areas.
					if (home_lin[ti] == UNREACH || bit(blocked_lin, ti))
						continue;
					const int ht = home_lin[ti];
					const int save = ht - (hl + static_cast<int>(bc::constants::tp_crystal_time) + 1);
					if (save > best_save)
						best_save = save, bt = { tx, ty };
				}
			if (bt.x >= 0)
			{
				if (hop_edges.size() < 64)
					hop_edges.push_back({ { x, y }, bt, best_save, hl });
				else
				{
					auto worst = std::min_element(hop_edges.begin(), hop_edges.end(), [](const HopEdge& a, const HopEdge& b) { return a.save < b.save; });
					if (worst->save < best_save)
						*worst = { { x, y }, bt, best_save, hl };
				}
			}
		}
	}
	hop_scan = -2;
	home_lin.clear();
	holes_lin.clear();
	blocked_lin.clear();
}

bool Nav::ensure_hop(int id)
{
	auto& w = world();
	auto& h = w.hops[static_cast<std::size_t>(id)];
	if (h.tried)
		return h.valid;
	if (hop_scan != -2 || bc::fuel_remaining() < 40000 + 80 * static_cast<long long>(hop_edges.size()))
		return false;
	h.tried = true;
	if (hop_edges.empty())
		return false;
	const auto& g = w.groups[static_cast<std::size_t>(id)];
	if (!ensure_group(id))
	{
		h.tried = false; // retry when the budget allows
		return false;
	}
	const auto& gf = group_fields[static_cast<std::size_t>(id)];
	int best = BIG;
	for (const auto& e : hop_edges)
	{
		const int after = gf.get(e.t);
		if (after >= BIG)
			continue;
		const int c = e.home + static_cast<int>(bc::constants::tp_crystal_time) + 1 + after;
		if (c < best)
			best = c, h.launch = e.l, h.land = e.t;
	}
	h.cost = best;
	h.valid = best < BIG && best + P.hop_min_save <= g.d_ally;
#ifdef LEGEND_TRACE
	debug_block({ std::printf("HOP g=%d walk=%d cost=%d launch=(%d,%d) land=(%d,%d) valid=%d edges=%zu\n", id, g.d_ally, h.cost, h.launch.x, h.launch.y, h.land.x, h.land.y, (int)h.valid, hop_edges.size()); });
#endif
	return h.valid;
}

int Nav::group_dist(const Group& g, vec2 from, bool allow_estimate)
{
	const auto& fld = group_fields[static_cast<std::size_t>(g.id)];
	if (fld.ready)
		return fld.get(from);
	if (!allow_estimate)
		return BIG;
	// Walled-off (island) groups: unreachable on foot from anywhere our spawn reaches.
	if (P.stuck_reach && g.d_ally >= BIG && world().home_reach.is_set(from))
		return BIG;
	int best = BIG;
	for (auto t : g.tiles)
		best = std::min(best, cheb(t, from));
	return best + best / 4;
}

int Nav::altar_dist(int id, vec2 from, bool allow_estimate)
{
	const auto& fld = altar_fields[static_cast<std::size_t>(id)];
	if (fld.ready)
		return fld.get(from);
	if (!allow_estimate)
		return BIG;
	const int d = std::max(0, cheb(world().altars[static_cast<std::size_t>(id)], from) - 1);
	return d + d / 4;
}

bc::bitboard Nav::blocked_now(vec2 me)
{
	auto& w = world();
	bc::bitboard b = w.walls | w.camp_occ;
	b |= w.ally_occ;
	b |= w.enemy_occ;
	b |= w.tele_occ;
	if (P.fz_wardblock)
		b |= w.ward_occ;
	if ((P.g23_divefilter || P.g23_campzone) && g_hard_block)
		b |= *g_hard_block;
	b.set(me, false);
	return b;
}

namespace
{
// Dash to the reachable tile within 2 that minimises `value`; walls cannot be crossed, holes can.
template <class Value> bool try_dash(vec2& pos, int here, const Value& value, const bc::bitboard& blocked, const bc::bitboard* avoid, int dash_slot,
									 bool holes_only = false)
{
	if (dash_slot < 0 || here < 2)
		return false;
	auto& me = bc::self();
	const auto ab = me.abilities()[static_cast<std::size_t>(dash_slot)];
	if (ab.cooldown() > 0)
		return false;
	vec2 best = pos;
	int best_d = here;
	for (int dy = -2; dy <= 2; ++dy)
		for (int dx = -2; dx <= 2; ++dx)
		{
			const vec2 p{ pos.x + dx, pos.y + dy };
			if ((dx == 0 && dy == 0) || !bc::map::is_in_bounds(p) || blocked.is_set(p))
				continue;
			if ((avoid && avoid->is_set(p)) || (g_dash_avoid && g_dash_avoid->is_set(p)))
				continue;
			if (std::abs(dx) == 2 || std::abs(dy) == 2)
			{
				const vec2 mid{ pos.x + dx / 2, pos.y + dy / 2 };
				if (bc::map::walls().is_set(mid))
					continue;
				if (holes_only && !bc::map::holes().is_set(mid))
					continue;
			}
			else if (holes_only)
				continue;
			const int d = value(p);
			if (d < best_d)
				best_d = d, best = p;
		}
	if (best == pos || here - best_d < 2)
		return false;
	try
	{
		if (ab.use(best))
		{
			pos = best;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}
} // namespace

bool Nav::step_field(vec2& pos, const Field& field, int stop_at, const bc::bitboard* avoid, int dash_slot, bool can_move,
					 const bc::bitboard& fallback_goals)
{
	int here = field.get(pos);
	if (here <= stop_at)
		return false;
	bool plain = false;
	if (P.g18_osc)
	{
		const int r0 = static_cast<int>(bc::round_number());
		if (g_osc.round != r0)
		{
			// back on the tile of two turns ago while descending a field: a walk-in-place; descend plainly for g18_osc rounds
			if (g_osc.round == r0 - 1 && pos == g_osc.p2 && !(pos == g_osc.p1))
				g_osc.plain_until = r0 + P.g18_osc;
			g_osc.p2 = g_osc.p1, g_osc.p1 = pos, g_osc.round = r0;
		}
		plain = r0 <= g_osc.plain_until;
	}
	const bc::bitboard blocked = blocked_now(pos);
	// v23 g23_save_dash: a hole crossing within this many steps down the field: keep the dash for it (an open-ground dash put it on
	// cooldown and the body then stood at the water; islands: 418 of 635 failed farm steps, 27-36% of body turns idle)
	bool holes_only = false;
	if (P.g23_save_dash > 0 && dash_slot >= 0 && P.dash_holes)
	{
		const bc::bitboard holes = bc::map::holes();
		vec2 q = pos;
		int v = here;
		for (int k = 0; k < P.g23_save_dash && v > stop_at && !holes_only; ++k)
		{
			vec2 nb = q;
			int nv = v;
			for (auto d : DIRS)
			{
				const vec2 p = q + d;
				if (bc::map::is_in_bounds(p) && field.get(p) < nv)
					nv = field.get(p), nb = p;
			}
			if (nb == q)
				break;
			holes_only = holes.is_set(nb);
			q = nb, v = nv;
		}
	}
	bool moved = here - stop_at >= 2 && try_dash(pos, here, [&](vec2 p) { return field.get(p); }, blocked, avoid, dash_slot, holes_only);
	if (moved)
	{
		here = field.get(pos);
		if (here <= stop_at)
			return true;
	}
	if (!can_move)
		return moved;
	const int rnd = static_cast<int>(bc::round_number());
	if (P.stuck_detour && detour.field == &field && !plain)
	{
		// Still going around a blocker: keep following the dynamic search until the field value drops below
		// where the detour started (past the blocker), or the hold expires.
		if (rnd <= detour.until && here >= detour.start_v && !fallback_goals.is_empty() && bc::fuel_remaining() > 30000)
		{
			if (step_to(pos, fallback_goals, avoid, -1, true))
				return true;
		}
		if (rnd > detour.until || here < detour.start_v)
			detour.field = nullptr;
	}
	auto& me = bc::self();
	// Rank improving neighbours: prefer lower field value, then not-avoided.
	std::array<std::pair<int, vec2>, 8> cand{};
	int n = 0;
	for (auto d : DIRS)
	{
		const vec2 p = pos + d;
		if (!bc::map::is_in_bounds(p) || blocked.is_set(p))
			continue;
		const int v = field.get(p);
		if (v >= here)
			continue;
		const int key = plain ? v * 4 : v * 4 + (avoid && avoid->is_set(p) ? 2 : 0) + (g_soft_avoid && g_soft_avoid->is_set(p) ? 1 : 0);
		cand[static_cast<std::size_t>(n++)] = { key, d };
	}
	// flee_exit: we stand inside the avoided area (enemy reach, an awake camp) and every improving step stays in it: a sideways
	// step (same field value) that leaves it comes first (ladder fragment: our Ren fled home past an awake elk for 8 rounds, 740 -> 0).
	if (!plain && g_exit_first && avoid && avoid->is_set(pos) && (n == 0 || (cand[0].first & 2) == 2))
		for (auto d : DIRS)
		{
			const vec2 p = pos + d;
			if (!bc::map::is_in_bounds(p) || blocked.is_set(p) || avoid->is_set(p))
				continue;
			const int v = field.get(p);
			if (v <= here && v < BIG && n < 8)
				cand[static_cast<std::size_t>(n++)] = { -1, d };
		}
	std::sort(cand.begin(), cand.begin() + n, [](const auto& a, const auto& b) { return a.first < b.first; });
	// Every improving step enters danger (enemy reach, awake camps, a posted alert) while we stand outside it:
	// the static field only breaks ties on danger, so bodies walked into enemies just to shorten the route
	// (ladder audit P1). Try the avoiding dynamic search first; it falls back to the plain route when no safe
	// path exists, so this never deadlocks.
	if (!plain && P.danger_detour && avoid && n > 0 && (cand[0].first & 2) == 2 && !avoid->is_set(pos) && !fallback_goals.is_empty() &&
		bc::fuel_remaining() > static_cast<std::uint64_t>(P.danger_detour_fuel))
	{
		if (step_to(pos, fallback_goals, avoid, -1, true))
			return true;
	}
	for (int i = 0; i < n; ++i)
	{
		try
		{
			if (me.move(cand[static_cast<std::size_t>(i)].second))
			{
				pos = pos + cand[static_cast<std::size_t>(i)].second;
				return true;
			}
#ifdef PROBE18T
			std::printf("  MOVEFAIL r=%d (%d,%d)+(%d,%d) false\n", static_cast<int>(bc::round_number()), pos.x, pos.y, cand[static_cast<std::size_t>(i)].second.x, cand[static_cast<std::size_t>(i)].second.y);
#endif
		}
#ifdef PROBE18T
		catch (const std::exception& ex)
		{
			std::printf("  MOVEFAIL r=%d (%d,%d)+(%d,%d) ex=%s\n", static_cast<int>(bc::round_number()), pos.x, pos.y, cand[static_cast<std::size_t>(i)].second.x, cand[static_cast<std::size_t>(i)].second.y, ex.what());
		}
#endif
		catch (...)
		{
		}
	}
	// A dash route (P.dash_holes) whose next tile is a 1-wide hole: wait a few rounds for the dash rather than
	// walking around (the next turn's field would pull the body back: an oscillation).
	if (P.dash_holes && dash_slot >= 0 && !moved)
	{
		const bc::bitboard holes = bc::map::holes();
		for (auto d : DIRS)
		{
			const vec2 p = pos + d;
			if (bc::map::is_in_bounds(p) && holes.is_set(p) && field.get(p) < here)
			{
				int c = 99;
				try
				{
					c = static_cast<int>(me.abilities()[static_cast<std::size_t>(dash_slot)].cooldown());
				}
				catch (...)
				{
				}
				// dash_gain1: the crossing's far side is only one field step closer (two crossing holes chained: the field's path goes
				// hole -> hole, which no dash can follow): a ready dash that gains one step still beats waiting here for ever (nx61x71).
				if (P.dash_gain1 && c <= 0)
				{
					vec2 best = pos;
					int best_d = here;
					for (int dy = -2; dy <= 2; ++dy)
						for (int dx = -2; dx <= 2; ++dx)
						{
							const vec2 q{ pos.x + dx, pos.y + dy };
							if ((dx == 0 && dy == 0) || !bc::map::is_in_bounds(q) || blocked.is_set(q) || (avoid && avoid->is_set(q)))
								continue;
							if ((std::abs(dx) == 2 || std::abs(dy) == 2) && bc::map::walls().is_set(vec2{ pos.x + dx / 2, pos.y + dy / 2 }))
								continue;
							const int v = field.get(q);
							if (v < best_d)
								best_d = v, best = q;
						}
					if (!(best == pos))
					{
						try
						{
							if (me.abilities()[static_cast<std::size_t>(dash_slot)].use(best))
							{
								pos = best;
								return true;
							}
						}
						catch (...)
						{
						}
					}
				}
				// v14 fz_dash 1: a ready dash that found no landing above cannot cross here: waiting for it waited for ever.
				if (c <= P.dash_wait_max && !((P.fz_dash & 1) && c <= 0))
					return false;
				break;
			}
		}
	}
	// Units block every improving step: route around them with a dynamic search. pocket_fix: not from a tile the field cannot reach,
	// nor from a pocket no walk leaves (the improving step is a hole crossing for the dash): the walking search would expand the map
	// for nothing every turn.
	if (!fallback_goals.is_empty() && bc::fuel_remaining() > 30000 && !(P.pocket_fix && (here >= BIG || world().dist_home(pos) >= BIG)))
	{
		const int start_v = here;
		if (step_to(pos, fallback_goals, avoid, -1, true))
		{
			if (P.stuck_detour && (detour.field != &field || rnd > detour.until))
				detour = { &field, rnd + P.detour_hold, start_v };
			return true;
		}
		return moved;
	}
	return moved;
}

bool Nav::step_to(vec2& pos, const bc::bitboard& goals, const bc::bitboard* avoid, int dash_slot, bool can_move)
{
	auto& me = bc::self();
	if (goals.is_set(pos))
		return false;
	const bc::bitboard blocked = blocked_now(pos);
	const bc::bitboard g = goals & ~blocked;
	if (g.is_empty())
		return false;
	bc::bitboard dest;
	dest.set(pos);
	bc::bitboard visited;
	bc::distance_field field;
	bool ok = false;
	if (avoid)
	{
		bc::bitboard walls2 = blocked | (*avoid & ~g);
		walls2.set(pos, false);
		// Every neighbour in danger (or blocked): the avoiding search cannot reach us and would expand the whole
		// map for nothing (~30k fuel on 98x99); go straight to the plain search.
		bool open = !P.stuck_avoid_skip;
		for (auto d : DIRS)
		{
			if (open)
				break;
			const vec2 p = pos + d;
			open = bc::map::is_in_bounds(p) && !walls2.is_set(p);
		}
		if (open)
		{
			field.compute_to(walls2, g, dest, visited);
			ok = field.get(pos) != UNREACH;
		}
	}
	if (!ok)
	{
		if (avoid && bc::fuel_remaining() < 25000)
			return false;
		field.compute_to(blocked, g, dest, visited);
	}
	const auto here16 = field.get(pos);
	if (here16 == UNREACH)
		return false;
	const int here = here16;
	bool moved = try_dash(pos, here, [&](vec2 p) { const auto v = field.get(p); return v == UNREACH ? BIG : static_cast<int>(v); }, blocked,
						  nullptr, dash_slot);
	if (g.is_set(pos) || !can_move)
		return moved;
	for (auto d : field.next_moves_from(pos))
	{
		try
		{
			if (me.move(d))
			{
				pos = pos + d;
				return true;
			}
		}
		catch (...)
		{
		}
	}
	return moved;
}
