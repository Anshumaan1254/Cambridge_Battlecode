# v84 ladder: how we die and who wins fights (helper-agent analysis, Nov 2 2026)

Data: 128 decoded ranked games (28 wins, 100 losses) in `experiments/ladder_nov2/dec/` (regenerate: decode_all.sh). Scripts here:
`extract.py` (deaths / fights / games / retreats / recalls / dives / chases jsonl, ~40 s), `report.py` (report_tables.txt), `extra.py`
(extra_tables.txt), `story.py <matchId> <body> <round>` (the last rounds before a death).

Definitions: fight = champion hits ≤ 5 rounds and ≤ 6 tiles apart; exchange = a fight where both teams landed a hit (2,988). R = (HP ×
damage per round of own side within 6, self included) ÷ (same for enemies within 6), item-adjusted strength / focus.

## 1. How our champions die

| | we W (135) | we L (922) | they W (483) | they L (751) |
|---|---|---|---|---|
| deaths per game | 4.8 | 9.2 | 17.2 | 7.5 |
| killed by a camp | 13% | 10% | 4% | 11% |
| champion kill in a fight the victim's team started | 42% | 30% | 29% | 42% |
| own side incl. self / enemies within 6 (5 rounds before) | 2.1 / 2.2 | 2.2 / 2.2 | 2.2 / 2.3 | 2.2 / 2.3 |
| outnumbered / no ally within 6 | 38% / 33% | 34% / 30% | 38% / 30% | 43% / 35% |
| 2+ steps toward the nearest enemy, last 8 rounds | 54% | 63% | 41% | 38% |
| no retreat step in the last 10 rounds (champion kills) | 25% | 34% | 23% | 19% |
| hp 5 rounds before: mean / share under 50% | 44% / 65% | 56% / 45% | 55% / 48% | 51% / 55% |
| carrying gems / gems lost per death | 14% / 3.1 | 23% / 5.9 | 27% / 7.3 | 25% / 6.3 |
| hit by an awake camp in the last 5 rounds / by a camp the enemy woke | 34% / 16% | 27% / 15% | 18% / 5% | 22% / 4% |
| lure (chased a target that kept its distance) | 11% | 12% | 8% | 7% |
| on the enemy half | 38% | 36% | 35% | 37% |
| stunned in the last 3 rounds | 43% | 41% | 45% | 44% |

Not outnumbered or alone more often than they are: our bodies walk in (63% vs 38-41%), never retreat (34% vs 19%), are burst down from
healthy, and take hits from camps the enemy woke (15% vs 4-5%). 70% of our deaths in losses are in fights the enemy opened. Gems carried,
map half, stuns and recalls do not separate us (our recall-then-cancel is the deliberate fake-recall bait, not an escape attempt).

## 2. Exchanges: who wins and why

| our win share | W games | L games |
|---|---|---|
| exchanges per game; win:loss:draw | 26.4; 488:148:102 = 77% | 22.5; 806:1019:425 = 44% |
| we hit first / they hit first | 83% / 67% | 56% / 32% |
| bodies within 6 at contact: more / equal / fewer | 84 / 70 / 78% | 49 / 46 / 34% |
| R at contact: <0.5 / 0.5-0.8 / 0.8-1.25 / 1.25-2 / >2 | 57 / 77 / 73 / 74 / 88% | 25 / 36 / 42 / 54 / 61% |

Logistic regression on 2,456 decisive exchanges (z): item gap per participant +12.3, hitting first +11.6, log R +5.3, body count at
contact +0.9 (n.s.), camp-damage gap −2.4. In losses the enemy has 26% more shards per body at r400 and 41% at r600. Arrival spread and
focus fire are not the lever. Retreats: started at 40%+ hp with no enemy dash / stun ready in reach: caught 8%; under 40% hp with one
ready: caught 41%. We start leaving less often (61% vs 70%).

## 3. Patterns that lose games (per game in losses / wins; enemy rate in brackets)

**P1 Walking into a stronger group** (2+ steps toward the nearest enemy within 4 rounds at R < 0.67): 12.4 / 5.0 [6.3 / 13.9]; 12% die
within 8 rounds = 1.45 deaths and 10.6 gems per loss [0.50, 2.1]. Death within 6 rounds after a step in: 9.7% at R < 0.67, 4.3% at
parity, 1.7% when stronger. 139 steps a game within 6 of a stronger group while having equal or more bodies [69]: we weigh bodies, not
items. Dying again within 40 rounds of respawning 0.90 [0.35]. Fix: R < 0.67 or Burst ≥ hp → no step that shortens the distance to any
visible enemy; 0.67 ≤ R < 1.5 → engage only if we hit first and an ally is within 3; bag ≥ 10 or just respawned → R ≥ 1.5.
(Implemented as `g23_divefilter`, first part.) More frequent on small maps / short spawn-to-spawn paths / few altars.

**P2 No disengage once the trade turns** (85% overlap with P1): 2.80 deaths per loss with no retreat step [1.27]. Fix: leave this turn
(toward allies / spawn) unless our attack kills now, when hp < 50% and an enemy within 4 has a dash / stun / damage spell ready, or hp <
40%, or Burst ≥ hp.

**P3 Contesting the enemy at a camp it woke**: 1.42 / 0.79 deaths a game with damage from a camp the enemy woke [0.29 / 0.82]. Camps hit
the nearest champion: closing on a farming enemy makes us the camp's target; 24% of our camp-involved deaths show 2+ move reversals in the
last 8 rounds [13%]. Fix: with an enemy champion within 6, never end a turn inside an awake camp's range where no enemy is closer to the
camp; hit enemies there only from outside; commit to the exit tile. More common when 40%+ of combat camps sit in the middle band, and with
5 champions a side.

**P4 Chasing a retreating target into its team (lure)**: 1.11 / 0.54 deaths a game [0.54 / 1.32]; in 91% another enemy made the kill;
53.5 chases started a game [41]. Fix: stop when 3 steps toward the same target did not shrink the gap, or its dash is ready; never take a
chase step onto a tile with more visible enemies than allies within 6, or more than 6 tiles from every ally.

Example matches: 34232fbd-3d4f-4e8e-94df-0e23adf39a1c, 6425e837-7261-4ed8-ab2e-d1acda791688, ff848547-cdeb-4f1f-9425-75dc35a7e9e1,
f2900a82-a986-417a-ad38-d1491b93ae98, 9028e5e6-20dc-4878-8734-902e6fd8784b, a58f3c4c-915b-4ce5-98e5-b3542c6d22ea,
f3155e2a-546b-411b-b88f-784a870a02c4, 3ef76771-ce2a-499d-b2d0-8a5bcc99f3d7, 28ee331d-ceeb-4d72-be5f-3d90a2ede6cf.
