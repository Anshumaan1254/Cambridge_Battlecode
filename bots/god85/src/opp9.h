// v9 adaptive layer: an opponent model and a team plan (strategy state) on top of the v8 cascade.
//
// Evidence comes from facts every body can read (global banked gems of both teams, global alive flags, the claims in shared
// memory) plus one shared "contact" bit (some body saw an enemy deep in our half this round). Every opp_window rounds the
// leader (body 0) closes a window, updates running indices (EMA) and picks a plan with a small decision tree. Two fast paths
// skip the waiting: a CUSUM change detector on the contact share, and hard evidence (opp_home_deaths of our deaths on our own
// half inside one window). The plan id (3 bits) is broadcast in shared memory; update_mode() applies the plan's preset on top
// of the existing stance / scoreboard / race modifiers. Nothing here acts on its own: it re-tunes thresholds the v8 cascade
// already uses, so every plan can be A/B tested on its own.
#pragma once
#include "common.h"

enum Plan9 : int
{
	PL_FARM = 0,   // default: v8 behaviour
	PL_DEFEND = 1, // they invade our half and win the trades: group up near home, bank small, answer rallies from farther
	PL_PUNISH = 2, // they invade but lose the trades: take the fights, deny their captures
	PL_HUNT = 3,   // they farm quietly and win the race, our trades are even: contest their half, chase their carriers
	PL_RACE = 4,   // they farm quietly and win the race, our trades are lost: avoid fights, gold worth little, farm fast
	PL_EVADE = 5,  // we lose team fights (2+ deaths within 4 rounds) wherever they happen: stay grouped, fight only with numbers
	PL_DENY = 6,   // they are close to 1,000 and finish first: deny tributes (opportunity radius, locks), accept closer fights
	PL_COUNT = 7
};

struct Preset9
{
	float fight_add;	  // added to fight_margin (min 0.9 after the change)
	float fight_back_add; // added to fight_back_margin (min 0.55)
	float half_mult;	  // enemy_half_penalty multiplier
	float deny_add;		  // added to deny_bonus (min 0)
	float iso_add;		  // added to isolated_fight_adv (min 1.0)
	float bank_mult;	  // tribute_min multiplier (min 10 gems)
	float gold_mult;	  // gold_v multiplier
	int stance;			  // forced team stance (-1: keep the bandit's)
	int rally_add;		  // extra tiles from which a RALLY is answered
	int opp_add;		  // extra tiles from which an OPPORTUNITY (enemy tribute / carrier) is answered
	int locks_contested;  // 1: altar locks also go on contested altars without one (use_locks)
};

const Preset9& preset9_of(int plan);
const char* plan9_name(int plan);

struct Opp9
{
	// Running indices (exponential moving averages over closed windows).
	float contact = 0.f;	  // share of rounds with an enemy seen deep in our half
	float contact_mean = 0.f; // slow mean of the per-window contact share (CUSUM reference)
	float cusum = 0.f;		  // upward change detector on the contact share
	int hi_run = 0;			  // consecutive windows with contact >= opp_contact_hi
	float balance = 0.f;	  // their deaths minus ours per window
	float home_deaths = 0.f;  // our deaths on our half per window
	std::array<int, 4> loss_r{ -1000, -1000, -1000, -1000 }; // rounds of our last lost team fights
	std::size_t loss_i = 0;
	int losses_within(int round, int horizon) const;
	float their_rate = 0.f, our_rate = 0.f; // banked gems per round, recent windows
	float their_bag = 0.f;	  // mean size of their bank events (big bags: carriers worth chasing)

	// Current window.
	int win_start = -1, w_rounds = 0, w_contact = 0, w_bank_n = 0, w_bank_gems = 0, w_our_gems = 0;
	int w_ally_d0 = 0, w_enemy_d0 = 0, w_home_d0 = 0, w_home_hard = 0;
	int last_theirs = 0, last_ours = 0, last_round = -1, last_ally_deaths = 0, carried = 0;
	std::array<int, 6> death_r{ -1000, -1000, -1000, -1000, -1000, -1000 };
	std::size_t death_i = 0;
	// Where each ally was last farming (its last claim in shared memory), to place deaths nobody saw.
	std::array<int, 6> last_claim{ -1, -1, -1, -1, -1, -1 };
	std::array<int, 6> last_claim_r{ -1000, -1000, -1000, -1000, -1000, -1000 };
	std::array<int, 6> seen_died{ -1000, -1000, -1000, -1000, -1000, -1000 };

	int plan = PL_FARM, plan_since = 0, windows = 0;
	int divers = 0, casters = 0;
	bool inited = false;

	void init();
	// Leader only, once per round (alive or dead). `contact_now`: the shared contact bit (or our own sighting) this round;
	// `carried_gems`: our bag plus the team's other bags (comms team sum).
	void tick(int round, bool contact_now, int carried_gems);
	int decide(int round) const;

private:
	void close_window(int round);
	void switch_to(int want, bool urgent);
};

Opp9& opp9();
