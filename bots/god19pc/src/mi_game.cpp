// mi_game.cpp: the champion side of draft memory version 2 (mi_game.h).
#include "mi_game.h"

#include <algorithm>
#include <array>
#include <cstdio>

#include "common.h"
#include "params.h"
#include "mapintel/dmem2.h"
#if __has_include("mapintel/known_maps.h")
#include "mapintel/known_maps.h"
#define MI_HAS_TABLE 1
#endif

namespace mi = mapintel;

namespace
{
struct State
{
	mi::Reader r;
	const std::uint8_t *team = nullptr, *own = nullptr, *body = nullptr, *code = nullptr, *mblk = nullptr, *dl = nullptr;
	int slot = -1, my_type = -1, ngroups = 0, known = -1, kteam = -1, captures = 0;
	bool own_partial = false, own_done = false;
	mi::OwnRecompute orc;
	// after a capture: the next model's two best groups until next_until
	int next[2] = { -1, -1 }, next_until = -1;
};

State& S()
{
	static State s; // static: the recompute holds vectors (the wasm shadow stack is small)
	return s;
}

const std::uint8_t* own_table()
{
	auto& s = S();
	if (s.own_partial)
		return s.own_done ? s.orc.out.b.data() : nullptr;
	return s.own;
}
} // namespace

namespace mig
{
void init(int my_type, int ngroups)
{
	auto& s = S();
	s.my_type = my_type, s.ngroups = ngroups;
	if (!s.r.load())
		return;
	s.team = s.r.block('T', 1);
	s.own = s.r.block('O', 1);
	s.body = s.r.block('B', 1);
	s.code = s.r.block('K', 1);
	s.mblk = s.r.block('M', 1);
	s.dl = s.r.block('L', 1);
	if (s.team)
	{
		s.slot = mi::team_slot(s.team, my_type);
		s.own_partial = s.team[11] < mi::team_size_of(s.team);
	}
	// the map's groups must be the M block's (the same camp_groups() order, at most 64)
	if (s.mblk && s.mblk[13] != std::min(ngroups, mi::NGRP))
		s.team = s.own = s.body = s.code = s.dl = nullptr, s.slot = -1;
#ifdef MI_HAS_TABLE
	if (s.mblk)
	{
		std::uint64_t fp = 0;
		for (int k = 0; k < 8; ++k)
			fp |= static_cast<std::uint64_t>(s.mblk[2 + k]) << (8 * k);
		s.known = mi::find_known(fp);
		if (s.known >= 0 && mi::KNOWN[s.known].ngroups == ngroups)
			s.kteam = mi::known_team_game(mi::KNOWN[s.known]);
		else
			s.known = -1;
	}
#endif
#ifdef MI_TRACE
	{
		const std::uint8_t* dbg = s.r.block('D', 1);
		int blocks = 0;
		for (int k = 0; k < 10; ++k)
			blocks |= s.r.block(mi::DM2_BLOCKS[k].id, mi::DM2_BLOCKS[k].version) ? 1 << k : 0;
		std::printf("MIG type=%d slot=%d n=%d known=%d kteam=%d partial=%d blocks=%d flags=%d fuel=", my_type, s.slot, s.team ? mi::team_size_of(s.team) : -1,
					s.known, s.kteam, s.own_partial ? 1 : 0, blocks, s.r.flags());
		for (int t = 0; dbg && t < 5; ++t)
			std::printf("%d,", 16 * (dbg[2 * t] | dbg[2 * t + 1] << 8));
		std::printf(" skips=%d\n", dbg ? dbg[13] : -1);
		std::fflush(stdout);
	}
#endif
}

void tail()
{
	auto& s = S();
	if (!(P.mi_own > 0.f) || !s.own_partial || s.own_done || s.orc.failed || !s.team || s.ngroups > P.mi_own_maxg)
		return;
	if (bc::fuel_remaining() < 60000)
		return; // only with fuel to spare (the recompute stops at its floor and resumes next turn)
	if (s.orc.step(s.r, 30000))
		s.own_done = true;
}

float group_mult(int g, int round)
{
	const auto& s = S();
	if (s.slot < 0 || g < 0 || g >= mi::NGRP)
		return 1.f;
	float m = 1.f;
	if (P.mi_own > 0.f && s.ngroups <= P.mi_own_maxg)
		if (const std::uint8_t* own = own_table(); own && mi::own_owner(own, g) == s.slot)
			m *= 1.f + P.mi_own;
	if (P.mi_next > 0.f && round <= s.next_until)
	{
		if (g == s.next[0])
			m *= 1.f + P.mi_next;
		else if (g == s.next[1])
			m *= 1.f + 0.5f * P.mi_next;
	}
	if (P.mi_open > 0.f && s.captures == 0 && s.body)
	{
		const std::uint8_t* b = s.body + 16 * s.slot;
		if (b[9] == g)
			m *= 1.f + P.mi_open;
		else if (b[10] == g || b[11] == g)
			m *= 1.f + 0.5f * P.mi_open;
	}
	return m;
}

void on_capture(int g, int round)
{
	auto& s = S();
	++s.captures;
	s.next[0] = s.next[1] = -1;
	s.next_until = round + P.mi_next_for;
#ifdef MI_HAS_TABLE
	if (s.known >= 0)
	{
		if (const std::uint8_t* nx = mi::known_dl_next(mi::KNOWN[s.known], s.kteam, round, s.my_type, g))
		{
			s.next[0] = nx[0] == 255 ? -1 : nx[0], s.next[1] = nx[1] == 255 ? -1 : nx[1];
			return;
		}
	}
#endif
	// an unknown map: the L block's route for our slot (plan 1's first target, then the next model's best groups)
	if (s.dl && s.slot >= 0 && (s.dl[0] & 2))
	{
		const std::uint8_t* rt = s.dl + 24 + 6 * s.slot;
		for (int k = 0; k + 1 < 6; ++k)
			if (rt[k] == g)
			{
				s.next[0] = rt[k + 1] == 255 ? -1 : rt[k + 1];
				s.next[1] = k + 2 < 6 && rt[k + 2] != 255 ? rt[k + 2] : -1;
				return;
			}
	}
}

int bank_bag()
{
	const auto& s = S();
	return s.body && s.slot >= 0 && s.body[16 * s.slot + 12] != 255 ? s.body[16 * s.slot + 12] : -1;
}

int retreat_pct()
{
	const auto& s = S();
	return s.body && s.slot >= 0 && s.body[16 * s.slot + 13] != 255 ? s.body[16 * s.slot + 13] : -1;
}

int team_types(int out[6])
{
	const auto& s = S();
	int n = 0;
	for (int k = 0; k < 6; ++k)
	{
		out[k] = s.team && s.team[4 + k] != 255 ? s.team[4 + k] : -1;
		n += out[k] >= 0;
	}
	return n;
}

int rallies(int out[8])
{
	const auto& s = S();
	int n = 0;
	for (int k = 0; s.code && k < 8; ++k)
	{
		const int t = s.code[2 * k] | s.code[2 * k + 1] << 8;
		if (t == 0xFFFF)
			break;
		out[n++] = t;
	}
	return n;
}

bool have_image() { return S().team != nullptr; }
} // namespace mig
