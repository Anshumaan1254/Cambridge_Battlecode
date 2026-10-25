# GOD v14 on the ladder, Oct 25: the user's 4 match groups (20 games, 0-20)

The user uploaded four match groups of our current bot (GOD v14, team A in every game) against top ladder teams. Opponents are
identified by their drafts against the Oct 24 ladder lists (`experiments/ladder_oct24/mapintel_20261024_0836/matches_current.jsonl`):

| group | opponent (by draft) | maps |
|---|---|---|
| 15ec | Claudus Maximus (Ve/Vd/HoR/Ta/Ma; rushbait Ve/Vd/HoR/CI) | rushbait-v2, fracture, stampede, elkring, concentrated-wealth |
| 27c8 | Univardisty of Shingtonwash (Marcella first: Ma/Ve/Wi/Ta, Ma/Va/St, ...) | swirl, broken-curve, starvation, great-wall, packs |
| b446 | a Ve/Vd/HoR/CI team (broken-curve matches FürFortnite's draft) | broken-curve, lost-world, starfish, starvation, corridors |
| cbc9 | Intercontinental Fish (Ve/Vd/HoR/CI/Ma) | reverse-spiral, boss-battle, corners, swirl, yellow-brick-road |

Files:
- `replays/` the 20 replays (`<group>_<nn>.repl26a`, engine v1.0.3); `summaries/` `tools/mapintel/replays.py` output (team 0 = us).
- `gapx.jsonl` session 17's gap extractor (`god2_session17/tools/top2/gap/gapx.mjs`) on the decoded games; `gap_tables.txt` its tables
  (`gapx_agg_local.py` = `gapx_agg.py` with this folder's `sides.json`); `behav.txt` `tools/analysis/behav.mjs --team both`;
  `pergame.txt` `tools/analysis/v15_agg.py` (per game: banked, captured gems and gold, deaths, bags lost, banks, first capture).
- Back-and-forth walks by enemy distance: `node tools/analysis/v15_osc.mjs DEC.json.gz...` (decoded with `tools/top2/gap/deccache.mjs`).

Headline (per game, us / them): banked 197 / 1,110; camp gems captured 319 / 1,091; middle-band captures 3.6 / 20.1 (74 / 634 gems);
gold 2,685 / 6,926; item shard equivalents at r600 63 / 125; deaths 12.3 / 7.0 (middle 6.6 / 2.9, alone 4.5 / 1.4); banks 7.8 / 26.9
(mean bag 27 / 63 in gapx, 25 / 41 in behav); bags lost at death 96 / 29; farm share with an enemy within 8: 4-8% / 15-19%; walk rounds a
body toward fights (r<1000) 175 / 73; back-and-forth walks with no attack or cast 260 / 89 over the 20 games, 233 / 39 of them with an enemy
within 8; respawn wait before a re-take (median) own half 55 / 28, middle 78 / 21. Fuel: 170 turns over 100k of 96,184 (not a cause).
Worst games: swirl (37 and 0 gems captured, 35 and 16 deaths: the spawns are 15 tiles apart and the middle groups feed us one body at a
time), stampede (69 captures, all gold clusters: 0 gems), boss-battle (889 captured, 0 banked, 584 lost at death next to the only altar).
Doc: `docs/strategy_v2/22_GOD_V15.md`.
