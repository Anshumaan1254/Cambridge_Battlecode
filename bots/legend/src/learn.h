// In-match online learning. Everything here is deterministic and cheap (a few hundred fuel per turn).
//
// Team level: the inputs (every champion's global alive flag, both teams' banked gems) are identical for all
// of our instances, so every instance holds the same estimates without spending shared memory.
// - Fight posterior: Beta(3,3) prior on "an exchange ends with an enemy death rather than ours", updated by
//   every death on either side. Fights that keep going badly make us more careful and keep us off their half.
// - Race model: banked-gem rates for both teams (exponential moving averages) project who finishes first.
//
// Instance level: each champion calibrates its own camp model against what actually happens.
// - Damage dealt to a camp group and damage taken from it, observed vs predicted while farming alone, as
//   decayed sums with pseudo-counts; the ratios scale the farm model's kill time and incoming damage.
// - The largest one-round damage each enemy has dealt us (its real burst, items included).
#pragma once
#include "common.h"
#include "params.h"

struct Learner
{
	// team level
	int ally_deaths = 0, enemy_deaths = 0;
	std::vector<std::uint8_t> ally_alive, enemy_alive;
	int ours = 0, theirs = 0, last_round = -1;
	float our_rate = 0, their_rate = 0; // banked gems per round, smoothed

	// instance level
	float out_obs = 0, out_pred = 0, in_obs = 0, in_pred = 0;
	std::vector<float> enemy_burst; // per enemy index

	void team_update(int round);
	// P(we win an exchange): 0.5 with no evidence.
	float fight_p() const { return (static_cast<float>(enemy_deaths) + 3.f) / (static_cast<float>(enemy_deaths + ally_deaths) + 6.f); }
#ifndef LG_NO_CALIB
	float k_out() const { return std::clamp((out_obs + 600.f) / (out_pred + 600.f), 0.6f, 1.8f); }
	float k_in() const { return std::clamp((in_obs + 300.f) / (in_pred + 300.f), 0.4f, 1.8f); }
#else
	float k_out() const { return 1.f; }
	float k_in() const { return 1.f; }
#endif
	void sample_out(float obs, float pred);
	void sample_in(float obs, float pred);
	// Rounds each team needs to reach the goal at its current pace (BIG when it is not scoring).
	int eta_ours() const;
	int eta_theirs() const;
};

Learner& learner();
