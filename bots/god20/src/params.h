// Every tunable weight and threshold lives here so variants can be generated for self-play tuning.
#pragma once
#include "common.h"
// GOD v8 (plan P0-2a): patch 3.0 values only. GOD v5.1-v7 chose 15 settings and the ml2 weights by SDK_HAS_HOR (patch 3.0 vs the sprint
// handbook's pre-patch rules); the platform runs patch 3.0 (+ the 3.0.2 Heart of Ruin hotfix, same SDK headers), so the old branch is gone.
// The compile guard (common.h) stays: the source still compiles on the 2.2.x API.

struct Params
{
	// Task valuation
	float gold_value = 0.5f;		 // gem-equivalent value of one gold (patch 3.0: a wolf pays 4 gems + 40 gold, an elk 15 + 90: 0.22 -> 0.33 won 158/170 vs
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
	float fight_margin = 1.4f;		 // engage proactively when our kill time beats theirs by this factor
	float fight_back_margin = 0.873f; // when they can already hit us, fight back unless this outmatched (ES: 0.75 -> 0.873)
	float cornered_margin = 0.7409f;	 // chasers we cannot outrun: hit back unless the advantage is below this (ES: 0.45 -> 0.634)
	float far_enemy_weight = 1.0f;	 // visible enemies beyond reach+2 count this much in the fight estimate
	int ally_spell_dps = 1;			 // count allies' spells in our damage (else basic attacks only)
	int spawn_heal_bonus = 1;		 // on our spawn, count one more health bar (we heal fully)
	int bag_caution = 40;			 // carrying this many gems, avoid even fights we can escape
	int backup_radius = 5;			 // allies (seen, or claiming a camp) this close count as backup
	float isolated_fight_adv = 1.35f; // alone, start a fight only at this advantage (or a sure kill) (ES: 1.6 -> 1.428)
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
	int mapdraft = 6;		   // 0 = our composition choice; sparring proxies: 1 = Mite's per-map drafts, 2 = ifish's (draft.cpp)
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
	int build_style = 2;	   // 0 = old farm builds, 1 = health/durability/treasure builds (ladder-proven),
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
	int ally_kit = 0;		   // patch 3.0.4: 1 = an ally's damage on a camp group from its kit (engine modifiers, dps_on()'s arithmetic) instead of
							   // the typed 3.4 / 2.0 / 1.5 x focus (Stellar / Cassi / the rest) of ally_dps_on() (ISSUES #39)
	int pocket_fix = 3;	   // patch 3.0.4 (bits): 1 = a body where no walk leads home (a hole pocket entered by a dash) dashes to the landing tile with
							   // the shortest walk home when it goes home, else recalls; step_field skips its fallback search from tiles its field cannot
							   // reach and from such pockets (it burned every turn's fuel there: 149 lost turns for a Vesper on nx100x100); 2 = in such a
							   // pocket the dash takes us out as soon as it is up, whatever the task (after fights, not on a reward to capture)
	int build_kit = 0;		   // patch 3.0.4: 1 = the build from the kit (Brain::build_from_kit: damage stat by what a shard pays, melee opens with
							   // Jungle health, ranged with Monster, the linked pair skips Treasure) instead of the per-champion lists of build_for()
	int build_stat = 0;	   // patch 3.0.4: 1 = the build list's focus / strength shards in the stat the kit pays most for (engine numbers, brain.cpp
							   // Brain::init) when one pays >= build_stat_margin x the other; else the typed list
	float build_stat_margin = 2.f;
	float build_stat_targets = 1.5f; // camps hit by an area spell / a damaging dash / Varg's splash, hits Ren takes a round
	int pd_stat = 3;		   // patch 3.0.4: 1 = draft priors re-measured on engine 3.0.4 (pd_pri_*, pd_ci_prior, pd_hor_prior) + pd_stat_k x ln(relative
							   // stat power now / on 3.0.4) from the engine's champion_designs (draft.cpp stat_prior), the "one ranged carry" bonus for
							   // any caster (v8: Stellar only), and the first pick = the frontliner with the best prior (v8: Ren); 2 = the same
							   // without the pair +0.3 and ranged-carry +0.2 bonuses (the measured values already hold them)
	float pd_stat_k = 1.f;
	float pd_stat_gems = 10.f;	   // gems Prism carries in the power estimate (prism_focus_per_gem each)
	float pd_stat_missing = 0.3f; // Heart of Ruin's health lost in the power estimate (its passive)
	float pd_pri_ren = 1.f;	   // pd_stat priors (defaults = v8's table)
	float pd_pri_stellar = 0.95f;
	float pd_pri_varg = 0.62f;
	float pd_pri_ryth = 0.6f;
	float pd_pri_prism = 0.36f;
	float pd_pri_tavi = 0.33f;
	float pd_pri_vendetta = 0.3f;
	float pd_pri_marcella = 0.2f;
	float pd_pri_vesper = 0.12f;
	float pd_pri_willow = 0.1f;
	// pd_stat 3: the draft-value model (draft.cpp model_value): weights of the logistic fit on 3.0.4 games (tools/draftmodel/fit.py; features:
	// effective health / 1000, basic damage / 50 a round, Varg's splash, spell damage (+ heal) / 50 a round, area damage / 50, stuns, a dash,
	// ranged, gold bonus, Ren's retaliation, bodies; interactions with the map's pack / elk / gold shares, team size 3, spread, monoliths)
	float pd_w_hp = 0.4321f;
	float pd_w_basic = 0.5442f;
	float pd_w_splash = 0.0000f;
	float pd_w_spell = 0.0000f;
	float pd_w_area = 0.4831f;
	float pd_w_stun = 0.1242f;
	float pd_w_dash = 0.1981f;
	float pd_w_ranged = 0.0000f;
	float pd_w_gold = 0.0565f;
	float pd_w_ret = 0.0000f;
	float pd_w_bodies = -0.8000f;
	float pd_w_area_pack = 0.5061f;
	float pd_w_stun_elk = 0.0239f;
	float pd_w_gold_gold = 1.4666f;
	float pd_w_bodies_small = -0.4046f;
	float pd_w_dash_dist = 0.0034f;
	float pd_w_ranged_mono = 0.0060f;
	float pd_w_hp_mono = 0.f;	   // monolith-map interactions (0 = the model of the first fit)
	float pd_w_basic_mono = 0.f;
	float pd_w_spell_mono = 0.f;
	float pd_w_area_mono = 0.f;
	float pd_w_area_close = 0.f;  // crowded maps (tiles per champion below 50 x 50 / 10): area damage and stuns x (close - 1)
	float pd_w_stun_close = 0.f;
	float pd_obj_ring = 0.75f;	   // objective map: + x (the pick's spell damage from 4) / (the best pick's) (v8: Prism / Tavi +0.75)
	float pd_obj_tank = 0.4f;	   // objective map: a melee pick with an area stun (v8: Ryth +0.4); other melee picks - pd_obj_melee (v8: Ren / Varg -0.6)
	float pd_obj_melee = 0.6f;
	float pd_open_ret = 0.5f;	   // open small-team map: - for retaliation (v8: Ren -0.5), + for splash (v8: Varg +0.45)
	float pd_open_splash = 0.45f;
	float pd_cw_ranged_melee = 0.f; // counters (pd_stat 3): x our pick's feature x the enemy picks' melee basic damage / burst / ranged count
	float pd_cw_stun_melee = 0.f;
	float pd_cw_hp_burst = 0.f;
	float pd_cw_dash_ranged = 0.f;
	int pd_sub_from = -1;	   // measurement only (patch 3.0.4 screen), -1 = off: the parameter draft plans as usual on a virtual roster where our
	int pd_sub_to = -1;	   // pd_sub_to pick stands for pd_sub_from, and a planned pd_sub_from is picked as pd_sub_to (draft ids: 0 Ryth, 1 Vesper,
							   // 2 Vendetta, 3 C&I, 4 Stellar, 5 Prism, 6 Marcella, 7 Willow, 8 Ren, 9 Varg, 10 Tavi, 11 Heart of Ruin): "Tavi wherever v8
							   // drafts Stellar", every map rule intact. A probe of champion value under a new balance, never a shipped draft
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

	// v9 adaptive layer (opp.h / opp.cpp; guide chapters 17-19). Every switch 0 = GOD v8's games, unchanged.
	// The leader (body 0, which also runs while dead) keeps an opponent model from evidence every body shares, picks a team plan and
	// broadcasts it in bit 7 of shared-memory bytes 3-5; every body applies that plan's preset at the end of update_mode().
	int opp_plan = 0;			  // 1: run the opponent model and apply its plan (needs alert_refresh 0: bit 7 of byte 2 becomes the contact bit)
	int opp_presets = 1;		  // 1: apply the preset of the broadcast plan; 0: compute and broadcast it only (dry run for traces)
	int opp_window = 30;		  // rounds per evidence window (opp_sim.py: 20-round windows of bursty sightings were too noisy)
	float opp_ema = 0.5f;		  // weight of the newest window in the running indices
	int opp_dwell = 2;			  // windows a plan is kept before an ordinary switch (an urgent switch skips the wait)
	float opp_contact_hi = 0.35f; // share of rounds with an enemy deep in our half (any body): an invading opponent ...
	int opp_consec = 2;			  // ... for this many consecutive windows (simulated: 9% false alarms per game at a 0.08 share)
	float opp_contact_stay = 0.20f; // once in DEFEND / PUNISH, stay while the contact index is at least this (tests F, G: one quiet window flipped it)
	float opp_contact_lo = 0.10f; // ... at most this: a farming opponent
	float opp_depth = 0.8f;		  // contact = an enemy with dist_home + 2 < opp_depth x dist_away (1.0: anywhere on our half)
	float opp_cusum_k = 0.2f;	  // change detector on the per-window contact share: drift allowance ...
	float opp_cusum_h = 0.8f;	  // ... and alarm level (a sudden invasion switches at once, not after opp_dwell windows)
	int opp_home_deaths = 2;	  // hard evidence: this many of our deaths on our half inside one window switch to DEFEND / PUNISH at once
	float opp_punish_bal = 0.5f;  // invaded but winning the trades (EMA of their deaths - ours per window >= this): PUNISH, else DEFEND
	int opp_loss_n = 2;			  // EVADE after this many lost team fights (2+ of our deaths within 4 rounds) ...
	int opp_loss_h = 100;		  // ... within this many rounds (an EMA over windows forgot the first loss before the second: test E)
	int opp_race_margin = 60;	  // they finish the gem race this many rounds before us: HUNT (trades even) or RACE (trades lost); once in
								  // HUNT / RACE we stay while they finish first at all (hysteresis: lumpy bank events made it flip, test B)
	int opp_race_from = 150;	  // no race plan (HUNT / RACE / DENY) before this round: the first bank events are too lumpy to project
	float opp_rate_ema = 0.3f;	  // EMA weight of the newest window's banking pace (slower than opp_ema: banks land in lumps)
	float opp_even_bal = -0.25f;  // trades count as even (HUNT, not RACE) down to this balance: a net loss decays below it in ~3 windows
	int opp_deny_at = 850;		  // their banked gems from which DENY applies when they also finish first
	float opp_dive_prior = 0.15f; // initial contact index per enemy diver (melee or dash champion) beyond the second
	int fix_my_dash = 1;		  // v9 tasks T01: combat()'s my_burst also counts our own ready damaging dash (Heart of Ruin's landing, focus x dash_mod), as
						  // burst_vs() already does (0 = v8: a Heart of Ruin judged its fights without its main spell)
	int fm_buffs = 0;		  // T09 (bits): 1 shields (a visible enemy's shield adds to its effective health, ours to ours: engine buff data),
						  // 2 a stunned enemy deals x0.7 in the exchange and nothing to us this round
	float farm_ema = 0.f;	  // T09d: > 0: learning rate of a multiplier (0.7-1.5) on incoming_on() from the camp damage we actually took vs predicted
	int risky_persist = 0;	  // T14a: the "risky" bank needs an enemy within 9 for this many rounds in a row (or health < 60%); 0 = one sighting
	int near_age_cap = 0;	  // T14b: a sighting's age shortens enemy_near_d by at most this many tiles (hold_spell_dist reads it); 0 = unbounded
	float bandit_discount = 0.f; // T11: > 0: every stance value x (1 - this) at each window close before the update (0.2: a window 10 windows back weighs 10%)
	int draft_guard = 1;	  // T13: a draft pick that throws falls back to the first legal pick of a fixed list (else the engine picks at random)
	float heavy_value = 1.f;	  // value x this for heavy groups (a monolith or >= om_heavy gems); the sparring objective style uses x pxs_obj_mult
	int ally_defend = 0;		  // 1: join a fight at the hit-back bar (fight_back_margin) when a visible ally within the target's reach + 1 took damage since
						  // our last turn and we have at least ally_defend_hp of our health (the vetoes below the ladder still apply)
	float ally_defend_hp = 0.5f;
	int deny_ramp = 0;		  // 1: OPPORTUNITY answers (their tributes / carriers) ramp with their banked total (UPG-4: radius 12 -> 16, health gate 0.40 ->
						  // 0.25 between deny_ramp_from and + deny_ramp_span) instead of the step at endgame_alarm (800)
	int deny_ramp_from = 600;
	int deny_ramp_span = 250;
	int opp_force = -1;		  // >= 0: that plan for the whole game (test of a preset with a perfect detector; 1 DEFEND, 2 PUNISH, 3 HUNT, 4 RACE, 5 EVADE, 6 DENY)
	int opp_mask = 127;		  // bit p: plan p may be entered (ablation of single plans; 127 = all seven)
	int contact_bit = 1;		  // with opp_plan: a body that sees an enemy on our half sets the contact bit for the leader
	int enemy_comp_init = 0;	  // 1: read the enemy champion types at init (the API: champion_name() reads live champions without vision)
	int safety_range = 1;		  // 1: safety() counts a camp while we stand inside its engine range (elk / golem 4, monolith 5) instead of 3
	int watchdog9 = 0;			  // v9 (> 0): after this many consecutive turns that threw an exception, play a minimal fallback turn (main.cpp)
	int ring_reach = 0;		  // 1: the objective ring counts an area spell's reach as range + radius and aims it at a tile next to the camp
							  // (v8 compared the cast range alone with 5, so since patch 3.0 the ring rarely qualified on elk / golem groups)
	int tavi_str = 0;			  // 1: Tavi builds strength instead of focus (estimate from the kit numbers: ~5.6 vs ~1.75 damage per round per shard);
							  // the default build style 2 switches her whole list, the proxy styles 3/4/10/12 keep the copied teams' Tavi lists
	// Sparring personas (for building A/B opponents only; inactive by default): between spar_from and spar_to the bot plays PUSH,
	// multiplies the enemy-half cost by spar_half, adds spar_deny and spar_fight, and with spar_db follows the leader (deathball).
	int spar_from = 0;
	int spar_to = 0;
	float spar_half = 1.f;
	float spar_deny = 0.f;
	float spar_fight = 0.f;
	int spar_db = 0;
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
	float ml2_flee = 0.35f;		// not in reach, not fighting: walk away when P(die8) >= this and an enemy is within flee_dist
	float ml2_enter = 0.f;		// not fighting: fight when P(kill8) >= this and P(die8) < ml2_enter_die (target within reach + 1)
	float ml2_enter_die = 0.15f;
	int ml2_hold = 0;			// after a model exit, keep out (no proactive fight) for this many rounds
	float ml2_adapt = 0.f;		// > 0: learning rate of an in-match logit offset (labels: died within 8 rounds of an evaluation or not)
	float ml2_adapt_min = -2.f, ml2_adapt_max = 1.f; // ... bounds of the offset
	int ml2_cornered = 1;		// 1: ml2_leave also when combat() thinks we cannot outrun a chaser (the cornered rule would trade)
	int ml2_gb = 0;				// 1: P(die8) from the boosted trees (held-out AUC on our bodies 0.829 vs the logistic's 0.806)

	// ---- Opponent model and counter plans (F1; opponent.h, docs/CHANGES.md, docs/COMMS.md). All 0 / off = GOD v8 play.
	int opp_model = 0;			// 1: the leader classifies the enemy every om_window rounds (farmer, invader, deathball, objective, altar,
								// ambush) and broadcasts a plan id (bit 7 of bytes 0-2, replacing the stance bits; ids 0-2 = the stance);
								// every body applies the plan's preset in update_mode() after the stance block (deficit / race on top)
	int om_force = 0;			// > 0: oracle test only: the leader broadcasts this plan id from om_start on (bounds what a perfect classifier can gain)
	int om_act = 1;				// 0: classify and trace only (the plan id carries the learner's stance): calibration runs against labelled proxies
	int om_learned = 0;			// 1: classify with the fitted model (om_model.h, tools/omfit.py: none vs raider, held-out window accuracy 0.70)
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
	int watchdog = 1;			// 1: after 3 turns in a row that threw, a minimal safe turn (hit an adjacent enemy, else step toward spawn)

	// ---- tools/teamplan (TEAMPLAN.md section 9; the test copy bots/_tp_v10 only, tools/teamplan/prepare_v10.py). 0 = v10.
	int tp_focus = 0;		 // 1: the fight target's value = teamplan focus.h kill_value (its bag + kill gold + the farming lost while it is dead,
							 // bodies from the SDK's pick structure) over its health, in place of v10's 60 (+ 60 for the pair) + bag
	int tp_bag = 0;			 // 1: the proactive fight bar rises with our bag (bag.h fight_bar: x (1 + bag / 60))
	int tp_timing = 0;		 // 1: the edge hold (open_first & 2, ranged) and the melee approach step into an enemy's reach only when we act again
							 // before it (timing.h; this and next round's priorities of the bodies in sight, team from sdk_my_team())
	int tp_tiebreak = 0;	 // 1: tiebreak mode (tiebreak.h): when both projected finishes lie beyond the round limit, a bag up to tp_tb_cap is
							 // kept (no bank trip, no small on-the-way banks) while no enemy is within tb_safe_dist; v10's endgame rule banks it
	int tp_tb_cap = 60;		 // ... the risk cap
	int tp_own = 0;			 // 1: soft group ownership (assign.h): the draft writes the OWN block (draft memory 8..), a body's own groups score
							 // x (1 + tp_own_bonus)
	float tp_own_bonus = 0.25f;

	// ---- GOD v12: tools/mapintel + draft memory version 2 + the step-7 DL tables + the live bytes (MAPAnalysis.md, TEAMPLAN.md 11,
	// docs/DRAFT_MEMORY.md). The draft side (mi_draft.cpp) writes the 1,024-byte image under the fuel guard; the champion side (mi_game.cpp)
	// reads it. Every use in play is behind its own switch (0 = GOD v10's play).
	int mi_dmem = 1;		  // 1: the draft writes draft memory v2 (mapintel's plans, TEAM, OWN, BODY, CONT, CODE, ENEMY, NAV, DEBUG, L)
	int mi_pick = 3;		  // 1: the pick value adds mi_prior_w x the strong teams' pick prior (LEARNED; ln(rate + 0.05), centred)
							  // 2 (GOD v18): only on maps with a monolith or an objective group (the draft's own map analysis: F.mono, MP.objective)
							  // 3: 2 + on the maps known_maps.h knows (the 40 old maps: the map's own strong-team pick rate)
	float mi_prior_w = 1.0f;
	float mi_own = 0.f;		  // > 0: groups the OWN block gives this body score x (1 + mi_own) (soft ownership, teamplan assign.h)
	int mi_own_maxg = 30;	  // ... only on maps with at most this many groups (on v10 the switch lost on maps with more than 30)
	float mi_next = 0.f;	  // > 0: after a capture, the step-7 next-target model's two best groups score x (1 + mi_next) / (1 + mi_next / 2)
	int mi_next_for = 120;	  // ... for this many rounds after the capture (or until the next one)
	float mi_open = 0.f;	  // > 0: before our first capture, plan 1's first targets for this body (BODY bytes 9-11) score x (1 + mi_open)
	int mi_live = 0;		  // 1: the 8 shared bytes in teamplan's live layout (live.h: claims as place codes, the team alert with its place
							  // vocabulary, beats, bag flags); 0: GOD v10's own layout (comms.h)
	int live_bag_flag = 25;	  // ... the bag flag: carrying at least this many gems (teamplan bag.h's hunt threshold)
	int mi_capture = 1;		  // 1: a shared reward goes to a near ally with a gold bonus first (teamplan capture.h mode 1, LEARNED); v15 2: to the ally it is worth the most gold to (Vesper Vale's bonus on the gold, Marcella's 2 gold a gem when she banks)
	int ic_build = 0;		  // GOD v13: Intercontinental Fish's builds on the carries (brain.cpp build_for): Treasure first on a gold-bonus kit,
							  // Monster, Jungle health, then Power in the damage stat for ever; supports keep the value-model lists
	int mi_body = 0;		  // 1: the BODY block's bank bag and retreat health (econ model, LEARNED) replace tribute_min / retreat_hp

	// ---- GOD v14 (Oct 24, the user's report: "stuttering, not moving or moving randomly, walking away from the altar with good gems,
	// not competing with enemies the right way, monoliths not killed, wards thrown at random tiles"). Measured in 80 games of v13
	// against Intercontinental Fish's draft (tools/analysis/behav.mjs, LEGEND_TRACE IDLE lines): 7.9% of our body-turns idle with
	// no enemy within 5, short back-and-forth walks 32.6 per 1000 alive body-rounds (the 600 ladder replays' teams 11-15), 518
	// wards a game with 6% on a bush (ladder 150, 61-65%). Every switch 0 = GOD v13.
	int fz_dead = 1;		  // 1: farm_group: a live camp whose reach tiles are all dead tiles of its own group (gem-fields' tTt rings) or whose
							  // off-group reach tiles cannot be stepped to: step onto the dead tiles (standable) instead of standing still
							  // (2,700 idle turns in 80 games: melee bodies two tiles from a live camp inside a ring of dead ones)
	int fz_dash = 0;		  // bits. 1: at a hole crossing with the dash ready but no landing that gains a step, walk around instead of waiting
							  // (the wait rule waited for ever with a ready dash); 2: Heart of Ruin's strike dash (held near enemies) may cross
							  // when no walking step improves and no enemy is within 5 (dash kits: 3,300 of 4,600 out-of-range idle turns)
	int fz_chase = 4;		  // > 0: a fight whose target's distance has not shrunk for this many rounds while out of reach is dropped and the
							  // target left alone for fz_chase_off rounds unless it comes into reach (eight: Ryth at 35% health with 37 gems
							  // chased a Vesper Vale walking away at the same speed for 13 rounds, then walked back)
	int fz_chase_off = 12;
	int ward_v14 = 1;		  // 1: wards go into bushes: the best bush tile in placement reach (2), scored by our target group, our altar trip, the
							  // other team's approach and recent sightings; a ward already in a bush near us stays; with no bush in reach the
							  // ward stays where it is while it is within ward_hold of us (no re-throw every 10 rounds 2 tiles ahead)
							  // 2: as 1, but with no bush in reach v13's forward ward (2 tiles toward their spawn) instead of holding
	int ward_hold = 10;
	int ward_open = 0;		  // > 0 (ward_v14): a bush tile needs at least this many walkable neighbours (of 8) to take a ward: a ward occupies its
							  // tile and blocks steps into it, and allies cannot see our ward (v14 games: 801 of 1,282 blocked moves were into an
							  // ally's ward, mostly in one-wide bush corridors)
	int fz_engage = 4;		  // > 0: a fight we were not in last round, with the target out of reach, starts only when the target is within this
							  // many tiles (fights are judged on everything within 9; bodies at the 7-9 band flipped fight / farm every round,
							  // one step in, one step back: v14's traced games, 2,000 such back-and-forth body-rounds in 80 games)
	int fz_wardblock = 0;	  // 1: the wards we see (ours and theirs) count as blocked tiles in the step searches (v13: 646 of 1,171 blocked
							  // moves were into a ward tile, most of them the other team's)
	int fz_osc = 0;			  // > 0: walking back and forth: over the last fz_osc rounds (a walking task, no attack or cast, no enemy within 5,
							  // off spawn) at least 60% of them moved and we end within 1 tile of where we were: drop the target (blacklisted
							  // fz_osc_bl rounds) or the bank / home trip, and re-plan (v13: 32.6 such walks per 1000 alive body-rounds, the
							  // ladder teams 11-15; 23% of target switches went back to the target left within 20 rounds)
	int fz_osc_bl = 20;
	int mono_v14 = 0;		  // 1 (with mono_team): monolith groups whose other camps are harmless are team targets too, judged with their own
							  // limits (mono_clear_max, mono_absorb: bodies rotate in front and heal between turns). The 600 ladder replays'
							  // teams kill 1.44 monoliths a game on monolith maps (first kill r530-900); v13 dropped every one as too heavy
	float mono_clear_max = 70.f;
	float mono_absorb = 1.5f;

	// ---- GOD v15 (Oct 25, the user's 20 ladder games of v14: 0-20, banked 197 a game against 1,110). Every switch 0 = v14.
	// Measured on those games (docs/strategy_v2/22_GOD_V15.md): with an enemy within 8 we farm 4-8% of rounds, they farm 15-19%; 233 of our
	// 260 back-and-forth walks have an enemy within 8 (theirs 39 of 89); middle-band captures 3.6 a game (74 gems) against 20.1 (634).
	int g15_calm = 5;		  // bits. Contact calm: an enemy is a threat only when it can hit us next turn (its reach + 1), closed in on us
							  // since our last turn (within 8), or appeared within g15_new_r. 1: the pre-emptive flee exits (alone / half the
							  // team dead, outmatched, ml2_flee) need a threat; 2: safety()'s burst retreat counts threats only; 4: a proactive
							  // fight walk (out of reach, no kill, not channelling) needs a threat or the target within our reach + 1;
							  // 8: a rally is answered only when we are not working a group (no camp hit in 3 rounds, no capture) or it is
							  // within g15_rally_near
	int g15_new_r = 6;
	int g15_rally_near = 5;
	int g15_fwalk = 0;		  // > 0: fight-walk budget: after this many turns in a row walking to a fight (or a rally) without a hit, proactive fights
							  // and rallies are off for g15_fwalk_off rounds (in reach, a kill, a channel or a tribute still fight). Traced on corners
							  // (v14 vs IC's draft): 1,522 fight-task walks with an enemy within 8, 671 of them at an unchanged distance with no hit
							  // within 3 rounds (same-speed chases the target-keyed fz_chase misses when the target changes)
	int g15_fwalk_off = 12;
	int g15_lock = 15;		  // bits. Altar locks: 1: every body carries a lock (bought at the first shop visit, not after the first emblem);
							  // 2: a visible enemy tribute of >= g15_lock_bag gems is posted at its altar tile with the ticks it has left (4 free
							  // bits: bit 7 of bytes 2-5, units of 4 rounds); 4: lock run: a body carrying a lock that reaches placement range
							  // (2) of that altar before the tribute lands walks there and places the lock (it cancels the channel); 8: within
							  // range, place the lock on such an altar even when we do not see the tributer (bush)
	int g15_lock_bag = 60;		// (the top teams ignore tributes under 60 gems: 11% hit, 1% locked; an_fights rule 7); 16: rallies do not overwrite a posted tribute
	float g15_lock_hp = 0.35f;	// lock run: health share needed
	int g15_lock_r = 24;		// lock run: at most this many steps
	int g15_lock_maxbag = 60;	// lock run: not with a bag this big (bank it)
	int g15_build = 0;		  // 1 (build_style 2): every body but Cassi & Issac and Willow buys Treasure first in its damage stat, then Jungle and
							  // Durability in health, Monster, then Power in the damage stat (the ladder teams' carries: Treasure, Jungle and Durability
							  // passives; with mi_capture 1 Vesper Vale also takes the shared captures: the gold funnel)
	int g15_stance = -1;	  // >= 0: the team stance is fixed (0 spread, 1 grouped: camps farther than group_radius from the allies' camps cost
							  // group_far_w rounds a tile; the ladder teams keep 3+ bodies together through r100-600, our isolated deaths 4.5 a
							  // game against their 1.4); -1 = the stance bandit (v14)
	// ---- GOD v16 (the user's second bot, Oct 25): "farm gold first, then go near their altar and kill all their members, then take our most
	// powerful champion near their spawn and kill them when they spawn again". Every switch 0 = GOD v15.
	int g16_camp = 0;		  // 1: hunt-and-camp plan from round g16_hunt_from: the g16_hunt_bodies strongest bodies (by kit: Vendetta, Heart of
							  // Ruin, Vesper Vale, Marcella, Varg, Ryth, Tavi, ...; every body ranks alike) wait at the altar the enemy banks at
							  // (most tributes seen, else the one nearest their spawn) and fight whoever comes (locks on); once g16_camp_dead
							  // enemies are dead at once, the strongest one waits g16_camp_d tiles from their spawn (out of reach of a body
							  // healing on it) and takes each one that steps out; the other bodies farm and bank as usual
	int g16_hunt_from = 300;
	int g16_hunt_bodies = 3;
	int g16_camp_dead = 2;
	int g16_camp_d = 5;
	int g16_camp_hold = 150;	// rounds the camp lasts after it started while any enemy is still dead
	float g16_hunt_hp = 0.55f;	// health share to hunt or camp (below it the body heals and banks as usual)
	int g16_hunt_bag = 40;		// a body carrying this many gems banks first
	float g16_fight_k = 0.85f;	// hunters' fight bars x this (bolder at the altar and at their spawn)
	int g16_gate = 0;			// 1: hunt and camp only while the fights go our way: our deaths so far at most theirs + g16_gate_margin (else v15 farming)
	int g16_gate_margin = 0;
	int g16_carry_camp = 0;		// 1: the camper is the gold-funnel carry (Vesper Vale first in the kit order: with mi_capture it holds the most items)
	int g16_only_camp = 0;		// 1: no hunt at their altar: every body farms like v15 until our fights leave g16_camp_dead of them dead, then the camper camps

	// ------------------------------------------------------------------------------------------------ GOD v17 (Oct 25)
	// Mite's bot starts a recall at the end of every turn and cancels it at the start of the next (1,100 recalls a game): every body looks
	// like it is channelling a recall. v15 posts a "recalling with a bag" enemy as a team OPPORTUNITY and walks up to 12 tiles to it.
	int g17_fakerec = 3;		// > 0: after this many fake recalls seen (an enemy recalling on consecutive rounds at different tiles: a real recall
								// cannot move), enemy recalls are never a channel (no OPPORTUNITY post, no stuck-target logic)
	int g17_bait = 1;			// 1: our bodies end every free turn recalling and cancel it on the next (Mite's bait); 2: only carrying >= g17_bait_bag
	int g17_bait_bag = 20;
	int g17_squad = 0;			// > 1: squads of this many bodies by team index farm their leader's (lowest living index) claimed group
	int g17_squad_until = 2000;	// ... until this round
	int g17_squad_bag = 1000;	// ... a follower carrying this many gems picks its own task (banks)
	int g17_shop_cap = 0;		// TESTING ONLY (never in a submission): > 0 stops buying shards after this many (a handicapped body for
								// 'play from behind' screens: IC carries 2.6x our items at r400)
	// ------------------------------------------------------------------------------------------------ GOD v18 (Oct 26, patch 2.0.0 / sprint 3)
	// Treasure 20% -> 10% gold, Monster 10% -> 15% camp damage; new families: Capture (capture 5 -> 3 turns when any capturer owns it as the
	// capture begins), Tribute (tribute time -33%), Greed (25 shards combine into 35 shards of stats), Prospector, Hunter, Skirmish, Collectors.
	int g18_treasure = 0;		// 1: every Treasure shard of the build list becomes Monster in the same stat (a second Monster run is dropped)
	int g18_capture = 0;		// 1: a Capture emblem (damage stat) for the gold-bonus body (the funnel's capturer); 2: for every body
	int g18_capture_pos = 0;	// ... at this emblem slot (0 = first)
	int g18_greed = 0;			// 1: the endless Power tail (1.2 shards of stats a shard) becomes Greed (35 for 25: 1.4) in the same stat
	int g18_tribute = 0;		// 1: a Tribute emblem (damage stat) for the gold-bonus body after its first emblems (slot g18_tribute_pos)
	int g18_tribute_pos = 2;
	int g18_osc = 6;			// > 0: a body back on the tile it stood on two turns ago while descending a field (A-B-A) descends plainly (no danger
								// / stuck detour, no sideways exit) for this many rounds (treasure-box: a 125-gem bag walked in place for 200+ rounds)
	int g18_capt_slack = 0;		// ... the recall lands this many rounds after the countdown ends (probe PROBE18: the reward lands at round + timer)
	int g18_capt_timer = 0;		// 1: recall-while-capturing times the recall on the engine's capture countdown (capture_state().timer: 3 with
								// a Capture emblem) instead of the fixed 5-turn capture time
	int g18_fast_init = 1;		// 1: cheaper World::init_static, same tables: one camp_groups() call instead of two, the altar-approach camp lookup
								// only for approach tiles that are camp tiles (islands: ~255k fuel, 2.5 rounds), the 1-wide hole crossings from
								// shifted bitboards instead of a per-hole scan (islands, dash kits: ~180k), no cluster loop for one-camp groups
	int g18_rich = 0;			// 1: a harmless group worth at least g18_rich_gems is joinable like a heavy pack (up to max_join extra bodies), joiners credited
	int g18_rich_gems = 80;		// g18_rich_share of its value (IC takes vault's 343-gem centre and the-line's 161 with the whole team in the opening)
	float g18_rich_share = 0.8f;
	int g18_calm_mono = 0;		// 1: on lone-monolith maps (World::mono_mode) contact discipline is off: g15_calm 0, ml2_flee and fz_engage below;
								// 2: also on objective maps (World::obj_mode)
	float g18_mono_ml2_flee = 0.2f;
	int g18_mono_fz_engage = 6;
	// ---- GOD v20 (IC study, Oct 26: 205 games against Intercontinental Fish). IC farms with its whole team as one pack until ~r400: the
	// pack clears a group in a few rounds, one body (Marcella) captures while the rest walk on, and the pack holds the rich middle groups
	// and the altar next to them, retaking each group on its respawn (corners: G27, G26, G29, G28 every ~60 rounds, all banked at the
	// central altar). Our bodies spread one per group, meet the pack one at a time and leave or die.
	int g20_pack = 0;			// 1: followers farm the group the pack leader claims (pk_leader); the leader plans with the pack's damage
	int g20_pack_until = 400;	// ... until this round
	int g20_pack_r = 10;		// allies within this many tiles of the leader are its pack (their damage, their health in the threat checks)
	int g20_pack_rew = 6;		// a follower may still take a reward this many steps away (the capture rules pick who), else only the leader's group
	float g20_pack_risk = 1.f;	// with 3+ pack bodies: enemy-half penalty and mid risk x this
	int g20_pack_min = 2;		// the pack plan needs at least this many bodies within g20_pack_r of the leader (else farm as before)
	float g20_safe = 0.f;		// v3 (> 0): the pack skips a group whose camps would deal more than its spare health / g20_safe while it clears it
	int g20_leash = 0;			// v3 (> 0): in pack mode, no walking after a target more than this many steps deeper in their half than ours
	int g20_farm_first = 0;		// 1: a body that hit a live camp in the last 2 rounds keeps farming instead of walking to a fight that cannot reach it
	int g20_adapt = 0;			// 1: the pack plan only while an enemy pack was seen in the last g20_adapt_mem rounds (2: or an ally's fresh DANGER alert)
	int g20_adapt_n = 3;
	int g20_adapt_mem = 60;
	int g20_worthy = 0;			// > 0: the pack forms only for groups worth at least this many gems (or a monolith); smaller ones are farmed alone
	int g20_worthy_rich = 0;	// > 0 (with g20_worthy): also any group worth this many gems, harmless or not
	int g20_pack_maps = 0;		// 1: the pack plan only on the maps of pack_maps.h (sprint-3 maps where it beat v18 locally); 2: always there,
								// adaptive (g20_adapt) elsewhere
	int g20_split = 0;			// > 0: a reward worth this many gems is captured by every body that gets onto its tiles (split, banked in parallel)
	int g20_hold = 3;			// v2: followers wait this many rounds next to the leader's dead group for its next choice
	int g20_modes = 0;			// 1: also on lone-monolith and objective maps (their own team plans otherwise: mono_follow, obj_team)
	int g17_opp_r = 12;			// respond_to_alert: an OPPORTUNITY (tributing / recalling carrier) is answered from this far (v15 12; endgame 16)
	int g17_ally_fresh = 1;		// with g17_bait: an ally seen recalling is not counted as channelling (the start / cancel flags are not visible)
	int g15_sight = 0;		  // 1 (with om_sight 1): shared sightings from every body and its ward anywhere on the map, not only on our half (each
							  // body sees only itself and its own ward; the alert slot is the team's only shared view): the nearest enemy we see
							  // when no RALLY / OPPORTUNITY / ESCORT is fresh; readers: groups within om_sight_r of a fresh one cost om_sight_cost

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
};

#ifdef LEGEND_RUNTIME_PARAMS
// Training builds only (tools/rl/a100/es_a100.py): the values are defined in a generated params_rt.cpp, so a new
// candidate recompiles one file instead of the whole bot. Submitted builds use the constexpr defaults above.
extern const Params P;
#else
inline constexpr Params P{};
#endif
