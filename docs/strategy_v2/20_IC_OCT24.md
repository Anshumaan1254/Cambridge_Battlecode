# Intercontinental Fish (Oct 24): the data, how they play, what beats them, and GOD v13

The user (Oct 24 evening): "fetch the data of this team, Intercontinental Fish (1890540d-1ffc-4847-adbf-d0d08772f268), improve the strategy
and beat them; improve on GOD v12" and then "combine v10, v12 and the IC data: the new bot should have a strategy on par with IC and improve
on our strengths and their weaknesses".

## 1. The data

- **Fetching from here needs `cambc login`** (the platform answers now, but every match list and replay call is behind the login, and this
  session never handles the user's credentials). Today's ladder archive (the user's upload of 08:36 UTC,
  `experiments/ladder_oct24/mapintel_20261024_0836/`) already holds IC: **300 ranked matches** (Oct 23 21:40 to Oct 24 08:00, engine
  1.0.3 = cambc 3.0.5 on both sides) and **73 full replays** among its 600 (`experiments/ic_oct24/replays.txt`).
- More data: `python3 tools/mapintel/ladder_fetch.py --team 1890540d-1ffc-4847-adbf-d0d08772f268 --max-per-team 1000 --max-mb 80`
  on the user's machine after `cambc login` (new one-team mode: only IC's match lists, every kept match downloaded, newest first; it
  prints the archive to upload).
- Decoded: `tools/strategy_v2/run_all.py` per side (IC on side A: 41 games, side B: 32), tables in `experiments/ic_oct24/side{A,B}/`,
  the per-team and per-champion summary in `experiments/ic_oct24/teamsum.md` (`analyze.py` needed one fix: a camp type the 3.0.5
  engine reports as a number broke a sort).

## 2. What IC is and how it plays

- **Rank 2** on the ladder (rating 2240; rank 1 "prism best girl" 2255). 171-129 in the 300 matches (57%).
- **A fixed draft table**: one roster per map, the same in every game on that map (40 of 40 maps). Vesper Vale first in all 300, then
  Vendetta and Heart of Ruin (all 300); + Cassi & Issac (237), + Ryth (145) or Varg (58) on the 5-champion maps.
- **Perfect maps**: contest 5/5, corners 7/7, interlock 7/7, quadrants 7/7, stampede 7/7, hooks 5/5; rushbait-v2 8/9.
  **Weak maps**: corridors 0/8, elk-arena 1/10, boss-battle 1/8, fracture 1/5, monolith 1/3, concentrated-wealth 2/8, packs 2/7,
  the-farm 2/7, starfish 2/4.
- **Gold into the carries**: Vesper Vale buys a Treasure (strength) emblem first at rounds 29-84, then Monster, Jungle (health), then
  Power in strength for the rest of the game; Vendetta Monster or Treasure first, Jungle health, Power strength; Heart of Ruin Monster or
  Treasure, Jungle health, Power focus. Cassi & Issac and Ryth often buy nothing in the whole game. Vesper Vale takes 38.5 capture gems
  and 363 gold per 100 alive rounds (first emblem at round 151 on average), Vendetta 22.4 and 173.
- **Pace**: in their wins they bank 203 gems by round 300 (the opponent 66) and 529 by round 600 (213); the first capture at round 36.
  They walk 46% of body-rounds (their opponents 29%), take more neutral and enemy-side camps (11.1 / 2.7 per game vs 9.5 / 1.7), recall
  58 times a game at 48% health.

## 3. What beats them (their 129 losses in the 300 matches; 29 of the 73 replays)

| Opponent | IC wins - losses | Their most frequent draft start in IC losses |
|---|---|---|
| willow best girl | 30 - 20 | Prism Vesper Marcella (16), Prism Vesper HoR (3) |
| prism best girl | 20 - 30 | Prism Vesper Marcella (18), Prism Marcella Ryth (5) |
| Univardisty of Shingtonwash | 25 - 20 | Marcella HoR Vesper (4), Marcella Varg Vesper (3) |
| :3 | 23 - 17 | HoR Prism Vendetta (12), Vesper Vendetta Tavi (2) |
| procless | 23 - 12 | HoR Vesper Ryth (8), Vesper HoR Vendetta (4) |
| Claudus Maximus | 13 - 12 | Vesper HoR Vendetta (8), Vesper Vendetta HoR (4) |
| Trzy Kwaterki | 11 - 4 | Marcella Vendetta Ryth (3), Vesper Marcella Vendetta (1) |
| policy wonk | 8 - 7 | Marcella Vesper Tavi (4), HoR Marcella Vesper (2) |
| new team(4) | 7 - 3 | HoR Marcella Vesper (3) |
| Zarzorki | 7 - 3 | HoR Vesper Marcella (3) |
| Noobot | 4 - 1 | Marcella Ryth Vesper (1) |

- **IC's weakness is the death cascade**: 19.3 deaths a game in their losses against 8.5 in their wins; their opponents die 6.2 times in
  those games. On elk-arena IC lost 68-18 and 74-17 in deaths while the winners farmed 114 and 216 captures to IC's 38 and 75.
- In IC's losses they bank 115 by round 300 (the winner 101): those games are decided later, by fights.
- **Marcella is in almost every team that beats IC** (stun immunity against IC's stunners: Heart of Ruin's dash, Cassi & Issac, Ryth).
  **Tested on the 8,455 current-patch ladder matches and rejected**: a "Marcella x enemy stunners" counter term adds nothing over team
  rating out of sample (leave-maps-out log loss 0.6879 vs rating alone 0.6851, coefficient -0.03). As step 6 found for every champion
  term: on the ladder the draft is explained by who drafts it (the strong teams pick Marcella), not by the draft itself.

## 4. On our brain (local proxies, cambc 3.0.5, 40 official maps x 2 sides)

Proxies (`tools/ic/make_team_proxy.py`): GOD v10 with a ladder team's own per-map roster forced: `_px_ic` (IC's table), `_px_pbg` (prism best
girl, rank 1), `_px_wbg` (willow best girl, rank 4), and `_px_ic2` (IC's table + IC's builds, `ic_build`). They draft like the team; the
play is our code family's. `python3 -I tools/ic/cells.py VARIANT...` pairs each game with GOD v10's own game against the same opponent.

- GOD v10 vs IC's draft: **40/80, +38 gems a map**: IC's draft is as good as ours inside our brain (v10's dynamic draft already picks
  Vesper Vale, Vendetta, Heart of Ruin on most maps). vs prism best girl's drafts 53/80 (+259), vs willow best girl's 13/16 so far.
- The results of the GOD v13 candidates are in section 5.

## 5. GOD v13 candidates

(filled in when the cells finish)
