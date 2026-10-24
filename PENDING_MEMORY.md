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
- **Step 4 is done** (`TEAMPLAN.md` 10, 14:25):
  - the copy comes from `tools/teamplan/prepare_v10.py` + `tools/teamplan/v10_adapter.patch`;
  - with all switches off it plays v10's games, 80 of 80 identical;
  - the family-2 opponent is `tools/teamplan/make_forced_v10.py`; it plays the forced rosters in 80 of 80 games, and v10 wins 37 of 80
    against it.

## Left (updated 16:35)

1. ~~Step 4~~, ~~step 5 batteries~~, ~~the capturer check (task 20)~~, ~~the `tp_own` draft-fuel check~~: done (`TEAMPLAN.md` 10,
   checkpoints 14:25 to 16:35; table `experiments/results/teamplan/batteries_v10.md`).
2. **The confirmation battery** (running): `tools/teamplan/batteries.py --confirm`, i.e. `tp_bag`, `tp_own` and both together against
   v10 and v10 forced to roster slots 0, 1 and 2 (`_tp_v10F`, `_tp_v10F1`, `_tp_v10F2`); writes
   `experiments/results/teamplan/batteries_v10_confirm.md`.
3. **Step 6**: TinyML is not built. v10's live bytes have no room for per-body progress codes, so the expected-value swap check cannot
   run in v10. `live.h` gives a new bot that room. To be recorded as a verdict.
4. **Step 7, docs**:
   - `TEAMPLAN.md` section 11 (results and answers to the user's questions);
   - `tools/teamplan/README.md`;
   - `docs/DRAFT_MEMORY.md` final (measured OWN fuel, the fuel guard);
   - ISSUES (a teamplan section: the ASSUMED constants and engine assumptions);
   - SUGGESTIONS (the rejected ideas).
5. **Step 8**: the handoff prompt for the other Claude, given in chat.
6. **Delete this file** once 2-5 are done.

## Rules in force

- Commit and push to `main` at every step: `git pull --no-rebase` first, never force, no pull request.
- `bots/god` and `submissions/` stay untouched; nothing ships.
- No champion names or map identities in logic. Kill processes by PID only, never `pkill -f`.
- Few subagents.
