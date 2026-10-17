# Session 4 (2026-10-17, new container): read this block first; it overrides everything below

- Baseline: **`bots/_ST`** = frozen copy of current `bots/legend` (= shipped `legend_st` + 2 inert switches). Read-only.
  Make your copy with `SRC=bots/_ST tools/variant.sh _x_NAME` (then edit `bots/_x_NAME/src`).
  Patch: `cd bots && diff -ruN _ST/src _x_NAME/src > ../experiments/wip/x_NAME.patch`.
- Sparring bots (read-only, built): `_base _v6 _r2 _hunt _hunt2 _devci` (panel), `_L0` (ladder build, 25bed8d),
  `_es2`, `_c3` (earlier shipped builds), `idle` (never moves: pace).
- Pools: 56 maps `'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a'` (112 games/opponent, ~50 s at 4 jobs);
  held-out `'maps/gold/*.map26a,maps/gold2/*.map26a,maps/obj/*.map26a'` (100 games). **`maps/comp/` (17 official maps) is the
  real ladder pool: always report it separately.** `python3 tools/sum.py [--maps] DIR...` prints all-map and comp-only
  win rates (and per official map with `--maps`).
- Reference: `_ST` vs `_c3` 56.2, `_L0` 70.5, `_es2` 59.8, `_r2` 74.1, `_v6` 86.6 (88.4 for this exact build), `_devci` 94.6.
  Unopposed pace on the 17 official maps (vs `idle`, mean of both sides): 585 rounds (ambush 820, collision 554,
  contest 1088, corners 411, eight 427, elkring 486, expanse 638, fragment 560, interlock 572, lanes 498, monolith 416,
  packs 374, pilgrimage 900, rows 436, rushbait-v2 716, stampede 706, swirl 342).
- Use `--jobs 2` / `PANEL_JOBS=2` and your own `--out /tmp/<name>/...`; 4 CPUs are shared with another agent and the coordinator.
- Acceptance for a merge: head-to-head vs `_ST` > 50 on the 56 maps **and** on the official maps, panel (`_L0 _es2 _r2 _v6 _devci`)
  mean not lower, 0 faults, no new rollovers. Gaps under ~4 points on 112 games are noise: confirm on the held-out pool.
- Never commit/push (the coordinator does). Keep `experiments/wip/x_NAME.patch` and `x_NAME_NOTES.md` up to date as you go.

# Session 3 (2026-10-17, from ~15:30 UTC): read this block first; it overrides the older text below

- New container: sparring panel rebuilt (`_base _v6 _r2 _hunt _hunt2 _devci`, `_L0` = 25bed8d, `_L1`, `_f1`, `_es2`).
- **(from ~18:00 UTC) Baseline: `bots/_C3`** = frozen copy of the shipped `legend_c3`; copies with `SRC=bots/_C3 tools/variant.sh _x_NAME`,
  patches `cd bots && diff -ruN _C3/src _x_NAME/src`. Earlier baseline (agents `obj`, `cast`): `bots/_k1` = current `bots/legend` + the 8 consistent ES params (deny_bonus 0.043,
  cap_recall_hp 0.61, q0_push -0.718, fight_learn_rate 0.235, cornered_margin 0.634, isolated_fight_adv 1.428,
  target_threat_adv 1.305, fight_back_margin 0.873). Read-only. Make your copy with
  `SRC=bots/_k1 tools/variant.sh _x_NAME` (then edit `bots/_x_NAME/src`). Patches: `cd bots && diff -ruN _k1/src _x_NAME/src`.
- Map pool: **56 maps** = `maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a` (112 games per opponent, ~50 s with 4 jobs).
  **`maps/comp/` (17 maps) is the real ladder pool**: always report it separately. `python3 /tmp/ev/sum.py DIR...` prints
  all-map and comp-only win rates and deaths for bench output dirs (copy it if /tmp/ev is gone: it is 20 lines).
- `_k1` reference (56 maps): vs `_es2` 49.1 (comp 47.1), `_r2` 67.0 (comp 70.6), `_v6` 86.6 (comp 82.4).
- Use `--jobs 2` / `PANEL_JOBS=2`; the coordinator also runs panels.

# Rules for parallel agents (session of 2026-10-17, from ~10:00 UTC)

Several agents work in this checkout at the same time. Read `AGENTS.md` first (sections 0b, 2, 3, 8, 10).

## Environment (already set up; do not redo)
- `cambc 2.2.5` (engine changed from 2.2.2: re-measured, legend's results are unchanged), SDK in `sdk/`, wasm toolchain
  cached in `/root/.cache/cambc/` (if a download ever fails TLS, fetch it with `curl --cacert /root/.ccr/ca-bundle.crt`).
- Sparring panel built: `bots/_base _v6 _r2 _hunt _hunt2 _devci`. **`bots/_L0`** = frozen copy of `bots/legend` at commit
  25bed8d (the current submitted build). Treat all of these as read-only.
- Baseline, legend on engine 2.2.5, 45-map pool, 90 games per cell: vs `_r2` 60.0, `_v6` 73.3, `_hunt` 91.1, `_hunt2` 95.6,
  `_devci` 76.7, `_base` 88.9 (mean of the last five: 85.1).

## Rules
1. Work only in your own bot copies, named `bots/_x_<yourname>*` (start: `mkdir -p bots/_x_NAME && cp -r bots/legend/src bots/_x_NAME/ && cp bots/legend/.gitignore bots/_x_NAME/`).
   Never edit `bots/legend`, `bots/_L0` or another agent's bots. Never rebuild the shared sparring bots.
2. Never `git commit`, `git push`, `git checkout`, `git stash` or `git reset`: the coordinator commits. You may create new
   files under `tools/` (new files only, or files you own), `maps/<your dir>/`, and `experiments/wip/`.
3. CPU: 4 cores shared by several agents. Benchmarks: `python3 tools/bench.py A B --maps ... --jobs 2`, panels:
   `PANEL_JOBS=2 tools/panel.sh BOT 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' _L0 _r2 _v6 _hunt _hunt2 _devci _base`.
   Use your own `--out` / `PANEL_OUT` directory under `/tmp/<yourname>/` (not the default).
4. Never use `pkill -f`, `pgrep -f` or `killall` (they killed agents' shells before). Run long jobs from a script file with
   `nohup script > log 2>&1 &` and wait on the PID.
5. Deliverables, kept up to date as you go (a session limit can cut you off at any time):
   - `experiments/wip/x_<name>.patch`: `cd bots && diff -ruN legend/src _x_<name>/src > ../experiments/wip/x_<name>.patch`
     (applies with `cd bots/X && patch -p1 < ../../experiments/wip/x_<name>.patch`). No `.orig` files in the bot.
   - `experiments/wip/x_<name>_NOTES.md`: what you measured (numbers, maps, opponents, games), what you changed and why,
     what you tried and rejected, params added, how to reproduce. Write it in the style of AGENTS.md (plain, short bullets).
6. Code conventions (AGENTS.md section 10): tabs; every behaviour change behind a `params.h` switch whose comment carries the
   measured evidence; engine actions in try/catch; check fuel: lost turns (rollovers) on `maps/gen16_98x99_V_c5.map26a`
   with `tools/replay/decode.mjs` (`{rollovers: true}`) must not rise.
7. Acceptance: judge on the 45-map panel mean (90 games per opponent); gaps under ~4 points are noise. Also report the
   head-to-head vs `_L0`. 0 faults required.
