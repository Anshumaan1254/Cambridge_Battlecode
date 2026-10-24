# MAPAnalysis.md: map analysis for the new bot (session 18, Oct 24 2026): read this first

This file is the complete handoff for the map-analysis work. It holds the user's requests (with every change they made in chat), every
fact measured so far with its evidence, the full plan, exact formats, commands, and where the work stopped. A new Claude session can
start from section 7 ("Where we left off") without reading the chat.

Read order: sections 1-2 (what the user wants and the rules), 3 (measured facts), 4 (the official map pool), 5 (the plan), 7 (resume).
`AGENTS.md` (long history) and `god2_session17/README.md` (the latest ladder study) are background; this file is the source for map analysis.

---

## 1. The user's requests (session 18, Oct 24), with their answers and corrections

### 1.1 The request
The user uploaded three patch-note PDFs and wrote: "As an expert data analyst and strategy develop plan the following objectives: now this
bot is old and many new patches are there ... there are new maps too, see all of them and tell me one thing at a time; tell me how i can do
map analysis, any technique of ML, DL, gen(etic/erative), maths etc. on any compute power, that increments our bot potential to its finest;
the github is not updated yet; see for new cambc package and download all new maps and analyze them; the data should be directly used by
the bot that I am going to create now; see dates of patch notes too."

### 1.2 Their answers to the four planning questions
| Question | Answer |
|---|---|
| How to get the official maps (`cambc maps pull` was blocked by the network policy) | **"i have allowed all domain"**: 2026a.battlecode.co.uk now answers (HTTP 200); `cambc init` downloads the pool without a login (section 4) |
| Should the bot recognise today's official maps exactly? | **"Table + model fallback"**: an exact-match table keyed by a map fingerprint holds the best measured settings for each official map; a learned model decides on any map it has never seen |
| Compute for heavy runs | **their laptop: 18 cores + GPU** (one-command scripts; the user uploads the result archive) |
| Pacing | **report each step, keep going** (short report and push after each step, no waiting) |

### 1.3 First addition (chat, mid-session): four per-map plans the analysis must produce
1. **Initial champion-to-camp assignments.**
2. **Legal altar approach tiles and banking routes.**
3. **Valuable contested groups and estimated arrival times.**
4. **Conditions for abandoning a route or regrouping.**

### 1.4 Second addition (chat): corrections to the economy and banking model
- "value / (kill + capture + travel + recall) is a useful first approximation, but it **omits tribute time** and **treats recall as
  mandatory**. Include **champion-specific clearing**, **damage taken**, **healing/shopping**, **respawn waits**, and **interference between
  teammates**."
- "'we cannot reach an altar -> play gold tiebreak' is **unsafe**: **check both teams separately, including legal dash/crystal access**.
  **Gold only decides when tribute totals tie**."

### 1.5 Third addition: this file
"push the plan along with my two chats ... to github as MAPAnalysis.md that tell other claude everything that we thought and he can start
from where we left off, detailed md, each detail."

### 1.6 Standing rules (from earlier sessions, still in force)
- Repository: single branch `main`; `git pull --no-rebase origin main` before every push, never force; no pull request unless asked.
  Commit and push at every step; keep a checkpoint (section 7) up to date.
- **Agents**: few subagents and few parallel background jobs. **Fable** subagents for the main / heavy tasks, **Opus** below that, then
  **Sonnet**, **Haiku** for the smallest (docs, file moves). Do the core reasoning yourself.
- **No hardcoded map strategy**, except the exact-match table the user approved in 1.2 (it is data measured per official map, with a model
  fallback for every other map). Everything else is computed from the map and the engine at runtime. List any hardcoding in `ISSUES.md`.
- Ship a bot only when it is measured better, and push the zip first. Never `pkill -f` / `killall` (kill by PID).
- Never use or commit the personal PDFs that arrived in session 13.
- The user answers slowly: decide, write the decision down, continue.

### 1.7 Fourth addition (Oct 24, a new prompt for the agent that carries out the plan): scope change and source rule
**Source rule** ("the repo is old; do not rely on anything in it from before the patches"). Allowed inputs, and only these:
1. the engine itself (cambc 3.0.5 = engine v1.0.3), its SDK header `sdk/cpp/cambc.h` (3.0.5) and our own engine probes
   (`experiments/results/probe_v3_0_5/engine_3_0_5.txt` from `tools/probe/engine_probe_main.cpp`, and any new probe);
2. the 40 official maps in `maps/official/` and their runtime dump (`tools/probe/groups_probe_main.cpp`,
   `experiments/results/mapintel/groups_runtime_official40.txt`, extended in step 3);
3. the current rules: `docs/patch_notes/week2_20261020.txt`, `docs/patch_notes/week3_20261021.txt`, the patch timeline of section 3.1,
   `docs/sprint/v3_0_4/GameRules.md`, `docs/sprint/v3_0_4/BotAPICpp.md`. Where a document disagrees with the engine, the engine wins (probe it);
4. current-patch ladder data only (engine 1.0.3 or newer): `god2_session17/findings/live/groups_matches.jsonl` (2,580 match summaries,
   Oct 22-23, all 40 maps, our team vs 14 teams; **only the opponent side is real data**: our side was an old bot of ours), and the match
   lists and replays the user downloads with `tools/mapintel/fetch_ladder.sh`;
5. this file (the plan and the facts measured on Oct 24).

**Not inputs**: every bot in `bots/` (GOD v10, legend, the proxies and personas) with its draft weights, parameters and build lists; every
ledger result and test pool (all308, train156, test152, ...); the old generated or replay maps; old findings and docs (the history in
`AGENTS.md`, `docs/strategy_v2/`, `docs/ENGINE_FACTS.md`, the pre-patch `docs/sprint/GameRules.md`, the contents of `SUGGESTIONS.md` /
`ISSUES.md`). Code in `tools/` may be reused **as code only**, after a check on the 3.0.5 engine (each check is recorded in section 7).
Probe and test bots are built fresh from the starter that `cambc init` (3.0.5) writes, never from a bot in `bots/`.

**Scope (changed Oct 24 after the plan was written; the user is writing their own new bot, which will use these outputs)**:
- IN: step 3 in full (geometry, the full-cycle economy model, plans 1-4, the per-champion tile analysis by kit class, the catalog); step 4
  (archetypes); step 6 (the map model: fitted on exact computation plus current-patch real data, refitted later on simulations with the
  user's new bot); step 8 (the exact-match table and a standalone header-only C++ library with its own tests); the laptop scripts (the
  ladder download now, the simulation batteries later, for the user's bot); step 7 only where step 6 plateaus, and only to improve the model.
- OUT: using any existing bot as a base or as a source of labels (GOD v10, legend, the proxies, the personas); integration into any bot;
  A/B tests, shipping, adversarial map search.
- Every output is marked by origin: **COMPUTED** (engine and map alone), **LEARNED** (current-patch real games), **SIMULATED** (the user's
  new bot's games, later).
- The plan's decisions stay: the exact-match table with model fallback, the four per-map plans, the full-cycle economy model, banking
  checked per team, the tiebreak cases. Wherever the plan relied on GOD v10 or old data, the allowed sources are used instead; each such
  adaptation is listed in section 7.
- Order of work: (A) the laptop scripts first (`fetch_ladder.sh`, `run_battery.sh --bot NAME`); (B) while the user runs the ladder download:
  step 3, step 4, the model-free parts of step 8, the step-6 code on the 2,580 summaries; (C) when the archive arrives: decode, fit the
  LEARNED models, validate, fill the table; (D) later, the user's own bot through the batteries, then the SIMULATED refit.
- The older prompt `docs/HANDOFF_PROMPT_MAPANALYSIS.md` (built on GOD v10, shipped a bot) is replaced by this one and was deleted.

### 1.8 Fifth addition (Oct 24, chat): GOD v10 may stand in for the user's new bot
"You can use v10 as a base model but it will go huge changes afterwards; use it as base only and make this like that after changes we can
also use it directly or by little changes; for many things you can use stats too; also plan and roster will be done by drafting team
...; but here you can use v10 as base for necessary tasks." Read as:
- GOD v10 (`bots/god`, read-only) may be used where a bot is necessary: the simulation batteries run now on a battery copy
  (`bots/_mi_v10` = v10 + the library headers + the forced-roster call, `tools/mapintel/prepare_bot.py god _mi_v10`), and v10's game
  statistics may serve as labels and checks (marked **SIMULATED (v10)**). They are refitted on the user's own bot when it exists
  (`run_battery.sh --bot <copy> --from <their bot>`).
- The library must plug into a v10-derived bot directly or with small changes: its draft-memory block must not collide with v10's
  (v10 writes 4 bytes `B7 ..` or its 0xC8 `dmplan` layout from offset 0; the mapintel block goes to offset 512, see 5.8 / 7.4).
- The draft decision (roster and plan) is made by the bot's draft code; the library supplies its inputs (features, table, model, plans).

---

## 2. Background: the bots and what the ladder says (as of Oct 24)

- **`submissions/god.zip` = GOD v10** (Oct 21, engine 3.0.4).
  - What it adds: the dynamic draft (a logistic model of champion stats × map features, fitted on ~17,000 games), the watchdog, the draft
    guard, `safety_range`, `fix_my_dash`, and two fight thresholds.
  - Source and numbers: `bots/god`, `README.md`, `docs/strategy_v2/17_PATCH_3_0_4.md`, `18_V9_AND_PLAN.md`.
  - Local A/B protocol: pools `experiments/pools/{all308,train156,test152}.csv`; tools `tools/abstat.py` (Wilson interval + per-map sign
    test) and `tools/abmargin.py` (gem margin, paired).
- **`god2_session17/` (Oct 23-24, the user's own session on their Windows machine, logged in to the platform)**:
  - The user's ladder bot `god.zip` there is GOD v8 + the opponent model (`bots/g8`, rank 15 before the patches).
  - Against the top three (prism best girl #1, Intercontinental Fish #2, Claudus Maximus) on all 40 maps × 2 sides it went **13-227**.
    The variants `god2_load` and `god2b` went 12-228.
  - **The gap is farming, not stolen bags**: we capture ~420 camp gems a game, they capture 1,050-1,090.
    - Split of the gap: farm share of alive time 41%, camp damage per farm round 31%, dead time 14%, target value 13%.
    - **73% of the gap is in the middle band** (126 vs 594 gems a game).
  - Other measured differences:
    - they stand on respawning groups 71 rounds per body, we 20; they re-hit respawned groups after 28 rounds, we after 37-49;
    - contact reflex: with an enemy within 8 we farm 3-6% of rounds and walk 76-82%; they farm 15.9%;
    - walking is the strongest behavioural predictor of strength;
    - strong teams keep 3+ bodies together through r100-600, take the first middle capture and the first kill, turn gold into max HP at
      every spawn visit, and bank at middle altars.
  - Source: `god2_session17/README.md`, `findings/top2/gap_g8.md`, `an_*.md`.
  - **Implication for this work**: map analysis must make farming faster and safer: better targets, assignments and routes; the middle
    band; respawn timing; banking. Fancier fighting is not the lever.
- **Local throughput** (this container, 4 CPUs): one game takes ~0.6 s on one core; `tools/ledger.py --jobs 4` plays ~1.3 games a second.
  Mean game length is 1,549 rounds, and **24% of games reach r2000** (tiebreak), measured on 3,968 ledger_v3 games. The 18-core laptop
  should do ~4-5 games a second (~16,000 an hour). The engine runs on CPU only; a GPU only helps model training.

---

## 3. Measured facts (step 1 of the plan, done Oct 24)

### 3.1 Patch timeline: notes, packages, engines
| Patch note (site date, author) | Content | cambc on PyPI (UTC) | Engine wasm | Our build on it |
|---|---|---|---|---|
| **1.0.0 "Week 2"** (20 Oct, updated 21 Oct; randomuserhi) | full rebalance (below); new champion Heart of Ruin; new camp Golem; camp rewards cut; monolith range 3→5, elk range 3→4; kill gold 50→100; ward cooldown 1→10; altar lock 3→5 hits; maps changed and added; breaking SDK (new enums, `ability_dash` fields) | 3.0.0 (20 Oct 02:50), 3.0.1 (03:27) | v1.0.0 | GOD v2-v7 |
| **1.0.1** (21 Oct; randomuserhi) | emergency nerf of Heart of Ruin: strength per shard 5→4, focus per shard 15→12. Ladder: a bot that no longer compiles is marked invalid, with 24 h to resubmit before auto-losing ranked matches | 3.0.2 (20 Oct 18:13); 3.0.3 (20 Oct 21:56, no note) | v1.0.1 | GOD v8 |
| **1.0.2** (21 Oct; Max) | Stellar hp 750→650 (+75→+65), focus 85→70 (+9→+7); Heart of Ruin str 40→30 (+4→+3.5), dash landing 1.75→1.5 × focus; Ren S1 stun damage 1.25→0.75 × focus; Vesper hp 900→1000, str 50→55; Vendetta hp 800→1000; Tavi hp 750→900, focus 100→110; Prism focus per carried gem 1→1.5 | 3.0.4 (21 Oct 02:18) | v1.0.2 | GOD v10 |
| (no note) | debug drawings now last until the drawing champion's next turn (SDK comment only) | **3.0.5 (22 Oct 06:44), current** | v1.0.3 | - |

1.0.0 details (also in `docs/patch_notes/week2_20261020.txt`):
- Cassi hp 700→600, growth hp 71.25→65, str 3.5→3, focus 15→13. Issac growth hp 95→80, str 4.75→3.
- Stellar focus 100→85, str 35→30, focus growth 10→9. Varg str 50→40. Ren str 40→35, focus growth 10→9. Ryth str 50→45.
- Marcella focus 50→60 (+10→+15), passive: 2 gold per tributed gem and stun immunity. Willow str 45→55, focus 105→120.
- Vesper gold bonus 20→33%, str 45→50. Vendetta str growth 5→6.
- Prism focus per gem 0.2→1, growth hp 75→60, str 3.5→2.5, focus 10→8. Tavi stun damage 2.2→1.4 × focus, str 35→45.
- Heart of Ruin: melee; 1000 hp (+100); str 40 (+5); focus 100 (+15); passive up to +50% damage at 0% health. S1: self shield 1.5 × focus for
  5 turns. S2: dash 2 that deals 1.75 × focus on landing and stuns for 1 turn within radius 1.
- Camps:
  - wolf 22→4 gems, 90→40 gold;
  - elk 36→15 gems, 160→90 gold, range 3→4;
  - gem cluster hp 500→120, gems 24→7;
  - gold cluster hp 500→120, gold 35→20;
  - monolith range 3→5;
  - Golem (new): 5000 hp, 120 str, range 4, 36 gems, 160 gold, respawn 80.

The site's dates are a few hours after the PyPI uploads (time zone / posting delay). The engine version numbers follow the patch numbers.

### 3.2 cambc 3.0.5 changes nothing in play (it is safe to treat 3.0.4 results as 3.0.5 results)
- **SDK diff 3.0.4 → 3.0.5**: `sdk/cpp/cambc.h` differs only in the comment on debug drawings (lines 5168-5169). `imports.h` is identical.
  The Python, Rust and OCaml SDKs differ in the same comment and its tests.
- **Engine probe**: `tools/probe/engine_probe_main.cpp` (new; prints game settings, all camp designs, all champion designs and abilities)
  gives identical output on 3.0.4 and 3.0.5 (`experiments/results/probe_v3_0_5/engine_3_0_{4,5}.txt`). The champion lines also equal the
  committed 3.0.4 probe (`experiments/results/probe_v3_0_4/champions_engine_3_0_4.txt`).
- **Identical games**: GOD v10 vs legend_m15 on all 40 official maps × 2 sides gives the same winner in the same round on both engines,
  80/80 (`experiments/results/probe_v3_0_5/identical_games_304_vs_305.txt`; GOD v10 won 76/80).
- Consequences, done this session:
  - `tools/ledger.py` maps engine 3.0.5 to the 3.0.4 ledger (`ledger_v3_0_4/`), so no game is replayed;
  - `cambc.toml` is now sdk 3.0.5; the repo's `sdk/` (git-ignored) is the 3.0.5 SDK;
  - `tools/setup_session.sh` installs 3.0.5, takes the SDK and the official maps from a scratch `cambc init`, copies the maps into
    `maps/official/`, and prints any map that is new or changed on the platform.

### 3.3 Engine constants (3.0.5 = 3.0.4), as the engine reports them
| Setting | Value | Setting | Value |
|---|---|---|---|
| capture time | 5 rounds | camp sleep | 2 rounds without a champion in range |
| champion respawn | 60 rounds | recall | 5 turns (3 with the Home emblem) |
| tribute (submit) duration | **max(1, ceil(0.1 × gems))** turns (mult 0.1, base 0, min 1) | tribute range | **1 (Chebyshev) from the altar** |
| max rounds / winning gems | 2000 / 1000 | kill / assist / passive gold | 100 / 0 / 0 |
| spawn healing | 100% of max hp per round on spawn | wards | 1 active, cooldown 10, never expire, vision 6, placement 2 |
| altar lock | 5 hits to break | teleport crystal | range 3, 3-turn channel |
| shared memory / draft memory | 8 / 1024 bytes | tile reveal | 1 round |
| Prism focus per carried gem | 1.5 | Varg splash radius | 1 |
| Vesper bonus gold | 33% | Marcella gold per tributed gem | 2 |
| Ryth strength per bonus hp | 0.01 | Ren retaliation | 0.2 × focus |
| Heart of Ruin max missing-health bonus | 50% | camp damage multiplier | 1.0 for every champion |

**Camp designs, with rewards and respawn measured on the 40 official maps.** Each group's reward is exactly the sum of its camps' rewards
(least squares over every runtime group: residual 0). Each group's respawn is that of its slowest camp.

| Camp | hp | str | range | gems | gold | respawn (group) |
|---|---|---|---|---|---|---|
| wolf | 1350 | 20 | 3 | 4 | 40 | 40 (50 with clusters) |
| elk | 2400 | 60 | 4 | 15 | 90 | 60 |
| gem cluster | 120 | 0 | 3 | 7 | 0 | 50 |
| gold cluster | 120 | 0 | 3 | 0 | 20 | 50 |
| golem | 5000 | 120 | 4 | 36 | 160 | 80 |
| monolith | 20000 | 200 | 5 | 200 | 300 | 150 |

**Champion designs (base, growth per shard; abilities; every cooldown is 8)**:
| id | Champion | hp | str | focus | range | abilities |
|---|---|---|---|---|---|---|
| 0 | Ryth | 1200 (+100) | 45 (+5) | 100 (+10) | 1 | aoe stun r4 rad1 1.0 × focus, dur 1; attack reset |
| 1 | Vesper Vale | 1000 (+100) | 55 (+5) | 100 (+10) | 3 | attack reset; **dash 2** |
| 2 | Vendetta | 1000 (+100) | 70 (+6) | 100 (+10) | 1 | attack reset; **dash 2** |
| 3 | Cassi | 600 (+65) | 30 (+3) | 70 (+13) | 3 | damage r4 2.0 × focus; cc r4 dur 1 |
| 4 | Issac | 900 (+80) | 40 (+3) | 100 (+10) | 1 | attack reset; **dash 2** |
| 5 | Stellar | 650 (+65) | 30 (+3.5) | 70 (+7) | 3 | damage r4 2.0 × focus; aoe r4 rad1 1.4 × focus |
| 6 | Prism | 700 (+60) | 35 (+2.5) | 80 (+8) | 3 | cc r4 1.5 × focus dur 1; aoe r4 rad1 1.0 × focus |
| 7 | Marcella | 1200 (+100) | 45 (+5) | 60 (+15) | 1 | enhanced attack reset; damage r4 2.0 × focus |
| 8 | Willow | 700 (+50) | 55 (+3) | 120 (+5) | 3 | heal r4 3.0 × focus; attack reset |
| 9 | Ren | 900 (+100) | 35 (+5) | 100 (+9) | 1 | cc r4 0.75 × focus dur 1; **dash 2** |
| 10 | Varg | 1000 (+100) | 40 (+5) | 100 (+10) | 1 | attack reset; shield r4 2.5 × focus, 5 turns |
| 11 | Tavi | 900 (+75) | 45 (+5) | 110 (+10) | 3 | attack reset; cc r4 1.4 × focus dur 1 |
| 12 | Heart of Ruin | 1000 (+100) | 30 (+3.5) | 100 (+12) | 1 | self shield 1.5 × focus, 5 turns; **dash 2, landing 1.5 × focus, radius 1, stun 1** |

Cassi and Issac are one draft pick (two bodies). Dash kits: Vesper, Vendetta, Issac, Ren and Heart of Ruin. Draft pick ids (`champion_draft`):
Ryth 0, Vesper 1, Vendetta 2, C&I 3, Stellar 4, Prism 5, Marcella 6, Willow 7, Ren 8, Varg 9, Tavi 10, HoR 11.

### 3.4 How the engine stores camps (important for every map tool)
- **A `.map26a` file stores one copy of each mirrored camp**: half of the camps and half of the groups. The engine builds the mirrored
  half at runtime.
- Inside a stored group, a camp may be stored as its mirror image. Example: elkring's stored group 0 is elk (3,6), gold (3,7), gem (25,23).
  At runtime that group is elk (3,6), gold (3,7), gem (4,6), and its mirror group holds (25,23).
- The engine therefore pairs the copies **by position**. A tool that reads map files must, for each stored group, take every member's
  copy (p or mirror(p)) nearest the group's first camp. That gives one side's group; the mirror of all members gives the other.
- **Ground truth**: `tools/probe/groups_probe_main.cpp` (new) prints `bc::map::camp_groups()` as a bot sees it: gems, gold, respawn,
  members with type and spawn tile.
  - Output for all 40 maps: `experiments/results/mapintel/groups_runtime_official40.txt`, 836 groups.
  - Each body is a separate process writing to the same team stdout, so every group appears up to 5 times; parsers keep one copy per
    group index.
  - Heavy maps need `--rounds 8`, because the first game turn spills over.
- Engine export layout found while probing (`tools/mapgen/engine.mjs` loader, map file loaded with `Game_FromMapFileBytes`):
  `Game_GetCampGroup(game, handle, out)` writes int32 [gems, gold, respawn, number of camps]; `Game_GetCampGroupCamp(game, handle, i, out)`
  gives the i-th member's camp handle. These read the **stored** half only.

---

## 4. The official map pool (step 2, done Oct 24)

- `cambc init` (3.0.4 and 3.0.5 alike) printed "Refreshing the map pool from https://2026a.battlecode.co.uk ... 40 platform maps
  available"; **no login needed**. Both versions downloaded byte-identical maps.
- Stored in **`maps/official/`** under the platform's names (`00*.map26a`, `01*.map26a`; unique under `maps/`, so the ledger is safe), with
  `SHA256SUMS` and **`summary.csv`** (`tools/mapintel/official_summary.py`).
- **21 of the 40 equal maps we had rebuilt from replays** (the engine's view, ASCII-identical):
  - `maps/comp30/*_v3`: ambush, collision, contest, corners, eight, elkring, expanse, fragment, interlock, lanes;
  - `maps/loss_oct20/ls50x50_R_c5_56fe6f` = 00monolith;
  - `maps/nyx_new`: nx100x100 = 01big-world, nx50x41 = 01boss-battle, nx40x40_c3 = 01broken-curve, nx61x61 = 01concentrated-wealth,
    nx51x40 = 01corridors, nx50x50 = 01elk-arena, nx61x71 = 01fracture, nx31x31_c3 = 01gold-rush, nx31x31_c4 = 01hooks,
    nx60x60 = 01islands.
- **19 are new to us**: 00gem-fields, 00gemfight, 00great-wall, 00lost-world, 00quadrants, 00reverse-spiral, 00road-of-riches, 00split,
  01shortcut, 01starfish, 01starvation, 01the-farm, 01yellow-brick-road; and the patch-3.0 versions of 00packs, 00pilgrimage, 00rows,
  00rushbait-v2, 00stampede, 00swirl (`maps/comp/` holds their old versions).
- Team sizes:
  - 3: collision, fragment, packs, broken-curve, gold-rush, the-farm;
  - 4: gemfight, interlock, reverse-spiral, rows, rushbait-v2, swirl, hooks, shortcut;
  - 5: the other 26.
- Golems: great-wall 4, quadrants 2, reverse-spiral 2, road-of-riches 2, split 2, lost-world 1.
- Monoliths: 16 maps (contest, great-wall 4, lost-world, monolith, road-of-riches, rows, split, big-world, boss-battle, broken-curve,
  corridors, fracture, gold-rush, shortcut, starvation, the-farm).
- One altar only: eight, hooks, boss-battle. boss-battle's altar sits inside a wall line behind monolith tiles and holes; GOD v8+ fixed
  banking there with `altar_no_camp`.
- Gems on the whole map (sum of group rewards, both sides) range from **68 (fragment)** to **1,404 (great-wall)**. On low-gem maps
  (fragment 68, elk-arena 72, hooks 88, packs 148, stampede 160, pilgrimage 184) the 1,000 gems come from many respawn cycles, so respawn
  timing and re-take speed decide them, and r2000 tiebreaks are likely.

`summary.csv` per map (gems / gold summed over both sides). `gems_mid` uses a crude side rule (the group's first camp within 2 tiles,
Chebyshev, of equidistant from the two spawn centres); step 3 replaces it with walking distances.

| map | size | sym | team | groups | gems | gold | wolf | elk | gem cl. | gold cl. | mono | golem | altars | holes | bushes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 00ambush | 100x100 | R180 | 5 | 12 | 270 | 1340 | 2 | 10 | 16 | 18 | 0 | 0 | 4 | 1832 | 132 |
| 00collision | 41x41 | V | 3 | 20 | 280 | 1700 | 8 | 10 | 14 | 24 | 0 | 0 | 2 | 60 | 222 |
| 00contest | 50x50 | R180 | 5 | 14 | 400 | 1240 | 0 | 0 | 0 | 32 | 2 | 0 | 2 | 0 | 26 |
| 00corners | 71x71 | H | 5 | 30 | 396 | 2820 | 14 | 18 | 10 | 32 | 0 | 0 | 5 | 84 | 60 |
| 00eight | 41x30 | H | 5 | 8 | 230 | 1300 | 6 | 10 | 8 | 8 | 0 | 0 | 1 | 22 | 24 |
| 00elkring | 30x30 | R180 | 5 | 10 | 220 | 1100 | 0 | 10 | 10 | 10 | 0 | 0 | 2 | 36 | 36 |
| 00expanse | 80x80 | R180 | 5 | 24 | 362 | 2340 | 10 | 14 | 16 | 34 | 0 | 0 | 10 | 16 | 0 |
| 00fragment | 30x30 | R180 | 3 | 6 | 68 | 540 | 6 | 2 | 2 | 6 | 0 | 0 | 2 | 320 | 24 |
| 00gem-fields | 50x40 | R180 | 5 | 18 | 364 | 600 | 6 | 4 | 40 | 0 | 0 | 0 | 4 | 46 | 112 |
| 00gemfight | 30x30 | R180 | 4 | 19 | 200 | 500 | 4 | 2 | 22 | 8 | 0 | 0 | 2 | 108 | 16 |
| 00great-wall | 50x40 | V | 5 | 17 | 1404 | 3120 | 8 | 8 | 44 | 12 | 4 | 4 | 4 | 80 | 60 |
| 00interlock | 40x40 | R180 | 4 | 14 | 200 | 1200 | 6 | 8 | 8 | 12 | 0 | 0 | 4 | 16 | 38 |
| 00lanes | 90x30 | H | 5 | 42 | 294 | 2460 | 30 | 6 | 12 | 36 | 0 | 0 | 18 | 76 | 144 |
| 00lost-world | 35x31 | V | 5 | 34 | 592 | 1440 | 8 | 2 | 42 | 24 | 1 | 1 | 3 | 42 | 24 |
| 00monolith | 50x50 | R180 | 5 | 20 | 670 | 1940 | 18 | 2 | 24 | 22 | 2 | 0 | 6 | 0 | 66 |
| 00packs | 31x31 | R180 | 3 | 8 | 148 | 1120 | 8 | 4 | 8 | 22 | 0 | 0 | 6 | 0 | 62 |
| 00pilgrimage | 50x65 | H | 5 | 23 | 184 | 1740 | 6 | 6 | 10 | 48 | 0 | 0 | 4 | 654 | 152 |
| 00quadrants | 45x45 | R180 | 5 | 21 | 763 | 1320 | 16 | 4 | 81 | 0 | 0 | 2 | 4 | 0 | 104 |
| 00reverse-spiral | 30x30 | R180 | 4 | 14 | 334 | 1280 | 12 | 4 | 22 | 6 | 0 | 2 | 2 | 32 | 16 |
| 00road-of-riches | 40x40 | R180 | 5 | 51 | 1158 | 2800 | 12 | 8 | 74 | 34 | 2 | 2 | 2 | 22 | 44 |
| 00rows | 50x50 | R180 | 4 | 9 | 584 | 1680 | 18 | 0 | 16 | 18 | 2 | 0 | 2 | 0 | 140 |
| 00rushbait-v2 | 30x80 | R180 | 4 | 18 | 258 | 1360 | 10 | 8 | 14 | 12 | 0 | 0 | 2 | 142 | 120 |
| 00split | 45x35 | H | 5 | 32 | 850 | 2660 | 16 | 6 | 32 | 28 | 2 | 2 | 3 | 30 | 44 |
| 00stampede | 60x50 | V | 5 | 13 | 160 | 1180 | 0 | 6 | 10 | 32 | 0 | 0 | 2 | 610 | 456 |
| 00swirl | 45x30 | R180 | 4 | 22 | 638 | 3760 | 24 | 24 | 26 | 32 | 0 | 0 | 2 | 354 | 14 |
| 01big-world | 100x100 | R180 | 5 | 24 | 832 | 2760 | 22 | 8 | 32 | 28 | 2 | 0 | 6 | 538 | 302 |
| 01boss-battle | 50x41 | V | 5 | 31 | 1180 | 7400 | 30 | 44 | 0 | 82 | 2 | 0 | 1 | 4 | 2 |
| 01broken-curve | 40x40 | R180 | 3 | 22 | 746 | 2520 | 10 | 12 | 18 | 22 | 2 | 0 | 4 | 0 | 68 |
| 01concentrated-wealth | 61x61 | R180 | 5 | 11 | 177 | 1110 | 12 | 3 | 12 | 18 | 0 | 0 | 2 | 22 | 256 |
| 01corridors | 51x40 | V | 5 | 12 | 752 | 2960 | 22 | 12 | 12 | 20 | 2 | 0 | 2 | 30 | 144 |
| 01elk-arena | 50x50 | R180 | 5 | 29 | 72 | 1260 | 0 | 2 | 6 | 54 | 0 | 0 | 2 | 0 | 186 |
| 01fracture | 61x71 | R180 | 5 | 28 | 844 | 3320 | 16 | 16 | 20 | 32 | 2 | 0 | 3 | 540 | 276 |
| 01gold-rush | 31x31 | R180 | 3 | 15 | 266 | 1100 | 6 | 0 | 6 | 28 | 1 | 0 | 4 | 72 | 46 |
| 01hooks | 31x31 | R180 | 4 | 12 | 88 | 760 | 0 | 4 | 4 | 20 | 0 | 0 | 1 | 0 | 60 |
| 01islands | 60x60 | R180 | 5 | 46 | 608 | 3860 | 24 | 22 | 26 | 46 | 0 | 0 | 10 | 878 | 406 |
| 01shortcut | 40x40 | V | 4 | 21 | 990 | 3040 | 6 | 20 | 38 | 20 | 2 | 0 | 2 | 136 | 52 |
| 01starfish | 50x50 | H | 5 | 16 | 334 | 1860 | 18 | 10 | 16 | 12 | 0 | 0 | 2 | 1302 | 146 |
| 01starvation | 80x80 | H | 5 | 14 | 532 | 1560 | 4 | 4 | 8 | 22 | 2 | 0 | 2 | 58 | 78 |
| 01the-farm | 50x40 | H | 3 | 28 | 1096 | 4540 | 24 | 26 | 30 | 32 | 2 | 0 | 6 | 0 | 76 |
| 01yellow-brick-road | 40x30 | R180 | 5 | 28 | 472 | 4600 | 30 | 16 | 16 | 98 | 0 | 0 | 10 | 0 | 292 |

Counts are camps on the whole map (both sides); "altars" counts altar tiles; holes and bushes are tile counts. A full-pool baseline of
GOD v10 on these 40 maps has not been run yet (step 5).

---

## 5. The plan (approved by the user; steps 1-2 done, step 3 next)

The bot gets two layers of map knowledge:
1. A **model** that turns map features computed at runtime into decisions. It works on any map, including the final sprint's new pool.
2. An **exact-match table** for the 40 official maps, holding the best settings measured per map.

Both, and the analysis behind them, are produced offline and shipped as generated C++ headers (section 5.8).

### 5.1 Step 1, patch and package check: done (section 3)
### 5.2 Step 2, download every map: done (section 4)
- Optional, not done: with `cambc login` (the user does it; never handle credentials), `cambc matches` / `match-groups` can download our
  recent ladder replays on these maps. session 17's `god2_session17/tools/live/` has the tooling (`dl_replays.py`, `fetch_matches.py`,
  `finish_sweep.py`).

### 5.3 Step 3, exact map geometry and the per-map plans (next): `tools/mapintel/`
Python (`python3 -I`), reading maps through the engine. Two sources:
- the **runtime dump** (groups, camps, altars, spawns as a bot sees them; extend `tools/probe/groups_probe_main.cpp` to also print the
  spawn regions, altar tiles and wall / hole / bush bitboards);
- or `tools/mapgen/engine.mjs` (stored half plus the mirror rule of 3.4).

Prefer the runtime dump: it is exactly what the bot sees. Per map (both teams, every quantity separately for team A and team B):

**a. Basics**: size, symmetry, team size, walkable / wall / hole / bush shares, spawn regions, altar tiles.

**b. Distances**:
- walking BFS (Chebyshev moves, one tile a round) from every spawn tile, altar and group;
- dash-augmented BFS for each champion with a dash (range 2, cooldown 8: model a dash as a 2-tile move that may cross holes, where legal,
  once per 8 rounds; verify the legality rules with an engine probe before relying on them; `World::dash_walls` in `bots/god/src/world.cpp`
  is the bot's current rule);
- crystal hops (range 3 over walls / holes, 3-turn channel; bought on spawn).

**c. Camp groups, values and the full cycle economy model (the user's correction, 1.4).** For a group g and a set S of our bodies:
- **clearing (champion-specific)**: per camp c, our damage per round
  DPS_S(c) = Σ_b [strength_b × (1 + attack-reset rate) × camp_damage_multiplier (1.0) × Monster emblem bonus if built]
  + Σ_b spell damage (modifier × focus / cooldown, when cast on camps)
  + Varg's splash on the other camps within radius 1 + area spells on clustered camps + Heart of Ruin's missing-health bonus.
  Kill time T_kill(S,g) = Σ over camps in kill order of hp_c / DPS_S(c). Camps wake on damage and sleep 2 rounds after no champion is in
  range; they never chase.
- **damage taken**: each awake camp hits the nearest champion within its range for its strength each round. A body outside the camp's range
  takes nothing (elk 4, golem 4, monolith 5; wolf 3; clusters do not attack). Count shields, the Jungle emblem and the rounds each camp lives.
- **healing and shopping**: when damage taken exceeds a body's hp above its retreat line, it needs trips to spawn (100% heal per round on
  spawn). trips = ceil(damage / usable hp), each costing the cheapest way back and forth. Shopping happens only on spawn (and for Tavi
  anywhere), so it rides on these trips; the gold value of the capture buys items at the next visit.
- **capture**: 5 rounds on one spawn tile of the dead group, uncontested (the timer resets if contested or left).
- **tribute (banking)**: max(1, ceil(0.1 × bag)) turns on a **legal approach tile** (5.3e). Bank where the bag's route makes it cheapest.
- **getting home is a choice, not a cost**: the cheapest of walking, recalling (5 turns, cancelled by any damage; 3 with the Home emblem)
  and banking at a nearby altar on the way. Recall is never assumed.
- **respawn waits**: the group's respawn timer (table 3.3) and the wait if we arrive early. Stand next to the group, never on a spawn tile:
  an occupied spawn tile delays the respawn.
- **interference between teammates**:
  - two bodies on one group finish sooner but split the reward (the lowest id gets the remainder);
  - two bodies heading for the same group or the same narrow route waste trips;
  - plans are joint: groups are assigned so bodies do not collide, and a body's value is net of what it takes from its allies.
- **rate and pace**: the gem rate of a plan = gems banked / rounds. The unopposed pace estimate (rounds to 1,000 banked) per team size
  comes from the multi-body plan of 5.3d. **Validation**: Spearman ≥ 0.8 against measured idle pace per map (`tools/ledger.py run god idle`),
  and per-group capture times against replays.

**d. Plan 1: initial champion-to-camp assignments (the user's item 1).**
- Inputs: our roster from the draft (each body's kit from the engine), spawn tiles, the groups, the BFS distances, and the clearing /
  damage model.
- Objective: the value banked by round R0 (e.g. 150), or the time to the first k captures weighted by value. Constraints:
  - each body survives its targets, or a pair is assigned (the heavy groups no single body can clear);
  - own-half groups come first;
  - a contested group (5.3f) is taken only with enough bodies committed.
- Method:
  - offline (exact, slow): enumerate or optimise with simulated annealing / a genetic algorithm over joint routes (an orienteering /
    vehicle-routing problem with time windows from respawn timers);
  - online (in the bot, fuel-bounded): Hungarian assignment of first targets (cost = arrival + kill time − value weight), then greedy
    insertion and one 2-opt pass for the next 2-3 groups.
- Output per body slot (pick order to body index): an ordered group list with planned arrival, capture and bank rounds.

**e. Plan 2: legal altar approach tiles and banking routes (the user's item 2, with the per-team correction of 1.4).**
- **Approach tiles** of an altar: every tile within Chebyshev `submit_gems_range` = 1 of the altar that a champion can stand on. That means
  not a wall, not a hole, not an altar, and not a living camp's tile. A dead camp's spawn tile can be stood on, but standing there delays
  that group's respawn; verify with a probe.
- **Reachability, per team separately**: from that team's spawn region, can its bodies reach an approach tile by walking, by a legal dash
  (only if that team's roster has a dash kit; the bot checks its own roster after the draft and the enemy's from the enemy picks), or by a
  teleport crystal hop (range 3, 3-turn channel, needs gold and a spawn visit)? The answer can depend on the draft: on a map where an altar
  is reachable only by dash, the draft should value a dash kit.
- **Bank route per group**: from the group's capture tile, the cheapest of:
  - walk to the nearest legal approach tile + tribute time;
  - recall + walk from spawn to an approach tile + tribute;
  - carry the bag on to the next group (bag risk counted).
  Store it per group: chosen altar, approach tile, ETA, and the altar's side (own / middle / enemy).
- **Tiebreak logic** (rules: tributed gems, then lifetime gold earned, then kills, then team B):
  - **neither team can bank** → play for gold earned, then kills;
  - **only the enemy can bank** → their tributes must be stopped (a stun or kill cancels a tribute; a new altar lock cancels it) and we must
    find our own dash / crystal route. Gold does not help: one tributed gem beats any amount of gold;
  - **only we can bank** → bank early; any banked gem wins the tiebreak;
  - **both can bank** → normal play.
  Never switch to "play for gold" only because we cannot reach an altar.

**f. Plan 3: valuable contested groups and estimated arrival times (the user's item 3).**
- For each group:
  - ETA_us = min over our bodies (spawn at r1, current position later) of walking (or dash) time to a tile from which the body can hit the
    group's camps (range 1 melee, 3 ranged) + kill time for the bodies that would go;
  - ETA_them likewise for the enemy (mirror on symmetric maps, or seen positions later);
  - gap = ETA_them − ETA_us;
  - value = gems + gold weight × gold (+ deny value: what the enemy loses if we take it).
- **Contested** = |gap| ≤ k rounds, or the group lies in the middle band (|d_us − d_them| ≤ band on walking distance). Priority =
  value × closeness of the race.
- Also the **first-contact round** on the route to it: the earliest round an enemy body could reach our path (meeting point of the two
  BFS fronts).
- Output per group: ETA_us, ETA_them, the predicted race winner, value, first contact. These are the inputs of the middle-band play that
  session 17 found decisive (126 vs 594 gems a game).

**g. Plan 4: conditions for abandoning a route or regrouping (the user's item 4).** Rules with thresholds, then learned and checked:
- **abandon a target** when ETA_us > ETA_them + k_abandon and the local power ratio (Lanchester estimate, the bot's `combat()`) < p;
- **regroup** when a body on a contested route is more than d_regroup tiles from the nearest ally, or 2+ enemies are seen within r;
- **abort a bank trip** when our expected arrival at the approach tile is later than the enemy's possible interception of that path
  (their BFS from last-seen positions) minus a margin;
- **drop a group** whose respawn wait exceeds w_max given the next best group's rate.
The thresholds (k_abandon, p, d_regroup, r, margin, w_max) are fitted per map and archetype from simulation traces and replays (Steps 5-6).
They ship in the table for official maps, and come from the model elsewhere.

**h. Conflict geometry**:
- number of separate lanes between the spawns (max-flow over node-split tiles) and chokepoints (articulation points);
- tiles that most routes cross (betweenness) and bushes next to them (ambush risk);
- corridor width (distance transform);
- first-contact point and round.

**i. Objectives**: monoliths and golems against the middle band, and the ring tiles just outside their range (range + 1). Which rosters can
clear them (kill time with spells from range 4 against monolith range 5).

**Outputs of step 3**:
- `maps/catalog/maps.csv` (one row, ~80 features);
- `maps/catalog/<map>.json` (groups with values, ETAs per team, contested flags, approach tiles, bank routes, opening assignments per team
  size, chokepoints);
- `maps/catalog/<map>.npz` (per-tile layers for deep learning);
- an HTML view per map (optional).

**Checks**:
- the bot's own draft-time features (`bots/god/src/draft.cpp` `analyse()`, FEAT lines with `--define "LEGEND_FEATURES 1"`) equal the Python
  values on every map;
- the idle-pace validation above.

### 5.4 Step 4, map archetypes (unsupervised ML)
- Standardise the feature table, then PCA. Cluster with k-means (k by silhouette) and HDBSCAN (outliers); keep the existing k-medoids /
  DBSCAN code in `tools/strategy_v2/map_plan.py` in mind.
- Expected archetypes, for example: small mirror brawls (fragment, hooks, gemfight, elkring), gold races with little gem supply
  (elk-arena, hooks, packs, stampede), monolith / golem economies (great-wall, road-of-riches, split, quadrants, the-farm), mazes and holes
  (ambush, starfish, islands, pilgrimage), large open maps (big-world, expanse, starvation), lanes (lanes, rushbait-v2, corridors).
- Uses:
  - stratified train / test pools;
  - the **nearest-archetype fallback** the bot uses on unknown maps (centroids and scaling exported to C++);
  - loss analysis per archetype.

### 5.5 Step 5, simulation labels per map (the ground truth; on the laptop)
`tools/mapintel/run_battery.sh` (to write, in the pattern of `tools/rl/train_local.sh`) does everything in one command:
- installs cambc 3.0.5;
- builds the bots (`tools/setup_session.sh --bots`);
- runs the batteries with `tools/ledger.py run ... --keep KEEP` (kept stats JSON per game; the draft dataset is read by
  `tools/draftmodel/dataset.py`);
- archives the ledger rows and kept stats for the user to upload.

Sizes on 18 cores (~4-5 games a second):
- **outcome battery**: GOD v10 vs a panel on the 40 official maps (+ all308) × 2 sides. The panel is v8, the `_pn*` personas, `_k_fit`,
  `_q_s2v`, `_mite`, `_ifish`, and the session-17 bots g8 / g8h / god2b as stand-ins for the ladder style. 800 games ≈ 3 min (official);
  records wins, gem margin, deaths, pace and tiebreak share.
- **draft battery**: per team size, the dynamic draft's top-K rosters + the top teams' rosters, against 4 opponents. 40 × 2 × 8 × 4 = 2,560
  games ≈ 10 min. Gives each map's best roster (the table) and data for refitting the draft model.
- **parameter battery**: 6 parameters × 3 levels, against 4 opponents: `gold_value`, `fight_margin`, `isolated_fight_adv`, `tribute_min`,
  `enemy_half_penalty`, `heavy_value`, and the abandon / regroup thresholds of 5.3g once built. 5,760 games ≈ 20 min. Gives each map's
  best levels (the table) and data for the parameter model.
- **traces**: the existing trace builds (`LEGEND_TRACE`, `PT` / `G2F` lines from session 17's `tools/top2/pathtrace.py`) give the
  decision-level labels for plan 4.

### 5.6 Step 6, learn map → decisions (supervised ML)
- **Targets**: win probability and gem margin, given (map features, our roster, their roster, parameter levels), and per-decision labels
  for plan 4.
- **Models**:
  - logistic / ridge with interaction terms (the baseline; `tools/draftmodel/fit.py` / `fit2.py` already fit the draft this way);
  - gradient-boosted trees (LightGBM / XGBoost; GPU optional) with SHAP to find which map × roster interactions matter;
  - **distil** them into the linear model plus its top interactions, or into a small tree ensemble (≤ 32 trees of depth ≤ 4) exported as
    C++ if/else.
- **Parameter policy**: θ(map) = θ0 + W·φ(map), fitted by ridge from the parameter battery's best levels. Refined by **contextual ES** on
  the laptop: W is the search space, games are sampled across maps; `tools/rl/es_train.py` takes `ES_SRC`, `ES_OUT`, `ES_PREFIX` and a space
  file.
- **Selection**: leave-maps-out cross-validation, grouped by archetype. Beat the current draft model's log loss before any game.
- **Lessons from earlier sessions**: only parameters that moved consistently transferred from ES runs. The opponent-model presets and the
  zone plans lost locally. Local proxies do not reproduce the top teams' execution (judge on the ladder too).

### 5.7 Step 7, deep learning and generative methods (laptop GPU; only where step 6 plateaus)
- **CNN / U-Net** on map tensors (walls, holes, bushes, altars, spawns, camp type and value layers) predicting the outcome margin and
  per-tile fight / death heat. Trained on battery replays (decoder `tools/replay/decode.mjs`).
- **GNN** over the camp-group graph (nodes: groups with value / hp / danger; edges: walking times) for roster and plan value.
- Both are offline tools that rank options and reveal features. They are **distilled** into the small in-bot models; fuel is 1M on the
  first draft turn and 100k on every other turn, and a distance field costs 13-19k.
- **Map generator calibrated to the official pool**: a genetic algorithm tunes `tools/mapgen/gen.mjs` parameters until generated maps match
  the official feature distribution. This gives thousands of training maps, so the model holds on the final sprint's unseen maps.
- **Adversarial map search** (GA / MAP-Elites): evolve maps on which GOD loses, to find weaknesses (walled altars, mazes, gem-starved
  maps).
- **Behaviour cloning** of target choice from top-team replays: which group a strong team takes next, given the group features. Session 17
  has their replays and the decoders. The result is weights for the bot's group scoring (`group_score` in `bots/god/src/brain.cpp`).

### 5.8 Step 8, data the bot uses directly (generated headers)
Header-only C++ using only the SDK, regenerated by `tools/mapintel/export_headers.py` and placed in the bot's `src/mapintel/`:
- **`features.h`**: runtime map features with the same definitions as the catalog. Computed once on the first draft turn (1M fuel) and
  packed into draft memory (1,024 bytes) for the bodies. Extend `bots/god/src/dmplan.{h,cpp}` (versioned layout, magic 0xC8).
- **`model_weights.h`** (generated): draft-value weights, the parameter-policy matrix W, the plan-4 threshold model, and the archetype
  centroids and scaling.
- **`known_maps.h`** (generated, the user's "table"): fingerprint → best roster + parameter overrides + offline-optimised plans 1-4 for each
  official map.
  - **Fingerprint**: FNV-1a 64 over (width, height, team size, the wall / hole / bush / altar bitboards as the SDK exports them, and the
    sorted list of runtime camps (type, x, y)).
  - The table's fingerprints are produced **by the same C++ function run inside the engine** (a probe over the 40 maps), never
    re-implemented in Python, so they always match.
  - A map that changes even slightly does not match, and falls back to the model.
- **`plans.h`**: the code that computes plans 1-4 at draft time (fuel-bounded: greedy + one 2-opt pass) and packs them.
  - Draft memory budget, about 400 bytes: per body slot 4 targets × (group id + ETA); per group 1 byte for the bank altar choice
    (≤ 64 groups); up to 16 contested groups × (id, ETA_us, ETA_them); 8 thresholds × 2 bytes; flags (bankable per team, tiebreak mode).
- **Tests**:
  - Python and runtime features are equal on all maps;
  - fuel on the largest maps adds no lost turns (`tools/fueltrace.py`);
  - 0 exceptions (`EXC_TRACE`, `tools/tracecount.py`);
  - builds on SDK 3.0.5 (and 3.0.4).
- **Integration**: a reference integration in GOD v10 behind switches (`mi_table`, `mi_model`, `mi_plans`, all off = v10's games), so each
  layer is measured alone. The user's new bot includes the same headers.

### 5.9 Step 9, measure and ship
- A/B against GOD v10 on held-out maps (test152) and the 40 official maps, both sides; third-party panel; pace; faults; fuel.
  Tools: `tools/abstat.py`, `tools/abmargin.py`, `tools/finalcheck.sh`.
- **Table guard**: the engine is deterministic, so per-map choices can overfit our own proxies. Keep a table entry only when its gain holds
  against at least two opponent families, and check on the ladder (session 17's sweep tools) when the user can run them.
- Ship if better: zip first (`tools/ship_god.sh`), then README / BUILDS / AGENTS / SUGGESTIONS / ISSUES.

### 5.10 What each technique family is for (the user's question "which techniques, on what compute")
| Family | Technique | What it gives the bot | Compute |
|---|---|---|---|
| Maths / graphs (exact) | BFS distance fields, dash / crystal graphs, Voronoi territory, max-flow lanes, articulation points, betweenness, distance transform | ETAs, territory, contested groups, approach tiles, chokepoints: the inputs to every decision; also run inside the bot | CPU, seconds |
| Operations research | assignment (Hungarian), orienteering / vehicle routing with time windows, 2-opt, simulated annealing | plans 1-2 (opening assignments, bank routes), pace estimates | CPU, minutes |
| Game theory / combat maths | Lanchester estimates, race (ETA gap) analysis, tiebreak case logic | plans 3-4, banking rules | CPU |
| Simulation | engine batteries (`cambc run-batch` through `tools/ledger.py`) | ground-truth labels per map: best roster, parameters, thresholds | **CPU-bound: laptop 18 cores** |
| Unsupervised ML | PCA, k-means, HDBSCAN | archetypes, stratified pools, nearest-archetype fallback | CPU, seconds |
| Supervised ML | logistic / ridge with interactions, GBM + SHAP, distillation | the model layer (draft, parameters, thresholds) | CPU / GPU, minutes |
| Black-box optimisation | ES / CMA-ES, contextual ES, Bayesian optimisation | parameter policies θ(map) | CPU-bound (games) |
| Deep learning | CNN / U-Net on map tensors, GNN on the group graph | offline ranking and feature discovery, then distilled | GPU |
| Generative / genetic | GA-calibrated map generator, MAP-Elites adversarial maps | robustness to unseen maps (final sprint) | CPU (games) |
| Imitation | behaviour cloning of top-team target choice | group-scoring weights | GPU optional |

---

## 6. Files added or changed this session

| Path | What |
|---|---|
| `MAPAnalysis.md` | this file |
| `maps/official/` | the 40 official maps (platform names), `SHA256SUMS`, `summary.csv` |
| `tools/probe/engine_probe_main.cpp` | engine probe: game settings, camp designs, champion designs and abilities |
| `tools/probe/groups_probe_main.cpp` | runtime camp groups as a bot sees them (single write per line; every body prints) |
| `tools/mapintel/official_summary.py` | per-map summary table from the maps and the runtime group dump |
| `experiments/results/probe_v3_0_5/` | probe outputs 3.0.4 / 3.0.5, identical-games list (80 games) |
| `experiments/results/mapintel/groups_runtime_official40.txt` | runtime groups of the 40 official maps (836 groups; duplicate lines from each body) |
| `tools/ledger.py` | engine 3.0.5 uses `ledger_v3_0_4/` (identical play) |
| `tools/setup_session.sh` | cambc 3.0.5; SDK and official maps from a scratch `cambc init`; maps go to `maps/official/` |
| `cambc.toml` | sdk_version 3.0.5 |

---

## 7. Where we left off, and how to resume (session 18b, from Oct 24 07:00 UTC: the agent carrying out the plan)

### 7.1 Status
- Steps 1-2 done (sections 3-4). Scope and source rule changed (1.7); GOD v10 may stand in for the user's bot (1.8).
- **A done**: the laptop scripts (`fetch_ladder.sh`, `run_battery.sh`); the user is running the ladder download.
- **B**: step 3 built (catalog of the 40 maps, plans 1-4, economy model; pace check vs GOD v10 Spearman 0.77); step 4 done (k = 3);
  step 8's model-free parts: fingerprint, features (tested equal), forced rosters, test bot; next: the draft-memory packer, the table
  generator, `plans.h`, and the step-6 code on the 2,580 summaries.
- **C** waits for the user's ladder archive (`mapintel_ladder_*.tar.gz`, possibly in 20 MB parts: `cat part* > archive`).

### 7.2 Checkpoints (newest last)
- **07:20 UTC**: new container: `pip install cambc==3.0.5`, wasm toolchain fetched by hand (`curl --cacert /root/.ccr/ca-bundle.crt`), `sdk/`
  copied from a scratch `cambc init`. **The platform host 2026a.battlecode.co.uk is refused by this container's proxy (HTTP 403 to CONNECT)**,
  so `cambc init` could not refresh the maps: `maps/official/` keeps the committed copy from this morning (SHA256SUMS verified). The user
  must allow the host in this environment's network settings for a refresh; the laptop scripts download from their machine anyway.
  The user uploaded 5 match groups of top teams (25 replays, engine v1_0_3 by the decoder: current patch); they go to
  `experiments/ladder_oct24/`. First commit: section 1.7, this section, AGENTS.md top bullet, `docs/HANDOFF_PROMPT_MAPANALYSIS.md` deleted.

- **07:25 UTC: 3A done (the two laptop scripts)**.
  - `tools/mapintel/fetch_ladder.sh` (+ `ladder_fetch.py`, stdlib Python): ladder -> top-50 teams' ranked match lists -> filter (both teams
    engine >= 1.0.3, official maps; platform names use `_` for the files' `-`) -> team strengths -> replay selection spread over the 40
    maps (strong vs strong first; strong = top 20 ratings; 15 per map) -> downloads (resumable, capped at 60 MB gzip) -> one archive.
    Tested: dry run on session 17's 2,580-row list (kind `unranked` there, so the default `ranked` filter correctly refuses it), and an
    end-to-end run with a fake `cambc` (archive with 120 replays). Session 17's `cli.py` / `fetch_matches.py` / `dl_replays.py` were
    reused as code (retry-on-busy wrapper, pagination, per-map download); the CLI options they use exist in 3.0.5 (`--help` checked);
    their JSON output could not be checked without a login.
  - `tools/mapintel/run_battery.sh --bot NAME` (+ `battery.py`): outcome battery (own draft vs `self,idle,starter`) and roster battery
    (both rosters forced; 8 candidates per map = LEARNED strong-team rosters + COMPUTED kit-class-balanced rosters,
    `tools/mapintel/data/battery_rosters.json` from `battery_rosters.py`; every pair, 2,240 games) through `tools/ledger.py run --release
    --keep` with `LEDGER_DIR` in the work folder. Rosters are forced by the bot under test through the library header
    `cpp/mapintel/force_roster.h` (`mapintel::forced_pick()`, keyed by the map fingerprint); the script checks every game's engine draft
    against the forced rosters. Function test with a 3.0.5 starter copy that calls `forced_pick()`: `--quick` 12 games, 0.3 MB archive,
    40 s; the check caught a real bug on the way (a `//` comment in the generated macro swallowed every second table entry).
  - Prerequisites built for it: `cpp/mapintel/fingerprint.h` (FNV-1a 64 of 5.8, team-independent; 20-142k fuel on the official maps,
    within the 1M first draft turn) and the probe bot `cpp/probe` + `dump_maps.py` -> `experiments/results/mapintel/dump/` (40 runtime
    dumps: fingerprint, team size, spawn regions, the four bitboards, groups; the groups equal the committed
    `groups_runtime_official40.txt` on all 40 maps; 40 distinct fingerprints).
  - `tools/ledger.py`: source hash now includes files in sub-folders (a bot with `src/mapintel/` made it fail); flat bots hash as before.

- **08:25 UTC: step 3 built, step 4 done; the library's features and fingerprint tested; GOD v10 battery done.**
  - Probes (7.6): every rule the geometry needs is engine-confirmed (Chebyshev ranges, nearest-champion camp targeting, sight for
    attacks but not for area spells, dash / crystal legality, dead-tile standing and the respawn hold, no camp regeneration).
  - `tools/mapintel/` (Python 3, `python3 -I`; numpy, scipy, scikit-learn, networkx installed with pip): `mapdata.py` (runtime dump ->
    arrays), `geometry.py` (BFS = the SDK's distance field, checked equal on all 40 maps; dash BFS with cooldown states, matching all 6
    probed dash cases; crystal hops), `economy.py` (per-round fight simulation: camps first, nearest champion, wake / sleep, kill order
    by strength / health, resets, spells, splash, retaliation, HoR bonus and dash landing, stuns, shields, heals, heal trips with
    shopping inside the fight; capture 6 rounds, tribute max(1, ceil(bag / 10))), `tiles.py` (per kit class: distance layers, camp
    threat, hit / safe layers for reach 1 / 3 / 4 / 5, per (champion, group) safe tiles and solo kill time / damage / trips), `plans.py`
    (plan 2: approach tiles, per-team access walk / after clearing (gate groups) / dash / crystal, bank routes, the banking cases and
    tiebreak rule; plan 3: ETAs per team and reach, gap, contested flag (scaled band), priority, first contact; plan 1: search over the
    first targets; the unopposed planner with coalitions and opportunity costs; plan 4: threshold formulas), `catalog.py` (the catalog),
    `archetypes.py`, `features.py` (runtime features v1), `validate_pace.py`, `replays.py` (ladder replays -> LEARNED summaries).
  - **Pace check against GOD v10's unopposed games** (SIMULATED v10, `experiments/results/mapintel/pace_check.csv`, the model run with the
    roster v10 drafted in each game): **Spearman 0.770 over the 80 games, 0.768 over the 40 maps** (target 0.8 not reached); median
    model / v10 0.95. The model is too slow on monolith / objective maps (contest 1.59x, rows 1.46x, stampede 1.32x) and 3-champion maps
    (gold-rush 1.34x), too fast on many-cluster maps (quadrants, yellow-brick-road, lanes 0.74-0.79x; gem-fields' v10 side B never
    finished: an outlier). The real target (top teams' rates) comes with the ladder archive (3C).
  - Plan 2 findings (COMPUTED): both teams can bank on foot on all 40 maps; boss-battle's only altar is usable only after killing the
    double monolith (its one approach tile is a monolith tile: mode walk_after_clearing, standing there holds the monolith's respawn);
    collision's second altar is crystal-only for both teams; islands has 6 dash-only altars. So the tiebreak case is "both can bank" on
    every official map.
  - **Step 4 (archetypes)**: 19 runtime features, PCA 10 components, k-means silhouette k2 0.169 / k3 0.181 / k4 0.168 / ... -> **k = 3**
    (weak structure; bootstrap ARI 0.58, p10 0.36): (0) small brawl / low-gem maps (collision, eight, elkring, fragment, gem-fields,
    gemfight, interlock, packs, reverse-spiral, rushbait-v2, elk-arena, hooks); (1) rich monolith / golem economies (contest, great-wall,
    lost-world, monolith, quadrants, road-of-riches, rows, split, swirl, big-world, boss-battle, broken-curve, corridors, fracture,
    gold-rush, shortcut, starvation, the-farm); (2) large / maze / spread maps (ambush, corners, expanse, lanes, pilgrimage, stampede,
    concentrated-wealth, islands, starfish, yellow-brick-road). HDBSCAN (min cluster 3) calls 17 of 40 outliers (40 points in 10-D are
    sparse). Strong teams' pick rates per archetype (LEARNED, opponent side of the 2,580 rows): Vesper 0.94-0.99, Heart of Ruin
    0.75-0.83, Marcella 0.63-0.83, Vendetta 0.51-0.72, Ryth 0.52-0.70. Files: `maps/catalog/archetypes.json`, `splits.json` (5 folds
    stratified by archetype).
  - **Library (step 8, model-free parts)**: `cpp/mapintel/features.h` = `features.py` (47 values, version 1) **equal on 40 maps x 2 teams
    (3,760 values) and on 11 perturbed copies**; `fingerprint.h` equal to the dump on all 40 and different on every perturbed copy.
    Fuel on the first draft turn (max over the 40 maps): fingerprint 142k, load_view 304k, features 239k (first-turn total <= 534k of
    1M); later draft turns untouched (99,984 of 100,000 left). Fuel lessons: a zero-initialised vector costs ~1.2 fuel per byte (field
    buffers are left uninitialised), host bitboard ops ~2.5k on 100x100, `distance_field::compute` 1.3-31k, `get` ~68.
  - **GOD v10 battery** (SIMULATED v10, MAPAnalysis 1.8; `experiments/results/mapintel/sim_v10/games.csv`): outcome 240 games (v10 vs
    itself 40/80, vs idle 80/80, vs starter 80/80) + roster battery 2,240 games (8 candidate rosters per map, both forced; the roster check
    passed on every game), 31 minutes here with 3 jobs. Archive 87.6 MB (kept in the scratchpad; replays not committed).
  - Decisions: (7.4) the catalog's runtime features are the features.py set (cheap, SDK-only definitions; line-of-sight, dash and
    simulation features are `ext_*`, offline only); team B's plans and pace on these mirror-symmetric maps are team A's mirrored (the
    planner has no turn order); contested thresholds scale with the map (max(3, 0.1 x spawn distance)).

### 7.3 Adaptations of the plan to the source rule (where the plan relied on GOD v10 or old data)
- 5.5 batteries: GOD v10 and its panel replaced by the user's bot (`--bot NAME`) against itself, an idle bot and the 3.0.5 starter; the
  draft battery's "dynamic draft's top-K rosters + the top teams' rosters" became the roster battery's LEARNED (top teams' current-patch
  rosters per map) + COMPUTED (kit-class-balanced) candidates; `tools/setup_session.sh --bots` (old bots) is not used: the script builds
  only the user's bot, its roster copies, an idle bot (`cpp/idle`) and the starter from a scratch `cambc init`.

### 7.4 Decisions on details the plan leaves open
- Outcome battery: the bot's own draft (its natural outcome, pace and tiebreak share); "both rosters forced" applies to the roster
  battery. Forced rosters are keyed by the map fingerprint (one compiled copy per roster slot plays all maps).
- Roster candidates: at most 4 LEARNED (most frequent strong-team rosters on the map, ties by wins), filled to 8 with COMPUTED rosters;
  a COMPUTED roster covers at least three of the four kit classes (all four would force Vesper Vale, the only ranged dash kit, into
  every roster), then the least-used champions. A team present in more than 90% of the rows (the requester's own team in match groups)
  is not counted as a strong team.
- Ladder selection: strong = the 20 best ladder ratings among the top 50; 15 replays per map; replays of strong-vs-strong games first.
- Runtime features (`features.py` = `features.h`, version 1): only quantities a bot gets in the draft from the SDK (BFS fields, bitboards,
  the camp groups and their designs); "meet" (the fronts' meeting round) was replaced by the enemy's nearest altar distance because it
  needs two full-field exports; line-of-sight layers, dash fields and simulations stay offline (`ext_*` columns).
- Economy model defaults (unfitted, step 6 fits them): retreat line 30% hp, heal at < 50% between jobs, bank at a 40-gem bag, shop trip
  at 300 unspent gold, model build Monster (damage stat) -> Jungle (health) -> Power (damage stat), gold weight 0.1 in values (0.02 in the
  pace), plan 4's drop rule w_max = 30 rounds of respawn wait.
- Plan 1: the first targets of every body are searched (each body's team-size + 1 best by solo rate; the 40 best distinct combinations by
  summed rate are played to R0 = 150 by the planner); team B = team A mirrored.

### 7.5 Deferred or dropped (scope of section 1.7)
- Step 5 simulation labels with GOD v10 and the old panel: dropped. Replaced by `tools/mapintel/run_battery.sh --bot NAME` for the user's
  new bot (outcome and roster batteries; the parameter battery does not apply to a bot without GOD's knobs).
- Step 6 contextual ES (`tools/rl/es_train.py`): deferred until the user's bot exists (needs a bot).
- Step 7 adversarial map search: dropped. Behaviour cloning into GOD's `group_score`: dropped (no bot integration); the behaviour labels from
  top-team replays are produced as model targets instead (step 6).
- Step 8 reference integration into GOD v10 (`mi_table`, `mi_model`, `mi_plans` switches): dropped. Step 9 (A/B, ship): dropped.
- The step-3 check against GOD's draft-time features (`bots/god/src/draft.cpp` FEAT lines): dropped (not an input); replaced by the test bot
  of step 8 (runtime features in the engine equal the Python values). The idle-pace validation: run against GOD v10's unopposed games
  (allowed since 1.8, SIMULATED v10) and, when the ladder archive arrives, the top teams' real gem rate and first-capture order (LEARNED).

### 7.6 Engine facts probed for this work, and tool checks on the 3.0.5 engine (code reused from `tools/`)
- **Engine rules probed on 3.0.5** (probe bots `tools/mapintel/probe_rules/rules_main.cpp`, `rules2_main.cpp` on the probe maps
  `maps/probe_mi/mi_rules.map26a`, `mi_rules2.map26a` built with the engine's MapBuilder (`rules_map.mjs`, `rules2_map.mjs`); outputs
  `experiments/results/mapintel/probe_rules/rules_probe_output.txt`, `rules2_probe_output.txt`; replays decoded with `decode.mjs`):
  - **Every range is Chebyshev**: ranged basic attack at offset (3,3) hits, (4,0) is "out of range"; melee hits at (1,1); a single-target
    spell hits at (4,4); an area spell (radius 1) hits the camps at (1,1) and (-1,-1) of its ground tile, not the one at (2,0); a wolf
    (range 3) hits a champion at (3,3) and an elk (range 4) at (4,4); tribute works from (1,1) of the altar and not from (2,2).
  - **A camp hits the nearest champion within its range**, not its attacker (the wolf Stellar attacked hit Vendetta, who was nearer).
  - **Attacks and single-target spells need the caster's own sight** (a camp behind a wall line: "Target must be a visible enemy or
    neutral camp" / "a visible unit"); **an area spell does not** (cast at an unseen ground tile behind a wall: the camp took 98).
  - **Dash** (range 2): crosses a 1-wide hole line straight and diagonally, a knight move through a hole when the other middle tile is
    a wall, and passes over an altar tile and a bush; it cannot pass walls (all middle tiles walls: "Destination is unreachable within
    movement range") or a living camp's tile (same error); it cannot land on a hole ("Forbidden landing tile"); it can land on a dead
    camp's tile (and that starts the capture: landed r27, reward r33).
  - **Teleport crystal**: range 3 over a wall line and diagonally (3,3), over holes; "Teleport out of range" at distance 4; no landing on
    a hole or an altar ("Forbidden landing tile") or a living camp ("Known occupied destination"); a refused use does not consume the
    crystal; used in round r, it lands at the start of round r + 3. Landing on a dead camp's tile is not tested (the camp had respawned).
  - **A dead camp's tile can be stood on**; capture: on the tile in round r, reward in round r + 6; **standing on the tile holds the
    respawn**: the gem cluster's timer reached 0 at r66 and it respawned at r89, the round after the body stepped off (r88).
  - **Camps do not regenerate**: a wolf left at 1200 of 1350 and an elk at 2260 of 2400 kept that health to r450.
  - Tribute of 7 gems: started r98, banked by r99. A melee body (Ryth, 45) kills a 120-hp cluster in 3 hits.
  - Hypothetical vision (`visible_tiles_from`) is refused during the draft ("Initialize the game before inspecting runtime state") and
    costs ~1.1k fuel in a game turn: the line-of-sight table (`dump/*.los.txt`, engine vision from every standing tile within Chebyshev
    5 of a camp) is computed by `cpp/probe/los_main.cpp` in the first game turns; `dump/*.vis.txt` holds the full vision of 60 sample
    tiles per map.

- `tools/replay/decode.mjs`: decodes the uploaded ladder replays with `v1_0_3-DRqNt1t2.wasm` (the newest in the cambc asset cache; meta.engine
  records it). Checked on the rules probes: its Move / Attack / Cast / CaptureGems events and camp health per round agree with what the
  probe bot printed (wolf 1350 -> 1200 in five Stellar hits; the gem cluster's capture at r16 and respawn at r89). Its camp-type list has
  no golem (it prints the number 5): handled by the readers.
- `tools/mapgen/engine.mjs` (MapBuilder): builds the probe maps; their runtime dumps equal the layout written (mapdata.py prints them).
- `tools/strategy_v2/s13/stdout.mjs`: extracts team stdout from run bundles (used for the probes); dump_maps.py reads the zip directly.

### 7.7 Resume in a new container
```bash
cd Cambridge_Battlecode && git pull --no-rebase origin main
pip install cambc==3.0.5 numpy scipy scikit-learn networkx      # (+ lightgbm shap for step 6)
S=$(mktemp -d) && (cd $S && cambc init --yes .)   # writes sdk/, cmake/ and bots/starter-cpp; toolchain download may fail TLS (next line)
# toolchain by hand: the first half of tools/setup_session.sh (wasi-sdk-33, cmake 3.31.8, ninja 1.12.1 into /root/.cache/cambc/,
# curl --cacert /root/.ccr/ca-bundle.crt); do NOT run the rest of that script (it rebuilds the old bots)
rm -rf sdk cmake && cp -r $S/sdk sdk && cp -r $S/cmake cmake
python3 -I tools/mapintel/dump_maps.py --los --vision     # runtime dumps (already committed; ~30 s)
python3 -I tools/mapintel/test_library.py                 # library tests (all checks passed on Oct 24)
python3 -I tools/mapintel/catalog.py                      # the catalog (~25 min on 4 CPUs); --csv-only rebuilds maps.csv
python3 -I tools/mapintel/archetypes.py                   # archetypes + splits
python3 tools/mapintel/battery.py --bot _mi_v10 --from god --jobs 3   # GOD v10 batteries (~31 min here)
python3 -I tools/mapintel/validate_pace.py WORK            # the pace check on a battery work folder
python3 -I tools/mapintel/replays.py DIR... --out experiments/results/mapintel/ladder   # decode + summarise ladder replays
```
