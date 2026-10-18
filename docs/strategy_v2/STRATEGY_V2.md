# Strategy v2: how we stop losing to the top teams

Written 18 Oct 2026 from: the 15 matches against the top 3 teams (3 match groups, 5 games each, we are side A
in all of them), the game rules, the `legend` source (`submissions/legend.zip` = `bots/legend/src`), and tests
run today on the local engine (cambc 2.2.5). Every number below comes from those files. The scripts that made
them are in `tools/strategy_v2/` so you can re-run them on new match groups.

Read this file first. The supporting files are:

| File | What it holds |
|---|---|
| [01_REPLAY_FINDINGS.md](01_REPLAY_FINDINGS.md) | everything measured in the 15 games, with tables per match, per champion, per fight |
| [02_RULES_GAPS.md](02_RULES_GAPS.md) | game rules we do not use, or use badly, and what each one is worth |
| [03_IMPLEMENTATION_SPEC.md](03_IMPLEMENTATION_SPEC.md) | exactly what to change in the code: functions, new params, memory layouts, fuel budgets |
| [04_ML_AND_CLUSTERING.md](04_ML_AND_CLUSTERING.md) | k-means, DBSCAN, SVM, trees, deep learning, RL: where each one helps us and where it does not |
| [05_TEST_AND_SHIP_PLAN.md](05_TEST_AND_SHIP_PLAN.md) | how to test each change so it holds up on the ladder, target numbers, ship rules |
| [06_EXPERIMENTS_18OCT.md](06_EXPERIMENTS_18OCT.md) | the tests run today (pace runs, head-to-heads, the fight patch), with all results |

---

## 1. The short version

**Record against the top 3:** 2 wins, 13 losses. Banked gems 7,596 to 15,312.

We lose for three reasons. In order of size:

1. **We lose fights, badly, even when we bring more champions.** Over 152 fights we dealt 91k damage and took
   192k. Our bodies died 166 times, theirs 72. In the 73 fights where we had *more* champions in the fight,
   we still lost 71 bodies to their 37. The early fights (rounds 0-100, before anyone has items) already go
   0.64 : 1 in damage against us, so this is not only about items. The clearest single fault: **in 74% of the
   rounds an enemy champion hits one of ours, our champion hits no champion back** (theirs: 55%). Most of
   those rounds our champion is walking, and in 278 of them an enemy was already in its attack range.
2. **Our gold buys too little damage.** They spent 68.4k gold and got 2,181 points of damage stat; we spent
   37.5k and got 775. Per 1,000 gold they get 32 damage points, we get 21, because 40% of our emblems are
   health (Durability, Jungle or Bruiser in health: 90 of 224; theirs 74 of 417) and our damage emblems are Bruiser,
   Monster or Treasure (5 damage points each) where theirs are Power (6). They earn 1.9x our gold, so they end with **2.8x our damage**.
   Every top team does the same thing: one health emblem per champion, then Power emblems in the damage stat
   for the rest of the game (295 of their emblems were Power in the damage stat).
3. **Our champions spend less time hitting camps, and hit them slower.** Camp gems = time alive x share of
   that time on camps x damage per round on camps x gems per damage. Ours against theirs:
   0.88 x 0.87 x 0.71 x 1.05 = **0.57**. We collected 57% of their camp gems, and the biggest single
   factor is damage per round (-29%). We kill a lone wolf in 18 rounds, they take 11; a two-elk group takes us
   184 rounds (several heal trips), them 25.

These three feed each other: lost fights cost time and gold, less gold means less damage, less damage means
slower farming and more lost fights. The top teams run the same loop the other way round.

**What we tested today** (details in [06_EXPERIMENTS_18OCT.md](06_EXPERIMENTS_18OCT.md)):

- A small fight patch (`experiments/wip/x_exec.patch`: hit what is in reach before walking, melee swings
  before stepping away, keep fighting instead of flip-flopping) beat the current bot 45-37 over 82 distinct
  games and cut deaths from 810 to 611. Against the older `legend_es2` it won 73% where the current bot wins 56%.
- Copying the top teams' builds alone (`build_style 3`) into the current bot: 47% over 34 distinct games (no
  gain). Copying their Varg-first draft alone: 35% (worse). Builds + fight patch against the fight patch alone: 44%.
- No single setting made unopposed farming faster (6 variants tried; the current bot needs 579 rounds on
  average to reach 1,000 gems alone on the 17 official maps).

So: the fight fix is real and should ship first. The items and the draft are **not** the main cause and do not
help on their own inside our current brain. They only make sense together with faster kills and better fights,
and they must be tested against an opponent that plays like the top teams, not only against our own bots.

**The plan in one line:** fix fight execution first, then make one map plan at draft time (zones and farming
circuits for each champion, found with clustering) and farm it tightly, then put all gold into damage and route
it to the champions that turn it into the most farming, and change how we test so the ladder agrees with the lab.

---

## 2. What the top teams do that we do not

| Area | Top teams (15 games) | Us |
|---|---|---|
| Fight execution | hit back in 45% of the rounds they are hit; hit first in 86 of 152 fights | hit back in 26%; when they hit first we lost 97 bodies to their 17 |
| Fight results | 72 body deaths, 115 kills | 166 body deaths, 42 kills |
| Items | 1 health emblem per champion, then Power in the damage stat (295 such emblems) | Bruiser, Monster, Jungle-health, Durability-health, Treasure spread |
| Damage points per 1,000 gold | 31.9 | 20.7 |
| Gold earned | 76.8k | 39.9k |
| Time dead | 9.0% of body-rounds | 19.5% |
| Time hitting camps (share of time alive) | 21.2% | 18.4% |
| Camp damage per round on camps | 118.5 | 84 |
| Captures | 355 (264 on their own half) | 202 (162 on our own half) |
| Camp groups after they respawn | touched again after 14 rounds (median) | 21 rounds |
| Recall | 476 recalls, at 58% health (median) | 383 recalls, at 45% health |
| Banking | 263 banks, 58 gems on average | 153 banks, 50 gems |
| Draft | Cassi & Issac 15/15, Stellar 15/15, Varg 12/15 (first pick 7 times), Ryth 9/15, Ren 8/15, Tavi 4/15 | Ren, Stellar, Cassi & Issac, Varg, Ryth in that order |

Per champion (games where both teams had it; full table in 01):

| Champion | Captures us / them | Gold earned | Deaths | Damage stat at round 300 | First emblem (round) |
|---|---|---|---|---|---|
| Varg | 2.1 / 5.4 | 472 / 1,339 | 1.5 / 0.2 | strength 84 / 152 | 232 / 88 |
| Issac | 2.5 / 5.5 | 420 / 1,019 | 2.7 / 1.3 | strength 45 / 91 | 311 / 165 |
| Cassi | 2.1 / 3.3 | 306 / 697 | 2.7 / 1.3 | focus 79 / 169 | 189 / 215 |
| Stellar | 2.3 / 4.6 | 577 / 1,008 | 1.8 / 0.7 | focus 143 / 206 | 404 / 161 |
| Ren | 4.2 / 5.3 | 762 / 1,094 | 1.6 / 0.9 | focus 163 / 191 | 125 / 118 |
| Ryth | 1.3 / 4.3 | 216 / 846 | 1.4 / 0.4 | strength 57 / 93 | 449 / 127 |

Things that are **not** the problem (checked, so do not spend time there): fuel (median 12-35k of 100k a turn,
at most 6 lost turns a game, all in rounds 1-3); focus fire (both teams put ~90% of a 3-round window's damage
on one target); gems per camp damage (ours is even slightly better); unspent gold; wards (we place 4x more).
On ambush, eight and corners (5 picks) our draft was exactly team Y's, and Y still beat us 1024-428, 1130-22 and
1004-320 with it.

---

## 3. Why the last six sessions did not move our rank

The repo holds a lot of careful work: dozens of switches, each tested over 100+ games. Most of it was judged
against **bots made from our own code** (old versions, or our code with other settings). That has two problems:

1. **It measures the wrong thing.** Our own bots share our blind spots. A change that helps against a bot that
   also dithers in fights tells us little about a team that does not. The repo's own record shows it:
   `legend_st` beat its sparring panel 70-97% and went 1-16 on the ladder.
2. **The ladder copies of the maps double count.** `maps/ladder/` holds exact copies of most official maps
   (today the same games came out with identical results), so a "58-game" test on comp + ladder maps is really
   about 34 distinct games. One 34-game result moves about 8 points by chance.

On top of that, the parameter space is used up: today 6 single-setting changes all made unopposed farming
slower or no faster. More tuning of the same brain will not close a 2x gap. The gap is structural: how fights
are played, where each champion farms, and where the gold goes.

---

## 4. The plan

Five parts. A (fights) comes first: it is the biggest gap and the only one with a measured fix today. C and D
change how farming works. B (items, gold routing, draft) is a package that pays only once A and C are in. E
changes how we test; without it we will keep shipping changes that look good in the lab and lose on the ladder.

### Part A. Fight doctrine (start here)

These are rules for every champion in every fight. Each one is aimed at a measured fault.

| # | Rule | Why (measured) |
|---|---|---|
| A1 | **Never waste a turn under fire.** If an enemy is in attack range, attack it. Melee: attack first, then step (melee may attack and move in one turn). Ranged: attack or cast and stand. Only walk when nothing can be hit. | 633 rounds hit while walking without hitting back (theirs 177); in 278 an enemy was already in our attack range |
| A2 | **Commit or leave, never both.** Once fighting, keep fighting until the target dies, our health falls below 30%, or the fight estimate falls below 0.7. Once leaving, keep leaving until no enemy is within 6. | the bot re-decides every turn from scratch and flips between fight and flee under fire |
| A3 | **Count only real helpers.** An ally counts in the fight estimate only if it can hit an enemy within 2 turns, is above the retreat line and is not recalling or banking. | in the 73 fights where we had more bodies we still lost 71 to 37 |
| A4 | **Spread against splash.** With an enemy Varg within 3, or an enemy Stellar, Prism or Ryth (radius-1 area spells) within 5, never end a move next to an ally. Cassi never stands next to Issac. | 14% of our deaths came with Varg splash hitting the victim and an ally in the same swing (theirs 6%); on collision Stellar's area spell hit our Cassi and Issac side by side (r41), then our Ren and Issac side by side (r50), killing Issac and, through the link, Cassi |
| A5 | **Do not fight inside an awake camp's range.** Camps hit the nearest champion. Count camp damage in the fight estimate, step out to 4 tiles before trading, and fight enemies who stand in their camp's range. | swirl r14-20: our Ren tanked an elk the enemy had woken, while fighting 3 enemies, and died |
| A6 | **Strike first, with the burst ready.** Start a fight only when the opener is ready (a stun plus a damage spell, or a Varg/Issac reset) and the others can hit in the same 1-2 turns. The stunner gets the highest priority so it acts first. | they hit first in 86 of 152 fights; when they did, our deaths were 97 to their 17 |
| A7 | **Leave before the finisher.** If the burst of every enemy that can reach us next turn is more than our health, step out of their reach now (or stun the nearest chaser). Burst = basic attack + the best ready cast (one cast per turn): a reset (one more basic attack) or a spell: Stellar 2.0 x focus, Tavi 2.2x, Cassi 2.0x, Prism 1.5x, Ren 1.25x, area 1.4x. | 40% of our death incidents had the victim above 60% health four rounds before: it was burst down, not worn down |
| A8 | **Fight where we are strong.** Defend our own zones; do not chase into their half; do not take even fights when their summed damage stat is higher than ours (visible enemies' strength and focus are readable). | our deaths: 80 on our half, 57 neutral, 29 on theirs |
| A9 | **Cassi & Issac move as one.** Cassi stays 2-3 tiles behind Issac (never adjacent), both leave when either is below 40% health or 2+ enemies are within 4, Issac does not dash into a fight Cassi cannot reach. | 40 pair deaths for us (80 bodies), 19 for them |

A1 and the fight half of A2 are in today's patch (`x_exec`): 54.9% against the current bot with a quarter fewer
deaths, 73% against `legend_es2` (the current bot: 56%), level against `legend_st` (53.7%; the current bot: 54.9%).
A3 already exists in part (`support_filter`). The flee half of A2 and A4-A9 are new. In the longer run, replace the single
fight formula with a short look-ahead (simulate the next 2-3 turns of the local fight for each choice: attack
target X, stun Y, step out); see 04 section 6. The engine is deterministic and the fights are small, so this is
cheap and much more exact than hand-set margins.

### Part B. The power loop (items, gold routing, draft)

**B1. Builds.** One survival emblem, then damage for the rest of the game. This is what all three top teams do:

| Champion | Build order (5 shards = 1 emblem) |
|---|---|
| Varg | Monster (strength), Durability (health), then Power (strength) forever |
| Issac | Power (strength), Durability (health), then Power (strength) |
| Cassi | Bruiser (health), then Power (focus) |
| Stellar | Power (focus), Durability (health), then Power (focus) |
| Ryth | Durability (health), Bruiser (health), then Power (strength) |
| Ren | Durability (health), Bruiser (health), then Power (focus) |
| Tavi | Treasure (focus), Durability (focus), then Power (focus); buys in the field |

Why Power and not Bruiser: Bruiser gives 7 stat points for 150 gold but only 5 in the stat that matters; Power
gives 6 in it (+20% damage per gold). Passives (Monster, Jungle, Durability) do not stack, so a second one is a
waste. Monster (+10% camp damage) beats one more Power emblem for farming once the stat is above 5 times its
per-shard growth (Varg: strength above 25), which every damage champion passes early, so farmers take Monster once.

**Today's warning:** this build alone tested at 47% inside the current brain (34 distinct games), and 44% on top
of the fight patch. Our current fights are long brawls where health matters more than damage; the top teams'
fights are short because they hit first and focus. So ship B1 only with Part A in place, and only after it beats the top-style
sparring bot (Part E). Keep it behind `build_style`.

**B2. Gold goes to the champion that turns it into the most farming.** The capturer gets all of a group's gold
(it is split only between allies standing on the group). Today the lowest draft index captures shared groups, so
Ren (index 0) collects the most gold even alone on the map (1,660 a game, Varg 846). Order the collector choice by
farming damage gained per gold: Varg (splash) > Issac > Stellar > Ryth > Cassi > Ren. The others step off the
reward tiles after the kill, so the reward is not split.

**B3. Draft.** Small lever, do not start here. At team size 5 our five champions are the five that X uses, and that
Y uses on three of its four 5-pick maps (Z swaps Tavi in). At size 3, two of the three top teams use Varg where we use
Ren; at size 4, both teams that played it (X and Z) use Ryth where we use Ren. When B1 and B2 are in, test:

| Team size | Draft |
|---|---|
| 3 | Varg, Stellar, Cassi & Issac |
| 4 | Varg, Stellar, Cassi & Issac, Ryth |
| 5 | Varg, Stellar, Cassi & Issac, Ryth, Ren (Tavi instead of Ren on objective maps) |

Measured today: with the current brain, this draft won only 35% of 34 distinct games against the current draft,
because our current Varg gets little gold and dies a lot (it needs B1 + B2 + Part A). The draft code already supports forced drafts
(`LEGEND_DRAFT`) for the test.

**B4. Shopping rhythm.** Recall to shop at a natural break (right after a capture, with the reward landing as the
recall lands, which the bot already does) as soon as 150 gold (one emblem) is on hand. Never walk home just to shop.

### Part C. One map plan, made at draft time

The draft turn has 1,000,000 fuel and sees the whole map. Today the draft writes 4 bytes into the 1,024-byte
draft memory, and every champion redoes the map analysis in its own first turn (that is what caused the old
opening fuel problems). Instead, plan once in the draft and store the plan:

1. Walking distances from both spawns; every camp group with its gems, gold, respawn, health and attack strength;
   each group labelled home, neutral or enemy (by walking distance, 3-tile band).
2. **Zones:** cluster the home and neutral groups into one zone per farming unit (Cassi & Issac count as one unit)
   with k-medoids on walking distance. This is k-means with real groups as centres, so walls are respected.
3. **Assignment:** try every unit-to-zone assignment (at most 5! = 120) and keep the one with the most
   value x fit (fit = how fast this champion clears this group and survives it: Varg on packs, ranged champions on
   harmless clusters and from range 4, tanks on elks).
4. **Circuits:** order each zone's groups as a loop from spawn (nearest next).
5. **Map type** (Part D) and the objective groups.
6. Write it to draft memory (about 20-70 bytes on the 17 official maps; layout in 03).

In the game, each champion farms its own circuit: the next group is the one that is alive, or respawns by the
time we arrive, with the best value per round, from its own zone first (neighbour zones only when its own is empty
or when an ally there is dead). Claims in shared memory stay for overflow and help. The prototype planner
(`tools/strategy_v2/map_plan.py`) already prints zones, circuits and types for all 17 official maps.

Why this beats the current per-champion greedy choice: the greedy choice has no memory and no ownership, so
champions switch targets, chip camps they never finish and drift across the map. Our Stellar on expanse
(trace in 01) spent rounds 55-136 walking 40 tiles out, chipping an elk it never killed, taking two gold clusters
and fighting a 2-wolf pack alone without finishing it: 70 gold and no gems in 80 rounds. The top teams'
champions run tight loops: their Issac on expanse made 14 captures, 9 of them from three wolf camps next to its
spawn and the rest from the two groups beside them.

### Part D. Playbooks by map type

The planner sorts every map into types from its numbers (home gem rate = gems per round the home groups can give
if each is taken right when it respawns):

| Type | Test | Official maps | How to play |
|---|---|---|---|
| Rich home | home groups alone reach 1,000 gems in under ~450 rounds | corners, expanse, lanes, ambush, rushbait-v2, collision, monolith, eight, rows | farm the home circuits fast; defend them (A8); take neutral groups only with a power lead |
| Contest | home groups are too few (fragment: 1.3 gems a round, 770 rounds to 1,000) | elkring, fragment, packs, interlock, pilgrimage, swirl (contest and stampede too, see Objective) | the neutral groups decide the game: fight-ready team, 2-3 bodies together at contested groups, wards on the bushes there, contest their captures (an enemy on any tile resets the capture) |
| Objective | one heavy group holds 40%+ of the map's gems | contest, stampede (also partly monolith, rows, eight, collision) | gold and power first, then take the objective with the whole team; keep the stampede plan (it won 1080-0 before), add a single-monolith plan for contest |
| Field | home groups 30+ steps from spawn | ambush, expanse, lanes | do not walk home: farm in the middle, bank at the middle altars, recall only to shop or heal; consider the Home emblem (recall in 3 turns instead of 5) for farmers |

The field type matters most for our pace: alone on ambush our champions walk 67-80% of the time and need 708
rounds to reach 1,000 (Ryth made no gem capture in 749 rounds).

### Part E. Test against the right things

1. **Unopposed pace** (each build alone against `idle` on the 17 official maps, both sides): must never get worse.
   It needs no opponent model, so it cannot fool us. Today: 579 rounds on average.
2. **Replay KPIs** from real ladder games, with `tools/strategy_v2/analyze.py`. Targets (now -> goal against the
   top teams): body deaths per game 11.1 -> 6; share of hit rounds without hitting back 0.74 -> 0.55; damage
   points per 1,000 gold 20.7 -> 30; camp damage per camp round 84 -> 110; time alive 80.5% -> 88%; captures per
   game 13.5 -> 20.
3. **A top-style sparring bot**, written apart from `legend` (spec in 05): Varg-first draft, damage builds, simple
   farming loops, attack anything in reach, focus the weakest, hit first. Our own family cannot stand in for the
   top teams.
4. **Distinct games only:** official maps plus the generated maps, both sides; never count `maps/ladder/` copies.
5. **Ladder truth:** after each ship, queue match groups against the top 3 (`cambc match-groups`), decode them, and
   compare the KPIs with the tables in 01.

---

## 5. Clustering, ML and RL: what to use

Short answer: the losses do not come from missing ML. They come from fight execution, item choices and farming
routes. ML helps in a few narrow places. Details and code in [04_ML_AND_CLUSTERING.md](04_ML_AND_CLUSTERING.md).

| Technique | Use it for | Verdict |
|---|---|---|
| k-means | farming zones | use **k-medoids** on walking distance instead (k-means centres fall inside walls); done in the draft, prototype written |
| DBSCAN | finding camp "hubs" on big maps and lone contested groups; cutting replays into fights | yes, offline and in the draft; it was used today to find the 152 fights |
| SVM | "will we win this fight?" | no: a kernel SVM is too costly in fuel; a logistic regression or a small tree does the same job cheaper and gives a probability |
| Decision trees / gradient boosting | fight and retreat gates learned from replays | yes, later, after Part A; export as plain if/else |
| Imitation of the top teams | learn their recall, bank and engage thresholds and their next-camp choices from their replays | yes, the most useful ML here: we see their full play in every replay |
| Deep learning | a fight-value network | not now: too little data, no gain expected over a tree, fuel cost |
| Reinforcement learning (full policy) | learning to play | no: 100k fuel a turn and ~1-2 s per local game make it impossible |
| Evolution strategies (already in `tools/rl/`) | tuning the new parameters | yes, but only after A-C are in, and against a league that includes the top-style bot, not only our own family |
| Short look-ahead search | fight choices (Part A) | yes: deterministic rules, small fights, cheap; the best "AI" upgrade available |
| In-match bandits | stance learning | already tested neutral; keep off |

---

## 6. Roadmap

About a month remains (the competition runs to 18 Nov). Each phase ends with a ship decision.

| Phase | Work | Days | Ship when |
|---|---|---|---|
| 0 | Tools: `tools/strategy_v2/` (done today), the top-style sparring bot, the distinct-map test suite | 1-2 | (no ship) |
| 1 | Part A1-A2 (`x_exec`, measured today) + A3 cleanup | 1 | beats current `legend` on distinct games and pace not worse: **ready now** as `submissions/candidates/legend_exec_20261018.zip` |
| 2 | Part A4-A9 (spacing, camps, strike first, leave before the finisher, pair rules) | 3-4 | beats phase 1 and the top-style bot; deaths per game down |
| 3 | Part C (draft-time plan, zones, circuits, draft memory) + Part D field and contest playbooks | 5-7 | unopposed pace down (goal: under 500 on average, ambush under 550), and beats phase 2 |
| 4 | Part B (builds, collector routing, draft) as one package | 2-3 | beats phase 3 against the top-style bot and on the ladder KPIs |
| 5 | Look-ahead fight search; replay-trained gates; ES tuning against the league | rest | each piece on its own A/B |

After every ship: queue match groups against the top 3 and run the analysis. Our sparring results are only a
filter; the ladder is the judge.

---

## 7. What could make this plan wrong

- The 15 games are one match group per team. Their bots may change; re-run the analysis on new groups.
- Our side was always side A. Side B can behave differently on some maps (the repo found collision and eight
  flip with the side).
- The fight patch was measured against our own family only. Its effect on the top teams is the first thing to
  check on the ladder.
- Builds and draft did not help on their own today. If they still do not help after Part A, believe the test and
  keep our builds.
- Counting a champion's "damage stat" ignores Ren's retaliation and Varg's shield; the item table in 01 is about
  the main damage stat only.
