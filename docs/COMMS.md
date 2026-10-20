# GOD shared state: the 8-byte shared memory and the 1,024-byte draft memory

Source of truth: `bots/god/src/comms.h/.cpp` (shared memory), `bots/god/src/dmplan.h/.cpp` (draft memory). Every field below that
belongs to a switched-off feature is never written while the switch is off; with all new switches off the 8 bytes are bit-for-bit
the GOD v8 bytes after every turn of every body (checked with `SM_TRACE` dumps, `tools/actiondiff.py`, docs/TESTING.md §1).

Teams alternate turns and the turns inside a team are sequential, so a body's read-modify-write of a byte cannot race with an ally.
Everything a body writes is visible to the allies that act after it in the same round, and to everyone in the next round.

## 1. Shared memory (8 bytes, whole match)

| Byte | Bits 0-5 | Bit 6 | Bit 7 |
|---|---|---|---|
| 0 | claim of body 0 | team bag sum, bit 0 | stance bit 0 / plan id bit 0 (leader) |
| 1 | claim of body 1 | team bag sum, bit 1 | stance bit 1 / plan id bit 1 (leader) |
| 2 | claim of body 2 | team bag sum, bit 2 | plan id bit 2 (leader; `opp_model`) / alert toggle (`alert_refresh`, off) |
| 3 | claim of body 3 | team bag sum, bit 3 | invasion counter bit 0 (`opp_model`) |
| 4 | claim of body 4 | team bag sum, bit 4 | invasion counter bit 1 (`opp_model`) |
| 5 | claim of body 5 | team bag sum, bit 5 | invasion counter bit 2 (`opp_model`) |
| 6-7 | alert: bits 0-13 tile index (y x width + x), bits 14-15 kind | | |

**Claims** (bits 0-5, v8 unchanged): claimed group id + 1, 0 = none. With the team bag sum on (`team_bank`, maps with at most 62 groups;
the official maximum is 46) claims use 6 bits; on a map with more than 62 groups claims use bits 0-6 and the bag sum is off.
`comms_fight` (v8 switch, off): value 63 = "fighting this turn, no claim" (read as no claim by every claim reader).

**Team bag sum** (bit 6, v8 unchanged): 6-bit sum over bodies of min(10, bag / 10); each body adds the change of its own term, so the
sum is exact.

**Stance / plan id** (bit 7 of bytes 0-2). Without the opponent model: the stance learner's leader (body 0) writes the 2-bit stance in
bytes 0-1; byte 2's bit 7 stays 0. With `opp_model` 1 the leader writes a 3-bit plan id instead:

| Plan id | Meaning | Stance used |
|---|---|---|
| 0, 1, 2 | no archetype detected (or FARMER for 2): the stance learner's SPREAD / GROUPED / PUSH | itself |
| 3 | counter INVADER (or the fitted model's "raider") | GROUPED + preset |
| 4 | counter DEATHBALL | GROUPED + preset |
| 5 | counter OBJECTIVE | SPREAD + preset |
| 6 | counter ALTAR denier | SPREAD + preset |
| 7 | counter AMBUSH | GROUPED + preset |

Ids 0-2 equal the stance values bit for bit, so a model that detects nothing writes exactly the v8 bytes. Choice vs the prompt's
proposal: the proposal replaced the stance with the plan id; this encoding keeps the stance learner whenever no counter plan is active
(the learner alone is worth +3 of 84 games: `learn_stance` 0 measured -3). While a counter plan is active the learner's windows are not
scored (`Learner::frozen`). `alert_refresh` must stay 0 with `opp_model` 1 (both use byte 2's bit 7; the code disables the toggle).

**Invasion counter** (bit 7 of bytes 3-5, `opp_model`): 3 bits, saturating at 7. Each living body adds 1 once per `om_window` (20)
rounds, the first turn in that window it sees an enemy on our half (nearer our spawn than theirs by walking distance, not on their
spawn). The leader reads it at its first turn of the next window, uses it as that window's `inv` signal and resets it to 0. Known
edge: a body that acts before the leader in the window's first round and adds 1 is wiped by the reset (one count lost); dead bodies
do not count; with 6 bodies the counter cannot saturate.

**Alert slot** (bytes 6-7, v8 layout): kind 0 none, 1 DANGER, 2 RALLY, 3 OPPORTUNITY. Uses of kind 1:
- ESCORT (v8 `escort_bag`): a carrier with a big bag at a hot altar posts kind 1 at the altar tile. An altar tile is a wall, no enemy can
  stand there, so a kind-1 alert on an altar tile is an escort call.
- Sightings (`om_sight`): a body that sees an enemy on our half posts kind 1 at that enemy (the one nearest our spawn) when the slot holds
  no RALLY / OPPORTUNITY / ESCORT younger than 6 rounds, and not again within 2 rounds and 3 tiles of the current sighting. Readers treat
  a sighting as a scoring cost only (groups within `om_sight_r` 5 of a sighting younger than `om_sight_age` 8 cost `om_sight_cost` 25
  rounds), never as a routing wall (the old alert zone, radius 8 in routing, measured worse).
- Priority (`alert_prio`, v8): a RALLY never replaces a fresh OPPORTUNITY or ESCORT; sightings never replace any of the three.

## 2. Draft memory (1,024 bytes, written in the draft, read-only in the game) - `dm_plan`

Written on every draft turn after our pick (the last write wins; the first draft turn, with 10x fuel, also computes the map part once).
The game reads the snapshot in `Brain::init()`. The plan is accepted only if every check below passes; otherwise `draft_plan().ok` is
false and every user (ward coordination, the opponent model's prior) falls back to its in-game logic.

| Offset | Size | Field |
|---|---|---|
| 0 | 1 | magic `0xC8` |
| 1 | 1 | version `1` |
| 2 | 1 | team size (champions per team) |
| 3 | 1 | map width |
| 4 | 1 | map height |
| 5 | 1 | G = number of camp groups (`bc::map::camp_groups()`; group id = index in that list, as in `World`) |
| 6 | 1 | map flags: 1 objective (one heavy multi-camp gem group on our half), 2 lone monoliths only, 4 no altar reachable on foot, 8 gold-heavy (gold / gem reward-rate ratio > 8), 16 islands (groups on our half unreachable on foot) |
| 7 | 1 + 5 | our picks so far: count, then up to 5 `champion_draft` values (255 = empty) |
| 13 | 1 + 5 | enemy picks seen so far (picks are simultaneous: the enemy's last pick may be missing) |
| 19 | 1 + 8 | heavy groups (>= `om_heavy` gems) and monoliths on our half, nearest our spawn first: count, ids |
| 28 | 1 + 5 | anchor ranking: our pick slots, best anchor first (Vesper, Marcella, Prism, then the lowest base health; C&I counts as Cassi) |
| 34 | G | zone owner per group: pick slot (0-4) of the angular sector of our half the group lies in, 255 = not ours (informational; zone farming lost in session 13) |
| 34+G | 1 + 5N | ward spots: count N <= 32, then per spot x, y, responsible pick slot, kind (0 bush by a group, 1 bush by an altar, 2 approach of an altar, 3 approach of a heavy / midline group), watched group id (255 none) |
| end | 1 | checksum: sum of all previous bytes mod 256 |

Size: 34 + G + 1 + 5N + 1 bytes, at most 34 + 255 + 1 + 160 + 1 = 451. Checks on read: buffer not empty, magic, version, structure
lengths, checksum, then map width / height and group count equal to this game's. Pick slots map to bodies by champion type in the
game (`Brain::my_slot`; Cassi and Issac share the slot of their pick).
