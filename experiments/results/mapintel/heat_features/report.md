# Heat-map features (U-Net, out of fold) for plan 3 and plan 4, held out

Plan 3: 787 groups reached by both teams on 40 maps; truth = the share of the map's ladder games in which both teams captured the group (label share >= 0.25: 0.25 of the groups).

| predictor | Spearman per map (mean) | AUC |
|---|---|---|
| catalog priority | 0.426 | 0.772 |
| catalog contested flag | 0.324 | 0.680 |
| runtime closeness | 0.386 | 0.719 |
| heat: fight | 0.332 | 0.733 |
| heat: death | 0.323 | 0.728 |
| logistic: closeness + value | 0.423 | 0.744 |
| logistic: closeness + value + heat | 0.454 | 0.769 |
| logistic: heat + value | 0.452 | 0.744 |
| logistic: catalog priority | 0.426 | 0.747 |
| logistic: catalog priority + heat | 0.452 | 0.774 |

Paired per map (the same maps; bootstrap over maps, 2,000 draws):
- logistic: closeness + value + heat vs logistic: closeness + value: Spearman +0.031 (95% -0.052 .. +0.105), better on 24 of 40 maps, worse on 16
- logistic: catalog priority + heat vs logistic: catalog priority: Spearman +0.026 (95% -0.057 .. +0.113), better on 20 of 40 maps, worse on 20

Plan 4: pooled balanced accuracy on held-out maps, the learned constant vs the heat-shifted threshold:

| threshold | constant | heat-shifted |
|---|---|---|
| ETA gap k_abandon (rounds) | 0.667 | 0.667 |
| regroup distance d (tiles) | 0.543 | 0.539 |
| bank-interception margin (rounds) | 0.609 | 0.607 |
| respawn wait w_max (rounds) | 0.878 | 0.883 |
