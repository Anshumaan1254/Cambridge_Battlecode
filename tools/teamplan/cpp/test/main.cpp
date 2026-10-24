// Test bot of the teamplan library (built as the git-ignored bots/_tp_test by tools/teamplan/test_teamplan.py from the cambc 3.0.5
// starter's loop). It runs every module inside the engine and prints compact results; the harness recomputes them with the Python twins
// (tools/teamplan/tp/) and compares bit for bit. stdout costs about 90 fuel per byte in this engine, so inputs go out packed and outputs
// as 64-bit FNV-1a hashes of the values' bytes.
//   draft turn 1 : TP DES t ... (the 13 designs, doubles as bit hex), TP CON ..., TP PAR ... (params.h defaults), TP KIT t <hash>,
//                  TP KF fuel_kits <f>
//   game turns of the tester body (the ally with the lowest body type alive on its first turn), one part per turn so that no turn runs
//   out of fuel (a turn that does continues in the next round, and the fuel numbers would mix two turns):
//     1: TP G n <packed groups: gems 3 hex, gold 3 hex, hp 5 hex, walk 3 hex (fff = unreachable)> fuel_groups <f> team_n <n>
//     2: TP A r <hash> fuel <worst call> (3 rosters; the plan and one variant per body left out)
//     3: TP C r <hash> fuel <worst call> (capturer choice on 16 groups per roster)
//     4: TP S1 timing <hash> bag <hash> focus <hash> fuel <f> <f> <f>     5: TP S2 tiebreak <hash> fuel <f>
//     6: TP S3 swap <hash> live <hash> nav <hash> fuel <f> <f> <f>        (the fuel of a sweep includes hashing its outputs)
//     7: TP NAV step <dx> <dy> fuel <f> units <n> (nav_sdk.h local detour toward the enemy spawn around the champions in sight)
//   every body, rounds 2-7 and every 10th round 20-80: TP O <round> <type> <prio> <prev_prio> (turn order inside a team) and
//   TP EP <round> <enemy type> dist <d> <prev_prio | err> for the first two enemies listed; from round 8 the other bodies walk to the
//   enemy spawn so enemies come into sight
//   TP E <what> on any exception.
#include <cambc.h>

#include <algorithm>
#include <cstdlib>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "teamplan/assign.h"
#include "teamplan/bag.h"
#include "teamplan/capture.h"
#include "teamplan/focus.h"
#include "teamplan/kit.h"
#include "teamplan/live.h"
#include "teamplan/nav.h"
#include "teamplan/nav_sdk.h"
#include "teamplan/params.h"
#include "teamplan/sdk_bridge.h"
#include "teamplan/swap.h"
#include "teamplan/tiebreak.h"
#include "teamplan/timing.h"
namespace bc = cambc;
namespace tp = teamplan;

static void line(const std::string& s)
{
	const std::string t = s + "\n";
	std::fputs(t.c_str(), stdout);
	std::fflush(stdout);
}
static long long fuel() { return static_cast<long long>(bc::fuel_remaining()); }

static const char* HX = "0123456789abcdef";
static std::string hexd(double v)
{
	std::uint64_t u;
	std::memcpy(&u, &v, 8);
	std::string s(16, '0');
	for (int i = 15; i >= 0; --i, u >>= 4)
		s[static_cast<std::size_t>(i)] = HX[u & 15];
	return s;
}
static std::string hexn(unsigned v, int digits)
{
	std::string s(static_cast<std::size_t>(digits), '0');
	for (int i = digits - 1; i >= 0; --i, v >>= 4)
		s[static_cast<std::size_t>(i)] = HX[v & 15];
	return s;
}

struct H
{
	std::uint64_t h = 0xcbf29ce484222325ull;
	void byte(std::uint8_t b)
	{
		h ^= b;
		h *= 0x100000001b3ull;
	}
	void i(long long v)
	{
		const auto u = static_cast<std::uint32_t>(static_cast<std::int32_t>(v));
		for (int k = 0; k < 4; ++k)
			byte(static_cast<std::uint8_t>(u >> (8 * k)));
	}
	void d(double v)
	{
		std::uint64_t u;
		std::memcpy(&u, &v, 8);
		for (int k = 0; k < 8; ++k)
			byte(static_cast<std::uint8_t>(u >> (8 * k)));
	}
	std::string str() const { return hexn(static_cast<unsigned>(h >> 32), 8) + hexn(static_cast<unsigned>(h), 8); }
};

static tp::Params P;
static tp::Consts C;
static tp::Kit K[13];
static bool have_kits = false;

static void make_kits()
{
	C = tp::consts_from_sdk();
	for (int t = 0; t < 13; ++t)
		K[t] = tp::compute_kit(tp::design_of(t), C, P);
	have_kits = true;
}

static void hash_kit(H& h, const tp::Kit& k)
{
	h.i(k.melee), h.i(k.has_dash), h.i(k.stun_immune), h.i(k.splash), h.i(k.remote_shop), h.i(k.reset_on_kill);
	const double v[] = { k.hp, k.resets, k.basic, k.spell, k.spell_mod, k.area, k.area_mod, k.stun, k.shield, k.heal, k.dash_range, k.reach,
						 k.gold_mult, k.tribute_gold, k.focus_per_gem, k.retaliation, k.mhp_bonus, k.str_per_hp, k.dps, k.camp_dps, k.ehp,
						 k.dmg_str_shard, k.dmg_foc_shard, k.dmg_hp_shard, k.w_gold, k.exposure, k.front };
	for (double x : v)
		h.d(x);
}

static void draft_turn1()
{
	for (int t = 0; t < 13; ++t)
	{
		const tp::Design d = tp::design_of(t);
		std::string s = "TP DES " + std::to_string(t);
		for (double x : { d.hp, d.hp_g, d.str, d.str_g, d.foc, d.foc_g, d.campmul })
			s += " " + hexd(x);
		s += " " + std::to_string(d.range) + " " + std::to_string(d.move) + " " + std::to_string(d.vision) + " " + std::to_string(d.passive);
		for (const auto& a : d.ab)
			s += " " + std::to_string(a.kind) + " " + std::to_string(a.enhanced) + " " + hexd(a.range) + " " + hexd(a.mod) + " " + hexd(a.radius) + " " +
				 std::to_string(a.dur) + " " + std::to_string(a.cd);
		line(s);
	}
	const long long f0 = fuel();
	make_kits();
	const long long f1 = fuel();
	std::string s = "TP CON";
	for (double x : { C.bonus_gold_pct, C.focus_per_gem, C.health_strength_ratio, C.retaliation_ratio, C.missing_health_bonus, C.tribute_gold_per_gem,
					  C.shard_cost })
		s += " " + hexd(x);
	s += " " + std::to_string(C.respawn_time) + " " + std::to_string(C.capture_time) + " " + std::to_string(C.max_rounds) + " " +
		 std::to_string(C.winning_gems) + " " + std::to_string(C.kill_gold);
	line(s);
	H hp;
	for (double x : { P.enhanced_extra, P.enhanced_stun, P.missing_hp_avg, P.hits_taken, P.splash_targets, P.area_targets, P.fight_rounds, P.ranged_front, P.immune_ehp,
					  P.dash_escape, P.reach_escape, P.gold_gems, P.team_rate, P.hazard, P.danger_hazard, P.items_half })
		hp.d(x);
	hp.i(P.capture_mode);
	hp.i(P.bag_fight), hp.d(P.bag_fight_scale), hp.d(P.hunt_bag), hp.d(P.hunt_bonus), hp.d(P.kv_ref);
	for (int x : { P.tb_period, P.tb_enter, P.tb_leave, P.tb_min_round, P.tb_defer_cap, P.tb_safe_dist, P.tb_final_margin, P.tb_denial_rounds })
		hp.i(x);
	hp.d(P.own_bonus), hp.d(P.gemfree_front), hp.i(P.swap_period), hp.i(P.swap_hold), hp.d(P.swap_margin), hp.d(P.lag_ratio);
	line("TP PAR version " + std::to_string(tp::kParamsVersion) + " " + hp.str());
	for (int t = 0; t < 13; ++t)
	{
		H h;
		hash_kit(h, K[t]);
		line("TP KIT " + std::to_string(t) + " " + h.str());
	}
	line("TP KF fuel_kits " + std::to_string(f0 - f1));
}

// ---- game-turn tests (tester body)
static const int ROSTER[3][5] = { { 1, 7, 12, 2, 0 }, { 3, 4, 5, 9, 10 }, { 6, 8, 11, 0, 12 } };
struct G
{
	int gems, gold, hp, walk;
};
static std::vector<G> groups;
static int team_n = 5;

static void load_groups()
{
	const bc::bitboard blocked = bc::map::walls() | bc::map::holes() | bc::map::altars() | bc::map::spawn_region(bc::team::enemy);
	bc::bitboard roots = bc::map::spawn_region(bc::team::ally), visited;
	bc::distance_field f;
	f.compute(blocked, roots, visited);
	for (const auto& g : bc::map::camp_groups())
	{
		G x{ static_cast<int>(g.gem_value()), static_cast<int>(g.gold_value()), 0, -1 };
		double hp = 0;
		for (const auto& c : g.camps())
		{
			hp += static_cast<double>(c.base_stats().base_health);
			const std::uint16_t d = f.get(c.spawn_position());
			if (d != bc::distance_field::unreachable && (x.walk < 0 || d < x.walk))
				x.walk = d;
		}
		x.hp = static_cast<int>(hp);
		groups.push_back(x);
	}
}

static std::vector<tp::AGroup> agroups()
{
	std::vector<tp::AGroup> out;
	for (const auto& g : groups)
	{
		tp::AGroup a;
		a.value = g.gems + P.gold_gems * g.gold;
		a.hp = g.hp;
		a.walk = g.walk;
		a.gem_free = g.gems == 0 ? 1 : 0;
		out.push_back(a);
	}
	return out;
}

static void game_turn1()
{
	const long long f0 = fuel();
	load_groups();
	const long long f1 = fuel();
	std::string s = "TP G " + std::to_string(groups.size()) + " ";
	for (const auto& g : groups)
		s += hexn(static_cast<unsigned>(g.gems), 3) + hexn(static_cast<unsigned>(g.gold), 3) + hexn(static_cast<unsigned>(g.hp), 5) +
			 hexn(g.walk < 0 ? 0xfffu : static_cast<unsigned>(g.walk), 3);
	s += " fuel_groups " + std::to_string(f0 - f1) + " team_n " + std::to_string(team_n);
	line(s);
}

static void game_turn_assign()
{
	const auto ag = agroups();
	const int Gn = static_cast<int>(ag.size());
	std::vector<std::uint8_t> owner(static_cast<std::size_t>(Gn));
	for (int r = 0; r < 3; ++r)
	{
		tp::Kit kits[5];
		for (int b = 0; b < team_n; ++b)
			kits[b] = K[ROSTER[r][b]];
		H h;
		long long worst = 0;
		for (int v = -1; v < team_n; ++v)
		{
			const unsigned alive = (1u << team_n) - 1u & ~(v >= 0 ? 1u << v : 0u);
			double tm[5], vl[5];
			const long long a0 = fuel();
			tp::assign_groups(ag.data(), Gn, kits, team_n, alive, C, P, owner.data(), tm, vl);
			worst = std::max(worst, a0 - fuel());
			for (int g = 0; g < Gn; ++g)
				h.i(owner[static_cast<std::size_t>(g)]);
			for (int b = 0; b < team_n; ++b)
				h.d(tm[b]), h.d(vl[b]);
		}
		line("TP A " + std::to_string(r) + " " + h.str() + " fuel " + std::to_string(worst));
	}
}

static void game_turn2()
{
	for (int r = 0; r < 3; ++r)
	{
		H h;
		long long worst = 0;
		int ng = 0;
		for (int g = 0; g < static_cast<int>(groups.size()) && ng < 16; ++g)
		{
			if (groups[static_cast<std::size_t>(g)].walk < 0)
				continue;
			++ng;
			tp::CaptureCand cs[5];
			int n = 0;
			for (int s = 0; s < team_n; ++s)
			{
				if ((g + s) % 3 == 0)
					continue;
				tp::CaptureCand& x = cs[n++];
				x.slot = s, x.bag = (g * 7 + s * 13) % 70, x.items = (g + 3 * s) % 15, x.walk_reward = (g + s) % 4;
				x.walk_bank = std::min(groups[static_cast<std::size_t>(g)].walk, 60), x.danger = (g * (s + 1)) % 3, x.kit = &K[ROSTER[r][s]];
			}
			for (int mode = 0; mode < 2; ++mode)
			{  // both rules (capture_mode 0 and 1), with items_half on (12) and off (0)
				tp::Params q = P;
				q.capture_mode = mode, q.items_half = mode ? 0.0 : 12.0;
				double gains[5];
				const long long c0 = fuel();
				const int w = tp::choose_capturer(cs, n, groups[static_cast<std::size_t>(g)].gems, groups[static_cast<std::size_t>(g)].gold, team_n, C, q, gains);
				worst = std::max(worst, c0 - fuel());
				h.i(w);
				for (int i = 0; i < n; ++i)
					h.d(gains[i]);
			}
		}
		line("TP C " + std::to_string(r) + " " + h.str() + " fuel " + std::to_string(worst));
	}
}

static void game_turn_s1()
{
	std::string out = "TP S1";
	std::string fu = " fuel";
	{  // timing
		const long long f0 = fuel();
		H h;
		for (int rnd = 1; rnd <= 4; ++rnd)
			for (int team = 0; team < 2; ++team)
				for (int no = 1; no <= 5; ++no)
					for (int nt = 1; nt <= 5; ++nt)
						for (int ur = 0; ur < no; ++ur)
							for (int er = 0; er < nt; ++er)
							{
								h.i(tp::turn_pos(rnd, team, ur, no, nt));
								h.i(tp::we_act_first(rnd, team, ur, no, er, nt) ? 1 : 0);
							}
		const int prio[5] = { 3, 1, 3, 0, 2 }, ids[5] = { 4, 2, 1, 0, 3 };
		for (int me = 0; me < 5; ++me)
			h.i(tp::rank_of(prio, ids, 5, me));
		out += " timing " + h.str();
		fu += " " + std::to_string(f0 - fuel());
	}
	{  // bag
		const long long f0 = fuel();
		H h;
		for (int bag = 0; bag <= 90; bag += 15)
		{
			h.d(tp::fight_bar(1.2, bag, P));
			for (int ed = 1; ed <= 9; ed += 2)
				for (int wb = 0; wb <= 12; wb += 4)
					h.i(tp::bank_before_fight(bag, ed, 4, wb, (ed + wb) % 2 == 0, P) ? 1 : 0);
			for (int o = 1; o <= 3; ++o)
				for (int t = 1; t <= 3; ++t)
					h.d(tp::hunt_bonus(bag, o, t, P));
			h.i(tp::bank_now_wins(900, bag, 15, C) ? 1 : 0);
		}
		out += " bag " + h.str();
		fu += " " + std::to_string(f0 - fuel());
	}
	{  // focus
		const long long f0 = fuel();
		H h;
		for (int bag = 0; bag <= 80; bag += 20)
			for (int bodies = 1; bodies <= 2; ++bodies)
				for (int n = 3; n <= 5; ++n)
				{
					const double kv = tp::kill_value(bag, bodies, n, C, P);
					h.d(kv);
					for (int rk = 0; rk <= 6; rk += 3)
						h.d(tp::target_priority(kv, rk, P));
				}
		out += " focus " + h.str();
		fu += " " + std::to_string(f0 - fuel());
	}
	line(out + fu);
}

static void game_turn_s2()
{
	std::string out = "TP S2";
	std::string fu = " fuel";
	{  // tiebreak
		const long long f0 = fuel();
		H h;
		for (int sc = 0; sc < 3; ++sc)
		{
			tp::TbState s;
			const double a = 0.25 + 0.15 * sc, b = 0.45 - 0.1 * sc;
			for (int rnd = 1; rnd <= 2000; rnd += 10)
			{
				const int ours = static_cast<int>(rnd * a), theirs = static_cast<int>(rnd * b), carried = (rnd / 7) % 40;
				h.i(tp::tb_update(s, rnd, ours, theirs, carried, sc % 2, C, P));
				h.i(s.proj_ours), h.i(s.proj_theirs);
				h.i(tp::tb_defer(s.mode, carried, (rnd / 3) % 15, P) ? 1 : 0);
				h.i(tp::tb_final(rnd, (rnd / 11) % 40, carried, C, P) ? 1 : 0);
				h.i(tp::tb_denial(rnd, C, P) ? 1 : 0);
			}
		}
		out += " tiebreak " + h.str();
		fu += " " + std::to_string(f0 - fuel());
	}
	line(out + fu);
}

static void game_turn_s3()
{
	std::string out = "TP S3";
	std::string fu = " fuel";
	{  // swap
		const long long f0 = fuel();
		H h;
		for (int r = 0; r < 3; ++r)
		{
			tp::Kit kits[5];
			for (int b = 0; b < team_n; ++b)
				kits[b] = K[ROSTER[r][b]];
			tp::SwapState s;
			for (int rnd = 0; rnd <= 1000; rnd += 50)
			{
				double plan[5];
				std::uint8_t code[5];
				for (int b = 0; b < team_n; ++b)
				{
					plan[b] = 0.1 + 0.05 * ((b * 3 + rnd / 50) % 7);
					code[b] = static_cast<std::uint8_t>((b + rnd / 100) % 4);
				}
				h.i(tp::swap_check(s, rnd, plan, code, kits, team_n, (1u << team_n) - 1u, P));
				h.i(s.a), h.i(s.b), h.i(s.last);
			}
			for (int b = 0; b < team_n; ++b)
				for (int q = 0; q < 8; ++q)
					h.i(tp::progress_code(0.25 * q)), h.i(tp::can_swap(kits[b], kits[q % team_n], 0.25) ? 1 : 0);
		}
		out += " swap " + h.str();
		fu += " " + std::to_string(f0 - fuel());
	}
	{  // live
		const long long f0 = fuel();
		H h;
		std::uint64_t v = 0;
		for (int k = 0; k < 40; ++k)
		{
			tp::BodyField o;
			o.claim = (k * 11) % 64, o.status = k % 4, o.beat = (k / 2) % 2, o.flag = (k / 3) % 2;
			v = tp::set_body(v, k % 6, o);
			v = tp::set_team(v, k % 8, (k / 5) % 2);
			std::uint8_t b[8];
			tp::store64(v, b);
			const std::uint64_t w = tp::load64(b);
			const tp::BodyField r = tp::get_body(w, (k * 5) % 6);
			h.i(static_cast<long long>(w & 0xFFFFFFFFull)), h.i(static_cast<long long>(w >> 32));
			h.i(r.claim), h.i(r.status), h.i(r.beat), h.i(r.flag), h.i(tp::get_cursor(w)), h.i(tp::get_tiebreak(w));
		}
		tp::Beat bt;
		for (int rnd = 0; rnd < 12; ++rnd)
			h.i(tp::beat_stale(bt, (rnd < 6 ? rnd % 2 : 1), rnd) ? 1 : 0);
		out += " live " + h.str();
		fu += " " + std::to_string(f0 - fuel());
	}
	{  // nav (pure)
		const long long f0 = fuel();
		H h;
		tp::Progress pr;
		tp::LoopGuard lg;
		for (int rnd = 0; rnd < 30; ++rnd)
		{
			const int target = rnd < 12 ? 7 : 9, dist = 20 - (rnd % 9);
			h.i(tp::progress_stuck(pr, target, dist, rnd, 4) ? 1 : 0);
			const int tile = (rnd * 7) % 11;
			h.i(tp::loop_seen(lg, tile) ? 1 : 0);
			tp::loop_push(lg, tile);
			h.i(tp::keep_target(dist, (rnd * 3) % 25) ? 1 : 0);
		}
		out += " nav " + h.str();
		fu += " " + std::to_string(f0 - fuel());
	}
	line(out + fu);
}

static void game_turn_nav()
{
	const auto& self = bc::self();
	const auto me = self.position();
	const bc::bitboard walls = bc::map::walls() | bc::map::holes() | bc::map::altars();
	bc::bitboard roots = bc::map::spawn_region(bc::team::enemy), visited;
	bc::distance_field global;
	global.compute(walls, roots, visited);
	std::vector<bc::vec2> units;
	for (const auto& c : bc::champions(bc::team::ally))
		try
		{
			if (!(c == self))
				units.push_back(c.position());
		}
		catch (...)
		{  // out of sight (vision is not shared)
		}
	for (const auto& c : bc::champions(bc::team::enemy))
		try
		{
			units.push_back(c.position());
		}
		catch (...)
		{  // not in sight
		}
	const long long f0 = fuel();
	const bc::vec2 st = tp::local_detour(walls, units.data(), static_cast<int>(units.size()), me, global, 3);
	const long long f1 = fuel();
	line("TP NAV step " + std::to_string(st.x - me.x) + " " + std::to_string(st.y - me.y) + " fuel " + std::to_string(f0 - f1) + " units " +
		 std::to_string(units.size()));
}

int main()
{
	int dturn = 0, gturn = 0;
	int tester = -1;
	while (true)
	{
		try
		{
			if (bc::is_draft())
			{
				++dturn;
				if (dturn == 1)
					draft_turn1();
				const auto chosen = bc::draft::current_draft(bc::team::ally);
				bc::draft::pick(static_cast<bc::champion_draft>(static_cast<int>(chosen.size())));
			}
			else
			{
				++gturn;
				const auto& self = bc::self();
				const int my_type = static_cast<int>(self.champion_name());
				const int rnd = static_cast<int>(bc::round_number());
				if (gturn == 1)
				{
					if (!have_kits)
						make_kits();
					int lo = 99;
					int n = 0;
					for (const auto& c : bc::champions(bc::team::ally))
						lo = std::min(lo, static_cast<int>(c.champion_name())), ++n;
					tester = lo == my_type ? 1 : 0;
					team_n = std::min(5, std::max(1, n));
				}
				if ((rnd >= 2 && rnd <= 7) || (rnd >= 20 && rnd % 10 == 0 && rnd <= 80))
				{
					line("TP O " + std::to_string(rnd) + " " + std::to_string(my_type) + " " + std::to_string(self.priority()) + " " +
						 std::to_string(self.prev_priority()));
					int ne = 0;
					for (const auto& e : bc::champions(bc::team::enemy))
					{
						if (ne++ >= 2)
							break;
						std::string v, d = "?";
						try
						{
							const auto q = e.position(), m = self.position();
							d = std::to_string(std::max(std::abs(q.x - m.x), std::abs(q.y - m.y)));
						}
						catch (...)
						{
						}
						try
						{
							v = std::to_string(e.prev_priority());
						}
						catch (const std::exception& x)
						{
							v = std::string("err:") + x.what();
						}
						line("TP EP " + std::to_string(rnd) + " " + std::to_string(static_cast<int>(e.champion_name())) + " dist " + d + " " + v.substr(0, 40));
					}
				}
				if (tester != 1 && rnd >= 8)
				{  // walk toward the enemy spawn so that enemies come into sight (the TP EP probe)
					const auto es = bc::map::spawn_region(bc::team::enemy).positions();
					if (!es.empty())
						try
						{
							self.move_towards(es.front());
						}
						catch (...)
						{  // a refused move (e.g. a forbidden landing tile) is not a test failure
						}
				}
				if (tester == 1)
				{
					if (gturn == 1)
						game_turn1();
					else if (gturn == 2)
						game_turn_assign();
					else if (gturn == 3)
						game_turn2();
					else if (gturn == 4)
						game_turn_s1();
					else if (gturn == 5)
						game_turn_s2();
					else if (gturn == 6)
						game_turn_s3();
					else if (gturn == 7)
						game_turn_nav();
				}
			}
		}
		catch (const std::exception& e)
		{
			line(std::string("TP E ") + e.what());
		}
		catch (...)
		{
			line("TP E unknown");
		}
		bc::end_turn();
	}
}
