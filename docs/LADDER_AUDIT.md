# HouseOfCoders: bot improvements for Claude

## Task and exact project

Improve **`D:\Downloads\cambridge\camb2\Cambridge_Battlecode`**, the current Claude C++ `legend` bot. Work from this project and preserve a frozen baseline before making changes.

This brief consolidates the source audit and all **40 supplied matches**, including **420 character records**. It is self-contained: no dashboard or separate report is required to understand the recommendations.

Audited revision: **`25bed8d`**. Submitted archive: `submissions/legend.zip`, SHA-256:

```text
1caa8cdf3155d74a4a4f5962301df186d4c49d7126d358fb8d48288fa53f1769
```

All 15 source files matched that archive after Windows line-ending normalization. If the project has changed since the audit, verify whether each defect still exists. Source line numbers below refer to the audited revision; function names are the stable references.

**Evidence status:** replay results and the cited source behavior were inspected. Proposed improvements have not been A/B tested. No new online matches were run. The user will run online tests. Opponent names cannot be reliably assigned to individual archives without match-summary metadata.

## 1. Main conclusion

**Optimize completed scoring routes, protect the linked pair, and fix combat/action decisions before adding a large ML system.** The bot already shops, recalls, casts spells, changes priorities, and adjusts its stance. Those features need better decisions around them.

| Metric across the 40 games | HouseOfCoders | Opponents |
|---|---:|---:|
| Wins | **5 / 40** | 35 / 40 |
| Zero-score losses | **5** | — |
| Camp gems collected | **21,246** | **39,948** |
| Gems banked | **19,530** | **39,134** |
| Body deaths | **645** | **331** |
| Recorded body-rounds spent dead | **22.9%** | **12.1%** |
| Gold earned | 131,062 | 204,258 |
| Gold spent | 122,120 | 185,730 |
| Recall starts | 1,198 | 1,310 |

The largest accounting deficit is camp-gem production. Deaths make that deficit worse by removing farming time and surrendering objectives. The bot spent **93.2% of its earned gold**, so unspent gold is not the main problem.

There were **105 own fuel rollovers: 104 during rounds 1–5, only one later**. Fix initialization and stale-round execution, but do not explain these losses primarily as persistent fuel exhaustion.

Every individual gem/gold ledger balances, and all team bank totals match replay scores. Cassi and Issac each count as a body death when their linked death triggers; credited kills are a different statistic.

## 2. Priority fixes

### P0 — Make scoring objectives drive the economy

**Evidence:** on stampede we lost **0–1080** despite leading **27–7 in kills** and **9,364–6,170 in gold earned**. All six of our bodies collected zero gems. Another stampede loss was **0–1080 despite a 25–12 kill lead**.

On contest, we lost **0–1000**, with **54–2 body deaths**. Our team recorded no direct attack/spell damage to a monolith, while the opponent completed the scoring objective.

**Source:** `bots/legend/src/brain.cpp`, `group_score()` around line 1844. The current value includes `gems + 0.22 × gold`, but does not fully price the bank route or gold's remaining payback time. Large compulsory objectives compete with easy gold groups under a local rate heuristic.

**Implement:**

- Classify maps from actual camp geometry: distributed scoring camps, concentrated heavy objectives, monolith objectives, long transport routes.
- Evaluate **travel → clear → capture → bank**, including healing and shopping detours.
- Value a gold detour by the future scoring improvement its upgrade enables before the likely finish. Gold must not remain equally attractive forever.
- For compulsory heavy objectives, support persistent damage across visits, protected ranged damage, appropriate tank positioning, and coordinated capture defense.
- Assign a collector and useful helpers. Helping clear and receiving the capture reward are different roles.

**Benefit:** directly addresses games where fighting and gold farming never become score.

**Risk:** moving to the objective too early can feed the enemy. Require a feasible clear/survival plan; avoid a permanent deathball on distributed-resource maps.

### P0 — Replace phantom support with reachable support; protect Cassi and Issac jointly

**Evidence:** each member of our pair spent about **31% of recorded body-rounds dead**, with **163 paired death incidents**. In one match, full-health Cassi carrying 44 gems died near home because Issac died far away.

**Source:** `brain.cpp`, `combat()` around lines 1046–1056 and `killable` around 1134. Nearby visible allies contribute HP, estimated DPS and burst without establishing whether they can hit the chosen target in time. A hidden ally's nearby claimed camp can also count as backup; a claim is not a current position or a commitment to help.

**Implement:**

- Count immediate allied damage only when reach, legal action availability, cooldown, stun/channel state and turn timing support it.
- Discount or exclude unseen allies from immediate burst. Keep longer-term reinforcement estimates separate.
- Model the cost of losing either linked partner as both bodies' downtime plus both bags at risk.
- Share a minimal pair status: danger/low health and valuable bag/banking. Use conservative assumptions when information is stale.
- Preserve the option to fight back when escape is worse. Simply raising every fight threshold can give chasers free attacks.

**Communication constraint:** the current protocol has only four unused high bits in bytes 2–5. Two status bits per partner fit; full position/HP/bag/cooldown sharing does not. Do not allocate those same bits again for alert timestamps.

**Benefit:** reduces expensive linked deaths and engagements based on nonexistent support.

**Risk:** excessive caution or keeping the pair permanently together sacrifices the extra body's farming value. Safe independent farming should remain possible.

### P1 — Bank before recalling when the complete route is better

**Evidence:** in interlock, we lost **976–1056** while carrying **116 unbanked gems**. Ren's 72-gem bag was enough to finish the game, but he recalled away from a nearby altar and spent the remaining rounds returning across the map.

**Source:** `brain.cpp`, `capture_group()` around line 2436. Recall is triggered by `rich || hurt || bag` without comparing the nearby direct-bank alternative. The turn pipeline also checks combat before initiating tribute.

**Implement:** before recall, compare:

1. Capture → direct safe altar → tribute.
2. Capture with recall overlap → necessary heal/shop → altar → tribute.
3. Capture → worthwhile nearby follow-up → bank, if the added delay and risk are justified.

Use predicted post-capture gems/gold, actual travel costs, current team score and partner risk. A **survivable winning bank** should outrank discretionary shopping and nonessential fighting. Persist the selected route until meaningful new information invalidates it.

**Benefit:** a relatively contained patch with a precise replay fixture; also improves pure farming races.

**Risk:** a shorter direct route can be dangerous or skip a necessary heal. Optimize safe completion, not geometric distance alone.

### P1 — Permit safe detours and eliminate unproductive task oscillation

**Source:** `bots/legend/src/nav.cpp`, `step_field()` around line 277, considers only neighbors whose static distance decreases. It cannot take a safe lateral step when a dangerous shortest-path step remains available. `step_to()` can retry without avoidance. Low-fuel movement fallbacks also need risk checks.

**Implement:** retain cached reverse distance fields, but invoke a bounded local risk search when all improving steps are too dangerous. Allow a temporary lateral/backward move. Use a stricter survival constraint for valuable carriers and a bounded damage allowance for tanks.

Track task, target, distance progress, damage and threat changes. Break repeated two-tile loops only when they produce neither objective progress nor useful combat effects. Reversals can be legitimate kiting.

**Benefit:** avoids walking through threats solely to reduce distance and reduces repeated task switching.

**Risk:** extra search consumes fuel; absolute danger avoidance can deadlock. Set an expansion cap, maintain a safe fallback, and add task hysteresis.

### P1 — Choose legal action sequences before walking

**Source:** `brain.cpp`, `farm_group()` around line 2537, first searches basic-attack range and then moves toward it. A range-4 spell is considered too late in some branches; walking can make that spell illegal.

**Implement:** enumerate a small set of legal candidates before acting:

- Hold position and cast single-target damage or AoE.
- Attack → reset → attack.
- Dash → attack.
- Walk → melee attack.
- Cassi's movement-compatible stun combined with movement.
- Hold range 4 for protected camp damage, or move into basic range when a nearer tank makes that faster and safe.

Respect movement exclusivity and **one successful cast across both ability slots**. Decide Varg shield versus reset from incoming damage and kill completion, instead of spending the cast automatically before evaluating the fight.

**Benefit:** improves damage opportunities and caster survival without changing the whole macro policy.

**Risk:** permanent spell-only kiting can be slower than tank-protected basic attacks. Compare modes rather than hardcoding one.

### P2 — Fix openings, helper accounting and channel bookkeeping

- **Opening income:** on eight, five of our six bodies earned zero gold in a 0–1052 loss. Give bodies feasible first jobs, measure first income/first capture, and abandon an invalid opening after enemy contact. Use draft memory where useful within measured fuel limits.
- **Helper credit:** the claim tie-break in `group_score()` can skip higher-index claimers when the current body already holds a task. Separate ownership resolution from actual helper DPS; investigate late-index Ryth's contribution.
- **Tribute progress:** `handle_channel()` around line 439 recalculates roughly the original duration from carried gems rather than subtracting elapsed channel time. Track the start and remaining duration. There were only 22 own manual channel cancellations, so this is not the primary loss explanation.
- **Capture resets:** enemy occupation can reset capture progress while `capture_since` retains the old start. Reschedule recall overlap after confirmed interruption and account for Home recall duration.
- **Repeated alerts:** `comms.cpp` refreshes received alert time only when the raw payload changes. Reposting the same tile/kind does not refresh other bodies. Add a properly budgeted freshness protocol with explicit wrap/expiry behavior.
- **Fuel and errors:** make expensive initialization resumable; check the observed round before mutations after a rollover. Add bounded debug counters for internally caught API failures.

## 3. Character-by-character priorities

These averages use only matches where **both teams drafted the same champion**. They share maps and match lengths, but teammates, routes and items still differ; this is not a controlled test of champion strength.

| Champion | Matched games | Our/enemy banked gems per game | Our/enemy deaths per game | Main improvement |
|---|---:|---:|---:|---|
| Ren | 26 | 110.4 / 250.5 | 2.46 / 1.15 | Better objective choice, tank positioning and bank completion; cast frequency is already similar |
| Stellar | 35 | 99.5 / 194.0 | 2.49 / 1.31 | Consider range-4 casts before walking; our casts average 34.7 versus 59.1 |
| Cassi | 38 | 48.7 / 83.0 | 3.97 / 2.34 | Safe caster position, escape stun and partner-aware banking |
| Issac | 38 | 72.9 / 175.2 | 3.97 / 2.34 | Dash commitment and paired risk; similar cast counts currently produce much worse outcomes |
| Varg | 23 | 106.9 / 249.1 | 2.17 / 1.30 | Dense-pack assignment, splash targeting, shield/reset choice and stable routes |
| Ryth | 11 | 31.6 / 291.8 | 2.55 / 0.55 | Useful opening/helper jobs and objective completion; do not conclude the champion itself is weak |

Most common enemy picks across the entire supplied sample: Cassi & Issac **38/40**, Stellar **35/40**, Varg **28/40**, Ren **26/40**, Ryth **15/40**. This describes these archives, not the whole current ladder.

Do not force every body to bank equally. A useful tank or screen can enable someone else's capture. Evaluate marginal team scoring contribution, while investigating bodies that neither score nor create useful protection/damage.

## 4. Exact replay evidence to use as regression fixtures

Raw inputs and decoded evidence are in:

```text
D:\Downloads\cambridge\camb2\audit_20261017\matches\<MATCH_ID>\
```

| Match ID | Observed failure / control case |
|---|---|
| `9ea4250b-e3a8-4281-8f65-b5a57ce2ef14` | Stampede, r1201: 0–1080 despite 27–7 kill lead. All six bodies collect zero gems. |
| `76c1ca46-f897-464e-918b-ed77bf012b83` | Stampede, r1517: 0–1080 despite 25–12 kill lead. Our Ryth has six kills and zero banked gems; enemy Ryth banks 720. |
| `f1bcfbdd-f90b-422b-99fb-0ea095d21804` | Contest, r1104: 0–1000; no own direct attack/spell damage to a monolith. |
| `a778962d-9832-4036-bbb8-71dd0af51683` | Interlock, r1117: 976–1056. Ren steps onto (32,10) at r1096, recalls r1097, gets 72 gems and teleports home r1102. Altar (36,12) is three static walking steps to submission range. He ends at (15,19), still carrying 72. |
| `6dcbc1bf-7924-4174-b983-050191263f32` | Packs, r365: Cassi at (0,4), full 771.25 HP, bag 44. Issac at (22,20), 11.5 HP. Enemy Ren attacks Issac and both partners die. |
| `21162405-c4ce-451c-a67d-b7291a647a7b` | Eight, r411: 0–1052. Only Varg earns gold, 90 total. Pair dies r33, Stellar r37, Ren r41, Varg r47. |
| `0b17bfc6-d2bf-4ba4-8f48-080b06bbea3e` | Expanse, r681: 986–1020, zero kills/deaths on both teams. Our 1,689 ordinary walking steps and 39 recalls versus 1,357 and 26. A throughput control case, not a combat problem. |
| `b0344ab7-491c-4e1f-905f-f9ab00dd3f1b` | Swirl, r385: 0–1040. Varg makes 39 two-tile reversals r118–158. Check actual progress before labeling them waste. |

For interlock, a direct walk and tribute suggests a finish around **r1112–1113**, before the observed enemy finish. This is a **counterfactual timing estimate**, not an executed alternative or guaranteed win. Build a mechanic fixture and test the route.

Preserve existing strengths too. Recorded wins: `db677121-ad23-41ec-b55f-3f19a5832dcc`, `bd667f95-c10e-4ca0-8f58-c19d78894d5e`, `fb5f2139-d872-4a8c-b80a-b79232ec3829`, `c3b1c185-cac4-4365-9978-7ab8ff06b6eb`, `ed0b76f9-fa37-4ce5-a0dc-a39f1991e08c`.

## 5. Recommended decision architecture

Keep the existing world model, navigation caches and champion kits. Add explicit, persistent task plans and bounded action evaluation:

```text
Legal observation and age-tagged memory
→ round/fuel validity and ongoing-channel checks
→ urgent plans: safe winning bank, necessary escape, reachable enemy-bank prevention
→ economic plans: clear/capture/bank, worthwhile upgrade, objective denial
→ helper/collector allocation and linked-partner risk
→ small set of legal movement/attack/spell sequences
→ execute, verify state, retain/release task
→ spare-budget cache work and bounded diagnostics
```

Use an approximate plan value such as:

```text
P(bank before deadline) × useful gems
+ upgrade's scoring payback before deadline
+ enemy score prevented
− expected death cost
− opportunity cost of time spent
```

For imminent winning plans, prioritize feasible finish time and survival rather than a simple value/time ratio. Consider combined friendly banks when observable/communicated. Estimate enemy finish conservatively from legal observations; do not use omniscient replay data in the live bot.

Counter efficient farmers with shorter full cycles; counter early invaders with feasible alternate openings and real support; counter heavy-objective casters with range discipline and tank spacing; counter bush/altar ambushes with relevant ward placement and alternate routes. Each counter must preserve scoring tempo—endless caution also loses.

## 6. ML/RL: repair evaluation before training

**Critical concrete bug:** `tools/rl/es_train.py` around lines 212–234 evaluates the current mean, updates `theta`, then saves the updated vector as `best_params.json`. That saved vector is not necessarily evaluated or best.

Fix these before trusting optimization:

1. Save each evaluated vector with its exact source/build hash and case manifest. Keep **latest** separate from **best validated**.
2. Promote using validation wins and map/opponent robustness. Current death/bag/kill shaping can outweigh the win/loss term; an improved shaped score is insufficient.
3. Retain failing replays and report missing/faulted games explicitly. The current evaluation routine deletes its run directory.
4. Self-play variants are useful sparring partners, not actual top-team implementations. Broaden opponent behavior and use fresh real-team results.
5. Split ML data by game, map family and opponent version. Keep correlated encounter rows together. Avoid future-state features leaking into decisions.

After deterministic fixes, consider a shallow model or tiny quantized network for a narrow question: survival of a proposed fight, camp-clear time, or choice among legal plans. Measure feature-extraction and inference fuel. Whole-game deep RL is a later experiment requiring a reliable simulator, broad training opponents and deployment validation.

## 7. Implementation sequence and acceptance criteria

Start with a frozen baseline and reliable evaluation, then implement separate variants:

1. Bank-route correction: small, explicit interlock fixture.
2. Reachable combat support and linked-pair risk.
3. Objective planning with finite gold payback.
4. Bounded danger detours and cast-before-move selection.
5. Opening, helper, channel and communication fixes.
6. Tune only the validated combination.

Strategically, objective planning is P0; starting with the smaller bank patch provides an easy-to-review change while the broader model is built. Do not combine every unfinished route/math/ML experiment into one patch.

The replays were decoded with **engine 0.0.3 / cambc 2.2.5**. Repository `ENGINE_FACTS.md` describes **0.0.2 / 2.2.2** and contains inconsistent old channel prose. Re-probe movement/cast exclusivity, tribute/stun behavior, capture resets and recall overlap on the engine used for deployment.

For each patch:

- Run the relevant mechanic fixtures and verify the actual engine behavior.
- Compare candidate and baseline on identical map/opponent/side cells. The audit-time official pool had 17 maps; both sides against five diverse opponents gives **170 cases per candidate**. Refresh the pool if it changes.
- Include starter, frozen current legend, aggressive, objective/caster and efficient-farming opponents. Use idle matches separately for throughput, not to inflate competitive win rate.
- Report completed/expected cases, wins, zero-score losses, captured/banked gems, first income, first bank, pair deaths, dead body-rounds, capture-to-bank delay, unfinished bags, rollovers and internal API failures. Break results down by map and opponent.
- User-run online matches should record opponent name/version, own submission ID/hash, map, side and timestamp.

**Return to the user:** separate changes and validation results, the combined candidate's exact submission hash, remaining failure cases, and which claims are still hypotheses. The aim is stronger demonstrated results against real opponents, not an unsupported promise to beat every bot.
