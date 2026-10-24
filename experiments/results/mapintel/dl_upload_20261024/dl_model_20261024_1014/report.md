# Step 7: deep models vs the step-6 bar (leave-maps-out, 5 archetype-stratified folds)

Device cuda, torch 2.11.0+cu128, seeds 3, hidden 8; 12.5 minutes. Held-out score: mean (sd) over seeds. Export needs the bar + 0.01 (share / top-1), - 0.003 (log loss).

## T1a opening (top-n share)

| task | model | share | epochs |
|---|---|---|---|
| t1a | bar: nearest | 0.6157 | |
| t1a | bar: boosted forest (first_scores) | 0.7228 | |
| t1a | mlp | 0.6764 (0.0085) | 140 |
| t1a | graph | 0.6525 (0.0171) | 40 |
| t1a | distil | 0.6720 (0.0052) | 200 |

## T1b next target (top-1, top-3)

| task | model | top-1 | top-3 | epochs |
|---|---|---|---|---|
| t1b | bar: nearest to previous | 0.1856 | 0.4669 | |
| t1b | bar: boosted forest | 0.4066 | 0.7240 | |
| t1b | mlp | 0.3404 (0.0029) | 0.6763 (0.0046) | 8 |
| t1b | graph | 0.3949 (0.0082) | 0.7203 (0.0091) | 6 |
| t1b | distil | 0.3419 (0.0006) | 0.6787 (0.0043) | 6 |

## T2 champion values (out-of-fold log loss, lower is better)

| task | model | log loss | epochs |
|---|---|---|---|
| t2 | bar: side only | 0.6619 | |
| t2 | bar: constant values (M1) | 0.6220 | |
| t2 | const | 0.6208 | 25 |
| t2 | values | 0.6683 | 25 |
| t2 | deepset | 0.6515 | 25 |

## T3 heat (Pearson on valid tiles, per channel)

| task | model | Pearson | epochs |
|---|---|---|---|
| t3 | bar: blurred camps | 0.2210 | |
| t3 | unet | 0.5186 (0.0030) | 145 |

## Exported (dl_weights.json -> dl_export.py -> dl_weights.h)

- t1a: not exported: mlp MLP 41-8-1, held-out share 0.6764 vs bar 0.7228 (LEARNED, current-patch ladder)
- t1b: not exported: distil MLP 56-8-1, held-out top1 0.3419 vs bar 0.4066 (LEARNED, current-patch ladder)
- t2: not exported: values w + MLP 19-8-12, held-out log loss 0.6683 vs bar 0.6220 (SIMULATED v10 roster battery)
