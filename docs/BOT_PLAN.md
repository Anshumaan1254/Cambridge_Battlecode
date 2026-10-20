# Addendum (session 14, Oct 20): GOD v4 for patch 3.0

`submissions/god.zip` = GOD v4 = `legend_m15` (below) + the patch-3.0 changes of session 13 (camp attack ranges from the engine, Heart of
Ruin, golem, `gold_value` 0.33) + session 14's fixes from the Nyx games (`docs/strategy_v2/14_NYX_PATCH3.md`):

- **Altars behind camps** (`altar_no_camp` 2): a camp's spawn tile is an altar approach tile only while that camp is dead; a map with no
  usable altar is played for gold earned and kills (the round-2000 tiebreaks); the group that blocks an altar is a team target as soon as
  the living team can clear it (the stampede team plan), and the team banks from the dead tile (a body standing there delays the respawn).
- **Stall guard** (`stall_guard` 10): any walking task (farm, capture, tribute, home, flee) that stays in a 3x3 box for 10 rounds without
  acting drops its target; a dash kit then routes without hole crossings for 150 rounds (`dash_gain1`: at a chained hole crossing a ready
  dash that gains one step is taken instead of waiting).
- **Draft**: the objective map (Prism first, caster ring) needs a heavy lone gem group (`pd_obj_heavy`), like the brain's objective mode;
  Heart of Ruin instead of Cassi & Issac at 3 champions (`pd_hor3`, kept: see SUGGESTIONS.md).

# The whole plan of our bot (`legend_m15`, shipped in `submissions/legend.zip` on Oct 20)

`legend_m15` = `legend_m14` + "finish the camp you started" (`commit_hit` 2, session 12) + session 13's area-spell reach 5
(`aoe_reach5` 2), openers (`open_first` 2), no map-size test for the caster ring (`o2_ring_size` 0), fight instead of a shop recall
(`recall_join` 1) and a danger model trained on 160 ladder games (`ml2_*`).

A top-down map of what the bot does, in the order it does it. Every number is a value in `bots/legend/src/params.h`
(the name in brackets). Code: `draft.cpp` (draft), `world.*` (what we know about the map and the units), `nav.*` (paths),
`brain.*` (decisions), `comms.*` (shared memory), `learn.*` (in-match learning).

**Goal:** first to 1,000 banked gems. At round 2000: more banked gems, then more gold earned, then more kills, then team B.
**Strategy in one line:** draft a balanced, tanky farming team for the map, farm camps faster than the opponent, bank often,
fight only when the numbers say we win, and coordinate every body through the team's 8 shared bytes.

---

## 1. Draft phase (once per match, before round 1) — `draft.cpp`, parameter draft (`mapdraft` 6)

1. **Read the map** (no map names, only features):
   - team size (3, 4 or 5 champions);
   - camp groups on our half by type (wolf, elk, gem, gold, monolith), share of multi-camp packs, share of elk camps;
   - number of gem groups, lone monoliths, map area, mean walking distance to the groups, holes, altars.
2. **Classify the map**:
   - *objective map*: exactly one gem group, multi-camp, and no monolith (stampede-like) (`pd_obj_multi`);
   - *open small map*: 3 champions, area >= 5,000 and groups >= 30 steps away on average (`pd_open_area`, `pd_open_dist`; expanse-like);
   - otherwise *default*.
3. **First pick** (no enemy pick visible yet): Prism on an objective map, Cassi & Issac on an open small map, Ren otherwise.
4. **Every later pick**: re-plan all remaining slots, best score first, then pick the planned champion that comes first
   in the order Ren, Stellar, C&I, Varg, Ryth, Tavi, Prism, ... Score of a champion =
   - **prior strength** (measured in an 8-draft x 45-map tournament): Ren 1.0, Stellar 0.95, C&I 0.9, Varg 0.62, Ryth 0.6,
     Prism 0.36, Tavi 0.33, Vendetta 0.3, Marcella 0.2, Vesper 0.12;
   - **map fit**: objective map: Prism / Tavi +0.75, Ryth +0.4, Stellar +0.1, Ren / Varg -0.6 (casters ring the objective from
     distance 4); open small map: Ren -0.5, Varg +0.45; Varg +0.15 on pack maps, Ryth +0.1 when packs < 50% (`pd_pack`) and, at
     4 champions, elk share >= 30% (`pd_elk`); Ryth +0.03 on monolith-only maps;
   - **synergy**: C&I +0.3 if we don't have it (two bodies + heal), Stellar +0.2 if we have no caster, any frontliner -0.4 once
     we already have (team size - 2) of them;
   - **counters** to the enemy's visible picks (picks are simultaneous, so pick k sees their first k-1): Ryth +0.06 per enemy caster
     beyond the first and +0.05 per frontliner beyond the second, Varg -0.04 per caster beyond the first (small on purpose: no
     counter-pick beat ours in session 10).
5. **Typical drafts**: 5 champions Ren, Stellar, C&I, Varg, Ryth; 4 champions Ren, Stellar, C&I + Varg (pack maps) or Ryth (elk maps);
   3 champions Ren, Stellar, C&I (open: C&I, Stellar, Varg); objective map Prism, Stellar, C&I, Ryth, Tavi.
6. Draft memory gets a 4-byte note of the chosen plan (not read in the game).

## 2. Game start (each body's first turn) — `Brain::init`, `World::init_static`

1. **Item plan** (`build_style` 2, from the item-value model; five shards = one emblem; the list never runs out):
   - Ren: Jungle health > Treasure focus > Monster focus > Bruiser focus x2 > Durability health > Bruiser cycles;
   - Stellar (also Prism, Tavi): Monster focus > Treasure focus > Bruiser focus > Durability health > Bruiser cycles;
   - Cassi: Monster focus > Durability health > Bruiser cycles; Issac: Monster strength > Durability health > Jungle health > Bruiser;
   - Varg: Monster strength > Treasure strength > Jungle strength > Durability health > Bruiser cycles;
   - Ryth: Jungle health > Monster strength > Durability health > Bruiser cycles.
2. **Map memory**:
   - camp groups (connected camps): gems, gold, health, damage, respawn time, splash clusters (for Varg / area spells);
   - ours or theirs (walking distance from both spawns), altars and their danger, 1-tile hole crossings for dash kits,
     teleport-crystal hops and island camps (searched a few turns later to save fuel);
   - **objective mode** (heavy multi-camp groups holding >= 70% of the gem rate, at most 8 of them: `obj_min_hp` 4500, `obj_share`
     0.7, `obj_max_groups` 8) -> team plan; **lone-monolith mode** (monoliths hold >= 90% of the gem rate and stand near the middle:
     `mono_share`, `mono_center` 0.45) -> contest plan.
3. Learners and comms reset (the team gem-bag sum is on when the map has <= 62 groups); bodies wait to move until round 2
   (`start_round`) so all start together.

## 3. Every turn — `Brain::turn` (the order matters: the first step that acts ends the turn)

1. **Read ourselves**; if **dead**: shop (allowed while dead), read comms, clear our claim, tick the learner, done.
2. **Perceive**: update enemies (positions remembered 7 rounds after they vanish: `threat_memory`), camp health and states, respawn
   timers; read shared memory; publish our share of the team's carried gems.
3. **Learn**: champion damage taken marks a painful place (pain map), an enemy death near us relieves it; an enemy banking or
   recalling with a bag is posted as an OPPORTUNITY alert.
4. **Danger map**: every tile an enemy can hit next turn (attack range, +1 melee step, +2 with a dash ready, 4 with a spell ready,
   5 for area spells = range + radius, range + 1 for stuns that allow a walk: `aoe_reach5` 2), plus awake camps' reach.
5. **Channels**: recalling / banking / teleporting continues; a recall is cancelled when a threat closes in (any hit breaks it anyway),
   and a healthy body recalling only to shop or heal cancels it to join a fight next to it (enemy within 7, a healthy ally within 6
   with an enemy within 5: `recall_join`).
6. **Shop** (on spawn or dead): next shards of the plan; a teleport crystal when islands or hops exist; a spare altar lock.
7. **Team context** (`update_mode`):
   - being invaded -> stay together, off their half; winning fights -> take their camps and more fights;
   - 3+ more of them alive than of us (`deficit_defend`) -> defensive play, only sure fights;
   - ahead -> protect the lead (smaller bags, only clearly winning fights); they're close to winning -> steal, hunt carriers;
   - **race mode**: every 25 rounds, project both teams' finish from their banking rate over ~200 rounds (ours + carried bags);
     behind by > 73 rounds (`race_margin`): if our fights go well, contest their gems (enemy-half risk x0.5), else gold is worth less;
   - gold value (0.22 gems per gold) shrinks over the last `gold_horizon` 500 rounds (gold can't pay back late);
   - near the end only banked gems count: bank smaller bags.
8. **Support spells and altar locks**: Cassi heals the most-hurt ally in range, shields go on ourselves below 90% health near camps or
   enemies; an altar lock goes on an altar within 2 where an enemy is banking, or on an unlocked altar on their side.
9. **Respawn escort**: with 2+ of us dead, a freshly respawned body waits on spawn for the next ally instead of walking out alone.
10. **Decision cascade**:
    1. `combat()` — fight or flee (section 4);
    2. `safety()` — camp damage: go home below 25% health (`retreat_hp`) or below 4 rounds of the camps hitting us; except: finish a
       camp that dies within 4 rounds, capture a reward first (dead camps don't hit), bank a game-winning bag; rest one turn on spawn
       to heal;
    3. `tribute()` — bank: from 22 gems early (`early_tribute_min`), else 54 (`tribute_min`), + 1.74 gems per step beyond 12 steps,
       capped at 2x (`bank_trip_*`); via recall + spawn altar when that is shorter; avoid altars where enemies were just seen; a bag
       that wins goes straight to the nearest altar (`win_bank`);
    4. `home_trip()` — recall (5 turns, only when no enemy within 7 and no camp can hit us) or walk home to heal and shop: after
       banking far away, when hurt, when 4+ shards are affordable (`shop_shards`);
    5. `shop_trip()` — walk home with 150+ gold when home is <= 9 steps away;
    6. `respond_to_alert()` — RALLY (a fight to join) / OPPORTUNITY (a carrier to punish);
    7. `farm()` — pick and work a camp group (section 5).
11. **End of turn**: a ward for vision (on a bush tile on contest-type maps: a ward inside a bush reveals who hides there), turn priority
    (fighters act first), unstick, precompute the next distance fields while fuel lasts, publish our claim (the group we farm / capture /
    wait at).

## 4. Fights — `combat()` / `engage()`

1. **Their side**: enemies that can hit us within ~2 turns count fully, the rest of the visible group half; ready stuns count as damage;
   enemies healing on their own spawn are ignored (unkillable).
2. **Our side**: us + visible allies within 6 that can actually help (above the retreat line and near an enemy: `support_filter`),
   their spells, hidden allies whose claimed camp is close; awake camps hitting an enemy count for us (`camp_in_fight` 3);
   Ren's retaliation (0.2 x focus per hit) counts against whoever hits Ren.
3. **Advantage** = (our health / their damage) / (their health / our damage), scaled by each body's learned confidence.
4. **Decision**:
   - start a fight when the advantage beats 1.3 (`fight_margin`); alone (no backup within 5) an escapable fight needs 1.23 unless it is a
     kill (`isolated_fight_adv`), and an isolated body leaves enemies within 5 below 1.5 (`isolated_flee_adv`); a sure kill is always taken;
   - with half the team dead: only sure fights; when we cannot escape (melee or dash chasers we can't outrun): trade (`cornered_margin`);
   - leave early when the group here outmatches us (advantage < 0.8, `outmatch_flee_adv`; 0.45 against one stronger enemy) while
     they are still out of stun range; Cassi & Issac leave earlier (+0.3, `pair_flee_bonus`);
   - having fought last turn, keep fighting unless the estimate clearly drops (no in-and-out dancing);
   - never dive their spawn; a game-winning bag beats any fight we can walk away from;
   - **danger model** (`ml2_*`, logistic on 58 features of what the body sees: health, stats, spells ready, enemies / allies within
     3-5-7 and their health and damage, distance home, bushes, camps awake...; trained on 160 real ladder games): P(this body dies
     within 8 rounds). A fight with no kill this turn is dropped when P >= 0.4, even when the old rule thought we were cornered;
     out of reach and not fighting, the body walks away when P >= 0.4 and an enemy is within 5.
5. **Targets**: the lowest-health body we can kill this turn with our hit + ready spell + allies next to it (`px_mode` 2);
   the weaker of Cassi & Issac (both bodies die); a low body does not swing at Ren.
6. **Execution**: hit what is in reach before walking; melee swings before stepping away; area spells from distance 5 (`aoe_cast5`);
   openers (`open_first` 2): a ranged body with its opener ready waits at the edge of the enemy's reach (at most 2 rounds) so they step
   in and we cast first, and a walk-compatible spell (Cassi's stun) is cast right after a fight step; stun the nearest chaser when
   fleeing; casters cast on camps on the way (`cast_en_route`).

## 5. Farming — `farm()` and `group_score()`

1. **Score of a camp group** = value / time (a long-run gem rate):
   - value = gems + 0.22 x gold (x0.6 when joining someone else's group: `join_share`); enemy-half groups x(1 + deny bonus);
   - time = walk to attack range (with dash pace) + wait for the respawn (at most 18 rounds: `max_wait`) + kill time + 6 capture
     rounds + heal trips;
   - kill time from our real damage (splash, spells, Monster's +10%, allies on the group); damage taken from a camp-by-camp model
     (camps die one by one; a melee ally in front takes the hits); trips home when the health budget runs out;
   - enemy-half groups: +10 rounds of risk x the share of enemies alive (`enemy_half_penalty`), skipped below 55% health;
   - painful places (pain map) and groups where a stronger enemy group was just seen cost extra; enemy-half groups unseen for 60+ rounds
     are discounted.
2. **Coordination through claims** (shared memory): one collector per reward (the first to arrive, then the lower index); a second or
   third body joins only heavy groups (at most 3 extra: `max_join`) and only if it arrives before the claimers finish (`join_reach`);
   a yielding body still counts as helper damage.
3. **Stability**: keep the current target unless a new one scores 15% better (`hysteresis`), and while we hit a live camp in the
   last 2 rounds its score counts double (`commit_hit` 2: 198 abandoned camps in 17 traced games); give up on a target with no
   progress for 2 x eta + 60 rounds (blacklisted 40 rounds).
4. **Capture**: stand on the reward tiles (6 rounds); recall-while-capturing (start the recall so it lands with the reward) when home is
   far; bank first at a nearby altar when that is shorter.
5. **Special plans**:
   - *objective map*: the whole team takes the objective group claimed by the lowest-index body, heals before the walk, gathers outside
     camp reach; with Prism / Tavi and 5 champions the casters ring it from distance 4 and never step into camp reach (`o2_ring` 3; no
     map-size test any more: `o2_ring_size` 0);
   - *contest (lone monolith) map*: bodies move as one blob behind the lowest claimant until round 200 (`mono_follow_until`), ward bushes;
   - islands via teleport crystals, hole crossings with a dash, crystal hops over mazes.
6. **Nothing worth farming**: top up at home if hurt or rich, else wait next to the soonest respawn on our half, else go back up an ally.

## 6. Team communication (8 shared bytes)

- Bytes 0-5: one claim per body (group id), bit 6 = team carried-gems sum (in tens), bit 7 of bytes 0-1 = team stance;
  bytes 6-7: one team alert (tile + DANGER / RALLY / OPPORTUNITY). Every body applies the same rules to the same bytes, so the
  team agrees with no leader. Details and measured gains: AGENTS.md §S12.

## 7. Learning inside a match — `learn.*`

1. **Stance bandit**: every 40 rounds the team scores its stance (banked gems + 40 per kill - 45 per death) and keeps the best of
   SPREAD / GROUPED / PUSH; body 0 decides, the others read it.
2. **Pain map**: where we took damage or died costs extra in camp scoring, decaying over time; kills heal it.
3. **Fight calibration**: each body trusts its fight estimate less after dying in a fight it chose, more after kills (rate 0.33).

## 8. How the bot is improved (outside the match)

1. Every idea becomes a switch in `params.h` (off by default) on a copy of the shipped bot.
2. A/B through the ledger (`tools/ledger.py`, deterministic games, never replayed): the 17 official maps x 2 sides against five sparring
   proxies (Mite, ifish, `_px9`, sneaky-bush, `_fA`) + head-to-head against the shipped bot, then the wider pools (27 generated,
   padded / resized official, fresh generated, held-out gem-scarce maps) and unopposed pace.
3. Ship only if it is >= the shipped bot head-to-head and not worse against the proxies (the user's rule); results kept in
   `submissions/BUILDS.md`, rejected ideas in `SUGGESTIONS.md`, hardcoded risks in `ISSUES.md`.
4. Inputs: the user's ladder replays (decoded by `tools/strategy_v2/`), offline parameter search (ES / A100 runs), traced games.
