// Draft: choose a whole team composition for this map, then pick its champions in order.
//
// Picks are simultaneous and duplicates across teams are allowed, so there is nothing to deny: the job is to
// field the composition that wins most on this kind of map. Composition values come from round-robin
// tournaments of the same bot code with forced drafts (tools/draft_tournament.py) on the ladder maps and
// our generated pool, split by team size, plus small adjustments for map features measured here.
// The choice is made once (first draft turn, 1M fuel) and kept, so later picks never switch plans.
#include "draft.h"

#include <cstdio>
#include <span>

#include "common.h"
#include "dmplan.h"
#include "params.h"
#include "tp_adapter.h"
#include "mi_draft.h"
#include "ladder_draft.h"

#include <cmath>
#if __has_include("draft_table.h")
#include "draft_table.h"
#define LEGEND_DRAFT_TABLE 1
#endif

namespace
{
using D = bc::champion_draft;

int g_last_pick = -1; // P.dm_plan: our pick of this draft turn (the plan written after it includes it)
void note_pick(D c)
{
	g_last_pick = static_cast<int>(c);
	if (!P.draft_guard)
	{
		bc::draft::pick(c);
		return;
	}
	try
	{
		bc::draft::pick(c);
		return;
	}
	catch (...)
	{
	}
	// v9 tasks T13: a pick that throws (an SDK or roster surprise) must not leave the slot to the engine's random pick.
	for (const D f : { D::ryth, D::vesper_vale, D::vendetta, D::varg, D::ren, D::marcella, D::tavi, D::prism, D::stellar, D::willow, D::cassi_and_issac })
	{
		if (f == c)
			continue;
		try
		{
			bc::draft::pick(f);
			g_last_pick = static_cast<int>(f);
			return;
		}
		catch (...)
		{
		}
	}
}

struct Features
{
	int team = 3;
	int groups = 0, gem = 0, gold = 0, wolf = 0, elk = 0, mono = 0, multi = 0, harmless = 0;
	int gem_groups = 0;		   // groups that give gems (excluding monolith-only)
	float gem_group_hp = 0;	   // pd_obj_heavy: total camp health of the heaviest gem group, and its camps that fight back
	int gem_group_att = 0;
	int gem_group_da = 0, gem_group_de = 0; // pd_obj_side: walking distance of the heaviest gem group from our spawn and from theirs
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
		float ghp = 0;
		bool has_elk = false, has_mono = false, has_wolf = false, has_gem = false, has_gold = false;
		for (const auto& c : g.camps())
		{
			const auto a = home.get(c.spawn_position()), e = away.get(c.spawn_position());
			da = std::min(da, a == UNREACH ? BIG : static_cast<int>(a));
			de = std::min(de, e == UNREACH ? BIG : static_cast<int>(e));
			ghp += c.base_stats().base_health;
			switch (c.kind())
			{
			case bc::camp_type::wolf: has_wolf = true, ++attackers; break;
			case bc::camp_type::elk: has_elk = true, ++attackers; break;
			case bc::camp_type::monolith: has_mono = true, ++attackers; break;
			case bc::camp_type::gem_cluster: has_gem = true; break;
			case bc::camp_type::gold_cluster: has_gold = true; break;
			case CAMP_GOLEM: has_elk = true, ++attackers; break; // patch 3.0: a heavy single camp (5000 hp, range 4)
			default: break;
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
		if ((has_gem || has_wolf || has_elk) && !has_mono && ghp > F.gem_group_hp)
			F.gem_group_hp = ghp, F.gem_group_att = attackers, F.gem_group_da = da, F.gem_group_de = de;
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

// mapdraft 7 (sparring proxy only): Intercontinental Fish's per-map draft, Stellar first (44 of the 45 Oct 19 INTERWIN games,
// experiments/interwin_oct19; the same table in all of them).
constexpr int ICT[][5] = {
	{ 4, 8, 3, 0, 9 }, { 4, 8, 3, -1, -1 }, { 4, 10, 5, 3, 8 }, { 4, 8, 3, 0, 9 }, { 4, 8, 3, 0, 9 }, { 4, 8, 3, 0, 9 },
	{ 3, 4, 9, -1, -1 }, { 4, 8, 3, -1, -1 }, { 4, 8, 3, 0, -1 }, { 4, 8, 3, 0, 9 }, { 4, 8, 3, 0, 9 }, { 4, 8, 3, -1, -1 },
	{ 4, 8, 3, 0, 9 }, { 4, 5, 3, 9, -1 }, { 4, 8, 3, 0, -1 }, { 4, 10, 5, 3, 8 }, { 4, 8, 3, 0, -1 },
	{ 4, 8, 3, -1, -1 }, { 4, 8, 3, 0, -1 }, { 4, 8, 3, 0, 9 } };

bool table_pick(const std::vector<D>& mine)
{
	const int om = official_map();
	if (P.mapdraft == 3 && (om < 0 || OURS[om][0] < 0 || (om == OM_STAMPEDE && !P.md_stampede)))
		return false;
	const int (*T)[5] = P.mapdraft == 7 ? ICT : P.mapdraft == 3 ? OURS : P.mapdraft == 1 ? MITE : IFISH;
	const int ts = std::clamp(static_cast<int>(bc::draft::team_size()), 3, 5);
	const int* row = T[om >= 0 ? om : 17 + ts - 3];
	for (int k = 0; k < 5 && row[k] >= 0; ++k)
	{
		const auto c = static_cast<D>(row[k]);
		if (std::find(mine.begin(), mine.end(), c) == mine.end())
		{
			note_pick(c);
			return true;
		}
	}
	return false;
}

// mapdraft 6: map-parameter draft (session 7R, the user's request). At the first draft turn the map is analysed (analyse()) and
// its parameters derived; the first pick comes from the map type alone (no enemy pick is visible yet); every later pick re-plans
// the remaining slots from champion priors + map fit + team synergy + the enemy's completed picks (current_draft(enemy) returns
// the rounds already played), then picks the next planned champion in a fixed order (so a plan equal to the old one keeps the
// old body order). On the 17 official maps the rules reproduce the per-map choices measured best in sessions 6-10 without map
// identity: open 3-champion maps (expanse) C&I, Stellar, Varg; 4-champion maps Varg only when >= 50% of our-half groups are
// multi-camp packs (swirl, rows) else Ryth (interlock, rushbait-v2); one gem group holding all gems (stampede) the caster ring.
struct MapParams
{
	int team = 5;
	double pack_share = 0, elk_share = 0, gold_share = 0;
	bool objective = false, monolith_only = false, open_small = false;
};
MapParams MP;
bool mp_ready = false;
int pd_type = 0; // 0 default (Ren first), 1 open small-team map (C&I first), 2 objective map (Prism first)

void derive_params()
{
	if (!F.ready)
		analyse();
	const double g = std::max(1, F.groups);
	MP.team = std::clamp(F.team, 3, 5);
	MP.pack_share = F.multi / g;
	MP.elk_share = F.elk / g;
	MP.gold_share = F.gold / g;
	// pd_obj_multi: the lone gem group must also be a multi-camp group (stampede and maps/obj: an elk + gem objective). On the gold_elk
	// maps the only gem group is one elk camp: no objective plan fires there, so the caster draft would farm without its ring.
	MP.objective = F.gem_groups == 1 && F.mono == 0 && (!P.pd_obj_multi || F.multi >= 1) &&
		(!P.pd_obj_heavy || (F.gem_group_hp >= P.obj_min_hp && F.gem_group_att >= P.obj_min_attackers)) && // pd_obj_heavy: the same test as the brain's objective mode
		(!P.pd_obj_side || F.gem_group_de - F.gem_group_da > P.pd_obj_mid); // pd_obj_side: the objective must be on our side, not midway between the spawns
	MP.monolith_only = F.gem_groups == 0 && F.mono > 0;
	MP.open_small = MP.team <= 3 && F.area >= P.pd_open_area && F.mean_dist >= P.pd_open_dist;
	pd_type = MP.objective ? 2 : MP.open_small ? 1 : 0;
	mp_ready = true;
}

bc::champion_type type_of(D c, int body);
int pick_range(D c, int body)
{
	static std::array<int, 32> cache{}; // 0 = not read yet (every attack range is >= 1)
	const auto k = static_cast<std::size_t>(c) * 2 + static_cast<std::size_t>(body & 1);
	if (k < cache.size() && cache[k])
		return cache[k];
	const auto ti = static_cast<std::size_t>(type_of(c, body));
	const int r = ti < bc::champion_designs.size() ? bc::champion_designs[ti].base_stats().base_attack_range : 1;
	if (k < cache.size())
		cache[k] = r;
	return r;
}
// pd_stat: roles from the engine's designs (every body melee = frontliner, one ranged body = caster); the same split as v8's name lists.
bool is_caster(D c)
{
	if (P.pd_stat)
		return c != D::cassi_and_issac && pick_range(c, 0) > 1;
	return c == D::stellar || c == D::prism || c == D::tavi || c == D::vesper_vale || c == D::willow;
}
bool is_front(D c)
{
	if (P.pd_stat)
		return pick_range(c, 0) <= 1 && (c != D::cassi_and_issac || pick_range(c, 1) <= 1);
	return c == D::ren || c == D::varg || c == D::ryth || c == D::vendetta || c == D::marcella || c == D_HOR;
}

// ---- pd_stat (patch 3.0.4): champion priors that follow the engine's numbers ----
// A pick's stat power from champion_designs (engine data, read at draft time): per body, effective health (base health + one shield)
// x the geometric mean of its damage per round against 1 and 3 targets (basic attacks +1/8 with an attack reset, Varg's splash x
// targets; spells modifier x focus / 8-round cooldown, area spells and a damaging dash x targets; Ren's retaliation per hit taken;
// Willow's heal counted as damage; Prism's focus + prism_focus_per_gem x pd_stat_gems carried; Heart of Ruin's damage + its passive
// at pd_stat_missing of its health lost). Cassi & Issac add their two bodies. A pick's relative power = its power / the mean power
// of the released picks.
bc::champion_type type_of(D c, int body)
{
	const int d = static_cast<int>(c), ci = static_cast<int>(D::cassi_and_issac);
	return static_cast<bc::champion_type>(d < ci ? d : d == ci ? d + body : d + 1);
}

double body_power(bc::champion_type t)
{
	const auto ti = static_cast<std::size_t>(t);
	if (ti >= bc::champion_designs.size())
		return 0;
	const auto& ch = bc::champion_designs[ti];
	const Kit k = kit_of(ch);
	const auto s = ch.base_stats();
	double foc = s.base_focus;
	if (t == bc::champion_type::prism)
		foc += bc::constants::passive_abilities::prism_focus_per_gem * P.pd_stat_gems;
	auto dps = [&](double tg) {
		double b = s.base_strength * (1.0 + (k.reset >= 0 ? 0.125 : 0.0));
		if (t == bc::champion_type::varg)
			b *= tg;
		double sp = 0;
		if (k.dmg >= 0)
			sp += k.dmg_mod;
		if (k.cc >= 0)
			sp += k.cc_mod;
		if (k.aoe >= 0)
			sp += k.aoe_mod * (k.aoe_radius >= 1.f ? tg : 1.0);
		if (k.dash >= 0)
			sp += k.dash_mod * (k.dash_radius >= 1.f ? tg : 1.0);
		if (k.heal >= 0)
			sp += k.heal_mod;
		double d = b + foc * sp / 8.0;
		if (t == bc::champion_type::ren)
			d += bc::constants::passive_abilities::ren_retaliation_focus_ratio * foc * std::min(tg, 3.0);
		if (SDK_HAS_HOR && t == CT_HOR)
			d *= 1.0 + 0.5 * P.pd_stat_missing; // engine constant heart_of_ruin_missing_health_damage_max_bonus (3.0 SDK only, ISSUES #35)
		return d;
	};
	const double ehp = s.base_health + (k.shield >= 0 ? k.shield_mod * foc : 0.0);
	return ehp * std::sqrt(std::max(0.0, dps(1.0) * dps(3.0)));
}

double stat_power(D c)
{
	return c == D::cassi_and_issac ? body_power(type_of(c, 0)) + body_power(type_of(c, 1)) : body_power(type_of(c, 0));
}

double rel_power(D c)
{
	static std::array<double, 16> cache{};
	static bool ready = false;
	if (!ready)
	{
		const int n = SDK_HAS_HOR ? 12 : 11;
		double sum = 0;
		for (int i = 0; i < n; ++i)
			sum += cache[static_cast<std::size_t>(i)] = stat_power(static_cast<D>(i));
		for (int i = 0; i < n; ++i)
			cache[static_cast<std::size_t>(i)] /= std::max(1e-9, sum / n);
		ready = true;
#ifdef PSTAT_TRACE
		for (int i = 0; i < n; ++i)
			std::printf("PSTAT %d %.4f\n", i, cache[static_cast<std::size_t>(i)]);
#endif
	}
	const auto i = static_cast<std::size_t>(c);
	return i < cache.size() ? cache[i] : 1.0;
}

// ---- pd_stat 3 (patch 3.0.4): the draft-value model ----
// A pick's value = sum over model features of weight x feature, every feature computed at draft time from the engine's designs
// (base stats, ability payloads, passive constants) and from this map's camp groups (analyse()); the weights (params.h pd_w_*) are the
// logistic fit of 7,520 games on engine 3.0.4 (tools/draftmodel/fit.py: win ~ side + w . (our team's features - theirs), team features
// = the sum over its picks). Nothing per champion is typed in: a balance patch changes the features, a new map the interactions.
struct PickF
{
	double hp = 0, basic = 0, splash = 0, spell = 0, area = 0, stun = 0, dash = 0, ranged = 0, gold = 0, ret = 0, bodies = 0;
};

PickF body_feats(bc::champion_type t)
{
	PickF f;
	const auto ti = static_cast<std::size_t>(t);
	if (ti >= bc::champion_designs.size())
		return f;
	const auto& ch = bc::champion_designs[ti];
	const auto s = ch.base_stats();
	const double foc = s.base_focus;
	double spell = 0, area = 0, heal = 0, shield = 0, stun = 0;
	bool reset = false, dash = false;
	for (const auto& a : ch.abilities())
	{
		const auto& inf = a.info();
		if (!inf)
			continue;
		std::visit(
			[&](const auto& v) {
				using T = std::decay_t<decltype(v)>;
				if constexpr (std::is_same_v<T, bc::ability_attack_reset>)
				{
					reset = true;
					stun += v.enhanced_attack ? 1 : 0; // Marcella's enhanced attack stuns
				}
				else if constexpr (std::is_same_v<T, bc::ability_damage>)
					spell += v.modifier * foc;
				else if constexpr (std::is_same_v<T, bc::ability_cc>)
					spell += v.modifier * foc, stun += 1;
				else if constexpr (std::is_same_v<T, bc::ability_aoe_damage>)
					area += v.modifier * foc, stun += v.duration > 0 ? 1 : 0;
				else if constexpr (std::is_same_v<T, bc::ability_heal>)
					heal += v.modifier * foc;
				else if constexpr (std::is_same_v<T, bc::ability_shield>)
					shield += v.modifier * foc;
				else if constexpr (std::is_same_v<T, bc::ability_dash>)
				{
					dash = true;
					if constexpr (requires { v.modifier; v.duration; }) // patch 3.0: Heart of Ruin's landing hit and stun
						area += v.modifier * foc, stun += v.duration > 0 ? 1 : 0;
				}
			},
			*inf);
	}
	const double basic = s.base_strength * (reset ? 1.125 : 1.0);
	f.hp = (s.base_health + shield) / 1000.0;
	f.basic = basic / 50.0;
	f.splash = t == bc::champion_type::varg && bc::constants::passive_abilities::varg_splash_radius > 0 ? basic / 50.0 : 0.0; // strength again on each other target
	f.spell = (spell + heal) / 8.0 / 50.0;
	f.area = area / 8.0 / 50.0;
	f.stun = stun;
	f.dash = dash ? 1.0 : 0.0;
	f.ranged = s.base_attack_range > 1 ? 1.0 : 0.0;
	f.gold = t == bc::champion_type::vesper_vale ? bc::constants::passive_abilities::vesper_vale_bonus_gold_percent / 100.0 : 0.0;
	f.ret = t == bc::champion_type::ren ? bc::constants::passive_abilities::ren_retaliation_focus_ratio * foc / 50.0 : 0.0;
	f.bodies = 1;
	return f;
}

bc::champion_type type_of(D c, int body);

PickF pick_feats_raw(D c)
{
	PickF f = body_feats(type_of(c, 0));
	if (c == D::cassi_and_issac)
	{
		const PickF g = body_feats(type_of(c, 1));
		f.hp += g.hp, f.basic += g.basic, f.splash += g.splash, f.spell += g.spell, f.area += g.area, f.stun += g.stun, f.dash += g.dash,
			f.ranged += g.ranged, f.gold += g.gold, f.ret += g.ret, f.bodies += g.bodies;
	}
	return f;
}

// Designs never change: every pick's features once, in the first draft turn (10x fuel); later turns (100k fuel) only add them up.
PickF pick_feats(D c)
{
	static std::array<PickF, 16> cache{};
	static std::array<bool, 16> ready{};
	const auto i = static_cast<std::size_t>(c);
	if (i >= cache.size())
		return pick_feats_raw(c);
	if (!ready[i])
		cache[i] = pick_feats_raw(c), ready[i] = true;
	return cache[i];
}

double model_value(D c)
{
	const PickF f = pick_feats(c);
	const double g = std::max(1, F.groups);
	double v = P.pd_w_hp * f.hp + P.pd_w_basic * f.basic + P.pd_w_splash * f.splash + P.pd_w_spell * f.spell + P.pd_w_area * f.area +
		P.pd_w_stun * f.stun + P.pd_w_dash * f.dash + P.pd_w_ranged * f.ranged + P.pd_w_gold * f.gold + P.pd_w_ret * f.ret + P.pd_w_bodies * f.bodies;
	// map interactions: area damage on packs, stuns on elks, a gold bonus on gold groups, several bodies on a 3-a-side map, a dash on a
	// spread-out map, range on monolith maps (range 5)
	v += P.pd_w_area_pack * (f.area + f.splash) * F.multi / g + P.pd_w_stun_elk * f.stun * F.elk / g + P.pd_w_gold_gold * f.gold * F.gold / g +
		P.pd_w_bodies_small * f.bodies * (F.team <= 3 ? 1.0 : 0.0) + P.pd_w_dash_dist * f.dash * F.mean_dist / 30.0 +
		P.pd_w_ranged_mono * f.ranged * (F.mono > 0 ? 1.0 : 0.0);
	if (F.mono > 0) // monolith maps (20,000 health, range 5): what holds and what deals damage there
		v += P.pd_w_hp_mono * f.hp + P.pd_w_basic_mono * f.basic + P.pd_w_spell_mono * f.spell + P.pd_w_area_mono * f.area;
	if (P.pd_w_area_close != 0.0f || P.pd_w_stun_close != 0.0f)
	{
		// crowded maps (few tiles per champion: contact all game) pay for area damage and stuns; close = 1 at 50 x 50 with 5 a side
		const double close = std::min(4.0, 2500.0 * F.team / 5.0 / std::max(625.0, static_cast<double>(F.area))) - 1.0;
		v += (P.pd_w_area_close * f.area + P.pd_w_stun_close * f.stun) * close;
	}
	return v;
}

// Objective maps (the caster ring, v8's rule in kit terms): spell damage that reaches 4 (the ring stands outside the camps' reach),
// area spells x 2 targets, relative to the best pick's.
double ring_of_raw(D c);
double ring_of(D c)
{
	static std::array<double, 16> cache{};
	static std::array<bool, 16> ready{};
	const auto i = static_cast<std::size_t>(c);
	if (i >= cache.size())
		return ring_of_raw(c);
	if (!ready[i])
		cache[i] = ring_of_raw(c), ready[i] = true;
	return cache[i];
}

double ring_of_raw(D c)
{
	double r = 0;
	for (int b = 0; b < (c == D::cassi_and_issac ? 2 : 1); ++b)
	{
		const auto ti = static_cast<std::size_t>(type_of(c, b));
		if (ti >= bc::champion_designs.size())
			continue;
		const auto& ch = bc::champion_designs[ti];
		const Kit k = kit_of(ch);
		const double foc = ch.base_stats().base_focus;
		if (k.dmg >= 0 && k.dmg_range >= 4.f)
			r += foc * k.dmg_mod;
		if (k.cc >= 0 && k.cc_range >= 4.f)
			r += foc * k.cc_mod;
		if (k.aoe >= 0 && k.aoe_range >= 4.f)
			r += foc * k.aoe_mod * (k.aoe_radius >= 1.f ? 2.0 : 1.0);
	}
	return r / 8.0;
}

bool area_stun_of(D c)
{
	const PickF f = pick_feats(c);
	return f.area > 0 && f.stun > 0;
}

double prior(D c);

// Relative stat power of each pick on engine 3.0.4 (draft ids 0-11; PSTAT_TRACE build of this code), the anchor of stat_prior().
#define PD_STAT_REF 1.2322, 0.8519, 1.0842, 0.9500, 0.6349, 0.7289, 1.0842, 1.0300, 1.0157, 1.3414, 0.8658, 1.1807

// pd_stat: the measured prior + pd_stat_k x ln(relative power now / relative power on the engine the prior was measured on). The
// priors are log-odds-like values (pd_stat 2: from substitution screens), so a change of power shifts them additively. The anchors are
// the relative powers of engine 3.0.4 (PSTAT_TRACE prints them), the engine of the 3.0.4 priors: there the shift is 0 exactly; a later
// balance patch moves every prior by how much it moved that champion's power against the field (Stellar 3.0.2 -> 3.0.4: -0.26).
double stat_prior(D c)
{
	double v = prior(c);
	if (P.pd_stat && P.pd_stat_k != 0.f)
	{
		static const double REF[12] = { PD_STAT_REF };
		const auto i = static_cast<std::size_t>(c);
		if (i < 12 && REF[i] > 0)
		{
			const double r = rel_power(c) / REF[i];
			if (std::fabs(r - 1.0) > 1e-3) // the anchors are printed to 4 decimals: on their own engine the shift is exactly 0
				v += static_cast<double>(P.pd_stat_k) * std::log(r);
		}
	}
	return v;
}

double prior(D c)
{
	if (P.pd_stat)
		switch (c) // pd_stat: the priors re-measured on engine 3.0.4 (params.h pd_pri_*)
		{
		case D::ren: return P.pd_pri_ren;
		case D::stellar: return P.pd_pri_stellar;
		case D::cassi_and_issac: return P.pd_ci_prior;
		case D::varg: return P.pd_pri_varg;
		case D::ryth: return P.pd_pri_ryth;
		case D::prism: return P.pd_pri_prism;
		case D::tavi: return P.pd_pri_tavi;
		case D::vendetta: return P.pd_pri_vendetta;
		case D::marcella: return P.pd_pri_marcella;
		case D::vesper_vale: return P.pd_pri_vesper;
		case D::willow: return P.pd_pri_willow;
		default: break;
		}
	switch (c)
	{
	case D::ren: return 1.0;
	case D::stellar: return 0.95;
	case D::cassi_and_issac: return P.pd_ci_prior;
	case D::varg: return 0.62;
	case D::ryth: return 0.6;
	case D::prism: return 0.36;
	case D::tavi: return 0.33;
	case D::vendetta: return 0.3;
	case D::marcella: return 0.2;
	case D::vesper_vale: return 0.12;
	case D_HOR: return P.pd_hor_prior; // patch 3.0's new champion: see pd_hor3, pd_counter_hor
	default: return 0.1;
	}
}

double pd_score_model(D c, const std::vector<D>& team, const std::vector<D>& enemy);

double pd_score(D c, const std::vector<D>& team, const std::vector<D>& enemy)
{
	if (P.pd_stat >= 3)
	{
		// mi_pick 2 (GOD v18): the strong teams' pre-patch prior only on monolith and objective maps. Without it the pick order changed on the
		// contest copies (ct2: 17/48, -283, 44 deaths to 8 in one game with the same five champions); with it everywhere the 30 new maps lost.
		// mi_pick 3: also on the maps known_maps.h knows (their prior is that map's own pick rate; on the 30 new maps it is a pre-patch guess
		// from the features): _v18e (prior everywhere) old maps +185, new maps -85; _v18a (none) old +18, new +171.
		const bool prior = P.mi_pick == 1 || (P.mi_pick >= 2 && (F.mono > 0 || MP.objective)) || (P.mi_pick == 3 && mi_known_map());
		return pd_score_model(c, team, enemy) + (prior ? P.mi_prior_w * mi_prior(static_cast<int>(c)) : 0.0);
	}
	double v = stat_prior(c);
	// Map fit.
	if (MP.objective)
	{
		if (c == D::prism || c == D::tavi)
			v += 0.75; // the ring kills the objective's camps from distance 4
		if (c == D::stellar)
			v += 0.1;
		if (c == D::ryth)
			v += 0.4; // the ring's tank and area stun
		if (c == D::ren || c == D::varg)
			v -= 0.6;
	}
	else
	{
		if (MP.open_small)
		{
			if (c == D::ren)
				v -= 0.5; // a farming race without early contact: Ren's retaliation earns nothing
			if (c == D::varg)
				v += 0.45; // splash on the wolf packs
		}
		// Ryth over Varg needs few packs; at team size 4 also elk camps to stun (interlock 0.33, rushbait-v2 0.44): the
		// generated size-4 maps with elk share <= 0.22 lost 16 of 72 proxy games with Ryth (mapscreen _fw _pd)
		const bool ryth_map = MP.pack_share < P.pd_pack && (MP.team != 4 || MP.elk_share >= P.pd_elk);
		if (c == D::varg)
			v += ryth_map ? -0.05 : 0.15;
		if (c == D::ryth && ryth_map)
			v += 0.1;
		if (c == D::ryth && MP.monolith_only)
			v += 0.03;
	}
	// Team synergy.
	int fronts = 0, casters = 0;
	bool pair = false;
	for (auto t : team)
		fronts += is_front(t), casters += is_caster(t), pair |= t == D::cassi_and_issac;
	if (c == D::cassi_and_issac && !pair && P.pd_stat < 2)
		v += 0.3; // every top draft has the pair: two bodies, the Cassi heal (pd_stat 2: inside the measured value)
	// pd_hor3 (patch 3.0): at team size 3, outside the objective / open farming types, Heart of Ruin (1000 health, a stunning dash, a
	// self shield) instead of the nerfed pair: Ren, Heart of Ruin, Stellar won 20-23 of 24 vs legend_m15 / Mite / ifish proxies on the
	// four 3-champion official maps, Ren, Stellar, C&I 19 (fragment 6 vs 4, packs 5-6 vs 4); at sizes 4-5 the pair stays (45-47 vs 40 of 54).
	if (SDK_HAS_HOR && P.pd_hor3 && MP.team == 3 && !MP.objective && !MP.open_small) // no penalty on the pair when the SDK has no HoR
	{
		if (c == D_HOR)
			v += 1.2;
		if (c == D::cassi_and_issac)
			v -= 0.5;
	}
	if ((P.pd_stat ? is_caster(c) : c == D::stellar) && casters == 0 && P.pd_stat < 2)
		v += 0.2; // one ranged carry (pd_stat 1: whichever caster, by its prior; 2: inside the measured value)
	if (is_front(c) && fronts >= MP.team - P.pd_front_free)
		v -= P.pd_front_pen; // at most team - pd_front_free frontliners (the pair and a ranged carry take the rest)
	// Counters to the enemy's visible picks.
	int e_cast = 0, e_dive = 0;
	for (auto e : enemy)
		e_cast += is_caster(e), e_dive += is_front(e);
	if (c == D::ryth)
		v += P.pd_counter * (0.06 * std::max(0, e_cast - 1) + 0.05 * std::max(0, e_dive - 2));
	// Session 14 (patch 3.0): bruiser picks on the enemy side favour Heart of Ruin over the pair; gold-rich halves favour the gold champions.
	int e_bruise = 0;
	for (auto e : enemy)
		e_bruise += e == D_HOR || e == D::marcella || e == D::vendetta;
	if (c == D_HOR && !pair)
		v += P.pd_counter_hor * e_bruise; // Heart of Ruin takes the pair's slot, never a frontliner's (HoR for Varg / Ryth: 19 / 14 of 42)
	if (c == D::cassi_and_issac)
		v -= P.pd_counter_hor * e_bruise;
	if (c == D::vesper_vale || c == D::marcella)
		v += P.pd_gold_vesper * MP.gold_share;
	if (c == D::varg)
		v -= P.pd_counter * 0.04 * std::max(0, e_cast - 1);
	return v;
}

int g_sub_done = 0; // P.pd_sub_from: our pd_sub_to pick stands for pd_sub_from (the draft instance lives through the whole draft)

double counter_model(D c, const std::vector<D>& enemy);

// pd_stat 3: the model's value of c on this map against the enemy's visible picks, plus v8's two map types in kit terms (measured
// rules: the objective ring and open small-team maps).
double pd_score_model(D c, const std::vector<D>& team, const std::vector<D>& enemy)
{
	(void)team; // the model is additive over picks: a pick's value does not depend on ours
	double v = model_value(c);
	if (MP.objective)
	{
		static double rmax = -1;
		if (rmax < 0)
		{
			rmax = 0;
			for (int i = 0; i < (SDK_HAS_HOR ? 12 : 11); ++i)
				rmax = std::max(rmax, ring_of(static_cast<D>(i)));
		}
		v += P.pd_obj_ring * ring_of(c) / std::max(1e-9, rmax); // v8: Prism / Tavi +0.75 (the ring kills the camps from 4)
		if (is_front(c))
			v += area_stun_of(c) ? P.pd_obj_tank : -P.pd_obj_melee; // v8: Ryth +0.4 (tank, area stun), Ren / Varg -0.6
	}
	if (MP.open_small)
	{
		const PickF f = pick_feats(c);
		if (f.ret > 0)
			v -= P.pd_open_ret; // v8: Ren -0.5 (a farming race without contact: retaliation earns nothing)
		if (f.splash > 0)
			v += P.pd_open_splash; // v8: Varg +0.45 (splash on the packs)
	}
	return v + counter_model(c, enemy);
}

// Counters to the enemy's visible picks (pd_stat 3): the enemy team's features (the same model features, summed over its picks)
// against ours: an enemy with melee basic damage favours our range and stuns; an enemy with burst favours our health. Weights
// pd_cw_* (0 = no counter term).
double counter_model(D c, const std::vector<D>& enemy)
{
	if (enemy.empty() || (P.pd_cw_ranged_melee == 0.f && P.pd_cw_stun_melee == 0.f && P.pd_cw_hp_burst == 0.f && P.pd_cw_dash_ranged == 0.f))
		return 0;
	double e_melee = 0, e_burst = 0, e_ranged = 0;
	for (auto e : enemy)
	{
		const PickF g = pick_feats(e);
		e_melee += (g.bodies - g.ranged) > 0 ? g.basic * (g.bodies - g.ranged) / g.bodies : 0.0;
		e_burst += g.spell + g.area;
		e_ranged += g.ranged;
	}
	const PickF f = pick_feats(c);
	return P.pd_cw_ranged_melee * f.ranged * e_melee + P.pd_cw_stun_melee * f.stun * e_melee + P.pd_cw_hp_burst * f.hp * e_burst +
		P.pd_cw_dash_ranged * f.dash * e_ranged;
}

// v28 ladder draft (experiments/v85/draftfit.py): a champion's value on this map from 47k ranked games of other teams, as a linear function of the draft-time features, so it
// carries to maps never seen. On maps left out of the fit a +0.40 roster edge won 7.9% more and -0.40 lost 10.5%; the same values also sort our own Varg swaps by map.
double ladder_value(D c)
{
	namespace L = ladder_draft;
	const double g = std::max(1, F.groups);
	const double m[L::J] = { std::log(g), F.gem / g, F.gold / g, F.multi / g, F.elk / g, F.wolf / g, F.harmless / g, F.mono > 0 ? 1.0 : 0.0, F.mean_dist / 30.0,
		std::log(std::max(1.0, static_cast<double>(F.area))), static_cast<double>(F.holes) / std::max(1.0, static_cast<double>(F.area)), std::log(1.0 + F.altars),
		F.team == 3 ? 1.0 : 0.0, F.team == 4 ? 1.0 : 0.0, F.gem_group_hp / 5000.0 };
	const auto i = static_cast<std::size_t>(c);
	double v = L::g[i];
	for (int j = 0; j < L::J; ++j)
		v += L::b[i][j] * (m[j] - L::mu[j]) / L::sd[j];
	return v;
}

bool param_pick(const std::vector<D>& mine_real)
{
	if (!mp_ready)
		derive_params();
#ifdef PSTAT_TRACE
	if (P.pd_stat >= 3 && mine_real.empty())
		for (int i = 0; i < (SDK_HAS_HOR ? 12 : 11); ++i)
		{
			const PickF f = pick_feats(static_cast<D>(i));
			std::printf("PMODEL %d hp=%.4f basic=%.4f splash=%.4f spell=%.4f area=%.4f stun=%.0f dash=%.0f ranged=%.0f gold=%.3f ret=%.4f bodies=%.0f value=%.4f score=%.4f\n", i,
				f.hp, f.basic, f.splash, f.spell, f.area, f.stun, f.dash, f.ranged, f.gold, f.ret, f.bodies, model_value(static_cast<D>(i)),
				pd_score(static_cast<D>(i), {}, {}));
		}
#endif
	const std::vector<D> enemy = bc::draft::current_draft(team::enemy);
	std::vector<D> mine = mine_real;
	if (P.pd_sub_from >= 0 && g_sub_done)
		for (auto& c : mine)
			if (c == static_cast<D>(P.pd_sub_to))
				c = static_cast<D>(P.pd_sub_from);
	auto emit = [&](D c, const std::vector<D>& plan) {
		if (P.pd_sub_from >= 0 && c == static_cast<D>(P.pd_sub_from) && !g_sub_done &&
			std::find(mine_real.begin(), mine_real.end(), static_cast<D>(P.pd_sub_to)) == mine_real.end() &&
			std::find(plan.begin(), plan.end(), static_cast<D>(P.pd_sub_to)) == plan.end())
			c = static_cast<D>(P.pd_sub_to), g_sub_done = 1;
		note_pick(c);
	};
	static const D order_all[] = { D::ren, D::stellar, D::cassi_and_issac, D::varg, D::ryth, D::tavi, D::prism, D::vendetta, D::marcella,
		D::vesper_vale, D::willow, D_HOR };
	const std::size_t n_order = std::size(order_all) - (SDK_HAS_HOR ? 0 : 1); // Heart of Ruin only when the SDK has it
	static D order_st[12];
	if (P.pd_stat)
	{
		// pd_stat: picks come out by prior (body indices follow it: the lower index wins claim ties), the fixed order breaking ties. With
		// v8's table this is v8's order for every team it drafts.
		std::copy(order_all, order_all + n_order, order_st);
		if (P.pd_stat >= 3)
		{
			double val[16] = {};
			for (std::size_t i = 0; i < n_order; ++i)
				val[static_cast<std::size_t>(order_st[i])] = pd_score(order_st[i], {}, enemy);
			std::stable_sort(order_st, order_st + n_order, [&](D a, D b) { return val[static_cast<std::size_t>(a)] > val[static_cast<std::size_t>(b)]; });
		}
		else
			std::stable_sort(order_st, order_st + n_order, [](D a, D b) { return stat_prior(a) > stat_prior(b); });
	}
	const std::span<const D> order(P.pd_stat ? order_st : order_all, n_order);
	auto has = [](const std::vector<D>& v, D c) { return std::find(v.begin(), v.end(), c) != v.end(); };
	if (P.pd_lad)
	{
		// v28: the roster this draft plans with no enemy picks, then up to pd_lad_swaps swaps to a champion the ladder values more by pd_lad_min. No swap = the usual flow below.
		std::vector<D> base;
		{
			D first = D::ren;
			double bv = -1e9;
			for (auto c : order)
				if (pd_type != 0 || is_front(c))
				{
					const double v = pd_score(c, {}, {});
					if (v > bv)
						bv = v, first = c;
				}
			base.push_back(first);
			for (int k = 1; k < MP.team; ++k)
			{
				D best = D::stellar;
				bv = -1e9;
				for (auto c : order)
				{
					if (has(base, c))
						continue;
					const double v = pd_score(c, base, {});
					if (v > bv)
						bv = v, best = c;
				}
				base.push_back(best);
			}
		}
		std::vector<D> lad = base;
		for (int s = 0; s < P.pd_lad_swaps; ++s)
		{
			double bd = static_cast<double>(P.pd_lad_min);
			int out = -1;
			D in = D::ryth;
			for (int o = 0; o < static_cast<int>(lad.size()); ++o)
			{
				if ((P.pd_lad_keep >> static_cast<int>(lad[static_cast<std::size_t>(o)])) & 1)
					continue;
				for (auto c : order)
				{
					if (has(lad, c) || !((P.pd_lad_mask >> static_cast<int>(c)) & 1))
						continue;
					const double d = ladder_value(c) - ladder_value(lad[static_cast<std::size_t>(o)]);
					if (d >= bd)
						bd = d, out = o, in = c;
				}
			}
			if (out < 0)
				break;
			lad[static_cast<std::size_t>(out)] = in;
		}
		// GOD v29w: on 5-champion maps Willow (ally heal 3 x focus at range 4, attack reset) takes Ryth's slot in the roster and in the pick
		// order. Among the top 30, rosters with Willow beat the standard Ryth, Vesper, Vendetta, Marcella, Heart of Ruin roster 425 of 760 games,
		// +39.5 over rating expectation. Ryth keeps its slot where the draft takes it for its area stun: lone-monolith and objective maps.
		const auto ryth = std::find(lad.begin(), lad.end(), D::ryth);
		if (MP.team == 5 && !MP.monolith_only && !MP.objective && ryth != lad.end() && !has(lad, D::willow))
			*ryth = D::willow;
#ifdef LEGEND_FEATURES
		if (mine_real.empty())
		{
			std::printf("LAD base");
			for (auto c : base)
				std::printf(" %d", static_cast<int>(c));
			std::printf(" lad");
			for (auto c : lad)
				std::printf(" %d", static_cast<int>(c));
			std::putchar(10);
		}
#endif
		if (lad != base)
			for (auto c : lad)
				if (!has(mine_real, c))
				{
					note_pick(c);
					return true;
				}
	}
	if (mine.empty())
	{
		// First pick: the map type alone (pd_stat: on the default type the frontliner with the best prior, Ren in v8's table).
		D first = pd_type == 2 ? D::prism : pd_type == 1 ? D::cassi_and_issac : D::ren;
		if (P.pd_stat >= 3)
		{
			// pd_stat 3: the best pick by the model on this map (on the default type the best frontliner: the lead body)
			double bv = -1e9;
			for (auto c : order)
				if (pd_type != 0 || is_front(c))
				{
					const double v = pd_score(c, {}, enemy);
					if (v > bv)
						bv = v, first = c;
				}
		}
		else if (P.pd_stat && pd_type == 0)
		{
			double bv = -1e9;
			for (auto c : order)
				if (is_front(c))
				{
					const double v = stat_prior(c);
					if (v > bv)
						bv = v, first = c;
				}
		}
		if (P.ci_first && first != D::cassi_and_issac)
		{
			// ci_first: same team, Cassi & Issac picked first (picks are not exclusive: the order only sets body indices). The lower
			// index captures shared rewards and wins claim ties: four of the ten ladder teams of Oct 19 pick C&I first; our C&I
			// earned 70 / 111 gold per 100 rounds to their 118 / 174 (first emblem r499 / r375 vs r400 / r227).
			std::vector<D> team{ first };
			for (int k = 1; k < MP.team; ++k)
			{
				D best = D::stellar;
				double bv = -1e9;
				for (auto c : order)
				{
					if (has(team, c))
						continue;
					const double v = pd_score(c, team, enemy);
					if (v > bv)
						bv = v, best = c;
				}
				team.push_back(best);
			}
			if (has(team, D::cassi_and_issac))
			{
				note_pick(D::cassi_and_issac);
				return true;
			}
		}
		emit(first, {});
		return true;
	}
	// Re-plan the remaining slots greedily, then pick the planned champion that comes first in the fixed order.
	std::vector<D> team = mine, plan;
	const int slots = MP.team - static_cast<int>(mine.size());
	for (int k = 0; k < slots; ++k)
	{
		D best = D::stellar;
		double bv = -1e9;
		for (auto c : order)
		{
			if (has(team, c) || (P.pd_sub_from >= 0 && g_sub_done && c == static_cast<D>(P.pd_sub_to)))
				continue;
			const double v = pd_score(c, team, enemy);
			if (v > bv)
				bv = v, best = c;
		}
		team.push_back(best);
		plan.push_back(best);
	}
	for (auto c : order)
		if (has(plan, c))
		{
#ifdef LEGEND_FEATURES
			std::printf("PD round=%d type=%d pack=%.2f elk=%.2f obj=%d mono=%d open=%d enemy=%d pick=%d\n", static_cast<int>(mine.size()) + 1, pd_type,
				MP.pack_share, MP.elk_share, (int)MP.objective, (int)MP.monolith_only, (int)MP.open_small, static_cast<int>(enemy.size()), static_cast<int>(c));
#endif
			emit(c, plan);
			return true;
		}
	return false;
}
} // namespace

namespace
{
void dm_write()
{
	// P.dm_plan: rebuild the plan's pick lists and anchor ranking each draft turn (the map part once) and submit it; the last write wins.
	static DraftPlan plan;
	static bool built = false;
	if (!built)
	{
		dm_build(plan);
		built = true;
	}
	plan.team = static_cast<int>(bc::draft::team_size());
	plan.ours.clear(), plan.theirs.clear();
	for (const auto c : bc::draft::current_draft(team::ally))
		plan.ours.push_back(static_cast<int>(c));
	if (g_last_pick >= 0 && std::find(plan.ours.begin(), plan.ours.end(), g_last_pick) == plan.ours.end())
		plan.ours.push_back(g_last_pick);
	for (const auto c : bc::draft::current_draft(team::enemy))
		plan.theirs.push_back(static_cast<int>(c));
	// Anchor ranking (F4): Vesper (gold +33%), Marcella (+2 gold per gem tributed), Prism (focus per carried gem), then the most fragile.
	std::vector<std::pair<float, int>> rank;
	for (int k = 0; k < static_cast<int>(plan.ours.size()); ++k)
	{
		const D d = static_cast<D>(plan.ours[static_cast<std::size_t>(k)]);
		const auto ct = static_cast<std::size_t>(dm_type_of(d));
		const float hp = ct < bc::champion_designs.size() ? static_cast<float>(bc::champion_designs[ct].base_stats().base_health) : 1000.f;
		const float pri = d == D::vesper_vale ? 3.f : d == D::marcella ? 2.f : d == D::prism ? 1.f : 0.f;
		rank.push_back({ -pri * 1e5f + hp, k });
	}
	std::sort(rank.begin(), rank.end());
	plan.anchor_slots.clear();
	for (const auto& r : rank)
		plan.anchor_slots.push_back(r.second);
	const auto bytes = dm_encode(plan);
	bc::draft_memory = bytes;
}
} // namespace

void play_draft_pick();

void play_draft()
{
	g_last_pick = -1;
	if (P.mi_dmem)
		try
		{
			mi_draft_begin();
			if (P.mi_pick)
				mi_draft_prepare(); // the pick prior needs mapintel's map work before the first pick
		}
		catch (...)
		{
		}
#ifdef DRAFT_FUEL
	const auto f0 = bc::fuel_remaining();
	play_draft_pick();
	const auto f1 = bc::fuel_remaining();
	debug_block({
		std::printf("DFUEL turn_start=%llu used=%lld pick=%d\n", static_cast<unsigned long long>(f0), static_cast<long long>(f0) - static_cast<long long>(f1), g_last_pick);
		std::fflush(stdout);
	});
#else
	play_draft_pick();
#endif
	if (P.tp_own)
		try
		{
			tpa::draft_write_own(g_last_pick);
		}
		catch (...)
		{
		}
	if (P.dm_plan)
		try
		{
			dm_write();
		}
		catch (...)
		{
		}
	if (P.mi_dmem)
		try
		{
			mi_draft_after_pick(g_last_pick);
		}
		catch (...)
		{
		}
}

void play_draft_pick()
{
	const auto mine = bc::draft::current_draft(team::ally);
	if (P.v23_draft)
	{
		// v23 4.1: the roster by rule (both top teams': Mite 130/130 games, IC 57/70): Vesper Vale first (+33% gold is the snowball),
		// Vendetta, Heart of Ruin; then Tavi + Marcella on 5-champion maps, Cassi & Issac on 4 (Marcella when the map has fewer than 8
		// gem groups); Ryth for Heart of Ruin on lone-monolith maps (area stun on their pack, strength from bonus health).
		try
		{
			if (!F.ready)
				analyse();
		}
		catch (...)
		{
			F.ready = true;
		}
		const int ts = std::clamp(F.team, 3, 5);
		const bool mono_only = F.mono > 0 && F.gem_groups == 0;
		std::vector<D> order{ D::vesper_vale, D::vendetta, mono_only ? D::ryth : D_HOR };
		if (P.v23_draft == 2)
		{
			// 2: the top three's roster (Oct 29, ~400 ranked games each among the top 12): prism best girl / IC: VV, Vendetta, C&I,
			// Marcella, Heart of Ruin; 4 champions: VV, Vendetta, C&I, Heart of Ruin (Mite too); 3: VV, Vendetta, Heart of Ruin.
			// Ad Astra, the one top-5 team with Ryth in its roster, is the weakest of the five.
			order = { D::vesper_vale, D::vendetta, D_HOR };
			if (ts >= 4)
				order.push_back(D::cassi_and_issac);
			if (ts == 5)
				order.push_back(D::marcella);
		}
		else if (ts == 5)
			order.push_back(D::tavi), order.push_back(D::marcella);
		else if (ts == 4)
			order.push_back(2 * F.gem_groups >= 8 ? D::cassi_and_issac : D::marcella);
		for (auto c : order)
			if (std::find(mine.begin(), mine.end(), c) == mine.end())
			{
				note_pick(c);
				return;
			}
	}
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
		std::printf("FEAT team=%d groups=%d gem=%d gold=%d wolf=%d elk=%d mono=%d multi=%d harmless=%d gem_groups=%d mean_dist=%.2f area=%d holes=%d altars=%d"
			" ghp=%.0f gatt=%d gda=%d gde=%d\n",
			F.team, F.groups, F.gem, F.gold, F.wolf, F.elk, F.mono, F.multi, F.harmless, F.gem_groups, F.mean_dist, F.area, F.holes, F.altars,
			F.gem_group_hp, F.gem_group_att, F.gem_group_da, F.gem_group_de);
	}
#endif
	if (P.mapdraft == 6)
	{
		try
		{
			if (param_pick(mine))
				return;
		}
		catch (...)
		{
		}
	}
	if ((P.mapdraft >= 1 && P.mapdraft <= 3) || P.mapdraft == 7)
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
				note_pick(c);
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
	note_pick(pick);
}
