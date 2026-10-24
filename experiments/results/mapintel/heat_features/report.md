# Heat-map features (U-Net, out of fold) for plan 3 and plan 4, held out

Plan 3: 787 groups reached by both teams on 40 maps; truth = the share of the map's ladder games in which both teams captured the group (label share >= 0.25: 0.35 of the groups).

| predictor | Spearman per map (mean) | AUC |
|---|---|---|
| catalog priority | 0.424 | 0.738 |
| catalog contested flag | 0.429 | 0.715 |
| runtime closeness | 0.509 | 0.772 |
| heat: fight | 0.405 | 0.752 |
| heat: death | 0.367 | 0.740 |
| logistic: closeness + value | 0.403 | 0.746 |
| logistic: closeness + value + heat | 0.437 | 0.798 |
| logistic: heat + value | 0.364 | 0.746 |
| logistic: catalog priority | 0.424 | 0.699 |
| logistic: catalog priority + heat | 0.460 | 0.759 |

Paired per map (the same maps; bootstrap over maps, 2,000 draws):
- logistic: closeness + value + heat vs logistic: closeness + value: Spearman +0.035 (95% -0.055 .. +0.118), better on 23 of 40 maps, worse on 17
- logistic: catalog priority + heat vs logistic: catalog priority: Spearman +0.035 (95% -0.063 .. +0.136), better on 21 of 40 maps, worse on 19

Plan 4: pooled balanced accuracy on held-out maps, the learned constant vs the heat-shifted threshold:

| threshold | constant | heat-shifted |
|---|---|---|
| ETA gap k_abandon (rounds) | 0.667 | 0.667 |
| regroup distance d (tiles) | 0.543 | 0.539 |
| bank-interception margin (rounds) | 0.609 | 0.607 |
| respawn wait w_max (rounds) | 0.878 | 0.883 |
