# x_fight7: why our champions die, and fewer deaths (agent fight7, session 7)

Baseline `bots/_b7`, copy `bots/_x_fight7` (every new switch default off = `_b7` behaviour until the final patch), patch
`experiments/wip/x_fight7.patch`, outputs `/tmp/fight7/` (benches `baseu/` (traced baseline), `ev/` (variants)).
New tool: `tools/analysis/fight_deaths.mjs` (needs an `XM_TRACE` build of "us"; the traced copy used here, `_f7u`, also prints
`FY` lines: dist home, task, recall possible, remembered hidden enemies, visible enemies within 12, and `KIT` lines).

## 1. Death breakdown (traced `_b7` = `_f7u`, 56 maps, both sides, 112 games vs `_lad`)

Note: the trace build does not play exactly like `_b7` (debug-only code still shifts games: `_f7t` (plain XM) matched `_b7`
in 96/112 games, `_f7u` in 31/112; `_f7u` vs `_lad` 43.8 where `_b7` vs `_lad` is 56.2). Mirror games are that chaotic; the
breakdown is distributional, so it is still valid, but every A/B below uses the plain `_b7` as the baseline.

vs `_lad` (ladder proxy): 13.3 body deaths per game vs their 9.6. Categories (bodies; C&I pair deaths count 2):

| category | share | what |
|---|---|---|
| fled after an escapable fight choice | 33.9% | chose a fight in the 15 rounds before, then walked away in reach and was caught |
| fled | 24.8% | walked away in reach and was caught (no escapable choice before) |
| cornered after a choice | 21.2% | chose an escapable fight, ended trading with can_escape = 0 |
| cornered | 9.2% | |
| fighting, still escapable | 4.8% | the estimate was wrong to the end |
| no decision line / channel / camp | 4.4 / 1.2 / 0.5% | |

- Fleeing deaths (59%): flee started 21+ steps from home in 59% (13-20: 28%); advantage at the flee < 0.63 in 84%
  (heavily outmatched); recall possible in 7%; killers Stellar 28%, Ren (dash) 24%, Varg 16%, Ryth 13%, Issac 9%.
- Deaths after an escapable choice (61% of deaths): the choice was mostly against ONE visible enemy (1v2 40%, 1v1 18%, 1v3 12%);
  1-3 more enemies arrived afterwards in 85%; rule: margin (proactive) 66%, fight-back 24%.
- Victims: Issac 27%, Cassi 23% (pair = 50% of body deaths), Stellar 15%, Ren 14%, Varg 11%, Ryth 9%.

Traced examples (`/tmp/fight7/scripts/tl.mjs REPLAY TY R0 R1` prints a body's decisions with every unit within 12):
- eight A r140-157, Stellar: the advantage flips 4.7 -> 0.96 -> 18.5 -> 5.1 -> 17.6 -> 1.36 -> 12.5 -> 0.50 as enemies drop in
  and out of sight (ne 1 <-> 2-3). Stellar steps toward, then away, every round between (17,12) and (19,10) for 9 rounds without a
  shot while Issac closes from 8 to 2 tiles; at r149 it is in reach and cornered (adv 0.34) and dies fleeing.
- corners B r82-98, Issac (22 gems): adv 0.72 (ne 2) -> 5.9 (ne 1: their Ryth hidden for a round) -> 0.81; not in reach and not
  isolated, combat() declines and returns, so `tribute()` (bag >= tribute_risky with an enemy near) walks it toward the altar
  past the enemies; caught at r90 (can_escape 0, adv 0.15-0.77), dies at r98.

Two mechanisms: (1) **visibility flicker**: combat() counts only enemies visible this round, so an enemy behind a bush or at the
vision edge for one round makes a losing fight look like 5-18x; (2) **no early retreat unless isolated**: a body that declines
a fight against a stronger group keeps doing its task (farm walk, bank walk) until they are in reach, and then it is too late
(same speed, 13-21+ steps from home).

## 2. Switches built (params.h, all default off in `_x_fight7`)

| switch | what |
|---|---|
| `fm_age` (+ `fm_w`, `fm_range`) | combat(): enemies seen in the last fm_age rounds, hidden now, still count in the enemy side (predicted 1 tile closer per unseen round) |
| `threat_flee_adv` | walk away before they reach us when the estimate is below this, also when not isolated (was isolated/reserve only) |
| `unk_w` (+ `unk_side0`, `unk_need`) | a proactive fight (margin rule, not in reach) must also beat the enemies not accounted for, weighted by how deep we stand toward their spawn |
| `fh_rounds` (+ `fh_mult`) | after walking away outmatched, proactive fights need fh_mult x the margin for this many rounds |

## 3. Results (56 maps, both sides, 112 games per cell; win % all / official 17, deaths us-them over 112 games)

Baseline `_b7`: vs `_lad` 56.2 (1315-1217), `_r2` 73.2 (962-1760), `_v6` 92.9 (1160-1761), `_devci` 93.8 (790-1773),
`_L0` 80.4 (935-1808): 5-opponent mean **79.3**, our deaths 9.22 per game, theirs 14.86. Pace (17 official vs idle) 565.2.

| bot | settings | vs `_b7` | `_lad` | `_r2` | `_v6` | `_devci` | `_L0` | 5-opp mean | our deaths/game (5 opp) | their deaths | pace |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `_b7` | baseline | (50) | 56.2 | 73.2 | 92.9 | 93.8 | 80.4 | 79.3 | 9.22 | 14.86 | 565.2 |
| `_f7a` | fm_age 3 | 55.4 / 52.9 (1102-1059) | 48.2 (1201-1052) | | | | | | | | |
| `_f7b` | fm_age 3, threat_flee_adv 0.8 | 51.8 / 52.9 (956-1169) | 62.5 (965-1293) | 82.1 (699-1753) | 92.0 (758-1687) | 96.4 (657-1700) | 73.2 (849-1707) | **81.2** | **7.01 (-24%)** | 14.54 (-2%) | 565.2 |
