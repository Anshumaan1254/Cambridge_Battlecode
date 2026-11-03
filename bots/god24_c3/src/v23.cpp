// GOD v23: the modules of docs/strategy_v2/36_GOD_V23_METHOD.md, each behind a P.v23_* switch (0 = v75's behaviour).
// Progress and verification: docs/plans/god23_impl.md. Section numbers in the comments refer to the method document.
#include "brain.h"

#include <cmath>

namespace
{
using I = bc::item_type;
using CT = bc::champion_type;

void add(std::vector<I>& v, I it, int n)
{
	for (int i = 0; i < n; ++i)
		v.push_back(it);
}

// Shards of one family in one stat: monster 0, power 1, durability 2, treasure 3, jungle 4, home 5, bruiser 6, tribute 7, capture 8,
// prospector 9 (x6); strength 0, focus 1, health 2 (x2); +1 is the emblem.
I shard(int fam, int stat) { return I{ static_cast<std::uint32_t>(fam * 6 + stat * 2) }; }
constexpr int MONSTER = 0, POWER = 1, DURABILITY = 2, TREASURE = 3, JUNGLE = 4, BRUISER = 6, TRIBUTE = 7;
constexpr int STR = 0, FOC = 1, HP = 2;
} // namespace

// ---------------------------------------------------------------------------------------------- 4.7 economy

// Builds by kit, not by name (4.7): Jungle first on every body (30% less camp damage: no heal trips by ~r95), then Bruiser (8 stat
// points for 150 gold); the damage stat on the carries; health first on the divers; Power focus on Marcella (Mite's Marcella deals 181
// a round to our 61). The Capture emblem (prime capturer) and Prospector are added by the team plan (4.3), not here.
std::vector<I> Brain::v23_build_list() const
{
	auto& W = world();
	// The damage stat: the one a shard pays most for (build_from_kit's formula), except where the method names it.
	float sp = 0;
	if (kit.dmg >= 0)
		sp += kit.dmg_mod;
	if (kit.cc >= 0)
		sp += kit.cc_mod;
	if (kit.aoe >= 0)
		sp += kit.aoe_mod * (kit.aoe_radius >= 1.f ? 1.5f : 1.f);
	if (kit.dash >= 0)
		sp += kit.dash_mod * (kit.dash_radius >= 1.f ? 1.5f : 1.f);
	if (kit.heal >= 0)
		sp += kit.heal_mod;
	const float vf = focus_growth * sp / 8.f;
	const float vs = str_growth * (1.f + (kit.reset >= 0 ? 0.125f : 0.f)) * (type == CT::varg ? 1.5f : 1.f);
	int dmg = vf >= vs ? FOC : STR;
	if (type == CT_HOR || type == CT::marcella)
		dmg = FOC; // their dash / shield / spells scale with focus
	else if (type == CT::vendetta || type == CT::vesper_vale || type == CT::issac)
		dmg = STR;
	std::vector<I> v;
	auto tail = [&](int a, int b) {
		for (int k = 0; k < 16; ++k)
			add(v, shard(BRUISER, a), 5), add(v, shard(BRUISER, b), 5);
	};
	if (type == CT::marcella)
	{
		add(v, shard(JUNGLE, FOC), 5);
		add(v, shard(POWER, FOC), 10);
		add(v, shard(BRUISER, HP), 5);
		if (W.altars.size() == 1)
			add(v, shard(TRIBUTE, FOC), 5); // single-altar maps: she is the banker (+2 gold a gem, stun-immune)
		tail(FOC, HP);
	}
	else if (type == CT::ryth)
	{
		add(v, shard(JUNGLE, HP), 5); // strength = 1% of bonus health
		add(v, shard(BRUISER, HP), 10);
		add(v, shard(DURABILITY, HP), 5);
		tail(HP, HP);
	}
	else if (type == CT::issac)
	{
		add(v, shard(JUNGLE, STR), 5);
		add(v, shard(BRUISER, HP), 5);
		add(v, shard(BRUISER, STR), 5);
		tail(HP, STR);
	}
	else if (!kit.ranged)
	{
		// dash melee carries (Vendetta, Heart of Ruin; Ren and Varg alike): they dive, so health first (Mite: 11.5 Bruiser health a game)
		add(v, shard(JUNGLE, dmg), 5);
		add(v, shard(BRUISER, HP), 5);
		add(v, shard(BRUISER, dmg), 5);
		add(v, shard(BRUISER, HP), 5);
		add(v, shard(DURABILITY, HP), 5);
		tail(dmg, HP);
	}
	else
	{
		// ranged carries (Vesper Vale, Tavi, Stellar, Prism, Cassi, Willow)
		int map_gold = 0;
		for (const auto& g : W.groups)
			map_gold += g.gold;
		add(v, shard(JUNGLE, dmg), 5);
		add(v, shard(BRUISER, dmg), 10);
		if (type == CT::vesper_vale && map_gold >= 2500)
			add(v, shard(TREASURE, dmg), 5); // +10% gold on the +33% gold body, where the map pays gold
		add(v, shard(MONSTER, dmg), 5);
		tail(dmg, dmg);
	}
	return v;
}

// 4.7 Tavi: field shopping is the point of the pick; once the camps no longer hurt (r600+) its Jungle emblem is sold at full value
// on spawn and the gold goes into Bruiser shards in the damage stat.
void Brain::v23_tavi_sell()
{
	if (v23_sold)
		return;
	auto& me = bc::self();
	try
	{
		if (!me.can_sell())
			return;
		const auto items = me.item_count();
		for (int stat = 0; stat < 3; ++stat)
		{
			const I emb = I{ static_cast<std::uint32_t>(JUNGLE * 6 + stat * 2 + 1) };
			if (items[emb] > 0)
			{
				me.sell(emb, 1);
				v23_sold = true;
				build.insert(build.begin() + static_cast<std::ptrdiff_t>(std::min(build_idx, build.size())), 5, shard(BRUISER, STR));
				break;
			}
		}
		if (!v23_sold && items[shard(JUNGLE, STR)] + items[shard(JUNGLE, FOC)] + items[shard(JUNGLE, HP)] == 0)
			v23_sold = true; // nothing to sell
	}
	catch (...)
	{
		v23_sold = true;
	}
}

// ---------------------------------------------------------------------------------------------- 4.6 banking

void Brain::v23_perceive()
{
	auto& W = world();
	if (v23_altar_e4.size() != W.altars.size())
		v23_altar_e4.assign(W.altars.size(), -1000);
	for (const auto& e : W.enemies)
		if (e.alive && e.visible)
			for (std::size_t i = 0; i < W.altars.size(); ++i)
				if (cheb(e.pos, W.altars[i]) <= 4)
					v23_altar_e4[i] = round;
}

bool Brain::v23_altar_unsafe(int i) const
{
	auto& W = world();
	if (i < 0 || static_cast<std::size_t>(i) >= v23_altar_e4.size() || round - v23_altar_e4[static_cast<std::size_t>(i)] > 8)
		return false;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, W.altars[static_cast<std::size_t>(i)]) <= 5)
			return false; // a two-body bank
	return true;
}

// 4.6: bank small and near. Mite banks 28 times a game with 35-gem bags carried 30 rounds; v75 12 times, 27 gems, 43 rounds, and 21%
// of what it captures is lost on death.
bool Brain::v23_bank_want(int dist) const
{
	auto& W = world();
	const int g = static_cast<int>(gems);
	if (g <= 0)
		return false;
	if (dist <= 1)
		return true; // next to an altar: a bag of 10 or less costs no stuck turn, anything more is cheapest here
	{
		// 4.13 endgame: from r1700, or when either team has banked 850, every bag of 10+ is banked
		const int lead = static_cast<int>(std::max(bc::global_submitted_gems(team::ally), bc::global_submitted_gems(team::enemy)));
		if (g >= 10 && (round >= 1700 || lead >= 850))
			return true;
	}
	if (g >= P.v23_bank_small && dist <= P.v23_bank_near)
		return true;
	if (g >= P.v23_bank_any)
		return true;
	if (g >= P.v23_bank_threat && enemies_within(10) > 0 && v23_ratio(pos, 10) < P.v23_bank_r)
		return true; // an outmatched fight is coming: the bag goes first
	if (g >= P.v23_bank_camp && !kit.ranged && task_group >= 0 && static_cast<std::size_t>(task_group) < W.groups.size())
	{
		// camp kills destroy the bag: a melee body does not front an elk / golem group with a bag
		const auto& tg = W.groups[static_cast<std::size_t>(task_group)];
		if (tg.st == ST_ALIVE && tg.max_range >= 4 && !tg.harmless)
			return true;
	}
	return false;
}

// 4.6 locks: an enemy carrier with >= 30 gems heading for an altar we stand next to (within 2, the placement range) and still >= 4
// away: the lock cancels its tribute (5 hits to clear) and costs 10 gold. Mite never places locks and has no counter-play.
bool Brain::v23_lock_carrier()
{
	auto& W = world();
	if (!g15_has_lock() || W.altars.empty())
		return false;
	for (std::size_t i = 0; i < W.altars.size(); ++i)
	{
		const vec2 at = W.altars[i];
		if (cheb(at, pos) > 2 || W.altar_locked_by_enemy(static_cast<int>(i)))
			continue;
		for (const auto& e : W.enemies)
		{
			if (!e.alive || !e.visible || e.gems < 30 || cheb(e.pos, at) < 4 || cheb(e.pos, at) > 12)
				continue;
			// heading for this altar: it is the nearest altar to the carrier
			int best = BIG;
			std::size_t bi = i;
			for (std::size_t j = 0; j < W.altars.size(); ++j)
				if (cheb(e.pos, W.altars[j]) < best)
					best = cheb(e.pos, W.altars[j]), bi = j;
			if (bi == i && g15_place_lock(at))
				return true;
		}
	}
	return false;
}

// ---------------------------------------------------------------------------------------------- 4.5.1 local power ratio

namespace
{
float best_spell(const Kit& k, float focus, bool dmg_up, bool cc_up, bool aoe_up, bool dash_up)
{
	float b = 0;
	if (k.dmg >= 0 && dmg_up)
		b = std::max(b, focus * k.dmg_mod);
	if (k.cc >= 0 && cc_up)
		b = std::max(b, focus * k.cc_mod);
	if (k.aoe >= 0 && aoe_up)
		b = std::max(b, focus * k.aoe_mod);
	if (k.dash >= 0 && dash_up && k.dash_mod > 0.f)
		b = std::max(b, focus * k.dash_mod);
	return b;
}
} // namespace

float Brain::v23_dps_me() const
{
	auto rdy = [&](int s) { return s >= 0 && cd[static_cast<std::size_t>(s)] <= 0; };
	float basic = str * (rdy(kit.reset) ? 2.f : 1.f);
	if (type == CT_HOR)
		basic *= 1.f + 0.5f * (1.f - hp / std::max(1.f, max_hp)); // missing-health bonus
	return basic + best_spell(kit, focus, rdy(kit.dmg), rdy(kit.cc), rdy(kit.aoe), rdy(kit.dash)) / 3.f;
}

// R = sum over our bodies of hp x dps / the same over theirs, within `rad` of `at` (4.5.1). A body that cannot reach the contact
// within 2 rounds weighs half; enemies on their spawn count 0 (they heal every round); a stunned enemy deals nothing this round.
float Brain::v23_ratio(vec2 at, int rad, int* n_ours, int* n_theirs) const
{
	auto& W = world();
	float ours = hp * v23_dps_me(), theirs = 0;
	int no = 1, nt = 0;
	for (const auto& a : W.allies)
	{
		if (a.handle == self || !a.alive || !a.visible || a.seen_round != round || a.channeling)
			continue;
		const int d = cheb(a.pos, at);
		if (d > rad)
			continue;
		const float w = d > a.kit.attack_range + 2 + (a.kit.dash >= 0 ? 2 : 0) ? 0.5f : 1.f;
		const float basic = a.str * (a.type == CT_HOR ? 1.f + 0.5f * (1.f - a.hp / std::max(1.f, a.max_hp)) : 1.f);
		ours += w * a.hp * (basic + best_spell(a.kit, a.focus, true, true, true, true) / 3.f);
		++no;
	}
	for (const auto& e : W.enemies)
	{
		if (!e.alive || e.seen_round < 0 || round - e.seen_round > 2 || W.enemy_spawn.is_set(e.pos))
			continue;
		const int d = cheb(e.pos, at);
		if (d > rad)
			continue;
		if (e.visible && e.stunned)
		{
			++nt;
			continue;
		}
		const bool fresh = e.visible && e.seen_round == round;
		auto up = [&](int s) { return s >= 0 && (!fresh || e.cd[static_cast<std::size_t>(s)] <= 0); };
		const float w = d > e.kit.attack_range + 2 + (up(e.kit.dash) ? 2 : 0) ? 0.5f : 1.f;
		float basic = e.str * (up(e.kit.reset) ? 2.f : 1.f);
		if (e.type == CT_HOR)
			basic *= 1.f + 0.5f * (1.f - e.hp / std::max(1.f, e.max_hp));
		theirs += w * std::max(1.f, e.hp) * (basic + best_spell(e.kit, e.focus, up(e.kit.dmg), up(e.kit.cc), up(e.kit.aoe), up(e.kit.dash)) / 3.f);
		++nt;
	}
	if (n_ours)
		*n_ours = no;
	if (n_theirs)
		*n_theirs = nt;
	return theirs > 0.f ? ours / theirs : 99.f;
}

// ---------------------------------------------------------------------------------------------- 4.3 team objective layer

// The prime set (4.3): the richest groups we reach no more than v23_prime_margin rounds after they can. Mite / IC capture the richest
// group 6.6 / 4.7 times a game, v75 0.3; it holds 54% of Mite's gems and is in the middle on 57 of the 70 maps.
void Brain::v23_prime_setup()
{
	auto& W = world();
	v23_prime_ready = true;
	float vmax = 0;
	for (const auto& g : W.groups)
		if (!g.monolith)
			vmax = std::max(vmax, static_cast<float>(g.gems) + P.v23_prime_gold * static_cast<float>(g.gold));
	std::vector<std::pair<float, int>> c;
	for (const auto& g : W.groups)
	{
		if (g.monolith || g.d_ally >= BIG)
			continue;
		const float v = static_cast<float>(g.gems) + P.v23_prime_gold * static_cast<float>(g.gold);
		if ((v >= P.v23_prime_share * vmax || g.gems >= P.v23_prime_gems) && g.d_ally <= g.d_enemy + P.v23_prime_margin)
			c.push_back({ v, g.id });
	}
	std::sort(c.begin(), c.end(), [](const auto& a, const auto& b) { return a.first > b.first || (a.first == b.first && a.second < b.second); });
	const int cap = std::min(P.v23_prime_max, W.team_champs <= 3 ? 2 : 3);
	const bc::bitboard bush = bc::map::bushes();
	for (const auto& [v, id] : c)
	{
		if (static_cast<int>(v23_P.size()) >= cap)
			break;
		const Group& g = W.groups[static_cast<std::size_t>(id)];
		// rally tile: outside every camp's reach, our side of the map, most camps within 4, a bush first, then nearer our spawn
		vec2 rally = g.center;
		float best = -1e9f;
		const int R = g.radius + g.max_range + 3;
		for (int dy = -R; dy <= R; ++dy)
			for (int dx = -R; dx <= R; ++dx)
			{
				const vec2 t{ g.center.x + dx, g.center.y + dy };
				if (!bc::map::is_in_bounds(t) || W.walls.is_set(t) || g.mask.is_set(t) || W.dist_home(t) >= BIG)
					continue;
				bool out = true;
				int in4 = 0;
				for (const auto& cp : g.camps)
				{
					const int d = cheb(t, cp.pos);
					out &= d >= cp.range + 1;
					in4 += d <= 4;
				}
				if (!out)
					continue;
				const bool ours = W.dist_home(t) <= W.dist_away(t);
				const float s = 10.f * static_cast<float>(in4) + (bush.is_set(t) ? 5.f : 0.f) + (ours ? 20.f : 0.f) - 0.05f * static_cast<float>(W.dist_home(t));
				if (s > best)
					best = s, rally = t;
			}
		// ward tile: within 2 of a spawn tile of the group (its respawn timer is readable while one is in vision), a bush first, near the rally
		vec2 wt = rally;
		float wb = -1e9f;
		for (const auto& gt : g.tiles)
			for (int dy = -2; dy <= 2; ++dy)
				for (int dx = -2; dx <= 2; ++dx)
				{
					const vec2 t{ gt.x + dx, gt.y + dy };
					if (!bc::map::is_in_bounds(t) || W.walls.is_set(t) || g.mask.is_set(t))
						continue;
					const float s = (bush.is_set(t) ? 10.f : 0.f) - static_cast<float>(cheb(t, rally));
					if (s > wb)
						wb = s, wt = t;
				}
		const int F = g.gems > 200 ? 5 : g.gems > 80 ? 4 : g.gems >= 36 ? 3 : 2;
		v23_P.push_back(id), v23_F.push_back(F), v23_rally.push_back(rally), v23_wtile.push_back(wt);
	}
}

// Every body computes the same roster from the same inputs (4.3): the prime clock (shared, or what we see), the committed bodies'
// walks to the rally, the F (+2 when they hold it) nearest commit. Our role: PRIME for one prime group, or FARM.
void Brain::v23_team_plan()
{
	auto& W = world();
	v23_role = 0, v23_role_k = -1, v23_deadline = -1, v23_warden = false;
	if (!v23_prime_ready)
	{
		if (round < init_round + 2 || bc::fuel_remaining() < 60000)
			return;
		v23_prime_setup();
	}
	if (v23_P.empty())
		return;
	// the prime clock of P0: bit 7 of bytes 0-5 (5 bits rounds / 4 to respawn, 31 unknown; bit 5 = an enemy holds it)
	int clk = 0;
	for (int i = 0; i < 6; ++i)
		clk |= ((bc::shared_memory[static_cast<std::size_t>(i)] >> 7) & 1) << i;
	const Group& g0 = W.groups[static_cast<std::size_t>(v23_P[0])];
	int ready0 = BIG;
	bool holds = (clk >> 5) & 1;
	holds |= round - g0.enemy_round <= 10;
	if (g0.seen_round == round)
	{
		ready0 = g0.st == ST_RESPAWN ? std::max(0, g0.ready_round - round) : 0;
		const int v = std::min(30, (ready0 + 3) / 4) | ((round - g0.enemy_round <= 10) ? 32 : 0);
		if (v != v23_clock_w || round % 8 == 0)
		{
			for (int i = 0; i < 6; ++i)
			{
				const std::uint8_t old = bc::shared_memory[static_cast<std::size_t>(i)];
				bc::shared_memory[static_cast<std::size_t>(i)] = static_cast<std::uint8_t>((old & 0x7F) | (((v >> i) & 1) << 7));
			}
			v23_clock_w = v;
		}
	}
	else if ((clk & 31) != 31 && clk != 0)
		ready0 = (clk & 31) * 4;
	else if (g0.st == ST_RESPAWN && g0.ready_round > round)
		ready0 = g0.ready_round - round;
	else if (g0.st == ST_ALIVE || g0.st == ST_REWARD || clk == 0)
		ready0 = 0;
	auto& C = comms();
	int alive_n = 0;
	for (const auto& a : W.allies)
		alive_n += a.alive;
	std::array<bool, 8> taken{};
	for (std::size_t k = 0; k < v23_P.size(); ++k)
	{
		const Group& g = W.groups[static_cast<std::size_t>(v23_P[k])];
		const int ready = k == 0 ? ready0 : g.st == ST_RESPAWN ? std::max(0, g.ready_round - round) : (g.st == ST_ALIVE || g.st == ST_REWARD) ? 0 : BIG;
		if (ready >= BIG)
			continue;
		const bool hk = k == 0 ? holds : round - g.enemy_round <= 10;
		const int need = std::min(alive_n, v23_F[k] + (hk ? 2 : 0));
		struct Cand
		{
			int eta;
			float hp;
			int i;
			bool ranged;
		};
		std::array<Cand, 8> cs{};
		int n = 0;
		for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
		{
			const auto& a = W.allies[static_cast<std::size_t>(i)];
			if (!a.alive || taken[static_cast<std::size_t>(i)])
				continue;
			vec2 p{ -1, -1 };
			float h = a.hp;
			bool ranged = a.kit.ranged;
			if (i == W.my_index)
				p = pos, h = hp, ranged = kit.ranged;
			else if (a.channeling)
				continue;
			else if (a.visible && a.seen_round >= round - 2)
				p = a.pos;
			else if (i < 6 && C.claim[static_cast<std::size_t>(i)] >= 0 && C.claim[static_cast<std::size_t>(i)] < static_cast<int>(W.groups.size()))
				p = W.groups[static_cast<std::size_t>(C.claim[static_cast<std::size_t>(i)])].center;
			if (p.x < 0)
				continue;
			const int eta = std::max(0, nav().group_dist(g, p) - (g.max_range + 1));
			if (ready == 0 ? eta > P.v23_prime_reach : eta > ready + 2)
				continue;
			cs[static_cast<std::size_t>(n++)] = { eta, h, i, ranged };
		}
		std::sort(cs.begin(), cs.begin() + n, [](const Cand& a, const Cand& b) { return a.eta != b.eta ? a.eta < b.eta : a.hp != b.hp ? a.hp > b.hp : a.i < b.i; });
		const int m = std::min(n, need);
		bool me = false;
		int last = 0, warden = -1;
		for (int j = 0; j < m; ++j)
		{
			taken[static_cast<std::size_t>(cs[static_cast<std::size_t>(j)].i)] = true;
			me |= cs[static_cast<std::size_t>(j)].i == W.my_index;
			if (cs[static_cast<std::size_t>(j)].i != W.my_index)
				last = std::max(last, cs[static_cast<std::size_t>(j)].eta);
			if (cs[static_cast<std::size_t>(j)].ranged && (warden < 0 || cs[static_cast<std::size_t>(j)].i < warden))
				warden = cs[static_cast<std::size_t>(j)].i;
		}
		if (me)
		{
			v23_role = 1, v23_role_k = static_cast<int>(k), v23_ready = ready, v23_holds = hk, v23_last_eta = last;
			v23_warden = warden == W.my_index;
			return;
		}
	}
}

// A farm target we finish (walk + clear) and still reach the rally before the respawn (the PRIME deadline).
bool Brain::v23_fits(const Group& g, int eta) const
{
	if (v23_deadline <= round || v23_role_k < 0)
		return true;
	const float kill = g.st == ST_ALIVE ? g.hp_total / std::max(10.f, dps_on(g)) : 6.f;
	const vec2 rally = v23_rally[static_cast<std::size_t>(v23_role_k)];
	return static_cast<float>(eta) + kill + static_cast<float>(cheb(g.center, rally)) <= static_cast<float>(v23_deadline - round);
}

// The PRIME executor (4.3): be at the rally when the group spawns, hit it the round it does; a contested group with the odds against
// us is left for the next cycle (the roster grows by 2 when they hold it); while it respawns, farm only what we finish in time.
bool Brain::v23_prime()
{
	if (v23_role != 1 || v23_role_k < 0)
		return false;
	auto& W = world();
	const std::size_t k = static_cast<std::size_t>(v23_role_k);
	Group& g = W.groups[static_cast<std::size_t>(v23_P[k])];
	const vec2 rally = v23_rally[k];
#ifdef FE_TRACE
	debug_block({
		std::printf("TOL r=%d %d k=%d g=%d st=%d ready=%d holds=%d last=%d eta=%d pos=(%d,%d) rally=(%d,%d) warden=%d\n", round, static_cast<int>(type), v23_role_k, g.id,
			static_cast<int>(g.st), v23_ready, static_cast<int>(v23_holds), v23_last_eta, std::max(0, nav().group_dist(g, pos) - (g.max_range + 1)), pos.x, pos.y, rally.x,
			rally.y, static_cast<int>(v23_warden));
	});
#endif
	if (v23_holds && v23_ratio(g.center, 8) < 1.f && enemies_within(10) > 0)
		return false; // 4.3.1: not with the odds against us; farm, and the next cycle brings everyone
	if (g.st == ST_REWARD)
		return false; // the capture rules decide the capturer (mi_capture / no_split); the others move on
	const int eta = std::max(0, nav().group_dist(g, pos) - (g.max_range + 1));
	if (g.st == ST_ALIVE)
	{
		// The clock's moment: the group spawned in the last rounds and we stand at its rally: take it now, together. Otherwise an alive
		// prime group is the farming scorer's to choose (it knows heal trips and whether the bodies present can clear it).
		const bool fresh = g.ready_round > 0 && round - g.ready_round <= P.v23_prime_fresh;
		if (!fresh || cheb(pos, rally) > 3)
			return false;
		const float solo = g.hp_total / std::max(10.f, dps_on(g));
		if (!g.awake && !g.harmless && solo > 12.f && v23_last_eta > eta + 2 && cheb(pos, rally) <= 1)
		{
			task = T_WAIT, task_group = g.id; // 4.4.1 synchronised arrival: the last roster body is close
			fe_state = fe_state == FE_AVOID ? FE_PRIME : fe_state;
			return true;
		}
		task = T_FARM, task_group = g.id;
		comms().write_self(W.my_index, g.id);
		return farm_group(g);
	}
	// respawning: farm what we finish in time, then wait at the rally
	if (eta + 2 < v23_ready - 1)
	{
		v23_deadline = round + v23_ready - 1;
		return false;
	}
	task = T_WAIT, task_group = g.id;
	fe_state = fe_state == FE_AVOID ? FE_PRIME : fe_state;
	comms().write_self(W.my_index, g.id);
	if (v23_warden && cheb(pos, v23_wtile[k]) <= 2 && !(ward_pos == v23_wtile[k]))
	{
		try
		{
			if (bc::self().place_ward(v23_wtile[k]))
				ward_pos = v23_wtile[k], ward_round = round;
		}
		catch (...)
		{
		}
	}
	if (pos == rally)
		return true;
	bc::bitboard goal;
	goal.set(rally);
	if (W.ally_occ.is_set(rally))
		goal.draw_chebyshev(rally, 1.f), goal &= ~W.walls & ~g.near;
	if (v23_warden && !(ward_pos == v23_wtile[k]))
		goal.set(v23_wtile[k]);
	step(goal, true, true);
	return true;
}

// ---------------------------------------------------------------------------------------------- 4.9 messages

// Allies' state and target as their priority says (readable for the allies we see; one host call each).
void Brain::v23_read_allies()
{
	auto& W = world();
	for (std::size_t i = 0; i < W.allies.size() && i < 8; ++i)
	{
		auto& a = W.allies[i];
		if (a.handle == self || !a.alive || !a.visible)
			continue;
		try
		{
			const std::int32_t p = a.ch.priority();
			const int pl = ((p % 4096) + 4096) % 4096;
			ally_hpb[i] = (pl >> 8) & 15;
			ally_fe[i] = (pl >> 6) & 3;
			ally_tgt[i] = ((pl >> 2) & 15) - 1;
			ally_fe_round[i] = round;
		}
		catch (...)
		{
		}
	}
}

// hp in 16ths x 256 + state x 64 + (target index + 1) x 4 + flags (1 committed, 2 carrying >= 20)
int Brain::v23_payload() const
{
	auto& W = world();
	const int hpb = std::clamp(static_cast<int>(16.f * hp / std::max(1.f, max_hp)), 0, 15);
	const bool fight = fe_state == FE_FIGHT || fe_state == FE_KILL;
	const int st = fight ? 2 : fe_state == FE_LEAVE ? 3 : fe_state == FE_PRIME ? 1 : 0;
	int tg = 0;
	if (fight && fe_target)
		for (std::size_t k = 0; k < W.enemies.size() && k < 14; ++k)
			if (W.enemies[k].handle == fe_target)
				tg = static_cast<int>(k) + 1;
	return hpb * 256 + st * 64 + tg * 4 + (fight ? 1 : 0) + (gems >= 20 ? 2 : 0);
}

// ---------------------------------------------------------------------------------------------- 4.5 fight engine

namespace
{
// Where an enemy can hit next turn: attack range (+1 step for melee), +2 with its dash up, its spells' reach when up.
int reach_next(const Enemy& e)
{
	int r = e.kit.attack_range + (e.kit.ranged ? 0 : 1) + (e.ready(e.kit.dash) ? 2 : 0);
	if (e.ready(e.kit.dmg) || e.ready(e.kit.cc))
		r = std::max(r, 4 + 1);
	if (e.ready(e.kit.aoe))
		r = std::max(r, static_cast<int>(e.kit.aoe_range + e.kit.aoe_radius) + (e.kit.aoe_excl ? 0 : 1));
	return r;
}
bool stun_up(const Enemy& e) { return e.ready(e.kit.cc) || (e.ready(e.kit.aoe) && e.kit.aoe_stuns); }
} // namespace

// 4.5.4 team target: the enemy in reach that dies soonest to the damage we and the allies near it deal, first the stunned, the
// channelling, Cassi / Issac (one kill is two bodies) and carriers of 20+ gems, and the target an ally we see is hitting.
Enemy* Brain::v23_target(const std::vector<Enemy*>& E, int my_reach)
{
	auto& W = world();
	Enemy* best = nullptr;
	float bk = 1e30f;
	const float mine = v23_dps_me();
	for (auto* e : E)
	{
		if (W.enemy_spawn.is_set(e->pos))
			continue;
		const int d = cheb(e->pos, pos);
		if (d > my_reach + 2)
			continue;
		float dmg = d <= my_reach ? mine : 0.5f * mine;
		const int ei = static_cast<int>(e - W.enemies.data());
		bool focused = false;
		for (std::size_t i = 0; i < W.allies.size() && i < 8; ++i)
		{
			const auto& a = W.allies[i];
			if (a.handle == self || !a.alive || !a.visible || a.channeling)
				continue;
			if (cheb(a.pos, e->pos) <= a.kit.attack_range + 1)
				dmg += a.str;
			focused |= P.v23_msg && ally_fe_round[i] == round && ally_tgt[i] == ei;
		}
		float key = (e->hp + e->shield) / std::max(1.f, dmg);
		if (e->stunned || e->channeling || e->type == CT::cassi || e->type == CT::issac || e->gems >= 20)
			key -= 200.f;
		if (focused)
			key -= 100.f;
		if (key < bk)
			bk = key, best = e;
	}
	return best;
}

// LEAVE (4.5.3): stun the fastest chaser first, a melee body swings at an adjacent enemy before the step, then walk to the nearest
// ally that can help (else home), never through an awake camp's range.
bool Brain::v23_leave(const std::vector<Enemy*>& E)
{
	auto& W = world();
	task = T_FLEE;
	if (kit.cc >= 0 && ready(kit.cc))
	{
		Enemy* ch = nullptr;
		int best = BIG;
		for (auto* e : E)
		{
			const int d = cheb(e->pos, pos);
			if (!e->ch || e->stunned || e->type == CT::marcella || d > static_cast<int>(kit.cc_range))
				continue;
			const int k = d - (e->ready(e->kit.dash) ? 3 : 0); // the dash kit catches up first
			if (k < best)
				best = k, ch = e;
		}
		if (ch)
			cast_unit_champ(kit.cc, *ch->ch);
	}
	if (!kit.ranged && can_attack)
		for (auto* e : E)
			if (e->ch && cheb(e->pos, pos) <= kit.attack_range && !W.enemy_spawn.is_set(e->pos))
			{
				attack_unit(*e->ch);
				break;
			}
	if (!can_move)
		return true;
	// the nearest ally that is not running (in a fight, or healthy) and no nearer the enemies than we are
	const Ally* to = nullptr;
	int bd = BIG, my_ed = BIG;
	for (auto* e : E)
		my_ed = std::min(my_ed, cheb(e->pos, pos));
	for (std::size_t i = 0; i < W.allies.size() && i < 8; ++i)
	{
		const auto& a = W.allies[i];
		if (a.handle == self || !a.alive || !a.visible || a.channeling || cheb(a.pos, pos) > 12)
			continue;
		const bool helps = (P.v23_msg && ally_fe_round[i] == round && ally_fe[i] == 2) || a.hp >= 0.6f * a.max_hp;
		if (!helps)
			continue;
		int ed = BIG;
		for (auto* e : E)
			ed = std::min(ed, cheb(e->pos, a.pos));
		if (ed + 1 < my_ed)
			continue; // walking to it walks into them
		const int d = cheb(a.pos, pos);
		if (d < bd)
			bd = d, to = &a;
	}
	if (to && bd > 1)
	{
		bc::bitboard goal;
		goal.draw_chebyshev(to->pos, 1.f);
		goal &= ~W.walls;
		if (step(goal, true, true))
			return true;
	}
	go_home_step(true);
	return true;
}

bool Brain::v23_fight()
{
	auto& W = world();
	engaged = false;
	if (P.v23_msg)
		v23_read_allies();
	std::vector<Enemy*> E;
	for (auto& e : W.enemies)
		if (e.alive && e.visible && e.ch && cheb(e.pos, pos) <= 10)
		{
			if (W.enemy_spawn.is_set(e.pos) && e.max_hp > burst_vs(e) + 1.f)
				continue; // it heals every round on its spawn
			E.push_back(&e);
		}
	if (E.empty())
	{
		fe_state = FE_AVOID, fe_until = -100, fe_target = 0, fe_chase = 0;
		return false;
	}
	const bool on_spawn = W.ally_spawn.is_set(pos);
	// next-turn threat on us
	float incoming = 0;
	bool threat = false;
	Enemy* nearest = nullptr;
	int nd = BIG;
	for (auto* e : E)
	{
		const int d = cheb(e->pos, pos);
		if (d < nd)
			nd = d, nearest = e;
		if (d <= reach_next(*e) && !e->stunned)
			threat = true, incoming += e->str + e->burst() / 2.f;
	}
	const int my_reach = std::max(kit.attack_range + (kit.ranged ? 0 : 1) + (ready(kit.dash) ? 2 : 0), (ready(kit.dmg) || ready(kit.cc) || ready(kit.aoe)) ? 4 : 0);
	// KILL: a visible enemy (not on its spawn) dies this turn to our hits
	Enemy* kill = nullptr;
	for (auto* e : E)
		if (!W.enemy_spawn.is_set(e->pos) && cheb(e->pos, pos) <= my_reach && burst_vs(*e) >= e->hp + e->shield && (!kill || e->hp < kill->hp))
			kill = e;
	// 4.5.2 escape test: running from a chaser that still reaches us after our move hands it free hits every round. Melee moves and
	// attacks in one turn, so a same-speed melee next to us is such a chaser too, as is a ranged body whose range covers our step, a
	// dash kit with its dash up, and any ready stun within 4 (a stun costs us the turn).
	bool escape = true;
	const int my_move = 1 + (ready(kit.dash) ? static_cast<int>(kit.dash_range) : 0);
	for (auto* e : E)
	{
		const int d = cheb(e->pos, pos);
		if (e->stunned)
			continue;
		const int chase = e->kit.attack_range + (e->kit.ranged ? 0 : 1) + (e->ready(e->kit.dash) ? static_cast<int>(e->kit.dash_range) : 0);
		const bool caught = d + my_move <= chase || (stun_up(*e) && d <= 4);
		if (caught)
		{
			escape = false;
			break;
		}
	}
	if (!escape && incoming > 0.f)
	{
		// a safe place sooner than we die: our spawn, or a tile next to 2+ allies
		const float t_die = hp / incoming;
		int safe = W.dist_home(pos);
		for (const auto& a : W.allies)
		{
			if (a.handle == self || !a.alive || !a.visible || a.channeling)
				continue;
			int n2 = 0;
			for (const auto& b : W.allies)
				n2 += b.handle != self && b.alive && b.visible && !b.channeling && cheb(b.pos, a.pos) <= 2;
			if (n2 >= 2)
				safe = std::min(safe, std::max(0, cheb(a.pos, pos) - 1));
		}
		if (static_cast<float>(safe) < t_die)
			escape = true;
	}
	// 4.5.1 the ratio at the contact, reinforcements within 10, allies already fighting within 8
	const vec2 contact = kill ? kill->pos : nearest->pos;
	int no = 0, nt = 0;
	const float R = v23_ratio(contact, 8, &no, &nt);
	int their10 = 0, our10 = 1;
	for (const auto& e : W.enemies)
		their10 += e.alive && e.seen_round >= 0 && round - e.seen_round <= 2 && !W.enemy_spawn.is_set(e.pos) && cheb(e.pos, contact) <= 10;
	bool ally_fight = false;
	for (std::size_t i = 0; i < W.allies.size() && i < 8; ++i)
	{
		const auto& a = W.allies[i];
		if (a.handle == self || !a.alive || !a.visible || a.channeling)
			continue;
		our10 += cheb(a.pos, contact) <= 10;
		if (cheb(a.pos, pos) <= 8)
			ally_fight |= P.v23_msg ? (ally_fe_round[i] == round && ally_fe[i] == 2) : (a.hit_round >= round - 1 && cheb(a.pos, contact) <= 6);
	}
	const bool pair = type == CT::cassi || type == CT::issac;
	const float gate = pair ? P.v23_gate_pair : P.v23_gate;
	bool pair_low = pair && hp < P.v23_pair_low * max_hp;
	if (pair)
		for (const auto& a : W.allies)
			if (a.handle != self && a.alive && a.visible && (a.type == CT::cassi || a.type == CT::issac) && a.hp < P.v23_pair_low * a.max_hp)
				pair_low = true;
	// 4.5.3 the state this turn
	int want = FE_AVOID;
	bool gate_fight = false;
	if (kill)
		want = FE_KILL;
	else if (!escape)
		want = FE_FIGHT;
	else if (on_spawn && threat)
		want = FE_FIGHT;
	else if (R >= gate && their10 <= our10 && !pair_low)
		want = FE_FIGHT, gate_fight = true;
	else if (ally_fight && R >= P.v23_join && !pair_low)
		want = FE_FIGHT;
	else
		want = threat ? FE_LEAVE : FE_AVOID;
	// hysteresis: FIGHT holds unless the target is gone, we are low and can get away, or a new enemy turned it
	if (fe_state == FE_FIGHT && round <= fe_until && want != FE_KILL && want != FE_FIGHT)
	{
		bool target_ok = false;
		for (auto* e : E)
			target_ok |= e->handle == fe_target;
		const bool release = !target_ok || (hp < P.v23_low * max_hp && escape) || (R < P.v23_release && nt > fe_enemies0) || pair_low ||
			(escape && (R < P.v23_fe_drop || hp < P.v23_fe_low * max_hp)); // a lost fight we can walk away from
		if (!release)
			want = FE_FIGHT;
	}
	// AVOID / LEAVE hold: no gate fight re-entry within the hold (the A-B-A walk)
	if ((fe_state == FE_LEAVE || fe_state == FE_AVOID) && round <= fe_until && want == FE_FIGHT && gate_fight)
		want = fe_state;
	if (want != fe_state && !(want == FE_KILL && fe_state == FE_FIGHT))
	{
		fe_until = round + (want == FE_FIGHT ? P.v23_fight_hold : P.v23_leave_hold);
		if (want == FE_FIGHT)
			fe_enemies0 = nt, fe_chase = 0, fe_chase_d = 99;
	}
	fe_state = want;
#ifdef FE_TRACE
	debug_block({
		std::printf("FE r=%d %d want=%d esc=%d thr=%d kill=%d R=%.2f no=%d nt=%d our10=%d their10=%d afight=%d hp=%.0f/%.0f nd=%d\n", round, static_cast<int>(type), want,
			static_cast<int>(escape), static_cast<int>(threat), kill ? 1 : 0, R, no, nt, our10, their10, static_cast<int>(ally_fight), hp, max_hp, nd);
	});
#endif
	if (want == FE_AVOID)
		return false;
	if (want == FE_LEAVE)
		return v23_leave(E);
	// KILL / FIGHT
	Enemy* t = want == FE_KILL ? kill : v23_target(E, my_reach);
	if (!t)
	{
		if (on_spawn)
		{
			task = T_FIGHT; // hold the spawn tile: anything that follows us here fights a body that heals every round
			return true;
		}
		fe_state = FE_AVOID;
		return false;
	}
	// 4.5.4 step 5: a bag next to an altar is banked now (damage does not cancel a tribute; a stun does)
	if (want != FE_KILL && static_cast<int>(gems) >= P.v23_fight_bank)
		for (const auto& at : W.altars)
			if (cheb(at, pos) <= 1)
			{
				try
				{
					bc::self().submit_gems(at);
					task = T_TRIBUTE;
					tribute_start = round, tribute_ticks = static_cast<int>((gems + 9) / 10);
					return true;
				}
				catch (...)
				{
				}
				break;
			}
	const int d = cheb(t->pos, pos);
	if (want != FE_KILL)
	{
		// 4.5.5: a target that is not a kill is never chased: not out of our reach as it walks away, not onto their half
		if (t->handle == fe_target && d > my_reach && d > fe_chase_d)
			++fe_chase;
		else if (d <= my_reach)
			fe_chase = 0;
		fe_chase_d = d;
		const bool deep = d > my_reach && W.dist_away(t->pos) + 4 < W.dist_home(t->pos);
		if (fe_chase >= P.v23_no_chase || deep || (on_spawn && d > my_reach))
		{
			fe_state = threat && !on_spawn ? FE_LEAVE : FE_AVOID;
			fe_until = round + P.v23_leave_hold;
			if (fe_state == FE_LEAVE)
				return v23_leave(E);
			if (on_spawn)
			{
				task = T_FIGHT;
				return true;
			}
			return false;
		}
	}
	fe_target = t->handle;
	task = T_FIGHT;
	engaged = true;
	last_fight_round = round;
	if (P.v23_msg && R < 1.f)
		comms().post(AL_RALLY, pos, round);
	fe_no_cc = t->stunned; // 4.5.4 step 2: a stun only on a target that is not already stunned
	engage(*t);
	fe_no_cc = false;
	return true;
}
