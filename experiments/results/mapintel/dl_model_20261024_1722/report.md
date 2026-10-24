# Step 7: deep models vs the step-6 bar (leave-maps-out, 5 archetype-stratified folds)

Device cuda, torch 2.11.0+cu128, seeds 3, hidden 8; 15.9 minutes. Held-out score: mean (sd) over seeds. Export needs the bar + 0.01 (share / top-1), - 0.003 (log loss).

## T1a opening (top-n share)

| task | model | share | epochs |
|---|---|---|---|
| t1a | bar: nearest | 0.6508 | |
| t1a | bar: boosted forest (first_scores) | 0.6945 | |
| t1a | mlp | 0.6973 (0.0023) | 170 |
| t1a | graph | 0.6949 (0.0064) | 70 |
| t1a | distil | 0.6996 (0.0033) | 140 |

## T1b next target (top-1, top-3)

| task | model | top-1 | top-3 | epochs |
|---|---|---|---|---|
| t1b | bar: nearest to previous | 0.2355 | 0.5333 | |
| t1b | bar: boosted forest | 0.3598 | 0.6831 | |
| t1b | mlp | 0.3288 (0.0023) | 0.6688 (0.0042) | 6 |
| t1b | graph | 0.3814 (0.0021) | 0.7136 (0.0078) | 4 |
| t1b | distil | 0.3302 (0.0065) | 0.6715 (0.0060) | 4 |

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
| t3 | bar: blurred camps | 0.2230 | |
| t3 | unet | 0.5375 (0.0059) | 150 |

## Exported (dl_weights.json -> dl_export.py -> dl_weights.h)

- t1a: not exported: distil MLP 41-8-1, held-out share 0.6996 vs bar 0.6945 (LEARNED, current-patch ladder)
- t1b: not exported: distil MLP 56-8-1, held-out top1 0.3302 vs bar 0.3598 (LEARNED, current-patch ladder)
- t2: not exported: values w + MLP 19-8-12, held-out log loss 0.6683 vs bar 0.6220 (SIMULATED v10 roster battery)
