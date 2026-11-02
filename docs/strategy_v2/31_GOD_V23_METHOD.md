# GOD v23 — the method: how to make the bot stronger, what to change, what to trade, and the fuel to pay for it

This is the build specification. It contains decisions, not options: for every area it says what the bot does, why that is the
best choice we can justify from the data (the loss study `WHY_WE_LOSE_TO_MITE_AND_IC_AND_THE_FIX.md`, the repository's own
measurements, and today's local runs), what the choice costs (the tradeoff), what it costs in fuel, and how to verify it. Where a
previous version of ours already had the mechanism, it says whether to keep it, switch it on, or replace it.

Scope of evidence: 130 replays of v75/v79 vs Mite, 70 of v75 vs IC, 70 official maps, 25 shipped versions with their local and
ladder records (`submissions/BUILDS.md`, docs 7–30), the fuel streams of the 130 Mite games, and 17 local benchmark runs made
today (2,266 games on the 70-map pool and the 51 held-out maps; section 2.3, Appendix A).

---

## 1. Decisions at a glance

| area | decision | why (evidence) | tradeoff accepted | fuel |
|---|---|---|---|---|
| base code | **v75 = GOD v18** (`bots/gpta75`) + the harmless v22 additions (`g22_exact`, `g22_msg` replaced by §4.9) | every version from v15 to v22 is level with v18 locally (±50 gems, the noise floor) and 0–8/70 against the top 3; v18 is the one with 400+ ladder games and the fewest defects (doc 30) | the v20/v21 pack code stays off (its job is done better by §4.3); the v19 fight margins stay off | unchanged, 31k mean / 79k p99 per turn |
| team objective | **own the richest reachable groups on a respawn clock** (§4.3) | Mite/IC capture the richest group 6.6× / 4.7× a game, we 0.3×; 54 % of Mite's gems; 57/70 maps have it in the middle | some own-half groups go unfarmed while the roster is at the prime group (Mite accepts the same: own-half 7.4 captures/group, ours 4.9) | +3k per turn, +3 distance fields at init (deferred) |
| fights | **commit-or-avoid engine** (§4.5): never run from a faster chaser, initiate only at R ≥ 1.15 or a kill, join allies at R ≥ 0.85, 6-round commitment | we start 25 % of fights and lose 52:12 when they start; 70 % of our deaths follow 2+ approach steps; defender hits 3.8 vs 7.0 in the first 10 rounds | more fights are fought to the end (a committed body can die where today it would have run and *also* died); the proxy that only "never flees" lost 32/140 (-339, deaths 18 vs 8): the gates are what make it work | +5–8k per turn with enemies in sight |
| farming | **farm through contact** (§4.4): an enemy in sight is not a reason to stop hitting; synchronized arrivals; tank rotation | camp-hit rate with an enemy within 8: us 6.3 %, Mite 16 %; our 20–50-gem clears take 66 rounds vs 37 with the same bodies | a body that keeps farming next to an enemy takes a first hit more often; §4.5's escape rule decides what happens next, not a flee reflex | none |
| banking | **bank small and near** (§4.6): ≥ 15 gems with an altar ≤ 6, ≥ 30 anywhere, hard cap 60; tribute during fights; locks on single altars | Mite banks 28× a game with 35-gem bags carried 30 rounds; we 12× / 27 / 43; 21 % of what we capture is lost on death | more bank trips = fewer farming rounds; at Mite's cadence that is ~90 body-rounds a game, far below the 600 we lose dead | none |
| economy | Jungle first on every body, Bruiser stacks, damage stat on carries, Power focus on Marcella, one Capture emblem, shop at Mite's cadence (§4.7) | Mite 2.4× our gold and ~2× our stats by r600; Jungle by r95 lets it farm without heal trips | no Treasure/Monster-first farming builds (they pay off only after the fights we lose) | none |
| draft | VV first always; Vendetta, HoR; **Tavi + Marcella** (5), **Cassi & Issac** (4), VV/Vendetta/HoR (3); adaptive engine keeps counter-picks (§4.1) | both top teams; our Ryth deals 47 dmg/round and dies 117 times in 65 games; C&I is 5 bodies for 4 picks (IC 57/70, Mite 16/16) | C&I die together: pair rules in §4.5.7 | draft turn 1 uses 0.6 M of 10 M |
| vision | ward roles: prime-clock warden, approach bush, bank altar; enemy-ward map; fight and hide from bushes (§4.8) | Mite 49 % / IC 71 % of wards in bushes, 38–43 % in the middle; ours 37 % / 22 % | a ward spent on the clock is one fewer following a farmer; the warden's ward never moves | ≤ 13k on a placement turn, ≤ 1 placement per 10 rounds per body |
| messages | `set_priority` carries hp/state/target/flags; shared memory carries claims + prime clock; OPPORTUNITY alert dropped (§4.9) | Mite writes 57 distinct values 800× a game; our fights are judged from one body's sight (doc 30 §5.1) | 2 host calls per turn (write + read) | +0.5k |
| recall bait | **off** (`g17_bait 0`) | 0 measurable effect in 130 games (Mite dies 3.1 with it, IC 8.5 without); 2 host calls per turn; the cancel can leave a body channelling | the viewer stops "stuttering"; local self-play said -64 ± noise because our own brain chased baits | −0.3k |
| learners | stance bandit, pain map, fight calibration, race mode, opponent model: **off** | never measured against a top team; they add state that makes behaviour non-reproducible between games | none that we could measure | −1–2k |
| fuel | budget per module (§5); heavy work in the draft (10 M) and at deferred init turns; floors in every loop | we lose 4–5 turns a game today (3 in rounds 1–3), Mite 25; p99 79k leaves ~20k for the new modules | ward scoring and far-group scoring yield to the fight engine when fuel is short | see §5 |
| evaluation | behaviour metrics on local replays + paired ladder groups vs IC/Mite; **no** ship decisions from self-play win rates (§7) | every self-play "level or worse" verdict since v14 was taken against our own older bots; the ladder never confirmed one | slower iteration; fewer false confidence | — |

---

## 2. Base version, configuration and what the repository's measurements say

### 2.1 Which of our versions is strongest

| website | GOD | what it added | local vs its predecessor | against the top teams / the ladder |
|---|---|---|---|---|
| v71 | v15 | gold funnel (`mi_capture`), locks | +113 vs v14 | 0–10 vs IC/Mite (doc 24) |
| v72–v73 | v17 | fake-recall filter, recall bait | +98 vs v15 | 0–10 post-patch (doc 25) |
| v74/v75 | **v18** | contact discipline, A-B-A breaker, fast init, pick prior | +154 vs v17 | IC 7–8/70, Mite 5/70; ranked 47.6 % (210 games) |
| v76 | v19 | stricter fight margins | — | IC 5/70, rolled back in 10 minutes |
| v77 | v20 | adaptive pack, capture funnel 2, rich joins | level vs v18 (+35 ± 100) | IC 7/70, Mite 5/70, TK 7/70; ranked 60 % (65 games, p ≈ 0.08) |
| v78 | v21 | pack all game | level vs v18 (+82 ± 105) | rolled back, no record |
| v79 | v22 | chase drop, solo veto, engine damage numbers, fight flags | level: 47/100 vs v75 today (+19 [−103, +137]) | Mite 0/65, same numbers as v75 |

Nothing in this lineage is stronger than v18 in a way the data can see; the one ladder differential (v20's 60 %) is 65 games and
p ≈ 0.08, and v20 was no better against IC or Mite. **Decision: build on the v75 source** (it has the largest ladder record and
the audit's defects are known), keep the v22 `g22_exact` (engine `damage_amount` in the kill check: correct and cheap), and
treat the v20/v21/v22 mechanisms as superseded by §4.3 and §4.5 rather than switched on.

### 2.2 The tradeoff that kept us weak: how changes were judged

Every switch since v14 was accepted or rejected by playing against our own earlier version (v13, v14, v17, v18) or against forced
rosters on our own brain. That test has a noise floor of ±50 gems (the null control in doc 28 moves by 41–50), it is a mirror draft,
and the opponent never hunts, so three classes of change were rejected for the wrong reason:

- **changes that fight more** (`_fl1` flee less +29, `fight_back_margin` 1.0 +16, C&I +16..+41, `_F4` +81 vs v18 but 50 % vs v17): they
  lose to v17 because v17 does not punish, and that was read as "non-transitive, not better";
- **changes that farm near enemies** (`g19_hold` −39..−78, `_pf` never-flee −339): they died more against our own brain's kiting, which
  is exactly what §4.5 fixes before §4.4 is switched on;
- **patch-2.0.0 items** (Capture −47, Greed −34, Treasure→Monster level): judged on a pool where both sides already farm alike.

The repository's own audit (doc 30 §8) reached the same conclusion. **Decision: the ship gate is (a) behaviour metrics on local
replays with Mite's numbers as targets (§7), (b) paired unranked groups against IC and Mite on the same maps and sides; local
self-play is only a null check (faults, fuel, no regression beyond −100).**

### 2.3 Today's local runs (70-map pool, both sides, 140 games each, vs the live v75; margin = banked gems, bootstrap 95 %)

These runs are *not* ship evidence (§2.2); they check that a switch does not break anything and show its direction on farming
numbers we can read from the engine's statistics. The table is filled in Appendix A with the numbers; the decisions below already
account for them.

| variant | switches | purpose in the plan |
|---|---|---|
| `_bank` | `tribute_min` 30, `early_tribute_min` 15 | §4.6 banking cadence (interim until the full rule) |
| `_cap` | `g18_capture` 2 | §4.7 Capture emblem |
| `_ward` | `g22_ward` 1 | §4.8 coverage wards (interim) |
| `_nobait` | `g17_bait` 0 | drop the recall bait |
| `_wait` | `max_wait` 40, `g18_rich` 1 | §4.3 respawn waiting and rich-group joins (interim) |
| `_defend` | `ally_defend` 1 | §4.5.6 second wave (interim) |
| `_combo1` | `_bank` + `_nobait` + `_wait` + `_defend` + `g18_capture` 1 + `cap_recall_gold` 250 + `mi_pick` 0 | the configuration-only build |
| `_fight1` | `outmatch_flee` 0, `ml2_flee` 0.5, `fight_back_margin` 1.0, `isolated_flee_adv` 1.2, `ml2_leave` 0.3 | "flee less" by parameters only (the §2.2 class) |
| `_tavi` | `pd_sub_from` 0, `pd_sub_to` 10 | Tavi wherever the draft plans Ryth |
| `_combo2` | `_combo1` + `_fight1` + `_tavi` | everything by parameters |
| `_combo3` | `_bank` + `_wait` + `_defend` | the three singles that were positive |
| `_cap1` | `g18_capture` 1 | one Capture holder |

### 2.4 Configuration ledger (what is on, what goes off, what is replaced)

| switch (v75 default) | action | reason |
|---|---|---|
| `g22_exact` 1 (v79) | **on** | engine damage after mitigation in the kill check |
| `g22_msg`, `g22_solo`, `g22_chase`, `g22_chase_deep` | off, replaced by §4.9 / §4.5 | same intent, done once instead of as vetoes |
| `g17_bait` 1 | **off** | §1 |
| `g17_fakerec` 3 | keep (filters enemy baits) | harmless |
| `g15_lock` 15 | keep bits 1,4,8; **drop bit 2** (OPPORTUNITY tribute timer) | the alert slot becomes DANGER/RALLY only; locks are driven by §4.6 |
| `mi_pick` 3 (pre-patch per-map prior on 40 maps) | **0** | pre-patch data; a per-map table; §4.1 fixes the roster by rules |
| `mi_capture` 1 | keep | the gold-bonus body captures shared rewards (matches top teams 65 %) |
| `learn_enabled` 1, `learn_stance`, `learn_fight`, `race_mode` 1, `opp_*`, `om_*`, `death_learn` | **off** | §1 learners; they were tuned on the pre-patch legend lineage against our own proxies; if a §7 metric drops when they are off, re-enable one at a time and measure it alone |
| `ml2_flee` 0.35, `ml2_leave` 0.2, `ml2_cornered` 1 | replaced by §4.5 (the model's P(die8) stays as one input, never a veto on its own) | the model was trained on our own old deaths |
| `outmatch_flee` 1, `isolated_flee_adv` 1.5, `flee_dist` 5, `burst_exit` | replaced by §4.5 | |
| `fight_margin` 1.4, `isolated_fight_adv` 1.35, `fight_back_margin` 0.873, `cornered_margin` 0.74, `px_mode` 2 | replaced by R thresholds (§4.5.3) | |
| `fz_engage` 4, `fz_chase` 4 | replaced by the engagement gate | |
| `g15_calm` 5 | keep bits 1 and 4 (threat = can hit us next turn) | consistent with §4.4 |
| `tribute_min` 54, `early_tribute_min` 22, `tribute_near` 5 | replaced by §4.6 | |
| `cap_recall_gold` 60 | **250** with §4.7's shop rule | 12.8 high-health recalls a game today |
| `max_wait` 18, `obj_max_wait` 18 | **40** at a prime rally (the roster's wait is a deadline, not a max) | Mite's median wait 0 = already there |
| `g18_rich` 0 | **1** | rich harmless groups are team targets (vault's 343-gem centre) |
| `g18_capture` 0 | **1** (one holder: the prime capturer) | §4.7 |
| `g18_fast_init` 1, `g18_osc` 6, `defer_islands` 1, `stall_guard` 10, `unstick_rounds` 10 | keep | movement hygiene |
| `ward_v14` 1 (bush ward within 2) | keep as the interim; replaced by §4.8's roles | `g22_ward` 1 is **not** the interim: +4.8k fuel a turn and only 16 % of wards in bushes (today's run) |
| `g21_fort` (v21 code) | **on** from round 1 as part of §4.5.3 ("on spawn: fight") | spawn heals every round |
| `pxs_*`, `mapdraft` proxies, `official_map()`, `pack_maps.h`, `known_maps.h` tables | out of the submission | per-map tables violate the standing rule; dead code costs fuel and size |

---

## 3. Architecture: one plan, five executors

```
draft turn 1 (10 M fuel)   map model: groups, values, BFS from both spawns, zones, prime set, rally/ward/altar per prime group,
                            opening schedule, roster → DRAFT MEMORY (PRIME block, 100 free bytes + the MAPINTEL block already written)
draft turns 2..k (100 k)    picks (adaptive engine, §4.1); refresh PRIME for the final roster on the last turn
game turn 1 (200 k)         init: read draft memory, spawn field, opening field (the rest deferred to turns 2–5)
every game turn (100 k)     1 perceive (own vision + ward)        2 read shared memory + ally priorities
                            3 TEAM PLAN (§4.3): prime clock, roster, my role          ~3 k
                            4 FIGHT ENGINE (§4.5): state ∈ {KILL, FIGHT, AVOID, LEAVE}  ~5–8 k with enemies in sight
                            5 the executor of my role: PRIME / FARM / BANK / SHOP / WAIT (§4.4, §4.6, §4.7)
                            6 ward (§4.8, ≤ 1 placement per 10 rounds)   7 write shared memory + priority (§4.9)
```

The body's **role** comes from the team plan; the **state** comes from the fight engine; the executor acts for the role unless
the state is FIGHT or LEAVE. Both have hysteresis (role: until the prime deadline or a capture; state: 6 rounds). Nothing else
in the turn may override them: `safety()`, `respond_to_alert()`, `home_trip()` and the capture-recall are folded into the
executors (they remain as helper functions, not as a decision chain).

---

## 4. Modules

Each module: what it does, the rule or API it relies on, parameters (chosen values), fuel, tradeoff, and the metric that proves it.

### 4.1 Draft

**Roster rule (decided).** Pick order and roster by team size:

| size | picks in order | notes |
|---|---|---|
| 5 | Vesper Vale, Vendetta, Heart of Ruin, Tavi, Marcella | Mite's roster; VV first because +33 % gold is the snowball itself |
| 4 | Vesper Vale, Vendetta, Heart of Ruin, Cassi & Issac | 5 bodies; C&I rules in §4.5.7; replaced by Marcella when the map has < 8 gem groups (few groups = nothing for a 5th body to farm) |
| 3 | Vesper Vale, Vendetta, Heart of Ruin | |

**Adaptive deviations (the existing `param_pick` engine keeps its model; these are its priors and rules):**

- single rich objective map (`rich_share ≥ 0.5`, §4.11): Prism replaces Tavi (ring damage from range 4, focus scales with the
  carried bag), Marcella stays;
- lone-monolith map (contest-type): Ryth replaces Heart of Ruin (area stun on their pack, strength from bonus health for the
  20,000-hp monolith): the game there is fights and gold, not farming speed; Tavi stays (stun + field shopping);
- counter-picks from the enemy's revealed picks: enemy has 2+ dash melee → Marcella's priority +0.3 (stun-immune); enemy shows C&I
  → a burst pick (Stellar or Marcella) +0.2 (one kill = two bodies); enemy has 3+ ranged → HoR +0.2 (dash landing stun on the
  backline). Counters never displace VV.

**Tradeoff.** Fixed-by-rule rosters are what both top teams do and what the standing rule forbids only as a *per-map table*; these
rules key on team size and map features, not map names. The draft model's learned weights (`pd_w_*`, fitted on engine 3.0.4)
stay only as tie-breakers. **When to ship the roster:** with the fight engine, not before it. Tavi for Ryth on the v75 brain
measured −22 alone and −102 / −165 (s3 / held-out) inside the Step-0 configuration today, with +1.4 to +2.9 deaths: a 900-hp
stunner that our current `combat()` sends into fights alone is a liability; under §4.5 (second wave, positioning behind the
melee, stun-the-chaser) it is Mite's best fighter (142 damage a round). The same holds for Cassi & Issac (−140 on v17's brain).

**Draft memory.** The draft already writes the MAPINTEL block (per group: bank altar, both walks, 16 contested groups, plan 1) and
the CODE rally tiles; 100 bytes are free. Add the **PRIME block** (version 1, TOC id `P`): for each of ≤ 3 prime groups: group id
(1), rally tile (2), ward tile (2), nearest altar id (1), force F (1), first-cycle plan (1: 0 = we are first, else the round
(÷8) at which the roster must be at the rally), and the opening group id, staging tile and the first 12 steps of each body's
opening path (12 × 5 = 60 bytes, so the first game turns walk without a field). Total ≤ 90 bytes. Fuel: ≤ 150k on draft turn 1
(the BFS fields are already computed there for the MAPINTEL block); the draft's remaining budget is 9.4 M, unused today.

### 4.2 Map model at init (per body, game turn 1 and deferred turns)

- Turn 1 (200k budget; today's init uses 180k): read draft memory, build the spawn field and the opening path from the PRIME block;
  **no other field**. Turns 2–5: one prime-group rally field per turn (13–19k each on 100×100), then the altar fields
  (`prebuild_fields` already staggers these; add the prime fields to its queue ahead of islands).
- Static caches (`map::camp_groups()` ≈ 25k: once; `max_respawn_timer` per group; camp ranges per type) stay as v18 does them.
- Zone of every group, `dA`/`dB` per group and per altar come from the MAPINTEL block (no recompute).

**Fuel.** Removes nothing from today's init; adds ≤ 19k on each of turns 2–4, which have 70k of headroom (mean turn 31k).

### 4.3 Team Objective Layer (TOL): own the rich groups on a clock

**Prime set P (draft time).** `value(g) = gems + 0.15·gold`. P = groups with `value ≥ 0.5·max_value` **or** `gems ≥ 36`, and
`dA(g) ≤ dB(g) + 6` (we reach it no more than 6 rounds after they can), sorted by value, capped at 3. A richest group deeper in
their half (`dB + 6 < dA`) is the **raid target** (§4.3.5), not prime. On 3-champion maps |P| ≤ 2. If no group qualifies (gem-less
maps like contest) P is empty and §4.11 applies.

**Per prime group (draft time):**
- rally tile: a free tile at distance `max_camp_range + 1` from every camp of the group, on our side (`dA ≤ dB` for that tile),
  from which the most camps are within 4; prefer a bush tile (invisible from outside) — ties by distance to our spawn;
- ward tile: a legal tile within 2 of a group tile whose ward vision (`ward::visible_tiles_from`) contains ≥ 1 original spawn
  tile of the group; prefer a bush; this is what makes the respawn timer readable (`camp_group::state()` needs an original spawn
  tile in vision);
- altar: nearest altar by walk from the group's centre and the walk length;
- force F(g): the number of bodies that clears it in ≤ 25 rounds at the roster's turn-1 damage: 3 for 36–80 gems, 4 for 81–200,
  5 above (recomputed live from `dps_on` once items change the numbers).

**Live state.** Shared memory bit 7 of bytes 0–5 = **prime clock**: 5 bits = rounds until P0 is next alive, in units of 4
(0 = alive now or dead with the reward uncaptured; 31 = unknown or ≥ 124), + 1 bit `enemy_holds` (an enemy body seen on a P0 tile
or within 3 in the last 10 rounds). Written by the warden (below) each turn, or by any body that sees P0's state when the warden is
dead. Requires `opp_plan`, `opp_model`, `alert_refresh`, `mi_live` off and `g15_lock & 2` off (§2.4). Claims (bits 0–6) and
the alert slot (bytes 6–7, DANGER / RALLY only) stay.

**Team plan (every body, every turn, identical inputs → identical output; ~3k fuel):**

```
ready_in = prime clock (own vision beats the shared value when P0's spawn tile is visible to me)
need     = F(P0) + (enemy_holds ? 2 : 0), capped at alive bodies
eta_i    = rally field value at ally i's position (position from vision, else the centre of its claimed group, else unknown → skip)
commit_i = alive_i and not channelling and eta_i ≤ ready_in + 2
roster   = the `need` committed allies with the smallest eta (ties: more hp, then lower index)
my_role  = PRIME if I am in roster else FARM
```

**PRIME role executor.**
1. Leave for the rally so as to arrive at `ready_in − 1`: while `eta_me + 1 < ready_in`, farm with the normal scorer under the
   constraint `clear_time(g) + walk(g → rally) ≤ ready_in − 1` (groups that cannot be finished in time are not started).
2. At the rally: `T_WAIT` with the deadline (never dropped by `max_wait`/`unstick`); place the ward if I am the warden; shop if
   spawn is ≤ 8 steps and `ready_in ≥ 12`.
3. The round the group is alive: hit (§4.4 execution). The **capturer** = the roster body with the Capture emblem, else the gold-bonus
   body (`mi_capture`), else the lowest index; the others start the next-best group within 8 or escort the capturer when
   `enemy_holds`.
4. After the capture: capturer → tribute if an altar is within 6 (§4.6), else back to FARM; the clock restarts from the engine's
   timer (`max_respawn_timer`), and the roster for the next cycle is already defined by the same formula.

**4.3.1 Contested prime group.** If `enemy_holds` and the local ratio R (§4.5.1) at the rally with the roster's bodies is < 1.0:
do not engage; farm the next groups; the next cycle's `need` = all alive bodies, and the roster arrives at `ready_in − 3` so the
whole team is there when it spawns. Mite stations 2.3 bodies there at the respawn moment (≥ 3 in 48 % of cycles) and keeps ~1.2
bodies waiting from 20 rounds before: five arriving together beat that. If R ≥ 1.0: engage as a team (§4.5.4) with the rally as
the anchor; never trickle in.

**4.3.2 Opening schedule (draft time).** `t_us = dA(P0)`, `t_them = dB(P0)`.
- `t_us ≤ t_them + 2`: everyone to P0 first (first hit ≤ `t_us + 4`).
- else: opening group O1 = the highest-value group with `dA(O1) + clear(O1, all bodies) + walk(O1 → rally(P0)) ≤ t_them +
  clear(P0, their 5) + 5 + max_respawn(P0)` (be at P0's rally for its first respawn with everyone); on the way, clusters (120 hp,
  harmless) are taken by whoever passes within 2.
- 3-champion maps: the same with 3 bodies; no raids.

**4.3.3 Warden.** The roster's ranged body with the lowest index places its ward on the ward tile at its first visit and never
re-places it (`ward_hold` ∞ for that body); it writes the prime clock every turn it sees the group's state. If it dies, the next
roster body takes the role on its next visit. One ward buys an exact timer for the whole team; today nobody knows when the richest
group respawns unless a body happens to look at it.

**4.3.4 Second and third prime groups.** The same formula runs for P1 and P2 with the bodies not in P0's roster; a body is in at
most one roster; P1/P2 clocks are kept per body from own vision (no shared bits) and shared through the RALLY alert when a roster
is short.

**4.3.5 Raid target.** Taken only when ≥ 4 bodies are alive, the enemy's bodies seen within 10 of it in the last 15 rounds ≤ 1,
and `ready_in(P0) > 25`; the raid party is 2 bodies (the FARM bodies with the smallest eta), it leaves the moment a second enemy is
seen (§4.5 AVOID), and the ward one of them carries is placed on the raid group's ward tile (its clock becomes readable too:
§4.8). Today: 31 attempts on their-half groups in 65 games, mostly by single bodies: 23 groups killed, 15 captured, and 17 % of
all our deaths happen on their half.

**4.3.6 Capture pressure.** A FARM body within 4 of a dead group that an enemy is capturing steps onto one of its tiles when no
second enemy is within 6 and it is faster than the capturer (dash ready, or the capturer is ranged and it is melee): the capture
timer resets (rule) and the enemy must restart its 5 rounds; the body leaves again under §4.5's AVOID the moment a second enemy
appears. Zero cost, no fight.

**Fuel.** Roster computation: ≤ 6 field lookups + a sort of ≤ 6 = < 1k; constraint checks reuse `group_score`'s eta. The rally
fields: §4.2. Writing the clock: one shared-memory byte write.

**Tradeoff.** While the roster waits at a rally, 1–2 bodies farm nothing for up to ~10 rounds a cycle (≤ 20 body-rounds per
60-round cycle, ~5 %); Mite pays the same. The pack variants (v20/v21) paid 10 % of unopposed pace because everyone walked
everywhere together; the TOL synchronises only one place at one time.

**Metric.** Richest-group captures ≥ 3 a game (today 0.3); middle gem groups ≥ 3 captures per group (0.7); rounds from respawn to
our first hit on P0 median ≤ 5 (28).

### 4.4 Farming executor

1. **Synchronized arrival.** A body heading to a group where ≥ 1 ally is also heading stops at the staging tile (`max_camp_range +
   2`) until the last expected ally is ≤ 2 rounds away, unless the group is harmless (clusters) or it can solo it in ≤ 12 rounds.
   Arrival spread today median 13 rounds; target ≤ 4.
2. **Continuous hitting.** Once in range, the body does not step except (a) to the tank-rotation tile, (b) FIGHT/LEAVE from §4.5,
   (c) the group is dead. Ranged bodies never move while a camp is in range (move *or* attack). Today 55 of 75 episode rounds have
   nobody hitting.
3. **Tank rotation (rule: camps hit the nearest champion).** Two melee bodies on a group alternate the nearest tile every time the
   front body's hp falls below 60 %: the camp retargets, both stay, nobody recalls. A ranged body stays strictly farther than every
   melee ally from every live camp. With one body on an elk/golem group (60/120 damage a round) it retreats only below 25 % and
   only if no ally can arrive within 6 rounds.
4. **Abandon rule.** A group is left only when (a) R < 0.6 against enemies that can reach the body next turn (§4.5 decides), or
   (b) `remaining_hp / our_dps > rounds until an enemy capture is possible` and the enemy would capture it (an enemy within 6 with
   more bodies), or (c) the PRIME deadline. Not for: an enemy in sight at 7–9 tiles; an enemy walking past; a RALLY from an ally
   more than 10 tiles away (RALLY answers are a §4.5.6 decision, not a farm interruption).
5. **Chip while passing** (`mi_chip` 1): camps never heal, so a ready damage spell on a camp within 4 while walking is free damage
   (and keep `hold_spells_near_enemies` for stuns only: a damage spell on cooldown costs nothing in a fight that is 8 rounds away).
6. **Capture → tribute** when the altar is within 6 (§4.6); the other bodies move to the next group before the capture completes
   (capture takes 5 rounds; the Capture holder 3).
7. **Camp-aware contact.** When an enemy approaches a body farming an awake camp, the body steps so that the enemy is nearer to the
   camp than it is (one step along the camp's far side): the camp hits them (`camp_in_fight 3` already counts this in the estimate;
   the executor must also *do* it).

**Fuel.** No new scoring; staging and rotation are a few comparisons.

**Tradeoff.** A body that keeps farming with an enemy at 6 will sometimes take the first hit. With §4.5 that first hit is answered
(KILL/FIGHT) or walked away from toward allies (LEAVE) — never with the 20-of-25-rounds running that kills us today. Switch §4.4 on
**after** §4.5; the never-flee proxy (`_pf`) shows what happens otherwise.

**Metric.** Camp-hit share of body-rounds ≥ 18 % (12.5); with an enemy within 8 ≥ 14 % (6.3); multi-body episode rounds with
nobody hitting ≤ 30 (55); first camp hit ≤ walk + 4 rounds (walk + 15).

### 4.5 Fight engine: commit or avoid

Replaces the rule stack in `combat()` (fight margins, isolated/outmatched flees, px_mode, ml2 vetoes, burst_exit, stay_rule,
fz_*, g22_*). Keeps the helpers: `burst_vs` with `g22_exact`, `reach_of`, `damage_amount`, `has_completed_turn`,
`remaining_channel_time`, `buffs()`, the enemy cooldown reads, `ml2_features` (as an input only).

**4.5.1 Local power ratio.** `R = Σ_ours hp_i·dps_i / Σ_theirs hp_j·dps_j` over bodies within 8 of the contact point.
`dps` = basic attack × (reset ready ? 2 : 1) + best ready spell / 3, with items through `damage_amount` on the real target
(ours and, for enemies, their `item_count()`), HoR's missing-health bonus, Varg's splash, Ren's retaliation. Bodies that cannot
reach the contact within 2 rounds weigh 0.5. Allies count if visible **or** their claim/priority puts them within 8; a committed
ally (priority flag) is never dropped for "walking away". Enemies on their spawn weigh 0. A stunned enemy's dps is 0 for this round.

**4.5.2 Escape test.** `escape = true` unless an enemy within `reach_of(e) + 2` is **faster than me**: melee with a ready dash
(from its readable cooldowns), or ranged with range ≥ 3 while I am melee, or any enemy with a ready stun within 4 (a stun costs
me a turn: it catches up); *or* if the walk to my spawn or to a tile adjacent to ≥ 2 allies is shorter than `hp /
incoming_per_round`. If `escape` is false, running hands over free hits every round: the state is FIGHT whatever R says.

**4.5.3 States and hysteresis.**

```
KILL   a visible enemy (not on its spawn) dies this turn to my hits + the committed allies' hits that land before its next turn
FIGHT  KILL, or !escape, or (R ≥ 1.15 and enemy reinforcement within 2 rounds ≤ ours), or (an ally within 6 is FIGHT and R ≥ 0.85),
       or I stand on my spawn tiles (full heal every round: anything that follows me there loses)
AVOID  otherwise, when no enemy can hit me next turn: keep the role (farm, walk to the rally, bank); do not step toward the enemy
LEAVE  otherwise: walk toward the nearest committed ally, else toward spawn, never through an awake camp's range; cast a stun on the
       fastest chaser first if one is ready; a melee swings at an adjacent enemy before the step (melee moves and attacks)
```
Hysteresis: FIGHT holds 6 rounds unless the target dies (re-evaluate at once), my hp < 20 % with `escape` true, or R < 0.6 because
a *new* enemy arrived. AVOID/LEAVE hold 3 rounds. A body that was FIGHT last turn and is AVOID now does not step toward the
enemy. `fight_commit` and `g18_osc` become redundant and are removed.

**4.5.4 Execution in FIGHT (order inside the turn).**
1. Team target: enemy in reach with the lowest `hp / Σ(committed allies' damage on it this round)`; +200 for stunned, channelling
   (`remaining_channel_time`), Cassi/Issac, carrying ≥ 20 gems; −∞ on its spawn. Broadcast its index (§4.9).
2. Stuns in sequence: a stun is cast only on a target not already stunned (`buffs()`), when it stops an escape or buys ≥ 2 committed
   hits this round. Marcella's enhanced attack, HoR's dash landing, Ryth's area, Tavi/Cassi/Prism/Ren.
3. Attack reset = a second basic attack in the same turn; cast only after the first landed.
4. Position: melee → the tile adjacent to the target that is adjacent to the fewest other enemies, then attack (move + attack same
   turn); ranged → do not move if the target is in range; else the nearest tile in range outside every other enemy's melee reach;
   `has_completed_turn()` true for all enemies in reach → stepping in is free this round. Never onto a tile in an awake camp's range
   unless the camp is nearer to an enemy (§4.4.7).
5. Bag: ≥ 20 gems and an altar within 1 → start the tribute now (damage does not cancel it; stuns do; Marcella is immune).
6. Low hp inside FIGHT: `escape` false → keep hitting (HoR: +50 % near zero, shield first); `escape` true and no KILL → LEAVE toward
   allies, not home.

**4.5.5 Engagement gate (starting fights).** We start a fight only at R ≥ 1.15 at the point of contact **and** their reinforcement
within 2 rounds ≤ ours (count bodies within 10 of the target on both sides). Nothing else walks toward an enemy: a non-KILL target
is not chased, not for 2 steps, not onto their half. Today 70 % of our deaths follow 2+ approach steps.

**4.5.6 Second wave.** When an ally within 8 is FIGHT (its priority flag), every body within 8 not in a tribute and not within 5
rounds of a prime deadline re-evaluates R with that ally's hp included; at R ≥ 0.85 it joins and focuses the broadcast target.
This replaces `ally_defend` (off today) and the single-responder `respond_to_alert`.

**4.5.7 Cassi & Issac.** Issac stays within 3 of Cassi; Issac fronts, Cassi at range 3 behind him; the pair's R uses both bodies
and their fight bar is 1.3 (one kill = two bodies for the enemy); they LEAVE together when either is below 35 %; the pair never
raids and is never the capturer under `enemy_holds`.

**4.5.8 Kill economy.** A kill pays 100 gold + the bag; Mite carries 23 gems when it dies and 9 kills a game is 850 gold + 60 gems
for it today. The KILL state and the carrier bonus in targeting turn that around; no separate "gank" module (`gank 0`).

**Fuel.** Per turn with enemies in sight: ≤ 6 enemies × ≤ 6 allies of arithmetic (~2k) + `damage_amount` on ≤ 6 enemies × ≤ 3 ready
spells (host calls, budget 5k) + reads of cooldowns/buffs (1k). Budget 8k; the executor's positioning is a 3×3 scan.

**Tradeoff.** Committed bodies die when a fight turns (a new enemy at round 3 of 6): accepted, because the alternative is what the
data shows (29 % death after being hit first vs Mite's 10 %). The 6-round commitment and the "new enemy → R < 0.6" release keep
that cost bounded. The engagement gate forgoes some winnable 1v1s at R 1.0–1.15: accepted, farming is worth more than a coin-flip
fight. **Why a replacement and not new margins:** today's `_fight1` (flee less by parameters) and `_combo2` lost 101 and 129
gems a game to v75 with 3.4–4.0 more deaths; a body that stays without the escape test, the stun-the-chaser step and the
positioning rules just dies more slowly. The margins are the smallest part of the engine.

**Metric.** Deaths ≤ 5 a game (10); deaths preceded by 2+ approach steps ≤ 30 % (70 %); after being hit first: fight ≥ 30 % of the
next 12 rounds, moves ≤ 50 % (17 % / 70 %); hits landed in the 10 rounds after being attacked ≥ 6 (3.8).

### 4.6 Banking and tribute

- **Thresholds.** Bank when `bag ≥ 15 and altar walk ≤ 6`, or `bag ≥ 30`, or `bag ≥ 20 and an enemy with R < 0.8 within 10`, or
  `bag ≥ 10 and prime clock ≥ walk-to-altar + walk-back + 2` (free time), or the bag wins the game. **Hard cap 60**: a body never
  carries more while an altar is reachable within 15 rounds. Target carry time ≤ 30 rounds (43–50 today).
- **Which altar.** The MAPINTEL block's bank altar per group (walk-length), with `unsafe_altar_penalty` only for an altar where an
  enemy was seen within 4 in the last 8 rounds; the spawn altar is never preferred for a recall when a field altar is ≤ 15 away
  (`bank_first` 1).
- **Tribute timing (rules).** Duration `max(1, ceil(bag/10))` turn ends, started on the move (moving and starting a tribute in the
  same turn works); ≤ 10 gems cost no stuck turn, so a 10-gem bag next to an altar is always banked. It completes at the next own
  turn start after reaching zero: in the last 30 rounds of the game, start the final tribute so that it completes before the enemy's
  can (we see their bag and channel: `remaining_channel_time`), and remember the first-mover alternates each round.
- **During fights.** §4.5.4 step 5. Marcella banks contested altars (stun-immune, +2 gold per gem).
- **Locks.** Every body carries one lock (10 gold, `g15_lock` bit 1). Placed (a) when the roster leaves a single-altar map's altar,
  (b) on the altar nearest to an enemy carrier with ≥ 30 gems when the body is within 2 of it and the carrier ≥ 4 away (its tribute
  is cancelled, five hits to clear; our roster takes the prime group meanwhile). IC places 2.6 a game, Mite 0: Mite has no counter-play.
- **Single-altar maps (15 of 70).** The altar is the second prime objective: the roster holds it between cycles; nobody starts a
  tribute with an enemy within 4 unless it is Marcella or the enemy is stunned; a bag > 60 waits for the roster rather than walking
  in alone (boss-battle: 344 + 255 gems lost at the altar).
- **Camps destroy carried gems.** A body with ≥ 20 gems does not front an elk/golem group; it banks first or stays at range.

**Fuel.** Threshold checks are arithmetic; the altar choice reads the MAPINTEL table.

**Tradeoff.** ~16 extra bank trips a game ≈ 90 body-rounds of walking; Mite pays it and still farms 1.6× our camp hits because it
does not spend 600 body-rounds dead and 1,000 walking near enemies.

**Metric.** Bank trips ≥ 24 a game, carry ≤ 30 rounds, gems lost on death ≤ 8 % of captured (21 %).

### 4.7 Economy

**Builds (by kit, not by name; Jungle first on every body):**

| kit | order | why |
|---|---|---|
| ranged carry (VV, Tavi, Stellar, Prism, Cassi) | Jungle(str, focus for casters) → Bruiser(str) → Bruiser(str) → Monster(str) → Capture(str) on the prime capturer only → Bruiser… | Jungle by ~r95 ends heal trips; Bruiser = 8 stat points for 150 gold; Monster +15 % on camps for the farmers. One Capture holder caps the whole team's timer (and keeps it capped after it leaves the region), so `g18_capture` 1, not 2: a Capture emblem on every body measured −41 today (150 gold × 5 for one effect) |
| dash melee (Vendetta, HoR) | Jungle(str / HoR: focus) → Bruiser(hp) → Bruiser(str / HoR: focus) → Bruiser(hp) → Durability(hp) | they dive: hp first (Mite 11.5 Bruiser hp a game); HoR's dash and shield scale with focus |
| Marcella | Jungle(focus) → Power(focus) → Power(focus) → Bruiser(hp) → Tribute(focus) on single-altar maps | 14 focus a shard, 2× focus spell: Mite's Marcella deals 181 a round to our 61 |
| Issac | Jungle(str) → Bruiser(hp) → Bruiser(str) | |
| Ryth (only on monolith maps) | Jungle(hp) → Bruiser(hp) → Bruiser(hp) → Durability(hp) | strength = 1 % of bonus health |

Extras by map feature: Treasure(str) as VV's 3rd emblem when the map's gold ≥ 2,500; Prospector on the prime capturer when
cluster gems ≥ 40 % of the map's gems (vault: 343 of 359); Home on nobody (2 rounds a recall is not worth 150 gold); Hunter,
Skirmish, Greed, Collectors never (late luxuries we will not reach before 1,000). Health bought **on spawn** heals the gained
amount (rules): a body shopping at spawn buys the hp shard first when hurt.

**Shop cadence.** A body goes to shop when `gold ≥ 90` and one of: hp < 50 %; spawn ≤ 12 steps; prime clock ≥ 25 rounds and it is
not in the next roster; `gold ≥ 180`. Tavi never walks home for shards (field buys at every 30 gold) and sells its Jungle at spawn
after r600 for a Bruiser. Dead bodies shop on every dead turn (already). Target 60–70 shop visits a game (39 today).
`cap_recall_gold` 250.

**Fuel.** The build lists are static tables; the shop decision is arithmetic.

**Tradeoff.** Fewer early farming-only emblems (Monster first) means the first 150 gold go to survivability; it pays because
heal trips and deaths cost more than the 15 % camp damage.

**Metric.** Gold earned ≥ 5,000 (2,600), shop visits ≥ 60 (39), shard-equivalents per body at r600 ≥ 24 (15).

### 4.8 Vision and wards

Rules used: ward vision 6, permanent, one per champion, placed within 2 on a legal tile (`ward_placement_tiles`), recharge 10 own
turn ends (`ward_cooldown`), a new ward replaces the old one; bushes block sight from outside, a body in a bush sees its whole bush
cluster; shadowcasting (`visible_tiles_from`, `ward::visible_tiles_from`); enemy wards are visible objects (`vision::wards(team::enemy)`,
`ward_tiles(team::enemy)`) and cannot be destroyed; `champion::is_alive()` works on unseen enemies; a visible enemy's cooldowns and
bag are readable; `camp_group::state()` (respawn timer) needs an original spawn tile in vision.

**Ward roles, in priority order per body:**
1. **Warden ward** (one body, §4.3.3): on P0's ward tile, never moved. Value: the team's clock.
2. **Approach ward**: for the group a FARM body is clearing, the bush tile within its placement reach (or the first bush on the
   enemy's BFS path from their spawn to the group, if within 2) that sees the most tiles of that path; re-placed when the body
   changes group and the cooldown is up. Value: a 4–6-round warning instead of a surprise at 4 tiles (today Mite initiates 75 %
   of fights; 18 % of IC's champion hits and 13 % of Mite's are made from inside a bush, 12 % of ours).
3. **Bank ward**: the altar a body banks at, if no ally ward is there (`has_ward(tile, team::ally)`), placed on the bush/tile that
   sees the altar's approaches.
4. Otherwise: the **bush tile** within placement reach that sees the most tiles on the enemy's side of my current group (ties: nearer
   the middle), and only if no bush is in reach the open tile with the most unseen tiles; corridor tiles excluded (a ward occupies
   its tile: allies cannot walk through it).

**Why not the v22 coverage scorer as written.** `g22_ward` 1 was measured today on the 70-map pool: it costs +4.8k fuel per turn on
average and +24k at p90 (31k → 36k mean, 54k → 78k p90; the `visible_tiles_from` host call on ~25 candidate tiles every placement
turn), and it puts only **16 %** of wards in bushes (v75's bush ward: 26–37 %), because a bush tile reveals fewer tiles than an
open one and the scorer counts tiles. The roles above are decided first; the tile count is only a tie-breaker among bush tiles.

**Placement cadence and fuel.** A body considers a placement only when `ward_cooldown() == 0` and ≥ 10 rounds since its last one,
and only with `fuel_remaining() > 45k` after the fight engine. Candidates ≤ 12 (bush tiles first, then the role tile, then ≤ 4 open
tiles). Each `visible_tiles_from` is a host shadowcast (~1.1k): ≤ 13k on a placement turn, ≤ 1 such turn per 10 rounds per body,
so the mean cost stays under 1.5k a turn. The warden's ward costs nothing after placement.

**Enemy wards.** Keep a per-owner map of seen enemy wards (`ward_enemy` 1: one active ward per enemy champion, so a new sighting
replaces the old). Uses: (a) a raid party and a lock run avoid their ward vision (the tile set `ward::visible_tiles_from(ward)` for
each known enemy ward, cached); (b) a bank with ≥ 30 gems prefers an altar outside enemy ward vision; (c) a carrier that must pass
a ward goes through a bush cluster (invisible inside it).

**Bushes.** FIGHT positioning prefers a bush tile adjacent to the target when one exists (enemies outside cannot see into it; their
ranged bodies need vision to attack); recalls are started inside a bush when one is within 2 (recall is cancelled by damage; an
unseen body is not attacked); the rally tiles of §4.3 are bushes when possible; a body with a bag > 30 walking home routes
through bush clusters when the detour is ≤ 2 steps.

**Death windows.** `is_alive()` on every enemy each turn costs ~80 per read: with ≥ 2 enemies dead (60-round respawn) the roster
`need` for P0 drops by 1 and the raid gate opens (§4.3.5). Mite's deaths are rare (3.1 a game), IC's are not (8.5, C&I in pairs).

**Tradeoff.** A warden ward does not follow its body; one of five wards is "spent" on information rather than on a farmer's
safety. The clock it provides is the single most valuable fact in the game (§4.3).

**Metric.** Wards in bushes ≥ 50 % (37 %); share of fights the enemy starts ≤ 55 % (75 %); respawn clock known (any body writes a
value ≠ unknown) ≥ 90 % of rounds after r100.

### 4.9 Messaging

- **Priority channel** (`set_priority`, read by allies with `query_priority(true)` when they see the body):
  `turn_class·4096 + hp_bucket·256 + state·64 + target·4 + flags`: `turn_class` keeps the fighter ordering (stunner before
  damage before capturer before the rest; a LEAVE body first); `hp_bucket` = hp/max in 16ths; `state` ∈ {FARM, PRIME, FIGHT, LEAVE,
  BANK}; `target` = the fight target's champion index; `flags` = {committed, carrying ≥ 20, warden}. One write per turn; reads
  only for visible allies (≤ 5 host calls).
- **Shared memory** (8 bytes): claims (bits 0–6 of bytes 0–5), prime clock + `enemy_holds` (bit 7 of bytes 0–5), alert (bytes 6–7:
  DANGER, RALLY; OPPORTUNITY removed). RALLY is posted by a FIGHT body with R < 1.0 and answered only through §4.5.6 (within 8),
  never by a lone walk across the map (`rally_r` 9 → 8, `respond_to_alert` reduced to this).
- **Draft memory**: §4.1 PRIME block.

**Fuel.** +0.5k per turn. **Tradeoff.** None measurable; the 8-byte limit is the engine's.

### 4.10 Movement

- A `move()`/dash that returns `false` (hidden occupant) is retried on the next-best tile in the same turn (`next_moves_from`,
  `move_absolute`); the blocked tile is remembered for the round. Today the failed step is retried on the same route next turn.
- Ranged bodies: in-range target → no move this turn (the executor must know the attack consumed the move allowance).
- Dash use: a dash kit saves its dash for the fight engine while an enemy is within 10 (`strike_dash_hold`), else uses it to
  cross holes and to close the last 2 tiles to a camp; never to walk toward a non-KILL enemy.
- Waiting states (rally, staging, escort) carry a deadline and are exempt from `unstick`/`stall_guard`; everything else keeps the
  v18 hygiene (`stall_guard`, `unstick_rounds`, `g18_osc`, `pocket_fix`, `dash_holes`, crystal hops on island maps).
- Opening path from the PRIME block (12 steps per body) so turn 1 walks without a field; after it the fields exist.

### 4.11 Special maps (features, not names)

| feature | detection (draft) | plan |
|---|---|---|
| single rich objective (`rich_share ≥ 0.5`) | one group holds ≥ half the gems | P = {it}; §4.3.2 opening; the ring plan (`o2_ring`) is the clearing method; if the enemy holds it with ≥ 3, farm gold groups **as a team** and shop until R ≥ 1.15 at its rally, then take it at a respawn with everyone (Mite on stampede: 600 rounds of gold, then every cycle) |
| lone monoliths only, no other gems | `mono` and gem groups = monoliths | the game is gold and kills (tiebreak: gems, then lifetime gold, then kills, then team B): farm gold groups in two pairs with approach wards; a monolith (20,000 hp, 200 dmg at range 5, 200 gems + 300 gold) only with 5 bodies at full hp, Jungle on everyone, Ryth's and Tavi's stuns rotated (a stunned camp skips its attack), and no enemy seen within 15 for 20 rounds; the capture needs the tile occupied uncontested, so the team holds it; never enter the middle one by one (contest: 56 deaths, 0–0, lost on gold) |
| single altar | `altars == 1` | §4.6: the altar is a prime objective; locks; Marcella banks; Tribute emblem on her |
| altar adjacent to P0 (`rich_altar_d ≤ 6`) | | capture → tribute in the same visit; the roster escorts |
| large maps (≥ 80×80) or ≥ 40 groups | | P0 roster 3 not 5; the rest farm the own half continuously; bank at the field altar nearest to the farm; far-group scoring capped at the 16 contested groups + own-half groups within 25 steps (fuel: vault/road-of-riches/islands lose 30–200 turns a game today) |
| 3-champion maps | | P capped at 2; opening always together; no raids; C&I never |
| islands (crystal maps) | `hops_enabled` | crystals bought at the first spawn visit by the two bodies whose first targets are behind holes; recall out to bank (`mi_island_bank`) |

### 4.12 Opponent profile (observed in-game, never a team name)

The bot cannot know who it plays, but six observable signatures change the best play, each read from the API during the game and
kept as flags:

| signature (observable) | what it means (from the replays) | adaptation |
|---|---|---|
| the enemy drafted Cassi & Issac | IC 57/70, Mite on 4-champion maps; the pair dies together: one kill = two bodies, two bags, 120 rounds of farming lost; in our 8 wins vs IC the pair died 5 times a game | targeting: Cassi/Issac +200 (§4.5.4); a FIGHT on the pair is worth starting at R ≥ 1.0 instead of 1.15; the pair is the raid-target kill of choice when seen alone |
| an enemy body recalls on consecutive rounds at different tiles (`g17_fakerec`) | Mite/TK bait; it never pays and it means recalls carry no information | recalling enemies are never targets or alerts; nothing changes in our play |
| the enemy never recalls (no recall seen by r300) and its hurt bodies walk home | IC (43 recalls a game): a body below 30 % walking toward its spawn is a KILL for a dash kit if we are between it and the spawn | a hurt enemy walking home is a KILL candidate when a dash kit of ours reaches it before its spawn tiles (it never heals on the way); its spawn tiles themselves are never entered |
| enemy altar locks seen (IC 2.6 a game) | our tributes get cancelled at contested altars | carry a lock ourselves (already), bank at the altar outside enemy ward vision, clear a lock only when ≥ 2 of us are there (5 hits) |
| enemy wards seen in bushes on our side (IC 22 %) | they watch our farm groups | §4.8 enemy-ward map: raids and bank trips route outside their vision; our approach ward goes one bush farther out |
| enemy bodies carrying ≥ 20 gems near an altar (Mite's bag at death 23, ≥ 20 in 29 %) | a lock raid (§4.6) or a KILL pays a full bag | the carrier bonus in targeting; the lock rule |

### 4.13 Endgame and tiebreaks

- From r1700, or when either team's bank ≥ 850: every bag ≥ 10 banks at the nearest altar; the roster holds P0 only if a capture
  completes before the projected finish; locks go on the enemy's nearest altar when their bag + bank ≥ 980.
- Round-limit games (2/65): the order is gems, lifetime gold (not unspent), kills, then team B. When gems are tied (0–0 maps), gold
  groups outrank everything and kills are worth 100 gold each: fight only KILL states.
- The first mover alternates each round and a tribute completes at the next own turn start: when both teams can reach 1,000 in the
  same round, the body that starts the tribute one round earlier wins; §4.6's final-tribute rule.

---

## 5. Fuel: budget and rules

**Measured today (v75, 130 Mite games, the engine's fuel stream):** draft turn 1 uses 0.58 M of 10 M (max 1.12 M); draft turns
2–5 use 62k of 100k (max 90k); the first game turn uses 180k of 200k (max = the limit: 146 bodies lost their first turn in 65 games);
later game turns: mean 31.5k, median 31k, p90 55k, p99 79k, max 100k. Lost turns: 5.1 a game (3.0 in rounds 1–3), concentrated
on vault (88 in one game), fracture, the-pack, islands, shortcut, yellow-brick-road: many-group maps where group scoring exceeds
the budget. Mite loses 25 a game and still wins: fuel is not what beats us, but every module below must keep p99 under 100k.

**Budget per game turn (100k):**

| step | today | allowance | guard |
|---|---|---|---|
| perceive + shared memory + priorities | ~8k | 9k | — |
| team plan (§4.3) | — | 3k | — |
| fight engine (§4.5) | ~6k (combat) | 8k | `damage_amount` only for ready spells and enemies within reach + 2 |
| farming scorer (`group_score`) | 10–60k | ≤ 35k | `score_near_floor` 38k, `score_far_floor` 55k kept; on ≥ 40-group maps candidates = contested 16 + own-half within 25 steps |
| executor (step, attack, casts) | ~5k | 6k | — |
| ward placement (§4.8) | ~2k | 13k on ≤ 1 turn in 10 | only with `fuel_remaining() > 45k` after the fight engine |
| bookkeeping, writes | ~3k | 3k | — |
| **total** | 31k mean / 79k p99 | **≤ 70k typical, ≤ 95k worst** | every loop over groups/tiles checks `fuel_remaining()` inside the loop |

**Draft turn 1 (10 M):** everything static goes here: BFS fields from both spawns, group values and zones, the prime set with its
rally/ward/altar tiles (each needs ≤ 50 `visible_tiles_from` calls ≈ 55k), the opening schedule, the 12-step opening paths. Budget
≤ 2 M; today's draft uses 0.6 M. **Rule:** never `printf` in the draft (90 fuel a byte; a verbose dump once ran the draft out of
fuel and the engine picked randomly).

**First game turn (200k):** no new work (it is at the limit today: on every map of ≥ 1,200 tiles or ≥ 40 camps all five bodies
use the full 200k and lose their first turn; on 30×30 maps none do). The opening path in the PRIME block (§4.1) is what removes
that loss: turn 1 then needs the spawn field only (≤ 19k) and the body walks its first 12 steps from the stored path while the
fields are built on turns 2–4 (one per turn, 13–19k each); islands stay deferred (`defer_islands`). Target: 0 lost turns in
rounds 1–3 (3.0 a game today).

**Known costs to design around** (from `ENGINE_FACTS` / `MAPAnalysis`): `distance_field::compute` 13–19k on 100×100;
`map::camp_groups()` 25k (cache once); `vision::camp_groups()` 36k (never per turn; read raw states per group); `champions(team)`
22k (never per turn; keep handles); a host bitboard op up to 2.5k on 100×100 (keep bitboards static, zero them with the engine
only when needed); a zero-initialised vector ~1.2 fuel a byte (static buffers); a wasm loop step 100–175 fuel (a 144-tile loop
with reads ≈ 25k); `printf` 90 a byte; a shadow-stack overflow corrupts static data silently (keep per-turn stack use small).

**Rollover policy:** a turn that runs out of fuel finishes next round and the body loses that round; on the three heavy maps the
scorer's candidate cap above is what removes the 30–200 lost turns; the fight engine and the executor must never be the part
that is cut, so they run before the scorer and the ward step.

---

## 6. Rules checklist: everything the rules give us, and where the method uses it

| rule | used in |
|---|---|
| melee move + attack in one turn; ranged move **or** attack; attack reset = second attack; one cast per turn across both slots | §4.5.4, §4.4.2 |
| dash 2 steps over holes; teleport crystal 3 tiles through terrain after a 3-turn channel | §4.10, §4.11 islands |
| camps attack the nearest champion in range (wolf 3, elk/golem 4, monolith 5), see 8 through bushes, never heal, sleep after 2 rounds without a target in range, stunned camps skip an attack | §4.4.3, §4.4.5, §4.4.7, §4.11 monoliths |
| capture: one body suffices, extra allies do not speed it, the Capture emblem caps the timer at 3, an enemy on the region resets it, an occupied spawn tile delays the respawn | §4.3 capturer and §4.3.6 capture pressure, §4.7; never wait *on* a spawn tile |
| tribute: ceil(bag/10) turn ends, start on the move, damage does not cancel, stun/death/new lock do, completes at the next own turn start, altar lock = 10 gold, 5 hits to clear, cancels channels | §4.6, §4.13 |
| recall 5 turn ends (3 with Home), any damage cancels, arrives at turn start, spawn heals fully every round, buying health on spawn heals the gain | §4.5.3 spawn fight, §4.7, §4.8 bush recalls |
| death: killer gets the bag + 100 gold; camp kills destroy the bag; 60 rounds; dead bodies shop | §4.5.8, §4.6 camps, §4.7 |
| vision 8 shadowcast, bushes block from outside, inside a bush you see the cluster; wards vision 6, permanent, one each, placed within 2, recharge 10; enemy wards visible; `is_alive()` on unseen enemies; visible enemies' cooldowns and bags readable; respawn timer readable with a spawn tile in vision | §4.8, §4.3.3 |
| shared memory 8 bytes, draft memory 1,024 bytes (read-only in game), `set_priority` readable by allies who see you, priority orders the next round's turns | §4.9, §4.1 |
| Marcella: stun-immune, +2 gold per gem tributed; Tavi: field shards, sells at spawn; Vendetta: kills reset cooldowns (camp kills too); HoR: +50 % damage near zero hp, dash stuns; Prism: +1.5 focus per carried gem; Ryth: strength from bonus health; Varg: splash; Ren: retaliation; C&I: die together | §4.1, §4.5, §4.7 |
| emblems: Jungle −30 % camp damage, Bruiser 5+1+1, Power 6, Monster +15 % camp damage, Capture, Tribute, Prospector +25 % clusters, Treasure +10 % gold (+43 % with VV) | §4.7 |
| hidden occupants return `false` and keep the move allowance | §4.10 |
| win: 1,000 gems, else gems, lifetime gold, kills, team B; first mover alternates each round | §4.13 |
| fuel: 100k a turn, 200k first game turn, 10 M first draft turn, rollover = lost round | §5 |

---

## 7. Evaluation and acceptance

**Local (every build, 70-map pool, both sides, vs the live bot as the null check):** 0 faults; lost turns ≤ v75's (5 a game,
≤ 1 after round 3 outside the three heavy maps); margin not below −100 (the self-play opponent kites and baits; a candidate that
farms through contact may lose a little to it and that is acceptable). Then the behaviour metrics from the kept replays with
`analysis/` (the loss study's scripts), with Mite's numbers as targets:

| metric | v75 today | target |
|---|---|---|
| richest-group captures a game | 0.3 | ≥ 3 |
| middle gem groups, captures per group | 0.7 | ≥ 3 |
| first camp hit − walk | +15 rounds | ≤ +4 |
| opening arrival spread (median) | 13 | ≤ 4 |
| camp-hit share of body-rounds | 12.5 % | ≥ 18 % |
| camp-hit rate with an enemy within 8 | 6.3 % | ≥ 14 % |
| walking with an enemy within 8 | 20.8 % | ≤ 15 % |
| deaths a game | 10 | ≤ 5 |
| deaths after 2+ approach steps | 70 % | ≤ 30 % |
| moves in the 12 rounds after being hit first | 70 % | ≤ 50 % |
| hits landed in the 10 rounds after being attacked / theirs | 3.8 / 7.0 | ≥ 6 / ≤ 6 |
| bank trips / carry rounds | 12 / 43 | ≥ 24 / ≤ 30 |
| shop visits / gold earned | 39 / 2,600 | ≥ 60 / ≥ 5,000 |
| wards in bushes | 37 % | ≥ 50 % |
| lost turns a game (fuel) | 5.1 | ≤ 5 |

**Ladder (the only ship gate):** `tools/paired_groups.py` — 14 unranked groups each against IC and Mite on the same 70 maps and
sides as the v75 baseline (the 130 uploaded games are that baseline for Mite); a version ships when it wins more of the paired
maps than v75 and the metrics above hold on those replays. The user uploads; nothing is submitted from here.

**Order of work (each step gated by its metrics):**
1. Step 0 (Appendix B: the five configuration values that are level on both pools) + the full §4.6 banking rule + §4.7 builds and shop cadence — one day; the rest of the §2.4 ledger goes in with the module it belongs to (Appendix B).
2. §4.5 fight engine — replace `combat()`; two to three days; the largest change; gate: deaths ≤ 6, approach-step deaths ≤ 35 %.
3. §4.4 farming executor and the OPPORTUNITY removal — one day; gate: camp-hit near enemies ≥ 12 %.
4. §4.3 TOL with the PRIME block, the warden and the clock — two days; gate: richest-group captures ≥ 2.
5. §4.8 wards, §4.9 messages, §4.10 movement retries — one day.
6. §4.1 roster rules and §4.11 special maps — half a day.
7. Fuel pass (§5): candidate caps on heavy maps, the per-turn floors, a `FUEL_TRACE` run on vault/fracture/islands.

---

## 8. Tradeoff register (what we deliberately do not do, and why)

| not done | why not |
|---|---|
| a permanent pack / deathball | −10 % unopposed pace (v20), −141 to −222 (deathball_until); the TOL synchronises one place per cycle instead |
| never flee | `_pf` 32/140, −339, deaths 18 vs 8: without the escape test and the gates it is suicide |
| chase retreating enemies / answer OPPORTUNITY across the map | 70 % of our deaths; Mite's bait feeds it |
| the recall bait | no measurable effect in 130 games; 2 host calls a turn; a failed cancel leaves a body channelling |
| per-map tables (pick prior, pack maps) | the pool changes weekly; a table helps only where it was selected (doc 25: +185 old maps, −85 new) |
| Treasure/Monster-first economy builds | they pay after fights we lose; Jungle + Bruiser pays during them |
| Home, Hunter, Skirmish, Greed, Collectors | not reached before 1,000, or < 150 gold of value a game at our kill counts |
| soloing the richest group | 26 attempts a game-set, 2.1 bodies, 130 rounds, 11 captures |
| fighting at R 1.0–1.15 | coin flips cost farming time twice (the fight and the respawn) |
| local self-play as the ship gate | §2.2 |

---

## Appendix A. Today's local runs (70-map pool, both sides, 140 games each, release build, vs the live v75)

Margin = banked gems a game, variant minus v75, bootstrap 95 %. Noise floor ≈ ±50 (doc 28's null control). Fuel of every variant was
read from the bundles' fuel streams: identical to v75 (mean 31k, p99 79k, 6 lost turns a game) except `_ward` (see below). 0 faults
in 2,266 games.

| variant | wins | margin | deaths (variant – v75) | note |
|---|---|---|---|---|
| `_bank` (`tribute_min` 30, `early_tribute_min` 15) | 74/140 | +58 [−36, +153] | 10.4 – 11.0 | the best single; bank trips 30.7 vs 27.9 a game in a sample, carry 39.5 vs 43.7: the threshold alone does not shorten trips much — §4.6's altar choice does |
| `_wait` (`max_wait` 40, `g18_rich` 1) | 76/140 | +19 [−77, +117] | 10.3 – 10.7 | |
| `_defend` (`ally_defend` 1) | 74/140 | +22 [−74, +124] | 10.6 – 10.4 | |
| `_cap1` (`g18_capture` 1, one holder) | 66/140 | +5 [−89, +105] | 10.6 – 10.9 | free |
| `_cap` (`g18_capture` 2, every body) | 63/140 | −41 [−137, +55] | 11.7 – 10.2 | 750 gold for one effect |
| `_ward` (`g22_ward` 1) | 73/140 | −31 [−122, +63] | 12.2 – 10.8 | **fuel +4.8k mean, p90 54k → 78k, p99 85k; 16 % of wards in bushes** (v75 26–37 %) |
| `_nobait` (`g17_bait` 0) | 66/140 | −39 [−135, +59] | 11.9 – 10.5 | our own brain chases baits, Mite's does not (0 effect in 130 games); keep off on the ladder, expect −40 in self-play |
| `_tavi` (Tavi wherever the draft plans Ryth) | 68/140 | −22 [−114, +71] | 10.3 – 10.7 | champion damage done 37.1k vs 32.9k, kills 9.9 vs 9.2: level in self-play, the right direction for fights |
| `_combo3` (`_bank` + `_wait` + `_defend`) | 71/140 | +33 [−69, +134] | 10.0 – 11.0 | gold 6,227 vs 5,936 |
| `_combo1` (`_combo3` + `_nobait` + `g18_capture` 1 + `cap_recall_gold` 250 + `mi_pick` 0) | 61/140 | −87 [−183, +10] | 12.3 – 8.8 | the bait and the recall cut cost deaths against our own kiting bot |
| `_fight1` (`outmatch_flee` 0, `ml2_flee` 0.5, `fight_back_margin` 1.0, `isolated_flee_adv` 1.2, `ml2_leave` 0.3) | 68/140 | −101 [−192, −3] | 13.6 – 10.2 | "flee less" by parameters loses to kiting: the engine must change, not the margins (§4.5) |
| `_combo2` (`_combo1` + `_fight1` + `_tavi`) | 58/140 | −129 [−236, −29] | 13.7 – 9.7 | everything by parameters: worse than its parts |
| `_step0` (`_combo3` + `g18_capture` 1 + `_tavi`) | 54/140 | −102 [−189, −10] | 11.7 – 10.3 | held-out var17: 36/102, −165 [−261, −68], deaths 11.4 – 8.5: Tavi on the v75 brain loses |
| `_combo3` on held-out var17 (51 maps) | 48/102 | −22 [−126, +87] | 10.5 – 9.7 | level on both pools |
| `_step0b` (`_combo3` + `g18_capture` 1) | 70/140 | +12 [−89, +115] | 10.6 – 10.7 | held-out var17: 42/102, −82 [−182, +14], deaths 11.1 – 9.0: the early 150 gold is not free on the v75 brain; the Capture holder ships with the TOL, where the capturer role and the cycles exist |

What the runs establish for the plan: (1) the farming/banking/waiting switches are safe to turn on now (Step 0 below); (2) fighting
more by parameters is not — the fight engine of §4.5 is a replacement, and it is gated on deaths; (3) the Capture emblem is one
holder, not five; (4) the v22 coverage ward costs fuel and puts wards in the open: §4.8's roles are the design; (5) the recall bait
is a self-play artefact.

## Appendix B. Step 0: the configuration-only build to upload first

**`bots/gpta75` + `tribute_min` 30, `early_tribute_min` 15, `max_wait` 40, `g18_rich` 1, `ally_defend` 1** (= `_combo3`: s3 71/140,
+33 [−69, +134]; held-out var17 48/102, −22 [−126, +87]: level on both pools, 0 faults, fuel unchanged). It changes no fight
logic and costs no fuel; its only purpose is to be the first paired-ladder data point against IC and Mite while §4.5 is built.
Expect it to be level with v75 against them, not to beat them. Build it as `bots/god23s0` from `gpta75` with those five values
(`tools/mkvariant.py god23s0 --src bots/gpta75 tribute_min=30 early_tribute_min=15 max_wait=40 g18_rich=1 ally_defend=1`),
null-check it (`abbench` vs `gpta75`: 140 games, 0 faults, lost turns ≤ 6 a game), zip it under `submissions/`.

**Not in Step 0:** Tavi for Ryth, the Capture holder, the recall-bait removal, `cap_recall_gold` 250 and `mi_pick` 0. Each of
them is right for the bot of §4 and wrong for the brain of v75: `_step0` (`_combo3` + Capture holder + Tavi) lost 54/140,
−102 [−189, −10] on s3 and 36/102, −165 [−261, −68] on var17 with +1.4 / +2.9 deaths; `_step0b` (`_combo3` + Capture holder)
+12 on s3 but −82 on var17; `_combo1` (bait off, recall cut, prior off) −87. They ship with the module that gives them their
value (§4.1 with §4.5; §4.7 with §4.3; §2.4's ledger with §4.5/§4.4).
