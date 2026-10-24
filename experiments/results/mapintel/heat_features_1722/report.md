# Heat-map features (U-Net, out of fold) for plan 3 and plan 4, held out

Plan 3: 787 groups reached by both teams on 40 maps; truth = the share of the map's ladder games in which both teams captured the group (label share >= 0.25: 0.35 of the groups).

| predictor | Spearman per map (mean) | AUC |
|---|---|---|
| catalog priority | 0.424 | 0.738 |
| catalog contested flag | 0.429 | 0.715 |
| runtime closeness | 0.509 | 0.772 |
| heat: fight | 0.446 | 0.776 |
| heat: death | 0.420 | 0.762 |
| logistic: closeness + value | 0.403 | 0.746 |
| logistic: closeness + value + heat | 0.474 | 0.804 |
| logistic: heat + value | 0.410 | 0.769 |
| logistic: catalog priority | 0.424 | 0.699 |
| logistic: catalog priority + heat | 0.472 | 0.772 |

Paired per map (the same maps; bootstrap over maps, 2,000 draws):
- logistic: closeness + value + heat vs logistic: closeness + value: Spearman +0.072 (95% -0.031 .. +0.159), better on 28 of 40 maps, worse on 12
- logistic: catalog priority + heat vs logistic: catalog priority: Spearman +0.047 (95% -0.065 .. +0.158), better on 24 of 40 maps, worse on 16

Plan 4: pooled balanced accuracy on held-out maps, the learned constant vs the heat-shifted threshold:

| threshold | constant | heat-shifted |
|---|---|---|
| ETA gap k_abandon (rounds) | 0.667 | 0.667 |
| regroup distance d (tiles) | 0.543 | 0.544 |
| bank-interception margin (rounds) | 0.609 | 0.608 |
| respawn wait w_max (rounds) | 0.878 | 0.883 |
