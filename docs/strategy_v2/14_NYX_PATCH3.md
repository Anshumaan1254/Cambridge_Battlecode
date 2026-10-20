# 14. Nyx after patch 3.0 (20 Oct 2026, session 14): what the 20 games show and what GOD v3 / v4 changed

Input: the user's two zips (4 match groups, 20 games, we are side A in all; Nyx won 17). Replays `experiments/nyx_oct20/{new,old}/`,
index `experiments/nyx_oct20/index.json` (map file name per game), analysis `experiments/nyx_oct20/analysis/` (report.md and CSVs from
`tools/strategy_v2/run_all.py`, `stalls_us.txt` from `stuck_eps.py`, `group_kills_by_team.txt` from `killers.py`). Maps: `maps/nyx_new`
(10 new maps) and `maps/comp30` (10 changed official maps, `*_v3`). Every number below is from those files.

## 1. Results

| Pool | Games | Wins | Typical loss |
|---|---|---|---|
| new maps (`nx*`) | 10 | 1 (nx31x31_c3, 1174-286) | 115-1000 (nx60x60, r757), 0-1012 (nx31x31_c4, 45 deaths), 72-1008 (nx50x50, caster draft), 0-0 at r2000 on gold (nx50x41) |
| changed official maps (`*_v3`) | 10 | 2 (expanse 1010-883, eight 1016-311) | 74-1012 (fragment, 3 champions), 0-400 at r2000 (contest, 54 deaths), 297-1026 (interlock) |

Drafts: Nyx = Ren, Stellar, C&I, Ryth, Varg (the old ifish table; Ren, Stellar, C&I at 3; + Ryth at 4) on 17 maps, Varg, Vendetta, C&I,
Willow, Ryth on 3. On 5-champion maps our five champions are the same; we still lost by 300-1,000 gems.

## 2. Where the gems go (20 games, us / Nyx)

| | Us | Nyx |
|---|---|---|
| camp gems collected | 10,740 | 24,203 |
| gold earned | 86,615 | 237,299 |
| captures (home / neutral / enemy side) | 492 (412 / 69 / 11) | 1,160 (891 / 173 / 96) |
| time on camps (share of alive body-rounds) | 15.5% | 20.5% |
| camp damage per camp round | 89 | 144 |
| idle body-rounds | 8.3% | 3.3% |
| body deaths | 333 | 271 |
| recalls (median health at start, overlapping a capture) | 1,136 (0.42, 341) | 1,752 (0.70, 788) |
| gold spent on items; Power-dmg emblems | 82,710; 0 | 226,140; **1,097** |
| damage-stat points per 1,000 gold | 21.6 | 33.6 |

Camp-group kills, first hit to kill (count, median rounds): 2 gold clusters 149 (13.9) vs **538 (8.1)**; 4 gold 25 vs 101; 1 gold + 1 wolf
61 (211) vs 163 (84); 1 elk + 1 gem 23 (167) vs 66 (116); 2 elk + 2 gold 8 vs 42 (72). Bodies per kill are the same (1.2-3.5): the gap
is damage and commitment. Unopposed, GOD v2 takes 113-125 rounds from first hit to kill on elk groups too (chip, leave, come back).

Their captures per 100 rounds grow from 55 (r0-100) to 106 (r700-800); ours stay at 36-54: the Power snowball (gold -> damage -> gold).
Nyx's builds: Treasure first on every body (Stellar / Cassi TfE at r46-180, Ren ThE, Issac TsE, Varg ThE), then Jungle in the damage
stat (casters) or Bruiser health (melee), Durability, then Power in the damage stat for ever; their Stellar ends with 20-27 Power emblems.

## 3. Where the deaths come from

- 51% of our deaths are bursts from >= 60% health 3-4 rounds before (theirs 33%); 49% by ranged champions (their Stellar 79 kills, Cassi 49).
  At our champion deaths the enemy had 1.6x our local health (median) and we were outnumbered only 16% of the time (they: 32%): a single
  Power-stacked caster kills a body of ours.
- Fights by who hits first (`engagements.csv`): on our own half when **they** open: 200 fights, deaths 80-10, damage 27k-143k; when we open
  on their half: 31-81. Openers win 3:1 either way; their openers on our half are the single worst item.
- Three hard stalls decided three games (both reproduce locally): the altar behind a monolith tile on nx50x41 (six bodies 1,000+ rounds),
  a chained hole crossing on nx61x71 (Ren 1,197 rounds), the hole maze on nx60x60 (Ren and Issac ~400 rounds each).

## 4. What was built (all switches in `bots/god/src/params.h`, patch `experiments/wip/x_g5.patch`) and what it measured

Pool for every A/B: the 20 Nyx maps x 2 sides = 40 games per opponent (`tools/ledger.py`, `experiments/results/ledger_v3/`).

| Change | h2h vs GOD v2 | Notes |
|---|---|---|
| `altar_no_camp` 1 + `no_altar_gold` (camp tiles are never altar approach tiles; a map without a usable altar is played for gold earned and kills) | 23/40 | nx50x41: 44,035 gold vs 2,994 (`legend_m15`) |
| `dash_gain1` + `stall_guard` 10 (a dash that gains one step at a chained crossing; any stalled walking task drops its target and its hole routing) | 24/40 | nx61x71: no stall left |
| `pd_obj_heavy` (the draft's objective map needs a heavy lone gem group) | 19/40 alone | kept: nx50x50 is not an objective map |
| **GOD v3** = the three above | **25/40**, vs `legend_m15` 27, `_mite` 35, `_ifish` 31, `_px9` 30 | shipped 13:05 UTC |
| `altar_no_camp` 2 (the camp-blocked altar opens when the camp is dead; the blocking group is a team target) | 25/40, nx50x41 **1092-0, 1054-0** | **GOD v4**, shipped 13:40 UTC: vs `legend_m15` 30/40, pace 1034 |
| Nyx's builds (`build_style` 12) / Treasure-first hybrid (13) / Power-late hybrid (14) | 16 / 19 / 18 | worse inside our brain (early brawls lost, then kill gold snowballs against us) |
| recall at 0.70 health (`home_hp` 0.6, `cap_recall_hp` 0.7) | 15 | worse |
| C&I instead of Heart of Ruin at 3 champions (`pd_hor3` 0) | 18 | non-transitive: Nyx's C&I beat our HoR 3 of 4 on the ladder, `_g4`'s HoR beats C&I locally |
| `elk_exposure`, `gold_value` 0.5 / 0.22 | 21, 19 / 22 | no |

## 5. What is left (in order)

1. The fights on our own half when a Power-stacked caster opens (80 deaths to 10): a danger model retrained on these games (in progress),
   `burst_retreat`, or an explicit "a visible caster whose one cast takes half our health: keep two more tiles" rule.
2. The economy snowball: Nyx's builds need Nyx's execution; a build that converts late gold into damage without losing the early brawls.
3. Lone monoliths as team targets on any map (`mono_team`): 7 of the 20 maps have one (200 gems + 300 gold a kill, 20,000 health, range 5).
4. Farming commitment on elk groups (first hit to kill 113-125 rounds unopposed): `commit_hit`, `max_trips`, `join_reach` variants.
