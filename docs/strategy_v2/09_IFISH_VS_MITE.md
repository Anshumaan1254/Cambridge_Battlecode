# 09. The two top teams against each other: Intercontinental Fish vs Mite (session 10, 18 Oct 2026)

Input: the user's `INTERWIN.zip` (29 match archives, **13 distinct games**), now `experiments/interwin_oct18/<map>.repl26a`;
tables in `experiments/interwin_oct18/analysis/` (`tools/strategy_v2/run_all.py`, `teamsum.py --skip contest`,
`micro.py --skip contest`). Five games are session 9's group 7b2474db (doc 08); eight are new.

Replays carry no team names. The teams are identified by their fixed per-map drafts (the same in all 33 ladder games we have
of them, against us, against each other and against the 3rd team): **side A = Mite (2nd on the ladder), side B = ifish (1st)**.

## 1. Results and drafts

| Map | Mite (A) | ifish (B) | Result A-B | Body deaths A-B |
|---|---|---|---|---|
| stampede x2 | Prism, Stellar, C&I, Ryth, Tavi | Stellar, Tavi, Prism, C&I, Ren | **Mite 1008-0 (r470), 1080-0 (r484)** | 1-2, 4-1 |
| contest | Prism, Stellar, C&I, Ryth, Tavi | Stellar, Tavi, Prism, C&I, Ren | **0-0 at r2000, Mite on gold 18.2k-2.3k** | 8-97 |
| packs x2 | Ren, Stellar, C&I | Ren, Stellar, C&I | **Mite 1014-716, 1008-928** | 4-7, 8-8 |
| rushbait-v2 | Varg, Ryth, C&I, Stellar | Ren, Stellar, C&I, Ryth | **Mite 1024-920** | 8-5 |
| rows | Varg, Ryth, C&I, Ren | C&I, Stellar, Varg, Ren | ifish 990-1056 | 0-0 |
| fragment | Varg, Stellar, C&I | Ren, Stellar, C&I | ifish 132-1034 | 12-3 |
| elkring x2 | Varg, Stellar, C&I, Ryth, Tavi | Ren, Stellar, C&I, Ryth, Varg | ifish 936-1008, 666-1026 | 4-2, 8-0 |
| eight | Varg, Stellar, C&I, Ryth, Tavi | Ren, Stellar, C&I, Ryth, Varg | ifish 374-1020 | 11-3 |
| corners | Varg, Stellar, C&I, Ryth, Tavi | Ren, Stellar, C&I, Ryth, Varg | ifish 596-1030 | 7-0 |
| lanes | Varg, Stellar, C&I, Tavi, Ren | Ren, Stellar, C&I, Ryth, Varg | ifish 972-1020 | 4-0 |

ifish 7, Mite 6. Without contest: ifish 2.6 body deaths per game, Mite 5.9; kills 4.2 vs 1.8; camp gems 816 vs 903 (Mite);
neutral captures 4.2 vs 8.1 (Mite); gold 4,394 vs 3,808.

**Draft tables** (both teams, every official map: `MITE` and `IFISH` in `draft.cpp` of `experiments/wip/x_proxy_mi.patch`):
- Mite: Varg first almost everywhere; Varg + Ryth on every 4-champion map; Tavi as the 5th pick on 5-maps (Ren instead on
  pilgrimage, lanes, ambush); Ren, Stellar, C&I on packs and expanse; Varg, Ryth, C&I on collision; **all casters** (Prism,
  Stellar, C&I, Ryth, Tavi) on stampede and contest.
- ifish: our own draft (Ren, Stellar, C&I, Ryth, Varg) on 5-maps; **Ryth, not Varg**, as the 4th pick on swirl, rushbait-v2,
  interlock; C&I, Stellar, Varg (+ Ren on rows) with Monster builds on rows and expanse; casters on stampede and contest.

## 2. How ifish beats Mite: it wins the fights on Mite's own half

- 82 fights on Mite's half (by walking distance from the spawns): Mite loses **39 bodies, ifish 6**; ifish deals 50.8k damage
  there to 39.7k. On ifish's half Mite wins (7-12 deaths), in the neutral band 18-11.
- Mite's victims: Cassi 17, Issac 17, Stellar 14, Tavi 9. Mite's casters stay at base health (Cassi, Stellar, Tavi 700-750 HP
  at r300), while ifish's frontline is built for health (Ren 1,900 HP by r100 with Bruiser + Durability health; Ryth 2,200).
- ifish's killer: its **Stellar** (30 of 71 Mite deaths), Power focus first (PfE at r38-46).
- Openers are even (65 vs 66) and Mite's out-damage (553 / 197 vs 467 / 275 in the 3 rounds after), but Mite's bodies die at
  close range: deaths in the next 4 rounds per 100 body-rounds at distance 2 / 3 / 4: Mite 14.6 / 10.2 / 6.4, ifish 4.8 / 3.2 / 3.6.
  Health decides the trades.

## 3. How Mite beats ifish

1. **stampede**: all five casters ring the 6-elk + 6-gem objective (17,400 HP) from distance 4 from r54, outside the elks'
   reach; first kill r124, then r263 and r412-428 (the 150-round respawn); each capture is split 5 x 72 = 360. 1080 by r470-484
   while ifish farms gold groups and never gets a gem.
2. **contest**: Treasure first on every caster (Mite's Stellar earns 5,148 gold), 79 kills to 7, decided on gold earned at r2000.
3. **Farming**: Ren / Ryth / Varg buy **Jungle in strength** first (-30% camp damage taken): packs Ren JsE at r21, 10-12 captures a
   game; rushbait-v2 Ryth 16 and Varg 14 captures. Ren and Ryth farm on strength on the small-team maps, on focus on 5-maps.
4. Mite's builds: Jungle, Durability in the damage stat, one Bruiser health, then Power forever (doc 08: "2nd team").

## 4. Sparring proxies (frozen: `x_proxy_mi.patch` on `_m7` + `x_o2.patch`)

- `official_map()` recognises the 17 official maps by size and camp mix (same answer in draft and game turns).
- `_mite` = `mapdraft=1 build_style=9 o2_ring=1 o2_ring_melee=1`; `_ifish` = `mapdraft=2 build_style=10`.
- `_ifish` vs `_mite`: 55.9% on the 34 official games (real 7-6). The proxies reproduce stampede (Mite 1080 both sides), contest
  (0-0, Mite on gold, deaths 94-11), rows (ifish 1056-990, the real score), eight, elkring.
- `_m7` vs `_mite` 75.0% (official 73.5), vs `_ifish` 65.9% (67.6): inside our brain our draft and builds beat theirs overall;
  the proxies won only where they used a map plan we lacked (rushbait-v2, stampede, expanse).

## 5. What went into `legend_m8`, and what did not

Shipped (`legend_m8`, `mapdraft=3 md_stampede=1 o2_ring=2`): ifish's 4th pick Ryth on rushbait-v2 and interlock, ifish's C&I,
Stellar, Varg on expanse, Mite's stampede (casters + ring from distance 4, gated to stampede by its 60x50 size so no extra fuel is
spent elsewhere). On those four maps 44 of 48 games won against six opponents (`legend_m7` 26). vs `legend_m7` 53.4% (official
55.9), every third-party cell higher, pace 503.8 (520.9; stampede 471/479 instead of 704/765). Numbers in BUILDS.md and README.

Tested and rejected (judged head-to-head against the previous bot, as the user asked):

| Change | vs previous bot (all / official) | Why rejected |
|---|---|---|
| Ryth instead of Varg on swirl | 6/12 vs 7/12 on swirl vs third parties | no gain, 90 rounds slower unopposed (Varg's splash on 12 wolf packs) |
| Ring plan everywhere (`o2_ring=1`) | ambush -5 in 11 changed games | the objective mode also fires on ambush |
| `official_map()` called in `group_score` | -14 wins outside stampede | its fuel cost changes fuel-floored group scoring on 15 maps |
| Mite's or ifish's whole draft table | per map, never better than ours beyond +-3 of 14 | the current table already holds the gains |
| Shop when within 2-4 steps of spawn with 60-120 gold | 50.0 / 48.9 / 50.0 vs `_m8` | fires in 1-7 of 88 games: `shop_trip` (150 gold within 9 steps) and recall-to-shop already cover it |
| Reward to the better gold user (`gold_rank` 1: Stellar, Varg, Cassi, Issac, Ryth, Ren) | 48.9 / 44.1 | fewer deaths, slower pace |
| Reward to Stellar first (`gold_rank` 2) | 47.7 / 47.1 | |
| Monster before health: Ren / Ryth / both | 54.5 / 41.2; 53.4 / 52.9; 46.6 / 41.2 | Ryth: third parties -2 to -6 points, held-out 48.0 (noise) |

What our builds already do: Stellar, Cassi, Issac and Varg buy their camp-damage emblem (Monster in the damage stat) first;
moving it first for Ren or Ryth loses. The top teams' full build orders lose inside our brain (sessions 8-10).
