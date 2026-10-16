# CAMBC 2026a — verified engine facts

Everything here was **measured on the real engine** (cambc 2.2.2, engine 0.0.2) with the probe bots in
`bots/probe-rules` and `bots/probe-fuel`, or read from `sdk/cpp/cambc.h` constants at runtime. Where
the handbook is vague or wrong, this file wins. Re-run the probes after every patch:

```bash
node tools/mapgen/testmap.mjs                     # builds maps/zz_test.map26a (30x30 controlled layout)
cambc run probe-rules probe-rules --map zz_test --rounds 140
```

## Constants (read from the engine)

| Setting | Value | Note |
|---|---|---|
| capture_time | 5 | capture phases; see timing below |
| camp_sleep_time | 2 | rounds without an in-range champion |
| respawn_time | 60 | champion death timer |
| recall_time | 5 | turn ends (3 with Home emblem) |
| submit range | 1 | Chebyshev distance to the altar |
| submit duration | max(1, ceil(gems/10)) | multiplier 0.1, base 0, minimum 1 |
| max_rounds / winning_gems | 2000 / 1000 | |
| kill_gold / assist_gold | 50 / **0** | assists pay nothing |
| passive_gold | **0** | no income except camps and kills |
| spawn_healing | **1.0** | 100% of max health per round on spawn |
| starting gold | **0** | first shard needs 30 gold from camps |
| ward cooldown / lifetime | 1 round / infinite | one ward per champion, placement radius 2, vision 6 |
| altar lock hits | 3 | |
| tp crystal channel | 3 | |
| shared / draft memory | 8 / 1024 bytes | |

## Camps

| Fact | Evidence | Consequence |
|---|---|---|
| **Camps never heal**, awake or asleep, between visits | wolf hit for 200 at r9 stayed at 1150/1350 through r18 after falling asleep at r12 | Damage persists: farm a group over several heal trips; chip with spells while passing; last-hit steals are real |
| Camps fall asleep 2 rounds after no champion is within 3 | awake r10–r11, asleep r12 | |
| Camp attack range is 3, **range-4 spells outrange them** | Stellar casting from 4 took 0 damage | Casters farm risk-free from range 4 |
| **Stuns work on camps**: a stunned camp skips its next attack | Ryth took 0 damage the round after Tavi's stun, 60 otherwise | Stun rotation reduces tank damage on elks and the monolith |
| Camps attack the **nearest** champion in range | tank adjacent absorbs everything | A melee tank in front, ranged at range 3 behind it, take no hits |
| Camp stats do **not grow** over time (`health_growth = strength_growth = 0`) | `camp.base_stats()` | Late camps are as easy as early ones; your items make them faster |
| Camps don't move or chase | | Step to distance 4 and you are safe |
| A camp kill credits Vendetta's cooldown reset | reset ready again right after the kill | |
| An occupied spawn tile delays the whole group's respawn | handbook + `wait_group` behaviour | Never wait *on* a respawning tile; standing on an enemy group's tile denies it |

## Capture, tribute, recall timing

| Action | Measured timeline |
|---|---|
| Capture | step onto a dead camp's tile in round *T* → gems arrive at the start of round *T+6* (5 capture phases) |
| Tribute | **moving and starting a tribute in the same turn works**. 24 gems: started r21, stuck r22–r23, banked at the start of r24. ≤10 gems costs **no** stuck turn |
| Recall | started r25 → arrived at the start of r30 (stuck 4 turns). **Any damage cancels it**: recalling while a camp or enemy can hit you is suicide (we lost a Ryth this way) |
| Spawn | full heal every round on spawn; buying health shards on spawn heals the gained amount |

## Actions and combat

| Fact | Evidence |
|---|---|
| Ranged champions: **dash then basic attack in the same turn works**; walking after attacking does not | Vesper: dash OK, attack OK, move → "Movement already used" |
| Attack reset gives a real second attack in the same turn | Vesper: atk 410 → reset → atk 365 |
| One successful cast per turn across both slots (dash and reset compete) | |
| Damage spells with `exclusive_with_movement` cannot share a turn with a walk | design flags |
| Shards add **one point of the champion's growth** (`strength_points = 1`), emblems 5 (Power 6) | `item_type::info()` |
| All champions have `camp_damage_multiplier = 1.0` | `champion_designs[*].base_stats()` |

## Information and vision

| Fact | Consequence |
|---|---|
| `champion.is_alive()` works on **every** champion, including unseen enemies | You always know exactly when an enemy is dead (60-round window) — free information for safe invasions |
| Allies outside your own vision are **not visible** (position throws `api_not_in_vision`) | Coordination must go through the 8-byte shared memory |
| An enemy's `gem_count()` is readable while it is visible | Hunt carriers |
| **A visible enemy's ability cooldowns are readable** (`sdk_champion_cooldown` on their handle) | Know whether their dash, stun or burst is up before committing; the bot's threat reach and fight estimate use it |
| The raw camp-group state call reports "unknown" for unseen groups (no leak) | Keep your own memory of timers |
| Matches are deterministic for fixed bots and map | A/B tests need many maps, not repeats |

## Teleport crystal

| Fact | Evidence |
|---|---|
| A crystal (10 gold, carry 1, bought on spawn or while dead) teleports up to Chebyshev 3 ignoring walls after a 3-turn channel | `isl_*` maps: champions entered walled islands from a tile 3 away |
| Recall works from inside a walled island and keeps the bag | island champions recall out and tribute |

## Fuel (100x100 map, C++, 100k per turn)

| Call | Fuel |
|---|---|
| `distance_field::compute` (full map) | 13–19k |
| `map::camp_groups()` | ~25k (cache it once) |
| `vision::camp_groups()` | ~36k (avoid; use raw state per group) |
| `champions(team)` | ~22k (constructing unseen champions builds costly error objects) |
| `export_linear_buffer` (100x100) + iterate | ~23k + ~35k |
| `sdk_champion` record (pos, hp, stats, state in one call) | ~80 |
| `printf` in the draft | expensive: a verbose draft dump ran out of the 1M first-draft-turn budget and the engine **auto-picked randomly** |

First draft turn has 1M fuel, each champion's first turn 200k. Release and debug builds produced identical results in our tests; the platform always runs release.

## Added October 16: probes, local runs and 24 decoded ladder replays

### Champion designs (read from `champion_designs[*]` with `bots/_dump`)

| Champion | Health (+growth) | Strength | Focus | Range | Slot 0 | Slot 1 |
|---|---|---|---|---|---|---|
| Ryth | 1200 (+100) | 50 | 100 | 1 | area stun 1.0x focus, radius 1, range 4 | attack reset |
| Vesper Vale | 900 (+100) | 45 | 100 | 3 | attack reset | dash 2 |
| Vendetta | 800 (+100) | 70 | 100 | 1 | attack reset | dash 2 |
| Cassi | 700 (+71) | 30 | 70 (+15) | 3 | damage 2.0x, range 4 | stun (no damage), range 4, usable while moving |
| Issac | 900 (+95) | 40 | 100 | 1 | attack reset | dash 2 |
| Stellar | 750 (+75) | 35 | 100 | 3 | damage 2.0x, range 4 | area 1.4x, radius 1, range 4 |
| Prism | 700 (+75) | 35 | 80 | 3 | stun 1.5x, range 4 | area 1.0x, radius 1 |
| Marcella | 1200 (+100) | 45 | 50 | 1 | enhanced attack reset | damage 2.0x, range 4 |
| Willow | 700 (+50) | 45 | 105 | 3 | heal 3.0x, range 4 | attack reset |
| Ren | 900 (+100) | 40 | 100 | 1 | stun 1.25x, range 4 | dash 2 |
| Varg | 1000 (+100) | 50 | 100 | 1 | attack reset | self-shield 2.5x focus for 5 rounds |
| Tavi | 750 (+75) | 35 | 100 | 3 | attack reset | stun 2.2x, range 4 |

Every spell has an 8-round cooldown; all damage spells except Cassi's stun are exclusive with walking.
Passives: Varg splash radius 1, Ren retaliation 0.2 x focus per damage instance (also hits our champions
that attack him: three of our ladder deaths were self-kills on Ren), Ryth +0.01 strength per bonus
health, Prism +0.2 focus per carried gem, Vesper +20% gold. The engine also knows a 13th champion,
`HeartOfRuin`, that is not in this SDK yet.

### Items

Shards cost 30 gold, emblems are five shards (150). Emblem passives: Monster +10% (camp damage),
Durability -10% damage taken, Treasure +20% gold, Jungle -30% camp damage, Home 50% faster recall.
Power emblems count as six shards; Bruiser emblems as five shards plus one of each other stat.

### Turn order and priority (decoded ladder replays)

Teams alternate turns inside a round; team A goes first in odd rounds, team B in even rounds. Within a
team, higher `set_priority` acts first (default 0, ties by body index) from the next round on. The
strongest ladder team re-prioritises every round so its engaged champion acts first; their killing
blow landed before our victim could act in 51 of 64 deaths.

### Recall while capturing

Step onto a dead camp's tile in round T, start a recall in round T+1 or later: the capture completes at
the start of round T+6 and the teleport lands the same round, so the champion arrives home with the
reward, healed, and can shop at once (verified locally: recall r30, +22 gems r34, shop r35). A recall
started in round T itself lands before the capture completes and loses it. With a Home emblem (faster
recall) the recall must start later.

### Other facts

- Teleport crystal range is Chebyshev 3 (all 14 opponent hops in the replays). It works over holes and
  walls, so it is also a shortcut through hole mazes, not only an island entry.
- `spawn_region` bounds have an exclusive maximum corner. Some maps put the two spawns next to each other;
  both teams heal 100% per round on spawn, so trading hits across the border never kills anyone.
- Map files (and the map inside a replay) store one half of the camps; the engine mirrors them when a
  game starts. `tools/replay/extract_map.mjs` relies on this to rebuild ladder maps exactly.
