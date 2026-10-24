// Shared helpers of the rules probes (rules_main.cpp, rules2_main.cpp): output lines, result capture, camp state, a step script.
#pragma once
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
inline const char* who = "?";
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

inline Script S;  // global: the step lambdas use S.sub without capturing it
