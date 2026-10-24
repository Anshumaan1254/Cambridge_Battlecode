# an_weak: weaknesses and exploits of prism best girl, Intercontinental Fish, Claudus Maximus (+ Pantheon, coo, Nyx)

Session 17, Oct 23 2026, dimension "weaknesses and exploits". Data = the current bot versions (ranked games Oct 23 ~07:00-15:00 UTC)
and the ranked lists. **Everything is MEASURED unless tagged INFERRED.** S = the study team, O = its opponent in the same games.
pbg = prism best girl (#1), IFish = Intercontinental Fish (#2), cm = Claudus Maximus (#19), coo = conqueror_of_openai.

## 0. Data, method, caveats

| source | content |
|---|---|
| replays + fight dumps | pbg 116 games (71-45), IFish 110 (66-44), cm 106 (58-48), Pantheon 105 (52-53), coo 101 (55-46), Nyx 100 (49-51); `C:/battlecode/cache/t2/<key>/`, `C:/battlecode/cache/t2dump/<key>/` |
| ranked lists | `experiments/live/lists/t2_pbg_ranked.jsonl`, `t2_ifish_ranked.jsonl` (400 games each, Oct 23 01:30-14:40), `experiments/live/lists/wr/<id8>.jsonl` (150 newest) |
| purchases | `experiments/live/compact/<matchId>.json` (pbg 116/116, IFish 108/110, cm 106/106 of the sample; plus 660 older pbg games for the lock check) |
| map geometry | `C:/battlecode/cache/an_strategy/mapgeo2.jsonl` (walking distances, groups, altars, features) |
| intermediate outputs | `C:/battlecode/cache/an_weak/*.jsonl`, 30 narrations in `C:/battlecode/cache/an_weak/narr/` |

- Zones use walking distance: f = d_own / (d_own + d_enemy); own < 0.4, mid 0.4-0.6, enemy > 0.6.
- Tribute outcome per channel (tools/top2/weak/wx.mjs, tribhaz.mjs): **done**; **self** = the tributer itself issued Cancel channel or another
  action (move / attack / cast / recall); **stun**; **lock** = an enemy altar lock placed on that altar during the channel; **death**; open = game end.
- "Chase death" = killed by a champion after moving >= 3 walking tiles AWAY from its own spawn in the last 10 rounds while hitting a champion.
- Caveat: bots are deterministic. When the same (map, opponent, side) repeats, the game is bit-identical in 6 of 18 repeat groups (e.g. IFish
  vs procless on 00expanse at 12:40 and 14:40: both 1001-577 at r799). Duplicates are few (pbg 1, IFish 3, Pantheon 2, Nyx 1) and were kept.
- Caveat: wins and losses are confounded with strength: "X happens in losses" is not always "X causes losses". The exploit sections say which
  part is a measured mechanism (e.g. per-round cancel hazard) and which is inferred.

## 1. Where they lose (ranked lists)

| | pbg (400 games) | IFish (400) | cm (150, 10:00-15:00) |
|---|---|---|---|
| record | 251-149 (63%) | 244-156 (61%) | 79-71 (53%) |
| side a / side b | 140-70 (67%) / 111-79 (58%) | 129-61 (68%) / 115-95 (55%) | 42-28 (60%) / 37-43 (46%) |
| worst maps (W-L) | the_farm 2-8, concentrated_wealth 3-9, fracture 2-7, collision 2-6, split 1-4, elk_arena 3-6, broken_curve 2-4, lanes 3-5, lost_world 3-4 | boss_battle 2-13, fracture 3-14, packs 2-9, split 3-8, lost_world 5-10, elk_arena 3-6, collision 4-6, the_farm 5-7 | yellow_brick_road 0-5, fragment 1-5, gem_fields 1-4, boss_battle 2-4, hooks 0-3, monolith 1-3, rushbait_v2 1-3 |
| best maps | rows 15-0, road_of_riches 11-0, interlock 12-1, gem_fields 10-1, eight 14-2, monolith 7-1 | islands 12-0, expanse 11-0, contest 6-0, gemfight 5-0, monolith 12-1, elkring 8-1 | big_world 6-1, gold_rush 4-1, starvation 4-1, reverse_spiral 3-1 |
| who beats them | :3 27 of 65, IFish 27/65, Pantheon 24/55, procless 21/55, policy wonk 21/55 | pbg 38/65, :3 33/60, Pantheon 20/50, policy wonk 18/45, procless 17/55 | NTU 11/20, the ruliad 8/20, dromedaries 5/10, EMPEROR Tung 5/10, Nyx 4/5, NEETCoders 4/5, Zarzorki 4/5 |

**Draft size (= champions per team, fixed by the map, known at draft time):**

| team | 3 champions (broken_curve, collision, fragment, gold_rush, packs, the_farm) | 4 champions (8 maps) | 5 champions (26 maps) |
|---|---|---|---|
| pbg | **25-34 (42%)** | 65-19 (77%) | 161-96 (63%) |
| IFish | **24-31 (44%)** | 53-20 (73%) | 167-105 (61%) |
| Pantheon (150) | 9-13 (41%) | 21-11 (66%) | 48-48 (50%) |
| cm / coo / Nyx (150 each) | 52% / 60% / 50% | 52% / 44% / 39% | 53% / 62% / 57% |

**Map features vs per-map win rate (Spearman over ~40 maps, tools/top2/weak/mapcorr.py):** IFish: wall share -0.43, golems -0.31,
monoliths -0.26, total gems -0.24, bushes -0.23; mincut (corridor width) +0.37, holes +0.28, area +0.21 -> IFish's blob is weakest on walled,
chokepoint maps with heavy camps. cm (29 maps): spawn-to-spawn walk +0.55, monoliths +0.36, mincut -0.35 -> cm is weakest on short maps.
pbg: no feature above |0.27| (bushes -0.27, groups -0.27).

## 2. Loss anatomy (replay sample, mean per game, study team / opponent)

| metric | pbg W (71) | pbg L (45) | IFish W (66) | IFish L (44) | cm W (58) | cm L (48) |
|---|---|---|---|---|---|---|
| banked r200 | 47 / 50 | 41 / 66 | 82 / 42 | 57 / 59 | 60 / 36 | 49 / 51 |
| banked r400 | 143 / 142 | 120 / 188 | 238 / 111 | 184 / 181 | 180 / 99 | 141 / 166 |
| banked r600 | 324 / 242 | 209 / 362 | 441 / 210 | 295 / 348 | 357 / 183 | 234 / 326 |
| captured gems by r200 | 119 / 92 | 88 / 105 | 119 / 89 | 96 / 119 | 89 / 73 | 73 / 89 |
| captured gems in the mid zone (game) | 698 / 245 | 382 / 594 | 615 / 213 | 459 / 675 | 637 / 274 | 244 / 583 |
| max-HP sum r600 (items) | 9880 / 7681 | 9582 / 9240 | 8596 / 8316 | 8033 / 8764 | 8755 / 7551 | 7547 / 10469 |
| deaths (game) | 4.9 / 13.9 | **11.2 / 5.9** | 7.8 / 12.2 | **18.8 / 8.9** | 6.7 / 14.9 | **20.0 / 6.6** |
| deaths r200-600 | 1.5 / 4.0 | 3.3 / 1.9 | 2.8 / 4.3 | 4.5 / 2.6 | 2.1 / 4.5 | 5.8 / 2.0 |
| gems lost in bags on death | 106 / 171 | 135 / 66 | 44 / 109 | **317** / 253 | 97 / 139 | 103 / 56 |
| tribute starts | 20.7 / 17.2 | 12.7 / 30.0 | 27.2 / 13.2 | 17.1 / 24.4 | 29.9 / 14.6 | 21.7 / 33.6 |
| biggest tributed bag | 414 / 94 | 180 / 209 | 149 / 100 | 223 / 353 | 140 / 78 | 79 / 132 |
| gems carried unbanked at the end | 94 / 54 | **210** / 80 | 47 / 76 | 131 / 108 | 59 / 51 | 33 / 45 |
| altar locks placed | **0.0** / 2.1 | **0.0** / 2.2 | 2.6 / 1.1 | 3.2 / 1.6 | 5.9 / 3.3 | 5.1 / 3.9 |
| largest cluster r20-150 | 3.0 / 2.6 | 2.9 / 2.7 | 3.9 / 2.6 | 3.3 / 2.6 | 2.5 / 2.7 | 2.5 / 2.7 |
| deaths to camps | 1.24 | 1.22 | 1.77 | **2.82** | 1.14 | 1.06 |
| deaths in the enemy zone | 0.66 | 0.82 | 1.03 | 0.89 | 1.05 | **3.25** |
| chase deaths | 0.68 | 2.04 | 0.95 | 2.82 | 0.91 | **4.00** |

**Loss types** (tools: wx.mjs + bagep.mjs; snowball = S deaths >= 10 and >= 2x O deaths; "bag race" = a >= 200-gem episode never banked):

| | race lost holding a >= 200 bag | fight snowball | pure race (deaths <= theirs + 2) | mixed |
|---|---|---|---|---|
| pbg (45 L) | **18** | 13 | 10 | 4 |
| IFish (44 L) | 6 | 17 | 15 | 6 |
| cm (48 L) | 1 | **25** | 10 | 12 |

First champion kill (MEASURED): IFish win 43% when they suffer it (n 42; median r152; victim Cassi 17 of 42) vs 70% otherwise (n 61);
pbg 48% (n 46) vs 70% (n 67); cm 44% (n 59; 18 of their first victims die in the ENEMY zone) vs 68% (n 44).

How the winners beat them (losses of S grouped by opponent, replay sample):
- vs pbg: **Pantheon** (10 of 21) banks 34 times vs pbg 9, pbg deaths 14.1 vs 4.2, mid gems 745 vs 337, 2.9 locks/game; **procless** (7 of 19)
  banks 34 vs 16 with about the same deaths (pbg 4.7, procless 5.7) and no locks: a pure banking race; **:3** (4 of 15): pbg 33 deaths/game (fight crush).
- vs IFish: **pbg** (11 of 20) by fights (IFish 33.2 deaths vs 11.5, mid gems 903 vs 371); procless / Univardisty by banking (28-30 banks vs 16).
- vs cm: everyone by fights: cm deaths 8-37/game in its losses vs 1.3-13 for the winners; winners bank 26-38 times.

## 3. Narrated losses (tools/live/narrate.mjs; full texts in C:/battlecode/cache/an_weak/narr/)

pbg:
1. `01starfish_24e6f58d` (b vs procless, 579-1075 r1510): Prism holds 100+ gems from r429 to the end (765 at r1300), first tribute try only at r1187;
   15 starts at altar (26,17) r1187-1467: 13 self-cancels (12 with an enemy within 8), 1 stun (Ryth r1246); the altar is in camp range (up to
   2,736 camp damage per try); ended with **765 unbanked**.
2. `00quadrants_24ebc1cc` (b vs procless, 446-1008 r598): even farm (b400 385 vs 587), 1 death; ends with **683 gems carried** (Prism 578).
3. `00great_wall_3a46ed8d` (b vs IFish, 699-1013): IFish's HoR **locks** pbg's altar at r904 (368-gem tribute) and r1077 (623); the Prism dies to a
   camp at r1104 with 623.
4. `00monolith_e2542db9` (a vs :3, 597-1013): pbg banks 20x (597), Prism dies r1038 with **576** to :3's Marcella, :3 banks it and wins.
5. `01the_farm_7f9cccb2` (b vs Pantheon, 345-1025; 3 champions): pbg banked 45 by r600 vs 283, 7 banks vs 14; Prism carries 389 at the end.
6. `00collision_1189ede2` (a vs procless, 516-1004; 3 champions): pbg 5 banks vs 46; b500 105 vs 305.
7. `00lost_world_3209a6ec` (a vs Pantheon, 0-1008 r509): 8 deaths before r200 (first kill r26), no capture until r174; mirror draft lost.
8. `01elk_arena_26396b1e` (a vs :3, 144-1008): 63 deaths vs 11; max HP r1100 10,900 vs 21,800: fight snowball on a 1-group contest map.
9. `01hooks_2eb199ff` (a vs :3, 110-1034): 42 deaths, 32 of them to :3's Vesper; pbg captured 7 elk vs 52.
10. `01concentrated_wealth_83e86a76` (b vs IFish, 287-1007): 21 deaths; mid gems 162 vs 762; 9 banks vs 36.

IFish:
1. `00lost_world_6cf3877c` (b vs procless, 477-1003): **8 bodies killed by camps r103-180** (Cassi+Issac by the golem r103, then Ryth, HoR, Vesper,
   Vendetta, Cassi+Issac by the monolith r124-180), 4 more to the monolith at r439-452; capture count 0 in r100-200 while procless took 11.
2. `00swirl_5cd065e4` (b vs Pantheon, 676-1066): IFish led 661-351 at r1100; **Vesper dies at r1100 with 700 gems** to Pantheon's Prism, Pantheon banks
   it and wins at r1176.
3. `01boss_battle_4b1716d2` (b vs pbg, 151-1021): Vesper dies with **1,481** (r1081) and with **1,902** (r1508); 39 deaths.
4. `01fracture_066b8204` (b vs Univardisty, 439-1040): IFish farms mostly its own half, 7 deaths to camps (Ryth x4, Cassi+Issac, Vendetta), Vesper dies
   r1214 with 200; 10 banks vs 45.
5. `00split_ae45497f` (a vs procless, 691-1011 r717): no fight until r631; IFish took golems (5) but lost the mid (116 vs 356) and the race.
6. `00packs_3600bc34` (b vs :3, 806-1024; 3 champions): IFish 4 deaths vs 8; :3 mid gems 1004 vs 546, 33 banks vs 24.
7. `01starfish_47358525` (a vs pbg, 202-1143): first blood r50 = Cassi+Issac (both) to Marcella; 40 deaths.
8. `01elk_arena_1dc1db3b` (a vs pbg, 504-1008 r1947): 88 deaths; first kill r31, first capture only r317.
9. `01hooks_7483792a` (a vs pbg, 165-1001): first kill r37, 49 deaths.
10. `00road_of_riches_77554456` (a vs pbg, 136-1238 r710): 26 deaths vs 3; pbg's 508-gem tribute ends the game (731 -> 1238 at r710).

cm:
1. `00fragment_28f9bafa` (b vs Zarzorki, 44-1020): 38 deaths vs 0; cm never captures a mid group; max HP 4,700 vs 31,500 at the end.
2. `01hooks_f3e1f596` (b vs NTU, 22-1034): 40 deaths vs 3, max HP 4,900 vs 32,900.
3. `00contest_dfb51b35` (a vs hello, 0-1000): 49 deaths; hello's single 200-gem monolith capture at r545 and 4 more win it.
4. `00gem_fields_0a0f0a07` (b vs Nyx, 234-1022): HoR r37 and Tavi r49 die in the ENEMY zone to Nyx's Prism; 23 deaths vs 1.
5. `01yellow_brick_road_e8544c26` (b vs Nyx, 349-1056): 28 deaths vs 3 (HoR dies r35 in the enemy zone).
6. `00monolith_9f33f38f` (b vs dromedaries, 566-1058): dromedaries capture monolith groups 12 times, cm never (mid gems 824 vs 8).
7. `01elk_arena_7b33dffa` (a vs NTU, 0-1008): cm got the first kill (r19) but never captured the elk; 37 deaths.
8. `00rushbait_v2_bf3b19f0` (b vs EMPEROR Tung, 486-1017): first kill r20 by them, 13 deaths vs 1.
9. `00lost_world_f242740a` (a vs subscribe, 105-1006 r608): 7 deaths before r200; them 60 banks.
10. `01starfish_2b0b9811` (a vs Tartarus, 96-1099): 38 deaths vs 8, first kill r33 by them.

## 4. Weaknesses and exploits

### E1. pbg's gem-hoarding Prism and the tribute that dies when an enemy is in sight (pbg = the #1 team)

MEASURED:
- pbg's Prism gets +1.5 Focus per carried gem (INFERRED: that is why it keeps the bag); its spell damage per cast by bag size (stun spell slot 0,
  median / p90): bag 0-49 **140**/207, 50-149 348/473, 150-299 610/792, **300-599 1136/1424**, 600+ 1600/2154; area spell median 108 -> 1340.
- Big-bag episodes (a body's bag passes 100 and peaks at >= 200; the episode ends when it drops below 50): pbg 107 in 72 of 116 games (Prism 59,
  Vesper 20, Marcella 19); peak mean 439; the bag is held **391 rounds** on average (median 293); the first tribute attempt comes 308 rounds
  after the bag passed 100 (21 episodes never try). The Prism carries >= 200 gems for 22,031 body-rounds
  (190 per game); in 44% of them no ally is within 4, its HP is below 50% in only 1%.
- 72% of pbg's tributes with >= 200 gems are at **mid-zone altars** (137 of 190; own 34, enemy 19): reachable.
- Outcome of those episodes: in **wins 66 of 78 are banked**; in **losses only 4 of 29** (17 still carried at game end, 8 died).
  pbg's most common loss type is "race lost while holding a >= 200 bag" (18 of 45 losses); at the end of a loss pbg carries 210 gems (wins 94).
- The channel is long (ceil(bag/10): mean 90 turns for 400+ bags) and **pbg cancels it itself when an enemy is in sight**: per channel round
  (bag >= 100) the self-cancel hazard is 6.8% with the nearest enemy at 4-5 tiles, **5.0% at 6-8**, 2.5% at <= 3, **0.2% at 9+** (n 354 / 1292 /
  200 / 3525 rounds). It is not damage-driven (1.0% in rounds with champion damage, 7.8% with camp damage). 93 of 100 self-cancels of a
  >= 200 bag had an enemy within 8 (68 within 6); only 39 of 100 hit a champion in the next 3 rounds (most cancels are not counter-attacks).
- Long channels (need >= 20 turns): **with an enemy within 8 at some point 45 of 161 complete (28%)** (self 99, lock 6, stun 5, death 3);
  **without, 27 of 31 (87%)**. Same pattern in IFish (23/86 = 27% vs 14/19), Nyx (29/119 = 24% vs 13/15), Pantheon (22/58 vs 25/29).
  cm never self-cancels (0.0% hazard; 24 of 34 long channels complete with enemies near).
- pbg **never buys or places altar locks**: 0 locks in 116 dumps, 0 Altar Lock purchases in 660 compact games (Oct 22: 355, Oct 23: 305).
  Their opponents placed 251 locks (66 games) cancelling 15 pbg tributes (4,682 gems); after an enemy lock on a 100+ bag pbg banked it only
  3 of 7 times, after +25 to +94 rounds (`00great_wall_3a46ed8d` r904/r1077, `00quadrants_cc168b7a` r450: 841 gems, banked r545).
- pbg's wins come late and in one piece: the final tribute is >= 200 gems in **62% of wins (44 of 71; median 239)** and **42% of their final score
  lands in the last 100 rounds** (>= 50% in 25 wins); IFish 14% / 21%, cm 17% / 20%. Example: `00gem_fields_3fc2330b` pbg 452 at r600 ->
  1313 at r681 (Marcella 747-gem tribute r606-681, no enemy within 5); `00road_of_riches_77554456` 731 -> 1238 at r710.
- pbg's conversion is slow: banked / captured gems at r600 = 0.60-0.62 (IFish 0.74-0.85, cm 0.76-0.80).

INFERRED mechanism: pbg's bot treats a visible enemy near a long channel as a threat and aborts; with a 70-turn channel any passer-by resets it.
The banked score under-states pbg's real gems by the Prism's bag (often 300-700).

Exploit / trigger (runtime-observable: `is_submitting_gems()`, `gem_count()` of visible enemies, altar positions, `global_submitted_gems()`):
see Rules R1-R3.

### E2. The banking race beats pbg; pbg's banked score lags

MEASURED: in pbg losses the opponents start 30.0 tributes/game vs pbg 12.7 (wins: 17.2 vs 20.7); procless beat pbg 7 times in the sample with
34 banks/game vs 16, no locks and about the same deaths (pbg 4.7, procless 5.7); on 3-champion maps opponents bank 25.3 times vs pbg 13.4 (pbg 8-10 there).
INFERRED: a steady small-bag banker that does not feed beats pbg's hoarding in a race unless the Prism converts; god2 cannot out-fight pbg,
so this is the realistic route (Rules R3, R7).

### E3. Bag carriers: kill them with superiority, never feed them

MEASURED:
- IFish big-bag episodes: in losses 10 of 19 end in the carrier's death (wins 2 of 40); IFish loses 317 gems/game in bags in losses (44 in wins).
  `00swirl_5cd065e4` r1100 Vesper 700 -> Pantheon wins from 661-351 down; `01boss_battle_4b1716d2` Vesper 1,481 (r1081) and 1,902 (r1508).
- pbg big-bag deaths: 15 episodes (11 to champions), 7,176 gems; e.g. `00monolith_e2542db9` r1038 Prism 576 -> :3 wins 1013-597;
  `00gem_fields_3fc2330b` r517 Prism 704 killed by Pantheon's Vesper at altar (32,10) mid-tribute (34 of 71 turns, 2,586 damage taken; pbg still won).
- The killer's team banks the bag: Pantheon's Vesper started a 711-gem tribute one round later (r518) and was stunned 41 turns in by pbg's Marcella.
- A big-bag pbg Prism is a nuke (E1 damage table): one stun spell at 300-599 gems = 1136 median, more than a base Vesper (1000 HP).
INFERRED: the bag is the biggest single swing in these games, but only a burst that kills before the Prism's next cast is safe.

### E4. They recall next to enemies and nobody punishes it

MEASURED (recall starts away from spawn; recall-spam rounds removed; tools/top2/weak/recallpun.mjs):

| team | nearest enemy <= 3 | 4-5 tiles | damaged within 5 r -> home / dead | undamaged -> home |
|---|---|---|---|---|
| pbg | 2.2/game | **7.2/game** | <=3: 27% damaged -> 10% / 49%; 4-5: 16% -> 11% / 26% | 75% / 80% |
| IFish | 2.5/game | **8.5/game** | <=3: 30% -> 11% / 40%; 4-5: **15%** -> 14% / **45%** | 74% / 80% |
| cm | 2.7/game | 3.7/game | <=3: 61% -> 9% / 59%; 4-5: 24% -> 11% / 35% | 91% / 86% |

The recaller's HP share averages 0.49-0.51 (all recalls). Examples: `ifish 00lost_world_6cf3877c` Issac at 18% HP recalls 3 tiles from an enemy at r665
and r667 and gets home untouched; `ifish 01fracture_066b8204` HoR at 13% HP at r537 (5 tiles).
INFERRED: any damage cancels the 5-turn recall (rules), so a body in reach converts a 15% punish rate into kills.

### E5. Cassi & Issac: one kill = two bodies (IFish drafts C&I in ~85% of its games)

MEASURED: 347 C&I pair deaths in IFish's 110 games (334 of them IFish's own pair: 2.4/game in wins, 4.0 in losses). The killing blow lands on Cassi 146 times, on Issac 135
(camps 66): the pair is a median **7 tiles apart** at death (>= 4 tiles in 70%) and the partner still has **78% HP** on average (> 50% in 79%).
IFish's first champion death is Cassi+Issac in 17 of the 42 games where IFish loses a body first (IFish wins 43% of those). Example:
`01starfish_47358525` r50 first blood = both bodies to pbg's Marcella.
INFERRED: whichever of the pair is isolated is a 2-for-1 target (Cassi has the lowest base HP in the game, 700).

### E6. 3-champion maps are where #1 and #2 are beatable

MEASURED: pbg 42%, IFish 44%, Pantheon 41% on the six 3-champion maps vs 61-77% elsewhere (section 1). In the replays (pbg 8-10, IFish 6-10)
they are farming races: deaths pbg 3.2 vs opponents 6.6, IFish 5.6 vs 6.2; the opponents capture more in their own zone (pbg games 459 vs 386 gems,
IFish games 427 vs 339) and bank more often (pbg games 25.3 vs 13.4). IFish's blob shrinks to 2.1 (5-champion maps 4.05).
INFERRED: the blob / Prism-nuke advantages need bodies; with 3 bodies each, spread farming and banking cadence decide.

### E7. cm over-extends and feeds; most of its losses are fight snowballs

MEASURED: cm spends 6-7% of its alive body-rounds in the enemy zone (pbg 2-5%, IFish 2-5%); in losses it dies there 1.38 times per 100 body-rounds
(0.26 in wins), 3.25 enemy-zone deaths/game; chase deaths 4.0/game in losses (0.91 in wins), 106 of 192 of them outnumbered (en6 > al6 + 1), 62 in the
enemy zone. In the 59 games where cm suffered the first champion kill, that victim died in the enemy zone 18 times (median r104). 25 of 48 losses are snowballs; over all 48 losses cm dies 20.0 times/game and trails in max HP at r600
(7,547 vs 10,469). cm wins more on long maps (spawn-to-spawn walk rho +0.55).
INFERRED: cm's bodies follow fights into the opponent's half alone; a home-side collapse wins those fights.

### E8. IFish dies to monoliths and camps

MEASURED: IFish deaths to camps 1.77/game in wins, **2.82 in losses** (pbg 1.2, cm 1.1); monolith kills 53 in 44 losses (1.2/game) vs 24 in 66 wins;
77 monolith deaths in total, 40 of them while the victim hit no camp in its last 10 rounds (walking / fighting inside the awake monolith's range 5);
maps: lost_world 21 (losses), corridors 16 (losses), boss_battle 7. `00lost_world_6cf3877c` r103-180: 8 bodies to the monolith/camps.
IFish's per-map win rate falls with walls (rho -0.43), golems (-0.31) and monoliths (-0.26).
INFERRED: the blob paths and fights through awake heavy camps (monolith str 200, range 5, attacks the NEAREST champion once hit).

### E9. Deterministic openings and the first fight

MEASURED (tools/top2/weak/routes.mjs + routeagg.py; pairs of games on the same map + side + draft against DIFFERENT opponents):

| | pairs | same tile at r20 / r30 / r60 / r100 | same first camp hit | same first ward tile | same first capture tile |
|---|---|---|---|---|---|
| pbg | 44 | 83% / 63% / 37% / 18% | 185/203 (91%) | 140/199 (70%) | 29/43 |
| IFish | 40 | 87% / 80% / 61% / 40% | 201/216 (93%) | 168/214 (79%) | 36/40 |
| cm | 29 | 66% / 52% / 43% / 32% | 109/127 (86%) | **127/127** | 22/28 |

First camp hit at median r14 (pbg), r16 (IFish), r18 (cm); it is one of the two nearest groups by walking distance for 54% (pbg) / 56% (IFish) /
34% (cm) of bodies, an elk group for 55% / 60% / 51%, in their own zone for 68% / 68% / 50%. 4-6 bodies share the first group in 57 of 116 pbg games,
5-6 bodies in 55 of 110 IFish games. Example: `pbg 00ambush_142ed602` (vs Zarzorki) and `00ambush_3b6468e6` (vs procless): every pbg body on the
same tile at r40, first elk hit r48 at (31,44), first capture r65 by Marcella (37 gems) in both.
First blood (section 2): they win 43-48% after suffering the first champion kill, 68-70% otherwise.

### E10. Who locks: pbg and Nyx never; IFish, cm, Pantheon a lot

MEASURED: locks placed per game: pbg 0.0 (0 in 116), Nyx 0.03 (3 in 100), coo 1.1, IFish 2.9, Pantheon 4.2, cm 5.6 (in 105 of 106 games; 983
purchases). Lock cancels of the study team's tributes: by cm's opponents 54 (3,100 gems), by pbg's opponents 15 (4,682 gems).
INFERRED: against pbg / Nyx a long tribute can only be stopped by stun, death or the tributer's own cancel; against IFish / cm / Pantheon a long
tribute near their bodies risks a 10-gold lock.

### E11. Hypotheses that did NOT hold (or are weak)

- "The early blob leaves the map undefended": opponents capture ~7 groups with no study body within 10 before r300 in both wins and losses
  (IFish 7.4 vs 7.2, pbg 7.1 vs 8.7, cm 4.6 vs 7.1); the extra uncontested gems in IFish losses are only +29 by r300 (130 vs 101). Not an exploit.
- "IFish depends on one carry (Vesper)": any dead core champion halves IFish's capture rate (Vesper dead 94 -> 40 gems/100 rounds, HoR 94 -> 37,
  Vendetta 93 -> 44) and quadruples its death rate; same for pbg and cm. The one Vesper-specific number: opponents capture 101 gems/100 r while
  IFish's Vesper is dead vs 72 alive (HoR dead 85, Vendetta dead 77). An early death (< r200) costs 10-40 win points for most champions and the Vesper is not special (IFish Vesper 44% vs 63%, HoR 38% vs 67%,
  Vendetta 39% vs 64%; pbg Prism 45% vs 65%, pbg Vesper 64% vs 61%; cm HoR 26% vs 68%).
- "They do not adapt when behind": all of them die 2-4.6x more per round when their max-HP share is < 0.43 (pbg 0.93 vs 0.20 per 100 body-rounds
  in losses) — but so does everyone (their opponents 0.45 vs 0.22). Not specific.
- Long stand-stills: pbg has a capture deadlock on 01yellow_brick_road (Vesper 1,288 rounds on (34,12) in `01yellow_brick_road_75c19376`,
  repeated 207+163 rounds in `eee626ba`, Vendetta 234 in `9888cae3`) and a 560-round stuck Marcella in `01fracture_35246d93`; IFish 5 runs, cm 13.
  Real but map-specific; nothing to do at runtime except not assuming 5 active enemies.

## 5. Pantheon, coo, Nyx (brief)

| | Pantheon W / L | coo W / L | Nyx W / L |
|---|---|---|---|
| banked r400 (S/O) | 212/113 / 122/159 | 188/127 / 91/182 | 163/97 / 93/158 |
| deaths (S/O) | 4.7/14.2 / 7.9/6.3 | 8.2/10.5 / 19.5/5.1 | 4.7/13.7 / 11.5/6.0 |
| mid-zone gems (S/O) | 607/281 / 280/569 | 575/246 / 279/572 | 608/219 / 273/594 |
| locks placed | 4.0 / 4.4 | 1.2 / 1.0 | 0.0 / 0.0 |
| long tributes with an enemy within 8: completed | 22/58 | 16/31 | 29/119 |

Pantheon loses races, not fights (7.9 deaths in losses), is weak on side b (17-27) and on 3-champion maps (41%), and spams Recall + Cancel channel
every turn (2,425 Recall events in `pbg 00gem_fields_3fc2330b`, mostly Pantheon's): only a body seen twice on the same tile is really channelling. coo loses by feeding (19.5 deaths)
like cm. Nyx never locks and self-cancels long tributes like pbg (24% complete with an enemy near).

## 6. Rules for god2

All triggers use runtime state only: visible enemy `gem_count()`, `is_submitting_gems()`, `is_recalling()`, champion type, max HP, position;
altar and camp positions from the map; `global_submitted_gems(team)`; the draft size. No map or team tables.

**R1. Tribute denial (top priority vs pbg, also vs IFish / Nyx / Pantheon).**
Trigger: a visible enemy with `is_submitting_gems()` and `gem_count() >= 60` (a channel of >= 6 turns), or a visible enemy with `gem_count() >= 150`
standing within 1 of an altar. Remaining turns T = ceil(bag/10) - turns seen channelling.
Action, first that applies:
1. A body holding an altar lock that can reach Chebyshev <= 2 of that altar within T - 1 turns: walk there and place the lock (cancels the channel;
   the tributer must hit the lock 5 times and restart the full channel). Lock the altar even when the bag is small if the tributer is pbg-like
   (bag >= 200 seen this game).
2. A stunner (Prism slot 0, Ryth, Tavi, Cassi, Ren, HoR dash, Marcella's empowered hit) that reaches cast range within T - 1 turns and whose local
   fight is not losing (our max-HP sum within 6 >= 0.9x theirs): stun the tributer. Note Marcella is stun-immune.
3. Otherwise **shadow**: send the nearest healthy body (HP >= 60%) to a tile at Chebyshev distance 6-8 from the tributer, visible to it, and hold
   there while the channel runs (measured self-cancel hazard ~5% per round at 6-8 vs 0.2% at 9+; long channels complete 28% with an enemy within
   8 vs 87% without). Do not step to <= 5 of a tributer whose `gem_count() >= 150` unless rule R4 says the kill is on.
Value: bag gems denied >> one body's farming for 15-20 rounds (~15-20 gems). Cancel the shadow when the channel ends or T > 60 and nothing changed.

**R2. Always carry an altar lock** (10 gold) on the 1-2 bodies that path through the middle most; re-buy at every shop visit; place it on the
enemy's nearest mid altar when an enemy carrier with `gem_count() >= 100` walks toward it (pbg tributes 72% of its >= 200 bags at mid altars).

**R3. Score accounting / end-game guard.** Track enemy_owned = `global_submitted_gems(enemy)` + sum of the last seen `gem_count()` of each living
enemy (drop on death, decay by 1/3 after 100 rounds unseen). When enemy_owned >= 700 or any enemy bag >= 250: switch the nearest two bodies to
"altar watch" (R1 shadow/lock on every altar within reach of that carrier) — pbg banks >= 200 in one tribute in 62% of its wins and 42% of its
final score in the last 100 rounds. Never treat a scoreboard lead of < (largest seen enemy bag) as safe.

**R4. Carrier kills.** Target value of a visible enemy = base value + its `gem_count()` (stolen on kill) + 100 (kill gold). Commit on a carrier with
`gem_count() >= 150` only when our bodies within 6 can deal >= its current HP within 2 turns AND (for a Prism) none of ours is inside its cast
range 4 at the start (its stun spell does ~1,140 at 300-599 gems). Our own bags: bank at >= 60-100 gems when an altar is within 10 and no enemy
within 8; never carry > 150 into a fight (IFish lost 10 of 19 big bags in its losses).

**R5. Punish recalls.** Trigger: a visible enemy `is_recalling()` (count it only on the 2nd consecutive sighting on the same tile: Pantheon-style
recall spam) within our reach this or next turn (melee <= 2, ranged basic <= 3, a damage spell <= 4, HoR dash <= 3). Action: hit it now (any damage
cancels the recall); keep focusing if its HP share < 0.5 and our local max-HP sum >= its team's within 6. Expected: they recall 6-11 times a game
with an enemy within 5; punished recalls end in death 26-59% of the time, unpunished ones get home 75-91%.

**R6. Cassi & Issac.** Count a kill on either as two bodies: target value x2 and +1 priority over equal-HP targets; prefer the member with no ally
within 3 (the pair is usually ~7 tiles apart, partner at ~78% HP). In the opening, a lone Cassi (700 base HP) in reach is the best first-blood target.

**R7. Draft size 3 -> race mode.** When each team has 3 champions: no voluntary fights except R1/R5/R6 opportunities, spread to own-half and mid
groups, bank at >= 40-60 gems (aim for 25+ banks/game), keep all three alive. (pbg 42%, IFish 44%, Pantheon 41% on those maps; winners there out-farm
their own zone and bank about twice as often.)

**R8. Home-zone collapse (vs over-extenders such as cm / coo).** Trigger: an enemy body inside our own zone (f_own < 0.4) with no ally of its own within 6
and our max-HP sum within 8 of it >= 1.2x its HP-max. Action: up to 2 nearest bodies engage; do not follow it past the midline (f > 0.5); return to
farming after 10 rounds or the kill. (cm: 55% of its chase deaths are outnumbered; 3.25 enemy-zone deaths/game in its losses.)

**R9. Monolith-aware fighting (vs blob teams, IFish).** Never fight inside Chebyshev 5 of a monolith (or golem 4) that is awake or that anyone hit in
the last 2 rounds unless every enemy in that radius is nearer to it than our nearest body (it attacks the NEAREST champion). When an enemy blob
stands nearer a sleeping monolith than any of ours, one hit from range 4-5 (wake it) is worth considering. (INFERRED; IFish 77 monolith deaths in 110
games, 40 not even hitting it.)

**R10. Opening.** Their first 20-40 rounds are fixed: 4-6 bodies on one of the two nearest groups to their spawn (an elk group in ~60%) at r14-18.
Rule: in r1-60 never contest the group that is nearest (walking distance) to the enemy spawn and holds an elk (run our own group scoring from the
enemy spawn to find it); take ours; first blood matters (43-48% vs 68-70% win for them), so take the first fight only with the R6 target or a
2-vs-1 near our side.

**R11. Lock safety by opponent behaviour.** Count enemy altar locks seen this game. If 0 locks after r400 (pbg, Nyx): our tributes of up to ~150 gems
are safe from locks; only keep stunners away. If the enemy has locked (IFish, cm, Pantheon): tribute only with no enemy within 8 of the altar, keep bags
<= 80 near their bodies, and clear an enemy lock with 5 basic attacks only when no enemy is within 8.

## 7. Open questions

- Is pbg's self-cancel a reaction to sight (vision 8) or to a threat model (it cancels 4-7% per round regardless of approach direction)? A local
  replay of the shadow rule against a pbg-like persona would tell whether a single shadow body is enough or it attacks the shadow.
- Do pbg / IFish react to an altar lock by moving to another altar (the bag then needs a full walk) or by clearing it? 7 pbg cases are too few.
- The 3-champion-map weakness: is it the bots or just higher variance on small maps (6 maps, ~59 games per team)?
- Monolith baiting (R9) is not observed being done deliberately by any team: test before trusting.
- Ranked samples cover one day of each team's versions; pbg had no lock purchases on Oct 22 either (355 games), which suggests a design choice.

## 8. Reproduce (scripts in tools/top2/weak/)

`wl_lists.py`, `wl_big.py` (records), `mapcorr.py` (map features), `wx.mjs` + `wagg.py` (anatomy, tributes, locks, deaths, raids, idle, per map),
`bagep.mjs` + `bagagg.py` (bag episodes), `tribhaz.mjs` + `hazagg.py` (cancel hazard), `tribtrace.mjs` (one game's big tributes), `endbags.py`,
`wx3.mjs` + `wx3agg.py` (camp deaths, HP-state deaths), `recallpun.mjs` + `recallagg.py`, `cikill.mjs`, `carryrate.py`, `zonerisk.mjs`,
`routes.mjs` + `routeagg.py` + `firsttarget.py` (openings), `blobfree.py`, `narr_batch.sh` (narrations). Run node scripts through
`python tools/live/par.py 3 OUT.jsonl SCRIPT -- FILES` (one output file per team: games against each other appear in two folders).
