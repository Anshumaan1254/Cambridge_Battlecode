# GOD v24 plan — why we lose to the top 30, and the fix for each shortcoming (Nov 3 2026)

Written for hand-over: any agent (Opus included) can execute it from here without the chat. Read §0 first, then §2 (the
shortcomings), then §4 (the order of work). Every number in §2 has a script behind it (§1); every fix names its switch, its hook in
the code, its test and its rollback. The plan is final once the user has approved it (§6).

## 0. State of the world (read first)

- Competition: CAMBC 2026a, ends Nov 18. **International Qualifiers: the entry is the SELECTED version at 2026-11-03T23:59Z**
  (`cambc submissions list --json` → `upcomingTournament`). Team HouseOfCoders rank ~70, rating ~2000; rank 30 ≈ 2175, rank 1 ≈ 2545.
- **Live and selected: website v88 = `bots/g23rcf`** (= website v84 `bots/god84` + `g23_fight 2`, `g23_veto_bits 64` (rescue a caught
  ally), `g23_capfix 7` (reward hand-off only to a claimer, near rewards taken now, no en-route kill of a last camp), `g23_watchfix 1`
  (wait next to a respawning group at timer 0, a stuck timer is no wait, a travel dash is not watchdog progress)). Best measured
  version: on 250 replayed ladder games v88 won 134, v84 121, v85 (the user's `bots/god29`) 68/150 vs v88's 75/150.
- **The user's ranked rule (11:26 IST, Nov 3): ranked matches are created every 10 minutes (UTC minute % 10 == 0). The best version
  must be live at every ranked slot. A test version is live only between slots.** Tool: `experiments/ladder_nov2/ladder_cycle.py`
  (`--submit BOT --note ... --best 88 --plan P --max 50 --execute`: after a slot uploads/activates the test version (~3 min to be
  live), queues its paired groups while it is live (waits for `--min-free` quota; 50 groups per rolling hour), re-activates the best
  (~2-3 min recompile) before the next slot, logs a CYCLE line in `loop_log.md`). Report: `python3 experiments/ladder_nov2/three_way.py
  PLAN` (new vs every version column on the same games; net flips + sign-test p). Next plan file for a candidate:
  `python3 experiments/ladder_nov2/next_plan.py OUT.json vNN PLAN...` (the replayed results of vNN become a column). Never use
  `ladder_loop.py deploy / rollback` any more (they leave a test version live across slots).
- Base for code: `bots/god85/src` = v84 + every module of this session behind `g23_*` switches (all off = v84's games exactly on 3
  maps; on fuel-limited maps new code moves fuel even when off: 17 of 86 map pairs differ). `tools/g23port/apply.sh <base> <new>`
  re-applies the modules onto another v84-lineage source (used for v85: `bots/g23on29`). v85 source = `bots/god29` (`god29.zip`).
- Local evaluation: `tools/mkvariant.py NAME --src bots/god85 k=v ...`; `/home/claude/analysis/run_vs.sh REF VARIANT...` (172 games on
  `maps/s4`, both sides, ~10 min each with 2 CPUs; rows in `experiments/ab2/<tag>/rows.jsonl`; a NEW tag after any code change);
  `/home/claude/analysis/run_vs_pool.sh heldout REF VARIANT` (103 generated maps, 206 games). Noise: ±80 gems (95%) per 172 games;
  deaths / kills / monster damage are the less noisy columns. Both pools are mirrors vs v84 (= v88 minus the fixes); vs `gpta75` (v75)
  as a second opponent. Local margins have NOT predicted the ladder: v89 (+43 s4) −10 on the ladder, v90 (+89 / +43) −8, v92 (+13 /
  +97) −10. The ladder paired test is the decision; local panels are a disaster filter (≥ −30 on both pools, deaths not up).
- Inert check after any edit of god85: `python3 tools/mkvariant.py _85nX --src bots/god85; cambc build _85nX --release; cambc run-batch
  /home/claude/analysis/inert/mX.txt --jobs 2 --log-limit 0 --release` (3 maps vs god84) and compare the statistics JSONs with the
  n4_* ones (every key identical) — see `loop_log.md` 00:46 for the recipe.
- Logs: `experiments/ladder_nov2/loop_log.md` (every measurement, newest last), `docs/plans/god23_plan.md` STATUS (the session's
  history, newest first), `AGENTS.md` (hand-over bullet), `experiments/ladder_nov2/DEPLOY_CHECKLIST.md` (gates; §5 updates it).
- Pitfalls (consolidated in `docs/plans/god23_plan.md` §5): pkill self-match, container restarts kill runs (salvage with
  `tools/g23port/salvage_bench2.py`), a body on a group's spawn tile blocks its respawn (timer reads 0), other teams queue groups vs
  our live version, an activated old version recompiles (~2-3 min), the platform's follow-newest mode makes an upload live by itself.

## 1. Evidence base (datasets and scripts)

| dataset | where | what |
|---|---|---|
| top-30 ranked games | `experiments/top30_nov3/` (`ladder_fetch.py --top 30`): `matches_current.jsonl` 6,795 matches / 45 teams, `replays/` + `dec/` + `mj/` ~1,200 top-30 vs top-30 games on the 86-map pool, `teams.json` | the benchmark |
| our ranked / paired games | `experiments/ladder_nov2/`: `matches_me.jsonl`, `dec/` 315 decoded (142 ranked v84-v87, 118 v88, 37 v84-87 unranked, 18 older) | us |
| per-stream analyses | `experiments/top30_nov3/<stream>/REPORT.txt` + scripts (§2 cites them) | the numbers in §2 |
| earlier studies | `experiments/ladder_nov2/agent_fights/REPORT.md`, `map_fail/REPORT.md` + `out/opening_findings.txt`, `v88_bugs/REPORT.txt`; docs/strategy_v2/28, 29, 31, 32 | fights, worst maps, openings, v88 bugs, method |
| measurement ledger | `experiments/ladder_nov2/loop_log.md` (LOCAL / PAIRED / CYCLE lines) | what was tried |

## 2. Shortcomings and fixes

(Filled from the streams in §1; each entry: evidence → cause in code → fix → test → status.)

### 2.A Ledger of this session's measurements (what already works and what does not)

| change | local s4 (172) | held-out (206) | ladder paired vs v88 | verdict |
|---|---|---|---|---|
| rescue a caught ally (bits 64) | +112, deaths 7.8 vs 9.2 (lucky sample; combos +6..+34) | +31 | v87 vs v84 +10/250 | in v88 |
| reward-capture fixes `g23_capfix 7` | +39 alone | — | v88 vs v87 +3 (73 flips); ladder: our kills stepped on within 1 round 88% (v84-87 71%, opponents 78%); late/never-captured rewards 6.8 → 2.0 a game | in v88, confirmed |
| respawn / watchdog fixes `g23_watchfix 1` | −2 alone | — | ladder: 0 respawn blocks (were 4 rounds a game), 40+-round stalls 0.21 → 0.07 a game | in v88, confirmed |
| rescue + commit (bits 192) | +42 | −2 | v86 +6/250 vs v84 | dropped (rescue alone better) |
| kit build orders `v23_build 1` | +43, deaths −1.0 | −36 | **v89 −10 vs v88** | off |
| strike_first 3 (hit-first holds) | +89 | +43 | **v90 −8 vs v88**; level vs v75 | off (non-transitive, as in Oct) |
| opening safety `g23_open_safe 100` | −23 | +17 | v91: 15/30 = v88 15/30 | untested further |
| v85 base + v88 switches (`g29rcf`) | vs v85 +55; vs v84 +13 | +97 | **v92 −10 vs v88**, +2 vs v85 | off; v85's own switches add nothing on the ladder |
| v24 build lists (Treasure first) `v24_build 31` | +15, deaths 7.2 vs 9.1 | −5 | not tested | candidate (after a ladder test) |
| team objective layer `g23_tol` | −341 → −190 (16 fixes) → −135 / −108 (conservative) | — | — | shelved (farming loss) |
| rule roster `v23_draft` (Tavi / C&I) | +72 alone; with rescue −44 / −49, deaths +2 | — | — | off |
| dive filter / camp zone / spawn farm / one-step / leave step / bank rules / disengage / hurt-wait / bag cap / squads / deathball / hold-safe | −22 / −57 / −49 / +42 then 0 / −106 / +22 / −22 / +10 (held-out −12) / −49 / −53 / −91 / no-op | | | off |

### 2.B Shortcomings vs the top 30 (to be filled)

S1 … (from the economy stream)
S2 … (fights)
S3 … (objectives / map control)
S4 … (banking / draft / items)
S5 … (endgame / map features / execution)

## 3. Fix designs (code-level)

(One subsection per fix in §2: switch name in `params.h`, hook (file:function), the rule in pseudo-code, fuel cost, inert-when-off
argument, local gates, ladder test, rollback.)

## 4. Order of work

1. Qualifiers (today): v88 stays selected; no deploys after ~21:00Z; re-check `Selected:` after 23:00Z (scheduled reminder 21:15Z).
2. … (ranked by expected gain / effort, with dependencies)

## 5. Procedure for every candidate (binding)

1. Code behind a switch in `bots/god85/src` (default off); inert check; `tools/g23port` patches regenerated.
2. Local: `run_vs.sh god84 VARIANT` and `run_vs_pool.sh heldout god84 VARIANT`: both ≥ −30, deaths not up by > 0.5, 0 faults, fuel
   p99 < 90k (fuel_dir.py on kept replays). Mechanism check where possible (a metric that the fix must move, measured on local games).
3. Bundle: `cambc bundle NAME --output submissions/history/<name>_<date>.zip`, sha256 in `loop_log.md`.
4. Ladder: `ladder_cycle.py --submit NAME --note ... --best <best> --plan <next_plan output> --max 50 --min-free 20 --execute` in a
   10-minute window (never over a ranked slot); `three_way.py PLAN` after the games (they finish within ~2 min).
5. Verdict after ≥ 150 paired games vs the best: KEEP (becomes the best) when net flips vs the best > 0 with p < 0.2 and not worse than
   v84 / v85; otherwise it stays a test version. Log a PAIRED line; update `docs/plans/god23_plan.md` STATUS and `AGENTS.md`; commit + push.

## 6. Approval and open questions

(To be settled with the user before execution.)
