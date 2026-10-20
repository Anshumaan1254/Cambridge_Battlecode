// Entry point: dispatch draft and gameplay; a failed turn is swallowed and still yields.
#include "brain.h"
#include "draft.h"
#include <cstdio>

int main()
{
	int fails = 0; // P.watchdog: turns in a row that threw out of turn()
	while (true)
	{
		try
		{
			if (bc::is_draft())
				play_draft();
			else
				brain().turn();
			if (P.watchdog)
				fails = 0;
		}
		catch (...)
		{
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
