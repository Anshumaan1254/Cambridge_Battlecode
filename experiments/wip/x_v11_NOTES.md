# v11 (session 14, Oct 21 evening): the user's requests on top of GOD v10

Code: `experiments/wip/x_v11.patch` on `bots/god` (= GOD v10). Rebuild: `cp -r bots/god bots/_x_v11 && rm -rf bots/_x_v11/.cambc &&
(cd bots/_x_v11 && patch -p1 < ../../experiments/wip/x_v11.patch)`, then `SRC=bots/_x_v11 tools/variant.sh NAME key=value ...`.
Every switch is off by default (v10 play). Measured on cambc 3.0.4, `experiments/pools/train78a.csv` (78 tuning maps x 2 sides = 156 games), h2h vs `_v10b` (= GOD v10).

The user's request: draft Prism instead of Vesper Vale; Prism as a safe anchor (home-side farmer and banker: groups near our spawn and
altar, bags of ~20 instead of 54, leaves fights at danger 0.1 instead of 0.2, never crosses to the enemy half; a killer on our half holds
the reward tile until the anchor steps on, then steps off); Heart of Ruin as the aggressor; three phases (0-666, 666-1332, 1332-2000);
change strategy when losing; better ward placement from map analysis.

| Switch | What |
|---|---|
| `pd_sub_from 1` / `pd_sub_to 5` | (existing measurement switch) the draft picks Prism wherever it would pick Vesper Vale |
| `anchor_prism 1` | Prism ranks first as the anchor (existing F4 `anchors`: Vesper 3, Marcella 2, Prism 1) |
| `anchor_side` 0.45 | the anchor never takes a group whose walk from our spawn exceeds 0.45 x (ours + theirs) |
| `anchor_trib` 0.38, `anchor_ml2` 0.1, `handoff` 1 | (existing F4) anchor bag threshold x0.38 (54 -> ~20), danger exit at 0.1, the killer's hold-and-step-off hand-off |
| `hor_aggro` 1 / 2 | Heart of Ruin: 1 = always (enemy half x0.4, deny +0.5, fight margins -0.15); 2 = margins only while health >= 0.7, strike dash up, an ally within 6 |
| `phases` 1 | phase multipliers on enemy-half penalty / deny bonus / bag threshold: early 1 / +0 / 1, mid 0.8 / +0.2 / 1, end 1 / +0.3 / 0.75 |
| `lose_adapt` 1 | from r666, behind by >= 100 banked gems: trades even -> press (half x0.6, deny +0.4); trades lost -> regroup (half x1.5, isolated +0.2, bags x0.8) |
| `ward_smart` 1 / 2 | 1 = the best map-scored tile in reach (our-half / contested groups x value, our altars, spawn-to-spawn corridor, bushes; x0.35 near an ally ward), kept unless a tile scores 1.3x; 2 = the same score but only tiles ahead (nearer their spawn), forwardness first, else v10's rule |

Fuel: the first `ward_smart` scored every camp group for each of 25 tiles (~65k fuel a call: 14,668-20,195 lost turns in 12 games);
now the groups / altars are filtered once per call and the call waits for 30k fuel: 61-63 lost turns in 6 games (v10 56-59).

Results (wins of 156 vs GOD v10):

| Variant | Switches | Wins | % | Deaths us-them |
|---|---|---|---|---|
| `_v11d` | Prism for Vesper | 58 | 37.2 | 2843-2516 |
| `_v11a` | + Prism anchor (side, bags, ml2, hand-off) | 58 | 37.2 | 2481-2306 |
| `_v11h` | + hor_aggro 1 | 46 | 29.5 | 2858-2308 |
| `_v11p` | + phases + lose_adapt | 43 | 27.6 | 2933-2363 |
| `_v11` | + ward_smart 1 (everything) | 28 | 17.9 | 3024-1995 |
| `_v11w` | ward_smart 1 alone (Vesper draft) | 60 | 38.5 | 2786-2166 |
| `_v11Ah` | hor_aggro 1 alone | 80 | 51.3 | 2621-2672 |
| `_v11Ap` | phases + lose_adapt alone | 71 | 45.5 | 2773-2607 |
| `_v11Aa` | anchors (Vesper anchor) + side + bags + hand-off alone | 64 | 41.0 | 2582-2376 |
| `_v11Aw2` | **ward_smart 2** (scouting: tiles ahead toward their spawn on the walk field, scored; else v10's rule) | **91** | **58.3** | 2357-2784 |
| `_v11Ah2` | hor_aggro 2 (margins only fresh + dash up + ally within 6) | 75 | 48.1 | 2523-2591 |
| `_v11Aph` | phases alone | 74 | 47.4 | 2818-2626 |
| `_v11Alo` | lose_adapt alone | 80 | 51.3 | 2603-2555 |

`_v11Aw2` confirmation: held-out test152 164/304 = 53.9% [48.3, 59.5], maps 30 / 104 / 18, sign p 0.11, margin +37.2 gems a map
[-12.4, +88.5]; train78b 81/156 = 51.9% (17 / 47 / 14), margin -18.6; all 308 maps 336/616 = 54.5%, maps 69 2-0 / 41 0-2.
Fuel (release, corners_v3 / nx100x100 / nx60x60 vs v10): 61 lost turns r>3 in 6 games (opponent 59). Builds on SDK 2.2.5.

Release check of `_v11Aw2` (`tools/finalcheck.sh _v11Aw2 _v10b`): vs v8 held-out 246/304 = 80.9% (v10 79.9%), all 308 81.5%; h2h vs v10
all 308 maps 336/616 = 54.5% [50.6, 58.4], sign p 0.0097, margin +43.3 gems a map [+2.9, +82.7]; **19 outside opponents (21 official maps,
42 games each) 655/798 vs v10's 678** (`_pnA` ambush persona 20 vs 32, `_k_fit` 21 vs 29, `_k_ci` 26 vs 31, `_pnO` 27 vs 30, `_g4` 38 vs
41; `_pnV` 34 vs 30, `_q_s2v` 28 vs 26, `_pnS` 36 vs 34); pace 990.0 (v10 978.8); 0 faults, lost turns r>3 60 / 64 / 60 in 12 games each
vs `_v8k1` / `_pws` / `_q_s2v`. Better head-to-head, worse against the outside opponents (the non-transitive pattern of strike_first):
not shipped. `_v11Pw2` (Prism + anchor + scouting wards) 38/156 = 24.4%.
`ward_smart` 3 = 2 + a bush next to our target group first (the ambush persona farms from bushes beside its camps).

