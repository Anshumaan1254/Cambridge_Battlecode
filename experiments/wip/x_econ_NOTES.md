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
| `join_age` 0.5 / 1.0 | joins use health estimated from the claim's age when the group is out of sight | pace 543.4 / 542.6 (stampede 698 -> 792/883: the objective group's estimate hit 0): rejected |
| `hysteresis` 1.3 | stickier targets | pace 528.3: noise |
| `max_join` 4 | 5 bodies per group (the ladder enemy's opening sweep) | pace 530.4: noise |
| `max_wait` 30 / 10 | respawn waits | 540.1 / 539.7: rejected |
| `claim_release` | an alive ally's claim leaving a group we remember as a reward = it collected it (mark respawning) | 56 maps: official 524.6 (= `_m4`), other 39 maps 410.7 vs 418.7 |
| `join_marginal` | joiner's value = claimers' rounds saved by its help (after its walk) / their clear, over its own rounds; no 0.6 share | expanse single game 569 (vs 581-618 for other variants), waste 25% -> 13.6%, Issac first capture r139 (r226-r328) |

| `join_marginal` (56 maps) | | pace official 541.6 (pilgrimage +98, rows +37, corners +40) / other 39 maps 410.5 (`_m4` 418.7); h2h vs `_m4` official 19/34 = 55.9 |
| `join_marginal` 2 | marginal value only on single-attacker groups (packs/elks keep join_share) | pace official 529.8 / other 417.5: no gain |
| `cap_recall_gold` 150 | recall after a capture only with an emblem's worth of gold | pace official 535.8 / other 417.3: rejected |
| `finish_trip` 15 | no voluntary home/shop trip while in range of a group that dies within 15 rounds | expanse single game: clear 29.9 -> 28.7 (C&I solo wolves still 25-40 rounds: base damage ~45 dps); not pursued |
| `pair_plans` 1 (+ cr + jm) | elk pairs on interlock | first elk pair capture r326 (cr+jm alone r310): no help |
| `_xe_0` (all switches off) | noise check | 56-map pace 450.6 = `_m4` 450.8: the switches are inert when off |

Interlock elk pairs: neither heavy_team nor pair_plans gets them done early; the bodies are spread over the wolves when the
pairs would need 3-4 of them together. Left open (needs a team-level schedule: sweep the near wolves together, then the pair).

Noise: the 17-map official pace moves +-10 for changes that do nothing on most maps (e.g. pilgrimage 579-670 across variants); `_m4`'s 524.5 is
the best of the farm agent's tuning on these 17 maps, so most variants regress toward ~530-540. Decide on the 56-map pool (112 games).
