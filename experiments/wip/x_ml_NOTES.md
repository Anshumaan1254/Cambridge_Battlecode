# x_ml notes: can a learned model replace the `combat()` fight formula?

Agent `ml`, 2026-10-17. Bots: `bots/_x_ml_log` (logging only), `bots/_x_ml_exp` (logging plus random boldness, data collection), `bots/_x_ml` (candidate).
Status: in progress (this file is updated as results arrive).

## 1. Logging build (done)

- `XML_LOG` (defined at the top of `params.h` in `_x_ml_log`): one `ML,...` line per `combat()` evaluation that has an enemy within 9 tiles
  (not counting enemies standing on their own spawn). 81 fields: our state, allies near, enemy group, the formula's inputs and outputs, the decision taken.
  The decision codes: 1 fight, 2 retreat (they can hit us), 4 early leave, 0 ignore.
- It runs inside `debug_block`, which is free of fuel and compiled out in release builds and on the platform. The submitted bundle is a release build, so the
  logging code cannot affect it.
- Behaviour check: `_x_ml_log` vs `_L0` (identical code, so 45-45 and identical total gems/deaths over 90 games), `_x_ml_log` vs `_r2` 60.0%,
  `_x_ml_log` vs `_v6` 73.3%, `_x_ml_log` vs `_devci` 76.7%. These equal the legend baselines in `AGENT_RULES.md` (60.0, 73.3, 76.7), and four single games
  gave statistics byte-identical to `_L0` (outcome, rounds, gems, per-champion deaths/kills/gold).
- Fuel: logging is inside `debug_block`, so no fuel is charged (nothing to measure).

## 2. Data

(see below)
