# x_f2 (agent fight2, session 9): area reach 5, area casts from 5, openers

Baseline `bots/_xp4` (= shipped `legend_m6`). Copy `bots/_x_f2` = `_xp4` + `x_f2.patch`; every switch default 0 plays
identically to `_xp4` (checked: `_x_f2` vs `_px9` on the 34 official games, every stats JSON byte-identical to `_xp4` vs `_px9`).
Evidence: `docs/strategy_v2/08_TOP3_VS_TOP3.md` section 2 (spells 72-82% of champion damage between top teams, 20-28% of it
at distance 5; we deal 3 and take 12 per body-round at distance 5 against them; the opener wins the first 3 rounds 391 to 58).

## Switches (params.h, block "Fight micro v2")
- `aoe_reach5` (F1): enemy area spells (ready, or cooldown unknown while unseen) reach `aoe_range + aoe_radius` = 5 (Ryth's area
  stun, Stellar's and Prism's areas), not 4: `build_danger` (danger map, routes), `combat()`'s `reach_of` (in-reach weight,
  incoming, burst_exit, holds), `engage_angle`, the tribute stun check in `handle_channel`. 2: also walk-compatible spells
  (Cassi's stun) reach range + 1. Helper `enemy_spell_reach()` in brain.cpp.
- `aoe_cast5` (F2): our area spells (Stellar, Prism; Ryth already did) aim at a tile within cast range whose radius catches
  the target, most enemies first (`cast_area_stun_at` generalised: the Marcella filter only for stuns): engage() ranged branch
  casts the area at d = 5 instead of stepping in, the area fallback at d <= 4 aims the same way, `cast_on_nearer` looks to 5,
  px targeting counts the area at 5, `killable` counts the area at 5. Bit 2: at d <= 4 an area that catches 2+ enemies is
  cast before the single-target spell.
- `open_first` (F3, bits): 1 = after a fight step, a walk-compatible spell that now reaches the target is cast (Cassi: walk
  5 -> 4 + stun); 2 = ranged body in a proactive fight with an opener ready that cannot hit this turn: when the next step
  enters an enemy's next-turn reach (with F1: 5 for area casters), hold at the edge for at most `open_hold` (2) rounds per fight.

## Recipes
- `_x_f2`: `SRC=bots/_xp4 tools/variant.sh _x_f2 && (cd bots/_x_f2 && patch -p1 < ../../experiments/wip/x_f2.patch)`
- variants: `SRC=bots/_x_f2 tools/variant.sh NAME key=val ...`
  `_f2a` aoe_reach5=1; `_f2b` aoe_cast5=1; `_f2c` aoe_cast5=3; `_f2d` open_first=1; `_f2e` open_first=2;
  `_f2f` aoe_reach5=1 aoe_cast5=1 open_first=1.
- proxy with reach-5 casts: `_f2p` = `_px9` + `x_f2.patch` (one hunk, the engage_angle loop, does not apply: `_px9` has no
  engage_angle; ignore it), then `SRC=bots/_f2p tools/variant.sh NAME aoe_cast5=...`.

## Results (88 distinct games / official 34 / deaths ours-theirs)

(in progress)
