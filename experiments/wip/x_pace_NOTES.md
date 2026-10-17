# x_pace: unopposed pace (agent `pace`, session 4)

Baseline `bots/_ST`. Bot copy `bots/_x_pace` (frozen as `_x_paceH` for the panels). Patch: `experiments/wip/x_pace.patch`
(`cd bots && diff -ruN _ST/src _x_pace/src`). Pace = round at which the first team banks 1000 gems vs `idle`
(mean of both sides; a failed game counts 2000).

## Result (final candidate = `_x_pace`)
- Pace vs `idle`, 56 maps: 479.2 -> 473.3. 17 official maps: **585.0 -> 568.0** (-17).
- Official maps, rounds to 1000 gems (before -> after): ambush 820 -> 642, pilgrimage 900 -> 777, rushbait-v2 716 -> 668,
  interlock 572 -> 553, eight 427 -> 423; unchanged: contest 1087 (see "off by default"), stampede 705, expanse 638, fragment 559, lanes 498,
  rows 436, packs 373; noise-level worse: collision 554 -> 573, monolith 416 -> 440, elkring 486 -> 500, corners 411 -> 418, swirl 342 -> 360.
- Switches in `params.h` (all values were changed; comments carry the evidence):
  - `bank_first` 1 -> 0 (the capture-recall + spawn bank is used everywhere).
  - `obj_min_hp` 6000 -> 4500, `obj_share` 0.6 -> 0.7, new `obj_max_groups` 8: the objective-map plan (team gathers, whole team clears a heavy gem group)
    now also fires on ambush (gem groups of 4,750-5,800 HP, 6 heavy groups): ambush pace 840 -> 642.
    `obj_max_groups` keeps it off on swirl and the ladder 45x30 map (14 heavy groups each: every group is heavy there, +15 rounds with the mode on).
  - `obj_min_attackers` stays 2 (= `_ST`). Setting it to 1 turns the plan on for a lone monolith: contest 1087 -> 905 and nothing else on the 56 maps,
    but see below.
- Head-to-head (56 maps, both sides, 112 games per cell, win %; `_x_paceH` vs): see the table at the end.
- Fuel: lost turns on `maps/gen16_98x99_V_c5.map26a` 18 for us (same as `_ST`), 0 faults in every run.

## Where the body-rounds go (route_stats on LEGEND_TRACE builds, 16 official maps, vs idle, `_ST`)
- Alive body-rounds: walk 47.6%, hit 21.2%, bank 9.0%, "noturn" 7.9% (these are the 5 channel rounds of every recall: the body takes no turn),
  wait 4.1%, hit-idle 4.0%, capture 3.3%, home-rest 1.3%, flee 1.1%. Unopposed 1.76 walking steps per collected gem (1.42 camp walking).
- 45.7% of camp walking is in segments abandoned before arrival (22,152 of 48,498 steps): "ally-took" 1,326 switches (10,996 steps, 5,591 of them
  still progressed toward the next target) and "rescore" 1,860 (10,562 steps, 5,141). Net waste about 11k steps = 11% of body-rounds. Duplicate walks
  (two bodies walking to one group) are 39% of walking body-rounds (by design for heavy groups: the join rule).
- Slow maps are walking maps: pilgrimage 58-65% walk, 3.0-4.0 steps/gem; ambush 64-70% walk, 3.6-4.3 steps/gem (expanse 1.4-1.6).
- Switch causes on ambush/rushbait-v2/stampede/expanse (`tools/pace/switch_stats.mjs`, 1,100 switches): old target invalid because respawning (an ally cleared
  it) 276 switches / 7,261 walked rounds; invalid while alive (claimed by an ally) 121 / 2,602; reward taken 56 / 2,732; still valid but a better one found
  478 / 9,997 (half to a nearer group, half to a farther one).

## Why bank_first helps on some maps and hurts on others
- `bank_first` banks at the altar next to the capture when `altar_walk + 5 + 2 <= spawn_altar_walk`, else recalls and banks from spawn.
- Pilgrimage is the clear case: holes walls cut the map into lanes; the spawn is in the left lane, the spawn altar (bottom, (5,58)) is 54 steps away and
  the gem groups g15/g16 are 150 steps from spawn (reachable only via the bottom corridor, the centre lane and the top). With bank_first the body banks
  at the bottom altar 14 steps from g10, but then `home_trip` ("just banked far from home", 3+ affordable shards) recalls it to spawn, from where the
  next camp is 40-55 steps away. Without bank_first it recalls on the capture and walks 54 steps to the same altar.
- Neither rule is robust: the pace of single maps moves +-30 rounds when a rule fires differently (chaos; unchanged-behaviour variants reproduce to 0.5
  round on the pool mean, but any behaviour change reshuffles which body meets which camp). Tried and rejected (all on the 56 maps, ALL/official):
  - `bank_first` 1 (baseline): 472.7 / 574.3; **0: 469.7 / 567.6**.
  - rule that compares the walk from each altar to the nearest candidate camp (new `bank_here_dest`, margins 2 and 6): 472.3 / 577.4 (margin 6), pilgrimage 800
    but ambush +50..+110, interlock +40: no better than plain off. Code removed.
  - `bank_first=1` and no shopping recall after a far bank (3+ shards no longer sends the body home): 466.2 / 554.7; `bank_first=0` + `shop_shards=6`:
    465.2 / 552.7. Both are inside the noise (+-4 on ALL, +-8 on official) of `bank_first=0` (obj plan on): not adopted.
  - `tribute_min=48 early_tribute_min=34`: 469.9 / 568.9; `cap_recall_gold=150`: 470.2 / 567.5; both: 470.2 / 570.6. Banking thresholds are not a pace lever.

## Other tries (pace on 56 maps, ALL / official)
| Try | Result | Verdict |
|---|---|---|
| `join_reach` (a joiner skips a claimed group farther than k x the claimers' clear time) k = 0.25 / 0.4 / 0.6 / 0.8 / off | 474.2 / 580.6, 463.7 / 563.0, 468.6 / 566.9, 471.8 / 569.6, 469.7 / 567.6 | no trend, mean of the four = off. Removed |
| `hysteresis` 1.35 / 1.6 (stickier targets) | 467.1 / 568.0, 481.1 / 591.2 | noise / worse |
| `max_wait` 30 | 478.5 / 571.9 | worse |
| `obj_min_hp` 4500 `obj_share` 0.4 | 470.5 / 563.2 | ambush -194 but eight +29, expanse +26, interlock +49 (they enter the mode at share 0.59-0.67) |
| `obj_min_hp` 2500 `obj_share` 0.5 | 477.1 / 565.9 | worse |
| `obj_min_hp` 4500 `obj_share` 0.7 (adopted, plus `obj_max_groups` 8) | 466.8 / 557.1 (with `obj_min_attackers` 1) | only ambush changes (-178) |
| contest: `obj_clear_max` 80 / 150 / 300, `obj_absorb` 0.8-100, `obj_gather` 2, `obj_min_bodies` 2 (with `obj_min_attackers` 1) | 905 / 858-923 / 1153-1246 | attacking the monolith early (weak items) is much slower; the 905 default is within noise of the best |

## Contest (monolith map)
- The only gem source is the 20,000 HP / 200 dps monolith (200 gems, 300 gold, respawn 150), inside a walled room, one per side. `_ST`: 5 captures at
  r615, 801, 904, 996, 1097; the team farms the gold clusters first (items) because the plan was off for a lone monolith (`obj_min_attackers` 2).
- `obj_min_attackers=1` turns the team plan on for it (gather, clear with the whole team): captures from r518 (518, 634, 700, 808, 877), pace 905.
  Early attack with weak items is slower (1153-1246).
- Held-out `maps/gold,gold2,obj` (100 games, mostly lone-monolith maps) head-to-head vs `_ST`: **46.0 with `obj_min_attackers=1`, 49.0 with 2**
  (both vs `_r2` 89 = `_ST` 89). The 56-map and official head-to-heads do not see a difference either. Kept at 2 (the user: do not rely on the monolith);
  switch it on only if contest's idle pace matters more than ~3 points on the monolith pool (noise level).

## Not done / ideas that look real
- ~11% of body-rounds are walks abandoned before arrival. Tried to cut them with the join rule and hysteresis (above); neither moved the pool. A shared
  assignment is the real fix, but bodies cannot see each other beyond vision and the 8 shared bytes are full (claims only).
- Pilgrimage-like maps (holes walls, spawn altar 50+ steps from the camps): the spawn is a bad place to bank and shop; a "forward base" rule (bank at
  the nearest altar and skip the post-bank recall unless hurt) is what `bank_first=1` + no shop recall approximates (sA above); results were noise.
- Expanse (22-gem groups, bag banked after every capture, 640 rounds): no param moved it robustly.

## Tools added (all new files)
- `tools/analysis/route_stats_p.mjs`: `route_stats.mjs` with two parse fixes for the current trace (NUL bytes in the replay stdout; the `G` line now has `dps=`).
  It fails on `corners` (group table without tiles).
- `tools/pace/pace_pool.sh BOT...` (pace vs idle on the 56 maps -> `/tmp/pace/res/BOT.txt`, summary in `/tmp/pace/full.log`), `pace_sum.py` (per map, ALL and official
  means), `pace_cmp.py A B` (per-map differences >= 15 rounds), `body_timeline.mjs FILE TYPE [from] [to]` (compressed task timeline of one body from a trace build),
  `switch_stats.mjs FILE...` (target switches by cause; needs the `SW` trace line below), `captures.mjs FILE` (capture and bank rounds).
- `LEGEND_TRACE` builds now print `SW r= type old= new= sold= snew= stold= dold= dnew= since=` at every target switch (in `farm()`; compiled out otherwise).
  The trace build's `std::map` costs fuel, so a trace build is not behaviour-identical (pilgrimage 900 vs 823): compare traces only with each other.

## Reproduce
```
SRC=bots/_ST tools/variant.sh _x_pace            # then apply the patch: cd bots/_x_pace && patch -p1 < ../../experiments/wip/x_pace.patch
python3 tools/bench.py _x_pace idle --maps 'maps/comp/*.map26a' --jobs 2 --out /tmp/pace/o --quiet     # ~25 s
tools/pace/pace_pool.sh _ST _x_pace ; python3 tools/pace/pace_cmp.py _ST _x_pace                         # 56 maps, ~90 s per bot
python3 tools/bench.py _x_pace _ST --maps 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' --jobs 2 --out /tmp/pace/h2h --quiet
```

## Head-to-head (final candidate `_x_paceH`, 56 maps, 112 games per cell)
(table below is filled in when the panel finished)
