# Session 13 scratch tools (moved from the scratchpad so they survive the container)

Quick, single-purpose replay readers written during session 13. They import `../../replay/decode.mjs`.
For replays of the patch-3.0 engine set `CAMBC_ENGINE_WASM` to the v1_0_0 engine (see AGENTS.md §S14), or the
decoder may fall back to an old engine. Side = 0 (team A) / 1 (team B).

| Script | Usage | Prints |
|---|---|---|
| `idx.mjs` | `node idx.mjs DIR` | one row per replay in DIR (`<group>_<nn>_<side>.repl26a`), writes `DIR/index.json`: size, champions, rounds, win, score, both drafts, camp counts |
| `nyxsum.py` | `python3 -I nyxsum.py DECODED_DIR` | per decoded game (`decode.mjs --out x.json`): banked at r200-800, deaths, captured gems, first capture, captures per camp type, casts / attacks / recalls / shops / wards per side (assumes we are side A) |
| `caps.mjs` | `node caps.mjs REPLAY [1]` | captures per body (with 1: every capture) |
| `deaths.mjs` / `deaths.py` | `node deaths.mjs REPLAY` | deaths with killer, position, bag |
| `evts.mjs` | `node evts.mjs REPLAY [FROM_ROUND]` | captures, banks, recalls, deaths from a round on |
| `farmstat.mjs` | `node farmstat.mjs REPLAY:SIDE ...` | capture grouping, respawn-to-first-touch delay, captures per side |
| `respawn_ctx.mjs` | `node respawn_ctx.mjs REPLAY:SIDE ...` | own-side camp respawns: nearest ally, alive count, delay to first touch |
| `track.mjs` | `node track.mjs REPLAY FROM TO [STEP] [TEAM]` | positions and health of one team every STEP rounds |
| `window.mjs` | `node window.mjs REPLAY FROM TO` | every body and its actions round by round (fight traces) |
| `pos.mjs` | `node pos.mjs REPLAY TEAM FROM TO [STEP]` | positions of a team |
| `race_end.mjs`, `rows_end.mjs` | `node race_end.mjs REPLAY SIDE FROM` | the end of a gem race: bags, positions, banks |
| `supply.mjs` | `node supply.mjs MAP...` | own-half gem supply rate and rounds to 1000 |
| `tl.mjs`, `zmap.mjs` | `node tl.mjs REPLAY [a|b] [MAXROUND]` | target timelines / zone plans from `LEGEND_TRACE` builds |
| `stdout.mjs` | `node stdout.mjs REPLAY [team-a.stdout]` | a team's stdout from a local run zip |
| `meta.mjs`, `peek.mjs` | `node meta.mjs REPLAY...` | raw decoded metadata / last events |
| `pergame.py` | `python3 pergame.py SCRATCH` | per-game table of the Oct 19 ladder set |
| `pace.py` | `python3 pace.py BOT... [--pool comp|gen2|pad17|all] [--maps]` | unopposed pace per pool from ledger cells vs idle |
| `pool_cmp.py` | `python3 pool_cmp.py BOT1 BOT2 OPP POOLDIR...` | two bots vs one opponent per map pool from the ledger |
| `summ.py` | `python3 summ.py DIR` | bench directory summary |
| `screen.sh`, `screen_ml.sh`, `q31.sh`, `q35.sh`, `qnx.sh` | examples | screen queues (official maps vs a base + the 5 proxies; draft screen; GOD tweaks; Nyx-map baseline) |
| `ckpt.sh`, `ckpt_loop.sh` | `nohup ckpt_loop.sh &` | the auto-checkpoint loop (git add a list, commit, pull, push every 15 min); edit its file list first |
