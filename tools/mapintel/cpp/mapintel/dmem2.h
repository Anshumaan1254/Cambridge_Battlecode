// mapintel/dmem2.h: draft memory version 2, the whole 1,024 bytes (docs/DRAFT_MEMORY.md, the spec byte by byte). The draft keeps one
// RAM image, rebuilds the blocks this turn's fuel allows after its pick, and submits the image whole; every champion reads the snapshot
// it got at startup through Reader. Python twin: tools/mapintel/dmem2.py (bit-equal; tools/mapintel/test_dmem2.py in the engine).
//
// Layout: 0-3 header (0x54, layout 2, flags: bit 0 final, bit 1 minimal; byte 3 = sum of bytes 4-99 mod 256); 4-99 the table of contents,
// 12 entries x 8 bytes (id, version, offset u16, length u16, checksum = sum of the block's bytes mod 256, valid), entry k = DM2_BLOCKS[k],
// entries 10-11 spare and an unwritten block's entry zero; then TEAM 100, OWN 116, BODY 180, CONT 276, CODE 308, ENEMY 340, NAV 356,
// DEBUG 420 (436-511 free), mapintel's v1 block (dmem.h) at 512 as `M`, the DL block at 864 as `L` when the bot writes one.
// Body slots (TEAM 4-9, OWN nibbles, BODY, CODE zone anchors) are the allies' body types in ascending order: the live slots of
// tools/teamplan/cpp/teamplan/live.h (`live_slot_of`). mapintel's plan 1 (the M block) keeps its own pick order; BODY maps it by type.
//
// Blocks (origins: COMPUTED unless marked):
//   TEAM   0 plan id 0; 1 OWN variants 0; 2 bit 0 tiebreak-prone (plan 4's mode != 0), bits 1-2 that mode; 3 capture rule
//          (teamplan Params::capture_mode, LEARNED); 4-9 body types by slot (255 none); 10 groups OWN covers; 11 bodies OWN covers
//          (below the roster size: recompute OWN in the game, own_recompute); 12-13 the body-type mask OWN was computed for (u16:
//          its slots are those types in ascending order); 14-15 zero.
//   OWN    per group g < 64: low nibble the owner slot, high nibble the next owner (15 none), teamplan::assign_groups on the groups'
//          value (gems + gold_gems x gold, LEARNED weight), total camp health, our walk (as the M block stores it: 255 = none) and
//          gem-free flag; groups beyond the table 0xFF.
//   BODY   6 x 16: 0 role (0 farmer, 1 front, 2 carry, 3 banker), 1-8 build order (the bot's hook; 255 = none), 9-11 plan 1's first
//          three groups for this body type (255 none), 12 bank bag (gems), 13 retreat health (percent), both LEARNED (econ_learn.py);
//          empty slots 0xFF.
//   CONT   0-23 per possible enemy last pick (draft ids 0-11): the BODY build to swap from (the bot's hook; 255 none) and its danger
//          class given their visible picks (0 none, 1 burst, 2 stun chain, 3 big-bag carrier); 24-31 the early-contact plan per case
//          (0 = the base plan: no variants yet).
//   CODE   0-15 8 rally tiles (u16 tile index y * W + x, 0xFFFF none: rally_tiles(), the approaches of plan 3's contested groups and
//          of the bank altars; the live bytes name them as places after the groups and the altars); 16-23 zone anchors per slot (each
//          body's first owned group in schedule order; 255 none); 24-31 altar ids (index in the ascending-tile altar list, as
//          live.h's places) in bank order (plan 2's groups' value per altar).
//   ENEMY  0-3 their predicted first groups (plan 1's first-target step for their visible picks over their nearest groups); 4-7 their
//          bank altar for each (plan 2 by box distance, their side); 8-11 their likely big-bag carriers (body types by passive and kit);
//          12-15 the danger classes of their visible picks (255 = no pick).
//   NAV    hazards.h.
//   DEBUG  0-9 fuel used in draft turns 1-5 (u16 in units of 16, up to the write); 10-11 builder version; 12 draft turns written;
//          13 blocks the guard skipped this turn (bit k = DM2_BLOCKS[k]); 14-15 zero.
// The fuel guard (spec section 7): a guarded block runs only when the fuel left exceeds 1.25 x its last cost + 10,000 (an estimate before
// its first run); otherwise it keeps its earlier valid version.
#pragma once
#include <cambc.h>
#include <algorithm>
#include <array>
#include <optional>
#include <cstdint>
#include <span>
#include <vector>
#include "dmem.h"
#include "hazards.h"
#include "plans.h"
#include "../teamplan/assign.h"
#include "../teamplan/kit.h"
#include "../teamplan/params.h"
#include "../teamplan/sdk_bridge.h"
#if __has_include("model_weights.h")
#include "model_weights.h"
#endif

namespace mapintel
{
inline constexpr std::uint8_t DM2_MAGIC = 0x54, DM2_LAYOUT = 2, DM2_FINAL = 1, DM2_MINIMAL = 2;
inline constexpr int DM2_SIZE = 1024, DM2_TOC = 4, DM2_NTOC = 12, DM2_BUILDER = 1, DM2_NBODY = 13;
inline constexpr int OWN_MAX = 64;
// the guard's cost estimates before a block's first run (upper bounds measured on the 40 official maps by test_dmem2.py; then the
// block's own last cost is used): OWN for the first bodies; ENEMY; CE_EST = the enemy side's tables on ENEMY's first run (the mirrored
// Compact and BankBox::build)
inline constexpr int OWN_EST = 50000, ENEMY_EST = 25000, CE_EST = 40000;
struct BlockSpec
{
	std::uint8_t id;
	int offset, length;
	std::uint8_t version;
};
inline constexpr BlockSpec DM2_BLOCKS[10] = { { 'T', 100, 16, 1 }, { 'O', 116, 64, 1 }, { 'B', 180, 96, 1 }, { 'C', 276, 32, 1 },
											  { 'K', 308, 32, 1 }, { 'E', 340, 16, 1 }, { 'N', 356, 64, 1 }, { 'D', 420, 16, 1 },
											  { 'M', 512, 352, 1 }, { 'L', 864, 136, 1 } };
enum : int
{
	BK_TEAM = 0,
	BK_OWN,
	BK_BODY,
	BK_CONT,
	BK_CODE,
	BK_ENEMY,
	BK_NAV,
	BK_DEBUG,
	BK_MAP,
	BK_DL
};

// ---- the economy constants BODY needs (model_weights.h when generated; else the economy model's defaults)
inline void econ_body(int& bank_bag, int& retreat_pct)
{
#ifdef MAPINTEL_ECON_BODY
	bank_bag = ECON_BANK_BAG, retreat_pct = ECON_RETREAT_PCT;
#else
	bank_bag = 40, retreat_pct = 30;
#endif
}

// ---- kits of every body type and the danger features (draft turn 1: all 13 designs ~20k fuel)
struct Kits13
{
	teamplan::Design d[DM2_NBODY];
	teamplan::Kit k[DM2_NBODY];
	double alpha[DM2_NBODY]{};		 // one round's damage: a basic attack + every damaging spell at once (mod x focus)
	std::uint8_t carrier[DM2_NBODY]{}; // big-bag carrier score: 4 gems-to-focus, 2 gold per tributed gem, 1 gold bonus (passive tags)
	double burst_thr = 0;			 // the floor(13 / 3)-th largest alpha: a body at or above it is a burst threat
	teamplan::Consts c;
	teamplan::Params p;
};

inline double kit_alpha(const teamplan::Design& d)
{
	double a = d.str;
	for (int s = 0; s < 2; ++s)
	{
		const auto& ab = d.ab[s];
		if ((ab.kind == teamplan::AB_DAMAGE || ab.kind == teamplan::AB_AOE || ab.kind == teamplan::AB_CC || ab.kind == teamplan::AB_DASH) && ab.mod > 0)
			a += ab.mod * d.foc;
	}
	return a;
}

inline void kits_finish(Kits13& K)
{
	double s[DM2_NBODY];
	for (int t = 0; t < DM2_NBODY; ++t)
	{
		K.alpha[t] = kit_alpha(K.d[t]);
		const auto& k = K.k[t];
		K.carrier[t] = static_cast<std::uint8_t>((k.focus_per_gem > 0 ? 4 : 0) + (k.tribute_gold > 0 ? 2 : 0) + (k.gold_mult > 1 ? 1 : 0));
		s[t] = K.alpha[t];
	}
	std::sort(s, s + DM2_NBODY, [](double a, double b) { return a > b; });
	K.burst_thr = s[DM2_NBODY / 3 - 1];
}

inline Kits13 kits13_from_sdk(const teamplan::Params& p = teamplan::Params{})
{
	Kits13 K;
	K.c = teamplan::consts_from_sdk(), K.p = p;
	for (int t = 0; t < DM2_NBODY; ++t)
		K.d[t] = teamplan::design_of(t), K.k[t] = teamplan::compute_kit(K.d[t], K.c, K.p);
	kits_finish(K);
	return K;
}

// kits of some body types only (the champions' OWN recompute needs its roster's: ~2.7k fuel a type instead of 35k for all 13); the other
// entries stay default and the danger features (alpha, carrier, burst_thr) are not computed
inline Kits13 kits_of_types(const int* types, int n, const teamplan::Params& p = teamplan::Params{})
{
	Kits13 K;
	K.c = teamplan::consts_from_sdk(), K.p = p;
	for (int i = 0; i < n; ++i)
		if (types[i] >= 0 && types[i] < DM2_NBODY)
			K.d[types[i]] = teamplan::design_of(types[i]), K.k[types[i]] = teamplan::compute_kit(K.d[types[i]], K.c, K.p);
	return K;
}

// danger class of draft pick `pick` against the context picks (the others visible): 1 burst, else 2 stun chain (it stuns and another
// context pick stuns), else 3 big-bag carrier, else 0
inline int pick_class(const Kits13& K, int pick, const int* ctx, int nctx)
{
	int b[2];
	const int nb = pick_bodies(pick, b);
	bool burst = false, stun = false, carry = false, cstun = false;
	for (int i = 0; i < nb; ++i)
		burst |= K.alpha[b[i]] >= K.burst_thr, stun |= K.k[b[i]].stun > 0, carry |= K.carrier[b[i]] > 0;
	for (int j = 0; j < nctx; ++j)
	{
		if (ctx[j] == pick)
			continue;
		int c[2];
		const int nc = pick_bodies(ctx[j], c);
		for (int i = 0; i < nc; ++i)
			cstun |= K.k[c[i]].stun > 0;
	}
	return burst ? 1 : (stun && cstun) ? 2 : carry ? 3 : 0;
}

// the bodies of the picks in ascending body type (the slots), at most 6
inline int roster_types(const int* picks, int np, int out[NSLOT])
{
	int n = 0;
	for (int i = 0; i < np; ++i)
	{
		int b[2];
		const int nb = pick_bodies(picks[i], b);
		for (int k = 0; k < nb && n < NSLOT; ++k)
			out[n++] = b[k];
	}
	std::sort(out, out + n);
	return static_cast<int>(std::unique(out, out + n) - out);
}

// ---- OWN
struct OwnResult
{
	std::array<std::uint8_t, OWN_MAX> b{};
	int n = 0, G = 0;
	unsigned mask = 0;							// body types covered (bit t)
	std::uint8_t anchor[NSLOT] = { 255, 255, 255, 255, 255, 255 }; // each slot's first group in the schedule (its highest key)
};

// the groups as OWN sees them: the first min(G, 64) groups; walk = our walk as the M block stores it (0-254, else none)
inline std::vector<teamplan::AGroup> own_groups(const Compact& C, const MapView& m, const teamplan::Params& p)
{
	const int G = std::min(static_cast<int>(m.groups.size()), OWN_MAX);
	std::vector<teamplan::AGroup> out(static_cast<std::size_t>(G));
	for (int g = 0; g < G; ++g)
	{
		const auto& grp = m.groups[static_cast<std::size_t>(g)];
		auto& a = out[static_cast<std::size_t>(g)];
		a.value = grp.gems + p.gold_gems * grp.gold;
		a.hp = C.prep[static_cast<std::size_t>(g)].tot;
		const int d = C.dU[static_cast<std::size_t>(g)];
		a.walk = d >= 0 && d <= 254 ? d : -1;
		a.gem_free = grp.gems == 0 ? 1 : 0;
	}
	return out;
}

inline OwnResult build_own(const std::vector<teamplan::AGroup>& gs, const int* types, int n, const Kits13& K)
{
	OwnResult r;
	r.G = static_cast<int>(gs.size()), r.n = n;
	teamplan::Kit kits[NSLOT];
	for (int s = 0; s < n; ++s)
		kits[s] = K.k[types[s]], r.mask |= 1u << types[s];
	std::uint8_t owner[OWN_MAX], run[OWN_MAX];
	int ord[OWN_MAX];
	double key[OWN_MAX];
	if (n > 0 && r.G > 0)
		teamplan::assign_groups(gs.data(), r.G, kits, n, (1u << n) - 1u, K.c, K.p, owner, nullptr, nullptr, ord, key, run);
	else
		for (int g = 0; g < r.G; ++g)
			owner[g] = run[g] = teamplan::kNoOwner;
	for (int g = 0; g < OWN_MAX; ++g)
	{
		if (g >= r.G)
		{
			r.b[static_cast<std::size_t>(g)] = 0xFF;
			continue;
		}
		const int o = owner[g] == teamplan::kNoOwner ? 15 : owner[g], u = run[g] == teamplan::kNoOwner ? 15 : run[g];
		r.b[static_cast<std::size_t>(g)] = static_cast<std::uint8_t>(o | (u << 4));
	}
	if (n > 0)
	{
		int m = 0;
		for (int g = 0; g < r.G; ++g)
			m += gs[static_cast<std::size_t>(g)].walk >= 0 ? 1 : 0;
		for (int i = 0; i < m; ++i)
		{
			const int g = ord[i], s = owner[g];
			if (s < n && r.anchor[s] == 255)
				r.anchor[s] = static_cast<std::uint8_t>(g);
		}
	}
	return r;
}

// ---- TEAM
inline std::array<std::uint8_t, 16> build_team(const Plans& P, const int* types, int n, const OwnResult* own, int capture_mode)
{
	std::array<std::uint8_t, 16> b{};
	b[2] = static_cast<std::uint8_t>((P.mode != 0 ? 1 : 0) | ((P.mode & 3) << 1));
	b[3] = static_cast<std::uint8_t>(capture_mode);
	for (int s = 0; s < NSLOT; ++s)
		b[static_cast<std::size_t>(4 + s)] = s < n ? static_cast<std::uint8_t>(types[s]) : 255;
	if (own)
	{
		b[10] = static_cast<std::uint8_t>(own->G), b[11] = static_cast<std::uint8_t>(own->n);
		b[12] = static_cast<std::uint8_t>(own->mask & 0xFF), b[13] = static_cast<std::uint8_t>((own->mask >> 8) & 0xFF);
	}
	return b;
}

// ---- BODY
using BuildHook = void (*)(int slot, int type, const int* types, int n, std::uint8_t out[8]);

// roles: the banker = the highest gold multiplier above 1 (the capture rule's choice), else the highest gold per tributed gem; the
// front = the first other body of teamplan::front_order (and the second at 5+ bodies); the carry = the remaining body with the highest
// damage per round; the rest farm (ties: the lower slot)
inline void body_roles(const int* types, int n, const Kits13& K, std::uint8_t role[NSLOT])
{
	for (int s = 0; s < NSLOT; ++s)
		role[s] = 0;
	int bank = -1;
	for (int s = 0; s < n; ++s)
		if (K.k[types[s]].gold_mult > 1 && (bank < 0 || K.k[types[s]].gold_mult > K.k[types[bank]].gold_mult))
			bank = s;
	if (bank < 0)
		for (int s = 0; s < n; ++s)
			if (K.k[types[s]].tribute_gold > 0 && (bank < 0 || K.k[types[s]].tribute_gold > K.k[types[bank]].tribute_gold))
				bank = s;
	if (bank >= 0)
		role[bank] = 3;
	teamplan::Kit kits[NSLOT];
	for (int s = 0; s < n; ++s)
		kits[s] = K.k[types[s]];
	std::uint8_t ord[NSLOT];
	teamplan::front_order(kits, n, ord);
	int fronts = 0;
	for (int i = 0; i < n && fronts < (n >= 5 ? 2 : 1); ++i)
		if (ord[i] != bank)
			role[ord[i]] = 1, ++fronts;
	int carry = -1;
	for (int s = 0; s < n; ++s)
		if (role[s] == 0 && s != bank && (carry < 0 || kits[s].dps > kits[carry].dps))
			carry = s;
	if (carry >= 0)
		role[carry] = 2;
}

inline std::array<std::uint8_t, 96> build_body(const int* types, int n, const Kits13& K, const Plans& P, int bank_bag, int retreat_pct,
											  BuildHook hook = nullptr)
{
	std::array<std::uint8_t, 96> b;
	b.fill(0xFF);
	std::uint8_t role[NSLOT];
	body_roles(types, n, K, role);
	for (int s = 0; s < n && s < NSLOT; ++s)
	{
		const auto o = static_cast<std::size_t>(16 * s);
		b[o] = role[s];
		if (hook)
			hook(s, types[s], types, n, b.data() + o + 1);
		int ps = -1;
		for (int i = 0; i < P.nbody; ++i)
			if (P.body[i] == types[s])
				ps = i;
		for (int k = 0; k < 3; ++k)
			b[o + 9 + static_cast<std::size_t>(k)] = ps >= 0 && k < P.ntgt[ps] && P.tgt[ps][k].g >= 0 ? static_cast<std::uint8_t>(P.tgt[ps][k].g) : 255;
		b[o + 12] = static_cast<std::uint8_t>(std::min(255, std::max(0, bank_bag)));
		b[o + 13] = static_cast<std::uint8_t>(std::min(100, std::max(0, retreat_pct)));
		b[o + 14] = b[o + 15] = 0;
	}
	return b;
}

// ---- CONT
using SwapHook = int (*)(int pick, const int* types, int n); // the BODY build to swap from when this enemy pick shows (255 = none)

inline std::array<std::uint8_t, 32> build_cont(const Kits13& K, const int* enemy_picks, int ne, const int* types, int n, SwapHook hook = nullptr)
{
	std::array<std::uint8_t, 32> b{};
	for (int p = 0; p < 12; ++p)
	{
		b[static_cast<std::size_t>(2 * p)] = hook ? static_cast<std::uint8_t>(hook(p, types, n)) : 255;
		b[static_cast<std::size_t>(2 * p + 1)] = static_cast<std::uint8_t>(pick_class(K, p, enemy_picks, ne));
	}
	return b; // 24-31: early-contact plan ids, all 0 (the base plan)
}

// ---- CODE
// altars by the value of plan 2's groups banking there (descending, ties: the lower altar), altars with at least one group; up to 8
inline int bank_order(const Compact& C, const Plans& P, int out[8])
{
	int nA = 0;
	for (const int a : P.bank)
		if (a != 255 && a + 1 > nA)
			nA = a + 1;
	std::vector<double> sum(static_cast<std::size_t>(nA), 0.0);
	std::vector<int> cnt(sum.size(), 0);
	for (std::size_t g = 0; g < P.bank.size(); ++g)
		if (P.bank[g] >= 0 && P.bank[g] < static_cast<int>(sum.size()))
			sum[static_cast<std::size_t>(P.bank[g])] += C.val[g], ++cnt[static_cast<std::size_t>(P.bank[g])];
	int n = 0;
	for (int a = 0; a < static_cast<int>(sum.size()); ++a)
	{
		if (cnt[static_cast<std::size_t>(a)] == 0)
			continue;
		int j = n < 8 ? n++ : 8;
		if (j == 8)
		{
			if (!(sum[static_cast<std::size_t>(a)] > sum[static_cast<std::size_t>(out[7])]))
				continue;
			j = 7;
		}
		while (j > 0 && sum[static_cast<std::size_t>(out[j - 1])] < sum[static_cast<std::size_t>(a)])
			out[j] = out[j - 1], --j;
		out[j] = a;
	}
	return n;
}

// rally tiles (CODE 0-15), places 51+ of the live bytes (teamplan/live.h place_code): first the approach of each contested group of
// plan 3 (up to 5, plan 3's order): from its camp tile nearest our spawn (Compact::near_tile), the traced walk towards our spawn (the
// first neighbour N, NE, E, SE, S, SW, W, NW one step nearer on our field) to its first tile outside every striking camp's range
// (Chebyshev > the largest range of the group's camps with strength; a group without one: the first tile that is no camp tile), where
// a team gathers before it wakes the group; then the approach of each bank altar in bank order (the standable tile within Chebyshev
// 1, the tribute range, nearest our spawn; no camp tile unless every one is; ties: the lower tile); then the remaining contested
// groups' approaches; a tile already listed is skipped; unreached groups and altars give none. Up to 8.
inline int rally_tiles(const Compact& C, const MapView& m, const Plans& P, const int* bank_ord, int nbo, int out[8])
{
	const auto& f = m.fc[0];
	int n = 0;
	auto add = [&](int t) {
		if (t < 0 || n >= 8)
			return;
		for (int k = 0; k < n; ++k)
			if (out[k] == t)
				return;
		out[n++] = t;
	};
	auto group_rally = [&](int g) {
		const int t0 = C.near_tile(g);
		if (g < 0 || g >= static_cast<int>(m.groups.size()) || t0 < 0 || f[t0] < 0)
			return -1;
		const auto& grp = m.groups[static_cast<std::size_t>(g)];
		int R = -1;
		for (const auto& c : grp.camps)
			if (c.str > 0)
				R = std::max(R, c.range);
		int x = t0 % m.W, y = t0 / m.W;
		for (int step = 0; step <= f[t0]; ++step)
		{
			bool out_of_reach = true;
			for (const auto& c : grp.camps)
			{
				const int d = std::max(std::abs(c.x - x), std::abs(c.y - y));
				if (R >= 0 ? (c.str > 0 && d <= R) : d == 0)
					out_of_reach = false;
			}
			const int v = f[m.at(x, y)];
			if (out_of_reach || v == 0)
				return m.at(x, y);
			int k = 0;
			for (; k < 8; ++k)
			{
				const int nx = x + NAV_DX[k], ny = y + NAV_DY[k];
				if (m.in(nx, ny) && f[m.at(nx, ny)] == v - 1)
					break;
			}
			if (k == 8)
				return -1;
			x += NAV_DX[k], y += NAV_DY[k];
		}
		return -1;
	};
	auto altar_rally = [&](int a) {
		if (a < 0 || a >= static_cast<int>(m.altar_tiles.size()))
			return -1;
		const auto p = m.altar_tiles[static_cast<std::size_t>(a)];
		int best[2] = { -1, -1 }, bv[2] = { 0, 0 };
		for (int dy = -1; dy <= 1; ++dy)
			for (int dx = -1; dx <= 1; ++dx)
			{
				const int x = p.x + dx, y = p.y + dy;
				if ((dx == 0 && dy == 0) || !m.in(x, y) || !m.pass(0, x, y))
					continue;
				const int t = m.at(x, y), v = f[t];
				if (v < 0 || (best[0] >= 0 && v >= bv[0]))
					continue; // tiles in ascending order: an equal later one never wins; the camp lookup only for a candidate
				const int c = m.camp_type(t) >= 0 ? 1 : 0;
				if (best[c] < 0 || v < bv[c])
					best[c] = t, bv[c] = v;
			}
		return best[0] >= 0 ? best[0] : best[1];
	};
	const int nc = std::min(P.ncon, NCON);
	int k = 0;
	for (; k < nc && n < 5; ++k)
		add(group_rally(P.con[k][0]));
	for (int j = 0; j < nbo && j < 8 && n < 8; ++j)
		add(altar_rally(bank_ord[j]));
	for (; k < nc && n < 8; ++k)
		add(group_rally(P.con[k][0]));
	return n;
}

// CODE from the rally tiles (rally_tiles(): roster-free, so a draft computes them once, on turn 1, and keeps them), the OWN anchors
// and the bank order
inline std::array<std::uint8_t, 32> build_code(const int* rt, int nr, const OwnResult* own, const int* bank_ord, int nbo)
{
	std::array<std::uint8_t, 32> b{};
	for (int k = 0; k < 8; ++k)
	{
		const int v = k < nr ? rt[k] : 0xFFFF;
		b[static_cast<std::size_t>(2 * k)] = static_cast<std::uint8_t>(v & 0xFF), b[static_cast<std::size_t>(2 * k + 1)] = static_cast<std::uint8_t>(v >> 8);
	}
	for (int k = 0; k < 8; ++k)
		b[static_cast<std::size_t>(16 + k)] = own && k < NSLOT ? own->anchor[k] : 255;
	for (int k = 0; k < 8; ++k)
		b[static_cast<std::size_t>(24 + k)] = k < nbo ? static_cast<std::uint8_t>(bank_ord[k]) : 255;
	return b;
}

// ---- the enemy's bank altars: Compact::bank_box with the altars' approach tiles tabled once per side. bank_box picks the first
// (altar, tile) with the least min(box distance, 6 + walk); per altar that least is min(the least box distance over its approach tiles,
// 6 + the least walk), so the result is the first altar with the least of those; an altar whose lower bound (box distance to the altar
// - 1, or that least walk) cannot beat the best so far is skipped. Equal to bank_box for every group, at a fraction of its fuel
// (bank_box ~20k a call on lanes).
struct BankBox
{
	int W = 0;
	std::vector<int> ax, ay, rec, off;	 // per altar: tile, 6 + the least walk of its approach tiles (huge: none reached), tiles [off[a], off[a+1])
	std::vector<std::int16_t> tx, ty;

	void build(const MapView& m, int side)
	{
		const int nA = static_cast<int>(m.altar_tiles.size());
		W = m.W;
		ax.resize(static_cast<std::size_t>(nA)), ay.resize(ax.size()), rec.assign(ax.size(), 1 << 29), off.assign(ax.size() + 1, 0);
		tx.reserve(static_cast<std::size_t>(8 * nA)), ty.reserve(static_cast<std::size_t>(8 * nA));
		const auto& f = m.fc[side == 1 ? 1 : 0];
		for (int a = 0; a < nA; ++a)
		{
			const auto at = m.altar_tiles[static_cast<std::size_t>(a)];
			ax[static_cast<std::size_t>(a)] = at.x, ay[static_cast<std::size_t>(a)] = at.y;
			for (int dy = -1; dy <= 1; ++dy)
				for (int dx = -1; dx <= 1; ++dx)
				{
					const int x = at.x + dx, y = at.y + dy;
					if ((dx == 0 && dy == 0) || !m.in(x, y) || !m.pass(side == 1 ? 1 : 0, x, y))
						continue;
					tx.push_back(static_cast<std::int16_t>(x)), ty.push_back(static_cast<std::int16_t>(y));
					const int v = f[m.at(x, y)];
					if (v >= 0 && 6 + v < rec[static_cast<std::size_t>(a)])
						rec[static_cast<std::size_t>(a)] = 6 + v;
				}
			off[static_cast<std::size_t>(a + 1)] = static_cast<int>(tx.size());
		}
	}
	int best(const Compact& C, int g) const
	{
		if (g < 0 || g >= static_cast<int>(C.bx.size()))
			return 255;
		const auto& b = C.bx[static_cast<std::size_t>(g)];
		auto box = [&](int x, int y) { return std::max(std::max(std::max(b[0] - x, x - b[2]), std::max(b[1] - y, y - b[3])), 0); };
		int bestc = 1 << 30, out = 255;
		for (std::size_t a = 0; a + 1 < off.size(); ++a)
		{
			if (off[a] == off[a + 1])
				continue;
			const int lb = std::min(std::max(0, box(ax[a], ay[a]) - 1), rec[a]);
			if (lb >= bestc)
				continue;
			int c = rec[a];
			for (int i = off[a]; i < off[a + 1] && c > lb; ++i)
				c = std::min(c, box(tx[static_cast<std::size_t>(i)], ty[static_cast<std::size_t>(i)]));
			if (c < bestc)
				bestc = c, out = static_cast<int>(a);
		}
		return out;
	}
};

// ---- ENEMY (CE = the enemy-side Compact: Compact(view, F, 1))
inline std::array<std::uint8_t, 16> build_enemy(const Compact& CE, const BankBox& BB, const Kits13& K, const int* enemy_picks, int ne)
{
	std::array<std::uint8_t, 16> b;
	b.fill(255);
	int bodies[NSLOT], nb = 0;
	for (int i = 0; i < ne; ++i)
	{
		int x[2];
		const int k = pick_bodies(enemy_picks[i], x);
		for (int j = 0; j < k && nb < NSLOT; ++j)
			bodies[nb++] = x[j];
	}
	// their reached groups nearest their spawn (ties: the lower index), the first max(4, bodies) of them, at most 6
	const int want = std::min(NSLOT, std::max(4, nb));
	int cand[NSLOT], m = 0;
	for (int g = 0; g < static_cast<int>(CE.dU.size()); ++g)
	{
		const int d = CE.dU[static_cast<std::size_t>(g)];
		if (d < 0)
			continue;
		int j = m < want ? m++ : want;
		if (j == want)
		{
			if (!(d < CE.dU[static_cast<std::size_t>(cand[want - 1])]))
				continue;
			j = want - 1;
		}
		while (j > 0 && CE.dU[static_cast<std::size_t>(cand[j - 1])] > d)
			cand[j] = cand[j - 1], --j;
		cand[j] = g;
	}
	int order[NSLOT * 2], no = 0;
	if (nb > 0 && m > 0)
	{
		int as[NSLOT];
		CE.first_assign(bodies, nb, cand, m, as);
		for (int i = 0; i < nb; ++i)
		{
			bool dup = as[i] < 0;
			for (int k = 0; k < no && !dup; ++k)
				dup = order[k] == as[i];
			if (!dup)
				order[no++] = as[i];
		}
	}
	for (int j = 0; j < m; ++j)
	{
		bool dup = false;
		for (int k = 0; k < no && !dup; ++k)
			dup = order[k] == cand[j];
		if (!dup)
			order[no++] = cand[j];
	}
	for (int k = 0; k < 4 && k < no; ++k)
		b[static_cast<std::size_t>(k)] = static_cast<std::uint8_t>(order[k]), b[static_cast<std::size_t>(4 + k)] = static_cast<std::uint8_t>(BB.best(CE, order[k]));
	// carriers: carrier score descending, ties in body order
	int nc = 0, cb[NSLOT];
	for (int i = 0; i < nb; ++i)
	{
		if (K.carrier[bodies[i]] == 0)
			continue;
		int j = nc++;
		while (j > 0 && K.carrier[bodies[cb[j - 1]]] < K.carrier[bodies[i]])
			cb[j] = cb[j - 1], --j;
		cb[j] = i;
	}
	for (int k = 0; k < 4 && k < nc; ++k)
		b[static_cast<std::size_t>(8 + k)] = static_cast<std::uint8_t>(bodies[cb[k]]);
	for (int k = 0; k < 4 && k < ne; ++k)
		b[static_cast<std::size_t>(12 + k)] = static_cast<std::uint8_t>(pick_class(K, enemy_picks[k], enemy_picks, ne));
	return b;
}

// ---- L (mapintel's DL outputs at 864, 136 bytes, version 1; docs/DRAFT_MEMORY.md 5.9): the step-7 models the bot carries (dl_weights.h)
//   0 flags: bit 0 the opening ranking, bit 1 the routes; 1 source: 1 computed in this draft (dl_weights.h), 2 copied from known_maps.h's
//   tables (dl_tables.py); 2-3 the round the late phase of the next model starts (u16); 4-5, 6-7 the next model's round input per phase;
//   8-23 the opening model's ranking (16 groups, best first, 255 none); 24-59 per body slot (TEAM order) a route of 6 groups: the
//   body's plan-1 first target (the M block), then each next the next model's best group after the previous one at the early phase,
//   skipping groups already on the route (from its two best; the route ends when both are on it; 255 none); 60-135 zero.
// The routes need the next model's best two groups after every group: known maps carry them (zero fuel); an unknown map's draft would
// score every group per step (~87k), so there the routes are left out and only the opening ranking is computed (dl_inputs ~62k +
// dl_opening_scores ~91k, on draft turn 1 when the guard allows). Champions of a known map read the same table in the game
// (known_maps.h known_dl_next) after any capture.
inline constexpr int DL_SIZE = 136;
// next_early: the table of our team at the early phase, [13 body types][G][2] (KnownMap::dl_next + 2 * (team * 2 * 13 * G)), or null
inline std::array<std::uint8_t, DL_SIZE> build_dl(const std::uint8_t* open16, int source, const std::uint8_t* next_early, int G, const int* types,
												  int n, const Plans* P, int split, int r_early, int r_late)
{
	std::array<std::uint8_t, DL_SIZE> b{};
	b[1] = static_cast<std::uint8_t>(source);
	b[2] = static_cast<std::uint8_t>(split & 0xFF), b[3] = static_cast<std::uint8_t>(split >> 8);
	b[4] = static_cast<std::uint8_t>(r_early & 0xFF), b[5] = static_cast<std::uint8_t>(r_early >> 8);
	b[6] = static_cast<std::uint8_t>(r_late & 0xFF), b[7] = static_cast<std::uint8_t>(r_late >> 8);
	for (int k = 0; k < 16; ++k)
		b[static_cast<std::size_t>(8 + k)] = open16 ? open16[k] : 255;
	if (open16)
		b[0] |= 1;
	for (int k = 24; k < 60; ++k)
		b[static_cast<std::size_t>(k)] = 255;
	if (next_early && P && P->nbody > 0)
	{
		b[0] |= 2;
		for (int s = 0; s < n && s < NSLOT; ++s)
		{
			std::uint8_t* r = b.data() + 24 + 6 * s;
			int ps = -1;
			for (int i = 0; i < P->nbody; ++i)
				if (P->body[i] == types[s])
					ps = i;
			const int first = ps >= 0 && P->ntgt[ps] > 0 ? P->tgt[ps][0].g : -1;
			if (first < 0 || first >= G)
				continue;
			r[0] = static_cast<std::uint8_t>(first);
			for (int k = 1; k < 6; ++k)
			{
				const std::uint8_t* c = next_early + 2 * (types[s] * G + r[k - 1]);
				int pick = 255;
				for (int j = 0; j < 2 && pick == 255; ++j)
				{
					bool on = c[j] == 255;
					for (int i = 0; i < k && !on; ++i)
						on = r[i] == c[j];
					if (!on)
						pick = c[j];
				}
				if (pick == 255)
					break;
				r[k] = static_cast<std::uint8_t>(pick);
			}
		}
	}
	return b;
}

// ---- NAV inputs: anchor groups = the first_scores() ranking when given, else the reached groups nearest our spawn
inline void nav_anchor_groups(const Compact& C, std::span<const int> rank, int out[4])
{
	int n = 0;
	for (const int g : rank)
		if (n < 4 && g >= 0 && g < static_cast<int>(C.dU.size()) && C.dU[static_cast<std::size_t>(g)] >= 0)
			out[n++] = g;
	if (rank.empty())
		for (int k = 0; k < 4; ++k)
		{
			int best = -1;
			for (int g = 0; g < static_cast<int>(C.dU.size()); ++g)
			{
				const int d = C.dU[static_cast<std::size_t>(g)];
				bool used = false;
				for (int i = 0; i < n; ++i)
					used |= out[i] == g;
				if (d >= 0 && !used && (best < 0 || d < C.dU[static_cast<std::size_t>(best)]))
					best = g;
			}
			if (best >= 0)
				out[n++] = best;
		}
	for (int k = n; k < 4; ++k)
		out[k] = -1;
}

inline std::array<std::uint8_t, NAV_SIZE> nav_from_table(const std::uint8_t* src)
{
	std::array<std::uint8_t, NAV_SIZE> b{};
	for (int k = 0; k < NAV_SIZE; ++k)
		b[static_cast<std::size_t>(k)] = src[k];
	b[61] = NAV_SRC_TABLE;
	return b;
}

// ---- DEBUG
inline std::array<std::uint8_t, 16> build_debug(const long long used[5], int turns, std::uint8_t skips)
{
	std::array<std::uint8_t, 16> b{};
	for (int k = 0; k < 5; ++k)
	{
		const long long v = std::min<long long>(65535, std::max<long long>(0, used[k] / 16));
		b[static_cast<std::size_t>(2 * k)] = static_cast<std::uint8_t>(v & 0xFF), b[static_cast<std::size_t>(2 * k + 1)] = static_cast<std::uint8_t>(v >> 8);
	}
	b[10] = DM2_BUILDER & 0xFF, b[11] = (DM2_BUILDER >> 8) & 0xFF, b[12] = static_cast<std::uint8_t>(turns), b[13] = skips;
	return b;
}

// ---- the image
struct Image
{
	std::array<std::uint8_t, DM2_SIZE> b{};

	// copy a block to its offset and fill its table entry (valid)
	void put(int k, const std::uint8_t* data, int len)
	{
		const auto& s = DM2_BLOCKS[k];
		const int n = std::min(len, s.length);
		unsigned sum = 0;
		for (int i = 0; i < n; ++i)
			b[static_cast<std::size_t>(s.offset + i)] = data[i], sum += data[i];
		for (int i = n; i < s.length; ++i)
			b[static_cast<std::size_t>(s.offset + i)] = 0;
		auto* e = &b[static_cast<std::size_t>(DM2_TOC + 8 * k)];
		e[0] = s.id, e[1] = s.version, e[2] = static_cast<std::uint8_t>(s.offset & 0xFF), e[3] = static_cast<std::uint8_t>(s.offset >> 8);
		e[4] = static_cast<std::uint8_t>(s.length & 0xFF), e[5] = static_cast<std::uint8_t>(s.length >> 8), e[6] = static_cast<std::uint8_t>(sum & 0xFF), e[7] = 1;
	}
	template <std::size_t N>
	void put(int k, const std::array<std::uint8_t, N>& a)
	{
		put(k, a.data(), static_cast<int>(N));
	}
	void drop(int k)
	{
		for (int i = 0; i < 8; ++i)
			b[static_cast<std::size_t>(DM2_TOC + 8 * k + i)] = 0;
	}
	void seal(std::uint8_t flags)
	{
		unsigned sum = 0;
		for (int i = DM2_TOC; i < DM2_TOC + 8 * DM2_NTOC; ++i)
			sum += b[static_cast<std::size_t>(i)];
		b[0] = DM2_MAGIC, b[1] = DM2_LAYOUT, b[2] = flags, b[3] = static_cast<std::uint8_t>(sum & 0xFF);
	}
	void submit() const { cambc::draft_memory = b; }
};

// ---- the reader (any process; never throws, never reads outside the buffer)
struct Reader
{
	const std::uint8_t* p = nullptr;
	std::size_t n = 0;
	bool ok = false; // the header is valid

	bool load(const std::uint8_t* data, std::size_t size)
	{
		p = data, n = size, ok = false;
		if (!p || n < static_cast<std::size_t>(DM2_TOC + 8 * DM2_NTOC) || p[0] != DM2_MAGIC || p[1] != DM2_LAYOUT)
			return false;
		unsigned sum = 0;
		for (int i = DM2_TOC; i < DM2_TOC + 8 * DM2_NTOC; ++i)
			sum += p[i];
		ok = (sum & 0xFF) == p[3];
		return ok;
	}
	bool load()
	{
		try
		{
			return load(reinterpret_cast<const std::uint8_t*>(cambc::draft_memory.data()), cambc::draft_memory.size());
		}
		catch (...)
		{
			p = nullptr, n = 0, ok = false;
			return false;
		}
	}
	std::uint8_t flags() const { return ok ? p[2] : 0; }
	// the block with this id and version: a pointer to its bytes (and its length), or nullptr (missing, other version, outside the
	// buffer, wrong checksum, not valid): the caller falls back
	const std::uint8_t* block(std::uint8_t id, std::uint8_t version, int* len = nullptr) const
	{
		if (!ok)
			return nullptr;
		for (int k = 0; k < DM2_NTOC; ++k)
		{
			const std::uint8_t* e = p + DM2_TOC + 8 * k;
			if (e[0] != id)
				continue;
			const int off = e[2] | (e[3] << 8), ln = e[4] | (e[5] << 8);
			if (e[1] != version || e[7] != 1 || off < DM2_TOC + 8 * DM2_NTOC || ln <= 0 || static_cast<std::size_t>(off + ln) > n || off + ln > DM2_SIZE)
				return nullptr;
			unsigned sum = 0;
			for (int i = 0; i < ln; ++i)
				sum += p[off + i];
			if ((sum & 0xFF) != e[6])
				return nullptr;
			if (len)
				*len = ln;
			return p + off;
		}
		return nullptr;
	}
};

// TEAM helpers: our slot (the index of our body type in bytes 4-9), the roster size
inline int team_slot(const std::uint8_t* team, int my_type)
{
	for (int s = 0; s < NSLOT; ++s)
		if (team[4 + s] == my_type)
			return s;
	return -1;
}
inline int team_size_of(const std::uint8_t* team)
{
	int n = 0;
	for (int s = 0; s < NSLOT; ++s)
		n += team[4 + s] != 255 ? 1 : 0;
	return n;
}
inline int own_owner(const std::uint8_t* own, int g) { return g >= 0 && g < OWN_MAX && own[g] != 0xFF && (own[g] & 15) != 15 ? own[g] & 15 : -1; }
inline int own_next(const std::uint8_t* own, int g) { return g >= 0 && g < OWN_MAX && own[g] != 0xFF && (own[g] >> 4) != 15 ? own[g] >> 4 : -1; }

// ---- the in-game OWN recompute (docs/DRAFT_MEMORY.md 7): when TEAM byte 11 is below the roster size, every body rebuilds the table
// for the full roster from the same inputs: the engine's groups (camp_groups, as load_view: values and camp health), the walks of the
// M block (bytes 87+g) and the kits of TEAM's body types (design_of). The draft built the same groups (own_groups), so every body gets
// the draft's table. The work is resumable across game turns: step(floor) reads the groups one by one, then the kits, then runs
// teamplan::assign_groups (up to ~56k at once), and returns true when the table is ready (out); it stops whenever the fuel left would
// fall below `floor`. Fuel: measured by tools/mapintel/test_dmem2.py (MAPAnalysis.md 7.2).
struct OwnRecompute
{
	int stage = 0, g = 0, G = 0, n = 0;
	bool failed = false;
	int types[NSLOT]{};
	std::vector<teamplan::AGroup> gs;
	std::vector<cambc::map::camp_group> groups;
	std::uint8_t walk[OWN_MAX]{};
	std::optional<Kits13> K;
	OwnResult out;
	cambc::camp_stats design[8]{};
	bool have[8]{};

	static long long left() { return static_cast<long long>(cambc::fuel_remaining()); }
	bool step(const Reader& r, long long floor, const teamplan::Params& p = teamplan::Params{})
	{
		if (failed)
			return false;
		try
		{
			if (stage == 0)
			{
				const std::uint8_t* team = r.block('T', DM2_BLOCKS[BK_TEAM].version);
				const std::uint8_t* mb = r.block('M', DM2_BLOCKS[BK_MAP].version);
				Block B;
				if (!team || !mb || !dmem_parse_block(mb, B))
					return failed = true, false;
				G = std::min<int>(B.b[13], OWN_MAX);
				for (int k = 0; k < G; ++k)
					walk[k] = B.b[static_cast<std::size_t>(87 + k)];
				for (int s = 0; s < NSLOT; ++s)
					if (team[4 + s] != 255 && team[4 + s] < DM2_NBODY)
						types[n++] = team[4 + s];
				gs.assign(static_cast<std::size_t>(G), {});
				stage = 1;
			}
			if (stage == 1)
			{
				if (groups.empty())
				{
					if (left() < floor + 50000)
						return false;
					groups = cambc::map::camp_groups(); // one batched host call; kept until the table is built
				}
				for (; g < G && g < static_cast<int>(groups.size()); ++g)
				{
					if (left() < floor + 12000)
						return false;
					const auto& cg = groups[static_cast<std::size_t>(g)];
					double hp = 0; // the camps' total health = group_prep's tot (integer healths: any summation order is exact)
					for (const auto& c : cg.camps())
					{
						const int k = static_cast<int>(c.kind());
						const int kk = k < 0 || k >= 8 ? 0 : k;
						if (k < 0 || k >= 8 || !have[k])
						{
							design[kk] = c.base_stats();
							if (k >= 0 && k < 8)
								have[k] = true;
						}
						hp += static_cast<double>(design[kk].base_health);
					}
					auto& a = gs[static_cast<std::size_t>(g)];
					const int gems = static_cast<int>(cg.gem_value()), gold = static_cast<int>(cg.gold_value());
					a.value = gems + p.gold_gems * gold;
					a.hp = hp;
					a.walk = walk[g] == 255 ? -1 : walk[g];
					a.gem_free = gems == 0 ? 1 : 0;
				}
				if (g < G)
					return failed = true, false; // fewer groups than the draft saw
				stage = 2;
			}
			if (stage == 2)
			{
				if (left() < floor + 3000 * n + 5000)
					return false;
				K.emplace(kits_of_types(types, n, p));
				stage = 3;
			}
			if (stage == 3)
			{
				if (left() < floor + 60000)
					return false;
				out = build_own(gs, types, n, *K);
				stage = 4;
				groups.clear(), groups.shrink_to_fit();
			}
			return stage == 4;
		}
		catch (...)
		{
			failed = true;
			return false;
		}
	}
};

// ---- the draft side: the image, the guard, the fuel per turn
struct Guard
{
	long long last[10] = { -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 };
	// runs when the fuel left exceeds 1.25 x the last cost (or the estimate before the first run) + 10,000
	bool ok(int k, long long left, long long estimate = -1) const
	{
#ifdef MAPINTEL_DM2_NO_GUARD
		return true; // measurement builds only: every block runs
#endif
		const long long c = last[k] >= 0 ? last[k] : estimate;
		return c < 0 || left > c + c / 4 + 10000;
	}
};

struct Draft2
{
	Image img;
	Guard guard;
	long long start = 0, used[5]{};
	int turn = 0;
	std::uint8_t skips = 0;

	void begin()
	{
		start = static_cast<long long>(cambc::fuel_remaining());
		++turn, skips = 0;
	}
	// run a guarded block builder (f writes the block into img); returns whether it ran
	template <class F>
	bool run(int k, F&& f, long long estimate = -1)
	{
		const long long left = static_cast<long long>(cambc::fuel_remaining());
		if (!guard.ok(k, left, estimate))
		{
			if (k < 8)
				skips |= static_cast<std::uint8_t>(1u << k);
			return false;
		}
		f();
		guard.last[k] = left - static_cast<long long>(cambc::fuel_remaining());
		return true;
	}
	// DEBUG (the fuel used this turn so far), the header, the whole image
	void write(bool final_turn, bool minimal)
	{
		if (turn >= 1 && turn <= 5)
			used[turn - 1] = start - static_cast<long long>(cambc::fuel_remaining());
		img.put(BK_DEBUG, build_debug(used, turn, skips));
		img.seal(static_cast<std::uint8_t>((final_turn ? DM2_FINAL : 0) | (minimal ? DM2_MINIMAL : 0)));
		img.submit();
	}
};
} // namespace mapintel
