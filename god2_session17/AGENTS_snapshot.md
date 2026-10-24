# AGENTS.md: live handoff file (read this first after any context reset)

Last updated: **2026-10-22 ~20:45 UTC (session 16, "live ladder loop", building bb4)**. Older history (sessions 1-15, legend m1-m15,
GOD v1-v11, every local A/B number) is archived verbatim in `docs/history/AGENTS_ARCHIVE_S1-S15_20261021.md`; read it
only when you need a specific old measurement. Keep THIS file short (< ~400 lines): prune old log lines when it grows.

## 1. The task (the user's words, session 16)
- Login to the platform through the CLI (done), **play unranked matches vs the real top 15-20 teams with our current bot,
  analyse why we lose and what their strategies are (ours and theirs), build an improved bot, submit it, test again,
  iterate.** Stop only when our bot beats top-league teams by a 2-3 margin (e.g. >= 3-2 in 5-game groups) consistently.
- **Submitting is pre-authorised** (submit on your own). **Push to GitHub only when a bot is measured better than the
  previous one** and deserves it.
- **Do not hardcode drafts, strategies or moves.** The organisers change maps/camp clusters and nerf over-used champions
  (patch every few days): everything must be derived at runtime from the engine (champion designs, camp stats) and the map.
- Learn from the top teams' real games, especially **Intercontinental Fish** (rank 1 for days; the user thinks it is
  sandbagging with a weak submission and will upload its best near the deadline). Do not rely on local proxy bots:
  "we beat the proxy bots but get defeated again and again in the real matches".
- Keep this file updated at every important step so work survives context compaction.
- **bb4 (user's design, Oct 22 ~19:30; bots/bb4 = god + modules, every piece behind a bb_* param, nothing hardcoded)**: roles from
  engine stats (roles.cpp: front / assassin / ranged / support); archetype draft by terrain class (compact walls+bushes -> all melee
  + support; open holes -> 2 front + 3 ranged; balanced -> 2 front + support/assassin + 2 ranged); 3-phase play = the stance bandit
  (spread / grouped / push) with archetype priors + territory context, switching when windows lose; shared memory as a call register
  (caller, kind RESCUE/AGGRESS/REGROUP, named responder, ACK); ranged never lead (formation); frontliner scouts regions; territory
  regions (k-centre clustering of groups) with chain value, front line (furthest held region), territory share; wards keep the spot
  that saw enemies and face their nearest region; monoliths by team capability (mono_team 1 = obj_team_ready); dash/crystal routing
  already in nav (dash_holes, hops).

- **SESSION 17 TASK (Oct 23 ~14:00 UTC, supersedes the bb4 line): build "god2" on the user's god.zip** (= git 28d7340, GOD v8 +
  opponent model, byte-identical; restored as `bots/g8`, builds on 3.0.5). Study ONLY the strongest teams: prism best girl (#1),
  Intercontinental Fish (#2), Claudus Maximus (#19, new, 92 games) and every top-50 team with > 65% recent win rate: strategy,
  decisions, play style, what they do in each situation; adopt the principles without their weaknesses (draft, strategy, items),
  exploit their shortcomings; do not copy blindly. Judge ONLY with real unranked games (CLI) on all 40 maps x both sides; god2 must
  be proven >= god.zip by playing BOTH vs these teams. Plan: `docs/plans/god2_plan.md` (phases: baseline S0 -> study workflow ->
  build behind switches -> ladder loop -> back-to-back final proof).

- **Session 17 state (15:30 UTC)**: study teams = prism best girl, IFish, Claudus Maximus + group win rate > 65% over the last 30 groups:
  Pantheon (#6), conqueror_of_openai (#18), Nyx (#31) (`tools/live/top_winrates.py`, `experiments/live/top_winrates.json`; game-level
  win rates are all <= 63%: ratings have converged). Data: `C:/battlecode/cache/t2/<pbg|ifish|cm|pantheon|coo|nyx|s0>/` (replays +
  index.jsonl), fight dumps `C:/battlecode/cache/t2dump/<key>/`; `tools/live/dl_replays.py` downloads any listed matches. Workflows:
  hygiene port (bots/g8h = g8 + fuel/stuck fixes, report experiments/top2/g8h_port.md), study (7 analysts + verifiers ->
  experiments/top2/an_*.md). Rules check: tribute is NOT interrupted by damage; stun, death or a NEW altar lock cancels it (prism best
  girl's Prism tributes 200-380-gem bags over 20-38 turns and the team buys no locks).

- **Session 17 progress (18:45 UTC)**: S0 = god.zip 13-227 vs the top 3. Study done (experiments/top2/an_{draft,opening,economy,items,
  fights,weak,playbooks}.md; verifiers died at the session limit, claims unverified; gap analysis experiments/top2/gap_g8.md: we farm
  4.4% vs 15.9% with an enemy near, deaths 14.9 vs 6.1, max HP r1000 1,733 vs 3,122, middle gems 126 vs 594). bots/g8h = g8 + hygiene
  ports + 3 review fixes (no-progress clock reset, pocket entry clock, hop floors 40k/30k) + per-enemy recall-spam filter: local vs g8
  40/80, fuel-outs 1.9 vs 16.6. **bots/god2 = g8h (frozen base)**; modules are built in copies and merged as patches
  (experiments/top2/patches/*.patch, reports mod_*.md): `load` (mine: mapdraft 8 role-slot draft from engine designs -> Ve/Ho/Vd(/Ma)(/Ry)
  by team size; build_style 20 health-weighted builds by role) local vs god2 54/80, gems 833-567, deaths 10.0-17.3; agents: `bank`
  (bank-often + recall gate), `deny` (lock/stun denial of big tributes, carrier targeting), `fight` (farm-through + fight gates + chase).
  god2_load submitted as version 57 (18:45), sweep label G2A.
- **19:45 UTC**: the module agents died at the usage limit with built but unreported copies (bots/god2_bank / _deny / _fight); merged
  by `python tools/top2/merge_modules.py god2b god2 god2_load god2_bank god2_deny god2_fight` (2 conflicts resolved by hand in combat():
  deny block, then fight block). Local vs god2_load: god2b 32/80 (deaths 17.1-9.8); leave-one-out: no fight 34, no bank 30, no deny 31
  (local mirrors mislead; the ladder judges). **god2b has an in-bot A/B** (g2ab.h/.cpp, P.g2ab_n 8): each game = one on/off combination
  of bank (bit 0), deny (bit 1), fight (bit 2) from strat_hash(W, H, camps, side, 0) % 8 (`variant_of.py 8 --nomask --bits`); macros
  G2B_ON / G2D_ON / G2F_ON. G2A so far 7-163 (vs S0 13-227 on the same cells: flips +3 / -4): the new draft + health builds alone do not
  move results vs the top 3.
- **20:20 UTC**: **G2A final 12-228** (S0 13-227); paired on 200 cells: flips +7/-7, deaths 14.4 -> 12.3, banked 341 -> 319, opponent
  1,028 -> 1,031 (their drafts identical in 200/200: they did not resubmit). **The gem gap is farming**: camp gems ~420 vs 1,050-1,090 a
  game for every opponent, bags lost/stolen only +-50 net (gap_g8.md: farm share of alive time 41% of the gap, dpf 31%, dead time 14%,
  target value 13%; they stand on respawning groups 71 rounds/body vs our 20 and hit respawned groups at 28 rounds vs our 37-49).
  **god2b = version 58 (20:17)**: + module `mid` = the v53 "middle" bit ported (value x (1 + 0.6 mid^2), middle threat veto 1.0 with
  allies within 12, half_grade 0.3, respawn wait 35, golem team plan; Group::golem added), in-bot A/B now **16 variants** (P.g2ab_n
  16: bit 0 bank, 1 deny, 2 fight, 3 mid; on-counts over the 80 cells 41/46/39/43). Local smoke on the 6 golem maps: 0 faults,
  fuel-outs 1.7 vs 1.2. Sweep label **G2B** (setF_top3); analyse with `variant_of.py 16 --nomask --bits` + per-cell deltas vs G2A/S0.
- **21:15 UTC, fight module traced (debug build, PT / G2F lines; `tools/top2/pathtrace.py team-a.stdout`)**: its C8 farm-through
  applies to 2.7% of contact turns (bodies are walking, not hitting a camp, when an enemy shows up); it mostly acts as C3 commit (keep
  fighting at own hp >= 35%, ch >= 0.6: 510 of 2,448 decisions) -> local fight-only vs god2_load 36/80, deaths 15.6-10.2, farming under
  contact 6.6% vs 5.3%. Our steps toward enemies: combat fight 30%, **rally answers 27%** (respond_to_alert: any body within rally_r 9
  walks to every fight an ally posts, farmers included), flee steps 22%, farm 13%. **Calm** (params g2f_calm / g2f_calm_slack /
  g2f_calm_out / g2f_rally_farm_d 4 / g2f_rally_r 6, default off in god2b; test copy bots/_g2c = fight + calm, commit off): no walk
  toward an enemy we cannot hit next turn (unless killable, channelling, hitting an ally within 3), no pre-emptive walk-away unless
  mh < 0.6, rallies answered by a farmer only within 4 and by others within 6: local vs god2_load **39/80**, gems 726-745, farming
  18.8% vs 17.2%, under contact 9.3% vs 5.3%, walk-to-fight 132 vs 156 rounds/body, dead 9.9% vs 6.6% (without the rally gate 27/80).
  G2A vs S0 mechanism (239 paired cells, `tools/top2/g2_mech.py DIR N --ref DIR`): walk-to-fight +16, dead -1.7 pts, farm +0.6 pts.
  Mechanism metrics per A/B bit: `python tools/top2/g2_mech.py C:/battlecode/cache/t2/g2b 16 --ref C:/battlecode/cache/t2/g2a`;
  outcome effects: `python tools/top2/g2_effects.py G2B 16 --ref G2A,S0` (placebo noise on G2A: margin SE ~53, so >~100 to read).
- **21:40 UTC, walk budget** (module `walk`, P.g2w_walk, default 0; an_playbooks A2: walking share is the strongest behavioural
  predictor for all six teams; ours 68% of alive time vs their 53-60%): group_score time += g2w_walk x walking rounds to the group.
  Unopposed pace unchanged (god2_load 1089.5, walk 0.5 1085.0). Local vs god2_load: **walk 0.5 47/80** (gems 717-660, deaths
  12.0-13.5), walk 1.0 45/80, walk 2.0 37/80, walk 0.5 + calm 32/80. Calm variants all 34-40/80 (calm_out 0.9 / 1.2, god2 group veto,
  ml2 0.2 change nothing: calm farms more but trades worse). In-bot A/B is now configurable: P.g2ab_mods = one hex digit per bit
  (0 bank, 1 deny, 2 fight, 3 mid, 4 walk; version 58 = 0x3210). Partial G2B (41 games): mid camp gems -108 +- 37 vs G2A.

## 2. Environment (the user's Windows PC; NOT the old cloud container)
- Repo: `C:\battlecode\Cambridge_Battlecode` (branch `main`, remote `origin` = github.com/Akshayg005/Cambridge_Battlecode,
  pushes work through the user's credential manager). Outer `C:\battlecode` is an unrelated starter workspace.
- Shells: Git Bash (`bash` tool) and PowerShell. **Use `python`, not `python3`** (python3 is the MS Store stub).
  Python inside Git Bash needs Windows paths in code strings (`C:/battlecode/...`, not `/c/battlecode/...`).
  Set `PYTHONIOENCODING=utf-8` (team names contain unicode). node is installed. 8 cores, 16 GB.
- cambc **3.0.5** (pip), SDK 3.0.5 (`cambc init --yes` is the non-interactive init), engine **1.0.3** locally = platform.
  Logged in on 2026-10-22 (session lasts 7 days; re-run `cambc login`, the user approves in the browser).
- A local game takes ~30 s (`cambc run A B --map NAME --release --statistics out.json --json -o DIR`).
- Platform API is rate-limited (HTTP 429): always go through `tools/live/cli.py` (retry with backoff), <= 4 parallel jobs.
- Data cache outside git: `C:/battlecode/cache/summ/<matchId>.bin` (binary summaries, ~120 KB each).

## 3. Platform workflow (tools/live/)
- `cambc ladder --json --limit 100` -> `experiments/live/ladder_<date>.json`; `experiments/live/top40.tsv` (rank, id, name, rating).
- `python tools/live/fetch_matches.py --team <uuid|me> [--kind ranked] --max N --out experiments/live/lists/<x>.jsonl`
  (match lists with drafts and results; merges by matchId). `tools/live/fetch_top.sh N MAX` does the top N teams.
- `python tools/live/summ.py fetch LIST.jsonl [--teams names.txt (both teams listed)] [--any names.txt] --jobs 4`:
  downloads summaries (`cambc matches summary ID -o x.bin`), converts (`cambc summary`), writes compact records
  `experiments/live/compact/<matchId>.json` (drafts, per-champion metrics + final items, deaths, kills, camp clears,
  gem collections / submissions / losses, purchases, wards, team gem timeline, fuel-exhausted events).
- Unranked groups: `cambc match-groups create <OPP_TEAM_ID> --maps m1,m2,m3,m4,m5 [--sides a,b,a,b,a]` (team quota **50
  groups**, 0 used at 12:00 UTC Oct 22; `cambc match-groups quota --json`), then `match-groups show/download <id>`.
  Groups use our team's CURRENT submission. `cambc submit god` uploads `bots/god` source.
- Ranked play is automatic and frequent (~30 ranked games/hour for us): a free, large evaluation signal after each submit.

## 4. State at session start (2026-10-22 12:00 UTC)
- We are **HouseOfCoders**, team id `5a103c90-b00b-4d46-8ace-6a3bb058dc72`, **rank 30 / 744, rating 1922**.
  Ranked record Oct 21 09:00 - Oct 22 12:00: ~50% (about 15-15 every hour).
- Top: 1 Intercontinental Fish 2245, 2 prism best girl 2236, 3 :3 2160, 4 procless 2158, 5 new team(4) 2116,
  6 policy wonk 2103, 7 EMPEROR Tung 2075, 8 Univardisty of Shingtonwash 2069, 9 Tartarus, 10 Trzy Kwaterki, ...
- On the ladder: **GOD v10** (`bots/god`, `submissions/god.zip`, shipped Oct 21 16:44 UTC by session 14): dynamic draft from
  engine designs + map features, typical drafts Vendetta(2), Vesper Vale(1), Heart of Ruin(11), Ryth(0), Marcella(6)/Varg(9).
  It builds on SDK 3.0.5 (warnings only). Local A/B claimed 57% vs previous build and big wins vs proxies: did not
  translate to the ladder.
- Map pool: 40 maps (`cambc maps list`): 25 `00*` (old + new: gem_fields, gemfight, great_wall, lost_world, quadrants,
  reverse_spiral, road_of_riches, split) and 15 `01*` (big_world, boss_battle, broken_curve, concentrated_wealth,
  corridors, elk_arena, fracture, gold_rush, hooks, islands, shortcut, starfish, starvation, the_farm, yellow_brick_road).
  Local files `maps/00*.map26a`, `maps/01*.map26a` (hyphens instead of underscores).

## 5. Game essentials (patch 3.0.4 values; engine reports designs at runtime, GOD reads them)
- First to 1000 banked gems wins; round 2000 tiebreak: gems, then gold earned, then kills, then team B.
- Champions (draft ids): 0 Ryth, 1 Vesper Vale, 2 Vendetta, 3 Cassi&Issac, 4 Stellar, 5 Prism, 6 Marcella, 7 Willow,
  8 Ren, 9 Varg, 10 Tavi, 11 Heart of Ruin. Platform `draftPicks` use these ids.
- Patch week 2 (Oct 20): camps devalued (wolf 4 gems/40 gold, elk 15/90 range 4, gem cluster 120hp/7 gems, gold cluster
  120hp/20 gold, monolith range 5), Golem added (5000hp, str 120, range 4, 160 gold, 36 gems, respawn 80), kill reward
  100 gold, ward cooldown 10, altar lock 5 hp, Heart of Ruin added. Week 3 (Oct 21, 3.0.4): Stellar/HoR/Ren nerfed;
  Vesper, Vendetta, Tavi, Prism buffed. Texts: `docs/patch_notes/`. Rules: `docs/sprint/v3_0_4/GameRules.md`.
- Summary event semantics: `death`/`gemLoss` owner = victim, target = killer; `kill` owner = killer; `gemCollection`
  owner = collector (context campGroup or champion).

## 6. Live loop protocol (each iteration)
**USER RULES (Oct 22 16:40 + 17:45 + 18:35):** train and test ONLY against the top-10 teams (others copy them; ladder noisy there).
Fix champions getting stuck first (the user sees it in most matches). A/B test EVERY bot (local vs the live version first; then the ladder). Live/blind
submissions are allowed when they help analysis (rank can be recovered with a better bot). Do NOT copy/imitate top teams:
analyse, find measured gaps, design our own answers. Use ML where it helps (bandits/RL, k-means clustering, models trained on
ladder games). Analyse more before coding; build several distinct strategies; drop the losers. Unranked groups can only use the LIVE submission (no version flag in `cambc match-groups create`).
1. Data: refresh lists (top 20 + us), fetch compact summaries for top-vs-top games, our losses, ifish games.
2. Analyse (tools/live/analyze*.py): per map / draft / phase: gems over time, first capture, deaths, gem losses,
   build orders, where and when fights happen; ours vs winners.
3. Change `bots/god` (runtime-derived logic only). Local sanity: builds, 0 faults, no crash, quick h2h vs previous
   version on the 40-map pool (only to catch regressions; proxies are NOT the judge).
4. Submit (`cambc submit god`), record version + time in §8. Queue unranked groups vs top teams; watch ranked rating.
5. Judge on real games only (unranked vs top 20 + ranked results since submit). Push to GitHub if better.

## 7. Findings log (newest last; keep each to 1-3 lines)
- **Baseline (Oct 22 12:10-12:45): GOD v10 vs ranks 1-10, 10 groups x 5 = 50 games on all 40 maps: 12-38 (24%)**
  (ifish 0-5, prism best girl 3-2, :3 0-5, procless 1-4, new team(4) 1-4, policy wonk 3-2, EMPEROR Tung 2-3,
  Univardisty 1-4, Tartarus 1-4, Trzy Kwaterki 0-5). Group ids/maps/sides in `experiments/live/groups.jsonl`
  (label v10): **re-run the SAME 10 groups (opponent, maps, sides) for every new version = paired comparison.**
- Games vs top teams are decided by r200: in our 38 losses gold 234 vs 421 at r100, 511 vs 953 at r200; camp gems
  21 vs 53 (r100), 48 vs 122 (r200); the gap only grows (r800 gold 2278 vs 5757). In our 12 wins we are level at r200.
- Our deaths vs top 10: 10.2/game (57% mid-map, 32% on our own half, only 11% deep in theirs; 2/3 after r400).
- Top-team builds (tools/live/items.py): EVERY top team buys **Treasure first** (melee Th, ranged Ts), then Jungle /
  Bruiser, then the damage stat for ever. IC's Vesper = hyper-carry: 43% of IC gold, 20 Power-strength emblems/game.
  Ours (v10, build_style 2): Monster first, few shards.
- Draft is NOT the gap: top 20 draft HoR / Vesper / Marcella / Ryth / Vendetta (+ Prism for #2, Stellar/Ren/C&I for
  IC's other half) and so do we (`tools/live/lists_report.py`).
- Replays (`cambc matches download`, decode with `CAMBC_CACHE="C:/Users/Anjali Gupta/AppData/Local/cambc/assets"
  node tools/strategy_v2/s13/track.mjs FILE from to step team`): hooks: 2 of ours walked into the enemy's 4-body
  elk group r13-31 and died; procless's 4 bodies opened together on their own elk. gold_rush: our 3 bodies took
  monolith-group damage at r21-31 (clusters fused to the monolith wake it), then invaded and were wiped r61-161.
  elk_arena (contest map): lost the first brawl, then scattered to far gold while IC held the centre (36 gems / 60 r).
- Golems (new camp, 5000 hp, 36 gems; quadrants' golem group = 120 gems + 160 gold) are on 6 maps (great_wall x2,
  lost_world, quadrants, reverse_spiral, road_of_riches, split). v10 never scores them (solo needs ~12 heal trips;
  pair plans off); procless took quadrants' at r152.
- **Init fuel**: every body spent rounds 1-3 in `World::init_static` (quadrants ~308k fuel; big_world group loop 139k +
  altar-block scan 119k). Allocation-heavy per-group work (bitboards, vectors) is the cost (-O3 already).
- Unranked quota = **50 groups per rolling hour** (`resetsAt` in `cambc match-groups quota --json`).
- **Unopposed pace** (`python tools/live/pace.py BOT --tag T`: BOT vs idle on the 40 maps, ~40-100 s): v10 988.5, v11 1022.4
  (golem plan +100-500 on golem maps), no-golem 1004.7. Per-map pace is CHAOTIC (identical logic +-300 rounds from fuel timing):
  trust 40-map means only. Param sweep (19 values): only hysteresis 1.3 helps (989.3); the rest neutral/worse.
- Top-5 winning games vs top-20 take ~1.11x our unopposed pace on average: our pure farming is NOT the main gap except gem_fields
  (0.52) and golem maps (quadrants 0.75, great_wall 0.77, road_of_riches 0.82, reverse_spiral 0.83). The gap is contested play.
- Time use vs top 10 (replays, tools/live/timeuse_agg.py): r1-300 we farm 18.5% (them 25.2%), walk 57.7% (50.1%), dead 8.2% (7.2%);
  r300-800 farm 13.4% (21.6%), dead 14% (8%). Our dying champion's max HP = 0.69 of its killers' (theirs 0.94): item gap.
- **Blob / squads (IC copies) FAILED in GOD**: whole-team blob pace 1300-1650 (slower on every map), vs v11 33.8%; pairs 1145 pace,
  36.2% vs v11. GOD's per-body farming is faster; IC's blob works with its own movement + fights. Code stays behind blob_until/squad_size.
- **LOCAL h2h vs our own builds does NOT predict the ladder**: v12 beat v11 61% locally, ladder flat (10-40 vs 11-39).
- Deaths (tools/live/deathmode.mjs): 38% of ours happen while only moving (fleeing/walking, hp 0.40 three rounds before),
  40% fighting; theirs 15% moving, 48% fighting. Making bodies trade instead (ml2_cornered 0, ml2_leave/flee 0.4) lost 34-42%
  locally vs v11 with MORE deaths: the ml2 leave rule saves lives; not shipped.
- golem_trips (start golems solo with more heal trips) slower on the 6 golem maps (915 vs 850): off.
- Our contested banking rate vs top teams ~0.45/round vs their ~0.9 (= our unopposed rate): they disrupt us, we do not
  disrupt them (deaths 10 vs 4-5 per game, our dying bodies have 0.69x their max HP).
- **Engagements (tools/live/engage.mjs, 919 in the baseline)**: outcome follows MAX-HEALTH SUMS (item power), not body counts:
  kill ratio 1.63 when ours > 1.15x theirs, 0.68 even, 0.21 when theirs > 1.15x ours (418 of 919!). They START 259 of those
  (our deaths 203, theirs 27); we start 159 (95 vs 36). But a power gate (v13) LOST on the ladder: caution costs more than it saves.
- Items: our max HP r400-1200 1773 vs their 2506; gold spent by r800 2816 vs 4995; health share of spend 34% vs 41-42%.
- **Champion effects (logistic regression, 4,300 ranked games, outcome ~ rating diff + pick diffs; logit)**: Prism +0.26,
  Vesper +0.19, Vendetta +0.10, C&I +0.05, Willow +0.04, Tavi -0.03, Marcella -0.04, Varg -0.06, HoR -0.10, Stellar -0.11,
  Ren -0.13, Ryth -0.17 (rating: +0.20 per 100). Draft prior `pd_ladder` (draft.cpp ladder_prior, follows engine power like
  stat_prior): weight 1 -> Prism 26/40 maps; 2 -> Prism 40/40, no Ryth; 3 -> + C&I 28, Willow 17, HoR 10.
- Set B (`experiments/live/setB.json`, `python tools/live/groups.py runset experiments/live/setB.json LABEL`): 10 groups vs
  ranks ~4-20 not in set A (Pantheon, Sponge, Zarzorki, Let's LARP again, ひななー, NTU, NEETCoders, Noobot, caterpillow, hello).
- Waiting for a submission to go live: `tools/live/wait_draft.py DRAFT_ID --after ISO` (draft change) or `moved_early.py`.
- IC's blob pipeline (replay quadrants): all 6 bodies together, Vesper captures, the others move on at once; bodies bank when
  passing an altar; golem (120 gems) taken by 2. procless kills golems in waves (2 tank with 1300-1700 HP, 2 recall/heal/return).

- **Session 16 evening analysis (50 v10 replays vs top 10; tools/live/opening_caps.mjs, first_moves.mjs, walks.mjs, halves.mjs,
  mapzones.mjs, bodylog.mjs, fightwalks.mjs, abandon.mjs; trace: tools/live/trace_walk.py on a LEGEND_TRACE build):**
  - Unopposed our opening equals theirs (first capture r57, 11 captures by r300); vs top 10 it halves (r91, 6.0) while theirs is 9.0:
    they disrupt us, we do not disrupt them. Top teams are NOT more grouped than us (largest cluster within 5: 2.4-3.3), except IC (4.7).
  - **THE GAP IS THE MIDDLE**: ~46% of a pool map's gem rate is in groups about as far from both spawns (7 maps ~100%); over a game
    they capture 14.4 middle groups (459 gems) vs our 4.6 (149); middle groups pay ~32 gems vs ~19 elsewhere. Our group_score yields
    them: target_threat_adv 1.49 veto (only allies within 8 counted) + full enemy-half penalty one step past the midline.
  - Walking r1-300: ours 171 rounds/body vs theirs 120 (unopposed ours 153); longer chases (fight walks 17.2 vs 11.4 rounds).
  - Rules study (subagent): kill order bug (lowest HP first -> clusters before the elk: +320..960 damage per elk group); k* bodies per
    group = sqrt(cSH/(DW)) (elk 2-3, golem 4-6 at base); gold routing by passives (Vesper +33%, Marcella 2 gold per gem banked); waking
    sleeping heavy camps onto enemies; altar locks; bush wards (top 5 put 52-100% of early wards in bushes, we 8%); Durability health.
  - SDK audit (subagent): unused ability::damage_amount(target), remaining_channel_time, buffs, item_type::info; camp_group timer 0
    (respawn blocked) treated as alive.
- **In-bot ladder A/B** (bots/god/src/strat.h/.cpp; P.ab_variants / ab_force / ab_shift / ab_base): each game plays variant
  strat_hash(W, H, total camps, side, enemy draft mask) % N; `python tools/live/variant_of.py N --since ISO --bits` attributes
  ranked + unranked games (hash verified identical to the bot). Bits: 1 middle control (mc_value 0.6, mid threat 1.0 w/ allies
  within 12, half_grade 0.3), 2 bold (threat_adv 1.1, ml2 leave/flee 0.3, enemy half 6), 4 attackers first.
  Local vs control (80 games): bold 67.5% (gems 800-599, deaths 13.5-16.4), atk-first 51.2% (761-636, 12.2-15.5), middle 46.2%,
  middle+bold 48.8%; pace control 1020.6, atk-first 1019.7, middle 1038.0.

- **ab1 ladder result (185 unranked games vs top 25 + ranked, 17:30-17:45)**: 39-146 (21%); main effects middle control +0.1,
  bold -0.0, attackers-first -1.5 (+-12): threshold tweaks inside GOD do not move results vs top teams (bold was +17.5 locally!).
- Per-map ladder win rate vs top teams (670 games): competitive on shortcut 83%, the_farm 62%, boss_battle / islands / expanse /
  starvation / concentrated_wealth 50%; **0% on gem_fields (0/28), split, hooks, fragment, packs, big_world, stampede, monolith,
  pilgrimage, rushbait**. Our UNOPPOSED banking beats theirs contested on average (r1000: 882 vs 754) but on gem_fields (1223 vs
  their 666), big_world, reverse_spiral, pilgrimage, quadrants our engine is too slow even alone (heavy multi-camp groups).
- **Movement bugs (tools/live/oscillate.mjs, A-B-A rounds per body)**: unopposed 14/game (gem_fields 90, elk_arena 46,
  reverse_spiral 44, corridors 35 with a 64-round run); vs top 10 ours 41 vs theirs 18. Causes found: (1) danger_detour steps
  sideways, the static field pulls back next turn (fix: keep the detour hold); (2) Heart of Ruin loops 20-tile rings: its route
  crosses a 1-wide hole with the dash it holds for fights (fix: no-progress detector -> route without hole crossings); (3) the
  old blob: leader target vetoed by join limits / unstick blacklisting a crowded group mid-kill. SV.osc_fix (bit 64) = (1)+(2)+
  A-B-A-B breaker: gem_fields A-B-A 87 -> 39, pace 1016.6 vs 1022.6, local h2h 51.2%.
- Convoy (team farms as one force, SV.convoy bit 128, convoy_farm/convoy_pick): gem_fields 285 gems by r300 vs spread 150, but whole
  pool pace 1657 (12 maps never finish): long harmless chains (yellow_brick_road 30-cluster groups), contested enemy-side groups,
  idle waits. Needs a hybrid (team only for heavy damaging groups). Parked.
- Round 2 local (vs control, 80 games): chase discipline 48.8% (more deaths), Durability-first build 43.8% (pace 1035.8), gold
  routing 43.8% (pace 1038.5): not promising.
- Engagements (tools/live/focus.mjs): even fights are even (deaths 0.55 vs 0.45, same focus fire); when they are stronger we die
  0.75 per engagement, when we are stronger they die 0.53; deaths ~13% of body-time + ~1,050 gold a game to them.
- Opponent profiles (20 games each): IC 0/20 (g200 27-109), :3 2/20 (our deaths 18.9/game, 2v1s), procless/Tartarus/Trzy crush the
  opening, prism best girl even gold but bag swings (we steal 484, lose 392 gems/game), Univardisty pulls away after r400.

- **Draft on REAL data (tools/draftmodel/fit_ladder.py; 1,210 ranked games with a top-10 team since Oct 21 12:00, 790 top-vs-top;
  lists in experiments/live/lists/ladder100/, ratings top100.tsv, map FEAT lines experiments/live/feat_lines.txt)**: neither the
  engine-stat draft model (5-fold leave-maps-out log loss 0.662) nor one coefficient per champion (0.650-0.656) beats side + rating
  alone (0.647). Among top teams the draft carries no detectable signal; champion effects ~+-0.1 logit (C&I +0.11, Tavi +0.09,
  Willow / Ren -0.10). Our picks = theirs. Do not chase the draft; the gap is play.
- **Stuck (tools/live/stuck.mjs on 50 v10-vs-top-10 replays, rounds per body per game)**: A-B-A 41 (them 18), loops (8 moving
  rounds, net displacement <= 2) 55 (them 17), idle 70 (them 86). 2/3 of A-B-A and loops have an enemy within 8: melee bodies dance
  around ranged kiters (Vendetta vs Vesper/Tavi at 2-7 tiles, 1162 -> 199 hp) and flee/return cycles (ml2 exit then re-engage next
  round: ml2_hold 0; group_score's threat check is a different model). SV.osc_fix now also: ml2_hold 4 and group_score skips groups
  within 8 of where we walked away from enemies for 15 rounds (WHY 15).

- **ab2 ladder (top-10 only, set D, 200 games + ranked): 31-169 (15.5%)**; stuck fix v1 +0.0, grouped -5.1, danger alerts -4.8 (+-10):
  grouped / danger dropped. Strike-first (A6) lost locally (45%), flee hold lost locally (47.5%): off.
- **Capture deadlock (the user's "stuck in most matches")**: tools/live/stuck_box.mjs / stuckwhere: our long stand-stills are ON camp
  tiles (2,668 body-rounds in 50 games vs theirs 1,165); yellow_brick_road: our Vesper stood 1,549 rounds on a 30-cluster gold row (600
  gold) in T_CAPTURE while an enemy stood on the far end (contested, unseen) -> both sides deadlocked. Fix in SV.osc_fix: capture
  timeout (15 rounds on a reward without it landing -> blacklist 40 rounds, step off). Local trace: our 30+-round stand-stills gone.
- **spawn_threat_off (bit 2048)**: group_score's threat veto ignored enemies standing on their own spawn: gem_fields unopposed 1150 -> 939
  (top teams contested 666); with osc_fix pace 1007.0 (control 1022.6), local h2h 51-52%, gems +91-108, deaths -3.
- **Squads (SV.convoy + SV.squad: bits 128 + 4096 pairs / 8192 trios)**: convoy restricted to index squads; followers do not follow a
  harmless target (spread for clusters); other squads' targets skipped. Testing (q6: pace + h2h vs _sv2112).
- **ab3 ladder (set D top-10, 200 games): 33-167 (16.5%)**; stuck fix v2 +2.3, spawn_threat_off -4.7 (+-10.4): flat.
- **Local games are deterministic** (same code -> identical results); per-map outcomes are chaotic, so judge on 80 games (40 maps x 2).
  Traced (non --release) runs differ from release: use traces for logic only, never for outcomes.
- **bb4 ablations (80 games vs _sv2112, release)**: bb4 37/80; without call register 32, without formation v2 27, without territory 35,
  without ward keep 35 -> every piece helps. Formation v1 (ranged stand still) and the responder-only call register lost on 16-game
  fight sets; v2 (hold only when the target is within range+2, else step behind the frontliner) and calls that ADD a named far
  responder on top of the old everyone-within-rally_r answer replaced them. Territory complete-linkage clustering cost ~7 extra
  fuel-outs a game (O(G^3)): replaced by k-centre (farthest point first, O(G x regions), radius max(9, (W+H)/8)).
- **bb4 fuel**: chain value over big regions was O(|R|^2) a turn: 00lanes (90x30, 84 camps) ran every body out of fuel every
  round (2,500 fuel-outs a game). Now 6 precomputed nearest neighbours per group, filled a few groups a turn with spare fuel
  (Territory::nb_step): fuel-outs 2.9 a game (opponent 2.2). With that fixed: bb4 38/80 (archetype draft), 39/80 (learned draft)
  vs _sv2112: parity, the draft no longer matters locally (the earlier -5 was the lanes bug).
- **Hooks death spiral (01hooks side A, release, deterministic)**: whichever side loses the first fights never gets gold for items
  (r650: theirs 2000-2700 max hp vs ours 1300-1600), they farm next to our spawn, we feed 38-45 deaths. Flips on tiny code
  differences (_sv64 beats _sv2112 1012-0 there; bb4 with every module off loses 0-1012): a general snowball, not a bb4 bug.
- **Opening gap (bb4D replays vs top 10; tools/live/opening_econ.mjs, opening_caps.mjs, first_moves.mjs)**: captures r100 2-3,
  r200 4.5-7.1 (deaths still 1-1), r300 7-11, r600 14-26; captured gold r300 ~570-940. Per capture identical (camp mix, distance
  16, kill ~25 rounds, 2.0 vs 2.3 hitters). Team first capture r81 vs r59; per body first camp hit r26.5 vs r22.9 at the SAME
  distance (16.1 vs 15.8 tiles; an earlier "26 vs 18" was an aggregation bug: None counted as 200). Early leads decide: first
  kill by them -> we win 2%, by us 16%; ahead in max hp at r200 -> 23%, behind -> 3%.
  SV.open (bit 65536: pre-init walk to the nearest camp + near-first cost) and SV.mid_risk (bit 131072) barely move the local
  opening (vs _sv2112, 80 x 300 rounds: first hit 30.1 -> 27.3, first cap 138.7 -> 132.6, caps@200 4.0 -> 4.1): not the fix.
- **WHY WE FARM LESS: we walk off camps whenever an enemy is near (tools/live/timebudget.mjs, bb4D, rounds < 300)**: body-time
  farm 15.7% vs 22.5%, walk 60.8% vs 53.9% (walk with an enemy within 8: 22.8% vs 16.7%), dead 9.6 vs 6.6. Camp efforts started
  12.9 vs 17.8 a game (abandon.mjs: captured 51% vs 61%). With an enemy within 8 (30% of our alive rounds, 28% theirs): we hit a camp
  2% / walk 80% / hit a champion 8%; they hit a camp 14% / walk 60% / champion 10%; we were locally stronger (hp within 8) in 67%.
  NE_TRACE (local, 3,890 turns): combat() decided 91% of them, 53% "fight" (mostly chasing out of reach), 38% flee; of the bodies
  that were farming when the enemy came, 19% kept their group (18% when locally stronger).
  -> SV.farm_thru (bit 262144): working a camp, no chase of an enemy that is out of our reach and cannot reach us next turn
  (kills, channels, enemies on an ally and in-reach rules unchanged).
  Local: fires on 58 of 2,224 near-enemy turns (kept-camp 19% -> 35%); 80 games vs _sv2112 (bb4 play on): 35/80 vs 33/80, deaths
  13.1 vs 15.7, gems 682 vs 655. The rest of the walking: in-reach flee (adv < fight_back_margin), hits on enemies in our reach,
  rally answers.
  Flee sources (NE_TRACE dbg_eng 60-63, old-play base): 59% in-reach flee (adv < fight_back_margin 0.873; we had more hp within
  8 in 33%), 30% outmatched early exit (outmatch_flee_adv 0.8; 45%), isolated exit 2%, ml2 flee 1%. Both thresholds are ES-tuned on
  mirror games (both sides flee alike there). SV.stand (bit 524288: fight_back 0.7, outmatch 0.6) on top of farm-through: local
  44/80 vs 49/80 (off). Same gap at r<150 with EQUAL max hp (near enemy: we farm 3% / walk 81%, they 16% / 60%): our caution, not
  their strength. SV.farm_hold (bit 1048576): a body working a camp above bb_hold_hp 0.6 skips the in-reach flee and the early
  exit until an enemy is within its basic reach.
- **Oct 23 analysis round (data)**: 219 top-10-vs-top-10 replays C:/battlecode/cache/rp_top (lists experiments/live/lists/top10_oct23/),
  our games vs top 10 rp_bb4D (200) + rp_ft52D; compact summaries being fetched. Four analysis agents write
  experiments/live/an_fights.md, an_powers.md, an_resources.md, an_strategy.md. tools/live/ladder_round.py LABEL N SINCE runs one
  A/B round end to end; tools/live/par.py runs a node analysis script over replays in parallel.
- **RL trainer (Oct 23, for the user's Linux i7-12th-gen machine)**: tools/rl/train_rl.py (stdlib only) + knowledge.json (87 genes
  in 7 blocks with ladder priors, map weights = sqrt(ladder freq) x (0.5 + top-10 loss rate), reward, 10-bot league) +
  run_rl.sh / stop_rl.sh; package `python tools/rl/make_pack.py` -> rl_pack_<date>.zip (0.6 MB). Block-subspace ES with antithetic
  candidates, successive halving on paired deterministic cases vs the incumbent, fresh-case validation (t >= 1.28), hall of fame,
  final championship. Smoke-tested here end to end; control flow tested with a fake simulator. The user runs it on Linux and
  brings back rl_results_<run>.tar.gz: apply best_params.json "params_h_overrides" to bots/bb4/src/params.h (ab_base carries the
  switch bits), then ladder-A/B before trusting it.
- **Strategy analysis (experiments/live/an_strategy.md, 611 replays)**: the MIDDLE decides games: middle gems per game us 168 vs
  them 601 (top-vs-top winner 657 vs loser 246); our middle share < 0.2 -> 0% wins, >= 0.6 -> 81%. Top winners hold positions
  next to respawning middle groups (~75 still rounds a game, we 12, we loop 103), take golems 2.1/game at r287 (us 0.42 at r666,
  1.6 bodies per attempt, 20% succeed), monoliths 0.99 vs 0.29; altar locks 2.1 vs 0.3. Stuck cases: islands dead-camp tile
  (ft52D/01islands_cda33abb r670-826), boss_battle altar holder with a 2,926 bag (bb4D/01boss_battle_6e52de7d r1014-1144),
  elk_arena all five idle at spawn (bb4D/01elk_arena_36f90f77).
- **Fights analysis (experiments/live/an_fights.md)**: deaths/team-game us 10.9 vs them 6.5 (top-vs-top 8.5). They strike first in
  44.6% of fresh contacts, we 22.8% (top-vs-top 35/35); first-3-round damage share decides 75% of fights. Excess deaths: walking into
  them without a hit (+1.4/game), even fights lost, fleeing inside reach (+0.6-0.9), contested camp kills (+0.3-0.4). Ranged: we never
  walk + reset + shoot (top Vespers 13% of hitting rounds); our Vesper dies 2.5/game, 74% without a shot in the last 8 rounds.
- **Powers analysis (an_powers.md)**: every power cast 30-65% less than top teams; melee reset used 40-54% of ready hitting turns vs
  70-92% (swing once and step away: 4.6-6.2 lost hits per melee body a game); HoR shield before contact 19% vs 47%; plain dash
  overused near enemies (45-59% of ready turns vs 9-17%).
- **Resources analysis (an_resources.md)**: the gold gap is income (66% capture count); we spend 97% of gold; Treasure opener on every
  body (prism best girl never buys it); banking 12.9 vs 26.2 a game, 66% after a recall home, 16 tiles / 20 rounds after the capture
  vs 10-11 / 11-14. Proposals: build_style 17, bank_first + lower tribute_min + tribute_near 8, Marcella banker, route gold.
- **New switches from the analyses (Oct 23; strat bits; trainer genes)**: stepin_shot 2097152, no_stepin 4194304 (edge_hold), convert
  8388608 (no chase of a retreating target; post-kill farming), smart_flee 16777216 (+ bb_sf_adv gate), melee_combo 33554432 (swing())
  , early_shield 67108864. Local gates (80 games vs _sv2112, base 45/80): all four of the first set 16/80; stepin_shot 44, no_stepin 36,
  convert 38, smart_flee 19 (deaths 23.8) and gated (bb_sf_adv 0.6) 27 (deaths 19.1), melee_combo 41, early_shield 45. Smart flee is
  the disaster (hits back in reach when outmatched): trainer prior 0.1, bb_sf_adv 0.6-1.3. Trainer priors: stepin/combo/shield 0.5,
  no_stepin/convert 0.35. RL pack v2 = rl_pack_20261023_v2.zip (102 genes) for the user's Linux run.
- **User (Oct 23 ~10:00): "still losing badly to the top 20 and others": build new bots; RL results come back ~13:30.** New eval set
  experiments/live/setE_top20.json (top 20, 2 groups x 5 maps each, sides balanced).
- **Stuck on islands = pockets (fixed, P.pocket_guard 1, always on)**: dash kits (HoR, Vendetta, Vesper) dash over 1-wide holes into
  pockets (dist_home BIG); the osc_fix no-progress / stall_guard then turned hole crossings off (dash_off_until) = no way out: local
  games had a HoR standing 1,079 rounds. Now crossings stay on in a pocket and pocket_idle (12) idle rounds end in pocket_dash or a
  recall. Islands re-run: won 1022-259 and 1002-975, no stand >= 40 rounds. STUCK_TRACE build define + tools/live/longstand.mjs.
  Boss_battle: bodies hold the monolith-gated altar tile with 1,500-2,900-gem bags (tribute = bag/10 turns, interrupted) - open.
- **More switches (Oct 23)**: safe_rally 134217728 (rally answers path around reach until close), mid_hold 268435456 (golem team plan
  + max_wait 35), bank_more 536870912 (tribute_min 32, tribute_near 8, bank before recall), kite 1073741824 (ranged shoot then
  dash_away(); dash kits escape with the dash). int ab bits are now all used up to 1<<30.
- **v53E per opponent**: 0-10 vs IFish, prism best girl, :3, procless, Zarzorki, hello; 1-9 Pantheon, EMPEROR Tung; 2-8 print dont int,
  NEETCoders, Noobot, dromedaries; 3-7 FurFortnite; 4-6 Sponge, Let's LARP, subscribe to caterpillow; policy wonk 2-3.
- **Match study (v53E replays; tools/live/narrate.mjs replay OURTEAM: 100-round timeline + every death)**:
  * captures by zone per game (capzones.mjs, deduplicated in grp_idle.mjs): our half us 13.0 / them on their half 24.0; middle us 4.7
    them 15.3. Farming cycle per own-half group (grp_cycles.mjs): respawn->first hit med 42 / mean 100 (them 30/76, top-vs-top 25/62);
    first hit->dead med 19 / mean 52 (them 15/30, top 14/23); capture 6-7; respawn 60 for all.
  * walk rounds per body (walks.mjs, r<1000): us 520 (to farm 274, to FIGHTS 137, recall 43, died 16), them 311 (198/50/25/1), top-vs-top
    419 (261/74/26/3): our extra walking is chasing fights.
  * contest map: 0-1000 every time (they kill the lone monolith 5x200, we never); IFish/procless recall low bodies mid-fight and we do
    not punish (recall is cancelled by damage): their HoR at 140 hp recalled 5-7 tiles from our bodies at r36.
  * RECALL SPAM: Pantheon and :3 start ~3,300 recalls a game (cancel -> act -> recall every turn; on idle turns no cancel = free trip
    home to shop). Our bot saw them "channeling" every turn (target bonus, fight bar 0.9, opportunity calls) -> SV.real_channel
    (bit 2^32): recalling counts only from the 2nd sighting on the same tile. P.persona_recall_spam (local persona) does not farm yet.
  * procless collision 44-1040 with 6 deaths: we farmed 1-15% of rounds, walked 40-73%, hit non-camp tiles 20-30% -> SV.no_chase
    (bit 2^33: no walking toward an enemy out of our reach unless killable / real channel / bag 30+ / on an ally).
- **Local mirror wins do not transfer**: bb4 play (local +), farm-through (local +4/80) were flat or negative on the ladder; the
  mirror opponent reacts like us. Judge on the ladder (in-bot A/B); local runs only gate regressions.
- **Ladder A/B plumbing for bb4**: P.ab_nomask 1 (variant = hash(map, side) only, so the draft and the game agree; verified by
  trace and by tools/live/variant_of.py --nomask); bit 16384 = archetype draft (SV.bb_draft), bit 32768 = every bb4 play module off
  (SV.bb_off; BB(name) macro in strat.h) = the god baseline inside the same submission. Set D balance: 36/44/64/56 games.

## 8. Submissions log
| UTC | version | what changed | ladder evidence |
|---|---|---|---|
| Oct 21 16:44 | GOD v10 | session 14 ship | ~50% ranked at rank ~30; top-10 groups 12-38 |
| Oct 22 12:58 | GOD v11 (platform bot version 38, commit f0c0c9c) | build_style 15 (Treasure-first, kit-derived damage stat), golem_team, init fuel cuts (camp stats per kind, neighbour masks, altar-block bit test) | local vs v10 45.0% / 48.8%; **ladder top-10 groups 11-39** (v10 12-38; paired: gold +17%, gems +9%, deaths +1, flips +3/-4) |
| Oct 22 15:07 | GOD v12 (bot version 40, commit ff8514f; v39 = same minus the hop fuel guard) | v11 + resumable map init (World::init_static_step, pre_init_move to the centre, init_turn_floor), golem_team 0, hysteresis 1.3, fuel guards on the crystal/island re-scoring (hop_score_start/floor: fuel-outs 9.1 -> 2.0 per game); blob / squad code in (blob_until 0, squad_size 0) | local vs v11 61.2%; **ladder top-10 groups 10-40** (paired vs v11: gems 472 vs 464, deaths 10.5 vs 11.2, flips +4/-5: flat) |
| Oct 22 15:23 | experiment (bot version 41) = v12 + blob_until 2000, blob_gather 0 | whole-team blob | **1-44: blob is dead** |
| Oct 22 15:35 | GOD v13 (version 42, ccd7aba) | v12 + power_gate 1.15 / power_flee 1.3 | A **5-45** (paired vs v12: flips +0/-5, gems 431 vs 472, deaths same): caution hurts; **set B 19-31** (first B baseline) |
| Oct 22 15:56 | GOD v14a (version 43) | v12 + pd_ladder 2 (ladder-fitted pick prior: Prism instead of Ryth) | A **8-42**, B 13-37; **ranked 2-13** (disaster) |
| Oct 22 16:23 | GOD v14f (version 44) | v12 + gold_early 2.5 (gold x2.5 at r0 fading to x1 at r400) | A **8-42**, B partial; ranked 1-4 |
| Oct 22 16:41 | **v12 restored** (version 45, `bots/_v12` = git ff8514f) | rollback: every experiment lost rating | ranked by window: v10 146-149, v11 23-22, v12 13-12 |
| Oct 22 17:24 | **ab1** (version 46, `bots/_ab1` = god + ab_variants 8) | 2x2x2 in-bot A/B: middle control x bold x attackers-first | queued sets A+B+C (45 groups) from 17:30; analyse with variant_of.py 8 --since 2026-10-22T17:29 --bits |
| Oct 22 18:59 | **ab2** (version 47, `bots/_ab2`: ab_variants 8, ab_b0 64 / b1 256 / b2 512) | 2x2x2: stuck fix (osc_fix: detour hold, A-B-A breaker, no-progress, ml2_hold 4, post-flee target skip) x grouped stance x danger alerts | set D top-10 only (40 groups `experiments/live/setD_top10.json`, label ab2D) from 19:04; variant_of.py 8 --since 2026-10-22T19:03 --bits; local: stuck fix 50.0% gems 741-652 deaths 12.6-16.0 |
| Oct 22 19:22 | **ab3** (version 48, `bots/_ab3`: ab_variants 4, b0 64 stuck fix v2, b1 2048 spawn-threat-off) | 2x2 | set D top-10 **33-167 (16.5%)**: b0 +2.3, b1 -4.7 (+-10.4) |
| Oct 22 20:45 | bb4 (version 49) | BUG: P.bb_draft 1 made every variant draft by archetype | replaced after 1 min by v50 |
| Oct 22 20:46 | **bb4** (version 50, `bots/_b4s` = bots/bb4 + ab_variants 4, ab_nomask 1, b0 16384 archetype draft, b1 32768 bb4 play OFF, ab_base 64 stuck fix, bb_draft 0) | 2x2: v0 bb4 learned, v1 bb4 archetype, v2 god learned, v3 god archetype | local vs _sv2112 **45/80 (56.2%)**, gems 745-666; **set D (bb4D) 22-178 (11.0%)**: v0 6-30 (16.7%), v1 3-41, v2 9-55 (14.1%), v3 4-52; **archetype draft -8.0 (+-8.6), bb4 play +0.4 (+-8.9)** |
| Oct 22 21:38 | **bb4 v51** (version 51: ab_variants 2, b0 32768 bb4 play OFF, learned draft, ab_base 64) | archetype draft dropped; bb4 play on/off | **ranked (40 games to 23:00): bb4 play ON 6-13, OFF 15-6 (+39.8 +- 28.5 for OFF)**; with set D: ON 15-84 (15.2%), OFF 28-113 (19.9%): bb4 play modules do not pay on the ladder (local said they did) |
| Oct 22 23:19 | **v52** (version 52, `bots/_b4s`: ab_variants 2, ab_nomask 1, b0 262144 farm-through, ab_base 32832 = stuck fix + bb4 play OFF, learned draft) | old play + stuck fix; A/B farm-through | local vs _sv2112: base 45/80, + farm-through **49/80 (61.2%)**; **set D (ft52D) 23-177 (11.5%)**: farm-through 10.0% vs 13.0% (-3.0 +- 8.8); **round 2 (ft52D2, Oct 23 06:35) 21-154 (12.0%)**: -1.0 +- 9.6; ranked since 06:30 37-43 (46%), farm-through +7.9 +- 21.8. Farm-through ~neutral vs top 10. |
| Oct 23 20:17 | **god2b** (version 58, `bots/god2b`) | god2a + modules bank / deny / fight / mid, in-bot A/B 16 variants (g2ab.h) | sweep G2B (setF_top3) |
| Oct 23 18:45 | **god2a = bots/god2_load** (version 57) | g8h + role-slot draft (Ve/Ho/Vd/Ma/Ry by team size) + health-weighted builds | local vs god2 base 54/80; **G2A 12-228** (S0 13-227; deaths 14.4 -> 12.3, gems flat) |
| Oct 23 15:46 | interim _v12 (version 56) | ranked protection while god2 is built (ranked since 14:58: g8 8-17, v54 before it 19-21) | - |
| Oct 23 14:57 | **g8 = god.zip unchanged** (version 55, `bots/g8` = git 28d7340) | baseline S0 for the god2 task | local vs _b54 26/80, fuel-outs 13.0/game (v54 1.8), 0 faults; **S0 (label S0, setF_top3: 40 maps x 2 sides x 3 teams) 13-227: prism best girl 1-79, IFish 5-75, Claudus Maximus 7-73** (wins: boss_battle 4, yellow_brick_road 2, collision, expanse, lost_world, rows, swirl, stampede, the_farm) |
| Oct 23 10:38 | **v53** (version 53, `bots/_b53`: ab_variants 16, ab_nomask 0 (variant hashes the enemy draft too), base 64 + bb4 modules off, b0 103809024 strike = stepin_shot + melee_combo + early_shield, b1 16 Durability-first build, b2 138412032 approach = no_stepin + safe_rally, b3 268435457 middle = middle_control + mid_hold) | 2^4 factorial | local 42/80 (strike: deaths 11.4 vs 16.7; approach 17/41 vs 25/39). Ladder: set E top 20 (v53E) then set D (v53D); `variant_of.py 16 --since 2026-10-23T10:38 --bits`; **result: set E (top 20, 33 groups) 27-138 (16.4%), set D 4-46 (10 groups, queue stopped 11:25); unranked 215 games by bit: strike +2.7, build17 +3.7, approach +1.3, middle +5.3 (+-9.4); middle also +109 gem margin, deaths 8.9 vs 12.7 -> middle goes to the base** |

## 9. Next steps (current plan)
- **v52 ladder round (label ft52D)**: when the 40 groups finish, `python tools/live/groups.py pull ft52D`, fetch ranked
  (`tools/live/fetch_matches.py --team me --kind ranked`), then `variant_of.py 2 --since 2026-10-22T23:18 --bits --nomask`
  (bit 0 = farm-through). Next levers from the time budget: in-reach flee while farming, rally answers pulling farmers off camps,
  early deaths (9.6% vs 6.6% of body-time before r300). Push to GitHub only when a version beats the previous one on the ladder.
0. Ladder test queue (one at a time, sets A + B, paired vs v12 / v13B): v14a Prism draft (running) -> ml2_leave/flee 0.35
   (less fleeing; the gate result suggests caution is costly) -> build_style 16 (health-heavy) -> gold_value 0.5.
1. Ladder-test v12 with `python tools/live/groups.py rerun v10 v12` (same 10 groups; paired compare: tools/live/paired.py v11 v12).
2. Candidates: golem waves (2-3 bodies, recall-heal-return) instead of the whole-team gather; carry capture (gold-bonus body
   takes rewards: IC Vesper 43% of gold); fight decisions (we die weaker: 0.69 max-HP ratio); gem_fields (71-gem elk groups
   next to both spawns: top teams win at r647, our unopposed 1247); late-game fuel-outs (~7/game, road_of_riches 287!).
