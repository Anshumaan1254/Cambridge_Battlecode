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
