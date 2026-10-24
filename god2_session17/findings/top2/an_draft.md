# Draft and team composition of the top teams (an_draft)

Dimension: draft and team composition. Data window: ranked games of the current bot versions (Oct 22 07:00 to Oct 23 15:00 UTC,
engine 1.0.3 = patch 3.0.4 balance). Every claim is tagged **[M]** (measured in the data, numbers given) or **[I]** (inferred /
interpretation). Draft ids: 0 Ryth (Ry), 1 Vesper Vale (Ve), 2 Vendetta (Vd), 3 Cassi & Issac (CI; Cas / Iss bodies), 4 Stellar (St),
5 Prism (Pr), 6 Marcella (Ma), 7 Willow (Wi), 8 Ren (Re), 9 Varg (Va), 10 Tavi (Ta), 11 Heart of Ruin (Ho).
Study teams: pbg = prism best girl (#1), ifish = Intercontinental Fish (#2), pantheon (#6), coo = conqueror_of_openai (#18),
cm = Claudus Maximus (#19), nyx (#31).

## 0. Summary (ranked by how much it matters for beating these teams)

1. **The Prism teams (pbg, Pantheon, Nyx) win through one carrier's bag, and lose when that bag is denied.** [M] pbg's Prism holds a
   time-averaged bag of 111 gems (per-game maximum 305 on average) and banks it in a few huge tributes: 408 gems on average at the start of a tribute
   (a 41-turn channel). Only 51 of 100 of those tributes complete; every other champion of every study team completes 92-100%.
   In pbg's 44 lost games (dumps) its Prism banked **0** gems, against 299 a game in its 71 wins. The same holds for Pantheon
   (264 vs 5 a game) and Nyx (172 vs 32 a game). The bag is destroyed by kills (stolen) and the channel by altar locks and stuns.
2. **ifish is a one-carry team.** [M] Its Vesper banks 42% of ifish's gems and takes 49% of the captured gold, but ends games with
   only 1,568 max HP (pbg's and Nyx's Vespers: ~5,900). In ifish's 43 losses its Vesper dies 3.4 times a game and loses 248 gems a
   game, against 0.7 deaths and 12 gems in its 64 wins.
3. **3-champion maps are the top two's weak spot, and the most random maps on the ladder.** [M] Since Oct 22 18:00, the opponents of
   pbg win 36 of 64 games on 3-champion maps (rating-expected 21-30) and those of ifish win 33 of 58 (expected 24-28). On 4-champion
   maps the same two teams dominate: their opponents win 19/88 and 20/74. Rating barely predicts 3-champion results: the logit
   slope is 0.10-0.44 per 100 rating points there, against 0.35-1.09 on 4-5 champion maps. The best-known answer is Vesper +
   Vendetta / Marcella + Tavi: :3 and policy wonk went 28-5 against pbg + ifish on these maps.
4. **Within the current meta, the draft itself is worth little; the rating gap is worth a lot.** [M] Over 3,987 top-50 games of Oct 23,
   champion picks add no out-of-sample signal to the rating difference (likelihood-ratio p = 0.27; cross-validated log loss 0.6773
   without picks, 0.6789 with). The only champions that are negative in every fit are **Ren and Stellar**, the core of our old g8 draft.
   Three study teams dropped Stellar / Ren for the Vesper + Vendetta or Vesper + Prism core after patch 3.0.4 and gained +66 to +128
   performance-rating points.
5. **Every top draft is a fixed priority list truncated by team size.** [M] pbg, ifish, coo, Nyx and Pantheon's newest version pick
   the same champions on every repeat of a map (purity 1.00). Nobody changes its champions because of the opponent's picks. cm only
   swaps the order of its last two picks. Team size (3 / 4 / 5, fixed per map) is the only robust map dependence. The per-map swaps of
   pbg, ifish and coo are not explained by map features better than chance (permutation p 0.06-0.35).
6. **The consensus core is Vesper + Heart of Ruin.** [M] Vesper is in 88-100% and Heart of Ruin in 76-100% of the study teams' drafts
   (84% and 86% over the top 50). Then come Marcella (79%), Ryth (64%) and Vendetta (61%). Vesper is a main banker and gold sink in
   every team: 24-46% of banked gems and 27-50% of captured gold (in cm and coo, Vendetta banks as much or more). Heart of Ruin is
   the frontline (22-32% of damage taken) and banks little.

The rules in section 9 turn this into a draft computed from engine stats, team size and the opponent's revealed picks, plus the
in-game hooks the composition needs.

---

## 1. Draft rules (docs/sprint/v3_0_4/GameRules.md, "Drafting", "Who goes first?", Altar locks)

- Each map fixes the team size: 3, 4 or 5 champions. [M] The lists confirm one size per map (table in 3.1): 6 maps of 3
  (collision, fragment, packs, broken_curve, gold_rush, the_farm), 8 maps of 4 (gemfight, interlock, reverse_spiral, rows,
  rushbait_v2, swirl, hooks, shortcut) and 26 maps of 5.
- Picks are made one at a time, and both teams pick simultaneously, "revealing their picks as they go". So at pick i a team sees
  the opponent's picks 1..i-1 (`bc::draft::current_draft(team::enemy)`).
- A champion is unique within a team, but **both teams may pick the same champion**. Nothing can be denied: the pick order only
  leaks information.
- Cassi & Issac is one pick that gives two bodies. If either dies, both die, and the pair gives one kill reward.
- A missed pick (yield, fuel-out or crash) is filled at random. The first draft turn gets 10x fuel, and a 1024-byte draft memory
  passes the plan to the bots.
- Draft order also sets acting order inside a team ("priority, then draft order") and the capture-remainder tie-break (lowest id).
  `set_priority` can override the acting order.
- Altar lock: 10 gold, one carried at a time, placed on an altar within 2 tiles. It cancels the enemy tribute channels at that altar.
  Five basic attacks clear it. A tribute lasts max(1, ceil(bag/10)) turns. Stun, death or a new lock cancels it; damage does not.

Implication [I]: the draft is a planning step. It can neither deny nor punish an opponent pick directly. What it can do is (a)
choose kits that fit our plan and (b) read the opponent's archetype from its first picks and write the counter-plan into the draft
memory.

## 2. Data and method

- **Lists** [M]: `experiments/live/lists/**` (14,532 distinct finished ranked matches since engine 1.0.3, Oct 22 07:00), including
  `wr/*.jsonl` (3,987 matches of the top 50 teams, Oct 23 09:50-15:00; both teams rated in `C:/battlecode/cache/ladder_now.json`).
- **Dumps** [M]: `C:/battlecode/cache/t2dump/<key>/*.json.gz`, 638 files: pbg 116, ifish 110, Pantheon 105, coo 101, cm 106, Nyx 100.
  Deduplicated per team: pbg 115 (71 W), ifish 107 (64 W), Pantheon 103 (51 W), coo 101 (55 W), cm 106 (58 W), Nyx 99 (48 W).
  Body-level metrics are in `experiments/top2/draft_roles.jsonl`; tribute attempts are in `experiments/top2/draft_tributes.jsonl`.
- **Map features** [M]: `experiments/top2/draft_mapfeat.json`. It combines W, H, wall, bush and hole from map_terrain.json, team size,
  spawn Euclid distance, spawn-to-spawn walk distance from an_strategy mapgeo2, and the camp mix and rewards from meta.camps.
- **Rating model** [M]: logit P(side a wins) = b0 + k·(r_a − r_b)/100. On the window k = 0.72 ± 0.07 per 100 points. Side a wins
  49.9%, so there is no side effect.
- **Games are deterministic per (bots, map, sides)** [M]. 7 pairs of the 584 dumped matches are identical replays an hour apart, e.g.
  `t2/pbg/00collision_5818f117` = `_75b04c87` (policy wonk 1006-536 both times). In the lists, 77-80% of repeated identical matchups
  (same teams, sides, map, drafts) have identical results. Repeats are 3.6% of the window, so they inflate sample sizes only slightly.
- Tools (all new, `tools/top2/draft/`): `common.py` (loaders, map features), `team_drafts.py` (draft per map and hour),
  `reactivity.py` (does a pick depend on the side or the opponent's earlier picks), `map_table.py` (per-map table, rule search),
  `comp_value.py` (logit models M0-M4), `comp_matrix.py` (comp vs comp, rating predictiveness by size and map), `flex_slot.py`
  (flex picks on top of a core), `counters.py` (counter-picks against an archetype), `vs_team.py` (what beats a team,
  head-to-head), `roles.mjs` + `roles_agg.py` (body role profiles from dumps), `tributes.mjs` (tribute attempts and why they
  fail), `carrier_kills.py` (who kills gem carriers).

## 3. The study teams' drafts

### 3.1 Current drafts per map [M]

The modal draft over each team's current version, in pick order. pbg uses games since Oct 22 18:00, ifish since Oct 22 08:00,
Pantheon since Oct 23 12:00, and coo, cm and Nyx since Oct 23 09:50. "(k/n)" marks the maps where not every game used the modal
draft.

| map | size | W x H | spawn d | hole | bush | gems | heavy | mono | pbg | ifish | pantheon | coo | cm | nyx |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 00collision | 3 | 41x41 | 36 | 0.04 | 0.13 | 280 | 0.54 | 0.00 | Pr/Ve/Ho | Ve/Ho/Vd | Pr/Ve/Ho | Ho/Ve/Va | Ve/Vd/Ho | Ho/Ve/Pr |
| 00fragment | 3 | 30x30 | 27 | 0.36 | 0.03 | 68 | 0.44 | 0.00 | Pr/Ve/Ho | Ve/Ho/Vd | Pr/Ve/Ho | Ho/Ve/Va | Ve/Vd/Ho | Ho/Ve/Pr |
| 00packs | 3 | 31x31 | 40 | 0.00 | 0.06 | 148 | 0.41 | 0.00 | Pr/Ve/Ho | Ve/Ho/Vd | Pr/Ve/Ho | Ho/Ve/Va | Ve/Vd/Ho | - |
| 01broken_curve | 3 | 40x40 | 31 | 0.00 | 0.04 | 746 | 0.78 | 0.54 | Pr/Ve/Ho | Ve/Ho/Vd | Pr/Ve/Ho | Ho/Ve/Va | Ve/Vd/Ho | Ho/Ve/Pr |
| 01gold_rush | 3 | 31x31 | 26 | 0.07 | 0.05 | 266 | 0.75 | 0.75 | Pr/Ve/Ho | Ve/Ho/Vd | Pr/Ve/Ho | Re/Ve/Ho | Ve/Vd/Ho | Ho/Ve/Pr |
| 01the_farm | 3 | 50x40 | 44 | 0.00 | 0.04 | 1096 | 0.72 | 0.36 | **Pr/Ma/Ho** | Ve/Ho/Vd | Pr/Ve/Ho | Ho/Ve/Va | Ve/Vd/Ho | Ho/Ve/Pr |
| 00gemfight | 4 | 30x30 | 35 | 0.12 | 0.02 | 200 | 0.15 | 0.00 | Pr/Ma/Ry/Re | Ve/Vd/Ho/CI | - | Ho/Ve/Va/Vd | Ve/Vd/Ho/Ta | Ho/Ve/Pr/Ma |
| 00interlock | 4 | 40x40 | 52 | 0.01 | 0.02 | 200 | 0.60 | 0.00 | Pr/Ve/Ma/Ry | Ve/Vd/Ho/CI | Pr/Ve/Ma/Wi | Ho/Ve/Va/Vd | Ve/Vd/Ho/Ta | Ho/Ve/Pr/Ma |
| 00reverse_spiral | 4 | 30x30 | 3 | 0.04 | 0.02 | 334 | 0.40 | 0.00 | Pr/Ve/Ma/Ry | Ve/Vd/Ho/CI | Pr/Ve/Ma/Wi | Ho/Ve/Va/Vd | Ve/Vd/Ho/Ta | Ho/Ve/Pr/Ma |
| 00rows | 4 | 50x50 | 59 | 0.00 | 0.06 | 584 | 0.69 | 0.69 | Pr/Ve/Ma/Vd | Ve/Vd/Ho/**Va** | Pr/Ve/Ma/Wi | Ho/Ve/Va/Vd | Ve/Vd/Ho/Ta | Ho/Ve/Pr/Ma |
| 00rushbait_v2 | 4 | 30x80 | 4 | 0.06 | 0.05 | 258 | 0.47 | 0.00 | Pr/Ve/Ma/Ry | Ve/Vd/Ho/CI | Pr/Ve/Ma/Wi | Re/Ve/Ho/Vd | Ve/Vd/Ho/Ta | Ho/Ve/Pr/Ma |
| 00swirl | 4 | 45x30 | 18 | 0.26 | 0.01 | 638 | 0.56 | 0.00 | Pr/Ve/Ma/Vd | Ve/Vd/Ho/CI | Pr/Ve/Ma/Wi | Ho/Ve/Va/Vd | Ve/Vd/Ho/Ta | Ho/Ve/Pr/Ma |
| 01hooks | 4 | 31x31 | 37 | 0.00 | 0.06 | 88 | 0.68 | 0.00 | Pr/Ve/Ma/Ry | Ve/Vd/Ho/CI | Pr/Ve/Ma/Wi | Re/Ve/Ho/Vd | Ve/Vd/Ho/Ta | Ho/Ve/Pr/Ma |
| 01shortcut | 4 | 40x40 | 13 | 0.09 | 0.03 | 990 | 0.71 | 0.40 | Pr/Ma/Vd/Re (12/13) | Ve/Vd/Ho/CI | Pr/Ve/Ma/Wi | Ho/Ve/Va/Vd | Ve/Vd/Ho/Ta (4/5) | Ho/Ve/Pr/Ma |
| 00ambush | 5 | 100x100 | 127 | 0.18 | 0.01 | 270 | 0.56 | 0.00 | Pr/Ma/Vd/Ho/Ve | Ve/Vd/Ho/Va/CI | Pr/Ve/Ma/Wi/Ho | Ho/Ta/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma | Ho/Ve/Pr/Ma/Vd |
| 00contest | 5 | 50x50 | 58 | 0.00 | 0.01 | 400 | 1.00 | 1.00 | Pr/Ve/Ma/Ry/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma | Ho/Ve/Pr/Ma/Vd |
| 00corners | 5 | 71x71 | 42 | 0.02 | 0.01 | 396 | 0.68 | 0.00 | Pr/Ve/Ma/Ry/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | - | Ve/Vd/Ho/Ta/Ma (1/2) | Ho/Ve/Pr/Ma/Vd |
| 00eight | 5 | 41x30 | 38 | 0.02 | 0.02 | 230 | 0.65 | 0.00 | Pr/Ma/Vd/Ho/Ve | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma (2/3) | Ho/Ve/Pr/Ma/Vd |
| 00elkring | 5 | 30x30 | 38 | 0.04 | 0.04 | 220 | 0.68 | 0.00 | Pr/Ma/Vd/Ho/Ve | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Re/Ve/Ho/Vd/Ry | Ve/Vd/Ho/Ta/Ma (3/4) | Ho/Ve/Pr/Ma/Vd |
| 00expanse | 5 | 80x80 | 100 | 0.00 | 0.00 | 362 | 0.58 | 0.00 | Pr/Ve/Ma/Vd/Ho | Ve/Vd/Ho/Va/CI | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma (3/4) | Ho/Ve/Pr/Ma/Vd |
| 00gem_fields | 5 | 50x40 | 11 | 0.02 | 0.06 | 364 | 0.17 | 0.00 | Pr/Ma/Ry/Ho/Ve | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | - | Ve/Vd/Ho/Ta/Ma (3/5) | Ho/Ve/Pr/Ma/Vd |
| 00great_wall | 5 | 50x40 | 37 | 0.04 | 0.03 | 1404 | 0.76 | 0.57 | Pr/Ma/Vd/Ho/Ve | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma | Ho/Ve/Pr/Ma/Vd |
| 00lanes | 5 | 90x30 | 83 | 0.03 | 0.05 | 294 | 0.31 | 0.00 | Pr/Ve/Ma/Ry/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Re/Ve/Ho/Vd/Ry | Ve/Vd/Ho/Ta/Ma (4/5) | Ho/Ve/Pr/Ma/Vd |
| 00lost_world | 5 | 35x31 | 28 | 0.04 | 0.02 | 592 | 0.45 | 0.34 | Pr/Ve/Ma/Ry/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Re/Ve/Ho/Vd/Ry | Ve/Vd/Ho/Ta/Ma | Ho/Ve/Pr/Ma/Vd |
| 00monolith | 5 | 50x50 | 61 | 0.00 | 0.03 | 670 | 0.64 | 0.60 | Pr/Ve/Ma/Ry/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma (3/4) | Ho/Ve/Pr/Ma/Vd |
| 00pilgrimage | 5 | 50x65 | 45 | 0.20 | 0.05 | 184 | 0.49 | 0.00 | Pr/Ve/Ma/Ry/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ta/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma | Ho/Ve/Pr/Ma/Vd |
| 00quadrants | 5 | 45x45 | 11 | 0.00 | 0.05 | 763 | 0.17 | 0.00 | Pr/Ma/Ry/Ho/Ve | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma (1/2) | Ho/Ve/Pr/Ma/Vd |
| 00road_of_riches | 5 | 40x40 | 14 | 0.01 | 0.03 | 1158 | 0.51 | 0.34 | Pr/Ve/Ma/Ry/Ho | Ve/Vd/Ho/Va/CI | - | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma | Ho/Ve/Pr/Ma/Vd |
| 00split | 5 | 45x35 | 22 | 0.02 | 0.03 | 850 | 0.66 | 0.47 | Pr/Ve/Ma/Ry/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma | Ho/Ve/Pr/Ma/Vd |
| 00stampede | 5 | 60x50 | 47 | 0.20 | 0.15 | 160 | 0.56 | 0.00 | Ry/Pr/Ve/Ma/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Pr/Ta/Ry | Ve/Vd/Ho/Ta/Ma (3/4) | Ho/Ve/Pr/Ma/Vd |
| 01big_world | 5 | 100x100 | 95 | 0.05 | 0.03 | 832 | 0.62 | 0.48 | Pr/Ma/Vd/Ho/Ve | Ve/Vd/Ho/Va/CI | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma | Ho/Ve/Pr/Ma/Vd |
| 01boss_battle | 5 | 50x41 | 39 | 0.00 | 0.00 | 1180 | 0.90 | 0.34 | Pr/Ve/Ma/Vd/Ry | Ve/Vd/Ho/CI/Ry | - | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma (5/6) | Ho/Ve/Pr/Ma/Vd |
| 01concentrated_wealth | 5 | 61x61 | 56 | 0.01 | 0.07 | 177 | 0.25 | 0.00 | Pr/Ve/Ma/Vd/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ta/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma (2/3) | Ho/Ve/Pr/Ma/Vd |
| 01corridors | 5 | 51x40 | 37 | 0.01 | 0.07 | 752 | 0.77 | 0.53 | Pr/Ve/Ma/Vd/Ho | Ve/Vd/Ho/CI/Ry | - | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma (4/5) | Ho/Ve/Pr/Ma/Vd |
| 01elk_arena | 5 | 50x50 | 22 | 0.00 | 0.07 | 72 | 0.42 | 0.00 | Pr/Ve/Ma/Ry/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Pr/Ta/Ry | Ve/Vd/Ho/Ta/Ma (5/6) | Ho/Ve/Pr/Ma/Vd |
| 01fracture | 5 | 61x71 | 85 | 0.12 | 0.06 | 844 | 0.76 | 0.47 | Pr/Ve/Ma/Vd/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma | Ho/Ve/Pr/Ma/Vd |
| 01islands | 5 | 60x60 | 51 | 0.24 | 0.11 | 608 | 0.54 | 0.00 | Pr/Ve/Ma/Ry/Ho | Ve/Vd/Ho/Va/CI | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma | Ho/Ve/Pr/Ma/Vd |
| 01starfish | 5 | 50x50 | 43 | 0.52 | 0.06 | 334 | 0.45 | 0.00 | Pr/Ma/Vd/Ho/Ve | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma (6/8) | Ho/Ve/Pr/Ma/Vd |
| 01starvation | 5 | 80x80 | 75 | 0.01 | 0.01 | 532 | 0.86 | 0.75 | Pr/Ve/Ma/Ry/Ho | Ve/Vd/Ho/CI/Ry | Pr/Ve/Ma/Wi/Ho | Ho/Ve/Pr/Ta/Ry | Ve/Vd/Ho/Ta/Ma (4/5) | Ho/Ve/Pr/Ma/Vd |
| 01yellow_brick_road | 5 | 40x30 | 32 | 0.00 | 0.24 | 472 | 0.51 | 0.00 | Pr/Ve/Ma/Vd/Ry | Ve/Vd/Ho/CI/Ry | - | Ho/Ve/Va/Vd/Ry | Ve/Vd/Ho/Ta/Ma (3/5) | Ho/Ve/Pr/Ma/Vd |

(heavy = share of the map's gems in elk / golem / monolith camps; mono = monolith share; gems = gems per full clear of all camps.)

The same drafts as size-indexed priority lists [M]:

| team | size 3 | size 4 | size 5 | pick 1 |
|---|---|---|---|---|
| pbg | Pr/Ve/Ho (the_farm: Pr/Ma/Ho) | Pr/Ve/Ma + Ry (4 maps) or Vd (2); no Vesper on gemfight / shortcut (Ren) | Pr/Ve/Ma/Ho + Ry (14 maps) or Vd (10); Pr/Ve/Ma/Vd/Ry without HoR on boss_battle, yellow_brick_road | Prism 146/150 |
| ifish | Ve/Ho/Vd | Ve/Vd/Ho/CI (rows: Va) | Ve/Vd/Ho/CI/Ry (21 maps); Va instead of Ry on ambush, expanse, big_world, road_of_riches, islands | Vesper 150/150 |
| pantheon (since Oct 23 12:00) | Pr/Ve/Ho | Pr/Ve/Ma/Wi | Pr/Ve/Ma/Wi/Ho, map-independent | Prism 150/150 |
| coo | Ho/Ve/Va (gold_rush: Re/Ve/Ho) | Ho/Ve/Va/Vd (rushbait, hooks: Re/Ve/Ho/Vd) | Ho/Ve/Va/Vd/Ry (15 of 24); Ren variants (3), Tavi variants (3), Prism + Tavi (3) | HoR 133/150, Ren 17 |
| cm | Ve/Vd/Ho | Ve/Vd/Ho/Ta | Ve/Vd/Ho/Ta/Ma, map-independent | Vesper 150/150 |
| nyx | Ho/Ve/Pr | Ho/Ve/Pr/Ma | Ho/Ve/Pr/Ma/Vd, map-independent | HoR 150/150 |

### 3.2 Determinism, side and reaction to the opponent [M]

`reactivity.py`: purity = the share of games whose pick equals the modal pick of its key, over keys seen at least twice. The keys are
map, map + side, and map + the opponent's earlier picks.

| team (window) | slots 1-5 purity given the map | given map + side | given map + opponent's earlier picks |
|---|---|---|---|
| pbg (150) | 1.00 / 1.00 / 1.00 / 0.99 / 1.00 | same | same |
| ifish (150) | 1.00 at every slot | 1.00 | 1.00 |
| coo (150), nyx (150) | 1.00 at every slot | 1.00 | 1.00 |
| pantheon (85, since Oct 23 12:00) | 1.00 at every slot | 1.00 | 1.00 |
| cm (150) | 1.00 / 1.00 / 1.00 / 0.83 / 0.81 | 0.80 / 0.77 | slot 4: 1.00 |

- Set level (champions regardless of order): pbg 149/150, ifish 150/150, coo 150/150, cm 149/150, Nyx 150/150 games use the map's
  modal set.
- cm is the only team that reacts to the opponent, and only by reordering. If the opponent picked Marcella before cm's 4th pick, cm
  takes Marcella 4th (62%, n=32); otherwise Tavi 4th (100%, n=44). The final set never changes.
- Pantheon's apparent variation in slot 4 over the whole window (0.69) is a version change at Oct 23 12:00 (Ryth or Vendetta became
  Willow), not randomness.
- No team depends on its side.

### 3.3 When the drafts changed [M]

From `team_drafts.py` (hourly share of games equal to the newest modal draft of the map) and the half-day draft history:

| team | until | from | new draft | performance rating before -> after (k = 0.72, opponents' current ratings) |
|---|---|---|---|---|
| ifish | Oct 22 ~07:00: Ry/CI/St/Re/Ho, CI/St/Re/Ho | Oct 22 08:00 | Ve/Vd/Ho/CI/Ry | 2153 (175 games) -> 2271 (715) |
| pantheon | Oct 22 ~11:00: Ry/Ve/St/Ma/Ho | Oct 22 11:00 | Pr/Ve/Ma/{Ry or Vd}/Ho | 2033 (265) -> 2161 (520) |
| pantheon | Oct 23 12:00 | Oct 23 12:00 | Pr/Ve/Ma/Wi/Ho | (too few games to separate) |
| nyx | Oct 23 ~09:00: Ry/St/Re/Ta/Ho | Oct 23 ~10:00 | Ho/Ve/Pr/Ma/Vd | 1903 (235) -> 1969 (150) |
| pbg | stable since at least Oct 22 07:00 (same champions; 24-28 of 30 games an hour already equal the newest map draft) | | | |
| coo | stable over the whole period | | | |
| cm | first games Oct 23 06:00 | | | |

[I] All three switches away from Stellar / Ren came with performance gains of +66 to +128 rating points. Each switch was also a new
code submission, so the draft's share of the gain cannot be separated. The direction agrees with the 3.0.4 patch (Stellar, Ren and
Heart of Ruin nerfed; Vesper, Vendetta, Prism and Tavi buffed) and with the regression in section 5.

### 3.4 Pick order [M]

- pbg: Prism p1 (146/150). Vesper is p2 (101) or p5 (36), Marcella p2 (45) or p3 (77), HoR p3-p5.
- ifish: Vesper p1, then Vendetta / HoR p2-p3, C&I p4-p5, Ryth p5.
- Pantheon: Prism, Vesper, Marcella. Nyx: HoR, Vesper, Prism, Marcella, Vendetta. cm: Vesper, Vendetta, HoR, Tavi / Marcella.
  coo: HoR (or Ren), Vesper, Varg, Vendetta, Ryth.

Since picks are not exclusive, order matters only for information and acting order. [I] Every team's first pick reveals its
archetype. Over the whole top 50 (window):

| first pick | n | later picks of the same team |
|---|---|---|
| Prism | 430 | Ve 0.95, Ma 0.82, Ho 0.76 |
| Vesper | 1,332 | Vd 0.86, Ho 0.73 |
| HoR | 4,512 | Ve 0.85, Ma 0.85, Ry 0.73, Vd 0.63 |

### 3.5 Drafts as rules over map features [M] + [I]

`map_table.py` searches, for each champion a team takes on some maps but not others, the best single map-feature threshold.
`permutation`: the best rule's accuracy against 300 label shuffles over the same maps and features.

| team | choice | best rule over map features | accuracy | permutation p |
|---|---|---|---|---|
| pbg, size 5 | Vendetta instead of Ryth | more than 7 elk camps on the map | 22/26 | 0.057 |
| pbg, size 5 | Ryth | (no clean rule) | 21/26 | 0.32 |
| pbg, size 4 | Ryth instead of Vendetta | map gems per clear < 459 (gemfight, interlock, reverse_spiral, rushbait, hooks vs rows, swirl, shortcut) | 8/8 | 0.35 |
| pbg, size 5 | no HoR (Vd + Ry) | map gold per clear > 4230 (boss_battle 7400, yellow_brick_road 4600) | 26/26 | (2 maps) |
| pbg, size 3 | Marcella instead of Vesper | biggest 3-map (the_farm: 50x40, 1096 gems) | 6/6 | (1 map) |
| ifish, size 5 | Varg instead of Ryth | spawn distance > 90 (ambush, expanse, big_world) + road_of_riches, islands | 24/26 | 0.12 |
| coo, size 5 | Tavi | map gems < 202 | 22/24 | 0.067 |
| coo, size 5 | Varg | camp HP > 26,700 | 21/24 | 0.31 |

[I] The per-map swaps look like per-map tuning, not a feature rule: no rule beats chance at p < 0.05 once the number of features
tried is accounted for. The robust structure is "fixed core + additions by team size". The one plausible mechanism is pbg's Vendetta
on elk-rich maps. Vendetta has 70 STR (+6 per shard) and resets every cooldown on any kill, camps included, so it farms 2,400-HP elk
quickly.

## 4. Role structure

### 4.1 Kits from the engine (experiments/results/probe_v3_0_4/champions_engine_3_0_4.txt) [M]

Basic attacks per 8 turns = 8, or 9 with an attack reset, times STR. A ranged champion must stand still to attack.

| champ | HP (+/shard) | STR (+) | FOC (+) | range | basic / 8 turns | spell (base) | stun | mobility | passive |
|---|---|---|---|---|---|---|---|---|---|
| Ryth | 1200 (+100) | 45 (+5) | 100 (+10) | 1 | 405 | area 100, radius 1 | area stun | - | +1% bonus HP as STR |
| Vesper | 1000 (+100) | 55 (+5) | 100 (+10) | 3 | 495 | - | - | dash 2 | **+33% gold** |
| Vendetta | 1000 (+100) | 70 (+6) | 100 (+10) | 1 | 630 | - | - | dash 2 | kill resets cooldowns (camps too) |
| Cassi / Issac | 600 / 900 | 30 / 40 | 70 (+13) / 100 | 3 / 1 | 240 / 360 | 140 single + stun (Cassi) | yes | dash (Issac) | linked death |
| Stellar | 650 (+65) | 30 (+3.5) | 70 (+7) | 3 | 240 | 140 single, 98 area | - | - | - |
| Prism | 700 (+60) | 35 (+2.5) | 80 (+8) | 3 | 280 | 120 + stun, 80 area | yes | - | **+1.5 FOC per carried gem** |
| Marcella | 1200 (+100) | 45 (+5) | 60 (+15) | 1 | 405 | 120 single, range 4 | enhanced attack | - | **stun immune; 2 gold per gem tributed** |
| Willow | 700 (+50) | 55 (+3) | 120 (+5) | 3 | 495 | heal 360 | - | - | - |
| Ren | 900 (+100) | 35 (+5) | 100 (+9) | 1 | 280 | 75 + stun | yes | dash 2 | retaliation 0.2 FOC |
| Varg | 1000 (+100) | 40 (+5) | 100 (+10) | 1 | 360 | shield 250 | - | - | splash = STR |
| Tavi | 900 (+75) | 45 (+5) | 110 (+10) | 3 | 405 | 154 + stun, range 4 | yes | - | buys shards anywhere |
| HoR | 1000 (+100) | 30 (+3.5) | 100 (+12) | 1 | 240 | dash landing 150 area + stun, shield 150 | area stun | dash 2 | up to +50% damage at low HP |

Reading [I]:

- Vesper is the only ranged kit with a gold passive, a dash and the best ranged basic damage: a natural gold sink and carry.
- Vendetta has the highest melee damage and a dash.
- HoR combines dash + area stun + shield (engage, frontline, channel cancel).
- Marcella is the only stun-immune body and turns banked gems into gold.
- Stellar and Cassi have 600-650 HP and no escape. Ren's stun damage was cut to 0.75 FOC in 3.0.4.

### 4.2 Measured roles per team (dumps, deduplicated per team) [M]

Shares are of the team's totals per game, averaged. bank = gems tributed; gold = gold from captures; dmg = damage dealt to
champions; taken = damage taken from champions; maxHP = final max HP (item investment); bag = time-averaged carried gems.

| team | champion: bank% / gold% / dmg% / taken% / deaths% / maxHP / bag |
|---|---|
| pbg (115, 71 W) | **Ve 33/38/32/29/13/5937/31**; **Ma 30/24/28/23/18/4136/22**; **Pr 17/22/24/9/17/2613/111**; Ho 16/12/12/29/27/3283/7; Vd 13/12/10/21/29/2500/11; Ry 8/7/12/19/23/1931/4 |
| ifish (107, 64 W) | **Ve 42/49/41/14/14/1568/41**; Vd 29/26/24/28/13/2877/16; Ho 17/15/13/25/11/3727/9; Va 14/14/3/13/9/1471/9; Ry 5/5/12/15/14/1900/3; Cas 5/4/10/9/28/932/3; Iss 5/4/3/15/28/1113/3 |
| pantheon (103, 51 W; both versions) | Ve 30/30/26/25/17/2455/8; Ma 30/23/22/27/13/2800/10; Ho 24/15/25/32/28/1993/8; **Pr 13/25/28/12/15/1700/88**; Wi 9/5/2/7/21/791/3 (0 kills) |
| coo (101, 55 W) | Vd 31/33/26/25/19/3016/20; Ve 29/33/40/24/20/3439/21; Ho 22/19/11/22/24/2070/11; Va 12/11/8/17/23/1642/10; Ry 11/10/17/19/19/1824/9 |
| cm (106, 58 W) | Vd 34/32/32/31/23/4168/11; Ve 24/27/21/18/21/3438/8; Ho 19/20/20/24/14/3400/9; Ma 18/14/16/21/18/3121/9; Ta 9/9/16/14/27/1634/7 |
| nyx (99, 48 W) | **Ve 46/50/24/21/10/5863/16**; Ma 19/16/21/22/21/3282/10; Vd 19/14/18/29/23/2940/9; Ho 13/12/21/27/31/1840/7; **Pr 11/15/25/15/21/2298/70** |

Role archetypes [I]:

- **Carry and banker:** Vesper in every team.
  - pbg and Nyx build it as a tank carry (~5,900 max HP).
  - ifish builds it as a glass cannon (1,568) that deals 41% of ifish's champion damage.
  - In coo and cm, Vendetta shares or leads the carry role.
- **Second banker:** Marcella (pbg 30%, Pantheon 30%); her passive pays 2 gold per tributed gem.
- **Bag battery:** Prism. It keeps 70-111 gems on average for focus and banks late (section 7).
- **Frontline:** HoR (22-32% of damage taken; 27-31% of deaths in pbg, Pantheon and Nyx) and Ryth (the most stuns: 16-28 a game).
- **Fodder / utility:**
  - C&I (ifish): each body banks 5%, each dies in 28% of team deaths, and the two die together.
  - Willow (Pantheon): pure heals, 2% of damage, 0 kills.
  - Tavi (cm): 9% bank, 27% of deaths.

## 5. Value of compositions on the ladder

### 5.1 The meta [M]

Pick rates over 3,987 top-50 games in the window (share of team-drafts): HoR 0.86, Vesper 0.84, Marcella 0.79, Ryth 0.64,
Vendetta 0.61, Willow 0.15, Varg 0.15, Tavi 0.13, Prism 0.12, C&I 0.08, Ren 0.08, Stellar 0.06.

The most common 5-champion comp, Ry/Ve/Vd/Ma/Ho, is 39% of all 5-champion team-drafts (2,049 of 5,204).

### 5.2 Logit models: P(side a wins) on rating difference and drafts [M]

`comp_value.py`. Champion effects are centred on the average champion (logit, ± SE).

| model | window (3,987 games, Oct 23) | Oct 22 07:00 - Oct 23 15:00 (14,097 games; ratings less contemporaneous) |
|---|---|---|
| M0 rating only | k = +0.72 ± 0.07 per 100; CV log loss 0.6773 | k = +0.37 ± 0.02; CV 0.6843 |
| M1 + champion picks | LR χ² 13.4, df 11, **p = 0.27**; CV 0.6789-0.6791 (worse) | χ² 54.1, p < 0.0001; CV 0.6833 (−0.001) |
| M1 effects | Willow +0.17±0.07, Varg +0.09±0.06, Vd +0.05±0.05, Ma +0.05±0.06, Ho +0.03±0.07, Ta 0.00, Ve −0.02±0.06, Ry −0.04±0.05, Pr −0.07±0.07, St −0.07±0.10, CI −0.08±0.09, **Re −0.12±0.09** | CI +0.11±0.04, Vd +0.09±0.03, Pr +0.05±0.04, Wi +0.05±0.04, Ve +0.04±0.03, Va +0.03±0.03, Ho 0.00, Ma −0.02, Ry −0.05±0.03, Ta −0.05±0.04, **Re −0.10±0.04, St −0.15±0.05** |
| M2 + engine role counts | χ² 13.0, p = 0.22; CV 0.6787 | χ² 53.0; CV 0.6832 (shield +0.15, stun +0.11, gold +0.13 per pick) |
| M4 team fixed effects + picks (within-team variation only) | Wi +0.21, Va +0.12, Ta +0.10, Vd +0.08, Ho +0.03, Ve 0, Ma 0, Ry −0.05, St −0.05, CI −0.05, **Re −0.18, Pr −0.19** | Wi +0.12, Va +0.11, Vd +0.10, Ma +0.09, CI +0.07, Ve +0.06, Ta +0.03, Pr +0.01, Ry −0.03, Ho −0.13, **St −0.15, Re −0.29** |
| top-21 teams only (rating ≥ 2000, 1,337 games) | χ² 13.7, p = 0.25; Varg +0.50±0.19, Ma +0.23±0.12, ... St −0.29±0.21, Re −0.36±0.29 | - |

Pairs over the larger set: Ve+Vd+HoR +0.08 ± 0.03 (z 3.0) and Pr+Ve+Ma +0.15 ± 0.05 (z 2.9). Over the window, both are 0.00.

[I] Conditional on rating, the draft explains almost nothing among top teams. Each team's draft is nearly fixed, so its value is
already inside its rating. The within-team (M4) and natural-experiment views (3.3) agree that effects are about ±0.1 logit, except
two picks:

- **Ren: −0.10 to −0.29 logit.** Negative in every model and subset.
- **Stellar: −0.07 to −0.29 logit.** Also −0.34 ± 0.13 against Ve+Vd+HoR comps (z −2.6) and −0.87 ± 0.39 against the ifish archetype.

The earlier conclusion in AGENTS.md section 7 ("the draft is not the gap") still holds for the meta picks.

### 5.3 Team size changes everything: rating predictiveness [M]

`comp_matrix.py`. The favourite is the team rated at least 50 points higher.

| size | window: games, slope per 100, favourite wins | all data (deduplicated): games, slope, favourite wins |
|---|---|---|
| 3 | 576, **+0.44 ± 0.16**, 0.600 | 1,959, **+0.10 ± 0.06**, 0.535 |
| 4 | 809, +1.09 ± 0.16, 0.658 | 2,576, +0.54 ± 0.06, 0.610 |
| 5 | 2,602, +0.69 ± 0.08, 0.639 | 8,320, +0.35 ± 0.03, 0.591 |

Per map (all data, deduplicated, games with a rating gap of at least 100, n = 41-73 each):

- Favourites win less than 50% on big_world 0.39, the_farm 0.43, starvation 0.43, fracture 0.45, gold_rush 0.45 and broken_curve 0.48.
- They win most on gemfight 0.89, elkring 0.82, monolith 0.75, lost_world 0.75, corners 0.74 and shortcut 0.73.

Size-specific champion effects (all data, M1 per size):

- **Size 3:** Vendetta +0.28 ± 0.07, Varg +0.23 ± 0.12, Tavi +0.23 ± 0.11, Vesper +0.17 ± 0.08, HoR +0.13, Ryth +0.14, Marcella +0.11,
  Prism −0.02, C&I −0.15, Ren −0.16, Stellar −0.22, Willow −0.73 ± 0.49.
- **Size 4:** C&I +0.32 ± 0.11, Vesper +0.14 ± 0.06, ..., **HoR −0.14 ± 0.07**, Tavi −0.18, Stellar −0.25.
- **Size 5:** Vendetta +0.11, C&I +0.10, Prism +0.09, HoR +0.08, Willow +0.08, ..., Ren −0.17 ± 0.05, Stellar −0.12.

[I] pbg and Pantheon drop HoR on 4-champion maps, and pbg is the strongest team there (5.6). That agrees with HoR's size-4 effect,
but z is only about 2.

### 5.4 Flex picks on top of the core [M]

`flex_slot.py`: rating-adjusted excess wins of the remaining picks, given the core.

- **Size 5, core Ve/Vd/Ma/Ho** (all data): +Ry 6,119 team-games, −3 (z −0.1); +Pr 570, +21 (z 1.8); +Wi 191, +9 (z 1.3);
  +Va 371, +7 (z 0.7); +Ta 194, −5. Window: +Ry +8 (z 0.3), +Pr +7 (z 0.8).
- **Size 4, core Ve/Ma/Ho:**
  - +Ry 1,656, +11 (z 0.5); +Vd 414, −9 (z −0.9); +Va 97, +9 (z 1.9).
  - Without HoR: Ry/Ve/Vd/Ma +8 (z 1.1) and Ry/Ve/Pr/Ma +17 (z 2.2).
  - Without Vesper: Ry/Vd/Ma/Ho −20 (z −2.4).
- **Size 3, core Ve/Ho:** +Vd 903, +27 (z 1.8); +Ma 903, −8; +Ry 208, +12 (z 1.7); +Pr 182, −4; +Va 130, +9 (z 1.6); +Re 20, −7 (z −3.1).

### 5.5 Our old draft (g8: Ren / Stellar / C&I / Varg / Ryth; ranked at Oct 23 15:00 as Ry/St/Re/Va/Ho) [M] + [I]

- [M] Our ranked record:
  - Meta-like drafts (Ry/Ve/Vd/Ma/Ho or Ry/Ve/Vd/Va/Ho): 221/455 (48.6%) on Oct 22 and 106/235 on Oct 23.
  - The g8 draft: 8/25 (32%) at 15:00.
  - The bot also changed between these games, so this is not a draft comparison.
- [I] Summing the champion effects (5.2), g8's draft is worse than Ve/Vd/Ma/Ho/Ry by +0.22 logit (all-data M1), +0.29 (window M1)
  and +0.38 (all-data M4). That is about +5 to +9 percentage points at even odds, or 30-50 rating points.

### 5.6 Head-to-head between the study teams (since Oct 22 18:00) [M]

| row vs column | pbg | ifish | pantheon |
|---|---|---|---|
| pbg | - | 38-27 | 35-25 |
| ifish | 27-38 | - | 30-20 |
| pantheon | 25-35 | 20-30 | - |

- By team size, pbg vs ifish + Pantheon is 13-7 on size 3, **24-7 on size 4** and 36-38 on size 5. ifish vs Pantheon: 2-4, 6-2, 22-14.
- coo, cm and Nyx (window): cm–coo 6-4, Nyx–cm 4-1, coo–Nyx 3-2. They did not meet the top three in the window.
- The outcome of the same pairing on the same map changes with sides and versions: pbg vs ifish on fragment went W, W, L in the window.
  Per-map head-to-heads of 1-3 games say little.

## 6. Prism-bank teams in detail (pbg, Pantheon, Nyx)

[M] Prism's tribute behaviour (`tributes.mjs`, deduplicated per team; a tribute attempt fails if no bank follows within
ceil(bag/10)+3 rounds):

| champion | starts | completed | mean bag at start | why failed (lock / stun / death / other) | failed gems |
|---|---|---|---|---|---|
| pbg Prism | 100 | **51%** | **408** | 13 / 8 / 4 / 24 | **27,887** |
| Pantheon Prism | 71 | 75% | 291 | 1 / 3 / 6 / 8 | 7,228 |
| Nyx Prism | 91 | 62% | 186 | 5 / 6 / 2 / 22 | 8,791 |
| Prism of the study teams' opponents | 2-41 | 61-100% | 171-435 | - | - |
| every other champion of every study team | 12-950 | 92-100% | 14-65 | - | - |
| coo's Prism (non-hoarding) | 17 | 94% | 28 | - | - |

"Other" includes channels still running when the game ended (7 of pbg's 24) and channels abandoned by the bot.

[M] The Prism decides the game:

| team | Prism banked a game, wins vs losses | Prism bag lost a game, W vs L | Prism deaths a game, W vs L |
|---|---|---|---|
| pbg | 299 (71) vs **0** (44) | 44 vs 67 | 1.0 vs 2.5 |
| Pantheon | 264 (51) vs 5 (52) | 97 vs 125 | 0.8 vs 1.8 |
| Nyx | 172 (48) vs 32 (51) | 39 vs 100 | 0.9 vs 3.0 |

[M] Who kills Prism carriers (all 577 unique games, Prism deaths with a bag of 30 or more: 191 deaths, 26,903 gems):

| killer | kills | gems | per game in which an enemy Prism faced it |
|---|---|---|---|
| Vesper | 57 | 9,084 | 0.16 (24.9 gems) |
| Marcella | 40 | 7,040 | 0.14 (25.0 gems) |
| camps (gems destroyed) | 30 | 3,935 | - |
| HoR | 25 | 2,854 | 0.07 (8.0) |
| Vendetta | 24 | 2,603 | 0.10 (11.1) |
| Ryth | 3 | 316 | 0.015 (1.5) |

Overall, Prism bodies hold 83.5 gems on average while alive, with a mean per-game maximum of 229 (398 Prism bodies).

Replay references [M]:

- **`t2/pbg/00great_wall_3a46ed8d`** (ifish 1013 - pbg 699). pbg's Prism starts tributes at r882 (368 gems), r988 (623) and r1069
  (623) at altar (17,19).
  - ifish cancels them with altar locks: HoR r904, Vesper r1017, HoR r1077 plus a HoR stun r1077.
  - The Prism then dies to a camp at r1104 holding 623 gems.
- **`t2/pbg/00monolith_e2542db9`** (:3 1013 - pbg 597). pbg's Prism tries to bank 576 gems at r898, r930 and r993.
  - :3's Vesper locks its altar at r962.
  - :3's Prism and Marcella stun it at r1036-1037, and :3's Marcella kills it at r1038, taking the 576 gems.
- **`t2/pbg/00quadrants_46848e89`** (pbg 1180 - :3 802). pbg's Prism banks **796 gems in one 80-turn channel**, r401-481, at
  altar (1,22). :3's locks went to the other altar (22,43). The bomb lands and wins.
- **`t2/pbg/00lost_world_3209a6ec`** (Pantheon 1008 - pbg 0 at r509; same comp on both sides).
  - Pantheon tributes 7-35 gem bags from r44 on.
  - pbg never completes a tribute. Its Prism, Vesper and Marcella die early (Prism killed r26 and r121).
  - The second game, **`_b74302c8`**, ends 1001-0 at r489.
- **`t2/pbg/00collision_5818f117` = `_75b04c87`** (policy wonk Ma/Ve/Ta 1006 - pbg 536, identical replays). pbg's Prism never
  tributes and dies once with 106 gems. Policy wonk's Marcella banks 628 gems with 8,500 max HP.

[I] Altar behaviour seen from the draft side:

- pbg and Nyx place **no altar locks at all**. Their opponents place 2.2 and 1.9 a game.
- ifish places 2.8, Pantheon 4.2, cm 5.6 and coo 1.1 a game.
- So a Prism team cannot guard its own 20-80-turn channel with a lock.
- See an_fights.md §4 and an_items.md §3.1 / §4.7 for the fight and item side of the same pattern.

## 7. What beats prism best girl's Prism / Vesper / Marcella core

- **Rating-adjusted results** (415 games since Oct 22 18:00, k = 0.72) [M]:
  - Opponents win 36.9% against 32.8% expected.
  - Size 3: **36 of 64** (expected 21.3; 30.4 even with the flattest slope 0.10). Size 4: 19 of 88 (28.9 expected). Size 5: 98 of 263 (85.9).
  - Opponents with Vendetta: +16.0 excess wins in 255 games (0.9 without). With Varg: −3.5 in 38.
  - Ve+Vd+HoR archetype: +12.0 in 175 games (procless, ifish, new team(4), print dont int).
- **On 3-champion maps** [M]:
  - pbg lost to :3 (Ve/Vd/Ta) 1-7, policy wonk (Ma/Ve/Ta) 1-7 and procless (Ve/Vd/Ho) 3-10.
  - It beat Pantheon (Pr/Ve/Ho) 7-3 and ifish (Ve/Ho/Vd) 6-4.
  - In its 17 unique 3-champion dump games pbg won 8. Its Prism banked 213 a game and lost 63 a game to deaths.
  - [I] pbg's 3-comp Pr/Ve/Ho has only one ordinary banker (Vesper) next to the Prism battery.
- **Counter-picks against Prism comps** [M]: `counters.py`, rating offset, Prism side vs non-Prism side; 750 window games, 1,204 in
  all data.
  - No pick of the other side is significant.
  - Window: Marcella +0.28 ± 0.18, Ren +0.34 ± 0.30, Willow +0.23, Tavi +0.20, Vendetta −0.31 ± 0.16, Ryth −0.25, HoR −0.29.
  - All data, Prism-bank archetype: HoR +0.21 ± 0.17, Prism +0.22, C&I +0.15, Ryth −0.22 ± 0.13.
- **Conclusion** [I]: no composition beats pbg by itself. What beats it is:
  1. Denying the Prism bank. Kill the Prism (Vesper or Marcella dives; Marcella ignores its stun), lock or stun its long channel,
     and lure it into camps. This takes its win condition: in all 44 of pbg's dump losses the Prism banked nothing.
  2. Winning the race before the bomb by banking small bags often.
  3. Taking 3-champion maps, where pbg loses more than half its games.
  - pbg is strongest on 4-champion maps (Pr/Ve/Ma + Ry/Vd, no HoR). Expect to lose most of those.

## 8. What beats Intercontinental Fish's Vesper / Vendetta / HoR / C&I core

- **Rating-adjusted results** (715 games since Oct 22 08:00) [M]:
  - Opponents win 33.1% against 38.8% expected; ifish is still under-rated.
  - Size 3: **33 of 58** (expected 23.6-28.2). Size 4: 20 of 74 (29.2 expected). Size 5: 109 of 283 (110.5 expected).
- **On 3-champion maps** [M]: :3's Ve/Vd/Ta beat ifish **9-0**, policy wonk's Ma/Ve/Ta 5-3, pbg 6-3, Pantheon 4-2 and
  new team(4) 4-1. ifish beat procless 6-4 and Univardisty 6-0.
  Examples:
  - **`t2/ifish/01broken_curve_34bbc10b`** (:3 1020 - ifish 445, r671): ifish's Vesper dies holding 270 gems, and :3's Vesper
    banks 657.
  - **`t2/ifish/00packs_3600bc34`** (:3 1024 - ifish 806): ifish's Vesper (1,600 max HP) dies 4 times against :3's 6,600-HP Vesper.
- **The single carry** [M]:
  - ifish's Vesper: 42% of bank, 49% of capture gold, 41% of champion damage, 1,568 max HP.
  - In ifish's wins it dies 0.7 times a game, loses 12 gems and banks 445. In losses: 3.4 deaths, 248 gems lost, 248 banked.
  - It is the most-killed carrier of the ifish team (37 deaths with a bag of 30+, 10,990 gems), killed mostly by Vesper (13), camps (8),
    Marcella (8) and Prism (6, 4,769 gems).
- **C&I** [M]: Cassi (932 final max HP) and Issac each account for 28% of ifish deaths, 3.7 a game (they die together), and each
  banks 5%.
- **Counter-picks against the ifish archetype** [M] (all data, 1,136 games):
  - Stellar −0.87 ± 0.39, Ryth −0.25 ± 0.13, Marcella −0.28 ± 0.14, C&I −0.54 ± 0.32. Prism +0.24 ± 0.16 and Tavi +0.10 lead.
  - Against Ve+Vd+HoR in general (window, 1,882 games): Vendetta +0.23 ± 0.10 (z 2.2), Stellar −0.34 ± 0.13 (z −2.6).
- **Conclusion** [I]:
  1. Focus the glass Vesper. It carries 33-52 gems on average and dies in 25% of ifish's deaths in losses.
  2. Kill Cassi, the 600-930 HP body, to remove two bodies.
  3. Take 3-champion maps with a durable Vesper + Vendetta / Marcella + Tavi comp.
  4. Don't draft fragile casters (Stellar) against its Ve/Vd/HoR dive.

## 9. Rules for god2

These are rules over runtime state (engine designs, team size, the opponent's revealed picks, visible gem counts). Thresholds come from
the data above. **D** = draft rules, **P** = in-game rules the composition depends on.

**D1. Fill role slots from engine stats, in this order, truncated to the team size.** Each slot takes the best-scoring champion not
yet picked. Per-shard growth counts 5 shards ahead (+5g). Attacks per 8 turns = 9 with an attack reset, else 8.

| slot | score (from champion_designs and kit flags) | patch 3.0.4 result |
|---|---|---|
| 1 carry | ranged only: (STR + 5g_STR) × attacks per 8 turns × (1 + gold bonus) × (1.5 if dash) | Vesper 1436; next Willow / Tavi 630 |
| 2 front | melee only: (HP + 5g_HP) × (1.3 if dash) × (1.3 if area stun) + shield | HoR 2685; then Ryth 2210, Vendetta 1950, Ren 1820 |
| 3 melee DPS (size ≥ 3) | melee only: (STR + 5g_STR) × attacks × (1.3 if dash) | Vendetta 1170; Issac 643, Ryth 630 |
| 4 banker / anti-stun (size ≥ 4) | stun immunity or a tribute-gold passive, then HP | Marcella |
| 5 utility (size 5) | area stun, then HP | Ryth |

- This gives Ve/Ho/Vd, Ve/Ho/Vd/Ma and Ve/Ho/Vd/Ma/Ry. Those are the ifish/cm cores plus the top-50 standard 5-champion comp.
- If a patch changes stats or kits, the picks move with it.
- Pick order = slot order. Picks are not exclusive, so order only sets our acting order and what the opponent can read.
- The kit flags (gold bonus, stun immunity, tribute gold) are the champions' passives from the rules. They are the only
  per-champion constants needed; everything else comes from `champion_designs` at runtime.

**D2. Two exclusion rules.**

- Never fill a slot with a champion whose base HP is below 700 and that has no dash, heal or shield. That means Stellar (650) and
  Cassi (600, linked to Issac).
- Exclude any champion whose rating-adjusted effect is negative in every ladder fit. Refit after each patch with
  `tools/top2/draft/comp_value.py`. On 3.0.4 that is Ren and Stellar (−0.10 to −0.29 logit), and dropping them came with +66 to +128
  performance points for three study teams.
- Only a local A/B result may override either rule; a hand-coded preference may not.

**D3. Team size is the only map feature the draft uses by default.** The top teams' per-map swaps are not reproducible from map
features (permutation p ≥ 0.06), and the flex slot is worth about ±0.1 logit. Optional A/B variants, decided only by local paired
tests (games are deterministic per bot pair, map and side):

- Size 4 without HoR (Ve/Ma/Vd/Ry; HoR's size-4 effect −0.14 ± 0.07; pbg and Pantheon both drop HoR at size 4).
- Size 3 Ve/Vd/Ta (:3's comp, 16-1 against pbg + ifish; Tavi's size-3 effect +0.23 ± 0.11).
- Vendetta instead of Ryth in slot 5 when the map has more than 7 elk camps (pbg's only near-significant rule, p = 0.057).

**D4. Read the opponent's archetype from its revealed picks and write it to draft memory (3 bits).** The comp itself does not
change; only the in-game plan does.

| bit | set when | why |
|---|---|---|
| ENEMY_PRISM_BANK | the enemy has Prism | P(Vesper) 0.95, P(Marcella) 0.82 with it; pbg, Pantheon, Nyx, :3 |
| ENEMY_VESPER_CARRY | the enemy's first pick is Vesper, or the enemy has Vesper + Vendetta | ifish, cm, procless |
| ENEMY_LINKED | the enemy has C&I | Cassi is the cheap kill that removes two bodies |

**P1. Prism bag priority** (ENEMY_PRISM_BANK).

- Target value of any visible enemy = 100 gold + its `gem_count()`.
- Make an enemy Prism with gem_count ≥ 60 the focus target of every body within 6 tiles that can reach it. This holds when we have
  at least 2 bodies there and the Prism has at most 1 ally within 3.
- Marcella first: she is immune to its stun-nuke. Then Vesper and Vendetta.
- Prism bodies average 83.5 gems while alive (mean per-game max 229).

**P2. Channel denial.** When a visible enemy starts a tribute with bag B ≥ 60 (ceil(B/10) ≥ 6 turns), send the nearest body that can
do one of the following within ceil(B/10) − 1 turns:

- (a) place an altar lock (within 2 tiles of the altar);
- (b) stun the channeler: HoR dash landing (reach 2 + radius 1), Ryth area stun (range 4), Marcella enhanced attack, Prism / Cassi /
  Tavi stun (range 4).

Damage alone does not cancel. pbg's Prism completes only 51% of its average 408-gem tributes, and locks / stuns account for 21 of
the 49 failures.

**P3. Always carry an altar lock** on at least one living body from about r100 on (10 gold, one per body). pbg and Nyx never lock,
so they cannot answer ours. ifish (2.8 a game) and Pantheon (4.2) do.

**P4. Vesper carry** (ours and theirs).

- Funnel captures, tributes and gold to our Vesper. Top teams give it 27-50% of capture gold and 24-46% of banks.
- Build it durable, like pbg and Nyx (5,900 max HP). ifish's 1,568-HP Vesper dies 3.4 times a game in its losses.
- With ENEMY_VESPER_CARRY, the enemy Vesper is the focus target when it is within dash + 3 of two of our bodies. ifish's Vesper
  loses 248 gems a game in ifish's losses.

**P5. Bank small and often unless we run a Prism.**

- Non-Prism bankers of every top team start tributes at 14-65 gems on average and complete 92-100%.
- Against Prism-bank teams the race is won before the bomb (lost_world 1008-0 at r509 and 1001-0 at r489).

**P6. Test where upsets happen.** Prioritise local tuning and A/B time for the 6 three-champion maps.

- pbg and ifish lose 56-57% of their games there.
- Rating barely predicts results there: slope 0.10-0.44 per 100 points, against 0.35-1.09 at size 4-5.
- The next most random maps for favourites are big_world, the_farm, starvation, fracture, gold_rush and broken_curve.

**P7. Kill C&I through Cassi** (ENEMY_LINKED): with 600 base HP and 932 final max HP, she is the cheapest kill that removes two bodies
and both bags.

## 10. Reproduce

```
export PYTHONIOENCODING=utf-8 CAMBC_CACHE="C:/Users/Anjali Gupta/AppData/Local/cambc/assets"
python tools/top2/draft/team_drafts.py [--team pbg]                         # drafts per map, determinism, history
python tools/top2/draft/reactivity.py [--team cm] [--since ISO]               # side / opponent dependence
python tools/top2/draft/map_table.py --md | python tools/top2/draft/map_table.py   # table 3.1 / rule search
python tools/top2/draft/comp_value.py [--which all --since 2026-10-22T07:00]  # logit models M0-M4
python tools/top2/draft/comp_matrix.py [--which all --since 2026-10-22T07:00 --dedup]
python tools/top2/draft/flex_slot.py [--which all --since 2026-10-22T07:00 --dedup]
python tools/top2/draft/counters.py --arch prism|prismbank|ifish|vevdho [--firstpick]
python tools/top2/draft/vs_team.py --team pbg --since 2026-10-22T18:00 ; python tools/top2/draft/vs_team.py --h2h --since 2026-10-22T18:00
node tools/top2/draft/roles.mjs pbg ifish pantheon coo cm nyx > experiments/top2/draft_roles.jsonl
python tools/top2/draft/roles_agg.py experiments/top2/draft_roles.jsonl [--team pbg --split]
python tools/top2/draft/carrier_kills.py experiments/top2/draft_roles.jsonl
node tools/top2/draft/tributes.mjs pbg ifish pantheon coo cm nyx > experiments/top2/draft_tributes.jsonl
```
