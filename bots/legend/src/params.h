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
	int farm_monolith = 1;			 // 0: never farm a monolith group (20,000 HP, 200 strength; the user: do not rely on it for gems)
	int max_trips = 5;				 // heal trips we accept to finish one camp group (camps never heal)
	float join_min_rounds = 14.f;	 // join an ally's group when it alone needs more rounds than this
	int max_join = 1;				 // extra bodies allowed on one (non-monolith) group
	float join_share = 0.6f;		 // value credited to a joining body (the claimer captures)
	int pair_plans = 0;				 // claim packs too heavy for one body and wait for a partner (off: costs pace)
	float pair_wait = 8.f;			 // rounds added to a pair plan for the partner to arrive
	int pair_wait_max = 18;			 // give up waiting for a partner after this many rounds
	float target_threat_adv = 1.1f;	 // skip camps where recently seen enemies beat us (and allies there)

	// Farming model corrections (prediction audit, tools/analysis/xm_audit.mjs on 48 traced games vs _v6 and _hunt2)
	int math_eta = 1;				 // travel = steps to attack range (ranged: 3), dash kits 10 tiles per 8 rounds
									 // (was d-1 for all: Cassi/Stellar/Issac/Ren arrived 2.3 rounds earlier than predicted)
	int math_taken = 1;				 // damage over a kill: camps die one by one (sequential integral), allies standing at
									 // the group tank like claimers, the safety retreat line is the HP budget (was 1.6-2.3x high)
	float ranged_exposure = 0.25f;	 // share of the time a lone ranged champion (range 3) is in reach of the camps it is
									 // not hitting (per-round damage / incoming: 0.88-0.91 with 1 live camp, 0.34-0.63 with 2-4)
	int presence_radius = 4;		 // visible allies this close to a group's centre count as tanks for the damage share
	float dash_pace = 0.8f;		 // dash kits: rounds per tile on a walk (one 2-tile dash per 8-round cooldown: 8 rounds / 10 tiles)
	float dash_head_start = 1.f; // ... after the first steps saved by the opening dash (refit on 789 Issac/Ren walks: travel
								 // MAE 1.59 rounds vs 1.75 with 2 steps and 3.4 for the old d-1)
	int math_gold = 1;				 // gold is worth less as the game nears its end (a shard pays off over the rounds left)
	float gold_horizon = 500.f;		 // rounds left at which one gold is worth gold_value gems; linearly less below that
									 // (+5 strength on 40-50 is ~+5% farm rate: 0.22 gem/gold needs ~500 rounds to pay)

	// Safety
	float retreat_hp = 0.25f;		 // retreat below this health fraction (or 4 rounds of incoming camp damage)
	int finish_camp = 1;		 // below the retreat line, stay to finish the group we farm when it dies within
								 // finish_rounds and we keep finish_hp_floor of max health (worst case: every camp in
								 // range hits us every round) and no enemy is within finish_enemy_d
	int capture_before_retreat = 1; // below the retreat line, still capture a reward next to us (no camp hits, no enemy near)
	int finish_rounds = 4;
	float finish_hp_floor = 0.08f;
	int finish_enemy_d = 8;
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
	int stay_rule = 1;				 // stay in a fight when our health > the enemies' worst damage until the target dies, with
									 // no other enemy within stay_support_r of the target (the user's rule, session 2)
	int stay_veto = 1;				 // ... and skip fights where that worst damage could kill us, while we can still escape
	int stay_support_r = 10;
	float stay_margin = 1.1f;
	int flee_recall = 1;			 // fleeing out of reach: recall when no enemy can interrupt it (safe_to_recall)
	int support_filter = 0;			 // a visible ally counts in the fight only when it can help: health above the retreat
									 // line and within support_reach of an enemy here (ladder audit: 'phantom support', a
									 // full-health Cassi died with Issac at 11 HP counted as backup)
	int support_reach = 6;
	float pair_caution = 0.f;		 // Cassi and Issac die together (both bodies, both bags): this much more advantage to fight
	int win_bank = 0;				 // a bag that wins the game goes to the nearest altar: no capture-recall away from it, no
									 // retreat home with it (ladder interlock: Ren recalled with 72 gems 3 steps from an altar
									 // and lost 976-1056)
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

	int build_style = 2;	   // 0 = old farm builds, 1 = health/durability/treasure builds (ladder-proven),
							   // 2 = value-model builds (tools/analysis/item_value.py): Bruiser over Power, early Treasure
							   //     on the rich farmers, survival first on Cassi & Issac, builds that never run out
	int rich_treasure_first = 0; // build_style 2: Ren and Stellar open with Treasure (1) or with r2's first emblem
							   // (Ren Jungle health, Stellar Monster) and Treasure second (0); vs _v6 on the ladder
							   // maps: 1 won 19/24 (gems +8,623), 0 won 21/24 (+9,385, deaths 441-670)
	int ci_health_first = 1;   // build_style 2: Cassi & Issac buy health first (1) or Monster damage first (0);
							   // vs _v6 on the ladder maps: 1 won 19/24 (gems +8,623, deaths 495-660), 0 won 16/24 (+3,449, 560-550)
	int monster_in_dps = 1;	   // count the Monster emblem's +10% camp damage in the kill-time model

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
	// ... "near" means a recently seen enemy within this many tiles (minus the rounds since we saw it). Measured
	// on 24 ladder games: with the nearest enemy 7-9 tiles away a fight followed within the 8-round cooldown
	// only 13% of the time while farming (28% overall), at 5-6 tiles 51-63%: casting on the camp is the better
	// bet beyond 6. Was 9 (enemy_near).
	int hold_spell_dist = 6;  // damage spells
	int hold_cc_dist = 7;	  // stuns (worth more in a fight: they deny a turn)
	// Spell timing in fights (one cast per turn, 8-round cooldowns: a ready spell not cast is lost value)
	int melee_aoe_stun = 1;	  // melee area stunners (Ryth) stun from range 2..range+radius instead of walking in first
	int flee_stun = 1;		  // fleeing with a walk-exclusive stun: stun a melee/dash chaser that can hit us next turn
	int step_hit_other = 1;	  // melee: after a step that leaves the target out of reach, hit another enemy in reach

	int dash_holes = 1;		   // dash kits route over 1-wide hole crossings (fields treat those holes as ground; the
							   // step waits for the dash instead of walking around), see world.cpp
	int dash_wait_max = 4;	   // at a crossing with the dash on cooldown: wait up to this many rounds, else walk around
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
	float ucb_c = 0.f;				 // exploration bonus (UCB1); 0.3 cost ~2 points over 540 games (a game has ~25 windows)
	float prior_pull = 0.f;			 // per window, unplayed stance values drift back to their priors (tested with ucb_c)
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
	int score_cap = 1;			  // skip groups whose score bound cannot beat the best so far (same choice, less fuel;
								  // gen16 98x99 vs _L0: scoring 1,350-1,660 fuel per group, ~60k a turn; see x_mr_NOTES)

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
	int claim_helpers = 1;		// ... but higher-index claimers there still add their damage to our kill plan
	int home_edge_fix = 1;		// home trips also from 1-2 steps away (else a hurt body flip-flops at the spawn edge)

	// Bank routes. Recall-while-capturing makes most trips spawn -> camp -> (teleport) spawn, and the bag is then
	// banked at the altar nearest spawn; where that altar is far (30x80: 36 steps), each bank costs a long walk
	// out and a recall back for a 22-34 gem bag. Unopposed, 14.6% of body-rounds were walks to an altar
	// (tools/analysis/bank_audit.mjs); banking before the recall would have saved >=10 rounds on 166 of 355
	// capture-recall-then-bank trips (tools/analysis/bank_first.mjs).
	int bank_first = 1;			// full bag at a capture: skip the recall and bank at the nearest altar when that beats banking from spawn
	int bank_first_margin = 2;	// ... by at least this many steps (nearest-altar walk + recall_time + margin <= spawn altar walk)
	float bank_trip_w = 1.0f;	// bank threshold rises by this many gems per step of bank trip beyond bank_trip_free
	int bank_trip_free = 12;	// bank trips up to this many steps keep the plain threshold
	float bank_trip_cap = 2.0f;	// ... and the threshold never exceeds this multiple of the plain one
	int bank_ignore_spawn = 1;	// "bank before a risky fight" ignores enemies standing on their own spawn

	// Aggression
	float steal_hp_frac = 0.55f; // need this health fraction to farm on the enemy half
	int gank_bag = 25;			 // chase a visible carrier with at least this many gems
	float deny_hp_frac = 0.6f;	 // contest an enemy's capture (step on its tiles) from this health fraction
	float deny_capture_mult = 1.3f; // value multiplier for contesting an enemy's capture
};

inline constexpr Params P{};
