#include "territory.h"
#include "comms.h"
#include "params.h"
#include "world.h"
#include <algorithm>
#include <array>

Territory& territory()
{
	static Territory t;
	return t;
}

namespace
{
int gdist(const Group& a, const Group& b)
{
	// A lower bound of the walk between two groups: no shorter than the straight line, nor than the change of either spawn's walk.
	int d = cheb(a.center, b.center);
	if (a.d_ally < BIG && b.d_ally < BIG)
		d = std::max(d, std::abs(a.d_ally - b.d_ally));
	if (a.d_enemy < BIG && b.d_enemy < BIG)
		d = std::max(d, std::abs(a.d_enemy - b.d_enemy));
	return d;
}

float gvalue(const Group& g, float gold_value) { return static_cast<float>(g.gems) + gold_value * static_cast<float>(g.gold); }
} // namespace

void Territory::build(const World& W, float gold_value)
{
	const int n = static_cast<int>(W.groups.size());
	region_of.assign(static_cast<std::size_t>(n), -1);
	chain.assign(static_cast<std::size_t>(n), 0.f);
	regions.clear();
	// k-centre clustering (farthest point first): a new seed at the group farthest from every seed until each group is within the
	// cut of one, then each group joins its nearest seed. O(groups x regions): a complete-linkage merge is O(groups^3) and ran
	// the bodies out of fuel for whole rounds on the larger maps.
	std::vector<int> id;
	for (int i = 0; i < n; ++i)
		if (W.groups[static_cast<std::size_t>(i)].d_ally < BIG)
			id.push_back(i);
	const int m = static_cast<int>(id.size());
	if (m == 0)
	{
		built = true;
		return;
	}
	const int cut = std::max(P.bb_region_d, (W.W + W.H) / std::max(1, P.bb_region_div));
	std::vector<int> near_d(static_cast<std::size_t>(m), BIG), near_s(static_cast<std::size_t>(m), -1);
	int next = 0;
	float bv = -1.f;
	for (int a = 0; a < m; ++a)
	{
		const float v = gvalue(W.groups[static_cast<std::size_t>(id[static_cast<std::size_t>(a)])], gold_value);
		if (v > bv)
			bv = v, next = a; // the first seed: the richest group
	}
	int seeds = 0;
	while (next >= 0)
	{
		const auto& sg = W.groups[static_cast<std::size_t>(id[static_cast<std::size_t>(next)])];
		int far = -1, fd = cut;
		for (int a = 0; a < m; ++a)
		{
			const int d = gdist(W.groups[static_cast<std::size_t>(id[static_cast<std::size_t>(a)])], sg);
			if (d < near_d[static_cast<std::size_t>(a)])
				near_d[static_cast<std::size_t>(a)] = d, near_s[static_cast<std::size_t>(a)] = seeds;
			if (near_d[static_cast<std::size_t>(a)] > fd)
				fd = near_d[static_cast<std::size_t>(a)], far = a;
		}
		++seeds;
		next = far;
	}
	regions.resize(static_cast<std::size_t>(seeds));
	for (int a = 0; a < m; ++a)
	{
		const int k = near_s[static_cast<std::size_t>(a)];
		const int gi = id[static_cast<std::size_t>(a)];
		region_of[static_cast<std::size_t>(gi)] = k;
		regions[static_cast<std::size_t>(k)].groups.push_back(gi);
	}
	for (auto& R : regions)
	{
		float sx = 0, sy = 0, st = 0, sw = 0;
		for (int gi : R.groups)
		{
			const auto& g = W.groups[static_cast<std::size_t>(gi)];
			const float v = gvalue(g, gold_value);
			const float w = std::max(1.f, v);
			if (g.respawn > 0)
				R.rate += v / static_cast<float>(g.respawn);
			sx += w * static_cast<float>(g.center.x), sy += w * static_cast<float>(g.center.y), sw += w;
			const int de = g.d_enemy < BIG ? g.d_enemy : g.d_ally;
			st += w * static_cast<float>(g.d_ally) / static_cast<float>(std::max(1, g.d_ally + de));
		}
		R.center = { static_cast<int>(sx / std::max(1.f, sw)), static_cast<int>(sy / std::max(1.f, sw)) };
		R.t = st / std::max(1.f, sw);
	}
	// Chain neighbours (each group's NB nearest groups of its region) are filled a few groups per turn by nb_step: a region of
	// dozens of groups (00lanes) made even a one-time all-pairs pass cost a turn of fuel.
	nb_id.assign(static_cast<std::size_t>(n * NB), -1);
	nb_w.assign(static_cast<std::size_t>(n * NB), 0.f);
	nb_done = 0;
	built = true;
}

void Territory::nb_step(const World& W, long long fuel_floor)
{
	const int n = static_cast<int>(W.groups.size());
	while (nb_done < n && bc::fuel_remaining() > fuel_floor)
	{
		const int gi = nb_done++;
		const int r = of(gi);
		if (r < 0)
			continue;
		const auto& g = W.groups[static_cast<std::size_t>(gi)];
		std::array<int, NB> bd{}, bi{};
		int cnt = 0;
		for (int hi : regions[static_cast<std::size_t>(r)].groups)
		{
			if (hi == gi)
				continue;
			const int d = cheb(g.center, W.groups[static_cast<std::size_t>(hi)].center);
			int k = cnt < NB ? cnt++ : NB; // insertion into the NB nearest so far
			if (k == NB && d >= bd[NB - 1])
				continue;
			if (k == NB)
				k = NB - 1;
			while (k > 0 && bd[static_cast<std::size_t>(k - 1)] > d)
			{
				bd[static_cast<std::size_t>(k)] = bd[static_cast<std::size_t>(k - 1)], bi[static_cast<std::size_t>(k)] = bi[static_cast<std::size_t>(k - 1)];
				--k;
			}
			bd[static_cast<std::size_t>(k)] = d, bi[static_cast<std::size_t>(k)] = hi;
		}
		for (int k = 0; k < cnt; ++k)
		{
			nb_id[static_cast<std::size_t>(gi * NB + k)] = bi[static_cast<std::size_t>(k)];
			nb_w[static_cast<std::size_t>(gi * NB + k)] = 1.f / (1.f + static_cast<float>(bd[static_cast<std::size_t>(k)]) / 6.f);
		}
	}
}

void Territory::tick(int round, const World& W, float gold_value)
{
	if (!built || tick_round == round)
		return;
	tick_round = round;
	const auto& C = comms();
	// Presence: our bodies seen this round (ourselves included) and the groups the team claims; theirs from the groups' enemy sightings.
	for (std::size_t k = 0; k < W.allies.size() && k < 6; ++k)
	{
		const auto& a = W.allies[k];
		if (!a.alive)
			continue;
		const int cg = C.claim[k];
		if (cg >= 0 && cg < static_cast<int>(W.groups.size()))
		{
			const int r = of(cg);
			// A claim counts once the body is close to the group: a claim alone is a walk that may never arrive.
			if (r >= 0 && (static_cast<int>(k) == W.my_index || (a.visible && a.seen_round == round)) && cheb(a.pos, W.groups[static_cast<std::size_t>(cg)].center) <= 8)
				regions[static_cast<std::size_t>(r)].our_round = round;
		}
	}
	for (auto& R : regions)
	{
		R.avail = 0.f;
		for (int gi : R.groups)
		{
			const auto& g = W.groups[static_cast<std::size_t>(gi)];
			R.their_round = std::max(R.their_round, g.enemy_round);
			if (g.st != ST_RESPAWN || g.ready_round - round <= P.bb_region_soon)
				R.avail += gvalue(g, gold_value);
		}
	}
	ours_rate = theirs_rate = 0.f;
	front = -1;
	front_t = 0.f;
	for (int k = 0; k < static_cast<int>(regions.size()); ++k)
	{
		auto& R = regions[static_cast<std::size_t>(k)];
		const bool us = round - R.our_round <= P.bb_hold_rounds;
		const bool them = round - R.their_round <= P.bb_hold_rounds;
		R.control = us && (!them || R.our_round > R.their_round) ? 1 : them ? -1 : 0;
		if (R.control > 0)
		{
			ours_rate += R.rate;
			if (front < 0 || R.t > front_t)
				front = k, front_t = R.t;
		}
		else if (R.control < 0)
			theirs_rate += R.rate;
	}
	share = ours_rate + theirs_rate > 0.f ? ours_rate / (ours_rate + theirs_rate) : 0.5f;
	// Chain value: what a body standing on a group can farm next without a long walk (its NB nearest region groups that are ready).
	const int n = static_cast<int>(W.groups.size());
	for (int gi = 0; gi < n && gi * NB < static_cast<int>(nb_id.size()); ++gi)
	{
		float c = 0.f;
		for (int k = 0; k < NB; ++k)
		{
			const int hi = nb_id[static_cast<std::size_t>(gi * NB + k)];
			if (hi < 0)
				break;
			const auto& h = W.groups[static_cast<std::size_t>(hi)];
			if (h.st == ST_RESPAWN && h.ready_round - round > P.bb_region_soon)
				continue;
			c += gvalue(h, gold_value) * nb_w[static_cast<std::size_t>(gi * NB + k)];
		}
		chain[static_cast<std::size_t>(gi)] = c;
	}
}
