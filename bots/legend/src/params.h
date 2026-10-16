// Every tunable weight and threshold lives here so variants can be generated for self-play tuning.
#pragma once

struct Params
{
	// Task valuation
	float gold_value = 0.22f;		 // gem-equivalent value of one gold
	float deny_bonus = 0.55f;		 // extra value for camps on the enemy half (they lose what we take)
	int deny_gems_only = 1;			 // apply deny_bonus to the gem part only
	int health_emblem = 1;			 // one Durability Emblem of Health after the first emblem
	float enemy_half_penalty = 10.f; // rounds-equivalent risk cost for enemy-half camps
	float unknown_discount = 0.75f;	 // value multiplier for groups whose state we have not seen recently
	float hysteresis = 1.15f;		 // keep current task unless a new one beats it by this factor
	float join_bonus = 1.25f;		 // bonus for joining an ally on a camp that needs two bodies
	float heavy_hp = 2500.f;		 // groups with this much health (or heavy_dps) may take two bodies
	float heavy_dps = 40.f;
	int max_wait = 18;				 // rounds we are willing to wait for a respawn on arrival
	int max_trips = 5;				 // heal trips we accept to finish one camp group (camps never heal)
	float kite_min_ratio = 0.8f; // kite (range-4 spells only) when spell damage is this share of our full damage
	float kite_max_kill = 40.f;	 // ... and the kill takes at most this many rounds

	// Safety
	float retreat_hp = 0.25f;		 // retreat below this health fraction (or 4 rounds of incoming camp damage)
	float camp_hp_reserve = 0.18f;	 // keep this fraction of max health after a camp fight
	float fight_margin = 1.30f;		 // engage proactively when our kill time beats theirs by this factor
	float fight_back_margin = 0.75f; // when they can already hit us, fight back unless this outmatched
	float cornered_margin = 0.45f;	 // melee chasers we cannot outrun: hit back unless hopeless
	int bag_caution = 40;			 // carrying this many gems, avoid even fights we can escape
	int threat_memory = 4;			 // rounds an unseen enemy is still assumed nearby
	int alert_radius = 0;			 // allies avoid this radius around a reported danger
	int alert_age = 12;				 // rounds a danger report stays valid
	int avoid_detour = 1;			 // when every improving step is in danger, search a detour around it
	int detour_extra = 6;			 // ... accepted if at most this many steps longer
	int danger_cd_slack = 1;		 // an enemy spell with this cooldown left counts as ready
	int danger_walk_cast = 1;		 // non-exclusive spells reach 5 (step + cast)

	// Tribute
	int tribute_min = 34;	   // carry at least this many gems before a dedicated altar trip
	int tribute_near = 5;	   // tribute anything when an altar is this close
	int tribute_risky = 10;	   // bank before risky fights when carrying this many
	int bank_first = 20;	   // enemy around but not in reach yet: bank this many before considering a fight
	int bank_first_dist = 14;  // ... when an altar is this close
	int endgame_margin = 12;   // extra rounds of slack for the final tribute
	int island_bank = 60;	   // inside a teleport island: recall out to bank at this bag
	int endgame_bank_at = 200; // within this many gems of the goal (either team), tribute_min shrinks linearly

	// Shopping
	int shop_gold = 150;	   // go home to shop at this much gold when home is close
	int shop_trip_max = 9;	   // max steps from spawn for a shopping trip
	int recall_shop_gold = 300; // recall home to shop from anywhere with this much gold

	// Team style: 0 = spread farming with claims, 1 = deathball (all follow the lowest-index living ally)
	int style = 0;
	int deathball_until = 0; // archetype knob: play deathball until this round (early rush)

	// Scoreboard-aware play: ahead by `lead` → safer; enemy close to winning and ahead → riskier
	int lead = 150;
	int desperate_at = 650;

	// In-match learning (learn.h)
	float learn_fight = 1.2f; // fight-margin multiplier slope per unit of (0.5 - P(win exchange))
	int race_after = 250;	  // trust the pace model after this round
	float race_ratio = 0.75f; // one team projects to finish this much sooner: change gear

	// Aggression
	float steal_hp_frac = 0.55f; // need this health fraction to farm on the enemy half
	int gank_bag = 25;			 // chase a visible carrier with at least this many gems
};

inline constexpr Params P{};
