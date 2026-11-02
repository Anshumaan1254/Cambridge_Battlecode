# Why GOD v75 / v79 lose to Mite (and IC), and the plan that fixes it

Data: the two uploaded loss sets (`v75_lost_vs_IC_Mite.zip` = 65 Mite games of website v75 = GOD v18 = `god__3_.zip`;
`v79_lost_vs_IC_Mite.zip` = 65 Mite games of website v79 = GOD v22 = `god22_1.zip`), plus the 70 IC-vs-v75 games already
decoded in the repo (`experiments/ic_oct26_v18/v18final/`, 8 wins / 62 losses) as the cross-check, plus the 70 official maps.
Every replay was decoded with the repo's `tools/replay/decode.mjs` (engine 2.0.0 wasm) and analysed round by round with the
scripts in `analysis/` (listed in Appendix C). All numbers below are per game unless stated. "Us" = HouseOfCoders, "them" = Mite
unless the table says IC.

---

## 0. The answer in one page

**The thing they do every time: Mite (and IC) take the richest camp groups of the map and never let go of them, and they
convert every contact near those groups into a kill because we walk in and then run.**

| fact (65 Mite games of v75; the 65 v79 games give the same numbers within ±0.1) | us | Mite |
|---|---|---|
| richest group of the map captured, times per game | **0.3** | **6.7** |
| middle-zone gem groups, captures per group per game | 0.73 | 6.51 |
| gems captured from the 3 richest groups, share of own total | 25 % | 55 % |
| gems captured in the middle zone | 96 | 679 |
| gems captured in own half | 272 | 398 |
| rounds from a rich group's respawn to the first hit on it | mean 150, median 28 | **mean 30, median 0** (≤ 5 rounds in 62 % of cycles) |
| fights started (first champion hit of an engagement) | 25 % | **75 %** |
| when Mite starts the fight: defender dies / attacker dies within 30 rounds | 52 % / 12 % | |
| when we start the fight (even 2v1, hp ratio 2.0): defender dies / attacker dies | 10 % / 40 % | |
| deaths | 10.0 | 3.1 |
| banked gems at the end | 323 | 1004 |

The map pool makes this map-independent: in 57 of the 70 official maps the richest group is in the middle, in 46 of 70 at least
half of all gems are in the middle, and the three richest groups hold 60 % of a map's gems on average (Appendix B). Whoever owns
the richest groups owns the game; the organisers' new maps follow the same generator, so this will stay true.

Everything else we measured is downstream of that one fact:

1. **Economy snowball.** Owning the rich groups gives Mite 2.4× our gold (6,449 vs 2,613), 67 shop visits vs 39, and ~2× our item
   stats from round 600 on (shard-equivalents per body: r200 4.8 vs 3.3, r400 14.2 vs 8.8, r600 27.9 vs 15.1, r800 43.2 vs 19.3).
   From r300 on every fight is against a body with more stats than ours.
2. **Fight execution.** Even at equal stats (r < 300) we lose exchanges: in the 10 rounds after Mite's first hit we land 3.8 champion
   hits and lose 832 hp; Mite lands 7.0 and loses 255. We walk *toward* the enemy for 2+ steps before the first hit in 70 % of our
   deaths, then move in 20 of the last 25 rounds before dying, landing 2.2 hits while taking 9.9. Mite's bodies hit back, chain
   stuns, and keep hitting at 99 hp.
3. **Farming discipline.** With an enemy within 8 tiles our camp-hit rate drops from 19.5 % of turns to **6.3 %**; Mite's drops
   from 22.7 % to 16.0 %. 31 % of all our body-rounds have an enemy within 8. That is the real "distraction": nobody lures us; our
   own threat logic stops us farming while Mite keeps farming next to us. On the same 20–50-gem groups with the same 2.5 bodies and
   the same 60 damage per hit, Mite clears in 37 rounds and we need 66 (opening), because our bodies arrive 13 rounds apart
   (median) and leave and come back (55 of 75 episode rounds with nobody hitting).
4. **Banking.** Mite banks 28 times a game (bag 35, carried 30 rounds); we bank 12 times (bag 27, carried 43 rounds), and on
   single-altar maps we carry 250–350 gems into a contested altar and lose them (boss-battle: 625 captured, 0 banked).

**v79 changed none of this** (its four switches touch chase-dropping and solo-fight vetoes; the game is the same: 339 vs 995,
8.7 deaths, middle 88 vs 605). The "lure" hypothesis the previous sessions worked on is not supported by the replays: by a
direct lure detector Mite lures us 18 times / 36 body-rounds a game and we "lure" them 33 / 72; it is noise either way.

The fix is not another switch in `combat()`. It is a **team objective layer** (section 6.1) that makes the richest groups the
team's target on a respawn clock, a **fight engine with commit/avoid semantics** (6.2), **farming through contact** (6.3), and an
**economy loop** (6.4) that shops and banks at Mite's cadence. Sections 6–10 give the algorithms, the parameters, the memory layout
and the acceptance metrics so the implementing agent can build and verify each part independently.

---

## 1. Scope, data and method

| set | games | engine | our bot | result |
|---|---|---|---|---|
| v75 vs Mite | 65 (all 70-pool maps except 5) | 2.0.0 | GOD v18 (`god__3_.zip` = `bots/gpta75`) | 0–65, 51 blowouts (margin ≥ 500) |
| v79 vs Mite | 65 | 2.0.0 | GOD v22 (`god22_1.zip`: v18 + `g22_chase 3`, `g22_solo 1`, `g22_exact 1`, `g22_msg 1`) | 0–65, 48 blowouts |
| v75 vs IC | 70 (repo, Oct 26) | 2.0.0 | GOD v18 | 8–62 |

Method (scripts in Appendix C, all re-runnable):

- `analyze.py`: per game: banked timeline, captures by zone (own half / middle / their half from BFS distances to both spawns,
  middle = |dA − dB| ≤ max(6, 20 %)), deaths with context, body-round budget (hit camp / fight / capture / tribute / walk / walk
  with enemy ≤ 8 / idle / dead), pack size, lure episodes, recalls, wards, banks, items, gold, priorities, opening.
- `groups.py`: every clearance of every camp group: who hit it, how many bodies, how long, who captured.
- `engage.py`, `exchange.py`, `response.py`, `deaths.py`: every engagement (first champion hit after 6 quiet rounds), local numbers,
  the 10-round damage exchange, what the defender did, death context.
- `opening.py`, `episodes.py`, `gaps.py`: the first 200 rounds and why farming bodies stop hitting.
- The 70 maps: structural features (Appendix B).

Watchable examples are given as (set, map, rounds) so you can open them in `cambc view`.

---

## 2. The scoreboard

### 2.1 Banked gems over time (mean, v75 vs Mite; v79 identical within noise)

| round | us | Mite | games where we are ahead or equal |
|---|---|---|---|
| 100 | 15 | 27 | 41 / 65 |
| 200 | 43 | 96 | 25 / 65 |
| 300 | 84 | 172 | 17 / 65 |
| 400 | 122 | 270 | 10 / 64 |
| 600 | 194 | 483 | 5 / 60 |
| 800 | 232 | 629 | 5 / 45 |
| end (mean r966) | 323 | 1004 | 0 / 65 |

Captured gems (before banking): by r100 32 vs 72, r200 73 vs 160, r300 121 vs 256, r500 212 vs 473, end 373 vs 1084. The gap is
2.2× from the first 100 rounds and stays 2.2–2.9× for the whole game: it is not a late collapse, it is a rate difference from
round 1, compounded by deaths and items.

### 2.2 Where the gems come from (130 Mite games, v75 + v79; IC in brackets)

| zone (our perspective) | gem groups there, captures per group per game: us | them |
|---|---|---|
| our half | 4.90 | 0.17 (they leave our half alone) |
| middle | 0.69 | **6.57** (IC 4.71) |
| their half | 0.06 | 7.36 |

The richest group alone (mean 141 gems when in the middle, which it is in 106 of 130 games): us 0.3 captures, Mite 6.6 (IC 4.7).
Mite's clearance of it: 3.1 bodies, 1.9 hitting concurrently, 37 rounds, 290 captures out of 297 kills, first hit a median of 0
rounds after the respawn. Ours: 26 attempts in 65 games, 2.1 bodies, 130 rounds, 11 captures. When we hit it first (11 games) we
killed it 7 times and captured it 3 times.

### 2.3 Time budget (share of body-rounds, v75 / v79 / IC games)

| activity | us | Mite (v75) | Mite (v79) | IC |
|---|---|---|---|---|
| hitting a camp | 12.5 % | 19.6 % | 20.4 % | 20.5 % |
| capturing (standing on a dead group) | 3.9 % | 8.7 % | 8.4 % | 6.9 % |
| hitting a champion | 2.5 % | 3.4 % | 3.1 % | 3.6 % |
| tributing | 0.5 % | 1.2 % | 1.2 % | 1.0 % |
| walking, no enemy within 8 | 39.6 % | 37.6 % | 38.9 % | 37.3 % |
| **walking with an enemy within 8** | **20.8 %** | 15.3 % | 14.1 % | 15.0 % |
| idle | 6.6 % | 10.1 % | 10.3 % | 6.0 % |
| **dead** | **13.5 %** | 4.2 % | 3.6 % | 9.8 % |

Camp hits per game: us 548, Mite 901 (IC 1,060). Damage per camp hit: equal in the opening (60), later 100–112 (us) vs 149–189
(them) because of items. Gems captured per 1,000 camp hp dealt: us 8.5, Mite 12 (they hit richer groups and lose fewer kills:
12.4 % of our killed groups are never captured by us or stolen, 3.8 % of theirs).

### 2.4 Deaths and kills

| | us | Mite | IC |
|---|---|---|---|
| deaths | 10.0 (v79 8.7) | 3.1 | 8.5 (Cassi & Issac count twice) |
| kills | 2.0 | 9.1 | 10.2 |
| gems lost on death | 79 (21 % of what we capture) | 71 (6.5 %) | 90 |
| killer is a camp | 9 % | 20 % | 17 % |
| alone (no ally within 6) at death | 31 % | 28 % | 34 % |
| 2+ enemies within 6 at death | 69 % | 62 % | 60 % |
| on their half | 17 % | 7 % | 17 % |

Deaths cost 60 rounds each: 10 deaths = 600 body-rounds (13.5 % of the team's time) plus 100 gold and the bag to the killer
(Mite earns 850 gold + ~60 gems a game from kills; the gold alone is 28 shards).

### 2.5 Economy

| | us | Mite (v75 games) | Mite (v79 games, Oct 28) | IC |
|---|---|---|---|---|
| gold earned (final + spent) | 2,613 | 6,449 | 6,340 | 7,078 |
| shop visits | 39 | 67 | 72 | 76 |
| first shard bought (median round) | 122 | 95 | | |
| first shard family | Jungle hp / Monster str | **Jungle** (focus or str) | Jungle | |
| emblems | Bruiser 6.4, Jungle 2.8, Monster 2.5, Durability 1.8, Treasure 1.7 | Bruiser 16.5, Power 4.3, Jungle 4.2, Treasure 3.5, Monster 3.3, Durability 2.8, Collectors 2.4 | Bruiser 16.3 (11.5 of them **hp**), Jungle 4.3, **Capture 4.0**, Durability 3.4, Monster 3.4, Collectors 1.9, Power 1.9, Tribute 1.0 | Bruiser 28.2 (23.2 **str**), Power 4.3, Treasure 3.3, Jungle 3.2 |
| bank trips | 11.8 (bag 27, carried 43 rounds) | 28.3 (bag 35, carried 30) | 29.7 (bag 34, carried 27) | 27.0 (bag 36, carried 28) |
| altar locks placed | 0.9 | 0.0 | 0.0 | 2.6 |
| real recalls | 509 | 566 | 580 | **43** (IC walks home) |
| fake recall-cancel pairs | 2,857 | 3,267 | 3,242 | 4 |
| wards placed / in a bush | 175 / 37 % | 244 / 49 % | 225 / 53 % | 168 / 71 % |
| distinct `set_priority` values | 4.8 | 57 | 60 | 11.5 |

Item stats per body over time (shard-equivalents: shard 1, emblem 5, Bruiser 8, Power 6): r100 1.5 vs 1.6, r200 3.3 vs 4.8,
r300 5.8 vs 8.8, r400 8.8 vs 14.2, r600 15.1 vs 27.9, r800 19.3 vs 43.2. We spend everything we earn (unspent gold ~55 at any
time); the gap is income, i.e. captures and kills.

---

## 3. Mite's system, decoded

Mite is not a pack bot and it is not a lure bot. Its team spread is the same as ours (mean pairwise distance between teammates
13–14 tiles in every phase; largest cluster within 3 tiles 2.45 vs our 2.14). It is a **rich-group ownership bot with a strong
fight engine**. The elements, each with the evidence:

### 3.1 Draft: fixed, economy-first

Mite's picks are the same in all 130 games: **Vesper Vale, Vendetta, Heart of Ruin**, then **Tavi + Marcella** on 5-champion maps,
**Cassi & Issac** on 4-champion maps (5 bodies for 4 picks), and VV/HoR/Vendetta on 3-champion maps. IC: VV, HoR, Vendetta, C&I in
57 of 70 games, Marcella. Neither adapts to the map or to our picks. The common core is: the +33 % gold champion first, two
dash melee carries, then stuns (Tavi 1.6× focus stun, Marcella's enhanced attack, Cassi's stun) and a field shopper (Tavi).

Our picks: HoR 65, VV 64, Ryth 56, Vendetta 55, Marcella 47. The only real difference is **Ryth instead of Tavi**. Our Ryth deals
47 damage per attacker-round on champions (35 after r600) and dies 117 times in 65 games; Mite's Tavi deals 142 (202 late).

### 3.2 Opening: everybody hits something by round 24

Mite's first camp hit is at round 24 on average (median 14), 3.7 rounds after the walking distance; ours at round 40 (median 19),
15 rounds after the walking distance. Mite's bodies go to a near 26–50-gem group together (arrival spread median 6 rounds), clear
it in 12–20 rounds, one body captures while the others move on. First gem capture: Mite median round 32, us 42. By round 100 Mite
has captured 72 gems to our 32.

Watch: v75 `00fragment` r0–60: Mite's three bodies hit the 26-gem group at (11–13,14–16) from r6, capture at r36; our three solo two
4-gem wolves, abandon them at r30 with 760–780 hp, walk into Mite's group at r45 with 475 hp, walk back, and recall at r57–63.
Our own 26-gem group next to our spawn (g1, 8 steps away) is captured 17 times by Mite and 0 times by us in that game.

### 3.3 The rich-group clock

After the opening (first hit on the richest group at r168 on average, with 3.5 bodies) Mite takes the richest group **every
respawn**: 62 % of its clearances start within 5 rounds of the respawn (median 0: a body is standing there). It keeps 25–30 % of its
alive bodies within 8 tiles of that group through the whole game (we 17–19 %), the rest farm the groups around it and bank. Between
cycles the bodies farm their own half (7.4 captures per own-half gem group vs our 4.9 of ours), so the clock costs them nothing.

Watch: v75 `01elk_arena` (the only gems are a 72-gem group dead centre, 8 steps from both spawns): we lose HoR and Ryth to the two
elks at r22–25 (they walked into the camps alone), Mite's five arrive together at r40 at 370–1,140 hp, capture it by r58, and take it
every respawn after that: 63 body-captures (the reward is split among the bodies present), we 0. `00stampede` (one 160-gem
objective group, the rest gold pairs): Mite farms gold pairs for 600–850 rounds, buys 2,000–5,000-hp bodies, takes the objective
(first capture r611 in the v79 game, r854 in the v75 game) and then every respawn until 1,000; we farm the same gold pairs for
1,500 rounds and never try it.

### 3.4 Fights: initiate, converge, chain stuns, never run

- Mite starts 75 % of engagements. At the first hit the local numbers (within 6 of the target) are even (1.84 vs 1.95), the hp
  ratio is even (median 0.96), the item count is not (10.1 vs 6.3).
- Outcome within 30 rounds when Mite starts: our body dies 52 %, theirs 12 %. **1v1**: 42 % vs 10 %. **1v2 (Mite outnumbered)**: 52 %
  vs 6 %. 2v2: 54 % vs 9 %.
- During the fight Mite converges: enemies within 6 of our dying body go from 1.46 at contact to 2.42 at death; our allies within 6
  stay at 1.2 (31 % of deaths have none).
- Damage per attacker-round on champions (solo attacker, no camp nearby): Mite Vendetta 203 (294 after r600), Marcella 181 (371),
  Tavi 142, VV 127 (198), HoR 104; ours VV 117, Vendetta 88, Marcella 61, HoR 51, Ryth 47. Mite's Marcella is a focus nuker
  (Power focus emblems, 14 focus per shard, 2× focus spell); ours is built as a tank (Jungle hp, Monster str).
- Stun chains: Marcella's enhanced attack (stun 1), then HoR's dash landing (stun 1), then Tavi/Cassi: a body of ours is stunned for
  2–3 consecutive rounds and dies without acting (crossing r213–215 below).
- Mite tributes **during** fights when an altar is adjacent (damage does not interrupt a tribute; a stun does, and Marcella is
  stun-immune).

Watch: v75 `02crossing` r196–225 (the central altar at (25,25) with four gem clusters around it): r197 our HoR (1,140) hits Mite's VV
(804) 1v1 and wins the exchange; r199 our Vendetta walks in at 840 hp and is shot to 444 in two rounds by VV's attack reset; r201
Mite's Vendetta (912 hp, 68 gems) **starts a tribute at the altar while fighting**; r203–206 our Vendetta at 444 → 28 hp keeps
dashing at the enemy and attacking; r206–207 we kill Mite's Vendetta (our VV picks up the 68 gems) — we won the first exchange 3v2;
r207–215 Mite's HoR, Marcella and VV arrive, focus our HoR (5 hits a round: 595 → 252 → 54 → dead at r216 while stunned by
Marcella r213 and HoR's dash r214); r216–221 our Marcella **walks away** from a ranged VV at the same speed and is shot from 924 to
dead at r222; our VV, standing 4 tiles from the altar with 68 gems in the bag, fights instead of tributing and dies at r225 with
the gems; Mite's HoR at 99 hp keeps attacking and survives; our Ryth was 15 tiles south being kited by Tavi and recalled. Net:
one kill each way, three of our bodies dead, 68 gems returned to Mite, the altar and all four gem clusters theirs.

### 3.5 Farm through contact

Camp-hit rate by enemy distance (share of body-rounds in which the body hits a camp):

| nearest enemy | us | Mite |
|---|---|---|
| ≤ 8 | **6.3 %** | **16.0 %** |
| 9–12 | 16.5 % | 24.2 % |
| > 12 | 19.5 % | 22.7 % |

A body of ours with an enemy in sight is three times less likely to be farming than a Mite body in the same situation. Mite
hits champions in 12 % of those near-enemy rounds (we 9.5 %) and farms in 16 % (we 6.3 %); the rest it walks or waits. That is
the whole "distraction" effect: the presence of an enemy switches our bot from farming to dithering (walk toward, walk away, walk
sideways, see section 4.2), while Mite's bot keeps its hands on the camp.

### 3.6 Banking and shopping cadence

Mite banks every ~30 rounds with 30–40 gems, 28–30 times a game, usually at the altar nearest to the group it just cleared
(the richest group is 15 tiles from an altar on the average map, often adjacent: crossing, boss-battle, elk-arena). It shops 67–72
times a game: with 5 bodies that is one shop visit every 13 rounds, most of them at the end of a bank trip or while a rich group
respawns. Jungle emblem first on every body (30 % less camp damage = no heal trips while farming), bought by r95 (median); then
Bruiser (hp on the divers, str on VV/Vendetta), Capture (the new emblem: the team's capture timer capped at 3 rounds, 4 per game
on Oct 28), Power focus on Marcella, Collectors late.

### 3.7 Messaging

Mite writes `set_priority` 800 times a game with ~57 distinct values (1000–1049 counting down with health for melee bodies, 1010–1020
for VV, 94–99 / 2095–2099 / 3097… as other message classes). Allies read it with `query_priority`. It is a per-body status broadcast
(health bucket, role, probably target) that also keeps the healthiest melee acting first. We write 4.8 distinct values.

### 3.8 The fake recall

Every Mite body ends every turn with `recall()` and cancels it next turn (3,267 pairs a game). Our v17+ does the same (`g17_bait`).
It has no measurable effect in these games either way (Mite's 3.1 deaths are not baited; IC does not do it at all and dies 8.5
times). Keep it or drop it; it is irrelevant to the result.

---

## 4. Our failure modes, ranked by cost

The cost estimate is gems per game relative to Mite's rate; they overlap, so they do not add up to the 680-gem gap.

### 4.1 We do not contest the richest groups (≈ 350–450 gems)

Evidence: section 2.2. Code: there is no team-level objective. `farm()` → `group_score()` (brain.cpp 6121–6679) scores groups per
body with `enemy_half_penalty 10`, `deny_bonus 0.043`, `join_reach 1.2`, `max_join 3`, `join_share 0.6` and a threat map; a middle
group with an enemy near it scores badly for every body independently, so nobody goes, or one body goes alone (2.1 bodies on our
26 attempts) and takes 130 rounds. The claim bytes in shared memory (`comms.h`) only say "I am on group g"; there is no "the team
owns group g, be there at round R". `max_wait 18` means a body that arrives early leaves; Mite's median wait is 0 because it is
already there.

### 4.2 We lose the fights we are in, and we are in the wrong ones (≈ 250–350 gems: 10 deaths × 60 rounds, 79 gems dropped, 850 gold to them)

Evidence: sections 2.4, 3.4. What the defender does in the 12 rounds after being hit first:

| | fight | move away | move toward | move sideways | idle | died within 15 rounds |
|---|---|---|---|---|---|---|
| us | 17 % | 37 % | 17 % | 16 % | 10 % | **29 %** |
| Mite | 21 % | 28 % | 15 % | 12 % | 19 % | 10 % |

Our bodies move in 70 % of the rounds after being hit, and the moves are indecisive (away 37, toward 17, sideways 16): the
"A-B-A" the user complained about. Fleeing from Vendetta or HoR (walk 1 + dash 2 every 8 turns) or from a range-3 VV at walking
speed is free damage for them; 205 + 136 of our 593 champion deaths are to those two, 82 to VV.

Code: `combat()` (brain.cpp 3451–4244) stacks eight generations of rules: `fight_margin 1.4`, `isolated_fight_adv 1.35`,
`isolated_flee_adv 1.5`, `outmatch_flee_adv 0.8`, `px_mode 2`, `ml2_leave 0.2`, `ml2_flee 0.35`, `burst_exit`, `stay_rule`,
`fight_commit`, `g15_calm 5`, `fz_engage 4`, `fz_chase 4`, `g22_solo`, `g22_chase`. Each one vetoes or forces `fight` under
different conditions, and the result flips from turn to turn as hp, distances and visible allies change. The engage path
(`engage()` 4275) then steps toward the target when `fight` is true and `safety()` (4758) walks home when it is false, with no
hysteresis between them except `fight_commit` (1 round). There is no notion of "I cannot outrun this chaser, so trading is the only
option" that overrides everything else, and no notion of "my team has committed, I do not leave".

### 4.3 We stop farming when an enemy is in sight (≈ 150–250 gems)

Evidence: section 3.5 and the episode study: multi-body farm episodes in the opening last 75 rounds for us with 55 rounds in which
nobody hits the group (Mite: 44 and 27). Of the body-rounds in which a body that had started a group is not hitting it: 24 % walking
back to it (it left), 12 % hitting another group (switched target), 10 % walking away (6 % with an enemy within 8), 10 % dead, 8 %
recalling, 7 % sideways. Code: `safety()`, `outmatch_flee`, `ml2_flee`, the threat map in `group_score` (`threat_map`, `tm_memory`),
`risky_persist`, the "risky bank" trip (`tribute_risky 10`), and `respond_to_alert()` (5540) which pulls a farming body toward a
RALLY/OPPORTUNITY alert posted by any ally. Mite's bait recall feeds the OPPORTUNITY path (v17 added `g17_fakerec 3` to filter it;
Mite still recalls every turn, so the filter fires constantly and the alert slot is noise).

### 4.4 Arrival spread and re-targeting (≈ 100–150 gems, opening and every cycle)

Evidence: arrival spread (first body's first hit → last body's first hit) median 13 rounds vs 6; 15 rounds of delay before the
first camp hit of the game vs 3.7. Code: `start_round 2` synchronises the first step but every body paths independently and
re-scores its target every turn (`mi_sticky_until`, `giveup_progress`, `commit_hit` only partly damp this); faster bodies (dash kits)
arrive, take camp damage alone, and step out (`retreat_hp 0.25`, "4 rounds of incoming camp damage").

### 4.5 Banking (≈ 80–120 gems and the single-altar maps)

Evidence: 2.5. `tribute_min 54`, `early_tribute_min 22`: we carry 43 rounds on average, 50 vs IC; bags of 60–350 on single-altar
maps. boss-battle (v75): 344 + 255 gems carried for 300+ rounds, both bodies killed at the only altar (r551, r635), Mite banks 563 at
r575. Captures of groups adjacent to an altar are not followed by a tribute (crossing r207: 68 gems, altar 4 tiles away, fought
instead). `win_bank` only triggers for a game-winning bag.

### 4.6 Builds (compounding)

We buy Jungle hp / Monster str / Durability / Treasure: a safe-farming build on every body including the carries; Marcella as a
tank. Mite: Jungle first (same idea, 30 rounds earlier), then raw stats (Bruiser) on everyone, damage stat on the damage dealers,
Capture on the cycler, Power focus on Marcella. Our VV ends with 117 damage per attacker-round, theirs 127 with 2× the hp.

### 4.7 Objective-type maps (0 gems in 3 of 65 games, near 0 in 8)

contest (two 200-gem monoliths, gold elsewhere): 0–0 at r2000, we died 56 times walking into the middle one at a time; lost on
the gold tiebreak. stampede, elk-arena, ribs, hooks, corridors: we never take the single rich objective. Our objective plans
(`obj_*`, `o2_ring`, `mono_*`) exist but require conditions that do not trigger, and they have no "farm gold first, then take it
with everything" fallback.

### 4.8 Wards and vision

37 % of our wards are in bushes (Mite 50 %, IC 71 %); none is dedicated to the rich-group respawn clock, so we never know when the
richest group respawns unless a body is looking at it.

---

## 5. Why the v79 switches changed nothing

`g22_chase 3` drops a target that keeps its distance; `g22_solo 1` vetoes fights alone vs 2+; `g22_exact` uses engine damage
numbers; `g22_msg` keeps committed allies in the estimate. All four act inside `combat()` on the *decision to fight*. The losses are
caused by (a) what the team farms, (b) what a body does *after* the decision (the chase / flee execution), and (c) the economy.
v79 deaths 8.7 vs 10.0, banked 339 vs 323, middle captures 88 vs 96: within noise. The same is true of the earlier pack (`g20_pack`),
squad and deathball attempts: they changed who walks with whom, not what the team is trying to own or how a body fights.

---

## 6. The correction plan

Principles the whole plan follows:

- **Map-agnostic by construction.** Every rule keys on features computed at draft time from the map (group values, BFS distances,
  zones, altar distances, respawn timers) and on live observations; no map names, no per-map tables.
- **Team-level intent, body-level execution.** One deterministic team plan that every body recomputes identically from shared
  state (so the 8 shared bytes carry only what cannot be recomputed), plus per-body execution.
- **Commit or avoid, never dither.** A decision to fight, farm, bank or go to the objective holds for a fixed window unless a
  hard trigger fires.
- **Fuel.** Everything below is O(groups + enemies + allies) per turn with precomputed BFS fields from the draft; the 100× draft fuel
  is used for the heavy precomputation.

### 6.1 Team Objective Layer (TOL): own the rich groups on a respawn clock

**Draft-time computation (100× fuel), written to the 1,024-byte draft memory:**

1. Groups: id (engine `camp_groups()` order), tiles, gems, gold, total hp, max camp attack range, `max_respawn_timer()`, centre.
2. BFS walking distances from our spawn (`dA`) and theirs (`dB`) to every tile (walls/holes/altars/enemy spawn blocked; camp tiles
   passable since camps die). Zone of each group: own / middle / theirs as in section 1.
3. **Prime set** P: groups sorted by `value = gems + 0.15·gold` (gold matters: it is items), keeping those with
   `value ≥ 0.5 · max_value` **or** `gems ≥ 36` (one golem / two elks), located where `dA ≤ dB + 6` (we can reach it no later than
   they can, or at most 6 rounds later). Cap |P| at 3. On maps where the richest group is deep in their half (13 of 70) P is the
   richest groups we *can* reach first, and the deep one becomes a "raid target" (6.1.4).
4. For each prime group: the nearest altar and its distance (tribute-after-capture plan), a **rally tile** (a free tile at
   distance `max_camp_range + 1` from every live camp of the group, on our side of it, preferring a bush tile and a tile from
   which all camps are within 4), a **ward tile** (a legal ward tile within 2 of a group tile that sees at least one original
   spawn tile of the group: the respawn clock is readable with `camp_group::state()` only while an original spawn tile is in
   vision), and the **required force** `F(g)` = bodies needed so that the group dies in ≤ 25 rounds with the team's current dps
   (recomputed live from `damage_amount`, start with 3 for 36–80 gems, 4 for 80–200, 5 for 200+).
5. Opening schedule (6.1.2) and the single-altar / objective flags (section 9).

**Live state (shared memory).** Bit 7 of bytes 0–5 (today: the learner stance in bytes 0–1, the alert toggle / contact bit in
byte 2, the opp-model plan or the `g15_lock & 2` tribute timer in bytes 3–5; none of them carries anything measurable in these
games) becomes the **prime clock**: 5 bits = rounds until prime group P0 is ready in units of 4 (0 = alive, or dead with the
reward uncaptured; 31 = unknown / ≥ 124), plus 1 bit "enemy holds P0" (an enemy body seen on a P0 tile or within 3 of it in the
last 10 rounds). The warden (6.1.3) writes it every turn; `opp_plan`, `opp_model`, `alert_refresh`, `mi_live` and `g15_lock & 2`
must be off (they are in v75 except the lock timer, which goes with OPPORTUNITY). The body claims (bits 0–6 of bytes 0–5) stay as
they are. The alert slot (bytes 6–7) keeps DANGER and RALLY; **drop OPPORTUNITY** (it is what Mite's bait recall feeds).

**Team plan, recomputed by every body every turn (identical inputs → identical output):**

```
ready_in  = prime clock (from shared memory; from own vision when the warden is me; else from World.ready_round)
need      = F(P0) + (enemy_holds ? 2 : 0)            // bring numbers if they are there
eta_i     = walking rounds of ally i to rally(P0)     // BFS field from the draft; allies' positions from claims/vision
commit_i  = alive_i && eta_i <= ready_in + 2          // can be there when it spawns (+2: capture starts 1 round after)
roster    = the `need` committed allies with the smallest eta (ties: higher hp, then index)
```

A body in `roster` has the **prime task**: it goes to the rally tile so as to arrive at `ready_in − 1` (not earlier: it farms
groups whose finish time ≤ ready_in − eta on the way; the existing `group_score` runs with the extra constraint
`clear_time + eta(g→rally) ≤ ready_in − 1`), then waits at the rally tile (a `T_WAIT` that is never dropped by `max_wait`), hits
on the first round the group is alive, and one designated body (lowest index in roster with the Capture emblem if any) captures
while the others start the next-best group within 8 tiles or escort the capturer if `enemy_holds`. The capturer tributes
immediately if an altar is within 6 (6.5), otherwise carries to the next cycle's bank point.

Bodies not in `roster` farm with the existing per-body scorer, with two changes: (a) own-half groups score normally, middle
groups outside P score with `enemy_half_penalty` halved, their-half groups unchanged; (b) the **deadline constraint** above for
bodies that will be in the next roster (so the next cycle is always staffed).

**Why this beats a pack:** the pack (v20/v21) walked everyone together everywhere and lost 10 % of unopposed pace. The TOL only
synchronises the team at one place at one time per respawn cycle (60–80 rounds), which is exactly what Mite does: 25–30 % of its
bodies near the rich group, the rest farming.

**6.1.1 Contested prime group.** If `enemy_holds` and the local power ratio at the rally (6.2.1, with the roster's bodies) is
< 1.0, the roster does not engage; it farms the next groups and the plan re-targets the **next** respawn with `need = 5` (everyone):
a 5-vs-3 at the group at its respawn is a fight we win when 6.2 is in place, and the enemy must split (their other bodies are
farming elsewhere). If the ratio is ≥ 1.0, engage as a team (6.2.4) with the rally tile as the anchor. Never trickle in.

**6.1.2 Opening schedule.** At draft time, with both spawns known:

- `t_prime_us = dA(P0)`, `t_prime_them = dB(P0)`. If `t_prime_us ≤ t_prime_them + 2`: **everyone to P0 first** (the richest group
  is the opening group; Mite's `01elk_arena`, `01corridors`, `00vault`, `00the_line` openings), arriving together (6.4.1).
- Else: opening group O1 = the highest-value group with `dA(O1) + clear_time(O1, 5 bodies) + walk(O1 → P0) ≤ first respawn of P0`
  where the enemy's first capture of P0 is estimated at `t_prime_them + clear_time(P0, their 5) + 5`; clear O1 with everyone, bank if
  an altar is within 6, and be at the P0 rally at its first respawn with everyone (`need = 5` for the first contested cycle).
- 3-champion maps: the same with 3; the prime set is capped at 2.

**6.1.3 The prime warden.** The body with the ranged kit and the lowest index in the roster places its ward on the P0 ward tile at
the first visit and never moves it (`ward_hold` for that body). Its turn writes the prime clock. If it dies, the next roster body
takes the role on its next visit. This is a one-ward cost for an exact respawn timer that the whole team uses.

**6.1.4 Raid target.** A richest group deep in their half (dB + 6 < dA) is taken only when the team has ≥ 4 alive, the enemy's
visible bodies near it are ≤ 1, and the prime clock says P0 is > 25 rounds away; the raid is the roster's "filler" task, not a
solo adventure (today: 31 attempts a game by single bodies, 74 % killed, 15 captured).

### 6.2 Fight engine: commit or avoid

Replace the rule stack in `combat()` with one evaluation that produces one of four states with hysteresis, and an execution
routine per state. Keep the existing helpers (`burst_vs` with `g22_exact`, `reach_of`, `damage_amount`, `has_completed_turn`,
`remaining_channel_time`, `buffs()`).

**6.2.1 Local power ratio** `R = (Σ_ours hp_i · dps_i) / (Σ_theirs hp_j · dps_j)` over bodies within 8 of the contact point,
where `dps` = basic attack × (reset ready ? 2 : 1) + best ready spell damage / 3, items included via `damage_amount` on the real
target, HoR's missing-health bonus and Varg's splash included, and bodies that cannot reach the contact within 2 rounds weighted
0.5. Allies count if they are visible **or** their claim is within 8 of the contact (shared memory), and are never dropped for
"walking away" (that rule produced the cascading retreats). Enemies on their spawn count 0 (they heal).

**6.2.2 Can I get away?** `escape = no enemy within reach_of(e) + 2 that moves faster than me` where faster = (melee with dash
ready) or (ranged with range ≥ 3 and I am melee) or (any enemy with a ready stun within 4), **or** the walk to my spawn / to 2+
allies is shorter than `hp / incoming_per_round`. If `escape` is false, running is strictly worse than trading: the state is FIGHT
regardless of R (today: `cornered_margin 0.74` lets `ml2_cornered` override it, and the body runs).

**6.2.3 States and hysteresis.**

```
KILL   : a visible enemy dies this turn to my hits + committed allies' hits (burst_vs + allies' damage_amount) and is not on its spawn
FIGHT  : KILL, or (!escape), or (R >= 1.15 and the target cannot be reinforced by more than we can within 2 rounds), or (an ally within 6 is
         committed and R >= 0.85), or (I am on my spawn tiles: heal every round, fight anything that comes)
AVOID  : else, if no enemy can hit me next turn: keep farming / keep the task (do NOT walk home, do NOT walk toward)
LEAVE  : else (escape and R < 0.85 and no committed ally): walk toward the nearest committed ally or spawn, casting a stun on the
         fastest chaser first if one is ready, never through camp range
```

Hysteresis: FIGHT holds for 6 rounds after entry unless (a) target dead → re-evaluate immediately, (b) hp < 20 % and `escape`
is true, (c) R falls below 0.6 because a *new* enemy arrived. AVOID/LEAVE hold for 3 rounds. A body that was FIGHT last round and
is now AVOID does not step toward the enemy (that is the A-B-A).

**6.2.4 Execution in FIGHT.** Order inside the turn:

1. **Target**: the team target = the enemy within reach with the lowest `hp / Σ(committed allies' damage on it this round)`, with
   +200 priority for a stunned enemy, a channelling enemy (`remaining_channel_time`), a Cassi/Issac (two bodies for one), and an
   enemy carrying ≥ 20 gems; −∞ for an enemy on its spawn. Broadcast the target index in the priority channel (6.7) so allies
   who see me converge on it.
2. **Stuns in sequence**: cast a stun only if the target is not already stunned (`buffs()`), and prefer the stun that lands when
   the target would otherwise escape or when ≥ 2 committed allies can hit it this round. Marcella's enhanced attack, HoR's dash
   landing, Ryth's area stun, Tavi/Cassi/Prism/Ren stuns all count.
3. **Attack reset = 2 hits**: cast the reset only when a basic attack already landed this turn and a second is possible.
4. **Position**: melee: step to a tile adjacent to the target that is adjacent to the fewest other enemies and then attack
   (move + attack same turn); ranged: do not move if the target is in range (ranged cannot move and attack); if not in range,
   step to the nearest tile in range that is out of melee reach of every other enemy; never step onto a tile inside an awake
   camp's range unless the camp is attacking the enemy (camps hit the nearest champion: fight on the far side of a camp from
   the enemy so the camp hits them — the reverse of what happens to us today).
5. **Bag**: if I carry ≥ 20 gems and an altar is within 1, start the tribute *now* and keep fighting (damage does not cancel it);
   Marcella is the preferred banker in contested altars (stun-immune).
6. **Low hp inside FIGHT**: at hp < 25 % with `escape` false keep hitting (HoR gets +50 % damage near zero; Mite's HoR survived at
   99 hp in the crossing fight by doing exactly this); with `escape` true and no KILL available, LEAVE toward allies, not home.

**6.2.5 Engagement gate (who starts fights).** We should start fights only when `R ≥ 1.15` at the rally point *and* the enemy's
bodies cannot bring more within 2 rounds than we can (count their bodies within 10 of the target against ours). Everything else is
AVOID: keep farming. A body never walks more than 2 steps toward an enemy that is not a KILL (today 70 % of our deaths are preceded
by 2+ approach steps). `fz_chase` / `g22_chase` become unnecessary: a target that is not killable is not chased at all.

**6.2.6 Second wave.** When an ally within 8 enters FIGHT (its priority flag), every body within 8 that is not in a tribute or on
a prime-clock deadline within 5 rounds re-evaluates with that ally's committed hp in R; at R ≥ 0.85 it joins (today
`ally_defend 0` is off and the joiner must independently see adv ≥ `fight_back_margin`).

### 6.3 Farm through contact

- An enemy in sight is **not** a reason to stop hitting a camp. The only reasons are: `escape` false with R < 0.6 (then FIGHT), or
  the camp group's remaining hp cannot be cleared before the enemy's expected arrival **and** the enemy would then capture it
  (then switch to the nearest other group or go to the prime rally), or a prime deadline.
- Remove the OPPORTUNITY alert and `respond_to_alert()`'s pull toward recalling/tributing carriers unless the carrier is within 6
  of a body that is already not farming (Mite recalls every turn: the signal is noise and it is also the bait).
- `threat_map` / `tm_memory` penalties in `group_score` apply only to groups where an enemy was seen within the last 15 rounds
  **and** the local ratio there was < 0.8 when seen.
- Retreat from camp damage (`retreat_hp 0.25`, "4 rounds of incoming") only when no ally is within 4 of the group: a camp hits
  the nearest champion, so a melee ally stepping in resets the target; two bodies alternating the front tile take half the
  damage each and never leave (this is what Mite's 2.5-body groups do; it is why its bodies rarely recall from a farm).
- Measure: camp-hit rate with an enemy within 8 must rise from 6.3 % toward 16 %; multi-body episode length toward 44 rounds
  with ≤ 27 rounds unhit.

### 6.4 Economy loop

**6.4.1 Opening, synchronised.** The draft schedule names the opening group and a **staging tile** at `max_camp_range + 2` from it.
Bodies walk there (the first turn's 2× fuel precomputes the field; the draft memory carries the tile), and the first hit happens
when ≥ 3 bodies (or all on 3-champion maps) are within 1 round of attack range; a body that would arrive more than 3 rounds before
the last one farms a cluster on the way (gem/gold clusters: 120 hp, harmless) instead of waiting. Target: first camp hit ≤ walking
distance + 4 rounds (today +15), arrival spread ≤ 4 (today 13).

**6.4.2 Builds (from the roster, role by kit, not by name).**

| role (kit) | order | why |
|---|---|---|
| ranged carry (VV, Tavi, Stellar, Prism, Cassi) | Jungle(str or focus) → Bruiser(str) ×3 → Capture(str) on the prime capturer → Bruiser(str)… Treasure only on VV when gold > 2,500 | Jungle first = no heal trips from r95; Bruiser 8 stat points for 150 gold is the best raw stats; Capture caps the team's capture timer at 3 |
| dash melee carry (Vendetta, HoR) | Jungle(str / HoR: focus) → Bruiser(hp) → Bruiser(str) → Bruiser(hp) → Monster(str) | hp lets them dive and survive (Mite's 11.5 Bruiser hp a game); HoR's dash scales with focus |
| stun-immune banker (Marcella) | Jungle(focus) → Power(focus) ×2 → Bruiser(hp) → Tribute(focus) on single-altar maps | 14 focus per shard, 2× focus spell: Mite's Marcella deals 181/round; +2 gold per gem tributed makes her the banker |
| Ryth (if drafted) | Jungle(hp) → Bruiser(hp) ×2 → Durability(hp) | her strength scales with bonus health (1 % of bonus hp) |
| Tavi | buys shards in the field every time gold ≥ 30 (never walks home to shop); sells Jungle for full value after r600 and buys Bruiser | field shopping is the whole point of the pick |

Shop cadence rule: a body with gold ≥ 90 goes to shop when (hp < 50 %) or (it is within 12 of its spawn) or (prime clock
≥ 25 rounds and it is not in the next roster) or (gold ≥ 180). Target 60–70 shop visits a game.

**6.4.3 Kill economy.** Each kill is 100 gold + the bag. The fight engine's KILL state and target priority for carriers (≥ 20 gems)
turn Mite's own carry habit (bag 22.7 at death) into our income.

### 6.5 Banking

- `tribute_min` becomes a function: bank when `bag ≥ 15 and altar within 6`, or `bag ≥ 30`, or `bag ≥ 20 and an enemy with R < 0.8
  within 10`, or `bag ≥ 10 and prime clock ≥ walk-to-altar + walk-back + 2` (free time), or the bag wins the game. Hard cap: a body
  never carries more than 60 while an altar is reachable in ≤ 15 rounds. Target carry time ≤ 30 rounds (today 43–50).
- Capture → tribute: the capturer of a group with an altar within 6 walks to it and tributes before anything else (the capture
  delay already costs 5 rounds; the tribute of 30 gems is 3 ticks).
- Single-altar maps (15 of 70): the altar is the team's second prime objective; the roster holds it, one body carries a 10-gold
  altar lock and places it when the team leaves (IC places 2.6 a game); tributes are never started with an enemy within 4 unless
  the body is Marcella or the enemy is stunned.
- Locks offensively: a body with a lock and a free turn locks the altar nearest to an enemy carrier with ≥ 30 gems when it is
  within 2 of that altar and the carrier is ≥ 4 away: the tribute is cancelled, five hits to clear, and our team takes the prime
  group meanwhile. That is the counter-distraction that costs 10 gold (section 8).

### 6.6 Draft (map- and enemy-aware, no fixed roster)

Keep `param_pick` and the model; change the priors and add two rules:

1. **First pick = Vesper Vale** on every map (both top teams; +33 % gold is the snowball itself). Second and third: the two
   highest-damage dash kits available (Vendetta, HoR).
2. **5-champion maps**: fourth = **Tavi** (stun + field shopping; replaces Ryth: 142 vs 47 damage per round, and no shop trips),
   fifth = Marcella (stun-immune banker, focus nuker). **4-champion maps**: Cassi & Issac if the map has ≥ 12 gem groups or ≥ 8
   harmless clusters (two farming bodies for one pick; IC's 57/70 choice), else Marcella. **3-champion**: VV, Vendetta, HoR.
3. **Counter-picks from the enemy's revealed picks** (the draft reveals picks as they go): if the enemy has ≥ 2 dash melee
   (Vendetta + HoR), raise Marcella (stun-immune) and Ryth's area stun by `pd_counter`; if the enemy has ≥ 2 ranged, raise HoR
   (dash landing stun on the backline); if the enemy took C&I, raise burst (Stellar/Marcella) because the pair dies to one kill.
   Never let a counter displace VV.
4. Map-feature leans (already computed by the draft): single rich objective (`rich_share ≥ 0.5`) → Prism or Stellar replaces
   Tavi (ring damage on a 6-elk group); monolith-only maps → the same plus Marcella.

Drafts are a second-order effect (the previous sessions measured ±120 gems between rosters); do not spend more than a day here.

### 6.7 Messaging through `set_priority` (allies who see each other)

`priority = turn_order_class · 4096 + hp_bucket · 256 + state · 64 + target_index · 4 + flags`, where `turn_order_class` keeps the
current fighter ordering (stunner before damage before capturer), `hp_bucket` = hp/max in 16ths, `state` ∈ {FARM, PRIME, FIGHT,
LEAVE, BANK}, `target_index` = the fight target's champion index (0–15), flags = {committed, carrying ≥ 20, warden}. Allies read it
with `query_priority(true)` for bodies in their vision; it costs no shared-memory bits and it is what Mite does with its 57
values. `g22_msg`'s two bits are a subset of this.

### 6.8 Wards

Three jobs, in priority order: (1) the prime warden's ward on the P0 ward tile (never moved), (2) a bush tile on the enemy's
approach path to the group we are farming (the BFS path from their spawn to it; `g22_ward`'s coverage scorer with the bush
bonus already does most of this), (3) the altar we bank at. Target ≥ 50 % of wards in bushes.

---

## 7. Movement and stuck fixes that the plan depends on

- A `move()` that returns `false` (hidden occupant in a bush) must be retried on the next-best tile in the same turn
  (`next_moves_from` / `move_absolute`); today `nav.cpp` 391–413 retries the same route next turn. The replays show 18–29 blocked
  moves a game for us; IC has 104 and farms fine because it retries.
- Ranged bodies never spend the move when the target is in range; the fight executor must know "I attacked, so I cannot move".
- The waiting state at a rally tile is explicit (`T_WAIT` with a deadline) and `unstick()` must not kick a waiting body.

---

## 8. Distraction: how not to be lured, and how to lure them

What actually distracts us is contact itself (section 3.5), so the defence is 6.2 (AVOID = keep farming) and 6.3. Explicit
rules on top:

- A body never follows an enemy that is not a KILL, never for more than 2 steps, and never onto their half unless in a raid
  roster (6.1.4). This covers the "retreat inside their reach" lure the v79 `g22_chase` tried to catch; with the engagement gate
  there is no chase to drop.
- A recalling or tributing enemy is a target only for a body already within 6 of it with a KILL or a stun ready; nobody travels
  for it. (Mite's bait recall then costs them a cancel every turn and gains nothing.)
- A body that is shot at by a ranged enemy it cannot reach (VV kiting a melee at range 3) does not walk after it; it walks to the
  nearest ally/camp cover tile or stands on its farm; two bodies converge on the kiter only when the KILL check passes.

Our own distraction plays, in order of expected value:

1. **The altar lock raid** (6.5): one body, 10 gold, cancels a 30–70-gem tribute and forces the carrier to hit the lock five times
   while our roster takes the prime group. Mite carries 23 gems on average when it dies and tributes bags of 35; it never places
   locks, so it has no counter-play today.
2. **The spawn fight**: our spawn tiles heal to full every round. A body chased home does not stop at the edge; it stands on the
   spawn and fights (FIGHT state includes "on spawn"). Any Mite body that follows is fighting a body with infinite hp. The lure is
   simply the retreat path of LEAVE: it ends on the spawn, not in front of it.
3. **The respawn steal**: the prime clock also works for *their* richest own-half group (a ward from a raid visit gives its
   timer). With 4 alive and their bodies seen elsewhere, the roster takes it at its respawn and leaves; it costs them a cycle and
   pulls their bodies back home while our other bodies take P0.
4. **Capture pressure**: a dead group they are capturing resets when an enemy enters the region; one body stepping onto a tile of
   a group Mite is capturing (and leaving) costs them the capture timer with no fight. Use only when the body is faster than the
   capturer (dash ready) and no second enemy is within 6.

---

## 9. Objective and special maps (detected from features, not names)

| feature | detection | plan |
|---|---|---|
| single rich objective (`rich_share ≥ 0.5`, e.g. stampede, elk-arena, ribs, vault, anvil, the-line) | draft | P = {objective}; opening per 6.1.2; the ring plan (`o2_ring`) is the clearing method; if the enemy holds it with ≥ 3, farm gold groups as a team and shop until R ≥ 1.15 at the rally (Mite's stampede play: 600 rounds of gold, then the objective every cycle); never send fewer than `need` |
| lone monoliths only (contest: 2 × 200 gems, 20,000 hp, range 5) | draft (`mono` and no other gems) | the game is decided by gold and kills (tiebreak); farm the gold groups in two pairs with wards on the approach paths; take a monolith only with 5 bodies, full hp, Jungle on everyone, and no enemy seen within 15 for 20 rounds; the capture needs the monolith's tile occupied uncontested: hold it with everyone. Avoid the middle otherwise; the 56-death game is the one to never repeat |
| single altar (15 maps) | draft | 6.5: the altar is a prime objective; locks; Marcella banks |
| altar adjacent to the richest group (crossing, boss-battle, elk-arena, hooks, the-pack) | draft (`rich_altar_d ≤ 6`) | capture → tribute in the same visit; the roster escorts the tribute |
| huge maps (≥ 80×80) with many small groups | draft | the roster for P0 is 3, not 5; two bodies farm the own half continuously; bank at the altar nearest to the current farm, never at spawn |
| 3-champion maps | draft | P capped at 2; the opening is always all three together; no raids |

---

## 10. Validation: metrics and targets

Run every candidate on the 70-map pool against `gpta75`, `god17` and the IC clone as the repo's panel does, but judge it on the
behaviour metrics below (from `analysis/` on the local replays) before the win rate, because the win rate against our own old
bots did not predict the ladder (v19, v20, v21). Targets are Mite's numbers from this study.

| metric (per game, mean over the pool) | today | target |
|---|---|---|
| richest-group captures | 0.3 | ≥ 3 |
| middle gem groups, captures per group | 0.7 | ≥ 3 |
| first camp hit − walking distance | 15 rounds | ≤ 4 |
| arrival spread on the opening group | 13 | ≤ 4 |
| camp-hit share of body-rounds | 12.5 % | ≥ 18 % |
| camp-hit rate with an enemy within 8 | 6.3 % | ≥ 14 % |
| walking with an enemy within 8 | 20.8 % | ≤ 15 % |
| multi-body episode: rounds with nobody hitting | 55 (opening) | ≤ 30 |
| deaths | 10 | ≤ 5 |
| deaths preceded by 2+ approach steps | 70 % | ≤ 30 % |
| moves in the 12 rounds after being hit first | 70 % | ≤ 50 % (fight ≥ 30 %) |
| 10-round exchange when attacked: hits landed by us / by them | 3.8 / 7.0 | ≥ 6 / ≤ 6 |
| bank trips / carry rounds | 12 / 43 | ≥ 24 / ≤ 30 |
| shop visits | 39 | ≥ 60 |
| gold earned | 2,600 | ≥ 5,000 |
| wards in bushes | 37 % | ≥ 50 % |

Then the ladder A/B with paired groups against Mite and IC on the same maps and sides (`tools/paired_groups.py`), 14 groups each,
as the god22 plan already specifies. Expect the TOL (6.1) alone to move the richest-group metric and the middle captures first;
the fight engine (6.2) moves deaths; 6.3/6.4 move the camp-hit share. Ship them as separate switches but test them together: the
TOL puts bodies where the fights are, so without 6.2 it will lose more bodies before it wins more gems.

Implementation order (each step gated by its metrics): 6.4.1 opening and 6.5 banking (one day, no risk) → 6.3 farm through
contact and the OPPORTUNITY removal (one day) → 6.2 fight engine (two to three days; the largest single change; replace, do not
add) → 6.1 TOL with the prime warden and the shared-memory clock (two days) → 6.6 draft priors and 6.4.2 builds (half a day) →
6.7/6.8 messaging and wards (one day) → section 9 special-map plans.

---

## Appendix A. Per-map results (v75 vs Mite; v79 in the second block of `aggregate.py` output)

`map  final  banked us-them  captured us-them  deaths us-them  first gem capture us-them  size  champs`

```
00stampede        1500    0-1040  cap    0-1120  d  9- 1  first None- 854  60x50 c5
01boss_battle      688    0-1017  cap  625-1303  d  5- 2  first   33-  29  50x41 c5   (625 captured, 0 banked: single altar)
00ribs            1151    0-1013  cap   57- 970  d 13- 3  first  255- 107  51x85 c5
01elk_arena       1083    0-1008  cap    0-1008  d 13- 3  first None-  58  50x50 c5
01hooks           1415    0-1001  cap   44- 968  d 24- 0  first  944-  42  31x31 c4
01corridors        839   64-1064  cap  130-1110  d  6- 1  first   99-  55  51x40 c5
00fragment        1321   44-1022  cap   76- 990  d 18- 0  first   75-  34  30x30 c3
adgato_gemcombat5  461  112-1085  cap  196-1071  d  8- 1  first   39-  57  99x99 c5
01starvation      1552   56-1013  cap  132-1028  d 15-10  first   80-  77  80x80 c5
00crater           878   76-1011  cap   87-1000  d 15- 1  first  117-  28  61x61 c5
01starfish         894   86-1000  cap   86-1164  d 22- 5  first   38-  27  50x50 c5
00gemfight         706   96-1007  cap  138- 979  d 13- 1  first  164-  10  30x30 c4
01concentrated_wealth 944 117-1020 cap 170- 989  d 24- 3  first   61-  61  61x61 c5
00dunes            760  116-1011  cap  220-1077  d  2- 2  first   51-  47  79x79 c5
00interlock        876  120-1009  cap  164-1021  d 10- 2  first   35-  20  40x40 c4
01fracture         946  135-1013  cap  431- 929  d  5- 4  first   50-  44  61x71 c5
00rushbait_v2      881  147-1023  cap  234-1035  d  6- 1  first   67-  32  30x80 c4
01shortcut         841  181-1054  cap  431-1212  d 10- 8  first   30-  27  40x40 c4
00reverse_spiral  1199  142-1012  cap  186-1160  d 14- 4  first  165-   8  30x30 c4
00quarry           832  142-1010  cap  114-1038  d 10- 4  first  188-  29  35x29 c4
00swirl            845  155-1008  cap  155-1008  d 18-12  first  102-  42  45x30 c4
00eight            825  166-1013  cap  343- 954  d 13- 2  first   37-  34  41x30 c5
00packs            909  174-1018  cap  174-1018  d  9- 0  first   29-  23  31x31 c3
00lost_world       626  189-1016  cap  182-1051  d 15- 7  first  185-  48  35x31 c5
01gold_rush       1350  187-1007  cap  209- 985  d 27- 3  first  151- 334  31x31 c3
02arena           1080  181-1001  cap  213- 976  d 16- 1  first    9-   8  30x30 c3
01the_farm         822  216-1025  cap  377- 864  d  6- 3  first   36-  40  50x40 c3
02treasure_box     944  310-1094  cap  405-1029  d 16- 5  first   81-  75  35x35 c5
00collision        883  305-1080  cap  464-1009  d  7- 0  first   28-  58  41x41 c3
02the_pack        1335  293-1068  cap  240-1417  d  8-10  first   42-  15  45x45 c3
01broken_curve     791  299-1030  cap  343- 990  d  5- 0  first   44-  29  40x40 c3
adgato_gemcombat3  443  273-1001  cap  434- 959  d  6- 2  first   17-  15  51x51 c4
00anvil           1840  298-1018  cap   85-1478  d 13- 8  first   89-  15  37x31 c3
00oasis           1375  312-1000  cap  378- 956  d 22- 1  first   28-  20  29x29 c4
00the_line         669  346-1030  cap  201-1207  d  9- 4  first   54- 101  33x33 c4
adgato_gemcombat2  661  364-1022  cap  371-1057  d  3- 3  first   17-  14  51x31 c4
00galaxy          1051  372-1001  cap  330-1127  d 10- 2  first   45-  32  93x93 c5
02geodes           678  409-1023  cap  594- 994  d  1- 0  first   35-  19  89x71 c5
00pilgrimage      1253  393-1006  cap  486-1006  d  8- 0  first   58-  55  50x65 c5
00lanes            782  414-1003  cap  425-1014  d  4- 0  first   56-  56  90x30 c5
00corners          740  428-1014  cap  420-1056  d  4- 2  first   30-  23  71x71 c5
02uncharted_lands  827  559-1143  cap  663-1132  d  6- 3  first   34-  14  50x46 c5
02tangle           947  422-1005  cap  662- 975  d  2- 0  first   52-  34 100x80 c5
00expanse          829  462-1036  cap  462-1036  d  3- 0  first   40-  17  80x80 c5
02fields           761  453-1022  cap  490-1080  d  6- 2  first   35-  32  51x51 c5
02stalactites     1108  512-1058  cap  257-1719  d 13-17  first   31-  54  30x30 c4
01yellow_brick_road 921 455-1000  cap  463-1037  d 11- 4  first   27- 148  40x30 c5
00quadrants        388  507-1046  cap  507-1046  d  1- 0  first   21-  18  45x45 c5
00gem_fields       557  482-1005  cap  482-1028  d  6- 0  first   11-  31  50x40 c5
00rows             914  594-1109  cap  594-1109  d  0- 0  first   42-  35  50x50 c4
02guardians       2000   45- 551  cap  513-2549  d 21-22  first   81-  24  41x41 c4   (round limit)
02crossing         604  527-1004  cap  534-1004  d  6- 2  first   29-  32  51x51 c5
00split            756  541-1012  cap  479-1093  d  7- 3  first   72-  46  45x35 c5
02harvest          905  570-1028  cap  624-1057  d  5- 1  first   42-  29 100x100 c5
adgato_gemcombat1 1061  567-1008  cap  567-1050  d  6- 2  first   13-  10  31x31 c3
00elkring          719  594-1012  cap  726- 968  d  5- 1  first   22-  17  30x30 c5
00vault            902  771-1151  cap  355-1739  d  6-16  first  226-  52  31x31 c4
00great_wall       995  662-1013  cap  806-1071  d  6- 4  first   28-  33  50x40 c5
02famine          1400  686-1005  cap  744-1047  d  3- 1  first   33-  25  91x75 c5
01islands          843  690-1008  cap  701-1008  d  2- 0  first   77- 117  60x60 c5
02cuts            1053  738-1044  cap  739-1076  d  1- 1  first   32-  24  60x60 c5
02gift_wrapping    780  738-1030  cap  738-1094  d  7- 2  first   35-  43  45x45 c5
00ambush          1286  840-1019  cap  979-1089  d  3- 0  first   69- 384 100x100 c5
adgato_gemcombat4  577  868-1029  cap  833-1120  d  6- 1  first   19-  15  41x61 c5
00contest         2000    0-   0  cap    0-   0  d 56- 0  first None-None 50x50 c5   (lost on gold/kills tiebreak)
```

Loss margin against our deaths and the map's middle richness (130 games):

| our deaths | games | our share of banked gems | our captures / theirs | middle share of map gems |
|---|---|---|---|---|
| 0–2 | 14 | 0.35 | 0.62 | 0.62 |
| 3–5 | 26 | 0.30 | 0.50 | 0.50 |
| 6–9 | 43 | 0.23 | 0.36 | 0.60 |
| 10+ | 47 | 0.14 | 0.19 | 0.73 |

Even with 0–2 deaths we capture 62 % of what Mite captures: the farming gap (sections 4.1, 4.3, 4.4) is the floor; deaths take it
from there to 19 %.

## Appendix B. The 70 official maps

Columns: size, champions, groups, gem groups, total gems, total gold, share of gems in the middle, richest group (gems, zone,
walking distance from spawn A / B, share of the map's gems), altars, walking distance richest group → nearest altar, spawn →
nearest altar, spawn → spawn, monoliths, golems, share of gems in the three richest groups. Full table: `map_pool_features.json`.

Pool summary: richest group in the middle on **57 / 70** maps (in our half on 13, never in theirs by symmetry); ≥ 50 % of gems in
the middle on 46 / 70; richest group ≥ 30 % of all gems on 29 / 70; three richest groups = 60 % of gems on average; single altar
on 15 maps; monolith maps 22; golem maps 18; 3 / 4 / 5 champions on 12 / 16 / 42 maps; mean 444 gems per map (so 1,000 banked
needs 2–3 full cycles of the map, i.e. the respawn clock decides).

The maps where the richest group is in a half (fracture, starvation, treasure-box, gem-fields, lanes, gemcombat1/4, corners,
collision, road-of-riches, eight, split, elkring) are the ones where 6.1.4's raid logic and the own-half cycling matter more than
P0; they are also the maps where we lose by the least today (ambush, gemcombat4, cuts, famine, islands: 0.7–0.85 of Mite's
captures).

## Appendix C. Scripts (`analysis/`, Python 3, no dependencies; decode with the repo's `tools/replay/decode.mjs`)

| script | output |
|---|---|
| `mapjson.mjs replay-or-map out.json` | tiles, spawns, camps (both sides) of a map or of the map inside a replay |
| `analyze.py <decoded dir> <mapjson dir> out.jsonl` | per-game record (section 1); `SIDES_JSON=…` overrides which team is ours (else the loser) |
| `aggregate.py out.jsonl` | the tables of section 2 and Appendix A |
| `groups.py` | every group clearance (bodies, concurrency, rounds, capture, steal) |
| `engage.py`, `exchange.py`, `response.py`, `deaths.py` | section 3.4 / 4.2 |
| `opening.py`, `episodes.py`, `gaps.py` | sections 3.2 / 4.3 / 4.4 |

Reproduce: decode (`node tools/replay/decode.mjs X.repl26a --gold-captures --out X.json`, 3 s a game), `mapjson.mjs` per replay,
then `analyze.py` + `aggregate.py`. The same scripts are the acceptance tests of section 10 on local `cambc run-batch` replays.
