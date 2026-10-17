// SCEN 5: Home emblem recall time. A Vendetta farms 160 gold (wolf + 2 gold clusters), buys 5 home shards (-> emblem) at spawn, walks out; A Ryth waits out.
// Both start a recall in round REC from tiles at the same distance from the spawn; arrival round = first turn on the spawn.
#ifndef REC
#define REC 125
#endif
static void scenario() {
	if (!is_team_a()) return;
	static Farm f1, f2, f3; static int ph = 0; static bool recalled = false; static unsigned rec_round = 0, arrived = 0;
	auto& me = bc::self();
	const auto t = me.champion_name();
	const auto r = bc::round_number();
	vec2 tile;
	if (t == bc::champion_type::vendetta) {
		tile = {8, 5};
		if (ph == 0) { if (!farm(f1, WOLF)) { ph = 1; } return; }
		if (ph == 1) { if (!farm(f2, GOLD1)) { ph = 2; } return; }
		if (ph == 2) { if (!farm(f3, GOLD2)) { ph = 3; P("gold=%u at round %u", me.gold_count(), r); } return; }
		if (ph == 3) {
			if (!bc::map::spawn_region(team::ally).is_set(me.position())) { goto_tile(vec2{3, 3}); return; }
			try { me.buy(bc::item_type::home_shard_of_health, 5); P("bought 5 home shards, gold left=%u", me.gold_count()); } catch (const std::exception& e) { P("buy ERR %s", e.what()); }
			ph = 4; return;
		}
	} else if (t == bc::champion_type::ryth) {
		tile = {8, 6};
	} else return;
	if (!recalled && me.position() != tile) { goto_tile(tile); return; }
	if (!recalled) {
		if (r >= REC && me.position() == tile) { try { me.recall(); recalled = true; rec_round = r; P("RECALL start at %s", bc::to_string(me.position()).c_str()); logst("recall"); } catch (const std::exception& e) { P("recall ERR %s", e.what()); } }
		return;
	}
	logst("recall");
	if (!arrived && bc::map::spawn_region(team::ally).is_set(me.position())) { arrived = r; P("ARRIVED on spawn at round %u (recall started %u, delta %u)", r, rec_round, r - rec_round); }
}
