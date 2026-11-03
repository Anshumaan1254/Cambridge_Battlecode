# Top-30 macro strategy fingerprints (CAMBC 2026a, data of Nov 2-3 2026)

## Per-team fingerprint table (all 30 teams, plus us and reference groups)

### Takeaway
All 30 teams fit one fingerprint table built from 854 decoded top-30-vs-top-30 games. The teams split into a few families: Cassi&Issac economy teams (Mite, Intercontinental Fish, test4, MFF1, Olympus), a Durability/Ryth/Varg banker (Univardisty of Shingtonwash), and a large group of 13 teams that run the "standard" Ry-VV-Vd-Ma-HR roster. That standard roster is also ours. On almost every macro column our side looks like a top-30 losing side rather than like the teams we lose to.

### Cited Findings
- Coverage: per-side features come from 854 top-30-vs-top-30 games (1,708 sides) for economy and opening, from about 837 games (1,674 sides) for territory and big-group contests, and from 305 games (610 sides) for banking and capture routing. Per team that is 25-72 economy sides (column n) and 10-25 banking sides. Our side has 305 decoded v84-v88 games (economy), 551 (objectives) and 232 (banking); 80% of them are losses — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Column definitions:
  - Roster, first pick, det and CI% come from each team's last 400 ranked games, as do our own (n=400 each). det is the share of games whose ordered draft equals the team's most common draft on that map.
  - g300± is gems captured by r300 minus the mean of all top-30 sides on the same map. p2± is gems captured per 100 rounds in r151-400, against the same map mean.
  - walk% is the share of alive body-rounds spent walking.
  - fight%c, recall%c and the other "%c" columns are shares of contact body-rounds (an enemy champion within 6 tiles) spent fighting or holding a recall.
  - heldRec is held recalls per game. bigArrN is bodies present on arrival at a ≥30-gem group's respawn.
  - trib/g is tributes per game. bag is the mean bag size at tribute.
  - Ma cap% and CI cap% are each champion's share of the team's captured gems. mid% is the share of captured gems taken in the middle band.
  - raids, locks and deaths are per game. gold@600 is unspent gold at r600. emb1 r is the round of the first emblem.
  - Sources: [table.md](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/table.md), [draft_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/draft_out.txt), definitions in [econ.py](/home/claude/cambridge_battlecode/experiments/top30_nov3/economy/econ.py), [extract_obj.py](/home/claude/cambridge_battlecode/experiments/top30_nov3/objectives/extract_obj.py), [extract_all.py](/home/claude/cambridge_battlecode/experiments/top30_nov3/draft_bank/extract_all.py)

{{TABLE}}

- Olympus's bag of 248 comes from one artifact game with a recorded bag of 2,769. Its other 12 games range from 18 to 61. Treat that cell, and the bag-size correlation below, as fragile — [fp_sides.jsonl](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_sides.jsonl)
- Win rates inside these replays: Mite 0.656 (n=61 sides), IC 0.627 (59), UW 0.603 (68), Ad Astra 0.623 (61), newer team 0.441 (68), NEETCoders 0.508 (61), BattleCats 0.455 (55), test4 0.356 (59), print dont int 0.485 (66), Sponge 0.426 (61) — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)

### Inferences
- The table's "our" row mixes wins and losses (80% losses), so read it against the two rows below it: OPP (the same games) and the top-30 losing sides. On walk% (61 vs 53/56), r300 economy (−52 vs −6/−30), tributes (20.7 vs 30.2/16.0) and gold@600 (96 vs 230/174), we sit at or below the top-30 losers.

### Gaps
- Extraction was stopped at 854 of 1,201 decoded games for economy, about 837 for objectives, and the existing 305 for banking, because of the time budget. To extend it, re-run `experiments/deep_research_nov3/macro/run_extract.py econ_db|obj`, then `fp.py` and `mk_table.py`.
- Banking columns (trib/g, bag, Ma cap%, CI cap%, locks) rest on only 10-25 sides per team.

## Top-10 macro styles (one paragraph each)

### Takeaway
The top 5 do not share one roster. They share four habits: a fast economy after the opening (r151-400), frequent banking or a strong capture distribution, disengaging by recall rather than fighting when contacted, and a consistent itemization theme with one emblem family across the whole team. Ranks 6-10 mostly run the standard Ry-VV-Vd-Ma-HR roster or a single fixed roster.

### Cited Findings
- **1 Mite (2583).**
  - Draft: one roster, VV-Vd-CI-Ma-HR, on 216 of 226 five-champion maps. On 3-champion maps it plays VV-Vd-HR (62/105) or Vd-Ma-HR (40/105); on 4-champion maps Vd-CI-Ma-HR (65/69). VV is first pick in 74% of games, and the same map always gets the same ordered draft (det 1.00, 7 distinct sets in 400 games).
  - Opening and economy: it stacks the most bodies of the top 5 on its first group (3.92). The first group is usually a gold group: '$' 13, '$E' 12 and '$W' 12 of 61 sides. First capture comes at r51, it is +16 gems vs the map mean at r150 and +36 at r300, and it has the best r151-400 pace of the 30 (+14.6 per 100 rounds).
  - Contact: 17% fighting and 17% recalling.
  - Banking: 32.7 tributes a game with 62-gem bags. Captures are spread across VV 30%, Ma 26%, HR 14% and CI 12%. It places zero altar locks.
  - Items: Jungle emblems first on HR (Jungle-foc 44 games), Vendetta (Jungle-str 39), Marcella (Jungle-foc 37) and Issac (Jungle-str 31); VV takes Monster-str (37). It holds the most unspent gold at r600 (311). Its games end at r951 on average.
  - Sources: [table.md](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/table.md); [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt); [draft_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/draft_out.txt)
- **2 Intercontinental Fish (2562).**
  - Draft: Cassi&Issac in 98% of games. On 5-champion maps it plays Vd-CI-Ma-Wi-HR (117/238), or VV-Vd-CI-Vg-HR on large maps (45/72). On 3-champion maps it plays VV-CI-Ma (43/80). First pick is split VV 50% / Ma 50%, and the draft is map-deterministic (1.00).
  - Opening: earliest first capture of the top 5 (r40), stack 4.15, +32 at r300.
  - Contact: the least fighting of the top 5 (13%) and 19% recalling.
  - Captures: CI takes 21% of captured gems, the highest of the 30. 27.1 tributes a game with 37-gem bags. It locks altars (4.6 a game) and dies 12.7 times a game.
  - Items: Capture emblems first on HR (Capture-hp 24), Vendetta (Capture-hp 21) and Marcella (Capture-foc 23); Issac takes Prospector-hp (32) and Cassi Power-foc (29).
  - Sources: same three files
- **3 Univardisty of Shingtonwash (2524).**
  - Draft: Ryth first (71%), HR in 99% of games, Varg in 71%. It plays Ry-CI-Wi-Vg-HR on gem-scarce maps (63/233) and Ry-Vd-Ma-Vg-HR on rich maps (39/167); 25 distinct sets, det 0.86.
  - Banking: the extreme banker. 49.8 tributes a game with 20-gem bags, both the most frequent and the smallest of the 30.
  - Recalls and contact: 179 held recalls a game (2nd of 30) and 26% of contact time recalling (highest of the top 5), with 13% fighting.
  - Big groups: 1.79 bodies on arrival at big-group respawns, highest of the 30.
  - Raids and territory: 14.3 raids and about 6 raid kills a game, 60% of gems taken in the middle band, zero locks, and the fewest deaths of the top 5 (7.7).
  - Items: Durability emblems first on every champion (HR Durability-foc 45, Ryth Durability-hp 42, Varg Durability-str 36, Marcella Durability-foc 37). Latest first emblem of the 30 (r184) and the fewest shards at r300 (27).
  - Sources: same three files
- **4 Ad Astra (2516).**
  - Draft: HR first 56%, VV in 92% of games, Ren in 46%. It plays VV-Ma-Wi-Re-HR on scarce maps (44/217) and VV-Vd-CI-Re-HR on rich maps (42/183); on 3-champion maps VV-CI-HR (44/73). det 1.00.
  - Opening: the slowest of the top 10. First capture at r107, −13 vs map at r150, −28 at r300, and −8.8 per 100 rounds in r151-400. It still wins 62% of its top-30 games.
  - Captures: VV takes 41%, the most VV-centric capture routing of the top 5. 19.6 tributes a game with 53-gem bags, no locks.
  - Recalls, raids and kills: 102 held recalls, 14.0 raids and 11.4 kills a game.
  - Items: VV Prospector-str (43), HR Jungle-foc (42), Ren Jungle-foc (25).
  - Sources: same three files
- **5 newer team (2481).**
  - Draft: the most varied drafter of the 30 (42 distinct sets in 400 games), but still map-deterministic (1.00). Prism in 63% of games, Vendetta first 43%. It plays Vd-Ma-HR on 3-champion maps (39/81) and Vd-CI-Pr-Vg-HR on large maps (38/82).
  - Economy: +25 at r300 and the 2nd-best r151-400 pace (+13.8).
  - Raids, locks and kills: the fewest raids of the top 10 (4.6) and the most locks of the top 5 (5.9 a game). 4.8 kills a game, the lowest of the top 10.
  - Items: Prospector on every champion (Marcella Prospector-foc 35, Vendetta Prospector-str 28, HR Prospector-foc/hp 25/25). Earliest first emblem of the 30 (r92).
  - Banking: Marcella takes 32% of captures; 25.5 tributes a game with 33-gem bags.
  - Sources: same three files
- **6 NEETCoders (2443).** Plays the standard Ry-VV-Vd-Ma-HR (120/238) with HR first (76%) and CI in 26% of games. Its defining trait is that it almost never recalls in contact (4% of contact time) and fights 21% of it, with only 38 held recalls a game. Economy +10 at r300; 23 tributes a game with 51-gem bags. Prospector emblems first (VV Prospector-str 32, Marcella Prospector-foc 30) — same three files
- **7 BattleCats (2381).** Ry-VV-Vd-Ma-HR (64/245), but Prism is first pick 36% of the time and it plays 25 distinct sets; no CI. Slow banking cadence (16.3 tributes a game, 69-gem bags) and the fewest bodies at big-group respawns in the top 10 (1.23). About level economy (+2 at r300). Prospector/Treasure emblems; 2.7 locks a game — same three files
- **8 test4 (2366).** One roster, VV-CI-Ma-Wi-HR, on all 240 five-champion maps, HR first 83%, CI in 100%. It stacks the most bodies on its first group of all 30 (4.56). Marcella takes 46% of captures, the top-10 high; 71-gem bags; 12.8 deaths a game. Items: Marcella Capture-foc (49), HR Jungle-foc (42), Issac Prospector-hp (39), VV Treasure-str (41), Cassi Power-foc (35) — same three files
- **9 print dont int (2366).** Ry-Vd-Ma-Wi-HR on all 250 five-champion maps, with Willow first pick 84% (unique); no CI. It banks like UW: 32.2 tributes a game with 31-gem bags. It dies the least of the top 10 (6.8 a game) and is +13 at r300. Treasure emblems on every champion (HR Treasure-foc 54, Vendetta Treasure-str 45, Marcella Treasure-foc 45) — same three files
- **10 Sponge (Albert and Bob) (2362).** Ry-VV-Vd-Ma-HR (145/234) with HR first in 100% of games; det 0.82. Slow economy: −21 at r300 and −9.3 per 100 rounds in r151-400. VV takes 34% of captures; 26.6 tributes a game with 45-gem bags; 3.1 locks a game. Capture emblems (HR Capture-hp 53, VV Capture-str 31, Marcella Capture-foc 33) and Treasure on Ryth/Issac — same three files

### Inferences
- Ad Astra's slow economy despite a 62% top-30 win rate suggests it wins later in the game through kills and raids rather than through the opening. That is the exception among the top 5; the other four are +25 to +36 gems at r300.
- A "theme" itemization (one emblem family across the whole team) is the norm at every rank, so the family itself is not what separates the top. Mite's Jungle, IC's Capture and UW's Durability are each unique among the top 5.

### Gaps
- Fight micro (who hits first, focus fire) belongs to other research streams and is not covered here.
- Per-team values rest on 25-72 sides, so small differences between neighbouring teams in the table are noise.

## Draft: rosters by map class, pick order, adaptation to the opponent

### Takeaway
Every top-30 team, and us, drafts a fixed ordered roster per map. There is no measurable reaction to the opponent's revealed picks, although the rules allow it. What differs is roster choice: the top 5 use Cassi&Issac far more and Ryth far less than ranks 20-30, and they vary the roster by map class. Many rank 20-30 teams, and we, play one standard Ry-VV-Vd-Ma-HR roster on every map.

### Cited Findings
- The rules let picks react: "Champions are picked one by one … both teams select champions simultaneously, revealing their picks as they go," and a team may pick a champion the opponent already holds — [GameRules.md](/mnt/user-data/attachments/d0c2bc72-a5f9-5bbd-beb3-d573bc0416a1/d3e01b7b-GameRules.md)
- Determinism, measured on each team's last 400 ranked games (Nov 2 17:20 to Nov 3 06:30 UTC, about 4.7 games per map): the share of games with the team's modal ordered draft on that map is 1.00 for 14 of 30 teams, at least 0.86 for 27 of 30, and lowest for policy wonk at 0.74. Ours is 1.00 — [draft_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/draft_out.txt)
- Adaptation test: information gain of pick k about the opponent's revealed picks 1..k−1, given map and own earlier picks, compared with a null that shuffles opponent drafts within map (20 shuffles).
  - The real gain minus the null gain is at most 0.014 bits for 29 of 30 teams, for example UW 0.116 vs 0.107, Sponge 0.278 vs 0.264, prism best girl 0.287 vs 0.276.
  - It is 0 vs 0 for every fully deterministic team.
  - Only policy wonk shows an excess: 0.80 vs 0.64 bits — [draft_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/draft_out.txt)
- Distinct champion sets in 400 games:
  - Top 5: Mite 7, IC 10, UW 25, Ad Astra 15, newer team 42 (median 15).
  - Ranks 20-30: EE 3, conqueror 4, procless 5, MFF1 6, Olympus 7, jazz 8, SSSA 9, RLP 10, prism 10, new team(4) 13, :3 23 (median 8).
  - HouseOfCoders: 12.
  - Source: [draft_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/draft_out.txt)
- Cassi&Issac pick rate:
  - Top 5: Mite 74%, IC 98%, UW 43%, Ad Astra 57%, newer team 39%.
  - Ranks 20-30: below 15% for 8 of 11 teams; the exceptions are MFF1 61%, Olympus 72% and new team(4) 23%.
  - Us: below 15% (HR 100, Ry 84, VV 84, Vd 82, Ma 75, Varg 16).
  - Team-level share of gems captured by Cassi/Issac correlates with rating (Spearman ρ=+0.36 over 30 teams); T5 12.6% vs T20 2.7%, ours 0%.
  - Sources: [draft_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/draft_out.txt); [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Ryth pick rate:
  - Top 5: Mite 0%, IC 0%, UW 71%, Ad Astra 15%, newer team 7%.
  - Ranks 20-30: conqueror 57, EE 56, procless 69, prism best girl 75, jazz 35, :3 27.
  - Us: 84%. Ryth takes 13% of our captured gems vs 3% (T5) and 4% (T20).
  - Sources: [draft_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/draft_out.txt); [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Standard roster: Ry-VV-Vd-Ma-HR is the modal 5-champion roster for NEETCoders (120/238), BattleCats (64/245), Sponge (145/234), Trzy Kwaterki (138/229), T1 (182/237), subscribe (254/254), Nyx (235/235), JukeFall (241/253), conqueror (233/233), EE (223/223), procless (256/256) and HouseOfCoders (172/235). None of the top 5 uses it as a modal roster — [table.md](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/table.md)
- Map-class adaptation by the top 5:
  - UW switches between scarce maps (gems per champion ≤92: Ry-CI-Wi-Vg-HR, 63/233) and rich maps (Ry-Vd-Ma-Vg-HR, 39/167).
  - Ad Astra switches the same way (scarce VV-Ma-Wi-Re-HR 44/217; rich VV-Vd-CI-Re-HR 42/183).
  - IC adds Varg and VV on large maps (VV-Vd-CI-Vg-HR 45/72).
  - Mite changes only with the champion count: 3-champion maps VV-Vd-HR 62/105, 4-champion maps Vd-CI-Ma-HR 65/69.
  - Most rank 20-30 teams use the same roster on scarce and rich maps (EE 119/104, procless 127/129, conqueror 115/118 games of the modal roster).
  - Breakdowns by monolith, islands, bush (≥15% bush tiles) and altar count are in the source file.
  - Source: [draft_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/draft_out.txt)
- Number of bodies: team mean bodies per game is 5.06 for T5 vs 4.63 for T20 (ρ=+0.21) and 4.39 for us. CI is one pick but two bodies — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt); [GameRules.md](/mnt/user-data/attachments/d0c2bc72-a5f9-5bbd-beb3-d573bc0416a1/d3e01b7b-GameRules.md)

### Inferences
- Adapting to the opponent's picks is not where the top gets its edge. Nobody does it measurably, so a counter-pick module is low priority.
- The draft levers that do track rating are fielding Cassi&Issac (an extra body that also captures) and a less Ryth-centric roster, plus varying the roster by map class.
- Whether CI causes the higher rating, or just comes with the strongest bots, cannot be separated from these data. UW reached rank 3 with Ryth first, so Ryth is not disqualifying.

### Gaps
- The 400-game window covers only about 13 hours. Version changes inside it could add to the small variation seen in det below 1; that does not affect the no-adaptation conclusion.
- No per-roster win rates on matched maps were computed here; the draft_bank stream has some of these.

## Opening (r1-300): first targets, stacking, first capture, gems by r150/r300

### Takeaway
The strongest teams are ahead by r150 and further ahead by r300: +7 / +17 gems vs the map mean for the top 5, against −3 / −8 for ranks 20-30. How they open (first target, own-side start, stack size, first-capture round) barely differs among the top 30. We differ from everyone: we split across more first targets with fewer bodies on each, and we are −23 / −52 gems vs the map mean.

### Cited Findings
- Gems captured by r150, map-adjusted: T5 +7.4 vs T20 −3.0 (ρ=+0.35, n=30 teams). By r300: T5 +16.9 vs T20 −8.2 (ρ=+0.40).
- Raw means: T5 88 and 198, T20 77 and 172. Our 305 games: 57 and 128 (map-adjusted −23 and −52), against 81 and 174 for our opponents in the same games.
- Losses only, map-adjusted at r300: our losing sides −57.7 (n=243), top-30 losing sides −26.5 for ranks 1-5 (n=131) and −36.7 for ranks 20-30 (n=292).
- Source for the above: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- First capture round: raw T5 59.7 vs T20 76.1 (ρ=−0.28), but map-adjusted T5 −0.5 vs T20 +0.6 (ρ=−0.10), so the raw gap comes from the map mix. Ours is 68.6 vs OPP 64.9, about +12.6 rounds vs map — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Stacking (most bodies whose first visited group is the same): T5 3.55 vs T20 3.39 (ρ=+0.03). Us 2.66 vs OPP 3.19. Distinct first groups: T5 2.15, T20 1.95, us 2.48, OPP 2.13 — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- First group touched:
  - It is on the team's own side (closer to own spawn) for 87-90% of sides in every group (T5 0.88, T20 0.90, us 0.90).
  - It holds 17.7 gems for T5 vs 21.7 for T20 (ρ=−0.28) and 13.6 for us.
  - The most common first-group types in the top 10 are gold-only ('$') or gold+wolf/elk, for example Mite '$' 13 / '$E' 12 / '$W' 12 of 61 sides.
  - Sources: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt); opening visit definitions in [econ.py](/home/claude/cambridge_battlecode/experiments/top30_nov3/economy/econ.py)

### Inferences
- The top-team edge at r300 grows out of the r151-400 phase (next section) more than out of the first target. Our opening deficit (−23 at r150) is already larger than the whole T5-T20 gap at r300 (25 gems). For us the opening is a first-order problem in a way it is not among the top 30.

### Gaps
- "Time to first capture" is measured per team, not per body.
- Stack size uses the first group each body visits; a later re-stack within r1-150 is not captured.

## Farming pace, walking, farming through contact, contested big groups

### Takeaway
Among the top 30, rating tracks sustained pace in r151-400 (ρ=+0.46) and what bodies do in contact. Strong teams spend contact time recalling and repositioning rather than fighting, and they bring more bodies to big-group respawns. Walking share and the share of camp hits made under contact do not separate the top 30. They do separate us: we walk 61% of alive time (opponents 53%) and almost stop farming when an enemy is within 6.

### Cited Findings
- Pace (gems per 100 rounds vs map mean):

  | Phase | T5 | T20 | ρ | Us | OPP |
  |---|---|---|---|---|---|
  | r1-150 | +4.9 | −2.0 | +0.35 | −15.4 | +0.2 |
  | r151-400 | +7.2 | −3.7 | +0.46 | −20.5 | −2.6 |
  | r401-800 | +11.9 | −5.4 | +0.34 | −32.4 | +0.9 |
  | r801+ | +14.9 | −6.8 | +0.29 | | |

  In losses only, r151-400: our losing sides −23.1, top-30 losing sides ranks 1-5 −12.2, ranks 20-30 −16.9 — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Walking: T5 53.4% vs T20 54.5% of alive body-rounds (ρ=−0.15). Us 60.6% vs OPP 53.5% (map-adjusted us +7.1 points, top-30 losers +2.1) — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Contact frequency: an enemy is within 6 for 26.1% (T5) vs 25.4% (T20) of alive body-rounds, and 27.3% for us vs 24.9% for OPP — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- What bodies do in contact (shares of contact body-rounds):

  | Activity | T5 | T20 | ρ | Us | OPP |
  |---|---|---|---|---|---|
  | Fighting | 14.8% | 20.0% | −0.50 | 17.2% | 21.5% |
  | Holding a recall | 20.0% | 10.1% | +0.52 | 14.8% | 10.8% |
  | Hitting camps | 7.1% | 7.2% | −0.02 | 3.8% | 7.5% |
  | Standing on a reward | 2.3% | 3.7% | −0.49 | 1.6% | 2.8% |
  | Walking | 48.3% | 49.3% | | 59.0% | 49.3% |

  Source: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- The style holds in losses. Top-30 losing sides from ranks 1-5 (n=129) recall in 18.8% and fight in 14.6% of contact time, against 9.8% and 19.7% for losing sides from ranks 20-30 (n=290) — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Recalls:
  - Held recalls per game: T5 101 vs T20 57 (ρ=+0.43). Us 78, OPP 70.
  - Recalls classified "reposition": T5 47% vs T20 30% (ρ=+0.45). Us 47%, OPP 26%.
  - Recalls classified "heal": T5 28% vs T20 40% (ρ=−0.40).
  - Sources: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt); recall classes per [extract_obj.py](/home/claude/cambridge_battlecode/experiments/top30_nov3/objectives/extract_obj.py)
- Farming through contact: the share of camp hits made with an enemy within 6 is 12.9% (T5) vs 12.2% (T20), ρ=−0.07. Ours is 7.4% vs OPP 12.3% (map-adjusted −6.5 points) — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Big groups (≥30 gems), per respawn cycle:

  | Measure | T5 | T20 | ρ | Us | OPP |
  |---|---|---|---|---|---|
  | Bodies present on arrival | 1.47 | 1.29 | +0.48 | 1.39 | 1.40 |
  | First to arrive | 51.6% | 48.6% | +0.29 | | |
  | Won when both teams arrived | 54.7% | 48.0% | +0.20 | 32.7% | 67.3% |
  | Arrival vs respawn (rounds) | −59 | −74 | | −60 | |
  | Share of all big-group rewards taken | 55.1% | 47.9% | +0.19 | 36.6% | 63.4% |

  The arrival row is the mean offset from the respawn round; negative means arriving after it. Top-30 losing sides take 29.7% of big-group rewards. In losses, bodies on arrival are equal (ranks 1-5 1.26 vs ranks 20-30 1.27) — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)

### Inferences
- The clearest style marker of the top 5 is disengaging when contacted: holding a recall instead of fighting, recalling to reposition rather than to heal, and doing it in losses too. That points to a rule, not an outcome.
- Bringing more bodies to big respawns looks partly outcome-driven, since the losing sides show no difference.
- Our contact problem is different from the T20 problem. We do not over-fight (17% vs OPP 21.5%). We stop farming and capturing and walk instead (59% of contact time), which fits the earlier finding that we walk away from camps on contact.

### Gaps
- "Contact" means an enemy champion within 6 tiles at the start of the round. Whether the enemy was actually threatening, or which side initiated, is not distinguished.
- Respawn-contest numbers for teams with few big-group maps rest on few cycles.

## Capture routing and banking

### Takeaway
Stronger teams bank much more often: 30.9 tributes a game for the top 5 vs 19.2 for ranks 20-30 (ρ=+0.49). They also spread captures across more carriers, including Cassi&Issac. Altar choice (spawn altar about 73% for everyone), deaths while carrying, and Marcella's capture share do not separate them. We tribute as rarely as ranks 20-30 (20.7 a game vs our opponents' 30.2), with small bags (33). Our captures run through HR, Vendetta and Ryth rather than Marcella and CI.

### Cited Findings
- Tributes per game: T5 30.9 vs T20 19.2 (ρ=+0.49, banking rows n=610 top-30 sides). Losing sides only: ranks 1-5 19.2 vs ranks 20-30 14.2. Us 20.7 (n=232) vs OPP 30.2 (n=318) — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Bag size at tribute: T5 41 vs T20 74 (ρ=−0.35). Without Olympus's artifact game the T20 mean is about 57. UW banks 20-gem bags 49.8 times a game, print dont int 31-gem bags 32.2 times; Mite uses 62-gem bags 32.7 times. Us 32.6, OPP 41.6 — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt); [table.md](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/table.md)
- Who captures (share of the team's captured gems):

  | Carrier | T5 | T20 | ρ | Us | OPP |
  |---|---|---|---|---|---|
  | Marcella | 25% | 31% | −0.15 | 14% | 28% |
  | Vesper Vale | 19% | 24% | −0.12 | 26% | 23% |
  | Heart of Ruin | 16% | 12% | +0.31 | 26% | 14% |
  | Vendetta | 11% | 13% | | 19% | 14% |
  | Cassi/Issac | 12.6% | 2.7% | +0.36 | 0% | 3% |
  | Ryth | 3% | 4% | | 13% | 9% |
  | Largest single carrier | 44% | 46% | | 41% | |

  Source: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Altars: spawn-altar share of tributes T5 73% vs T20 74% (ρ=−0.24); us 78%, OPP 69%. Tributes made with an enemy within 6: T5 27% vs T20 22%; us 15%, OPP 18% — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Gems lost on death per game: T5 85 vs T20 107 (draft_bank rows, ρ=−0.12). Economy rows: T5 115 vs T20 181. Top-30 losing sides lose 30.8% of captured gems on death vs 6.9% for winners; ours 14.4%, OPP 7.8%. Deaths while carrying ≥20 gems: T5 1.37 vs T20 1.36 a game — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Rounds carried per tribute: T5 75.5 vs T20 105.8 (ρ=−0.28); us 80.2, OPP 62.9 — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)

### Inferences
- With bag sizes similar to our opponents' (33 vs 42), our banking gap comes from too few tributes. That in turn follows from capturing too little: 618 vs 931 gems captured a game, us vs OPP.
- Concentrating captures on HR, Vendetta and Ryth is unusual. No top-10 team routes 26% of captures through HR or 13% through Ryth.

### Gaps
- Banking rows exist for only 305 top-30 games (10-25 sides per team), because the extended extraction did not reach the banking stage. Per-team banking columns are noisy.
- Tribute cadence by phase (early vs late) was not computed.

## Items: emblem and shard build order per champion; shop timing

### Takeaway
Each strong team commits to one emblem family across its roster: Jungle (Mite), Capture (IC), Durability (UW), Prospector (newer team, NEETCoders, BattleCats), Treasure (print dont int, policy wonk). Shard counts and first-emblem timing barely correlate with rating once maps are matched. What we buy is not unusual (Jungle and Prospector); what differs is that we earn about 35% less gold and keep almost none of it unspent.

### Cited Findings
- First emblem (family-stat) by team and champion, count of games:
  - Mite: HR Jungle-foc 44, Vendetta Jungle-str 39, Marcella Jungle-foc 37, Issac Jungle-str 31, VV Monster-str 37.
  - IC: HR Capture-hp 24, Vendetta Capture-hp 21, Marcella Capture-foc 23, Issac Prospector-hp 32, Cassi Power-foc 29.
  - UW: Durability on every champion (HR -foc 45, Ryth -hp 42, Varg -str 36, Marcella -foc 37).
  - Ad Astra: VV Prospector-str 43, HR Jungle-foc 42, Ren Jungle-foc 25.
  - newer team: Prospector on every champion (Marcella -foc 35, Vendetta -str 28, HR -foc/-hp 25/25).
  - Us: HR Jungle-hp 268, VV Prospector-str 231, Vendetta Prospector-str 225, Ryth Jungle-hp 206, Marcella Jungle-hp 199 (of about 305 games).
  - Source: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Marcella's first-emblem stat is focus for Mite, IC, UW, newer team, NEETCoders, BattleCats, test4, print dont int and Sponge, and hp for Ad Astra (Prospector-hp 24) and for us (Jungle-hp 199) — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Timing:
  - First emblem round: T5 126 vs T20 117 (ρ=+0.12); us 144, OPP 136.
  - Shards at r300: raw T5 39.4 vs T20 37.7; map-adjusted ρ=+0.40 (T5 +1.4 vs T20 −1.6); us 29.8, OPP 31.5.
  - Emblems at r300 map-adjusted: ρ=+0.35.
  - First shop round is about 62 for all groups; ours is 56.
  - Share of shop trips made on foot rather than by recall: T5 12% vs T20 18% (ρ=−0.19).
  - Source: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Gold:
  - Unspent at r600: T5 284 vs T20 232 (ρ=+0.25); us 96, OPP 230, top-30 losers 175.
  - Unspent at r150: T5 160, us 68, OPP 147.
  - Gold earned per 100 rounds in r1-150: T5 347, T20 358, us 216, OPP 325.
  - Source: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)

### Inferences
- Our item shortfall (−7.5 shards at r300 map-adjusted) mostly follows from earning less gold, not from a wrong build. Top teams carry 150-300 unspent gold through r600, which suggests they save for emblem purchases rather than spending as soon as they can; we spend down to about 70-100.

### Gaps
- The full build order beyond the first emblem is in the economy rows (`builds`) but was not summarized per team.
- The "hp vs foc" Marcella difference is an observation without a measured effect.

## Territory and denial: middle and enemy-half captures, raids, steals, locks, wards

### Takeaway
Territory and denial counts barely separate the top 30. Mid-band capture share, enemy-half captures, wards, locks and steals all have |ρ| ≤ 0.27. The exception is raids: stronger teams raid for kills (ρ=+0.43), while weaker teams' raids take more gems (raid gems ρ=−0.38). In our games, opponents raid us for 30 gems a game while our raids take 6.

### Cited Findings
- Share of captured gems taken in the middle band: T5 54.7% vs T20 49.6% (ρ=+0.16); us 49.0%, OPP 59.2%. Enemy band: about 2.9% for both groups; us 2.1%, OPP 4.5% — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Raids per game: T5 9.7 vs T20 9.2 (ρ=+0.22). Kills on raids: T5 3.2 vs T20 2.1 (ρ=+0.43). Gems captured on raids: T5 16.6 vs T20 24.4 (ρ=−0.38). Us: 13.2 raids, 1.9 kills, 5.6 gems; OPP: 14.0 raids, 2.3 kills, 29.5 gems. UW 14.3 raids and Ad Astra 14.0 vs newer team 4.6 — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt); [table.md](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/table.md)
- Steals (capturing a group the other side did most of the damage on): 0.40 (T5) vs 0.43 (T20) a game; steal gems 28.6 vs 35.4 (ρ=−0.27). Us 0.55 a game and 36 gems, OPP 0.79 and 56 gems — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Altar locks: T5 2.1 vs T20 1.9 a game (ρ=+0.11). Mite, UW and Ad Astra place none; IC 4.6, newer team 5.9; us 1.1, OPP 3.0 — [table.md](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/table.md)
- Wards per game: T5 132 vs T20 128 (ρ=+0.06); by r300 43 vs 38; coverage at r600 24% in both groups. Us 232 and OPP 261 in our own games — a different map/opponent mix, so not like-with-like — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)

### Inferences
- Denial is not what the top 5 do differently. They raid to kill and reset enemy farmers, not to take gems. We lose about 24 gems a game net on raids against our opponents (5.6 taken vs 29.5 conceded), which fits the walking and leaving-camps-on-contact pattern above.

### Gaps
- Our ward counts can only be compared with our opponents in the same games, and they are similar there (232 vs 261).

## Endgame: reaching 1000 vs round 2000, closing games

### Takeaway
Top-30 wins come from reaching 1000 banked gems. Tiebreak (round 2000) wins are 4.2% of top-30 ranked wins, the same for ranks 1-5 and 20-30, against 10.5% of ours. Stronger teams finish sooner: their games end at r989 vs r1084 for ranks 20-30 (ρ=−0.52), and our games last 1217 rounds.

### Cited Findings
- Ranked results from the lists (400 games per team): 259 of 6,112 top-30 wins (4.2%) were tiebreak_gems or tiebreak_gold at round 2000. Ranks 1-5: 53 of 1,167 (4.5%); ranks 20-30: 94 of 2,238 (4.2%). HouseOfCoders: 21 of 200 wins (10.5%). Tiebreak endings are 291 of the 6,795 matches in the ranked union — [draft_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/draft_out.txt); [matches_current.jsonl](/home/claude/cambridge_battlecode/experiments/top30_nov3/matches_current.jsonl)
- In decoded games, the winner had banked ≥1000 in 97.5% of top-30 wins (T5 98.3%, T20 97.7%), 88.7% of our wins (n=62) and 93.4% of our opponents' wins (n=243) — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Game length: T5 games end at r989 vs r1084 for T20 (ρ=−0.52); ours at r1217. Round of reaching 1000 in wins: T5 931 vs T20 1022 (ρ=−0.29); our wins 1183 (n=34), our opponents' wins 1139 — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Final margins: top-30 winners lead by +577 banked gems on average; T5 team mean margin +112 vs T20 −44 — [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)

### Inferences
- Top teams close games by banking steadily: about 30 tributes a game in wins (top-30 winners 29.6) until they cross 1000, not by a late sprint or stalling to round 2000. Our higher tiebreak share is consistent with a slower bank rate rather than a deliberate endgame plan.

### Gaps
- No per-round "who leads" trajectories were computed for the top 30 here (the confusion and nemesis streams have them for some games), so comeback rates are unknown.

## What separates ranks 1-5 from ranks 20-30 and from us

### Takeaway
Across the 30 teams, the macro features that track rating (|ρ| ≥ 0.40, n=30) are:
- shorter games (−0.52);
- recalling rather than fighting in contact (+0.52 / −0.50);
- more kills (+0.50);
- more tributes (+0.49);
- more bodies at big respawns (+0.48);
- faster r151-400 pace (+0.46);
- reposition-type recalls (+0.45);
- more raid kills (+0.43);
- more gems by r300 (+0.40);
- fewer heal recalls (−0.40).

Opening shape, walking share, contested camp-hit share, deaths, wards, locks, steals, altar choice and the first-emblem round do not separate the top 30 (|ρ| ≤ 0.2). Against our own opponents in the same games, our largest gaps are elsewhere:
- economy and pace (−46 gems at r300; −15 to −32 gems per 100 rounds by phase);
- walking (61% vs 53%);
- farming through contact (7.4% vs 12.3% of camp hits);
- tribute count (20.7 vs 30.2);
- gold income (216 vs 325 per 100 rounds early);
- capture routing (Marcella 14% vs 28%; CI 0%).

### Cited Findings
- Spearman ρ with rating over 30 teams, with T5 vs T20 team-level means. |ρ| ≥ 0.36 is significant at p < 0.05 (two-sided, n=30).

  | Feature | ρ | T5 | T20 |
  |---|---|---|---|
  | Game length | −0.52 | 989 | 1084 |
  | Contact share recalling | +0.52 | 20.0% | 10.1% |
  | Kills per game | +0.50 | 10.3 | 7.5 |
  | Contact share fighting | −0.50 | 14.8% | 20.0% |
  | Contact share on reward tiles | −0.49 | 2.3% | 3.7% |
  | Tributes per game | +0.49 | 30.9 | 19.2 |
  | Bodies at big-group arrival | +0.48 | 1.47 | 1.29 |
  | r151-400 pace vs map | +0.46 | +7.2 | −3.7 |
  | Reposition-recall share | +0.45 | 47% | 30% |
  | Held recalls | +0.43 | 101 | 57 |
  | Raid kills | +0.43 | 3.2 | 2.1 |
  | r300 gems vs map | +0.40 | +16.9 | −8.2 |
  | Heal-recall share | −0.40 | 28% | 40% |
  | Shards at r300 vs map | +0.40 | +1.4 | −1.6 |
  | Raid gems | −0.38 | 16.6 | 24.4 |
  | CI capture share | +0.36 | 12.6% | 2.7% |
  | r150 gems vs map | +0.35 | +7.4 | −3.0 |

  Source: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Non-separating features (ρ):
  - deaths per game +0.06 (T5 10.6 vs T20 10.4);
  - walk share −0.15;
  - contested camp-hit share −0.07;
  - opening stack +0.03;
  - mid-band share +0.16;
  - enemy-band share −0.05;
  - wards +0.06;
  - locks +0.11;
  - steals −0.17;
  - spawn-altar share −0.24;
  - first-emblem round +0.12;
  - share of wins by reaching 1000 +0.03.

  Source: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- Like-with-like for us: same games vs OPP (305 economy games, 551 objectives games, 232/318 banking sides), and our losses vs top-30 losing sides (ours n=243, ranks 1-5 n=131, ranks 20-30 n=292).
  - r300 gems vs map: ours −57.7 in losses vs −26.5 (ranks 1-5) and −36.7 (ranks 20-30).
  - r151-400 pace: −23.1 vs −12.2 and −16.9.
  - Recall share of contact time: 14.4% vs 18.8% and 9.8%.
  - Fight share of contact time: 17.0% vs 14.6% and 19.7%.
  - Walk share: 61.1% vs 55.9% and 56.1%.
  - Contact time hitting camps: 3.6% (ours) vs 5.7% (ranks 1-5 losing) and 6.5% (ranks 20-30 losing).
  - Source: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)
- In the same games vs OPP:
  - gems captured per game 618 vs 931;
  - tributes 20.7 vs 30.2;
  - big-group rewards taken 36.6% vs 63.4%;
  - raid gems 5.6 vs 29.5;
  - gold earned r1-150 216 vs 325 per 100 rounds;
  - unspent gold at r600 96 vs 230.
  - Source: [fp_out.txt](/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/fp_out.txt)

### Inferences
- Two rules separate the top 5 from ranks 20-30 and hold in their losses too, so they look like strategy rather than outcome:
  - disengage-by-recall when contacted (recall 19-20% vs about 10% of contact time, fight 15% vs 20%);
  - bank often (31 vs 19 tributes; 19 vs 14 in losses).
- Faster r151-400 pace and more gems by r300 also hold in losses.
- On disengagement and fighting we already sit between the top 5 and ranks 20-30. Our gap to rank 30 is not mainly the same gap that separates rank 1 from rank 30. It is a lower economic floor:
  - we walk more;
  - we stop farming in contact;
  - we split the opening;
  - we route captures through HR, Vendetta and Ryth instead of Marcella and CI;
  - we earn about a third less gold;
  - we tribute about a third less often.
- These are the macro gaps the v95 vs v88 ladder tie leaves unaddressed. If v95's +133 gems a game in local panels came from fights or execution, it would not move these economy and contact-behaviour numbers. That is untested here because no v95 replays were analysed.
- Fielding Cassi&Issac is the one draft change that correlates with rating (+0.36), but its effect cannot be separated from bot quality with these data.

### Gaps
- Correlations are across 30 team means with 25-72 sides each. Many features co-vary with winning, and the T5 losing vs T20 losing comparison is the only outcome control used.
- No v95 games were analysed. Our numbers are v84-v88 (305 economy games, 80% losses; v88 alone n=119, all losses).
- 347 of the 1,201 decoded top-30 games were not processed for economy, about 364 for objectives, and 896 for banking, because of the time budget. The extraction drivers in `experiments/deep_research_nov3/macro/` can resume.
