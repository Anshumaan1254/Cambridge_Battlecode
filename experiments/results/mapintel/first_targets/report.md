# First targets: which groups the top teams capture first (leave-maps-out)

1162 team-games on 40 maps. Share of the true first-n groups among the n best ranked, on held-out maps:

| ranking | share |
|---|---|
| nearest by walk (dU) | 0.648 |
| compact plan 1 (validate_ladder.py, in-sample maps) | 0.532 |
| learned logistic, C = 0.01 | 0.696 |
| learned logistic, C = 0.1 | 0.695 |
| learned logistic, C = 1.0 | 0.690 |
| boosted forest, depth 2, 20 trees, learning rate 0.3 | 0.689 |

Chosen C = 0.01; coefficients on standardised features (positive = captured earlier):
- rank_dU: -1.916
- log_dU: -0.454
- gold: -0.325
- S: -0.298
- ncamps: +0.286
- heavy: -0.272
- dE: +0.261
- dU_minus_dE: -0.216
- contested: +0.210
- value: -0.201
- gems: -0.166
- hp: -0.146
- value_share: +0.087
- dU: +0.013
