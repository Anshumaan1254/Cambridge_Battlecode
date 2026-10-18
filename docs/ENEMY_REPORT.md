# HouseOfCoders: enemy strategy analysis and counter-strategy brief for Claude Opus

Prepared 18 October 2026 (Asia/Calcutta). Analysis only: no bot source, parameters, submission, or Git history was changed.

## 1. What Claude should take from this report

**The opponents win by completing productive farming cycles while HouseOfCoders loses farming time, concentrates too little income on useful champions, and repeatedly loses the linked pair. There are three observable enemy styles, and they require different responses.**

1. **Ren-first pressure/economy profile:** 13 games, 13 enemy wins. Develop durable frontliners and damage carries, repeatedly harvest camps, exploit vulnerable champions, then collect and bank with little downtime. Most of its camp income still comes from its own side; this is not simply an all-in invasion bot.
2. **Cassi & Issac-first farming profile:** wins `rows` and `expanse` with **zero deaths on either team**. Monster emblems, specialized farming roles, concentrated income, and repeated productive routes beat us without needing combat.
3. **Stellar/Tavi/Prism objective profile:** dominates `contest` by building gold and combat strength before harvesting monoliths. However, it loses `stampede` **0–1080** when we secure the compulsory scoring objective. Its combat/economy strength is not an automatic answer to every objective map.

Do not respond by making every champion more aggressive, permanently grouping the whole team, or copying an enemy draft and declaring the opponent reproduced. Prioritize a reliable opening economy, linked-pair survival, productive camp allocation, and map-specific scoring plans. Test targeted changes against independent opponent implementations and fresh real matches.

**No report can guarantee a win.** The sequences below are observed; proposed counters are hypotheses to validate. The enemy source code is not present, so exact scoring weights, hidden state machines, and intentional coordination cannot be recovered from these replays alone.

## 2. Evidence, identity, and version control

### Dataset

- Four supplied match-group ZIPs contain 20 match archives, but only **17 distinct replay byte streams**. Three games occur twice under different match IDs. Deduplicate them before calculating performance.
- The 17 distinct games cover **all 17 maps in the local official map directory**, once each. Maps were matched using dimensions, camp types/coordinates, and terrain against `Cambridge_Battlecode/maps/comp`.
- This report treats **Team A as HouseOfCoders**: every archive contains only `team-a` private logs, Team A consistently uses the repository's draft family, and the user identified their team as HouseOfCoders. This is strong evidence, but the archives do not include an authenticated team-name/submission-ID mapping.
- Opponent names are unavailable. The three profiles below are behavioral/draft groupings, **not verified team identities**. A match group must not be assumed to contain one opponent: some supplied groups contain multiple profiles.
- All 17 games were decoded with the official `v0_0_3-zaIi77qe.wasm` replay engine distributed inside the `cambc 2.2.5` package. No new matches were played.
- Both teams' gem and gold ledgers balance in every distinct replay; reconstructed deposits equal the replay's final scores.

### Which bot was inspected?

- Repository HEAD: `5f63085`.
- Current submission archive: `Cambridge_Battlecode/submissions/legend.zip` (`legend_st`).
- SHA-256: `8129b632868d159f77fd4eccfcc6596d4630d54145a616637ecce13491424777`.
- After line-ending normalization, 13 of its 15 source files match `bots/legend/src`. Differences are in `brain.cpp` and `params.h`: added `cast_route_*` checks/parameters, with the controlling settings zero. They are strategically disabled, although extra code can still affect fuel and deterministic timing.
- **The replay archives do not prove the exact uploaded source hash.** Treat source defects as confirmed properties of this inspected baseline, and replay sequences as confirmed match behavior. Connecting a particular decision to a particular source branch remains an inference until the submission ID is matched.
- `AGENTS.md` describes session-4 fuel, capture-reset, tribute-elapsed, and danger-detour work, but those fixes are **absent from the inspected source**. Historical prose is not proof a change exists.
- `docs/LADDER_AUDIT.md` concerns an older build and 40 other games. Its statistics are not included in this report's totals.

### Evidence labels used below

**Observed** means a decoded replay action/state or directly inspected source. **Inference** means a plausible explanation consistent with those observations. **Proposed counter** means an untested change, not a measured improvement.

## 3. What the new games actually show

| Metric, 17 distinct games | HouseOfCoders | Opponents |
|---|---:|---:|
| Wins | 1 | 16 |
| Camp gems awarded | 7,938 | 16,210 |
| Gems banked | 6,572 | 16,478 |
| Gems gained from champion deaths | 514 | 1,328 |
| Carried gems lost on death | 1,350 | 554 |
| Gems still carried at game end | 530 | 506 |
| Body deaths | 232 | 50 |
| Recorded body-rounds dead | 25.1% | 5.4% |
| Credited champion kills | 30 | 167 |
| Gold gained | 39,622 | 86,962 |
| Gold spent | 38,170 | 80,860 |
| Recall starts | 340 | 509 |
| Ability casts | 3,804 | 5,253 |
| Fuel rollover events | 84 | 0 |
| Bot error events | 0 | 0 |

Deaths count bodies: one Cassi/Issac incident usually kills two bodies but awards one credited kill. Do not compare body deaths with kill credits as if they were interchangeable.

The banked-score deficit is exactly explainable by the gem ledger:

`9,906 = 8,272 fewer camp gems + 814 fewer stolen gems + 796 more gems lost on death + 24 more gems left unbanked`.

The camp-income term is **83.5% of the net score gap**. This is an accounting decomposition, not proof camp selection alone caused the losses: deaths, fighting, routes, and upgrades all affect camp income. It does show why only adjusting banking thresholds cannot solve the whole problem.

HouseOfCoders spends **96.3%** of its gained gold. The broad problem is not “the bot never shops.” It earns too little, and sometimes spends on a build or champion that does not turn that investment into enough score.

## 4. Enemy profile A: Ren-first pressure backed by farming

### Observed composition and outcomes

The enemy selects `Ren → Stellar → Cassi & Issac`, then `Ryth`, then `Varg` when slots permit. This occurs on 13 maps. Our five-pick order instead puts Varg before Ryth; on four-pick maps this changes the actual roster.

Across these 13 games:

| Metric | HouseOfCoders | Ren-first enemy |
|---|---:|---:|
| Wins | 0 | 13 |
| Camp gems | 5,102 | 12,872 |
| Banked gems | 3,890 | 13,406 |
| Body deaths | 159 | 37 |
| Gold gained | 23,779 | 58,655 |
| Recall starts | 224 | 365 |

### A1. It funds a durable frontline and scaling damage

**Observed item pattern:**

| Enemy champion | Repeated observed build pattern |
|---|---|
| Ren | Bruiser Health and Durability Health, then repeated Power Focus |
| Ryth | Bruiser Health / Durability Health, then Power Strength |
| Issac | Power Strength, Durability Health, then more Power Strength |
| Varg | Power Strength and Durability Health, then more Strength |
| Stellar | Power Focus plus Durability Health, then further Focus |
| Cassi | Bruiser Health and Durability Focus where income permits |

These are patterns across inspected inventories, not a claim that every item is bought in that exact order in every game. Purchases can complete several emblems on one visit.

**Concrete `fragment` sequence:**

1. Enemy Ren captures 22 gems at `(27,18)` on round 19.
2. Ren captures a 58-gem, 250-gold group at `(17,13)` on round 47.
3. Ren starts recall on round 51 and shops on round 56.
4. By round 56, Ren has both Bruiser Health and Durability Health. At round 100 its maximum HP is **1,900**, versus its 900 starting HP, and it also has four Power Focus shards.
5. Our linked pair dies on round 65; Stellar dies on round 88. The enemy loses no bodies throughout the game.
6. Enemy Ren subsequently harvests the same valuable regions repeatedly, including the opposite-side group around `(12,15)`.

**Inference:** early health is enabling repeated productive combat and safe farming, while Focus later converts Ren's spells and retaliation into pressure. It is a reinforced farming loop: income buys staying power; staying power preserves more income. Merely matching a damage-per-gold spreadsheet misses that survival benefit.

**Proposed counter:** track visible enemy item/HP power spikes and avoid taking the same fight before and after their shopping trip. Protect the first safe camps needed for our own useful upgrade. Test role-specific survivability, particularly a frontline that can hold a camp while damage dealers operate. Do not turn on health-first for every champion: the repository records a broad health-first experiment that lost locally.

### A2. It exploits the weak member of Cassi & Issac

**Observed across all games:** our Cassi and Issac each die **59 times**, versus 15 each for the enemy. Our pair spends roughly **34%** of its recorded body-rounds dead. The pair accounts for **118 of our 232 body deaths** and loses 516 carried gems across its two members.

Examples:

- **`fragment`, round 65:** at the end of round 64, our Cassi is at `(14,9)` with **945 HP and 22 gems**; Issac is at `(15,18)` with **18 HP**. Enemy Cassi causes the linked deaths. A healthy farmer carrying income is removed because the other body is exposed.
- **`eight`, round 32:** Cassi has 620 HP at the preceding round snapshot, while Issac has 215 HP near several enemies. Enemy Stellar causes both deaths. By round 50 we have lost five bodies, including two deaths to camps during the collapse.
- **`interlock`, round 82:** our Cassi has 7 HP at the preceding snapshot while Issac has **1,165 HP**. Enemy Ryth causes both deaths.

These observations establish the repeated vulnerability. They do not prove an explicit “always target the linked pair” rule in the enemy's code.

**Proposed counter:** value an engagement using the risk to **both bodies and both bags**. Share a compact partner-danger/banking status; make stale information conservative. The endangered partner should disengage before the healthy partner's local combat calculation becomes relevant. Let safe independent farming continue—permanent pair grouping would throw away much of the reason to draft them.

When attacking their pair, target the member whose **reachable lethal sequence** is cheapest. Do not chase Cassi through several enemies merely because a fixed target bonus says a double kill is valuable.

### A3. Its economy is mostly home-side, with selective expansion

Using static walking distance from the two spawns to classify capture tiles, with a three-step neutral band, this profile collects approximately:

- **9,658 gems (75.0%) on its own side**;
- **2,364 (18.4%) in the central/equidistant band**;
- **850 (6.6%) on our side**.

This classification ignores dash shortcuts and moving threats; it describes geography, not ownership or tactical safety. The whole `swirl` scoring corridor falls in the neutral band.

**Implication:** sacrificing our economy to hunt their backline everywhere is a poor default counter. Their main engine is reliable local production. They can beat us while stealing only a modest fraction of camps directly.

**Observed expansion:** on `fragment`, the enemy collects **312 of 924 camp gems** on our side under this classifier and never dies. On `eight`, it collects **292 of 1,108** on our side. This is consistent with expansion after local superiority; it is not proof of a coded invasion phase.

**Proposed counter:** secure our reachable resource cycle first, contest the few choke points that decide access, and trade camps when an invasion is too expensive to repel. Require arriving combat strength before accepting an enemy-half task. Do not count a distant farming claim as immediate reinforcement.

### A4. It repeatedly returns to productive camps

**`pilgrimage` is a particularly clear comparison.** Our team captures the same 68-gem group on rounds **85, 227, 328, 444, 554** and captures no other gem group. We end with 340 gems banked and no carried gems. Our Ren and Ryth collect zero gems; Ren remains alive throughout, so deaths cannot explain its complete lack of production.

The enemy first captures its corresponding 68-gem group on round **52**, revisits on **122, 194, 279, 351, 418, 480, 566, 638**, and adds higher-value groups paying 92 and 144 gems. Enemy Ren collects **388 gems**, versus our Ren's zero. Final score: **340–1032**, with only **3–2 body deaths**.

**Inference:** the enemy has substantially more productive routing/target persistence and an expansion path after the first resource cycle. Our Ren wanders over widely separated coordinates across the game without acquiring gold or gems. Calling this simply “needs to recall more” would miss the failure to finish a task.

**Proposed counter:** measure progress toward completed capture, not merely movement or distance traveled. Preserve a profitable route unless new information changes feasibility or value. Add a watchdog for long periods alive without earning, clearing, or contributing useful combat; the existing 3×3 stuck detector does not catch long wandering loops.

### A5. It can overturn an early scoring lead

On `corners`, we lead **320–80 at round 200**. The enemy passes us by round 250 (**320–436**), before our first body death at round 260. Then Stellar dies at 260, the pair at 263, Varg at 266, and Ryth at 273. We never score again and lose **320–1018**.

**Implication:** “we were ahead, then died” is incomplete. Enemy farming already overtook us before the death sequence. A safer lead mode must preserve production as well as avoid catastrophic combat.

**Proposed counter:** estimate both teams' recent scoring and collection rates. Do not become passive merely because the current banked score is ahead. Reassign idle champions to safe work and protect carriers with actual reachable support.

## 5. Enemy profile B: specialized farming, not fighting

### Observed composition

- `expanse`: `Cassi & Issac → Stellar → Varg`.
- `rows`: the same first three selections, then `Ren`.

Across these two games, **neither side suffers a single death**. The enemy collects **2,138 camp gems** against our 1,756 and gains **9,440 gold** against our 7,520. All of its gem collection is on its own side under the static-distance classifier.

This is strong evidence of a farming/upgrade/routing advantage, not evidence that we need more defensive combat thresholds on these maps.

### B1. Its item policy is specialized for low-contact farming

All inspected final builds in these two games follow **Monster in the relevant damage stat, then repeated Power in that stat**:

- Issac and Varg: Strength.
- Cassi, Stellar, and Ren: Focus.

The enemy finishes without health emblems in these games. That works here because there are no deaths; it is not a universal build recommendation.

**Why this can outperform our Bruiser-heavy general build:** Bruiser gives more total stat points, but those points are spread across stats. Power gives six points in the chosen stat. A no-contact farmer may benefit more from faster clears in its productive stat than from two off-stat points. Monster's passive boosts camp damage once; subsequent Power emblems scale the relevant stat. Duplicate passives do not stack, while item stats do.

**Proposed counter:** use map/contact-aware economic builds. Compare completed scoring rate, not total stat points. Test a farming specialization only where safe resource access makes it appropriate, and switch or prepare defense when credible contact approaches.

### B2. Varg and Issac carry the economy; every body does not receive equal income

On `expanse`:

| Champion | Our camp gems | Enemy camp gems |
|---|---:|---:|
| Cassi | 110 | 66 |
| Issac | 88 | 408 |
| Stellar | 332 | 190 |
| Ren | 368 | Not drafted |
| Varg | Not drafted | 352 |

Enemy Issac + Varg collect **760 of 1,016 camp gems**, about 75%. Enemy Cassi's low personal collection is compatible with a winning team economy; do not require equal output from every champion. The replay establishes the asymmetry but cannot prove whether it comes from deliberate collector roles or local decisions.

**Proposed counter:** assign the right champions to the right groups. Prioritize Varg for pack-clearing opportunities and give Issac safe productive work instead of repeated hazardous excursions. A helper should contribute when it shortens a clear sufficiently; it need not occupy the reward region and split the gold afterward.

Test Varg-containing three-pick compositions on distributed/pack maps. Do not claim that replacing Ren alone fixes `expanse`: routing, item policy, and opponent implementation also differ.

### B3. `rows` exposes the income-allocation difference

Enemy Varg takes the 66-gem/270-gold group around `(31,45)` on round **27**, recalls that same round **after the capture**, and shops on round **32** for Monster Strength plus four Power Strength shards. Varg takes that group again at **85** and **139**. At round 100 it already owns Monster Strength, two Power Strength emblems, and three further Power Strength shards.

Enemy Ren takes its 66-gem group at **53, 124, 179, 228, 282**. The sequences are consistent with repeated farming circuits around respawn availability.

Our first two group captures arrive later and split rewards:

- Round **59**: Ren and Cassi each get **33 gems** from one group.
- Round **75**: Stellar and Varg each get **33 gems** from another group.

Our Varg ends with **66 camp gems**, versus **396** for enemy Varg. The enemy completes **17 group-equivalent 66-gem rewards**; we complete 13. Our 18 individual reward-award events must not be mistaken for 18 cleared groups, because several rewards are split.

**Proposed counter:** separate **clear helper**, **collector**, and **next assignment**. Estimate marginal help: does the second body save enough clear time to justify its lost alternative income? If not, send it to another group. Once the group is dead and safe, keep one intended collector; additional bodies do not accelerate capture.

A collector reservation should persist through capture. Do not make a helper chase another helper's newly stale claim or cause both bodies to abandon the reward.

### B4. Banking matters, but does not explain the whole race

- `rows`: lose **726–1056**, carrying **132** gems. Even instant banking would give 858, still short of both 1000 and the opponent's score. More production was necessary.
- `expanse`: lose **876–1016**, carrying **22**. Again, faster banking alone cannot close the deficit.
- The enemy wins these races despite generally starting recall **after** capture, while our bot often overlaps the two channels. Its larger advantages outweigh the few rounds that trick can save.

**Proposed counter:** optimize the complete cycle: approach → clear → capture → upgrade/heal when worthwhile → tribute → next useful task. Compare direct banking, recall, and continuing the circuit by expected completion time and risk. Preserve good overlap behavior when safe; do not assume it is the missing enemy trick.

## 6. Enemy profile C: caster economy into compulsory objectives

### C1. `contest`: establish strength, then repeatedly harvest monoliths

Enemy draft: `Stellar → Tavi → Prism → Cassi & Issac → Ren`.

This map has monolith scoring objectives. Our team deals **zero direct attack/spell damage to monoliths**, captures zero gems, and loses **0–1000** after 1327 rounds. Body deaths are **63–3**.

The enemy's progression is observable:

| Round | Our cumulative gold / body deaths | Enemy cumulative gold / body deaths |
|---|---:|---:|
| 100 | 175 / 4 | 535 / 0 |
| 300 | 450 / 13 | 2,263 / 3 |
| 500 | 800 / 21 | 3,931 / 3 |
| 800 | 1,157 / 34 | 6,981 / 3 |
| 1000 | 1,374 / 43 | 9,058 / 3 |

The enemy first deals direct monolith damage at **round 526**. It captures 200-gem rewards at **899, 937, 1066, 1125, 1240, 1314**, alternating between `(17,31)` and `(32,18)`. It banks five rewards and ends with the sixth still carried.

Repeated same-location capture intervals later approach **167–188 rounds**, consistent with exploiting a 150-round respawn plus clearing/capture time. The first monolith takes much longer than later cycles: this is not evidence of a single fixed clear-time threshold.

The enemy's purchases support this progression: Tavi completes Treasure Focus at round **191**, Durability Focus at **211**, then Power Focus; other casters acquire Focus and some survivability. Tavi receives **14 credited kills**, Prism 9, Issac 11. This is a team economy supported by combat, not one uncontested farmer.

**Inference:** gold/control first, then scaled objective production. The delayed first monolith hit could reflect readiness, routing, or target scoring; do not hard-code “attack monolith at round 526.”

### C2. Why our existing objective plan misses this

In the inspected `world.cpp`, objective detection requires a sufficiently heavy group with at least `obj_min_attackers` attacking camps. `params.h` sets **`obj_min_attackers = 2`**. Each isolated monolith has only one attacking camp, so the stampede-style objective plan does not classify these groups as intended compulsory team objectives.

`farm_monolith = 1` merely permits ordinary monolith scoring; it does not guarantee that a coordinated feasible scoring plan will ever be selected. This is compatible with the replay's zero monolith damage, although the replay cannot expose the internal branch taken.

**Proposed counter, in stages:**

1. During draft/static analysis, recognize “all meaningful gem income requires monoliths.” Gold is preparation; it is not a substitute win condition unless a genuine timeout plan is feasible.
2. Establish a safe gold route and survival plan first. The 63–3 death deficit means an immediate unprepared objective rush is likely to feed.
3. Reserve the people actually needed, their arrival times, healing, and a collector. Count present/arriving damage and sustainable tanking, not all living champions anywhere on the map.
4. Exploit persistent damage and cooldown windows when useful; estimate the complete cycle including capture and banking. Include interruption/contest risk.
5. Once an objective is ours, schedule its next respawn and defend the collector/route rather than returning to unrelated farming indefinitely.

Simply changing `obj_min_attackers` from 2 to 1 is a **diagnostic variant**, not a complete counter. The repository already documents failed variants that gathered at a monolith and were picked off.

### C3. `stampede` reveals an actual weakness to exploit

Against the same draft profile on `stampede`, we win **1080–0**, with body deaths **10–10** and near-equal gold gained (**6557–6448**).

We capture the 360-gem objective at **617**, **744**, and **913**; the last reward is split 180/180 between Ren and Varg. The enemy never receives a gem reward.

**Inference:** the enemy can build substantial combat stats without converting them into control of the compulsory group. Its objective policy appears less effective on this geometry than on `contest`. This is one observed game, not proof the profile always loses stampede.

**Proposed counter:** preserve our working heavy-group plan, improve its timing and protection, and measure objective ownership directly. Do not sacrifice the collectors or abandon the group to chase this opponent's casters. A controlled objective can beat a comparable fighting economy without winning every duel.

## 7. What the opponents are NOT demonstrably doing

These negative findings matter because the older documentation suggests some different explanations.

- **Not primarily winning through recall/capture overlap.** Inspecting event order, there are only **1/405 enemy gem-award events** with an earlier recall start within five rounds and no intervening recorded cancellation/death, versus **128/214 for us**. This is a timing signature, not proof every such recall completed. Same-round recall starts occurring *after* capture are excluded. Most enemy recalls in these sequences are capture-then-recall.
- **Not winning through altar-lock spam.** No enemy `Place altar lock` event occurs in these games; we place three. Locks remain a possible future counter, not an explanation of the observed defeats.
- **Not winning simply because they place more wards.** We record 3,672 placements versus 953. Useful information and acting on it matter more than placement count.
- **Not consistently using a completely different draft.** Several severe losses occur with the same first three selections as ours. Execution is a major gap.
- **Not proven to have perfect pathfinding.** The enemy records many more movement-blocked events. The event count alone does not imply poor realized throughput: it can include inexpensive failed attempts followed by a successful alternative.
- **Not proven to use ML or learn between games.** Replays reveal actions, not their internal implementation.
- **Not shown exploiting ongoing fuel failures.** All our 84 rollovers occur in rounds **1–6**: 50 at r1, 19 at r2, 9 at r3, and two each at r4–r6. None occur later. Opening delay is real, but it cannot explain all midgame losses.

## 8. Current source weaknesses that make these strategies effective

Line references are for the inspected source folder; function names are the stable anchors. These are implementation tasks for a later coding session, not changes made by this report.

| Priority | Source location | Confirmed limitation | Why it matters against these enemies |
|---|---|---|---|
| P0 | `brain.cpp:1119`, `can_support`; `brain.cpp:1129`, `combat`; `world.h`, `Ally` | Support filter checks HP and distance to any enemy, but ally state has no stored cooldown/channel/stun/action-availability model. Allies contribute pooled HP/DPS and a generic burst. Hidden camp claims still affect isolation. | A nearby farmer, channeler, or ally unable to reach the chosen target can make a losing engagement appear supported. The health filter already exists; finish the reach/action model instead of reimplementing it. |
| P0 | `brain.cpp:1265`, `killable`; combat pair policy | A generic `allies_burst` contribution participates in “killable”; pair caution is a scalar set to zero, without shared partner-risk protection. | The enemy repeatedly removes two bodies by killing the exposed partner. A false guaranteed-kill exception can override caution. |
| P0 | `brain.cpp:2643`, `farm`; `group_score`, claims and helper selection | No demonstrated reliable role allocation that preserves early productive income for the best clearer/collector. Reward sharing and low-output roaming persist in the replays. | `rows` enemy Varg and Ren compound income while ours split early rewards; `pilgrimage` Ren remains unproductive. The precise branch causing each route needs tracing, not speculation. |
| P0 | `world.cpp:140–179`, objective input/detection; `params.h`, `obj_min_attackers` | Single-attacker monolith groups are excluded from the heavy-objective detector. | Enemy caster economy eventually owns the only scoring source on `contest`. |
| P1 | `brain.cpp:274`, `init`; `world.cpp:23`, `init_static`; `brain.cpp:342`, `turn` | Initialization performs substantial static work in champion turns; the turn's round number is read before initialization and not immediately refreshed afterward. | On `ambush`, our Ren/Issac first move/cast at r7 while enemy bodies start at r1. Staggered arrivals and stale-round decisions are plausible consequences. |
| P1 | `nav.cpp:290`, `step_field`, especially `:331` | Candidate key is `field_distance * 4 + danger_penalty(0 or 3)`. A dangerous tile one field step closer always beats a safe tile one step farther; non-improving safe steps are not candidates. | “Avoid danger” is largely a tie-break in this path, not a safe-detour guarantee. Valuable farmers can enter exposed corridors. |
| P1 | `brain.cpp:2931`, `capture_group` | `capture_since` follows entering/switching group; it is not reset on every empty/contested capture interruption. | A preplanned recall can leave before a restarted capture finishes. Opponents usually avoid this particular complexity by recalling after reward. Fix bookkeeping rather than deleting safe overlap wholesale. |
| P1 | `brain.cpp:534`, `handle_channel` | Remaining tribute time is estimated from the current bag every turn, without subtracting actual elapsed channel time. Winning bags bypass the normal cancellation assessment. | Can abandon a nearly completed bank or remain in a doomed one. Only four manual cancellations occur in this dataset, so this is a correctness defect, not the main aggregate loss explanation. |
| P1 | `brain.cpp:2931`, `capture_group`; `:1886`, `tribute` | Capture uses full group gems in prospective bag/win checks, although rewards can be shared; route decisions use coarse distance comparisons and partially different recall assumptions. | `rows` contains real split rewards. A projected winning bag may not belong entirely to this champion, and a route can be fast geometrically but poor in productive time. |
| P2 | `comms.cpp:5`, `read`; `params.h`, `alert_refresh=0` | Reposting an unchanged alert does not refresh another reader's timestamp with the current setting. A one-bit toggle is not a robust universal timestamp under multiple writes. | A sustained fight/rally can look stale. Design expiry/ownership together with partner-status bits; do not allocate the same bits twice. |

The macro danger model and combat planner also need to distinguish **real action reach** from Chebyshev proximity. Walls, bushes, occupied tiles, move-exclusive ranged attacks/spells, dash availability, and team turn order change who can actually contribute.

### Existing improvements to retain and verify

The inspected baseline already includes `support_filter`, `win_bank`, `cast_en_route`, `cast_near_target`, `obj_plan`, `capture_before_retreat`, `finish_camp`, `dash_holes`, and stuck-navigation work. The next agent should refine those behaviors and inspect regressions, not present them as wholly missing.

The repository reports that blanket “stay and fight” rules, broad health-first builds, generic coordination, and a monolith gathering prototype failed or were neutral in prior local tests. Those results are useful cautions, although not independently rerun here. All local sparring bots described in the repository are from our own code family, which limits the strength of those results against these enemies.

## 9. Counter-strategy plan, in implementation order

### Phase 1: preserve a useful economy through the first contact

**Against Ren-first:** reserve safe opening camps per champion, give a feasible upgrade path to the frontline and one productive carry, and avoid sending a low-health linked partner into the first enemy concentration. Model the enemy's post-shop HP/damage, not just its champion name.

**Against CI-first:** prioritize pack efficiency, repeated camp cycles, and relevant damage upgrades. Avoid gratuitous shared captures and unnecessary team grouping. These games currently offer the cleanest way to measure an economic improvement without combat confounding it.

**Against the caster profile:** preserve economy while preparing the actual scoring objective. `contest` requires a feasible monolith plan; `stampede` requires maintaining the heavy-group capture plan that already won.

Implementation principles:

1. Use draft time and the 1,024-byte draft memory for bounded opening assignments or compact map features. Keep all game-time communication within the real eight-byte shared-memory budget.
2. Count helpers by arrival time, legal attack/cast opportunity, health, and commitment. A claim is an assignment, not a current location.
3. Reserve the collector separately from helpers. Let surplus bodies begin the next productive task when capture no longer needs them.
4. On linked-partner danger, compare retreat, protected continuation, immediate bank, and fight-back outcomes. Do not blindly flee a chaser that cannot be escaped.
5. Fix opening fuel without causing dangerous staggered deployment. Faster individual first moves do not automatically produce a better team opening; verify actual arrival sequences.

### Phase 2: use enemy predictability selectively

The repeated camp coordinates in `fragment`, `rows`, and `pilgrimage` provide candidate interception windows. Infer expected returns from the most recent observed clear/capture and respawn rules; do not hard-code replay rounds as a live schedule.

Potential tactics to test:

- **Capture interruption:** enter a contested reward region with a survivable, mobile unit while the enemy collector is exposed. Extra allies do not accelerate capture, and contest resets progress. Do this only when denied value exceeds travel, injury, and lost own farming.
- **Punish a weak linked partner:** kill the reachable low-health member rather than attacking a durable Ren. Include the other body's lost downtime and possible bag transfer in the value calculation.
- **Attack during a split shopping cycle:** if visible information establishes that the frontline has recalled and a collector remains exposed, use the temporary local advantage. Do not assume an unseen champion has recalled.
- **Trade productive territory:** when the enemy concentrates at one objective, take a feasible scoring source elsewhere. On compulsory-objective maps, protect/contest the actual source instead of accumulating irrelevant gold forever.
- **Altar denial near a likely finish:** locks cost 10 gold and can interrupt enemy tribute. Reserve this as a targeted endgame experiment; chasing altars for routine locks could cost more farming than it denies.

These are test candidates, not evidence that the opponents are already vulnerable to a guaranteed exploit. All live decisions must use legal personal vision and permitted shared information; full replay visibility is analysis-only.

### Phase 3: make scoring completion the decision objective

For each candidate task, estimate:

`expected secured score / (travel + clear + capture + necessary recovery/upgrade + bank + transition to next task)`.

Add the marginal future benefit of gold, denial value where actionable, and the risk/cost of losing either linked partner. Discount gold whose upgrades cannot pay back before the expected finish. Include actual collector share and the probability the channel can complete.

This is a design objective, not a request to pile every estimate into one uncalibrated formula. Keep intermediate predictions traceable so Claude can compare predicted and actual times, rewards, and risks.

## 10. Replay fixtures Claude should use first

Coordinates are zero-based `(x,y)`. HP snapshots cited above are generally the preceding round's recorded state, not an assertion about HP immediately before the fatal action.

| Fixture | Match ID | Inspect | Desired change to validate |
|---|---|---|---|
| `fragment` | `7dfd2788-5f3f-4e97-99f9-b8b7b5c530e2` | r19–100: enemy Ren income, shopping at r56, pair death at r65 | Respect power spikes; save linked partner while maintaining early income |
| `eight` | `60384919-d834-47e4-9972-3bf438f9924c` | r20–50: contact, pair collapse, subsequent camp deaths | Safe coordinated opening; no automatic global cast-disable conclusion |
| `interlock` | `ad00b5b2-dfc2-43f0-a20e-4d9d15d5f81e` | r81–86: Cassi near death, healthy Issac lost, Varg follows | Joint pair risk and real reinforcement checks |
| `rows` | `077d8679-86c3-4cf1-b64a-516441f53196` | r20–144: enemy Varg capture/shop/repeat; our r59/r75 splits | Faster first profitable cycles and purposeful collector assignment |
| `expanse` | `27bcacab-984b-42dc-a97d-fed2d0b68eff` | Whole farming race; Issac/Varg output | Map-specific build and allocation; no extra combat conservatism |
| `pilgrimage` | `711f2c37-06a9-43cb-bc28-547d49883adf` | Our Ren's zero-resource roaming; enemy cycles from r52 | Long-loop productivity watchdog and stable route completion |
| `contest` | `aaee8bc8-6aae-40ea-8d65-baad4cb06e93` | r1–500 economy; first enemy monolith hit r526; captures r899 onward | Safe preparation plus explicit single-monolith objective plan |
| `stampede` | `4433f733-808b-4de5-959a-ede593d97836` | Captures r617/r744/r913 | Preserve existing winning objective behavior |
| `corners` | `b6d500f1-cd34-4d59-a3eb-acd37638ceea` | r200–275: score overtaken before death cascade | Maintain production when ahead, then avoid losing the whole working team |
| `ambush` | `a8dcfcf7-f7a6-44bf-a8ec-3622d6844f39` | r1–7 startup; Ren/Issac delayed to r7 | Fuel-safe initialization and deliberate arrival synchronization |

## 11. Full distinct-match results

All score/death pairs below are **HouseOfCoders–enemy**. “Deaths” means bodies, not credited kills.

| Map | Rounds | Score | Body deaths | Enemy profile |
|---|---:|---:|---:|---|
| ambush | 561 | 394–1010 | 7–3 | Ren-first |
| collision | 556 | 132–1002 | 14–1 | Ren-first |
| contest | 1327 | 0–1000 | 63–3 | Caster/objective |
| corners | 447 | 320–1018 | 8–3 | Ren-first |
| eight | 459 | 44–1130 | 22–4 | Ren-first |
| stampede | 960 | **1080–0** | 10–10 | Caster/objective |
| swirl | 406 | 72–1018 | 21–5 | Ren-first |
| expanse | 580 | 876–1016 | 0–0 | CI-first farming |
| fragment | 488 | 22–1034 | 17–0 | Ren-first |
| elkring | 451 | 324–1008 | 14–3 | Ren-first |
| interlock | 499 | 66–1042 | 19–1 | Ren-first |
| lanes | 465 | 532–1014 | 6–4 | Ren-first |
| monolith | 489 | 702–1016 | 6–5 | Ren-first |
| packs | 543 | 700–1044 | 14–6 | Ren-first |
| pilgrimage | 658 | 340–1032 | 3–2 | Ren-first |
| rows | 355 | 726–1056 | 0–0 | CI-first farming |
| rushbait-v2 | 525 | 242–1038 | 8–0 | Ren-first |

Duplicate replay pairs, despite different match IDs:

- `383ad399-6714-4351-a6a4-2c9e784c737d` = `e15191bf-82c0-4715-81e8-f942df6f2439` (`collision`).
- `27bcacab-984b-42dc-a97d-fed2d0b68eff` = `b9ff95eb-eba5-42ee-8b0a-f2847edc22b1` (`expanse`).
- `7dfd2788-5f3f-4e97-99f9-b8b7b5c530e2` = `169afdb9-8fab-4479-b9ee-6a7ab3447fc6` (`fragment`).

Do not interpret the 1/17 result as a precise estimate of future ladder win probability. This is one supplied replay per official map, all on the inferred HouseOfCoders A side, with unknown opponent versions and no randomized repeated sample.

## 12. Validation requirements for the next coding session

1. Match the actual ladder submission ID/hash to a frozen baseline. Preserve `legend_st` separately from source-only changes. Reconcile session notes with files before merging any unfinished patch.
2. Add one focused variant at a time: reachable-support/pair protection; productive opening/collector roles; single-monolith planning; safe route and timer correctness. Evaluate interactions after individual effects are understood.
3. Test **all 17 official maps on both sides**, and report each map and side separately. These supplied replays cannot establish B-side strength.
4. Use fresh real-opponent games or genuinely independent enemy implementations when available. A forced enemy draft on our own code is a draft test, not a faithful enemy strategy clone. These replays cannot be replayed as reactive opponent programs.
5. Retain `stampede` as a regression fixture. Also measure `rows`/`expanse` without combat, so a win from more fighting elsewhere does not hide worse farming.
6. Record first capture, first useful emblem, gold/camp gems at r100/r200, linked-pair deaths, productive time, reward splits, long no-income loops, and time from collection to completed bank. Separate gold-only awards from gem awards.
7. Check zero faults; count rollovers and stale-round resumes; verify turn/timer rules on tiny fixtures. Fix the opening without assuming that earlier individual departure always helps.
8. Use paired comparisons with fixed baseline/opponents, both sides, and multiple seeds where relevant. Repeating an identical deterministic fixture is not new independent evidence. Keep final evaluation maps/opponents separate from parameter tuning.
9. Accept a strategic change only if it improves relevant enemy-profile outcomes without material regression elsewhere. Fewer deaths alone are insufficient if camp production collapses; more kills are insufficient if objectives remain unclaimed.
10. Tune parameters after validating the structural changes. Save the best **evaluated** parameter vector, and verify which code/ZIP it was evaluated against.

## 13. Ready-to-paste instruction for Claude Opus

> Work from the actual `Cambridge_Battlecode` files and first verify the ladder submission baseline. Use this report as replay evidence, not as a claim that proposed counters are already tested. Focus on three enemy behaviors: Ren-first durable farming into pressure; CI-first Monster/Power farming with concentrated Varg/Issac income; caster economy into monolith scoring. Preserve the working stampede objective plan. First investigate reachable support and linked-pair risk, productive opening/collector assignment, long no-income roaming, and compulsory single-monolith planning. Distinguish already-present fixes from unfinished notes. Keep variants isolated and switchable, respect eight-byte match memory and legal personal vision, and measure official maps on both sides. Do not claim an enemy clone from its draft alone or promise a guaranteed win. Report predicted versus realized economics and fresh opponent results before recommending a submission.

This instruction describes a **future implementation session**. The present task requested only analysis, and no bot was created or modified.

## 14. Supporting files and reproducibility

This Markdown file is self-contained. Supporting evidence is in the sibling `match_analysis/` directory:

- `manifest.json`: archive membership, replay SHA-256, and duplicate mapping.
- `summary.json`: per-match/team/champion metrics.
- `maps.json`: extracted geometry and official map matches.
- `match_details.txt`: capture/death/banking sequences and score timelines.
- `enemy_details.txt`: opponent item inventories, capture circuits, early actions, and comparisons.
- `profiles.json`: aggregates by observed draft profile. The legacy key `capture_near_recall` means an earlier recall start within five rounds, ordered before capture, without an intervening recorded cancel/death—not proof of completed teleport.
- Each unique match directory contains `decoded.json` and the unchanged replay bytes.
- `decode_all.mjs`, `audit_decoder.mjs`, `maps.mjs`, `summarize.py`, `enemy_analysis.py`: analysis utilities only; none is bot code.

Reproduce from `D:\Downloads\camb2` after the existing engine asset and extracted archives are present:

```powershell
node match_analysis/decode_all.mjs
node match_analysis/maps.mjs
python match_analysis/summarize.py
python match_analysis/enemy_analysis.py
```

Rules and API references: supplied `GameRules.md` (capture, channels, items, vision, linked death, fuel, memory) and `BotAPICpp.md` (champion state/cooldown/visibility and shared memory). The [official matches page](https://2026a.battlecode.co.uk/game/matches) did not expose authenticated match metadata during this analysis. The official replay engine was obtained from the [cambc 2.2.5 package](https://pypi.org/project/cambc/2.2.5/); match claims above come from the user's supplied local replays, not inferred website results.
