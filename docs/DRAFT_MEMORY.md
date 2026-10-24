# Draft memory: the final layout (version 2)

This is the specification for the user's new bot (TEAMPLAN.md 8). The mapintel library implements it; the handoff prompt for that is
given in chat at the end of the team-play session.

**Status**:
- The layout below is the plan.
- One block has a working prototype: OWN (version 1, at offset 8 in the GOD v10 test copy, `tools/teamplan/v10_adapter.patch`).
- mapintel's block (version 1, at 512) is in use.
- The fuel numbers are measured where a number is given; the rest are marked "to be measured".

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
- **A draft bot that crashes or runs out of fuel before it picks gets random picks.** So pick first, then compute, then write.

## 2. What goes in

- **Static knowledge about a map goes in the binary**: the catalog table, the model weights.
- **The draft memory carries only what the draft can produce and a champion cannot cheaply derive**:
  1. **results too expensive for a champion's 200k first turn**: the ownership plan costs 54k fuel per call on the largest group lists,
     and the full group list with a spawn field 54-94k (measured, `tools/teamplan/test_teamplan.py`);
  2. **decisions that depend on this game**: our roster, the enemy's visible picks, our side;
  3. **one consistent team decision**: every body reads the same bytes, so nothing has to be agreed in the game.
- **Not stored**, because every body derives it cheaply and identically at startup:
  - the kits: all 13 designs cost 20k fuel;
  - the team side: `cambc::detail::sdk_my_team()`;
  - the roster: allies are in sight on spawn.
- **Data is stored in the form a champion reads it**: fixed offsets and direct indexing, no decode loops. Tiles are `y * W + x` as
  uint16 little-endian.

## 3. Byte map

| Offset | Size | Block | Content |
|---|---|---|---|
| 0-3 | 4 | HDR | magic 0x54, layout version 2, flags (bit 0 final: written after our last pick; bit 1 minimal: only the turn-1 blocks), sum of bytes 4-67 mod 256 |
| 4-67 | 64 | TOC | 8 entries x 8 bytes (section 4) |
| 68-83 | 16 | TEAM | team decisions (section 5.1) |
| 84-147 | 64 | OWN | one byte per group (section 5.2) |
| 148-243 | 96 | BODY | 6 body slots x 16 bytes (section 5.3) |
| 244-275 | 32 | CONT | contingencies (section 5.4) |
| 276-307 | 32 | CODE | the codebook the live bytes index into (section 5.5) |
| 308-323 | 16 | ENEMY | the enemy model from their picks (section 5.6) |
| 324-387 | 64 | NAV | static navigation hazards for unknown maps (section 5.7) |
| 388-403 | 16 | DEBUG | draft fuel per turn, builder version (section 5.8) |
| 404-511 | 108 | free | reserved for later patches |
| 512-863 | 352 | MAPINTEL | mapintel's block, version 1, unchanged (`tools/mapintel/cpp/mapintel/dmem.h`): fingerprint, flags, archetype, per group the bank altar and both walks, 16 contested groups, 8 thresholds, plan 1, checksum |
| 864-999 | 136 | MAPINTEL-DL | mapintel's optional DL outputs (`dl_weights.h`): opening ranking, next-target ranking, champion values |
| 1000-1023 | 24 | free | |

The total in use is 404 + 352 + 136 = 892 bytes, which leaves 132 free.

## 4. Header and table of contents

**TOC entry** (8 bytes):
- id (u8; ASCII letter: T, O, B, C, K, E, N, D, M for mapintel, L for mapintel-DL);
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
- Each draft turn: pick first, update the blocks this turn's fuel allows, recompute their TOC entries and the HDR sum, submit the
  whole image.
- `final` is set on the write after our last pick.

## 5. Blocks

### 5.1 TEAM (16 bytes): the team-level decisions

| Byte | Content |
|---|---|
| 0 | plan id (the variant the team starts with: 0 = base) |
| 1 | number of OWN variants available (0 = only the base table) |
| 2 | tiebreak-prone map (bit 0, `tiebreak.h` / mapintel plan 4's mode); bits 1-2 the mapintel tiebreak mode copy |
| 3 | capture rule (`capture.h` capture_mode) |
| 4-9 | body types by slot, the same order as OWN and BODY (255 = none), so a body finds its slot without reading the roster |
| 10 | groups G covered by OWN |
| 11-15 | reserved |

### 5.2 OWN (64 bytes): soft ownership, one byte per group (G <= 64; groups 64+ have no owner)

- Low nibble: the owner slot (15 = none). High nibble: the next owner, who takes the group while the owner is dead (15 = none).
- Computed by `teamplan::assign_groups` (list scheduling; gem-free groups lean to front bodies) for the bodies picked so far, and again
  after our last pick.
- The next owner is the same plan with the owner left out.
- **Fuel**:
  - 54k worst per call (51 groups);
  - the group list with the spawn field 54-94k (turn 1, cached in RAM);
  - the next owners need one more call per body (computed only while the turn has fuel; else 15).
- **In the game**: a score bonus for the owner (x 1.25 in the v10 test), never a hard rule.
- **Prototype**: version 1 of this block is written at offset 8 by the v10 test copy. Batteries: TEAMPLAN.md section 11.

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

## 6. Live bytes (8 bytes, all game): `tools/teamplan/cpp/teamplan/live.h`

- **Bits 10b..10b+9, body slot b = 0..5, written only by that body**:
  - claim: 6 bits, a group index (63 = none);
  - status: 2 bits, the progress code of `swap.h` or a role state;
  - beat: 1 bit, toggled each turn the body acts; a field unchanged for 2 rounds is stale;
  - flag: 1 bit, carrying at least the hunt threshold.
- **Bits 60-63, written by the lowest alive slot**: the plan cursor (3 bits: the variant in use) and the tiebreak bit (1).
- **Indices point into OWN, CODE and the variant set**: the draft and the champions computed the same tables.

## 7. Write order across draft turns

1. **Turn 1 (1,000,000 fuel)**, after the pick:
   - the group list with the spawn field (cached);
   - mapintel's block;
   - NAV;
   - TEAM with the bodies so far;
   - write with `minimal` set.
2. **Turns 2 to the last but one (100,000)**, after the pick: OWN for the bodies so far, ENEMY from their visible picks, CODE. Write.
3. **Last turn (100,000)**, after our last pick:
   - OWN for the final roster: 54k worst;
   - BODY and CONT;
   - write with `final` set.
   - Anything that does not fit keeps its earlier valid version: the TOC says which.

## 8. Tests the implementation needs (for the other Claude)

1. **Round trip**: pack in C++, unpack in Python (and back). Bit-equal on 40 maps x 2 teams x 3 rosters.
2. **Prefix rule**: a shorter write after the image leaves the tail intact, and every champion reads the final image.
3. **Fuel**: each draft turn's work stays under its limit on the largest official maps. The pick always comes first.
4. **Coexistence**:
   - mapintel's block at 512 (and DL at 864) is byte-identical to `compact.pack`;
   - the TOC entry M points at it;
   - an old reader of mapintel's block still works.
5. **Fallback**: a corrupted or missing block (wrong checksum, wrong version) makes every reader take its fallback, with no exception.
