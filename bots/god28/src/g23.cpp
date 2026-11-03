// GOD v23 (the method: GOD_V23_METHOD.md). Fight engine (P.g23_fight), priority messages (P.g23_msg), farming through contact
// (always on since GOD v25) and g23_stage, team objective layer (P.g23_tol), the warden's ward (P.g23_ward). Everything here sits behind its switch;
// the hooks in brain.cpp are a few lines each.
#include "brain.h"
#include "nav.h"

#include <cmath>
#include <cstdio>

namespace
{
using CT = bc::champion_type;

// Private copies of brain.cpp's helpers (kept there in its anonymous namespace so the base's code generation, and so its fuel use, is
// unchanged with every g23 switch off).
float best_mod(const Kit& k)
{
	return std::max({ k.dmg >= 0 ? k.dmg_mod : 0.f, k.cc >= 0 ? k.cc_mod : 0.f, k.aoe >= 0 ? k.aoe_mod : 0.f, k.dash >= 0 ? k.dash_mod : 0.f });
}

int enemy_spell_reach(const Enemy& e, bool assume_ready)
{
	auto up = [&](int slot) { return slot >= 0 && (assume_ready || e.ready(slot)); };
	int r = (up(e.kit.dmg) || up(e.kit.cc) || up(e.kit.aoe)) ? 4 : 0;
	if (P.aoe_reach5 && up(e.kit.aoe))
		r = std::max(r, static_cast<int>(e.kit.aoe_range + e.kit.aoe_radius) + (e.kit.aoe_excl ? 0 : 1));
	if (P.aoe_reach5 >= 2)
	{
		if (up(e.kit.cc) && !e.kit.cc_excl)
			r = std::max(r, static_cast<int>(e.kit.cc_range) + 1);
		if (up(e.kit.dmg) && !e.kit.dmg_excl)
			r = std::max(r, static_cast<int>(e.kit.dmg_range) + 1);
	}
	return r;
}

// Next-turn reach of an enemy: attack range (+1 step for melee), +2 with a dash ready, its spells.
int enemy_reach(const Enemy& e)
{
	int r = e.kit.attack_range + (e.kit.ranged ? 0 : 1) + (e.ready(e.kit.dash) ? 2 : 0);
	if (P.aoe_reach5 && P.aoe_reach5 != 3)
		r = std::max(r, enemy_spell_reach(e, false));
	else if (e.ready(e.kit.dmg) || e.ready(e.kit.cc) || e.ready(e.kit.aoe))
		r = std::max(r, 4);
	return r;
}

int ally_reach(const Ally& a)
{
	return std::max(a.kit.attack_range + (a.kit.ranged ? 0 : 1) + (a.kit.dash >= 0 ? 2 : 0), (a.kit.dmg >= 0 || a.kit.cc >= 0 || a.kit.aoe >= 0) ? 4 : 0);
}

bool stun_ready(const Enemy& e) { return (e.kit.cc >= 0 && e.ready(e.kit.cc)) || (e.kit.aoe_stuns && e.ready(e.kit.aoe)); }
} // namespace

// ---------------------------------------------------------------------------------------------- fight engine (4.5)

// Damage a body deals per round in a fight: basic attack (x2 with a reset ready) + its best ready spell over 3 rounds; Heart of Ruin
// hits harder the lower it is; Varg's splash lands on the neighbours too.
float Brain::g23_dps_of(float str_, float focus_, const Kit& k, bool reset_ready, bool spell_ready, float hp_frac, CT t, bool enemy) const
{
	// over a 5-round exchange: the basic attack every round, one reset swing and one spell if they are up now (cooldowns are 8);
	// an enemy Marcella's enhanced reset also stuns (a round of our damage lost): x1.5
	float d = str_ * (reset_ready ? (enemy && t == CT::marcella ? 1.5f : 1.2f) : 1.f);
	if (spell_ready)
		d += focus_ * best_mod(k) / 5.f;
	if (t == CT_HOR)
		d *= 1.f + 0.5f * (1.f - std::clamp(hp_frac, 0.f, 1.f));
	if (t == CT::varg)
		d *= 1.2f;
	return std::max(1.f, d);
}

// Local power ratio R = sum of hp x dps of our bodies within g23_contact_r of the contact over the same for theirs. Bodies that cannot
// reach the contact within 2 rounds weigh g23_far_w; a committed ally (its priority message) always counts fully; enemies on their spawn
// weigh 0; a stunned enemy's damage is halved this round. reinf_*: bodies within 10 of the contact on each side.
float Brain::g23_ratio(vec2 contact, const std::vector<Enemy*>& E, int* new_enemy, int* reinf_us, int* reinf_them) const
{
	// R = (our health / their damage per round) / (their health / our damage per round): rounds they need to kill us over rounds we
	// need to kill them. Awake camps that hit us (we are their nearest champion) add to their damage.
	auto& W = world();
	const auto& C = comms();
	const int cr = P.g23_contact_r;
	const bool my_spell = ready(kit.dmg) || ready(kit.cc) || ready(kit.aoe) || (ready(kit.dash) && kit.dash_mod > 0.f);
	float our_hp = hp + ((P.fm_buffs & 1) ? my_shield : 0.f), our_dps = g23_dps_of(str, focus, kit, ready(kit.reset), my_spell, hp / max_hp, type, false);
	int ru = 1, rt = 0;
	for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
	{
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (i == W.my_index || !a.alive)
			continue;
		const auto k = static_cast<std::size_t>(i);
		const bool msg = P.g23_msg && i < 8 && round - g23_ally[k].round <= 1;
		const bool committed = msg && g23_ally[k].state >= 2;
		vec2 ap{ -1, -1 };
		if (a.visible)
			ap = a.pos;
		else if (i < 6 && C.claim[k] >= 0 && C.claim[k] < static_cast<int>(W.groups.size()))
			ap = W.groups[static_cast<std::size_t>(C.claim[k])].center;
		else if (round - a.seen_round <= 3)
			ap = a.pos;
		if (ap.x < 0)
			continue;
		const int d = cheb(ap, contact);
		if (d <= 10)
			++ru;
		if (d > cr || (a.visible && a.channeling))
			continue;
		if (!a.kit_ready)
			continue;
		float w = (committed || d <= ally_reach(a) + 2) ? 1.f : P.g23_far_w;
		if (!a.visible && !committed)
			w *= 0.5f;
		const float ahp = a.visible ? a.hp : msg ? static_cast<float>(g23_ally[k].hpb + 0.5f) / 16.f * a.max_hp : 0.5f * a.max_hp;
		// allies' cooldowns are not stored: half a spell on average
		our_hp += w * ahp;
		our_dps += w * g23_dps_of(a.str, 0.5f * a.focus, a.kit, false, true, ahp / std::max(1.f, a.max_hp), a.type, false);
	}
	float their_hp = 0, their_dps = 0;
	int mask = 0;
	bool marc_stun = false; // an enemy Marcella with her reset up stands within 2 of the contact
	for (auto* e : E)
	{
		const int d = cheb(e->pos, contact);
		if (d <= 10)
			++rt;
		if (d > cr || W.enemy_spawn.is_set(e->pos))
			continue;
		const int idx = static_cast<int>(e - W.enemies.data());
		if (idx >= 0 && idx < 8)
			mask |= 1 << idx;
		const float w = d <= enemy_reach(*e) + 2 ? 1.f : P.g23_far_w;
		const bool sp = e->ready(e->kit.dmg) || e->ready(e->kit.cc) || e->ready(e->kit.aoe) || (e->ready(e->kit.dash) && e->kit.dash_mod > 0.f);
		float dps = g23_dps_of(e->str, e->focus, e->kit, e->ready(e->kit.reset), sp, e->hp / std::max(1.f, e->max_hp), e->type, true);
		if ((P.fm_buffs & 2) && e->stunned)
			dps *= 0.5f;
		// her reset (cooldown read every round she is visible, world.cpp) is up within 2 of the contact: its stun costs our side a round
		if (e->type == CT::marcella && d <= 2 && e->ready(e->kit.reset))
			marc_stun = true;
		their_hp += w * (e->hp + ((P.fm_buffs & 1) ? e->shield : 0.f));
		their_dps += w * dps;
	}
	// Seen a round or two ago, out of sight now (a bush, a corner): still there at half weight.
	for (const auto& e : W.enemies)
		if (e.alive && !e.visible && e.seen_round >= 0 && round - e.seen_round <= 2 && !W.enemy_spawn.is_set(e.pos))
		{
			const int d = cheb(e.pos, contact);
			if (d <= 10)
				++rt;
			if (d > cr)
				continue;
			their_hp += 0.5f * e.hp;
			their_dps += 0.5f * g23_dps_of(e.str, 0.5f * e.focus, e.kit, false, true, e.hp / std::max(1.f, e.max_hp), e.type, true);
		}
	// awake camps hitting us: the nearest champion within their range (no ally nearer); an enemy nearer takes them instead
	for (const auto& g : W.groups)
	{
		if (g.st != ST_ALIVE || !g.awake || g.harmless || cheb(g.center, pos) > 8)
			continue;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (g.hp[i] <= 0 || g.camps[i].str <= 0)
				continue;
			const vec2 c = g.camps[i].pos;
			const int dm = cheb(c, pos);
			if (dm > std::max(3, g.camps[i].range))
				continue;
			bool nearer = false;
			for (const auto& a : W.allies)
				if (a.handle != self && a.alive && a.visible && cheb(a.pos, c) < dm)
					nearer = true;
			for (auto* e : E)
				if (cheb(e->pos, c) < dm)
					nearer = true;
			if (!nearer)
				their_dps += g.camps[i].str;
		}
	}
	if (new_enemy)
		*new_enemy = (mask & ~g23_emask) != 0;
	if (reinf_us)
		*reinf_us = ru;
	if (reinf_them)
		*reinf_them = rt;
	g23_emask_now = mask;
	if (marc_stun)
		our_dps *= 0.85f; // her stun takes a round off our damage
	if (their_hp <= 0.f || their_dps <= 0.f)
		return 99.f;
	const float t_us = our_hp / their_dps, t_them = their_hp / std::max(1.f, our_dps);
	return t_us / std::max(0.1f, t_them);
}

// Can we get away? A melee chaser (3, +2 with a dash ready) or a ready stun within 4 follows and hits every round; then only our own
// dash (theirs down), our spawn, or a walk to spawn / an ally shorter than the rounds we survive makes leaving a real option.
bool Brain::g23_escape_test(const std::vector<Enemy*>& E, float incoming) const
{
	auto& W = world();
	if (W.ally_spawn.is_set(pos))
		return true;
	bool chaser = false, chaser_dash = false;
	for (auto* e : E)
	{
		if (W.enemy_spawn.is_set(e->pos))
			continue;
		const int d = cheb(e->pos, pos);
		if (!e->kit.ranged && d <= 3 + (e->ready(e->kit.dash) ? 2 : 0))
			chaser = true, chaser_dash |= e->ready(e->kit.dash);
		else if (d <= 4 && stun_ready(*e))
			chaser = true;
		else if (e->kit.ranged && e->ready(e->kit.dash) && d <= 4)
			chaser = true, chaser_dash = true;
	}
	if (!chaser)
		return true;
	if (ready(kit.dash) && !chaser_dash)
		return true;
	const float t_die = hp / std::max(1.f, incoming);
	const int dh = W.dist_home(pos);
	if (dh < BIG && static_cast<float>(dh) + 1.f < t_die)
		return true;
	int da = BIG;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && !a.channeling && a.hp >= 0.4f * a.max_hp && cheb(a.pos, pos) >= 2)
			da = std::min(da, cheb(a.pos, pos) - 1);
	return da < BIG && static_cast<float>(da) + 1.f < t_die;
}

// Team target: the enemy in reach that dies soonest to what the team lands on it this round (+200 health credit for stunned,
// channelling, Cassi / Issac and carriers); an ally's broadcast target first; never one on its spawn.
Enemy* Brain::g23_pick_target(std::vector<Enemy*>& E, Enemy* fallback) const
{
	auto& W = world();
	const bool spell_up = ready(kit.dmg) || ready(kit.cc) || ready(kit.aoe);
	const int my_reach = kit.attack_range + (kit.ranged ? 0 : 1) + (ready(kit.dash) ? 2 : 0);
	const int aoe_r5 = P.aoe_cast5 && ready(kit.aoe) ? static_cast<int>(kit.aoe_range + kit.aoe_radius) : 0;
	int focus_idx = -1;
	if (P.g23_msg)
		for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
		{
			const auto& m = g23_ally[static_cast<std::size_t>(i)];
			if (i != W.my_index && round - m.round <= 1 && m.state >= 2 && m.target >= 0)
			{
				focus_idx = m.target;
				break;
			}
		}
	Enemy* best = nullptr;
	float bk = 1e30f;
	for (auto* e : E)
	{
		const int d = cheb(pos, e->pos);
		const bool spell_r = (spell_up && d <= 4) || d <= aoe_r5;
		if ((d > my_reach && !spell_r) || W.enemy_spawn.is_set(e->pos))
			continue;
		if (e->type == CT::ren)
		{
			const float reflect = bc::constants::passive_abilities::ren_retaliation_focus_ratio * e->focus;
			if (hp < 3.f * reflect && e->hp > burst_vs(*e))
				continue;
		}
		float mine = d <= my_reach && can_attack ? str * (ready(kit.reset) ? 2.f : 1.f) : 0.f;
		if (spell_r)
			mine += d > 4 ? focus * kit.aoe_mod : std::max({ ready(kit.dmg) ? focus * kit.dmg_mod : 0.f, ready(kit.cc) ? focus * kit.cc_mod : 0.f, ready(kit.aoe) ? focus * kit.aoe_mod : 0.f });
		float allies_d = 0;
		for (const auto& a : W.allies)
			if (a.handle != self && a.alive && a.visible && a.kit_ready && !a.channeling && cheb(a.pos, e->pos) <= std::max(a.kit.attack_range + 1, 4))
				allies_d += (cheb(a.pos, e->pos) <= a.kit.attack_range + 1 ? a.str : 0.f) + 0.5f * a.focus * best_mod(a.kit);
		const float ehp = e->hp + ((P.fm_buffs & 1) ? e->shield : 0.f);
		float bonus = 0;
		if ((P.fm_buffs & 2) && e->stunned)
			bonus += 200.f;
		if (e->channeling)
			bonus += 200.f;
		if (e->type == CT::cassi || e->type == CT::issac)
			bonus += 200.f;
		if (e->gems >= 20)
			bonus += 200.f;
		float key = (ehp - bonus) / std::max(1.f, mine + allies_d);
		if (ehp <= mine + allies_d)
			key -= 1e6f;
		if (static_cast<int>(e - W.enemies.data()) == focus_idx)
			key -= 500.f;
		if (key < bk)
			bk = key, best = e;
	}
	return best ? best : fallback;
}

// The decision. Returns the state; `tgt` may change to the team target.
int Brain::g23_decide(std::vector<Enemy*>& E, Enemy*& tgt, float allies_burst, bool in_reach, float incoming)
{
	auto& W = world();
	const bool on_spawn = W.ally_spawn.is_set(pos);
	const int my_reach = kit.attack_range + (kit.ranged ? 0 : 1) + (ready(kit.dash) ? 2 : 0);
	const int aoe_r5 = P.aoe_cast5 && ready(kit.aoe) ? static_cast<int>(kit.aoe_range + kit.aoe_radius) : 0;
	auto kill_now = [&](const Enemy& e) {
		const int d = cheb(pos, e.pos);
		const float ehp = e.hp + ((P.fm_buffs & 1) ? e.shield : 0.f);
		bool k = d <= std::max(my_reach, (ready(kit.dmg) || ready(kit.cc)) ? 4 : 0) && ehp <= burst_vs(e) + allies_burst;
		if (!k && aoe_r5 > 0 && d <= aoe_r5)
			k = ehp <= (d <= kit.attack_range && can_attack ? str : 0.f) + focus * kit.aoe_mod + allies_burst;
		return k && !W.enemy_spawn.is_set(e.pos);
	};
	const bool prev_fresh = g23_round == round - 1;
	const bool prev_fight = prev_fresh && g23_state >= G23_FIGHT;
	const bool prev_avoid = prev_fresh && (g23_state == G23_AVOID || g23_state == G23_LEAVE);
	// A committed target still here keeps the focus (unless another one dies now).
	Enemy* committed = nullptr;
	if (prev_fight && g23_tgt_idx >= 0 && g23_tgt_idx < static_cast<int>(W.enemies.size()))
		for (auto* e : E)
			if (e == &W.enemies[static_cast<std::size_t>(g23_tgt_idx)])
				committed = e;
	if (Enemy* t2 = g23_pick_target(E, committed ? committed : tgt))
		tgt = t2;
	bool killable = kill_now(*tgt);
	if (committed && !killable && tgt != committed)
		tgt = committed, killable = kill_now(*tgt);
	int new_e = 0, ru = 0, rt = 0;
	const float R = g23_ratio(tgt->pos, E, &new_e, &ru, &rt);
	const bool escape = g23_escape_test(E, incoming);
	bool ally_fight = false;
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
	{
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (i == W.my_index || !a.alive || !a.visible || cheb(a.pos, pos) > 6)
			continue;
		const auto& m = g23_ally[static_cast<std::size_t>(i)];
		if ((P.g23_msg && round - m.round <= 1 && m.state >= 2) || (P.ally_defend && a.hit_round == round && cheb(a.pos, tgt->pos) <= 4))
			ally_fight = true;
	}
	const bool tgt_spawn = W.enemy_spawn.is_set(tgt->pos) || cheb(tgt->pos, W.enemy_spawn_c) <= 3;
	const bool low = hp < P.g23_low_hp * max_hp;
	bool fight = killable || !escape || (on_spawn && in_reach) || (R >= P.g23_r_engage && rt <= ru) || (ally_fight && R >= P.g23_r_join);
	if (fight && !killable && escape && !on_spawn)
	{
		if (static_cast<int>(gems) >= P.g23_bag_caution && R < P.g23_bag_r)
			fight = false; // the bag is worth more than this fight
		if (P.win_bank && gems > 0 && wins_with(static_cast<int>(gems)))
			fight = false;
		if (low)
			fight = false;
	}
	if (fight && !killable && tgt_spawn)
		fight = false; // never dive their spawn: it heals them every round
	const int td = cheb(pos, tgt->pos);
	if (fight && !killable && td > my_reach && !in_reach && !tgt->channeling && !tgt->tributing)
	{
		// a target we have to walk to: never deeper into their half, and never a chase that does not close (4 rounds without the
		// distance shrinking: it kites; leave it alone for 15 rounds)
		if (W.dist_away(tgt->pos) < BIG && W.dist_home(tgt->pos) < BIG && W.dist_away(tgt->pos) + 4 < W.dist_home(tgt->pos))
			fight = false;
		const int ti = static_cast<int>(tgt - W.enemies.data());
		if (ti >= 0 && ti < 8 && round < g23_chase_off[static_cast<std::size_t>(ti)])
			fight = false;
	}
	bool lure = false;
	if (!killable && td > my_reach && !in_awake_camp_range() && camp_danger.is_set(tgt->pos))
		lure = true; // it stands inside an awake camp's reach and we do not: walking in feeds the camp (the lure)
	if (fight && lure)
		fight = false;
	if (fight && !killable && !ally_fight && !in_reach && td > my_reach + 1 && !tgt->channeling && !tgt->tributing)
		fight = false; // starting a fight: one step at most; a target farther away is not walked to (70% of our deaths followed 2+ approach steps)
	if (prev_fight && !fight && round - g23_since < P.g23_fight_hold)
	{
		const bool release = !committed || (low && escape) || R < P.g23_r_release || tgt_spawn || lure || (td > my_reach + 1 && g23_chase_n >= 3);
		if (!release)
			fight = true;
	}
	if (prev_avoid && fight && round - g23_since < P.g23_avoid_hold && !killable && escape && !on_spawn && !ally_fight)
		fight = false;
	if (fight && !killable && td > my_reach)
	{
		const int ti = static_cast<int>(tgt - W.enemies.data());
		if (g23_chase_h != tgt->handle || round - g23_chase_round > 1)
			g23_chase_h = tgt->handle, g23_chase_best = td, g23_chase_n = 0;
		else if (td < g23_chase_best)
			g23_chase_best = td, g23_chase_n = 0;
		else
			++g23_chase_n;
		g23_chase_round = round;
		if (g23_chase_n >= 4 && ti >= 0 && ti < 8)
		{
			g23_chase_off[static_cast<std::size_t>(ti)] = round + 15;
			fight = false;
		}
	}
	const int st = fight ? (killable ? G23_KILL : G23_FIGHT) : (in_reach ? G23_LEAVE : G23_AVOID);
	if (!prev_fresh || (st >= G23_FIGHT) != (g23_state >= G23_FIGHT))
		g23_since = round;
	g23_state = st;
	g23_round = round;
	g23_R = R;
	g23_escape = escape;
	g23_tgt_idx = fight ? static_cast<int>(tgt - W.enemies.data()) : -1;
	g23_emask = g23_emask_now;
#ifdef G23_TRACE
	std::printf("FE r=%d ch=%d st=%d R=%.2f esc=%d kill=%d inr=%d ru=%d rt=%d af=%d tgt=%d d=%d hp=%.2f\n", round, static_cast<int>(type), st, R, static_cast<int>(escape),
		static_cast<int>(killable), static_cast<int>(in_reach), ru, rt, static_cast<int>(ally_fight), g23_tgt_idx, cheb(pos, tgt->pos), hp / max_hp);
#endif
	return st;
}

// Mode 2 (P.g23_fight 2): v75's `fight` decision, then the v23 vetoes and the second-wave join.
bool Brain::g23_veto(std::vector<Enemy*>& E, Enemy*& tgt, bool fight, bool killable, bool in_reach, float adv, int d, int my_reach)
{
	auto& W = world();
	bool ally_fight = false;
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
	{
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (i == W.my_index || !a.alive || !a.visible || cheb(a.pos, pos) > 6)
			continue;
		const auto& m = g23_ally[static_cast<std::size_t>(i)];
		if ((P.g23_msg && round - m.round <= 1 && m.state >= 2) || (P.ally_defend && a.hit_round == round && cheb(a.pos, tgt->pos) <= 4))
			ally_fight = true;
	}
	const bool tgt_spawn = W.enemy_spawn.is_set(tgt->pos) || cheb(tgt->pos, W.enemy_spawn_c) <= 3;
	// second wave: an ally next to us is in a fight: join it at the join bar (focus its target when it is in reach)
	if ((P.g23_veto_bits & 16) && !fight && ally_fight && !killable && adv >= P.g23_r_join && !tgt_spawn && !in_reach && d <= 6 && hp >= 0.35f * max_hp)
	{
		fight = true;
		if (Enemy* t2 = g23_pick_target(E, tgt))
			tgt = t2;
	}
	// rescue (bit 64): an ally within 4 is caught (an enemy can hit it now and a melee / dash chaser is within 2 of it: it cannot walk
	// away) and we are healthy: turn and fight for it when our bodies there (it, us, the healthy allies within 4 of it) are not fewer than
	// their bodies within 4 of it. Ladder crater losses: a chased Heart of Ruin died to 3 enemies over 7 rounds while a full-health Ryth
	// next to it and a Marcella 4 tiles away walked away with the team (each body's flee decision was right for itself).
	bool rescued = false;
	if ((P.g23_veto_bits & 64) && !fight && !killable && hp >= P.g23_rescue_hp * max_hp)
	{
		Enemy* best_t = nullptr;
		float best_h = 1e30f;
		for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
		{
			const auto& a = W.allies[static_cast<std::size_t>(i)];
			if (i == W.my_index || !a.alive || !a.visible || a.channeling || cheb(a.pos, pos) > P.g23_rescue_r || a.hp < 0.15f * a.max_hp)
				continue;
			bool hit_now = false, chased = false;
			for (auto* e : E)
			{
				if (W.enemy_spawn.is_set(e->pos))
					continue;
				const int de = cheb(e->pos, a.pos);
				hit_now |= de <= e->kit.attack_range + (e->kit.ranged ? 0 : 1);
				chased |= (!e->kit.ranged || e->ready(e->kit.dash)) && de <= 2;
			}
			if (!hit_now || !chased)
				continue;
			int n_en = 0, n_us = 1; // us + the healthy allies within 4 of it (it included)
			for (auto* e : E)
				n_en += !W.enemy_spawn.is_set(e->pos) && cheb(e->pos, a.pos) <= 4;
			for (int j = 0; j < static_cast<int>(W.allies.size()); ++j)
			{
				const auto& b = W.allies[static_cast<std::size_t>(j)];
				if (j != W.my_index && b.alive && b.visible && !b.channeling && cheb(b.pos, a.pos) <= 4 && b.hp >= 0.3f * b.max_hp)
					++n_us;
			}
			if (n_en > n_us)
				continue;
			// F2 g24_rescue_pw: bodies are not power (a fed carry counts as one): our health x damage at the ally against theirs
			if (g23_ratio(a.pos, E, nullptr, nullptr, nullptr) < P.g23_r_join)
				continue;
			// the enemy on it that we can reach soonest, lowest health first
			for (auto* e : E)
			{
				if (W.enemy_spawn.is_set(e->pos) || cheb(e->pos, a.pos) > 2 || cheb(e->pos, pos) > my_reach + 2)
					continue;
				const float h = e->hp + 50.f * static_cast<float>(cheb(e->pos, pos));
				if (h < best_h)
					best_h = h, best_t = e;
			}
		}
		if (best_t)
			fight = true, rescued = true, tgt = best_t;
	}
	if (fight && !killable)
	{
		// F4 g24_lure: a target inside an awake camp's reach while we stand outside it is a lure, rescues included (deaths to camps the enemy
		// woke 0.96 a game vs 0.20; 73% walked in); the veto holds 3 rounds on that target
		const bool lure24 = cheb(pos, tgt->pos) > my_reach && !in_awake_camp_range() && camp_danger.is_set(tgt->pos);
		if (lure24)
			g24_lure_h = tgt->handle, g24_lure_until = round + 3;
		if (lure24 || (g24_lure_h == tgt->handle && round < g24_lure_until && !in_reach))
			fight = false, rescued = false;
	}
	if (P.g23_veto_bits & 128)
		g23_rescue_now = rescued; // read by combat() right after this call (bit 128: the rescue commits)
	const int td = cheb(pos, tgt->pos);
	bool lure = false;
	if (!killable && !rescued && td > my_reach && !in_awake_camp_range() && camp_danger.is_set(tgt->pos))
		lure = true;
	if (fight && lure && (P.g23_veto_bits & 1))
		fight = false;
	if ((P.g23_veto_bits & 2) && fight && !killable && !ally_fight && !rescued && !in_reach && td > my_reach + 1 && !tgt->channeling && !tgt->tributing)
		fight = false; // one approach step at most
	if (fight && !killable && td > my_reach && !in_reach && !tgt->channeling && !tgt->tributing)
	{
		if ((P.g23_veto_bits & 8) && W.dist_away(tgt->pos) < BIG && W.dist_home(tgt->pos) < BIG && W.dist_away(tgt->pos) + 4 < W.dist_home(tgt->pos))
			fight = false; // deeper into their half
		const int ti = static_cast<int>(tgt - W.enemies.data());
		if ((P.g23_veto_bits & 4) && ti >= 0 && ti < 8 && round < g23_chase_off[static_cast<std::size_t>(ti)])
			fight = false;
	}
	if ((P.g23_veto_bits & 4) && fight && !killable && td > my_reach)
	{
		const int ti = static_cast<int>(tgt - W.enemies.data());
		if (g23_chase_h != tgt->handle || round - g23_chase_round > 1)
			g23_chase_h = tgt->handle, g23_chase_best = td, g23_chase_n = 0;
		else if (td < g23_chase_best)
			g23_chase_best = td, g23_chase_n = 0;
		else
			++g23_chase_n;
		g23_chase_round = round;
		if (g23_chase_n >= 4 && ti >= 0 && ti < 8)
		{
			g23_chase_off[static_cast<std::size_t>(ti)] = round + 15;
			fight = false;
		}
	}
	// disengage (bit 256, ladder P2): the trade turned; leave now (v75's flee / avoid takes over) unless our attack kills this turn
	if ((P.g23_veto_bits & 256) && fight && !killable && !rescued && !tgt->channeling && !tgt->tributing)
	{
		bool spell_near = false;
		float burst = 0;
		for (auto* e : E)
		{
			if (W.enemy_spawn.is_set(e->pos))
				continue;
			const int de = cheb(e->pos, pos);
			const bool sp = e->ready(e->kit.dash) || e->ready(e->kit.cc) || e->ready(e->kit.dmg) || (e->kit.aoe_stuns && e->ready(e->kit.aoe));
			spell_near |= de <= 4 && sp;
			int reach = e->kit.attack_range + (e->kit.ranged ? 0 : 1) + (e->ready(e->kit.dash) ? 2 : 0);
			if (e->ready(e->kit.dmg) || e->ready(e->kit.cc) || e->ready(e->kit.aoe))
				reach = std::max(reach, 4);
			if (de <= reach)
				burst += e->str * (e->ready(e->kit.reset) ? 2.f : 1.f) + e->burst();
		}
		if (hp < P.g23_dis_hp * max_hp || (spell_near && hp < P.g23_dis_spell_hp * max_hp) || burst >= hp)
			fight = false;
	}
	g23_state = fight ? (killable ? G23_KILL : G23_FIGHT) : (in_reach ? G23_LEAVE : G23_AVOID);
	g23_round = round;
	g23_R = adv;
	g23_tgt_idx = fight ? static_cast<int>(tgt - W.enemies.data()) : -1;
#ifdef G23_TRACE
	std::printf("FE r=%d ch=%d st=%d R=%.2f esc=%d kill=%d inr=%d ru=0 rt=%d af=%d tgt=%d d=%d hp=%.2f\n", round, static_cast<int>(type), g23_state, adv, 1,
		static_cast<int>(killable), static_cast<int>(in_reach), static_cast<int>(E.size()), static_cast<int>(ally_fight), g23_tgt_idx, td, hp / max_hp);
#endif
	return fight;
}

// LEAVE: a melee swings at an adjacent enemy first (it moves and attacks); a stun on the chaser that would still hit us after our step;
// then one step toward the nearest healthy ally out of every enemy's reach, else toward spawn; cornered: hit back.
bool Brain::g23_leave(std::vector<Enemy*>& E, Enemy& tgt)
{
	auto& W = world();
	post_danger(tgt.pos);
	task = T_FLEE;
	if (P.g23_divefilter || P.g23_campzone)
		g_hard_block = nullptr; // leaving keeps every step open
	avoid_note(E); // v27_avoid: groups near them are no target for a while
	g23_leave_round = round;
	if (!kit.ranged && can_attack)
		if (Enemy* o = best_in_reach(nullptr))
			attack_unit(*o->ch);
	// a stun usable while walking: on the closest chaser, then step
	for (auto* e : E)
		if (e->ch && kit.cc >= 0 && !kit.cc_excl && ready(kit.cc) && e->type != CT::marcella && (!e->kit.ranged || e->ready(e->kit.dash)) &&
			cheb(pos, e->pos) <= static_cast<int>(kit.cc_range))
		{
			cast_unit_champ(kit.cc, *e->ch);
			break;
		}
	if (!cast_done && W.dist_home(pos) > 2 && ((kit.cc >= 0 && kit.cc_excl && ready(kit.cc)) || (kit.aoe_stuns && ready(kit.aoe))))
	{
		// a walk-exclusive stun costs the step, but a chaser whose hit reaches us after that step gains nothing from it: deny its turn
		Enemy* ch = nullptr;
		int bd = BIG;
		for (auto* e : E)
		{
			if (!e->ch || e->type == CT::marcella || W.enemy_spawn.is_set(e->pos))
				continue;
			const int dd = cheb(pos, e->pos);
			const int hit_reach = e->kit.attack_range + (e->kit.ranged ? 0 : 1) + (e->ready(e->kit.dash) ? 2 : 0);
			if (dd + 1 <= hit_reach && dd < bd)
				bd = dd, ch = e;
		}
		if (ch)
		{
			const bool cc_ok = kit.cc >= 0 && kit.cc_excl && bd <= static_cast<int>(kit.cc_range) && cast_unit_champ(kit.cc, *ch->ch);
			if (cc_ok || (kit.aoe_stuns && ready(kit.aoe) && cast_area_stun_at(*ch)))
			{
				if (!kit.ranged && can_attack && bd <= kit.attack_range)
					attack_unit(*ch->ch);
				return true;
			}
		}
	}
	auto swing = [&] {
		if (!kit.ranged && can_attack)
			for (auto* e : E)
				if (e->ch && cheb(pos, e->pos) <= kit.attack_range)
				{
					attack_unit(*e->ch);
					break;
				}
	};
	vec2 help{ -1, -1 };
	int hd = BIG;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && !a.channeling && a.hp >= 0.4f * a.max_hp && cheb(a.pos, pos) >= 2 && cheb(a.pos, pos) <= 12 && cheb(a.pos, pos) < hd)
			hd = cheb(a.pos, pos), help = a.pos;
	if (help.x >= 0)
	{
		bc::bitboard goal;
		goal.draw_chebyshev(help, 1.f);
		goal &= ~W.walls & ~danger;
		const bc::bitboard g2 = goal & ~camp_danger;
		if (!g2.is_empty())
			goal = g2;
		if (!goal.is_empty() && step(goal, true, true))
		{
			swing();
			return true;
		}
	}
	// home, but not through an awake camp's reach when a step out of every reach exists
	{
		bc::bitboard out = ~danger & ~camp_danger & ~W.walls;
		bc::bitboard ring;
		ring.draw_chebyshev(pos, 1.f);
		out &= ring;
		if (!out.is_empty() && W.dist_home(pos) < BIG)
		{
			// among the safe neighbours, the one nearest home
			vec2 best{ -1, -1 };
			int bd = W.dist_home(pos);
			const bc::bitboard blocked = Nav::blocked_now(pos);
			for (int dy = -1; dy <= 1; ++dy)
				for (int dx = -1; dx <= 1; ++dx)
				{
					const vec2 q{ pos.x + dx, pos.y + dy };
					if ((dx == 0 && dy == 0) || !bc::map::is_in_bounds(q) || !out.is_set(q) || blocked.is_set(q))
						continue;
					const int dq = W.dist_home(q);
					if (dq < bd)
						bd = dq, best = q;
				}
			if (best.x >= 0)
			{
				bc::bitboard gq;
				gq.set(best);
				if (step(gq, false, false))
				{
					swing();
					return true;
				}
			}
		}
	}
	if (go_home_step(true))
	{
		swing();
		return true;
	}
	return engage(tgt);
}

// ---------------------------------------------------------------------------------------------- messages (4.9)

// priority = (turn class + 16) x 4096 + hp bucket x 256 + state x 64 + (target index + 1) x 4 + flags. The turn class keeps v75's order
// (escapers, then fighters, captures, idle); the rest is a message every ally that sees us reads with query_priority.
void Brain::g23_set_priority()
{
	int base = P.prio_idle;
	if (g23_round == round && g23_state == G23_LEAVE)
		base = 12;
	else if (engaged || task == T_FIGHT || task == T_FLEE)
		base = 8 + ((kit.cc >= 0 || kit.aoe_stuns) ? 1 : 0) + (hp < 0.35f * max_hp ? 1 : 0);
	else if (task == T_CAPTURE)
		base = P.prio_capture;
	const int hpb = std::clamp(static_cast<int>(hp / std::max(1.f, max_hp) * 15.99f), 0, 15);
	const int st = g23_round == round ? (g23_state == G23_KILL ? 3 : g23_state == G23_FIGHT ? 2 : g23_state == G23_NONE ? 0 : 1) : 0;
	const int tg = g23_round == round && g23_tgt_idx >= 0 && g23_tgt_idx < 15 ? g23_tgt_idx + 1 : 0;
	const int flags = (st >= 2 ? 1 : 0) | (task == T_CAPTURE ? 2 : 0);
	const int prio = (std::clamp(base, -16, 15) + 16) * 4096 + hpb * 256 + st * 64 + tg * 4 + flags;
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

void Brain::g23_read_allies()
{
	auto& W = world();
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
	{
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (i == W.my_index || !a.alive || !a.visible)
			continue;
		std::int32_t v = 0;
		if (bc::detail::sdk_bc_champion_priority(a.handle, 1, &v) != 0 || v < 4096)
			continue;
		auto& m = g23_ally[static_cast<std::size_t>(i)];
		m.round = round;
		m.turn_class = v / 4096 - 16;
		m.hpb = (v / 256) & 15;
		m.state = (v / 64) & 3;
		m.target = ((v / 4) & 15) - 1;
		m.flags = v & 3;
	}
}

// ---------------------------------------------------------------------------------------------- farming through contact (4.4)

// Synchronized arrival: an ally claims this group and is still on its way; we are not able to clear it alone within g23_stage_solo
// rounds: wait at staging distance until the last such ally is within 2 rounds (at most g23_stage_max rounds). Camps hit the nearest
// champion from the first hit on: two bodies arriving 13 rounds apart (today's median) means one body tanks alone twice.
bool Brain::g23_stage(Group& g)
{
	auto& W = world();
	auto& C = comms();
	if (g.harmless || g.st != ST_ALIVE || g.awake)
		return false;
	if (g.hp_total / std::max(10.f, dps_on(g)) <= static_cast<float>(P.g23_stage_solo))
		return false;
	const int stage_d = std::max(3, g.max_range + 2);
	const int my_d = nav().group_dist(g, pos);
	if (my_d > stage_d + 1)
		return false; // still walking
	int coming = 0, here = 0;
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
	{
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (i == W.my_index || !a.alive || C.claim[static_cast<std::size_t>(i)] != g.id)
			continue;
		if (a.visible)
		{
			const int d = nav().group_dist(g, a.pos);
			if (d <= stage_d + 2)
				++here;
			else
				++coming;
		}
		else if (round - a.seen_round <= 10 && nav().group_dist(g, a.pos) <= 14)
			++coming;
	}
	if (coming == 0)
		return false;
	if (g23_stage_g != g.id || round - g23_stage_since > 60)
		g23_stage_g = g.id, g23_stage_since = round;
	if (round - g23_stage_since > P.g23_stage_max)
		return false;
	task = T_WAIT;
	if (my_d < stage_d)
	{
		// too close: out of the camps' reach
		bc::bitboard out = ~g.near & ~W.walls;
		step(out, true, false);
		return true;
	}
	if (my_d > stage_d)
		go_group(g, stage_d, true);
	return true;
}

// ---------------------------------------------------------------------------------------------- team objective layer (4.3)

float Brain::g23_team_dps() const
{
	auto& W = world();
	float d = 0;
	for (const auto& a : W.allies)
	{
		const auto ti = static_cast<std::size_t>(a.type);
		if (ti >= bc::champion_designs.size())
			continue;
		const auto bs = bc::champion_designs[ti].base_stats();
		d += static_cast<float>(bs.base_strength) + static_cast<float>(bs.base_focus) * best_mod(kit_of(bc::champion_designs[ti])) / 8.f;
	}
	return std::max(1.f, d);
}

// Prime set: value = gems + 0.15 gold; value >= g23_prime_share x max or gems >= g23_prime_gems; dA <= dB + g23_prime_margin (we reach it no
// later than they do, give or take); no monoliths; sorted by value, capped. Per prime: force F, the rally tile (our side, out of every camp's
// reach, most camps within 4, a bush first), the nearest altar.
void Brain::g23_tol_init()
{
	auto& W = world();
	g23_tol_ready = true;
	g23_nprime = 0;
	float vmax = 0;
	auto value = [](const Group& g) { return static_cast<float>(g.gems) + 0.15f * static_cast<float>(g.gold); };
	for (const auto& g : W.groups)
		if (!g.monolith && g.d_ally < BIG)
			vmax = std::max(vmax, value(g));
	if (vmax <= 0.f)
		return;
	const float team_dps = g23_team_dps();
	const int cap = std::min(P.g23_prime_cap, W.team_champs <= 3 ? 2 : 3);
	std::vector<std::pair<float, int>> cand;
	for (const auto& g : W.groups)
	{
		if (g.monolith || g.d_ally >= BIG || g.d_enemy >= BIG)
			continue;
		const float v = value(g);
		if (v < P.g23_prime_share * vmax && g.gems < P.g23_prime_gems)
			continue;
		if (g.d_ally > g.d_enemy + P.g23_prime_margin)
			continue;
		if (g.d_ally > P.g23_prime_maxd || static_cast<float>(g.gems) < P.g23_prime_perstep * static_cast<float>(std::max(1, g.d_ally)))
			continue; // too far for its value: a cycle there costs more farming than it pays (ambush: 51 gems at 73 steps)
		if (g.max_hp / team_dps > 40.f)
			continue; // the whole team cannot clear it in 40 rounds: not a cycle target
		cand.push_back({ -v, g.id });
	}
	std::sort(cand.begin(), cand.end());
	const auto& B = bc::map::bushes();
	for (const auto& c : cand)
	{
		if (g23_nprime >= cap)
			break;
		const auto& g = W.groups[static_cast<std::size_t>(c.second)];
		Prime p;
		p.g = g.id;
		// force: bodies that clear it within g23_force_rounds at the team's mean damage per body
		const float per_body = team_dps / static_cast<float>(std::max(1, static_cast<int>(W.allies.size())));
		p.force = std::clamp(static_cast<int>(std::ceil(g.max_hp / (per_body * static_cast<float>(P.g23_force_rounds)))), 2, g.gems > 80 ? static_cast<int>(W.allies.size()) : std::min(3, static_cast<int>(W.allies.size())));
		if (g.gems > 80)
			p.force = std::max(p.force, 4);
		// rally tile
		const int reach = std::max(3, g.max_range + 1);
		int best = -1;
		for (int dy = -(g.radius + reach + 1); dy <= g.radius + reach + 1; ++dy)
			for (int dx = -(g.radius + reach + 1); dx <= g.radius + reach + 1; ++dx)
			{
				const vec2 t{ g.center.x + dx, g.center.y + dy };
				if (!bc::map::is_in_bounds(t) || W.walls.is_set(t) || g.mask.is_set(t) || W.dist_home(t) >= BIG)
					continue;
				bool ok = true;
				int within4 = 0;
				for (const auto& cm : g.camps)
				{
					const int d = cheb(t, cm.pos);
					if (d <= std::max(cm.range, 3))
						ok = false;
					within4 += d <= 4;
				}
				if (!ok || within4 == 0)
					continue;
				if (W.dist_home(t) > W.dist_away(t) + 2)
					continue; // their side
				int s = within4 * 10 + (B.is_set(t) ? 15 : 0) - std::min(9, cheb(t, g.center));
				if (s > best)
					best = s, p.rally = t;
			}
		if (p.rally.x < 0)
			continue;
		int ad = BIG;
		for (std::size_t a = 0; a < W.altars.size(); ++a)
			if (!W.altar_approach[a].empty())
			{
				const int d = cheb(W.altars[a], g.center);
				if (d < ad)
					ad = d, p.altar = static_cast<int>(a);
			}
		g23_prime[static_cast<std::size_t>(g23_nprime++)] = p;
	}
	// Opening: we reach P0 no later than they do (+ margin): everyone to P0 first.
	if (g23_nprime > 0)
	{
		const auto& g0 = W.groups[static_cast<std::size_t>(g23_prime[0].g)];
		if (g0.d_ally <= g0.d_enemy + P.g23_open_margin && g0.d_ally <= P.g23_open_maxd)
			g23_open_until = g0.d_ally + 30;
	}
#ifdef G23_TRACE
	for (int i = 0; i < g23_nprime; ++i)
		std::printf("PR r=%d body=%d i=%d g=%d gems=%d force=%d rally=(%d,%d) altar=%d open=%d\n", round, W.my_index, i, g23_prime[static_cast<std::size_t>(i)].g,
			W.groups[static_cast<std::size_t>(g23_prime[static_cast<std::size_t>(i)].g)].gems, g23_prime[static_cast<std::size_t>(i)].force,
			g23_prime[static_cast<std::size_t>(i)].rally.x, g23_prime[static_cast<std::size_t>(i)].rally.y, g23_prime[static_cast<std::size_t>(i)].altar, g23_open_until);
#endif
}

bool Brain::g23_sees_group(const Group& g) const
{
	for (const auto& cm : g.camps)
		if (world().vis.is_set(cm.pos))
			return true;
	return false;
}

// The clock: bit 7 of bytes 0-4 = (ready round / 5) mod 31 (so readers decode ready_in = (v x 5 - round) mod 155, valid up to 154 rounds;
// a decoded value above 130 means "alive, stale": 0); bit 7 of byte 5 = an enemy holds the group.
int Brain::g23_clock_read() const
{
	std::array<std::uint8_t, 8> b{};
	bc::shared_memory.read(0, std::span<std::uint8_t>{ b });
	int v = 0;
	for (int i = 0; i < 5; ++i)
		v |= ((b[static_cast<std::size_t>(i)] >> 7) & 1) << i;
	g23_holds_read = ((b[5] >> 7) & 1) != 0;
	if (v != g23_clock_v)
		g23_clock_v = v, g23_clock_since = round;
	if (v == 0 || round - g23_clock_since > 85)
		return 0; // alive (or nothing written yet, or nobody refreshed it for 85 rounds: it respawned unseen)
	int ri = (((v - 1) * 5 - round) % 150 + 150) % 150;
	if (ri > 100)
		ri = 0; // a timer that ran out while nobody looked
	return ri;
}

void Brain::g23_clock_write(int ready_in, bool holds)
{
	const int v = ready_in <= 0 ? 0 : 1 + (((round + ready_in) / 5) % 30 + 30) % 30;
	for (int i = 0; i < 6; ++i)
	{
		const std::uint8_t old = bc::shared_memory[static_cast<std::size_t>(i)];
		const int bit = i < 5 ? (v >> i) & 1 : (holds ? 1 : 0);
		bc::shared_memory[static_cast<std::size_t>(i)] = static_cast<std::uint8_t>((old & 0x7F) | (bit << 7));
	}
}

int Brain::g23_eta(const Group& g, vec2 from) const
{
	const int d = nav().group_dist(g, from);
	if (d >= BIG)
		return BIG;
	return approach_rounds(std::max(0, d - std::max(1, g.max_range)));
}

// Every turn: the P0 clock (own vision beats the shared value), the roster (the `need` committed bodies with the smallest eta), my role.
void Brain::g23_tol_tick()
{
	auto& W = world();
	auto& C = comms();
	g23_role = G23_FARM;
	if (!g23_tol_ready)
	{
		if (round < 2 || bc::fuel_remaining() < 60000)
			return;
		g23_tol_init();
	}
	if (g23_nprime == 0)
		return;
	auto& p0 = g23_prime[0];
	auto& g = W.groups[static_cast<std::size_t>(p0.g)];
	const bool sees = g23_sees_group(g);
	g23_sees = sees;
	bool holds = false;
	for (const auto& e : W.enemies)
		if (e.alive && e.seen_round >= 0 && round - e.seen_round <= 10 && cheb(e.pos, g.center) <= g.radius + 3)
			holds = true;
	int ready_in;
	if (sees)
	{
		// not alive = at least 1 (a blocked respawn reads 0 rounds; a reward being captured respawns capture + respawn rounds after we saw it)
		ready_in = g.st == ST_RESPAWN ? std::max(1, g.ready_round - round)
			: g.st == ST_REWARD ? std::max(1, g.reward_round + static_cast<int>(bc::constants::capture_time) + 1 + g.respawn - round) : 0;
		g23_clock_write(ready_in, holds);
		g23_enemy_holds = holds;
	}
	else
	{
		ready_in = g23_clock_read();
		g23_enemy_holds = g23_holds_read || holds;
		// a belief of our own that is fresher than the shared one: a respawn we saw start
		if (g.st == ST_RESPAWN && g.ready_round > round && round - g.seen_round <= 30)
			ready_in = g.ready_round - round;
	}
	g23_ready_in = ready_in;
	if (ready_in > 0)
		g23_open_until = 0; // the opening (everyone to P0) ends with its first respawn
	// roster
	int alive_n = 0;
	for (const auto& a : W.allies)
		alive_n += a.alive;
	int need = std::min(alive_n, p0.force + (g23_enemy_holds ? P.g23_hold_extra : 0));
	if (g23_enemy_holds && g23_R < 1.f && round - g23_round <= 1)
		need = 0; // contested and outpowered here: nobody goes (farm elsewhere; the next cycle decides again)
	if (round < g23_open_until)
		need = alive_n;
	struct Cand
	{
		int eta, hpk, idx;
	};
	std::array<Cand, 8> cs{};
	int n = 0;
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
	{
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (!a.alive)
			continue;
		vec2 ap{ -1, -1 };
		float ahp = 0.5f;
		if (i == W.my_index)
			ap = pos, ahp = hp / max_hp;
		else if (a.visible)
		{
			if (a.channeling)
				continue;
			ap = a.pos, ahp = a.hp / std::max(1.f, a.max_hp);
		}
		else if (i < 6 && C.claim[static_cast<std::size_t>(i)] >= 0 && C.claim[static_cast<std::size_t>(i)] < static_cast<int>(W.groups.size()))
			ap = W.groups[static_cast<std::size_t>(C.claim[static_cast<std::size_t>(i)])].center;
		else if (round - a.seen_round <= 10)
			ap = a.pos;
		else
			continue;
		const int eta = g23_eta(g, ap);
		// committed: it arrives in time (alive now: within 25 rounds; respawning: at most 6 rounds after the respawn)
		if (eta >= BIG || eta > (ready_in <= 0 ? P.g23_alive_eta : ready_in + 6))
			continue;
		const int rank_eta = P.g23_prime_sticky > 0 && i == W.my_index && g23_role_round == round - 1 ? eta - P.g23_prime_sticky : eta;
		cs[static_cast<std::size_t>(n++)] = { rank_eta, -static_cast<int>(ahp * 100.f), i };
	}
	std::sort(cs.begin(), cs.begin() + n, [](const Cand& a, const Cand& b) { return a.eta != b.eta ? a.eta < b.eta : a.hpk != b.hpk ? a.hpk < b.hpk : a.idx < b.idx; });
	bool mine = false;
	int lowest_ranged = -1;
	for (int k = 0; k < n && k < need; ++k)
	{
		const int i = cs[static_cast<std::size_t>(k)].idx;
		if (i == W.my_index)
			mine = true;
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (a.kit_ready && a.kit.ranged && (lowest_ranged < 0 || i < lowest_ranged))
			lowest_ranged = i;
	}
	if (mine)
		g23_role = G23_PRIME, g23_role_round = round;
	g23_warden = mine && lowest_ranged == W.my_index;
#ifdef G23_TRACE
	std::printf("TL r=%d ch=%d body=%d p0=%d ready=%d sees=%d holds=%d need=%d n=%d role=%d warden=%d\n", round, static_cast<int>(type), W.my_index, p0.g, g23_ready_in,
		static_cast<int>(sees), static_cast<int>(g23_enemy_holds), need, n, g23_role, static_cast<int>(g23_warden));
#endif
}

// PRIME executor: on the way (farm() keeps us under the in-time constraint) until eta + 1 >= ready_in; then the rally (T_WAIT with the
// deadline); the round the group is alive, hit it (farm_group). Returns true when it used the turn.
bool Brain::g23_prime_turn()
{
	auto& W = world();
	if (g23_role != G23_PRIME || g23_nprime == 0)
		return false;
	auto& p0 = g23_prime[0];
	auto& g = W.groups[static_cast<std::size_t>(p0.g)];
	if (g.st == ST_REWARD)
		return false; // the normal farm: the capturer takes it (mi_capture), the others move on
	// never walk off a capture or a group we are finishing (it would reset / heal while we are away)
	if (task == T_CAPTURE || reward_here())
		return false;
	if (task_group >= 0 && task_group != p0.g && task_group < static_cast<int>(W.groups.size()) && round - target_hit_round <= P.v27_commit_r &&
		W.groups[static_cast<std::size_t>(task_group)].st == ST_ALIVE)
		return false;
	const int eta = g23_eta(g, pos);
	if (eta >= BIG)
		return false;
	// own vision beats our own stale model; without vision the shared clock decides. A respawning group we see is never alive: its timer
	// reads 0 when an occupied spawn tile blocks the respawn, and walking onto it (farm_group) kept it blocked for hundreds of rounds
	// (01boss_battle trace: bodies stood 600+ turns at the prime group with st = RESPAWN).
	const bool alive_now = g23_sees ? g.st == ST_ALIVE : g23_ready_in <= 0;
#ifdef G23_TRACE
	auto pt = [&](const char* what) { std::printf("PT r=%d body=%d what=%s eta=%d ready=%d alive=%d st=%d pos=(%d,%d) hp=%.0f gems=%d\n", round,
		world().my_index, what, eta, g23_ready_in, static_cast<int>(alive_now), static_cast<int>(g.st), pos.x, pos.y, hp, static_cast<int>(gems)); };
#else
	auto pt = [](const char*) {};
#endif
	if (alive_now)
	{
		// the scorer's own checks still apply (enemy force at the group, their half while hurt, unreachable, survivability)
		prepare_scoring();
		int e2 = 0;
		if (group_score(g, e2) <= 0.f)
		{
			pt("score0");
			return false;
		}
		if (task_group != p0.g)
			task_group = p0.g, task_since = round;
		task = T_FARM;
		if (P.g23_stage && g23_stage(g))
			return true;
		pt("farmP0");
		farm_group(g);
		return true;
	}
	if (eta + 1 < g23_ready_in)
	{
		pt("onway");
		return false; // farm on the way (the constraint in group_score keeps it in time)
	}
	pt("rally");
	return g23_go_rally();
}

// To the rally tile of the prime group (T_WAIT with the deadline: giveup / unstick never drop it); out of the camps' reach; the warden's ward.
bool Brain::g23_go_rally()
{
	auto& W = world();
	if (g23_nprime == 0)
		return false;
	auto& p0 = g23_prime[0];
	auto& g = W.groups[static_cast<std::size_t>(p0.g)];
	if (task_group != p0.g)
		task_group = p0.g, task_since = round;
	task = T_WAIT;
	task_progress = round;
	if (g23_rally_since < 0 || round - g23_rally_since > 2)
		g23_rally_since = round;
	const int rd = cheb(pos, p0.rally);
	if (rd > 1)
	{
		bc::bitboard goal;
		goal.draw_chebyshev(p0.rally, 1.f);
		goal &= ~W.walls & ~g.near;
		if (goal.is_empty())
			goal.set(p0.rally);
		step(goal, true, true);
	}
	else if (g.near.is_set(pos))
	{
		bc::bitboard out = ~g.near & ~W.walls;
		step(out, true, false);
	}
	if (P.g23_ward && g23_warden)
		g23_warden_ward();
	return true;
}

// The warden's ward: a legal tile within 2 of us whose ward vision covers an original spawn tile of the prime group (the engine's respawn
// timer becomes readable from anywhere), a bush first. Placed once; never re-placed by this body.
bool Brain::g23_warden_ward()
{
	auto& W = world();
	if (g23_ward_placed || g23_nprime == 0 || bc::fuel_remaining() < 25000)
		return false;
	auto& p0 = g23_prime[0];
	const auto& g = W.groups[static_cast<std::size_t>(p0.g)];
	const auto& B = bc::map::bushes();
	vec2 best{ -1, -1 };
	int bs = -1;
	bc::bitboard seen{ bc::uninitialized };
	for (int dy = -2; dy <= 2; ++dy)
		for (int dx = -2; dx <= 2; ++dx)
		{
			const vec2 t = pos + vec2{ dx, dy };
			if (!bc::map::is_in_bounds(t) || W.walls.is_set(t) || W.camp_occ.is_set(t) || g.mask.is_set(t))
				continue;
			if (cheb(t, g.center) > g.radius + 6)
				continue;
			try
			{
				bc::ward::visible_tiles_from_into(t, seen);
			}
			catch (...)
			{
				continue;
			}
			int cover = 0;
			for (const auto& cm : g.camps)
				cover += seen.is_set(cm.pos);
			if (cover == 0)
				continue;
			const int s = cover * 4 + (B.is_set(t) ? 10 : 0);
			if (s > bs)
				bs = s, best = t;
		}
	if (best.x < 0)
		return false;
	try
	{
		if (bc::self().place_ward(best))
		{
			ward_round = round;
			ward_pos = best;
			g23_ward_placed = true;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

// ---------------------------------------------------------------------------------------------- spawn farming (homonoliths and the like)

// A live camp of g within our attack range of one of our spawn tiles: the body hits it from the spawn and is healed fully every round.
bool Brain::g23_spawn_reach(const Group& g) const
{
	auto& W = world();
	if (g.st != ST_ALIVE && g.st != ST_RESPAWN)
		return false;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
	{
		if (g.st == ST_ALIVE && g.hp[i] <= 0)
			continue;
		if (cheb(g.camps[i].pos, W.ally_spawn_c) > kit.attack_range + 6)
			continue;
		for (const auto t : W.ally_spawn.positions())
			if (cheb(t, g.camps[i].pos) <= kit.attack_range)
				return true;
	}
	return false;
}

// The executor: stand on the spawn tile in range of the lowest-health live camp (out of the reach of the others when our health is
// below what they deal in a round), attack; true when the turn was used.
bool Brain::g23_spawn_farm(Group& g)
{
	auto& W = world();
	if (!g23_spawn_reach(g) || g.st != ST_ALIVE)
		return false;
	// camps that could hit a tile: all live attacking camps of any alive group
	auto camp_in_at = [&](vec2 t) {
		float in = 0;
		for (const auto& og : W.groups)
		{
			if (og.st != ST_ALIVE || og.harmless || cheb(og.center, t) > 10)
				continue;
			for (std::size_t i = 0; i < og.camps.size(); ++i)
				if (og.hp[i] > 0 && og.camps[i].str > 0 && cheb(og.camps[i].pos, t) <= std::max(3, og.camps[i].range))
					in += og.camps[i].str;
		}
		return in;
	};
	const bc::bitboard blocked = Nav::blocked_now(pos);
	vec2 best{ -1, -1 };
	float bk = 1e30f;
	std::size_t best_camp = g.camps.size();
	for (const auto t : W.ally_spawn.positions())
	{
		if (W.walls.is_set(t) || (blocked.is_set(t) && !(t == pos)))
			continue;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (g.hp[i] <= 0 || cheb(t, g.camps[i].pos) > kit.attack_range)
				continue;
			const float in = camp_in_at(t);
			if (hp <= 1.3f * in && !(t == pos))
				continue; // we would not survive the round there
			const float key = g.hp[i] + 50.f * static_cast<float>(cheb(t, pos)) + in * 0.1f;
			if (key < bk)
				bk = key, best = t, best_camp = i;
		}
	}
	if (best.x < 0)
	{
		// no survivable tile in range: a spawn tile out of every camp's reach, then come back healed
		for (const auto t : W.ally_spawn.positions())
			if (!W.walls.is_set(t) && camp_in_at(t) <= 0.f && (!blocked.is_set(t) || t == pos))
			{
				task = T_WAIT;
				task_progress = round;
				if (!(t == pos))
				{
					bc::bitboard goal;
					goal.set(t);
					step(goal, false, false);
				}
				return true;
			}
		return false;
	}
	task = T_FARM;
	if (!(best == pos))
	{
		bc::bitboard goal;
		goal.set(best);
		step(goal, false, false);
		if (kit.ranged || !(pos == best))
		{
			if (!(pos == best) && !can_move)
				return true;
			if (kit.ranged)
				return true; // ranged: the attack comes next turn (move or attack)
		}
	}
	task_progress = round;
	// hit the lowest-health camp in range from here
	std::size_t t = g.camps.size();
	float bh = 1e30f;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
		if (g.hp[i] > 0 && W.camp_occ.is_set(g.camps[i].pos) && cheb(pos, g.camps[i].pos) <= kit.attack_range && g.hp[i] < bh)
			bh = g.hp[i], t = i;
	if (t == g.camps.size())
		return true;
	if (!(enemy_near_d <= P.hold_spell_dist && P.hold_spells_near_enemies))
		spells_on_camp(g, t, enemy_near_d <= P.hold_cc_dist);
	attack_chain_camp(g, t);
	return true;
}

// ---------------------------------------------------------------------------------------------- dive filter (ladder analysis P1)

// Outnumbered here (R < g23_dive_r at our tile, or the burst the visible enemies can land on our tile next turn is at least our health):
// every tile within 2 that is nearer to the nearest visible enemy than our tile is blocked for this turn's walks and dashes (Nav::
// blocked_now reads g_hard_block). combat() clears it when it decides to fight.
void Brain::g23_dive_prepare()
{
	auto& W = world();
	std::vector<Enemy*> E;
	int d0 = BIG;
	for (auto& e : W.enemies)
		if (e.alive && e.visible && cheb(e.pos, pos) <= 9 && !W.enemy_spawn.is_set(e.pos))
		{
			E.push_back(&e);
			d0 = std::min(d0, cheb(e.pos, pos));
		}
	if (E.empty() || W.ally_spawn.is_set(pos))
		return;
	g23_block.clear();
	if (P.g23_campzone && d0 <= 6)
	{
		// awake camps of other groups than our target: the tiles in their reach where we would be the nearest champion (they hit us)
		for (const auto& g : W.groups)
		{
			if (g.st != ST_ALIVE || !g.awake || g.harmless || g.id == task_group || cheb(g.center, pos) > 10)
				continue;
			for (std::size_t i = 0; i < g.camps.size(); ++i)
			{
				if (g.hp[i] <= 0 || g.camps[i].str <= 0)
					continue;
				const vec2 c = g.camps[i].pos;
				const int rng = std::max(3, g.camps[i].range);
				int de = BIG; // nearest enemy champion to the camp
				for (auto* e : E)
					de = std::min(de, cheb(e->pos, c));
				for (int dy = -2; dy <= 2; ++dy)
					for (int dx = -2; dx <= 2; ++dx)
					{
						const vec2 t{ pos.x + dx, pos.y + dy };
						if ((dx == 0 && dy == 0) || !bc::map::is_in_bounds(t))
							continue;
						const int dt = cheb(t, c);
						if (dt <= rng && dt <= de)
							g23_block.set(t);
					}
			}
		}
	}
	if (!P.g23_divefilter)
	{
		if (!g23_block.is_empty())
			g_hard_block = &g23_block;
		return;
	}
	float burst = 0;
	for (auto* e : E)
	{
		int reach = e->kit.attack_range + (e->kit.ranged ? 0 : 1) + (e->ready(e->kit.dash) ? 2 : 0);
		if (e->ready(e->kit.dmg) || e->ready(e->kit.cc) || e->ready(e->kit.aoe))
			reach = std::max(reach, 4);
		if (cheb(e->pos, pos) <= reach)
			burst += e->str * (e->ready(e->kit.reset) ? 2.f : 1.f) + e->burst();
	}
	const float R = g23_ratio(pos, E, nullptr, nullptr, nullptr);
	if (!(R < P.g23_dive_r || burst >= hp))
	{
		if (!g23_block.is_empty())
			g_hard_block = &g23_block; // the camp zone alone
		return;
	}
	for (int dy = -2; dy <= 2; ++dy)
		for (int dx = -2; dx <= 2; ++dx)
		{
			const vec2 t{ pos.x + dx, pos.y + dy };
			if ((dx == 0 && dy == 0) || !bc::map::is_in_bounds(t))
				continue;
			int dt = BIG;
			for (auto* e : E)
				dt = std::min(dt, cheb(e->pos, t));
			if (dt < d0)
				g23_block.set(t);
		}
	if (!g23_block.is_empty())
		g_hard_block = &g23_block;
}

// ---------------------------------------------------------------------------------------------- hold out of camps (map_fail B1)

// A hold inside an awake camp's reach takes the camp's hits while we wait for the enemy: step to a tile out of every awake camp's reach,
// avoiding enemy reach (step() with avoid_danger). No step (cornered, rooted): hold where we are.
bool Brain::g23_hold_out_of_camps()
{
	if (!can_move || !camp_danger.is_set(pos))
		return false;
	bc::bitboard out = ~camp_danger & ~world().walls;
	bc::bitboard near2;
	near2.draw_chebyshev(pos, 2.f);
	out &= near2;
	if (out.is_empty())
		return false;
	return step(out, true, false);
}
