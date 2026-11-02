# AGENTS.md: handoff context for AI agents (and humans)

Read this first. It records what has been done on this bot, what was measured, what failed, what is
running or unfinished, and what to do next, so a new agent can continue without the original chat.

- **Session 24 (Nov 2, a remote session, IN PROGRESS): GOD v23 + the ladder loop.** The user now allows this agent to submit / activate
  (ladder testing with rollback, target rank < 30). Logged in from the container (session to Nov 9). Team HouseOfCoders rank 86 / 825
  (1955); live = website v84 "GPTA 8.0.0 SHASTRA" (source not in the repo; the user was asked for the zip). Map pool is 86 (`maps/s4/`).
  **The full plan and handoff: `docs/plans/god23_plan.md`** (state, what was learned, every switch of `bots/god23`, the order of work,
  the ladder loop, pitfalls). Analysis of 130 ranked losses: `/home/claude/data/WHY_WE_LOSE_TO_MITE_AND_IC_AND_THE_FIX.md`; the method:
  `/home/claude/data/GOD_V23_METHOD.md` (copy them into docs/ before committing). `bots/god23` = gpta75 + `src/g23.cpp` (fight engine,
  messages, farming through contact, team objective layer, banking, draft roster), all behind `g23_*` switches; null check exact (70/140).
- **Session 23 (Oct 27, the user's Windows PC, 8 cores; IN PROGRESS): GOD v22.** Live = website v75 "GPTA" = the user's `god__3_.zip`,
  byte-identical to `submissions/god18.zip` (sha256 bc6abe19...) = **GOD v18** (website history: v76 GOD v19 and v78 GOD v21 were rolled back,
  v77 = GOD v20). Base chosen by the user: v75 -> `bots/gpta75` (frozen) and `bots/god22` (= god18 + `g22_*` switches, all off = v75).
  Approved plan (11 phases: rules / API audit, 70-map base strategy, IC + Mite on every map (14 groups each), why-we-lose ledger, draft
  vs patch, Ryth stuck, coverage wards, team fights "never alone" + roles + priority-channel messages, Mite-style lure & farm):
  `docs/plans/god22_plan.md`. Merged GitHub main (remote sessions 22 / 22b) into this PC's clone on Oct 27; this PC's `bots/god19`
  is now `bots/god19pc`. **Status: Phase 0 done (merge, base, prune); next: queue the IC / Mite groups.**
- **Session 22b (Oct 27): GOD v20 live (website v77 "GPTA AWAKEN", user's order); v21 candidate built, not submitted.** v20 on all 70 maps vs IC 7/70, Mite 5/70, Trzy Kwaterki 7/70; on the ladder v20 39/65 (60%) vs v18 100/210 (48%). Top-3 / ranks 4-12 / our ranked-loss study and the v21 sweep: `docs/strategy_v2/29_GOD_V21_TOP3.md` (scripts `experiments/top3_oct27/`, `experiments/god21/`). The user's stutter / high-health recall / back-and-forth complaints were measured (A-B-A near enemies 95 vs the top teams' 45-62 per 1000) but every fix lost locally (kiting, capture-recalls and the recall bait are worth keeping). `bots/god21` = v20 + switches `g21_lock`, `g21_noback`, `g21_fort` (off) + `g20_pack_until` 2000; candidate `submissions/candidates/god21_wholepack_20261027.zip`.
- **Audit (Oct 28, a remote session, no bot changed): GOD v21 and the repo state**, `docs/strategy_v2/30_V21_AUDIT.md` (data
  `experiments/v21_audit/`). v21 = v20 with the pack until r2000. Its pack follows a leader in only 5-6% of late body-turns, its time
  budget equals v18's, and it is level vs the live v18 on all 70 maps (78/140, p 0.18). It uses pre-2.0.0 draft data and no new emblems.
  The repo has a stale BUILDS row (says v21 live), `setup_session.sh` still on cambc 3.0.5, no `_icc2` recipe, ISSUES / SUGGESTIONS stop at
  v14, and 9 remote branches.
- **Session 22 (Oct 26, 12:15-18:30 UTC): no new build; GOD v18 stays.** The user rolled v19 back (website v76, 5/70 vs IC) and asked for a deep IC + ranked-loss study and a bot that beats IC, nothing on the website until told. Study: `docs/strategy_v2/28_IC_RANKED_STUDY.md` (205 IC games, 247 decoded post-patch ranked games in `experiments/ladder_oct26_v18/`; scripts in `experiments/ic_oct26_v18/analysis/`): the middle decides (70% of the gap in our ranked losses), capture lead at r300 predicts the result, IC farms as one pack. `bots/god20` = v18 + switches (all off): `g20_pack` (leader / followers, hold, rejoin), `g20_safe`, `g20_leash`, `g20_adapt` (pack only after an enemy pack is seen), `g20_farm_first`, `g20_worthy*`, `g20_pack_maps` (per-map table, `pack_maps.h`), `g20_max_area`, `g20_mid_pull`, `g20_split`. Sweep of 20+ variants (doc 28 §6-8, ledger rows `_pk*`, `_v20*`, `_null`, `_mp*`, `_mc2`, `_rich`, `_spl`): always-pack -6 to -93 vs v18, adaptive level vs v18 and better vs the pack bot on s3 but not on fresh maps; the null control (`_null`, v18 + inert code) moves v18-vs-v17 by -43: per-map and v17 numbers are chaos-dominated. Candidate zip `submissions/candidates/god20d_adaptive_pack_20261026.zip` (level, not recommended). Local games run ~1.6 s each with 2 jobs when nothing else uses the CPU (290 games in ~10 min).
- **Session 22pc (Oct 26, 11:00-18:00 UTC, the user's Windows PC, in parallel with the remote session 22): GOD v19 work** (`bots/god19pc`, renamed Oct 27 to avoid the remote `bots/god19`; = v18 +
  switches, all off = v18). **Rules now: never `cambc submit` / `submissions activate` (the user submits); unranked match groups with the live bot are
  allowed; the bot handed over must be final.** Live = v74 = `god18.zip` (the user's upload). Ladder study of v74 (200 games, 95 vs the top 10: 9 wins)
  and 349 top-12 games: doc `docs/strategy_v2/28_V74_LADDER_STUDY.md`. Key: unopposed, v18 farms as fast as IC does against us (equal per 100 rounds
  r0-900); vs IC we get half from r50 on (the middle band: 56 of 108 gems by r150 unopposed, 11 vs IC; vs ranks 11-80 our wins had 49 middle gems by
  r300, our losses 18); when locally outmatched we choose to fight 44% (they 31%) and die in 27% of those. Local bench (`tools/abbench.py` on
  `cambc run-batch`, 140 games in ~2.5 min; deterministic: v18 vs v18 = 70/140, v18 vs v17 = 85/140 +154 as on Linux), variants via
  `tools/mkvariant.py`. Screens vs v18 so far all level or worse: builds (`g19_build`), farm-through contact (`g19_hold`), team targets
  (`g19_team`), middle priority (`g19_mid`), opening deathball, C&I for Marcella with pair caution (+16..+41 on s3, level held out), flee
  thresholds; the 25-shard "behind" screen moves none of them. Best vs v18: `_F4` (flee less + C&I for Marcella with pair caution +
  fight_back_margin 1.0) 82/140 +81, but vs v17 only 50% -14 (v18: +154): non-transitive, v18 stays best on the {v18, v17} panel.
  Ghost opponent (`tools/ghost/`, IC's recorded actions) does not work (open loop: v18 kills it 35-0). **No new submission recommended
  (Oct 26 23:30 local)**; the ladder A/B tool for any future upload: `tools/paired_groups.py` (plan in `experiments/ladder_oct26_v74/paired_plan.json`).
  Patch notes text: `docs/patch_notes/week4_20261026.txt` (engine-checked).
- **Session 21 (Oct 26, 07:30-13:00 UTC): SHIPPED GOD v18** (`submissions/god.zip` = `god18.zip` sha256 bc6abe19…, `bots/god18`, history `god_v18_20261026.zip`; doc `docs/strategy_v2/25_GOD_V18.md`). Patch 2.0.0 (Sprint 3): CLI 4.0.0 / engine 2.0.0 (`sdk/` = 4.0.0; the 84-item backpack), 70-map pool `maps/s3` (40 old + 30 new), replay decoder for the 42,840-byte snapshots, ledger rows in `experiments/results/ledger_v4_0_0/`. Ladder study of v17 after the patch (`experiments/ladder_oct26_v17/analysis/`: 16 losses, 10 IC and 10 Mite wins): mirror drafts; the gap is camp hits (922 vs 1,348 a game, damage per hit equal) lost to near-enemy walking; strong teams keep farming through contact. v18 = v17 + contact discipline + `g18_osc` + `g18_fast_init` + `mi_pick` 3: vs v17 85/140, +154 [+55, +248] on `maps/s3`. Level or worse (off): every new emblem, Ren / Varg / C&I swaps (Varg for HoR and Tavi for Ryth: see doc 25), more middle camps, the prior everywhere (new maps -85) or nowhere (contest copies -254). Map-refresh laptop flows ported to 4.0.0 / 70 maps (runbook doc 26). Never submitted or activated.
- **Session 20 (Oct 25, 10:30-15:00 UTC): SHIPPED GOD v17** (`submissions/god.zip` = `god17.zip` sha256 5d0201bd…, `bots/god17`, history
  `god_v17_20261025.zip`; doc `docs/strategy_v2/24_GOD_V17.md`) and the camp bot (`submissions/god16_camp.zip`, `bots/god16`, doc 23: level with
  v15, 48.5% over 334). The user: "get all the matches of our live bot (v71 on the website = GOD v15), see the lost ones, beat IC and Mite 5-0".
  Data (read-only with the user's CLI login, nothing submitted): `experiments/ladder_oct25_v15/` (our match list, the 10 IC / Mite games, gap
  tables). Findings: **Mite's bait** (every body recalls at the end of its turn, cancels next turn; v15 posted every recalling Mite carrier as a
  team OPPORTUNITY); v15 farms half the camp damage of the teams that beat it; unopposed pace 952.7 rounds (vs idle) and on 9 maps no faster
  than their contested finish. GOD v17 = v15 + `g17_fakerec` 3 + `g17_bait` 1: vs v15 192/334 = 57.5% [52.1, 62.7], +98 [+30, +171], level on the
  proxies. Measured level or worse and off: squads (`g17_squad`, pace 1,158-1,304), deathball mimics (7/80, 2/80), `g15_calm` + `g15_fwalk`
  (52.1%), `g15_fwalk` + fakerec (43.2%), grouped stance, `g17_opp_r` 6, fewer shop recalls (pace 980-1,008), IC / Mite / VT / LL / wbg / pbg drafts
  on our brain. **Method**: `g17_shop_cap` 25 (testing only) makes a body that loses to v15 like v15 loses to IC (330-1,005, deaths 11.8-6.7): the
  play-from-behind screen; nothing tried there gained more than +15 (`g15_fwalk`). **Next**: the ladder loop (the user submits; unranked groups
  vs IC / Mite; analyse those games); a squad farm that does not idle the followers; pace work (61% of unopposed body-rounds are walks).
- **Session 19 (Oct 25, 06:00-11:30 UTC): SHIPPED GOD v15** (`submissions/god.zip` sha256 2b05b91e…, `bots/god15`, history `god_v15_20261025.zip`;
  doc `docs/strategy_v2/22_GOD_V15.md`). The user: 20 ladder losses of v14 (0-20, banked 197 vs 1,110; `experiments/ladder_oct25_v14/`), "change the
  strategy and the drafting, share ward outputs, use gold and emblems, use locks, beat their bots and beat or tie v14", then IC's and Mite's data
  (fetched read-only with the user's CLI login, nothing submitted: `experiments/ladder_oct25_icmite/`, 1,144 matches, 257 replays). GOD v15 = v14 +
  `mi_capture` 1 (the gold funnel) + `gold_value` 0.5 + `g15_lock` 15: vs v14 194/334 = 58.1% [52.7, 63.3], +113 [+35, +180] over 167 maps, 0 faults.
  Measured level or worse and off: `g15_calm`, `g15_fwalk`, `g15_sight`, `g15_build`, `mi_capture` 2, `tribute_min` 38, `max_wait` 30, `half_grade` 0.5.
  Method facts: the `_px_*` proxies (v10's brain) farm 1% near an enemy (ladder 16%) and v14 was selected on them, so pairing with v14's games there is
  biased; judge on h2h vs `_f4ec` (= bots/god14) over the extended pool. Unranked groups only play the live submission. **Next: the second bot**
  `bots/god16` (= god15 + `g16_camp`, hunt at their altar then camp their spawn), the user's idea; the IC / Mite drafts on v14's brain (`_d_ic2`,
  `_d_mite`) are built but not screened. Setup: `env -u no_proxy -u NO_PROXY pip download cambc==3.0.5`, toolchain by curl, 2 CPUs (~0.3 games a second).
- **Session 18f (Oct 24 22:20 - Oct 25 03:20 UTC): SHIPPED GOD v14** (`submissions/god.zip` sha256 5726664c…, `bots/god14`, history
  `god_v14_20261025.zip`; doc `docs/strategy_v2/21_GOD_V14.md`). The user: "v12 stutters, does not move or moves randomly, walks away
  from the altar with good gems, does not compete with enemies the right way, monoliths are not killed, wards are thrown at random
  tiles: throw them into bushes". Measured first (`experiments/behav_oct24/`, `tools/analysis/behav.mjs`, `mono_kills.mjs`, `trace/`)
  against the 600 ladder replays' teams, traced the causes (LEGEND_TRACE IDLE lines), fixed behind switches (all 0 = v13), screened 22
  candidates (h2h vs v13 `_e_p10`, 8 roster families paired vs v10, 3 team proxies paired vs v13). GOD v14 = v13 + `fz_dead` 1 (close in
  over dead group tiles), `ward_v14` 1 (wards into bushes), `fz_engage` 6, `fz_chase` 4: 4 real rosters +209.6 [+113, +310] (v13
  +120.6), proxies +171 [+78, +264] over v13, h2h vs v13 47/80 +105; 126/160 wins vs IC / prism best girl drafts (v13 111), deaths 9.0
  (11.5), monoliths 60 to 20 (35 to 30), wards 36% on a bush (6%). Off (measured worse or level): monolith team plan `mono_v14`, `fz_dash`,
  `fz_osc`, flip margins, unstick 6, `stall_dash_off` 40, `ward_open`, `fz_wardblock`. Wards occupy their tile (allies walk into them).
  Candidate `submissions/candidates/god_v14_wards_dead_20261025.zip` (`_f2dw`: best h2h vs v13, 57/80 +287). New variants: `SRC=bots/god14`.
- **Session 18e (2026-10-24, 22:10 UTC): SHIPPED GOD v13** (`submissions/god.zip` sha256 125a87c6…, `bots/god13`, history `god_v13_20261024.zip`; doc
  `docs/strategy_v2/20_IC_OCT24.md`). The user: "fetch Intercontinental Fish's data, beat them, improve on v12; combine v10, v12 and the IC data". IC
  (rank 2) analysed from today's ladder archive (300 matches, 73 replays; fetching more needs the user's `cambc login`: `ladder_fetch.py --team ID`).
  GOD v13 = v10's brain + v12's map analysis / draft memory + the strong teams' per-map pick prior at weight 1.0: vs the 4 real strong rosters
  +120.6 gems a map [+25, +221], vs IC's draft +120, h2h vs v10 47/80. Proxies `tools/ic/make_team_proxy.py` (`_px_ic`, `_px_ic2`, `_px_pbg`, `_px_wbg`),
  cells `tools/ic/cells.py`, rosters `tools/god12/screen.py`. Anti-IC candidate (+ ownership 0.1: +222 vs IC's draft, worse vs Prism / Willow teams):
  `submissions/candidates/god_v13_anti_ic_20261024.zip`. `bots/god12` is again exactly the v12 zip; new variants: `SRC=bots/god13 tools/variant.sh`.
- **Session 18d (2026-10-24, 20:15 UTC): GOD v12 built at the user's request** ("push a new bot with everything we did today"; then "use all the
  switches with every new feature on"): `bots/god12`, zip `submissions/god_v12.zip`, doc `docs/strategy_v2/19_GOD_V12.md`. It is GOD v10 + map
  analysis + draft memory v2 + the DL tables + the live bytes + the teamplan rules, every new switch on. **Measured worse than v10** (h2h 29/80, -160 gems
  a map vs 8 forced rosters), so `submissions/god.zip` stays GOD v10. The best subset (pick prior + ownership) is level: `submissions/candidates/god_v12_prior_own_20261024.zip`.
  Screens: `python3 -I tools/god12/screen.py VARIANT --slots 0,...,7`; variants `SRC=bots/god12 tools/variant.sh NAME key=value`.
- **Session 18 (2026-10-24): MAP ANALYSIS. Read `MAPAnalysis.md` first: it is the only record of the current work** (map analysis,
  map model and exact-match map table for the user's new bot; no bot is built or shipped in this work). **Everything else in this file,
  and the older docs it points to (`docs/strategy_v2/`, `docs/ENGINE_FACTS.md`, `SUGGESTIONS.md`, `ISSUES.md` before its map-analysis
  section, the bots in `bots/`, the ledgers and test pools), predates the Oct 20-22 patches and is NOT an input to the map-analysis
  work** (the user's source rule, `MAPAnalysis.md` section 1.7). Session 17's ladder study is in `god2_session17/README.md` (context only).
  **Team play, navigation and the final draft-memory layout** (a second session, Oct 24): `TEAMPLAN.md` (code in `tools/teamplan/`,
  spec `docs/DRAFT_MEMORY.md`, results in TEAMPLAN.md section 11, the implementation prompt for the map-analysis agent
  `docs/PROMPT_DRAFT_MEMORY_V2.md`); `MAPAnalysis.md` section 1.9 says what concerns the map analysis.


## Standing rules (read before doing anything)

- Competition: Cambridge Battlecode 2026a (CAMBC), 12 Oct to 18 Nov 2026. C++ bot compiled to wasm; CLI `cambc` 4.0.0, platform engine 2.0.0.
  A submitted bot cannot change and keeps nothing between matches (learning is offline or in-match).
- **Never `cambc submit` / `cambc submissions activate`: the user uploads and activates.** Read-only CLI use and unranked match groups
  with the live bot are allowed (team quota about 50 groups per rolling hour). Deliver zips under `submissions/` and say so.
- Test panel (user, Oct 27): every candidate vs v75 (`bots/gpta75`), v17 (`bots/god17`) and the IC clone on `maps/s3` + held-out
  pools (`gen2`, `gold3`, `var17`); then the user's upload and paired ladder groups decide (`tools/paired_groups.py`).
- No per-map tables or fixed drafts: decisions come from map features computed at runtime.
- One branch, `main`: `git pull` (merge, never force) before every push; no PR unless asked. Update this file at every step, keep it short.
- History before Oct 24 (sessions 1-17, sections S7-S15): `docs/history/AGENTS_ARCHIVE_S1-S15_20261021.md`.
