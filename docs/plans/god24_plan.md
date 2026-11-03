# GOD v24 plan — why we lose to the top 30, and the fix for each shortcoming (Nov 3 2026)

Written for hand-over: any agent (Opus included) can execute it from here without the chat. Read §0 first, then §2 (the
shortcomings), then §4 (the order of work) and §5 (the binding procedure). Every number in §2 has a script and a report behind it
(§1); every fix names its switch, its hook in the code, its mechanism test and its rollback. **Nothing in §3-§4 is executed before the
user approves the plan (§6).**

## 0. State of the world (read first)

- Competition: CAMBC 2026a, ends Nov 18. **International Qualifiers: the entry is the SELECTED version at 2026-11-03T23:59Z**
  (`cambc submissions list --json` → `upcomingTournament`). Team HouseOfCoders: rating 1979 on Nov 3 06:20Z, performance rating over
  2,215 ranked games since Oct 30 = 1978, exactly what the Elo model expects (1,094 wins vs 1,096 expected): **we are not unlucky, the
  bot is a 1980 bot.** Rank 30 = 2175: **+197 rating points, i.e. scoring ~75% against the teams we now score 50% against.** No single
  fix of §2 does that; the economy gap (§2 E1-E3) is large enough that closing half of it would.
- **Live and selected: website v88 = `bots/g23rcf`** (= website v84 `bots/god84` + `g23_fight 2`, `g23_veto_bits 64` (rescue a caught
  ally), `g23_capfix 7`, `g23_watchfix 1`). Best measured version: on 250 replayed ladder games v88 won 134, v84 121; v85 (`bots/god29`)
  68/150 vs v88's 75/150. Every later candidate (v89-v92) was level or worse (§2.A).
- **The user's ranked rule (11:26 IST, Nov 3): ranked matches are created every 10 minutes (UTC minute % 10 == 0). The best version
  must be live at every ranked slot. A test version is live only between slots.** Tool: `experiments/ladder_nov2/ladder_cycle.py`
  (`--submit BOT --note ... --best 88 --plan P --max 50 --execute`: after a slot it uploads / activates the test version (~3 min to be
  live), queues its paired groups while it is live (waits for `--min-free` quota; 50 groups per rolling hour), re-activates the best
  (~2-3 min recompile) before the next slot, logs a CYCLE line in `loop_log.md`). Report: `python3 experiments/ladder_nov2/three_way.py
  PLAN` (new vs every version column on the same games; net flips + sign-test p). Next plan file for a candidate:
  `python3 experiments/ladder_nov2/next_plan.py OUT.json vNN PLAN...`. Never use `ladder_loop.py deploy / rollback` any more.
- Base for code: `bots/god85/src` = v84 + every module of this session behind `g23_*` switches (all off = v84's games exactly on 3
  maps; on fuel-limited maps new code moves fuel even when off: 17 of 86 map pairs differ). **v24 work starts from a copy with v88's
  values as defaults: `bots/god24` = `bots/god85` with `g23_fight 2`, `g23_veto_bits 64`, `g23_capfix 7`, `g23_watchfix 1` (§4 step 0);
  every new switch is `g24_*`, default 0 = v88.** `tools/g23port/apply.sh <base> <new>` re-applies modules onto another v84-lineage
  source.
- Local evaluation: `tools/mkvariant.py NAME --src bots/god24 k=v ...`; `/home/claude/analysis/run_vs.sh REF VARIANT...` (172 games on
  `maps/s4`, both sides, ~10 min with 2 CPUs; rows in `experiments/ab2/<tag>/rows.jsonl`, replays in `experiments/ab2/<tag>/g/`);
  `/home/claude/analysis/run_vs_pool.sh heldout REF VARIANT` (103 generated maps, 206 games). Noise ±80 gems (95%) per 172 games.
  **REF is now `g23rcf` (v88)**, second opponent `gpta75`. Local margins have NOT predicted the ladder (v89 +43 → −10, v90 +89/+43 → −8,
  v92 +13/+97 → −10): local panels are a disaster filter plus a mechanism check (§5), the ladder paired test decides.
- Inert check after any edit: `python3 tools/mkvariant.py _24nX --src bots/god24; cambc build _24nX --release; cambc run-batch
  /home/claude/analysis/inert/mX.txt --jobs 2 --log-limit 0 --release` vs `g23rcf` on 3 maps; every statistics key identical (recipe
  `loop_log.md` 00:46).
- Logs: `experiments/ladder_nov2/loop_log.md` (every measurement), `docs/plans/god23_plan.md` STATUS (history), `AGENTS.md`,
  `experiments/ladder_nov2/DEPLOY_CHECKLIST.md`.
- Pitfalls (`docs/plans/god23_plan.md` §5): pkill self-match, container restarts kill runs (salvage `tools/g23port/salvage_bench2.py`),
  a body on a group's spawn tile blocks its respawn, other teams queue groups vs our live version, an activated old version
  recompiles (~2-3 min), the platform's follow-newest mode makes an upload live by itself, **our decoded ladder games are loss-heavy
  (v88's are the paired LOSSES): never read a map-class win rate off them; use `matches_me.jsonl` (all ranked results)** — the "monolith
  maps 0/33" alarm of the first draft was this bias (ranked: monolith maps 57%, n=870).

## 1. Evidence base

| dataset | where | what |
|---|---|---|
| top-30 games | `experiments/top30_nov3/`: `matches_current.jsonl` 6,795 ranked matches / 45 teams, 1,202 top-30 vs top-30 replays (`replays/`, `dec/` ~1,000 decoded, `mj/`) | the benchmark |
| our games | `experiments/ladder_nov2/`: `matches_me.jsonl` (2,795 ranked games since Oct 30 with results), `dec/` 315 decoded (v84-v88, loss-heavy) | us |
| stream reports (Nov 3, 08:00-08:45Z) | `experiments/top30_nov3/economy/REPORT.txt` (economy + objectives), `fights/REPORT.txt`, `draft_bank/REPORT.txt` (banking, draft, execution, map classes), `nemesis/REPORT.txt` (who beats us) | the shortcomings below; each has scripts + tables beside it |
| tables | `economy/tables.txt` (map-matched v88 vs top-30), `objectives/out/stats.txt`, `fights/tables_full.txt`, `draft_bank/out/tables.txt`, `execution/out/summary.txt`, `execution/out/mapreg.txt`, `nemesis/out/winrate.txt` | |
| earlier studies | `experiments/ladder_nov2/agent_fights/REPORT.md`, `map_fail/REPORT.md`, `v88_bugs/REPORT.txt` | fights, worst maps, v88 bugs |
| measurement ledger | `experiments/ladder_nov2/loop_log.md` | what was tried |

Comparisons: "MM" = map-matched v88 vs top-30 (economy tables, right of `|`); OPP = our opponents in the same games; TOPl = the losing
top-30 side (the loss-conditioned benchmark, since our decoded games are mostly losses).

## 2. Shortcomings and fixes

### 2.A Ledger of this session's measurements (what already works and what does not)

| change | local s4 (172) | held-out (206) | ladder paired vs v88 | verdict |
|---|---|---|---|---|
| rescue a caught ally (bits 64) | +112, deaths 7.8 vs 9.2 (lucky sample; combos +6..+34) | +31 | v87 vs v84 +10/250 | in v88 |
| reward-capture fixes `g23_capfix 7` | +39 alone | — | v88 vs v87 +3 (73 flips); our kills stepped on within 1 round 88% (v84-87 71%) | in v88, confirmed |
| respawn / watchdog fixes `g23_watchfix 1` | −2 alone | — | 0 respawn blocks (were 4 rounds a game), 40+-round stalls 0.21 → 0.07 a game | in v88, confirmed |
| rescue + commit (bits 192) | +42 | −2 | v86 +6/250 vs v84 | dropped |
| kit build orders `v23_build 1` | +43, deaths −1.0 | −36 | **v89 −10 vs v88** | off |
| strike_first 3 (hit-first holds) | +89 | +43 | **v90 −8 vs v88** | off |
| opening safety `g23_open_safe 100` | −23 | +17 | v91: 15/30 = v88 15/30 | untested further |
| v85 base + v88 switches (`g29rcf`) | vs v85 +55; vs v84 +13 | +97 | **v92 −10 vs v88** | off |
| v24 build lists (Treasure first) `v24_build 31` | +15, deaths 7.2 vs 9.1 | −5 | not tested | candidate (E4) |
| team objective layer `g23_tol` | −341 → −108 after 16 fixes | — | — | shelved |
| rule roster `v23_draft` | +72 alone; with rescue −44 / −49 | — | — | off |
| **flee less by parameters `_fight1`** (`isolated_flee_adv` 1.2, `outmatch_flee` 0, `ml2_flee` 0.5, `fight_back_margin` 1.0, `ml2_leave` 0.3; Nov 2, god23 base) | — | — | — | **68/140, −101 vs v75**: a blanket "flee less" loses (E1 must stay narrow) |
| **`g23_farm` + `g23_stage` + `g23_msg` on the old god23 base (`_g23ff2`)** | vs v75: −72 (fight engine alone `_g23f2` −106) | — | — | +34 over the engine alone; never measured on v88 (E1) |
| dive filter / camp zone / spawn farm / one-step / leave step / bank rules / disengage / hurt-wait / bag cap `g23_bankcap` / squads / deathball / hold-safe / `open_follow` (23/42) | −22 / −57 / −49 / +42 then 0 / −106 / +22 / −22 / +10 (held-out −12) / −49 / −53 / −91 / no-op | | | off |

### 2.B The shortcomings (ranked by estimated gain; numbers are v88 unless marked)

Summary (gains are the streams' estimates before overlap; "games/100" = ranked wins per 100 games):

| id | shortcoming | type | est. gain | fix switch(es) | prior / risk |
|---|---|---|---|---|---|
| E1 | we give up contested big groups at an even contact (3 rules fire at 1 v 1) | STRATEGY, rule-driven | +40 gems/g (+ as much denied) | `g24_hold` + `g23_farm 1` | `_fight1` (blanket flee-less) −101; this is narrow |
| E2 | rich groups farmed by 1 body (join rule); worst on gem-scarce maps | STRATEGY, deterministic rule | +30 gems/g; +2.5 games/100 on scarce maps | `g24_join` (+ `g24_scarce`) | squads / deathball / `open_follow` lost (they idled followers) |
| E3 | no Marcella funnel: captures go to the tank, she banks late; the nemesis teams' Marcella has +31% shards at r600 and kills 4.5 of ours a game | STRATEGY | +2-4 games/100 (nemesis + draft streams) | `g24_marc_funnel` (+ `g24_carry_cap`) | `mi_capture 2` (Oct) level: it only re-ordered bodies within 5 |
| E4 | gold / items 25-40% behind (consequence of E1-E3) | — | follows | (`v24_build 31` as an extra) | — |
| F1 | dashers don't dash out of a fight they leave; HoR never does | BUG | 0.45 deaths/g ≈ 6 gems/g | `g24_flee_dash` | none (corrects an inconsistency) |
| F2 | walk-ins into stronger groups (abandon only at R < 0.3; rescue counts bodies, not power) | STRATEGY | 0.4-0.6 deaths/g | `g24_abandon_r`, `g24_rescue_pw` | dive filter −22 (it was blanket) |
| F3 | deaths within 40 rounds of respawn doubled on v88 (1.49 vs 0.31/g) | STRATEGY | 0.4 deaths/g (overlaps F2) | `g24_fresh` | none |
| F4 | deaths to camps the enemy woke (0.96 vs 0.20/g) | STRATEGY | 0.3 deaths/g | `g24_lure` | camp zone −57 (it was blanket) |
| F5 | slow answer to a ranged opener (48% vs 59% within 1 round) | STRATEGY | < 1 gem/g | `g24_hit_is_fight` | — |
| X1 | camp execution: passive camp damage, wake-and-leave, A-B-A, wasted dashes (21.6 gems/g priced) | BUG + STRATEGY | +10-20 gems/g | `commit_keep 1` (exists, never measured), `g24_dash_travel` | — |
| X2 | endgame: a winning bag recalled over and over, never landed | BUG | +0.5 games/100 | `g24_bank_fallback` | — |
| X3 | wards: re-warded near our spawn, few on bushes | BUG-like, small | 0-10 gems/g | `g24_ward_keep`, `g24_bush_ward` | unconditional bush warding lost before |
| N1-N3 | the teams that beat us: their Marcella is not our priority target; our model under-rates an itemized Marcella; filter's locks | STRATEGY / model | +17-21 perf points at most in total (the gap is general) | `g24_marc_focus`, `g24_marc_threat`, `g24_lock_memory` | — |
| M1-M3 | method: local panels don't predict the ladder; replay samples are loss-biased; ladder tests have little power | METHOD | decides whether any of the above ships | §5 | — |

**Checked and NOT gaps** (do not spend time here): first-target choice (nearest-group share 45% vs 44% MM); capture execution (our
kills captured by us 98% vs 97.5%); gems per capture (16.4 vs 16.6); shop rules (we spend fast: unspent gold 67 vs 155 at r300 — the gap
is income); bait recalls 3,847 vs 2,263 a game (`g17_bait`, measured +98); banking loser-vs-loser (421 vs 445 banked, gems lost on death
75 vs 118); the draft (main roster = the top-30's most common, edge −0.1 over 2,443 games); stuns before death like with like (41% vs
40%); target choice and focus fire in exchanges (same); **losing exchanges at equal power is the item gap** (with the shard gap held
within ±3 we win 58% vs OPP 57%); monolith and single-altar maps (ranked 57% / 55%: our better maps).

The map picture: our ranked win rate by gems per champion (quartiles) 41% / 45% / 57% / 59% (n 697 / 783 / 663 / 652); the top-30 are
flat (±0.3 points). The 10 worst maps (13-26%: 00crater, 01elk_arena, 03ambush_field, 00gemfight, 00oasis, 01islands,
00rushbait_v2, 00quarry, 00elkring, 00gem_fields) average 253 gems, area 1,990, spawn distance 38 (others 536 / 3,125 / 68). Logistic
regression (n 2,795, per sd): gems +0.37 (z +3.9), area +0.21 (+4.0), altars −0.20 (−3.8), golems −0.17, narrow −0.15, bush −0.12. **Our
weakness is small, gem-scarce, contact-heavy maps** — where E1, E2, F2 and the death gap (small maps 11.7 deaths/g vs OPP 8.8) all act.

#### E1 — We give up contested big groups at an even contact [STRATEGY] est. +40 gems/game (+ about the same denied)
- **Numbers** (objectives Q1; economy MM): of the contested big-group (≥ 30 gems, |dA−dB| ≤ 20%) respawn cycles that were taken we
  capture 0.27 (v88) / 0.34 (v84-88) vs TOP 0.50, OPP 0.66. Present within 4 at the respawn: we capture 0.36 vs TOP 0.69, OPP 0.80.
  Cycles we hit first and then lost: 0.41 vs TOP 0.20, OPP 0.13. Gems on contested big groups per game 108 (v88) vs TOP 239, OPP 352.
  First 12 rounds of contact, 1 v 1 at hp ≥ 0.8: we LEAVE 35% vs TOP 18%, farm 24% vs 34%, die 4% vs 5% (n 83 / 406). Body-rounds
  hitting a camp with an enemy within 6: 3.3% vs 9.7% (r1-150) … 3.0% vs 5.8% (r801+); walking then 57-61% vs 45-53%.
- **Examples**: 85179b55 02uncharted_lands G0 (57 g) respawn r364, contact r375 1 v 1 hp 1.0 → left, taken r422; e70ce6f5 03ambush_field
  G10 (85 g) r277 1 v 1 hp 0.86 → left, taken r351; e33a81a9 01fracture G24 r1241 → left, taken r1290; 9afd7274 01fracture G25 hit first
  r908, left r913, taken r931 (`economy/s2/ex2.py`).
- **Cause** (verified in `bots/g23rcf/src`): three rules, all fire at an even 1 v 1:
  1. `brain.cpp` combat() l.4794: `if (!calm && ((((isolated || reserve) && adv < P.isolated_flee_adv && nearest_enemy <= P.flee_dist) ||
     outmatched) && task != T_CAPTURE ...` with `isolated_flee_adv = 1.5` (params.h:75), `flee_dist 5`: a body with no ally within 5
     flees from any enemy that is not 1.5× weaker; `flee_recall` then recalls (our held recalls are hit 33% vs 23%).
  2. The flee calls `avoid_note(E)` (l.2048); `v27_avoid = 12` (params.h:1134) bans every group within their reach + 2 for 12 rounds:
     group_score l.6810 `if (P.v27_avoid > 0 && round < av_until && in_avoid(g)) { WHY(10); return -1; }`; farm()'s hard commit (l.7673)
     does not keep a WHY-10 target.
  3. group_score l.7245: `if (round - g.enemy_round < 12 && !(P.g23_farm && P.g23_fight && g.id == task_group && g23_keep_farm)) time
     += 12.f;` — `g23_farm` is 0 in v88, so any group an enemy was seen at costs 12 extra rounds.
- **Fix `g24_hold`** (+ `g24_hold_gems 30`, `g24_hold_r 0.8`, `g24_hold_hp 0.5`): (a) the isolated pre-emptive flee at l.4794 does not
  fire when `task_group` has ≥ `g24_hold_gems` gems (or, with `g24_hold_own 1`, is on our half), we are within attack range + 2 of it,
  hp ≥ `g24_hold_hp`·max_hp and adv ≥ `g24_hold_r`; the outmatched rule (adv < 0.8 vs 2+), real-fight, cornered and burst rules stay;
  (b) no `avoid_note` in that case; (c) `g23_farm 1` in the same variant (removes the +12 for the task group while the engine says
  nobody can hit us next turn at R ≥ `g23_keep_r`). Narrow by design: `_fight1` (flee less everywhere) lost −101.
- **Mechanism test** (local, our side): 1 v 1 hp ≥ 0.8 contacts at contested big cycles "left" 35% → ≤ 20%; contested capture share
  ≥ 0.45; camp-hit share with an enemy within 6 ≥ 6%; deaths/g up ≤ 0.5.

#### E2 — Rich groups are farmed by one body: the join rule [STRATEGY + deterministic rule] est. +30 gems/game; +2.5 games/100 on scarce maps
- **Numbers**: gems captured by r150 66 vs 88 (MM; vs TOPl 66 vs 75), by r300 142 vs 197 (TOPl 163); first gem capture r69 vs r53; all
  bodies on ONE first group 12% vs 38%; bodies on the first target 2.36 vs 3.16; first group killed in 30.9 vs 24.6 rounds; opening
  visits to ≥ 30-gem groups: alone 45% vs 17%, killed 45% vs 55%; harmless (gem / gold-only) ≥ 30-gem groups always alone (1.00 vs 2.03
  bodies). Scarce maps (≤ 92 gems per champion, 53% of ranked games): share of ≥ 12-gem kills made by one body 0.72 vs TOPl 0.59 (rich
  maps 0.62 vs 0.57); attackers per ≥ 30-gem kill 1.44 vs 1.68; group kills per game 44 vs 49 (TOPl) / 71 (OPP).
- **Examples**: adde6089 adgato_gemcombat2 b4 alone on G0 (56 g harmless) r18-24, left without a kill; 87897445 02stalactites b5 G7 (77 g
  harmless) r43; e33e2b41 02the_pack b1 G0 (192 g wolf pack) r7 / r83; c17d8fdc 00breadcrumbs 28 of 28 kills solo; 853d2055 01hooks
  first groups per body [8,0,4,10], 22 gems by r150.
- **Cause**: group_score claimers branch l.6994-7008: `const bool heavy = rich || follow_g || g.monolith || g.elk || (!g.harmless &&
  (solo_rounds > P.join_min_rounds || g.attackers >= 2)); ... if (!committed && (!heavy || ...)) { WHY(6); return -1; }` — a harmless
  group of any size is never joined (`g18_rich 0`), a group one body clears in ≤ 14 rounds (`join_min_rounds`) is never joined, a joiner
  must arrive within `join_reach 1.2` × the claimers' clear time, and is credited `join_share 0.6` of the value. The leader-follow
  opening (l.6789) runs only on lone-monolith maps; `v28_scarce` fires only when the map cannot pay 1,000 gems (none of the 10 worst).
- **Fix `g24_join`** (+ `g24_join_gems 30`, `g24_join_until 300`, `g24_join_min 6`, `g24_join_reach 2.0`, `g24_join_share 0.9`): when
  `round < g24_join_until && g.gems >= g24_join_gems`: heavy = `solo_rounds > g24_join_min` (harmless included), reach test with
  `g24_join_reach`, share `g24_join_share`; up to `max_join` (3) joiners as now. **`g24_scarce`** (+ `g24_scarce_gpc 92`): computed at
  world init (`W.scarce_mode = total group gems / champions per team ≤ 92`); on scarce maps heavy = true for gem groups ≥ 12 gems with
  at most one joiner, all game. Bodies still choose by score, nobody follows a leader (the failure mode of squads / deathball /
  `open_follow`: idle followers, monster damage down); rich maps stay byte-identical under `g24_scarce`.
- **Mechanism test**: opening bodies per visit on ≥ 30-gem groups 2.5 → ≥ 3.0, alone 45% → ≤ 25%, first group killed in ≤ 26 rounds,
  gems by r300 +20; scarce maps solo share 0.72 → ≤ 0.60; monster damage r1-300 NOT down (the squad failure mode).

#### E3 — No Marcella funnel: our damage dealer is a minor collector [STRATEGY] est. +2-4 games/100 (+5-8 vs the nemesis teams)
- **Numbers**: (draft stream, loser vs loser) our Marcella makes 26% of the team's camp hits but takes 19% of its gem captures and 20% of
  its gold (TOPl Marcella 19% / 34% / 28%); our HoR takes 28% of captures vs 16%; per game our Marcella ends with 454 gold vs 925 and
  0.42 spell kills vs 2.96. (Nemesis stream, our losses to them, n=90) their Marcella: 14.6 captures / 378 gems / 1,318 gold a game,
  banks 385 gems (+770 gold from her 2-gold-a-gem passive) ≈ 70 shards on one body; ours 5.9 / 96 / 383, banks 87. She banks 40% of her
  captures within 20 rounds (median 27 rounds, 10 tiles); ours 18% (65 rounds, 16 tiles). Their team shards at r600 100.5 vs our 76.6
  (+31%); the easy teams only +2. Their Marcella kills 4.5 of ours a game in those losses vs 1.9 for the easy teams — the whole excess
  in our deaths; per team the funnel size orders the kill rate. Fights: the attackers' shard lead at our deaths 32.9 vs 12.9 (OPP).
- **Examples**: 603f9ead (dromedaries, 00oasis): their Marcella b7 captures r24, banks r33, r57, r87, r121, r318; 87 shards at r600 vs
  our best 19; kills 22 of ours. 4032595e (KKB, 00gem_fields): their Marcella b0 64 shards at r600, ours 5. 8acd6fee (smurphy, 00oasis).
- **Cause**: (1) group_score() capture hand-off (~l.6907-6933): `return P.mi_capture == 2 ? k.gold_mult * g.gold + k.tribute_gold *
  g.gems : k.gold_mult;` with `mi_capture = 1` (params.h:906): a reward goes only to a higher `gold_mult` ally (Vesper 1.2) within
  `gold_rank_d = 5`; Marcella's tribute gold never counts. (2) capture_group() (l.8102): whoever stands on the tile captures, and the
  melee tank is already there. (3) tribute() / bank_min(): every body waits for `tribute_min = 54` + 1.74 a step; the anchor rules
  (`anchors 0`) are off and rank Vesper first when on.
- **Fix `g24_marc_funnel`** (only when we drafted Marcella and she is alive): (1) a reward with gems ≥ 10 or gold ≥ 60 yields to our
  Marcella within `g24_mf_r = 8` steps (not channelling); her value = gold + 2 × gems; the holder steps off when she arrives (reuse the
  handoff path), waits at most `g24_mf_wait = 6` rounds, then captures itself; never with an enemy within 4. (2) bank_min() for
  Marcella: need = max(20, 0.5 × tribute_min) when a field altar is within `g24_mf_altar = 12` steps; else unchanged; no recall-banking
  change (the failed `g23_bankcap` forced recalls). (3) `g24_carry_cap` (draft stream S2) is the same idea for capture_group() without
  the bank part; implement it as bit 2 of `g24_marc_funnel` (1 = hand-off + bank, 2 = tank steps to the ring when the carry is within 2).
  Details: `nemesis/REPORT.txt` S1, `draft_bank/REPORT.txt` S2.
- **Mechanism test**: our Marcella's capture gold 383 → ≥ 900 a game, her banked gems 87 → ≥ 250, her shards at r600 ×2, team shards
  at r600 +15, team captured gems by r600 not down by > 20, deaths not up by > 0.5, late rewards (> 8 rounds) not up.

#### E4 — Gold and items are 25-40% behind [consequence] no separate fix
- Gold income /100 r (shards bought × 30 + unspent change) 284 vs 375 (r1-150), 338 vs 493, 353 vs 598, 327 vs 652 (r801+); shards per
  body r600 14.7 vs 20.6, r900 22 vs 34; damage per hit 77.7 vs 94.6 (r401-800). Camps −1,500 gold a game, non-camp (kills, banking
  gold) −1,300. Closes through E1-E3; metric for every economy candidate: gold income /100r r151-400 ≥ 400. Optional build lever:
  `v24_build 31` (Treasure first; local +15, held-out −5, never on the ladder).

#### F1 — Dashers don't dash out of a fight they leave; Heart of Ruin never does [BUG] est. 0.45 deaths/g ≈ 6 gems/g
- **Numbers**: retreats with our dash ready that dash within 2 rounds: 38% vs OPP 71%, TOP 74%; HoR 12% vs 68% / 70%; Vesper 64% vs
  75%; Vendetta 68% vs 70%. Caught within 8 rounds: with the dash 10%, without 25%; under 50% hp 15% vs 41%. ~1.9 deaths a game after
  a dashless retreat (HoR 1.2).
- **Examples**: 5b7f0c2e r371-377 b1 (HoR 230/1100 hp, 21 gems) walks one tile a round with Marcella 2 behind for 6 rounds, dash ready,
  dies r377; f39bc1ca r746 b3 (HoR 57%); 2ef5ac90 r848 b2 (Vendetta 19%, chaser 1 tile away, dash ready).
- **Cause**: (a) `mob_dash()` l.2495 `if (kit.dash_mod > 0.f && !strike_dash && enemy_near_d <= P.strike_dash_hold) return -1;`
  (`strike_dash_hold 9`): every flee step goes through go_home_step() (l.2650 `Nav::step_field(..., mob_dash(), ...)`), so a fleeing
  HoR within 9 tiles of an enemy can never dash. (b) combat() l.4239 `can_escape = on_spawn || !chaser || (ready(kit.dash) &&
  !chaser_dash) || ...` counts that dash, so a caught HoR skips the cornered trade (l.4305) and walks home being hit. (c) nav.cpp
  try_dash() l.285 refuses every landing tile in `avoid` (danger | camp_danger | alert_zone) and any dash gaining < 2 home steps.
- **Fix `g24_flee_dash`**: in combat()'s two flee branches (~l.4764 before `toward_help() || go_home_step(true)`, ~l.4815) and in
  g23_leave(): when our dash is ready and a chaser could hit us after a walk step (melee enemy within 3, +2 if its dash is ready; ranged
  within its range + 1), cast the dash (ignore `strike_dash_hold` while task == T_FLEE); landing tile within 2: fewest enemies whose
  next-turn reach covers it, then shortest `W.dist_home`; a `danger` tile is allowed if it is the best; never a sleeping-camp tile
  (`wakes_sleeper`) or an awake camp's range. Bit 2: `can_escape` counts our dash only if `g24_flee_dash` is on or the kit has no strike
  dash (`dash_mod == 0`).
- **Mechanism test**: dash within 2 rounds of a retreat with the dash ready: HoR 12% → ≥ 60%, Vesper / Vendetta → ≥ 80%; caught within 8
  rounds after a retreat under 50% hp 41% → ≤ 30%; HoR deaths −0.3/g (`fights/extract2.py` retreats: dash / own_dash / died8).

#### F2 — Bodies walk into stronger groups [STRATEGY] est. 0.4-0.6 deaths/g
- **Numbers**: champion deaths after 2+ steps toward the nearest enemy in the last 8 rounds 5.45/g (60%) vs OPP 2.72/g (38%); v88 5.98 vs
  1.92. Steps toward an enemy within 6 at R < 0.67: v88 52.9/g (13% die within 6 rounds) vs OPP 30.1/g (5%); while having more bodies
  ("weak+nmore") 8.0/g (17% die) vs 0.8/g; rose from v84 4.1/g → v88 8.0/g (the rescue). Dives at R < 0.67: 11.6/g, 1.58 deaths vs 6.9 /
  0.53.
- **Examples**: 6fa9287c r703-709 b1 (Vesper walks 5 steps into a farming Vendetta 3000 hp + HoR 3313, R 0.39, dead r709); fd46f2d5 r1072
  b5 (HoR R 0.24); 2bbe045f r769 b7 (Marcella 2 v 2, R 0.11).
- **Cause**: (a) group_score l.7240 `if (tadv < (P.v23_contact ? P.v23_abandon_r : P.target_threat_adv) * (big ? 0.5f : 1.f)) return
  -1;` with `v23_abandon_r 0.3` (was 1.49): between 0.3 and 0.67 a body keeps walking to a group stronger enemies hold. (b) g23.cpp
  g23_veto() rescue l.453 `if (n_en > n_us) continue;` — bodies, no power test.
- **Fix**: `g24_abandon_r 0.67` (group_score drops the group below it, ×0.5 for big groups, unless it is our task group and
  `g23_keep_farm`); `g24_rescue_pw 1` (rescue also needs `g23_ratio(a.pos, ...) >= g23_r_join` (0.85)). Consistent with E1: hold at
  R ≥ 0.8, abandon below 0.67. Not the dive filter (that blocked every step closer at R < 0.67, retreat corridors included).
- **Mechanism test**: steps toward at R < 0.67 with ≥ equal bodies 32.6/g → ≤ 20/g; walk-in deaths −0.5/g; rescue fights started keep
  ≥ 70% of today's count (rescue is the one ladder-confirmed fight gain).

#### F3 — Deaths soon after respawn doubled on v88 [STRATEGY] est. 0.4 deaths/g (overlaps F2)
- **Numbers**: deaths within 40 rounds of the body's respawn v88 1.49/g vs OPP 0.31/g; v84 0.74 vs 0.57; TOPl 1.88. Of v88's: 69% walked
  in, 59% at R < 0.67, 38% within 8 tiles of our spawn.
- **Examples**: 0929d08d r1122 b0 (HoR, 23 rounds after respawn, 4 steps in); f39bc1ca r717 b5 (Vendetta, 28 rounds, R 0.15); bfe31ac3
  r1211 b1 (Vesper, 5 rounds after respawn, R 0.36).
- **Cause**: a respawned body is at full hp and passes every hp gate: g23_veto's rescue (`hp >= g23_rescue_hp * max_hp`), combat()'s
  ally_defend (l.4307), the hit-back bar (`fight_back_margin` 0.873). Nothing asks whether the team just lost a fight there.
- **Fix `g24_fresh 40`** (+ `g24_fresh_adv 1.5`): for 40 rounds after our respawn a fight that is not killable and not in reach (rescue,
  ally_defend, second wave, proactive) needs adv ≥ 1.5; hook combat() just after g23_veto (~l.4576).
- **Mechanism test**: deaths within 40 rounds of respawn −50% (to v84's level); farm rounds unchanged.

#### F4 — We die to camps the enemy woke [STRATEGY] est. 0.3 deaths/g
- **Numbers**: deaths with hits from an enemy-woken camp in the last 5 rounds 0.96/g vs OPP 0.20 (v88 0.73 vs 0.14; TOP 0.40); 73% walked
  in.
- **Examples**: 4f472198 r1479 b7 (Ryth, 3 steps in, killed by the camp); 010b54dd r997 b1 (HoR); 372c305c r903 b2 (HoR).
- **Cause**: g23.cpp g23_veto() l.471-475 has the lure test (`lure = !killable && !rescued && td > my_reach && !in_awake_camp_range()
  && camp_danger.is_set(tgt->pos)`) but it acts only with `g23_veto_bits & 1` (live value 64), and skips rescues.
- **Fix `g24_lure 1`**: apply the lure veto to every non-killable fight, rescues included, and hold it 3 rounds on that target. Not the
  camp zone (that blocked all walks near awake camps).
- **Mechanism test**: deaths with damage from an enemy-woken camp −0.3/g; fights started on a target inside an awake camp's range → 0
  except kills.

#### F5 — Slow answer to a ranged opener [STRATEGY] est. < 1 gem/g (last)
- Received exchanges answered within 1 round 48% vs OPP 59% (spells from 4+ tiles 31% vs 48%; our Vesper 39% vs 52%); worth +5 points of
  receiver win share. Cause: combat() l.4583 fz_engage hold uses `last_fight_round`, which is set only when we fought, not when we were
  hit. Fix `g24_hit_is_fight`: `last_hit_round >= round - 1` counts as in a fight when adv ≥ `fight_back_margin` and the attacker is
  within my_reach + 1. Test: answered within 1 round 48% → 55%, deaths not up.

#### X1 — Camp execution [BUG + STRATEGY] est. +10-20 gems/g
- **Numbers** (v88 vs TOPl per game): passive camp damage 2,734 vs 1,952 (wolves 702 vs 349); camp hits taken per hit given: wolf 1.13 vs
  0.91, golem 1.28 vs 0.68; wake-and-leave alone 2.8 vs 1.7; A-B-A with no fight 61.6 vs 45.1; wasted travel dashes 11.8 vs 4.8; stalls
  ≥ 12 rounds 11.6 vs 7.5. Priced at 21.6 gems a game (`execution/summarize.py`).
- **Examples**: e33e2b41 02the_pack Marcella b1 r1099-1112 (14 wolf hits, attacking nothing), HoR b2 stalled 137 rounds from r388 beside a
  live group; 9c7cbc9f 00lanes HoR b5 A-B-A r474-561; 70d8f57d 00anvil Marcella b5 woke the monolith r883 and left.
- **Cause**: (a) solo farming (E2): one body takes every hit of a wolf pack; (b) wake-and-leave: `commit_keep = 0` (params.h:412: "a camp
  we hit in the last 2 rounds is not dropped by the join limits"; 67 camps left on this rule in 17 games), never measured; (c) A-B-A and
  wasted dashes: not traced (travel dashes per 100 rounds Vendetta 7.2 vs 5.7, Vesper 6.4 vs 5.1).
- **Fix**: `commit_keep 1` alone first; then `g24_dash_travel` (no travel dash with no enemy within 8 unless it saves ≥ 2 field steps on
  a path ≥ 10) if wasted dashes stay > 6/g. A-B-A: trace with LEGEND_TRACE on 00lanes / 01corridors before writing a fix.
- **Mechanism test**: wake-and-leave alone 2.8 → ≤ 2.0; wolf passive damage −30%; wasted dashes ≤ 6 (`execution/metrics.py` on local
  replays).

#### X2 — Endgame: a winning bag is recalled over and over and never lands [BUG] est. +0.5 games/100
- e36c7dd7 02the_pond: lost 843-846 holding 232 gems; the bag was winning from r1961; recall every round r1940-1991; tribute submitted
  r1992 lands r2016. 11 of 118 v88 losses reached r2000 (9.3% vs 3.6% of top-30 sides).
- **Cause** (two candidates, trace before fixing): tribute() l.6013 v27_avoid hot-altar branch sets `recall_bank` even when endgame /
  winning; combat / farm run before tribute() that turn.
- **Fix `g24_bank_fallback`**: the v27_avoid branch does not apply when endgame or winning; after ≥ 3 cancelled bank recalls in a row
  walk to the nearest altar; a winning / endgame bag calls tribute(true) before farm and camp combat (enemy combat keeps priority).
- **Test**: mechanism log "recall cancelled ≥ 3 times while winning" → 0 on local games.

#### X3 — Wards [BUG-like, small] est. 0-10 gems/g
- 215 wards a game vs 147; 33% within 8 steps of our spawn vs 17%; bush share 0.41 vs 0.74. Wards cost no action (place_ward() runs at
  the end of turn()); the cost is that each re-ward deletes the champion's forward ward. Win rate on bushy maps (bush ≥ 6%) 46% vs 63%
  on bush ≤ 3% (mechanism not verified).
- **Fix `g24_ward_keep`**: don't re-place when the new tile is within 8 steps of our spawn, or not a bush while the old one is, or within
  6 of the old ward (force placements unchanged). `g24_bush_ward`: `ward_bush 2` on maps with bush share ≥ 0.06 only (unconditional
  bush warding lost before). Test: spawn-area share ≤ 0.15, bush share ≥ 0.6; then ladder only (no local effect expected).

#### N — The teams that beat us (nemesis stream; see `nemesis/REPORT.txt`)
- Our ranked score is exactly Elo-expected overall (1,094 wins vs 1,096). 8 "nemesis" teams: 121/375 (32%) vs 173 expected (−52 wins);
  3 teams we beat far above expectation (OneTap 79/100, eclipsed Sunlight 24/30, SilverSamurai 19/25: +40 wins). **Playing the nemesis
  teams at their Elo expectation would add only +17 perf points (gap to rank 30: 197).** The gap is general strength, not matchups.
  Biggest drains (wins below expectation in 4 days): filter +15.5, Gem Simons +13.2, Sneaky Bush Campers +9.8, shoutout MAPS +9.1, KKB
  +8.6, the ruliad +8.4. Our only deficit band is opponents rated 1900-1999 (51% vs 53% expected); vs 2000-2199 we beat expectation.
- What the nemesis teams do that the easy teams don't: **the Marcella funnel (E3)** — not invasions, range-4 spells, wards, steals or
  teleports (equal, or the easy teams do more). Their opening stacks a 32-gem first target with ~2 bodies while we split onto 19-gem
  groups (= E2).
- **N1 `g24_marc_focus`** [STRATEGY, +0.5-1 games/100]: their Marcella dies 2.5 times a game in our wins vs 1.0 in our losses (n 27 / 90).
  g23.cpp g23_pick_target() (l.224) keys on the damage race only. Fix: divide an enemy Marcella's key by (1 + bag/40) and by 1.3 when
  her seen strength ≥ 1.5 × her base; target choice only. Test: their Marcella deaths +0.5 a game vs a funnel opponent (our own bot
  with `g24_marc_funnel 1`), our deaths not up.
- **N2 `g24_marc_threat`** [model gap, +0.5 games/100]: g23.cpp g23_dps_of() (l.60) `float d = str_ * (reset_ready ? 1.2f : 1.f);` treats
  Marcella's enhanced reset as ×1.2 and ignores its stun. Fix: ×1.5 for Marcella with the reset ready, and our side's damage ×0.85 in
  g23_ratio() while such a Marcella is within 2 of the contact. Test: steps toward groups with a Marcella at R < 0.67 −30%, deaths to
  Marcella −0.5/g.
- **N3 `g24_lock_memory`** [STRATEGY, +0.3 games/100; filter only]: filter cancels 1.06 of our tributes a game by lock (64 gems; others
  ≤ 0.40). Fix: after a lock cancels our tribute at altar A, nearest_altar() adds +8 steps to A for 150 rounds while an enemy was seen
  within 8 of A in the last 20 rounds.
- `g24_open_stack` (nemesis S3: first target = the largest group with dA ≤ dB + 2, wait until 3 have arrived or 12 rounds) is the
  leader-style alternative to E2's `g24_join`; try it only if `g24_join` fails its mechanism test (the waiting is the squad failure mode).
- Next profiles (not done): Gem Simons, Sneaky Bush Campers, 天天开心 :(, Midnight Wardens.

#### M — Method shortcomings (why the last four candidates told us nothing)
- **M1 local panels don't predict the ladder** (3 of 3 misses). Local opponents are mirrors of our own lineage; ladder opponents farm
  through contact and stack bodies (E1, E2), so a change that wins vs v84 can lose vs them. Fix: the local panel is a disaster filter
  (≥ −30 on both pools, deaths not up > 0.5, no faults, fuel p99 < 90k) plus a **mechanism check** that the targeted metric moved
  (each §2 entry names it). Build the mechanism bench first (§4 step 1).
- **M2 decoded ladder samples are loss-heavy** (v88's are the paired losses) → class win rates from replays are biased (the monolith
  false alarm). Fix: map-class win rates only from `matches_me.jsonl`; replay comparisons only us vs OPP (same games) or vs TOPl.
- **M3 ladder tests have little power**: net flips of ±10 over 150-250 games had p 0.2-0.3. Fix: bundle fixes whose mechanisms are
  large (E1+E2 should flip far more than 10 games if the +40-70 gems/g estimate holds), aim each paired plan at the maps where the fix
  acts (scarce / small maps for E2, F2-F4), and use the decision rule of §5.

## 3. Fix designs — implementation notes

All switches go in `bots/god24/src/params.h`, default 0 (= v88), each with a one-line comment carrying its measurement once it has one.
Implementation details beyond §2 are in the stream reports (fix paragraphs quote the exact lines). Common rules:
- A switch off must not change a single game on the 3 inert maps (inert check, §0). Code that runs when off (new fields, extra
  computations) is allowed only if it does not change decisions; on fuel-limited maps a changed fuel use may still move games: accept
  only if the 86-map inert diff is ≤ the 17/86 baseline.
- Every new rule writes one trace line under `LEGEND_TRACE` / `G23_TRACE` (`G24 <switch> <body> <round> <why>`) so a local game shows
  each time it fired.
- Fuel: no new per-tile loops over the whole map per body per turn; reuse `danger`, `camp_danger`, `g23_ratio`.

| switch | file:function (hook) | rule (short) | values to try |
|---|---|---|---|
| `g24_hold` (+ `_gems`, `_r`, `_hp`, `_own`) | brain.cpp combat() l.4794 isolated-flee condition; no avoid_note in that case | skip the pre-emptive isolated flee on our ≥ 30-gem task group at adv ≥ 0.8, hp ≥ 0.5 | 1 with `g23_farm 1`; `_own 1` second |
| `g24_join` (+ `_gems 30`, `_until 300`, `_min 6`, `_reach 2.0`, `_share 0.9`) | brain.cpp group_score() claimers branch l.6994-7008 | rich groups open to joiners before r300 | 1; `_until 2000` second |
| `g24_scarce` (+ `_gpc 92`) | world.cpp init (scarce_mode next to mono_mode ~l.261); group_score claimers branch | on scarce maps ≥ 12-gem gem groups take one joiner all game | 1 |
| `g24_marc_funnel` (bit 1 hand-off + bank, bit 2 carry steps on; + `g24_mf_r 8`, `_wait 6`, `_altar 12`) | group_score() hand-off ~l.6907-6933; capture_group() l.8102; bank_min() / tribute() l.6003-6013 | rewards to Marcella within 8; she banks from 20+ gems at a near altar | 1, then 3 |
| `g24_marc_focus` | g23.cpp g23_pick_target() l.224 | enemy Marcella's key ÷ (1 + bag/40), ÷ 1.3 when itemized | 1 |
| `g24_marc_threat` | g23.cpp g23_dps_of() l.60, g23_ratio() | Marcella reset ×1.5; our damage ×0.85 near her | 1 |
| `g24_lock_memory` | nearest_altar() / tribute() | +8 steps to a locked altar for 150 rounds | 1 |
| `g24_flee_dash` (bit 1 dash, bit 2 can_escape model) | combat() flee branches ~l.4764 / ~l.4815, g23.cpp g23_leave(); mob_dash() l.2495; combat() l.4239 | dash out when a chaser can hit after a walk | 3 |
| `g24_abandon_r` | group_score() l.7240 | drop a group at tadv < 0.67 (×0.5 big) unless g23_keep_farm | 0.67 |
| `g24_rescue_pw` | g23.cpp g23_veto() rescue l.453 | rescue also needs g23_ratio ≥ g23_r_join | 1 |
| `g24_fresh` (+ `_adv 1.5`) | combat() after g23_veto (~l.4576) | 40 rounds after respawn: non-killable, not-in-reach fights need adv ≥ 1.5 | 40 |
| `g24_lure` | g23.cpp g23_veto() l.471-475 | lure veto for every non-killable fight incl. rescues; 3-round hold | 1 |
| `g24_hit_is_fight` | combat() l.4583 fz_engage hold | being hit last round counts as in a fight | 1 |
| `commit_keep` (exists) | group_score join limits | a camp hit in the last 2 rounds is kept | 1 |
| `g24_dash_travel` | mob_dash() / travel dash | no low-gain travel dash with no enemy within 8 | 1 |
| `g24_bank_fallback` | brain.cpp tribute() l.6013 + turn() order | winning / endgame bag first; walk after 3 cancelled recalls | 1 |
| `g24_ward_keep`, `g24_bush_ward` | place_ward() l.3160 / 3175 | keep forward / bush wards; bush wards on bushy maps | 1 |

## 4. Order of work

Step 0 (15 min): `bots/god24` = copy of `bots/god85` with v88's four values as defaults; inert check vs `g23rcf` (must be identical on
3 maps). `tools/g23port` not needed (god24 is the only base). Commit.

Step 1 (45 min, in parallel with step 2's coding): **mechanism bench** `tools/g24/mech.py TAG [REFTAG]`: decode
`experiments/ab2/<TAG>/g/*.repl26a` with `tools/replay/decode.mjs --gold-captures` + map JSON from `/home/claude/data/mapjson_pool`,
run the streams' extractors on them (`economy/econ.py` rows, `fights/extract2.py`, `objectives/extract_obj.py`,
`execution/metrics.py`; add a `--dec DIR --out DIR` option where a script has fixed paths) and print one table: our side, variant vs
reference, for every mechanism metric named in §2 (E1 left-at-1v1 / contested capture share / hit% near enemies; E2 bodies per visit /
solo share / gems by r300; E3 Marcella capture share; F1 dash on retreat / caught8; F2 weak steps / walk-in deaths; F3 deaths ≤ 40 r
after respawn; F4 enemy-woken camp deaths; X1 wake-leave / passive wolf damage / wasted dashes; deaths, banked). Validate on
`_g23f2`-era tags: v88 vs v84 must show capfix's late-reward drop.

Step 2 — wave 1 (today; qualifiers: best version selected by 21:00Z, re-checked after 23:00Z):
1. **C1 = v88 + `g24_flee_dash 3`** (F1, a bug fix, no prior failure). Local s4 + held-out vs v88 (disaster filter), mechanism check,
   ladder ~150-250 paired games.
2. **C2 = v88 + `g24_hold 1` + `g23_farm 1` + `g24_join 1`** (E1 + E2, the biggest measured gap). Same gates; the paired plan weighted to
   the 10 worst / scarce maps (half the groups there).
3. **C3 = v88 + `g24_marc_funnel 1`** (E3, the item-gap root cause and the nemesis teams' weapon).
4. **C4** = the passing ones of C1-C3 together (if two or more passed), else C2 + `g24_scarce 1` or + F2/F3 (`g24_abandon_r 0.67`,
   `g24_rescue_pw 1`, `g24_fresh 40`).
5. Whatever beats v88 by the §5 rule by ~20:30Z becomes the selected version for the qualifiers; otherwise v88 stays.
Coding happens while the previous candidate's ladder games run (they need no CPU); local panels never overlap.

Step 3 — wave 2 (Nov 4-6): F2+F3+F4 bundle (fight entry gates), `g24_marc_funnel 3` (carry steps on), X1 `commit_keep 1` (+
`g24_dash_travel`), X2 `g24_bank_fallback`, `g24_scarce` if not in wave 1, N1 `g24_marc_focus` + N2 `g24_marc_threat`, N3
`g24_lock_memory`, `v24_build 31` on top of the economy fixes.

Step 4 — wave 3 (Nov 7-18): second-order items (F5, X3 wards, A-B-A after tracing), re-run the top-30 streams on our new live version
(the same scripts; `matches_me.jsonl` refreshed) to find the next gap; repeat.

Expected size: E1+E2 ≈ +50-70 gems a game if the estimates hold (our banked per game is ~490 in losses vs ~1,000 for winners): the first
candidate that should flip clearly more than 10 of 250 paired games. If it does not, the estimates are wrong and the next step is a
LEGEND_TRACE study of the contested contacts, not more switches.

## 5. Procedure for every candidate (binding)

1. Code behind a switch in `bots/god24/src` (default off = v88); inert check vs `g23rcf`; commit.
2. Local vs `g23rcf`: `run_vs.sh g23rcf VARIANT` and `run_vs_pool.sh heldout g23rcf VARIANT`: both ≥ −30 gems, deaths not up by > 0.5,
   0 faults, fuel p99 < 90k. **Mechanism check** with `tools/g24/mech.py` on the s4 tag: the §2 metric must move in the stated direction
   by at least half the stated amount, else the code does not do what it should — fix the code, do not go to the ladder.
3. Bundle: `cambc bundle NAME --output submissions/history/<name>_<date>.zip`, sha256 in `loop_log.md`.
4. Ladder: `ladder_cycle.py --submit NAME --note ... --best <best> --plan <next_plan output> --max 50 --min-free 20 --execute` in a
   10-minute window (never over a ranked slot); `three_way.py PLAN` after the games.
5. Verdict: after 150 paired games vs the best: net flips ≥ +8 (p ≈ 0.2) and not worse than v84 → run 100 more; KEEP if the 250-game net
   is > 0 with p < 0.2. Net ≤ 0 after 150 → DROP (log it with its mechanism numbers). Log a PAIRED line; update god23_plan STATUS and
   AGENTS.md; commit + push.
6. Qualifiers day only: a new best is selected only if its verdict is in by 20:30Z; at 23:00-23:30Z check `Selected:` once more.

## 6. Approval and open questions

For the user to settle before execution:
1. Approve wave 1 as written (C1 flee-dash bug fix, C2 economy bundle, C3 combination) with the ranked rule and the §5 verdict rule?
2. Qualifiers risk: switch the selected version to a candidate that passes §5 today, or keep v88 for the qualifiers whatever the tests
   show and ship v24 candidates from Nov 4?
3. Ladder quota: wave 1 uses the whole 50 groups/hour for ~3-4 hours today; other testing of your own (if any) would share it.
