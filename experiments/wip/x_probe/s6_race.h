// SCEN 6: win race on maps/probe5/p6.map26a (31x31, 4 bodies per team, 16 gem clusters per half, altar (15,15)).
// Phase 1: every body cycles its 4 clusters until round F1, then banks its whole bag at its altar tile.
// Final: Tavi keeps farming KF more clusters after banking and starts one last tribute at round FIN_A (team A) / FIN_B (team B).
#ifndef F1
#define F1 200
#endif
#ifndef BD
#define BD 0
#endif
#ifndef KF
#define KF 1
#endif
#ifndef FIN_A
#define FIN_A 250
#endif
#ifndef FIN_B
#define FIN_B 250
#endif
static void scenario() {
	auto& me = bc::self();
	const auto t = me.champion_name();
	const bool A = is_team_a();
	const unsigned r = bc::round_number();
	static vec2 cl[4]; static vec2 tile; static bool init = false;
	if (!init) {
		init = true;
		switch (t) {
			case bc::champion_type::vendetta: cl[0]={6,2}; cl[1]={9,2}; cl[2]={12,2}; cl[3]={12,5}; tile={14,14}; break;
			case bc::champion_type::ryth: cl[0]={2,6}; cl[1]={2,9}; cl[2]={2,12}; cl[3]={5,12}; tile={14,15}; break;
			case bc::champion_type::vesper_vale: cl[0]={6,6}; cl[1]={9,6}; cl[2]={6,9}; cl[3]={9,9}; tile={15,14}; break;
			default: cl[0]={12,8}; cl[1]={12,11}; cl[2]={8,12}; cl[3]={15,6}; tile={14,16}; break;
		}
		for (auto& c : cl) c = mir(c);
		tile = mir(tile);
	}
	static Farm f; static int idx = 0; static int phase = 0; static int extra = 0; static bool trib = false; static unsigned trib_round = 0;
	const bool final_body = (t == bc::champion_type::tavi);
	if (me.is_submitting_gems()) { if (r % 10 == 0) logst("bank"); return; }
	if (phase == 0) {                    // farming
		if (r >= F1 && f.phase == 0 && !f.seen) { phase = 1; return; }
		if (r >= F1 && f.phase == 2) { phase = 1; return; }
		if (!farm(f, cl[idx % 4], 1)) { idx++; f = Farm{}; }
		return;
	}
	if (phase == 1) {                    // bank everything
		if (me.position() != tile) { goto_tile(tile); return; }
		if (me.gem_count() == 0) { phase = final_body ? 2 : 3; P("banked; bag empty at round %u", r); return; }
		static unsigned at_tile = 0; if (!at_tile) at_tile = r;
		if (r < at_tile + BD) return;
		if (!trib) { try { me.submit_gems(ALTAR15); trib = true; trib_round = r; P("BANK START gems=%u", me.gem_count()); } catch (const std::exception& e) { P("submit ERR %s", e.what()); } }
		else trib = false;
		return;
	}
	if (phase == 2) {                    // final body: extra clusters, then the last tribute at FIN
		if (extra < KF) { if (!farm(f, cl[(idx + extra) % 4], 1)) { extra++; f = Farm{}; } return; }
		if (me.position() != tile) { goto_tile(tile); return; }
		if (r >= (A ? FIN_A : FIN_B) && me.gem_count() > 0) {
			try { me.submit_gems(ALTAR15); P("FINAL START gems=%u (completes round %u)", me.gem_count(), r + (me.gem_count() + 9) / 10); phase = 4; } catch (const std::exception& e) { P("submit ERR %s", e.what()); }
		}
		return;
	}
}
