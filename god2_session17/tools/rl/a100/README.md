# RL training on a Lightning AI A100 studio

`run_a100.sh` trains the parameters of `bots/legend` (every value in `src/params.h` named in `space.json`) against
the ladder-team archetypes and our frozen builds, on many test cases, for a fixed wall-clock budget, and packs the
results into one archive to send back.

## Steps

1. Lightning AI: create a Studio, choose the **A100** machine, open its terminal.
2. Get the code (this branch carries the trainer, the archetypes and the shipped build), either from GitHub:
   ```bash
   git clone -b ccr-a858cd03-q87cpi https://github.com/Akshayg005/Cambridge_Battlecode.git
   cd Cambridge_Battlecode
   ```
   or, without GitHub access, from the single-file bundle `cambc_rl.bundle` (the whole repo with its history; upload
   it to the studio first):
   ```bash
   git clone -b ccr-a858cd03-q87cpi cambc_rl.bundle Cambridge_Battlecode
   cd Cambridge_Battlecode
   ```
3. Start it in the background so a closed browser tab does not stop it (also turn off the Studio's auto-sleep):
   ```bash
   nohup bash tools/rl/a100/run_a100.sh --hours 2.5 > a100.out 2>&1 &
   tail -f tune_out/a100/log.txt        # one line per generation
   ```
   Setup (pip, SDK, ~20 opponent builds) takes 10-20 minutes before training starts; `--hours` counts training plus
   the final tournament; the validation bench afterwards takes another 5-15 minutes.
4. When it prints `done. Send back: .../rl_a100_results_<date>_<commit>.tar.gz`, send that file.
   Interrupted? `bash tools/rl/a100/run_a100.sh --resume --skip-setup --hours <hours left>`.

## What runs where

- **Games run on the CPUs** (the engine is a CPU program): the script uses every core (`nproc`), so the number of
  games per hour is set by the machine's core count, not by the GPU. Expect ~1.5-2 core-seconds per game.
- **The GPU trains the surrogate**: an ensemble of MLPs that predicts the reward of any parameter vector on any test
  case from every game played so far. It proposes two extra candidates per generation and ranks every vector seen
  for the final tournament. Without a GPU or torch it falls back to a ridge model on the CPU.

## Test cases (`suite.json`)

| Group | Cases | Why |
|---|---|---|
| `official_vs_ladder_archetypes` (weight 4) | 17 official maps x `_eA` `_eB` `_eC` `_eD` | the three enemy profiles of the Oct 18 ladder replays (`docs/HOUSEOFCODERS_ENEMY_STRATEGY_REPORT.md`) plus a grouped hunter |
| `official_vs_frozen` (2) | 17 maps x `_ST` (the build that went 1-16), `_rm` (shipped), `_self` (frozen start) | do not lose to ourselves |
| `official_pace` (1.5) | 17 maps vs `idle` | farming speed against the ladder winners' finish round per map |
| `regression_fixtures` (1) | stampede, contest vs `_eC`; rows, expanse vs `_eB`; fragment, eight vs `_eA` | the report's fixtures |
| `ladder_and_generated_vs_panel` (1) | 39 other maps x 6 opponents | generalisation (not in the tournament) |
| `heldout_gold_obj` (0.5) | gold-only and objective maps | gem-scarce maps (not in the tournament) |

Each generation samples `per_gen` cases from each group and plays every candidate on them, both sides.
The final tournament plays the best vectors and the defaults on every tournament case; the winner is `best_params.json`.

## Outputs (`tune_out/a100/`, all in the archive)

`log.txt`, `history.json` (per generation: cases, rewards, theta), `dataset.npz` (every game: vector, case, reward),
`tournament.json` (every entrant's reward per group), `best_params.json` + `best_meta.json` (the winner and how much it
beat the defaults by), `latest_params.json`, `surrogate_report.txt` (held-out accuracy), `validation.txt` (the winner
vs each opponent on the 17 official maps), `meta.txt` (commit, cores, GPU).
