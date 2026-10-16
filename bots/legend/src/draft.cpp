// Draft: choose a whole team composition for this map, then pick its champions in order.
//
// Picks are simultaneous and duplicates across teams are allowed, so there is nothing to deny: the job is to
// field the composition that wins most on this kind of map. Composition values come from round-robin
// tournaments of the same bot code with forced drafts (tools/draft_tournament.py) on the ladder maps and
// our generated pool, split by team size, plus small adjustments for map features measured here.
// The choice is made once (first draft turn, 1M fuel) and kept, so later picks never switch plans.
#include "draft.h"

#include "common.h"
#include "params.h"

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

// Values: win rate in the composition round robin (tools/draft_tournament.py: 5 drafts, 39 maps x 2 sides,
// 780 games, same bot code), split by team size 3 / 4 / 5. "meta" (Ren, Stellar, Cassi & Issac, Ryth, Varg)
// had the best mean and the best worst case; the ladder's strongest team drafts it too. Our old draft
// (Varg, Tavi, Stellar, Ren, Ryth) came last. Cassi & Issac is two bodies for one pick: +33% farmers at 3.
const std::array<Comp, 5> COMPS{ {
	{ "meta", { D::ren, D::stellar, D::cassi_and_issac, D::ryth, D::varg }, { 0.54, 0.53, 0.58 } },
	{ "metaV", { D::ren, D::stellar, D::cassi_and_issac, D::varg, D::ryth }, { 0.54, 0.54, 0.58 } },
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

void play_draft()
{
	const auto mine = bc::draft::current_draft(team::ally);
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
			chosen = choose_comp();
		}
		catch (...)
		{
			chosen = 0;
		}
	}
	D pick = D::stellar;
	bool found = false;
	for (auto c : COMPS[static_cast<std::size_t>(chosen)].picks)
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
