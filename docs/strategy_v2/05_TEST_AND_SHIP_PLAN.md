# 05. How to test, and when to ship

The repo's sparring results and its ladder results have not agreed: `legend_st` beat its sparring panel 70-97% and
went 1-16 against the top teams. This file sets up tests that are harder to fool, target numbers taken from the top
teams' replays, and ship rules.

---

## 1. Four kinds of test

| Test | What it answers | Opponent model needed? | Cost (2 CPUs) |
|---|---|---|---|
| T1 Unopposed pace | how fast do we farm with nobody in the way | no | ~50 s (34 games) |
| T2 Distinct head-to-head | are we stronger than bot B | yes (B) | ~1.5 min per opponent (82 games) |
| T3 League | are we stronger than a mix of styles, including a top-style bot | yes (several) | ~6 min |
| T4 Ladder KPIs | does it hold against the real top teams | no (real games) | one match group = 5 games, uses the team's quota |

T1 and T4 cannot be fooled by our own blind spots. T2 and T3 are fast filters. A change ships only if it passes
T1-T3 (section 4), and stays shipped only if T4 agrees.

### T1. Unopposed pace

```bash
python3 tools/bench.py BOT idle --maps 'maps/comp/*.map26a' --jobs 2 --release --out /tmp/pace_BOT
python3 tools/strategy_v2/pacesum.py /tmp/pace_legend /tmp/pace_BOT     # mean rounds to 1,000, per map, per champion
```

Current `legend`: **579** rounds on average (per map in 06). Goals: under 520 after Part C, under 500 at the end;
ambush under 550 (now 708), pilgrimage under 750 (now 891).

### T2. Distinct head-to-head

```bash
python3 tools/bench.py A B --maps 'maps/comp/*.map26a,maps/gen*.map26a' --jobs 2 --release --out /tmp/h2h_A_B --quiet
python3 tools/strategy_v2/h2hsum.py /tmp/h2h_A_B          # official / generated / all, deaths, skipping maps/ladder copies
```

**Do not add `maps/ladder/`**: most of its maps are exact copies of official maps and replay identically, so they
count the same game twice. 17 official + 24 generated maps x 2 sides = 82 distinct games. With 82 games one result
moves about +-5.5 points by chance (one standard deviation), so read the win rate together with deaths, gems and the
per-map list, and repeat a close call against a second opponent.

### T3. League

| Opponent | What it stands for | How to get it |
|---|---|---|
| `legend` (current submission) | regression check | `bots/legend` |
| `_st` (= `legend_st`, the Oct 17 ladder build) | our older play | unzip `submissions/history/legend_st_20261017.zip` into `bots/_st` |
| `_es2` (= `legend_es2`) | an older, more aggressive family member | unzip `legend_es2_20261017.zip` |
| **`_top`** | the top teams' style | new bot, section 2 |

Score = mean win rate over the four, plus the per-opponent table. A change that wins against our own family but loses
against `_top` is not shipped.

### T4. Ladder KPIs

After each ship, queue match groups against the top 3 teams on maps we choose (5 per group):

```bash
cambc login
cambc ladder                                                       # find the top teams' ids
cambc match-groups create <TEAM_ID> --maps eight,swirl,fragment,expanse,ambush
cambc match-groups show <GROUP_ID>
cambc match-groups download <GROUP_ID> -o groups/<GROUP_ID>
python3 tools/strategy_v2/run_all.py /tmp/report_<GROUP_ID> groups/<GROUP_ID>   # decode + analyze + report.md
```

(The website's "download match group" zip works the same way: pass the zip to `run_all.py`.)

Rotate the maps so all 17 get covered over a few groups, and keep the 5 worst maps (eight, swirl, fragment, collision,
elkring) in rotation as fixed checks.

---

## 2. The top-style sparring bot (`bots/_top`)

A separate, simple bot that plays the way the top teams play in the 15 replays. It is a stand-in, not a copy: we do
not have their code. Write it from `bots/starter-cpp` (not from `legend`, so it does not share our code's habits).
Target size: 600-900 lines.

| Part | Behaviour |
|---|---|
| Draft | 3 picks: Varg, Stellar, Cassi & Issac; 4: + Ryth; 5: + Ren (Tavi on maps where a heavy group holds 40%+ of the gems) |
| Items | one health emblem (Durability-health; Ren and Ryth also Bruiser-health), then Power in the damage stat forever; shop whenever on spawn or dead |
| Farming | each body: the nearest live (or respawning within its travel time) camp group on its own half or neutral, not claimed by an ally (one shared-memory byte per body); Varg prefers multi-camp groups; attack the lowest-health camp (Varg: the camp with most neighbours); capture by standing on a tile; the best converter captures (Varg > Issac > Stellar > Ryth > Cassi > Ren) |
| Recall | after a capture when health < 60% or gold >= 150, if no enemy within 7; any time health < 35% and no enemy within 7 |
| Banking | bag >= 44, or any bag with an altar within 6, or the bag wins the game |
| Fights | attack anything in reach first (melee: attack then move); cast every ready damage spell or stun on the focus target (lowest health in reach, Cassi or Issac preferred); engage enemies within 6 when (our HP x damage) >= 1.2 x theirs counting allies within 4; retreat below 35% health; Varg aims at the enemy with most adjacent enemies |
| Priority | stunners and the champion closest to an enemy act first |

What it is for: (1) a sparring partner that does not dither, stacks damage and hits first, so our fight rules are
tested against that style; (2) a reality check: if this simple bot beats `legend`, our extra complexity is not
helping, and the plan should lean even more on simple rules.

Check that it is realistic before trusting it: its KPIs (deaths, damage per gold, captures per champion, hit-back
share) should look like the top teams' column in section 3, not like ours.

---

## 3. KPIs and targets

All computed from replays by `tools/strategy_v2/analyze.py` + `report.py` (no debug output needed in the bot).

| KPI | Us now (vs top 3) | Top teams | Goal after Part A | Goal at the end |
|---|---|---|---|---|
| Win rate vs top 3 | 2/15 | - | 4/15 | 7/15 |
| Body deaths per game | 11.1 | 4.8 | 8 | 6 |
| Share of hit rounds with no hit back | 0.74 | 0.55 | 0.62 | 0.55 |
| Fight damage ratio (ours / theirs) | 0.47 | - | 0.7 | 1.0 |
| Damage-stat points per 1,000 gold | 20.7 | 31.9 | 21 | 30 |
| Gold earned per game | 2,661 | 5,123 | 3,200 | 4,500 |
| Time alive | 80.5% | 91.0% | 85% | 88% |
| Time on camps (share of alive) | 18.4% | 21.2% | 19% | 22% |
| Camp damage per camp round | 84 | 118.5 | 90 | 110 |
| Gem captures per game | 13.5 | 23.7 | 16 | 20 |
| Respawn wait before first hit (median rounds) | 21 | 14 | 21 | 15 |
| Unopposed pace (T1, mean rounds to 1,000) | 579 | - | 579 | 500 |

A KPI that moves the wrong way is a warning even when the win rate goes up.

---

## 4. Ship rules

A change goes into `submissions/legend.zip` only when all of these hold:

1. **T1:** mean pace not worse than the current build by more than 10 rounds, and no single map worse by more than 60.
2. **T2:** beats the current `legend` over the 82 distinct games (above 50%), with fewer or equal deaths.
3. **T3:** mean over the league not below the current build's, and not worse against `_top` (once `_top` exists).
4. **No faults**, and no new fuel rollovers after round 6 caused by the change (`decode(..., { rollovers: true })`; check
   the round in a trace before blaming the change, see section 5).
5. The zip holds only `src/*.cpp|*.h`; it goes to `submissions/history/` with a row in `submissions/BUILDS.md`.

After shipping: T4 within a day. If the T4 KPIs get worse than the previous build's on the same maps, roll back.

---

## 5. Today's status against these rules

| Build | T1 | T2 vs legend | T3 | Ship? |
|---|---|---|---|---|
| `x_exec` (A1 + A2) | 579, identical to legend (the patch only acts with enemies in sight) | 54.9% (45/82), deaths 611 vs 810 | `_st` 53.7%, `_es2` 73.2% (legend: 54.9%, 56.1%) | **yes**. One note: 2 lost turns after round 6 in 82 games (Issac at r891 and r893, ambush side B; `legend` 0). They come from the existing farming code (Issac was hitting a gem cluster with no enemy near; a fuel floor on the patch's own calls changed nothing, identical games), so the patch is not the cause |
| `build_style 3` alone | 608 (worse, contest +388) | 47% (34 games) | - | no |
| Varg-first draft alone | 593 (worse) | 35% (34 games) | - | no |
| `x_exec` + `build_style 3` | - | 50% (34 games); 44% vs `x_exec` | - | no |

`x_exec` passed T1-T3. The zip is ready: `submissions/candidates/legend_exec_20261018.zip` (checked: it plays the same games
as the tested build). Ship it as `legend_exec` (copy to `legend.zip`, `submissions/history/`, BUILDS row) and queue a match
group against each top team. Separately, look at the farm-scoring fuel on 100x100 maps late in the game (the 2 lost turns above).
