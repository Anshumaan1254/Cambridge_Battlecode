# 04. Clustering, machine learning and RL: where they help us

You asked to look at this through k-means, DBSCAN, SVM and other ML, deep learning and RL ideas. Here is the honest
answer, technique by technique, with what we can build and test now.

**The main point first.** Our losses come from fight execution, where our gold goes, and farming routes (see 01).
None of those is fixed by adding a learned model on top of the current rules. ML is useful in a few narrow places:
planning the map (clustering), learning thresholds from the top teams' replays (imitation), and checking or
replacing the fight estimate (a small model or, better, a short look-ahead). Full reinforcement learning is not
possible inside this game's limits.

Two hard limits shape everything:

- **Fuel.** 100,000 instructions a turn in C++ (1,000,000 in the first draft turn). A model must be a few hundred
  multiply-adds, or a small tree, to be safe.
- **Data.** A 15-game match group gives about 150 fights. Local games give thousands, but they are against our own
  code family, which plays differently from the top teams (01, 05). Small, simple models fit small data.

---

## 1. k-means / k-medoids: farming zones (use it, in the draft)

**What it is, plainly:** split points into k groups so each point is close to its group's centre.

**Our use:** split the camp groups on our half (and the neutral ones) into one zone per farming unit, so each
champion has its own loop of camps near each other. Plain k-means puts each centre at an average position, which can
be inside a wall, and it measures straight-line distance, which ignores walls. **k-medoids** uses real camp groups as
centres and any distance we give it, so we feed it walking distance from BFS. Each group is weighted by how much it
pays per round (value / (respawn + 5 + health / 150)), so valuable groups pull the centres.

Then a second step assigns champions to zones: with at most 5 zones there are at most 120 ways, so we try them all and
keep the one with the most value x fit (Varg gets the packs, ranged champions the harmless clusters and elks from
range 4, tanks the elks).

**Built today:** `tools/strategy_v2/map_plan.py` (weighted k-medoids with PAM swaps, brute-force assignment,
nearest-neighbour circuits, map type). Example output (team size 5, eight):

```
Varg       cycle ~78 rounds, ~1.68 gems/round: 3elk+1gem+1gold@13,25
Stellar    cycle ~78 rounds, ~0.92 gems/round: 2elk@13,3
CassiIssac cycle ~55 rounds, ~0.79 gems/round: 2wolf@18,10
Ren        cycle ~35 rounds, ~0.49 gems/round: 1wolf@9,15
```

Port to C++ in `draft.cpp` (03 section 3); fuel ~400-700k on the biggest maps, inside the first draft turn.

**What to check:** unopposed pace (05 test 1) must drop, and the share of walking (01 section 2) must fall, mostly on
ambush, expanse, lanes and pilgrimage.

## 2. DBSCAN: hubs, lone contested groups, and cutting replays into fights (use it)

**What it is, plainly:** groups points that have enough neighbours within a distance `eps`; points with too few
neighbours are "noise". No need to choose k.

**Our uses:**

1. **Hubs on big maps.** On ambush, expanse and lanes the camps sit in dense patches far from spawn. DBSCAN on walking
   distance (eps ~ 10 tiles, minimum 2 groups) finds those patches; each hub gets its nearest altar, and the field
   playbook (Part D) farms a hub and banks at its altar instead of walking home.
2. **Lone groups away from the others** come out as noise: these are the contest points, for example the 4-elk +
   4-gold group and two gold groups in the middle of pilgrimage, or the 6-elk objective on stampede (the full list per
   map is in `data/map_plans_17.txt`). They are where we send 2-3 bodies together, not one. On the small maps
   (fragment, packs, elkring) every group sits in one hub, so there the whole map is the contest.
3. **Fights in replays.** `analyze.py` joins champion hits within 3 rounds and 8 tiles into one fight (that is DBSCAN
   with a minimum of one point, also called single-linkage clustering). This is how the 152 fights in 01 were found.

## 3. SVM: not recommended

An SVM is a classifier ("will we win this fight?"). A kernel SVM needs to keep many training points (support
vectors) and compare against each one at decision time: too costly in fuel and hard to export. A linear SVM is just a
weighted sum, the same shape as a logistic regression, and logistic regression also gives a probability, which is what
we need to set a fight threshold. So: use logistic regression or a small tree instead (next section).

## 4. Logistic regression and small trees: checking the fight estimate (use it, carefully)

**Built today:** `tools/strategy_v2/fight_model.py` takes each of the 152 fights, reads the state one round before the
first hit (health, strength and focus of every body within 8 tiles, from the items they own), and asks how well
simple numbers predict "we lost more bodies than they did". Folds are grouped by match, so no match is in both
training and test data.

| Predictor | AUC (0.5 = coin flip, 1.0 = perfect) |
|---|---|
| Lanchester estimate log((HP x DPS)_us / (HP x DPS)_them), the same idea as `combat()` | 0.67 |
| Body difference | 0.60 |
| We hit first | 0.62 |
| We took camp damage in the 3 rounds before | 0.51 |
| Logistic regression on all four | 0.67-0.69 (cross-validated; the range comes from how the 15 matches fall into folds) |
| Decision tree, depth 3 | 0.63 |

And the most useful table, the estimate against what happened:

| Lanchester log-advantage at the start | Fights | We lost more bodies |
|---|---|---|
| below -0.5 (they are much stronger) | 58 | 62% |
| -0.5 to 0 | 31 | 52% |
| **0 to +0.5 (we are up to 1.65x stronger on paper)** | 18 | **56%** |
| above +0.5 | 45 | 18% |

So in fights our formula calls even or slightly in our favour, we still lose more than half. The current
`fight_margin` (1.30, log 0.26) sits inside the band that loses. Two lessons:

1. Stats and health explain only part of a fight (AUC 0.67). Execution (hitting first, spacing, camps, not walking
   under fire) is the rest. That is why Part A comes before any model.
2. Raising the bar for *starting* fights to about 1.65x (log 0.5) looks right on paper. **Tested today, it is not
   clear-cut:** `fight_margin = 1.65` alone scored 48.8% against the current bot; on top of the fight patch it beat the
   current bot 58.5% (the patch alone: 54.9%) but lost 40.2% to the patch alone. Leave `fight_margin` at 1.30 and let
   the look-ahead (section 6) or a trained gate replace the single margin.

**Later**, with more data (every ladder match group adds ~50 fights; local games against the top-style bot add
thousands), fit a logistic regression on in-game features: our and their health and damage, ready stuns on each side,
splash exposure (our bodies adjacent to each other with an enemy Varg or area caster near), awake camps that hit each
side, distance to each spawn, carried gems. Export the weights as constants in C++: one dot product per fight check.
Use it as a gate next to the formula, then A/B it.

Rules for the data (from the repo's ML notes and the audit): split by match and by map family, never by fight; use only
what a champion can see at that moment (no replay-only knowledge); keep correlated fights of one match together.

## 5. Imitation of the top teams (the most useful ML here)

In a replay we see everything both teams did. So we can learn the top teams' decision rules directly, and copy the
ones that are simple:

| Decision | Data from their replays | Model |
|---|---|---|
| When to recall | health fraction, gold, bag, distance home, enemies near, at each of their turns, label = recalled | logistic regression, then read off the thresholds |
| When to bank | bag size, distance to nearest altar, enemies near, label = went to bank | same |
| Which camp group next | their position, every group's state and distance, label = the group they captured next | learning to rank (a scored list; a linear score is enough) |
| When to engage | the fight features above, label = they started a fight | logistic regression |
| What to buy | already clear without a model: one health emblem, then Power in the damage stat |

What we already read off without a model: they recall at a median 58% health (us 45%), bank bags of 58 on average
(us 50), and let respawned home groups wait 14 rounds before hitting them (us 21).

The script to build these datasets is a small extension of `analyze.py` (each body-round of the top team becomes a row).
Start with recall and engage: they are the cheapest to copy.

## 6. Search instead of learning: a short look-ahead for fights (recommended)

The engine is deterministic and its rules are known exactly (ENGINE_FACTS, GameRules). Local fights are small (2-10
units). So instead of learning a fight score, we can **simulate** the next 2-3 turns for each choice this champion has
(attack target t, cast spell s on t, step to tile p then act, retreat) against a simple enemy policy ("hit the
lowest-health champion in reach, cast every ready spell"), and pick the choice with the best result
(enemy health lost + 1,500 per enemy body killed - the same for us). This is what game AIs call a shallow search or
Monte Carlo rollout.

Why it fits: it handles splash, area spells, stuns, camp aggro and turn order without hand-set margins; it needs no
training data; and it costs roughly 30 options x 3 turns x 10 units, about 1,000 cheap steps (well under 10k fuel).
Build it after Part A (03 section 1, "fight_sim"), and first check it offline: replay each of the 152 fights from its
start state in Python and see whether the search's choice matches the side that won.

## 7. Deep learning: not now

A small neural network (for example 20 inputs, 16 hidden, 1 output: ~350 multiply-adds) would fit in fuel. But with a
few hundred real fights it will not beat a logistic regression or a tree, and it is harder to check. Revisit only if
the simple models plateau with thousands of ladder fights.

## 8. Reinforcement learning

| Kind | Verdict |
|---|---|
| Full RL policy (learn every move) | not possible: a local game takes 1-2 seconds, a useful policy would need millions of games, and the result must run in 100k fuel a turn |
| In-match learning (bandits) | already built and measured neutral (`learn_stance`); a game has only ~25 decision windows; keep off |
| **Evolution strategies over parameters** | yes, already in `tools/rl/` (local and A100 scripts). Use it **after** Parts A-C, on the new parameters (`fight_commit_margin`, `burst_exit_k`, `zone_own_bonus`, collector order, build switches), and against a **league**: the top-style bot (05), the current `legend`, `legend_st`, `legend_es2`. Fitness = win rate first, then the KPIs (deaths, damage per gold). Save the best *evaluated* vector, not the last one (the repo fixed that bug once). |
| Contextual bandit per map type, offline | possible later: tune one parameter set per map type (rich home, contest, objective, field) with ES, select by the draft's map type |

## 9. Opponent modelling

**Offline:** cluster the opponents' behaviour across match groups (k-means on features like first-contact round, share
of captures on our half, health at recall, emblem types) to name a few styles and build one sparring variant per
style. With 3 teams so far, the styles are already visible by hand: all three farm with damage stacking; X fights the
most (80 of the 152 fights, spread over the whole map); half of Y's 40 fights are on our half (it invades), and Y
plays a caster draft on stampede; Z fights least (32) and mostly in the middle (44% on neutral ground).

**Online:** the bot cannot know who it plays, but it can see how they play by round ~100: early invasions of our half,
their bodies' visible damage stats. Two switches are enough: "they invade" -> group 2 bodies per zone near the border;
"they out-scale us" (A8 power index) -> no even fights, farm and defend.

---

## What to build, in order

1. `map_plan.py` -> C++ draft planner (k-medoids zones, DBSCAN hubs) - with Part C.
2. The fight-start bar: tested, inconclusive (above); revisit with the look-ahead.
3. The fight look-ahead - after Part A.
4. Imitation datasets for recall and engage from the top teams' replays - any time, offline.
5. ES tuning against the league - last, on the final structure.
