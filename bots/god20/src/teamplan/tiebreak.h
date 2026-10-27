// teamplan/tiebreak.h: tiebreak mode (TEAMPLAN.md 5; the user: "whenever you sense a tiebreaker then only we will submit the gems at
// last, else we will also be racing for finishing"). At round max_rounds the tributed gems decide, then gold earned, then kills. Both
// teams' tributed totals are readable (cambc::global_submitted_gems), so each body can run this on the same inputs.
//   1. Detect: both projected finishes (the last ~200 rounds' banking rate; ours counts the team's carried bags) lie beyond the round
//      limit by tb_enter; leave when either comes within tb_leave (hysteresis). A map flagged tiebreak-prone by the draft (pace or gem
//      supply) may enter from half of tb_min_round.
//   2. In the mode, a bag may grow up to tb_defer_cap while no enemy is within tb_safe_dist; else it is banked as usual (the risk cap).
//   3. The final tribute window: start for the altar when round + walk + tribute turns + tb_final_margin reaches the limit.
//   4. The last tb_denial_rounds: deny enemy tributes (stuns, locks) and hunt bags.
// Outside the mode the bot races: bank_now_wins() (bag.h) whenever the team's bags win. Python twin: tools/teamplan/tiebreak.py.
#pragma once
#include "capture.h"

namespace teamplan
{
inline constexpr int kTbRing = 9;  // samples kept: rate over the last (kTbRing - 1) x tb_period rounds

struct TbState
{
	int mode = 0;
	int n = 0;					 // samples stored
	int last_round = -1000000;	 // round of the last sample
	int ours[kTbRing] = {}, theirs[kTbRing] = {}, rnd[kTbRing] = {};
	int proj_ours = 0, proj_theirs = 0;	 // last projected finishing rounds (diagnostics)
};

// Projected round at which `banked` (+ `carried`) reaches the win at `rate` gems per round; 2 x limit when the rate is 0.
inline int tb_project(int round, int banked, int carried, double rate, const Consts& c)
{
	const int need = c.winning_gems - banked - carried;
	if (need <= 0)
		return round;
	if (rate <= 0)
		return 2 * c.max_rounds;
	const double r = round + need / rate;
	return r > 2.0 * c.max_rounds ? 2 * c.max_rounds : static_cast<int>(r);
}

// Feed the state every round (it samples every tb_period rounds); returns the mode (1 = tiebreak).
inline int tb_update(TbState& s, int round, int our_banked, int their_banked, int our_carried, int prone, const Consts& c, const Params& p)
{
	if (round - s.last_round < p.tb_period)
		return s.mode;
	s.last_round = round;
	if (s.n == kTbRing)
	{
		for (int i = 1; i < kTbRing; ++i)
			s.ours[i - 1] = s.ours[i], s.theirs[i - 1] = s.theirs[i], s.rnd[i - 1] = s.rnd[i];
		s.n = kTbRing - 1;
	}
	s.ours[s.n] = our_banked, s.theirs[s.n] = their_banked, s.rnd[s.n] = round;
	++s.n;
	if (s.n < 3)
		return s.mode;
	const int dt = s.rnd[s.n - 1] - s.rnd[0];
	const double ro = static_cast<double>(s.ours[s.n - 1] - s.ours[0]) / dt;
	const double rt = static_cast<double>(s.theirs[s.n - 1] - s.theirs[0]) / dt;
	s.proj_ours = tb_project(round, our_banked, our_carried, ro, c);
	s.proj_theirs = tb_project(round, their_banked, 0, rt, c);
	const int min_round = prone ? p.tb_min_round / 2 : p.tb_min_round;
	if (!s.mode)
	{
		if (round >= min_round && s.proj_ours > c.max_rounds + p.tb_enter && s.proj_theirs > c.max_rounds + p.tb_enter)
			s.mode = 1;
	}
	else if (s.proj_ours < c.max_rounds + p.tb_leave || s.proj_theirs < c.max_rounds + p.tb_leave)
		s.mode = 0;
	return s.mode;
}

// In tiebreak mode, may this body keep its bag (now `bag`) instead of banking it? `enemy_dist`: nearest enemy seen recently (a large
// number when none).
inline bool tb_defer(int mode, int bag, int enemy_dist, const Params& p) { return mode && bag <= p.tb_defer_cap && enemy_dist > p.tb_safe_dist; }

// Time to start the final tribute (walk `walk_bank` rounds to the altar, then the tribute turns of `bag`).
inline bool tb_final(int round, int walk_bank, int bag, const Consts& c, const Params& p)
{
	return bag > 0 && round + walk_bank + tribute_turns(bag) + p.tb_final_margin >= c.max_rounds;
}

// The last rounds: deny enemy tributes.
inline bool tb_denial(int round, const Consts& c, const Params& p) { return round >= c.max_rounds - p.tb_denial_rounds; }
} // namespace teamplan
