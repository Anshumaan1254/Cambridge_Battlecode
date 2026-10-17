#include "brain.h"
#include "learn.h"

#include <cmath>
#include <cstdio>

// Prediction audit hooks: compiled only into XM_TRACE builds and run inside debug_block (fuel paused).
#ifdef XM_TRACE
#define XM(stmt) debug_block({ stmt; })
#else
#define XM(stmt) (void)0
#endif

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
			if (P.squishy_hp_first)
				rep(v, I::durability_shard_of_health, 5);
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
			if (P.squishy_hp_first)
				rep(v, I::durability_shard_of_health, 5);
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
	W.dash_kit = kit.dash >= 0;
	W.init_static();
	W.find_islands();
	W.init_units();
	blacklist.assign(W.groups.size(), -1);
	nav().init();
	learner().init(W.W, W.H);
	comms().bodies = static_cast<int>(W.allies.size());
	inited = true;
#ifdef LEGEND_TRACE
	// Route analysis (tools/analysis): the static camp-group table, printed once per team (fuel-free in debug).
	debug_block({
		if (W.my_index == 0)
		{
			std::printf("M w=%d h=%d spawn=(%d,%d) team=%d\n", W.W, W.H, W.ally_spawn_c.x, W.ally_spawn_c.y, static_cast<int>(bc::detail::sdk_my_team()));
			std::printf("O mode=%d share=%.2f groups=%d first=%d\n", static_cast<int>(W.obj_mode), W.obj_share, static_cast<int>(W.obj_groups.size()), W.obj_groups.empty() ? -1 : W.obj_groups[0]);
			for (const auto& g : W.groups)
			{
				std::printf("G id=%d gems=%d gold=%d respawn=%d ours=%d d_ally=%d hp=%.0f dps=%.0f tiles=", g.id, g.gems, g.gold, g.respawn, (int)g.ours, g.d_ally, g.max_hp, g.dps);
				for (auto t : g.tiles)
					std::printf("%d,%d;", t.x, t.y);
				std::printf("\n");
			}
		}
	});
#endif
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
		XM(xm_dead());
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
	XM(xm_pre());

	if (flag(state, bc::champion_state::recalling) || flag(state, bc::champion_state::submitting_gems) ||
		flag(state, bc::champion_state::teleporting))
	{
		handle_channel();
		read_self();
		if (flag(state, bc::champion_state::recalling) || flag(state, bc::champion_state::submitting_gems) ||
			flag(state, bc::champion_state::teleporting))
		{
			XM(xm_post());
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
		XM(xm_post());
		last_hp = hp;
		return;
	}

	dbg_path = 0, dbg_eng = 0, dbg_hit_other = false;
#ifdef SPELL_TRACE
	const vec2 pos0 = pos;
	const bool dmg_up0 = kit.dmg >= 0 && cd[static_cast<std::size_t>(kit.dmg)] <= 0, aoe_up0 = kit.aoe >= 0 && cd[static_cast<std::size_t>(kit.aoe)] <= 0;
#endif
	bool acted = combat();
	if (acted)
		dbg_path = task == T_FIGHT ? 1 : 2;
	if (!acted && (acted = safety()))
		dbg_path = 3;
	if (!acted && (acted = tribute(false)))
		dbg_path = 4;
	if (!acted && (acted = home_trip()))
		dbg_path = 5;
	if (!acted && (acted = shop_trip()))
		dbg_path = 6;
	if (!acted && (acted = respond_to_alert()))
		dbg_path = 7;
	if (!acted)
		farm(), dbg_path = 8;
#ifdef SPELL_TRACE
	debug_block({
		auto& WW = world();
		if ((dmg_up0 || aoe_up0) && !cast_done)
		{
			int cd4 = 99, live4 = 0;
			for (const auto& g : WW.groups)
				for (std::size_t k = 0; k < g.camps.size(); ++k)
					if (g.hp[k] > 0 && WW.camp_occ.is_set(g.camps[k].pos) && cheb(pos0, g.camps[k].pos) <= 4)
						cd4 = std::min(cd4, cheb(pos0, g.camps[k].pos)), ++live4;
			int tg4 = 99;
			if (task_group >= 0 && task_group < static_cast<int>(WW.groups.size()))
			{
				const auto& g = WW.groups[static_cast<std::size_t>(task_group)];
				for (std::size_t k = 0; k < g.camps.size(); ++k)
					if (g.hp[k] > 0 && WW.camp_occ.is_set(g.camps[k].pos))
						tg4 = std::min(tg4, cheb(pos0, g.camps[k].pos));
			}
			if (live4 > 0)
				std::printf("WM tg=%d r=%d ch=%d path=%d eng=%d task=%d cd4=%d live4=%d mv=%d enemy=%d\n", tg4, round, static_cast<int>(type), dbg_path, dbg_eng, task, cd4, live4, static_cast<int>(!can_move), enemy_near_d);
		}
		int nd = 99, nt = -1, nsp = 0;
		for (const auto& e : WW.enemies)
			if (e.alive && e.visible && cheb(e.pos, pos) < nd)
				nd = cheb(e.pos, pos), nt = static_cast<int>(e.type), nsp = WW.enemy_spawn.is_set(e.pos) ? 1 : 0;
		const bool spell_ready = (kit.dmg >= 0 && cd[static_cast<std::size_t>(kit.dmg)] <= 0) || (kit.cc >= 0 && cd[static_cast<std::size_t>(kit.cc)] <= 0) ||
			(kit.aoe >= 0 && cd[static_cast<std::size_t>(kit.aoe)] <= 0);
		if ((spell_ready && nd <= 4) || dbg_eng == 7 || dbg_eng == 17 || dbg_eng == 8 || dbg_hit_other)
			std::printf("SP r=%d ch=%d path=%d eng=%d task=%d nd=%d nt=%d nsp=%d cast=%d mv=%d atk=%d hp=%.0f/%.0f cd=%d,%d near=%d hito=%d\n", round, static_cast<int>(type), dbg_path, dbg_eng, task, nd, nt, nsp,
				static_cast<int>(cast_done), static_cast<int>(!can_move), static_cast<int>(!can_attack), hp, max_hp, cd[0], cd[1], static_cast<int>(enemy_near), static_cast<int>(dbg_hit_other));
	});
#endif

	place_ward(false);
	update_priority();
	if (P.unstick_rounds > 0)
		unstick();
	prebuild_fields();
	XM(xm_post());
#ifdef LEGEND_TRACE
	debug_block({
		std::printf("T r=%d %d task=%d g=%d pos=(%d,%d) hp=%.0f gems=%u gold=%u fuel=%llu\n", round, static_cast<int>(type), task, task_group, pos.x, pos.y, hp, gems, gold,
			static_cast<unsigned long long>(bc::fuel_remaining()));
		if (W.obj_mode && round % 25 == 0)
			for (int id : W.obj_groups)
			{
				const auto& og = W.groups[static_cast<std::size_t>(id)];
				float k = 0;
				const bool rd = obj_team_ready(og, og.st == ST_ALIVE ? og.hp_total : og.max_hp, k);
				int eta = 0;
				const float sc = group_score(og, eta);
				std::printf("OB r=%d %d g=%d st=%d hp=%.0f ready=%d kill=%.1f score=%.3f\n", round, static_cast<int>(type), id, static_cast<int>(og.st), og.hp_total, static_cast<int>(rd), k, sc);
			}
	});
#endif
	C.write_self(W.my_index, (task == T_FARM || task == T_CAPTURE || task == T_WAIT) ? task_group : -1);
	last_hp = hp;
}

void Brain::unstick()
{
	// Last resort: a body walking to a camp that has not left a 3x3 box (and not attacked) for unstick_rounds
	// gives the target up for a while. Every path to it may be held by allies or camps that do not move, or the
	// target sits where its own tiles block it; re-planning elsewhere beats standing there.
	auto& W = world();
	const bool walking = task == T_FARM || task == T_CAPTURE;
	const bool on_reward = task == T_CAPTURE && task_group >= 0 && W.groups[static_cast<std::size_t>(task_group)].mask.is_set(pos);
	if (!walking || task_group < 0 || on_reward || last_act_round >= round - 1 || W.ally_spawn.is_set(pos) || cheb(pos, ust_anchor) > 1)
	{
		ust_anchor = pos;
		ust_since = round;
		return;
	}
	if (round - ust_since < P.unstick_rounds)
		return;
#ifdef LEGEND_TRACE
	debug_block({ std::printf("UNSTICK r=%d %d task=%d g=%d pos=(%d,%d) since=%d\n", round, static_cast<int>(type), task, task_group, pos.x, pos.y, ust_since); });
#endif
	blacklist[static_cast<std::size_t>(task_group)] = round + P.unstick_blacklist;
	task_group = -1;
	tp_hop = -1;
	tp_island = -1;
	ust_anchor = pos;
	ust_since = round;
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
	if (tributing && !(P.win_bank && wins_with(static_cast<int>(gems))))
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
	enemy_near_field = false;
	enemy_near_d = BIG;
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
		const int ed = cheb(e.pos, pos);
		if (ed <= 9)
		{
			enemy_near = true;
			// An enemy on its own spawn heals fully every round and cannot chase a bag that stays away; on
			// maps whose spawns touch, counting it made every body bank whatever it carried straight off its
			// spawn (30x80: 40 bank walks of 37 steps for 22-25 gems each).
			if (!P.bank_ignore_spawn || !W.enemy_spawn.is_set(e.pos))
				enemy_near_field = true;
		}
		enemy_near_d = std::min(enemy_near_d, std::max(0, ed - age));
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
	// Farming a live group: the goal is reach of a camp still standing. Any group tile (dead camps included)
	// made a tile next to a dead wolf count as arrived while its live partner stood two tiles away: on the
	// 98x99 map, where the group field is often not built yet, bodies froze there for 30-78 rounds.
	bool live = false;
	if (P.stuck_live_goal && stop_at > 0 && g.st == ST_ALIVE)
		for (std::size_t i = 0; i < g.camps.size(); ++i)
			if (g.hp[i] > 0)
			{
				fallback.draw_chebyshev(g.camps[i].pos, static_cast<float>(stop_at));
				live = true;
			}
	if (!live)
		for (auto t : g.tiles)
			fallback.draw_chebyshev(t, static_cast<float>(stop_at));
	if (stop_at > 0)
		fallback &= ~g.mask;
	const bc::bitboard av = danger | (camp_danger & ~g.near) | alert_zone;
	if (N.ensure_group(g.id, P.target_field_fuel))
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
	if (N.ensure_altar(id, P.target_field_fuel))
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
		last_act_round = round;
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

bool Brain::cast_area_stun_at(const Enemy& e)
{
	// Aim at a tile within cast range and within the radius of the target (reach = range + radius); prefer
	// the aim that also catches more enemies (Marcella cannot be stunned), then the target's own tile.
	if (kit.aoe < 0 || !ready(kit.aoe))
		return false;
	const int range = static_cast<int>(kit.aoe_range), rad = static_cast<int>(kit.aoe_radius);
	if (cheb(pos, e.pos) > range + rad)
		return false;
	const auto& W = world();
	vec2 best{ -1, -1 };
	int best_n = 0;
	for (int dy = -rad; dy <= rad; ++dy)
		for (int dx = -rad; dx <= rad; ++dx)
		{
			const vec2 c{ e.pos.x + dx, e.pos.y + dy };
			if (cheb(pos, c) > range || !bc::map::is_in_bounds(c))
				continue;
			int n = 0;
			for (const auto& o : W.enemies)
				n += o.alive && o.visible && o.type != CT::marcella && cheb(o.pos, c) <= rad;
			if (n > best_n || (n == best_n && dx == 0 && dy == 0))
				best_n = n, best = c;
		}
	return best_n > 0 && cast_ground(kit.aoe, best);
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

bool Brain::wins_with(int bag) const
{
	return static_cast<int>(bc::global_submitted_gems(team::ally)) + bag >= static_cast<int>(bc::constants::winning_gems);
}

bool Brain::can_support(const Ally& a, const std::vector<Enemy*>& E) const
{
	if (a.hp < P.retreat_hp * a.max_hp)
		return false; // it is walking home, not fighting
	for (const auto* e : E)
		if (cheb(a.pos, e->pos) <= P.support_reach)
			return true;
	return false;
}

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
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 6 && (!P.support_filter || can_support(a, E)))
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
	// The user's rule (session 2): stay and keep hitting only when our own health outlasts the most the enemies
	// here can deal before the target dies (every visible enemy hitting us every round, spells included) and no
	// other enemy is near the target to support it; when they could kill us first, do not start it while we can
	// still get away (when we cannot, the cornered rule above trades instead of handing a dash/ranged chaser
	// free hits).
	if (P.stay_rule)
	{
		int support = 0;
		for (const auto& e : W.enemies)
			if (e.alive && e.seen_round >= 0 && round - e.seen_round <= P.threat_memory && &e != tgt && cheb(e.pos, tgt->pos) <= P.stay_support_r)
				++support;
		const float worst = their_dps * (std::ceil(tgt->hp / std::max(1.f, our_dps)) + 1.f);
		if (support == 0 && hp > worst * P.stay_margin && d <= my_reach + 2)
			fight = true;
		else if (P.stay_veto && fight && !killable && can_escape && hp <= worst)
			fight = false;
	}
	// A bag that wins the game is worth more than any fight we can walk away from.
	if (fight && P.win_bank && !killable && can_escape && gems > 0 && wins_with(static_cast<int>(gems)))
		fight = false;
	// Do not dive their spawn: it heals them and they block us.
	if (W.enemy_spawn.is_set(tgt->pos) || cheb(tgt->pos, W.enemy_spawn_c) <= 3)
		fight = fight && killable;
	XM(xm_fight(adv, t_kill_us, t_kill_them, our_hp, their_hp, our_dps, their_dps, allies_near, static_cast<int>(E.size()), fight, killable, in_reach,
		can_escape, isolated, reserve, static_cast<int>(tgt->type), d, incoming, t_die, tgt->hp, backup, str + focus * best_mod(kit) / 8.f + my_burst / 3.f));
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
		// A walk-exclusive stun (Ren, Ryth, Tavi, Prism) costs our step, but against a chaser whose basic attack
		// still reaches us after that step (melee step + hit, dash + hit, or ranged at 2) the step gains nothing:
		// it follows and hits. The stun denies that turn (this round's if it has not acted yet, else the next),
		// deals damage, and the walk resumes next turn. Traced: 245 flee turns with such a stun ready in 3 games,
		// none cast. Not near home: there the step to the healing spawn is worth more.
		if (P.flee_stun && !cast_done && W.dist_home(pos) > 2 && ((kit.cc >= 0 && kit.cc_excl && ready(kit.cc)) || (kit.aoe_stuns && ready(kit.aoe))))
		{
			Enemy* chaser_e = nullptr;
			int best_d = BIG;
			for (auto* e : E)
			{
				if (!e->ch || e->type == CT::marcella)
					continue;
				const int dd = cheb(pos, e->pos);
				const int hit_reach = e->kit.attack_range + (e->kit.ranged ? 0 : 1) + (e->ready(e->kit.dash) ? 2 : 0);
				if (dd + 1 <= hit_reach && dd < best_d)
					best_d = dd, chaser_e = e;
			}
			if (chaser_e)
			{
				const bool cc_ok = kit.cc >= 0 && kit.cc_excl && best_d <= static_cast<int>(kit.cc_range) && cast_unit_champ(kit.cc, *chaser_e->ch);
				if (cc_ok || (kit.aoe_stuns && ready(kit.aoe) && cast_area_stun_at(*chaser_e)))
				{
					dbg_eng = 8;
					if (!kit.ranged && can_attack && best_d <= kit.attack_range)
						attack_unit(*chaser_e->ch);
					return true;
				}
			}
		}
		if (P.flee_recall && W.dist_home(pos) > P.recall_min_dist && safe_to_recall())
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
		if (P.flee_recall && W.dist_home(pos) > P.recall_min_dist && safe_to_recall())
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
	if (d > 4 && cast_on_nearer(e))
		return true;
	if (d > kit.attack_range)
	{
		bc::bitboard goal;
		goal.draw_chebyshev(e.pos, static_cast<float>(kit.attack_range));
		if (kit.ranged)
		{
			const bool spell_now = d <= 4 && (ready(kit.cc) || ready(kit.dmg) || ready(kit.aoe));
			if (d <= kit.attack_range + 2 && ready(kit.dash))
				step(goal, false, true), dbg_eng = 2;
			else if (spell_now)
			{
				dbg_eng = 3;
				if (!cast_unit_champ(kit.cc, ec) && !cast_unit_champ(kit.dmg, ec))
					cast_ground(kit.aoe, e.pos);
				return true;
			}
			else
				step(goal, false, true), dbg_eng = 4;
		}
		else
		{
			// Area stun (Ryth: walk-exclusive, radius 1): cast it before walking in. Walking first makes it
			// uncastable this turn, and next turn it competes with the attack reset (one cast per turn); stunning
			// now lands it a turn earlier and next turn is step + attack + reset + attack. The old check below only
			// knew single-target stuns: Ryth walked in with the stun ready in 279 fight turns of 3 traced games.
			if (P.melee_aoe_stun && kit.aoe_stuns && d >= 2 && ready(kit.aoe) && e.type != CT::marcella && cast_area_stun_at(e))
				dbg_eng = 7;
			else if (d == 2 || !(d <= 4 && (ready(kit.cc) || ready(kit.dmg))))
				step(goal, false, true), dbg_eng = 5;
			else if (!cast_unit_champ(kit.cc, ec))
				cast_unit_champ(kit.dmg, ec), dbg_eng = 6;
			else
				dbg_eng = 6;
		}
		d = cheb(pos, e.pos);
		// Melee can still swing after walking: when the step leaves the target out of reach, hit an enemy that is
		// in reach instead of wasting the attack (traced: Ryth ending next to Issac without swinging).
		if (P.step_hit_other && !kit.ranged && d > kit.attack_range && can_attack)
		{
			auto& W = world();
			for (auto& o : W.enemies)
			{
				if (&o == &e || !o.ch || !o.alive || !o.visible || cheb(pos, o.pos) > kit.attack_range || W.enemy_spawn.is_set(o.pos))
					continue;
				if (o.type == CT::ren && hp <= 2.5f * bc::constants::passive_abilities::ren_retaliation_focus_ratio * o.focus && o.hp > str)
					continue;
				if (attack_unit(*o.ch))
				{
					dbg_hit_other = true;
					std::int32_t alive_flag = 1;
					bc::detail::sdk_champion_is_alive(o.handle, &alive_flag);
					if (alive_flag && !cast_done && ready(kit.reset) && cast_self(kit.reset))
						attack_unit(*o.ch);
				}
				break;
			}
		}
	}
	if (d <= kit.attack_range)
	{
		dbg_eng += 10;
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
	// Within two steps of spawn the trip is almost free, so it is not skipped there: skipping it let farm()
	// walk a hurt champion back out, and at three steps this check sent it home again, a farm/home flip-flop
	// that held bodies at the spawn edge for hundreds of rounds (63% of all turns on the 30x80 ladder map).
	if (dh >= BIG || dh <= (P.home_edge_fix ? 0 : 2))
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
	float camp_in = 0, obj_in = 0;
	int escape = 0, obj_escape = 0;
	for (const auto& g : W.groups)
		if (g.st == ST_ALIVE && g.awake && !g.harmless && g.near.is_set(pos))
		{
			// Only while no enemy is near: with enemies around the old line stays (gold_mono_48 vs _k1: the two
			// monoliths are 9 tiles apart; 20 of our 33 deaths were next to ours and they took 2 of our 3 kills).
			const bool obj = P.obj_shield && g.objective && W.obj_mode && enemy_near_d > P.obj_shield_enemy_d;
			for (std::size_t i = 0; i < g.camps.size(); ++i)
			{
				const int d = cheb(g.camps[i].pos, pos);
				if (g.hp[i] <= 0 || d > 3)
					continue;
				bool shielded = false;
				for (const auto& a : W.allies)
					if (P.safety_v2 || obj)
					if (a.handle != self && a.alive && a.visible && cheb(a.pos, g.camps[i].pos) < d)
					{
						shielded = true;
						break;
					}
				if (shielded)
					continue;
				if (obj)
				{
					obj_in += g.camps[i].str;
					obj_escape = std::max(obj_escape, 4 - d);
					continue;
				}
				camp_in += g.camps[i].str;
				escape = std::max(escape, 4 - d);
			}
		}
	float threshold = std::max(P.retreat_hp * max_hp, camp_in * static_cast<float>(P.safety_v2 ? escape + 1 : 4));
	if (obj_in > 0)
	{
		// Objective camps: only those that target us (no ally nearer), after our emblems, for the steps out of
		// reach plus one. Four rounds of every elk in reach (stampede: 6 x 60) exceeded Stellar's whole health
		// (975 at r540), so the ranged bodies stepped in and out of range without a shot.
		float eff = obj_in * (jungle_done() ? 0.7f : 1.f) * (durability_done() ? 0.9f : 1.f);
		threshold = std::max(threshold, eff * static_cast<float>(obj_escape + 1));
		camp_in += obj_in;
	}
	if (hp < threshold && P.finish_camp && camp_in > 0 && enemy_near_d > P.finish_enemy_d && task_group >= 0 &&
		task_group < static_cast<int>(W.groups.size()))
	{
		// The group we farm is nearly dead: finishing it costs at most camp_in per round until it dies (camps
		// die one by one, so less), then the capture is free (dead camps do not hit). Retreating instead walks
		// home and back for the last few hits (camps never heal, but the trip costs ~2x the walk).
		const auto& g = W.groups[static_cast<std::size_t>(task_group)];
		if (g.st == ST_ALIVE && g.near.is_set(pos))
		{
			const float kill = std::ceil(g.hp_total / std::max(10.f, dps_on(g)));
			const float left = hp - camp_in * kill;
			if (kill <= static_cast<float>(P.finish_rounds) && left >= std::max(camp_in, P.finish_hp_floor * max_hp))
				threshold = 0;
		}
	}
	// A reward waiting next to us (or a capture under way) is safe from camps: dead camps do not hit, and the
	// capture can recall home with the reward. Walking home first left rewards to expire (contest: 6 of 91
	// rewards waited 46 rounds, the expiry, tools/analysis/rewards.mjs).
	if (hp < threshold && P.capture_before_retreat && camp_in <= 0 && enemy_near_d > P.finish_enemy_d && (task == T_CAPTURE || reward_here()))
		threshold = 0;
	if (hp < threshold && P.win_bank && camp_in <= 0 && enemy_near_d > P.finish_enemy_d && gems > 0 && wins_with(static_cast<int>(gems)))
		threshold = 0; // the bag wins the game: tribute() banks it before anything else
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
#ifdef LEGEND_TRACE
	debug_block({ if (W.obj_mode) std::printf("SF r=%d %d hp=%.0f/%.0f thr=%.0f camp_in=%.0f obj_in=%.0f\n", round, static_cast<int>(type), hp, max_hp, threshold, camp_in, obj_in); });
#endif
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
	gold_v = P.gold_value;
	if (P.math_gold)
	{
		// Gold only turns into gems through the shards it buys, and a shard pays off over the rounds left: +5
		// strength on 40-50 is about +5% farming rate, which earns back 30 gold x gold_value = 6.6 gems in
		// ~gold_horizon rounds. Rounds left: the leading team's time to the winning score at its average pace so
		// far (an underestimate of its pace, so this errs toward valuing gold), capped by the round limit.
		// In the 48 audit games 20% of all gold was earned after a team passed 800 and ~485 gold per team
		// was never spent.
		const int lead_g = std::max(ours, theirs);
		float left = static_cast<float>(static_cast<int>(bc::constants::max_rounds) - round);
		if (lead_g > 0 && round > 0)
			left = std::min(left, static_cast<float>(static_cast<int>(bc::constants::winning_gems) - lead_g) * static_cast<float>(round) / static_cast<float>(lead_g));
		gold_v = P.gold_value * std::clamp(left / std::max(1.f, P.gold_horizon), 0.f, 1.f);
	}
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
	if (type == CT::cassi || type == CT::issac)
	{
		fight_margin += P.pair_caution;
		isolated_fight_adv += P.pair_caution;
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

int Brain::bank_min(int trip) const
{
	// Each bank costs about the walk to the altar (and back out, or a recall), whatever the bag: fewer, bigger
	// bags when the altar is far. Short trips keep the plain threshold (risk and scoreboard rules set it).
	if (P.bank_trip_w <= 0.f || trip >= BIG)
		return tribute_min;
	const int extra = static_cast<int>(P.bank_trip_w * static_cast<float>(std::max(0, trip - P.bank_trip_free)));
	return std::min(tribute_min + extra, static_cast<int>(P.bank_trip_cap * static_cast<float>(tribute_min)));
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
	const bool risky = enemy_near_field && static_cast<int>(gems) >= P.tribute_risky;
	// Once a bank trip starts, finish it: re-deciding every turn let a passing enemy or the on-the-way test
	// flip the choice each round and the champion oscillated in place for hundreds of rounds.
	const bool committed = P.sticky_tribute && task == T_TRIBUTE && static_cast<int>(gems) >= 10;
	// Recall and bank at the altar next to spawn when that beats walking (and heals and shops on the way).
	const int via_home = static_cast<int>(bc::constants::recall_time) + W.spawn_altar_d;
	const bool recall_bank = W.dist_home(pos) > P.recall_min_dist && via_home + 2 < dist && safe_to_recall() && !endgame;
	// A long bank trip is worth a bigger bag: the threshold rises with the cheapest way to an altar from here,
	// so a body far from every altar keeps farming and banks when its route passes close to one.
	const int need = bank_min(recall_bank ? via_home : dist);
	const bool want = force || endgame || winning || risky || committed || static_cast<int>(gems) >= need || dist <= P.tribute_near ||
		(static_cast<int>(gems) >= 10 && on_the_way(a));
	if (!want)
		return false;
#ifdef LEGEND_TRACE
	debug_block({
		if (task != T_TRIBUTE)
			std::printf("B r=%d %d gems=%u dist=%d need=%d via=%d rb=%d f=%d e=%d w=%d risky=%d near=%d otw=%d\n", round, static_cast<int>(type), gems, dist, need, via_home, (int)recall_bank,
				(int)force, (int)endgame, (int)winning, (int)risky, (int)(dist <= P.tribute_near), (int)(gems >= 10 && on_the_way(a)));
	});
#endif
	// A tribute cancelled this turn or last (a threat made it pointless): flee, fight or move on first.
	if (round - tribute_cancel_round <= 2 && !endgame && !winning && !force)
		return false;
	if (recall_bank)
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

int Brain::approach_rounds(int d_tile) const
{
	// Rounds until we can hit a group d_tile steps away (non-decreasing in d_tile: score_cap relies on it).
	if (!P.math_eta)
		return std::max(0, d_tile - 1);
	float t = static_cast<float>(std::max(0, d_tile - kit.attack_range));
	if (kit.dash >= 0)
		t = std::max(0.f, t - P.dash_head_start) * P.dash_pace;
	return static_cast<int>(t + 0.5f);
}

float Brain::score_cap(const Group& g) const
{
	// An upper bound on group_score(g): its value with the largest multipliers group_score can apply (the deny
	// bonus on their half, contesting an enemy capture; shares and discounts are <= 1) over its smallest time
	// (the walk, at least the Chebyshev distance to the nearest tile, plus the 6 capture rounds; waits, kill
	// time, trips and penalties only add). farm() skips a group whose cap cannot beat the best score so far:
	// the same choice, without the cost of scoring it.
	float v = static_cast<float>(g.gems) + gold_v * static_cast<float>(g.gold);
	if (!g.ours)
		v *= 1.f + std::max(0.f, deny_bonus);
	if (g.enemy_on_tile)
		v *= std::max(1.f, P.deny_capture_mult);
	const int lb = std::max(0, cheb(g.center, pos) - g.radius);
	const int d = g.st == ST_REWARD ? lb : approach_rounds(lb);
	return v / std::max(1.f, static_cast<float>(d) + 6.f);
}

bool Brain::obj_team_ready(const Group& g, float hp_left, float& kill) const
{
	// Objective map: can the living team clear g quickly and absorb its camps' damage? Every body runs the same
	// estimate from the same facts (designs, growth, alive flags), so they switch to the objective together.
	auto& W = world();
	float dps = std::max(10.f, dps_on(g));
	float pool = max_hp * (1.f - P.retreat_hp);
	int alive_n = 1, dead_n = 0;
	for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
	{
		if (i == W.my_index)
			continue;
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (!a.alive)
		{
			++dead_n;
			continue;
		}
		++alive_n;
		dps += ally_dps_on(i, g);
		const float mh = a.max_hp > 1.f ? a.max_hp : bc::champion_designs[static_cast<std::size_t>(a.type)].base_stats().base_health;
		pool += mh * (1.f - P.retreat_hp);
	}
	if (alive_n < P.obj_min_bodies || dead_n > P.obj_dead_max)
		return false;
	kill = hp_left / dps;
	// Camps that hit back die first (obj_attackers_first): each attacker hits until the team's damage has gone
	// through it and every attacker before it.
	std::array<float, 16> hs{}, ss{};
	int n = 0;
	for (std::size_t i = 0; i < g.camps.size() && n < 16; ++i)
	{
		const float h = g.st == ST_RESPAWN ? g.camps[i].max_hp : g.hp[i];
		if (h <= 0 || g.camps[i].str <= 0)
			continue;
		hs[static_cast<std::size_t>(n)] = h, ss[static_cast<std::size_t>(n)] = g.camps[i].str, ++n;
	}
	float cum = 0, taken = 0;
	for (int k = 0; k < n; ++k)
	{
		cum += hs[static_cast<std::size_t>(k)];
		taken += ss[static_cast<std::size_t>(k)] * cum / dps;
	}
	return kill <= P.obj_clear_max && taken <= P.obj_absorb * pool;
}

float Brain::group_score(const Group& g, int& eta, bool* need_pair, int d_override) const
{
	if (need_pair)
		*need_pair = false;
	auto& W = world();
	auto& C = comms();
	eta = BIG;
	if (g.monolith && !P.farm_monolith)
		return -1;
	if (P.obj_open_rounds > 0 && W.obj_mode && round < P.obj_open_rounds && !g.objective && g.d_enemy - g.d_ally < P.obj_open_margin)
		return -1;
	const int d_tile = d_override >= 0 ? d_override : nav().group_dist(g, pos);
	if (d_tile >= BIG)
		return -1;
	// Rounds until we can hit the group. Ranged champions stop at their attack range; a dash kit covers 10 tiles
	// per 8-round cooldown (walk + 2-tile dash). Fitted on 1,659 engaged episodes: d-1 was exact for Ryth and Varg
	// and 2.2-2.3 rounds long for Cassi, Stellar (actual = -2.1 + 1.0 x predicted), Issac and Ren (0.85 x).
	const int d_adj = approach_rounds(d_tile);
#ifdef XM_TRACE
	const int xm_d_old = std::max(0, d_tile - 1);
#endif

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
			{
				// A higher-index claimer yields the group to us but still fights on it. Dropping its damage too
				// made a pack that needs two bodies look impossible every other turn: the lower-index body
				// flipped between joining (partner counted) and leaving (partner ignored) each round
				// (route_stats: most target flip-flops in local games).
				if (P.claim_helpers)
				{
					ally_dps += ally_dps_on(i, g);
					melee_ally |= ally_melee(i);
				}
				continue;
			}
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
		if (avail > d_adj + (W.obj_mode && g.objective ? P.obj_max_wait : P.max_wait))
			return -1;
		wait = std::max(0, avail - d_adj);
		hp_left = g.max_hp;
		break;
	}
	default:
		hp_left = g.hp_total;
		break;
	}
	sc_team = false;
	if (g.st != ST_REWARD)
	{
		eta = d_adj;
		if (claimers)
		{
			// Join only packs too heavy for one body; never a third body except on a monolith.
			const float solo_rounds = hp_left / std::max(10.f, ally_dps);
			const bool heavy = g.monolith || g.elk || (!g.harmless && (solo_rounds > P.join_min_rounds || g.attackers >= 2));
			if (!heavy || (claimers >= (g.monolith ? 4 : 1 + P.max_join) && !(W.obj_mode && g.objective && P.obj_team)))
				return -1;
			share = P.join_share;
		}
		// Rounds to clear the group with the given helpers; false when it cannot be done in max_trips.
		auto plan = [&](float helpers_dps, bool helper_melee, float& t) {
			const float kill = hp_left / (my_dps + helpers_dps);
			t = static_cast<float>(d_adj + wait) + kill + 6.f;
#ifdef XM_TRACE
			if (xm_sp)
			{
				*xm_sp = ScoreParts{};
				xm_sp->my_dps = my_dps, xm_sp->ally_dps = helpers_dps, xm_sp->hp_left = hp_left, xm_sp->kill = kill;
				xm_sp->d_adj = d_adj, xm_sp->d0 = xm_d_old, xm_sp->wait = wait, xm_sp->claimers = claimers, xm_sp->melee_ally = helper_melee, xm_sp->planned = true;
			}
#endif
			if (g.harmless)
				return true;
			// Camps hit the nearest champion: a ranged champion next to a melee ally takes almost nothing.
			const float in = incoming_on(g);
#ifdef XM_TRACE
			// The uncorrected model, logged next to the new one so both are scored on the same episodes.
			const bool xm_tank0 = !(kit.ranged && helper_melee);
			const float xm_share0 = xm_tank0 ? (helper_melee && !kit.ranged ? 0.5f : 1.f) : 0.1f;
			const float xm_res0 = std::max(P.camp_hp_reserve * max_hp, in * 3.f);
			const float xm_taken0 = in * xm_share0 * kill, xm_bf0 = std::max(1.f, max_hp - xm_res0);
			const float xm_ex0 = xm_taken0 - std::max(0.f, hp - xm_res0);
			const int xm_trips0 = xm_ex0 > 0 ? static_cast<int>(std::ceil(xm_ex0 / xm_bf0)) : 0;
#endif
			// A melee ally standing at the group (claiming it or not) is nearer to the camps than a ranged champion
			// and takes their hits: with one in sight, Cassi and Stellar took 0.29-0.35 of the claim-only prediction.
			bool melee_present = false;
			if (P.math_taken)
				for (int i = 0; i < static_cast<int>(W.allies.size()) && !melee_present; ++i)
				{
					const auto& a = W.allies[static_cast<std::size_t>(i)];
					melee_present = i != W.my_index && a.alive && a.visible && cheb(a.pos, g.center) <= P.presence_radius && ally_melee(i);
				}
			const bool tank_melee = helper_melee || melee_present;
			const bool i_tank = !(kit.ranged && tank_melee);
			float my_share = i_tank ? (tank_melee && !kit.ranged ? 0.5f : 1.f) : 0.1f;
			float taken = in * my_share * kill;
			float reserve = std::max(P.camp_hp_reserve * max_hp, in * 3.f);
			float seq = 1.f, in_now = in; // in_now: what reaches us in the first rounds
			if (P.math_taken)
			{
				// Camps die one by one (farm_group hits the lowest health first) and each one attacks from the
				// round after our first hit until the round it dies, t_k = health of camps 1..k / our damage.
				// While it is our target it reaches us; before that (t < t_{k-1}) it is a bystander, which
				// reaches a melee champion standing in the pack but a lone ranged one hitting from range 3 only
				// part of the time (ranged_exposure). taken = sum_k str_k x (q t_{k-1} + t_k - t_{k-1} - 1).
				// A melee champion on a pack of n equal camps takes (n+1)/(2n) of the old constant-incoming
				// product, which overstated a pack by up to 2x.
				const float q = kit.ranged && !tank_melee ? P.ranged_exposure : 1.f;
				std::array<float, 8> hs{}, ss{};
				int n = 0;
				float raw = 0;
				for (std::size_t i = 0; i < g.camps.size() && n < 8; ++i)
				{
					const float h = g.st == ST_RESPAWN ? g.camps[i].max_hp : g.hp[i];
					if (h <= 0)
						continue;
					int j = n++;
					for (; j > 0 && hs[static_cast<std::size_t>(j - 1)] > h; --j)
						hs[static_cast<std::size_t>(j)] = hs[static_cast<std::size_t>(j - 1)], ss[static_cast<std::size_t>(j)] = ss[static_cast<std::size_t>(j - 1)];
					hs[static_cast<std::size_t>(j)] = h, ss[static_cast<std::size_t>(j)] = g.camps[i].str;
					raw += g.camps[i].str;
				}
				const float dps_all = my_dps + helpers_dps;
				float cum = 0, num = 0;
				for (int k = 0; k < n; ++k)
				{
					const float t_prev = cum / dps_all;
					cum += hs[static_cast<std::size_t>(k)];
					const float t_k = cum / dps_all;
					num += ss[static_cast<std::size_t>(k)] * std::max(0.f, q * t_prev + (t_k - t_prev) - 1.f);
				}
				if (raw > 0 && kill > 0)
					seq = std::min(1.f, num / (raw * kill));
				taken = in * my_share * kill * seq;
				// The HP budget of one trip ends where safety() sends us home: below retreat_hp, or below 4 rounds
				// of the raw strength of the camps in reach (safety counts every live camp within 3, before
				// emblems). The old 18% / 3 rounds reserve promised health the retreat never lets us spend.
				const float reach = n > 0 ? ss[0] + q * (raw - ss[0]) : raw;
				reserve = std::max(std::max(P.camp_hp_reserve, P.retreat_hp) * max_hp, reach * 4.f);
				if (raw > 0)
					in_now = in * reach / raw;
			}
			const float budget_now = std::max(0.f, hp - reserve);
			const float budget_full = std::max(1.f, max_hp - reserve);
			if (i_tank && budget_full < in_now * my_share * 5.f)
				return false; // cannot even survive a few rounds next to it
			const float extra = taken - budget_now;
			const int trips = extra > 0 ? static_cast<int>(std::ceil(extra / budget_full)) : 0;
#ifdef XM_TRACE
			if (xm_sp)
			{
				xm_sp->in = in, xm_sp->share = my_share, xm_sp->taken = taken, xm_sp->budget_now = budget_now, xm_sp->budget_full = budget_full;
				xm_sp->trips = trips;
				xm_sp->share0 = xm_share0, xm_sp->taken0 = xm_taken0, xm_sp->trips0 = xm_trips0, xm_sp->seq = seq, xm_sp->present = melee_present;
				xm_sp->reach = in > 0 ? in_now / in : 1.f;
			}
#endif
			if (trips > P.max_trips)
				return false;
			t += static_cast<float>(trips * trip_cost(g));
			return true;
		};
		float team_kill = 0;
		const bool solo_ok = plan(ally_dps, melee_ally, time);
		if (!solo_ok && W.obj_mode && g.objective && P.obj_team && g.attackers >= P.obj_team_attackers && obj_team_ready(g, hp_left, team_kill))
		{
			// Objective map: too heavy for us and the bodies already on it, but not for the whole team.
			sc_team = true;
			time = static_cast<float>(d_adj + wait) + team_kill + 6.f;
			share = P.obj_value_share;
		}
		else if (!solo_ok)
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

	float value = (static_cast<float>(g.gems) + gold_v * static_cast<float>(g.gold)) * share;
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
#ifdef XM_TRACE
	if (xm_sp)
		xm_sp->time = time, xm_sp->value = value, xm_sp->score = value / std::max(1.f, time);
#endif
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
		value += static_cast<float>(g.gems) + gold_v * static_cast<float>(g.gold);
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
	if (task != T_CAPTURE && cast_en_route())
		return;
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
	bool best_pair = false, best_team = false;
	float best_s = 0;
	prepare_scoring();
	{
		// Score the current target first, then groups near us, then the rest while fuel lasts: on a
		// 48-group map scoring everything every turn cost ~55k and turns spilled into the next round.
		auto consider = [&](Group& g) {
			if (blacklist[static_cast<std::size_t>(g.id)] > round)
				return;
			// Groups that cannot beat the best so far are skipped unscored (exact, see score_cap). Scoring took
			// ~60k fuel a turn on the 98x99 48-group map and the math model made each group ~23% dearer, so
			// the loop ran down to score_fuel_floor and farm_group (up to ~29k) spilled turns into the next round.
			if (P.score_cap && best_s > 0 && g.id != task_group && score_cap(g) <= best_s)
				return;
			int eta = 0;
			bool np = false;
			float s = group_score(g, eta, &np);
			if (s <= 0)
				return;
			const bool tm = sc_team;
			if (g.id == task_group)
				s *= P.hysteresis;
			else if (P.flip_window > 0 && g.id == left_group && round - left_round <= P.flip_window)
				s /= P.flip_margin; // going back to a target we just left: A-B-A-B flips walk in place
			if (s > best_s)
				best_s = s, best = g.id, best_eta = eta, best_pair = np, best_team = tm;
		};
		if (task_group >= 0 && task_group < static_cast<int>(W.groups.size()))
			consider(W.groups[static_cast<std::size_t>(task_group)]);
		// Far groups stop at a higher floor so the walk keeps the fuel it needs: on the 98x99 map scoring all
		// 70 groups left ~35k, no target field could be built (45k) and the dynamic searches that replace it
		// (30k) were skipped, so bodies stood behind an ally or next to a dead camp. The start rotates so every
		// far group is still scored every few turns.
		const int ng = static_cast<int>(W.groups.size());
		const long long far_floor = P.score_far_floor > 0 ? P.score_far_floor : P.score_fuel_floor;
		const int off = P.score_far_floor > 0 && ng > 0 ? (round * 7) % ng : 0;
		for (int pass = 0; pass < 2; ++pass)
			for (int k = 0; k < ng; ++k)
			{
				auto& g = W.groups[static_cast<std::size_t>((k + off) % ng)];
				if (g.id == task_group || (cheb(g.center, pos) <= P.score_near) != (pass == 0))
					continue;
				if (pass == 1 && bc::fuel_remaining() < far_floor)
					break;
				// Near groups too: on the 90x30 official map (40 groups, most within 20 tiles) scoring alone took
				// 70-85k and the walk after it spilled into the next round every other turn.
				if (pass == 0 && P.score_near_floor > 0 && bc::fuel_remaining() < P.score_near_floor)
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
	XM(xm_decide(best));
#ifdef STUCK_DBG
	debug_block({
		int cur_eta = 0;
		const float cur_s = task_group >= 0 ? group_score(W.groups[static_cast<std::size_t>(task_group)], cur_eta) : -9.f;
		std::printf("F r=%d %d best=%d s=%.3f eta=%d cur=%d cs=%.3f hop=%d isl=%d pos=(%d,%d) fuel=%lld start=%lld\n", round, static_cast<int>(type), best, best_s, best_eta, task_group, cur_s, tp_hop, tp_island, pos.x, pos.y, (long long)bc::fuel_remaining(), dbg_ff);
	});
#endif
	if (best != task_group)
	{
		if (task_group >= 0)
			left_group = task_group, left_round = round;
		task_group = best;
		task_since = round;
	}
	// Give up on targets we cannot reach in reasonable time.
	if (round - task_since > 2 * best_eta + 60 + (W.obj_mode && W.groups[static_cast<std::size_t>(best)].objective ? P.obj_commit : 0))
	{
		blacklist[static_cast<std::size_t>(best)] = round + 40;
		task_group = -1;
		return;
	}
	Group& g = W.groups[static_cast<std::size_t>(best)];
	task_team = best_team;
	if (best_team && g.st != ST_REWARD && hp < P.obj_go_hp * max_hp && !W.ally_spawn.is_set(pos) &&
		nav().group_dist(g, pos) > P.obj_go_far)
	{
		// Objective walk: arrive healthy. Ren and Varg walked in at 30-40% health and were the first to leave.
		if (go_home())
			return;
	}
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
			// Where will the bag be banked? After the recall, from spawn (spawn_altar_d steps, after the rest
			// turn); without it, at the altar nearest this tile. When the nearest altar plus a recall home
			// afterwards is still cheaper, bank first: tribute() walks there once the reward lands and
			// home_trip() recalls from the altar to heal and shop.
			const int spawn_altar = world().spawn_altar_d;
			int adist = BIG;
			if (P.bank_first || P.bank_trip_w > 0 || P.win_bank)
				nearest_altar(adist);
			// A bag that wins the game: bank it at the nearest altar unless the recall route is faster.
			if (P.win_bank && adist < BIG && wins_with(static_cast<int>(gems) + g.gems) &&
				(spawn_altar >= BIG || adist <= recall_t + 1 + spawn_altar))
			{
				place_ward(round - ward_round > 4);
				return true;
			}
			const bool bank_here = P.bank_first && adist < BIG && spawn_altar < BIG &&
				adist + static_cast<int>(bc::constants::recall_time) + P.bank_first_margin <= spawn_altar;
			const bool bag = static_cast<int>(gems) + g.gems >= bank_min(std::min(adist, spawn_altar < BIG ? 1 + spawn_altar : BIG));
			if (bag && bank_here && !hurt)
			{
				place_ward(round - ward_round > 4);
				return true;
			}
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

// Cast before walking: a ready damage spell is lost cooldown while the body walks past camps. Casting from exactly 4
// tiles is free (camps hit at 3), and camps never heal, so the damage is still there when a body farms the group.
// Only groups that are not the task group (farm_group already casts there), and only when no enemy is near.
bool Brain::cast_en_route()
{
	if (!P.cast_en_route || cast_done || !can_move || !can_cast)
		return false;
	const bool dmg_up = kit.dmg >= 0 && ready(kit.dmg);
	const bool aoe_up = kit.aoe >= 0 && ready(kit.aoe) && (!kit.aoe_stuns || P.cast_en_route >= 2);
	const bool cc_up = P.cast_en_route >= 2 && kit.cc >= 0 && ready(kit.cc) && kit.cc_mod > 0;
	if (!dmg_up && !aoe_up && !cc_up)
		return false;
	if (enemy_near_d <= P.hold_spell_dist || enemies_within(9) > 0)
		return false;
	auto& W = world();
	const int reach = static_cast<int>(std::max({ dmg_up ? kit.dmg_range : 0.f, aoe_up ? kit.aoe_range : 0.f, cc_up ? kit.cc_range : 0.f }));
	Group* bg = nullptr;
	std::size_t bi = 0;
	float bk = 1e30f;
	for (auto& g : W.groups)
	{
		if (!g.ours || g.monolith || g.id == task_group || g.st != ST_ALIVE || g.seen_round < 0 || cheb(g.center, pos) > reach + g.radius + 1)
			continue;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			const int d = cheb(pos, g.camps[i].pos);
			if (g.hp[i] <= 0 || !W.camp_occ.is_set(g.camps[i].pos) || d < 4 || d > reach)
				continue;
			// A camp at 4 is outside every camp's reach (3); a group whose other camps stand closer than that could hit us.
			bool safe = true;
			for (std::size_t j = 0; j < g.camps.size(); ++j)
				safe &= !(g.hp[j] > 0 && W.camp_occ.is_set(g.camps[j].pos) && cheb(pos, g.camps[j].pos) <= 3);
			if (!safe)
				continue;
			if (g.hp[i] < bk)
				bk = g.hp[i], bg = &g, bi = i;
		}
	}
	if (!bg)
		return false;
	return spells_on_camp(*bg, bi, P.cast_en_route < 2);
}

// Fight: the target is out of reach but another enemy stands within spell range: cast on it, hold position.
bool Brain::cast_on_nearer(const Enemy& skip)
{
	if (!P.cast_near_target || cast_done || !can_cast)
		return false;
	if (!(ready(kit.cc) || ready(kit.dmg) || ready(kit.aoe)))
		return false;
	auto& W = world();
	Enemy* pick = nullptr;
	for (auto& o : W.enemies)
	{
		if (&o == &skip || !o.ch || !o.alive || !o.visible || cheb(pos, o.pos) > 4 || W.enemy_spawn.is_set(o.pos))
			continue;
		if (o.type == CT::ren && hp <= 2.5f * bc::constants::passive_abilities::ren_retaliation_focus_ratio * o.focus && o.hp > burst_vs(o))
			continue;
		if (!pick || o.hp < pick->hp)
			pick = &o;
	}
	if (!pick)
		return false;
	if (!cast_unit_champ(kit.cc, *pick->ch) && !cast_unit_champ(kit.dmg, *pick->ch))
		cast_ground(kit.aoe, pick->pos);
	return cast_done;
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
	const bool obj = W.obj_mode && g.objective;
	const bool obj_first = obj && P.obj_attackers_first;
	if (obj && task_team && P.obj_gather > 1 && g.st == ST_ALIVE && !g.awake && g.hp_total / std::max(10.f, dps_on(g)) > P.obj_solo_rounds)
	{
		// Objective: bodies arriving one by one were worn down by the camps (6 elks hit for 360 a round) and
		// left it half dead for the enemy (stampede vs _v6: 1,707 of 17,400 left for 130 rounds, then their
		// Ren took 360 gems). Wait just outside camp range for the team, unless someone already woke it.
		int near = 0, alive_n = 0;
		for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
		{
			const auto& a = W.allies[static_cast<std::size_t>(i)];
			if (!a.alive)
				continue;
			++alive_n;
			const vec2 ap = i == W.my_index ? pos : a.pos;
			if ((i == W.my_index || (a.visible && a.seen_round == round)) && nav().group_dist(g, ap) <= P.obj_gather_r)
				++near;
		}
		if (obj_gather_group != g.id)
			obj_gather_group = g.id, obj_gather_since = -1;
		const int need = std::min(P.obj_gather, alive_n);
		if (near < need)
		{
			if (nav().group_dist(g, pos) <= P.obj_gather_r && obj_gather_since < 0)
				obj_gather_since = round;
			if (obj_gather_since < 0 || round - obj_gather_since <= P.obj_gather_max)
			{
#ifdef LEGEND_TRACE
				debug_block({ std::printf("GW r=%d %d near=%d need=%d since=%d awake=%d\n", round, static_cast<int>(type), near, need, obj_gather_since, (int)g.awake); });
#endif
				task = T_WAIT;
				go_group(g, 4, true);
				return true;
			}
		}
	}
	// Choose among live, visible camps in attack range: lowest health first (Varg: most neighbours for splash).
	auto pick = [&](int range) {
		std::size_t best = g.camps.size();
		float best_key = 1e30f;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (g.hp[i] <= 0 || !W.camp_occ.is_set(g.camps[i].pos) || cheb(pos, g.camps[i].pos) > range)
				continue;
			float key = g.hp[i];
			if (obj_first && g.camps[i].str <= 0)
				key += 1e6f; // harmless camps (gem clusters) last: the elks hit until they die
			if (type == CT::varg)
				for (std::size_t j = 0; j < g.camps.size(); ++j)
					if (j != i && g.hp[j] > 0 && cheb(g.camps[i].pos, g.camps[j].pos) <= 1)
						key -= 600.f;
			if (key < best_key)
				best_key = key, best = i;
		}
		return best;
	};
	// Keep burst for a fight only when one is likely within the cooldown: an unused ready spell is lost value
	// (8-round cooldowns), and an enemy 7-9 tiles away led to a fight within 8 rounds only 13% of the time.
	const bool save_cc = enemy_near_d <= P.hold_cc_dist;
	const bool hold_spells = enemy_near_d <= P.hold_spell_dist && P.hold_spells_near_enemies;
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
				if (g.hp[i] > 0 && (W.camp_occ.is_set(g.camps[i].pos) || (P.stuck_live_goal && !W.vis.is_set(g.camps[i].pos))))
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
	if (obj_first && g.camps[t].str <= 0 && can_move)
	{
		// A gem cluster is in reach but an elk is not: ranged bodies stopped at the first camp in range and the
		// outer gem clusters of stampede's group died first while all six elks kept hitting (3,000 health of
		// damage spent under full fire). Step into reach of a camp that hits back.
		bc::bitboard goal;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
			if (g.hp[i] > 0 && g.camps[i].str > 0 && W.camp_occ.is_set(g.camps[i].pos))
				goal.draw_chebyshev(g.camps[i].pos, static_cast<float>(kit.attack_range));
		goal &= ~g.mask;
		goal &= ~W.walls;
		if (!goal.is_empty() && !goal.is_set(pos) && step(goal, false, true))
		{
			const std::size_t t2 = pick(kit.attack_range);
			if (t2 < g.camps.size())
				attack_chain_camp(g, t2);
			return true;
		}
	}
	if (!hold_spells)
		spells_on_camp(g, t, save_cc);
	attack_chain_camp(g, t);
	return true;
}

#ifdef XM_TRACE
// ---------------------------------------------------------------------------------------------- prediction audit
// Every function below runs inside debug_block (fuel paused) and only prints and updates xm_* state, so an
// XM_TRACE build plays the same game as the plain build. tools/analysis/xm_audit.py joins the lines with
// the replay.

void Brain::xm_pre()
{
	auto& W = world();
	if (round == init_round && W.my_index == 0)
		for (const auto& g : W.groups)
		{
			int k[5] = { 0, 0, 0, 0, 0 };
			float str_sum = 0;
			for (const auto& c : g.camps)
				++k[std::min(4, std::max(0, static_cast<int>(c.type)))], str_sum += c.str;
			std::printf("GI g=%d n=%zu gems=%d gold=%d resp=%d mhp=%.0f str=%.0f wolf=%d elk=%d gem=%d gold_c=%d mono=%d ours=%d dh=%d cl=%.2f\n", g.id, g.camps.size(), g.gems, g.gold, g.respawn,
				g.max_hp, str_sum, k[0], k[1], k[2], k[3], k[4], static_cast<int>(g.ours), g.d_home_c, g.cluster);
		}
	// Per-round farming check: the prediction made at the end of our previous turn against what happened since
	// (our attack that turn, allies' attacks, then the camps' attacks at the start of this round).
	if (xm_pg >= 0 && xm_pr == round - 1)
	{
		const auto& g = W.groups[static_cast<std::size_t>(xm_pg)];
		if (g.seen_round == round)
		{
			const float dealt = std::max(0.f, xm_g_hp - g.hp_total);
			const float lost = std::max(0.f, xm_my_hp - hp);
			std::printf("FR r=%d ty=%d g=%d live=%d cl=%.2f myd=%.1f ad=%.1f claim=%d vis=%d pin=%.1f share=%.2f near=%.1f dealt=%.1f lost=%.1f clean=%d str=%.0f foc=%.0f hp=%.0f mhp=%.0f j=%d du=%d killed=%d share0=%.2f pres=%d reach=%.3f\n",
				round, static_cast<int>(type), xm_pg, xm_p_live, g.cluster, xm_p_my, xm_p_ally, xm_p_claim, xm_p_vis, xm_p_in, xm_p_share, xm_p_near, dealt, lost,
				static_cast<int>(xm_p_clean && enemies_within(8) == 0), str, focus, xm_my_hp, max_hp, static_cast<int>(jungle_done()), static_cast<int>(durability_done()),
				static_cast<int>(g.hp_total <= 0), xm_p_share0, static_cast<int>(xm_p_pres), xm_p_reach);
		}
	}
	xm_pg = -1;
	// Episode bookkeeping: health lost while engaged, and the group's death.
	if (xm_ep.g >= 0)
	{
		const auto& g = W.groups[static_cast<std::size_t>(xm_ep.g)];
		if (xm_ep.engage_r >= 0 && !xm_ep.away)
			xm_ep.lost += std::max(0.f, xm_my_hp - hp);
		if (g.st == ST_ALIVE)
			xm_ep.saw_alive = true;
		if (g.seen_round == round && (g.st == ST_REWARD || (g.st == ST_ALIVE && g.hp_total <= 0)))
			xm_close("kill");
		else if (g.seen_round == round && g.st == ST_RESPAWN && xm_ep.saw_alive)
			xm_close("gone");
	}
}

void Brain::xm_decide(int best)
{
	auto& W = world();
	if (best < 0 || best == xm_ep.g)
		return;
	if (xm_ep.g >= 0)
		xm_close("switch");
	const auto& g = W.groups[static_cast<std::size_t>(best)];
	if (g.st == ST_REWARD)
		return;
	ScoreParts sp;
	xm_sp = &sp;
	int eta = 0;
	group_score(g, eta);
	xm_sp = nullptr;
	xm_ep = XmEp{};
	xm_ep.g = best;
	xm_ep.commit_r = round;
	xm_ep.p = sp;
	xm_ep.g_hp_commit = g.st == ST_RESPAWN ? g.max_hp : g.hp_total;
	xm_ep.gv = gold_v;
	xm_ep.my_hp0 = hp;
}

void Brain::xm_close(const char* why)
{
	auto& W = world();
	if (xm_ep.g < 0)
		return;
	const auto& g = W.groups[static_cast<std::size_t>(xm_ep.g)];
	const auto& p = xm_ep.p;
	std::printf("FE r=%d ty=%d g=%d why=%s n=%zu gems=%d gold=%d elk=%d mono=%d commit=%d eng=%d pk=%.1f pd=%.1f pad=%.1f pcl=%d pin=%.1f psh=%.2f ptk=%.0f pbn=%.0f pbf=%.0f ptr=%d tc=%d ptime=%.1f peta=%d pwait=%d pval=%.1f psc=%.3f plan=%d ghpc=%.0f hp0=%.0f myhp0=%.0f mhp=%.0f ak=%d atot=%d lost=%.0f trips=%d psh0=%.2f ptk0=%.0f ptr0=%d seq=%.3f pres=%d peta0=%d gv=%.3f\n",
		round, static_cast<int>(type), xm_ep.g, why, g.camps.size(), g.gems, g.gold, static_cast<int>(g.elk), static_cast<int>(g.monolith), xm_ep.commit_r, xm_ep.engage_r, p.kill, p.my_dps,
		p.ally_dps, p.claimers, p.in, p.share, p.taken, p.budget_now, p.budget_full, p.trips, trip_cost(g), p.time, p.d_adj, p.wait, p.value, p.score, static_cast<int>(p.planned),
		xm_ep.g_hp_commit, xm_ep.hp0, xm_ep.my_hp0, max_hp, xm_ep.engage_r >= 0 ? round - xm_ep.engage_r : -1, round - xm_ep.commit_r, xm_ep.lost, xm_ep.trips,
		p.share0, p.taken0, p.trips0, p.seq, static_cast<int>(p.present), p.d0, xm_ep.gv);
	xm_ep = XmEp{};
}

void Brain::xm_dead()
{
	if (xm_was_alive)
	{
		std::printf("DTH r=%d ty=%d gems=%u task=%d g=%d\n", round, static_cast<int>(type), gems, task, task_group);
		xm_close("death");
	}
	xm_was_alive = false;
	xm_pg = -1;
}

void Brain::xm_post()
{
	auto& W = world();
	xm_was_alive = true;
	const int cur = (task == T_FARM || task == T_WAIT || task == T_CAPTURE) ? task_group : -1;
	if (xm_ep.g >= 0 && cur >= 0 && cur != xm_ep.g)
		xm_close("switch");
	if (xm_ep.g >= 0 && round - xm_ep.commit_r > 400)
		xm_close("timeout");
	if (xm_ep.g >= 0)
	{
		// A heal trip: home (walk or recall) and back to the same group.
		if (task == T_HOME || flag(state, bc::champion_state::recalling) || W.ally_spawn.is_set(pos))
			xm_ep.away = true;
		else if (cur == xm_ep.g && xm_ep.away)
			xm_ep.away = false, ++xm_ep.trips;
	}
	if (task == T_FARM && task_group >= 0)
	{
		const auto& g = W.groups[static_cast<std::size_t>(task_group)];
		bool in_range = false;
		int live = 0;
		float near_in = 0;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (g.hp[i] <= 0)
				continue;
			++live;
			const int d = cheb(g.camps[i].pos, pos);
			in_range |= d <= kit.attack_range && W.camp_occ.is_set(g.camps[i].pos);
			if (d <= 3)
			{
				// Camps hit the nearest champion: count this camp only if no visible ally is strictly nearer.
				bool shielded = false;
				for (const auto& a : W.allies)
					if (a.handle != self && a.alive && a.visible && cheb(a.pos, g.camps[i].pos) < d)
						shielded = true;
				if (!shielded)
					near_in += g.camps[i].str;
			}
		}
		if (in_range && g.st == ST_ALIVE && g.hp_total > 0)
		{
			ScoreParts sp;
			xm_sp = &sp;
			int eta = 0;
			group_score(g, eta);
			xm_sp = nullptr;
			int vis = 0;
			for (const auto& a : W.allies)
				if (a.handle != self && a.alive && a.visible && cheb(a.pos, g.center) <= 4)
					++vis;
			xm_pg = g.id;
			xm_pr = round;
			xm_p_my = dps_on(g);
			xm_p_ally = sp.ally_dps;
			xm_p_in = incoming_on(g);
			xm_p_share = sp.planned ? sp.share : -1.f;
			xm_p_share0 = sp.planned ? sp.share0 : -1.f;
			xm_p_reach = sp.reach;
			xm_p_pres = sp.present;
			xm_p_claim = sp.claimers;
			xm_p_live = live;
			xm_p_vis = vis;
			xm_p_near = near_in;
			xm_g_hp = g.hp_total;
			xm_p_clean = enemies_within(8) == 0;
			if (xm_ep.g == g.id && xm_ep.engage_r < 0)
				xm_ep.engage_r = round, xm_ep.hp0 = g.hp_total;
		}
	}
	xm_my_hp = hp;
}

void Brain::xm_fight(float adv, float tku, float tkt, float ohp, float thp, float odps, float tdps, int na, int ne, int fight, int killable, int in_reach,
					 int can_escape, int isolated, int reserve, int tgt_type, int tgt_d, float incoming, float t_die, float tgt_hp, int backup, float my_dps)
{
	// Split of the estimate: allies (visible within 6) and enemies remembered but not visible now (seen in the
	// last threat_memory rounds within 9 + age) that combat() does not count.
	auto& W = world();
	float a_hp = 0, a_dps = 0, m_hp = 0, m_dps = 0;
	int m_n = 0;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 6)
			a_hp += a.hp, a_dps += a.str + a.focus * best_mod(a.kit) / 8.f + std::max(a.str, a.focus * best_mod(a.kit)) / 3.f;
	for (const auto& e : W.enemies)
		if (e.alive && !e.visible && e.seen_round >= 0 && round - e.seen_round <= P.threat_memory && cheb(e.pos, pos) <= 9 + (round - e.seen_round) &&
			!W.enemy_spawn.is_set(e.pos))
			++m_n, m_hp += e.hp, m_dps += e.str + e.focus * best_mod(e.kit) / 8.f + e.burst() / 3.f;
	std::printf("FX r=%d ty=%d mydps=%.1f ahp=%.0f adps=%.1f mn=%d mhp=%.0f mdps=%.1f\n", round, static_cast<int>(type), my_dps, a_hp, a_dps, m_n, m_hp, m_dps);
	std::printf("FC r=%d ty=%d x=%d y=%d hp=%.0f mhp=%.0f gems=%u adv=%.3f tku=%.2f tkt=%.2f ohp=%.0f thp=%.0f odps=%.1f tdps=%.1f na=%d ne=%d fight=%d kill=%d reach=%d esc=%d iso=%d res=%d tt=%d td=%d inc=%.0f tdie=%.1f thp1=%.0f bk=%d sc=%.3f fm=%.2f\n",
		round, static_cast<int>(type), pos.x, pos.y, hp, max_hp, gems, adv, tku, tkt, ohp, thp, odps, tdps, na, ne, fight, killable, in_reach, can_escape, isolated, reserve, tgt_type, tgt_d,
		incoming, t_die, tgt_hp, backup, learner().fight_scale(), fight_margin);
}
#endif
