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
	// Decay the pain map (half-life ~ pain_half_life rounds), every few rounds: it is read as a cost, so a
	// few rounds of lag do not matter and decaying every turn cost fuel on every body.
	if (round - pain_round >= 8)
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

	// Deaths on both sides from the global alive flags (World refreshed them this turn, alive or dead).
	if (ally_alive.size() != W.allies.size())
		ally_alive.assign(W.allies.size(), true);
	if (enemy_alive.size() != W.enemies.size())
		enemy_alive.assign(W.enemies.size(), true);
	const auto& C = comms();
	for (std::size_t i = 0; i < W.allies.size(); ++i)
	{
		const bool a = W.allies[i].alive;
		if (ally_alive[i] && !a)
		{
			++ally_deaths;
			// Where: a sighting from the last two rounds, else the team's fresh fight alert; otherwise we do
			// not know (an old sighting or a claim kept during a recall points somewhere else entirely).
			vec2 at{ -1, -1 };
			if (round - W.allies[i].seen_round <= 2)
				at = W.allies[i].pos;
			else if (C.fresh(round, 3) && (C.alert_kind == AL_RALLY || C.alert_kind == AL_DANGER))
				at = C.alert_pos;
			if (at.x >= 0)
			{
				add_pain(at, P.pain_death);
				if (W.dist_home(at) <= W.dist_away(at))
					++ally_deaths_our_half;
			}
		}
		ally_alive[i] = a;
	}
	for (std::size_t i = 0; i < W.enemies.size(); ++i)
	{
		const bool a = W.enemies[i].alive;
		if (enemy_alive[i] && !a)
			++enemy_deaths;
		enemy_alive[i] = a;
	}

	if (P.g15_stance >= 0)
	{
		stance = P.g15_stance; // v15: a fixed team stance (every body computes the same; the leader still broadcasts it)
		return;
	}
	if (!leader || !P.learn_stance)
		return;
	if (round - window_start < P.learn_window)
		return;
	// ---- end of a window: score the stance we played (contextual bandit), then choose the next one.
	// Reward, all in gems: banked difference + kill_gems per kill - death_gems per death (a death costs a
	// minute of farming, often a bag, and pays them 50 gold), normalised to about +-1 per window. Banks
	// land in lumps of one capture, so the gem term blends in half of the previous window's.
	const int ours = static_cast<int>(bc::global_submitted_gems(team::ally));
	const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
	if (frozen)
	{
		// A window played under a counter plan says nothing about the learner's stance: restart the window.
		window_start = round;
		ours0 = ours, theirs0 = theirs, prev_diff = 0;
		ally_deaths0 = ally_deaths, enemy_deaths0 = enemy_deaths, our_half0 = ally_deaths_our_half;
		return;
	}
	const float diff = static_cast<float>((ours - ours0) - (theirs - theirs0));
	const float gem_term = 0.67f * diff + 0.33f * prev_diff;
	prev_diff = diff;
	const int dk = enemy_deaths - enemy_deaths0;
	const int dd = ally_deaths - ally_deaths0;
	const float r = (gem_term + P.kill_gems * static_cast<float>(dk) - P.death_gems * static_cast<float>(dd)) / std::max(1.f, P.reward_scale);
	last_reward = r;
	const auto si = static_cast<std::size_t>(stance);
	// Soft (exponential moving average) update of the played stance; unplayed ones drift back to their
	// priors so a single bad window cannot lock a stance out for the rest of the game.
	if (P.bandit_discount > 0.f)
		for (auto& v : q)
			v *= 1.f - P.bandit_discount; // v9 tasks T11: old windows weigh less (a changing opponent makes old lessons stale)
	q[si] += P.learn_rate * (r - q[si]);
	++plays[si];
	const std::array<float, STANCE_COUNT> q0{ P.q0_spread, P.q0_grouped, P.q0_push };
	for (std::size_t s = 0; s < STANCE_COUNT; ++s)
		if (s != si)
			q[s] += P.prior_pull * (q0[s] - q[s]);
	// Context: deaths on our own half mean we are being invaded; winning fights invites pushing.
	const int invaded = ally_deaths_our_half - our_half0;
	int n = 0;
	for (int p : plays)
		n += p;
	std::array<float, STANCE_COUNT> pref = q;
	for (std::size_t s = 0; s < STANCE_COUNT; ++s)
		pref[s] += P.ucb_c * std::sqrt(std::log(1.f + static_cast<float>(n)) / (1.f + static_cast<float>(plays[s]))); // optimism (UCB1)
	pref[STANCE_GROUPED] += P.ctx_invaded * static_cast<float>(invaded);
	pref[STANCE_PUSH] += P.ctx_fights * static_cast<float>(dk - dd);
	pref[si] += P.stance_hysteresis;
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
