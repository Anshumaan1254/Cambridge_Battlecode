# x_cast: cast before walking (agent `cast`, session 3)

Base `bots/_k1`; copy `bots/_x_cast`; patch `experiments/wip/x_cast.patch` (against `bots/_k1/src`). Switches in `params.h`:
`cast_en_route` (default 1) and `cast_near_target` (default 1).

## Measured (before)
- `tools/analysis/spell_usage.mjs` on 34 comp-map games per opponent (`_k1` vs `_v6`, `_r2`). Stellar casts per game: us 47.5 / 49.4,
  the opponent's (same code family) 40.3 / 43.0. Our local casts are not low: the ladder gap (34.7 vs 59.1) comes from real opponents.
- "Camp within 4, spell ready, no enemy within 9, body walked": 92 turns per game for Stellar (each slot), 100 camp-safe waste turns.
- SPELL_TRACE line `WM` (3 comp games, Stellar + Cassi, spell ready and a live camp within 4 of the start tile, no cast): 444 turns.
  Of these 47% were camps of groups other than the task group (walked past), 18% the task group's camp exactly at 4, 5% in range 3.
- Task group at exactly 4: NOT changed on purpose. A ranged body must walk one step (no attack that turn) before it can hit at 3, and
  at 3 it casts both spells and attacks; casting at 4 first delays that by a turn for a cooldown gain of one round. Equal at best.
- Fights: `engage()` already casts before walking when the target is within 4. The only gap: target farther than 4 while another enemy
  stands within spell range (`cast_near_target`). The post-move `SP` trace lines (nd = distance after the step) mislead here.

## Changes
- `cast_en_route()` at the top of `farm()` (not while capturing): ready damage spell or non-stun area spell, a live visible camp of
  one of our groups (not the task group, not a monolith) exactly 4..range away, no other live camp of that group within 3, no enemy
  seen within `hold_spell_dist` or visible within 9: cast through `spells_on_camp()` and hold (damage spells cannot share a turn
  with a walk). Camps hit at 3 and never heal, so the damage waits for the next body that farms the group.
- `cast_on_nearer()` at the start of `engage()`: target farther than 4 and another visible enemy (not on its spawn) within 4:
  cast cc/dmg/aoe on that one instead of walking.
- SPELL_TRACE build prints `WM` lines (see above); no change to a normal build.

## Results (56 maps = 112 games per cell, `--release`, both sides; comp = the 17 official maps, 34 games)
| Bot | vs `_k1` | `_r2` | `_v6` | `_devci` | deaths us-them vs `_k1` |
|---|---|---|---|---|---|
| `_k1` | | 67.0 | 86.6 | 83.9 | |
| `_x_cast` (both switches) | **54.5** (comp 64.7) | **75.9** (comp 76.5) | 84.8 (comp 82.4) | **92.0** (comp 94.1) | 1131-1348 |
| `_x_castA` (en route only) | 52.7 (comp 55.9) | 76.8 (comp 70.6) | | | 1234-1301 |
| `_x_castB` (near target only) | 52.7 (comp 52.9) | 66.1 (comp 64.7) | | | 1236-1409 |
| `_x_castD` (`cast_en_route=2`: also stuns that do damage) | 44.6 (comp 50.0) | 80.0 on 50 games | | | worse head-to-head: stuns are wasted on camps |
- Mean over `_r2`, `_v6`, `_devci`: `_k1` 79.2, `_x_cast` 84.2 (+5.0). Comp-only vs `_r2`/`_v6`/`_devci`: 76.5 / 82.4 / 94.1.
- Casts per game on comp maps (34 games per opponent, `spell_usage.mjs`): Stellar 47.5 -> 58.9 (vs `_v6`), 49.4 -> 59.2 (vs `_r2`);
  Cassi 61.4 -> 64.5, 59.2 -> 63.1; Ren/Ryth unchanged. Stellar camp-safe waste turns per game 100 -> 51.
- 0 faults in 560+ games. Lost turns on `maps/gen16_98x99_V_c5.map26a` vs `_v6`: 19 for both `_k1` and `_x_cast` (unchanged).
- `cast_near_target` alone is neutral (66.1 vs `_r2`, 67.0 for `_k1`); it fires rarely. Kept on (measured inside the combined row).
  The en-route cast carries the gain. Noise is about +-5 points per cell.

## Rejected
- Stuns en route (`cast_en_route=2`): head-to-head 44.6; a Ren/Ryth/Prism/Tavi stun is worth more kept for a fight.
- Casting at 4 on the task group before walking in (see above): not built.

## Reproduce
`SRC=bots/_k1 tools/variant.sh _x_cast`, apply the patch, `cambc build`. Panels: `/tmp/cast/panel.sh _x_cast _k1 _r2 _v6 _devci`;
casts: `node tools/analysis/spell_usage.mjs DIR`; trace: `SRC=bots/_x_cast tools/variant.sh _x_cast_t --define "SPELL_TRACE 1"`,
`cambc run`, then `unzip -p replay team-a.stdout | tr -d '\0' | grep -a '^WM'`.
