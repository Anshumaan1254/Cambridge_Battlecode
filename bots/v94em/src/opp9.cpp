#include "opp9.h"

#include "comms.h"
#include "learn.h"
#include "params.h"
#include "world.h"

#include <algorithm>
#include <cmath>
#include <cstdio>

Opp9& opp9()
{
	static Opp9 m;
	return m;
}

namespace
{
// Directions are the guide's counter-playbook (chapter 17); magnitudes are starting points for the ES / A-B tuning.
//                                  fight  fback   half  deny   iso  bank  gold  stance                 rally opp locks
constexpr std::array<Preset9, PL_COUNT> PRESETS9{ {
	/* FARM   */ { 0.00f, 0.00f, 1.0f, 0.00f, 0.0f, 1.0f, 1.0f, -1, 0, 0, 0 },
	/* DEFEND */ { 0.10f, 0.00f, 2.5f, -0.05f, 0.2f, 0.7f, 1.0f, 1 /* GROUPED */, 3, 0, 0 },
	/* PUNISH */ { -0.15f, -0.10f, 0.6f, 0.30f, 0.0f, 1.0f, 1.0f, 2 /* PUSH */, 2, 2, 0 },
	/* HUNT   */ { -0.10f, -0.05f, 0.4f, 0.50f, 0.0f, 1.0f, 0.8f, 2 /* PUSH */, 0, 4, 1 },
	/* RACE   */ { 0.30f, 0.00f, 1.5f, -0.05f, 0.3f, 1.0f, 0.3f, 0 /* SPREAD */, 0, 0, 0 },
	/* EVADE  */ { 0.40f, 0.00f, 1.5f, 0.00f, 0.4f, 0.7f, 1.0f, 1 /* GROUPED */, 2, 0, 0 },
	/* DENY   */ { -0.20f, -0.15f, 0.4f, 0.60f, -0.1f, 0.6f, 0.5f, 2 /* PUSH */, 2, 6, 1 },
} };
constexpr const char* NAMES9[PL_COUNT] = { "FARM", "DEFEND", "PUNISH", "HUNT", "RACE", "EVADE", "DENY" };
} // namespace

const Preset9& preset9_of(int plan) { return PRESETS9[static_cast<std::size_t>(std::clamp(plan, 0, PL_COUNT - 1))]; }
const char* plan9_name(int plan) { return NAMES9[static_cast<std::size_t>(std::clamp(plan, 0, PL_COUNT - 1))]; }

void Opp9::init()
{
	inited = true;
	auto& W = world();
	divers = casters = 0;
	if (P.enemy_comp_init)
		for (const auto& e : W.enemies)
		{
			const bool diver = !e.kit.ranged || e.kit.dash >= 0;
			divers += diver;
			casters += !diver;
		}
	// A diving composition (4 melee / dash champions, Vendetta, Heart of Ruin...) starts closer to the invasion line, so the first
	// windows of contact switch the plan sooner. It never sets a plan by itself.
	contact = P.opp_dive_prior * static_cast<float>(std::max(0, divers - 2));
	last_ally_deaths = W.ally_deaths;
}

void Opp9::switch_to(int want, bool urgent)
{
	if (want < 0 || want >= PL_COUNT || !((P.opp_mask >> want) & 1))
		want = PL_FARM; // P.opp_mask: plans switched off for an ablation
	if (want == plan)
		return;
	plan = want;
	plan_since = windows;
	if (urgent)
		cusum = 0.f;
}

void Opp9::tick(int round, bool contact_now, int carried_gems)
{
	if (!inited)
		init();
	if (P.opp_force >= 0)
	{
		plan = std::clamp(P.opp_force, 0, PL_COUNT - 1); // ADP-2 test: one plan for the whole game (the preset's value with a perfect detector)
		return;
	}
	if (round == last_round)
		return;
	last_round = round;
	auto& W = world();
	const auto& C = comms();
	const int ours = static_cast<int>(bc::global_submitted_gems(team::ally));
	const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
	if (win_start < 0)
	{
		win_start = round;
		last_ours = ours, last_theirs = theirs;
		w_ally_d0 = W.ally_deaths, w_enemy_d0 = W.enemy_deaths, w_home_d0 = learner().ally_deaths_our_half;
	}
	carried = carried_gems;
	// Their bank events: exact size and timing for every body (global score); no vision needed.
	if (theirs > last_theirs)
		++w_bank_n, w_bank_gems += theirs - last_theirs;
	w_our_gems += std::max(0, ours - last_ours);
	last_theirs = theirs, last_ours = ours;
	// Lost team fights: a second death of ours within 4 rounds of another.
	while (last_ally_deaths < W.ally_deaths)
	{
		++last_ally_deaths;
		bool recent = false;
		for (const int r : death_r)
			recent |= round - r <= 4;
		if (recent)
			loss_r[loss_i++ % loss_r.size()] = round;
		death_r[death_i++ % death_r.size()] = round;
	}
	// Deaths on our half without vision: an ally that dies within 8 rounds of claiming a group on our half died there
	// (a body clears its claim while it fights, so the last claim it held is the best guess of where it was).
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
	{
		const auto k = static_cast<std::size_t>(i);
		const auto& a = W.allies[k];
		if (a.alive && C.claim[k] >= 0)
			last_claim[k] = C.claim[k], last_claim_r[k] = round;
		if (!a.alive && a.died_round > seen_died[k])
		{
			seen_died[k] = a.died_round;
			const int g = last_claim[k];
			if (g >= 0 && g < static_cast<int>(W.groups.size()) && a.died_round - last_claim_r[k] <= 8 && W.groups[static_cast<std::size_t>(g)].ours)
				++w_home_hard;
		}
	}
	w_contact += contact_now;
	++w_rounds;
	if (P.opp_loss_n > 0 && plan == PL_FARM && losses_within(round, P.opp_loss_h) >= P.opp_loss_n)
		switch_to(PL_EVADE, true);
	// Hard evidence: they are killing us on our own half. Switch now (DEFEND, or PUNISH when we win the trades anyway).
	if (P.opp_home_deaths > 0 && w_home_hard >= P.opp_home_deaths && plan != PL_DEFEND && plan != PL_PUNISH && plan != PL_DENY)
		switch_to(balance >= P.opp_punish_bal ? PL_PUNISH : PL_DEFEND, true);
	// Endgame: no waiting for the window when they are about to win.
	if (theirs >= P.opp_deny_at && plan != PL_DENY && decide(round) == PL_DENY)
		switch_to(PL_DENY, true);
	if (round - win_start >= P.opp_window)
		close_window(round);
}

void Opp9::close_window(int round)
{
	auto& W = world();
	const float n = static_cast<float>(std::max(1, w_rounds));
	const float a = std::clamp(P.opp_ema, 0.05f, 1.f);
	const float c = static_cast<float>(w_contact) / n;
	contact = (1.f - a) * contact + a * c;
	hi_run = contact >= P.opp_contact_hi ? hi_run + 1 : 0;
	// CUSUM (Page's test) on the contact share: accumulates only rises beyond the slow mean plus a drift allowance.
	cusum = std::max(0.f, cusum + (c - contact_mean) - P.opp_cusum_k);
	contact_mean = 0.85f * contact_mean + 0.15f * c;
	const int d_ally = W.ally_deaths - w_ally_d0, d_enemy = W.enemy_deaths - w_enemy_d0;
	const int d_home = std::max(learner().ally_deaths_our_half - w_home_d0, w_home_hard);
	balance = (1.f - a) * balance + a * static_cast<float>(d_enemy - d_ally);
	home_deaths = (1.f - a) * home_deaths + a * static_cast<float>(d_home);
	const float ar = std::clamp(P.opp_rate_ema, 0.05f, 1.f);
	their_rate = windows == 0 ? static_cast<float>(w_bank_gems) / n : (1.f - ar) * their_rate + ar * static_cast<float>(w_bank_gems) / n;
	our_rate = windows == 0 ? static_cast<float>(w_our_gems) / n : (1.f - ar) * our_rate + ar * static_cast<float>(w_our_gems) / n;
	if (w_bank_n > 0)
		their_bag = (1.f - a) * their_bag + a * static_cast<float>(w_bank_gems) / static_cast<float>(w_bank_n);

	const int want = decide(round);
	const bool urgent = cusum >= P.opp_cusum_h && (want == PL_DEFEND || want == PL_PUNISH || want == PL_EVADE);
	// Leaving FARM needs no dwell (the evidence rules already demand persistence); leaving a counter-plan does.
	if (want != plan && (urgent || plan == PL_FARM || windows - plan_since >= P.opp_dwell))
		switch_to(want, urgent);
	++windows;
#ifdef OPP_TRACE
	debug_block({
		std::printf("OPP r=%d plan=%s contact=%.2f run=%d cusum=%.2f bal=%.2f home=%.2f losses=%d their=%.2f/r ours=%.2f/r bag=%.0f divers=%d\n",
			round, plan9_name(plan), contact, hi_run, cusum, balance, home_deaths, losses_within(round, P.opp_loss_h), their_rate, our_rate, their_bag, divers);
	});
#endif
	win_start = round;
	w_rounds = w_contact = w_bank_n = w_bank_gems = w_our_gems = w_home_hard = 0;
	w_ally_d0 = W.ally_deaths, w_enemy_d0 = W.enemy_deaths, w_home_d0 = learner().ally_deaths_our_half;
}

int Opp9::decide(int round) const
{
	const int ours = static_cast<int>(bc::global_submitted_gems(team::ally));
	const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
	const int goal = static_cast<int>(bc::constants::winning_gems);
	// Paces: the recent windows blended with the whole game so far (bank events are lumpy).
	const float avg_us = static_cast<float>(ours) / static_cast<float>(std::max(1, round));
	const float avg_them = static_cast<float>(theirs) / static_cast<float>(std::max(1, round));
	const float rate_us = std::max(0.05f, 0.5f * our_rate + 0.5f * avg_us);
	const float rate_them = std::max(0.05f, 0.5f * their_rate + 0.5f * avg_them);
	const float t_us = static_cast<float>(std::max(0, goal - ours - carried)) / rate_us;
	const float t_them = static_cast<float>(std::max(0, goal - theirs)) / rate_them;
	const bool they_finish = static_cast<float>(round) + t_them < static_cast<float>(bc::constants::max_rounds);
	// Hysteresis: entering the race plans needs a clear deficit, staying in them only that they still finish first.
	const bool racing = plan == PL_HUNT || plan == PL_RACE || plan == PL_DENY;
	// Not before opp_race_from (like v8's race_from): one or two early bank events make the projection meaningless.
	const bool behind = round >= P.opp_race_from && they_finish && t_them + (racing ? 0.f : static_cast<float>(P.opp_race_margin)) < t_us;
	if (theirs >= P.opp_deny_at && behind)
		return PL_DENY;
	if (windows < 1)
		return PL_FARM; // no closed window yet
	const bool holding = (plan == PL_DEFEND || plan == PL_PUNISH) && contact >= P.opp_contact_stay;
	if (hi_run >= P.opp_consec || holding || home_deaths >= 1.f)
		return balance >= P.opp_punish_bal && home_deaths < 0.5f ? PL_PUNISH : PL_DEFEND;
	if (P.opp_loss_n > 0 && losses_within(round, P.opp_loss_h) >= P.opp_loss_n)
		return PL_EVADE;
	// Hysteresis again: a quiet opponent is one below opp_contact_lo to enter the race plans, below opp_contact_hi to stay in them.
	const bool quiet = contact <= (racing ? P.opp_contact_hi : P.opp_contact_lo);
	if (quiet && behind)
		return balance >= P.opp_even_bal ? PL_HUNT : PL_RACE; // an EMA never returns exactly to 0 after a lost fight
	return PL_FARM;
}

int Opp9::losses_within(int round, int horizon) const
{
	int n = 0;
	for (const int r : loss_r)
		n += round - r <= horizon;
	return n;
}
