// god2 in-bot ladder A/B (session 17): each game plays one on/off combination of the god2 modules, chosen from the map and our side
// (the same FNV-1a hash as bots/god/src/strat.cpp with an empty enemy mask; tools/live/variant_of.py N --nomask recovers it). With
// P.g2ab_n 0 every module is on.
#pragma once
#include <cstdint>

struct G2ab
{
	int variant = -1;
	bool bank = true, deny = true, fight = true, mid = true, walk = true; // the modules; P.g2ab_mods says which A/B bit switches which
};
inline G2ab G2{};

std::uint32_t g2ab_hash(std::uint32_t w, std::uint32_t h, std::uint32_t camps, std::uint32_t side, std::uint32_t enemy_mask);
void g2ab_pick(); // once per game, before the modules are read

#define G2B_ON (P.g2b && G2.bank)
#define G2D_ON (P.g2d_on && G2.deny)
#define G2F_ON (P.g2f_on && G2.fight)
#define G2M_ON (P.g2m_on && G2.mid)
#define G2W_ON (P.g2w_walk > 0.f && G2.walk)
