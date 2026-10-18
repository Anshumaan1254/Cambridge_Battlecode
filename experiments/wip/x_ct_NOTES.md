# x_ct: contest plan (agent `ct`, session 11/S7R workflow `contest-and-neutral`)

Baseline `_m10` (= `_m8` play). Copy `bots/_x_ct` (= `_m10` + `mono_*` code, diff in `x_ct.patch`), variants `_ct0`..`_ct5` (params of the copy).
Test maps `maps/ct/` (contest_sw, contest_tr, contest_swtr = geometry variants; pert_s1..6 = perturbed copies). Helper scripts of the previous
agent: /tmp/ct/ (cell.sh, pools.sh, sum.py, mono.mjs); lost with the container, not needed.
Contest pool CT4 = `maps/comp/contest.map26a,maps/ct/*.map26a` (10 maps = 20 games); GM = gold_mono_* of gold, gold2 (12 maps).

## State at takeover (20:30)
- `_ct0` = detector only (identical to `_m10`). `_ct1` mono_open_rounds 150: vs `_m8` 25.0 on CT4 (bad), vs `_mite` 45, `_ifish` 45.
- `_ct2..5` cells were being run by /tmp/ct/run1.sh (CT4 vs `_mite _ifish _px9 _m8`).

## Plan
1. Understand how contest is lost/won (replays of `_m10` vs `_mite`/`_snk`/`_ifish` on contest, both sides).
2. Build a plan gated by `World::mono_mode`: no feeding in the opening, Treasure/gold for the tiebreak, spawn-camp avoidance, monolith with the whole team.
3. Inertness check on the 88 distinct games vs `_m10`.

## Results log
(see below; updated after every result)
