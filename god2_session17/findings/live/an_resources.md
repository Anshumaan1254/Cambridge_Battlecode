# Resources vs the top 10: gold, items, shopping, banking, recalls (Oct 23)

Our side is HouseOfCoders against the top-10 teams of `lists/top10_oct23` (IC, prism best girl, procless, Univardisty, new team(4),
Pantheon, policy wonk, :3, EMPEROR Tung, Trzy Kwaterki). Every game is on engine 1.0.3.

**Data**
- **Compact summaries** (item names, buys with the gold before each purchase, emblem completions, gold and gem timelines per champion):
  - **NEW**: 367 games of ours vs the top 10 (bb4 v50 set `bb4D` + v52 set `ft52D`, Oct 22 20:50-24:00 UTC) and 405 top-vs-top games
    (Oct 23 04-06 UTC).
  - **ALL** adds 140 games of ours (v11-ab3, Oct 22 13-20 UTC) and 520 top-vs-top games (Oct 22 07-12 UTC). The patterns match, so
    the tables use NEW unless marked.
- **Replays**, for timing: 200 `rp_bb4D` + 192 `rp_ft52D` (ours vs the top 10; 392 games, 1,767 of our bodies) and 219 `rp_top`
  (top vs top; 2,043 bodies). They give per-round gold, max HP and items, and the shop, recall, tribute, capture and death events.
- **Group labels**: OURS = our side. OPP = the top team in those same games. TOP = both sides of top-vs-top games, split into
  TOPW (winners) and TOPL (losers). We win 11% of NEW games.
- **v50 and v52 agree.** I checked every replay metric on `ft52D` (v52, the live bot) alone; it matches unless noted.
- **Tools** (new, read-only analysis):
  - `tools/live/res_compact.py` (writes `rc.json`) -> `res_report.py`, `res_compact2.py`, `res_routing.py`, `res_shop.py`, `res_builds.py`
  - `tools/live/res_replay.mjs` (through par.py) -> `res_replay_agg.py`, `res_recalls.py`, `res_banks.py`, `res_bankvia.py`
  - `tools/live/res_routeopp.mjs` -> `res_routeopp_agg.py`
  - All outputs are in `C:/battlecode/cache/an_resources/` (`*.txt`, `rr_*.jsonl`, `ro_*.jsonl`, `rc.json`).

## TL;DR
1. **Income is the gap. Conversion is not.**
   - **Totals:** we earn 3.5 gold/round against their 7.8 (4,091 vs 8,731 a game).
   - **Where the 4,640-gold gap comes from:**
     - **66%:** capture count. We make half the captures (31.7 vs 60.4 a game).
     - **12%:** gold per capture, 107 vs 116.
     - **12%:** kill gold.
     - **10%:** Marcella's tribute gold.
   - **Conversion is already efficient:** we spend 97% of what we earn (they spend 90-93%) and hold 12-18 gold per body; they hold
     28-103. **Unspent gold is not a problem.**
2. **Our melee bodies keep up. Our Vesper and Marcella do not.**
   - **Melee:** our Vendetta, Heart of Ruin and Ryth earn about what theirs earn and have equal or higher max HP until r300-400.
   - **Vesper at r300:** ours has earned 190 gold, against 421 for OPP and 489-609 for TOP/TOPW. It has 0.8 emblems against 2.0-3.1,
     and 5 strength + 1 health shards against 9-13 + 4-6. Its max HP is 1,082 against 1,384-1,567 (1,314 against 2,018-2,394 at r600).
   - **Marcella at r300:** ours has earned 153 against 390-449.
   - **Not explicit routing.** Our Vesper takes a similar share of our captures (24% vs 21-28%), and top teams also often leave
     rewards to others when their Vesper is near.
   - **Why their carries get more:**
     - The whole team earns 1.6-2x.
     - Their Vesper dies 1.2-1.6 times a game; ours dies 2.5 times.
     - Their Marcella takes the big rewards: 17-22 gems per collection against our 9.9.
     - Their Marcella banks 5-7.5 times a game (2 gold per gem), against our 2.1.
3. **Builds: Treasure everywhere, too little Durability.**
   - **Our build:** we buy the IC / procless order on every body (Treasure first, then Jungle, then Bruiser) in 54-72% of games. Treasure
     is 15.5% of our shards against 6.2-6.4% for theirs; Durability 4.2% against 8.6-10.4%; Power 12.5% against 22.7-23.3%.
   - **Treasure does not pay for us:** on our income the Treasure emblem returns a median of 56-138 gold over the rest of the game, and in
     26-51% of cases less than the 60 gold of extra stats a Bruiser emblem gives. Theirs returns a median of 140-316.
   - **#2 skips it:** prism best girl (#2) never buys Treasure (Power / Durability / Bruiser health).
4. **Banking: we bag-carry home and bank from spawn.**
   - **Via spawn:** 66% of our tributes come after a recall home (68% in v52). For top teams it is 37-41%.
   - **Timing and distance:** median capture-to-tribute is 20 rounds for us against 11-14. Capture-to-altar distance is 16 tiles against
     10-11. We bank within 8 tiles of the last capture in 22% of tributes; they do in 39-52%.
   - **Their direct banks:** about 36-gem bags, 6-9 rounds after the capture, 7-8 tiles away.
   - **What it costs:** tempo and walking, not gems. Gems lost on death per body are the same (21 vs 20), and top-vs-top teams leave a
     similar share of their gems unbanked at the end (15% vs our 16%).
5. **Shopping is fine.**
   - **Same pattern as theirs:** 75-78% of visits come right after a recall in both, 6-9% while dead. Our first shard visit is at r126
     against r123.
   - **Gap = income:** we visit every 92 rounds against 81 and buy 4.7 shards a visit against 6.4, only because of income.
6. **Recalls are the same as theirs, except a trick used by 3 teams.**
   - **Same count:** we complete 8.3 recalls per body per game (0.74 per 100 rounds); IC, prism best girl, procless and five others
     complete 7.4-10.4. The purpose mix is similar.
   - **The trick:** Pantheon, :3 and EMPEROR Tung start a recall at the end of every turn and cancel it at the start of the next
     (~800-980 starts per body per game). Every idle 5-turn stretch takes them home. They complete 20-32 recalls per body per game,
     6.8-9.4 of them by r300 (we complete 2.4).

## 1. Gold

Team sums (NEW). OURS and OPP are the same 367 games; TOP is 405 games (810 sides).

| | OURS | OPP | TOP | TOPW | TOPL |
|---|---|---|---|---|---|
| earned r100 | 254 | 370 | 374 | 411 | 337 |
| earned r200 | 563 | 861 | 852 | 965 | 740 |
| earned r300 | 918 | 1,440 | 1,396 | 1,602 | 1,190 |
| earned r600 | 2,090 | 3,707 | 3,449 | 4,112 | 2,786 |
| of which kills, r100 / r300 / r600 | 29 / 122 / 295 | 49 / 196 / 510 | 37 / 145 / 360 | 46 / 194 / 495 | 28 / 97 / 224 |
| of which Marcella tribute gold, r300 / r600 | 5 / 15 | 54 / 165 | 48 / 127 | 56 / 146 | 40 / 107 |
| captures (the rest), r600 | ~1,780 | ~3,030 | ~2,960 | ~3,470 | ~2,455 |
| held (unspent) r100 / r300 / r600 / r800 | 52 / 69 / 79 / 83 | 122 / 193 / 315 / 378 | 127 / 179 / 264 / 281 | 144 / 203 / 321 / 345 | 111 / 155 / 206 / 217 |
| held per champion, mean over r0-300 / r300-600 / r600+ | 12 / 17 / 18 | 28 / 52 / 103 | 28 / 49 / 67 | 31 / 58 / 88 | 24 / 40 / 46 |
| spent / earned | 0.97 | 0.90 | 0.93 | 0.92 | 0.95 |
| gold per round (whole game) | 3.47 | 7.83 | 6.50 | 8.15 | 4.84 |
| captures per game (per 100 rounds) | 31.7 (2.80) | 60.4 (5.47) | 52.7 (4.89) | 60.3 (5.59) | 45.1 (4.18) |

- **Whole-game gap decomposition** (per game): ours 4,091 gold against OPP 8,731.
  - **Capture count:** (60.4 - 31.7) x 107 = **3,070 (66%)**. This is farming and contest, outside this topic.
  - **Gold per capture:** 107 against 116 (TOP 113, TOPW 120) = **540 (12%)**. The camps taken and the carry bonus.
  - **Kill gold:** 650 against 1,196 = **546 (12%)**.
  - **Marcella's tribute gold:** 42 against 522 = **480 (10%)**. OPP drafts Marcella in 81% of these games, we do in 34%. Per game with
    Marcella it is ~640 against ~124.
- **Unspent gold.** We convert faster than anyone. The top teams keep a buffer of 30-100 gold per body; OPP bodies die holding 109 gold
  on average against our 23 (replays). That costs them nothing, because dead champions can shop.

## 2. Who earns: carries and reward routing

Shares of the team total, ALL compact games (`res_routing.py`). The fair share is 1/bodies (~22%).

| type | grp | games | captures % | gems collected % | gems banked % | gold % | tributes/game | bag |
|---|---|---|---|---|---|---|---|---|
| Vesper | OURS | 470 | 20.7 | 18.1 | 19.1 | 22.8 | 2.9 | 28 |
| Vesper | OPP | 483 | 23.3 | 22.3 | 22.2 | 25.7 | 6.0 | 36 |
| Vesper | TOP / TOPW | 1,763 / 880 | 24.5 / 25.6 | 25.3 / 27.4 | 26.1 / 27.7 | 28.5 / 30.1 | 5.0 / 6.6 | 40 / 43 |
| Marcella | OURS | 184 | 17.4 | 14.6 | 13.7 | 20.0 | 2.2 | 28 |
| Marcella | OPP | 413 | 25.4 | 31.8 | 32.4 | 35.3 | 7.5 | 42 |
| Marcella | TOP | 1,456 | 24.7 | 27.5 | 28.9 | 31.6 | 5.4 | 40 |
| Prism | OURS | 25 | 14.7 | 5.6 | 5.9 | 10.5 | 1.0 | 21 |
| Prism | TOP | 522 | 25.0 | 25.9 | 15.3 | 20.6 | 0.7 | **207** |
| Vendetta | OURS / TOP | 476 / 1,097 | **27.2** / 23.5 | 28.0 / 23.6 | 27.3 / 23.8 | 29.0 / 22.2 | 3.8 / 5.2 | 33 / 37 |
| Heart of Ruin | OURS / TOP | 507 / 1,391 | **27.2** / 21.3 | 25.7 / 18.9 | 24.6 / 19.3 | 24.8 / 17.8 | 3.6 / 4.5 | 32 / 32 |

**Gems per collection.** Marcella: 21.6 (OPP) and 17.3 (TOP) against our 9.9. Vesper: 15.5-16.4 against our 12.5. Their carries take
the big rewards.

**Is it explicit routing?** Mostly not (`res_routeopp.mjs`: 67 of our games, 73 top-vs-top games; captures that pay gems):

| | OURS | OPP | TOP |
|---|---|---|---|
| captures (with gems) per side-game | 22.0 | 43.6 | 38.3 |
| captures taken by Vesper (games with Vesper) | 24.3% | 21.4% | 28.2% |
| others' captures with our Vesper alive within 2 / 4 / 6 tiles | 2.5 / 8.6 / 18.7% | 8.0 / 20.0 / 31.1% | 9.1 / 18.5 / 29.1% |
| Vesper bonus left to others within 4 tiles (gold per Vesper game) | 71 | 257 | 165 |
| captures taken by Marcella (games with Marcella) | 18.2% | 26.6% | 24.0% |
| Marcella bank gold left to others within 4 tiles (per Marcella game) | 77 | 248 | 168 |
| captures with an ally waiting on the tile | 3.2% | 9.6% | 11.2% |

What this shows:
- **Their Vesper's 2x gold has four sources:** the team's 1.6-2x income, a few points more capture share, bigger rewards, and fewer
  deaths (Vesper deaths per game: ours 2.5, OPP 1.2, TOP 1.6; all our bodies die ~1.7x as often, 2.4 vs 1.4 per body).
- **Top teams are not careful routers either:** their Vesper or Marcella is next to 18-20% of the other bodies' captures and lets
  them go.
- **We have little to route:** our bodies spread out, so our Vesper is within 4 tiles of only 8.6% of the other bodies' captures.
  Routing would recover about 70 gold per Vesper game and 77 per Marcella game.

**Marcella.** OPP's Marcella banks 318 gems a game, which is ~640 gold from her passive. Ours banks 62 gems (~124 gold): she collects small
rewards and banks 2.1 times a game.

**Per type** (NEW compact; earned gold r300 / r600, first and third emblem as median rounds, shards by r300):

| type | OURS | OPP | TOP |
|---|---|---|---|
| Vesper | 196 / 459, r258 / r525, 5.6 | 408 / 991, r200 / r419, 11.4 | 485 / 1,182, r152 / r334, 13.7 |
| Marcella | 160 / 393, r286 / r583, 4.5 | 433 / 1,165, r169 / r363, 12.4 | 400 / 992, r177 / r377, 11.5 |
| Vendetta | 267 / 606, r218 / r453, 7.9 | 265 / 747, r234 / r464, 7.3 | 289 / 747, r215 / r464, 8.5 |
| Heart of Ruin | 252 / 565, r215 / r480, 7.5 | 289 / 731, r224 / r450, 8.0 | 234 / 565, r258 / r509, 6.4 |
| Ryth | 157 / 347, r292 / r625, 4.6 | 218 / 562, r290 / r549, 6.0 | 188 / 485, r283 / r586, 5.3 |

## 3. Items

**Shards per champion.** r150: ours 2.4 against OPP 3.2, TOP 3.3. r300: 6.0 against 8.7 and 8.6. r600: 14.6 against 23.9 and 23.0.
Team first emblem (median round): r130 for us, r99 for OPP, r83 for TOPW.

**Shard shares (NEW):**

| family / stat | OURS | OPP | TOP | TOPW | TOPL |
|---|---|---|---|---|---|
| Treasure | **15.5** | 6.2 | 6.4 | 5.4 | 8.0 |
| Jungle | 9.7 | 6.4 | 7.0 | 5.7 | 9.0 |
| Bruiser | 58.1 | 51.9 | 47.9 | 52.3 | 40.6 |
| Durability | **4.2** | 8.6 | 10.4 | 9.1 | 12.5 |
| Power | **12.5** | 22.7 | 23.3 | 22.9 | 23.9 |
| Monster | 0 | 3.2 | 3.7 | 3.3 | 4.3 |
| Home | 0 | 0.9 | 1.4 | 1.3 | 1.7 |
| Health / Strength / Focus | 38.7 / 46.4 / 14.9 | 40.5 / 44.6 / 14.9 | 37.6 / 46.7 / 15.8 | 37.0 / 47.7 / 15.3 | 38.5 / 44.9 / 16.6 |

**Health share is the same (~38-40%).** The difference is the passives: Treasure on every body for us, Durability and Power stacks for them.
Our Vesper's shards are 20% health against 23-26% for theirs.

**First three emblems** (ALL compact, `builds.txt`). Our build is identical in every game:
- Vesper and Tavi: Treasure-str > Bruiser-str > Durability-hp (62%).
- Melee: Treasure-hp > Jungle (damage stat) > Bruiser-hp (54-72%).

The top teams each have their own build:

| team | Vesper | melee (Vendetta / HoR / Ryth / Marcella) | Prism |
|---|---|---|---|
| IC (#1) | Ts > Bs > Dh 85% | Th > Js > Bh; Ryth Bh > Dh > Ps | - |
| prism best girl (#2) | **Ps > Ph > Dh 86%** | Vendetta Ps > Ph > Dh; HoR Ph > Dh > Pf; Ryth Bh > Dh > Ps; Marcella Bs > Bh > Bf 91% | **Dh > Mf > Jh 80%** |
| procless, EMPEROR Tung | Ts > Js > Bh | Th > Js > Bh (79-91%) | - |
| :3 | Jh > Ts > Ms | Jh > Th > Mh; HoR Jf > Tf > Mf | Dh > Tf > Mf |
| new team(4) | Ts > Dh > Ps | Vendetta Ts > Dh > Js; Ryth / Marcella Js > Dh > Ts; HoR Jf > Dh > Tf | - |
| Pantheon | Js > Ps > Ps | Js > Ps > Dh | Mf > Pf > Jh |

**Treasure payback** (gold its +20% returned after completion, all games; a Bruiser emblem in its place would give 60 gold of extra stats):

| type | ours: done / median return / under 60 gold | top: done / median return / under 60 gold |
|---|---|---|
| Vesper | r252 / 92 / 40% | r221 / 196 / 19% |
| Vendetta | r227 / 138 / 26% | r242 / 215 / 12% |
| Heart of Ruin | r215 / 110 / 30% | r290 / 162 / 18% |
| Ryth | r288 / 76 / 43% | r287 / 180 / 17% |
| Marcella | r298 / 85 / 41% | r228 / 316 / 11% |
| Varg | r329 / 56 / 51% | r303 / 184 / 16% |
| Tavi | r301 / 75 / 42% | r302 / 140 / 29% |

**Max HP and stat points over time** (replays, per body; OURS 1,767 bodies in 392 games, OPP 1,823, TOP 2,043 in 219 games):

| | OURS | OPP | TOP | TOPW |
|---|---|---|---|---|
| maxHp r100 / r200 / r300 | 1,141 / 1,253 / 1,369 | 1,083 / 1,222 / 1,390 | 1,068 / 1,191 / 1,347 | 1,069 / 1,211 / 1,399 |
| maxHp r400 / r600 / r800 | 1,492 / 1,739 / 2,004 | 1,602 / 2,082 / 2,606 | 1,515 / 1,936 / 2,363 | 1,594 / 2,099 / 2,640 |
| stat points (str/foc/hp shards) r300 | 2/1/3 | 4/2/4 | 4/2/3 | 5/2/4 |
| stat points r600 | 7/3/7 | 12/5/11 | 12/5/10 | 15/6/11 |
| emblems by r300 / first emblem (median round) | 0.90 / r309 | 1.40 / r240 | 1.38 / r246 | 1.66 / r224 |
| **Vesper** maxHp r300 / r600 | **1,082 / 1,314** | 1,384 / 2,018 | 1,458 / 2,150 | 1,567 / 2,394 |
| Vesper str/foc/hp shards r300; r600 | 5/0/1; 12/1/3 | 9/0/4; 24/1/10 | 10/0/5; 29/2/12 | 13/1/6; 38/3/14 |
| Vesper emblems by r300 | 0.81 | 2.01 | 2.41 | 3.13 |
| **Marcella** maxHp r300 / r600 | 1,537 / **1,906** | 1,733 / 2,872 | 1,607 / 2,475 | 1,701 / 2,780 |
| Heart of Ruin maxHp r300 / r400 / r600 | **1,491** / 1,668 / 1,976 | 1,368 / 1,573 / 2,067 | 1,294 / 1,441 / 1,850 | 1,327 / 1,499 / 2,001 |
| Vendetta maxHp r300 / r400 / r600 | 1,505 / 1,663 / 2,031 | 1,436 / 1,657 / 2,199 | 1,449 / 1,619 / 2,039 | 1,529 / 1,713 / 2,198 |
| Ryth maxHp r300 / r400 / r600 | 1,532 / 1,634 / 1,857 | 1,568 / 1,766 / 2,180 | 1,500 / 1,651 / 2,067 | 1,541 / 1,725 / 2,234 |

## 4. Shopping

| per champion (NEW compact; ALL for the visit-size rows) | OURS | OPP | TOP | TOPW | TOPL |
|---|---|---|---|---|---|
| visits / game (per 100 rounds) | 6.6 (0.56) | 8.7 (0.78) | 8.1 (0.74) | 9.0 (0.82) | 7.2 (0.66) |
| visits by r300 | 1.79 | 2.02 | 2.04 | 2.17 | 1.91 |
| gold before a visit, median (mean) | 127 (146) | 166 (208) | 153 (192) | 165 (212) | 138 (166) |
| shards per visit / r<=300 | 4.7 / 3.6 | 6.4 / 4.4 | 5.9 / 4.2 | 6.5 / 4.5 | 5.1 / 3.9 |
| visits with 5+ shards | 38.5% | 56.6% | 51.8% | 57.1% | 45.0% |
| rounds between visits (median) | 92 | 81 | 84 | 80 | 91 |
| first shard visit (median round) | 126 | 123 | 122 | 118 | 128 |
| visits while dead / spend while dead | 6.6% / 4.0% | 7.1% / 5.3% | 8.5% / 5.9% | 5.6% / 4.0% | 12.2% / 8.9% |
| Teleport Crystal buys / champion | 0.82 | 1.40 | 1.12 | 1.37 | 0.87 |
| Altar Lock buys / champion | 0.84 | 0.82 | 0.89 | 0.84 | 0.94 |

**How bodies get to the shop** (replays): via a completed recall 78% (ours) against 74% (OPP, TOP); while dead 6% against 7-9%; walking
4% against 4-5%; remote (Tavi) 12% against 13-14%. **Same mechanics.** Shopping logic (`Brain::shop()`, `home_trip()`, `shop_trip()`) needs
no change.

## 5. Banking

| | OURS | OPP | TOP | TOPW | TOPL |
|---|---|---|---|---|---|
| tributes / team-game (per 100 rounds), compact NEW | 12.9 (1.19) | 26.2 (2.55) | 19.3 (1.92) | 24.5 (2.46) | 14.0 (1.38) |
| mean / median bag | 31.0 / 22 | 37.5 / 26 | 38.6 / 28 | 42.2 / 29 | 32.4 / 23 |
| bag 11-20 / 31-80 (% of tributes) | 30.0 / 24.5 | 18.1 / 31.9 | 20.8 / 35.0 | 17.6 / 36.1 | 26.4 / 33.0 |
| first tribute (median round) / none by r300 | r140 / 26% | r115 / 15% | r122 / 20% | r105 / 17% | r142 / 23% |
| collected / banked / lost on death / carried at the end (gems per game) | 572 / 399 / 96 / 94 | 1,115 / 984 / 97 / 132 | 994 / 744 / 162 / 149 | 1,240 / 1,034 / 136 / 192 | 749 / 454 / 188 / 106 |
| lost / carried at end, % of collected | 16.8 / 16.4 | 8.7 / 11.8 | 16.3 / 15.0 | 10.9 / 15.5 | 25.2 / 14.1 |

**Replay timings** (`res_banks.py`, `res_bankvia.py`; tributes that completed):

| | OURS | top vs us | top vs top | IC | prism best girl |
|---|---|---|---|---|---|
| tributes / body / 100 rounds | 0.26 | 0.55 | 0.42 | 0.48 | 0.43 |
| tribute channel time (% of rounds) | 0.95 | 2.3 | 1.8 | 2.1 | 2.3 |
| median last capture -> altar (tiles) | **16** | 10 | 11 | 8 | 8 |
| median rounds capture -> tribute (mean) | **20 (47)** | 11 (25) | 14 (29) | 10 (24) | 12 (29) |
| altar within 8 tiles of the last capture | **22%** | 43% | 39% | 52% | 50% |
| tributes after a recall home (bank from spawn) | **66%** (v52 68%) | 37% | 41% | | |
| direct tributes: bag / rounds after capture / tiles | 23.4 / 8 / 10 | 36.4 / 6 / 7 | 36.3 / 9 / 8 | | |
| tributes via recall: bag / rounds after capture / tiles | 35.3 / 34 / 18 | 40.8 / 28 / 16 | 41.7 / 31 / 17 | | |
| median altar distance to spawn | 16 | 16 | 17 | 16 | 16 |

**Gems lost on death** (replays, per body per game): 20.6 for us against 20.3 for top teams vs us and 34.7 for top vs top. Deaths with a
bag of 20 or more are 10.5% of ours against 16%. In v52, Vendetta (25 vs 14) and Varg (29 vs 10) lose the most. In v50 it was Heart of
Ruin (40 vs 18); in v52 our Heart of Ruin loses 14.

**How we bank.** The capture-recall in `capture_group()` fires on gold (`cap_recall_gold` 60 including the reward), hurt
(`cap_recall_hp` 0.61) or a bag at `bank_min`. We get 3.0 capture-recalls per body per game, against 2.8 for the non-spam top teams.
The body then walks 16-18 tiles from spawn to the altar. Direct field banks happen only through `tribute_near` (5) or `on_the_way`
(detour <= 2), so they are small (23 gems).

**How the top teams bank.** They walk a ~36-gem bag to an altar 7-8 tiles from the capture within 6-9 rounds. 11-13% of tributes on both
sides are followed by a recall within 10 rounds.

## 6. Recalls (completed recalls, replays; `res_recalls.py`)

| team | bodies | starts / body | completed / body / game | per 100 rounds | completed by r300 | capture % | hurt % | bag >=20 % | gold >=90 % | median hp at start | shop on arrival % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HouseOfCoders | 1,767 | 9.4 | 8.3 | 0.74 | 2.43 | 35.8 | 44.8 | 4.1 | 4.2 | 0.49 | 60.8 |
| Intercontinental Fish | 515 | 11.1 | 9.1 | 0.89 | 2.73 | 20.7 | 54.4 | 10.8 | 9.2 | 0.42 | 59.4 |
| prism best girl | 454 | 12.0 | 10.2 | 0.94 | 3.04 | 21.7 | 48.7 | 14.2 | 7.1 | 0.47 | 57.4 |
| procless | 432 | 11.5 | 10.0 | 0.93 | 3.55 | 40.0 | 51.7 | 2.8 | 3.0 | 0.42 | 60.6 |
| policy wonk | 430 | 8.4 | 7.4 | 0.67 | 1.94 | 27.8 | 39.8 | 16.7 | 11.7 | 0.68 | 70.8 |
| new team(4) | 413 | 11.2 | 9.7 | 0.85 | 2.77 | 39.8 | 34.5 | 6.2 | 8.5 | 0.60 | 76.5 |
| Univardisty | 365 | 10.3 | 9.4 | 0.80 | 2.16 | 31.5 | 41.7 | 7.6 | 13.4 | 0.50 | 75.3 |
| Trzy Kwaterki | 269 | 11.9 | 10.4 | 0.87 | 2.81 | 24.7 | 38.5 | 2.7 | 10.0 | 0.57 | 65.9 |
| **Pantheon** | 416 | **904** | 23.7 | 2.13 | 7.77 | 24.7 | 43.2 | 9.2 | 5.2 | 0.50 | 64.0 |
| **:3** | 400 | **814** | 20.4 | 1.99 | 6.80 | 29.3 | 37.1 | 7.7 | 9.4 | 0.53 | 64.4 |
| **EMPEROR Tung** | 147 | **978** | 32.0 | 2.65 | 9.43 | 46.7 | 31.4 | 4.8 | 8.7 | 0.59 | 68.2 |

Purpose is classified at the start of the completed recall, in this order: a capture lands within the channel, hp < 50%, bag >= 20,
gold >= 90, other. A recall takes 5 turns, so each one costs a body ~5-6 rounds: ~45 rounds per body per game (4%) for us and the
non-spam teams alike.

**The recall-on-idle trick** (`C:/battlecode/cache/an_resources/peek3.mjs`, :3's Vesper on 00collision_6cc41c8c).
- **The loop:** every turn it plays "Cancel channel, act, Recall".
- **What it buys:** when the body stops acting (it stood on a capture tile r49-53), the open recall completes. It arrived home at r54 with
  the capture (15 gems, 239 gold), bought 8 items and went from 1,000 to 1,700 max HP.
- **No downside:** damage interrupts the recall at no cost, which is the 120-170 "interrupted" starts per body.
- **Who uses it:** not IC or prism best girl (#1, #2).

## 7. Differences that matter, with proposed changes (ranked by expected effect x confidence)

Two thirds of the gold gap is capture count, and kill gold is another 12%. Neither is resource logic, so these changes are second-order.
Each needs a ladder A/B; local mirror games do not predict the ladder (AGENTS.md).

1. **Build: Durability health first, Treasure only on the gold-bonus carry.**
   - **Evidence:**
     - Our Treasure-first-everywhere returns a median of 56-138 gold (26-51% of cases under the 60 gold a Bruiser emblem gives).
     - Durability is 4% of our shards against 9-10%; the #2 team buys no Treasure.
     - Our Vesper is a glass cannon: 5/0/1 str/foc/hp shards and 1,082 max HP at r300, against 9-13 / 4-6 and 1,384-1,567.
     - Engagements follow max-HP sums (AGENTS.md).
   - **Code:** already written. `build_top(..., dura_first=true, gold_carry)` (brain.cpp:541, selected at brain.cpp:749):
     - every body opens Durability-hp;
     - the bonus-gold kit (Vesper) then buys Treasure;
     - melee then buy Jungle and the Bruiser cycle; ranged then buy a damage Bruiser and Power for ever.
     - It is `SV.build_style` 17 = **in-bot A/B bit 16** (strat.cpp). It was only tested locally (43.8% vs control, mirror).
   - **Proposal:** ladder A/B bit 16.
   - **Lighter variant** (if it loses): keep style 15 and move Durability-hp to the 2nd emblem on ranged-strength kits. In `build_top`'s
     `!foc` ranged branch the order becomes Treasure-str, Durability-hp, Bruiser-str (new team(4)'s Vesper order).
2. **Bank in the field, at the altar nearest the capture, before going home.**
   - **Evidence:**
     - 66-68% of our tributes go through spawn, against 37-41%.
     - We bank 20 rounds after the capture (them 11-14), from 16 tiles (them 10-11).
     - Our field banks are 23-gem bags (theirs 36).
     - Each spawn-route bag is banked ~25 rounds later, after a 16-18 tile walk from spawn.
   - **Proposal** (params.h / brain.cpp):
     - `P.bank_first` 0 -> 1 (`capture_group()` ~brain.cpp:7408: bank at the nearest altar when `adist + recall_t + bank_first_margin <= spawn_altar`).
     - `P.tribute_min` 54 -> ~32. `bank_min()` (brain.cpp:5071) still raises it for trips over `bank_trip_free` 12.
     - `P.tribute_near` 5 -> 8.
     - `Brain::on_the_way()` (brain.cpp:5052) detour `via - direct <= 2` -> 4.
     - In `capture_group()`, do not recall on the `rich` trigger (`cap_recall_gold` 60) alone while the bag is >= 20 and an altar is within
       ~10. Bank first; `home_trip()` recalls right after a bank (`last_bank_round`) when hurt or holding 90+ gold.
   - **Expected effect:** tempo and fewer walks. It will not save gems: our loss per body already equals theirs.
   - **Caveat:** `bank_first` was turned off for a 0.6% unopposed-pace loss, which does not measure contested play.
3. **Marcella as the banker and big-reward collector** (she is in 34% of our games; the top teams' Marcella in 81%).
   - **Evidence:** her bank gold is ~640 a game for them against ~124 for us. Ours collects 9.9 gems per capture (theirs 17-22) and banks
     2.1 times a game (theirs 5.4-7.5). Her gold lands at the moment she banks, so frequent banking compounds.
   - **Proposal:** for Marcella only, `bank_min()` x ~0.6 and `tribute_near` +3. Combine with #4 so that heavy-gem rewards near her go to
     her.
4. **Reward routing to Vesper / Marcella: cheap, but small with our spread play.**
   - **Evidence:** our Vesper is within 4 tiles of only 8.6% of the other bodies' captures (top teams 18-20%). That is ~70 bonus gold per
     Vesper game plus ~77 per Marcella game.
   - **Code:** `SV.route_gold_d` (strat.h:36; **bit 32** sets 4), used in `Brain::group_score()` (brain.cpp ~5951) through
     `route_extra()` (brain.cpp:634: Vesper +33% of the gold, Marcella 2 per gem).
   - **Proposal:** put bit 32 (with `route_gold_d` 6) in the same A/B round as #3. It only becomes significant if bodies farm together.
5. **Prism as the gem holder** (only when we draft Prism: 25 of our games, against 396 OPP/TOP Prism bodies in NEW).
   - **Evidence:** their Prism carries 78-103 gems on average (+117-155 focus), banks 0.6-1.2 times a game with 200-300-gem bags, and
     opens Durability-hp > Monster-focus > Jungle-hp (61-76% health shards). Ours carries 3-4 gems and opens Treasure-focus.
   - **Proposal:** set `P.prism_bank` 1 (params.h:927; tribute() already honours it) and give Prism a health-first build (style 17 already
     does Durability-hp first).
6. **Recall-on-idle** (experimental; 3 of the top 10, ranks 4-7; not IC or prism best girl).
   - **Proposal:** at the end of a turn with no action, no enemy within reach, off spawn and not channelling, call `recall()`; cancel it
     at the start of the next turn if the body wants to act.
   - **Effect:** 2.5-3.5x more completed recalls (heal, shop, spawn-side bank) at no cost, and idle capture waits become capture-recalls.
   - **Risk:** it touches every rule that reads "channelling" (`handle_channel`, `recall_join`, `chan_keep`, escort and capture-recall
     timing). Try it after 1-3.

**No change needed:** unspent gold (we convert faster than the top teams), shop cadence and triggers (`shop()`, `home_trip()`,
`shop_trip()`), and recall counts and purposes. The resource gap is income: captures, kills, and the carries' share and survival.
