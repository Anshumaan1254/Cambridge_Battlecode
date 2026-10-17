# x_gold: tiebreak-aware economy for gem-scarce maps (agent `gold`, 2026-10-17)

Bot copy: `bots/_x_gold2` (local; rebased on the new legend = `_f1`). Patch: `experiments/wip/x_gold.patch`
(against the current `bots/legend/src`, applies cleanly).
Status: **done. Recommendation: do not merge as a behaviour change** (neutral vs `_f1`, see Results). The scarcity
detector, test maps and tools are worth keeping.

## Engine facts measured
- Tiebreak order (strings in the cambc 2.2.5 binary): round limit reached, then more banked gems, then
  "tied on gems, more gold earned", then "tied on gems and gold, more kills", then "team B wins ties".
- earnedGold (match statistics, per champion) = every gold gain: capture rewards and 50 per kill, both
  with the Treasure / Vesper +20% bonus (replay check on packs: Stellar 2,978 = 2,388 capture gold + 10 kills
  at 50-60). Spending does not reduce it. Assists 0, passive income 0.
- Camp group rewards (read from the engine's map API, `/tmp/gold/scratch/groups.mjs` method, now in the
  notes below): gem cluster 24 gems / 0 gold / respawn 50; gold cluster 0 / 35 / 50; wolf 22 / 90 / 40;
  elk 36 / 160 / 60; monolith 200 / 300 / 150. Multi-camp groups add up (3 gold clusters = 105 gold), with
  some engine bonus on mixed monolith groups (M+g = 448 gems / 600 gold; M+E = 236 / 460; M+E+E = 272 / 620).
- Theoretical non-monolith gem supply per side (sum of gems / respawn over our half): 45-map panel 2.5-17.8
  gems per round, except the monolith-only ladder map lad_50x50_R_c5_65bb75 (0; its two monoliths give
  1.33 per side). Legend banks about 0.27-0.39 of that rate (finish rounds on the panel).

## Test maps (`maps/gold/`, generator `tools/mapgen/goldmaps.mjs`, seed 7)
| Map | Gem sources per side | Champs |
|---|---|---|
| gold_mono_30x30_V_c3, gold_mono_36x36_R_c3, gold_mono_48x48_H_c4, gold_mono_64x64_V_c5 | 1 monolith | 3-5 |
| gold_monoelk_56x56_R_c5 | monolith + 1 elk | 5 |
| gold_monowolf_72x72_V_c5 | monolith + 1 wolf | 5 |
| gold_monoelk2_80x80_H_c5 | monolith + elk pair | 5 |
| gold_elk_44x44_R_c4 | 1 elk | 4 |
| gold_elkwolf_60x60_H_c4 | 1 elk + 1 wolf (centre) | 4 |
| gold_monoEE_40x40_R_c3, gold_monoE_52x52_H_c4, gold_monoEE_68x68_V_c5 | one fused monolith+elk(s) group | 3-5 |
| ctrl_scarce_50x50_R_c4, ctrl_scarce_58x58_V_c5 (controls) | 2 gem clusters + wolves/elk (+ monolith) | 4-5 |
Gold clusters everywhere (singles, pairs, triples).

## Baseline: `_L0` (legend) on the gold maps (both sides, 14 maps = 28 games per opponent)
- Games still mostly end by someone reaching 1000 gems (r1100-1990): the side that wins the early fights
  snowballs (kill gold -> items), then farms both monoliths/elks. Round-limit finishes: mirror 4/28.
- First monolith capture is late (r780-1200): one body must be able to solo it within 5 heal trips before it
  claims it (`group_score` plan), then others join.
- vs `_r2` 23/28, `_v6` 25/28, `_hunt2` 26/28, `_devci` 22/28 (mean 85.7%). Tiebreak games seen: vs `_v6`
  gold_mono_48x48 B lost 600-600 on gold (8,452 vs 8,796); several 200-800 gem round-limit results.

## Changes (all behind `params.h` switches, `tb_*`; only active when the map is detected scarce)
- **Scarcity detector** (`detect_scarcity`, init): our half's non-monolith gem supply (sum gems/respawn) x `tb_eff` 0.3
  x max_rounds < winning_gems. Checked with a GOLD_TRACE build on all 56 pool maps (`maps/*`, ladder, the 17 real comp
  maps): **on only for `contest` and its ladder copy `lad_50x50_R_c5_65bb75`** (monolith + gold only). `monolith`,
  `rows`, `elkring` are not scarce (non-monolith supply 5.6, 5.0, 3.0 gems/round; legend finishes them by gems).
  On `maps/gold` all 12 gold layouts trigger except `gold_elkwolf` (centre camps count for both sides: 1.70, borderline);
  both controls stay off. Games on non-triggering maps were byte-identical to the baseline (deterministic check).
- **Dynamic check** (`tb_dyn_from` 1300, `tb_dyn_frac` 0.9): neither team's projected bank reaches 900 by r2000 ->
  tiebreak game (endgame logic only).
- In scarce mode: `gold_v` = `tb_gold_value` (no end-of-game gold discount: earned gold is the tiebreaker);
  `tb_tribute_min` 1 (moot since the route patch's `bank_min`); `tb_bag_caution` 20; enemy carriers with
  >= `tb_hunt_bag` 30 gems posted as opportunities; stepping on an enemy gem capture x`tb_deny_mult` 3.
- `tb_treasure`: Treasure emblem first.
- `tb_endgame` 250: last rounds of a tiebreak game: ahead on gems -> safer fights, stay home; behind -> all-in for gems
  (gold value 0.05, lower fight margins, more deny/steal).
- `tb_safe_bag` 100 / `tb_safe_quiet` 25: a big bag (monolith 200) waits on spawn until we outnumber them or the altar
  has been quiet 25 rounds (traced: on `contest` vs `_v6` two 200-gem bags died at the central altar).
- `tb_mono_team` (**default 0**): team monolith call. Body 0 decides from one estimate (team damage, team health above
  each retreat line, <= 1 + `tb_mono_trips` rotations, not outnumbered, not in the last 90 rounds) and broadcasts bit 7
  of shared-memory byte 2 (free); bodies gather at range 4 and wake it when 60% of the team is there. First version
  (team plan inside `group_score`) sent ranged bodies to wait alone at both monoliths from r1 (it assumed a melee
  tank): 28.6% vs `_L0`. The call version: feasible from ~r300, but the gathered team is picked off; see Results.

## Results (bench.py, both sides; scarce pool = `maps/gold/gold_*` + `maps/gold2/*` + `maps/comp/contest`, 37 maps, 74 games)
| Variant (on new legend) | vs `_f1` | gems | gold earned | deaths |
|---|---|---|---|---|
| a: all on, team monolith call | **35.1%** | 37,978-55,334 | 450,602-558,469 | 2,910-2,443 |
| b: call off, no safe-bag | 47.3% | 46,524-48,914 | 540,446-540,318 | 2,874-2,750 |
| c: call off + safe-bag (patch defaults) | 45.9% | 45,944-49,620 | 538,736-542,054 | 2,881-2,745 |
| d: c without Treasure-first | 47.3% | 48,058-48,800 | 533,966-553,299 | 3,099-2,979 |
- vs `_v6` on the same 74 games: c **93.2%** (69-5) vs `_f1` 89.2% (66-8); on `contest` c won 2/2, `_f1` 1/2 (lost 0-600).
- Bags lost at death (b vs c, 74 games each): ours 2,656 vs 2,856, big captures identical (140/138): the safe-bag hold
  rarely triggers.
- Older (on `_L0`, 24 games on maps/gold vs `_L0`): v2 (no team plan) 50.0%, v3 (also no Treasure) 50.0%, v4 (team plan
  with HP budget in group_score) 45.8%.
- Reading: on these maps vs our own code the game is decided by the early fights (the side that wins them snowballs on
  kill gold, then farms both monoliths and reaches 1000 at r1100-1990); mirror outcomes flip with any small change
  (side A/B swaps on half the maps). Round-limit games are ~15% of games, gold-decided ones ~1%. None of the economy
  changes moves that; the team monolith call hurts.
- No-regression check on the 56-map pool not run: with the flag off on 54 of 56 maps behaviour there is identical by
  construction (deterministic), and the patch is not recommended for merge.

## What to keep / next ideas
- Keep: `goldmaps.mjs` + `maps/gold*`, `tools/analysis/gold_stats.py` (tiebreak reason per game), the detector.
- The real lever on `contest`-like maps is fights early and carrying 200-gem bags to contested central altars. A carrier
  escort (team moves with the bag) needs shared state; the shared-memory bits 7 of bytes 2-5 are free (used here only by
  the off-by-default call).

## Reproduce
```bash
node tools/mapgen/goldmaps.mjs maps/gold 7
python3 tools/bench.py _x_gold2 _f1 --maps 'maps/gold/*.map26a' --jobs 2 --out /tmp/gold/runs/x
python3 tools/analysis/gold_stats.py --per-game /tmp/gold/runs/x/*   # wins, tiebreak reason, gems, gold, kills
```
