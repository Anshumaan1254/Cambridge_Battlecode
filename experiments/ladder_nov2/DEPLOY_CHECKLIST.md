# Deploy checklist: a GOD v23 candidate to the live ladder slot

Applies to every candidate this loop puts live. Tool: `experiments/ladder_nov2/ladder_loop.py` (details in `LADDER_LOOP.md`).
Base for candidates: `bots/god85` (= website v84 + g23 modules, every switch off = v84's games exactly). Live before the first deploy:
website v85 (the user's other session); rollback target = whatever `loop_state.json` records as `previous`.

## Pre-deploy
- [ ] Candidate is a plain bot dir (no leading underscore, e.g. `bots/g23c1`) made with `tools/mkvariant.py NAME --src bots/god85 k=v ...`
      and a `cambc build NAME --release` with 0 errors.
- [ ] All-off build still plays v84's games exactly (3 maps × side a; `/home/claude/analysis/inert/`), re-checked after the last edit.
- [ ] Local panel vs `god84` on `maps/s4` (172 games): margin ≥ −30, our deaths not up by more than 1 a game, 0 faults.
- [ ] Held-out panel vs `god84` on `maps/heldout` (103 generated maps, 206 games): margin ≥ −30, 0 faults.
- [ ] Fuel: the candidate's game-turn fuel p99 < 90k and no more lost turns than v84 on 4 big maps (fuel streams in the bundles).
- [ ] New code since the independent review (rescue, dive filter, camp zone) read once more for the review's bug classes: inert when
      off, no early return that skips base logic, state reset per turn, no stale positions.
- [ ] `cambc bundle NAME --output submissions/history/<name>_<date>.zip`; sha256 recorded in `loop_log.md`.
- [ ] Quota: `cambc match-groups quota --json` shows ≥ 30 free of 50.
- [ ] `loop_state.json` `current` is the live version (run `ladder_loop.py adopt ...` if the live version changed by hand).
- [ ] Note in `docs/plans/god23_plan.md` STATUS: candidate, switches, local numbers, time put live (so the user's other session knows the
      live slot is under test).

## Deploy
- [ ] `python3 experiments/ladder_nov2/ladder_loop.py deploy NAME --note "<=80 chars" --execute` (submit → wait for the build → activate).
- [ ] `cambc submissions list` shows `Live: <new>`; record the activation time.
- [ ] Smoke: the first ranked / unranked games of the new version finish normally (status finished, results present).
- [ ] Paired replays: `ladder_loop.py paired-run --plan experiments/ladder_nov2/paired_v84_to_v85.json --max 30 --execute` (3-way: v84 old,
      v85 new_group, candidate) then the remaining v84 groups (`paired_plan_v84.json`) as quota allows.

## Verdict and rollback triggers (decided before deploying)
- Immediate rollback: any build / runtime failure, games lost to faults, or the platform marks the version failed.
- After ≥ 60 paired games: `ladder_loop.py paired-report` + `verdict`.
  - ROLLBACK when net flips vs v84 are negative with sign-test p < 0.2, or the candidate is ≥ 6 net flips worse than v85 on the 30 shared
    groups, or ranked games since activation (≥ 40) are below Elo expectation by more than 1.5 SE.
  - KEEP when net flips vs v84 are positive with p < 0.2 and not worse than v85 on the shared groups.
  - Otherwise WAIT (more groups; next quota window).
- Rollback = `ladder_loop.py rollback --execute` (activates `previous`); then analyse the candidate's paired losses
  (`cambc matches download`, decode, `experiments/ladder_nov2/agent_fights/extract.py`) before the next candidate.

## Post-deploy
- [ ] `loop_log.md` line with the verdict and numbers; plan STATUS updated; commit + push.
- [ ] Message to the user: what is live, the paired numbers, KEEP / ROLLBACK, what is next.
