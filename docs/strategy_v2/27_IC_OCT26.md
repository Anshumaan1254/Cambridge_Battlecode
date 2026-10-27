# Intercontinental Fish vs GOD v18 (Oct 26): the user's 15 match groups

The user ran unranked match groups of GOD v18 against Intercontinental Fish (IC) on the whole sprint-3 pool (14 distinct groups; two
groups were the same five maps and played identical games: the engine and both bots are deterministic) and lost 58 of 65 maps. The live
bot was the **interim v18** (`_v18a`, `submissions/history/god_v18_interim_v18a_20261026.zip`: no pick prior anywhere), not the shipped
v18 (`_v18g`, prior on the 40 known maps). Data: `experiments/ic_oct26_v18/` (replays by map, group data, `gap_tables.txt`, `report.txt`,
produced with the scripts in `experiments/ladder_oct26_v17/analysis/`).

## 1. What IC does

| | GOD v18 interim | IC |
|---|---|---|
| captured gems by r150 (mean of 65 maps) | 52 | 109 |
| first middle capture (median round) | 216 | 98 |
| middle captures / gems a game (band where the two spawns are within 4 tiles of equal distance) | 5.8 / 158 | **15.2 / 525** |
| own-half captures / gems | 15.2 / 268 | 22.3 / 430 |
| camp hits a game / damage | 593 / 55k | 1,156 / 105k (damage per hit 93 vs 91) |
| contact while farming: keep farming / fight / walk off | 34% / 37% / 17% | 44% / 30% / 10% |
| near-enemy steps toward the enemy when ahead | 37-41% | 22-25% |
| deaths a game (Vendetta) | 11.5 (3.5) | 9.2 (C&I 2.4 pairs) |
| shards at r800 (Bruiser) | 78 (26) | 160 (89) |

- **The middle, with the whole team, from the opening.** On every map IC's five or six bodies go to the richest group near the middle and
  take it, then retake it on every respawn: vault's 49-cluster centre (343 gems) at r78, the-line's 23-cluster line (161) at r48 and r144,
  gem-fields' 71-gem group at r29 and r123, quarry's 46-gem group at r47, stalactites' 84-gem groups at r43. The early capture gap is
  largest exactly on those maps (vault 4 vs 347 by r150, the-line 12 vs 334, stalactites 12 vs 265, gem-fields 14 vs 220).
- **Six bodies.** On 5-champion maps IC's Cassi & Issac are two bodies (329 of its 1,156 camp hits); since the patch Cassi has 100 focus
  and Issac 45 strength.
- **Builds.** Treasure first (11 shards by r200; ours 3.5), then Jungle and Bruiser stacks.
- **Its weak spot.** Cassi & Issac die together (2.4 pair deaths a game); our first kill was Cassi in 13 games.

## 2. Why we lose

- We give up the middle: our bodies spread one per group on our half, and a harmless gem field is a one-body target in our join rule
  (harmless groups are never "heavy"), so no second body joins it.
- Our Vendetta dashes into fights at mid and dies (77 deaths before r400 in 65 games, 87% within 8 rounds of a cast, 37 in the middle).
- We still chase when ahead and leave camps on contact (the interim build already had contact discipline).

## 3. What was tried (local, none reproduces IC)

- IC proxy: IC's exact rosters from these groups forced on our brain (`_icp0`), plus value and middle rushing (`_icp1`: `heavy_value` 2,
  `big_reward` 60, `big_reward_dive` 60, `enemy_half_penalty` 3, Treasure-first builds). v18 beats `_icp1` 65/108, +152, deaths 10.2-17.3:
  our brain on IC's draft does not play like IC, so it cannot stand in for IC.
- `g18_rich` (the team may join a harmless group worth 80+ gems): on the four maps with such groups (vault, the-line, stalactites,
  gemcombat5, both sides) 3/8 vs v17 where v18 went 7/8; off.
- `_ax1` (`heavy_value` 1.6, `big_reward` 60, `big_reward_dive` 60: value big groups, fight for them with the team near, contest an enemy
  capture of one): vs `_icp1` 85/140, +138 (v18 the same); vs v17 81/140, +59 [-42, +155] (old maps +143, new -53).
- `_fd` (fight discipline against the Vendetta dives: `fight_margin` 1.6, `isolated_fight_adv` 1.6, `outmatch_flee_adv` 1.0): vs v17 79/140,
  +96 [+4, +188], deaths 10.8-12.1 (old maps +106, new +83).
- Shipped v18 (`_v18g`) on the same pool: 85/140, +154 [+59, +250]. Neither candidate beats it locally; both are zips in
  `submissions/candidates/` (`god18_fd.zip`, `god18_ax1.zip`) for a real test against IC.
- Varg in every slot and Tavi for Ryth: all below v17 (doc 25).

## 4. How to test against the real IC

Match groups are deterministic: one game per map is the full answer for that version pair. A candidate is tested by submitting it, making
it the active version (the user's decision), and queueing groups against IC (`cambc match-groups create 1890540d-1ffc-4847-adbf-d0d08772f268`,
optionally `--source-group <a group id above>` to keep the same IC version and `--maps` for five chosen maps). The 14 group ids of this run
are in `experiments/ic_oct26_v18/groups/`.
