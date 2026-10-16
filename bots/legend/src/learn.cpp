#include "learn.h"

#include "world.h"

Learner& learner()
{
	static Learner l;
	return l;
}

void Learner::team_update(int round)
{
	if (round == last_round)
		return;
	auto& W = world();
	if (ally_alive.size() != W.allies.size())
		ally_alive.assign(W.allies.size(), 1);
	if (enemy_alive.size() != W.enemies.size())
		enemy_alive.assign(W.enemies.size(), 1), enemy_burst.assign(W.enemies.size(), 0.f);
	for (std::size_t i = 0; i < W.allies.size(); ++i)
	{
		std::int32_t a = 1;
		if (bc::detail::sdk_champion_is_alive(W.allies[i].handle, &a) != 0)
			continue;
		if (ally_alive[i] && !a)
			++ally_deaths;
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
	const int o = static_cast<int>(bc::global_submitted_gems(team::ally));
	const int t = static_cast<int>(bc::global_submitted_gems(team::enemy));
	if (last_round >= 0)
	{
		const int dt = std::max(1, round - last_round);
		// ~150-round memory: tributes are lumpy, so the rate is smoothed over several of them.
		const float a = std::min(1.f, static_cast<float>(dt) / 150.f);
		our_rate += a * (static_cast<float>(o - ours) / static_cast<float>(dt) - our_rate);
		their_rate += a * (static_cast<float>(t - theirs) / static_cast<float>(dt) - their_rate);
	}
	ours = o, theirs = t, last_round = round;
}

void Learner::sample_out(float obs, float pred)
{
	out_obs = 0.98f * out_obs + obs;
	out_pred = 0.98f * out_pred + pred;
}

void Learner::sample_in(float obs, float pred)
{
	in_obs = 0.98f * in_obs + obs;
	in_pred = 0.98f * in_pred + pred;
}

int Learner::eta_ours() const
{
	const int left = static_cast<int>(bc::constants::winning_gems) - ours;
	return our_rate > 0.05f ? static_cast<int>(static_cast<float>(left) / our_rate) : BIG;
}

int Learner::eta_theirs() const
{
	const int left = static_cast<int>(bc::constants::winning_gems) - theirs;
	return their_rate > 0.05f ? static_cast<int>(static_cast<float>(left) / their_rate) : BIG;
}
