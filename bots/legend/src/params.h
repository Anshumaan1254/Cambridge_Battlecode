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
	int max_trips = 5;				 // heal trips we accept to finish one camp group (camps never heal)
	float join_min_rounds = 14.f;	 // join an ally's group when it alone needs more rounds than this
	int max_join = 1;				 // extra bodies allowed on one (non-monolith) group
	float join_share = 0.6f;		 // value credited to a joining body (the claimer captures)
	int pair_plans = 0;				 // claim packs too heavy for one body and wait for a partner (off: costs pace)
	float pair_wait = 8.f;			 // rounds added to a pair plan for the partner to arrive
	int pair_wait_max = 18;			 // give up waiting for a partner after this many rounds
	float target_threat_adv = 1.1f;	 // skip camps where recently seen enemies beat us (and allies there)

	// Safety
	float retreat_hp = 0.25f;		 // retreat below this health fraction (or 4 rounds of incoming camp damage)
	float camp_hp_reserve = 0.18f;	 // keep this fraction of max health after a camp fight
	float fight_margin = 1.30f;		 // engage proactively when our kill time beats theirs by this factor
	float fight_back_margin = 0.75f; // when they can already hit us, fight back unless this outmatched
	float cornered_margin = 0.45f;	 // chasers we cannot outrun: hit back unless the advantage is below this
	float far_enemy_weight = 1.0f;	 // visible enemies beyond reach+2 count this much in the fight estimate
	int ally_spell_dps = 1;			 // count allies' spells in our damage (else basic attacks only)
	int spawn_heal_bonus = 1;		 // on our spawn, count one more health bar (we heal fully)
	int bag_caution = 40;			 // carrying this many gems, avoid even fights we can escape
	int backup_radius = 8;			 // allies (seen, or claiming a camp) this close count as backup
	float isolated_fight_adv = 1.6f; // alone, start a fight only at this advantage (or a sure kill)
	float isolated_flee_adv = 1.1f;	 // alone and weaker than this: walk away as soon as they are in sight
	int flee_dist = 7;				 // ... when the nearest enemy is this close
	float reserve_margin = 0.5f;	 // half the team dead: extra advantage needed to fight
	int deficit_defend = 1;			 // this many more enemies alive than allies: defensive play
	int deficit_escort = 2;			 // ... this many: a respawned champion waits on spawn for the next ally
	int escort_wait = 15;			 // max rounds to wait on spawn for an escort
	int threat_memory = 4;			 // rounds an unseen enemy is still assumed nearby
	int alert_radius = 0;			 // allies avoid this radius around a reported danger
	int alert_age = 12;				 // rounds a danger report stays valid

	// Tribute
	int tribute_min = 34;	   // carry at least this many gems before a dedicated altar trip
	int early_round = 150;	   // before this round ...
	int early_tribute_min = 22; // ... bank from this bag size (first gold and safety sooner)
	int tribute_near = 5;	   // tribute anything when an altar is this close
	int tribute_risky = 10;	   // bank before risky fights when carrying this many
	int unsafe_altar_penalty = 14; // extra steps for a contested altar where enemies were just seen
	int altar_enemy_memory = 8;    // rounds an enemy sighting near an altar keeps it unsafe
	int endgame_margin = 12;   // extra rounds of slack for the final tribute
	int endgame_alarm = 800;   // their score from which stopping their tributes overrides everything

	int build_style = 1;	   // 0 = old farm builds, 1 = health/durability/treasure builds (ladder-proven)

	// Shopping and home trips (heal + shop + bank near spawn; recall makes them cheap)
	int shop_gold = 150;	   // go home to shop at this much gold when home is close
	int shop_trip_max = 9;	   // max steps from spawn for a walking shopping trip
	int shop_shards = 4;	   // recall home to shop once this many shards are affordable
	int shop_cost_max = 6;	   // max rounds to reach spawn for a shopping trip (recall = 5)
	float home_hp = 0.45f;	   // below this health fraction a trip home is welcome (heal + shop)
	int recall_min_dist = 5;   // recall instead of walking when spawn is farther than this
	int cap_recall_min_home = 8;  // recall while capturing when spawn is farther than this ...
	float cap_recall_hp = 0.75f;  // ... and health is below this fraction,
	int cap_recall_gold = 90;     // ... or gold after the capture reaches this (shopping),
								  // ... or the bag after the capture reaches tribute_min
	int hold_spells_near_enemies = 1; // no spells on camps while enemies are near (keep burst for them)

	int hops_enabled = 1;	   // crystal shortcuts over hole mazes
	int hop_min_save = 15;	   // use a teleport-crystal shortcut when it saves this many rounds

	// Team style: 0 = spread farming with claims, 1 = deathball (all follow the lowest-index living ally)
	int style = 0;
	int deathball_until = 0; // archetype knob: play deathball until this round (early rush)

	// Scoreboard-aware play: ahead by `lead` → safer; enemy close to winning and ahead → riskier
	int lead = 150;
	int desperate_at = 650;

	// In-match learning (learn.h): team stance bandit, pain map, fight calibration
	int learn_enabled = 1;			 // 0 disables all three online learners (A/B testing)
	int learn_stance = 1;			 // team stance bandit on/off
	int learn_pain = 1;				 // pain map on/off
	int learn_fight = 1;			 // fight calibration on/off
	int learn_window = 40;			 // rounds per stance evaluation window
	float learn_rate = 0.5f;		 // step size of the stance value update
	float kill_gems = 25.f;			 // stance reward per enemy death, in gems (bag + 60 rounds of their farming)
	float death_gems = 45.f;		 // stance punishment per ally death, in gems (heavier: we also pay them 50 gold)
	float reward_scale = 40.f;		 // gems per window that count as reward 1
	float ucb_c = 0.3f;				 // exploration bonus (UCB1) for rarely played stances
	float prior_pull = 0.1f;		 // per window, unplayed stance values drift back to their priors
	float q0_spread = 0.3f;			 // optimistic prior values per stance (SPREAD starts preferred)
	float q0_grouped = 0.f;
	float q0_push = -0.2f;
	float ctx_invaded = 0.6f;		 // preference for GROUPED per ally death on our half in the last window
	float ctx_fights = 0.3f;		 // preference for PUSH per (kills - deaths) in the last window
	float stance_hysteresis = 0.15f; // keep the current stance unless another is better by this
	float pain_death = 1.0f;		 // pain added where an ally died
	float pain_hit = 1.0f;			 // pain per max-health fraction of champion damage taken
	float pain_kill_relief = 0.6f;	 // pain removed where an enemy died near us
	float pain_half_life = 50.f;	 // rounds
	float pain_w = 8.f;				 // farming-score rounds added per unit of pain at a camp
	float fight_learn_rate = 0.15f;	 // fight-estimate change per death after a fight / kill after a fight
	float fight_bias_max = 0.3f;	 // max boldness (log scale); caution may go to twice this
	int group_radius = 12;			 // GROUPED: camps farther than this from allies' camps cost extra
	float group_far_w = 0.8f;		 // ... rounds per tile beyond the radius

	// Draft
	int draft_model = 1; // 1: map-aware composition choice from draft_table.h (nearest training maps) when present

	// Fuel: farm scoring order and budget
	int score_near = 20;			  // score groups within this Chebyshev distance first
	int score_fuel_floor = 30000; // stop scoring farther groups below this much fuel

	// Turn order (set_priority, higher acts first within our team, from the next round)
	int prio_idle = 2;
	int prio_capture = 5;
	int prio_fight = 1000;		// fighters: +this when we lead the next round, -this when we trail it
	int prio_flee = 2000;		// escapers act first
	int prio_alternate = 0;		// 1: fighters alternate for double turns (lost 8-17 points head-to-head); 0: engaged act first
	int safety_v2 = 0;			// 1: retreat counts only camps that would target us (stayed out too long: -10 points)
	int rest_on_spawn = 1;		// rest one turn on spawn after arriving hurt (health is restored at turn end)
	int sticky_tribute = 1;		// finish a bank trip once started
	int claim_tiebreak = 1;		// on our own group only lower-index claimers count

	// Aggression
	float steal_hp_frac = 0.55f; // need this health fraction to farm on the enemy half
	int gank_bag = 25;			 // chase a visible carrier with at least this many gems
	float deny_hp_frac = 0.6f;	 // contest an enemy's capture (step on its tiles) from this health fraction
	float deny_capture_mult = 1.3f; // value multiplier for contesting an enemy's capture
};

inline constexpr Params P{};
