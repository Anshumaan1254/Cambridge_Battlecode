// Draft: score champions against this map's camps, then pick greedily under composition rules.
// Picks are simultaneous and duplicates across teams are allowed, so there is no denial; we only build our best team.
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
	double mean_dist = 0;
	int area = 0, holes = 0;
	bool ready = false;
};

Features F;

void analyse()
{
	F.team = static_cast<int>(bc::draft::team_size());
	F.area = bc::map::width() * bc::map::height();
	F.holes = static_cast<int>(bc::map::holes().count());
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
		dsum += da;
	}
	F.mean_dist = F.groups ? dsum / F.groups : 0;
	F.ready = true;
}

double score(D c)
{
	const double per_body = F.groups / std::max(1.0, static_cast<double>(F.team));
	const double multi = F.groups ? static_cast<double>(F.multi) / F.groups : 0;
	const bool big = F.area >= 3600 || F.mean_dist >= 22;
	// Base values come from composition tournaments (tools/bench.py, 128 games each): the durable
	// Varg/Tavi/Stellar/Ren/Ryth core beat a Vendetta-first draft ~60% because 800-health Vendetta dies too often.
	switch (c)
	{
	case D::varg: return 10.0 + 2.0 * multi;
	case D::tavi: return 9.6 + (big ? 0.6 : 0);
	case D::stellar: return 9.3 + 1.0 * multi;
	case D::ren: return 9.2 + 1.0 * multi;
	case D::ryth: return 8.6 + (F.elk >= 2 ? 0.3 : 0) + (F.mono ? 0.2 : 0);
	case D::cassi_and_issac: return 8.2 + (per_body >= 3.5 ? 0.4 : 0) + (F.harmless >= F.team ? 0.2 : 0);
	case D::vendetta: return 8.0;
	case D::prism: return 7.0;
	case D::marcella: return 6.5 + (F.elk ? 0.3 : 0);
	case D::vesper_vale: return 6.2 + (F.gold >= 2 ? 0.4 : 0);
	case D::willow: return 5.0 + (F.elk >= 2 ? 0.5 : 0);
	}
	return 0;
}

bool is_stunner(D c) { return c == D::tavi || c == D::ryth || c == D::ren || c == D::prism || c == D::cassi_and_issac || c == D::marcella; }
bool is_tank(D c) { return c == D::varg || c == D::ryth || c == D::marcella || c == D::ren; }

D choose(const std::vector<D>& mine)
{
	std::array<D, 11> all{ D::ryth, D::vesper_vale, D::vendetta, D::cassi_and_issac, D::stellar, D::prism, D::marcella, D::willow, D::ren, D::varg, D::tavi };
	bool have_stun = false, have_tank = false;
	for (auto m : mine)
		have_stun |= is_stunner(m), have_tank |= is_tank(m);
	const int remaining = F.team - static_cast<int>(mine.size());
	D best = D::vendetta;
	double best_s = -1e9;
	for (auto c : all)
	{
		if (std::find(mine.begin(), mine.end(), c) != mine.end())
			continue;
		double s = score(c);
		if (!have_stun && remaining <= 2 && is_stunner(c))
			s += 2.0;
		if (!have_tank && remaining <= 2 && is_tank(c) && (F.elk || F.mono))
			s += 1.5;
		if (s > best_s)
			best_s = s, best = c;
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
		F.ready = true; // fall back to static scores
	}
	D pick = D::vendetta;
	try
	{
		pick = choose(mine);
	}
	catch (...)
	{
		const D fallback[] = { D::vendetta, D::varg, D::tavi, D::stellar, D::ren, D::ryth, D::marcella, D::vesper_vale, D::prism, D::willow, D::cassi_and_issac };
		for (auto f : fallback)
			if (std::find(mine.begin(), mine.end(), f) == mine.end())
			{
				pick = f;
				break;
			}
	}
	try
	{
		const std::array<std::uint8_t, 4> mem{ 0xB7, 1, static_cast<std::uint8_t>(F.team), 0 };
		bc::draft_memory = mem;
	}
	catch (...)
	{
	}
	bc::draft::pick(pick);
}
