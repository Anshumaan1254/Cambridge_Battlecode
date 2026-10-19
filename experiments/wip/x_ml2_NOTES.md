# x_ml2: fight / danger model learned from real ladder games (agent ml2, session 13)

Baseline `bots/_ch2` (legend_m14_commit). Copy `bots/_x_ml2` (switches default off), patch `experiments/wip/x_ml2.patch`.
Scripts: `tools/ml/ml2_decode.py` (decode replay folders), `tools/ml/ml2_dataset.py` (contact dataset), `tools/ml/ml2_train.py` (models).

## State (update at every step)
- 23:00 UTC: decoding all real replay sets into the scratchpad (`$S/ml2/dec/<set>/`): ladder_oct19b (50, us = index.json side),
  ladder_oct18 (17, us = team 0), sneaky_oct18 (17, us = team 0), interwin_oct19 (45), interwin_oct18 (13), ladder_top3 (15),
  intercon_oct18 (30): 187 games. Dataset builder written and checked on ladder_oct19b: 54,467 contact rows (an enemy champion
  within 7), our die-within-8 rate 11.8% vs theirs 6.0%.

## Data
- Row = alive body with an alive enemy champion within 7 (true positions). Features from what that body sees (enemy in a bush hidden
  unless we stand in a bush within 2). Labels die4, die8, kill8 (enemy within 6 dies within 8), net3 / taken3 / dealt3 (champion damage
  over the next 3 rounds), act_hit1, act_away1.

## Results
(pending)

## Next
Train logistic / boosted models with games kept whole in folds; compare with the bot's estimate; port the best to C++.
