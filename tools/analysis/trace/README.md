# Trace readers (GOD v14 behaviour work, Oct 24)

Inputs: replays kept by `tools/ledger.py run ... --keep DIR` from a LEGEND_TRACE build played without `--release` (team stdout is
inside the bundle; `SRC=bots/god14 tools/variant.sh NAME --define "LEGEND_TRACE 1"`).

- `idle.mjs DIR`: IDLE lines (a body that neither moved nor attacked nor cast, no enemy within 5) by decision point (`path` = the
  turn's chain step, `at` = the source line of the last IDL() marker in farm()/farm_group(), `mf` = a move attempt failed), and idle
  streaks of 4+ rounds.
- `osc.mjs DIR`: back-and-forth windows (tools/analysis/behav.mjs definition) with the traced task / targets of their rounds.
- `sw.mjs DIR`: target switches (SW lines): per game, A-B-A returns within 20 rounds, why the old target was dropped (WHY codes in
  group_score).
- `tr.mjs FILE TYPE R0 R1`: one body's trace lines in a round window, with the enemies within 12.
