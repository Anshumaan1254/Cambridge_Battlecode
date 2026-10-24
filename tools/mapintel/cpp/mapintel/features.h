// mapintel/features.h: runtime map features, version 1 (MAPAnalysis.md 5.8). The C++ twin of tools/mapintel/features.py: the same names,
// order and definitions (FEATURE_NAMES; features.py documents each), checked equal on the 40 official maps and perturbed copies by the
// test bot (tools/mapintel/test_library.py). Team-relative: computed for the calling bot's own team (ally).
//
// Usage (once, on the first draft turn: 1M fuel):
//     const auto view = mapintel::load_view();               // the map, the groups and the BFS fields (shared with plans.h)
//     const auto F = mapintel::compute_features(view);       // F.v[i] in FEATURE_NAMES order
// Fuel (measured by the test bot on the 40 official maps): load_view + compute_features stay well under the first draft turn's budget
// (see tools/mapintel/README.md for the numbers). Fuel notes: a zero-initialised std::vector costs ~1.2 fuel per byte in this engine, so
// field buffers are left uninitialised and filled by the host export; bitboard operations are host calls (~2.5k on a 100x100 map).
#pragma once
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <memory>
#include <span>
#include <vector>

namespace mapintel
{
inline constexpr int FEATURES_VERSION = 1;
inline constexpr int NF = 47;
inline constexpr const char* FEATURE_NAMES[NF] = {
	"w", "h", "area", "sym", "team", "walk_share", "wall_share", "hole_share", "bush_share", "altars", "groups", "n_wolf", "n_elk",
	"n_gem_cluster", "n_gold_cluster", "n_monolith", "n_golem", "gems", "gold", "gem_rate", "gold_rate", "gold_per_gem", "spawn_dist",
	"gems_own_share", "gems_mid_share", "gold_mid_share", "wide_contested_value_share", "dist_gem_weighted", "dist_nearest_gem_group",
	"hp_total", "gems_per_khp", "gems_heavy_share", "n_heavy", "mono_golem_gem_share", "cluster_only_gem_share", "max_group_gems",
	"mean_respawn_w", "dist_nearest_altar", "altars_walk", "altar_camp_gated", "bank_mode", "bank_mode_enemy", "altars_own",
	"dist_nearest_altar_enemy", "islands", "safe_area_share", "reserved" };

struct Camp
{
	int type, x, y;
	float hp, str;
	int range;
};

struct Group
{
	int gems, gold, respawn;
	double hp;
	std::vector<Camp> camps;
};

struct Bits
{
	// a bitboard as export_linear_buffer() packs it: bit i = y * W + x, least significant bit first (tested without a host call)
	std::vector<std::uint8_t> b;
	int count = 0;
	bool operator[](int i) const { return (b[static_cast<std::size_t>(i) >> 3] >> (i & 7)) & 1; }
};

struct Field
{
	// a distance field exported row-major (uint16, 65535 = not reached) into an uninitialised buffer
	std::unique_ptr<std::uint16_t[]> v;
	int operator[](int i) const { return v[static_cast<std::size_t>(i)] == 65535 ? -1 : static_cast<int>(v[static_cast<std::size_t>(i)]); }
};

// The map as the engine shows it, with the BFS fields of features.py: fc[0] (ally) / fc[1] (enemy): camps passable; fb: every camp
// alive; fn: spawns passable (from the ally spawn).
struct MapView
{
	int W = 0, H = 0, sym = 0, team = 0;
	Bits wall, hole, bush, altar, spawn[2]; // spawn[0] = ally, spawn[1] = enemy
	std::vector<std::pair<int, int>> camp_at; // (tile index, camp type), sorted by tile
	std::vector<Group> groups;
	std::vector<cambc::vec2> altar_tiles;	  // row-major order (y, then x), as the Python dump
	std::vector<int> spawn_tiles[2];
	Field fc[2], fb[2], fn;
	cambc::bitboard camps_bb, blocked[2];	  // camp tiles; wall | hole | altar | the other team's spawn (per team)

	int at(int x, int y) const { return y * W + x; }
	bool in(int x, int y) const { return x >= 0 && y >= 0 && x < W && y < H; }
	bool pass(int t, int x, int y) const
	{
		const int i = at(x, y);
		return !wall[i] && !hole[i] && !altar[i] && !spawn[1 - t][i];
	}
	int camp_type(int i) const
	{
		const auto it = std::lower_bound(camp_at.begin(), camp_at.end(), std::make_pair(i, -1));
		return it != camp_at.end() && it->first == i ? it->second : -1;
	}
};

inline Bits pack(const cambc::bitboard& b)
{
	Bits out;
	out.b = b.export_linear_buffer();
	out.count = static_cast<int>(b.count());
	return out;
}

inline Field bfs_field(const cambc::bitboard& walls, const cambc::bitboard& roots, int area)
{
	cambc::distance_field f;
	cambc::bitboard visited;
	f.compute(walls, roots, visited);
	Field out;
	out.v.reset(new std::uint16_t[static_cast<std::size_t>(area)]);  // no value-initialisation: the export writes every entry
	f.export_linear_buffer(std::span<std::uint16_t>(out.v.get(), static_cast<std::size_t>(area)));
	return out;
}

inline MapView load_view(int team_size = -1)
{
	namespace bc = cambc;
	MapView m;
	m.W = bc::map::width();
	m.H = bc::map::height();
	const int area = m.W * m.H;
	m.sym = static_cast<int>(bc::map::symmetry());
	if (team_size < 0)
	{
		try
		{
			team_size = static_cast<int>(bc::draft::team_size());
		}
		catch (...)
		{
			team_size = -1;
		}
	}
	m.team = team_size;
	m.wall = pack(bc::map::walls());
	m.hole = pack(bc::map::holes());
	m.bush = pack(bc::map::bushes());
	m.altar = pack(bc::map::altars());
	m.spawn[0] = pack(bc::map::spawn_region(bc::team::ally));
	m.spawn[1] = pack(bc::map::spawn_region(bc::team::enemy));
	for (const auto& g : bc::map::camp_groups())
	{
		Group G{ static_cast<int>(g.gem_value()), static_cast<int>(g.gold_value()), g.max_respawn_timer(), 0.0, {} };
		for (const auto& c : g.camps())
		{
			const auto s = c.base_stats();
			const auto p = c.spawn_position();
			G.camps.push_back({ static_cast<int>(c.kind()), p.x, p.y, s.base_health, s.base_strength, s.base_attack_range });
			G.hp += static_cast<double>(s.base_health);
			m.camp_at.push_back({ m.at(p.x, p.y), static_cast<int>(c.kind()) });
			m.camps_bb.set(p);
		}
		m.groups.push_back(std::move(G));
	}
	std::sort(m.camp_at.begin(), m.camp_at.end());
	m.altar_tiles = bc::map::altars().positions();
	std::sort(m.altar_tiles.begin(), m.altar_tiles.end(), [](bc::vec2 a, bc::vec2 b) { return a.y != b.y ? a.y < b.y : a.x < b.x; });
	for (int t = 0; t < 2; ++t)
		for (const auto p : bc::map::spawn_region(t == 0 ? bc::team::ally : bc::team::enemy).positions())
			m.spawn_tiles[t].push_back(m.at(p.x, p.y));
	const auto base = bc::map::walls() | bc::map::holes() | bc::map::altars();
	const bc::team side[2] = { bc::team::ally, bc::team::enemy };
	for (int t = 0; t < 2; ++t)
	{
		m.blocked[t] = base | bc::map::spawn_region(side[1 - t]);
		m.fc[t] = bfs_field(m.blocked[t], bc::map::spawn_region(side[t]), area);
		m.fb[t] = bfs_field(m.blocked[t] | m.camps_bb, bc::map::spawn_region(side[t]), area);
	}
	m.fn = bfs_field(base, bc::map::spawn_region(bc::team::ally), area);
	return m;
}

struct Features
{
	std::array<double, NF> v{};
	bool ok = false;
};

inline Features compute_features(const MapView& m)
{
	namespace bc = cambc;
	Features F;
	auto& v = F.v;
	const int area = m.W * m.H;
	// the three terrain kinds never share a tile (one kind per tile in a map), so the blocked count is their sum
	const int nblock = m.wall.count + m.hole.count + m.altar.count;
	int k = 0;
	v[k++] = m.W;
	v[k++] = m.H;
	v[k++] = area;
	v[k++] = m.sym;
	v[k++] = m.team;
	v[k++] = static_cast<double>(area - nblock) / area;
	v[k++] = static_cast<double>(m.wall.count) / area;
	v[k++] = static_cast<double>(m.hole.count) / area;
	v[k++] = static_cast<double>(m.bush.count) / area;
	v[k++] = static_cast<double>(m.altar_tiles.size());
	v[k++] = static_cast<double>(m.groups.size());
	int cnt[6] = { 0, 0, 0, 0, 0, 0 };
	for (const auto& g : m.groups)
		for (const auto& c : g.camps)
			if (c.type >= 0 && c.type < 6)
				++cnt[c.type];
	for (int t = 0; t < 6; ++t)
		v[k++] = cnt[t];
	long Sg = 0, So = 0;
	double gr = 0, orr = 0;
	for (const auto& g : m.groups)
	{
		Sg += g.gems;
		So += g.gold;
		gr += static_cast<double>(g.gems) / g.respawn;
		orr += static_cast<double>(g.gold) / g.respawn;
	}
	v[k++] = static_cast<double>(Sg);
	v[k++] = static_cast<double>(So);
	v[k++] = gr;
	v[k++] = orr;
	v[k++] = static_cast<double>(So) / std::max<long>(1, Sg);
	int sp = -1;
	for (const int i : m.spawn_tiles[1])
	{
		const int dd = m.fn[i];
		if (dd >= 0 && (sp < 0 || dd < sp))
			sp = dd;
	}
	v[k++] = sp;
	const std::size_t G = m.groups.size();
	std::vector<int> dU(G, -1), dE(G, -1);
	for (std::size_t g = 0; g < G; ++g)
		for (const auto& c : m.groups[g].camps)
		{
			const int i = m.at(c.x, c.y);
			const int a = m.fc[0][i], b = m.fc[1][i];
			if (a >= 0 && (dU[g] < 0 || a < dU[g]))
				dU[g] = a;
			if (b >= 0 && (dE[g] < 0 || b < dE[g]))
				dE[g] = b;
		}
	double own = 0, midg = 0, mido = 0, wide = 0, valsum = 0, wsum = 0, wd = 0, heavy = 0, mono = 0, clus = 0, hp = 0, rw = 0;
	int nearest = -1, nheavy = 0, maxg = 0;
	for (std::size_t g = 0; g < G; ++g)
	{
		const auto& gr_ = m.groups[g];
		const bool both = dU[g] >= 0 && dE[g] >= 0;
		if (both && dU[g] + 6 < dE[g])
			own += gr_.gems;
		const bool mid = both && std::abs(dU[g] - dE[g]) <= 6;
		if (mid)
			midg += gr_.gems, mido += gr_.gold;
		const double val = gr_.gems + 0.1 * gr_.gold;
		valsum += val;
		if (both && std::abs(dU[g] - dE[g]) <= 12)
			wide += val;
		if (gr_.gems > 0 && dU[g] >= 0)
		{
			wsum += static_cast<double>(gr_.gems) / gr_.respawn;
			wd += dU[g] * static_cast<double>(gr_.gems) / gr_.respawn;
			if (nearest < 0 || dU[g] < nearest)
				nearest = dU[g];
		}
		hp += gr_.hp;
		if (gr_.hp >= 4800)
			heavy += gr_.gems, ++nheavy;
		bool mg = false, co = true;
		for (const auto& c : gr_.camps)
		{
			mg |= c.type == 4 || c.type == 5;
			co &= c.type == 2 || c.type == 3;
		}
		if (mg)
			mono += gr_.gems;
		if (co)
			clus += gr_.gems;
		maxg = std::max(maxg, gr_.gems);
		rw += static_cast<double>(gr_.respawn) * gr_.gems;
	}
	const double sg1 = static_cast<double>(std::max<long>(1, Sg));
	v[k++] = 2.0 * own / sg1;
	v[k++] = midg / sg1;
	v[k++] = mido / static_cast<double>(std::max<long>(1, So));
	v[k++] = wide / std::max(1e-9, valsum);
	v[k++] = wsum > 0 ? wd / wsum : -1.0;
	v[k++] = nearest;
	v[k++] = hp;
	v[k++] = 1000.0 * static_cast<double>(Sg) / std::max(1.0, hp);
	v[k++] = heavy / sg1;
	v[k++] = nheavy;
	v[k++] = mono / sg1;
	v[k++] = clus / sg1;
	v[k++] = maxg;
	v[k++] = rw / sg1;
	// altars and their approach tiles (Chebyshev 1, inside C_t)
	int best = -1, beste = -1, walk = 0, gated = 0, ownalt = 0, mode[2] = { 2, 2 };
	for (const auto a : m.altar_tiles)
	{
		int app[2][8], na[2] = { 0, 0 };
		for (int t = 0; t < 2; ++t)
			for (int dy = -1; dy <= 1; ++dy)
				for (int dx = -1; dx <= 1; ++dx)
				{
					const int x = a.x + dx, y = a.y + dy;
					if ((dx || dy) && m.in(x, y) && m.pass(t, x, y))
						app[t][na[t]++] = m.at(x, y);
				}
		bool allcamp = na[0] > 0;
		for (int j = 0; j < na[0]; ++j)
			allcamp &= m.camp_type(app[0][j]) >= 0;
		gated |= allcamp ? 1 : 0;
		int du = -1, de = -1;
		for (int j = 0; j < na[0]; ++j)
		{
			const int dd = m.fc[0][app[0][j]];
			if (dd >= 0 && (du < 0 || dd < du))
				du = dd;
		}
		for (int j = 0; j < na[1]; ++j)
		{
			const int dd = m.fc[1][app[1][j]];
			if (dd >= 0 && (de < 0 || dd < de))
				de = dd;
		}
		if (du >= 0 && (best < 0 || du < best))
			best = du;
		if (de >= 0 && (beste < 0 || de < beste))
			beste = de;
		if (du >= 0 && (de < 0 || du + 6 < de))
			++ownalt;
		bool w0 = false;
		for (int j = 0; j < na[0]; ++j)
			w0 |= m.camp_type(app[0][j]) < 0 && m.fb[0][app[0][j]] >= 0;
		walk += w0 ? 1 : 0;
		for (int t = 0; t < 2; ++t)
		{
			bool wf = false, wc = false;
			for (int j = 0; j < na[t]; ++j)
			{
				wf |= m.camp_type(app[t][j]) < 0 && m.fb[t][app[t][j]] >= 0;
				wc |= m.fc[t][app[t][j]] >= 0;
			}
			if (wf)
				mode[t] = 0;
			else if (mode[t] > 1 && wc)
				mode[t] = 1;
		}
	}
	v[k++] = best;
	v[k++] = walk;
	v[k++] = gated;
	v[k++] = mode[0];
	v[k++] = mode[1];
	v[k++] = ownalt;
	v[k++] = beste;
	int isl = 0;
	for (std::size_t g = 0; g < G; ++g)
		isl += dU[g] < 0 ? 1 : 0;
	v[k++] = isl;
	// safe area-spell tiles: standable (C_t, no camp) and outside every striking camp's range; a group with a striking camp is "safe"
	// when one of its camps is within Chebyshev 5 of such a tile: the Chebyshev distance to the nearest safe tile = a BFS with no walls
	// rooted at the safe tiles (host calls only)
	bc::bitboard threat;
	for (const auto& g : m.groups)
		for (const auto& c : g.camps)
			if (c.str > 0)
				threat.draw_chebyshev({ c.x, c.y }, static_cast<float>(c.range));
	bc::bitboard all;
	all.draw_chebyshev({ 0, 0 }, static_cast<float>(std::max(m.W, m.H)));
	const bc::bitboard safe = all & ~(m.blocked[0] | m.camps_bb | threat);
	int nstrike = 0, nsafe = 0;
	if (!safe.is_empty())
	{
		bc::bitboard none;
		const Field ds = bfs_field(none, safe, area);
		for (const auto& g : m.groups)
		{
			bool strike = false, ok = false;
			for (const auto& c : g.camps)
				strike |= c.str > 0;
			if (!strike)
				continue;
			++nstrike;
			for (const auto& c : g.camps)
			{
				const int dd = ds[m.at(c.x, c.y)];
				ok |= dd >= 0 && dd <= 5;
			}
			nsafe += ok ? 1 : 0;
		}
	}
	else
		for (const auto& g : m.groups)
		{
			bool strike = false;
			for (const auto& c : g.camps)
				strike |= c.str > 0;
			nstrike += strike ? 1 : 0;
		}
	v[k++] = nstrike ? static_cast<double>(nsafe) / nstrike : 1.0;
	v[k++] = 0.0; // reserved
	F.ok = true;
	return F;
}

inline Features compute_features(int team_size = -1) { return compute_features(load_view(team_size)); }
} // namespace mapintel
