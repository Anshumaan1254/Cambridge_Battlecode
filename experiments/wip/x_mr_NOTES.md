# x_mr: maths + route prototypes, review and panels (agent `mr`, 2026-10-17)

Status: IN PROGRESS (this file is updated as results come in).

## What was built
- `bots/_x_math` = current legend (`_L0`, commit 25bed8d) + `experiments/wip/x_math.patch` (applied cleanly, offsets only).
- `bots/_x_route` = current legend + `experiments/wip/x_route.patch`. Hunks 2-3 of `brain.cpp` (`build_danger()`) and hunk 2 of
  `brain.h` conflicted with the spells patch; merged by hand, keeping both `enemy_near_d` (spells) and `enemy_near_field` (route).
- `bots/_x_mr` = `_x_route` + the `_x_math` diff (applied cleanly with offsets).
- Frozen copies for benchmarks (same source): `_x_mr_m0` = `_x_math`, `_x_mr_r0` = `_x_route`.
- All build; trace builds (`XM_TRACE`, `LEGEND_TRACE`) also compile. No `.orig`/`.rej` files.

## Review findings
(see below, filled in as the review goes)

## Panels (45 maps, both sides, 90 games per line)
(filled in as they finish)
