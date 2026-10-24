// Idle opponent for tools/mapintel/run_battery.sh (fresh, from the cambc 3.0.5 starter's main loop): drafts the first champions
// not yet picked and never acts in the game, so the other team plays unopposed (its pace to 1,000 gems is a SIMULATED label).
#include <cambc.h>
namespace bc = cambc;

int main()
{
	while (true)
	{
		try
		{
			if (bc::is_draft())
			{
				const auto chosen = bc::draft::current_draft(bc::team::ally);
				for (int i = 0; i < 12; ++i)
				{
					const auto p = static_cast<bc::champion_draft>(i);
					bool have = false;
					for (const auto c : chosen)
						have |= c == p;
					if (!have)
					{
						bc::draft::pick(p);
						break;
					}
				}
			}
		}
		catch (...)
		{
		}
		bc::end_turn();
	}
}
