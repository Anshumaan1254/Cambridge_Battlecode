# AGENTS.md: handoff context for AI agents (and humans)

Read this first. It records what has been done on this bot, what was measured, what failed, what is
running or unfinished, and what to do next, so a new agent can continue without the original chat.

- Last updated: **2026-10-20 12:50 UTC (session 15, parallel: the sprint documents; read §S15 and §S14 first, then §S13-GOD, §S13)**.
  Rule from the user: update this file and push at every step. Start with **§S14**, then **§S13-GOD**, **§S13**, then **§S12**, then §S7R (m11-m14), §S11, §S10, §S9, §S8,
  §S7, §S7-SV2, then §000000 (resume protocol). **The repository now has a single branch, `main`** (the user merged every branch into it
  on Oct 19 and said "the ccr-a858cd03-q87cpi is no more so do the changes in main branch"): commit and push to `main`; `git pull` (merge,
  never force) before every push. No PR unless the user asks.
- Competition: Cambridge Battlecode 2026a (CAMBC), 12 Oct to 18 Nov 2026. C++ bot compiled to wasm.
- The submitted bot cannot be changed after submission and keeps nothing between matches. All "learning"
  is either offline (training parameters before submission) or in-match (adapting inside one game).

---

## S15. SPRINT DOCUMENTS (2026-10-20 12:20 UTC, a parallel session in the session-12 container): read with §S14

- **Input**: the user's `GameRules.md` and `BotAPICpp.md`, "the new documents for this sprint" (now `docs/sprint/`; analysis
  `docs/sprint/RULES_DIFF.md`). **GameRules.md is the pre-patch game** (no Heart of Ruin, no Golem, wolf 22 gems / 90 gold, gem cluster 500 hp /
  24 gems, kills 50 gold, monsters range 3, altar lock 3 hits, wards every round, the old champion numbers). **BotAPICpp.md is mixed**: its
  functions are the 3.0 SDK's (`vision::awake_camp_tiles`, no `dash_range`), its enums / structs the pre-patch ones (no `heart_of_ruin`, no
  `golem`, `ability_dash` with only `range`). The Oct 20 ladder games were played on 3.0 (Heart of Ruin in the drafts), so the handbook may be
  stale, or the sprint runs the old balance: unknown from here (platform blocked). **Rule from now on: every submission must compile on both.**
- **GOD v5 does not compile on that API** (16 `heart_of_ruin`, 1 `camp_type::golem`, `ability_dash::modifier / radius`); legend_m15 compiles on
  2.2.5 and 3.0.1. Fix: `experiments/wip/x_sdkcompat.patch` (on `bots/god`): `common.h` `SDK_HAS_HOR`, `CT_HOR`, `D_HOR`, `CAMP_GOLEM` through
  `requires`-expressions, the dash fields under `if constexpr (requires ...)`, the draft's pick order and `pd_hor3` only with Heart of Ruin.
  **`bots/_god_c` = GOD v5 + that patch: wasm byte-identical to GOD v5 on 3.0.1 (sha256 47cd9ae8…), compiles on 2.2.5.** Scratch projects for both
  SDKs: `cambc` 3.0.1 unpacked from its wheel (`pip download cambc==3.0.1 --no-deps`, the binary is `cambc-3.0.1.data/scripts/cambc`; `cambc init`
  writes its `sdk/`), the installed CLI here is 2.2.5. `tools/sdk_apidiff.py DOC OLD_H NEW_H` lists API names missing from either header.
- **Measured under the documents' rules** (2.2.5 engine, `maps/comp`, 34 games per cell, ledger `experiments/results/ledger/`): legend_m15 vs the five
  proxies 149/170; GOD v5 (`_god_c`) 127/170, h2h 13/34; GOD with `gold_value` 0.22 + `burst_retreat` 0 (`_gc_old`) 133/170, h2h **19/34**; gold only
  (`_gc_gv`) h2h 19/34, burst only (`_gc_br`) 14/34. `bots/_god_d` = `_god_c` with `gold_value = SDK_HAS_HOR ? 0.33f : 0.22f`, `burst_retreat =
  SDK_HAS_HOR ? 1.2f : 0.f`: **wasm identical to GOD v5 on 3.0.1 and to `_gc_old` on 2.2.5.** Running (`$S/q_sprint3.sh`): which other GOD switch
  costs the 16 proxy wins under the old rules (`_go_all0` all GOD-only switches off, `_go_ac0` altar_no_camp 0, `_go_dg0` dash_gain1 0, `_go_sg0`
  stall_guard 0, `_go_oh0` pd_obj_heavy 0; all on `_gc_old`).

## S14. HANDOFF (2026-10-20 10:40 UTC, end of session 13): the next agent starts here

### S14.1 The task you inherit (the user's words, in priority order; the prompt the user was given for you: `docs/HANDOFF_PROMPT_S14.md`)
1. **"We are losing every time on the new maps."** The user uploaded two match zips of the best opponent right now, **Nyx**, vs our GOD
   bot: `new_maps_us_vs_nyx.zip` (patch-3.0 maps nobody had seen) and `old_maps_us_vs_nyx.zip` (the official maps as changed by the patch).
   Request: study the new maps, develop the strategy and drafting, **reverse-engineer Nyx's good strategies**, analyse the old maps too, and
   **make a new GOD that is better. Do it first.** Also: "check new maps from the SDK or cambc and download them" (blocked here, S14.4).
2. Patch 3.0 (Oct 20 patch notes, text in `docs/patch_notes/week2_20261020.txt`, summary in §S13-GOD): the bot must use every change
   (re-balanced champions, re-valued camps, Golem, Heart of Ruin, changed maps) and be "the best of its kind". **The bot's name and level is GOD.**
3. Still open from earlier: "legend m15 is still losing to Mite and Nyx: fix it" (§S13, last checkpoint). GOD is the answer now; Mite has
   not been seen since the patch.

### S14.2 The user's working rules (all still in force)
- **Agents (new rule, end of session 13): few subagents, few parallel background tasks. Fable subagents for the main / heavy tasks,
  Opus for the tasks below that, then Sonnet, then Haiku for the smallest (documentation, file moves).** Do the core reasoning yourself.
- Single branch `main`: commit and push at every step (`git pull --no-rebase` before each push, never force); no PR unless asked.
  Keep this file updated at every step (a checkpoint bullet in §S14.7 with the time, what ran, what it showed, what runs now).
- **No hardcoded map strategy**: every plan and draft choice must come from map features computed at runtime (the final sprint changes the
  map pool again). Report anything hardcoded in `ISSUES.md`; strategies that should work but did not measure better go in `SUGGESTIONS.md`.
- Loopholes, exploits and reverse engineering are allowed. Ship a new zip only when it is measured better; push the zip first, then continue.
- The four PDFs in the session-13 upload are personal documents: never use or commit them. Never `pkill -f` / `killall` (kill by PID).
- The user answers slowly and is often away: do not stop to ask; decide, record the decision here, continue.

### S14.3 What is shipped and which bot played Nyx
- **`submissions/god.zip` = GOD v2** (sha256 f1a13eef…; source `bots/god` = frozen `bots/_g4`, hash 19a1785457d3; history
  `submissions/history/god_v2_20261020.zip`). This is the patch-3.0 build to upload. `submissions/legend.zip` = `legend_m15` (pre-patch tuning;
  it still compiles on 3.0.1). GOD v2 = m15 + Heart of Ruin in builds, golem in the map analysis, engine camp ranges (elk 4, golem 4,
  monolith 5) in danger / ring / kite plans, damaging-dash handling, `pd_hor3` (Heart of Ruin instead of C&I at team size 3), `gold_value` 0.33.
- The Nyx games were played by a GOD build (our 3-champion drafts are Ren, Stellar, Heart of Ruin = `pd_hor3`).
- Camp rewards are read from the engine at runtime (`world.cpp`: `g.gem_value()`, camp stats), so the new values are already used.

### S14.4 Environment (new container) and data
- Setup: `tools/setup_session.sh` (now installs **cambc 3.0.1**, the toolchain, and rebuilds every sparring bot plus `_mlkc40` = legend_m15
  exactly (hash 8eb9563d0d5b, via `experiments/wip/m15zip_to_mlkc40.patch`) and `_g4` / `god` = GOD v2 (19a1785457d3)). The proxies `_mite`,
  `_ifish`, `_px9`, `_snk`, `_fA` compile on 3.0.1 unchanged. Ledger rows for cambc >= 3 go to `experiments/results/ledger_v3/` (per engine).
- **`cambc maps pull` is blocked** (proxy 403 on 2026a.battlecode.co.uk), so the official patch-3.0 map pool cannot be downloaded here. Tell the
  user once: allow that domain in the environment's network settings, or upload the maps (`cambc maps pull` on their machine, zip `maps/`).
  Until then the maps come from replays (`tools/replay/extract_map.mjs --dir REPLAY_DIR OUT_DIR PREFIX`).
- Replays decode with the newest engine in the cambc asset cache (`v1_0_0` for patch 3.0); in a fresh container run `cambc view <replay>` once
  if `~/.cache/cambc/assets/*/visualiser/assets/v1_0_0-*.wasm` is missing. `CAMBC_ENGINE_WASM` forces one engine. (A zero-byte stray file in
  the upload looked like an engine error; `decode.mjs` now says "empty replay file".)
- **Data from this upload** (committed):
  - `experiments/nyx_oct20/new/` and `old/`: 20 replays `<group>_<nn>_A.repl26a` (we are side A in all), `index.json` per folder.
    Groups: new maps 0308edc9, b6be1477; old maps 7162f242, 0e08cb72.
  - `maps/nyx_new/`: the 10 new maps (names `nx<W>x<H>_<sym>_c<champions>_<hash>`).
  - `maps/comp30/`: the patch-3.0 versions of 10 official maps, named `<map>_v3` (ambush, collision, contest, corners, eight, elkring,
    expanse, fragment, interlock, lanes). **The official maps changed**: more gold and gem clusters (contest 16 gold clusters per side instead
    of 10, lanes 18 + 6 gem clusters, elkring 5 gem clusters added), expanse now has **5** champions per team (was 3). The other 7 official
    maps (monolith, packs, pilgrimage, rows, rushbait-v2, stampede, swirl) are not available in their 3.0 form; `maps/comp/` holds the old files.
  - `maps/p30/`, `maps/p30g/`: my synthetic patch-style copies (gem clusters added, golems): useful, but not the real pool.
- **Ledger gotcha fixed**: rows are keyed by map file name only. The first `comp30` run reused `maps/comp` rows of the same names; the maps are
  now `*_v3` and `tools/ledger.py run` refuses a pool whose names belong to two different files under `maps/`. Keep every map name unique.
- Session-13 scratch tools are now in `tools/strategy_v2/s13/` (README there): `idx.mjs` (index a replay folder), `nyxsum.py` (per-game
  side summary of decoded games), `window.mjs` / `track.mjs` / `pos.mjs` (fight and movement traces), `farmstat.mjs`, `respawn_ctx.mjs`,
  `caps.mjs`, `deaths.mjs`, `poolcell.py`, queue examples.

### S14.5 What the Nyx games show (decoded with `nyxsum.py`; "us" first)
New maps (Nyx won 9 of 10):

| Map (`maps/nyx_new`) | Ch | Result (round) | Our draft / Nyx draft | Deaths | First capture | Captures (us / them) |
|---|---|---|---|---|---|---|
| nx60x60_R_c5_0cdefa | 5 | 115-1000 (r757) | ours meta / Ren, Stellar, C&I, Ryth, Varg | 6-0 | r136 / r46 | wolf 5, elk 2 / elk 8, gem 13, gold 8 |
| nx31x31_R_c4_9e9a40 | 4 | **0-1012** (r1466) | Ren, Stellar, C&I, Ryth (both) | **45-22** | none / r177 | nothing / elk 36, gem 13 |
| nx31x31_R_c3_142ce0 | 3 | **WIN 1174-286** | Ren, Stellar, HoR / Varg, Stellar, C&I | 9-40 | r56 / r27 | similar |
| nx61x71_R_c5_d26c0c | 5 | 893-1016 (r1423) | meta / meta | 9-15 | r47 / r30 | 43 / 76 groups |
| nx50x50_R_c5_3a3eb5 | 5 | **72-1008** | **Prism, Stellar, C&I, Ryth, Tavi** (objective draft) / meta | **39-5** | r353 / r170 | gem 1 / gem 13, elk 2 |
| nx100x100_R_c5_bbb066 | 5 | 582-1032 (r1084) | meta / Varg, Vendetta, C&I, Willow, Ryth | 9-2 | r26 / r50 | 30 / 52 |
| nx50x41_V_c5_86f1cb | 5 | **0-0 at r2000** (lost on gold earned) | meta / Varg, Vendetta, C&I, Willow, Ryth | 10-24 | r39 / r44 | gold 17 / gold 84, elk 62, wolf 43 (1 altar) |
| nx40x40_R_c3_b9da0c | 3 | 951-1012 (r1172) | Ren, Stellar, HoR / Ren, Stellar, C&I | 9-15 | r138 / r32 | 31 / 62 |
| nx61x61_R_c5_15b37f | 5 | 274-1034 | meta / meta | **21-4** | r52 / r42 | 22 / 62 |
| nx51x40_V_c5_ec2893 | 5 | 136-1049 | meta / meta | 15-11 | r58 / r64 | 9 / 42 |

Old maps (patch-3.0 versions, `maps/comp30`; Nyx won 8 of 10): elkring 638-1012 (deaths 13-10), **expanse WIN 1010-883**, **fragment 74-1012**
(Ren, Stellar, HoR vs Ren, Stellar, C&I; first capture r171 vs r18; we took 10 wolves, they 85 groups), interlock 297-1026 (16-9), lanes
593-1012, ambush 738-1011, **collision 373-1019** (HoR draft again), **contest 0-400 at r2000** (deaths 54-28; Nyx took the monolith twice
from r1707; we never captured anything), corners 571-1012, **eight WIN 1016-311** (vs Varg, Vendetta, C&I, Willow, Ryth; deaths 22-42).

What this says:
- **Nyx drafts the old meta**: Ren, Stellar, C&I, Ryth, Varg (5), Ren, Stellar, C&I, Ryth (4), Ren, Stellar, C&I (3) on 16 of 20 maps; on
  nx100x100, nx50x41 and eight it drafted Varg, Vendetta, C&I, Willow, Ryth (a map-dependent table, or a second team in the same group).
  **On 5-champion maps our draft is the same five champions, and we still lose by 300-1000 gems: the gap is execution and economy, not the draft.**
- **Economy**: they capture 1.5-5x more groups, mostly **elks and gem clusters** (gem cluster = 7 gems for 120 HP: the cheapest gems after the
  patch; a wolf is 4 gems), and start earlier (fragment_v3 r18 vs our r171, nx40x40 r32 vs r138, nx60x60 r46 vs r136, interlock_v3 r23 vs r80). We take wolves (worst gems per HP now).
- **Activity**: their attack steps are 1.2-2.9x ours, shop actions 1.2-6x (nx31x31_c4 156 vs 25, nx50x50 199 vs 35, nx50x41 473 vs 80),
  recalls usually 1.3-2.6x (nx50x50 105 vs 6). We place 3-10x more wards (one per 10-round cooldown on every body: check what it costs us).
- **Death cascades** on four maps (45, 39, 54, 21 deaths); on small maps (31x31 c4) we never captured anything in 1,466 rounds.
- **Two games went to r2000 and were decided on gold earned** (contest_v3 0-400 was gems; nx50x41 0-0 on gold): the tiebreak matters more now.
- **Our objective plan misfired** on nx50x50 (27 gold clusters, 3 gem clusters, 1 elk per side): it drafted the stampede casters and lost 72-1008.
- **`pd_hor3` (Heart of Ruin at team size 3) is not proven**: 1 win (nx31x31_c3), 1 close loss, 2 blowouts (fragment_v3, collision_v3) against
  Nyx's Ren, Stellar, C&I. Locally it scored 20-23/24 vs 19 on the old fragment / packs files only.

### S14.6 Local baseline on these 20 maps (ledger_v3; both sides; GOD v2 = `god`)
| Bot (wins of 20 per pool) | vs `_mite` new / v3 | vs `_ifish` | vs `_px9` | vs `_mlkc40` | unopposed pace new / v3 |
|---|---|---|---|---|---|
| GOD v2 (`god`) | 18 / 16 | 15 / 16 | 13 / 17 | 15 / 14 | 1234 / 998 rounds |
| legend_m15 (`_mlkc40`) | 14 / 19 | 15 / 17 | 12 / 12 | - | - |

(`python3 tools/strategy_v2/s13/poolcell.py god _mite _ifish _px9 _mlkc40 idle --pool maps/nyx_new --pool maps/comp30 [--maps]`.)
Deaths are 20-30 per game per side in these local games (pre-patch ~7): after the patch our code family brawls.
**Nyx's contested finish beats GOD's unopposed pace** on nx60x60 (Nyx r757 with us on the map; GOD alone r943 / r1026), nx100x100 (r1084 vs
1182 / 1237) and roughly ties on nx51x40 and nx61x61: on those maps our farming route itself is slower than theirs. On the old maps (elkring,
corners, interlock, lanes, collision, fragment) GOD alone is faster than Nyx's finish, so the losses there come from contact (fights, deaths,
lost bags, denied camps). **nx50x41: GOD alone banks nothing in 2,000 rounds** (both sides 0-0, like the Nyx game): its only altar (25,20)
sits in a wall line behind two monolith tiles and holes (`node tools/replay/mapinfo.mjs maps/nyx_new/nx50x41_V_c5_86f1cb.map26a`), so the
game is decided on gold earned, then kills. Open questions for that map: the tribute range, whether a dead monolith tile can be stood on
(then killing the monolith opens the altar), whether a teleport crystal reaches a tile next to it. Either way the bot must detect "no
reachable altar" from the map and switch to the gold / kill tiebreak.
Locally GOD beats every proxy on these maps while Nyx beats it 17 of 20: **our proxies are our own code family and do not play like Nyx.**
A Nyx-like sparring partner is the first thing to build (S14.7 step 2).

### S14.7 Plan for the next agent (my recommendation, in order)
1. **Trace the blowouts** (no games needed): `node tools/strategy_v2/s13/window.mjs REPLAY FROM TO` and `track.mjs` on
   new/0308edc9_02 (31x31 c4, 0-1012), new/0308edc9_01 (60x60, first capture r136 vs r46), new/b6be1477_04 (61x61, deaths 21-4),
   old/0e08cb72_03 (fragment_v3, HoR); r0-250: where each Nyx body goes, which groups it takes in which order, who fights where, when they shop
   and recall; then the same for us. Write the findings to `docs/strategy_v2/14_NYX_PATCH3.md`.
2. **A Nyx proxy** built from what step 1 finds (draft table by team size, opening route to elks / gem clusters, shop and recall cadence), or an
   ES exploiter trained against GOD on `maps/nyx_new` + `maps/comp30` (`ES_SRC=bots/god`, `tools/rl/es_train.py`), so local screens mean something.
3. **Economy for patch 3.0**: re-check `group_score` against the new values (gem clusters cheap, wolves poor, elk range 4); first capture by
   r30-50; take neutral elks / gem clusters like Nyx; re-take respawns faster; gold-earned tiebreak awareness near r2000 (kills now pay 100).
4. **Map-derived special cases**: no reachable altar (nx50x41: play for gold earned and kills); fix the objective-plan misfire (nx50x50): the detector must not fire when the "objective" is small after the patch; check
   `derive_params` / `pd_score` on every new map (print our draft per map locally).
5. **Draft**: drop or gate `pd_hor3` (HoR lost twice to Ren, Stellar, C&I); consider Nyx's choices; screen on the 20 maps vs the new proxy.
6. Ship GOD v3 when it beats GOD v2 head-to-head on `maps/nyx_new` + `maps/comp30` and the proxies (and the new Nyx proxy), pace not worse;
   zip to `submissions/god.zip`, history, BUILDS row; push first, then continue.

### S14.9 Session 14 findings (10:10-11:30 UTC, this container): what Nyx does better, measured on the 20 games

Tools: `tools/strategy_v2/run_all.py` on the 4 group zips (`analyze.py` now has the patch-3.0 champion stats + Heart of Ruin), output in
`experiments/nyx_oct20/analysis/` (report.md, CSVs); `tools/strategy_v2/stuck_eps.py DMG_DIR [team]` (stall episodes), `killers.py DMG_DIR`
(bodies and rounds per camp-group kill, both teams); the top-level `experiments/nyx_oct20/index.json` maps every game to its map file name.
- **Economy x2.3**: camp gems 10,740 vs 24,203; gold earned 86,615 vs 237,299; captures 492 vs 1,160; camp time 15.5% vs 20.5% of alive
  rounds; camp damage per camp round 89 vs 144; idle 8.3% vs 3.3% of body-rounds. Camp-group kills (first hit to kill, `killers.py`): 2 gold
  clusters 149 of ours (13.9 rounds) vs 538 (8.1); 4 gold 25 vs 101; 1gold+1wolf 61 (211 rounds) vs 163 (84); 1elk+1gem 23 (167) vs 66 (116);
  2elk+2gold 8 vs 42 (72). Same bodies per kill (1.2-3.5): the gap is damage and commitment, not team size.
- **Builds**: Nyx buys **Treasure first on every body** (Stellar / Cassi TfE at r46-180, Ren ThE, Issac TsE, Varg ThE), then Jungle in the
  damage stat (casters) or Bruiser health (melee), then Durability, then **Power in the damage stat for the rest of the game** (1,097 Power-dmg
  emblems in 20 games; their Stellar ends with 20-27 Power emblems = 1,500+ focus, 3,000-damage casts). Damage points per 1,000 gold 33.6 vs
  21.6; their first emblems come 100-300 rounds before ours (Cassi r140 vs r641, Stellar r138 vs r435).
- **Recalls**: 1,752 vs 1,136, started at 0.70 health (ours 0.42), 788 overlapping a capture (ours 341).
- **Deaths**: 333 vs 271; 51% of ours are bursts from >= 60% health; their Stellar killed 79 of our bodies, Cassi 49 (ranged 49% of our deaths).
- **Three hard stalls decided three games** (`stalls_us.txt`; both reproduce locally with `_g4`):
  1. `nx50x41` (one altar inside a wall box; its only non-hole neighbour is a monolith's spawn tile): `altar_approach` includes camp tiles, so all
     six bodies stood next to the sleeping monolith for 1,000+ rounds in a sticky tribute trip (the step onto the camp tile is blocked every
     turn): 0-0 at r2000, lost on gold 9,262 vs 56,770. `_m15` and `_g4` stall the same way locally (both sides 0-0).
  2. `nx61x71`: Ren stood at (41,25)/(42,24) for 1,197 rounds with a bag in a tribute trip. Traced locally (LEGEND_TRACE build): the altar field
     is built with `dash_walls` (1-wide hole crossings count as ground); here two crossing holes are chained diagonally, so the field's path
     goes hole -> hole, the dash can only land one field step closer (`try_dash` needs 2) and every walking step that improves is a hole:
     `step_field` waits for a dash that never comes (`dash_wait_max`), forever. Issac stalled on the same tile later.
  3. `nx60x60` (878 holes): Ren and Issac oscillated between three tiles for ~400 rounds (same mechanism, in a maze).
- Unopposed `_g4` pace on the 20 maps: mean 1,116 rounds; Nyx's contested finishes 757-1,534: our farming alone is not slower on most maps;
  the losses are contact (bursts from range), the damage snowball (Power stacks) and the stalls.
- Draft: `pd_hor3` loses (3 of 4 Heart-of-Ruin games lost; `_g4` also loses both nx31x31_c3 games to `_m15`'s C&I draft); the objective
  draft fires on nx50x50 (one gem group + any multi-camp group) without a heavy group: Prism / Tavi there = 72-1008.

### S14.8 Checkpoints (newest last)
- **11:30 UTC (session 14)**: container set up (3.0.1), the user's two Nyx zips decoded and analysed (S14.9), the handoff's data layout kept
  (my duplicate map / replay names removed; `_g4` ledger rows renamed to `nx*` / `*_v3`), baselines: `_g4` vs `_m15` 29/40, vs the 5 proxies
  164/200, vs idle 40/40 (`experiments/results/ledger_v3/_g4_vs_*`). Working copy `bots/_x_g5` = `bots/god`; next: switches for the altar /
  no-altar mode, the dash-hole stall, `pd_hor3` 0, objective draft only for heavy groups, Nyx builds (`build_style` 12), gold value; A/B on the
  20 maps (h2h vs `_g4`, then the proxies).
- **12:20 UTC**: `bots/_x_g5` = `bots/god` + `experiments/wip/x_g5.patch` (rebuild: `cp -r bots/god bots/_x_g5 && cd bots/_x_g5 && patch -p1
  < ../../experiments/wip/x_g5.patch`; control plays GOD v2's games: 6/6 identical vs `_mite`). Switches (all off = v2): `altar_no_camp`
  (altar approach tiles never on camp tiles; `World::no_altar` when none is left) + `no_altar_gold` (gems worth 0, no tribute trips, full
  gold value), `dash_gain1` + `stall_guard` 10 / `stall_dash_off` 150 (a stalled walking task of any kind drops its target; a dash kit routes
  without hole crossings for a while), `pd_obj_heavy` (draft objective only for a heavy lone gem group), `build_style` 12 (Nyx: Treasure,
  Jungle / Bruiser, Durability, then Power dmg forever), 13 (Treasure, our style-2 survival emblems, then Power dmg), 14 (13 without Treasure).
  **H2h vs `_g4` on the 20 maps (40 games)**: `_g5a` (altar + no-altar gold) **23**, `_g5n` (dash + stall guard) **24**, `_g5all` (everything
  with builds 12) 21, `_g5b` (builds 12 alone) **16**, `_g5d` (`pd_hor3` 0 + `pd_obj_heavy`) 18. Local checks: `_g5n` on nx61x71 no stall;
  `_g5a` on nx50x41 earns 44,035 gold vs `_m15`'s 2,994 (deaths 7-36) but `_m15` banked 80 gems there: **the altar opens when the monolith
  on its only approach tile is dead** (a dead camp tile is standable), so the unlock plan (kill the 40k-HP double monolith late, hold the
  tile, bank from it) is the real win condition on that map (not built yet). Nyx's builds lose inside our brain (as every top-team build
  did before): traced corners_v3 (120-1003): an even brawl at r146-156 on our half went 4 deaths to 2 before anyone had an emblem, then kill
  gold (100 each) snowballed. Running `q2.sh`: `_g5and` (a + n + obj heavy), `_g5b13`, `_g5b14`, `_g5r` (`home_hp` 0.6, `cap_recall_hp` 0.7:
  Nyx recalls at 0.70 health), `_g5d1` (`pd_hor3` 0), `_g5d2` h2h vs `_g4`, then `_g5and` vs `_m15` + 3 proxies.
- **13:05 UTC: SHIPPED GOD v3** = `_g5and` (`submissions/god.zip` sha256 f71c8b74…, history `god_v3_20261020.zip`, `bots/god/src` = it, source
  hash 287d8b286527; BUILDS row). H2h vs `_g4` **25/40** (deaths 678-748), vs `_m15` 27/40 (v2 29), `_mite` 35 (34), `_ifish` 31 (31), `_px9` 30
  (30), 0 faults. Rejected (SUGGESTIONS.md): builds 12 / 13 / 14 (16 / 19 / 18 of 40), earlier recalls `_g5r` 15, `pd_hor3` 0 (`_g5d1`) 18,
  `pd_obj_heavy` alone 19 (kept in v3 as the principled fix). Running `q3.sh`: `_g5u` (`altar_no_camp` 2: the camp-blocked altar opens when the
  camp dies, the blocking group is a team unlock target), `_g5ex` (`elk_exposure`), `_g5gv5` / `_g5gv2` (`gold_value` 0.5 / 0.22) h2h vs
  `_g4`; `_g5and` vs idle (pace). Next levers: the fights on our own half when Nyx opens (80 deaths to 10), the economy snowball.
- **13:20 UTC**: **`altar_no_camp` 2 works**: `_g5u` (= v3 switches with mode 2) wins nx50x41 **1092-0 and 1054-0 vs `_g4`** (and 1013-0 at r679
  vs `_m15` locally: Ryth captured the 400-gem double monolith at r616, the team banked 604 + 91 + 318 from its tile); h2h vs `_g4` 25/40
  (deaths 708-692). Queued (`q4.sh`): `_g5u` vs `_m15` + 3 proxies + idle, then farming-commitment variants `_g5ch3` (`commit_hit` 3),
  `_g5mt8` (`max_trips` 8), `_g5jr2` (`join_reach` 2.0) vs idle and `_g4`. A Fable subagent retrains the danger model on the Nyx games
  (`bots/_x_ml4`, `experiments/wip/x_ml4_NOTES.md`, variants `_g5ml`, `_g5ml30`). Candidate for the next ship: `_g5u`.
- **13:40 UTC: SHIPPED GOD v4** = `_g5u` (`submissions/god.zip` sha256 db10fc92…, history `god_v4_20261020.zip`, `bots/god/src` = it; BUILDS row):
  h2h vs `_g4` 25/40, vs `_m15` **30/40**, `_mite` 35, `_ifish` 31, `_px9` 30, idle 40/40 (pace 1034.4), 0 faults. Rejected on top of v3:
  `elk_exposure` 21/40, `gold_value` 0.5 / 0.22: 19 / 22 (0.33 stays). Running `q4.sh` rest: `_g5ch3` / `_g5mt8` / `_g5jr2` (commitment)
  vs idle and `_g4`. Next: `mono_team` (team plan for lone monoliths on any map: 7 of the 20 maps have one; Nyx killed contest_v3's twice),
  `burst_retreat` 1.2, the ML retrain (agent).
- **14:00 UTC**: commitment variants on v4: `commit_hit` 3 22/40 (pace 1042), `max_trips` 8 25/40 (pace 1074), `join_reach` 2.0 22/40 (pace
  1064): none better than v4 (25, pace 1034). Docs: `docs/strategy_v2/14_NYX_PATCH3.md` (the analysis and the measured table), ISSUES.md
  #17-20, SUGGESTIONS.md session-14 table. Running `q5.sh`: `_g5mo` (`mono_team`), `_g5br` (`burst_retreat` 1.2) h2h; `_g5mo` vs `_m15`.
- 10:40 UTC: handoff written. Nothing left running (the baseline of S14.6 finished; the checkpoint loop of session 13 stops with the container).
  Also measured before the handoff: `_g4fm` (GOD v2 + `fight_margin` 1.15) h2h vs GOD v2 10/34 on the old official files: rejected.
  Untested queue from session 13 (cheap to resume, all on `bots/god`): `ml2_leave`/`ml2_flee` 0.5 and 0.3, `tribute_min` 30 (games are
  longer and bags smaller after the patch), draft without `pd_hor3` (`pd_hor3=0`).
- **SHIPPED GOD v5 (container clock 11:10 UTC; the S14.8 labels above ran ahead of the container clock, from here on they are its UTC)** =
  `_g5br` = v4 + `burst_retreat` 1.2 (`submissions/god.zip` sha256 f6d456bf…, history `god_v5_20261020.zip`, source hash 8cb539b26681, `bots/god/src` = it,
  wasm byte-identical; BUILDS row, README): h2h vs `_g4` **27/40** (deaths 654-727), vs `_m15` 29/40, `_mite` 38, `_ifish` 33, `_px9` 32, pace 1039.6, 0 faults.
  Thresholds: `burst_retreat` 1.0 (`_g5br10`) 26/40; 1.5 and + `lock_hits_sdk` running (q6). `mid_risk` 15 / 30 (`_g5mr`, `_g5mr30`: a round cost on
  midline groups before r200 on top of `_g5br`) 22 / 24: rejected (SUGGESTIONS). The q6 / ES queue scripts had waited on PID 1 (a wrong PID
  substitution): restarted; ES (`tune_out/es_nyx`, 8 gens) is chained after q6. **New input (11:08 UTC)**: the user's `our_losses.zip` = 5 match groups,
  25 games of GOD v3 vs top teams, lost badly, some to teams the earlier bot beat; the user: analyse, fix, make the draft dynamic (map, resources,
  strategy, enemy picks), nothing hardcoded. Replays `experiments/losses_oct20/raw/` (we are side A), decode `experiments/losses_oct20/an/`.
- **11:40 UTC: the 25 losses decoded** (`experiments/losses_oct20/index.json`, `an/report.md`, `an/out/*.csv`; tool `tools/strategy_v2/game_index.py`;
  16 distinct maps, one new: `maps/loss_oct20/ls50x50_R_c5_56fe6f.map26a`; the pool for every A/B is now the 21 maps = `maps/nyx_new` + `maps/comp30` +
  `maps/loss_oct20`, 42 games). Five opponents: 38998622 (Ren, Stellar, C&I, Ryth, Varg; 1 real win + 2 tiebreak wins of 5), b6bdb9e4 (HoR, Ren, Varg,
  Ryth, Marcella / Stellar; 0/5), c47c8c26 (Prism, Stellar, C&I, Marcella, HoR; 2/5), e6475502 (Vesper, C&I, Varg, Vendetta, Stellar / Stellar, Ren, C&I,
  HoR, Varg; 0/5), f8a4f886 (HoR, Ren, Stellar, Ryth, Varg; 1/5). Totals: deaths 455-222, camp gems 19.5k-28.7k, gold 168k-250k, captures 784-1,246.
  **All five stack Power in the damage stat** (950 Power-dmg + 178 Power-off emblems; damage points 6,542 vs our 2,739; c47c8c26 buys Power first:
  PfE DhE PfE PfE; f8a4f886 Treasure, Jungle, Bruiser-hp, Durability, then Power; b6bdb9e4 Jungle-dmg, Bruiser-hp, Durability, Power). Their gold is
  spread (top-1 share 0.29-0.33, ours 0.35-0.55: Ren), their Stellar's first emblem r130-268 (ours r208-661), their Stellar earns 1,080-2,718 gold a game
  (ours 442-544). **Fights on our own half when they open: 221 fights, our deaths 121 to their 7** (when we open, 49-73 in our favour): the opener
  wins, and their Power makes the opener lethal. 93 of our deaths (20%) are by camps, 66 with no enemy within 6, median health 7% four rounds
  before (Cassi 22, Issac 22, Stellar 20; eight_v3 13, ambush_v3 11): agent `cd` (Opus) traces and fixes them (`bots/_x_cd`, notes
  `experiments/wip/x_cd_NOTES.md`, patch `x_cd.patch`). Unspent gold 44.6k of 168k (26%; theirs 7%): Ren 612 a game on average (13,410 on the
  no-altar map: the style-2 build lists end after 24-30 emblems). The objective draft (Prism, Stellar, C&I, Ryth, Tavi) fired on nx50x50 (the only gem
  group, 2 elks + 6 gems = 72 gems, midway between the spawns, 27 gold clusters per side) and lost 72-1008 twice (37 and 32 deaths): `pd_obj_heavy`
  did not stop it (the group is heavy enough); new switch `pd_obj_side` (the objective must be nearer to us than to them). New switch `build_tail`
  (1: Power in the damage stat for ever after the list, 2: the Bruiser mix for ever). Proxy `_pw` = `_x_g5` + v5 switches + `build_style` 12 +
  f8a4f886's draft (HoR, Ren, Stellar, Ryth, Varg; forced with `LEGEND_DRAFT`, `mapdraft` 0: a sparring partner, never shipped). Queue `$S/q8.sh`:
  `_g5br` vs `_pw`; `_g5x0` (control), `_g5pt1`, `_g5pt2`, `_g5os` vs `_g4`; the draft screen `_d0f` (8,4,3,9,0), `_dh1` (11,8,4,0,9), `_dh2`
  (8,4,11,9,0), `_dh3` (8,4,3,11,0), `_dh4` (8,4,3,9,11), `_dm1` (11,8,9,0,6), `_dv1` (1,3,9,2,4), `_dc1` (5,4,3,6,11) vs `_g4` (forced drafts are
  measurement only: the result becomes priors and enemy-pick terms of the parameter draft; the user: nothing forced or hardcoded ships, everything
  from the map and the enemy's moves). ML agent told to add the 25 games to its training set.
- **12:05 UTC**: doc `docs/strategy_v2/15_LOSSES_OCT20.md` (the 25 games: results by opponent, builds, fights, camp deaths, maps). Tools
  `tools/strategy_v2/opener_ctx.py` (what our body did when the enemy opened on it: health at the first hit median 34%, death within 2 rounds
  57%; both teams spend the same share of field time hurt, so they pick our hurt bodies), `tools/ledger_maps.py OPP BOT...` (per-map ledger
  wins). Killer x victim: their Stellar 104 of our 362 champion deaths, HoR 72 in 11 games; our C&I 148 (41%); the two teams without C&I beat
  us 9-1. nx61x61: the central 71-gem group is captured by whoever stands on its tile (38998622_01: we dealt 2,850 of 4,460, their Stellar
  took it 6 rounds later; 0 of 8 kills captured by us). Results so far (42 games vs `_g4`; control `_g5x0` 28): `build_tail` 1 / 2 28 / 26,
  `pd_obj_side` 27 (nx50x50 0/2 vs the caster draft of `_g4`; but `_g5br` vs `_pw` 0/2 there), `_d0f` 24, `_dh1` 23; `_g5br` vs `_pw` 30/42
  (loses nx50x50 and nx61x61 0/2). New switches: `burst_far` (+ `burst_far_d`), `gold_rank` (+ `gold_rank_d`); variants `_g5bf5`, `_g5bf8`,
  `_g5bf5d4`, `_g5gr1`, `_g5gr1d8` (q9), `_g5bg40`, `_g5bg40p`, `_g5bg40d`, `_g5oa1` and the drafts vs `_pw` (q10).
- **11:45 UTC**: draft screen vs `_g4` (forced lists, `mapdraft` 0; of 42; forced control `_d0f` 24): `_dh1` HoR, Ren, Stellar, Ryth, Varg 23, **`_dh2` Ren,
  Stellar, HoR, Varg, Ryth 25**, `_dh3` HoR for Varg 19, `_dh4` HoR for Ryth 14, `_dm1` HoR, Ren, Varg, Ryth, Marcella 18, `_dv1` Vesper, C&I, Varg,
  Vendetta, Stellar 14; `_dc1` running; the same vs `_pw` queued (q10). The draft code is now parametric for the patch-3.0 tuning: `pd_hor_prior`
  (0.5), `pd_ci_prior` (0.9), `pd_counter_hor` (per enemy HoR / Marcella / Vendetta pick: + HoR, - C&I), `pd_gold_vesper` (x gold share of our
  half: Vesper, Marcella), `pd_obj_side` / `pd_obj_mid`; defaults = v5 play. New: `build_react` (a Durability / Bruiser health emblem is inserted
  at the shop whenever max health < build_react x the biggest potential burst any visible enemy has shown: the build answers their Power),
  variants `_g5rb25`, `_g5rb35` (+ `build_tail` 1; q11). Proxies `_pc` (c47c8c26: Prism, Stellar, C&I, Marcella, HoR + Power builds) and `_pv`
  (e6475502: Vesper, C&I, Varg, Vendetta, Stellar) built, not yet run. **ES stopped at generation 3** (load 20 on 4 cores: the screens come first;
  gens 0-2 mean-policy reward +0.29 / -0.42 / -0.01, nothing to apply; history `experiments/wip/x_es_nyx_history.json`). Deaths run at 2:1 in
  every 200-round bucket (59-75 vs ~30); contest_v3 (57 deaths vs c47c8c26): the opening 5v5 brawl at r38-55 lost (their Stellar cast first
  from 5), then bodies walking alone into their roaming 3 (Prism, Marcella, Stellar) at 64-98% health, dead in 1-9 rounds. ISSUES #21 (objective
  draft on a central group), #22 (`gold_rank_of` order).


## S13-GOD. PATCH 3.0 AND THE GOD BOT (2026-10-20 from 08:51 UTC): read this first

- **The user (08:51 UTC)**: patch notes "Week 2" (uploaded PDF, text in the scratchpad `patchdoc/new.txt`; summary below): every champion
  re-balanced, camps re-valued, new camp Golem, new champion **Heart of Ruin**, maps changed / added; update cambc and maps, make a bot
  better than m15 after the patch, named and levelled **GOD**.
- **Patch 3.0 facts** (SDK `sdk/cpp/cambc.h` 3.0.1 confirms the constants): Cassi HP 700 -> 600, per shard health 71.25 -> 65, str 3.5 -> 3,
  focus 15 -> 13; Issac health/shard 95 -> 80, str/shard 4.75 -> 3; Stellar focus 100 -> 85, str 35 -> 30, focus/shard 10 -> 9; Varg str 50 -> 40;
  Ren str 40 -> 35, focus/shard 10 -> 9; Ryth str 50 -> 45; Marcella focus 50 -> 60 (+15/shard), passive 2 gold per gem tributed + stun immunity;
  Willow str 45 -> 55, focus 105 -> 120; Vesper gold 20% -> 33%, str 45 -> 50; Vendetta str/shard 5 -> 6; Prism focus per carried gem 0.2 -> 1,
  health/shard 75 -> 60, str/shard 3.5 -> 2.5, focus/shard 10 -> 8; Tavi stun 2.2 -> 1.4 x focus, str 35 -> 45. **Heart of Ruin** (draft id 11):
  melee, 1000 HP (+100/shard), str 40 (+5), focus 100 (+15), passive up to +50% damage at 0% health, S1 self shield 1.5 x focus for 5 turns,
  S2 dash 2 that lands for 1.75 x focus and stuns 1 turn within radius 1. Camps: wolf 22 -> 4 gems, 90 -> 40 gold; elk 36 -> 15 gems, 160 -> 90
  gold, **range 3 -> 4**; gem cluster 500 -> 120 HP, 24 -> 7 gems; gold cluster 500 -> 120 HP, 35 -> 20 gold; **monolith range 3 -> 5**; **Golem**
  (new): 5000 HP, 120 str, range 4, 160 gold, 36 gems, respawn 80. Kill gold 50 -> 100. Ward cooldown 1 -> 10. Altar lock HP 3 -> 5.
  Breaking SDK: new enum values (camp `golem`, champion `heart_of_ruin`, passive `missing_health_damage`), `ability_dash` gained `radius`,
  `modifier`, `duration`.
- **Done**: `pip install cambc==3.0.1`, `cambc init --yes .` (SDK refreshed; `cambc.toml` sdk 3.0.1). **`cambc maps pull` is blocked**
  (proxy 403 on 2026a.battlecode.co.uk): the new official maps are not here; the user must allow the domain (environment network settings)
  or upload the maps. The old 2.2.5 SDK copy: scratchpad `sdk225/`. `legend_m15` still compiles on 3.0.1 (warnings only), so the ladder
  submission is not broken. **Ledger is now per engine**: `tools/ledger.py` writes `experiments/results/ledger_v3/` when cambc >= 3
  (`LEDGER_DIR` overrides); `ledger_pace.py`, `ledger_sum.py` follow it; old rows (engine 2.2.5) stay in `experiments/results/ledger/`.
- **New-engine baseline** (old official map files, cambc 3.0.1): `legend_m15` (`_mlkc40`) unopposed pace **1396.6** rounds (was 508; monolith
  hits r2000): games will often reach r2000 (tiebreak: gems, then gold earned, then kills; kills now pay 100). vs the proxies `_mite` 30,
  `_ifish` 24, `_px9` 18, `_snk` 31, `_fA` 27 = **130/170**.
- **GOD code (`bots/god`, = `legend_m15` + changes, all derived from the SDK)**: (1) Heart of Ruin in every build switch (with Ren: melee,
  focus-scaled spells) and in the focus-stat lists; (2) golem handled in the draft map analysis (heavy camp); (3) **camp attack range from
  the engine** (`CampRef::range`, `Group::max_range`): `near` / camp danger, the objective ring and the kite plan stand one tile outside the
  real range and count only spells that reach it (elk 4, golem 4, monolith 5); (4) `Kit::dash_mod` / `dash_radius` (dash landing damage) in
  `best_mod` / `burst_vs`; a damaging dash is not spent on walking while an enemy was seen within `strike_dash_hold` 9 (`mob_dash()`),
  `engage()` uses it as the strike (`strike_dash`). Frozen copies: `_g1` (1-3), `_g2` (1-4).
- **First result**: `_g1` vs `legend_m15` **26/34** on the official maps (new engine). Running: `$S/q31.sh` draft screen on `_g2`
  (`mapdraft` 0 + `LEGEND_DRAFT`): `_gd0` 8,4,3,9,0 (Ren, Stellar, C&I, Varg, Ryth), `_gdh1` 11,8,4,3,0 (HoR, Ren, Stellar, C&I, Ryth), `_gdh2`
  8,11,4,9,0 (no C&I), `_gdh3` 11,4,3,8,9, `_gdw` 11,8,3,4,7 (+ Willow), `_gdh4` 11,8,4,9,0, vs `_mlkc40`, `_mite`, `_ifish`; `$S/g1b.sh`: `_g1`, `_g2`
  vs `_mlkc40` + 5 proxies. Next: draft priors from the screen, gold value (a wolf is now 4 gems + 40 gold), fight margin (kills 100 gold),
  then ship `submissions/god.zip`.

- **Checkpoint 09:55 UTC: SHIPPED GOD v2** (`submissions/god.zip` sha256 f1a13eef…, history `god_v1_20261020.zip`, `god_v2_20261020.zip`,
  BUILDS rows; `bots/god` wasm = `_g3v33`). Screens (new engine, official map files, vs `_mite _ifish _px9 _snk _fA`, 170 games):
  `legend_m15` 130, `_g1` / `_g2` 144 (h2h vs m15 26 / 25), `_g3` (+ `pd_hor3`) 145 (26), gold value on `_g3`: 0.33 **158** (h2h vs `_g3` 20,
  vs m15 25), 0.44 156 (19, 22), 0.55 159 (19, 21), 0.66 156 (23, 20); `_g2`-based: 0.11 148 (14 vs `_g2`), fight_margin 1.15 149 (15).
  Draft screen (forced picks on `_g2`, vs m15 / Mite / ifish, 102 games): Ren, HoR, Stellar, Varg, Ryth 87; param draft 86; Ren, Stellar,
  C&I, Varg, Ryth 83; HoR first 76-79; HoR first with C&I second 57; + Willow 66. By team size: 3-maps HoR instead of C&I 20-23/24 vs 19
  (fragment, packs), 5-maps C&I better (45-47 vs 40): hence `pd_hor3` (draft.cpp: size 3, not objective / open farming). Unopposed pace
  official files `legend_m15` 1396.6, GOD v1 1295.6. **Patch-style maps** `maps/p30/` (official maps + gem clusters next to wolves / elks /
  gem clusters; `tools/mapgen/patch30.mjs`; `maps/p30g/` 6 copies with a golem per side): vs Mite / ifish / `_px9` (102): `legend_m15` 64,
  `_g3` 73, `_g3v33` **81**; h2h `_g3v33` vs `_g3` 21/34, vs m15 23/34; pace 834 / 828 / 877. Golems are farmed (interlock copy: 3 kills).
  Stopped at 10:00 when the Nyx zips arrived (only `_g4fm` finished: pooled 142/186, **h2h vs `_g4` 10/34: worse**; the rest never ran). Was: `$S/q35.sh` on `_g4` (= GOD v2): `_g4fm` (fight_margin 1.15), `_g4ml5` / `_g4ml3` (ML cut-offs 0.5 / 0.3), `_g4tm30` (tribute_min 30),
  official vs `_g4` + m15 + 5 proxies, and p30 vs `_g4`.

## S13. SESSION 13 (2026-10-19 21:00 UTC, new container): read this first

- **The user's request**: the main bot is now **`legend_m14_commit`** (= `_ch2`, zip sha256 e49afea0…, source hash 5f24a1979ddc; now
  `submissions/legend.zip`, `bots/legend/src` = it + the inert `LEGEND_RUNTIME_PARAMS` block, wasm byte-identical). New input: `new_matches.zip`
  = 10 match groups, **50 games, 11 wins** (`experiments/ladder_oct19b/`, `index.json` has map / our side / drafts / score; we are side B in
  group cd6785ff). The new bot must beat these opponents by a wide margin; loopholes / exploits / reverse engineering allowed; **no hardcoded
  map strategy** (everything derived from the map); ideas to test: a mobile body as a distraction, fight instead of recalling when still able,
  team synergies (Willow + two tanks; other champions), and the user's list: (1) drop the 60x50 ring term (ISSUES #1), (2) draft-time farming
  zones and routes (port `tools/strategy_v2/map_plan.py`, spec in doc 03), (3) `aoe_reach5`, `spread_vs_splash`, `pair_space`, `burst_exit`
  one at a time, (4) validate commitment. Opus subagents only for heavy work, few parallel tasks, checkpoints here. The four PDFs in the upload
  are personal documents (invoices, a boarding pass, a paper): not used, not committed.
- Setup in a new container: `tools/setup_session.sh` (now also builds `_ch2` from `submissions/history/legend_m14_commit_20261019.zip`, `_x_ic`, `_snk`).
- **Ladder findings (doc 13 in progress; tables `experiments/ladder_oct19b/analysis/`, `pergame.txt`; tools `tools/strategy_v2/ladder_pergame.py`,
  `ladder_deaths.py` take the side of each game from `index.json`)**:
  - Opponents (one per group, by draft): 2306b82f Varg/Ryth-first (0/5), 25464f3d C&I-first + Tavi/Willow/Vendetta (0/5), 43bd73e8 C&I-first (1/5),
    44b9a95f Varg-first (2/5), 5f7de946 Tavi/Willow casters (1/5), 6713bf97 Ren-first = old ifish table (2/5), 78da97d8 C&I-first + Vendetta/Tavi (1/5),
    c3f76526 Stellar-first = IC (1/5), c6ed5477 Stellar-first + Tavi (1/5), cd6785ff C&I + Tavi (2/5, we are side B).
  - Per game (47 non-contest): deaths 7.2 vs 5.5, camp gems 733 vs 993, captures home / neutral / enemy 15.9 / 2.6 / 0.4 vs 19.3 / 6.1 / 1.3,
    camp damage per round 81 vs 108 (per camp round: their Stellar 170 vs 144, Ryth 114 vs 86, Issac 78 vs 60).
  - **contest 0/3 with 87, 66, 51 deaths** (they earn 10-24k gold to our 1.5-2.8k); swirl 20 and 24 deaths, fragment 21 / 17 (mirror drafts),
    eight 20 / 17 / 20, collision up to 12: the blowouts are death cascades.
  - **Close races lost by timing**: rows 990-1012 (we reached 990 at r345, they 990 at r355 and won with a 22-gem bag at r358), 990-1023, 990-1056;
    lanes 918-1016 etc.: needs an endgame finisher (fastest bag >= the gems still needed), not the best gem rate.
  - Traced (fragment mirror, r28-44): the enemy woke an elk and stepped back; our Ren walked into its range and stood / walked next to it for 8
    rounds without attacking (740 -> 0, killed by the camp); our C&I at 220/700 stayed in the field and died to Stellar / Cassi area casts.

- **More ladder findings (21:15 UTC)**: burst deaths (>= 60% health 3 rounds before) are 41% of ours (them 34%), 99 of 147 are Cassi & Issac,
  the killer usually at distance 4-5, 68% of the damage from spells (`tools/strategy_v2/death_ctx.py`, `burst_ctx.py`). Opponents' contested
  finish beats our UNOPPOSED pace on rows / lanes / monolith / pilgrimage / ambush; same-draft monolith game: they re-take each near group at
  its respawn (every 55-70 rounds), we leave near groups 100-120 rounds. Stampede: the objective reward is stolen by bodies standing on its dead
  gem tiles (we killed it 4 times vs the Varg-first team and captured once; vs IC we captured all 3 of its kills: 1080-0).
- **Work in this container (checkpoint 21:20 UTC)**:
  - Agent `zone` (Opus, background): draft-time farming zones / circuits on `bots/_x_zone` (variants `_z*`), notes `experiments/wip/x_zone_NOTES.md`,
    patch `x_zone.patch` (committed by the checkpoint loop every 15 min). If it is gone: read its notes, rebuild from the patch, continue.
  - Coordinator code `bots/_x_s13` = `_ch2` + `experiments/wip/x_s13.patch` (switches off = `_ch2` play): `finish_race` (endgame: groups that
    finish the game alone score by landing time), `big_reward` / `big_reward_r` / `big_reward_hp` (fight for 100+ gem groups: whole team in the
    threat check, contest an enemy waiting on a dead tile via `contest_tiles()`, every body contests their capture), `big_reward_dive` (deny an
    enemy capture of a 200+ gem reward whatever the threat), `recall_join` (cancel a shop/heal recall to join a fight next to us).
  - Screens (official 34 vs `_ch2` + the 5 proxies; `_ch2` pooled 129/170): `o2_ring_size` 0 130 (h2h 17, same games: SHIP, ISSUES #1);
    **`aoe_reach5` 2: 136/170, h2h 19/34, deaths 328-409 (lead)**; `aoe_reach5` 1: 132, h2h 16; `spread_vs_splash` 1: 117, 2: 127 (both h2h 19): no.
    Queued: `pair_space` 1/2, `burst_exit` 2/1; then `_s_c0` (control), `finish_race` 70/150, `big_reward` 100, `recall_join` (+ pace vs idle);
    draft synergy `_d_wt` (Ryth, Varg, Willow, Ren, Stellar), `_d_w5` (Willow for C&I), `_d_ci` (C&I-first), `_d_vt` (Varg-first), `_d_mar`
    (Marcella), `_d_ven` (Vendetta); then `_s_brd` (big_reward + dive 200), fight-more `_f_fm115`, `_f_fb75`, `_f_crh45`, `_f_of65`.
    Scripts in the scratchpad (lost with the container): `screen.sh VARIANT...` = `tools/ledger.py run V OPP --maps 'maps/comp/*.map26a'` for
    OPP in `_ch2 _mite _ifish _px9 _snk _fA`; results: `BASE=_ch2 python3 tools/screensum.py VARIANTS`.

- **Checkpoint 22:05 UTC: results so far** (official 34 vs `_ch2` + 5 proxies; `_ch2` 129/170):
  - **Economy is not routing, it is contact**: unopposed `_ch2` captures 151 gems by r100 and 564 by r300 (15 maps; better than the ladder
    teams do contested: 136 / 480); on the ladder we get 111 / 401. By r150 (equal items) they deal 21% more camp damage, more champion damage
    (1.66k vs 1.27k) and die less (0.9 vs 1.3). Fight openers decide 3-round trades ~4:1 and they open 55% of fights. The zone agent finds the
    same (unopposed revisit gaps are already short; best `_z5` official pace 497.1 vs 502.7, gen2 +7 worse).
  - Unopposed pace understates our race pace: ahead by >= `lead` (150) the bot banks smaller bags (tribute_min x 3/4); unopposed it always is.
  - Builds (unopposed pace, official / var17 51 maps): our builds 502.7 / 501.6; IC (`build_style` 11) 526.4 / 535.9; ladder style 3: 538.8 / 531.1;
    ifish 10: 534.8 / 532.6 (damage builds win only monolith 398 vs 437 and ambush): **no build change**.
  - `recall_join` 132 (h2h 17): small plus; `finish_race` 70 / 150: 126 / 123 and slower unopposed (the rows races were decided by
    split captures: three 22-gem bags bank in 3 turns, a 66 bag in 7): rejected; `big_reward` 100: 126 official; objective pool (stampede +
    `maps/obj`, vs `_mite _ifish _px9`, 78 games): `_ch2` 53, `_s_br100` 55, `_s_brd` (+ dive 200) 54, `_s_brp` (+ reward_pre 3) 54, but h2h vs
    `_ch2` there 9 / 11 / 12 of 26 (slugfests at the objective): parked. `aoe_reach5` 2 on the 28 generated maps 169/270 vs `_ch2` 181 (official +7,
    generated -12; 88 distinct 305 vs 310, h2h 45/88): mixed. `pair_space` 1 / 2: 122 / 129; `burst_exit` 1 / 2: 130 (same games mostly).
  - Draft synergy screen had a bug (LEGEND_DRAFT is ignored while `mapdraft` 6): rebuilt with `mapdraft=0`: `_d_ours` (fixed Ren, Stellar, C&I,
    Varg, Ryth: the control), `_d_wt` (Ryth, Varg, Willow, Ren, Stellar), `_d_w5`, `_d_ci`, `_d_vt`, `_d_mar`, `_d_ven`; compare per team size with
    `tools/pickscreen.py`. Combos queued: `_c_ar2rj`, `_c_ar2of` (open_first 3), `_c_ar2of2`, `_c_ar2rjof`. `ci_first` (`_s_cif`), `burst_retreat`
    (`_s_bt10`, `_s_bt15`), `ci_health_first` (`_f_cih`) and fight-more params (`_f_fm115 _f_fb75 _f_crh45 _f_of65`) queued.

- **Checkpoint 23:15 UTC (after a container restart at 22:50; the user: "the final bot must crush every team in the zip and the current
  legend; their strategies may change; best bot by this evening (IST); 3 more sessions; k-means / logistic regression allowed")**:
  - All background jobs died with the restart; the filesystem survived (bots, scratchpad, ledger). Zone agent: stopped at the session limit,
    nothing shippable (`x_zone_NOTES.md`: zones spread bodies and cost fights; pair zones 131 pooled but 13/34 h2h): **direction closed**.
  - More screens (official, pooled of 170 / h2h of 34): `outmatch_flee_adv` 0.65 131 / 18, `fight_margin` 1.15 128 / 17, `cap_recall_hp` 0.45
    128 / 19, `fight_back_margin` 0.75 126 / 16, `burst_retreat` 1.0 / 1.5 127 / 122, `ci_health_first` 116 / 14, `aoe_reach5` 2 + `recall_join`
    136 / 19 (= `aoe_reach5` 2 alone), + `open_first` 3: 133 / 18. **Local contest is the mirror of the ladder**: `_ch2` beats every proxy there
    9/10 with deaths 7-37 vs 47-66; the ladder teams draft the same casters and crush us: our proxies cannot reproduce their execution.
  - Contest traces (r20-45): both teams reach the centre by r25; ours splits: Ren recalls home at r31 or keeps farming the centre gold 10-13
    tiles from the fight (rallies are answered only within 9 and never while capturing), 4 of ours lose to 5. New switches in `x_s13.patch`:
    `rally_r` / `rally_hp` (variants `_s_ra13`, `_s_ra13h`), `recall_join` 2 (an ally's fight within 8 is enough; `_s_rj2`).
  - **Running**: (1) Opus agent **`mlfight`**: fight / danger model by logistic regression on ~190 decoded ladder games (ours and top-vs-top),
    integrated as switches in `bots/_x_ml2`; notes `experiments/wip/x_ml2_NOTES.md`, patch `x_ml2.patch`, scripts `tools/ml/`. (2) **ES exploiter**:
    `tools/rl/es_train.py` (now takes `ES_SRC`, `ES_OUT`, `ES_PREFIX`) trains `_x_s13`'s parameters and switches (39, space
    `experiments/wip/x_es13_adv_space.json`) to beat `_ch2` on the official maps (`tune_out/es_adv/`, log in the scratchpad `es_adv.log`):
    the result is a stronger sparring opponent (and maybe a candidate). (3) Queue: drafts `_d_*` (mapdraft 0 + forced picks), `_g_q05*`, `_s_cif`,
    then `_s_ra13*`, then candidate **`_cand1`** (= `_x_s13` + `aoe_reach5` 2 + `o2_ring_size` 0 + `recall_join` 1; hash b35c20488598) on pad17 + gen2
    and the 28 generated maps vs `_ch2` + the 5 proxies.

- **Checkpoint 23:45 UTC**: ES exploiter run 1 failed (relative `ES_OUT`: `run-batch` resolves paths from the manifest folder; fixed in
  `es_train.py`, restarted 23:25 with 12 generations). Draft / synergy results in SUGGESTIONS.md (Willow + two tanks 75/170, Willow for C&I 90,
  C&I-first team 107, Varg-first 102, our fixed team 124 < parameter draft 129, `ci_first` 116): the draft stays. **New best combination
  `_c_ar2of2` = `aoe_reach5` 2 + `open_first` 2 (hold at the edge of enemy reach with an opener ready): 138/170, h2h 19/34.** Candidate
  **`_cand2`** = `_x_s13` + `aoe_reach5=2 open_first=2 o2_ring_size=0 recall_join=1`; queue (`$S/q14.sh`, `q15.sh`): `_cand2` official screen,
  `_s_ra13`, `_s_rj2`, `_s_fx` (`flee_exit` 1: sideways step out of enemy / camp reach while fleeing), then `_ch2` and `_cand2` on generated +
  pad17 + gen2 vs `_ch2` + 5 proxies, then `_c2_oh3` / `_c2_oh4` (`open_hold`), `_c2_sf1` / `_c2_sf2` (`strike_first`) on `_cand2`.

- **Checkpoint 23:55 UTC: release candidate 1 sent to the user** = `submissions/candidates/legend_m15_rc1_20261020.zip` (sha256 4bb34776…) =
  `_cand2` (source hash 33f088e5eb74): official 34 vs the 5 proxies **141/170** (`_ch2` 129), h2h vs `_ch2` 20/34; wider pools running. Also:
  `_c2_of6` (+ melee edge hold, `open_first` bit 4, new code) 139 / 20; `_g_q05` (GROUPED stance prior 0.5) 128 / 20; `_d_mar` 102, `_d_ven` 114.
  **ML agent results** (`x_ml2_NOTES.md`): logistic P(die within 8 rounds) on 160 ladder games, AUC 0.81 on our bodies vs 0.60 for the bot's
  own fight estimate; our bodies die x1.7 more often than others' in the same visible state; first variants `_mll40`, `_mlf40` 130/170
  (level locally, as expected for a model calibrated on stronger opponents). The agent was told to stack its switches on `_cand2`.
  New coordinator switches (all in `x_s13.patch`): `open_first` bit 4 (melee hold), `bush_ghost` N (an enemy that vanished in / next to a
  bush stays in the danger map N rounds; `_c2_bg20`), `flee_exit` (`_s_fx`). Queue: `_s_ra13`, `_s_rj2`, `_s_fx` (on the `_ch2` base), wide
  pools for `_cand2`, then on `_cand2`: `_c2_oh3`, `_c2_oh4` (`open_hold`), `_c2_sf1`, `_c2_sf2` (`strike_first`), `_c2_ea` (`engage_angle`),
  `_c2_bg20`. The ES exploiter runs at nice 15 (CPU goes to the screens first).

- **Checkpoint 00:10 UTC (Oct 20): new lead `_mlkc40`** (ML agent) = `_cand2` + `experiments/wip/x_ml2.patch` (base copy `bots/_x_ml2c`) with
  `ml2_leave` 0.4, `ml2_flee` 0.4, `ml2_cornered` 1: the ladder-trained logistic danger model (P(die within 8 rounds), 58 features, weights in
  `src/ml2_model.h`); the part that works is `ml2_cornered` (deadly states count as cornered, so the body trades instead of giving free hits).
  Official 34 vs the 5 proxies **149/170** (`_cand2` 141, `_ch2` 129); h2h vs `_cand2` 19/34 (deaths 309-340), vs `_ch2` 22/34 (313-432);
  rollovers unchanged (gen16 8 per team r1-3; contest / eight 0). Health-only ablation (`_mlhp45`, same veto at health < 45%) 133: the model
  picks better. On `_ch2`: `_mlcf40` 141 / 20 (deaths -19%). **Wide validation running** (agent: `_mlkc40` on 28 generated + pad17 + gen2 vs
  `_cand2`, `_ch2` + 5 proxies; coordinator: `_ch2` and `_cand2` vs the 5 proxies on the same pools). Coordinator's rally 13 / recall_join 2 /
  flee_exit / grouped: level or worse (SUGGESTIONS.md). ES exploiter stopped after 2 generations (history `experiments/wip/x_es13_history.json`).
- **Checkpoint 00:15 UTC**: wide pool (28 generated + pad17 + gen2 = 134 games) h2h `_mlkc40` vs `_cand2` **77/134**, vs `_ch2` **71/134**; its
  proxy cells still running (agent `wide2`), `_ch2` / `_cand2` proxy cells on the same pool by the coordinator (`$S/q14.sh`). Stack build
  `bots/_x_fin` = `_mlkc40` sources + `bush_ghost` and `open_first` bit 4 (melee hold) ported from `_x_s13` (all off = `_mlkc40` play; rebuild:
  `SRC=bots/_mlkc40 tools/variant.sh _x_fin`, then `cd bots && diff -ruN _cand2/src _x_s13/src` applied with `patch -p1` inside `_x_fin`, then
  restore `recall_join` 1, `o2_ring_size` 0, `aoe_reach5` 2, `open_first` 2 in params.h). Variants `_xf0` (control), `_xf_bg20`, `_xf_of6`,
  `_xf_sf1`, `_xf_oh3`, `_xf_ea` queued (`$S/q19.sh` -> `screen_ml.sh`: official 34 vs `_mlkc40` + 5 proxies; `BASE=_mlkc40 tools/screensum.py`).

- **SHIPPED `legend_m15` (04:20 UTC, Oct 20)** = `_mlkc40` (source hash 8eb9563d0d5b; `submissions/legend.zip` sha256 4caf8438…, history
  `submissions/history/legend_m15_20261020.zip`, BUILDS row; `bots/legend/src` = `_mlkc40` + the inert `LEGEND_RUNTIME_PARAMS` block, wasm
  byte-identical). Rebuild `_mlkc40` in a new container: `_cand2` = `_x_s13` (= `_ch2` + `experiments/wip/x_s13.patch`) + `aoe_reach5=2 open_first=2
  o2_ring_size=0 recall_join=1`; `_x_ml2c` = `_cand2` + `experiments/wip/x_ml2.patch`; `_mlkc40` = `_x_ml2c` + `ml2_leave=0.4f ml2_flee=0.4f ml2_cornered=1`
  (or simply copy `bots/legend` and drop the runtime block). Evidence: official 34 vs the 5 proxies 149/170 (`_ch2` 129), h2h vs `_ch2` 22/34;
  67 more maps 475/670 (`_ch2` 452; pad17 128 vs 118, gen2 165 vs 153, generated 182 vs 181), our deaths 3,725 vs 4,297, h2h vs `_ch2` 71/134,
  vs `_cand2` 77/134; pace 508.1 vs 502.7 (only rushbait-v2: 699 vs 606, from `aoe_reach5` vs idle enemies at spawn; ISSUES #16); 0 faults;
  rollovers unchanged. Stacked tweaks on it all worse (`_xf_*`: bush ghost 141, melee hold 144, hold 3 144, strike first 136, engage angle 141;
  SUGGESTIONS.md). ML agent (session limit hit 03:50; notes `x_ml2_NOTES.md`): `_mlkc30` 142, `_mlka40` (in-match recalibration) 146.
  ISSUES.md: #1 fixed, #15 (model fixed to the Oct 19 opponents), #16 added. **Next**: the user's ladder check of `legend_m15`; locally, a
  decision model (P(die | step away) vs P(die | hit)), contest / stampede execution (the proxies cannot reproduce the ladder teams there).

- **Checkpoint 04:45 UTC**: running (scratchpad scripts, lost with the container; results land in the ledger): `q20.sh` = held-out pools
  (gold, gold2, gold3, obj; 78 maps) for `_mlkc40` and `_ch2` vs `_mite _px9 _ifish`; `q21.sh` = **objective-reward theft** test on
  `maps/obj` + stampede (26 games per cell): stealing proxies `_stl` (= `_mlkc40` + `big_reward` 100 + `big_reward_dive` 200: stands on our
  dead objective tiles like the ladder teams did) and `_stlm` (+ Mite draft / builds / ring); defences on `_mlkc40`: `_m15br` (big_reward 100),
  `_m15brd` (+ dive 200), `_m15brp` (+ reward_pre 3), vs `_stl _stlm _mite _ifish _px9`. ML agent resumed (03:50 reset) on `ml2_enter`
  (kill model: fight more when P(kill8) high and P(die8) low) and the action-conditioned decision model, baseline `_mlkc40`.
  Rows traced (ladder 25464f3d_03): at 990 every body walked to far groups; Cassi's 66 capture landed 13 steps from our altar (7 tribute
  turns) while they split the last group 3 x 22 (3 turns each): geometry + pace, not a last-rounds choice; `finish_race` changed no local rows game.

- **Checkpoint 04:15 UTC: held-out regression found** (gold, gold2, gold3, obj = 78 maps, 156 games): vs `_mite` `_mlkc40` 126 / `_ch2` 138 /
  `_cand2` 122 (so `_cand2`'s switches cost it and the ML model wins 4 back); vs `_px9` 98 / 99 (level; per-pool swings of +-9: these long
  gem-scarce games are chaotic). Objective theft (26 games): vs `_stl` `_mlkc40` 12, `_m15br` / `_m15brd` / `_m15brp` 13; vs `_stlm` 12 vs 16 / 16.
  Running: `q23.sh` one-switch ablations of `_mlkc40` on held-out vs `_mite` (`_pz_ar0` aoe_reach5 0, `_pz_of0` open_first 0, `_pz_rs1`
  o2_ring_size 1, `_pz_rj0` recall_join 0); `q24.sh` official screen of `_pz_ar0` (vs `_mlkc40` + 5 proxies) after `q20`. ML agent: `_ml3e40`
  (enter fights at P(kill8) >= 0.4, P(die8) < 0.15) 147/170, h2h 16/34: no; more enter variants queued.

- **Checkpoint (after q20-q26)**: held-out totals (gold, gold2, gold3, obj; vs `_mite` / `_ifish` / `_px9`, 156 each): `_mlkc40` 126 / 131 / 98 =
  **355/468**, `_ch2` 138 / 121 / 99 = 358, **`_pz_ar0` (= `_mlkc40` without `aoe_reach5`) 141 / 131 / 115 = 387**. But on the official 34
  `_pz_ar0` 137/170 vs 149 (h2h 14/34): `aoe_reach5` gains elkring +3, monolith +3, rushbait-v2 +3, packs +2 there (so no simple scarcity gate)
  and was selected on those maps (biased). Running `q27.sh`: `_pz_ar0` on the 67-map wide pool vs the 5 proxies + h2h vs `_mlkc40`
  (`_mlkc40` there: 475/670). `big_reward` 100 on `_mlkc40` (`_m15br`): objective pool 85/130 vs 79 (stealing proxies +5) but official
  145/170 (h2h 17): off. `_m16a` (no reach5 + big_reward) 135. ML agent phase 2 (`x_ml3.patch`, `bots/_x_ml3`): `ml2_enter` 0.3 / 0.4 / 0.5
  149 / 147 / 148 (h2h 17 / 16 / 17), recall cancel never fires, two-action model 142 (h2h 19): ties at best, nothing shipped.

- **Checkpoint 05:05 UTC**: ML agent finished (final report in `experiments/wip/x_ml2_NOTES.md`; phase 2 `x_ml3.patch` / `bots/_x_ml3`:
  nothing beats `_mlkc40`; skipping the early flee raises deaths 31-49%; recall cancel never fires; only the exit rule holds). Wide pool, `_pz_ar0`
  (no aoe_reach5) vs `_mite _ifish _px9 _snk` 98 / 87 / 93 / 93 (`_mlkc40` 100 / 88 / 90 / 95): level, so `aoe_reach5` stays (official +12,
  ladder deaths from spells at 4-5; held-out cost recorded in ISSUES). Running: `q27` (rest of `_pz_ar0` wide), `q28` (`_ml3e30` wide: the
  "fight more" tie), `q29` **decoy** (the user's distraction idea: `bots/_x_dc` = `_mlkc40` + `experiments/wip/x_dc.patch`; the free dash
  body = Ren works the enemy half while healthy and carrying < 10: `enemy_half_penalty` x `decoy_half`, `deny_bonus` + `decoy_deny`;
  `_dc0` control, `_dc1` (0.2 / +0.5, r0-600), `_dc2` (0 / +1.0), `_dc3` (r150-2000); official 34 vs `_mlkc40` + 5 proxies).

- **Checkpoint 05:45 UTC**: decoy rejected (`_dc1` 137, `_dc2` 125, `_dc3` 141; h2h 17 / 18 / 15); `_ml3e30` wide 478/670 (`_mlkc40` 475,
  h2h 65/134): a tie, not shipped; `_pz_ar0` wide 479/670 (h2h 65/134): level, `aoe_reach5` stays; fallback zip without it:
  `submissions/candidates/legend_m15_noreach5_20261020.zip` (for a gem-scarce final pool). Robustness vs other styles (official 34, `_mlkc40` /
  `_ch2`): `_pg3` (= m14) 16 / 21, `_m8` 17 / 21 (same flips: m14 = m8 there), `_ST` 30 / 30, `_eD` 32 / 33, ES exploiter `_esx` 18 / 13,
  `_stlm` 22 / 21. Traced fragment A vs `_m8` (80-1056, deaths 23-6; `_ch2` wins it): r122 the ML exit pulled Cassi, Issac and Ren out together
  with their Stellar at 175 HP and their Issac at 720; our slow pair died anyway at r127 with no kill; `_ch2` stayed, traded 2 for 2, won.
  New switches `ml2_stayk` (no ML exit while P(kill8) >= X) and `ml2_trade` (no ML exit while an enemy in reach + 1 has health <= N x our local
  damage per round): `bots/_x_tr` = `_mlkc40` + `experiments/wip/x_tr.patch`; `q30.sh`: control `_tr0`, `_trk4`, `_trt15`, `_trk6`, `_trt3`.

- **Checkpoint 05:35 UTC**: trade exceptions rejected (`_trk4` 145, `_trk6` 148, `_trt15` 143, `_trt3` 141; h2h 13-16). Ladder A/B option zipped:
  `submissions/candidates/legend_m15_cautious_20261020.zip` (= `_mlkc30`, cut-offs 0.3; reasoning in `submissions/candidates/README.md`).
  **Running: ES on `legend_m15`'s own parameters** (`$S/es15.sh`: `ES_SRC=bots/_mlkc40 ES_OUT=tune_out/es15 ES_PREFIX=_e15`, space
  `experiments/wip/x_es15_space.json` = 29 fight / economy params + `ml2_leave`, `ml2_flee`; opponents the 5 proxies; maps official 17 +
  gen2 24, 8 per generation; 30 generations x ~720 games, ~7 min each). Judge the result like the A100 run: apply only parameters that moved
  consistently, then validate on pad17 + generated + held-out (not used in training) and the official screen. `tune_out/` is git-ignored:
  copy `history.json`, `best_params.json` to `experiments/wip/x_es15_*` when done.

- **Checkpoint 05:40 UTC: the user: "legend m15 is still losing to Mite and Nyx; fix the issues after completing all other tasks"** (no replays
  of m15 came with it; Nyx is a team name not seen in any file). From the Oct 19 replays: **Mite = group 2306b82f** (drafts match our MITE table
  except Ren instead of Tavi as the 5th pick on stampede / contest); Nyx candidates 25464f3d (C&I-first + Tavi / Willow / Vendetta, 0/5) or
  44b9a95f (Varg-first, 2/5). vs Mite (`$S/farmstat.mjs`, `caps.mjs`, `track.mjs`, `deaths.mjs`): interlock / collision are economy losses
  while winning the kills (deaths 6-10, 12-16): they take the neutral elk pairs (interlock 576 neutral gems vs our 0; a 4-body group on the
  corner elks from r40) and re-take their own respawned camps after 15-23 rounds (ours 20-39; our Issac solo-cleared a wolf in 25 rounds;
  our Cassi hovered 70 rounds at the centre after banking); swirl 20-3 deaths at the centre camps between the spawns; stampede objective
  stolen; contest. Across all 10 groups: they re-touch own-side respawned camps after 11-25 rounds, we 30-46, they capture 1.5-2x more.
  Proxy `_mite2` (`bots/_x_mt2` = `_mlkc40` + `experiments/wip/x_mt2.patch`: MITE table with Ren 5th; + Mite builds, ring, big_reward + dive):
  `_mlkc40` 26/34, `_ch2` 24/34 (our brain plays their draft worse: not a real stand-in). Plan: after the ES run, an **exploiter** ES that
  trains a copy to beat `_mlkc40` (league training), then harden `_mlkc40` against it + the proxies. Ask the user for the m15-vs-Mite/Nyx zips.

## S12. SESSION 12 (2026-10-19, same container as S10/S11): read this first

- Shipped bot at the start: **`legend_m14`** (`submissions/legend.zip` sha256 50ca7600…, frozen `bots/_pg3`, S7R). Baseline for every A/B: `_pg3`.
- The user's request: examine the new INTERWIN.zip (Intercontinental Fish = IC, ladder #1, vs other teams), find what IC does efficiently,
  implement it on a new bot, A/B vs the current legend, keep what helps; write **SUGGESTIONS.md** (strategies that should work in theory but did
  not measure better) and **ISSUES.md** (anything hardcoded that may break when the map pool changes); **derive parameters, do not hardcode**;
  notify the user about any hardcoding. Mid-session: explain / establish the shared-memory communication (it exists: comms.h; report in chat).
- Analysis: `docs/strategy_v2/12_IC_OCT19.md`; replays `experiments/interwin_oct19/` (45 distinct games), tables in `analysis/`; tools
  `tools/strategy_v2/ictab.py` (IC side by its Stellar-first table), `regap.py` (respawned camps left unattacked, first touch), `tools/screensum.py`
  (pooled proxy cells + h2h vs `_pg3`), `tools/samegames.py` (identical-games check of a control). IC wins 32 of 44; deaths 3.2 per game (ours 7.6
  vs the ifish proxy); captures per 100 rounds rise 3.9 -> 5.1 over r0-400 (ours flat 2.7-3.5); Stellar collects 1.44 captures / 262 gold per 100
  alive rounds (ours 0.73 / 150); Power emblem first on its carries, **Home emblem (recall in 3 turns) second** on Stellar / Issac / Varg; respawned
  camps re-hit after 13.8 rounds on average (ours 26.5: a long tail; unopposed our maps are fine except interlock, lanes, pilgrimage, rushbait-v2).
- Code: `bots/_x_ic` = `_pg3` + `experiments/wip/x_ic.patch` (all switches off = m14 play; control `_ic0` 33/34 games identical vs Mite):
  `ic_home` 1/2/3 (Home emblem: after a damage first emblem / on all / after N recalls), `build_style` 11 (IC builds), `recall_turns()` (recall
  time aware of Home), `o2_ring_size` (ISSUES #1: drop the 60x50 term), `reward_claim_gone` (a living ally's claim leaving an unseen reward =
  taken; found in a traced interlock game: Ryth walked 12 steps to a reward Ren had captured), `commit_hit` / `commit_keep` (do not leave a camp
  we hit in the last 2 rounds: 198 such abandonments in 17 unopposed official games, 92 for a slightly better score, 67 on the join limits),
  `mapdraft` 7 (IC's per-map table: proxy only). Recall counter `recalls_started`, `target_hit_round`.
- Screen (official 34 vs `_mite _ifish _px9 _snk _fA` pooled 170 games; `_pg3` 135 = 79.4; h2h of 34 vs `_pg3`), all in SUGGESTIONS.md:
  controls `_ic0` 134 (18), `_ic1` 132 (17; carried a capture-time bug, see below); Home emblem `_ich1` 114 (15), `_ich2` 120 (16), `_ich3` 132 (17);
  IC builds `_icb` 105 (16); IC proxy `_icp` (IC table + builds) 112 (11), IC draft only `_icd` 119 (14); `max_wait` 24 / 30: 120 / 118; `cap_recall_hp`
  0.45 / 0.5: 133 / 135 (16, 16); `tribute_min` 66: 131 (19); `early_tribute_min` 40: 137 (13: non-transitive); bulk shopping `_ss8` 130, `_crg120` 131
  (11), `_bulk` 126; `reward_claim_gone` 1: 125 (17; too eager: claims also leave rewards the ally abandons to heal); `o2_ring_size` 0: identical to its
  control on the official maps (as designed). **Commit switches**: `_ch2` (`commit_hit` 2) 129, **h2h 21/34**, pace 502.7 (control `_ic2` 509.4;
  rushbait-v2 670 -> 606, ambush 553 -> 508, elkring 452 -> 428); `_chk` (+ `commit_keep`) 130, h2h 19, pace 498.8; `_ck` 128, h2h 14, pace 498.0.
  Wider pools (88 distinct maps x 5 proxies = 440; pad17 + gen2 x 3 proxies = 240; m14 322 / 155, control `_ic2` 316 / 155, h2h 43/88, 41/80):
  `_ch2` 310 / 148, **h2h 51/88, 44/80**; `_chk` 313 / 152, h2h 47/88, 35/80. Softer: `_ch15` 125, h2h 21; `commit_prog` 1 / 2 (`_cp1`, `_cp2`)
  132 / 129, h2h 18 / 22, pace 503.1 / 502.9. `half_grade` 0.3 / 0.5: 130 / 125 (h2h 19 / 16). `reward_claim_gone` 2: 124 (15).
  **Verdict: nothing passes the rule; `legend_m14` stays shipped.** The commit switch is the one lead (beats m14 head-to-head on every pool, faster
  unopposed, ~1 SD worse vs the proxies): ladder candidate `submissions/candidates/legend_m14_commit_20261019.zip` (= `_ch2`, sha256 e49afea0…).
  Code of every switch: `experiments/wip/x_ic.patch` on `_pg3` (rebuild: `SRC=bots/_pg3 tools/variant.sh _x_ic && (cd bots/_x_ic && patch -p1
  --no-backup-if-mismatch < ../../experiments/wip/x_ic.patch)`, then `SRC=bots/_x_ic tools/variant.sh NAME switch=value`).
- Next (if the user wants more): (1) ladder A/B of the commit candidate vs `legend_m14`; (2) commitment that releases when an enemy is within
  danger reach (its losses concentrate on `_fA`); (3) a comms repack to give each body an "I captured" bit (makes the claim rule exact);
  (4) ISSUES.md #1 (`o2_ring_size` 0) whenever the next build ships (no effect on the official maps).
- **Bug found and fixed in my own change**: `capture_time` is 5; the literal 6 in `world.cpp` meant `capture_time + 1`. Replacing it with
  `capture_time` alone shifted respawn predictions one round early (control 132 instead of 134-135). Fixed to `capture_time + 1`; variants built
  before the fix (`_ic1`, `_rsz0`, `_rcg`, first `_icp`) carry it (`_icp`/`_icd` were rebuilt after the fix).
- The user also asked how the shared memory works (answered in chat: bytes 0-5 claims + team bag bits + stance, 6-7 one alert; claims are
  leases resolved by the same tie-break in every body; measured gains listed there).

## S7R. SESSION 7 RESUMED (2026-10-18 20:05 UTC, the original S7 container, live in parallel with S11): read with §S11

- **SHIPPED `legend_m14` (23:50 UTC)** = `_pg3` = m13 + `experiments/wip/x_pg.patch` with `o2_ring` 3, `o2_ring_team` 5, `mono_size50` 2, `pd_obj_multi` 1
  (hash cdc6dc9027f3; sha256 50ca7600…; `submissions/history/legend_m14_20261018.zip`; `bots/legend/src` = it + the inert `LEGEND_RUNTIME_PARAMS` block,
  wasm byte-identical; `tools/setup_session.sh` rebuilds `_x_pg`, `_pg3`). `o2_ring_team` 5 because on the three 4-champion objective maps
  (obj_pack4) the ring won 14/30 vs 20/30 without it (m12 15/30); at 5 champions 75/90 vs m13 51/90, m12 62/90. Final cells (win %, pooled
  vs Mite, ifish, `_px9`, `_snk`, `_fA`; m12 / m13 / m14): official 79.4 / 79.4 / 79.4 (identical games, 170/170); resized official 65.6 / 69.4 / 73.1;
  objective + resized stampede 64.2 / 59.2 / 79.2; contest at new sizes 96.2 / 60.0 / 96.2; fresh generated 66.7 x3 (identical); held-out
  (gold, gold2, gold3, obj; 78 maps, vs Mite / `_px9` / ifish) m12 80.8 / 59.0 / 76.3, m13 84.0 / 57.7 / 74.4, m14 86.5 / 62.2 / 75.0. h2h m14 vs m13
  64.3 (126) / held-out 55.1 (156); vs m12 54.4 (160) / held-out 50.0 (156). m14 >= m13 in every cell. Earlier cuts `_pg`, `_pg2`, `_pr`, `_pcg`, `_pg0`
  (rows in the ledger) came from intermediate versions of `x_pg.patch` (without `o2_ring_team` / `pd_obj_multi`) and cannot be rebuilt exactly.
- **23:25 UTC, the user: "improve the bot by A/B testing m13 and m12 on the official maps and on maps you create"** (the final sprint changes the
  map pool). New pools: `maps/pad17` (16 official maps framed by walls: new sizes, same play; `tools/mapgen/pad_map.mjs`), `maps/ctsz` (contest at
  6 new sizes + perturbed copies, `tools/mapgen/perturb.mjs`), `maps/gen2` (24 fresh `gen.mjs` maps, seed 2026), `maps/gold3` (gem-scarce, seeds 31/37).
  Found: m13's draft is size-free but two brain plans were not: the stampede ring only at 60x50 (m13 drafts the casters on any objective map, then
  plays them without the ring) and the contest plan only at 50x50. Candidate code `_x_pg` = m13 + `experiments/wip/x_pg.patch`: `o2_ring` 3 (ring
  also when our team has Prism or Tavi), `mono_size50` 2 (contest plan when every lone monolith stands near the middle: min(d, 1-d) of the
  spawn-to-spawn walk >= `mono_center` 0.45; contest and copies 0.50 at any size, the gold_mono maps where the plan lost 0.38-0.42), `pd_obj_multi`
  (objective draft only when the lone gem group is multi-camp: excludes the gold_elk maps, where no objective plan runs). Control `_pg0` (defaults)
  34/34 games identical to m13. `_pg` = o2_ring 3 + mono_size50 2; `_pg2` = `_pg` + pd_obj_multi 1 (ship candidate).
  Results (win % vs Mite, ifish, `_px9`, `_snk`, `_fA` pooled; games): objective / resized-transposed stampede (12 maps, 120): m12 64.2, m13 59.2,
  `_pg` **74.2** (unopposed stampede_p2 471/479 rounds = the original map's, m13 803/790); contest at new sizes (13 maps, 130): m12 96.2, m13 **60.0**,
  `_pg` 96.2; resized official (16 maps, 160): m12 65.6, m13 69.4, `_pg` **73.1**; fresh generated (24 maps, 240): all three 66.7 (identical games:
  same drafts, no plan fires). Head-to-head on those pools: `_pg` vs m13 88.0 (ring + contest maps) and 53.8 (pads + fresh), vs m12 60.0 and 53.8;
  m13 vs m12 50.0. Running: `_pg2` everywhere + held-out (gold, gold2, gold3, obj) vs Mite / `_px9` / ifish (`$S/pg2.sh`, then `pg3.sh`).
- **SHIPPED `legend_m13` (22:40 UTC)** = `_pd2` = `_fc` + the **parameter draft** (`experiments/wip/x_pd.patch`, `mapdraft` 6, hash c8272a7e1846; sha256 8f1ac104…).
  The user's request: analyse the map first, derive parameters, choose the first pick from them, later picks from the enemy's picks + synergy + map
  (for the final sprint, where the map pool changes). draft.cpp `derive_params()` / `pd_score()` / `param_pick()`: no per-map table. Accuracy vs the
  old hardcoded picks: official 17 x 3 enemies 51/51, generated 27/27, `maps/var17` (51 transposed / swapped copies of the official maps) 51/51
  (old 47/51). Same games as `legend_m12b` on the 88 maps (identical drafts give identical games: checked 68/68). On the 4 copies where the old
  model broke (rushbait-v2_tr/_swtr, stampede_tr/_swtr): 29/40 vs 23/40 against Mite, ifish, `_snk`, `_px9`, `_fA`. First version `_pd` (Ryth at
  size 4 whenever packs < 0.5, open map = area >= 4000 or distance >= 30) lost ifish 61.4, `_snk` 60.2: tightened to elk share >= 0.3 at size 4 and
  area >= 5000 and distance >= 30. Caveat: brain-side special plans are still gated by map size (stampede ring by 60x50, contest plan by 50x50).
- **SHIPPED `legend_m12b` (22:15 UTC)** = `_fc` = `_fw` + `mono_size50` 1 (`experiments/wip/x_m12b.patch` on `_m10`, hash 531e7331a283; sha256 5650ab96…).
  Confirmation cells of `_fw` found its held-out loss vs `_px9` (56.0 vs `_m10` 66.0) sits entirely on the 24 generated `gold_mono_*` maps (29 vs 39 of 60;
  the other 40 held-out games identical to `_m10`'s). `_fc` gates the contest plan to 50x50 maps: official games identical to `_fw` (34/34 vs Mite, 34/34 vs
  `_px9`), contest pool identical (68/68 vs `_snk`), gold_mono games = `_m10`'s (59/60), held-out vs `_px9` 65.0; rollovers 8/8. `_fw` 88-game cells:
  Mite 77.3, ifish 69.3, `_px9` 77.3, `_snk` 67.0 (all at `_m8`'s level). **New baseline: `_fc` (= legend_m12b).**
- **SHIPPED `legend_m12` (22:06 UTC; the user: "finish the bot by 4 am, best bot by as much A/B testing as possible")**: `submissions/legend.zip`
  sha256 6e33d2b5…, `submissions/history/legend_m12_20261018.zip`, BUILDS row. `_fw` = `_m10` + `experiments/wip/x_m12.patch` (hash 104743e4f1d5) =
  `_m11` + `ward_bush_maps` 1 (warding only on contest-type maps). Decision metric changed after the user's ladder report: **the top-team proxies on the
  official maps**, not head-to-head vs our own builds (m11 beat m10 67.6 official but lost to Mite 76.5 vs 82.4 and ifish 70.6 vs 79.4: non-transitive).
  Official 34: `_fw` Mite 85.3, ifish 79.4, `_px9` 76.5, `_snk` 67.6, `_fA` 88.2 (mean 79.4; `_m10` 76.5, `_m11` 74.1); identical to `_fo200` (= `_m10` +
  contest blob, no warding) on every map but contest; contest pool 88.2 / 95.6 / 97.1 vs `_m8` / `_mite` / `_snk` (`_fo200` 69.1 / 89.7 / 83.8); h2h vs `_m8`
  52.3 / 52.9, vs `_m10` 51.1 / 52.9; pace 507.6; rollovers 8/8; 0 faults. Rejected in the same hour: paired opening `pair_open_until` 150/250
  (`x_po.patch`: 64.7 vs every proxy at 150, beats `_m11` 55.9: non-transitive), ward gap 2 (38.2 vs `_m11`). **New baseline: `_fw` (= legend_m12).**

- **22:00 UTC, the user: "m11 is performing poorly on the top ladder; implement the handoff"** (`docs/strategy_v2/11_FINAL_STRATEGY_HANDOFF.md`, from an
  unpushed session 12; its zip `submissions/history/legend_final_s12_20261018.zip`, hash 3729300fd292 verified = `legend_m10` + `ward_bush=2` +
  `mono_grouped_until=300`). `legend_m11` already is that build with the contest variant the handoff prefers (`mono_follow_until` 200). Its §1-2:
  the 30 uploaded games (`experiments/intercon_oct18/`, analysis in `analysis/`) are Intercontinental Fish (ladder #1, now Stellar-first) vs 6
  teams, 25-5; IC's edge is execution: paired opening (melee bodies farm with an ally 84-93% before r200, ours 52-70%), fights opened with
  spells from 4-5, more neutral captures; copying its draft, Stellar-first order or builds lost inside our brain. Working on §5 #1 now:
  `pair_open_until` (`experiments/wip/x_po.patch` on `_m11`: before round R, off contest, bodies 1/3/5 farm the group their partner 0/2/4 claims).

- **SHIPPED `legend_m11` (S7R, ~21:55 UTC)** at the user's request ("prioritize finishing the bot so we get feedback from the actual ladder"):
  `submissions/legend.zip` sha256 1fb13fa2…, `submissions/history/legend_m11_20261018.zip`, BUILDS row. `_m11` = `_m10` + `experiments/wip/x_m11.patch`
  (source hash 0dd8010eaf12; = contest agent's `_fo200` (`mono_plan` detector + `mono_follow_until` 200) + `x_wb.patch` with `ward_bush=2`).
  `bots/legend/src` = it + the inert `LEGEND_RUNTIME_PARAMS` block (wasm byte-identical). Evidence: vs `_m8` 52.3 / 67.6 (88 distinct / official),
  83 of 86 non-contest games identical to `_wb2`'s; contest pool (68 games) vs `_m8` 88.2, `_mite` 95.6, `_snk` 97.1; `_wb2` held-out vs `_mite` 87.0
  (`_m10` 79.0), `_px9` 74.0 (66.0); gen16 rollovers 8/8. Caveat: on the 88-map pool `_wb2` scored 63.6 vs `_mite` (`_m8` 76.1): held-out reverses it.
  Held-out (100 games, warding alone `_wb2` / `_m10`): vs `_m8` 51.0, `_mite` 87.0 / 79.0, `_px9` 74.0 / 66.0, `_ifish` 83.0 / 80.0, `_snk` 86.0 / 84.0:
  better than `_m10` against every proxy on maps that were never used for selection. `_m11` on the 88: vs `_m10` 53.4, vs `_mite` 65.9.
  **Full `_m11` cells (88 distinct / official 34; `_m8`'s in brackets)**: vs `_m10` 53.4 / 67.6, `_m8` 52.3 / 67.6, `_mite` 65.9 / 76.5 (76.1 / 82.4), `_ifish`
  69.3 / 70.6 (69.3 / 79.4), `_px9` 71.6 / 79.4 (78.4 / 76.5), `_fA` 77.3 / 76.5 (73.9 / 82.4), `_ST` 85.2 / 91.2 (83.0 / 91.2); deaths lower in every cell;
  pace 505.5; rollovers 8/8. Third-party mean on the 88 is 73.9 vs 76.1 (official 78.8 vs 82.4): the ladder decides between that and the held-out gains. **New baseline: `_m11`.** Rollback: `legend_m10` zip.
  The opening-gold workflow was stopped to free CPU (its notes: `x_og_NOTES.md`; nothing passed vs the proxies).

- This container (S7's) resumed after the session limit; its agents econ / fight / contest died then. It works on: (1) **`join_marginal`**
  (agent econ's best switch: 63.4 / 55.9 vs `_m4`, never picked up by S8-S11) ported onto `_m8`: `_jm8` = `_m8` + `experiments/wip/x_jm8.patch`
  (rebuild: `SRC=bots/_m8 tools/variant.sh _jm8 && (cd bots/_jm8 && patch -p1 --no-backup-if-mismatch < ../../experiments/wip/x_jm8.patch)`;
  control `_jm8c` = `_jm8` with `join_marginal=0`: 50.0, identical games). **Rejected** (88 distinct / official 34, `_m8`'s cell in brackets): vs `_m8`
  54.5 / 47.1 (deaths 665-652); `_mite` 76.1 / 79.4 (76.1 / 82.4); **`_ifish` 58.0 / 52.9 (69.3 / 79.4)**; **`_px9` 68.2 / 55.9 (78.4 / 76.5)**; `_fA` 79.5 / 79.4
  (73.9 / 82.4); `_ST` 81.8 / 85.3 (83.0 / 91.2); `_xp4` 70.5 / 58.8 (68.2 / 79.4); third-party mean 72.4 vs 74.8 (official much worse); pace 500.9 (503.8).
  Fewer helpers on claimed camps saves walking but loses the fights the Ren-first proxies bring: a farming gain that costs contact strength.
  (2) **The user's rules (S7R, 20:30 UTC)**: "don't lose in strategy to legend_m8 while incorporating the good drafts" (every candidate needs >= 50
  head-to-head vs `_m8` and `_m10` on the 88 distinct and the official 34, and not worse vs the third parties) and "prioritize gold at the start of
  rounds so champions upgrade early". The workflow `contest-and-neutral` was stopped (neutral control had built nothing yet) and replaced by
  **`opening-gold-and-contest`** (~20:35 UTC): agent `og` (Opus) = opening economy (copy `bots/_x_og`, variants `_og*`, notes `experiments/wip/x_og_NOTES.md`,
  patch `x_og.patch`) and agent `ct` (Sonnet) = contest, continuing from `bots/_x_ct` (`experiments/wip/x_ct.patch`: the mono_* detector and switches
  ported onto `_m10`) and variants `_ct0`-`_ct5`, test maps `maps/ct/`; each ship claim then goes to an independent verifier.
  Opening evidence (sneaky games, `experiments/sneaky_oct18/analysis/body.csv`): our first emblem median Cassi r437 (theirs r250), Issac r236 (r142),
  Ryth r219 (r99), Stellar r194 (r191), Ren r66, Varg r70; gold by r150 Cassi 64 / Issac 66 (theirs 121 / 159): gold piles on Ren and Varg.
  (3) **Sneaky-bush draft** (the user's upload, 17 distinct games vs `legend_m8`/`m10`, we won 5; `experiments/sneaky_oct18/`, report in `analysis/`):
  their per-map table is `mapdraft` 4 / the `md_sneaky` bit mask (bit = OfficialMap id) in `experiments/wip/x_sn.patch` (on `_m10`; control 34/34 games
  identical). Their builds = Mite style (`build_style` 9). Proxy `_snk` = `_x_sn` + `mapdraft=4 build_style=9`; candidate `_snd` = `_x_sn` + `mapdraft=4`.
  Running: per-map screen on the 11 maps where their draft differs (collision, contest, corners, eight, elkring, interlock, monolith, rows, rushbait-v2,
  stampede, swirl), `_snd` and `_m10` vs 18 opponents both sides (`$S/sneaky_screen.sh`; `python3 tools/mapscreen.py _m10 _snd --opps ...`). First cells:
  `_snd` vs `_m10` 8/22 on those maps. **Screen done** (17 opponents x 2 sides = 34 games per map; wins `_snd` / `_m10`; top proxies `_mite _ifish _px9`):
  contest **27 / 21 (+6)**, top 3 / 4, h2h 2/2; collision 28 / 25 (+3), top 5 / 4, h2h 1/2; stampede 31 / 31; interlock 26 / 29; eight 25 / 29; corners 22 / 28;
  rushbait-v2 21 / 27; swirl 18 / 24; monolith 19 / 26; elkring 19 / 27; **rows 20 / 33**; all 256 / 300 (-44), top 34 / 53. Their draft loses inside our
  brain on 8 of 11 maps (Tavi, Willow and Vendetta are played worse by our code than the champions they replace); only contest (their caster
  draft Tavi, Willow, Stellar, Ren, Prism) and maybe collision gain. Candidates: `_sdc` (`md_sneaky=4`: contest), `_sdl` (`=2`: collision),
  **`_sdC` (`=6`: both)**; running (`$S/sdc.sh`): `_sdc` vs 10 opponents on the contest geometry variants `maps/ct/contest_{sw,tr,swtr}` (more
  contest samples), then `_sdC` full acceptance vs `_m10 _m8 _mite _ifish _px9 _fA _ST _snk` (88 distinct) and pace.
  **Contest draft rejected**: on the contest geometry variants (`maps/ct/contest_{sw,tr,swtr}`, 10 opponents, 54 games) `_sdc` won 25 vs `_m10`'s 36
  (top proxies 8 vs 11; h2h vs `_m10` 1/6): the official-map +6 is specific to that one layout. `_sdC` acceptance stopped (moot). Collision: same check
  on `maps/cl/collision_{sw,tr,swtr}` (made with `tools/mapgen/swap_sides.mjs`) for `_sdl` before any acceptance.
  **Collision draft rejected** too: 33 vs 37 wins (54 games; top proxies 10 vs 13; h2h 2/6). **Verdict: no sneaky-bush draft choice improves our bot**
  on any map once checked on more than one layout; `legend_m10`'s draft stays. `_snk` joins the sparring panel (`_m10` vs `_snk` on their 11 maps 12/22).
  A workflow `sneaky-bush-study` (Sonnet + Haiku, no games) writes `docs/strategy_v2/10_SNEAKY_BUSH.md` (bush play, same-draft losses) and checks the table.
  (4) **Opening agent `og` so far** (`experiments/wip/x_og_NOTES.md`): shop lag after the first affordable emblem is 0-1 round already (nothing to gain);
  `og_poor_collect` (poorer body collects before r400) **38.2** official vs `_m10`: gold spreads (Cassi's first emblem r200 vs r352) but team gold falls
  148.5k -> 130.7k (Ren is the fastest, Treasure-boosted collector): rejected. `og_gold_mult` 2.5 (gold x2.5 while a body owns < 150, until r300)
  **55.9** official vs `_m10` (deaths 325-369): the effect is earlier gold-cluster targets, not earlier emblems. Later: every opening variant lost
  to the proxies on the official 34 (`_og2` sum 214.7, `_og4` 208.9 and 38.6 on the 88 vs `_m10`, Jungle-first C&I 202.8, solo C&I 197.1-211.8;
  `_m10` 238.3): the gold-first opening as built so far is not a better trade (agent still working).
  (5) **Contest agent `ct` so far** (`experiments/wip/x_ct_NOTES.md`): games are bimodal: whoever wins the first centre clash (r30-60) snowballs; our
  bodies arrive one by one. Contest pool CT4 (contest + `maps/ct`, 20 games; vs `_snk` / `_mite` / `_ifish` / `_px9` / `_m8` / `_fA`): `_ct0` (= `_m10`
  play) 30/60/50/50/50/75; skip the enemy half to r150/r300 (`_ct1`/`_ct2`): worse (passivity loses); **GROUPED stance to r150 (`_ct3`)
  75/55/60/55/65/85, to r300 (`_cw1`) 70/55/70/55/65/90**. **CT34 (contest + 33 perturbed copies, 68 games)**: `mono_follow_until` 200 (`_fo200`, bodies
  follow each other as a blob until r200) vs `_snk` / `_mite` / `_ifish` / `_px9` / `_m8` **83.8 / 89.7 / 77.9 / 66.2 / 69.1** (`_ct0` = `_m10` play vs `_snk` 38.2);
  rollovers 8/8. Inertness on the 88 and the verifier still to come.
  (6) **Sneaky-bush study done** (`docs/strategy_v2/10_SNEAKY_BUSH.md`, tool `tools/strategy_v2/bush.py`; the draft-table check found 0 mismatches in 17 rows):
  their bush time 7.9% of alive body-rounds vs our 3.3% (4.8 vs 3.3 without contest; contest 21.7, eight 10.5, stampede 12.5, fragment 13.2); 23.5% of their
  champion damage comes from a bush (ours 9.0%); 48% of our champion-caused deaths had a bush hitter in the last 5 rounds (40% without contest); **all
  1,683 of their wards are on bush tiles, ours 19% when one was in reach**. But 8 of our 12 losses are income races with 0-7 deaths (ambush: banking
  carry 59.7 vs 41.4 gem-rounds per gem; expanse: they take the 120-gem far-corner groups 6 times to our 2; pilgrimage: 72% of our body time walking,
  12 of 21 group kills gold-only); outside contest 70% of the camp-gem gap is neutral camps and camps on our half. Counters proposed: C1 ward the
  bush (**testing: `ward_bush` in `experiments/wip/x_wb.patch` on `_m10`, variants `_wb1` = prefer a bush tile within 2, `_wb2` = + re-ward after 3
  rounds when a bush is in reach**; official 34: `_wb1` vs `_m10` 47.1, vs `_snk` 58.8; **`_wb2` vs `_m10` 64.7 (deaths 254-405), vs `_snk` 70.6** (`_m10` 61.8);
  control 34/34 identical. **`_wb2` full cells (88 distinct / official 34; `_m8`'s in brackets)**: vs `_m10` 52.3 / 64.7 (deaths 552-700), vs `_m8` 51.1 / 64.7;
  **`_mite` 63.6 / 70.6 (76.1 / 82.4)**, `_ifish` 70.5 / 73.5 (69.3 / 79.4), `_px9` 72.7 / 82.4 (78.4 / 76.5), `_fA` 78.4 / 79.4 (73.9 / 82.4), `_ST` 85.2 / 91.2
  (83.0 / 91.2), `_snk` 64.8 / 70.6 (`_m10` 64.8 / 61.8); pace 504.4 (503.8). Third-party mean 74.1 vs 76.1: **fails the user's rule on the Mite cell**
  (29 of 88 games flipped, 20 to losses, spread over generated maps). Open question: real cost (wards are obstacles: our re-wards may block our own
  paths) or selection bias (`_m8`'s draft choices were selected on these proxies)? Held-out check running (`$S/wbh.sh`: `_wb2` and `_m10` vs `_mite`,
  `_px9` on gold/gold2/obj, 100 games each). **Held-out (100 games, maps never used to select `_m8`)**: vs `_mite` `_wb2` **87.0** / `_m10` 79.0,
  vs `_px9` **74.0** / 66.0, h2h vs `_m10` 51.0: the 88-map Mite drop is mostly selection bias (188 games vs `_mite`: 76.1 vs 77.7; vs `_px9` 73.4 vs 71.8).
  `_wb3` (early re-ward only with an enemy near) official 34: vs `_m10` 47.1, `_mite` 70.6, `_px9` 79.4, `_ifish` 70.6: worse than `_wb2`, dropped.
  Running: held-out vs `_m8`, `_ifish`, `_snk` (`$S/wbh2.sh`), then an independent verifier. Not shipped yet. C2 bush ghost in the fight estimate, C3 contest bush-ring no-go for lone bodies (for `ct`), C5 expanse far-corner
  cycle, C6 neutral-camp scoring, C7 earlier banking on 100x100 / 50x65 maps.
- The user got the zips in chat: `legend_m8` (best measured), then `legend_m10` (current `submissions/legend.zip`, plays `legend_m8`'s games).

## S11. SESSION 11 (2026-10-18, same container as S10): read this first

- The user asked (1) whether the new bot was pushed (yes: `legend_m8`; GitHub's front page shows the default branch
  `claude/lucid-pasteur-2jiojv`, which this branch is 142 commits ahead of), (2) "push the main changes that give better tradeoffs
  into the ccr branch", then (3) **"for now first push the ideas into the bot and if they are detrimental I will notify you"**.
- The default branch: its last bot commit a25ae20 (Oct 17 merge of laughing-curie into lucid-pasteur) **does not compile**
  (`brain.cpp` calls `team_update`, `learn_observe`, `chip_passing`, `camp_in` that its headers lack). Its last coherent bot,
  the Oct 16 "round-2" bot b5d4e56 (`_r2main`), plays **8.0% vs `_m8`** (official 2.9, deaths 979-320) and 10.2% vs `_mite`.
  Its non-bot files (`docs/LADDER_LOSSES.md`, `tools/stall_audit.py`, `tools/raw_summary.py`, `tools/mapgen/replica.mjs`, 2 replica maps,
  5 ladder match JSONs) are not merged here.
- **Shipped `legend_m9`** (`submissions/legend.zip` sha256 58e567ef…, `submissions/history/legend_m9_20261018.zip`) = `_m9` = `_m8` +
  `experiments/wip/x_mi.patch` (source hash 0df32fa5ee2d; `bots/legend/src` = it + the inert `LEGEND_RUNTIME_PARAMS` block, wasm
  byte-identical). The default branch's ideas, ported onto `legend_m8`, one `mi_*` switch each, all on: `mi_health_emblem` (Durability
  health as the 2nd emblem), `mi_learn_burst` (each enemy's biggest one-round hit on us, used in `combat()` while its spells are up),
  `mi_lethal` (leave an escapable fight when such a hit would kill us), `mi_cd_slack` 1 and `mi_walk_cast` (danger map), `mi_endgame_bank`
  200, `mi_learn_fight` 1.2 (fight record caution), `mi_learn_race` (banking-rate race), `mi_island_bank` 60, `mi_recall_shop` 300,
  `mi_relaxed` (rescore with 3x limits instead of idling), `mi_two_bodies`, `mi_deny_gems`, `mi_flip_guard`, `mi_kite` (spells from
  distance 4), `mi_chip` (idle spells on camps while passing), `mi_close_in`. Not ported (we already have our own version): danger detour,
  progress-aware give-up clock, camp damage in fights, the round-2 bot's farm calibration multipliers.
- Checks before the push: control `_mi0` (all switches 0) vs `_m8` 50.0 with identical games (deaths 360-360); `_mi1` (= `_m9`) vs `_m8`
  **35.3% on the 34 official games** (deaths 371-358), 0 faults, rollovers unchanged (gen16 8/8, stampede 1/1, lanes 6/6, ambush 7 vs 6).
  **Locally the combined ideas look detrimental**; the user will judge on the ladder. Rollback: `submissions/history/legend_m8_20261018.zip`.
- **Full cells of `_m9` (ledger name `_mi1`; 88 distinct / official 34, `_m8`'s cell in brackets)**: vs `_m8` 58.0 / **35.3** (deaths
  639-711); `_mite` 63.6 / 64.7 (76.1 / 82.4); `_ifish` 51.1 / **35.3** (69.3 / 79.4); `_px9` 65.9 / 58.8 (78.4 / 76.5). **Worse than
  `legend_m8` against every third party by 12-18 points (official 18-44)**: the user was told; recommended rollback = `legend_m8`.
- The user then asked for a finished bot first ("give me a bot, then continue; I will give feedback from the ladder"). Screen so far (88 games /
  official vs `_m8`), each idea **alone** on `_m8`: `health_emblem` 47.7 / 50.0, `learn_burst` 52.3 / 52.9 (deaths 590-631), `lethal` 51.1 / 50.0,
  `cd_slack` 47.7 / 41.2, `walk_cast` 44.3 / 47.1, `endgame_bank` 48.9 / 50.0 (the other 11 not yet run). Each idea **removed** from `_m9`:
  `health_emblem` 55.7 / 38.2, `learn_burst` 55.7 / 29.4, `lethal` 58.0 / 35.3, `cd_slack` 61.4 / 47.1, `walk_cast` 58.0 / 44.1.
  Quick candidate `_bl2` (= `_m9` code, only `learn_burst` + `lethal` on; ledger cells `_bl2_vs_*`): vs `_m8` 50.0 / 52.9, `_mite` 77.3 / 88.2
  (76.1 / 82.4), `_ifish` 69.3 / 76.5 (69.3 / 79.4), `_px9` **63.6 / 61.8 (78.4 / 76.5)**, pace 503.8: not a better trade.
- **SHIPPED `legend_m10`** (`submissions/legend.zip` sha256 43d3b1ed…, `submissions/history/legend_m10_20261018.zip`) = `_m10` = `_m9` with every
  `mi_*` switch 0 (`bots/legend/src` = that + the `LEGEND_RUNTIME_PARAMS` block and a comment with the numbers: wasm byte-identical).
  It plays `legend_m8`'s games: vs `_mite` 86 / 88 games identical, vs `_px9` 87 / 88, same wins (76.1, 78.4). **New baseline: `_m10`** (= `_m8` play).
- **Per-idea screen complete** (88 distinct / official 34 vs `_m8`; `_a_<idea>` = `_m8` code + that idea alone, `_l_<idea>` = `_m9` minus it):

  | idea | alone on legend_m8 (all / official, deaths) | removed from legend_m9 (all / official) |
  |---|---|---|
  | `mi_health_emblem` | 47.7 / 50.0 (662-682) | 55.7 / 38.2 |
  | `mi_learn_burst` | 52.3 / 52.9 (590-631) | 55.7 / 29.4 |
  | `mi_lethal` | 51.1 / 50.0 (646-644) | 58.0 / 35.3 |
  | `mi_cd_slack` | 47.7 / 41.2 (668-627) | 61.4 / 47.1 |
  | `mi_walk_cast` | 44.3 / 47.1 (705-641) | 58.0 / 44.1 |
  | `mi_endgame_bank` | 48.9 / 50.0 (641-645) | 53.4 / 32.4 |
  | `mi_learn_fight` | 55.7 / 58.8 (602-662) | 47.7 / 20.6 |
  | `mi_learn_race` | 46.6 / 41.2 (660-607) | 59.1 / 38.2 |
  | `mi_island_bank` | 52.3 / 50.0 (640-651) | 56.8 / 35.3 |
  | `mi_recall_shop` | 51.1 / 50.0 (648-651) | 58.0 / 35.3 |
  | `mi_relaxed` | 46.6 / 47.1 (651-657) | 60.2 / 41.2 |
  | `mi_two_bodies` | 54.5 / 47.1 (605-693) | 47.7 / 41.2 |
  | `mi_deny_gems` | 54.5 / 61.8 (612-650) | 59.1 / 38.2 |
  | `mi_flip_guard` | 54.5 / 58.8 (631-658) | 58.0 / 50.0 |
  | `mi_kite` | 52.3 / 47.1 (645-648) | 59.1 / 50.0 |
  | `mi_chip` | 54.5 / 50.0 (610-648) | 53.4 / 32.4 |
  | `mi_close_in` | 51.1 / 50.0 (649-654) | 58.0 / 35.3 |

  Pass the first gate (>= 50 all and official vs `_m8`): `learn_fight`, `deny_gems`, `flip_guard`, `chip`, `learn_burst`. **Third parties** (88 / official;
  `_m8`: `_mite` 76.1 / 82.4, `_ifish` 69.3 / 79.4, `_px9` 78.4 / 76.5): `learn_fight` 72.7 / 82.4, 65.9 / 70.6, **65.9 / 55.9**; `deny_gems` 72.7 / 73.5,
  71.6 / 79.4, 73.9 / 73.5; `flip_guard` 73.9 / 79.4, 64.8 / 73.5, 72.7 / 70.6; `chip` 75.0 / 76.5, 70.5 / 82.4, 77.3 / 70.6 (mean -0.3: level);
  `learn_burst` 76.1 / 85.3, 68.2 / 73.5, **64.8 / 61.8**. **None passes the user's rule** (each beats our previous build head-to-head but loses to the
  outside opponents, `_px9` most): all `mi_*` stay off, `legend_m10` stays. Combination builds `_cmb2` (learn_fight + deny_gems), `_cmb3` (+ flip_guard),
  `_cmb5` (+ chip + learn_burst) were built but not played (every part is worse alone vs the third parties). Revisit only with ladder evidence.
  S7R owns opening gold, contest and the sneaky-bush draft; this session stays on the default-branch ideas.

## S10. SESSION 10 (2026-10-18 17:20 UTC, new container): read this first

- Input: the user's `INTERWIN.zip` = 29 match archives, **13 distinct games between the two top teams**, now in
  `experiments/interwin_oct18/<map>.repl26a` (analysis tables in `analysis/`: `report.md`, `teamsum.md`, `micro.md`, CSVs from
  `tools/strategy_v2/run_all.py`). 5 of them are session 9's group 7b2474db (2nd vs 1st); 8 are new (stampede, rows, fragment,
  packs x2, elkring x2, lanes). Side A = **Mite = 2nd**, side B = **ifish (Intercontinental Fish) = 1st** (by their fixed per-map drafts).
- The user's request: analyse how ifish deals with Mite and how Mite beats ifish, reverse-engineer their drafting against each
  other, map parameters and champion synergy, recreate them, and make **our ifish-like bot beat a Mite-like strategy**; no RL now;
  never ship a change that loses performance; Opus agents only for make-or-break work.
- Setup: `tools/setup_session.sh --bots` after the SDK/toolchain (all 15 hashes ok). `tools/cell.py BOT OPP [--maps]` prints a
  ledger cell (all / official / deaths / per official map, both sides).

### S10.1 Findings (ifish vs Mite, 13 games; ifish 7, Mite 6)
| Map | Mite (A) draft | ifish (B) draft | Result A-B | Deaths A-B |
|---|---|---|---|---|
| stampede x2 | Prism, Stellar, C&I, Ryth, Tavi | Stellar, Tavi, Prism, C&I, Ren | **Mite 1008-0, 1080-0** (r470, r484) | 1-2, 4-1 |
| contest | Prism, Stellar, C&I, Ryth, Tavi | Stellar, Tavi, Prism, C&I, Ren | **0-0 r2000, Mite on gold 18.2k-2.3k** | 8-97 |
| packs x2 | Ren, Stellar, C&I | Ren, Stellar, C&I | **Mite 1014-716, 1008-928** | 4-7, 8-8 |
| rushbait-v2 | Varg, Ryth, C&I, Stellar | Ren, Stellar, C&I, Ryth | **Mite 1024-920** | 8-5 |
| rows | Varg, Ryth, C&I, Ren | C&I, Stellar, Varg, Ren | ifish 990-1056 | 0-0 |
| fragment | Varg, Stellar, C&I | Ren, Stellar, C&I | ifish 132-1034 | 12-3 |
| elkring x2 | Varg, Stellar, C&I, Ryth, Tavi | Ren, Stellar, C&I, Ryth, Varg | ifish 936-1008, 666-1026 | 4-2, 8-0 |
| eight | Varg, Stellar, C&I, Ryth, Tavi | Ren, Stellar, C&I, Ryth, Varg | ifish 374-1020 | 11-3 |
| corners | Varg, Stellar, C&I, Ryth, Tavi | Ren, Stellar, C&I, Ryth, Varg | ifish 596-1030 | 7-0 |
| lanes | Varg, Stellar, C&I, Tavi, Ren | Ren, Stellar, C&I, Ryth, Varg | ifish 972-1020 | 4-0 |

- Both teams draft from a fixed per-map table (identical vs us, vs each other, vs the 3rd team; 33 games): tables in `draft.cpp`
  (`MITE`, `IFISH`, x_proxy_mi.patch). Mite: Varg-first, Tavi as the 5th on most 5-maps, Varg + Ryth on every 4-map, all casters on
  stampede/contest. ifish: our draft on 5-maps, Ryth (not Varg) on swirl/rushbait/interlock, C&I-first + Monster builds on rows/expanse.
- **How ifish beats Mite: fights on Mite's own half.** Without contest: 82 fights on Mite's half, Mite loses 39 bodies to ifish's 6
  (ifish deals 50.8k vs 39.7k there); ifish deaths 2.6 per game vs Mite 5.9. Mite's victims: C&I 34, Stellar 14, Tavi 9 (Mite's casters
  stay at base health: Cassi / Stellar / Tavi 700-750 HP at r300; ifish's Ren 1,900, Ryth 2,200). ifish's killer: Stellar 30 of 71 (Power
  focus first: PfE at r38-46). Mite opens as often (66 vs 65) and its openers out-damage (553/197 vs 467/275) but its bodies die at
  bands 2-4 (deaths per 100 body-rounds 14.6 / 10.2 / 6.4 vs ifish 4.8 / 3.2 / 3.6): health decides the trades.
- **How Mite beats ifish**: (1) stampede: all five casters ring the 6-elk + 6-gem objective from distance 4 from r54, capture 360 (split
  5 x 72) at r124, r263, r412-428: 1080 by r470-484 while ifish farms gold; (2) contest: Treasure first on every caster (Stellar gold 5.1k),
  98-9 deaths, decided on gold earned; (3) farming: more neutral captures (8.1 vs 4.2 per game), camp gems 903 vs 816; Mite's Ren / Ryth /
  Varg buy **Jungle in strength** first (packs Ren JsE r21, 10-12 captures; rushbait Ryth 16 and Varg 14 captures) and farm without heal trips.
- Mite builds (style 9 in the proxy): Jungle, Durability in the damage stat, Bruiser health, Power forever; Ren / Ryth on strength on the
  small-team maps, focus on 5-maps; Treasure first on contest. ifish builds (style 3): Bruiser + Durability health on Ren / Ryth, Power
  first on Stellar / Issac / Varg; Monster then Power on rows / expanse (style 4).

### S10.2 Proxies (frozen: `experiments/wip/x_proxy_mi.patch` on `_m7` + `x_o2.patch`)
- `_x_mt` (code, hash dfb71a28348c) = `_m7` + `x_o2.patch` + `x_proxy_mi.patch`: `official_map()` (the 17 official maps by size and camp mix),
  `mapdraft` 1 = Mite's table, 2 = ifish's; `build_style` 9 = Mite, 10 = ifish (3, or 4 on rows / expanse).
  `_mite` = `_x_mt` + `mapdraft=1 build_style=9 o2_ring=1 o2_ring_melee=1` (688b37be81e3); `_ifish` = `_x_mt` + `mapdraft=2 build_style=10` (6fde429be694).
- Calibration: `_ifish` vs `_mite` 55.9 on the official 34 (real 7-6): Mite proxy wins stampede 1080 both sides and contest 0-0 on gold
  (deaths 94-11), ifish proxy wins rows 1056-990 (the real score), eight, elkring, expanse, monolith. Good enough as sparring partners.
- `_m7` vs `_mite` **75.0 / 73.5** (deaths 593-785), vs `_ifish` **65.9 / 67.6** (703-668): inside our brain our draft and builds beat theirs
  overall. `_m7` loses to the proxies where they use a map plan we lack: rushbait-v2 (both sides vs `_mite`; both top teams draft Ryth at
  size 4), swirl B, stampede B (Mite's ring), expanse (ifish's C&I, Stellar, Varg + Monster), lanes A, elkring B.

### S10.3 Candidates and the ship (code `_x_c1` = `_x_mt` + `x_m8.patch`; control `_x_c1` defaults vs `_mite`: 86 of 88 games identical to `_m7`)
- `_cA` = `mapdraft=3` (Ryth instead of Varg on swirl / rushbait-v2 / interlock, C&I, Stellar, Varg on expanse): vs `_m7` 53.4 / 55.9; on the
  4 maps 32/40 vs `_m7`'s 22/40 against 5 third parties (rushbait 8/10 vs 3/10, expanse 10/10 vs 7/10, interlock 9/10 vs 6/10, swirl 5/10 vs 6/10).
- `_cB` = `_cA` + Mite's stampede (casters + `o2_ring=1`): stampede 11/12 vs 7/12, but **the ring also fires on ambush** (objective mode):
  -5 wins in 11 changed games. `_cR` (`o2_ring=1`, our draft): same as `_m7`. `o2_ring_melee` changes nothing.
- `o2_ring=2` = ring only on stampede. First version called `official_map()` inside `group_score`: the extra fuel changed games on 15 maps
  (fuel-floored group scoring is chaotic), net -14 outside stampede. **Gate by `W.W == 60 && W.H == 50` (no host call)**: only stampede
  and fuel noise change (`_cS2`). Swirl with Ryth: 6/12 vs 7/12 and 90 rounds slower unopposed -> swirl keeps our draft (`_cS3`).
- **SHIPPED `legend_m8` (18:10 UTC)** = `_cS3` = `_m8` (source hash 540e17bfe5a4; zip sha256 710bc048…, `submissions/history/legend_m8_20261018.zip`;
  `bots/legend/src` = `_cS3` + the inert `LEGEND_RUNTIME_PARAMS` block: **wasm byte-identical to `_cS3`**). 88 distinct / official 34:
  vs `_m7` **53.4 / 55.9** (deaths 641-653), held-out 48.0 (inert there: 85 of 100 games identical to `_m7`'s vs `_xp4`); `_mite` 76.1 / 82.4
  (`_m7` 75.0 / 73.5), `_ifish` 69.3 / 79.4 (65.9 / 67.6), `_px9` 78.4 / 76.5 (73.9 / 67.6), `_fA` 73.9 / 82.4 (70.5 / 73.5), `_xp4` 68.2 / 79.4
  (63.8 / 70.6), `_ST` 83.0 / 91.2 (78.4 / 82.4); changed maps 44/48 vs 26/48; pace **503.8** (520.9; stampede 471/479 vs 704/765); 0 faults;
  rollovers unchanged. Ledger rows under `_cS3_vs_*` and `_m8_vs_*`. **New baseline: `_m8`** (`tools/setup_session.sh` rebuilds it, `_mite`, `_ifish`).

### S10.4 The user's requests after the ship (message 2 of session 10) and what is left
- Shop when **near our spawn** (not only on it), **emblem order by benefit to the team** (e.g. Stellar's damage first if it clears camps
  faster), win efficiently (reach 1000 first) rather than by dominance, champions play for the team, small changes only, and **judge every
  change head-to-head against the previous bot** (`_m8`). Code base `_x_c2` = `_x_c1` + `shop_near_*`, `gold_rank`, `dmg_first` (all off;
  control `_sn0`/`_gr0` vs `_m8` 50.0, deaths 653-653: inert). Results (88 distinct / official 34 vs `_m8`):
  - shop within 2 / 3 / 4 steps of spawn with 60 / 90 / 120 gold (`_sn2/3/4`): 50.0 / 48.9 / 50.0; it changes only 7 / 6 / 1 games:
    `shop_trip` (150 gold within 9 steps) and recall-to-shop already cover it. Not shipped.
  - reward to the better gold user (`gold_rank` 1: Stellar, Varg, Cassi, Issac, Ryth, Ren instead of the lower index): 48.9 / 44.1, pace 506.5;
    Stellar only (`gold_rank` 2): 47.7 / 47.1. Rejected.
  - Monster (camp damage) emblem first: Ren (`dmg_first=1`) 54.5 / 41.2; Ryth (`16`) 53.4 / 52.9, pace 498.4, but vs third parties
    `_mite` 72.7 (76.1), `_ifish` 67.0 (69.3), `_px9` 72.7 (78.4), `_xp4` 63.6 (68.2), held-out 48.0: noise; both 46.6 / 41.2. Rejected.
    Stellar, Cassi, Issac and Varg already buy Monster in the damage stat first.
  - Per-map screen of Mite's and ifish's whole draft tables (`_mdM`, `_mdI`, official 17 vs 7 opponents): no map better than `_m8` beyond +-3 of 14.
  - Doc: `docs/strategy_v2/09_IFISH_VS_MITE.md`.
- Fight switches re-screened vs `_m8` (`_fs_*`, 88 distinct / official): burst_exit 1 / 2 47.7 / 47.1 both; spread_vs_splash 1 53.4 / 50.0,
  2 50.0 / 47.1; **strike_first 1 59.1 / 61.8**, 3 45.5 / 47.1; pair_space 1 / 2 47.7; support_v2 51.1 / 47.1; engage_angle 46.6 / 41.2;
  open_first 1 50.0, 3 48.9. Confirmation of the two best (third parties, `_m8`'s cell in brackets): strike_first 1: `_mite` 69.3 (76.1),
  `_ifish` 64.8 (69.3), `_px9` 64.8 (78.4), `_fA` 72.7 (73.9), `_ST` 79.5 (83.0), `_xp4` 64.8 (68.2), held-out vs `_m8` -> 188 games 50.0:
  **non-transitive (beats our previous build, loses to everyone else, the Mite proxy included): rejected**. spread_vs_splash 1: 188 games 54.3,
  third parties -2 to -8 except `_xp4` level: rejected.
- Draft (the user's message 3): safest pick first, counter the enemy's visible picks (`current_draft(team::enemy)` returns the completed
  rounds, so our last pick sees their first 3-4), then the map. Screen (`last_pick`, `last_pick_size`; `tools/pickscreen.py`): 5th pick on
  5-champion maps vs Varg-first (`_mite`, `_px9`) / Ren-first (`_ifish`, `_fA`): **Ryth (ours) 76 / 71**, Marcella 59 / 65, Prism 58 / 63,
  Vendetta 58 / 62, Tavi 56 / 48 (h2h vs `_m8` 47.7-50.0, Tavi 39.8). 4th pick on 4-maps: Varg (ours) 75 / 75, Ryth 58 / 58 (45.5 h2h).
  No counter beats the current picks against either profile: **not adopted; documented in README ("Options measured in session 10")**
  as a future option. Test code for all session-10 switches: `experiments/wip/x_s10_tests.patch` (on `_cS3` sources).
- ifish-style pressure (`_eh6` enemy_half_penalty 6, `_fm12` fight_margin 1.2; on `_cS3`): vs `_m8` 51.1 / 47.1 and 51.1 / 52.9; `_eh6` vs `_mite`
  70.5 (76.1); `_fm12` vs `_mite` 77.3 / 88.2 but `_ifish` 63.6 (69.3), `_px9` 70.5 (78.4). Not adopted (README options table).

### S10.5 CURRENT STATE (20:10 UTC) and WHAT IS LEFT (priority order)
**Shipped: `legend_m8`** (`submissions/legend.zip`, sha256 710bc048…). Baseline for every new change: `_m8` (= `_cS3`), with `_mite` / `_ifish`
as the top-team proxies next to `_px9`, `_fA`, `_ST`, `_xp4`, `_m7`. Rule used all session (the user's): judge every change head-to-head against
the previous bot, and keep it only if it is also not worse against the other opponents (a change that only beats our own previous build is
rejected: `strike_first`). Nothing below is running.
1. **Ladder check of `legend_m8`** (the user): upload the zip, queue match groups vs the top 3 (Mite and ifish especially) on all 17 maps,
   send the zips; then `tools/strategy_v2/run_all.py`, `teamsum.py`, `micro.py` as in S9 and compare with doc 08 / doc 09.
   Watch stampede (we now play Mite's caster ring: should capture the 360 group from ~r124), rushbait-v2, interlock, expanse.
2. contest (spawn-camped on the ladder; locally `_m8` wins 8 of 12): no-feeding opening and gold for the tiebreak (S9 item 4).
3. Neutral control under opposition (S9 item 5); gold routing was tried here and lost.
4. If the ladder shows a new enemy draft profile, re-run the counter-pick screen (`last_pick`, `tools/pickscreen.py`) against a proxy of it.
5. Gem-race endgame / altar denial (S7 task 6), Part C draft-time map plan (S9 item 9).
- Still open from S9: contest (spawn-camped), neutral control / gold routing, gem-race endgame, fight micro re-tests vs the new proxies.

## S9. SESSION 9 (2026-10-18 15:15 UTC, new container): read this first

- Inputs: two zips from the user: **top 3 vs each other** (3 match groups, 15 games: `experiments/ladder_top3/`, replays in `repl/`)
  and "our fight with top 3" (= the same 3 groups as `experiments/ladder_m5/top4`, played by `legend_m5`; nothing new).
  The user's requests: continue AGENTS.md's open list by priority, recreate the top teams' strategies in our bot without making it
  worse than `legend_m6`, Opus agents only for make-or-break work (Sonnet/Haiku otherwise), push every better bot first,
  update this file at every step, no RL bundle this time. After the main tasks: look at our games vs the top 3 again.
- Setup: `tools/setup_session.sh` (all hashes ok). Games are fast here: 34 games in 11 s at 4 jobs.
- **Findings** (doc `docs/strategy_v2/08_TOP3_VS_TOP3.md`):
  1. Teams by draft: 23206e46 = 3rd (A) vs 1st, 7b2474db = 2nd vs 1st, c47bab28 = 3rd vs 1st. Top-vs-top games are farming
     races with 0-22 deaths; their opposed finish beats our unopposed pace on expanse, lanes, monolith, stampede. Contest is a
     massacre for the weaker side (1st loses it to both, 98-9 deaths).
  2. **Spells are 72-82% of champion damage between top teams** (ours 48%), cast from distance 4-5: area spells (radius 1 at
     range 4) reach 5. Our danger map treats every spell as reach 4; at distance 5 we deal 3 and take 12 per body-round.
  3. **The opener wins**: first hit of a fight -> 391 vs 58 damage in 3 rounds (top vs us); they open 129 fights to our 74.
  4. **Cassi focus at r300: ours 70 (health-first build), theirs 195-248**; Issac strength 47 vs 77-108. 3rd team: Treasure,
     Jungle, Durability emblems **in the damage stat**, one Bruiser health, then Power forever; 2nd: Jungle (damage stat) first.
     Gold: our Ren takes 35-38% of capture gold; 3rd's Stellar 33% + Cassi 27%.
- Tools added: `tools/strategy_v2/teamsum.py` (named-team per-champion summary), `micro.py` (distance bands, hit ranges, openers).
- Agents started 15:25 UTC (baseline `_xp4`, rules `experiments/wip/AGENT_RULES.md` session-9 block):
  `fight2` (Opus, high): area reach 5, cast-first openers, no idling at 4-5 from ready casters; copy `bots/_x_f2`, variants `_f2*`,
  notes `experiments/wip/x_f2_NOTES.md`, patch `x_f2.patch`.
  `econ2` (Sonnet, high): 3rd/2nd-team builds, Cassi focus, gold to casters; copy `bots/_x_e2`, variants `_e2*`, notes `x_e2_NOTES.md`, patch `x_e2.patch`.
- **SHIPPED `legend_m7` (16:40 UTC)** = `_m7` (= coordinator's `_c9a`) = `_xp4` + `experiments/wip/x_m7.patch` (fight2's `x_f2.patch` code with
  `aoe_cast5=3`, plus `ci_health_first=0`); source hash 61dd9019869d, zip sha256 ee467569…, `submissions/history/legend_m7_20261018.zip`;
  `bots/legend/src` = `_m7` + the inert code (build_style 3/4, LEGEND_RUNTIME_PARAMS; checked: legend vs `_px9` on the 34 official games =
  `_m7`'s ledger rows exactly). 88 distinct / official 34: vs `_xp4` **65.9 / 70.6** (deaths 649-709), held-out **62.0**; `_px9` 73.9 / 67.6
  (`_xp4` 58.0 / 64.7), `_fA` 70.5 / 73.5 (72.7 / 82.4), `_ST` 78.4 / 82.4 (73.9 / 82.4), `_f2q` 53.4 / 41.2 (44.3 / 41.2); pace 520.9; 0 faults;
  rollovers 8 per team (r1-3). Ledger cells are under both names (`_c9a_vs_*`, `_m7_vs_*`). **New baseline: `_m7`.**
  Parts alone on `_xp4`: `_f2c` (aoe_cast5=3) 54.5 / 58.8, held-out 60.0; `_e2h0` (ci_health_first=0) 58.0 / 58.8, held-out 54.0.
- Agent results: `econ2` done (notes `x_e2_NOTES.md`): every top-team build order loses inside our brain (style 7 = 3rd team 34.1%, style 8 =
  2nd team 47.7%, Cassi focus-before-health 39-44%); only `ci_health_first=0` wins. Gold routing (E4) not attempted. `fight2` (notes
  `x_f2_NOTES.md`): F2 area casts from 5 win; F1 (counting enemy areas as reach 5 in the danger map / fight triggers) loses (42.0): bodies flee
  from 5; F3 holds at the edge lose again (46.6). Built the reach-5 proxy `_f2q`. `obj2` (Sonnet) started 16:30 on the stampede objective
  (top teams start its 360-gem group at r54, we at r175; loosening obj_clear_max/obj_absorb alone did not help).
- Session 8's `evade` and `neutral` agents pushed nothing (no notes in git): their tasks are folded into `fight2` / `econ2`.

### S9 CURRENT STATE (16:50 UTC) and WHAT IS LEFT TO DO (in priority order)

**Shipped: `legend_m7`** (`submissions/legend.zip`, sha256 ee467569…; frozen copy `bots/_m7`, rebuilt by `tools/setup_session.sh`).
**Baseline for every new change: `_m7`.** Its gains are local only: it has **not** played the ladder yet (neither has `legend_m6`).

| # | Task | Who | State |
|---|---|---|---|
| 1 | **Ladder check of `legend_m7`**: upload `submissions/legend.zip`, queue match groups vs the top 3 (and a few teams ranked 30-100, our real neighbours), rotate all 17 maps, send the zips. Then `python3 tools/strategy_v2/run_all.py DIR ZIPS...`, `python3 -I tools/strategy_v2/micro.py --skip contest DIR/dmg=*:us:them`, `python3 -I tools/strategy_v2/teamsum.py --skip contest DIR/out=*:us:them`; compare with `experiments/ladder_m5/top4/micro.md` and doc 08: spell damage at distance 5 (was 8%), distance-5 band dealt/taken (was 3 / 12), openers (74 vs 129), Cassi focus at r300 (70 -> ~125 locally), deaths (6.7 per game vs 3-5), wins. Roll back to `submissions/history/legend_m6_20261018.zip` only if the KPIs get worse | the user | waiting for match groups |
| 2 | **Fight micro on top of `_m7`** (agent `fight2`, Opus, running): F4 opener coordination and any F-rule left, rebased onto `_m7`; judge vs `_m7` (88 distinct + official), `_f2q`, `_px9`, `_fA`, `_ST`, pace. Notes `experiments/wip/x_f2_NOTES.md` | agent fight2 | running |
| 3 | **Objective maps** (agent `obj2`, Sonnet, running): start stampede's 360-gem group early like the top teams (r54, tank in front, casters at range 3-4, one body farms gold; we start r175, pace 732), check other obj_mode maps. Notes `experiments/wip/x_o2_NOTES.md`, patch `x_o2.patch` (cut vs `_xp4`: re-test on `_m7`) | agent obj2 | running |
| 4 | **contest** (lost every ladder game, spawn-camped from r100-200; 2nd and 3rd do the same to 1st): no feeding (do not walk out alone into their camp), gold income for the tiebreak, monolith only with the whole team. Detector `mono_mode` in `experiments/wip/x_contest.patch` (session 7). obj2 may leave an analysis | next agent (Sonnet) | not started |
| 5 | **Neutral control and gold routing**: under opposition our neutral captures fall to 2.6 per game (top teams 7-10) and 34% of our neutral kills have 2+ bodies near (theirs 63-75%); our Ren takes 35-38% of capture gold, the 3rd team's Stellar + Cassi 60%. econ2 did not try routing (E4). Unopposed pace (`ledger.py run BOT idle`) is the fair first test | open | not started |
| 6 | **A better sparring proxy**: `_f2q` (= `_px9` + reach-5 area casts) is the closest so far (`_xp4` beat it only 44.3%). Next: `_f2q` + `ci_health_first=0` + the 1st/3rd draft (8,4,3,0,9), so the proxy has the top teams' Cassi and openers | coordinator | not started |
| 7 | Re-test the fight switches kept off against `_f2q` (doctrine `burst_exit`, `spread_vs_splash`, `strike_first`, `pair_space`, `support_v2`, `engage_angle`; S7 fight `fight_mem`, `pair_pool`, `kill_reach`, `fight_smooth`, `flee_fail_turns`, `flee_hold`; fight2 `aoe_reach5`, `open_first`): they were judged against opponents that never cast from 5 | open | not started |
| 8 | Builds: the full top-team orders lose inside our brain (34-48%, session 9); re-test only after fights change (e.g. Cassi focus beyond `ci_health_first=0`: theirs 195-248 at r300, ours ~125) | open | parked |
| 9 | Part C draft-time map plan (zones, circuits; `tools/strategy_v2/map_plan.py`), gem-race endgame (S7 task 6), altar denial | open | not started |
| 10 | A100 RL re-run on `legend_m7` (`tools/rl/a100/run_a100.sh`): the user said not now (session 9) | the user, later | parked |

Rules that held: distinct maps only (`'maps/*.map26a,maps/comp/*.map26a'`, 88 games; never `maps/ladder`), every game through `tools/ledger.py`,
ship only with >= 50 vs the baseline on all and official, not worse vs the third parties (mean), pace within 10, 0 faults, no new rollovers;
push the zip first, then continue. Local KPIs of any match-up: `tools/strategy_v2/kpi_local.sh BOT OPP OUT`.

## S8. SESSION 8 (2026-10-18 13:00 UTC, new container): read this first

- Inputs: the A100 RL results (`rl_a100_results_20261018_1821_0f32bbb`, same files as `tune_out/a100/`; trained on the user's laptop:
  18 cores, RTX 5070, cambc 2.2.2, 35 generations, 45,322 games, commit 0f32bbb = **`legend_rm` code**, not `legend_m4`), the strategy-v2 plan
  (`docs/strategy_v2/`, candidate `submissions/candidates/legend_exec_20261018.zip` = `_rm` + `x_exec`). The user's "analysis.md" did not arrive
  (only the two zips). Both session-7 sessions have stopped; their agents (econ, fight, contest) are gone; their notes are the handoff.
- **RL result**: tournament (142 cases x 2 sides): best `_t4` (gen 32 mean vector) reward +0.527, win 0.768 vs the defaults +0.243 / 0.687;
  validation of `_t4` (official 17): `_rm` 70.6, `_ST` 55.9, `_eA` 50.0, `_eB` 94.1, `_eC` 85.3, `_eD` 85.3. Parameters that moved consistently
  (share of generation steps in the final direction >= 0.7, move >= 12% of the range): `deficit_defend` 1->3, `race_margin` 40->73,
  `isolated_flee_adv` 1.1->1.5, `flee_dist` 7->5, `tribute_min` 34->54, `bank_trip_w` 1->1.74, `backup_radius` 8->5, `kill_gems` 25->40,
  `ctx_invaded` 0.6->0, `threat_memory` 4->7, `reserve_margin` 0.5->0.33, `cap_recall_gold` 90->60, `fight_learn_rate` 0.235->0.33,
  `max_wait` 18->14, `target_threat_adv` 1.3->1.49, `cornered_margin` 0.63->0.74, `isolated_fight_adv` 1.43->1.23. `max_join` (range 0-1 in
  that run) is left at `_m4`'s 3. Analysis script: `tools/rl/a100/analyze_run.py` (to be committed).
- Variants under test (ledger, 44 distinct maps = `maps/*.map26a` + `maps/comp`, no ladder copies; then pace vs `idle`, then `_fA`, `_ST`):
  `_m4x` = `_m4` + `x_exec.patch`; `_m4r` = `_m4` + every RL value (not `max_join`); `_m4c` = `_m4` + the consistent subset;
  `_m4xr`, `_m4xc` = `_m4x` + the same. Rebuild: `SRC=bots/_m4 tools/variant.sh _m4x && (cd bots/_m4x && patch -p1 < ../../experiments/wip/x_exec.patch)`,
  then `SRC=bots/_m4 tools/variant.sh _m4r $(cat experiments/wip/rl_a100_all_args.txt)` (args files committed next to the patches).
- **Round 1 results (13:40 UTC; 88 distinct games per cell; all / official 34 / deaths ours-theirs)**:

| Bot | vs `_m4` | vs `_fA` | vs `_ST` | pace (official 17) |
|---|---|---|---|---|
| `_m4` (shipped) | - | 63.6 / 64.7 / 731-787 | 73.9 / 70.6 / 654-817 | 524.5 |
| `_m4x` (+ x_exec) | 48.9 / 41.2 / 668-572 | 64.8 / 73.5 | 64.8 / 64.7 | 524.5 |
| `_m4r` (+ all RL) | 47.7 / 32.4 / 433-513 | 54.5 / 44.1 | 61.4 / 61.8 | 528.6 |
| `_m4c` (+ consistent RL) | 51.1 / 50.0 / 530-595 | 67.0 / 70.6 | 70.5 / 79.4 | 538.1 |
| `_m4xr` | 50.0 / 44.1 / 439-572 | 60.2 / 55.9 | 70.5 / 67.6 | 528.6 |
| **`_m4xc`** (+ x_exec + consistent RL) | **55.7** / 47.1 / 559-625 | **70.5 / 79.4** / 610-975 | **80.7 / 91.2** / 507-929 | 538.1 |

  The full RL vector (tuned on `_rm`) does not transfer to `_m4` (its fight values undo the survive patch); x_exec alone does not either.
  Together, x_exec + the consistent RL subset is the best against every third party. Pace cost +13.6 (pilgrimage +72, ambush +55,
  expanse +45): drop-one pace screen `_pc_*` (= `_m4c` minus one farm param) running. A100 trainer updated for the next run:
  `max_join` range 1-4 (was 0-1, which would clip `_m4`'s 3), `_m4` built from its history zip and added to `official_vs_frozen` and validation.
- **SHIPPED `legend_m5` (13:45 UTC)** = `_m5a` = `_m4x` + 16 consistent RL values (all but `max_wait`: the drop-one pace screen `_pc_*` showed
  `max_wait` 14 alone cost 14 rounds; without it pace 523.4). `submissions/legend.zip` sha256 efea8ec2…, `submissions/history/legend_m5_20261018.zip`,
  source hash 5620bb02867a (`tools/setup_session.sh` rebuilds `_m4x` and `_m5a`). 88 distinct games / official 34: vs `_m4` **61.4 / 58.8** (deaths 565-673),
  `_fA` 76.1 / 79.4, `_ST` 73.9 / 91.2, `_eA` 68.2 / 76.5, `_rm` 65.9 / 76.5, `_m2` 53.4 / 55.9, `_eB` 77.3 / 94.1, `_eC` 87.5 / 88.2 (mean of the 7
  third parties 71.8; `_m4` 70.0); 0 faults; gen16 rollovers 8 per team (rounds 1-3). `bots/legend/src` = `_m5a` + the inert 78c32bf code.
  **New baseline for every agent: `_m5a`.** Held-out (gold, gold2, obj; 100 games) vs `_m4`: **59.0** (deaths 1707-2144).
- **Agent `top` done (14:30 UTC)**: `bots/_top` (from starter-cpp, `experiments/wip/x_top.patch`, notes `x_top_NOTES.md`; rebuild:
  `mkdir -p bots/_top && cp -r bots/starter-cpp/* bots/_top/ && cp bots/legend/.gitignore bots/_top/ && (cd bots && patch -p0 < ../experiments/wip/x_top.patch)`,
  source hash a629b67deee1). Top-style fight order and damage builds (28.4 damage points per 1000 gold, hit-back gap 0.62) but a weak economy:
  pace 827 (objective maps never cleared), 12.6 deaths per game; `_m4` beats it 91.2% (official), `_m5a` 100%. **Not a realistic stand-in**:
  use it only as an extra sparring partner, never as evidence about the real top teams. The pressure archetype `_fA` stays the main proxy.
- **Part B screen on `legend_m5` (15:10 UTC)**, variants of `bots/legend` (= `_m5a` + inert code; control `_L5c` vs `_m5a` 50.0, deaths 318-318: identical play).
  88 distinct games / official 34, then pace: `build_style 3` (`_L5b3`) vs `_m5a` 46.6 / 41.2, vs `_fA` 70.5 (`_m5a` 76.1), pace 564.5 (contest 1045 -> 1463);
  top draft Varg, Stellar, C&I, Ryth, Ren (`_L5d`, `LEGEND_DRAFT 9,4,3,0,8`) 51.1 / 52.9, vs `_fA` 62.5, pace 529.5; both (`_L5b3d`) 45.5 / 35.3, `_fA` 63.6, pace 570.5.
  **Still no gain from the top teams' builds or draft, now with x_exec in the brain**: rejected again. Builds would need faster kills and a
  contest plan first (style 3 cannot clear contest's monolith: no health).
- **Agent `doctrine` done (16:00 UTC)**, notes `experiments/wip/x_doc_NOTES.md`, patches `x_doc.patch` (vs `_m4`) and `x_doc_m5.patch` (vs `_m5a`); switches
  all off by default: `camp_in_fight` (A5), `spread_vs_splash` (A4), `burst_exit` (A7), `strike_first` (A6), `pair_space` (A9), `support_v2` (A3), `engage_angle`.
  Nothing beats `_m5a`: best `_xm5c` (`camp_in_fight=3`) vs `_m5a` 51.1 / official 44.1, held-out 49.0, `_fA` 75.0 / 82.4, `_ST` 75.0 / 88.2, pace 521.8
  (on `_m4` the same switch was +6.8: x_exec + RL already take those fights). burst_exit, strike_first, spread, pair_space, engage_angle: noise or worse;
  combinations do not add. Diagnosis: the ladder gap (fight deaths 183-34, hit-nobody-back 75% vs 50%, 53% burst deaths) does not exist in our sparring
  (`_m4` vs `_fA`: 68% vs 63%, damage ratio 0.88), so local tests cannot rank rules aimed at it. `_xm5c` zipped as a ladder A/B candidate
  (`submissions/candidates/legend_m5_campfight_20261018.zip`).
- **Conclusion of session 8**: local sparring is exhausted for fight rules; the next signal must come from the ladder (match groups of `legend_m5`,
  and optionally the campfight candidate, vs the top 3) and from an A100 run on `legend_m5`. Open, not started: Part C draft-time plan / zone farming,
  Part D contest single-monolith plan, gem-race endgame (S7 task 6).
- **Ladder (evening): `legend_m5` vs the top 3, 60 games (51 distinct): 5 wins** (doc `docs/strategy_v2/07_LADDER_M5_18OCT.md`, data
  `experiments/ladder_m5/`). Burst deaths 52-69% of ours (theirs 17-26%), ranged kills 56-61%, Stellar the top killer, neutral captures 3-4x
  fewer, half their camp gems, bags at the end equal (banking is not the gap), contest spawn-camped (55-84 deaths).
- **Agent `proxy` (Opus) done**: notes `experiments/wip/x_px_NOTES.md`. Proxy `_px9` = legend@61fdce4 + `x_px.patch` + `px_mode=2` + draft
  9,4,3,0,8 (2nd team's): our economy, top-team targeting. Beats `_m5a` 64.7 (official), burst share of our deaths 46%, neutral captures 39 vs 76;
  death ratio only 1.2x (ladder 2.7x): partly calibrated. Finding: the top teams avoid being hit more than they out-damage (on the ladder
  `_m5a` deals 5.5k champion damage per game and takes 13.4k; locally it deals ~19k). More aggressive proxies all lost (6-50%).
- **SHIPPED `legend_m6` (15:30 UTC)** = `_xp4` = `_m5a` + `x_pxfix.patch` + `px_mode=2 camp_in_fight=3` (source hash 6a1a52e4ddb8; zip sha256
  8f62a7c5…, `submissions/history/legend_m6_20261018.zip`; `bots/legend/src` = `_xp4` + inert code; setup script rebuilds `_px9`, `_xp4`).
  vs `_m5a` 52.3 / 61.8 (deaths 580-710), held-out 59.0 (188 games: 55.9); vs `_px9` 64.7 (`_m5a` 35.3); `_fA` 72.7 / 82.4, `_ST` 73.9 / 82.4,
  `_eA` 71.6, `_eB` 79.5, `_eC` 88.6, `_m4` 53.4 / 47.1 (third-party mean 73.3 vs `_m5a` 74.1: level); pace 521.9; 0 faults; rollovers 8 (r1-3).
  Not helping on top: `burst_exit` (58.8 = no gain), stun-first and ally-spell ablations. **New baseline: `_xp4`.**
- Agents of session 8 (all finished, nothing running): `top` (Sonnet: `bots/_top`, `x_top_NOTES.md`), `doctrine` (Opus: fight switches A3-A9,
  `x_doc_NOTES.md`, `x_doc.patch`, `x_doc_m5.patch`), `proxy` (Opus: `_px9` proxy and the `legend_m6` fix, `x_px_NOTES.md`, `x_px.patch`, `x_pxfix.patch`).

### S8 CURRENT STATE (16:00 UTC) and WHAT IS LEFT TO DO

**Shipped: `legend_m6`** (`submissions/legend.zip`, sha256 8f62a7c5…; frozen copy `bots/_xp4`, rebuilt by `tools/setup_session.sh`).
Baseline for every new change: `_xp4`. Its gains are local only: it has **not** played the ladder yet.

Left to do, in priority order:

1. **Ladder check of `legend_m6` (the user)**: upload `submissions/legend.zip`, queue match groups vs the top 3
   (`cambc match-groups create <TEAM_ID> --maps ...`, rotate all 17 maps; keep eight, swirl, fragment, collision, elkring, contest in rotation),
   send the zips. Then: `python3 tools/strategy_v2/run_all.py DIR ZIPS...` per team, `python3 -I tools/strategy_v2/bags.py SCRATCH`,
   compare with `docs/strategy_v2/07_LADDER_M5_18OCT.md` (wins 5/60, deaths ~200-60 per 20 games, burst share 52-69%, neutral captures 41-54 vs
   147-168, camp gems 0.5x). Keep `legend_m6` only if the ladder KPIs are not worse than `legend_m5`'s; else roll back to
   `submissions/history/legend_m5_20261018.zip`. Optional A/B candidate: `submissions/candidates/legend_m5_campfight_20261018.zip`.
2. **A100 RL re-run on `legend_m6` (the user)**: `nohup bash tools/rl/a100/run_a100.sh --hours 2.5 > a100.out 2>&1 &` on this commit (it trains
   `bots/legend` = `legend_m6`; frozen opponents now `_ST`, `_m4`, `_m5`, `_self`; `max_join` range 1-4). When the archive comes back: analyse it with
   `python3 tools/rl/a100/analyze_run.py RUN_DIR`, apply only the parameters that moved consistently (session 8: the full vector did not transfer, the
   consistent subset did), screen each farm parameter on pace (session 8: `max_wait` alone cost 14 rounds), then the usual cells vs `_xp4`, `_px9`, `_fA`, `_ST`.
   Add `_px9` (proxy) to the A100 suite once its recipe is in `run_a100.sh` (it needs `x_px.patch` on legend@61fdce4).
3. **Avoid being hit (biggest open fight lever)**: on the ladder `_m5a` dealt 5.5k champion damage per game and took 13.4k (locally ~19k dealt);
   52-69% of our deaths are bursts from above 60% health, mostly ranged (enemy Stellar: stun + 2.0x focus from range 4, then focus fire).
   Work: do not stand in an enemy's next-turn reach (attack range, or 4 with a damage/stun spell up) unless we hit this turn; ranged bodies move
   out then attack (dash/move then attack works, attack then move does not); melee enter-hit-leave; leave Stellar's range-4 cast reach when its
   spell is up and our health is below its burst plus its allies' hits. Judge against `_px9` first, then the usual guard cells vs `_xp4`.
   Improve the proxy too (its death ratio is 1.2x, the ladder's 2.7x): a proxy that avoids hits like the top teams is the better sparring partner.
4. **Neutral control / farming income**: the top teams take 3-4x our neutral captures and collect 2x our camp gems; our Issac earns 280 gold vs their
   1,060 (gold piles on Ren: 1,724 per game unopposed). Ideas: contest neutral groups when the local power estimate allows (the `race_mode` deny
   logic is the start), collector rank (gold to Varg/Issac/Stellar, strategy v2 B2), Part C draft-time plan with zones and circuits
   (`tools/strategy_v2/map_plan.py` prototype, spec in `03_IMPLEMENTATION_SPEC.md` §3). Unopposed pace (`ledger.py run BOT idle`) is a fair test for this part.
5. **contest map** (lost every time, 55-84 deaths: spawn-camped from r100-200; vs 2nd it went to r2000 at 0-0 and was lost on gold earned 2.6k vs 19.8k):
   the contest agent's detector `mono_mode` (`experiments/wip/x_contest.patch`, notes `x_contest_NOTES.md`) fires only there; needed: no feeding
   (stay off their spawn-camp path, regroup before walking out), gold income for the tiebreak, a monolith attempt only with the whole team.
6. **Builds / draft (Part B)**: still rejected inside our brain (session 8 on `legend_m5`: `build_style 3` 46.6 and pace +41, top draft 51.1, both 45.5).
   Re-test only after items 3-4 change how fights and farming go.
7. **Gem-race endgame** (S7 task 6, not started): close finishes, altar denial (a stun cancels a tribute; probes in ENGINE_FACTS "Session 5 probes").
8. Switches kept off in the code for later tests against a realistic opponent: `burst_exit`, `spread_vs_splash`, `strike_first`, `pair_space`,
   `support_v2`, `engage_angle` (doctrine), `fight_mem`, `pair_pool`, `kill_reach`, `fight_smooth`, `flee_fail_turns`, `flee_hold` (S7 fight),
   `join_marginal`, `claim_release` (S7 econ).

**Update 16:40 UTC**: 3 more ladder groups ("top 4", 15 games, `experiments/ladder_m5/top4/`, addendum in doc 07): 2 wins; same gaps
(neutral captures 63 vs 192, damage per gold 20.6 vs 29.4, burst deaths 43% vs 16%); 3 games replay identically to the `legend_m5`
groups, so those were played by the same build. Agents started on items 3 and 4 (both Opus, baseline `_xp4`, judged vs `_px9` + guards):
`evade` (avoid being hit; copy `bots/_x_ev`, variants `_xv*`, notes `experiments/wip/x_ev_NOTES.md`, patch `x_ev.patch`) and
`neutral` (neutral control, income, damage per gold; copy `bots/_x_nt`, variants `_xn*`, notes `x_nt_NOTES.md`, patch `x_nt.patch`).

Rules that held this session: test on distinct maps only (`'maps/*.map26a,maps/comp/*.map26a'`, 88 games; never `maps/ladder` copies), every game
through `tools/ledger.py`, ship only with >= 50 vs the baseline on all and official, not worse vs the third parties, pace within 10, 0 faults,
no new rollovers; push the zip first, then continue.

## S7. SESSION 7 (2026-10-18, new container): read this first

- Setup in a new container: **`tools/setup_session.sh`** (SDK, toolchain, and `_rm _ST _eA _eB _eC _m2 _m3` rebuilt with the exact sources of their
  ledger rows; it prints each source hash and `ok`). Do not run it while a ledger run is playing (it rebuilds the bots).
  Recipes it encodes: `_rm` = legend@60d9930; `_ST` = legend@cd4e2aa; archetypes = `_rm` + the brain.cpp part of 78c32bf (`build_style` 3/4,
  no `LEGEND_RUNTIME_PARAMS`), then `tools/make_archetypes.sh`; `_m2` = `_rm` + `x_farm.patch` and `x_survive.patch` as of cbe612b.
- **Shipped `legend_m2`** (`submissions/legend.zip` sha256 9568accf…, `submissions/history/legend_m2_20261018.zip`, BUILDS row) = `_m2` exactly
  (source hash 1684aa2a482c). Its 560 ledger games: vs `_rm` 61.6 / 70.6 (all / official 17), `_ST` 63.4 / 67.6, `_eA` 72.3 / 76.5, `_eB` 73.2 / 85.3,
  `_eC` 85.7 / 85.3, 0 faults; gen16 rollovers 8 per team (= `_rm`, rounds 1-3). `bots/legend/src` = `_m2` + the inert 78c32bf code (`build_style`
  3/4 branches, `LEGEND_RUNTIME_PARAMS` for the A100 trainer). Frozen shipped copy: unzip the history zip, or `bots/_m2` from the setup script.
- The agents' final patches (`x_farm.patch` at 72f4da8, `x_survive.patch` at 52e9b65) differ from `_m2` only in two defaults:
  `join_reach` 0 -> 1.2 (farm `_C5`: vs `_rm` 70.5 / 85.3 where `_C4` scored 61.6 / 67.6; direct `_C5` vs `_C4` 50.9 / 52.9, held-out 50.0) and
  `outmatch_solo_adv` 0.6 -> 0.45 (survive `_svI`: vs `_rm` 63.4, `_ST` 63.4 where `_svF` scored 61.6 / 56.2). So **`_m3` = `_m2` + those two values**
  (`SRC=bots/_m2 tools/variant.sh _m3 join_reach=1.2f outmatch_solo_adv=0.45f`). The agents themselves are finished: nothing of theirs is left to rerun.
- **`_m3` acceptance done** (ledger, 56 maps / official 17): vs `_m2` **48.2 / 47.1** (deaths 821-819), but better than `_m2` against every
  third party: `_ST` 68.8 / 64.7 (`_m2` 63.4 / 67.6), `_eA` 79.5 / 88.2 (72.3 / 76.5), `_eB` 76.8 / 88.2 (73.2 / 85.3), `_eC` 83.0 (85.7), `_rm` 62.5 / 73.5 (61.6 / 70.6).
- **Bug found and fixed: the farm give-up clock** (`giveup_progress`, in `bots/_x_gp` = `_m2` + fix, and `_m4` = `_m3` + fix). `farm()` blacklisted its
  target when `round - task_since > 2 x eta + 60`, with eta = the walk left (0 at the group) and `task_since` reset only on a target change: any body
  spending 60+ rounds on one group (heavy pack, heal trips, waiting out a respawn, camp cycling) dropped it for 40 rounds. Now the clock restarts on
  every hit on the target, capture turn and respawn wait next to it. Unopposed pace (17 official maps): `_m2` 546.6 -> `_x_gp` **526.1**
  (pilgrimage 763 -> 694, stampede 742 -> 698, eight 426 -> 386, rushbait-v2 646 -> 604; no map slower); `_m4` **524.5**.
- **Shipped `legend_m4`** (`submissions/legend.zip` sha256 c1217ccc…, `submissions/history/legend_m4_20261018.zip`, BUILDS row) = `_m4` exactly
  (source hash 0dc2a2aac28a; `tools/setup_session.sh` rebuilds it: `_x_gp` = `_m2` + `experiments/wip/x_gp.patch`, `_m4` = `_x_gp` + `join_reach=1.2f
  outmatch_solo_adv=0.45f`). Ledger (56 maps / official 17): vs `_m2` **58.0 / 58.8** (deaths 770-732), vs `_ST` **73.2 / 70.6** (958-1114), vs `_rm`
  **67.0 / 79.4** (902-1187), 0 faults; pace 524.5; gen16 rollovers 8 per team. `_x_gp` (fix alone on `_m2`) vs `_m2` 51.8 / 61.8.
  Archetypes: `_eA` 75.0 / 94.1 (`_m2` 72.3 / 76.5), `_eB` 82.1 / 94.1 (73.2 / 85.3), `_eC` 83.9 / 91.2 (85.7 / 85.3). `bots/legend/src` = `_m4` + the inert 78c32bf code.
  The A100 space (`tools/rl/a100/space.json`) now also has `outmatch_flee_adv`, `outmatch_solo_adv`, `pair_flee_bonus`, `join_reach`, `outmatch_flee_dist` (52).
  **Ask the user to re-run the A100 trainer on this build** (the bundle they have trains `legend_rm`).

| # | Task | State |
|---|---|---|
| 1 | Ship the survive + farm merge | **done**: `legend_m2` |
| 2 | `_m3` / `_m4` acceptance | **done**: `legend_m4` shipped |
| 3 | **Agent `econ` (Opus, high)**: farming income vs the real teams (opening: our first captures r55-125, their Varg r27; income to the clearers; contact-aware damage builds: their Varg ends `MsE+PsE8`; body-time waste). Baseline `_m4`, copy `bots/_x_econ`, deliverables `experiments/wip/x_econ.patch` + `x_econ_NOTES.md` | running (started ~11:20 UTC) |
| 4 | **Agent `contest` (Sonnet, high)**: lone-monolith maps (contest 0-1000 on the ladder, zero monolith damage): detector + feasible monolith cycle / denial, inert elsewhere. Baseline `_m4`, copy `bots/_x_contest`, deliverables `x_contest.patch` + `x_contest_NOTES.md` | running (started ~11:20 UTC) |
| 5 | **Agent `fight` (Opus, high)**: deaths and kills vs pressure teams (enemy memory in combat(): adv flickers with visibility; burst deaths from bushes; cornered fights; chasers; punishing their weak C&I partner; focus fire). Baseline `_m4`, opponents incl. **`_fA _fB _fC`** = the archetypes rebuilt on `legend_m4` code (setup script). Copy `bots/_x_fight`, deliverables `x_fight.patch` + `x_fight_NOTES.md` | running (started ~10:50 container clock) |
| 6 | Later: gem-race endgame (`race`: close finishes, altar denial; probes in ENGINE_FACTS "Session 5 probes"), deaths at full health (enemies appearing inside reach) | not started |
- **CURRENT STATE, checkpoint 11:30 (container clock)**. Shipped: **`legend_m4`** (`submissions/legend.zip`, sha256 c1217ccc…). Nothing better yet.
  Three agents running on baseline `_m4` (their notes are the handoff: `experiments/wip/x_{econ,fight,contest}_NOTES.md`, patches next to them;
  their ledger cells are `_xe*` econ, `_xf*` fight, `_xc* _xm* _xg* _xp* _xq*` contest):
  - **`econ` (Opus)**: `_m4` unopposed already collects camp gems about as fast as the ladder teams did *contested* on their half (r100-300 level or
    ahead on 11 of 17 maps; behind at r100 on collision, expanse, interlock, lanes, packs, rows). **The ladder gem gap is mostly contact** (deaths,
    chases), plus the opening on those 6 maps. 24.3% of alive body-rounds are in target segments that produce nothing. Rejected on pace: `econ_build`
    bits (Power/Monster/Jungle build tweaks: noise), bigger bags, `heavy_team`, `join_age`, `max_wait`, `hysteresis` 1.3, `max_join` 4.
    Candidates: `join_marginal` (joiner value = claimers' rounds saved; waste 25% -> 13.6% on expanse) and `claim_release` (56-map pace 410.7 vs
    418.7 off the official maps); head-to-head cells `_xe_jm_vs__m4`, `_xe_cj_vs__m4` in progress. Told (coordinator message) to take them to 112-game
    head-to-heads vs `_m4`/`_ST`/`_fA`, then fix the opening on the 6 maps (interlock elk pairs nobody claims; expanse single wolves 29.9 rounds vs 8.6).
  - **`fight` (Opus)**: 53 of the 73 ladder deaths at 75%+ health are Cassi or Issac (the healthy partner dies with the weak one). Traced `_m4` vs
    `_fA`: being without escape kills (~40% death within 8 rounds); once there, fighting trades better than fleeing. `_m4` vs `_fA` 64.7 (official 17).
    Screens vs `_m4` (34 games): `fight_mem` 50.0, `pair_pool` 47.1, `kill_reach` 44.1, `cornered_margin` 0 / 0.4 44.1, `fight_smooth` 0.5 47.1
    (73.5 vs `_fA`), `flee_fail_turns` 2 47.1, **`flee_hold` 6 23.5** (our deaths same, theirs 318 -> 198: they farm freely), `die_soon` 55.9.
    56 maps: `_xfC1` (fight_mem + pair_pool + kill_reach) **42.0** (official 44.1): rejected. Lesson: every rule that makes the whole body more
    cautious loses head-to-head (staying out of fights costs more than the deaths it saves); only targeted, short disengages are worth testing.
  - **`contest` (Sonnet)**: detector `mono_mode` (share of gem rate in single-camp monoliths >= 0.9) fires on contest, its ladder copy and the 12
    `gold_mono_*` maps only. Contest is decided by r100-200 (one team wiped, then spawn-camped: final deaths 50-65 vs 10-15). Variants `_xc1`-`_xc8`,
    `_xm1`/`_xm2`, `_xg1` on the scarce pool (contest + ladder copy + gold/gold2, 26 games): no clear winner yet (`_xm2` vs `_m2` 42.3, vs `_ST` 46.2;
    `_m4` itself vs `_m2` on the same pool 61.2).
- If the session stops: the agents stop too. Next session: `tools/setup_session.sh`, read the three NOTES files, rebuild a candidate from its
  patch (`SRC=bots/_m4 tools/variant.sh _x_NAME && (cd bots/_x_NAME && patch -p1 --no-backup-if-mismatch < ../../experiments/wip/x_NAME.patch)`,
  then the variant's switches from the notes), and use `tools/ledger.py run` for the missing cells only.
- Summaries: `python3 tools/ledger_sum.py [--maps] [--pool GLOBS|all] BOT` (all / official / deaths per cell, no rebuild; default pool = the 56 maps:
  agents add other pools to the same cells). Pace: `python3 tools/ledger_pace.py BOT... --maps`.
- Auto checkpoint: `$S/ckpt.sh` commits and pushes `experiments/wip/x_econ*`, `x_contest*`, the ledger and new tools every 10 minutes
  (`$S` = this session's scratchpad; lost with the container, which is fine: everything it pushes is in git).

## S7-SV2. SESSION 7, STRATEGY V2 (2026-10-18, a second session on this branch): the top-3 replay study and the new plan

### Inputs from the user
- 3 match groups against the top 3 ladder teams (15 games, we are side A in all; ids b26d9db7 = "X", 24706e13 = "Y",
  8ba81317 = "Z"), `GameRules.md`. Request: find why we are stuck around rank 100 and lose to the top teams, check the rules
  for unused mechanics, analyse the top teams' play, and write a new strategy (md) plus the supporting documents to
  implement it, considering k-means, DBSCAN, SVM and other ML / DL / RL ideas.

### Output (all committed on this branch)
- `docs/strategy_v2/STRATEGY_V2.md` (main plan) + `01_REPLAY_FINDINGS.md`, `02_RULES_GAPS.md`, `03_IMPLEMENTATION_SPEC.md`,
  `04_ML_AND_CLUSTERING.md`, `05_TEST_AND_SHIP_PLAN.md`, `06_EXPERIMENTS_18OCT.md`, `data/` (generated report, 17 map plans).
- `tools/strategy_v2/`: `run_all.py` (zips -> report in one command), `decode_dmg.mjs` (decoder with per-step damage),
  `analyze.py`, `report.py`, `trace.py`, `fight_model.py`, `map_plan.py` (k-medoids zones, DBSCAN hubs, assignment,
  circuits, map types), `pacesum.py`, `h2hsum.py`. README in the folder.
- `experiments/wip/x_exec.patch`: fight-execution patch (A1 hit what is in reach before walking, melee swings before stepping
  away; A2 fight commitment). **Not merged into `bots/legend` and not shipped.**
- **Baseline note:** every "`legend`" in `docs/strategy_v2/` is `legend_rm` (`_rm`, `bots/legend` at fcf0820). `legend_m4` was shipped in
  parallel by §S7 while this work ran. The x_exec numbers below are on `_rm`; the re-test on `_m4` is in progress (results will be added here).

### Findings (15 games: 2 wins, banked 7,596 vs 15,312)
- Fights: we deal 91k and take 192k; body deaths 166 vs 72; even with more bodies in the fight we lose 71 to 37. In 74% of
  the rounds our champion is hit by a champion it hits nobody back (theirs 55%), mostly walking (633 rounds; 278 with an
  enemy already in attack range).
- Items: they get 31.9 damage-stat points per 1,000 gold, we get 20.7; with 1.9x our gold they have 2.8x our damage points.
  All three: one health emblem per champion, then Power in the damage stat (295 such emblems).
- Farming: camp gems = alive x camp time x camp damage x conversion = 0.88 x 0.87 x 0.71 x 1.05 = 0.57 of theirs.
- Not the problem: fuel, focus fire, conversion of damage to gems, unspent gold, wards, draft at 5 picks (our set = Y's on ambush, eight, corners, and we still lost those).

### Measured today (06 has every number)
- Unopposed pace of `legend`: 579 rounds mean on the 17 official maps; no single setting (6 tried) improved it.
- `x_exec` vs `legend`: 54.9% over 82 distinct games (official + generated), deaths 611 vs 810; vs `_es2` 73.2% (legend 56.1%),
  vs `_st` 53.7% (legend 54.9%). Ablation: removing any one of its 3 parts drops it to 49-52%; ship all three. Pace identical to legend.
  2 lost turns after round 6 in 82 games (Issac r891/r893, ambush side B; legend 0): from the existing farm code in that game
  state (a fuel floor on the patch's calls gave identical games), not from the patch.
- `build_style 3` alone 47% (34 official games), Varg-first draft alone 35%, `x_exec` + `build_style 3` vs `x_exec` 44%:
  the top teams' builds and draft do **not** help inside the current brain on their own.
- `maps/ladder/` copies official maps (identical games): never count it in head-to-heads (`h2hsum.py` skips it).

### Next steps (STRATEGY_V2 section 6)
1. Ship `x_exec` as `legend_exec`: the zip is ready in `submissions/candidates/legend_exec_20261018.zip` (sha256 4c0d3446...; plays the
   same games as the tested build). Apply the patch to `bots/legend`, copy the zip to `legend.zip`, history, BUILDS row; queue match
   groups vs the top 3, run `run_all.py`.
2. Part A4-A9 (spacing vs splash, camps in the fight estimate, strike first, leave before the finisher, pair rules).
3. Part C: port `map_plan.py` to `draft.cpp`, draft memory v3, zone farming; Part D playbooks (field, contest).
4. Build the top-style sparring bot `bots/_top` (spec in 05 section 2) and use it in every test.
5. Part B (damage builds, collector rank, Varg-first draft) as one package, tested against `_top`.

### How to resume in a new container
- `pip install cambc==2.2.5 --break-system-packages`; `cambc init --yes .`; toolchain by hand with
  `curl --cacert /root/.ccr/ca-bundle.crt`: wasi-sdk-33 (extract `wasi-sdk-33.0-x86_64-linux.tar.gz` into `/root/.cache/cambc/`,
  rename to `wasi-sdk-33`), `cmake-3.31.8-linux-x86_64.tar.gz` into `/root/.cache/cambc/`, `ninja-linux.zip` (1.12.1) into
  `/root/.cache/cambc/ninja-1.12.1-linux-x86_64/`. Engine wasm for the decoders: run `cambc view <any replay>` once.
- Older builds as opponents: unzip `submissions/history/legend_st_20261017.zip` / `legend_es2_20261017.zip` into `bots/_st`, `bots/_es2`.

## 000000. RESUME PROTOCOL (session limits, container restarts): read before running any test

- **Never redo a finished game.** Every bot-vs-bot result goes to the committed ledger `experiments/results/ledger/<BOT>_vs_<OPP>.jsonl`
  (one line per game: map, side, win, rounds, gems, deaths, gold, faults, and the SOURCE HASH of both bots). A row is only reused for the
  exact code it was played with: rebuild a bot (new sources) and its old rows stop counting, automatically.
- Check first: `python3 tools/ledger.py table BOT --opps _rm,_ST,_eA,_eB,_eC --maps 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a'`
  (complete cells show `complete`; others show how many games are on the current code).
- Play the rest (chunks of 8 maps; a cut loses at most one chunk; re-running resumes):
  `python3 tools/ledger.py run BOT OPP --maps '...' --jobs 2`. It prints "N of M games already in the ledger, K to play".
- If an old-style `tools/bench.py` run was cut off (its output dir, e.g. `/tmp/ev/m2`): `python3 tools/ledger.py import DIR` first. It keeps
  every finished game (the stats file is written when a game ends) and skips duplicates. Then `ledger.py run` for the rest.
- After a container restart `/tmp` is empty: the ledger (in git) survives, replays and stats do not, which is fine. Rebuild the bots from the
  committed patches (`SRC=bots/_rm tools/variant.sh`, `patch -p1 < experiments/wip/x_*.patch`), then `ledger.py run` for the missing games.
  Bots that a panel uses must be built with the sources they were played with: the hash check refuses anything else.
- Agents (survive, farm, any new one) must use `ledger.py` for their cells too, so their results survive a cut the same way.
- Replays and full stats (~1.8 MB per game) stay out of git. Only the ledger is committed.
- Status at 10:05 UTC: `_m2` vs `_rm` complete (61.6%), vs `_ST` complete (63.4%), vs `_eA` 110/112 (bench run still finishing; import it when done),
  vs `_eB`, `_eC` not started. The rest: `ledger.py run` after the import.

## 00000. SESSION 6 (2026-10-18, new container): read this first

### Inputs from the user (message 1 of session 6)
- 4 ladder match groups (20 archives, **17 distinct games, one per official map, `legend_st` on side A: 1 win, 16 losses**),
  now in `experiments/ladder_oct18/<map>.repl26a` (deduplicated, named by map).
- `docs/HOUSEOFCODERS_ENEMY_STRATEGY_REPORT.md` (external analysis of those 17 games; read §3, §4-6, §8, §9).
- Requests: continue what is left here first, then the unstarted tasks; implement what the report shows is important;
  recreate the opponents' good strategies in our bot and as sparring opponents; **an RL script to run on a Lightning AI
  A100 machine for 2-3 hours** with many test cases and the opponent archetypes; Opus subagents only for make-or-break
  work (Sonnet/Haiku otherwise, effort sized to the task); push every better bot first, then continue; keep this file updated.

### Ladder evidence (measured this session with `tools/analysis/ladder_econ.mjs` and `tools/analysis/death_ctx.mjs`)
- Totals (us - them): body deaths 232 - 50, camp gems 7,938 - 16,210, gold 39.6k - 87.0k, kills 30 - 167.
- **60% of our deaths are on our own half**, 58% with the enemy holding >1.2x our health within 6 tiles, 39% with 3+ enemies
  within 6, 41% with no ally within 6, 31% at 75%+ health (burst). The enemy roams in groups into our half and picks off
  spread farmers. Cassi & Issac: 59 pair deaths (118 bodies), trigger Issac 63%, trigger at <25% HP 64%, fighting 47% /
  fleeing 34%, the partner usually healthy and 7+ tiles away (`tools/analysis/pair_deaths.mjs` on the ladder dir).
- **Builds**: every enemy profile buys **one Durability health emblem (and a Bruiser health emblem on Ren / Ryth / Cassi)
  early, then stacks Power emblems in its damage stat** (focus: Ren, Stellar, Cassi, Tavi, Prism; strength: Issac, Varg,
  Ryth), e.g. Ren `PfE12+DhE+BhE`, Issac `PsE8+DhE` by r450. Farming profile (rows, expanse): Monster emblem in the damage
  stat, then Power. Ours: Monster / Treasure / Jungle / Durability passives + Bruiser; our Ren's first emblem lands ~r240,
  theirs at r56 (fragment, after a 58-gem group).
- **Farming**: enemy realized finish (with us on the map) beats our *unopposed* pace on ambush (561 vs 820), pilgrimage
  (658 vs 900), rows (355 vs 436), fragment (488 vs 560), interlock (499 vs 572), expanse (580 vs 638), elkring, lanes.
  rows: 10 of our 18 captures were split rewards (two bodies on a 66-gem group); their Varg solo-farms one group every
  ~55 rounds from r27. Our Stellar captured once on collision (their Stellar 9 times).
- contest: we never touch a monolith (0-1000, deaths 63-3); stampede: our objective plan won 1080-0 (keep it).

### Checkpoint 09:00 UTC (agents still running; read their notes for the latest)
- **survive** best = `_svA` = `_rm` + `outmatch_flee=1` (adv 0.8) + `pair_flee_bonus=0.3` + `ren_reflect=1` + `pair_low_hp=0.4`
  (patch `experiments/wip/x_survive.patch`). 56 maps: vs `_rm` **60.7** (official 64.7), deaths 893-1240; vs `_eA` 61.6 (70.6), `_eB` 76.8 (88.2),
  `_ST` 50.9 (44.1 official: the weak cell); deaths -23..38% everywhere, gems up; no new rollovers. `_svC` (= `_svA` without pair_low_hp): vs `_rm` 59.8, `_ST` 53.6 (52.9).
- **farm** best = `_C2` = `_rm` + session-4 pace patch + `no_split` + `unknown_keep` + `obj_focus` + `max_join=3` (patch `experiments/wip/x_farm.patch`).
  Unopposed official pace 579 -> 553. 56 maps: vs `_rm` 54.5 (official 61.8), `_eA` 67.0 (73.5), `_eB` 66.1 (85.3), `_eC` 85.7 (91.2), `_ST` 56.2 (61.8); 0 faults, no new rollovers.
  Under test: `_C3` (+ `varg_splash_pos`, `no_split` in `go_home`).
- **Next step (anyone resuming)**: build the merge `_m1` = `_rm` + x_farm.patch + x_survive.patch (resolve params.h conflicts by hand), switches at the values above
  (`_svC` variant if `_ST` stays weak); bench vs `_rm _ST _eA _eB _eC` on the 56 maps (`--jobs 2`); if it beats `_rm` and `_ST` overall and on the official maps:
  copy into `bots/legend`, rebuild the zip, `submissions/history/legend_m1_<date>.zip`, BUILDS row, push (**ship first**), then add the new switches to `tools/rl/a100/space.json`.

### Checkpoint 09:25 UTC
- **farm** now `_C3` (= `_C2` + `varg_splash_pos` + step off the reward before a recall): pace 546.8; 56 maps / official: vs `_rm` 56.2 / 67.6,
  `_ST` 59.8 / 70.6, `_eA` 64.3 / 73.5, `_eB` 68.8 / 82.4, `_eC` 77.7 / 82.4; held-out 56.0. Testing `_C4` (collector = first to arrive) and
  `join_reach` 1.2 (pace 537.2; pilgrimage 765 -> 649). `x_farm.patch` has `join_reach` 0 (off) for now.
- **survive** unchanged (`_svA` best; death categories vs `_eA`: all -23%, own half -26%, outmatched -33%, C&I -25%; burst deaths at full health barely move).
- **`bots/_m1` built** = `_rm` + `x_farm.patch` + `x_survive.patch` (both apply cleanly) with `outmatch_flee=1 pair_flee_bonus=0.3 ren_reflect=1 pair_low_hp=0.4`.
  First test running: `/tmp/ev/e3.sh` (official 17 maps vs `_rm`, `_ST`, `_eA`, 1 job; results in `/tmp/ev/m1c`, `python3 tools/sum.py /tmp/ev/m1c`).
  Redo `_m1` from the agents' final patches when they finish.

### Checkpoint 09:53 UTC (read this with the 09:25 checkpoint above)
- **`_m1` official 17 maps (34 games each)**: vs `_rm` 76.5 (deaths 231-539), vs `legend_st` 67.6 (276-509), vs `_eA` 64.7 (451-548). 0 faults.
  It was built from older patches (`_svA` settings), so it is superseded.
- **survive** now recommends `_svF` = `_svC` + `outmatch_solo_adv` 0.6 (pair_low_hp left at 0.25: 0.4 costs 4-5 points vs `legend_st`).
  56 maps: vs `_rm` 61.6 (official 64.7), vs `legend_st` 56.2 (58.8), vs `_eA` 69.6 (67.6), vs `_eB` 73.2 (82.4), vs `_eC` 76.8 (70.6); held-out vs `_rm` 56.0.
- **farm** is on `_C5` (not in `x_farm.patch` yet; the patch holds `_C2`-level code plus `_C3` features as of the last commit). Pace on `_C4` ~537-541.
- **`bots/_m2`** = `_rm` + current `x_farm.patch` + current `x_survive.patch` + `outmatch_flee=1 pair_flee_bonus=0.3 ren_reflect=1` (the `_svF`
  settings as the patch's defaults). Acceptance running since 09:53 UTC: `/tmp/ev/e4.sh` -> `/tmp/ev/m2` (56 maps, 112 games per opponent
  vs `_rm`, `_ST`, `_eA`, `_eB`, `_eC`; log `/tmp/ev/e4.log`). Ship rule: beats `_rm` and `_ST` overall and on the official maps, 0 faults.
- **10:02 UTC: survive changed its default to `outmatch_solo_adv` 0.45 (`_svI`: vs `_rm` 63.4, `_ST` 63.4, `_eA` 68.8, `_eC` 85.7).**
  `_m2` was built with 0.6 (`_svF`), so it stays as the reference for 0.6 (its rows are keyed to its own code). When survive is final:
  build `_m3` from the committed patches (defaults from the patch: no overrides) and run only `tools/ledger.py run` for `_m3`; that is the
  acceptance run. Do not reuse `_m2` rows for `_m3`: the hash differs by design.

### Plan (priority order) and state
| # | Task | Who | State |
|---|---|---|---|
| 1 | Ship `_rm` (= session-4 legend: opening fuel, `start_round=2`, `capture_reset`, `tribute_elapsed`, `danger_detour`, `team_bank`, `race_mode`; the report's P1 fixes) | me | **shipped** as `legend_rm` (zip + `submissions/history/legend_rm_20261018.zip`, BUILDS row) |
| 2 | Enemy builds (`build_style 3`: Durability/Bruiser health first, then Power stacks in the damage stat; `4`: Monster then Power for farming maps) | me | **built, not default**: 56 maps vs `_rm`: style 3 48.2 (deaths 1219-1201, neutral), style 4 33.9 (deaths 1429-870: rejected); `_b3` vs `_eA` 57.1 = `_rm` vs `_eA` 57.1. Official 17 maps (34 games): `_b3` vs `_ST` **32.4** (`_rm` 52.9), `_eC` 73.5 (`_rm` 76.5), `_eB` 85.3 (73.5), `_rm` 47.1; gold -15% (no Treasure). Not shipped; left to the A100 ES (`build_style` 2..3 in its space) and to ladder evidence |
| 3 | Opponent archetypes from the report (`tools/make_archetypes.sh`: `_eA` Ren-first pressure, `_eB` CI-first farming, `_eC` caster objective, `_eD` grouped hunter) | me | **built**. `_rm` beats them (56 maps): `_eA` 57.1, `_eB` 68.8, `_eC` 80.4. Diverse sparring, but far weaker than the real teams (1-16): our code family cannot reproduce their execution |
| 4 | Survival vs grouped invaders + Cassi & Issac pair protection (232 vs 50 deaths) | Opus agent `survive` (effort high) | running: `bots/_x_survive`, `/tmp/survive/`, deliverables `experiments/wip/x_survive.patch` + `x_survive_NOTES.md` |
| 5 | Farming throughput: no split rewards, fast first captures, camp circuits on respawn, idle-roaming watchdog (unopposed pace on the 17 official maps) | Opus agent `farm` (effort high) | running: `bots/_x_farm`, `/tmp/farm/`, deliverables `experiments/wip/x_farm.patch` + `x_farm_NOTES.md` |
| 6 | A100 RL script (`tools/rl/a100/`: `run_a100.sh`, `es_a100.py`, `suite.json`, `space.json` (47 params incl. `build_style`, `max_join`, `threat_memory`, `obj_min_attackers`), README) | me | **written and tested end to end here** (selftest + a mini run: training generation, tournament, `best_params.json`); a runtime-params slot plays identically to the static build (rows vs idle: same round, gems, gold). Candidates compile with `LEGEND_RUNTIME_PARAMS` (params in a generated `params_rt.cpp`, rebuild <1 s in release). Surrogate: torch MLP ensemble only with CUDA (tested with `A100_FORCE_TORCH=1` on CPU torch: runs, too slow for CPU cores), else ridge on [z, z^2, case one-hot] (synthetic test: recovers the true ascent direction, cos 0.998). Fits run in a thread during the games and never block a generation. Tournament entrants: final theta, the vector that beat its generation by the most, then the surrogate ranking. User instructions: `tools/rl/a100/README.md`. **Sent to the user** (session 6): `cambc_rl.bundle` (git bundle of this branch with history, 1.6 MB; `git clone -b ccr-a858cd03-q87cpi cambc_rl.bundle Cambridge_Battlecode`), the trainer files as a zip, and the README. When the results archive `rl_a100_results_<date>_<commit>.tar.gz` comes back: read `tournament.json` / `best_meta.json` (did it beat the defaults?) and `validation.txt`, apply `best_params.json` to a copy (`tools/rl/apply_params.py FILE --bot NAME`), A/B it here before baking anything in |
| 7 | contest single-monolith plan; the `race`/`rush` tasks of §0000 (their work was lost with the session-5 container) | Sonnet, later | not started |

## 0000. SESSION 5: CURRENT POSITION (started 2026-10-17 19:46 UTC in a new container): read this first, then §000

- Session 4 stopped pushing at 19:45 UTC with its full panels half done; its container (and `/tmp/ev/`, `bots/_*`) is not here.
  Session 5 rebuilt everything (toolchain, sparring panel, `_L0 _ST _rm _es2 _c3 _st`, `_x_side`, `_rmx`, `_rmxp`) with
  `/tmp/ev/setup.sh` (local; the recipe is §000 "How to resume" plus `_ST` = `tools/snapshot.sh _ST cd4e2aa`, `_rm` = snapshot of HEAD).
- Shipped build is still `legend_st`. Agent rules for this session: top block of `experiments/wip/AGENT_RULES.md` (baseline `bots/_rm`).
- **20:27 UTC `_rmxp` full panel done** (all / official, 212 / 34 games per cell): vs `_ST` 51.9 / 47.1, `_L0` 76.9 / 76.5, `_es2` 59.4 / 58.8,
  `_r2` 84.4 / 82.4, `_v6` 90.6 / 91.2, `_c3` 49.5 / 55.9; 0 faults. Mean of the 5 (no `_ST`): **72.2** all, **73.0** official
  (`_ST` 73.4 / 67.6, `_rm` 72.3 / 72.3). Same picture as `_rm`: better on the official maps and vs `_L0`/`_r2`, worse vs `_es2`/`_c3`
  (our closest relatives). `_rmx` panel running (`/tmp/ev/fp__rmx`).

| Task | Where | Left to do |
|---|---|---|
| Full panels `_rmxp` then `_rmx` (vs `_ST _L0 _es2 _r2 _v6 _c3`, 1,272 games each, 2 jobs, ~45 min each) | `/tmp/ev/e1.sh`, log `/tmp/ev/e1.log`, results `/tmp/ev/fp_<bot>/` (`python3 tools/sum.py DIR`) | compare with `_ST` (mean 73.4, official 67.6) and `_rm` (72.3 / 72.3); ship the best that beats `_ST` |
| Agent `race` (Opus): close gem-race endgame (late banking, race hysteresis, endgame denial) | copy `bots/_x_race`, outputs `/tmp/race/`, deliverables `experiments/wip/x_race.patch` + `x_race_NOTES.md` | merge if it beats `_rm` (acceptance in AGENT_RULES.md) |
| ~~Agent `probe`~~ **done**: a stun cancels a tribute (bag kept, restart from 0), an altar lock on an enemy mid-tribute cancels it (3 hits to break, range 2, 10 gold), tributes run in parallel at one altar, gems count on landing and simultaneous winning tributes go to the team acting first that round, Home emblem recall = 3 turns. Legend's assumptions were right; ENGINE_FACTS.md fixed | `docs/ENGINE_FACTS.md` "Session 5 probes", `experiments/wip/x_probe*`, `tools/probe5_all.sh` | passed to agent `race` for endgame denial |
| Agent `rush` (Sonnet): port and test the user's gold-rush strategy for gem-scarce maps (`x_rush_wip.patch`) | copy `bots/_x_rush`, outputs `/tmp/rush/`, deliverables `experiments/wip/x_rush.patch` + `x_rush_NOTES.md` | merge if it wins on the gold pool and is identical elsewhere |
| Agent `pair` (Opus): Cassi & Issac joint deaths (audit P0: 31% of body-rounds dead, 163 paired deaths); owns comms bit 7 of bytes 2-5 | copy `bots/_x_pair`, outputs `/tmp/pair/`, deliverables `experiments/wip/x_pair.patch` + `x_pair_NOTES.md` | merge if it beats `_rm` |

- Plan: (1) full panels of `_rmxp` then `_rmx` (the panels session 4 had queued; `_rnr`/`_rnd` ablations only if needed), ship the best
  build that beats `_ST`; (2) agents on the unstarted tasks of §000.4 (gem-race endgame, engine probes, walk waste, audit items).

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
| **Full panels** (decide what ships) | `/tmp/ev/e9.sh` (log `/tmp/ev/e9.log`) then `/tmp/ev/e10.sh` (`e10.log`) then `/tmp/ev/e11.sh`; results in `/tmp/ev/fp_<bot>/`, summary `python3 tools/sum.py /tmp/ev/fp_<bot>` | **19:35 UTC**: `_ST` done: `_L0` 72.6, `_es2` 65.6, `_r2` 81.1, `_v6` 91.0, `_c3` 56.6 (mean **73.4**, official 67.6). `_rm` (= legend) done: `_L0` 75.0, `_es2` 64.2, `_r2` 88.7, `_v6` 89.2, `_c3` **44.3** (mean 72.3, official **72.3**), vs `_ST` 53.3 (official 52.9). Better on the official maps and vs `_L0`/`_r2`, but loses to `_c3` (non-transitive: `_ST` beats `_c3`). **19:44 UTC** `_rs3` (`start_round=3`) done: `_L0` 71.2, `_es2` 65.1, `_r2` 81.6, `_v6` 92.9, `_c3` 42.0 (mean 70.6, official 65.8), vs `_ST` 44.3: worse than `start_round=2`, and start timing is not what loses the `_c3` cell. **19:53 UTC** `_rnr` (`race_mode=0`) done: `_L0` 76.9, `_es2` 68.4, `_r2` 85.8, `_v6` 90.1, `_c3` 44.8 (mean 73.2, official 67.1), vs `_ST` 51.4 (official 52.9). So `race_mode` costs ~1 point over all maps but gains **+5.2 on the official maps** (72.3 vs 67.1): kept. It does not cause the `_c3` loss. Running: `_rnd` (`danger_detour=0`), then `_rmx`, `_x_side`, `_rmxp` (~25 min per bot, all done ~21:30 UTC). ~4 min per cell | read all panels; pick the best combination (all-map mean, official-map mean, no cell much worse than `_ST`); if it beats `_ST`: apply to `bots/legend`, rebuild the zip, BUILDS row, push (**ship first, then continue**) |
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
