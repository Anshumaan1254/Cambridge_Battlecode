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
