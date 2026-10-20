# 13. `legend_m14_commit` on the ladder, 19 Oct 2026 (session 13)

Input: the user's `new_matches.zip`: 10 match groups, **50 games, 11 wins** (`experiments/ladder_oct19b/<group>_<NN>_<side>.repl26a`,
`index.json` = map, our side, both drafts, score; we are side B in group cd6785ff). Tables: `experiments/ladder_oct19b/analysis/`
(`run_all.py` CSVs; `pergame.txt`). Tools added: `tools/strategy_v2/ladder_pergame.py`, `ladder_deaths.py`, `death_ctx.py`, `burst_ctx.py`
(all read our side of each game from `index.json`). Contest is left out of the farming and death numbers unless stated (3 games, 204 of our deaths).

## 1. Opponents and results

| Group | Profile (their draft) | Wins |
|---|---|---|
| 2306b82f | Varg / Ryth first; casters on stampede and contest | 0/5 |
| 25464f3d | C&I first + Tavi / Willow / Vendetta | 0/5 |
| 43bd73e8 | C&I first (C&I, Ren, Varg, Ryth, Stellar) | 1/5 |
| 44b9a95f | Varg first (Varg, Stellar, C&I, Ryth, Ren) | 2/5 |
| 5f7de946 | Tavi / Willow casters | 1/5 |
| 6713bf97 | Ren first (the old ifish table) | 2/5 |
| 78da97d8 | C&I first + Vendetta / Tavi | 1/5 |
| c3f76526 | Stellar first (IC) | 1/5 |
| c6ed5477 | Stellar first + Tavi | 1/5 |
| cd6785ff | C&I + Tavi (we are side B) | 2/5 |

## 2. What decides the games

Per game, 47 non-contest games (us / them): deaths 7.2 / 5.5, camp gems 733 / 993, gold 3,278 / 4,524, captures on our half / neutral /
their half 15.9 / 2.6 / 0.4 vs 19.3 / 6.1 / 1.3, camp damage per round 81 / 108; body time walking 50.4% / 46.1%, on camps 17.8 / 20.1,
capturing 1.9 / 4.5, dead 13.1 / 9.6.

1. **Farming speed.** Their finishing round *with us on the map* beats our *unopposed* pace (`_ch2` vs idle) on rows (348-358 vs 393),
   lanes (450 vs 462), monolith (408 vs 454), pilgrimage (570 vs 630) and ambush (499 vs 508). Same draft and no deaths for us (monolith,
   43bd73e8_03): they captured 1,126 camp gems to our 900 by r408 because they take every near group again right at its respawn (the 22-gem
   group 6 steps from their spawn at r19, 80, 137, 197, 270, 330, 381); we left the same group alone r92 -> r193 -> r315 while walking to far
   groups. Gold per 100 alive rounds by champion (them / us): Issac 174 / 111, Cassi 118 / 70, Ryth 167 / 102, Stellar 169 / 94; first emblem
   Issac r227 / r375, Ryth r209 / r330, Cassi r400 / r499. Their captures are spread over all bodies; ours pile on Ren.
2. **Close races lost on timing.** rows (5 games, 0 deaths both sides): we reached 990 banked at r345, they reached 990 at r355 and won at r358
   with a 22-gem bag while every one of our bodies walked to a 66-gem group. Same in 990-1023 and 990-1056.
3. **Burst deaths of Cassi & Issac.** 41% of our deaths start at >= 60% health 3 rounds before (theirs 34%); 99 of those 147 are Cassi or Issac;
   the nearest enemy is at distance 4-5 (35%) and 68% of the damage is spells; we hit back in only 32% of them.
4. **Objective rewards are stolen from dead tiles.** Stampede vs the Varg-first team: we killed the 360-gem objective all 4 times (damage 17,400 /
   0, 11,931 / 3,669, ...) and captured once; their Ren and Stellar stood on the dead gem tiles of the group while our ring stood at distance 4,
   so the reward landed under them. Against IC we did the same to them: they killed it 3 times, we captured all 3 (1080-0).
5. **Contest: 0/3, deaths 87, 66, 51.** The first team fight at the centre triple (r30-45) is lost every time (our blob of 6 bodies against
   5 casters hiding in the altar bush; our Ren, at full health, completed a recall home at r31 as the fight started), then bodies keep walking
   into the centre and die at full health without hitting back. They win on gold (24,186 vs 2,522 in the 0-0 game) or by monoliths (r1094, r1758).
6. **Camp pulling.** Fragment (same draft): they woke an elk and stepped back; our Ren walked into its range and stood next to it for 8 rounds
   (740 -> 0, killed by the camp); Cassi & Issac at 220/700 stayed in the field and died to area casts.

No fuel problem: 72 of our turns roll over, all in rounds 1-6.

## 2b. Deeper traces (session 13, later)

- **Our farming is not the gap, contact is.** Unopposed, `_ch2` captures 151 gems by r100 and 564 by r300 (15 maps); the ladder teams
  manage 136 / 480 while contested, and we fall to 111 / 401 on the ladder. By r150 (items still about equal) they deal 21% more camp damage
  (16.1k vs 13.3k), more champion damage (1.66k vs 1.27k) and die less (0.9 vs 1.3 per game). First contacts (an enemy within 5 after 5+
  quiet rounds; `tools/strategy_v2/contact.py`): we close the gap ourselves in 33% (they 20%) and the first 4 rounds go 205 dealt / 251
  taken for us, 237 / 170 for them. Distance bands (`micro.py`): at 3 they deal 47 and take 31 per body-round, we 29 / 42.
- **Unopposed pace understates race pace**: ahead by `lead` (150) the bot banks smaller bags; unopposed it always is (rows: 345 rounds to 990
  on the ladder vs 393 unopposed to 1000).
- **Contest centre fight** (r20-45, every game): both teams reach the centre by r25; ours splits: Ren recalls home at r31 (full health) or
  keeps farming the centre gold 10-13 tiles from the fight (rallies are answered only within 9, never while capturing); their casters stand
  at 3-4 in the altar bush and focus Cassi and Varg; our melee do not dive. Locally `_ch2` wins contest 9 of 10 against every proxy (deaths
  7-37 vs 47-66): the mirror image of the ladder; the proxies cannot reproduce the ladder teams' caster play.
- **Stampede ring race** (2306b82f_01, 72-1008): r55-118 they dealt 13.5k to the objective camps vs our 7.2k (6 bodies with tanks and casters
  within attack range against our 5 casters at distance 4; our Issac farmed elsewhere while Cassi rang the objective) and 2.2k to our bodies.
  Locally the same plan wins 8 of 10 stampede games (it loses both to the sneaky-bush proxy, whose ring out-damages ours).

## 2c. Mite (group 2306b82f) and the Nyx candidates (after `legend_m15`; the user: "still losing to Mite and Nyx")

- Mite = 2306b82f: its drafts match our MITE table (session 10) except that Ren replaced Tavi as the 5th pick (stampede, contest). We lost 0/5:
  interlock 650-1010 and collision 476-1018 while winning the kills (deaths 6-10, 12-16), swirl 88-1004 (deaths 20-3), stampede 72-1008
  (objective stolen), contest 0-0 on gold.
- Interlock (40x40, spawns in opposite corners, our 3 wolf packs on x = 5, theirs on x = 34, elk pairs in the two other corners): Mite put
  4 bodies on the corner elk pair (31-32, 10) from r40 and took it at r63, then took the corner elks 8 times (576 gems; ours 0 neutral). Our
  bodies farmed only our 3 wolf packs: Issac solo-cleared one in 25 rounds (720 -> 280 HP), Cassi banked at the centre altar at r57 and then
  hovered at (21-29, 16-25) for 70 rounds placing wards. Unopposed `legend_m15` takes those elks (648 neutral gems), so it is contact, not scoring.
- Swirl (45x30, spawns top / bottom 15 apart): 20 of our deaths at the centre camps (18-22, 12-15), from r56 on: Mite holds the centre and our
  bodies walk back in one or two at a time (0-160 at r100, 0-408 at r200).
- All 10 groups (`$S/respawn_ctx.mjs`, 47 non-contest games): an own-side camp that respawns is first hit after 39.3 rounds by us, 33.8 by
  them, with an ally within 5 at the respawn in 48% / 49%; but they kill their own-side camps 919 times to our 672 (+37%): faster clears, more
  bodies alive, less walking. Captures 1.5-2x ours in most games.
- Nyx: not identified (no file names teams); 25464f3d (C&I-first + Tavi / Willow / Vendetta, 0/5: two close races, two blowouts) or
  44b9a95f (Varg-first everywhere, 2/5). A Mite proxy on our brain with their drafts / builds / ring / reward stealing (`_mite2`) loses to
  `legend_m15` 26/34: the gap is their execution, which our code family does not reproduce.

## 3. What was built and measured (session 13)

See AGENTS.md §S13 for the live state, `experiments/wip/x_s13.patch` (coordinator switches) and `experiments/wip/x_zone.patch` (zones agent).

Shipped: **`legend_m15`** (`_mlkc40`): `legend_m14_commit` + a danger model learned from these ladder games (logistic P(die within 8
rounds), AUC 0.81 on our ladder bodies vs 0.60 for the bot's own fight estimate; drop escapable fights and walk away at P >= 0.4; a deadly
state counts as cornered, so the body trades instead of giving free hits) + `aoe_reach5` 2, `open_first` 2, `recall_join` 1, `o2_ring_size` 0.
Locally: 149/170 vs the 5 proxies on the official maps (`_ch2` 129), 475/670 on 67 more maps (452), deaths -13%. Everything that did not
measure better is in SUGGESTIONS.md (session 13 tables). The proxies are our own code family, so the ladder decides.

