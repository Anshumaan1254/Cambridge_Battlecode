# Economy constants fitted to the top teams' replays

| constant | before | after | evidence |
|---|---|---|---|
| retreat | 0.3 | 0.52 | measured: median health at a mid-fight heal trip (3,109 trips); also the best pace Spearman of the grid |
| heal_frac | 0.5 | 0.9 | fitted (grid 0.3-0.95): the top teams go home after a capture 59% of the time at a median health of 0.93, so health does not separate the decision; 0.9 keeps the model going home after most jobs |
| bank_bag | 40 | 20 | fitted to the real bank sizes (median 26 gems over 24,945 banks): bag 20 gives the model's median bank 28 |
| shop_gold | 300 | 115 | measured: median unspent gold at a shop visit after a recall with an empty bag (18,572 visits) |
| gold_w | 0.1 | 0.167 | measured: the top teams' next-group choice (12,000 choices with the gold-only captures; gems, gold, walk, health, heavy controls) values 1 gold as 0.167 gems (0.020 when the decoder missed the gold-only captures) |
| pace_gold_w | 0.02 | 0.167 | the same measurement |
| dmg_mult | 1.0 | 1.3 | fitted to the real kill durations (1-2 attacker kills, 43,782 episodes): 1.3 makes the model's median kill time equal |
| contest | none (unopposed) | a -0.000, b 0.630 | LEARNED logistic of the team's capture share of a group on (their walk - ours) / band, all ladder captures; the pace check uses out-of-fold coefficients |

Checks (the catalog's pace model on the 40 maps, the reference rosters; real = 599 ladder games):

| set | pace Spearman | real / model: many-cluster | objective | other | first-capture Spearman | bank log ratio | kill log ratio |
|---|---|---|---|---|---|---|---|
| before (defaults) | 0.758 | 1.24 | 1.02 | 1.28 | 0.496 | +0.60 | +0.29 |
| after, unopposed | 0.707 | 1.24 | 1.13 | 1.29 | 0.649 | +0.03 | +0.00 |
| after (+ contest, out of fold) | 0.802 | 0.94 | 0.91 | 0.93 | 0.720 | -0.01 | +0.00 |

Map types: many-cluster = 60+ gem and gold clusters (10 maps), objective = monolith + golem gem share >= 0.3 (18), other (12). real / model = median over the type's maps of the real finish over the model's pace; a type is biased when it differs from the others.
Measured: retreat median 0.52 (q25 0.38, q75 0.96); after a capture home 60% (median health 1.00 home, 1.00 on); shop gold median 115; bank size median 26 (q25 14, q75 44); gold per gem 0.167.
