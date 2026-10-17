# x_gold: tiebreak-aware economy for gem-scarce maps (agent `gold`, 2026-10-17)

Bot copy: `bots/_x_gold` (local). Patch: `experiments/wip/x_gold.patch` (against `bots/legend/src`).
Status: in progress (this file is updated as results come in).

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

## Changes (all behind `params.h` switches, `tb_*`)
(in progress)

## Results
(in progress)

## Reproduce
```bash
node tools/mapgen/goldmaps.mjs maps/gold 7
python3 tools/bench.py _x_gold _L0 --maps 'maps/gold/*.map26a' --jobs 2 --out /tmp/gold/runs/x
python3 tools/analysis/gold_stats.py --per-game /tmp/gold/runs/x/*   # wins, tiebreak reason, gems, gold, kills
```
