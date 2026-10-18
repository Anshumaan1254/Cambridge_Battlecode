# x_pair6: Cassi & Issac deaths (agent `pair6`, session 6)

Baseline `bots/_b6`, copy `bots/_x_pair6` (all new switches default off = `_b6` behaviour), patch
`experiments/wip/x_pair6.patch`, outputs `/tmp/pair6/` (bench dirs `base`, `e1`..`e7`, held-out `e3h e4h e5h e7h`;
scripts `/tmp/pair6/tools/dsum.py` (deaths per game, pair deaths, both pools) and `means.py` (5-opponent means)).

## 1. Baseline (`_b6`, 56 maps, 112 games per cell; all maps / official 17)

| vs | win | deaths/game | pair deaths/game | other bodies' deaths | their deaths |
|---|---|---|---|---|---|
| `_r2` | 82.1 / 85.3 | 8.63 / 9.76 | 2.45 / 2.91 | 3.74 / 3.94 | 17.2 / 22.5 |
| `_v6` | 87.5 / 91.2 | 9.87 / 11.65 | 2.53 / 3.12 | 4.81 / 5.41 | 14.9 / 18.2 |
| `_hunt2` | 99.1 / 100 | 8.15 / 9.24 | 2.24 / 2.59 | 3.67 / 4.06 | 24.2 / 27.7 |
| `_devci` | 92.9 / 94.1 | 8.06 / 10.00 | 2.21 / 2.85 | 3.63 / 4.29 | 16.3 / 21.0 |
| `_L0` | 75.9 / 79.4 | 11.07 / 14.71 | 2.86 / 3.76 | 5.36 / 7.18 | 15.4 / 19.4 |
| **mean of 5** | 87.5 / 90.0 | 9.16 / 11.07 | **2.46 / 3.05** | 4.24 / 4.98 | 17.6 / 21.8 |

Pair deaths = Cassi deaths from the match statistics (each is 2 body deaths). The pair is 54-60% of our body deaths.
Each pair body triggers ~1.1-1.4 pair deaths per game (Issac 1.38, Cassi 1.06 vs `_r2`) against 0.93 deaths per other body.

## 2. What the replays say (`pair_deaths.mjs`, `pair_trace.mjs` on an `XM_TRACE` copy, 224 games vs `_r2`/`_hunt2`)

- The trigger (the body actually killed) was fighting in 64%, fleeing in 23%; at <25% health the round before in 82%;
  2+ enemies within 6 in 85%. The partner was healthy (75%+) in 68% and 13+ tiles away in 36%.
- Bags: both empty in 74% of pair deaths; 12 gems lost per pair death (29 per game vs `_r2`).
- **65% of pair deaths start with a fight chosen while escapable**, 141 of 161 by the margin rule (adv >= fight_margin),
  88 of them proactive (not yet in reach) at high health, mostly **1 visible enemy vs the pair** (`1v2`: 82 of 161), with no
  remembered hidden enemy (136 of 161). More enemies arrive (1 -> 3 or more in 64 of 120 one-enemy starts); the trigger is
  cornered within 1-2 rounds (65 of 161) and dies with the team estimate still favourable (adv 1.1-10 at 10-35% own health).
- Fight starts by champion (`pair_fights.mjs` + type split, 112 traced games vs `_r2`): death within 12 rounds after a start
  not in reach: Cassi 10.9%, Issac 11.0% against Ren 2.7, Ryth 1.9, Stellar 3.6, Varg 4.4. Net value (enemy deaths within 8 -
  2 x pair death) is still positive in every bin against our code family, which is why plain caution (`pair_caution`) measured
  neutral before: locally the fights pay. Against the ladder (kills 30 vs 167) they do not.
- Distance between the pair bodies (224 games): together (0-3) 6.6 pair deaths per 1000 rounds, 13+ apart 4.4. Keeping the pair
  together would not help (they are together when fighting).
- Comms partner status: the bits work (traced: Issac at risk r142-147, Cassi sees `prisk`), but the bank-on-partner-risk
  rule fired twice in a game (needs an altar within ~6 rounds). Low value; kept as a switch, off.

## 3. What was built (all in `params.h`, default off)

| Switch | What |
|---|---|
| `pair_join_w` (1 = off) | in `combat()`, when both pair bodies are on our side, their health counts as min + w x max (the sum before: the enemy kills both through the weaker one) |
| `pair_veto` (0 = off; 1, 2) | a pair body skips an escapable, not-killable fight when every visible enemy hitting it until the target dies (+1 round) x `pair_veto_margin` exceeds its health (the user's stay_veto, for the pair only); 2 = with the partner in the fight, the weaker body's health |
| `pair_abort_hp`, `pair_retreat_hp` (0.25) | pair body leaves an escapable fight / retreats in `safety()` below this health fraction |
| `pair_bits` (0) | 2 status bits per pair body in bit 7 of bytes 2-5 (Cassi 2-3, Issac 4-5; not with `alert_refresh`): at risk (health < `pair_low` 0.4 and an enemy within `pair_danger_d` 5 or in reach), bag >= `pair_bag_min` 20. The partner of a body at risk banks when walk + ticks <= `pair_bank_t` 6; `bag_caution` counts the partner's posted bag |

## 4. Results (56 maps, 112 games per cell)

5-opponent mean = `_r2 _v6 _hunt2 _devci _L0`. h2h = head-to-head vs `_b6`, all / official (34 games). Held-out = `maps/gold,gold2,obj` vs `_b6` (100 games).

| Bot | settings | win (5-opp mean) all / comp | deaths/game all / comp | pair deaths/game all / comp | other deaths | h2h vs `_b6` | held-out |
|---|---|---|---|---|---|---|---|
| `_b6` | baseline | 87.5 / 90.0 | 9.16 / 11.07 | 2.46 / 3.05 | 4.24 | (50) | (50) |
| `_p6a` | join_w 0.5 | 87.5 / 89.4 | 9.64 / 11.94 | 2.51 / 3.17 | 4.61 | 51.8 / 50.0 | |
| `_p6f` | join_w 0 | 88.0 / 86.5 | 9.00 / 11.21 | 2.26 / 2.88 | 4.48 | 55.4 / 47.1 | 52.0 |
| `_p6c` | veto 1 | 88.0 / 89.4 | 8.72 / 10.62 | 2.14 / 2.62 | 4.45 | 42.9 / 41.2 | 49.0 |
| `_p6e` | pair_caution 0.5 | 87.5 / 86.5 | 9.06 / 11.22 | 2.41 / 3.03 | 4.23 | 49.1 / 50.0 | |
| `_p6i` | veto 1 + join_w 0 | 88.4 / 88.2 | **8.38 / 10.50** | **2.06 / 2.61** | 4.26 | 48.2 / 41.2 | 49.0 |
| `_p6b` | abort 0.4, retreat 0.35 (vs `_r2` only) | 80.4 | 9.26 | 2.47 | | 52.7 / 50.0 | |
| `_p6d` | a + b + veto (vs `_r2` only) | 84.8 | 8.05 | 2.01 | | 43.8 / 35.3 | |
| `_p6g` | veto + bits (vs `_r2` only) | 76.8 | 8.62 | 2.28 | | 42.9 / 44.1 | 49.0 |
| `_p6h` | veto 1, margin 0.8 | (pending) | | | | 54.5 / 55.9 | |

Mirror (h2h vs `_b6`, both sides' deaths per game, pair us/them, all deaths us/them, other bodies us/them):
`_p6f` 2.47/2.78, 9.71/10.71, 4.76/5.15; `_p6h` 2.36/2.79, 9.84/11.33; `_p6i` 2.52/2.66, 10.74/10.42, 5.71/5.10;
`_p6c` 2.51/2.64, 10.60/10.29, 5.58/5.01. With the strict veto (margin 1) the pair declines team fights and the other bodies die
more against an equal opponent; `join_w 0` and margin 0.8 do not have that cost.

Pace (17 official maps vs `idle`): `_p6i` 576.2 = `_b6` (identical per map: the rules only act with enemies in sight).
Fuel: gen16_98x99 rollovers unchanged (A 8 / B 12 in the opening, both sides, `_p6i` vs `_b6`).

## Final report (agent pair6, restored by the coordinator from the hand-back after a worker restart)
- **Recommended and merged into legend**: `pair_veto=1`, `pair_veto_margin=0.8`, `pair_join_w=0`; `pair_bits=0`, `pair_abort_hp`/`pair_retreat_hp` 0.25,
  `pair_caution=0` (`bots/_x_pair6` wasm = tested `_p6k`).
- Means over `_r2 _v6 _hunt2 _devci _L0` (56 maps, 112 games per cell), `_b6` -> recommended: deaths per game 9.16 -> 8.17 (official 11.07 -> 9.92),
  pair deaths 2.46 -> 2.03 (official 3.05 -> 2.52), others 4.24 -> 4.11, win 87.5 -> 88.0 (official 90.0 -> 89.4).
- Head-to-head vs `_b6`: 56 maps 51.8; official 47.1 (16/34) + side-swapped/transposed official copies 48.5 (68 games) = 48.0 over 102; held-out 58.0.
  All switches off = games identical to `_b6`. Pace 576.2 = `_b6`. 0 faults, no new rollovers.
- Rejected: strict veto (margin 1.0: 42.9 h2h, the pair drops out of team fights), margin 0.65 (48.2), veto mode 2 (50.9, held-out 44.0),
  `pair_join_w` 0.5, `pair_caution` 0.5, keeping the pair together (they die more per round within 3 tiles: 6.6 vs 4.4 per 1000).
- Mechanism: 65% of 248 traced pair deaths began as an escapable fight started by the margin rule on one visible enemy; more arrived from the fog.
  Open: a prior for alive enemies not seen recently (64 of 120 such starts ended with 3+ enemies).
