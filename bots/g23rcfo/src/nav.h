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
	void reset_fields(); // drop every cached field (the routing walls changed)
	void new_turn() { built_this_turn = 0; }
	// Build the field if it is missing and the turn budget allows; returns true when available.
	bool ensure_group(int id, long long fuel_floor = 45000);
	bool ensure_altar(int id, long long fuel_floor = 45000);
	// Crystal shortcuts: a resumable scan of the map (local copies of the home field and terrain) collects
	// launch -> land pairs within crystal range that save many walking steps from our spawn; each group then
	// takes the best pair by its own walking field. Spread over turns with spare fuel.
	struct HopEdge
	{
		vec2 l, t;
		int save;
		int home; // steps from our spawn to the launch tile
	};
	std::vector<HopEdge> hop_edges;
	int hop_scan = -1; // next row to scan; -1 not started, -2 done
	int hop_x = 0;		// next column within that row
	std::vector<std::uint16_t> home_lin;
	std::vector<std::uint8_t> holes_lin, blocked_lin; // packed bits: holes, camp spawn tiles
	void hop_scan_step(long long fuel_floor, int turn_round);
	bool ensure_hop(int id);
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
// P.spread_vs_splash: tiles to avoid below enemy reach (next to an ally under a splash threat); null when off.
inline const bc::bitboard* g_soft_avoid = nullptr;
// P.v26_nowake: dash landings that would hit a sleeping camp we do not farm (a damaging dash wakes its group); null when off.
inline const bc::bitboard* g_dash_avoid = nullptr;
inline bool g_exit_first = false; // P.flee_exit: go_home_step while fleeing (step_field may take a sideways exit step)
inline const bc::bitboard* g_hard_block = nullptr; // P.g23_divefilter: tiles no walk / dash may enter this turn (set and cleared by Brain)
