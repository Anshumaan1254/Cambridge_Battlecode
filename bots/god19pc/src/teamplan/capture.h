// teamplan/capture.h: who captures a dead group's reward (TEAMPLAN.md 4, U3'). Two rules (Params::capture_mode):
//   1 (default, LEARNED): the body with the highest gold multiplier, then the nearest: what the top teams do (65% of their captures with
//     two or more bodies near, chance 41%; tools/teamplan/capture_check.py on 25 raw replays, 3 rounds before the capture began);
//   0: the risk-matched gain below (gold at the body's multiplier and weight, gems at the chance to bank them, the bag put at risk, the
//     farming lost): 54-58% agreement, so the top teams do not choose this way; kept for tests.
// The reward is split evenly among the allies present when the capture finishes, and more allies do not speed it up, so one body
// captures and the others move on. Every present body runs this on the same inputs (kits, the present allies' bags and items, which
// are in sight, the walks from the reward tile, the shared danger count) and gets the same answer; ties go to the lower slot.
// Python twin: tools/teamplan/capture.py.
#pragma once
#include "kit.h"

namespace teamplan
{
struct CaptureCand
{
	int slot = 0;		  // our body slot (tie-break: lower first)
	int bag = 0;		  // gems it carries now
	int items = 0;		  // items it owns
	int walk_reward = 0;  // rounds to the reward tile (0 when on it)
	int walk_bank = 0;	  // rounds from the reward tile to where it banks (an altar walk, or a recall + the spawn altar)
	double danger = 0;	  // enemies able to reach its bank route (the caller's count; it must be the same for every present body)
	const Kit* kit = nullptr;
};

inline int tribute_turns(int bag) { return bag <= 0 ? 0 : (bag + 9) / 10; }  // max(1, ceil(bag / 10)) of the owner's turn ends
inline double p_bank(double h, double t) { return 1.0 / (1.0 + h * t); }	   // hazard h per round over t rounds, no exp()

// Expected gain in gems of `x` capturing a reward of `gems` and `gold` (gold at the body's own multiplier and weight `w_rel`, its gold
// weight over the candidates' mean). `rate` = gems a body earns per round elsewhere (team rate / team size) and `dps_rel` its camp damage
// over the candidates' mean: the five capture rounds cost it that much farming.
inline double capture_gain(const CaptureCand& x, int gems, int gold, double w_rel, double rate, double dps_rel, const Consts& c, const Params& p)
{
	const Kit& k = *x.kit;
	const double h = p.hazard * k.exposure + p.danger_hazard * x.danger;
	const int t0 = x.walk_bank + tribute_turns(x.bag);
	const int t1 = x.walk_reward + c.capture_time + x.walk_bank + tribute_turns(x.bag + gems);
	const double p0 = p_bank(h, t0), p1 = p_bank(h, t1);
	double v = gems * p1 - x.bag * (p0 - p1);
	v += p.gold_gems * gold * k.gold_mult * w_rel;
	v += p.gold_gems * k.tribute_gold * gems * p1;
	v -= (x.walk_reward + c.capture_time) * rate * dps_rel;
	return v;
}

// Index (into cands) of the body that captures; -1 when n == 0. `team_n` = our team size.
inline int choose_capturer(const CaptureCand* cands, int n, int gems, int gold, int team_n, const Consts& c, const Params& p, double* gains = nullptr)
{
	if (n <= 0)
		return -1;
	double wsum = 0, dsum = 0;
	for (int i = 0; i < n; ++i)
	{
		wsum += gold_weight(*cands[i].kit, cands[i].items, p);
		dsum += cands[i].kit->camp_dps;
	}
	const double wmean = wsum / n, dmean = dsum / n;
	const double rate = p.team_rate / (team_n > 0 ? team_n : 1);
	int best = -1;
	double bv = 0;
	for (int i = 0; i < n; ++i)
	{
		const double wr = wmean > 0 ? gold_weight(*cands[i].kit, cands[i].items, p) / wmean : 1.0;
		const double dr = dmean > 0 ? cands[i].kit->camp_dps / dmean : 1.0;
		const double v = capture_gain(cands[i], gems, gold, wr, rate, dr, c, p);
		if (gains)
			gains[i] = v;
		if (p.capture_mode == 0 && (best < 0 || v > bv || (v == bv && cands[i].slot < cands[best].slot)))
			best = i, bv = v;
	}
	if (p.capture_mode == 0)
		return best;
	best = 0;
	for (int i = 1; i < n; ++i)
	{
		const CaptureCand &x = cands[i], &b = cands[best];
		const double gx = x.kit->gold_mult, gb = b.kit->gold_mult;
		if (gx > gb || (gx == gb && (x.walk_reward < b.walk_reward || (x.walk_reward == b.walk_reward && x.slot < b.slot))))
			best = i;
	}
	return best;
}
} // namespace teamplan
