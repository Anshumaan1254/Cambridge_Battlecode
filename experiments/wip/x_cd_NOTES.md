# x_cd: camp deaths at low health (agent `cd`, session 14, Oct 20)

Baseline: GOD v5 = `bots/_g5br` (sources untouched). Working copy `bots/_x_cd` = `_g5br` + `experiments/wip/x_cd.patch`
(rebuild: `SRC=bots/_g5br tools/variant.sh _x_cd && (cd bots/_x_cd && patch -p1 --no-backup-if-mismatch < ../../experiments/wip/x_cd.patch)`;
variants: `SRC=bots/_x_cd tools/variant.sh NAME switch=value ...`). Every switch 0 = GOD v5's games (control `_cd0`: 42/42 games identical
to `_g5br` vs `_g4`).

## 1. The problem (25 ladder games of GOD v3 vs five top teams, `experiments/losses_oct20/`)

93 of our 455 body deaths were by camps (theirs 42 of 222): 73 trigger deaths + 20 Cassi/Issac partners that died through the pair link
(the partner's death row shows the killing camp 13-34 tiles away). By killer: elk 62, monolith 5, wolf 6. 41 of the 73 were hit at
least once from distance >= 4 (outside the pre-patch camp range 3), 30 took the killing blow from distance >= 4. 31 had an enemy champion
within 6 in their last 6 rounds, 42 did not. 23 happened before r200.

Tools (scratchpad copies are in this note's appendix; they read the decoded `an/dmg/*.json`):
- `trace.py DMG_DIR [--game G] --print`: the last 15 rounds of every camp death: health, position, distance to home, which camp hit for how
  much from which distance, champion damage, nearest enemy / ally, every action (moves, attacks with the target camp, casts, recalls).
- `cats.py DMG_DIR [--side-from-name] [--list]`: the categories below for every trigger death (first match wins).
- `campdeaths.py BOT OPP OUT`: plays BOT vs OPP on the 21-map pool (both sides, one game at a time), decodes every replay, so `cats.py` and
  `econ.py` / `econ2.py` (deaths, captures, camp damage, recalls per team and per champion) can count local camp deaths.
- `CD_TRACE` (a define in `_x_cd`, inert otherwise): per turn, when hit or inside an awake camp's range, the camps around the body as the
  world model holds them (distance / range / health / state / visible / seen / awake), and `CDS` lines with safety()'s line, camp damage,
  escape steps and the latch.

## 2. Traces (ladder, GOD v3 is side A = team 0 in every game)

Distances are Chebyshev from the camp; elk range is 4, monolith 5, wolf 3 (patch 3.0). "d3/d4" = distance 3 / 4.

| # | Game (map) | Body, round | What the trace shows | What it should have done |
|---|---|---|---|---|
| 1 | 38998622_02 (nx60x60) | Ren r42 | r22 stopped at (18,18) in the hole maze, d4 from elk32 (15,22); r28 elk32 woke (someone else hit its group) and hit Ren 60 a round for 14 rounds, 900 -> 0; no action at all (waiting at the tile) | step one tile N/E (d5) at the first hit: safety() never saw the elk (its camp scan stops at distance 3) |
| 2 | 38998622_02 (nx60x60) | Issac r733 | hit elk46 at d1 553 -> 402, walked out d1 -> d4 (r722-725), then stood at (41,33) d4 for 7 rounds, 37 a round, 289 -> 0 | keep walking to d5 (one more step), then recall |
| 3 | 38998622_02 (nx60x60) | Stellar r384 | cast + attack elk50 from d3 with elk52 at d4: both hit (120 a round), 750 -> 270 in 4 rounds, then walked d3 -> d4 -> d4 and died | count both elks (the second one at d4): leave at ~480, two steps out |
| 4 | b6bdb9e4_03 (ambush_v3) | Stellar r446 | attacked elk24 (30,44) from the bush door (27,44) d3, elk22 d4: 750 -> 150, then (27,44) <-> (26,43): d3/d4 of elk24, hit every round | leave the room past d4 (25,43), recall |
| 5 | c47c8c26_04 (ambush_v3) | Varg r458 | hit elk22 at d1 880 -> 410, walked out d1 -> d4 to the same door, then 6 rounds (26,43) <-> (27,44) at 170 HP, dead | same: the d4 tile counts as out, the home path leads back through the elk room |
| 6 | b6bdb9e4_04 (elkring_v3) | Stellar r108 | attacked elk2 (9,2) from (12,0) d3, 503 -> 263, then 8 rounds (12,0) d3 <-> (13,1) d4, 263 -> 0 (the elk stands between Stellar and home) | at d4 keep fleeing to d5, then recall (out of range the recall is safe) |
| 7 | b6bdb9e4_02 (corners_v3) | Cassi r597 | melee on elk32 at d1 600 -> 240, left at 180 and died at the edge d4 (3 hits on the way out: 180) | leave one round earlier: from d1 an elk needs 4 steps, the line of 4 rounds x 60 = 240 is exactly the escape cost (hp 240 stayed, 240 < 240 is false) |
| 8 | c47c8c26_02 (nx51x40) | Stellar r125 | walked down the corridor to (20,16); the two elks (21,19)/(21,20) behind the bush row y=17 woke and hit 120 a round; Stellar recalled at r122, r123, r124, each cancelled by the next hit | the elks were invisible (bush row), so the world model kept them asleep: no camp danger, safe_to_recall() true. An unexplained hit next to a camp we cannot see must count as that camp awake: step out, no recall |
| 9 | e6475502_01 (nx61x71) | Cassi r245 | stood at (35,7) and recalled 13 times (r232-244) while wolf6 at (35,10), behind the wall row y=8, hit 20 a round: 300 -> 0 | same as 8 (wall, not bush) |
| 10 | e6475502_02 (lanes_v3) | Cassi r217 (+ Issac) | at 340/600 walked toward Issac (43,25) through elk20 + wolf22 reach (d2-d4), 340 -> 0; Issac died through the link | stay out of reach; the pair walk ignores camp reach |
| 11 | e6475502_04 (eight_v3) | Stellar r139 | at 261/750 attacked elk2 (13,4) from d3 (a double elk group); dead 2 rounds later | do not start a camp group whose reach kills us in its first rounds |
| 12 | e6475502_03 (corners_v3) | Cassi r505 | banked at an altar inside two wolves' reach (d1) at 213 HP (2 tribute turns, 40 a round), then walked out 3 rounds and died at d3 | bank elsewhere or leave first |
| 13 | 38998622_01 (nx61x61) | Issac r123 | farmed the centre group's gold / gem tiles; the group's elk (30,30) and a wolf hit it at d2 (80 a round), 460 -> 60 while it walked on inside the group's reach toward the next tile; Cassi died with it | leave at the 4-round line (320) by the shortest way out (the centre box has wall exits: the Chebyshev escape is shorter than the real one) |
| 14 | e6475502_04 (eight_v3) | Ryth r128 | 15 rounds (16,3) <-> (17,4) at 469/1200 at d4 of the elks; when they woke it kept stepping between the two tiles inside the reach | the same blind spot: d4 never counted |
| 15 | e6475502_05 (nx100x100) | Ryth r776 | hit monolith57 at d1 2422 -> 1540, walked out into the reach of the second monolith56 (126 each, 252 a round), then (46,51) <-> (46,52) at d3/d4 of 57 and d5 of 56: 1540 -> 0 in 6 rounds | monolith range 5: d4 and d5 count, the escape is 5 steps |

Pattern behind 1-7, 13-15: `Brain::safety()` (brain.cpp) scanned only camps within distance 3 (`if (g.hp[i] <= 0 || d > 3) continue;`)
and counted the escape as `4 - d` steps: the pre-patch range. GOD v2 moved the danger map, the ring and the kite plan to the engine ranges
(`CampRef::range`) but not this scan. So at distance 4 of an elk (4-5 of a monolith, 4 of a golem) the body saw no camp damage: no camp
line (threshold = retreat_hp only), and the flee step (`in_awake_camp_range() && camp_in > 0`) never ran. The flee step itself aims out of
the real range (`~camp_danger`), so its first step lands on a d4 tile; there safety() saw nothing, so the farm walk (above retreat_hp) or
the home walk (below it: `go_home()` cannot recall inside `camp_danger` and walks the home field, which often runs back past the camp)
took the body back to d3, where the flee started again: the d3 <-> d4 oscillation, hit every round. Monoliths do the same at d4/d5.
Pattern 8-9: camps hidden behind a bush row or a wall keep their last known state in `World::update` (their state reads need vision), so a
camp woken by someone else is "asleep" for us while it hits us; `safe_to_recall()` then allows a recall that the next hit cancels.

## 3. Categories (`cats.py`, first match wins; trigger deaths only, the 20 / 28 pair partners counted with their trigger)

| Category | Rule | Ladder (73) | Local `_g5br` vs `_g4`, 42 games (131) |
|---|---|---|---|
| oscillate_edge | last 4 positions alternate between 2 tiles, >= 3 moves, hit (d3 <-> d4 of an elk, d4 <-> d5 of a monolith) | 22 (Stellar 7, Varg 5; ambush 6, nx100x100 4, elkring 3) | 30 |
| champ_fight | champion damage >= 25% of max health in the last 12 rounds | 15 | 21 |
| escape_too_late | walked away over the last 4 rounds, distance to the killer rising, died at the edge | 10 (Issac 4) | 31 |
| walk_through_reach | walked inside the reach without leaving it (to a target, home, the partner) | 10 | 21 |
| mixed | none of the above; mostly the ambush bush door [3,3,4,3] | 8 (Stellar 5) | 9 |
| recall_in_reach | a recall in the last 6 rounds while hit (hidden camp behind a wall / bush row) | 3 | 8 |
| idle_in_reach | no move and no attack in the last 4 rounds while hit | 2 (nx60x60) | 5 |
| tribute_in_reach | banked in the last 8 rounds inside a camp's reach | 2 | 1 |
| stayed_attacking | attacked in >= 2 of the last 4 rounds without moving | 1 | 5 |

Common to all: hit from distance >= 4 at least once 41 / 73 (local 80 / 131), killing blow from >= 4: 30 / 73 (local 59 / 131); attacked a camp
below 50% health in the window 36 / 73; an enemy within 6 in the last 6 rounds 31 / 73 (local 63 / 131). The local games reproduce the
ladder pattern (local camp deaths: ours 159 of 697, `_g4`'s 156 of 754: GOD v2 has the same scan), so the A/B below measures the problem.

## 4. Code paths that keep a low-health body in a camp's reach (`bots/_g5br/src`)

1. **`Brain::safety()` scans camps within 3 only** (`if (g.hp[i] <= 0 || d > 3) continue;`, escape `4 - d`): the pre-patch range. Elk / golem
   at 4 and monolith at 4-5 are invisible to the retreat line (`threshold = max(retreat_hp x max, 4 x camp_in)`) and to the flee step
   (`if (in_awake_camp_range() && camp_in > 0) step(~camp_danger)`), while `camp_danger` / `Group::near` use the real range. Hence the
   d3 <-> d4 oscillation (flee to the first tile outside 3, which is still inside 4; there safety sees nothing and either the farm walk
   goes back in, or `go_home()` finds the recall unsafe (inside `camp_danger`) and walks the home field, which on elkring / ambush / eight
   runs back past the same camp), the standing at d4 (Ren, Issac on nx60x60: no line at all until 25%), and the late escapes: from d1 an elk
   now takes 4 steps (3 hits after the turn), and 4 rounds of strength is exactly that cost (Cassi 240 / 600 next to an elk stayed one
   round too long and died at the edge).
2. **Hidden camps** (`World::update`): a camp's state is read only when its tile is in vision; a camp behind a bush row or a wall keeps the
   last known state. One woken by someone else hits us while `g.awake` is false: no `camp_danger`, so `safe_to_recall()` allows the recall
   and the next hit cancels it (13 recalls in a row on nx61x71, 3 on nx51x40). The trace build counted 10 such hit turns in one local game.
3. `finish_camp` and `capture_before_retreat` (safety exceptions) use the same scan: with an elk at d4 not counted, "no camp in reach"
   lets a body stay on a reward next to an awake elk, and the finish estimate is optimistic.
4. Smaller: the home field and the flee search are Chebyshev / plain BFS (the escape from the nx61x61 centre box is ~6 steps through walls,
   the line assumes 3); Cassi walking to Issac through a pack's reach (lanes_v3); a tribute inside two wolves' reach (corners_v3);
   starting a double elk at 35% health (eight_v3). Not changed here.

## 5. The switches (`params.h`, all 0 = GOD v5)

- `cd_range` (bits):
  - 1: `safety()` counts every awake camp within its **engine** range (`CampRef::range`: elk / golem 4, monolith 5), the escape is
    `range + 1 - d` steps, and the camp line is `max(4, steps + 1)` rounds of camp strength (one round of margin beyond the walk out).
  - 2: **retreat latch**: a body that retreats with camp damage on it remembers the line it fell below and keeps going home (recall as soon
    as it is out of reach) until it is above that line again (spawn heals), the bag would win the game, or `cd_latch_max` (40) rounds pass.
    Without it the line drops to `retreat_hp` once out of reach, and the farm walk or the home walk led back in.
  - 4: a camp beyond distance 3 counts only when no visible ally stands strictly nearer to it (the camp hits its nearest champion: behind a
    melee ally the far elk of a pack does not reach the ranged body).
  - 8: margin `max(4, steps)` rounds instead of `steps + 1`, and the line holds at equality (Cassi at exactly 240 = 4 x 60 next to an elk).
  - 16: the steps out by the real shortest path (walls, holes, camps, the map edge) when longer than Chebyshev: a box-limited distance field
    from the tiles outside `camp_danger` to us (elkring_v3: at the east edge 4 steps south at distance 3; fuel: rollovers on nx100x100 6 vs 4
    for `_g5br`, within game-to-game noise).
- `cd_enemy_d` (0 = off): `cd_range` applies only while no enemy was seen within this distance; with an enemy near, the old line keeps the
  fight (see section 6: fragment_v3 vs `_pw`).
- `cd_hidden` (rounds, 0 = off): health lost since our last turn with no visible enemy within 6 marks every live camp we cannot see whose
  range covers our tile as awake for this many rounds (danger map, `safety()`, no recall into its hits). The mark is ours: when it lapses
  and the group is still unseen, its awake flag goes back to false (a first version left it set for as long as the group stayed unseen).
