# Draft memory: the final layout (version 2)

This is the specification for the user's new bot (TEAMPLAN.md 8). The mapintel library implements it; the handoff prompt for that is
given in chat at the end of the team-play session.

**Status (Oct 24, end of the team-play session)**:
- The layout below is final for version 2. The other Claude implements it in the mapintel library.
- **One block has a working prototype**: OWN version 1, written by the GOD v10 test copy at offset 8 (`tools/teamplan/v10_adapter.patch`).
  - Its draft fuel is measured (section 7).
  - Its effect is measured on v10: TEAMPLAN.md 11 (SIMULATED (v10)).
- **mapintel's block** (version 1, at 512) is in use and stays where it is.
- Fuel numbers are measured where a number is given; the rest are marked "to be measured".

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
  - the kits: all 13 designs cost 20k fuel;
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
| 864-999 | 136 | MAPINTEL-DL | mapintel's optional DL outputs (`dl_weights.h`): opening ranking, next-target ranking, champion values |
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
| 12-15 | reserved |

### 5.2 OWN (64 bytes): soft ownership, one byte per group (G <= 64; groups 64+ have no owner)

- **Low nibble: the owner slot** (15 = none; the library's `kNoOwner` 255 is stored as 15). Computed by `teamplan::assign_groups` (list
  scheduling; gem-free groups lean to front bodies) for the bodies picked so far.
- **High nibble: the next owner**, who takes the group while the owner is dead (15 = none). It is the runner-up body of the same
  scheduling step: `assign_groups`'s `runner_up` output, added for this layout, so it costs no extra call.
- **Fuel**:
  - the library call: up to 56.1k with the next owners (51 groups, 5 bodies; 54k without them);
  - in the GOD v10 test, where the adapter also builds its own group list, the whole write cost 138k on draft turn 1 and 48-65k on
    turns 2-5. It left at least 24.2k of 100k after v10's pick (TEAMPLAN.md 10, 16:35).
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

Fuel: to be measured with the bot's build logic. The route is a copy of mapintel's plan 1 (no new computation).

### 5.4 CONT (32 bytes): contingencies

- **Bytes 0-23**: for each possible enemy last pick (12 draft picks x 2 bytes), the response:
  - byte 0: the BODY build index to swap from;
  - byte 1: a danger class (0 none, 1 burst, 2 stun chain, 3 big-bag carrier).
  - Our draft cannot see that pick, so the champions apply the entry when they first see it.
- **Bytes 24-31**: the early-contact plan: the variant to switch to (plan id) for contact before rounds 50 / 100 / 200 on our half, our
  side of the map, and theirs.

### 5.5 CODE (32 bytes): the codebook

The live bytes carry 3- to 6-bit indices into these tables instead of raw tiles (smite, 4 Musketeers):

| Bytes | Content |
|---|---|
| 0-15 | 8 rally tiles (uint16) |
| 16-23 | 8 zone anchors (group ids) |
| 24-31 | 8 altar ids in bank order |

### 5.6 ENEMY (16 bytes): the enemy model from their visible picks (a soft input)

| Bytes | Content |
|---|---|
| 0-3 | their predicted first four groups |
| 4-7 | their likely bank altars |
| 8-11 | their likely big-bag carriers (body types, by passive and kit: gold bonus, gems-to-focus, stun immunity) |
| 12-15 | danger classes of their picks |

### 5.7 NAV (64 bytes): static navigation hazards (for unknown maps; known maps carry them in the binary)

| Bytes | Content |
|---|---|
| 0-15 | 8 chokepoint tiles (uint16; articulation points or one-tile-wide crossings of the spawn-to-spawn and spawn-to-group paths) |
| 16-23 | 4 dash-only pocket entry tiles |
| 24-39 | 8 dash-crossable hole-line tiles |
| 40-55 | 8 field anchors: the tiles worth caching a full field for (spawn, bank altars, top groups) |
| 56-59 | counts |
| 60-63 | reserved |

- **Fuel**: to be measured. A full host field costs 1.3-31k, so the anchors are chosen in the draft and the fields built at startup.
- The local detour (`teamplan/nav_sdk.h`) costs 9k median, 17k max per call.

### 5.8 DEBUG (16 bytes)

| Bytes | Content |
|---|---|
| 0-9 | fuel used in draft turns 1-5 (uint16, in units of 16) |
| 10-11 | builder version |
| 12-15 | reserved |

## 6. Live bytes (8 bytes, all game): `teamplan/live.h` + `teamplan/live_sdk.h` (built and engine-tested)

**Layout** (64 bits, little-endian):
- **Bits 10b..10b+9, body slot b = 0..5, written only by that body**:
  - claim: 6 bits, a group index (63 = none);
  - status: 2 bits, the progress code of `swap.h` or a role state;
  - beat: 1 bit, toggled every turn the body publishes;
  - flag: 1 bit, carrying at least the hunt threshold.
- **Bits 60-63, written only by the lowest live slot**: the plan cursor (3 bits: the variant in use) and the tiebreak bit (1).
- **Indices point into OWN, CODE and the variant set**: the draft and the champions computed the same tables.

**Slots**: the allies' body types in ascending order (`live_slot_of`). Every body computes the same order at spawn, and TEAM bytes 4-9
list the bodies in that same order, so OWN's owner nibbles and the live slots agree.

**Every turn, at its start** (`live_sdk.h`):
1. `live_observe(L, live_read(), round)`: one host read of the 8 bytes, and which slots are live;
2. the body decides what to publish;
3. `live_write(live_compose(L, claim, status, flag, cursor, tiebreak))`: our field with the beat toggled, plus the team bits when no lower
   slot is live; one host write.
- **Turns never overlap**, so the read-modify-write is safe: the engine test checked every read against the previous body's write.
- **Fuel**: 708 at most per body-turn (engine test, 40 maps x 2 teams).

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
| | mapintel's turn-1 work: view, fingerprint, features, plans 2-4, the first pick's rows, `first_scores()` | at most 777.7k |
| | the `AGroup` list built from mapintel's view (no second scan of the camp groups) | to be measured |
| | OWN for the first body (or two, for a two-body pick); NAV; TEAM; write with `minimal` set | to be measured |
| 2 to the last but one (100,000) | the pick; mapintel's `row()` for the champion just picked | at most 13.5k |
| | OWN for the bodies so far | at most 56.1k |
| | ENEMY from their visible picks; CODE; write | to be measured |
| last (100,000) | the pick; `row()`; mapintel's `plan1` and its block | mapintel leaves at least 28k |
| | TEAM with the final roster, BODY and CONT; write with `final` set | to be measured |
| | OWN for the final roster, only under the guard | 56.1k does not fit in 28k on the largest maps |

**OWN for the final roster in the game**:
- When TEAM byte 11 is below the roster size, every body recomputes OWN once for the full roster (TEAM bytes 4-9), on the map's groups,
  with the same library call. That costs at most 56.1k.
- **The inputs are identical in every body** (static map data, the engine's designs, the draft's body list), so every body gets the
  same table without a message (P3: XSquare 2020, smite).
- **The recompute waits for a turn with fuel to spare** (a later 100k turn, not the first one). Until then mapintel's plan 1 gives the
  opening targets (6 bodies x 4 targets).

## 8. Tests the implementation needs (for the other Claude)

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
