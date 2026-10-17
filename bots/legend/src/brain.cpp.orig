#include "brain.h"
#include "learn.h"

#include <cmath>
#include <cstdio>

namespace
{
using I = bc::item_type;
using CT = bc::champion_type;

void rep(std::vector<I>& v, I it, int n)
{
	for (int i = 0; i < n; ++i)
		v.push_back(it);
}

// Repeat a cycle of five-shard blocks n times (late-game raw stats; the list must never run out: a rich Ren
// earned 3,058 gold in one r2 game and stopped buying at 2,100 with 948 gold left).
void cycle(std::vector<I>& v, std::initializer_list<I> blocks, int n)
{
	for (int k = 0; k < n; ++k)
		for (const I it : blocks)
			rep(v, it, 5);
}

// Shard plans: five shards of a family complete its emblem; only the emblem grants the passive.
std::vector<I> build_for(CT t)
{
	std::vector<I> v;
	if (P.build_style == 2)
	{
		// Value-model builds (tools/analysis/item_value.py, calibrated on 36 r2 games). Every shard adds one point
		// of its stat whatever the family, so the family only decides the emblem bonus:
		//  - Bruiser (5 points + 1 of each other stat) beats Power (6 of one): the sixth point of a stat is worth
		//    less than a first point of two others (log utility), at the same 150 gold.
		//  - Passives are unique per family (they do not stack), so each is bought once.
		//  - Ren and Stellar earn 1.3-1.6 gold per round (30% of team gold each): Treasure (+20% gold) pays for
		//    itself ~2x over a 700-round game. The model puts it first; measured vs _v6, keeping r2's first emblem
		//    and Treasure second won 21/24 (gems +9,385) against 19/24 (+8,623) for Treasure first.
		//  - Cassi and Issac earn 0.6 gold per round (first emblem near round 400) and die together 6 times a
		//    game: health with Durability / Jungle first (ci_health_first). It halves Cassi's own farming, but
		//    the pair survives fights: vs _v6 it measured 19/24 wins against 16/24 with Monster first.
		switch (t)
		{
		case CT::ren:
			if (P.rich_treasure_first)
				rep(v, I::treasure_shard_of_focus, 5);
			else
			{
				// The first emblem lands near round 240 and sets the early pace: Ren tanks the packs, and the
				// kill-time planner (incoming_on) accepts more of them with Jungle health.
				rep(v, I::jungle_shard_of_health, 5);
				rep(v, I::treasure_shard_of_focus, 5);
			}
			rep(v, I::monster_shard_of_focus, 5);
			rep(v, I::bruiser_shard_of_focus, 5);
			if (P.rich_treasure_first)
				rep(v, I::jungle_shard_of_health, 5);
			rep(v, I::bruiser_shard_of_focus, 5);
			rep(v, I::durability_shard_of_health, 5);
			cycle(v, { I::bruiser_shard_of_focus, I::bruiser_shard_of_focus, I::bruiser_shard_of_health }, 8);
			break;
		case CT::stellar:
		case CT::prism:
		case CT::tavi:
			if (P.rich_treasure_first)
			{
				rep(v, I::treasure_shard_of_focus, 5);
				rep(v, I::monster_shard_of_focus, 5);
			}
			else
			{
				rep(v, I::monster_shard_of_focus, 5);
				rep(v, I::treasure_shard_of_focus, 5);
			}
			rep(v, I::bruiser_shard_of_focus, 5);
			rep(v, I::durability_shard_of_health, 5);
			cycle(v, { I::bruiser_shard_of_focus, I::bruiser_shard_of_focus, I::bruiser_shard_of_health }, 8);
			break;
		case CT::cassi:
		case CT::willow:
			if (P.ci_health_first)
			{
				rep(v, I::durability_shard_of_health, 5);
				rep(v, I::jungle_shard_of_health, 5);
				rep(v, I::bruiser_shard_of_health, 5);
				rep(v, I::monster_shard_of_focus, 5);
			}
			else
			{
				// The r2 order without Treasure: damage first, survival second (measured weaker, kept for A/B).
				rep(v, I::monster_shard_of_focus, 5);
				rep(v, I::durability_shard_of_health, 5);
			}
			cycle(v, { I::bruiser_shard_of_focus, I::bruiser_shard_of_health }, 12);
			break;
		case CT::issac:
			if (P.ci_health_first)
			{
				rep(v, I::durability_shard_of_health, 5);
				rep(v, I::jungle_shard_of_health, 5);
				rep(v, I::bruiser_shard_of_strength, 5);
				rep(v, I::monster_shard_of_strength, 5);
			}
			else
			{
				rep(v, I::monster_shard_of_strength, 5);
				rep(v, I::durability_shard_of_health, 5);
				rep(v, I::jungle_shard_of_health, 5);
			}
			cycle(v, { I::bruiser_shard_of_strength, I::bruiser_shard_of_health }, 12);
			break;
		case CT::ryth:
		case CT::marcella:
			// Model margin over the r2 order is ~0 here: keep it, Bruiser for the raw stats.
			rep(v, I::jungle_shard_of_health, 5);
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			cycle(v, { I::bruiser_shard_of_strength, I::bruiser_shard_of_health }, 12);
			break;
		case CT::varg:
		case CT::vendetta:
		case CT::vesper_vale:
			// Splash makes strength Varg's best stat (2.2x on packs): Jungle on strength, not health.
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::treasure_shard_of_strength, 5);
			rep(v, I::jungle_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			cycle(v, { I::bruiser_shard_of_strength, I::bruiser_shard_of_strength, I::bruiser_shard_of_health }, 8);
			break;
		}
		return v;
	}
	if (P.build_style == 1)
	{
		// Ladder-proven: survive first (Jungle health, Durability), farm faster (Monster), earn more (Treasure),
		// then raw stats through Power emblems (6 shards for the price of 5).
		switch (t)
		{
		case CT::varg:
		case CT::vendetta:
		case CT::issac:
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::jungle_shard_of_health, 5);
			rep(v, I::treasure_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::power_shard_of_strength, 50);
			break;
		case CT::ren:
			// Retaliation scales with focus (0.2 x focus per hit taken): a health and focus tank.
			rep(v, I::jungle_shard_of_health, 5);
			rep(v, I::power_shard_of_focus, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::treasure_shard_of_focus, 5);
			rep(v, I::power_shard_of_focus, 50);
			break;
		case CT::ryth:
		case CT::marcella:
			rep(v, I::jungle_shard_of_health, 5);
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			for (int i = 0; i < 10; ++i)
			{
				rep(v, I::power_shard_of_strength, 3);
				rep(v, I::power_shard_of_health, 2);
			}
			break;
		case CT::tavi:
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::treasure_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::power_shard_of_strength, 50);
			break;
		case CT::vesper_vale:
			rep(v, I::treasure_shard_of_strength, 5);
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::power_shard_of_strength, 50);
			break;
		case CT::stellar:
		case CT::cassi:
		case CT::prism:
			rep(v, I::monster_shard_of_focus, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::treasure_shard_of_focus, 5);
			rep(v, I::power_shard_of_focus, 50);
			break;
		case CT::willow:
			rep(v, I::power_shard_of_focus, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::power_shard_of_focus, 50);
			break;
		}
		return v;
	}
	switch (t)
	{
	case CT::vendetta:
	case CT::varg:
	case CT::ren:
	case CT::issac:
		rep(v, I::jungle_shard_of_strength, 5);
		rep(v, I::monster_shard_of_strength, 5);
		rep(v, I::power_shard_of_strength, 60);
		break;
	case CT::ryth:
	case CT::marcella:
		rep(v, I::jungle_shard_of_health, 5);
		rep(v, I::monster_shard_of_strength, 5);
		for (int i = 0; i < 12; ++i)
		{
			rep(v, I::power_shard_of_strength, 3);
			rep(v, I::power_shard_of_health, 2);
		}
		break;
	case CT::tavi:
		rep(v, I::monster_shard_of_strength, 5);
		rep(v, I::power_shard_of_strength, 60);
		break;
	case CT::vesper_vale:
		rep(v, I::treasure_shard_of_strength, 5);
		rep(v, I::monster_shard_of_strength, 5);
		rep(v, I::power_shard_of_strength, 60);
		break;
	case CT::stellar:
	case CT::cassi:
		rep(v, I::monster_shard_of_focus, 5);
		rep(v, I::power_shard_of_focus, 60);
		break;
	case CT::prism:
		rep(v, I::monster_shard_of_strength, 5);
		rep(v, I::power_shard_of_focus, 60);
		break;
	case CT::willow:
		rep(v, I::power_shard_of_focus, 5);
		rep(v, I::durability_shard_of_health, 5);
		rep(v, I::power_shard_of_focus, 60);
		break;
	}
	return v;
}

float best_mod(const Kit& k)
{
	return std::max({ k.dmg >= 0 ? k.dmg_mod : 0.f, k.cc >= 0 ? k.cc_mod : 0.f, k.aoe >= 0 ? k.aoe_mod : 0.f });
}

vec2 sgn_step(vec2 from, vec2 to)
{
	return { (to.x > from.x) - (to.x < from.x), (to.y > from.y) - (to.y < from.y) };
}
} // namespace

Brain& brain()
{
	static Brain b;
	return b;
}

// ---------------------------------------------------------------------------------------------- lifecycle

void Brain::init()
{
	init_round = static_cast<int>(bc::round_number());
	auto& me = bc::self();
	self = handle_of(me);
	type = me.champion_name();
	kit = kit_of(me);
	const auto abl = me.abilities();
	ab.assign(abl.begin(), abl.end());
	build = build_for(type);
	auto& W = world();
	W.init_static();
	W.find_islands();
	W.init_units();
	blacklist.assign(W.groups.size(), -1);
	nav().init();
	learner().init(W.W, W.H);
	comms().bodies = static_cast<int>(W.allies.size());
	inited = true;
}

void Brain::read_self()
{
	bc::detail::champion_info i{};
	bc::detail::check(bc::detail::sdk_champion(self, &i));
	alive = flag(i.state, bc::champion_state::alive);
	pos = { i.x, i.y };
	hp = i.health;
	max_hp = std::max(1.f, i.max_health);
	str = i.strength;
	focus = i.focus;
	state = i.state;
	can_move = flag(i.state, bc::champion_state::can_move);
	can_attack = flag(i.state, bc::champion_state::can_attack);
	can_cast = flag(i.state, bc::champion_state::can_cast);
	cast_done = false;
	for (std::uint32_t s = 0; s < 2; ++s)
	{
		std::int32_t c = 0;
		if (bc::detail::sdk_champion_cooldown(self, s, &c) != 0)
			c = 99;
		cd[s] = c;
	}
	const std::uint32_t before = gems;
	bc::detail::sdk_champion_gems(self, &gems);
	bc::detail::sdk_champion_gold(self, &gold);
	if (alive && before > 0 && gems == 0 && flag(i.state, bc::champion_state::alive))
		last_bank_round = round;
}

void Brain::turn()
{
	round = static_cast<int>(bc::round_number());
	auto& W = world();
	W.round = round;
	if (!inited)
		init();
	read_self();
	auto& C = comms();
	if (!alive)
	{
		was_alive = false;
		W.update_alive(round);
		shop();
		C.read(round);
		C.write_self(W.my_index, -1);
		learner().tick(round, W.my_index == 0, false);
		if (W.my_index == 0)
			C.write_stance(learner().stance);
		task = T_NONE;
		return;
	}
	W.perceive(pos);
	C.read(round);
	{
		// Learning signals: champion damage marks a painful place; an enemy dying near us relieves it.
		auto& L = learner();
		L.tick(round, W.my_index == 0, true);
		if (W.my_index == 0)
			C.write_stance(L.stance);
		if (hp < last_hp - 0.5f)
		{
			last_hit_round = round;
			if (enemies_within(5) > 0)
				L.add_pain(pos, P.pain_hit * (last_hp - hp) / max_hp);
		}
		for (const auto& e : W.enemies)
			if (e.died_round == round && round - e.seen_round <= 2 && cheb(e.pos, pos) <= 8)
				L.on_enemy_killed_near(e.pos, round);
		// A visible enemy tributing a bag (or recalling with one) is an opportunity for the whole team.
		for (const auto& e : W.enemies)
			if (e.visible && e.alive && (e.tributing || (e.recalling && e.gems >= 20)) && e.gems >= 10 && !W.enemy_spawn.is_set(e.pos))
			{
				C.post(AL_OPPORTUNITY, e.pos, round);
				break;
			}
	}
	build_danger();

	if (flag(state, bc::champion_state::recalling) || flag(state, bc::champion_state::submitting_gems) ||
		flag(state, bc::champion_state::teleporting))
	{
		handle_channel();
		read_self();
		if (flag(state, bc::champion_state::recalling) || flag(state, bc::champion_state::submitting_gems) ||
			flag(state, bc::champion_state::teleporting))
		{
			last_hp = hp;
			return;
		}
	}

	shop();
	nav().new_turn();
	update_mode();

	support_spells();
	use_locks();

	if (!was_alive)
		respawn_round = round;
	was_alive = true;
	if (escort_wait())
	{
		place_ward(false);
		update_priority();
		prebuild_fields();
		C.write_self(W.my_index, -1);
		last_hp = hp;
		return;
	}

	bool acted = combat();
	if (!acted)
		acted = safety();
	if (!acted)
		acted = tribute(false);
	if (!acted)
		acted = home_trip();
	if (!acted)
		acted = shop_trip();
	if (!acted)
		acted = respond_to_alert();
	if (!acted)
		farm();

	place_ward(false);
	update_priority();
	prebuild_fields();
#ifdef LEGEND_TRACE
	debug_block({
		std::printf("T r=%d %d task=%d g=%d pos=(%d,%d) hp=%.0f gems=%u gold=%u fuel=%llu\n", round, static_cast<int>(type), task, task_group, pos.x, pos.y, hp, gems, gold,
			static_cast<unsigned long long>(bc::fuel_remaining()));
	});
#endif
	C.write_self(W.my_index, (task == T_FARM || task == T_CAPTURE || task == T_WAIT) ? task_group : -1);
	last_hp = hp;
}

void Brain::handle_channel()
{
	// Channels are cut short only when finishing them would cost more than the bag or our life:
	// recall is broken by any damage (so an enemy about to reach us makes it pointless), a tribute survives
	// damage but not a stun or death.
	auto& me = bc::self();
	const bool recalling = flag(state, bc::champion_state::recalling);
	const bool tributing = flag(state, bc::champion_state::submitting_gems);
	float incoming = 0;
	bool stunner_close = false, threat_close = false;
	for (const auto& e : world().enemies)
	{
		if (!e.visible || !e.alive)
			continue;
		const int d = cheb(e.pos, pos);
		const int reach = e.kit.attack_range + (e.kit.ranged ? 0 : 1) + (e.ready(e.kit.dash) ? 2 : 0);
		if (d <= reach + 1)
		{
			threat_close = true;
			incoming += e.str + e.burst() / 2.f;
		}
		if (d <= 4 && (e.ready(e.kit.cc) || (e.ready(e.kit.aoe) && e.kit.aoe_stuns)))
			stunner_close = true;
	}
	bool cancel = false;
	if (recalling && threat_close && !world().ally_spawn.is_set(pos))
		cancel = true; // they will hit us before it completes: act instead of standing still
	if (tributing)
	{
		const int left = std::max(1, static_cast<int>((gems + 9) / 10) - 1);
		if (incoming * static_cast<float>(left + 1) >= hp || (stunner_close && gems >= 20 && threat_close))
			cancel = true;
	}
	if (cancel)
	{
		try
		{
			if (recalling)
				me.cancel_recall();
			else
			{
				me.cancel_submit_gems();
				tribute_cancel_round = round;
			}
		}
		catch (...)
		{
		}
		return;
	}
	auto& C = comms();
	C.write_self(world().my_index, task == T_CAPTURE ? task_group : -1);
}

void Brain::shop()
{
	auto& me = bc::self();
	auto& W = world();
	const bool on_spawn = alive && W.ally_spawn.is_set(pos);
	const bool remote = type == CT::tavi;
	if (!on_spawn && alive && !remote)
		return;
	// A teleport crystal opens uncontested island camps; it is cheap, buy it first.
	bool any_hop = false;
	for (const auto& h : W.hops)
		any_hop |= h.valid;
	if ((on_spawn || !alive) && (!W.islands.empty() || any_hop) && gold >= 10)
	{
		try
		{
			if (me.consumables()[bc::consumable_type::tp_crystal].count() == 0)
			{
				me.buy(bc::consumable_type::tp_crystal);
				gold -= 10;
			}
		}
		catch (...)
		{
		}
	}
	while (build_idx < build.size() && gold >= 30)
	{
		const I item = build[build_idx];
		std::uint32_t n = 0;
		while (build_idx + n < build.size() && build[build_idx + n] == item && gold >= 30 * (n + 1))
			++n;
		try
		{
			me.buy(item, n);
			build_idx += n;
			gold -= 30 * n;
		}
		catch (...)
		{
			break;
		}
	}
	// A spare altar lock once the first emblem is done (consumables only on spawn or while dead).
	if ((on_spawn || !alive) && build_idx >= 5 && gold >= 10)
	{
		try
		{
			if (me.consumables()[bc::consumable_type::altar_lock].count() == 0)
			{
				me.buy(bc::consumable_type::altar_lock);
				gold -= 10;
			}
		}
		catch (...)
		{
		}
	}
	if (on_spawn)
	{
		// Health bought on spawn heals; refresh our numbers.
		bc::detail::champion_info i{};
		if (bc::detail::sdk_champion(self, &i) == 0)
			hp = i.health, max_hp = std::max(1.f, i.max_health), str = i.strength, focus = i.focus;
	}
}

// ---------------------------------------------------------------------------------------------- perception helpers

void Brain::build_danger()
{
	auto& W = world();
	danger.clear();
	camp_danger.clear();
	enemy_near = false;
	for (const auto& e : W.enemies)
	{
		if (!e.alive || e.seen_round < 0)
			continue;
		const int age = round - e.seen_round;
		if (age > P.threat_memory)
			continue;
		// Cooldowns are known while visible; an unseen enemy is assumed to have everything ready.
		const bool fresh = age == 0;
		const bool dash_up = e.kit.dash >= 0 && (!fresh || e.ready(e.kit.dash));
		const bool spell_up = (e.kit.dmg >= 0 && (!fresh || e.ready(e.kit.dmg))) || (e.kit.cc >= 0 && (!fresh || e.ready(e.kit.cc))) ||
			(e.kit.aoe >= 0 && (!fresh || e.ready(e.kit.aoe)));
		int reach = e.kit.attack_range + (e.kit.ranged ? 0 : 1) + (dash_up ? 2 : 0);
		if (spell_up)
			reach = std::max(reach, 4);
		reach += age;
		danger.draw_chebyshev(e.pos, static_cast<float>(reach));
		if (cheb(e.pos, pos) <= 9)
			enemy_near = true;
	}
	for (const auto& g : W.groups)
		if (g.st == ST_ALIVE && g.awake && g.hp_total > 0 && !g.harmless && cheb(g.center, pos) <= 10)
			camp_danger |= g.near;
	alert_zone.clear();
	const auto& C = comms();
	if (P.alert_radius > 0 && C.alert_kind == AL_DANGER && C.fresh(round, P.alert_age))
		alert_zone.draw_chebyshev(C.alert_pos, static_cast<float>(P.alert_radius));
}

bool Brain::in_awake_camp_range() const { return camp_danger.is_set(pos); }

int Brain::enemies_within(int r) const
{
	int n = 0;
	for (const auto& e : world().enemies)
		if (e.alive && e.visible && cheb(e.pos, pos) <= r)
			++n;
	return n;
}

int Brain::nearest_altar(int& dist) const
{
	auto& W = world();
	int best = -1;
	dist = BIG;
	for (std::size_t i = 0; i < W.altars.size(); ++i)
	{
		nav().ensure_altar(static_cast<int>(i));
		int d = nav().altar_dist(static_cast<int>(i), pos);
		if (W.altar_locked_by_enemy(static_cast<int>(i)))
			d += 6; // three hits to clear it
		if (altar_unsafe(static_cast<int>(i)))
			d += P.unsafe_altar_penalty; // contested and enemies seen there: our carriers die on the way
		if (d < dist)
			dist = d, best = static_cast<int>(i);
	}
	return best;
}

bool Brain::after_move(bool moved)
{
	if (!moved)
		return false;
	// Refresh allowances after moving (ranged champions lose their attack when walking; a dash spends the cast).
	bc::detail::champion_info i{};
	if (bc::detail::sdk_champion(self, &i) == 0)
	{
		pos = { i.x, i.y };
		can_move = flag(i.state, bc::champion_state::can_move);
		can_attack = flag(i.state, bc::champion_state::can_attack);
		can_cast = flag(i.state, bc::champion_state::can_cast);
	}
	if (kit.dash >= 0)
	{
		std::int32_t c = 0;
		if (bc::detail::sdk_champion_cooldown(self, static_cast<std::uint32_t>(kit.dash), &c) == 0 && c > cd[static_cast<std::size_t>(kit.dash)])
		{
			cd[static_cast<std::size_t>(kit.dash)] = c;
			cast_done = true;
		}
	}
	return true;
}

bool Brain::step(const bc::bitboard& goals, bool avoid_danger, bool allow_dash)
{
	if (bc::fuel_remaining() < 22000)
	{
		const auto pts = goals.positions();
		if (pts.empty() || !can_move)
			return false;
		try
		{
			return after_move(bc::self().move_towards(pts.front()));
		}
		catch (...)
		{
		}
		return false;
	}
	bc::bitboard avoid = danger | camp_danger | alert_zone;
	return after_move(Nav::step_to(pos, goals, avoid_danger ? &avoid : nullptr, allow_dash ? kit.dash : -1, can_move));
}

bool Brain::go_group(Group& g, int stop_at, bool avoid)
{
	auto& N = nav();
	bc::bitboard fallback;
	for (auto t : g.tiles)
		fallback.draw_chebyshev(t, static_cast<float>(stop_at));
	if (stop_at > 0)
		fallback &= ~g.mask;
	const bc::bitboard av = danger | (camp_danger & ~g.near) | alert_zone;
	if (N.ensure_group(g.id))
		return after_move(Nav::step_field(pos, N.group_fields[static_cast<std::size_t>(g.id)], stop_at, avoid ? &av : nullptr, kit.dash, can_move, fallback));
	return after_move(Nav::step_to(pos, fallback, avoid ? &av : nullptr, kit.dash, can_move));
}

bool Brain::go_altar(int id)
{
	auto& N = nav();
	auto& W = world();
	bc::bitboard fallback;
	for (auto t : W.altar_approach[static_cast<std::size_t>(id)])
		fallback.set(t);
	const bc::bitboard av = danger | camp_danger | alert_zone;
	if (N.ensure_altar(id))
		return after_move(Nav::step_field(pos, N.altar_fields[static_cast<std::size_t>(id)], 0, &av, kit.dash, can_move, fallback));
	return after_move(Nav::step_to(pos, fallback, &av, kit.dash, can_move));
}

bool Brain::go_home_step(bool avoid)
{
	auto& W = world();
	const bc::bitboard av = danger | camp_danger | alert_zone;
	return after_move(Nav::step_field(pos, W.home, 0, avoid ? &av : nullptr, kit.dash, can_move, W.ally_spawn));
}

void Brain::prebuild_fields()
{
	{
		// Crystal shortcuts: try one untested group per turn while fuel is plentiful. Never on a turn that
		// already ran out of fuel (it continues in a later round: extra work there costs whole rounds), and
		// not in the opening turns, which need their fuel for the first moves.
		auto& W = world();
		if (static_cast<int>(bc::round_number()) != round)
			return;
		if (P.hops_enabled && round >= init_round + 3)
		{
			nav().hop_scan_step(22000, round);
			if (bc::fuel_remaining() >= 50000 && static_cast<int>(bc::round_number()) == round)
				for (const auto& g : W.groups)
					if (!W.hops[static_cast<std::size_t>(g.id)].tried)
					{
						nav().ensure_hop(g.id);
						break;
					}
		}
	}
	// Spend leftover fuel building fields for the nearest groups we have not mapped yet.
	auto& W = world();
	auto& N = nav();
	for (int k = 0; k < 2 && bc::fuel_remaining() > 60000 && static_cast<int>(bc::round_number()) == round; ++k)
	{
		int best = -1, best_d = BIG;
		for (const auto& g : W.groups)
			if (!N.group_fields[static_cast<std::size_t>(g.id)].ready)
			{
				const int d = cheb(g.center, pos);
				if (d < best_d)
					best_d = d, best = g.id;
			}
		if (best < 0 || !N.ensure_group(best))
			return;
	}
}

// ---------------------------------------------------------------------------------------------- actions

bool Brain::attack_unit(const bc::unit& u)
{
	if (!can_attack)
		return false;
	try
	{
		bc::self().attack(u);
		can_attack = false;
		if (kit.ranged)
			can_move = false;
		return true;
	}
	catch (...)
	{
		return false;
	}
}

bool Brain::cast_unit_camp(int slot, const bc::camp& c)
{
	if (!ready(slot))
		return false;
	try
	{
		if (ab[static_cast<std::size_t>(slot)].use(c))
		{
			cast_done = true;
			cd[static_cast<std::size_t>(slot)] = 8;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

bool Brain::cast_unit_champ(int slot, const bc::champion& c)
{
	if (!ready(slot))
		return false;
	try
	{
		if (ab[static_cast<std::size_t>(slot)].use(c))
		{
			cast_done = true;
			cd[static_cast<std::size_t>(slot)] = 8;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

bool Brain::cast_ground(int slot, vec2 p)
{
	if (!ready(slot))
		return false;
	try
	{
		if (ab[static_cast<std::size_t>(slot)].use(p))
		{
			cast_done = true;
			cd[static_cast<std::size_t>(slot)] = 8;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

bool Brain::cast_self(int slot)
{
	if (!ready(slot))
		return false;
	try
	{
		if (ab[static_cast<std::size_t>(slot)].use())
		{
			cast_done = true;
			cd[static_cast<std::size_t>(slot)] = 8;
			if (slot == kit.reset)
				can_attack = true;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

float Brain::camp_dps() const
{
	float base = str * (1.f + (kit.reset >= 0 ? 0.125f : 0.f));
	float spells = 0;
	if (kit.dmg >= 0)
		spells += focus * kit.dmg_mod;
	if (kit.cc >= 0)
		spells += focus * kit.cc_mod;
	if (kit.aoe >= 0)
		spells += focus * kit.aoe_mod;
	return base + spells / 8.f;
}

float Brain::burst_vs(const Enemy& e) const
{
	(void)e;
	float b = can_attack ? str : 0.f;
	float extra = 0;
	if (ready(kit.reset))
		extra = std::max(extra, str);
	if (ready(kit.dmg))
		extra = std::max(extra, focus * kit.dmg_mod);
	if (ready(kit.cc))
		extra = std::max(extra, focus * kit.cc_mod);
	if (ready(kit.aoe))
		extra = std::max(extra, focus * kit.aoe_mod);
	return b + extra;
}

void Brain::support_spells()
{
	auto& W = world();
	if (kit.heal >= 0 && ready(kit.heal))
	{
		const Ally* best = nullptr;
		float best_missing = focus * kit.heal_mod * 0.6f;
		for (const auto& a : W.allies)
			if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= static_cast<int>(kit.heal_range))
			{
				const float missing = a.max_hp - a.hp;
				if (missing > best_missing)
					best_missing = missing, best = &a;
			}
		if (best)
			cast_unit_champ(kit.heal, best->ch);
	}
	if (kit.shield >= 0 && ready(kit.shield) && hp < 0.9f * max_hp && (in_awake_camp_range() || enemies_within(4) > 0))
		cast_self(kit.shield);
}

void Brain::use_locks()
{
	auto& W = world();
	auto& me = bc::self();
	std::uint32_t locks = 0;
	try
	{
		locks = me.consumables()[bc::consumable_type::altar_lock].count();
	}
	catch (...)
	{
		return;
	}
	if (locks == 0)
		return;
	for (std::size_t i = 0; i < W.altars.size(); ++i)
	{
		const vec2 a = W.altars[i];
		if (cheb(a, pos) > 2)
			continue;
		bool enemy_tributing = false;
		for (const auto& e : W.enemies)
			if (e.visible && e.alive && e.tributing && cheb(e.pos, a) <= 1)
				enemy_tributing = true;
		const bool enemy_side = W.dist_away(a) + 2 < W.dist_home(a);
		bool has_any_lock = false;
		try
		{
			has_any_lock = bc::vision::has_altar_lock(a);
		}
		catch (...)
		{
		}
		if (enemy_tributing || (enemy_side && !has_any_lock))
		{
			try
			{
				if (me.consumables()[bc::consumable_type::altar_lock].use(a))
					return;
			}
			catch (...)
			{
			}
		}
	}
}

void Brain::place_ward(bool force)
{
	if (!force && round - ward_round < 10)
		return;
	auto& W = world();
	const vec2 dir = sgn_step(pos, W.enemy_spawn_c);
	const vec2 cands[] = { pos + dir * 2, pos + dir, pos + vec2{ dir.x * 2, dir.y }, pos + vec2{ dir.x, dir.y * 2 } };
	for (auto c : cands)
	{
		if (!bc::map::is_in_bounds(c) || W.walls.is_set(c) || W.camp_occ.is_set(c))
			continue;
		try
		{
			if (bc::self().place_ward(c))
			{
				ward_round = round;
				return;
			}
		}
		catch (...)
		{
		}
	}
	ward_round = round; // do not retry every turn
}

// ---------------------------------------------------------------------------------------------- champion combat

bool Brain::combat()
{
	auto& W = world();
	engaged = false;
	std::vector<Enemy*> E;
	for (auto& e : W.enemies)
		if (e.alive && e.visible && cheb(e.pos, pos) <= 9)
		{
			// An enemy on its own spawn heals fully every round: it cannot be killed (unless one turn of
			// burst does it) and is no reason to stand and trade. Maps with adjacent spawns otherwise lock
			// both teams in a pointless duel for the whole game.
			if (W.enemy_spawn.is_set(e.pos) && e.max_hp > burst_vs(e) + 1.f)
				continue;
			E.push_back(&e);
		}
	if (E.empty())
		return false;

	// Enemy reach next turn: attack range (+1 step for melee), +2 with a dash ready, 4 with a spell ready.
	auto reach_of = [](const Enemy& e) {
		int r = e.kit.attack_range + (e.kit.ranged ? 0 : 1) + (e.ready(e.kit.dash) ? 2 : 0);
		if (e.ready(e.kit.dmg) || e.ready(e.kit.cc) || e.ready(e.kit.aoe))
			r = std::max(r, 4);
		return r;
	};
	// Their side: enemies that can hit us within about two turns count fully, the rest of the visible
	// group half (they arrive a turn or two later). Stuns cost us a turn: count ready stuns as damage.
	float their_hp = 0, their_dps = 0, incoming = 0;
	int stunners = 0;
	for (auto* e : E)
	{
		const int d = cheb(e->pos, pos);
		const float w = d <= reach_of(*e) + 2 ? 1.f : P.far_enemy_weight;
		float dps = e->str + e->focus * best_mod(e->kit) / 8.f + e->burst() / 3.f;
		if (e->ready(e->kit.cc) || (e->ready(e->kit.aoe) && e->kit.aoe_stuns))
			++stunners, dps *= 1.15f;
		their_hp += w * e->hp;
		their_dps += w * dps;
		if (d <= reach_of(*e))
			incoming += e->str + e->burst() / 2.f;
	}
	// Our side: self plus visible allies within 6 (with their spells, not just basic attacks).
	float my_burst = 0;
	if (ready(kit.dmg)) my_burst = std::max(my_burst, focus * kit.dmg_mod);
	if (ready(kit.cc)) my_burst = std::max(my_burst, focus * kit.cc_mod);
	if (ready(kit.aoe)) my_burst = std::max(my_burst, focus * kit.aoe_mod);
	if (ready(kit.reset)) my_burst = std::max(my_burst, str);
	float our_hp = hp, our_dps = str + focus * best_mod(kit) / 8.f + my_burst / 3.f;
	float allies_burst = 0;
	int allies_near = 0;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 6)
		{
			const float ab = std::max(a.str, a.focus * best_mod(a.kit));
			our_hp += a.hp;
			our_dps += P.ally_spell_dps ? a.str + a.focus * best_mod(a.kit) / 8.f + ab / 3.f : a.str * 1.2f;
			allies_burst += a.str;
			++allies_near;
		}
	if (W.ally_spawn.is_set(pos) && P.spawn_heal_bonus)
	{
		// We heal fully next round on spawn, but only while the fight stays here: stepping off spawn to
		// engage loses the heal, and counting it there made champions bounce on and off spawn.
		const int hit_r = (ready(kit.dmg) || ready(kit.cc) || ready(kit.aoe)) ? std::max(4, kit.attack_range) : kit.attack_range;
		bool here = false;
		for (auto* e : E)
			here |= cheb(e->pos, pos) <= hit_r;
		if (here)
			our_hp += max_hp;
	}
	const float t_kill_them = their_hp / std::max(1.f, our_dps);
	const float t_kill_us = our_hp / std::max(1.f, their_dps);
	// Learned calibration: bodies that died after choosing fights trust their estimate less.
	const float adv = t_kill_us / std::max(0.1f, t_kill_them) * learner().fight_scale();

	// Backup: allies in sight, plus hidden allies whose claimed camp is close (they are a few steps away).
	// Half our deaths on the ladder were lone champions caught by two or more enemies.
	int backup = allies_near;
	int dead_allies = 0;
	{
		const auto& C = comms();
		for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
		{
			const auto& a = W.allies[static_cast<std::size_t>(i)];
			if (!a.alive)
			{
				++dead_allies;
				continue;
			}
			if (a.handle == self || (a.visible && cheb(a.pos, pos) <= 6))
				continue;
			const int cg = i < 6 ? C.claim[static_cast<std::size_t>(i)] : -1;
			const vec2 at = a.visible ? a.pos : (cg >= 0 && cg < static_cast<int>(W.groups.size()) ? W.groups[static_cast<std::size_t>(cg)].center : vec2{ -100, -100 });
			if (cheb(at, pos) <= P.backup_radius)
				++backup;
		}
	}
	const bool isolated = backup == 0;
	// With half the team waiting to respawn, another death hands them the map: only sure fights.
	const bool reserve = dead_allies * 2 >= static_cast<int>(W.allies.size());
	int nearest_enemy = BIG;
	for (auto* e : E)
		nearest_enemy = std::min(nearest_enemy, cheb(e->pos, pos));

	// Team-consistent focus target: allies seeing the same fight pick the same enemy (no distance term).
	// Cassi and Issac die together: hitting the weaker of the pair kills two bodies. Ren reflects 0.2 x focus
	// per hit, so a low champion should not swing at him unless he dies now.
	const int my_reach = kit.attack_range + (kit.ranged ? 0 : 1) + (ready(kit.dash) ? 2 : 0);
	Enemy* tgt = nullptr;
	float best = -1;
	for (auto* e : E)
	{
		if (cheb(pos, e->pos) > std::max(my_reach, 4) + 2)
			continue;
		float eff_hp = std::max(50.f, e->hp);
		float bonus = 0;
		if (e->type == CT::cassi || e->type == CT::issac)
			bonus += 60.f;
		if (e->type == CT::ren)
		{
			const float reflect = bc::constants::passive_abilities::ren_retaliation_focus_ratio * e->focus;
			if (hp < 4.f * reflect && e->hp > burst_vs(*e))
				continue;
		}
		const float v = (60.f + bonus + static_cast<float>(e->gems) + (e->channeling ? 60.f : 0.f)) / eff_hp;
		if (v > best)
			best = v, tgt = e;
	}
	if (!tgt)
	{
		tgt = E.front();
		for (auto* e : E)
			if (cheb(pos, e->pos) < cheb(pos, tgt->pos))
				tgt = e;
	}
	const int d = cheb(pos, tgt->pos);
	const bool killable = d <= std::max(my_reach, (ready(kit.dmg) || ready(kit.cc)) ? 4 : 0) &&
		tgt->hp <= burst_vs(*tgt) + allies_burst;
	const bool in_reach = danger.is_set(pos);

	// Can we actually get away? Melee and dash chasers move and hit in the same turn. Fleeing only works
	// if no such chaser is close, if our own dash outruns theirs, or if we survive the whole walk home.
	bool chaser = false, chaser_dash = false;
	for (auto* e : E)
		if ((!e->kit.ranged || e->ready(e->kit.dash)) && cheb(pos, e->pos) <= 3 + (e->ready(e->kit.dash) ? 2 : 0))
		{
			chaser = true;
			chaser_dash |= e->ready(e->kit.dash);
		}
	const float t_die = hp / std::max(1.f, incoming);
	const int dh = W.dist_home(pos);
	const bool on_spawn = W.ally_spawn.is_set(pos);
	const bool can_escape = on_spawn || !chaser || (ready(kit.dash) && !chaser_dash) || static_cast<float>(dh) + 1.f < t_die;

	bool fight = false;
	if (killable && adv >= 0.5f)
		fight = true;
	else if (adv >= fight_margin)
		fight = true;
	else if (in_reach && adv >= fight_back_margin)
		fight = true;
	else if (in_reach && !can_escape && adv >= P.cornered_margin)
		fight = true; // fleeing a same-speed chaser hands it free hits: trade instead
	else if (tgt->channeling && adv >= 0.9f)
		fight = true;
	if (fight && !killable && can_escape && (hp < 0.25f * max_hp || (static_cast<int>(gems) >= P.bag_caution && adv < 1.5f)))
		fight = false;
	if (fight && reserve && !(killable && adv >= 1.f) && adv < fight_margin + P.reserve_margin && can_escape)
		fight = false;
	if (fight && isolated && !killable && adv < isolated_fight_adv && can_escape)
		fight = false;
	// Do not dive their spawn: it heals them and they block us.
	if (W.enemy_spawn.is_set(tgt->pos) || cheb(tgt->pos, W.enemy_spawn_c) <= 3)
		fight = fight && killable;
	engaged = fight || in_reach || nearest_enemy <= 5;
	(void)stunners;

	// Early warning: an outnumbering group is visible; allies keep away from it.
	if (!fight && E.size() >= 3 && adv < 1.f)
		post_danger(tgt->pos);
	if (fight)
	{
		comms().post(AL_RALLY, tgt->pos, round);
		learner().on_fight(round);
		task = T_FIGHT;
		return engage(*tgt);
	}
	if (in_reach)
	{
		post_danger(tgt->pos);
		task = T_FLEE;
		// A stun on the closest melee chaser buys a free step (only stuns that still let us walk).
		for (auto* e : E)
			if (e->ch && !kit.cc_excl && (!e->kit.ranged || e->ready(e->kit.dash)) && cheb(pos, e->pos) <= static_cast<int>(kit.cc_range) && ready(kit.cc))
			{
				cast_unit_champ(kit.cc, *e->ch);
				break;
			}
		if (go_home_step(true))
		{
			// Melee champions can still swing after walking.
			if (!kit.ranged && can_attack)
				for (auto* e : E)
					if (e->ch && cheb(pos, e->pos) <= kit.attack_range)
					{
						attack_unit(*e->ch);
						break;
					}
			return true;
		}
		return engage(*tgt); // cornered: hit back
	}
	// Leave before they reach us: alone (or with half the team dead) against a stronger group, start walking
	// home while they are still out of stun range. Same speed means they cannot close the gap.
	if ((isolated || reserve) && adv < P.isolated_flee_adv && nearest_enemy <= P.flee_dist && task != T_CAPTURE)
	{
		post_danger(tgt->pos);
		task = T_FLEE;
		if (go_home_step(true))
			return true;
		if (W.ally_spawn.is_set(pos))
		{
			task = T_WAIT; // already home: hold here (healing) rather than step out to them and back
			return true;
		}
	}
	return false;
}

void Brain::post_danger(vec2 at)
{
	// Nothing reads DANGER unless alert_radius > 0, and the team has one alert slot: never let it replace a
	// fresh RALLY or OPPORTUNITY (an enemy tribute the team should converge on).
	auto& C = comms();
	if (P.alert_radius <= 0 || (C.fresh(round, 6) && (C.alert_kind == AL_RALLY || C.alert_kind == AL_OPPORTUNITY)))
		return;
	C.post(AL_DANGER, at, round);
}

bool Brain::engage(Enemy& e)
{
	if (!e.ch)
		return false;
	if (e.type == CT::ren)
	{
		// Ren reflects 0.2 x focus of every hit back at the attacker: never trade our last health into him.
		const float reflect = bc::constants::passive_abilities::ren_retaliation_focus_ratio * e.focus;
		if (hp <= 2.5f * reflect && e.hp > burst_vs(e))
		{
			task = T_FLEE;
			go_home_step(true);
			return true;
		}
	}
	auto& ec = *e.ch;
	int d = cheb(pos, e.pos);
	if (d > kit.attack_range)
	{
		bc::bitboard goal;
		goal.draw_chebyshev(e.pos, static_cast<float>(kit.attack_range));
		if (kit.ranged)
		{
			const bool spell_now = d <= 4 && (ready(kit.cc) || ready(kit.dmg) || ready(kit.aoe));
			if (d <= kit.attack_range + 2 && ready(kit.dash))
				step(goal, false, true);
			else if (spell_now)
			{
				if (!cast_unit_champ(kit.cc, ec) && !cast_unit_champ(kit.dmg, ec))
					cast_ground(kit.aoe, e.pos);
				return true;
			}
			else
				step(goal, false, true);
		}
		else
		{
			if (d == 2 || !(d <= 4 && (ready(kit.cc) || ready(kit.dmg))))
				step(goal, false, true);
			else if (!cast_unit_champ(kit.cc, ec))
				cast_unit_champ(kit.dmg, ec);
		}
		d = cheb(pos, e.pos);
	}
	if (d <= kit.attack_range)
	{
		const bool want_stun = e.channeling || e.kit.ranged == false;
		if (want_stun)
			cast_unit_champ(kit.cc, ec);
		if (!cast_done && kit.enhanced_reset && ready(kit.reset))
			cast_self(kit.reset);
		if (!cast_done && kit.dmg >= 0 && focus * kit.dmg_mod > str)
			cast_unit_champ(kit.dmg, ec);
		if (!cast_done && kit.aoe >= 0 && kit.aoe_stuns)
			cast_ground(kit.aoe, e.pos);
		if (attack_unit(ec))
		{
			std::int32_t alive_flag = 1;
			bc::detail::sdk_champion_is_alive(e.handle, &alive_flag);
			if (alive_flag && !cast_done && ready(kit.reset) && cast_self(kit.reset))
				attack_unit(ec);
		}
		if (!cast_done)
			cast_unit_champ(kit.cc, ec) || cast_unit_champ(kit.dmg, ec) || cast_ground(kit.aoe, e.pos);
	}
	return true;
}

// ---------------------------------------------------------------------------------------------- safety, tribute, shopping

bool Brain::go_home()
{
	auto& W = world();
	task = T_HOME;
	if (W.ally_spawn.is_set(pos))
		return true;
	const int dh = W.dist_home(pos);
	if (dh > P.recall_min_dist && safe_to_recall())
	{
		try
		{
			bc::self().recall();
			return true;
		}
		catch (...)
		{
		}
	}
	go_home_step(true);
	return true;
}

void Brain::update_priority()
{
	// Turn order (verified on 14,069 ladder rounds): team A leads odd rounds, team B even rounds; teams
	// alternate turns; within a team higher priority acts first; set_priority applies from the next round.
	// A fighter that acts last in a round we trail and first in the next round we lead gets two actions in
	// a row with no enemy turn between them. So fighters alternate: high when we lead the next round, low
	// when we trail it. Escapers move first. (57.6% vs the previous bot in mirror tests, -14% deaths.)
	int prio = P.prio_idle;
	if (!P.prio_alternate)
	{
		// Previous scheme: engaged champions simply act first.
		if (engaged || task == T_FIGHT || task == T_FLEE)
			prio = 8 + ((kit.cc >= 0 || kit.aoe_stuns) ? 1 : 0) + (hp < 0.35f * max_hp ? 1 : 0);
		else if (task == T_CAPTURE)
			prio = P.prio_capture;
	}
	else if (task == T_FLEE)
		prio = P.prio_flee;
	else if (engaged || task == T_FIGHT)
	{
		const bool team_a = bc::detail::sdk_my_team() == 0;
		const bool lead_next = (((round + 1) & 1) == 1) == team_a;
		const int bonus = ((kit.cc >= 0 || kit.aoe_stuns) ? 1 : 0) + (hp < 0.35f * max_hp ? 1 : 0);
		prio = lead_next ? P.prio_fight + bonus : -P.prio_fight + bonus;
	}
	else if (task == T_CAPTURE)
		prio = P.prio_capture;
	if (prio == cur_prio)
		return;
	try
	{
		bc::self().set_priority(prio);
		cur_prio = prio;
	}
	catch (...)
	{
	}
}

bool Brain::escort_wait()
{
	// After a wipe, champions that walk out one at a time meet their pack one at a time. A freshly respawned
	// champion holds on spawn (healing, shopping) while we are down by deficit_escort or more bodies and
	// an ally respawns soon, then they leave together.
	auto& W = world();
	if (deficit < P.deficit_escort || !W.ally_spawn.is_set(pos) || round - respawn_round > P.escort_wait || enemies_within(9) > 0)
		return false;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 4)
			return false; // someone to walk with
	const int respawn = static_cast<int>(bc::constants::respawn_time);
	for (const auto& a : W.allies)
		if (!a.alive && a.died_round > -1000 && a.died_round + respawn - round <= P.escort_wait)
		{
			task = T_WAIT;
			return true;
		}
	return false;
}

bool Brain::altar_unsafe(int i) const
{
	auto& W = world();
	if (!W.altar_contested[static_cast<std::size_t>(i)] || round - W.altar_enemy_round[static_cast<std::size_t>(i)] > P.altar_enemy_memory)
		return false;
	// An ally standing by makes it a two-body bank.
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, W.altars[static_cast<std::size_t>(i)]) <= 5)
			return false;
	return true;
}

bool Brain::safe_to_recall() const
{
	// Any damage cancels a recall: no awake camp in range and no enemy that could reach us during the channel.
	if (in_awake_camp_range() || danger.is_set(pos))
		return false;
	for (const auto& e : world().enemies)
		if (e.alive && e.seen_round >= 0 && round - e.seen_round <= 2 && cheb(e.pos, pos) <= 7)
			return false;
	return true;
}

bool Brain::home_trip()
{
	// A trip home heals fully and turns gold into shards; recall (5 turn ends) makes it cheap from far away.
	// Strong teams recall right after captures to heal, shop and bank near spawn instead of walking.
	auto& W = world();
	if (task == T_CAPTURE || reward_here() || W.ally_spawn.is_set(pos))
		return false;
	const int dh = W.dist_home(pos);
	if (dh >= BIG || dh <= 2)
		return false;
	const bool can_recall = dh > P.recall_min_dist && safe_to_recall();
	const int cost = can_recall ? static_cast<int>(bc::constants::recall_time) : dh;
	const bool shopper = type != CT::tavi && build_idx < build.size();
	const int shards = shopper ? static_cast<int>(gold / 30) : 0;
	const bool hurt = hp < P.home_hp * max_hp;
	bool go = false;
	if (shards >= P.shop_shards && cost <= P.shop_cost_max)
		go = true; // a batch of shards is waiting
	else if (hurt && (shards >= 2 || cost <= 6))
		go = true; // low anyway: heal now and spend what we have
	else if (round - last_bank_round <= 1 && can_recall && dh > P.cap_recall_min_home &&
		(hp < P.cap_recall_hp * max_hp || shards >= 3))
		go = true; // just banked far from home: recall to heal and shop instead of walking on hurt
	if (!go)
		return false;
	return go_home();
}

bool Brain::safety()
{
	// Incoming camp damage per round: each camp hits the nearest champion in its range 3, so a camp with a
	// visible ally strictly nearer to it does not hit us (a tank in front shields the ranged behind it).
	// Keep enough health to walk out of range (escape steps) plus a margin.
	auto& W = world();
	float camp_in = 0;
	int escape = 0;
	for (const auto& g : W.groups)
		if (g.st == ST_ALIVE && g.awake && !g.harmless && g.near.is_set(pos))
			for (std::size_t i = 0; i < g.camps.size(); ++i)
			{
				const int d = cheb(g.camps[i].pos, pos);
				if (g.hp[i] <= 0 || d > 3)
					continue;
				bool shielded = false;
				for (const auto& a : W.allies)
					if (P.safety_v2)
					if (a.handle != self && a.alive && a.visible && cheb(a.pos, g.camps[i].pos) < d)
					{
						shielded = true;
						break;
					}
				if (shielded)
					continue;
				camp_in += g.camps[i].str;
				escape = std::max(escape, 4 - d);
			}
	const float threshold = std::max(P.retreat_hp * max_hp, camp_in * static_cast<float>(P.safety_v2 ? escape + 1 : 4));
	if (hp >= threshold)
	{
		// On spawn, health is restored only after a turn ends there: after a recall or a walk home, rest one
		// turn before leaving (unless an enemy keeps hitting us, as on maps where the spawns touch).
		if (P.rest_on_spawn && W.ally_spawn.is_set(pos) && hp < 0.95f * max_hp && round - last_hit_round > 1 && enemies_within(6) == 0)
		{
			task = T_HOME;
			return true;
		}
		return false;
	}
	if (in_awake_camp_range() && camp_in > 0)
	{
		task = T_FLEE;
		const bc::bitboard out = ~camp_danger;
		if (step(out, true, true))
			return true;
	}
	return go_home();
}

void Brain::update_mode()
{
	fight_margin = P.fight_margin;
	fight_back_margin = P.fight_back_margin;
	deny_bonus = P.deny_bonus;
	enemy_half_penalty = P.enemy_half_penalty;
	tribute_min = P.tribute_min;
	if (round < P.early_round)
		tribute_min = std::min(tribute_min, P.early_tribute_min); // bank small and early: gold and safety
	stance = comms().stance;
	isolated_fight_adv = P.isolated_fight_adv;
	if (stance == STANCE_GROUPED)
	{
		// Being invaded: stay together and off their half, demand more before fighting alone.
		enemy_half_penalty *= 2.f;
		deny_bonus *= 0.5f;
		isolated_fight_adv += 0.3f;
	}
	else if (stance == STANCE_PUSH)
	{
		// Winning fights: take their camps and more fights.
		enemy_half_penalty *= 0.4f;
		deny_bonus += 0.4f;
		fight_margin = std::max(1.0f, fight_margin - 0.2f);
	}
	// Numbers: fewer of us alive than of them means their pack meets our singles. Play defensively.
	{
		auto& W = world();
		int us = 0, them = 0;
		for (const auto& a : W.allies)
			us += a.alive;
		for (const auto& e : W.enemies)
			them += e.alive;
		deficit = them - us;
		if (deficit >= P.deficit_defend)
		{
			enemy_half_penalty *= 3.f;
			deny_bonus = 0.f;
			fight_margin += 0.4f;
			isolated_fight_adv += 0.3f;
		}
	}
	const int ours = static_cast<int>(bc::global_submitted_gems(team::ally));
	const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
	if (ours - theirs >= P.lead)
	{
		// Ahead: protect the lead. Bank smaller bags, take only clearly winning fights.
		fight_margin += 0.3f;
		tribute_min = std::max(16, tribute_min * 3 / 4);
	}
	else if (theirs >= P.desperate_at && theirs - ours >= P.lead / 2)
	{
		// They are close to winning: steal, hunt carriers, accept closer fights.
		fight_margin = std::max(0.9f, fight_margin - 0.3f);
		fight_back_margin = std::max(0.55f, fight_back_margin - 0.15f);
		deny_bonus += 0.6f;
		enemy_half_penalty *= 0.4f;
	}
}

bool Brain::on_the_way(int altar) const
{
	// Bank when the altar costs at most two extra steps on the way to our current target.
	if (task_group < 0)
		return false;
	auto& N = nav();
	const auto& gf = N.group_fields[static_cast<std::size_t>(task_group)];
	const auto& af = N.altar_fields[static_cast<std::size_t>(altar)];
	if (!gf.ready || !af.ready)
		return false;
	const auto& g = world().groups[static_cast<std::size_t>(task_group)];
	int altar_to_group = BIG;
	for (auto t : g.tiles)
		altar_to_group = std::min(altar_to_group, af.get(t));
	const int direct = gf.get(pos);
	const int via = af.get(pos) + altar_to_group;
	return direct < BIG && via < BIG && via - direct <= 2;
}

bool Brain::tribute(bool force)
{
	if (gems == 0)
		return false;
	auto& W = world();
	int dist = BIG;
	const int a = nearest_altar(dist);
	if (a < 0 || dist >= BIG)
		return false;
	const int ticks = static_cast<int>((gems + 9) / 10);
	const bool endgame = round + dist + ticks + P.endgame_margin >= static_cast<int>(bc::constants::max_rounds);
	const bool winning = bc::global_submitted_gems(team::ally) + gems >= bc::constants::winning_gems;
	const bool risky = enemy_near && static_cast<int>(gems) >= P.tribute_risky;
	// Once a bank trip starts, finish it: re-deciding every turn let a passing enemy or the on-the-way test
	// flip the choice each round and the champion oscillated in place for hundreds of rounds.
	const bool committed = P.sticky_tribute && task == T_TRIBUTE && static_cast<int>(gems) >= 10;
	const bool want = force || endgame || winning || risky || committed || static_cast<int>(gems) >= tribute_min || dist <= P.tribute_near ||
		(static_cast<int>(gems) >= 10 && on_the_way(a));
	if (!want)
		return false;
	// A tribute cancelled this turn or last (a threat made it pointless): flee, fight or move on first.
	if (round - tribute_cancel_round <= 2 && !endgame && !winning && !force)
		return false;
	// Recall and bank at the altar next to spawn when that beats walking (and heals and shops on the way).
	const int via_home = static_cast<int>(bc::constants::recall_time) + W.spawn_altar_d;
	if (W.dist_home(pos) > P.recall_min_dist && via_home + 2 < dist && safe_to_recall() && !endgame)
	{
		task = T_TRIBUTE;
		return go_home();
	}
	// The best altar is contested and enemies were just there: do not walk a bag into them alone. Keep
	// farming (the bag is safer moving with us than dying at their altar) unless the game is on the line.
	if (altar_unsafe(a) && !endgame && !winning && !force)
		return false;
	task = T_TRIBUTE;
	const vec2 altar = W.altars[static_cast<std::size_t>(a)];
	if (cheb(pos, altar) > 1)
		go_altar(a);
	if (cheb(pos, altar) <= 1)
	{
		try
		{
			bc::self().submit_gems(altar);
			place_ward(true);
		}
		catch (...)
		{
		}
	}
	return true;
}

bool Brain::shop_trip()
{
	auto& W = world();
	if (type == CT::tavi || build_idx >= build.size())
		return false;
	const int dh = W.dist_home(pos);
	const bool rich = static_cast<int>(gold) >= P.shop_gold && dh <= P.shop_trip_max;
	const bool hurt_and_rich = gold >= 90 && hp < 0.6f * max_hp && dh <= P.shop_trip_max;
	if (!rich && !hurt_and_rich)
		return false;
	if (task == T_CAPTURE || reward_here())
		return false;
	return go_home();
}

bool Brain::reward_here()
{
	// `task` still holds last turn's value: right after the last camp dies it says T_FARM while the reward
	// waits next to us. Capture first (capture_group recalls with the reward when that pays).
	if (task_group < 0)
		return false;
	const auto& g = world().groups[static_cast<std::size_t>(task_group)];
	return g.st == ST_REWARD && nav().group_dist(g, pos) <= 2;
}

bool Brain::respond_to_alert()
{
	auto& C = comms();
	if (!C.fresh(round, 6) || (C.alert_kind != AL_RALLY && C.alert_kind != AL_OPPORTUNITY))
		return false;
	// An enemy channelling a tribute (posted as an opportunity) is the cheapest kill in the game, and the
	// only way to stop a winning tribute: answer it from farther and at lower health than a rally.
	const bool opp = C.alert_kind == AL_OPPORTUNITY;
	const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
	const bool their_endgame = theirs >= P.endgame_alarm;
	const float hp_gate = opp ? (their_endgame ? 0.25f : 0.4f) : 0.6f;
	const int max_d = opp ? (their_endgame ? 16 : 12) : 9;
	if (hp < hp_gate * max_hp || ((task == T_CAPTURE || reward_here()) && !their_endgame))
		return false;
	const int d = cheb(C.alert_pos, pos);
	if (d > max_d || d < 2)
		return false;
	task = T_FIGHT;
	bc::bitboard goal;
	goal.draw_chebyshev(C.alert_pos, static_cast<float>(kit.attack_range));
	return step(goal, false, true);
}

// ---------------------------------------------------------------------------------------------- farming

void Brain::refresh_item_flags() const
{
	// Emblems complete at five shards of a family; recounted only when the build index moves (this is read
	// for every camp group every turn).
	if (item_flags_idx == build_idx)
		return;
	int j = 0, d = 0, m = 0;
	for (std::size_t i = 0; i < build_idx && i < build.size(); ++i)
	{
		j += build[i] == I::jungle_shard_of_strength || build[i] == I::jungle_shard_of_health || build[i] == I::jungle_shard_of_focus;
		d += build[i] == I::durability_shard_of_health || build[i] == I::durability_shard_of_strength || build[i] == I::durability_shard_of_focus;
		m += build[i] == I::monster_shard_of_health || build[i] == I::monster_shard_of_strength || build[i] == I::monster_shard_of_focus;
	}
	jungle_ok = j >= 5;
	durability_ok = d >= 5;
	monster_ok = m >= 5;
	item_flags_idx = build_idx;
}

bool Brain::jungle_done() const
{
	refresh_item_flags();
	return jungle_ok;
}

bool Brain::durability_done() const
{
	refresh_item_flags();
	return durability_ok;
}

bool Brain::monster_done() const
{
	refresh_item_flags();
	return monster_ok;
}

float Brain::dps_on(const Group& g) const
{
	// Basic attacks every round (+1/8 with an attack reset); Varg's splash hits every live camp next to the
	// target, so packed groups die several times faster. Spells land once per cooldown (8 rounds); radius-1
	// area spells hit the same cluster. Ren's retaliation hits back each camp attacking him.
	const float cl = g.cluster;
	float base = str * (1.f + (kit.reset >= 0 ? 0.125f : 0.f));
	if (type == CT::varg)
		base *= cl;
	float spells = 0;
	if (kit.dmg >= 0)
		spells += focus * kit.dmg_mod;
	if (kit.cc >= 0)
		spells += focus * kit.cc_mod;
	if (kit.aoe >= 0)
		spells += focus * kit.aoe_mod * (kit.aoe_radius >= 1.f ? cl : 1.f);
	float d = base + spells / 8.f;
	if (type == CT::ren && !kit.ranged)
		d += bc::constants::passive_abilities::ren_retaliation_focus_ratio * focus * static_cast<float>(std::min(g.attackers, 3));
	// The Monster emblem's 10% applies to every damage dealt to camps (the engine's strength does not include it).
	if (P.monster_in_dps && monster_done())
		d *= 1.1f;
	return d;
}

float Brain::incoming_on(const Group& g) const
{
	float in = 0;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
		if (g.hp[i] > 0)
			in += g.camps[i].str;
	if (jungle_done())
		in *= 0.7f;
	if (durability_done())
		in *= 0.9f;
	// Varg's self-shield (2.5 x focus, every 8 rounds) soaks a share of it.
	if (kit.shield >= 0)
		in = std::max(in * 0.35f, in - kit.shield_mod * focus / 8.f);
	// Stuns on camps skip their next attack: one camp per cast (area stuns: the cluster).
	if (kit.cc >= 0 || kit.aoe_stuns)
		in *= 1.f - std::min(0.35f, (kit.aoe_stuns ? g.cluster : 1.f) / (8.f * std::max(1, g.attackers)));
	return in;
}

bool Brain::ally_melee(int ally) const
{
	const auto t = world().allies[static_cast<std::size_t>(ally)].type;
	return !(t == CT::tavi || t == CT::stellar || t == CT::cassi || t == CT::prism || t == CT::willow || t == CT::vesper_vale);
}

float Brain::ally_dps_on(int ally, const Group& g) const
{
	const auto& a = world().allies[static_cast<std::size_t>(ally)];
	const auto& d = bc::champion_designs[static_cast<std::size_t>(a.type)];
	const auto s = d.base_stats();
	// Scale the design by how much our own strength has grown (allies shop on the same schedule).
	const auto mine = bc::champion_designs[static_cast<std::size_t>(type)].base_stats();
	const float growth = std::max(1.f, str / std::max(1.f, mine.base_strength));
	float st = a.visible && a.str > 0 ? a.str : s.base_strength * growth;
	float v = st * 1.1f;
	if (a.type == CT::varg)
		v *= g.cluster;
	v += s.base_focus * growth * (a.type == CT::stellar ? 3.4f * std::min(g.cluster, 2.f) / 2.f : (a.type == CT::cassi ? 2.f : 1.5f)) / 8.f;
	return v;
}

int Brain::trip_cost(const Group& g) const
{
	// Heal at spawn and come back: recall (5 turn ends, 3 with Home) beats walking once spawn is far.
	const int hd = std::min(g.d_home_c, 60);
	const int recall = static_cast<int>(bc::constants::recall_time);
	return 2 + std::min(2 * hd, recall + hd);
}

float Brain::group_score(const Group& g, int& eta, bool* need_pair, int d_override) const
{
	if (need_pair)
		*need_pair = false;
	auto& W = world();
	auto& C = comms();
	eta = BIG;
	const int d_tile = d_override >= 0 ? d_override : nav().group_dist(g, pos);
	if (d_tile >= BIG)
		return -1;
	const int d_adj = std::max(0, d_tile - 1);

	// Living allies that claim this group, and the lowest claimer index (it captures).
	int claimers = 0, first_claimer = 99;
	bool closer_lower_claimer = false; // a lower-index claimer at least as close to a reward as we are
	float ally_dps = 0;
	bool melee_ally = false;
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
		if (i != W.my_index && C.claim[static_cast<std::size_t>(i)] == g.id && W.allies[static_cast<std::size_t>(i)].alive)
		{
			// Claims are seen a round late: on the group we already hold only lower-index claimers count,
			// otherwise two allies wanting one group both yield, both switch, and repeat forever.
			if (P.claim_tiebreak && g.id == task_group && i > W.my_index)
				continue;
			++claimers;
			first_claimer = std::min(first_claimer, i);
			if (g.st == ST_REWARD && i < W.my_index)
			{
				const auto& a = W.allies[static_cast<std::size_t>(i)];
				// Unseen allies are beyond vision, so farther than us when we are close.
				closer_lower_claimer |= a.visible ? nav().group_dist(g, a.pos) <= d_tile : d_tile > 7;
			}
			ally_dps += ally_dps_on(i, g);
			melee_ally |= ally_melee(i);
		}

	const float my_dps = std::max(10.f, dps_on(g));
	float hp_left = 0;
	float time = 0;
	int wait = 0;
	float share = 1.f;
	switch (g.st)
	{
	case ST_REWARD:
		// One body captures; if allies claim it, the lowest index takes it unless we are clearly nearer
		// (the joiner may still be walking in while we stand next to the reward).
		if (claimers && first_claimer < W.my_index && closer_lower_claimer)
			return -1;
		eta = d_tile;
		time = static_cast<float>(eta) + 6.f;
		break;
	case ST_RESPAWN:
	{
		const int avail = g.ready_round - round;
		if (avail > d_adj + P.max_wait)
			return -1;
		wait = std::max(0, avail - d_adj);
		hp_left = g.max_hp;
		break;
	}
	default:
		hp_left = g.hp_total;
		break;
	}
	if (g.st != ST_REWARD)
	{
		eta = d_adj;
		if (claimers)
		{
			// Join only packs too heavy for one body; never a third body except on a monolith.
			const float solo_rounds = hp_left / std::max(10.f, ally_dps);
			const bool heavy = g.monolith || g.elk || (!g.harmless && (solo_rounds > P.join_min_rounds || g.attackers >= 2));
			if (!heavy || claimers >= (g.monolith ? 4 : 1 + P.max_join))
				return -1;
			share = P.join_share;
		}
		// Rounds to clear the group with the given helpers; false when it cannot be done in max_trips.
		auto plan = [&](float helpers_dps, bool helper_melee, float& t) {
			const float kill = hp_left / (my_dps + helpers_dps);
			t = static_cast<float>(d_adj + wait) + kill + 6.f;
			if (g.harmless)
				return true;
			// Camps hit the nearest champion: a ranged champion next to a melee ally takes almost nothing.
			const float in = incoming_on(g);
			const bool i_tank = !(kit.ranged && helper_melee);
			const float my_share = i_tank ? (helper_melee && !kit.ranged ? 0.5f : 1.f) : 0.1f;
			const float taken = in * my_share * kill;
			const float reserve = std::max(P.camp_hp_reserve * max_hp, in * 3.f);
			const float budget_now = std::max(0.f, hp - reserve);
			const float budget_full = std::max(1.f, max_hp - reserve);
			if (i_tank && budget_full < in * my_share * 5.f)
				return false; // cannot even survive a few rounds next to it
			const float extra = taken - budget_now;
			const int trips = extra > 0 ? static_cast<int>(std::ceil(extra / budget_full)) : 0;
			if (trips > P.max_trips)
				return false;
			t += static_cast<float>(trips * trip_cost(g));
			return true;
		};
		if (!plan(ally_dps, melee_ally, time))
		{
			// Too heavy for us (and the bodies already on it). Plan it as a pair: claim it, wait outside camp
			// range for the best-suited ally, then kill it together (elk pairs, wolf packs early in the game).
			if (claimers || !P.pair_plans || g.monolith)
				return -1;
			float best_dps = 0;
			bool best_melee = false;
			for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
				if (i != W.my_index && W.allies[static_cast<std::size_t>(i)].alive)
				{
					const float a = ally_dps_on(i, g);
					if (a > best_dps)
						best_dps = a, best_melee = ally_melee(i);
				}
			if (best_dps <= 0 || !plan(best_dps, best_melee, time))
				return -1;
			time += P.pair_wait;
			share = 0.5f;
			if (need_pair)
				*need_pair = true;
		}
	}

	float value = (static_cast<float>(g.gems) + P.gold_value * static_cast<float>(g.gold)) * share;
	if (!g.ours)
	{
		const float risk = sc_risk;
		if (hp < P.steal_hp_frac * max_hp && risk > 0)
			return -1;
		value *= 1.f + deny_bonus;
		time += enemy_half_penalty * risk;
		if (round - g.seen_round > 60)
			value *= P.unknown_discount;
	}
	{
		// A stronger enemy force recently seen at the camp: walking in alone is how we die.
		float ehp = 0, edps = 0;
		for (int k = 0; k < sc_recent_n; ++k)
			if (cheb(sc_recent[static_cast<std::size_t>(k)].pos, g.center) <= 8)
			{
				ehp += sc_recent[static_cast<std::size_t>(k)].hp;
				edps += sc_recent[static_cast<std::size_t>(k)].dps;
			}
		if (edps > 0)
		{
			float ohp = hp, odps = str + focus * best_mod(kit) / 8.f;
			for (const auto& a : W.allies)
				if (a.handle != self && a.alive && a.visible && cheb(a.pos, g.center) <= 8)
					ohp += a.hp, odps += a.str + a.focus * best_mod(a.kit) / 8.f;
			const float tadv = (ohp / edps) / std::max(0.1f, ehp / std::max(1.f, odps));
			if (tadv < P.target_threat_adv)
				return -1;
		}
	}
	if (round - g.enemy_round < 12)
		time += 12.f;
	if (sc_alert && alert_zone.is_set(g.center))
		time += 25.f;
	// Learned pain: regions where we lost champions recently cost extra rounds.
	time += P.pain_w * learner().pain_at(g.center) * (stance == STANCE_PUSH ? 0.5f : 1.f);
	if (stance == STANCE_GROUPED && !claimers)
	{
		// Grouped: prefer camps near where allies are farming (backup within reach).
		int near = BIG;
		for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
		{
			const int cg = C.claim[static_cast<std::size_t>(i)];
			if (i != W.my_index && cg >= 0 && cg < static_cast<int>(W.groups.size()) && W.allies[static_cast<std::size_t>(i)].alive)
				near = std::min(near, cheb(W.groups[static_cast<std::size_t>(cg)].center, g.center));
		}
		if (near < BIG && near > P.group_radius)
			time += P.group_far_w * static_cast<float>(near - P.group_radius);
	}
	if (g.enemy_on_tile)
	{
		// An enemy capturing a reward: any of our bodies on any tile of the group resets their capture (it
		// completes 6 rounds after they leave, and they get nothing). Healthy, it is a steal; hurt, avoid.
		if (g.st == ST_REWARD && hp >= P.deny_hp_frac * max_hp)
			value *= P.deny_capture_mult;
		else
			value *= 0.5f;
	}
	return value / std::max(1.f, time);
}

bool Brain::inside_island() const { return world().dist_home(pos) >= BIG; }

bool Brain::has_crystal() const
{
	try
	{
		return bc::self().consumables()[bc::consumable_type::tp_crystal].count() > 0;
	}
	catch (...)
	{
		return false;
	}
}

bool Brain::hop_task(int gid)
{
	auto& W = world();
	auto& h = W.hops[static_cast<std::size_t>(gid)];
	auto& me = bc::self();
	if (!h.valid)
	{
		tp_hop = -1;
		return false;
	}
	if (!has_crystal())
	{
		if (W.ally_spawn.is_set(pos) && gold >= 10)
		{
			try
			{
				me.buy(bc::consumable_type::tp_crystal);
				gold -= 10;
			}
			catch (...)
			{
			}
		}
		if (!has_crystal())
		{
			tp_hop = -1;
			return false;
		}
	}
	task = T_FARM;
	task_group = gid;
	if (pos != h.launch)
	{
		if (!h.to_launch.ready && bc::fuel_remaining() > 45000)
		{
			bc::bitboard root, visited;
			root.set(h.launch);
			h.to_launch.f.compute(W.walls, root, visited);
			h.to_launch.ready = true;
		}
		bc::bitboard goal;
		goal.set(h.launch);
		if (h.to_launch.ready)
			after_move(Nav::step_field(pos, h.to_launch, 0, &danger, kit.dash, can_move, goal));
		else
			after_move(Nav::step_to(pos, goal, &danger, kit.dash, can_move));
		if (pos != h.launch)
			return true;
	}
	bool ok = false;
	try
	{
		ok = me.consumables()[bc::consumable_type::tp_crystal].use(h.land);
	}
	catch (...)
	{
	}
	if (!ok)
		h.valid = false; // landing refused (occupied or invalid): never retry this hop
	tp_hop = -1;
	return true;
}

float Brain::island_score(int i) const
{
	auto& W = world();
	const Island& isl = W.islands[static_cast<std::size_t>(i)];
	auto& C = comms();
	for (int k = 0; k < static_cast<int>(W.allies.size()) && k < 6; ++k)
		if (k != W.my_index && W.allies[static_cast<std::size_t>(k)].alive)
			for (int gid : isl.groups)
				if (C.claim[static_cast<std::size_t>(k)] == gid)
					return -1; // an ally is on it
	float value = 0, hp_total = 0;
	for (int gid : isl.groups)
	{
		const Group& g = W.groups[static_cast<std::size_t>(gid)];
		if (g.st == ST_RESPAWN && g.ready_round - round > 30)
			continue;
		value += static_cast<float>(g.gems) + P.gold_value * static_cast<float>(g.gold);
		hp_total += g.st == ST_REWARD ? 0.f : g.hp_total;
	}
	if (value <= 0)
		return -1;
	const int to_launch = isl.to_launch.get(pos);
	if (to_launch >= BIG)
		return -1;
	const float time = static_cast<float>(to_launch) + 4.f + hp_total / std::max(10.f, camp_dps()) +
		6.f * static_cast<float>(isl.groups.size()) + 6.f;
	return value / time;
}

bool Brain::island_task(int i)
{
	auto& W = world();
	Island& isl = W.islands[static_cast<std::size_t>(i)];
	auto& me = bc::self();
	std::uint32_t crystals = 0;
	try
	{
		crystals = me.consumables()[bc::consumable_type::tp_crystal].count();
	}
	catch (...)
	{
	}
	if (crystals == 0)
		return false;
	tp_island = i;
	task = T_FARM;
	task_group = isl.groups.front();
	if (pos != isl.launch)
	{
		bc::bitboard goal;
		goal.set(isl.launch);
		after_move(Nav::step_field(pos, isl.to_launch, 0, &danger, kit.dash, can_move, goal));
		if (pos != isl.launch)
			return true;
	}
	try
	{
		me.consumables()[bc::consumable_type::tp_crystal].use(isl.land);
	}
	catch (...)
	{
	}
	tp_island = -1; // the hop is under way (or failed): re-plan from the island score next time
	return true;
}

void Brain::prepare_scoring()
{
	// Values group_score needs that do not depend on the group: computed once per turn.
	auto& W = world();
	int alive_enemies = 0;
	sc_recent_n = 0;
	for (const auto& e : W.enemies)
	{
		alive_enemies += e.alive;
		if (e.alive && e.seen_round >= 0 && round - e.seen_round <= 8 && sc_recent_n < static_cast<int>(sc_recent.size()))
			sc_recent[static_cast<std::size_t>(sc_recent_n++)] = { e.pos, e.hp, e.str + e.focus * best_mod(e.kit) / 8.f + e.burst() / 3.f };
	}
	sc_risk = static_cast<float>(alive_enemies) / std::max<std::size_t>(1, W.enemies.size());
	sc_alert = !alert_zone.is_empty();
}

void Brain::farm()
{
	auto& W = world();
	if (P.style == 1 || round < P.deathball_until)
	{
		int leader = -1;
		for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
			if (W.allies[static_cast<std::size_t>(i)].alive)
			{
				leader = i;
				break;
			}
		auto& C = comms();
		if (leader == W.my_index)
			C.post(AL_RALLY, pos, round);
		else if (leader >= 0)
		{
			const int lg = C.claim[static_cast<std::size_t>(leader)];
			const bool leader_far = C.alert_kind == AL_RALLY && cheb(C.alert_pos, pos) > 4;
			if (leader_far || lg < 0)
			{
				task = T_WAIT;
				bc::bitboard goal;
				goal.draw_chebyshev(C.alert_pos, 2.f);
				step(goal, true, true);
				return;
			}
			Group& g = W.groups[static_cast<std::size_t>(lg)];
			task_group = lg;
			task = g.st == ST_REWARD ? T_WAIT : T_FARM;
			if (g.st == ST_REWARD)
				wait_group(g); // one body captures
			else
				farm_group(g);
			return;
		}
	}
	int best = -1, best_eta = BIG;
	bool best_pair = false;
	float best_s = 0;
	prepare_scoring();
	{
		// Score the current target first, then groups near us, then the rest while fuel lasts: on a
		// 48-group map scoring everything every turn cost ~55k and turns spilled into the next round.
		auto consider = [&](Group& g) {
			if (blacklist[static_cast<std::size_t>(g.id)] > round)
				return;
			int eta = 0;
			bool np = false;
			float s = group_score(g, eta, &np);
			if (s <= 0)
				return;
			if (g.id == task_group)
				s *= P.hysteresis;
			if (s > best_s)
				best_s = s, best = g.id, best_eta = eta, best_pair = np;
		};
		if (task_group >= 0 && task_group < static_cast<int>(W.groups.size()))
			consider(W.groups[static_cast<std::size_t>(task_group)]);
		for (int pass = 0; pass < 2; ++pass)
			for (auto& g : W.groups)
			{
				if (g.id == task_group || (cheb(g.center, pos) <= P.score_near) != (pass == 0))
					continue;
				if (pass == 1 && bc::fuel_remaining() < P.score_fuel_floor)
					break;
				consider(g);
			}
	}
	// Islands: from near home, compare a crystal trip with the best walking target.
	if (!W.islands.empty() && !inside_island() && W.dist_home(pos) <= 4)
	{
		int bi = -1;
		float bs = best_s;
		for (int i = 0; i < static_cast<int>(W.islands.size()); ++i)
		{
			const float s = island_score(i);
			if (s > bs)
				bs = s, bi = i;
		}
		if (bi >= 0 && island_task(bi))
			return;
	}
	if (tp_island >= 0 && !inside_island() && W.dist_home(pos) > 4)
	{
		// Mid-way to the launch tile: keep going.
		if (island_task(tp_island))
			return;
	}
	// Crystal shortcuts over hole mazes: from near home, a hop can beat a long walk around.
	if (tp_hop >= 0)
	{
		if (round - tp_hop_since > 40)
			tp_hop = -1;
		else if (hop_task(tp_hop))
			return;
	}
	if (W.dist_home(pos) <= 4 && !inside_island())
	{
		const bool crystal = has_crystal() || (W.ally_spawn.is_set(pos) && gold >= 10);
		if (crystal)
		{
			int bh = -1;
			float bs = best_s;
			for (auto& g : W.groups)
			{
				const auto& h = W.hops[static_cast<std::size_t>(g.id)];
				if (!h.valid || blacklist[static_cast<std::size_t>(g.id)] > round)
					continue;
				int eta = 0;
				const float sc = group_score(g, eta, nullptr, h.cost + W.dist_home(pos));
				if (sc > bs * 1.1f)
					bs = sc, bh = g.id;
			}
			if (bh >= 0)
			{
				tp_hop = bh;
				tp_hop_since = round;
				task_group = bh;
				if (hop_task(bh))
					return;
			}
		}
	}
	if (inside_island() && best < 0)
	{
		// Island cleared or respawning: recall out (keeps the bag) once nothing can hit us.
		tp_island = -1;
		if (!in_awake_camp_range() && !danger.is_set(pos))
		{
			try
			{
				bc::self().recall();
				task = T_HOME;
				return;
			}
			catch (...)
			{
			}
		}
	}
	if (best < 0)
	{
		// Nothing worth doing: wait near the soonest respawn on our half, else hold near home.
		int soon = -1, soon_t = BIG;
		for (auto& g : W.groups)
			if (g.st == ST_RESPAWN && g.ours && g.ready_round - round < soon_t)
				soon_t = g.ready_round - round, soon = g.id;
		task = T_WAIT;
		// Nothing to farm: top up at home (heal and shop) rather than stand around hurt or rich.
		const bool shopper = type != CT::tavi && build_idx < build.size();
		if (!W.ally_spawn.is_set(pos) && (hp < 0.9f * max_hp || (shopper && gold >= 60)))
		{
			go_home();
			return;
		}
		if (soon >= 0)
		{
			task_group = soon;
			wait_group(W.groups[static_cast<std::size_t>(soon)]);
			return;
		}
		// Else go where an ally is farming: backup, and a share of its pack.
		auto& C = comms();
		int help = -1, help_d = BIG;
		for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
		{
			const int cg = C.claim[static_cast<std::size_t>(i)];
			if (i == W.my_index || cg < 0 || cg >= static_cast<int>(W.groups.size()) || !W.allies[static_cast<std::size_t>(i)].alive)
				continue;
			const int dd = cheb(W.groups[static_cast<std::size_t>(cg)].center, pos);
			if (dd < help_d)
				help_d = dd, help = cg;
		}
		if (help >= 0 && help_d > 3)
			go_group(W.groups[static_cast<std::size_t>(help)], 3, true);
		return;
	}
#ifdef LEGEND_TRACE
	debug_block({
		if (round % 50 == 0 && W.my_index == 0)
			for (auto& g : W.groups)
			{
				int eta = 0;
				const float sc = group_score(g, eta);
				std::printf("S r=%d g=%d ours=%d st=%d gems=%d elk=%d hp=%.0f d=%d ready=%d score=%.3f\n", round, g.id, (int)g.ours, (int)g.st, g.gems, (int)g.elk, g.hp_total, eta, g.ready_round - round, sc);
			}
	});
#endif
	if (best != task_group)
	{
		task_group = best;
		task_since = round;
	}
	// Give up on targets we cannot reach in reasonable time.
	if (round - task_since > 2 * best_eta + 60)
	{
		blacklist[static_cast<std::size_t>(best)] = round + 40;
		task_group = -1;
		return;
	}
	Group& g = W.groups[static_cast<std::size_t>(best)];
	if (best_pair && g.st != ST_REWARD)
	{
		// Pair plan: hold just outside camp range until a partner claims it too (then group_score sees a
		// claimer and both farm it); give up after pair_wait_max rounds.
		if (pair_group != g.id)
			pair_group = g.id, pair_since = round;
		if (round - pair_since > P.pair_wait_max)
		{
			blacklist[static_cast<std::size_t>(g.id)] = round + 30;
			pair_group = -1;
			task_group = -1;
			return;
		}
		task = T_WAIT;
		go_group(g, 4, true);
		return;
	}
	pair_group = -1;
	switch (g.st)
	{
	case ST_REWARD: task = T_CAPTURE; capture_group(g); break;
	case ST_RESPAWN:
		task = T_WAIT;
		if (g.ready_round - round > 0)
			wait_group(g);
		else
			farm_group(g);
		break;
	default: task = T_FARM; farm_group(g); break;
	}
}

bool Brain::wait_group(Group& g)
{
	// Stand next to (never on) the spawn tiles: an occupied spawn tile delays the respawn.
	if (g.mask.is_set(pos))
	{
		bc::bitboard ring;
		for (auto t : g.tiles)
			ring.draw_chebyshev(t, 1.f);
		ring &= ~g.mask;
		return step(ring, false, false);
	}
	return go_group(g, 1, true);
}

bool Brain::capture_group(Group& g)
{
	if (g.mask.is_set(pos))
	{
		if (capture_group_id != g.id)
			capture_group_id = g.id, capture_since = round;
		// Recall while capturing: started one turn after stepping on the tile, the teleport lands as the
		// capture completes, so we arrive home with the reward, healed, ready to shop and bank near spawn.
		// Strong ladder teams do this after almost every capture far from home.
		// Capture lands at the start of round since + capture_time + 1; a recall started in round R lands at
		// R + recall_time. Start it so both land together (never earlier: an early teleport loses the reward).
		const int recall_t = static_cast<int>(bc::constants::recall_time) - (has_home ? 2 : 0);
		const int start_at = capture_since + static_cast<int>(bc::constants::capture_time) + 1 - recall_t;
		if (round >= std::max(capture_since + 1, start_at) && W_dist_home_ok() && safe_to_recall())
		{
			const bool shopper = type != CT::tavi && build_idx < build.size();
			const bool rich = shopper && gold + static_cast<std::uint32_t>(g.gold) >= static_cast<std::uint32_t>(P.cap_recall_gold);
			const bool hurt = hp < P.cap_recall_hp * max_hp;
			const bool bag = static_cast<int>(gems) + g.gems >= tribute_min;
			if (rich || hurt || bag)
			{
				try
				{
					bc::self().recall();
					task = T_CAPTURE;
					return true;
				}
				catch (...)
				{
				}
			}
		}
		place_ward(round - ward_round > 4);
		return true;
	}
	capture_group_id = -1;
	const bool mv = go_group(g, 0, true);
	if (g.mask.is_set(pos))
		capture_group_id = g.id, capture_since = round; // the capture starts in the turn we step on
	return mv;
}

bool Brain::W_dist_home_ok() const { return world().dist_home(pos) > P.cap_recall_min_home && world().dist_home(pos) < BIG; }

bool Brain::spells_on_camp(Group& g, std::size_t idx, bool save_cc)
{
	const auto& c = g.camps[idx];
	const int d = cheb(pos, c.pos);
	if (kit.aoe >= 0 && d <= static_cast<int>(kit.aoe_range) && (!kit.aoe_stuns || !save_cc) && ready(kit.aoe))
	{
		// Centre the blast on the camp with the most live neighbours.
		vec2 best = c.pos;
		int best_n = -1;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (g.hp[i] <= 0 || cheb(pos, g.camps[i].pos) > static_cast<int>(kit.aoe_range))
				continue;
			int n = 0;
			for (std::size_t j = 0; j < g.camps.size(); ++j)
				n += g.hp[j] > 0 && cheb(g.camps[i].pos, g.camps[j].pos) <= 1;
			if (n > best_n)
				best_n = n, best = g.camps[i].pos;
		}
		if (best_n >= 2 || kit.dmg < 0 || !ready(kit.dmg))
			if (cast_ground(kit.aoe, best))
				return true;
	}
	if (kit.dmg >= 0 && d <= static_cast<int>(kit.dmg_range) && cast_unit_camp(kit.dmg, c.camp))
		return true;
	if (kit.cc >= 0 && d <= static_cast<int>(kit.cc_range) && !save_cc && (kit.cc_mod > 0 || g.awake) && cast_unit_camp(kit.cc, c.camp))
		return true;
	return false;
}

bool Brain::attack_chain_camp(Group& g, std::size_t idx)
{
	auto& W = world();
	if (!attack_unit(g.camps[idx].camp))
		return false;
	// Second swing with an attack reset; retarget if the first swing killed it.
	if (kit.reset >= 0 && ready(kit.reset))
	{
		std::size_t target = idx;
		bc::detail::camp_state cs{};
		const bool dead = bc::detail::sdk_camp(handle_of(g.camps[idx].camp), &cs) != 0 || cs.health <= 0;
		if (dead)
		{
			target = g.camps.size();
			for (std::size_t i = 0; i < g.camps.size(); ++i)
				if (i != idx && g.hp[i] > 0 && W.camp_occ.is_set(g.camps[i].pos) && cheb(pos, g.camps[i].pos) <= kit.attack_range)
					target = i;
			// Vendetta's kill reset makes this free; others keep the reset for later.
			if (target == g.camps.size())
				return true;
		}
		if (cast_self(kit.reset))
			attack_unit(g.camps[target].camp);
	}
	return true;
}

bool Brain::farm_group(Group& g)
{
	auto& W = world();
	// Choose among live, visible camps in attack range: lowest health first (Varg: most neighbours for splash).
	auto pick = [&](int range) {
		std::size_t best = g.camps.size();
		float best_key = 1e30f;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (g.hp[i] <= 0 || !W.camp_occ.is_set(g.camps[i].pos) || cheb(pos, g.camps[i].pos) > range)
				continue;
			float key = g.hp[i];
			if (type == CT::varg)
				for (std::size_t j = 0; j < g.camps.size(); ++j)
					if (j != i && g.hp[j] > 0 && cheb(g.camps[i].pos, g.camps[j].pos) <= 1)
						key -= 600.f;
			if (key < best_key)
				best_key = key, best = i;
		}
		return best;
	};
	const bool save_cc = enemy_near;
	const bool hold_spells = enemy_near && P.hold_spells_near_enemies; // keep burst for the fight that is coming
	std::size_t t = pick(kit.attack_range);
	if (t == g.camps.size())
	{
		// The group field is rooted at every spawn tile, dead camps included; once we are "there" by the field,
		// close the last gap toward the live camps with a direct search.
		const auto& gf = nav().group_fields[static_cast<std::size_t>(g.id)];
		if (gf.ready && gf.get(pos) <= kit.attack_range)
		{
			bc::bitboard goal;
			for (std::size_t i = 0; i < g.camps.size(); ++i)
				if (g.hp[i] > 0 && W.camp_occ.is_set(g.camps[i].pos))
					goal.draw_chebyshev(g.camps[i].pos, static_cast<float>(kit.attack_range));
			goal &= ~g.mask;
			if (!goal.is_empty())
				step(goal, false, true);
		}
		else
			go_group(g, kit.attack_range, true);
		t = pick(kit.attack_range);
		if (t == g.camps.size())
		{
			// Still out of attack range: if we are pinned in place this turn, use a range-4 spell.
			if (!can_move && !cast_done)
			{
				const std::size_t s4 = pick(4);
				if (s4 < g.camps.size() && !hold_spells)
					spells_on_camp(g, s4, save_cc);
			}
			return true;
		}
		// Melee can still swing after walking; ranged only after a dash (walking spends the attack).
		attack_chain_camp(g, t);
		return true;
	}
	if (!hold_spells)
		spells_on_camp(g, t, save_cc);
	attack_chain_camp(g, t);
	return true;
}
