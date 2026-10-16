// World model: static map facts computed once, plus per-turn perception and memory.
#pragma once
#include "common.h"

enum GroupState : std::uint8_t
{
	ST_UNKNOWN = 0,
	ST_ALIVE = 1,
	ST_REWARD = 2,
	ST_RESPAWN = 3
};

struct CampRef
{
	bc::camp camp;
	bc::camp_type type;
	vec2 pos;
	float max_hp, str;
};

struct Group
{
	std::uint32_t handle = 0;
	int id = 0;
	std::vector<CampRef> camps;
	std::vector<vec2> tiles;
	bc::bitboard mask;	   // spawn tiles of the group
	bc::bitboard near;	   // tiles within Chebyshev 3 (camp attack range)
	vec2 center;
	int gems = 0, gold = 0, respawn = 0;
	float max_hp = 0, dps = 0;
	bool monolith = false, elk = false, harmless = true;
	int d_ally = BIG, d_enemy = BIG;
	bool ours = true;

	// Dynamic memory
	GroupState st = ST_ALIVE; // every group starts alive
	int ready_round = 0;	  // first round it is alive again when respawning
	int seen_round = -1;
	std::vector<float> hp;	  // last seen health per camp
	float hp_total = 0;
	bool awake = false;
	int enemy_round = -1000;  // last round an enemy was seen within 6 tiles
	bool enemy_on_tile = false;
};

struct Enemy
{
	std::optional<bc::champion> ch; // built lazily on first sight (cheap only while visible)
	std::uint32_t handle;
	bc::champion_type type;
	Kit kit;
	bool alive = true, visible = false;
	vec2 pos{ -1, -1 };
	int seen_round = -1000;
	int died_round = -1000;
	float hp = 0, max_hp = 1, str = 0, focus = 0;
	std::uint32_t gems = 0;
	std::int32_t state = 0;
	bool channeling = false, tributing = false, recalling = false;
};

struct Ally
{
	bc::champion ch;
	std::uint32_t handle;
	bc::champion_type type;
	bool alive = true, visible = false;
	vec2 pos{ -1, -1 };
	float hp = 0, max_hp = 1, str = 0;
};

struct World
{
	int W = 0, H = 0, round = 0;
	bc::bitboard walls;	  // static impassable: walls, holes, altars, enemy spawn
	bc::bitboard terrain; // walls | holes (vision/terrain only)
	bc::bitboard ally_spawn, enemy_spawn;
	vec2 ally_spawn_c, enemy_spawn_c;
	std::vector<vec2> altars;
	std::vector<std::vector<vec2>> altar_approach;
	std::vector<Group> groups;
	Field home; // steps from our spawn
	Field away; // steps from enemy spawn

	std::vector<Ally> allies;
	std::vector<Enemy> enemies;
	int my_index = 0;

	// Per-turn perception
	bc::bitboard vis, camp_occ, ally_occ, enemy_occ, tele_occ;
	bc::bitboard enemy_locks; // visible enemy altar locks

	void init_static();
	void init_units();
	void perceive(vec2 me);
	int group_at(vec2 p) const;
	bool altar_locked_by_enemy(int altar_index) const;
	int dist_home(vec2 p) const { return home.get(p); }
	int dist_away(vec2 p) const { return away.get(p); }
};

World& world();
