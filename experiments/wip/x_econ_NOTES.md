# x_econ: farming throughput / income (agent `econ`, session 7)

Baseline `bots/_m4` (read-only). Copy `bots/_x_econ`. Patch `experiments/wip/x_econ.patch` (`cd bots && diff -ruN _m4/src _x_econ/src`).
Pace = round at which we bank 1000 gems vs `idle`, mean of both sides, 17 official maps (ledger cells `BOT_vs_idle`). `_m4` = **524.5**.

## Status: work in progress (kept current)

## New tools
- `tools/econ/cycles.mjs [--groups] FILE...`: per camp group and capture, both teams: idle (available -> first damage), clear (first damage ->
  all dead), lag (dead -> capture), hitters, collector. Capture-recall rewards are attributed to the group the body last stood on.
- `tools/econ/waste.mjs FILE...` (LEGEND_TRACE builds): share of alive body-rounds in camp-target segments that never hit the target nor
  captured anything (walks abandoned before arrival, waits for a respawn someone else took), by task and champion.

## Diagnosis (measured)
### Ladder (17 games of legend_st, enemy side) vs `_m4` unopposed (trace build `_xe_tr` = `_m4` + LEGEND_TRACE, side A)
- Camp gems collected at r100/200/300: our *unopposed* `_m4` is about level with the enemy's *contested* games (they farm only their half):
  ahead on corners, eight, monolith, swirl, pilgrimage; level on ambush, elkring, fragment; behind at r100 on collision (110 vs 146), expanse
  (88 vs 132), interlock (88 vs 160), lanes (146 vs 176), packs (180 vs 228), rows (198 vs 264). So `_m4`'s farming already matches the
  ladder teams per half-map; the ladder gap (7.9k vs 16.2k camp gems) is mostly contact (deaths, chases), plus the opening on 6 maps.
- Capture cycles (cycles.mjs, all 17 maps): enemy (contested) clear 24.3 rounds with 2.5 hitters; `_m4` unopposed clear 25.7 with 2.2.
  expanse is the exception: enemy clears single wolves in 8.6 rounds (Issac/Varg MsE + Power strength), we take 29.9.
- rows: per pack the enemy cycle is ~52 rounds (respawn 40 after the capture + clear ~8 + capture 6), ours ~57-60 unopposed.
- Allocation: our gold piles up on Ren (expanse end: Ren ~15 emblems, Cassi 8 shards, Issac 13 shards); enemy Issac collected 408 of
  1,016 camp gems on expanse. Our Issac on expanse flipped between 4 wolves for 220 rounds before his first capture (r226).
- Waste (waste.mjs, `_m4` unopposed, 17 official maps): **24.3% of alive body-rounds** are in target segments that produced nothing
  (farm 19.4, wait 3.7, capture 1.2; Issac 5.4, Cassi 4.9, Stellar 4.8, Ren 4.0, Varg 3.3). Switch causes (sw_why): respawn too far off
  668 switches (15,008 rounds on the target), rescored lower 1,060, reward to a lower claimer 282, no_split 170, join refused 101.
- interlock: our two near elk pairs (72 gems + 320 gold, 4,800 HP, 120 dps) sat untouched 100-350 rounds (no single body can plan them,
  nobody claims them, nobody joins); the ladder enemy took one at r73 with 4 bodies.

## Switches (all in params.h, default off = `_m4` behaviour)
| switch | what | result |
|---|---|---|
| `econ_build` (bits) | 1: C&I passives in damage stat; 2: Ren Jungle focus; 4: Varg/Stellar 2 Power emblems after Monster; 8: Ren Monster first | pace: 1 524.9, 2 531.0, 4 530.8, 10 529.8 (all noise) |
| `bank_trip_cap` 4 / + `bank_trip_free` 6 / `tribute_min` 60 + cap 3 | bigger bags | pace 527.9 / 525.7 / 526.7 (rushbait worse 650 -> 674-707): rejected |
| `heavy_team` | team plan (objective-plan test + gather) for heavy groups off objective maps | pace 542.1 (pilgrimage 579 -> 722; interlock unchanged: Ren waits alone at the elk pair, the others farm wolves): rejected |
| `join_age` | joins use health estimated from the claim's age when the group is out of sight | testing |
