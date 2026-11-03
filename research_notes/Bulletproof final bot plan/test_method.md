# Test method: deciding whether a new CAMBC 2026a version is really better

Everything here was computed from the repository data on Nov 3 (12:55–13:20 UTC). No bot was submitted or activated, no match groups were queued, and no local games were run.

Scripts and outputs are in `experiments/deep_research_nov3/method/`:

| Script | Output |
|---|---|
| `ladder_matrix.py` | `out_ladder_matrix.txt`, `ladder_matrix.json` (505 paired ladder games × versions v84–v95, merged from paired_v84_to_v85, cand_*, c2–c10 and the matches_me.jsonl cache) |
| `local_vs_ladder.py` | `out_local_vs_ladder.txt` (54 local variants vs god84 on s4, held-out pools) |
| `power.py` | `out_power.txt` (exact sign-test power, SPRT simulations, ranked noise, margin vs win, transfer regression) |

"pp" means percentage points of win rate. At a 50% base: 1pp = 7 Elo, 3pp = 21 Elo, 5pp = 35 Elo, 10pp = 70 Elo. The gap to rank 30 (2192 − 1979 = 213 Elo) is about 27pp more wins against the same opponents.

## Why did local tests mis-predict the ladder?

### Takeaway
The local panel measures how a variant fares against near-copies of itself. In those games about 46% of results flip whenever any code changes, so they are mostly chaos. The variants we deployed were also selected for their local luck, and the local opponents play differently from ladder opponents. The result: local gains of +5 to +9pp shrank to about 0 on the ladder, and the transfer is statistically far from complete.

The ladder tests are just as weak at the other end. Every version from v85 to v95 is within noise of v84 and of v88, so the ladder cannot tell us which local signal was right.

### Cited findings

**Chaos dominates local games.** Source: [out_local_vs_ladder.txt](experiments/deep_research_nov3/method/out_local_vs_ladder.txt).
- Across 1,431 pairs of local variants on the same 172 s4 games against god84, the median share of games whose result flips is 45.9% (10th–90th percentile 38–52%).
  - Near-identical builds flip less: g23r vs g23rc 9%, g23r vs _rr6 2.9%.
  - Switch no-ops play the same games exactly (_r80 = _rcf = _rcfh = _rpxh).
- On the ladder, the pooled flip rate over 54 version pairs is 29.5%. Most real changes sit at 25–35%; v86 vs v87 is 4.8%. Source: [out_ladder_matrix.txt](experiments/deep_research_nov3/method/out_ladder_matrix.txt).
- Inert code shifts results too. An exact mirror would cancel on every map pair (86/172, margin 0).
  - _85null: +25 (SE 44), 12 of 86 map pairs not mirrored.
  - _hs: +17 (SE 44), 17 of 86 map pairs not mirrored.
- Local noise level:
  - Per-game SD of the gem margin is about 541 gems.
  - A 172-game panel has SE ≈ 41 gems and ≈ 3.8pp of win rate.
  - Across variants, win% ≈ 49.5% + 7.5pp per 100 gems of margin (correlation 0.93).

**Selection and regression to the mean.**
- The SD of variant margins against god84 is 72 gems, against a sampling SE of 41, so the true SD is about 59. Any local leader is therefore inflated by roughly a third. Applying that shrinkage to v95's +133 would give about +89, from my own estimate.
- On the held-out pool, the 12 selected variants fell from a mean of +54 on s4 to +31 (Pearson r = +0.51 between pools, permutation p 0.09).
- The same effect hit the ladder. v88 was kept for its +13/250 against v84 (z 1.39) on paired_c3. Every later candidate (v89–v95) was then compared with v88's results on the same games. Their mean result against v88 was −3.1pp (SE 1.4), which matches v88's panel luck being repaid.
  - Against the unselected v84 column, the same versions average +2.8pp: v85 +2.7, v86 +2.4, v87 +4.0, v88 +5.2, v89 +1.2, v90 +1.2, v92 −0.6, v94 +6.7, v95 +2.7. Each is ±3.2 to 4.4pp, so all |z| < 1.7.
  - The estimated between-version true variance is ≤ 0, so the spread is all noise.

**Local results do not predict ladder results.** Over the 8 versions with both measurements:
- Pearson correlation of the local s4 margin with the ladder effect against v84 is −0.31 (permutation p 0.45). Spearman is −0.40. Using s4 plus held-out margin gives −0.48 (p 0.23).
- Local paired predictions against v88 averaged +4.5pp; the ladder gave −3.1pp (z 3.8). Even after adding back v88's luck (about +2.4pp), local overpredicts by about 5pp (z ≈ 2.6, my estimate).
- A weighted regression of ladder effect on local effect has slope 0.24, 95% CI [−0.65, +1.14]. Source: [out_power.txt §G](experiments/deep_research_nov3/method/out_power.txt).
- Examples (local vs ladder):

  | Version | Local | Ladder |
  |---|---|---|
  | v90 (strike_first) | +8.7pp via god84 games, +89 s4 | −3.7pp vs v88 |
  | v87 | +112 s4, +7pp | +4.0pp vs v84, −1.2pp vs v88 |
  | v92 | +97 held-out | −5.6pp vs v88 |
  | v95 | +8.1pp s4, +8.7pp held-out, deaths 6.3 vs 10.4 | −0.5pp vs v88 (n 185), −2.2pp vs v94 |

**Results are not transitive locally.**
- _g24all: +113 against v88, but +1 against v94.
- strike_first: +89 against god84, but adds nothing against gpta75 (+112 vs v88's +136).
- v88 (_rcf): +6 against god84, but +136 against gpta75 (baseline god84 vs gpta75: +79).

**Ladder opponents play differently from our lineage.** Our numbers first, top teams second:
- Body-rounds hitting a camp with an enemy within 6: 3.3% vs 9.7% (r1–150).
- All bodies on one first group: 12% vs 38%.
- Bodies on the first target: 2.36 vs 3.16.
- Contacts farmed: 26% vs 38%; contacts left: 25% vs 15%.

Sources: experiments/top30_nov3/economy/REPORT.txt and tables.txt §5; objectives/out/stats.txt.

A local opponent that never contests or stacks cannot reward or punish the contest and stacking behaviour that decides ladder games. The deathball proxy was useless: god84 beat pxs_style 3 171/172 (loop_log).

**Outside evidence.**
- Chess engine developers: "Typically, self play (or very similar engine) testing over estimates the rating gain". Self-testing "can make you blind for gaps", and it can underestimate features the old version never exercised. — [talkchess, May 2018](https://talkchess.com/viewtopic.php?p=762630)
- AlphaStar: plain self-play can cycle ("chasing its tail", rock-paper-scissors). Even play against a mixture of all previous strategies was not enough; DeepMind added exploiter agents. — [DeepMind AlphaStar](https://deepmind.google/discover/blog/alphastar-grandmaster-level-in-starcraft-ii-using-multi-agent-reinforcement-learning/)
- Non-transitive cycles are largest at mid-range transitive strength, so populations of opponents are needed. — [Czarnecki et al. 2020, "Real World Games Look Like Spinning Tops"](https://arxiv.org/abs/2004.09468)
- Battlecode practice is informal: "test against older versions", "run scrimmages against other teams". — [Battlecode 2025 postmortem, The Kragle](https://battlecode.org/assets/files/postmortem-2025-the-kragle.pdf)

### Inferences
- Local tests should only check that the mechanism works and that nothing breaks. They should never rank candidates or replace a ladder test.
- A champion's results on the games that selected it are biased upward. Never use them as the baseline for the next candidate.
- With n ≈ 250, the ladder tests had a 95% CI of ±6.7pp, wider than any plausible true difference between versions. The 'mis-prediction' is partly that neither test could see effects of the true size, which is probably ≤ 3pp.

### Gaps
- Ladder gem margins are not recorded in matches_me.jsonl (W/L only), so margin-based ladder power could only be measured locally.
- The ranked cache has almost no ranked games after Nov 3 06:20Z, so the ranked performance of v88 (after 06:20), v94 and v95 could not be measured.

## How noisy is each test and how many games are needed?

### Takeaway
A paired ladder test has per-game variance equal to its flip rate f (≈0.29), against 0.50 unpaired. With f ≈ 0.29, one-sided α 0.05 and 80% power, it needs:

| Gain to detect | Games | Quota-hours (250 games/h) |
|---|---|---|
| +10pp | ~195 | 0.8 |
| +5pp | ~750 | 3 |
| +3pp | ~2,050 | 8 |

The current rule (250 games, KEEP if p < 0.2) sees a +5pp gain only half the time. Ranked performance needs about 1.7 days per version to see +5pp.

### Cited findings (out_power.txt unless noted)

**Pairing.**
- E[p(1−p)] per game = 0.144. That gives a paired variance of 0.288 against an unpaired 0.498, a 42% saving in games.
- 30% of panel games never flip across versions (16% always won, 14% always lost).
- The 5-game group design effect is 0.6–1.3 (≈1), so the game can be the statistical unit. Source: out_ladder_matrix.

**Exact sign-test sample sizes** (80% power, one-sided α 0.05; games, 5 per group):

| Flip rate f | +3pp | +5pp | +10pp |
|---|---|---|---|
| 0.10 | 741 | 268 | 68 |
| 0.20 | 1,434 | 531 | 136 |
| 0.29 | 2,054 | 751 | 195 |
| 0.35 | 2,469 | 902 | 234 |
| 0.46 | 3,225 | 1,175 | 302 |

- Two-sided α 0.05 at f 0.29: 2,591 / 946 / 244 games.
- Unpaired, e.g. two versions' ranked games: 3,435 / 1,237 / 309 games per version.

**Power at today's feasible sizes** (f 0.29, one-sided 0.05):

| Games | +3pp | +5pp | +8pp | +10pp |
|---|---|---|---|---|
| 300 | 0.21 | 0.44 | 0.80 | — |
| 450 | 0.29 | 0.60 | 0.93 | — |
| 625 | 0.37 | 0.73 | 0.98 | — |
| 750 | 0.43 | 0.80 | 0.99 | 1.00 |

- Chance of a net ≥ 0 when the true effect is −3pp: 0.18 at 300 games, 0.09 at 625.

**The current rule** (n 250, f 0.295, KEEP if two-sided p < 0.2):
- P(KEEP) is 0.08 at 0pp, 0.30 at +3pp, 0.52 at +5pp, 0.94 at +10pp.
- With 10 equal candidates, P(at least one false KEEP) = 0.57.
- The SD of the net is 8.6 games, i.e. 3.4pp.

**Ranked performance.**
- About 659 ranked games a day: one 5-game match per 10-minute slot, roughly 6 groups and 30 games an hour.
- Performance-rating SE: 35 Elo (5pp) at 100 games, 20 at 300, 13 at 720 (≈1 day), 7.5 at 2,160.
- The displayed rating (K ≈ 4.6) relaxes in about 151 games (5.5 h) and wanders with a stationary SD of about 20 Elo around true strength.
- Nov 2–3 version windows: v84 254/505, perf 1970 ± 16; v85 66/110, perf 2059 ± 34; the other windows had 5–40 games (± 55–159).

**Per-game measure.** On local pairs, mean z² is 3.42 for gem margin vs 2.52 for win flips (z-score correlation 0.93), so margin carries about 1.6× the effective sample size. On the ladder it needs replay download and decode for each game.

### Inferences
- Paired ladder games are the only affordable instrument for effects of ≤ 5pp. One quota-hour (250 games) has a 95% CI of ±6.7pp.
- Ranked performance is unpaired, confounded by opponent updates and only about 30 games an hour. It works as a guardrail, not as a selector.

### Gaps
- f depends on the change: 4.8% for v86 vs v87 against ~30% typically. The SPRT should estimate s² from its own data.

## Alternatives: SPRT, ranked tracking, targeted maps, proxies, opponent pools

### Takeaway
Use a sequential test (SPRT, as Fishtest, OpenBench and Leela Zero do) on paired ladder games. At the same error rates it stops roughly twice as early as a fixed-n test. Use proxy opponents and targeted maps only for mechanism diagnostics. Use opponent diversity, i.e. fresh panels of real ladder opponents rated at or above our band, instead of self-play.

### Cited findings
- **SPRT practice.**
  - Gainer bounds are [0, 5] Elo for stronger engines and [0, 10] for those under 2500. Non-regression bounds are [−5, 0] and [−10, 0]. α = β = 0.05 gives LLR bounds ±2.94. The Elo estimate an SPRT reports "should not be trusted for accuracy". — [engine testing guide](https://dannyhammer.github.io/engine-testing-guide/print.html)
  - Stockfish uses STC [0, 2] and LTC [0.5, 2.5], with non-regression [−1.75, 0.25]. An SPRT "does not require prior knowledge of how large the sample size should be". — [Chessprogramming wiki: SPRT](https://chessprogramming.org/Sequential_Probability_Ratio_Test)
  - Fishtest runs paired games and a pentanomial model, which gives "a substantial saving of testing resources compared to the trinomial model". Its normalized-Elo bounds make test duration depend only on the bounds. — [Fishtest Mathematics](https://official-stockfish.github.io/docs/fishtest-wiki/Fishtest-Mathematics.html)
  - Leela Zero promoted a network only if "SPRT finds it's 95% confident that the new network has a 55% (boils down to 35 elo) win rate over the previous best". This often took only dozens of games. — [Leela Zero FAQ](https://github.com/frechele/leela-zero/blob/master/FAQ.md)
- **Our SPRT simulations** (paired trinomial, f 0.295, LLR checked every 5-game group, capped at 3,000 games):

  | Test | P(pass) at −3 / 0 / +2 / +3 / +5 / +10pp | Mean games at 0 / +3 / +5pp |
  |---|---|---|
  | [0, 4pp], α 0.05, β 0.10 | 0.00 / 0.05 / 0.42 / 0.71 / 0.97 / 1.00 | 766 / 1,129 / 686 |
  | [0, 5pp], α = β = 0.05 | — / 0.05 / 0.35 / 0.64 / 0.96 / — | 644 / 1,034 / 647 |
  | [0, 5pp], β 0.20 | — / 0.05 / — / 0.48 / 0.83 / — | 341 / 590 / 486 |
  | [0, 3pp], β 0.10 | — / 0.05 / — / 0.82 / — / — | 1,277 / 1,474 / — |

- **Targeted maps.** `cambc match-groups create` accepts `--source-group`, `--maps` (five names) and `--sides` (checked with --help; nothing created). A change that only acts on a share s of maps dilutes the global effect to s × the on-map effect. Map-targeted groups raise power for "does the mechanism win where it acts?" but do not measure the global gain.
- **Proxies and opponent pools.** pxs_style 3 lost 171/172, so a proxy that does not reproduce the top teams' behaviour statistics is worthless as a test opponent.

### Inferences
- A proxy opponent built from our switches is acceptable locally only if it reproduces the measured top-team behaviour statistics: contacts farmed ≈38%, one-group openings ≈37%, bodies per first target ≈3.2. It remains a diagnostic.
- Ranked tracking is the true target metric but costs 1–2 days per version. Keep it as a do-no-harm check.
- Gem margin on the ladder could cut games by about a third, but needs replays and measures gems, not rating. Use it only as a secondary statistic.

### Gaps
- It is not verified whether a ranked match group can be used as a `--source-group`; all existing plans used unranked groups.
- How long a top team's pinned old version stays representative is unknown.

## Protocol: decision rules, sample sizes, schedule

### Takeaway
- **Local mechanism gate → paired ladder SPRT [0, +4pp] on a fresh panel (this decides) → 24-hour ranked guardrail.**
- One cycle per quota-hour gives about 250 paired games an hour with 2 activations.
- Today there is time for one fixed-size test only. The default is to keep v95 unless a candidate clears a pre-set rule.

### Rules
1. **Local gate.** Used to catch faults and disasters, never to rank candidates.
   - 0 faults; fuel p99 at the champion's level.
   - Inert all-off check on all 86 maps: the 3-map check misses the fuel-limited maps.
   - Mechanism metric moves as designed (the capfix-style check).
   - Local win% over s4 + held-out (378 games) not below −8pp (3σ).
   - A local margin is never a reason to deploy.
2. **Fresh panel.**
   - Source groups are recent ranked matches from the last 24–72 h, opponents rated between our rating − 50 and 2250. Drop teams we never beat (2450+); about 30% of the old panel's games never flipped.
   - Champion column:
     - Free for ranked groups the champion itself played (about 144 groups a day).
     - For other groups, queue them while the champion is live. That costs quota only, with no activation.
   - Several candidates may share one champion column.
   - After any promotion, start a new panel. The champion's results on the games that promoted it are biased upward.
3. **Decision: paired GSPRT.**
   - Hypotheses: H0 = 0pp, H1 = +4pp, α 0.05, β 0.10, giving LLR bounds −2.25 and +2.89.
   - Statistic: x_i ∈ {−1, 0, +1} per paired game, m = mean(x), s² = mean(x²) − m². Then LLR = n·δ1·(m − δ1/2)/s² with δ1 = 0.04.
   - Check after every cycle; stop at 2,000 games. If undecided, keep the champion.
   - If several candidates pass on one panel, take the larger net only if the head-to-head z > 1. Otherwise take the smaller change.
4. **Guardrail.**
   - For 24 h after a promotion (about 700 ranked games, SE ≈ 13 Elo), roll back if performance is more than 2 SE below the previous champion's last 48 h (about −32 Elo).
   - Otherwise do not re-test the champion.
5. **Cycle.**
   - Ranked slots are at UTC minute % 10 == 0.
   - Activate the test version right after a slot and queue all 50 groups while it is live (games run within about 1 minute).
   - Re-activate the champion at least 3 minutes before the next slot. ladder_cycle.py already retries 503 errors until slot + 3 min.
   - One 50-group cycle per hour keeps activation incidents to 2 an hour.
6. **Sample sizes and capacity to Nov 18** (about 14.3 days after today 16:30Z).
   - An SPRT takes about 3 quota-hours at 0 or +5pp and about 4.5 h at +2–3pp, plus the champion column when the panel is not free.
   - Running 16 h a day: about 230 quota-hours, enough for roughly 50–70 candidate SPRTs on free panels or 25–35 when the champion column must be paid.
   - Development time is the binding constraint: plan on 2–4 bundled candidates a day, about 30–40 by Nov 18.
   - Bundle related switches into one candidate and test the bundle.

### Today: 13:20 → 16:30 UTC (a new bot must be live by 16:30)
- **Time available.** Three quota-hours remain. With a candidate ready by about 13:40–14:00, the cycles are about 14:00, 15:00 and 16:00 (≤ 150 groups, ≈ 750 games). The 16:00 cycle's games finish by about 16:06, then decide, then activate the final pick in the 16:10–16:20 gap.
- **Candidates.** Test one candidate, not two: two candidates at 375 games each have only about 0.5 power for +5pp.
- **Panel order.**
  1. The 38 paired_c10 groups (v95 and v94 columns already exist). v95 was not selected on these games, so its column is unbiased.
  2. The 39 paired_c9 groups (v94 column; v94 and v95 are level, −4/185).
  3. v95's own ranked groups since 12:52Z (only about 6 per hour, so about 15–20 by 15:40).
  4. If the panel is still short, queue more groups now while v95 is live (champion column, quota only).
- **Decision at about 16:08.**
  - Promote if the GSPRT crosses +2.89 or the one-sided sign test gives p < 0.05. At 750 games that is about 0.80 power for +5pp.
  - If the mandate requires a new bot regardless, deploy the candidate only if the net is ≥ 0 over ≥ 500 games and the local gate passes. That leaves a 9–13% risk of shipping a −3pp version.
  - Otherwise keep v95 live and selected.
- Whatever is selected at 23:59Z is the International Qualifiers entry. After 16:30, change the selection only if a GSPRT passes.

### Gaps
- Nov 18 end time and whether the final tournament uses the ladder's selected version are unknown.
- Whether ranked groups can be source groups needs one test call (user-approved).
