# Items, consumables and ability use: the top teams vs their opponents (current versions, Oct 23 07:00-15:00 UTC)

Dimension: what the six study teams buy (build order, max HP and damage over time, gold), how they use consumables (altar
locks, teleport crystals, wards) and abilities (casts, fight vs camp use, resets, dashes, shields, heals, stuns, channel
cancels, Prism with big bags), compared with their opponents in the same games. Section 7 turns it into runtime rules for god2.

Every number is **MEASURED** from the replays unless the line says **INFERRED**. "S" = the study team's bodies, "O" = its
opponents in the same games. Replay references are `map_matchId8` (files in `C:/battlecode/cache/t2/<team>/`) plus a round.

## 0. Ranked findings (details and evidence in sections 2-6)

1. **The #1 team out-builds everyone on health.**
   - 46% of prism best girl's (pbg) stat points go into health, against 31% for its opponents. Nyx copies the build: 43% against 31%.
   - Their Vesper has 3,505 max HP at r600, against 2,109 for the opponents' Vesper. It gains 165 HP per 100 gold spent, against 91, and dies 1.28 times a game against 2.06.
   - pbg wins 73% of games when its team max-HP ratio at r600 is at least 1.1, and 8% when it is below 0.9.
   - The damage-heavy builders die more (deaths per body per 1000 alive rounds):

     | team | stat points into strength | deaths | opponents' deaths |
     |---|---|---|---|
     | IFish | 69% | 2.38 | 2.51 |
     | coo | 66% | 2.85 | 1.58 |
     | cm | 47% | 2.74 | 2.29 |
     | pbg | 36% | 1.56 | 2.29 |
2. **Prism is a gem-powered nuke, and its holders build health.**
   - Prism damage per cast rises with the carried bag: 119 on champions with no bag, 931 with a bag of 200+, and 2,310 with 778 gems (`00packs_475b8b69` r1426).
   - pbg, Nyx and Pantheon draft Prism in 100% of their games.
   - pbg and Nyx open Prism with Durability-hp, then Monster-focus, Jungle-hp, Home-hp and Bruiser-hp.
   - They hold 66-107 gems on average at r400-600 and 93-215 at r1000, and bank 0.6-0.8 times a game (mean 157-322 gems).
   - Pantheon builds its Prism for focus and loses 99 gems per Prism death (33 deaths with a bag of 100+ in 105 games). pbg loses 35.
3. **Big-bag tributes are the weak spot of every gem-holding team.**
   - A tribute channels for bag/10 turns. Tributes with a bag of 150+ are interrupted in 8-60% of cases (most teams 36-60%) even with no enemy within 6 at the start, and in 57-97% with one.
   - They are interrupted by stuns, altar locks, death or the tributer cancelling.
   - Opponents cancelled pbg tributes of 841, 741, 521, 491 and 368 gems with locks, and others with stuns.
   - pbg's Marcella stunned and killed Pantheon's Vesper 40 rounds into a 711-gem tribute (`00gem_fields_3fc2330b` r558-560): 711 gems changed hands.
4. **Altar locks are per team, and the top teams use them to protect their own banking spot.**
   - Placing a lock cancels the other team's channels at that altar. Each team can hold its own lock on the same altar; five attacks by the blocked team clear it.
   - Locks placed per game: cm 5.6, Pantheon 4.2, IFish 2.9, coo 1.1. pbg and Nyx place 0.
   - 42-83% of their locks are followed by their own tribute at that altar within 3 rounds.
   - A lock stands for a median of 74-145 rounds, covers 3.0-5.3 of their own banks, and costs the enemy 3.1-3.9 attack turns to clear.
5. **Ready spells are used in fights more often by the study teams.** Share of ready in-fight turns with a cast, study team vs opponents:

   | slot | study team | opponents |
   |---|---|---|
   | Heart of Ruin dash | 51-67% (coo 40%) | 37-53% |
   | Ryth stun | 44-50% | 29-41% |
   | Marcella damage, pbg / Nyx | 48% / 62% | 24-26% |
   | Vesper reset, pbg / Pantheon / coo | 48-59% | 25-36% |

   - Melee reset use in champion-attack turns is 90-97% when ready for Marcella and Ryth.
   - Ranged walk + reset + shot is 9-20% of Vesper and Tavi attack turns. Nyx never does it.
6. **Stuns:** 22-29 per game on champions.
   - Ryth is the main stunner (8.9-10.9 a game). Then come Prism (7.5-11.9), Heart of Ruin (3.3-9.2), cm's Tavi (11.7) and IFish's Cassi (7.8).
   - Stuns on enemies who are tributing: pbg 39, coo 30, Nyx 32, cm 23 and IFish 20 per 100-116 games. Bags reach 711.
7. **Teleport crystals are a map tool.**
   - pbg, IFish and coo use 4.5-7.7 a game, all on hop maps: 01shortcut about 45 a game, 00road_of_riches 18-38, 00pilgrimage, 01fracture, 00reverse_spiral, 01starvation and 00great_wall.
   - pbg and IFish hops replace walks with a median length of 54-65 tiles; 85-93% land within 3 of a camp.
   - cm and Nyx never buy crystals; Pantheon almost never (3 uses in 105 games).
8. **Openers vary by map; health dominates the long tail.**
   - pbg switched its bot at about 14:00 UTC to Jungle openers (Vesper Js>Bs>Bh) and went 18-7.
   - IFish opens Monster on six maps (four of them the largest in the pool) and Treasure elsewhere, with no exception per map.
   - Treasure-first (IFish, cm, coo, Pantheon) is not needed: pbg never buys Treasure and still earns 10-23% more gold per body than its opponents.
9. **Wards:**
   - About 3 per body per 100 alive rounds, 68-100% in bushes, ~50% within 3 of a camp, placed at maximum range (1.9 tiles).
   - pbg and IFish ward more toward the enemy (28-30% on the enemy half, against 18-19%).
   - cm instead drops one on every charge (9.4 per 100 rounds), only 6% of them in bushes.

## 1. Data and method

**Games** (ranked, current bots):
- 584 unique replays, 663 study-team games.
- Opponents are mostly other top-10 teams for pbg, IFish and Pantheon, and rank ~15-50 teams for coo, cm and Nyx.

| key | team | games | W-L | most frequent opponents |
|---|---|---|---|---|
| pbg | prism best girl (#1) | 116 | 71-45 | Pantheon 21, IFish 19, procless 19, :3 15, policy wonk 13 |
| pbg14 | **pbg's newer bot, games from 14:00 UTC** (subset of pbg) | 25 | 18-7 | Pantheon, IFish, procless, :3, Univardisty (5 each) |
| ifish | Intercontinental Fish (#2) | 110 | 66-44 | pbg 20, :3 18, procless 17, policy wonk 16, Pantheon 15 |
| pantheon | Pantheon (#6) | 105 | 52-53 | :3 19, pbg 17, IFish 17 |
| coo | conqueror_of_openai (#18) | 101 | 55-46 | Mite 12, hello 10, NTU 9, EMPEROR Tung 9 |
| cm | Claudus Maximus (#19) | 106 | 58-48 | NTU 14, the ruliad 13, caterpillow 11, coo 9 |
| nyx | Nyx (#31) | 100 | 49-51 | EggsAfter11AM 15, AlphaSlop 9, Ad Astra 9 |

- **Version change:** pbg's build signature changes at 14:00 UTC (section 2.3), so `pbg14` is reported separately as its latest bot.
- The other teams' builds are stable through the window (hour-by-hour first-emblem signatures), except:
  - cm's Tavi opens Bruiser-strength until ~12:00 and Treasure-strength after;
  - IFish's lock use rises after ~11:00 (0.2-0.6 to 0.5-0.7 locks per body);
  - Pantheon's lock use falls after ~12:00 (1.2-1.3 to 0.7-0.9).

**Tools** (new, all in `tools/top2/items/`):
- `ix.mjs`: one engine pass per replay (every step). It records:
  - per-step diffs of items, consumable counters and gold, giving every purchase with its round, gold before and where it was made;
  - checkpoints every 50 rounds (max HP, gold, gems, earned, spent);
  - wards with terrain features, altar locks with context, teleports with walk distance (BFS), tribute channels, and stuns with the victim's channel.

  Consumable counters: `cons[0]` = teleport crystal, `cons[2]` = altar lock (`probe.mjs`).
- `ab.mjs`: one pass per fight dump. It records casts with their exact effect (damage, stun or heal in the same step), turn context, readiness, action sequences of champion-attack turns, shields, heals, stuns versus channels and Prism bag buckets.
- `run_par.py` (parallel runner reading a file list) and `common.py` (index with pbg14, engine stats, item codes).
- Aggregators: `agg_items.py`, `agg_extra.py`, `agg_openers.py`, `agg_tribs.py`, `agg_ab.py`.
- Outputs are in `C:/battlecode/cache/top2_items/`: `ix_all.jsonl`, `ab_all.jsonl`, `rep_items.txt`, `rep_extra.txt`, `rep_openers.txt` and `rep_ab.txt`. The full tables are there; this report quotes them.

**Item codes:** family letter (Monster, Power, Durability, Treasure, Jungle, Home, Bruiser) + stat letter (s strength, f focus, h health).
- Example: `Ps` = Power emblem/shard of strength.
- An emblem is 5 shards (150 gold). Power counts as 6 points of its stat. Bruiser counts 5 of its stat plus 1 of each other stat.
- The "first 3 emblems" are in completion order.

**Engine facts checked in replays** (they matter for the rules):
- **Locks are per team.**
  - In `00corners_06869e89` (IFish vs new team(4)), IFish's Vendetta locked altar (35,34) at r95 and new team(4)'s Ryth locked the same altar at r182.
  - Then *both* teams attacked it: new team(4)'s Vesper hit it 5 times at r191-198 to clear IFish's lock, and IFish cleared the other by r236.
- **Placing a lock cancels the other team's tribute even if that team has its own lock there.** In `00lost_world_5977a569`:
  - r302-306: IFish's Vendetta clears a lock with 5 attacks.
  - r307: it places its own lock and starts a 43-gem tribute.
  - r309: the enemy Marcella places a lock and the tribute is cancelled; the bag is unchanged.
  - r314-316: IFish clears that lock with 5 attacks (two bodies), and both bank at r319-320.
- **Five attacks by any bodies of the blocked team clear a lock.** pbg's Prism and Ryth cleared one in 3 rounds (`00quadrants_cc168b7a` r451-453), then the Prism re-banked 903 gems in a 91-round channel (r454-545).
- Tribute attempts against a locked altar appear as attacks on the altar tile.
- A stun cancels a tribute (`00gem_fields_3fc2330b` r558).

**Caveats:**
- **Readiness:** Vendetta's camp-kill cooldown resets are not seen, so her readiness is underestimated. Shields absorbing a whole hit can hide an attack ("A" needs a health loss).
- **Fight context** F means the body hit or was hit by an enemy champion in the last 2 rounds, or earlier this round.
- **Small samples:** coo's Prism (9 bodies), coo's Tavi (18), IFish's Varg (18) and pbg14 (25 games).
- **Correlation:** win rate by max-HP ratio is a correlation (gold lead and item power move together). Section 2.4 shows the build choice itself (HP per 100 gold), which is not income-driven.

## 2. Items

### 2.1 Build per team and champion (study team; full tables with opponents in `rep_items.txt` section 2)

| team | champion (bodies) | first three emblems (share of bodies) | long tail (emblems 4-8, most common) | shards (top) | first emblem, median round |
|---|---|---|---|---|---|
| pbg | Vesper (109) | **Ps>Ph>Dh 75** / Js>Bs>Bh 20 (pbg14) | Ps>Ps>Ph>Dh>Ps (62) | Ps 42, Dh 19, Ph 19, Bs 10, Bh 9 | r116 |
| pbg | Prism (116) | **Dh>Mf>Jh 88** | Hh>Bh>Bh>Bh>Bf (50) | Bh 46, Dh 12, Bf 11, Mf 11, Jh 10, Hh 9 | r297 |
| pbg | Marcella (101) | **Bs>Bh>Bf 89** | Bs>Bh>Bf>Bs>Bh (72) | Bs 35, Bh 32, Bf 30 | r179 |
| pbg | Heart of Ruin (89) | **Ph>Dh>Pf 51** / Jf>Bh>Dh 10 | Ph>Ph>Dh>Pf>Ph (15) | Ph 39, Dh 25, Pf 19, Bh 10 | r259 |
| pbg | Ryth (59) | Bh>Dh>Ps 23 (12 finish none) | Ps cycle | Ps 57, Bh 20, Dh 17 | r360 |
| pbg | Vendetta (45) | Ps>Ph>Dh 20 | Ps>Ps>Ph>Dh | Ps 34, Ph 19, Dh 17, Bs 15 | r470 |
| pbg14 | Vesper (24) | **Js>Bs>Bh 20** | Dh>Bs>Bs>Bh>Bh (19) | Bs 46, Bh 44 | r87 |
| pbg14 | Heart of Ruin (19) | Jf>Bh>Dh 10 | Bf>Bh>Bh>Bh>Bf | Bh 51, Bf 18, Jf 18, Dh 14 | r234 |
| pbg14 | Vendetta / Ryth | Js>Bs>Bh 6/11, Js>Bh>Dh 7/13 | Bs / Ps cycle | | |
| nyx | Vesper (100) | **Ps>Ph>Dh 91** | Ps>Ps>Ph>Dh>Ps (76) | Ps 50, Ph 26, Dh 24 | r100 |
| nyx | Prism (100) | **Dh>Mf>Jh 82** | Hh>Bh>Bh... | Bh 44, Dh 15, Mf 15, Jh 13, Hh 12 | r256 |
| nyx | Marcella (88) / Vendetta (64) | Bs>Bh>Bf 71 / Ps>Ph>Dh 46 | cycles | | |
| nyx | Heart of Ruin (100) | Mf>Dh>Tf 73 | Jf>Bf>Bf>Bf>Bf (40) | Bf 58 | r330 |
| ifish | Vesper (110) | **Ts>Bs>Dh 90** / Ts>Ms>Jh 17 | **Ps>Ps>Ps>Ps>Ps (78)** | **Ps 88** | r99 |
| ifish | Vendetta (110) | Th>Js>Bh 85 / Ms>Jh>Ps 17 | Dh>Bs>Bs>Bs>Bs (65) | Bs 54, Ps 17 | r203 |
| ifish | Heart of Ruin (110) | Th>Jf>Bh 76 / Mf>Jh>Pf 15 | Bh>Bh>Bh>Bh>Bh (35) | Bh 59, Pf 15 | r242 |
| ifish | Cassi + Issac (91) | Pf>Df>Bh 26 + Ts>Ps>Hh 19; **28 of 91 finish no emblem** | | Cassi Bh 42 Pf 29; Issac Ps 38 Ts 31 | r453-567 |
| ifish | Ryth (58) / Varg (18) | Bh>Dh>Ps 23 / Ms>Jh>Ps 14 | Ps cycle | | |
| cm | Vesper (106) | Ts>Js>Ps 95 | Dh>Bs>Bs>Bh>Bs (65) | Bs 50, Bh 22 | r179 |
| cm | Vendetta (106) / Heart of Ruin (106) | Th>Js>Ps 97 / Th>Jf>Dh 95 | Bs/Bh / Bf/Bh cycles | | r163 / r229 |
| cm | Tavi (87) / Marcella (70) | Ts>Dh>Ms 38, Bs>Dh>Ms 20 / Js>Dh>Bf 39 | Bs cycle | | r366 / r308 |
| coo | Vesper / Vendetta / Tavi | Ts>Js>Ds 76/70/12 | Bh>Ps>Ph>Ps>Ps | Ps 46-50, Ph 20-25 | r158-256 |
| coo | Heart of Ruin / Varg / Ryth | **Js>Mh>Ps** 74/42/35 | Dh>Ps>Ps>Ps | Ps 38-51 | r214-418 |
| pantheon | Vesper (105) | Ts>Js>Ps 30, Ts>Js>Dh 28 | Ps / Dh mix | Ps 60, Dh 25 | r170 |
| pantheon | Prism (105) | Mf>Jh>Pf 17, Mf>Pf>Jh 12 | **focus** | Pf 51, Ph 11 | r188 |
| pantheon | Heart of Ruin / Marcella | Jf>Dh>Pf 18 / Js-Jf>Dh>Ps-Pf | Pf / Ps cycles | | |
| pantheon | Willow (65) | Js>Ps; 20 of 65 finish no emblem | | Ps 57, Js 27 | r397 |

What the builds share:
- **Treasure:**
  - pbg (all versions) never buys it (0 Treasure emblems). Nyx buys it only as Heart of Ruin's third emblem (Mf>Dh>Tf; 0.16 per body).
  - IFish, cm, coo and Pantheon buy one as the **first** emblem on Vesper, and IFish and cm also on melee bodies (Th). It does not appear again in the first eight emblems.
- **The second and third emblems are almost always Jungle, Durability or Bruiser health.**
- **The long tail is a stat cycle:**
  - pbg and Nyx Vesper: 2 Power-strength, 1 Power-health, 1 Durability-health.
  - Bruiser cycles: pbg Marcella, cm, pbg14.
  - IFish's Vesper: Power-strength only.

### 2.2 Max HP, damage stat and gold over time (per body; S vs O; `rep_items.txt` sections 1, 2, 10, 11)

- Gold spent = earned x the spent/earned ratio.
- The damage stat per champion at r300 and r600 (strength, or focus for Prism, Cassi, Willow and Heart of Ruin) is in `rep_items.txt` section 2. The Vesper table below quotes it.

| team | grp | gold earned r300 / r600 / end | spent / earned | max HP r300 | r600 | r1000 | stat points str / foc / hp | deaths per body per 1000 alive rounds |
|---|---|---|---|---|---|---|---|---|
| pbg | S | 322 / 774 / 1,612 | 0.95 | **1,459** | **2,237** | **3,199** | 36 / 17 / **46%** | **1.56** |
| pbg | O | 291 / 726 / 1,471 | 0.94 | 1,287 | 1,805 | 2,425 | 48 / 22 / 31% | 2.29 |
| pbg14 | S | 360 / 852 / 1,683 | 0.94 | 1,436 | **2,290** | **3,362** | 35 / 22 / 44% | 1.43 |
| pbg14 | O | 295 / 704 / 1,363 | 0.96 | 1,302 | 1,751 | 2,243 | 50 / 20 / 29% | 2.39 |
| nyx | S | 272 / 630 / 1,584 | 0.93 | 1,335 | 1,920 | 2,839 | 35 / 22 / 43% | 1.58 |
| nyx | O | 251 / 621 / 1,488 | 0.94 | 1,339 | 1,869 | 2,495 | 44 / 25 / 31% | 1.92 |
| ifish | S | 310 / 757 / 1,472 | 0.96 | 1,246 | 1,585 | 2,042 | **69** / 10 / 21% | 2.38 |
| ifish | O | 300 / 712 / 1,511 | 0.95 | 1,313 | 1,899 | 2,882 | 41 / 22 / 38% | 2.51 |
| cm | S | 280 / 692 / 1,675 | 0.94 | 1,312 | 1,839 | 2,798 | 47 / 19 / 34% | 2.74 |
| cm | O | 290 / 683 / 1,668 | 0.94 | 1,346 | 1,936 | 2,807 | 36 / 29 / 35% | 2.29 |
| coo | S | 250 / 608 / 1,334 | 0.91 | 1,164 | 1,613 | 2,157 | 66 / 4 / 30% | 2.85 |
| coo | O | 292 / 703 / 1,612 | 0.94 | 1,372 | 1,894 | 2,631 | 42 / 26 / 32% | 1.58 |
| pantheon | S | 301 / 709 / 1,449 | 0.89 | 1,097 | 1,420 | 1,902 | 43 / 30 / 28% | 1.35 (recall spam) |
| pantheon | O | 291 / 713 / 1,497 | 0.93 | 1,348 | 1,923 | 2,571 | 46 / 19 / 35% | 2.21 |

The carry (Vesper):

| team | grp | Vesper max HP r300 / r600 / r1000 | strength r600 | HP per 100 gold by r600 | deaths / game |
|---|---|---|---|---|---|
| pbg | S / O | **1,984 / 3,505 / 5,341** vs 1,461 / 2,109 / 2,854 | 197 vs 225 | **165** vs 91 | **1.28** vs 2.06 |
| pbg14 | S / O | 1,892 / 3,577 / 5,623 vs 1,523 / 2,100 / 2,569 | 206 vs 231 | 163 vs 83 | 1.21 vs 2.09 |
| nyx | S / O | 1,883 / 3,060 / 5,004 vs 1,380 / 2,028 / 2,747 | 164 vs 173 | 183 vs 96 | 1.02 vs 1.73 |
| ifish | S / O | 1,415 / **1,522 / 1,583** vs 1,580 / 2,519 / 3,912 | **376** vs 194 | **37** vs 119 | 1.74 vs 1.88 (bag lost per death **60**) |
| cm | S / O | 1,081 / 1,631 / 3,018 vs 1,563 / 2,705 / 4,419 | 156 vs 191 | 57 vs 122 | 2.89 vs 1.58 |
| coo | S / O | 1,172 / 1,900 / 2,956 vs 1,431 / 2,162 / 3,333 | 169 vs 182 | 76 vs 111 | 3.03 vs 1.27 |
| pantheon | S / O | 1,123 / 1,545 / 2,152 vs 1,549 / 2,357 / 3,034 | 183 vs 217 | 57 vs 120 | 1.27 vs 1.98 |

- **pbg and Nyx Vesper:**
  - About the same strength as the opponents' Vesper (164-206 against 173-231 at r600), with 1.5-1.9 times the max HP.
  - They die 40% less, from the same gold (pbg's Vesper gains 165 HP per 100 gold; the opponents' 91).
- **IFish's Vesper is the opposite.**
  - Double strength (376 at r600), flat health of about 1,500 all game.
  - IFish surrounds it with five other bodies built to take hits: Heart of Ruin Bruiser-health (Bh 59%), Vendetta Bruiser-strength (Bs 54%), and Ryth opening Bh>Dh.

### 2.3 What changes the opener (runtime triggers)

- **pbg changed its bot at about 14:00 UTC.**
  - Games from 07-13h: Vesper Ps, Heart of Ruin Ph, Vendetta Ps, Ryth Bh. No Vesper opened Js before 14:00: 81 Ps, plus 3 Ms on 00road_of_riches.
  - From 14:00: Vesper Js 23/24, Heart of Ruin Jf 15/19, Vendetta Js 11/11, Ryth Js 10/13. Prism (Dh) and Marcella (Bs) are unchanged.
  - Results: 18-7 from 14:00 against 53-38 before.
  - The newest pbg is therefore "Jungle first, then the Bruiser cycle"; the Bruiser share is 8.3 emblems per body.
- **IFish opens Monster on six maps:** 01big_world, 00ambush, 00expanse, 01islands, 00rows and 00road_of_riches (Vendetta Ms, Heart of Ruin Mf, Issac Ms, Vesper Ts>Ms>Jh).
  - Elsewhere it opens Treasure, with no exception per map (agg_openers: "maps with mixed openers: {}").
  - Four of the six are among the largest maps in the pool: big_world, ambush, expanse and islands (3,600-10,000 tiles, spawn distance 51-90).
  - 00rows (2,500 tiles) and 00road_of_riches (1,600 tiles, 132 camps) are not large.
  - 01starvation, 00lanes and 01fracture are large but stay Treasure.
  - INFERRED: a map-derived farming signal (large or camp-rich maps where Monster's +10% camp damage pays). The exact feature is unknown.
- **pbg's alternatives:** pbg opens Monster only on 00road_of_riches (Vesper Ms, Marcella Ms, Heart of Ruin Mf, Prism Mf, Ryth Ms; all 3 games). 00road_of_riches is also the map where it uses 38 crystals a game (section 3.2).

### 2.4 Item power and outcome

Team max-HP ratio (S per-body mean / O per-body mean) and the study team's win rate:

| team | ratio r600 median | wins when ratio r600 >= 1.1 | 0.9-1.1 | < 0.9 |
|---|---|---|---|---|
| pbg | **1.26** | 73% (66) | 55% (29) | **8% (12)** |
| pbg14 | 1.37 | 75% (16) | 83% (6) | 0% (1) |
| nyx | 1.03 | 75% (36) | 45% (33) | 4% (25) |
| cm | 0.97 | 92% (38) | 62% (21) | 20% (45) |
| coo | 0.86 | 90% (20) | 61% (23) | 41% (54) |
| pantheon | 0.75 | 92% (12) | 71% (17) | 34% (71) |
| ifish | 0.88 | 76% (25) | 71% (21) | **51% (59)** |

- **MEASURED:** every team wins far more when ahead in max HP.
- **INFERRED:** part of this is income (gold lead leads to more items). The build part is the HP per 100 gold column of 2.2: pbg and Nyx get about 1.8 times the HP from the same gold.
- IFish is the only team that wins half its games while behind in HP, by damage (its Vesper does 13,220 champion damage a game against the opponents' Vesper 10,539).

### 2.5 Shopping

| team | grp | visits / body-game | gold before a visit (median) | shards per visit | visits while dead | first visit (median round) |
|---|---|---|---|---|---|---|
| pbg | S / O | 7.6 / 7.9 | **177** / 155 | **6.6** / 5.8 | 8% / 11% | r136 / r126 |
| ifish | S / O | 6.9 / 7.9 | 174 / 159 | 6.7 / 6.0 | 11% / 11% | r142 / r114 |
| pantheon | S / O | 7.8 / 7.7 | 130 / 153 | 5.4 / 5.9 | 7% / 10% | r104 / r128 |
| coo | S / O | 8.3 / 9.0 | 120 / 154 | 4.8 / 5.5 | 13% / 7% | r102 / r124 |
| cm | S / O | 9.4 / 8.3 | 144 / 160 | 5.5 / 6.2 | 10% / 10% | r128 / r127 |
| nyx | S / O | 10.2 / 8.0 | 132 / 153 | 4.8 / 5.8 | 5% / 8% | r106 / r130 |

- pbg and IFish shop in whole-emblem batches (6.6-6.7 shards per visit at about 175 gold).
- **Consumables are bought at the same visits as shards.** Gold before a lock purchase has a median of 15-18 gold, because the lock (10) is the last purchase of the visit: IFish 562 lock buys, Pantheon 807, coo 501, cm 983.
- 10-17% of lock purchases are made while dead.

## 3. Consumables

### 3.1 Altar locks (`rep_items.txt` section 5, `rep_extra.txt` section C)

| team | grp | placed / game | bought / game | own tribute at that altar within 3 r | no enemy within 8 | enemy carrier within 8 (mean max bag) | cleared by the enemy | median life | own banks while it stands (gems) | enemy attack turns spent per lock | cancelled an enemy tribute (largest bags) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cm | S | **5.56** | 9.27 | 63% | 51% | 144 (41) | 69% | 113 r | 3.68 (122) | 3.53 | 11 (200/200/200/133) |
| cm | O | 3.58 | 6.89 | 50% | 42% | 115 (50) | 76% | 79 r | 3.31 (108) | 3.88 | 53 (211/200/181/118) |
| pantheon | S | **4.22** | 7.69 | 42% | 52% | 108 (276) | 60% | 145 r | **5.28** (152) | 3.12 | 15 (632/521/463/434) |
| pantheon | O | 1.80 | 3.85 | 63% | 51% | 58 (81) | 71% | 100 r | 2.87 (150) | 3.59 | 13 (377/287/275) |
| ifish | S | **2.87** | 5.11 | 49% | 48% | 100 (131) | 76% | 94 r | 3.70 (148) | 3.92 | 10 (741/368/209/93) |
| ifish | O | 1.31 | 3.19 | 60% | 57% | 39 (278) | 49% | 178 r | 4.02 (175) | 2.43 | 8 (434/244/64) |
| coo | S | 1.13 | 4.96 | **83%** | 18% | 59 (125) | 62% | 74 r | 3.01 (170) | 3.20 | 18 (200/200/132/118) |
| coo | O | 2.76 | 5.64 | 46% | 35% | 110 (53) | 76% | 83 r | 3.24 (118) | 3.86 | 37 (408/200/200/200) |
| pbg | S | **0.00** | 0.00 | - | - | - | - | - | - | - | - |
| pbg | O | 2.16 | 4.44 | 52% | 49% | 92 (204) | 63% | 152 r | 4.02 (144) | 3.19 | **13 (841/741/521/491/368)** |
| nyx | S | 0.03 | 0.16 | - | - | - | - | - | - | - | 3 (400/400/30) |
| nyx | O | 1.90 | 3.97 | 61% | 37% | 75 (103) | 72% | 92 r | 3.24 (123) | 3.63 | 16 (332/275/275/202) |

**Who places them:**
- IFish: Vesper 114, Vendetta 90, Heart of Ruin 69.
- cm: Vendetta 187, Heart of Ruin 147, Vesper 136.
- Pantheon: Vesper 145, Marcella 96, Heart of Ruin 93.

The carriers place them, since they arrive to bank. Round quartiles: IFish r301/610/895, cm r310/584/912, Pantheon r199/488/868, coo r524/730/1000. Locks are a mid-to-late-game tool.

**Locks on locks:** 274 placements in 127 team-games went onto an altar that still held an uncleared enemy lock. This is consistent with per-team locks.

**Whose altar:** altars are neutral. 38-51% of the study teams' locks are on an altar nearer their own spawn (cm 38%, coo 44%, IFish 45%, Pantheon 51%), so about half are on middle or enemy-side altars.

**Other consumables:** the two other consumable counters were never bought by anyone in 584 games. Crystal and lock are the whole consumable game.

**How they use locks:**
- **Lock, then bank** at the same altar (42-83%). Examples:
  - IFish `00fragment_e1ff7810` r206: its Vendetta locks (15,24) with no enemy within 8. 8 own banks follow; the lock stands 1,260 rounds.
  - Pantheon `00fragment_a2a7ff19` r214: its Vesper locks; 15 own banks, standing 1,188 rounds.
  - cm `00ambush_1586d15b` r316: its Vendetta locks; 10 own banks, standing 966 rounds.

  INFERRED: the lock turns the team's banking altar into a private one. An enemy who wants it pays about 3.5 attack turns standing next to it. A lock does **not** protect your own channel from an enemy lock.
- **Cancelling a channel:**
  - IFish `00great_wall_3a46ed8d` r904: its Heart of Ruin cancels pbg's Prism 22 rounds into a 368-gem tribute.
  - IFish `01boss_battle_4b1716d2` r1359: its Vendetta cancels pbg's Prism's 741-gem tribute.
  - Pantheon `01gold_rush_2376a4f9` r1355: its Heart of Ruin cancels pbg's Prism's 521.
  - cm `00contest_c5fb4d6a` r1626 / r1978: 200-gem monolith bags.
  - Only 1-18 such cancels per team in 100+ games, but the bags are the largest in the game.
- **pbg never buys a lock**, so pbg's opponents can tribute anywhere safely from locks.

### 3.2 Teleport crystals (`rep_items.txt` section 7, `rep_extra.txt` section D)

| team | grp | uses / game | walk replaced by the 3-tile hop (median tiles) | unreachable on foot within 80 | lands within 3 of a camp | carrying gems (mean bag) | enemy within 6 at start |
|---|---|---|---|---|---|---|---|
| pbg | S / O | 4.53 / 2.88 | **54** / 25 | 48% / 43% | **86%** / 57% | 53% (72) | 13% |
| ifish | S / O | 4.76 / 4.74 | **65** / 29 | 60% / 50% | 85% / 61% | 44% (36) | 19% |
| coo | S / O | **7.67** / 4.46 | 25 / 15 | 22% / 17% | 54% / 56% | 63% (36) | 4% |
| pantheon / cm / nyx | S | 0.03 / 0 / 0 | - | - | - | - | - |

**By map** (uses per game, study team):
- pbg: 01shortcut 47, 00road_of_riches 37.7, 00reverse_spiral 27.7, 01fracture 22, 00pilgrimage 21.7, 01starvation 18.3; 0-1 elsewhere.
- IFish: 01shortcut 44.7, 00pilgrimage 36.3, 00road_of_riches 35.3, 01fracture 25, 01starvation 24.7, 00reverse_spiral 23.
- coo: 00great_wall 34, 00split 30, 00gemfight 23, 01shortcut / 01starvation / 01gold_rush 20, 00road_of_riches 18, 00quadrants 17, 01concentrated_wealth 15.

**Examples:**
- pbg on `00road_of_riches_0127165b` uses 31 crystals (the opponent 1). It hops from just outside its spawn, (19,25) to (22,22), 10 times, starting at r32.
- coo on `00gemfight_c80d2b6c` hops (24,24) to (21,21) from r36 on, replacing a 36-tile walk.

Every channel completed (99-100%), and 4-20% started with an enemy within 6.

**INFERRED:** the use is a precomputed "hop" table: a tile pair over a wall or hole, 3 apart, with a long walk between them, near the spawn exit or on the way to camps. It is bought on every spawn visit on such maps.

### 3.3 Wards (`rep_items.txt` section 6, `rep_extra.txt` section E)

| team | grp | wards per body per 100 alive rounds | first ward (median round) | in a bush | camp within 3 | altar within 3 | on the enemy half | enemy within 8 of the placer | median gap between a body's wards |
|---|---|---|---|---|---|---|---|---|---|
| pbg | S / O | 3.12 / 2.97 | r9 / r11 | 73% / 72% | 52% / 49% | 16% | **30%** / 18% | **51%** / 37% | 16 / 16 |
| pbg14 | S / O | 3.33 / 3.37 | r8 / r8 | 81% / 65% | 50% / 50% | 12% | 27% / 15% | 43% / 34% | 16 / 16 |
| ifish | S / O | 3.10 / 3.23 | r10 / r12 | 74% / 61% | 50% / 48% | 17% | 28% / 19% | 50% / 35% | 17 / 14 |
| pantheon | S / O | 1.75 / 3.34 | r19 / r13 | **100%** / 68% | 50% / 49% | 21% | 16% / 23% | 35% / 38% | 21 / 14 |
| coo | S / O | 2.84 / 3.45 | r12 / r9 | 68% / 62% | 67% / 57% | 14% | 18% / 21% | 35% / 38% | 27 / 13 |
| cm | S / O | **9.38** / 4.15 | **r1** / r7 | **6%** / 53% | 57% / 57% | 12% | 22% / 19% | 32% / 38% | **10** / 12 |
| nyx | S / O | 1.92 / 4.11 | r10 / r9 | **100%** / 55% | 42% / 54% | 15% | 21% / 19% | 36% / 39% | 24 / 12 |

- All teams place wards about 1.9 tiles from the placer, the 2-tile maximum. The placer stood in a bush only 1-10% of the time, so the ward goes **into** a bush next to the body.
- pbg and IFish ward more often while an enemy is within 8 (50-51%) and on the enemy half (28-30%).

## 4. Abilities (`rep_ab.txt`)

### 4.1 Use of ready slots by context

Cast share of the turns on which the slot was ready, by context:
- **F:** in a fight.
- **N:** enemy champion within 5, not fighting.
- **C:** working a camp.
- **O:** other (walking).

Selected rows; the full table is in `rep_ab.txt` section 1.

| team | slot | S: F / N / C | O: F / N / C | casts per 100 alive rounds S / O |
|---|---|---|---|---|
| pbg | Vesper reset | **52%** / 16% / 94% | 31% / 13% / 91% | 5.33 / 4.86 |
| pbg | Marcella damage | **48%** / 21% / 92% | 24% / 13% / 74% | 4.54 / 4.25 |
| pbg | Heart of Ruin shield | 61% / 27% / 42% | 51% / 20% / 33% | 5.02 / 5.35 |
| pbg | Heart of Ruin dash | **56%** / 32% / 62% | 37% / 22% / 63% | 9.77 / 8.70 |
| pbg | Ryth area stun | **46%** / 37% / 81% | 35% / 25% / 78% | 5.37 / 4.69 |
| pbg | Prism damage+stun / area | 31% / 19% / 70%; 51% / 26% / 81% | 29% / 20% / 58%; 44% / 17% / 73% | 4.78+5.29 / 3.95+4.24 |
| ifish | Heart of Ruin shield / dash | 65% / 30% / 39%; 51% / 33% / 49% | 62% / 20% / 34%; 46% / 23% / 54% | |
| ifish | Ryth area stun | **50%** / 44% / 89% | 41% / 36% / 76% | 5.49 / 4.96 |
| ifish | Cassi damage / stun | 41% / 29% / 98%; 35% / 21% / 34% | - | 5.33 / 4.49 |
| pantheon | Heart of Ruin shield / dash | 68% / 26%; **67%** / 29% | 53% / 18%; 44% / 23% | |
| pantheon | Vesper reset | 49% / 17% | 25% / 12% | |
| coo | Ryth area stun | 46% / 33% / 56% | 29% / 23% / 64% | |
| coo | Heart of Ruin shield / dash | **25%** / 5%; **40%** / 24% | 55% / 20%; 46% / 23% | 2.89 / 4.25 shields |
| cm | Heart of Ruin shield / dash | **73%** / 35%; 65% / 35% / 92% | 38% / 15%; 53% / 29% / 59% | 5.64 / 4.21 shields |
| cm | Marcella damage | **15%** / 13% / 93% | 38% / 23% / 76% | |
| nyx | Marcella damage | **62%** / 23% | 26% / 15% | |
| nyx | Heart of Ruin dash | 59% / **53%** / 43% / 50% (other) | 49% / 28% | 10.84 / 8.90 |

- **The study teams cast ready fight spells more often in fights than their opponents.** The exceptions are coo's Heart of Ruin and cm's Marcella.
- **On camps every team casts nearly every ready damage spell (70-98%).** Out of fights and away from camps the use is about 0%: spells are not wasted on travel. Dashes are the exception: 14-50% of ready "other" turns, i.e. travel.

### 4.2 Effects: champions vs camps

| spell | share of casts that hit a champion: study team (opponents) | share that hit a camp |
|---|---|---|
| Prism damage+stun | pbg 22% (23%), Nyx 30% (29%), Pantheon 23% (19%) | 70-81% |
| Prism area | pbg 23% (23%), Nyx 38% (29%), Pantheon 25% (16%) | 61-80% |
| Ryth area stun | pbg 38% (32%), IFish 33% (34%), coo 38% (33%) | 62-68% |
| Marcella damage | pbg 30% (27%), Nyx 41% (31%), Pantheon 38% (24%), cm 21% (37%) | 56-77% |
| Tavi damage+stun | cm 30% (36%), coo 54% (31%) | 46-70% |
| Cassi stun (IFish) | 24%; the other 76% show no champion effect | - |

- **Cassi's stun:** INFERRED cast on stunned or moving targets or camps. Camp stuns do not show as champion effects.
- **Heart of Ruin dash:**

  | dash class | share of dashes |
  |---|---|
  | travel | 33-52% |
  | camp strike | 20-40% (cm 40%) |
  | strike on a champion | 4-15% (Pantheon 15%) |
  | escape | 4-13% |

- **Vesper and Vendetta dashes:** travel 63-82%, engage 11-20%, escape 8-17%. pbg's Vesper engages 18% and escapes 10%; its opponents' Vesper 13% and 14%.

### 4.3 Champion-attack turns: resets and sequences

Letters: M move, D dash, A hit on an enemy champion, K killing hit, R attack reset, C other cast, r recall start.

| team | champion | attack turns / body-game | reset used when ready | top sequences |
|---|---|---|---|---|
| pbg | Vesper | 50.0 | 87% (O 83%) | A 55%, DA 13%, ARA 13%, **MRA 11%** |
| ifish | Vesper | 37.0 | 83% (O 86%) | A 48%, DA 14%, ARA 14%, **MRA 12%** |
| coo | Vesper | 61.0 | 80% (O 90%) | A 53%, MRA 13%, ARA 12%, DA 12%, AD 5% |
| cm | Vesper | 45.1 | 91% (O 88%) | A 57%, ARA 15%, MRA 10%, DA 10% |
| nyx | Vesper | 46.2 | **98%** (O 83%) | A 69%, ARA 26%, **MRA 0%** |
| pantheon | Vesper | 48.0 | 79% (O 80%) | Ar 49%, DAr 18%, MRAr 16% (r = recall spam) |
| coo | Tavi | 53.2 | 90% | A 51%, **MRA 20%**, CA 15% |
| pbg | Marcella | 23.8 | **93%** | A 24%, AM 20%, MA 18%, MARA 14% |
| pbg | Ryth | 23.8 | **91%** | AM 27%, A 20%, MA 15%, MARA 14%, ARAM 9% |
| ifish | Ryth | 24.0 | **95%** (O 81%) | AM 26%, A 19%, MA 17%, MARA 16% |
| nyx | Marcella | 28.5 | **51%** (O 75%) | AM 30%, A 26% |
| cm | Vendetta | 45.7 | **46%** (O 65%) | A 22%, MA 19%, MDA 16% |
| coo | Ryth / Vendetta / Varg | | 67% / 62% / 64% | |

- The reset is ready in only 25-45% of attack turns, because attack turns cluster in exchanges and the cooldown is 8.
- When it is ready, the top melee bodies double-hit in 90-97% of turns: ARA, MARA, ARAM. The exceptions are Nyx's Marcella, cm's and coo's Vendetta and coo's Ryth (46-67%).
- Ranged walk + reset + shot (MRA, or MRAr for Pantheon) is 9-20% of the attack turns of Vesper and Tavi, for every team except Nyx.

Examples:
- pbg Vesper MRA: `00ambush_3001d3f1` r500 body 9; `00collision_1189ede2` r615 body 1.
- IFish Vesper MRA: `00fragment_e1ff7810` r114 body 3.
- pbg Marcella MARA: `00contest_52dbafca` r27 body 8.
- coo Tavi MRA: `00ambush_00daddc2` r549 body 6.

### 4.4 Shields and heals

| team | Heart of Ruin shields / game | pre-emptive (no damage in the previous round) | enemy within 4 | hit within the next 5 rounds |
|---|---|---|---|---|
| pbg | 51.0 (O 55.2) | 40% (50%) | 31% | 50% |
| ifish | 51.9 (O 54.3) | 48% (47%) | 33% | 41% |
| pantheon | 51.5 (O 49.0) | 53% (44%) | 28% | 29% |
| cm | **59.5** (O 43.8) | 50% (46%) | 39% | 26% |
| nyx | 39.9 (O 52.0) | 41% (48%) | 46% | 31% |
| coo | **29.9** (O 46.4) | 42% (47%) | 32% | 60% |

- **Varg** (opponents): 39-139 shields a game. Some opponents shield on cooldown: IFish's opponents' Varg 139 a game, 81% pre-emptive.
- **Willow (Pantheon):** 25 heals a game on allies missing 506 HP (0.67 health). 22% of them during a fight. Opponents' Willow: 23-48 heals, 443-569 missing.

### 4.5 Stuns and channel cancels

Stuns per team-game on enemy champions:

| team | grp | stuns / game | by champion (per game) | victim died within 3 rounds | on tributing victims (all games, ix; largest bags) | on spam recalls* |
|---|---|---|---|---|---|---|
| pbg | S | **29.0** | Ryth 10.4, Prism 8.7, Heart of Ruin 5.3, Marcella 4.2 | 11% | 39 (711/549/288/200x4) | 910 |
| pbg | O | 19.9 | Ryth 6.5, Heart of Ruin 5.6, Marcella 2.7 | 9% | 14 (765/623/566/509/486/465) | 0 |
| ifish | S | 23.2 | Ryth 8.9, Cassi 7.8, Heart of Ruin 6.6 | 12% | 20 (623/486/370/202) | 548 |
| ifish | O | 26.3 | Ryth 8.5, Heart of Ruin 6.5, Marcella 4.8, Prism 4.3 | 10% | **50** (242/242/242/200...) | 0 |
| pantheon | S | 24.7 | Heart of Ruin 9.2, Prism 7.5, Marcella 4.5 | 11% | 7 | 304 |
| pantheon | O | 19.2 | Ryth 7.3, Heart of Ruin 4.8 | 8% | 26 (711/611/455/455/298) | **1,955** |
| coo | S | 22.1 | Ryth 10.9, Ren 3.6, Heart of Ruin 3.3, Tavi 2.5 | 7% | 30 (200/200/190/118) | 492 |
| coo | O | 28.3 | Ryth 10.0, Heart of Ruin 7.5, Marcella 4.4 | 15% | 36 (2,324/400/126) | 0 |
| cm | S | 24.1 | **Tavi 11.7**, Heart of Ruin 8.8, Marcella 3.6 | 12% | 23 (200x4/139) | 250 |
| cm | O | 32.4 | Ryth 15.3, Heart of Ruin 7.6, Marcella 4.9 | 12% | 41 (235/200/200/200) | 0 |
| nyx | S | 24.8 | **Prism 11.9**, Heart of Ruin 9.1, Marcella 3.8 | 8% | 32 (400/400/310/310/222) | 449 |
| nyx | O | 24.2 | Ryth 10.2, Heart of Ruin 6.1 | 7% | 19 | 0 |

\* **Recall spam:** recall spammers start a recall at the end of every turn and cancel it at the start of the next. Those stuns cancel nothing of value.
- The spammers are Pantheon (100% of bodies, 90 recall starts per 100 alive rounds), :3, EggsAfter11AM and EMPEROR Tung.
- pbg, IFish, coo, cm and Nyx never spam (0.8-1.5 per 100 rounds).
- Stuns on real (non-spam) recalls: 22-50 per 100+ games for each study team.

Examples:
- pbg Marcella stuns Pantheon's Vesper 40 rounds into a 711-gem tribute, and kills it at r560 (`00gem_fields_3fc2330b` r558-560).
- Opponents' Ryth stuns IFish's Vesper three times in one 242-gem banking attempt (`00lost_world_5977a569` r711, 719, 735).
- coo's Vesper tried to bank 2,324 gems (a 233-turn channel). It was stunned at r1108 and died at r1139 with the bag (`01boss_battle_ac23c263`). coo still won 1019-0.

### 4.6 Tribute channels: who gets interrupted (`agg_tribs.py`)

Interruption rate of tributes (stun, lock, death or self-cancel), by bag and by whether an enemy champion was within 6 at the start:

| team | grp | tributes / game | median bag | bag 1-49: enemy near / not | bag 50-149 | bag 150+ |
|---|---|---|---|---|---|---|
| pbg | S | 17.5 | 33 | 2% / 0% | 8% / 2% | **64% / 54%** (53 / 153) |
| pbg | O | 22.0 | 22 | 8% / 0% | 25% / 1% | 72% / 52% |
| ifish | S | 23.0 | 29 | 9% / 0% | 14% / 2% | 74% / 47% |
| pantheon | S | 27.5 | 21 | 7% / 0% | 22% / 2% | 57% / 36% |
| coo | S | 21.2 | 29 | 13% / 0% | 36% / 2% | 61% / 29% |
| cm | S | 26.1 | 22 | 15% / 0% | 31% / 6% | 67% / 8% |
| nyx | S | 22.1 | 29 | 23% / 1% | 56% / 6% | 82% / 47% |
| nyx | O | 23.4 | 30 | 11% / 1% | 49% / 1% | **97%** / 41% |

- A tribute of up to 49 gems with no enemy within 6 is never interrupted (0-1%).
- With an enemy within 6, interruptions run 2-24% at bag 1-49, 8-56% at bag 50-149 and 57-97% at 150+.
- Most interruptions are the tributer's own cancel when the enemy closes in ("cancel": pbg 100, Nyx 208, cm's opponents 105). Then come stuns, locks and deaths. INFERRED: the bots abort long channels under threat, so the channel time is lost either way.

### 4.7 Prism and the bag

Prism damage per champion-hitting cast, by carried bag:

| team | bag 0 | 25-49 | 50-99 | 100-199 | 200+ | share of alive rounds at 200+ |
|---|---|---|---|---|---|---|
| pbg S | 119 | 191 | 271 | 397 | **931** | 18% |
| pbg O | 168 | 256 | 341 | 450 | 759 | 10% |
| pantheon S | 174 | 270 | 321 | 487 | 754 | 13% |
| nyx S | 133 | 202 | 275 | 379 | 620 | 10% |
| ifish O | 168 | 281 | 308 | 509 | 948 | 14% |

- **Camp-hitting casts scale the same way** (pbg: 149 to 920). The largest hits are pbg's Prism with 584-778 gems: 1,777-2,310 per cast on Vesper, Heart of Ruin and Vendetta (`00packs_475b8b69` r1124-1427).
- **Bag 0 shows the build choice.** pbg's Prism does less than opponents' Prisms with no bag (119 against 168-174: focus shards skipped), and more with a bag.
- **pbg's Prism casts slightly less at 200+:** 8.1 casts per 100 rounds against 10.7 at bag 0.
- **It rarely fights:** champion-exchange rounds are 3.8% of its alive rounds, the same as the opponents' Prism.
- **Bag economy (ix):**

  | team | mean bag r400 / r600 / r1000 | tributes / game (mean gems) | mean bag lost per death | deaths with a bag of 100+ |
  |---|---|---|---|---|
  | pbg | 80 / 79 / 171 | 0.57 (322) | 35 | 16 in 116 games |
  | pbg14 | 107 / 81 / 215 | 0.80 (251) | 64 | 3 in 25 games |
  | nyx | 66 / 72 / 93 | 0.63 (157) | 37 | 24 in 100 games |
  | pantheon | 71 / 98 / 172 | 0.51 (253) | **99** | **33** |

## 5. Weak spots to exploit, per team

- **pbg (#1):**
  - It never locks (0 locks in 116 games), so our tributes are safe from it except through stuns (29 a game; Ryth 10.4, Prism 8.7).
  - Its Prism banks mean 322-gem bags (largest 903) in channels of bag/10 turns (25-91 rounds); 54-64% of its 150+ tributes get interrupted.
  - Its health build makes it hard to kill (Vesper 3,500 HP at r600).
  - **INFERRED:** contest its banking with locks and stuns rather than fights.
- **IFish (#2):**
  - Its Vesper is a glass cannon: about 1,500 HP all game, 37 HP per 100 gold, 60 gems lost per death. It does 13,220 champion damage a game.
  - IFish's tributes get stunned 50 times in 110 games (bags up to 242).
  - C&I is item-starved: 28 of 91 C&I bodies never finish an emblem, and they die 3.7 times a game.
  - **INFERRED:** burst its Vesper with a stun plus focus fire; never trade at range 3 with it.
- **Pantheon (#6):**
  - It spams recalls, and its Prism (focus build, low HP) dies with big bags: 99 gems per death, 33 deaths with a bag of 100+.
  - Its Willow is item-starved (17 HP per 100 gold).
  - It locks a lot (4.2 a game) to protect its banking altars.
- **coo and cm:**
  - Damage builds; they die 2.7-2.9 times per 1000 alive rounds against their opponents' 1.6-2.3. coo's Vesper dies 3.0 times a game and cm's 2.9.
  - Both drop locks on contested altars (cm 5.6 a game).
  - cm's opponents cancel cm tributes with locks 53 times (bags up to 211).
- **Nyx:**
  - A pbg-old clone in items, so it is tough.
  - It never locks, never walks + resets + shoots, and its Marcella uses the reset in only 51% of ready attack turns.
  - Its tributes with a bag of 50-149 and an enemy near are interrupted 56% of the time.

## 6. Notes on what g8 / god2 already has (code read, not changed)

- `Brain::shop()` (bots/g8/src/brain.cpp ~1486):
  - buys a teleport crystal first when islands or hops exist;
  - follows `build[]`;
  - buys a spare altar lock once the first emblem is done.
- `Brain::use_locks()` (~2111) locks an altar within 2 if an enemy is tributing there, or if it is an enemy-side altar without a lock.
- Hops: `nav.cpp` (`hop_min_save`).
- Wards: `place_ward()` (`ward_bush_maps`: bush wards only on lone-monolith maps).

The rules below say what to change in this machinery.

## 7. Rules for god2

All rules are written over observable state with thresholds. Stats, kits and passives come from the engine at runtime; nothing here is per-map or per-draft. Each rule carries its evidence and a confidence.

**R1. Health-weighted build on every body (high value, high confidence that it is the #1 team's choice).**
- **Target:** about 45% of stat points in health and about 55% in the kit's damage stat, from the second emblem on. The first emblem is the damage stat: pbg's Vesper Power-strength done at r116, or Jungle-strength at r87 in pbg14.
- **Generic order per body:**
  - **Damage-carry kit** (basic-attack ranged, high strength growth):
    - pbg/Nyx: `[D] Power-dmg`, then `Power-hp`, then `Durability-hp`, then cycle `Power-dmg, Power-dmg, Power-hp, Durability-hp`.
    - Newest pbg: `[D] Jungle-dmg`, then `Bruiser-dmg`, then `Bruiser-hp`, then `Durability-hp`, then cycle `Bruiser-dmg, Bruiser-dmg, Bruiser-hp, Bruiser-hp`.
  - **Melee frontliner** (high base HP): the Bruiser cycle `dmg, hp, focus` (Marcella), or Power-hp then Durability-hp then Power-focus (Heart of Ruin). Durability's -10% damage taken is taken once, early, on every body that fights.
  - **Ryth** (strength from bonus health): `Bruiser-hp, Durability-hp`, then Power-strength.
- **Guard:**
  - check `maxHp(r600)` against the visible enemies' mean;
  - if our team's per-body max-HP ratio is below 1.0 at a shop visit, the next emblem is health (g8's existing `build_react` insert can carry this).
- **Evidence:**
  - 46% health and +24% max HP per body at r600 for pbg against its opponents.
  - Vesper gains 165 HP per 100 gold against 91, and dies 1.28 times a game against 2.06.
  - Team ratio at r600 of at least 1.1 wins 73%; below 0.9 wins 8%. Nyx: 75% against 4%.
  - Damage builds (coo, cm, IFish) die 2.4-2.9 times per 1000 alive rounds.

**R2. No Treasure (medium confidence).**
- pbg (#1) never buys Treasure (Nyx almost never) and still out-earns its opponents: +10% gold per body, pbg14 +23%.
- If one Treasure is kept, it is only the first emblem of the bonus-gold kit (Vesper) and never again, which is IFish, cm and coo's pattern.

**R3. Prism holds the gems and buys health (high confidence; only when Prism is drafted).**
- **Build:** `Durability-hp, Monster-focus, Jungle-hp, Home-hp`, then Bruiser-hp cycling, with about 50% health shards. Do not buy focus shards beyond Monster-focus: at bag b, focus = base + growth·f + 1.5·b, so 100 gems = 150 focus = 19 focus shards (570 gold).
- **Bag:**
  - Carry 100-250 gems as a weapon: damage per cast is 119 at bag 0 and 931 at 200+.
  - Bank only when the bag is at least 250 AND no enemy champion is within 8, or when the gems are needed to finish the game (1000 - banked ≤ bag).
- **Avoid fights** when the bag is 200 or more and two or more enemies are within 6. A Prism death costs the bag: Pantheon loses 99 gems per Prism death.
- **Evidence:** Prism is in 100% of pbg, Nyx and Pantheon games; section 4.7 (bag scaling) and the Prism bag-economy numbers.

**R4. Cancel enemy big-bag tributes (high value, high confidence).**
- **Always carry one altar lock.** Buy it at every spawn visit when none is held: 10 gold, bought last in the visit.
- **Trigger:** a visible enemy champion is channelling a tribute (it stands within 1 of an altar and stays; the SDK channel state) with bag ≥ 50, i.e. 5 or more turns left.
- **Action:**
  - If we are within 2 of the altar: place the lock (cancels at once).
  - Else, if a stun kit is within its cast range (4 for unit stuns and Ryth's area stun; dash 2 + landing radius 1 for Heart of Ruin; most stun spells exclude walking, Cassi's does not): stun the tributer.
  - Else, if we can reach lock range or stun range before `ceil(bag/10)` minus the rounds already channelled run out: go.
  - Then attack the carrier, since the kill takes the bag.
- **Priority:** the bag is the value, so 200+ gems beats any farm target within 15 tiles.
- **Evidence:**
  - With an enemy within 6, 150+ tributes are interrupted 57-97% of the time.
  - Locks cancelled pbg Prism tributes of 368-841 gems, and Pantheon's locks cancelled opponents' tributes of 434-632 gems (section 3.1).
  - The 711-gem kill in `00gem_fields_3fc2330b` r558-560.

**R5. Safe banking for our own carriers (high confidence).**
- **Never start a tribute with bag ≥ 50 while an enemy champion is within 6.**
  - Bag 50-149: interrupted 8-56% with an enemy near, against 0-6% with nobody near.
  - Bag 150+: 57-97% with an enemy near, against 8-60% with nobody near (the channel outlasts the quiet).
- **Bag 1-49 is safe** (0-1% interrupted without an enemy near): bank it immediately when passing an altar.
- **If the bag is above 150, look 8 tiles out before starting**, because the channel lasts bag/10 turns. Prefer the altar farther from enemies even if it is 4-6 tiles longer.
- **Do not count on our own lock to protect the channel.** Locks are per team, and an enemy lock still cancels.

**R6. Lock the altar we bank at when it is contested (medium value, medium confidence).**
- **When:** our carrier reaches an altar to bank, with at least one enemy champion within 10, or the altar is nearer the enemy spawn. Place our lock first (IFish, cm, coo, Pantheon: 42-83% of their locks precede an own tribute within 3 rounds).
- **What it buys:** the altar becomes ours for a median of 74-145 rounds, covering 3-5 own banks. Enemies who want it spend about 3.5 attack turns next to it.
- **Who:** the carrier places it. Expect 1-5 a game from about r300.

**R7. React to enemy locks (medium confidence).**
- If our target altar holds an enemy lock:
  - if another altar is at most 6 steps farther, go there;
  - otherwise clear it with 5 attacks. Two bodies clear it in 3 rounds (`00quadrants_cc168b7a` r451-453).
- Never start a tribute into an enemy lock. The attempt becomes an attack anyway, but our channel would be lost if they re-lock.

**R8. Use ready spells in fights (medium confidence on the size).**
- **Fight rate:** in a fight (hit or hit by an enemy champion in the last 2 rounds), cast a ready damage spell, area stun or Heart of Ruin dash in at least 50% of ready turns. Study teams: Heart of Ruin dash 51-67%, Ryth stun 44-50%, Marcella damage 48-62%, Vesper reset 48-59%. Opponents: 24-53%.
- **Camps:** keep casting ready damage spells on camps (70-98%). Never cast on travel except dashes.
- **Melee reset:** in contact, when the reset is ready, do attack-reset-attack before any step: at least 90% for Marcella and Ryth on the top teams.
- **Ranged reset:** a ranged reset kit with the target at range+1 does walk-reset-shoot (9-20% of the top Vesper and Tavi attack turns).

**R9. Stun priority (medium confidence).** In order:
1. An enemy channelling a tribute with bag ≥ 20 (R4).
2. An enemy Prism carrying 100 gems or more: its next cast does 400-2,300.
3. A non-spam recall channel: a body that has not started a recall in each of its last 3 turns.
4. The enemy we can kill within 3 rounds.

Ignore recall spammers' channels: they were 1,955 of the stuns that landed on Pantheon.

**R10. Teleport crystals on hop maps (medium value, high confidence in the pattern).**
- **At init:** list hop pairs (A, B), with both tiles passable, Chebyshev distance 3 or less, walk(A, B) - 3 turns ≥ 6, and B not a camp tile.
- **Keep the hops** that lie within about 5 of our spawn exit or on the walk to a camp group or altar we use.
- **On such maps,** buy one crystal at every spawn visit. Use it when the route passes A and no enemy is within 4 (the channel is only stopped by stun or death).
- **Evidence:** pbg, IFish and coo use 4.5-7.7 a game, up to 45 a game on 01shortcut, and none on non-hop maps. Hops replace walks of 54-65 tiles; 85-93% land within 3 of a camp.

**R11. Wards (low-medium value).**
- Place the ward on every charge **if** a bush tile within 2 exists outside our current vision.
- Choose by: a bush adjacent to a camp group we farm or contest (about 50% of top wards are within 3 of a camp), then a bush on the enemy side of us (28-30% for pbg and IFish), then any.
- Expect about 3 per body per 100 rounds, the first by about r10.
- **Do not** drop wards on every charge in the open. cm is the only team that does it (9.4 per 100 rounds, 6% in bushes), and nothing here shows it helps.

**R12. Map-derived opener (low confidence).**
- **Default first emblem: Jungle in the damage stat.** It is the newest #1 bot's default (-30% damage from camps while farming; 18-7 since 14:00), then go to R1's cycle.
- **Monster first for melee farmers** only on large, low-contact maps (IFish: big_world, ambush, expanse, islands; the proxy area ≥ 3,600 and spawn distance ≥ 50 also picks starvation, lanes and fracture, where IFish does not). Try it as a ladder A/B, not a default.

## Appendix: reproduce

```
python tools/top2/items/run_par.py 3 C:/battlecode/cache/top2_items/ix_all.jsonl C:/battlecode/cache/top2_items/list_all.txt tools/top2/items/ix.mjs
python tools/top2/items/run_par.py 3 C:/battlecode/cache/top2_items/ab_all.jsonl C:/battlecode/cache/top2_items/list_dumps.txt tools/top2/items/ab.mjs
python tools/top2/items/agg_items.py   C:/battlecode/cache/top2_items/ix_all.jsonl   (> rep_items.txt)
python tools/top2/items/agg_extra.py   C:/battlecode/cache/top2_items/ix_all.jsonl   (> rep_extra.txt)
python tools/top2/items/agg_openers.py C:/battlecode/cache/top2_items/ix_all.jsonl   (> rep_openers.txt)
python tools/top2/items/agg_tribs.py   C:/battlecode/cache/top2_items/ix_all.jsonl
python tools/top2/items/agg_ab.py      C:/battlecode/cache/top2_items/ab_all.jsonl   (> rep_ab.txt)
```
