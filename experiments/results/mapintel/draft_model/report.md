# Draft win models, leave-maps-out (5 folds of maps stratified by archetype)

8455 games on 40 maps; side a wins 0.504; higher-rated team wins 0.569

| model | log loss | AUC | C per fold |
|---|---|---|---|
| M0 | 0.6829 | 0.5852 | [0.03, 0.03, 0.03, 0.1, 0.1] |
| M1 | 0.6847 | 0.5790 | [0.01, 0.01, 0.01, 0.01, 0.01] |
| M2 | 0.6836 | 0.5836 | [0.01, 0.01, 0.01, 0.01, 0.01] |
| M3 | 0.6944 | 0.5647 | [0.01, 0.01, 0.01, 0.01, 0.01] |
| M4 | 0.6943 | 0.5660 | [0.01, 0.01, 0.01, 0.01, 0.01] |

Chosen for the headers: M1 (C = 0.01); full-data fit weights in weights.json. Champion values (log-odds, rating held fixed; M1-style mean over maps):
- Ryth: +0.040 (range over maps +0.040 .. +0.040)
- Willow: +0.032 (range over maps +0.032 .. +0.032)
- Vendetta: +0.030 (range over maps +0.030 .. +0.030)
- Vesper Vale: +0.030 (range over maps +0.030 .. +0.030)
- Cassi & Issac: +0.022 (range over maps +0.022 .. +0.022)
- Stellar: +0.008 (range over maps +0.008 .. +0.008)
- Marcella: +0.008 (range over maps +0.008 .. +0.008)
- Prism: +0.007 (range over maps +0.007 .. +0.007)
- Tavi: -0.005 (range over maps -0.004 .. -0.004)
- Heart of Ruin: -0.007 (range over maps -0.007 .. -0.007)
- Varg: -0.041 (range over maps -0.041 .. -0.041)
- Ren: -0.125 (range over maps -0.125 .. -0.125)

## Roster battery (GOD v10, 2240 games, both rosters forced), leave-maps-out

| model | C | log loss | AUC |
|---|---|---|---|
| M0 | 0.03 | 0.6619 | 0.4637 |
| M0 | 0.1 | 0.6620 | 0.4637 |
| M0 | 0.3 | 0.6620 | 0.4637 |
| M0 | 1.0 | 0.6620 | 0.4637 |
| M1 | 0.03 | 0.6220 | 0.6546 |
| M1 | 0.1 | 0.6229 | 0.6545 |
| M1 | 0.3 | 0.6236 | 0.6543 |
| M1 | 1.0 | 0.6241 | 0.6543 |
| M2 | 0.03 | 0.6230 | 0.6577 |
| M2 | 0.1 | 0.6274 | 0.6562 |
| M2 | 0.3 | 0.6313 | 0.6553 |
| M2 | 1.0 | 0.6341 | 0.6546 |
| M3 | 0.03 | 0.6843 | 0.6143 |
| M3 | 0.1 | 0.7430 | 0.6017 |
| M3 | 0.3 | 0.8250 | 0.5869 |
| M3 | 1.0 | 0.9593 | 0.5674 |

Used: M1, C = 0.03. Champion values (log-odds per champion difference):
- Vesper Vale: +0.452
- Ryth: +0.179
- Vendetta: +0.157
- Heart of Ruin: +0.083
- Tavi: +0.016
- Varg: -0.004
- Marcella: -0.006
- Prism: -0.071
- Ren: -0.113
- Willow: -0.154
- Cassi & Issac: -0.219
- Stellar: -0.319
