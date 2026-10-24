# Cambridge Battlecode 2026a — `legend`

A complete, tested C++ bot for CAMBC 2026a, plus the tooling to verify engine rules, generate maps,
benchmark against sparring archetypes, tune by self-play and analyse ladder matches.

| Read this | For |
|---|---|
| [AGENTS.md](AGENTS.md) | **handoff context for AI agents**: status, everything done and measured, setbacks, open work, next steps |
| [docs/strategy_v2/STRATEGY_V2.md](docs/strategy_v2/STRATEGY_V2.md) | **the new strategy (18 Oct)**: why we lose to the top 3 teams, the plan, the rules we miss, the implementation spec, ML/clustering, tests |
| [docs/STRATEGY.md](docs/STRATEGY.md) | how the game is won, hidden techniques, traps, the meta and its counters, the final strategy |
| [docs/ENGINE_FACTS.md](docs/ENGINE_FACTS.md) | every rule we verified on the real engine (with evidence) and fuel costs |
| [docs/HLD.md](docs/HLD.md) | architecture: modules, turn pipeline, data model, navigation, comms, fuel budget |
| [docs/FEEDBACK_LOOP.md](docs/FEEDBACK_LOOP.md) | how to play the top teams, decode the replays and re-tune |
| [docs/LEARNING.md](docs/LEARNING.md) | reward/punishment learning: offline evolution-strategies training and the in-match learners |

## Current build: **GOD v13** (`submissions/god.zip`, Oct 24): v10 + v12 + the Intercontinental Fish data

GOD v13 (`bots/god13`) = GOD v10's brain and dynamic draft + v12's map analysis and draft memory + **the strong teams' per-map pick prior** (weight 1.0; on a known map the top-20 teams' own pick rates, which include IC's table). Studied: IC's 300 matches and 73 replays (`docs/strategy_v2/20_IC_OCT24.md`). Measured on cambc 3.0.5 (40 official maps x 2 sides, paired with v10's own games): **+120.6 gems a map [+25, +221] against the 4 real strong-team rosters**, +55 over all 8 roster families, **+120 against IC's draft** (22 games turned to wins, 12 to losses), 47/80 head-to-head vs v10 (+137 gems a map). Not in it (measured no better in our brain): IC's builds, IC-size bags, kill-value targeting, the live bytes, the capture rule. Anti-IC option: `submissions/candidates/god_v13_anti_ic_20261024.zip` (+ soft ownership: +222 against IC's draft, but worse against the Prism / Willow teams). Previous build GOD v10: `submissions/history/god_v10_20261021.zip`.

## New bot: **GOD v12** (`submissions/god_v12.zip`, Oct 24): everything from Oct 24, every new feature on (the user's request)

GOD v12 (`bots/god12`) = GOD v10 + map analysis + draft memory v2 + the step-7 DL tables + the live bytes + the teamplan rules, every new switch on (`docs/strategy_v2/19_GOD_V12.md`). **It measures worse than GOD v10**: head-to-head 29/80, and -160 gems a map against v10's own games versus 8 strong-team rosters (each feature alone is level with v10; together they interfere). `submissions/god.zip` stayed GOD v10 until GOD v13. A level alternative with only the two best features: `submissions/candidates/god_v12_prior_own_20261024.zip`.

## Previous build: **GOD v10** (session 14, Oct 21): patch 3.0.4, measured on cambc 3.0.4

GOD v10 = GOD v8 + the patch-3.0.4 dynamic draft + what held up from the user's v9 upload and the two improvement plans
(`docs/strategy_v2/18_V9_AND_PLAN.md` has every measurement; the 3.0.4 draft is `docs/strategy_v2/17_PATCH_3_0_4.md`):
- **Dynamic draft** (`pd_stat` 3): a pick's value = fitted weights x features read from the engine's champion designs (health, basic and
  area damage, stuns, dash, range, gold bonus, bodies) and from this map's camps (pack / elk / gold shares, size, spread, monoliths). No
  per-champion number and no per-map table. **v10 refits the weights on 17,004 games of the 156 tuning maps**: the gold bonus now counts
  only on gold-heavy maps, area damage more on pack maps, extra bodies cost more on small maps.
- **Hole-pocket escape** (`pocket_fix` 3): a body that no walk leads home from dashes out (else recalls), instead of burning every turn's fuel.
- **Fights**: camps are counted at their engine range in `safety()` (elk / golem 4, monolith 5; from the upload), our own ready damaging dash
  counts in the fight burst (Heart of Ruin's landing), and a lone body starts a fight only at advantage 1.35 (fight margin 1.4).
- **Insurance**: a watchdog plays a minimal safe turn after 3 throwing turns, and a draft pick that throws falls back to a legal pick.
- **Not taken from the upload**: its opponent model and plan presets lose (44.9% vs v8 with them on, 19.2% against our 3.0.4 bot).

| Measure (cambc 3.0.4, every map both sides) | GOD v10 | dynamic draft `_m1p3` | GOD v8 |
|---|---|---|---|
| Head-to-head vs `_m1p3`, 152 held-out maps | **56.9%** (173/304, p 0.024, +82.5 gems a map) | - | |
| Head-to-head vs `_m1p3`, all 308 maps | **57.3%** (353/616, p 0.0003) | - | |
| vs GOD v8, 152 held-out maps | **79.9%** | 76.3% | - |
| 19 outside opponents (ladder proxies, adapted drafts, personas), 21 official maps | **678/798** | 634/798 | |
| Unopposed pace (rounds to 1000 gems) | **978.8** | 1030.8 | 1099.8 |
| Faults (release mode) | 0 | 0 | 0 |
| Builds on SDK | 3.0.4, 3.0.2, 2.2.5 | 3.0.4, 2.2.5 | 3.0.2, 2.2.5 |

Ladder A/B pair: branches `god-v10-on` (this build) and `god-v10-off` (the dynamic draft alone), each with its own `submissions/god.zip`.

## Previous build: **GOD v8** (session 14, Oct 20): the code review's plan, measured on cambc 3.0.2

GOD v8 implements the review plan (`docs/strategy_v2/GOD_IMPROVEMENT_PLAN.md`; structured plan and every measurement in
`docs/strategy_v2/16_GOD_V8_PLAN.md`). It runs on cambc 3.0.2, which carries the Heart of Ruin hotfix (focus per shard 15 -> 12, strength 5 -> 4).
Each change has a switch in `params.h`, and each one was measured on its own before it was combined:
- **Heart of Ruin**:
  - its strike dash also lands in contact, not only on approach;
  - the shield waits for the strike, because they share the turn's one cast;
  - the dash lands on camp packs (175 damage and a stun at base focus, more than a cluster's 120 health).
  On its own this was +16 games over v7 on five cells and 11 rounds faster unopposed.
- **Fights count support by timing**: an ally counts as much as it can arrive before our body would die, and not at all if it would be focused down first or is walking away. The old rule counted every ally within 6 at full weight. Alone: +10.
- **Bag escort**: a bag of 60+ gems is not tributed at an altar where an enemy was just seen until two healthy allies stand by. The carrier calls them with an ESCORT alert, and a fight's RALLY never overwrites a fresh OPPORTUNITY or ESCORT. Alone: +12. Traced loss on contest: a 200-gem bag is a 20-turn channel, and v7 lost it there.
- **The pain map is off**: alone it measured +3 with it off.
- **Only patch-3.0 values remain**: the old-ruleset branch is gone (wasm identical on 3.0.x), and the source still compiles on the 2.2.5 API.

| Measure (cambc 3.0.2, the 21 official maps, both sides, 42 games per cell) | GOD v8 | GOD v7 |
|---|---|---|
| Head-to-head vs GOD v7 | **22** | - |
| vs GOD v2 / legend_m15 | **35 / 33** | 31 / 28 |
| vs the Heart of Ruin proxies `_pws` (striking HoR) / `_pw` / `_pc` | **33 / 39 / 37** | 25 / 31 / 36 |
| vs `_mite` / `_ifish` / `_px9` | 42 / 37 / 36 | 40 / 39 / 36 |
| Unopposed pace (rounds to 1000 gems) | **1040.0** | 1045.5 |
| SDK 2.2.5 | builds | builds |

## Previous build: **GOD v7** (session 14, Oct 20): GOD v6 + Heart of Ruin's strike dash

Heart of Ruin's dash is its main fight spell (1.75 x focus damage and a stun around the landing tile), but GOD v6 never used it in a fight: only
the ranged branch of the engage code allowed a strike dash, and Heart of Ruin is melee. GOD v7 dashes onto a tile within range that puts the
target, and as many other enemies as possible, inside the landing radius. Only games with Heart of Ruin on a side change; everything else plays
GOD v6's games. The official pool (21 maps, pulled by the user) is the test pool.

| Measure (cambc 3.0.1, the 21 official maps, both sides, 42 games per cell) | GOD v7 | GOD v6 |
|---|---|---|
| Head-to-head vs GOD v2 | **31** | 30 |
| vs the Heart of Ruin Power proxy / the Prism, Marcella, Heart of Ruin proxy | **35 / 39** | 32 / 38 |
| vs legend_m15 | **29** | 25 |
| Unopposed pace (rounds to 1000 gems) | 1044.1 (same 42 games) | 1044.1 |
| SDK 2.2.5 (the handbook's rules) | builds, plays v6's games | |

## Previous build: **GOD v6** (`submissions/god.zip`, session 14, Oct 20): GOD v5.1 + the lessons of 25 ladder losses

GOD v3 lost 25 ladder games to five top teams (`docs/strategy_v2/15_LOSSES_OCT20.md`): every one of them stacks Power emblems in its damage
stat (6,542 damage points to our 2,739), opens fights on our own half (our deaths 121 to their 7 when they open), spreads its gold over the
team, and 26% of our gold was never spent. GOD v6 keeps what measured better on the 21 maps of those games: the build never ends (Power in
the damage stat once the list is done), a reactive health emblem whenever our max health falls below 2.5 x the biggest burst a visible enemy
has shown, the objective draft only for a gem group on our side of the map (the Prism / Tavi misdraft on nx50x50 cost two games), draft
priors that put Heart of Ruin in the pair's slot against bruiser picks seen before ours (nothing forced, nothing per map), and the danger
model retrained on the 45 patch-3.0 games. Both rulesets: without Heart of Ruin in the SDK it plays GOD v5.1's old-rules game (legend_m15's
values and model weights). Every switch is in `params.h`; `experiments/wip/x_g5.patch` on GOD v2 is the full diff.

| Measure (cambc 3.0.1, the 21 maps of the Nyx and loss games, both sides, 42 games per cell) | GOD v6 | GOD v5 |
|---|---|---|
| Head-to-head vs GOD v2 (`_g4`) | **30/42** (deaths 637-872) | 28/42 (697-754) |
| vs the Power-stacking ladder proxies `_pw` / `_pc` / `_ph` | **32 / 38 / 33** | 30 / 34 / 31 |
| vs `_mite` / `_ifish` / `_px9` | 39 / 39 / 37 | 40 / 35 / 34 |
| vs legend_m15 (`_m15`) | 25/42 | 30/42 |
| Unopposed pace, rounds to 1000 gems (20 maps) | 1037.1 | 1039.6 |
| SDK 2.2.5 (the handbook's rules): official 34, head-to-head vs legend_m15 | 18/34 | 18/34 (GOD v5.1) |

The weak cell is legend_m15 (the pre-patch bot): the retrained danger model leaves fights earlier against our own old code family, while
it gains against every Power-stacking proxy. The ladder is the real test; `submissions/history/god_v5_1_20261020.zip` is the rollback.

## Previous build: **GOD v5.1** (`submissions/god.zip`, session 15, Oct 20): GOD v5 for both rulesets

The sprint documents (`docs/sprint/GameRules.md`, `BotAPICpp.md`) describe the game before patch 3.0 and an API without Heart of Ruin, Golem or
the damaging dash fields; GOD v5 named all three and **did not compile against that API** (a failed compile removes the team from matchmaking).
GOD v5.1 names them through `requires`-expressions (`common.h`: `SDK_HAS_HOR`, `CT_HOR`, `D_HOR`, `CAMP_GOLEM`) and, when the SDK has no Heart of
Ruin, takes legend_m15's values for the seven settings that were tuned for patch 3.0. Details: `docs/sprint/RULES_DIFF.md`.

| Engine the platform compiles with | What GOD v5.1 is | Measured |
|---|---|---|
| cambc 3.0.x (patch 3.0, Heart of Ruin) | **byte-identical wasm to GOD v5** | GOD v5's numbers below |
| cambc 2.2.x / the handbook's API (old balance) | GOD with legend_m15's settings (`_go_all0`, byte-identical wasm) | official 34 vs the 5 proxies 148/170 (legend_m15 149, GOD v5's settings 127); h2h vs legend_m15 18/34 |

## Previous build: **GOD v5** (`submissions/god.zip`, session 14, Oct 20): GOD v4 + the burst retreat

Against Nyx (20 ladder games after patch 3.0) 51% of our deaths were bursts from 60%+ health, 49% by ranged champions stacking Power
emblems in their damage stat: one Stellar cast plus a hit took half a body's health. GOD v5 retreats one cast earlier: `safety()` leaves when
our health is below 1.2 x the burst an enemy in reach can land this turn (its best ready spell plus one hit), the damage read from the enemy's
visible stats each turn (nothing is hardcoded per opponent). Everything else as GOD v4.

| Measure (cambc 3.0.1, the 20 maps Nyx played, both sides) | GOD v5 | GOD v4 | GOD v3 | GOD v2 |
|---|---|---|---|---|
| head-to-head vs GOD v2 | **27/40** (deaths 654-727) | 25/40 | 25/40 | - |
| vs `legend_m15` | 29/40 | 30/40 | 27/40 | 29/40 |
| vs the proxies `_mite` / `_ifish` / `_px9` | **38 / 33 / 32** | 35 / 31 / 30 | 35 / 31 / 30 | 34 / 31 / 30 |
| unopposed pace (rounds to 1,000) | 1039.6 | 1034.4 | 1108.9 | 1115.8 |

## Previous build: **GOD v4** (session 14, Oct 20): GOD v3 + the camp-blocked altar unlock

On the new 50x41 map the only altar's only approach tile is a monolith's spawn tile. GOD v3 plays that map for gold (no banking); GOD v4
knows the altar opens when that camp is dead: the two-monolith group (40,000 health, 400 gems) becomes a team target once the living team
can clear it, and the team then banks from the dead tile (a body standing there also stops the respawn). Against GOD v2 it wins that map
1092-0 and 1054-0 (both were 0-0 gold races); against `legend_m15` 1013-0 at round 679. Everything else as GOD v3.

| Measure (cambc 3.0.1, the 20 maps Nyx played, both sides) | GOD v4 | GOD v3 | GOD v2 |
|---|---|---|---|
| head-to-head vs GOD v2 | **25/40** | 25/40 | - |
| vs `legend_m15` | **30/40** | 27/40 | 29/40 |
| vs the proxies `_mite` / `_ifish` / `_px9` | 35 / 31 / 30 | 35 / 31 / 30 | 34 / 31 / 30 |
| unopposed pace (rounds to 1,000) | 1034.4 | 1108.9 | 1115.8 |

## Previous build: **GOD v3** (`submissions/god.zip`, session 14, Oct 20): the stalls seen against Nyx fixed

GOD v2 lost 17 of 20 games to the team Nyx after patch 3.0 (`experiments/nyx_oct20`). Three of those games were thrown by hard stalls:
on a map whose only altar has a monolith's spawn tile as its only neighbour, all six bodies stood for 1,000+ rounds trying to step onto
the camp (now: camp tiles are never altar approach tiles, and a map with no usable altar is played for gold earned and kills, the
round-2000 tiebreaks); on a hole-maze map a body waited 1,197 rounds at a chained hole crossing for a dash the field could not use (now:
a dash that gains one step is taken, and any walking task that stalls drops its target and its hole routing for a while); the objective
draft (Prism, Tavi) fired on a map whose lone gem group is small (now: the draft needs a heavy group, like the brain's objective mode).

| Measure (cambc 3.0.1, the 20 maps Nyx played, both sides) | GOD v3 | GOD v2 |
|---|---|---|
| head-to-head vs GOD v2 | **25/40** (deaths 678-748) | - |
| vs `legend_m15` | 27/40 | 29/40 |
| vs the proxies `_mite` / `_ifish` / `_px9` | 35 / 31 / 30 of 40 | 34 / 31 / 30 |

What Nyx does better and what did not transfer (Nyx's Power-stacking builds, earlier recalls): AGENTS.md §S14.9, SUGGESTIONS.md.

## Previous build: **GOD v2** (`submissions/god.zip`, session 13, Oct 20): `legend_m15` rebuilt for balance patch 3.0

The Oct 20 patch (cambc 3.0.1) re-balanced every champion, cut camp rewards (wolf 4 gems, elk 15, gem cluster 7), added the Golem camp
and the champion Heart of Ruin, doubled kill gold and made elks (4) and monoliths (5) hit from farther. GOD = `legend_m15` plus:

- camp attack ranges read from the engine instead of an assumed 3 (danger zones, the objective ring and the kite plan stand one tile
  outside the real range and count only spells that reach);
- Heart of Ruin: item builds, its dash counted as burst and held for fights (it lands for 1.75 x focus and stuns), drafted instead of
  Cassi & Issac on 3-champion maps;
- golem camps in the map analysis; gold valued 0.33 gems (was 0.22): a wolf now pays 4 gems and 40 gold.

| Measure (cambc 3.0.1; proxies = our code with the top teams' drafts / builds) | GOD v2 | `legend_m15` |
|---|---|---|
| official map files vs the 5 proxies | **158/170** | 130/170 |
| head-to-head (official / patch-style maps) | **25/34, 23/34** | - |
| patch-style maps (`maps/p30`) vs Mite / ifish / `_px9` | **81/102** | 64/102 |
| unopposed pace, patch-style maps (rounds to 1000) | 834 | 877 |

The new official map pool could not be downloaded here (the environment blocks 2026a.battlecode.co.uk), so the patch-style maps stand in
for it. `submissions/legend.zip` (`legend_m15`) still compiles on 3.0.1.

## Previous build: `legend_m15` (session 13, Oct 20): a danger model learned from the ladder

`submissions/legend.zip` = `legend_m15` (`submissions/history/legend_m15_20261020.zip`). It is `legend_m14_commit` (the bot the user made
the main one on Oct 19) plus:

- **a fight / danger model trained on 160 decoded ladder games** (logistic regression, P(die within 8 rounds) from 58 features of the
  visible state; weights in `bots/legend/src/ml2_model.h`, trainer `tools/ml/ml2_train.py`). On our ladder bodies it ranks deaths with
  AUC 0.81, against 0.60 for the bot's own fight estimate. Used three ways: an escapable fight is dropped when P >= 0.4, a body walks
  away before contact when P >= 0.4, and a deadly state counts as cornered (the body trades instead of giving free hits);
- enemy area spells counted at reach 5 (radius 1 at range 4), a hold at the edge of enemy reach while our opener is ready, a shop / heal
  recall cancelled to join a fight next to us, and no 60x50 size term in the objective ring (ISSUES.md #1).

| Measure (local; the proxies are our own code with the ladder teams' drafts / builds) | `legend_m15` | `legend_m14_commit` |
|---|---|---|
| official 34 games vs the 5 proxies (`_mite _ifish _px9 _snk _fA`), pooled | **149/170** | 129/170 |
| 67 more maps (generated, resized official, fresh generated) vs the 5 proxies | **475/670** | 452/670 |
| our deaths on those 670 games | **3,725** | 4,297 |
| head-to-head vs `legend_m14_commit` (official / 67 maps) | 22/34, 71/134 | - |
| unopposed pace, 17 official maps (rounds to 1000) | 508.1 | 502.7 |

Rejected this session (SUGGESTIONS.md): Willow + two tanks and five other draft changes, finish-the-race endgame scoring, fight-for-big-rewards,
grouped stance, bigger rally radius, bush ghosts, melee hold, strike-first, engage angle, draft-time farming zones.

## Previous build: `legend_m14` (session 7R, Oct 18, 23:50 UTC): no map-size rules

`legend_m13` with its two remaining map-size rules replaced by map features, for the final sprint's new map pool: the stampede caster
ring now runs on any objective map when we drafted Prism or Tavi with 5 champions (was: only 60x50 maps), and the contest plan runs on
any lone-monolith map whose monoliths stand in the middle (was: only 50x50). On the 17 official maps it plays the same games as m13.

| Map pool (win % vs Mite, ifish, `_px9`, sneaky, `_fA` proxies) | m12 | m13 | **m14** |
|---|---|---|---|
| 17 official maps (170 games) | 79.4 | 79.4 | **79.4** (same games) |
| Official maps at new sizes (16 maps, 160) | 65.6 | 69.4 | **73.1** |
| Objective maps, resized / transposed stampede (12, 120) | 64.2 | 59.2 | **79.2** |
| Contest at 6 new sizes + perturbed (13, 130) | 96.2 | 60.0 | **96.2** |
| 24 fresh generated maps (240) | 66.7 | 66.7 | **66.7** (same games) |
| Held-out gem-scarce + objective (78 maps, 468 vs Mite, `_px9`, ifish) | 72.0 | 72.0 | **74.6** |

## Previous build: `legend_m13` (session 7R, Oct 18, 22:40 UTC): parameter draft

`legend_m12b` + a parameter draft (`mapdraft` 6): when the map is revealed it is analysed first (team size, share of wolf packs, share of
elk camps, lone gem group, monoliths only, open small map); the first pick comes from those parameters and every later pick from map fit,
team synergy and the enemy's picks so far. No per-map table. It reproduces the old per-map picks on every known map (51/51 official x 3
enemies, 27/27 generated), so it plays the same games as `legend_m12b` there, and keeps the intended picks on transposed / side-swapped
copies of the official maps (51/51; the old model 47/51). Details: `submissions/BUILDS.md`, AGENTS.md §S7R.

## Previous build: `legend_m12b` (session 7R, Oct 18): ready for the ladder

`legend_m12b` = `legend_m12` with the contest plan restricted to 50x50 maps (contest and its copies): identical games on all 17 official maps,
and `legend_m10`'s play on generated monolith-only maps of other sizes (where the plan had lost). The table below is `legend_m12`'s (same games).

`legend_m12` plays `legend_m10`'s proven game everywhere, and on contest-type maps (gems only in lone monoliths) it opens as one group until
round 200 and wards the bushes. `legend_m11` warded bushes on every map: that beat our own older builds but lost to the top-team proxies (and,
per the user, on the top ladder); `legend_m12` keeps the warding only where it wins.

| Official 17 maps x 2 sides vs | `legend_m12` | `legend_m10` | `legend_m11` |
|---|---|---|---|
| Mite proxy (#2 team) | **85.3%** | 82.4% | 76.5% |
| ifish proxy (#1 team) | **79.4%** | 79.4% | 70.6% |
| `_px9` (ladder-calibrated) | 76.5% | 76.5% | 79.4% |
| sneaky-bush proxy | **67.6%** | 61.8% | 67.6% |
| `_fA` (pressure) | **88.2%** | 82.4% | 76.5% |
| contest pool, 68 games, vs `legend_m8` / Mite / sneaky | **88.2 / 95.6 / 97.1** | 50 / 60 / 38 (CT4/CT34 cells) | 88.2 / 95.6 / 97.1 |

Head-to-head vs `legend_m8` 52.3% (official 52.9%), vs `legend_m10` 51.1% (52.9%). Full numbers: `submissions/BUILDS.md`.

## Previous build: `legend_m11` (session 7R, Oct 18): ready for the ladder

`legend_m11` = `legend_m10` (= `legend_m8`'s play) + **bush warding** (a ward inside a bush reveals champions hiding there; we now ward a bush
tile within 2 when one is in reach, as the sneaky-bush ladder team does with every ward) + **a grouped opening on contest-type maps** (the bodies
farm together until round 200 instead of arriving one by one at the centre fight we lost in every ladder contest game).

| Opponent | `legend_m11` |
|---|---|
| `legend_m8` (previous best), 88 distinct games / official 34 | **52.3% / 67.6%** (deaths 593-712) |
| contest pool (68 games) vs `legend_m8` / Mite proxy / sneaky-bush proxy | **88.2% / 95.6% / 97.1%** (old play vs the sneaky proxy: 38.2%) |
| held-out maps (100 games, warding alone) vs Mite / `_px9` proxies | 87.0% / 74.0% (`legend_m10`: 79.0% / 66.0%) |

Previous: `legend_m10` (`submissions/history/legend_m10_20261018.zip`). Full numbers: `submissions/BUILDS.md`.

## Previous build: `legend_m10` (session 11): `legend_m8`'s play, ready for the ladder check

`submissions/legend.zip` = `legend_m10`. It plays exactly as `legend_m8` (the results table below applies: it takes the two top
teams' per-map draft choices where they beat ours and Mite's stampede plan). The 17 ideas from the repository's default branch
(`claude/lucid-pasteur-2jiojv`, the Oct 16 "round-2" bot) are in the code behind `mi_*` switches, all off: switched on together
(`legend_m9`, shipped briefly at the user's request) they lost to every sparring opponent (Mite proxy 63.6% vs 76.1%, ifish proxy
51.1% vs 69.3%, `_px9` 65.9% vs 78.4%). Per-idea numbers and what stays off: AGENTS.md §S11. Ladder feedback decides the next step.

## Results of `legend_m8` (session 10, Oct 18; 44 distinct maps × both sides = 88 games per row)

`legend_m8` = `legend_m7` + what the two top teams do against each other (13 games of Intercontinental Fish vs Mite,
`experiments/interwin_oct18/`): both draft from a fixed per-map table, and where their choice beat ours in our own brain we
take it: Ryth instead of Varg on rushbait-v2 and interlock, Cassi & Issac, Stellar, Varg on expanse, and on stampede Mite's
all-caster draft (Prism, Stellar, Cassi & Issac, Ryth, Tavi) clearing the 6-elk objective from distance 4 (the ring plan),
as Mite did to beat ifish 1080-0 and 1008-0. Everywhere else the bot is unchanged. Pace 503.8 rounds (`legend_m7` 520.9;
stampede 471/479 instead of 704/765). On those four maps it wins 44 of 48 games against six opponents (`legend_m7`: 26).
Sparring proxies of the two teams (their per-map drafts and builds, Mite's stampede plan) are `_mite` and `_ifish`.

| Opponent | `legend_m8` | deaths (ours-theirs) | `legend_m7` on the same games |
|---|---|---|---|
| `legend_m7` (previous ship) | **53.4%** (55.9); held-out maps 48.0% (the change does not act there: 85% of games identical) | 641-653 | - |
| `_mite` (Mite proxy) | **76.1%** (82.4) | 588-806 | 75.0% (73.5) |
| `_ifish` (ifish proxy) | **69.3%** (79.4) | 638-649 | 65.9% (67.6) |
| `_px9` ladder-calibrated proxy | **78.4%** (76.5) | 589-682 | 73.9% (67.6) |
| `_fA` pressure archetype | **73.9%** (82.4) | 687-920 | 70.5% (73.5) |
| `legend_m6` | **68.2%** (79.4) | 584-725 | 63.8% (70.6) |
| `legend_st` | **83.0%** (91.2) | 491-899 | 78.4% (82.4) |

### Options measured in session 10 and kept for future updates (not in `legend_m8`)

Every option below was A/B tested against the previous bot (`legend_m8`) and against the sparring panel; none was a better
trade, so they stay off. Code: `experiments/wip/x_s10_tests.patch` (switches on top of `legend_m8`'s sources).

| Option | How it works | Result vs `legend_m8` (88 distinct games / official 34) | Why kept off |
|---|---|---|---|
| **Counter-pick draft** (`last_pick`, `last_pick_size`) | Picks are simultaneous per round, but `bc::draft::current_draft(team::enemy)` returns the enemy's completed rounds, so our last pick sees their first 3-4 picks. Plan: commit the safe picks first (Ren, Stellar, Cassi & Issac: in every top-team draft), counter in the last round, fill by map features | 5th pick on 5-champion maps against Varg-first enemies (Mite, `_px9`) / Ren-first enemies (ifish, `_fA`): **Ryth (ours) 76% / 71%**, Marcella 59 / 65, Prism 58 / 63, Vendetta 58 / 62, Tavi 56 / 48. 4th pick on 4-champion maps: Varg (ours) 75 / 75, Ryth 58 / 58 | our current last picks are already the best answer to both enemy profiles; revisit when a new enemy profile appears (e.g. a different first pick on the ladder) |
| Shop when passing within 2-4 steps of spawn with 60-120 gold (`shop_near_dist`, `shop_near_gold`) | detour onto spawn to buy shards | 50.0 / 48.9 / 50.0 | changes 1-7 games in 88: walking home at 150 gold within 9 steps and recall-to-shop already cover it |
| Reward gold to the champion that uses it best (`gold_rank` 1: Stellar, Varg, Cassi, Issac, Ryth, Ren; 2: Stellar only) | when two of our bodies want one reward, the better gold user captures it instead of the lower index | 48.9 / 44.1; 47.7 / 47.1 | fewer deaths but slower farming |
| Camp-damage emblem first for Ren / Ryth (`dmg_first`) | Monster before the first health emblem (Stellar, Cassi, Issac and Varg already buy it first) | Ren 54.5 / 41.2; Ryth 53.4 / 52.9 but every third-party cell 2-6 points lower; both 46.6 / 41.2 | not a better trade |
| Hold for the spell before opening a fight (`strike_first=1`) | wait up to 2 rounds outside reach when a spell is about to come off cooldown | 59.1 / 61.8 head-to-head, but 50.0 over 188 games with the held-out maps, and lower against 6 of 7 other opponents (Mite proxy 69.3 vs 76.1) | beats only our own previous build |
| Mite's or ifish's whole per-map draft table | `mapdraft` 1 / 2 | no map better than ours beyond noise | `legend_m8` already takes their choices where they win |
| The default branch's 17 ideas (`mi_*` switches, `experiments/wip/x_mi.patch`; session 11) | the Oct 16 round-2 bot's fight record, learned enemy burst, lethal leave, danger slack, endgame banking, kiting, chip spells, flip guard, two-body cap, gem-only deny, relaxed rescoring, recall to shop, island bank, close-in, health emblem second | all on (`legend_m9`): 58.0 / 35.3 vs `legend_m8`; alone, the best are fight record 55.7 / 58.8, gem-only deny 54.5 / 61.8, flip guard 54.5 / 58.8, chip 54.5 / 50.0 | every one is worse than `legend_m8` against the outside opponents (fight record: `_px9` 65.9 vs 78.4; learned burst: `_px9` 64.8); all off in `legend_m10` |
| **Sneaky-bush team's per-map draft** (session 7R; their 17 ladder games vs `legend_m8`/`m10`, `experiments/sneaky_oct18/`) | `mapdraft` 4 = their table everywhere; `md_sneaky` = their choice on chosen official maps only (`experiments/wip/x_sn.patch`) | per-map screen on the 11 maps where they differ, 17 opponents x 2 sides: **256 vs 300 wins for ours**; worse on 8 maps (rows 20 vs 33, elkring 19 vs 27, monolith 19 vs 26). Only contest (+6) and collision (+3) gained, and both lost on side-swapped / transposed copies of those maps (contest 25 vs 36, collision 33 vs 37 over 54 games each) | our code plays Tavi, Willow and Vendetta worse than the champions they replace; the official-map gains were layout-specific. Their proxy `_snk` (their draft + Mite-style builds) stays in the sparring panel |
| ifish-style pressure on the enemy half (`enemy_half_penalty` 10 -> 6; `fight_margin` 1.30 -> 1.2) | farm and fight more on their side, take fights at a smaller margin | 51.1 / 47.1; 51.1 / 52.9 | penalty 6: Mite proxy 70.5 vs 76.1; margin 1.2: Mite proxy 77.3 (88.2 official) but ifish proxy 63.6 vs 69.3, `_px9` 70.5 vs 78.4 |

## Results of `legend_m7` (session 9, Oct 18; 44 distinct maps × both sides = 88 games per row)

`legend_m7` = `legend_m6` + two changes taken from 15 games of the top 3 teams playing **each other**
(`docs/strategy_v2/08_TOP3_VS_TOP3.md`): area spells (Stellar, Prism) are aimed so their radius catches enemies at
distance 5 (the top teams land 20-28% of their spell damage there, we landed 3-8%), and Cassi & Issac buy damage before
health (our Cassi had 70 focus at round 300, theirs 195-248). Pace 520.9 rounds (unopposed, 17 official maps).

| Opponent | `legend_m7` | deaths (ours-theirs) | `legend_m6` on the same games |
|---|---|---|---|
| `legend_m6` (previous ship) | **65.9%** (70.6); held-out maps 62.0% | 649-709 | - |
| `_px9` ladder-calibrated proxy | **73.9%** (67.6) | 602-675 | 58.0% (64.7) |
| `_f2q` proxy that casts its areas from 5 like the top teams | 53.4% (41.2) | 678-586 | 44.3% (41.2) |
| `_fA` pressure archetype | 70.5% (73.5) | 724-932 | 72.7% (82.4) |
| `legend_st` | 78.4% (82.4) | 520-916 | 73.9% (82.4) |

## Results of `legend_m6` (session 8, Oct 18 evening; 44 distinct maps × both sides = 88 games per row)

`legend_m6` = `legend_m5` + the top teams' targeting, learned from 60 ladder games of `legend_m5` against the top 3
(`docs/strategy_v2/07_LADDER_M5_18OCT.md`): hit the body we can hit this turn with the lowest health, take every kill the
team can finish this turn, stun the target first, and count an awake camp that is hitting an enemy as our damage. Tested
also against `_px9`, a sparring proxy calibrated on those ladder games (it beats `legend_m5` 64.7% on the official maps).

| Opponent | `legend_m6` | deaths (ours-theirs) | `legend_m5` on the same games |
|---|---|---|---|
| `legend_m5` (previous ship) | **52.3%** (61.8); held-out maps 59.0% | 580-710 | - |
| `_px9` ladder-calibrated proxy (official 17) | **64.7%** | 348-352 | 35.3% |
| `_fA` pressure archetype | 72.7% (82.4) | 561-1015 | 76.1% (79.4) |
| `legend_st` | 73.9% (82.4) | 465-909 | 73.9% (91.2) |
| `_eA` / `_eB` / `_eC` archetypes | 71.6% / 79.5% / 88.6% | | 68.2% / 77.3% / 87.5% |
| `legend_m4` | 53.4% (47.1) | 572-683 | 61.4% (58.8) |

## Results of `legend_m5` (session 8, Oct 18; 44 distinct maps × both sides = 88 games per row)

`legend_m5` = `legend_m4` + strategy-v2 fight execution (`experiments/wip/x_exec.patch`: hit what is in reach before
walking, melee swings before stepping away, keep fighting once committed) + the 16 parameters the A100 RL run moved
consistently (fight/flee thresholds, threat memory, bigger bags, defence of our half; `experiments/wip/rl_a100_m5a_args.txt`,
analysis in `experiments/rl_a100_20261018/`). Pace 523.4 rounds to 1000 gems (unopposed, 17 official maps). The 44 maps are
the 17 official ones plus the 27 generated ones (no `maps/ladder/` copies, which replay official maps). Official-map rates
in brackets. Every game is in `experiments/results/ledger/` (`python3 tools/ledger_sum.py --pool 'maps/*.map26a,maps/comp/*.map26a' _m5a`).

| Opponent | `legend_m5` | deaths (ours-theirs) | `legend_m4` on the same games |
|---|---|---|---|
| `legend_m4` (previous ship) | **61.4%** (58.8) | 565-673 | - |
| `_fA` pressure archetype on `legend_m4` code | **76.1%** (79.4) | 611-956 | 63.6% (64.7) |
| `legend_st` (on the ladder Oct 18: 1 win in 17) | 73.9% (91.2) | 526-849 | 73.9% (70.6) |
| `legend_rm` | 65.9% (76.5) | 521-862 | 63.6% (79.4) |
| `legend_m2` | 53.4% (55.9) | 603-595 | 56.8% (58.8) |
| `_eA` Ren-first pressure archetype | 68.2% (76.5) | 710-1109 | 70.5% (94.1) |
| `_eB` C&I-first farming archetype | 77.3% (94.1) | 534-976 | 79.5% (94.1) |
| `_eC` caster objective archetype | 87.5% (88.2) | 516-1043 | 81.8% (91.2) |

## Results of `legend_m4` (session 7, Oct 18; 56 maps × both sides = 112 games per row)

`legend_m4` = `legend_rm` + the `survive` agent's early retreat from outmatched groups (and from one stronger enemy;
Cassi & Issac leave earlier; Ren's retaliation counted) + the `farm` agent's farming fixes (no split rewards, the
first body on a reward keeps it, up to 3 bodies on a heavy group only when they arrive in time, Varg's splash position,
objective focus) + a fixed farm give-up clock (bodies no longer drop a group after 60 rounds on it). Unopposed it banks
1000 gems in 524.5 rounds on the 17 official maps (`legend_rm` 579). Official-map rates (`maps/comp/`, the real ladder
pool) in brackets. Every game is in `experiments/results/ledger/` (`python3 tools/ledger_sum.py _m4`).

| Opponent | `legend_m4` | deaths (ours-theirs) |
|---|---|---|
| `legend_m2` (previous ship) | **58.0%** (58.8) | 770-732 |
| `legend_rm` | **67.0%** (79.4) | 902-1187 |
| `legend_st` (on the ladder Oct 18: 1 win in 17) | **73.2%** (70.6) | 958-1114 |
| `_eA` Ren-first pressure archetype | 75.0% (94.1) | 840-1710 |
| `_eB` C&I-first farming archetype | 82.1% (94.1) | 675-1559 |
| `_eC` caster objective archetype | 83.9% (91.2) | 686-1319 |

## Results (local, 56 maps × both sides = 112 games per row; session 3, Oct 17)

The 56 maps are the 17 official ladder maps (`maps/comp/`, the real pool), 12 real ladder maps rebuilt from replays
(`maps/ladder/`) and 27 generated ones. Opponents are frozen past versions of this bot and aggressive archetypes with
the top ladder teams' drafts (`tools/make_sparring.sh`). Official-map-only rates in brackets.

| Opponent | `legend` (submitted on the ladder Oct 17, `_L0`) | `legend` now (`legend_c3`) |
|---|---|---|
| the Oct 17 ladder build (`_L0`) | — | **60.7%** (61.8) |
| `_r2` (commit 4a3920d) | 60.0% | **79.5%** (73.5) |
| `_v6` (first rewrite) | 73.3% | **91.1%** (97.1) |
| aggressive Stellar/C&I draft (`_devci`) | 76.7% | **90.2%** (91.2) |
| aggressive C&I hunter (`_hunt2`) | 95.6% | **99.1%** (100) |

These opponents are all our own code family. The user's audit of 40 real ladder games of `_L0` (5 wins) found we
collect half the gems of the top teams and die twice as often; the session-3 changes target exactly that (deaths
against `_devci` fell from 1,784 to 796 per 112 games). Build-by-build numbers: [`submissions/BUILDS.md`](submissions/BUILDS.md).

What changed and why: [docs/STRATEGY.md](docs/STRATEGY.md) §1. How the bot learns:
[docs/LEARNING.md](docs/LEARNING.md).

## Ready-to-submit ZIP

[`submissions/legend.zip`](submissions/legend.zip) is `cambc bundle legend` output (the bot's `src/` only).
Upload it on the platform's Submissions page, or submit from the CLI with `cambc login && cambc submit legend`.
Rebuild it after changing the bot: `cambc bundle legend --output submissions/legend.zip` (delete the old file first).
Every recommended build, with its commit and measured results, is logged in
[`submissions/BUILDS.md`](submissions/BUILDS.md); previous zips are kept in `submissions/history/`.

## Quick start

```bash
pip install cambc
cambc init .            # adds the C++ SDK (sdk/, cmake/; git-ignored). Choose C++.
cambc build legend
cambc run legend starter-cpp --map gen10_62x66_R_c4 --view
python3 tools/bench.py legend starter-cpp          # all maps, both sides
tools/suite.sh legend                              # vs the sparring panel (build it first, below)
cambc submit legend                                # needs `cambc login`
```

Sparring opponents are generated, not committed. `tools/make_sparring.sh` rebuilds the whole current panel
(`_base`, `_v6`, `_r2`, `_hunt`, `_hunt2`, `_devci`) from commits, identical to the bots behind the result tables.
The individual recipes:

```bash
tools/snapshot.sh _base 6bb913e                    # old bot (v5), what was on the ladder on Oct 16
SRC=bots/legend tools/variant.sh _hunt learn_enabled=0 fight_margin=0.95f fight_back_margin=0.6f enemy_half_penalty=0.f \
    deny_bonus=1.5f steal_hp_frac=0.3f deathball_until=110 deficit_defend=99 deficit_escort=99 --define "LEGEND_DRAFT 8,4,3,0,9"
SRC=bots/legend tools/variant.sh _hunt2 learn_enabled=0 fight_margin=0.9f fight_back_margin=0.6f enemy_half_penalty=2.f \
    deny_bonus=1.2f steal_hp_frac=0.4f isolated_fight_adv=1.0f deficit_defend=99 deficit_escort=99 --define "LEGEND_DRAFT 3,2,9,0,4"
SRC=bots/legend tools/variant.sh _devci learn_enabled=0 --define "LEGEND_DRAFT 4,3,9,10,8"
tools/panel.sh legend 'maps/*.map26a,maps/ladder/*.map26a' _base _hunt _hunt2 _devci starter-cpp idle
```

The second map pool (40 maps) is reproducible: `node tools/mapgen/gen.mjs maps 40 991 s2_`.
Island maps (camps behind walls, teleport-crystal test): `node tools/mapgen/island.mjs maps`.
Real competition maps: `cambc maps pull` (needs network access to the platform).

### Train the bot yourself

`tools/rl/train_local.sh` trains the parameters on your own machine with one command. It sets up the SDK,
the sparring panel and a frozen copy of the bot, runs the evolution-strategies training, validates the result
on every map and packs it into `rl_results_<date>_<commit>.tar.gz` to send back. Linux and macOS (WSL on
Windows). A default run plays 864 games per generation and takes about 1 to 3 hours on 4 cores (less with more cores).

```bash
tools/rl/train_local.sh          # 16 generations; --gens, --jobs, --resume and --validate-only are described in the link
```

Steps, options, cost and how the results are used: [docs/LEARNING.md](docs/LEARNING.md#training-on-your-own-machine-toolsrltrain_localsh).

## Layout

```
bots/legend/        the bot (C++20 → wasm). Tunables in src/params.h
bots/starter-cpp/   official starter bot (baseline)
bots/idle/          does nothing: measures unopposed farming pace
bots/probe-rules/   scripted rule probe for maps/zz_test (capture/tribute/recall timing, stuns, sleep, dash)
bots/probe-fuel/    fuel cost of SDK helpers
maps/               generated test maps (gen*), zz_test probe map
maps/ladder/        12 real ladder maps rebuilt from replays (tools/replay/extract_map.mjs)
maps/comp/          6 official competition maps (SDK 2.1.6 map pool; the ones not already in maps/ladder)
tools/replay/       replay decoder, readable match report, map extractor, ASCII map view, map features
tools/rl/           offline RL: evolution-strategies trainer (es_train.py), search space, apply_params.py
tools/rl/train_local.sh  one-command training on your own machine (see docs/LEARNING.md, section 1)
tools/draft_tournament.py  composition round robins (forced drafts, same code) -> draft table
tools/draft_model.py       map-aware draft model from a tournament (nearest training maps) -> draft_table.h
tools/panel.sh      one summary line per sparring opponent
tools/bench.py      parallel A-vs-B benchmark with summary (comma-separated map globs)
tools/ledger.py     resumable per-game results ledger (experiments/results/ledger): play only missing games, import cut-off runs
tools/suite.sh      bench against the sparring panel
tools/tune.py       self-play parameter tuner
tools/variant.sh    build a parameter/define variant of legend
tools/make_sparring.sh  recreate the sparring panel from commits
tools/analysis/     item-value model, spell usage, decision-formula audit, bag/recall risk, route time use
experiments/patches/  unmerged prototypes as patches (economy, spells), see AGENTS.md
tools/snapshot.sh   freeze a past commit of legend as an opponent
tools/analyze_match.py  report from a match statistics JSON (local or ladder)
tools/trace_stats.py    task-time breakdown from LEGEND_TRACE builds
tools/mapgen/       symmetric map generator using the engine's MapBuilder
```

## How it plays, in one paragraph

Draft **Ren → Stellar → Cassi & Issac → Ryth → Varg** (Varg before Ryth on pack-heavy 4-champion maps),
the composition that won our 780-game tournament and the one the strongest ladder team uses. Every
champion scores every camp group by gems-and-gold per round of travel, kill time (Varg splash, area
spells, Ren retaliation), capture and heal trips, and claims it in shared memory; a second body joins
packs that are heavy for one. Recall is transport: recall while capturing (the reward lands with the
teleport), after banking far away, to shop, and bank via the altar next to spawn. In fights it counts
allies and their spells, fights back against chasers it cannot outrun, retreats early when alone, plays
defensively when outnumbered, never trades with enemies healing on their spawn, acts first through
dynamic `set_priority`, and converges on enemy tributes. A team stance bandit, a pain map and per-champion
fight calibration learn from rewards and punishments during each match; the parameters themselves are
trained offline by evolution strategies.
