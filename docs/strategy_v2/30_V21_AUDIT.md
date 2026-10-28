# GOD v21 and the GitHub state: what is wrong (audit, Oct 28)

The user (Oct 28): "analyze the current GitHub state and bot v21 and give a detailed report of everything wrong with it".

**Sources**:
- GitHub `main` at `ca444e6` (Oct 27, session 23 start);
- `bots/god21` and `submissions/history/god_v21_20261027.zip`;
- docs 28-29 and `docs/plans/god22_plan.md`;
- new measurements made for this report on cambc 4.0.0 / engine 2.0.0, in release mode, on the 70-map pool `maps/s3` (byte-identical to the platform pool fetched on Oct 28).

Data and scripts are in `experiments/v21_audit/`. The ledger rows are `experiments/results/ledger_v4_0_0/god2{0,1}_vs_gpta75.jsonl`.

## 0. Verdict in five lines

1. **v21 changes almost nothing.** It is GOD v20 with one setting changed (`g20_pack_until` 400 -> 2000). After round 400 its bodies follow a pack leader in only 5-6% of body-turns, and they spend their time exactly as v18 does.
2. **It does not touch why we lose.** The top teams beat us on farming volume:
   - they capture about 2x our gems;
   - they make their first capture 70-130 rounds earlier;
   - they die about half as often.

   v21 farms 12.6% of body-rounds and walks 61%. With an enemy within 8 tiles it farms 5.1% and walks 74.8%, even though it is locally stronger in 68% of those rounds. These are v18's numbers to the decimal.
3. **It shipped on evidence that cannot see it.** Against v18 the local results are level within noise:
   - 158/290 (sign p 0.11) in the ledger;
   - today 78/140 (p 0.18), +82 gems a game [-23, +187].

   The null control moves results by up to 41-50 gems. Every local game is a mirror draft against our own code family. The ladder premise (v20 60% vs v18 48%) is p ≈ 0.08 and unpaired.
4. **It is out of date for patch 2.0.0.** It drafts with a pre-patch per-map pick table and buys none of the new emblems (Capture, Tribute, Prospector, Hunter). It never drafts Cassi & Issac, although Cassi got +43% focus and IC drafts them.
5. **It inherits v18's team-play defects** (fights judged from one body's sight, retreat cascades, lone responders, the recall bait every turn, the opening fuel loss). Its new code also runs every turn even with its switches off.

v21 went live as website v78 and was rolled back to v18 (v75). **No v21 ladder game is saved in the repository**, so how it lost on the ladder cannot be analysed from here. This container has no `cambc login`; fetching those games needs the user's login.

## 1. What v21 is (provenance: correct)

- `submissions/history/god_v21_20261027.zip` (sha256 e32e6531…) = `candidates/god21_wholepack_20261027.zip` = `bots/god21/src`, byte for byte.
- It builds on cambc 4.0.0 (18 warnings, all `-Wconstant-logical-operand` from compile-time switches: harmless).
- v21 = v20 (`bots/god20`) with these changes:
  - `g20_pack_until` 400 -> 2000: the adaptive IC-style pack all game;
  - three new switches, all off: `g21_lock`, `g21_noback`, `g21_fort`;
  - trace codes (`dbg_eng`).
- v20 = v18 with:
  - the adaptive pack (`g20_pack` 2, `g20_adapt` 2: on for 30 rounds after this body sees 3 enemies within 3 tiles of each other, or after an ally's fresh DANGER alert);
  - `mi_capture` 2;
  - `g18_rich` 1.
- Live now: `submissions/god.zip` = `god18.zip` = `bots/gpta75` = GOD v18 (website v75). That is correct.
- `bots/god18` is not the live bot: it is v18 plus the inert `g18_rich` code. The repo ledger's "vs god18" cells, used for v19-v21, are against that copy. Today's runs use `gpta75`, the live zip.

## 2. v21's one change, measured (trace build, 70 maps, v21 as team A vs v18, debug mode)

| | r0-399 | r400-999 | r1000+ |
|---|---|---|---|
| body-turns in pack mode, v21 | 11.7% | 15.1% | 17.3% |
| ... switched on by an enemy pack seen | 10.4% | 12.7% | 15.7% |
| ... switched on by an ally's DANGER alert only | 1.3% | 2.4% | 1.6% |
| body-turns actually following a leader, v21 | 3.6% | **5.4%** | **6.1%** |
| following a leader, v20 (pack until r400) | 3.5% | 0 | 0 |

- **Following comes in short bursts**: median run 9 rounds, and 31% of runs last 3 rounds or less. The target changes in 4.6% of consecutive follower turns and the leader in 3.3%.
  - This is the "pack" the user saw split: it forms for a few rounds, then dissolves.
- **Pack mode is decided per body, from its own sight.** `pk_mode()` (`brain.cpp` 6850) and the enemy-pack detector (1065) use only what this body sees this turn.
  - Vision is not shared, so two bodies standing side by side can be in different modes.
  - The leader may not be in pack mode while its followers are, so it picks targets for itself, not for the pack.
- **The leader is the lowest SDK index with a claim** (`prepare_scoring`, 6902). The leader is chosen by index, not by role, health or position.
  - A carry can lead the pack.
  - When the leader banks, heals or dies, leadership jumps to the next index and the pack's target jumps with it.
- **The time budget is unchanged** (session-17 `timebudget.mjs` on the release replays, side A, 70 games each):

| | farm | fight | walk | on camp | idle | dead | walk with an enemy within 8 | with an enemy within 8: farm / walk |
|---|---|---|---|---|---|---|---|---|
| v21 | 12.6% | 2.8% | 61.4% | 4.5% | 7.8% | 10.9% | 22.4% | 5.1% / 74.8% |
| v20 | 12.5% | 2.7% | 60.8% | 4.8% | 8.0% | 11.3% | 21.3% | 5.1% / 74.7% |
| v18 (opponent) | 12.6% | 2.7% | 61.1% | 4.5% | 7.9% | 11.1% | 22.3% | 5.3% / 74.8% |

  For comparison (doc 29, v20 vs Mite): Mite hits camps 15.2% of body-rounds (we 10.4%) and is dead 6.3% (we 13.5%). Session 17 measured that the top teams farm 15.9% of rounds with an enemy within 8.

## 3. Strength, measured

| | games | wins | 95% | maps 2-0 / 0-2 | sign p | gems a game [95%] | deaths us-them |
|---|---|---|---|---|---|---|---|
| v21 vs live v18 (`gpta75`), today, 70 maps x 2 | 140 | 78 (55.7%) | [47.4, 63.7] | 18 / 10 | 0.18 | +81.7 [-22.5, +186.5] | 1,443-1,642 |
| v20 vs live v18, today | 140 | 72 (51.4%) | [43.2, 59.6] | 17 / 15 | 0.86 | +35.5 [-62.1, +135.8] | 1,496-1,558 |
| v21 vs `god18` (repo ledger, s3 + var17 + gen2) | 290 | 158 (54.5%) | [48.7, 60.1] | 35 / 22 | 0.11 | doc 29: +4 [-35, +45] paired to the unchanged build | 2,952-3,065 |
| v21 vs the IC clone `_icc2` (repo ledger) | 140 | 92 (65.7%) | [57.5, 73.1] | 31 / 9 | 0.0007 | doc 29: -19 [-87, +46] paired to v20 | - |

**Why none of this predicts the ladder**:
- **Mirror drafts**: v21 drafted the same roster as v18 in 140 of 140 games, so a local A/B tests only the in-game brain, against itself.
  - Our drafts: Heart of Ruin, Marcella, Ryth, Vendetta, Vesper 80 times; subsets on the 3- and 4-champion maps; Varg 4 times.
- **Per-map results flip by chance.** islands is 0-2 for v20 and 2-0 for v21, and treasure-box flips the same way, although v21's pack acts in about 5% of late body-turns.
  - Session 22's null control (v18 vs the same play, rebuilt) moved by up to 41-50 gems.
  - So nothing within about ±50 gems is real locally.
- **The "IC clone" is not IC.** Doc 28: "our brain with IC's drafts and a pack is not IC". v18 already beats it 85/140, yet the real IC beat v20 63-7.
  - No build recipe for `_icc2` is committed (only its ledger rows), so it cannot be rebuilt.
- **The ladder premise is weak.** "v20 39/65 = 60% vs v18 100/210 = 47.6%" is p ≈ 0.08 (two-proportion test). The two samples are not paired, come from different days and opponents, and vary in rating.
  - On the 70-map unranked groups v20 was no better than v18 against IC: 7/70 vs 8/70.
  - v21 was never played against IC, Mite or Trzy Kwaterki before it went live.

## 4. Out of date for patch 2.0.0 (Oct 26: engine 2.0.0, CLI 4.0.0)

- **The draft uses pre-patch data on 40 maps.**
  - `mi_pick` 3 (`draft.cpp` 692-697) adds the strong teams' pick rate per map from `known_maps.h`.
  - That table was generated on Oct 24 from engine 1.0.3 ladder games, before the 2.0.0 balance. Its comment calls it "pre-patch".
  - It fires on the 40 old maps, which are byte-identical in today's pool. On the 30 new maps it does not fire.
  - Its own measurement was "prior everywhere: old maps +185, new maps -85": it helps only where it was selected.
  - It is also a per-map table, against the standing rule "no per-map tables or fixed drafts".
- **The draft model's weights** (`pd_stat` 3, `pd_w_*`) were fitted on engine 3.0.4 games. The champion features adapt to the new designs, but the weights do not.
  - The draft never takes Cassi & Issac, although Cassi's focus rose 70 -> 100 (her damage spell is 2.0 x focus) and IC drafts C&I.
  - Doc 25 measured C&I-for-Vesper on our brain at -140. That may say more about how our brain plays C&I than about the pick.
- **None of the new emblems are bought.**
  - The new families: Capture (capture 5 -> 3 turns), Tribute (-33% tribute time), Prospector (+25% from clusters), Hunter (+50 gold a kill), Skirmish, Greed, Collectors.
  - `g18_capture`, `g18_tribute`, `g18_greed` and `g18_treasure` exist but are off ("level or worse" on the mirror tests).
  - Capture and Tribute speed up exactly what the top teams beat us on: captures and banks.
- **Treasure (gold bonus 20% -> 10%) is still in the build lists of several champions.** Those lists are typed per champion (`build_for`, `brain.cpp` 76-440; ISSUES #44).
- **An ally's camp damage uses typed multipliers** (`ally_dps_on`, `brain.cpp` 5740-5743: 3.4 x focus for Stellar, 2.0 for Cassi, 1.5 for everyone else). `ally_kit` is 0, so this is ISSUES #39, still open after two balance patches.
  - Join and kill-time estimates are wrong for every kit whose spell is not a 1.5 x focus damage spell.

## 5. Code defects in v21 (file:line in `bots/god21/src`)

1. **Fight odds from one body's own sight** (`combat()`, 3528-3544). An ally counts as support only if this body sees it.
   - An ally that is walking away is dropped, so one leaver lowers everyone's odds: the retreat cascade.
   - Rallies are answered by single responders (`respond_to_alert`, 5501).
   - These are the user's "champions go alone into fights" and "fights split" (`docs/plans/god22_plan.md` lists them in v18; v21 has the same code).
2. **The recall bait every turn** (`g17_bait` 1; start 1351-1364, cancel 1099-1114).
   - Every body ends every free turn recalling and cancels the recall the next turn: the "stutter" in the viewer.
   - It "won" locally only because the local opponents are our own code family, and our brain posts a recalling carrier as an OPPORTUNITY and chases it.
   - The real IC does not chase baits like that (doc 29: IC does not use it, so we have no evidence it pays against IC).
   - Cost: a host call to recall and one to cancel, every turn. If a cancel fails, the body is left channelling (god22 plan, Ryth-stuck cause 5).
3. **Capture-recalls at high health** (`cap_recall_gold` 60, `brain.cpp` 7509). Any capture that leaves 60 gold sends the body home to shop: 12.8 recalls a game start from 80% health or more.
   - The top teams keep 300-400 gold unspent at r800 (we keep 60): they do not go home for small purses.
   - The cuts tried locally lost, measured on the same mirror tests.
4. **"Off" code still runs every turn.**
   - Two `bc::bitboard` objects are allocated and cleared by a host call (`sdk_Bitboard_Zero`) on every body-turn (1183, 1230), whatever the switches. Host bitboard operations cost up to about 2.5k fuel on 100x100 maps (MAPAnalysis fuel facts).
   - There are also `g21_start_pos` bookkeeping and the `dbg_eng` writes.
   - So v21 with all `g21_*` switches off does not replay v20's games (doc 29's null control: -17 / -41 gems). Its measurements mix a chaotic fuel effect into the switch effect.
5. **A per-map fingerprint table in the zip.** `pack_maps.h` holds 21 sprint-3 maps "where the pack beat v18 locally". It is dead (`g20_pack_maps` 0), but it is a per-map table in the submission, against the standing rule.
6. **The legacy name-based recogniser** `official_map()` (`draft.cpp` 239; the 17 maps of Oct 17) is still compiled in, used only by proxy build styles.
7. **Corrupted parameter comments** (`params.h` 1040-1076):
   - `g20_modes` lost its comment, which now sits at the end of `g21_noback`'s comment;
   - `g20_pack_until`'s comment is duplicated.

   Harmless to play, but the switch documentation is wrong.

## 6. Fuel and lost turns (release, today: 140 games per bot vs live v18)

| | lost turns after round 3 | rounds 1-3 | faults |
|---|---|---|---|
| v21 | 589 (4.2 a game) | 442 | 0 |
| v20 | 728 (5.2 a game) | 442 | 0 |
| v18 (opponent in both runs) | 555 / 586 | 442 | 0 |

- **road-of-riches** (51 groups) loses 104-202 turns per team per game in every version; vault 28-79; fracture 20-98; islands 14-54. Group scoring on many-group maps runs out of fuel.
- **The opening on the large maps**: all 5 bodies lose 2 turns each in rounds 1-3 (10 per team on big-world, islands, road-of-riches, ambush, monolith, quadrants).
  - In a mirror game both teams lose them, so local tests cannot see it.
  - Against a top team whose bodies move on round 1 we start 2 rounds late.
  - Patch 2.0.0 raised the **draft** first-turn fuel x10, not a champion's first turn.

## 7. What is wrong with the GitHub state

1. **`submissions/BUILDS.md` says v21 is live** ("website v78 ... live from Oct 27 09:31 IST"). AGENTS.md (session 23) says v78 was rolled back to v75 = v18, and `god.zip` is v18. The BUILDS row is stale.
2. **`tools/setup_session.sh` installs cambc 3.0.5**, the old engine, while the game is on 2.0.0 / CLI 4.0.0 (`cambc.toml` says 4.0.0).
   - A new container that runs it plays the wrong engine.
   - In this container a plain `pip install cambc==4.0.0` also stalls: pypi is in the proxy's no-proxy list. `env -u no_proxy -u NO_PROXY pip install ...` works.
   - The SDK has to come from a scratch `cambc init`.
3. **The main test opponent cannot be rebuilt.** The IC clone `_icc2` has no recipe in `tools/` or `experiments/`, so doc 28-29's IC-clone numbers cannot be reproduced.
4. **No v21 ladder record.** v78's games were never fetched or saved, so the one real test of v21 is lost.
5. **ISSUES.md stops at v14** (Oct 25), and **SUGGESTIONS.md at Oct 24**.
   - Missing: the v15-v21 hardcoding (the `pack_maps.h` table, the pre-patch pick prior `mi_pick` 3, typed ally damage, Treasure after its nerf).
   - Missing: the dozens of rejected ideas of docs 22-29.
6. **Two docs share number 28** (`28_IC_RANKED_STUDY.md` from the remote session, `28_V74_LADDER_STUDY.md` from the PC session).
7. **Nine branches on GitHub**: `main`, `god-dynamic-draft-on/off`, `god-opponent-model-on/off`, `god-v10-on/off`, `claude/nice-franklin-lgyb4x`, `claude/relaxed-volta-smlhdz`. The user asked for `main` only (earlier: plus two). The git proxy refuses deletions, so the user must delete them in the GitHub UI.
8. **Bot copies sprawl**: 14 tracked GOD copies (`god`, `god12`-`god22`, `god19pc`, `gpta75`) of about 15,000 lines each.
   - `god19` and `god19pc` are different bots with the same version number.
   - `god18` and the live `gpta75` differ (the inert `g18_rich` code), and the ledger cells named `god18` are not the live bot.
9. **About 150 commits named "ledger rows"** bury the real history. `experiments/` is 274 MB.
10. **Two clones diverged** (the user's PC and the remote sessions) and were merged by hand on Oct 27 (`ca444e6`). Session 23 is still running on the PC, so pushes from elsewhere can collide again.

## 8. What to do (in order)

1. **Get the ladder record of v78 = v21** (the user's login: `cambc matches` / `tools/paired_groups.py`) and analyse why it was rolled back before any v22 decision.
2. **Stop judging on mirror tests.**
   - Use `tools/paired_groups.py` (paired unranked groups vs IC / Mite / TK with the live bot as control) as the only ship gate.
   - Locally, measure behaviour (time budget, deaths after r500, first capture round), not wins.
3. **Attack the measured gap: farming through contact.**
   - With an enemy within 8 we farm 5% and walk 75%, even when locally stronger 68% of the time.
   - Fix the sight-only fight odds and the retreat cascade (5.1), then the single-responder rallies.
4. **Patch 2.0.0**:
   - test the Capture and Tribute emblems against the real opponents;
   - drop the pre-patch pick prior (`mi_pick` 0 or a refit on 2.0.0 ladder games);
   - read ally damage from the kits (`ally_kit` 1);
   - re-test C&I.
5. **Fuel**: the opening (2 lost turns per body on large maps) and group scoring on many-group maps (road-of-riches, vault).
6. **Housekeeping**:
   - fix the BUILDS row;
   - set `setup_session.sh` to 4.0.0;
   - commit the `_icc2` recipe;
   - bring ISSUES / SUGGESTIONS up to date;
   - renumber one doc 28;
   - delete the stale branches;
   - move `bots/god12`-`god17` and `god19*` to zips in `submissions/history/`;
   - squash the "ledger rows" commits into per-session commits from now on.

## 9. How the new numbers were made (reproduce)

```bash
pip install cambc==4.0.0          # here: env -u no_proxy -u NO_PROXY pip install cambc==4.0.0 --break-system-packages
cambc init --yes <scratch>; cp -r <scratch>/sdk <scratch>/cmake .   # SDK 4.0.0 (git-ignored)
LEDGER_DIR=<dir> python3 -I tools/ledger.py run god21 gpta75 --maps 'maps/s3/*.map26a' --jobs 4 --chunk 16 --release --keep <keep>
python3 -I tools/abstat.py god21 gpta75 --ledger <dir>
node tools/analysis/rollovers.mjs <keep>/god21_vs_gpta75/*.repl26a > roll21.txt; python3 -I experiments/v21_audit/rollsum.py <dir> 21
node <copy of god2_session17/tools/live/timebudget.mjs> 2001 <keep>/god21_vs_gpta75/*_A.repl26a > tb21.jsonl
# pack trace: bots/_t21 = bots/god21 + experiments/v21_audit/trace_patch_v21.diff + "#define G20_TRACE 1" atop brain.cpp
python3 -I experiments/v21_audit/run_trace.py _t21 gpta75 <out>; python3 -I experiments/v21_audit/pack_an.py <out>
```
