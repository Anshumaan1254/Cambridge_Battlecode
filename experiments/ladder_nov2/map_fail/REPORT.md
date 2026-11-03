# Why we lose on the worst maps: ranked replays since Nov 2 (helper-agent analysis, Nov 3 2026)

Saved by the main session from the helper's reply (the helper could not write .md files). Scripts and data: this folder and `out/`.

**Data.** Every RANKED game created since 2026-11-02T00:00Z on the 5 worst maps — 00crater 6, 00gem_fields 4, 00gemfight 5,
01elk_arena 8, 01islands 8 (31 games, 5-26) — plus 00quarry 11, 00oasis 10, 01corridors 13 for pattern counts: 65 games (12-53), all
of them; 32 replays downloaded today. 4-8 games per map, so per-map numbers are rough. Versions: v84 in 57 games, v85 in 8, none yet for
v86 / v87. 00crater 7355a70b and 5787c757 are the same game played twice (one piece of evidence). "a/b" = us / opponent. A "big
group" is a camp group worth 30+ gems; a "cycle" runs from one respawn of a group to the next.

## 1. Per-map tables

### 1a. Timeline (mean of the losses; banked gems)

| map | games (W-L) | r200 | r400 | r600 | r800 | final | collected | lost on death | decided (loser 150+ behind for good) |
|---|---|---|---|---|---|---|---|---|---|
| 00crater | 6 (1-5) | 25/62 | 102/150 | 160/298 | 262/462 | 460/1026 | 425/1081 | 53/105 | r842 (earliest r254) |
| 00gem_fields | 4 (0-4) | 97/166 | 180/325 | 280/468 | 415/695 | 551/1020 | 563/1040 | 34/24 | r662 (earliest r337) |
| 00gemfight | 5 (0-5) | 9/136 | 62/266 | 73/530 | 81/880 | 92/1030 | 207/966 | 82/4 | r317 (earliest r179) |
| 01elk_arena | 8 (1-7) | 17/63 | 41/154 | 41/315 | 65/447 | 111/985 | 76/1030 | 10/45 | r650 (earliest r145) |
| 01islands | 8 (3-5) | 54/89 | 176/224 | 358/450 | 549/749 | 747/1023 | 751/1056 | 6/15 | r837 |
| 00quarry | 11 (2-9) | 47/103 | 114/245 | 140/450 | 164/720 | 220/1021 | 254/1012 | 54/38 | r510 |
| 00oasis | 10 (2-8) | 58/30 | 98/100 | 146/200 | 189/336 | 311/1016 | 314/1034 | 60/59 | r896 |
| 01corridors | 13 (3-10) | 7/33 | 63/115 | 100/250 | 162/380 | 483/1100 | 731/1127 | 189/84 | r1028 |

- elk_arena: the centre group G0 (72 gems, 2 elks) is the only group that pays gems; we banked 0 in 5 of the 7 losses and got 534 of its
  7,742 gems.
- gemfight: the opponent took the centre group G0 (78 gems) in 41 of its 43 cycles.

### 1b. Economy (losses)

| map | item shards r300 | shards r600 | camp gold r1-300 | camp attacks r1-300 | first capture |
|---|---|---|---|---|---|
| crater | 10/18 | 26/43 | 236/440 | 152/235 | r92/r43 |
| gem_fields | 14/26 | 40/50 | 200/426 | 168/263 | r54/r40 |
| gemfight | 10/24 | 19/74 | 292/470 | 141/237 | r57/r27 |
| elk_arena | 33/49 | 71/142 | 855/1350 | 139/210 | r37/r18 |
| islands | 33/47 | 110/140 | 1193/1383 | 335/373 | r18/r15 |
| quarry | 24/37 | 51/91 | 675/925 | 165/212 | r14/r12 |
| oasis | 27/28 | 57/86 | 652/644 | 170/242 | r29/r26 |
| corridors | 34/28 | 69/75 | 998/762 | 368/303 | r53/r57 |

In wins the shard gap flips: elk_arena 80/14 at r300, quarry 30/22, oasis 30/22.

### 1c. Deaths and camps (per game, all games)

| map | deaths | killed by camp | champion kill with camp hits in last 5 rounds | our death context: fight / caught / jumped while farming / camp | own/mid/their half | most deaths near | passive camp damage | big-group cycles we opened → they took |
|---|---|---|---|---|---|---|---|---|
| crater | 12.0/9.8 | 1.0/0.2 | 2.7/1.2 | 41/18/5/6 | 26/42/4 | G2 (36 gems, elk) 32 | 4470/2507 | 29/57 |
| gem_fields | 14.0/15.0 | 3.0/0.5 | 3.2/2.5 | 25/16/2/12 | 20/22/14 | G5 (71 gems, elk) 25 | 6090/1110 | 8/32 |
| gemfight | 11.6/3.0 | 0.2/0.6 | 4.2/0.4 | 28/26/2/1 | 27/30/1 | G0 (centre) 25 | 2260/964 | 8/8 |
| elk_arena | 16.4/16.9 | 2.2/1.4 | 3.4/2.4 | 90/17/5/18 | 53/51/27 | G0 (centre) 50 | 4238/1808 | 28/46 |
| islands | 2.5/3.5 | 1.1/1.6 | 0.9/0.1 | 9/1/1/9 | 5/11/3 | G3 (58 gems) 7 | 5072/2655 | 13/147 |
| quarry | 10.5/10.5 | 0.1/0.0 | 1.5/1.1 | 86/27/2/1 | 64/48/4 | G8 (46 gems) 67 | 540/180 | 38/89 |
| oasis | 21.9/20.4 | 4.3/2.7 | 5.5/3.7 | 95/65/14/43 | 121/68/30 | G6 (36 gems) 44 | 11312/5940 | 30/53 |
| corridors | 10.2/8.9 | 3.3/3.4 | 2.0/1.0 | 48/26/13/43 | 34/62/36 | G1 (58 gems) 39 | 8518/4551 | 70/197 |

Passive camp damage is an estimate: camp strength × hits taken in runs of 5+ hit-rounds in which the body attacked nothing. Marcella is
the top killer: 38 of our 72 deaths on crater, 39/58 on gemfight, 53/131 on elk_arena, 47/116 on quarry.

### 1d. Time use (losses, % of body-rounds)

| map | dead | walk | farm | capture | idle |
|---|---|---|---|---|---|
| crater | 10/7 | 67/59 | 7/12 | 1/3 | 2/5 |
| gem_fields | 16/16 | 54/48 | 7/11 | 3/3 | 2/4 |
| gemfight | 19/4 | 54/51 | 8/15 | 4/6 | 2/6 |
| elk_arena | 15/11 | 54/39 | 6/11 | 6/9 | 3/9 |
| islands | 3/5 | 45/48 | 20/21 | 5/5 | 15/9 |

- Respawn blocks (body-rounds on a group's tile after its respawn was due): islands 199/0 (144 of them by one body), corridors 68/1,
  elk_arena 115/18 (all short).
- Oscillation episodes: corridors 22 episodes / 685 rounds vs 3/62; crater 4/107 vs 3/79; elsewhere at most 1 of ours.
- Stalls in general do not separate the teams: 13.3k vs 15.7k body-rounds over the 65 games, 24k vs 31k over all 160 decoded games.

### Per-map mechanism

- **crater: S1 + S2.** 61x61; we walk 67% of the time; first capture r92 (theirs r43). They out-farm the north-centre group G2 (70 vs 25
  captures) and the two wolf groups at y=11 (130 vs 36). 54 of our 72 deaths are in fights the enemy opened.
- **gem_fields: mostly B1.** The two 71-gem elk groups sit beside the spawns' walking paths: we take 5.5x their passive elk damage and die
  to camps 3.0 vs 0.5 a game. The elk group nearer their spawn: they took 32 of 36 cycles; nearer ours: we took 19 of 30.
- **gemfight: S1 + S2.** Decided by r317. Deaths near the centre group 42 ours vs 6 theirs; we lose 82 gems a game in bags vs 4; 3.9x
  fewer shards at r600.
- **elk_arena: S1 → S2, B1 in the opening contest** (trace 98e86952, `gtrace.py … 0 1 420`): we open G0 at r9-13; when enemies appear 4-5
  tiles away our bodies stop hitting it but stay in elk reach; our Ryth goes 1200 → 35 hp and dies at r25; they farm G0 from r30 and
  capture it at r54. Later respawns: our bodies wait beside G0, often damaged (32 of them under 60% hp when it respawned), then leave (60
  cases) or stand without attacking (35) as 2,300-2,500-hp enemies arrive. In the win (bf8e7228) we took 12 of the 13 cycles we opened.
- **islands: close games, slower economy, plus B3 and B1.** B3: 648e1540 body 7 stood idle 166 rounds on gold group G20. B1: e28a17f2 body
  6 (Heart of Ruin) stood still 157 rounds at full hp beside an alive wolf+gold group, then next to the awake wolf for 50 rounds without a
  basic attack, then waited on that group's dead tile while a neighbouring elk (range 4) hit it, 1098 → 426 hp.

## 2. Failure patterns ranked by estimated games lost (overlapping)

**S1 — Opening economy gap (STRATEGY, ~25 losses).** In r1-300 the opponents make 28-68% more camp attacks on crater, gem_fields,
gemfight, elk_arena and quarry; their first capture comes earlier (by 49 rounds on crater, 30 on gemfight, 19 on elk_arena, 14 on
gem_fields); we walk as much or more (crater 1,150 vs 1,033 moves by r300); the item gap then decides the fights (z +12.3 in
`agent_fights/REPORT.md`). Levers: opening targets and travel; farm the gold groups instead of waiting at the contested centre (elk_arena
farm share 6% vs 11%).

**S2 — We open the big group and they take it (STRATEGY + tactics, ~15).** Opened by us → taken by them: elk_arena 28/46, gemfight 8/8,
oasis 30/53 (our deaths in those cycles 61 vs 38), quarry 38/89, crater 29/57. In wins we keep what we open (elk_arena 12/13, oasis
17/21, quarry 24/29). The tactical part is B1: farming stops when enemies appear but the body stays in the camp's reach.

**B1 — Passive camp damage (BUG-ish, ~6 losses).** Ours 703 runs, est. 367k damage, 80 deaths at run end; theirs 307 / 180k / 31. Our runs:
enemy within 6: 347 runs / 52 deaths (theirs 143 / 12); no enemy 269 / 22 (123 / 14); waiting on a dead group's tile 44 / 5 (21 / 1).
Examples: 98e86952 body 7 r13-25; 2988db7a body 6 r710-747 (on a dead tile, hit 34 times by elks, 95% hp → dead); e28a17f2 body 6
r716-760; df39df70 body 8 r1380-1400 (2200 → 474 hp with no attack). Code: brain.cpp `Brain::safety()` (l. 5361): the threshold is
`max(retreat_hp*max_hp, camp_in*4)` (~l. 5405) and `if (hp >= threshold) return false;` (~l. 5466) comes before the camp exit `if
(in_awake_camp_range() && camp_in > 0) { T_FLEE; step(~camp_danger) }` (~l. 5484); `v26_wait_safe` in `wait_group` (l. 8055-8070) only
applies within `radius + 4`; combat holds do not consult `camp_danger`. Hypothesis: a healthy body that stops hitting camps (enemy near,
hold, wait, capture) is never moved out of an awake camp's reach until hp < `camp_in*4`. Fix to test: in `camp_danger`, not the
nearest-to-camp shield and not hitting a camp this turn → step out before any hold / wait / capture. Caveat: `_85cz` (camp zone) measured
−57 locally: the exit must not cancel hits on an enemy that stands closer to the camp.

**B2 — Dash-walk and ping-pong loops the watchdog misses (BUG, ~2-3 losses, corridors).** d675c6c3 body 8 (Vendetta, 51% hp) r805-848:
dash (30,21) → (28,23), walk back, repeat every 8 rounds beside a sleeping group, no attack; again at r938 / r1042, body 5 at r1042 / r1617;
lost 894-966 at r2000 with 636 stalled body-rounds (513 with a dash) vs 287. b31fff63 body 7 (Marcella, 26% hp): (22,23)↔(22,24) for 67
rounds, 41 of them with no enemy within 7. 2988db7a: bodies 5, 7, 8, 9 in 5 loops of 20-33 rounds. Stalls containing a dash: ours 440 vs
221 over 160 games (20 vs 8 lasting 40+ rounds); corridors 82 vs 25. Code: any travel dash sets `cast_done` (brain.cpp l. 2454-2461);
brain.cpp:1443 `progress_watch(last_act_round==round || cast_done || target_hit_round==round)`; dash cooldown (8) < `v27_watch` (12,
params.h:1131) so a dash every 8 rounds resets the watchdog (the case its comment at l. 1980 says it was written for); `fz_osc = 0`
(params.h:939); when the watchdog fires (~l. 2015-2050) it only blacklists `task_group`, which does not break a home/flee flip-flop with no
group. Fix to test: travel dashes are not progress (or require > 3 tiles from the anchor); the remedy also forces a recall / home trip or
bans the tile pair.

**B3 — Respawn deadlock (BUG, ~1 loss).** 648e1540 body 7: idle r788-954 on G20's tile (23,39) at 55% hp, respawn overdue r838-982;
16af1597 body 2: r1278-1339 on G1's tile (58 gems), an enemy 3 tiles away, respawn overdue 62 rounds (stalled body-rounds ours 398,
theirs 0); b74dc23a body 6: 30 + 23 rounds; elk_arena: many 1-9-round blocks of G0. Code: brain.cpp ~8032-8046 `case ST_RESPAWN: … if
(g.ready_round - round > 0) wait_group(g); else farm_group(g);` — at timer 0 the body goes onto the group's free tiles; world.cpp ~655-660
`ready_round = round + timer`, and the timer stays 0 while a tile is occupied; `legit_wait` (~l. 1989-1993) is then always true. The same
deadlock as the TOL bug fixed today under `g23_tol` only (off live). Fix to test: never stand on `g.mask` while the group is respawning;
"timer 0 for 2+ turns with our body on g.mask" = blocked by us → step off.

**Checked, not causes:** recall deaths (5 ours vs 46 theirs, real held recalls only; the `g17_bait` recall is not one); bags lost
(corridors 119 vs 89 a game: both teams; on gemfight a consequence of S2). One example worth a look: a Heart of Ruin made no basic attack
beside an awake wolf for 50 rounds (e28a17f2 r654-707; see `hor_camp_dash`, brain.cpp:8550).

## 3. Scripts (`map_fail/`)

| script | what it does |
|---|---|
| `download_decode.sh` | downloads and decodes the replays in `to_download.txt` |
| `groups.mjs`, `mapgroups.py` | full camp groups (half-map groups mirrored the engine's way), validated against the bot's runtime dumps on 6 maps and the replay group counts on all 8 |
| `analyze.py` | per game: timeline, deaths, time use and episodes → `out/games.jsonl`, `out/deaths.jsonl` |
| `summary.py` | per-map summary → `out/summary.txt` |
| `cycles.py` | big-group contest cycles → `out/cycles.txt` |
| `respawn_react.py` | what bodies do in the 12 rounds after a big group respawns |
| `passive.py` | passive camp damage runs → `out/passive.txt` |
| `stall.py` | stalls by the bot's own watchdog definition; `stall.py all` covers all 160 games |
| `gtrace.py <mid> <gid> [r0 r1]` | one group's timeline |
| `tables.py` | the markdown tables above |
