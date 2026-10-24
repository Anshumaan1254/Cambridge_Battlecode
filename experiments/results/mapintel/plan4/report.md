# Plan 4 thresholds learned from the top teams' replays (leave-maps-out, archetype folds)

599 games on 40 maps. Pooled balanced accuracy of each rule on held-out maps (the threshold from the current formula, the training folds' best constant, or the ridge over the 19 runtime map features); the winner goes into model_weights.h.

| threshold | moments (label 1) | maps | formula | constant | ridge | used | final value / intercept |
|---|---|---|---|---|---|---|---|
| ETA gap k_abandon (rounds), local power p (percent) | 388873 (30144) | 40 | 0.557 | 0.667 | 0.656 | constant | k 0.0, p 1000.0 |
| regroup distance d (tiles) | 31086 (11305) | 40 | 0.532 | 0.543 | 0.539 | constant | d 6.0 |
| bank-interception margin (rounds) | 327615 (44240) | 40 | 0.593 | 0.609 | 0.592 | constant | m 7.0 |
| respawn wait w_max (rounds) | 128452 (15731) | 40 | 0.881 | 0.878 | 0.879 | formula | w 30.0 |

Abandons with no enemy within 12 tiles (not plan 4: heal / other reasons): 7165, health at the moment median 0.54 (the economy model's retreat line, change 2).

Per-map best thresholds (balanced accuracy on that map alone): `results.<key>.per_map_best` in weights.json.
