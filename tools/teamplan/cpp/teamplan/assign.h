// teamplan/assign.h: soft group ownership (TEAMPLAN.md 4, D1). Greedy list scheduling (below); gem-free groups lean to front bodies and
// gem groups to the others (the top teams'
// pattern: gold-only captures are 15-26% of their front bodies' capture gold and 5-7% of their carries', TEAMPLAN.md 3). In game it is a
// score bonus for the owner, never a hard rule (rigid plans break on contact). Variants: the same with one body left out (a body dead).
// Python twin: tools/teamplan/assign.py.
#pragma once
#include <cstdint>

#include "kit.h"

namespace teamplan
{
inline constexpr std::uint8_t kNoOwner = 255;

struct AGroup
{
	double value = 0;	 // gems + gold_gems x gold of its reward
	double hp = 0;		 // total camp health
	int walk = -1;		 // rounds from our spawn (-1 = unreachable)
	std::uint8_t gem_free = 0;
};

// front_norm[b] in [0, 1]: 1 = the team's most front body (from front_order()).
inline void front_norm_of(const Kit* kits, int n, double* out)
{
	std::uint8_t ord[16];
	front_order(kits, n, ord);
	for (int r = 0; r < n; ++r)
		out[ord[r]] = n > 1 ? static_cast<double>(n - 1 - r) / (n - 1) : 0.5;
}

// The group order: value per round of a trip from spawn at the team's mean camp damage (all bodies agree on it).
inline double group_key(const AGroup& g, double dps_mean, const Consts& c)
{
	const double clear = dps_mean > 0 ? g.hp / dps_mean : 1e9;
	return g.value / (g.walk + clear + c.capture_time);
}

// List scheduling (measured: 83% of top-team captures end in a recall, so trips start at spawn): take the groups in group_key order and
// give each to the body that finishes it first, weighted by its preference: (used + walk + clear + capture time) / pref, ties to the lower
// slot. The body's clock then moves to that finish. O(G log G + G n); the first version (best pair over all bodies and groups each step)
// cost 39k fuel for 12 groups in the engine.
// owner[g] = body slot, or kNoOwner when unreachable or when no body in `alive` (bit mask) is left. Up to 16 bodies, any number of groups.
// time_out[b] (optional) = the time the plan gives body b; value_out[b] = the value of its groups.
inline void assign_groups(const AGroup* gs, int G, const Kit* kits, int n, unsigned alive, const Consts& c, const Params& p,
						  std::uint8_t* owner, double* time_out = nullptr, double* value_out = nullptr, int* order_buf = nullptr,
						  double* key_buf = nullptr)
{
	double fn[16], used[16], val[16];
	front_norm_of(kits, n, fn);
	double dsum = 0;
	int na = 0;
	for (int b = 0; b < n; ++b)
	{
		used[b] = 0, val[b] = 0;
		if (alive >> b & 1u)
			dsum += kits[b].camp_dps, ++na;
	}
	for (int g = 0; g < G; ++g)
		owner[g] = kNoOwner;
	if (na > 0)
	{
		const double dmean = dsum / na;
		// insertion sort of the reachable groups by key (descending, ties: lower index). Without buffers (G ints and G doubles) at most
		// 64 groups are planned (the first 64 reachable ones by index).
		int local[64];
		double lkey[64];
		const bool own = order_buf && key_buf;
		int* ord = own ? order_buf : local;
		double* key = own ? key_buf : lkey;
		const int cap = own ? G : (G < 64 ? G : 64);
		int m = 0;
		for (int g = 0; g < G && m < cap; ++g)
		{
			if (gs[g].walk < 0)
				continue;
			const double kg = group_key(gs[g], dmean, c);
			int j = m++;
			while (j > 0 && key[j - 1] < kg)
				ord[j] = ord[j - 1], key[j] = key[j - 1], --j;
			ord[j] = g, key[j] = kg;
		}
		for (int i = 0; i < m; ++i)
		{
			const AGroup& g = gs[ord[i]];
			int bb = -1;
			double bc = 0, bf = 0;
			for (int b = 0; b < n; ++b)
			{
				if (!(alive >> b & 1u))
					continue;
				const Kit& k = kits[b];
				const double pref = g.gem_free ? 1.0 + p.gemfree_front * (fn[b] - 0.5) : 1.0 - p.gemfree_front * (fn[b] - 0.5);
				const double clear = k.camp_dps > 0 ? g.hp / k.camp_dps : 1e9;
				const double fin = used[b] + g.walk + clear + c.capture_time;
				const double cost = fin / pref;
				if (bb < 0 || cost < bc)
					bb = b, bc = cost, bf = fin;
			}
			owner[ord[i]] = static_cast<std::uint8_t>(bb);
			used[bb] = bf;
			val[bb] += g.value;
		}
	}
	for (int b = 0; b < n; ++b)
	{
		if (time_out)
			time_out[b] = used[b];
		if (value_out)
			value_out[b] = val[b];
	}
}
} // namespace teamplan
