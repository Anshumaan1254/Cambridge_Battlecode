# Role tables from 599 decoded top-team games (LEARNED; tools/teamplan/ladder_roles.py)

| Champion | Games | Captures | Gold share | Gem share | Gold / capture | Capture gold / game | Kills / game | Gems its kills took / game | Kill-gold share | Deaths / game | Death hazard / round | Bag at death | Deaths with bag 20+ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VesperVale | 1084 | 11309 | 32.1% | 26.2% | 165.3 | 1725 | 1.76 | 20.5 | 0.12 | 1.65 | 0.00148 | 12.0 | 15.2% |
| Marcella | 989 | 9454 | 20.8% | 22.6% | 128.3 | 1226 | 1.71 | 17.2 | 0.12 | 1.60 | 0.00144 | 11.4 | 14.7% |
| HeartOfRuin | 947 | 8197 | 14.7% | 16.4% | 104.2 | 902 | 1.48 | 13.8 | 0.14 | 1.91 | 0.00171 | 9.9 | 14.6% |
| Ryth | 748 | 5006 | 9.6% | 10.2% | 112.0 | 750 | 2.31 | 19.7 | 0.24 | 2.07 | 0.00184 | 9.1 | 12.1% |
| Vendetta | 724 | 6762 | 13.5% | 13.7% | 115.9 | 1083 | 1.68 | 18.0 | 0.13 | 1.87 | 0.00170 | 9.4 | 14.2% |
| Tavi | 281 | 1732 | 2.3% | 2.7% | 78.2 | 482 | 1.20 | 10.5 | 0.20 | 2.22 | 0.00204 | 6.8 | 11.7% |
| Prism | 208 | 2096 | 3.4% | 4.4% | 95.4 | 962 | 2.16 | 19.9 | 0.18 | 1.69 | 0.00154 | 26.7 | 28.7% |
| Willow | 169 | 397 | 0.5% | 0.7% | 72.1 | 169 | 0.78 | 2.7 | 0.32 | 2.09 | 0.00190 | 2.6 | 5.1% |
| Varg | 105 | 711 | 1.9% | 1.7% | 151.7 | 1028 | 1.40 | 10.7 | 0.12 | 2.03 | 0.00183 | 11.5 | 12.2% |
| Cassi | 88 | 257 | 0.3% | 0.4% | 57.6 | 168 | 1.11 | 9.0 | 0.40 | 3.28 | 0.00302 | 3.0 | 4.2% |
| Issac | 88 | 461 | 0.6% | 0.7% | 76.5 | 401 | 1.11 | 5.1 | 0.22 | 3.28 | 0.00302 | 3.7 | 8.0% |
| Stellar | 34 | 134 | 0.2% | 0.2% | 93.3 | 368 | 2.53 | 21.7 | 0.41 | 2.53 | 0.00228 | 6.6 | 14.0% |
| Ren | 13 | 79 | 0.1% | 0.1% | 72.5 | 441 | 1.08 | 10.2 | 0.20 | 1.85 | 0.00165 | 10.2 | 8.3% |

- Captures shared by two or more bodies: 2370 of 43850 (5.4%).
- Bag swing per team-game: winners take 102.3 gems from enemy bags and lose 57.5; losers take 49.5 and lose 116.1.
- Top body's share of team capture gold: winners 0.467, losers 0.484.
- Ends: {'gems': 583, 'tiebreak': 16}; final round median 1064, mean 1117; reaching round 1990+: 2.7%; close races (loser 900+): 9.3%.
- The death hazard uses the game length as the exposure (dead time included): a lower bound of the hazard while alive.

## Gold-only captures (25 raw replays; the summaries above miss them)

500 of 2480 captures are gold-only, 9.4% of all capture gold.

| Champion | Capture gold share | Gold-only share of its own capture gold | Gold-only captures / all its captures |
|---|---|---|---|
| VesperVale | 36.8% | 7.3% | 113 / 666 |
| Marcella | 19.6% | 5.0% | 51 / 436 |
| Prism | 14.6% | 6.7% | 56 / 460 |
| HeartOfRuin | 12.6% | 16.0% | 130 / 402 |
| Vendetta | 7.6% | 7.3% | 24 / 179 |
| Ryth | 3.5% | 26.1% | 55 / 125 |
| Varg | 2.3% | 14.8% | 17 / 58 |
| Tavi | 1.0% | 11.9% | 8 / 43 |
| Willow | 0.7% | 28.2% | 12 / 30 |
| Stellar | 0.5% | 48.8% | 11 / 26 |
| Issac | 0.3% | 27.2% | 6 / 16 |
| Ren | 0.3% | 51.6% | 11 / 26 |
| Cassi | 0.2% | 59.6% | 6 / 13 |
