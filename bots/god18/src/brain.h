// Per-champion decision making: perceive, score tasks, then plan and execute one legal turn.
#pragma once
#include "comms.h"
#include "nav.h"
#include "params.h"
#include "world.h"
#include "tp_adapter.h"

enum TaskKind : int
{
	T_NONE,
	T_FARM,
	T_CAPTURE,
	T_WAIT,
	T_TRIBUTE,
	T_HOME,
	T_FIGHT,
	T_FLEE
};

#ifdef XM_TRACE
// Prediction audit (XM_TRACE builds only): the parts of group_score's farming model for one group, so the
// trace can compare predicted kill time and damage taken with what happened.
struct ScoreParts
{
	float my_dps = 0, ally_dps = 0, hp_left = 0, kill = 0, in = 0, share = 0, taken = 0, budget_now = 0, budget_full = 0, time = 0, value = 0, score = 0;
	float share0 = 0, taken0 = 0, seq = 1, reach = 1; // the uncorrected damage model, the sequential-kill factor, in_now/in
	int trips = 0, trips0 = 0, d_adj = 0, d0 = 0, wait = 0, claimers = 0;
	bool melee_ally = false, planned = false, present = false;
};
#endif

class Brain
{
public:
	void debug_state(unsigned long long fuel_left) const; // FUEL_STATE builds: one line per turn (called inside debug_block)
	void safe_fallback(); // F6 watchdog (main.cpp)
	void turn();

private:
	// lifecycle
	std::vector<bc::item_type> build_from_kit() const; // build_kit (patch 3.0.4)
	void init();
	void read_self();
	void shop();
	void handle_channel();

	// decisions (each returns true when it used the turn)
	bool combat();
	bool wins_with(int bag) const;
	bool can_support(const Ally& a, const std::vector<Enemy*>& E) const;
	bool safety();
	bool tribute(bool force);
	int bank_min(int trip) const; // gems worth a bank trip of `trip` rounds (longer trips bank bigger bags)
	bool on_the_way(int altar) const;
	bool shop_trip();
	bool home_trip();
	void update_priority();
	bool escort_wait();
	bool regroup_active();
	int rg_until = -1000;
	bool mono_forced = false;
	int deficit = 0, respawn_round = -1000;
	bool was_alive = true;
	int cur_prio = -1;
	int capture_group_id = -1, capture_since = -1, last_bank_round = -100;
	int tribute_cancel_round = -1000;
	int tribute_start = -1000, tribute_ticks = 0;
	// Gem race (P.race_mode): banked totals sampled every race_sample rounds, the race state they imply.
	std::array<int, 8> race_r{}, race_us{}, race_them{};
	int race_n = 0;
	int race_state = 0; // 0 even or ahead, 1 behind and we win fights (contest gems), 2 behind and we do not (pure gem pace) // round the current tribute started and its length
	bool W_dist_home_ok() const;
	bool engaged = false;
	int last_fight_round = -100;
	int px_hold_since = -100, px_hold_round = -100; // P.px_hold
	Enemy* best_in_reach(const Enemy* skip);
	int dbg_path = 0, dbg_eng = 0; // SPELL_TRACE: which decision used the turn / which engage branch
	bool dbg_hit_other = false;	   // SPELL_TRACE: the melee step-then-hit-another-enemy branch swung
	bool safe_to_recall() const;
	bool altar_unsafe(int i) const;
	bool bag_needs_escort(int i) const; // P.escort_bag
	void post_danger(vec2 at);
	void prepare_scoring();
	struct RecentEnemy
	{
		vec2 pos;
		float hp, dps;
	};
	std::array<RecentEnemy, 8> sc_recent{};
	int sc_recent_n = 0;
	struct ThreatEnemy
	{
		vec2 pos;
		int age;
		float hp, dps;
	};
	std::array<ThreatEnemy, 8> sc_threat{}; // P.threat_map
	int sc_threat_n = 0;
	float sc_risk = 0;
	bool sc_alert = false;
	int sc_obj_focus = -1; // objective group the team plan is limited to this turn (P.obj_focus)
	bool reward_here(); // a dead group we were farming waits for its capture next to us
	bool respond_to_alert();
	void farm();
	bool farm_group(Group& g);
	bool contest_tiles(Group& g); // big_reward: stand on a dead tile of a big group an enemy waits on
	bool capture_group(Group& g);
	bool wait_group(Group& g);
	float group_score(const Group& g, int& eta, bool* need_pair = nullptr, int d_override = -1) const;
	int approach_rounds(int d_tile) const; // rounds to attack range of a group d_tile steps away
	float score_cap(const Group& g) const;  // upper bound on group_score(g)
	bool obj_team_ready(const Group& g, float hp_left, float& kill) const; // objective map: the team can clear g
	int obj_gather_since = -1, obj_gather_group = -1;
	mutable bool sc_team = false; // the last group_score used the objective team plan (the solo plan failed)
	bool task_team = false;		  // ... for the current farm target
	mutable bool sc_ring = false; // the last group_score used the objective ring plan (o2_ring)
	bool task_ring = false;		  // ... for the current farm target
	// Session 11 ideas from the default branch (mi_* params)
	mutable bool sc_relaxed = false, sc_kite = false; // group_score: relaxed limits pass; the last score used the kite plan
	bool task_kite = false;
	int mi_last_round = -10, mi_sticky_until = -1;
	float mi_camp_in = 0, mi_camp_in_prev = 0;
	std::array<int, 8> mi_switch_log{ -1000, -1000, -1000, -1000, -1000, -1000, -1000, -1000 };
	std::size_t mi_switch_pos = 0;
	float kite_dps(const Group& g) const;
	bool kite_group(Group& g);
	void chip_passing();
	void learn_burst();
	float ring_dps(const Kit& k, float foc, const Group& g) const;
	bool ring_ready(const Group& g, float hp_left, float& kill) const;
	bool ring_farm(Group& g, bool respawning = false);
	bool hop_task(int gid);
	bool has_crystal() const;
	int tp_hop = -1, tp_hop_since = 0;
	int pair_group = -1, pair_since = 0;
	bool go_home();
	// Teleport-crystal islands
	float island_score(int i) const;
	bool island_task(int i);
	bool inside_island() const;
	int tp_island = -1;

	// farming model
	float dps_on(const Group& g) const;			  // our damage per round against g (splash, area, retaliation)
	float incoming_on(const Group& g) const;
	float incoming_on_raw(const Group& g) const; // P.farm_ema: the model before the learned multiplier
	float my_shield = 0.f;						  // P.fm_buffs: our shield buff value
	float farm_ema_v = 1.f, farm_pred = 0.f;		  // P.farm_ema: learned multiplier, last turn's prediction
	int enemy_near_rounds = 0;					  // P.risky_persist: rounds in a row with an enemy within 9	  // damage per round g deals to the champion it targets (after passives)
	float ally_dps_on(int ally, const Group& g) const; // estimated contribution of an ally farming g
	bool ally_melee(int ally) const;
	int trip_cost(const Group& g) const;		  // rounds to heal at spawn and come back to g
	bool jungle_done() const;
	bool durability_done() const;
	bool monster_done() const;
	void refresh_item_flags() const;
	mutable std::size_t item_flags_idx = static_cast<std::size_t>(-1);
	mutable bool jungle_ok = false, durability_ok = false, monster_ok = false, home_ok = false;
	void insert_home(std::size_t at);
	void insert_health(std::size_t at);
	float base_hp = 0, hp_growth = 1, base_str = 0, str_growth = 1, base_focus = 0, focus_growth = 1; // gold_rank 2: our design stats
	float enemy_burst_seen = 0; // build_react: the biggest potential one-round burst any visible enemy has shown this game
	int recall_turns() const;
	int recalls_started = 0; // ic_home 3
	std::array<int, 6> prev_claim{ -1, -1, -1, -1, -1, -1 }; // reward_claim_gone: last round's claims
	std::array<int, 6> prev_claim_since{}; // ... and the round each ally's claim took its value
	bool was_recalling = false;
	bool g17_bait_on = false;
	void g18_adjust_build(); // v17: the recall we started at the end of our last turn is bait
	bool has_home = false; // Home emblem (faster recall); we never buy it, kept for the capture-recall timing
#ifdef XM_TRACE
	// Prediction audit state (all updated inside debug_block, so it costs no fuel and changes no decision).
	mutable ScoreParts* xm_sp = nullptr;
	struct XmEp
	{
		int g = -1, commit_r = 0, engage_r = -1, trips = 0, away_r = -1;
		bool away = false, saw_alive = false;
		float hp0 = 0, lost = 0, dealt = 0, my_hp0 = 0, g_hp_commit = 0, gv = 0;
		ScoreParts p{};
	} xm_ep;
	int xm_pg = -1, xm_pr = -100; // per-round farm prediction: group and round it was made
	float xm_p_my = 0, xm_p_ally = 0, xm_p_in = 0, xm_p_near = 0, xm_p_share = 0, xm_p_share0 = 0, xm_g_hp = 0, xm_my_hp = 0;
	bool xm_p_pres = false;
	float xm_p_reach = 1;
	int xm_p_claim = 0, xm_p_live = 0, xm_p_vis = 0;
	bool xm_p_clean = false;
	bool xm_was_alive = true;
	void xm_pre();
	void xm_post();
	void xm_decide(int best);
	void xm_dead();
	void xm_close(const char* why);
	void xm_fight(float adv, float tku, float tkt, float ohp, float thp, float odps, float tdps, int na, int ne, int fight, int killable, int in_reach,
				  int can_escape, int isolated, int reserve, int tgt_type, int tgt_d, float incoming, float t_die, float tgt_hp, int backup, float my_dps);
#endif

	// ml2: fight / danger model (features in tools/ml/ml2_dataset.py order)
	void ml2_features(float* f) const;
	float ml2_p_die = 0, ml2_p_kill = 0;
	int ml2_exit_round = -1000;
	void ml2_learn(bool died);
	float ml2_off = 0;				  // ml2_adapt: learned logit offset (this opponent vs the ladder)
	std::array<int, 24> ml2_buf_r{};  // evaluations waiting for their label (round, logit)
	std::array<float, 24> ml2_buf_z{};
	int ml2_buf_n = 0;

	// combat helpers
	float camp_dps() const;
	float burst_vs(const Enemy& e) const;
	bool attack_unit(const bc::unit& u);
	bool attack_chain_camp(Group& g, std::size_t idx);
	bool spells_on_camp(Group& g, std::size_t idx, bool save_cc);
	bool cast_en_route();
	bool cast_on_nearer(const Enemy& skip);
	bool engage(Enemy& e);
	bool cast_unit_camp(int slot, const bc::camp& c);
	bool cast_unit_champ(int slot, const bc::champion& c);
	bool cast_ground(int slot, vec2 p);
	bool strike_dash_at(const Enemy& e); // P.hor_strike: damaging dash onto a tile with the target in the landing radius
	bool hor_camp_dash(Group& g, std::size_t idx); // P.hor_camp: damaging dash onto a camp pack
	bool cast_self(int slot);
	bool ready(int slot) const { return slot >= 0 && cd[static_cast<std::size_t>(slot)] <= 0 && can_cast && !cast_done; }
	void support_spells();

	// utilities
	void build_danger();
	void place_ward(bool force);
	void use_locks();
	bool step(const bc::bitboard& goals, bool avoid_danger, bool allow_dash);
	int mob_dash() const;
	bool strike_dash = false;
	bool shield_deferred = false;
	// Opponent model (P.opp_model, P.om_sight; opponent.h). update_mode() sets the plan's working values every turn; with the switches off
	// they equal the params.h values.
	int plan_now = 0;
	int escort_bag_now = P.escort_bag;
	int group_r_now = P.group_radius;
	int ward_bush_now = -1; // >= 0: the plan's ward_bush mode replaces P.ward_bush
	bool role_guard = false, role_hunter = false;
	int om_inv_win = -1;	// window this body last added to the invasion counter
	int om_theirs = 0, om_ad = 0, om_ed = 0, om_ad_home = 0, om_last_ad_round = -1000, om_cancel_seen = -1000;
	std::array<int, 8> om_ward_win{};	// per enemy index: window its ward was last counted
	std::vector<vec2> om_ward_tiles;	// ... wards of unknown owner (2.2.x SDK) counted this window
	int om_ward_tiles_win = -1;
	std::vector<int> om_gst;			// per group: state the leader last saw (heavy groups taken unclaimed)
	int om_lock_win = -1, om_lock_mask = 0;
	std::vector<int> om_heavy_ids;		// heavy groups and monoliths (fixed for the match: the leader's per-turn loop visits only these)
	int om_half_round = -1;				// om_enemy_ours(): per-turn memo of "visible enemy k stands on our half"
	std::array<signed char, 8> om_half{};
	mutable std::vector<signed char> altar_side; // altar_ours(): side per altar, computed once (-1 = not yet)
	bool om_enemy_ours(std::size_t k);
	vec2 sc_sight{ -1, -1 };			// P.om_sight: fresh DANGER sighting this turn (scoring cost)
	void om_tick();
	void om_tick_traced(); // om_tick, plus its fuel cost printed in FUEL_TRACE builds
	int style_now() const; // P.pxs_style: the proxy style this round
	bool pxs_deny_altar();
	void om_observe();
	bool is_altar_tile(vec2 p) const;
	bool altar_ours(std::size_t i) const; // our half by its approach tiles (the altar tile itself is a wall: no distance)
	bool escort_alert() const; // the alert slot holds a fresh ESCORT (DANGER posted at an altar tile)
	int my_slot = -1;		   // P.dm_plan: our pick slot in the draft plan (-1 unknown)
	// F4 anchors (P.anchors): the team's anchor order (fixed at init), this turn's anchors, our role.
	std::vector<int> anchor_order;
	std::array<bool, 8> anchor_now{};
	bool is_anchor = false;
	int anchor_rank = -1, anchor_altar = -1;
	int bag_caution_now = P.bag_caution;
	void update_anchors();
	bool gank_carrier();		  // F6
	bool deny_enemy_altar();	  // F6
	std::vector<int> enemy_tribute_seen; // F6: rounds we saw an enemy tributing at each altar
	bool chain_keep(const Group& g, int recall_t, bool bag, bool rich); // F5: a nearby target beats the home trip
	bool body_is_anchor(int i) const { return i >= 0 && i < 8 && anchor_now[static_cast<std::size_t>(i)]; }
	bool plan_ward(bool force); // P.ward_plan
	bool v14_ward(bool force);  // P.ward_v14 (false: ward_v14 2 leaves it to v13's rule)
	bool mono_group(const Group& g) const; // P.mono_team (+ P.mono_v14)
	std::array<vec2, 8> ew_pos{};	 // P.ward_enemy: last seen enemy ward per enemy index (owner)
	std::array<int, 8> ew_round{};
	std::vector<std::pair<vec2, int>> ew_tiles; // ... owner unknown (2.2.x SDK): tile, last seen round
	void enemy_wards_update();
	bool near_enemy_ward(vec2 p, int r) const;
	struct DLRow
	{
		int round = -1000;
		float hpf = 1.f;
		int enemies5 = 0, casters5 = 0, allies6 = 0;
		bool channel = false;
	};
	std::array<DLRow, 5> dl_hist{}; // P.death_learn: last 5 rounds (ring)
	float dl_burst = 0, dl_iso = 0, dl_chan = 0, dl_camp = 0;
	int dl_burst_r = -1000, dl_iso_r = -1000, dl_chan_r = -1000, dl_camp_r = -1000;
	float dl_val(float v, int r) const { return P.death_learn ? v * std::max(0.f, 1.f - static_cast<float>(round - r) / static_cast<float>(std::max(1, P.dl_decay))) : 0.f; }
	void dl_record();
	void dl_on_death();
	float gv_base = -1.f; // P.gv_map: map-derived gold value (computed once) // hor_strike 2: the shield was held for the strike dash this turn (cast at the end of the turn if no cast happened)
	bool go_group(Group& g, int stop_at, bool avoid);
	bool go_altar(int id);
	bool go_home_step(bool avoid);
	bool pocket_dash(); // P.pocket_fix
	bool after_move(bool moved);
	void prebuild_fields();
	int nearest_altar(int& dist) const;
	bool in_awake_camp_range() const;
	int enemies_within(int r) const;

	// identity
	bool inited = false;
	int init_round = 0;
	std::uint32_t self = 0;
	bc::champion_type type = bc::champion_type::ryth;
	Kit kit;
	std::vector<bc::ability> ab;
	std::vector<bc::item_type> build;
	std::size_t build_idx = 0;

	// per-turn self state
	int round = 0;
	vec2 pos{};
	float hp = 0, max_hp = 1, str = 0, focus = 0;
	std::int32_t state = 0;
	std::uint32_t gems = 0, gold = 0;
	bool alive = true, can_move = false, can_attack = false, can_cast = false, cast_done = false;
	std::array<int, 2> cd{};
	bc::bitboard danger;	  // tiles enemies can hit next turn
	bc::bitboard danger4;	  // P.aoe_reach5 == 3: the legend danger map (every spell 4), for combat()'s in_reach
	bc::bitboard camp_danger; // tiles in range of awake camps
	bc::bitboard alert_zone;  // area an ally reported as dangerous (shared memory)
	bc::bitboard clump;		  // P.spread_vs_splash: tiles next to an ally while a splash/area threat is near (else empty)
	bool splash_threat = false;
	int sf_round = -100, sf_since = -100; // P.strike_first: hold rounds
	std::uint32_t chase_h = 0; // v14 fz_chase: the fight target being chased, its best distance so far and since when
	int chase_best = 99, chase_since = -100, chase_round = -100, chase_off_until = -100;
	// GOD v15 (P.g15_calm, P.g15_lock): per enemy index, where we last saw it and when (threat test), whether it is a threat this turn,
	// and since when we see it tributing with what bag (the ticks it has left).
	std::array<vec2, 8> g15_epos{};
	std::array<int, 8> g15_eround{ -100, -100, -100, -100, -100, -100, -100, -100 };
	std::array<char, 8> g15_threat{};
	std::array<int, 8> g15_trib_since{ -1, -1, -1, -1, -1, -1, -1, -1 };
	std::array<int, 8> g15_trib_gems{};
	int g15_nthreat = 0;
	// GOD v18 g18_calm_mono: the contact-discipline values in force for this map (v17's on lone-monolith maps), set in init()
	int calm_bits = 0;
	float ml2_flee_eff = 0.f;
	int fz_engage_eff = 0;
	int g15_lock_round = -100;
	int g15_fw_n = 0, g15_fw_round = -100, g15_fw_off = -100; // g15_fwalk: turns in a row walking to a fight without a hit, cooldown end
	void g15_threats();
	bool g15_is_threat(const Enemy& e) const;
	bool g15_has_lock() const;
	bool g15_place_lock(vec2 altar);
	bool lock_run();
	int g16_rank() const;		// v16: this body's rank among the living allies by kit strength (0 = strongest)
	bool hunt_camp();			// v16: the hunt-and-camp plan
	int g16_camp_start = -1000;	// round the spawn camp started

	bool enemy_near = false;
	int enemy_near_d = BIG; // nearest recently seen enemy, minus the rounds since we saw it (it may have closed in)
	bool enemy_near_field = false; // enemy_near, not counting enemies standing on their own spawn
	bool cast_area_stun_at(const Enemy& e); // area stun hitting e from up to range + radius away
	int cast_area_n(const Enemy& e) const;  // enemies one area cast catching e can hit
	int of_round = -100, of_since = -100;	// P.open_first & 2: hold rounds

	// game-state modulated thresholds (recomputed each turn from P and the scoreboard)
	float fight_margin = 1.3f, fight_back_margin = 0.75f, deny_bonus = 0.55f, enemy_half_penalty = 10.f;
	float isolated_fight_adv = 1.6f;
	float gold_v = 0.22f; // gem value of one gold this turn (P.gold_value scaled by the rounds left, update_mode)
	int stance = 0;
	int tribute_min = 34;
	void update_mode();
	// v9 (P.opp_plan): the team plan in force this turn and the preset knobs update_mode() cannot express through the thresholds above
	int plan9_now = 0;
	int rally_add = 0, opp_add = 0;
	bool locks_contested = false;
	bool enemy_on_our_half() const;
	bool sparring_window() const; // v9: P.spar_from <= round < P.spar_to (sparring personas only)
	bool ally_engaged(const Enemy& t) const; // P.ally_defend

	// memory
	int task = T_NONE, task_group = -1, task_since = 0;
	int target_hit_round = -100; // commit_hit / commit_keep: last round we hit a camp of task_group
	int task_progress = -1; // giveup_progress: last round we hit, captured or waited at task_group
	int ward_round = -100;
	vec2 ward_pos{ -1, -1 }; // where our ward was last placed (ward_bush)
	float last_hp = 0;
	int last_hit_round = -100;
	std::vector<int> blacklist; // per group: round until which we ignore it
	std::vector<float> dmg_on;  // kill_captures: our damage on each group since its last respawn
	void note_dmg(int gid, float amount);
	// Last-resort unstick: a walking task that stays inside a 3x3 box without attacking for unstick_rounds.
	int last_act_round = -100;
	vec2 ust_anchor{ -1, -1 };
	int ust_since = 0;
	std::array<vec2, 16> osc_pos{};	 // v14 fz_osc: our tile at the end of each of the last 16 rounds
	std::array<int, 16> osc_quiet{ -100, -100, -100, -100, -100, -100, -100, -100, -100, -100, -100, -100, -100, -100, -100, -100 }; // ... and the round, when it was a quiet walking round
	void osc_guard();
	int left_group = -1, left_round = -1000; // target we last switched away from (flip guard)
	// no_split: positions at the end of the last turn (ours and the allies we saw)
	void remember_positions();
	vec2 my_prev_pos{ -1, -1 };
	int my_prev_round = -100;
	std::array<vec2, 8> ally_prev_pos{};
	std::array<int, 8> ally_prev_round{};
	std::array<int, 8> ally_still_since{};
#ifdef LEGEND_TRACE
	int tr_hits = 0; // trace: attacks on the current target since it was set
#endif
	void unstick();
	// tools/teamplan (P.tp_*; tp_adapter.h)
	tpa::Own tp_own_;
	teamplan::TbState tp_tb_;
	float tp_target_value(const Enemy& e, float eff_hp) const; // P.tp_focus
	bool tp_we_first(const Enemy& e) const;					   // P.tp_timing: we act again before e
	// GOD v12 (mi_game.h): capture detection for P.mi_next / P.mi_open
	int mi_cap_since = -100;
	std::uint32_t mi_prev_gems = 0, mi_prev_gold = 0;
};

Brain& brain();
