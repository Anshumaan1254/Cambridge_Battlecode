# x_side: opening fights and side asymmetry on the official maps (agent `side`, session 4)

Base: `bots/_ST` (= shipped `legend_st`). Copy: `bots/_x_side` (+ variants `_x_side_cf`, `_x_side_wg`).
Patch: `experiments/wip/x_side.patch` (`cd bots && diff -ruN _ST/src _x_side/src`). Outputs: `/tmp/side/` (local).
Work in progress: this file is updated as results come in.

## Baseline (`_ST`, 17 official maps, both sides, 34 games per opponent)
- vs `_v6` 91.2, `_es2` 64.7, `_L0` 64.7, `_r2` 67.6 (mean of es2/L0/r2: 65.7).
- Worst official maps (8 games each vs the 4): **eight 2/8**, monolith 3/8 (side A 1/4), rows side B 1/4 (pure race,
  0 deaths), rushbait-v2 side A 1/4, collision side B 2/4, elkring side B 2/4.
- Deaths per game (`tools/analysis/side_deaths.mjs`): eight 35-28 (us-them, both sides), contest 30-65 (we still win 7/8),
  collision B 13.8-16.5 vs A 3.3-19.8.

## Causes found
- **eight** (one altar, centre): in all 6 losses our team woke a heavy camp beside the enemy's path at r16-17 (side A:
  the top wolves 18,10/18,11; side B: the elk at 27,3) while their 4-5 bodies were 6-9 tiles away. They arrived at full
  health, the awake camp kept hitting our bodies, C&I died at r24-27 (4v5), then Ren, Varg, Ryth by r40.
  `combat()` never counted camp damage: a team tanking a camp judged an even fight against fresh arrivals as even.
- **collision B**: the opening is a C&I duel in the centre (the opponent's Issac rushes the middle at r10-14). As A our
  Stellar walks to the centre and helps (their C&I die r30); as B our Stellar and Ren stay on the bottom-left wolves and our
  C&I die at r33. Same pattern for the opponents (whoever is B loses its C&I against `_r2`/`_L0`).

## Changes (switches in params.h)
- `camp_in_fight` (1): in `combat()`, every awake camp within 3 of a body hits the nearest champion (ties counted against
  us): its strength is added to the enemy DPS (and to `incoming` when it is us) or to ours when an enemy is nearest.
- `wake_guard` (1): `farm_group()` does not wake a sleeping, harmful group while enemies seen in the last
  `threat_memory` rounds stand within `wake_guard_d` 9 of it (or of us), unless we kill it within `wake_guard_kill` 3
  rounds or our side (health after the camp's hits) beats them by `wake_guard_adv` 1.5; it holds at range 4 for at most
  `wake_guard_max` 16 rounds per group.

## Results (comp = 17 official maps, 34 games per cell)
| Bot | vs `_ST` | `_es2` | `_L0` | `_r2` | mean of 3 | eight (8 games) |
|---|---|---|---|---|---|---|
| `_ST` | - | 64.7 | 64.7 | 67.6 | 65.7 | 2/8 (incl. `_v6`) |
| `_x_side` (both) | 52.9 | 70.6 | 67.6 | 76.5 | 71.6 | 7/8 |
| `_x_side_cf` (camp_in_fight only) | 44.1 | 64.7 | 76.5 | 82.4 | 74.5 | 7/8 |
| `_x_side_wg` (wake_guard only) | 44.1 | 61.8 | 58.8 | 79.4 | 66.7 | 4/8 |

## 56-map pool (112 games per cell; `_ST` reference: `_L0` 70.5, `_es2` 59.8, `_r2` 74.1, `_v6` 86.6-88.4, mean ~73)
| Bot | vs `_ST` | `_L0` | `_es2` | `_r2` | `_v6` | mean of 4 |
|---|---|---|---|---|---|---|
| `_x_side` (both) | 47.3 (comp 52.9) | 71.4 | 64.3 | 80.4 | 92.0 | 77.0 |
| `_x_side_cf` | 45.5 (comp 44.1) | 72.3 | 61.6 | 83.9 | 91.1 | 77.2 |
- Panel +4 (all of it from `camp_in_fight`), head-to-head vs `_ST` slightly under 50 (noise range, deaths equal 1120-1115).
- `wake_guard_open` 80 (opening guard against enemies not seen yet, arrival = their walk to the group - 4 + 1; never-seen
  enemies counted like our own bodies): comp `_ST` 52.9, `_es2` 67.6, `_L0` 64.7, `_r2` 85.3 (eight 7/8): same as without.
  Bug found on the way: never-seen enemies have max_hp 1 and str 0, so the first version never held.

## Split of camp_in_fight (the panel gain): only the enemy side counts
- `camp_in_fight` 2 (only camps hitting us, the defensive half): vs `_ST` **41.1** (comp 38.2), deaths 1202-1078.
- `camp_in_fight` 3 (only camps hitting an enemy add to our DPS, the offensive half: punish bodies tanking a camp):
  vs `_ST` **57.1** (comp 58.8), deaths 1007-1147; panel `_L0` 73.2, `_es2` 65.2, `_r2` 80.4, `_v6` 96.4 (mean 78.8,
  `_ST` ~73); comp `_L0` 73.5, `_es2` 73.5, `_r2` 79.4, `_v6` 100; held-out vs `_ST` 54.0 (100 games). 0 faults; gen16
  lost turns 18 per game (same as `_ST`).
- So the eight story (our team tanking a camp loses to fresh arrivals) is real, but the cure "count it and back off" loses
  more than it saves: bodies leave camps and rewards and get chased. Counting the enemy's camp damage makes us take the
  fights where *they* tank, which both wins those fights and wins eight (7/8 with or without the defensive half).
- `wake_guard` off is better: `_xs_off0` (camp_in_fight 3, wake_guard 0) vs `_ST` **56.2** (comp 61.8), vs `_xs_off`
  (same + wake_guard) 54.5. wake_guard also lost interlock side A vs `_ST` (710-1042) in every variant that had it.

- `_xs_off0` panel (56 maps): `_L0` 71.4, `_es2` 63.4, `_r2` 75.9, `_v6` 92.0 (mean 75.7, `_ST` ~73); comp `_L0` 70.6,
  `_es2` 73.5, `_r2` 67.6, `_v6` 91.2; held-out vs `_ST` 53.0. 0 faults. With wake_guard (`_xs_off`) the four panel cells
  were each 2-4 points higher (mean 78.8) while the direct match went 54.5 to the version without: unresolved, noise-level;
  the patch ships wake_guard off (simpler; switch kept).
- `camp_kill` (a camp's hit on the target this round counts toward `killable`): vs `_xs_off0` 50.9, vs `_ST` 56.2:
  neutral, not kept (code not in the patch).

## Side asymmetry (swapped maps, `/tmp/side/swapmaps`, `_ST` vs `_r2`, `_es2`, `_L0`, `_ST`)
- **collision is geometry, not the team letter**: the top spawn wins. Original: as A (top) 4/4, as B (bottom) 2/4; swapped:
  as A (bottom) 0/4, as B (top) 4/4, and the `_ST` mirror match is won by the top team on both versions.
  Our bodies' paths differ from round 1 (step tie-breaks are not mirror-symmetric), and the camp-tank / hurt / recall
  pattern that follows decides the first altar duel: in the mirror the bottom Ren banks 22 gems at the midline altar at
  r32, duels their Ren there, our Stellar and Issac (hurt from tanking wolves) recall home at r40, their three come, Ren
  dies 1v4 (r45, stunned in place 4 rounds while fleeing), Cassi walks the next 22 bag to the same altar and dies (r54).
- **monolith favours team B** (team letter): A lost 3/4 on both the original and the swapped map; races decided by
  ~150 gems at r470-650 with few deaths (both monoliths are exactly as far from both spawns).
- rows (pure race, 0 deaths) and eight: mixed, no consistent side.

## Tools
- `tools/analysis/side_deaths.mjs [--maps a,b] [--list] DIR...`: per game result, deaths, opening kills (r<=150), first
  death, our deaths by cause (bag, near altar, enemy half, alone, outnumbered); per map and side summary.
- `tools/mapgen/swap_sides.mjs IN OUT`: side-swapped copy of a map (team A spawns where B did).
