// Every tunable weight and threshold lives here so variants can be generated for self-play tuning.
#pragma once

struct Params
{
	// Task valuation
	float gold_value = 0.22f;		 // gem-equivalent value of one gold
	float deny_bonus = 0.043f;		 // extra value for camps on the enemy half (they lose what we take) (ES: 0.55 -> 0.043)
	float enemy_half_penalty = 10.f; // rounds-equivalent risk cost for enemy-half camps
	float unknown_discount = 0.75f;	 // value multiplier for groups whose state we have not seen recently
	float hysteresis = 1.15f;		 // keep current task unless a new one beats it by this factor
	float join_bonus = 1.25f;		 // bonus for joining an ally on a camp that needs two bodies
	int max_wait = 18;				 // rounds we are willing to wait for a respawn on arrival
	int farm_monolith = 1;			 // 0: never farm a monolith group (20,000 HP, 200 strength; the user: do not rely on it for gems)
	int max_trips = 5;				 // heal trips we accept to finish one camp group (camps never heal)
	float join_min_rounds = 14.f;	 // join an ally's group when it alone needs more rounds than this
	int max_join = 3;				 // extra bodies allowed on one (non-monolith) group. Was 1; 3 (agent farm): unopposed pace on the 17 official maps
									 // 563.1 -> 553.3 (rows 425 -> 398, monolith 474 -> 417, elkring 472 -> 442, eight 427 -> 396), head-to-head vs _rm
									 // 54.5 both (official 58.8 -> 61.8). Ladder rows: the enemy clears each 3-wolf pack with 3-5 bodies in ~11 rounds
	float join_reach = 1.2f;			 // (0 off) join a claimed group only when we reach it within this share of the claimers' remaining clear time
	float join_share = 0.6f;		 // value credited to a joining body (the claimer captures)
	int pair_plans = 0;				 // claim packs too heavy for one body and wait for a partner (off: costs pace)
	float pair_wait = 8.f;			 // rounds added to a pair plan for the partner to arrive
	int pair_wait_max = 18;			 // give up waiting for a partner after this many rounds
	int no_split = 1;				 // a reward with a visible ally on its tiles is left to that ally (lower index wins when both stand
									 // there): ladder rows, 10 of our 18 captures were 33/33 splits of one 66-gem pack; unopposed
									 // rows 6 of 21 (agent farm)
	int unknown_keep = 2;			 // 1: the unseen-for-60-rounds discount (unknown_discount) does not apply to the target we walk to:
									 // every unseen enemy-half group lost 25% at round 61 and bodies that had walked 60 rounds to one
									 // switched there (pilgrimage, ambush: 3-4 bodies turned back at r61-66; agent farm).
									 // 2 (default): no exemption, but a group never seen is discounted from round 0 (no cliff at r61 either).
									 // Head-to-head vs _rm (56 maps, with no_split, obj_focus and the pace patch): 1 -> 48.2 (official 44.1, deaths
									 // 1255-1101: bodies kept walking into the enemy half); 2 -> 54.5 (58.8, deaths 1055-1287). Pace 559.0 vs 563.1
	float target_threat_adv = 1.4942f;	 // skip camps where recently seen enemies beat us (and allies there) (ES: 1.1 -> 1.305)

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
	float fight_back_margin = 0.873f; // when they can already hit us, fight back unless this outmatched (ES: 0.75 -> 0.873)
	float cornered_margin = 0.7409f;	 // chasers we cannot outrun: hit back unless the advantage is below this (ES: 0.45 -> 0.634)
	float far_enemy_weight = 1.0f;	 // visible enemies beyond reach+2 count this much in the fight estimate
	int ally_spell_dps = 1;			 // count allies' spells in our damage (else basic attacks only)
	int spawn_heal_bonus = 1;		 // on our spawn, count one more health bar (we heal fully)
	int bag_caution = 40;			 // carrying this many gems, avoid even fights we can escape
	int backup_radius = 5;			 // allies (seen, or claiming a camp) this close count as backup
	float isolated_fight_adv = 1.2335f; // alone, start a fight only at this advantage (or a sure kill) (ES: 1.6 -> 1.428)
	float isolated_flee_adv = 1.5000f;	 // alone and weaker than this: walk away as soon as they are in sight
	int flee_dist = 5;				 // ... when the nearest enemy is this close
	// Survival vs grouped invaders (agent survive, session 6; experiments/wip/x_survive_NOTES.md). Ladder: 232 deaths vs 50 in
	// 17 games; the killers were within 8 tiles for 7+ rounds before 75% of them. Recommended set (_svF) vs _rm, 56 maps,
	// 112 games: 61.6% head-to-head (official 64.7), deaths 881-1301; vs _ST 56.2 (_rm 54.5), _eA 69.6 (_rm 57.1); held-out pool
	// and _eB/_eC in the notes. Our deaths fall 23-38% against every opponent with more gems banked.
	int outmatch_flee = 1;			 // also walk away (not alone) when the visible group here outmatches us: adv below
	float outmatch_flee_adv = 0.8f;	 // ... this (1.0: 50.0% vs _rm on the official 17, 0.7: 52.9, 0.8: 55.9), with at least
	int outmatch_min_enemies = 2;	 // ... this many visible enemies within 9 and the nearest within outmatch_flee_dist (not yet
	int outmatch_flee_dist = 8;		 // ... in reach: in reach the fight-back / cornered rules apply)
	float outmatch_solo_adv = 0.45f;	 // ... against a single visible enemy flee below this advantage (0: never; traces: 7 of 68
									 // deaths began outside reach against one stronger enemy, e.g. their 1,900-health Ren)
	float pair_flee_bonus = 0.3f;	 // Cassi & Issac (two bodies, two bags per death): flee bar + this (official 17: 55.9 -> 55.9 vs
									 // _rm, 61.8 -> 70.6 vs _eA)
	float pair_low_hp = 0.25f;		 // Cassi & Issac: below this health fraction skip fights we can escape (others: 0.25). 0.4 cut
									 // pair deaths a further 12% vs _eA but cost 4-5 points vs _ST every time (_svA/_svD 50.9 vs 53.6/56.2)
	float pair_kill_adv = 0.5f;		 // ... and below it a 'killable' target needs this advantage (1.0: same games as 0.5, off)
	float pair_retreat_hp = 0.f;	 // Cassi & Issac: safety() retreat line (max with retreat_hp; 0.4: 55.9 vs _eA vs 70.6 without)
	int ren_reflect = 1;			 // combat(): a fight on Ren counts its retaliation (0.2 x focus per hit) on each of our hitters
	int threat_score_memory = 8;	 // group_score: enemies seen this many rounds ago still guard the camps within 8 of them
									 // (20: 50.0 vs _rm, more deaths; alert_radius 8 for the team DANGER alert: 47.1, more deaths)
	float reserve_margin = 0.3284f;	 // half the team dead: extra advantage needed to fight
	int stay_rule = 0;				 // off: all three on (+ ES params) = 49.1% vs this build, fewer deaths (1301 vs 1504) but
									 // lower panel mean (vs _r2 67.0 vs 78.6, _L0 58.9 vs 67.0); without stay_veto 41.1%
									 // rule: stay in a fight when our health > the enemies' worst damage until the target dies, with
									 // no other enemy within stay_support_r of the target (the user's rule, session 2)
	int stay_veto = 0;				 // ... and skip fights where that worst damage could kill us, while we can still escape
	int stay_support_r = 10;
	float stay_margin = 1.1f;
	int flee_recall = 0;			 // fleeing out of reach: recall when no enemy can interrupt it (safe_to_recall)
	int support_filter = 1;			 // a visible ally counts in the fight only when it can help: health above the retreat
									 // line and within support_reach of an enemy here (ladder audit: 'phantom support', a
									 // full-health Cassi died with Issac at 11 HP counted as backup)
	int support_reach = 6;			 // A/B on legend (56 maps, 112 games): 55.4% head-to-head, vs _L0 68.8 (67.0), _r2 80.4 (78.6),
									 // _v6 86.6 (83.9), _devci 85.7 (80.4), _hunt2 94.6 (93.8); deaths -16%
	float pair_caution = 0.f;		 // Cassi and Issac die together (both bodies, both bags): this much more advantage to fight
									 // (0.3 measured neutral: 63.4 vs _r2 against 67.0, 87.5 vs _v6 against 86.6)
	int alert_refresh = 0;			 // (A/B neutral: 50.9% head-to-head, +2.6 vs _r2) re-posting the same alert refreshes it for the team (a toggle bit; before, an alert
									 // re-posted at one tile expired after its max age while the fight went on)
	int squishy_hp_first = 0;		 // (A/B: 40.2% head-to-head, -8 vs _devci: rejected) Stellar/Prism/Tavi and Varg/Vendetta/Vesper buy a Durability health emblem first (they
									 // bought 15 damage shards first: 750-1000 max HP vs 1125-1800 for the same picks of _devci)
	int win_bank = 1;				 // A/B: neutral (50.0% vs base; 56.2 vs 55.4 with support_filter)				 // a bag that wins the game goes to the nearest altar: no capture-recall away from it, no
									 // retreat home with it (ladder interlock: Ren recalled with 72 gems 3 steps from an altar
									 // and lost 976-1056)
	int deficit_defend = 3;			 // this many more enemies alive than allies: defensive play
	int deficit_escort = 2;			 // ... this many: a respawned champion waits on spawn for the next ally
	int escort_wait = 15;			 // max rounds to wait on spawn for an escort
	int threat_memory = 7;			 // rounds an unseen enemy is still assumed nearby
	int alert_radius = 0;			 // allies avoid this radius around a reported danger
	int alert_age = 12;				 // rounds a danger report stays valid

	// Tribute
	int tribute_min = 54;	   // carry at least this many gems before a dedicated altar trip
	int early_round = 150;	   // before this round ...
	int early_tribute_min = 22; // ... bank from this bag size (first gold and safety sooner)
	int tribute_near = 5;	   // tribute anything when an altar is this close
	int tribute_risky = 10;	   // bank before risky fights when carrying this many
	int unsafe_altar_penalty = 14; // extra steps for a contested altar where enemies were just seen
	int altar_enemy_memory = 8;    // rounds an enemy sighting near an altar keeps it unsafe
	int endgame_margin = 12;   // extra rounds of slack for the final tribute
	int endgame_alarm = 800;   // their score from which stopping their tributes overrides everything

	// Session 11: ideas from the default branch (claude/lucid-pasteur-2jiojv: the Oct 16 "round-2" bot, b5d4e56, and its
	// Oct 17 merge a25ae20, which does not compile), ported onto legend_m8 at the user's request: "push the ideas into the
	// bot; if they are detrimental I will notify you". Each one has its own switch (0 = legend_m8's behaviour).
	// legend_m9 had them all on: vs legend_m8 58.0 / official 35.3, Mite proxy 63.6 (legend_m8 76.1), ifish proxy 51.1 (69.3),
	// _px9 65.9 (78.4). legend_m10 ships them all off (= legend_m8's games). Alone on legend_m8 (88 games / official vs
	// legend_m8): health_emblem 47.7 / 50.0, learn_burst 52.3 / 52.9, lethal 51.1 / 50.0, cd_slack 47.7 / 41.2, walk_cast
	// 44.3 / 47.1, endgame_bank 48.9 / 50.0; learn_burst + lethal: 50.0 / 52.9, Mite proxy 77.3 / 88.2, _px9 63.6 (78.4).
	int mi_health_emblem = 0;	   // a Durability health emblem as the second emblem of every build
	int mi_learn_burst = 0;		   // remember each enemy's biggest one-round hit on us; combat() uses it while its spells are up
	int mi_lethal = 0;			   // leave a fight we can walk away from when an enemy within 5, spells up, has shown it can kill us from here
	int mi_cd_slack = 0;		   // danger map: an enemy spell this many rounds from ready already counts as ready
	int mi_walk_cast = 0;		   // danger map: a ready spell that can follow a step (not move-exclusive) reaches 5, not 4
	int mi_endgame_bank = 0;	   // within this many gems of the goal (either team) the bank threshold shrinks linearly
	float mi_learn_fight = 0.f;   // fight record: P(we win an exchange) = (their deaths + 3) / (all deaths + 6); losing makes us
								   // more careful (fight margin x caution, enemy-half penalty x caution^2, deny bonus x 2p)
	int mi_learn_race = 0;		   // banking-rate race: they finish first by mi_race_ratio -> deny +0.4, enemy-half x0.6; we do -> fight margin +0.15
	int mi_race_after = 250;
	float mi_race_ratio = 0.75f;
	int mi_island_bank = 0;	   // inside a crystal island (no altar): recall out to bank at this bag
	int mi_recall_shop = 0;	   // recall home to shop with this much gold when nothing can interrupt the channel
	int mi_relaxed = 0;			   // never idle while something is farmable: if nothing scores, score again with 3x wait / trip limits
	int mi_two_bodies = 0;		   // at most two bodies on one group (join limit 1), objectives and monoliths excepted
	int mi_deny_gems = 0;		   // the enemy-half deny bonus applies to the gem part of a group's value only
	int mi_flip_guard = 0;		   // 6+ target switches within 20 rounds: keep the current target for 25 rounds
	int mi_kite = 0;			   // farm a group from distance 4 with spells only when that is faster (no damage taken, no heal trips)
	float mi_kite_ratio = 0.8f;	   // ... only with spell damage at least this share of our full camp damage
	float mi_kite_max_kill = 40.f; // ... and a kill within this many rounds
	int mi_chip = 0;			   // an idle damage spell hits a camp within 4 while passing (camps never heal)
	int mi_close_in = 0;		   // in range by the group field but no live camp in sight (walls block vision): walk closer
	int ward_bush = 2;		   // place_ward: 1 = prefer a bush tile within 2 (a ward inside a bush reveals it; the sneaky-bush team wards bushes
							   // 100% of the time, we 19%); 2 = also re-ward after ward_bush_gap rounds when a bush is in reach and our ward is not in it
	int ward_bush_gap = 3;	   // ... (ward_bush 2)
	int mapdraft = 3;		   // 0 = our composition choice; sparring proxies: 1 = Mite's per-map drafts, 2 = ifish's (draft.cpp)
							   // 3 = ours with the top teams' choices where they beat ours (rushbait-v2, interlock, expanse; stampede with md_stampede)
	int md_stampede = 1;	   // mapdraft 3: stampede drafts the 2nd team's casters (Prism, Stellar, C&I, Ryth, Tavi) for the ring plan
	int build_style = 2;	   // 0 = old farm builds, 1 = health/durability/treasure builds (ladder-proven),
							   // sparring proxies: 3 / 4 / 10 = ifish (frontline health then Power / Monster then Power / 3 or 4 by map),
							   //     9 = Mite (Jungle, Durability in the damage stat, Bruiser health, Power)
							   // 2 = value-model builds (tools/analysis/item_value.py): Bruiser over Power, early Treasure
							   //     on the rich farmers, survival first on Cassi & Issac, builds that never run out
	int rich_treasure_first = 0; // build_style 2: Ren and Stellar open with Treasure (1) or with r2's first emblem
							   // (Ren Jungle health, Stellar Monster) and Treasure second (0); vs _v6 on the ladder
							   // maps: 1 won 19/24 (gems +8,623), 0 won 21/24 (+9,385, deaths 441-670)
	int ci_health_first = 0;   // build_style 2: Cassi & Issac buy health first (1) or Monster damage first (0);
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
	float cap_recall_hp = 0.610f;  // ... and health is below this fraction, (ES: 0.75 -> 0.61)
	int cap_recall_gold = 60;     // ... or gold after the capture reaches this (shopping),
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
	// Cast before walking (session 3, agent cast). Damage spells are walk-exclusive, so a turn spent walking past a
	// camp wastes the cooldown. Traced on 3 comp games: Stellar/Cassi had a ready damage spell, a live camp of
	// another group 4 tiles away, and walked on in ~150 turns (only the task group's camps were ever cast on).
	int cast_en_route = 1;	  // 0 off; 1 farming bodies cast dmg / non-stun area spells on a camp (of one of our groups, not the
							  // task group) exactly 4 tiles away instead of walking that turn; 2 also stuns that do damage
	int cast_route_enemy_d = 0;		// cast_en_route: not when an enemy seen in the last cast_route_memory rounds is this close
									// (eight, 6 games vs _es2/_r2/_L0: casts on 0/6, casts off 6/6, enemy_d 14 0/6, from r150 3/6,
									// en_route off 3/6, near_target off 2/6: a knife-edge opening map, not a systematic loss)
	int cast_route_memory = 10;
	int cast_route_from = 0;		// cast_en_route: not before this round (opening fights)
	int cast_near_target = 1; // fighting: the chosen target is out of spell range but another enemy is within 4: cast on that one
							  // instead of walking toward the target (path1/eng4 in the trace: 41 turns in 3 games)

	int varg_splash_pos = 1;   // Varg steps next to the camp with the most live neighbours before hitting (splash covers it all; agent farm)
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
	float kill_gems = 40.1472f;			 // stance reward per enemy death, in gems (bag + 60 rounds of their farming)
	float death_gems = 45.f;		 // stance punishment per ally death, in gems (heavier: we also pay them 50 gold)
	float reward_scale = 40.f;		 // gems per window that count as reward 1
	float ucb_c = 0.f;				 // exploration bonus (UCB1); 0.3 cost ~2 points over 540 games (a game has ~25 windows)
	float prior_pull = 0.f;			 // per window, unplayed stance values drift back to their priors (tested with ucb_c)
	float q0_spread = 0.3f;			 // optimistic prior values per stance (SPREAD starts preferred)
	float q0_grouped = 0.f;
	float q0_push = -0.718f; // ES: -0.2 -> -0.718
	float ctx_invaded = 0.0075f;		 // preference for GROUPED per ally death on our half in the last window
	float ctx_fights = 0.3f;		 // preference for PUSH per (kills - deaths) in the last window
	float stance_hysteresis = 0.15f; // keep the current stance unless another is better by this
	float pain_death = 1.0f;		 // pain added where an ally died
	float pain_hit = 1.0f;			 // pain per max-health fraction of champion damage taken
	float pain_kill_relief = 0.6f;	 // pain removed where an enemy died near us
	float pain_half_life = 50.f;	 // rounds
	float pain_w = 8.f;				 // farming-score rounds added per unit of pain at a camp
	float fight_learn_rate = 0.3262f;	 // fight-estimate change per death after a fight / kill after a fight (ES: 0.15 -> 0.235)
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
	int defer_islands = 1;			// find_islands runs from prebuild_fields on a later turn (~47k fuel on 100x100 maps), not in init
	int start_round = 2;			// no body acts before this round: with the opening-fuel fix bodies started in round 1 or 2 depending on
								// their init cost (staggered: 40.2% vs _ST); 2: panel mean 75.9 vs 72.8 (_L0 _es2 _r2 _v6), 50.9 head-to-head
	int danger_detour = 1;			// step_field: when every improving step is in danger and we are not, route around it (dynamic search)
	int danger_detour_fuel = 40000;	// ... only with this much fuel left (the search costs up to ~30k on 100x100 maps)
	int team_bank = 1;				// share the team's carried gems (comms bit 6); wins_with counts the others' bags: every carrier banks when the team's bags win
	// Gem race (update_mode): project both finishes from the banking rates; behind by race_margin rounds -> gold is
	// worth race_gold of its value; and when our fights go well, contest their gems (deny, half penalty, fight bar,
	// carriers with race_carrier+ gems posted as opportunities).
	int race_mode = 1;
	int race_sample = 25;			// sample both banked totals every this many rounds (8 samples kept)
	int race_from = 150;			// not before this round
	int race_margin = 73;			// behind = they finish this many rounds before us
	int race_death_slack = 2;		// "fights go well": enemy deaths + this >= our deaths, and not outnumbered now
	float race_gold = 0.3f;
	float race_deny = 0.5f;
	float race_half = 0.5f;
	float race_fight = 0.15f;
	int race_carrier = 30;
	int capture_reset = 1;		// an enemy seen on the group's tiles restarts the capture-recall clock (the engine resets the capture)
	int tribute_elapsed = 1;	// handle_channel counts the tribute's remaining turns from its start, not from the carried bag
	int bank_first = 0;			// full bag at a capture: skip the recall and bank at the nearest altar when that beats banking from spawn.
								// OFF (agent pace): unopposed pace on 56 maps 472.7 -> 469.7 with it off (official 17: 574.3 -> 567.6; pilgrimage -123,
								// rushbait-v2 -48, interlock -19; ambush/monolith/collision +16..+24 are map noise).
	int bank_first_margin = 2;	// ... by at least this many steps (nearest-altar walk + recall_time + margin <= spawn altar walk)
	float bank_trip_w = 1.7394f;	// bank threshold rises by this many gems per step of bank trip beyond bank_trip_free
	int bank_trip_free = 12;	// bank trips up to this many steps keep the plain threshold
	float bank_trip_cap = 2.0f;	// ... and the threshold never exceeds this multiple of the plain one
	int bank_ignore_spawn = 1;	// "bank before a risky fight" ignores enemies standing on their own spawn

	// Objective maps (agent obj, session 3): the gems sit in one or a few heavy groups (stampede, contest)
	int obj_plan = 1;			// detect objective maps at init (World::detect_objective); everything below needs it
	float obj_min_hp = 4500.f;	// a group this heavy cannot be soloed early (elk 2,400; monolith 20,000). Was 6000; 4500 admits ambush's
								// 4,750-5,800 HP gem groups: ambush pace 840 -> 646 (agent pace)
	float obj_share = 0.7f;		// ... objective map when such groups hold this share of the map's gem rate (was 0.6; 0.7 keeps eight 0.67,
								// expanse 0.64, interlock 0.59 out: with 0.4 they got +26..+49 rounds slower, ambush the same -194)
	int obj_max_groups = 8;		// ... and at most this many such groups on the whole map (both sides). ambush 6, contest 2, stampede 1; swirl and the
								// ladder 45x30 map have 14 (every gem group is heavy there): with the mode on they got +15 rounds and 2 of 12 more losses
	int obj_min_attackers = 2;	// ... counting only groups with at least this many camps that hit back (2 excludes a lone monolith: monolith-only
								// maps with the mode on: 105 of 152 games vs _k1/_v6/_r2/_es2, about baseline; x_obj_NOTES). Agent pace re-tested
								// 1: contest unopposed pace 1087 -> 905 and nothing else changes, but the held-out gold/obj pool (100 games vs
								// _ST) went 49 -> 46 with it (noise level) and the gold maps' lone monoliths are what it turns on: left at 2
	int obj_focus = 1;			// the team plan is only for the objective group claimed by the lowest-index body: on ambush (6 objective groups)
								// every body chose a different one (Ren g1, Stellar g6, Cassi g11, Varg the enemy's g10), arrived alone, fled at
								// 120-230 HP, and the gather rule (obj_gather) never saw 3 bodies (agent farm)
	int obj_team = 1;			// score an objective group with the whole living team's damage once the team can
								// clear it (obj_team_ready); the solo plan never passes (stampede: nobody touched
								// the 360-gem group before r905; bodies chipped it one or two at a time and left it)
	float obj_clear_max = 40.f;	// ... team clear time (rounds) at most this
	float obj_absorb = 0.6f;	// ... and the camp damage it takes at most this share of the team's usable health
	int obj_team_attackers = 1;	// ... only on groups with at least this many camps that hit back (2: not a lone monolith)
	int obj_min_bodies = 3;		// ... with at least this many bodies alive
	int obj_dead_max = 1;		// ... and at most this many dead
	float obj_value_share = 0.5f; // value credited to each body for the team plan
	int obj_gather = 3;			// wait just outside camp range until this many bodies are at the objective
	int obj_gather_r = 6;		// ... counted within this distance of the group's tiles
	int obj_gather_max = 30;	// ... for at most this many rounds
	float obj_solo_rounds = 8.f; // no gathering when we kill what is left alone within this many rounds
	float obj_go_hp = 0.8f;		// heal at home first when heading for the objective below this health fraction
	int obj_go_far = 12;		// ... from farther than this
	int obj_max_wait = 18;		// rounds we wait on arrival for an objective group's respawn (max_wait elsewhere)
	int obj_commit = 200;		// extra rounds before giving up on an objective target (the kill alone takes 20-40)
	int obj_attackers_first = 1; // on an objective group hit the camps that hit back first (elks before gem clusters)
	int obj_shield = 1;			// safety: an objective camp with a visible ally strictly nearer to it does not hit us
	int obj_shield_enemy_d = 8;	// ... only while no enemy is within this distance
	int obj_open_rounds = 0;	// objective map opening: before this round skip gold groups that are not clearly ours
	int obj_open_margin = 4;	// ... (enemy spawn less than this many steps farther than ours; contest: the opening
								// fights at the central gold triples decided the game, 6 of our deaths by r59 vs _r2)
	// Session 9 (agent obj2): objective ring. The 2nd ladder team killed stampede's 17,400-HP group at r54-124 taking 0 damage:
	// every body stood at Chebyshev 4 from the elks (camps hit within 3) and cast range-4 spells (area spells hit up to 6 camps).
	int o2_ring = 2;			// objective group with live elks: casters (a range-4 damage/stun/area spell) cast from distance 4 and never step into camp reach
								// (2 = on stampede only: elsewhere, e.g. ambush, it lost 5 of 11 changed games in session 10)
	float o2_ring_clear = 160.f; // ring plan ready when the casters' spell damage clears the group within this many rounds
	float o2_ring_share = 0.5f;	 // value share per caster
	int o2_ring_min = 2;		 // at least this many living casters (including us)
	int o2_ring_melee = 0;		 // 1: bodies that are not casters (melee kits) never take the all-in team plan while the ring is on
	float o2_ring_mindps = 0.f;	 // a caster whose spell damage per round is below this stays out of the ring plan (Ren's stun is 15.6, Cassi's 17.5)


	// Lone-monolith maps (agent contest, session 7): contest (the ladder map we lost 0-1000 with 63 deaths), its ladder copy and gold_mono_*
	int mono_plan = 1;			// detect them at init (World::mono_mode); everything mono_* needs it (0: the baseline, byte-identical play)
	float mono_share = 0.9f;	// ... when lone monoliths hold at least this share of the map's gem rate
	int mono_obj = 0;			// ... plan the lone monoliths with the objective team plan (obj_*; obj_min_attackers=2 left them out)
	int mono_grouped_until = 0;	// ... play the GROUPED stance (stay together, off their half) until this round
	int mono_build = 0;			// builds on those maps: 0 = build_style, 3 = the ladder teams' (Durability / Bruiser health, then Power stacks)
	int mono_fort = 0;			// probe: lone-monolith maps: before mono_fort_until hold on spawn (healing 100% per round) instead of farming
	int mono_fort_until = 0;
	int mono_rg = 0;			// regroup: lone-monolith maps: a body that sees >= mono_rg_n enemies (within mono_rg_see) and is outnumbered by them goes home to
								// heal on spawn (100% per round) and alerts the team (mono_rg_team); they hold there mono_rg_hold rounds after the last sighting
	int mono_rg_n = 3;
	int mono_rg_see = 10;
	int mono_rg_margin = 0;
	int mono_rg_hold = 30;
	int mono_rg_team = 1;
	int mono_rg_from = 0;
	int mono_rg_fight_r = 3;	 // an enemy this close: combat() decides instead of walking home
	int mono_gmask = 15;		// which parts of the GROUPED stance apply while mono_grouped_until forces it: 1 enemy-half penalty x2, 2 deny bonus x0.5, 4 isolated fight +0.3, 8 stay near allies' claims
	int home_emblem = 0;		// champions that buy a Home health emblem (recall in 3 turn ends, not 5): Ren 1, Stellar 2, Cassi 4, Issac 8,
							// Ryth 16, Varg 32, others 64 (Intercontinental Fish: Stellar, Issac, Varg, 2nd emblem; we never bought it)
	int home_at = 1;			// ... inserted as this emblem (0 = first). Measured on legend_m11 (official 34): every variant loses (vs m11 32.4-47.1,
							// mite 64.7-76.5 vs 76.5, px9 55.9-73.5 vs 79.4; pace +7..+13 except Stellar/Issac/Varg as 3rd emblem 503.8): off
	int follow_all_until = 60;	// legend_m13: the mono_follow_until blob opening (bodies farm the lowest-index claimant's group) until this round,
							// on the follow_maps only. Clash pool (interlock, eight, rushbait-v2, collision, swirl x 4 layouts, 40 games): vs legend_m11
							// 62.5, proxies mite 82.5 (m11 72.5), px9 80.0 (72.5), snk 75.0 (67.5), fA 80.0 (82.5), ST 85.0 (85.0), ifish 55.0 (57.5);
							// 88 distinct: vs legend_m11 51.1 / official 55.9. On every map (follow_maps 0) it lost 44.1; until r120 57.5, r200 57.5
	int follow_maps = 7;		// follow_all_until only on these maps (0 = all): interlock 1, eight 2, rushbait-v2 4, collision 8, swirl 16 (31: 72.5 h2h
							// but px9 52.5 on the clash pool)
	int pair_open_until = 0;	// every map: before this round any fighting group an ally claims counts as heavy enough to join (IC pairs)
	int mono_follow_until = 200;	// opening: bodies farm the group the lowest-index living claimant farms (one blob) until this round
	float mono_group_w = 0.f;	// cohesion (with mono_grouped_until): rounds of extra cost per tile beyond mono_group_r from the nearest ally's claimed group
	int mono_group_r = 8;
	int mono_open_rounds = 0;	// opening: before this round skip groups on the enemy's half (the enemy's triples at 25 steps from us: on contest
								// two of five bodies walked there from r2 and met 3-4 enemies alone)

	// Stuck champions (tools/analysis/stuck.mjs; experiments/wip/x_stuck_NOTES.md)
	int stuck_live_goal = 1;	 // farming without the group's field: walk to tiles in range of live camps, not of any
								 // group tile (a tile next to a dead camp counted as arrived: frozen 30-78 rounds on gen16)
	int stuck_avoid_skip = 1;	 // step_to: skip the danger-avoiding search when every neighbour is in danger (it cannot
								 // succeed; it cost a full-map search, ~30k fuel, and froze bodies when fuel ran low)
	int target_field_fuel = 32000; // build the current target's field from this much fuel (other fields need 45000): a
								 // per-turn dynamic search to it costs about as much (big maps: scoring left ~36-41k)
	int stuck_detour = 1;		 // after a unit blocks the field's step and the dynamic search detours, keep the detour
								 // until the field value drops below where it started (else A-B-A-B: the field steps back)
	int detour_hold = 12;		 // ... for at most this many rounds
	int stuck_reach = 1;		 // a group unreachable on foot from our side is not estimated by straight-line distance
	int unstick_rounds = 10;	 // a farm/capture walk stuck inside a 3x3 box this many rounds (no attack) drops its target
	int unstick_blacklist = 30;	 // ... for this many rounds (0 rounds: off)
	int giveup_progress = 1;	 // farm(): the give-up clock (2 x eta + 60 rounds on one target) restarts on every hit on the target,
								 // capture turn and respawn wait next to it. Before, eta was the walk left (0 at the group), so any body
								 // spending 60+ rounds on one group (heavy pack, heal trips, waiting out a respawn) blacklisted it for 40
								 // rounds, often just before it paid
	int flip_window = 12;		 // for this many rounds after leaving a target, going back to it needs ...
	float flip_margin = 1.5f;	 // ... this factor more score (on top of hysteresis): stops A-B-A-B target flips
	int score_near_floor = 38000; // stop scoring near groups below this much fuel (0: never); start rotates too
	int score_far_floor = 55000; // stop scoring far groups below this much fuel, rotating the start (0: score_fuel_floor)

	// Aggression
	float steal_hp_frac = 0.55f; // need this health fraction to farm on the enemy half
	int gank_bag = 25;			 // chase a visible carrier with at least this many gems
	float deny_hp_frac = 0.6f;	 // contest an enemy's capture (step on its tiles) from this health fraction
	float deny_capture_mult = 1.3f; // value multiplier for contesting an enemy's capture

	// Fight execution (strategy v2, replay audit of 15 top-team games: 74% of the rounds our champions were hit by
	// champions they dealt no champion damage back; 636 of those rounds they walked, 278 with an enemy already in reach)
	int exec_hit_first = 1;		// engage(): the chosen target is out of reach but another enemy is in reach: hit that one now
								// (ranged: attack/cast and stand; melee: attack, then still step toward the target)
	int exec_flee_hit = 1;		// fleeing melee champions swing at an adjacent enemy before the step (melee may attack and move)
	int fight_commit = 1;		// keep fighting the next turn unless the estimate falls below fight_commit_margin or health
	float fight_commit_margin = 0.7f; // below fight_commit_hp (no engage / flee flip-flop: walking in and out under fire)
	float fight_commit_hp = 0.3f;

	// Fight doctrine (agent doctrine, session 8; docs/strategy_v2/03 section 1). All default off = legend_m4.
	int camp_in_fight = 3;		 // A5 (port of x_side): awake camps hit the nearest champion within 3. 3: a camp whose
								 // nearest body is an enemy adds its strength to our DPS; 2: one hitting us/an ally adds to
								 // theirs; 1: both. On _ST 3 = 56.2 vs _ST (comp 61.8), 2 = 41.1
	int burst_exit = 0;			 // A7 (2: only with no melee/dash chaser within 3, i.e. the step really leaves): drop a fight we can walk away from when the enemies that can reach us next turn
								 // can kill us in one turn (basic attack + best ready cast each), unless the target dies now
	float burst_exit_k = 1.1f;	 // ... our health <= k x that burst
	int spread_vs_splash = 0;	 // A4 (2: area casters count with the spell on cooldown too): with an enemy Varg within 4 or a ready area caster within 5, steps avoid tiles next
								 // to an ally (soft, below enemy reach); melee goal rings skip them when another is free
	int pair_space = 0;			 // A9 (2: also every step of Cassi with an enemy within 9 avoids tiles next to Issac): Cassi fighting with Issac visible: goal ring at 2-3 from Issac, never adjacent
	int support_v2 = 0;			 // A3: an ally recalling/banking/teleporting (seen this round) is not fight support
	int engage_angle = 0;		 // engage(): the walk's end tile avoids the next-turn reach of the target's visible allies when possible
	int strike_first = 0;		 // A6 (bits): 1 = proactive fight (not in reach) with nothing of ours ready and a spell ready
								 // within strike_hold rounds: hold; 2 = ranged without dash/spell for this distance: do not
								 // walk into range (the walk spends the attack), let them come
	int strike_hold = 2;		 // ... at most this many rounds per fight

	// Sparring proxy of the ladder's top teams (agent proxy, experiments/wip/x_px_NOTES.md). All 0 = legend.
	int px_mode = 2;			// 1: combat() takes the top teams' fight rules: focus the lowest-health body in reach (a team
								// kill this turn first), engage at even local power, fight back when hit, commit, retreat late
	float px_engage = 1.0f;		// engage proactively (walk in) at this local power ratio (ours / theirs, hp x dps sums)
	int px_hunt_r = 6;			// ... toward an enemy within this many tiles
	float px_fightback = 0.6f;	// in reach of an enemy: hit back down to this ratio
	float px_commit = 0.6f;		// fought last turn: keep fighting down to this ratio
	float px_retreat_hp = 0.25f; // below this health fraction leave unless a kill is on
	float px_flee_adv = 0.5f;	// not in reach: walk away from a group this much stronger
	int px_stun_first = 1;		// engage(): in reach, stun the target first whatever it is (chain stuns onto the focus)
	int px_ally_spells = 1;
	int px_hold = 0;			// proactive fight, no kill this turn, target out of our reach: when the next step would enter an
								// enemy's next-turn reach, hold outside it (let them walk in and take the first volley) for at
								// most this many rounds per fight (ranged must choose between a step and an attack)
	int px_burst_wait = 0;		// proactive fight with no spell ready: hold outside their reach while a spell is at most this many
								// rounds from ready (open with the burst)		// the team-kill estimate counts allies' spells at half weight (cooldowns unknown)

	// Fight micro v2 (agent fight2, session 9; docs/strategy_v2/08 section 2, experiments/wip/x_f2_NOTES.md). All 0 = legend_m6.
	int aoe_reach5 = 0;			// F1: an enemy area spell (ready, or cooldown unknown) threatens range + radius (5), not 4: danger
								// map, combat()'s reach/incoming, the channel stun check, engage_angle. 2: also walk-compatible
								// spells (Cassi's stun) range + 1. 3: only the danger map for routes (combat() stays at 4)
	int aoe_cast5 = 3;			// F2: our area spells aim at a tile within range whose radius catches the target (reach 5), most
								// enemies first: engage() (ranged), cast_on_nearer, px targeting reach, killable
	int open_first = 0;			// F3 (bits): 1 = after a fight step, cast a walk-compatible spell that now reaches the target
								// (Cassi's stun: walk + stun = the opener); 2 = proactive fight, no cast/attack possible this turn
								// (ranged, an opener of ours ready): when the step enters an enemy's next-turn reach, hold at the
								// edge (they step in, we cast first) for at most open_hold rounds per fight
	int open_hold = 2;			// ... rounds
};

#ifdef LEGEND_RUNTIME_PARAMS
// Training builds only (tools/rl/a100/es_a100.py): the values are defined in a generated params_rt.cpp, so a new
// candidate recompiles one file instead of the whole bot. Submitted builds use the constexpr defaults above.
extern const Params P;
#else
inline constexpr Params P{};
#endif
