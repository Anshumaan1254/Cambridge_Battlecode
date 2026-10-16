#include "nav.h"

Nav& nav()
{
	static Nav n;
	return n;
}

namespace
{
constexpr std::array<vec2, 8> DIRS{ vec2::north, vec2::north_east, vec2::east, vec2::south_east,
									vec2::south, vec2::south_west, vec2::west, vec2::north_west };

bool can_build(int built)
{
	// A 100x100 field costs ~13-19k fuel; keep room for the rest of the turn.
	return built < 3 && bc::fuel_remaining() > 45000;
}
} // namespace

void Nav::init()
{
	auto& w = world();
	group_fields.assign(w.groups.size(), Field{});
	altar_fields.assign(w.altars.size(), Field{});
}

bool Nav::ensure_group(int id)
{
	auto& fld = group_fields[static_cast<std::size_t>(id)];
	if (fld.ready)
		return true;
	if (!can_build(built_this_turn))
		return false;
	auto& w = world();
	bc::bitboard visited;
	fld.f.compute(w.walls, w.groups[static_cast<std::size_t>(id)].mask, visited);
	fld.ready = true;
	++built_this_turn;
	return true;
}

bool Nav::ensure_altar(int id)
{
	auto& fld = altar_fields[static_cast<std::size_t>(id)];
	if (fld.ready)
		return true;
	if (!can_build(built_this_turn))
		return false;
	auto& w = world();
	bc::bitboard roots, visited;
	for (auto t : w.altar_approach[static_cast<std::size_t>(id)])
		roots.set(t);
	fld.f.compute(w.walls, roots, visited);
	fld.ready = true;
	++built_this_turn;
	return true;
}

int Nav::group_dist(const Group& g, vec2 from, bool allow_estimate)
{
	const auto& fld = group_fields[static_cast<std::size_t>(g.id)];
	if (fld.ready)
		return fld.get(from);
	if (!allow_estimate)
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
	b.set(me, false);
	return b;
}

namespace
{
// Dash to the reachable tile within 2 that minimises `value`; walls cannot be crossed, holes can.
template <class Value> bool try_dash(vec2& pos, int here, const Value& value, const bc::bitboard& blocked, const bc::bitboard* avoid, int dash_slot)
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
			if (avoid && avoid->is_set(p))
				continue;
			if (std::abs(dx) == 2 || std::abs(dy) == 2)
			{
				const vec2 mid{ pos.x + dx / 2, pos.y + dy / 2 };
				if (bc::map::walls().is_set(mid))
					continue;
			}
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
	const bc::bitboard blocked = blocked_now(pos);
	bool moved = here - stop_at >= 2 && try_dash(pos, here, [&](vec2 p) { return field.get(p); }, blocked, avoid, dash_slot);
	if (moved)
	{
		here = field.get(pos);
		if (here <= stop_at)
			return true;
	}
	if (!can_move)
		return moved;
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
		const int key = v * 4 + (avoid && avoid->is_set(p) ? 3 : 0);
		cand[static_cast<std::size_t>(n++)] = { key, d };
	}
	std::sort(cand.begin(), cand.begin() + n, [](const auto& a, const auto& b) { return a.first < b.first; });
	for (int i = 0; i < n; ++i)
	{
		try
		{
			if (me.move(cand[static_cast<std::size_t>(i)].second))
			{
				pos = pos + cand[static_cast<std::size_t>(i)].second;
				return true;
			}
		}
		catch (...)
		{
		}
	}
	// Units block every improving step: route around them with a dynamic search.
	if (!fallback_goals.is_empty() && bc::fuel_remaining() > 30000)
		return step_to(pos, fallback_goals, avoid, -1, true) || moved;
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
		field.compute_to(walls2, g, dest, visited);
		ok = field.get(pos) != UNREACH;
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
