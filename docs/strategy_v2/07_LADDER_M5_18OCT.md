# 07. legend_m5 against the top 3 (ladder, 18 Oct 2026, evening)

Input: 12 match groups the user ran with `legend_m5` (side A) against the teams in 1st, 2nd and 3rd place, 4 groups each
(60 games; some groups repeat a map and the games replay identically, so 51 distinct games). Reports, CSVs and replays:
`experiments/ladder_m5/{1st,2nd,3rd}/` (made with `tools/strategy_v2/run_all.py`; bag check `tools/strategy_v2/bags.py`).

## Results

| Opponent | Wins | Banked us-them | Body deaths | Kills | Camp gems | Gold earned | Captures | Banks |
|---|---|---|---|---|---|---|---|---|
| 1st | 2/20 (expanse, ambush) | 9,438-20,784 | 198-74 | 43-150 | 11,178-20,620 | 50.5k-101.4k | 261-493 | 185-305 |
| 2nd | 1/20 (ambush) | 9,380-19,081 | 206-43 | 32-157 | 11,258-19,270 | 52.7k-103.3k | 281-521 | 190-390 |
| 3rd | 2/20 (rows twice, same game) | 9,593-20,390 | 189-60 | 36-136 | 10,502-21,610 | 49.8k-129.0k | 282-547 | 200-390 |

Against the Oct 18 morning group (`legend_st`-era, 2/15) nothing has changed on the ladder: our local gains (`legend_m5`
beats `legend_st` 74-91% locally) did not reach the top teams.

## Where it goes wrong (all three teams alike)

| | Us | Them |
|---|---|---|
| Time alive | 83% | 91-93% |
| Fight damage dealt / taken | 0.48 (1st) | |
| Death incidents that are **burst** (above 60% health 4 rounds before) | **52-69%** | 17-26% |
| Deaths to ranged hits | 56-61% | 14-31% |
| Our killers | Stellar 171 of ~460, then Cassi, Ren, Ryth, Issac | |
| Failed escapes (below 35%, enemy within 6) | 13-24% | 30-40% |
| Hit rounds with no hit back | 0.66 (1st) | 0.53 |
| Gem captures home / neutral / enemy side (1st) | 217 / 41 / 3 | 331 / 147 / 15 |
| Damage points per 1,000 gold | 20.8 | 32.7 (458 Power-damage emblems, one Durability/Bruiser health each) |
| Camp damage per camp round | 81-87 | 113-125 |
| Issac: captures, gold, first emblem (1st) | 1.8, 280, r260 | 6.2, 1,060, r124 |
| Gems carried at game end (51 games) | 2,232 | 2,290 |

- Banking is **not** the gap (bags at the end are equal); collection is (half their camp gems), and collection is lost to
  deaths (17% of body-rounds dead vs 7%) and to the neutral groups they hold (neutral captures 3-4x ours).
- We die at high health from range (their Stellar's focus with Power emblems: stun + 2.0x focus from range 4, then focus
  fire); they die low, while escaping. Our bodies do not leave before the burst lands.
- Fight-free maps still lose on pace when the enemy takes neutral groups: expanse 562-1,024 and 690-1,018 with 0 deaths
  on both sides; rows is the one map we win (1,056-924).
- contest: spawn-camped every time (deaths 55-10, 84-0, 73-4); against 2nd it went to round 2,000 at 0-0 and was decided on gold
  earned (2.6k vs 19.8k).

## Consequence for testing

Session 8 found that our sparring bots (all our own code; `_fA` = our brain with the top teams' draft and builds) do not
reproduce this fight gap (`_m4` vs `_fA`: hit-nobody-back 68% vs 63%, damage ratio 0.88), so rules aimed at burst
(`burst_exit`, spacing, strike first) score as noise locally. Next step: a sparring proxy calibrated on these 51 games
(target KPIs above) before any more fight rules are judged; ladder match groups stay the final judge.
