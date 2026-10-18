# 06. Tests run on 18 Oct 2026

Local engine cambc 2.2.5 (engine 0.0.3), release builds (`--release`), 2 CPUs. All bots built from this branch.
Raw outputs are not committed (they are large); every command below re-creates them.

Opponents and maps:

- `legend` = `bots/legend/src` = `submissions/legend.zip` (the zip differs only by two switches that are off).
- `_st` = `submissions/history/legend_st_20261017.zip`, `_es2` = `legend_es2_20261017.zip` (older shipped builds).
- "Official" = the 17 maps in `maps/comp/`; "generated" = the 24 `maps/gen*.map26a`. Both sides of each map.
  `maps/ladder/` was **not** used for the final numbers: its maps are copies of official maps and gave identical
  games (checked: e.g. `lad_30x30_R_c5_57b7a2` = elkring, `lad_41x41_V_c3_5ca980` = collision,
  `lad_50x50_R_c5_65bb75` = contest, same rounds, gems and deaths), so they count a game twice.

---

## 1. Unopposed pace (each bot alone against `idle`, official maps, 34 games)

Mean rounds to reach 1,000 gems (lower is better), per map average of both sides.

| Bot | Mean | ambush | collision | contest | corners | eight | elkring | expanse | fragment | interlock | lanes | monolith | packs | pilgrimage | rows | rushbait-v2 | stampede | swirl |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `legend` | **579** | 708 | 583 | 1074 | 394 | 426 | 466 | 616 | 581 | 558 | 490 | 451 | 394 | 891 | 422 | 640 | 771 | 380 |
| `build_style 3` (top-team builds) | 608 | +30 | -24 | +388 | +2 | -8 | +10 | +52 | -5 | -8 | +16 | -48 | +10 | -28 | +18 | +60 | +62 | -42 |
| `build_style 4` (Monster, then Power, no health) | 673 | +76 | -58 | +926 | -19 | +30 | -12 | -2 | +9 | +46 | -16 | -46 | -1 | -54 | -8 | +286 | +470 | -29 |
| `max_trips = 1` | 595 | +142 | 0 | +256 | +13 | -6 | +32 | +12 | -12 | -36 | -6 | -44 | -4 | -106 | +10 | +104 | -38 | -52 |
| `cast_en_route = 0` | 617 | +255 | +8 | +78 | +24 | +20 | -4 | +72 | +8 | +36 | +17 | -7 | -12 | +78 | +25 | +129 | -36 | -46 |
| `early_tribute_min = 34` | 588 | +80 | -23 | 0 | +2 | +19 | +1 | +83 | -5 | -38 | -8 | +15 | 0 | -73 | +10 | +90 | 0 | 0 |
| Varg-first draft (Varg, Stellar, C&I, Ryth, Ren) | 593 | +22 | +34 | +10 | +30 | +12 | +50 | -20 | -5 | +44 | +38 | +39 | 0 | -10 | +43 | -2 | -2 | -45 |
| `x_exec` (fight patch) | 579 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

What it says: no single setting makes farming faster. The builds without health break the objective maps (contest
never finishes with `build_style 4`). Chip damage on the way (`cast_en_route`) pays: without it the mean is 38 rounds worse (ambush +255). The fight patch does not touch
farming (identical games when no enemy is in sight). Gold per champion in the `legend` pace runs: Ren 1,660,
Stellar 1,157, Varg 846, Issac 705, Cassi 584, Ryth 546 (Ren collects shared groups as body 0).

Where the walking goes, `legend` alone (replays decoded with `decode_dmg.mjs`): ambush 74% of body-rounds walking,
13.8% on camps (Ryth 0 gem captures in 749 rounds); corners 46.7% / 29.2%; elkring 42.1% / 29.6%; expanse 51.8% /
26.0%; monolith 53.5% / 27.6%.

Commands:

```bash
python3 tools/bench.py legend idle --maps 'maps/comp/*.map26a' --jobs 2 --release --out /tmp/pace/legend --quiet
SRC=bots/legend tools/variant.sh _vb3 build_style=3          # likewise _vb4 build_style=4, _vtrip max_trips=1,
                                                             # _vroute cast_en_route=0, _vbank early_tribute_min=34
SRC=bots/legend tools/variant.sh _vdraft --define "LEGEND_DRAFT 9,4,3,0,8"
python3 tools/strategy_v2/pacesum.py /tmp/pace/legend /tmp/pace/_vb3 ...
```

---

## 2. Head-to-head, distinct games

`A vs B`: A's win rate; deaths A-B.

### Official maps only (34 games)

| A vs B | Win rate | Deaths |
|---|---|---|
| `build_style 3` vs legend | 47% (16/34) | 502-487 |
| Varg-first draft vs legend | 35% (12/34) | 476-396 |
| `x_exec` vs legend | 56% (19/34) | 366-527 |
| `x_exec` + `build_style 3` vs legend | 50% (17/34) | 427-540 |
| `x_exec` + `build_style 3` + Varg-first vs legend | 47% (16/34) | 421-543 |
| `x_exec` + `build_style 3` vs `x_exec` | 44% (15/34) | 439-558 |

### Official + generated (82 games)

| A vs B | Win rate | Deaths | Gems | Gold |
|---|---|---|---|---|
| **`x_exec` vs legend** | **54.9% (45/82)** | **611-810** | 74.6k-66.2k | 305k-268k |
| `x_exec` vs `_st` | 53.7% (44/82) | 826-835 | 71.7k-71.0k | 296k-293k |
| legend vs `_st` | 54.9% (45/82) | 790-681 | 70.3k-72.0k | 284k-302k |
| **`x_exec` vs `_es2`** | **73.2% (60/82); official 30/34** | **625-991** | 80.3k-62.0k | 333k-259k |
| legend vs `_es2` | 56.1% (46/82); official 25/34 | 818-923 | 73.5k-71.2k | 303k-302k |
| `x_exec` without commitment vs legend | 48.8% | 741-795 | | |
| `x_exec` without hit-first vs legend | 52.4% | 773-749 | | |
| `x_exec` without flee-hit vs legend | 52.4% | 745-802 | | |
| `fight_margin = 1.65` vs legend | 48.8% | 784-726 | | |
| `x_exec` + `fight_margin = 1.65` vs legend | 58.5% | 633-821 | | |
| `x_exec` + `fight_margin = 1.65` vs `x_exec` | 40.2% | 812-685 | | |

One 82-game result moves by about +-5.5 points by chance. `x_exec` is ahead of `legend` against all three opponents
(legend itself scores 50% against itself): mean 60.6 vs 53.7 over {legend, `_st`, `_es2`}. The three parts only work
together (each ablation falls back to ~50%). The last two rows show the usual self-play trap: a change can beat one
opponent by more and lose to another.

Fuel: `x_exec` had 2 lost turns after round 6 in 82 games (Issac at r891 and r893, ambush side B); `legend` had none
in its 82 games against `_st`. The trace shows Issac farming a gem cluster with no enemy within 6 at those rounds, and
a build with a fuel floor on the patch's new calls played the identical 82 games, so the lost turns come from the
existing farming code in that game state, not from the patch. All runs: 0 faults.

Commands:

```bash
cd bots && mkdir _xexec && cp -r legend/src _xexec/ && cp legend/.gitignore _xexec/ && cd _xexec && patch -p1 < ../../experiments/wip/x_exec.patch && cd ../..
python3 tools/bench.py _xexec legend --maps 'maps/comp/*.map26a,maps/gen*.map26a' --jobs 2 --release --out /tmp/h2h/xe_legend --quiet
python3 tools/strategy_v2/h2hsum.py /tmp/h2h/xe_legend
SRC=bots/_xexec tools/variant.sh _xe_nocommit fight_commit=0    # ablations: exec_hit_first=0, exec_flee_hit=0
```

---

## 3. Replay analysis pipeline check

`python3 tools/strategy_v2/run_all.py /tmp/top3 <the three uploaded match-group zips>` re-ran the whole analysis
from the zips in a fresh folder: every table in 01 came out the same (15 games, 7,596-15,312 banked, decomposition
product 0.570, 775 vs 2,181 damage points, 152 fights, 74% / 55% no-hit-back).

## 4. Fight-outcome check

`python3 tools/strategy_v2/fight_model.py <dmg dir> <analysis.json>`: AUC 0.67 for the Lanchester estimate alone, 0.67-0.69
for a 4-feature logistic regression (cross-validated, grouped by match; the range is the fold split); in fights the estimate puts at 0 to +0.5
(log), we still lose more bodies 56% of the time. Details in 04 section 4.

## 5. Map planner

`python3 tools/strategy_v2/map_plan.py <map dumps>` over the 17 official maps (dumps from `tools/replay/mapinfo.mjs`):
zones, circuits and types for each; draft-memory size 22-66 bytes. Output in `data/map_plans_17.txt`.
