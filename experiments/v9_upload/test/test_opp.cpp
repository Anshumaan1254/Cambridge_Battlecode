// Behaviour test of the v9 opponent model (opp.cpp) on scripted scenarios. Links the real opp.cpp; the SDK and the bot's
// singletons are replaced by the minimal fakes below (the stub cambc.h only declares the SDK).
#include "../src/comms.h"
#include "../src/learn.h"
#include "../src/opp.h"
#include "../src/params.h"
#include "../src/world.h"
#include <cstdio>
#include <random>
#include <string>

namespace cambc
{
bitboard::bitboard() {}
bitboard::bitboard(const bitboard&) {}
bitboard::bitboard(bitboard&&) noexcept {}
bitboard& bitboard::operator=(const bitboard&) { return *this; }
bitboard& bitboard::operator=(bitboard&&) noexcept { return *this; }
distance_field::distance_field() {}
distance_field::distance_field(const distance_field&) {}
distance_field::distance_field(distance_field&&) noexcept {}
distance_field& distance_field::operator=(const distance_field&) { return *this; }
distance_field& distance_field::operator=(distance_field&&) noexcept { return *this; }
std::int32_t unit::attack_range() const { return 1; }
float unit::focus() const { return 0; }
float unit::health() const { return 0; }
bool unit::is_visible() const { return false; }
float unit::max_health() const { return 0; }
vec2 unit::position() const { return {}; }
float unit::strength() const { return 0; }
champion::champion(champion_type) {}
int g_ours = 0, g_theirs = 0;
std::uint32_t global_submitted_gems(team t) { return static_cast<std::uint32_t>(t == team::ally ? g_ours : g_theirs); }
} // namespace cambc

World& world() { static World w; return w; }
Learner& learner() { static Learner l; return l; }
Comms& comms() { static Comms c; return c; }

struct Sim
{
	std::mt19937 rng{ 3 };
	std::string log;
	int last_plan = -1;
	void setup()
	{
		auto& W = world();
		W.groups.clear();
		for (int i = 0; i < 6; ++i)
		{
			Group g;
			g.id = i;
			g.ours = i < 3; // groups 0-2 on our half
			W.groups.push_back(std::move(g));
		}
		W.allies.clear();
		for (int i = 0; i < 4; ++i)
			W.allies.push_back(Ally{ bc::champion(bc::champion_type::ren), static_cast<std::uint32_t>(i), bc::champion_type::ren });
		W.enemies.clear();
		for (int i = 0; i < 4; ++i)
			W.enemies.push_back(Enemy{ std::nullopt, static_cast<std::uint32_t>(10 + i), bc::champion_type::ren, Kit{} });
		for (int i = 0; i < 6; ++i)
			comms().claim[static_cast<std::size_t>(i)] = i < 4 ? i % 3 : -1; // everyone farms our half
		opp() = OppModel{};
		bc::g_ours = bc::g_theirs = 0;
	}
	void kill_ally(int i, int round)
	{
		auto& W = world();
		auto& a = W.allies[static_cast<std::size_t>(i)];
		if (!a.alive)
			return;
		a.alive = false, a.died_round = round, ++W.ally_deaths;
	}
	void respawn(int round)
	{
		for (auto& a : world().allies)
			if (!a.alive && round - a.died_round >= 60)
				a.alive = true;
	}
	void step(int round, bool contact)
	{
		respawn(round);
		opp().tick(round, contact, 0);
		if (opp().plan != last_plan)
		{
			char buf[96];
			std::snprintf(buf, sizeof buf, "r%d:%s ", round, plan_name(opp().plan));
			log += buf;
			last_plan = opp().plan;
		}
	}
	bool burst(double share) // bursty sightings, episodes of mean 5 rounds
	{
		static bool on = false;
		const double p_end = 0.2, p_start = share * p_end / (1 - share);
		std::uniform_real_distribution<double> u(0, 1);
		on = on ? u(rng) >= p_end : u(rng) < p_start;
		return on;
	}
};

int main()
{
	std::printf("params: window %d ema %.2f hi %.2f consec %d home_deaths %d race_margin %d deny_at %d\n", P.opp_window, P.opp_ema,
		P.opp_contact_hi, P.opp_consec, P.opp_home_deaths, P.opp_race_margin, P.opp_deny_at);
	{
		// A. Even farmer (same pace, 5% contact): should stay FARM all game.
		Sim s;
		s.setup();
		for (int r = 2; r <= 1200; ++r)
		{
			if (r % 40 == 0) bc::g_ours += 30, bc::g_theirs += 30;
			s.step(r, s.burst(0.05));
		}
		std::printf("A even farmer         : %s\n", s.log.c_str());
	}
	{
		// B. Quiet farmer that out-farms us 1.6x; our trades even: HUNT expected, then DENY near 850.
		Sim s;
		s.setup();
		for (int r = 2; r <= 1400; ++r)
		{
			if (r % 40 == 0) bc::g_ours += 25, bc::g_theirs += 40;
			s.step(r, s.burst(0.04));
		}
		std::printf("B faster farmer       : %s (theirs %d ours %d)\n", s.log.c_str(), bc::g_theirs, bc::g_ours);
	}
	{
		// C. Farmer until r400, then invades: 50% contact and two of our deaths on our half at r430 / r436.
		Sim s;
		s.setup();
		for (int r = 2; r <= 800; ++r)
		{
			if (r % 40 == 0) bc::g_ours += 30, bc::g_theirs += 30;
			if (r == 430) s.kill_ally(1, r);
			if (r == 436) s.kill_ally(2, r);
			s.step(r, r < 400 ? s.burst(0.05) : s.burst(0.5));
		}
		std::printf("C invader from r400   : %s\n", s.log.c_str());
	}
	{
		// D. Invasion with no deaths (presence only, 50% contact from r400): the slower contact path.
		Sim s;
		s.setup();
		for (int r = 2; r <= 800; ++r)
		{
			if (r % 40 == 0) bc::g_ours += 30, bc::g_theirs += 30;
			s.step(r, r < 400 ? s.burst(0.05) : s.burst(0.5));
		}
		std::printf("D presence-only invade: %s\n", s.log.c_str());
	}
	{
		// E. Lost team fights away from home (claims on their half): 2 deaths within 4 rounds, twice: EVADE.
		Sim s;
		s.setup();
		for (int i = 0; i < 4; ++i)
			comms().claim[static_cast<std::size_t>(i)] = 3 + i % 3; // farming their half
		for (int r = 2; r <= 700; ++r)
		{
			if (r % 40 == 0) bc::g_ours += 30, bc::g_theirs += 30;
			if (r == 300) s.kill_ally(0, r);
			if (r == 302) s.kill_ally(3, r);
			if (r == 335) s.kill_ally(1, r);
			if (r == 337) s.kill_ally(2, r);
			s.step(r, s.burst(0.05));
		}
		std::printf("E lost team fights    : %s\n", s.log.c_str());
	}

	{
		// F. Invader until r600 (50% contact, deaths at r200/r205 on our half), then passive and slower than us: DEFEND, then FARM.
		Sim s;
		s.setup();
		for (int r = 2; r <= 1100; ++r)
		{
			if (r % 40 == 0) bc::g_ours += 30, bc::g_theirs += r < 600 ? 30 : 20;
			if (r == 200) s.kill_ally(1, r);
			if (r == 205) s.kill_ally(2, r);
			s.step(r, r < 600 ? s.burst(0.5) : s.burst(0.03));
		}
		std::printf("F invader then passive: %s\n", s.log.c_str());
	}
	{
		// G. Invasion that we win: 50% contact from r300, they lose a champion every ~25 rounds, we lose none: PUNISH.
		Sim s;
		s.setup();
		for (int r = 2; r <= 700; ++r)
		{
			if (r % 40 == 0) bc::g_ours += 30, bc::g_theirs += 30;
			if (r >= 300 && r % 25 == 0) ++world().enemy_deaths;
			s.step(r, r < 300 ? s.burst(0.05) : s.burst(0.5));
		}
		std::printf("G invasion we win     : %s\n", s.log.c_str());
	}
	{
		// H. Faster quiet farmer and our trades are lost (we lose a champion every 50 rounds away from home, one at a time): RACE.
		Sim s;
		s.setup();
		for (int i = 0; i < 4; ++i)
			comms().claim[static_cast<std::size_t>(i)] = 3 + i % 3;
		int k = 0;
		for (int r = 2; r <= 900; ++r)
		{
			if (r % 40 == 0) bc::g_ours += 25, bc::g_theirs += 40;
			if (r % 50 == 0) s.kill_ally(k++ % 4, r);
			s.step(r, s.burst(0.04));
		}
		std::printf("H faster, trades lost : %s\n", s.log.c_str());
	}
	{
		// J. Mid-match switcher (the guide's timeline): even farmer until r400; invades r400-700 (50% contact, two of our deaths
		// on our half at r430 / r436); then turns passive and out-farms us 1.6x until the end.
		Sim s;
		s.setup();
		for (int r = 2; r <= 1500; ++r)
		{
			if (r % 40 == 0) bc::g_ours += r < 700 ? 30 : 25, bc::g_theirs += r < 700 ? 30 : 40;
			if (r == 430) s.kill_ally(1, r);
			if (r == 436) s.kill_ally(2, r);
			s.step(r, (r >= 400 && r < 700) ? s.burst(0.5) : s.burst(0.04));
		}
		std::printf("J mid-match switcher  : %s (theirs %d ours %d)\n", s.log.c_str(), bc::g_theirs, bc::g_ours);
	}
	{
		// I. False alarms: even farmer, sightings deep in our half 8% / 12% of rounds (bursty), 200 seeded games each.
		for (double share : { 0.08, 0.12 })
		{
			int left = 0;
			for (int seed = 0; seed < 200; ++seed)
			{
				Sim s;
				s.rng.seed(static_cast<unsigned>(1000 + seed));
				s.setup();
				bool moved = false;
				for (int r = 2; r <= 2000; ++r)
				{
					if (r % 40 == 0) bc::g_ours += 20, bc::g_theirs += 20;
					s.step(r, s.burst(share));
					moved |= opp().plan != PL_FARM;
				}
				left += moved;
			}
			std::printf("I false alarms share %.2f: %d of 200 games left FARM at least once\n", share, left);
		}
	}
	return 0;
}
