#pragma once

// Pick one champion for the current draft round and write the team plan to draft memory.
void play_draft();

// The 17 official maps (maps/comp, the ladder pool), recognised from the size and the camp mix so draft and game
// turns agree without draft memory; -1 on any other map. Cached after the first call.
enum OfficialMap { OM_NONE = -1, OM_AMBUSH, OM_COLLISION, OM_CONTEST, OM_CORNERS, OM_EIGHT, OM_ELKRING, OM_EXPANSE,
	OM_FRAGMENT, OM_INTERLOCK, OM_LANES, OM_MONOLITH, OM_PACKS, OM_PILGRIMAGE, OM_ROWS, OM_RUSHBAIT, OM_STAMPEDE, OM_SWIRL };
int official_map();
