// teamplan/focus.h: what a kill is worth (TEAMPLAN.md 4, P1: Don't @ Me, food, SPAARK). Gem units: the bag the victim carries (the
// killer takes it), the kill gold, and the farming the enemy team loses while the body is dead (respawn time x one body's rate).
// Python twin: tools/teamplan/focus.py.
#pragma once
#include "kit.h"

namespace teamplan
{
// `bodies`: bodies that die with the kill (2 for a pick that is two bodies dying together), `enemy_n`: their team size.
inline double kill_value(int enemy_bag, int bodies, int enemy_n, const Consts& c, const Params& p)
{
	const double rate = p.team_rate / (enemy_n > 0 ? enemy_n : 1);
	return enemy_bag + p.gold_gems * c.kill_gold + bodies * c.respawn_time * rate;
}

// Priority of a target: kill value per round it takes to kill it (`rounds_to_kill` >= 0), scaled so that kv_ref doubles it.
inline double target_priority(double kv, double rounds_to_kill, const Params& p) { return (1.0 + kv / p.kv_ref) / (1.0 + rounds_to_kill); }
} // namespace teamplan
