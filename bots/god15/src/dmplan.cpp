#include "dmplan.h"

#include "params.h"

#include <cmath>

using D = bc::champion_draft;

bc::champion_type dm_type_of(bc::champion_draft d)
{
	switch (d)
	{
	case D::ren: return bc::champion_type::ren;
	case D::stellar: return bc::champion_type::stellar;
	case D::cassi_and_issac: return bc::champion_type::cassi; // the fragile half of the pair
	case D::varg: return bc::champion_type::varg;
	case D::ryth: return bc::champion_type::ryth;
	case D::tavi: return bc::champion_type::tavi;
	case D::prism: return bc::champion_type::prism;
	case D::vendetta: return bc::champion_type::vendetta;
	case D::marcella: return bc::champion_type::marcella;
	case D::vesper_vale: return bc::champion_type::vesper_vale;
	case D::willow: return bc::champion_type::willow;
	default: return d == D_HOR ? CT_HOR : bc::champion_type::ren;
	}
}

DraftPlan& draft_plan()
{
	static DraftPlan p;
	return p;
}

std::vector<std::uint8_t> dm_encode(const DraftPlan& p)
{
	// Layout v1 (docs/COMMS.md): fixed header, the per-group zone table, the ward list, a one-byte checksum.
	std::vector<std::uint8_t> b;
	b.reserve(64 + p.zone.size() + 5 * p.wards.size());
	auto u8 = [&](int v) { b.push_back(static_cast<std::uint8_t>(std::clamp(v, 0, 255))); };
	auto list = [&](const std::vector<int>& v, std::size_t cap) {
		u8(static_cast<int>(std::min(v.size(), cap)));
		for (std::size_t i = 0; i < cap; ++i)
			u8(i < v.size() ? v[i] : 255);
	};
	u8(DM_MAGIC), u8(DM_VERSION), u8(p.team), u8(p.width), u8(p.height), u8(p.groups), u8(p.flags);
	list(p.ours, 5);
	list(p.theirs, 5);
	list(p.obj_groups, 8);
	list(p.anchor_slots, 5);
	for (int g = 0; g < p.groups; ++g)
		u8(g < static_cast<int>(p.zone.size()) ? p.zone[static_cast<std::size_t>(g)] : 255);
	const std::size_t nw = std::min<std::size_t>(p.wards.size(), 32);
	u8(static_cast<int>(nw));
	for (std::size_t i = 0; i < nw; ++i)
	{
		const auto& s = p.wards[i];
		u8(s.p.x), u8(s.p.y), u8(s.slot), u8(s.kind), u8(s.group);
	}
	int sum = 0;
	for (auto v : b)
		sum += v;
	u8(sum & 0xFF);
	return b;
}

bool dm_decode(const std::vector<std::uint8_t>& b, DraftPlan& o)
{
	o = DraftPlan{};
	std::size_t i = 0;
	auto has = [&](std::size_t n) { return i + n <= b.size(); };
	auto u8 = [&]() { return static_cast<int>(b[i++]); };
	auto list = [&](std::vector<int>& v, std::size_t cap) {
		const int n = u8();
		for (std::size_t k = 0; k < cap; ++k)
		{
			const int x = u8();
			if (static_cast<int>(k) < n)
				v.push_back(x);
		}
	};
	if (!has(7 + 4 * 6 + 9) || b[0] != DM_MAGIC || b[1] != DM_VERSION)
		return false;
	i = 2;
	o.team = u8(), o.width = u8(), o.height = u8(), o.groups = u8(), o.flags = u8();
	list(o.ours, 5);
	list(o.theirs, 5);
	list(o.obj_groups, 8);
	list(o.anchor_slots, 5);
	if (!has(static_cast<std::size_t>(o.groups) + 1))
		return false;
	for (int g = 0; g < o.groups; ++g)
		o.zone.push_back(u8());
	const int nw = u8();
	if (nw > 32 || !has(static_cast<std::size_t>(5 * nw) + 1))
		return false;
	for (int k = 0; k < nw; ++k)
	{
		DmSpot s;
		s.p.x = u8(), s.p.y = u8(), s.slot = u8(), s.kind = u8(), s.group = u8();
		o.wards.push_back(s);
	}
	int sum = 0;
	for (std::size_t k = 0; k < i; ++k)
		sum += b[k];
	if ((sum & 0xFF) != b[i])
		return false;
	o.ok = true;
	return true;
}

void dm_build(DraftPlan& p)
{
	// Draft turn, once (the first draft turn has 10x fuel): map facts the bodies would otherwise each recompute or never compute.
	p.width = bc::map::width();
	p.height = bc::map::height();
	const auto groups = bc::map::camp_groups();
	p.groups = static_cast<int>(std::min<std::size_t>(groups.size(), 255));
	const bc::bitboard walls = bc::map::walls() | bc::map::holes() | bc::map::altars();
	bc::distance_field home, away;
	bc::bitboard visited;
	home.compute(walls | bc::map::spawn_region(team::enemy), bc::map::spawn_region(team::ally), visited);
	away.compute(walls | bc::map::spawn_region(team::ally), bc::map::spawn_region(team::enemy), visited);
	auto dist = [](const bc::distance_field& f, vec2 t) { const auto v = f.get(t); return v == UNREACH ? (1 << 20) : static_cast<int>(v); };
	struct G
	{
		vec2 c;
		int da, de, gems;
		bool heavy, ours, gem_group;
		float hp;
		int attackers;
	};
	std::vector<G> gs;
	bc::bitboard camp_tiles;
	float sg = 0, sm = 0;
	int our_gem_groups = 0, our_monos = 0, unreachable = 0;
	for (const auto& g : groups)
	{
		G x{ { 0, 0 }, 1 << 20, 1 << 20, static_cast<int>(g.gem_value()), false, false, false, 0.f, 0 };
		long sx = 0, sy = 0;
		int n = 0;
		bool mono = false, gemish = false;
		for (const auto& c : g.camps())
		{
			const vec2 t = c.spawn_position();
			camp_tiles.set(t);
			x.da = std::min(x.da, dist(home, t));
			x.de = std::min(x.de, dist(away, t));
			sx += t.x, sy += t.y, ++n;
			const auto s = c.base_stats();
			x.hp += s.base_health;
			x.attackers += s.base_strength > 0;
			mono |= c.kind() == bc::camp_type::monolith;
			gemish |= c.kind() == bc::camp_type::gem_cluster || c.kind() == bc::camp_type::wolf || c.kind() == bc::camp_type::elk;
		}
		x.c = { static_cast<int>(sx / std::max(1, n)), static_cast<int>(sy / std::max(1, n)) };
		x.ours = x.da <= x.de;
		x.heavy = mono || x.gems >= P.om_heavy;
		x.gem_group = gemish && !mono;
		const int resp = std::max(1, static_cast<int>(g.max_respawn_timer()));
		sg += static_cast<float>(g.gold_value()) / static_cast<float>(resp);
		sm += static_cast<float>(g.gem_value()) / static_cast<float>(resp);
		if (x.ours)
		{
			our_gem_groups += x.gem_group;
			our_monos += mono && g.camps().size() == 1;
		}
		if (x.da >= (1 << 20) && x.de >= (1 << 20))
			++unreachable;
		gs.push_back(x);
	}
	(void)unreachable;
	// Map type flags.
	p.flags = 0;
	int our_heavy_gem = 0;
	for (const auto& x : gs)
		our_heavy_gem += x.ours && x.gem_group && x.hp >= P.obj_min_hp && x.attackers >= P.obj_min_attackers;
	if (our_gem_groups == 1 && our_heavy_gem == 1)
		p.flags |= DMF_OBJECTIVE;
	if (our_gem_groups == 0 && our_monos > 0)
		p.flags |= DMF_MONOLITH;
	if (sm > 0.f && sg / sm > 8.f)
		p.flags |= DMF_GOLD_HEAVY;
	bool altar_reach = false;
	const auto altars = bc::map::altars().positions();
	for (const auto a : altars)
		for (int dy = -1; dy <= 1 && !altar_reach; ++dy)
			for (int dx = -1; dx <= 1 && !altar_reach; ++dx)
			{
				const vec2 t{ a.x + dx, a.y + dy };
				altar_reach = bc::map::is_in_bounds(t) && !walls.is_set(t) && !camp_tiles.is_set(t) && dist(home, t) < (1 << 20);
			}
	if (!altar_reach)
		p.flags |= DMF_NO_ALTAR;
	for (const auto& x : gs)
		if (x.ours && x.da >= (1 << 20))
			p.flags |= DMF_ISLANDS;
	// Heavy groups and monoliths on our half, nearest first.
	p.obj_groups.clear();
	std::vector<int> order;
	for (int k = 0; k < static_cast<int>(gs.size()); ++k)
		if (gs[static_cast<std::size_t>(k)].ours && gs[static_cast<std::size_t>(k)].heavy)
			order.push_back(k);
	std::sort(order.begin(), order.end(), [&](int a, int b) { return gs[static_cast<std::size_t>(a)].da < gs[static_cast<std::size_t>(b)].da; });
	for (int k : order)
		if (p.obj_groups.size() < 8 && k < 255)
			p.obj_groups.push_back(k);
	// Zone owner per group: our half split into team-size angular sectors around our spawn (slot k = sector k, sorted clockwise from the
	// direction of the enemy spawn). Informational: zone farming lost in session 13 (x_zone), so no farming rule reads it.
	const int team = std::max(1, static_cast<int>(bc::draft::team_size()));
	vec2 hs{ 0, 0 }, es{ 0, 0 };
	{
		const auto a = bc::map::spawn_region(team::ally).positions(), e = bc::map::spawn_region(team::enemy).positions();
		long ax = 0, ay = 0, ex = 0, ey = 0;
		for (auto t : a)
			ax += t.x, ay += t.y;
		for (auto t : e)
			ex += t.x, ey += t.y;
		if (!a.empty())
			hs = { static_cast<int>(ax / static_cast<long>(a.size())), static_cast<int>(ay / static_cast<long>(a.size())) };
		if (!e.empty())
			es = { static_cast<int>(ex / static_cast<long>(e.size())), static_cast<int>(ey / static_cast<long>(e.size())) };
	}
	const double base = std::atan2(static_cast<double>(es.y - hs.y), static_cast<double>(es.x - hs.x));
	std::vector<std::pair<double, int>> ang;
	for (int k = 0; k < static_cast<int>(gs.size()); ++k)
		if (gs[static_cast<std::size_t>(k)].ours)
		{
			double a = std::atan2(static_cast<double>(gs[static_cast<std::size_t>(k)].c.y - hs.y), static_cast<double>(gs[static_cast<std::size_t>(k)].c.x - hs.x)) - base;
			while (a < 0)
				a += 2 * 3.14159265358979;
			ang.push_back({ a, k });
		}
	std::sort(ang.begin(), ang.end());
	p.zone.assign(static_cast<std::size_t>(p.groups), 255);
	for (std::size_t j = 0; j < ang.size(); ++j)
		if (ang[j].second < p.groups)
			p.zone[static_cast<std::size_t>(ang[j].second)] = static_cast<int>(j * static_cast<std::size_t>(team) / std::max<std::size_t>(1, ang.size()));
	// Planned ward spots: bushes next to our altars and groups (a body stands still there), and the enemy-facing approach of our altars
	// and of heavy / midline groups. Best first, at least 4 tiles apart.
	struct Cand
	{
		vec2 p;
		float score;
		int kind, group, slot;
	};
	std::vector<Cand> cands;
	const auto& bush = bc::map::bushes();
	auto nearest_group = [&](vec2 t) {
		int best = 255, bd = 1 << 20;
		for (int k = 0; k < static_cast<int>(gs.size()); ++k)
			if (gs[static_cast<std::size_t>(k)].ours && cheb(gs[static_cast<std::size_t>(k)].c, t) < bd)
				bd = cheb(gs[static_cast<std::size_t>(k)].c, t), best = k;
		return best;
	};
	auto add_target = [&](vec2 c, float w, bool altar, int group, bool approach) {
		int bkind = altar ? DMW_BUSH_ALTAR : DMW_BUSH_GROUP, akind = altar ? DMW_APPROACH_ALTAR : DMW_APPROACH_GROUP;
		vec2 app{ -1, -1 };
		int app_d = 1 << 20;
		for (int dy = -3; dy <= 3; ++dy)
			for (int dx = -3; dx <= 3; ++dx)
			{
				const vec2 t{ c.x + dx, c.y + dy };
				if (!bc::map::is_in_bounds(t) || walls.is_set(t) || camp_tiles.is_set(t) || dist(home, t) >= (1 << 20))
					continue;
				const int g = group >= 0 ? group : nearest_group(t);
				const int slot = g < p.groups ? p.zone[static_cast<std::size_t>(g)] : 255;
				if (bush.is_set(t))
					cands.push_back({ t, w + 1.f, bkind, g, slot });
				if (cheb(t, c) >= 2 && dist(away, t) < app_d)
					app_d = dist(away, t), app = t;
			}
		if (approach && app.x >= 0)
		{
			const int g = group >= 0 ? group : nearest_group(app);
			cands.push_back({ app, w, akind, g, g < p.groups ? p.zone[static_cast<std::size_t>(g)] : 255 });
		}
	};
	for (const auto a : altars)
	{
		const int da = dist(home, a), de = dist(away, a); // the altar tile itself is a wall: use the nearest open neighbour
		int ha = 1 << 20, ea = 1 << 20;
		for (int dy = -1; dy <= 1; ++dy)
			for (int dx = -1; dx <= 1; ++dx)
			{
				const vec2 t{ a.x + dx, a.y + dy };
				if (bc::map::is_in_bounds(t) && !walls.is_set(t))
					ha = std::min(ha, dist(home, t)), ea = std::min(ea, dist(away, t));
			}
		(void)da, (void)de;
		if (ha >= (1 << 20) || ha > ea)
			continue;
		add_target(a, 3.f + (std::abs(ha - ea) <= 6 ? 1.f : 0.f), true, -1, true);
	}
	for (int k = 0; k < static_cast<int>(gs.size()); ++k)
	{
		const auto& x = gs[static_cast<std::size_t>(k)];
		if (!x.ours || x.da >= (1 << 20))
			continue;
		const bool mid = x.de - x.da <= 6;
		add_target(x.c, (x.heavy ? 2.f : 0.5f) + (mid ? 1.f : 0.f), false, k, x.heavy || mid); // every group's bushes; approaches of heavy / midline ones
	}
	std::sort(cands.begin(), cands.end(), [&](const Cand& a, const Cand& b) {
		return a.score != b.score ? a.score > b.score : dist(home, a.p) < dist(home, b.p);
	});
	p.wards.clear();
	for (const auto& c : cands)
	{
		if (p.wards.size() >= 32)
			break;
		bool close = false;
		for (const auto& s : p.wards)
			close |= cheb(s.p, c.p) < 4;
		if (close)
			continue;
		p.wards.push_back({ c.p, c.slot, c.kind, c.group });
	}
}
