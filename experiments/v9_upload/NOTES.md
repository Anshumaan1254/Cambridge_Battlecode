# The user's god_v9_adaptive upload (Oct 21)

`god_v9_adaptive.zip` = the shipped GOD v8 zip (submissions/history/god_v8_20261020.zip, checked: reversing `v9.patch` on its `src/`
gives v8's sources byte for byte) + `v9.patch` (+576 / -20 lines: opponent model `opp.h/opp.cpp`, contact bit, plan presets,
`safety_range`, `enemy_comp_init`, `watchdog`, `ring_reach`, `tavi_str`, sparring personas `spar_*`). Its own README says it was
compile-checked against a stub SDK only and never played. Here it builds on the real SDK 3.0.4 unchanged (bot `bots/_v9up`).

Port onto main (all switches off = main): `experiments/wip/x_v10.patch` (`bots/_x_v10`): the opponent model renamed (`opp9.h`,
`Opp9`, `Preset9`, `opp9()`, `plan9`, `write_plan9`, `plan9_now`: main already has its own `opponent.h` with `OppModel` / `Preset` /
`plan`), v9's `watchdog` renamed `watchdog9` (main has its own `watchdog`), every new line guarded by its switch (fuel-floored scoring:
unguarded instructions change games on large maps; the upload's defaults-build differs from v8 on 4 of 156 maps for that reason, same
winners), `opp_mask` (bit p = plan p may be entered) for ablations; v9's layer is skipped when main's `opp_model` is on (they share bits).

Results: AGENTS.md §S14.8 (Oct 21 checkpoints) and docs/strategy_v2/18_V9_AND_PLAN.md.
