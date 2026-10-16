#include "brain.h"

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

// Shard plans: five shards of a family complete its emblem; only the emblem grants the passive.
std::vector<I> build_for(CT t)
{
	std::vector<I> v;
	switch (t)
	{
	case CT::vendetta:
	case CT::varg:
	case CT::ren:
	case CT::issac:
		rep(v, I::jungle_shard_of_strength, 5);
		if (P.health_emblem)
			rep(v, I::durability_shard_of_health, 5);
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
		if (P.health_emblem)
			rep(v, I::durability_shard_of_health, 5);
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
		if (P.health_emblem)
			rep(v, I::durability_shard_of_health, 5);
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
	// Stunners act first within our team so their stun lands before allies (and later enemies) act;
	// healers act last so they see the damage of the round. Takes effect from the next round.
	try
	{
		const int prio = (kit.cc >= 0 || kit.aoe_stuns) ? 30 : (kit.heal >= 0 ? 5 : 20);
		bc::self().set_priority(prio);
	}
	catch (...)
	{
	}
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
	bc::detail::sdk_champion_gems(self, &gems);
	bc::detail::sdk_champion_gold(self, &gold);
}

void Brain::turn()
{
	round = static_cast<int>(bc::round_number());
	auto& W = world();
	W.round = round;
	if (!inited)
		init();
	read_self();
	learner().team_update(round);
	auto& C = comms();
	if (!alive)
	{
		shop();
		C.read(round);
		C.write_self(W.my_index, -1, false);
		task = T_NONE;
		return;
	}
	if (hp < last_hp - 0.5f)
		last_hit_round = round;
	W.perceive(pos);
	C.read(round);
	build_danger();
	if (round - 1 == last_turn_round)
		learn_observe();
	else
		cal_round = -1;
	last_turn_round = round;
	camp_in_prev = camp_in;

	if (flag(state, bc::champion_state::recalling) || flag(state, bc::champion_state::submitting_gems) ||
		flag(state, bc::champion_state::teleporting))
	{
		handle_channel();
		last_hp = hp;
		return;
	}

	shop();
	nav().new_turn();
	update_mode();

	support_spells();
	use_locks();

	bool acted = false;
	const bool bag_wins = bc::global_submitted_gems(team::ally) + gems >= bc::constants::winning_gems;
	if (((static_cast<int>(gems) >= P.bank_first && enemy_near) || (bag_wins && gems > 0)) && !danger.is_set(pos) && !in_awake_camp_range())
	{
		int ad = BIG;
		if (nearest_altar(ad) >= 0 && ad <= P.bank_first_dist)
			acted = tribute(true);
	}
	if (!acted)
		acted = combat();
	if (!acted)
		acted = safety();
	if (!acted)
		acted = tribute(false);
	if (!acted)
		acted = shop_trip();
	if (!acted)
		acted = respond_to_alert();
	if (!acted)
		farm();

	chip_passing();
	place_ward(false);
	prebuild_fields();
#ifdef LEGEND_TRACE
	debug_block({
		std::printf("T r=%d %d task=%d g=%d pos=(%d,%d) hp=%.0f gems=%u gold=%u fuel=%llu\n", round, static_cast<int>(type), task, task_group, pos.x, pos.y, hp, gems, gold,
			static_cast<unsigned long long>(bc::fuel_remaining()));
	});
#endif
	const bool help = task == T_FIGHT && hp < 0.6f * max_hp;
	C.write_self(W.my_index, (task == T_FARM || task == T_CAPTURE || task == T_WAIT) ? task_group : -1, help);
	last_hp = hp;
}

// Score last turn's calibration sample and attribute champion damage we took to the enemies around us.
void Brain::learn_observe()
{
	auto& L = learner();
	auto& W = world();
	if (cal_round == round - 1 && cal_group >= 0)
	{
		const Group& g = W.groups[static_cast<std::size_t>(cal_group)];
		if (!enemy_near)
		{
			L.sample_out(std::max(0.f, cal_ghp - (g.st == ST_ALIVE ? g.hp_total : 0.f)), cal_pred_out);
			if (cal_pred_in > 0)
				L.sample_in(std::max(0.f, last_hp - hp), cal_pred_in);
		}
	}
	cal_round = -1;
	const float took = last_hp - hp - camp_in_prev;
	if (took > 30.f)
	{
		int who = -1;
		float best = -1;
		for (std::size_t i = 0; i < W.enemies.size(); ++i)
		{
			const auto& e = W.enemies[i];
			if (!e.visible || cheb(e.pos, pos) > 5)
				continue;
			const float threat = e.str + e.focus * best_mod(e.kit);
			if (threat > best)
				best = threat, who = static_cast<int>(i);
		}
		if (who >= 0 && static_cast<std::size_t>(who) < L.enemy_burst.size())
			L.enemy_burst[static_cast<std::size_t>(who)] = std::max(L.enemy_burst[static_cast<std::size_t>(who)], took);
	}
}

void Brain::handle_channel()
{
	// Recall is broken by damage anyway; tribute survives damage but not stuns. Cancel a tribute only if
	// a visible enemy can stun or kill us before it completes and we carry a big bag.
	auto& me = bc::self();
	if (flag(state, bc::champion_state::submitting_gems) && gems >= 30)
	{
		for (const auto& e : world().enemies)
			if (e.visible && e.alive && cheb(e.pos, pos) <= 2 && e.str * 3 >= hp)
			{
				try
				{
					me.cancel_submit_gems();
				}
				catch (...)
				{
				}
				return;
			}
	}
	auto& C = comms();
	C.write_self(world().my_index, task_group, false);
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
	if ((on_spawn || !alive) && !W.islands.empty() && gold >= 10)
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
		// A spell coming off cooldown next turn is as good as up: we only move once before it acts.
		auto up = [&](int slot) { return slot >= 0 && (!fresh || e.cd[static_cast<std::size_t>(slot)] <= P.danger_cd_slack); };
		const bool dash_up = up(e.kit.dash);
		const bool spell_up = up(e.kit.dmg) || up(e.kit.cc) || up(e.kit.aoe);
		const bool walk_cast = (up(e.kit.dmg) && !e.kit.dmg_excl) || (up(e.kit.cc) && !e.kit.cc_excl) || (up(e.kit.aoe) && !e.kit.aoe_excl);
		int reach = e.kit.attack_range + (e.kit.ranged ? 0 : 1) + (dash_up ? 2 : 0);
		if (spell_up)
			reach = std::max(reach, 4 + (P.danger_walk_cast && walk_cast ? 1 : 0));
		reach += age;
		danger.draw_chebyshev(e.pos, static_cast<float>(reach));
		if (cheb(e.pos, pos) <= 9)
			enemy_near = true;
	}
	camp_in = 0;
	for (const auto& g : W.groups)
		if (g.st == ST_ALIVE && g.awake && g.hp_total > 0 && !g.harmless && cheb(g.center, pos) <= 10)
		{
			camp_danger |= g.near;
			if (g.near.is_set(pos))
				for (std::size_t i = 0; i < g.camps.size(); ++i)
					if (g.hp[i] > 0 && cheb(g.camps[i].pos, pos) <= 3)
						camp_in += g.camps[i].str;
		}
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
	// Spend leftover fuel building fields for the nearest groups we have not mapped yet.
	auto& W = world();
	auto& N = nav();
	for (int k = 0; k < 2 && bc::fuel_remaining() > 60000; ++k)
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
	std::vector<Enemy*> E;
	for (auto& e : W.enemies)
		if (e.alive && e.visible && cheb(e.pos, pos) <= 8)
			E.push_back(&e);
	if (E.empty())
		return false;

	float their_hp = 0, their_dps = 0;
	auto& L = learner();
	float lethal = 0; // largest burst a nearby enemy has shown us and has ready now
	for (auto* e : E)
	{
		their_hp += e->hp;
		// Sustained damage plus whatever burst is actually off cooldown right now; a burst it has already
		// landed on us (items included) replaces the model when its spells are up.
		float b = e->burst();
		const std::size_t ei = static_cast<std::size_t>(e - W.enemies.data());
		const bool up = e->ready(e->kit.dmg) || e->ready(e->kit.cc) || e->ready(e->kit.aoe);
		if (up && ei < L.enemy_burst.size())
		{
			b = std::max(b, L.enemy_burst[ei]);
			if (cheb(e->pos, pos) <= 5)
				lethal = std::max(lethal, L.enemy_burst[ei]);
		}
		their_dps += e->str + e->focus * best_mod(e->kit) / 8.f + b / 3.f;
	}
	their_dps += camp_in;
	float my_burst = 0;
	if (ready(kit.dmg)) my_burst = std::max(my_burst, focus * kit.dmg_mod);
	if (ready(kit.cc)) my_burst = std::max(my_burst, focus * kit.cc_mod);
	if (ready(kit.aoe)) my_burst = std::max(my_burst, focus * kit.aoe_mod);
	if (ready(kit.reset)) my_burst = std::max(my_burst, str);
	float our_hp = hp, our_dps = str + focus * best_mod(kit) / 8.f + my_burst / 3.f;
	int allies_near = 0;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 5)
		{
			our_hp += a.hp;
			our_dps += a.str * 1.2f;
			++allies_near;
		}
	const float t_kill_them = their_hp / std::max(1.f, our_dps);
	const float t_kill_us = our_hp / std::max(1.f, their_dps);
	const float adv = t_kill_us / std::max(0.1f, t_kill_them);

	// Team-consistent focus target: allies seeing the same fight pick the same enemy (no distance term).
	const int my_reach = kit.attack_range + (kit.ranged ? 0 : 1) + (ready(kit.dash) ? 2 : 0);
	Enemy* tgt = nullptr;
	float best = -1;
	for (auto* e : E)
	{
		if (cheb(pos, e->pos) > std::max(my_reach, 4) + 2)
			continue;
		const float v = (60.f + static_cast<float>(e->gems) + (e->channeling ? 60.f : 0.f)) / std::max(50.f, e->hp);
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
		tgt->hp <= burst_vs(*tgt) + 45.f * static_cast<float>(allies_near);
	const bool in_reach = danger.is_set(pos);

	// Can we actually get away? Melee enemies move and hit in one turn; ranged ones must stop to shoot.
	bool chased_by_melee = false;
	for (auto* e : E)
		if (!e->kit.ranged && cheb(pos, e->pos) <= 3 + (e->ready(e->kit.dash) ? 2 : 0))
			chased_by_melee = true;
	const bool can_escape = !chased_by_melee || ready(kit.dash);

	bool fight = false;
	if (killable && adv >= 0.5f)
		fight = true;
	else if (adv >= fight_margin)
		fight = true;
	else if (in_reach && adv >= fight_back_margin)
		fight = true;
	else if (in_reach && !can_escape && adv >= P.cornered_margin)
		fight = true;
	else if (tgt->channeling && adv >= 0.9f)
		fight = true;
	const bool cornered = in_reach && !can_escape;
#ifndef LG_NO_ADAPT
	// It has shown it can kill us from here: leave unless the kill is ours first.
	if (fight && !killable && !cornered && lethal >= hp)
		fight = false;
#endif
	if (fight && !killable && !cornered && (hp < 0.25f * max_hp || (static_cast<int>(gems) >= P.bag_caution && adv < 1.5f)))
		fight = false;
	// Do not dive their spawn: it heals them and they block us.
	if (W.enemy_spawn.is_set(tgt->pos) || cheb(tgt->pos, W.enemy_spawn_c) <= 3)
		fight = fight && killable;

	// Early warning: an outnumbering group is visible; allies keep away from it.
	if (!fight && E.size() >= 3 && adv < 1.f)
		comms().post(AL_DANGER, tgt->pos, round);
	if (fight)
	{
		comms().post(AL_RALLY, tgt->pos, round);
		task = T_FIGHT;
		return engage(*tgt);
	}
	if (in_reach)
	{
		comms().post(AL_DANGER, tgt->pos, round);
		task = T_FLEE;
		if (go_home_step(true))
			return true;
		return engage(*tgt); // cornered: hit back
	}
	return false;
}

bool Brain::engage(Enemy& e)
{
	if (!e.ch)
		return false;
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
	if (dh > 5 && !in_awake_camp_range() && !danger.is_set(pos))
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

bool Brain::safety()
{
	const float threshold = std::max(P.retreat_hp * max_hp, camp_in * 4.f);
	if (hp < threshold && camp_in <= 0 && !danger.is_set(pos) && !enemy_near && task == T_CAPTURE && task_group >= 0 &&
		world().groups[static_cast<std::size_t>(task_group)].st == ST_REWARD && nav().group_dist(world().groups[static_cast<std::size_t>(task_group)], pos) <= 3)
		return false; // a cleared group is ours only once we stand on it
	if (hp >= threshold)
	{
		if (task == T_HOME && world().ally_spawn.is_set(pos) && hp < max_hp)
			return true; // finish healing on spawn
		return false;
	}
	if (in_awake_camp_range())
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
	const int ours = static_cast<int>(bc::global_submitted_gems(team::ally));
	const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
	// Near the end only banked gems count: bank smaller bags the closer either team is to winning.
	const int top = std::max(ours, theirs);
	const int goal = static_cast<int>(bc::constants::winning_gems);
	if (top >= goal - P.endgame_bank_at)
		tribute_min = std::max(1, std::min(tribute_min, tribute_min * (goal - top) / std::max(1, P.endgame_bank_at)));
#ifndef LG_NO_ADAPT
	{
		// Learned fight record: losing exchanges → engage less and stay off their half; winning → press.
		auto& L = learner();
		const float p = L.fight_p();
		const float caution = std::clamp(1.f + (0.5f - p) * P.learn_fight, 0.8f, 1.4f);
		fight_margin *= caution;
		enemy_half_penalty *= caution * caution;
		deny_bonus *= std::clamp(2.f * p, 0.5f, 1.4f);
		// Learned race: projected finish rounds at both teams' current banking pace.
		if (round > P.race_after)
		{
			const int eo = L.eta_ours(), et = L.eta_theirs();
			if (et < BIG && static_cast<float>(et) < P.race_ratio * static_cast<float>(eo))
			{
				// Losing the race: farming harder will not catch up, take their gems.
				deny_bonus += 0.4f;
				enemy_half_penalty *= 0.6f;
			}
			else if (eo < BIG && static_cast<float>(eo) < P.race_ratio * static_cast<float>(et))
				fight_margin += 0.15f; // winning the race: no need for even fights
		}
	}
#endif
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
	if (inside_island())
	{
		// No altar inside an island: recall out (the bag is kept) once it is worth banking, then walk to an altar.
		const bool wins = bc::global_submitted_gems(team::ally) + gems >= bc::constants::winning_gems;
		const bool late = round >= static_cast<int>(bc::constants::max_rounds) - 150;
		if ((force || wins || late || static_cast<int>(gems) >= P.island_bank) && !in_awake_camp_range() && !danger.is_set(pos))
		{
			try
			{
				bc::self().recall();
				task = T_HOME;
				tp_island = -1;
				return true;
			}
			catch (...)
			{
			}
		}
		return false;
	}
	int dist = BIG;
	const int a = nearest_altar(dist);
	if (a < 0 || dist >= BIG)
		return false;
	const int ticks = static_cast<int>((gems + 9) / 10);
	const bool endgame = round + dist + ticks + P.endgame_margin >= static_cast<int>(bc::constants::max_rounds);
	const bool winning = bc::global_submitted_gems(team::ally) + gems >= bc::constants::winning_gems;
	const bool risky = enemy_near && static_cast<int>(gems) >= P.tribute_risky;
	const bool want = force || endgame || winning || risky || static_cast<int>(gems) >= tribute_min || dist <= P.tribute_near ||
		(static_cast<int>(gems) >= 10 && on_the_way(a));
	if (!want)
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
	// A big purse is a big power spike: recall for it when nothing can interrupt the channel.
	if (static_cast<int>(gold) >= P.recall_shop_gold && task != T_CAPTURE && !enemy_near && !in_awake_camp_range() && !danger.is_set(pos) &&
		static_cast<int>(gems) < tribute_min && !inside_island() && tp_island < 0)
		return go_home();
	const bool hurt_and_rich = gold >= 90 && hp < 0.6f * max_hp && dh <= P.shop_trip_max;
	if (!rich && !hurt_and_rich)
		return false;
	if (task == T_CAPTURE)
		return false;
	return go_home();
}

bool Brain::respond_to_alert()
{
	auto& C = comms();
	if (!C.fresh(round, 6) || (C.alert_kind != AL_RALLY && C.alert_kind != AL_OPPORTUNITY))
		return false;
	if (hp < 0.6f * max_hp || task == T_CAPTURE)
		return false;
	const int d = cheb(C.alert_pos, pos);
	if (d > 9 || d < 2)
		return false;
	task = T_FIGHT;
	bc::bitboard goal;
	goal.draw_chebyshev(C.alert_pos, static_cast<float>(kit.attack_range));
	return step(goal, false, true);
}

// ---------------------------------------------------------------------------------------------- farming

// Damage per round we deal to the group: splash (Varg) and area spells hit every live camp within radius 1 of
// the best target, single spells hit one, Ren retaliates against every camp that hits him.
float Brain::dps_vs_group(const Group& g) const { return dps_vs_group_raw(g) * learner().k_out(); }

float Brain::dps_vs_group_raw(const Group& g) const
{
	const bool fresh = g.st != ST_ALIVE; // respawning/unknown: assume every camp is back
	int live = 0, cluster = 1;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
	{
		if (!fresh && g.hp[i] <= 0)
			continue;
		++live;
		int n = 1;
		for (std::size_t j = 0; j < g.camps.size(); ++j)
			if (j != i && (fresh || g.hp[j] > 0) && cheb(g.camps[i].pos, g.camps[j].pos) <= 1)
				++n;
		cluster = std::max(cluster, n);
	}
	float basic = str * (1.f + (kit.reset >= 0 ? 0.125f : 0.f));
	if (type == CT::varg)
		basic *= static_cast<float>(cluster);
	float spells = 0;
	if (kit.dmg >= 0)
		spells += focus * kit.dmg_mod;
	if (kit.cc >= 0)
		spells += focus * kit.cc_mod;
	if (kit.aoe >= 0)
		spells += focus * kit.aoe_mod * static_cast<float>(cluster);
	float retaliation = 0;
	if (type == CT::ren && !g.harmless)
		retaliation = 0.2f * focus * static_cast<float>(std::min(live, 3));
	return std::max(10.f, basic + spells / 8.f + retaliation);
}

// Camp damage per round we expect to absorb while killing the group, after our mitigation, shared with helpers.
// Camp damage per round after our own mitigation (jungle emblem, shield, stuns), before calibration.
float Brain::mitigated(float raw, int live) const
{
	const bool jungle = build_idx >= 5 && (build.front() == I::jungle_shard_of_strength || build.front() == I::jungle_shard_of_health);
	float per = raw * (jungle ? 0.7f : 1.f);
	if (kit.shield >= 0)
		per -= focus * kit.shield_mod / 8.f;
	if (kit.cc >= 0 || kit.aoe_stuns)
		per -= (raw / static_cast<float>(std::max(1, live))) / 8.f; // one stunned camp skips an attack every 8 rounds
	return std::max(0.f, per);
}

float Brain::incoming_per_round(const Group& g, int helpers) const
{
	if (g.harmless)
		return 0;
	float dps = 0;
	int live = 0;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
		if (g.st != ST_ALIVE || g.hp[i] > 0)
			dps += g.camps[i].str, ++live;
	// Camps die during the fight; splash kills a pack together, otherwise damage tapers off.
	const float decay = live <= 1 ? 1.f : (type == CT::varg ? 0.9f : 0.65f);
	float per = mitigated(dps * decay, live) * learner().k_in();
	if (helpers > 0)
		per /= static_cast<float>(1 + helpers) * (kit.ranged ? 2.f : 1.f); // a melee ally in front takes the hits
	return per;
}

// Spell damage per round from range 4, where camps (range 3) cannot answer. Every spell has an 8-round cooldown.
float Brain::kite_dps(const Group& g) const
{
	if (g.harmless)
		return 0;
	const bool fresh = g.st != ST_ALIVE;
	int cluster = 1;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
	{
		if (!fresh && g.hp[i] <= 0)
			continue;
		int n = 1;
		for (std::size_t j = 0; j < g.camps.size(); ++j)
			if (j != i && (fresh || g.hp[j] > 0) && cheb(g.camps[i].pos, g.camps[j].pos) <= static_cast<int>(kit.aoe_radius))
				++n;
		cluster = std::max(cluster, n);
	}
	float per8 = 0;
	if (kit.dmg >= 0 && kit.dmg_range >= 4)
		per8 += focus * kit.dmg_mod;
	if (kit.aoe >= 0 && kit.aoe_range >= 4)
		per8 += focus * kit.aoe_mod * static_cast<float>(cluster);
	if (kit.cc >= 0 && kit.cc_range >= 4)
		per8 += focus * kit.cc_mod;
	return per8 / 8.f;
}

float Brain::group_score(const Group& g, int& eta, bool relaxed, bool* kite) const
{
	auto& W = world();
	auto& C = comms();
	eta = BIG;
	if (kite)
		*kite = false;
	const int d_tile = nav().group_dist(g, pos);
	if (d_tile >= BIG)
		return -1;
	const int d_adj = std::max(0, d_tile - 1);

	// Claims by living allies. Conflicts resolve by body index: a group we already hold stays ours against
	// higher-index claimers (they yield to us), so every body's choice depends only on lower-index ones and
	// claims cannot oscillate between allies whose memories disagree.
	int claimers = 0;
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
		if (i != W.my_index && C.claim[static_cast<std::size_t>(i)] == g.id && W.allies[static_cast<std::size_t>(i)].alive)
		{
			if (i > W.my_index && g.id == task_group)
				continue;
			++claimers;
		}
	const bool heavy = g.max_hp >= P.heavy_hp || g.dps >= P.heavy_dps;

	float hp_left = 0;
	float time = 0;
	int wait = 0;
	switch (g.st)
	{
	case ST_REWARD:
		if (claimers)
			return -1; // one body captures
		eta = d_tile;
		time = static_cast<float>(eta) + 6.f;
		break;
	case ST_RESPAWN:
	{
		const int avail = g.ready_round - round;
		if (avail > d_adj + (relaxed ? 3 * P.max_wait : P.max_wait))
			return -1;
		wait = std::max(0, avail - d_adj);
		hp_left = g.max_hp;
		break;
	}
	default:
		hp_left = g.hp_total;
		break;
	}
	float share = 1.f;
	bool use_kite = false;
	if (g.st != ST_REWARD)
	{
		if (claimers && !heavy)
			return -1; // light groups take one body
		if (claimers >= 2)
			return -1;
		eta = d_adj;
		const float mine = dps_vs_group(g);
		const float team_dps = mine * static_cast<float>(1 + claimers);
		const float kill = hp_left / team_dps;
		bool walk_ok = true;
		float walk_time = static_cast<float>(d_adj + wait) + kill + 6.f;
		if (claimers)
			share = 0.5f * P.join_bonus; // we split the work, the team gets the whole reward sooner
		if (!g.harmless)
		{
			// Camps never heal, so a group too strong for one health bar is still farmable over several trips:
			// fight until the reserve, heal at spawn, come back. Charge each extra trip as a round trip home.
			const float per_round = incoming_per_round(g, claimers);
			const float taken = per_round * kill;
			const float burst = g.dps * 4.f / static_cast<float>(1 + claimers);
			const float reserve = std::max(P.camp_hp_reserve * max_hp, burst);
			const float budget_now = std::max(0.f, hp - reserve);
			const float budget_full = std::max(1.f, max_hp - reserve);
			if (budget_full < per_round * 6.f && !(relaxed && claimers))
				walk_ok = false; // cannot even survive a few rounds next to it
			const float extra = taken - budget_now;
			const int trips = extra > 0 ? static_cast<int>(std::ceil(extra / budget_full)) : 0;
			if (trips > (relaxed ? 3 * P.max_trips : P.max_trips))
				walk_ok = false;
			const int home_d = std::min(W.dist_home(g.center), 24);
			walk_time += static_cast<float>(trips) * (2.f * static_cast<float>(std::min(home_d, 6)) + 6.f + static_cast<float>(std::max(0, home_d - 6)));
			// Kiting: stand at range 4 and use spells only. No damage taken, no trips; an ally on the group adds its damage.
			const float kd = kite_dps(g);
			// Kiting only pays with real spell power (focus items) or when the group dies soon anyway.
			if (kd > 0 && kd >= P.kite_min_ratio * mine && hp_left / (kd + mine * static_cast<float>(claimers)) <= P.kite_max_kill)
			{
				const float k_team = kd + mine * static_cast<float>(claimers);
				const float k_time = static_cast<float>(std::max(0, d_tile - 4) + wait) + hp_left / k_team + 9.f;
				if (!walk_ok || k_time < walk_time)
				{
					walk_time = k_time;
					walk_ok = true;
					use_kite = true;
				}
			}
		}
		if (!walk_ok)
			return -1;
		time = walk_time;
	}

	float value = (static_cast<float>(g.gems) + P.gold_value * static_cast<float>(g.gold)) * share;
	const float gem_part = static_cast<float>(g.gems) * share;
	if (!g.ours)
	{
		int alive_enemies = 0;
		for (const auto& e : W.enemies)
			alive_enemies += e.alive;
		const float risk = static_cast<float>(alive_enemies) / std::max<std::size_t>(1, W.enemies.size());
		if (!relaxed && hp < P.steal_hp_frac * max_hp && risk > 0)
			return -1;
		if (P.deny_gems_only)
			value += deny_bonus * gem_part;
		else
			value *= 1.f + deny_bonus;
		time += enemy_half_penalty * risk;
		if (round - g.seen_round > 60)
			value *= P.unknown_discount;
	}
	if (round - g.enemy_round < 12)
		time += 12.f;
	if (alert_zone.is_set(g.center))
		time += 25.f;
	if (g.enemy_on_tile)
		value *= 0.5f;
	if (kite)
		*kite = use_kite;
	return value / std::max(1.f, time);
}

bool Brain::inside_island() const { return world().dist_home(pos) >= BIG; }

// Camps never heal: a spell that is up and would otherwise idle is free progress on a group we will farm later.
void Brain::chip_passing()
{
	if (cast_done || !can_cast || enemy_near || task == T_FIGHT || task == T_FLEE)
		return;
	const bool dmg_up = kit.dmg >= 0 && ready(kit.dmg) && kit.dmg_mod > 0 && (!kit.dmg_excl || can_move);
	const bool aoe_up = kit.aoe >= 0 && ready(kit.aoe) && kit.aoe_mod > 0 && (!kit.aoe_excl || can_move);
	if (!dmg_up && !aoe_up)
		return;
	auto& W = world();
	for (auto& g : W.groups)
	{
		if (g.st != ST_ALIVE || g.harmless || g.hp_total <= 0 || cheb(g.center, pos) > 6)
			continue;
		if (!g.ours && round - g.enemy_round < 30)
			continue; // do not finish camps for the enemy
		for (std::size_t i = 0; i < g.camps.size(); ++i)
			if (g.hp[i] > 0 && W.camp_occ.is_set(g.camps[i].pos) && cheb(pos, g.camps[i].pos) <= 4)
			{
				if (spells_on_camp(g, i, true))
					return;
			}
	}
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
		tp_island = -1;
	}
	return true;
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
	float best_s = 0;
	bool best_kite = false;
	for (auto& g : W.groups)
	{
		if (blacklist[static_cast<std::size_t>(g.id)] > round)
			continue;
		int eta = 0;
		bool k = false;
		float s = group_score(g, eta, false, &k);
		if (s <= 0)
			continue;
		if (g.id == task_group)
			s *= round < sticky_until ? 1000.f : P.hysteresis;
		if (s > best_s)
			best_s = s, best = g.id, best_eta = eta, best_kite = k;
	}
	// Never idle while something is farmable: relax the trip/wait/steal limits rather than stand still.
	if (best < 0)
		for (auto& g : W.groups)
		{
			if (blacklist[static_cast<std::size_t>(g.id)] > round)
				continue;
			int eta = 0;
			bool k = false;
			const float s = group_score(g, eta, true, &k);
			if (s > best_s)
				best_s = s, best = g.id, best_eta = eta, best_kite = k;
		}
	task_kite = best_kite;
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
		task_group = soon; // -1 when there is nothing to wait for: never broadcast a stale claim
		if (soon >= 0)
			wait_group(W.groups[static_cast<std::size_t>(soon)]);
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
		// Flip-flop guard: many target switches in a short window → commit to the current target for a while.
		switch_log[switch_pos++ % switch_log.size()] = round;
		int recent = 0;
		for (int r : switch_log)
			recent += round - r < 20;
		if (recent >= 6)
			sticky_until = round + 25;
		task_group = best;
		task_since = round;
		task_hp = W.groups[static_cast<std::size_t>(best)].hp_total;
		task_st = W.groups[static_cast<std::size_t>(best)].st;
	}
	{
		// Progress resets the give-up clock: big groups take several heal trips and are worth finishing.
		const Group& tg = W.groups[static_cast<std::size_t>(best)];
		// Only damage dealt or a state change is progress: standing near a group we cannot hit is not.
		if (tg.hp_total < task_hp - 1.f || tg.st != task_st)
			task_since = round;
		task_st = tg.st;
		task_hp = tg.hp_total;
	}
	// Give up on targets we cannot reach in reasonable time.
	if (round - task_since > 2 * best_eta + 60)
	{
		blacklist[static_cast<std::size_t>(best)] = round + 40;
		task_group = -1;
		return;
	}
	Group& g = W.groups[static_cast<std::size_t>(best)];
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
		place_ward(round - ward_round > 4);
		return true;
	}
	return go_group(g, 0, true);
}

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

// Stand at Chebyshev 4 from a live camp and out of range 3 of all of them; cast every damage spell that is up.
bool Brain::kite_group(Group& g)
{
	auto& W = world();
	const bool fresh = g.st != ST_ALIVE;
	bc::bitboard ring, inner;
	std::size_t target = g.camps.size();
	float target_key = 1e30f;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
	{
		if (!fresh && g.hp[i] <= 0)
			continue;
		ring.draw_chebyshev(g.camps[i].pos, 4.f);
		inner.draw_chebyshev(g.camps[i].pos, 3.f);
		const int d = cheb(pos, g.camps[i].pos);
		if (d <= 4 && W.camp_occ.is_set(g.camps[i].pos) && g.hp[i] < target_key)
			target_key = g.hp[i], target = i;
	}
	ring &= ~inner;
	ring &= ~W.walls;
	if (ring.is_empty())
		return farm_group(g);
	if (!ring.is_set(pos))
	{
		if (inner.is_set(pos))
		{
			// Too close (arrived from the wrong side or the group respawned around us): back out first.
			if (step(ring, true, false))
				return true;
		}
		else if (nav().group_dist(g, pos) > 6)
			go_group(g, 4, true);
		else
			step(ring, true, true);
		return true;
	}
	if (target < g.camps.size() && !cast_done)
		spells_on_camp(g, target, enemy_near);
	return true;
}

bool Brain::farm_group(Group& g)
{
	auto& W = world();
	if (task_kite)
		return kite_group(g);
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
			else
				go_group(g, 1, true); // in range by the field but no camp in sight (walls block vision): close in
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
				if (s4 < g.camps.size())
					spells_on_camp(g, s4, save_cc);
			}
			return true;
		}
		// Melee can still swing after walking; ranged only after a dash (walking spends the attack).
		if (attack_chain_camp(g, t))
			calibration_sample(g);
		return true;
	}
	spells_on_camp(g, t, save_cc);
	if (attack_chain_camp(g, t))
		calibration_sample(g);
	return true;
}

// Solo farming turn with nothing else around: what the model predicts for this round, checked next turn.
void Brain::calibration_sample(const Group& g)
{
	if (enemy_near)
		return;
	auto& W = world();
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 4)
			return;
	float raw = 0;
	int live = 0;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
		if (g.hp[i] > 0)
		{
			++live;
			if (cheb(g.camps[i].pos, pos) <= 3)
				raw += g.camps[i].str;
		}
	cal_round = round;
	cal_group = g.id;
	cal_ghp = g.hp_total;
	cal_pred_out = dps_vs_group_raw(g);
	cal_pred_in = mitigated(raw, live);
}
