# Pending memory (team-play session, Oct 24): what is done and what is left

The user asked for this file on Oct 24 ("write all things done till now and what are left, push it, and delete it after all tasks are
done"). It is temporary: **delete it once every task in "Left" is done**. The full record is in `TEAMPLAN.md` (sections 1-10). For map
analysis, see `MAPAnalysis.md` 1.9.

## The user's requests in this session (Oct 24)

1. Use the 1,024-byte draft memory better.
2. Answer three questions:
   - should every body farm;
   - should farmers with gold engage the enemy;
   - should the frontliner take the gold, and should jobs be swapped when a frontliner lags (TinyML suggested, other techniques
     allowed).
3. Argue against every idea, and implement it only if it still wins against its alternatives.
4. Make the code modular and open to future patch notes and maps.
5. Decisions:
   - "Me, in the repo": I build here;
   - "do both offline and v10": tests offline and on a GOD v10 copy.
6. Read the uploaded Gone Fishin' 2023 postmortem and the others on battlecode.org/past.html.
7. Consider the pasted Unrolled BFS / Bug Nav / BugBFS excerpt, for map analysis and anywhere else it fits.
8. Note everything in the md files.
9. The tiebreak idea: "whenever you sense a tiebreaker then only we will submit the gems at last, else we will also be racing for
   finishing".
10. When done, give a prompt for the other Claude to implement the final draft-memory state.
11. This file.

## Done (all on `main`)

| Step | What | Where |
|---|---|---|
| 1 | Research written up: rules and SDK facts; 599 top-team games; the for-and-against table of every idea with its verdict; tiebreak mode (risk-capped); BugBFS mapped to CAMBC; 17 postmortems; the build plan | `TEAMPLAN.md` sections 1-9 (commit 2a29a25); `MAPAnalysis.md` 1.9; pointer at the top of `AGENTS.md` |
| 2 | Probes and offline checks (commit 84df669); details below | `tools/teamplan/capture_rows.mjs`, `ladder_roles.py`, `probe_nav.py`; `experiments/results/teamplan/` |
| 3 | The modules (commit edec6de); details below | `tools/teamplan/cpp/teamplan/`, `tools/teamplan/tp/`, `tools/teamplan/test_teamplan.py`, `tools/teamplan/kit_table.py` |

### Step 2 results

- **Turn order** (measured): champion turns alternate between the teams one body at a time, and the starting team swaps every round. So
  there is a double move at round boundaries.
- **Gold-only captures**: the replay decoder missed them. It now has an opt-in `--gold-captures`, which the other Claude has merged
  into its readers.
- **Role tables**: per champion, capture share, kills, death hazard and bag at death.
- **Navigation fuel**: a host distance field limited to radius 3 costs 1.2k + 0.4-3.5k fuel. An unrolled 7x7 BFS in wasm costs 10.8k.
  So navigation uses host fields.

### Step 3 results

- **Modules** (C++, header-only): `params.h` (one versioned parameter set, every value labelled), `kit.h`, `sdk_bridge.h`,
  `capture.h`, `bag.h`, `focus.h`, `timing.h`, `tiebreak.h`, `assign.h`, `swap.h`, `live.h`, `nav.h`, `nav_sdk.h`.
- **Python twins** of every module, and the engine designs file `experiments/results/teamplan/designs_3_0_5.txt`.
- **Engine test**: 2,080 results are bit-equal between C++ and Python on 40 maps x 2 teams.
- **Fuel, worst call**:
  - all 13 kits: 20k (in the draft);
  - capturer choice: 1k;
  - ownership plan: 54k (so it is computed in the draft and stored in draft memory);
  - local detour: 9k median, 17k max.

### Findings since the last commit (not yet in `TEAMPLAN.md`)

- **GOD v10 almost never shares a capture.** In 10 mirror games it shared 1.1% of capture events (1.01 bodies per capture); the top
  teams share 5.5%. So the capture rule (one body captures, the others move on) has nothing to save in v10, and it is not in the v10
  batteries. In v10 the useful part is which body goes to which group: `tp_own`.
- **v10 already has three of the planned rules**: the turn-order fact (in `update_priority`), the endgame bank window (in `tribute()`),
  and "bank now if it wins" (`win_bank` + `team_bank`).
- **The v10 test copy `bots/_tp_v10`** (git-ignored; `bots/god` is untouched) has five switches, all 0 by default:
  - `tp_focus`: kill-value targeting;
  - `tp_bag`: a fight bar that rises with the bag;
  - `tp_timing`: step into an enemy's reach only when we act again first;
  - `tp_tiebreak`: tiebreak mode, plus the cap `tp_tb_cap`;
  - `tp_own`: soft group ownership through a draft-memory OWN block at offset 8, plus `tp_own_bonus`.
- It builds. The control check (80 games, all switches off against v10) is running; the first readout was empty because of a ledger
  release-flag query, not the games.
- The edit script that made the copy is in my scratchpad. Its result becomes `tools/teamplan/v10_adapter.patch` plus
  `tools/teamplan/prepare_v10.py` (left, step 4).

## Left

1. **Step 4**:
   - commit `tools/teamplan/v10_adapter.patch` and `tools/teamplan/prepare_v10.py`;
   - confirm that all switches off plays v10's games (80 of 80 identical: same winner, rounds and gems).
2. **Step 5, batteries**: each switch alone, then all combined, on 40 official maps x 2 sides.
   - Family 1: against GOD v10.
   - Family 2: against a v10 copy forced to the strong teams' roster per map (`tools/mapintel/data/battery_rosters.json` rosters[0],
     through mapintel's `force_roster.h`).
   - Stats: `tools/abstat.py` / `tools/abmargin.py`, labelled SIMULATED (v10).
   - Also a tiebreak variant with the cap at 150, the closer form of the user's "hold the gems" idea.
3. **Step 6**: TinyML only if the expected-value swap check fails. It cannot be tested in v10, because v10's live bytes have no room
   for per-body progress codes. `live.h` gives a new bot that room.
4. **Offline check**: does the risk-matched capturer match the top teams' choices on the 25 raw replays? (task 20)
5. **Step 7**:
   - `docs/DRAFT_MEMORY.md`, the final byte map with measured fuel: header and table of contents at 4; the blocks TEAM, OWN, BODY,
     CONT, CODEBOOK, ENEMY, NAV and DEBUG; mapintel's block kept at 512-863;
   - `tools/teamplan/README.md`;
   - ISSUES entries;
   - the results in `TEAMPLAN.md` section 11, with checkpoints.
6. **Step 8**: the handoff prompt for the other Claude (implement the final draft-memory state + static navigation hazards in the
   mapintel library), given to the user in chat.
7. **Delete this file** once 1-6 are done.

## Rules in force

- Commit and push to `main` at every step: `git pull --no-rebase` first, never force, no pull request.
- `bots/god` and `submissions/` stay untouched; nothing ships.
- No champion names or map identities in logic. Kill processes by PID only, never `pkill -f`.
- Few subagents.
