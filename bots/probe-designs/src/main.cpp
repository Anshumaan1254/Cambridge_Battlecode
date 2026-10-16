// Dumps champion designs (stats, growth, abilities with range/modifier/cooldown) one per round.
#include <cambc.h>
#include <cstdio>
#include <variant>
namespace bc = cambc;
int main() {
    while (true) {
        try {
            if (bc::is_draft()) {
                const auto mine = bc::draft::current_draft(bc::team::ally);
                const bc::champion_draft order[] = { bc::champion_draft::varg, bc::champion_draft::tavi, bc::champion_draft::stellar, bc::champion_draft::ren, bc::champion_draft::ryth };
                bc::draft::pick(order[mine.size() % 5]);
            } else {
                auto& me = bc::self();
                const int r = (int)bc::round_number();
                if (me.champion_name() == bc::champion_type::varg && r >= 1 && r <= 12) {
                    const auto& c = bc::champion_designs[r - 1];
                    const auto s = c.base_stats();
                    std::printf("D %d hp=%.0f+%.0f str=%.0f+%.0f foc=%.0f+%.0f range=%d ms=%d\n", (int)c.champion_name(), (double)s.base_health, (double)s.health_growth, (double)s.base_strength, (double)s.strength_growth, (double)s.base_focus, (double)s.focus_growth,
                        (int)s.base_attack_range, (int)s.base_move_speed);
                    for (const auto& a : c.abilities()) {
                        const auto& inf = a.info();
                        if (!inf) continue;
                        std::visit([&](const auto& v) {
                            using T = std::decay_t<decltype(v)>;
                            float rg = -1, md = -1, rad = -1; int dur = -1;
                            if constexpr (requires { v.range; }) rg = v.range;
                            if constexpr (requires { v.modifier; }) md = v.modifier;
                            if constexpr (requires { v.radius; }) rad = v.radius;
                            if constexpr (requires { v.duration; }) dur = v.duration;
                            std::printf("  A slot=%d kind=%d cd=%d excl=%d range=%.1f mod=%.2f rad=%.1f dur=%d\n", (int)a.slot(), (int)T::kind, v.max_cooldown, (int)v.exclusive_with_movement, rg, md, rad, dur);
                        }, *inf);
                    }
                }
            }
        } catch (...) {}
        bc::end_turn();
    }
}
