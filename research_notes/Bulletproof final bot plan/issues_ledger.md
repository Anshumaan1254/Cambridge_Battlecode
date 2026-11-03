# Issues ledger of HouseOfCoders' bot (CAMBC 2026a) and v95 on its live games (Nov 3, 13:15Z)

Sources are repo files (paths under /home/claude/cambridge_battlecode). New measurements: experiments/deep_research_nov3/v95/
(out/summary.txt = aggregate.py over the top30_nov3 stream extractors; out/paired.txt; out/ranked_by_version.txt; out/wards.txt).
v95 sample = **50 decoded v95 games** (31 W / 19 L) of 215 v95 games (195 paired unranked 12:45-12:46, 20 ladder games 12:50-13:00). The rest were not downloaded because the budget ran out.
v88 reference = the stream outputs tagged v88 (91-137 games, ~97% losses), so compare like with like (v95 L vs v88 L, and OPP in the same games).

## Q1. Complete issue list, grouped, with status

### Takeaway
About 45 distinct issues have been recorded since October. v95 ships fixes for 12 of them (E1-E3, F1-F5, the Marcella build, cap rank). 4 more are coded but untested (g24_pace, g24_bank_hold, g24_flip_mem, g24_bush_flee); g24_marc_focus and g24_marc_threat are also coded in g23.cpp and off. About 10 are planned but not coded. Many of the user's complaints were measured and "fixed" before, but the fix lost locally.

### Cited Findings
Status key: FIXED-LIVE = in v95; FAILED = tried, measured level or worse; OPEN = no fix tried; CODED = coded but never tested.
**Economy**
- E1 we give up contested big groups at an even contact (isolated flee at adv<1.5, the v27_avoid 12-round ban, the +12 enemy surcharge). v88 took 0.27 of the contested big cycles vs TOP 0.50 / OPP 0.66, and left 35% of 1v1 contacts vs 18%. Fix `g24_hold 1` + `g23_farm 1`: FIXED-LIVE. Earlier tries: `_fight1` (flee less everywhere) −101 vs v75 (FAILED); g19_hold level. — [god24_plan §2 E1](docs/plans/god24_plan.md), [economy REPORT S1](experiments/top30_nov3/economy/REPORT.txt)
- E2 rich groups farmed by one body (join rule; harmless groups never joined): alone on 45% of opening visits to ≥30-gem groups vs 17%. Fix `g24_join 1` + `g24_scarce 1`: FIXED-LIVE. Squads (−53), deathball (−91), open_follow (23/42) and g18_rich (level) all FAILED. — [god24_plan E2](docs/plans/god24_plan.md), [loop_log 03:22Z](experiments/ladder_nov2/loop_log.md)
- E3 no Marcella funnel (captures go to HoR: Marcella 19% vs top 33%). Fix `g24_marc_funnel 3` + `g24_cap_rank 1`: FIXED-LIVE. mi_capture 2 (Oct) was level; anchors / handoff / gold_rank (Oct 20) lost. — [confusion REPORT S2](experiments/top30_nov3/confusion/REPORT.txt), [nemesis REPORT S1](experiments/top30_nov3/nemesis/REPORT.txt)
- E4 gold / items 25-40% behind: a consequence of E1-E3 (shop rules are not a gap). — [economy REPORT S4](experiments/top30_nov3/economy/REPORT.txt)
- E5 enemy farms our half and the middle (3.75 vs 2.33 captures a game on our half). `g24_hold_own` exists, off: CODED (variant), not measured. — [economy S5](experiments/top30_nov3/economy/REPORT.txt)
- Earlier economy items: TOL `g23_tol` −341 → −108 (shelved); `v24_build 31` local +15 / held-out −5, never laddered. — [god24_plan 2.A](docs/plans/god24_plan.md)
**Fights**
- F1 dashers don't dash out of a retreat (HoR 12% vs 70%; the cause is the `strike_dash_hold` 9 bug). `g24_flee_dash 3`: FIXED-LIVE. — [fights REPORT S1](experiments/top30_nov3/fights/REPORT.txt)
- F2 walk-ins into stronger groups (abandon only at R<0.3; rescue counts bodies). `g24_abandon_r 0.67`, `g24_rescue_pw 1`: FIXED-LIVE. The dive filter (−22) FAILED. — [fights S2](experiments/top30_nov3/fights/REPORT.txt)
- F3 deaths ≤40 rounds after respawn (1.49 vs 0.31/g). `g24_fresh 40`: FIXED-LIVE. F4 deaths to enemy-woken camps: `g24_lure 1` FIXED-LIVE; camp zone −57 FAILED. F5 slow answer to a ranged opener: `g24_hit_is_fight 1` FIXED-LIVE. — [fights S3-S6](experiments/top30_nov3/fights/REPORT.txt)
- Rescue of a caught ally (bits 64): the one fight change confirmed on the ladder (v87 +10/250 vs v84). Rescue + commit (bits 192): v86 +6, dropped. strike_first 3: local +89 / +43, ladder **v90 −8** (FAILED). Disengage −22, leave step −106, one-step lost its edge when stacked (all FAILED). — [loop_log 01:15-05:20Z](experiments/ladder_nov2/loop_log.md)
- N1 their Marcella is not our priority target; N2 our model under-rates an itemized Marcella: CODED (`g24_marc_focus`, `g24_marc_threat` in g23.cpp), never tested. N3 filter's locks (`g24_lock_memory`): OPEN, not coded. — [god24_plan N](docs/plans/god24_plan.md)
- Lure / chase into their team (P4): chase veto bit 4 −9 locally, not used; still OPEN. — [agent_fights REPORT P4](experiments/ladder_nov2/agent_fights/REPORT.md)
**Movement / indecision** (user: stutter, back-and-forth, random moves, wasted rounds)
- Oct 24: back-and-forth 37.5 vs 11-15 per 1000 alive body-rounds; idle causes traced. The fz_dead fix went into v14; fz_osc and unstick FAILED. — [21_GOD_V14](docs/strategy_v2/21_GOD_V14.md)
- Oct 27: A-B-A near enemies 95 vs 45-62 per 1000. `g21_lock` −52 / −126 and `g21_noback` −74 / −167 vs the IC clone (FAILED: "largely kiting"). — [29_GOD_V21_TOP3](docs/strategy_v2/29_GOD_V21_TOP3.md)
- Nov 3: S1 flee/farm pacing near enemies (256 wasted rounds/g vs 177 top_L): `g24_pace` CODED. S3 bag holders pacing between farm and a hot altar: `g24_bank_hold` CODED. S4 target flips OPEN/LIVEGRP: `g24_flip_mem` CODED. — [confusion REPORT](experiments/top30_nov3/confusion/REPORT.txt)
- Watchdog / respawn deadlock / capture delay: `g23_watchfix`, `g23_capfix` FIXED (v88; confirmed on the ladder: step-on within 1 round 88% vs 71%). — [v88_bugs REPORT A1-A2](experiments/ladder_nov2/v88_bugs/REPORT.txt)
- X1 camp execution (passive damage, wake-and-leave, wasted travel dashes 11.8 vs 4.8): `commit_keep 1` was never measured; `g24_dash_travel` is not coded. Both OPEN. B3, the idle body beside an island camp (02the_pond), and B4, chipping inside a monolith's range: OPEN. — [draft_bank S3](experiments/top30_nov3/draft_bank/REPORT.txt), [v88_bugs B3-B4](experiments/ladder_nov2/v88_bugs/REPORT.txt)
- High-health recalls (capture recalls) and the recall bait: by design. Cutting them lost (cap_recall_gold 250 −54, chain_farm −94, g17_bait 0 −64). — [29_GOD_V21_TOP3 §6](docs/strategy_v2/29_GOD_V21_TOP3.md)
**Banking / endgame**
- B2 long bag carries (≥20 gems for 150+ rounds: 1.19 vs 0.39/g). Not traced; `g23_bankcap 50` −49 FAILED; `g24_bank_hold` CODED. X2, a winning bag recalled and never landed: `g24_bank_fallback` OPEN (not coded). Banking like with like is level (not a gap). — [v88_bugs B2](experiments/ladder_nov2/v88_bugs/REPORT.txt), [draft_bank S5, N1](experiments/top30_nov3/draft_bank/REPORT.txt)
**Items / draft / maps / wards**
- Marcella built 0% focus vs 74% for the top-30. `v24_build 4`: FIXED-LIVE. HoR / Ryth buy Jungle-hp first (ECON first in 25% / 10% vs 50-69%): `g24_build_econ` OPEN. v23_build kit orders: ladder v89 −10 (FAILED). — [bush_emblem S1, S5](experiments/top30_nov3/bush_emblem/REPORT.txt)
- Draft: our main roster is the top-30's majority (edge −0.1); `v23_draft` lost with rescue (−44 / −49). Not a gap. — [draft_bank N3](experiments/top30_nov3/draft_bank/REPORT.txt)
- Map classes: scarce maps 43% vs rich 58%, the 10 worst maps 13-26%, bushy maps 46% vs 63%. Monolith maps 57% (not a gap: the "0/33" was a loss-sample artefact). 02the_pack's altar sits inside a wolf ring (not fixed). `g23_spawnfarm` (03homonoliths) is coded but OFF in v95. — [draft_bank S1, S4, N2](experiments/top30_nov3/draft_bank/REPORT.txt), [god23_plan 0b](docs/plans/god23_plan.md)
- Wards: Oct 24 only 6% landed on a bush; `ward_v14` raised that to 36%. Nov 3: 215 wards/g vs 147, bush share 0.41 vs 0.74, 33% near our spawn. `g24_ward_keep` / `g24_bush_ward`: OPEN (not coded). Retreat into a bush (−7 to −12 points of deaths): `g24_bush_flee` CODED. Attacking from bushes: not a gap. — [economy S7](experiments/top30_nov3/economy/REPORT.txt), [bush_emblem S2-S4](experiments/top30_nov3/bush_emblem/REPORT.txt)
**Method**
- M1 local panels don't predict the ladder: v89 +43 → −10, v90 +89 → −8, v92 +97 → −10, **v95 +133 → −1**. M2 the decoded samples are loss-heavy. M3 paired tests have low power (±12 net flips per 150 games). The inert check is not exact on fuel-limited maps (17/86 differ). — [god24_plan M](docs/plans/god24_plan.md), [loop_log](experiments/ladder_nov2/loop_log.md)

### Inferences
- Only three changes were measured as gains on the ladder: rescue (v87), capfix / watchfix (v88), and v85's base (+7/150 vs v84). Every v89-v95 candidate came out level or negative on paired games.

### Gaps
- The archive (S1-S15) and SUGGESTIONS.md predate patch 2.0.0 and were skimmed only. The god22_plan phases (Ryth stuck, coverage wards, "never alone") were not executed.

## Q2. Which fixes were ladder gains, which were level, which lost?

### Takeaway
Gains: rescue (v87 +10/250 vs v84) and capfix / watchfix (v88 +13/250 vs v84). Level: v86, v91, v94 and v95. Lost: v89 (builds) −10, v90 (strike_first) −8, v92 (v85 base + v88 switches) −10.

### Cited Findings
- Paired on the same 195 games (39 groups of paired_c10): v95 101 vs v88 102 (flips 27 / 28, net −1), v94 103/190 (net −4), v84 93 (net +8, p 0.35), v92 net +8. — [out/paired.txt](experiments/deep_research_nov3/v95/out/paired.txt)
- Ranked by live version (Elo expectation at 1979): v84 321/630 (exp ~51.6%), v85 68/115 = 59.1% (exp 48.7%, the best), v87 24/45, v88 92/185 = 49.7% (exp 87.0/180), v94 30/60 (exp 29.6), v95 4/10 (exp 5.1). — [out/ranked_by_version.txt](experiments/deep_research_nov3/v95/out/ranked_by_version.txt)

### Inferences
- Since v85 no version shows a ladder edge. The task's "v88 = games before 12:45Z" is wrong: v94 was live 10:26-12:45Z.

### Gaps
- The opponents' bots change between paired runs, which confounds the paired comparisons.

## Q3. v95 on its live games: results and which shortcomings still show (n = 50 decoded v95 games)

### Takeaway
v95's mechanisms changed a lot: deaths, walk-ins, the respawn deaths, the HoR dash, the Marcella share and the opening economy all moved to or past OPP. Results did not move: paired level with v88 (101 vs 102 of 195), ranked 4/10. Three gaps remain: farming through contact (E1), pacing loops near enemies and groups, and carried-bag losses.

### Cited Findings (v95 we | v95 OPP | v88 we, loss-heavy | v88 OPP; from out/summary.txt)
- Banked 860 | 666 (margin +194); in losses 655, margin −370 (v88 losses 489, −485).
- Deaths/g 3.84 | 8.96 | 10.65 | 6.40 (v95 losses 5.89). Walk-in deaths 2.60 (v88 6.15). Respawn ≤40 r deaths 0.20 (v88 1.56). Enemy-woken camp deaths 0.50 (v88 0.73; OPP 0.30). Killed by their Marcella 0.92 (v88 3.34). Steps toward at R<0.67 with ≥ bodies 12.1/g (v88 32.6; v95 losses 19.8).
- F1 dash on retreat with the dash ready: all 71.6% (v88 37.0%), HoR 58.8% (v88 12.0%; OPP 75%), Vesper 93%, Vendetta 76%.
- E3: Marcella capture share 32.0% (v88 19.0%, OPP 23.9%); HoR 17.6% (v88 24.9%). Marcella focus share of her first 20 shards 0.70 (v88 0.00; OPP 0.50).
- E2 / economy: gems by r150 90.7 vs OPP 79.4 (v88 65.9); by r300 196 vs 173 (v88 142). Alone on ≥30-gem opening visits 8.3% (v88 25.8%, OPP 15.5%). Gold income /100r r401-800: 625 vs 482.
- E1 still open: hit% with an enemy within 6 is 6.3 / 6.2 / 5.3 / 3.9 by phase vs OPP 11.1 / 7.9 / 8.1 / 8.2 (v88 3.0-3.5).
- Wasted loops/g (v95 | OPP | v88): ENEMY12 130.9 | 109.8 | 149.1; ENEMY6 85.7 | 64.5 | 107.0; BAG 14.8 | 4.5 | 18.9; **LIVEGRP 25.1 | 17.1 | 19.2 and DEADGRP 30.4 | 15.0 | 22.7 (worse than v88: new)**. aba_pure 58.9 | 49.0 | 61.6; wasted travel dashes 12.8 | 7.1 | 12.0 (no change).
- **New / worse**: gems lost on death 110.9/g vs OPP 150.7 (v88 63.2) and deaths with a bag ≥40 0.50/g (v88 0.47). Passive camp damage in wins 5,193/g (all 4,128 vs OPP 2,289).
- Wards: v95 227/g, 0.36 on a bush, 0.32 near our spawn = v88 (214, 0.40, 0.33). X3 unchanged. — [out/wards.txt](experiments/deep_research_nov3/v95/out/wards.txt)
- HoR's first emblem is ECON in 3% of games, Ryth's in 0% (OPP 62-69%): unchanged. — [out/summary.txt](experiments/deep_research_nov3/v95/out/summary.txt)

### Inferences
- The god24_plan mechanisms worked as designed but did not turn into ladder wins. The gem lead per game is mostly in won games; in losses v95 is still −370.

### Gaps
- n = 50 of 215 decoded, so per-champion numbers are ±30%. v95 is only 10 ranked games so far. The contested-cycle capture share (objectives extractor) and bag-carry episodes were not run on v95.

## Q4. Top remaining issues by estimated cost

### Takeaway
1. E1, farming through contact (hit% under contact about 60% of OPP's; about +40 gems/g in the plan's estimate).
2. Pacing loops near enemies and groups (ENEMY + LIVE/DEADGRP: ~70 more wasted rounds/g than OPP, ~5-9 gems/g; `g24_pace` / `g24_flip_mem` are coded).
3. Bag exposure: BAG pacing and gems lost on death (`g24_bank_hold` coded; `g24_bank_fallback` not coded).
4. Small items: front-line ECON emblems, wards, wasted dashes, bush retreats (each 0-10 gems/g).

### Cited Findings
- The estimates are from [god24_plan 2.B](docs/plans/god24_plan.md) and [confusion REPORT S1-S4](experiments/top30_nov3/confusion/REPORT.txt), applied to the v95 deltas above.

### Inferences
- Given M1 / M3, the next candidate should bundle the coded pace / flip / bank_hold switches and be judged on a paired run, not on the local panel.

### Gaps
- No ladder-cost estimate exists for the LIVEGRP / DEADGRP rise. It may come from g24_join's bodies converging on groups; this has not been traced.
