# Ladder losses, round 1: why `legend` lost and what changed

Five lost ladder matches (raw summaries in `matches/ladder1/`, converted with `tools/raw_summary.py`) were
dissected one by one against the bot's source and replays of reconstructed maps, then cross-checked.
Every number below comes from those files or from local benchmarks.

| Match | Map | Score | What happened |
|---|---|---|---|
| 727cae82 | 50×50, 4v4 | 0 – 1023 | We banked **0 gems**: every 66-gem 3-wolf line scored "infeasible", champions idled or farmed 0-gem gold |
| e7ce6da9 | 41×30, 5v5 | 176 – 1084 | Both elk groups on our half (204 of 270 gems per cycle) rejected; enemy Stellar farmed them from range 4 and snowballed |
| e90a37bf | 50×65, 5v5 | 724 – 1028 | Richest group (144 gems) rejected; 24 of our 31 captures were 0-gem gold; a timer abandoned big groups at 95% |
| c2429a3a | 80×80, 3v3 | 754 – 1050 | Pure farming race, 0 kills: the enemy cashed 120-gem elk groups 6 times; we never touched them |
| 2be1b72e | 71×71, 5v5 | 962 – 1000 | We led all game and won fights 10–3, then lost holding **152 unbanked gems** |

## The opponent (one bot, all five matches)

Draft Varg → Cassi & Issac → Tavi → Stellar → Vendetta. It never needs to fight: it wins on farm
throughput. Varg solos 3-wolf lines in ~24 rounds with splash; casters chip elk groups from range 4 with
almost no damage taken; every farmer buys one health emblem; it banks 66–154-gem bags; it steals the big
groups on our half that we leave alone. 58% of everything it farmed came from groups our scorer refused.

## Root causes (ranked) and fixes

| # | Root cause | Fix in the bot | Local effect |
|---|---|---|---|
| 1 | `group_score` hard-rejected every group with summed camp damage ≥ 60 (3-wolf lines, 2+ elk groups): no splash/AoE credit, every camp assumed to hit us for the whole fight, `trips > 3 → -1` | Damage model per kit: Varg splash × live neighbours, AoE × cluster, Ren retaliation; incoming damage decays as camps die, minus shield and stun uptime, shared with an ally; up to 5 heal trips; two bodies on heavy groups; "never idle" fallback | 75% vs the old bot on official-style maps; unopposed pace 452 → 374 rounds |
| 2 | Give-up timer blacklisted any task 60 rounds after it was picked, including heal trips and the capture itself | Progress resets the clock (damage dealt, state change, being in range) | biggest single gain of round 2 (with #6): 53% → 58% vs `_dev2`, 56% → 67% vs the opponent proxy |
| 3 | No health in our builds, so elk groups never became affordable | One Durability Emblem of Health after the first emblem for Varg, Ren, Tavi, Stellar, Cassi, Issac, Vendetta | +8 points vs the opponent proxy |
| 4 | Deny bonus multiplied gold too, sending lone bodies 45 steps for 0-gem gold columns | Deny bonus applies to gems only | +3 points |
| 5 | No team endgame banking: no single bag reached the winning total | Tribute threshold shrinks to ~1 gem as either team nears 1,000; bank first when our bag wins | targets the 962–1000 loss directly |
| 6 | Cleared groups abandoned at capture time by low-health retreats | Finish the 5-round capture when no enemy and no camp can reach us | (in #2's gain) |
| 7 | Danger avoidance was only a tie-break between shortest steps; spells coming off cooldown next turn ignored | Detour search around enemy reach when every shortest step is threatened; spells with 1 round of cooldown count as ready, non-exclusive spells reach 5 | +2.5 points, fewest deaths of all variants |
| 8 | Fights ignored the awake camps hitting us | Camp damage on our tile added to the enemy's damage | +3 points |
| 9 | Carriers fought with bags | Bank first when an enemy is near but cannot reach us yet (≥ 20 gems, altar ≤ 14 steps) | +6 points |
| 10 | Big purses sat unspent | Recall to shop with ≥ 300 gold when nothing can interrupt | neutral |
| 11 | Spells idle on cooldown while walking | Chip any live camp in range 4 with spare spells (camps never heal) | +1.5 points |
| 12 | First-turn fuel exhaustion on large maps (171k of init on 100×97) | Pre-sized group storage; the engine resumes the turn next round, so the cost is one round | small |
| 13 | (found during validation) Inside a teleport island there is no altar, and the only exit fired when the island was empty; with the progress-aware timer a champion hoarded 604 gems there for 900 rounds | Recall out to bank at 60 gems (or a winning bag, or the last 150 rounds); no recall-to-shop from an island | island maps 2/6 → 5/6 vs the old bot |

Tested and **rejected** (data said no): kiting big groups from range 4 at base focus (−18 points with
the old give-up timer, still −2 after fixing it: ~30 damage per round is too slow, e.g. Tavi alone on a
7,200-HP elk group); it is kept only once spells are ≥ 80% of a champion's damage, i.e. late game with
focus items. Skipping rallies while farming also lost (−2 to −4 points in two ablations).

## Self-learning (in-match, C++)

`bots/legend/src/learn.{h,cpp}`. Deterministic, a few hundred fuel per turn, no shared memory needed.

- **Fight posterior.** Beta(3,3) prior on "an exchange ends with an enemy death", updated by every
  death on both sides (global alive flags, so every instance holds the same number). Losing exchanges
  raise the fight margin and the cost of the enemy half; winning ones raise the deny bonus.
- **Race model.** Smoothed banking rate of both teams projects who finishes first; when the enemy
  will finish 25% sooner, take their gems; when we will, stop taking even fights.
- **Model calibration.** Each champion compares the damage it actually deals to and takes from camps
  while farming alone with what its model predicted (decayed sums with pseudo-counts), and scales the
  model's kill time and incoming damage by the ratios.
- **Burst memory.** The largest one-round damage each enemy has landed on us (items included) replaces
  the model's burst for that enemy while its spells are up, and vetoes fights it can win in one round.

Build with `--define "LG_NO_ADAPT 1"` or `--define "LG_NO_CALIB 1"` to A/B the layer.

## Why the bot stays in C++ (not Python)

Python gets 25× the fuel (2.5M per turn) but every bytecode costs fuel. Measured on the engine: a bare
1,000-iteration loop costs **1.78M fuel (71% of a turn)**, and 100 distance-field lookups cost 250k.
The C++ bot spends 30–70k per turn on perception and pathing on 100×100 maps; the same work in Python
would not fit. Net usable compute in Python is ~15× lower, so the learning above is written in C++.

## Sparring partners built from this data

- `_oppR`: our bot with the opponent's draft, health emblem, always-kite casters and 66-gem banking.
  It beats the old `legend` 63–37, close to what the ladder showed.
- Reconstructed ladder maps: `node tools/mapgen/replica.mjs maps` (`rep_727cae82_50x50_R_c4`,
  `rep_e7ce6da9_41x30_H_c5`); official-style pools: `node tools/mapgen/gen.mjs maps 30 4242 o_ official`
  and `node tools/mapgen/gen.mjs maps 120 7777 o2_ official`.
