# 15. GOD v3 against five top teams (20 Oct 2026, session 14): 25 ladder games, 5 wins

Input: the user's `our_losses.zip` (5 match groups; we are side A in all). Replays `experiments/losses_oct20/an/replays/`, index
`experiments/losses_oct20/index.json` (map, drafts, outcome per game; tool `tools/strategy_v2/game_index.py`), KPI report
`experiments/losses_oct20/an/report.md` and tables `an/out/*.csv` (`tools/strategy_v2/run_all.py`), opener contexts
`tools/strategy_v2/opener_ctx.py`. Maps: 16 distinct, all in `maps/nyx_new` / `maps/comp30` except the new `maps/loss_oct20/ls50x50_R_c5_56fe6f`.
The A/B pool is now the 21 maps (42 games per cell). Every number below is from those files.

## 1. Results by opponent

| Group | Their draft (5 champions) | Games | Our wins | Our deaths - theirs | Camp gems | Gold earned |
|---|---|---|---|---|---|---|
| 38998622 | Ren, Stellar, C&I, Ryth, Varg (Varg, Vendetta, C&I, Willow, Ryth on nx50x41) | 5 | 2 (both at r2000 on gold / 200-0) | 93-72 | 8,524-8,798 | 80.9k-97.2k |
| b6bdb9e4 | **HoR**, Ren, Varg, Ryth, Marcella / Stellar | 5 | 0 | 58-19 | 3,131-4,748 | 20.8k-33.4k |
| c47c8c26 | Prism, Stellar, C&I, Marcella, **HoR** (Stellar, HoR, Varg at 3) | 5 | 2 (ambush 1012-987, nx100x100 1087-747) | 103-24 | 3,115-4,826 | 23.4k-41.5k |
| e6475502 | Vesper, C&I, Varg, Vendetta, Stellar / Stellar, Ren, C&I, **HoR**, Varg | 5 | 0 | 80-60 | 2,723-5,334 | 21.1k-37.5k |
| f8a4f886 | **HoR**, Ren, Stellar, Ryth, Varg | 5 | 1 (nx100x100 1055-719) | 121-47 | 2,043-4,986 | 22.1k-40.8k |

Totals: deaths 455-222, kills 146-288, camp gems 19.5k-28.7k, gold 168k-250k, captures 784-1,246 (neutral 67 vs 195, enemy side 15 vs 109),
banks 340-635. Camp-gem decomposition (alive x camp time x camp damage per round x gems per damage) = 0.925 x 0.881 x 0.865 x 0.907 = **0.64**.

## 2. Builds: every top team stacks Power in the damage stat

| | Us | Them |
|---|---|---|
| gold spent on items | 123,690 | 233,790 |
| damage-stat points (per 1,000 gold) | 2,739 (22.1) | 6,542 (28.0) |
| health points per 1,000 gold | 14.6 | 5.6 |
| emblems | Bruiser-dmg 293, Bruiser-hp 137, Monster-dmg 123, Durability-hp 86, Jungle-hp 59, Treasure-dmg 56 | **Power-dmg 950, Power-off 178**, Durability-hp 99, Bruiser-hp 86, Jungle-dmg 46, Treasure 64 |
| unspent gold at the end | 44,630 (26%; Ren 612 a game on average, 13,410 on the no-altar map) | 16,562 (7%) |

Orders (first five emblems, median first-emblem round): c47c8c26 Stellar / Marcella / Prism **PfE DhE PfE PfE PfE** (r130 / 316 / 422), HoR BhE DhE PfE;
f8a4f886 Stellar TfE PfE DhE PfE PfE (r268), HoR ThE JfE BhE DhE PfE (r124), Ryth ThE JsE BhE DhE PsE; b6bdb9e4 every body JsE/JfE BhE DhE PsE PsE
(Stellar r131, Varg r149, HoR r164); 38998622 Stellar TfE JfE DfE BhE PfE (r154), Cassi TfE JfE DfE BhE PfE (r161); e6475502 Vesper MsE TsE JhE PsE
(r69), Ren BhE DhE PfE PfE. Ours (build_style 2): Ren JhE TfE MfE BfE BfE (r122-164), Stellar MfE TfE BfE DhE BfE (r208-661), Cassi MfE DhE BfE
(r436-784), Varg MsE TsE JsE DhE BsE (r195-1005). Their gold is spread (top-1 share 0.29-0.33; ours 0.35-0.55 = Ren): their Stellar earns
1,080-2,718 gold a game and captures 8.5 times, ours 442-544 and 3.0.

## 3. Fights: the opener wins, and theirs are lethal

| Where / who opened (fights with 4+ hits) | Fights | Our deaths - theirs | Damage us - them |
|---|---|---|---|
| our half, they open | 221 | **121 - 7** | 38k - 188k |
| our half, we open | 157 | 59 - 44 | 112k - 114k |
| neutral, they open | 141 | 84 - 13 | 43k - 144k |
| neutral, we open | 120 | 41 - 34 | 89k - 75k |
| their half, they open | 87 | 37 - 13 | 30k - 76k |
| their half, we open | 187 | 39 - 73 | 126k - 82k |

Our 362 champion deaths (`opener_ctx.py`): the first hit of the fight was a cast in 242 (Stellar 86, HoR 73, Ren 47, Varg 40, Ryth 34, Prism 22,
Marcella 16); our health at that hit was **34% (median)**, 54% below 40%; we died within 2 rounds in 57% of them (first-round damage 33% of max
health, median); 55% had no ally within 6; in the 12 rounds before, 38% were walking, 28% fighting, 15% farming. Yet both teams spend the same
share of field time hurt (below 50% health: 10% vs 9% of body-rounds): **they pick the hurt body and burst it; our hurt bodies stay in the field
near them.** Killer x victim: their Stellar 104, HoR 72 (in 11 games), Ren 49, Varg 43, Marcella 22, Prism 20; our Cassi & Issac 148 of 362 (every
Cassi death with Issac's within 10 rounds), Ryth 57, Varg 52, Stellar 48, Ren 44. Our killers: Ren 53, Stellar 34 (theirs 104: the Power focus).
The two teams without C&I (b6bdb9e4, f8a4f886) beat us 9-1 with 66 deaths against our 179.

## 4. Camps kill 20% of our bodies

93 of 455: Cassi 22, Issac 22, Stellar 20, Ryth 10, Varg 9, Ren 7; 66 with no enemy within 6; median health four rounds before 7%; 30 in rounds
0-200; eight_v3 13, ambush_v3 11, nx100x100 9, nx61x61 7, nx60x60 7, interlock_v3 7, nx50x50 7. Theirs: 42. Under investigation (agent `cd`,
`experiments/wip/x_cd_NOTES.md`).

## 5. Maps

- **nx50x50** (72-1008 vs f8a4f886, 37 deaths; 72-1008 vs Nyx): the only gem group (2 elks + 6 gems = 72 gems) sits midway between the spawns with
  two altars next to it; 27 gold clusters per side. Our draft took the objective team (Prism, Stellar, C&I, Ryth, Tavi; `pd_obj_heavy` passes:
  5,520 health, 2 attackers) and the ring died to the HoR brawl team. Locally the caster team beats our default team there (`_g5os` 0/2 on that
  map vs `_g4`'s casters) but loses 0/2 to the Power / HoR proxy `_pw`.
- **nx61x61** (377-1017, 240-1011; Nyx 3rd loss): the central 1 elk + 8 gem + 12 gold group (71 gems, 396 gold) is killed by whoever chips last and
  **captured by whoever stands on its tile**: game 38998622_01 we dealt 2,850 of 4,460 at r292 and left (Issac to the east at 50% health, Ren
  banking 4 gems at the altar); their Stellar walked 6 tiles onto the tile and took 71 gems at r299; we never captured it in that game (they did 5
  times), b6bdb9e4_05 once vs 3. The group is not an objective (one camp that hits back; `obj_min_attackers` 2). Switches under test: `big_reward`
  40 (+ `reward_pre`, `big_reward_dive`), `obj_min_attackers` 1 with `pd_obj_side` (no caster draft on a central objective).
- contest_v3: 0-1000 with 57 deaths (c47c8c26), 200-1000 with 33 (f8a4f886), 200-0 at r2000 (38998622). eight_v3: 0-1028 (31 deaths), 48-1002 (32).

## 6. What is being measured (ledger, 21 maps, 42 games; vs GOD v2 `_g4` and the Power / HoR proxy `_pw`)

Shipped meanwhile: **GOD v5** = v4 + `burst_retreat` 1.2 (27/40 vs v2; proxies 38 / 33 / 32; vs `_pw` 30/42). Variants: `build_tail` 1 / 2
(28 / 26 of 42, control 28: level, kept as a component), `pd_obj_side` 27, the forced-draft screen (`_d0f` our fixed team 24, `_dh1` HoR, Ren,
Stellar, Ryth, Varg 23, others running; measurement only: the result becomes priors of the parameter draft), `burst_far` 0.5 / 0.8 (the burst
retreat also counts enemies two or three steps from reach), `gold_rank` (a landed reward goes to the best gold user within 5 tiles, not to the
lowest index), `big_reward` 40 variants, `obj_min_attackers` 1. Results in AGENTS.md §S14.8 and SUGGESTIONS.md as they land.
