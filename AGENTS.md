# AGENTS.md: handoff context for AI agents (and humans)

Read this first. It records what has been done on this bot, what was measured, what failed, what is
running or unfinished, and what to do next, so a new agent can continue without the original chat.

- Last updated: **2026-10-17 19:45 UTC (session 4)**. Rule from the user: update this file and push at every step. Start with **§000**, then **§00** below. Branch `claude/laughing-curie-3rq6hu` (do not open a PR unless the user asks).
- Competition: Cambridge Battlecode 2026a (CAMBC), 12 Oct to 18 Nov 2026. C++ bot compiled to wasm.
- The submitted bot cannot be changed after submission and keeps nothing between matches. All "learning"
  is either offline (training parameters before submission) or in-match (adapting inside one game).

---

## 000. SESSION 4: CURRENT POSITION (written 2026-10-17 19:20 UTC, updated at every step): read this first, then §00

Branch `claude/laughing-curie-3rq6hu` (no PR unless the user asks). Session 4 started 17:25 UTC in a **new container**
(everything local from session 3 was gone). Everything below is committed and pushed unless marked "local".
Local bots (`bots/_*`) and `/tmp/ev/` are lost when the container restarts: see "How to resume" at the end of this section.

### 1. Current position
- **Shipped build is still `legend_st`** = `submissions/legend.zip` (unchanged this session; row in `submissions/BUILDS.md`).
  Frozen locally as `bots/_ST` (= `legend_st` + 2 inert switches; the baseline of every session-4 A/B).
- **`bots/legend/src` (committed, NOT shipped)** = `_ST` + everything below (= local frozen copy `bots/_rm`):
  opening-fuel fix, `start_round=2`, `capture_reset`, `tribute_elapsed`, `danger_detour`, `team_bank`, `race_mode`.
  The side agent's `camp_in_fight` is **not** in legend yet (in `experiments/wip/x_side.patch`; tested as `bots/_rmx` = legend + it).
  The pace agent's switches are **not** in legend yet (`experiments/wip/x_pace.patch`, cut against `_ST`).
- Ship rule this session (the user: "when a better bot is made, push it first, then continue"): ship only what beats
  `_ST` on the **full panel** (`tools/fullpanel.sh`: 6 opponents x 106 maps = 1,272 games), not on single 112-game cells
  (mirror-family matches are chaotic: one cell has a standard deviation of ~5 points).
- User inputs this session: `docs/LADDER_AUDIT.md` (external audit of 40 ladder games of `_L0`, analysed: see §00 and below);
  request "fight for the gems and win by gems, situationally, not hard-coded" (answered by `team_bank` + `race_mode`, below);
  use Opus subagents only for important work, Sonnet/Haiku otherwise, keep AGENTS.md updated, push often.

### 2. Findings (session 4)
- **`bank_first=0` alone**: held-out pool 49.0 head-to-head vs `_ST` (100 games); official-map pace 578 vs 585 but mixed
  (pilgrimage -122, rushbait-v2 -48; monolith +24, collision +19, ambush +16, elkring +14). Not shipped alone (it is part of the pace patch).
- **Opening fuel (in legend)**: init used up to ~320k fuel against the 200k first turn; 84 lost turns in rounds 1-6 over the
  17 official maps (team A vs idle). **Memory allocation is what costs fuel** in this engine: an unreserved vector doubled a loop
  (altar approach 36k -> 17k with `reserve`), exporting a 100x100 distance field cost ~25k, the dash-hole scan over every tile
  cost 87k on lanes, `find_islands` ~47k on 100x100. Fixed: hole scan over hole tiles only, reserves, altar approach from one
  packed walls export (bit layout verified), `World::contested()` lazy, `find_islands` deferred to `prebuild_fields`
  (`defer_islands`). 84 -> 28 lost turns. Remaining cost is ~2.4k fuel per camp group (allocations), lanes still 1 lost turn per body.
- **Start timing flips mirror games**: bodies staggered (light-init bodies from round 1, heavy ones from round 2): 40.2 vs `_ST`
  (official 35.3, contest 0-1000 both sides; unopposed it plays normally). `start_round=3`: 54.5 (official 52.9);
  `start_round=2` without the new mechanics 44.6 (official 32.4), with them 50.9 (official 50.0). Both are synchronized starts,
  so what matters is who reaches contested points first relative to our own code family: chaotic, says little about real opponents.
- **Gem race (the user's request)**, measured with `tools/analysis/gem_race.py` on 336 games of `_ST` vs `_L0 _es2 _r2 _v6`:
  - our losses are **fight losses that cost gems**, not gold preferred over gems: lost games vs `_r2`: collected 903 vs 1156,
    gems lost at death 145 vs 76, kills 8.6 vs 14, gold 3,872 vs 5,669;
  - 12 of 77 losses ended with banked + carried >= 1000 (gen02 968 + 88 carried, gen19 990 + 48, gen13 982 + 44): close races
    where the last bag landed too late (a 66-gem tribute takes 7 turns), not bodies ignoring the win;
  - hidden allies' bags cannot be read (`sdk_champion_gems` rc 97 when not visible), hence a shared sum.
- **`team_bank` (in legend)**: 6-bit team sum of carried gems in bit 6 of the claim bytes 0-5 (claims use bits 0-5 when the map has
  <= 62 groups; each body adds the change of its own min(10, bag/10), so the sum is exact; verified in a game). `wins_with()` counts
  the others' bags, so every carrier banks when the team's bags win. Neutral: 45.5 vs `_w2d` (56 maps), 51.0 held-out, panel mean 76.1 vs 75.9.
- **`race_mode` (in legend)**: every 25 rounds each body samples both teams' banked totals; the last ~200 rounds give each rate and
  projected finish (ours counts the team's carried bags). Behind by > 40 rounds: gold worth 0.3 of its value (cannot pay back in time);
  and if our fights go well (enemy deaths + 2 >= ours, not outnumbered now) contest their gems: deny bonus +0.5, enemy-half
  penalty x0.5, fight bar -0.15, enemy carriers with 30+ gems posted as opportunities. 54.5 vs `_tb` (56 maps), 47.0 held-out;
  56-map panel mean 75.2 but **official maps 79.4 vs 75.0**. The state flickers between 1 and 2 early (no hysteresis yet).
- `capture_reset`, `tribute_elapsed` (audit P2 bookkeeping) and `danger_detour` (audit P1: `step_field` routes around danger
  with the avoiding search when every improving step is dangerous and we stand outside it): together +6 head-to-head
  (`_w2d` 50.9 vs `_w2` 44.6), `danger_detour` carries it.
- **Agent `side` (Opus, done 19:10 UTC)**, `experiments/wip/x_side_NOTES.md`:
  - eight: in all 6 losses we woke a heavy camp at r16-17 while 4-5 enemies were 6-9 tiles away; `combat()` never counted camp damage.
  - collision side B is geometry, not team letter (on side-swapped maps the top spawn always wins, even `_ST` vs itself):
    a mirror artifact. monolith side A loses either way (team-letter effect). No fix for either.
  - **`camp_in_fight=3`** (a camp whose nearest body is an enemy adds its strength to our DPS): 56.2 vs `_ST` (official 61.8),
    eight 2/8 -> 7/10, held-out 53.0; panel `_L0` 71.4, `_es2` 63.4, `_r2` 75.9, `_v6` 92.0, `_devci` 94.6, but `_c3` 49.1 (`_ST` 56.2).
    `wake_guard` built, off (lost 45.5 head-to-head as an addition). Rejected: `camp_kill`, `tank_alert`, `engage_parity`.
- **Agent `pace` (Sonnet, notes final, may still be finishing)**, `experiments/wip/x_pace_NOTES.md`:
  - official-map pace 585 -> **568**: `bank_first` 0, `obj_min_hp` 4500, `obj_share` 0.7, new `obj_max_groups` 8 (the objective
    plan now fires on ambush: 820 -> 642; pilgrimage 900 -> 777); `obj_min_attackers` kept 2 (1 = contest 1087 -> 905 but 46.0 on
    the monolith-heavy held-out pool, and the user said do not rely on the monolith).
  - ~45% of camp walking is in walks abandoned before arrival (an ally took the target or a rescore): ~11% of body-rounds wasted;
    join rule and hysteresis did not fix it; a shared assignment would, but shared memory is full.
  - its head-to-head table is at the end of its notes; read it before merging.

### 3. In progress (at 19:30 UTC)
| Task | Where | Progress | Left to do |
|---|---|---|---|
| **Full panels** (decide what ships) | `/tmp/ev/e9.sh` (log `/tmp/ev/e9.log`) then `/tmp/ev/e10.sh` (`e10.log`) then `/tmp/ev/e11.sh`; results in `/tmp/ev/fp_<bot>/`, summary `python3 tools/sum.py /tmp/ev/fp_<bot>` | **19:35 UTC**: `_ST` done: `_L0` 72.6, `_es2` 65.6, `_r2` 81.1, `_v6` 91.0, `_c3` 56.6 (mean **73.4**, official 67.6). `_rm` (= legend) done: `_L0` 75.0, `_es2` 64.2, `_r2` 88.7, `_v6` 89.2, `_c3` **44.3** (mean 72.3, official **72.3**), vs `_ST` 53.3 (official 52.9). Better on the official maps and vs `_L0`/`_r2`, but loses to `_c3` (non-transitive: `_ST` beats `_c3`). **19:44 UTC** `_rs3` (`start_round=3`) done: `_L0` 71.2, `_es2` 65.1, `_r2` 81.6, `_v6` 92.9, `_c3` 42.0 (mean 70.6, official 65.8), vs `_ST` 44.3: worse than `start_round=2`, and start timing is not what loses the `_c3` cell. **19:45 UTC** running `_rnr` (`race_mode=0`): first cell in progress (`_L0` 77.8 after 176 of 212 games); then `_rnd` (`danger_detour=0`), then `_rmx` (legend + `camp_in_fight`), `_x_side` (`_ST` + `camp_in_fight`), `_rmxp` (legend + `camp_in_fight` + pace patch). Each bot takes ~25 min (6 cells): all done around 22:00 UTC. ~4 min per cell | read all panels; pick the best combination (all-map mean, official-map mean, no cell much worse than `_ST`); if it beats `_ST`: apply to `bots/legend`, rebuild the zip, BUILDS row, push (**ship first, then continue**) |
| **Merge the pace patch** | `experiments/wip/x_pace.patch` (against `_ST`); stacked build `bots/_rmxp` = legend + `camp_in_fight` + pace patch (`bank_first=0` set by hand: the only conflict) | agent done (19:40): official pace 585 -> 568, head-to-head vs `_ST` 51.8 (official 52.9), panel mean 79.5 vs 77.5; `_rmxp` full panel queued after `e10` (`/tmp/ev/e11.sh`, results `/tmp/ev/fp__rmxp`) | apply onto the winning build (params only + `obj_max_groups` code + `LEGEND_TRACE` `SW` line), full panel it; keep only if not worse; pace check: `python3 tools/bench.py BOT idle --maps 'maps/comp/*.map26a'` |
| ES on the user's machine | the user | not run on any session-4 build | after the next ship, ask the user to re-run `tools/rl/train_local.sh` on the pushed build |

### 4. Tasks left (in order)
1. Finish the full panels above, ship the best build (zip, `submissions/history/`, BUILDS row, README table), push.
2. Merge the pace patch on top (full panel), ship again if it wins.
3. `race_mode` refinements: hysteresis on the race state; close-endgame banking (when both teams near 1000, bank smaller bags
   earlier so the last tribute lands first: the remaining "winning bag" losses are timing); measure race-state frequency per map.
4. Contest (official monolith map): pace 1087 is the slowest official map; `obj_min_attackers=1` gives 905 but loses on the
   monolith pool. The untested gold-rush patch for gem-scarce maps is `experiments/wip/x_rush_wip.patch` (from session 2, see the note below).
5. Walk waste (~11% of body-rounds, pace notes): a shared assignment needs comms space; bit 7 of bytes 2-5 is free when
   `alert_refresh` stays off (4 bits).
6. Audit items still open (`docs/LADDER_AUDIT.md`): Cassi & Issac pair risk (pair status bits), opening income on eight
   (partly fixed by `camp_in_fight`), helper credit in `group_score`, probe on the deploy engine whether a stun cancels a tribute
   (`ENGINE_FACTS.md` says only death; the code assumes stun too).
7. Ask the user for: real ladder replays of the new build (best signal: all our sparring bots are our own code family), and permission to
   build public top-team bots (Tarot Club repo) as sparring opponents (was blocked as untrusted code in session 1).

### 5. Tools added this session
- `tools/sum.py [--maps] DIR...`: all-map and official-map (`maps/comp`) win rates per bench dir, per official map with `--maps`.
- `tools/fullpanel.sh BOT [OUT] [OPPS...]`: 6 opponents x 106 maps (56-map pool + `maps/gold,gold2,obj`), 212 games per opponent.
- `tools/analysis/gem_race.py [--comp] [--lost] [--games] DIR...`: gems collected / banked / lost at death, gold, kills, monster damage, rounds to 250/500/750.
- From the agents: `tools/analysis/side_deaths.mjs` (deaths per map and side), `tools/mapgen/swap_sides.mjs` (side-swapped map copies),
  `tools/analysis/route_stats_p.mjs`, `tools/pace/*` (pace pool, per-map pace diff, body timelines, target-switch causes, captures).
- Fuel probing: build a copy with `debug_block` printf of `bc::fuel_remaining()` at checkpoints, run `cambc run BOT idle --map M --rounds 3 -o DIR`,
  read the team stdout from the replay with `unwrapReplay(raw, 'team-a.stdout')` (`tools/replay/decode.mjs`).

### 6. How to resume (new container)
- `pip install cambc==2.2.5 && cambc init --yes .`; toolchain by hand into `/root/.cache/cambc/` with `curl --cacert /root/.ccr/ca-bundle.crt`
  (wasi-sdk-33 renamed from `wasi-sdk-33.0-x86_64-linux`, cmake-3.31.8-linux-x86_64, ninja 1.12.1 into `ninja-1.12.1-linux-x86_64/`).
- `git fetch --unshallow origin` (the clone is shallow; snapshots need old commits), then `tools/make_sparring.sh`, `tools/snapshot.sh _L0 25bed8d`.
- Frozen builds from zips: `for z in es2 c3 st; do mkdir -p bots/_$z && (cd bots/_$z && python3 -c "import zipfile,sys;zipfile.ZipFile(sys.argv[1]).extractall('.')" ../../submissions/history/legend_${z}_20261017.zip) && cp bots/legend/.gitignore bots/_$z/; done`
  (`_ST` = `_st` plus the 2 inert switches: either works as the baseline). `_rm` = current `bots/legend`.
- Variants: `SRC=bots/X tools/variant.sh NAME key=val ...`; patches: `cd bots/NAME && patch -p1 --no-backup-if-mismatch < ../../experiments/wip/x_*.patch`.
- Gotchas: never `pkill -f`; long runs via `nohup script &`; the remote branch can move (an old session pushed twice): `git pull --rebase` before pushing.

### Note from the session-2 container (19:20 UTC): stopped, nothing running there

Session 2 (the original chat) ran in parallel with sessions 3-4 without knowing about them; it has now stopped its own
agents and evaluations and synced to this branch. Its only addition: **`experiments/wip/x_rush_wip.patch`** (unfinished,
untested), the user's **gold-rush strategy** for gem-scarce maps (user messages 9-10: "do not rely on the monolith,
collect gold as fast as possible, melee on near clusters, ranged clear near then far ones, kill lone enemies we can
surround or catch; kills count for the tiebreak"). It is cut against `_f1` (= `legend_es2` without the ES params) and
already contains the gold agent's `x_gold.patch` (the `tb_*` scarcity detector, which fires only on `contest` and its
ladder copy among the 56 maps). Params `rush_no_mono`, `rush_assign`, `rush_near_r`, `rush_melee_pen`, `rush_far_bonus`,
`rush_gold_value`, `rush_hunt*`. Its agent was stopped before any A/B: if you pick it up, rebase onto current legend and
test on `maps/gold`, `maps/gold2`, `contest` vs legend, `_v6`, `_r2` (`tools/analysis/gold_stats.py` shows how games were decided).

## 00. CURRENT POSITION (written 2026-10-17 17:10 UTC, session 3): read this first

Branch `claude/laughing-curie-3rq6hu` (no PR unless the user asks). Everything below is committed and pushed unless it says
"local". Local bots (`bots/_*`) and `/tmp/ev/` are lost when the container restarts: see "How to resume" at the end.

### 1. Current position
- **Shipped build: `legend_st`** = `submissions/legend.zip` (sha256 8129b632…, copy in `submissions/history/legend_st_20261017.zip`,
  row in `submissions/BUILDS.md`). `bots/legend/src` = that build plus two inert switches added later
  (`cast_route_enemy_d`, `cast_route_from`, both 0 = no effect). Rebuild the zip at the next ship anyway.
- Four builds were shipped this session, each pushed as soon as it beat the previous one:

| # | Build | What was added | Key numbers (56 maps, both sides, 112 games per cell, win %) |
|---|---|---|---|
| 1 | `legend_es2` | `_L1` (maths + route) + `dash_holes`, `finish_camp`, `capture_before_retreat` + the 8 consistent ES params from the user's RL run | vs `_L0` (old ladder build) 67.0, `_r2` 78.6, `_v6` 83.9, `_devci` 80.4, `_hunt2` 93.8 |
| 2 | `legend_sf` | + `support_filter` (an ally counts as fight support only above the retreat line and within 6 of an enemy: the audit's "phantom support") + `win_bank` (a game-winning bag goes straight to the nearest altar) | 56.2 head-to-head vs #1; `_L0` 68.8, `_r2` 80.4, `_v6` 86.6, `_devci` 85.7, `_hunt2` 94.6; deaths -16% |
| 3 | `legend_c3` | + cast before walking (`cast_en_route`, `cast_near_target`; Sonnet agent `cast`) + objective-map plan (`obj_*`; Opus agent `obj`; fires only on stampede-type maps where gems sit in one heavy multi-camp group) | 54.5 head-to-head vs #2, 65.6 on objective maps; `_L0` 60.7, `_r2` 79.5, `_v6` 91.1, `_devci` 90.2, `_hunt2` 99.1 |
| 4 | **`legend_st` (now)** | + stuck-navigation fixes (`experiments/wip/x_stuck_v3.patch`, from the session-2 `stuck` agent, rebased) | 56.2 head-to-head vs #3 (56 maps), 57.0 on 50 held-out maps (gold, gold2, obj), 56.2 on `maps/stuck`; `_L0` 70.5, `_es2` 59.8, `_r2` 74.1, `_v6` 86.6, `_devci` 94.6, `_hunt2` 97.3; 0 faults; 18 lost turns on gen16 |

- Unopposed pace on the 17 official maps (vs `idle`): `_L0` 685 rounds to 1000 gems → `legend_st` **585** (-15%).
  Slow maps: contest 1132, pilgrimage 945 (worse than `_L0`'s 851), ambush 849, stampede 727, rushbait-v2 724.
- Measured and kept **off**: `stay_rule`/`stay_veto`/`flee_recall` (the user's fight rule: fewer deaths but 45.5% head-to-head
  on the current build), `pair_caution` 0.3 (neutral), `alert_refresh` (neutral: 49.1 head-to-head), `squishy_hp_first`
  (health emblem first for Stellar/Varg: 40.2%, rejected), forced Ryth as 4th pick at team size 4 (noise), `farm_monolith=0`
  (45.5 vs `_es2`).
- Tooling done: `es_train.py` now saves `best_params.json` = best *evaluated* vector (+ `best_meta.json`) and
  `latest_params.json` = last update, keeps failed batches; `train_local.sh` trains on `maps/comp` + `maps/ladder` only;
  `tools/rl/space.json` has 33 params (added `support_reach`, `stay_margin`, `stay_support_r`, `pair_caution`,
  `finish_rounds`, `bank_trip_w`; widened `join_min_rounds`, `fight_learn_rate`).
- **The 17 official maps (`maps/comp/`) are the real ladder pool**: report them separately. `/tmp/ev/sum.py DIR...` prints
  all-map and comp-only win rates (local; recreate: it loads each `*_A/B.json` with `tools/bench.py`'s `load_stats`).

### 2. Findings (this session)
- Uploaded ladder audit (`analysis.md`, 40 real games of `_L0`, 5 wins): we collect half the camp gems of top teams
  (21k vs 40k) and die twice as often (645 vs 331). Concrete cases and what was done:
  - stampede lost 0-1080 with a 27-7 kill lead: nobody planned the 360-gem group (no single body can clear it) → `obj_*` plan (merged).
  - interlock 976-1056, Ren recalled a winning 72-gem bag 3 steps from an altar → `win_bank` (merged).
  - phantom support (allies at 11 HP counted as backup) → `support_filter` (merged, the biggest single win).
  - Stellar casts 34.7 vs 59.1 per game → cast before walking (merged; Stellar +11 casts per game).
  - re-posted alerts never refresh → `alert_refresh` (bit 7 of byte 2 toggles; neutral, off).
  - ES saved an unevaluated vector → fixed.
- Per-official-map results of `legend_st` (14 games each vs `legend_c3`, `_r2`, `_v6`, `_devci`, `_L0`, `_es2`, `_hunt2`):
  weakest **eight 7/14**, then monolith 9/14, collision, pilgrimage, elkring, corners, rows, rushbait-v2 10/14.
- **eight is a knife-edge opening map**: with both cast switches on we lost 6/6 vs `_es2`/`_r2`/`_L0`; with both off we won 6/6;
  either alone 2-3/6; casting only from r150 3/6. One early centre fight decides it, so any timing change flips whole games.
  Not treated as a systematic cast flaw (the full panel favours the cast patch).
- Side asymmetry: contest, collision and eight flip with the side we play (e.g. collision side B loses 22-1016 to `_v6`
  while side A wins 1106-66: team B's bodies keep trying to bank at the midline altars and die on the way).
- `bank_first` (from the route patch) **slows** pilgrimage by ~120 rounds and is slightly slower overall
  (29 real maps vs `idle`: 583 rounds with it, 574 without).

### 3. In progress (at 17:10 UTC)
| Task | Who / where | Progress | Left to do |
|---|---|---|---|
| **`bank_first=0` A/B** (variant `bots/_pA` = legend with `bank_first=0`) | `/tmp/ev/e12.sh` (local), log `/tmp/ev/e12.log` | **finished 17:15 UTC**: `_pA` vs legend 50.9 head-to-head; vs `_r2` 83.0 (current legend 74.1), `_v6` 89.3 (88.4), `_devci` 92.9 (96.4), `_L0` 72.3 (70.5): mean of the 4 = 84.4 vs 82.4, i.e. +2 (noise-level except vs `_r2`). Note: current `bots/legend` (with the 2 inert `cast_route_*` switches) scored `_v6` 88.4 / `_devci` 96.4 where the shipped `legend_st` scored 86.6 / 94.6: an unused code change shifts fuel-dependent decisions, so cells move ±2 with no behaviour change | decide: ship `bank_first=0` (pace -9 rounds on 29 real maps, pilgrimage -120, +9 vs `_r2`) or confirm on the held-out maps first (`maps/gold,gold2,obj`, head-to-head vs legend); then rebuild zip, BUILDS row, push |
| **Side asymmetry / opening fights** (contest, collision side B, eight, interlock) | Opus agent `side`, copy `bots/_x_side` from `bots/_C3` (= `legend_c3`, frozen), outputs `/tmp/side/`, deliverables `experiments/wip/x_side.patch` + `x_side_NOTES.md` | started ~16:35; so far it added `tools/mapgen/swap_sides.mjs` (uncommitted, its own); no report yet | read its report; its patch is cut against `_C3`, **rebase onto current legend** (`legend_st`) before testing; merge only if it wins on the official maps and is not worse on the 56-map pool |
| ES on the user's machine | the user | not started on the new build | the user re-runs `tools/rl/train_local.sh` on the pushed build; when the archive comes back, apply `best_params.json` to a copy (`tools/variant.sh`), panel it, bake in only what wins (last time only the 8 params that moved consistently won) |

### 4. Tasks left (in order)
1. Ship `bank_first=0` (see above), then merge `x_side` if it wins.
2. eight / contest / collision side B / pilgrimage pace (if `side` does not fix them). For pilgrimage: why bank trips are slow
   on a 65-tall map with the gems far from spawn (route_stats.mjs / bank_audit.mjs with a `LEGEND_TRACE` build).
3. Pre-match map plan beyond stampede-type maps (decide team knobs at init from map features); danger-weighted paths;
   coordination (narrow version: the measured top failure "help does not come"; `_c1` lost, `support_filter` helped).
4. After each ship: tell the user to re-run ES on the new build (ES must train the final code).
5. Ideas still untried (§7.5): camp parking, altar locks on enemy altars, capture-overlap tribute, Home emblem.
6. Highest-value outside help to ask the user for: (a) the 8 ladder fixture replays named in `analysis.md` §4 (stampede,
   contest, interlock, packs, eight, expanse, swirl) to test against real behaviour; (b) permission to build the public
   top-team bot clones (Tarot Club repo) as sparring opponents: every opponent we have is our own code family.

### How to resume if the processes are gone
- `pip install cambc==2.2.5 && cambc init --yes .`; fetch the toolchain by hand (§3 gotchas: wasi-sdk-33, cmake 3.31.8,
  ninja 1.12.1 into `/root/.cache/cambc/` with `curl --cacert /root/.ccr/ca-bundle.crt`); `tools/make_sparring.sh`;
  `tools/snapshot.sh _L0 25bed8d`.
- `_es2` = `git show <legend_es2 commit>` or legend with `support_filter=0 win_bank=0 cast_en_route=0 cast_near_target=0 obj_plan=0`
  minus the stuck patch (easiest: unzip `submissions/history/legend_es2_20261017.zip` into `bots/_es2/`; same for
  `_sf`, `_C3` = `legend_c3`, `legend_st`). `_L1` = `bots/_es2` with `dash_holes=0 finish_camp=0 capture_before_retreat=0`
  and the 8 ES params at their old values.
- Benches: `python3 tools/bench.py A B --maps 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' --jobs 4 --out DIR --quiet`
  (~50 s per 112 games with 4 free CPUs).

---

## 0. Status right now (read this if nothing else)

| Item | State |
|---|---|
| Bot | `bots/legend/src` (C++). Ready-to-upload bundle: `submissions/legend.zip` (rebuild after every change, section 3) |
| Current legend | **session 2: legend = `_L1` (old legend + maths + route patches, merged 14:00 UTC) + three switchable fixes under test** (`dash_holes`, `finish_camp`, `capture_before_retreat`; frozen as `bots/_f1`). `submissions/legend.zip` is still the old build until the fixes pass the panel |
| Strength (45-map panel, 90 games per cell) | economy + spells on `_r2`: panel mean **85.2%** (vs `_r2` 77.6%), 57.8% head-to-head vs `_r2`. Promoted legend vs `_v6` (18 maps): 26/36, 0 faults, 2.6 lost turns per game. Full numbers in section 5 |
| Engine | **cambc 2.2.5** since session 2 (was 2.2.2). Legend re-measured on it: unchanged (§0b) |
| Tiebreakers (round 2000) | banked gems, then **gold earned**, then kills, then team B (read from the engine binary, §2) |
| In flight | see **§0b**: five subagents (gold/tiebreak economy, stuck navigation, team coordination, maths + route review, ML fight model). RL training now runs on the user's machine with `tools/rl/train_local.sh` |
| Next | Merge the prototypes that win one by one (panel after each), rebuild the zip, update README/STRATEGY tables, commit, push; apply the user's ES results when they arrive (§0b) |

---

## 0a. Session 2, part 2 (from 13:45 UTC): read this first

At ~11:00 UTC the account's session limit stopped all five agents mid-work; the container survived (all `bots/_*`
copies and `/tmp/<agent>/` outputs were still there at 13:45).

**The user's new requests (message 7, 13:45 UTC)**, with the state of each:

| Request | State |
|---|---|
| Analyse the RL results (`rl_results_20261017_1715_ccc8269.tar.gz`, plus the same files sent loose) | **done**, see below |
| Champions kill camps but do not collect them | **cause found, fix under test**: `safety()` runs before the capture, so a body at low HP after a kill walked home and left the reward (dead camps do not hit). `capture_before_retreat`. Measured with `tools/analysis/rewards.mjs`: on `contest`, 6 of 91 rewards waited 46 rounds (= expiry) uncollected |
| Retreating from a camp that is almost dead | **fix under test**: `finish_camp` (stay when the group dies within 4 rounds and we keep 8% HP in the worst case, no enemy within 8) |
| Not dashing over 1-tile holes | **cause found, fix under test**: every route field treated holes as walls, so routes never planned a dash. `dash_holes`: dash kits build fields where 1-wide hole crossings are ground (`World::dash_walls`), and wait up to `dash_wait_max` rounds at the crossing for the dash. Crossings exist on rushbait-v2 (62 tiles), eight (22), expanse (16), ambush (42) |
| Use emblems / gold (only Ren seemed to) | **measured: not a bug in our local games**: on `contest` every legend champion owns 4-6 emblems except Cassi & Issac (1 emblem + shards each: they earned ~270 gold each and died 17 times). If ladder replays show otherwise, the ladder build may be an old zip |
| Use recall better | **measured: already good locally** (`tools/analysis/home_walks.mjs` on `_L1` vs `_r2`/`_v6`: 34 recalls per game vs their 30; walks home from 10+ tiles 0.5 per game, ~4 rounds a recall would save). Added `flee_recall`: fleeing out of reach, recall when no enemy can interrupt it |
| **The user's fight rule (message 8)**: stay and keep hitting only if our health is more than the enemy's max damage and no enemy support is near; otherwise retreat or (better) recall; fleeing dash/ranged chasers can get us killed | **implemented, under test**: `stay_rule` (stay when our own HP > every visible enemy's damage per round x rounds until the target dies + 1, x `stay_margin` 1.1, and no other enemy within `stay_support_r` 10 of the target), `stay_veto` (skip fights that worst damage could kill us in, while escape is possible; when it is not, the existing cornered rule trades), `flee_recall`. `finish_camp` already follows the same rule for camps (worst-case damage, no enemy within 8). Variants `_s1` (all), `_s2` (no veto) vs `_f1` |
| Optimal (danger/reward-weighted) paths | open; partly covered by camp scoring (risk, pain map, threat); route fields are still shortest-walk |
| Stuck, walking the same path again and again | `stuck` agent resumed (its detector: 75 episodes per game; top causes target-flip 505, home-edge 351 (fixed by the merged `home_edge_fix`), walk-away 238, task-flip 248 over 360 games) |
| **Gold-only maps / tiebreak** (`gold` agent, finished 15:10 UTC) | **built, not merged** (`experiments/wip/x_gold.patch`, applies to current legend; `x_gold_NOTES.md`). Scarcity detector is on only for `contest` and its ladder copy among the 56 maps (`monolith` 5.6, `rows` 5.0, `elkring` 3.0 gems/round outside monoliths: legend finishes them at 1000 gems). Scarce pool (`maps/gold` + `maps/gold2` + `contest`, 74 games) vs `_f1`: everything on 35.1%, without the team monolith call 47.3%, + holding big bags on spawn 45.9%, without Treasure-first 47.3%. Vs `_v6` the variant won 93.2% where `_f1` won 89.2%. Why nothing moves: the side that wins early fights snowballs to 1000 gems late (r1100-1990); ~15% of games reach r2000 and ~1% are decided on gold. The team monolith call reaches the monolith from ~r300 but the gathered team gets picked off |
| **Gold-rush strategy on gold-only maps** (message 9): gold as fast as possible, melee on near clusters, ranged clear near then far ones, kill lone enemies we can surround or catch (kills are tiebreak 3); **never rely on the monolith** (message 10) | Sonnet agent `rush` building it on `_x_gold2` (`bots/_x_rush`, deliverables `experiments/wip/x_rush.patch`, `x_rush_NOTES.md`); tested on `maps/gold` + `maps/gold2` + `contest` vs `_f1`, `_v6`, `_r2`. Separately, `farm_monolith` switch added to legend (default 1); `_nomono` (= `_f1`, monolith never farmed) queued on the 56 maps and the monolith maps |
| **ES subset `_es2`** (= `_f1` + the 8 consistent ES params) | **wins**: vs `_f1` 58.0, `_r2` 78.6, `_v6` 83.9, `_devci` 80.4 (mean of three 81.0 vs `_f1` 75.0, `_L1` 80.6), fewer deaths (1,376 vs 1,800 against `_r2`). To be baked into legend |
| Coordination `_c1` (coord agent's `coord_joint` + `coord_flee_ally` on `_L1`) | **loses**: vs `_L1` 40.2, `_r2` 65.2, `_v6` 76.8, `_devci` 74.1. Dropped |
| Dash routing on hole maps (`_f1` vs `_L1` on rushbait-v2, eight, expanse, ambush, the 30x80 ladder map, `maps/stuck`, `isl_*`) | 65.6% (21-11) |
| `_f1` (the three fixes) on the 56 maps | vs `_L1` 57.1, `_r2` 59.8 (`_L1` 72.3), `_v6` 77.7 (`_L1` 86.6), `_devci` 87.5 (`_L1` 83.0): wins head-to-head but loses ground vs `_r2`/`_v6`; ablations `_ab_dash`, `_ab_fin`, `_ab_cap` (each = `_f1` minus one fix) queued vs `_r2`, `_v6` |
| Coordination between champions | coord agent's best variant (`coord_joint` + `coord_flee_ally`) rebased onto legend as `bots/_c1`, under test. Its measurements are in §0b |
| A strategy decided before the match from the map | open (next after the panel results) |
| Keep this file updated | ongoing |
| Use Opus subagents as little as possible | only `gold` and `stuck` were resumed (they held hours of context); coord and ML stay stopped; the rest is done by the main session |

**RL results from the user's machine** (Windows/MSYS, 20 CPUs, commit ccc8269 = old legend `_L0` code, 16 generations x
864 games, 76-map pool incl. `maps/gold/`, opponents `_v6,_hunt,_hunt2,_devci,_r2,_self`):
- Training worked: mean-policy reward +0.66 (gen 0) → +0.79 (gen 15), noisy (+0.44 to +1.03; each generation samples 8 maps).
- **Validation played 0 games** on Windows: `bench.py` ran without `--release` and hid the error. Fixed: `bench.py --release`,
  an error message when a batch produces no statistics, and `train_local.sh` validates with `--release`.
- The archive brought the **17-map official pool** (`cambc maps pull`): now in `maps/comp/` (11 new maps; the 6 we had
  are updated versions). **Panel pool from now on: 56 maps = 27 generated + 12 ladder + 17 official, 112 games per
  opponent.** Real gem-scarce maps: `contest` (1 monolith + 10 gold clusters per side), `elkring` (elks + gold only),
  `monolith`, `rows` (monolith is the big gem source).
- `best_params.json` applied to the merged legend (`_es1`): **43% head-to-head vs `_L1`** (it was tuned for the old code).
- Consistency of each parameter's drift (share of generation steps in the final direction, move in % of its range):
  8 moved consistently: `deny_bonus` 0.60 → 0.04 (100%, −47%), `cap_recall_hp` 0.73 → 0.61 (100%), `q0_push` −0.27 → −0.72
  (100%), `fight_learn_rate` 0.16 → 0.24 (100%), `cornered_margin` 0.48 → 0.63 (93%), `isolated_fight_adv` 1.65 → 1.43
  (93%), `target_threat_adv` 1.06 → 1.31 (93%), `fight_back_margin` 0.77 → 0.87 (87%). The rest drifted like noise
  (`gold_value`, `fight_margin`, `tribute_min`, `early_tribute_min`, `shop_shards`, `steal_hp_frac`, `deficit_defend`).
  Variant `_es2` = `_f1` + only those 8, under test.

**Merged at 14:00 UTC: maths + route** (`mr` agent's panels, 45-map pool, 90 games each):

| Bot | vs `_L0` | `_r2` | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | mean of last five | pace vs `idle` |
|---|---|---|---|---|---|---|---|---|---|
| `_L0` (old legend) | — | 60.0 | 73.3 | 91.1 | 95.6 | 76.7 | 88.9 | 85.1 | 467 |
| `_x_math` (+ score cap) | 53.3 | 67.8 | 81.1 | 87.8 | 92.2 | 77.8 | 96.7 | 87.1 | 455 |
| `_x_route` | 53.3 | 56.7 | 76.7 | 95.6 | 93.3 | 76.7 | 91.1 | 86.7 | 442 |
| **`_x_mr` (both) = `_L1`, merged** | **62.2** | 72.2 | 84.4 | 93.3 | 95.6 | 80.0 | 94.4 | **89.5** | **428** |

Lost turns on gen16_98x99 unchanged (12, `tools/analysis/rollovers.mjs`). On the new 56-map pool `_L1`: vs `_L0` 56.2,
`_r2` 72.3, `_v6` 86.6, `_hunt` 93.8, `_hunt2` 94.6 (rest running).

**Running now**: `scratchpad/eval1.sh` / `eval2.sh` (panels of `_L1`, `_es1`, `_L0` on the 56 maps, then `_f1`, `_c1`, `_es2`,
and `_f1` vs `_L1` on the hole maps); agents `gold` and `stuck` (resumed, working on copies of the new legend).
If they are gone: rebuild from `experiments/wip/x_*.patch` (§0b recovery steps; base = current legend).

## 0b. Work in progress (session 2, from 2026-10-17 09:45 UTC)

Everything below is **unfinished or unmerged** unless marked done. Patches in `experiments/wip/` are snapshots of local
bot copies (the copies are git-ignored); they may still change in the agent's copy.

**Session 2 started in a new container**: everything local from session 1 was gone (its ES run, all `bots/_*` copies,
`tune_out/`). Session 1's ES run had finished generations 0 and 1 only (mean-policy reward +0.831 and +0.864); nothing was
saved. Recreated in session 2:
- `pip install cambc` gave **2.2.5** (was 2.2.2); `cambc init` moved `cambc.toml` to 2.2.5. The wasm toolchain had to be
  fetched by hand again (TLS, §3 gotchas): wasi-sdk-33 into `/root/.cache/cambc/wasi-sdk-33`, cmake 3.31.8, ninja 1.12.1.
- `tools/make_sparring.sh` rebuilt the panel. **`bots/_L0`** = frozen copy of legend at 25bed8d: baseline of every A/B in
  session 2.
- Legend re-measured on engine 2.2.5 (45 maps, 90 games per cell): results match session 1, so the engine change does
  not affect us.

| Bot | `_r2` | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | Mean of the last five |
|---|---|---|---|---|---|---|---|
| legend (= `_L0`) on engine 2.2.5 | 60.0 | 73.3 | 91.1 | 95.6 | 76.7 | 88.9 | **85.1** |

**User requests in session 2** (also in §1, item 6):
- continue the work in the md files, using Opus subagents for major tasks, Sonnet for medium, Haiku for documentation;
- RL training moves to the user's machine: give an exact script; the user sends back the weights and every output;
- maps with only gold and gems only in very hard camps: the bot must understand them and favour gold, as the
  tiebreakers say;
- our champions lack coordination: a proper team strategy;
- champions sometimes get stuck between walls, which loses games;
- keep this file updated at every step, in the same style.

**Agents in flight** (rules every parallel agent follows: `experiments/wip/AGENT_RULES.md`):

| Agent (model) | Task | Bot copies | Deliverables |
|---|---|---|---|
| `mr` (Opus) | review, fix and panel the maths and route prototypes from session 1; combine the winners | `_x_math`, `_x_route`, `_x_mr` | refreshed `x_math.patch`, `x_route.patch`; `x_mr.patch`, `x_mr_NOTES.md` |
| `gold` (Opus) | gem-scarce maps: test maps, scarcity detection, tiebreak-aware economy (gold earned, gem lead, monolith, endgame) | `_x_gold` | `x_gold.patch`, `x_gold_NOTES.md`, `maps/gold/`, map generator |
| `stuck` (Opus) | champions stuck between walls: detector over replays, stress maps, root causes, nav fix | `_x_stuck` | `x_stuck.patch`, `x_stuck_NOTES.md`, `tools/analysis/stuck.mjs`, `maps/stuck/` |
| `coord` (Opus) | team coordination: measure the failures first (deaths alone, allies not joining, split damage), then fix the costly ones (focus fire, engage protocol, buddies, sectors) | `_x_coord` | `x_coord.patch`, `x_coord_NOTES.md`, `tools/analysis/coord_audit.mjs` |
| `ml` (Sonnet) | ML fight model: logging build, data, formula vs logistic / tree / boosted trees / MLP; export only if it clearly wins | `_x_ml`, `_x_ml_log` | `x_ml_NOTES.md` (+ `x_ml.patch` only if it wins) |
| `docs` (Haiku) | **done**: `docs/LEARNING.md` §1 "Training on your own machine", README "Train the bot yourself". Its review of the script found 3 issues, fixed: PATH on macOS / with `--skip-setup`, the printed map count included `zz_test`, `apply_params.py` could only write into legend (now `--bot NAME`) | none | docs |

**Session 2 log: what has been done, in order** (all committed and pushed unless marked local):

| Time (UTC) | Step | Result |
|---|---|---|
| 09:45 | New container: `pip install cambc` (2.2.5), `cambc init`, toolchain by hand, `make_sparring.sh` | builds work; `cambc.toml` → 2.2.5 |
| 09:50 | Legend panel on engine 2.2.5 (540 games) | unchanged: mean 85.1 (table above) |
| 09:50 | Tiebreak rules read from the engine binary (`strings /usr/local/bin/cambc`) | gems → gold earned → kills → team B (§2) |
| 09:55 | `tools/rl/train_local.sh` written and tested end to end (1 generation, 6 games, validation, archive) | works; commit 0809d36 |
| 09:55 | Portability and parallel-safety fixes: `variant.sh` / `es_train.py` without GNU `sed -i`; `bench.py` rebuilds only stale bots; `panel.sh` `PANEL_JOBS`; ES space 29 → 27 params | verified: the new `variant.sh` builds `_hunt` byte-identical to the old one |
| 10:00 | `bots/_L0` frozen; `experiments/wip/AGENT_RULES.md`; six subagents launched | see the table above |
| 10:25 | Docs agent done; its script review found 3 issues, fixed (PATH on macOS / `--skip-setup`, map count, `apply_params.py --bot`) | commit after 0809d36 |
| 10:20-10:45 | Agents' work-in-progress committed as it appeared: `tools/analysis/gold_stats.py`, `coord_audit.mjs`, `coord_trace.mjs`, `stuck.mjs`; `tools/mapgen/goldmaps.mjs`, `stuck_maps.mjs`; 14 maps in `maps/gold/` (+24 hold-out in `maps/gold2/`), 8 in `maps/stuck/`; every agent's `x_*_NOTES.md` | in the repo |
| 10:45 | Snapshots of the agents' bot copies: `experiments/wip/x_gold.patch`, `x_stuck.patch`, `x_coord.patch`, `x_mr.patch` (= legend + math + route as built by `mr`, before its review fixes) | unfinished code: the agents overwrite these with their final versions |

**Early findings from the agents** (10:45 UTC; details and updates in each `experiments/wip/x_*_NOTES.md`):
- **Coordination (`coord`)**, measured on 360 games of `_L0` vs `_r2`, `_v6`, `_devci` and itself:
  - Vision is **not** shared across the team (56% of alive-ally turns had an ally hidden); bushes hide allies too.
  - The costliest failure is **help that does not come**: 39% of our champion deaths had an ally within 10 tiles that
    did not hit anyone in the 3 rounds before (155 gem-equivalent per game; 244 in lost games). Most of those allies
    (57%) were within 6 tiles and healthy; they saw the fight, counted no ally near themselves, and declined or fled.
  - Next: lone deaths while fleeing (29% of deaths had no ally within 6; 54 of 59 deaths with no ally within 10 were
    fleeing). Locally outnumbered fights lose (net −0.17 kills per fight; −0.77 in lost games).
  - Not problems: focus fire (81% of multi-hitter rounds on one target, same as the opponents), abandonment (6%),
    walking out of spawn alone.
  - Cause: each body judges a fight only with allies within 6 of itself.
- **Gold / tiebreak (`gold`)**:
  - `earnedGold` = every gold gain (captures and 50 per kill, both with Treasure/Vesper +20%); spending does not lower it.
  - Camp rewards (gems / gold / respawn rounds): gem cluster 24 / 0 / 50, gold cluster 0 / 35 / 50, wolf 22 / 90 / 40,
    elk 36 / 160 / 60, monolith 200 / 300 / 150; fused monolith groups pay more (monolith + gem cluster 448 / 600).
  - One real map is gem-scarce already: ladder `lad_50x50_R_c5_65bb75` (monoliths are its only gems).
  - Legend on the 14 gold maps: 85.7% mean vs `_r2`/`_v6`/`_hunt2`/`_devci`; games still mostly end at 1000 gems late
    (r1100-1990) because the side that wins early fights snowballs and farms the monoliths; the first monolith
    capture comes late (r780-1200, a body must solo-plan it first); one loss 600-600 on gold earned.
- **Stuck (`stuck`)**: detector built (frozen / jiggle / oscillation / no-progress episodes, blocked moves, rollovers,
  9x9 views of the worst episodes) and 8 stress maps; root causes being traced.
- **Maths + route (`mr`)**: both prototypes rebuilt on the current legend (route merged by hand as planned) and combined
  into `_x_mr`; review and panels running.
- **ML (`ml`)**: logging build verified identical to legend (same results on 90-game panels, byte-identical statistics);
  data collection running.

**Merge plan** (coordinator): `mr` first, then `stuck`, `gold`, `coord`, `ml`. Each on top of the previous merge, a
45-map panel after each, kept only if it wins (§7.1 rule), then a `submissions/BUILDS.md` row and a new zip.

**Offline RL now runs on the user's machine** (session 2): `tools/rl/train_local.sh` does everything in one command
(prerequisites, SDK, `cambc maps pull`, sparring panel + `_self` = frozen copy of the bot being trained, build and smoke
test, ES training, validation panel of the learned parameters, results archive). Tested here end to end with a tiny run.
- The user sends back `rl_results_<date>_<commit>.tar.gz` (git-ignored): `meta.txt` (commit, cambc version, CPUs, args),
  `console.txt`, `log.txt`, `history.json`, `best_params.json`, `validation.txt` (learned parameters vs every opponent,
  every map, both sides) and any official maps the repo does not have yet (`cambc maps pull` on their machine works;
  it is blocked here).
- When it arrives: extract it into a scratch directory, read `validation.txt` and `meta.txt` (which commit it trained),
  apply `best_params.json` to a copy (`tools/variant.sh _es_user $(python3 -c "import json;print(' '.join(f'{k}={v}' for k,v in json.load(open('best_params.json')).items()))")`),
  panel it against the current legend, and bake it in only if it wins. Add new official maps to `maps/comp/`.
- Changes for it: `tools/variant.sh` and `es_train.py`'s variant builder no longer use GNU `sed -i` (macOS); the search
  space (`tools/rl/space.json`) dropped `ucb_c` and `prior_pull` (27 params): both are measured harmful and sit at their
  lower bound, where ES noise can only push them up.
- Other tooling changes: `tools/bench.py` rebuilds a bot only when its sources are newer than its wasm (parallel agents
  share the sparring bots); `tools/panel.sh` takes `PANEL_JOBS`.

**If you are a new agent and these runs are gone** (new machine or container restart: running processes,
`bots/_*` and `tune_out/` are local only), continue like this:

1. Set up: `pip install cambc && cambc init .` (choose C++); if the toolchain download fails TLS, fetch it by hand (above).
   Then `tools/make_sparring.sh` and freeze the baseline: `mkdir -p bots/_L0 && cp -r bots/legend/src bots/_L0/ && cp bots/legend/.gitignore bots/_L0/`.
2. Rebuild each prototype from its patch on top of the current legend:
   `for p in x_math x_route x_gold x_stuck x_coord; do mkdir -p bots/_$p && cp -r bots/legend/src bots/_$p/ && cp bots/legend/.gitignore bots/_$p/ && (cd bots/_$p && patch -p1 --no-backup-if-mismatch < ../../experiments/wip/$p.patch) && cambc build _$p; done`
   (session 2 patches are cut against legend at 25bed8d; read each `x_*_NOTES.md` for its state).
3. Panel each prototype (90 games per opponent):
   `tools/panel.sh _x_math 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' _L0 _r2 _v6 _hunt _hunt2 _devci _base`.
   Compare with the engine-2.2.5 legend row above (mean 85.1).
4. Merge winners onto `bots/legend` one at a time (merge plan above), panel after each.
5. For each new build: rebuild the zip (`rm -f submissions/legend.zip && cambc bundle legend --output submissions/legend.zip`),
   check that it holds only `src/*.cpp|*.h` (no `.orig` files), archive it in `submissions/history/`, add a row to
   `submissions/BUILDS.md`, update §0 and §5 here, commit and push.

### Findings from session 1's prototypes (still valid; the `mr` agent is reviewing and panelling them)

**Decision maths: findings and changes** (`_x_math`; tools `xm_audit.mjs`, `xm_paired.mjs`, `xm_fe_time.mjs`, `xm_fe_taken.mjs`, `xm_fr_split.mjs`, `xm_econ.mjs`)
- The bot does decide with explicit formulas; checked against 120 traced games:
  - camp score = value / time = long-run gem rate;
  - DPS model accurate solo (actual/predicted 0.85-1.12);
  - `combat()` advantage already behaves like Lanchester's square law;
  - tribute thresholds, recall safety and capture-recall timing hold up (512 of 518 capture-recalls got the reward).
- Measurably wrong:
  - **damage taken over a kill** was over-predicted 1.7-2.3x: it was assumed constant, but camps die one by one, and allies at the group tank;
  - **travel** was 2.2-2.5 rounds too long for ranged and dash champions;
  - the heal-trip HP budget did not match `safety()`'s retreat line;
  - **gold had no end-of-game discount**: 20% of gold is earned after a team passes 800 gems, and ~485 gold per team is never spent.
- Fixes, all switchable:
  - travel to attack range, with a dash pace;
  - sequential kill integral, with exposure 0.25 for a lone ranged champion and allies counted as tanks;
  - reserve aligned with `safety()`;
  - gold value scaled down over the last 500 rounds.
- Prediction errors on the same episodes: travel 3.08 → 1.74 rounds, damage 281 → 167 HP, episode time 10.5 → 6.8 rounds.
- Smoke tests (24 ladder games each): vs `_v6` 18-6 (`_r2` 17-7), vs `_r2` 15-9, vs `_hunt2` 23-1 (same as `_r2`). 13-28% fewer deaths.
- Weak spot: fight-free farming races are 3-7% slower; it lost 3 of 4 of them to `_r2`.
- The fight estimator over-states advantage x1.6-2.0, growing with body count, but the fights it picks are net positive in every bin. It was left unchanged, as was the double-counted spell DPS in `combat()` (it affects both sides; fixing it rescales every threshold).

**Routes: findings and changes** (`_x_route`; tools `route_stats.mjs`, `route_audit.mjs`, `bank_audit.mjs`, `bank_first.mjs`)
- **Optimal path, answered with data:**
  - camp ordering (two-step lookahead / TSP) would save only 0.2-0.7% of walking: 83% of captures end in a recall-while-capturing, so trips are star-shaped (spawn → camp → teleport home);
  - camp supply is not the bottleneck: ~440 gem-value of untouched live groups on our half;
  - target swaps between bodies are limited by the 8-byte shared memory.
- **Real waste:**
  - banking walks: 14.6% of body-rounds unopposed, 32% on the 30x80 map;
  - farm↔home flip-flops at the spawn edge: 15.3% of turns → 1.1%;
  - walks abandoned before arrival: ~37% of camp-walk steps.
- **Changes:**
  - `home_edge_fix` (home trips also from 1-2 steps away);
  - `claim_helpers` (a yielding ally's damage still counts in the kill plan);
  - **bank first** (when a capture fills the bag and the nearest altar plus a recall home beats banking from spawn, bank there, then recall);
  - a trip-aware bank threshold (+1 gem per step beyond 12, capped at 2x);
  - "bank before a risky fight" ignores enemies standing on their own spawn.
- **Results:**
  - unopposed pace 622 → 523 rounds to 1000 (−16%);
  - bank walking −30-35%, gems per bank 40 → 44;
  - head-to-head vs `_r2` 25-11 (69%);
  - vs `_v6` side A only, 13/18: not yet confirmed neutral.
- Rejected:
  - claim seniority: fewer target swaps, but slower pace;
  - lookahead ordering, as above;
  - camp scoring that includes the bank cost: not built.

**ML fight model** (`_x_ml`): session 1 built the pipeline (`tools/ml/`) but not the model; the `ml` agent continues it in
session 2. The plan:
- log the `combat()` features and the decision taken;
- label the outcome from replays (death within 12 rounds, kill within 12 rounds);
- compare the current formula, logistic regression, a decision tree, gradient-boosted trees (XGBoost if pip allows, else sklearn) and a tiny MLP, by AUC with a game-level split;
- export to C++ (< 3k fuel per call) only if the model clearly beats the formula, then A/B it.

The maths audit above already found the formula is biased but its chosen fights are net positive, so a learned model has to beat a reasonable baseline.

**All analysis tools** (`tools/analysis/`, `tools/ml/`):

| Tool | Measures |
|---|---|
| `item_value.py` | item value per champion (log utility over farming, kills, survival, heal trips), greedy build order |
| `spell_usage.mjs` (+ `spell_decode.mjs`) | per champion and ability slot: ready turns, casts, wasted cooldowns, stun timing, resets, shields, wards and locks |
| `xm_audit.mjs`, `xm_paired.mjs`, `xm_fe_time.mjs`, `xm_fe_taken.mjs`, `xm_fr_split.mjs` | predicted vs actual (kill time, damage, trips, fight advantage) from `XM_TRACE` builds |
| `xm_econ.mjs` | bags lost at death, bag-size histograms, recall reliability |
| `route_stats.mjs`, `route_audit.mjs` | time shares, walking per gem, oscillation, duplicate walks, ordering regret, coverage (`LEGEND_TRACE` builds) |
| `bank_audit.mjs`, `bank_first.mjs` | banking time split; capture-recall versus bank-first |
| `gold_stats.py` (session 2) | per bench directory: how each game was decided (gems, gold earned, kills, team B), banked gems, earned gold, kills, deaths |
| `coord_audit.mjs` (session 2) | coordination failures from replays, both sides: deaths alone / help did not come / outnumbered / abandoned, focus fire, fights by local numbers, walk-outs (`--split` won vs lost games) |
| `coord_trace.mjs` (session 2) | joins the audit's death categories with `COORD_TRACE` decision lines: why an idle ally did not help |
| `stuck.mjs` (session 2) | stuck episodes (frozen, jiggle, oscillation, no progress), blocked moves, rollovers, 9x9 views of the worst episodes |
| `tools/mapgen/goldmaps.mjs`, `stuck_maps.mjs` (session 2) | gem-scarce test maps (`maps/gold/`), navigation stress maps (`maps/stuck/`) |
| `tools/ml/benchsum.py` | summary of bench.py output directories |
| `tools/ml/run_games.py` | runs a chosen list of single-side games (one at a time), bench.py naming |
| `tools/ml/parse_logs.mjs` | turns `XML_LOG` fight logs (one line per `combat()` evaluation) into a labelled CSV: did this body die / did an enemy within 6 die in the next 12 rounds |
| `tools/ml/train.py` | compares fight-outcome predictors (the formula vs learned models) with game-level cross-validation |
| `tools/ml/explore.py` | off-policy (contextual-bandit) analysis of `XML_EXPLORE` data: the logging bot multiplies its fight advantage by exp(u), u ~ U(-0.7, 0.7), to measure what bolder or more careful fighting would earn: epsilon-style exploration done offline, not in submitted games |

---

## 1. What the user asked for (all requests in this chat)

1. Learn the repo and keep looking for improvements. "We are winning, but when losing we lose by a little,
   rarely by a big margin." Problems the user named:
   - we do not use **recall** and lose too much time walking;
   - the **draft** does not pick strategic champions: analyse each map, then pick for it;
   - in fights there is **no backup**: everyone goes out, we all die and are locked out for a long time.
2. Make the learning better: **reinforcement learning** with a **reward/punishment** system that learns
   from mistakes, keeping in mind that the submitted bot cannot be updated.
3. Use the strategy plan (`CAMBC_2026a_Strategy_Plan_1.md`, uploaded by the user, not in the repo), other
   people's views, and the uploaded match results (4 zip match groups, 24 ladder losses). Analyse our moves
   and the enemies' moves, find out why we lost, and fix it. Search the internet for better strategies.
4. (Second message) **Use gold**: shards, emblems, "upgrade abilities". **Check the maths** in decisions.
   Use **decision trees, XGBoost, RL soft updates, epsilon-greedy, content-based filtering**, deep learning
   or RL concepts **only if they make the bot better**. Choose **optimal paths**, and work out **when to
   optimally use powers** and items.
5. (Third message) Write this context file and push it, top priority.
6. (Session 2, Oct 17) Continue the work in the md files with subagents: **Opus** for major tasks, **Sonnet** for medium
   ones, **Haiku** for documentation. **RL training moves to the user's machine**: give an exact script; the user returns
   the weights and all outputs. Some maps have **only gold, with gems only in very hard camps**: the bot must recognise
   them and favour gold, as the **tiebreakers** say (the attachment did not arrive; the rules were read from the engine,
   §2). Our champions **lack coordination**: build a proper team strategy. Champions sometimes **get stuck between
   walls**, which loses games. Keep this file updated at every step, in the same style.

---

## 2. Game and engine essentials (full evidence in `docs/ENGINE_FACTS.md`)

- First team to 1000 banked gems wins (round limit 2000). **Tiebreakers at round 2000** (strings in the engine binary
  `/usr/local/bin/cambc`, cambc 2.2.5): more banked gems; tied on gems → more **gold earned** (match statistics
  `earnedGold`); tied on gems and gold → more kills; tied on all three → team B wins. Lexicographic: one banked gem
  beats any amount of gold. Kill gold is 50, assists and passive income are 0.
- Champions farm camp groups (wolf, elk, gem and
  gold clusters, monolith), capture rewards (gems + gold), carry gems and **tribute** (bank) them at an
  altar. A tribute takes max(1, ceil(gems/10)) turns; damage does not cancel it, a stun or death does.
- **Recall**: 5 turn ends; *any* damage cancels it. Health is restored only after a turn ends on spawn.
  Recall while capturing: step on the reward tile in round T, start the recall at T+1 or later, and the
  reward lands with the teleport.
- **Respawn** takes 60 rounds. Cassi & Issac are one pick but two bodies, and they die together.
- **Turn order**: camps act first; team A leads odd rounds, team B even rounds. Within a team, higher
  `set_priority` acts first (it applies from the next round).
- **Fuel**: 100k per turn (200k on a champion's first turn, 1M on the first draft turn). A turn that runs out
  **continues in the next round, so that champion loses a whole round** (counted as "Turn rollover" in
  replays). Host calls (distance-field get, `bitboard::is_set`) cost ~50-60 fuel each; a full distance
  field costs 13-19k. **Bitboard exports are bit-packed** (LSB first); distance-field exports are uint16 per tile.
- **Shared memory**: 8 bytes for the whole team (bytes 0-5 hold claims plus 2 stance bits, bytes 6-7 one
  team alert). Draft memory is 1024 bytes.
- **Items**:
  - Every shard costs 30 gold and adds 1 point of its stat (growth per point: health +100, or +71/+75/+95
    for some champions; strength +5 (+4); focus +10 (Cassi +15)). Five shards of one family combine
    automatically into an emblem.
  - Emblem bonuses: Monster +10% camp damage, Jungle −30% camp damage taken, Durability −10% damage taken,
    Treasure +20% gold, Home faster recall. These passives do not stack within a family.
  - Power emblem = 6 points of one stat. Bruiser emblem = 5 points + 1 of each other stat.
  - Shopping only on spawn or while dead (Tavi anywhere). Consumables: teleport crystal (hops up to
    Chebyshev 3 over walls and holes), altar lock, ward.
  - **No item upgrades abilities directly**: focus is the ability stat (spell = modifier × focus, Ren's
    retaliation = 0.2 × focus per hit, Varg's shield = 2.5 × focus). Cooldowns are fixed at 8 rounds.
- Matches are **deterministic** for fixed bots and map: never repeat a game; variance comes only from
  more maps and opponents.

---

## 3. Repo map and how to run things

```bash
pip install cambc && cambc init .              # SDK into sdk/ (git-ignored); choose C++
tools/make_sparring.sh                         # recreate the git-ignored sparring panel (bots/_*), verified identical
cambc build legend
python3 tools/bench.py legend _v6 --maps 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a'   # 90 games, ~40 s on 4 CPUs
tools/panel.sh legend 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' _v6 _hunt _hunt2 _devci _base
rm -f submissions/legend.zip && cambc bundle legend --output submissions/legend.zip                # submission bundle
```

| Path | What |
|---|---|
| `bots/legend/src/` | the bot: `brain.*` decisions, `world.*` perception/memory, `nav.*` distance fields and stepping, `comms.*` shared memory, `learn.*` in-match learners, `draft.cpp` composition choice, `params.h` every tunable |
| `bots/_*` | **git-ignored** local bots: sparring opponents, prototypes, variants. Recreate the panel with `tools/make_sparring.sh` |
| `experiments/patches/` | the finished prototypes as patches against `_r2` (apply on legend: `cd bots/X && patch -p1 --no-backup-if-mismatch < ../../experiments/patches/x_econ.patch`) |
| `maps/*.map26a` | 27 generated maps. `maps/ladder/`: 12 real ladder maps rebuilt from replays. `maps/comp/`: 6 official maps (SDK 2.1.6 pool, from the public Tarot Club repo; the other 3 official maps duplicate ladder ones) |
| `maps/gold/`, `maps/gold2/`, `maps/stuck/` | session 2 test maps: 14 gem-scarce maps (`maps/gold2/`: the same 12 gold layouts with seeds 11 and 23, 24 maps, a hold-out set) (gems only from monoliths/elks, gold everywhere; 2 controls) and 8 navigation stress maps. **Not in the 45-map panel** (panel them separately) |
| `tools/bench.py`, `tools/panel.sh` | A-vs-B on every map, both sides, in parallel; one summary line per opponent |
| `tools/variant.sh`, `tools/snapshot.sh` | build a param/define variant (`SRC=bots/X tools/variant.sh NAME key=val --define "M v"`); freeze a past commit as a bot |
| `tools/replay/decode.mjs` | replay decoder using the engine's own wasm: per-round state + events (`{rollovers: true}` keeps fuel rollovers); `report.py`, `extract_map.mjs`, `mapinfo.mjs`, `mapfeatures.mjs` |
| `tools/rl/es_train.py` | offline RL: evolution strategies over `tools/rl/space.json` (27 params since session 2), shaped reward, uses bots/legend's params.h as the start |
| `tools/rl/train_local.sh` | one-command ES training for the user's own machine: setup, training, validation panel, results archive (§0b) |
| `tools/draft_tournament.py`, `tools/draft_model.py` | composition round robin (per-map wins and gem margins); nearest-map draft model with leave-one-map-out validation (`--vs` scores against a chosen field) |
| `tools/analysis/` | item-value model (`item_value.py`), spell usage (`spell_usage.mjs`), decision-formula audit (`xm_audit.mjs`), bag/recall risk (`xm_econ.mjs`), route time use (`route_stats.mjs`) |
| `docs/` | `STRATEGY.md`, `ENGINE_FACTS.md`, `HLD.md` (architecture), `LEARNING.md` (RL), `FEEDBACK_LOOP.md` (ladder replay loop) |

**Sparring panel** (all from `tools/make_sparring.sh`):
- `_base`: old v5, what was on the ladder.
- `_v6`: commit 58c2fe4.
- `_r2`: commit 4a3920d.
- `_hunt`, `_hunt2`, `_devci`: aggressive archetypes on the 58c2fe4 code, using the drafts of the top ladder teams.
- Also available: `starter-cpp`, and `idle` (never moves; used to measure unopposed pace).
- `_r1` (review fixes without the fuel fixes) was a local intermediate and cannot be recreated exactly.

**Gotchas that cost us time:**
- **Never use `pkill -f` / `pgrep -f` / `killall` with patterns**: they matched and killed the agent's own shell
  several times. To wait for a background job, wait on that script's own PID
  (`ps -eo pid,args | grep "[s]cratch/x.sh" | grep -v "bash -c"`). The shell that launched it lingers, so
  pattern-waiting deadlocked once.
- Launch long jobs from a script file with `nohup script > log 2>&1 &`; container restarts kill them
  (the ES run died this way).
- **Noise**: one 90-game result has a standard deviation of about ±5 points, so judge changes on the
  average over 5-6 opponents, and treat gaps under ~4 points as noise. Identical code differing only in fuel
  use can move a result by ~3 points.
- `cambc` toolchain download fails TLS in **every new cloud container** (sessions 1 and 2): fetch wasi-sdk-33 (extract
  `wasi-sdk-33.0-x86_64-linux` and rename it to `wasi-sdk-33`), cmake-3.31.8-linux-x86_64 and ninja-1.12.1 (`ninja-linux.zip`
  into `ninja-1.12.1-linux-x86_64/`) by hand into `/root/.cache/cambc/` with `curl --cacert /root/.ccr/ca-bundle.crt`.
- The platform API (`2026a.battlecode.co.uk`) is blocked from the cloud container; the user must download
  ladder replays and match JSON themselves.
- Building and running other teams' bot code (the Tarot Club clones of the top teams) was blocked by the
  permission classifier as untrusted code; only their map files were used. The user can allow it if wanted.
- With 4 CPUs a Workflow runs only 2 agents at a time, and the account's session limit has cut workflows
  twice. Keep workflows small, and save findings to files as you go.

---

## 4. What has been implemented (chronological, with evidence)

**Commit 58c2fe4: first rewrite, built from 24 decoded ladder losses** (we had lost 17 of 20 scrims).
- **Farming of big packs.**
  - The camp score now counts Varg's splash, area spells, Ren's retaliation, allies, up to 5 heal trips,
    and lets a second body join heavy packs.
  - The 3-wolf-pack ladder map went from losing 132-1012 to the starter bot to winning.
- **Recall loop.**
  - Recall while capturing (the reward lands with the teleport), after banking far away, to shop, and to
    bank at the altar next to spawn.
  - Never recall when an enemy seen in the last 2 rounds is within 7 tiles; cancel when a threat closes in.
  - Unopposed pace improved from 574 to 500 rounds.
- **Fights (`combat()`).**
  - Advantage = (our HP / their DPS) / (their HP / our DPS), counting allies' spells.
  - Escape feasibility: fight back against chasers we cannot outrun; stun the chaser; melee champions
    swing after their step.
  - Never trade with enemies healing on their spawn.
  - Backup counting; early retreat when isolated; a higher fight bar with half the team dead.
  - Respawn escort: when down 2+ bodies, wait on spawn for the next ally instead of walking out alone.
- **Turn order:** dynamic `set_priority` (fighters act first).
- **Draft:**
  - Ren, Stellar, Cassi & Issac, Ryth, Varg ("meta"), chosen from a 780-game composition tournament;
  - the same draft the strongest ladder team uses.
- **Builds.**
  - Durability/Jungle health, then Monster, Treasure, Power.
  - Won 65% head-to-head against the old builds.
- **Crystal shortcuts** over hole mazes, and island camps.
- **Learning** (`docs/LEARNING.md`):
  - offline: ES trainer;
  - in-match: team stance bandit (SPREAD / GROUPED / PUSH), pain map of where we died, per-champion
    fight calibration.

**Commit 4a3920d: lost turns, review fixes, learner rework.**
- **Fuel.**
  - On the 98x99, 48-group map the team lost **566 of ~2,700 champion turns** to fuel rollovers; now **12**
    (just the two heavy opening turns per body).
  - Causes fixed:
    - emblem checks that recounted the build for every group, every turn;
    - all groups scored every turn: the loop now scores the current and nearby groups first, under a
      fuel floor;
    - the hop scan read bit-packed exports as bytes and checked fuel only per row: it now reads bits,
      resumes per tile, stops after a pause, and is skipped when no hop can pay;
    - splash clusters recomputed every turn: now only when a camp dies or respawns;
    - the pain map decayed every turn: now lazily, every 8 rounds.
- **Review fixes:**
  - the respawn escort now waits: allies that died while this body was dead get their real death round;
  - a dead group's reward is captured before any home or shop trip;
  - when the altar is unsafe, banking via recall and the spawn altar is tried before giving up;
  - a cancelled tribute is not restarted in the same turn;
  - a nearer claimer captures a reward even when a lower-index ally also claims it;
  - DANGER alerts no longer overwrite RALLY or OPPORTUNITY;
  - champions hold on spawn instead of bouncing on and off it;
  - the spawn-heal bonus counts only for fights on spawn;
  - capture-recall starts in the right round;
  - failed hops are dropped.
- **Ablation (leave-one-out, 78 games × 4 opponents):** priority alternation (double turns) and the
  "shielded camp" retreat rule each cost 7-17 points and are off by default. Rest-on-spawn is worth up to 17
  points; it stays, with sticky tributes and the claim tie-break.
- **Stance learner:**
  - rewards in gem units: kill +25, death −45, banks smoothed over two windows;
  - soft (EMA) update;
  - UCB exploration and a pull back to priors (both now off, see below);
  - death locations only from fresh sightings.
- **Draft model hook:**
  - `draft.cpp` reads an optional `draft_table.h` produced by `tools/draft_model.py`;
  - without it (the current state) the draft is unchanged.

**Commit aece821: draft values** from an 8-draft × 45-map tournament (2,520 games, section 5). At team size 4,
Varg as the 4th pick now beats Ryth.

**Commit 564785f: stance exploration off** (measured −2 points; section 5).

**Analysis tools** (commits 5cf8001 to e751b1b): `tools/analysis/*` (see section 3).

**Session 2 (Oct 17, commits from 0809d36): tooling, no bot change yet.**
- `tools/rl/train_local.sh`: one-command ES training on the user's machine (§0b).
- Portable variant builders, stale-only rebuilds in `bench.py`, `PANEL_JOBS`, `apply_params.py --bot`.
- New analysis tools and test maps from the session-2 agents (§0b log): `gold_stats.py`, `coord_audit.mjs`,
  `coord_trace.mjs`, `stuck.mjs`, `goldmaps.mjs`, `stuck_maps.mjs`, `maps/gold/`, `maps/stuck/`.

---

## 5. Measured results (latest first)

All on the 45-map pool (27 generated + 12 ladder + 6 official), both sides: 90 games per cell, win rate %.

**Round 3 (stance-learner A/B on `_r2`):**

| Bot | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | `_r1` | Mean |
|---|---|---|---|---|---|---|---|
| `_r2` (learner, UCB 0.3) | 74.4 | 88.9 | 94.4 | 63.3 | 87.8 | 56.7 | 77.6 |
| learner off | 78.9 | 82.2 | 93.3 | 66.7 | 93.3 | 62.2 | 79.4 |
| learner, no exploration (**now default**) | 77.8 | 90.0 | 96.7 | 66.7 | 86.7 | 62.2 | **80.0** |

**Round 2 (review fixes and retreat threshold):**

| Bot | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | Mean |
|---|---|---|---|---|---|---|
| `_m1` (before the review fixes) | 48.9 | 87.8 | 72.2 | 45.6 | 83.3 | 67.6 |
| `_c1` (`_m1` + the 2 harmful toggles off) | 54.4 | 83.3 | 85.6 | 50.0 | 82.2 | 71.1 |
| `_r1` (+ review fixes) | 60.0 | 86.7 | 90.0 | 64.4 | 83.3 | 76.9 |
| `_r1` + `retreat_hp` 0.40 | 64.4 | 82.2 | 88.9 | 67.8 | 83.3 | 77.3 |
| `_r1` + `retreat_hp` 0.50 | 67.8 | 85.6 | 84.4 | 65.6 | 84.4 | 77.6 (noise; left to ES, range up to 0.55) |
| `_r1` without the claim tie-break | 65.6 | 87.8 | 86.7 | 60.0 | 81.1 | 76.2 (noise; kept) |

**Draft tournament** (8 drafts, same code, mean win rate vs the field):

| Draft | Mean | Worst |
|---|---|---|
| `metaV` (Ren, Stellar, C&I, Varg, Ryth) | 0.590 | 0.489 |
| `meta` (Ren, Stellar, C&I, Ryth, Varg) | 0.581 | 0.500 |
| `vci` (Vendetta, C&I, Varg, Stellar, Ren) | 0.565 | 0.500 |
| `civr`, `ryt`, `tav` | 0.49-0.52 | |
| `ven2` (Tarot's Vendetta/C&I/Varg/Tavi/Vesper) | 0.421 | |
| `wil` (Willow-based) | 0.321 | |

- The **nearest-map draft model** (content-based: "maps like this one") beat the team-size choice by +2 to
  +4 points in leave-one-map-out validation against the whole field.
- Against only the strong drafts it gave no gain. With ~6 games per map per draft, per-map differences are
  noise: `meta` and `metaV` are identical at team size 5, yet scored 0.500 vs 0.467.
- So it is **not shipped**; the hook and the tool are ready for when more real maps and replays exist.

**Round 4 (prototypes vs the panel; same learner setting as `_r2`):**

| Bot | vs `_r2` | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | `_r1` | Mean (excluding `_r2`) |
|---|---|---|---|---|---|---|---|---|
| `_r2` (round 3) | — | 74.4 | 88.9 | 94.4 | 63.3 | 87.8 | 56.7 | 77.6 |
| `_x_econ` (economy patch) | **60.0** | 74.4 | 90.0 | 92.2 | 73.3 | 83.3 | 61.1 | **79.1** |
| `_x_spell` (spells patch) | **54.4** | 75.6 | 88.9 | 90.0 | 81.1 | 91.1 | 63.3 | **81.7** |
| `_x_combo` (econ + spells, **now legend**) | **57.8** | 77.8 | 94.4 | 98.9 | 75.6 | 90.0 | 74.4 | **85.2** (vs `_x_econ` 46.7%, vs `_x_spell` 55.6% head-to-head) |

**Earlier (39-map pool, the first rewrite):**
- The old bot (v5) won 88% vs the starter bot, 42% vs `_hunt`, 28% vs `_hunt2` and 14% vs `_devci`.
- The rewrite won 100%, 87%, 82% and 55% respectively.
- Unopposed pace: 574 → 500 rounds.

---

## 6. Analyses and findings (what the data said)

**Why we lost on the ladder** (24 decoded replays; `docs/STRATEGY.md` §1):
- Death cascades: 12.2 deaths per match vs their 4.0. Half came with no ally within 6 tiles; many came
  while fleeing same-speed chasers.
- Big packs went unfarmed.
- They recall as transport (at 58-73% HP, 22-49 times per game); we recalled only in emergencies.
- They act first in fights (`set_priority`).
- Every top team drafts Cassi & Issac.
- Spawns that touch caused a stalemate.
- Our HP builds were too low (they reach 1800-2000 HP).
- One opponent (group 8694af79) is the ladder team "ifish" (draft Ren, Stellar, C&I, Ryth, Varg).

**Web research** (public repos; the best source was Tarot Club, github.com/FHL-08/Tarot-Club-Cambc2026,
cloned read-only to `/home/user/fhl-08/tarot-club-cambc2026` in this container):
- **Top teams' habits:** ~220 casts per game; recall at ~0.46 HP and never under threat; camp parking
  (wait on a cleared camp until it respawns); spend all gold; a grouped opening, then split the map into
  sectors; a disable-chain to focus fire.
- **What failed for Tarot:**
  - pulling allies into a teammate's fight cost 17 to 401 gem margin;
  - forcing the whole team onto one camp won only 3 of 18 games;
  - a full kill-race rewrite won 0 of 18.
- **Deep RL** at Lux-AI scale cannot fit in 100k fuel. Feasible instead: SPSA/ES parameter tuning, and
  tiny MLP gates trained to imitate replays.

**Economy** (`_x_econ` agent; `tools/analysis/item_value.py`):
- Gold is not wasted: 91-97% is spent, and gold held away from spawn is small (12-45 per champion).
- What was wrong:
  - **no Bruiser** emblems (7 stat points vs Power's 6, at the same 150 gold);
  - the rich champions' build lists **ran out** (Ren once had 948 gold unspent);
  - Cassi & Issac are gold-poor (~580 gold per game) yet bought damage first, while dying together
    6 times a game;
  - Treasure came too late.
- The prototype fixes all four, and counts Monster's +10% in the kill-time estimate:
  - its own tests: 21/24 vs `_v6` (`_r2`: 17/24), 20% fewer deaths, +15% gold;
  - full panel so far: 60% head-to-head vs `_r2`;
  - its weak spot is pure farming races, ~20 rounds slower.

**Abilities** (`_x_spell` agent; `tools/analysis/spell_usage.mjs`):
- Spells are ready on 66-84% of turns but used on only 21-40%, mostly because there is no target in range
  or the champion is walking (damage spells cannot be cast in a turn that walks).
- Three fixable losses:
  1. Ryth's area stun was never cast from range: 5.6 stuns per game on champions despite ~36 fight turns
     with it ready.
  2. Fleeing champions never stunned a chaser that would hit them anyway.
  3. Spells on camps were held whenever an enemy was within 9 tiles, but a fight followed within the
     cooldown only 13% of the time at 7-9 tiles (51-63% at 5-6).
- Already fine: attack resets, Varg's shield timing, stun timing relative to the target's turn, wards,
  altar locks, crystals.
- Prototype: 55.6% vs `_r2` over 36 games, 13% fewer deaths, Ryth's champion stuns ×3; full panel pending.

**Maths of decisions** (`docs/STRATEGY.md` §3-4):
- The decisions are explicit models:
  - camp value per round = (gems + 0.22 × gold) / (travel + wait + kill time + 6 capture rounds + heal trips);
  - kill time from real DPS (splash, spells, retaliation);
  - damage taken from the nearest-champion rule and emblems;
  - fight advantage in the Lanchester style (HP over enemy DPS, counting allies and stuns).
- A calibration audit against replays (predicted vs actual kill time, damage, fight outcomes) was being
  built when the session limit hit (`tools/analysis/xm_audit.mjs`); it is being re-run now.

**Learning (RL)**:
- In-match stance learner: neutral (±2 points); exploration hurts (a game has only ~25 decision windows).
- Offline ES: the main learning path. Each generation samples 8 maps, so its "mean reward" moves with the
  map sample; judge it only on a fixed panel after training.

---

## 7. Unimplemented / open work (by priority)

1. **Done: the economy and spells prototypes are merged** into `bots/legend` and `bots/_dev` (panel mean
   85.2% vs 77.6%). Keep the rule for later prototypes: merge a change only if the 5-6-opponent mean improves
   by more than ~3 points, or the gem margin improves clearly with no regression.
2. **Maths, route and ML prototypes**: a Workflow is building them now (`bots/_x_math`, `bots/_x_route`,
   `bots/_x_ml`, local only). The workflow script is
   `.../workflows/scripts/legend-decision-upgrade-*.js` in the session dir; if it is lost, the brief for each
   is below.
   - *Maths*: log each formula's predictions (kill time, damage taken, trips, fight advantage) and compare
     with the replay outcome; refit the coefficients; fix unit errors; consider Lanchester N² for
     multi-body fights.
   - *Route*: measure time shares (walk, farm, capture, wait, bank, home); then two-step lookahead (pick a
     group by its value plus the best follow-up), team assignment of groups to avoid duplicate walks, wait
     on camps that respawn soon, danger-weighted paths. Must stay under the fuel budget.
   - *ML*:
     - log the `combat()` features and the decision taken;
     - label outcomes from replays (death within 12 rounds, kill within 12 rounds);
     - compare the current formula with logistic regression, a decision tree, gradient-boosted trees
       (XGBoost if installable, or sklearn) and a tiny MLP, by AUC with a game-level split;
     - export the winner to C++ (if/else trees or constexpr weights, < 3k fuel per call) only if it
       clearly wins.
3. **ES on the final code** (session 2: the user runs it on their machine with `tools/rl/train_local.sh`, §0b). In a
   container the equivalent is:
   ```bash
   python3 tools/rl/es_train.py --space tools/rl/space.json --opponents _v6,_hunt,_hunt2,_devci,_r2 \
     --maps 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' --gens 10 --pop 4 --maps-per-gen 8 --jobs 4
   ```
   Then apply `best_params.json` to a copy (§0b), validate on the panel, and keep the result only if it wins.
   ES reads its starting values from `bots/legend/src/params.h`.
4. **Ship**: sync `bots/_dev/src` into `bots/legend/src`; rebuild `submissions/legend.zip`; update the
   results tables in `README.md` and `docs/STRATEGY.md`; commit and push.
5. **Ideas not yet tried** (from research and analysis):
   - camp parking (hold a cleared camp until it respawns);
   - a grouped opening then map sectors (note: our earlier "deathball" opening lost);
   - a shared focus-fire target in comms (shared memory is full: it needs a redesign);
   - altar locks on enemy-side altars;
   - capture-overlap tribute (start a 1-tick tribute next to an altar as a capture lands);
   - the Home emblem for recall-heavy play;
   - sending captures to gold-poor champions;
   - imitation gates trained on top-team replays.
6. **Feedback loop with the real ladder**: the user downloads new ladder replays, then decode them, extract
   new maps into `maps/ladder/`, re-run the draft tournament and ES (`docs/FEEDBACK_LOOP.md`). Our sparring
   bots are archetypes of our own code, so real teams will differ.

---

## 8. Setbacks and things that did not work (do not repeat blindly)

| Idea | Result | Where |
|---|---|---|
| Priority alternation for double turns (+/-1000) | −8 to −17 points head-to-head | `prio_alternate = 0` |
| Retreat counting only "unshielded" camps | −10 points (champions stayed out at lower HP) | `safety_v2 = 0` |
| Pair plans (wait for a partner on heavy packs) | 24 rounds slower unopposed, no win-rate gain | `pair_plans = 0` |
| Early deathball opening | lost to spread farming | `deathball_until = 0` |
| First untuned online learners | −10 points until the combat model was fixed | — |
| UCB exploration in the stance bandit | −2 points over 540 games | `ucb_c = 0` |
| Nearest-map draft model | no gain against strong drafts (noise) | no table shipped |
| Treasure-first builds for Ren/Stellar | worse than Treasure second (19/24 vs 21/24) | `rich_treasure_first = 0` in the econ patch |
| Hop scan v1 | read bit-packed exports as bytes and overran fuel (bodies lost 13-14 of their first 40 turns) | fixed in 4a3920d |
| Health emblem first for Stellar/Varg kits (`squishy_hp_first`, session 3) | 40.2% head-to-head vs the ES build, -8 vs `_devci`, -7 vs `_r2`: damage first wins; the HP gap is fixed better by `support_filter` (fewer bad fights) | `squishy_hp_first = 0` |
| The user's fight rule (`stay_rule` + `stay_veto` + `flee_recall`, session 3) | fewer deaths but lower win rate: 49.1% vs `_es2`, 45.5% vs `legend_st`; without `stay_veto` 41.1% | switches kept, off |
| Extra fight margin for Cassi & Issac (`pair_caution` 0.3) / re-posted alert refresh (`alert_refresh`) | neutral (63.4 vs 67.0 vs `_r2`; 49.1% head-to-head) | off |
| Ryth instead of Varg as 4th pick at team size 4 | 53.1% head-to-head on 16 size-4 maps, mixed vs the panel: noise | draft unchanged |
| Process handling | `pkill -f` killed our shell; a pattern-based wait deadlocked; container restarts killed ES at generation 4; session limits cut two workflows | see the gotchas in §3 |

---

## 9. What we are thinking right now (next actions, in order)

Session 2 (10:15 UTC):
1. Wait for the five agents (§0b). Merge in order `mr` → `stuck` → `gold` → `coord` → `ml`, each on the previous
   merge, panel after each (45 maps, 90 games per opponent, plus the gold and stuck test maps), keep only winners.
2. Gem-scarce maps: the gold mode must leave normal maps untouched (flag off on all 45 maps) and win the tiebreak on
   `maps/gold/`; if the user sends the current official pool (from `train_local.sh`), test on the real gold maps too.
3. Rebuild the zip, `submissions/BUILDS.md` row, README/STRATEGY tables (Haiku agent), commit, push.
4. When the user's ES archive arrives: validate `best_params.json` on the merged build and bake it in only if it wins.
   Best is for the user to train the merged build: tell them when it is pushed.

---

## 10. Conventions

- Commit messages end with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01HwDbgTPDFYPU6J7emgx9Ev
  ```
  Push with `git push -u origin claude/laughing-curie-3rq6hu`. No PR unless asked.
- Code style:
  - tabs;
  - comments explain *why*, with the measured evidence;
  - every tunable lives in `params.h` with a comment;
  - every engine action is wrapped in try/catch;
  - every new loop is checked for fuel cost (count rollovers with `decode(..., {rollovers: true})` on
    `maps/gen16_98x99_V_c5.map26a`).
- Every behaviour change gets a switch in `params.h` and an A/B on the panel before it becomes the default.
  Record the result in the param's comment and in `docs/STRATEGY.md` §7.
- Work on copies (`bots/_dev`, `bots/_x_*`) and benchmark frozen copies; never rebuild a bot a running
  benchmark uses.
