# Session 13 (2026-10-19 evening, new container): read this block first; it overrides everything below

- Branch: **`main`** only (the only branch). Baseline: **`bots/_ch2`** (= shipped `legend_m14_commit`, source hash 5f24a1979ddc). Read-only.
  Copy: `SRC=bots/_ch2 tools/variant.sh _x_NAME`; patch: `cd bots && diff -ruN _ch2/src _x_NAME/src > ../experiments/wip/x_NAME.patch`.
  Variants: `SRC=bots/_x_NAME tools/variant.sh _<prefix>N key=val ...` (your own prefix only). Every new behaviour behind a switch in `params.h`, default off.
- Opponents (built, read-only): `_ch2` (baseline), proxies `_mite` (Mite / 2nd), `_ifish` (old ifish), `_px9` (ladder-calibrated), `_snk`
  (sneaky-bush), `_fA` (pressure); older builds `_pg3` (legend_m14), `_m8`, `_m10`; `idle` (unopposed pace).
- Pools: official `'maps/comp/*.map26a'` (17 maps, 34 games); distinct 88 `'maps/*.map26a,maps/comp/*.map26a'`; new-map stand-ins (no hardcoding:
  the final sprint changes the map pool) `'maps/pad17/*.map26a'` (official maps framed: new sizes), `'maps/gen2/*.map26a'` (fresh generated),
  `'maps/var17/*.map26a'` (transposed / swapped official), held-out `'maps/gold3/*.map26a,maps/obj/*.map26a'`. Never `maps/ladder`.
- Every game through `tools/ledger.py run BOT OPP --maps POOL --jobs 2`; summaries `python3 tools/ledger_sum.py --pool POOL BOT`, pace
  `python3 tools/ledger.py run BOT idle --maps POOL --jobs 2` then `python3 tools/ledger_pace.py BOT _ch2 --maps` (`_ch2` 502.7 on the official 17).
  Pooled proxy screen: `python3 tools/screensum.py` (see its header). `--jobs 2` at most (4 cores shared).
- Ladder evidence of THIS build: `experiments/ladder_oct19b/` (50 games, 11 wins; `index.json`, `analysis/*.csv`, `analysis/pergame.txt`), AGENTS.md §S13.
- Never commit/push/checkout/stash/reset (the coordinator's checkpoint loop commits `experiments/wip/x_NAME*` and the ledger every 15 min),
  never `pkill -f`/`pgrep -f`/`killall`, never edit `bots/legend`, `bots/_ch2` or others' bots, never run `tools/setup_session.sh`.
  Keep `experiments/wip/x_NAME.patch` and `x_NAME_NOTES.md` current after every step (they are the handoff if the session dies).

# Session 9 (2026-10-18 afternoon, new container): read this block first; it overrides everything below

- Work only on branch `ccr-a858cd03-q87cpi`. Baseline: **`bots/_xp4`** (= shipped `legend_m6`, source hash 6a1a52e4ddb8). Read-only.
  Copy: `SRC=bots/_xp4 tools/variant.sh _x_NAME`; patch: `cd bots && diff -ruN _xp4/src _x_NAME/src > ../experiments/wip/x_NAME.patch`.
  Variants: `SRC=bots/_x_NAME tools/variant.sh _<prefix>N key=val ...` (your own prefix only).
- Opponents (built, read-only): `_xp4` (baseline), `_px9` (ladder-calibrated proxy, session 8), `_fA` (pressure archetype on legend_m4
  code), `_ST` (legend_st), `_m5a` (legend_m5), `_m4`, `_eA _eB _eC`, `idle`.
- Pools: **distinct maps only** `'maps/*.map26a,maps/comp/*.map26a'` (44 maps, 88 games; never `maps/ladder`, it copies official maps);
  official `'maps/comp/*.map26a'` (34 games) is part of it, report it apart (`tools/ledger_sum.py --pool ...`); held-out
  `'maps/gold/*.map26a,maps/gold2/*.map26a,maps/obj/*.map26a'` (100 games). Games are fast (34 games in ~11 s at 4 jobs).
- Every game through `tools/ledger.py run BOT OPP --maps POOL --jobs 2`; summaries `python3 tools/ledger_sum.py --pool 'maps/*.map26a,maps/comp/*.map26a' BOT`.
  Pace: `python3 tools/ledger.py run BOT idle --maps 'maps/comp/*.map26a' --jobs 2` then `python3 tools/ledger_pace.py BOT _xp4 --maps` (`_xp4` 521.9).
- Replay KPIs for your local games: `python3 tools/bench.py A B --maps ... --out DIR` keeps replays; then
  `python3 tools/strategy_v2/run_all.py OUT DIR_with_side_A_replays` (report.md), `python3 -I tools/strategy_v2/micro.py OUT/dmg=*:A:B`
  (distance bands, hit ranges, fight openers), `python3 -I tools/strategy_v2/teamsum.py OUT/out=*:A:B` (per champion farming).
- Ladder evidence (read these first): `docs/strategy_v2/08_TOP3_VS_TOP3.md`, `experiments/ladder_top3/` (top 3 vs each other),
  `experiments/ladder_m5/` (legend_m5 vs the top 3), `docs/strategy_v2/07_LADDER_M5_18OCT.md`.
- Ship rule (coordinator): >= 50 vs `_xp4` on the 88 and on the official 34, not worse vs `_px9` / `_fA` / `_ST`, pace within +10 of 521.9,
  0 faults, no new fuel rollovers (`node tools/analysis/rollovers.mjs REPLAY` on `gen16_98x99_V_c5`, both sides: 8 per team, rounds 1-3).
- CPU: 4 cores shared by two agents and the coordinator: `--jobs 2`.
- Never commit/push/checkout/stash/reset, never `pkill -f`/`pgrep -f`/`killall`, never edit `bots/legend`, `bots/_xp4` or others' bots,
  never run `tools/setup_session.sh`. Keep `experiments/wip/x_NAME.patch` and `x_NAME_NOTES.md` current (the coordinator commits them).

# Session 7 (2026-10-18, new container): read this block first; it overrides everything below

- Work only on branch `ccr-a858cd03-q87cpi` and only with what is in it (the user: do not look at or merge other branches).
- Baseline: **`bots/_BASE_`** (named in your task prompt) = the shipped build or its successor. Read-only. Make your copy with
  `SRC=bots/_BASE_ tools/variant.sh _x_NAME` (then edit `bots/_x_NAME/src`). Patch: `cd bots && diff -ruN _BASE_/src _x_NAME/src > ../experiments/wip/x_NAME.patch`.
  Variants of your copy: `SRC=bots/_x_NAME tools/variant.sh _xN_k key=val ...` (name them with your prefix; never touch others' bots).
- **Every game goes through the ledger** (`tools/ledger.py`, see AGENTS.md "Resume protocol"): a session cut must not lose finished games.
  - head-to-head: `python3 tools/ledger.py run BOT OPP --maps 'maps/comp/*.map26a' --jobs 2` (official 17, 34 games) first, then the 56-map pool
    `'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a'` (112 games), held-out `'maps/gold/*.map26a,maps/gold2/*.map26a,maps/obj/*.map26a'` (100).
  - unopposed pace: `python3 tools/ledger.py run BOT idle --maps 'maps/comp/*.map26a' --jobs 2`, then `python3 tools/ledger_pace.py BOT1 BOT2 --maps`.
  - summaries without rebuilding: `python3 tools/ledger_sum.py [--maps] BOT_vs_OPP ...` (all / official / deaths / maps not won).
  - a cell is reused only for the exact sources: do not edit a bot after you started its cells (make a new variant instead).
  - replays for analysis: `cambc run A B --map M -o /tmp/<name>/r` (one game) or `tools/bench.py ... --out /tmp/<name>/...`.
- Read-only opponents (built): `_m2` (= shipped `legend_m2`), `_rm` (`legend_rm`), `_ST` (`legend_st`, 1-16 on the ladder), archetypes `_eA` (Ren-first
  pressure), `_eB` (C&I-first farming), `_eC` (caster objective), `idle`. Real evidence: `experiments/ladder_oct18/<map>.repl26a` (17 ladder games of
  `legend_st` as team A, 1 win) and `docs/HOUSEOFCODERS_ENEMY_STRATEGY_REPORT.md`. Our sparring bots are our own code family: a change must make
  sense on the ladder evidence too.
- CPU: 4 cores shared by up to two agents and the coordinator: always `--jobs 2`.
- Acceptance: head-to-head vs the baseline >= 50 on the 56 maps **and** the official 17, not worse vs `_ST` / `_eA` / `_eB` / `_eC`, 0 faults,
  no new fuel rollovers (`node tools/analysis/rollovers.mjs REPLAY` on `gen16_98x99_V_c5`, both sides: baseline 8 per team, rounds 1-3 only).
  Gaps under ~4 points on 112 games are noise: confirm on the held-out pool.
- Never commit/push/checkout/stash/reset, never `pkill -f`/`pgrep -f`/`killall`, never edit `bots/legend` or others' bots, never run
  `tools/setup_session.sh` (it rebuilds shared bots). Keep `experiments/wip/x_NAME.patch` and `x_NAME_NOTES.md` current as you go
  (a session limit can stop you at any time: your notes are the only handoff).

# Session 6 (2026-10-18, new container): read this block first; it overrides everything below

- Baseline: **`bots/_rm`** = frozen copy of `bots/legend` as shipped (`legend_rm`, `submissions/legend.zip`). Read-only.
  Make your copy with `SRC=bots/_rm tools/variant.sh _x_NAME` (then edit `bots/_x_NAME/src`).
  Patch: `cd bots && diff -ruN _rm/src _x_NAME/src > ../experiments/wip/x_NAME.patch`.
- Other read-only bots, built: `_ST` (`legend_st`, the build that went 1-16 on the ladder), `_L0 _es2 _c3 _st _r2 _v6 _hunt _hunt2 _devci _base`,
  `idle`, `_b3`/`_b4` (= legend with `build_style` 3 / 4, the coordinator's), and the **opponent archetypes** (our code with the
  ladder teams' drafts, builds and a more aggressive style; not faithful clones):
  `_eA` Ren-first pressure (Ren, Stellar, C&I, Ryth, Varg; `build_style=3`; fight_margin 1.1, isolated_fight_adv 1.2, PUSH stance first),
  `_eB` CI-first farming (C&I, Stellar, Varg, Ren; `build_style=4`; no joins), `_eC` caster objective (Stellar, Tavi, Prism, C&I, Ren).
- **Real evidence**: `experiments/ladder_oct18/<map>.repl26a` (17 ladder games of `legend_st` as team A, 1 win) and
  `docs/HOUSEOFCODERS_ENEMY_STRATEGY_REPORT.md`. Tools: `node tools/analysis/ladder_econ.mjs FILES --bodies` (captures, splits,
  deaths, items per body, both teams), `node tools/analysis/death_ctx.mjs FILES [--team 1] [--list]` (where / how outnumbered we die),
  `node tools/analysis/pair_deaths.mjs DIR` (needs `<map>_A.repl26a` names: `/tmp/claude-0/up/lad/` has symlinks; recreate with `ln -s`).
  Our local sparring bots are all our own code family: a change must make sense on the ladder evidence, not only locally.
- CPU: 4 cores, two agents + the coordinator. Use `--jobs 2` and your own `--out /tmp/<name>/...`; prefer the cheapest test that
  answers the question (17 official maps x 2 sides = 34 games before the 56-map pool).
- Acceptance: head-to-head vs `_rm` >= 50 on the 56 maps **and** on the official 17, not worse vs `_eA` / `_eB` / `_eC` and `_ST`,
  0 faults, no new fuel rollovers. Gaps under ~4 points on 112 games are noise: confirm on the held-out pool (`maps/gold,gold2,obj`).
- Same rules as below otherwise: never commit/push/checkout/stash/reset, never `pkill -f`/`pgrep -f`/`killall`, never edit
  `bots/legend` or others' bots, keep `experiments/wip/x_NAME.patch` and `x_NAME_NOTES.md` current as you go (a session limit can
  stop you at any time).

# Session 5 (2026-10-17, from ~19:50 UTC, new container): read this block first; it overrides everything below

- Baseline: **`bots/_rm`** = frozen copy of current `bots/legend` (commit d6aa4ef: `_ST` + opening fuel fix, `start_round=2`,
  `capture_reset`, `tribute_elapsed`, `danger_detour`, `team_bank`, `race_mode`). Read-only.
  Make your copy with `SRC=bots/_rm tools/variant.sh _x_NAME` (then edit `bots/_x_NAME/src`).
  Patch: `cd bots && diff -ruN _rm/src _x_NAME/src > ../experiments/wip/x_NAME.patch`.
- Other read-only bots, built: `_ST` (shipped `legend_st` + 2 inert switches), `_L0 _es2 _c3 _st _r2 _v6 _hunt _hunt2 _devci _base`,
  `_rmx` (= `_rm` + `x_side.patch`, `camp_in_fight=3`), `_rmxp` (= `_rmx` + `x_pace.patch`), `_x_side` (= `_ST` + side), `idle`.
- Reference numbers (full panel, 106 maps, 212 games per cell): `_ST`: `_L0` 72.6, `_es2` 65.6, `_r2` 81.1, `_v6` 91.0, `_c3` 56.6
  (mean 73.4, official 67.6). `_rm`: `_L0` 75.0, `_es2` 64.2, `_r2` 88.7, `_v6` 89.2, `_c3` 44.3 (mean 72.3, official 72.3), vs `_ST` 53.3.
- CPU: 4 cores; the coordinator runs full panels with 2 jobs. Use `--jobs 2` and your own `--out /tmp/<name>/...`.
- Acceptance: head-to-head vs `_rm` > 50 on the 56 maps **and** on the official 17, mean over `_ST _L0 _es2 _r2 _v6 _c3` not lower,
  0 faults, no new fuel rollovers. Confirm small gains on the held-out pool (`maps/gold,gold2,obj`).
- Same rules as below otherwise: never commit/push/checkout/stash/reset, never `pkill -f`/`pgrep -f`/`killall`, never edit
  `bots/legend` or others' bots, keep `experiments/wip/x_NAME.patch` and `x_NAME_NOTES.md` current as you go.

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
