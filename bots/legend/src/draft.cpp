// Draft: choose a whole team composition for this map, then pick its champions in order.
//
// Picks are simultaneous and duplicates across teams are allowed, so there is nothing to deny: the job is to
// field the composition that wins most on this kind of map. Composition values come from round-robin
// tournaments of the same bot code with forced drafts (tools/draft_tournament.py) on the ladder maps and
// our generated pool, split by team size, plus small adjustments for map features measured here.
// The choice is made once (first draft turn, 1M fuel) and kept, so later picks never switch plans.
#include "draft.h"

#include <cstdio>

#include "common.h"
#include "params.h"

#include <cmath>
#if __has_include("draft_table.h")
#include "draft_table.h"
#define LEGEND_DRAFT_TABLE 1
#endif

namespace
{
using D = bc::champion_draft;

struct Features
{
	int team = 3;
	int groups = 0, gem = 0, gold = 0, wolf = 0, elk = 0, mono = 0, multi = 0, harmless = 0;
	int gem_groups = 0;		   // groups that give gems (excluding monolith-only)
	double mean_dist = 0;
	int area = 0, holes = 0, altars = 0;
	bool ready = false;
};

struct Comp
{
	const char* name;
	std::array<D, 5> picks;
	std::array<double, 3> base; // tournament value at team size 3, 4, 5
};

// Values: win rate in the composition round robin (tools/draft_tournament.py, same bot code, forced drafts),
// split by team size 3 / 4 / 5. October 17 run: 8 drafts, 45 maps (12 real ladder, 6 official, 27 generated)
// x 2 sides, 2,520 games. Ren, Stellar, Cassi & Issac (+ Varg, Ryth) had the best mean and worst case; at team
// size 4 Varg as the fourth pick beat Ryth (0.626 vs 0.610). Vendetta, C&I, Varg, Stellar, Ren was level at
// size 5. Willow- and Vesper-based drafts finished last. Older drafts keep their earlier values (5-draft run).
// A per-map nearest-neighbour model (tools/draft_model.py) did not beat this team-size choice in
// leave-one-map-out validation against the strong drafts, so it is not shipped (draft_table.h absent).
const std::array<Comp, 6> COMPS{ {
	{ "meta", { D::ren, D::stellar, D::cassi_and_issac, D::ryth, D::varg }, { 0.603, 0.610, 0.556 } },
	{ "metaV", { D::ren, D::stellar, D::cassi_and_issac, D::varg, D::ryth }, { 0.603, 0.626, 0.565 } },
	{ "vci", { D::vendetta, D::cassi_and_issac, D::varg, D::stellar, D::ren }, { 0.516, 0.599, 0.565 } },
	{ "ciS", { D::stellar, D::cassi_and_issac, D::varg, D::tavi, D::ren }, { 0.46, 0.46, 0.55 } },
	{ "ciY", { D::stellar, D::cassi_and_issac, D::varg, D::ryth, D::tavi }, { 0.46, 0.49, 0.51 } },
	{ "cur", { D::varg, D::tavi, D::stellar, D::ren, D::ryth }, { 0.50, 0.48, 0.36 } },
} };

Features F;
int chosen = -1;

void analyse()
{
	F.team = static_cast<int>(bc::draft::team_size());
	F.area = bc::map::width() * bc::map::height();
	F.holes = static_cast<int>(bc::map::holes().count());
	F.altars = static_cast<int>(bc::map::altars().count());
	const bc::bitboard walls = bc::map::walls() | bc::map::holes() | bc::map::altars();
	bc::distance_field home, away;
	bc::bitboard visited;
	home.compute(walls | bc::map::spawn_region(team::enemy), bc::map::spawn_region(team::ally), visited);
	away.compute(walls | bc::map::spawn_region(team::ally), bc::map::spawn_region(team::enemy), visited);
	double dsum = 0;
	for (const auto& g : bc::map::camp_groups())
	{
		int da = BIG, de = BIG, attackers = 0;
		bool has_elk = false, has_mono = false, has_wolf = false, has_gem = false, has_gold = false;
		for (const auto& c : g.camps())
		{
			const auto a = home.get(c.spawn_position()), e = away.get(c.spawn_position());
			da = std::min(da, a == UNREACH ? BIG : static_cast<int>(a));
			de = std::min(de, e == UNREACH ? BIG : static_cast<int>(e));
			switch (c.kind())
			{
			case bc::camp_type::wolf: has_wolf = true, ++attackers; break;
			case bc::camp_type::elk: has_elk = true, ++attackers; break;
			case bc::camp_type::monolith: has_mono = true, ++attackers; break;
			case bc::camp_type::gem_cluster: has_gem = true; break;
			case bc::camp_type::gold_cluster: has_gold = true; break;
			}
		}
		if (da > de || da >= BIG)
			continue; // count our half only (the map is symmetric)
		++F.groups;
		F.gem += has_gem;
		F.gold += has_gold;
		F.wolf += has_wolf;
		F.elk += has_elk;
		F.mono += has_mono;
		F.multi += attackers >= 2;
		F.harmless += attackers == 0;
		F.gem_groups += (has_gem || has_wolf || has_elk) && !has_mono;
		dsum += da;
	}
	F.mean_dist = F.groups ? dsum / F.groups : 0;
	F.ready = true;
}

double comp_value(const Comp& c)
{
	const int ts = std::clamp(F.team, 3, 5) - 3;
	double v = c.base[static_cast<std::size_t>(ts)];
	const auto end = c.picks.begin() + std::clamp(F.team, 3, 5);
	const bool has_varg = std::find(c.picks.begin(), end, D::varg) != end;
	const bool has_ryth = std::find(c.picks.begin(), end, D::ryth) != end;
	// Multi-camp packs on our half: Varg's splash clears them several times faster (wolf-pack maps).
	if (F.groups > 0 && F.multi * 5 >= F.groups * 2 && has_varg)
		v += 0.03;
	// Elk-heavy maps without packs: Ryth's health and area stun tank them.
	if (F.elk >= 2 && F.multi * 5 < F.groups * 2 && has_ryth)
		v += 0.01;
	// Monolith-only maps (no other gem source): a 1200-health tank with an area stun.
	if (F.gem_groups == 0 && F.mono > 0 && has_ryth)
		v += 0.03;
	return v;
}

#ifdef LEGEND_DRAFT_TABLE
// Map-aware choice (content-based: "maps like this one"): compare this map's features with the training maps of
// the composition tournament and take the composition that did best on the most similar ones, shrunk towards
// its average at this team size. Feature vector and normalisation must match tools/draft_model.py.
int choose_table()
{
	namespace T = draft_table;
	const double g = std::max(1, F.groups), area = std::max(1, F.area);
	const std::array<double, T::NF> x{ std::log(area), static_cast<double>(F.groups), F.multi / g, F.elk / g, F.mono > 0 ? 1.0 : 0.0,
		F.wolf / g, F.gem_groups / g, F.harmless / g, F.mean_dist / std::sqrt(area), F.holes / area, static_cast<double>(F.altars) };
	std::array<double, T::NF> z{};
	for (int j = 0; j < T::NF; ++j)
		z[static_cast<std::size_t>(j)] = (x[static_cast<std::size_t>(j)] - T::MEAN[static_cast<std::size_t>(j)]) / T::SD[static_cast<std::size_t>(j)];
	const int team = std::clamp(F.team, 3, 5);
	std::array<double, T::NCOMP> base{};
	int nbase = 0;
	std::array<std::pair<double, int>, T::ROWS.size()> d{};
	for (std::size_t r = 0; r < T::ROWS.size(); ++r)
	{
		const auto& row = T::ROWS[r];
		double s2 = 0;
		for (int j = 0; j < T::NF; ++j)
		{
			const double dz = z[static_cast<std::size_t>(j)] - row.z[static_cast<std::size_t>(j)];
			s2 += dz * dz;
		}
		d[r] = { std::sqrt(s2) + T::TEAM_PENALTY * std::abs(row.team - team), static_cast<int>(r) };
		if (row.team == team)
		{
			++nbase;
			for (int c = 0; c < T::NCOMP; ++c)
				base[static_cast<std::size_t>(c)] += row.score[static_cast<std::size_t>(c)];
		}
	}
	std::sort(d.begin(), d.end());
	const int k = std::min<int>(T::K, static_cast<int>(d.size()));
	int best = 0;
	double bv = -1e9;
	for (int c = 0; c < T::NCOMP; ++c)
	{
		double v = T::PRIOR * (nbase ? base[static_cast<std::size_t>(c)] / nbase : 0.5);
		for (int i = 0; i < k; ++i)
			v += T::ROWS[static_cast<std::size_t>(d[static_cast<std::size_t>(i)].second)].score[static_cast<std::size_t>(c)];
		v /= T::PRIOR + k;
		if (v > bv)
			bv = v, best = c;
	}
	return best;
}
#endif

int choose_comp()
{
	int best = 0;
	double bv = -1e9;
	for (std::size_t i = 0; i < COMPS.size(); ++i)
	{
		const double v = comp_value(COMPS[i]);
		if (v > bv)
			bv = v, best = static_cast<int>(i);
	}
	return best;
}
} // namespace

int official_map()
{
	static int cached = -2;
	if (cached != -2)
		return cached;
	cached = OM_NONE;
	try
	{
		const int w = bc::map::width(), h = bc::map::height();
		int gem = 0, wolf = 0;
		for (const auto& g : bc::map::camp_groups())
			for (const auto& c : g.camps())
				gem += c.kind() == bc::camp_type::gem_cluster, wolf += c.kind() == bc::camp_type::wolf;
		struct M { int w, h, id; };
		static const M T[] = { { 100, 100, OM_AMBUSH }, { 41, 41, OM_COLLISION }, { 71, 71, OM_CORNERS }, { 41, 30, OM_EIGHT },
			{ 80, 80, OM_EXPANSE }, { 40, 40, OM_INTERLOCK }, { 90, 30, OM_LANES }, { 31, 31, OM_PACKS }, { 50, 65, OM_PILGRIMAGE },
			{ 30, 80, OM_RUSHBAIT }, { 60, 50, OM_STAMPEDE }, { 45, 30, OM_SWIRL } };
		for (const auto& m : T)
			if (m.w == w && m.h == h)
				cached = m.id;
		if (w == 50 && h == 50) // contest: monoliths and gold only; monolith: 8 gem clusters a side; rows: 1
			cached = gem == 0 ? OM_CONTEST : gem >= 10 ? OM_MONOLITH : OM_ROWS;
		if (w == 30 && h == 30) // elkring: elks and gold only
			cached = wolf == 0 ? OM_ELKRING : OM_FRAGMENT;
	}
	catch (...)
	{
	}
	return cached;
}

namespace
{
// Sparring proxies (mapdraft 1 and 2): the per-map drafts of the two top ladder teams, read from 33 of their ladder games
// (experiments/interwin_oct18: the 13 games between them; experiments/ladder_m5, experiments/ladder_top3). Both draft the
// same way every time on a map, whoever the opponent is. Order: OfficialMap; then the defaults by team size 3, 4, 5.
// Draft ids: Ryth 0, Vesper 1, Vendetta 2, C&I 3, Stellar 4, Prism 5, Marcella 6, Willow 7, Ren 8, Varg 9, Tavi 10.
constexpr int MITE[][5] = {
	{ 9, 4, 3, 10, 8 }, { 9, 0, 3, -1, -1 }, { 5, 4, 3, 0, 10 }, { 9, 4, 3, 0, 10 }, { 9, 4, 3, 0, 10 }, { 9, 4, 3, 0, 10 },
	{ 8, 4, 3, -1, -1 }, { 9, 4, 3, -1, -1 }, { 9, 0, 3, 4, -1 }, { 9, 4, 3, 10, 8 }, { 9, 4, 3, 0, 10 }, { 8, 4, 3, -1, -1 },
	{ 9, 4, 3, 10, 8 }, { 9, 0, 3, 8, -1 }, { 9, 0, 3, 4, -1 }, { 5, 4, 3, 0, 10 }, { 9, 0, 3, 4, -1 },
	{ 9, 4, 3, -1, -1 }, { 9, 0, 3, 4, -1 }, { 9, 4, 3, 0, 10 } };
constexpr int IFISH[][5] = {
	{ 8, 4, 3, 0, 9 }, { 8, 4, 3, -1, -1 }, { 4, 10, 5, 3, 8 }, { 8, 4, 3, 0, 9 }, { 8, 4, 3, 0, 9 }, { 8, 4, 3, 0, 9 },
	{ 3, 4, 9, -1, -1 }, { 8, 4, 3, -1, -1 }, { 8, 4, 3, 0, -1 }, { 8, 4, 3, 0, 9 }, { 8, 4, 3, 0, 9 }, { 8, 4, 3, -1, -1 },
	{ 8, 4, 3, 0, 9 }, { 3, 4, 9, 8, -1 }, { 8, 4, 3, 0, -1 }, { 4, 10, 5, 3, 8 }, { 8, 4, 3, 0, -1 },
	{ 8, 4, 3, -1, -1 }, { 8, 4, 3, 0, -1 }, { 8, 4, 3, 0, 9 } };

// mapdraft 3: our composition, except on the official maps where the top teams' choice beat ours in our own brain
// (session 10; 6 third-party opponents x 2 sides per map, 88-game cells): Ryth, not Varg, as the fourth pick on rushbait-v2
// and interlock (both top teams draft it; ifish keeps Varg on rows), C&I, Stellar, Varg on expanse (ifish), and on stampede
// the 2nd team's all-caster draft for the ring plan (md_stampede; o2_ring clears the 6-elk objective from distance 4).
// On those four maps: 44 of 48 games won vs 26 for our own draft. Swirl with Ryth: 6 of 12 vs 7 and 90 rounds slower
// unopposed (Varg's splash on its 12 wolf packs), so swirl keeps ours.
constexpr int OURS[][5] = {
	{ -1 }, { -1 }, { -1 }, { -1 }, { -1 }, { -1 }, { 3, 4, 9, -1, -1 }, { -1 }, { 8, 4, 3, 0, -1 }, { -1 }, { -1 }, { -1 },
	{ -1 }, { -1 }, { 8, 4, 3, 0, -1 }, { 5, 4, 3, 0, 10 }, { -1 } };

bool table_pick(const std::vector<D>& mine)
{
	const int om = official_map();
	if (P.mapdraft == 3 && (om < 0 || OURS[om][0] < 0 || (om == OM_STAMPEDE && !P.md_stampede)))
		return false;
	const int (*T)[5] = P.mapdraft == 3 ? OURS : P.mapdraft == 1 ? MITE : IFISH;
	const int ts = std::clamp(static_cast<int>(bc::draft::team_size()), 3, 5);
	const int* row = T[om >= 0 ? om : 17 + ts - 3];
	for (int k = 0; k < 5 && row[k] >= 0; ++k)
	{
		const auto c = static_cast<D>(row[k]);
		if (std::find(mine.begin(), mine.end(), c) == mine.end())
		{
			bc::draft::pick(c);
			return true;
		}
	}
	return false;
}
} // namespace

void play_draft()
{
	const auto mine = bc::draft::current_draft(team::ally);
#ifdef LEGEND_FEATURES
	// One line of map features for the offline draft model (tools/draft_model.py).
	if (!F.ready)
	{
		try
		{
			analyse();
		}
		catch (...)
		{
		}
		std::printf("FEAT team=%d groups=%d gem=%d gold=%d wolf=%d elk=%d mono=%d multi=%d harmless=%d gem_groups=%d mean_dist=%.2f area=%d holes=%d altars=%d\n",
			F.team, F.groups, F.gem, F.gold, F.wolf, F.elk, F.mono, F.multi, F.harmless, F.gem_groups, F.mean_dist, F.area, F.holes, F.altars);
	}
#endif
	if (P.mapdraft >= 1 && P.mapdraft <= 3)
	{
		try
		{
			if (table_pick(mine))
				return;
		}
		catch (...)
		{
		}
	}
#ifdef LEGEND_DRAFT
	// Forced composition for experiments: picks in this order (champion_draft values).
	{
		static const int forced[] = { LEGEND_DRAFT };
		for (int f : forced)
		{
			const auto c = static_cast<D>(f);
			if (std::find(mine.begin(), mine.end(), c) == mine.end())
			{
				bc::draft::pick(c);
				return;
			}
		}
	}
#endif
	try
	{
		if (!F.ready)
			analyse();
	}
	catch (...)
	{
		F.ready = true; // fall back to base values
	}
	if (chosen < 0)
	{
		try
		{
#ifdef LEGEND_DRAFT_TABLE
			chosen = P.draft_model ? 100 + choose_table() : choose_comp();
#else
			chosen = choose_comp();
#endif
		}
		catch (...)
		{
			chosen = 0;
		}
	}
	D pick = D::stellar;
	bool found = false;
	std::array<D, 5> plan = COMPS[0].picks;
#ifdef LEGEND_DRAFT_TABLE
	if (chosen >= 100)
		plan = draft_table::COMPS[static_cast<std::size_t>(chosen - 100)].picks;
	else
#endif
		plan = COMPS[static_cast<std::size_t>(chosen)].picks;
	for (auto c : plan)
		if (std::find(mine.begin(), mine.end(), c) == mine.end())
		{
			pick = c, found = true;
			break;
		}
	if (!found)
	{
		const D fallback[] = { D::stellar, D::cassi_and_issac, D::varg, D::tavi, D::ren, D::ryth, D::vendetta, D::marcella, D::vesper_vale, D::prism, D::willow };
		for (auto f : fallback)
			if (std::find(mine.begin(), mine.end(), f) == mine.end())
			{
				pick = f;
				break;
			}
	}
	try
	{
		const std::array<std::uint8_t, 4> mem{ 0xB7, 2, static_cast<std::uint8_t>(F.team), static_cast<std::uint8_t>(chosen) };
		bc::draft_memory = mem;
	}
	catch (...)
	{
	}
	bc::draft::pick(pick);
}
