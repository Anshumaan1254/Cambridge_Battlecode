// Navigation built on cached target-rooted distance fields (reverse search from each goal).
// A field rooted at a camp group gives, at any tile, the walking steps to that group; stepping is a neighbour lookup.
// Fields are computed lazily and a few per turn, so no turn pays for a full-map search it does not need.
#pragma once
#include "world.h"

struct Nav
{
	std::vector<Field> group_fields; // one per camp group, rooted at its spawn tiles
	std::vector<Field> altar_fields; // one per altar, rooted at its free neighbours
	int built_this_turn = 0;

	void init();
	void new_turn() { built_this_turn = 0; }
	// Build the field if it is missing and the turn budget allows; returns true when available.
	bool ensure_group(int id);
	bool ensure_altar(int id);
	// Steps to stand on a group tile (BIG if unknown/unreachable); estimate from Chebyshev when the field is missing.
	int group_dist(const Group& g, vec2 from, bool allow_estimate = true);
	int altar_dist(int id, vec2 from, bool allow_estimate = true);

	// Dynamic obstacles for this turn (terrain, visible units, teleports), excluding `me`.
	static bc::bitboard blocked_now(vec2 me);

	// Step along a field until its value is <= stop_at. Uses dash when it saves at least two steps.
	// Soft-avoids `avoid` tiles. Falls back to a dynamic search when units block every improving step.
	static bool step_field(vec2& pos, const Field& field, int stop_at, const bc::bitboard* avoid, int dash_slot, bool can_move,
						   const bc::bitboard& fallback_goals);
	// One step (plus optional dash) toward any goal tile using a fresh dynamic search.
	static bool step_to(vec2& pos, const bc::bitboard& goals, const bc::bitboard* avoid, int dash_slot, bool can_move);
};

Nav& nav();
