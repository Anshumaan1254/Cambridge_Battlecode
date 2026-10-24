// teamplan/swap.h: swap two bodies' jobs when one lags (TEAMPLAN.md 4, U4': an expected-value check, not TinyML first).
// Each body measures its own progress q = realized rate / planned rate (its own gold and captures are readable; an ally's are not, so
// the check needs every body's 2-bit code; the live bytes carried them until the team alert took those bits, TEAMPLAN.md 11.7, so a
// bot that wants this check must find another channel for the codes). Assume a body's efficiency q stays with the body: swapping the plans
// of bodies a and b changes the expected total from P_a q_a + P_b q_b to P_a q_b + P_b q_a, a gain of (P_a - P_b)(q_b - q_a). Swap when
// a lags (q_a < lag_ratio), the kits allow it (can_swap), and the gain is at least swap_margin of the current total; then hold for
// swap_hold rounds. A learned correction (the TinyML slot, weights 0 = off) can be added to the gain. Python twin: tools/teamplan/swap.py.
#pragma once
#include <cstdint>

#include "kit.h"

namespace teamplan
{
inline int progress_code(double q) { return q < 0.5 ? 0 : q < 1.0 ? 1 : q < 1.5 ? 2 : 3; }
inline double progress_center(int code) { return 0.25 + 0.5 * code; }

// The TinyML slot: a linear correction on (q_a, q_b, P_a, P_b), all weights 0 by default.
struct SwapModel
{
	double w[5] = { 0, 0, 0, 0, 0 };
};

struct SwapState
{
	int last = -1000000;   // round of the last swap
	int a = -1, b = -1;	   // the bodies swapped (-1: none)
};

// Returns 1 and sets s.a, s.b when a swap is decided this round. `plan_rate[b]` = planned value per round (assign_groups' value / time),
// `code[b]` = the progress codes, `alive` = bit mask.
inline int swap_check(SwapState& s, int round, const double* plan_rate, const std::uint8_t* code, const Kit* kits, int n, unsigned alive,
					  const Params& p, const SwapModel* m = nullptr)
{
	if (round - s.last < p.swap_hold || round % p.swap_period != 0)
		return 0;
	int ba = -1, bb = -1;
	double bg = 0;
	for (int a = 0; a < n; ++a)
	{
		if (!(alive >> a & 1u))
			continue;
		const double qa = progress_center(code[a]);
		if (qa >= p.lag_ratio)
			continue;
		for (int b = 0; b < n; ++b)
		{
			if (b == a || !(alive >> b & 1u) || !can_swap(kits[a], kits[b], 0.25))
				continue;
			const double qb = progress_center(code[b]);
			const double cur = plan_rate[a] * qa + plan_rate[b] * qb;
			double gain = (plan_rate[a] - plan_rate[b]) * (qb - qa);
			if (m)
				gain += m->w[0] * qa + m->w[1] * qb + m->w[2] * plan_rate[a] + m->w[3] * plan_rate[b] + m->w[4];
			if (cur > 0 && gain >= p.swap_margin * cur && (ba < 0 || gain > bg))
				ba = a, bb = b, bg = gain;
		}
	}
	if (ba < 0)
		return 0;
	s.last = round, s.a = ba, s.b = bb;
	return 1;
}

// Apply a swap to an ownership table (assign.h): a's groups go to b and b's to a.
inline void swap_owners(std::uint8_t* owner, int G, int a, int b)
{
	for (int g = 0; g < G; ++g)
		if (owner[g] == a)
			owner[g] = static_cast<std::uint8_t>(b);
		else if (owner[g] == b)
			owner[g] = static_cast<std::uint8_t>(a);
}
} // namespace teamplan
