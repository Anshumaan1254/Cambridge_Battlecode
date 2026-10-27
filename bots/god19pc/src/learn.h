// In-match learning: reward good outcomes and punish mistakes while the game is running.
//
// A submitted bot cannot be updated and keeps nothing between matches, so learning happens at two levels:
//   * offline, the parameters in params.h are trained by self-play policy search (tools/rl/es_train.py);
//   * online, inside every match, this module adapts the team to the opponent it is actually facing.
//
// Three online learners, all cheap in fuel:
//   1. Team stance bandit. Every `learn_window` rounds the team scores the stance it just played
//      (reward = banked-gem difference per 10 rounds + kills - deaths, punishments weighted heavier)
//      and picks the stance with the best running value: SPREAD (farm everywhere), GROUPED (farm close
//      together, keep backup, stay off their half) or PUSH (invade, contest, take fights).
//      One body (the lowest index, which runs every round even while dead) decides and broadcasts the
//      stance in two spare shared-memory bits, so every body plays the same stance.
//   2. Pain map. Each body remembers where allies died and where it took champion damage, decaying
//      over time; farming targets in painful regions cost extra, places where we got kills heal.
//   3. Fight calibration. Each body scales its fight-advantage estimate: dying soon after choosing to
//      fight makes it more careful, kills after choosing to fight make it bolder.
#pragma once
#include "common.h"

enum Stance : int
{
	STANCE_SPREAD = 0,
	STANCE_GROUPED = 1,
	STANCE_PUSH = 2,
	STANCE_COUNT = 3
};

struct Learner
{
	// ---- team stance (decided by the leader, read by everyone through comms)
	int stance = STANCE_SPREAD;
	std::array<float, STANCE_COUNT> q{};
	std::array<int, STANCE_COUNT> plays{};
	int window_start = 1;
	int ours0 = 0, theirs0 = 0;
	int ally_deaths = 0, enemy_deaths = 0;	   // running totals seen by this body
	int ally_deaths0 = 0, enemy_deaths0 = 0;   // at window start
	int ally_deaths_our_half = 0, our_half0 = 0;
	std::vector<bool> ally_alive, enemy_alive;
	float last_reward = 0;
	bool frozen = false; // P.opp_model: the team plays a counter plan, not the learner's stance: windows are not scored
	float prev_diff = 0; // previous window's banked-gem difference (smooths the lumps)

	// ---- pain map (per body): coarse cells of CELL x CELL tiles
	static constexpr int CELL = 6;
	int cw = 0, ch = 0;
	std::vector<float> pain;
	int pain_round = 0;

	// ---- fight calibration (per body)
	float fight_bias = 0.f;			// log-scale multiplier on the advantage estimate
	std::vector<float> enemy_burst; // mi_learn_burst: the biggest one-round damage each enemy has dealt this body
	int fight_round = -1000;		// last round we chose to fight
	bool was_alive = true;

	void init(int width, int height);
	// Called every turn by every body (alive or dead). Leader updates the stance; others read it.
	void tick(int round, bool leader, bool me_alive);
	void add_pain(vec2 p, float amount);
	float pain_at(vec2 p) const;
	void on_fight(int round) { fight_round = round; }
	void on_enemy_killed_near(vec2 p, int round);
	float fight_scale() const;
};

Learner& learner();
