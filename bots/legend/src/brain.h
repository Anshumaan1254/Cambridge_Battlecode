// Per-champion decision making: perceive, score tasks, then plan and execute one legal turn.
#pragma once
#include "comms.h"
#include "learn.h"
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
	bool respond_to_alert();
	void farm();
	bool farm_group(Group& g);
	bool capture_group(Group& g);
	bool wait_group(Group& g);
	float group_score(const Group& g, int& eta, bool relaxed = false, bool* kite = nullptr) const;
	float dps_vs_group(const Group& g) const; // calibrated by learner().k_out()
	float dps_vs_group_raw(const Group& g) const;
	float mitigated(float raw, int live) const;
	void learn_observe();
	float kite_dps(const Group& g) const;
	bool kite_group(Group& g);
	void chip_passing();
	float incoming_per_round(const Group& g, int helpers) const;
	bool go_home();
	// Teleport-crystal islands
	float island_score(int i) const;
	bool island_task(int i);
	bool inside_island() const;
	int tp_island = -1;

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
	float camp_in = 0;		  // damage per round awake camps can deal to our tile

	// game-state modulated thresholds (recomputed each turn from P and the scoreboard)
	float fight_margin = 1.3f, fight_back_margin = 0.75f, deny_bonus = 0.55f, enemy_half_penalty = 10.f;
	int tribute_min = 34;
	void update_mode();

	// memory
	int task = T_NONE, task_group = -1, task_since = 0;
	bool task_kite = false; // farming the task group from range 4 with spells only
	float task_hp = 0;		// task group's health when last checked (progress detection)
	GroupState task_st = ST_ALIVE;
	std::array<int, 8> switch_log{ -1000, -1000, -1000, -1000, -1000, -1000, -1000, -1000 };
	std::size_t switch_pos = 0;
	int sticky_until = -1;
	// calibration sample taken this turn, scored at the start of the next one
	int cal_round = -1, cal_group = -1;
	float cal_ghp = 0, cal_pred_out = 0, cal_pred_in = 0;
	float camp_in_prev = 0;
	int last_turn_round = -10;
	void calibration_sample(const Group& g);
	int ward_round = -100;
	float last_hp = 0;
	int last_hit_round = -100;
	std::vector<int> blacklist; // per group: round until which we ignore it
};

Brain& brain();
