// Runtime strategy knobs (session 16): the few parameters an in-bot ladder A/B test switches per game. Everything else stays in
// the constexpr Params P. Each game plays one variant, chosen in Brain::init from a hash of the map, our side and the enemy draft
// (strat_pick), so every ranked or unranked game is a sample and tools/live/variant_of.py recovers the variant offline.
#pragma once
#include <cstdint>

struct Strat
{
	int variant = 0;
	long long bits = 0; // strategy bits in play (strat_apply; 64-bit since bit 31)
	// Middle control: ~46% of a pool map's gem rate sits in groups about as far from both spawns (tools/live/mapzones.mjs); top
	// teams capture 14.4 of those a game against our 4.6 (459 gems vs 149). Our scoring gave them away: any group with a comparable
	// enemy force seen nearby was vetoed (target_threat_adv 1.49 with only allies within 8 counted) and one step past the midline cost
	// the full enemy-half penalty.
	float mc_value = 0.f;	  // > 0: value x (1 + mc_value x mid^2), mid = 1 - |d_ally - d_enemy| / (d_ally + d_enemy) (walking steps)
	float mc_mid = 0.5f;	  // groups with mid >= this are "middle" for the threat rule below
	float mc_threat = 0.f;	  // > 0: the recent-enemy veto on a middle group needs only this advantage, allies within mc_ally_r counted
	int mc_ally_r = 12;
	float half_grade = -1.f;  // >= 0: overrides P.half_grade (enemy-half risk graded by depth: a group just past the midline costs little)
	// Global boldness: the ES-tuned caution was learned against our own bots; on the ladder caution lost (v13 power gate 5-45).
	float threat_adv = -1.f;  // >= 0: overrides P.target_threat_adv everywhere
	float ml2_leave = -1.f;	  // >= 0: overrides P.ml2_leave
	float ml2_flee = -1.f;	  // >= 0: overrides P.ml2_flee
	float half_penalty = -1.f; // >= 0: overrides P.enemy_half_penalty
	// Farming fix (rules study): farm_group hit the lowest-health camp first, so a group's gem clusters died while its elk kept hitting
	// (+320 camp damage on 1 elk + 2 clusters, +960 with 6 clusters for a solo body); objective groups already went attackers first.
	bool atk_first = false;
	// Chase discipline: our walks into fights average 17.2 rounds against the top teams' 11.4 (tools/live/fightwalks.mjs); a target that
	// stays out of reach for chase_max rounds without the gap closing is let go and not chased again for chase_ban rounds.
	int chase_max = 0;
	int chase_ban = 10;
	// Builds: >= 0 overrides P.build_style (17 = Durability health first, Treasure only on a gold-bonus kit).
	int build_style = -1;
	// Gold routing: a reward is taken by the nearby body that earns the most extra gold from it (Vesper +33% of its gold; Marcella 2 gold
	// per gem she banks); others leave it to that body (route_gold_d: the router must be within this of the reward).
	int route_gold_d = 0;
	// Oscillation fix: bodies stepped back and forth between two tiles (A-B-A: 14 rounds per body per unopposed game, 90 on gem_fields;
	// 41 vs the top teams' 18 in ladder games). Keep the danger detour, and break any A-B-A-B by dropping the danger preference for a
	// few rounds.
	bool osc_fix = false;
	// Convoy: the team farms as one force. Heavy groups need 3-6 bodies (k* = sqrt(c S H / (D W)): elk groups 2-3, golems 4-6 at base);
	// our per-body planner left them half-killed and slow (gem_fields unopposed 1223 rounds vs the top teams' 666 contested), and our
	// spread bodies die outnumbered (deaths 2 enemies vs 1.3 allies). One leader picks targets by team value / (walk + team kill
	// time), the others go straight to it, heavy groups wait a few rounds outside reach for the team, one body captures (gold bonus first)
	// while the rest move on. The old blob (P.blob_until) broke on claim rules and a formation step (A-B-A oscillation).
	bool convoy = false;
	float convoy_hyst = 1.3f; // the leader keeps its target unless another scores this much more
	int convoy_gather_max = 6; // rounds a heavy group waits for the team before the first hit
	// Deaths are our largest measured loss (13% of body-time with the walk back, ~1,050 gold a game to the enemy); we die outnumbered
	// (2 enemies vs 1.3 allies within 6). Grouped stance always: bodies farm near each other (group_radius). Team danger alerts: a body
	// that sees an enemy force posts it and the others route around it (alert_radius; measured worse locally where no one hunts).
	bool force_grouped = false;
	int alert_radius = -1; // >= 0 overrides P.alert_radius
	// First strike: in ladder engagements where we were the stronger force, hitting first left our deaths 0.22 vs their 0.53; when they hit
	// first the same fights were even (0.40 vs 0.42). strike_first (A6): hold just outside their reach for our opener (>= 0 overrides P).
	int strike_first = -1;
	// Enemies standing on their own spawn do not guard camps outside their reach (gem_fields: both 71-gem groups sit 5 tiles from a spawn
	// across a hole line; our bodies vetoed them every time the other team stood at home).
	bool spawn_threat_off = false;
	bool flee_hold = false; // after a flee, no proactive fight for 3 rounds (measured: local 47.5%, no less dithering)
	int squad = 0; // SV.convoy: squad size (bodies by index: 0-1, 2-3, 4 for 2); 0 = the whole team
	bool open = false;	   // bit 65536: near-first opening (pre-init walk to the nearest camp, spawn-distance cost until bb_open_until)
	float mid_risk = 0.f; // bit 131072: midline groups cost rounds in the opening (20 x mid^2, fading by mid_risk_until)
	bool farm_thru = false; // bit 262144: working a camp, do not chase an enemy that cannot reach us next turn
	bool stand = false;		// bit 524288: hit back when in reach down to bb_stand_back, leave a stronger group early only below bb_stand_out
	bool farm_hold = false; // bit 1048576: a healthy body working a camp flees only once an enemy is within its basic reach
	bool stepin_shot = false; // bit 2097152: a ranged body that walked into range casts its attack reset and shoots (walk + reset + shot)
	bool no_stepin = false;	  // bit 4194304: no step into an enemy's next-turn reach unless we can hit this turn (hold at the edge, open_hold rounds)
	bool convert = false;	  // bit 8388608: no chase of a retreating target; after a nearby kill, farm on (threat check on enemies seen now only)
	bool smart_flee = false;  // bit 16777216: in their reach with no adjacent tile out of it, hit back instead of fleeing
	bool melee_combo = false; // bit 33554432: a melee body hits, resets and hits again before it steps away (flee swings, exec_hit_first)
	bool early_shield = false; // bit 67108864: self shields go up when an enemy champion is within 5, not only below 90% health
	bool safe_rally = false;  // bit 134217728: rally / call answers path around enemy reach until within reach + 2 of the call
	bool mid_hold = false;	  // bit 268435456: golems get the team plan and bodies wait longer at respawning groups (max_wait / obj_max_wait 35)
	bool bank_more = false; // bit 536870912: bank sooner and nearer (tribute_min 32, tribute_near 8, bank at the nearest altar before a recall)
	bool kite = false;		// bit 1073741824: in their reach a ranged body shoots first and dashes away; a strike-dash kit may dash to escape
	bool contest = false; // bit 2^31: with nothing to farm, stage outside enemy reach 6 tiles from the richest reachable group (the team gathers)
	bool real_channel = false; // bit 2^32: an enemy counts as recalling only from its second sighting recalling on one tile (recall spammers)
	bool no_chase = false; // bit 2^33: never walk toward an enemy out of our reach unless killable, channelling, carrying 30+, or on an ally
	int bb_off = 0;	  // bit 32768: every bb4 play module off (formation, call register, territory, wards, stance prior, wall hops)
	int bb_draft = -1; // bit 16384: the archetype draft (else P.bb_draft)
};

inline Strat SV{};

std::uint32_t strat_hash(std::uint32_t w, std::uint32_t h, std::uint32_t camps, std::uint32_t side, std::uint32_t enemy_mask);
void strat_apply(int variant);
int strat_pick(); // Brain::init: the variant of this game (P.ab_variants > 0), else P.ab_force

// A bb4 module switch: the param unless this game's variant turns the bb4 play modules off (ladder A/B against the god baseline).
#define BB(name) (SV.bb_off ? 0 : P.name)
