# Test method: deciding whether a new CAMBC 2026a version is really better

Scripts and outputs: /home/claude/cambridge_battlecode/experiments/deep_research_nov3/method/ (ladder_matrix.py → out_ladder_matrix.txt, ladder_matrix.json; local_vs_ladder.py → out_local_vs_ladder.txt; power.py → out_power.txt). "Local" = experiments/ab2 rows; "ladder" = the merged paired plans (505 games × v84–v95) plus matches_me.jsonl.

## Why did local tests mis-predict the ladder?

### Takeaway
There are three reasons. (1) Local games against near-mirrors are mostly coin flips decided by chaos. (2) Local winners are selected, and the champion's ladder column was reused after it had been picked. (3) The local opponents do not play like the ladder opponents. Local gains of +5 to +9pp became about 0 on the ladder. On the ladder itself, v85–v95 cannot be told apart.

### Cited findings
- **Local panels are chaos-dominated.** Across 1,431 pairs of variants played against god84 on the same 172 games, the median flip rate is 45.9% (10th–90th percentile 38–52%). On the ladder it is 29.5%. So almost every local game is a coin flip that any code change re-rolls. — [out_local_vs_ladder.txt §3](experiments/deep_research_nov3/method/out_local_vs_ladder.txt)
- **Local noise level.** The per-game margin has SD ≈ 541 gems. A 172-game panel therefore has SE ≈ 41 gems on the margin and 3.8pp on win%. Each 100 gems of margin is worth about 7.5pp of win%.
- **Inert controls move the score by ±0.5 SE.** _85null scored +25 (12 of 86 map pairs not mirrored); _hs scored +17 (17 of 86).
- **Local margins do not predict the ladder.** Over 8 deployed versions:
  - Pearson correlation of local s4 margin with the ladder effect vs v84 is −0.31 (permutation p 0.45).
  - Spearman is −0.40.
  - s4 plus held-out margin gives −0.48 (p 0.23). — §4
- **Local overpredicts the ladder.** Mean local paired prediction vs v88: +4.5pp. Mean ladder result: −3.1pp (SE 1.4), z 3.8. The weighted regression slope (ladder on local) is 0.24, 95% CI [−0.65, +1.14]. — [out_power.txt §G](experiments/deep_research_nov3/method/out_power.txt)
- **Examples:**
  - v90: +8.7pp locally, −3.7pp on the ladder.
  - v95: +8.1pp (s4) and +8.7pp (held-out) locally, −0.5pp on the ladder over 185 games.
- **Non-transitivity locally.**
  - _g24all: +113 vs v88, but +1 vs v94.
  - strike_first: +89 vs god84, but adds nothing vs gpta75. — §5
- **Held-out pools regress to the mean.** Over 12 variants, s4 and held-out agree only at r = +0.51 (p 0.09). Mean s4 margin +54 falls to +31 held-out. — §6
- **On the ladder, all versions are within noise.**
  - Every net vs v84 or v88 has |z| < 1.7.
  - Versus v84: mean +2.8pp, SD across versions 2.4pp, sampling SE 3.2–5.6pp. The estimated true between-version variance is ≤ 0. — [out_ladder_matrix.txt](experiments/deep_research_nov3/method/out_ladder_matrix.txt), out_local_vs_ladder §4
- **The champion's column was "lucky", which biased later tests.** v88 was kept for its +13 vs v84 (z 1.39) on paired_c3. Candidates v89–v95 were then compared with v88's results on the same games. The mean result vs v88 was −3.1pp, about what regression to the mean predicts. — out_ladder_matrix
- **Ladder opponents behave differently from our lineage.**
  - Hitting a camp with an enemy within 6: 3.3% of body-rounds vs 9.7% for the top teams.
  - All bodies on one first group: 12% vs 38%.
  - Contacts farmed: 26% vs 38%. — experiments/top30_nov3/economy/REPORT.txt; objectives/out/stats.txt
- **Outside evidence.**
  - Chess programmers report that "self play (or very similar engine) testing over estimates the rating gain". It can also miss gaps that the old version never exposed. — [talkchess 2018](https://talkchess.com/viewtopic.php?p=762630)
  - Self-play can cycle in rock-paper-scissors fashion ("chasing its tail"). AlphaStar used exploiter agents and play against past strategies. — [DeepMind AlphaStar](https://deepmind.google/discover/blog/alphastar-grandmaster-level-in-starcraft-ii-using-multi-agent-reinforcement-learning/)
  - Non-transitivity peaks at mid-range strength, so populations of opponents are needed. — [Czarnecki et al. 2020](https://arxiv.org/abs/2004.09468)

### Inferences
- Use local tests only for mechanism checks and to catch disasters, never to rank candidates.
- Never compare a candidate against the panel that was used to select the champion.

### Gaps
- Gem margins on the ladder need replays; matches_me.jsonl has W/L only.
- The ranked cache is incomplete after Nov 3 06:20Z.

## How noisy is each test, and how many games does it need?

### Takeaway
A paired ladder test at a flip rate of about 0.29 needs, per candidate, at 80% power and one-sided α 0.05:

| Effect to detect | Games | Quota-hours |
|---|---|---|
| +10pp | ~195 | 0.8 |
| +5pp | ~750 | 3 |
| +3pp | ~2,050 | 8 |

The current rule (250 games, KEEP if p < 0.2) catches a +5pp gain only half the time.

### Cited findings (all from out_power.txt unless noted)
- **Conversions:** 3pp = 21 Elo, 5pp = 35 Elo, 10pp = 70 Elo. Rank 30 minus our rating = 213 Elo, about 27pp.
- **Exact sign-test sample sizes** (one-sided α 0.05, 80% power):

  | Flip rate f | +3pp | +5pp | +10pp |
  |---|---|---|---|
  | 0.20 | 1,434 | 531 | 136 |
  | 0.29 | 2,054 | 751 | 195 |
  | 0.35 | 2,469 | 902 | 234 |
  | 0.46 (local mirror) | 3,225 | 1,175 | 302 |

  - Comparing two versions without pairing (e.g. their ranked games) needs 1,237 games per version for +5pp.
  - Pairing saves about 42%: per-game variance falls from 0.50 to 0.288, since E[p(1−p)] = 0.144. 30% of games never flip (16% always won, 14% always lost). — out_ladder_matrix
- **Five-game groups act like independent games.** The design effect is 0.6–1.3, so the game can be the unit.
- **The current rule (n = 250, f 0.295, KEEP if p < 0.2):**
  - P(KEEP) is 0.08 at 0pp, 0.30 at +3pp, 0.52 at +5pp and 0.94 at +10pp.
  - If 10 candidates with no real gain are each tested once, P(at least one false KEEP) = 0.57.
  - The SD of the net is 3.4pp, so the 95% CI is ±6.7pp.
- **SPRT on paired games** (trinomial, LLR checked every group):

  | Test | Mean games at true 0pp | at +3pp | at +5pp | P(pass) at 0 / +2 / +3 / +5pp |
  |---|---|---|---|---|
  | [0, 5pp], α=β=0.05 | 644 | 1,034 | 647 | 0.05 / 0.35 / 0.64 / 0.96 |
  | [0, 4pp], α 0.05, β 0.10 | 766 | 1,129 | 686 | 0.05 / 0.42 / 0.71 / 0.97 |
  | [0, 5pp], α 0.05, β 0.20 | 341 | 590 | 486 | 0.05 / 0.27 / 0.48 / 0.83 |

- **Ranked-performance tracking.**
  - Volume: about 659 ranked games a day, about 30 an hour.
  - SE of the performance rating: 35 Elo (5pp) at 100 games, 13 Elo (1.9pp) at 720, 7.5 Elo at 2,160.
  - The displayed rating (K 4.6) lags true strength by about 151 games (5.5 h) and wanders with SD ≈ 20 Elo around it.
  - Each version's Nov 2–3 window gave only 5–110 ranked games (SE 34–159 Elo). The exception is v84: 505 games, perf 1970 ± 16.
- **Gem margin vs win flips (local pairs).** Mean z² is 3.42 for margin vs 2.52 for wins, so margin carries about 1.6× the effective sample. The two z-scores correlate at 0.93.
- **Practice in chess and Go engine testing.**
  - Bounds: SPRT gainer bounds are [0, 5] Elo for stronger engines and [0, 10] for those under 2500; non-regression bounds are [−5, 0] and [−10, 0]. α = β = 0.05 gives LLR bounds ±2.94. The Elo estimate from an SPRT is not accurate. — [engine testing guide](https://dannyhammer.github.io/engine-testing-guide/print.html)
  - Stockfish uses STC [0, 2] and LTC [0.5, 2.5]. — [CPW SPRT](https://chessprogramming.org/Sequential_Probability_Ratio_Test)
  - Pairing games saves "substantial" resources (Fishtest's pentanomial model). — [Fishtest Mathematics](https://official-stockfish.github.io/docs/fishtest-wiki/Fishtest-Mathematics.html)
  - Leela Zero promoted a network only if "SPRT finds it's 95% confident" it wins 55% (about 35 Elo); this often took only dozens of games. — [LZ FAQ](https://github.com/frechele/leela-zero/blob/master/FAQ.md)

### Inferences
- For changes of +3pp or less, the paired ladder test is the only affordable selector. Ranked performance is a slow guardrail.
- Gem margin is not available on the ladder without replays. If decoding is cheap, use it only as a secondary measure.

### Gaps
- The flip rate varies by change: 4.8% for v86 vs v87, ~30% typical. Estimate f per test from its own data.

## Protocol: decision rules, schedule and capacity

### Takeaway
1. A local mechanism check, used as a gate only.
2. A paired ladder SPRT [0, +4pp] on a fresh panel. This is what decides.
3. A 24-hour ranked guardrail after each promotion.

Today, the time to 16:30Z allows one fixed test, not a full SPRT.

### Protocol
1. **Local gate (minutes, not used to rank):**
   - 0 faults; fuel p99 at the champion's level.
   - Inert all-off check on all 86 maps, not just 3: the 3-map check misses fuel-limited maps.
   - Mechanism metric moves as designed (e.g. capfix: uncaptured 30+ rounds dropped 18 → 6).
   - No disaster: local win% over the 378 s4 + held-out games ≥ −8pp, which is 3σ.
2. **Fresh panel.**
   - Source groups are the champion's own last 24–48 h of ranked matches. The baseline column is free, because the champion already played them.
   - Prefer opponents rated between our rating − 50 and 2250, which is the band we must beat to climb. Drop teams we never beat (2450+).
   - Never reuse the panel that promoted the current champion.
   - `cambc match-groups create` accepts `--source-group`, `--maps` and `--sides` (checked with --help), so mechanism-targeted map sets are possible. Use them only for diagnostics, because the effect is diluted by the map share.
3. **Decision: paired GSPRT.**
   - Test H0 = 0pp against H1 = +4pp, with α 0.05, β 0.10 (LLR bounds −2.25 / +2.89).
   - Formula: LLR = n·δ1/s²·(m − δ1/2), where m is the mean net flip per game and s² is the flip rate.
   - Check after every cycle. Truncate at 2,000 games; if undecided, keep the champion.
   - Pass → promote. Fail → discard. Never stop on a p-value.
4. **Guardrail.** For 24 h after a promotion (~700 ranked games, SE ≈ 13 Elo):
   - Roll back if performance is more than 2 SE below the previous champion's last 48 h, i.e. more than about −32 Elo.
   - Otherwise keep the champion and do not re-test it.
5. **Schedule within the ranked rule.**
   - Ranked slots are at :00, :10, … each hour. The quota is 50 groups (250 games) per rolling hour.
   - Run one cycle per hour: activate the test right after a slot, queue all 50 groups, then re-activate the champion at least 3 min before the next slot.
   - This gives about 250 paired games per hour and needs only 2 activations per hour, which limits the risk of 503 errors.
   - An SPRT therefore takes about 3 h at 0pp or +5pp and about 4.5 h at +2–3pp.
6. **Capacity to Nov 18 (~14.5 days).**
   - At 16 h a day: about 230 quota-hours, about 57k paired games, about 50–70 SPRTs.
   - Development time, not quota, is the limit. Plan on 2–4 candidates a day, so 30–50 by Nov 18.
   - Bundle related switches into one candidate rather than testing each switch.
7. **Today (to 16:30Z, about 3 quota-hours).**
   - Run one paired test of the single best candidate vs v95 on a fresh panel: v95's ranked groups since 12:52Z, about 150 groups = 750 games, enough to detect +5pp at 80% power.
   - Promote only if the GSPRT crosses +2.89 or the one-sided sign test gives p < 0.05. Otherwise v95 stays live.
   - Do not deploy on local margins. v94 and v95 are level on the ladder (v95 − v94 = −4/185).

### Gaps
- It is not verified whether a ranked group can be a `--source-group`; the existing plans used unranked groups. If it cannot, the champion column costs quota: run the champion's groups once per panel.
- Opponents update their bots, so a panel older than about 3 days goes stale.
