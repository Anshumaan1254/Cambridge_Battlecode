# Fights and deaths vs the top 10 (session 16, Oct 23)

Why our champions lose fights and die against the top-10 teams, and what the top teams do in fights that we do not.

## Data and method

- **Replays**: 392 of our games vs the top 10: `rp_bb4D` (200, v50) + `rp_ft52D` (192, v52). We won 45 of them. Plus 219 top-vs-top ranked
  games (`rp_top`, 438 team-games). Sides come from `groups_matches.jsonl`, `top10_oct23/*.jsonl`.
- **Exact damage attribution**: `tools/live/fightdump.mjs` decodes each replay once (the same engine path as `decode.mjs`). It records every
  health drop inside the step of the champion or camp that acts, with attacker, victim, amount, attack or cast, and slot. It also records
  stuns, heals and champion damage on camps. I checked 40 games: every champion health drop is attributed, and 613 of 614 deaths have
  their killing hit. This replaces position matching, which misattributed hits. Dumps are in `C:/battlecode/cache/an_fights/dec/`.
- **Analysis scripts** (all new, under `tools/live/`):
  - `fightan.mjs`: deaths, engagements and contacts → `an.jsonl`.
  - `fightfirst.mjs`: lead-up to first strikes and to kills → `ff.jsonl`.
  - `shotdisc.mjs`: action per round with an enemy within 4 → `sd.jsonl`.
  - `fightfollow.mjs`: follow-through after the opener → `fol.jsonl`.
  - `idleallies.mjs`: allies near a death that did not hit → `ia.jsonl`.
  - `rangedseq.mjs`: in-round action order of ranged champions.
  - Aggregators: `fightagg.py`, `fightagg2.py`, `fightagg3.py`, `fightfirst_agg.py`, `shotdisc_agg.py`, `fightfollow_agg.py`.
  - Printed tables: `C:/battlecode/cache/an_fights/agg_*.txt`.
- **Definitions**:
  - **Engagement**: champion-vs-champion damage clustered with gaps of 6 rounds or less, within 10 tiles. We count it if it has 3 or
    more hits or a death.
  - **Starter**: the side whose damage lands first.
  - **Local power**: the max-health sum within 8 tiles of the first hit, at the start.
  - **Contact**: opposing bodies within 4 tiles, with no champion damage within 10 tiles for 8 rounds.
  - **"Them"**: the top teams in our games.
  - **"Top"**: top-vs-top games. Rates are per team-game.
- **Robustness**: both bot versions show the same picture.

  | Metric | bb4D | ft52D |
  |---|---|---|
  | Our deaths per game | 11.1 | 10.7 |
  | Their deaths per game | 6.5 | 6.4 |
  | Contacts where we strike first | 23% | 22% |
  | Contacts where they strike first | 44% | 46% |
  | Engagements they start | 62% | 64% |
  | Our ranged hit share in reach | 28% | 30% |
  | Their ranged hit share in reach | 42% | 44% |

## Headline

1. **The side that lands the first three rounds of damage wins the fight, and the top teams strike first against us twice as often as we
   strike them.**
   - In fresh contacts they strike first 44.6% of the time, we strike first 22.8%, and nobody strikes 32.6%. Between top teams it is
     35.4% each.
   - They start 63% of all engagements: 12.5 a game against our 7.4. Between top teams each side starts 50%.
   - When they start, we lose 0.63 bodies per engagement and they lose 0.23. They still win when our local max health is more than 1.15x
     theirs: our deaths 0.51 vs theirs 0.36.
   - **75% of our deaths come from engagements they started.** For their deaths against us the figure is 54%, and 64% between top teams.
2. **Our ranged champions walk instead of shooting.**
   - With an enemy inside basic range, our ranged champions hit in 29% of rounds. Theirs hit in 43% (vs us) and 45% (top-vs-top).
   - Our Vesper, Tavi and Willow never use the attack reset to shoot after a step: **0 of 10,207 hitting rounds**.
   - Top Vespers do it in 13% of their hitting rounds, and they also shoot and then dash away.
   - Our Vesper dies 2.5 times a game, against 1.2 for theirs vs us and 1.6 between top teams. In 74% of our Vesper deaths it fired no
     shot in the previous 8 rounds; for top Vespers it is 30-33%.
3. **We do not convert the fights we start or win.**
   - After our opener, our bodies walk toward the enemy in 30% of rounds; top starters do it in 19%. Our damage share drops from 0.63 to
     0.44 by rounds +3 to +6. Top starters drop from 0.68 to 0.52.
   - After a won engagement, we farm 4% of the next 15 rounds and make 0.06 captures within 20 rounds. Top winners farm 15-18% and make
     0.37-0.38 captures.

## Q1. Deaths: context and patterns

Deaths per team-game (Cassi and Issac partner deaths not counted twice):

| Group | All | r ≤ 300 | r 300-600 | r 600-1000 | r > 1000 | Bag lost per game |
|---|---|---|---|---|---|---|
| Us vs top 10 (n=4,287) | **10.94** | 2.28 | 2.84 | 3.53 | 2.28 | 93 gems |
| Them vs us (n=2,536) | 6.47 | 1.57 | 1.67 | 1.76 | 1.47 | 94 gems |
| Top vs top (n=3,732) | 8.52 | 1.76 | 2.19 | 2.57 | 1.99 | 162 gems |

**Death patterns.** Each death is classified from the victim's activity over its last 3-5 rounds. "Fighting" means it hit an enemy
champion in its last 3 rounds. "Fleeing" and "approach" mean the majority of its last 5 moves increased or reduced its distance to the
nearest enemy.

Several top bots issue a Recall step every turn while walking or fighting. A Recall or Submit only counts as a channel in a round with no
move or hit.

All rounds, deaths per team-game:

| Pattern | Us | Them vs us | Top | Excess vs them | Excess vs top |
|---|---|---|---|---|---|
| Fight, outnumbered within 6 | 1.85 | 1.69 | 1.72 | +0.16 | +0.13 |
| **Walking into them (approach, no hit in the last 3 rounds)** | **1.77** | 0.38 | 0.85 | **+1.39** | **+0.92** |
| Fight, even or ahead in numbers | 1.71 | 0.99 | 1.26 | +0.72 | +0.45 |
| Fleeing after fighting | 1.16 | 0.91 | 1.09 | +0.25 | +0.07 |
| **Fleeing, no fight** | **1.14** | 0.51 | 0.63 | **+0.63** | **+0.51** |
| Camp kill | 1.13 | 0.94 | 0.99 | +0.19 | +0.14 |
| Fight, even numbers, more than 1.15x weaker | 1.02 | 0.52 | 0.93 | +0.50 | +0.09 |
| Walking, stunned or other | 0.86 | 0.38 | 0.66 | +0.48 | +0.20 |
| Channel (bank or recall) | 0.20 | 0.05 | 0.11 | +0.15 | +0.09 |
| Caught farming or capturing | 0.10 | 0.10 | 0.28 | 0 | -0.18 |

Rounds 300 and earlier, deaths per team-game:

| Pattern | Us | Them | Top |
|---|---|---|---|
| Camp kill | 0.52 | 0.41 | 0.39 |
| Outnumbered | 0.50 | 0.35 | 0.44 |
| Even or ahead | 0.42 | 0.25 | 0.30 |
| Flee after fight | 0.23 | 0.20 | 0.20 |
| Approach | 0.18 | 0.06 | 0.10 |
| Flee, no fight | 0.18 | 0.08 | 0.10 |

The approach gap grows with the game (us / them / top):

| Rounds | Us | Them | Top |
|---|---|---|---|
| 300-600 | 0.40 | 0.09 | 0.20 |
| 600 and later | 1.19 | 0.23 | 0.56 |

**What is not different** (rounds 300 and earlier, excluding camp and linked deaths: us n=691, them n=452, top n=600):

- **Outnumbered within 6** at the death: 48% for us, 47% for them, 48% for top teams. Alone within 6: 32%, 39%, 33%.
- **Burst deaths**: the victim was above 60% health when its fatal damage sequence started in 81% / 75% / 79% of deaths. The sequence
  lasts 8-9 rounds and the enemy had been within 8 tiles for about 23-24 rounds before.
- **Location**: own half 24% / 29% / 24%, middle 60% / 57% / 64%, their half 16% / 14% / 12%. Within 8 of their spawn: 12% for all three.
- **Killers of our bodies**:

  | Killer | Share of our deaths (r ≤ 300) |
  |---|---|
  | Camp | 23% |
  | Vesper | 17% |
  | Marcella | 15% |
  | Heart of Ruin | 15% |
  | Ryth | 9% |
  | Vendetta | 8% |
  | Prism | 8% |

  Every one of our champions dies 2.3-2.9 times a game. Theirs die 1.1-1.7 times against us.

**What is different:**

- **Approach deaths** (n=693, median round 763):
  - Killers: Vesper 31%, Marcella 25%, Heart of Ruin 15%, Prism 13% (ranged and spell kills).
  - Victims: our Vesper 269, Vendetta 141, Heart of Ruin 110.
  - 75% of these victims dealt no damage in their last 10 rounds.
  - Local max-health ratio at the death 0.80. Theirs is 1.18 when they die this way.
- **Victims walk into hits**: our victim was hit while closing on its killer in 53% of our champion kills. Theirs: 30% (vs us) and 37%
  (top). At least 2 rounds of this: 22.5% / 8% / 12%.
- **Victims die without hitting**: our victim landed no hit in its last 8 rounds in 37% of deaths. Theirs: 21% / 28%.
- **Fleeing-no-fight deaths**:
  - Victims: our Vesper 223 of 445.
  - Killers are melee 57% and dash champions 60%.
  - The victim was at 0.73 health when its sequence started.
- **Contested camp kills** (a camp lands the kill while enemy champions are also hitting): 0.63 a game for us, 0.25 for them, 0.34 between
  top teams. 58% of ours happen while moving. Pure camp deaths are not worse: 0.50 for us vs 0.69 / 0.65, but ours carry 26-gem bags,
  which camps destroy.
- **Allies near the victim that did not hit**: a healthy ally within 8 did not hit in the last 5 rounds in 50% of our deaths, against
  42% (them) and 46% (top). Allies were within 8 but none hit in 37% of ours, 28% of theirs and 29% of top deaths.

  The behaviour of those idle allies is the same for everyone: about half were walking toward the victim, arriving too late, and about a
  third were walking away. We simply have more of them: 8.7 a game against 3.8 for them and 6.3 for top teams. **This is a consequence of
  dying more, not a separate cause.**

## Q2. Engagements: who starts, state, execution, outcome

Who starts, by our local max-health ratio at the start (ours / theirs within 8). All rounds, 7,795 engagements (19.9 a game); "per
engagement" columns are bodies lost:

| Starter | Our power | Engagements | Our deaths per engagement | Their deaths per engagement | Net per engagement | Net total |
|---|---|---|---|---|---|---|
| Us | Weaker (< 0.87) | 1,271 (44% of our starts) | 0.50 | 0.35 | -0.15 | -185 |
| Us | Even | 468 | 0.37 | 0.39 | +0.01 | +6 |
| Us | Stronger (> 1.15) | 1,164 | 0.25 | 0.53 | +0.27 | +318 |
| Them | We are weaker | 2,438 (50% of their starts) | 0.73 | 0.14 | -0.59 | -1,431 |
| Them | Even | 747 | 0.57 | 0.21 | -0.37 | -274 |
| Them | We are stronger | 1,700 | 0.51 | 0.36 | **-0.15** | -257 |

The same table for the first 300 rounds (1,703 engagements):

- When we start: net -0.06 if we are weaker, -0.17 at even power, +0.28 if we are stronger.
- When they start: net -0.55 if we are weaker, -0.35 at even power, -0.12 if we are stronger.

**Top-vs-top, starter's view** (4,480 engagements): net per engagement for the starter is -0.05 when weaker, +0.17 at even power and
+0.47 when stronger; +0.21 overall. In the first 300 rounds: +0.03 / +0.09 / +0.32.

Their starts against us are worth about twice a top team's starts against another top team. Ours are worth a quarter: +0.05 per
engagement.

**Execution.** All rounds, A = us; first 300 rounds in brackets where different:

| | We start (n=2,903) | They start (n=4,892) | Top-vs-top starter / other |
|---|---|---|---|
| Starter's damage share, first 3 rounds | 0.70 | 0.83 | 0.76 |
| Starter's damage share, whole fight | 0.57 | 0.72 | 0.63 |
| Bodies hitting or hit by round +5 (us / them) | 1.60 / 1.44 | 1.50 / 1.55 | 1.58 / 1.53 |
| Bodies within 8 at the start (us / them) | 2.02 / 2.04 | 2.11 / 2.08 | 2.10 / 2.19 |
| Focus: share of a side's damage on its most-hit target (us / them) | 0.86 / 0.82 | 0.81 / 0.86 | 0.82 / 0.83 |
| Stuns in the first 3 rounds (us / them) | 0.55 / 0.29 | 0.19 / 0.55 | 0.45 / 0.21 |
| Spell hits in the first 3 rounds (us / them) | 0.72 / 0.36 | 0.23 / 0.85 | 0.82 / 0.32 |
| Spell slots ready at the start (us / them) | 3.09 / 2.53 | 3.00 / 2.83 | 2.93 / 2.79 |
| Spells cast on camps in the 8 rounds before (us / them) | 0.04 / 0.33 | 0.09 / 0.32 | 0.27 / 0.37 |
| First hit is a spell | 51% | 51% | 53% |
| First victim was farming / walking | 19% / 76% | **6% / 91%** | 20% / 75% |

- Numbers, focus fire and ready spells are **not** where we lose.
- Top teams spend spells on camps right before fights and still win. We hold ours and still lose.
- They catch our bodies walking (91%), not farming, because our bodies are almost never on a camp with an enemy near.

**Take vs avoid** (fresh contacts, all rounds, who strikes first within 5 rounds, by side A's local max-health ratio):

| Side A | n | A first, weaker | A first, even | A first, stronger | A first, all | B first, all | Nobody |
|---|---|---|---|---|---|---|---|
| Us | 10,036 | 17.1% | 27.3% | 30.0% | 22.8% | 44.6% | 32.6% |
| Them vs us | 10,036 | 37.7% | 42.5% | 49.5% | 44.6% | 22.8% | 32.6% |
| Top (each side) | 10,886 | 30.7% | 36.6% | 39.7% | 35.4% | 35.4% | 29.2% |

- Top teams are only mildly selective: they strike first 31% when weaker and 40% when stronger.
- Against us they strike first more at every power level (38-50%). We strike first less at every level (17-30%): we "avoid" even when
  stronger.

**How their first strikes happen** (lead-up, all rounds; `fightfirst_agg.py`):

| | They strike us (n=5,270) | Top-vs-top (n=4,981) | We strike them (n=3,147) |
|---|---|---|---|
| Victim stepped toward the attacker in the strike round | **53%** | 38% | 24% |
| Only the victim closed the gap in rounds -3 to -1 | **25%** | 20% | 8% |
| Only the attacker closed the gap | 13% | 25% | **34%** |
| Ranged first hitter did not move | 22% | 19% | **6%** |
| Victim could have struck first from where it stood | 31% | 34% | 44% |
| Starting team acted first in the round | 56% | 56% | 53% |

- **They hold and we walk in.** When we strike, our attacker usually did the walking: only the attacker closed 34%, against 25% for top
  starters, and our ranged first hitters almost never stand still (6%).
- Turn order is not the explanation: the starter's team acted first in 53-56% of rounds in every group.

## Q3. Top vs top: what wins fights and how they convert

**Logistic regression on decisive engagements** (the two sides' deaths differ; 2,258 engagements; standardised coefficients, z in
brackets; pseudo-R² 0.27):

| Factor | Coefficient | Direction |
|---|---|---|
| Current-health ratio within 8 | **+3.00** (z 9.8) | More current health wins |
| Max-health ratio within 8 | **-2.28** (z -7.9) | Given current health, a hurt rich team loses: catch them damaged |
| Damage share in the first 3 rounds | **+1.24** (z 14.9) | Winning the first 3 rounds wins the fight |
| Focus difference | +0.29 (z 4.0) | Focusing one target helps a little |
| Bodies arriving by round +5 | +0.17 (z 2.7) | More bodies arriving helps a little |
| Started the engagement | -0.03 (n.s.) | No effect once early damage is known |
| Stuns in the first 3 rounds | -0.19 (z -2.7) | Slightly negative given early damage |
| Spell hits in the first 3 rounds | -0.11 (n.s.) | No effect given early damage |
| Spell slots ready | -0.17 (z -2.1) | Slightly negative given early damage |

Univariate win rates for the side that is ahead on a factor:

| Factor | Win rate when ahead | Win rate when behind |
|---|---|---|
| First-3-round damage | **75%** | 29% |
| Current health | 73% | 32% |
| Max health | 70% | 35% |
| Started the engagement | 69% | - |
| Spell hits in the first 3 rounds | 67% | 37% |
| Bodies by round +5 | 65% | 43% |
| Stuns | 60% | 47% |
| Raw numbers within 8 | 58% | 47% |
| Focus | 54% | 50% |

The same model on our games (4,150 decisive engagements, we win 35%) has the same structure. Early damage: z 18.7. Current health: z 12.4.
Focus: z 6.5. Bodies by round +5: z 6.0.

**Conversion.** Participants that are still alive, over the 15 rounds after the engagement's last hit:

| Side | Farm | Hit a champion | Move | Moves homeward | Still | Captures within 20 rounds per engagement |
|---|---|---|---|---|---|---|
| Top-vs-top winner | **15%** | 2% | 65% | 34% | 23% | **0.38** |
| Top-vs-top loser | 9% | 3% | 73% | 34% | 18% | 0.07 |
| Them, after beating us | **18%** | 2% | 63% | 34% | 22% | **0.37** |
| Us, after beating them | **4%** | 2% | 79% (47% toward the enemy) | 34% | 17% | **0.06** |
| Us, no kill | 2% | 3% | 86% | 42% | 11% | 0.03 |
| Them, no kill | 10% | 4% | 72% | 38% | 18% | 0.13 |

**Follow-through after the opener.** The opener's participants, rounds +1 to +3, all rounds:

| Starter | Hit | Toward | Away | Farm |
|---|---|---|---|---|
| Top | 37-39% | 19-20% | 17-19% | 3-4% |
| Them vs us | 45-46% | 16-17% | 16-17% | 2-3% |
| Us | 36-39% | **28-30%** | 14-15% | 0.2-0.3% |

Starter damage share by window (rounds 0 to +2, +3 to +6, +7 and later):

| Starter | 0 to +2 | +3 to +6 | +7 and later |
|---|---|---|---|
| Top | 0.68 | 0.51-0.52 | 0.52-0.56 |
| Them vs us | 0.75-0.81 | 0.58-0.59 | 0.60-0.63 |
| Us | 0.62-0.63 | **0.44** | 0.46-0.48 |

Top teams win the opener, keep hitting while the target is in reach, do not chase, go back to camps (even mid-fight: 6% of rounds +4 to
+8) and capture. We chase after our opener, lose the exchange from round +3 and do not farm afterwards.

## Shot discipline: what a body does with an enemy in its basic reach

All rounds. Basic reach is 3 tiles for ranged champions and 2 for melee (step and hit). Shares of rounds:

| Group | Rounds | Hit | Hit and move | Toward | Away | Sideways | Still |
|---|---|---|---|---|---|---|---|
| **Ranged, us** | 31,768 | 28.7% | 0.5% | **14.2%** | **31.8%** | 10.5% | 13.6% |
| Ranged, them | 41,327 | 39.4% | 3.8% | 9.6% | 25.5% | 5.5% | 13.9% |
| Ranged, top | 43,493 | 41.1% | 3.6% | 7.7% | 24.7% | 5.4% | 14.9% |
| Melee, us | 79,087 | 20.5% | 34.4% | 8.0% | 17.7% | 6.4% | 12.7% |
| Melee, them | 67,445 | 19.6% | 41.1% | 6.4% | 15.4% | 4.5% | 11.9% |
| Melee, top | 65,234 | 18.5% | 37.1% | 6.5% | 17.2% | 5.8% | 13.7% |

Hit share (hit plus hit-and-move) by distance to the nearest enemy:

| Distance | Ranged us | Ranged them | Ranged top | Melee us | Melee them | Melee top |
|---|---|---|---|---|---|---|
| 1 | 29% | 47% | 48% | 69% | 74% | 72% |
| 2 | 33% | 49% | 46% | 38% | 44% | 38% |
| 3 | 28% (toward 21%) | 40% (15%) | 43% (11%) | | | |
| 4 | 5% (toward 43%) | 16% (26%) | 16% (25%) | | | |

At distance 3-4, melee bodies walk toward the enemy in 35-38% of our rounds against 26% for them and top teams.

Our share of bodies that die within 10 rounds, by action with an enemy in reach:

| Action | Us | Them | Top |
|---|---|---|---|
| Hit | 12.5% | 9.6% | 12.8% |
| Away | 20.1% | 17.4% | 17.2% |
| Sideways | 22.8% | 13.7% | 15.9% |
| Still | 39.6% | 24.6% | 28.1% |
| Toward | 11.8% | 4.8% | 8.2% |

**The attack-reset mechanic** (`rangedseq.mjs`, all games, in-round order of a ranged champion's actions in rounds where it hit a
champion). The rules say a ranged walk spends the attack, but an attack-reset ability restores it.

| Champion | Rounds with a hit | Walk, reset, shoot (`M,C0,A*`) | Dash, shoot (`C1,A*`) | Shoot, dash away (`A*,C1`) | Double shot (`A*,C0,A*`) |
|---|---|---|---|---|---|
| Vesper, us | 9,386 | **0** | 10.6% | **0** | 28.2% |
| Vesper, them | 15,995 | 10.2% | 9.4% | 2.1% | 16.5% |
| Vesper, top | 18,017 | **13.2%** | 11.2% | 1.9% | 14.1% |
| Tavi, us | 520 | **0** | | | |
| Tavi, them / top | 2,430 / 2,117 | 11.0% / 13.3% | | | |
| Willow, us (`M,C1,A*`) | 301 | **0** | | | |
| Willow, them / top (`M,C1,A*`) | 932 / 1,192 | 14.7% / 15.9% | | | |

Top teams split the reset between double shots and step-in shots. We only ever use it for the double shot, so every step into range costs
our ranged champion its shot. That is the first strike conceded.

## Q4. Our most damaging decision patterns, ranked, with proposed rule changes

Costs are excess per game against the top teams' own rates. Code references are to `bots/bb4/src/brain.cpp`.

### 1. Walking into their reach and conceding the first strike

**Frequency.**

- They strike first in 44.6% of fresh contacts; we strike first in 22.8%.
- They start 12.5 engagements a game, we start 7.4.
- In 53% of the engagements they start, our victim stepped toward its attacker in the strike round (top-vs-top 38%).
- Approach deaths: 1.77 a game (them 0.38, top 0.85).
- Melee bodies at distance 3-4 walk in 35-38% of rounds (them 26%).

**Cost.**

- An engagement they start costs us 0.63 bodies against 0.23 of theirs.
- Moving to the top-vs-top 50/50 split of starts is worth about +1.1 net bodies a game, plus 0.9-1.4 fewer approach deaths. Each death is
  100 gold to them, the bag, and 60 rounds of body-time.

**What top teams do.** They hold position and let the other side step in. Their ranged first hitters stand still in 19-22% of cases (ours
6%). They open from 4 tiles with spells (53% of first hits are casts).

**Code.**

- `engage()` approaches with `step(goal, false, true)`, which ignores the danger field:
  - ranged branch: line ~4226;
  - melee branch: line ~4243;
  - the hold at the reach edge (`P.open_first & 2`, lines 4168-4187) only covers ranged bodies with an opener ready, standing outside
    danger.
- `respond_to_alert()` sends rally answers with `step(goal, false, true)` (lines 5276, 5303), so bodies arrive one at a time into the
  enemy group.
- Related switches are off: `P.strike_first` 0 and `P.engage_angle` 0. `P.px_hold` is unused, because `px_mode` 2 skips that branch.

**Proposed rule ("no free step-ins").**

- **Where**: in `engage()`, for both melee and ranged bodies.
- **Hold condition**: the target is not killable now and not channelling, and the step's destination is inside an enemy's next-turn
  reach (the `danger` field, or the `n_reach()` lambda from `toward_help`). A body cannot hit after the step without any of: a walk-cast
  spell, a dash-then-hit, or a ranged reset (see pattern 2).
- **What to do**: hold, or take a sideways step that stays outside reach, for at most 2 rounds per target (the `of_since` / `sf_since`
  pattern).
- **Release**: an ally arrives, or the target channels or comes in.
- **Rally answers**: use `step(goal, true, true)` until the body is within reach + 1 of the calling ally.
- **Testing**: put it behind an SV bit and A/B it on the ladder. The local mirror rejected A6 and F3 variants, but local results did not
  transfer.

### 2. Ranged champions spend their shot on walking (shot discipline and the attack reset)

**Frequency.**

- With an enemy in basic range, our ranged champions hit in 29% of rounds against 41-43%, walk away in 32% against 25%, and walk toward
  it in 14% against 8-10%.
- Walk-reset-shoot is used 0 times by us, against 10-13% of hitting rounds for top teams.
- Shoot-then-dash-away: 0 for us, 2% for top teams.

**Cost.**

- Our Vesper dies 2.5 times a game against 1.2-1.6, that is +0.9-1.3 deaths. It is in 355 of our 392 games.
- 74% of our Vesper deaths come with no shot in the previous 8 rounds. Tavi: 2.9 deaths vs 2.4.
- Every ranged step-in becomes their first strike (pattern 1).

**What top teams do.** They walk then reset then shoot (13%), dash then shoot (11%), shoot then dash away (2%), and only half of their
resets go on double shots.

**Code.**

- After a walk, `after_move()` (line 2147) refreshes `can_attack`, which is false for a ranged body.
- In `engage()`, the hit block `if (d <= kit.attack_range) {...}` (lines 4273-4298) only calls `attack_unit(ec)`, and the reset is cast
  only after a successful attack (`if (attack_unit(ec)) {... cast_self(kit.reset) ...}`). So the reset is never used to restore a shot.
- The in-reach flee branch of `combat()` (lines 3890-3961) swings before stepping only for melee (`P.exec_flee_hit && !kit.ranged`,
  line 3897).

**Proposed changes.**

- **Reset to restore the shot**: in `engage()`, before `attack_unit`, add:

  ```cpp
  if (kit.ranged && !can_attack && kit.reset >= 0 && ready(kit.reset) && !cast_done && d <= kit.attack_range)
      cast_self(kit.reset);
  ```

  Also allow the approach step whenever the reset makes it a step-in shot, in the hold logic (`open_first`, `strike_first`). That turns a
  conceded first strike into ours from 4 tiles.
- **Shoot, then dash**: in the in-reach flee branch, a ranged body with `can_attack` and its dash ready shoots `best_in_reach()` first,
  then dashes home (dash-only step). This is the `A*,C1` pattern.
- **Shot preferences** when `combat()` returns "no fight" with an enemy inside our range that cannot reach us next turn (a free shot):
  - take the shot when we cannot be reached;
  - do not take a toward-step while an enemy is already in range.

### 3. Chasing after the opener and not converting won fights

**Frequency.**

- After our opener, our bodies walk toward the enemy in 28-30% of the next 3 rounds (top starters 19-20%).
- Our damage share falls to 0.44 in rounds +3 to +6 (top 0.51-0.52).
- Engagements we start are worth +0.05 net (top starters +0.21).
- After a won engagement we farm 4% (top teams 15-18%) and capture 0.06 per engagement (top teams 0.37-0.38). We move 79% of the time,
  47% of it toward the enemy.

**Cost.**

- About +1.2 net bodies a game if our starts converted like top starts (7.4 starts a game x 0.16).
- About 1.1 captures a game lost after won fights (3.7 a game x 0.31), roughly 25-35 gems plus gold.

**What top teams do.** They keep hitting while the target is in reach, do not chase it out of reach, and return to camps even mid-fight
(6% of rounds +4 to +8). After a won fight they farm and capture.

**Code.**

- `combat()`: a target out of reach that is not killable still yields `fight = true` (the `adv >= fight_margin` and commit rules) and
  `engage()` walks after it.
- The only chase cut is `SV.farm_thru` (lines 3853-3863), which needs `task == T_FARM || T_CAPTURE`. Once the body has fought, `task`
  is `T_FIGHT` from the previous turn, so the cut no longer applies. `SV.chase_max` is off.
- `group_score()` vetoes camps near the fight:
  - threat veto `tadv < target_threat_adv` (1.49, lines 6300-6325), counting enemies seen within the last 7 rounds;
  - `SV.osc_fix` vetoes groups within 8 of `flee_pos` for 15 rounds (line 6328);
  - `post_danger()` also sets `flee_pos` on the "early warning" path (line 3761), even when the body did not flee;
  - groups get +12 rounds of cost when an enemy was seen within 12 rounds (line 6331).

**Proposed rules.**

- **Chase cap after contact**:
  - Applies when the target is out of our reach, not killable now, not channelling, and its distance to us grew last turn.
  - It also requires that no enemy can reach us.
  - Then `fight = false` and `return false`, so `farm()` runs.
  - Generalise the `SV.farm_thru` condition to every task once the body has hit or been hit in the last 6 rounds.
- **Farm again after a won fight** (an enemy died within 8 tiles in the last 10 rounds):
  - in `group_score()`, count only enemies seen this round in the threat veto;
  - skip the `flee_pos` veto;
  - drop the +12 penalty.
- **Keep the early-warning post off `flee_pos`**: only real flees set it.

### 4. Fleeing inside their reach (walking away under fire)

**Frequency.**

- Fleeing-no-fight deaths: 1.14 a game (them 0.51, top 0.63).
- Fleeing-after-fight deaths: 1.16 (0.91 / 1.09).
- Killers are melee 57-70% and dash champions 60-67%.
- With an enemy in reach, bodies that step away die within 10 rounds 20% of the time (17% for them and top teams). Sideways: 23% (14-16%).
  Still: 40% (25-28%).
- When they start, our hit share in the first 3 rounds is 29% (top defenders 31%).

**Cost.** +0.6-0.9 deaths a game, many of them our Vesper (223 of our 445 fleeing-no-fight deaths).

**What top teams do.** They hit back more while in reach, and their walk-aways are rarer and safer.

**Code.**

- `combat()` takes the in-reach flee whenever `fight` ends false (lines 3890-3961). That happens when:
  - `adv < fight_back_margin` (0.873);
  - `ml2_leave`: P(die within 8) ≥ 0.2 with `can_escape` (line 3737);
  - other veto rules, such as the isolated rule.
- `can_escape` (lines 3469-3479) only looks for melee or dash chasers within 3 (+2). Ranged and spell enemies (Prism, Tavi, Marcella's
  4-range spell) keep hitting a walking body.

**Proposed rule.**

- Flee in reach only if the chosen flee tile is outside every visible enemy's next-turn reach (count with `n_reach(dest)` as in
  `toward_help`), or the step reaches spawn. Otherwise hit back with `engage(*tgt)`.
- For ranged bodies, use shoot-then-dash (pattern 2) instead of a plain step.
- In reach, raise the `ml2_leave` bar (for example to 0.35) or require the destination check above. The 0.2 bar drops fights a body
  cannot leave.

### 5. Dying to camps while enemies hit us (contested camp deaths)

**Frequency.**

- 0.63 a game, against 0.25 (them) and 0.34 (top).
- 58% happen while moving, 40% while fighting.
- On average 1.8 enemies within 6 and 661 camp damage taken in the sequence.

**Cost.** +0.3-0.4 deaths a game. Camp kills destroy the bag, and our pure camp deaths carry 26-gem bags on average.

**Code.**

- `P.camp_in_fight` = 3 counts only camps that hit the enemy (the offensive half). Awake camps that will hit **us** are left out of
  `their_dps` and `incoming` (lines 3346-3384).
- Chases and rally walks use `step(goal, false, ...)`, which also ignores `camp_danger`.

**Proposed changes.**

- Set `camp_in_fight = 1`, so both halves are counted.
- In `engage()` and `respond_to_alert()`, pass `camp_danger` as an avoid set (`step(goal, true, ...)`) unless the target is killable.

### 6. (Smaller) Starting fights at even or lower local power

**Frequency.** 44% of our starts are made while our local max health is below 0.87x theirs.

**Cost.**

- Those starts are worth -0.15 net per engagement (-185 bodies over all games).
- Even-power starts in the first 300 rounds are worth -0.17.
- Top starters break even when weaker (-0.05) and win at even power (+0.17).

**Assessment.** Most of this gap is pattern 3, the poor follow-through. A start-power gate already lost on the ladder (`power_gate` in
v13), so do not re-add caution here. Fix the follow-through and the first strike first.

### Side note

Top teams cast their spells on camps (0.27-0.37 camp casts in the 8 rounds before an engagement, against our 0.04-0.09) and still win
fights. Our spell hoarding buys nothing in fights: we have more slots ready and still lose. Using spells on camps would speed up farming,
which is a different topic.

## Caveats

- Engagements are clusters of damage. A long skirmish can split into several engagements, and two nearby fights can merge.
- "Starter" means whoever lands damage first, not who decided to fight.
- Death patterns come from movement relative to the **nearest** enemy, and the classes are heuristic.
- Late-game numbers mix behaviour with the item gap: our max health is lower after round 400. The first-300-round numbers are the cleaner
  behavioural signal, and they show the same direction everywhere.
- The ranged mechanic (walk, reset, shoot) is inferred from replay action order: `Move` then `Cast ability` slot 0 then a damaging
  `Attack` in the same champion turn. Its 2,385 occurrences in top games show the engine allows it.
