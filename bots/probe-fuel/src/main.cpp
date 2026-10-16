// Fuel profiler for SDK helpers.
#include <cambc.h>
#include <cstdio>
namespace bc = cambc;
using bc::vec2; using bc::team;
static std::uint64_t F() { return bc::fuel_remaining(); }
int main() {
    while (true) {
        try {
            if (bc::is_draft()) {
                auto f0 = F();
                auto groups = bc::map::camp_groups();
                auto f1 = F();
                bc::bitboard walls = bc::map::walls() | bc::map::holes() | bc::map::altars();
                auto f2 = F();
                bc::distance_field df; bc::bitboard vis;
                bc::bitboard roots = bc::map::spawn_region(team::ally);
                df.compute(walls, roots, vis);
                auto f3 = F();
                auto lin = df.export_linear_buffer();
                auto f4 = F();
                int s = 0; for (auto v : lin) s += v;
                auto f5 = F();
                std::printf("DRAFT size=%dx%d groups=%zu camp_groups=%llu bbor=%llu df=%llu export=%llu sum=%llu (s=%d)\n", bc::map::width(), bc::map::height(), groups.size(),
                    (unsigned long long)(f0-f1), (unsigned long long)(f1-f2), (unsigned long long)(f2-f3), (unsigned long long)(f3-f4), (unsigned long long)(f4-f5), s);
                const auto mine = bc::draft::current_draft(team::ally);
                const bc::champion_draft order[] = { bc::champion_draft::vendetta, bc::champion_draft::tavi, bc::champion_draft::stellar, bc::champion_draft::varg, bc::champion_draft::ryth };
                bc::draft::pick(order[mine.size() % 5]);
            } else {
                auto& me = bc::self();
                if (bc::round_number() == 2 && me.champion_name() == bc::champion_type::vendetta) {
                    auto a = F(); auto p = me.position(); auto b = F();
                    auto h = me.health(); auto c = F();
                    auto vt = bc::vision::visible_tiles(); auto d = F();
                    auto vc = bc::vision::camps(); auto e = F();
                    auto ct = bc::vision::camp_tiles(); auto f = F();
                    auto pos = ct.positions(); auto g = F();
                    bc::bitboard blocked = bc::map::walls() | bc::map::holes() | bc::map::altars() | bc::map::spawn_region(team::enemy) | bc::vision::champion_tiles() | ct; auto hh = F();
                    bc::distance_field df; bc::bitboard vis, dest; dest.set(p);
                    bc::bitboard roots; roots.set({bc::map::width()/2, bc::map::height()/2});
                    df.compute(blocked, roots, vis); auto i = F();
                    df.compute_to(blocked, roots, dest, vis); auto j = F();
                    auto st = df.next_move_from(p); auto k = F();
                    auto ab = me.abilities(); auto l = F();
                    bool rdy = ab[0].is_ready(); auto m = F();
                    auto en = bc::champions(team::enemy); auto n = F();
                    bool v = en[0].is_visible(); auto o = F();
                    auto grp = bc::vision::camp_groups(); auto q = F();
                    std::uint8_t sm = bc::shared_memory[0]; auto r = F();
                    bc::shared_memory[0] = (std::uint8_t)(sm + 1); auto s = F();
                    auto g2 = bc::map::camp_groups(); auto t = F();
                    auto reach = blocked.reachable_tiles(p, 1); auto u = F();
                    auto gc = me.gold_count(); auto w = F();
                    auto stt = me.state(); auto x = F();
                    std::printf("PLAY pos=%llu hp=%llu vis=%llu vcamps=%llu(%zu) camptiles=%llu positions=%llu blocked=%llu df=%llu df_to=%llu next=%llu abil=%llu ready=%llu champs=%llu isvis=%llu vgroups=%llu shm_r=%llu shm_w=%llu mapgroups=%llu reach=%llu gold=%llu state=%llu left=%llu %d%d%d%d%u%u\n",
                        (unsigned long long)(a-b),(unsigned long long)(b-c),(unsigned long long)(c-d),(unsigned long long)(d-e),vc.size(),(unsigned long long)(e-f),(unsigned long long)(f-g),(unsigned long long)(g-hh),
                        (unsigned long long)(hh-i),(unsigned long long)(i-j),(unsigned long long)(j-k),(unsigned long long)(k-l),(unsigned long long)(l-m),(unsigned long long)(m-n),(unsigned long long)(n-o),(unsigned long long)(o-q),(unsigned long long)(q-r),(unsigned long long)(r-s),(unsigned long long)(s-t),(unsigned long long)(t-u),(unsigned long long)(u-w),(unsigned long long)(w-x),(unsigned long long)x,
                        (int)rdy,(int)v,(int)st.has_value(),(int)h, gc, stt.bits());
                }
            }
        } catch (const std::exception& e) { std::printf("ERR %s\n", e.what()); }
        bc::end_turn();
    }
}
