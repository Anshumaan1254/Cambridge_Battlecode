// Second rules probe for tools/mapintel (fresh code; nothing from bots/). Map maps/probe_mi/mi_rules2.map26a (rules2_map.mjs). Team A drafts
// Stellar, Vendetta, Ryth; results are "PR <round> <body> <test> <result>" lines on team A's stdout:
//   area spell at a ground tile the caster cannot see; dash through an altar tile and through a bush; dash and crystal onto a dead camp's
//   tile; crystal onto an altar; crystal over holes.
//   cambc run _mi_rules2 _mi_rules2 --map maps/probe_mi/mi_rules2.map26a --rounds 300 -o DIR
#include "probe_common.h"

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
				bc::draft::pick(static_cast<bc::champion_draft>(teamA ? want[chosen.size()] : static_cast<int>(chosen.size()) + 5));
			}
			else if ((teamA = bc::map::spawn_region(bc::team::ally).is_set({ 1, 1 })))
			{
				auto& me = bc::self();
				if (!init)
				{
					init = true;
					const auto t = me.champion_name();
					if (t == bc::champion_type::stellar)
					{
						who = "Stellar";
						const vec2 S0{ 6, 6 }, GT{ 10, 5 }, X1{ 10, 6 };
						S.steps.push_back({ "walk_S0", [=] { return walk(S0); } });
						S.steps.push_back({ "aoe_unseen_ground", [=] {
							if (!ready(1)) return false;
							pr("aoe_at_unseen_ground_d(4,-1)", std::string("ground_visible ") + (bc::vision::visible_tiles().is_set(GT) ? "yes" : "no") + " camp_visible " +
								(bc::vision::visible_tiles().is_set(X1) ? "yes" : "no") + " cast " + tryit([&] { return bc::self().abilities()[1].use(GT); }));
							return true; } });
						S.steps.push_back({ "walk_see", [=] { return walk({ 9, 8 }); } });
						S.steps.push_back({ "aoe_result", [=] { pr("aoe_unseen_result", "X1 hp " + camp_hp(X1)); return true; } });
					}
					else if (t == bc::champion_type::vendetta)
					{
						who = "Vendetta";
						auto dash_test = [=](const char* name, vec2 from, vec2 to) {
							return std::pair<std::string, std::function<bool()>>{ name, [=] {
								if (!walk(from)) return false;
								if (!ready(1)) return false;
								pr(name, tryit([&] { return bc::self().abilities()[1].use(to); }) + " from " + P(from) + " to " + P(to));
								return true; } };
						};
						auto where = [](const char* name) {
							return std::pair<std::string, std::function<bool()>>{ name, [=] { pr(name, "pos " + P(bc::self().position())); return true; } };
						};
						auto kill = [=](const char* name, vec2 stand, vec2 c) {
							return std::pair<std::string, std::function<bool()>>{ name, [=] {
								if (!walk(stand)) return false;
								if (group_state(c) != "alive") return true;
								if (bc::self().can_attack()) tryit([&] { bc::self().attack(bc::map::camp(c)); return true; });
								return false; } };
						};
						auto capture = [=](const char* name, vec2 c) {
							return std::pair<std::string, std::function<bool()>>{ name, [=] {
								walk(c);
								if (group_state(c).rfind("respawning", 0) == 0) { pr(name, "gold " + std::to_string(bc::self().gold_count())); return true; }
								return false; } };
						};
						auto tp = [](vec2 to) { return tryit([&] { return bc::self().consumables()[bc::consumable_type::tp_crystal].use(to); }); };
						auto buy = [=](const char* name) {
							return std::pair<std::string, std::function<bool()>>{ name, [=] {
								if (!walk({ 2, 2 })) return false;
								pr(name, tryit([&] { bc::self().buy(bc::consumable_type::tp_crystal); return true; }) + " gold " + std::to_string(bc::self().gold_count()));
								return true; } };
						};
						auto wait_tp = [=](const char* name) {
							return std::pair<std::string, std::function<bool()>>{ name, [=] {
								pr(name, "pos " + P(bc::self().position()) + (bc::self().state().contains(bc::champion_state::teleporting) ? " teleporting" : ""));
								return ++S.sub > 4; } };
						};
						const vec2 G7{ 17, 10 }, GC1{ 1, 9 }, GC2{ 3, 9 };
						S.steps.push_back(dash_test("dash_through_altar", { 13, 2 }, { 15, 2 }));
						S.steps.push_back(where("after_altar"));
						S.steps.push_back(dash_test("dash_through_bush", { 13, 6 }, { 15, 6 }));
						S.steps.push_back(where("after_bush"));
						S.steps.push_back(kill("kill_G7", { 16, 10 }, G7));
						S.steps.push_back(dash_test("dash_onto_dead_camp_tile", { 15, 10 }, G7));
						S.steps.push_back(where("after_dead_tile"));
						S.steps.push_back({ "g7_state", [=] { pr("g7_state_after_landing", group_state(G7)); return ++S.sub > 6; } });
						S.steps.push_back(kill("kill_gc1", { 2, 10 }, GC1));
						S.steps.push_back(capture("capture_gc1", GC1));
						S.steps.push_back(kill("kill_gc2", { 2, 10 }, GC2));
						S.steps.push_back(capture("capture_gc2", GC2));
						S.steps.push_back(buy("buy_1"));
						S.steps.push_back({ "walk_a", [=] { return walk({ 13, 4 }); } });
						S.steps.push_back({ "crystal_onto_altar", [=] { pr("crystal_onto_altar_d(1,-2)", tp({ 14, 2 })); return true; } });
						S.steps.push_back({ "walk_h", [=] { return walk({ 9, 11 }); } });
						S.steps.push_back({ "crystal_over_holes", [=] { pr("crystal_over_holes_d(0,3)", tp({ 9, 14 })); return true; } });
						S.steps.push_back(wait_tp("wait_1"));
						S.steps.push_back(buy("buy_2"));
						S.steps.push_back({ "walk_d", [=] { return walk({ 17, 13 }); } });
						S.steps.push_back({ "crystal_onto_dead_camp", [=] { pr("crystal_onto_dead_camp_tile_d(0,-3)", tp(G7) + " g7 " + group_state(G7)); return true; } });
						S.steps.push_back(wait_tp("wait_2"));
					}
					else
						who = "Ryth";
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
