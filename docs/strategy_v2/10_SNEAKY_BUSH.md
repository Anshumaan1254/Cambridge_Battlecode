# 10. The "sneaky bush camper" ladder team (18 Oct 2026)

Input: the user's `sneaky_bush_vs_us.zip` (20 match archives, **17 distinct games**, one per official map; rows, pilgrimage and
rushbait-v2 each appear twice), now `experiments/sneaky_oct18/<map>.repl26a`. Us = team 0 = side A (`legend_m8` / `m10`);
them = team 1. Tables of the first pass are in `experiments/sneaky_oct18/analysis/` (`run_all.py`); everything about bushes below
comes from the new `tools/strategy_v2/bush.py` (decoded with `decode_dmg.mjs`, map dumps with `mapinfo.mjs`; section 8 has the commands).
Nothing here was run as a game: it is replay analysis only, and no bot was changed.

## 0. Summary

| # | Finding | Number |
|---|---|---|
| 1 | They hide far more than we do, but mostly on four maps | alive body-rounds in a bush: **7.9% vs 3.3%** (contest 21.7% vs 3.5%, eight 10.5% vs 1.9%, stampede 12.5% vs 6.4%, fragment 13.2% vs 11.3%); without contest 4.8% vs 3.3%; in our 5 wins their share is 2.6% (ours 2.8%) |
| 2 | A quarter of their champion damage is dealt from inside a bush, and little comes back | 23.5% of 266k vs 9.0% of 122k (without contest 15.3% vs 7.8%); after an attack turn from a bush they take back **43** damage in the next 3 rounds (65 without contest) against 111 (128) after one from the open |
| 3 | Bush killers are a large share of our deaths, a small share of theirs | killer standing in a bush at the final blow: **34 of 113** champion-caused incidents (30%; 16 of 62 = 26% without contest) vs **4 of 59** (7%) of theirs; a bush attacker among the hitters of the last 5 rounds: 48% (40%) vs 10% |
| 4 | Their wards are a bush tool; ours are not | **1,689 of 1,689** of their wards stand on a bush tile (1,668 of them exactly 2 tiles from the body, and only when a bush tile is within 2); ours **169 of 4,338** (3.9%; 127 of 672 when a bush tile was within 2) |
| 5 | They wait in bushes, we almost never do | 187 waits (3+ rounds on one bush tile, no camp, no recall / bank): 1,284 body-rounds, longest 27; ours 14 waits, 59 body-rounds. Contest 100 of the 187 |
| 6 | The bush explains the contest game and part of fragment, not the rest | the 4 losses with 10+ of our body deaths (contest 64, fragment 19, eight 17, swirl 14); the other 8 losses have 0-7 deaths and are **income** losses |
| 7 | Outside contest the gap is income, not fights | body deaths 94 vs 70, kills 58 vs 62; camp gems **11,354 vs 15,428**; 70% of the 4,074 gem gap is neutral camps (+1,840) and camps on our half (+1,024) |
| 8 | Their off-meta champions (Tavi, Willow, Prism, Vendetta) are camp farmers first | Tavi: 6.0 rewards a game outside contest, 13.2k camp damage, 2.6k champion damage; Willow is a healer (7-8k healed on elkring and contest); Prism / Tavi are the contest killers (11 kills each); details in section 4 |
| 9 | The four losses with our champions were not bush losses | ambush, expanse, pilgrimage: 1 / 0 / 3 body deaths for us, farm races; fragment: 19-2 deaths from r36 (section 3) |

## 1. Results, drafts and where the gap sits

| Map | Banked us-them | Body deaths us-them | Their draft (pick order) | Our draft |
|---|---|---|---|---|
| ambush | 842-1000 | 1-1 | Ren, Stellar, C&I, Ryth, Varg | Ren, Stellar, C&I, Varg, Ryth |
| collision | **1036-748** | 7-12 | Stellar, Tavi, Ren | Ren, Stellar, C&I |
| contest | 0-1000 | **64-1** | Tavi, Willow, Stellar, Ren, Prism | Ren, Stellar, C&I, Varg, Ryth |
| corners | **1018-226** | 4-12 | Ren, Stellar, C&I, Tavi, Ryth | Ren, Stellar, C&I, Varg, Ryth |
| eight | 22-1030 | 17-6 | Stellar, C&I, Ren, Tavi, Ryth | Ren, Stellar, C&I, Varg, Ryth |
| elkring | 396-1008 | 7-0 | C&I, Stellar, Willow, Ren, Tavi | Ren, Stellar, C&I, Varg, Ryth |
| expanse | 700-1016 | 0-0 | C&I, Stellar, Varg | C&I, Stellar, Varg |
| fragment | 124-1006 | 19-2 | Ren, Stellar, C&I | Ren, Stellar, C&I |
| interlock | **1004-622** | 4-8 | Tavi, Stellar, Prism, Ren | Ren, Stellar, C&I, Ryth |
| lanes | **1020-934** | 1-3 | C&I, Ren, Stellar, Ryth, Varg | Ren, Stellar, C&I, Varg, Ryth |
| monolith | 842-1002 | 3-2 | Ryth, C&I, Stellar, Varg, Tavi | Ren, Stellar, C&I, Varg, Ryth |
| packs | **1028-724** | 4-11 | Ren, Stellar, C&I | Ren, Stellar, C&I |
| pilgrimage | 592-1028 | 3-0 | Ren, Stellar, C&I, Ryth, Varg | Ren, Stellar, C&I, Varg, Ryth |
| rows | 858-1023 | 0-0 | C&I, Stellar, Varg, Vendetta | Ren, Stellar, C&I, Varg |
| rushbait-v2 | 534-1014 | 6-7 | C&I, Stellar, Varg, Tavi | Ren, Stellar, C&I, Ryth |
| stampede | 0-1080 | 4-1 | Stellar, Prism, Willow, Ryth, Tavi | Prism, Stellar, C&I, Ryth, Tavi |
| swirl | 734-1074 | 14-5 | Ren, Stellar, C&I, Ryth | Ren, Stellar, C&I, Varg |

We won 5 (bold). Totals over the 17 games: banked 10,750 vs 15,535; camp gems 11,354 vs 16,428; rewards captured 301 vs 387
(their 444 body-captures include 57 that are two bodies sharing one reward; ours 301 = 301); gold earned 55.6k vs 76.5k; body deaths **158 vs 71**; kills 59 vs 113.

- **The deaths are one game.** Contest has 64 of our 158 deaths (their 1). Without it: deaths 94 vs 70, kills 58 vs 62, camp gems 11,354 vs 15,428
  (1.36x), rewards 301 vs 387; the gem gap of 4,074 splits into **own-half camps +1,210 (30%), neutral camps +1,840 (45%), camps on our half +1,024 (25%)**
  (by the side of the camp, counted per body-capture: their 36 captures on our half carry 1,414 gems, our 11 on theirs 390).
- **12 losses split in two**: contest 64, fragment 19, eight 17, swirl 14 of our body deaths decided by fights; ambush 1, expanse 0, pilgrimage 3,
  rows 0, rushbait-v2 6, elkring 7, monolith 3, stampede 4 are races for gems.
- Openers (micro.py definition, all 17 games): they open 163 fights, we 70. Their openers are spells from 4-5 tiles (Stellar d5 x33, Ren d4 x20, Prism d5 x17,
  Ryth d5 x14, Tavi d4 x10); the damage in the 3 rounds after an opener is 568 / 85 when they open and 337 / 232 when we do.
  Where they open (side seen from them): neutral 83, their own half 48, our half 32 (ours: neutral 34, own 27, their half 9).
  Deaths in the next 4 rounds per 100 body-rounds with the nearest enemy at distance 1 / 2 / 3: us 20.9 / 14.7 / 12.1, them 8.4 / 11.7 / 5.6.

## 2. Bush play

### 2.1 Definitions

- Bush tiles: `tools/replay/mapinfo.mjs` prints them as `"` (a wall, hole, altar, camp or spawn on the same tile would hide the mark; checked on 6 maps: the
  dump's count equals the engine's `Game_GetBush` count, no bush lies under a camp or spawn). `analyze.py` / `micro.py` / `report.py` have no bush notion;
  `bush.py` is the first tool that uses it. Bushes hide a body from everyone outside the bush, even while it attacks; a ward only reveals a bush if it
  stands inside it (`ENGINE_FACTS.md`). The tools do not know the champions' vision radius, so "unseen" below always means "stood in a bush".
- Positions: end-of-round snapshots; the tile of an attack is the `from` of its Attack event; a cast carries no tile (`from` is [0, 0] unless it is a dash),
  so it takes the tile tracked through the round's Move / Attack events from the previous snapshot. Damage spells cannot share a turn with walking, so a spell
  is cast from the end-of-previous-round tile ("in a bush at the action" = "in a bush the round before" for spells). *The first version of this analysis used the
  cast's `from` and put every spell at (0, 0); that gave "5 of 163 openers from a bush" and "121 of 163 openers on our half", both wrong. The tables below are from the fixed tool.*
- Side: walking distance from the two spawns, 3-tile neutral band (`analyze.py`'s `side_of`), seen from the body's own team.

### 2.2 How much they hide (alive body-rounds on a bush tile)

| Map | Bush tiles (% walkable) | Us | Them | Their damage dealt from a bush | Our damage from a bush | Our death incidents: killer in a bush / by a champion / all |
|---|---|---|---|---|---|---|
| ambush | 132 (1.7%) | 5.9% | 6.9% | - (no champion hits) | - | 0 / 0 / 1 |
| collision | 222 (14.5%) | 0.0% | 0.0% | 0% of 28.8k | 0% of 25.4k | 0 / 5 / 5 |
| **contest** | 26 (1.1%) | 3.5% | **21.7%** | 40% of 87.5k | 27% of 7.7k | **18 / 51 / 51** |
| corners | 60 (1.2%) | 1.4% | 2.5% | 3% of 9.4k | 0% of 10.4k | 1 / 3 / 3 |
| **eight** | 24 (2.0%) | 1.9% | **10.5%** | 26% of 26.9k | 10% of 12.4k | 2 / 10 / 12 |
| elkring | 36 (4.2%) | 4.0% | 2.0% | 27% of 15.6k | 20% of 4.5k | 1 / 4 / 5 |
| expanse | 0 | - | - | - | - | - |
| **fragment** | 24 (4.3%) | 11.3% | 13.2% | 37% of 17.4k | 37% of 7.2k | **7 / 13 / 13** |
| interlock | 38 (2.5%) | 2.7% | 3.7% | 10% of 14.8k | 1% of 13.1k | 0 / 3 / 3 |
| lanes | 144 (5.5%) | 7.2% | 2.4% | 0% of 3.3k | 2% of 3.0k | 0 / 1 / 1 |
| monolith | 66 (2.8%) | 1.7% | 3.2% | 6% of 7.6k | 0% of 4.1k | 1 / 3 / 3 |
| packs | 62 (6.5%) | 3.8% | 5.8% | 30% of 10.9k | 9% of 13.5k | 1 / 2 / 2 |
| pilgrimage | 152 (5.9%) | 2.6% | 2.7% | 20% of 5.4k | 22% of 2.2k | 1 / 2 / 2 |
| rows | 142 (6.2%) | 1.7% | 1.3% | - | - | - |
| rushbait-v2 | 120 (5.5%) | 2.1% | 3.5% | 3% of 11.4k | 8% of 8.4k | 0 / 5 / 5 |
| stampede | 456 (19.1%) | 6.4% | 12.5% | 0% of 7.5k | 0% of 2.4k | 0 / 2 / 3 |
| swirl | 14 (1.5%) | 4.8% | 4.2% | 15% of 20.0k | 18% of 8.4k | 2 / 9 / 11 |
| **all** | | **3.3%** (1,551 of 46,574) | **7.9%** (3,780 of 48,026) | 23.5% of 266k | 9.0% of 122k | 34 / 113 / 120 |

- Groups of games: our 5 wins: us 2.8%, them 2.6%. The 11 losses other than contest: us 3.6%, them 5.6%. Contest: us 3.5%, them 21.7%.
  A map with a lot of bush is not a bush loss: stampede has 456 tiles and they stand in them 12.5% of the time against our 6.4%, collision has
  222 and nobody (0.0% / 0.0%) enters them.
- **It is not just geography**: both teams stand in bushes more when fighting. Share of body-rounds in a bush: no enemy within 6 tiles us 2.7% / them 6.4%; enemy within 6 us 7.0% / them 17.4%;
  hitting or being hit that round us 7.6% / them 18.8%. The ratio is 2.4-2.5x in every context.
- By side (seen from the body's team): us own half 2.9%, neutral 5.6%, their half 2.4%; them own half 4.2%, **neutral 18.3%**, our half 7.5%.
- By champion (their share in a bush): Prism 17.8%, Willow 16.6%, Tavi 9.0%, Ren 9.1%, Stellar 7.7%, Cassi 6.9%, Ryth 5.3%, Varg 3.2%, Issac 2.7%, Vendetta 0.6%. Ours: 3.2-3.6% for each of our champions (Tavi 5.3% on 453 body-rounds).

### 2.3 Strikes from a bush, and what comes back

| | Us | Them |
|---|---|---|
| Champion damage dealt by a body standing in a bush (all / without contest) | 9.0% / 7.8% | **23.5% / 15.3%** |
| Their damage from a bush by champion (all) | | Willow 52%, Prism 33%, Cassi 30%, Ren 27%, Tavi 22%, Stellar 22% of 100k, Issac 20%, Ryth 8%, Varg 0% |
| Damage taken back by the attacker in the 3 rounds after an attack turn, **from a bush** | 153 (70 attack turns) | **43** (244) |
| ... same, from the open | 130 (763) | 111 (876) |
| Without contest: from a bush / from the open | 145 (49) / 131 (709) | **65** (124) / 128 (715) |
| Fight openers (all / without contest) | 70 / 68 | 163 / 111 |
| ... opened by a body in a bush at the action | 7 (10%) / 6 | 36 (22%) / 13 (12%) |
| ... damage in the next 3 rounds mine / theirs, opener hidden the round before | 439 / 235 (n=10) | **743 / 7** (n=37); without contest 646 / 9 (n=14) |
| ... same, opener not hidden | 320 / 231 | 516 / 108 |

- A bush attack costs them less than half of what a normal attack does (43 vs 111 returned, 65 vs 128 without contest) and gives us nothing (153 vs 130): our bush attacks are answered.
  A likely reason is the wards of section 2.6: in **62 of our 70 bush attack turns an enemy ward stood inside the same bush** (return fire 166; the other 8 turns 52), while our wards were
  in the attacker's bush in only 47 of their 244 (return fire 21, the other 197 turns 48). Small samples, and the ward's reveal rule is untested (section 7).
- Outside contest, openers from a hidden body are as rare for them as for us (14 of 111 vs 9 of 68), so the first strike is not where the games are lost; the gap is the damage afterwards
  and the number of fights they start (111 vs 68).

### 2.4 Our deaths: who killed us from where

Death incidents (a Cassi & Issac double death counts once): ours 120 (113 by a champion, 7 by camps), theirs 60 (59 by a champion).

| | Ours | Theirs |
|---|---|---|
| Killer standing in a bush at the final blow (all maps) | **34 of 113 (30%)** | 4 of 59 (7%) |
| ... without contest | 16 of 62 (26%) | 3 of 58 (5%) |
| A bush attacker among the hitters of the last 5 rounds (all / without contest) | 54 (48%) / 25 (40%) | 6 (10%) / 5 (9%) |
| By side of the victim: own half / neutral / their half (killer in a bush) | 19 of 55 / 11 of 46 / 4 of 12 | 3 of 39 / 1 of 17 / 0 of 3 |
| Victim at 75%+ health the round before (killer in a bush / such deaths) | 13 / 41 (3 / 15 without contest) | 2 / 9 |
| Killers of our bodies (bodies, a C&I pair = 2) | Stellar 69, Tavi 22, Prism 15, Ren 15, Cassi 14, Ryth 10, Issac 3, Varg 1, Willow 1 | |
| Killer hidden at the end of the previous round, by killer champion (bodies killed, all maps) | Stellar 21 of 69, Tavi 6 of 22, Prism 6 of 15, Ren 7 of 15, Cassi 6 of 14, Ryth 2 of 10 | |

By map the 34 are: contest 18, fragment 7, eight 2, swirl 2, corners 1, elkring 1, monolith 1, packs 1, pilgrimage 1 (all other maps 0).
Half of the bush kills are one game (contest 18 of 34). Where the victim stood: our own half 19 of 55 (35%), neutral 11 of 46 (24%), their half 4 of 12: they do not only wait at their camps, they sit next to the contested groups
(fragment: the bush at (21-22, 14-16) is 4 tiles from the centre elk group; their Cassi killed our C&I from (22, 15) at r44 and their Stellar from (22, 16) at r207-208).

### 2.5 Waiting

A wait = the same bush tile for 3+ rounds, no camp damage dealt, no recall / bank / shop / capture that round (so not a farm and not a channel).

| Map | Us: waits / rounds | Them: waits / rounds / longest | Ended with a champion hit by that body within 3 rounds |
|---|---|---|---|
| contest | 4 / 17 | **100 / 785 / 27** | 26 |
| eight | 3 / 16 | 31 / 165 / 8 | 13 |
| fragment | 0 / 0 | 20 / 128 / 10 | 6 |
| packs | 0 / 0 | 9 / 41 / 8 | 5 |
| interlock | 2 / 7 | 8 / 37 / 8 | 2 |
| pilgrimage | 1 / 3 | 3 / 39 / 28 | 1 |
| swirl, elkring, monolith, corners, rushbait-v2, ambush, stampede (ours: elkring, ambush, stampede, rows) | 4 / 16 | 16 / 89 / 10 | 8 |
| **all** | **14 / 59** | **187 / 1,284** | **61** |

Contest is the extreme case. The map has a bush ring around the altars at (21-28, 21-28) (26 bush tiles). **34.2% of their alive body-rounds** stand inside that 8x8 box (3,019 of 8,825;
195-451 per 200 rounds all game long) against 6.5% of ours (444 of 6,843); 55 of our 64 deaths are within 8 tiles of it; our team is dead 23-46% of the time in every 200-round window;
their first monolith capture is at **r1395** (five 200-gem rewards at r1395-1735); over the game they make 51 kills to our 1 and earn 11,960 gold to 3,405.

### 2.6 A hidden enemy within 4 tiles, and wards

Body-rounds (not on a spawn) with an enemy champion within 4 tiles, by whether that enemy stood in a bush:

| Team | Enemy within 4 | Body-rounds | Damage taken next round | Damage dealt next round | Deaths in 4 rounds per 100 |
|---|---|---|---|---|---|
| us | hidden only | 483 | 66 | **5** | 14.7 |
| us | visible only | 2,294 | 53 | 38 | 9.4 |
| us | hidden + visible | 209 | 102 | 40 | **35.4** |
| them | hidden only | 223 | 27 | 59 | 3.6 |
| them | visible only | 2,480 | 36 | 64 | 7.1 |
| them | hidden + visible | 116 | 49 | 52 | 0.0 |

Walking within 4 tiles of a bush that holds an enemy we cannot target costs us 5 damage dealt against 38 for 66 taken, and the mixed case (one visible, one hidden) kills 35 of every 100 body-rounds.
It touches only 692 of our 46,574 body-rounds (1.5%), so it is a few dozen deaths, not the whole gap.

**Wards**: placements 4,338 (ours) vs 1,689 (theirs). Theirs: **all 1,689 on a bush tile**, 1,668 at Chebyshev distance exactly 2 from the body (the placement radius), and they ward only when a bush tile is within 2
(1,683 of 1,687 placements had one; 12,324 alive body-rounds had a bush tile within 2, one ward per 7.3 of them). Ours: 3.9% on bush tiles; with a bush tile within 2 we chose it 127 times of 672 (19%).
`Brain::place_ward` puts the ward on `pos + 2 * (step toward the enemy spawn)` every 10 rounds and never looks at the bush mask. Per map their ward counts are 0-1 on collision (222 bush tiles that nobody enters) and expanse (no bush) and
837 on contest, 195 pilgrimage, 134 swirl, 98 stampede, 82 ambush.
Wards also **block the tile**: 1,182 of their 1,221 `Movement blocked` events are their own bodies walking into their own ward on a bush tile (ours: 12 into our wards, 8 into theirs; theirs into ours: 1);
in the 1,211 rounds with such a block (all targets) the body still moved in 776 and attacked or cast in 293 more, so it costs them little.

## 3. The four losses with the same champions

Same champions as ours (order differs): ambush (Ren, Stellar, C&I, Ryth, Varg), pilgrimage (same), expanse (C&I, Stellar, Varg), fragment (Ren, Stellar, C&I). We also won packs (same draft) and lanes (same set) against it.

| | ambush 842-1000 (r535) | expanse 700-1016 (r446) | pilgrimage 592-1028 (r616) | fragment 124-1006 (r587) |
|---|---|---|---|---|
| Champion hits in the game (us / them) | 0 / 0 | 0 / 0 | 26 / 49 (2.2k / 5.4k damage) | 54 / 78 (7.2k / 17.4k) |
| Body deaths (kills) | 1-1 (both by camps) | 0-0 | 3-0 (0-2) | **19-2 (1-13)** |
| Share of body-rounds dead | 1.9% / 1.9% | 0 / 0 | 4.9% / 0 | **48.9%** / 5.1% |
| Rewards captured (gems) | 13 (1,068) / 10 (1,000) | 18 (700) / 19 (1,136) | 9 (660) / 14 (1,096) | 6 (168) / 30 (984) |
| ... on neutral / the other half (gems) | 144 / 0 vs 0 / 0 | 0 / 0 vs 0 / 360 | 184 / 0 vs 552 / 0 | 0 / 0 vs 0 / 386 |
| Gems captured by r200 / r300 / r400 | 284 / 438 / 664 vs 284 / 510 / 702 | 256 / 424 / 700 vs 354 / 532 / 852 | 136 / 272 / 364 vs 296 / 456 / 616 | 124 / 124 / 146 vs 168 / 336 / 496 |
| First reward (round) | r69 / r71 | r29 / r43 | r55 / r53 | r22 / r36 |
| Gold earned | 2,834 / 3,270 | 2,674 / 3,660 | 2,260 / 2,880 | 950 / 5,525 |
| Time walking / on camps / idle | 64% 16% 8% vs 68% 18% 2% | 56% 25% 3% vs 45% 23% 17% | 72% 11% 2% vs 61% 14% 13% | 30% 10% 2% vs 40% 21% 11% |
| Gems banked per bank trip (trips) | 94 (9) vs 77 (13) | 44 (16) vs 73 (14) | 74 (8) vs 47 (22) | 31 (4) vs 35 (29) |
| Gem-rounds carried per banked gem | 59.7 vs 41.4 | 18.3 vs 25.7 | 63.3 vs 73.1 | 27.0 vs 26.6 |
| Wards (all on bush tiles for them) | 310 vs 82 | 169 vs 0 | 295 vs 195 | 128 vs 72 |
| Their hits from a body hidden the round before | - | - | 8 of 49 | 25 of 78 |

**ambush (a pure pace race; no bush, no fight).** 100x100; 13 rewards for us, 10 for them (13 body-captures each). They had captured 1,000 gems by r497; we had 890 by r500 and 1,068 by r531, but only 842 banked: 226 gems
sat in three bags (Ren 72, Cassi 106, Issac 48) 7-19 tiles from the nearest altar when they banked their 1,000 at r535. Two gaps stack: capture pace (438 vs 510 gems at r300, 890 vs 1,000 at r500)
and carry time (59.7 vs 41.4 gem-rounds per banked gem; 9 trips of 94 gems against 13 of 77; the altars are 30+ tiles from spawn). Banking alone would not have won it: banked + bags was 996 at r528 and first passed 1,000 at r531, four rounds before they finished. Their rewards are fewer and bigger (10 of ~100 gems against our 13 of ~82).
Items: our Stellar earned 0 gold and bought nothing (0 rewards in 535 rounds) and our Issac has no emblem either, our Ren's first emblem is r327 (theirs: none), our Varg took 1 reward (240 gold, one Monster emblem at r158) while their Varg
took 4 (1,120 gold; Durability + Jungle strength at r145, two Power strength emblems by r362). Camp damage: Varg 15.3k vs 21.8k, Ryth 6.8k vs 11.9k. Idle 7.6% of our body-rounds vs 2.0%.

**expanse (a corner-group race; no bush on the map).** Both clear small wolf and gold groups near spawn. They also cycle the **5,800-HP, 120-gem groups of 2 elks + 2 gems** in the far corners:
(71, 4) cleared at r157 (90 rounds from first hit), r293 (42), r422 (35) and captured by their Stellar at r166, r302, r431 (70 tiles from home); (71, 14) cleared at r278, r375 and captured by their Varg at r284, r381; (71, 19) cleared at r400 (348 rounds from first hit) and captured by their Cassi at r409.
They captured **six 120-gem rewards (720 of 1,136 gems, first at r166)**; we captured **two (240 of 700, Issac r391 and Varg r395)** at the mirror corner groups (8, 60) / (8, 65), cleared once each at r385-388. Our other 16 rewards average 29 gems. Their Stellar's whole gem income is its three corner rewards (360 gems, ~0.8 gem per round of the game); ours averages 0.39 gem per body-round.
First emblems: ours Varg Monster r70, Cassi Monster r98, Issac Monster r122, Stellar Monster r180; theirs Varg Jungle r69, Issac Jungle r86, Stellar Power focus r166, Cassi none. By r300 their Issac has 135 strength against 88 and their Varg 180 against 105 (gold 1,220 / 1,160 vs 980 / 916; camp damage 18.3k / 19.4k vs 8.6k / 16.4k).
They idle (Cassi 205 rounds, Stellar 83) and still bank more: the difference is the reward size per trip (73 vs 44 gems a bank).

**pilgrimage (income; captures, not fights).** 3-0 deaths, 26 and 49 champion hits. They captured 14 rewards (1,096 gems; 552 gems on neutral camps) against 9 (660; 184 neutral): gems per reward 78 vs 73, count 1.55x. Our bodies walk 72% of the time
(Ryth 548 of 616 rounds, 0 rewards, 44 camp rounds, 3.9k camp damage; Issac 433 walking, 0 rewards, 60 gold; Stellar 20.2k camp damage and 1 reward at r510). 12 of our 21 group kills were gold-only clusters (1gold / 2gold: no gems; they killed 2 such of 16).
Our first emblems: Varg r56, Cassi r133, Ren r204, Stellar r510, Issac and Ryth none (gold 60 and 0); theirs: all six bought one by r434 (Ren r120, Varg r145, Issac r268, Stellar r339, Cassi r340, Ryth r434).
Gems per 1,000 camp damage 13.1 vs 21.9: we hit camps harder (120 vs 98 damage per camp round) and complete fewer rewards.

**fragment (fights, from r36).** The only one of the four with a body-count gap. At r36 our Ren (335 of 900 hp) is fighting at the centre group (17, 13) against their Ren (355), Issac (860) and Cassi (680), the camps hitting everyone; our Cassi and Issac arrive from 4-5 tiles away and die at r44 (their Cassi, standing in the bush at (22, 15), hit our Issac at (19, 14); our Cassi dies with it). Then Ren r104 (their Stellar from the bush at (14, 20)), Ren r202 (their Cassi from (21, 15)), C&I r207 and Stellar r208 (their Stellar from (22, 16)), C&I r279 / r370 / r437 / r523, Stellar r321 / r379 / r477, Ren r480: 13 incidents, 19 bodies, dead for 244 / 181 / 365 / 360 rounds (Ren / Stellar / Cassi / Issac); 49% of all our body-rounds are dead.
Their Stellar alone: 9 kills, 11.4k champion damage (ours 4.5k), 11 rewards, 2,012 gold, Power-focus emblem first at r71 (9 of its 12 emblems are Power focus by r544); our Stellar: Monster + Treasure focus at r160, Bruiser r357.
Our Cassi and Issac earned 0 gold and bought nothing all game. Income follows the bodies: 6 rewards (168 gems) against 30 (984), 11 of which (386 gems) are camps on **our** half, taken at r214-576; from r250 on we had 0-3 of 4 bodies alive at every 50-round mark.
Seven of the 13 champion-caused incidents have a killer standing in a bush at the blow and 7 of 13 a bush attacker in the last 5 rounds, but our own damage from a bush is 37% too: both teams fight around the same 24 bush tiles, and they bring more damage (17.4k vs 7.2k) and lose 2 bodies to our 19.

## 4. Their champions: Tavi, Willow, Prism, Vendetta

Where they are drafted: Tavi in 9 games (collision, contest, corners, eight, elkring, interlock, monolith, rushbait-v2, stampede), Willow in 3 (contest, elkring, stampede), Prism in 3 (contest, interlock, stampede), Vendetta in 1 (rows).
Per game, outside contest unless noted (`body.csv`; kills = credited kills):

| Champion (games) | Rewards / gems | Gold | Camp damage | Champion damage | Kills / deaths | First emblem | Items at the end |
|---|---|---|---|---|---|---|---|
| Tavi, 8 games | 6.0 / 183 | 790 | 13.2k (Varg 14.8k, Stellar 14.3k) | 2.6k | 0.9 / 0.6 | median r140 | `PfE` ×0-6 + `DfE` + `JfE` + `BhE` (focus, Power first) |
| Tavi, contest | 1 / 200 | 2,310 | 36.0k | 18.2k | 11 / 0 | r127 | `PfE` ×14 + `DhE` |
| Willow, 2 games (elkring, stampede) | 3.5 / 204 | 728 | 5.9k | 0.3k | 0 / 0 | r177 | strength Power (`PsE` ×2) + `DsE` + `JsE` + `BhE` |
| Willow, contest | 1 / 200 | 2,335 | 41.6k | 1.7k | 1 / 0 | r172 | `PsE` ×13 + `DhE` |
| Prism, 2 games (stampede, interlock) | 3.5 / 111 | 468 | 6.2k | 3.5k | 0.5 / 1.5 | r165 | `PfE` + `Df` + `JfE`; `PfE` ×2 + `DhE` |
| Prism, contest | 1 / 200 | 2,138 | 44.3k | 25.3k | 11 / 0 | r215 | `PfE` ×12 + `DhE` |
| Vendetta, rows | 4 / 264 | 1,080 | 10.7k | 0 | 0 / 0 | r75 | `PsE` ×4 (strength Power) + `DsE` + `JsE` + `BhE` |

- **Tavi is a farmer with a stun**: 6.0 rewards a game and about as much camp damage as their Stellar (13.2k vs 14.3k), 22.5% of its champion damage from a bush, 9.0% of its body-rounds in one; it killed 22 of our bodies (9 outside contest) and its
  stun (2.2x focus, range 4) is the fifth most common opener (spell from 4 tiles, x10). On collision (3 champions: Stellar, Tavi, Ren) it made 10 captures and dealt 10.1k champion damage (we won that game 1036-748).
- **Willow heals**: 7,315 healed in 24 casts on contest, 8,094 in 29 on elkring, 765 in 3 on stampede; her own champion damage is 2.2k in total over the three games, 52% of it from a bush. Elkring was 396-1008 with deaths 7-0 and zero champion hits by Willow.
- **Prism** (stun 1.5x focus, area): 33% of its damage from a bush; killed 15 of our bodies, 14 of them on contest (11 kills credited there, 25.3k champion damage), 1 elsewhere. In interlock (we won) it died twice.
- **Vendetta** appeared once, on rows (a farm race, 0 deaths either side, 858-1023 at r348): 4 rewards, 264 gems, 1,080 gold, 10.7k camp damage.
- On **contest and stampede** the whole team is casters (Tavi, Willow, Stellar, Ren, Prism / Stellar, Prism, Willow, Ryth, Tavi) and on contest each of the three stacks 12-14 Power emblems by r1777 (2,138-2,335 gold earned each).
- Builds, all 17 games: Power is the first emblem for 31 of their 79 bodies with an emblem (Jungle 27, Bruiser 15, Durability 5); ours are Monster for 48 of 71 and Jungle for 22; **we bought 0 Power emblems in the whole set** against 250 of theirs.
  Stellar's first emblem: theirs `PfE` 14 of 14, ours `MfE` 14 of 14. Damage stat at r300 (mean, outside contest): Cassi 184 vs our 122, Issac 99 vs 61, Ryth 90 vs 66, Varg 149 vs 106, Stellar 196 vs 173, Ren 205 vs our 248 (we lead on Ren);
  champion damage per game: their Stellar 4,277 vs our 2,256, Cassi 1,526 vs 774. Build changes inside our brain were tested and lost (docs 06 and 08; `build_style 3`: 48.2% vs `_rm` on 56 maps, 32.4% vs `_ST` on the official 17): this table says what they buy, not that buying it wins here.

## 5. How this team beats us, ranked by measured size

1. **Income, outside contest**: 1.36x camp gems; 70% of the gap is neutral camps (+1,840 gems) and camps on our half (+1,024), and rewards are bigger per trip (expanse 120-gem groups 6 vs 2; ambush 100 vs 82; pilgrimage 78 vs 73 gems and 14 vs 9 rewards).
2. **Contest**: a bush-ringed fort at the map centre holds 34% of their body-rounds; 64-1 deaths, 51-1 kills; monolith taken from r1395. It is one game of 17 but 40% of our deaths.
3. **Fights** (contest, fragment, eight, swirl: 64 + 19 + 17 + 14 = 114 of our 158 deaths): they win the trades with the same or fewer bodies (95-49 deaths in the 146 fights with 4+ hits, 2.3 vs 2.0 bodies each; they deal 266k champion damage to our 122k).
4. **The bush itself**: 34 of our 113 champion-caused deaths (16 of 62 without contest) and 15.3% of their damage outside contest (23.5% with it), against 7.8% (9.0%) of ours, with 65 against 145 damage returned. Real, concentrated on four maps
   (contest 18, fragment 7, eight 2, swirl 2 of the 34 bush kills), and not the reason for ambush, expanse, pilgrimage, rows, elkring, rushbait-v2 or monolith.

## 6. Counters for our bot, each tied to a number

None of these was run; section 7 says how to test them. All stay inert on maps without bushes (expanse 0 tiles, collision where nobody enters) so the control maps do not move.

| # | Change | Number it rests on | Where | First test |
|---|---|---|---|---|
| C1 | **Ward the bush**: in `place_ward`, when a tile of `bc::map::bushes()` lies within Chebyshev 2 of the body, ward it (prefer the one nearest the enemy approach / the camp group being farmed or contested), else the current rule | their 1,683 of 1,683 vs our 127 of 672 (19%); 48% of our champion-caused deaths (40% without contest) have a bush attacker among the last 5 rounds' hitters; their bush attacks take back 43 (65) vs 111 (128) from the open; **in 62 of our 70 bush attack turns an enemy ward stood in the bush** | `brain.cpp` `place_ward` (rate-limited to 10 rounds, 5 at capture and recall time); one `bitboard` mask test per call | **Engine probe first**: does a ward on one bush tile reveal occupants of the other tiles of that bush, and within what radius? (`ENGINE_FACTS.md` says only "a ward inside does"; control wards have their own radius). Then A/B on the bush maps |
| C2 | **Bush ghost near contested groups**: when an enemy champion was last seen within 2 tiles of a bush tile and is now gone, keep it in the fight estimate at that tile for ~4 rounds; skip or abort a camp visit when 2+ such ghosts sit within 5 of the group and no ward stands in that bush | hidden-only band: 5 damage dealt vs 38, 14.7 vs 9.4 deaths per 100 body-rounds; mixed band 35.4; fragment 7 of 13 bush kills at the centre group, contest 18 of 51 | `combat()` / group score; narrower than the rejected `fight_mem` (it only fires for a vanished enemy next to a bush, and only near a group we score) | `fragment`, `eight`, `swirl`, `packs` both sides vs `_m10`; contest, fragment, eight and swirl hold 29 of the 34 bush kills (18 + 7 + 2 + 2) |
| C3 | **Contest ring**: treat the 8x8 bush box (and 4 tiles around it) as a no-go for single bodies until 4+ of ours are alive and together | 34.2% of their body-rounds inside it vs 6.5% of ours; 55 of 64 deaths within 8 tiles; first monolith capture r1395 | the contest owner (S7R); a danger layer, not new logic | `contest` + its ladder copy only |
| C4 | **Do not build our own bush ambush** | our bush attacks draw 153 back (62 of 70 with an enemy ward inside), 9.0% of our damage; the 8 attacks without such a ward drew 52 | none | decided by C1's probe: only after our wards sit in the bushes |
| C5 | **Far-corner solo cycle on expanse**: send the Stellar-class body to the 5,800-HP / 120-gem corner groups that are 60-70 tiles from home, with recall after the capture | 6 rewards (720 of 1,136 gems, first r166) vs 2 (240 of 700, first r391); their Stellar earns 360 gems from three corner rewards (136 and 129 rounds apart) = ~0.8 gem per round, our average is 0.39 per body-round | `obj_*` gating (expanse was left out on purpose: `obj_share`); `draft.cpp` `official_map()` | unopposed pace (`idle`) on expanse first (target: the 120-gem rewards before r200), then head-to-head |
| C6 | **Neutral-camp income**: score neutral camps like own-half ones when the enemy has not been seen near them | neutral-camp gems 4,964 vs 2,124 (3,964 without contest); camps on the other team's half 1,414 vs 390; pilgrimage neutral 552 vs 184 | `group_score` side weights | `econ` agent's cells (opening and income); this is the largest income line |
| C7 | **Shorter carry on 100x100 / 50x65 maps**: bank earlier in the last third (smaller threshold when the altar is 30+ tiles away and banked + bags is within ~150 of 1,000) | ambush: carry time 59.7 vs 41.4 gem-rounds per gem, 9 trips of 94 vs 13 of 77; 226 gems still in three bags at the end (not enough alone to win: see section 3) | `race_mode` / `win_bank` (session 8 task 6, not started) | ambush and pilgrimage vs `idle`, then vs `_m10` |

Already tested and rejected, so not repeated here: Power-heavy builds (`build_style 3/4`), Monster before health for Ren / Ryth, a reward to the better gold user, `fight_mem` / `pair_pool` / `kill_reach`, stay-out-of-fights rules
(`flee_hold`: 23.5%). The lesson of those: every rule that makes the whole body more cautious loses head-to-head; C1-C2 are targeted at one tile pattern, C3 at one map.

## 7. How to test (nothing here was run: the CPU is shared)

1. Probe for C1 (idle vs a scripted bot with one body in a bush and a ward in/next to it; see `tools/probe5_all.sh` for the pattern). If a ward only reveals its own tile, C1 is dead; if it reveals the bush field, build it.
2. C1 / C2 as `params.h` switches with the default off (`ward_bush`, `bush_ghost`), `ledger.py run` on the 16 official maps with bush tiles (all but expanse; collision is inert because nobody enters its bushes) both sides vs `_m10`, `_ST`, the third-party panel (`_ifish`, `_px9`)
   and the sneaky proxy (`_snd`); report separately: fragment, eight, swirl, packs, contest. Accept if the bush maps do not lose and the rest are identical (check fuel: one bush mask test per ward call, one scan per camp visit).
3. C5 / C6 / C7 through the pace tool first (`bench.py BOT idle`, 17 official maps) because they change pace, then head-to-head.

## 8. Method and caveats

- Reproduce: `for f in experiments/sneaky_oct18/*.repl26a; do m=$(basename $f .repl26a); node tools/strategy_v2/decode_dmg.mjs $f --out DMG/$m.json --rollovers; node tools/replay/mapinfo.mjs $f > MAPS/$m.txt; done`,
  then `python3 -I tools/strategy_v2/bush.py DMG MAPS` (`--section occ,hits,deaths,wait,hidden,wards`, `--skip contest`). The group-kill / capture / emblem numbers are from `experiments/sneaky_oct18/analysis/*.csv`.
- Duplicates (04-f3a / 05-29 / 05-325) are dropped everywhere above; the committed `report.md` counts 20 archives.
- "In a bush" is a snapshot or action-tile fact. The tools do not model vision radius or wards' coverage, so none of these numbers says what our bodies could see; they say where the attackers stood.
- Samples are small where it matters: hidden-only band 483 body-rounds, 37 hidden openers (14 without contest), 8 bush attack turns without an enemy ward. Read them as direction, not as effect sizes.
- Rewards per game: a reward captured by two bodies in one round is one reward (the csv counts it twice: 444 body-captures vs 387 rewards for them, 301 vs 301 for us). Rewards stolen from the team that killed the group are negligible (14 theirs, 7 ours).
- The first draft of the bush numbers read casts as standing at (0, 0); fixed before this write-up, and the old "they open fights on our half" claim does not hold (their openers: 83 neutral, 48 own half, 32 our half).
