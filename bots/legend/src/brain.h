// Per-champion decision making: perceive, score tasks, then plan and execute one legal turn.
#pragma once
#include "comms.h"
#include "nav.h"
#include "params.h"
#include "world.h"

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

class Brain
{
public:
	void turn();

private:
	// lifecycle
	void init();
	void read_self();
	void shop();
	void handle_channel();

	// decisions (each returns true when it used the turn)
	bool combat();
	bool safety();
	bool tribute(bool force);
	bool on_the_way(int altar) const;
	bool shop_trip();
	bool home_trip();
	void update_priority();
	bool escort_wait();
	int deficit = 0, respawn_round = -1000;
	bool was_alive = true;
	int cur_prio = -1;
	int capture_group_id = -1, capture_since = -1, last_bank_round = -100;
	int tribute_cancel_round = -1000;
	bool W_dist_home_ok() const;
	bool engaged = false;
	bool safe_to_recall() const;
	bool altar_unsafe(int i) const;
	void post_danger(vec2 at);
	void prepare_scoring();
	struct RecentEnemy
	{
		vec2 pos;
		float hp, dps;
	};
	std::array<RecentEnemy, 8> sc_recent{};
	int sc_recent_n = 0;
	float sc_risk = 0;
	bool sc_alert = false;
	bool reward_here(); // a dead group we were farming waits for its capture next to us
	bool respond_to_alert();
	void farm();
	bool farm_group(Group& g);
	bool capture_group(Group& g);
	bool wait_group(Group& g);
	float group_score(const Group& g, int& eta, bool* need_pair = nullptr, int d_override = -1) const;
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
	float incoming_on(const Group& g) const;	  // damage per round g deals to the champion it targets (after passives)
	float ally_dps_on(int ally, const Group& g) const; // estimated contribution of an ally farming g
	bool ally_melee(int ally) const;
	int trip_cost(const Group& g) const;		  // rounds to heal at spawn and come back to g
	bool jungle_done() const;
	bool durability_done() const;
	void refresh_item_flags() const;
	mutable std::size_t item_flags_idx = static_cast<std::size_t>(-1);
	mutable bool jungle_ok = false, durability_ok = false;
	bool has_home = false; // Home emblem (faster recall); we never buy it, kept for the capture-recall timing

	// combat helpers
	float camp_dps() const;
	float burst_vs(const Enemy& e) const;
	bool attack_unit(const bc::unit& u);
	bool attack_chain_camp(Group& g, std::size_t idx);
	bool spells_on_camp(Group& g, std::size_t idx, bool save_cc);
	bool engage(Enemy& e);
	bool cast_unit_camp(int slot, const bc::camp& c);
	bool cast_unit_champ(int slot, const bc::champion& c);
	bool cast_ground(int slot, vec2 p);
	bool cast_self(int slot);
	bool ready(int slot) const { return slot >= 0 && cd[static_cast<std::size_t>(slot)] <= 0 && can_cast && !cast_done; }
	void support_spells();

	// utilities
	void build_danger();
	void place_ward(bool force);
	void use_locks();
	bool step(const bc::bitboard& goals, bool avoid_danger, bool allow_dash);
	bool go_group(Group& g, int stop_at, bool avoid);
	bool go_altar(int id);
	bool go_home_step(bool avoid);
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
	bc::bitboard camp_danger; // tiles in range of awake camps
	bc::bitboard alert_zone;  // area an ally reported as dangerous (shared memory)
	bool enemy_near = false;

	// game-state modulated thresholds (recomputed each turn from P and the scoreboard)
	float fight_margin = 1.3f, fight_back_margin = 0.75f, deny_bonus = 0.55f, enemy_half_penalty = 10.f;
	float isolated_fight_adv = 1.6f;
	int stance = 0;
	int tribute_min = 34;
	void update_mode();

	// memory
	int task = T_NONE, task_group = -1, task_since = 0;
	int ward_round = -100;
	float last_hp = 0;
	int last_hit_round = -100;
	std::vector<int> blacklist; // per group: round until which we ignore it
};

Brain& brain();
