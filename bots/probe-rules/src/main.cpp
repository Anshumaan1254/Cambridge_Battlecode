// Scripted rule probe on maps/zz_test (30x30, rot180). Team A runs the scripts; team B idles.
#include <cambc.h>
#include <cstdio>
#include <string>
#include <variant>

namespace bc = cambc;
using bc::vec2;
using bc::team;

static const char* cname(bc::champion_type t) {
    static const char* n[] = {"ryth","vesper","vendetta","cassi","issac","stellar","prism","marcella","willow","ren","varg","tavi"};
    return n[static_cast<int>(t)];
}
static int cheb(vec2 a, vec2 b) { return (int)a.chebyshev_distance(b); }
static bool is_team_a() { return bc::map::spawn_region(team::ally).is_set({2, 2}); }

static void P(const char* fmt, auto... args) {
    std::printf("[r%u %s] ", bc::round_number(), cname(bc::self().champion_name()));
    std::printf(fmt, args...);
    std::printf("\n");
}

static void log_camp(vec2 spawn, const char* tag) {
    try {
        auto c = bc::map::camp(spawn);
        if (!c.is_visible()) { P("%s camp not visible", tag); return; }
        auto st = c.state();
        P("%s camp hp=%.0f/%.0f str=%.0f state=%u pos=%s stun=%d", tag, c.health(), c.max_health(), c.strength(), (unsigned)st, bc::to_string(c.position()).c_str(), (int)c.buffs().has_stun());
    } catch (const std::exception& e) { P("%s camp err %s", tag, e.what()); }
}

static void draft() {
    const bc::champion_draft order[] = { bc::champion_draft::stellar, bc::champion_draft::tavi, bc::champion_draft::vendetta, bc::champion_draft::ryth, bc::champion_draft::vesper_vale };
    const auto mine = bc::draft::current_draft(team::ally);
    bc::draft::pick(order[mine.size() % 5]);
}


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

const vec2 GEM{9, 2}, WOLF{12, 9}, ELK{3, 12}, GOLD{8, 8}, ALTAR{6, 2}, MONO{14, 13};

static void vendetta() {
    auto& me = bc::self();
    static int phase = 0; static unsigned last_gems = 0, last_sub = 0;
    const auto r = bc::round_number();
    const auto gems = me.gem_count();
    const auto sub = bc::global_submitted_gems(team::ally);
    if (gems != last_gems || sub != last_sub) { P("gems %u->%u submitted %u->%u state=%u", last_gems, gems, last_sub, sub, me.state().bits()); last_gems = gems; last_sub = sub; }
    if (me.is_submitting_gems()) { P("submitting... remaining=%d", me.remaining_channel_time()); return; }
    if (phase == 0) {
        // kill gem cluster; detect death through vision occupancy
        if (cheb(me.position(), GEM) > 1) { approach(GEM,1); return; }
        if (!bc::vision::has_camp(GEM)) { phase = 1; P("gem dead (no camp on tile)"); }
        else {
            auto c = bc::vision::camp_at(GEM);
            if (me.can_attack()) { me.attack(c); P("hit gem hp=%.0f", c.health()); }
            if (bc::vision::has_camp(GEM)) { try { bool ok = me.abilities()[0].use(); P("vend reset ok=%d", (int)ok); if (me.can_attack()) { me.attack(c); P("hit2 gem"); } } catch (const std::exception& e) {} }
            if (!bc::vision::has_camp(GEM)) { P("gem died this turn; cd0=%d", me.abilities()[0].cooldown()); }
            return;
        }
    }
    if (phase == 1) {
        if (me.position() != GEM) { bool ok = me.move_absolute(GEM); P("step onto gem tile ok=%d", (int)ok); return; }
        for (auto& g : bc::vision::camp_groups()) {
            auto s = g.state();
            if (std::holds_alternative<bc::map::camp_group_reward_available>(s)) P("group reward available");
            else if (auto* rr = std::get_if<bc::map::camp_group_respawning>(&s)) P("group respawning timer=%d", rr->timer);
        }
        if (gems > 0) { phase = 2; P("got gems at round"); }
        return;
    }
    if (phase == 2) {
        // walk to altar and try submit in the same turn as moving
        if (cheb(me.position(), ALTAR) > 1) {
            bool moved = approach(ALTAR,1);
            if (cheb(me.position(), ALTAR) <= 1) {
                try { me.submit_gems(ALTAR); P("move+submit same turn OK (moved=%d)", (int)moved); }
                catch (const std::exception& e) { P("move+submit same turn ERR %s", e.what()); }
            }
            return;
        }
        try { me.submit_gems(ALTAR); P("submit started"); } catch (const std::exception& e) { P("submit ERR %s", e.what()); }
        phase = 3;
        return;
    }
    if (phase == 3 && gems == 0 && r > 5) {
        // test recall timing from here
        try { me.recall(); P("recall started"); phase = 4; } catch (const std::exception& e) { P("recall err %s", e.what()); }
        return;
    }
    if (phase == 4) {
        if (me.is_recalling()) P("recalling remaining=%d", me.remaining_channel_time());
        else { P("recall done pos=%s hp=%.0f", bc::to_string(me.position()).c_str(), me.health()); phase = 5; }
    }
}

static void stellar() {
    // Hit wolf once from range 4, then hold position; observe HP/sleep.
    auto& me = bc::self();
    static int phase = 0; static unsigned hit_round = 0;
    const auto r = bc::round_number();
    if (phase == 0) {
        if (cheb(me.position(), WOLF) > 4) { approach(WOLF,4); return; }
        phase = 1; return;
    }
    if (phase == 1) {
        auto c = bc::map::camp(WOLF);
        try { bool ok = me.abilities()[0].use(c); P("cast dmg on wolf ok=%d", (int)ok); hit_round = r; } catch (const std::exception& e) { P("cast err %s", e.what()); }
        phase = 2; return;
    }
    if (phase == 2) {
        log_camp(WOLF, "wolf");
        P("my hp=%.0f", me.health());
        if (r > hit_round + 8) phase = 3;
        return;
    }
    if (phase == 3) {
        // basic attack from range 3: does the wolf retaliate? stays in range now
        if (cheb(me.position(), WOLF) > 3) { approach(WOLF,4); return; }
        auto c = bc::map::camp(WOLF);
        if (c.is_alive() && me.can_attack()) { me.attack(c); }
        log_camp(WOLF, "wolf-melee");
        P("my hp=%.0f", me.health());
        if (!c.is_alive()) phase = 4;
    }
}

static void ryth() {
    // Tank the elk; log damage taken per round.
    auto& me = bc::self();
    static float last_hp = -1;
    if (cheb(me.position(), ELK) > 1) { approach(ELK,1); last_hp = me.health(); return; }
    auto c = bc::map::camp(ELK);
    if (c.is_visible() && c.is_alive() && me.can_attack()) me.attack(c);
    P("ryth hp=%.0f (delta %.0f) elk_hp=%.0f elk_stun=%d", me.health(), me.health() - last_hp, c.is_alive() ? c.health() : 0.f, c.is_alive() ? (int)c.buffs().has_stun() : -1);
    last_hp = me.health();
    if (me.health() < 300 && !me.is_recalling()) { try { me.recall(); P("ryth recall"); } catch (...) {} }
}

static void tavi() {
    // Stun the elk every time the stun is up, from range 4.
    auto& me = bc::self();
    if (cheb(me.position(), ELK) > 4) { approach(ELK,4); return; }
    auto c = bc::map::camp(ELK);
    if (!c.is_visible() || !c.is_alive()) return;
    if (c.is_awake() && me.abilities()[1].is_ready()) {
        try { bool ok = me.abilities()[1].use(c); P("stun elk ok=%d", (int)ok); } catch (const std::exception& e) { P("stun err %s", e.what()); }
    }
}

static void vesper() {
    // Dash then basic attack on the gold cluster; ward cooldown log.
    auto& me = bc::self();
    static int phase = 0;
    if (phase == 0) {
        if (cheb(me.position(), GOLD) > 5) { approach(GOLD,5); return; }
        phase = 1; return;
    }
    if (phase == 1) {
        // dash 2 tiles toward the gold
        vec2 d{ (GOLD.x > me.position().x) - (GOLD.x < me.position().x), (GOLD.y > me.position().y) - (GOLD.y < me.position().y) };
        vec2 dst = me.position() + d * 2;
        try { bool ok = me.abilities()[1].use(dst); P("dash ok=%d now=%s dist=%d can_attack=%d can_move=%d", (int)ok, bc::to_string(me.position()).c_str(), cheb(me.position(), GOLD), (int)me.can_attack(), (int)me.can_move()); }
        catch (const std::exception& e) { P("dash err %s", e.what()); }
        auto c = bc::map::camp(GOLD);
        if (cheb(me.position(), GOLD) <= 3) {
            try { me.attack(c); P("attack after dash OK"); } catch (const std::exception& e) { P("attack after dash ERR %s", e.what()); }
        }
        // move after attack?
        try { bool ok = me.move(vec2{0, 1}); P("move after attack ok=%d", (int)ok); } catch (const std::exception& e) { P("move after attack ERR %s", e.what()); }
        phase = 2; return;
    }
    if (phase >= 2 && phase < 8) {
        try { bool ok = me.place_ward(me.position()); P("ward ok=%d cd=%d", (int)ok, me.ward_cooldown()); } catch (const std::exception& e) { P("ward err %s cd=%d", e.what(), me.ward_cooldown()); }
        // attack reset test: attack, reset, attack
        auto c = bc::map::camp(GOLD);
        if (c.is_visible() && c.is_alive() && cheb(me.position(), GOLD) <= 3) {
            try { me.attack(c); P("atk1 hp=%.0f", c.health()); } catch (const std::exception& e) { P("atk1 ERR %s", e.what()); }
            try { bool ok = me.abilities()[0].use(); P("reset ok=%d can_attack=%d", (int)ok, (int)me.can_attack()); } catch (const std::exception& e) { P("reset ERR %s", e.what()); }
            try { me.attack(c); P("atk2 hp=%.0f", c.health()); } catch (const std::exception& e) { P("atk2 ERR %s", e.what()); }
        }
        phase++;
    }
}

int main() {
    while (true) {
        try {
            if (bc::is_draft()) draft();
            else if (is_team_a() && bc::self().is_alive()) {
                const auto r = bc::round_number();
                if (r == 1) {
                    for (auto& g : bc::map::camp_groups()) for (auto& c : g.camps()) {
                        auto s = c.base_stats();
                        P("CAMPSTATS kind=%d hp=%.0f+%.1f str=%.0f+%.2f foc=%.0f+%.2f range=%d vis=%.0f", (int)c.kind(), s.base_health, s.health_growth, s.base_strength, s.strength_growth, s.base_focus, s.focus_growth, s.base_attack_range, s.vision_radius);
                        break;
                    }
                }
                if (r < 400) switch (bc::self().champion_name()) {
                    case bc::champion_type::vendetta: vendetta(); break;
                    case bc::champion_type::stellar: stellar(); break;
                    case bc::champion_type::ryth: ryth(); break;
                    case bc::champion_type::tavi: tavi(); break;
                    case bc::champion_type::vesper_vale: vesper(); break;
                    default: break;
                }
                if (r == 2) {
                    for (auto& e : bc::champions(team::enemy)) {
                        try { P("enemy visible=%d", (int)e.is_visible()); P("enemy gems=%u", e.gem_count()); } catch (const std::exception& ex) { P("enemy gem_count err %s", ex.what()); }
                        break;
                    }
                }
            }
        } catch (const std::exception& e) {
            std::printf("ERR %s\n", e.what());
        }
        bc::end_turn();
    }
}
