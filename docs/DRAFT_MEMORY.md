# Draft memory: the final layout (version 2)

This is the specification for the user's new bot (TEAMPLAN.md 8). The mapintel library implements it; the handoff prompt for that is
given in chat at the end of the team-play session.

**Status (Oct 24, end of the team-play session)**:
- The layout below is final for version 2. The other Claude implements it in the mapintel library.
- **One block has a working prototype**: OWN version 1, written by the GOD v10 test copy at offset 8 (`tools/teamplan/v10_adapter.patch`).
  - Its draft fuel is measured (section 7).
  - Its effect is measured on v10: TEAMPLAN.md 11 (SIMULATED (v10)).
- **mapintel's block** (version 1, at 512) is in use and stays where it is.

**Status (Oct 24, 18:55 UTC): implemented and engine-tested in the mapintel library** (MAPAnalysis.md 7.2, 18:40 and 18:55):
- Code: `tools/mapintel/cpp/mapintel/dmem2.h` (the image, the TOC, the reader, the guard, every block builder, the in-game OWN recompute)
  and `hazards.h` (NAV), with the Python twins `tools/mapintel/dmem2.py` and `hazards.py`; how a draft writes the image and a champion
  reads it: `tools/mapintel/README.md`; the reference draft integration is the test bot `tools/mapintel/cpp/test2/main.cpp`.
- Every test of section 8 passes (`python3 -I tools/mapintel/test_dmem2.py`): 40 official + 12 perturbed (unknown) maps x 2 teams x 3
  rosters, 2,108 blocks and 264 whole images bit-equal to the twins. Every fuel number below is measured by it on the worst map.
- Where the implementation fixed a detail the layout left open, the section says so ("implementation:").

## 1. The medium (facts; sources in TEAMPLAN.md section 2)

**Size and access**:
- 1,024 bytes, written only by the draft bot and only during the draft; frozen afterwards (SDK error 20).
- The enemy cannot read it.
- **A write always starts at offset 0.** A shorter write leaves the later bytes unchanged, and the last write wins (checked in the
  engine by `tools/mapintel/test_library.py`).
- **A champion reads one snapshot of all 1,024 bytes when its process starts.** Later writes are not seen by a process that is
  already running.

**The draft bot**:
- It keeps its RAM between draft turns.
- Its own snapshot (`cambc::draft_memory`) does not change when it writes. Keep one image in RAM, edit that image, and submit it whole.

**Fuel**: 1,000,000 on the first draft turn, 100,000 on every later draft turn.

**Picks**:
- Both teams pick at the same time, one pick per round. Our pick in round k sees the enemy's picks of rounds 1..k-1, so **our draft
  never sees the enemy's last pick**.
- `current_draft(ally)` does not include this turn's pick.
- **A draft bot that crashes or runs out of fuel before it picks gets random picks.** In session 14, draft turns that ran out lost
  the remaining picks to random draws (AGENTS.md). So **pick first, then compute, then write**, and never let a turn run out after
  the pick either (the fuel guard, section 7).

## 2. What goes in

- **Static knowledge about a map goes in the binary**: the catalog table, the model weights.
- **The draft memory carries only what the draft can produce and a champion cannot cheaply derive**:
  1. **results too expensive for a champion's turn**: the ownership plan costs up to 56k fuel per call (51 groups, 5 bodies, with
     the next owners), and a camp-group list with a spawn field 54-94k (both measured, `tools/teamplan/test_teamplan.py`);
  2. **decisions that depend on this game**: our roster, the enemy's visible picks, our side;
  3. **one consistent team decision**: every body reads the same bytes, so nothing has to be agreed in the game.
- **Not stored**, because every body derives it cheaply and identically at startup:
  - the kits: all 13 designs cost 20k fuel (35.2k measured in the draft with the danger features of 5.4 / 5.6; a champion needs only
    its roster's, ~2.7k a type: `dmem2.h kits_of_types`);
  - the team side: `cambc::detail::sdk_my_team()`.
- **Data is stored in the form a champion reads it**: fixed offsets and direct indexing, no decode loops. Tiles are `y * W + x` as
  uint16 little-endian.

## 3. Byte map

| Offset | Size | Block | Content |
|---|---|---|---|
| 0-3 | 4 | HDR | byte 0 magic 0x54; byte 1 layout version 2; byte 2 flags (bit 0 final: written after our last pick; bit 1 minimal: only the turn-1 blocks); byte 3 the sum of bytes 4-99 mod 256 |
| 4-99 | 96 | TOC | 12 entries x 8 bytes: 10 used, 2 spare for later patches (section 4) |
| 100-115 | 16 | TEAM | team decisions (section 5.1) |
| 116-179 | 64 | OWN | one byte per group (section 5.2) |
| 180-275 | 96 | BODY | 6 body slots x 16 bytes (section 5.3) |
| 276-307 | 32 | CONT | contingencies (section 5.4) |
| 308-339 | 32 | CODE | the codebook the live bytes index into (section 5.5) |
| 340-355 | 16 | ENEMY | the enemy model from their picks (section 5.6) |
| 356-419 | 64 | NAV | static navigation hazards for unknown maps (section 5.7) |
| 420-435 | 16 | DEBUG | draft fuel per turn, builder version (section 5.8) |
| 436-511 | 76 | free | reserved for later patches |
| 512-863 | 352 | MAPINTEL | mapintel's block, version 1, unchanged (`tools/mapintel/cpp/mapintel/dmem.h`): fingerprint, flags, archetype, per group the bank altar and both walks, 16 contested groups, 8 thresholds, plan 1, checksum |
| 864-999 | 136 | MAPINTEL-DL | mapintel's optional DL outputs: the opening model's ranking and per-slot next-target routes (section 5.9). No champion values: the step-7 values model is worse than the constant values (log loss 0.668 vs 0.622) |
| 1000-1023 | 24 | free | |

The total in use is 436 + 352 + 136 = 924 bytes, which leaves 100 free.

## 4. Header and table of contents

**TOC entry** (8 bytes):
- id (u8; ASCII letter: `T` TEAM, `O` OWN, `B` BODY, `C` CONT, `K` CODE, `E` ENEMY, `N` NAV, `D` DEBUG, `M` mapintel, `L` mapintel-DL);
- block version (u8);
- offset (u16 LE);
- length (u16 LE);
- checksum (u8: sum of the block's bytes mod 256);
- valid (u8: 1 = written and complete).

Unused entries are zero.

**Reader**:
1. Check HDR (magic, layout version, TOC sum).
2. For each block it uses, find the entry by id, then check the version it understands, the checksum and `valid`.
3. A missing or invalid block means fall back: compute it in the game, or use a default.
4. Never trust offsets outside 0-1023 or lengths past the end.

**Writer**:
- One 1,024-byte RAM image.
- Each draft turn:
  1. pick first;
  2. update the blocks this turn's fuel allows, under the guard of section 7;
  3. recompute their TOC entries and the HDR sum;
  4. submit the whole image.
- `final` is set on the write after our last pick.

## 5. Blocks

### 5.1 TEAM (16 bytes): the team-level decisions

| Byte | Content |
|---|---|
| 0 | plan id (the variant the team starts with: 0 = base) |
| 1 | number of OWN variants available (0 = only the base table) |
| 2 | tiebreak-prone map (bit 0, `tiebreak.h` / mapintel plan 4's mode); bits 1-2 the mapintel tiebreak mode copy |
| 3 | capture rule (`capture.h` capture_mode) |
| 4-9 | body types by slot, in ascending body type: the order of OWN, BODY and the live slots (section 6; 255 = none), so a body finds its slot without reading the roster. Written for the final roster on the last draft turn (cheap). |
| 10 | groups G covered by OWN |
| 11 | bodies covered by OWN: the roster size the OWN table was computed for. Below the roster size means recompute in the game (section 7) |
| 12-13 | implementation: the body types OWN was computed for (u16 bit mask; its slots are those types in ascending order) |
| 14-15 | reserved |

Implementation: byte 0 = 0 and byte 1 = 0 (no variants yet); byte 2 from mapintel plan 4's mode; byte 3 = `teamplan::Params::capture_mode`
(1, LEARNED). TEAM + CODE together cost 0.7k a write.

### 5.2 OWN (64 bytes): soft ownership, one byte per group (G <= 64; groups 64+ have no owner)

- **Low nibble: the owner slot** (15 = none; the library's `kNoOwner` 255 is stored as 15). Computed by `teamplan::assign_groups` (list
  scheduling; gem-free groups lean to front bodies) for the bodies picked so far.
- **High nibble: the next owner**, who takes the group while the owner is dead (15 = none). It is the runner-up body of the same
  scheduling step: `assign_groups`'s `runner_up` output, added for this layout, so it costs no extra call.
- **Fuel**:
  - the library call: up to 56.1k with the next owners (51 groups, 5 bodies; 54k without them);
  - in the GOD v10 test, where the adapter also builds its own group list, the whole write cost 138k on draft turn 1 and 48-65k on
    turns 2-5. It left at least 24.2k of 100k after v10's pick (TEAMPLAN.md 10, 16:35).
  - **measured in the library** (`dmem2.h own_groups` + `build_own`, the groups built from mapintel's view): 42.2k for the first
    body on draft turn 1, at most 64.0k in a draft turn (5-6 bodies); the guard skips it on the last turn on most maps.
  - implementation: the group values are gems + `gold_gems` x gold (`teamplan::Params`, 0.167 LEARNED); the walks are the M block's
    (255 = none), so a champion's recompute has the same inputs.
- **In the game**: a score bonus for the owner (x 1.25 in the v10 test), never a hard rule. Measured on v10: level over 8 rosters
  (TEAMPLAN.md 11). The new bot should start with a small bonus and test it, maps with more than 30 groups separately (it lost
  there on v10).
- **Prototype**: version 1 of this block, at offset 8 in the v10 test copy. Batteries: TEAMPLAN.md section 11.

### 5.3 BODY (6 x 16 bytes): what each body cannot cheaply derive

| Byte | Content |
|---|---|
| 0 | role code (0 farmer, 1 front, 2 carry, 3 banker; from kit.h scores and the capture rule) |
| 1-8 | build order: 8 item codes (SDK `item_type` order; 255 = end) chosen against the enemy's visible picks |
| 9-11 | opening route: the first three groups (from mapintel plan 1 when present) |
| 12 | bank bag (gems) |
| 13 | retreat health (percent of maximum) |
| 14-15 | reserved |

Fuel: BODY and CONT together 10.4k on the last draft turn (measured with the default build hook; a bot's own build logic adds its
cost). The route is a copy of mapintel's plan 1 (no new computation).

Implementation (`dmem2.h build_body`): roles from the kits: the banker = the highest gold multiplier above 1, else the highest gold
per tributed gem; the front = the first other body of `teamplan::front_order` (two at 5+ bodies); the carry = the remaining body with
the highest damage per round; the rest farm. Bytes 1-8 come from the bot's `BuildHook` (255 without one). Bytes 9-11: plan 1's first
three groups of the plan slot with this body type. Bytes 12-13: the economy model's bank bag (20 gems) and retreat health (52%),
LEARNED (`econ_learn.py`). Empty slots are 0xFF.

### 5.4 CONT (32 bytes): contingencies

- **Bytes 0-23**: for each possible enemy last pick (12 draft picks x 2 bytes), the response:
  - byte 0: the BODY build index to swap from;
  - byte 1: a danger class (0 none, 1 burst, 2 stun chain, 3 big-bag carrier).
  - Our draft cannot see that pick, so the champions apply the entry when they first see it.
- **Bytes 24-31**: the early-contact plan: the variant to switch to (plan id) for contact before rounds 50 / 100 / 200 on our half, our
  side of the map, and theirs.
- Implementation (`dmem2.h build_cont`, written on the last draft turn with the enemy's visible picks as the context): byte 0 from the
  bot's `SwapHook` (255 without one); the danger class: 1 burst when the pick's one-round damage (strength + modifier x focus of every
  damaging spell) is at least the 4th largest of the 13 designs; else 2 stun chain when it stuns and another visible enemy pick stuns;
  else 3 big-bag carrier when its kit takes focus from gems, gold from tributes or a gold bonus; else 0. Bytes 24-31 are zero (no
  variants yet).

### 5.5 CODE (32 bytes): the codebook

The live bytes carry 6-bit place codes instead of raw tiles (smite, 4 Musketeers). The places are the groups, then the altars, then
the rally tiles below (section 6), so a claim or an alert can point at a rally tile or an altar:

| Bytes | Content |
|---|---|
| 0-15 | 8 rally tiles (uint16) |
| 16-23 | 8 zone anchors (group ids) |
| 24-31 | 8 altar ids (index in the altar list: ascending tile index) in bank order |

Implementation (`dmem2.h rally_tiles`, `build_code`):
- **Rally tiles**, up to 8, so claims and alerts can name them: first the approach of each contested group of mapintel plan 3 (up to
  5, plan 3's order): from the group's camp tile nearest our spawn, our traced walk towards our spawn to its first tile outside every
  striking camp's range (Chebyshev > the largest range among the group's camps with strength; a group without one: the first tile
  that is no camp tile), where a team gathers before it wakes the group; then the approach of each bank altar in bank order (the
  standable tile within Chebyshev 1, the tribute range, nearest our spawn; no camp tile unless every one is); then the remaining
  contested groups. Roster-free: computed once on draft turn 1 with the bank order (both 38.2k at most). 0xFFFF = none.
- **Zone anchors**: per slot, the first group in OWN's schedule order that the slot owns (255 none).
- **Group and altar indices** are the places' (section 6): mapintel's groups come in `camp_groups()` order and its altars in
  ascending tile index.

### 5.6 ENEMY (16 bytes): the enemy model from their visible picks (a soft input)

| Bytes | Content |
|---|---|
| 0-3 | their predicted first four groups |
| 4-7 | their likely bank altars |
| 8-11 | their likely big-bag carriers (body types, by passive and kit: gold bonus, gems-to-focus, stun immunity) |
| 12-15 | danger classes of their picks |

Implementation (`dmem2.h build_enemy`, on every draft turn the guard allows): their bodies' first targets as plan 1 assigns ours
(`Compact::first_assign`: walk to attack range + work, over their max(4, bodies) <= 6 nearest reached groups), then their nearest
groups; their bank altar for each = plan 2 by box distance (`BankBox`, equal to `Compact::bank_box`); carriers by the CONT carrier
score; danger classes as in CONT. The enemy side's tables are our Compact mirrored (`Compact(ours, 1)`: no second group preparation).
Fuel: 51.7k on its first run (the mirrored tables and the altar table) and 7-19k after.

### 5.7 NAV (64 bytes): static navigation hazards (for unknown maps; known maps carry them in the binary)

| Bytes | Content |
|---|---|
| 0-15 | 8 chokepoint tiles (uint16; articulation points or one-tile-wide crossings of the spawn-to-spawn and spawn-to-group paths) |
| 16-23 | 4 dash-only pocket entry tiles |
| 24-39 | 8 dash-crossable hole-line tiles |
| 40-55 | 8 field anchors: the tiles worth caching a full field for (spawn, bank altars, top groups) |
| 56-59 | counts |
| 60 | implementation: the parts computed (63 = all; a computed block is written only when complete) |
| 61 | implementation: the source: 1 computed in this draft, 2 copied from `known_maps.h` |
| 62-63 | reserved |

- **Definitions** (`hazards.h` header comment): chokepoints are cut tiles (a passable tile whose passable neighbours split into two
  or more king-connected parts) on the traced spawn-to-spawn walk and the walks to the first three anchor groups; pocket entries are
  passable tiles our walk does not reach but a dash (range 2) does; hole tiles are holes with passable tiles on both sides in a line,
  kept when the walk saving is at least 3; anchors: our spawn end of the spawn-to-spawn walk, the first three bank altars, the near
  tiles of the first four anchor groups (`first_scores()` ranking).
- **Fuel**: a known map copies the table (free). An unknown map computes it as resumable work (`NavWork`, `nav_resume`): it runs
  down to a fuel floor each draft turn and continues on the next; measured at most 236k in all (traced walks cost ~300-900 fuel a
  step); complete on draft turn 1 on 102 of 104 map-teams, on a later turn on the other 2. A full host field costs 1.3-31k, so the
  anchors are chosen in the draft and the fields built at startup.
- The local detour (`teamplan/nav_sdk.h`) costs 9k median, 17k max per call.

### 5.8 DEBUG (16 bytes)

| Bytes | Content |
|---|---|
| 0-9 | fuel used in draft turns 1-5 (uint16, in units of 16) |
| 10-11 | builder version |
| 12 | implementation: the draft turns written |
| 13 | implementation: the guarded blocks skipped on this write's turn (bit k = TOC entry k) |
| 14-15 | reserved |

### 5.9 MAPINTEL-DL (136 bytes at 864, TOC id `L`, version 1): the step-7 models (implementation, Oct 24)

The user's GPU run of 17:22 applied at the user's request (MAPAnalysis.md 7.2, 17:55 and 18:55): the distilled opening and
next-target MLPs (`dl_weights.h`, below the export rule: opening share 0.700 vs 0.696 for `first_scores()`; next target top-1 0.330
vs 0.236 for the nearest group to the previous one and 0.360 for the step-6 forest, which the library does not carry). LEARNED.

| Bytes | Content |
|---|---|
| 0 | flags: bit 0 the opening ranking, bit 1 the routes |
| 1 | source: 1 computed in this draft (`dl_weights.h`), 2 copied from `known_maps.h`'s tables (`tools/mapintel/dl/dl_tables.py`) |
| 2-3 | the round the next model's late phase starts (571, the median of its training samples) |
| 4-7 | the next model's round input per phase: 329 and 849 (the quartiles) |
| 8-23 | the opening model's ranking: 16 groups, best first (255 none) |
| 24-59 | per body slot (TEAM order) a route of 6 groups: its plan-1 first target, then each the next model's best group after the previous one at the early phase, skipping groups already on the route (from its two best; 255 none) |
| 60-135 | zero |

- **Known maps** (zero fuel in the game): `known_maps.h` carries per map and team the opening ranking and, per phase, body type and
  group, the next model's two best groups (`known_dl_next(entry, team, round, type, group)`), so a champion looks up its next target
  after any capture; the draft copies the ranking (turn 1) and builds the routes from the table (last turn, 3.7k).
- **Unknown maps**: the draft computes the opening ranking on turn 1 when the guard allows (`dl_inputs` ~62k + `dl_opening_scores`
  ~91k; it did on 20 of 24 unknown map-teams in the test); no routes (each step would score every group, ~87k).

## 6. Live bytes (8 bytes, all game): `teamplan/live.h` + `teamplan/live_sdk.h` (built and engine-tested)

**Layout** (64 bits, little-endian; vision is not shared between allies, so the alert is how one body tells the others what it sees):

| Bits | Written by | Content |
|---|---|---|
| 8b..8b+7, slot b = 0..5 | that body only | its field: claim (6 bits, a place code; 63 = none, also while dead), beat (1 bit, toggled every turn it publishes), flag (1 bit, carrying at least the hunt threshold, 25 gems by default) |
| 48-53 | any body, under the post rule | alert place: a place code, stored + 1 so the all-zero start means "no alert" |
| 54-55 | | alert kind, also its rank: 0 an enemy army (keep away, do not walk in alone), 1 an enemy at an altar (its tribute can be cancelled by a stun or a lock; or it threatens ours), 2 a kill chance (an enemy with low health or a big bag), 3 help (an ally is fighting there) |
| 56-57 | | enemies seen there: 1-4 (4 = four or more) |
| 58-59 | | sequence: bumped by every post, so a repost of the same sighting still changes the field |
| 60-62 | the lowest live slot | plan cursor (the variant in use) |
| 63 | the lowest live slot | tiebreak bit |

**Places** (`place_code`, `place_kind`, `nearest_place`): one 6-bit vocabulary for claims and alerts.
- **Order**:
  1. the map's camp groups, in the SDK's `camp_groups()` order;
  2. the altars, in ascending tile index (`y * W + x`);
  3. the CODE block's rally tiles, in its order.
- **Codes** are 0-62. Places past 62 get no code: the rally tiles go first, then the last altars.
- **Fit**: the largest official map has 51 groups, so every official map fits.
- **Readers**: every body and the draft compute the same list, so no tile coordinates are sent.
- **A sighting is reported at the place nearest the enemy** (Chebyshev distance, ties to the lower code).

**The post rule** (`alert_accepts`): a post replaces the current alert when any of these holds:
- there is none;
- it is at least 5 rounds old (`LiveState::ttl`, ASSUMED; rounds since its field last changed, as the poster saw it);
- the post ranks higher;
- the post is the same sighting (same kind and place: a refresh).

Otherwise the current alert stays (first come, first served), so two posters do not flip it every turn. Readers ignore an alert older
than the ttl.

**Slots**: the allies' body types in ascending order (`live_slot_of`). Every body computes the same order at spawn, and TEAM bytes 4-9
list the bodies in that same order, so OWN's owner nibbles and the live slots agree.

**Every turn, at its start** (`live_sdk.h`):
1. `live_observe(L, live_read(), round)`: one host read of the 8 bytes; which slots are live; the alert and its age;
2. the body decides what to publish and whether to post a sighting;
3. `live_write(live_compose(L, claim, flag, cursor, tiebreak, post))`: one host write. It carries:
   - our field with the beat toggled;
   - the team bits, when no lower slot is live;
   - our alert, when the post rule accepts it.
- **Turns never overlap**, so the read-modify-write is safe: the engine test checked every read against the previous body's write.
- **Fuel**: 991 at most per body-turn with alerts (engine test, 40 maps x 2 teams). `nearest_place` over the place list is extra, once
  per sighting.

**When a slot is live**:
- **The slot has published once**: a nonzero field, or a change, was seen. The memory starts at zero.
- **Its field showed a sign of life within the last 2 rounds**: a beat toggle or any changed bit.
- **One round of doubt**: a reader that lost its own previous turn cannot tell two toggles from none. A field unchanged across exactly one
  skipped round gets one round of doubt, once in a row.
- **The bounds**:
  - a body that stops publishing is stale in every view within 4 rounds of the reader first seeing its last write (3 without a
    skipped round);
  - a body that keeps publishing is never marked stale (engine test, with real lost turns).

**Dead champions still act** (they get a turn to shop, GameRules), so a dead body keeps beating. It publishes claim 63 (none) while
dead. Staleness catches lost turns and stopped processes, not deaths.

**Agreement with the draft memory** (checked in the engine by `tools/mapintel/test_dmem2.py`, MAPAnalysis.md 7.2, 18:55): TEAM
bytes 4-9 hold the body types in ascending order (`dmem2.h roster_types`); on 1,360 of 1,360 bodies the game's `live_init` slot (from
the engine's ally list) equals the TEAM slot and the body counts agree, so OWN's nibbles, BODY and the CODE zone anchors use the live
slots. Group indices everywhere are mapintel's, which follow `camp_groups()` (the in-game OWN recompute, which reads `camp_groups()`,
reproduces the draft's table on 264 of 264 map-teams); altar ids index the ascending-tile altar list; every CODE rally tile and altar
id round-trips through `place_code` / `place_kind`. **One limit**: a map with groups + altars + 8 rally tiles over 63 places names only
the first rally tiles: on lanes (42 groups, 18 altars) 3 of its 8 (the contested groups' approaches, which come first); every other
official map names all of them.

**Removed from the first version**: each body's 2-bit progress code (the input of `swap.h`'s job-swap check). The alert took those 12
bits (TEAMPLAN.md 11.7).

## 7. Write order across draft turns, and the fuel guard

**The guard**:
- Every optional block measures its own cost (`fuel_remaining()` before and after) on the turn it runs.
- On a later turn it runs only when the fuel left exceeds **1.25 x its last cost + 10,000**. Otherwise it keeps its earlier valid
  version, and the TOC and TEAM byte 11 say which version that is.
- The margin covers growth from one more body: the OWN write grew 10-13% per body in the v10 test (47.9k, 54.0k, 59.2k, 65.1k for
  2-5 bodies).

**Per turn, with mapintel's measured costs** (`tools/mapintel/README.md`, worst official map):

| Turn (fuel) | Work, in order | Fuel |
|---|---|---|
| 1 (1,000,000) | the pick | mapintel's draft signal: under 3k |
| | mapintel's turn-1 work: view, fingerprint, features, plans 2-4, the first pick's rows, `first_scores()` | at most 778.8k |
| | the kits of the 13 designs; the bank order and the rally tiles; the M block; TEAM; CODE | 35.2k; 38.2k; 7.4k; 0.7k |
| | NAV: copied (known map) or resumed down to a 30k floor (unknown map) | 0; up to 236k in all, over turns |
| | OWN for the first body (the `AGroup` list from mapintel's view, no second scan), guarded; ENEMY, guarded; the DL opening, guarded; write with `minimal` set | 42.2k; 51.7k; ~153k; 0.6k |
| 2 to the last but one (100,000) | the pick; mapintel's `row()` for the champion just picked | at most 13.5k |
| | OWN for the bodies so far, guarded | at most 64.0k |
| | TEAM, CODE; ENEMY from their visible picks, guarded; NAV resumed down to a 12k floor; write | 0.7k; 7-19k; the rest |
| last (100,000) | the pick; `row()`; mapintel's `plan1` and its block | mapintel leaves at least 28k |
| | BODY and CONT; the L block's routes; TEAM with the final roster; write with `final` set | 10.4k; 3.7k; 0.7k; 0.6k |
| | OWN for the final roster and ENEMY, only under the guard | skipped on most maps |

Measured with the test bot (the reference integration): draft turn 1 used at most 989,852 of 1,000,000 by the engine's own count
(big-world, NAV computed; 896,494 with NAV copied), every later draft turn at most 93,024, and the last turn left at least 7,904
before its write.

**The engine's behaviour when a draft turn runs out** (measured): the turn continues in the next turn's budget (`fuel_remaining()`
then reads the next turn's), so that next turn's pick is lost; the engine reports "yielded without picking" and draws the rest at
random. The per-turn counts are in the replay (`team-*.fuel`: 8 limits, then every turn of the team, its draft turns first).

**OWN for the final roster in the game**:
- When TEAM byte 11 is below the roster size, every body recomputes OWN once for the full roster (TEAM bytes 4-9), on the map's groups,
  with the same library call. The call costs at most 56.1k; reading the map's groups in a game turn (`camp_groups()`, a camp's type
  and health) costs more on maps with many camps, so the implementation (`dmem2.h OwnRecompute`) is resumable work over game turns
  down to a fuel floor: measured 154.8k in all, over at most 2 game turns with a 20k floor.
- **The inputs are identical in every body** (static map data, the engine's designs, the draft's body list), so every body gets the
  same table without a message (P3: XSquare 2020, smite).
- **The recompute waits for a turn with fuel to spare** (a later 100k turn, not the first one). Until then mapintel's plan 1 gives the
  opening targets (6 bodies x 4 targets).

## 8. Tests the implementation needs (for the other Claude)

**Status: all six pass** (`python3 -I tools/mapintel/test_dmem2.py`, Oct 24): 1. 2,108 blocks and 264 images bit-equal; 2. every
champion reads 0xAB at byte 1000 after the 1,000-byte write and the rest unchanged; 3. the numbers of section 7 (lanes, big-world,
road-of-riches and every other official map; the pick first on every turn, all picks ours); 4. the M block equals `compact.pack`, the
TOC entry M points at 512 / 352, `dmem_get` (the v1 reader) reads it, and the L block equals the twins; 5. six corrupted copies
(OWN data, BODY version, header magic, CODE offset past the end, ENEMY not valid, NAV missing): the reader finds exactly the other
blocks, none with a bad header, no exception; 6. OWN is written for the final roster or left at the earlier version (TEAM byte 11),
and the in-game recompute gives the same table in every body, equal to the twin's for the full roster (264 of 264).

1. **Round trip**: pack in C++, unpack in Python (and back). Bit-equal on 40 maps x 2 teams x 3 rosters.
2. **Prefix rule**: a shorter write after the image leaves the tail intact, and every champion reads the final image.
3. **Fuel**: each draft turn's work stays under its limit on the largest official maps (lanes, big-world, road-of-riches), and the pick
   always comes first.
4. **Coexistence**:
   - mapintel's block at 512 (and DL at 864) is byte-identical to `compact.pack`;
   - the TOC entry M points at it;
   - an old reader of mapintel's block still works.
5. **Fallback**: a corrupted or missing block (wrong checksum, wrong version) makes every reader take its fallback, with no exception.
6. **The last turn and the in-game OWN**:
   - with the guard, the last draft turn never runs out on the largest maps;
   - OWN is either written for the final roster or left at the earlier version (TEAM byte 11 says which);
   - in the second case, every body's in-game recompute gives the same table (print a hash per body and compare).
