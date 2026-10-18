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

## Results
(none yet)
