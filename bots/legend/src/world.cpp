#include "world.h"

World& world()
{
	static World w;
	return w;
}

static vec2 centroid(const bc::bitboard& mask)
{
	const auto pts = mask.positions();
	if (pts.empty())
		return { 0, 0 };
	long sx = 0, sy = 0;
	for (auto p : pts)
		sx += p.x, sy += p.y;
	return { static_cast<int>(sx / static_cast<long>(pts.size())), static_cast<int>(sy / static_cast<long>(pts.size())) };
}

void World::init_static()
{
	W = bc::map::width();
	H = bc::map::height();
	terrain = bc::map::walls() | bc::map::holes();
	ally_spawn = bc::map::spawn_region(team::ally);
	enemy_spawn = bc::map::spawn_region(team::enemy);
	walls = terrain | bc::map::altars() | enemy_spawn;
	ally_spawn_c = centroid(ally_spawn);
	enemy_spawn_c = centroid(enemy_spawn);

	altars = bc::map::altars().positions();
	altar_approach.clear();
	for (auto a : altars)
	{
		std::vector<vec2> app;
		for (int dy = -1; dy <= 1; ++dy)
			for (int dx = -1; dx <= 1; ++dx)
			{
				const vec2 p{ a.x + dx, a.y + dy };
				if ((dx || dy) && bc::map::is_in_bounds(p) && !walls.is_set(p))
					app.push_back(p);
			}
		altar_approach.push_back(std::move(app));
	}

	bc::bitboard visited;
	home.f.compute(walls, ally_spawn, visited);
	home.ready = true;
	home_reach = visited;
	const bc::bitboard enemy_walls = terrain | bc::map::altars() | ally_spawn;
	away.f.compute(enemy_walls, enemy_spawn, visited);
	away.ready = true;

	groups.clear();
	int id = 0;
	for (const auto& g : bc::map::camp_groups())
	{
		Group G;
		G.handle = static_cast<std::uint32_t>(static_cast<bc::handle_camp_group_t>(g));
		G.id = id++;
		G.gems = static_cast<int>(g.gem_value());
		G.gold = static_cast<int>(g.gold_value());
		G.respawn = g.max_respawn_timer();
		long sx = 0, sy = 0;
		for (const auto& c : g.camps())
		{
			const auto s = c.base_stats();
			CampRef r{ c, c.kind(), c.spawn_position(), s.base_health, s.base_strength };
			G.camps.push_back(r);
			G.tiles.push_back(r.pos);
			G.mask.set(r.pos);
			G.near.draw_chebyshev(r.pos, 3.0f);
			G.max_hp += s.base_health;
			G.dps += s.base_strength;
			G.hp.push_back(s.base_health);
			if (c.kind() == bc::camp_type::monolith)
				G.monolith = true;
			if (c.kind() == bc::camp_type::elk)
				G.elk = true;
			if (s.base_strength > 0)
				G.harmless = false;
			sx += r.pos.x, sy += r.pos.y;
			const int da = dist_home(r.pos), de = dist_away(r.pos);
			G.d_ally = std::min(G.d_ally, da);
			G.d_enemy = std::min(G.d_enemy, de);
		}
		const int n = static_cast<int>(G.tiles.size());
		const vec2 mean{ static_cast<int>(sx / std::max(1, n)), static_cast<int>(sy / std::max(1, n)) };
		G.center = G.tiles.front();
		for (auto t : G.tiles)
			if (cheb(t, mean) < cheb(G.center, mean))
				G.center = t;
		G.hp_total = G.max_hp;
		G.ours = G.d_ally <= G.d_enemy;
		groups.push_back(std::move(G));
	}
}

void World::find_islands()
{
	islands.clear();
	island_of.assign(groups.size(), -1);
	const auto& camp_tiles_all = [&] {
		bc::bitboard m;
		for (const auto& g : groups)
			m |= g.mask;
		return m;
	}();
	for (auto& g : groups)
	{
		if (g.d_ally < BIG || island_of[static_cast<std::size_t>(g.id)] >= 0 || bc::fuel_remaining() < 60000)
			continue;
		// Region reachable from this group on foot (the island interior).
		bc::distance_field f;
		bc::bitboard visited;
		f.compute(walls, g.mask, visited);
		Island isl;
		for (auto& h : groups)
			if (h.d_ally >= BIG && visited.is_set(h.tiles.front()))
			{
				isl.groups.push_back(h.id);
				isl.gems += h.gems;
			}
		if (isl.groups.empty())
			continue;
		// Landing tiles: free interior tiles. Launch tiles: walkable from home within Chebyshev 3 of one.
		const bc::bitboard interior = visited & ~walls & ~camp_tiles_all;
		const auto inner = interior.positions();
		bc::bitboard near_inner;
		for (auto t : inner)
			near_inner.draw_chebyshev(t, 3.f);
		const bc::bitboard launch_cand = near_inner & home_reach & ~walls & ~camp_tiles_all;
		for (auto r : launch_cand.positions())
		{
			const int d = dist_home(r);
			if (d < isl.launch_home)
				isl.launch_home = d, isl.launch = r;
		}
		if (isl.launch_home < BIG)
			for (auto t : inner)
				if (cheb(t, isl.launch) <= 3 && (isl.land.x < 0 || cheb(t, isl.launch) < cheb(isl.land, isl.launch)))
					isl.land = t; // nearest valid landing tile
		if (isl.launch_home >= BIG)
			continue;
		bc::bitboard root;
		root.set(isl.launch);
		isl.to_launch.f.compute(walls, root, visited);
		isl.to_launch.ready = true;
		const int idx = static_cast<int>(islands.size());
		for (int id : isl.groups)
			island_of[static_cast<std::size_t>(id)] = idx;
		islands.push_back(std::move(isl));
	}
}

void World::init_units()
{
	allies.clear();
	enemies.clear();
	const auto me = handle_of(bc::self());
	int i = 0;
	for (const auto& c : bc::champions(team::ally))
	{
		Ally a{ c, handle_of(c), bc::champion_type::ryth };
		bc::detail::champion_info info{};
		if (read_champion(a.handle, info))
			a.type = static_cast<bc::champion_type>(info.type);
		if (a.handle == me)
			my_index = i;
		allies.push_back(a);
		++i;
	}
	std::uint32_t count = 0;
	bc::detail::check(bc::detail::sdk_num_enemies(&count));
	std::vector<std::uint32_t> handles(count);
	bc::detail::check(bc::detail::sdk_enemies(handles.data(), count, &count));
	for (std::uint32_t i = 0; i < count; ++i)
		enemies.push_back(Enemy{ std::nullopt, handles[i], bc::champion_type::ryth, Kit{} });
}

int World::group_at(vec2 p) const
{
	for (const auto& g : groups)
		if (g.mask.is_set(p))
			return g.id;
	return -1;
}

bool World::altar_locked_by_enemy(int altar_index) const
{
	return enemy_locks.is_set(altars[static_cast<std::size_t>(altar_index)]);
}

void World::perceive(vec2 me)
{
	(void)me;
	bc::vision::visible_tiles_into(vis);
	bc::vision::camp_tiles_into(camp_occ);
	bc::vision::champion_tiles_into(team::ally, ally_occ);
	bc::vision::champion_tiles_into(team::enemy, enemy_occ);
	bc::vision::teleport_tiles_into(tele_occ);
	try
	{
		bc::vision::altar_lock_tiles_into(team::enemy, enemy_locks);
	}
	catch (...)
	{
		enemy_locks.clear();
	}

	// Enemies: global alive flag is always readable; details only when visible.
	for (auto& e : enemies)
	{
		std::int32_t alive = 1;
		if (bc::detail::sdk_champion_is_alive(e.handle, &alive) == 0)
		{
			if (e.alive && !alive)
				e.died_round = round;
			e.alive = alive != 0;
		}
		bc::detail::champion_info info{};
		e.visible = e.alive && read_champion(e.handle, info);
		if (!e.visible)
			continue;
		const auto t = static_cast<bc::champion_type>(info.type);
		if (!e.ch)
			e.ch.emplace(bc::detail::handle_access::make_champion(static_cast<bc::handle_champion_t>(e.handle)));
		if (e.seen_round < 0 || e.type != t)
		{
			e.type = t;
			e.kit = kit_of(bc::champion_designs[static_cast<std::size_t>(t)]);
		}
		e.pos = { info.x, info.y };
		e.hp = info.health;
		e.max_hp = info.max_health;
		e.str = info.strength;
		e.focus = info.focus;
		e.state = info.state;
		e.recalling = flag(info.state, bc::champion_state::recalling);
		e.tributing = flag(info.state, bc::champion_state::submitting_gems);
		e.channeling = e.recalling || e.tributing || flag(info.state, bc::champion_state::teleporting);
		std::uint32_t gems = 0;
		if (bc::detail::sdk_champion_gems(e.handle, &gems) == 0)
			e.gems = gems;
		for (std::uint32_t slot = 0; slot < 2; ++slot)
		{
			std::int32_t c = 0;
			e.cd[slot] = bc::detail::sdk_champion_cooldown(e.handle, slot, &c) == 0 ? c : 0;
		}
		e.seen_round = round;
	}
	for (auto& a : allies)
	{
		std::int32_t alive = 1;
		if (bc::detail::sdk_champion_is_alive(a.handle, &alive) == 0)
			a.alive = alive != 0;
		bc::detail::champion_info info{};
		a.visible = a.alive && read_champion(a.handle, info);
		if (a.visible)
		{
			a.type = static_cast<bc::champion_type>(info.type);
			a.pos = { info.x, info.y };
			a.hp = info.health;
			a.max_hp = info.max_health;
			a.str = info.strength;
		}
	}

	// Camp groups: cheap raw state query; the engine reports unknown when unseen.
	for (auto& g : groups)
	{
		std::uint32_t s = 0;
		if (bc::detail::sdk_camp_group_state(g.handle, &s) == 0 && s != 0)
		{
			g.seen_round = round;
			if (s == 1)
			{
				g.st = ST_ALIVE;
				float total = 0;
				bool awake = false;
				for (std::size_t i = 0; i < g.camps.size(); ++i)
				{
					bc::detail::camp_state cs{};
					if (bc::detail::sdk_camp(handle_of(g.camps[i].camp), &cs) == 0)
						g.hp[i] = cs.health;
					total += g.hp[i];
					if (g.hp[i] > 0 && cheb(g.camps[i].pos, me) <= 6)
					{
						std::uint32_t cst = 0;
						if (bc::detail::sdk_camp_state(handle_of(g.camps[i].camp), &cst) == 0 && cst == 1)
							awake = true;
					}
				}
				g.hp_total = total;
				g.awake = awake;
			}
			else if (s == 2)
			{
				g.st = ST_REWARD;
				g.awake = false;
				for (auto& h : g.hp)
					h = 0;
				g.hp_total = 0;
			}
			else if (s == 3)
			{
				std::int32_t timer = 0;
				bc::detail::sdk_camp_group_cooldown(g.handle, &timer);
				g.st = ST_RESPAWN;
				g.ready_round = round + timer;
				g.awake = false;
			}
		}
		else
		{
			// Unseen: advance our belief.
			if (g.st == ST_RESPAWN && round >= g.ready_round)
			{
				g.st = ST_ALIVE;
				for (std::size_t i = 0; i < g.camps.size(); ++i)
					g.hp[i] = g.camps[i].max_hp;
				g.hp_total = g.max_hp;
			}
			else if (g.st == ST_REWARD && round - g.seen_round > 8)
			{
				g.st = ST_RESPAWN;
				g.ready_round = g.seen_round + 6 + g.respawn;
			}
		}
		g.enemy_on_tile = false;
	}

	// Enemy proximity to groups.
	for (const auto& e : enemies)
		if (e.visible)
			for (auto& g : groups)
			{
				const int d = cheb(g.center, e.pos);
				if (d <= 6)
					g.enemy_round = round;
				if (g.mask.is_set(e.pos))
					g.enemy_on_tile = true;
			}
}
