#include "learn.h"

#include "comms.h"
#include "params.h"
#include "world.h"

#include <cmath>

Learner& learner()
{
	static Learner l;
	return l;
}

void Learner::init(int width, int height)
{
	cw = (width + CELL - 1) / CELL;
	ch = (height + CELL - 1) / CELL;
	pain.assign(static_cast<std::size_t>(cw * ch), 0.f);
	q = { P.q0_spread, P.q0_grouped, P.q0_push };
}

void Learner::add_pain(vec2 p, float amount)
{
	if (!P.learn_enabled || !P.learn_pain || pain.empty() || p.x < 0 || p.y < 0)
		return;
	const int cx = p.x / CELL, cy = p.y / CELL;
	for (int dy = -1; dy <= 1; ++dy)
		for (int dx = -1; dx <= 1; ++dx)
		{
			const int x = cx + dx, y = cy + dy;
			if (x < 0 || y < 0 || x >= cw || y >= ch)
				continue;
			float& v = pain[static_cast<std::size_t>(y * cw + x)];
			v = std::max(0.f, v + ((dx || dy) ? 0.5f * amount : amount));
		}
}

float Learner::pain_at(vec2 p) const
{
	if (pain.empty() || p.x < 0 || p.y < 0)
		return 0.f;
	const int x = std::min(cw - 1, p.x / CELL), y = std::min(ch - 1, p.y / CELL);
	return pain[static_cast<std::size_t>(y * cw + x)];
}

void Learner::on_enemy_killed_near(vec2 p, int round)
{
	if (!P.learn_enabled)
		return;
	add_pain(p, -P.pain_kill_relief);
	if (round - fight_round <= 10)
		fight_bias = std::min(P.fight_bias_max, fight_bias + P.fight_learn_rate * 0.5f);
}

float Learner::fight_scale() const { return P.learn_fight ? std::exp(fight_bias) : 1.f; }

void Learner::tick(int round, bool leader, bool me_alive)
{
	if (!P.learn_enabled)
		return;
	auto& W = world();
	// Decay the pain map (half-life ~ pain_half_life rounds).
	if (round > pain_round)
	{
		const float k = std::pow(0.5f, static_cast<float>(round - pain_round) / std::max(1.f, P.pain_half_life));
		for (auto& v : pain)
			v *= k;
		pain_round = round;
	}
	// Our own death right after choosing a fight: punish the fight model.
	if (was_alive && !me_alive && round - fight_round <= 8)
		fight_bias = std::max(-P.fight_bias_max * 2.f, fight_bias - P.fight_learn_rate);
	was_alive = me_alive;

	// Deaths on both sides from the global alive flags (readable for every champion).
	if (ally_alive.size() != W.allies.size())
		ally_alive.assign(W.allies.size(), true);
	if (enemy_alive.size() != W.enemies.size())
		enemy_alive.assign(W.enemies.size(), true);
	const auto& C = comms();
	for (std::size_t i = 0; i < W.allies.size(); ++i)
	{
		std::int32_t a = 1;
		if (bc::detail::sdk_champion_is_alive(W.allies[i].handle, &a) != 0)
			continue;
		if (ally_alive[i] && !a)
		{
			++ally_deaths;
			// Where: last seen position, else the camp it claimed.
			vec2 at = W.allies[i].pos;
			const int cg = i < 6 ? C.claim[i] : -1;
			if (!W.allies[i].visible && cg >= 0 && cg < static_cast<int>(W.groups.size()))
				at = W.groups[static_cast<std::size_t>(cg)].center;
			if (at.x >= 0)
			{
				add_pain(at, P.pain_death);
				if (W.dist_home(at) <= W.dist_away(at))
					++ally_deaths_our_half;
			}
		}
		ally_alive[i] = a != 0;
	}
	for (std::size_t i = 0; i < W.enemies.size(); ++i)
	{
		std::int32_t a = 1;
		if (bc::detail::sdk_champion_is_alive(W.enemies[i].handle, &a) != 0)
			continue;
		if (enemy_alive[i] && !a)
			++enemy_deaths;
		enemy_alive[i] = a != 0;
	}

	if (!leader || !P.learn_stance)
		return;
	if (round - window_start < P.learn_window)
		return;
	// ---- end of a window: score the stance we played, then choose the next one.
	const int ours = static_cast<int>(bc::global_submitted_gems(team::ally));
	const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
	const float len = static_cast<float>(round - window_start);
	const float gem_rate = 10.f * static_cast<float>((ours - ours0) - (theirs - theirs0)) / std::max(1.f, len);
	const int dk = enemy_deaths - enemy_deaths0;
	const int dd = ally_deaths - ally_deaths0;
	const float r = gem_rate + P.reward_kill * static_cast<float>(dk) - P.punish_death * static_cast<float>(dd);
	last_reward = r;
	q[static_cast<std::size_t>(stance)] += P.learn_rate * (r - q[static_cast<std::size_t>(stance)]);
	++plays[static_cast<std::size_t>(stance)];
	// Context: deaths on our own half mean we are being invaded; winning fights invites pushing.
	const int invaded = ally_deaths_our_half - our_half0;
	std::array<float, STANCE_COUNT> pref = q;
	pref[STANCE_GROUPED] += P.ctx_invaded * static_cast<float>(invaded);
	pref[STANCE_PUSH] += P.ctx_fights * static_cast<float>(dk - dd);
	pref[static_cast<std::size_t>(stance)] += P.stance_hysteresis;
	int best = stance;
	for (int s = 0; s < STANCE_COUNT; ++s)
		if (pref[static_cast<std::size_t>(s)] > pref[static_cast<std::size_t>(best)])
			best = s;
	stance = best;
	window_start = round;
	ours0 = ours;
	theirs0 = theirs;
	ally_deaths0 = ally_deaths;
	enemy_deaths0 = enemy_deaths;
	our_half0 = ally_deaths_our_half;
}
