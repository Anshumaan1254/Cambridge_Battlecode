# tools/teamplan: team play for a CAMBC bot

This folder holds team-play rules for the user's new bot, written as a library: who farms which group, who captures a reward, when a
body with a bag fights, kill value, turn order, tiebreak mode, job swaps, the live-byte protocol and navigation guards.
- The reasoning, the evidence and the results are in `TEAMPLAN.md`: sections 2-9 for the reasoning and evidence, section 11 for the
  results.
- The draft-memory layout the library feeds is in `docs/DRAFT_MEMORY.md`.

**Status**:
- Every module has a Python twin and an engine test.
- The rules were tested on a git-ignored GOD v10 copy (results SIMULATED (v10)). None beat v10 over all the rosters tried: the timing
  gate and the tiebreak deferral lost, and the bag rule, soft ownership and kill-value targeting were level (TEAMPLAN.md 11).
- No bot ships with this library yet. `bots/god` and `submissions/` are untouched.

## Layout

| Path | What |
|---|---|
| `cpp/teamplan/*.h` | the library: header-only C++17, no SDK dependency except `sdk_bridge.h` and `nav_sdk.h` |
| `tp/*.py` | Python twins of every module, bit-equal |
| `cpp/test/main.cpp` + `test_teamplan.py` | the engine test: the test bot prints hashes of every result, and the twins recompute them |
| `cpp/probe_nav/main.cpp` + `probe_nav.py` | the navigation fuel probe (TEAMPLAN.md 6) |
| `prepare_v10.py` + `v10_adapter.patch` | the GOD v10 test copy with the `tp_*` switches |
| `make_forced_v10.py` | opponent family 2: v10 forced to a strong-team roster per map |
| `batteries.py` | the batteries: every switch alone and combined, two opponent families; `--confirm` for the confirmation battery |
| `kit_table.py` | the kit table for every engine design (a report) |
| `capture_rows.mjs`, `capture_ctx.mjs`, `capture_check.py` | captures from replays, and the check of the capture rules against the top teams' choices |
| `ladder_roles.py` | role tables from decoded top-team games (TEAMPLAN.md 3) |

## Modules

| Header | Twin | Content | Worst fuel per call (measured) | Where it runs |
|---|---|---|---|---|
| `params.h` | `params.py` | one versioned parameter set (`kParamsVersion`), every value labelled | - | - |
| `kit.h` | `kit.py` | a kit's worth from the engine design: attack resets, spell and area damage, stun, shield, heal, damage per round, camp damage per round, effective health, shard values, gold weight, exposure, front score; `front_order`, `can_swap` | all 13 designs 20k | the draft, or a champion's first turn |
| `sdk_bridge.h` | `designs.py` | fills the plain structs from `cambc.h` (designs, constants per passive tag) | in the 20k above | as above |
| `capture.h` | `capture.py` | who captures a dead group's reward. Mode 1 (default, LEARNED): the highest gold multiplier, then the nearest. Mode 0: the risk-matched gain | 1k | in game, every present body on the same inputs |
| `bag.h` | `bag.py` | the fight bar raised by the bag; bank before an avoidable fight; hunt a visible big bag only with local numbers; bank now when the team's bags win | under 1k | in game |
| `focus.h` | `focus.py` | kill value (the victim's bag + kill gold + the enemy's farming lost while it is dead) and target priority | under 1k | in game |
| `timing.h` | `timing.py` | who acts next between two opposing bodies (round parity, team, ranks); the "step in only when we act again first" gate | under 1k | in game |
| `tiebreak.h` | `tiebreak.py` | tiebreak detection with hysteresis, the risk-capped deferral, the final tribute window, the denial window | under 1k | in game |
| `assign.h` | `assign.py` | soft group ownership by list scheduling (gem-free groups lean to front bodies); the runner-up per group (the next owner); variants with one body left out | **56.1k** (51 groups, 5 bodies) | **the draft**, stored in draft memory (the OWN block); in game only as the one-off recompute of `docs/DRAFT_MEMORY.md` 7 |
| `swap.h` | `swap.py` | the expected-value swap check with hysteresis; a TinyML slot with zero weights (off) | under 1k | in game |
| `live.h` | `live.py` | the 64-bit live protocol: per body a claim, a progress code, a heartbeat and a flag; a plan cursor and a tiebreak bit; the per-turn layer (`LiveState`, `live_observe`, `live_compose`: who is live, with one round of doubt after a lost turn; the team bits to the lowest live slot) | 708 per body-turn with the two host calls | in game, every turn |
| `live_sdk.h` | (checked in the test) | `live_read` / `live_write` of the 8 shared bytes; `live_init`: our slot from the allies' body types | in the 708 above | in game |
| `nav.h` | `nav.py` | progress monitor, loop guard, target hysteresis | under 1k | in game |
| `nav_sdk.h` | (checked in the test) | local detour on host distance fields: walls + units, a field of radius 3-5 | 9k median, 17k max | in game, only when stuck |

The fuel numbers come from the engine test on the 40 official maps (`test_teamplan.py`, last run Oct 24 after the runner-up output was
added). "Under 1k" rests on its fixed sweeps: timing, bag, focus, tiebreak, live and nav cost tens of fuel per call, hashing included;
`swap_check` costs under 800.

**How a draft write fits** (the OWN block in the v10 test, TEAMPLAN.md 10, 16:35):
- turn 1: 138k;
- later turns: 48-65k, leaving at least 24k of the 100k after v10's own pick.

## Labels

Every number in `params.h`, and every result, carries one label:

| Label | Meaning |
|---|---|
| COMPUTED | from the engine or the rules |
| LEARNED | fitted to current-patch top-team games; the source is named in the comment |
| ASSUMED | a starting value; `ISSUES.md` (teamplan section) lists them all |
| SIMULATED (v10) | a result on the GOD v10 test copy. It says how a rule changes v10's games, not how it plays on the ladder |

## Commands

```bash
# engine test: 7,939 results bit-equal between C++ and Python (40 maps x 2 teams, the live bytes included), fuel per part; exit 1 on any failure
python3 -I tools/teamplan/test_teamplan.py [--maps 'maps/official/*.map26a'] [--jobs 4]
python3 -I tools/teamplan/test_teamplan.py --dump-designs     # after a patch: rewrite experiments/results/teamplan/designs_3_0_5.txt
python3 -I tools/teamplan/kit_table.py --md                   # the kit table

# the GOD v10 test copy (bots/<name>, git-ignored); with no KEY=VALUE every tp_* switch is 0 and it plays v10's games
python3 -I tools/teamplan/prepare_v10.py --name _tp_bag tp_bag=1
python3 -I tools/teamplan/make_forced_v10.py --name _tp_v10F1 --slot 1   # opponent family 2

# batteries (tools/ledger.py underneath: release mode, both sides, a cut run resumes)
python3 -I tools/teamplan/batteries.py [--maps 'maps/official/*.map26a'] [--jobs 4] [--only NAME,...] [--report-only]
python3 -I tools/teamplan/batteries.py --confirm --slots 0,1,2,3,4,5,6,7   # the two leads vs v10 forced to roster slots 0-7

# offline checks on replays
node tools/teamplan/capture_ctx.mjs --lag 8 experiments/ladder_oct24/raw > CTX.jsonl
python3 -I tools/teamplan/capture_check.py CTX.jsonl
node tools/teamplan/capture_rows.mjs experiments/ladder_oct24/raw > ROWS.jsonl
python3 -I tools/teamplan/ladder_roles.py --caprows ROWS.jsonl --out experiments/results/teamplan/roles_ladder.md
```

Outputs go to `experiments/results/teamplan/` and the ledger `experiments/results/ledger_v3_0_4/` (`_tp_*` rows).

## Using the library in a bot

1. Copy `cpp/teamplan/` into the bot's `src/teamplan/`, the way `prepare_v10.py` does, and include the headers.
2. Only `sdk_bridge.h` and `nav_sdk.h` include `cambc.h`. Everything else takes plain structs (`Design`, `Consts`, `Kit`, `AGroup`,
   `CaptureCand`, ...), so it compiles and tests without the engine.
3. **In the draft**, after the pick:
   - kits for the roster (`compute_kit`);
   - `assign_groups` for the bodies picked so far, written to draft memory (`docs/DRAFT_MEMORY.md`).
4. **In the game**:
   - read the blocks;
   - recompute nothing over 20k;
   - call the cheap modules every turn;
   - the live bytes: `live_init(L)` on the first turn; then at the start of every turn `live_observe(L, live_read(), round)`, decide,
     and `live_write(live_compose(L, claim, status, flag, cursor, tiebreak))`. A dead body keeps its turns (it may shop) and publishes
     claim 63.
5. **No champion names**:
   - champions enter through their designs, `passive_type` and the SDK constants;
   - `sdk_bridge.h` finds a passive's constant by the passive tag, so a passive moved to another champion still works.

## After a patch or on new maps

1. Rerun `test_teamplan.py --dump-designs`, then `test_teamplan.py`. A changed design changes every kit value by itself, and the twins
   follow the new designs file.
2. Refit the LEARNED values on new top-team games:
   - `team_rate` and `hazard`: `ladder_roles.py`;
   - `capture_mode`: `capture_check.py`;
   - `gold_gems`: mapintel's `econ_learn.py`.
3. The ASSUMED values are settings for the batteries. Rerun `batteries.py` on the new map pool before trusting them.
4. New maps need nothing in this library: the groups, walks and the ownership plan are computed from the map at draft time.
