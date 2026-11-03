// Draft-memory plan (P.dm_plan, docs/COMMS.md): what the draft turn (1M fuel on its first turn, the whole map, no champion yet) works
// out once and every body reads in Brain::init(): the picks, the map type, the objective / monolith groups, a zone owner per group, the
// anchor ranking and up to 32 planned ward spots. The draft writes the versioned layout on every draft turn (the last write wins); in
// the game the bytes are a read-only snapshot. A missing, foreign or stale buffer (magic, version, map size, group count, checksum) is
// ignored and every user falls back to its in-game logic.
#pragma once
#include "common.h"

constexpr std::uint8_t DM_MAGIC = 0xC8;
constexpr std::uint8_t DM_VERSION = 1;

enum DmFlag : int
{
	DMF_OBJECTIVE = 1,	  // one heavy multi-camp gem group holds the map's gems (the objective draft's test)
	DMF_MONOLITH = 2,	  // gems only in lone monoliths
	DMF_NO_ALTAR = 4,	  // no altar reachable from our spawn
	DMF_GOLD_HEAVY = 8,	  // gold / gem reward rate ratio above 8 (the 21 maps: median 6.3)
	DMF_ISLANDS = 16	  // groups not reachable on foot from our spawn
};

enum DmWardKind : int
{
	DMW_BUSH_GROUP = 0, // bush next to one of our groups (a body stands still there while farming / capturing)
	DMW_BUSH_ALTAR = 1, // bush next to one of our altars (tributes stand still for up to 20 turns)
	DMW_APPROACH_ALTAR = 2, // the enemy-facing approach of an altar
	DMW_APPROACH_GROUP = 3, // the enemy-facing approach of a heavy / midline group
};

struct DmSpot
{
	vec2 p{ -1, -1 };
	int slot = 255; // responsible pick slot (0-4: the order of our picks; the game maps it to bodies by champion type)
	int kind = 0;
	int group = 255; // group (or 255) the spot watches
};

struct DraftPlan
{
	bool ok = false;
	int team = 0, width = 0, height = 0, groups = 0, flags = 0;
	std::vector<int> ours, theirs;	 // champion_draft values (picks seen so far)
	std::vector<int> obj_groups;	 // heavy groups and monoliths on our half (group ids = index in bc::map::camp_groups())
	std::vector<int> anchor_slots;	 // our pick slots, best anchor first (Vesper, Marcella, Prism, then the lowest base health)
	std::vector<int> zone;			 // per group: owning pick slot (255 = not ours)
	std::vector<DmSpot> wards;		 // up to 32 planned ward spots, best first
};

std::vector<std::uint8_t> dm_encode(const DraftPlan& p);
bool dm_decode(const std::vector<std::uint8_t>& b, DraftPlan& out); // structural checks only (the caller checks map size / groups)
DraftPlan& draft_plan();		// the game's copy (Brain::init)
void dm_build(DraftPlan& p);	// draft turn: everything but the picks (expensive, once)
bc::champion_type dm_type_of(bc::champion_draft d); // a pick's champion (Cassi for the pair)
