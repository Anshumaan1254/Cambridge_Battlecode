# Learning: reward, punishment, and what can learn when

A submitted bot is frozen: the platform runs exactly the code we upload, every match starts from a
clean wasm sandbox, and nothing (no file, no network, no memory) survives from one match to the next.
So "the bot learns from its mistakes" has to mean one of three things, and the bot does all three.

| Level | When it learns | What changes | Where |
|---|---|---|---|
| 1. Offline training (reinforcement learning by policy search) | before we submit, on our machines | the parameter vector in `params.h` | `tools/rl/es_train.py` |
| 2. In-match online learning (reward/punishment while playing) | during every ladder/tournament game | team stance, danger memory, fight confidence | `bots/legend/src/learn.*` |
| 3. Learning from ladder replays (imitation and diagnosis) | between submissions | code and parameters, by us | `tools/replay/*` |

## 1. Offline training: evolution strategies with a shaped reward

The policy is the bot's decision rules; the learnable part is their parameters (fight margins,
recall thresholds, how much gold is worth, learner hyperparameters, ...). 100k fuel per turn leaves no
room for a neural network, but matches are deterministic and take ~1.5 s, so we optimise the parameters
directly with antithetic **Evolution Strategies** (Salimans et al., 2017), a standard RL method that
needs only episode returns.

Reward per game (our side; all from the engine's match statistics):

| Term | Weight | Why |
|---|---|---|
| win / loss | +1 / -1 | the objective |
| banked-gem difference / 1000 | +0.6 | how convincingly |
| each of our deaths | **-0.03** | punishment: a death costs 60 rounds of a body and feeds them 50 gold |
| each enemy death | +0.015 | reward kills, but less than we punish deaths |
| gems we carried into deaths / 22 | **-0.02** | punishment: dying with a bag hands it to the killer |
| (2000 - win round) / 2000 on wins | +0.15 | win fast (fewer rounds for comebacks) |

Each generation samples `pop` antithetic pairs of perturbations of the parameter vector, builds every
candidate, plays all of them against the same maps and opponents (common random numbers), ranks the
rewards (fitness shaping) and moves the mean along the estimated gradient with an Adam step. The
opponent pool is a league: the previous release, aggressive "hunter" archetypes built on the current
code with the ladder's drafts, a Cassi & Issac draft, and the starter bot. The mean policy is evaluated
every generation, so the log shows real progress, not the luckiest sample.

```bash
python3 tools/rl/es_train.py --space tools/rl/space.json \
    --opponents _base,_hunt,_hunt2,_devci --maps 'maps/*.map26a,maps/ladder/*.map26a' \
    --gens 10 --pop 4 --maps-per-gen 8          # ~6-10 min per generation on 4 cores
python3 tools/rl/apply_params.py tune_out/es/best_params.json   # bake the learned values in
```

`tools/rl/space.json` lists the 32 trained parameters and their ranges. Learner hyperparameters are
in the space too, so training can also decide how much the in-match learners should be trusted (for
example `pain_w = 0` switches the pain map off).

### Training on your own machine (tools/rl/train_local.sh)

`tools/rl/train_local.sh` runs the loop above on your own computer with one command. It sets up
everything it needs, trains, validates the result and packs it into one archive to send back. It runs on
Linux and macOS (on Windows, use WSL).

```bash
git pull                                     # the latest pushed bot (use a full clone, not --depth 1)
tools/rl/train_local.sh                      # defaults: 16 generations, 4 antithetic pairs, all CPUs
tools/rl/train_local.sh --resume --gens 6    # after an interruption: 6 more generations
```

**Prerequisites.** git and python3. The script installs numpy and `cambc==2.2.5` with `pip --user` if
they are missing. It needs network access for that, and for the first `cambc build`, which downloads the
wasm toolchain once. The bot was last verified on cambc 2.2.5; the script warns about any other version.
The sparring panel is built from three older commits, so the clone must have their history.

**The seven steps.** Each step is logged to the console and to `tune_out/es/console.txt`.

| Step | What it does |
|---|---|
| 1. Prerequisites | Checks git and python3; installs numpy and cambc 2.2.5 if they are missing. |
| 2. SDK and maps | `cambc init .` (C++) if `sdk/cpp` is missing, then `cambc maps pull` for the current official maps. Offline, it trains on the committed maps. |
| 3. Opponents | `tools/make_sparring.sh` rebuilds the sparring panel (`_base`, `_v6`, `_r2`, `_hunt`, `_hunt2`, `_devci`). It also freezes the bot being trained into `bots/_self`, a self-play opponent. |
| 4. Build and smoke test | Builds `legend` and plays one 300-round game against `_v6`, so a broken toolchain fails here, not after an hour. |
| 5. Training | `tools/rl/es_train.py` on `tools/rl/space.json` (32 parameters). Each finished generation is saved to `tune_out/es/`. |
| 6. Validation | Copies the bot to `bots/_es_best`, writes `best_params.json` into its `params.h`, and plays it against every opponent on every map, both sides. One `==` line per opponent goes to `tune_out/es/validation.txt`. |
| 7. Archive | Writes `rl_results_<date>_<commit>.tar.gz` in the repo root. |

The archive holds:

- `meta.txt`: commit, branch, cambc version, host, CPUs, options, start and end time, and how many files
  in `bots/legend/src` were uncommitted. A non-zero count means local edits were trained, so the commit
  alone does not identify the bot.
- `console.txt`, `validation.txt`, `log.txt`, `history.json`, `best_params.json` and `best_meta.json`, plus `latest_params.json`.
  `best_params.json` is the vector that was actually played in training with the highest mean reward so far
  (`best_meta.json` says which generation, its reward, win rate and maps); `latest_params.json` is the final updated
  vector, which was never played, so only `best_params.json` is validated and should be the one you judge.
- Any official maps the repo does not have yet (untracked `.map26a` files), so the next round can test on them.

**Options.**

| Option | Default | Meaning |
|---|---|---|
| `--gens N` | 16 | generations to run. With `--resume`, they are added to the saved ones. |
| `--pop N` | 4 | antithetic pairs per generation (2N perturbations plus the mean are played) |
| `--maps-per-gen N` | 8 | maps sampled per generation; every candidate plays the same ones |
| `--jobs N` | all CPUs | parallel games (`nproc`, else `sysctl -n hw.ncpu`, else 4) |
| `--opponents LIST` | `_v6,_hunt,_hunt2,_devci,_r2,_self` | comma-separated opponents |
| `--maps GLOBS` | `maps/*.map26a`, `maps/ladder/`, `maps/comp/`, `maps/gold/` | comma-separated map globs. `maps/gold/` (gem-scarce test maps) is optional: a glob with no matches is simply empty. |
| `--resume` | off | continue from `tune_out/es/history.json` |
| `--validate-only` | off | skip step 5 and re-run steps 6 and 7 from the existing `best_params.json`. Steps 1 to 4 still run unless `--skip-setup` is given. |
| `--skip-setup` | off | skip steps 1 to 4, when the SDK, the panel and the build are already in place |

**Cost.** One generation plays `(2 × pop + 1) × maps-per-gen × opponents × 2` games. With the defaults that
is 9 × 8 × 6 × 2 = **864 games per generation**. A game takes about 1 to 3 s on one core, so a generation
takes about 4 to 11 min on 4 cores, and the 16 default generations about 1 to 3 hours. Validation plays
every opponent on every map, both sides: 6 × 45 × 2 = 540 games on the committed maps (the `zz_test` probe map is
skipped), about 2 to 7 min on 4 cores.

**Notes.**

- Training starts from the current values in `bots/legend/src/params.h`, so a `git pull` that changes them
  changes the starting point.
- A run without `--resume` moves the previous `history.json`, `best_params.json`, `best_meta.json`,
  `latest_params.json` and `log.txt` into `tune_out/es/previous_<timestamp>/`.
- `--resume` adds `--gens` generations to the saved ones, so after an interruption pass the number still
  missing. Ctrl-C is safe: every finished generation is saved.
- Each generation's reward moves with the 8 maps it sampled. Judge a run on the validation table and the
  fixed panel, not on the training log.

**Results.** Send the `rl_results_*.tar.gz` file back. Nothing is applied to `bots/legend` automatically (step 6 only
tests a copy). To validate on a copy: `cp -r bots/legend bots/_es_user && python3 tools/rl/apply_params.py best_params.json --bot _es_user`
(without `--bot` it writes into `bots/legend/src/params.h`; `--dry-run` only prints the values). The learned values are
kept only if the copy beats the current build on the fixed panel.

**Portability.** `tools/variant.sh` and the variant builder in `es_train.py` do their parameter
substitutions in Python instead of GNU `sed -i`, so they also work on macOS. The script puts both pip `--user` script directories on the PATH
(`~/.local/bin` on Linux, `~/Library/Python/<version>/bin` on macOS), with or without `--skip-setup`.

## 2. In-match online learning (`learn.h`, `learn.cpp`)

Three learners run inside every game. All are cheap (a few hundred fuel per turn; the pain map decays every 8 rounds).

**Team stance bandit (reward and punishment per 40-round window).** The team plays one of three stances:
SPREAD (farm everywhere), GROUPED (farm near allies, stay off their half, need more advantage to fight
alone) or PUSH (invade, contest, take closer fights). At the end of each window the stance just played is
scored, with every term in gems:

    gem term = 0.67 x (our banked - their banked this window) + 0.33 x (the same for the previous window)
    reward   = (gem term + kill_gems x enemy deaths - death_gems x our deaths) / reward_scale

(`kill_gems` 25, `death_gems` 45, `reward_scale` 40). Banks land in lumps of one capture, so half of the
previous window is blended in; a death costs more than a kill earns because it also pays the enemy 50 gold
and usually a bag. The first version mixed units (a death counted as about 6 gems while one bank swung the
reward by 18-36), so the bandit followed the bank cycle and could lock a stance out for the whole game.

The value of the played stance gets a soft update (`q += learn_rate x (reward - q)`, an exponential moving
average, the same idea as soft target updates in deep RL). The next stance maximises value + context
(deaths on our own half favour GROUPED, winning fights favours PUSH) + hysteresis for the current one.

Exploration was measured, not assumed. A UCB1 bonus (`ucb_c x sqrt(ln N / (1 + plays))`) plus a drift of
unplayed stances back to their priors (`prior_pull`) cost about 2 points over 540 games (77.6% vs 80.0%
mean win rate on the 45-map panel; the learner switched off scored 79.4%). A game has only ~25 windows
against one fixed opponent, so deliberately trying a worse stance costs more than it teaches; optimistic
priors give enough exploration. Both knobs stay in the code at 0. They were removed from the trainer's search space (`space.json`):
both measured harmful, and both sat at their lower bound.
Epsilon-greedy would be worse still for the same reason (random bad windows). One body (index 0, which runs every round even while dead) decides; the stance travels to the
others in two spare shared-memory bits, so all bodies play the same stance.

**Pain map (punishment memory).** The map is split into 6x6 cells. Pain is added where an ally dies (its
sighting from the last two rounds, else the team's fresh fight alert; unknown deaths add no pain) and where
we take champion damage; it decays with a 50-round half-life, and an enemy dying near us relieves
it. Farming targets in painful cells cost extra rounds, so after losing champions somewhere the team
stops walking back into the same trap one at a time.

**Fight calibration (per champion).** Each champion scales its fight-advantage estimate by
`exp(fight_bias)`. Dying within 8 rounds of choosing a fight lowers the bias (more careful); an enemy
dying near it after it chose to fight raises it (bolder), within limits.

`learn_enabled = 0` (or the per-learner switches) disables them for A/B tests.

## 3. Learning from ladder replays

The platform's match downloads are binary replays. `tools/replay/decode.mjs` decodes them with the
engine's own wasm (per-round state of every champion, camp and group, plus every action), and
`tools/replay/report.py` turns that into a readable report: captures, banking, recalls, shopping,
deaths with killer and local headcount, idle time, set_priority use. `tools/replay/extract_map.mjs`
rebuilds the map each replay was played on, so losses can be replayed locally against our own
imitation opponents. This is how the current version was built: 24 ladder losses were decoded and
analysed, and every finding became either a code change or an opponent archetype that the offline
trainer now plays against.

The loop to repeat after each batch of ladder games:

```bash
node tools/replay/extract_map.mjs --dir <downloaded match folder> maps/ladder lad_   # new real maps
for f in <replays>; do node tools/replay/decode.mjs $f --out $f.json; python3 tools/replay/report.py $f.json; done
python3 tools/draft_tournament.py --src bots/legend --maps 'maps/*.map26a,maps/ladder/*.map26a'
python3 tools/rl/es_train.py ...                     # retrain on the enlarged map pool
```
