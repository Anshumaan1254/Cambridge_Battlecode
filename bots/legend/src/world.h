// World model: static map facts computed once, plus per-turn perception and memory.
#pragma once
#include "common.h"
#include "params.h"

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
	int attackers = 0; // camps that fight back
	// Live camps hit by a radius-1 splash or area spell centred on the best target, averaged over the kill
	// (a packed trio starts at 3 and ends at 1). Recomputed from remembered health every perception.
	float cluster = 1.f;
	int d_ally = BIG, d_enemy = BIG;
	int d_home_c = BIG; // walking steps from our spawn to the centre (static; trip costs read it every turn)
	int radius = 0;		// Chebyshev reach of the tiles from the centre
	bool ours = true;
	bool objective = false; // objective map (P.obj_plan): one of the few heavy groups that hold most of the gems
	int exit_steps = -1;	// most steps out of camp reach seen while farming here (P.exit_aware; -1 unknown)

	// Dynamic memory
	GroupState st = ST_ALIVE; // every group starts alive
	int ready_round = 0;	  // first round it is alive again when respawning
	int seen_round = -1;
	std::vector<float> hp;	  // last seen health per camp
	float hp_total = 0;
	bool awake = false;
	int enemy_round = -1000;  // last round an enemy was seen within 6 tiles
	bool enemy_on_tile = false;

	void update_cluster();
	// Rounds of hits a retreat from here costs in the farm plan's HP budget (open ground: 4).
	int exit_rounds() const { return P.exit_aware && exit_steps >= 4 ? std::min(4 + P.exit_extra_max, exit_steps + 1) : 4; }
};

// Camp groups that cannot be reached on foot from our spawn, with a teleport-crystal entry (range 3).
struct Island
{
	std::vector<int> groups;
	vec2 launch{ -1, -1 }, land{ -1, -1 };
	int launch_home = BIG; // steps from our spawn to the launch tile
	int gems = 0;
	Field to_launch;	   // field rooted at the launch tile (built at init)
};

// A teleport-crystal shortcut to a camp group that is far on foot (hole mazes): walk to `launch`, hop to
// `land` (up to 3 tiles over holes), then walk on. Computed lazily per group.
struct Hop
{
	bool tried = false, valid = false;
	vec2 launch{ -1, -1 }, land{ -1, -1 };
	int cost = BIG; // rounds from our spawn to the group through the hop
	Field to_launch;
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
	std::array<int, 2> cd{ 0, 0 }; // ability cooldowns, readable while visible
	bool ready(int slot) const { return slot >= 0 && cd[static_cast<std::size_t>(slot)] <= 0; }
	// Damage it can add this turn on top of a basic attack (best ready spell or a reset swing).
	float burst() const
	{
		float b = 0;
		if (ready(kit.dmg)) b = std::max(b, focus * kit.dmg_mod);
		if (ready(kit.cc)) b = std::max(b, focus * kit.cc_mod);
		if (ready(kit.aoe)) b = std::max(b, focus * kit.aoe_mod);
		if (ready(kit.reset)) b = std::max(b, str);
		return b;
	}
};

struct Ally
{
	bc::champion ch;
	std::uint32_t handle;
	bc::champion_type type;
	bool alive = true, visible = false;
	vec2 pos{ -1, -1 };
	float hp = 0, max_hp = 1, str = 0, focus = 0;
	Kit kit{};
	bool kit_ready = false;
	int died_round = -1000; // last death we saw (respawn after respawn_time)
	int seen_round = -1000; // last round this body saw it (pos is that sighting)
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
	std::vector<bool> altar_contested;	 // about as close to their spawn as to ours
	std::vector<int> altar_enemy_round;	 // last round an enemy was seen within 6 of the altar
	std::vector<Group> groups;
	std::vector<Island> islands;
	std::vector<Hop> hops;	 // per group
	bc::bitboard walls_no_holes; // walls, altars and the enemy spawn (holes passable: a crystal hops them)
	bc::bitboard dash_walls;	 // walls minus 1-wide hole crossings (a dash kit routes over them, see P.dash_holes)
	bool dash_kit = false;		 // this body has a dash (set by Brain::init before init_static)
	const bc::bitboard& route_walls() const;
	// Steps out of every live awake camp's reach from `from`, around walls (P.exit_aware); max_d + 1 if not within max_d.
	int escape_steps(vec2 from, int max_d) const;
	std::vector<std::uint8_t> walls_bits; // packed export of `walls` (LSB first, row-major) // field walls for this body: dash_walls for dash kits, else walls
	std::vector<int> island_of; // per group: island index or -1
	// Objective map (P.obj_plan): the gem supply sits in one or a few heavy groups (stampede: one fused 2 gem
	// clusters + 6 elks group pays 360 gems; contest: two monoliths). Decided once at init from camp geometry.
	bool obj_mode = false;
	float obj_share = 0;		 // share of the map's gem rate (gems / respawn) held by heavy groups
	float obj_rate_total = 0, obj_rate_heavy = 0;
	std::vector<int> obj_groups; // heavy gem groups, nearest to our spawn first
	void detect_objective();
	// Contest-like map (P.cm_mode, agent contest6): every gem comes from lone monoliths (one camp, no elks, wolves
	// or gem clusters), the rest is gold. contest, its ladder copy and the 12 maps/gold*/gold_mono_* maps fire; no
	// other map of the 56-map pool does. Decided at init from camp geometry.
	void detect_contest();
	bool cm_mode = false;
	int cm_lone = 0, cm_other = 0; // gem groups that are a lone monolith / any other gem group
	int cm_rush_group = -1;		   // the gold group the opening rush converges on (P.cm_rush_until)
	Field home; // steps from our spawn
	int spawn_altar_d = BIG; // walking steps from our spawn to the nearest altar's approach tile
	bc::bitboard home_reach; // tiles reachable on foot from our spawn
	Field away; // steps from enemy spawn

	std::vector<Ally> allies;
	std::vector<Enemy> enemies;
	int my_index = 0;

	// Per-turn perception
	bc::bitboard vis, camp_occ, ally_occ, enemy_occ, tele_occ;
	bc::bitboard enemy_locks; // visible enemy altar locks

	void init_static();
	int ally_deaths = 0, enemy_deaths = 0; // body deaths seen from the global alive flags (both teams, whole game)
	void find_islands();
	bool islands_pending = false; // find_islands deferred from init to a later turn with spare fuel
	bool contested(int i);		 // altar about as close to their spawn as to ours (lazy)
	void init_units();
	void update_alive(int round); // ally and enemy alive flags and death rounds (cheap; also while dead)
	void perceive(vec2 me);
	int group_at(vec2 p) const;
	bool altar_locked_by_enemy(int altar_index) const;
	int dist_home(vec2 p) const { return home.get(p); }
	int dist_away(vec2 p) const { return away.get(p); }
};

World& world();
