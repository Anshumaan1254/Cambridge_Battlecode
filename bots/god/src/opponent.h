// Opponent model (P.opp_model): what strategy the enemy plays, whether it changed, and the counter plan the team follows.
//
// Every om_window rounds the leader (body 0, which also runs while dead) turns the window's signals into evidence for six
// archetypes, smooths it (exponential forgetting), and picks a plan: a margin and a minimum duration stop it from flickering, and a
// two-sided CUSUM on the contact level lets a real change switch at once. The plan id travels in 3 spare shared-memory bits; every
// body applies the plan's preset in Brain::update_mode(). Classification only: the signals are gathered in brain.cpp (om_tick).
//
// Plan ids 0-2 are the stance learner's stances, written exactly as the 2 stance bits of v8 (bit 7 of bytes 0-1, byte 2's bit 7 = 0):
// while no archetype is detected the shared bytes are the same as without the model. FARMER maps to PUSH (2): against a team that
// stays home, take their camps and fights (the existing PUSH stance). The five hostile archetypes get plans 3-7.
#pragma once
#include "common.h"

enum Archetype : int
{
	ARC_NONE = 0,
	ARC_FARMER,	   // stays on its half and farms: little contact
	ARC_INVADER,   // walks into our half and picks off farmers
	ARC_DEATHBALL, // moves as one pack (3+ bodies together)
	ARC_OBJECTIVE, // takes the heavy objective (big lumps banked at once)
	ARC_ALTAR,	   // denies our altars (locks, wards and bodies at them, our tributes broken)
	ARC_AMBUSH,	   // hits from bushes / unseen positions
	ARC_COUNT
};

enum PlanId : int
{
	PLAN_SPREAD = 0,
	PLAN_GROUPED = 1,
	PLAN_PUSH = 2,
	PLAN_INVADER = 3,
	PLAN_DEATHBALL = 4,
	PLAN_OBJECTIVE = 5,
	PLAN_ALTAR = 6,
	PLAN_AMBUSH = 7
};

// The counter plan's preset: stance plus adjustments on top of it (Brain::update_mode). Directions only; each archetype's magnitude is
// a switch in params.h (om_k_*), so the size of every adjustment is fitted by games, not chosen here.
struct Preset
{
	int stance;	  // STANCE_* the team plays under this plan
	float dfm;	  // fight_margin += k x dfm
	float ehp;	  // enemy_half_penalty *= ehp^k
	float ddeny;  // deny_bonus += k x ddeny
	float trib;	  // tribute_min *= trib^k (smaller bags under pressure)
	float diso;	  // isolated_fight_adv += k x diso
	float esc;	  // escort_bag *= esc^k (escorted banking from smaller bags)
	float grp;	  // group_radius *= grp^k (GROUPED: stay closer)
	int ward_bush; // bush-first warding while this plan is active (F3)
	int guard;	   // altar-guard role (F6)
	int hunter;	   // carrier-hunter role (F6)
};
const Preset& preset_of(int plan);

// Signals of one window, collected by the leader.
struct OmWindow
{
	int rounds = 0, alive_rounds = 0;
	int inv = 0;					 // invasion counter: bodies that saw an enemy on our half (shared memory)
	int ally_deaths = 0, enemy_deaths = 0, multi_deaths = 0, ally_deaths_home = 0;
	int pack = 0;					 // largest enemy group the leader saw (enemies within 4 of one of them, itself included)
	int bank_events = 0, bank_gems = 0, bank_lump = 0; // enemy banking (global submitted gems)
	int ward_home = 0, ward_altar = 0, ward_bush = 0; // distinct enemy wards seen on our half / within 6 of our altars / in a bush
	int locks = 0, cancels = 0, altar_presence = 0;	  // our altars locked, our tributes cancelled, enemy-rounds next to our altars
	int bush_hits = 0, unseen_hits = 0;				  // health lost with no visible attacker in reach (a bush within 4: bush hit)
	int heavy_lost = 0;								  // heavy groups we saw taken while none of us claimed them
};

struct OppModel
{
	std::array<float, ARC_COUNT> score{}; // smoothed evidence
	std::array<float, ARC_COUNT> ev{};	  // the last window's evidence
	std::array<float, ARC_COUNT> prior{}; // from the enemy draft (P.om_prior)
	int arc = ARC_NONE;					  // current archetype
	int arc_since = 0;					  // window index the current archetype started
	int windows = 0;					  // windows classified so far
	float contact = 0, cus_mu = 0, cus_pos = 0, cus_neg = 0;
	bool fired = false; // the change detector fired on the last window
	int switches = 0;
	OmWindow cur;
	int win_id = -1;

	void set_prior(const std::vector<bc::champion_type>& enemy);
	void end_window(int bodies, int round);
	int plan_id(int learner_stance) const;
};

OppModel& opp_model();
const char* arc_name(int a);
