// Session 5 engine-rule probe (cambc 2.2.5). Scenario chosen by scen.h (SCEN). Map: maps/probe5/p5.map26a (25x25 rot180).
// Both teams run this same code; scripts depend on (team, champion). Output goes to stdout (replay logs).
#include <cambc.h>
#include <cstdio>
#include <string>
#include <variant>
#include "scen.h"

namespace bc = cambc;
using bc::vec2;
using bc::team;

static const char* cname(bc::champion_type t) {
	static const char* n[] = {"ryth","vesper","vendetta","cassi","issac","stellar","prism","marcella","willow","ren","varg","tavi"};
	return n[static_cast<int>(t)];
}
static int cheb(vec2 a, vec2 b) { return (int)a.chebyshev_distance(b); }
static bool is_team_a() { return bc::map::spawn_region(team::ally).is_set({2, 2}); }
static const char* TN() { return is_team_a() ? "A" : "B"; }

static void P(const char* fmt, auto... args) {
	std::printf("[r%u %s %s] ", bc::round_number(), TN(), cname(bc::self().champion_name()));
	std::printf(fmt, args...);
	std::printf("\n");
}

// Team A coordinates; team B uses the 180 degree mirror. Map is 25x25.
#ifndef MAPW
#define MAPW 25
#endif
static vec2 mir(vec2 p) { return is_team_a() ? p : vec2{MAPW - 1 - p.x, MAPW - 1 - p.y}; }
static const vec2 GEM1{7, 2}, GEM2{2, 7}, GEM3{7, 7}, GOLD1{10, 3}, GOLD2{3, 10}, WOLF{9, 9}, ALTAR{12, 12};
static const vec2 ALTAR15{15, 15};

static bool approach(vec2 target, int range) {
	auto& me = bc::self();
	if (!me.can_move() || cheb(me.position(), target) <= range) return false;
	auto blocked = bc::map::walls() | bc::map::holes() | bc::map::altars() | bc::map::spawn_region(team::enemy)
		| bc::vision::champion_tiles() | bc::vision::camp_tiles();
	blocked.set(me.position(), false);
	bc::bitboard goals; goals.draw_chebyshev(target, (float)range);
	goals &= ~blocked;
	if (goals.is_empty()) return false;
	bc::distance_field f; bc::bitboard visited, dest; dest.set(me.position());
	f.compute_to(blocked, goals, dest, visited);
	auto step = f.next_move_from(me.position());
	if (!step) return false;
	return me.move(*step);
}
// Move to an exact tile (path blocked by other champions and camps).
static bool goto_tile(vec2 t) { return approach(t, 0); }

static void draft() {
	static const bc::champion_draft order[] = { SCEN_DRAFT };
	const auto mine = bc::draft::current_draft(team::ally);
	bc::draft::pick(order[mine.size() % 5]);
}

// ---- farming helper: kill the camp at c (melee: from adjacent), step on its tile, wait for the reward.
struct Farm { int phase = 0; unsigned base = 0; unsigned step_round = 0; bool seen = false; };
static int reset_slot() {
	switch (bc::self().champion_name()) {
		case bc::champion_type::ryth: return 1;
		case bc::champion_type::vendetta: case bc::champion_type::vesper_vale: case bc::champion_type::tavi: case bc::champion_type::varg: return 0;
		default: return -1;
	}
}
static unsigned wealth() { return bc::self().gem_count() + bc::self().gold_count(); }
// true while busy, false once the reward has arrived
static bool farm(Farm& f, vec2 c, int range = 1) {
	auto& me = bc::self();
	if (f.phase == 0) {
		if (cheb(me.position(), c) > range) { approach(c, range); return true; }
		if (bc::vision::has_camp(c)) f.seen = true;
		if (!bc::vision::has_camp(c) && !f.seen) { return true; }   // not (yet) respawned: wait next to it
		if (!bc::vision::has_camp(c)) { f.phase = 1; }
		else {
			auto cp = bc::vision::camp_at(c);
			if (me.can_attack()) me.attack(cp);
			int rs = reset_slot();
			if (bc::vision::has_camp(c) && rs >= 0 && me.abilities()[rs].is_ready()) { try { me.abilities()[rs].use(); if (me.can_attack()) me.attack(cp); } catch (...) {} }
			if (!bc::vision::has_camp(c)) { P("camp %d,%d died", c.x, c.y); f.phase = 1; }
			return true;
		}
	}
	if (f.phase == 1) {
		if (me.position() != c) {
			if (!goto_tile(c)) { try { me.move_absolute(c); } catch (...) {} }
			if (me.position() == c) { f.base = wealth(); f.step_round = bc::round_number(); P("stepped on %d,%d", c.x, c.y); }
			return true;
		}
		if (f.base == 0 && f.step_round == 0) { f.base = wealth(); f.step_round = bc::round_number(); }
		if (wealth() > f.base) { f.phase = 2; return false; }
		return true;
	}
	return false;
}

struct Tgt { vec2 p; int range; };
struct Carrier { int i = 0; Farm f; unsigned trib_start = 0; int trib_gems = 0; bool started = false; };
static void logst(const char* tag) {
	auto& me = bc::self();
	int rem = -1; try { rem = me.remaining_channel_time(); } catch (...) {}
	P("%s sub=%d rec=%d rem=%d gems=%u stun=%d pos=%s | submitted A=%u B=%u", tag, (int)me.is_submitting_gems(), (int)me.is_recalling(), rem, me.gem_count(), (int)me.buffs().has_stun(),
		bc::to_string(me.position()).c_str(), bc::global_submitted_gems(is_team_a() ? team::ally : team::enemy), bc::global_submitted_gems(is_team_a() ? team::enemy : team::ally));
}
// Farm the targets in order, walk to `tile` next to the altar and start a tribute in round >= tr_round. Returns true once started.
static bool carrier(Carrier& c, std::initializer_list<Tgt> ts, vec2 tile, unsigned tr_round) {
	auto& me = bc::self();
	const Tgt* t = ts.begin();
	if (c.i < (int)ts.size()) { if (!farm(c.f, t[c.i].p, t[c.i].range)) { c.i++; c.f = Farm{}; } return false; }
	if (c.started) return true;
	if (me.position() != tile) { goto_tile(tile); return false; }
	if (bc::round_number() < tr_round) return false;
	if (me.gem_count() == 0) return false;
	c.trib_gems = (int)me.gem_count();
	try { me.submit_gems(ALTAR); c.started = true; c.trib_start = bc::round_number(); P("TRIBUTE START gems=%d", c.trib_gems); logst("after-start"); }
	catch (const std::exception& e) { P("submit_gems ERR %s", e.what()); }
	return c.started;
}

static unsigned last_gems = 0, last_gold = 0;
static void trace_bag() {
	auto& me = bc::self();
	if (me.gem_count() != last_gems || me.gold_count() != last_gold) {
		P("bag gems %u->%u gold %u->%u pos=%s", last_gems, me.gem_count(), last_gold, me.gold_count(), bc::to_string(me.position()).c_str());
		last_gems = me.gem_count(); last_gold = me.gold_count();
	}
}

#include "scen_body.h"

int main() {
	while (true) {
		try {
			if (bc::is_draft()) draft();
			else if (bc::self().is_alive()) {
				if (bc::round_number() == 1 && bc::self().champion_name() == bc::champion_type::vendetta) {
					P("CONST submit_mult=%.3f base=%d min=%d range=%d recall=%d lock_hits=%u max_rounds=%u win=%u capture=%d", bc::constants::submit_gem_duration_multiplier, (int)bc::constants::submit_gem_base_duration, (int)bc::constants::submit_gem_minimum_duration, (int)bc::constants::submit_gems_range, (int)bc::constants::recall_time, (unsigned)bc::constants::altar_lock_hits, (unsigned)bc::constants::max_rounds, (unsigned)bc::constants::winning_gems, (int)bc::constants::capture_time);
					try { auto i = bc::consumable_type::altar_lock.info(); P("altar_lock cost=%u carry=%u", i.cost, i.carry_limit); auto j = bc::consumable_type::tp_crystal.info(); P("tp cost=%u carry=%u", j.cost, j.carry_limit); } catch (...) {}
				}
				trace_bag();
				scenario();
			}
		} catch (const std::exception& e) {
			std::printf("ERR r%u %s\n", bc::round_number(), e.what());
		}
		bc::end_turn();
	}
}
