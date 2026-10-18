# Candidate builds (not shipped)

Builds that passed the tests in `docs/strategy_v2/05_TEST_AND_SHIP_PLAN.md` but are not `submissions/legend.zip` yet.
Upload one on the platform's Submissions page to try it on the ladder; to make it the official build, follow the ship
steps in `submissions/BUILDS.md` (copy to `legend.zip`, add to `history/`, add a row).

| Zip | sha256 | What | Tested (18 Oct 2026) |
|---|---|---|---|
| `legend_exec_20261018.zip` (superseded: its patch is in `legend_m5`) | 4c0d3446c7dd1f587e2fb06b1912d2b040a03d291a544c1001fdf39a56460b9f | `legend_rm` (the build before `legend_m2`/`legend_m4`) + `experiments/wip/x_exec.patch` (hit what is in reach before walking, melee swings before stepping away, fight commitment) | vs `legend` 54.9% (45/82 distinct games), deaths 611-810; vs `legend_st` 53.7%; vs `legend_es2` 73.2%; unopposed pace identical (579); 0 faults. Details: `docs/strategy_v2/06_EXPERIMENTS_18OCT.md` |
| `legend_m5_campfight_20261018.zip` | beba6029513282549a6d9343d7ed5e350ba84fabfd3525be636f83afd2a9566d | `legend_m5` + `camp_in_fight=3` (strategy-v2 A5: an awake camp whose nearest body is an enemy counts as our damage; `experiments/wip/x_doc_m5.patch`) | neutral locally: vs `legend_m5` 51.1 (official 44.1), held-out 49.0; vs `_fA` 75.0 / 82.4, `legend_st` 75.0 / 88.2; pace 521.8; 0 faults. A ladder A/B candidate only: our sparring cannot separate fight rules aimed at the top teams' burst (doctrine agent, `x_doc_NOTES.md`) |
