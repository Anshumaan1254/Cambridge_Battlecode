// mi_game.h: the champion side of draft memory version 2 (GOD v12; docs/DRAFT_MEMORY.md, mapintel/dmem2.h Reader). Every body reads
// the image its process got at startup; a missing or invalid block leaves the matching switch without effect (GOD v10's play).
#pragma once
#include <cstdint>

namespace mig
{
// Brain::init: read TEAM, OWN, BODY, CODE, M and L, find the map in known_maps.h (from the M block's fingerprint).
void init(int my_type, int ngroups);
// End of a game turn: the in-game OWN recompute (resumable, docs/DRAFT_MEMORY.md 7) when the draft's OWN covers fewer bodies than the
// roster and P.mi_own is on; it runs only with fuel to spare.
void tail();
// The group's score multiplier (1 when every switch is off or the data is missing): P.mi_own (OWN owner = our slot), P.mi_next (the
// step-7 next-target model's two best groups after our last capture), P.mi_open (plan 1's first targets before our first capture).
float group_mult(int g, int round);
// A capture of group g landed for this body in this round.
void on_capture(int g, int round);
// BODY bytes 12-13 (econ model, LEARNED): the bank bag in gems and the retreat health in percent; -1 when missing.
int bank_bag();
int retreat_pct();
// The draft's data as the live layout needs it (P.mi_live): the TEAM body types by slot (-1 none; returns the count), the CODE rally
// tiles (tile index y * W + x; returns the count).
int team_types(int out[6]);
int rallies(int out[8]);
bool have_image();
// The draft's map fingerprint (mapintel/fingerprint.h, from the M block; 0 when the block is missing).
std::uint64_t map_fp();
} // namespace mig
