# x_fight7: fight deaths (agent fight7, session 7)

Baseline `bots/_s7`, copy `bots/_x_fight7` (all new switches default off = `_s7` behaviour), patch `experiments/wip/x_fight7.patch`,
outputs `/tmp/fight7/` (bench dirs `base/`, `fog/`, `esc/`, traces `tr/`; summary script `/tmp/fight7/tools/m.py DIR...`).
New tool: `tools/analysis/fight_deaths.mjs` (needs an `XM_TRACE` + `LEGEND_TRACE` build as bot A): every body death of ours, the
dying body's `combat()` lines over the 15 rounds before, classified (fight started while escapable / fled in reach / cornered),
visible enemies at the start vs enemies within 9 at death, remembered hidden enemies at the start, last task.

(work in progress: see the sections below)
