#include "tp_adapter.h"

#include <algorithm>

#include "params.h"
#include "teamplan/sdk_bridge.h"

namespace tpa
{
const teamplan::Params& params()
{
	static const teamplan::Params p = [] {
		teamplan::Params q;
		q.tb_defer_cap = P.tp_tb_cap;
		q.own_bonus = static_cast<double>(P.tp_own_bonus);
		return q;
	}();
	return p;
}

const teamplan::Consts& consts()
{
	static const teamplan::Consts c = teamplan::consts_from_sdk();
	return c;
}

const teamplan::Kit& kit_of(int type)
{
	static teamplan::Kit k[13];
	static bool have[13] = {};
	const int t = type < 0 || type > 12 ? 0 : type;
	if (!have[t])
		k[t] = teamplan::compute_kit(teamplan::design_of(t), consts(), params()), have[t] = true;
	return k[t];
}

int pick_of_type(int type) { return type < 3 ? type : type <= 4 ? 3 : type - 1; }

int bodies_of_type(int type)
{
	int n = 0;
	for (int t = 0; t < 13; ++t)
		n += pick_of_type(t) == pick_of_type(type) ? 1 : 0;
	return n;
}

namespace
{
std::vector<teamplan::AGroup> g_groups; // the map's groups with the walk from our spawn (draft turn 1, kept in the draft's RAM)
bool g_loaded = false;

void load_groups()
{
	g_loaded = true;
	const bc::bitboard blocked = bc::map::walls() | bc::map::holes() | bc::map::altars() | bc::map::spawn_region(team::enemy);
	bc::bitboard roots = bc::map::spawn_region(team::ally), visited;
	bc::distance_field f;
	f.compute(blocked, roots, visited);
	const auto& prm = params();
	for (const auto& g : bc::map::camp_groups())
	{
		teamplan::AGroup a;
		const int gems = static_cast<int>(g.gem_value()), gold = static_cast<int>(g.gold_value());
		a.value = gems + prm.gold_gems * gold;
		a.gem_free = gems == 0 ? 1 : 0;
		double hp = 0;
		for (const auto& c : g.camps())
		{
			hp += static_cast<double>(c.base_stats().base_health);
			const std::uint16_t d = f.get(c.spawn_position());
			if (d != bc::distance_field::unreachable && (a.walk < 0 || d < a.walk))
				a.walk = d;
		}
		a.hp = hp;
		g_groups.push_back(a);
	}
}
} // namespace

void draft_write_own(int last_pick)
{
	if (!g_loaded)
		load_groups();
	const int G = static_cast<int>(g_groups.size());
	if (G > 250)
		return;
	std::vector<int> picks;
	for (const auto d : bc::draft::current_draft(team::ally))
		picks.push_back(static_cast<int>(d));
	if (last_pick >= 0 && std::find(picks.begin(), picks.end(), last_pick) == picks.end())
		picks.push_back(last_pick);
	std::vector<int> types;
	for (int t = 0; t < 13; ++t)
		if (std::find(picks.begin(), picks.end(), pick_of_type(t)) != picks.end())
			types.push_back(t);
	const int n = std::min<int>(6, static_cast<int>(types.size()));
	if (n == 0)
		return;
	teamplan::Kit kits[6];
	for (int b = 0; b < n; ++b)
		kits[b] = kit_of(types[static_cast<std::size_t>(b)]);
	std::vector<std::uint8_t> owner(static_cast<std::size_t>(G));
	std::vector<int> ord(static_cast<std::size_t>(G));
	std::vector<double> key(static_cast<std::size_t>(G));
	teamplan::assign_groups(g_groups.data(), G, kits, n, (1u << n) - 1u, consts(), params(), owner.data(), nullptr, nullptr, ord.data(), key.data());
	std::vector<std::uint8_t> b(static_cast<std::size_t>(8 + 10 + G + 1), 0);
	b[0] = 0xB7, b[1] = 2;
	b[8] = 0x54, b[9] = 1, b[10] = static_cast<std::uint8_t>(n), b[11] = static_cast<std::uint8_t>(G);
	for (int i = 0; i < 6; ++i)
		b[static_cast<std::size_t>(12 + i)] = i < n ? static_cast<std::uint8_t>(types[static_cast<std::size_t>(i)]) : 255;
	std::uint8_t x = 0;
	for (int g = 0; g < G; ++g)
		b[static_cast<std::size_t>(18 + g)] = owner[static_cast<std::size_t>(g)];
	for (int i = 8; i < 18 + G; ++i)
		x ^= b[static_cast<std::size_t>(i)];
	b[static_cast<std::size_t>(18 + G)] = x;
	bc::draft_memory = b;
}

Own read_own(int my_type, int n_groups)
{
	Own o;
	const auto& m = bc::draft_memory;
	if (m.size() < 19)
		return o;
	auto at = [&](int i) { return std::to_integer<std::uint8_t>(m[static_cast<std::size_t>(i)]); };
	if (at(8) != 0x54 || at(9) != 1 || at(11) != n_groups || static_cast<int>(m.size()) < 19 + n_groups)
		return o;
	std::uint8_t x = 0;
	for (int i = 8; i < 18 + n_groups; ++i)
		x ^= at(i);
	if (x != at(18 + n_groups))
		return o;
	const int n = at(10);
	for (int i = 0; i < n && i < 6; ++i)
		if (at(12 + i) == my_type)
			o.slot = i;
	if (o.slot < 0)
		return o;
	o.owner.resize(static_cast<std::size_t>(n_groups));
	for (int g = 0; g < n_groups; ++g)
		o.owner[static_cast<std::size_t>(g)] = at(18 + g);
	o.ok = true;
	return o;
}
} // namespace tpa
