#include "g2ab.h"
#include "common.h"
#include "params.h"

std::uint32_t g2ab_hash(std::uint32_t w, std::uint32_t h, std::uint32_t camps, std::uint32_t side, std::uint32_t enemy_mask)
{
	// FNV-1a over five words, then a finaliser (the same arithmetic as tools/live/variant_of.py)
	std::uint32_t x = 2166136261u;
	const std::uint32_t words[5] = { w, h, camps, side, enemy_mask };
	for (std::uint32_t v : words)
	{
		x ^= v;
		x *= 16777619u;
	}
	x ^= x >> 15;
	x *= 0x2c1b3c6du;
	x ^= x >> 12;
	x *= 0x297a2d39u;
	x ^= x >> 15;
	return x;
}

void g2ab_pick()
{
	if (G2.variant >= 0 || P.g2ab_n <= 0)
		return;
	std::uint32_t camps = 0, side = 0;
	try
	{
		for (const auto& g : bc::map::camp_groups())
			camps += static_cast<std::uint32_t>(g.camps().size());
		side = bc::detail::sdk_my_team() == 0 ? 0u : 1u;
	}
	catch (...)
	{
	}
	const std::uint32_t x = g2ab_hash(static_cast<std::uint32_t>(bc::map::width()), static_cast<std::uint32_t>(bc::map::height()), camps, side, static_cast<std::uint32_t>(P.g2ab_salt));
	const int v = static_cast<int>(x % static_cast<std::uint32_t>(P.g2ab_n));
	G2.variant = v;
	// P.g2ab_mods: one hex digit per A/B bit, lowest digit = bit 0: the module that bit switches (0 bank, 1 deny, 2 fight, 3 mid, 4 walk;
	// F = no module). Modules not named stay on (their own master switches decide).
	bool* mod[5] = { &G2.bank, &G2.deny, &G2.fight, &G2.mid, &G2.walk };
	for (int k = 0; k < 4; ++k)
	{
		const int m = (P.g2ab_mods >> (4 * k)) & 15;
		if (m < 5)
			*mod[m] = ((v >> k) & 1) != 0;
	}
}
