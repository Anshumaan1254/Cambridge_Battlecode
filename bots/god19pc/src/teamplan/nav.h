// teamplan/nav.h: navigation guards (TEAMPLAN.md 6, the user's BugBFS excerpt mapped to CAMBC). The host gives exact distance fields
// (measured: a radius-3 field over walls + unit tiles costs 1.2k + 0.4-3.5k fuel, cheaper than an unrolled 7x7 BFS in wasm, 10.8k), so
// the global path is the host's; what is left is dynamic and lives here, SDK-free:
//   Progress  : the field distance to the target has not dropped for k turns -> stuck (then: a local field over walls + units, a
//               sidestep, or yield by priority; the caller chooses).
//   LoopGuard : the last 8 tiles; stepping onto one of them again is an oscillation.
//   keep_target: XSquare's target hysteresis: switch only when the new target is nearer than the best distance reached so far.
// nav_sdk.h has the local detour on host fields. Python twin: tools/teamplan/nav.py.
#pragma once

namespace teamplan
{
struct Progress
{
	int target = -1, best = 1 << 30, since = 0;
};

// True when no progress toward `target` for `k` rounds (a new target resets the clock).
inline bool progress_stuck(Progress& s, int target, int dist, int round, int k)
{
	if (target != s.target)
	{
		s.target = target, s.best = dist, s.since = round;
		return false;
	}
	if (dist < s.best)
	{
		s.best = dist, s.since = round;
		return false;
	}
	return round - s.since >= k;
}

struct LoopGuard
{
	int n = 0, head = 0;
	int tile[8] = {};
};
inline void loop_push(LoopGuard& g, int t)
{
	g.tile[g.head] = t;
	g.head = (g.head + 1) & 7;
	if (g.n < 8)
		++g.n;
}
inline bool loop_seen(const LoopGuard& g, int t)
{
	for (int i = 0; i < g.n; ++i)
		if (g.tile[i] == t)
			return true;
	return false;
}

// Switch from the current target (best distance reached so far `best_dist`) to a new one at `new_dist` only if it is nearer.
inline bool keep_target(int best_dist, int new_dist) { return new_dist >= best_dist; }
} // namespace teamplan
