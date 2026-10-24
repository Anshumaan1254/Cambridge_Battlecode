// mi_draft.cpp: draft memory version 2 inside GOD's draft (mi_draft.h). Order per draft turn, after GOD's pick:
//   turn 1: mapintel's map work (view, fingerprint, features, Compact, plans 2-4, the pick's rows, the table lookup, the opening
//           ranking), stage by stage while the fuel left covers the rest (else no image this game); then the kits, bank order and
//           rally tiles, the M block, TEAM, CODE, NAV (table copy or resumed), OWN, ENEMY, the DL opening and L, each only when its
//           fuel fits (a step that does not fit waits for a later draft turn).
//   later turns: the pick's rows, the waiting steps, OWN, TEAM, CODE, ENEMY, NAV resumed; the last turn first plan 1, M, BODY, CONT
//           and the L routes.
// Every turn ends with one whole-image write. GOD v10 itself writes no draft memory with its default switches (P.dm_plan 0, and its
// comp-path 4 bytes come before this write in the same turn).
#include "mi_draft.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <optional>
#include <span>
#include <vector>

#include "common.h"
#include "params.h"
#include "mapintel/dmem.h"
#include "mapintel/dmem2.h"
#include "mapintel/features.h"
#include "mapintel/fingerprint.h"
#include "mapintel/hazards.h"
#include "mapintel/plans.h"
#if __has_include("mapintel/known_maps.h")
#include "mapintel/known_maps.h"
#define MI_HAS_TABLE 1
#endif
#if __has_include("mapintel/model_weights.h")
#include "mapintel/model_weights.h"
#define MI_HAS_WEIGHTS 1
#endif
#if __has_include("mapintel/dl_weights.h")
#include "mapintel/dl_weights.h"
#endif

namespace mi = mapintel;

namespace
{
long long fuel() { return static_cast<long long>(bc::fuel_remaining()); }
// a step with a measured worst cost c runs when the fuel left exceeds the guard's 1.25 c + 10,000
bool fits(long long c) { return fuel() > c + c / 4 + 10000; }

// Worst costs of the unguarded steps, measured on the 40 official maps (test_dmem2.py / this bot's MI_TRACE build): fuel per tile of
// the map work's stages (big-world, 100 x 100, is the worst map for each), and the fixed steps.
constexpr long long EST_KITS = 36000, EST_BANK = 40000, EST_MAP = 8000, EST_TC = 2000, EST_ROW = 14000, EST_PLAN1 = 45000,
					EST_BODY = 12000, EST_L = 5000, EST_WRITE = 3000;

struct State
{
	std::optional<mi::MapView> V;
	std::optional<mi::Features> F;
	std::optional<mi::Compact> C, CE;
	mi::Plans Pl;
	std::optional<mi::Kits13> K;
	mi::Draft2 D;
	mi::OwnResult own;
	mi::NavWork navw;
	mi::BankBox BB;
	bool began = false, core_a = false, core = false, failed = false, kits = false, bank = false, map_put = false, have_own = false, nav_done = false,
		 plan1 = false, body = false, routes = false, have_dl_open = false, dl_tried = false, prior = false;
	std::uint8_t dl_open[16]{};
	int dl_source = 0;
	std::vector<int> picks;
	int ts = 0, known = -1, kteam = -1, arch = 255, nrank = 0, nbo = 0, nrally = 0, rows_done = 0;
	std::uint64_t fp = 0;
	int rank[16]{}, bank_ord[8]{}, rally[8]{};
	double prior_v[12]{};
};

State& S()
{
	static State s; // static: tens of KB (the wasm shadow stack is small)
	return s;
}

void rows_of(State& s, int pick)
{
	int b[2];
	const int nb = mi::pick_bodies(pick, b);
	for (int j = 0; j < nb; ++j)
		s.C->row(b[j]);
}

int types_of(const State& s, int out[mi::NSLOT]) { return mi::roster_types(s.picks.data(), static_cast<int>(s.picks.size()), out); }

// The map work of turn 1, stage by stage, in two phases: A (the view, fingerprint, features, the table lookup, the archetype and the pick
// prior) and B (the Compact, plans 2-4, the opening ranking). Worst costs per stage, measured on the 40 official maps (this bot's MI_TRACE
// build: view 295k (big-world), fingerprint 71k, features 239k (lanes), plans 256k (big-world), first_scores 96k (road-of-riches, 51
// groups)), x 1.15; features and plans grow with the groups (lanes, 42 groups: 239k / 207k), first_scores ~2k a group. Each stage runs
// only when the fuel left covers it, the M block's write and `reserve` (GOD's own pick when phase A runs before it): a stage that does
// not fit ends the map work for this game (no lost pick, no image).
constexpr long long PICK_RESERVE = 200000; // GOD v10's first draft turn: at most 151,785 (big-world), x 1.3
long long g_ng = 0;
#ifdef MI_TRACE
long long g_tf[6]{};
#define MI_T(k) g_tf[k] = fuel()
#else
#define MI_T(k)
#endif

bool core_need(long long c, long long reserve) { return fuel() > c + EST_MAP + EST_WRITE + 5000 + 15000 + reserve; }

bool run_core_a(State& s, long long reserve)
{
	MI_T(0);
	if (!core_need(340000, reserve))
		return false;
	s.ts = mi::team_size_now();
	s.V.emplace(mi::load_view(s.ts));
	MI_T(1);
	g_ng = static_cast<long long>(s.V->groups.size());
	if (!core_need(82000, reserve))
		return false;
	s.fp = mi::fingerprint(*s.V);
	MI_T(2);
	if (!core_need(std::max<long long>(275000, 6000 * g_ng), reserve))
		return false;
	s.F.emplace(mi::compute_features(*s.V));
	MI_T(3);
#ifdef MI_HAS_TABLE
	s.known = mi::find_known(s.fp);
	if (s.known >= 0)
		s.kteam = mi::known_team(*s.V, mi::KNOWN[s.known]);
#endif
#ifdef MI_HAS_WEIGHTS
	double z[mi::MW_NF];
	mi::zfeat(*s.F, z);
	s.arch = mi::archetype_of(z);
	// the strong teams' pick prior (LEARNED): the map's own rate when known, else predicted from the features
	double rate[12], first[12];
	mi::pick_prior(z, rate, first);
#ifdef MI_HAS_TABLE
	if (s.known >= 0)
		for (int c = 0; c < 12; ++c)
			rate[c] = mi::KNOWN[s.known].pick_strong[c] / 200.0;
#endif
	double m = 0;
	for (int c = 0; c < 12; ++c)
		s.prior_v[c] = std::log(std::max(0.0, rate[c]) + 0.05), m += s.prior_v[c] / 12;
	for (int c = 0; c < 12; ++c)
		s.prior_v[c] -= m;
	s.prior = true;
#endif
	return true;
}

bool run_core_b(State& s)
{
	if (!core_need(std::max<long long>(295000, 5000 * g_ng), 0))
		return false;
	s.C.emplace(*s.V, *s.F);
	s.Pl = mi::base_plans(*s.C, *s.V, *s.F);
	MI_T(4);
#if defined(MI_HAS_WEIGHTS) && defined(MAPINTEL_FIRST_SCORES)
	if (core_need(15000 + 2400 * g_ng, 0))
	{
		const auto sc = mi::first_scores(*s.C, *s.V, *s.F);
		std::vector<int> gs;
		for (int g = 0; g < static_cast<int>(sc.size()); ++g)
			if (sc[static_cast<std::size_t>(g)] > -1e299)
				gs.push_back(g);
		std::sort(gs.begin(), gs.end(), [&](int a, int b) { return sc[static_cast<std::size_t>(a)] != sc[static_cast<std::size_t>(b)] ? sc[static_cast<std::size_t>(a)] > sc[static_cast<std::size_t>(b)] : a < b; });
		for (int k = 0; k < 16 && k < static_cast<int>(gs.size()); ++k)
			s.rank[s.nrank++] = gs[static_cast<std::size_t>(k)];
	}
#endif
	MI_T(5);
#ifdef MI_TRACE
	std::printf("MIT core area=%d groups=%lld start=%lld view=%lld fp=%lld feat=%lld plans=%lld rank=%lld left=%lld\n",
				bc::map::width() * bc::map::height(), g_ng, g_tf[0], g_tf[0] - g_tf[1], g_tf[1] - g_tf[2], g_tf[2] - g_tf[3], g_tf[3] - g_tf[4],
				g_tf[4] - g_tf[5], g_tf[5]);
	std::fflush(stdout);
#endif
	return true;
}
#undef MI_T

void put_team(State& s)
{
	int types[mi::NSLOT];
	const int n = types_of(s, types);
	s.D.img.put(mi::BK_TEAM, mi::build_team(s.Pl, types, n, s.have_own ? &s.own : nullptr, s.K->p.capture_mode));
}

void put_code(State& s) { s.D.img.put(mi::BK_CODE, mi::build_code(s.rally, s.nrally, s.have_own ? &s.own : nullptr, s.bank_ord, s.nbo)); }

void put_map(State& s) { s.D.img.put(mi::BK_MAP, mi::dmem_pack(s.Pl, s.fp, s.ts, s.known >= 0, s.arch)); }

void run_own(State& s)
{
	int types[mi::NSLOT];
	const int n = types_of(s, types);
	s.D.run(mi::BK_OWN, [&] {
		const auto gs = mi::own_groups(*s.C, *s.V, s.K->p);
		s.own = mi::build_own(gs, types, n, *s.K);
		s.have_own = true;
		s.D.img.put(mi::BK_OWN, s.own.b);
	}, mi::OWN_EST);
}

void run_enemy(State& s)
{
	std::vector<int> ep;
	for (const auto d : bc::draft::current_draft(team::enemy))
		ep.push_back(static_cast<int>(d));
	s.D.run(mi::BK_ENEMY, [&] {
		if (!s.CE)
			s.CE.emplace(*s.C, 1), s.BB.build(*s.V, 1); // the enemy side's tables: our Compact mirrored
		s.D.img.put(mi::BK_ENEMY, mi::build_enemy(*s.CE, s.BB, *s.K, ep.data(), static_cast<int>(ep.size())));
	}, s.CE ? mi::ENEMY_EST : mi::ENEMY_EST + mi::CE_EST);
}

// NAV: a known map copies known_maps.h's block; an unknown map resumes the work down to a fuel floor each turn
void run_nav(State& s, long long floor)
{
	if (s.nav_done || !s.bank)
		return;
	mi::NavInput in;
	mi::nav_anchor_groups(*s.C, std::span<const int>(s.rank, static_cast<std::size_t>(s.nrank)), in.anchor_groups);
	for (int k = 0; k < 3; ++k)
		in.altars[k] = k < s.nbo ? s.bank_ord[k] : -1;
#ifdef MI_HAS_TABLE
	if (s.known >= 0)
	{
		s.D.img.put(mi::BK_NAV, mi::nav_from_table(mi::KNOWN[s.known].nav + 64 * s.kteam));
		s.nav_done = true;
		return;
	}
#endif
	in.floor = std::max<long long>(floor, EST_WRITE + 10000);
	if (fuel() <= in.floor + 5000)
		return;
	if (!mi::nav_resume(s.navw, *s.V, *s.C, in))
		return;
	s.D.img.put(mi::BK_NAV, mi::nav_block(s.navw, *s.V, *s.C, in));
	s.nav_done = true;
}

// L: the step-7 opening ranking (turn 1; a known map copies the table, an unknown one computes it when the guard allows) and the
// routes (last turn, known maps: the table)
void dl_opening(State& s)
{
	if (s.dl_tried)
		return;
	s.dl_tried = true;
#if defined(MI_HAS_TABLE) && defined(MAPINTEL_DL_TABLES)
	if (s.known >= 0 && mi::KNOWN[s.known].dl_open)
	{
		std::copy(mi::KNOWN[s.known].dl_open + 16 * s.kteam, mi::KNOWN[s.known].dl_open + 16 * s.kteam + 16, s.dl_open);
		s.have_dl_open = true, s.dl_source = 2;
		return;
	}
#endif
#ifdef MAPINTEL_DL_OPENING
	if (s.known >= 0)
		return;
	s.D.run(mi::BK_DL, [&] {
		const auto I = mi::dl_inputs(*s.C, *s.V, *s.F);
		const auto sc = mi::dl_opening_scores(I);
		std::vector<int> gs;
		for (int g = 0; g < static_cast<int>(sc.size()); ++g)
			if (sc[static_cast<std::size_t>(g)] > -1e299)
				gs.push_back(g);
		std::sort(gs.begin(), gs.end(), [&](int a, int b) { return sc[static_cast<std::size_t>(a)] != sc[static_cast<std::size_t>(b)] ? sc[static_cast<std::size_t>(a)] > sc[static_cast<std::size_t>(b)] : a < b; });
		for (int k = 0; k < 16; ++k)
			s.dl_open[k] = k < static_cast<int>(gs.size()) ? static_cast<std::uint8_t>(gs[static_cast<std::size_t>(k)]) : 255;
		s.have_dl_open = true, s.dl_source = 1;
	}, 160000);
#endif
}

void put_dl(State& s, bool routes)
{
	const std::uint8_t* nx = nullptr;
	int G = 0, split = 0, r0 = 0, r1 = 0;
#if defined(MI_HAS_TABLE) && defined(MAPINTEL_DL_TABLES)
	split = mi::DL_TABLE_SPLIT, r0 = mi::DL_TABLE_ROUNDS[0], r1 = mi::DL_TABLE_ROUNDS[1];
	if (routes && s.known >= 0 && mi::KNOWN[s.known].dl_next)
		G = mi::KNOWN[s.known].ngroups, nx = mi::KNOWN[s.known].dl_next + 2 * (s.kteam * 2 * 13 * G);
#endif
	if (!s.have_dl_open && !nx)
		return;
	int types[mi::NSLOT];
	const int n = types_of(s, types);
	if (nx && s.dl_source == 0)
		s.dl_source = 2;
	s.D.img.put(mi::BK_DL, mi::build_dl(s.have_dl_open ? s.dl_open : nullptr, s.dl_source, nx, G, types, n, s.plan1 ? &s.Pl : nullptr, split, r0, r1));
}

// the waiting steps, in order, while each fits
void catch_up(State& s)
{
	if (!s.kits && fits(EST_KITS + EST_WRITE))
		s.K.emplace(mi::kits13_from_sdk()), s.kits = true;
	if (s.kits && !s.bank && fits(EST_BANK + EST_WRITE))
	{
		s.nbo = mi::bank_order(*s.C, s.Pl, s.bank_ord);
		s.nrally = mi::rally_tiles(*s.C, *s.V, s.Pl, s.bank_ord, s.nbo, s.rally);
		s.bank = true;
	}
	if (!s.map_put && fits(EST_MAP + EST_WRITE))
		put_map(s), s.map_put = true;
	if (s.kits && fits(EST_TC + EST_WRITE))
	{
		put_team(s);
		if (s.bank)
			put_code(s);
	}
}
} // namespace

void mi_draft_begin()
{
	auto& s = S();
	s.D.begin();
	s.began = true;
}

// Phase A of the map work (before GOD's pick with P.mi_pick: its fuel is held back), or both phases (after the pick).
bool core_step(State& s, long long reserve, bool both)
{
	try
	{
		if (!s.core_a)
			s.core_a = run_core_a(s, reserve);
		if (!s.core_a)
			s.failed = true;
		else if (both && !s.core)
		{
			s.core = run_core_b(s);
			s.failed = !s.core;
		}
	}
	catch (...)
	{
		s.failed = true;
	}
	return s.core_a;
}

bool mi_draft_prepare()
{
	auto& s = S();
	if (!s.failed && !s.core_a && s.D.turn <= 1)
		core_step(s, PICK_RESERVE, false);
	return s.prior;
}

double mi_prior(int c)
{
	const auto& s = S();
	return s.prior && c >= 0 && c < 12 ? s.prior_v[c] : 0.0;
}

void mi_draft_after_pick(int pick)
{
	auto& s = S();
	if (!s.began)
		s.D.begin();
	s.began = false;
	if (pick >= 0 && std::find(s.picks.begin(), s.picks.end(), pick) == s.picks.end())
		s.picks.push_back(pick);
	if (s.failed)
		return;
	const int t = s.D.turn;
	if (!s.core)
	{
		if (t != 1)
			return; // the map work runs only on the first draft turn
		core_step(s, 0, true);
		if (!s.core)
			return;
	}
	// the rows of every body picked so far (the turn-1 pick, and each later pick), while they fit
	while (s.rows_done < static_cast<int>(s.picks.size()) && fits(EST_ROW + EST_WRITE))
		rows_of(s, s.picks[static_cast<std::size_t>(s.rows_done++)]);
	const bool last = s.ts > 0 && static_cast<int>(s.picks.size()) >= s.ts;
	catch_up(s);
	if (last && s.kits && s.rows_done == static_cast<int>(s.picks.size()))
	{
		if (!s.plan1 && fits(EST_PLAN1 + EST_MAP + EST_WRITE))
		{
			s.C->plan1(std::span<const int>(s.picks.data(), s.picks.size()), s.Pl, std::span<const int>(s.rank, static_cast<std::size_t>(s.nrank)));
			s.plan1 = true;
			put_map(s), s.map_put = true;
		}
		if (!s.body && fits(EST_BODY + EST_WRITE))
		{
			int types[mi::NSLOT];
			const int n = types_of(s, types);
			int bb, rp;
			mi::econ_body(bb, rp);
			s.D.img.put(mi::BK_BODY, mi::build_body(types, n, *s.K, s.Pl, bb, rp));
			std::vector<int> ep;
			for (const auto d : bc::draft::current_draft(team::enemy))
				ep.push_back(static_cast<int>(d));
			s.D.img.put(mi::BK_CONT, mi::build_cont(*s.K, ep.data(), static_cast<int>(ep.size()), types, n));
			s.body = true;
		}
		if (!s.routes && fits(EST_L + EST_WRITE))
			put_dl(s, true), s.routes = true;
	}
	if (s.kits)
	{
		run_nav(s, t == 1 ? 30000 : 12000);
		run_own(s);
		if (fits(EST_TC + EST_WRITE))
		{
			put_team(s);
			if (s.bank)
				put_code(s);
		}
		run_enemy(s);
		if (!s.dl_tried)
		{
			dl_opening(s);
			if (!last && fits(EST_L + EST_WRITE))
				put_dl(s, false);
		}
	}
	if (fuel() > EST_WRITE)
		s.D.write(last, t == 1);
}
