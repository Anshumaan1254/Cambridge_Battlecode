# First targets: which groups the top teams capture first (leave-maps-out)

963 team-games on 40 maps. Share of the true first-n groups among the n best ranked, on held-out maps:

| ranking | share |
|---|---|
| nearest by walk (dU) | 0.608 |
| compact plan 1 (validate_ladder.py, in-sample maps) | 0.532 |
| learned logistic, C = 0.01 | 0.616 |
| learned logistic, C = 0.1 | 0.647 |
| learned logistic, C = 1.0 | 0.653 |
| boosted forest, depth 2, 20 trees, learning rate 0.3 | 0.717 |

Chosen C = 1.0; coefficients on standardised features (positive = captured earlier):
- hp: +4.379
- S: -2.461
- gold: -1.998
- rank_dU: -1.972
- heavy: -1.154
- log_dU: -0.674
- ncamps: +0.375
- value: -0.364
- dE: +0.358
- dU: +0.303
- value_share: +0.263
- contested: +0.202
- dU_minus_dE: -0.046
- gems: -0.007
