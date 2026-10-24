// Test bot of the mapintel library (built fresh from the cambc 3.0.5 starter's main loop; built as the git-ignored bots/_mi_test by
// tools/mapintel/test_library.py). On its first draft turn it computes the fingerprint, the runtime features, the table lookup and the
// draft-time plans, and prints them with the fuel each part cost; on every later draft turn it checks the fuel left; it then picks
// through mapintel::forced_pick() when a roster table is present, else the first free champions; in the game it ends every turn.
//   MI T fp <hex> ts <n> fuel_fp <f> fuel_view <f> fuel_feat <f> fuel_plan <f> table <0|1> turn_fuel_left <f>
//   MI F <name> <value %.17g>        (one line per feature, FEATURE_NAMES order)
//   MI K <entry index or -1> archetype <i> ...                    (known_maps.h / model_weights.h, when present)
//   MI P ...                                                      (plans.h output, when present)
//   MI E <what>                                                   (any exception)
#include <cambc.h>
#include <cstdio>
#include <string>
#include "mapintel/features.h"
#include "mapintel/fingerprint.h"
#include "mapintel/force_roster.h"
#if __has_include("mapintel/known_maps.h")
#include "mapintel/known_maps.h"
#define MI_HAS_TABLE 1
#endif
#if __has_include("mapintel/plans.h")
#include "mapintel/plans.h"
#define MI_HAS_PLANS 1
#endif
namespace bc = cambc;

static void line(const std::string& s)
{
	const std::string t = s + "\n";
	std::fputs(t.c_str(), stdout);
	std::fflush(stdout);
}

int main()
{
	bool first = true;
	while (true)
	{
		try
		{
			if (bc::is_draft())
			{
				if (first)
				{
					first = false;
					const auto f0 = bc::fuel_remaining();
					const auto ts = mapintel::team_size_now();
					const auto fp = mapintel::fingerprint(ts);
					const auto f1 = bc::fuel_remaining();
					const auto view = mapintel::load_view(ts);
					const auto f2 = bc::fuel_remaining();
					const auto F = mapintel::compute_features(view);
					const auto f3 = bc::fuel_remaining();
					int table = 0;
					std::string extra;
#ifdef MI_HAS_TABLE
					const int e = mapintel::find_known(fp);
					table = e >= 0;
					extra += "MI K " + std::to_string(e);
#endif
#ifdef MI_HAS_PLANS
					const auto plan = mapintel::make_plans(view, F);
					extra += (extra.empty() ? "" : "\n") + mapintel::describe(plan);
#endif
					const auto f4 = bc::fuel_remaining();
					char buf[320];
					std::snprintf(buf, sizeof buf, "MI T fp %016llx ts %d fuel_fp %llu fuel_view %llu fuel_feat %llu fuel_plan %llu table %d turn_fuel_left %llu",
						static_cast<unsigned long long>(fp), ts, static_cast<unsigned long long>(f0 - f1), static_cast<unsigned long long>(f1 - f2),
						static_cast<unsigned long long>(f2 - f3), static_cast<unsigned long long>(f3 - f4), table, static_cast<unsigned long long>(f4));
					line(buf);
					for (int i = 0; i < mapintel::NF; ++i)
					{
						std::snprintf(buf, sizeof buf, "MI F %s %.17g", mapintel::FEATURE_NAMES[i], F.v[i]);
						line(buf);
					}
					if (!extra.empty())
						line(extra);
				}
				else
					line("MI L turn_fuel_left " + std::to_string(bc::fuel_remaining()));
				if (const int p = mapintel::forced_pick(); p >= 0)
				{
					bc::draft::pick(static_cast<bc::champion_draft>(p));
				}
				else
				{
					const auto chosen = bc::draft::current_draft(bc::team::ally);
					bc::draft::pick(static_cast<bc::champion_draft>(static_cast<int>(chosen.size())));
				}
			}
		}
		catch (const std::exception& e)
		{
			line(std::string("MI E ") + e.what());
		}
		catch (...)
		{
			line("MI E unknown");
		}
		bc::end_turn();
	}
}
