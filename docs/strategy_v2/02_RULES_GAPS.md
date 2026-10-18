# 02. Game rules we do not use, or use badly

Checked against `GameRules.md` (cambc2026a handbook export, uploaded 18 Oct), `docs/ENGINE_FACTS.md` (probed on the
real engine) and the current `legend` source. Ordered by how much each one is worth to us now.

Legend for "Now": **No** = the bot does not use it; **Weak** = uses it, but the replays show it goes wrong;
**Yes** = fine as it is.

## A. Big gaps

| # | Rule | Now | What the replays / code show | What to do |
|---|---|---|---|---|
| 1 | **Melee champions can move and attack in the same turn; ranged must choose.** | Weak | 633 rounds our bodies walked while being hit and dealt no champion damage (theirs 177); 278 of them with an enemy already in attack range. Fleeing melee champions step first, then have nobody in reach. | Melee: attack first, then step. Ranged: if anything is in range 3, attack and stand; cast before walking. (Part A1, `x_exec`.) |
| 2 | **Shards and emblems add stats that stack; passives do not stack.** Power = 6 points of one stat; Bruiser = 5 + 1 + 1; other emblems = 5 + a passive. | Weak | We get 21 damage points per 1,000 gold, they get 32. We buy several passives in health (Jungle, Durability) and Bruiser cycles; they buy one health emblem, then Power forever. | One health emblem, then Power in the damage stat (Part B1). Take each useful passive once and in the damage stat when possible (Durability-strength gives -10% damage taken and keeps the stat). |
| 3 | **The capturer gets the whole reward (it splits only between allies standing on the group).** | Weak | The lowest draft index captures shared groups, so Ren (index 0) earns the most gold even alone on the map (1,660 a game; Varg 846). Gold is not going to the best farmer. | Collector = the best gold converter present (Varg > Issac > Stellar > Ryth > Cassi > Ren); the others step off (Part B2). |
| 4 | **Draft phase: 10x fuel on the first turn (1,000,000), whole map visible, 1,024 bytes of draft memory readable by every champion all game.** | No | The draft writes 4 bytes (magic, version, team size, chosen comp). Every champion redoes the whole map analysis in its own first turn (the old opening fuel problem). | Plan the map once in the draft: zones, circuits, map type, objective groups, ward tiles; store ~20-70 bytes (Part C, layout in 03). |
| 5 | **Varg's basic attacks splash full strength onto every other enemy and camp within 1 tile of the target.** Area spells (Stellar 1.4x focus, Prism 1.0x, Ryth's stun) hit radius 1. | No | 14% of our deaths had Varg splash hit the victim and an ally in the same swing (theirs 6%). Our fight estimate counts enemy damage as single-target only. | Spread rule (A4) and count splash and area damage against the number of our bodies standing together. Our Varg should also look for these clumps: its swing is worth 2-3x on two adjacent enemies. |
| 6 | **Camps attack the nearest champion in range 3, every round, until they sleep (2 rounds without a champion in range).** | Weak | Our champions trade with enemies while standing next to awake camps and take the camp's hits for them (swirl r14-20, eight r30-49). | Count awake-camp damage in the fight estimate; step out to 4 before trading; prefer fights where the enemy stands nearest the awake camp (A5). |
| 7 | **Camps never heal; damage persists between visits.** | Weak | We start groups we cannot finish (`max_trips = 5` heal trips): two elks take us 184 rounds from the first hit, them 25. A half-killed group can be finished by the enemy. | Prefer groups we can clear in one visit; allow a heal trip only on our own side where nobody else will finish it, or on objectives. Keep `cast_en_route` (chip damage on our own groups on the way pays off: switching it off made unopposed pace 38 rounds worse on average, 255 on ambush). |
| 8 | **Recall: 5 turns, 3 with a Home emblem; any damage cancels it.** | Weak | We never buy Home. On big maps our bodies walk 67-80% of the time (ambush, unopposed). | On field maps (ambush, expanse, lanes) give recall-heavy farmers a Home emblem *in the damage stat* (5 damage points plus a 3-turn recall). Test it against pace. |
| 9 | **Tavi buys shards anywhere on the map** (not consumables) and can sell at spawn for full value. | No | We never draft Tavi. Team Z drafts him on 3 of 5 maps and team Y once. He never needs a shopping trip: gold turns into stats the moment it arrives. | Test Tavi as the 5th pick (instead of Ren) on field and objective maps: Treasure-focus, Durability-focus, then Power-focus, bought in the field. |
| 10 | **Picks are simultaneous, but revealed one by one.** | No | Our draft ignores what the enemy has picked. | Read the enemy's picks before each of ours. Simple rules: if they have Varg, raise our spacing distance (A4); if they have 3+ stunners, Marcella (immune to stuns) becomes an option. Keep this small: the draft is a small lever. |

## B. Medium gaps

| # | Rule | Now | Finding | What to do |
|---|---|---|---|---|
| 11 | **Turn order: camps act first; the leading team alternates every round; inside a team, higher `set_priority` acts first (from the next round).** A stun before the target acts removes its turn this round. | Weak | They hit first in 86 of 152 fights; when they did our deaths were 97 to their 17. | Strike-first rule (A6): the stunner gets the top priority the round before the engage so its stun lands before the enemy acts. |
| 12 | **Enemy stats are readable while visible** (health, strength, focus, cooldowns, carried gems). | Yes, partly | The fight estimate uses them, but treats every visible enemy within 9 as part of the fight and ignores splash, area spells and camp damage. | Keep the reads; fix the model (A3-A7), or replace it with a short look-ahead (04 section 6). |
| 13 | **An enemy on any tile of a dead group resets our capture; ours resets theirs.** | Yes | `deny_capture_mult`, `capture_reset` exist. | On contest maps, send one healthy body to step on an enemy capture when the denied value beats its lost farming (deny value = reward + their recall time). |
| 14 | **A stun cancels a tribute (bag kept, restart from 0) and a recall; damage cancels a recall only.** | Yes | Probed in session 5; `handle_channel` accounts for it. | Use range-4 stuns (Ren, Tavi, Prism, Cassi) on enemies that start banking big bags near our side, especially near the end (their score above 800). |
| 15 | **Win = first to 1,000 banked; at round 2,000: gems, then gold earned, then kills, then team B.** Simultaneous landings: the team acting first that round wins. | Yes | `win_bank`, `team_bank`, `race_mode` exist. | Keep. On the last bank, split the bag across two bodies at two altars if one tribute would take 2+ more turns than the other (ENGINE_FACTS 4c). |
| 16 | **Death: the killer takes the whole bag and 50 gold; a camp kill destroys the bag; respawn after 60 rounds.** | Weak | We lost 1,294 gems in bags at death, they lost 832. | Bank before fights when carrying 40+ (exists as `bag_caution`, `tribute_risky`); make the fight rules (A7) stricter for carriers. |
| 17 | **Bushes hide champions completely from outside; a ward inside the bush reveals it. A move into an unseen occupied tile fails and reveals it.** | Weak | We place 4.3x more wards than the top teams, yet our Varg walked into hidden enemies on swirl ("movement blocked"). | Put the ward on bushes next to the zone being farmed (the zone plan can store 2-4 ward tiles per zone) and treat "movement blocked" as a sighting. |
| 18 | **Altar lock: 10 gold, placed within 2 of an altar, blocks the enemy's tributes there until hit 3 times; placing it cancels a running enemy tribute.** | Yes, rarely | 3 placed by us, 0 by the top teams. | Keep as an end-game tool only: enemy at 850+ with a big bag next to an altar we can reach. |
| 19 | **Stuns work on camps: a stunned camp skips its attack.** | Yes | `spells_on_camp` uses stuns on camps. | Ryth's area stun on packs every 8 rounds is a free tank; keep it. |
| 20 | **Range-4 spells out-range camps (range 3).** | Yes | `cast_en_route`, casters farm from 4. | Keep. Our Stellar should do most of its camp damage from 4, not stand at 3 for basic attacks unless a tank holds the camp. |

## C. Small or situational

| # | Rule | Note |
|---|---|---|
| 21 | Vendetta: every kill (camps too) resets both cooldowns | strong on multi-camp groups (reset + dash per kill); never drafted by the top teams; not worth testing before Part A-C |
| 22 | Prism: +0.2 focus per carried gem | a Prism carrying 100 gems has +20 focus; drafted once by team Y (stampede) |
| 23 | Marcella is immune to stuns | counter-pick if the enemy has 3+ stunners; low priority |
| 24 | Willow heals an ally for 3x focus | the repo's tournament ranked Willow drafts last; skip |
| 25 | Any occupied spawn tile of a dead group delays the whole group's respawn | a body can hold an enemy group down by standing on one of its tiles; only worth it on contest maps for their best group, and only when that body has nothing better (it is a whole body's time) |
| 26 | Health bought on spawn heals the amount bought; dead champions can shop | the bot already shops while dead and on spawn |
| 27 | Teleport crystal: 3-tile hop over walls and holes after a 3-turn channel | used for islands and hole shortcuts; fine |
| 28 | Shared memory: 8 bytes for the team, all match | fully used now (claims, bag sum, stance, one alert); the new layout in 03 frees room for a focus target and engage flags by shrinking claims to zone circuit positions |
| 29 | Vision is not shared between allies | the reason the fight estimate must not count allies it cannot see as helpers (A3) |
| 30 | Fuel: 100k a turn (200k on the first play turn); a turn that runs out finishes next round | fine now; keep the draft planner inside the first draft turn's 1M (03 section 3) |
| 31 | Vesper Vale: +20% gold (+40% with a Treasure emblem), ranged, strength 45 | gold is one of our gaps (they earn 1.9x), but Vesper's camp damage is low and the repo's draft test with Vesper scored 0.42 (`ven2`); no top team drafts it; skip unless Part B shows that gold, not damage, is what limits us |

## What the top teams clearly use

From their replays: rules 1, 2, 3 (their best farmer collects), 5 (their Varg splashes our clumps), 6 (they fight us
while we stand in camp range), 11 (they hit first), 13 (30 captures on our half), 16 (our bags lost 1,294 gems at death,
theirs 832). There is no sign that they use 18 (locks), 25 (respawn blocking) or many wards. Their edge is in the basics.
