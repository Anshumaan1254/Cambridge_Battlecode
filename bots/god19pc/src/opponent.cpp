#include "opponent.h"

#include "learn.h"
#include "om_model.h"
#include "params.h"

#include <cmath>

using CT = bc::champion_type;

OppModel& opp_model()
{
	static OppModel m;
	return m;
}

const char* arc_name(int a)
{
	static const char* const N[] = { "none", "farmer", "invader", "deathball", "objective", "altar", "ambush" };
	return a >= 0 && a < ARC_COUNT ? N[a] : "?";
}

const Preset& preset_of(int plan)
{
	// Directions (hypotheses); magnitudes are om_k_* in params.h. Plans 0-2 are the plain stances (no adjustment).
	//   INVADER: farm together on our half, fight back there, bank smaller bags with an escort.
	//   DEATHBALL: never fight their pack piecemeal: grouped, higher fight bar, smaller bags.
	//   OBJECTIVE: while their team is on the objective, take the rest of the map (their half too) and deny.
	//   ALTAR: bank small and escorted, keep a guard at our altar.
	//   AMBUSH: grouped, more careful, bush-first wards.
	static const Preset T[8] = {
		{ STANCE_SPREAD, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0 },
		{ STANCE_GROUPED, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0 },
		{ STANCE_PUSH, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1 },
		{ STANCE_GROUPED, -0.1f, 1.5f, -0.2f, 0.8f, 0.1f, 0.67f, 0.75f, 0, 0, 0 },
		{ STANCE_GROUPED, 0.3f, 1.f, 0.f, 0.8f, 0.3f, 1.f, 0.75f, 0, 0, 0 },
		{ STANCE_SPREAD, 0.f, 0.6f, 0.3f, 1.f, 0.f, 1.f, 1.f, 0, 0, 0 },
		{ STANCE_SPREAD, 0.f, 1.f, 0.f, 0.6f, 0.f, 0.67f, 1.f, 0, 1, 0 },
		{ STANCE_GROUPED, 0.15f, 1.2f, 0.f, 1.f, 0.2f, 1.f, 0.75f, 1, 0, 0 },
	};
	return T[plan >= 0 && plan < 8 ? plan : 0];
}

void OppModel::set_prior(const std::vector<bc::champion_type>& enemy)
{
	// The enemy draft as a weak prior (P.om_prior, 0 = off): divers and bruisers invade, a healer holds a pack together, the caster
	// ring takes objectives, Marcella profits from tributes. It only seeds the scores; evidence replaces it within a few windows.
	std::array<float, ARC_COUNT> n{};
	for (const auto t : enemy)
	{
		if (t == CT::varg || t == CT::vesper_vale || t == CT::vendetta || t == CT_HOR)
			n[ARC_INVADER] += 1.f;
		if (t == CT::ren)
			n[ARC_INVADER] += 0.5f;
		if (t == CT::willow)
			n[ARC_DEATHBALL] += 1.f;
		if (t == CT::prism || t == CT::tavi)
			n[ARC_OBJECTIVE] += 1.f;
		if (t == CT::marcella)
			n[ARC_ALTAR] += 1.f, n[ARC_DEATHBALL] += 0.5f;
	}
	for (int a = 0; a < ARC_COUNT; ++a)
		prior[static_cast<std::size_t>(a)] = P.om_prior * std::min(1.f, n[static_cast<std::size_t>(a)] / 3.f);
	score = prior;
}

void OppModel::features(const OmWindow& w, int bodies, float* f)
{
	const float B = static_cast<float>(std::max(1, bodies));
	const float v[17] = { static_cast<float>(w.inv) / B, static_cast<float>(w.inv_self) / 20.f, static_cast<float>(w.ally_deaths), static_cast<float>(w.enemy_deaths),
		static_cast<float>(w.multi_deaths), static_cast<float>(w.pack) / 3.f, static_cast<float>(w.vis_max) / 3.f, static_cast<float>(w.bank_events),
		static_cast<float>(w.bank_gems) / 50.f, static_cast<float>(w.bank_lump) / 100.f, static_cast<float>(w.ward_home), static_cast<float>(w.ward_altar),
		static_cast<float>(w.ward_bush), static_cast<float>(w.altar_presence) / 5.f, static_cast<float>(w.bush_hits), static_cast<float>(w.unseen_hits),
		static_cast<float>(w.heavy_lost) };
	for (int i = 0; i < 17; ++i)
		f[i] = v[i];
}

void OppModel::end_window(int bodies, int round)
{
	const OmWindow& w = cur;
	const float B = static_cast<float>(std::max(1, bodies));
	auto clamp01 = [](float v) { return std::clamp(v, 0.f, 1.f); };
	ev.fill(0.f);
	const bool calm = w.inv == 0 && w.ally_deaths == 0 && w.enemy_deaths == 0 && w.pack <= 1;
	ev[ARC_FARMER] = calm ? 1.f : (w.inv <= 1 && w.ally_deaths == 0 && w.pack <= 2 ? 0.5f : 0.f);
	ev[ARC_INVADER] = 0.7f * clamp01(static_cast<float>(w.inv) / (0.5f * B)) + 0.3f * clamp01(static_cast<float>(w.ally_deaths_home) / 2.f);
	ev[ARC_DEATHBALL] = 0.7f * clamp01(static_cast<float>(w.pack - 2) / 2.f) + 0.3f * clamp01(static_cast<float>(w.multi_deaths));
	ev[ARC_OBJECTIVE] = (w.bank_lump >= P.om_obj_lump ? clamp01(static_cast<float>(w.bank_lump) / (2.f * static_cast<float>(P.om_obj_lump))) : 0.f) +
		0.5f * clamp01(static_cast<float>(w.heavy_lost));
	ev[ARC_ALTAR] = clamp01((static_cast<float>(w.ward_altar + w.locks + w.cancels) + static_cast<float>(w.altar_presence) / 5.f) / 2.f);
	ev[ARC_AMBUSH] = clamp01((static_cast<float>(w.bush_hits) + 0.5f * static_cast<float>(w.unseen_hits) + static_cast<float>(w.ward_bush)) / 3.f);
	for (auto& v : ev)
		v = std::min(v, 1.f);
	// Contact level: how much the two teams touch per body (sightings on our half, deaths on both sides).
	contact = static_cast<float>(w.inv) / B + static_cast<float>(w.ally_deaths + w.enemy_deaths) / B;
	// Two-sided CUSUM against the slow running mean: a sustained rise or fall of contact (a strategy switch) fires within 1-2 windows,
	// single noisy windows do not (k is the per-window slack, h the alarm level).
	fired = false;
	if (windows >= P.om_cus_warm)
	{
		cus_pos = std::max(0.f, cus_pos + contact - cus_mu - P.om_cus_k);
		cus_neg = std::max(0.f, cus_neg + cus_mu - contact - P.om_cus_k);
		if (cus_pos > P.om_cus_h || cus_neg > P.om_cus_h)
		{
			fired = true;
			cus_pos = cus_neg = 0.f;
			cus_mu = contact; // the new regime is the reference from here
		}
	}
	cus_mu = windows == 0 ? contact : cus_mu + P.om_cus_alpha * (contact - cus_mu);
	if (P.om_learned)
	{
		// Fitted classifier (tools/omfit.py, om_model.h): P(raider: invader or deathball) from the smoothed signals; a hysteresis band
		// (om_p_on / om_p_off) and the minimum duration keep the plan from flickering, a fired change detector bypasses the duration.
		static_assert(OM_NF == 17 && OM_NROW == 1, "om_model.h must be the binary none / raider model");
		float f[17];
		features(w, bodies, f);
		const float lam = P.om_feat_lambda;
		for (int i = 0; i < 17; ++i)
		{
			auto& e = fema[static_cast<std::size_t>(i)];
			e = !fema_init ? f[i] : fired ? 0.5f * e + 0.5f * f[i] : lam * e + (1.f - lam) * f[i];
		}
		fema_init = true;
		float z = OM_B[0];
		for (int i = 0; i < 17; ++i)
			z += OM_W[0][i] * fema[static_cast<std::size_t>(i)];
		p_raider = 1.f / (1.f + std::exp(-z));
		ev.fill(0.f);
		ev[ARC_INVADER] = p_raider;
		score = ev;
		++windows;
		if (round < P.om_start)
			return;
		const bool held = windows - arc_since >= P.om_min_windows;
		int next = arc;
		if (arc != ARC_INVADER && p_raider >= P.om_p_on && (held || fired || arc == ARC_NONE))
			next = ARC_INVADER;
		else if (arc == ARC_INVADER && p_raider < P.om_p_off && (held || fired))
			next = ARC_NONE;
		if (next != arc)
			arc = next, arc_since = windows, ++switches;
		return;
	}
	// Exponential forgetting; a fired change detector forgets faster (half the old memory at once).
	const float lam = fired ? 0.5f * P.om_lambda : P.om_lambda;
	for (int a = 1; a < ARC_COUNT; ++a)
	{
		auto& s = score[static_cast<std::size_t>(a)];
		s = lam * s + (1.f - lam) * ev[static_cast<std::size_t>(a)];
	}
	++windows;
	if (round < P.om_start)
		return; // the opening (both teams farm their own half) says nothing about the enemy's plan
	int best = ARC_NONE;
	for (int a = 1; a < ARC_COUNT; ++a)
		if (score[static_cast<std::size_t>(a)] > (best ? score[static_cast<std::size_t>(best)] : 0.f))
			best = a;
	const float sb = best ? score[static_cast<std::size_t>(best)] : 0.f;
	const float sc = arc ? score[static_cast<std::size_t>(arc)] : 0.f;
	const bool held = windows - arc_since >= P.om_min_windows;
	int next = arc;
	if (best != arc && sb >= P.om_thresh && sb >= sc + P.om_margin && (held || fired || arc == ARC_NONE))
		next = best;
	else if (arc != ARC_NONE && sc < P.om_drop * P.om_thresh && (held || fired))
		next = ARC_NONE;
	if (next != arc)
	{
		arc = next;
		arc_since = windows;
		++switches;
	}
}

int OppModel::plan_id(int learner_stance) const
{
	switch (arc)
	{
	case ARC_FARMER: return PLAN_PUSH;
	case ARC_INVADER: return PLAN_INVADER;
	case ARC_DEATHBALL: return PLAN_DEATHBALL;
	case ARC_OBJECTIVE: return PLAN_OBJECTIVE;
	case ARC_ALTAR: return PLAN_ALTAR;
	case ARC_AMBUSH: return PLAN_AMBUSH;
	default: return std::clamp(learner_stance, 0, 2);
	}
}
