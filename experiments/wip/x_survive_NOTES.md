# x_survive: cut deaths vs grouped invaders (agent `survive`, session 6)

Baseline `bots/_rm`; copy `bots/_x_survive` (all switches default off = `_rm` behaviour); variants `bots/_sv*`
(`SRC=bots/_x_survive tools/variant.sh _svN key=val ...`). Outputs in `/tmp/survive/`. Patch: `experiments/wip/x_survive.patch`.

## Diagnosis (ladder, 17 games of legend_st, 232 deaths; `tools/analysis/death_story.mjs`, new)
- `node tools/analysis/death_story.mjs experiments/ladder_oct18/*.repl26a --team 0 [--sum] [--max N]`: the 10 rounds before
  each death (victim pos/hp/bag/actions, enemies and allies within 10) and a summary of mechanisms.
- **Not ambushes**: the enemies that end within 6 of the victim were within 8 of it for **7+ rounds before 75%** of deaths
  (none seen: 14%, 0-3 rounds: 2%). The victim moved net **toward** them in 48%, away 29%.
- Victims were mostly **walking, not fighting**: only 64 of 232 attacked a champion twice in the last 8 rounds; 145 mostly moved;
  55% moved away in the last 3 rounds (caught fleeing a same-speed chaser after waiting too long).
- Code: `combat()` has three bands. adv >= fight bars: fight. In reach: fight back or flee. Not in reach and adv between the flee
  rule (only when **isolated** or half the team dead, adv < 1.1) and the fight bar (1.3): return false, so the body keeps farming,
  answers a RALLY (`respond_to_alert` walks in without any assessment) or walks its route, until the group is in reach.
  Then a same-speed chaser cannot be outrun. That is the main mechanism.
- Enemy builds: their bodies have 1.3-2x our max health (Ryth 2,000-2,200 vs our 1,200, Varg 1,464 vs 1,000, Stellar 1,125 vs 750):
  even fights are lost. Builds are the coordinator's task (`build_style 3`); this patch only makes the bodies leave in time.
- Ren retaliation (0.2 x focus per hit received) is not in `combat()`'s enemy damage: fragment r78-88 our Stellar (750) and Ren
  hit their Ren (1,900) for 10 rounds; Stellar lost ~70 a round and died.
- Cassi & Issac: the trigger partner is below 25% health in 64% (ladder) / 70% (local, `_sv1` vs `_eA`, 127 pair deaths) and
  fighting in 47% / 57%; the other partner healthy (72%) and far (13+ tiles 35%). Locally the pair is 52% of all our body deaths.
- Danger memory: an enemy is forgotten by `build_danger` after `threat_memory` 4 rounds and by `group_score` after 8; vision is
  per body; the team DANGER alert is posted but **never read** (`alert_radius` = 0 since it was written, never A/B'd).

## Switches (params.h, all default off)
- `outmatch_flee` (+ `outmatch_flee_adv` 0.8, `outmatch_min_enemies` 2, `outmatch_flee_dist` 8): the isolated early exit also when
  we are not alone but the visible group (2+ enemies, nearest within 8, not yet in reach) gives adv < 0.8.
- `pair_flee_bonus`: Cassi & Issac use outmatch_flee_adv + this.
- `pair_low_hp`: Cassi & Issac skip escapable fights below this health fraction (others 0.25).
- `pair_retreat_hp`: Cassi & Issac safety() retreat line (max with retreat_hp 0.25).
- `ren_reflect`: a fight on Ren adds 0.2 x focus x (1 + allies here) to the enemy damage.
- `threat_score_memory`: rounds a seen enemy still guards camps within 8 in group_score (was a literal 8).

## Results (official 17 maps, both sides, 34 games per cell; deaths ours-theirs)
| Bot | vs `_rm` | vs `_eA` |
|---|---|---|
| `_rm` (baseline) | - | 58.8 (508-612); vs `_eC` 76.5 (464-540) |
| `_sv1` outmatch_flee 0.8 | 55.9 (419-482) | 61.8 (467-567) |
| `_sv2` outmatch_flee 1.0 | 50.0 (433-481) | 61.8 (509-576) |
| `_sv3` alert_radius 8 | 47.1 (494-419) | 50.0 (643-510) |
| `_sv4` threat_score_memory 20 | 50.0 (461-418) | 58.8 (491-602) |
| `_sv5` outmatch 0.8 + pair_flee_bonus 0.3 | 55.9 (423-514) | 70.6 (477-551) |
| `_sv6` outmatch 0.7 | 52.9 (410-469) | 55.9 (488-560) |
| `_sv7` outmatch 0.8, min_enemies 1 | 50.0 (405-569) | 55.9 (445-571) |
| `_sv8` outmatch 0.8 + ren_reflect | 58.8 (430-551) | 61.8 (497-559) |
| `_sv9` outmatch 0.8 + pair_low_hp 0.4 | 55.9 (413-500) | 64.7 (466-582) |
| **`_svA`** outmatch 0.8 + pair_flee_bonus 0.3 + ren_reflect + pair_low_hp 0.4 | **64.7 (355-522)** | **70.6 (394-614)** |
| `_svB` = `_svA` + pair_retreat_hp 0.4 | 64.7 (376-528) | 55.9 (417-561) |
| `_svC` = `_svA` without pair_low_hp | 61.8 (339-531) | 70.6 (455-642) |

Other cells (official 17, 34 games): vs `_eC`: `_rm` 76.5 (464-540), `_sv1` 94.1, `_svA` 85.3 (372-616), `_svB` 85.3, `_svC` 88.2.
vs `_ST`: `_rm` 52.9 (534-403), `_sv1` 55.9, `_svA` 44.1 (393-415), `_svB` 44.1, `_svC` 52.9. vs `_eB`: `_rm` 73.5 (451-569).
34-game cells have a standard deviation of ~8.5 points: the 56-map pool decides (below).
- Fuel: `_svA` vs `_rm` on gen16_98x99 both sides: 8 rollovers per team, same as `_rm` (no new lost turns).

## Traced games (`_svT` = `_svA` + XM_TRACE vs `_eA` on eight, fragment, interlock, swirl, collision; `tools/analysis/pair_trace.mjs`)
- Fights started from outside reach are rarely deadly: 5% of such turns (1,225) were followed by the body's death within 10 rounds.
- The deaths come from in-reach turns: 101 'cornered' fight turns (no escape, adv >= cornered_margin 0.634, typically 0.65-0.75),
  96 in-reach fights with escape, 128 in-reach flee turns. adv swings a lot turn to turn (0.74 -> 1.72 -> 1.28 -> 0.42).
- 15 of 68 deaths began outside reach with adv < 0.8 and no fight: 7 against a single visible enemy (outmatch needs 2), the rest fled late.
- ~30 deaths began already in reach (the enemy appeared inside reach: bushes / vision): no early rule can see those.

- Death categories vs `_eA` (`death_ctx.mjs`, A and B files): `_rm` 508 deaths (C&I 260), `_sv1` 467 (C&I 244): the non-pair
  deaths fell 248 -> 213 (-14%), the pair barely moved.
- Rejected: `alert_radius` 8 (more deaths: the avoid zone blocks routes), `threat_score_memory` 20 (neutral, more deaths vs `_rm`).

## 56-map pool (112 games per cell; win % all maps (official 17); deaths ours-theirs)
| Bot | vs `_rm` | vs `_ST` | vs `_eA` | vs `_eB` |
|---|---|---|---|---|
| `_rm` | - | 54.5 (52.9) 1241-1053 | 57.1 (58.8) 1404-1604 | 68.8 (73.5) 1060-1399 |
| `_svA` | **60.7 (64.7) 893-1240** | 50.9 (44.1) 1017-1082 | 61.6 (70.6) 1075-1580 | 76.8 (88.2) 662-1504 |
| `_svC` | **59.8 (61.8) 862-1292** | 53.6 (52.9) 1016-1070 | 59.8 (70.6) 1223-1614 | 73.2 (82.4) 696-1492 |
- Our deaths fall 23-38% against every opponent (vs `_eA` 1404 -> 1075, vs `_eB` 1060 -> 662, vs `_ST` 1241 -> 1016) and gems rise
  (vs `_rm` 103k-91k): farming does not collapse.
- Cassi & Issac vs `_eA` (official 17, pair_deaths.mjs): `_rm` ~3.8 pair deaths per game, `_sv1` 3.74, `_svA` 2.88; gems lost per pair
  death 13.1 (`_sv1`) -> 5.1 (`_svA`); C&I body-rounds dead 25.1% -> 19.2%.
