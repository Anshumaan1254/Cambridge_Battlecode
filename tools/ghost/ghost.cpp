// Test-only ghost opponent: see ghost.h. Never in a submission.
#include "ghost.h"
#include "ghost_data.h"
#include <algorithm>
#include <cstdlib>
#include <optional>
#include <cambc.h>

namespace bc = cambc;
using bc::vec2;

namespace
{
int g_map = -2;
int g_cur = -1;

int find_map()
{
	if (g_map != -2)
		return g_map;
	g_map = -1;
	const int w = static_cast<int>(bc::map::width()), h = static_cast<int>(bc::map::height());
	int x0 = 1 << 30, y0 = 1 << 30, x1 = -1, y1 = -1;
	for (const auto p : bc::map::spawn_region(bc::team::enemy).positions()) // the ghost plays side b: the enemy spawn is side a's
		x0 = std::min(x0, static_cast<int>(p.x)), y0 = std::min(y0, static_cast<int>(p.y)), x1 = std::max(x1, static_cast<int>(p.x)), y1 = std::max(y1, static_cast<int>(p.y));
	for (int i = 0; i < GHOST_NMAPS; ++i)
		if (GHOST_MAPS[i].w == w && GHOST_MAPS[i].h == h && GHOST_MAPS[i].x0 == x0 && GHOST_MAPS[i].y0 == y0 &&
			(GHOST_MAPS[i].x1 == x1 || GHOST_MAPS[i].x1 == x1 + 1) && (GHOST_MAPS[i].y1 == y1 || GHOST_MAPS[i].y1 == y1 + 1))
		{
			g_map = i;
			break;
		}
	return g_map;
}

template <class F> void guard(F f)
{
	try
	{
		f();
	}
	catch (...)
	{
	}
}
} // namespace

bool ghost_draft()
{
	const int gm = find_map();
	if (gm < 0)
		return false;
	const auto& M = GHOST_MAPS[gm];
	const auto cur = bc::draft::current_draft(bc::team::ally);
	if (static_cast<int>(cur.size()) >= M.npick)
		return false;
	bc::draft::pick(static_cast<bc::champion_draft>(M.picks[cur.size()]));
	return true;
}

bool ghost_turn()
{
	const int gm = find_map();
	if (gm < 0)
		return false;
	const int r = static_cast<int>(bc::round_number());
	if (r > GHOST_ROUNDS)
		return false;
	const auto& M = GHOST_MAPS[gm];
	auto& me = bc::self();
	const int ty = static_cast<int>(me.champion_name());
	if (g_cur < 0)
		g_cur = M.start;
	const int end = M.start + M.count;
	while (g_cur < end && GHOST_ACTS[5 * g_cur] < r)
		++g_cur;
	for (int i = g_cur; i < end && GHOST_ACTS[5 * i] == r; ++i)
	{
		const std::int32_t* a = GHOST_ACTS + 5 * i;
		if (a[1] != ty)
			continue;
		const int op = a[2] % 100, kind = a[2] / 100, x = a[3], y = a[4];
		const vec2 t{ x, y };
		const vec2 here = me.position();
		auto cheb2 = [](vec2 p, vec2 q) { return std::max(std::abs(p.x - q.x), std::abs(p.y - q.y)); };
		// fallbacks when the game has drifted from the ladder: the nearest target of the recorded kind within reach
		auto near_camp = [&](int reach) {
			std::optional<bc::camp> out;
			int best = 1 << 30;
			for (const auto& c : bc::vision::camps())
				if (c.is_alive() && cheb2(c.position(), here) <= reach && cheb2(c.position(), t) < best)
					best = cheb2(c.position(), t), out.emplace(c);
			return out;
		};
		auto near_enemy = [&](int reach) {
			std::optional<bc::champion> out;
			int best = 1 << 30;
			for (const auto& c : bc::vision::champions())
				if (c.is_enemy() && c.is_alive() && cheb2(c.position(), here) <= reach && cheb2(c.position(), t) < best)
					best = cheb2(c.position(), t), out.emplace(c);
			return out;
		};
		switch (op)
		{
		case 1:
			guard([&] {
				if (!(here == t))
				{
					if (cheb2(here, t) == 1)
						me.move_absolute(t);
					else
						me.move_towards(t);
				}
			});
			break;
		case 2:
			guard([&] {
				if (kind == 1 || (kind == 0 && bc::vision::camp_tiles().is_set(t)))
				{
					if (bc::vision::camp_tiles().is_set(t))
						me.attack(bc::vision::camp_at(t));
					else if (auto c = near_camp(me.attack_range()))
						me.attack(*c);
				}
				else
				{
					if (bc::vision::champion_tiles().is_set(t) && bc::vision::champion_at(t).is_enemy())
						me.attack(bc::vision::champion_at(t));
					else if (auto c = near_enemy(me.attack_range()))
						me.attack(*c);
				}
			});
			break;
		case 3:
		case 4:
			guard([&] {
				const auto ab = me.abilities()[static_cast<std::size_t>(op - 3)];
				if (kind == 1)
				{
					if (bc::vision::camp_tiles().is_set(t))
						ab.use(bc::vision::camp_at(t));
					else if (auto c = near_camp(4))
						ab.use(*c);
				}
				else if (kind == 2)
				{
					if (bc::vision::champion_tiles().is_set(t) && bc::vision::champion_at(t).is_enemy())
						ab.use(bc::vision::champion_at(t));
					else if (auto c = near_enemy(4))
						ab.use(*c);
				}
				else if (t == here)
					ab.use();
				else if (bc::vision::champion_tiles().is_set(t))
					ab.use(bc::vision::champion_at(t));
				else
					ab.use(t);
			});
			break;
		case 5: guard([&] { me.set_priority(static_cast<std::int32_t>(static_cast<std::uint32_t>(static_cast<std::uint16_t>(x)) | (static_cast<std::uint32_t>(static_cast<std::uint16_t>(y)) << 16))); }); break;
		case 6: guard([&] { me.place_ward(t); }); break;
		case 7: guard([&] { me.submit_gems(t); }); break;
		case 8: guard([&] { me.recall(); }); break;
		case 9:
			guard([&] {
				if (me.state().contains(bc::champion_state::recalling))
					me.cancel_recall();
				else if (me.state().contains(bc::champion_state::submitting_gems))
					me.cancel_submit_gems();
			});
			break;
		case 10: guard([&] { me.consumables()[bc::consumable_type::tp_crystal].use(t); }); break;
		case 11: guard([&] { me.consumables()[bc::consumable_type::altar_lock].use(t); }); break;
		case 12: guard([&] { me.buy(bc::item_type{ static_cast<std::uint32_t>(x) }, static_cast<std::uint32_t>(y)); }); break;
		case 13: guard([&] { if (me.consumables()[bc::consumable_type::tp_crystal].count() == 0) me.buy(bc::consumable_type::tp_crystal); }); break;
		case 14: guard([&] { if (me.consumables()[bc::consumable_type::altar_lock].count() == 0) me.buy(bc::consumable_type::altar_lock); }); break;
		default: break;
		}
	}
	return true;
}
