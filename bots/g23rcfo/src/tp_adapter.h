// tp_adapter.h: tools/teamplan inside GOD v10 (the test copy of TEAMPLAN.md section 9; tools/teamplan/v10_adapter.patch). Every use is
// behind a P.tp_* switch (params.h), and with all of them 0 nothing here runs: the copy plays v10's games.
#pragma once
#include <cstdint>
#include <vector>

#include "common.h"
#include "teamplan/assign.h"
#include "teamplan/bag.h"
#include "teamplan/focus.h"
#include "teamplan/kit.h"
#include "teamplan/params.h"
#include "teamplan/tiebreak.h"
#include "teamplan/timing.h"

namespace tpa
{
const teamplan::Params& params();	   // the module defaults with the test copy's overrides (P.tp_tb_cap, P.tp_own_bonus)
const teamplan::Consts& consts();	   // from the SDK, once
const teamplan::Kit& kit_of(int type); // from the engine design, once per type
int pick_of_type(int type);			   // the draft pick a body type belongs to (SDK enum order: picks 0-2 = bodies 0-2, 3 = bodies 3-4, ...)
int bodies_of_type(int type);		   // bodies that die with a kill of this type (a pick of two bodies dies together)

// Draft side (P.tp_own): after our pick of this draft turn (`last_pick`, -1 if none), plan the ownership of every group for the bodies
// picked so far and write the OWN block to draft memory: offsets 8.. (bytes 0-7 are v10's header area, which its champions read only
// with P.dm_plan): magic 0x54, version 1, bodies n, groups G, 6 body types (255 = none), G owners (body slot, 255 = none), XOR checksum.
void draft_write_own(int last_pick);

struct Own
{
	bool ok = false;
	int slot = -1; // our body slot in the block
	std::vector<std::uint8_t> owner;
};
// Champion side: read and check the block (the map's group count, the checksum, our type in its body list).
Own read_own(int my_type, int n_groups);
} // namespace tpa
