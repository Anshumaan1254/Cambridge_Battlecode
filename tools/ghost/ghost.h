// Test-only ghost opponent (tools/ghost/make_ghost.py): replays a ladder team's recorded actions for the first GHOST_ROUNDS rounds.
#pragma once
bool ghost_draft(); // true when this map has a script: the recorded team's picks
bool ghost_turn();	// true when this round's recorded actions were played (the turn is used)
