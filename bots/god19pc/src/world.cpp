#include "world.h"
#include "params.h"

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
	altar_approach.reserve(altars.size()); // reallocations are costly in fuel: reserving halved this loop
	// Opening fuel: the first turn has 200k and init used up to ~320k (lanes, ambush, corners, pilgrimage: bodies
	// lost their first 2 rounds; 84 lost turns over the 17 official maps). Memory allocation is what costs: exporting
	// a 100x100 distance field cost ~25k, unreserved vectors doubled loops. Bit reads of one packed walls export
	// replace per-tile host calls here; vectors are reserved; the hole scan visits holes only; islands and contested
	// altars are computed later (find_islands from prebuild_fields, contested() on first use).
	const auto walls_lin = walls.export_linear_buffer();
	auto bit = [](const std::vector<std::uint8_t>& v, int i) { return ((v[static_cast<std::size_t>(i) >> 3] >> (i & 7)) & 1) != 0; };
	// altar_no_camp: a camp's spawn tile is not standable while the camp lives (and the group never respawns while a body stands on it),
	// so it is no approach tile (nx50x41: the one altar's only non-hole neighbour is a monolith's tile).
	bc::bitboard camp_tiles;
	// g18_fast_init: one camp_groups() call (it builds every camp object: ~13-37k fuel) serves this loop and the group table below
	std::vector<bc::map::camp_group> fast_groups;
	if (P.g18_fast_init)
		fast_groups = bc::map::camp_groups();
	if (P.altar_no_camp)
	{
		if (P.g18_fast_init)
		{
			for (const auto& g : fast_groups)
				for (const auto& c : g.camps())
					camp_tiles.set(c.spawn_position());
		}
		else
			for (const auto& g : bc::map::camp_groups())
				for (const auto& c : g.camps())
					camp_tiles.set(c.spawn_position());
	}
	altar_block_g.assign(altars.size(), -1);
	altar_block_c.assign(altars.size(), -1);
	std::vector<vec2> blocked_tiles; // mode 2: camp tiles kept as approach tiles, resolved to their group below (groups are built after this)
	for (auto a : altars)
	{
		std::vector<vec2> app;
		app.reserve(8);
		for (int dy = -1; dy <= 1; ++dy)
			for (int dx = -1; dx <= 1; ++dx)
			{
				const vec2 p{ a.x + dx, a.y + dy };
				if (!((dx || dy) && p.x >= 0 && p.y >= 0 && p.x < W && p.y < H && !bit(walls_lin, p.y * W + p.x)))
					continue;
				if (P.altar_no_camp && camp_tiles.is_set(p))
				{
					if (P.altar_no_camp >= 2 && app.empty())
						blocked_tiles.push_back(p); // only used when no free tile exists (resolved after the free ones below)
					continue;
				}
				app.push_back(p);
			}
		if (app.empty() && P.altar_no_camp >= 2)
			for (auto p : blocked_tiles)
				if (cheb(p, a) <= 1)
				{
					app.push_back(p); // the altar opens when this camp dies
					break;
				}
		blocked_tiles.clear();
		altar_approach.push_back(std::move(app));
	}

	bc::bitboard visited;
	home.f.compute(walls, ally_spawn, visited);
	home.ready = true;
	home_reach = visited;
	const bc::bitboard enemy_walls = terrain | bc::map::altars() | ally_spawn;
	away.f.compute(enemy_walls, enemy_spawn, visited);
	away.ready = true;
	spawn_altar_d = BIG;
	for (const auto& app : altar_approach)
		for (auto t : app)
			spawn_altar_d = std::min(spawn_altar_d, home.get(t));
	no_altar = P.altar_no_camp && spawn_altar_d >= BIG; // no usable altar on foot from spawn: the game is decided on gold earned, then kills
	// altar_contested is computed on first use (contested()): ~17k fuel on altar-rich maps, not needed in the opening.
	altar_contested.clear();
	altar_enemy_round.assign(altars.size(), -1000);

	walls_no_holes = bc::map::walls() | bc::map::altars() | enemy_spawn;
	// 1-wide hole crossings: a hole tile with standable ground on both opposite sides is one dash (range 2)
	// for a dash kit. The fields used to treat every hole as a wall, so routes never planned a dash and the
	// bodies walked around (rushbait-v2 / 30x80 ladder: 62 such tiles, eight: 22, expanse: 16). Read from the
	// packed exports in plain code: per-tile host calls on 1,800-hole maps would cost ~1M fuel.
	dash_walls = walls;
	if (P.dash_holes && dash_kit && P.g18_fast_init)
	{
		// g18_fast_init: the same crossings from host-side bitboard shifts (a hole with standable ground on both opposite sides along a row,
		// a column or a diagonal); the per-hole scan below cost ~180k fuel on islands (two rounds of every dash body's opening).
		const bc::bitboard ground = ~walls;
		auto sh = [](const bc::bitboard& b, int dx, int dy) {
			bc::bitboard t = dx ? b.shift_right(dx) : b;
			return dy ? t.shift_up(dy) : t;
		};
		bc::bitboard cross = sh(ground, 1, 0) & sh(ground, -1, 0);
		cross |= sh(ground, 0, 1) & sh(ground, 0, -1);
		cross |= sh(ground, 1, 1) & sh(ground, -1, -1);
		cross |= sh(ground, 1, -1) & sh(ground, -1, 1);
		cross &= bc::map::holes();
		dash_walls = walls & ~cross;
	}
	else if (P.dash_holes && dash_kit)
	{
		// Only the hole tiles are visited (a full-map scan cost ~87k fuel on lanes, most of the first turn).
		auto ground = [&](int x, int y) { return x >= 0 && y >= 0 && x < W && y < H && !bit(walls_lin, y * W + x); };
		for (const auto h : bc::map::holes().positions())
		{
			static constexpr int D[4][2] = { { 1, 0 }, { 0, 1 }, { 1, 1 }, { 1, -1 } };
			for (const auto& d : D)
				if (ground(h.x - d[0], h.y - d[1]) && ground(h.x + d[0], h.y + d[1]))
				{
					dash_walls.set(h, false);
					break;
				}
		}
	}
	groups.clear();
	int id = 0;
	const auto all_groups = P.g18_fast_init ? std::move(fast_groups) : bc::map::camp_groups();
	groups.reserve(all_groups.size());
	for (const auto& g : all_groups)
	{
		Group G;
		G.handle = static_cast<std::uint32_t>(static_cast<bc::handle_camp_group_t>(g));
		G.id = id++;
		G.gems = static_cast<int>(g.gem_value());
		G.gold = static_cast<int>(g.gold_value());
		G.respawn = g.max_respawn_timer();
		long sx = 0, sy = 0;
		const auto camps = g.camps();
		G.camps.reserve(camps.size()), G.tiles.reserve(camps.size()), G.hp.reserve(camps.size());
		for (const auto& c : camps)
		{
			const auto s = c.base_stats();
			CampRef r{ c, c.kind(), c.spawn_position(), s.base_health, s.base_strength };
			if (s.base_strength > 0 && s.base_attack_range > 0)
				r.range = s.base_attack_range;
			G.camps.push_back(r);
			G.tiles.push_back(r.pos);
			G.mask.set(r.pos);
			G.near.draw_chebyshev(r.pos, static_cast<float>(r.range));
			G.max_range = std::max(G.max_range, r.range);
			G.max_hp += s.base_health;
			G.dps += s.base_strength;
			G.hp.push_back(s.base_health);
			if (c.kind() == bc::camp_type::monolith)
				G.monolith = true;
			if (c.kind() == bc::camp_type::elk)
				G.elk = true;
			if (s.base_strength > 0)
				G.harmless = false, ++G.attackers;
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
		G.d_home_c = dist_home(G.center);
		for (auto t : G.tiles)
			G.radius = std::max(G.radius, cheb(t, G.center));
		G.update_cluster();
		if (P.mono_plan && G.gems > 0)
		{
			const float rate = static_cast<float>(G.gems) / static_cast<float>(std::max(1, G.respawn));
			mono_rate_total += rate;
			if (G.monolith && G.camps.size() == 1)
			{
				mono_rate_lone += rate;
				if (G.d_ally < BIG)
					mono_groups.push_back(G.id);
				if (G.d_ally < BIG && G.d_enemy < BIG && G.d_ally + G.d_enemy > 0)
				{
					const float r = static_cast<float>(G.d_ally) / static_cast<float>(G.d_ally + G.d_enemy);
					mono_mid = std::min(mono_mid, std::min(r, 1.f - r));
				}
			}
		}
		if (P.obj_plan && G.gems > 0)
		{
			// Objective-map detector input (see detect_objective), gathered here to keep init fuel flat.
			const float rate = static_cast<float>(G.gems) / static_cast<float>(std::max(1, G.respawn));
			obj_rate_total += rate;
			if (G.max_hp >= P.obj_min_hp && G.d_ally < BIG && G.attackers >= P.obj_min_attackers)
			{
				obj_rate_heavy += rate;
				obj_groups.push_back(G.id);
			}
		}
		groups.push_back(std::move(G));
	}
	if (P.altar_no_camp >= 2)
		for (std::size_t i = 0; i < altars.size(); ++i)
			for (auto t : altar_approach[i])
				if (!P.g18_fast_init || camp_tiles.is_set(t)) // g18_fast_init: only a camp tile can match below (islands: ~255k fuel)
				for (auto& g : groups)
					for (std::size_t c = 0; c < g.camps.size(); ++c)
						if (g.camps[c].pos == t)
						{
							altar_block_g[i] = g.id, altar_block_c[i] = static_cast<int>(c);
							g.unlock = true;
						}
	hops.assign(groups.size(), Hop{});
	mono_share = mono_rate_total > 0 ? mono_rate_lone / mono_rate_total : 0;
	// mono_size50: only on 50x50 maps (contest and its copies). On the 24 generated monolith-only test maps (maps/gold*/gold_mono*, 30-80
	// wide) the blob opening + bush warding lost to _px9 29 of 60 vs legend_m10's 39; on contest and 33 copies it won 88-97%.
	// mono_size50 2: no size test; the lone monoliths must stand near the middle instead (contest and its copies 0.49 at any size; the
	// generated monolith-only maps where the plan lost have them on each half, 0.39-0.42)
	mono_mode = P.mono_plan && mono_rate_total > 0 && mono_share >= P.mono_share
		&& (!P.mono_size50 || (P.mono_size50 == 1 ? (W == 50 && H == 50) : mono_mid >= P.mono_center));
	detect_objective();
}

bool World::contested(int i)
{
	if (altar_contested.empty())
	{
		altar_contested.assign(altars.size(), false);
		for (std::size_t k = 0; k < altars.size(); ++k)
		{
			int dh = BIG, da = BIG;
			for (auto t : altar_approach[k])
				dh = std::min(dh, home.get(t)), da = std::min(da, away.get(t));
			altar_contested[k] = dh < BIG && da < BIG && std::abs(dh - da) <= 6;
		}
	}
	return altar_contested[static_cast<std::size_t>(i)];
}

void World::detect_objective()
{
	// Heavy = too much health for one body to clear in a few trips (elk 2,400, monolith 20,000; stampede's fused
	// group 17,400). Gem rate = gems per respawn round; a centre group counts once for the whole map, side groups
	// once per copy, so the share is map-wide. The sums are gathered in init_static's group loop.
	if (mono_mode && P.mono_obj)
	{
		// Lone monoliths are the whole gem supply: plan them as the team objective (obj_min_attackers 2 excluded them).
		obj_groups = mono_groups;
		obj_share = mono_share;
		obj_mode = !obj_groups.empty();
		if (obj_mode)
		{
			std::sort(obj_groups.begin(), obj_groups.end(), [&](int a, int b) { return groups[static_cast<std::size_t>(a)].d_ally < groups[static_cast<std::size_t>(b)].d_ally; });
			for (int id : obj_groups)
				groups[static_cast<std::size_t>(id)].objective = true;
		}
		return;
	}
	obj_share = obj_rate_total > 0 ? obj_rate_heavy / obj_rate_total : 0;
	obj_mode = !obj_groups.empty() && static_cast<int>(obj_groups.size()) <= P.obj_max_groups && obj_share >= P.obj_share;
	if (!obj_mode)
		return;
	std::sort(obj_groups.begin(), obj_groups.end(), [&](int a, int b) { return groups[static_cast<std::size_t>(a)].d_ally < groups[static_cast<std::size_t>(b)].d_ally; });
	for (int id : obj_groups)
		groups[static_cast<std::size_t>(id)].objective = true;
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
	team_champs = 0;
	ring_comp = false;
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
		ring_comp = ring_comp || a.type == bc::champion_type::prism || a.type == bc::champion_type::tavi;
		team_champs += a.type != bc::champion_type::issac;
		allies.push_back(a);
		++i;
	}
	std::uint32_t count = 0;
	bc::detail::check(bc::detail::sdk_num_enemies(&count));
	std::vector<std::uint32_t> handles(count);
	bc::detail::check(bc::detail::sdk_enemies(handles.data(), count, &count));
	for (std::uint32_t i = 0; i < count; ++i)
		enemies.push_back(Enemy{ std::nullopt, handles[i], bc::champion_type::ryth, Kit{} });
	if (P.enemy_comp_init)
	{
		// v9: the enemy composition from round 1 (BotAPICpp: champion_name() "live champions read it without vision"), so the
		// opponent model and the danger maps know the kits before the first sighting. Perception still refreshes them on sight.
		try
		{
			for (const auto& c : bc::champions(team::enemy))
			{
				const auto h = handle_of(c);
				for (auto& e : enemies)
					if (e.handle == h)
					{
						e.type = c.champion_name();
						e.kit = kit_of(bc::champion_designs[static_cast<std::size_t>(e.type)]);
					}
			}
		}
		catch (...)
		{
		}
	}
}

void Group::update_cluster()
{
	if (P.g18_fast_init && camps.size() <= 1)
	{
		cluster = 1.f; // what the loop below computes for one camp, without the loop
		return;
	}
	int best = 0, live = 0;
	for (std::size_t i = 0; i < camps.size(); ++i)
	{
		if (hp[i] <= 0)
			continue;
		++live;
		int n = 0;
		for (std::size_t j = 0; j < camps.size(); ++j)
			n += hp[j] > 0 && cheb(camps[i].pos, camps[j].pos) <= 1;
		best = std::max(best, n);
	}
	// Splash on the best target hits `best` camps while all live; as they die it falls to 1.
	cluster = best <= 1 ? 1.f : (static_cast<float>(best) + 1.f) * 0.5f + (best >= 3 ? 0.2f : 0.f);
	(void)live;
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
	if (P.fz_wardblock)
		bc::vision::ward_tiles_into(ward_occ);
	try
	{
		bc::vision::altar_lock_tiles_into(team::enemy, enemy_locks);
	}
	catch (...)
	{
		enemy_locks.clear();
	}

	// Enemies: global alive flag is always readable; details only when visible.
	update_alive(round);
	for (auto& e : enemies)
	{
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
		e.recall_fresh = flag(info.state, bc::champion_state::recall_started);
		if (e.recalling)
		{
			// v17: a real recall cannot move and lands within the recall time; a body seen recalling on consecutive rounds at different
			// tiles (Mite: cancel, act, recall again every turn) fakes it.
			if (e.rec_round == round - 1 && e.rec_pos != e.pos)
				++enemy_recall_cancels;
			e.rec_round = round, e.rec_pos = e.pos;
		}
#ifdef PROBE17
		if (e.recalling)
			std::printf("PR r=%d h=%d n=%d\n", round, static_cast<int>(e.handle), enemy_recall_cancels);
#endif
		if (P.g17_fakerec > 0 && enemy_recall_cancels >= P.g17_fakerec)
			e.recalling = false; // v17: their recalls are bait: never a channel
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
		if (P.fm_buffs)
		{
			// v9 tasks T09: shields (Varg 2.5 x focus, Heart of Ruin 1.5 x focus) and stuns are invisible in the health number.
			e.shield = 0.f, e.stunned = false;
			std::array<bc::detail::buff_data, static_cast<std::size_t>(bc::buff_types::count)> raw{};
			std::uint32_t n = 0;
			if (bc::detail::sdk_champion_buff_data(e.handle, raw.data(), static_cast<std::uint32_t>(raw.size()), &n) == 0)
				for (std::uint32_t k = 0; k < n && k < raw.size(); ++k)
				{
					if (raw[k].type == static_cast<std::uint32_t>(bc::buff_types::shield))
						e.shield = std::max(0.f, raw[k].data.shield.value);
					else if (raw[k].type == static_cast<std::uint32_t>(bc::buff_types::stun))
						e.stunned = true;
				}
		}
		e.seen_round = round;
	}
	for (auto& a : allies)
	{
		bc::detail::champion_info info{};
		a.visible = a.alive && read_champion(a.handle, info);
		if (a.visible)
		{
			if (P.ally_defend && a.seen_round == round - 1 && info.health < a.hp - 1.f)
				a.hit_round = round;
			a.seen_round = round;
			a.type = static_cast<bc::champion_type>(info.type);
			a.pos = { info.x, info.y };
			a.hp = info.health;
			a.max_hp = info.max_health;
			a.str = info.strength;
			a.focus = info.focus;
			a.channeling = (flag(info.state, bc::champion_state::recalling) && !(P.g17_bait && P.g17_ally_fresh)) ||
				flag(info.state, bc::champion_state::submitting_gems) || flag(info.state, bc::champion_state::teleporting);
			if (!a.kit_ready)
			{
				a.kit = kit_of(bc::champion_designs[static_cast<std::size_t>(a.type)]);
				a.kit_ready = true;
				const auto bs = bc::champion_designs[static_cast<std::size_t>(a.type)].base_stats();
				a.base_hp = bs.base_health, a.hp_growth = bs.health_growth, a.base_str = bs.base_strength, a.str_growth = bs.strength_growth;
				a.base_focus = bs.base_focus, a.focus_growth = bs.focus_growth;
			}
		}
	}

	// Camp groups: cheap raw state query; the engine reports unknown when unseen.
	for (auto& g : groups)
	{
		std::uint32_t s = 0;
		bool changed = false; // a camp died or came back: the splash cluster changes only then
		if (bc::detail::sdk_camp_group_state(g.handle, &s) == 0 && s != 0)
		{
			g.seen_round = round;
			if (s == 1)
			{
				changed |= g.st != ST_ALIVE;
				g.st = ST_ALIVE;
				float total = 0;
				bool awake = false;
				for (std::size_t i = 0; i < g.camps.size(); ++i)
				{
					bc::detail::camp_state cs{};
					if (bc::detail::sdk_camp(handle_of(g.camps[i].camp), &cs) == 0)
					{
						changed |= (g.hp[i] > 0) != (cs.health > 0);
						g.hp[i] = cs.health;
					}
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
				if (g.st != ST_REWARD)
					g.reward_round = round;
				changed |= g.st != ST_REWARD;
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
				changed = true;
				g.st = ST_ALIVE;
				for (std::size_t i = 0; i < g.camps.size(); ++i)
					g.hp[i] = g.camps[i].max_hp;
				g.hp_total = g.max_hp;
			}
			else if (g.st == ST_REWARD && round - g.seen_round > 8)
			{
				g.st = ST_RESPAWN;
				g.ready_round = g.seen_round + static_cast<int>(bc::constants::capture_time) + 1 + g.respawn; // the reward lands one round after the capture phases
			}
		}
		g.enemy_on_tile = false;
		if (changed)
			g.update_cluster();
	}

	// Enemy proximity to altars (contested-altar discipline).
	for (const auto& e : enemies)
		if (e.visible)
			for (std::size_t i = 0; i < altars.size(); ++i)
				if (cheb(altars[i], e.pos) <= 6)
					altar_enemy_round[i] = round;
	// Enemy proximity to groups.
	for (const auto& e : enemies)
		if (e.visible)
			for (auto& g : groups)
			{
				const int d = cheb(g.center, e.pos);
				if (d <= 6)
					g.enemy_round = round;
				if (d <= g.radius && g.mask.is_set(e.pos)) // host call only when it can be on a tile
					g.enemy_on_tile = true;
			}
}

void World::update_alive(int round)
{
	// Cheap (one host call per ally); also run while this body is dead so deaths it did not witness get
	// their real round (the respawn escort predicts respawns from it).
	for (auto& a : allies)
	{
		std::int32_t alive = 1;
		if (bc::detail::sdk_champion_is_alive(a.handle, &alive) == 0)
		{
			if (a.alive && !alive)
				a.died_round = round, ++ally_deaths;
			a.alive = alive != 0;
		}
	}
	for (auto& e : enemies)
	{
		std::int32_t alive = 1;
		if (bc::detail::sdk_champion_is_alive(e.handle, &alive) == 0)
		{
			if (e.alive && !alive)
				e.died_round = round, ++enemy_deaths;
			e.alive = alive != 0;
		}
	}
}

bool World::altar_open(int i) const
{
	const auto k = static_cast<std::size_t>(i);
	if (altar_approach[k].empty())
		return false;
	if (P.altar_no_camp < 2 || altar_block_g[k] < 0)
		return true;
	const auto& g = groups[static_cast<std::size_t>(altar_block_g[k])];
	// Open while the blocking camp is dead: the reward waits (ST_REWARD), or the group respawns later, or its camp is at 0 health.
	return g.st == ST_REWARD || g.st == ST_RESPAWN || (g.st == ST_ALIVE && g.seen_round >= 0 && g.hp[static_cast<std::size_t>(altar_block_c[k])] <= 0);
}

bool World::no_altar_now() const
{
	if (no_altar)
		return true;
	if (P.altar_no_camp < 2)
		return false;
	for (std::size_t i = 0; i < altars.size(); ++i)
		if (altar_open(static_cast<int>(i)) && !altar_approach[i].empty())
		{
			int d = BIG;
			for (auto t : altar_approach[i])
				d = std::min(d, home.get(t));
			if (d < BIG)
				return false;
		}
	return true;
}

const bc::bitboard& World::route_walls() const { return P.dash_holes && dash_kit && round >= dash_off_until ? dash_walls : walls; }
