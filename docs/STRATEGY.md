# CAMBC 2026a — winning strategy

This is the strategy the `legend` bot implements and the evidence behind it. The October 16 revision
is built on 24 decoded ladder losses (we lost 17 of 20 scrims against four top teams) and the 12 real
ladder maps extracted from those replays. Verified mechanics are in [ENGINE_FACTS.md](ENGINE_FACTS.md),
the learning system in [LEARNING.md](LEARNING.md).

## 1. Why we were losing

Every number below comes from the decoded replays (`tools/replay/decode.mjs` + `report.py`).

| Finding | Evidence | Fixed by |
|---|---|---|
| **Big packs were never farmed.** The camp score assumed one champion tanks every camp for the whole kill, ignored Varg's splash and allies, and rejected anything needing more than 3 heal trips | On the 3-wolf-pack ladder map the old bot lost **132-1012 to the official starter bot** on both sides; every 66-gem pack scored -1, the team farmed gold clusters | §3 farming model |
| **We died 3x as often.** 12.2 deaths per match vs their 4.0; 28-42% of our body-rounds dead; half the team dead for a third of the game | 245 deaths: 50% with no ally within 6 tiles, 64% on our own half, median HP 5 rounds before death 58% (burst, not attrition), 40 of 69 deaths against one opponent dealt zero damage (we fled same-speed chasers) | §4 fights |
| **They recall as transport, we only in emergencies** | They recall 2.4x more, at ~50-70% HP, right after captures (the reward still lands), then heal, shop and bank near spawn. Our recalls came at a median 20% HP; 8 of 28 died mid-recall | §3 recall loop |
| **They act first in fights** | One team called `set_priority` ~200 times per game; its killing blow landed before our victim could act in 51 of 64 deaths | §4 priority |
| **Every top team drafts Cassi & Issac** | 24 of 24 opponent drafts; an extra body for one pick (+33% farmers at team size 3) | §2 draft |
| **Spawn deadlock** | On maps where the spawns touch, three of our four champions traded hits with healing enemies on their spawn for the whole game (110-286 at round 2000 vs the starter bot) | §4 |
| **Gold-only clusters overvalued, HP never bought** | 25 of 32 captures gave 0 gems in one loss; their champions ended with 1800-2000 HP vs our 1125-1500 | §3 items |

## 2. Draft

Picks are simultaneous and duplicates are allowed, so the draft is about fielding the composition that
wins most on the map, not denial. Values come from round-robin tournaments of the **same bot code** with
forced drafts (`tools/draft_tournament.py`, 5 drafts, 39 maps x 2 sides, 780 games):

| Draft (pick order) | Mean | Worst matchup | Size 3 / 4 / 5 |
|---|---|---|---|
| **Ren, Stellar, Cassi & Issac, Ryth, Varg** ("meta") | **0.554** | **0.538** | 0.50 / 0.53 / 0.58 |
| Stellar, C&I, Ren, Varg, Tavi | 0.522 | 0.462 | 0.58 / 0.54 / 0.49 |
| Stellar, C&I, Varg, Tavi, Ren | 0.506 | 0.436 | 0.46 / 0.46 / 0.55 |
| Stellar, C&I, Varg, Ryth, Tavi | 0.497 | 0.449 | 0.46 / 0.49 / 0.51 |
| Varg, Tavi, Stellar, Ren, Ryth (old) | 0.420 | 0.385 | 0.50 / 0.48 / 0.36 |

The bot drafts "meta" (it is also what the strongest ladder team drafts), with one map adjustment: at
team size 4, when most of our camp groups are multi-camp packs, Varg comes before Ryth (splash). Ren is
a health/focus tank whose retaliation hits every camp (and champion) that hits him; Cassi & Issac are two
farmers; Stellar is the range-4 burst; Ryth tanks elks and stuns packs. The draft code keeps every
composition's measured value so re-running the tournament after a patch updates the choice.

## 3. Farming

**Camp value per round** (`group_score`): gems + 0.22 x gold, divided by travel + wait + kill time + 6
capture rounds + heal trips, with risk terms.

- *Kill time* uses our real damage against this group: Varg's basic attack hits every live camp next to
  the target (a packed trio takes ~2.2x damage), radius-1 area spells likewise, Ren's retaliation adds
  0.2 x focus per attacking camp, attack resets add 1/8.
- *Damage taken*: camps hit the nearest champion, so a ranged champion next to a melee ally takes almost
  nothing; Jungle (-30%) and Durability (-10%) emblems, Varg's shield and stuns on camps reduce it.
- *Heal trips*: camps never heal, so a group too strong for one health bar is farmed over several trips;
  each costs recall-or-walk home and back. Up to 5 trips.
- *Joining*: a second body joins a pack that is heavy for the bodies already on it (multi-camp, elk, or
  more than 14 rounds for them); the lowest claimer index captures.
- *Threat*: camps where a stronger enemy force was seen in the last 8 rounds are skipped.
- *Never idle*: with nothing worth farming, top up at home (heal, shop) or move to an ally's pack.

**Recall loop.** Recall is transport, not an emergency:
- *Recall while capturing*: step on the dead camp's tile, recall one turn later; the reward lands with
  the teleport (ENGINE_FACTS). Done whenever spawn is 8+ steps away, nothing can reach us, and we are
  hurt, can shop (90+ gold after the capture), or will need to bank.
- *After banking* far from home while hurt or rich; *to shop* once 4 shards are affordable; bank via the
  altar next to spawn when recall + walk beats walking to the nearest altar.
- Never recall when an enemy seen in the last 2 rounds is within 7 tiles (any damage cancels it), and
  cancel a recall when a threat closes in.

**Banking**: from 22 gems before round 150 (gold and safety sooner), 34 after; immediately when an altar
is on the way, before risky fights, or when it wins. *Contested altars* (about as close to their spawn as
ours) where enemies were seen in the last 8 rounds are avoided unless an ally stands by: the bag is
safer moving with us than walking alone into their pack.

**Items**: Monster > Jungle (health) > Treasure > Durability (health) > Power for melee farmers; Ren:
Jungle (health) > Power (focus) > Durability > Treasure (focus); casters: Monster (focus) > Durability >
Treasure > Power. +13% gold and 65% head-to-head against the old builds.

**Crystal shortcuts.** Teleport crystals hop up to Chebyshev 3 over holes and walls. A resumable scan of
the map collects launch->land pairs that save 15+ steps; a group reached much faster through a hop is
scored with the hop's travel time, and the champion buys a crystal, walks to the launch tile and hops.

## 4. Fights

Each champion estimates the local fight (`combat()`):

    advantage = (our HP / their DPS) / (their HP / our DPS) x learned confidence

Our side counts allies within 6 with their spells (Stellar and Cassi were counted as ~0 before); a ready
enemy stun counts as extra damage; on our own spawn we add a full health bar (it heals 100% per round).

- **Ignore enemies on their own spawn** unless one turn of burst kills them.
- **Escape feasibility**: fleeing works only if no melee/dash chaser is close, our dash outruns theirs,
  or we survive the walk home. Otherwise fight back (unless hopeless): fleeing a same-speed chaser
  hands it free hits. When we do retreat, stun the chaser if that stun allows walking, and melee
  champions strike after their step.
- **Backup**: allies in sight or claiming a camp within 8 tiles count as backup. Alone, a fight needs
  advantage 1.6 or a sure kill, and we start walking home as soon as a stronger group is within 7.
- **Numbers**: with more enemies alive than allies, play defensively (no enemy half, higher fight bar);
  down by two, a freshly respawned champion waits up to 15 rounds on spawn for the next ally instead of
  walking out alone into their pack. With half the team dead, only sure fights.
- **Targets** are team-consistent: carriers, channellers, and Cassi/Issac (linked death) first; never
  swing at Ren with less health than 2.5x his retaliation.
- **Turn order**: the engaged champion sets the highest priority (stunners and low-health champions a
  little higher) so it acts before the enemy fighters it faces; capturers medium; others low.
- **Channels** are cancelled when finishing them would cost the bag or our life.
- **Opportunities**: a visible enemy tributing (or recalling with a bag) is posted to the team; allies
  within 12 (16 when they are close to winning) converge, at lower health than a normal rally.

## 5. Scoreboard and stance

`global_submitted_gems()` shows both scores. Ahead by 150: bank smaller bags and fight only clearly
winning fights. They have 650+ and lead: steal, hunt carriers, take closer fights. On top of that the
in-match learner (LEARNING.md) picks a team stance every 40 rounds from rewards and punishments: SPREAD,
GROUPED (when we are being invaded) or PUSH (when we win fights).

## 6. Measured results

Local evaluation on 39 maps (12 real ladder maps + 27 generated) x both sides = 78 games per row; the
"hunter" opponents are aggressive archetypes on the new code with the ladder's drafts.

| Opponent | Old bot (v5, what was on the ladder) | New bot |
|---|---|---|
| starter bot | 88% (lost the 3-wolf-pack map on both sides) | **100%** |
| old bot (v5) | — | **81%** |
| pack-opening hunter (Ren/Stellar/C&I/Ryth/Varg, aggressive) | 42% | **87%** |
| aggressive C&I hunter (C&I/Vendetta/Varg/Ryth/Stellar) | 28% | **82%** |
| new code with the Stellar/C&I draft | 14% | **55%** |
| unopposed, rounds to 1,000 | 574 | **500** |

Noise floor: identical code differing only in fuel use moves a 78-game result by up to ~3 points, so
differences under ~5 points are not significant.

## 7. What did not work (kept switchable)

| Idea | Result | Switch |
|---|---|---|
| Pair plans (claim a pack too heavy for one, wait for a partner) | -24 rounds unopposed pace, no win-rate gain | `pair_plans` |
| Untuned online learners (first version) | -10 points until the combat model was fixed; neutral now; the trainer tunes them | `learn_*` |
| Early deathball opening (`deathball_until`) | Lost to plain spread farming (also found by the analysts) | `deathball_until` |

## 8. Where this could be wrong

- Our opponents in local tests are archetypes built on our own code. They reproduce the ladder result
  (the old bot loses 14-42% to them) but real teams will differ: keep feeding ladder replays back
  (FEEDBACK_LOOP.md).
- Map pool: 12 real maps so far. Tournament maps are unseen; the draft and the trainer should be re-run
  as more real maps are extracted.
- Balance patches (Prism buff, kill reward, `HeartOfRuin`): all stats are read from the engine at run
  time, but the draft table and the trained parameters need re-running after a patch.
