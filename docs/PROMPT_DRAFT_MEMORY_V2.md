# Prompt for the agent of the map-analysis work: implement the final draft-memory layout (team-play handoff, Oct 24 2026)

Paste everything below the line into the session that carries out the map-analysis work (or a new session).

---

You continue the **map-analysis work** for Cambridge Battlecode 2026a (CAMBC; C++ bots compiled to wasm; engine cambc 3.0.5 = engine
v1.0.3). The user is writing **their own new bot**. A second session (team play, `TEAMPLAN.md`) has finished the final draft-memory
layout for that bot. **Your task: implement it in the mapintel library** (`tools/mapintel/cpp/mapintel/`), with Python twins and engine
tests. Then the user's bot can write and read all 1,024 bytes through one API. You do not build or ship a bot.

**Read first**:
1. `docs/DRAFT_MEMORY.md`: the spec, byte by byte, with the write order, the fuel guard and the tests;
2. `TEAMPLAN.md` section 2 (the facts it relies on), the 16:35 checkpoint in section 10 (the draft fuel of the ownership block), and
   section 11 (the results);
3. `tools/teamplan/README.md` (the team-play library you reuse);
4. your own `MAPAnalysis.md` and `tools/mapintel/README.md`.

## Rules (the user's, still in force)
- **Report and record each step**:
  - report in a few lines;
  - write it into `MAPAnalysis.md` (a checkpoint in 7.2 with the UTC time, and the status in 7.1);
  - commit and push, then keep going without waiting. The user answers slowly: decide, record the decision, continue.
- **Git**:
  - commit and push to `main` at every step;
  - run `git pull --no-rebase origin main` before each push;
  - never force-push; no pull request;
  - end commit messages with the session's attribution lines;
  - no model identifier in any repository file.
- **No bot changes**: do not modify anything under `bots/` (apart from your git-ignored test bots) or `submissions/`, and do not ship any
  bot.
- **No names in logic**:
  - champions enter through their designs, `passive_type` and the SDK constants;
  - maps enter through their features;
  - the exact-match table of the official maps is the only approved exception;
  - list anything hardcoded in `ISSUES.md`.
- **Sources**: the 3.0.5 engine and SDK, your own probes, the 40 official maps (`maps/official/`), current-patch ladder data,
  `MAPAnalysis.md`, `TEAMPLAN.md`. Mark every output **COMPUTED**, **LEARNED** or **SIMULATED (v10)**.
- **Process and data safety**:
  - never `pkill -f` or `killall`: kill by PID;
  - never handle the user's credentials;
  - never use or commit the personal PDFs from session 13;
  - map file names stay unique under `maps/`.
- **Fuel**: 1,000,000 on the first draft turn, 200,000 on a champion's first turn, 100,000 on every other turn. Measure every new
  in-bot function in the engine.
- **Few subagents**; do the core reasoning yourself.

## What exists
- **Your mapintel block**, version 1, at 512-863:
  - `dmem.h` (`dmem_pack`, `dmem_put`, `dmem_parse`, `dmem_get`) and `compact.pack` in Python;
  - the DL outputs are reserved at 864-999.
  - **Keep both byte-identical.**
- **The team-play library** `tools/teamplan/cpp/teamplan/` (header-only C++ with Python twins in `tools/teamplan/tp/`). Its engine test
  `python3 -I tools/teamplan/test_teamplan.py` checks 8,019 results bit-equal on 40 maps x 2 teams. What you need from it:
  - `assign.h`: `assign_groups`, the soft ownership plan. Its `runner_up` output is the next owner. 56.1k fuel worst (51 groups, 5
    bodies).
  - `kit.h`: kit values from the designs; `front_order`; passives by tag.
  - `sdk_bridge.h`: `design_of`, `consts_from_sdk`.
  - `capture.h`: mode 1, the LEARNED rule.
  - `tiebreak.h`, `nav.h` / `nav_sdk.h`.
  - **The 8 shared live bytes are already built**: `live.h` and `live_sdk.h` (`live_read` / `live_write` / `live_init`). They cost 991
    fuel per body-turn.
    - What they carry: per body a claim, a heartbeat and a bag flag; the team alert (an enemy army, an enemy at an altar, a kill chance,
      help: where, how many enemies); the plan cursor and the tiebreak bit.
    - What the engine test checks: every read equals the previous write, lost turns, stale detection, the hand-over of the team bits,
      and the alert's post rule.
    - Do not rebuild them. Your blocks must agree with them in three ways (`docs/DRAFT_MEMORY.md` 5.1, 5.5 and 6):
      - **Slots**: the live slots are the allies' body types in ascending order, and your TEAM block (bytes 4-9) lists the bodies in
        that order.
      - **Places**: claims and alerts use one 6-bit place code (`live.h` `place_code`). The order is the map's camp groups in the SDK's
        `camp_groups()` order, then the altars in ascending tile index, then your CODE block's rally tiles. Your group indices (OWN,
        CODE zone anchors, ENEMY) must use that same group order, and your altar ids the ascending-tile altar list.
      - **Rally tiles**: CODE bytes 0-15 hold the rally tiles. Pick them so a claim or an alert can name them, for example the
        contested groups' approach tiles and the bank altars' approaches.
- **The OWN prototype** (version 1 at offset 8) in the git-ignored GOD v10 test copy (`tools/teamplan/v10_adapter.patch`):
  - draft fuel measured: 138k on turn 1, 48-65k on turns 2-5, at least 24.2k left;
  - rosters equal v10's in 80 of 80 games.
- **Results** (TEAMPLAN.md 11): soft ownership was the only lead. The bag rule, the timing gate and the tiebreak deferral did not hold.

## The task
1. **The image**: `tools/mapintel/cpp/mapintel/dmem2.h` + the twin `tools/mapintel/dmem2.py`.
   - The 1,024 bytes per `docs/DRAFT_MEMORY.md` 3-4:
     - HDR at 0-3 (magic 0x54, version 2, flags, TOC sum);
     - the TOC at 4-99 (12 entries x 8 bytes);
     - the blocks at their offsets.
   - Pack, parse and validate. One RAM image, submitted whole every draft turn.
   - Your v1 block goes in unchanged at 512 (`dmem_pack` / `dmem_put`), listed in the TOC as `M`; the DL block as `L` when present.
   - The fuel guard of section 7: a block runs only when the fuel left exceeds 1.25 x its last cost + 10,000, else it keeps its earlier
     valid version.
2. **The block builders** (C++ and twin, each with its fuel measured in the engine):
   - **TEAM**:
     - plan id 0;
     - the tiebreak-prone flag from your plan 4's mode;
     - capture mode 1;
     - the body types by slot in ascending body type (the live slots' order), G, and the bodies OWN covers (byte 11).
   - **OWN**:
     - `teamplan::assign_groups` on `AGroup`s built from your view (value = gems + `gold_gems` x gold, the camps' total health, the walk
       from our spawn, gem-free). Reuse your walks: no second scan of the camp groups.
     - The owner goes in the low nibble, the runner-up in the high nibble.
     - Draft turns 1 to the last but one: written for the bodies picked so far. The last turn: under the guard only (56.1k does not fit
       after `plan1`).
     - The reader recomputes OWN once in the game when byte 11 is below the roster size; every body gets the same table.
   - **BODY**:
     - the role from `kit.h` (`front_order`) and the capture rule;
     - the route = plan 1's first three groups;
     - the bank bag and retreat health from your LEARNED economy constants;
     - the build order through a hook the user's bot provides (default 255 = none).
   - **CONT**:
     - danger classes per possible enemy last pick, from kit features (burst, stun chain, big-bag carrier by passive);
     - the build-swap index through the hook (default 255).
   - **CODE**:
     - rally tiles (your contested groups);
     - zone anchors (each body's best owned group);
     - altar ids in bank order (plan 2).
   - **ENEMY**:
     - their predicted first groups (plan 1 for their side and their visible picks);
     - their bank altars (plan 2 for their side);
     - their likely big-bag carriers (by passive and kit);
     - danger classes.
   - **NAV**, the static hazards:
     - what: chokepoints (articulation points of the spawn-to-spawn and spawn-to-group paths), dash-only pocket entries, dash-crossable
       hole-line tiles, and the field anchors (spawn, bank altars, top groups);
     - unknown maps: computed in the draft on turn 1 (fuel measured);
     - known maps: also in the catalog and `known_maps.h`, so the draft copies them.
   - **DEBUG**: the fuel per draft turn and the builder version.
3. **The reader API for champions**:
   - find a block by its TOC id;
   - check its version, checksum and `valid`;
   - otherwise take the fallback, with no exception.
4. **Tests** (`docs/DRAFT_MEMORY.md` 8), in the engine like `test_library.py`:
   - round trip C++ <-> Python, bit-equal on 40 maps x 2 teams x 3 rosters;
   - the prefix rule;
   - fuel per draft turn on the largest maps (lanes, big-world, road-of-riches), with the pick first;
   - coexistence:
     - the 512 block is byte-identical to `compact.pack`;
     - the TOC entry `M` points at it;
     - an old v1 reader still works;
   - the fallback on corrupted or missing blocks;
   - the last-turn guard, and the in-game OWN recompute giving the same hash in every body.
5. **Docs**:
   - `MAPAnalysis.md` checkpoints;
   - `tools/mapintel/README.md` (how a draft writes v2 and how a champion reads it);
   - the `ISSUES.md` mapintel section;
   - the status lines of `docs/DRAFT_MEMORY.md` (replace every "to be measured" with the number).

## Constraints
- **The bot's own bytes stay below 512** (the v2 blocks use 0-435). Your block stays at 512-863, the DL block at 864-999.
- **Changes to `tools/teamplan/`**: only bug fixes. After any change to a teamplan header, update its Python twin and rerun
  `python3 -I tools/teamplan/test_teamplan.py`; it must print "all checks passed".
- **The first draft turn**: your library takes at most 777.7k on the worst official map. The v2 additions must fit in what is left,
  with the pick done first.
- **Later turns** (100,000 each): your `row()` takes at most 13.5k and `plan1` at most 43k. On the last turn your work leaves at least
  28k, so OWN for the final roster is written there only under the guard.
