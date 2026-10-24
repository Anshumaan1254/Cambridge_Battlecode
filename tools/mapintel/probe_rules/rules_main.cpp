// Rules probe for tools/mapintel (fresh, from the cambc 3.0.5 starter's main loop; nothing from bots/). Runs on maps/probe_mi/mi_rules.map26a
// (tools/mapintel/probe_rules/rules_map.mjs has the layout). Team A drafts Stellar, Vendetta, Ryth and runs one scripted test list per body;
// team B (same bot) drafts and idles. Every result is one line "PR <round> <body> <test> <result>" on team A's stdout:
//   attack / spell / area / camp-attack ranges (Chebyshev or not), line of sight for attacks, standing on a dead camp's tile and the respawn
//   delay, tribute range, dash legality (over holes, walls, a camp, onto a hole, diagonal, knight move), teleport-crystal legality.
//   cambc run _mi_rules _mi_rules --map maps/probe_mi/mi_rules.map26a --rounds 420 -o DIR
#include <cambc.h>
#include <cstdio>
#include <functional>
#include <string>
#include <vector>
namespace bc = cambc;
using bc::vec2;

static void out(const std::string& s)
{
	const std::string t = s + "\n";
	std::fputs(t.c_str(), stdout);
	std::fflush(stdout);
}
static std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }
static const char* who = "?";
static void pr(const std::string& test, const std::string& res) { out("PR " + std::to_string(bc::round_number()) + " " + who + " " + test + " " + res); }

template <class F> static std::string tryit(F f)
{
	try
	{
		return f() ? "ok" : "false";
	}
	catch (const std::exception& e)
	{
		return std::string("ERR ") + e.what();
	}
}
static std::string camp_hp(vec2 p)
{
	try
	{
		const auto c = bc::map::camp(p);
		if (!bc::vision::visible_tiles().is_set(p))
			return "notvisible";
		return std::to_string(static_cast<int>(c.health()));
	}
	catch (const std::exception& e)
	{
		return std::string("ERR ") + e.what();
	}
}
static std::string group_state(vec2 p)
{
	try
	{
		const auto st = bc::map::camp(p).camp_group().state();
		if (std::holds_alternative<bc::map::camp_group_alive>(st))
			return "alive";
		if (std::holds_alternative<bc::map::camp_group_reward_available>(st))
			return "reward";
		return "respawning " + std::to_string(std::get<bc::map::camp_group_respawning>(st).timer);
	}
	catch (const std::exception& e)
	{
		return std::string("ERR ") + e.what();
	}
}

// A step returns true when finished; the script moves to the next step. Steps get at most 220 rounds.
struct Script
{
	std::vector<std::pair<std::string, std::function<bool()>>> steps;
	size_t i = 0;
	unsigned since = 0;
	int sub = 0;
	void run()
	{
		if (i >= steps.size())
			return;
		if (since == 0)
			since = bc::round_number();
		bool done = false;
		try
		{
			done = steps[i].second();
		}
		catch (const std::exception& e)
		{
			pr(steps[i].first, std::string("EXC ") + e.what());
			done = true;
		}
		if (!done && bc::round_number() - since > 220)
		{
			pr(steps[i].first, "TIMEOUT");
			done = true;
		}
		if (done)
		{
			++i;
			since = 0;
			sub = 0;
		}
	}
};

static bool at(vec2 p) { return bc::self().position() == p; }
static bool walk(vec2 p)
{
	auto& me = bc::self();
	if (at(p))
		return true;
	if (me.can_move())
		me.move_towards(p);
	return at(p);
}
static int hp() { return static_cast<int>(bc::self().health()); }
static bool ready(int slot) { return bc::self().abilities()[slot].is_ready(); }

static Script S;  // global: the step lambdas use S.sub without capturing it

int main()
{
	bool init = false, teamA = false;
	while (true)
	{
		try
		{
			if (bc::is_draft())
			{
				teamA = bc::map::spawn_region(bc::team::ally).is_set({ 1, 1 });
				const auto chosen = bc::draft::current_draft(bc::team::ally);
				const int want[3] = { 4, 2, 0 };  // Stellar, Vendetta, Ryth
				if (teamA)
					bc::draft::pick(static_cast<bc::champion_draft>(want[chosen.size()]));
				else
					bc::draft::pick(static_cast<bc::champion_draft>(static_cast<int>(chosen.size()) + 5));
			}
			else if ((teamA = bc::map::spawn_region(bc::team::ally).is_set({ 1, 1 })))  // each body is its own process: no draft state
			{
				auto& me = bc::self();
				if (!init)
				{
					init = true;
					const auto t = me.champion_name();
					if (t == bc::champion_type::stellar)
					{
						who = "Stellar";
						const vec2 S3{ 2, 16 }, L{ 5, 16 }, S0{ 6, 9 }, C2{ 10, 9 }, C1{ 9, 12 }, C3{ 10, 13 }, Q{ 6, 13 }, A1{ 7, 14 }, A2{ 8, 13 },
							A3{ 5, 12 }, S1{ 13, 12 }, W{ 16, 9 }, S1b{ 12, 12 }, S2{ 10, 14 }, E{ 6, 18 };
						S.steps.push_back({ "walk_S3", [=] { return walk(S3); } });
						S.steps.push_back({ "los_wall", [=] {
							pr("los_wall", std::string("visible ") + (bc::vision::visible_tiles().is_set(L) ? "yes" : "no") + " attack " +
								tryit([&] { bc::self().attack(bc::map::camp(L)); return true; }) + " spell " +
								tryit([&] { return bc::self().abilities()[0].use(bc::map::camp(L)); }));
							return true; } });
						S.steps.push_back({ "walk_S0", [=] { return walk(S0); } });
						S.steps.push_back({ "attack_4_0", [=] { pr("attack_d(4,0)", tryit([&] { bc::self().attack(bc::map::camp(C2)); return true; })); return true; } });
						S.steps.push_back({ "attack_3_3", [=] {
							pr("attack_d(3,3)", tryit([&] { bc::self().attack(bc::map::camp(C1)); return true; }) + " hp_before " + camp_hp(C1));
							return true; } });
						S.steps.push_back({ "spell_4_4", [=] {
							pr("attack_d(3,3)_after", "hp " + camp_hp(C1));
							if (!ready(0)) return false;
							pr("spell_damage_d(4,4)", tryit([&] { return bc::self().abilities()[0].use(bc::map::camp(C3)); }) + " hp_before " + camp_hp(C3));
							return true; } });
						S.steps.push_back({ "aoe", [=] {
							pr("spell_damage_d(4,4)_after", "hp " + camp_hp(C3));
							if (!ready(1)) return false;
							pr("aoe_at_d(0,4)", tryit([&] { return bc::self().abilities()[1].use(Q); }) + " before Q+(1,1) " + camp_hp(A1) + " Q+(2,0) " +
								camp_hp(A2) + " Q+(-1,-1) " + camp_hp(A3));
							return true; } });
						S.steps.push_back({ "aoe_after", [=] {
							pr("aoe_after", "Q+(1,1) " + camp_hp(A1) + " Q+(2,0) " + camp_hp(A2) + " Q+(-1,-1) " + camp_hp(A3));
							return true; } });
						S.steps.push_back({ "walk_S1", [=] { return walk(S1); } });
						S.steps.push_back({ "wolf_d(3,-3)", [=] {
							if (S.sub == 0)
								pr("wolf_attack_d(3,-3)", tryit([&] { bc::self().attack(bc::map::camp(W)); return true; }) + " myhp " + std::to_string(hp()));
							else
							{
								pr("wolf_stand_d(3,-3)", "myhp " + std::to_string(hp()) + " wolfhp " + camp_hp(W));
								if (bc::self().can_attack())
									tryit([&] { bc::self().attack(bc::map::camp(W)); return true; });
							}
							return ++S.sub > 4; } });
						S.steps.push_back({ "walk_S1b", [=] { return walk(S1b); } });
						S.steps.push_back({ "wolf_d(4,-3)", [=] {
							pr("wolf_stand_d(4,-3)", "myhp " + std::to_string(hp()) + " wolfhp " + camp_hp(W));
							return ++S.sub > 4; } });
						S.steps.push_back({ "walk_S2", [=] { return walk(S2); } });
						S.steps.push_back({ "elk_d(-4,4)", [=] {
							if (S.sub == 0)
							{
								if (!ready(0)) return false;
								pr("elk_spell_d(-4,4)", tryit([&] { return bc::self().abilities()[0].use(bc::map::camp(E)); }) + " myhp " + std::to_string(hp()));
							}
							else
								pr("elk_stand_d(-4,4)", "myhp " + std::to_string(hp()) + " elkhp " + camp_hp(E));
							return ++S.sub > 5; } });
						S.steps.push_back({ "leave", [=] { return walk({ 3, 9 }); } });
					}
					else if (t == bc::champion_type::ryth)
					{
						who = "Ryth";
						const vec2 D{ 1, 6 }, M1{ 2, 7 }, AL{ 5, 5 }, T2{ 7, 7 }, T1{ 6, 6 }, OFF{ 1, 7 };
						S.steps.push_back({ "walk_diag", [=] { return walk(D); } });
						S.steps.push_back({ "melee_diag", [=] {
							if (camp_hp(M1) == "0" || group_state(M1) != "alive") return true;
							if (!bc::self().can_attack()) return false;
							pr("melee_attack_d(1,1)", tryit([&] { bc::self().attack(bc::map::camp(M1)); return true; }) + " hp_after " + camp_hp(M1) + " group " + group_state(M1));
							return false; } });
						S.steps.push_back({ "onto_dead_tile", [=] {
							if (S.sub == 0) pr("move_onto_dead_camp_tile", tryit([&] { return bc::self().move_absolute(M1); }) + " group " + group_state(M1));
							++S.sub;
							if (bc::self().gem_count() > 0)
							{
								pr("captured", "gems " + std::to_string(bc::self().gem_count()) + " group " + group_state(M1));
								return true;
							}
							return false; } });
						S.steps.push_back({ "stand_on_dead_tile", [=] {
							if (S.sub % 5 == 0) pr("standing_on_dead_tile", "group " + group_state(M1) + " pos " + P(bc::self().position()));
							return ++S.sub > 70; } });
						S.steps.push_back({ "step_off", [=] { return walk(OFF); } });
						S.steps.push_back({ "after_step_off", [=] {
							const auto g = group_state(M1);
							if (S.sub % 5 == 0 || g == "alive") pr("after_step_off", "group " + g);
							++S.sub;
							return g == "alive"; } });
						S.steps.push_back({ "walk_T2", [=] { return walk(T2); } });
						S.steps.push_back({ "tribute_d2", [=] { pr("tribute_d(2,2)", tryit([&] { bc::self().submit_gems(AL); return true; })); return true; } });
						S.steps.push_back({ "walk_T1", [=] { return walk(T1); } });
						S.steps.push_back({ "tribute_d1", [=] {
							if (S.sub == 0)
								pr("tribute_d(1,1)", tryit([&] { bc::self().submit_gems(AL); return true; }) + " bag " + std::to_string(bc::self().gem_count()) + " banked " +
									std::to_string(bc::global_submitted_gems(bc::team::ally)));
							else
								pr("tribute_wait", "bag " + std::to_string(bc::self().gem_count()) + " banked " + std::to_string(bc::global_submitted_gems(bc::team::ally)) +
									(bc::self().state().contains(bc::champion_state::submitting_gems) ? " submitting" : ""));
							return ++S.sub > 3; } });
					}
					else
					{
						who = "Vendetta";
						auto dash = [](vec2 to) { return tryit([&] { return bc::self().abilities()[1].use(to); }); };
						auto dash_test = [=](const char* name, vec2 from, vec2 to) {
							return std::pair<std::string, std::function<bool()>>{ name, [=] {
								if (!walk(from)) return false;
								if (!ready(1)) return false;
								pr(name, dash(to) + " from " + P(from) + " to " + P(to));
								return true; } };
						};
						auto where = [](const char* name) {
							return std::pair<std::string, std::function<bool()>>{ name, [=] { pr(name, "pos " + P(bc::self().position())); return true; } };
						};
						S.steps.push_back(dash_test("dash_over_holes_(a)", { 8, 2 }, { 10, 2 }));
						S.steps.push_back(where("after_(a)"));
						S.steps.push_back(dash_test("dash_onto_hole_(e)", { 10, 2 }, { 9, 3 }));
						S.steps.push_back(dash_test("dash_over_walls_(b)", { 12, 2 }, { 14, 2 }));
						S.steps.push_back(where("after_(b)"));
						S.steps.push_back(dash_test("dash_diag_over_hole_(c)", { 16, 1 }, { 18, 3 }));
						S.steps.push_back(where("after_(c)"));
						S.steps.push_back(dash_test("dash_knight_wall_or_hole_(d)", { 16, 5 }, { 18, 6 }));
						S.steps.push_back(where("after_(d)"));
						S.steps.push_back(dash_test("dash_over_camp_(f)", { 14, 7 }, { 16, 7 }));
						S.steps.push_back(where("after_(f)"));
						const vec2 GC{ 1, 9 };
						S.steps.push_back({ "walk_gc", [=] { return walk({ 2, 9 }); } });
						S.steps.push_back({ "kill_gc", [=] {
							if (group_state(GC) != "alive") return true;
							if (bc::self().can_attack()) tryit([&] { bc::self().attack(bc::map::camp(GC)); return true; });
							return false; } });
						S.steps.push_back({ "capture_gc", [=] {
							walk(GC);
							if (bc::self().gold_count() > 0) { pr("gold_captured", std::to_string(bc::self().gold_count())); return true; }
							return false; } });
						auto buy = [=](const char* name) {
							return std::pair<std::string, std::function<bool()>>{ name, [=] {
								if (!walk({ 2, 2 })) return false;
								pr(name, tryit([&] { bc::self().buy(bc::consumable_type::tp_crystal); return true; }) + " gold " + std::to_string(bc::self().gold_count()));
								return true; } };
						};
						auto tp = [](vec2 to) { return tryit([&] { return bc::self().consumables()[bc::consumable_type::tp_crystal].use(to); }); };
						S.steps.push_back(buy("buy_crystal_1"));
						S.steps.push_back({ "walk_c0", [=] { return walk({ 1, 12 }); } });
						S.steps.push_back({ "crystal_tests_1", [=] {
							pr("crystal_d(4,-1)_(k)", tp({ 5, 11 }));
							pr("crystal_onto_hole_(j)", tp({ 1, 15 }));
							pr("crystal_over_walls_d(3,0)_(h)", tp({ 4, 12 }));
							return true; } });
						S.steps.push_back({ "crystal_wait_1", [=] {
							pr("crystal_wait", "pos " + P(bc::self().position()) + (bc::self().state().contains(bc::champion_state::teleporting) ? " teleporting" : ""));
							return ++S.sub > 4; } });
						S.steps.push_back(buy("buy_crystal_2"));
						S.steps.push_back({ "walk_c1", [=] { return walk({ 4, 12 }); } });
						S.steps.push_back({ "crystal_test_2", [=] { pr("crystal_diag_d(3,3)_(i)", tp({ 7, 15 })); return true; } });
						S.steps.push_back({ "crystal_wait_2", [=] {
							pr("crystal_wait", "pos " + P(bc::self().position()) + (bc::self().state().contains(bc::champion_state::teleporting) ? " teleporting" : ""));
							return ++S.sub > 4; } });
					}
				}
				S.run();
			}
		}
		catch (const std::exception& e)
		{
			out(std::string("PR ERR ") + who + " " + e.what());
		}
		bc::end_turn();
	}
}
