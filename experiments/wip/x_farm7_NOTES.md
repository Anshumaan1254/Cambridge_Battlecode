# Agent farm7 (session 7): farm faster (unopposed pace)

Baseline `bots/_b7` (pace 565.2 on the 17 official maps vs `idle`, both sides). Copy `bots/_x_farm7`.
Measure: `tools/pace17.sh BOT 2` (per map in `/tmp/ev/p_BOT.txt`). Trace builds: `/tmp/farm7/tr.sh SRC NAME [k=v..]`
(LEGEND_TRACE variant + pace bench in `/tmp/farm7/trace_NAME`), then `tools/analysis/time_use.mjs`, `econ_open.mjs`,
`tools/pace/body_timeline.mjs REPLAY TYPEIDX FROM TO` (type index: Ryth 0, Cassi 3, Issac 4, Stellar 5, Ren 9, Varg 10).

## Findings (in order)

1. **Give-up clock bug** (`giveup_progress`). `farm()` blacklists the current target for 40 rounds when
   `round - task_since > 2 x eta + 60`. `task_since` is the round the target was chosen and `eta` is the *current* eta
   (0 once we stand at the group), so any clear that took more than 60 rounds from the choice (walk + kill + heal trips)
   was abandoned, often the round the pack died. rows: Varg walked 38 rounds to the far pack, hit it 22 rounds, was
   blacklisted from its own reward at r63 and walked to another pack; Cassi took the reward at r81.
   Fix: the clock restarts at every hit on the group and every capture turn.
   **Pace 565.2 -> 551.4** (pilgrimage 778 -> 662, stampede 711 -> 673, swirl 320 -> 281, rows 441 -> 416). ON.

## Per-map pace (17 official maps, vs idle, mean of both sides)

| map | `_b7` | +giveup |
|---|---|---|
(table filled at the end; raw per-map files `/tmp/farm7/p_NAME.txt`)

## Param sweep on top of giveup (17 maps, pace; giveup alone = 551.4)

| variant | pace | note |
|---|---|---|
| `ci_health_first=0` (C&I damage first) | **537.9** | monolith 523->451, collision 572->522, interlock 540->498, lanes 520->485, expanse 609->577; stampede 673->739 |
| `build_style=1` | 547.3 | |
| `build_style=0` | 557.9 | |
| `rich_treasure_first=1` | 559.1 | |
| `max_wait=30` / `10` | 552.9 / 557.4 | 18 is right |
| `max_join=2` | 545.4 | a third body helps on supply-limited maps |
| `join_min_rounds=8` | 547.2 | |
| `shop_shards=2` | 560.0 | gold is already spent fast: mean gold held 10-26 per body, >=150 only 0.1-3.7% of alive rounds |
| `obj_team_best=1` (new switch) | **543.4** | ambush 716 -> 585 (enemy contested 561), contest 920 -> 915, no other map moves. ON |
| `farm_prio=1` (new switch, without otb) | 541.0 (vs 551.4) | ambush 621, lanes 477, pilgrimage 613, contest 871; rushbait 707 (+83) |
| `incumbent=1` (new switch, with otb) | 542.7 (vs 543.4) | monolith 453 (-70), lanes -28, elkring -23; swirl +58, rushbait +53, pilgrimage +45: neutral on 17 |
| `build_style=4` (Monster + Power in the damage stat, new) | 613.5 | contest 1731, stampede 1083 (objective team plan needs health); without those two 507.7 vs 510.0 |
| `build_style=4 farm_ren_str=1` | 607.0 | without contest/stampede 503.8 |
| `tribute_min=50` | 545.7 | |
| `hysteresis=1.3` | 544.3 | |
| `join_share=0.8` | 561.6 | |

## Stacks (giveup + obj_team_best on; 17 maps)

| stack | pace |
|---|---|
| s1 = + `ci_health_first=0` | 529.8 |
| s2 = s1 + `farm_prio=1` | 528.6 |
| s3 = s1 + `max_join=2` | 526.3 |
| s4 = s1 + `farm_prio=1 max_join=2 incumbent=1` | 525.0 |
| s5 = s1 + `ren_dmg_first=1` (new: Ren/Ryth Monster before Jungle health) | 537.5 (worse) |
| s6 = s1 + `ci_health_obj=1` (new: health-first C&I on objective maps only) | 530.9 (neutral: stampede 739 -> 735) |
| s8 = s1 + `no_split=1` (new: leave a reward an ally stands on; 40 split pairs in 854 rewards) | 536.9 (worse) |
| s9 = s4 + `bank_trip_cap=4` | 528.5 (worse) |
| s10 = s4 + `bank_trip_cap=4 bank_trip_w=2` | 539.0 (worse) |

56-map pool (pace vs idle, 112 games): `_b7` 469.1, s1 448.0, s2 445.9, s3 449.8, **s4 443.7**.

**Regression guard s4 vs `_b7`: 64.3% (72/112), official 58.8% (20/34), deaths 961-1276, 0 faults.**

Trace of s4 (17 maps): walk 32.4%, hit 28.7%, wait 16.6%, bank 13.3%, capture 5.7%; abandoned episodes 13.1% -> 10.1%.
rows (s4): the far pack (x=42, 38 steps) was captured at r100 and next at r351: Stellar, Cassi and Issac kept joining the
two near packs as helpers (Issac 0 captures in 447 rounds). Joiner credit = 0.6 of the reward overstates a helper's
value (the claimer clears the pack anyway): test `join_share` 0.3-0.4 and `join_dps_share` (share = my dps / all dps).

## Diagnostics so far
- Time use unopposed (giveup build, 34 games): walk 32%, hit 29%, wait 16% (2/3 of it walking to a respawning group or an
  objective gather point, standing only 2.6%), bank 12.6% (Varg 27%), capture 6.4%, home 1.9%, flee 0.8%.
- Bank walks (`bank_audit.mjs`): 11.2% of alive body-rounds, 349 submits, 51 gems per submit, walk median 14 steps.
- Abandoned target episodes (`/tmp/farm7/aband.mjs`: farm/wait/capture runs on one group with no hit and no capture, ended by
  a switch to another group): 13.1% of farm/wait/capture turns (ambush 29%, lanes 17%, contest 16%).
- ambush: Stellar, Cassi and Ryth captured nothing in 827 rounds. Score debug (`_x_dbg`, SCD lines): Varg and Stellar took
  turns on elk group 6, each leaving when the other joined. Cause: a helper's claim makes the solo plan feasible with 5 heal
  trips (217-302 rounds), which replaced the 43-round objective team plan (the team plan ran only when the solo plan failed).
  Fix `obj_team_best` (team plan when it scores better).
- lanes: Issac walked 38 rounds to a single wolf, hit it from distance 1; Cassi (lower index, same rank) joined and Issac's
  view turned it into "not heavy, already claimed" (-1): Issac left for a group 13 away. Fix `incumbent` (first claimer keeps
  the group; the claim history is in every body's comms read, one round late at most, so the views agree).
- fragment (30x30): supply-limited (3 wolves + 1 elk per side); Issac waits 43% of its time and captures 0-33 gems.
