// Test bot of the mapintel library (built fresh from the cambc 3.0.5 starter's main loop; built as the git-ignored bots/_mi_test by
// tools/mapintel/test_library.py). It spreads the work over the draft turns as a bot would, measures the fuel of the library calls on
// each turn, and prints the results on turns where printing does not hide the measurement:
//   turn 1: load_view, fingerprint(view), compute_features, Compact, base_plans (plans 2-4), row() of the first test pick's bodies
//           MI T fp <hex> ts <n> fuel_view <f> fuel_fp <f> fuel_feat <f> fuel_base <f> fuel_row <f> table <0|1> turn_fuel_left <f>
//   turn 2: row() of the second test pick (MI R2 fuel_row <f>)
//   turn 3: rows of the remaining test picks + plan 1 (measured), the draft-memory block packed and written to the engine whole, then a
//           4-byte write from offset 0 as GOD v10 makes: MI R fuel_rows <f> fuel_plan1 <f> turn_fuel_left <f> fuel_pack_write <f>
//   turn 4 (teams of 4+): the plans: MI P1 slot body (g arrive_bits end_bits)..., MI P2 banks, MI P3 band (g dU dE)..., MI P4 ... mode m
//   turns 5+: plan 1 again from the cached rows: MI L turn_fuel_left <f> plan_fuel <f> nbody <n>
//   each champion's first game turn: MI G <hex|none> prefix <byte> (the block read back; the test compares it with compact.pack) and
//           MI FX <47 doubles' bits, FEATURE_NAMES order> known <int32 hex> kteam <int32 hex> (written by turn 3 at offsets 128-511),
//           MI MW <archetype int32, 12 champion values: model_weights.h> (offsets 24-123) rank <16 groups by first_scores()> (8-23)
//           MI DL <offsets 864-999: 16 groups by dl_opening_scores(), the 16 groups nearest the nearest group ranked by dl_next_scores()
//           for the first test pick's first body at round 100, 12 dl_champion_values(), that group and body as int32> (only with dl_weights.h; turn 1
//           measures their fuel last: MI TD skip <0|1: less than 350,000 left> fuel_dl_inputs <f> fuel_dl_open <f> fuel_dl_next <f> fuel_dl_val <f> fuel_dl_nextall <f>)
// stdout costs fuel per byte in this engine, so each turn prints little and after its measurements.
//   MI E <what> on any exception. Test roster: TEST_PICKS cut to the team size.
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <optional>
#include <string>
#include <vector>
#include "mapintel/dmem.h"
#include "mapintel/features.h"
#include "mapintel/fingerprint.h"
#include "mapintel/force_roster.h"
#include "mapintel/plans.h"
#if __has_include("mapintel/known_maps.h")
#include "mapintel/known_maps.h"
#define MI_HAS_TABLE 1
#endif
#if __has_include("mapintel/model_weights.h")
#include "mapintel/model_weights.h"
#define MI_HAS_WEIGHTS 1
#endif
#ifdef MAPINTEL_FIRST_SCORES
#define MI_HAS_FIRST 1
#endif
#if __has_include("mapintel/dl_weights.h")
#include "mapintel/dl_weights.h"
#define MI_HAS_DL 1
#endif
namespace bc = cambc;

static void line(const std::string& s)
{
	const std::string t = s + "\n";
	std::fputs(t.c_str(), stdout);
	std::fflush(stdout);
}

static const char* HX = "0123456789abcdef";

static std::string hex(const std::uint8_t* p, int n)
{
	std::string s;
	s.reserve(static_cast<std::size_t>(2 * n));
	for (int k = 0; k < n; ++k)
		s += HX[p[k] >> 4], s += HX[p[k] & 15];
	return s;
}

// a double's bits as 16 hex digits (exact and cheap: no floating-point formatting)
static std::string bits(double v)
{
	std::uint64_t u;
	std::memcpy(&u, &v, 8);
	std::string s(16, '0');
	for (int k = 15; k >= 0; --k, u >>= 4)
		s[static_cast<std::size_t>(k)] = HX[u & 15];
	return s;
}

static std::string describe_bits(const mapintel::Plans& P)
{
	std::string s;
	for (int i = 0; i < P.nbody; ++i)
	{
		s += "MI P1 " + std::to_string(i) + " " + std::to_string(P.body[i]);
		for (int k = 0; k < P.ntgt[i]; ++k)
			s += " " + std::to_string(P.tgt[i][k].g) + " " + bits(P.tgt[i][k].arrive) + " " + bits(P.tgt[i][k].end);
		s += "\n";
	}
	s += "MI P2";
	for (const int b : P.bank)
		s += " " + std::to_string(b);
	s += "\nMI P3 " + std::to_string(P.band);
	for (int k = 0; k < P.ncon; ++k)
		s += " " + std::to_string(P.con[k][0]) + " " + std::to_string(P.con[k][1]) + " " + std::to_string(P.con[k][2]);
	s += "\nMI P4";
	for (const int t : P.thr)
		s += " " + std::to_string(t);
	s += " mode " + std::to_string(P.mode);
	return s;
}

struct State
{
	std::optional<mapintel::MapView> V;
	std::optional<mapintel::Features> F;
	std::optional<mapintel::Compact> C;
	mapintel::Plans P;
	std::uint64_t fp = 0;
	int ts = 0, turn = 0, npk = 0, known = -1, kteam = -1, arch = -1;
	double vals[12]{};
	unsigned long long fuel_mw = 0, fuel_fs = 0;
	std::uint8_t rank[16] = { 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255 };
	std::uint8_t dl_open[16] = { 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255 };
	std::uint8_t dl_next[16] = { 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255 };
	double dl_vals[12]{};
	std::int32_t dl_prev = -1, dl_ct = -1;
	unsigned long long fuel_dl[5]{}; // inputs, opening, next (16 candidates), values, next (all groups)
	int dl_skip = 0;
};

// the 16 best groups of a score vector (unreached groups score -1e300), ties to the lower index, as the Python references rank them
[[maybe_unused]] static void top16(const std::vector<double>& sc, std::uint8_t out[16])
{
	std::vector<int> gs;
	for (int g = 0; g < static_cast<int>(sc.size()); ++g)
		if (sc[static_cast<std::size_t>(g)] > -1e299)
			gs.push_back(g);
	std::sort(gs.begin(), gs.end(), [&](int a, int b) { return sc[static_cast<std::size_t>(a)] != sc[static_cast<std::size_t>(b)] ? sc[static_cast<std::size_t>(a)] > sc[static_cast<std::size_t>(b)] : a < b; });
	for (int k = 0; k < 16 && k < static_cast<int>(gs.size()); ++k)
		out[k] = static_cast<std::uint8_t>(gs[static_cast<std::size_t>(k)]);
}

static void turn1(State& S)
{
	const auto f0 = bc::fuel_remaining();
	S.ts = mapintel::team_size_now();
	S.npk = std::max(0, std::min(5, S.ts));
	S.V.emplace(mapintel::load_view(S.ts));
	const auto f1 = bc::fuel_remaining();
	S.fp = mapintel::fingerprint(*S.V);
	const auto f2 = bc::fuel_remaining();
	S.F.emplace(mapintel::compute_features(*S.V));
	const auto f3 = bc::fuel_remaining();
	S.C.emplace(*S.V, *S.F);
	S.P = mapintel::base_plans(*S.C, *S.V, *S.F);
	const auto f4 = bc::fuel_remaining();
	int b[2];
	const int nb = S.npk > 0 ? mapintel::pick_bodies(mapintel::TEST_PICKS[0], b) : 0;
	for (int k = 0; k < nb; ++k)
		S.C->row(b[k]);
	const auto f5 = bc::fuel_remaining();
#ifdef MI_HAS_TABLE
	S.known = mapintel::find_known(S.fp);
	if (S.known >= 0)
		S.kteam = mapintel::known_team(*S.V, mapintel::KNOWN[S.known]);
#endif
#ifdef MI_HAS_WEIGHTS
	{
		const auto m0 = bc::fuel_remaining();
		double z[mapintel::MW_NF];
		mapintel::zfeat(*S.F, z);
		S.arch = mapintel::archetype_of(z);
		mapintel::champion_values(z, S.vals);
		S.fuel_mw = m0 - bc::fuel_remaining();
	}
#ifdef MI_HAS_FIRST
	{
		const auto m0 = bc::fuel_remaining();
		top16(mapintel::first_scores(*S.C, *S.V, *S.F), S.rank);
		S.fuel_fs = m0 - bc::fuel_remaining();
	}
#endif
#endif
#ifdef MI_HAS_DL
	// dl_weights.h, measured last in the first draft turn (its 1M fuel); skipped (dl_skip 1) when less than 350,000 is left
	if (bc::fuel_remaining() < 350000)
		S.dl_skip = 1;
	else
	{
		auto a = bc::fuel_remaining();
		const auto I = mapintel::dl_inputs(*S.C, *S.V, *S.F);
		S.fuel_dl[0] = a - bc::fuel_remaining();
#ifdef MAPINTEL_DL_OPENING
		a = bc::fuel_remaining();
		top16(mapintel::dl_opening_scores(I), S.dl_open);
		S.fuel_dl[1] = a - bc::fuel_remaining();
#endif
#ifdef MAPINTEL_DL_NEXT
		for (int g = 0; g < static_cast<int>(S.C->dU.size()); ++g)
			if (S.C->dU[static_cast<std::size_t>(g)] >= 0 && (S.dl_prev < 0 || S.C->dU[static_cast<std::size_t>(g)] < S.C->dU[static_cast<std::size_t>(S.dl_prev)]))
				S.dl_prev = g;
		int b[2];
		S.dl_ct = mapintel::pick_bodies(mapintel::TEST_PICKS[0], b) > 0 ? b[0] : 0;
		// what a bot scores in a game turn: the 16 reached groups nearest the previous capture (box distance, ties to the lower index)
		std::vector<int> cand;
		for (int g = 0; g < static_cast<int>(S.C->dU.size()); ++g)
			if (S.C->dU[static_cast<std::size_t>(g)] >= 0)
				cand.push_back(g);
		const auto bd = [&](int g) { return mapintel::detail::box_dist(S.C->bx[static_cast<std::size_t>(S.dl_prev)], S.C->bx[static_cast<std::size_t>(g)]); };
		std::sort(cand.begin(), cand.end(), [&](int x, int y) { return bd(x) != bd(y) ? bd(x) < bd(y) : x < y; });
		if (cand.size() > 16)
			cand.resize(16);
		a = bc::fuel_remaining();
		top16(mapintel::dl_next_scores(*S.C, I, S.dl_prev, S.dl_ct, 100, &cand), S.dl_next);
		S.fuel_dl[2] = a - bc::fuel_remaining();
		a = bc::fuel_remaining();
		(void)mapintel::dl_next_scores(*S.C, I, S.dl_prev, S.dl_ct, 100);
		S.fuel_dl[4] = a - bc::fuel_remaining();
#endif
#ifdef MAPINTEL_DL_VALUES
		a = bc::fuel_remaining();
		mapintel::dl_champion_values(*S.F, S.dl_vals);
		S.fuel_dl[3] = a - bc::fuel_remaining();
#endif
	}
#endif
	char buf[360];
	auto u = [](auto v) { return static_cast<unsigned long long>(v); };
	std::snprintf(buf, sizeof buf, "MI T fp %016llx ts %d fuel_view %llu fuel_fp %llu fuel_feat %llu fuel_base %llu fuel_row %llu table %d fuel_mw %llu fuel_fs %llu turn_fuel_left %llu",
				  u(S.fp), S.ts, u(f0 - f1), u(f1 - f2), u(f2 - f3), u(f3 - f4), u(f4 - f5), S.known >= 0 ? 1 : 0, S.fuel_mw, S.fuel_fs, u(bc::fuel_remaining()));
	line(buf);
#ifdef MI_HAS_DL
	line("MI TD skip " + std::to_string(S.dl_skip) + " fuel_dl_inputs " + std::to_string(S.fuel_dl[0]) + " fuel_dl_open " + std::to_string(S.fuel_dl[1]) +
		 " fuel_dl_next " + std::to_string(S.fuel_dl[2]) + " fuel_dl_val " + std::to_string(S.fuel_dl[3]) + " fuel_dl_nextall " + std::to_string(S.fuel_dl[4]));
#endif
}

static void turn2(State& S)
{
	const auto g0 = bc::fuel_remaining();
	if (S.npk > 1)
	{
		int b[2];
		const int nb = mapintel::pick_bodies(mapintel::TEST_PICKS[1], b);
		for (int j = 0; j < nb; ++j)
			S.C->row(b[j]);
	}
	const auto g1 = bc::fuel_remaining();
	line("MI R2 fuel_row " + std::to_string(g0 - g1));
}

static void turn3(State& S)
{
	const auto g0 = bc::fuel_remaining();
	for (int k = 2; k < S.npk; ++k)
	{
		int b[2];
		const int nb = mapintel::pick_bodies(mapintel::TEST_PICKS[k], b);
		for (int j = 0; j < nb; ++j)
			S.C->row(b[j]);
	}
	const auto g1 = bc::fuel_remaining();
	S.C->plan1(std::span<const int>(mapintel::TEST_PICKS, static_cast<std::size_t>(S.npk)), S.P);
	const auto g2 = bc::fuel_remaining();
	const auto blk = mapintel::dmem_pack(S.P, S.fp, S.ts, S.known >= 0, 255);
	std::vector<std::uint8_t> mem(1024, 0);
	mapintel::dmem_put(mem, blk);
	bc::draft_memory = mem;
	const auto g3a = bc::fuel_remaining();
	// test only: the features (47 doubles) and the table lookup at offsets 128-511 for the champions to print (stdout costs fuel per
	// byte, a draft turn cannot afford the print); a real bot keeps its own data below offset 512
	for (int i = 0; i < mapintel::NF; ++i)
		std::memcpy(&mem[static_cast<std::size_t>(128 + 8 * i)], &S.F->v[static_cast<std::size_t>(i)], 8);
	std::memcpy(&mem[504], &S.known, 4);
	std::memcpy(&mem[508], &S.kteam, 4);
	std::memcpy(&mem[8], S.rank, 16);
	std::memcpy(&mem[24], &S.arch, 4);
	std::memcpy(&mem[28], S.vals, 96);
	std::memcpy(&mem[864], S.dl_open, 16);
	std::memcpy(&mem[880], S.dl_next, 16);
	std::memcpy(&mem[896], S.dl_vals, 96);
	std::memcpy(&mem[992], &S.dl_prev, 4);
	std::memcpy(&mem[996], &S.dl_ct, 4);
	bc::draft_memory = mem;
	const std::array<std::uint8_t, 4> v10{ 0xB7, 2, 0, 0 }; // a shorter write from offset 0, as GOD v10 makes it
	bc::draft_memory = v10;
	const auto g3 = g3a;
	line("MI R fuel_rows " + std::to_string(g0 - g1) + " fuel_plan1 " + std::to_string(g1 - g2) + " turn_fuel_left " + std::to_string(g2) +
		 " fuel_pack_write " + std::to_string(g2 - g3));
}

int main()
{
	State S;
	bool game_done = false;
	while (true)
	{
		try
		{
			if (bc::is_draft())
			{
				++S.turn;
				if (S.turn == 1)
					turn1(S);
				else if (S.turn == 2 && S.F)
					turn2(S);
				else if (S.turn == 3 && S.C)
					turn3(S);
				else if (S.turn == 4 && S.C)
					line(describe_bits(S.P)); // stdout costs fuel per byte: the plans print on a turn of their own
				else if (S.C)
				{
					const auto g0 = bc::fuel_remaining();
					mapintel::Plans P;
					S.C->plan1(std::span<const int>(mapintel::TEST_PICKS, static_cast<std::size_t>(S.npk)), P);
					const auto g1 = bc::fuel_remaining();
					line("MI L turn_fuel_left " + std::to_string(g1) + " plan_fuel " + std::to_string(g0 - g1) + " nbody " + std::to_string(P.nbody));
				}
				if (const int p = mapintel::forced_pick(); p >= 0)
					bc::draft::pick(static_cast<bc::champion_draft>(p));
				else
				{
					const auto chosen = bc::draft::current_draft(bc::team::ally);
					bc::draft::pick(static_cast<bc::champion_draft>(static_cast<int>(chosen.size())));
				}
			}
			else if (!game_done)
			{
				game_done = true;
				mapintel::Block B;
				const bool ok = mapintel::dmem_get(B);
				const int prefix = bc::draft_memory.size() > 0 ? std::to_integer<int>(bc::draft_memory[0]) : -1;
				line(std::string("MI G ") + (ok ? hex(B.b.data(), mapintel::DMEM_SIZE) : std::string("none")) + " prefix " + std::to_string(prefix));
				if (bc::draft_memory.size() >= 512)
				{
					std::uint8_t raw[384], mw[116];
					for (int k = 0; k < 384; ++k)
						raw[k] = std::to_integer<std::uint8_t>(bc::draft_memory[static_cast<std::size_t>(128 + k)]);
					for (int k = 0; k < 116; ++k)
						mw[k] = std::to_integer<std::uint8_t>(bc::draft_memory[static_cast<std::size_t>(8 + k)]);
					line("MI FX " + hex(raw, 8 * mapintel::NF) + " known " + hex(raw + 376, 4) + " kteam " + hex(raw + 380, 4));
					line("MI MW " + hex(mw + 16, 100) + " rank " + hex(mw, 16));
				}
#ifdef MI_HAS_DL
				if (bc::draft_memory.size() >= 1000)
				{
					std::uint8_t d[136];
					for (int k = 0; k < 136; ++k)
						d[k] = std::to_integer<std::uint8_t>(bc::draft_memory[static_cast<std::size_t>(864 + k)]);
					line("MI DL " + hex(d, 136));
				}
#endif
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
