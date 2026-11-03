# Issues ledger of HouseOfCoders' bot (CAMBC 2026a) and v95 on its live games (Nov 3, 13:35Z)

All sources are repo files (paths relative to /home/claude/cambridge_battlecode). The new v95 measurements are in experiments/deep_research_nov3/v95/:
- out/summary.txt: aggregate.py = the top30_nov3 extractors fights/extract2, execution/metrics, confusion/flips and economy/econ, run per game by run_all.py.
- out/obj.txt: objectives/extract_obj.
- out/paired.txt, out/classes.txt, out/ranked_by_version.txt, out/bags.txt, out/wards.txt.

**v95 sample:** 225 games were played with v95 live: 195 paired unranked (39 groups, 12:45-12:46Z), ranked 12:50 / 13:00 / 13:12, and unranked 12:54 / 12:56. Results cover all of them; the behaviour metrics cover the **167 decoded (82 W / 85 L)**. The 12:51:21 DOOMSDAY group is excluded (v94 or v95 live, unclear).

**v88 reference:** the streams' v88 rows (91-188 games, ~97% losses). So the like-with-like reads are "v95 L vs v88 L" and "v95 L vs the winners in those same games (OPP-W)".

**Caution:** an earlier draft built on the first 50 decoded games (31 W) looked much rosier. That sample was win-heavy; the n=167 numbers below supersede it.

## Q1. Complete issue list, grouped, with status

### Takeaway
About 45 issues have been recorded since October.
- **In v95 (12):** E1-E3, F1-F5, Marcella focus build, capture rank.
- **Coded, never tested (6):** g24_pace, g24_bank_hold, g24_flip_mem, g24_bush_flee, plus g24_marc_focus and g24_marc_threat (both implemented in g23.cpp, off).
- **Planned, not coded (~8):** g24_bank_fallback, g24_ward_keep, g24_bush_ward, g24_dash_travel, g24_lock_memory, g24_build_econ, g24_carry_cap, g24_bush_wait.
- **Tried and failed:** most of the user's older complaints (stutter, high-health recalls, wards, monoliths). Each fix was measured and lost locally.

### Cited Findings
Status: LIVE = in v95; FAILED = measured level or worse; OPEN = no fix tried; CODED = switch exists, never measured.

**Economy**
- **E1** we give up contested big groups at an even contact. Three rules do it: the isolated flee (adv<1.5), the v27_avoid 12-round ban, and the +12 enemy surcharge.
  - v88: captured 0.27 of the taken contested cycles vs TOP 0.50.
  - LIVE `g24_hold 1` + `g23_farm 1`. Blanket flee-less `_fight1` −101 vs v75 (FAILED). — [god24_plan E1](docs/plans/god24_plan.md), [economy S1](experiments/top30_nov3/economy/REPORT.txt)
- **E2** rich groups farmed by one body (the join rule). LIVE `g24_join 1` + `g24_scarce 1`. FAILED before: squads −53, deathball −91, open_follow 23/42, g18_rich level. — [god24_plan E2](docs/plans/god24_plan.md), [loop_log 03:22Z](experiments/ladder_nov2/loop_log.md)
- **E3** no Marcella funnel: her capture share was 19% vs the top-30's 33%. LIVE `g24_marc_funnel 3` + `g24_cap_rank 1`. FAILED before: mi_capture 2 (level), anchors / handoff, gold_rank. — [confusion S2](experiments/top30_nov3/confusion/REPORT.txt), [nemesis S1](experiments/top30_nov3/nemesis/REPORT.txt)
- **E4** gold / items 25-40% behind: a consequence of E1-E3, not a shop-rule gap. — [economy S4](experiments/top30_nov3/economy/REPORT.txt)
- **E5** the enemy farms our half (3.75 vs 2.33 captures/g). CODED `g24_hold_own`, never measured. — [economy S5](experiments/top30_nov3/economy/REPORT.txt)
- TOL `g23_tol` −341 → −108 after 16 fixes: shelved. `v24_build 31`: local +15 / held-out −5, never laddered. — [god24_plan 2.A](docs/plans/god24_plan.md)

**Fights**
- **F1** dashers don't dash out of a retreat (HoR 12%). LIVE `g24_flee_dash 3`. — [fights S1](experiments/top30_nov3/fights/REPORT.txt)
- **F2** walk-ins into stronger groups (abandon only at R<0.3; rescue counts bodies). LIVE `g24_abandon_r 0.67`, `g24_rescue_pw 1`. Dive filter −22 FAILED. — [fights S2](experiments/top30_nov3/fights/REPORT.txt)
- **F3** deaths ≤40 r after respawn: LIVE `g24_fresh 40`. **F4** enemy-woken camps: LIVE `g24_lure 1` (camp zone −57 FAILED). **F5** slow answer to a ranged opener: LIVE `g24_hit_is_fight 1`. — [fights S3-S6](experiments/top30_nov3/fights/REPORT.txt)
- Rescue (bits 64) is the one fight change ladder-confirmed (v87 +10/250 vs v84).
  - FAILED: rescue + commit (v86 +6, dropped); strike_first 3 (local +89 / +43, ladder **v90 −8**); disengage −22; leave step −106; one-step +53 alone but lost when stacked. — [loop_log](experiments/ladder_nov2/loop_log.md)
- **N1 / N2** their Marcella is not our priority target, and our model under-rates an itemized Marcella: CODED (`g24_marc_focus`, `g24_marc_threat`).
- **N3** filter's altar locks: OPEN (`g24_lock_memory`, not coded).
- **P4** chasing into their team (lure): chase veto bit 4 −9, OPEN. — [god24_plan N](docs/plans/god24_plan.md), [agent_fights P4](experiments/ladder_nov2/agent_fights/REPORT.md)

**Movement / indecision** (the user's stutter, back-and-forth, random moves, wasted rounds, per-champion priorities)
- Oct 24: back-and-forth 37.5 vs 11-15 per 1000 alive body-rounds. `fz_dead` fixed one idle cause (v14); fz_osc and unstick FAILED. — [21_GOD_V14](docs/strategy_v2/21_GOD_V14.md)
- Oct 27: A-B-A near enemies 95 vs 45-62 per 1000. FAILED: `g21_lock` −126 and `g21_noback` −167 vs the IC clone (judged "largely kiting"). — [29_GOD_V21_TOP3](docs/strategy_v2/29_GOD_V21_TOP3.md)
- Nov 3 (confusion stream), all CODED, never measured:
  - S1 flee/farm pacing near enemies: `g24_pace`.
  - S3 bag pacing at a hot altar: `g24_bank_hold`.
  - S4 target flips: `g24_flip_mem`.
  - S5: Vesper walks more and captures half as often. — [confusion REPORT](experiments/top30_nov3/confusion/REPORT.txt)
- Fixed in v88 and ladder-confirmed: capture delay `g23_capfix` (step-on within 1 round 88% vs 71%) and respawn blocks / stalls `g23_watchfix`. — [v88_bugs A1-A2](experiments/ladder_nov2/v88_bugs/REPORT.txt)
- OPEN:
  - X1 camp execution: `commit_keep 1` was never measured and `g24_dash_travel` is not coded.
  - B3: a body idles beside an island camp (02the_pond).
  - B4: chipping inside a monolith's range. — [draft_bank S3](experiments/top30_nov3/draft_bank/REPORT.txt), [v88_bugs B3-B4](experiments/ladder_nov2/v88_bugs/REPORT.txt)
- High-health capture recalls and the recall bait: by design. Every cut lost (cap_recall_gold 250 −54, chain_farm −94, g17_bait 0 −64). — [29_GOD_V21_TOP3 §6](docs/strategy_v2/29_GOD_V21_TOP3.md)

**Banking / endgame**
- Long bag carries (≥20 gems for 150+ r: 1.19 vs 0.39/g): not traced. `g23_bankcap 50` −49 FAILED; `g24_bank_hold` CODED.
- **X2** a winning bag that never lands: `g24_bank_fallback` OPEN, not coded.
- Banking like with like: level, not a gap.
- Oct 24 complaint, "carriers walk away from the altar": measured at the ladder rate overall; the bad cases are map-specific. — [v88_bugs B2](experiments/ladder_nov2/v88_bugs/REPORT.txt), [draft_bank S5 / N1](experiments/top30_nov3/draft_bank/REPORT.txt), [21_GOD_V14 §1](docs/strategy_v2/21_GOD_V14.md)

**Items / draft / maps / wards / monoliths**
- Marcella built 0% focus vs 74%: LIVE `v24_build 4`.
- HoR / Ryth buy Jungle-hp first: `g24_build_econ` OPEN.
- Kit build orders `v23_build`: **ladder v89 −10** (FAILED). Damage-first builds (Oct 19) were slower. — [bush_emblem S1, S5](experiments/top30_nov3/bush_emblem/REPORT.txt), [SUGGESTIONS s13](SUGGESTIONS.md)
- Draft: our main roster is the top-30's majority (edge −0.1). `v23_draft` with rescue −44 / −49. Prism / Willow / C&I swaps all lost (Oct). Not a gap. — [draft_bank N3](experiments/top30_nov3/draft_bank/REPORT.txt)
- Map classes (ranked): scarce maps 43% vs rich 58%; the 10 worst maps 13-26%; bushy maps 46% vs 63%. Monolith maps are 57%, our better class. — [draft_bank S1, S4, N2](experiments/top30_nov3/draft_bank/REPORT.txt)
- Monoliths: Oct 24, our solo plan never targeted them (WHY 7). `mono_v14` lost; kills rose anyway as deaths fell.
- 03homonoliths: `g23_spawnfarm` exists but is OFF in v95.
- 02the_pack: the only altar sits inside a wolf ring; not fixed. — [21_GOD_V14](docs/strategy_v2/21_GOD_V14.md), [god23_plan 0b](docs/plans/god23_plan.md)
- Wards:
  - Oct 24: 6% landed on a bush; `ward_v14` raised that to 36%.
  - Nov 3: 215 wards/g vs 147, bush share 0.41 vs 0.74, 33% within 8 of our spawn. `g24_ward_keep` / `g24_bush_ward` OPEN.
  - Retreating into a bush is worth −7 to −12 points of deaths: `g24_bush_flee` CODED.
  - Attacking from bushes and being ambushed: not gaps. — [economy S7](experiments/top30_nov3/economy/REPORT.txt), [bush_emblem S2-S4](experiments/top30_nov3/bush_emblem/REPORT.txt)

**Method**
- M1 local panels don't predict the ladder: v89 +43 → −10, v90 +89 → −8, v92 +97 → −10, **v95 +133 local → −1 paired**.
- M2 decoded samples are loss-heavy (the monolith false alarm).
- M3 paired tests have low power (±12 net flips per 150 games).
- The inert check is not exact on fuel-limited maps (17/86).
- The null control moves ±41-50 gems locally.
- Results are non-transitive (strike_first, _F4).
- Paired runs are hours apart, so the opponents' bots may change in between. — [god24_plan M, §0](docs/plans/god24_plan.md), [29_GOD_V21_TOP3 §6](docs/strategy_v2/29_GOD_V21_TOP3.md)

### Inferences
- The pre-patch history (SUGGESTIONS.md, AGENTS archive S1-S15) is a long list of reasonable ideas that lost locally. The current lineage has only three ladder-measured gains (rescue, capfix / watchfix, v85's base).

### Gaps
- The archive was only skimmed. The god22_plan phases 6-9 (Ryth stuck, coverage wards, "never alone", lure & farm) were never executed, so there are no measurements for them.

## Q2. Which fixes were measured as ladder gains, level, or losses?

### Takeaway
- **Gains:** rescue (v87 +10/250 vs v84) and capfix / watchfix (v88 +13/250 vs v84, +3 vs v87). v85's base was +7/150 and is the best ranked performer.
- **Level:** v86 and v91, plus v94 and v95 relative to v88.
- **Lost:** v89 builds −10, v90 strike_first −8, v92 −10.

### Cited Findings
- Paired, the same 195 games (39 groups of paired_c10):
  - v95 101 vs v88 102 (flips 27/28, net −1).
  - v94 103/190 (net −4).
  - v84 93 (net +8, p 0.35); v92 net +8; v89 / v90 net +6. — [out/paired.txt](experiments/deep_research_nov3/v95/out/paired.txt)
- Paired, by map class (v95 / v88 / v94):

| class | v95 | v88 | v94 |
|---|---|---|---|
| scarce | 44/104 = 42% | 48 (46%) | 51/102 (50%) |
| rich | 57/91 = 63% | 54 | 52/88 |
| 10 worst maps | 6/18 | 8/18 | 6/18 |
| monolith | 37/58 | 33 | 34/57 |

  `g24_scarce` did not help on scarce maps. — [out/classes.txt](experiments/deep_research_nov3/v95/out/classes.txt)
- OneTap ("easy", 79% ranked): v95 0/5 on the same maps where v94 went 5/5 (v88 1/5). This may be an opponent update; the runs were 1 h apart. — [out/paired.txt](experiments/deep_research_nov3/v95/out/paired.txt)
- Ranked by live version (Elo expectation at 1979, from the Nov 3 ratings):

| version | ranked | win% | Elo-expected |
|---|---|---|---|
| v84 | 321/630 | 51% | ~51.6% |
| v85 | 68/115 | 59.1% | 48.7% (best) |
| v88 | 92/185 | 49.7% | 87.0/180 |
| v94 | 30/60 | 50% | 29.6 |
| v95 | 4/15 | — | — |

  v95's 15 ranked games: janestreethireusplease 3/5, 天天开心 :( 1/5, bentheboss 0/5 at 13:12 (expectation ~5.1 for the first 10). — [out/ranked_by_version.txt](experiments/deep_research_nov3/v95/out/ranked_by_version.txt)

### Inferences
- No version since v85 shows a ladder edge.
- The task brief's "v88 = Nov 3 games before 12:45Z" is wrong: v94 was live 10:26-12:45Z. v88 was live 02:52-10:26Z, apart from the test windows.

### Gaps
- n is too small to separate versions: ±12 net flips is the 2-SE noise at ~150-200 paired games.

## Q3. v95 on its live games: what remains, what improved, what got worse (n = 167 decoded: 82 W / 85 L)

### Takeaway
v95's mechanisms move where they were aimed: HoR dashes, Marcella captures, banks and builds focus, and contested cycles are won in wins. **In losses, v95 plays like v88's losses:**
- Deaths: 10.25 vs 10.65.
- Walk-ins: 6.6 vs 6.2.
- Contested captures: 0.29 vs 0.27.
- Contested farming: hit% under contact is 3-4 vs the winners' 8-9.
- Indecision loops: 97 vs 89 per 1000.

On top of that, two things got worse: the opening is slower, and 6 losses came from bags or banking at r2000.

### Cited Findings (from out/summary.txt; v95 L | the winners in those games | v88 L, loss-heavy)
- **Result:** banked 495 | 958 | 489; margin −462 (v88 −485); all v95 games +19.
- **Deaths/g** 10.25 | 6.44 | 10.65.
  - Walk-in deaths 6.59 | 2.41 | 6.15.
  - Within 40 r of respawn 1.24 | 0.29 | 1.56.
  - Enemy-woken camps 0.62 | 0.15 | 0.73.
  - Killed by their Marcella 3.47 | 2.02 | 3.34.
  - Caught, not hitting back 2.76 | 1.15 | 2.15.
  - Steps toward at R<0.67 with ≥ bodies 30.8 | 14.0 | 32.6.
  - **F2-F4 are unchanged in losses.** In wins: deaths 3.4/g, walk-ins 2.2/g.
- **F1 improved (FIXED):** dash used on a retreat with the dash ready, HoR 72.7% (v88 12.0%, winners 69%); Vesper 90%, Vendetta 89%. But caught within 8 r of a retreat at hp<0.5 is 35.2% vs 33.5% (v88) and 28.3% (winners), so it saves no deaths.
- **E3 / build improved (FIXED):**
  - Marcella's capture share 32.0% vs v88 19.0% (winners' 23.7%); her banked share 31.9%.
  - HoR's capture share 18.7% (v88 25%).
  - Marcella's focus share of her first 20 shards 0.78 (v88 0.00, winners 0.60); her first emblem is ECON in 98% of games.
  - Still open: HoR / Ryth first emblem ECON 3% / 0% vs the winners' 66% / 69%.
- **E1 partly improved:**
  - Contested big cycles, share of the taken ones captured: all v95 0.51 vs OPP 0.49 (v88 0.27 vs 0.73); **in losses 0.29**, hit first then lost 0.29.
  - At 1v1 hp≥0.8 contacts, v95 L **left 40%** (v88 31%, OPP 26%). — [out/obj.txt](experiments/deep_research_nov3/v95/out/obj.txt)
  - Hit% with an enemy within 6, by phase: 2.7 / 4.0 / 3.5 / 2.6 vs the winners' 8.0 / 7.8 / 8.7 / 9.1 (v88 3.0-3.5).
- **E2 and the opening: worse (new):**
  - First gem capture r102 overall (OPP r68; v88 r69).
  - Gems by r150 in losses 64 vs the winners' 93 (v88 66).
  - Alone on ≥30-gem opening visits 18% (v88 26%, winners 11.5%).
- **Economy:** gold income /100r in losses 300 / 355 / 393 / 366 vs the winners' 387 / 508 / 653 / 728 (v88 284 / 338 / 353 / 317).
- **Indecision / movement: worse in losses (new):**
  - Wasted rounds outside fights per 1000 alive body-rounds 96.6 (v88 89.2, winners 52.0).
  - ENEMY12 171.5 / g (v88 152, winners 95); OPEN 45 (v88 38).
  - A-B-A 70.4 (v88 61.6, winners 45); wasted travel dashes 12.8 (12.0; winners 6.6).
  - HoR walks 51.8% of its rounds (v88 45.2%, winners 43.7%); Vesper captures 3.5% of its rounds vs 11.0%.
- **Banking / endgame: worse (new):**
  - Long carries 1.06 / g (v88 1.32, winners 0.85); 57 gems carried at the end.
  - **8 of 85 losses went to r2000.** In 3 of them landing the carried bag would have won: 643bea4e 00reverse_spiral 690+91 vs 704; 599c964a 03ultrastarvation 194+34 vs 217; 1d9b0cef 01starvation 524+95 vs 581. In 3 more we **never banked** (0-0 tiebreaks lost carrying 600 / 200 / 200): 4703b682 03homonoliths, 16fe60e0 and b63d17fb 00contest. v88: 1 such case in 121 losses. — [out/bags.txt](experiments/deep_research_nov3/v95/out/bags.txt)
- **Wards:** unchanged (n=44): 227 / g, 0.36 on a bush, 0.32 near our spawn (v88 214 / 0.40 / 0.33). — [out/wards.txt](experiments/deep_research_nov3/v95/out/wards.txt)

### Inferences
- The v95 bundle shifted play in winnable games but not in the games it loses. The paired net of −1 matches that.
- The v95-specific new costs are the slower opening (joining or waiting delays the first capture), more pacing loops, and endgame banking. These may cancel the gains.

### Gaps
- 58 v95 games were not decoded (results counted only).
- The passive camp damage numbers look anomalous at n=167 (OPP 9,402/g) and are not used.
- The tiebreak rule for 0-0 games was not checked in docs/ENGINE_FACTS.md.
- The per-champion "wrong priority" data is shares only; nothing was traced turn by turn.

## Q4. Top remaining issues by estimated cost

### Takeaway (my estimates from the deltas above; ~13 gems per death and 0.135 gems per wasted body-round, from the fights / confusion reports)
1. **Fight deaths in losses:** +3.8 deaths / g vs the winners ≈ 50 gems/g. F2 / F3 did not move in losses, and their Marcella kills 3.5 / g. N1 / N2 are coded and untested.
2. **Farming through contact / contested cycles (E1):** hit% under contact is a third of the winners'. The plan's estimate is ~40 gems/g.
3. **Opening speed:** first capture ~34 rounds late; ~29 gems behind by r150 in losses.
4. **Endgame banking:** 6 of 85 losses (3.6% of all games) lost with a bag or with zero banked. Cheap: `g24_bank_fallback` plus never-banked maps (00contest, 03homonoliths with `g23_spawnfarm`).
5. **Indecision loops:** ~180 more wasted rounds / g than the winners ≈ 12 gems/g. `g24_pace` and `g24_flip_mem` are coded.
6. **Small:** front-line ECON emblems, wards, wasted dashes, bush retreats (0-10 gems/g each).

### Cited Findings
- The gem prices per death and per round come from [fights REPORT](experiments/top30_nov3/fights/REPORT.txt) and [confusion REPORT](experiments/top30_nov3/confusion/REPORT.txt); the deltas are in [out/summary.txt](experiments/deep_research_nov3/v95/out/summary.txt) and [out/bags.txt](experiments/deep_research_nov3/v95/out/bags.txt).

### Inferences
- Item 4 is the cheapest certain gain: about 3-4 games per 100 are lost with a bag or with nothing banked.
- Items 1-3 need tracing in losses: why the F2 / F3 gates do not fire in v95 losses, and why the first capture is late.

### Gaps
- The cost estimates overlap and are not additive. None of them was measured by a ladder A/B.
