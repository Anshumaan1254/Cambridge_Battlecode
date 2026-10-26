# 28: Why the live bot (v74 = GOD v18) loses to the top teams (Oct 26 evening, patch 2.0.0)

Data (read-only, the user's CLI login on their Windows PC): 200 games of v74 (`experiments/ladder_oct26_v74/`: match list, replays,
decoded `dec/`, scripts), 349 strong-vs-strong games of the top 12 on engine 2.0.0 (`experiments/ladder_oct26_top/`), local runs on the
70-map pool (`experiments/ab/`, `tools/abbench.py`). Patch 2.0.0 numbers checked against the engine: `docs/patch_notes/week4_20261026.txt`.

## 1. The result

v74 vs the top 10: 9 of 95 (IC 8 of 70 distinct map-sides, Mite / Sponge / hello 0-5 each). Ranked vs ranks 40-55: 40%.

## 2. Where the gap is (v74 vs top 10, per game)

| | us | them |
|---|---|---|
| captures (CaptureGems events) / gems captured | 23 / 482 | 45 / 1,038 |
| banked at the end | 419 | 985 |
| camp damage / camp hits | 66k / 655 | 115k / 1,195 |
| deaths (Vendetta) | 11.3 (3.3) | 8.5 (0.7) |
| bodies | 4.5 | 5.2 (Cassi & Issac = 2 bodies, 1 pick) |
| farm episodes per body / gap between episodes | 14.2 / 56 rounds | 21.5 / 36 |
| near an enemy (8): hit / still / toward / away / side | 22 / 8 / 30 / 28 / 12% | 33 / 15 / 22 / 23 / 7% |
| toward<->away flips, A-B-A steps (share of near-enemy turns) | 11.8%, 7.2% | 6.2%, 2.9% |
| respawn -> first camp hit (median) | 33 rounds | IC 20, others 23-27 |
| shards by r800 (Bruiser) | 82 (31) | 154 (87) |

The gem gap is 2x already at r50 and grows linearly.

## 3. The key finding: it is the contest, not the farming

- **Unopposed, v18 farms as fast as IC does against us.** v18 vs idle (70 maps, side b): captured gems 23 / 53 / 93 / 126 / 216 by
  r50 / 100 / 150 / 200 / 300; IC vs v18: 28 / 68 / 102 / 132 / 204. Per 100 rounds, every window from r0 to r900 is equal.
- **Against IC we get half**: 13 / 30 / 45 / 64 / 115. IC is not slowed by us at all.
- By r150 (equal items, 1.25 vs 1.32 deaths) we already lose 58 of our unopposed 108 gems. Our 150-round body budget: camp hits 177
  unopposed vs 119 contested; the time goes to walking near enemies (13 -> 100 body-rounds), fights (35 -> 56) and death (0 -> 61).
- Rewards stolen from each other: 5-10% either way. Damage on camps never captured: 11% vs 8%. Neither explains it.
- Quiet farming (no enemy within 12): camp-hit share 19.2% us, 18-22% the top six. Contested (enemy within 12): camp hits 8.3% us,
  13-17% them; walking 67% us, 52-59% them.
- Our near-enemy turns (local G17_TRACE join, `experiments/local_oct26/tr_analyze.py`): 35% combat() fight (hit 43%, step toward 41%),
  34% combat() not fighting (step away 60%), 16% farm (camp hit only 14%), 9% alert walks (toward 78%).
- On 27 of 62 maps IC finishes its contested game faster than v18 finishes unopposed (corridors 862 vs 1,231, gem-fields 561 vs 901,
  islands 650 vs 923): IC takes rich groups with the whole team at once (gem-fields' 71-gem elk groups at r29 and r68 vs our r108;
  corridors' 58-gem centre at r36 vs r150); on as many maps v18 alone is faster, so on average the engines farm alike.
- Top-12 drafts on the patch: Marcella 83% of games, Heart of Ruin 83%, Vendetta 79%, Vesper 78%, Ryth 47%; C&I 11% with the best
  win rate (74%). Our drafts are near mirrors: the draft does not explain the gap.
- Not causes: fuel (p99 49k per turn), target choice (a conditional-logit model of the next cluster gives the same weights for us and
  them), dash use, bank sizes, the v17 bait recall (IC hits our champions as often as it hits other top teams').

## 4. What was tried locally (h2h vs v18, 70 maps x 2 sides unless noted; v18 vs v18 = exactly 50%, v18 vs v17 = 85/140 +154 as before)

| variant | what | result |
|---|---|---|
| `g19_build` 1-4 | Treasure first + Bruiser stacks (the top teams' builds) | 37-45%, -9 to -142: off |
| `g19_hold` 1 / 3 | in reach but not fighting, keep hitting the camp in range (and stay on a reward) | 46-49%, -39 to -78, deaths +1: off |
| `g19_team` | team targets on any map (rich group cleared by the whole team) | pace 918-947 (v18 927), h2h 45-49%: off |
| C&I for Marcella (`pd_sub_from 6 pd_sub_to 3`) + pair caution | IC's extra body | 54-57%, +16 to +41 on the pool; held-out gen2 / gold3 / var17 level (-176 on gold3) |
| `deathball_until` 60 / 100 / 150 | follow the lowest-index body in the opening (IC's opening cohesion, crudely) | 32-35%, -141 to -222: off |
| `g19_mid` 1 / 3 / 7 / 15 | middle band worth more / joinable / lower fight and flee bars there before r300 | 44-47%, +11 to -61: off |
| flee bars (`outmatch_flee` 0, `outmatch_flee_adv` 0.6, `isolated_flee_adv` 1.2, `ml2_flee` 0.5, `ml2_leave` 0.3, `flee_dist` 3) | flee less (ladder: farming on contact dies 5%, leaving 5%, fighting 9%; outmatched: fight 44% of contacts, 27% die) | `outmatch_flee` 0: 44%, -135; `outmatch_flee_adv` 0.6 + `ml2_flee` 0.5 (`_fl1`): 53%, +29 |
| `fight_back_margin` 1.0 (`_fb1`) | fight back only at even odds | 53%, +16 |
| `_F1` = `_fl1` + C&I for Marcella (pair space 2, caution 0.3, low hp 0.4) | the two together | **82/140, +72** vs v18; held out level (gen2 +10, gold3 -25, var17 -16); **vs v17 48.6%, -24 (v18: 60.7%, +154)** |
| `_F4` = `_F1` + `fight_back_margin` 1.0 | | 82/140, +81 vs v18; held out gen2 +44, gold3 21/56 -140, var17 +8; vs v17 50%, -14 |

**Non-transitive.** Every variant that beats v18 gives up most of v18's edge over v17 (`_fl1` +22, C&I +27, `_fb1` +66 vs v17; v18 +154).
On the panel {v18, v17} v18 stays the best version: what wins against v18 exploits v18's own habits, not a general weakness.

**The 25-shard "behind" screen** (our candidate capped at 25 shards vs full v18: 7% wins, -594, close to v18 vs IC) moves by at most +46
(C&I + hold); none of the contact or middle switches changes it.

**Ghost opponent** (`tools/ghost/`, test only): a bot that replays IC's recorded actions from the ladder replays on the same map for 400
rounds. Exact replay fails at round 1 (our draft order on the platform depends on draft memory carried between the games of a group);
the robust version (step toward the recorded tile, nearest target of the recorded kind) is open loop and v18 kills it 35-0 on
gem-fields: IC's strength is its reactions, which no script reproduces. Not usable as an evaluator.

## 5. Conclusion and the ladder test

Local play cannot measure what loses to the top teams (the contested middle under IC's / Mite's reactions). The only real test is the
ladder: `tools/paired_groups.py` re-creates v74's 43 distinct unranked groups (215 games, 15 vs IC) against the same opponent versions on
the same maps and sides once a new version is live (deterministic: a map-by-map comparison), and `cambc submissions activate 74` restores
v74 without a new upload.
