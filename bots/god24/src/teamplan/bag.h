// teamplan/bag.h: bag rules (TEAMPLAN.md 4, U2'). A killer takes the whole carried bag, and in top-team games about 110 gems a game
// change hands that way, so: fight with an empty bag, bank before a fight that can wait, hunt visible big bags only with local numbers,
// and bank at once when the team's bags win the game. Python twin: tools/teamplan/bag.py.
#pragma once
#include "kit.h"

namespace teamplan
{
// The fight bar: the advantage a body needs before it fights, raised by what it carries.
inline double fight_bar(double base, int bag, const Params& p) { return base * (1.0 + bag / p.bag_fight_scale); }

// Bank (or recall to bank) before an avoidable fight: the bag is big and an enemy is about to reach us (`enemy_dist` tiles, its reach
// `enemy_reach`, our walk to where we bank `walk_bank` rounds).
inline bool bank_before_fight(int bag, int enemy_dist, int enemy_reach, int walk_bank, bool avoidable, const Params& p)
{
	return avoidable && bag >= p.bag_fight && enemy_dist <= enemy_reach + 3 && walk_bank <= enemy_dist + p.bag_fight / 10;
}

// Target-score bonus for a visible enemy carrying `enemy_bag`, when we have at least their numbers here (`ours`, `theirs`: bodies within
// a fight radius of the target). 0 without local numbers: hunting alone into their group loses (Cout for Clout's 47-vs-50 ablation).
inline double hunt_bonus(int enemy_bag, int ours, int theirs, const Params& p)
{
	if (ours < theirs || enemy_bag < p.hunt_bag)
		return 0.0;
	return p.hunt_bonus * enemy_bag / p.hunt_bag;
}

// The team's banked gems plus the bags we know about reach the win: bank now, whatever else the score says.
inline bool bank_now_wins(int banked, int own_bag, int allies_bags, const Consts& c) { return banked + own_bag + allies_bags >= c.winning_gems; }
} // namespace teamplan
