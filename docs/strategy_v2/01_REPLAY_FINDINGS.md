# 01. What the 15 top-team games show

Data: 3 match groups uploaded on 18 Oct 2026 (one group = 5 games against one team). We are side A (team 0) in
all 15. The opponents are called **X**, **Y** and **Z** here (match-group ids `b26d9db7`, `24706e13`,
`8ba81317`); the archives carry no team names. The bot that played is the current `legend` build: its replays
show the opening-fuel fix of `legend_rm` (at most 6 lost turns a game, all in rounds 1-3).

How the numbers were made (all scripts in `tools/strategy_v2/`, see its README):

1. `decode_dmg.mjs` decodes each replay with the engine's own wasm (the repo's `tools/replay/decode.mjs` plus
   one addition: the health change of every champion and camp at every step, so each point of damage is tied
   to who dealt it and to whom).
2. `analyze.py` turns that into tables: per team, per body, per fight, per death, per recall, per bank, per
   capture, per camp-group kill.
3. `report.py` prints the tables of this file (results, decomposition, items, champions, fights, hit-back,
   deaths, KPIs); `map_plan.py` the map capacity and zones; `fight_model.py` the fight-outcome check;
   `trace.py` a round-by-round view of any window. `run_all.py` does all of it from the downloaded zips.

Definitions used below:

- **Body**: Cassi and Issac are two bodies. "Body deaths" counts both when the pair dies.
- **Fight (engagement)**: champion-on-champion hits grouped together when they are within 3 rounds and 8 tiles of
  each other (single-linkage clustering, like DBSCAN with one point minimum). Fights with fewer than 4 hits are
  left out. 152 fights.
- **Home / neutral / enemy side**: by walking distance from the two spawns (BFS, walls, holes and altars block),
  with a 3-tile neutral band.
- **Gold earned**: every increase of a body's gold plus what it spent on items between two snapshots.
- **Damage stat**: strength for Varg, Issac, Ryth; focus for Ren, Stellar, Cassi, Tavi, Prism.

---

## 1. Results

| Map | Opp | Picks | Rounds | Banked (us-them) | Body deaths | Kills | Camp gems | Gold earned |
|---|---|---|---|---|---|---|---|---|
| collision | X | 3 | 621 | 242-1002 | 15-5 | 3-10 | 336-1024 | 1663-4775 |
| eight | X | 5 | 566 | 264-1008 | 13-6 | 4-10 | 264-1096 | 1280-4985 |
| elkring | X | 5 | 486 | 360-1008 | 10-6 | 5-7 | 432-1044 | 2659-6005 |
| packs | X | 3 | 609 | **1024-884 (win)** | 6-8 | 5-4 | 864-1088 | 3708-3640 |
| swirl | X | 4 | 466 | 168-1016 | 18-13 | 3-10 | 124-1104 | 775-5460 |
| ambush | Y | 5 | 538 | 428-1024 | 3-2 | 1-2 | 428-1024 | 1120-3340 |
| corners | Y | 5 | 446 | 320-1004 | 10-0 | 0-8 | 692-886 | 2952-4400 |
| eight | Y | 5 | 436 | 22-1130 | 17-1 | 0-13 | 88-1130 | 360-5350 |
| expanse | Y | 3 | 599 | 806-1016 | 1-0 | 0-1 | 806-1016 | 3466-4760 |
| stampede | Y | 5 | 1268 | 900-1260 | 28-14 | 10-20 | 1080-1080 | 6649-10064 |
| ambush | Z | 5 | 720 | **1110-870 (win)** | 0-3 | 1-0 | 1110-976 | 2549-3240 |
| elkring | Z | 5 | 439 | 288-1008 | 9-2 | 2-7 | 540-864 | 3210-5030 |
| fragment | Z | 3 | 639 | 270-1056 | 16-5 | 5-10 | 300-1048 | 2035-5500 |
| monolith | Z | 5 | 392 | 724-1002 | 1-0 | 0-1 | 834-980 | 3552-4110 |
| swirl | Z | 4 | 498 | 670-1024 | 19-7 | 3-12 | 864-1024 | 3932-6180 |

| Opponent | Wins us/them | Banked | Camp gems | Gold | Body deaths | Kills | Camp damage | Champion damage |
|---|---|---|---|---|---|---|---|---|
| X | 1/4 | 2,058 / 4,918 | 2,020 / 5,356 | 10.1k / 24.9k | 62 / 38 | 20 / 41 | 138k / 315k | 64k / 96k |
| Y | 0/5 | 2,476 / 5,434 | 3,094 / 5,136 | 14.5k / 27.9k | 59 / 17 | 11 / 44 | 224k / 392k | 31k / 91k |
| Z | 1/4 | 3,062 / 4,960 | 3,648 / 4,892 | 15.3k / 24.1k | 45 / 17 | 11 / 30 | 216k / 357k | 18k / 69k |
| **All** | **2/13** | **7,596 / 15,312** | **8,762 / 15,384** | **39.9k / 76.8k** | **166 / 72** | **42 / 115** | **579k / 1,065k** | **115k / 257k** |

Our two wins: packs against X (same draft on both sides, 3 picks) and ambush against Z (almost no fighting: 0-3 body deaths).
We lose both kinds of game: fight-heavy (swirl, eight, fragment, collision) and quiet farming races (expanse 1-0
deaths, monolith 1-0, ambush against Y 3-2).

---

## 2. Where the camp-gem gap comes from

Camp gems = (share of body-rounds alive) x (share of alive rounds spent hitting camps) x (camp damage per such
round) x (gems per point of camp damage).

| | Us | Them | Ratio |
|---|---|---|---|
| Alive | 80.5% | 91.0% | 0.884 |
| Hitting camps, share of alive time | 18.4% | 21.2% | 0.865 |
| Camp damage per camp round | 84.3 | 118.5 | 0.711 |
| Gems per 1,000 camp damage | 15.1 | 14.4 | 1.047 |
| **Product** | | | **0.570** (camp gems 8,762 / 15,384 = 0.570) |

So we do not waste damage (we convert it to gems as well as they do). We are dead more, hit camps less of the
time we are alive, and hit them much softer.

Per match (us / them):

| Match | Alive % | Camp rounds | Camp damage per camp round | Gems per 1k camp damage |
|---|---|---|---|---|
| X_collision | 68 / 88 | 378 / 605 | 61 / 99 | 14.6 / 17.1 |
| X_eight | 81 / 90 | 376 / 656 | 51 / 99 | 13.7 / 16.8 |
| X_elkring | 86 / 88 | 522 / 831 | 75 / 88 | 11.1 / 14.2 |
| X_packs | 85 / 80 | 512 / 523 | 78 / 93 | 21.8 / 22.3 |
| X_swirl | 56 / 72 | 238 / 424 | 74 / 162 | 7.0 / 16.0 |
| Y_ambush | 94 / 96 | 297 / 566 | 77 / 100 | 18.7 / 18.0 |
| Y_corners | 81 / 100 | 566 / 694 | 73 / 88 | 16.7 / 14.4 |
| Y_eight | 61 / 98 | 228 / 589 | 43 / 115 | 9.0 / 16.7 |
| Y_expanse | 99 / 100 | 564 / 449 | 85 / 169 | 16.7 / 13.4 |
| Y_stampede | 80 / 89 | 701 / 851 | 146 / 153 | 10.5 / 8.3 |
| Z_ambush | 100 / 96 | 605 / 570 | 73 / 105 | 25.1 / 16.3 |
| Z_elkring | 79 / 95 | 575 / 681 | 72 / 102 | 13.0 / 12.4 |
| Z_fragment | 64 / 88 | 422 / 483 | 60 / 151 | 11.8 / 14.3 |
| Z_monolith | 99 / 100 | 638 / 585 | 85 / 103 | 15.3 / 16.3 |
| Z_swirl | 57 / 83 | 255 / 482 | 199 / 197 | 17.1 / 10.8 |

Expanse is the cleanest case: almost no fighting, we even spend *more* rounds on camps (564 vs 449), and still
lose 806-1016 because their camp damage per round is twice ours (169 vs 85).

### How each body spends its time (share of all body-rounds)

| | Dead | Recall | Bank | Fight | Camp | Capture | On spawn | Walk | Idle |
|---|---|---|---|---|---|---|---|---|---|
| Us, all | 19.5 | 3.9 | 1.9 | 3.8 | 14.8 | 2.1 | 2.6 | 49.0 | 2.4 |
| Them, all | 9.0 | 5.1 | 4.1 | 3.6 | 19.3 | 5.0 | 2.2 | 49.7 | 2.1 |
| Us, Varg | 16.7 | 3.6 | 1.9 | 4.3 | 11.6 | 1.9 | 3.2 | 55.9 | 0.9 |
| Them, Varg | 3.8 | 5.4 | 7.0 | 4.8 | 17.5 | 5.9 | 2.2 | 51.7 | 1.6 |
| Us, Ryth | 14.5 | 3.2 | 0.9 | 4.0 | 12.3 | 1.2 | 2.4 | 59.1 | 2.3 |
| Them, Ryth | 10.8 | 4.5 | 5.0 | 5.9 | 23.0 | 4.7 | 2.4 | 41.5 | 2.2 |
| Us, Cassi | 24.5 | 3.0 | 1.1 | 3.1 | 14.8 | 1.8 | 2.8 | 47.3 | 1.8 |
| Them, Cassi | 12.3 | 4.7 | 3.0 | 2.5 | 20.7 | 4.2 | 2.2 | 48.4 | 2.0 |

(Labels in priority order: dead, recalling, banking, any champion damage dealt or taken, any camp damage dealt or
taken, standing on a dead camp tile, on spawn, moved, did nothing.) Both teams walk about half the time. The
difference is dead time and camp time. Their Varg is dead 3.8% of the game, ours 16.7%.

---

## 3. Items: what the gold buys

| | Us | Them |
|---|---|---|
| Gold spent on shards and emblems | 37,530 | 68,370 |
| Damage-stat points bought | 775 | 2,181 |
| Damage points per 1,000 gold | 20.7 | 31.9 |
| Health points per 1,000 gold | 14.8 | 5.7 |
| Emblems, by family and stat | Bruiser-damage 64, Monster-damage 40, Durability-health 39, Jungle-health 34, Treasure-damage 24, Bruiser-health 17, Jungle-damage 6 | **Power-damage 295**, Durability-health 38, Bruiser-health 36, Durability-damage 23, Jungle-damage 21, Monster-damage 4 |

Their pattern, the same in all three teams: about one health emblem per champion (Durability or Bruiser in
health: 74 over their 80 bodies; 44 bodies bought exactly one, 15 two, 21 none), then Power in the damage stat for
the rest of the game. Team Z also
takes Durability and Jungle *in the damage stat* (so the passive comes without giving up damage). Examples at the
end of a game: X's Varg on eight `Ps1+PsE12+DhE` (12 Power-strength emblems, 1 Durability-health), Y's Issac on
stampede `PsE16+DhE`, Z's Varg on swirl `PsE15+DsE+JsE+BhE`.

Ours on the same maps: Varg `MsE+TsE+Js1` (ambush), Cassi `DhE+JhE+Bh2` (packs), Issac `DhE+Jh2` (packs), Stellar
`MfE+Tf1` (elkring). Our Cassi and Issac buy health first (build_style 2, `ci_health_first`) and still die twice as
often as theirs.

### Per champion (only games where both teams drafted it)

| Champion | Games | Captures | Gold earned | Deaths | Camp damage per camp round | Damage stat at r300 | First emblem (median round) |
|---|---|---|---|---|---|---|---|
| Varg | 10 | 2.1 / 5.4 | 472 / 1,339 | 1.5 / 0.2 | 138 / 219 | str 84 / 152 | 232 / 88 |
| Issac | 15 | 2.5 / 5.5 | 420 / 1,019 | 2.7 / 1.3 | 41 / 83 | str 45 / 91 | 311 / 165 |
| Cassi | 15 | 2.1 / 3.3 | 306 / 697 | 2.7 / 1.3 | 48 / 81 | focus 79 / 169 | 189 / 215 |
| Stellar | 15 | 2.3 / 4.6 | 577 / 1,008 | 1.8 / 0.7 | 141 / 195 | focus 143 / 206 | 404 / 161 |
| Ren | 9 | 4.2 / 5.3 | 762 / 1,094 | 1.6 / 0.9 | 56 / 69 | focus 163 / 191 | 125 / 118 |
| Ryth | 7 | 1.3 / 4.3 | 216 / 846 | 1.4 / 0.4 | 57 / 105 | str 57 / 93 | 449 / 127 |

Gold follows captures, and the capturer keeps it. Their Varg makes 2.6x our Varg's captures and earns 2.8x the gold.
Ours gets far less because it is drafted 4th, loses shared captures to the lowest claimer index (Varg is body 4
of 6, Ren is body 0), and dies 7x as often.

---

## 4. Farming

### Capture pace (gems captured per 100-round window, us / them)

| Match | r0-100 | r100-200 | r200-300 | r300-400 |
|---|---|---|---|---|
| X_collision | 66 / 132 | 124 / 124 | 44 / 110 | 22 / 154 |
| X_eight | 132 / 72 | 0 / 154 | 66 / 182 | 22 / 132 |
| X_elkring | 108 / 180 | 108 / 288 | 72 / 216 | 72 / 180 |
| X_packs | 44 / 44 | 136 / 180 | 132 / 184 | 136 / 228 |
| X_swirl | 0 / 124 | 124 / 88 | 0 / 168 | 0 / 416 |
| Y_ambush | 0 / 106 | 48 / 178 | 96 / 250 | 178 / 192 |
| Y_corners | 204 / 196 | 102 / 160 | 116 / 174 | 248 / 290 |
| Y_eight | 22 / 160 | 0 / 160 | 22 / 226 | 22 / 540 |
| Y_expanse | 88 / 132 | 124 / 146 | 146 / 168 | 124 / 212 |
| Z_ambush | 0 / 72 | 48 / 226 | 48 / 72 | 226 / 178 |
| Z_elkring | 108 / 180 | 144 / 180 | 72 / 216 | 108 / 180 |
| Z_fragment | 102 / 66 | 44 / 80 | 44 / 240 | 22 / 182 |
| Z_monolith | 168 / 212 | 242 / 278 | 256 / 270 | 168 / 220 |
| Z_swirl | 0 / 72 | 124 / 36 | 198 / 292 | 304 / 304 |

(Y_stampede is left out: neither side captured gems before round 400; its gems come from the central heavy group.)

The first 100 rounds are often even (eight, corners, fragment, monolith). They pull away from round 100-200, when
their first damage emblems land and the first fights go their way.

### Camp-group kills (median rounds from the first hit to the kill)

| Group | Kills us / them | Rounds us / them |
|---|---|---|
| 1 wolf | 64 / 108 | 18 / 11 |
| 2 gold | 32 / 66 | 19 / 9 |
| 2 wolf | 32 / 51 | 21 / 14 |
| 1 elk + 1 gold | 29 / 51 | 24 / 15 |
| 1 elk | 17 / 29 | 24 / 11 |
| 1 gold + 1 wolf | 11 / 17 | 35 / 6 |
| 2 elk | 6 / 20 | 184 / 25 |
| 1 elk + 3 gold | 2 / 14 | 121 / 24 |
| 4 wolf | 6 / 9 | 78 / 25 |
| 1 elk + 2 gem + 1 wolf | 5 / 9 | 181 / 21 |
| 2 gem (harmless) | 10 / 0 | 22 / - |

Our multi-camp kills take 3-9x longer because the planner accepts groups that need several heal trips
(`max_trips = 5`): hit, go home, come back. Theirs die in one visit.

### Captures, recalls, banks

| | Us | Them |
|---|---|---|
| Gem captures | 202 (home 162, neutral 36, enemy 4) | 355 (home 264, neutral 61, enemy 30) |
| Rounds a respawned home group waits before the first hit | median 21, mean 35 (125 cycles) | median 14, mean 29 (204 cycles) |
| Split rewards (two of a team's bodies capture in the same round, not the pair) | 7 | 14 |
| Recalls | 383, median health 45%, 82% arrive | 476, median health 58%, 84% arrive |
| Recalls that overlap a capture (reward lands with the teleport) | 100 | 174 |
| Banks | 153, mean 49.6 gems | 263, mean 58.2 gems |
| Banks at neutral altars | 67 | 160 |

They make 63% more gem captures on **their own half** than we make on ours (264 vs 162). The halves are mirror
images, so this is pure farming speed: faster kills, so more respawn cycles, so more captures.

### One timeline: our Stellar on expanse (no fighting in this game)

| Rounds | What it did | Income |
|---|---|---|
| 1-42 | hit two wolves near spawn with spells, recalled, captured one (22 gems) | 22 gems |
| 42-54 | walked to the altar at (14,4) to bank those 22 gems (dedicated trip, `early_tribute_min = 22`) | - |
| 55-136 | walked ~40 tiles to the middle; cast on an elk at (25,15) twice in passing (never killed it), on two gold clusters (took them: 70 gold), then fought a 2-wolf pack at (41,5) alone for 36 rounds with 35-damage basic attacks, left at 330 health with one wolf alive, recalled | 70 gold |
| 136-215 | walked out again, cast on gold clusters in passing, back and forth between (29,26) and (41,13), finally killed one wolf at (17,34) and recalled with it | 22 gems |

Their Issac on the same map made 14 captures, 9 of them from three wolf camps next to its spawn ((74,57), (74,67),
(62,45)) and the rest from the two groups beside them.

### Unopposed, the big maps are slow

`legend` alone against `idle` (17 official maps, both sides) needs 579 rounds on average to reach 1,000 gems
(see 06). Five of those games decoded: on corners, elkring, expanse and monolith its camp damage per camp round is
89-104 with nobody in the way, still below the 118.5 the top teams reach in contested games. On ambush (100x100) it is
83 and the bodies walk 67-80% of the time (74% overall); the two ambush games average 708 rounds, and in the decoded
one (749 rounds) Ryth makes no gem capture at all.

---

## 5. Fights

152 fights with 4+ champion hits.

| | Us | Them |
|---|---|---|
| Damage dealt to champions in fights | 91k | 192k |
| Body deaths in fights | 133 | 46 |
| Bodies taking part (mean) | 2.43 | 1.95 |
| Fights where they hit first | 86 (our deaths 97, theirs 17) | |
| Fights where we hit first | 66 (our deaths 36, theirs 29) | |

By number of bodies taking part:

| | Fights | Deaths us / them | Damage us / them |
|---|---|---|---|
| They had more | 28 | 21 / 0 | 8.3k / 28.9k |
| Equal | 51 | 41 / 9 | 21.6k / 55.7k |
| **We had more** | 73 | **71 / 37** | 61.3k / 107.6k |

By game phase:

| Rounds | Fights | Deaths us / them | Damage ratio us : them |
|---|---|---|---|
| 0-100 | 23 | 16 / 10 | 0.64 |
| 100-200 | 31 | 24 / 14 | 0.60 |
| 200-350 | 51 | 43 / 12 | 0.39 |
| 350+ | 47 | 50 / 10 | 0.44 |

Before round 100 nobody has more than a few shards, so the 0.64 ratio is execution, not items. After round 200
the item gap makes it worse (0.39-0.44).

By side of the map: our half 57 fights (deaths 47 / 17), neutral 43 (54 / 16), their half 52 (32 / 13).

### Rounds hit without hitting back

For every round where a body takes champion damage, did it deal any champion damage that round?

| | Rounds hit | Hit nobody back | Share |
|---|---|---|---|
| Us | 1,331 | 985 | **74%** |
| Them | 766 | 422 | 55% |

What our bodies did in those 985 rounds: moved at above 50% health 446 (45%), moved below 50% 186 (19%), no action
(stunned, channel, waiting) 163 (17%), died that round 135 (14%), started a recall or bank 29 (3%). Theirs, of 422:
moved 108 + 69, no action 170, died 49.

Of the 633 rounds where our body moved while hit and dealt nothing (theirs: 177):

| Before the move | Moved away | Moved toward |
|---|---|---|
| an enemy was in its basic-attack range | 204 | 74 |
| an enemy was within 4 (spell range) | 102 | 151 |
| nothing in reach | 2 | 100 |

Every champion does it (Ren 130, Varg 111, Cassi 106, Stellar 104, Issac 103, Ryth 79). The causes in the code
(`combat()` and `engage()` in `brain.cpp`): the fight is re-decided from scratch every turn (fight / flee flips under
fire); the focus target is chosen without a distance term, so a champion walks toward it while another enemy is in
reach; fleeing melee champions step first and then cannot reach anyone to swing at.

Focus fire is **not** the problem: both teams put ~90% of each 3-round window's damage on one target (median 1.0).

### Death causes (death incidents, a Cassi & Issac double death counted once: 126 ours, 53 theirs)

| | Us | Them |
|---|---|---|
| Killed by an enemy melee champion | 52% | 49% |
| Killed by an enemy ranged champion | 39% | 30% |
| Killed by a camp | 9% | 21% |
| Victim above 60% health 4 rounds before (burst) | 40% | 40% |
| Victim below 35% health with an enemy near 4 rounds before (failed escape) | 25% | 28% |
| Enemy Varg splash hit the victim and an ally in one swing within the last 5 rounds | 14% | 6% |
| 60+ camp damage taken in the last 5 rounds | 18% | 30% |
| Bag lost at death (total gems) | 1,294 | 832 |

Who killed us (per incident): their Stellar 35, Varg 25, Issac 19, Ren 12, Cassi 12, camps 11, Ryth 10, Prism 1, Tavi 1.
Who killed them: our Stellar 15, Ren 13, camps 11, Ryth 5, Varg 4, Issac 4, Cassi 1.

### Four fights, round by round (`tools/strategy_v2/trace.py`)

- **swirl vs X, r7-22.** Their Varg wakes the elk + 3 gold group in the middle at r7. Our Ren walks in and stands
  next to the elk, which now hits *him* (the nearest champion) for 60 a round from r14, while their Varg and Cassi
  hit him too. Our Varg walks around the bushes ("movement blocked" twice: enemies hidden in bushes) and deals 0
  damage in 14 rounds; our Stellar casts on a gold cluster near our spawn. Ren dies r20, Cassi and Issac r22 to
  their Stellar. 3-0 in their favour before round 25.
- **elkring vs X, r73-83.** Their Varg (hitting for 100 at r73, so about 100 strength from early Power shards) fights
  our Ren, Ryth and Issac, who stand next to each other. Each Varg swing splashes all three for 100; with the reset that is 600
  damage a turn. Our three hit back for 30-36 each (no damage items). Ryth dies at 80 health still in melee; Varg
  leaves at 998 of 1,300.
- **eight vs Y, r30-49.** Our team stands inside the range of an awake 4-wolf pack (20-80 camp damage a round on us)
  while the enemy waits outside it. Our Varg walks alone into their group at (24,10) and is focused by Varg, Ren,
  Stellar and Cassi: dead in 2 turns.
- **collision vs X, r41-50.** Their Stellar's area spell hits our Cassi and Issac standing side by side (r41), their
  Cassi and Issac finish the work while our Ren dashes around without attacking until r46, and at r50 the area spell
  hits Ren and Issac side by side; Issac dies and takes Cassi with him.

---

## 6. Draft

| Team | Map (picks) | Draft |
|---|---|---|
| X | eight (5), elkring (5) | Varg, Ryth, C&I, Ren, Stellar |
| X | collision (3), packs (3) | C&I, Ren, Stellar |
| X | swirl (4) | C&I, Stellar, Varg, Ryth |
| Y | ambush, eight, corners (5) | Ren, Stellar, C&I, Ryth, Varg |
| Y | stampede (5) | Stellar, Tavi, Prism, C&I, Ren |
| Y | expanse (3) | C&I, Stellar, Varg |
| Z | elkring, monolith (5) | Varg, Stellar, C&I, Ryth, Tavi |
| Z | ambush (5) | Varg, Stellar, C&I, Tavi, Ren |
| Z | swirl (4) | Varg, Ryth, C&I, Stellar |
| Z | fragment (3) | Varg, Stellar, C&I |
| Us | all | Ren, Stellar, C&I, Varg, Ryth (first N picks) |

Cassi & Issac 15/15, Stellar 15/15, Varg 12/15 (first pick 7 times), Ryth 9/15, Ren 8/15, Tavi 4/15, Prism 1/15.
Each team changes its draft with the map. At 5 picks our set equals Y's set on ambush, eight and corners, and we
lost those 428-1024, 22-1130 and 320-1004: the draft is not what decided them.

---

## 7. Checked and ruled out

| Suspect | Finding |
|---|---|
| Fuel | median 12-35k of 100k a turn; at most 6 lost turns a game, all rounds 1-3 (Ren and Issac's first turns) |
| Focus fire | ~90% of each 3-round window's damage on one target, same as theirs |
| Wasted camp damage | gems per 1,000 camp damage 15.1 vs their 14.4 |
| Not enough recalls | 383 vs 476; we recall later (45% vs 58% health) but this is small next to the rest |
| Unspent gold | spent 94% of earned gold (37.5k of 39.9k) |
| Wards | we place 4.3x more (3,477 vs 806 across the 15 games); they win without them |
| Priority | team X sets priority 35-82 times a game, team Z 2,089-4,150 times; both beat us |
| Altar locks | top teams place none |

---

## 8. Map capacity

`map_plan.py` adds up, for each side, the gems per round its groups can give if each is taken
right when it respawns (kill time at about 150 damage a round). Rounds to 1,000 gems from the home side alone:
corners 168, expanse 214, lanes 200, rushbait-v2 262, monolith 266, collision 326, ambush 333, eight 339,
rows 364, elkring 469, interlock 510, packs 714, fragment 769, pilgrimage 1,176; contest, stampede and swirl have
no home gems (monoliths, the central heavy group, or a shared middle). Maps above ~450 cannot be won from home: the
neutral groups and the enemy's groups decide them. That is the basis of the map types in the strategy (Part D).
