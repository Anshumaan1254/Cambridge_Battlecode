# x_zone: draft-time farming zones and camp circuits (session 13, agent zone)

Base: `bots/_ch2` (= shipped `legend_m14_commit`, hash 5f24a1979ddc). Copy: `bots/_x_zone` (patch `experiments/wip/x_zone.patch`).
Rebuild: `SRC=bots/_ch2 tools/variant.sh _x_zone && (cd bots/_x_zone && patch -p1 --no-backup-if-mismatch < ../../experiments/wip/x_zone.patch)`
(the patch adds `src/zone.h`, `src/zone.cpp`), then `SRC=bots/_x_zone tools/variant.sh NAME switch=value ...`.

## What is built (all behind `params.h` switches, default off = `_ch2`'s play)

- `draft.cpp zone_draft()` (only with `zone_plan` 1): on the first draft turn (1M fuel) the walking distance between every pair of
  camp groups on our side (`d_home <= d_away + zone_band`, no monoliths, up to the 44 nearest our spawn) with one distance field per
  group (stops at 300k fuel left; remaining pairs Chebyshev x 1.3). Written to draft memory: magic 0xB9, version 1, M, groups, W, H,
  M group ids, upper triangle (uint8 steps, 255 unreachable).
- `zone.cpp ZonePlan::build()` (each body, in `Brain::init`): units = our picks (Cassi & Issac one unit, two bodies); items = measured
  groups minus objective groups and monoliths; zones = weighted k-medoids on walking distance (weight = value / (respawn + 6 +
  hp/150)); units to zones by brute force over permutations maximising the sum of value / (base-stat kill + 6 + 25 x heal trips).
- `group_score`: own zone x `zone_own`, another living pick's zone x `zone_other` (not on rewards); own zone respawn window
  `zone_wait` (max_wait elsewhere); `score_cap` stays an upper bound. `zone_idle` 1: with nothing to farm wait at our own zone's
  next respawn.

## Baseline numbers (_ch2)

Unopposed pace (ledger vs idle, mean of both sides): official 17 **502.7**, gen2 (24) **373.0**, pad17 (16) **502.5**.

## Variants and results (unopposed pace vs idle, mean of both sides; lower is better)

| variant | switches | official 17 | gen2 24 | pad17 16 |
|---|---|---|---|---|
| `_ch2` | baseline | 502.7 | 373.0 | 502.5 |
| `_z0` | zone_plan 0 (control, older source) | 502.7 (same per map) | | |
| `_z1` | plan 1, k-medoids on walking distance, own 1.3, other 0.6 | 520.6 | | |
| `_z2` | `_z1` + zone_idle 1, zone_wait 30 | 528.1 | | |
| `_z3` | sectors (shape 1), balance 0.25, solo_trips 1.5, help 1, own 1.3 / other 0.6 | 499.4 | 377.5 | 497.3 |
| `_z4` | `_z3` with shape 0 (walking-distance clusters) | 512.4 | | |
| `_z5` | `_z3` with own 1.15 / other 0.85 | 497.1 | 380.0 | 502.7 |
| `_z6` | `_z3` + zone_idle 1, zone_wait 30 | 503.3 | | |
| `_z7` | `_z3` with own 1.2 / other 1.0 (bonus only) | 510.6 | (16 maps) | |
| `_z8` | `_z5` + zone_skip_obj 1 | 498.4 | | |

Findings so far:
- `_z1` lost 18 rounds: on swirl (heavy packs that need 2-3 bodies) the penalty on other zones pushed every non-owner onto the
  unzoned heavy packs (3 bodies on one 4,550-HP pack for 44 rounds; Varg never captured before r272); on expanse (3 picks) the
  walking-distance k-medoids gave Varg and Stellar the far corners (d 53-66). Fixes: sectors around spawn (`zone_shape` 1),
  groups the owner cannot clear alone stay unzoned (`zone_solo_trips`), no penalty on a group an ally already claims (`zone_help`),
  load balance (`zone_balance`).
- The penalty on other zones is what makes zones work (bonus only `_z7`: 510.6).
- Route stats on 6 traced unopposed maps (monolith, rows, lanes, pilgrimage, interlock, fragment), `_ch2` -> `_z3`: walking steps
  9,301 -> 8,831, crossing paths 38.1% -> 22.8% of camp walking, walks abandoned before arrival 43.7% -> 35.1%, duplicate walks 42.2 ->
  40.0%, mean win round 496 -> 474. Respawn revisit gap unopposed barely changes (monolith own groups 12.0 -> 12.1 rounds; lanes 18.9 ->
  15.1): unopposed the gap is already short; the ladder's 26.5 is mostly contact.
- Monolith-map banking: the nearest altar is ~27 steps from spawn; bodies capture-recall home and walk 25-30 rounds per bank
  (bank = 16% of body time). Not a zone matter (banking thresholds), noted for later.
