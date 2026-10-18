# x_px: a sparring proxy of the ladder's top teams (agent `proxy`, session 8)

Goal: a sparring bot that reproduces the ladder fight gap of `legend_m5` (`_m5a`) vs the top 3 (docs/strategy_v2/07_LADDER_M5_18OCT.md),
then use it to judge fight fixes for `_m5a`.

## Build recipes
- Working copy `bots/_px` = `bots/legend` + `experiments/wip/x_px.patch` (switches all 0 = legend):
  `SRC=bots/legend tools/variant.sh _px && (cd bots/_px && patch -p1 --no-backup-if-mismatch < ../../experiments/wip/x_px.patch)`.
- Switches (params.h, end of the struct): `px_mode` (1 = top-team fight rules in combat(): team target = lowest-health body we can
  hit this turn, a team kill this turn first, Cassi/Issac and channelers preferred; engage at `px_engage` local power, hit back down to
  `px_fightback`, commit down to `px_commit`, leave below `px_retreat_hp`, walk away from a group below `px_flee_adv`; the legend
  isolated / reserve / outmatch exits are skipped), `px_stun_first` (engage(): stun the target in reach first, any type),
  `px_ally_spells`, `px_hold` (do not step into an enemy's next-turn reach for a proactive fight: let them walk in, at most N rounds),
  `px_burst_wait` (proactive fight with all spells on cooldown: hold while one is <= N rounds from ready).
  `build_style 5` = style 3 health emblems + a Treasure emblem in the damage stat + Power forever (2nd/3rd teams' builds);
  `build_style 6` = one Durability health emblem + Treasure + Power.
- `PRESS` = `steal_hp_frac=0.4f enemy_half_penalty=4.f deny_bonus=0.4f gank_bag=15` (contest neutral / enemy-half groups).
- Variants: `SRC=bots/_px tools/variant.sh _pxN key=val ... --define "LEGEND_DRAFT 8,4,3,0,9"` (1st/3rd teams' draft: Ren, Stellar, C&I, Ryth, Varg).

| Proxy | Recipe |
|---|---|
| `_px0` | `SRC=bots/legend tools/variant.sh _px0 build_style=3 --define "LEGEND_DRAFT 9,4,3,0,8"` |
| `_px1` | `_px` px_mode=1 build_style=3, draft 8,4,3,0,9 (before px_hold existed; same behaviour with hold 0) |
| `_px2` | `_px` px_mode=1 build_style=5 PRESS, draft 8,4,3,0,9 |
| `_px3` | `_px2` + px_hold=3 px_burst_wait=3 |
| `_px4` | `_px3` + px_engage=1.3f px_fightback=0.8f |
| `_px5` | `_px2` + px_fightback=0.f px_commit=0.3f px_flee_adv=0.3f |
| `_px6` | `_px5` + px_hold=2 px_burst_wait=2 |
| `_px7` | `_px` px_mode=1 px_engage=1.3f, legend builds (style 2), draft 9,4,3,0,8 (2nd team: Varg, Stellar, C&I, Ryth, Ren) |
| `_px8` | `_px` px_mode=1 px_hold=2, draft 9,4,3,0,8 |
| **`_px9`** | `_px` **px_mode=2** (targeting only: legend's fight decision and exits, plus the lowest-health body in reach as target, a team kill this turn always taken, stun the target first), legend builds, draft 9,4,3,0,8: `SRC=bots/_px tools/variant.sh _px9 px_mode=2 --define "LEGEND_DRAFT 9,4,3,0,8"` |
| `_px10` | `_px` px_mode=1 px_engage=1.6f px_fightback=0.873f px_flee_adv=0.8f, draft 9,4,3,0,8 |
| `_px11` | `_px9` + build_style=5 |
| `_px12` | `_px9` + PRESS |

## Calibration (`_m5a` = "us" vs proxy = "them", official 17 maps; win% = proxy wins of 34; KPIs on the 17 side-A games)
Ladder targets (07): our deaths 189-206 vs 43-74 per 20 games (2.8-4.8x), burst share of our death incidents 52-69% (theirs 17-26%),
killed by ranged 56-61%, fight damage ratio 0.48, hit-nobody-back 0.66 vs 0.53, neutral captures 41 vs 147.

| Proxy | proxy wins | deaths us-them (34 games) | dmg ratio | hit-no-back us/them | burst us/them | ranged us | neutral caps us/them |
|---|---|---|---|---|---|---|---|
| ladder (1st) | 90% | 198-74 (20 games) | 0.48 | 0.66 / 0.53 | 52% / 22% | 56% | 41 / 147 |
| `_px0` | 35.3 | 329-393 | 1.04 | 0.50 / 0.54 | 42% / 42% | 46% | 68 / 62 |
| `_px1` | 32.4 | 380-425 | | | | | |
| `_px2` | 35.3 | 316-461 | 1.09 | 0.50 / 0.51 | 39% / 41% | 35% | 70 / 53 |
| `_px3` | 29.4 | 353-492 | | | | | |
| `_px4` | 26.5 | 444-501 | | | | | |
| `_px5` | 5.9 | 243-677 | | | | | |
| `_px6` | 14.7 | 306-663 | | | | | |
| `_px7` | 50.0 | 355-458 | | | | | |
| `_px8` | 47.1 | 389-429 | | | | | |
| **`_px9`** | **64.7** | **405-338** | **0.72** | 0.55 / 0.50 | **46% / 39%** | 39% | **39 / 76** |
| `_px10` | 38.2 | 387-410 | | | | | |
| `_px11` | 35.3 | 355-329 | | | | | |
| `_px12` | 38.2 | 361-349 | | | | | |
| ref `_L5d` (legend, draft 9,4,3,0,8 only; ledger cell `_L5d_vs__m5a`) | 52.9 | 392-341 | | | | | |

## Findings so far
- Ladder vs local: on the ladder `_m5a` deals 5.5k champion damage per game and takes 13.4k (Stellar casts on champions 5.2 per game);
  against our proxies it deals ~19k and takes ~17k. Our deaths per game are the same (9.9 ladder, 9.8 vs `_px2`): what the ladder
  teams do differently is **not getting hit** (their deaths 3.7 per game vs the proxy's 12.9).
- Ladder top teams walk under fire much less (no-hit-back rounds spent walking above 50% health: 134 / 75 vs our ~300; proxies ~310).
- Stats at r300 are about equal (Stellar focus 170-250 for every side, ladder or local): the gap is not the item build at r300.
- Ladder burst pattern (interlock r269, 1st): Stellar and Ren walk to range 4 of a lone Varg at 70% and cast in the same round
  (320 + 325), Stellar's area finishes next round. Cohesion: ally within 4 tiles 61% of body-rounds (us 53%, proxies 47%).

- Standing and trading (px_mode 1 with fightback 0: `_px5`, `_px6`) is a disaster (677 proxy deaths in 34 games). Walking in at even
  power (`_px1`-`_px4`) loses too. Making the proxy more aggressive in our code family never reproduced the ladder.
- **What worked: `px_mode=2`** = legend's own fight decision, only the targeting changed (hit what is in reach now, lowest health,
  team kill first, stun first). `_px9` beats `_m5a` 64.7% (official 34) and its KPIs move toward the ladder: damage ratio 0.72,
  our deaths 1.2x theirs, burst 46% of our deaths, neutral captures 39 vs 76, Stellar our top killer, "they hit first" fights
  deaths 117-32. Damage builds (style 5) and PRESS (more enemy-half farming) both made it weaker (`_px11`, `_px12`).

## Phase 2: fixes for `_m5a` judged against the proxy
- Copy `bots/_x_px` = `_m5a` + `x_doc_m5.patch` (doctrine switches, all off) + the px code (switches off):
  patch `experiments/wip/x_pxfix.patch` (`SRC=bots/_m5a tools/variant.sh _x_px && (cd bots/_x_px && patch -p1 --no-backup-if-mismatch < ../../experiments/wip/x_pxfix.patch)`).
  Variants `SRC=bots/_x_px tools/variant.sh _xpN key=val ...`.
- `_xp1` = `px_mode=2` (the proxy's targeting on our own draft and builds). `_xp2` = `_xp1` + px_stun_first=0. `_xp3` = `_xp1` + px_ally_spells=0.

| Fix | vs `_m5a` (all / official / deaths) | vs `_px9` official | vs `_fA` | vs `_ST` | pace |
|---|---|---|---|---|---|
| `_m5a` reference | - | 35.3 (88: 47.7), deaths 405-338 | 76.1 / 79.4 (611-956) | 73.9 / 91.2 (526-849) | 523.4 |
| `_xp1` px_mode=2 | **52.3 / 58.8 / 585-719** | **55.9** (340-296) | 73.9 / 79.4 (520-964) | 71.6 / 82.4 (511-860) | 521.9 |
| `_xp2` = `_xp1` + px_stun_first=0 | official 58.8 (319-414) | | | | |
| `_xp3` = `_xp1` + px_ally_spells=0 | official 61.8 | | | | |
| **`_xp4`** = `_xp1` + camp_in_fight=3 | **52.3 / 61.8 / 580-710** | **64.7** (348-352) | 72.7 / 82.4 (561-1015) | 73.9 / 82.4 (465-909) | 521.9 |
| `_xp5` = `_xp1` + burst_exit=1 | official 58.8 (272-403) | 58.8 (355-333) | | | |

gen16 fuel rollovers (`_xp1` and `_xp4` vs `_m5a`, one game each): 8 per team, all in rounds 1-3 (= baseline). 0 faults in every cell.

KPIs against the proxy (`tools/strategy_v2/run_all.py`, 17 side-A games, "us" = the bot named first):
| | `_m5a` vs `_px9` | `_xp4` vs `_px9` | ladder (1st) |
|---|---|---|---|
| wins | 5/17 | 11/17 (34 games: 64.7%) | 2/20 |
| deaths us-them (34 games) | 405-338 | 348-352 | 198-74 (20) |
| fight damage ratio | 0.72 | 0.87 | 0.48 |
| burst share of our deaths | 46% | 37% | 52% |
| killed by ranged | 39% | 28% | 56% |
| hit-nobody-back us / them | 0.55 / 0.50 | 0.52 / 0.51 | 0.66 / 0.53 |
| neutral captures us / them | 39 / 76 | 56 / 64 | 41 / 147 |

## Verdict
- **Proxy**: `_px9` (recipe above) is the best stand-in we have: it beats `_m5a` 64.7% on the official maps (52.3% on 88 distinct
  games) and moves every fight KPI in the ladder's direction (burst 46%, damage ratio 0.72, Stellar our top killer, neutral captures
  half theirs), but not all the way (our deaths 1.2x theirs, not 2.8-4.8x; damage ratio 0.72, not 0.48; ranged kills 39%, not 56%).
  Every attempt to make it more aggressive (walk in at even power, stand and trade, hold for the first volley, damage builds, PRESS)
  made it weaker. Use it with `_fA` and `_ST` as the guard set, not as proof about the real top teams.
- **Best fix**: `_xp4` = `_m5a` + `x_pxfix.patch` with `px_mode=2 camp_in_fight=3` (everything else default). It passes every guard
  (88 distinct vs `_m5a` 52.3 / official 61.8 / deaths 580-710; `_fA` -3.4 all, +3.0 official; `_ST` +0.0 all, -8.8 official
  (34 games); pace 521.9; 0 faults; rollovers 8/8) and beats the proxy 64.7% where `_m5a` wins 35.3%.
  `_xp1` (`px_mode=2` alone) is the simpler alternative: 52.3 / 58.8, proxy 55.9.
  What `px_mode=2` changes (combat(), right before the fight is executed; the fight decision itself is legend's): the target is the
  body we can hit this turn (attack reach, or 4 with a spell up) with the lowest health, a body the team kills this turn first (our hit
  x2 with a reset ready + best ready spell + each visible ally next to it: its strength and half its best spell), Cassi/Issac -150 and
  channelers -200 health-equivalent, Ren skipped when our health < 3x his reflect; a team kill this turn is always taken (not on their
  spawn); engage() stuns the target first whatever it is (ablation `px_stun_first=0`: same 58.8 official, so the targeting carries it).
- Did not work (proxy side): px_mode 1 variants (`_px1`-`_px8`, `_px10`), build_style 5 (Treasure + Power), PRESS. (fix side):
  burst_exit on top of px_mode=2 (`_xp5`: proxy 58.8, `_m5a` 58.8: no gain over `_xp1`); stun-first and ally spells are not what
  carries the gain (`_xp2` 58.8, `_xp3` 61.8 official vs `_m5a`).
- Held-out (gold, gold2, obj; 100 games) `_xp4` vs `_m5a`: **59.0** (deaths 1885-2085); with the 88: 105/188 = 55.9%
  (`_xm5c`, camp_in_fight alone: 49.0 held-out). Next: ship decision for the coordinator, then a ladder A/B (the only real judge). Tools: `kpi.sh`-style runs = `tools/bench.py A B --out DIR` then
  `tools/strategy_v2/run_all.py OUT DIR_of_side_A_replays` (replays renamed `<group>_<NN>_<map>.repl26a`).
