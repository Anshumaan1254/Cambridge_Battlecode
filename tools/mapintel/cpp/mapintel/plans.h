// mapintel/plans.h: the compact runtime plans 1-4 (MAPAnalysis.md 5.8) for a map the table does not know. COMPUTED. The C++ twin of
// tools/mapintel/compact.py (its docstring has the model; the same operations in the same order, checked equal by the test bot on the 40
// official maps x 2 teams: tools/mapintel/test_library.py). The offline catalog (maps/catalog, the detailed fight simulation) is the
// reference these approximate; known maps get the catalog's plans from known_maps.h instead.
//
// Usage (draft, after load_view / compute_features of features.h; keep view, F and C alive across draft turns):
//     mapintel::Compact C(view, F);                           // first draft turn: per-group tables (dU, dE, values, kill-order sums)
//     auto P = mapintel::base_plans(C, view, F);              // plans 2-4 (roster-free)
//     C.plan1(picks, P, rank);                                // plan 1, on the turn the roster is complete (picks = champion_draft ids;
//                                                             // rank = groups by model_weights.h first_scores(), from an earlier turn)
// or all at once: mapintel::make_plans(view, F, picks). dmem.h packs a Plans into the draft-memory block that the champions read in
// the game. Fuel (test bot, 40 official maps): see tools/mapintel/README.md.
#pragma once
#include <cambc.h>
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <vector>
#include "features.h"

namespace mapintel
{
inline constexpr int NSLOT = 6, NTGT = 4, NCON = 16, NGRP = 64, NTOP = 12;
inline constexpr int TEST_PICKS[5] = { 8, 4, 3, 0, 9 }; // test roster of test_library.py (Ren, Stellar, Cassi & Issac, Ryth, Varg)

constexpr int feature_index(std::string_view name)
{
	for (int i = 0; i < NF; ++i)
		if (name == FEATURE_NAMES[i])
			return i;
	return -1;
}

// Body type ids of a draft pick (SDK enum order: champion_draft vs champion_type): picks 0-2 are bodies 0-2, pick 3 (Cassi & Issac) is
// bodies 3 and 4, picks 4-11 are bodies 5-12.
inline int pick_bodies(int pick, int out[2])
{
	if (pick < 3)
		return out[0] = pick, 1;
	if (pick == 3)
		return out[0] = 3, out[1] = 4, 2;
	return out[0] = pick + 1, 1;
}

struct Target
{
	int g = -1;
	double arrive = 0.0, end = 0.0;
};

struct Plans
{
	int nbody = 0;
	int body[NSLOT]{};
	int ntgt[NSLOT]{};
	Target tgt[NSLOT][NTGT]{};
	int ngroups = 0;
	std::vector<int> bank, dU, dE;	// per group: bank altar index (row-major altar order, 255 = none); our / their walk to its nearest camp
	int band = 0, ncon = 0;
	std::array<int, 3> con[NCON]{}; // (group, dU, dE)
	int thr[8]{};
	int mode = 0;					// tiebreak: 0 both teams can bank, 1 neither, 2 only the enemy, 3 only us
	bool us_bank = false, them_bank = false;
};

namespace detail
{
// Design values rounded to 3 decimals: the engine's floats (1.4f = 1.39999997...) as the probe prints them for the Python twin.
inline double r3(double x) { return std::nearbyint(x * 1000.0) / 1000.0; }

struct Kit
{
	double hp = 0, str = 0, foc = 0;
	int range = 1;
	bool reset = false;
	double single = 0, area = 0; // sum of mod x focus / cooldown of single-target (damage, cc) and area (aoe, damaging dash) abilities
};

inline Kit kit(int type)
{
	Kit k;
	const auto& c = cambc::champion_designs[static_cast<std::size_t>(type)];
	const auto s = c.base_stats();
	k.hp = r3(s.base_health), k.str = r3(s.base_strength), k.foc = r3(s.base_focus), k.range = s.base_attack_range;
	for (const auto& a : c.abilities())
	{
		const auto& inf = a.info();
		if (!inf)
			continue;
		std::visit(
			[&](const auto& v) {
				using T = std::decay_t<decltype(v)>;
				if constexpr (std::is_same_v<T, cambc::ability_attack_reset>)
					k.reset = true;
				else if constexpr (std::is_same_v<T, cambc::ability_damage> || std::is_same_v<T, cambc::ability_cc>)
				{
					const double m = r3(v.modifier);
					if (m > 0)
						k.single += m * k.foc / v.max_cooldown;
				}
				else if constexpr (std::is_same_v<T, cambc::ability_aoe_damage> || std::is_same_v<T, cambc::ability_dash>)
				{
					const double m = r3(v.modifier);
					if (m > 0)
						k.area += m * k.foc / v.max_cooldown;
				}
			},
			*inf);
	}
	return k;
}

inline std::array<int, 4> box(const Group& g)
{
	std::array<int, 4> b{ 1 << 20, 1 << 20, -1, -1 };
	for (const auto& c : g.camps)
		b[0] = std::min(b[0], c.x), b[1] = std::min(b[1], c.y), b[2] = std::max(b[2], c.x), b[3] = std::max(b[3], c.y);
	return b;
}

inline int box_dist(const std::array<int, 4>& a, const std::array<int, 4>& b)
{
	const int dx = std::max(0, std::max(a[0], b[0]) - std::min(a[2], b[2]));
	const int dy = std::max(0, std::max(a[1], b[1]) - std::min(a[3], b[3]));
	return std::max(dx, dy);
}

// mean over the group's camps of the number of other camps of the group within Chebyshev 1 (compact.adjacency: pairs once, times 2)
inline double adjacency(const Group& g)
{
	int tot = 0;
	const int n = static_cast<int>(g.camps.size());
	const Camp* c = g.camps.data();
	for (int i = 0; i < n; ++i)
		for (int j = i + 1; j < n; ++j)
			if (static_cast<unsigned>(c[i].x - c[j].x + 1) <= 2u && static_cast<unsigned>(c[i].y - c[j].y + 1) <= 2u)
				++tot;
	return static_cast<double>(2 * tot) / n;
}

// Per group, once (compact.group_prep): adjacency, total health and S = sum over the camps in kill order (strength / health descending,
// ties by camp index) of strength x the cumulative health killed up to and including that camp.
struct GroupPrep
{
	double adj = 0, tot = 0, S = 0;
};

inline GroupPrep group_prep(const Group& g)
{
	struct E
	{
		double r;
		int i;
	};
	const int n = static_cast<int>(g.camps.size());
	E buf[64]; // trivial type: not zero-filled (a zero-filled buffer costs ~1.2 fuel per byte)
	std::vector<E> big;
	E* order = buf;
	if (n > 64)
		big.resize(static_cast<std::size_t>(n)), order = big.data();
	for (int i = 0; i < n; ++i)
	{
		const auto& c = g.camps[static_cast<std::size_t>(i)];
		const E e{ static_cast<double>(c.str) / static_cast<double>(c.hp), i };
		int j = i;
		while (j > 0 && order[j - 1].r < e.r)
			order[j] = order[j - 1], --j;
		order[j] = e;
	}
	GroupPrep p;
	p.adj = adjacency(g);
	for (int k = 0; k < n; ++k)
	{
		const auto& c = g.camps[static_cast<std::size_t>(order[k].i)];
		p.tot += c.hp;
		p.S += c.str * p.tot;
	}
	return p;
}

// (kill rounds, damage taken) of one body solo on a group: compact.body_model.
inline std::pair<double, double> body_model(const Kit& k, bool varg, const GroupPrep& p)
{
	const double basic = k.str * (1.0 + (k.reset ? 1.0 / 8.0 : 0.0)) * (1.0 + (varg ? p.adj : 0.0));
	const double dps = basic + k.single + k.area * (1.0 + p.adj);
	return { p.tot / dps, p.S / dps };
}
// compact.assign_dp: the cheapest assignment of n rows (bodies, slot order) to distinct columns of the first m of cost (n, m <= NSLOT);
// a dynamic program over the sets of used columns, masks and columns in increasing order, a strictly cheaper sum wins. out[i] = column
// or -1 (rows beyond m).
inline void assign_dp(const double cost[NSLOT][NSLOT], int n, int m, int out[NSLOT])
{
	const int k = std::min(n, m);
	constexpr double INF = 1e300;
	double dp[1 << NSLOT];
	int par[1 << NSLOT];
	for (int s = 0; s < (1 << m); ++s)
		dp[s] = INF, par[s] = -1;
	dp[0] = 0.0;
	const unsigned full = (1u << m) - 1u;
	for (int mask = 0; mask < (1 << m); ++mask)
	{
		const int i = std::popcount(static_cast<unsigned>(mask));
		if (i >= k || dp[mask] >= INF)
			continue;
		const double base = dp[mask];
		const double* ci = cost[i];
		// the free columns in increasing order (lowest set bit first): compact.assign_dp's j loop
		for (unsigned fr = full & ~static_cast<unsigned>(mask); fr; fr &= fr - 1u)
		{
			const int j = std::countr_zero(fr);
			const int nm = mask | 1 << j;
			const double v = base + ci[j];
			if (v < dp[nm])
				dp[nm] = v, par[nm] = j;
		}
	}
	int best = -1;
	if (k == m)
		best = static_cast<int>(full); // every column used: the one mask with k bits
	else
		for (int mask = 0; mask < (1 << m); ++mask)
			if (std::popcount(static_cast<unsigned>(mask)) == k && dp[mask] < INF && (best < 0 || dp[mask] < dp[best]))
				best = mask;
	if (best >= 0 && dp[best] >= INF)
		best = -1;
	for (int i = 0; i < n; ++i)
		out[i] = -1;
	int mask = best < 0 ? 0 : best, i = k - 1;
	while (mask)
	{
		const int j = par[mask];
		out[i] = j;
		mask ^= 1 << j;
		--i;
	}
}
} // namespace detail

inline constexpr int FI_SPAWN_DIST = feature_index("spawn_dist"), FI_BANK_MODE = feature_index("bank_mode"),
					 FI_BANK_MODE_ENEMY = feature_index("bank_mode_enemy");

// plan 4's thresholds (k_abandon, p percent, d_regroup, r_enemies, bank margin, w_max, 0, 0): the formulas of compact.formula_thresholds()
inline void p4_formula(const Features& F, const MapView& m, int t[8])
{
	const double sd = F.v[FI_SPAWN_DIST];
	const double d = sd > 0 ? sd : static_cast<double>(std::max(m.W, m.H));
	const int f[8] = { std::max(3, static_cast<int>(std::floor(0.12 * d + 0.5))), 80, std::max(5, static_cast<int>(std::floor(0.2 * d + 0.5))), 8, 3, 30, 0, 0 };
	for (int k = 0; k < 8; ++k)
		t[k] = f[k];
}
// the thresholds a bot uses: model_weights.h defines it (the formulas with the LEARNED thresholds of plan4_learn.py written over them,
// MAPINTEL_P4_FITTED); without a fitted model the end of this file defines it as the formulas
inline void p4_thresholds(const Features& F, const MapView& m, int t[8]);

class Compact
{
public:
	Compact(const MapView& m, const Features& F) : m_(m), F_(F)
	{
		G_ = static_cast<int>(m.groups.size());
		const auto G = static_cast<std::size_t>(G_);
		dU.resize(G), dE.resize(G), val.resize(G), bx.resize(G);
		for (std::size_t g = 0; g < G; ++g)
		{
			const auto& grp = m.groups[g];
			dU[g] = dmin(m.fc[0], grp), dE[g] = dmin(m.fc[1], grp);
			val[g] = grp.gems + 0.1 * grp.gold;
			bx[g] = detail::box(grp);
		}
		prep.resize(G);
		for (std::size_t g = 0; g < G; ++g)
			prep[g] = detail::group_prep(m.groups[g]);
		rows_.reserve(13);
		rg_.reserve(G);
		rgi_.assign(std::max<std::size_t>(1, static_cast<std::size_t>(G)), -1);
		for (std::size_t g = 0; g < G; ++g)
			if (dU[g] >= 0)
				rgi_[g] = static_cast<int>(rg_.size()), rg_.push_back({ static_cast<int>(g), dU[g], std::min(dU[g], 6) + 1 + dU[g], 1.0 + prep[g].adj, prep[g].tot, prep[g].S, val[g] });
	}

	std::vector<int> dU, dE;
	std::vector<double> val;
	std::vector<std::array<int, 4>> bx;
	std::vector<detail::GroupPrep> prep;

	// rounds at group g after arriving (compact.work): kill + heal trips + capture
	static double work(const detail::Kit& k, bool varg, const detail::GroupPrep& gp, int d)
	{
		const auto e = detail::body_model(k, varg, gp);
		const double trips = std::max(0.0, std::ceil(e.second / (0.7 * k.hp)) - 1.0);
		const int trip = std::min(d, 6) + 1 + d;
		return e.first + trips * trip + 6.0;
	}

	// Body type's candidate row (compact.row): its NTOP best reached groups by first-target rate, rate descending then group index;
	// with the work at those groups. Cached per type: call row() on the turn a pick is made to spread the cost over the draft.
	struct Row
	{
		int type = -1, n = 0;
		int g[NTOP]{};
		double rate[NTOP]{}, w[NTOP]{};
	};

	const Row& row(int type)
	{
		for (const auto& r : rows_)
			if (r.type == type)
				return r;
		Row R;
		R.type = type;
		const detail::Kit k = detail::kit(type);
		const bool varg = type == static_cast<int>(cambc::champion_type::varg);
		const double basic0 = k.str * (1.0 + (k.reset ? 1.0 / 8.0 : 0.0)), hp7 = 0.7 * k.hp;
		const int nr = static_cast<int>(rg_.size());
		const Rg* q = rg_.data();
		for (int r = 0; r < nr; ++r)
		{
			// compact.work and compact.row: the same operations in the same order
			const Rg& e = q[r];
			const double basic = varg ? basic0 * e.adj1 : basic0 * 1.0;
			const double dps = basic + k.single + k.area * e.adj1;
			const double kill = e.tot / dps, dmg = e.S / dps;
			const double trips = std::max(0.0, std::ceil(dmg / hp7) - 1.0);
			const double w = kill + trips * e.trip + 6.0;
			const double rate = e.val / (std::max(0, e.d - k.range) + w);
			if (R.n == NTOP && !(rate > R.rate[NTOP - 1]))
				continue;
			int j = R.n < NTOP ? R.n++ : NTOP - 1;
			while (j > 0 && R.rate[j - 1] < rate)
				R.g[j] = R.g[j - 1], R.rate[j] = R.rate[j - 1], R.w[j] = R.w[j - 1], --j;
			R.g[j] = e.g, R.rate[j] = rate, R.w[j] = w;
		}
		rows_.push_back(R);
		return rows_.back();
	}

	// the work of a body with kit k (detail::kit: read it once, it reads the engine's designs) at group g (compact.work): the same
	// operations as row()
	double work_at(const detail::Kit& k, int type, int g) const
	{
		const bool varg = type == static_cast<int>(cambc::champion_type::varg);
		const double basic0 = k.str * (1.0 + (k.reset ? 1.0 / 8.0 : 0.0)), hp7 = 0.7 * k.hp;
		if (g < 0 || g >= static_cast<int>(rgi_.size()) || rgi_[static_cast<std::size_t>(g)] < 0)
			return 0.0;
		const Rg& e = rg_[static_cast<std::size_t>(rgi_[static_cast<std::size_t>(g)])];
		const double basic = varg ? basic0 * e.adj1 : basic0 * 1.0;
		const double dps = basic + k.single + k.area * e.adj1;
		const double kill = e.tot / dps, dmg = e.S / dps;
		const double trips = std::max(0.0, std::ceil(dmg / hp7) - 1.0);
		return kill + trips * e.trip + 6.0;
	}

	// plan 1: compact.plan1. First targets: with rank (the groups by first_scores() of model_weights.h, best first, computed on an
	// earlier draft turn: it costs ~61k), the first n reached groups of it assigned to the n bodies by the cheapest total of walk to
	// attack range + work (detail::assign_dp); without rank, the greedy (body, group) pairs by first-target rate. Then 3 more per body
	// from its candidate row, one 2-opt pass.
	void plan1(std::span<const int> picks, Plans& P, std::span<const int> rank = {})
	{
		P.nbody = 0;
		for (const int p : picks)
		{
			int b[2];
			const int n = pick_bodies(p, b);
			for (int k = 0; k < n && P.nbody < NSLOT; ++k)
				P.body[P.nbody++] = b[k];
		}
		const int nb = P.nbody;
		const Row* rw[NSLOT]{};
		int rng[NSLOT]{};
		detail::Kit kt[NSLOT];
		for (int i = 0; i < nb; ++i)
			row(P.body[i]);
		for (int i = 0; i < nb; ++i)
		{
			for (const auto& r : rows_)
				if (r.type == P.body[i])
					rw[i] = &r;
			kt[i] = detail::kit(P.body[i]);
			rng[i] = kt[i].range;
		}
		std::vector<char> used(static_cast<std::size_t>(std::max(1, G_)), 0);
		bool done[NSLOT]{};
		int tg[NSLOT][NTGT]{};	   // plan 1 targets (groups) and their work, per body
		double tw[NSLOT][NTGT]{};
		for (int s = 0; s < NSLOT; ++s)
			P.ntgt[s] = 0;
		if (!rank.empty())
		{
			int top[NSLOT], m = 0;
			for (const int g : rank)
				if (m < nb && g >= 0 && g < G_ && dU[static_cast<std::size_t>(g)] >= 0)
					top[m++] = g;
			double cost[NSLOT][NSLOT];
			for (int i = 0; i < nb; ++i)
				for (int j = 0; j < m; ++j)
					cost[i][j] = std::max(0, dU[static_cast<std::size_t>(top[j])] - rng[i]) + work_at(kt[i], P.body[i], top[j]);
			int as[NSLOT];
			detail::assign_dp(cost, nb, m, as);
			for (int i = 0; i < nb; ++i)
			{
				done[i] = true;
				if (as[i] < 0)
					continue;
				const int g = top[as[i]];
				const int eta = std::max(0, dU[static_cast<std::size_t>(g)] - rng[i]);
				const double w = work_at(kt[i], P.body[i], g);
				P.tgt[i][0] = { g, static_cast<double>(eta), eta + w };
				P.ntgt[i] = 1, tg[i][0] = g, tw[i][0] = w;
				used[static_cast<std::size_t>(g)] = 1;
			}
		}
		while (true)
		{
			double br = 0.0;
			int bi = -1, bj = -1;
			for (int i = 0; i < nb; ++i)
			{
				if (done[i])
					continue;
				const Row& R = *rw[i];
				int j = 0;
				while (j < R.n && used[static_cast<std::size_t>(R.g[j])])
					++j;
				if (j < R.n && (bi < 0 || R.rate[j] > br))
					br = R.rate[j], bi = i, bj = j;
			}
			if (bi < 0)
				break;
			const Row& R = *rw[bi];
			const int g = R.g[bj];
			const int eta = std::max(0, dU[static_cast<std::size_t>(g)] - rng[bi]);
			P.tgt[bi][0] = { g, static_cast<double>(eta), eta + R.w[bj] };
			P.ntgt[bi] = 1, tg[bi][0] = g, tw[bi][0] = R.w[bj];
			used[static_cast<std::size_t>(g)] = 1, done[bi] = true;
		}
		for (int round = 0; round < NTGT - 1; ++round)
			for (int i = 0; i < nb; ++i)
			{
				if (P.ntgt[i] == 0)
					continue;
				const Row& R = *rw[i];
				const Target last = P.tgt[i][P.ntgt[i] - 1];
				const auto& lb = bx[static_cast<std::size_t>(last.g)];
				double br = 0.0;
				int bj = -1, btr = 0;
				for (int j = 0; j < R.n; ++j)
				{
					if (used[static_cast<std::size_t>(R.g[j])])
						continue;
					const int tr = detail::box_dist(lb, bx[static_cast<std::size_t>(R.g[j])]);
					const double v = val[static_cast<std::size_t>(R.g[j])] / (tr + R.w[j]);
					if (bj < 0 || v > br)
						br = v, bj = j, btr = tr;
				}
				if (bj >= 0)
				{
					tg[i][P.ntgt[i]] = R.g[bj], tw[i][P.ntgt[i]] = R.w[bj];
					P.tgt[i][P.ntgt[i]++] = { R.g[bj], last.end + btr, last.end + (btr + R.w[bj]) };
					used[static_cast<std::size_t>(R.g[bj])] = 1;
				}
			}
		for (int i = 0; i < nb; ++i)
			for (int k = 1; k < P.ntgt[i] - 1; ++k)
			{
				const int n = P.ntgt[i];
				int ag[NTGT];
				double aw[NTGT];
				for (int j = 0; j < n; ++j)
					ag[j] = tg[i][j], aw[j] = tw[i][j];
				std::swap(ag[k], ag[k + 1]), std::swap(aw[k], aw[k + 1]);
				Target ta[NTGT];
				double t = 0.0;
				for (int j = 0; j < n; ++j)
				{
					const int g = ag[j];
					const int tr = j == 0 ? std::max(0, dU[static_cast<std::size_t>(g)] - rng[i])
										  : detail::box_dist(bx[static_cast<std::size_t>(ag[j - 1])], bx[static_cast<std::size_t>(g)]);
					const double c = tr + aw[j];
					ta[j] = { g, t + tr, t + c };
					t += c;
				}
				if (ta[n - 1].end < P.tgt[i][n - 1].end)
					for (int j = 0; j < n; ++j)
						P.tgt[i][j] = ta[j], tg[i][j] = ag[j], tw[i][j] = aw[j];
			}
	}

	// plan 2: bank altar per group (compact.bank_altars). The same result as compact's scan of every approach tile (altars in row-major
	// order, tiles in (dy, dx) order, the first tile with the least cost min(walk, 6 + spawn walk) wins), computed in two parts: the
	// recall cost 6 + f does not depend on the group (its least value and first tile once), and the walk's least value and first tile
	// per group, skipping altars that cannot beat the best walk so far (an approach tile is within 1 of its altar). The first tile with
	// the least cost is then the earlier of the two first tiles (or the only one that reaches the minimum).
	std::vector<int> bank_altars() const
	{
		struct Ap
		{
			int x, y, a;
		};
		struct Al
		{
			int x, y, begin, end;
		};
		constexpr int INF = 1 << 29;
		std::vector<Ap> ap;
		std::vector<Al> al;
		ap.reserve(m_.altar_tiles.size() * 8), al.reserve(m_.altar_tiles.size());
		int rbest = INF, rfirst = -1;
		for (int a = 0; a < static_cast<int>(m_.altar_tiles.size()); ++a)
		{
			const auto at = m_.altar_tiles[static_cast<std::size_t>(a)];
			Al A{ at.x, at.y, static_cast<int>(ap.size()), 0 };
			for (int dy = -1; dy <= 1; ++dy)
				for (int dx = -1; dx <= 1; ++dx)
				{
					const int x = at.x + dx, y = at.y + dy;
					if ((dx == 0 && dy == 0) || !m_.in(x, y) || !m_.pass(0, x, y))
						continue;
					const int f = m_.fc[0][m_.at(x, y)];
					if (f >= 0 && 6 + f < rbest)
						rbest = 6 + f, rfirst = static_cast<int>(ap.size());
					ap.push_back({ x, y, a });
				}
			A.end = static_cast<int>(ap.size());
			if (A.end > A.begin)
				al.push_back(A);
		}
		std::vector<int> out;
		out.reserve(static_cast<std::size_t>(G_));
		for (int g = 0; g < G_; ++g)
		{
			// Chebyshev distance from the group's box to a tile: max(b0 - x, x - b2, b1 - y, y - b3, 0)
			const auto& b = bx[static_cast<std::size_t>(g)];
			const int b0 = b[0], b1 = b[1], b2 = b[2], b3 = b[3];
			int wbest = INF, wfirst = -1;
			for (const Al& A : al)
			{
				const int d = std::max(std::max(std::max(b0 - A.x, A.x - b2), std::max(b1 - A.y, A.y - b3)), 0);
				const int lo = d > 0 ? d - 1 : 0;
				if (lo >= wbest)
					continue;
				for (int k = A.begin; k < A.end; ++k)
				{
					const Ap& p = ap[static_cast<std::size_t>(k)];
					const int walk = std::max(std::max(std::max(b0 - p.x, p.x - b2), std::max(b1 - p.y, p.y - b3)), 0);
					if (walk < wbest)
					{
						wbest = walk, wfirst = k;
						if (walk == lo) // no later tile of this altar can be strictly shorter
							break;
					}
				}
			}
			int t = -1;
			if (wfirst >= 0 || rfirst >= 0)
				t = wbest < rbest ? wfirst : rbest < wbest ? rfirst : std::min(wfirst, rfirst);
			out.push_back(t >= 0 ? ap[static_cast<std::size_t>(t)].a : 255);
		}
		return out;
	}

	// plan 3: contested groups (compact.contested)
	void contested(Plans& P) const
	{
		const double sd = F_.v[FI_SPAWN_DIST];
		P.band = std::max(3, static_cast<int>(std::floor(0.1 * (sd > 0 ? sd : static_cast<double>(std::max(m_.W, m_.H))) + 0.5)));
		std::vector<std::pair<double, int>> rows;
		for (int g = 0; g < G_; ++g)
		{
			const int a = dU[static_cast<std::size_t>(g)], b = dE[static_cast<std::size_t>(g)];
			if (a >= 0 && b >= 0 && std::abs(a - b) <= P.band)
				rows.push_back({ val[static_cast<std::size_t>(g)] * std::exp(-static_cast<double>(std::abs(a - b)) / P.band), g });
		}
		std::sort(rows.begin(), rows.end(), [](const auto& x, const auto& y) { return x.first != y.first ? x.first > y.first : x.second < y.second; });
		P.ncon = std::min(NCON, static_cast<int>(rows.size()));
		for (int k = 0; k < P.ncon; ++k)
		{
			const int g = rows[static_cast<std::size_t>(k)].second;
			P.con[k] = { g, dU[static_cast<std::size_t>(g)], dE[static_cast<std::size_t>(g)] };
		}
	}

	// plan 4: the formulas, with the learned thresholds over them when model_weights.h has them (compact.thresholds)
	void thresholds(Plans& P) const
	{
		int t[8];
		p4_thresholds(F_, m_, t);
		for (int k = 0; k < 8; ++k)
			P.thr[k] = t[k];
	}

private:
	int dmin(const Field& f, const Group& g) const
	{
		int best = -1;
		for (const auto& c : g.camps)
		{
			const int v = f[m_.at(c.x, c.y)];
			if (v >= 0 && (best < 0 || v < best))
				best = v;
		}
		return best;
	}

	const MapView& m_;
	const Features& F_;
	int G_ = 0;
	std::vector<Row> rows_; // candidate rows per body type (reserved: plan1 keeps pointers into it)
	struct Rg
	{
		int g, d, trip;
		double adj1, tot, S, val;
	};
	std::vector<Rg> rg_;	// reached groups with their body-independent terms (row())
	std::vector<int> rgi_;	// group -> its entry in rg_ (-1: not reached)
};

// Plans 2-4 and the per-group tables from a Compact (keep the Compact, with its MapView and Features, to add plan 1 on a later turn).
inline Plans base_plans(const Compact& C, const MapView& m, const Features& F)
{
	Plans P;
	P.ngroups = static_cast<int>(m.groups.size());
	P.dU = C.dU, P.dE = C.dE;
	P.bank = C.bank_altars();
	C.contested(P);
	C.thresholds(P);
	P.us_bank = F.v[FI_BANK_MODE] < 2;
	P.them_bank = F.v[FI_BANK_MODE_ENEMY] < 2;
	P.mode = P.us_bank && P.them_bank ? 0 : !P.us_bank && !P.them_bank ? 1 : P.them_bank ? 2 : 3;
	return P;
}

// Plans 2-4 and the per-group tables; plan 1 too when picks is not empty.
inline Plans make_plans(const MapView& m, const Features& F, std::span<const int> picks = {}, std::span<const int> rank = {})
{
	Compact C(m, F);
	Plans P = base_plans(C, m, F);
	if (!picks.empty())
		C.plan1(picks, P, rank);
	return P;
}

// One text line per plan (the test bot prints them; test_library.py compares them with compact.py).
inline std::string describe(const Plans& P)
{
	std::string s;
	char buf[96];
	for (int i = 0; i < P.nbody; ++i)
	{
		std::snprintf(buf, sizeof buf, "MI P1 %d %d", i, P.body[i]);
		s += buf;
		for (int k = 0; k < P.ntgt[i]; ++k)
		{
			std::snprintf(buf, sizeof buf, " %d %.17g %.17g", P.tgt[i][k].g, P.tgt[i][k].arrive, P.tgt[i][k].end);
			s += buf;
		}
		s += "\n";
	}
	s += "MI P2";
	for (const int b : P.bank)
		s += " " + std::to_string(b);
	std::snprintf(buf, sizeof buf, "\nMI P3 %d", P.band);
	s += buf;
	for (int k = 0; k < P.ncon; ++k)
	{
		std::snprintf(buf, sizeof buf, " %d %d %d", P.con[k][0], P.con[k][1], P.con[k][2]);
		s += buf;
	}
	s += "\nMI P4";
	for (const int t : P.thr)
		s += " " + std::to_string(t);
	std::snprintf(buf, sizeof buf, " mode %d", P.mode);
	s += buf;
	return s;
}
} // namespace mapintel

// the learned plan-4 thresholds (model_weights.h defines MAPINTEL_P4_FITTED before it includes this file, so either include order works)
#if __has_include("model_weights.h")
#include "model_weights.h"
#endif
#ifndef MAPINTEL_P4_FITTED
namespace mapintel
{
inline void p4_thresholds(const Features& F, const MapView& m, int t[8])
{
	p4_formula(F, m, t);
}
} // namespace mapintel
#endif
