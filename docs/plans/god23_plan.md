# GOD v23 plan and handoff (Nov 2, 2026) — read this first if you are continuing this work

Goal set by the user: build a new bot (GOD v23) from the live bot's lineage that fixes the ranked losses, put it live on the ladder,
keep it live only while it does better than the previous live version (else roll back and fix), and **finish under rank 30 globally**.
Standing rule changed on Nov 2: the user explicitly allowed this agent to `cambc submit` / `cambc submissions activate` as part of the
ladder loop (earlier sessions were forbidden to). Still: commit/push only when the user asks; no per-map tables or fixed drafts by map name.

## STATUS (newest first)

**Nov 3, 01:25 UTC — LIVE: website v87 = `bots/g23r`** ("GOD v23 rc2: v84 + caught-ally rescue (g23 mode 2 bits 64)"), activated
01:21:19Z (rank 69 / 2000); state `previous` = v86 (to fall back to the user's version use `rollback --to 85`). Why: v86 (`g23rc`,
rescue + commit) paired on 50 groups = net +6 of 250 vs v84 (p 0.53), +3 of 150 vs v85 → WAIT; locally the commit was worse on both
pools (g23r s4 +112 / held-out +31, deaths 7.8 vs 9.2 / 8.3; g23rc +42 / −2): the commit skips the strike-first holds, so rescuers hit
second (hitting first is the z +11.6 factor of the fight study) — the stale-d theory of 00:45 was wrong (g23r has the refreshed d and the
fewest deaths). **Next at 02:02Z (quota reset):** `ladder_loop.py paired-run --plan experiments/ladder_nov2/paired_c2.json --max 50
--execute` (its first 50 groups carry v84 `old`, v85 on 30, and v86 as columns, so `three_way.py experiments/ladder_nov2/paired_c2.json`
gives g23r vs v84 / v85 / v86 on the same games). **TOL:** the deadlock (a seen respawning P0 with timer 0 = blocked by our own bodies on
its spawn tiles, counted alive) is fixed; still −135 on 108 games (`_85tolc`): on 01hooks P0 (22 gems) is held by the enemy 68% of turns
and the roster sends 2-4 bodies into it (25 deaths vs 17). Conservative variant `_85tolk` (no contesting: `g23_hold_extra −10`, primes
only ≥ 36 gems and dA ≤ dB, `g23_prime_sticky 6`) on the panel now (`g85_run14.log`). Helpers: `next_plan.py` (results of a replayed
candidate become a column), `three_way.py` (compares with every column).

**Nov 3, 01:05 UTC — LIVE: website v86 = `bots/g23rc`** ("GOD v23 rc1: v84 + caught-ally rescue that commits (g23 bits 192)"),
activated 01:00:56Z by this agent (rank 72 / 1990 at activation); `previous` = v85 (rollback: `ladder_loop.py rollback --execute`).
Local: panel +42 (deaths 8.4 vs 8.7), held-out 103 maps 95/206 −2 (deaths 8.0 vs 8.4), 0 faults. Paired groups queued 01:02-01:05:
all 30 of `paired_cand_shared30.json` (3-way: v84 old, v85, candidate) + 20 of `paired_cand_rest71.json`; quota resets 02:01Z → queue
the other 51. Report: `python3 experiments/ladder_nov2/three_way.py experiments/ladder_nov2/paired_cand_shared30.json
experiments/ladder_nov2/paired_cand_rest71.json`; rules in `DEPLOY_CHECKLIST.md` (rollback if net flips vs v84 < 0 with p < 0.2, or ≥ 6
net worse than v85 on the shared 30, or ranked ≥ 40 games below Elo expectation by > 1.5 SE). **`_85tolb` (TOL alone after the 15 + 1
fixes; 16th = the altar-lock tribute timer t4 shared bit 7 of bytes 2-5 with the clock, now off under g23_tol) −190 [−272, −107]**,
monster damage 85k vs 104k, gold 5137 vs 6372: still broken (bodies not farming) → trace before any further TOL work.

**Nov 3, 01:00 UTC.** Ladder: rank 67, rating 2003, v85 live (100 ranked since 21:15Z: 62/100, Elo-expected 54.6, z +1.5, perf 2057).
Panel vs god84 since 23:40 (172 games each, `g85_run7..11.log`): `_85v2n` one-step +42 (deaths 7.0 vs 7.5); `_85r` **rescue** (bit 64)
+70 (deaths 8.0 vs 8.7); `_85r2` rescue + one-step −2; `_85dr` / `_85draft` v84's `v23_draft` +72 / +67 (**the same games**: 171 of
172 identical, so one sample, not two); `_85sf` fixed spawn-farm −49; `_85dv` dive filter −22; `_85cz` camp zone −57; `_85ca` rescue +
draft −44 with **deaths 10.2 vs 8.4**; `_85cb` rescue + one-step + draft +32, deaths 9.5 vs 8.6. `_85tolb` / `_85x` / `_85m` / `_85v2b`
were never created (BUILD FAILED = missing dir) → **TOL after the 15 fixes is still unmeasured** (queue it). Noise: ±80 at 95%; the
picked singles regress (combinations of the best singles all come out lower).
**Root cause of the rescue deaths (found 00:45):** `_85r` was built before the stale-`d` fix; `_85ca`/`_85cb` after it. With `d`
refreshed to the rescue target, combat()'s later approach holds (fz_engage, chase guards, calm 4, fwalk, strike_first 1/2) cancel or
*hold in place* a rescue — the body stands next to its caught ally inside enemy reach without fighting. With the stale `d` (old target)
the holds mostly did not fire. Fix: **bit 128 = the rescue commits** (`g23_rescue_now` set by g23_veto; `rescue_commit` skips those
holds). Inert when off (verified: all-off build `_85n5` = v84's games on 3 maps, every statistic identical). Candidates `g23r` (bits 64:
refreshed d, no commit) and **`g23rc` (bits 192)** on the panel now (`g85_run11.log`). Fuel (82 games of `_85cb`, mode 2 + rescue):
p99 78.9k = v84's 78.9k. `tools/g23port` regenerated after the edit (reproduces god85 exactly).
Draft facts from the ladder: v84 and v85 both play HoR (id 11) every game + Vesper (1) / Vendetta (2) / Ryth (0) / Marcella (6), Varg
(9) rarely; `v23_draft` brings Tavi / C&I instead (never played live). Next: `g23rc` held-out → deploy → paired groups
(`paired_cand_shared30.json`, then `paired_cand_rest71.json`) per `experiments/ladder_nov2/DEPLOY_CHECKLIST.md`; locally meanwhile
`_85tolb` (TOL alone, fixed).

**Nov 2, 23:20 UTC.** Website **v85 "GPTA 8.1.0 Shastra" (god29.zip) is live** since ~21:15 UTC, uploaded by the user's other session
(not by this agent). It is doing well: 40/60 ranked (Elo-expected 34.0); team rank 71, rating 1992 (was 89 / 1946 on v84). Its source is
not here yet (asked the user for god29.zip). **Naming trap: `bots/god85` is THIS agent's work (= website v84 + g23 modules), not website
v85.** When god29.zip arrives: unzip to `bots/god29` (strip CRLF), then `tools/g23port/apply.sh god29 g23on29` ports every g23 module and
hook onto it (patches made from god84 → god85; `tools/g23port/g23.cpp` is a snapshot: re-copy it after editing bots/god85/src/g23.cpp).
Any candidate must now beat **v85**, locally and on the ladder.
Panel vs god84 (172 games, maps/s4, both sides; `/home/claude/analysis/g85_run1.log`, `g85_run2.log`): `_85null` +25 (level), `_85tol`
**−341** (the PRIME executor sends the roster onto P0 without the scorer's survivability/trip checks, and the in-time constraint scores
every other group −1 when P0 is alive or a reward: bodies die on heavy groups (elk_arena 53 deaths, 0 gems) or idle at the rally; monster
damage −30%) → OFF, redesign or drop; `_85sf` −94 was the spawn-farm bug (safety() returned before rest-on-spawn on every map; fixed,
re-running); veto bits alone: lure −26, **one-step +53 [−21, +125]**, chase −9, their-half −10, second wave −20; leave step, bank, draft,
combined, held-out confirmation of one-step (maps/heldout = gen2+gold3+var17, 103 maps) are queued (`queue3.sh`, `queue4.sh`).
**Nov 2, 23:40 UTC — code review (independent agent) of every g23 hook; fixes applied to bots/god85:** (1) with `g23_tol` the clock bits
were read back as the team STANCE by every body (comms.cpp: random PUSH/GROUPED) — the main cause of `_85tol` −341; (2) v27_watch
blacklisted P0 while bodies waited at a rally; (3) PRIME walked off captures / half-killed groups; (4) a live P0 skipped the scorer's
safety checks (now `group_score(P0) > 0` is required); (5) the in-time constraint and the rally fallback applied while P0 was alive /
a reward, and replaced healing; (6) contested + outpowered sent the whole team (now nobody); (7) stale own model beat a fresh clock;
(8) a clock nobody refreshed for 85+ rounds decoded as "respawning"; (9) the warden's ward was re-thrown; (10) `g23_keep_farm` started
true; (11) mode 2 broadcast FIGHT for fights a later veto cancelled; (12) the leave step did not call `avoid_note` (v27_avoid);
(13) "on spawn" alone forced FIGHT; (14) staging never re-armed; (15) the two helpers moved out of brain.cpp's anonymous namespace
changed v84's code generation: they are back, g23.cpp has private copies. **Verified: all switches off now plays exactly v84's games**
(3 maps × both bots identical). `tools/g23port` regenerated (now also patches comms.cpp). `_85c1` (one-step + spawn-farm + exact + msg,
old source) +13. Queued with the fixed source: isolation (`_85v2n` one-step alone, `_85x` exact, `_85m` msg), `_85sf`, `_85v2b`,
`_85tolb` (TOL alone), `_85dr` (v84's draft).

**Ladder loop tool** (`experiments/ladder_nov2/ladder_loop.py`, docs `LADDER_LOOP.md`, written by a helper agent; read-only paths
tested for real, write paths only in dry-run / against a fake CLI): snapshot / adopt / deploy / paired-run / paired-report / verdict /
rollback, platform-changing commands only with `--execute`. Platform fact: a live version's `statusAt` keeps moving; its activation time
is when the version it replaced went inactive. State recorded with `adopt`: v85 live since 21:15:46Z (v84 inactive then). Caveat: v73's
status changed at 22:56:35Z, so v73 may have been live 21:15–22:56 (ranked 35/50 then; 13/25 since 22:56; drafts look like v85's).

Paired ladder test v85 vs v84 (30 of v84's unranked groups re-played with v85 live, 150 games): 68 vs 64 wins, flips 22 L→W / 18 W→L
(level; p ≈ 0.64). Calibration for every later A/B: ~27% of paired games flip between two versions, so 150 paired games resolve about
±12 net flips (±8 pp) at 2 SE. v84's banking module alone (`_85bank` = `v23_bank 1`) +22 vs god84 (level with `_85null` +25).
Leave step (bit 32, `g23_leave` instead of v75's flee when in reach) **−106 [−188, −30]** → OFF (it steps toward an ally up to 12
tiles away without checking that the path leaves enemy reach; v75's `toward_help` only moves to a helper arriving within 3 rounds and never
into more reach).
Subagents launched Nov 2 (code review of g23 hooks; death/fight analysis of 128 ladder replays → `experiments/ladder_nov2/agent_fights/`;
`experiments/ladder_nov2/ladder_loop.py` automation) were cut by the usage limit and resumed at 23:16 UTC.

## 0. State of the world (Nov 2, 17:30 UTC)

- Platform login: done inside this container (`cambc login`, device flow; session valid 7 days from Nov 2 17:15 UTC). If it expires,
  run `cambc login < /dev/null > /tmp/login_out.txt 2>&1 &`, read the URL from the file and send it to the user to approve.
- Team: **HouseOfCoders**, teamId `5a103c90-b00b-4d46-8ace-6a3bb058dc72`. Ladder: **rank 86 of 825, rating 1955**. Rank 30 ≈ 2164,
  Mite 2552 (rank 1), Intercontinental Fish 2546 (rank 2). Ranked matchmaking pairs us with ranks 61-150; today's record 154/305 (50%).
- Live submission: **v84 "GPTA 8.0.0 SHASTRA"** (`cambc submissions list`). Its source is NOT in this repo (repo has up to v79 =
  `bots/god22u`; v75 = `bots/gpta75` = GOD v18). The user was asked (17:20 UTC) to attach the v84 zip. Until it arrives, every
  local comparison uses `bots/gpta75` (v75) as the reference; when it arrives: unzip to `bots/god84` (strip CRLF, see §4), rerun
  the null check and the panel against it, and re-base the v23 switches on it if it is stronger than v75 locally AND on the ladder.
- Map pool: now **86 maps** (16 new `03_*` maps + `00happy_halloween`), pulled with `cambc maps pull` into `maps/` and copied with
  normalised names to **`maps/s4/*.map26a`** (use this pool for every local run; `maps/s3` is the old 70).
- Our matches: `experiments/ladder_nov2/matches_me.jsonl` (fetch_me.py, cursor-paginated); the last 60 ranked losses' replays are in
  `experiments/ladder_nov2/replays/*.repl26a` (download loop; `dl.done` appears when finished).
- Analysis pipeline (built Oct 28-29, works on local and ladder replays): `/home/claude/analysis/*.py` (analyze.py per-game record,
  aggregate.py, groups.py, deaths.py, engage.py, exchange.py, response.py, opening.py, episodes.py, gaps.py, wards.py, fuel.py,
  fuel_local.py, bench2.py); decoder `tools/replay/decode.mjs` (engine wasm cached under /root/.cache/cambc). Earlier studies:
  `/home/claude/data/WHY_WE_LOSE_TO_MITE_AND_IC_AND_THE_FIX.md` (65 v75 + 65 v79 losses) and the method `/home/claude/data/GOD_V23_METHOD.md`.
- Local bench: `python3 -I /home/claude/analysis/bench2.py A B --maps 'maps/s4/*.map26a' --jobs 2 --tag T --nobuild` (both sides,
  ~1.8 s a game with 2 CPUs; rows in `experiments/ab2/T/rows.jsonl`, resumable; prints wins, gem margin with bootstrap CI, deaths, kills).
  Variants: `python3 tools/mkvariant.py NAME --src bots/god23 key=value ... [--define G23_TRACE]` then `cambc build NAME --release`.
  Null check passed: `bots/god23` with every `g23_*` switch off vs `bots/gpta75` = 70/140, margin +0 (identical games).

## 0b. Update 18:45 UTC: v84 source received, base moved to `bots/god84`; the new work lives in `bots/god85`

- `bots/god84` = the live v84 zip (`submissions/history/god_v84_website_20261102.zip`, sha256 d32c45a2…). It is v75 + the user's other
  sessions' work: `src/v23.cpp` (their implementation of the v23 method: `v23_fe` fight engine OFF (they measured 16 deaths a game without
  the burst retreat), `v23_bank` OFF, `v23_draft` OFF, `v23_contact` ON = farm through contact, `v23_fast_cluster`, `v23_init_resume`),
  v24-v28 switches (`v26_nowake`, `v26_wait_safe`, `v27_commit/watch/avoid`, `v28_scarce`, `v28_cap_hold`, `pd_lad` ladder draft).
  Locally **god84 vs gpta75 = 102/172 (59%), +79** on maps/s4: the base for everything from now on is god84, never gpta75.
- `bots/god85` = god84 + `src/g23.cpp` (ported from god23; same hooks, grep `g23_`) + **`g23_spawnfarm`** (new, see below). `_85null`
  (all off) vs god84 = 88/172, +25 (level; not identical because two helpers left the anonymous namespace: fuel chaos).
- Mode 2 of the fight engine (`g23_fight 2` = v75's decision + vetoes) on the v75 base lost: `_g23f2` vs gpta75 75/172, −106, deaths
  11.1 vs 8.2. The vetoes are now bits (`g23_veto_bits`: 1 lure, 2 one-step, 4 chase, 8 their-half, 16 second wave, 32 leave step) and
  each bit is measured alone vs god84 (`_85v1 … _85v32`, log `/home/claude/analysis/g85_run1.log`). Keep only bits that measure ≥ 0.
- The TOL (`g23_tol`) as first written sent 4-5 bodies to a 51-gem group 73 steps away on ambush: added `g23_prime_maxd` 40,
  `g23_prime_perstep` 0.8, `g23_open_maxd` 25, `g23_alive_eta` 12, force ≤ 3 unless > 80 gems. Still unmeasured on 172 games.
- **Ladder facts (2,440 ranked games, Oct 30 – Nov 2, all ≈ 50%)**: per-map win rate ranges from 11% (crater) to 100%; the ten worst
  (crater 11, elk_arena 15, islands 18, gemfight 19, rushbait_v2 22, oasis 22, elkring 25, quarry 26, lanes 26, gem_fields 27) are poor
  maps (≤ 220 gems, few groups, the rich group in the middle). Loss-vs-win comparison on them (`experiments/ladder_nov2/cmp_maps.py`):
  the middle captures decide (oasis losses 17 vs 55, wins 46 vs 36; quarry 10 vs 35 / 26 vs 17; elk_arena 14 vs 57 / 28 vs 13) and so
  do deaths (losses: ours ≥ theirs; wins: theirs 2-4x ours). Presence in the middle is the same in wins and losses: the fights there are
  lost, not the walking. Their Marcella kills 187 of our 487 deaths. They shop 162 events a game to our 63 (gold 7160 vs 4656: captures).
- **Structural map failures found and fixed/known**: `03homonoliths` (gems only in 3 monoliths adjacent to each spawn corner): v84 farmed
  gold clusters all game and never touched them (0-1200). `g23_spawnfarm` hits a camp within attack range of a spawn tile from the spawn
  (full heal every round): 1200-0 both sides in 877 / 1167 rounds (the ladder enemy needs 1111). `02the_pack`: the only altar sits inside a
  ring of ~40 wolves; v84 never banked in one game (0-1002 with 330 captured) and first banked at r990 in another — the unlock-group
  logic (`altar_no_camp` 2, `g.unlock`) does not clear the pack; not fixed yet. `00stampede`: first capture of the objective at r955+.
- The side effect: god84 vs god84 mirror games are decided by the side (A 1026-36 on starfish, 1045-148 on crater), so single local
  games say nothing; only the 172-game both-sides panel does. On the ladder: side a 51.9%, side b 48.1%.

## 1. What was learned (the causes, from 130 ranked losses + the repo's 955-game ladder record)

1. Mite/IC own the richest group of the map on a clock (6.7x / 4.7x our captures of it); middle captures 6.5 vs 0.7 per group.
2. Mite initiates 75% of fights and wins them 52:12 because it arrives with numbers; our bodies walk in one by one (arrival spread 13
   rounds vs 6) and 70% of our deaths follow 2+ approach steps toward an enemy. Deaths 10 a game vs 3.
3. We stop farming when an enemy is in sight (camp-hit rate near an enemy 6.3% vs 16%); farming through contact is the top teams' reflex.
4. Banking: 12 bank trips vs 28; bags carried 43-50 rounds; 21% of captured gems lost on death.
5. Lures: an enemy standing inside an awake camp's reach kites our melee along the camps (Ryth died exactly like this in the first
   traced v23 game: 165 damage a round from wolves while "fighting" a Marcella at distance 2).
6. The draft decides little (mirrors); builds: Jungle first then Bruiser; one Capture emblem holder.
Ranked record by map (955 games up to Oct 28): worst rushbait_v2 2/24, fields, corners, elk_arena, fragment, reverse_spiral, oasis,
uncharted_lands, dunes, ribs, quarry; best guardians, stalactites, boss_battle 26/27. Today (v84): worst reverse_spiral, elk_arena,
quarry, crater, ambush_field, starfish, dunes.

## 2. GOD v23 code (bots/god23 = bots/gpta75 + g23.cpp + hooks), every module behind a switch (params.h, bottom)

| switch | module | status |
|---|---|---|
| `g22_exact` | engine `damage_amount` in burst_vs (v79's kill check) | ported, off by default |
| `g23_fight` (+ `g23_msg`, `g23_no_opp`) | fight engine replacing combat()'s decision stack: R = (our hp / their dps) / (their hp / our dps) over bodies within 8 of the contact, awake camps hitting us added to their dps; escape test (melee chaser ≤3 (+2 dash), stun ≤4; our dash; walk to spawn/ally < hp/incoming); states KILL / FIGHT / AVOID / LEAVE, FIGHT holds 6 rounds (released: target gone, hp<20% with escape, R<0.6, lure, chase not closing), AVOID/LEAVE hold 3; start a fight only at R ≥ 1.15, their reinforcement within 10 ≤ ours, and one step at most from reach; join an ally's fight (its priority message says FIGHT) at R ≥ 0.85 from ≤ 6; lure rule (target inside awake camp reach, we outside → no); chase guard (4 rounds without closing → that target ignored 15 rounds); never deeper into their half; bag ≥ 40 → no escapable fight unless R ≥ 1.5; LEAVE = swing (melee), stun the chaser, step to the nearest healthy ally out of reach, else spawn | written; first trace was a disaster (74 deaths vs _pxhunt) with the Σhp·dps form; rewritten to the time-ratio form + camps + lure + chase + one-step rule; **not yet measured** |
| `g23_msg` | priority = (turn class+16)·4096 + hp bucket·256 + state·64 + (target+1)·4 + flags; allies read with `sdk_bc_champion_priority` | written |
| `g23_farm`, `g23_stage` | farming through contact (current group keeps its score while the engine says AVOID and R ≥ 0.8; damage spells still go on camps near enemies), synchronized arrival (wait at staging distance ≤ 8 rounds for a claimer on the way) | written, not measured |
| `g23_tol`, `g23_ward` | team objective layer: prime set at turn ≥2 (value = gems+0.15 gold ≥ 0.5·max or gems ≥ 36, dA ≤ dB+6, ≤3, not monoliths, team clears in ≤ 40 rounds), rally tile per prime, force F, P0 clock in bit 7 of shared bytes 0-4 (0 = alive, 1..30 = (ready round/5)%30+1) + enemy_holds in byte 5, roster = `need` bodies with the smallest eta, PRIME role (farm in time → rally T_WAIT → hit), the warden's ward on a tile whose ward vision covers a spawn tile (`ward::visible_tiles_from_into`); requires learners' stance writes off (`!P.g23_tol` guards in turn()) and `g15_lock` bit 2 off | written, traced once (prime set found: starfish g=4 36 gems), not measured |
| `g23_bank` | bank at ≥15 with an altar ≤ 6, ≥ tribute_min (30), ≥ 20 with R < 0.8 nearby, free time at a rally, hard cap 60 within 15; no tribute with an enemy within 4 of the altar unless Marcella | written |
| `g23_draft` | roster rule by team size (5: VV, Vendetta, HoR, Tavi, Marcella; 4: VV, Vendetta, HoR, C&I or Marcella; 3: first three; Prism for Tavi on a single-objective map, Ryth for HoR on lone-monolith maps; counter-pick promotions) | written, not measured (method says: ship with the fight engine, never alone: Tavi/C&I on the old brain measured −100 to −165) |
| config ledger (§2.4 of the method) | g17_bait 0, g15_lock 13, mi_pick 0, learn_enabled 0, race_mode 0, death_learn 0, tribute_min 30, early_tribute_min 15, max_wait 40, g18_rich 1, ally_defend 1, cap_recall_gold 250, bank_first 1, fm_buffs 3 | to be applied as a variant and measured one at a time |

Hooks in brain.cpp (grep `g23_`): turn() (stance writes guarded, OPPORTUNITY posts, g23_read_allies, g23_tol_tick), combat() (the
`if (P.g23_fight)` block before `if (P.px_mode)`; the E.empty() early return sets keep_farm), update_priority(), group_score() (keep23,
the enemy_round surcharge, the PRIME in-time constraint WHY(15)), farm() (g23_prime_turn first, g23_go_rally when nothing scores,
g23_stage before farm_group), farm_group() (hold_spells), respond_to_alert() (no OPPORTUNITY, rallies ≤ g23_rally_r), tribute()
(g23_bank block). draft.cpp param_pick(): the `P.g23_draft` block. `best_mod` / `enemy_spell_reach` were moved out of the anonymous
namespace (declared in brain.h) for g23.cpp.

Trace build: `--define G23_TRACE` prints `FE` (fight engine per turn), `PR` (prime set), `TL` (team layer per turn) lines to
team-*.stdout inside the replay bundle (unzip the .repl26a). Script that joins deaths with FE lines: see the python in the Nov 2 session
log (decode with `node tools/replay/decode.mjs X.repl26a --out X.json`; rounds[].ch = [index, team, type, x, y, hp, maxhp, alive, gems, gold, ?, items]).
Proxy opponent for fights: `bots/_pxhunt` = gpta75 with `pxs_style=2 px_mode=1` (invader that hunts at even odds; gpta75 beats it
1048-60 on starfish, so losing to it = broken).

## 3. The order of work (do not reorder; each step is measured before the next) — base = god84, pool = maps/s4

0. Candidate 1 (ready when the panel confirms): god85 + `g23_spawnfarm 1` + the veto bits that measured ≥ 0 + `v23_bank 1` if it
   measured ≥ 0 (+ `v23_draft 1` if ≥ 0). Submit it as the next website version, run the ladder loop (§4). Everything below continues
   in parallel on the next candidate.

1. **Fight engine alone** (`_g23f` = g22_exact 1, g23_fight 1, g23_msg 1, g23_no_opp 1) vs gpta75 on maps/s4 both sides (172 games) and
   vs `_pxhunt`; also 2-3 traced games read by hand (deaths joined with FE lines). Acceptance: deaths ≤ v75's, margin ≥ 0 vs gpta75,
   ≥ v75's margin vs _pxhunt; no faults. If a death pattern is clear (lure, chase, walked in alone, stayed at R < 0.6), fix the rule, not
   the thresholds. Thresholds to sweep only after the patterns are gone: g23_r_engage 1.0/1.15/1.3, g23_fight_hold 4/6, g23_bag_caution.
2. **+ farming through contact** (`_g23ff` = + g23_farm 1 g23_stage 1). Acceptance: camp damage up, deaths not up.
3. **+ banking** (`_g23fb` = + g23_bank 1 tribute_min 30 early_tribute_min 15 bank_first 1 cap_recall_gold 250).
4. **+ TOL** (`g23_tol 1 g23_ward 1`). Acceptance: richest-group captures up (groups.py on local replays), margin ≥ step 3.
5. **+ draft roster** (`g23_draft 1`), only on top of 1-4.
6. **+ config ledger** items one at a time (learners off etc.).
7. Held-out pools: `maps/gen2`, `maps/gold3`, `maps/var17` (if present) and the 16 new 03_* maps alone.
8. Package: `cambc bundle god23` → `submissions/god23.zip` (+ copy to `submissions/history/god_v23_<date>.zip`), sha256 in BUILDS.md,
   a changelog line in AGENTS.md.

Benchmark runner: `/home/claude/analysis/run_g23.sh VARIANT...` (builds each, benches vs gpta75 on maps/s3 — change to s4 — and prints
the summary into `/home/claude/analysis/g23_run1.log`). Kill a stuck batch by PID (`pgrep -fa "cambc|bench2"`), never with
`pkill -f run_g23` from inside a shell whose command line contains that string (it kills the shell).

## 4. The ladder loop (the user's rule) — do this only with a candidate that passed §3

1. Snapshot: `cambc submissions list` (note the live version number, today v84), `cambc ladder --page 4 --limit 25 --json` (our rank /
   rating), `python3 experiments/ladder_nov2/fetch_me.py --pages 5` (the record of the live version: last N ranked games, win rate, by
   opponent-rank band). Record them in `experiments/ladder_nov2/loop_log.md`.
2. Paired unranked groups BEFORE going live (they play the live submission, so this needs the candidate live? No: unranked groups use
   our LIVE bot; so paired groups come after activation): `python3 tools/paired_groups.py plan experiments/ladder_nov2/matches_me.jsonl
   --since <ISO of the live version's activation> > experiments/ladder_nov2/paired_plan.json`.
3. Upload and activate: `cambc submit bots/god23 --note "GOD v23 <desc>"` (check `cambc submit --help` for the exact flags), then
   `cambc submissions activate <new version>`. Write the time (UTC) into loop_log.md.
4. Paired groups: `python3 tools/paired_groups.py run experiments/ladder_nov2/paired_plan.json --max 20` (quota ~50 groups per rolling
   hour, `cambc match-groups quota`), then after ~30 min `fetch_me.py` and `paired_groups.py report`.
5. Judge after ≥ 60 ranked games of the new version (ranked games come ~30 an hour): compare win rate and rating trend with the
   previous version's last 100 ranked games (same opponent-rank bands). **Roll back** (`cambc submissions activate <previous>`) when the
   new version's ranked win rate is below the old one's by more than the noise (two-proportion z > 1.5) or paired groups are net
   negative; then analyse its losses (download replays, run the analysis scripts), fix, go to §3 step 1 with the fix.
6. Keep: when it is better, it stays; the next candidate is measured against it (it becomes the "previous live").
Never leave a worse bot live overnight: if the agent cannot monitor, roll back before stopping.

## 5. Pitfalls found so far

- Σ(hp·dps) ratios explode when the enemy is low: use time ratios. Camps must be in the fight estimate: lures.
- A melee "kill" at distance 2 is only real when the step is free (target acted this round, stunned, channelling) — otherwise it kites.
- The FIGHT hold must be released by the chase guard and by R < 0.6, not only by "a new enemy arrived".
- First game turn fuel is 200k and init uses ~180k on big maps: everything new runs from round 2 with a fuel floor (g23_tol_init needs
  60k free). Game turns: mean 31k, p90 55k; keep the fight engine under ~8k.
- mkvariant copies `src/` at creation: recreate variants after every edit of bots/god23 (the bench runner builds what is in the variant).
- `cambc matches list --limit` ≤ 100; use the cursor. The ladder JSON: `{"teams": [...], "total": N}`; our team is on page 4 at limit 25.
- Replays: `--log-limit 0` in run-batch drops stdout; omit it for trace builds.
- Queues: never chain background queues with `while pgrep -f "queueN.sh"` — the wrapper shells that launched them keep that text in
  their command line, so the wait never ends (lost ~40 min on Nov 2). Use one sequential script (`/home/claude/analysis/master_queue.sh`)
  or anchor the pattern (`pgrep -f "^/bin/bash /home/claude/analysis/queueN.sh"`).
- bench2 resumes from `experiments/ab2/<tag>/rows.jsonl`: after changing a variant's code, use a NEW tag (or move the old rows), else the
  old result is printed again (happened with `_85sf`).
