# Candidate builds (not shipped)

Builds that passed the tests in `docs/strategy_v2/05_TEST_AND_SHIP_PLAN.md` but are not `submissions/legend.zip` yet.
Upload one on the platform's Submissions page to try it on the ladder; to make it the official build, follow the ship
steps in `submissions/BUILDS.md` (copy to `legend.zip`, add to `history/`, add a row).

| Zip | sha256 | What | Tested (18 Oct 2026) |
|---|---|---|---|
| `legend_exec_20261018.zip` | 4c0d3446c7dd1f587e2fb06b1912d2b040a03d291a544c1001fdf39a56460b9f | `legend_rm` (the build before `legend_m2`/`legend_m4`) + `experiments/wip/x_exec.patch` (hit what is in reach before walking, melee swings before stepping away, fight commitment) | vs `legend` 54.9% (45/82 distinct games), deaths 611-810; vs `legend_st` 53.7%; vs `legend_es2` 73.2%; unopposed pace identical (579); 0 faults. Details: `docs/strategy_v2/06_EXPERIMENTS_18OCT.md` |
