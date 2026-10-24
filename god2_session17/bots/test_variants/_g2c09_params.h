// Every tunable weight and threshold lives here so variants can be generated for self-play tuning.
#pragma once
#include "common.h"
// GOD v8 (plan P0-2a): patch 3.0 values only. GOD v5.1-v7 chose 15 settings and the ml2 weights by SDK_HAS_HOR (patch 3.0 vs the sprint
// handbook's pre-patch rules); the platform runs patch 3.0 (+ the 3.0.2 Heart of Ruin hotfix, same SDK headers), so the old branch is gone.
// The compile guard (common.h) stays: the source still compiles on the 2.2.x API.

struct Params
{
	// Task valuation
	float gold_value = 0.33f;		 // gem-equivalent value of one gold (patch 3.0: a wolf pays 4 gems + 40 gold, an elk 15 + 90: 0.22 -> 0.33 won 158/170 vs
									 // the 5 proxies (0.22: 145), h2h 20/34 and on the patch-style maps 21/34 vs 0.22; 0.44-0.66 level vs the proxies, worse vs legend_m15)
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
	// bot; if they are detrimental I will notify you". All on; each one has its own switch (0 = legend_m8's behaviour).
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
	int ward_bush_maps = 1;	   // 0 = ward bushes on every map; 1 = only on lone-monolith (contest-type) maps
	int mapdraft = 8;		   // 0 = our composition choice; sparring proxies: 1 = Mite's per-map drafts, 2 = ifish's (draft.cpp)
							   // 7 = Intercontinental Fish's per-map table (sparring proxy, session 12)
							   // 3 = ours with the top teams' choices where they beat ours (rushbait-v2, interlock, expanse; stampede with md_stampede)
	int md_stampede = 1;	   // mapdraft 3: stampede drafts the 2nd team's casters (Prism, Stellar, C&I, Ryth, Tavi) for the ring plan
	// mapdraft 6 (parameter draft): open small-team map when area >= pd_open_area and mean group distance >= pd_open_dist; Varg as the
	// 4th pick when the pack share (multi-camp groups / groups on our half) >= pd_pack; pd_counter scales the enemy-pick counters
	int pd_open_area = 5000;
	float pd_open_dist = 30.f;
	float pd_pack = 0.5f;
	float pd_elk = 0.3f; // team size 4: Ryth only with elk share >= pd_elk
	float pd_counter = 1.f;
	int pd_obj_multi = 1;	   // 1: an objective map also needs the lone gem group to be a multi-camp group (draft.cpp derive_params)
	int build_style = 20;	   // 0 = old farm builds, 1 = health/durability/treasure builds (ladder-proven),
							   // sparring proxies: 3 / 4 / 10 = ifish (frontline health then Power / Monster then Power / 3 or 4 by map),
							   //     9 = Mite (Jungle, Durability in the damage stat, Bruiser health, Power)
							   // 2 = value-model builds (tools/analysis/item_value.py): Bruiser over Power, early Treasure
							   //     on the rich farmers, survival first on Cassi & Issac, builds that never run out
							   // 12 = Nyx (patch 3.0, Oct 20): Treasure first on every body, Jungle (dmg stat) / Bruiser health, Durability, then Power dmg forever
							   // 13 = Treasure first, our survival emblems (style 2's first two), then Power dmg forever; 14 = 13 without Treasure first
							   // 11 = Intercontinental Fish (ladder #1, 45 games of Oct 19): carries open with Power in the damage stat,
							   //     tanks with Bruiser + Durability health, Home health second on the carries, then Power forever
	// Home emblem (recall takes 3 turn ends instead of 5). IC buys it second on the bodies whose first emblem is a damage
	// emblem (Stellar, Issac, Varg); it recalls 28 times a game, 44% of them capture-recalls.
	int ic_home = 0;		   // 1: Home health emblem right after the first emblem when that one is in the damage stat (derived
							   //    from the build, not the champion); 2: on every body; 3: once this body has recalled ic_home_recalls times
	int ic_home_recalls = 6;   // ic_home 3
	// Session 13 switches (all 0 = legend_m14_commit's games)
	int finish_race = 0;	   // > 0: when the team needs at most this many gems (1000 - banked - every bag we carry), a group that finishes the
							   // game alone scores by when its gems land on an altar (walk + kill + capture + bank), not by gem rate (ladder rows,
							   // Oct 19: we banked 990 at r345 and lost at r358 to a 22-gem bag while every body walked to a 66-gem group)
	int big_reward = 0;		   // > 0: groups worth at least this many gems are fought for (ladder stampede, Oct 19: we killed the 360-gem
							   // objective 4 times, the enemy captured 3 of the rewards from dead camp tiles it stood on while our bodies stayed
							   // 8+ tiles away): the threat check counts our bodies within big_reward_r of the group and needs only half the
							   // advantage, an enemy on its tiles is contested by every healthy body (no_split off), from big_reward_hp health
	int big_reward_r = 12;
	float big_reward_hp = 0.4f;
	float reward_pre = 0.f;		// > 0 (with big_reward): a ring body steps onto a dead tile of the big group once the ring kills it within this many rounds
	int big_reward_dive = 0;   // > 0: an enemy capturing a reward worth at least this many gems is denied whatever the threat (any of our
							   // bodies on any tile resets their capture: a death costs ~100 gems of farming, a monolith reward is 200-448)
	int recall_join = 1;	   // 1: a healthy body recalling to shop / heal (not a capture-recall, not a winning bag) cancels the recall when an
							   // enemy is within 7 and a healthy ally within 6 of us has an enemy within 5 (the user: fight while still able;
							   // ladder contest r26-31: our full-health Ren completed a recall as the team fight started, the other 5 lost it)
	float recall_join_hp = 0.7f;
	float burst_retreat = 1.2f;  // > 0: safety() also retreats when our health is below this x the burst (best ready spell + one hit) of the
							   // visible enemies that can step into reach (spell reach + 2): 41% of our ladder deaths (Oct 19) came from >= 60%
							   // health within 3 rounds, Cassi 31% health (220/700) stayed out next to casters and died to one area cast
	int ci_first = 0;		   // 1: the parameter draft picks Cassi & Issac first when the planned team has them (same team, lower body
							   // indices: they capture shared rewards and win claim ties; see draft.cpp param_pick)
	int rally_r = 9;		   // respond_to_alert: answer an ally's rally from at most this far (ladder contest r25-40: our Ren farmed the
							   // centre triple 11-13 tiles from the team fight, 4 of ours lost to 5 of theirs; "help that does not come")
	float rally_hp = 0.6f;	   // ... with at least this health fraction
	int pd_hor3 = 1;			   // patch 3.0: Heart of Ruin instead of Cassi & Issac at team size 3 (draft.cpp pd_score)
	// Session 14 (GOD v3, the Nyx games of Oct 20). All 0 = GOD v2's games.
	int altar_no_camp = 2;	   // 1: altar approach tiles never include a camp's spawn tile (nx50x41: the only neighbour of the one altar is a monolith
							   // 2: a camp tile is an approach tile only while that camp is dead (a dead camp's tile is standable and a body on it delays the
							   //    respawn): the altar opens when the camp dies, the group that blocks it is the team's unlock target (its gems count even
							   //    in the no-altar gold mode and the team plan may take it; nx50x41: 2 monoliths, 40,000 health, 400 gems)
							   // tile; six bodies stood next to the sleeping monolith for 1,000+ rounds trying to step onto it); an altar with no
							   // approach tile left is unusable, and with no usable altar reachable from spawn the map has no banking (World::no_altar)
	int no_altar_gold = 1;	   // 1: on a map with no usable altar the gems are worth nothing: groups score by gold only (full gold_value, no
							   // end-of-game decay), no tribute trips, the bag never makes a body cautious (the tiebreak at r2000: gold earned, then kills)
	int dash_gain1 = 1;		   // 1: at a hole crossing where every improving walking step is a hole, a ready dash that gains one field step is taken
							   // (nx61x71: two crossing holes chained diagonally; the field's path went hole -> hole and the body waited forever)
	int stall_guard = 10;	   // > 0: a walking task (farm, capture, tribute, home, flee) that stays inside a 3x3 box this many rounds without acting
							   // drops its target; a dash kit also routes without hole crossings for stall_dash_off rounds (fields rebuilt)
	int stall_dash_off = 150;
	float mid_risk = 0.f;	   // > 0: before mid_risk_until, a group near the midline costs this many rounds x (1 - |d_ally - d_enemy| / (d_ally + d_enemy))^2:
							   // both teams reach the centre groups at the same time with full teams (fragment_v3 vs Nyx: our three bodies opened on the centre
							   // elk + wolf group at r10, met their four bodies there at r26 and were all below 30% health by r58 with no capture; Nyx took a
							   // side wolf first). The term fades out linearly over the last mid_risk_fade rounds before mid_risk_until
	int mid_risk_until = 200;
	int mid_risk_fade = 50;
	int lock_hits_sdk = 0;	   // 1: an enemy-locked altar costs 2 x constants::altar_lock_hits extra steps (patch 3.0: 5 hits, was 3; the literal said 6)
	int mono_team = 0;		   // 1: a lone monolith group (one camp: 20,000 health, 200 strength, range 5 since patch 3.0; 200 gems + 300 gold a kill) is a
							   // team target on any map, like an objective group: scored with the whole living team's damage when obj_team_ready says the
							   // team clears it within obj_clear_max absorbing at most obj_absorb of its health pool, gathered outside its reach first,
							   // the nearest body alone counts its hits (obj_shield). The solo plan never clears it; 7 of the 20 Nyx maps have one and Nyx
							   // took contest_v3's twice (400 gems) while we never touched it
	int elk_exposure = 0;	   // 1: the farm model's ranged exposure (share of the time a lone ranged body is in reach of the camps it is not hitting)
							   // is 1 for groups with a camp whose range reaches past our attack range (patch 3.0: elk / golem 4, monolith 5; a
							   // body at range 3 stands inside their reach the whole time), ranged_exposure for the others
	int pd_obj_heavy = 1;	   // 1: the draft's objective map (Prism first, the caster ring) also needs the lone gem group to be heavy: total camp health
							   // >= obj_min_hp with >= obj_min_attackers camps that fight back (nx50x50: one elk + gem cluster group and 27 gold
							   // clusters per side took the caster draft: 72-1008). Same test as World::detect_objective

	int pd_front_free = 0;	   // parameter draft: at most team - pd_front_free frontliners (the pair and a ranged carry take the rest), penalty pd_front_pen
	float pd_front_pen = 0.4f;
	float pd_hor_prior = 0.4f;  // parameter draft priors re-tunable for patch 3.0 (session 14): Heart of Ruin and Cassi & Issac at any team size
	float pd_ci_prior = 0.9f;
	float pd_counter_hor = 0.8f; // per enemy bruiser pick seen (Heart of Ruin, Marcella, Vendetta): + for Heart of Ruin, - for Cassi & Issac (the pair
							   // died 148 of our 362 champion deaths in the 25 ladder games of Oct 20; the two teams without the pair beat us 9-1)
	float pd_gold_vesper = 0.f; // x the share of our half's groups that hold gold: Vesper Vale (+33% gold since patch 3.0) and Marcella (2 gold per gem)
	int pd_obj_side = 1;	   // 1: the draft's objective map also needs the lone gem group nearer to our spawn than to theirs by more than pd_obj_mid steps
							   // (session 14: nx50x50's only gem group, 2 elks + 6 gems = 72 gems, sits midway between the spawns with two altars next to it;
							   // the caster ring (Prism, Stellar, C&I, Ryth, Tavi) lost it 72-1008 twice on the ladder with 37 deaths: both teams
							   // meet there every respawn, and the casters die to Power-stacked melee)
	int pd_obj_mid = 2;
	float build_react = 2.5f;   // > 0: a reactive health emblem (Durability health, then Bruiser health) is inserted at the shop whenever our max
							   // health is below this x the biggest one-round burst (strength + focus x best spell) any enemy has shown us this game:
							   // the build answers the enemy's Power stacks (25 ladder games of Oct 20: first-round damage 33% of max health, median)
	float kill_captures = 0.f; // > 0: the body that dealt at least this share of a group's health takes its reward even if a lower-index ally claims
							   // it, and a body that dealt less than 1 - share yields to a living ally within gold_rank_d (25 ladder games of Oct 20: our
							   // Stellar took part in 354 group kills and captured 103, our Ren 233 and 221: the killer's gold went to the lowest index)
	int gold_rank = 0;		   // 1: a landed reward goes to the body (2: to the body that has bought the fewest stat points, ties by the same rank) that turns gold into the most damage (Stellar, Prism > Tavi, Cassi, Willow, Vesper >
							   // Issac, Marcella, Vendetta > Varg, Ryth > Ren, Heart of Ruin) among the living allies within gold_rank_d of it, not to the
							   // lowest index: on the ladder (25 games, Oct 20) our Ren took 35-55% of the team gold and our Stellar earned 442-544 a
							   // game (first emblem r208-661) while the top teams spread gold evenly (Stellar 1,080-2,718, first emblem r130-268)
	int gold_rank_d = 5;
	float gold_rank_margin = 5.f; // gold_rank 2: the poorest body (fewest stat points bought) collects; within this many points the type rank decides
	float burst_far = 0.f;	   // > 0: burst_retreat also counts, at this weight, enemies within burst_far_d more tiles than their reach: the opener
							   // arrives from 2-3 tiles out and kills a hurt body in 2 rounds (25 ladder games of Oct 20: our health at the first hit
							   // median 34%, death within 2 rounds in 57% of our champion deaths), so a hurt body leaves while it still can
	int burst_far_d = 5;
	int build_tail = 1;	   // build_style 2 lists end after 24-30 emblems; 1: then Power in the damage stat for ever (the five top teams of
							   // Oct 20: 950 Power-dmg emblems in 25 games; our Ren sat on 612 gold unspent on average, 13,410 on the no-altar map),
							   // 2: the Bruiser cycle for ever
	int hor_strike = 2;		   // 1: a melee champion with a damaging dash (Heart of Ruin) uses it as its fight spell in engage(): it dashes onto a tile
							   // within dash range that has the target inside the landing radius (most enemies hit first). Before, only the ranged branch
							   // set strike_dash, and mob_dash() blocks a damaging dash within strike_dash_hold of an enemy: on nx31x31_c3 vs legend_m15 our
							   // Heart of Ruin spent 391 rounds within 3 of an enemy and landed the dash on one once (62 of its 70 dashes were walking)
	int burst_dash = 0;		   // 1: Enemy::burst() counts a ready damaging dash (Heart of Ruin: 1.75 x focus) like a spell; the fight estimate, burst
							   // retreat, burst_exit, danger map and the ml2 burst_e5 input read it (before: no dash damage; build_react already had it)
	int chan_keep = 0;	   // v8: a tribute with <= chan_keep turns left is not cancelled for a stunner nearby (only if their damage kills us first):
				   // contest_v3, v7 vs legend_m15: Stellar (3,150 health, two allies next to it) cancelled a 200-gem tribute 1-2 turns
				   // before it landed (an enemy stunner came within 4), restarted the 20-turn channel and died with the bag 6 rounds later
	int death_learn = 0;	   // v8 P1-2: on its first dead turn a body classifies its death from its last 5 rounds and nudges one setting of its own
				   // (decays linearly over dl_decay rounds): burst (>= 60% health 3 rounds before, a caster within 5) -> burst_retreat
				   // x (1 + 0.2 per death, max +0.6); isolated (no ally within 6 for 3 rounds, 2+ enemies within 5) -> isolated_fight_adv
				   // +0.1 (max +0.4); channel (recalling / banking) -> recall safety radius +2 (max +4); camp (no enemy within 6) ->
				   // retreat line +0.05 (max +0.15)
	int dl_decay = 200;
	int threat_map = 0;	   // v8 P1-1: enemy threat at a group instead of the pain map: each living enemy seen t <= tm_memory rounds ago at P
				   // can be within t + 2 tiles of P now (dead ones nowhere); weight 1 / (1 + (t / 8)^2) when the group centre is inside
				   // that area + 4; net = max(0, 1 - (our hp x dps there) / (their weighted hp x dps)); cost tm_w x net rounds. The pain
				   // map marked where we lost, faded on a timer whether the enemy left or not, and was per body (plan P1-1).
	int tm_memory = 40;
	float tm_w = 20.f;
	int tail_stat = 0;	   // v8 P1-7: build_tail 1's endless Power stat from the engine, not a typed champion list: focus when focus_growth x
				   // (sum of our spell modifiers) / 8 (cooldown) beats strength_growth x (1 + 1/8 with an attack reset), else strength
	int hor_build = 0;	   // v8 P0-1f Heart of Ruin builds after the 3.0.2 hotfix (focus per shard 15 -> 12, health still +100): 1 health first
				   // (Jungle, Durability, Bruiser health) then Ren's focus emblems; 2 = 1 + a Bruiser health / focus tail instead of
				   // Power focus (its passive pays a body that stays alive at low health); 3 = Ren's list + that tail
	int gv_map = 0;	   // v8 P1-6: gold_value from the map: rho = sum(gold / respawn) / sum(gems / respawn) over the camp groups (engine
				   // rewards), value = gold_value x (rho / gv_rho_ref)^gv_exp, clamped 0.15-0.5. The review's formula (0.22 at rho 4,
				   // 0.33 at 10) gave 0.23-0.31 on 19 of the 21 official maps (their rho is 4.4-9.6, median 6.3; elk-arena 20.5): the 0.22
				   // direction measured worse (19/42), so the reference is the measured best 0.33 at the pool median.
	float gv_rho_ref = 6.3f;
	float gv_exp = 0.5f;
	int fm_mode = 0;	   // v8 P1-3 fight-model effects (bits): 1 Heart of Ruin's passive (up to +50% damage at 0 health, linear; engine
				   // constant heart_of_ruin_missing_health_damage_max_bonus) on both sides; 2 our Ren's retaliation (0.2 x focus per
				   // enemy hitting it) on our side; 4 combat()'s camp term uses each camp's engine range (elk / golem 4, monolith 5), not 3
	int hor_threat = 0;	   // v8 P1-4 enemy Heart of Ruin, narrow (bits): 1 in handle_channel() a ready dash within dash range + radius + 1 is a
				   // stunner (its landing stun cancels a tribute / recall); 2 safety()'s burst retreat adds the ready dash's landing damage
				   // within that reach (Enemy::burst() ignores it; the blunt burst_dash counted it everywhere and lost)
	int escort_bag = 60;	   // v8 P0-6: a bag of >= this many gems is not tributed at an altar where an enemy was seen within 6 in the last
				   // escort_quiet rounds (or is visible within 10 now) until min(2, living allies) healthy allies stand within 5 of it;
				   // meanwhile it posts an ESCORT alert there (the DANGER code, never posted in v7). Contest_v3: a 200-gem bag is a
				   // 20-turn channel; three tries at the central altar with enemies around, then the carrier died with the bag. 0 = off.
	int escort_quiet = 12;
	float escort_alt_w = 0.f;   // > 0: with a bag >= escort_bag, an altar where an enemy was seen within escort_quiet rounds costs this many extra
				   // steps per tribute turn (a far but quiet altar wins for a long channel; plan P0-6.4)
	int escort_r = 14;		   // allies answer an ESCORT alert from this far (healthy, not capturing)
	int alert_prio = 1;		   // v8 B9: a RALLY never replaces a fresh OPPORTUNITY / ESCORT (one shared alert slot)
	int sup_mode = 1;	   // v8 P0-4 support-aware fights (bits): 1 visible allies within sup_radius weighted by w = 1 - arrival / my time to live
				   // (0 when it would die within a round, is walking away, hurt below retreat_hp or channeling) instead of every
				   // supporting ally within 6 at full weight; 2 the backup head-count from those helpers only (no unseen claims, B10);
				   // 4 a body leaving a fight steps toward a helper that arrives within 3 rounds when that enters no more enemy reach;
				   // 8 the danger model's leave / flee threshold rises by sup_ml2_bonus x min(1, weighted helper health / max health)
	int sup_radius = 10;
	float sup_ml2_bonus = 0.2f;
	float sup_low_hp = 0.25f;   // sup_mode 4: below this share of health the body goes home, not toward help
	int hor_camp = 1;	   // v8: a damaging dash (Heart of Ruin) farming a group dashes onto a tile in reach of the target camp with >= this many live
				   // camps in its landing radius (all hit and stunned); 0 = off. Only while no enemy is within strike_dash_hold.
	float hor_shield_hp = 0.5f; // hor_strike 2: the shield waits for the strike while health >= this share and the dash is ready with an enemy in its reach
	int strike_dash_hold = 9;   // patch 3.0: a damaging dash (Heart of Ruin) is not used to walk while an enemy was seen within this many tiles
	int flee_exit = 0;		   // 1: a body walking home from inside enemy reach / an awake camp's range takes a sideways step out of it when
							   // every step toward home stays inside (nav.cpp step_field)
	float commit_hit = 2.0f;	   // > 0: the current target's score x this while we hit it in the last 2 rounds (finish what we started)
	int commit_keep = 0;	   // 1: a camp we hit in the last 2 rounds is not dropped by the join limits
	float half_grade = 0.f;	   // > 0: enemy-half risk cost x min(1, (d_ally - d_enemy) / (half_grade x (d_ally + d_enemy))) (0 = flat cost)
	int reward_claim_gone = 0; // 1: a living ally's claim that leaves a reward we cannot see means the reward was taken (shared-memory read)
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
	int learn_pain = 0;				 // pain map on/off
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
	int o2_ring = 3;			// objective group with live elks: casters (a range-4 damage/stun/area spell) cast from distance 4 and never step into camp reach
								// 3: on 60x50 or whenever our team has Prism or Tavi (the parameter draft takes them on objective maps of any size)
	int o2_ring_team = 5;		// o2_ring 3: only with this many champions per team (obj_pack4, 4 champions: ring 14/30 vs 20/30 without it; 5: 75/90 vs 51/90)
	int o2_ring_size = 0;		// o2_ring 2-3: also ring on any 60x50 objective map whatever the draft (the stampede size; 0 = only the team test of o2_ring 3, ISSUES.md #1)
								// (2 = on stampede only: elsewhere, e.g. ambush, it lost 5 of 11 changed games in session 10)
	float o2_ring_clear = 160.f; // ring plan ready when the casters' spell damage clears the group within this many rounds
	float o2_ring_share = 0.5f;	 // value share per caster
	int o2_ring_min = 2;		 // at least this many living casters (including us)
	int o2_ring_melee = 0;		 // 1: bodies that are not casters (melee kits) never take the all-in team plan while the ring is on
	float o2_ring_mindps = 0.f;	 // a caster whose spell damage per round is below this stays out of the ring plan (Ren's stun is 15.6, Cassi's 17.5)


	// Lone-monolith maps (agent contest, session 7): contest (the ladder map we lost 0-1000 with 63 deaths), its ladder copy and gold_mono_*
	int mono_plan = 1;			// detect them at init (World::mono_mode); everything mono_* needs it (0: the baseline, byte-identical play)
	float mono_share = 0.9f;	// ... when lone monoliths hold at least this share of the map's gem rate
	int mono_size50 = 2;		// ... and only on 50x50 maps (1: contest and its copies; the generated monolith-only test maps of other sizes keep legend_m10's play)
	float mono_center = 0.45f;	// ... mono_size50 2: instead of the size, every lone monolith at least this far toward the middle (min(d, 1 - d) of the spawn-to-spawn walk)
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
	int gank_bag = 25;			 // chase a visible carrier with at least this many gems (read only with P.gank, F6; unused in v8)
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
	int aoe_reach5 = 2;			// F1: an enemy area spell (ready, or cooldown unknown) threatens range + radius (5), not 4: danger
								// map, combat()'s reach/incoming, the channel stun check, engage_angle. 2: also walk-compatible
								// spells (Cassi's stun) range + 1. 3: only the danger map for routes (combat() stays at 4)
	int aoe_cast5 = 3;			// F2: our area spells aim at a tile within range whose radius catches the target (reach 5), most
								// enemies first: engage() (ranged), cast_on_nearer, px targeting reach, killable
	int open_first = 2;			// F3 (bits): 1 = after a fight step, cast a walk-compatible spell that now reaches the target
								// (Cassi's stun: walk + stun = the opener); 2 = proactive fight, no cast/attack possible this turn
								// (ranged, an opener of ours ready): when the step enters an enemy's next-turn reach, hold at the
								// edge (they step in, we cast first) for at most open_hold rounds per fight
	int open_hold = 2;			// ... rounds

	// Fight / danger model learned from real ladder games (agent ml2, session 13; experiments/wip/x_ml2_NOTES.md,
	// tools/ml/ml2_*.py). P(this body dies within 8 rounds) from a logistic model on what the body sees (ml2_model.h),
	// trained on 160 ladder games (ours vs ladder teams and top teams vs each other). All 0 = legend_m14_commit.
	float ml2_leave = 0.2f;		// a fight we can walk away from (no kill now) is dropped when P(die8) >= this
	float ml2_flee = 0.2f;		// not in reach, not fighting: walk away when P(die8) >= this and an enemy is within flee_dist
	float ml2_enter = 0.f;		// not fighting: fight when P(kill8) >= this and P(die8) < ml2_enter_die (target within reach + 1)
	float ml2_enter_die = 0.15f;
	int ml2_hold = 0;			// after a model exit, keep out (no proactive fight) for this many rounds
	float ml2_adapt = 0.f;		// > 0: learning rate of an in-match logit offset (labels: died within 8 rounds of an evaluation or not)
	float ml2_adapt_min = -2.f, ml2_adapt_max = 1.f; // ... bounds of the offset
	int ml2_cornered = 1;		// 1: ml2_leave also when combat() thinks we cannot outrun a chaser (the cornered rule would trade)
	int ml2_gb = 0;				// 1: P(die8) from the boosted trees (held-out AUC on our bodies 0.829 vs the logistic's 0.806)

	// ---- Opponent model and counter plans (F1; opponent.h, docs/CHANGES.md, docs/COMMS.md). All 0 / off = GOD v8 play.
	int opp_model = 1;			// 1: the leader classifies the enemy every om_window rounds (farmer, invader, deathball, objective, altar,
								// ambush) and broadcasts a plan id (bit 7 of bytes 0-2, replacing the stance bits; ids 0-2 = the stance);
								// every body applies the plan's preset in update_mode() after the stance block (deficit / race on top)
	int om_force = 0;			// > 0: oracle test only: the leader broadcasts this plan id from om_start on (bounds what a perfect classifier can gain)
	int om_act = 1;				// 0: classify and trace only (the plan id carries the learner's stance): calibration runs against labelled proxies
	int om_learned = 1;			// 1: classify with the fitted model (om_model.h, tools/omfit.py: none vs raider, held-out window accuracy 0.70)
								// instead of the hand-written evidence; raider -> the INVADER plan
	float om_feat_lambda = 0.8f; // ... forgetting of the smoothed features (the fit used 0.8)
	float om_p_on = 0.6f;		// ... P(raider) to switch to the INVADER plan
	float om_p_off = 0.4f;		// ... and below which it switches back
	int om_window = 20;			// rounds per classification window (also the invasion counter's window)
	int om_start = 100;			// no plan change before this round (both teams farm their own half in the opening)
	float om_lambda = 0.6f;		// exponential forgetting of the archetype scores per window (a fired change detector halves it)
	float om_thresh = 0.35f;	// smoothed score an archetype needs to become the plan
	float om_margin = 0.1f;		// ... and its lead over the current one
	float om_drop = 0.6f;		// the plan returns to the stance learner when its score falls below om_drop x om_thresh
	int om_min_windows = 3;		// minimum windows per plan, unless the change detector fires
	float om_cus_k = 0.15f;		// CUSUM on the contact level: slack per window
	float om_cus_h = 0.6f;		// ... alarm level
	float om_cus_alpha = 0.2f;	// ... running mean rate
	int om_cus_warm = 3;		// ... windows before it may fire
	int om_obj_lump = 100;		// an enemy bank of at least this many gems at once is objective evidence (a monolith pays 200)
	int om_heavy = 60;			// a group of at least this many gems (or a monolith) is heavy (objective evidence when taken unclaimed)
	float om_prior = 0.f;		// weight of the enemy-draft prior (0 = off)
	float om_k_invader = 1.f;	// preset magnitude per counter plan (opponent.cpp preset_of: directions)
	float om_k_deathball = 1.f;
	float om_k_objective = 1.f;
	float om_k_altar = 1.f;
	float om_k_ambush = 1.f;
	int om_sight = 0;			// 1: every body posts an enemy it sees on our half as DANGER in the alert slot (when no RALLY / OPPORTUNITY /
								// ESCORT younger than 6 rounds is there); groups within om_sight_r of a fresh one cost om_sight_cost rounds.
								// A scoring cost, not a routing wall: the old DANGER zone (alert_radius 8, routes) measured worse
	int om_sight_r = 5;
	float om_sight_cost = 25.f;
	int om_sight_age = 8;		// rounds a sighting stays fresh

	// ---- Draft-memory plan (F2; dmplan.h, docs/COMMS.md). 0 = no draft memory written or read (v8).
	int dm_plan = 0;			// 1: the draft writes the versioned plan on every draft turn; Brain::init() reads and checks it

	// ---- Ward coordination (F3). 0 = v8 warding.
	int ward_plan = 0;			// 1: a ready ward goes to a draft-plan spot within reach that watches our task group, capture tile or banking
								// altar and no ally ward covers (two bodies on one group: the lower index takes the enemy-facing approach,
								// the higher the bush); bush spots first only under the AMBUSH plan, while standing still (capture, tribute,
								// farming in reach) or on lone-monolith / objective maps (unconditional bush warding lost: ward_bush_maps)
	int ward_enemy = 0;			// 1: enemy wards seen are remembered by owner (one active ward per champion); a carrier with >= ward_avoid_bag
								// gems pays ward_avoid_cost rounds for a group or altar within 6 of one (their vision reveals the bag)
	int ward_avoid_bag = 30;
	float ward_avoid_cost = 8.f;

	// ---- Anchors and the Prism banker (F4). 0 = v8.
	int anchors = 0;			// 0 off; 1 / 2 anchors; 3 = by team size (1 with 3 champions, 2 with 4-5). Ranking every body computes alike from
								// the team's types: Vesper, Marcella, Prism, then the lowest base health; the top living ones are anchors
	float anchor_trib = 0.6f;	// anchor: tribute_min x this (banks smaller bags)
	int anchor_bag_caution = 20; // anchor: avoids even fights it can leave while carrying this many gems (everyone: bag_caution 40)
	float anchor_ehp = 3.f;		// anchor: enemy_half_penalty x this
	float anchor_ml2 = 0.1f;	// anchor: danger-model leave / flee threshold (everyone 0.2)
	float anchor_home_w = 0.5f; // anchor: rounds of cost per tile between a group and its altar (two anchors: two different altars)
	int handoff = 0;			// 1: a non-anchor capturing a reward with an anchor within handoff_r skips its capture-recall; once the anchor
								// stands on the group it steps off (one collector, the region never empties, the timer keeps running)
	int handoff_r = 4;
	float handoff_bonus = 1.5f;	// anchor: value x this for a reward an ally holds for it
	int prism_bank = 0;			// 1: our Prism (focus grows with its bag) holds bags: banks only a winning bag, in the endgame or below prism_bank_hp
	float prism_bank_hp = 0.35f;

	// ---- Chain farming (F5). 0 = v8's capture-recall triggers (health < cap_recall_hp 0.61, gold after the capture >= 60, a bankable bag).
	int chain_farm = 0;			// 1: after a capture, recall only when hurt, or when the home trip (bank + shop) is worth more per round than the
								// best target within chain_r (scored as usual): keep farming from capture to capture while healthy
	float chain_hp = 0.5f;		// fighters' health trigger (anchors keep cap_recall_hp)
	float chain_bag = 1.5f;		// fighters bank from bank_min x this (anchors x 1; the Prism banker never recalls to bank)
	int chain_gold = 150;		// shopping trigger with chain farming on
	int chain_r = 12;			// groups within this many tiles compete with the home trip
	float chain_bank_w = 0.5f;	// home trip value: chain_bank_w x (bag + gold_value x gold) over (recall + rest + walk back)

	// ---- Smaller items (F6). 0 = v8.
	int gank = 0;				// 1: a healthy body moves to intercept a visible enemy carrier with >= gank_bag gems within gank_r (its path home
								// predicted from their spawn's distance field), when our side near it is not weaker (gank_margin)
	int gank_r = 10;			// ... 14 for the hunter role (the FARMER counter plan)
	float gank_margin = 1.f;
	int deny_altar = 0;			// 1: when the enemy has >= deny_altar_at banked or the race says they finish first, the lowest-index living non-anchor
								// body waits within 2 of the altar they use most (tributes we saw; else their spawn's nearest), locking it
	int deny_altar_at = 850;
	int watchdog = 1;			// 1: after 3 turns in a row that threw, a minimal safe turn (hit an adjacent enemy, else step toward spawn) (g8h: on, as GOD v10 fc05b5d)

	// ---- g8h (session 17): later GOD fixes ported by hand onto GOD v8 + opponent model (experiments/top2/g8h_port.md). 0 = g8's play.
	// (The init fuel cuts of f0c0c9c in world.cpp have no switch: same results, less fuel.)
	int hop_score_start = 40000; // ff8514f: crystal / island comparisons near spawn only with this much fuel left (they spilled turns: road_of_riches)
	int hop_score_floor = 30000; // ff8514f: ... and the hop loop stops below this
	int pocket_fix = 3;			// 14f1bc8 (bits): 1 = no walk leads home (a hole pocket entered by a dash): dash to the landing tile nearest home when going
								// home, else recall; step_field skips its fallback search from such tiles; 2 = dash out as soon as the dash is up, any task
	int pocket_guard = 1;		// bb4: in such a pocket the hole crossings stay on, and pocket_idle rounds without an attack or a capture end in a dash out
								// or a recall (islands: dash kits stood 268-1,079 rounds in pockets)
	int pocket_idle = 12;		// bb4: ... idle rounds before that
	int cap_timeout = 1;		// cfe377c: 15 rounds on a reward without it landing: blacklist the group 40 rounds and step off (yellow_brick_road deadlock)
	int osc_fix = 1;			// 9618135 + 1d5510c: danger-detour hold, A-B-A-B breaker, no-progress detector (15 rounds), ml2_hold 4, post-flee target skip
	int real_channel = 1;		// bb4: an enemy counts as recalling only from its 2nd sighting recalling on one tile in consecutive rounds (recall spammers)
	int draft_guard = 1;		// fc05b5d: a draft pick that throws falls back to the first legal pick of a fixed list (else the engine picks at random)
	int init_resume = 1;		// 15ed961: resumable map init (the group loop yields below init_fuel_floor and goes on next turn; bodies walk to the centre)
	long long init_fuel_floor = 30000; // 15ed961: ... the group loop stops below this much fuel
	long long init_turn_floor = 60000; // 15ed961: ... and the turn the init finishes plays the full logic only with this much fuel left

	// ---- Sparring proxies (testing only, docs/TESTING.md; never on in a submission): a fixed playing style, optionally switching at
	// set rounds, built from existing GOD mechanisms. 1 farmer (stays home, avoids fights), 2 invader (PUSH: their half free, deny,
	// lower fight bar), 3 deathball (2 + the whole team follows the lowest living body: P.style 1's blob), 4 objective rusher (heavy
	// groups and monoliths x pxs_obj_mult), 5 bush ambusher (farms standing in bushes, bush wards), 6 altar denier (body 0 camps the
	// other team's altar with a lock; the rest farm).
	int pxs_style = 0;
	int pxs_style2 = 0;			// style from round pxs_switch (0 = no switch)
	int pxs_switch = 0;
	int pxs_style3 = 0;			// style from round pxs_switch2
	int pxs_switch2 = 0;
	float pxs_obj_mult = 3.f;
	float pxs_raid_mult = 3.f;	// styles 2 / 3: groups on the other team's half are worth this much more (a raid, not just a lower penalty)
	int pxs_deny_bodies = 2;	// style 6: bodies 0 .. n-1 camp the other team's altars
	// ---- god2 load (session 17): draft and builds from the top-team study (experiments/top2/an_draft.md, an_items.md).
	// mapdraft 8 = role-slot draft from the engine designs (6 = god.zip's map-parameter draft); build_style 20 = health-weighted builds by
	// role (2 = god.zip's value-model builds).
	float g2l_gold_bonus = 0.33f; // the bonus_gold passive's extra gold share (rules: Vesper +33%) in the carry slot's score
	float g2l_min_hp = 700.f;	  // draft: no champion with base health below this unless it has a dash, a heal or a shield (D2)

	// ---- god2 bank (session 17): bank small and often, keep bags off fights, recall safely (experiments/top2/mod_bank.md). Study rules
	// (experiments/top2/an_economy.md 3.1-3.3 + rules 2-3, an_weak.md E4 / R11, gap_g8.md 4.4 + finding 7): g8 banked 11.7 times a game at
	// 35 gems against the top teams' 25.2 at 62, lost 109 gems a game in bags at death, and on contested-altar maps hardly banked at all
	// (road_of_riches 0.7 banks a game, first bank r1471). All runtime state: walking distances, visible enemies, altar locks seen. Every
	// g2b_* rule needs the master switch; g2b 0 = bots/god2's play.
	int g2ab_n = 0; 			// god2 in-bot A/B (g2ab.h): variants = on/off combinations of bank (bit 0), deny (bit 1), fight (bit 2), mid (bit 3); 0 = all on
	int g2b = 0;				// master switch (0: every rule below off, the bot plays exactly like bots/god2)
	// E2 / C9 bank cadence (an_economy 3.2: ifish banks a bag >= 20 with an altar within 5 walking steps of the capture 81%, >= 40 within 10
	// 70%, >= 80 at any distance; cm banks almost every bag >= 40 anywhere; completed tributes W 26.5 vs L 15.1 a game, P 0.82)
	int g2b_tier = 1;			// the bag a bank trip needs is min(g8's bank_min(trip), the tier below for the walk to the altar)
	int g2b_t5 = 20;			// ... altar within 5 steps: 20 gems (g8's tribute_near 5 still banks any bag there)
	int g2b_t10 = 40;			// ... within 10: 40 (g8: tribute_min 54 after r150)
	int g2b_t20 = 51;			// ... within 20: 51 (g8: 54 + 1.74 per step beyond 12, up to 68)
	int g2b_tfar = 80;			// ... farther: 80, never more than ~80 gems away from an altar without heading to bank (g8: up to 108)
	int g2b_capbank = 1;		// right after a capture: a bag that meets the tier at the altar nearest the capture tile skips the capture-recall and
								// banks there first (tribute() walks it once the reward lands); a hurt or rich body (it recalls anyway after the bank,
								// home_trip) only when that altar is no farther than the spawn's altar route. g8 recalled home with it: 66% of our banks
								// came after a recall home, 16 tiles / 20 rounds after the capture vs their 10-11 / 11-14 (an_resources)
	float g2b_capbank_hp = 0.35f; // ... and never below this health share (C4: heal first)
	int g2b_chain = 1;			// C9: at the end of a capture chain (no target, or the best one respawns more than g2b_chain_wait rounds after we
								// could reach it) a bag of g2b_chain_min+ is banked at an altar within min(g2b_chain_far, wait / 2) steps
	int g2b_chain_min = 10;
	int g2b_chain_wait = 10;
	int g2b_chain_far = 20;
	// E9 channel safety (an_economy 3.3: completed channels had their closest enemy at a median 10-12 tiles; nobody cancels without an enemy
	// within 8; the bank-often teams never cancel bags of 20 or less: damage does not interrupt a tribute, a stun, a death or a new lock does)
	int g2b_e9 = 1;				// a tribute of more than 2 turns (bag > 20) starts only with no visible enemy champion within g2b_e9_r: at the altar
								// the body holds at most g2b_e9_hold rounds, then leaves that altar for g2b_e9_block rounds (g2b_block_cost steps)
	int g2b_e9_r = 7;
	int g2b_e9_lock_r = 8;		// R11: once an enemy lock was seen this game, 8 (a lock placed from 2 tiles cancels the channel)
	int g2b_e9_hold = 4;
	int g2b_e9_block = 25;
	int g2b_block_cost = 30;
	int g2b_cancel = 1;			// handle_channel: a tribute of 20 or less always finishes; a longer one is cancelled only with an enemy within
								// g2b_cancel_r and our max-health sum within g2b_cancel_r below theirs (or their damage kills us before it lands).
								// g8 also cancelled for any ready stunner within 4 (our 200+ tributes: done 40%)
	int g2b_cancel_r = 6;
	// F7 contested altars (gap_g8 4.4: altar_unsafe() refused an altar about as close to their spawn as to ours where an enemy was seen in the
	// last 8 rounds unless an ally stood within 5, bag_needs_escort() held bags of 60+ for two escorts: road_of_riches 0.7 banks a game,
	// hooks 0.5, elk_arena 0.2, stampede 0.5; bags lost 230 a game on road_of_riches)
	int g2b_f7 = 1;				// altar_unsafe = a bag > 20 and a visible enemy within the E9 radius of the altar (no map-position rule, no escort
								// ally); bag_needs_escort never holds a bag (the E9 start check replaces it)
	// R11 altar locks (an_weak R11 / E10: IFish, cm, Pantheon lock 2.9-5.6 times a game; pbg and Nyx never)
	int g2b_locks = 1;			// enemy locks are remembered per altar (seen locked / seen clear, forgotten after g2b_lock_mem rounds): a locked
								// target costs g2b_lock_cost steps (another altar wins when at most that much farther); at a locked altar the body
								// clears it (5 basic attacks: submit_gems hits the lock) only with no enemy within g2b_lock_clear_r
	int g2b_lock_cost = 6;
	int g2b_lock_mem = 150;
	int g2b_lock_clear_r = 8;
	// C4 recall gate (an_weak E4: the top teams recall 4-5 tiles from us, 7-8.5 times a game, 74-91% complete; we 1.2 a game within 5)
	int g2b_recall = 1;			// safe_to_recall: no enemy seen in the last 2 rounds within g2b_recall_r (g8: 7); below g2b_low_hp with an enemy within
								// g2b_recall_r, go_home steps toward a healthy ally within g2b_ally_r (not toward the enemy), else walks home
	int g2b_recall_r = 5;
	float g2b_low_hp = 0.35f;
	int g2b_ally_r = 8;
	// Bag defence (an_economy rule 5 / 8: camps killed pbg's Prism 7 times with 100+ bags; Pantheon's Prism lost 132 gems a game)
	int g2b_bigbag = 100;		// a body carrying this many gems takes no fight it can walk away from (sure kills and cornered trades only), flees an
								// outmatching group g2b_bigbag_flee earlier (outmatch bar + this) and never hits a monolith or golem group
	float g2b_bigbag_flee = 0.3f;

	// ---- god2 deny (session 17): deny the enemy's big tributes and hunt gem carriers (experiments/top2/mod_deny.md). Rules P1-P3 of
	// experiments/top2/an_draft.md, R1 / R4-R6 and E3-E4 of an_weak.md, R4 of an_items.md. Every g2d_* rule needs g2d_on; 0 = bots/god2's play.
	// Gap (gap_g8.md 4.4 / 7 / 8.11): we place 0.1 altar locks a game against the top teams' 2.0, are within 8 of 76% of the Prism's 200+
	// tributes yet stun or lock 7%, and their recalls within 5 of us complete 67-71%.
	int g2d_on = 0;				// master switch
	int g2d_lock_from = 100;	// P3: from this round every body buys one altar lock (10 gold) at each spawn visit (or dead turn) when it holds none,
								// before its shards (god2 bought a spare only after its first emblem, from the gold the shards left): the body that
								// sees a big tribute should have one. -1 = god2's rule
	int g2d_trib_bag = 60;		// P2/R1: a visible enemy channelling a tribute of at least this many gems (>= 6 turns) is a deny target
	int g2d_near_bag = 150;		// R1: so is one carrying at least this many within 1 of an altar before it starts (only a lock answers that one)
	int g2d_lock_r = 2;			// a lock is placed on an altar within this Chebyshev distance (GameRules: "within two tiles"; no engine constant)
	int g2d_slack = 0;			// the lock / stun must land by our turn (remaining channel turns - 1 + this); 0: also safe when we act after the tributer
	float g2d_lock_power = 0.5f; // P2(a): a lock holder walks to the altar while our max-health sum near the tributer (us, allies within 6 of it or of us)
								// is >= this x theirs within 6 of it: the lock lands from 2 tiles and cancels at once, the body need not win a fight
	float g2d_stun_power = 0.9f; // P2(b): a stunner walks in only from this ratio (the study rule: our max-health sum within 6 >= 0.9x theirs)
	float g2d_deny_hp = 0.35f;	// responders need this share of their health (the finisher alarm ignores the health, power and bag gates)
	int g2d_alert = 1;			// R1 comms: a body that sees a deny tribute posts OPPORTUNITY on the altar tile (an altar is a wall, no enemy stands there,
								// so readers tell it from the tributer-position OPPORTUNITY); a reader with a lock or a stun answers it
	int g2d_alert_age = 20;		// ... rounds a reader keeps the call (it cannot see the bag or the channel time; it re-judges on sight)
	int g2d_alert_reach = 14;	// ... readers answer from at most this many steps to lock / stun range (x 1.5 when their banked score >= g2d_fin_score)
	int g2d_fin = 1;			// finisher alarm: their banked score + the tributer's bag reaches the winning score: every body that can land a lock,
								// a stun or a hit in time converges on it
	int g2d_fin_score = 700;	// ... readers of a call (bag unknown) answer like that from this enemy score
	int g2d_value = 1;			// R4/E4/R6/P1 target value: value = kill gold + bag (the killer's team banks the bag 61-83% of the time); combat()
								// targets by value per health (the px key: health x kill gold / value), best_in_reach the same
	float g2d_pair_mult = 2.f;	// R6: Cassi & Issac die together: a kill on either removes both bodies (replaces god2's +60 / -150 health terms)
	float g2d_iso_mult = 1.25f;	// R6: ... the member with no other enemy within 3 first (the pair stands ~7 apart, partner at ~78% health)
	int g2d_commit_bag = 150;	// R4/E3: a carrier (not channelling) with this many gems is engaged proactively only when our bodies within 6 deal its
								// health within 2 turns (IFish lost 10 of 19 big bags in its losses, but carriers fed when the burst was short)
	int g2d_prism_bag = 60;		// P1: an enemy whose focus grows with its bag (passive gem_focus: Prism) carrying this many gems ...
	float g2d_prism_mult = 3.f;	// ... is the focus target (value x this) while >= 2 of our bodies are within 6 of it and <= 1 of its allies within 3
	int g2d_prism_avoid = 1;	// P1: ... and with a spell up we start no fight that walks inside its range 4 unless our bodies there kill it within 2
								// turns (one stun-nuke at 300-599 gems hits for ~1,140, more than a base Vesper's health)
	int g2d_recall = 1;			// R5: a genuine recall (World::perceive drops recall spammers) in our reach this turn is the target and is hit ...
	float g2d_recall_adv = 0.6f; // ... down to this fight advantage (god2: 0.9 for any channel): any damage cancels the 5-turn recall

	// ---- god2 fight (session 17): the strongest teams' fight rules (experiments/top2/an_fights.md section 5, gap_g8.md finding 1;
	// report experiments/top2/mod_fight.md). With an enemy within 8 (30% of our alive time) g8 farmed 4.4% of rounds vs their 15.9% and
	// walked 74% vs 52%: combat() took the turn on any visible enemy (chase out of reach at adv 1.3, flee at 0.873 / 0.8, ml2 exits at
	// 0.2) and group_score's threat veto dropped the group. Local ratio = our side's health sum within 8 (us + visible allies) / the
	// enemies' (visible or seen within g2f_seen rounds, not on their spawn): mh = max health (items), ch = current health. Every rule
	// reads only what the body sees; g2f_on 0 = god2's play.
	int g2f_on = 1;				// master switch
	int g2f_seen = 2;			// enemies seen this many rounds ago (stepped into a bush) still count in the local ratio
	int g2f_engaged_r = 2;		// "in a fight": we chose to fight, or took champion damage, within this many rounds
	// C8 farming under pressure (study 2a: the top teams keep farming 58% of arrivals; at an enemy within 4 they fight from 0.9 and
	// leave below 0.6). A body working a camp (a live camp of its target in attack range or hit within 2 rounds, or capturing a reward)
	// and not in a fight:
	int g2f_farm = 1;			// enemy g2f_far_d or more away that cannot reach us next turn: keep farming (no chase, no walk-away)
	int g2f_far_d = 5;
	float g2f_farm_fight = 0.9f; // enemy within 4 (or in reach): fight at ch >= this (if the start gate allows) ...
	float g2f_farm_leave = 0.6f; // ... leave below this ...
	int g2f_finish_r = 3;		// ... in between keep farming only when the group dies (the capture lands) within this many rounds
	// C1 start gate (study h2 / headline 2: starts below 0.67 lose games, logit -0.96; 0.67-0.87 pay only when they would start anyway):
	int g2f_start = 1;			// god2's fight decisions that start damage (not in a fight) need mh >= g2f_start_mh and own health >= g2f_start_hp ...
	float g2f_start_mh = 0.87f;
	float g2f_start_hp = 0.5f;
	float g2f_start_min = 0.67f; // ... or mh >= this and (the enemy reaches us next turn, the target channels, or it is below g2f_start_low)
	float g2f_start_low = 0.35f;
	// C3 commit (study headline 3 / t1: the retreat trigger is own health; fighting nets +12 to +58 per 100 at ch >= 0.6):
	int g2f_commit = 0;			// in a fight with an enemy within 4: keep fighting while own health >= g2f_commit_hp and ch >= g2f_commit_ch,
	float g2f_commit_hp = 0.35f; // else step out of their next-turn reach (cornered: hit back), unless the target dies this turn
	float g2f_commit_ch = 0.6f;
	float g2f_ml2 = 0.35f;		// ml2 exits (god2 0.2) when the rules keep a fight or a farm: only from this P(die within 8 rounds)
	// C7 chase (study h8: kill 40% of chases on targets below 35%, 12% above 70%; median 4 rounds, p90 10):
	int g2f_chase = 1;			// walking after a retreating target out of our reach: only below g2f_chase_hp of its health, at most
	float g2f_chase_hp = 0.5f;	// g2f_chase_max rounds, not at their spawn, and never with a second enemy within 8 of us
	int g2f_chase_max = 10;
	// C9 after a local win (study g1: winners farm 15% of the next 20 rounds and take 0.8 groups; "push" falls after a win):
	int g2f_win = 1;			// our kills > our losses within g2f_win_r tiles over the last g2f_win_rounds rounds: no walking toward an
	int g2f_win_r = 10;			// enemy out of reach (unless it dies this turn); groups within g2f_win_r skip the threat veto and score
	int g2f_win_rounds = 10;	// x g2f_win_bonus (take the nearest camp group)
	float g2f_win_bonus = 1.3f;
	// Group choice (gap F1/F6): group_score's threat veto with the local view and allies that will be there (visible within 8 of the
	// group, or claiming it or a group within 8 of it): skip a group only when our current-health sum there is below g2f_grp_ratio of
	// the enemies seen there (god2: hp x dps of the allies within 8 now vs target_threat_adv 1.49). Our target while we work it is
	// never vetoed (C8 decides when to leave it).
	int g2f_grp = 1;
	float g2f_grp_ratio = 0.8f;
	// Calm (session 17, after a trace of the module: the C8 farm-through applied to 2.7% of contact turns, since our bodies are walking,
	// not hitting a camp, when an enemy shows up; 47% of contact turns were god2's reflex: a proactive fight at adv >= 1.3 walks after
	// any enemy within 9, a lone body flees from any enemy within 5 unless 1.5x stronger. G2A replays: 144-217 walk rounds per body
	// into fights vs their 58-89). An enemy that cannot reach us next turn does not take the turn: no walk toward it unless we hit it
	// next turn (d <= our reach + g2f_calm_slack), it is killable, channels, or hits an ally within 3 of us; no pre-emptive walk-away
	// unless our local max-health ratio is below g2f_calm_out. In reach, god2's fight-back / flee rules decide as before.
	int g2f_calm = 1;
	int g2f_calm_slack = 1;
	float g2f_calm_out = 0.9f;
	int g2f_rally_farm_d = 4;	// calm: a body working a camp answers a rally only this close (god2: rally_r 9 for every body)
	int g2f_rally_r = 6;		// calm: any other body from at most this far

	// ---- god2 mid (session 17): the v53 "middle" bit ported onto god2 (ladder, v53 factorial vs the top 20: +109 gem margin, deaths 8.9 vs
	// 12.7). Gap (gap_g8.md 4.3 / finding 6): middle-band gems 126 vs 594 a game, first middle capture r391 vs r134, golems 0.42 vs 2.64
	// captures a game; their groups are hit 28 rounds after the respawn, ours 37-49. Every g2m_* rule needs g2m_on; 0 = bots/god2's play.
	int g2m_on = 0;				// master switch
	float g2m_value = 0.6f;		// value x (1 + g2m_value x mid^2), mid = 1 - |d_ally - d_enemy| / (d_ally + d_enemy) (walking steps; 1 = the midline)
	float g2m_mid = 0.5f;		// groups with mid >= this are "middle" for the threat veto: ...
	float g2m_threat = 1.0f;	// ... the recent-enemy veto needs this advantage there (god2: target_threat_adv 1.49) ...
	int g2m_ally_r = 12;		// ... with the allies within this many tiles of the group counted (god2: 8). The fight module's veto replaces both.
	float g2m_half_grade = 0.3f; // enemy-half risk graded by depth (god2: flat: one step past the midline cost as much as their spawn)
	int g2m_wait = 35;			// rounds a body waits on arrival for a respawn (god2: max_wait / obj_max_wait 18)
	int g2m_golem = 1;			// golem groups (5,000 HP, 120 strength, 36 gems) get the team plan (join limits off, obj_team_ready, gather rules)
};

#ifdef LEGEND_RUNTIME_PARAMS
// Training builds only (tools/rl/a100/es_a100.py): the values are defined in a generated params_rt.cpp, so a new
// candidate recompiles one file instead of the whole bot. Submitted builds use the constexpr defaults above.
extern const Params P;
#else
inline constexpr Params P{
};
#endif
