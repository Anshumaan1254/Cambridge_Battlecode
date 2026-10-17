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

Export formats: `bitboard::export_linear_buffer()` is **bit-packed** (`ceil(W·H/8)` bytes, row-major, least
significant bit first), while `distance_field::export_linear_buffer()` is one `uint16` per tile. Reading a
bitboard export one byte per tile reads past the buffer (our first crystal-shortcut scan did this).

A turn that runs out of fuel pauses and finishes in the next round: the body loses that round. Any loop that
can cost more than the remaining budget must check `fuel_remaining()` inside the loop, not only before it
(the same scan lost each body 13-14 of its first 40 turns on the 50x65 hole map before this was fixed).

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

### Turn order and priority (probe bots + 14,069 decoded ladder rounds, 0 mismatches)

Each round: camp respawns, capture resolution, then **all camps attack**, then champion turns. Recall and
tribute completions and respawns happen at the start of that champion's own turn.

1. Team A acts first in odd rounds, team B in even rounds, whatever the priorities.
2. Each team's bodies are sorted by priority, highest first (ties by draft index; dead bodies keep their
   slot; Cassi and Issac are two bodies).
3. The teams alternate turns, starting with the round's lead team; the bigger team's extra bodies act
   last, one after another.
4. `set_priority` accepts any int32; the last call in a turn wins; it applies from the next round and
   persists. A visible enemy's current and next priority and its completed-turn bit are readable.

So a champion can act twice in a row: last in a round its team trails, first in the next round its team
leads. The strongest ladder team (5 bodies vs our 4) did this 5-21 times per game in fights. Our bot now
gives fighters +1000 priority when we lead the next round and -1000 when we trail it, and escapers 2000.

A stun cast before its target has acted this round removes the target's turn in the same round; cast
after, it removes the next one.

### Camps

- Each camp hits the nearest champion within range 3; ties go to the tied champion that acts earliest in
  the round. A tank strictly nearer to every camp absorbs all hits; a ranged ally at distance 2-3 takes 0.
- Camps never wake from proximity, only from damage; damaging one camp wakes its whole group.
- Varg's splash deals full damage to every camp within Chebyshev 1 of the target, diagonals included.

### Recall, tribute, capture

- Recall started in round R lands at the start of the champion's turn in R+5 with the bag and a full turn.
  **Health is restored only after a turn ends on spawn**, so rest one turn. Moving and recalling in the
  same turn is legal. Any camp or champion damage cancels it silently.
- Tribute (banking) is **not** cancelled by camp or champion damage; death, **a stun** and **an enemy altar lock** do stop it (measured on 2.2.5, see "Session 5 probes" at the end; the old text said only death).
- An enemy on any tile of a group **resets** our capture: it completes 6 rounds after they leave and they
  get nothing. Two allies on a group split the reward equally with no speed-up.
- Cassi and Issac die together wherever they are, both bags lost; they split a shared capture.

### Vision

- Bushes hide a champion completely from anyone outside the bush, even adjacent and even while it
  attacks; a ward outside the bush does not reveal it, a ward inside does.

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

## Session 5 probes (cambc 2.2.5)

Scripted two-team games on purpose-built maps (`maps/probe5/p5.map26a`, 25x25 rot180, one centre altar at (12,12), gem clusters and a wolf near each
spawn; `p6.map26a`, 31x31, 16 gem clusters per half). Probe bot: `experiments/wip/x_probe/` (copy of the `probe-rules` approach, one scenario file per
test); re-run everything with `tools/probe5_all.sh` (about 70 s, one game at a time). Logs land in `/tmp/probe5/<name>/` and the numbers below are
`team-a.stdout`/`team-b.stdout` lines plus replay events from `tools/replay/decode.mjs`. How to reproduce each: `experiments/wip/x_probe_NOTES.md`.

Camp rewards measured on the way: gem cluster 24 gems, wolf 22 gems + 90 gold, gold cluster 35 gold; a gem group respawns about 50 rounds after its reward
is taken. Altar lock costs 10 gold (carry limit 1) and, like every consumable, can only be bought on spawn (error 55 elsewhere; Tavi is no exception).

| # | Fact | Evidence | Consequence for the bot |
|---|---|---|---|
| 1 | **A stun cancels a tribute in progress**, immediately and for good. The bag stays carried and nothing resumes: the tribute has to be restarted from tick 0. | `s1`: B Vendetta starts a 46-gem tribute r52 (`rem=5`); A Tavi's stun (slot 1, range 4) lands r52; r53 `sub=0 stun=1 gems=46`, never banked (`submitted B=0` to r90). Control `s1b`: Tavi basic-attacks it every turn r52-r56 (hp 445 to 305): `rem` counts 5..1 and the 46 gems land at the start of r57. | Damage never stops a tribute; a stun or death does. ENGINE_FACTS line "only death stops it" was wrong. Legend already assumes this (see below) and is right. A stunner at range 4 is the cheapest way to stop even a winning tribute (cooldown 8, no gold): the opportunity/rally logic should count Tavi, Ren, Prism, Cassi stuns, not only melee kills. |
| 2a | **An altar lock placed on an altar where an enemy is mid-tribute stops that tribute at once.** | `s2`: B starts r51 (`sub=1 rem=5`); A Tavi places the lock the same round (event `Place altar lock` r51, from Chebyshev 2); B's next turn r52 `sub=0`, bag still 46. | `use_locks()` (brain.cpp ~1069) is right to place a lock when an enemy tributes next to the altar: it cancels the bank and costs the victim the ticks already spent. |
| 2b | **The locking team can still tribute at its own lock.** | `s2c`: lock placed r47 (3 hits left until r55); A Vendetta starts a 24-gem tribute r50 with the lock standing and banks it at the start of r53 (`submitted A=24`). Same in `s2`: A banks r50-r53 while B is cancelled. | A lock is a one-way gate: our own banking is unaffected. |
| 2c | **Destroying a lock takes 3 hits, one basic attack per hit.** An attack on the lock is a normal `attack(altar_lock)`: the attacker's attack is used up (`can_attack` 0 afterwards; move and cast stay available). Vendetta's attack reset gives 2 hits in one turn (`s2c` r58: atk, reset, atk, 2 to 0, lock gone). No decay: `hits_remaining` stayed 3 for 8 rounds untouched. | `s2c`: Ryth r55 `attack` -> hits 3 to 2, `can_attack=0 can_move=1`; Vendetta r58 `attack` 2 to 1, `reset ok=1 can_attack=1`, `attack` 1 to 0, `has_altar_lock` false. | An enemy lock costs a Vendetta/Tavi/Vesper/Varg-type body 2 turns, anyone else 3. |
| 2d | **`submit_gems` on an altar locked by the enemy does not throw: it is executed as an attack on the lock** (1 hit per call, no tribute started). The 4th call starts the tribute normally. | `s2`: B calls `submit_gems` r52, r53, r54: each returns normally with `sub=0`, replay events are `Attack` from (13,13) to (12,12) (not `Submit gems`), lock hits 3 to 2 to 1 to gone; r55 `Submit gems` event, tribute runs r55-r60 (46 gems = 5 ticks, banked start of r60). | Legend already prices an enemy-locked altar at +6 steps (brain.cpp 740, "three hits to clear it") and clears it implicitly: `tribute()` keeps calling `submit_gems` each turn (3 wasted turns, then the 4th starts the channel), and `tribute_start` is overwritten by every call, so the tick bookkeeping in `handle_channel` stays right. Right as it is. Never read "returned without exception" as "tribute started": check `is_submitting_gems()`. |
| 2e | **Placement range is 2 (Chebyshev), not 3.** | `s2`: from (9,12), distance 3, `use(altar)` throws engine error 119 "Altar is outside ward placement range"; from (10,12), distance 2, `ok=1`. The target is the altar tile itself, no tribute needs to be running (`s2c` places on an idle altar). | `use_locks()` requires `cheb(altar,pos) <= 2`: correct. |
| 3 | **Several champions tribute at the same altar at once**: two of one team, and both teams together. | `s3`: round 66 all four start (A Vendetta 72 gems, A Ryth 22, B Vendetta 48, B Ryth 24; tiles (11,11),(11,12),(13,13),(13,12)); every body shows `sub=1` with `rem` counting down in parallel r66-r73; they land independently (r69, r69, r71, r74). The submit range is 1 from the altar tile, so an altar has at most 8 usable tiles. | No queueing at an altar, but its 8 neighbour tiles are the capacity; the enemy standing on them blocks ours. Altars are not a shared resource in time. |
| 4a | **Duration = ceil(gems / 10), minimum 1** (settings: `submit_gem_duration_multiplier 0.1, base 0, minimum 1`, read from `bc::constants`). It lands at the start of the tributer's own turn in round R + ticks, so a 1-tick bank (<= 10 gems) has no stuck turn. | Measured (start round, bag landed): 22 gems 3 ticks (r66 to r69), 24 gems 3 (r50 to r53), 46 gems 5 (r52 to r57), 48 gems 5 (r66 to r71), 72 gems 8 (r66 to r74), 264 gems 27. 22 and 24 rule out floor/round (2), 72 rules out round (7). Exactly 10, 11, 20 and 66 gems could not be built (camp rewards are 22/24 gems, a split needs Cassi & Issac); the boundary is covered by the constants. | Formula in `tribute()` (`(gems + 9) / 10`) is exact. `rem` shown to others starts at ticks and reaches 1 on the last stuck turn. |
| 4b | **Gems stay in the bag for the whole channel and count as banked only when the tribute lands**; `global_submitted_gems` jumps at that moment, not at the start. | `s1b`: bag 46 and `submitted B=0` through r56, bag 0 and `submitted B=46` in r57. | A tribute that is stunned, locked or whose carrier dies before the landing round contributes nothing. A "winning tribute" is only won on its last turn. |
| 4c | **The win registers the moment a tribute lands, mid-round, and the game ends there.** If both teams' last tributes land in the same round, the team whose champions act first in that round wins: team A in odd rounds, team B in even rounds. The other tribute never lands. | `s6`: both teams, mirrored scripts, 1032 gems each; both final 264-gem tributes start r222 and would land r249. Result: `Team A wins: reached 1000 gems in round 249`, final gems A 1032, B 768. `s6b`: everything delayed one round, both land r250: `Team B wins ... round 250`, A 768, B 1032. | Photo finishes are decided by turn order, not by gem count: one tick of duration matters, and a body that can complete one round earlier (smaller last bag, or a split of the last bank across two bodies at 8 tiles) wins outright. `set_priority` only orders bodies inside a team, so it cannot flip this. |
| 4d | **Round-limit tiebreak** (not played out, read from the engine's result strings in the `cambc` binary): after round 2000 the winner has more banked gems; if tied, more gold earned; if tied, more kills; if still tied, **team B wins**. | strings in `/usr/local/bin/cambc`: "round limit (2000) reached with more gems", "...; tied on gems, more gold earned", "...; tied on gems and gold, more kills", "...; tied on gems, gold and kills; team B wins ties". | A stalled game is decided by banked gems, then total gold earned (not held), then kills. |
| 5 | **Home emblem: recall takes 3 turn ends instead of 5.** | `s5`: A Vendetta buys 5 home shards (160 gold to 10), recall at r125 shows `rem=3` and the body is on spawn at the start of r128. A Ryth without the emblem recalls the same round: `rem=5`, arrives r130. | `constants::recall_time - 2` with Home (brain.cpp 3013) is right. The other uses of `recall_time` (brain.cpp 1692, 1969, 2173) ignore `has_home`, which is harmless while we never buy it, but an enemy with Home recalls 2 turns faster than our model of its escape/return time. |
