# x_fight: fewer deaths, more won fights vs the real ladder teams (agent `fight`, session 7)

Baseline `bots/_m4` (= shipped `legend_m4`); copy `bots/_x_fight` (every new switch default off = `_m4` behaviour);
variants `bots/_xf*`. Outputs in `/tmp/fight/`. Patch: `experiments/wip/x_fight.patch` (`cd bots && diff -ruN _m4/src _x_fight/src`).

## Diagnosis
- Ladder (17 games of legend_st, 232 deaths, `death_ctx.mjs --list`): of the 73 deaths "at 75%+ health" (burst), **53 are
  Cassi or Issac** (the healthy partner dying with the weak one); only 20 are other bodies, 10 of them on contest.
  So "burst at full health" is mostly the pair link, not hidden enemies.
- `_m4` vs `_fA` (official 17, 34 games): 64.7%, deaths 409-348 (we die more than the proxy and still win); our deaths
  46% Cassi + Issac, 64% on our own half, 54% with the enemy >1.2x our health within 6 (ladder 60% / 58%).
- Traced `_m4` vs `_fA` (`_xfT` = `_m4` + XM_TRACE, side A, eight interlock fragment swirl collision elkring packs; 78 deaths,
  pair deaths counted per body; `/tmp/fight/dstat.mjs`, `/tmp/fight/flip.mjs`):
  - first in-reach decision before death: flee without escape 20, cornered fight 18, fight back with escape 12, out of reach 9.
  - visible-enemy count jumps (1 -> 3-5) on the turn the body enters reach; 27 of 78 deaths had 2+ fight/flee flips in the last stretch.
  - per in-reach turn, death within 8 rounds / an enemy killed within 6 tiles and 8 rounds:
    no escape (`esc=0`): fight 13-43% / 32-40%, flee 37-39% / 15-19%; with escape: fight at adv 0.8-1.3 14% / 27%,
    flee 1-8% / 9-18%. Being without escape at all is what kills (~40%); once there, fighting trades better than fleeing.

## Switches (params.h, all default off)
- `fight_mem` (+ `fight_mem_w` 0.75, `fight_mem_r` 8): combat() counts enemies seen 1..fight_mem rounds ago, now hidden,
  within fight_mem_r of their last tile (spells assumed ready); they also count for the outmatch enemy count.
- `pair_pool`: Cassi + Issac both on our side count 2 x min(health) instead of the sum.
- `kill_reach`: 'killable' counts an ally's hit only when that ally is within its reach of the target.
- `fight_smooth`: adv = last^a x now^(1-a) (geometric blend) when the body also judged a fight last round.
- `flee_fail_turns` (+ `flee_fail_adv` 0.2): after this many in-reach flee turns that lost health with the chaser still
  within its hit reach, hit back.
- `flee_hold` (+ `flee_hold_d` 3, `flee_hold_adv` 0.2): for flee_hold rounds after an outmatch flee the bars widen, an
  unseen enemy (seen within threat_memory) within outmatch_flee_dist + flee_hold_d keeps us walking home, and rallies
  are not answered. Traces: bodies fled to 8 tiles, farmed back toward the group, and were caught 3-4 rounds later.
- Trace-only: `FIGHT_TRACE` define prints a `TK` line per turn with an enemy within 10 (path, task, enemy distance,
  in-danger flag, health); `/tmp/fight/tk.mjs` prints the 12 rounds before each death.

## Results
Screen: official 17 maps, both sides (34 games per cell; one cell's SD is ~8.5 points: a screen only).
Control `_xf0` (= `_x_fight`, all switches off) vs `_m4`: 50.0, deaths 318-318 (plays identically).

| Variant | vs `_m4` (deaths ours-theirs) | vs `_fA` |
|---|---|---|
| `_m4` | - | 64.7 (409-348) |
| `_xf1` fight_mem 3 | 50.0 (298-313) | 55.9 (366-407) |
| `_xf2` pair_pool | 47.1 (338-367) | 58.8 (403-343) |
| `_xf3` kill_reach | 44.1 (340-300) | 61.8 (403-345) |
| `_xf4` cornered_margin 0 | 44.1 (419-284) | 61.8 (402-458) |
| `_xf5` cornered_margin 0.4 | 44.1 (374-255) | 52.9 (469-327) |
| `_xf6` fight_smooth 0.5 | 47.1 (312-280) | 73.5 |
- 13 of 34 games change winner between `_m4` and `_xf1` vs `_fA`: fight changes flip whole games; judge on 112+ games.
