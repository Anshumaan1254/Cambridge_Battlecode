# 13. `legend_m14_commit` on the ladder, 19 Oct 2026 (session 13)

Input: the user's `new_matches.zip`: 10 match groups, **50 games, 11 wins** (`experiments/ladder_oct19b/<group>_<NN>_<side>.repl26a`,
`index.json` = map, our side, both drafts, score; we are side B in group cd6785ff). Tables: `experiments/ladder_oct19b/analysis/`
(`run_all.py` CSVs; `pergame.txt`). Tools added: `tools/strategy_v2/ladder_pergame.py`, `ladder_deaths.py`, `death_ctx.py`, `burst_ctx.py`
(all read our side of each game from `index.json`). Contest is left out of the farming and death numbers unless stated (3 games, 204 of our deaths).

## 1. Opponents and results

| Group | Profile (their draft) | Wins |
|---|---|---|
| 2306b82f | Varg / Ryth first; casters on stampede and contest | 0/5 |
| 25464f3d | C&I first + Tavi / Willow / Vendetta | 0/5 |
| 43bd73e8 | C&I first (C&I, Ren, Varg, Ryth, Stellar) | 1/5 |
| 44b9a95f | Varg first (Varg, Stellar, C&I, Ryth, Ren) | 2/5 |
| 5f7de946 | Tavi / Willow casters | 1/5 |
| 6713bf97 | Ren first (the old ifish table) | 2/5 |
| 78da97d8 | C&I first + Vendetta / Tavi | 1/5 |
| c3f76526 | Stellar first (IC) | 1/5 |
| c6ed5477 | Stellar first + Tavi | 1/5 |
| cd6785ff | C&I + Tavi (we are side B) | 2/5 |

## 2. What decides the games

Per game, 47 non-contest games (us / them): deaths 7.2 / 5.5, camp gems 733 / 993, gold 3,278 / 4,524, captures on our half / neutral /
their half 15.9 / 2.6 / 0.4 vs 19.3 / 6.1 / 1.3, camp damage per round 81 / 108; body time walking 50.4% / 46.1%, on camps 17.8 / 20.1,
capturing 1.9 / 4.5, dead 13.1 / 9.6.

1. **Farming speed.** Their finishing round *with us on the map* beats our *unopposed* pace (`_ch2` vs idle) on rows (348-358 vs 393),
   lanes (450 vs 462), monolith (408 vs 454), pilgrimage (570 vs 630) and ambush (499 vs 508). Same draft and no deaths for us (monolith,
   43bd73e8_03): they captured 1,126 camp gems to our 900 by r408 because they take every near group again right at its respawn (the 22-gem
   group 6 steps from their spawn at r19, 80, 137, 197, 270, 330, 381); we left the same group alone r92 -> r193 -> r315 while walking to far
   groups. Gold per 100 alive rounds by champion (them / us): Issac 174 / 111, Cassi 118 / 70, Ryth 167 / 102, Stellar 169 / 94; first emblem
   Issac r227 / r375, Ryth r209 / r330, Cassi r400 / r499. Their captures are spread over all bodies; ours pile on Ren.
2. **Close races lost on timing.** rows (5 games, 0 deaths both sides): we reached 990 banked at r345, they reached 990 at r355 and won at r358
   with a 22-gem bag while every one of our bodies walked to a 66-gem group. Same in 990-1023 and 990-1056.
3. **Burst deaths of Cassi & Issac.** 41% of our deaths start at >= 60% health 3 rounds before (theirs 34%); 99 of those 147 are Cassi or Issac;
   the nearest enemy is at distance 4-5 (35%) and 68% of the damage is spells; we hit back in only 32% of them.
4. **Objective rewards are stolen from dead tiles.** Stampede vs the Varg-first team: we killed the 360-gem objective all 4 times (damage 17,400 /
   0, 11,931 / 3,669, ...) and captured once; their Ren and Stellar stood on the dead gem tiles of the group while our ring stood at distance 4,
   so the reward landed under them. Against IC we did the same to them: they killed it 3 times, we captured all 3 (1080-0).
5. **Contest: 0/3, deaths 87, 66, 51.** The first team fight at the centre triple (r30-45) is lost every time (our blob of 6 bodies against
   5 casters hiding in the altar bush; our Ren, at full health, completed a recall home at r31 as the fight started), then bodies keep walking
   into the centre and die at full health without hitting back. They win on gold (24,186 vs 2,522 in the 0-0 game) or by monoliths (r1094, r1758).
6. **Camp pulling.** Fragment (same draft): they woke an elk and stepped back; our Ren walked into its range and stood next to it for 8 rounds
   (740 -> 0, killed by the camp); Cassi & Issac at 220/700 stayed in the field and died to area casts.

No fuel problem: 72 of our turns roll over, all in rounds 1-6.

## 3. What was built and measured (session 13)

See AGENTS.md §S13 for the live state, `experiments/wip/x_s13.patch` (coordinator switches) and `experiments/wip/x_zone.patch` (zones agent).
