# GOD bot: improvement plan after the Oct 20 code review

**For the agent that implements the next GOD (v8).** Read this file end to end before touching code. It collects every bug, wrong
assumption and improvement found in a full read of `bots/god/src` (about 9,200 lines), the measurements behind them, and the open
items of `ISSUES.md`, in the order they should be done.

- **Baseline:** GOD v7 = `submissions/god.zip` (sha256 `16c5907a…`), source `bots/god/src`, repo commit `6e82e0a` (Oct 20, 18:08 UTC;
  `bots/god/src` is unchanged since `7cdf491`, v7's ship). Line numbers below are for that source; if the code has moved, search by the
  function name given next to each number.
- **Engine: move to cambc 3.0.2 now.** 3.0.2 is the **Heart of Ruin emergency hotfix** (near-100% pick rate at the top of the ladder):
  Heart of Ruin's focus per shard 15 → **12**, strength per shard 5 → **4**. Every measurement in this file and in the repo's ledgers was
  played on 3.0.1, before the hotfix: any result with Heart of Ruin on either side is stale until re-run (§2.0, P0-0).
- **Status tags used below:** **[verified]** = checked in the code and/or measured here; **[measured]** = numbers from the repo's ledgers;
  **[design]** = a proposal that must be A/B tested before it ships; **[hypothesis]** = a lead to investigate, not a fact.
- Companion files: `AGENTS.md` (history and working rules), `ISSUES.md` (hardcoded choices), `SUGGESTIONS.md` (ideas that lost their
  tests: read it before re-trying anything), `docs/ENGINE_FACTS.md`, `docs/patch_notes/week2_20261020.txt` (patch 3.0).

---

## 0. TL;DR: what to do, in order

| # | Item | Why now | Size |
|---|---|---|---|
| P0-0 | **Move to cambc 3.0.2 (the Heart of Ruin hotfix) and re-baseline**: install 3.0.2, give its games their own ledger directory (the ledger reuses rows across 3.0.x), re-run v7 and the panel, rebuild the proxies | every cell with Heart of Ruin on a side changed: our 3-champion drafts, our counter-picks, and the proxies `_pw` / `_pws` / `_pc` all play HoR; nothing measured before is comparable (§2.0) | small, but blocks everything else |
| P0-1 | **Finish Heart of Ruin**: strike in contact, strike before shield, stop wasting the dash on travel, dash onto camp packs; then re-screen the HoR draft priors and its build **on 3.0.2** | v7 fixed the first half of the bug (+4 games vs legend_m15, +8 vs a striking-HoR proxy, on 3.0.1); HoR still lands its dash next to an enemy only 1-10 times per game while spending 18-55 rounds adjacent to one (§3 B2-B4); the hotfix cut its scaling, so its draft priors and build are open questions again | small |
| P0-2 | **Patch-3.0-only cleanup + engine constants** (drop the old-ruleset branch, read lock hits / ward cooldown / kill gold from the engine) and **make the test setup reproducible** (commit the proxy recipes and the official map files) | removes 15 dual-value settings and one of the two danger-model weight sets; fixes ISSUES #24 / #25 / #26 / #3; today the Power proxies `_pw`/`_pc`/`_ph`/`_pws` cannot be rebuilt from the repo | small |
| P0-3 | **Measure the in-match learners alone** (`learn_stance` 0, `learn_pain` 0 on v7) | they have never been measured one at a time; their results decide P0-5 (free bits) and P1-1 (pain-map replacement) | tiny (2 cells) |
| P0-4 | **Support-aware fight decision** (the user's rule): allies weighted by whether they arrive before our fighter dies, a low-health floor, retreat toward help | the biggest loss pattern: bodies dying alone or retreating one by one (19 of 33 deaths alone on nx61x61, 22 of 45 on contest); the danger model gives allies no net credit (§3 B11) | medium |
| P0-5 | **Shared memory v2**: per-body state (farm / waiting / fighting / out of action), alert priority, local stance | lets P0-4 count allies before they are in sight; fixes the dead DANGER alert and the RALLY-overwrites-OPPORTUNITY bug (§3 B9, B10) | medium |
| P0-6 | **Escort big bags at contested altars** | contest: our Stellar captured the 200-gem monolith, carried it 111 rounds, two 20-turn tributes at the central altar were broken, it died with the bag (§2.4) | medium |
| P0-7 | **Investigate the three blowout maps** (nx31x31_c4, contest_v3, nx61x61) | they are in the official pool and lose badly to every strong opponent (Nyx too) | investigation |

P1 (next): threat map instead of the pain map, death-cause learning, the missing passives in the fight model, a narrow enemy-HoR threat
model, economy / pace, builds derived from the engine's growth values. P2: draft-memory opening plan, synchronized heavy-camp starts,
bush warding, dead-code cleanup. Details in §5-§6.

---

## 1. Ground rules (from the user and `AGENTS.md` §S14.2; still in force)

1. **The game is patch 3.0 plus the 3.0.2 Heart of Ruin hotfix.** The platform runs patch 3.0: the Oct 20 ladder games have Heart of Ruin
   in the drafts (4 of the 5 teams that beat us picked it) and the replays decode only with the patch-3.0 engine. The hotfix (Heart of Ruin
   focus per shard 15 → 12, strength per shard 5 → 4) is being deployed; cambc 3.0.2 on PyPI already has it (§2.0). `docs/sprint/GameRules.md`
   (the "sprint handbook") describes the **pre-patch** game (wolf 22 gems, kill gold 50, camp range 3, altar lock 3 hits, ward every round):
   do not take numbers from it. Use the patch notes, this file's §2.0 and the engine (`bc::constants`, camp and champion designs).
2. **No per-map hardcoding.** Every plan and draft choice must come from map features computed at runtime or from engine values. Anything
   hardcoded goes into `ISSUES.md`; a strategy that should work but did not measure better goes into `SUGGESTIONS.md`.
3. **Every change behind a switch** in `params.h`, default = v7 behaviour. A control build with every new switch off must replay v7's
   games exactly (42 of 42 identical, as `_g8x0` did for v7).
4. **Measure, then ship.** The 21-map official pool, both sides = 42 games per cell (§2.3, §8). A cell moves by about ±3 games from noise. Ship
   only when the candidate is at least level with v7 head-to-head and better on the cells that look like the real top teams. Push the zip
   first (`tools/ship_god.sh CAND v8`), then continue. Keep the previous zip as the rollback.
5. **Local opponents are our own code family.** GOD beat every local proxy and still lost 17 of 20 to Nyx: a local win is necessary, not
   sufficient. The ladder decides. Prefer proxies that imitate what the top teams actually do (Power stacks, striking HoR, early openers).
6. **Compile safety.** Keep the `requires`-based compile guard in `common.h` until the platform's engine version is confirmed (ask the
   user once for `cambc --version` on their machine or the version on the submission page); a failed compile removes the team from
   matchmaking. Build and measure with **cambc 3.0.2** (its SDK headers are byte-identical to 3.0.1's, so v7 compiles unchanged).
7. Repo hygiene (user's rules): single branch `main`, `git pull --no-rebase` before every push, never force, no PR unless asked; add a
   checkpoint to `AGENTS.md` §S14.8 at every step; update `README.md` / `submissions/BUILDS.md` on every ship.

---

## 2. Where things stand

### 2.0 The Heart of Ruin hotfix (cambc 3.0.2), read first

**Announcement (devs, Oct 20):** emergency nerf to Heart of Ruin because of near-100% usage at the top of the ladder: focus per shard
15 → 12, strength per shard 5 → 4. This hotfix is being deployed.

**Verified here** (a probe bot printing every champion design from the draft turn, run on both engines):

| Heart of Ruin | cambc 3.0.1 | cambc 3.0.2 |
|---|---|---|
| health (base + per shard) | 1000 + 100 | 1000 + 100 |
| strength (base + per shard) | 40 + 5 | 40 + **4** |
| focus (base + per shard) | 100 + 15 | 100 + **12** |

- Every other champion design and every engine constant (kill gold 100, altar-lock hits 5, ward cooldown 10, recall 5, respawn 60,
  capture 5) is identical between 3.0.1 and 3.0.2, and the SDK headers (`sdk/`) are byte-identical: **GOD v7 compiles unchanged on 3.0.2.**
- Only games with Heart of Ruin on a side change: GOD v7 vs legend_m15 on corners_v3 (no Heart of Ruin on either side) replays exactly
  on 3.0.2 (1023–441 at r1141, deaths 9–18).
- The base stats did not change, so Heart of Ruin's early game is the same (strike dash 1.75 × 100 = 175 plus a stun at base focus); its
  scaling dropped ~20%. Per shard: strike dash +21 damage (was +26.25), shield +18 (was +22.5), basic attack +4 (was +5). After 30 focus
  shards (six emblems) the dash lands 805 instead of 962 (−16%).

**Quick measurement** (GOD v7 vs legend_m15 on the four 3-champion maps where v7 drafts Heart of Ruin; both sides; legend_m15 drafts Ren,
Stellar, Cassi & Issac there, so only our side has HoR):

| Map | 3.0.1 (v7 side A / side B) | 3.0.2 (v7 side A / side B) |
|---|---|---|
| collision_v3 | W 1001–119 / W 1003–406 | W 1008–21 / W 1019–308 |
| fragment_v3 | W 1018–114 (r1941) / W 1002–72 (r1756) | W 932–160 (r2000, did not finish) / **L 152–672** |
| nx31x31_c3 | W 1163–308 / W 1130–275 (r1394) | W 1119–264 / W 1007–352 (r1556) |
| nx40x40_c3 | L 903–1196 / W 1128–873 | L 982–1027 / W 1167–929 |
| **wins** | **7 of 8** | **6 of 8**, and slower finishes |

Eight games are a signal, not a verdict, but the direction matches the nerf: our Heart of Ruin draft lost one game outright (fragment,
side B, a 1002–72 win became a 152–672 loss) and finished later elsewhere.

**What GOD adapts to automatically** (reads the engine at runtime): its own and every enemy's live strength / focus (fight estimates,
`burst_vs()`, `Enemy::burst()`, the danger-model inputs, `build_react`), ability modifiers (`kit_of()`), and the design growth used by
`ally_dps_on()`.

**What does not adapt, and needs action** (P0-0, P0-1e/f, P1-7):
1. **Every measurement.** The ledgers, the cells in §2.2 and the draft conclusions were all made on 3.0.1. The ledger keys its directory by
   the engine's *major* version only (`tools/ledger.py` `_engine_ledger()` → `ledger_v3`) and reuses any row with the same bot source hashes,
   so a 3.0.2 run would silently reuse 3.0.1 results. Use a separate directory (P0-0).
2. **Draft priors** tuned while Heart of Ruin was stronger: `pd_hor3` (+1.2 for HoR at team size 3), `pd_hor_prior` 0.4, `pd_counter_hor` 0.8
   (HoR into the C&I slot per enemy bruiser pick).
3. **Item builds.** In `build_style` 2 Heart of Ruin shares Ren's list (Jungle health, Treasure focus, Monster focus, Bruiser focus × 2,
   Durability health, Bruiser cycles) and `build_tail` 1 then buys Power **focus** forever (`CT_HOR` is in the focus list). Focus is now worth
   20% less to it while health still gives +100 per shard.
4. **The sparring proxies** `_pw`, `_pws`, `_pc` draft Heart of Ruin: they are weaker on 3.0.2, so "the hardest partner" may change.
5. **The danger model** was trained on pre-hotfix games (minor: its inputs use live stats).
6. **Comments** in `build_for()` still say "+15 focus, +100 health per shard".

**What the hotfix means for strategy** (hypotheses to test on 3.0.2, in this order):
- **Our Heart of Ruin is now an early-game pick.** Same base stats and strike, weaker late. Most of our games run 1,000-2,000 rounds, so
  the late game matters: re-screen `pd_hor3` 0 / 1 (Cassi & Issac or HoR as the third pick) on the full pool, not only the four 3-champion
  maps, against `_g4`, `_mlkc40` and the re-built proxies.
- **Expect the ladder to shift.** If the top teams keep Heart of Ruin, it is weaker late, so the reason for `pd_counter_hor` (answering their
  bruisers with our HoR in the C&I slot) shrinks: screen 0 / 0.4 / 0.8. If they drop it, expect the old meta (Ren, Stellar, C&I, Ryth, Varg:
  Nyx's draft on 16 of 20 maps) and more Marcella / Vendetta; build a post-hotfix proxy with that draft and Power builds (P0-0).
- **Heart of Ruin builds:** test health-leaning tails (Bruiser health, Durability health first) against the Power-focus tail; its passive
  (up to +50% damage at low health) rewards a body that stays alive at low health, and its shield and strike lost a fifth of their scaling.
- **Make builds follow the engine** (P1-7), so the next weekly hotfix does not need a hand re-tune.

### 2.1 GOD v7 in one paragraph

GOD v7 = GOD v6 + Heart of Ruin's strike dash (`hor_strike`); every switch screened on top of it so far lost, so it stays shipped (all
measured on 3.0.1). GOD v6 = legend_m15 rebuilt for patch 3.0: engine camp ranges, Golem and
Heart of Ruin support, gold valued 0.33 gems, the camp-blocked-altar unlock, stall guards, the burst retreat, a never-ending build list,
a reactive health emblem, and a logistic danger model (P(die within 8 rounds), 58 features) retrained on patch-3.0 games with the leave /
flee threshold at 0.2. The draft is the parameter draft (`mapdraft` 6). On the official pool it always produces **Ren, Stellar, Cassi &
Issac, Varg, Ryth** at team size 5, **Ren, Stellar, C&I, Ryth** at 4, **Ren, Stellar, Heart of Ruin** at 3 **[verified]** (21-map run,
§2.4); the objective and open-map drafts no longer fire on any official map, and only the enemy-bruiser counter (`pd_counter_hor`) can
change a pick.

### 2.2 Measured cells (42 games each, 21 official maps) **[measured]**

Ledger rows: v7 = `_g8s` (wasm-identical to the shipped build up to the toolchain's 32-byte directory variation), v6 = `_g6m`.

| Opponent (ledger name) | What it is | v7 | v6 |
|---|---|---|---|
| `_g4` | GOD v2 | **31** | 30 |
| `_pw` | Heart of Ruin, Ren, Stellar, Ryth, Varg with Power builds (our code family) | **35** | 32 |
| `_pws` | `_pw` whose Heart of Ruin strikes (built after the v7 fix) | **26** | 18 |
| `_pc` | Prism, Stellar, C&I, Marcella, HoR with Power builds | **39** | 38 |
| `_mlkc40` | legend_m15, the pre-patch main bot | **29** | 25 |
| `idle` | does nothing (pace test) | 42, 1044.1 rounds to 1000 gems | 42, 1044.1 |

**All of these cells were played on cambc 3.0.1 (before the Heart of Ruin hotfix).** `_pw`, `_pws` and `_pc` draft Heart of Ruin, so every
cell in this table is stale on 3.0.2 except `idle`; re-run them first (P0-0).

v7 follow-ups, all measured on 3.0.1 and **all rejected** (`bots/_x_g9` = v7 + `experiments/wip/x_g9.patch`, control 42/42 identical to v7):

| Variant | What | vs GOD v7 (h2h) | vs GOD v2 | vs `_pws` | vs legend_m15 | vs `_pw` / `_pc` |
|---|---|---|---|---|---|---|
| GOD v7 | shipped | - | 31 | 26 | 29 | 35 / 39 |
| `_g9c32` | `cd_range` 32: a retreating body first steps out of an awake camp's engine range | 21 | 28 | 29 | 30 | 33 / 37 |
| `_g9hp9` | `pd_hor_prior` 0.9: Heart of Ruin also replaces Varg / Ryth at team sizes 4-5 | **16** | 26 | 26 | **38** | - |
| `_g9hp7` | `pd_hor_prior` 0.7 | - | 27 | 26 | **37** | - |
| `_g9h3o` | `pd_hor3` 0: Cassi & Issac instead of Heart of Ruin at team size 3 | - | 28 | 26 | 28 | - |
| `_g8sb` | strike dash + `burst_dash` (enemy dash in `Enemy::burst()`) | 20 | 31 | 25 | 29 | 35 / 37 |

Readings (pre-hotfix): Heart of Ruin was a better third pick (`pd_hor3` stays) but not a better fourth or fifth; the camp rule halves
unopposed camp deaths (96 → 48) yet loses 3 games over the outside cells; `_pws` (whose Heart of Ruin strikes) became the hardest sparring
partner (v6 18/42, v7 26/42). The draft conclusions are exactly the ones the hotfix can overturn: re-screen them on 3.0.2 (P0-1e).

### 2.3 The official pool = our 21-map test pool

The user pulled the official pool: 21 maps, each tile-identical to a local file (`maps/comp30` + `maps/nyx_new` + `maps/loss_oct20`).
Only some names are mapped in the docs. **Action (P0-2):** commit the official files under their official names and write the full
name ↔ file table (use `tools/mapdiff.py`).

| Local file | Official name | Size | Champions | Camp groups | Altars | Camps per side |
|---|---|---|---|---|---|---|
| `comp30/ambush_v3` | ambush | 100x100 | 5 | 12 | 4 | E5 g8 $9 W1 |
| `comp30/collision_v3` | collision | 41x41 | **3** | 20 | 2 | W4 $12 E5 g7 |
| `comp30/contest_v3` | contest | 50x50 | 5 | 14 | 2 | M1 $16 |
| `comp30/corners_v3` | corners | 71x71 | 5 | 30 | 5 | E9 $16 g5 W7 |
| `comp30/eight_v3` | eight | 41x30 | 5 | 8 | 1 | E5 W3 $4 g4 |
| `comp30/elkring_v3` | elkring | 30x30 | 5 | 10 | 2 | E5 $5 g5 |
| `comp30/expanse_v3` | expanse | 80x80 | 5 | 24 | 10 | g8 E7 W5 $17 |
| `comp30/fragment_v3` | fragment | 30x30 | **3** | 6 | 2 | W3 E1 $3 g1 |
| `comp30/interlock_v3` | interlock | 40x40 | **4** | 14 | 4 | E4 W3 $6 g4 |
| `comp30/lanes_v3` | lanes | 90x30 | 5 | 42 | 18 | W15 E3 $18 g6 |
| `loss_oct20/ls50x50_R_c5_56fe6f` | monolith | 50x50 | 5 | 20 | 6 | M1 W9 E1 $11 g12 |
| `nyx_new/nx50x41_V_c5_86f1cb` | boss-battle | 50x41 | 5 | 31 | 1 (walled, unlock by killing the monoliths) | E22 W15 $41 M2 |
| `nyx_new/nx50x50_R_c5_3a3eb5` | elk-arena | 50x50 | 5 | 29 | 2 | E1 g3 $27 |
| `nyx_new/nx100x100_R_c5_bbb066` | (unmapped) | 100x100 | 5 | 24 | 6 | g16 $14 W11 E4 M1 |
| `nyx_new/nx31x31_R_c3_142ce0` | (unmapped) | 31x31 | **3** | 15 | 4 | $14 M1 W3 g3 |
| `nyx_new/nx31x31_R_c4_9e9a40` | (unmapped) | 31x31 | **4** | 12 | **1** (centre box) | $10 E2 g2 |
| `nyx_new/nx40x40_R_c3_b9da0c` | (unmapped) | 40x40 | **3** | 22 | 4 | M1 W5 E6 $11 g9 |
| `nyx_new/nx51x40_V_c5_ec2893` | (unmapped) | 51x40 | 5 | 12 | 2 | M1 g6 E6 W11 $10 |
| `nyx_new/nx60x60_R_c5_0cdefa` | (unmapped) | 60x60 | 5 | **46** (max) | 10 | E11 W12 g13 $23 |
| `nyx_new/nx61x61_R_c5_15b37f` | (unmapped) | 61x61 | 5 | 11 | 2 | E2 g6 W6 $9 |
| `nyx_new/nx61x71_R_c5_d26c0c` | (unmapped) | 61x71 | 5 | 28 | 3 | g10 W8 E8 $16 M1 |

Unmapped official names: big-world, broken-curve, concentrated-wealth, corridors, fracture, gold-rush, hooks, islands. Facts that matter
for this plan: the most camp groups on any map is **46** (so 6-bit claims fit, §P0-5); 15 maps have 5 champions (with C&I that is **6
bodies**), 2 have 4, 4 have 3.

### 2.4 Smoke run: GOD v7 vs legend_m15, one game per map, v7 on side A **[verified]**

One game per map is not a measurement (side matters, and legend_m15 is not a top team), but it shows the shape of the losses.
v7 won 15 of 21. Played on cambc 3.0.1; on 3.0.2 only the Heart of Ruin games differ (the four 3-champion maps, §2.0).

| Map | Result (v7–m15) | Deaths (v7–m15) | Note |
|---|---|---|---|
| nx31x31_c4 | **L 66–1012** (r1981) | **72–33** | worst map; also lost 0–1012 to Nyx. We captured gems 4 times vs 46, banked 3 times vs 46 |
| contest_v3 | **L 200–800** (r2000) | 45–45 | 22 of our 45 deaths alone; a 200-gem monolith bag died unbanked (below) |
| nx61x61 | **L 611–955** (r2000) | 33–16 | 19 of 33 deaths alone; 262 gems lost on deaths vs their 125; banks 28 vs 51 |
| ambush_v3 | L 689–1012 | 9–6 | lost the race, not the fights (pace) |
| nx40x40_c3 | L 903–1196 | 4–17 | lost the race with fewer deaths (pace); Heart of Ruin draft |
| nx60x60 | L 955–1012 | 7–20 | lost the race (pace) |
| collision, fragment, nx31x31_c3 | W 1001–119, 1018–114, 1163–308 | 1–21, 6–53, 5–42 | Heart of Ruin drafts win big |
| nx50x50 (elk-arena) | W 1008–0 | 18–36 | ISSUES #21 fixed in practice: v7 drafts the meta five; legend_m15 drafted the caster ring and lost |
| nx50x41 (boss-battle) | W 1034–94 at r651 | 3–19 | the altar unlock works |
| the other 10 | W | | |

Two kinds of losses: **fights** (nx31x31_c4, contest, nx61x61: many deaths, many alone, bags lost) and **pace** (ambush, nx40x40_c3,
nx60x60: fewer deaths, slower farming). P0-4 to P0-7 target the first kind; P1-6 the second.

**The contest bag** (replay trace): Stellar captured the 200-gem monolith at r997 with a capture-recall, walked to the central altar,
started a 200-gem tribute at r1035 (200 gems = **20 turns** of channel; damage does not stop it, a stun or death does), cancelled it at
r1036 under threat, recalled home to heal and shop, started again at r1080 and r1102 at the same contested altar with three or four enemies
within 8 tiles while the only ally nearby (Cassi) walked away, and died at r1108 still carrying all 200 gems. Our team banked once all game;
theirs four times.

### 2.5 Code map (commit `7cdf491`)

| File | What lives there |
|---|---|
| `main.cpp` | loop: draft turn or body turn, swallow exceptions, always `end_turn()` |
| `draft.cpp` | `analyse()` map features, `derive_params()`, `pd_score()` champion scoring, `param_pick()` (shipped draft) |
| `params.h` | `struct Params`: **374 settings**, 84 of them 0 (switched off), 15 written `SDK_HAS_HOR ? new : old` |
| `common.h` | SDK compatibility (`SDK_HAS_HOR`, `CT_HOR`, `D_HOR`, `CAMP_GOLEM`), `Kit` (abilities read from the engine designs) |
| `world.h/.cpp` | static map model (walls, altars and approach tiles, camp groups, islands), per-turn perception, `Enemy` / `Ally` memory, `Enemy::burst()` (world.h:98) |
| `nav.h/.cpp` | lazy distance fields per group / altar, `step_field`, `step_to`, dash routing, crystal hops |
| `comms.h/.cpp` | the 8-byte shared memory protocol |
| `learn.h/.cpp` | stance bandit, pain map, fight calibration |
| `ml2_model.h` | danger model weights (new and old sets), boosted trees (unused, `ml2_gb` 0) |
| `brain.cpp` | everything else; key functions below |

`brain.cpp` key functions: `turn()` 617 (pipeline: `support_spells()` 740 → `use_locks` → `escort_wait` → `combat()` 766 → `safety()` →
`tribute()` → `home_trip()` → `shop_trip()` → `respond_to_alert()` → `farm()`), `handle_channel()` 938, `shop()` 1016, `build_danger()` 1089,
`nearest_altar()` 1191, `mob_dash()` 1259, `strike_dash_at()` 1427, `burst_vs()` 1584, `support_spells()` 1602, `place_ward()` 1670,
`ml2_features()` ~1769, `combat()` 2012 (our side 2075-2090, `adv` 2143, backup/isolated 2147-2167, `can_escape` 2234, fight rules
2238-2300, `fight_commit` 2280, danger model 2404-2455, RALLY post 2497, outmatched flee 2580-2606), `post_danger()` 2610, `engage()` 2640
(approach branch 2683, melee strike 2805, contact branch 2840), `safety()` 3055, `update_mode()` 3168, `tribute()` 3354,
`respond_to_alert()` 3469, `dps_on()` 3565, `group_score()` 3967 (pain cost 4385), `prepare_scoring()` 4582, `farm()` 4610,
`capture_group()` 4978, `spells_on_camp()` 5050, `farm_group()` 5230.

---

## 3. Bugs and wrong assumptions (each has an owner item below)

| ID | What | Where | Status | Item |
|---|---|---|---|---|
| B1 | Heart of Ruin never used its damaging dash (1.75 × focus + 1-turn stun in radius 1) in a fight: only the ranged branch of `engage()` set `strike_dash`, and `mob_dash()` refuses a damaging dash within 9 tiles of an enemy | `engage()`, `mob_dash()` 1259 | **fixed in v7** (`hor_strike`, `strike_dash_at()` 1427) | done |
| B2 | **The strike only happens on approach.** `strike_dash_at()` is called only inside `if (d > kit.attack_range)` (2683/2805). Once Heart of Ruin is adjacent to its target, the contact branch (2840) never dashes, although a dash to another tile within 2 that keeps the target within 1 still lands 1.75 × focus + stun | `engage()` | open **[verified]** | P0-1 |
| B3 | **The shield uses the turn's only cast before the fight code runs.** `support_spells()` (called at 740, before `combat()`) casts Heart of Ruin's shield when health < 90% and an enemy is within 4; `ready()` then refuses the strike that turn (one successful cast per turn) | `support_spells()` 1602-1621 | open **[verified]** | P0-1 |
| B4 | **Travel dashes spend the strike.** In v7 games 85-97% of Heart of Ruin's dashes start with no enemy within 3 (they are walking dashes); when an enemy appears from beyond 9 tiles (`strike_dash_hold`) the dash is often on cooldown. Measured in the smoke run: dashes landing next to an enemy / all dashes / rounds adjacent to an enemy: nx31x31_c3 6/100/33, fragment 10/111/55, collision 10/75/34, nx40x40_c3 1/86/18 | `mob_dash()` | open **[verified]** | P0-1 |
| B5 | Heart of Ruin's dash is never used on camps: `spells_on_camp()` knows damage, stun and area spells only. A dash onto a pack hits every camp within 1 for 1.75 × focus and stuns them (stunned camps skip their next attack) | `spells_on_camp()` 5050 | open **[verified]** | P0-1 |
| B6 | `Enemy::burst()` ignores an enemy's damaging dash (and its passive). The blunt fix (`burst_dash`: max with focus × dash_mod everywhere) measured negative: it makes every body cautious of every enemy HoR at any distance | world.h:98 | open, needs the narrow version | P1-4 |
| B7 | `safety()` counts only camps within 3 (`d > 3` at 3073, `4 - d` at 3088/3092): elks and golems hit from 4 and monoliths from 5 since patch 3.0. `cd_range` 32 (step out of an awake camp's real range before walking home) halves unopposed camp deaths (96 → 48) and is faster, but lost on v7 too (h2h vs v7 21/42, outside cells 157 vs 160) | `safety()` | rejected twice; parked | P1-3 (a narrower version: count the real range in the retreat line only for camps that target us) |
| B8 | `combat()`'s camp term counts only camps within 3 (`best_d = 4` at 2116) | `combat()` | open | P1-3 |
| B9 | **DANGER alerts are dead code.** `post_danger()` returns at once while `alert_radius` = 0 (2615), so no DANGER alert is ever posted (only the switched-off contest regroup posts one). **And one alert slot is shared**: a RALLY is posted on every fight turn (2497) and replaces a fresh OPPORTUNITY (an enemy tributing, posted at 700), and the reverse, so the team can lose the cheapest kill in the game to a skirmish elsewhere | `post_danger()`, `turn()`, `combat()` | open **[verified]** | P0-5 |
| B10 | **Phantom support from unseen allies.** In `combat()` an ally we cannot see counts as backup if its claimed group's centre is within 5 tiles (2147-2167), even when it is walking home at 10% health or recalling; only visible allies within 6 add health and damage (2075-2090) | `combat()` | open **[verified]** | P0-4, P0-5 |
| B11 | **The danger model gives nearby allies no net credit.** Patch-3.0 weights (log-odds per unit): ally within 5 −0.16, but the same ally also counts "within 7" +0.21; ally health within 5 +0.21 per 1,000; hurt ally within 5 +0.26; versus each enemy within 3 +0.57. The model learned "allies near = big brawl", so a body leaves at P ≥ 0.2 whether help is two tiles away or not | `ml2_model.h`, `combat()` 2439 | open **[verified]** | P0-4 |
| B12 | Our own Ren's retaliation is not counted on our side in fights (it is counted when an enemy Ren is hit, 2211, and when farming camps, 3583) | `combat()` | open | P1-3 |
| B13 | Hardcoded rule numbers: enemy-locked altar costs 6 steps ("3 hits"; the engine reports 5 since the patch, `lock_hits_sdk` 0) at 1203; ward rhythm literal 10 at 1675/1704 (equals the patch-3.0 cooldown, so harmless now); capture time literal `6.f` in `group_score()`; stance reward `kill_gems` 40 with a comment about 50 kill gold (the engine pays 100 now) | several | open (ISSUES #24, #26, #3) | P0-2 |
| B14 | The draft memory (1,024 bytes, read-only in the game) is never written by the shipped draft: `param_pick()` returns before the write in `play_draft()` | `draft.cpp` | unused capacity | P2-1 |
| B15 | Big bags are banked alone at contested altars (the contest trace in §2.4) | `tribute()`, `handle_channel()` | open **[verified]** | P0-6 |
| B16 | **The results ledger cannot tell 3.0.1 from 3.0.2.** `_engine_ledger()` names the directory by the engine's major version only, and rows are reused whenever the bot source hashes match, so after the hotfix every "missing game" check passes and 3.0.1 results are reported as current | `tools/ledger.py` | open **[verified]** | P0-0 |
| B17 | **Builds do not follow the engine.** Heart of Ruin's tail stat is focus because `CT_HOR` is in a hardcoded focus list, and `build_for()` comments still quote +15 focus per shard; the hotfix made focus 20% weaker for it without any code noticing | `build_for()` | open | P0-1f, P1-7 |

Wrong statements in the docs (do not rely on them):
- `docs/sprint/GameRules.md`: pre-patch numbers throughout (see §1.1).
- `docs/HLD.md` shared-memory table: missing the team bag sum (bit 6 of bytes 0-5) and the alert-refresh bit (bit 7 of byte 2, off).
- `submissions/BUILDS.md` GOD v1 row: "its dash held for fights (landing hit + stun)" was not true until v7.
- `build_for()` comments ("+15 focus, +100 health per shard" for Heart of Ruin), `docs/patch_notes/week2_20261020.txt` and every doc that
  quotes Heart of Ruin's growth: since the 3.0.2 hotfix it is +12 focus and +4 strength per shard (§2.0).
- `AGENTS.md` §S14.3 ("engine camp ranges in danger / ring / kite plans"): true for those, but `safety()` and `combat()` still used 3 (B7, B8).
- Earlier in the review I said "about 150 switches" and "DANGER alerts are posted but nobody reads them": the correct numbers are 374
  settings at `7cdf491` (84 set to 0), and DANGER alerts are not posted at all.

---

## 4. P0: do now

### P0-0. Move to cambc 3.0.2 and re-baseline (blocks everything else)

1. **Install the hotfix engine:** `pip install --break-system-packages cambc==3.0.2`; change `tools/setup_session.sh` (it pins
   `cambc==3.0.1`) and the repo's `cambc.toml` (`sdk_version = "3.0.1"`) to 3.0.2. `cambc init` on 3.0.2 writes `sdk_version = "3.0.2"`; the
   SDK files themselves are identical.
2. **Keep the 3.0.2 games apart:** run every ledger command with `LEDGER_DIR=experiments/results/ledger_v3_0_2` (supported by
   `tools/ledger.py`), or better, change `_engine_ledger()` to use the full version (`ledger_v3.0.2`) and add an `engine` field to every row.
   Otherwise the ledger reuses the 3.0.1 rows (same bot hashes, same directory) and nothing gets re-played.
3. **Rebuild every bot and re-run the panel for GOD v7** (`_g8s` / `god`): `_g4`, `_pw`, `_pws`, `_pc`, `_mlkc40`, `idle`, then `_mite`,
   `_ifish`, `_px9`. Sanity check: games with no Heart of Ruin on either side must replay exactly as on 3.0.1 (compare the two ledger
   directories map by map); only HoR games may change.
4. **Re-run the v7 follow-ups that involve Heart of Ruin** on 3.0.2: `pd_hor3` 0 (`_g9h3o`), `pd_hor_prior` 0.7 / 0.9, `pd_counter_hor` 0 /
   0.4, and `burst_dash` (enemy HoR in `Enemy::burst()`), because their 3.0.1 verdicts were about a stronger Heart of Ruin.
5. **Add a post-hotfix proxy:** the old meta draft (Ren, Stellar, Cassi & Issac, Ryth, Varg) with Power builds (`build_style` 12, `build_tail`
   1) and the v7 brain, for the case where the ladder drops Heart of Ruin. Record its recipe in `tools/setup_session.sh` (P0-2d).
6. Ask the user once whether the platform has finished deploying the hotfix (the submission page shows the engine version); measure on
   3.0.2 either way, since that is where the game is going.

### P0-1. Finish Heart of Ruin, then re-screen its draft priors (on 3.0.2)

Heart of Ruin (patch 3.0 + hotfix 3.0.2): melee, 1000 health (+100 per shard), 40 strength (**+4**, was +5), 100 focus (**+12**, was +15).
Slot 0 (S1): self shield 1.5 × focus for 5 turns. Slot 1 (S2): dash up to 2 tiles; on landing, 1.75 × focus damage and a 1-turn stun to
every enemy and camp within Chebyshev 1. Passive: up to +50% damage from every source, linear in missing health
(`bc::constants::passive_abilities::heart_of_ruin_missing_health_damage_max_bonus` = 0.5). The hotfix cut its scaling, not its kit:
items a-d below are worth as much as before in the early game and somewhat less late.

Changes (new switch `hor_strike` 2 = all of a-c; keep 1 = v7):

a. **Strike in contact (B2).** In `engage()`'s contact branch (`if (d <= kit.attack_range)`, 2840), before the basic attack: if the dash
   is ready and no cast was made this turn, call `strike_dash_at(e)`. It already picks a landing tile within dash range that keeps the
   target within the landing radius and catches the most enemies; it must exclude the current tile (it does: `best == pos` returns
   false). After the dash, still attack (melee may attack after moving; `after_move(true)` refreshes `can_attack`). Prefer landing tiles
   outside the reach of enemies not caught by the dash when the catch count ties.
b. **Strike before shield (B3).** In `support_spells()`, skip a shield cast when the body has a damaging dash that is ready and a visible
   enemy is within `dash_range + dash_radius` (3); let `combat()` decide. In `engage()`, cast the shield only if the strike was not
   possible this turn and health < 50% with enemies in reach.
c. **Keep the strike for fights (B4).** Do not spend a damaging dash on travel when (i) an enemy was seen within 12-15 tiles in the last
   few rounds (raise `strike_dash_hold` from 9; screen 12 and 15), or (ii) the body is on the enemy half or on a midline group, where
   contact is likely. Check unopposed pace (`idle` cell) because travel gets slower.
d. **Dash onto camp packs (B5)** (separate switch, it affects pace): in `spells_on_camp()`, when the body already stands in melee reach of
   a group and a landing tile within 2 has 2+ live camps within radius 1, dash there (count the damage with `note_dmg`). Measure on the
   `idle` cell (pace) and on HoR maps.
e. **Then re-screen the draft priors on 3.0.2.** `pd_hor3` (+1.2 for HoR at team size 3), `pd_hor_prior` 0.4 and `pd_counter_hor` 0.8 were
   tuned while Heart of Ruin could not dash, and the v7 re-screens (§2.2: `pd_hor3` 0 rejected 82 vs 86 over three cells; `pd_hor_prior`
   0.7 / 0.9 rejected, 16/42 vs v7) were made before the hotfix. Screen `pd_hor3` 0 / 1, `pd_hor_prior` 0.2 / 0.4 and `pd_counter_hor` 0 /
   0.4 / 0.8 against `_g4`, `_pws`, `_pw`, `_pc`, the post-hotfix proxy (P0-0.5) and `_mlkc40`. Nothing forced or per-map: priors and
   enemy-pick terms only.
f. **Heart of Ruin's build after the hotfix.** Screen, for Heart of Ruin only: the current list (Ren's style-2 list + Power focus tail),
   Durability health then Bruiser health first, and a Bruiser-health tail instead of Power focus. Judge on the 3-champion maps (where we
   draft it) and on the cells where we counter-pick it.

Measurement: only games with Heart of Ruin on a side change, so most of the 42 are identical; judge on the HoR-heavy cells (`_pws`,
`_pw`, `_pc`) and the four 3-champion maps. Log per game (replay or a `HOR_TRACE` build): strike dashes, strikes per round adjacent to an
enemy, enemies hit per strike. Target: most dashes in contact rounds land on an enemy.

### P0-2. Patch-3.0-only cleanup, engine constants, reproducible tests

a. **Drop the old-ruleset tuning.** Replace each of the 15 `SDK_HAS_HOR ? new : old` settings in `params.h` with its patch-3.0 value
   (`gold_value`, `burst_retreat`, `altar_no_camp`, `no_altar_gold`, `dash_gain1`, `stall_guard`, `pd_obj_heavy`, `pd_front_pen`,
   `pd_counter_hor`, `pd_obj_side`, `build_react`, `build_tail`, `hor_strike`, `ml2_leave` / `ml2_flee`) and delete the `ML2OLD_*` weights
   in `ml2_model.h`. Keep the compile guard in `common.h` (§1.6). Check: it plays v7's games identically on 3.0.2 (the wasm should be
   byte-identical up to the toolchain's known 32-byte directory variation, since `SDK_HAS_HOR` is already true on 3.0.x).
b. **Engine constants instead of literals (B13):** `lock_hits_sdk` → always `2 × bc::constants::altar_lock_hits`; ward rhythm from
   `bc::constants::ward_cooldown`; capture time in `group_score()` from `bc::constants::capture_time + 1`; the stance reward's kill value
   from `bc::constants::kill_gold × gold_value` plus the average bag. These change a few games: measure (one cell vs `_g4`, one vs `_pw`).
c. **Why still bother with runtime values:** patches are weekly ("Patch Notes – Week 2"; the competition runs to 18 November) and the devs
   said they will re-value camp groups with gem and gold clusters. The 3.0.2 hotfix proves the point: its SDK headers are identical to
   3.0.1's, so **no compile-time check (`SDK_HAS_HOR` or any other) can see it**; only the values the engine reports at runtime change.
   Values that the engine reports should be read, not typed.
d. **Make the tests reproducible.** `tools/setup_session.sh` does not rebuild the Power proxies `_pw`, `_pc`, `_ph`, `_pws` (they were
   built from scratch scripts outside the repo). Write their recipes into the setup script (base, patches, switches, forced draft) and
   check them by source hash like the others. Commit the official map files under their official names (§2.3).

### P0-3. Measure the in-match learners one at a time

Two cells on v7: `learn_stance` 0 and `learn_pain` 0 (each vs `_g4` and `_pw`, plus `idle` for pace). The docs only report all three
learners off together (79.4% vs 80.0% over 540 games, against our old code family). Decision rule: if a learner is level or worse with it
on, remove it (its bits and fuel are better used by P0-5 / P1-1).

### P0-4. Support-aware fight decision (the user's rule)

**Goal.** A body should not blindly keep fighting when its own health is low; nearby allies should raise its confidence the closer they
are; the damage it takes alone should lower it; and when we are outnumbered at close range but arriving support makes our side win, the
body should hold or kite toward the support instead of fleeing home.

**Why the current code fails.** Our side counts visible allies within 6 tiles at full weight (2075-2090), unseen allies as head-count by
their claims (B10), and the danger model then ignores them (B11). The result: one-by-one retreats and lone deaths (§2.4).

**The rule** (new switch `sup_mode` 1; all other values = v7 when 0):

1. My time to live against what can hit me now: `T_me = hp / max(1, incoming)`. `incoming` is already computed in `combat()` (enemies in
   reach: strength + half the ready burst, plus camps hitting me).
2. Candidate helpers. A visible ally counts only if alive, health ≥ its retreat line, not recalling / banking / teleporting
   (`Ally::channeling`), and not moving away from the fight (compare its distance to the nearest enemy with last turn's; `ally_prev_pos`
   is already tracked when `no_split` is on). With P0-5, an unseen ally counts if its shared state is "fighting" near our rally cell;
   "out of action" never counts.
3. Arrival: `a_i` = rounds until ally *i* can hit an enemy here ≈ max(0, distance to the nearest enemy − its reach) − 2 if its dash is
   ready (reach: attack range, +1 for melee, 4 with a damage spell ready).
4. Weight: `w_i = clamp(1 − a_i / max(1, T_me), 0, 1)`. In reach now → 1; arrives after I would be dead → 0. An ally that the enemies in
   reach would kill within one round counts 0 (enemies focus the lowest health).
5. Team strength with support:

```
our_hp  = hp     + Σ w_i · ally_hp_i          their_hp  = Σ hp of enemies in close range   (as now)
our_dps = my_dps + Σ w_i · ally_dps_i         their_dps = Σ dps of those enemies, ready bursts included (as now)
adv_sup = (our_hp / their_dps) / (their_hp / our_dps) × learner().fight_scale()
```

6. Decision, in order:
   - a kill this turn (`killable`, or the px team-kill) → fight (unchanged);
   - **low-health floor:** hp < `sup_low_hp` (0.25) × max_hp, no ally with `a_i ≤ 1`, and we can escape → leave;
   - sort helpers by arrival; find the smallest set whose `adv_sup` reaches the margin in force (`fight_back_margin` 0.873 when they can
     hit us, `fight_commit_margin` 0.7 when we fought last turn, `fight_margin` 1.30 for a new fight); stay only if
     `T_me ≥ a_needed + 1`, where `a_needed` is the arrival of the last ally in that set;
   - otherwise leave; **if an ally with `a_i ≤ 3` exists and a step toward it does not enter more enemy reach, step toward the ally**, not
     home (new helper next to `go_home_step()`).
7. Danger-model leave threshold scales with real support:
   `thr = ml2_leave + sup_ml2_bonus × min(1, Σ w_i · ally_hp_i / max_hp)` with `sup_ml2_bonus` 0.2 (0.2 → 0.4).
8. Use `adv_sup` everywhere `adv` decides: proactive engage, fight back, `fight_commit` (2280), the cornered rule, and the outmatched
   flee (2580-2606). Replace the claim-based backup head-count with the helpers above.

**Why weighted sums, not a mean or median** (the user asked): the fight is decided by total damage against total health, so sums are the
right measure; averages mislead. Example: me 900/900, an ally with 1,000 health two tiles away, an ally with 60 health next to me. The
mean (653) looks mediocre, the median (900) looks great; in reality the 60-health ally dies to one hit and the 1,000-health ally decides
the fight. The weighted sum gets this right. The only non-sum statistic that matters is the weakest body under focus (step 4).

**Behaviour this produces:** an ally walks closer → `a_i` falls → `w_i` and `adv_sup` rise; our fighter takes damage → `T_me` falls →
far helpers stop counting and our own health term shrinks → `adv_sup` falls; nearly dead → only helpers already in reach count.

**Measure:** cells vs `_g4`, `_pw`, `_pws`, `_pc`, `_mlkc40`, `idle`; from replays: deaths, deaths with no ally within 6 in the previous
round (the smoke-run script in §8), fights left, and our deaths on our own half when they open (the Oct 20 number: 121 to their 7).
v1 can count visible allies only; v2 adds P0-5's states.

### P0-5. Shared memory v2

**What a body already knows without sharing.** Each champion is a separate bot instance; vision is not shared. A body reads, live, for
every enemy inside its own vision (8 tiles with line of sight, plus its own ward): position, health and max health, strength and focus
(items included), both spell cooldowns, carried gems, and whether it is recalling / banking / teleporting. Every body also knows which
enemies and allies are dead (global alive flags). It does **not** know enemies outside its own sight, the health or position of allies it
cannot see, or what other bodies learned (burst memory, pain map, fight calibration). The only live channel is 8 bytes.

**Today** (`comms.h`): bytes 0-5 = one claim per body (7 bits, or 6 bits + 1 bit of the team bag sum on maps with ≤ 62 groups); bit 7 of
bytes 0-1 = stance (body 0 writes it); bit 7 of byte 2 = alert-refresh toggle (off); bytes 6-7 = one alert (14-bit exact tile + 2-bit
kind). Waste: six claim bytes even with three bodies; four idle top bits; DANGER never posted; one shared alert slot (B9).

**New layout** (switch `comms_v2`; read and write the 8 bytes as one little-endian 64-bit word; turns inside a team are sequential, so a
read-modify-write is safe and a write is visible to every ally acting later in the same round):

```
for body i in 0..N-1 (N = bodies, 3..6):  bits 8i..8i+5 = claimed group id + 1 (0 = none; up to 63 groups, the official max is 46)
                                          bits 8i+6..8i+7 = state: 0 FARM, 1 WAIT, 2 FIGHT, 3 OUT
team field (the remaining 64 − 8N bits: 16 when N = 6, 24 when N = 5, 32 when N = 4, 40 when N = 3):
   6 bits  team carried gems in tens (sum of min(10, bag/10) per body; as today)
   2 bits  alert kind: 0 none, 1 OPPORTUNITY (enemy tributing / carrier), 2 RALLY (fight here), 3 ESCORT (bank escort, P0-6)
   8 bits  alert cell on a 16x16 grid (cell = x·16/W, y·16/H; ~3 tiles on 50x50, ~6 on 100x100; rallies are answered from 9 tiles)
N = 5 (8 spare bits): + 3 bits focus target (enemy index, 7 = none) + 3 bits last death type (P1-2)
N ≤ 4 (16+ spare bits): + the above + 8 bits cell and 3 bits count of the last enemy group seen (P1-1)
```

State rules: FIGHT when `task == T_FIGHT` this turn or last; WAIT when waiting at the claimed group outside camp range (gather, respawn
wait, ring); OUT when below the retreat line, walking home (`T_HOME` / `T_FLEE`), recalling, banking or dead (dead bodies still get a turn
and write OUT; also treat any body with a false alive flag as OUT). Alert priority: OPPORTUNITY > ESCORT > RALLY; a lower kind never
overwrites a higher kind posted within the last 6 rounds. Fallback to the v1 layout when groups > 63.

**Stance without bits.** The stance reward uses banked gems and alive flags, which every body can read, so each body can compute the same
stance itself (drop the leader check in `Learner::tick` and the `ctx_invaded` term, the only input that depends on what one body saw).
Caveat: a tribute can land between two of our bodies' turns in the same round, so two bodies can read different totals at a window
boundary; check stance agreement in traces, or delete the stance if P0-3 shows it is worth nothing.

What it enables: P0-4 counts unseen helpers; synchronized starts (WAIT); P1-1 enemy-group sightings; P0-6 escorts.

### P0-6. Escort big bags at contested altars

Facts: tribute time = ceil(bag / 10) turns; damage does not interrupt it, a stun, death or an enemy altar lock does; the bag lands only at
the end. A 200-gem bag is a 20-turn channel (§2.4).

Design (switch `escort_bag`, e.g. 60):
1. A body carrying ≥ `escort_bag` gems (or a bag that wins the game) whose chosen altar is contested (`World::contested()`, or enemies seen
   within 10 of it recently) does not start the tribute until (a) at least `min(2, living allies)` healthy allies are within 5 of the altar,
   or (b) no enemy has been seen within 10 of the altar for 10+ rounds. While waiting it stays out of enemy reach (near the altar on our
   side, or on spawn).
2. It posts an ESCORT alert at the altar cell; `respond_to_alert()` answers ESCORT from farther than a RALLY (like OPPORTUNITY) and the
   escorts stand between the altar and the enemy side, targeting enemies with a ready stun first.
3. During the channel, `handle_channel()` keeps the tribute when the escort count holds and `adv_sup` ≥ 1 (today it cancels on a nearby
   stunner whenever the bag is ≥ 20 and a threat is close).
4. Altar choice: scale `unsafe_altar_penalty` (14 steps today) with the bag's channel length, so a far but quiet altar wins for big bags.

Measure: gems lost on our deaths and bank count per game (replay), cells as usual, contest_v3 and nx61x61 in particular.

### P0-7. Investigate the blowout maps

| Map | What the smoke run shows | Leads **[hypothesis]** |
|---|---|---|
| nx31x31_c4 (31x31, 4 champions, the **only altar at (15,15) inside a walled centre box** with the centre elk + gem groups) | 66–1012, deaths 72–33 evenly through the game (7-11 per 250 rounds), gem captures 4 vs 46, banks 3 vs 46; our deaths cluster at the box's west approach: (7,11) ×5, (11,9) ×4, (12,10) ×3, (8,12) ×3; only 17 of 72 deaths alone, so we also lose group fights | bodies enter the box piecemeal and lose the centre; `aoe_reach5` 2 treats every unseen enemy's area spell as ready at reach 5, which on a 31x31 map may keep most groups "in danger" (ISSUES #16); the single contested altar draws every bank trip into them. Try `aoe_reach5` 1 and 3, P0-4, P0-6, a team gather before entering the box |
| contest_v3 (50x50, one lone monolith per side, gold only, two central altars) | 200–800 at r2000, deaths 45–45, 22 of ours alone, the 200-gem bag lost (§2.4), banks 1 vs 4 | P0-6 first; check with a `LEGEND_TRACE` build whether `mono_mode` fires here (its detector was tuned on the old contest: `mono_center` 0.45); `mono_team` (lone monolith as a team target) was level on v4 |
| nx61x61 (61x61, 11 groups, central 71-gem group) | 611–955 at r2000, deaths 33–16, 19 of 33 alone, gems lost on deaths 262 vs 125, banks 28 vs 51 | the centre group goes to whoever stands on its tiles when it dies (known from the Oct 20 losses); P0-4 and P0-6; `big_reward` won that centre against the Power proxy but lost head-to-head (SUGGESTIONS) |

Method: decode the replays (`node tools/replay/decode.mjs`), trace rounds of the first deaths with `tools/strategy_v2/s13/window.mjs` and
`track.mjs`, and play the map both sides against `_pws`, `_pw` and `_g4`. Write findings into `docs/strategy_v2/` and `AGENTS.md`.

---

## 5. P1: next

### P1-1. Replace the pain map with an enemy-threat map

The pain map (`learn.cpp`; 6x6-tile cells; +1.0 where an ally died, +damage share where we were hit by a champion, −0.6 where an enemy
died, half-life 50 rounds; `group_score()` adds 8 rounds per unit at a group's centre, 4385) records **where** we lost, not **why**, fades on
a timer whether the enemy left or not, is per body, and can push us off our own camps.

Replacement (switch `threat_map`; first compare v7 with `learn_pain` 0, P0-3):
1. **Where each enemy can be now.** Alive and seen `t` rounds ago at P: within `t` tiles of P plus 2 per dash (per 8 rounds). Dead: nowhere
   until `died_round + respawn_time`, then at its spawn, spreading from there (alive flags are global, so every body knows this). A tile this
   body sees with no enemy on it is clear until an enemy could walk back in.
2. `threat(x) = Σ power_e × c_e(x)`, with `c_e` = 1 near a fresh sighting, falling as the possible area grows (≈ 1 / area). Compute it only
   at group centres and on routes (≤ 6 enemies × ≤ 46 groups: no extra distance fields).
3. **Net danger** = max(0, threat − our strength that can be there in time) (claims, visible allies, P0-5 states). Where we are strong the
   cost drops; where we are weak, avoid or ask for an escort.
4. Use it in: farm scoring (instead of the pain cost), routes, flee direction (away from threat and toward allies), recall safety (no enemy
   can arrive within the 5-turn channel), and altar choice.
5. **Opportunities:** with 2+ enemies dead, take camps on their half inside the respawn window (respawn 60 minus their walk back); the bot
   never does this on purpose today. Their camps' respawn timers are known: be there when a camp they farm comes back.
6. Keep location memory only where the place is the cause: a bush where we were hit by an unseen enemy → ward it before entering (a ward
   inside a bush reveals it); a midline group both teams reach at once → go with 2+ bodies; an altar near their spawn → bank elsewhere
   unless escorted.

### P1-2. Learn from why each death happened

On a body's first dead turn, classify the death from a ring buffer of its last ~5 rounds (health, position, visible enemies and their
kits, allies within 6, channel state) and nudge one bounded setting for that body (decaying back over ~200 rounds; log it in traces):

| Death type | Test | Adjustment |
|---|---|---|
| Burst | health ≥ 60% within 3 rounds of death, a spell caster within 5 | remember that enemy's real burst; raise the burst-retreat factor against it; stand one tile farther from it |
| Isolated | no ally within 6 for 3 rounds, 2+ enemies within 5 | `isolated_fight_adv` +0.1 (cap +0.4); prefer camps near allies |
| Opened on | our first damage taken in the engagement came while the enemy was not in our reach the turn before | hold at the edge of their reach (`open_first` style) more strictly against this team; this targets "deaths 121 to 7 when they open" |
| Walked in | we moved toward a visible group in the 3 rounds before contact | add route cost through their reach |
| Channel | died while recalling or banking | that altar unsafe for longer; stricter `safe_to_recall()` |
| Camp | no enemy within 6 | earlier camp retreat (B7) |

With P0-5's spare bits on teams of ≤ 5 bodies, broadcast the death type (3 bits) so allies adjust too.

### P1-3. Passives and effects missing from the fight estimate (`combat()`)

| Effect | Today | Fix |
|---|---|---|
| Heart of Ruin passive (+50% damage at 0% health, linear) | ignored, both sides | multiply that body's damage by `1 + 0.5 × (1 − hp/max_hp)` (engine constant above; it exists only in the 3.0 SDK, so reach it through a `requires` guard like `common.h` does while the compile guard is kept); a low enemy HoR hits ~1.4× harder |
| Shields (Varg 2.5 × focus, HoR 1.5 × focus, 5 turns) | ignored, both sides | add the live shield to effective health; `unit::buffs()` returns shield buffs; check with a probe that it works on visible enemies |
| Durability emblem (−10% damage taken), Jungle vs camps | only in camp farming | apply when known (our build list; for enemies check whether `sdk_champion_items` is readable on visible enemies) |
| Our Ren's retaliation (0.2 × focus per hit taken) | only charged against us | add to our damage while Ren is being hit (B12) |
| Varg's splash in fights | ignored | our Varg × the number of enemies clumped within 1; enemy Varg: avoid standing next to allies (`spread_vs_splash` exists, off) |
| Willow's heal (3 × focus to an ally every 8 rounds) | ignored | add to the healed side's effective health |
| Vendetta's kill reset | ignored | after a kill she has every spell ready again: count a second burst |
| Camps within their real range | `best_d = 4` (B8) | use `g.camps[i].range` |

### P1-4. Enemy Heart of Ruin threat, narrow version

Count an enemy HoR's dash (1.75 × focus, stun) only when it is ready **and** the HoR is within `dash_range + dash_radius + 1` (4) of the
body, and apply it first in `safety()` (burst retreat) and in `handle_channel()`'s stunner check (its landing stun cancels a tribute or a
recall), not in the fight advantage. Add the HoR passive (P1-3). The blunt `burst_dash` lost because it made bodies cautious of every HoR
everywhere; judge the narrow version against `_pws` (whose HoR strikes) and `_pw`.

### P1-5. Opponent learning that changes decisions

`ml2_adapt` (in-match recalibration of the danger model's offset from our own deaths), `mi_learn_burst` (each enemy's real biggest hit) and
`mi_learn_fight` (team fight record) all lost locally, but the local opponents are our own code, so there is little to learn from them.
Re-test them against `_pws` / `_pw` / `_pc`, and treat them as ladder A/B candidates. Add the "who opened each fight and how it ended"
counter from P1-2 as a team-level signal.

### P1-6. Economy and pace (the other half of the losses)

Unopposed v7 needs 1044 rounds to bank 1000; Nyx finished nx60x60 at r757 with us on the map. Known gaps (AGENTS §S14.9, SUGGESTIONS):
first capture r92-171 vs Nyx r18-46; our bodies arrive at a heavy group 10-22 rounds apart and split after the first elk; Nyx's stack
hits 83 per hit vs our 52 (Power builds); 26% of our gold went unspent before `build_tail`. Suggestions:
- **`gold_value` from the map** instead of the fixed 0.33: compute the map's gold-to-gem reward ratio ρ = Σ(gold/respawn) / Σ(gems/respawn)
  at init, and interpolate `0.22 + 0.11 × ln(ρ/4) / ln(2.5)` (0.22 at the pre-patch ratio ≈ 4, 0.33 at ≈ 10; clamp 0.15-0.5); first print ρ
  for the 21 maps and check the two calibration points against them. The existing end-of-game decay stays.
- **Re-test Power-first builds after P0-4 / P1-1.** Nyx's builds (`build_style` 12/13/14) lost locally because of early brawls (4 deaths
  to 2 at r146 on corners, then kill gold snowballed); the support rule and the threat map address exactly those brawls.

### P1-7. Builds that follow the engine (so a hotfix needs no hand re-tune)

The build lists in `build_for()` are typed per champion, and the "damage stat" for the endless tail comes from a hardcoded list of
focus champions (it contains `CT_HOR`). The 3.0.2 hotfix shows why that is fragile: Heart of Ruin's focus shard lost 20% of its value
and nothing in the build noticed. Derive the choice at init from the engine's design for our champion
(`bc::champion_designs[type].base_stats()`: `health_growth`, `strength_growth`, `focus_growth`) and its kit (`kit_of()`):

```
value_focus    ≈ focus_growth    × (sum of the damage modifiers of our focus spells, dash included) / 8   (cooldown 8)
value_strength ≈ strength_growth × (1 + 1/8 with an attack reset) × (splash cluster for Varg)
value_health   ≈ health_growth   × survival weight (tune once; higher for frontliners and for Heart of Ruin's passive)
```

Pick the tail stat (and the stat of Monster / Power emblems) by the larger value; keep the hand lists only for the first two emblems
until the derived version measures level. Check that it reproduces today's choices on 3.0.1 for every champion except where a reason
exists, then measure on 3.0.2.

---

## 6. P2: later

1. **Draft-memory opening plan (B14).** The draft turn has 1M fuel and the whole map: compute a round-1 team assignment (the strongest
   hitters on the nearest heavy group, the dash body on the spawn gold clusters, Nyx-style) and write it to draft memory; bodies read it
   instead of each re-analysing the map.
2. **Synchronized heavy-camp starts** with the WAIT state. Caution: `gather_any` 2 / 3 (gather on every heavy claimed group) lost 22 / 25
   of 42 on v6; the trace showed the stack formed but hit for 52 vs Nyx's 83 and our Issac farmed a lone wolf. Do it only together with a
   composition rule (who joins) and after the damage gap is addressed.
3. **Bush warding after unseen hits** (P1-1 item 6). Warding bushes on every map lost before (`ward_bush`): make it conditional on being hit
   from a bush.
4. **Dead-code cleanup.** 84 settings are 0; many guard code that lost its tests (`mi_*`, `stay_*`, `px_hold`, `px_burst_wait`, `big_reward*`,
   `kill_captures`, `gold_rank`, `pair_plans`, `strike_first`, `engage_angle`, `ring`/`kite` pieces). Remove them in one change whose wasm
   plays v7's games identically (42/42 vs `_g4`, `idle`), so `brain.cpp` becomes readable. Do it after the P0 items are merged, not during.
5. **Fuel on 100x100 maps (ISSUES #12):** count turn rollovers (a turn that runs out of fuel finishes next round) on ambush_v3 and
   nx100x100 with a `LEGEND_TRACE` build ("FUEL low" lines).

---

## 7. ISSUES.md: status at v7 and what to do now

Critical items are marked **▲**.

| # | Issue (ISSUES.md) | Status at v7 | Action |
|---|---|---|---|
| 1 | ring plan fired on any 60x50 objective map | fixed in legend_m15 | none |
| 2 | team gem sum only on maps with ≤ 62 groups | the official max is 46 | none; P0-5 keeps a v1 fallback |
| 3 | capture time literals | `world.cpp` fixed; `group_score()` still uses `6.f` | P0-2 |
| 4-6 | draft thresholds and priors fit on the **old 17-map pool**, and the Heart of Ruin priors fit **before the 3.0.2 hotfix** | the pool changed (6 maps left, 10 new); on the new pool the draft is constant per team size; HoR's scaling dropped ~20% | ▲ re-validate on the 21 maps: print the draft and the map parameters per map (`LEGEND_FEATURES` build) and re-screen the HoR priors on 3.0.2 (P0-1e) |
| 7, 20 | objective detector `obj_min_hp` 4500 etc. | no official map is an objective map now (elk-arena blocked by `pd_obj_side`) | check the `O mode=` trace line per map; keep |
| 8 | lone-monolith (contest) detector `mono_center` 0.45 | unknown whether it fires on contest_v3 | ▲ check with `LEGEND_TRACE` (P0-7) |
| 9 | `pd_obj_multi` | inert on the pool | none |
| 10-11 | economy and fight thresholds tuned against our code family | still true | P0-4 / P1 work replaces several; re-tune after |
| 12 | fuel limits on big maps | unmeasured on the new 100x100 maps | P2-5 |
| 13 | fixed build orders | `build_tail` 1 and `build_react` 2.5 shipped; Heart of Ruin's focus tail is now weaker (hotfix) | ▲ P0-1f for Heart of Ruin, P1-7 (derive the stat from the engine), P1-6 re-test |
| 14 | spell-reach literals (area spells reach 5) | still literal | fold into P1-3 |
| 15 | danger model fixed to its training opponents | retrained on patch-3.0 games for v6; gives allies no net credit (B11) | P0-4; retrain with ally-arrival features when new ladder replays arrive |
| 16 | `aoe_reach5` 2 costs on gem-scarce maps | gem-scarce maps are now official (contest_v3, elk-arena, nx31x31_c4) | ▲ screen `aoe_reach5` 1 / 3 on the 21 maps (P0-7) |
| 17 | altar rule looks only at Chebyshev-1 neighbours | works on boss-battle (1034–94) | none |
| 18 | no teleport crystal to a walled altar | an official map is called "islands" | ▲ identify it (§2.3) and check that we bank there |
| 19 | stall literals | tuned on two maps | low |
| 21 | objective draft on a central group | **fixed in practice** by `pd_obj_side` (elk-arena W 1008–0 in the smoke run) | none |
| 22 | `gold_rank_of()` order | `gold_rank` off | none |
| 23 | compile on the handbook's API | fixed (compile guard) | keep the guard (§1.6) |
| 24 | enemy-locked altar costs 6 steps | open (`lock_hits_sdk` 0) | ▲ P0-2b |
| 25 | tuning chosen by SDK version | the platform runs patch 3.0; the 3.0.2 hotfix has the same SDK headers as 3.0.1, so a compile-time switch cannot even see it | ▲ P0-2a (drop the old branch), P0-2c / P1-7 (read values at runtime) |
| 26 | ward rhythm literal 10 | equals the patch-3.0 cooldown | P0-2b |

Also add to ISSUES.md: B2-B5, B9-B11 and B17 of this file until they are fixed, the `strike_dash_hold` literal, and the hardcoded focus
champion lists in `build_for()` (they include `CT_HOR`).

---

## 8. Workflow and tools

```bash
tools/setup_session.sh                      # toolchain (curl through the proxy CA), sparring bots; see AGENTS §S14.4 (it pins 3.0.1: change it)
pip install --break-system-packages cambc==3.0.2 && cambc --version          # the Heart of Ruin hotfix engine
export LEDGER_DIR=$PWD/experiments/results/ledger_v3_0_2                    # never mix 3.0.2 games with the 3.0.1 rows (B16)
# a variant of GOD with switches:
SRC=bots/god tools/variant.sh _x_v8a hor_strike=2 strike_dash_hold=12      # params.h values; --define MACRO for defines
# or copy and patch: cp -r bots/god bots/_x_v8 && (cd bots/_x_v8 && patch -p1 < ../../experiments/wip/x_v8.patch)
POOL='maps/comp30/*.map26a,maps/nyx_new/*.map26a,maps/loss_oct20/*.map26a'
python3 tools/ledger.py run _x_v8a _g4 --maps "$POOL" --jobs 2         # 42 games, resumable, rows in $LEDGER_DIR
python3 tools/ledger.py table _x_v8a --opps _g4,_pw,_pws,_pc,_mlkc40,idle --maps "$POOL"
python3 tools/samegames.py _x_v8x0 _g8s _g4,idle    # a control (new switches off) must show all games identical to v7 (v7's rows: _g8s; re-run them on 3.0.2 first)
tools/ship_god.sh _x_v8a v8                 # clean build, wasm check, bundle submissions/god.zip, history copy
```

Reading an engine's champion designs (how §2.0 was verified): a bot whose draft turn prints
`bc::champion_designs[i].base_stats()` (`base_health`/`health_growth`, `base_strength`/`strength_growth`, `base_focus`/`focus_growth`) for
`i` = 0..12 (12 = Heart of Ruin) and `bc::constants::*`; run 3 rounds; the lines are in `team-a.stdout` inside the run's `.repl26a`
bundle (it is a zip). Re-run it after every engine update to see what changed.

Panel for every candidate: `_g4` (head-to-head reference), `_pw`, `_pws`, `_pc` (Power / striking-HoR proxies), `_mlkc40` (legend_m15),
`idle` (pace); `_mite`, `_ifish`, `_px9` before shipping. A 42-game cell takes a few minutes on 2 cores.

Replay metrics used in this file (decode with `node tools/replay/decode.mjs REPLAY --out OUT.json`; events have `k`, `r`, `who`, `team`;
deaths are `k == "Death"` with `at`, `bag`, `by`; captures `CaptureGems`; banks `Banked`; per-round champions in `rounds[].ch` as
`[id, team, type, x, y, hp, max_hp, alive, gems, ...]`, type 12 = Heart of Ruin):

```python
import json, collections
d = json.load(open('OUT.json')); R = {r['r']: r for r in d['rounds']}
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
deaths = [e for e in d['events'] if e.get('k') == 'Death']
alone = sum(1 for e in deaths if e['team'] == 0 and R.get(e['r'] - 1) and not any(
    c[1] == 0 and c[7] and c[0] != e['who'] and cheb((c[3], c[4]), e['at']) <= 6 for c in R[e['r'] - 1]['ch']))
lost = collections.Counter(); [lost.update({e['team']: e.get('bag', 0)}) for e in deaths]
banks = collections.Counter(e['team'] for e in d['events'] if e.get('k') == 'Banked')
# Heart of Ruin strikes: slot-1 casts by a type-12 body whose landing tile 'to' is within 1 of an enemy (positions from R[r-1])
```

Report every change with: the cells, deaths both sides, lone deaths, gems lost on deaths, banks, unopposed pace, and for HoR changes the
strike counts.

---

## 9. Do not repeat (lost their tests; details in SUGGESTIONS.md)

Nyx's builds as-is (`build_style` 12: 16/40; 13: 19; 14: 18), earlier recalls (`home_hp` 0.6 / `cap_recall_hp` 0.7: 15/40), `mid_risk`
(22 / 24), `commit_hit` 3 / `max_trips` 8 / `join_reach` 2.0 (no gain), `burst_far` (level), `gold_rank` 1 / 2 and `kill_captures` (worse:
reward hand-offs cost walks), `big_reward` (mixed: wins vs `_pw`, loses head-to-head), `open_follow` (23/42), `dash_box` 3 (27), `cd_hidden`
alone (24), `gather_any` 2 / 3 (22 / 25), `elk_exposure` (21/40), `gold_value` 0.5 / 0.22 (19 / 22), `mono_team` (level), the refit danger model at 0.4
(18/42), forced Marcella / Vesper / Vendetta / Prism-first drafts (our brain does not play them), bush warding on every map, `burst_dash`
(blunt version), `cd_range` 32 on v7 (21/42 vs v7). Some of these may flip once P0-4 / P1-1 change how fights go; re-test only with a reason.

**Exception: re-test after the hotfix.** These were rejected on 3.0.1 and are about Heart of Ruin's strength, so their verdicts do not
carry over to 3.0.2: `pd_hor3` 0, `pd_hor_prior` 0.7 / 0.9, `pd_counter_hor`, `burst_dash`, and every forced draft that contains Heart of Ruin
(P0-0 step 4, P0-1e).
