# RL trainer for the HouseOfCoders bot (Linux)

`tools/rl/train_rl.py` tunes the bot's parameters (fights, farming, economy and build, team stance, strategy switches,
draft priors) by playing thousands of local games. It outputs the best parameter set plus the learned "weights". It does
not submit anything; send the results archive back and the bot gets built from it.

## What is in this package

| path | what |
|---|---|
| `bots/bb4/src/` | the bot being trained (its `params.h` is the parameter vector) |
| `maps/*.map26a` | the 40 ladder maps |
| `tools/rl/train_rl.py` | the trainer (Python standard library only) |
| `tools/rl/knowledge.json` | what the training starts from: 87 genes with ranges and ladder-measured priors, map weights from ~3,600 ladder games, the reward, the opponent league |
| `tools/rl/make_knowledge.py` | regenerates `knowledge.json` |
| `cambc.toml`, `cmake/`, `sdk/` | the cambc 3.0.5 project files |
| `run_rl.sh` / `stop_rl.sh` | one-command start (installs cambc, trains in the background) / graceful stop |

## Steps

1. Copy `rl_pack_<date>.zip` to the Linux machine and unpack it:
   ```bash
   unzip rl_pack_*.zip
   cd cambc_rl
   ```
2. Start everything with one command (installs cambc 3.0.5 in `./.venv`, then trains 3.5 hours in the background):
   ```bash
   ./run_rl.sh
   ```
   If it says Python or venv is missing: `sudo apt install -y python3 python3-venv python3-pip`, then run it again.
3. Watch it (optional): `tail -f rl_run.log`. In the first ~5 minutes you should see `built 1/1 bots`, then the league
   builds and the first batch of games. The run ends by itself after the time budget.
4. When `rl_run.log` ends with `results: ...`, send back the file **`rl_results_<run>.tar.gz`** from this folder.

Other ways to run it:

| command | what |
|---|---|
| `./run_rl.sh 5` | train for 5 hours instead of 3.5 |
| `./run_rl.sh smoke` | 20-30 minute end-to-end check in the foreground |
| `./run_rl.sh 3.5 --fg` | train in the foreground (stops if the terminal closes) |
| `./run_rl.sh 3.5 --workers 12` | fewer parallel games (if the machine has under ~12 GB free memory) |
| `./stop_rl.sh` | stop early: no new generations, the championship and the results are still written (a few minutes); run twice to exit at once |
| `./run_rl.sh resume rl_results/<run> 2` | continue a stopped run for 2 more hours |

Notes:
- The first bot build downloads cambc's compiler toolchain (cmake, ninja, wasi-sdk), so the machine needs internet once.
- If a build complains about the SDK or CMake files, run `cambc init --yes .` in this folder and start again.
- Parallelism is automatic: games = CPU threads - 2 (an i7-12700 with 20 threads plays 18 games at once, fewer if free
  memory is under ~0.7 GB per game), builds = threads / 3. Override with `--workers N` / `--build-jobs N`.
- It stops starting new work in time to finish inside the budget.

## What to send back

The archive in the project folder: **`rl_results_<run>.tar.gz`**. It contains:

- `best_params.json`: the chosen parameter values, the changes against the start point, and the championship table
- `learned_distribution.json`: the learned search distribution (gene means, step sizes, switch probabilities)
- `report.md`: readable summary (results per opponent before and after, every generation's decision)
- `history.jsonl`, `games.jsonl`, `state.json`, `train.log`: the raw record

## How it works (short)

- **Policy search.** Evolution strategies over the parameter vector. Each generation:
  1. A bandit picks 1-2 parameter blocks (fight, farm, economy, team, switches, objectives, draft).
  2. It samples 12 antithetic candidates; at most 3 switch flips per candidate.
  3. Successive halving races them: 8, then 16, then 24 cases (scaled up to 3x automatically when games are fast
     compared to builds).
  4. The winner must beat the incumbent on 40 *fresh* cases (paired one-sided t-test) to be accepted.
- **Opponents.** Every candidate plays the same `(map, side, opponent)` cases as the incumbent; games are deterministic,
  so scores are paired differences. The opponents are a league, not one copy of ourselves, because local mirror games
  misled us three times this session:
  - the live bot;
  - a "brave" bot that farms through enemies the way top-10 teams do;
  - the previous live bot;
  - the bb4 modules with the archetype draft;
  - six strategy personas: turtle, invader, deathball, objective rusher, ambusher, altar camper;
  - every accepted champion (hall of fame).
- **Maps.** Weighted by ladder frequency × how badly we do there against the top 10.
- **Reward per game.** Win ±1, banked-gem margin, round-300 economy (the ladder's best early predictor), first kill,
  deaths, fast wins, and penalties for bot faults and fuel-outs.
- **Finish.** A championship on new cases ranks the start point, the final incumbent and the best runners-up; the top one
  is `best_params.json`.

## Troubleshooting

- Build failures: `rl_results/<run>/build_logs/<bot>.log`.
- Game failures: `rl_results/<run>/tmp/b<N>/run.log` (kept only when a batch had failures).
- Disk: replays are deleted as soon as they are scored; the bot copies live in `bots/_rl_*` (pruned each generation).
