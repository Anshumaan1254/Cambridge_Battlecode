// Entry point: dispatch draft and gameplay; a failed turn is swallowed and still yields.
#include "brain.h"
#include "draft.h"
#include "mi_game.h"
#include "params.h"
#include <cstdio>
#include <exception>

namespace
{
// v9 watchdog (P.watchdog9): a turn that keeps throwing (an unexpected map or SDK state) used to idle the body for the rest of the
// game. After P.watchdog9 consecutive failures this plays a minimal, defensive turn instead: bank if next to an altar, else hit a
// visible camp in range, else walk home. Every call is guarded; the next normal turn resets the counter.
void fallback_turn()
{
	auto& me = bc::self();
	if (!me.is_alive())
		return;
	const vec2 p = me.position();
	if (me.gem_count() > 0)
		for (const auto a : bc::map::altars().positions())
			if (cheb(a, p) <= 1)
			{
				me.submit_gems(a);
				return;
			}
	if (me.can_attack())
		for (const auto& c : bc::vision::camps())
			if (c.is_alive() && cheb(c.position(), p) <= me.attack_range())
			{
				me.attack(c);
				return;
			}
	if (me.can_move())
	{
		const auto home = bc::map::spawn_region(team::ally).positions();
		if (!home.empty())
			me.move_towards(home.front());
	}
}
} // namespace

int main()
{
	int fails = 0; // P.watchdog / P.watchdog9: turns in a row that threw out of turn()
	while (true)
	{
		try
		{
			if (bc::is_draft())
				play_draft();
			else
			{
				brain().turn();
				if (P.mi_own > 0.f)
					mig::tail(); // GOD v12: the in-game OWN recompute, with fuel to spare
			}
			if (P.watchdog || P.watchdog9)
				fails = 0;
		}
#ifdef EXC_TRACE
		catch (const std::exception& e)
		{
			// GOD_Improvement_Plan INF-4: count exceptions (any is a bug to fix, not a case for the watchdog); tools/exccount.py.
			debug_block({ std::printf("EXC r=%u what=%s\n", bc::round_number(), e.what()); });
		}
#endif
		catch (...)
		{
#ifdef EXC_TRACE
			debug_block({ std::printf("EXC r=%u what=unknown\n", bc::round_number()); });
#endif
			if (P.watchdog9 > 0 && !bc::is_draft() && ++fails >= P.watchdog9)
			{
				try
				{
					fallback_turn();
				}
				catch (...)
				{
				}
			}
			if (P.watchdog && !bc::is_draft() && ++fails >= 3)
			{
#ifdef LEGEND_TRACE
				debug_block({ std::printf("WATCHDOG r=%u fails=%d\n", bc::round_number(), fails); });
#endif
				brain().safe_fallback();
			}
		}
#ifdef LEGEND_TRACE
		debug_block({
			const auto left = bc::fuel_remaining();
			if (!bc::is_draft() && left < 15000)
				std::printf("FUEL low r=%u left=%llu\n", bc::round_number(), static_cast<unsigned long long>(left));
		});
#endif
#ifdef FUEL_TRACE
		// tools/fueltrace.py: fuel left when the turn ends (debug_block pauses fuel; the read itself exists only in FUEL_TRACE builds).
		{
			const auto left = bc::fuel_remaining();
			debug_block({
				if (!bc::is_draft())
				{
					std::printf("FL r=%u %llu\n", bc::round_number(), static_cast<unsigned long long>(left));
#ifdef FUEL_STATE
					brain().debug_state(static_cast<unsigned long long>(left));
#endif
				}
			});
		}
#endif
#ifdef SM_TRACE
		// tools/actiondiff.py: the 8 shared bytes after every game turn (debug_block pauses fuel: the trace changes nothing).
		debug_block({
			if (!bc::is_draft())
			{
				std::printf("SM r=%u", bc::round_number());
				for (std::size_t i = 0; i < 8; ++i)
					std::printf(" %02x", static_cast<unsigned>(bc::shared_memory[i]));
				std::printf("\n");
			}
		});
#endif
		bc::end_turn();
	}
}
