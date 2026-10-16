# CAMBC 2026a — winning strategy

This is the strategy the `legend` bot implements, why, and how it was validated. It follows the team
plan (`CAMBC_2026a_Strategy_Plan.md`) section by section, and replaces its guesses with measurements
from the real engine wherever we could test them. Numbers marked *(measured)* come from the local
engine; the full list of verified mechanics is in [ENGINE_FACTS.md](ENGINE_FACTS.md).

> Scope note. The competition site (`2026a.battlecode.co.uk`) is blocked from the environment this was
> built in, so the official map pool, ladder and other teams' replays were not available. Everything
> was tested on 64 generated symmetric maps (sizes 30–100, all three symmetries, 3–5 champions) against
> our own sparring archetypes. The feedback loop in [FEEDBACK_LOOP.md](FEEDBACK_LOOP.md) closes that gap:
> it turns your ladder matches into reports this strategy can be re-tuned from.

## 1. What actually decides a game

1. **It is a farming race with a fixed supply.** First to 1,000 tributed gems wins. Unopposed, the
   bot reaches 1,000 in ~440 rounds on average *(measured, 128 games)*. Against an equal opponent
   it takes ~630 rounds, so the opponent removes about a third of our pace. Every round a body is idle,
   travelling or dead is lost supply.
2. **The real throughput limit is body-rounds, not camps.** A capture pins one champion for 6 rounds,
   and only one champion is needed. With 3–5 bodies the team is body-limited on most maps. The plan's
   rule "one champion per camp, pairs only for elks" is right; **extra allies on a capture split the
   reward and waste a body**.
3. **Deaths are the biggest leak.** In contested games each team loses 8–18 champions per game *(measured)*.
   Each death costs 60 rounds of that body plus the carried bag, and gives the killer 50 gold and the bag.
   Cutting our deaths was worth more than any farming tweak.
4. **Gold snowballs.** Shards add the champion's full growth per 30 gold. A 2x gold edge shows up as
   faster kills and won fights. Lifetime gold is also the first tiebreak at round 2,000.
5. **Camps never heal.** This one fact changes the economy (section 3).

## 2. Hidden techniques, loopholes, traps and baits

### Techniques we exploit (all verified)

| # | Technique | Why it works | Where in the bot |
|---|---|---|---|
| 1 | **Multi-trip farming** | Camps never heal. A group too strong for one health bar (2-wolf packs, elks) is cleared over several heal trips. This removed ~50% idle time on elk-heavy maps (747 → 349 rounds to win on one map) | `group_score` trip model |
| 2 | **Zero-risk spell chipping** | Range-4 spells outrange the camps' range 3 | `spells_on_camp`, pinned-turn casts |
| 3 | **Stun the camp, not just the enemy** | Stunned camps skip their attack | Tavi/Prism/Ren/Ryth casts on awake camps when no enemy is near |
| 4 | **Move + tribute in one turn; ≤10 gems is free** | Engine allows starting the channel after walking | `tribute()` |
| 5 | **Global death tracking** | `is_alive()` works on unseen enemies | enemy-half risk scales with living enemies |
| 6 | **Retreat before recalling** | Any damage cancels recall; camps don't chase | `safety()`, `go_home()` |
| 7 | **Ranged dash-then-shoot, double attack** | Dash spends the cast, not the move/attack; reset restores the attack | `farm_group`, `engage` |
| 8 | **Never wait on a respawning tile** | An occupied spawn tile delays the respawn | `wait_group` |
| 9 | **One body per capture** | Rewards are split | claims in shared memory |
| 10 | **Altar lock as a channel breaker** | Placing a lock cancels enemy tributes at that altar; our own team can still use it | `use_locks()` |
| 11 | **Reverse search fields** | One field per target, built lazily; stepping is a neighbour lookup | `nav.cpp` |
| 12 | **Fuel discipline** | Cache `camp_groups()` (25k) and champion handles; never iterate tiles | `world.cpp` |
| 13 | **Read enemy cooldowns** | A visible enemy's ability cooldowns are readable: no dash up means melee reach 2, not 4; no burst up means a cheaper fight | `build_danger`, `combat` |
| 14 | **Teleport islands** | Camps walled off from walking are reachable with a 10-gold crystal (range 3, ignores walls); recall gets you out with the bag. Uncontested gems on maps that have them (5–1 on our island maps) | `find_islands`, `island_task` |
| 15 | **Stunners act first** | Within a team, higher priority acts first; stunners get the highest so their stun lands before allies and enemies act | `Brain::init` |
| 16 | **Play the scoreboard** | Ahead by 150: bank smaller bags, raise the fight bar. Enemy ≥ 650 and ahead: steal, hunt carriers, take closer fights (+4.6% head-to-head) | `update_mode` |

### Traps and baits (what looks good but loses)

| Trap | Why it loses | Evidence |
|---|---|---|
| **Vendetta first pick** (the plan's default) | Best farmer on paper, but 800 health melee dies too often in contested games | Varg/Tavi/Stellar/Ren core beat a Vendetta-first draft ~60% over 128 games |
| **Monolith early** | 20,000 HP, 200 damage per round: even five range-4 casters need ~170 rounds for 200 gems — farming pays ~2.5x more | arithmetic + scoring |
| **Solo elk at full commitment** | 2,400 HP × 60 dps kills any champion before the elk dies | Ryth died soloing an elk in the probe |
| **Recalling in a fight** | Damage cancels it; you die channelling | probe |
| **Chasing fleeing enemies** | Kills don't win; gems do. We killed a passive bot ~10× per game and still lost 25% of games until chasing was reined in | sparring results |
| **Waiting for respawns** while enemy-side camps sit untouched | Bodies idle 50%+ | trace stats |
| **Cassi & Issac as "free extra body"** | Linked death: one gank kills both and pays one bag | tournaments: never better than Ryth/Ren in the 5th slot |
| **Danger-zone avoidance via one shared alert** | One 2-byte alert slot overwrites rally calls; allies abandon contested areas | win rate vs aggressive fell 79% → 67%; disabled |
| **Verbose draft analysis** | 1M first-turn fuel runs out → random picks | probe |
| **Standing on spawn tiles to "guard" a camp** | Delays our own respawn | engine rule |

## 3. The meta: common strategies and their counters

We built each common archetype as a parameter or style variant of the same engine-correct bot,
so the comparison isolates the strategy, not the code quality.

| Archetype | What it does | How it fares | Counter (implemented) |
|---|---|---|---|
| **Pure farmer** ("passive") | Farms, never fights, banks often | Loses to fighters: we win 90.6% | Punish carriers and channellers; fight only with local edge; keep farming |
| **Aggressive invader** | Fights at even odds, farms the enemy half | Bloody, many deaths both sides; we win 80–85% | Fight back when they can already hit us; don't flee same-speed melee; focus fire; tribute before risky fights |
| **Deathball** (all five together) | Groups up, kills isolated champions | Kills us often but farms ~5x slower: we win 99–100% | Keep farming in parallel; one body per capture; avoid 1v5s; their side is empty, so steal it |
| **Vendetta rush / burst drafts** | Early ganks with dash + reset | Dies to durable comps | Durable draft (Varg, Ren, Ryth), stun first |
| **Monolith rush** | Whole team on the monolith | 170+ team-rounds for 200 gems | Farm harder; contest the capture tile at the end (one body on any tile resets their timer) |
| **Altar locker** | Locks our altars | Costs 3 attacks per lock | Tribute converts to lock attacks automatically; prefer unlocked altars (+6 step penalty) |

Game-theoretically the draft is **simultaneous with duplicates allowed**, so there is no denial and no
counter-picking on information we don't have: the right move is the best *robust* composition, found
empirically by round-robin tournaments (section 5), with small map adjustments.

## 4. The final strategy (what `legend` does)

### Draft
Base values from composition tournaments, then small map adjustments (multi-monster groups favour
Varg/Stellar/Ren, two or more elks favour Ryth, very spread small camps favour Cassi & Issac):

**Varg → Tavi → Stellar → Ren → Ryth** (Cassi & Issac / Vendetta as alternates).

- Varg: splash on multi-camp groups, 250-point self-shield, 1,000 HP — the most robust farmer-fighter.
- Tavi: shops anywhere (no trips home), 2.2× focus stun-nuke at range 4.
- Stellar: highest spell damage at range 4 (2.0× and 1.4× area) — safe chipping and burst.
- Ren: stun + dash + retaliation (hits back at every camp and enemy that hits him).
- Ryth: 1,200 HP tank, area stun, strength from health.

Fuel-safe: analysis is one BFS from each spawn; any failure falls back to a fixed list so a pick is
never missed.

### Farming loop (every champion, every turn)
Score every camp group and run the best one (claims in shared memory stop duplicates):

```
score = (gems + 0.22·gold) × (1 + 0.55 if enemy half) / (travel + wait + kill + 6 + trips·homeTrip + risk)
```

- *kill* = remaining HP (remembered — camps don't heal) / our damage per round.
- *trips* = extra heal trips needed when the camps' damage over the kill time exceeds our health budget.
- *risk* adds rounds for the enemy half (scaled by how many enemies are alive), for recent enemy
  sightings, and halves the value if an enemy stands on the tile.
- Respawning groups are worth going to if they come back within ~18 rounds of arrival; we wait next to
  the tiles, never on them.
- A little hysteresis (×1.15) keeps a champion on its current task.

### Tribute
Bank when carrying ≥34, when an altar is ≤5 steps away, before fights while carrying ≥10, when the
team would reach 1,000, and in the endgame (round + distance + ticks + margin ≥ 2,000). Ten gems or fewer
are free; moving and starting a tribute happen in the same turn.

### Combat
Each champion estimates a local fight from what it can see:

```
advantage = (our HP / their DPS) / (their HP / our DPS)      (allies within 5, enemies within 8)
```

- **Engage** proactively at advantage ≥ 1.3, or when the focus target dies to our burst this turn.
- **Fight back** when they can already hit us and advantage ≥ 0.75 — fleeing an even fight just
  hands them free hits.
- **Cornered** by melee we can't outrun (same speed, they move and hit in one turn): fight unless
  advantage < 0.45.
- **Flee** otherwise, toward spawn, avoiding threatened tiles; post a danger alert.
- **Focus target** is team-consistent (gems + channelling bonus over HP, no distance term), so allies
  who see the same fight hit the same enemy. Stun first on channellers and melee divers.
- Don't fight near their spawn unless the kill is certain; don't take even fights while carrying ≥40 gems.

### Scoreboard modes
`global_submitted_gems()` shows both scores. Ahead by ≥150: tribute at ¾ of the normal bag and require
advantage ≥1.6 to start a fight. When the enemy has ≥650 and leads by ≥75: lower the fight bars, raise
the value of their camps and drop the enemy-half risk, because a slow loss is still a loss.

### Teleport islands
At start, find camp groups no walking path reaches, and a launch tile within range 3 of a free tile
inside. Buy a crystal (10 gold) first when such islands exist; a champion near spawn compares the trip
(walk + 4-turn channel + kills + captures) with its best walking target, teleports in, farms every group
inside, then recalls out once nothing there is worth waiting for.

### Safety
Retreat when health falls below 25% or below four rounds of the camp damage hitting us. Step out of
camp range first, recall only when nothing can hit us and spawn is > 5 steps away; heal fully on spawn.

### Items
Complete one emblem at a time: melee farmers **Jungle (strength)** first (30% less camp damage =
fewer heal trips), then Monster, then Power. Tavi buys Monster/Power strength anywhere. Casters build
Focus. Carry one 10-gold altar lock after the first emblem.

### Team talk (8 bytes)
Bytes 0–5: one per body, claimed group + "need help" bit. Bytes 6–7: one alert (tile + kind:
danger / rally / opportunity). Allies within ~9 tiles answer rally calls when healthy.

## 5. ML, RL and game theory: what is used and why

- **In-game neural policies are not viable.** 100k fuel per turn is ~100k wasm instructions; the bot
  already spends 30–70k on perception and pathing on 100×100 maps. A tiny linear scorer is the most a
  turn can afford, which is exactly what the utility function is.
- **Offline optimisation is where learning pays.** Matches are deterministic and take ~1.5 s, so the
  bot is tuned by **self-play black-box optimisation**: `tools/tune.py` runs coordinate descent over
  `params.h`. Each candidate plays head-to-head against the current best on 64 maps × both sides and
  must not regress against a panel of frozen opponents. This is the same idea as RL from self-play,
  but with a sample-efficient optimiser instead of gradient steps.
- **Empirical game theory for the draft.** Composition tournaments (round robins of forced drafts)
  form a payoff matrix; we pick the composition with the best worst-case and average, which is the
  robust answer to a simultaneous, duplicate-allowed draft.
- **Next steps** (see FEEDBACK_LOOP): behaviour cloning targets from top-team replays (their tribute
  thresholds, fight timing, routes) and CMA-ES over the full parameter vector once ladder data exists.

## 6. Measured results (current bot)

| Opponent | Win rate (134 games: 67 maps × both sides) |
|---|---|
| starter bot | 100% |
| deathball variant | 100% |
| early rush (deathball invade for 160 rounds) | 88% |
| v1 aggressive variant | 86% |
| v1 passive variant | 85% |
| v1 (first version of this bot) | 63% |
| previous release (v4) | 56% |
| unopposed pace | 1,000 gems in ~466 rounds |

Tuning log, for the record: a 30-candidate coordinate-descent pass over 15 parameters accepted only
`gold_value 0.22 → 0.12`, and that gain did **not** transfer once the newer features were merged
(0.12 lost 48.5% to 0.22 head-to-head), so the shipped value is 0.22. The hand-set defaults sit at a
local optimum for our sparring panel; real gains came from structural changes (multi-trip farming,
fight-back rules, the durable draft, scoreboard modes, cooldown reading, islands). Re-tune on the
official map pool against ladder-derived opponents (FEEDBACK_LOOP.md).

## 7. Where this could be wrong

- **Map pool.** Our generator is a guess at the official maps. Re-run the composition tournament
  and the tuner on the real pool (`cambc maps pull`) as soon as you have it.
- **Top teams may fight better than our archetypes.** If ladder reports show us losing fights we
  "should" win, raise `fight_margin`, and look at the death list in the match report.
- **Turn order inside a round** was not probed. Priority (`set_priority`) is unused; stunners acting
  first could matter in close fights.
- **Patches.** All costs, ranges and stats are read from the API at runtime, but tuned constants
  should be re-validated after any balance change.
