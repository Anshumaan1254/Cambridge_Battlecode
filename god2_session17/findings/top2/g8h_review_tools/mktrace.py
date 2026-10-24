"""Make a traced copy of bots/g8h/src outside the repo (fuel-free debug_block prints; run it with `cambc run` in debug mode).
  python mktrace.py DST_DIR [KEY=VALUE ...]      (params.h overrides as in vbench.py)"""
import os, re, shutil, sys

SRC = os.environ.get("TRACE_SRC", "C:/battlecode/Cambridge_Battlecode/bots/g8h/src")
dst = sys.argv[1]
if os.path.exists(dst + "/src"):
    shutil.rmtree(dst + "/src")
os.makedirs(dst, exist_ok=True)
shutil.copytree(SRC, dst + "/src")


def patch(fn, old, new, count=1):
    p = f"{dst}/src/{fn}"
    s = open(p, encoding="utf-8").read()
    n = s.count(old)
    if n != count:
        sys.exit(f"{fn}: anchor found {n} times: {old[:80]!r}")
    s = s.replace(old, new)
    open(p, "w", encoding="utf-8", newline="\n").write(s)


B = "brain.cpp"
# per-turn state line
patch(B, "\tif (round <= 6)\n\t\tG8H_FT(\"prebuild\");\n\tXM(xm_post());",
      "\tif (round <= 6)\n\t\tG8H_FT(\"prebuild\");\n\tdebug_block({ std::printf(\"T r=%d b=%d ty=%d task=%d g=%d pos=%d,%d hp=%.0f gems=%u gold=%u doff=%d ob=%d fs=%d fuel=%llu\\n\", round, world().my_index, static_cast<int>(type), task, task_group, pos.x, pos.y, hp, gems, gold, world().dash_off_until, osc_break_until, g_rv_fs, static_cast<unsigned long long>(bc::fuel_remaining())); g_rv_fs = 0; });\n\tXM(xm_post());")
patch(B, "namespace\n{\nusing I = bc::item_type;", "static int g_rv_fs = 0; // trace: post-flee skips this turn\nnamespace\n{\nusing I = bc::item_type;")
# no-progress detector
patch(B, "\t\telse if (round - prog_round >= 15)\n\t\t{\n",
      "\t\telse if (round - prog_round >= 15)\n\t\t{\n\t\t\tdebug_block({ std::printf(\"NP r=%d b=%d ty=%d task=%d g=%d pos=%d,%d d=%d best=%d since=%d doff=%d dash=%d home=%d\\n\", round, W.my_index, static_cast<int>(type), task, task_group, pos.x, pos.y, dnow, prog_best, prog_round, W.dash_off_until, kit.dash, W.dist_home(pos)); });\n")
# stall guard / unstick
patch(B, "\tif (P.stall_guard > 0 && kit.dash >= 0 && P.dash_holes && !(P.pocket_guard && W.dist_home(pos) >= BIG))\n\t{\n",
      "\tdebug_block({ std::printf(\"US r=%d b=%d ty=%d task=%d g=%d pos=%d,%d since=%d guard=%d dash=%d\\n\", round, W.my_index, static_cast<int>(type), task, task_group, pos.x, pos.y, ust_since, (int)guard, kit.dash); });\n\tif (P.stall_guard > 0 && kit.dash >= 0 && P.dash_holes && !(P.pocket_guard && W.dist_home(pos) >= BIG))\n\t{\n")
# pocket guard
patch(B, "\t\t\t!flag(state, bc::champion_state::submitting_gems))\n\t\t{\n\t\t\tif (!(can_cast && pocket_dash()))",
      "\t\t\t!flag(state, bc::champion_state::submitting_gems))\n\t\t{\n\t\t\tdebug_block({ std::printf(\"PG r=%d b=%d ty=%d task=%d g=%d pos=%d,%d last_act=%d cast=%d\\n\", round, W.my_index, static_cast<int>(type), task, task_group, pos.x, pos.y, last_act_round, (int)can_cast); });\n\t\t\tif (!(can_cast && pocket_dash()))")
# capture timeout
patch(B, "\t\tif (round - cap_stand_since > static_cast<int>(bc::constants::capture_time) + 10)\n\t\t{\n",
      "\t\tif (round - cap_stand_since > static_cast<int>(bc::constants::capture_time) + 10)\n\t\t{\n\t\t\tdebug_block({ std::printf(\"CT r=%d b=%d ty=%d g=%d pos=%d,%d since=%d enemy_on=%d\\n\", round, world().my_index, static_cast<int>(type), g.id, pos.x, pos.y, cap_stand_since, (int)g.enemy_on_tile); });\n")
# osc breaker
patch(B, "\t\t\tosc_break_until = round + 3;\n",
      "\t\t{\n\t\t\tosc_break_until = round + 3;\n\t\t\tdebug_block({ std::printf(\"OB r=%d b=%d ty=%d task=%d g=%d pos=%d,%d prev=%d,%d\\n\", round, W.my_index, static_cast<int>(type), task, task_group, pos.x, pos.y, osc_hist[0].x, osc_hist[0].y); });\n\t\t}\n")
# post-flee skip
patch(B, "\t\t{ WHY(15); return -1; }", "\t\t{ WHY(15); debug_block({ ++g_rv_fs; }); return -1; }")
# pocket dash success
patch(B, "\t\t\t\tpos = c[static_cast<std::size_t>(i)].second;\n\t\t\t\tcast_done = true;\n",
      "\t\t\t\tdebug_block({ std::printf(\"PD r=%d b=%d ty=%d from=%d,%d to=%d,%d\\n\", round, W.my_index, static_cast<int>(type), pos.x, pos.y, c[static_cast<std::size_t>(i)].second.x, c[static_cast<std::size_t>(i)].second.y); });\n\t\t\t\tpos = c[static_cast<std::size_t>(i)].second;\n\t\t\t\tcast_done = true;\n")
# pre-init move
patch(B, "\tif (!alive || !can_move || bc::fuel_remaining() < 20000)\n\t\treturn;\n\ttry\n\t{\n\t\tbc::self().move_towards(",
      "\tdebug_block({ std::printf(\"PI r=%d b=%d ty=%d pos=%d,%d fuel=%llu inited=%d\\n\", round, world().my_index, static_cast<int>(type), pos.x, pos.y, static_cast<unsigned long long>(bc::fuel_remaining()), (int)inited); });\n\tif (!alive || !can_move || bc::fuel_remaining() < 20000)\n\t\treturn;\n\ttry\n\t{\n\t\tbc::self().move_towards(")
# tribute: why no bank (rate limited) and a new bank decision
patch(B, "\tif (!want)\n\t\treturn false;\n#ifdef LEGEND_TRACE",
      "\tdebug_block({ if ((!want && gems >= 20 && round % 10 == 0) || (want && task != T_TRIBUTE)) std::printf(\"%s r=%d b=%d ty=%d gems=%u dist=%d need=%d via=%d rb=%d spawn_altar=%d doff=%d pos=%d,%d\\n\", want ? \"BANK\" : \"NB\", round, W.my_index, static_cast<int>(type), gems, dist, need, via_home, (int)recall_bank, W.spawn_altar_d, W.dash_off_until, pos.x, pos.y); });\n\tif (!want)\n\t\treturn false;\n#ifdef LEGEND_TRACE")
# real channel suppression
patch("world.cpp", "\t\tif (P.real_channel)\n\t\t\te.recalling = e.recalling && e.recall_streak >= 2;\n",
      "\t\tif (P.real_channel)\n\t\t\te.recalling = e.recalling && e.recall_streak >= 2;\n\t\tdebug_block({ if (flag(info.state, bc::champion_state::recalling)) std::printf(\"RC r=%d me=%d enemy=%d at=%d,%d streak=%d counted=%d gems=%u\\n\", round, my_index, static_cast<int>(t), info.x, info.y, e.recall_streak, (int)e.recalling, e.gems); });\n")
# danger detour hold
patch("nav.cpp", "\t\t\tif (P.osc_fix && P.stuck_detour && (detour.field != &field || rnd > detour.until))\n\t\t\t\tdetour = { &field, rnd + P.detour_hold, start_v };\n",
      "\t\t\tif (P.osc_fix && P.stuck_detour && (detour.field != &field || rnd > detour.until))\n\t\t\t{\n\t\t\t\tdetour = { &field, rnd + P.detour_hold, start_v };\n\t\t\t\tdebug_block({ std::printf(\"DH r=%d pos=%d,%d\\n\", rnd, pos.x, pos.y); });\n\t\t\t}\n")

# hop fuel guard: fuel at the crystal comparison near spawn
if os.environ.get("TRACE_HOP"):
    patch(B, "\tif (W.dist_home(pos) <= 4 && !inside_island() && bc::fuel_remaining() >= static_cast<unsigned long long>(P.hop_score_start))\n\t{\n\t\tconst bool crystal",
          "\tdebug_block({ if (W.dist_home(pos) <= 4 && !inside_island()) std::printf(\"HG r=%d b=%d ty=%d fuel=%llu crystal_ok=%d has=%d gold=%u blocked=%d\\n\", round, W.my_index, static_cast<int>(type), static_cast<unsigned long long>(bc::fuel_remaining()), (int)(has_crystal() || (W.ally_spawn.is_set(pos) && gold >= 10)), (int)has_crystal(), gold, (int)(bc::fuel_remaining() < static_cast<unsigned long long>(P.hop_score_start))); });\n"
          "\tif (W.dist_home(pos) <= 4 && !inside_island() && bc::fuel_remaining() >= static_cast<unsigned long long>(P.hop_score_start))\n\t{\n\t\tconst bool crystal")

# params overrides
p = f"{dst}/src/params.h"
s = open(p, encoding="utf-8").read()
for kv in sys.argv[2:]:
    k, v = kv.split("=", 1)
    s, n = re.subn(r"^(\s*[a-z]+(?: [a-z]+)? " + re.escape(k) + r" = )[^;]*;", lambda m: m.group(1) + v + ";", s, flags=re.M)
    if n != 1:
        sys.exit(f"param {k}: {n} matches")
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok", dst)
