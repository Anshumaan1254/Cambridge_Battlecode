// GOD v24 (docs/plans/god24_plan.md): fight fixes F1-F5 and economy fixes E1-E3, always on since GOD v25 (the g24_* parameters are values).
// The hooks sit in brain.cpp (combat(), group_score(), capture_group(), bank_min()) and g23.cpp (g23_veto()); the helpers are here.

#include "brain.h"
#include "nav.h"

#include <cmath>
#include <cstdio>

namespace
{
// an enemy's basic-attack reach next turn: a walk step for melee, two more with its dash ready
int hit_reach(const Enemy& e)
{
	return e.kit.attack_range + (e.kit.ranged ? 0 : 1) + (e.ready(e.kit.dash) ? 2 : 0);
}
} // namespace

// ---------------------------------------------------------------------------------------------- F1 dash out of a fight we leave

// F1 g24_flee_dash bit 1: leaving a fight with a chaser that still hits us after a walk step (melee within 3, +2 with its dash ready; ranged
// within its range + 1), the dash goes first. mob_dash() keeps a damaging dash (Heart of Ruin) for the fight while an enemy is within
// strike_dash_hold, so a fleeing HoR walked one tile a round being hit (ladder: HoR dashed on 12% of retreats with the dash ready, the top
// teams 70%). Landing tile within dash range: fewest enemies whose next-turn reach covers it, then nearest home; never an awake camp's
// reach or a tile that wakes a sleeping camp. True when we dashed (the caller still walks).
bool Brain::g24_dash_out(const std::vector<Enemy*>& E)
{
	auto& W = world();
	if (kit.dash < 0 || !ready(kit.dash) || W.ally_spawn.is_set(pos))
		return false;
	bool chased = false;
	for (auto* e : E)
	{
		if (W.enemy_spawn.is_set(e->pos))
			continue;
		const int d = cheb(pos, e->pos);
		chased |= e->kit.ranged ? d <= e->kit.attack_range + 1 : d <= 3 + (e->ready(e->kit.dash) ? 2 : 0);
	}
	if (!chased)
		return false;
	auto covered = [&](vec2 q) {
		int n = 0;
		for (auto* e : E)
			n += !W.enemy_spawn.is_set(e->pos) && cheb(q, e->pos) <= hit_reach(*e);
		return n;
	};
	const int rng = std::max(1, static_cast<int>(kit.dash_range));
	const int rad = std::max(0, static_cast<int>(kit.dash_radius));
	const bc::bitboard blocked = Nav::blocked_now(pos);
	const int here_n = covered(pos), here_d = W.dist_home(pos);
	vec2 best = pos;
	int best_n = here_n, best_d = here_d;
	for (int dy = -rng; dy <= rng; ++dy)
		for (int dx = -rng; dx <= rng; ++dx)
		{
			const vec2 q{ pos.x + dx, pos.y + dy };
			if ((dx == 0 && dy == 0) || !bc::map::is_in_bounds(q) || blocked.is_set(q) || camp_danger.is_set(q))
				continue;
			if ((std::abs(dx) == 2 || std::abs(dy) == 2) && bc::map::walls().is_set(vec2{ pos.x + dx / 2, pos.y + dy / 2 }))
				continue;
			if (kit.dash_mod > 0.f && wakes_sleeper(q, rad))
				continue;
			const int dq = W.dist_home(q);
			if (dq >= BIG)
				continue;
			const int nq = covered(q);
			if (nq < best_n || (nq == best_n && dq < best_d))
				best = q, best_n = nq, best_d = dq;
		}
	if (best == pos || (best_n >= here_n && best_d > here_d - 2))
		return false; // neither out of a reach nor two steps nearer home: keep the dash
	try
	{
		if (bc::self().abilities()[static_cast<std::size_t>(kit.dash)].use(best))
		{
			pos = best;
			cast_done = true;
			after_move(true);
#ifdef G24_TRACE
			std::printf("G24 flee_dash body=%d r=%d covered %d->%d home %d->%d\n", W.my_index, round, here_n, best_n, here_d, best_d);
#endif
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

// ---------------------------------------------------------------------------------------------- E1 hold a contested big group

// E1 g24_hold: the isolated pre-emptive flee (combat(): no ally within 5 and adv < isolated_flee_adv 1.5) does not fire while we work a
// group that we stand within attack range + 2 of, at adv >= g24_hold_r and health >= g24_hold_hp. A group qualifies when it is big
// (>= g24_hold_gems), when we hit it in the last 2 rounds, or when it is on our half (nearer our spawn than theirs). Ladder: at a 1 v 1
// contact on a contested big respawn at hp >= 0.8 we left 35% (top 30: 18%) and took 27% of those cycles (top 30: 50%); our hit share
// under contact is half the opponents' and they capture more on our half. The outmatched, cornered, burst and real-fight rules are
// untouched: a blanket "flee less" (_fight1) lost 101.
bool Brain::g24_hold_ok(float adv) const
{
	auto& W = world();
	if (task_group < 0 || task_group >= static_cast<int>(W.groups.size()) || adv < P.g24_hold_r || hp < P.g24_hold_hp * max_hp)
		return false;
	const auto& g = W.groups[static_cast<std::size_t>(task_group)];
	if (g.st != ST_ALIVE && g.st != ST_REWARD)
		return false;
	const bool worked = round - target_hit_round <= 2;
	const bool own = g.d_ally < g.d_enemy;
	if (g.gems < P.g24_hold_gems && !worked && !own)
		return false;
	int d = BIG;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
		if (g.st == ST_REWARD || g.hp[i] > 0)
			d = std::min(d, cheb(pos, g.camps[i].pos));
	return d <= kit.attack_range + 2;
}

// ---------------------------------------------------------------------------------------------- E2 scarce maps

// E2 g24_scarce: total group gems per champion of a team <= g24_scarce_gpc (our worst quarter of maps: 41% wins vs 59% on the richest; the
// top 30 are flat across them). Computed once.
bool Brain::g24_scarce_map() const
{
	if (g24_scarce_state < 0)
	{
		const auto& W = world();
		int gems = 0;
		for (const auto& g : W.groups)
			gems += g.gems;
		g24_scarce_state = gems <= P.g24_scarce_gpc * std::max(1, W.team_champs) ? 1 : 0;
	}
	return g24_scarce_state == 1;
}

// ---------------------------------------------------------------------------------------------- E3 Marcella funnel

// E3 g24_marc_funnel bit 1: the index of our Marcella when this reward should go to her: she is alive, seen this round, not channelling and
// within g24_mf_r steps of it (or she is us); the reward pays (gems >= 10 or gold >= 60) and no enemy stands within 4 of it. -1 otherwise.
// Ladder: the teams that beat us route rewards and quick banks through Marcella (2 gold a banked gem): theirs takes 14.6 captures a game, ours
// 5.9; their team has +31% shards at r600 and their Marcella kills 4.5 of ours a game.
int Brain::g24_marc_for(const Group& g) const
{
	auto& W = world();
	if (g.st != ST_REWARD || (g.gems < 10 && g.gold < 60))
		return -1;
	for (const auto& e : W.enemies)
		if (e.alive && e.visible && cheb(e.pos, g.center) <= g.radius + 4)
			return -1;
	if (type == bc::champion_type::marcella)
		return nav().group_dist(g, pos) <= P.g24_mf_r ? W.my_index : -1;
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
	{
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (i == W.my_index || a.type != bc::champion_type::marcella || !a.alive || !a.visible || a.seen_round != round || a.channeling)
			continue;
		if (nav().group_dist(g, a.pos) <= P.g24_mf_r)
			return i;
	}
	return -1;
}

// E3: a body (not Marcella) at a reward she should take: off its tiles, wait next to it up to g24_mf_wait rounds, step aside when she is on
// it. True when the turn was used; false: capture it ourselves (she did not come, or the hand-off does not apply).
bool Brain::g24_hold_for_marc(Group& g)
{
	auto& W = world();
	if (type == bc::champion_type::marcella)
		return false;
	const int mi = g24_marc_for(g);
	if (mi < 0)
	{
		g24_mf_g = -1;
		return false;
	}
	if (g24_mf_g != g.id)
		g24_mf_g = g.id, g24_mf_since = round;
	const auto& m = W.allies[static_cast<std::size_t>(mi)];
	const bool she_on = g.mask.is_set(m.pos);
	if (!she_on && round - g24_mf_since >= P.g24_mf_wait)
		return false; // she did not come: take it
	if (g.mask.is_set(pos))
	{
		bc::bitboard off;
		off.draw_chebyshev(pos, 1.f);
		off &= ~g.mask & ~W.walls & ~W.ally_occ & ~W.enemy_occ & ~W.camp_occ & ~camp_danger;
		if (off.is_empty() || !step(off, false, false))
			return false; // no tile beside it: capture (a split still beats leaving it)
	}
	if (she_on)
	{
		blacklist[static_cast<std::size_t>(g.id)] = round + 8;
		task = T_NONE;
	}
	else
		task = T_WAIT;
#ifdef G24_TRACE
	std::printf("G24 marc_hold body=%d r=%d g=%d she_on=%d waited=%d\n", W.my_index, round, g.id, static_cast<int>(she_on), round - g24_mf_since);
#endif
	return true;
}
