// teamplan: team-play modules for a CAMBC bot (TEAMPLAN.md section 9). Header-only, no SDK dependency (sdk_bridge.h reads the engine).
// One versioned parameter set. Every value is labelled:
//   COMPUTED: from the engine or the rules;  LEARNED: fitted to current-patch top-team games (source named);
//   ASSUMED: a starting value for the batteries (TEAMPLAN.md section 11 has what they showed).
// tools/teamplan/params.py is the Python twin; tools/teamplan/test_teamplan.py checks that the two sets are equal.
#pragma once
#include <cstdint>

namespace teamplan
{
inline constexpr int kParamsVersion = 1;

struct Params
{
	// ---- kit.h
	double enhanced_extra = 1.0;  // ASSUMED: an enhanced attack reset counts as one more basic attack per cooldown (its stun is in `stun`)
	double enhanced_stun = 1.0;	  // COMPUTED (rules): "the next enhanced attack stuns for one round" (the SDK payload has no duration)
	double missing_hp_avg = 0.5;  // ASSUMED: mean missing health in a fight, for the missing-health damage passive
	double hits_taken = 1.0;	  // ASSUMED: hits taken per fight round (retaliation passive)
	double splash_targets = 1.0;  // ASSUMED: extra bodies a splash basic attack hits
	double area_targets = 1.0;	  // ASSUMED: extra bodies an area spell hits
	double fight_rounds = 8.0;	  // ASSUMED: length of a fight in rounds (one 8-round cooldown), for shields and heals
	double ranged_front = 0.5;	  // ASSUMED: weight of a ranged body as a front body
	double immune_ehp = 0.15;	  // ASSUMED: effective-health bonus of stun immunity
	double dash_escape = 0.2;	  // ASSUMED: exposure cut from a dash (escape)
	double reach_escape = 0.05;	  // ASSUMED: exposure cut per tile of attack range above 1
	// ---- capture.h, bag.h, focus.h, tiebreak.h: economy
	double gold_gems = 0.02;	 // LEARNED: gem value of one gold in the top teams' next-group choices (mapintel econ_learn.py gold_w; GOD v10 uses 0.33)
	double team_rate = 0.94;	 // LEARNED: a top team's gems per round (1,000 gems at the median final round 1,064; tools/teamplan/ladder_roles.py)
	double hazard = 0.0016;		 // LEARNED: deaths per body-round in top-team games (1.4-1.9 per 1,000 for the common picks; roles_ladder.md)
	double danger_hazard = 0.02; // ASSUMED: extra deaths per round per enemy in reach of the bank route (the caller's danger count)
	double items_half = 0.0;	 // owned items at which one more gold is worth half as much (0 = off). ASSUMED 12 first; the top teams' capture
								 // choices contradict it (tools/teamplan/capture_check.py: 42% agreement with it, 54% without), so off
	int capture_mode = 1;		 // capture.h: 1 = the top teams' pattern, the highest gold multiplier, then the nearest (LEARNED: 65% of their
								 // captures with 2+ bodies near, chance 41%); 0 = the risk-matched gain (54-58%: not what they do)
	// ---- bag.h
	int bag_fight = 30;			  // ASSUMED: bag (gems) above which a body banks before a fight it can avoid
	double bag_fight_scale = 60.0;// ASSUMED: the fight bar rises by bag / this (a full bag makes the body choosier)
	double hunt_bag = 25.0;		  // ASSUMED: visible enemy bag (gems) worth hunting with local numbers
	double hunt_bonus = 0.5;	  // ASSUMED: target-score bonus per hunt_bag gems of enemy bag
	// ---- focus.h
	double kv_ref = 40.0;		  // ASSUMED: kill value (gems) that doubles a target's priority
	// ---- tiebreak.h
	int tb_period = 25;			  // ASSUMED: rounds between score samples
	int tb_enter = 150;			  // ASSUMED: both projected finishes beyond max_rounds + this enters tiebreak mode
	int tb_leave = 50;			  // ASSUMED: either projected finish before max_rounds + this leaves it (hysteresis)
	int tb_min_round = 600;		  // ASSUMED: no tiebreak call before this round (rates are noisy early)
	int tb_defer_cap = 60;		  // ASSUMED: largest bag held back in tiebreak mode
	int tb_safe_dist = 9;		  // ASSUMED: no enemy seen within this many tiles while a bag is held back
	int tb_final_margin = 30;	  // ASSUMED: rounds of slack in the final tribute window
	int tb_denial_rounds = 60;	  // ASSUMED: the last rounds in which enemy tributes are denied
	// ---- assign.h
	double own_bonus = 0.25;	  // ASSUMED: score bonus of a body's own groups (soft ownership)
	double gemfree_front = 0.5;	  // ASSUMED: preference of gem-free groups for front bodies (0 = none)
	// ---- swap.h
	int swap_period = 50;		  // ASSUMED: rounds between swap checks
	int swap_hold = 150;		  // ASSUMED: no second swap within this many rounds
	double swap_margin = 0.25;	  // ASSUMED: relative gain a swap must show
	double lag_ratio = 0.6;		  // ASSUMED: a body below this share of its planned rate is lagging
};
} // namespace teamplan
