# Fights and "what they do in each situation": the six study teams (top2 study, Oct 23)

What the strongest teams do in each combat situation, what it earns them, and which decision rules god2 should adopt or
exploit. Every number is from replays of the teams' **current** bots (ranked games of Oct 23, ~07:00-15:00 UTC).

Notation: **[M]** = measured directly from the replays; **[I]** = inferred (an interpretation or a causal reading of a
measured association). S = the study team, O = its opponents in the same games (mostly other top-50 teams; pbg, ifish
and Pantheon also play each other). "ALL S" pools the six study teams.

## 0. Data, method, definitions

| key | team | ladder | games | W-L | win% | most frequent opponents |
|---|---|---|---|---|---|---|
| pbg | prism best girl | #1 | 116 | 71-45 | 61% | Pantheon 21, IFish 19, procless 19, :3 15 |
| ifish | Intercontinental Fish | #2 | 110 | 66-44 | 60% | pbg 20, :3 18, procless 17, policy wonk 16 |
| cm | Claudus Maximus | #19 | 106 | 58-48 | 55% | NTU 14, the ruliad 13, caterpillow 11, coo 9 |
| pantheon | Pantheon | #6 | 105 | 52-53 | 50% | :3 19, pbg 17, IFish 17, Univardisty 11 |
| coo | conqueror_of_openai | #18 | 101 | 55-46 | 54% | Mite 12, hello 10, NTU 9, EMPEROR Tung 9 |
| nyx | Nyx | #31 | 100 | 49-51 | 49% | EggsAfter11AM 15, AlphaSlop 9, Ad Astra 9 |

638 games, all 40 maps, both sides (sides and results from `C:/battlecode/cache/t2/<key>/index.jsonl`). Every game was
decoded once with `tools/live/fightdump.mjs` (exact per-step damage attribution, every action event).

**Tools (all new, `tools/top2/fights/`)**:
- `mk_sides.py`: study-team side per dump + map geometry (altars, spawns, walking distances).
- `sit.mjs`: the situation miner. One JSON line per game with these records:
  - decision samples every 3rd round with an enemy within 8;
  - (a) arrivals at farmers; (b) ally-hit events, per ally; (c) capture-to-bank decisions and tribute channels;
  - (d) low-health crossings and recall attempts; (e) outmatched / outmatching states; (f) enemy channels near us and
    altar locks;
  - (g, h) engagements with aftermath, chases, deaths and fresh contacts.
- Downstream: `flat.py` (pandas tables), `agg.py` (all tables below), `explore.py` (follow-ups, logits, examples),
  `trib_ctx.mjs` + `trib_agg.py` (big tributes with score context).
- Outputs: `C:/battlecode/cache/top2_fights/` (`sit_<key>.jsonl`, `flat/*.pkl`, `tables_v1.txt`, `tables_v2.txt`,
  `explore_v*.txt`, `trib_agg.txt`).

**Definitions**:
- **Local state within 8**: computed at the decision round. Allies = all bodies of the team within 8 tiles (Chebyshev),
  the decider included. Enemies = alive bodies within 8 that are not on their own spawn. The local current-health ratio is
  the sum of allies' current health over the enemies' sum. The local max-health ratio is the same with maximum health,
  which carries the item gap.
- **Action window**: what the body does in the next 3 rounds (decision samples) or 5 rounds (event triggers). The class
  is taken in this order, first match wins:
  1. fight: dealt damage to an enemy champion;
  2. recall: a recall channel started or running;
  3. bank: a tribute started;
  4. dead;
  5. farm: hit a camp or captured;
  6. leave: the distance to the triggering enemy grew by 2 or more, or the body walked 2 or more tiles toward home;
  7. toward: the distance shrank by 2 or more;
  8. hold: none of the above.
- **Engagement**: champion-vs-champion damage clustered with gaps of 6 rounds or less, within 10 tiles, with 3 or more
  hits or a death.
  - Starter: the side that lands the first damage.
  - Decisive: the two sides lost different numbers of bodies; the side that lost fewer won.
  - Net: enemy deaths minus own deaths.
- **Fresh contact**: opposing bodies within 5, with no champion damage within 10 tiles in the previous 8 rounds. "First"
  is the side that hits first within 5 rounds.
- **Recall attempt**: a `Recall` action away from spawn. Done means the body arrived on its spawn within 6 rounds.
  - Interrupted: damage or a stun hit it first. Killed: it died in the window.
  - Pantheon recall-spams: it cancels and restarts every turn, about 6,000 `Recall` events a game. For Pantheon only
    channels kept for a full idle round count, and its recall rates are reported apart.
- **Tribute outcome**: done (the `Gems submitted` event), killed, stunned, locked (an enemy lock on that altar), or
  cancelled. Cancelled is split into "enemy within 4 when it stopped" and "other".
- **Chase**: within 3 rounds of a hit between A and V, V steps away from A and A steps after it. The chase lasts while A
  keeps closing (or hitting). It ends after 2 rounds without that, or on a kill, the chaser's death, a gap above 10, or
  V reaching its spawn.

Per-game summary (means per game; from `tables_v1.txt` section 0) [M]:

| team | deaths S / O | kills S | gems lost on death S / O | max bag (median) S / O | banks S / O | altar locks S / O | max health r300 S / O |
|---|---|---|---|---|---|---|---|
| pbg | **7.4** / 10.0 | 9.3 | 117 / 127 | **261** / 95 | 16.3 / 21.2 | **0.0** / 2.2 | 6,567 / 5,991 |
| ifish | 9.2 / 10.7 | 9.8 | 143 / 167 | 112 / 103 | 21.9 / 16.5 | 2.9 / 1.3 | 6,660 / 5,947 |
| cm | **12.7** / 10.6 | 9.5 | 100 / 100 | 86 / 86 | 24.9 / 21.7 | **5.6** / 3.6 | 5,881 / 6,173 |
| pantheon | **6.3** / 9.4 | 8.6 | **237** / 195 | **211** / 132 | 26.8 / 16.6 | 4.2 / 1.8 | **4,932** / 6,276 |
| coo | **13.3** / 7.9 | 6.6 | 168 / 105 | 86 / 92 | 20.1 / 23.2 | 1.1 / 2.8 | 5,289 / 6,384 |
| nyx | 8.2 / 9.7 | 8.2 | 133 / 99 | 149 / 112 | 19.6 / 20.2 | 0.0 / 1.9 | 6,032 / 6,118 |

## 1. Headline

1. **The fight is decided before it starts: local max health and who lands the first damage** [M].
   - Logit over 7,116 decisive engagements, with standardised coefficients:
     - pre-fight state alone (pseudo-R² 0.28): local max-health ratio +1.83 (z 31), current/max health share +0.74 (z 15),
       starting the fight +0.57 (z 19);
     - adding what happens in the fight (pseudo-R² 0.38): first-3-round damage share +0.96 (z 20).
   - At even power (|log max-health ratio| < 0.15) the starter wins 69% of decisive engagements (n = 552); the side that
     is started on wins 39% (n = 483).
   - The study teams start 54% of engagements and net +0.21 bodies per start; when they are started on they net −0.20.
2. **Starting fights while weaker is what loses games** [M].
   - The share of a team's own starts made at a local max-health ratio below 0.67 is 0.24 in the study teams' wins and 0.44
     in their losses (pooled correlation −0.44).
   - It stays significant in a game-level logit that also includes max health at r300: −0.96, z −3.9, n = 262.
   - Starts at 0.67-0.87 are still net-positive (+0.15 a start), because the other side would have started anyway (−0.28
     when they start at the same ratio).
3. **The retreat trigger is the body's own health, not local power** [M].
   - With an enemy within 4 and own health ≥ 35%, the study teams fight in 41-52% of rounds at every local ratio from
     <0.45 to ≥1.4, and leave or recall in 21-30%.
   - Leave/recall overtakes fight only below 35% own health (34% fight vs 43% leave+recall at 20-35%).
   - Outcomes, per 100 decision samples: fighting nets −17 kills-minus-deaths at a current-health ratio below 0.6, +12.5
     at 0.6-0.9, +27 at 0.9-1.2 and +38 at 1.2-2. Leaving nets −7 below 0.6.
4. **Prism gem-carry and the game-winning tribute** (pbg, Pantheon, Nyx) [M].
   - The Prism carries 73-94% of these teams' 100+ gem bags. pbg's Prism tributes once or twice a game, a median of 532
     gems at a median r1194. 72% of those tributes would end the game (score + bag ≥ 1,000), and they bank 55% of pbg's
     gems.
   - A Prism carrying 150+ gems deals 2.8-3.4x the damage per 5 rounds and dies 3-4x less often than an empty Prism in the
     same game phase.
   - These channels are long: medians of 26-54 turns, up to 108. Only 27% of 400+ gem tributes complete (S), and 79% of the 200+ gem enemy
     tributes that the study teams reach within 8 fail.
5. **Tributes are stopped by stuns and locks, not by damage; recalls are stopped by any hit** [M].
   - Enemy tribute with our body within 4: no response 22% fail, damage only 30%, a stun 92%, a lock 97%.
   - Enemy recall within 4: hit it and 95.5% fail, 24% of those recallers die; leave it and 31% fail.
   - The study teams punish by bag size: 11% hits and 1% locks on tributes under 100 gems, 54% hits, 27% stuns and 22%
     locks at 200+ gems.
6. **Recall discipline** [M].
   - Outcome by the nearest enemy at the start:

     | Nearest enemy | Recalls complete | Recaller dies |
     |---|---|---|
     | ≤ 3 | 37% | 23% |
     | 4-5 | 60% | 6% |
     | 6-8 | 85% | 1% |
     | > 8 | 95% | under 1% |

   - The study teams recall 37-74 times a game, at a median 0.42-0.71 of max health.
   - Below 35% health with an enemy within 8, a recall is followed by death within 15 rounds in 7% of cases, leaving in
     12-16%, fighting on in 49-53%.
7. **Chase only wounded targets** [M]. Chases end in a kill 40% of the time when the target started below 35% health, 23% at
   35-70% and 12% above 70%. The chaser dies within 10 rounds afterwards in 5-7% of cases at any target health. The median
   chase lasts 4 rounds (p90 10-11).
8. **Farming under pressure: keep farming unless the body is clearly weaker** [M].
   - An enemy arriving within 8 does not stop the farm: 58% keep farming, 8% fight, 6% leave, 12% recall.
   - With the enemy within 4 and a local ratio below 0.6, net per 100 samples is −2.7 for leaving, −8.5 for keeping
     farming and −13 for fighting. At 0.9 and above fighting is best (+22 to +48).
9. **After a won fight they convert** [M].
   - Winners' survivors farm 15% of the next 20 rounds (losers 10%) and capture 0.8 groups (14 gems) within 30 rounds
     (losers 0.1).
   - 41% walk or recall home (shop with the kill gold); winners start the next fight in that area 34% of the time
     (losers 25%).
10. **Two habits are team-specific, not universal** [M].
    - Capture-recall combo: the recall runs while the 5-round capture timer runs, so the body captures and teleports home in
      the same round. Nyx does it on 54% of captures, Pantheon 42%, pbg 7%, IFish 6%, cm 0%.
    - Guard locks: a team's own lock placed on the altar just before its tribute; an altar holds one lock. cm places
      3.4 a game, Pantheon 1.8, IFish 1.4; pbg and Nyx never lock.

## 2. Situation tables

### (a) An enemy champion comes within 8 while a body is farming or capturing

**What triggers it**: a body that hit a camp in the last 3 rounds, or stands still on a camp tile, sees an enemy within
8, with no enemy within 8 in the previous 4 rounds. The window is the next 5 rounds. There are 18 such events per
team-game.

a1, per team [M]:

| grp | n | keep farming | fight | leave | recall | died ≤ 20 r | own capture ≤ 40 r | enemy captures it |
|---|---|---|---|---|---|---|---|---|
| pbg S / O | 2,294 / 1,732 | 57 / 59% | 8.6 / 7.5% | 5.8 / 5.8% | 12.7 / 11.7% | 3.5 / 6.6% | 71 / 69% | 3.4 / 9.4% |
| ifish S / O | 2,165 / 1,707 | 58 / 61% | 6.2 / 8.6% | 6.2 / 5.7% | 10.8 / 10.7% | 6.2 / 8.4% | 76 / 72% | 3.6 / 7.8% |
| cm S / O | 2,024 / 1,696 | **67.5** / 54% | 7.2 / 12.1% | 4.8 / 7.0% | **6.4** / 10.8% | 7.5 / 6.5% | 66 / 67% | **9.2** / 6.5% |
| pantheon S / O | 1,712 / 1,714 | 52 / 62% | 10.9 / 4.5% | 6.2 / 7.1% | 15.9 / 10.3% | 4.8 / 5.9% | 65 / 73% | 8.4 / 3.3% |
| coo S / O | 1,425 / 1,690 | 59 / 57% | 7.2 / 8.2% | 8.1 / 7.4% | 10.0 / 10.5% | 7.2 / 3.6% | 72 / 73% | 5.6 / 5.0% |
| nyx S / O | 1,865 / 1,853 | 56 / 62% | 10.5 / 6.6% | 6.0 / 5.5% | 14.6 / 9.2% | 4.3 / 5.5% | 70 / 67% | 6.4 / 6.5% |

- [M] The "recall" column counts a recall channel started or already running in the window. For Nyx and Pantheon part
  of it is the capture-recall combo (section 1, item 10): the recall was running before the enemy arrived.

**By local current-health ratio** (a2, ALL S; from left to right the farmer's side gets stronger) [M]:

| ratio | n | farm | fight | leave | recall | died ≤ 20 r | enemy captures |
|---|---|---|---|---|---|---|---|
| < 0.6 | 865 | 53% | 5% | 6% | **20%** | 12.5% | 17% |
| 0.6-0.9 | 859 | 59% | 9% | 6% | 16% | 9.1% | 14% |
| 0.9-1.2 | 844 | 56% | 11% | 5% | 15% | 8.1% | 11% |
| 1.2-2 | 2,227 | 58% | 9% | 6% | 12% | 6.5% | 7% |
| ≥ 2 | 6,690 | 59% | 8% | 7% | 10% | 3.5% | 3% |

Per team, at a ratio below 0.6:
- cm keeps farming in 71% of cases (pbg 33%, IFish 50%) and recalls in only 9% (pbg 34%, IFish 29%, Pantheon 28%).
- The enemy then takes cm's group 21% of the time.
- pbg's opponents keep farming in 55% of cases.

**With the enemy within 4** (decision samples on farming or capturing bodies, next 3 rounds; `explore_v3.txt`) [M]:

| ratio | S fight / farm / leave | S died ≤ 10 r | S net per 100 by action: fight / farm / leave | O net: fight / farm / leave |
|---|---|---|---|---|
| < 0.6 | 37 / 24 / 16% | 24% | **−13.0 / −8.5 / −2.7** | −19.6 / −11.2 / −4.9 |
| 0.6-0.9 | 41 / 29 / 13% | 12% | **+10.1** / −0.5 / +4.4 | −0.9 / +0.4 / +2.2 |
| 0.9-1.2 | 41 / 28 / 12% | 8.5% | **+21.7** / +4.4 / +7.7 | +15.6 / +3.1 / +6.0 |
| 1.2-2 | 38 / 32 / 11% | 4.8% | +33.3 / +6.2 / +10.4 | +29.5 / +6.1 / +17.7 |
| ≥ 2 | 34 / 37 / 12% | 2.5% | +48.5 / +13.2 / +27.7 | +51.7 / +17.5 / +26.5 |

- [M] At 0.6-0.9 the study teams' fights pay (+10) and their opponents' do not (−1): same state, better execution or
  hidden power (focus and strength items are not in max health).
- [M] The bag changes the choice (a4). Farmers carrying 150+ gems, mostly Prism carriers, keep farming less (42% vs 60%
  with an empty bag), fight more (13% vs 8.5%) and recall a little more (14% vs 11%).
- Example: cm's Vendetta keeps farming at 1,420 health while a 5,400-health Marcella is within 8, and dies (cm vs
  Zarzorki, `t2/cm/00fragment_28f9bafa`, r1059-1068).

### (b) An ally gets hit nearby: who helps, from how far, how fast

**What triggers it**: the first champion hit on a body after 6 quiet rounds; 40 per team-game. For every ally within 20
tiles we record whether it hits an enemy within 8 of the victim (or the attacker) in the next 10 rounds and how fast it
comes [M]:

| distance at the hit | ALL S hit back | median latency | came within 4 | ALL O hit back |
|---|---|---|---|---|
| 0-4 | 57.5% | 1 round | n/a | 56.5% |
| 5-8 | 30.9% | 4 rounds | 56% | 30.0% |
| 9-12 | 14.3% | 6 rounds | 28% | 13.4% |
| 13-16 | 6.0% | 8 rounds | 15% | 4.9% |

- The response rate is almost the same for every team (b1: 55-61% at 0-4, 29-34% at 5-8). Help is local: nobody crosses
  the map. 33-34% of the allies within 8 walk away.
- **Who helps** (allies within 8, b4): Ryth 58-65%, Vesper 43-60%, Prism / Marcella 47-59%, Tavi 50-63%. Least: Vendetta
  33-41%, Issac 33%, Varg 25-39%, and Willow 21% (heals are not counted as hits).
- Busy allies help less (b3): farming 40%, on a capture tile 45%, free 53%, tributing 38%. Recalling allies keep
  recalling (83% walk away / teleport).
- **What help buys** (b2), by the number of allies that hit back (0 / 1 / 2+): the victim dies within 15 rounds in 22.9%
  / 19.2% / 18.7% of cases, the attacker in 9.1% / 22.1% / 34.0%. [I] Help rarely saves the hit body; it turns the
  exchange into a kill on the attacker.

### (c) Carrying a big bag: bank or keep farming?

**After a gem capture, the next bag event** (c1) [M]:

| team | caps/game | bank next | capture again first | died with it | median rounds to bank | via spawn | median bag banked |
|---|---|---|---|---|---|---|---|
| pbg S | 36.7 | 42.5% | 50.6% | 4.7% | 19 | 44% | 30 |
| ifish S | 38.5 | 54.5% | 37.8% | 5.6% | 17 | 39% | 28 |
| cm S | 36.8 | **64.9%** | 24.9% | 7.4% | 14 | **14%** | 22 |
| pantheon S | 42.4 | 60.6% | 32.1% | 4.9% | 15 | 47% | 19 |
| coo S | 41.6 | 47.6% | 40.5% | **10.2%** | 17 | 32% | 28 |
| nyx S | 45.5 | 42.0% | 49.6% | 6.2% | 20 | 60% | 26 |
| ALL O | 38.2 | 50.3% | 40.0% | 7.1% | 19 | 41% | 26 |

P(bank before the next capture) by bag after the capture (c2) [M]:

| team | < 30 | 30-59 | 60-99 | 100-199 | 200+ |
|---|---|---|---|---|---|
| pbg S | 46% | 53% | 46% | **22%** | **15%** |
| ifish S | 51% | 58% | 64% | 65% | 35% |
| cm S | 62% | 67% | **89%** | **88%** | 79% |
| pantheon S | **75%** | 71% | **20%** | **4%** | 12% |
| coo S | 41% | 58% | 60% | 54% | 34% |
| nyx S | 42% | 55% | 37% | 15% | 19% |

- Two policies [I]:
  - Bank-small: cm, IFish and coo bank most bags under 100 when an altar is near.
  - Carry: pbg, Pantheon and Nyx bank small bags but stop banking once a bag passes about 60-100 gems. Those bags are on
    the Prism (next table).
- **Altar distance matters for everyone** (c3, ALL S, bag under 30): 75% bank next at an altar within 5 walking tiles,
  53% at 6-12, 43% at 13-25, 37% beyond 25. For 30-59 gem bags: 77% / 61% / 59% / 46%.
- **Threat barely changes banking** (c4): with an enemy within 8 at the capture, bank next is 53% (51% without), but the
  bag is then lost to death twice as often: 10.2% vs 5.2%.
- **Tribute channels** (c5): 23 a game, median bag 26 (p90 80). 94% complete; 5% are hit during the channel; 0.7% killed,
  1.6% stunned, 1.1% locked. [M] Ordinary tributes are almost never punished.

**Who carries the big bags** (p1, p2) [M]:

| team | captures leaving 100+ gems | carrier | Prism tributes/game | median Prism tribute | Prism share of banked gems |
|---|---|---|---|---|---|
| pbg | 19.1% | Prism 73%, Vesper 17% | 1.4 | **521** (p90 1,011) | **55%** |
| pantheon | 15.3% | Prism 94% | 0.8 | 262 (p90 601) | 27% |
| nyx | 10.5% | Prism 86% | 1.6 | 260 (p90 367) | 30% |
| ifish | 5.9% | Vesper 69%, Vendetta 23% | (no Prism) | n/a | n/a |
| cm / coo | 1.6% / 2.6% | Vendetta / Vesper | n/a | n/a | n/a |

**Why the carry works**: the Prism gains +1.5 focus per carried gem (rules). [M] A Prism with an enemy within 6, by
bag and game phase (decision samples, `p3` + phase check):

| phase | bag | n (S) | damage dealt / 5 r | died ≤ 10 r | enemy deaths ≤ 10 r per 100 |
|---|---|---|---|---|---|
| r < 600 | < 50 | 7,039 | 96 | 7.0% | 17 |
| r < 600 | 150+ | 833 | 266 | 2.0% | 27 |
| r 600-1000 | < 50 | 3,016 | 106 | 10.5% | 12 |
| r 600-1000 | 150+ | 1,792 | 327 | 3.2% | 26 |
| r ≥ 1000 | < 50 | 2,872 | 131 | 13.2% | 14 |
| r ≥ 1000 | 150+ | 1,509 | 449 | 3.6% | 27 |

**When the carry is banked** (`trib_agg.txt`; Prism tributes of 100+ gems) [M]:

| team | n | median bag | median round | median own / enemy score | would end the game | completed per attempt |
|---|---|---|---|---|---|---|
| pbg S | 138 | **532** | 1194 | 579 / 363 | **72%** | 36% |
| nyx S | 123 | 260 | 1014 | 750 / 363 | 61% | 30% |
| pantheon S | 66 | 296 | 923 | 662 / 440 | 23% | 59% |

- All teams, tributes of 60+ gems by bag (S, done%): 60-99 89%, 100-199 84%, 200-399 50%, 400+ **27%** (O: 90 / 60 /
  46 / 15%).
- Of the 400+ gem tributes: killed 7%, stunned 5%, locked 3%, the carrier stops with an enemy within 4 10%, other 48%
  (mostly re-tries).
- Game-winning tributes (score + bag ≥ 1,000) complete in 38% (S) / 33% (O) of attempts. A carry team retries:
  82% of the games with a big Prism tribute (151 games) end with one completed.
- With an enemy within 8 at the start, a 100+ Prism tribute completes in 23% of cases (S), against 53% without one.
- Examples:
  - **pbg vs Pantheon, `t2/pbg/01gold_rush_5e908f99` r1285**. pbg's Prism (4,578/4,900 health) starts a 1,075-gem,
    108-turn tribute while pbg trails 165-341 in tributed gems. It completes and pbg wins on gems. The same scene shows
    Pantheon's recall spam: every Pantheon body issues `Recall` every round (r1245-1255).
  - **IFish vs pbg, `t2/pbg/00great_wall_3a46ed8d`**:
    - r882: pbg's Prism (368 gems) is locked out by IFish.
    - r1069: the Prism (623 gems) is stunned.
    - r1094: it is killed.
    - IFish wins.
  - **pbg vs Pantheon, `t2/pbg/00gem_fields_3fc2330b`**. r483: pbg's Prism starts a 704-gem, 71-turn tribute with no ally
    within 6. Pantheon's Vesper kills it at r517 and starts tributing the stolen bag at the same altar at r518.
- **Loaded Prisms die** [M]: 99 deaths of Prisms carrying 100+ gems.
  - Pantheon S: 33 deaths, 11,745 gems (112 a game). Nyx S: 24 deaths (4,632 gems). pbg S: 16 deaths (4,267 gems).
  - Killers: Marcella 27, Vesper 26, camps 20, Heart of Ruin 12.
  - What the Prism was doing: fighting 23, banking 17, fleeing after a fight 16, camp 15. 36% were isolated (no ally
    within 6).

**Bags lost on death** (c6), gems per game for S / O:
- Pantheon 237 / 195; coo 168 / 105; IFish 143 / 167; Nyx 133 / 99; pbg 117 / 127; cm 100 / 100.
- [M] Over all games, the S−O difference in gems lost correlates −0.35 with S winning. In the game logit it is the
  strongest term: −1.27, z −4.6.

### (d) Low health: recall, flee or fight on?

**What triggers it**: a body's health crosses below 35% away from spawn; the window is the next 5 rounds (d1, ALL S /
ALL O) [M]:

| context | n/game | recall | leave | fight | farm | died ≤ 15 r | home ≤ 40 r |
|---|---|---|---|---|---|---|---|
| enemy within 8, S | 15.8 | 20% | 16% | 35% | 4% | 44% | 54% |
| enemy within 8, O | 16.9 | 18% | 20% | 32% | 2% | 46% | 52% |
| no enemy within 8, S | 8.0 | 66% | 3% | 0% | 22% | 7.7% | 91% |

Per team, with an enemy within 8 (recall / leave / fight, then died ≤ 15 r):

| team | recall | leave | fight | died ≤ 15 r |
|---|---|---|---|---|
| pantheon | 28% | 16% | 30% | 39% |
| ifish | 27% | 13% | 34% | 41% |
| pbg | 23% | 9% | 43% | 45% |
| nyx | 21% | 22% | 26% | 42% |
| coo | 16% | 16% | 42% | 52% |
| cm | 13.5% | 20% | 33% | 43% |

**Outcome by action** (d2, ALL S; low health, enemy within 8) [M]:
- fight on: 49% die within 15 rounds (n = 3,521; the enemy is at a median distance of 1);
- leave: 15.5% (n = 1,633; median distance 3);
- recall: 6.7% (n = 2,058; median distance 4, median local ratio 1.0);
- hold: 38%.
- [I] Recall is chosen when the enemy is farther, so part of the gap is selection. The ordering matches every other cut
  (d4, s2): a body that is low and close dies when it stays.

**Recall attempts** (d3; teams that do not recall-spam) [M]:
- Attempts per game: pbg 55, IFish 60, Nyx 74, cm 48, coo 37. Completed: 85-89%.
- Median health at the start: IFish 0.42, cm 0.45, pbg 0.46, coo 0.57, Nyx **0.71**. They recall to shop as much as to
  heal.
- Pantheon (recall spam) completes 40.8 recalls a game.
- Started with an enemy within 4: 5.5-11.6% of attempts.

**Is the recall punished?** (d4, pooled) [M]:

| nearest enemy at the start | n (S) | done | interrupted | killed | hit during the channel |
|---|---|---|---|---|---|
| ≤ 3 | 1,266 | **37%** | 27% | **23%** | 48% |
| 4-5 | 3,251 | 60% | 12.5% | 5.7% | 16% |
| 6-8 | 6,998 | 85% | 4% | 0.9% | 3% |
| > 8 | 17,731 | 95% | 0.9% | 0.2% | 0.2% |

The O rows are the same within 1-4 points. Example: pbg's Vesper recalls at 16% health with an enemy adjacent and is
killed (`t2/pbg/00gem_fields_3fc2330b` r35).

**When do they turn and leave?** (t1: enemy within 4; fight % / leave+recall % by own health, ALL S) [M]:

| own health | < 20% | 20-35% | 35-50% | 50-70% | 70%+ |
|---|---|---|---|---|---|
| fight / leave+recall | 22 / 34 | 34 / 43 | 43 / 35 | 50 / 25 | 50 / 20 |

Nyx leaves earliest: 33 / 49 at 35-50% own health. cm at <20%: 15 / 42.

### (e) Outnumbered or outmatched: retreat rules

**What triggers it**: an enemy within 6, with the local max-health ratio below 0.7 or 2+ fewer bodies ("under"), or above
1.43 or 2+ more bodies ("over"). The window is the next 5 rounds (e1, e2) [M]:

| state | grp | n/game | fight | leave | hold | farm | recall | died ≤ 15 r | enemy deaths ≤ 15 r per 100 |
|---|---|---|---|---|---|---|---|---|---|
| under | ALL S | 39.7 | 36% | 22% | 16% | 10% | 6% | 17.8% | 15.0 |
| under | ALL O | 36.6 | 32.5% | 26% | 16% | 10% | 5% | 17.6% | 12.6 |
| over | ALL S | 78.2 | 30% | 18% | 14% | 20.5% | 9% | 4.9% | 26.5 |
| over | ALL O | 80.0 | 30% | 20% | 16% | 18% | 8% | 6.0% | 27.1 |

Under, outcome by action (S):
- fight: 23.6% die, 28.6 enemy deaths per 100;
- leave: 6.5% / 7.8;
- hold: 10.6% / 5.9;
- toward: 20.9% / 9.3.

[M] The study teams fight back when outmatched slightly more than their opponents and trade evenly (+5 net per 100 vs
+1.3 for leaving). This is not a retreat rule: **the local ratio barely moves their fight rate** (t2; own health ≥ 35%,
enemy within 4):

| team | fight / leave+recall at ratio < 0.45 | at ≥ 1.4 |
|---|---|---|
| pbg | 53 / 23 | 53 / 21 |
| ifish | 43 / 28 | 49 / 22 |
| cm | 35 / 30 | 49 / 20 |
| pantheon (most ratio-sensitive) | 36 / 38 | 59 / 19 |
| coo | 42 / 30 | 45 / 22 |
| nyx | 40 / 32 | 52 / 20 |

By body count (t3; own health ≥ 35%): pbg fights more when outnumbered by 2 (62 / 19) than when ahead by 2 (50 / 22).
Pantheon is the reverse: 48 / 30 vs 57 / 20.

[I] Their bodies carry more items than max health shows (strength and focus shards, the Prism's gem focus), so "under" is
often not really weaker for them. A bot without that power edge should not copy the stand-and-fight habit: see the
outcome tables in (a) and (h).

### (f) An enemy is tributing or recalling nearby: do they punish it?

f1, f2: an enemy channel with our body within 8, judged from the punishing team [M]:

| channel | closest of us | n (S) | S: hit / stun / lock | S: channel failed | O: hit / stun / lock | O: failed |
|---|---|---|---|---|---|---|
| tribute | ≤ 4 | 936 | 36 / 14.5 / 4.8% | 44% | 47 / 18 / 11% | 34% |
| tribute | 5-6 | 1,820 | 17 / 8 / 3% | 23% | 13 / 5 / 4% | 15% |
| tribute | 7-8 | 1,733 | 3 / 1 / 1% | 6% | 5 / 1 / 2% | 7% |
| recall | ≤ 4 | 1,679 | 46.5% hit | 60% (11% killed) | 43.7% hit | 60% (11.5%) |
| recall | 5-6 | 3,075 | 11% hit | 30% | 9% hit | 30% |

**What works** (punout, pooled; enemy tribute with our body within 4) [M]:

| response | n | tribute failed | channeller killed |
|---|---|---|---|
| none | 993 | 22% (self-cancel) | 0.2% |
| damage only | 390 | 30% | 10.5% |
| stun | 286 | **92%** | 14% |
| altar lock | 137 | **97%** | 17.5% |

For an enemy recall within 4: without a hit 31% fail; with a hit **95.5%** fail and 24% of the recallers die.

**They punish by bag size** (enemy tribute, our body within 8) [M]:

| enemy bag | S: hit / stun / lock | S: failed | O: hit / stun / lock | O: failed |
|---|---|---|---|---|
| < 100 | 11 / 4 / 1.3% | 12% | 13 / 5 / 3% | 10% |
| 100-199 | 26.5 / 20 / 3% | 67% | 21 / 8 / 6.5% | 28% |
| ≥ 200 | **54 / 26.5 / 22%** | **79%** | 45 / 18.5 / 15% | 70% |

Against tributes of 150+ gems each team uses a different tool:
- IFish and Pantheon lock (36% each);
- Nyx stuns (40%; it fails 93% of those tributes);
- cm uses both (stun 32%, lock 29%);
- pbg only hits and stuns (53% / 15%).

**Altar locks per game** (f3) [M]:

| team | locks | guard (own tribute ≤ 3 r later, same altar) | counter (cancels a running enemy tribute) | deny / other |
|---|---|---|---|---|
| cm | **5.6** | **3.4** | 0.16 | 2.0 |
| pantheon | 4.2 | 1.8 | 0.36 | 2.1 |
| ifish | 2.9 | 1.4 | 0.25 | 1.3 |
| coo | 1.1 | 0.9 | 0.23 | 0.0 |
| pbg | **0.0** | 0 | 0 | 0 |
| nyx | 0.03 | 0 | 0.03 | 0 |

- [M] An altar holds one lock (`invalid_action_altar_lock_already_locked`, SDK error 120). [I] A guard lock placed just
  before the team's own tribute therefore blocks the enemy's counter-lock until 5 basic attacks clear it.
- Example: cm's Vesper locks altar (37, 59) at r1435 and tributes there at r1437 (`t2/cm/00ambush_1586d15b`).
- Locks do not correlate with winning (r = 0.00); stopping game-winning tributes does (section 3).

### (g) After winning or losing a fight

g1, pooled. Participants alive at the end of an engagement, next 20 rounds; captures within 30 [M]:

| side | farm | hit champions | recall | captures / engagement | gems captured | push (4+ tiles toward their spawn) | reset (4+ tiles home) | in their third | starts the next fight |
|---|---|---|---|---|---|---|---|---|---|
| S after a win | **15.1%** | 2.7% | 9.2% | **0.8** | **14.3** | 19% | **41%** | 11.9% | 34% |
| S after a loss | 10.3% | 4.0% | 7.7% | 0.1 | 1.5 | 29% | 30% | 3.1% | 25% |
| O after a win | 13.6% | 2.7% | 9.0% | 0.7 | 13.0 | 21% | 42% | 9.9% | 30% |
| O after a loss | 9.2% | 3.6% | 6.2% | 0.2 | 1.5 | 29% | 29% | 3.5% | 22% |
| no deaths (S) | 11.3% | 3.9% | 9.9% | 0.4 | 5.8 | 20% | 40% | 7.4% | 37% |

- The pattern is the same for every team. Pantheon winners farm most (17.8%); cm winners go deepest (17% of rounds in the
  enemy third).
- [I] Winners convert in two ways:
  - they take the nearby group while the dead respawn (60 rounds);
  - they go home to spend the 100-gold kill reward.
  - They do not chase into the enemy half: "push" is lower after a win than after a loss.
- [I] Losers' survivors mostly walk back to the fight area ("push" 29%) rather than to camps.
- Early first blood matters [M]:
  - The side that gets the first kill before r300 wins the game 60-80% of the time; the other side wins 25-48%.
  - pbg gets it in 54% of its games and wins 74% of those. coo gets it in 30% and cm in 37%.

### (h) Fight execution

**Who starts and who wins** (h1) [M]:

| team | engagements/game | S starts | S wins (decisive) | net per S start | net per O start | S first-3-round damage share | focus S / O |
|---|---|---|---|---|---|---|---|
| pbg | 19.0 | 57% | **62%** | +0.31 | −0.02 | 0.58 | 0.80 / 0.83 |
| ifish | 18.9 | 46% | 58% | +0.31 | −0.06 | 0.46 | 0.83 / 0.80 |
| cm | 23.7 | 45% | 45% | +0.22 | −0.34 | 0.43 | 0.83 / 0.82 |
| pantheon | 19.2 | **66%** | 58% | +0.28 | −0.13 | **0.63** | 0.83 / 0.86 |
| coo | 21.0 | 47% | **32%** | −0.08 | −0.41 | 0.45 | 0.83 / 0.84 |
| nyx | 25.8 | 62% | 55% | +0.18 | −0.11 | 0.59 | 0.81 / 0.86 |
| ALL | 21.2 | 54% | 51% | +0.21 | −0.20 | 0.52 | 0.82 / 0.83 |

**Outcome vs local max-health ratio** (h2, h3; S/O within 8 at the start) [M]:

| S/O ratio | n | S wins (decisive) | net per engagement | net if S starts | net if O starts | share started by S |
|---|---|---|---|---|---|---|
| < 0.67 | 4,518 | 24% | −0.35 | −0.16 | −0.54 | 51% |
| 0.67-0.87 | 1,532 | 46% | −0.06 | **+0.15** | −0.28 | 51% |
| 0.87-1.15 | 1,905 | 55% | +0.08 | **+0.27** | −0.15 | 54% |
| 1.15-1.5 | 1,523 | 62% | +0.17 | +0.33 | −0.03 | 55% |
| ≥ 1.5 | 4,038 | 78% | +0.39 | +0.53 | +0.20 | 57% |

Selectivity (h4) [M]:
- The study teams start about 51% of fights when weaker and 57% when stronger.
- cm is the most selective: 37% of fights at <0.67, 54% at ≥1.5.
- Pantheon starts 64-69% at every level.
- Share of each team's own starts made at <0.67: pbg 22%, IFish 30%, cm 30%, Nyx 33%, Pantheon 36%, coo 41%.

**First strike in fresh contacts** (h7; contacts within 5, 36 a team-game) [M]:

| team | S first / O first / nobody | S first when weaker | O first when S weaker |
|---|---|---|---|
| pantheon | **40 / 18** / 43% | 35% | 19% |
| nyx | 33 / 20 / 47% | 30% | 25% |
| pbg | 31 / 23 / 46% | 28% | 26% |
| coo | 26 / 28 / 46% | 23% | 32% |
| cm | 22 / 29 / 49% | 19% | 35% |
| ifish | **24 / 31** / 45% | 20% | 34% |

[I] IFish wins without the first strike: the best defence (−0.06 when started on) and the best chases.

**How fights open** (h5) [M]:
- The first hit is a spell in 48% (S) / 52% (O) of engagements: pbg 59%, Pantheon 57%, Nyx 58% (Prism teams), against
  IFish 32%, cm 37%, coo 35%.
- The victim had walked in 67-69% of the time and was farming 19-20%; it was channelling 6% of the time.
- The opener stood still before its hit in 11% of cases (Nyx 19%).
- Example: pbg's Ryth opens on Issac at r258 with 1,800-2,100 max-health bodies against 600-1,200, and Willow dies at
  r270 (pbg vs Univardisty, `t2/pbg/00contest_a136a0ec`).

**Follow-through** (h6) [M]: the starter's damage share is 0.77 in rounds 0..+2, 0.55 in +3..+6 and 0.61 after that. The
Prism teams keep it best: 0.80 → 0.56-0.59 → 0.62-0.69.

**Focus fire**: 80-86% of a side's damage lands on its most-hit target for every team. It is not a differentiator.

**Chases** (h8, chase2) [M]:
- About 14 chases per team-game. Median length 3-4 rounds, mean about 5, p90 10-11.
- They end in a kill 22% (S) / 19.5% (O) of the time: IFish 31%, cm 25%, pbg 24%, Pantheon 20%, coo 19%, Nyx 15%.
- By target health at the start: < 35%: 40% kill (n = 1,979, S); 35-70%: 23%; ≥ 70%: 12%.
- By length: 1-2 rounds 10%; 3-5 rounds 27%; 6-9 rounds 31%; 10+ rounds 32%.
- The chaser dies within 10 rounds after in 6% of chases at every length.
- The chase reaches a median of 1-2 tiles deeper than the start (from the chaser's home).
- Example: IFish's Vendetta chases a Prism for 12 rounds, hits 4 times and kills it (`t2/ifish/00ambush_6b531f81` r252).

**Death contexts** (h9; champion kills only, victim side) [M]:

| grp | deaths/game | fighting | flee after fight | flee | approach | walk | recalling | isolated (no ally ≤ 6) | outnumbered ≤ 6 | no hit in the last 8 r |
|---|---|---|---|---|---|---|---|---|---|---|
| ALL S | 8.2 | 48.5% | 13% | 9% | 11% | 9.6% | 4.7% | 40.7% | 41.8% | 29% |
| ALL O | 8.7 | 48.2% | 14.5% | 10% | 11% | 8.7% | 4.4% | 37.2% | 39.1% | 28% |
| pbg S | 6.1 | 55.5% | 15% | 5% | 11% | 6% | 4% | 37% | 46% | **18%** |
| cm S | 11.6 | 35% | 13% | 9% | **16.4%** | 12% | 6% | 42% | 47% | **40.5%** |
| coo S | 11.9 | 60% | 7.5% | 8% | 7% | 11.5% | 3% | **45.6%** | 40% | 24% |
| pantheon S | 6.0 | 48% | 13% | 8% | 11% | 7.5% | 6% | 44% | 44% | 28% |

- Victims had a median of 0.7-0.8 of their killers' max health.
- Victims were above 90% health when their damage sequence started: "burst" deaths are the norm.

## 3. What wins fights and games

**Engagements** (explore `englogit`; decisive engagements, n = 7,116, standardised) [M]:

| factor | with in-fight terms | pre-fight only |
|---|---|---|
| log local max-health ratio | +1.83 (z 27.8) | +1.83 (z 31.0) |
| current/max health share | +0.57 (z 10.4) | +0.74 (z 14.7) |
| S started | −0.11 (z −2.5) | **+0.57 (z 19.3)** |
| body-count difference (given max health) | −0.86 (z −17) | −0.74 (z −16.6) |
| first-3-round damage share | **+0.96 (z 19.6)** | n/a |
| casts difference | +0.67 (z 17.3) | n/a |
| focus difference | +0.40 (z 9.1) | n/a |
| stuns in the first 3 rounds difference | −0.45 (z −12.6) | n/a |
| pseudo-R² | 0.38 | 0.28 |

[I] Starting is worth about a third of a max-health doubling, and it works through the early damage. At equal max health
fewer, stronger bodies beat more, weaker ones.

**Decisions that pay at the same state** [M]:

| state | best action | evidence |
|---|---|---|
| enemy within 4, ratio < 0.6 | leave (not hold, not fight) | net per 100: leave −7.4, fight −17.1, hold −18.4 |
| enemy within 4, ratio ≥ 0.6 | fight | +12.5 (0.6-0.9), +26.7 (0.9-1.2), +38 (1.2-2) |
| low health, enemy within 8 | recall if the enemy is 6+ away, else leave | died ≤ 15 r: recall 7%, leave 12-16%, fight 49-53% |
| nearest enemy health < 35% | attack or chase | kills ≤ 10 r: 53 per 100, own deaths 4.8% |
| nearest enemy health ≥ 70% | do not chase | chase kill 12% |

**Games** [M]:
- The S−O difference of each per-game decision feature was correlated with S winning, pooled over 638 games
  (`tables_v2.txt` w1).
- A joint logit used the 262 games that have every feature. Coefficients are standardised; z in brackets.

| feature (S − O) | pooled correlation | joint logit |
|---|---|---|
| share of own starts at max-health ratio < 0.67 ("bad starts") | **−0.44** (wins 0.24 vs losses 0.44) | **−0.96 (z −3.9)** |
| gems lost on death | −0.35 | **−1.27 (z −4.6)** |
| low health, enemy near: share recalled | +0.16 | +0.59 (z 2.9) |
| outmatched: share fought back | +0.28 | +0.64 (z 3.0) |
| enemy channel within 4: share punished | +0.20 | +0.36 (z 1.9) |
| first-3-round damage share | +0.29 | +0.54 (z 1.6) |
| chase kill rate | +0.39 | +0.26 (z 1.3) |
| max health at r300 | +0.30 | −0.08 (n.s. given the rest) |
| help rate (allies within 8 hitting back) | −0.03 | −0.45 (z −1.9) |
| keep farming on arrival, chase length, locks | −0.04 / −0.11 / 0.00 | n.s. |

- [I] These are associations. Kills and deaths are partly the result of being ahead.
- [I] Two terms read as real decisions: "bad starts" and losing the bag on death. Both keep their sign inside every study
  team (per-team correlations −0.28 to −0.59 and −0.27 to −0.56).

## 4. Team rule cards (their rules, thresholds, weak spots)

**prism best girl (#1)** — *Prism carry, fight first, never lock*:
- Rules [M]:
  - The Prism is drafted in all 116 games and carries the bag. pbg stops banking at about 100 gems (P(bank) 22% at
    100-199, 15% at 200+).
  - It tributes the carry once it ends the game: median 532 gems at r1194, 72% game-ending.
  - Starts 57% of fights; spell opener 59%; starter damage share 0.80.
  - Fights on at every local ratio: 53% even below 0.45; 62% when outnumbered by 2. Leaves below 35% own health.
  - Recalls 55 times a game at a median 0.46 health.
  - Fewest "silent" deaths: only 18% without a hit in the last 8 rounds.
  - Item lead at r300: 6,567 vs 5,991 max health.
- Weak spots [M]:
  - The carry tribute takes 54 turns at the median and completes in only 36% of attempts. With an enemy within 8,
    the carries of all three Prism teams complete 23%.
  - pbg places no altar locks, so it cannot guard the channel against an enemy lock.
  - The Prism tributes alone (killed at 704 gems, gem_fields r517).
  - P(bank) collapses for big bags, so its score lags its real strength. Watch the bag plus score.

**Intercontinental Fish (#2)** — *defend, chase, lock the carry*:
- Rules [M]:
  - No Prism. Vesper and Vendetta carry the rare big bags; banks 64-65% of 60-199 gem bags.
  - Starts only 46% and concedes the first strike (24% vs 31%), but nets +0.31 on its own starts and only −0.06 when
    started on.
  - Best chases: 31% end in a kill.
  - Locks 2.9 a game; locks 36% of enemy tributes of 150+ gems (great_wall r882 vs pbg).
  - Recall at 27% when low with an enemy near.
- Weak spots [M]: basic-attack openers (spells 32%); it is struck first. Strike first from range.

**Claudus Maximus (#19)** — *economy: bank small, guard-lock, keep farming*:
- Rules [M]:
  - Banks next after 65% of captures (89% of 60-99 gem bags), with a median bag of 22 and only 14% via spawn.
  - Guard-locks its own tributes: 3.4 locks a game.
  - Keeps farming when an enemy arrives: 67.5% overall, 71% when weaker; recalls only 6.4%.
  - The most selective starter: 37% of fights at <0.67, 54% at ≥1.5. Opens with spells 37% of the time.
- Weak spots [M]:
  - Most deaths: 12.7 a game vs its opponents' 10.6.
  - Walks into fights: 16% of deaths are approaches; 40.5% die without a hit in the last 8 rounds (its opponents 19%).
  - Loses the early fights (first kill 37% vs 48%) and nets −0.34 when started on.
  - Its farmers ignore threats: when weaker, the enemy takes its group 21% of the time.
  - Counter: hold just outside its reach and strike first; contest its camps when it farms alone.

**Pantheon (#6)** — *first strike everywhere, recall spam, Prism carry*:
- Rules [M]:
  - Starts 66% of fights at every power level (64-69%); first strike in 40% of contacts vs 18%; spell opener 57%;
    first-3-round damage share 0.63.
  - The most ratio-sensitive fighter: 36 / 38 below 0.45, 59 / 19 at ≥ 1.4.
  - Recall-spams: Cancel + Recall every turn, 40.8 completed recalls a game. Capture-recall combo on 42% of captures.
  - Prism carry: 94% of big bags; Prism tribute median 262.
  - Fewest deaths: 6.3 a game.
- Weak spots [M]:
  - Starts 36% of its fights at <0.67 max health.
  - Has the least max health at r300: 4,932 vs 6,276.
  - Loses 237 gems a game on deaths: 112 a game in loaded-Prism deaths alone.
  - Counter: do not step into its reach (it strikes first); answer its weak starts at full strength; kill the loaded
    Prism; ignore its "recalling" flag unless the channel is idle for a full round.

**conqueror_of_openai (#18)** — *trades badly, wins on economy*:
- Rules [M]:
  - Starts 47% of fights but wins only 32% of decisive ones: −0.08 per start, −0.41 when started on.
  - 41% of its starts are made at <0.67.
  - 13.3 deaths a game vs its opponents' 7.9; 46% of them isolated; 60% die fighting.
- Weak spots [M]:
  - First kill before r300 only 30% (54% for the opponent).
  - Gems lost 168 a game.
  - Counter: pressure early and pick off isolated bodies.

**Nyx (#31)** — *patient ranged openers, capture-recall, Prism carry*:
- Rules [M]:
  - Starts 62% of fights; the opener stood still 19% (the most); spell opener 58%.
  - Leaves early: at 35-50% own health, 33% fight vs 49% leave.
  - Capture-recall combo on 54% of captures, by all its champions (Vesper example: `t2/nyx/00ambush_c325017c`):
    - r622-623 kills the camp;
    - r626 recall;
    - r631 +33 gems and teleport home;
    - three shop actions.
  - 74 recall attempts a game, at a median 0.71 health.
  - Prism carry: 86% of big bags, median tribute 260.
  - Stuns 40% of big enemy tributes; no locks.
- Weak spots [M]:
  - A Nyx capturer standing still is mid-recall: one hit cancels both the recall and, if we contest the tile, the capture.
  - 24 loaded-Prism deaths (4,632 gems).
  - Its carry tributes complete 30% of the time.

## 5. Rules for god2

All inputs are observable at runtime:
- positions, health and max health of the champions in view;
- visible enemies' `gem_count()`, `is_submitting_gems()`, `is_recalling()` and `remaining_channel_time()`;
- `global_submitted_gems(side)` and the walking distance to the nearest altar.

Each body computes the local ratios over the allies and enemies it sees within 8. Thresholds are the measured
break-even points above; tune them on the ladder, not locally.

1. **Start gate (first strike).**
   - Start damage when the local max-health ratio is ≥ 0.87 and own health ≥ 50%.
   - At 0.67-0.87, start only when an enemy will reach us next turn anyway (+0.15 if we start, −0.28 if they do), or the
     target is channelling or below 35%.
   - Never start below 0.67: −0.16, and these starts lose games (logit −0.96).
   - Open with the 4-range spell when it is ready (Prism teams 57-59% spell openers, starter damage share 0.80).
   - Exploit: Pantheon and Nyx start 62-66% of fights, so stay one tile outside their reach and answer. cm, IFish and coo
     get struck first or walk in, so strike them first.
2. **Commit and retreat on own health, filtered by the local ratio.**
   - With an enemy within 4, keep fighting while own health ≥ 35% and the current-health ratio ≥ 0.6: fighting nets +12
     to +58 per 100.
   - Below 0.6, step out of reach. Do not hold (−18) and do not fight (−17).
   - Below 35% own health, disengage unless the target dies this turn.
3. **Farming under pressure.**
   - Enemy within 5-8: keep farming (died ≤ 20 r 3.5-9% at ratio ≥ 0.6; the default of every top team).
   - Enemy within 4: fight at ratio ≥ 0.9; at 0.6-0.9 keep farming only if the group dies within 2-3 rounds, else
     fight if our execution is good; below 0.6 leave or recall.
   - Never keep farming at < 0.6 with the enemy within 4. This is cm's leak: the enemy takes its group 21% of the time.
4. **Recall gate.**
   - Start a recall only with no visible enemy within 5 (85-95% complete). At ≤ 3, 37% complete and 23% die: walk out of
     reach first.
   - Low health with an enemy near: recall if the enemy is 6+ away, else leave toward allies or home.
5. **Capture-recall combo.**
   - Trigger: a body stands on a capture tile of a dead group, with health < 60% or gold for its next item, and no enemy
     within 5.
   - Start the recall on the turn after stepping on, once the capture timer has started. The 5-turn recall then finishes
     right after the 5-round capture lands. Nyx: step on r625, recall r626, capture and teleport r631.
   - Started on the step-in turn, the recall would leave one round before the capture. Nyx does this on 54% of its
     captures, Pantheon on 42%.
   - Cancel the recall if an enemy comes within 4.
6. **Punish recalls.** A visible enemy `is_recalling()` within our reach this turn: hit it (95.5% cancelled, 24% die).
   Pantheon spams recalls, so require that the channel has persisted for a round with no action.
7. **Punish tributes by stakes.**
   - Trigger: an enemy `is_submitting_gems()` with `gem_count()` ≥ 100, or enemy score + gem_count ≥ 1,000.
   - Send the nearest bodies. Use a stun (Ryth area stun, Prism slot 0, Tavi, Cassi, Ren, Marcella's empowered attack,
     the Heart of Ruin dash) and place an altar lock: 92-97% of tributes fail. Damage alone stops only 30%.
   - Ignore tributes under 60 gems unless the body is killable. The top teams ignore small ones too: 11% hit, 1% locked.
   - `remaining_channel_time()` tells how long we have: 26-108 turns for carries.
   - Always keep one altar lock (10 gold) on at least one living body.
8. **Guard our own big tributes.**
   - Before a tribute of 100+ gems, or a game-winning one: place our own lock on that altar first. An altar takes one
     lock, so it blocks their lock.
   - Start only with no enemy within 8 (23% vs 53% completion for carries) and with an ally within 6.
   - Bank 30-99 gem bags whenever an altar is within 12 walking tiles: the top teams bank 45-77% there. Bag losses are the
     strongest game-level term (−1.27).
9. **Prism carry, only if a Prism is drafted.**
   - Route captures to the Prism: +1.5 focus per gem gives 2.8-3.4x the damage and a 3-4x lower death rate at 150+ gems.
   - Tribute the carry only when score + bag ≥ 1,000, or late with no enemy within 8 (rule 8 guard first).
   - Keep the loaded Prism with an ally and away from camps: 36% of loaded-Prism deaths are isolated and 20 of 99 are to
     camps.
10. **Chase gate.**
    - Chase targets below 50% health (40% kill under 35%), for up to 10 rounds.
    - Stop when the target reaches its spawn, or when a second enemy enters 8 of us.
    - Do not chase targets above 70% (12% kill).
11. **Help radius.**
    - Answer an ally hit within 8: the top teams answer at 0-4 in 1 round (57%) and at 5-8 in 4 rounds (31%).
    - Do not leave a capture that lands within 2 rounds. Do not cross 12+ tiles to help (6% useful).
    - Answer to kill the attacker, not to save the victim: the victim's death rate barely moves, the attacker's goes from
      9% to 34%.
12. **After a won fight.**
    - Trigger: our kills > our losses within 10 tiles in the last 10 rounds.
    - Take the nearest group within 30 rounds; winners capture 0.8 groups (14 gems) per engagement.
    - Spend the kill gold: recall if no enemy within 5.
    - Do not chase deeper: winners "push" less than losers.
13. **Watch the enemy carry.**
    - Per visible enemy, track `gem_count()`. Track the score.
    - A loaded enemy Prism (150+) deals 3x damage: avoid 1v1 duels with it when it is above 50% health.
    - Its tribute is our best moment (rule 7). So is any time it walks alone or near camps.

## 6. Caveats

- **Vision**: "within 8" uses Chebyshev distance; walls and bushes are not modelled. Some arrivals and contacts were not
  seen by the bot.
- **Hidden power**: max health measures health items only. Focus and strength shards, and the Prism's gem focus, are
  hidden. "Outmatched" by max health is often not weaker for pbg or Pantheon.
- **Engagement definition**:
  - "Starter" is whoever lands damage first, not who decided to fight.
  - Engagements are damage clusters, so long skirmishes split and nearby fights merge.
  - Decisive-only win rates drop the many 0-0 engagements.
- **Sampling**: decision samples are taken every 3rd round and are autocorrelated. Use their proportions, not their n.
- **Selection**: action-outcome tables compare choices made at the same binned state, but bodies choose with information
  we do not bin (cooldowns, items). Treat "net per 100" as a guide, not an effect size.
- **Recall-spam teams**: Pantheon issues `Recall` every turn. Its recall-attempt rates use committed channels only and are
  reported apart. Recalls interrupted on their first tick are invisible for Pantheon.
- **Tribute outcome classes**: "cancel_other" mixes voluntary cancels and repeated re-starts. An example is
  boss_battle_4b1716d2, where pbg's Prism restarted a 3,884-gem, 389-turn tribute every few rounds from r1741 and never
  finished before r2000.
- **Captures**: detected from gem or gold jumps of a body standing at a camp group. The first-capture rounds may be off by
  1.

## 7. Reproduce

```
python tools/top2/fights/mk_sides.py C:/battlecode/cache/top2_fights
for k in pbg ifish cm pantheon coo nyx; do python tools/live/par.py 3 C:/battlecode/cache/top2_fights/sit_$k.jsonl \
  tools/top2/fights/sit.mjs C:/battlecode/cache/top2_fights/sides.json C:/battlecode/cache/top2_fights/geo.json -- \
  C:/battlecode/cache/t2dump/$k/*.json.gz; done
python tools/top2/fights/flat.py C:/battlecode/cache/top2_fights
python tools/top2/fights/agg.py C:/battlecode/cache/top2_fights            # tables_v1/v2
python tools/top2/fights/explore.py C:/battlecode/cache/top2_fights        # prism, combo, locks, englogit, gamelogit, arr5, punout, chase2, farm4
for k in ...; do python tools/live/par.py 3 C:/battlecode/cache/top2_fights/trib_$k.jsonl tools/top2/fights/trib_ctx.mjs \
  C:/battlecode/cache/top2_fights/sides.json -- C:/battlecode/cache/t2dump/$k/*.json.gz; done
python tools/top2/fights/trib_agg.py C:/battlecode/cache/top2_fights
```
