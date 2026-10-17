# Session 3 (2026-10-17, from ~15:30 UTC): read this block first; it overrides the older text below

- New container: sparring panel rebuilt (`_base _v6 _r2 _hunt _hunt2 _devci`, `_L0` = 25bed8d, `_L1`, `_f1`, `_es2`).
- **Baseline for every A/B now: `bots/_k1`** = current `bots/legend` + the 8 consistent ES params (deny_bonus 0.043,
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
