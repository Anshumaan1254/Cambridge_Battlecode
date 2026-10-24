"""Make a patched copy of bots/g8h/src (no traces) for release benches: python mkvar.py DST_SRC_DIR PATCH[,PATCH...]
Patches: npfix (no-progress clock restarts after any turn not spent pursuing the target)."""
import os, shutil, sys

SRC = "C:/battlecode/Cambridge_Battlecode/bots/g8h/src"
dst = sys.argv[1]
if os.path.exists(dst):
    shutil.rmtree(dst)
shutil.copytree(SRC, dst)


def patch(fn, old, new):
    p = f"{dst}/{fn}"
    s = open(p, encoding="utf-8").read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"{fn}: anchor found {n} times: {old[:80]!r}")
    open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new))


for name in sys.argv[2].split(","):
    if name == "npfix":
        patch("brain.h", "\tint prog_group = -1, prog_best = 9999, prog_round = -1000;",
              "\tint prog_group = -1, prog_best = 9999, prog_round = -1000, prog_seen = -1000;")
        patch("brain.cpp", "\t\tif (task_group != prog_group)\n\t\t\tprog_group = task_group, prog_best = dnow, prog_round = round;",
              "\t\tconst bool prog_fresh = task_group != prog_group || prog_seen < round - 1; // a turn spent elsewhere (bank, home, fight, recall, death) restarts the clock\n"
              "\t\tprog_seen = round;\n\t\tif (prog_fresh)\n\t\t\tprog_group = task_group, prog_best = dnow, prog_round = round;")
    elif name == "npfix2":
        # narrower: restart the no-progress clock only after a recall / channel / death gap, a bank or home trip, or a stop on spawn
        patch("brain.h", "\tint prog_group = -1, prog_best = 9999, prog_round = -1000;",
              "\tint prog_group = -1, prog_best = 9999, prog_round = -1000, prog_turn = -1000;")
        patch("brain.cpp", "\tif (P.osc_fix && task_group >= 0 && task_group < static_cast<int>(world().groups.size()) && (task == T_FARM || task == T_CAPTURE || task == T_WAIT))\n\t{\n",
              "\tif (P.osc_fix && (prog_turn < round - 1 || task == T_TRIBUTE || task == T_HOME || world().ally_spawn.is_set(pos)))\n"
              "\t\tprog_group = -1; // away from the target (recalled, channelled, dead, banking, home): the next pursuit starts a new clock\n"
              "\tprog_turn = round;\n"
              "\tif (P.osc_fix && task_group >= 0 && task_group < static_cast<int>(world().groups.size()) && (task == T_FARM || task == T_CAPTURE || task == T_WAIT))\n\t{\n")
    elif name == "npnodash":
        # the no-progress detector only blacklists the target (never turns the hole crossings off for stall_dash_off rounds)
        patch("brain.cpp", "\t\t\tif (kit.dash >= 0 && P.dash_holes && W.dash_off_until < round && !(P.pocket_guard && W.dist_home(pos) >= BIG))\n\t\t\t{\n\t\t\t\tW.dash_off_until = round + P.stall_dash_off; // (never inside a pocket: the hole crossings are its only way out)",
              "\t\t\tif (false && kit.dash >= 0 && P.dash_holes && W.dash_off_until < round && !(P.pocket_guard && W.dist_home(pos) >= BIG))\n\t\t\t{\n\t\t\t\tW.dash_off_until = round + P.stall_dash_off; // (never inside a pocket: the hole crossings are its only way out)")
    elif name == "pgfix":
        patch("brain.h", "\tint prog_group = -1, prog_best = 9999, prog_round = -1000",
              "\tint pocket_since = -1000, pocket_seen = -1000; // pocket guard: when we entered the pocket we stand in, last turn seen in one\n\tint prog_group = -1, prog_best = 9999, prog_round = -1000")
        patch("brain.cpp", "\t\tif (round - last_act_round >= P.pocket_idle && task != T_CAPTURE && !reward_here()",
              "\t\tif (pocket_seen < round - 1)\n\t\t\tpocket_since = round; // just entered (or re-entered) a pocket: its idle clock starts now\n\t\tpocket_seen = round;\n"
              "\t\tif (round - std::max(last_act_round, pocket_since) >= P.pocket_idle && task != T_CAPTURE && !reward_here()")
    else:
        sys.exit("unknown patch " + name)
print("ok", dst)
