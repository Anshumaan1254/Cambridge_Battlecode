// SCEN 2: altar lock. B Vendetta banks 46 gems at the centre altar (starts r52). A Tavi buys a lock, tries to place it from range 3
// (expect error) then from range 2 as soon as it sees B submitting. A Vendetta then tries to tribute on the locked altar itself.
// B Ryth (adjacent) and B Vendetta attack the lock: hits_remaining and attack availability are logged.
static void lock_log(const char* who) {
	try {
		if (!bc::vision::has_altar_lock(ALTAR)) { return; }
		auto l = bc::vision::altar_lock_at(ALTAR);
		P("%s lock hits=%u team=%s", who, l.hits_remaining(), l.is_ally() ? "ally" : "enemy");
	} catch (const std::exception& e) { P("lock_log ERR %s", e.what()); }
}
static void scenario() {
	static Carrier cv; static Farm ft; static int tavi_phase = 0, lock_round = 0, retry = 0;
	auto& me = bc::self();
	const auto t = me.champion_name();
	const auto r = bc::round_number();
	const bool A = is_team_a();
	if (!A && t == bc::champion_type::vendetta) {
				carrier(cv, { {mir(GEM1), 1}, {mir(WOLF), 1} }, mir(vec2{11, 11}), 100000);   // farm and walk to the tile, never tribute by itself
		if (cv.i < 2 || me.position() != mir(vec2{11, 11})) return;
#ifdef S2C
		// explicit lock attacks: attack, reset, attack in one turn
		if (r >= 58 && bc::vision::has_altar_lock(ALTAR)) {
			auto l = bc::vision::altar_lock_at(ALTAR);
			P("B-vend before atk can_attack=%d can_move=%d can_cast=%d hits=%u", (int)me.can_attack(), (int)me.can_move(), (int)me.can_cast(), l.hits_remaining());
			try { me.attack(l); P("atk1 ok can_attack=%d can_move=%d can_cast=%d", (int)me.can_attack(), (int)me.can_move(), (int)me.can_cast()); } catch (const std::exception& e) { P("atk1 ERR %s", e.what()); }
			lock_log("after-atk1");
			try { bool ok = me.abilities()[0].use(); P("reset ok=%d can_attack=%d", (int)ok, (int)me.can_attack()); } catch (const std::exception& e) { P("reset ERR %s", e.what()); }
			try { if (bc::vision::has_altar_lock(ALTAR)) { me.attack(bc::vision::altar_lock_at(ALTAR)); P("atk2 ok"); } else P("lock gone before atk2"); } catch (const std::exception& e) { P("atk2 ERR %s", e.what()); }
			lock_log("after-atk2");
		}
#else
		if (r >= 50 && me.gem_count() > 0) {
			if (me.is_submitting_gems()) { logst("B-vend"); return; }
			lock_log("B-vend before submit");
			try { me.submit_gems(ALTAR); P("submit_gems returned normally; sub now=%d can_attack=%d", (int)me.is_submitting_gems(), (int)me.can_attack()); } catch (const std::exception& e) { P("submit ERR %s", e.what()); }
			lock_log("B-vend after submit");
			if (me.is_submitting_gems()) P("TRIBUTE (re)START gems=%u", me.gem_count());
		} else if (r >= 50) logst("B-vend");
#endif
		return;
	}
	if (!A && t == bc::champion_type::ryth) {
		const vec2 tile{13, 12};
		if (me.position() != tile) { goto_tile(tile); return; }
		if (bc::vision::has_altar_lock(ALTAR)) {
			lock_log("Ryth sees");
			if (r == 55) {   // explicit attacks on the lock (S2C only the Ryth path matters)
				auto l = bc::vision::altar_lock_at(ALTAR);
				try { me.attack(l); P("Ryth ATTACK lock; can_attack now=%d can_move=%d", (int)me.can_attack(), (int)me.can_move()); } catch (const std::exception& e) { P("Ryth attack ERR %s", e.what()); }
				lock_log("Ryth after");
			}
		}
		return;
	}
	if (A && t == bc::champion_type::tavi) {
		if (tavi_phase == 0) { if (!farm(ft, GOLD1)) { tavi_phase = 1; P("gold=%u", me.gold_count()); } return; }
		if (tavi_phase == 1) {
			if (!bc::map::spawn_region(team::ally).is_set(me.position())) { goto_tile(vec2{3, 3}); return; }
			try { me.buy(bc::consumable_type::altar_lock); P("bought lock, gold=%u count=%u", me.gold_count(), me.consumables()[bc::consumable_type::altar_lock].count()); tavi_phase = 2; }
			catch (const std::exception& e) { P("buy ERR %s", e.what()); tavi_phase = 2; }
			return;
		}
		if (tavi_phase == 2) {   // range 3 from the altar
			const vec2 w3{9, 12};
			if (me.position() != w3) { goto_tile(w3); return; }
			try { bool ok = me.consumables()[bc::consumable_type::altar_lock].use(ALTAR); P("lock from range 3: ok=%d", (int)ok); } catch (const std::exception& e) { P("lock from range 3 ERR %s", e.what()); }
			tavi_phase = 3; return;
		}
		if (tavi_phase == 3) {   // range 2
			const vec2 w2{10, 12};
			if (me.position() != w2) { goto_tile(w2); return; }
			bool sub = false;
			for (auto& e : bc::champions(team::enemy)) if (e.is_visible() && e.is_submitting_gems()) sub = true;
			P("waiting at range 2; enemy submitting=%d", (int)sub);
#ifdef S2C
			if (true) {
#else
			if (sub) {
#endif
				try { bool ok = me.consumables()[bc::consumable_type::altar_lock].use(ALTAR); P("LOCK placed from range 2: ok=%d left=%u", (int)ok, me.consumables()[bc::consumable_type::altar_lock].count()); if (ok) { tavi_phase = 4; lock_round = r; } }
				catch (const std::exception& e) { P("lock from range 2 ERR %s", e.what()); }
			}
			return;
		}
		lock_log("Tavi");
		return;
	}
	if (A && t == bc::champion_type::vendetta) {
		const bool sb = cv.started;
		static unsigned lockseen = 0;
		if (!cv.started && cv.i >= 1 && bc::vision::has_altar_lock(ALTAR) && !lockseen) lockseen = r;
		// tribute only once the (enemy-owned or ally-owned) lock exists and 3 rounds passed
		carrier(cv, { {GEM1, 1} }, vec2{11, 11}, 50);
		if (cv.started || sb) logst("A-vend");
		if (cv.i >= 1 && me.position() == vec2{11, 11} && !cv.started && r % 5 == 0) { P("A-vend waiting; lock seen at %u, gems=%u", lockseen, me.gem_count()); }
		return;
	}
}
