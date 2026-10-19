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

## Variants and results

(in progress)
