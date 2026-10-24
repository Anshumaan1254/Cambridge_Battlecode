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
  Vesper Vale, Vendetta, Heart of Ruin on most maps). vs IC's draft + IC's builds (`_px_ic2`) 48/80 (+146): IC's builds are worse in our
  brain. vs prism best girl's drafts 53/80 (+259), vs willow best girl's 13/16 in the first cell.

## 5. GOD v13: v10 + v12 + the IC data, measured

Every candidate is `bots/god13` (= v12's code + `ic_build`) with switches set (`SRC=bots/god13 tools/variant.sh`). Paired = the variant's
gem margin minus GOD v10's in the same game (opponent, map, side), mean [bootstrap 95%]; turned = games it won where v10 lost / the reverse.
40 official maps x 2 sides, cambc 3.0.5, release mode.

| Candidate | h2h vs v10 | IC's draft (`_px_ic`) | prism best girl | willow best girl | 8 strong-team roster families | of which the 4 real ones |
|---|---|---|---|---|---|---|
| pick prior 0.3 | 45/80, +113 | +45, 13/9 | -59 | +1 | | |
| pick prior 0.6 | 49/80, **+201 [+61, +335]** | +45, 18/15 | +71 | -22 | +42.9 [-14, +98], 114/94 | +80 [-7, +170] |
| **pick prior 1.0 = GOD v13** | **47/80, +137 [-5, +272]** | **+120, 22/12** | +43 | -108 | **+55.0 [-8, +115], 135/101** | **+120.6 [+25, +221], 88/51** |
| pick prior 1.5 | 41/80, +9 | +182, 24/12 | -96 | -173 | | |
| prior 0.3 + IC's builds | 35/80, -126 | -221 | -245 | -203 | | |
| prior 0.6 + kill-value targeting | 45/80, +119 | +17 | +57 | -43 | | |
| prior 0.6 + live bytes | 38/80, -59 | +36 | -103 | -52 | | |
| prior 0.6 + IC-size bags (38) | 51/80, +204 | +55 | -7 | -42 | | |
| prior 0.6 + capture rule (IC's carry funnel) | 40/80, -22 | +92, 22/13 | -39 | +35 | | |
| prior 0.6 + ownership 0.1 | 48/80, +116 | **+214 [+30, +403], 23/11** | -96 | -240 | +22.1 [-39, +84] | +53 [-37, +153] |
| **prior 1.0 + ownership 0.1 = anti-IC candidate** | 45/80, +93 | **+222 [+42, +401], 25/11** | -171 | -146 | | |
| prior 0.6 + capture + ownership | 42/80, +27 | +69 | -130 | -158 | | |
| GOD v12 (everything on) | 29/80, -185 | -106 | -287 | -89 | -160 [-218, -100] | -157 |

Against both IC proxies (IC's draft, and IC's draft + IC's builds) pooled: GOD v13 +97 [-22, +219] (39 / 26 games turned); prior 0.6 + ownership
+174 [+56, +290] (39 / 16).

**Reading**:
- **Following the strong teams' per-map choices is what helps** (the pick prior: on a known map its own top-20 pick rates, which include IC's
  table; on an unknown map the rates predicted from the map's features). The more the draft follows it, the better against IC's draft
  (+45 at 0.3, +120 at 1.0, +182 at 1.5) and against the real strong rosters; past 1.0 it starts losing against the Prism / Willow drafts.
- **IC's builds, IC-size bags, kill-value targeting and the live bytes do not help** in our brain; the capture rule helps against IC only.
- **Soft ownership is anti-IC**: with it the bot beats IC's draft by +214 to +222 gems a map (intervals above 0), but it loses that against
  the Prism / Willow drafts, so it is not in GOD v13; it is the candidate zip for a ladder A/B against IC.

**Shipped**: GOD v13 = `bots/god13` = GOD v10's brain and dynamic draft + v12's map analysis and draft memory v2 (written every draft turn) +
the strong teams' pick prior at weight 1.0 (`mi_pick` 1, `mi_prior_w` 1.0); every other v12 switch off (measured worse or level),
`ic_build` off. `submissions/god.zip` sha256 125a87c6…, history `god_v13_20261024.zip`, source hash 4f22e7cba062. Draft fuel: turn 1 at most
959,773 (lanes), no draft turn ran out, every map got its map analysis; 0 faults in every cell above. Anti-IC candidate:
`submissions/candidates/god_v13_anti_ic_20261024.zip` (sha256 65b44499…, source hash 7e0de0e2f719).
