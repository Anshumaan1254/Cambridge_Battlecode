# x_top: the top-style sparring bot `bots/_top` (agent `top`, session 7)

Status (first build, 14:00 container clock): `bots/_top/src/{bot.cpp,draft.cpp,main.cpp}` written from `bots/starter-cpp`
(no legend logic), builds, 0 faults. Rules and the realism check: see the end of this file (updated as I go).

Debug build with a per-turn trace line: `cp -r bots/_top/src bots/_topd/; sed -i '1i #define TOP_TRACE 1' bots/_topd/src/bot.cpp; cambc build _topd`,
read with `node /tmp/top/stdout.mjs REPLAY` (unwrapReplay of `team-a.stdout`).

## Bugs found while bringing it up (useful for anyone writing a bot on this API)
- A DEAD camp has no live record: `sdk_camp` returns 97 (not visible); use `sdk_camp_state` (0 = dead) for liveness, else
  the bot attacks a dead camp forever (attack throws "Target must be a visible enemy or neutral camp").
- Recall while a live camp is within 3 is cancelled every round (the body bled to death "recalling"): step out of camp reach first.
- A stand-still watchdog must not count turns spent attacking.

## Final state (agent `top`, session 7)

`bots/_top/src` (bot.cpp ~1550 lines Allman style, draft.cpp, main.cpp), patch `experiments/wip/x_top.patch` (vs `starter-cpp/src`),
source hash a629b67deee1. Debug trace: define `TOP_TRACE` (see above); `why=` labels each turn's rule.

What it does: draft Varg, Stellar, C&I (+Ryth, +Ren; Tavi instead of Ren when one group holds 40%+ of the gems). Items: Durability-health
emblem (+Bruiser-health for Ren/Ryth/Cassi), then Power in the damage stat forever; Tavi: Treasure-focus first, shops anywhere.
Farming: per body one claimed group (shared-memory byte = group id+1), score (gems+0.3 gold)/(walk+wait+kill+6), own half first
(d_ally+2 <= d_enemy), then neutral band, then anything; kill-time/damage-taken estimate per kit (solo if taken <= 1.6 x max HP,
a pair job is joined, started alone only if taken <= 3 x HP); Varg hits the camp with most neighbours; spells on camps when no enemy within 9;
Cassi and Issac follow each other's claim (pair deaths were 46% of body deaths); the best converter (Varg>Issac>Stellar>Ryth>Cassi>Ren) captures,
others yield. Recall on the reward tile the round after stepping on it when HP < 60% or gold >= 150 and no enemy within 7 (and no live camp within 3);
bank at bag >= 44, or >= 12 with an altar within 6 walking steps, or a winning bag. Fights: always hit what is in reach first
(melee: attack, then step), cast the best ready damage spell/area/stun on the focus (lowest HP, Cassi/Issac first), reset, second swing;
engage within 6 when (HP x dps) >= 1.2 x theirs counting allies within 4 (or when under fire and ratio >= 0.7); back off when ratio < 0.7;
retreat below 35% (recall if safe, else stun + run, or finish a nearly dead enemy in reach); priority = 1000 - 20 x distance to the nearest enemy, +300 with a stun ready.

### Results (bots/_top vs the shipped builds, official 17 maps, 34 games unless noted)
- Pace vs idle: mean **827** rounds to 1000 (m4 524.5). Without the two objective maps (contest 2000 = round-limit win, stampede 1760) 687.
  Per map: ambush 932, collision 742, corners 493, eight 565, elkring 570, expanse 794, fragment 710, interlock 707, lanes 590,
  monolith 475, packs 488, pilgrimage 989, rows 614, rushbait-v2 1100, swirl 538. 34/34 wins, 0 faults, 6 rollovers on gen16 (rounds 1-3 only).
- `_m4` as A vs `_top`: **_top wins 8.8% (3/34)**, deaths m4 133 - _top 385; 56-map pool (112 games): `_top` 6.2% (7/112), deaths 353-946.
  `_m5a` vs `_top` (official 17): `_top` 0/34, deaths 114-440. So it is NOT competitive (target was 40%+). `_top` beats m4 only on rushbait-v2
  (m4 died 27 times there in one game); m4 wins everything else.
- KPIs from `tools/strategy_v2/run_all.py` on 17 m4-vs-_top games (_top = "Them"; real top teams in brackets):
  deaths per game 12.6 (4.8), share of hit rounds without hitting back 0.62 (0.55), damage-stat points per 1,000 gold 28.4 (31.9),
  gold earned 3053 (5123), time alive 79.7% (91.0%), time on camps 21.2% (21.2%), camp damage per camp round 75.9 (118.5),
  captures per game 14.9 (23.7), casts 143 per game (top ~220, m4 356), first emblems r187-445 (top 88-215).
  Style-level KPIs (camps share, build, damage per gold, hit-back share) look like the top teams; survival, income and damage output do not.

### Known weaknesses / ideas (in order of size)
1. Survival: 12.6 deaths/game; 59% on its own half, 3+ enemies near in 36%, usually even fights lost to focus fire. Burst deaths 43%.
   m4's early deathball meets split farmers (swirl r18-25). Pairing Cassi+Issac cut deaths 459 -> 385; pairing Stellar->Varg and Ren->Ryth too gave no gain
   (385 -> 387, pace 827 -> 796; reverted for spec fidelity: `/tmp` copy not kept, the change is a 10-line switch in `choose_group`).
2. Income: gold 3053 vs 5123; walking 40-55% of body-rounds, 5-9% of time on respawn waits; no heal-trip planning, no crystal shortcuts, no
   capture-recall unless hurt or rich. First emblem too late for the same reason.
3. Objective maps: contest (monoliths) and stampede (one fused 6-elk group) are not cleared (2000 / 1760 rounds): nobody starts a group needing 4 bodies.
4. Not implemented: dash use, wards, altar locks, camps in the fight estimate, spacing against splash, stun-before-target-acts timing.
Do not use `_top` as evidence that a rule works against the top teams; use it as an extra sparring partner whose economy is weak but whose
fight order (hit first, cast, commit) and builds are top-style. Tuning against m4 was not done (parameters are the spec's).
