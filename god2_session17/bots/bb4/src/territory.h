// BB4 territory: the camp groups clustered into regions once per map, and per round who holds each region.
//
// Regions: k-centre clustering (farthest point first) of the groups on a walking-distance lower bound (Chebyshev between the centres,
// and the differences of the walks from each spawn), every group within the cut (P.bb_region_d, at least (W + H) /
// P.bb_region_div) of its region's seed, so a region is a part of the map whose groups a body chains on foot. Each
// region knows its value rate (gems + gold value per respawn) and its place between the spawns (t: 0 at our spawn, 1 at theirs).
//
// Control (per body, from its own sightings and the team's claims): a region is ours while an ally farmed or stood in it after the
// last enemy sighting there, theirs while an enemy was seen there after us. The furthest region we hold (largest t) is our front
// line into their side; the value share of the regions we hold is the territory score the team plays to (brain.cpp, update_mode).
#pragma once
#include "common.h"

struct World;

struct Region
{
	std::vector<int> groups;
	vec2 center{ -1, -1 };
	float rate = 0.f;	// value per round when every group is farmed at its respawn
	float t = 0.5f;		// walk-share position: 0 = our spawn, 1 = theirs
	int our_round = -1000, their_round = -1000;
	float avail = 0.f;	// value of the groups ready now or within P.bb_region_soon rounds (per round)
	int control = 0;	// +1 ours, -1 theirs, 0 neutral (per round)
};

struct Territory
{
	std::vector<Region> regions;
	std::vector<int> region_of; // per group: region index (-1 unreachable)
	bool built = false;
	int tick_round = -1;
	int front = -1;			// our held region with the largest t (-1 none)
	float front_t = 0.f;	// its t
	float share = 0.5f;		// rate share of the held regions that are ours (0.5 with none held)
	float ours_rate = 0.f, theirs_rate = 0.f;
	std::vector<float> chain; // per group: value of the other ready groups in its region, nearer counting more (per round)
	static constexpr int NB = 6;	  // chain neighbours per group (the nearest in its region): keeps the per-round sum O(groups)
	std::vector<int> nb_id;		  // per group: NB neighbour group ids (-1 none)
	std::vector<float> nb_w;	  // their weights 1 / (1 + Chebyshev / 6)
	int nb_done = 0;			  // groups whose neighbours are filled
	void nb_step(const World& W, long long fuel_floor);

	void build(const World& W, float gold_value);
	void tick(int round, const World& W, float gold_value);
	int of(int gid) const { return gid >= 0 && gid < static_cast<int>(region_of.size()) ? region_of[static_cast<std::size_t>(gid)] : -1; }
};

Territory& territory();
