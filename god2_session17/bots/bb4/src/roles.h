// BB4 roles (session 16): every champion type gets a role from the engine's design numbers, normalised over all champion types, so a
// balance patch (stats, growth, abilities) moves the roles by itself. Roles: FRONT (melee, health and crowd control: takes the hits, leads),
// ASSASSIN (melee damage with mobility: dash / reset), RANGED (damage from range 3+), SUPPORT (heals, ranged stuns, field shopping).
// Map classes from terrain (draft and play): walls and bushes block sight (close fights: frontliners), holes block walking but not
// attacks (ranged shoot across, melee walk around).
#pragma once
#include "common.h"
#include <array>

enum Role : int
{
	R_FRONT = 0,
	R_ASSASSIN = 1,
	R_RANGED = 2,
	R_SUPPORT = 3,
	R_COUNT = 4
};

struct RoleInfo
{
	std::array<float, R_COUNT> score{}; // fit for each role (z-scored features; higher = better)
	Role primary = R_FRONT;
	bool ranged = false;
};

const RoleInfo& role_of(bc::champion_type t);
const char* role_name(Role r);

enum MapClass : int
{
	MC_COMPACT = 0, // walls and bushes: close engagements
	MC_BALANCED = 1,
	MC_OPEN = 2 // holes and plain: ranged across holes
};

struct Terrain
{
	float wall = 0, bush = 0, hole = 0, compact = 0; // shares of the map's tiles; compact = wall + bush - hole
	MapClass cls = MC_BALANCED;
};

const Terrain& terrain();
