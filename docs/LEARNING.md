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

`tools/rl/space.json` lists the 26 trained parameters and their ranges. Learner hyperparameters are
in the space too, so training can also decide how much the in-match learners should be trusted (for
example `pain_w = 0` switches the pain map off).

## 2. In-match online learning (`learn.h`, `learn.cpp`)

Three learners run inside every game. All are cheap (a few hundred fuel per turn).

**Team stance bandit (reward and punishment per 40-round window).** The team plays one of three stances:
SPREAD (farm everywhere), GROUPED (farm near allies, stay off their half, need more advantage to fight
alone) or PUSH (invade, contest, take closer fights). At the end of each window the stance just played is
scored:

    reward = 10 x (our banked gems - their banked gems) / window
             + reward_kill x enemy deaths - punish_death x our deaths

and its running value is updated (`q += learn_rate x (reward - q)`, a non-stationary bandit). The next
stance is the best value plus context: deaths on our own half (being invaded) add to GROUPED, winning
fights adds to PUSH, and a hysteresis bonus keeps the current one. Optimistic starting values make the
team try another stance as soon as the current one is punished. One body (index 0, which runs every round
even while dead) decides; the stance travels to the others in two spare shared-memory bits, so all bodies
play the same stance.

**Pain map (punishment memory).** The map is split into 6x6 cells. Pain is added where an ally dies and
where we take champion damage; it decays with a 50-round half-life, and an enemy dying near us relieves
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
