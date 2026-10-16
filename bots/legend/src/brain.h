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
	bool shop_trip();
	bool respond_to_alert();
	void farm();
	bool farm_group(Group& g);
	bool capture_group(Group& g);
	bool wait_group(Group& g);
	float group_score(const Group& g, int& eta) const;
	bool go_home();

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
	bool enemy_near = false;

	// memory
	int task = T_NONE, task_group = -1, task_since = 0;
	int ward_round = -100;
	float last_hp = 0;
	int last_hit_round = -100;
	std::vector<int> blacklist; // per group: round until which we ignore it
};

Brain& brain();
