// Entry point: dispatch draft and gameplay; a failed turn is swallowed and still yields.
#include "brain.h"
#include "draft.h"
#include <cstdio>

int main()
{
	while (true)
	{
		try
		{
			if (bc::is_draft())
				play_draft();
			else
				brain().turn();
		}
		catch (...)
		{
		}
#ifdef LEGEND_TRACE
		debug_block({
			const auto left = bc::fuel_remaining();
			if (!bc::is_draft() && left < 15000)
				std::printf("FUEL low r=%u left=%llu\n", bc::round_number(), static_cast<unsigned long long>(left));
		});
#endif
		bc::end_turn();
	}
}
