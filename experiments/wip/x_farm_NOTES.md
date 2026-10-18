# x_farm: farming throughput (agent `farm`, session 6)

Baseline `bots/_rm` (read-only). Bot copy `bots/_x_farm`. Patch: `experiments/wip/x_farm.patch` (`cd bots && diff -ruN _rm/src _x_farm/src`).
Pace = round at which our team banks 1000 gems vs `idle` (mean of both sides; a failed game counts 2000), 17 official maps (`maps/comp`).

## Status: work in progress (notes kept current)

## Measurements
- `_rm` unopposed pace, 17 official maps: **579.0** (ambush 708, collision 583, contest 1074, corners 394, eight 426, elkring 465, expanse 615,
  fragment 581, interlock 558, lanes 489, monolith 451, packs 393, pilgrimage 891, rows 421, rushbait-v2 640, stampede 771, swirl 379).
- `_rm` + the session-4 pace patch (`bank_first=0`, `obj_min_hp` 4500, `obj_share` 0.7, `obj_max_groups` 8): 579.9 (pilgrimage 841, rushbait-v2 678,
  ambush 707: the objective mode now fires on ambush but its pace did not move on `_rm`). Neutral on its own here.
- Ladder (17 games of `legend_st`, `tools/analysis/ladder_econ.mjs --bodies`) vs our own unopposed games:
  - rows (no deaths): the enemy clears each 3-wolf pack (4,050 HP, 60 dps) with 3-5 bodies in ~11 rounds (r10-r21), one collector stays on the tiles,
    the helpers walk to the next pack before the last wolf dies (`tools/farm/pack_watch.mjs`). Our bodies go one per pack: pack (31,4) took r22-r73
    (Issac alone 900 -> 200 HP, home; Cassi alone; then Ren). Our Varg (splash: 3x on a vertical pack) flipped g4/g2/g0 for 40 rounds, then shared g4
    with Issac 47 rounds and went home at 400 HP with nothing; first Varg capture r320.
  - pilgrimage / ambush: every heavy group (ambush elk groups 4,750-5,800 HP, 80-120 dps) scores -1 for a single body (cannot clear in max_trips) and
    nobody claims it, so nobody joins: first gem capture r128 (ambush), bodies walk 60 rounds to far groups and turn back.
  - unknown-group cliff: `group_score` discounts an enemy-half group unseen for 60 rounds by 0.75; groups start unseen, so at r61-66 every body walking to
    one switched (pilgrimage: Ryth and Varg walked r20-r62/78 to the enemy-half 68-gem group, then turned back).
  - enemy banks rarely (pilgrimage: Ren banked 136 and 160 at once, Issac 68 gems 80 rounds after the capture) and walks its bag along; we bank each bag.
- Target switches on the 17 official maps (`_xt_farm` trace, `tools/farm/sw_why.mjs`): respawning after an ally/us cleared it 1,529 switches; rescored
  lower (still valid) 2,519; reward left to a lower-index claimer 418; join refused (claimed, not heavy or full) 319.

## Changes in `_x_farm` (all switches in `params.h`)
- The session-4 pace patch (`x_pace.patch`): `bank_first=0`, `obj_min_hp` 4500, `obj_share` 0.7, new `obj_max_groups` 8, `SW` trace line.
- `no_split` 1: a reward with a visible ally standing on its tiles is left to that ally (both on it: lower index keeps it). Rows unopposed: splits 6 -> 0.
- `unknown_keep` 1: the 60-round unseen discount does not hit the current target (2: never-seen groups are discounted from round 0 instead).
- `obj_focus` 1: on objective maps the team plan only applies to the objective group claimed by the lowest-index body.
- Trace only (`LEGEND_TRACE`): `SW ... why= hit= bag=` (why the old target scored <= 0, attacks on it, bag).

## Results so far (unopposed pace, 17 official maps, mean of 2 sides)
| Build | pace | notes |
|---|---|---|
| `_rm` | 579.0 | |
| + pace patch (`_c_pace`) | 579.9 | |
| + `no_split` + `unknown_keep` (`_fb1`) | 562.3 | ambush 609, pilgrimage 785, swirl 327, fragment 551 |
| `_fb1` without `no_split` / without `unknown_keep` | 579.9 / 575.8 | each one carries part of it |
| `_fb1` + `max_join` 2 / 3 | 555.0 / 549.4 | rows 389-398, monolith 417-431, elkring 438 |
| `_fb1` + `pair_plans` 1 | 564.2 | no gain |
| + `obj_focus` (`_fb2`) | **559.0** | ambush 609 -> 552 |
| `_fb2` + `max_join` 3 | 544.4 | |
- Head-to-head (56 maps, 112 games): `_c_pace` vs `_rm` 54.5 (official 55.9), deaths 1196-1206. **`_fb2` vs `_rm` 48.2 (official 44.1), deaths 1255-1101**:
  the pace gain does not carry over; single-feature runs to find the culprit are below.

## Tools (new files, agent farm)
- `tools/farm/pack_watch.mjs FILE X,Y FROM TO [R]`: per round, health of the pack at (X,Y) and the champions near it (both teams).
- `tools/farm/cycle.mjs FILE TEAM [TO]`: per body, captures / banks / recalls / shops / deaths in order.
- `tools/farm/out.mjs FILE`: our team's stdout from a replay (trace builds).
- `tools/farm/sw_why.mjs FILE...`: target switches by cause (needs the `SW ... why= hit= bag=` trace line of `_x_farm` LEGEND_TRACE builds).
