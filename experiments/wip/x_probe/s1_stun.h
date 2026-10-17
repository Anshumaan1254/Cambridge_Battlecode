// SCEN 1: does a stun cancel an enemy tribute? B Vendetta banks 46 gems (gem + wolf) at the centre altar; A Tavi waits at range 4 and stuns it
// as soon as it is seen submitting (default), or with S1_ATTACK waits at range 3 and basic-attacks it every turn instead (damage control).
static void scenario() {
	static Carrier cv;
	auto& me = bc::self();
	const auto t = me.champion_name();
	if (!is_team_a() && t == bc::champion_type::vendetta) {
		const bool started_before = cv.started;
		carrier(cv, { {mir(GEM1), 1}, {mir(WOLF), 1} }, mir(vec2{11, 11}), 50);
		if (cv.started || started_before) logst("B-vend");
		return;
	}
	if (is_team_a() && t == bc::champion_type::tavi) {
		static int stunned_round = 0;
#ifdef S1_ATTACK
		const vec2 wait{10, 13}; // Chebyshev 3: basic attack range
#else
		const vec2 wait{9, 13};  // Chebyshev 4 from B's tribute tile (13,13)
#endif
		if (me.position() != wait && !stunned_round) { goto_tile(wait); return; }
		for (auto& e : bc::champions(team::enemy)) {
			if (!e.is_visible()) continue;
			if (e.champion_name() != bc::champion_type::vendetta) continue;
			int rem = -1; try { rem = e.remaining_channel_time(); } catch (...) {}
			P("see B-vend sub=%d rem=%d gems=%u stun=%d pos=%s", (int)e.is_submitting_gems(), rem, e.gem_count(), (int)e.buffs().has_stun(), bc::to_string(e.position()).c_str());
#ifdef S1_ATTACK
			if (e.is_submitting_gems() && me.can_attack()) { try { me.attack(e); P("ATTACK on tributing B-vend hp=%.0f", e.health()); } catch (const std::exception& ex) { P("attack ERR %s", ex.what()); } }
#else
			if (!stunned_round && e.is_submitting_gems() && me.abilities()[1].is_ready()) {
				try { bool ok = me.abilities()[1].use(e); P("STUN cast ok=%d", (int)ok); if (ok) stunned_round = bc::round_number(); } catch (const std::exception& ex) { P("stun ERR %s", ex.what()); }
			}
#endif
		}
		return;
	}
}
