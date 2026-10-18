# econ2 (session 9): top-team item builds on `_xp4`

Copy `bots/_x_e2` = `_xp4` + switches (patch `x_e2.patch`, defaults reproduce `_xp4`). Build helper `top_build()` in brain.cpp.
Recipes (`SRC=bots/_x_e2 tools/variant.sh NAME ...`):
- `_e2s7` build_style=7 (3rd team: Treasure, Jungle, Durability in the damage stat, Bruiser health, Power forever, every champion)
- `_e2s8` build_style=8 (2nd team: Jungle, Durability in damage stat, Bruiser health, Power); `_e2s8b` same with e2_power_after=0 (Power x5 before Durability)
- `_e2c1..c4` e2_cassi (Cassi/Willow only): 1 = 3rd-team order, 2 = 2nd-team order, 3 = Jungle focus + Durability health + Power, 4 = Treasure focus + Durability health + Power
- `_e2i1..i4` e2_issac: 1 = 3rd-team order (strength), 2 = Power strength x5, Durability health, Power; 3 = 2nd-team order; 4 = Durability health then Power strength
- `_e2h0` ci_health_first=0 (existing switch: Cassi/Issac Monster damage first)
- `_e2k1..k5` ci_health_first=0 plus e2_cassi / e2_issac 5 (Monster, Durability health, Power forever) or 6 (Monster, Jungle health, Durability health, Power):
  k1 = cassi5+issac5, k2 = cassi6+issac6, k3 = issac4, k4 = cassi5, k5 = issac5.

## Results (88 distinct games = maps/*.map26a + maps/comp; "off" = official 34; pace = unopposed official 17, _xp4 521.9)
| Variant | pace | vs _xp4 all / off / deaths ours-theirs |
|---|---|---|
| _e2s7 | 543.1 | 34.1 / 26.5 / 762-564 |
| _e2s8 | 551.1 | 47.7 / 44.1 / 699-608 |
| _e2s8b | 547.3 | 46.6 / 41.2 / 700-617 |
| _e2c1 | 526.6 | 39.8 / 38.2 / 698-585 |
| _e2c2 | 523.8 | 39.8 / 35.3 / 680-584 |
| _e2c3 | 530.6 | 44.3 |
| _e2c4 | 528.7 | 38.6 |
| _e2i1 | 522.4 | 51.1 / 44.1 / 726-636 |
| _e2i2 | 524.5 | 48.9 / 38.2 |
| _e2i3 | 521.9 | 53.4 / 50.0 |
| _e2i4 | 516.2 | 53.4 / 55.9 / 677-672 |
| **_e2h0** | 522.6 | **58.0 / 58.8 / 673-628**; held-out 54.0 (2097-2080); vs _px9 62.5 / 52.9, _fA 67.0 / 70.6, _ST 76.1 / 82.4 (_xp4: 58.0, 72.7, 73.9) |

## Verdict so far
- Top-team orders (passives in the damage stat, Bruiser health, Power forever) lose inside our brain: styles 7/8 cost 21-29 rounds of pace and 34-48% head-to-head.
  Cassi in a focus build before any health loses (39-44%).
- The one switch that wins is the old `ci_health_first=0` (Cassi/Issac Monster damage first): it was measured weaker in session 1-2 (vs _v6), but now beats `_xp4` 58.0.

## Later cells (all on the 88 distinct games vs _xp4; pace in brackets)
| Variant | pace | all / off / deaths |
|---|---|---|
| _e2k1 (h0 + cassi5 + issac5) | 517.6 | 54.5 / 52.9 / 702-644 |
| _e2k2 (h0 + cassi6 + issac6) | 519.7 | 51.1 / 50.0 / 680-602 |
| _e2k3 (h0 + issac4) | 527.9 | 46.6 / 41.2 |
| _e2k4 (h0 + cassi5) | 523.5 | 54.5 / 58.8 / 672-628 |
| _e2k5 (h0 + issac5) | 511.5 | 56.8 / 55.9 / 707-653 |
No refinement beats plain h0 (58.0); differences are noise. Replacing the Bruiser cycle by Power forever does not matter.

## h0 stat check (17 official maps, side A = _e2h0 vs _xp4): r300 stats
Cassi focus 124.7 (xp4 70.0), hp 842 (1048); Issac strength 58.2 (45.9), hp 1241 (1498). Ladder top teams: Cassi focus 195-248, so only part of the gap.
Cassi camp damage per camp round 73 vs 50 (xp4 in same games), Varg and Ren gold up too. Deaths per game 7.9 vs 12.6 in these 17 games (h0 wins 12/17 as side A).
Fuel: gen16_98x99_V_c5 rollovers 8 per team, rounds 1-3 (baseline). 0 faults in every cell.

## E4 (gold routing): not attempted. Rewards go to whoever kills the camp (the claimer); a collector rank would need a change in who farms what,
not in who steps on the tile, and the build results show the casters-carry idea loses when it costs health. Left open.

## Recommendation
`ci_health_first=0` (params.h default 1 -> 0; no code change): vs _xp4 58.0 / 58.8 (deaths 673-628), held-out 54.0, vs _px9 62.5 / 52.9, _fA 67.0 / 70.6,
_ST 76.1 / 82.4 (_xp4 itself: 58.0, 72.7, 73.9), pace 522.6 (+0.7), 0 faults, no new rollovers. Do not adopt build_style 7/8 or any Cassi focus-before-health order.
Coordinator is combining h0 with fight2's aoe_cast5=3 (not built here).
