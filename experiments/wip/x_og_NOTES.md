# Agent `opening` (og): opening economy plan (session 11 workflow, started ~20:35 container clock)

Baseline `bots/_m10` (= legend_m10, plays legend_m8's games). Copy `bots/_x_og`, variants `_og1`, `_og2`, ...
Patch `experiments/wip/x_og.patch` (`cd bots && diff -ruN _m10/src _x_og/src`). Rule: >= 50 vs `_m8` and `_m10` (88 distinct and official 34),
not worse than `_m8` vs `_mite _ifish _px9 _fA _ST`, pace within +10 of 503.8, 0 faults, rollovers 8 per team.

## Ladder evidence (experiments/sneaky_oct18/analysis/body.csv, 17 games, team 0 = us, team 1 = sneaky)
| champ | first emblem median us / them | gold by r150 us / them | first capture median us / them | captures us / them |
|---|---|---|---|---|
| Ren | 66 / 120 | 345 / 306 | 29 / 30 | 5.7 / 7.7 |
| Varg | 60 / 145 | 255 / 342 | 56 / 46 | 3.0 / 5.7 |
| Stellar | 192 / 241 | 80 / 104 | 159 / 160 | 3.5 / 4.0 |
| Ryth | 219 / 127 | 101 / 135 | 96 / 71 | 2.7 / 4.6 |
| Issac | 253 / 149 | 59 / 152 | 212 / 65 | 3.1 / 6.6 |
| Cassi | 441 / 250 | 68 / 144 | 179 / 117 | 2.3 / 4.2 |
Our C&I start capturing ~100 rounds later than theirs (first capture r179 / r212 vs r117 / r65).

## Plan
1. Measure local baseline (first emblem round, gold by r150 per champion) on `_m10` vs `_mite` / `_snk` (official 17, side A replays).
2. Switches (each its own, `og_*` in params.h): opening gold weight for poor bodies, poorer collector in the opening,
   first-emblem shop trips, C&I safe own-half camps.

## Local baseline: `_m10` vs `_snk`, official 17 both sides (34 games, 21-13), from the bench stats JSONs
Tool: `/tmp/og/tools/econ.py DIR [--opp]` (copied below in "Tools"): first emblem = spentGold reaches 150; shop lag = rounds from
earnedGold 150 to spentGold 150.
| champ | first emblem med | gold r150 | gold r300 | first gold med | total earned | shop lag |
|---|---|---|---|---|---|---|
| Cassi | 266 | 76 | 193 | 136 | 395 | 1 |
| Issac | 233 | 116 | 269 | 55 | 617 | 0 |
| Ren | 94 | 313 | 701 | 29 | 1491 | 0 |
| Ryth | 228 | 104 | 212 | 83 | 627 | 0 |
| Stellar | 186 | 94 | 270 | 100 | 752 | 0 |
| Varg | 112 | 207 | 568 | 70 | 1058 | 0 |
Body mean gold r150 144 (`_snk` itself: 144; its Issac 165, Cassi 108, Stellar 148). The local games reproduce the ladder pattern.
- **Shop lag is 0-1 round**: bodies already shop the moment the first emblem is affordable (home_trip recalls at 4 shards when safe).
  Idea 3 (shop sooner) has nothing to gain: not built.
- packs (`_m10` vs `_snk`, side A): by r250 Cassi + Issac made 257 attacks/casts and 1 capture; Ren + Stellar 164 and 8 captures.
  The helpers do the work, the lower index (Ren) or first arrival collects.

## Switches (bots/_x_og, all off by default = `_m10`)
- `og_poor_collect` N: before round N the reward goes to the poorer body (item points from visible stats, gap `og_poor_gap` 3,
  slack `og_poor_slack` 3 steps); richer allies on the tiles are ignored by no_split / claim rules (they step off).
- `og_gold_mult` x: gold's gem value x while (shards x 30 + gold) < `og_gold_need` 150 and round < `og_gold_until` 300.
- `og_jungle_first` bits (1 Cassi, 2 Issac, 4 Ryth, 8 Stellar, 16 Varg, 32 Ren): first emblem Jungle in the damage stat, the later
  Jungle block dropped.

## Results
(running: `_og0` control vs `_mite`, `_og1` = og_poor_collect 400, `_og2` = og_gold_mult 2.5 vs `_m10` / `_snk` official 34)
