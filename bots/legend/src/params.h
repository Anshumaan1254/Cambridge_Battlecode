// Every tunable weight and threshold lives here so variants can be generated for self-play tuning.
#pragma once

struct Params
{
	// Task valuation
	float gold_value = 0.22f;		 // gem-equivalent value of one gold
	float deny_bonus = 0.55f;		 // extra value for camps on the enemy half (they lose what we take)
	float enemy_half_penalty = 10.f; // rounds-equivalent risk cost for enemy-half camps
	float unknown_discount = 0.75f;	 // value multiplier for groups whose state we have not seen recently
	float hysteresis = 1.15f;		 // keep current task unless a new one beats it by this factor
	float join_bonus = 1.25f;		 // bonus for joining an ally on a camp that needs two bodies
	int max_wait = 18;				 // rounds we are willing to wait for a respawn on arrival

	// Safety
	float retreat_hp = 0.32f;		 // retreat below this health fraction
	float camp_hp_reserve = 0.18f;	 // keep this fraction of max health after a camp fight
	float fight_margin = 1.30f;		 // engage when our kill time beats theirs by this factor
	int threat_memory = 4;			 // rounds an unseen enemy is still assumed nearby

	// Tribute
	int tribute_min = 34;	   // carry at least this many gems before a dedicated altar trip
	int tribute_near = 5;	   // tribute anything when an altar is this close
	int tribute_risky = 10;	   // bank before risky fights when carrying this many
	int endgame_margin = 12;   // extra rounds of slack for the final tribute

	// Shopping
	int shop_gold = 150;	   // go home to shop at this much gold when home is close
	int shop_trip_max = 9;	   // max steps from spawn for a shopping trip

	// Aggression
	float steal_hp_frac = 0.55f; // need this health fraction to farm on the enemy half
	int gank_bag = 25;			 // chase a visible carrier with at least this many gems
};

inline constexpr Params P{};
