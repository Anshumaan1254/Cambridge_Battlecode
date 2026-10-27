# Why we lose: Intercontinental Fish (205 games) and our ranked losses (Oct 26, patch 2.0.0)

The user (Oct 26, 17:39 IST): v19 was worse than v18 against IC; roll back to v18, analyse the new and the old IC matches deeply,
build a bot that beats IC by using its strategy and its shortcomings, quality over speed, nothing on the website until told. 17:43 IST:
"see our previous ranked battle losses too and overcome those problems too".

## 1. Data

- **IC**: 205 games of GOD v18 / v19 against IC on the whole sprint-3 pool (interim v18 65, final v18 70, v19 70; `experiments/ic_oct26_v18/`,
  decoded index `/tmp/claude-0/ic_all.json` during the session). Results: 7/65, 8/70, 5/70.
- **Ranked**: our 360 ranked games on engine 2.0.0 (Oct 26 00:24-12:10 UTC: v17 315, interim v18 30, v18 5, v19 10), 183-177. The 177
  losses and 70 wins decoded (`experiments/ladder_oct26_v18/`: `ranked_me.jsonl`, `rk_index.py`). We are 51st (1,943); IC is first (2,390).
- Scripts: `experiments/ic_oct26_v18/analysis/` (`icx.py` loader, `ic_open.py` opening and zones, `ic_pack.py` cohesion, `ic_budget.py`
  time budget, `mapgroups.py` captures per group, `deaths_ctx.py`, `trace.py` per-body traces, `capsum.py`, `permap.py`, `contest_idx.py`).

## 2. The game is decided in the middle

Captured gems a game by zone (M = groups about as far from both spawns, O = our half, T = theirs) and phase (p0 < r200 < p1 < r500 < p2):

| | O p0/p1/p2 | **M p0/p1/p2** | T p0/p1/p2 |
|---|---|---|---|
| IC games (final v18): us | 52 / 104 / 120 | **17 / 48 / 80** | 0 / 3 / 11 |
| IC games: IC | 66 / 131 / 188 | **77 / 154 / 360** | 4 / 17 / 47 |
| ranked losses (177): us | 52 / 92 / 180 | **15 / 32 / 94** | 1 / 4 / 14 |
| ranked losses: them | 56 / 105 / 270 | **45 / 101 / 406** | 5 / 13 / 62 |
| ranked wins (70): us | 60 / 122 / 294 | **31 / 76 / 401** | 2 / 6 / 29 |
| ranked wins: them | 60 / 110 / 260 | **32 / 50 / 141** | 5 / 5 / 21 |

70% of the gap in our ranked losses is the middle; in our wins we hold it. IC and the ranked teams that beat us bring more bodies:
first group of the game shared by 4.35 bodies (IC) / 3.2 (ranked winners) against our 2.3-2.5; allies within 4 of a capture 1.7 / 1.6
against our 0.7.

## 3. How IC plays (traces, `trace.py`)

- **One pack**: the whole team (6 bodies on 5-champion maps: Cassi & Issac) clears one group, then the next. Corners: G19 (its near elk
  group) r7-17 x6, then the four middle groups G27 r22, G26 r37, G29 r55, G28 r70, Marcella capturing each; then the pack sits in the
  middle and retakes every middle group on its respawn (G27 again at r103, G26 r127 ...) and raids our half between respawns (r82-112,
  2 of ours killed). Corners totals: IC 909 captured (middle 644), we 316 and 0 of the 4 middle groups.
- **Bank next to the work**: Marcella (2 gold a gem banked) captures and banks at the central altar (35,34) every 10-20 rounds; IC banks
  27 times a game (we 12), bags of the same size (median 25 vs 22). Altar lock on that altar (2.6 a game).
- **Pack loosens later**: largest pack 3.4 / 2.6 / 2.3 / 2.0 bodies by phase (ours 2.2 / 1.8 / 1.8 / 1.6).
- **Items follow the gold**: Treasure first, then Bruiser strength emblems: strength from items at r800 107 vs our 43.
- **Time budget** (share of body-rounds): IC hits camps 17.2% (us 10.3%), is dead 9.8% (us 15.0%), walks with an enemy within 8 14.2%
  (us 20.0%). Captures a game 39.6 vs 21.7, hits per capture equal (28 vs 24): IC simply farms twice as long, because it holds the
  middle and does not die.

## 4. How we lose (traces)

- **Corners**: four of ours clear G18, walk to the middle at r34, meet IC's six, walk back, wander until r60; Heart of Ruin carries 22
  gems for 66 rounds without banking and dies with them; Vesper solos a wolf for 27 rounds.
- **Elk arena** (the only gems: a 72-gem group in the centre): we lose the first fight (2 dead by r31) and the other three walk to the
  corners to farm gold groups for 50 rounds while IC's three survivors take the 72 gems.
- **Maps with a rich centre** (vault, the-line, quarry, fragment, ribs, pilgrimage, reverse spiral, rushbait): IC 760-1,000 captured,
  we 0-385; we die 12-23 times.
- **Heavy groups**: ranked winners cycle their elk / rich groups about twice as often as we cycle ours (great wall, big world, eight).
- **Deaths**: 80% while fighting, 65% with 2+ enemies near and a local health ratio below 0.8; Vendetta 2.7 a game (IC's 0.6).
- **Ranked map record** (engine 2.0.0): at most one win in rushbait-v2 0-6, eight 1-7, fragment 0-6, big-world 1-6, elk-arena 0-5,
  quarry 0-5, great-wall 1-6, reverse-spiral 0-5, ribs 0-4, pilgrimage 0-4, the-pack 0-3, gold-rush 0-3; corners 2-6, stampede 2-5,
  dunes 2-5. Best: boss-battle 8-1, harvest 9-2, gemcombat5 6-0, guardians 6-0, vault 5-0, stalactites 5-0.

## 5. What the evidence says to change

- **Win the opening economy.** In ranked games the capture difference at r300 decides: ahead by 60+ we win 16/23, behind by 60+ 8/92
  (r150: we are behind by 20+ in 109 of 247 games, ahead in 32). Items at r150 are equal in our losses (12.0 vs 12.3 shard
  equivalents) and 15.8 vs 9.0 in our wins; by r800 84 vs 124 and 137 vs 85.
- **Fights follow the economy.** Team fights (2+ enemies within 5 of a body): early (r < 250) with more bodies we win them (deaths per
  episode 0.38 vs IC's 0.54), even numbers we lose (0.51 vs 0.35); late we lose them whatever the numbers (0.46 vs 0.30 with more
  bodies). In our ranked wins we win every kind (0.16 vs 0.75).
- **Near an enemy, keep farming.** With an enemy within 8, IC hits something 35% of its turns, we 23%; when ahead we step toward the
  enemy 38-41% of those turns (IC 24%), when behind we walk away 34-36% (IC 28-32%, and still hits 32-36%).
- **Bring numbers where the gems are.** Rushbait (ranked loss, mirror draft): the other team's four bodies clear the small groups of
  one lane one after another (G1 r6-15, G3 r16-25, G5 r26-40 ...), while ours walk 25 rounds to a far elk group and Vesper solos a wolf
  for 40 rounds (4 gems). Pilgrimage (v18 alone, no enemy): no body touches the 33-gem elk groups or the 88-gem centre in 250 rounds.

## 6. GOD v20 work: the pack (`bots/god20`, every switch off by default = v18)

- **`g20_pack` 1** (v1): followers farm the group the lowest-index living claimant ("leader") claims, the leader plans with the
  damage of the allies within 10. It hardly packed (largest pack 2.4 bodies in p0; IC 3.4): followers left the leader's group on
  the join-reach rule (223 of 815 follower turns on corners), on "too heavy for us" (54), and every body picked its own target the
  moment the pack's group died.
- **`g20_pack` 2** (v2): a claim on a dead group still leads unless that ally stands on the reward; followers hold next to it up to
  3 rounds (`g20_hold`); a new leader first rejoins the group most others claim; join-reach and the solo heavy check do not apply to
  the pack's group. Corners trace: G18 x5, G16 x4, middle G26 x5, G28 x5, G27 x4, captures banked at the central altar, as IC does.
- **v3** (`g20_safe` 1, `g20_leash` 4): the pack skips a group whose camps would deal more than its spare health while it clears it
  (starfish: 3 of 4 died to the 6-elk centre), and a body in pack mode does not walk after a target more than 4 steps deeper in their
  half (crater: five of ours chased to their spawn from r16 to r61).
- **`g20_adapt` 2**: the pack plan only while an enemy pack (3+ bodies within 3 tiles of one of them) was seen in the last 60 rounds,
  or an ally posted DANGER. **`g20_max_area`**: no pack on maps larger than 60x60.
- Lone-monolith and objective maps keep their own team plans (`g20_modes` 0).

Results against GOD v18 on the 70-map pool (140 games, margin = our banked gems minus theirs a game, bootstrap 95%):

| variant | wins | margin |
|---|---|---|
| v1 (`_pk1`) | 64/140 | -57 [-143, +30] |
| v2 (`_pk2`) | 61/140 | -93 [-181, -12] |
| v3 (`_pk3`) | 65/140 | -28 [-121, +69] |
| v3 until r200 (`_pk3u2`) | 68/140 | -6 [-88, +78] |
| adaptive (`_pkA`) | 72/140 | -22 [-111, +66] |
| farm-first (`_ff`: keep hitting a live camp while no enemy can reach us) | 69/140 | -44 [-113, +20] |
| IC's rosters on the v1 pack (`_icc`) | 51/140 | -142 |

Against a pack opponent (`_pk3`): v18 75/140 (+28), adaptive `_pkA` **85/140, +107 [+18, +194]** (paired with v18's games: +80
[-33, +192]). v18 beats the IC clone with the v2 pack (`_icc2`) 85/140, +154: our brain with IC's drafts and a pack is not IC.

Per-map margins are dominated by chaos: an inert code change (fuel spent elsewhere) moves single maps by +-900 gems, so per-map
selection (the `g20_pack_maps` table) does not survive; only pooled effects of 100+ gems are visible in 140 games. Unopposed
opening pace (captured by r150 / r250, 70 maps alone): v18 114 / 207, always-pack 102 / 185, pack only for 80+ gem groups 112 / 204
(vault 379 -> 698, the-line 370 -> 511; quadrants 449 -> 239).

## 7. The candidate sweep (big pool = s3 70 + var17 51 + gen2 24 maps, 290 games against v18; 140 against the pack bot `_pk3` and v17)

Margins are gems a game; "paired" = the candidate's games minus v18's games against the same opponent, map and side.

| candidate | vs v18 (290) | vs pack bot, paired | vs IC clone `_icc2`, paired | vs v17, paired with the null control |
|---|---|---|---|---|
| **null control** (`bots/god20`, every switch off: v18's play + inert code) | 145/290, +10 [-14, +33] | | | (-43 vs v18's own games) |
| adaptive pack `_pkA` | 144/290, -20 [-74, +33] | +80 [-33, +192] | +25 [-66, +118] | -4 |
| adaptive, 4-body trigger `_pkA4` | 139/290, -24 | +86 | | |
| adaptive, own sightings only `_pkA1` | 145/290, -14 | +70 | | -25 |
| adaptive, 30-round memory `_pkAm30` | 137/290, -37 [-84, +8] | **+116 [+15, +223]** | | -24 |
| adaptive until r250 / whole game | 134 / 133 of 290, -23 / -34 | +50 / +55 | | |
| middle pull 8 / 16 (`g20_mid_pull`) | 133 / 147 of 290, -26 / -4 | 0 / +16 | | |
| captures to Marcella (`mi_capture` 2) | 145/290, +17 [-23, +57] | -6 | | -48 |
| join rich harmless groups (`g18_rich` 1) | 142/290, -8 [-36, +21] | +34 | | -32 |
| split 100+ gem rewards (`g20_split` 100) | 147/290, +14 [-14, +42] | +37 | | -32 |
| `_v20c` = `_pkA1` + Marcella + rich | 146/290, -12 | +54 | -7 | -89 |
| **`_v20d` = `_pkAm30` (DANGER alerts too) + Marcella + rich** | **150/290, +23 [-27, +73]** | **+87 [-21, +202]** | **+27 [-76, +121]** | -45 [-153, +64] |
| `_v20e` = `_v20c` + split | 146/290, -15 | +62 | -9 | -86 |
| `_v20n` = Marcella + rich + split, no pack | 144/290, +7 | +12 | +40 | -59 |

The null control shows the noise floor: v18's own play with a few unused lines of code moves the big-pool margin by +10 and the v17
margin by -43 (v18's +154 against v17 is partly a lucky draw: any code change reshuffles those games). No candidate is clearly better
than v18 against v18 or v17; the pack variants are consistently better against a pack opponent.

## 8. Confirmation and decision

`_v20d` (the best of the sweep) on 80 maps it had never played (ct2, gold3, pad17, obj; 160 games each): vs v18 75/160, -12 [-80, +55]
(ct2 +4, gold3 +17, pad17 -43, obj -71); vs the pack bot, paired with v18's own games on those maps, +2 [-80, +81]. Its s3 advantage
against the pack bot (+87) was the winner of ten noisy comparisons and did not hold.

**Decision: no new build. GOD v18 stays the recommended bot.** Nothing measured here beats v18 locally (every candidate is within the
noise floor of the null control), and the one property that looked better (play against pack opponents) did not survive fresh maps.
v19 showed that a locally level change can lose to IC on the website (5/70 vs 8/70), so a level candidate is not shipped as "better".
`_v20d` is kept as a candidate zip (`submissions/candidates/god20d_adaptive_pack_20261026.zip`) for a website A/B against IC only if the
user asks for one. `bots/god20` keeps every switch (off by default = v18's play).

What the study says to work on next (not solved here): the opening economy and the middle (section 2, 5). The pack as built is a
weaker farmer than v18's spread on large maps and on many-small-group maps (unopposed pace -10%), and our brain with IC's drafts and a
pack still loses to v18 (`_icc2`): IC's edge is not the pack alone but how efficiently it farms and fights inside it.
