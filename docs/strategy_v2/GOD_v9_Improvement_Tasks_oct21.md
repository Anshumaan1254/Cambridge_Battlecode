# GOD v8 → v9 — Improvement Task Specification (patch 3.1 balance edition)

**Scope of this file.** Only the changes that make the bot stronger, rewritten for the balance patch whose notes reached us on 21 October 2026 ("patch 3.1" below; section 1). No description of how the existing bot works beyond what an implementer needs to place a change correctly (the full working is in `GOD_v8_Bot_Complete_Manual.pdf`). Every task is written so that an agent with the `god/src` sources, the CAMBC SDK (`BotAPICpp.md`), the rules (`GameRules.md`, patch 3.0 + 3.0.2 + the 3.1 balance notes) and a match runner can implement it completely, verify it and roll it back on its own.

**Target.** The bot must win against opponents it has never seen and against opponents that change strategy during a match: it must notice the change within ~20–40 rounds, name it, and switch to a coherent counter-plan without losing the farming and survival quality it already has — on the post-patch champion values.

---

## 0. Ground rules for every task (read first, apply always)

### 0.1 Repository and build

| Item | Value |
|---|---|
| Sources | `god/src/`: `main.cpp`, `common.h`, `params.h`, `draft.cpp/.h`, `world.cpp/.h`, `nav.cpp/.h`, `brain.cpp/.h`, `comms.cpp/.h`, `learn.cpp/.h`, `ml2_model.h` |
| Language / SDK | C++20 against the CAMBC C++ SDK (patch 3.0 API, balance 3.1). The zip ships only `src/`; build with the official SDK toolchain used for submission. |
| Compile compatibility | The code compiles on both SDK variants (with / without Heart of Ruin) through `SDK_HAS_HOR`, `D_HOR`, `CT_HOR` in `common.h`. New code must keep that: never name `champion_draft::heart_of_ruin` or `champion_type::heart_of_ruin` directly; use `D_HOR` / `CT_HOR` and guard with `SDK_HAS_HOR` where a value is required. |
| Warnings | Build warning-clean (`-Wall -Wextra`); the existing code is. |
| Line references | All `file:line` anchors refer to the **unmodified v8 sources**. Lines shift as tasks are applied: locate anchors by the quoted code, not by the number alone. |

### 0.2 Mandatory conventions

1. **Every behavioural change is behind a `params.h` switch** whose default keeps the v8 behaviour (usually `0`), unless the task says *"default ON"*. New switches are added as new fields at the **end** of `struct Params` (just before the closing `};` at `params.h:662`), with a one-line comment in the existing style. `P` is `inline constexpr Params P{}`; the `LEGEND_RUNTIME_PARAMS` branch is for the training tool only and needs no change.
2. **Never throw out of a turn.** Every new SDK call is wrapped in `try { … } catch (...) { }` exactly like the existing code. Every new loop over the map has a hard bound.
3. **Fuel.** 100,000 fuel per turn. All new per-turn work of v9 together must stay under ~2,000 fuel on 100×100 maps (measure with `bc::fuel_remaining()` before/after under `#ifdef LEGEND_TRACE`). Host (SDK) calls are the expensive part; cache their results per turn.
4. **Do not change the ml2 feature definitions** (`Brain::ml2_features`, `ML2_NF`, `ml2_model.h`): the logistic weights and the boosted trees were fitted on them. New fight-model knowledge goes into the heuristic estimate in `combat()` only. Re-fitting the weights on post-patch games is task T15.
5. **`[VERIFY]` marker.** Where an SDK function is marked `[VERIFY]`, open `BotAPICpp.md`, confirm the exact name and signature, and adapt the call. If the function does not exist, implement the stated fallback and leave that switch at `0`. Never guess an SDK name into the build.
6. **Shared memory is read-modify-write safe** (turns inside a team are sequential) but every bit is accounted for in `comms.h`; do not use a bit without updating the layout comment there.
7. **Deterministic replay.** Keep the bot deterministic given the same inputs, except where task T14 introduces *seeded* randomness.
8. **One task = one branch = one commit** named `T<nn>-<slug>`. A task is *done* only when all its acceptance criteria pass and the A/B gate of Appendix A is met (or the task is marked *no A/B needed*).
9. **Style.** Tabs; the existing naming (`snake_case`, `P.` for params, `W` = `world()`, `C` = `comms()`, `N` = `nav()`); comments that state the *reason*, in the existing voice.
10. **Numbers from the engine, never from this file.** Where a champion number is needed in code (a multiplier, a growth, a range), read it from `bc::champion_designs` / `Kit` / `bc::constants` as the existing code does. The patch numbers in section 1 are for reasoning and for the *priors* that are hard-coded by design (the draft), never for new literals.

### 0.3 Vocabulary

| Term | Meaning |
|---|---|
| body | One champion of our team; one program instance per body; `W.my_index` is its index in `bc::champions(team::ally)` order (= draft pick order; Cassi & Issac are two consecutive bodies). |
| group | A camp group; `Group::id` = index in `bc::map::camp_groups()` order (identical on the draft side and in play). |
| claim | The group id a body publishes in shared memory while farming / capturing / waiting (`Comms::write_self`). |
| stance | The 3-value team mode from the bandit in `learn.cpp` (SPREAD / GROUPED / PUSH), broadcast by body 0. |
| plan | New in v9: the 8-value team plan id chosen by body 0 from the opponent model (T05/T06). |
| archetype | New in v9: the opponent class the model believes it faces (FARMER, INVADER, …). |
| window | A fixed number of rounds over which counters accumulate before a decision (bandit: 40; opponent model: 20). |
| cascade | The per-turn priority order in `Brain::turn()`: `combat → safety → tribute → home_trip → shop_trip → respond_to_alert → farm` (`brain.cpp:788–811`). |
| A/B | A match batch of the candidate build against the baseline build and the proxy opponents (Appendix A). |

---

## 1. Patch 3.1 balance changes and what they change for GOD

### 1.1 The changes

| Champion | Stat | 3.0 → 3.1 | Change | Who this matters for |
|---|---|---|---|---|
| Stellar | Health / per shard | 750 → 650 / 75 → 65 | −13% / −13% | **Our 2nd pick** (prior 0.95) is squishier and scales worse |
| Stellar | Focus / per shard | 85 → 70 / 9 → 7 | −18% / −22% | Its 2×F damage (170 → 140) and 1.4×F area (119 → 98) at base; every Power shard adds less |
| Heart of Ruin | Strength / per shard | 40 → 30 / 4 → 3.5 | −25% / −12.5% | **Our 3rd pick at team size 3** farms and trades slower with basic attacks |
| Heart of Ruin | Dash landing (S2) | 1.75×F → 1.5×F | −14% | Landing hit 175 → 150 at base focus; still its main fight spell |
| Ren | Stun damage (S1) | 1.25×F → 0.75×F | −40% | **Our first pick**: burst 125 → 75; tank, reflect and the stun itself unchanged |
| Vesper Vale | Health / Strength | 900 → 1000 / 50 → 55 | +11% / +10% | A ranged gold farmer with reset + dash becomes viable; expect it on the enemy side |
| Vendetta | Health | 800 → 1000 | +25% | The enemy bruiser / invader gets much harder to kill; reset-on-kill chains |
| Tavi | Health / Focus | 750 → 900 / 100 → 110 | +20% / +10% | 1.4×F damage + stun 140 → 154; the ring plan's second caster is now solid |
| Prism | Passive focus per carried gem | 1 → 1.5 | +50% | A Prism carrying 60 gems has +90 focus (base focus 80 per GameRules 3.0 → 170; 1.5×F spell = 255 + stun): a loaded Prism is the most dangerous unit in the game, ours or theirs |

### 1.2 What updates automatically and what is hard-coded

GOD reads every kit number from the engine (`common.h:86 kit_of`: slot, range, multiplier, walk-exclusivity, radius; `world.cpp:452–454` (allies) and `brain.cpp:530–532` (self): base stats and growth; `read_self` / `perceive`: live health, strength, focus, cooldowns). **No code change is needed for the fight estimate, the farm model, the danger map or the build to use the 3.1 numbers.** Verify once after rebuilding against the 3.1 SDK (T02 acceptance 1).

What *is* hard-coded and therefore wrong after the patch until re-tuned:

| Item | Where | Why the patch invalidates it | Fixed in |
|---|---|---|---|
| Draft priors (Ren 1.0, Stellar 0.95, Varg 0.62, Ryth 0.6, Prism 0.36, Tavi 0.33, Vendetta 0.3, Vesper 0.12, HoR `pd_hor_prior` 0.4) | `draft.cpp:328–344 prior()` | Tuned by the 17 October tournament on 3.0 values; three of our picks were nerfed, four enemy options buffed | T02 |
| Heart of Ruin at team size 3: +1.2, pair −0.5 | `draft.cpp:388–394` (`pd_hor3`) | HoR lost 25% strength and 14% landing damage | T02 |
| Counter to enemy bruisers: HoR +0.8 / pair −0.8 per Marcella, Vendetta, HoR (`pd_counter_hor`) | `draft.cpp:411–414` | Vendetta is a 1000-HP bruiser now and HoR is a weaker answer; Ryth / Varg are the tanks that still hold | T02 |
| "One ranged carry" synergy counts only Stellar | `draft.cpp:395–396` | Tavi (900 HP, 110 focus) now fills the role at least as well | T02 |
| Objective draft (Prism first, the ring) fires on heavy groups the ring cannot farm | `draft.cpp:316–318` + `brain.cpp:4006 ring_dps` | Unchanged by 3.1 but the buffed Prism/Tavi ring makes the objective plan worth fixing: the ring needs spell range ≥ camp range + 1, impossible on elk / golem / monolith groups (range 4 / 4 / 5 vs spell range 4) | T02 |
| `gold_rank_of`: Stellar and Prism 4, Tavi 3 | `brain.cpp:3883` | Stellar's focus per shard fell to 7, Tavi's is 10 with a higher base | T02 (inert while `gold_rank = 0`) |
| Comments that say "1.75 × focus" / "175 at base focus" | `params.h:286`, `brain.cpp:5352` | Now 1.5 × focus = 150; harmless in code (engine-derived) | T01 |
| ml2 danger model weights (`ML2_W_DIE8`, boosted trees) | `ml2_model.h`, `brain.cpp:2082` | Fitted on 3.0 games; Stellar's lower health shifts its death rate; needs re-fitting on 3.1 games | T15 (and `ml2_adapt` in T03 meanwhile) |
| Opponent-model priors (new in v9) | `opponent.h` | Set for a 3.1 ladder: bruiser invades and Prism/Tavi rings more likely | T05 |

### 1.3 Strategic consequences (both sides)

1. **Our standard team (Ren, Stellar, HoR / C&I) is weaker in every fight it chose on 3.0 numbers.** The fight estimate already knows (live stats), so the bot will fight *less* on its own; the draft must be re-balanced so we are not drafting the nerfed trio by inertia (T02), and the fight-model gaps that made us lose fights we should have won matter more (T01, T09).
2. **Enemy invaders are tougher** (Vendetta 1000 HP). Expect more INVADER / DEATHBALL opponents in the finals: detecting them early (T05), the DEFEND / EVADE presets (T06), region memory (T08) and bush-aware wards (T12) are the answer; the counter-pick is a tank (Ryth, Varg), no longer HoR (T02).
3. **Ring compositions (Prism + Tavi (+ Stellar)) are now strong on objective maps.** Drafting them only where the ring can actually run (T02 ring-range gate) and contesting an enemy ring's objective (CONTEST preset, `big_reward_dive`, T06) both gain value.
4. **A loaded Prism is a win condition and a liability.** Ours: keep the bag longer when nothing threatens it (T14 d), escort it (`escort_bag` preset), never leave it alone on their half. Theirs: a carrying Prism is the carrier to intercept *before* it loads (T10) and the one *not* to chase alone once loaded (the live-stat fight estimate already refuses; T09's shield / hidden-support terms keep that estimate honest).
5. **Gold farmers (Vesper, Marcella) are back.** The race projector and HUNT preset (T06) punish passive gold farmers if our fights go well; `pd_gold_vesper` is worth testing again for our own draft (T02).
6. **Everything else in this file is unchanged by the patch** — it fixes blindness (no opponent model, no shared vision, no region memory, no draft memory), not numbers.

---

## 2. Task index, priority and dependencies

| Id | Task | Why it wins games | Effort | Depends on | A/B |
|---|---|---|---|---|---|
| T01 | Count our own damaging dash in the fight estimate | Our Heart of Ruin undervalues itself by ~50 DPS (3.1) and walks home instead of trading | XS | – | optional (bug fix, default ON) |
| T02 | Re-tune the draft and champion tables for patch 3.1 | The draft is the first decision of the game and all its priors are 3.0 numbers | S (+ tournament) | – | required (draft tournament) |
| T03 | Flip 12 existing switches after A/B | Working code that is off: real enemy burst, endgame finishing, HoR/Ren passives, support-aware fights, team monolith, engine-chosen Power stat | S | – | required, per group |
| T04 | Shared memory v2: plan id, invasion flag, SIGHTING record | The team can share a plan and where the enemy is; foundation for T05–T08 | S | – | no (inert until T05/T08) |
| T05 | Opponent model (`opponent.h`) | Names the opponent's strategy within 20–40 rounds and detects a mid-match switch | M | T04 | no (inert until T06) |
| T06 | Plans and counter-presets in `update_mode()` | Turns the model's verdict into coherent counter-play through the existing knobs | M | T04, T05 | required |
| T07 | Draft memory: writer and reader (enemy composition prior, opening zones) | Every body knows the enemy draft and its opening zone from round 1 | S | T05 (for the prior) | required (zones) |
| T08 | Team influence map | Region memory of where the enemy is, team-wide, with age; replaces three ad-hoc risk terms | M | T04 | required |
| T09 | Fight-model completeness: shields, stuns, hidden support, farm-damage calibration | Fewer lost fights against Varg / HoR shields, deathballs and bush teams | M | T06 (plan for the hidden prior) | required |
| T10 | Carrier interception, tribute reachability, altar guard (DENY-ALTAR / ENDGAME roles) | Stops a 950-gem opponent; converts OPPORTUNITY alerts into kills | M | T04, T06, T09 | required |
| T11 | Non-stationary stance bandit | Forgets stale lessons, explores when the opponent changed | S | T05 | required |
| T12 | Ward placement by information gain | Vision where fights and invasions happen; bush ambushes revealed | S | T04, T08 | required |
| T13 | Robustness: watchdog fallback, guaranteed draft pick, exception report | A recurring exception no longer idles a champion for the whole game | S | – | no A/B needed |
| T14 | Small fixes: risky-bank herding, held spells after a flash sighting, seeded tie-breaks, Prism bag rule, dead knobs | Removes three cheap exploits, uses the Prism buff, deletes dead code | S | – | required (a–d) |
| T15 | Testing workflow, model fitting, ml2 re-fit on 3.1, pre-submission checklist | Every change above is measured; nothing ships untested | S | – | – |

**Recommended order:** T01 → T13 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T09 → T10 → T11 → T12 → T14, with T15 applied throughout. T01, T04, T13 can run in parallel; T05 and T07 can run in parallel once T04 is merged. T02's tournament can run in the background from day one.

---
## T01 — Count our own damaging dash in the fight estimate

**Goal.** `Brain::combat()` builds `my_burst` from the damage / stun / area / reset slots only (`brain.cpp:2180–2184`); our own damaging dash (Heart of Ruin, `kit.dash_mod > 0`) is missing, while `burst_vs()` (`brain.cpp:1699`), `build_react`'s `enemy_burst_seen` (`brain.cpp:741`) and `hor_threat` already count it (the enemy-side `Enemy::burst()` counts it only behind `burst_dash`, which is off and stays off). A Heart of Ruin therefore computes its DPS as `str + focus·best_mod/8` with no burst term, judges even fights as lost (3.0 worked example: adv 0.65 instead of 1.26) and retreats under fire instead of trading. On 3.1 the landing is 1.5 × focus = 150 at base; the omission is still ~50 DPS.

**Files.** `brain.cpp` (combat), `params.h` (switch), comments in `params.h:286` and `brain.cpp:5352`.

**Exact changes.**

1. `params.h`, end of `struct Params`:
```cpp
	// ---- v9 (patch 3.1 edition)
	int fix_my_dash = 1;	   // T01: combat()'s my_burst counts our own ready damaging dash (Heart of Ruin's landing, focus x dash_mod) like
						   // burst_vs() already does; 0 = v8 (a Heart of Ruin judged its fights without its main spell)
```
2. `brain.cpp:2184`, directly after `if (ready(kit.reset)) my_burst = std::max(my_burst, str);` add:
```cpp
	if (P.fix_my_dash && ready(kit.dash) && kit.dash_mod > 0.f)
		my_burst = std::max(my_burst, focus * kit.dash_mod); // Heart of Ruin: the landing hit is our fight spell (burst_vs counts it; combat did not)
```
3. Do **not** touch `ml2_features` (`brain.cpp:1880–1901`): `f[6]` keeps its trained definition (rule 0.2-4).
4. Comments only: `params.h:286` "1.75 x focus" → "1.5 x focus (3.1; engine-derived)"; `brain.cpp:5352` "175 at base focus" → "150 at base focus (3.1)".

**Acceptance criteria.**
- Builds warning-clean on both SDK variants.
- Under `#ifdef FIGHT_TRACE` (add a one-line `debug_block` print of `my_burst`, `our_dps`, `type` after `our_dps` is computed), a game with our Heart of Ruin shows `my_burst == focus * kit.dash_mod` (±0.01) whenever the dash is ready and `0`/spell value otherwise. For every other champion the print is unchanged versus v8.
- Rebuilt against the 3.1 SDK, `kit.dash_mod` reads 1.5 (print it once in `Brain::init()` under `LEGEND_TRACE`).

**Tests.** 100 games, our size-3 comp (Ren, Stellar, HoR) vs the proxy set, both sides: HoR fights chosen (`learner().on_fight` count, or `task == T_FIGHT` turns) up; HoR deaths per game not up by more than 10%; win rate ≥ baseline − 1 pt. No A/B is required to merge (bug fix), but record the numbers in the ledger (T15).

**Rollback.** `fix_my_dash = 0`.

---

## T02 — Re-tune the draft and champion tables for patch 3.1

**Goal.** Make the draft reflect the 3.1 champion values and the opponents 3.1 will produce, fix the objective draft so it only fires where the ring plan can run, and move every literal that the patch invalidated into a `params.h` knob so the tournament (T15) can set it without code edits. All numbers below are **provisional starting points**; the draft tournament decides the final values.

**Files.** `draft.cpp` (`analyse`, `derive_params`, `prior`, `pd_score`), `brain.cpp:3883 gold_rank_of`, `params.h`.

**Exact changes.**

1. `params.h`, end of `struct Params` (replace the three existing prior knobs' *values* in place, add the rest):
```cpp
	// T02: draft priors and bonuses re-opened for the 3.1 balance patch (Stellar / Heart of Ruin / Ren nerfed; Vesper, Vendetta, Tavi,
	// Prism buffed). Values below are provisional; tools/draft_tournament.py (T15.3) sets the final ones.
	// (double, not float: prior() and pd_score() compute in double, so the old literals stay bit-exact for the T02 acceptance diff)
	double pd_ren_prior = 0.95;		// was the literal 1.0 (Ren's stun damage 1.25 -> 0.75 x focus; tank and reflect unchanged)
	double pd_stellar_prior = 0.80;	// was 0.95 (health 750 -> 650, focus 85 -> 70, growth 9 -> 7)
	double pd_varg_prior = 0.66;	// was 0.62 (unchanged champion; relatively better)
	double pd_ryth_prior = 0.70;	// was 0.60 (unchanged; the tank that answers 1000-health Vendettas)
	double pd_prism_prior = 0.42;	// was 0.36 (passive 1 -> 1.5 focus per carried gem)
	double pd_tavi_prior = 0.50;	// was 0.33 (health 750 -> 900, focus 100 -> 110)
	double pd_vendetta_prior = 0.42;	// was 0.30 (health 800 -> 1000)
	double pd_vesper_prior = 0.30;	// was 0.12 (health 900 -> 1000, strength 50 -> 55)
	double pd_hor3_bonus = 0.9;		// was the literal 1.2 at team size 3 (strength 40 -> 30, landing 1.75 -> 1.5 x focus)
	double pd_hor3_pair_pen = 0.5;	// the pair's penalty at team size 3 (unchanged literal, now a knob)
	double pd_counter_tank = 0.2;	// Ryth (+) and Varg (+0.75 x) per enemy bruiser beyond the first: the tanks answer Vendetta / Marcella / HoR now
	int pd_caster_any = 1;			// 1: the "one ranged carry" synergy (+0.2 with no caster yet) counts Tavi as well as Stellar
	int pd_first_default = 0;		// first pick on default-type maps: 0 Ren (v8), 1 Varg, 2 Ryth (the tournament decides whether the nerfed Ren keeps the slot)
	int pd_obj_ring_range = 1;		// 1: the objective draft (Prism first) needs the heavy gem group's attacking camps to have range <= 3:
									// the ring stands at max camp range + 1 and every spell reaches 4, so elk / golem / monolith objectives
									// cannot be ring-farmed (brain.cpp ring_dps) and the caster draft then farms them with casters in front
```
   and change the existing values `pd_hor_prior = 0.4f` → `0.35f`, `pd_counter_hor = 0.8f` → `0.5f`, `pd_gold_vesper = 0.f` → `0.3f` (`params.h:253–257`).

2. `draft.cpp` `struct Features` (line 26): add `int gem_group_range = 0;` after `gem_group_de`.

3. `draft.cpp` `analyse()` (lines 77–112): track the heaviest gem group's largest attacking range. In the per-camp loop replace `ghp += c.base_stats().base_health;` by
```cpp
			const auto bs = c.base_stats();
			ghp += bs.base_health;
			if (bs.base_strength > 0 && bs.base_attack_range > grng)
				grng = static_cast<int>(bs.base_attack_range);
```
   declare `int grng = 0;` next to `int da = BIG, de = BIG, attackers = 0;`, and extend the heaviest-group assignment to
```cpp
		if ((has_gem || has_wolf || has_elk) && !has_mono && ghp > F.gem_group_hp)
			F.gem_group_hp = ghp, F.gem_group_att = attackers, F.gem_group_da = da, F.gem_group_de = de, F.gem_group_range = grng;
```

4. `draft.cpp` `derive_params()` (line 316): append one condition to `MP.objective`:
```cpp
		(!P.pd_obj_side || F.gem_group_de - F.gem_group_da > P.pd_obj_mid) && // pd_obj_side: ...
		(!P.pd_obj_ring_range || F.gem_group_range <= 3); // T02: the ring (spell range 4) only works outside wolf / cluster range 3
```

5. `draft.cpp` `prior()` (lines 328–344): replace the literals by the knobs:
```cpp
	case D::ren: return P.pd_ren_prior;
	case D::stellar: return P.pd_stellar_prior;
	case D::cassi_and_issac: return P.pd_ci_prior;
	case D::varg: return P.pd_varg_prior;
	case D::ryth: return P.pd_ryth_prior;
	case D::prism: return P.pd_prism_prior;
	case D::tavi: return P.pd_tavi_prior;
	case D::vendetta: return P.pd_vendetta_prior;
	case D::marcella: return 0.2;
	case D::vesper_vale: return P.pd_vesper_prior;
	case D_HOR: return P.pd_hor_prior;
	default: return 0.1;
```

6. `draft.cpp` `pd_score()`:
   - lines 388–394 (`pd_hor3` block): `v += 1.2;` → `v += P.pd_hor3_bonus;` and `v -= 0.5;` → `v -= P.pd_hor3_pair_pen;`.
   - lines 395–396: `if (c == D::stellar && casters == 0)` → `if ((c == D::stellar || (P.pd_caster_any && c == D::tavi)) && casters == 0)`.
   - directly after line 414 (`v -= P.pd_counter_hor * e_bruise;`) and **before** line 415 (`if (c == D::vesper_vale || c == D::marcella)`, whose body is line 416 — do not insert between those two), add:
```cpp
	// T02 (3.1): a 1000-health Vendetta or a Marcella is answered by a tank, not by the nerfed Heart of Ruin.
	if (c == D::ryth)
		v += P.pd_counter_tank * std::max(0, e_bruise - 1);
	if (c == D::varg)
		v += 0.75 * P.pd_counter_tank * std::max(0, e_bruise - 1);
```

7. `draft.cpp` `param_pick()` line 435: `const D first = pd_type == 2 ? D::prism : pd_type == 1 ? D::cassi_and_issac : D::ren;` → `const D first = pd_type == 2 ? D::prism : pd_type == 1 ? D::cassi_and_issac : (P.pd_first_default == 1 ? D::varg : P.pd_first_default == 2 ? D::ryth : D::ren);`

8. `brain.cpp:3883 gold_rank_of()`: move `CT::stellar` from the `return 4` group to the `return 3` group and `CT::tavi` from 3 to 4 (Prism stays 4). Inert while `gold_rank = 0`; documents the 3.1 ranking for when it is switched on.

**Acceptance criteria.**
- Builds; with every new knob at its *old* literal value (`pd_ren_prior 1.0`, `pd_stellar_prior 0.95`, …, `pd_hor3_bonus 1.2`, `pd_counter_tank 0`, `pd_caster_any 0`, `pd_obj_ring_range 0`, `pd_first_default 0`) the draft output is byte-identical to v8 on the 20 Nyx maps and the official maps (log `PD` lines under `LEGEND_FEATURES` for both builds and diff them). This proves the refactor is behaviour-preserving before the values change.
- With the new values: on a size-3 default map with no enemy picks the plan is still a 3-body team containing Ren (the first pick) and a caster; on an objective map whose heavy gem group contains an elk or golem the first pick is **no longer Prism** (type 0 or 1), on one whose heavy group is wolves + clusters it still is.
- After the tournament (T15.3) the knob values are replaced by its winners and the acceptance is re-run.

**Tests.** The draft tournament of T15.3 (≥ 8 candidate drafts × ≥ 40 maps × 2 sides, same bot code, forced drafts) on the 3.1 SDK; the composition-vs-composition matrix is the ground truth for the priors. Then the full A/B (Appendix A) of the new draft against the v8 draft.

**Rollback.** Set every knob back to the old literal (listed in the comments).

---

## T03 — Flip existing switches after A/B (no new logic)

**Goal.** Twelve features are implemented, tested in isolation on 3.0 and switched off. Flip them in groups, A/B each group (Appendix A), keep the winners. Two more are *not* flipped globally but by plan (T06): `big_reward_dive` (CONTEST) and `ward_bush_maps` (AMBUSH).

| Group | Switch (`params.h` line) | From → to | What it does (from its comment) | Gate / note |
|---|---|---|---|---|
| A fight model | `fm_mode` (314) | 0 → 7 | HoR's missing-health bonus on both sides, our Ren's retaliation, real camp ranges in `combat()`'s camp term | win rate; HoR/Ren deaths |
| A | `hor_threat` (317) | 0 → 3 | an enemy's ready damaging dash counts as a stunner for channel cancels and in `safety()`'s burst retreat | tributes cancelled by a landing; **do not** flip `burst_dash` (its comment: "the blunt burst_dash counted it everywhere and lost") |
| A | `mi_learn_burst` (141) | 0 → 1 | each enemy's biggest real one-round hit on us (items included) replaces the model while its spells are up | deaths to burst |
| A | `sup_mode` (329) | 1 → 7 | backup counted from weighted visible helpers only (no phantom claims); a body leaving a fight steps toward help that arrives within 3 rounds | isolated deaths |
| A | `chan_keep` (288) | 0 → 2 | a tribute with ≤ 2 turns left is not cancelled for a nearby stunner unless their damage kills us first | gems lost mid-channel |
| B endgame | `finish_race` (193) | 0 → 120 | with ≤ 120 gems needed, game-finishing groups are ranked by when their gems land on an altar | rounds from 880 banked to the win |
| B | `mi_endgame_bank` (145) | 0 → 100 | within 100 gems of the goal (either team) the bank threshold shrinks linearly | losses while holding ≥ the deficit in bags |
| C learning | `ml2_adapt` (658) | 0 → 0.02 | in-match logit offset of the danger model (re-centres it on this opponent and on 3.1 stats until T15 re-fits) | deaths; fights taken |
| C | `ml2_gb` (661) | 0 → 1 | boosted trees instead of the logistic (held-out AUC 0.829 vs 0.806) | **fuel**: log the worst turn on 100×100; keep only if < 60k fuel |
| C | `threat_map` (297) | 0 → 1 | enemy threat at a group by last sighting and age instead of the pain map | interim until T08 replaces both |
| D map | `mono_team` (239) | 0 → 1 | a lone monolith (20,000 HP, 200 gems + 300 gold) is a team target when `obj_team_ready` says the team clears it | contest-type maps only; A/B on them |
| E build | `tail_stat` (303) | 0 → 1 | the endless Power stat is chosen from the engine's growth values, not a typed champion list | patch-proof build; must pick focus for Stellar / Tavi / Prism / HoR and strength for Vendetta / Varg on 3.1 — print it once |

**Procedure.** One branch per group (`T03-A` … `T03-E`), all knobs of the group flipped together; if a group loses, bisect it (halve the set) until the losing knob is found; ship the winners. Each group: ≥ 300 games vs the baseline + ≥ 200 vs the proxy set (Appendix A).

**Acceptance criteria.** Each flipped knob has a ledger row (T15.1) with the A/B result; the final `params.h` carries the winners with the result quoted in the comment, in the existing style.

---

## T04 — Shared memory v2: plan id, invasion flag, SIGHTING record

**Goal.** Give the 8 bytes three things they lack: a team **plan id** (3 bits, written by body 0), an **"enemy seen on our half"** flag any body can raise, and a **SIGHTING** record (where the biggest enemy pack was seen) that is information, never a routing wall. Backward compatible: every existing reader keeps working; nothing changes in play until T05/T06/T08 consume the new fields.

**Layout after this task** (`comms.h` header comment must be updated to exactly this):

| Bits | v8 use | v9 use |
|---|---|---|
| bytes 0–5, bits 0–5 (or 0–6) | claim | unchanged |
| bytes 0–5, bit 6 | team bag sum (`team_bank`) | unchanged |
| bytes 0–1, bit 7 | stance (2 bits) | unchanged |
| byte 2, bit 7 | alert refresh toggle (`alert_refresh`, off) | **plan bit 0** — `alert_refresh` must stay 0 (enforced by `static_assert`) |
| bytes 3–4, bit 7 | unused | **plan bits 1–2** |
| byte 5, bit 7 | unused | **invaded flag** (any body sets, body 0 clears at window end) |
| bytes 6–7 | alert: bits 0–13 tile, 14–15 kind (1–3) | unchanged for kinds 1–3; **kind 0 with a non-zero value = SIGHTING**: bits 0–11 coarse cell `(y/2)·ceil(W/2) + x/2` (≤ 2,500 cells on 100×100), bits 12–13 pack size − 1 (1, 2, 3, 4+) |

**Files.** `comms.h`, `comms.cpp`, `brain.cpp` (`turn()`), `params.h`.

**Exact changes.**

1. `params.h`:
```cpp
	int sighting_mode = 0;	   // T04: 1 = post a SIGHTING record (biggest visible enemy pack, or any enemy on our half) in the alert slot's
						   // kind 0 when no alert is fresh, and raise the invaded flag; read by the opponent model (T05) and the influence map (T08)
	int v9_fuel_floor = 30000; // the v9 modules that cost fuel (influence map T08, interception T10, ward gain T12) skip their work below this much fuel left
```

2. `comms.h`, add to `enum AlertKind` a comment `// kind 0 with a non-zero raw value is a SIGHTING (see Sighting)`, and add before `struct Comms`:
```cpp
struct Sighting
{
	vec2 pos{ -1, -1 }; // top-left tile of the 2x2 cell
	int pack = 0;		// enemies seen together (1-4)
	int round = -1000;	// round this body first read it
};
```
   Add to `struct Comms` (after `int last_toggle = 0;`):
```cpp
	int plan = 0;							// T04: team plan id (PL_*, opponent.h), bit 7 of bytes 2-4; written by body 0
	bool invaded_flag = false;				// T04: bit 7 of byte 5 as read this turn
	std::array<Sighting, 4> sightings{};	// T04: the last SIGHTING records this body read (ring; newest at (sight_n - 1) % 4)
	int sight_n = 0;
	int last_sight_post = -1000;

	void write_plan(int p);
	void set_invaded();
	void clear_invaded();
	bool post_sighting(vec2 tile, int pack, int round);
	const Sighting* newest_sighting() const { return sight_n > 0 ? &sightings[static_cast<std::size_t>((sight_n - 1) % 4)] : nullptr; }
```

3. `comms.cpp` `Comms::read()`: replace the block from `stance = ...` to the end of the function with:
```cpp
	stance = ((b[0] >> 7) & 1) | (((b[1] >> 7) & 1) << 1);
	plan = ((b[2] >> 7) & 1) | (((b[3] >> 7) & 1) << 1) | (((b[4] >> 7) & 1) << 2);
	invaded_flag = ((b[5] >> 7) & 1) != 0;
	const std::uint16_t raw = static_cast<std::uint16_t>(b[6] | (b[7] << 8));
	const int toggle = P.alert_refresh ? (b[2] >> 7) & 1 : 0;
	if (raw != last_raw || toggle != last_toggle)
	{
		last_raw = raw;
		last_toggle = toggle;
		if ((raw >> 14) == AL_NONE)
		{
			// Kind 0: no alert, or a SIGHTING record (T04). Not an alert: fresh() stays false, alert_round is untouched.
			alert_kind = AL_NONE;
			if (raw != 0)
			{
				const int cw = (bc::map::width() + 1) / 2;
				const int cell = raw & 0xFFF;
				Sighting s;
				s.pos = { (cell % cw) * 2, (cell / cw) * 2 };
				s.pack = ((raw >> 12) & 3) + 1;
				s.round = round;
				sightings[static_cast<std::size_t>(sight_n % 4)] = s;
				++sight_n;
			}
		}
		else
		{
			alert_round = round;
			alert_kind = raw >> 14;
			const int tile = raw & 0x3FFF;
			const int w = bc::map::width();
			alert_pos = { tile % w, tile / w };
		}
	}
```
   Add the new functions:
```cpp
void Comms::write_plan(int p)
{
#ifndef LEGEND_RUNTIME_PARAMS // P is constexpr in submitted builds only
	static_assert(P.alert_refresh == 0, "T04: bit 7 of byte 2 is the plan's bit 0; alert_refresh's toggle would corrupt it");
#endif
	for (int i = 0; i < 3; ++i)
	{
		const auto k = static_cast<std::size_t>(2 + i);
		const std::uint8_t old = bc::shared_memory[k];
		const std::uint8_t bit = static_cast<std::uint8_t>(((p >> i) & 1) << 7);
		bc::shared_memory[k] = static_cast<std::uint8_t>((old & 0x7F) | bit);
	}
	plan = p;
}

void Comms::set_invaded()
{
	const std::uint8_t old = bc::shared_memory[5];
	if (!(old & 0x80))
		bc::shared_memory[5] = static_cast<std::uint8_t>(old | 0x80);
	invaded_flag = true;
}

void Comms::clear_invaded()
{
	const std::uint8_t old = bc::shared_memory[5];
	bc::shared_memory[5] = static_cast<std::uint8_t>(old & 0x7F);
	invaded_flag = false;
}

bool Comms::post_sighting(vec2 tile, int pack, int round)
{
	// Never over a live alert, at most every 3 rounds per body; cell 0 with pack 1 would read as "no alert", skip it.
	if (fresh(round, 6) || round - last_sight_post < 3)
		return false;
	const int cw = (bc::map::width() + 1) / 2;
	const int cell = (tile.y / 2) * cw + tile.x / 2;
	if (cell < 0 || cell > 0xFFF)
		return false;
	const std::uint16_t raw = static_cast<std::uint16_t>(((std::clamp(pack, 1, 4) - 1) << 12) | cell);
	if (raw == 0)
		return false;
	std::array<std::uint8_t, 2> b{ static_cast<std::uint8_t>(raw & 0xFF), static_cast<std::uint8_t>(raw >> 8) };
	bc::shared_memory.write(6, std::span<std::uint8_t>{ b });
	last_raw = raw; // our own post is not news to us
	last_sight_post = round;
	return true;
}
```
   `write_self` (`comms.cpp:40–50`) already preserves bit 7 of every byte (`v |= old & 0x80`); `write_bag` keeps it too (`old & ~0x40`); `write_stance` touches bytes 0–1 only; `post()` overwrites a sighting (intended: alerts outrank sightings). No change there.

4. `brain.cpp` `turn()`, inside the block that posts `AL_OPPORTUNITY` (after the `for (const auto& e : W.enemies) … C.post(AL_OPPORTUNITY, …)` loop, line 729), add:
```cpp
		if (P.sighting_mode)
		{
			// SIGHTING (T04): what we see is news for the team: the biggest visible pack (enemies within 4 of each other), or any
			// enemy on our half. Information for scoring and the opponent model, never a routing wall (the alert_zone wall lost in A/B).
			int best_pack = 0;
			vec2 best_pos{ -1, -1 };
			bool on_our_half = false;
			for (const auto& e : W.enemies)
			{
				if (!e.visible || !e.alive || W.enemy_spawn.is_set(e.pos))
					continue;
				int pack = 0;
				for (const auto& o : W.enemies)
					pack += o.visible && o.alive && cheb(o.pos, e.pos) <= 4;
				const bool ours = W.dist_home(e.pos) < W.dist_away(e.pos);
				on_our_half = on_our_half || ours;
				if (pack > best_pack || (pack == best_pack && ours && best_pos.x < 0))
					best_pack = pack, best_pos = e.pos;
			}
			if (on_our_half)
				C.set_invaded();
			if (best_pos.x >= 0 && (best_pack >= 2 || on_our_half))
				C.post_sighting(best_pos, best_pack, round);
		}
```

**Acceptance criteria.**
- `sighting_mode = 0`: shared-memory bytes written by the bot are byte-identical to v8 in a 200-round replay (dump `bc::shared_memory` each turn under `LEGEND_TRACE` for both builds and diff).
- `sighting_mode = 1`: a unit replay where body 1 sees two enemies at (10, 12) produces, on body 0's next read, `sightings[0] == { {10, 12}, 2, round }` and `alert_kind == AL_NONE`, `fresh(round, 6) == false`; a RALLY posted afterwards overwrites it and is read as before; a sighting is never posted while a RALLY / OPPORTUNITY / ESCORT is ≤ 6 rounds old.
- `write_plan(5)` followed by `read()` on another body gives `plan == 5`, claims and stance unchanged; `set_invaded()` / `clear_invaded()` round-trip through `invaded_flag`.
- The `static_assert` fires if `alert_refresh` is set to 1.

**Tests.** No A/B (inert alone). Fuel: the sighting block costs O(enemies²) ≤ 36 comparisons per turn.

**Rollback.** `sighting_mode = 0` (the plan bits stay 0 while T06 is off).

---
## T05 — Opponent model (`opponent.h`)

**Goal.** Body 0 (it runs every round, dead or alive) keeps a model of *what strategy the enemy is playing* from cheap signals, scores 20-round windows with a Naive-Bayes evidence table (Millington §7.5), smooths the evidence, detects jumps with a CUSUM change detector and switches archetype only with hysteresis — so a farmer that turns invader at round 300 is named INVADER within 20–40 rounds, and a single noisy window never flips the team. T06 turns the archetype into a plan. Inert while `plan_mode = 0`.

**Files.** New `opponent.h`, `opponent.cpp`; `brain.h`, `brain.cpp` (`init`, `turn`), `learn.h/.cpp` (one counter), `params.h`.

**Exact changes.**

1. `params.h`:
```cpp
	// T05 opponent model (body 0) and T06 plans
	int plan_mode = 0;			// 1: body 0 classifies the opponent every opp_window rounds and broadcasts a plan id (T04 bits); update_mode applies PRESET[plan]
	int opp_window = 20;		// rounds per evidence window
	float opp_hysteresis = 0.5f;	// a new archetype must beat the current one's smoothed log-evidence by this
	float opp_seed = 1.0f;		// log-evidence bias from the draft-memory composition hint (T07), decays x0.8 per window
	int opp_early_round = 80;	// "early contact" attribute: enemy within 10 of body 0 / a RALLY / a sighting on our half before this round
	int opp_scale_round = 300;	// "scaler" attribute: the biggest enemy burst seen grows x1.6 from this round on
	int plan_endgame_at = 850;	// either team banked this many: PL_ENDGAME (finish fast, guard their altar, hunt carriers)
	int plan_deny_at = 850;		// they banked this many and lead by plan_deny_lead: PL_DENY_ALTAR
	int plan_deny_lead = 60;
	int plan_hunt_farmer = 1;	// 1: a passive FARMER opponent is hunted (PL_HUNT) from round 150 when our fights go well
	int bandit_reset = 0;		// T11: 1 = an archetype switch resets the stance bandit's values and plays (shorter windows for a while)
```

2. `learn.h`: add `int ally_deaths_blind = 0;` under `ally_deaths_our_half` and declare `void reset_stance_values();` (T11 fills it in; until then it is this stub in `learn.cpp`):
```cpp
void Learner::reset_stance_values()
{
	q = { P.q0_spread, P.q0_grouped, P.q0_push };
	plays = {};
}
```
   In `learn.cpp` `Learner::tick`, in the ally-death loop, after `if (at.x >= 0) { … }` add `else ++ally_deaths_blind;` (a death whose place nobody saw: ambush evidence for the ledger and T15's labelling).

3. New `opponent.h`:
```cpp
// Opponent model (T05): what strategy is the enemy playing, and did it change? Body 0 keeps it (it runs every round, dead or
// alive), scores opp_window-round windows of cheap signals with a Naive-Bayes evidence table, smooths the evidence, detects
// jumps with a CUSUM and only then switches archetype; T06 maps the archetype to a team plan broadcast in shared memory (T04).
#pragma once
#include "common.h"
#include "params.h"
#include <array>

enum Arch : int { A_FARMER = 0, A_INVADER, A_DEATHBALL, A_OBJECTIVE, A_ALTAR, A_AMBUSH, A_RUSHER, A_SCALER, A_COUNT };
// 3 bits in shared memory (T04). PL_FARM = 0 is the v8 behaviour: with plan_mode 0 nothing is written and every body reads 0.
enum Plan : int { PL_FARM = 0, PL_DEFEND, PL_HUNT, PL_CONTEST, PL_EVADE, PL_DENY_ALTAR, PL_ENDGAME, PL_OPENING_SAFE, PL_COUNT };

struct OppModel
{
	static constexpr int NATTR = 9;
	// P(attribute = 1 | archetype), hand-set for a 3.1 ladder; replaced by counts from labelled games (T15.4).
	// attributes per window: 0 inv (>= 3 rounds with an enemy on our half), 1 pack (>= 3 enemies within 4 of each other),
	// 2 home (one of us died on our half), 3 bigbank (they banked >= 60), 4 alt (an enemy lock on one of our altars),
	// 5 bush (>= 2 hits from an unseen or bush-standing attacker), 6 obj (an objective group lost >= 400 health unclaimed),
	// 7 early (contact before opp_early_round), 8 scale (enemy burst x1.6 since opp_scale_round)
	static constexpr float PA[A_COUNT][NATTR] = {
		{ 0.10f, 0.10f, 0.05f, 0.60f, 0.05f, 0.05f, 0.10f, 0.05f, 0.20f }, // FARMER
		{ 0.80f, 0.40f, 0.60f, 0.30f, 0.30f, 0.20f, 0.15f, 0.40f, 0.30f }, // INVADER
		{ 0.60f, 0.85f, 0.50f, 0.30f, 0.20f, 0.15f, 0.30f, 0.40f, 0.40f }, // DEATHBALL
		{ 0.30f, 0.50f, 0.15f, 0.70f, 0.10f, 0.10f, 0.85f, 0.30f, 0.30f }, // OBJECTIVE
		{ 0.50f, 0.20f, 0.30f, 0.30f, 0.85f, 0.20f, 0.10f, 0.20f, 0.30f }, // ALTAR
		{ 0.50f, 0.30f, 0.50f, 0.30f, 0.20f, 0.85f, 0.15f, 0.30f, 0.30f }, // AMBUSH
		{ 0.60f, 0.50f, 0.40f, 0.20f, 0.15f, 0.15f, 0.20f, 0.90f, 0.20f }, // RUSHER
		{ 0.30f, 0.30f, 0.20f, 0.50f, 0.10f, 0.10f, 0.20f, 0.10f, 0.90f }, // SCALER
	};
	// Priors for 3.1: 1000-health Vendettas make invades and deathballs likelier, buffed Prism / Tavi make rings likelier.
	static constexpr float PRIOR[A_COUNT] = { 0.26f, 0.17f, 0.12f, 0.12f, 0.08f, 0.09f, 0.08f, 0.08f };

	// window counters (reset at every close)
	int win_start = 0, last_their = 0, bank_gems = 0;
	int inv_rounds = 0, max_pack = 0, deaths_home = 0, deaths_home0 = 0, locks_seen = 0, bush_hits = 0, obj_drops = 0, early_contact = 0;
	float burst_base = 0.f;				// enemy_burst_seen at opp_scale_round
	std::array<float, 16> obj_hp_prev{};	// last seen health of each objective group (-1 unknown), index = position in W.obj_groups
	// state
	std::array<float, A_COUNT> ll{}, bias{};	// smoothed log-evidence; draft-memory seed (decays)
	int windows = 0, arch = A_FARMER, arch_since = 0, arch_cand = -1, cand_windows = 0, last_switch = -1000, switches = 0;
	float cusum = 0.f, mean_contact = 0.f;
	int arch_plan = PL_FARM;			// the archetype's plan, recomputed at every window close

	void seed(int hint)
	{
		if (hint >= 0 && hint < A_COUNT)
			bias[static_cast<std::size_t>(hint)] += P.opp_seed;
	}
	bool changed_recently(int round) const { return round - last_switch <= 2 * P.opp_window; }
	float score(int a) const { return ll[static_cast<std::size_t>(a)] + bias[static_cast<std::size_t>(a)]; }
	bool close_window(int round, float burst_now, bool fights_ok); // true when the archetype switched (T11 resets the stance bandit)
	int plan_for_arch(int round, bool fights_ok) const;
};
```

4. New `opponent.cpp`:
```cpp
#include "opponent.h"
#include <cmath>

bool OppModel::close_window(int round, float burst_now, bool fights_ok)
{
	const bool x[NATTR] = { inv_rounds >= 3, max_pack >= 3, deaths_home >= 1, bank_gems >= 60, locks_seen >= 1, bush_hits >= 2,
		obj_drops >= 1, early_contact >= 1 && round <= P.opp_early_round, burst_base > 0.f && burst_now >= 1.6f * burst_base };
	for (int a = 0; a < A_COUNT; ++a)
	{
		float e = std::log(PRIOR[a]);
		for (int k = 0; k < NATTR; ++k)
			e += std::log(x[k] ? PA[a][k] : 1.f - PA[a][k]);
		const auto ai = static_cast<std::size_t>(a);
		ll[ai] = windows == 0 ? e : 0.6f * ll[ai] + 0.4f * e; // forget old windows (Millington §6.2.4)
	}
	// Change detector on the contact level: a jump away from its running mean allows a fast switch.
	const float contact = static_cast<float>(inv_rounds) + 2.f * static_cast<float>(max_pack) + 3.f * static_cast<float>(deaths_home);
	cusum = windows == 0 ? 0.f : std::max(0.f, cusum + std::fabs(contact - mean_contact) - 3.f);
	mean_contact = windows == 0 ? contact : 0.8f * mean_contact + 0.2f * contact;
	int top = 0;
	for (int a = 1; a < A_COUNT; ++a)
		if (score(a) > score(top))
			top = a;
	const int best = top != arch && score(top) > score(arch) + P.opp_hysteresis ? top : arch;
	if (best != arch)
	{
		cand_windows = best == arch_cand ? cand_windows + 1 : 1;
		arch_cand = best;
	}
	else
		cand_windows = 0, arch_cand = -1;
	const bool may_switch = cand_windows >= 2 || cusum > 6.f || round - arch_since >= 4 * P.opp_window;
	bool switched = false;
	if (best != arch && may_switch)
	{
		arch = best;
		arch_since = round;
		last_switch = round;
		++switches;
		cusum = 0.f;
		cand_windows = 0;
		arch_cand = -1;
		switched = true;
	}
	arch_plan = plan_for_arch(round, fights_ok);
	for (auto& b : bias)
		b *= 0.8f;
	++windows;
	win_start = round;
	bank_gems = 0;
	inv_rounds = max_pack = deaths_home = locks_seen = bush_hits = obj_drops = early_contact = 0;
	return switched;
}

int OppModel::plan_for_arch(int round, bool fights_ok) const
{
	switch (arch)
	{
	case A_INVADER: return PL_DEFEND;
	case A_DEATHBALL: return fights_ok ? PL_DEFEND : PL_EVADE;
	case A_OBJECTIVE: return PL_CONTEST;
	case A_ALTAR: return PL_DEFEND;		// the DEFEND preset lowers the escort threshold (T06)
	case A_AMBUSH: return PL_DEFEND;		// the DEFEND preset wards bushes everywhere (T06)
	case A_RUSHER: return round < P.mid_risk_until ? PL_OPENING_SAFE : PL_FARM;
	case A_SCALER: return fights_ok && round < 400 ? PL_HUNT : PL_FARM;
	default: return P.plan_hunt_farmer && fights_ok && round >= 150 ? PL_HUNT : PL_FARM;
	}
}
```

5. `brain.h`: `#include "opponent.h"`; private members `OppModel omodel; int plan = PL_FARM;` (not `opp`: `respond_to_alert` has a local `const bool opp`, `brain.cpp:3749`); private method `void opp_observe();`.

6. `brain.cpp` `Brain::init()`, before `inited = true;` (line 593): `omodel.obj_hp_prev.fill(-1.f); omodel.win_start = round; omodel.arch_since = round;` (T07 adds `omodel.seed(W.enemy_hint)` here).

7. `brain.cpp` `Brain::turn()`: call `opp_observe()` in **both** paths for body 0:
   - dead path (lines 658–675): directly after `learner().tick(round, W.my_index == 0, false);` add `if (P.plan_mode && W.my_index == 0) opp_observe();`
   - alive path: directly after the closing brace of the "Learning signals" block (the block that ends with the `AL_OPPORTUNITY` post and T04's sighting post, before `build_danger();` at line 731) add `if (P.plan_mode && W.my_index == 0) opp_observe();`. (It runs before `build_danger()`, so `in_awake_camp_range()` inside it reads last turn's `camp_danger` — the one that applied to the damage taken since then, which is what the "hits from the dark" signal needs.)

8. `brain.cpp`, new function (place after `learn_burst`):
```cpp
// T05: body 0 feeds the opponent model and broadcasts the plan. Exact signals from the global API (their banks, deaths), vision
// signals from its own eyes, the team's SIGHTING record and the invaded flag (T04). ~100 operations a turn.
void Brain::opp_observe()
{
	auto& W = world();
	auto& C = comms();
	auto& O = omodel;
	const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
	if (theirs > O.last_their)
		O.bank_gems += theirs - O.last_their;
	O.last_their = theirs;
	O.deaths_home = learner().ally_deaths_our_half - O.deaths_home0;
	bool inv = false; // this round, from our own eyes and the team's sighting; the invaded flag counts once per window (below)
	int pack = 0;
	if (alive)
	{
		for (const auto& e : W.enemies)
		{
			if (!e.visible || !e.alive || W.enemy_spawn.is_set(e.pos))
				continue;
			int p = 0;
			for (const auto& o : W.enemies)
				p += o.visible && o.alive && cheb(o.pos, e.pos) <= 4;
			pack = std::max(pack, p);
			inv = inv || W.dist_home(e.pos) < W.dist_away(e.pos);
			if (round <= P.opp_early_round && cheb(e.pos, pos) <= 10)
				O.early_contact = 1;
		}
		for (int i = 0; i < static_cast<int>(W.altars.size()); ++i)
			if (W.dist_home(W.altars[static_cast<std::size_t>(i)]) < W.dist_away(W.altars[static_cast<std::size_t>(i)]) && W.altar_locked_by_enemy(i))
			{
				++O.locks_seen;
				break;
			}
		// Hits from the dark: health lost with no awake camp in range and no visible enemy within 5, or from one standing in a bush.
		if (hp < last_hp - 0.5f && !in_awake_camp_range())
		{
			bool seen = false, bush = false;
			const auto& B = bc::map::bushes();
			for (const auto& e : W.enemies)
				if (e.visible && e.alive && cheb(e.pos, pos) <= 5)
					seen = true, bush = bush || B.is_set(e.pos);
			if (!seen || bush)
				++O.bush_hits;
		}
		// An objective group losing health while none of us claims it: someone else is farming it.
		if (W.obj_mode)
			for (std::size_t k = 0; k < W.obj_groups.size() && k < O.obj_hp_prev.size(); ++k)
			{
				const auto& g = W.groups[static_cast<std::size_t>(W.obj_groups[k])];
				if (g.seen_round != round)
					continue;
				bool claimed = false;
				for (int i = 0; i < 6; ++i)
					claimed = claimed || C.claim[static_cast<std::size_t>(i)] == g.id;
				if (O.obj_hp_prev[k] >= 0.f && !claimed && O.obj_hp_prev[k] - g.hp_total >= 400.f)
					++O.obj_drops;
				O.obj_hp_prev[k] = g.st == ST_ALIVE ? g.hp_total : -1.f;
			}
	}
	if (const Sighting* s = C.newest_sighting(); s && s->round == round)
	{
		const int dh = W.dist_home(s->pos), da = W.dist_away(s->pos);
		pack = std::max(pack, s->pack);
		inv = inv || dh < da;
		if (round <= P.opp_early_round && (dh < da || (dh < BIG && da < BIG && std::abs(dh - da) <= 10)))
			O.early_contact = 1; // contact on our half or around the midline counts; a pack deep on their half does not
	}
	if (C.fresh(round, 1) && C.alert_kind == AL_RALLY && round <= P.opp_early_round)
		O.early_contact = 1;
	O.inv_rounds += inv;
	O.max_pack = std::max(O.max_pack, pack);
	if (round == P.opp_scale_round)
		O.burst_base = std::max(1.f, enemy_burst_seen);
	int us = 0, them = 0;
	for (const auto& a : W.allies)
		us += a.alive;
	for (const auto& e : W.enemies)
		them += e.alive;
	const bool fights_ok = W.enemy_deaths >= W.ally_deaths && them <= us;
	if (round - O.win_start >= P.opp_window)
	{
		if (C.invaded_flag)
			O.inv_rounds += 2; // another body saw an enemy on our half this window: bounded evidence, not a round count
		const bool switched = O.close_window(round, enemy_burst_seen, fights_ok);
		O.deaths_home0 = learner().ally_deaths_our_half;
		C.clear_invaded();
		if (switched && P.bandit_reset)
			learner().reset_stance_values(); // T11: a new opponent, fresh stance values
#ifdef OPP_TRACE
		debug_block({ std::printf("OPP r=%d arch=%d plan=%d ll=%.2f/%.2f/%.2f/%.2f/%.2f/%.2f/%.2f/%.2f cusum=%.1f sw=%d\n", round, O.arch, O.arch_plan,
			O.score(0), O.score(1), O.score(2), O.score(3), O.score(4), O.score(5), O.score(6), O.score(7), O.cusum, O.switches); });
#endif
	}
	// The plan: score-triggered plans are checked every turn, archetype plans change at window close only.
	const int ours = static_cast<int>(bc::global_submitted_gems(team::ally));
	int pl = O.arch_plan;
	if (std::max(ours, theirs) >= P.plan_endgame_at)
		pl = PL_ENDGAME;
	if (theirs >= P.plan_deny_at && theirs > ours + P.plan_deny_lead)
		pl = PL_DENY_ALTAR;
	if (pl != C.plan || round % 10 == 0)
		C.write_plan(pl);
}
```
   `enemy_burst_seen` is maintained by the existing `build_react` block (`brain.cpp:738–741`, on while `build_react > 0`). `in_awake_camp_range()`, `last_hp`, `learner().ally_deaths_our_half`, `W.altar_locked_by_enemy()` exist.

**Acceptance criteria.**
- Builds; with `plan_mode = 0` no shared-memory byte differs from v8 (same diff test as T04).
- With `plan_mode = 1` and `sighting_mode = 1`, `OPP_TRACE` prints one line per 20 rounds from body 0 only, alive or dead.
- Scripted-opponent tests (Appendix A proxies, 30 games each): vs a pure farmer → `arch == A_FARMER` in ≥ 90% of windows after round 40; vs a round-1 invader → `A_INVADER` by round ≤ 60 in ≥ 80% of games; vs a switcher (farmer until round 300, invader after) → `A_INVADER` within 60 rounds of the switch in ≥ 80% of games; false switches vs the farmer ≤ 1 per game on average.
- `plan` bits: PL_ENDGAME from the turn either team reaches 850; PL_DENY_ALTAR when they lead by more than 60 at ≥ 850 (911–850 yes, 910–850 no).

**Tests.** No A/B alone (inert until T06). Fuel: measure `opp_observe()` on 100×100 (expect < 500).

**Rollback.** `plan_mode = 0`.

---

## T06 — Plans and counter-presets in `update_mode()`

**Goal.** Turn the plan id into coherent counter-play through the knobs the stance already re-tunes (fight margin, enemy-half penalty, deny bonus, bank size, isolation margin) plus five plan-only knobs (bush warding, grouping radius, escort threshold, reward-dive threshold, midline risk). The cascade itself is unchanged; a wrong plan costs a few points, a right one wins the match-up.

**Files.** `brain.h`, `brain.cpp` (`update_mode`, `bag_needs_escort`, `group_score`, `place_ward`), `params.h`.

**Exact changes.**

1. `brain.h`, after `int plan = PL_FARM;` (T05):
```cpp
	// T06 plan presets: effective values read by place_ward / group_score / bag_needs_escort (set in update_mode every turn)
	int ward_bush_eff = 0, group_r_eff = 0, escort_bag_eff = 0, dive_eff = 0;
	float mid_risk_eff = 0.f;
```

2. `opponent.h`, after `enum Plan` (brain.h includes it, so `update_mode()` and T10's role functions both see it):
```cpp
// T06: what kind of opponent we face (the plan from body 0) re-tunes the knobs the stance uses, plus five of its own.
// Columns: fight_add (fight_margin +), half_mult (enemy_half_penalty x), deny_add (deny_bonus +), bank_mult (tribute_min x),
// iso_add (isolated_fight_adv +), ward_bush (bush wards on every map), group_r (farm within this many tiles of allies' claims),
// escort_bag (escort threshold override, 0 = P.escort_bag), dive (big_reward_dive override, 0 = P.big_reward_dive),
// mid_risk (midline risk override while round < mid_risk_until, 0 = P.mid_risk), guard_altar / hunter (roles, T10).
struct Preset
{
	float fight_add, half_mult, deny_add, bank_mult, iso_add;
	int ward_bush, group_r, escort_bag, dive;
	float mid_risk;
	int guard_altar, hunter;
};
inline constexpr Preset PRESET[PL_COUNT] = {
	//  fight  half   deny   bank   iso   bush grp  esc  dive  mid   grd hunt
	{  0.0f, 1.0f,  0.00f, 1.0f,  0.0f,  0,   0,   0,    0,  0.f,  0, 0 }, // PL_FARM: baseline = v8
	{ +0.2f, 2.5f, -0.50f, 0.6f, +0.3f,  1,  10,  30,    0,  0.f,  0, 0 }, // PL_DEFEND: stay together on our half, bank small, ward bushes, escort bags
	{ -0.2f, 0.4f, +0.40f, 1.0f,  0.0f,  0,   0,   0,    0,  0.f,  0, 1 }, // PL_HUNT: their camps, their carriers, one hunter
	{  0.0f, 1.0f, +0.30f, 1.0f,  0.0f,  0,   8,   0,  150,  0.f,  0, 0 }, // PL_CONTEST: the team on the objective, deny big rewards
	{ +0.5f, 0.6f, +0.20f, 0.6f, +0.5f,  0,   0,  30,    0,  0.f,  0, 0 }, // PL_EVADE: no even fights, farm away from the ball, bank often
	{  0.0f, 1.0f,  0.00f, 0.8f,  0.0f,  0,   0,  30,    0,  0.f,  1, 0 }, // PL_DENY_ALTAR: a guard with a lock at their altar, escorted banks
	{  0.0f, 1.0f,  0.00f, 0.5f,  0.0f,  0,   0,  30,    0,  0.f,  1, 1 }, // PL_ENDGAME: finish, bank small, guard their altar, hunt carriers
	{  0.0f, 1.0f,  0.00f, 1.0f, +0.2f,  0,   8,   0,    0, 12.f,  0, 0 }, // PL_OPENING_SAFE: rusher opponent: side groups first, close to allies
};
```

3. `brain.cpp` `update_mode()`: after the `else if (stance == STANCE_PUSH) { … }` block (ends at line 3438) and before the `// Numbers: …` block, insert:
```cpp
	// T06: the opponent plan (body 0, opponent.h) on top of the stance; the scoreboard, deficit and race modifiers below still apply.
	plan = P.plan_mode ? std::clamp(comms().plan, 0, PL_COUNT - 1) : PL_FARM;
	{
		const Preset& pr = PRESET[static_cast<std::size_t>(plan)];
		fight_margin += pr.fight_add;
		enemy_half_penalty *= pr.half_mult;
		deny_bonus = std::max(0.f, deny_bonus + pr.deny_add); // never a negative deny bonus (GROUPED already halves it)
		tribute_min = std::max(10, static_cast<int>(static_cast<float>(tribute_min) * pr.bank_mult));
		isolated_fight_adv += pr.iso_add;
		ward_bush_eff = pr.ward_bush;
		group_r_eff = pr.group_r;
		escort_bag_eff = P.escort_bag <= 0 ? 0 : (pr.escort_bag > 0 ? std::min(P.escort_bag, pr.escort_bag) : P.escort_bag);
		dive_eff = pr.dive > 0 ? pr.dive : P.big_reward_dive;
		mid_risk_eff = pr.mid_risk > 0.f ? pr.mid_risk : P.mid_risk;
	}
```

4. Consumers (replace the `P.` read by the effective member; keep everything else):
   - `bag_needs_escort()` (`brain.cpp:3228–3249`): every `P.escort_bag` → `escort_bag_eff`.
   - `group_score()` line 4631: `P.big_reward_dive` → `dive_eff` (both occurrences on that line).
   - `group_score()` line 4648: `P.mid_risk` → `mid_risk_eff` (the condition and the term).
   - `group_score()` line 4681: `if (stance == STANCE_GROUPED && !claimers && …)` → `if ((stance == STANCE_GROUPED || group_r_eff > 0) && !claimers && …)`, and inside, `float rad = static_cast<float>(P.group_radius), fw = P.group_far_w;` → `float rad = static_cast<float>(group_r_eff > 0 ? std::min(P.group_radius, group_r_eff) : P.group_radius), fw = P.group_far_w;`.
   - `place_ward()` line 1785: `const int wb = (P.ward_bush_maps == 1 && !world().mono_mode) ? 0 : P.ward_bush;` → `const int wb = (P.ward_bush_maps == 1 && !world().mono_mode && !ward_bush_eff) ? 0 : P.ward_bush;`.

**Acceptance criteria.**
- `plan_mode = 0`: every effective member equals its `P.` source and the game log is identical to v8 (replay diff).
- `plan_mode = 1`, forced plans (temporary `#ifdef PLAN_FORCE` that overrides `plan`): DEFEND gives `enemy_half_penalty` ×2.5, `deny_bonus` −0.5 floored at 0, `tribute_min` ×0.6 (≥ 10), `escort_bag_eff = 30`, `ward_bush_eff = 1`; CONTEST sets `dive_eff = 150`; OPENING_SAFE sets `mid_risk_eff = 12` — verified by a `LEGEND_TRACE` print of the five members once per 50 rounds.

**Tests.** A/B (Appendix A) of `plan_mode = 1` (with T04 `sighting_mode = 1`) against the baseline on (a) the proxy set, (b) the scripted switcher proxies, both sides, ≥ 300 games each. Gate: ≥ baseline on (a) and ≥ +5 pts on (b). Then a magnitude pass: ES / coordinate search over the 6 non-baseline rows (one row at a time, ±50%) against the switcher proxies.

**Rollback.** `plan_mode = 0`.

---

## T07 — Draft memory: writer and reader (enemy composition prior, opening zones)

**Goal.** `play_draft()` returns before writing anything in the default path (`draft.cpp:515–525`) and no game code reads `bc::draft_memory`. Write a 1,024-byte record on every draft turn (the last write wins) with the enemy picks seen so far, a composition hint for the opponent model, and an **opening zone** per camp group; read it in `Brain::init()`. Removes the opening claim collisions (claims are read one round late) and seeds the opponent model before the first contact.

**Layout v1** (bytes; all others 0):

| Offset | Content |
|---|---|
| 0 | magic `0xB8` |
| 1 | version `1` |
| 2 | team size (`bc::draft::team_size()`, picks per team) |
| 3 | bodies: our picks expanded (Cassi & Issac = 2) + remaining picks counted as 1 each |
| 4–9 | our picks in pick order (`champion_draft` as uint8, `0xFF` = none) |
| 10–15 | enemy picks seen so far (`0xFF` = none; the enemy's last pick may be missing: the model fills it on sight) |
| 16 | enemy archetype hint (`Arch`, `0xFF` = none) |
| 20–275 | zone owner per camp group id (engine order): body index 0–5, `0xFF` = none / enemy half / unreachable |

**Files.** `draft.cpp`, `world.h`, `brain.cpp` (`init`, `group_score`), `params.h`.

**Exact changes.**

1. `params.h`:
```cpp
	int draft_mem = 0;		   // T07: 1 = the draft writes the v1 record above on every pick and init() reads it (zones, enemy hint)
	float zone_bonus = 0.10f;  // group_score: x (1 + zone_bonus) for the groups the draft assigned to this body while round < zone_until
	int zone_until = 150;
```

2. `draft.cpp`: `#include "opponent.h"` and, inside the anonymous namespace **after `is_front` (line 326, `enemy_hint` needs it) and before `param_pick` (line 422, which calls `write_draft_memory`)**, add:
```cpp
// T07: a composition hint for the opponent model from the enemy picks seen so far.
int enemy_hint(const std::vector<D>& enemy)
{
	int front = 0, bruiser = 0;
	bool prism = false, tavi = false, stellar = false;
	for (D c : enemy)
	{
		front += is_front(c);
		bruiser += c == D::vendetta || c == D::marcella || c == D_HOR;
		prism = prism || c == D::prism;
		tavi = tavi || c == D::tavi;
		stellar = stellar || c == D::stellar;
	}
	if (front >= 4)
		return A_DEATHBALL;
	if (front >= 3 && bruiser >= 1)
		return A_INVADER;
	if (prism && (tavi || stellar))
		return A_OBJECTIVE;
	return -1;
}

// T07: opening zones. Groups on our half, nearest to our spawn first, go to the body with the lightest load (camp health) with a
// pull toward the groups it already owns (Most Constrained first, Millington §3.7.8). Soft: group_score only multiplies by
// (1 + zone_bonus) for the owner until zone_until, so an imperfect partition costs nothing.
void plan_zones(std::array<std::uint8_t, 256>& owner, int bodies)
{
	owner.fill(0xFF);
	if (bodies <= 0)
		return;
	bodies = std::min(bodies, 6);
	const bc::bitboard walls = bc::map::walls() | bc::map::holes() | bc::map::altars();
	bc::distance_field home, away;
	bc::bitboard visited;
	home.compute(walls | bc::map::spawn_region(team::enemy), bc::map::spawn_region(team::ally), visited);
	away.compute(walls | bc::map::spawn_region(team::ally), bc::map::spawn_region(team::enemy), visited);
	struct ZG { int id, da; float hp; int cx, cy; };
	std::vector<ZG> gs;
	int id = 0;
	for (const auto& g : bc::map::camp_groups())
	{
		int da = BIG, de = BIG, n = 0;
		float hp = 0;
		long sx = 0, sy = 0;
		for (const auto& c : g.camps())
		{
			const vec2 p = c.spawn_position();
			const auto a = home.get(p), e = away.get(p);
			da = std::min(da, a == UNREACH ? BIG : static_cast<int>(a));
			de = std::min(de, e == UNREACH ? BIG : static_cast<int>(e));
			hp += c.base_stats().base_health;
			sx += p.x, sy += p.y, ++n;
		}
		if (id < 256 && n > 0 && da < BIG && da <= de)
			gs.push_back({ id, da, hp, static_cast<int>(sx / n), static_cast<int>(sy / n) });
		++id;
	}
	std::sort(gs.begin(), gs.end(), [](const ZG& a, const ZG& b) { return a.da < b.da || (a.da == b.da && a.id < b.id); });
	std::array<float, 6> load{};
	std::array<std::vector<const ZG*>, 6> mine{};
	for (const auto& g : gs)
	{
		int best = 0;
		float bs = 1e30f;
		for (int b = 0; b < bodies; ++b)
		{
			const auto bi = static_cast<std::size_t>(b);
			float near = 0.f;
			for (const ZG* o : mine[bi])
				near += static_cast<float>(std::max(std::abs(o->cx - g.cx), std::abs(o->cy - g.cy)));
			if (!mine[bi].empty())
				near /= static_cast<float>(mine[bi].size());
			const float s = load[bi] / 1000.f + 0.05f * near;
			if (s < bs)
				bs = s, best = b;
		}
		const auto bi = static_cast<std::size_t>(best);
		load[bi] += g.hp;
		mine[bi].push_back(&g);
		owner[static_cast<std::size_t>(g.id)] = static_cast<std::uint8_t>(best);
	}
}

// T07: write the record (every draft turn; the last write wins).
void write_draft_memory(const std::vector<D>& mine, const std::vector<D>& enemy)
{
	if (!P.draft_mem)
		return;
	try
	{
		std::array<std::uint8_t, 1024> m{};
		const int team = static_cast<int>(bc::draft::team_size());
		m[0] = 0xB8, m[1] = 1, m[2] = static_cast<std::uint8_t>(team);
		int bodies = 0;
		for (std::size_t i = 0; i < 6; ++i)
		{
			m[4 + i] = i < mine.size() ? static_cast<std::uint8_t>(mine[i]) : 0xFF;
			m[10 + i] = i < enemy.size() ? static_cast<std::uint8_t>(enemy[i]) : 0xFF;
			if (i < mine.size())
				bodies += mine[i] == D::cassi_and_issac ? 2 : 1;
		}
		bodies += std::max(0, team - static_cast<int>(mine.size())); // picks still to come: one body each
		m[3] = static_cast<std::uint8_t>(std::min(6, bodies));
		const int hint = enemy_hint(enemy);
		m[16] = hint < 0 ? 0xFF : static_cast<std::uint8_t>(hint);
		std::array<std::uint8_t, 256> owner{};
		plan_zones(owner, std::min(6, bodies));
		for (std::size_t i = 0; i < 256; ++i)
			m[20 + i] = owner[i];
		bc::draft_memory = m; // [VERIFY] same assignment form as draft.cpp:605; if the SDK wants a span, bc::draft_memory.write(0, m)
	}
	catch (...)
	{
	}
}
```
   Call it before **every** `bc::draft::pick(x)` in `param_pick` (lines 458, 462, 490) with the pick appended: e.g. at 490
```cpp
			{ std::vector<D> after = mine; after.push_back(c); write_draft_memory(after, enemy); }
			bc::draft::pick(c);
```
   (at 458 the pick is `D::cassi_and_issac`, at 462 `first`), and replace the old 4-byte write at lines 601–608 by `write_draft_memory(mine_after, bc::draft::current_draft(team::enemy))` with `mine_after = mine + pick`.

3. `world.h` `struct World`: add `std::array<std::uint8_t, 256> zone_owner{}; int enemy_hint = -1; int draft_bodies = 0;` (initialise `zone_owner.fill(0xFF)` in `World::init_units`).

4. `brain.cpp` `Brain::init()`, before `inited = true;`:
```cpp
	if (P.draft_mem)
	{
		// T07: the draft's record (a startup snapshot of the 1,024 bytes; read-only in play).
		try
		{
			const auto& dm = bc::draft_memory; // [VERIFY] is_empty() and operator[] (std::byte) per BotAPICpp.md
			if (!dm.is_empty() && static_cast<std::uint8_t>(dm[0]) == 0xB8 && static_cast<std::uint8_t>(dm[1]) == 1)
			{
				W.draft_bodies = static_cast<std::uint8_t>(dm[3]);
				const auto h = static_cast<std::uint8_t>(dm[16]);
				W.enemy_hint = h == 0xFF ? -1 : static_cast<int>(h);
				for (std::size_t i = 0; i < 256; ++i)
					W.zone_owner[i] = static_cast<std::uint8_t>(dm[20 + i]);
				for (std::size_t i = 0; i < 6; ++i) // T14c: the enemy draft varies the game seed (omit these two lines until T14 adds game_seed / mix32)
					game_seed = mix32(game_seed ^ (static_cast<std::uint32_t>(static_cast<std::uint8_t>(dm[10 + i])) << (i * 4)));
			}
		}
		catch (...)
		{
		}
		if (W.my_index == 0)
			omodel.seed(W.enemy_hint);
	}
```

5. `brain.cpp` `group_score()`: immediately before the `#ifdef XM_TRACE` block that precedes `if (P.finish_race > 0)` (line 4706), add:
```cpp
	if (P.draft_mem && P.zone_bonus > 0.f && round < P.zone_until && g.id >= 0 && g.id < 256 &&
		W.zone_owner[static_cast<std::size_t>(g.id)] == static_cast<std::uint8_t>(W.my_index))
		value *= 1.f + P.zone_bonus; // T07: the opening zone the draft assigned to this body
```

**Acceptance criteria.**
- `draft_mem = 0`: no draft-memory write in the default path (as v8), no read.
- `draft_mem = 1`: a `LEGEND_TRACE` dump in `init()` of bytes 0–19 and the first 16 zone owners matches what the draft printed under `LEGEND_FEATURES` on the same map; every group on our half has an owner < bodies, every enemy-half group `0xFF`; loads per body differ by at most the heaviest single group.
- Opening check on 10 maps: two bodies never claim the same group in rounds 1–20 (count from the shared-memory dump) in ≥ 90% of games (v8 baseline: measure first).
- `W.enemy_hint` equals `enemy_hint()` of the enemy picks visible at our last draft turn.

**Tests.** A/B of `draft_mem = 1` (zones) vs baseline, ≥ 300 games. Draft-turn fuel: `plan_zones` is one distance field pair + O(groups × bodies); log `bc::fuel_remaining()` at the end of the draft turn (the draft turn has 10× fuel).

**Rollback.** `draft_mem = 0`.

---

## T08 — Team influence map

**Goal.** One coarse grid (6×6-tile cells, ≤ 17×17 = 289 cells on 100×100) per body with two layers — *enemy influence* from every recent sighting (own eyes + the team's SIGHTING records, weighted by hp·dps and faded by age) and *our influence* from living allies (visible position or claimed group) — and `security = ours − enemy`. It replaces three ad-hoc risk terms in `group_score` (`enemy_round` +12, the `threat_map` block, the pain map), informs the altar choice and (T12) the ward site. Never a routing wall (that use lost in A/B).

**Files.** `brain.h`, `brain.cpp` (`turn`, new `build_influence`, `group_score`, `nearest_altar`), `params.h`.

**Exact changes.**

1. `params.h`:
```cpp
	// T08 team influence map (6x6 cells)
	int infl_mode = 0;			// bits: 1 group_score risk term (replaces enemy_round +12, threat_map and the pain term), 2 nearest_altar cost, 4 ward site (T12)
	int infl_every = 4;			// rebuild every this many rounds (anytime: a stale map is a few rounds old at most)
	int infl_memory = 40;		// sightings older than this are dropped
	int infl_radius = 3;		// cells around a source that receive its influence (3 cells = 18 tiles)
	int infl_max_src = 8;		// newest sources used (own sightings first, then SIGHTING records)
	float infl_scale = 60000.f;	// hp x dps units that count as "fully theirs" (one 1500-health, 80-dps enemy adjacent = 120,000)
	float infl_w = 20.f;		// group_score: rounds added at a fully enemy-controlled group
	float infl_altar_w = 8.f;	// nearest_altar: steps added at a fully enemy-controlled altar
	float infl_sight_unit = 100000.f;	// hp x dps assumed per enemy in a SIGHTING record (its stats are unknown)
	float infl_unseen_ally = 60000.f;	// hp x dps assumed for a living ally we cannot see (at its claimed group)
```
   (`v9_fuel_floor` was declared in T04.)

2. `brain.h`:
```cpp
struct Influence // T08
{
	static constexpr int CELL = 6, MAXC = 289;
	int cw = 0, ch = 0, built_round = -1000;
	std::array<float, MAXC> enemy{}, ours{};
	int idx(vec2 p) const { return (p.y / CELL) * cw + (p.x / CELL); }
	float security(vec2 p) const
	{
		const int i = idx(p);
		return cw > 0 && i >= 0 && i < cw * ch ? ours[static_cast<std::size_t>(i)] - enemy[static_cast<std::size_t>(i)] : 0.f;
	}
};
```
   and in `struct Brain`: `Influence infl; void build_influence();`.

3. `brain.cpp`, new function:
```cpp
// T08: enemy and own influence on a coarse grid from everything the team has seen lately (Millington §6.2).
void Brain::build_influence()
{
	auto& W = world();
	auto& C = comms();
	auto& IM = infl; // not `I`: brain.cpp:27 has `using I = bc::item_type`
	IM.cw = bc::map::width() / Influence::CELL + 1;
	IM.ch = bc::map::height() / Influence::CELL + 1;
	if (IM.cw * IM.ch > Influence::MAXC)
		return;
	IM.enemy.fill(0.f);
	IM.ours.fill(0.f);
	struct Src { vec2 pos; float w; int age; };
	std::array<Src, 16> src{};
	int ns = 0;
	for (const auto& e : W.enemies)
		if (e.alive && e.seen_round >= 0 && round - e.seen_round <= P.infl_memory && !W.enemy_spawn.is_set(e.pos) && ns < P.infl_max_src)
			src[static_cast<std::size_t>(ns++)] = { e.pos, e.hp * (e.str + e.focus * best_mod(e.kit) / 8.f), round - e.seen_round };
	for (const auto& s : C.sightings)
		if (s.round > -1000 && round - s.round <= P.infl_memory && ns < P.infl_max_src)
			src[static_cast<std::size_t>(ns++)] = { s.pos, P.infl_sight_unit * static_cast<float>(s.pack), round - s.round };
	auto splat = [&](std::array<float, Influence::MAXC>& layer, vec2 p, float w, int age) {
		const int cx0 = p.x / Influence::CELL, cy0 = p.y / Influence::CELL;
		const float af = 1.f / (1.f + (static_cast<float>(age) / 8.f) * (static_cast<float>(age) / 8.f));
		for (int cy = std::max(0, cy0 - P.infl_radius); cy <= std::min(IM.ch - 1, cy0 + P.infl_radius); ++cy)
			for (int cx = std::max(0, cx0 - P.infl_radius); cx <= std::min(IM.cw - 1, cx0 + P.infl_radius); ++cx)
			{
				const int d = std::max(std::abs(cx - cx0), std::abs(cy - cy0));
				layer[static_cast<std::size_t>(cy * IM.cw + cx)] += w * af / (1.f + static_cast<float>(d));
			}
	};
	for (int k = 0; k < ns; ++k)
		splat(IM.enemy, src[static_cast<std::size_t>(k)].pos, src[static_cast<std::size_t>(k)].w, src[static_cast<std::size_t>(k)].age);
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
	{
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (!a.alive || i == W.my_index)
			continue;
		vec2 p{ -1, -1 };
		float w = P.infl_unseen_ally;
		if (a.visible)
			p = a.pos, w = a.hp * (a.str + a.focus * best_mod(a.kit) / 8.f);
		else if (C.claim[static_cast<std::size_t>(i)] >= 0 && C.claim[static_cast<std::size_t>(i)] < static_cast<int>(W.groups.size()))
			p = W.groups[static_cast<std::size_t>(C.claim[static_cast<std::size_t>(i)])].center;
		if (p.x >= 0)
			splat(IM.ours, p, w, 0);
	}
	IM.built_round = round;
}
```
   In `turn()`, directly after `build_danger();` (line 731): `if (P.infl_mode && round - infl.built_round >= P.infl_every && bc::fuel_remaining() > static_cast<decltype(bc::fuel_remaining())>(P.v9_fuel_floor)) build_influence();`

4. `group_score()`:
   - line 4646: `if (round - g.enemy_round < 12)` → `if (!(P.infl_mode & 1) && round - g.enemy_round < 12)`.
   - line 4657: `if (P.threat_map)` → 
```cpp
	if (P.infl_mode & 1)
	{
		// T08: the team's picture of who controls the ground there, us arriving included.
		const float sec = infl.security(g.center) + hp * (str + focus * best_mod(kit) / 8.f);
		time += P.infl_w * std::clamp(-sec / P.infl_scale, 0.f, 1.f);
	}
	else if (P.threat_map)
```
   (the existing `else time += P.pain_w * …` branch stays as the final `else`).

5. `nearest_altar()` line 1300, after the `unsafe_altar` penalty:
```cpp
		if (P.infl_mode & 2)
			d += static_cast<int>(P.infl_altar_w * std::clamp(-infl.security(W.altars[i]) / P.infl_scale, 0.f, 1.f)); // T08: contested altars cost steps
```

**Acceptance criteria.**
- `infl_mode = 0`: identical logs to v8.
- A unit check under `LEGEND_TRACE`: with one visible enemy (1500 hp, 80 dps) at the centre of cell c, `infl.enemy[c] == 120000` (±1), the neighbouring cell `== 60000`, a cell 4 away `== 0`; 16 rounds later the same sighting gives `120000 / (1 + 4) = 24000`.
- Fuel: `build_influence()` measured on 100×100 with 8 sources ≤ 6,000 fuel per rebuild (≤ 1,500 per turn average, Appendix B; worst rebuild ≤ 10,000); if above, lower `infl_max_src` or `infl_radius` until it fits and record the numbers.
- Behaviour: in a replay where an ally died at group G 20 rounds ago with the killers last seen there, G's `time` carries `+infl_w × (≥ 0.5)` while an unseen group 30 tiles away carries 0.

**Tests.** A/B of `infl_mode = 3` (with `sighting_mode = 1`) vs baseline and vs `threat_map = 1` from T03-C, ≥ 300 games each.

**Rollback.** `infl_mode = 0`.

---
## T09 — Fight-model completeness: shields, stuns, hidden support, farm-damage calibration

**Goal.** Four blind spots of `combat()` that 3.1 makes more expensive: (a) **shields** — a Varg (2.5 × focus) or Heart of Ruin (1.5 × focus) self-shield is invisible to `Enemy::hp`, so a volley is judged lethal when it is not; (b) a **stunned** enemy is a free round; (c) **hidden support** — against a DEATHBALL / AMBUSH opponent the visible enemies are not all the enemies; (d) the **camp-damage model** never checks itself against what the camps actually did to us.

**Files.** `world.h`, `world.cpp` (`perceive`), `brain.h`, `brain.cpp` (`read_self`, `combat`, `turn`, `incoming_on`), `params.h`.

**Exact changes.**

1. `params.h`:
```cpp
	// T09 fight-model completeness
	int fm_buffs = 0;		   // bits: 1 shields (a visible unit's shield buff adds to its effective health, ours too), 2 a stunned enemy's damage counts x0.7 and 0 now
	float fm_hidden = 0.f;	   // > 0: under PL_DEFEND / PL_EVADE, unseen living enemies last seen <= 10 rounds ago within 12 + age tiles add this share of their health and damage
	float farm_ema = 0.f;	   // > 0: learning rate of a multiplier on incoming_on() from (health actually lost / predicted) on rounds spent in reach of every live camp, alone; clamp 0.7-1.5
```

2. `world.h` `struct Enemy`: append `float shield = 0.f; bool stunned = false; // T09: visible buffs` **after `cd`** (`Enemy` is aggregate-initialised with four values at `world.cpp:346`; trailing members keep their defaults). `world.cpp` `World::perceive`, after the cooldown loop (`e.cd[slot] = …`) and before `e.seen_round = round;`:
```cpp
		e.shield = 0.f, e.stunned = false;
		if (P.fm_buffs && e.ch)
		{
			try
			{
				const auto bf = e.ch->buffs();									// [VERIFY] unit::buffs() in BotAPICpp.md
				if (bf.has(bc::buff_types::shield))								// [VERIFY] the shield buff's type tag
					e.shield = std::max(0.f, bf.get<bc::buff_shield>().value);	// [VERIFY] the shield buff's remaining value
				e.stunned = bf.has(bc::buff_types::stun);						// [VERIFY] the stun buff's type tag
			}
			catch (...)
			{
			}
		}
```
   Fallback if the SDK exposes no buff reading: leave the four lines out and keep `fm_buffs = 0`.

3. `brain.h`: `float my_shield = 0.f;`. `brain.cpp` `read_self()`, after the `cd[s] = c;` loop: `my_shield = 0.f;` first (an expired shield must not linger), then the same block for `bc::self()` into `my_shield` (`try { const auto bf = bc::self().buffs(); if (bf.has(bc::buff_types::shield)) my_shield = …; } catch (...) {}`, gated by `P.fm_buffs & 1`).

4. `brain.cpp` `combat()`:
   - line 2174: `their_hp += w * e->hp;` → `their_hp += w * (e->hp + ((P.fm_buffs & 1) ? e->shield : 0.f));`
   - directly before `their_dps += w * dps * pm;` (line 2175): `if ((P.fm_buffs & 2) && e->stunned) dps *= 0.7f; // a stunned enemy loses the first round of a ~3-round exchange`
   - line 2176: `if (d <= reach_of(*e))` → `if (d <= reach_of(*e) && !((P.fm_buffs & 2) && e->stunned))`
   - line 2185: `float our_hp = hp,` → `float our_hp = hp + ((P.fm_buffs & 1) ? my_shield : 0.f),`
   - line 2392: `tgt->hp <= burst_vs(*tgt) + allies_burst;` → `tgt->hp + ((P.fm_buffs & 1) ? tgt->shield : 0.f) <= burst_vs(*tgt) + allies_burst;`
   - after the loop over `E` that accumulates `their_hp` / `their_dps` (i.e. just before `// Our side:` at line 2179):
```cpp
	if (P.fm_hidden > 0.f && (plan == PL_DEFEND || plan == PL_EVADE))
	{
		// T09 c: the model says they move as a pack / strike from hiding: enemies we lost sight of lately and that can be here count in part.
		for (const auto& e : W.enemies)
			if (e.alive && !e.visible && e.seen_round >= 0 && round - e.seen_round <= 10 && cheb(e.pos, pos) <= 12 + (round - e.seen_round))
				their_hp += P.fm_hidden * e.hp, their_dps += P.fm_hidden * (e.str + e.focus * best_mod(e.kit) / 8.f);
	}
```

5. Farm-damage calibration (d):
   - `brain.h`: `float incoming_on_raw(const Group& g) const; float farm_ema_v = 1.f, farm_pred = 0.f;`
   - `brain.cpp:3863`: rename the existing function body to `incoming_on_raw` and add
```cpp
float Brain::incoming_on(const Group& g) const
{
	return incoming_on_raw(g) * (P.farm_ema > 0.f ? farm_ema_v : 1.f);
}
```
   - `turn()`, alive path, directly after `W.perceive(pos); C.read(round);` (line 677–678):
```cpp
	if (P.farm_ema > 0.f)
	{
		// T09 d: what the camps did to us last round against what the model predicted (rounds spent in reach of every live camp of
		// our group, alone, no champion near, no heal). Millington §5.7.4: a model that measures its own error.
		if (farm_pred > 0.f && hp <= last_hp && enemies_within(6) == 0)
		{
			const float ratio = std::clamp((last_hp - hp) / farm_pred, 0.f, 3.f);
			farm_ema_v = std::clamp(farm_ema_v + P.farm_ema * (ratio - farm_ema_v), 0.7f, 1.5f);
		}
		farm_pred = 0.f;
	}
```
   - `turn()`, end, directly before `C.write_self(W.my_index, …)` (line 874):
```cpp
	if (P.farm_ema > 0.f && task == T_FARM && task_group >= 0 && task_group < static_cast<int>(W.groups.size()))
	{
		const auto& g = W.groups[static_cast<std::size_t>(task_group)];
		bool all_in_reach = g.st == ST_ALIVE && g.awake;
		for (std::size_t i = 0; i < g.camps.size() && all_in_reach; ++i)
			if (g.hp[i] > 0 && g.camps[i].str > 0)
				all_in_reach = cheb(g.camps[i].pos, pos) <= g.camps[i].range;
		for (int i = 0; i < static_cast<int>(W.allies.size()) && all_in_reach; ++i)
			if (i != W.my_index && W.allies[static_cast<std::size_t>(i)].alive && W.allies[static_cast<std::size_t>(i)].visible && cheb(W.allies[static_cast<std::size_t>(i)].pos, g.center) <= 5)
				all_in_reach = false; // a camp hits the nearest champion only: with an ally near, our share is not the model's
		if (all_in_reach)
			farm_pred = incoming_on_raw(g);
	}
```

**Acceptance criteria.**
- `fm_buffs = 0, fm_hidden = 0, farm_ema = 0`: logs identical to v8.
- `fm_buffs = 3`: a replay against a Varg that just shielded shows `their_hp` larger by the shield value in the `FIGHT_TRACE` print; a stunned enemy's `incoming` contribution is 0 that round; our own shield raises `our_hp`.
- `fm_hidden = 0.3` under a forced `PL_DEFEND`: an enemy seen 5 rounds ago 10 tiles away adds 0.3 × its hp / dps; a visible one adds nothing extra; an enemy seen 11 rounds ago adds nothing.
- `farm_ema = 0.05`: `farm_ema_v` stays within 0.7–1.5, updates only on qualifying rounds (print `farm_pred`, `last_hp - hp`, `farm_ema_v` under `LEGEND_TRACE` once per 20 rounds), and over a 2,000-round game of pure farming converges to a value within 0.85–1.15 (the model is roughly right).

**Tests.** A/B each of the three knobs separately (`fm_buffs = 3`; `fm_hidden = 0.3` with `plan_mode = 1`; `farm_ema = 0.05`), ≥ 300 games each. Gate per Appendix A; the shield knob is additionally checked against Varg- and HoR-heavy proxy drafts (deaths while attacking a shielded unit).

**Rollback.** The three knobs at 0.

---

## T10 — Carrier interception, tribute reachability, altar guard (DENY-ALTAR / ENDGAME roles)

**Goal.** Today a carrier is punished only when it is seen tributing (OPPORTUNITY); `gank_bag` is never read; `use_locks` only fires within 2 tiles by chance; nothing stops a 950-gem opponent except luck. Add: (a) **interception by prediction** of a visible carrier's path (Millington §3.3.8); (b) answer OPPORTUNITY tributes only when we can arrive before the channel lands; (c) a **guard** role under PL_DENY_ALTAR / PL_ENDGAME: the lowest-index living body stands (in a bush if possible) at the altar the enemy banks at and re-locks it — if it holds no lock it simply falls through to the normal cascade (locks are bought on spawn after the first emblem, `brain.cpp:1158`, so a lockless guard is rare after the opening); (d) a **hunter** role under PL_HUNT / PL_ENDGAME (the highest-index living body) that intercepts from farther. On 3.1 a loaded Prism is the carrier *not* to chase alone — the live-stat fight test in (a) refuses it.

**Files.** `brain.h`, `brain.cpp` (`turn`, `respond_to_alert`, new `hunt_carrier`, `guard_altar`, `predict_intercept`, `am_guard`, `am_hunter`), `params.h`. Depends on T04 (`v9_fuel_floor`), T06 (plan, `PRESET`) and T09 (`shield`).

**Exact changes.**

1. `params.h` (also change the existing `int gank_bag = 25;` comment to say it is now read by T10):
```cpp
	// T10 interception and altar guard
	int gank_mode = 0;		   // 1: hunt_carrier() intercepts a visible, alone, killable carrier with >= gank_bag gems within gank_r (gank_r_hunter for the hunter role)
	int gank_r = 8, gank_r_hunter = 14, gank_steps = 8;
	int opp_reach = 0;		   // 1: respond_to_alert answers an OPPORTUNITY tribute only if we arrive before it lands (remaining channel time)
	int opp_unseen_ticks = 8;  // ... channel length assumed for a tribute nobody sees any more
	int guard_mode = 0;		   // 1: guard_altar(): under a plan with guard_altar, the lowest-index living body with a lock holds their bank altar
```

2. `brain.h` members and methods:
```cpp
	// T10
	std::array<int, 8> altar_bank_hits{};	// enemy tributes seen per altar index (who banks where)
	std::array<bool, 6> prev_trib{};
	bool am_guard() const;
	bool am_hunter() const;
	vec2 predict_intercept(const Enemy& e, int& at_step) const;
	bool hunt_carrier();
	bool guard_altar();
```

3. `brain.cpp` `turn()`, alive path, after `W.perceive(pos); C.read(round);`:
```cpp
	if (P.gank_mode || P.guard_mode)
		for (std::size_t k = 0; k < W.enemies.size() && k < prev_trib.size(); ++k)
		{
			// T10: learn which altar they bank at (a tribute starting within 1 of it).
			const auto& e = W.enemies[k];
			const bool trib = e.visible && e.alive && e.tributing;
			if (trib && !prev_trib[k])
				for (std::size_t a = 0; a < W.altars.size() && a < altar_bank_hits.size(); ++a)
					if (cheb(e.pos, W.altars[a]) <= 1)
						++altar_bank_hits[a];
			prev_trib[k] = trib;
		}
```

4. New functions:
```cpp
bool Brain::am_guard() const
{
	auto& W = world();
	for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
		if (W.allies[static_cast<std::size_t>(i)].alive)
			return i == W.my_index; // the lowest living index
	return false;
}

bool Brain::am_hunter() const
{
	auto& W = world();
	int alive = 0, last = -1;
	for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
		if (W.allies[static_cast<std::size_t>(i)].alive)
			++alive, last = i;
	return alive >= 2 && last == W.my_index; // the highest living index, never the guard
}

// T10 a: where a carrier will be. It walks down the distance field of its nearest altar; the first predicted tile we reach no later
// than it (turn alternation gives us one step of slack) is the cut-off point.
vec2 Brain::predict_intercept(const Enemy& e, int& at_step) const
{
	auto& N = nav();
	auto& W = world();
	at_step = -1;
	int best_a = -1, bd = BIG;
	for (int a = 0; a < static_cast<int>(W.altars.size()); ++a)
	{
		N.ensure_altar(a);
		const int d = N.altar_dist(a, e.pos);
		if (d < bd)
			bd = d, best_a = a;
	}
	if (best_a < 0 || bd >= BIG)
		return { -1, -1 };
	vec2 p = e.pos;
	int dcur = bd;
	for (int j = 1; j <= P.gank_steps; ++j)
	{
		vec2 nxt = p;
		int nd = dcur;
		for (int dy = -1; dy <= 1; ++dy)
			for (int dx = -1; dx <= 1; ++dx)
			{
				if (!dx && !dy)
					continue;
				const vec2 q = p + vec2{ dx, dy };
				if (!bc::map::is_in_bounds(q) || W.walls.is_set(q))
					continue;
				const int d = N.altar_dist(best_a, q);
				if (d < nd)
					nd = d, nxt = q;
			}
		if (nxt == p)
			break;
		p = nxt, dcur = nd;
		if (cheb(p, pos) <= j + 1)
		{
			at_step = j;
			return p;
		}
	}
	return { -1, -1 };
}

bool Brain::hunt_carrier()
{
	if (!P.gank_mode || bc::fuel_remaining() < static_cast<decltype(bc::fuel_remaining())>(P.v9_fuel_floor))
		return false;
	auto& W = world();
	const bool hunter = PRESET[static_cast<std::size_t>(plan)].hunter && am_hunter();
	if (hp < 0.5f * max_hp || static_cast<int>(gems) >= 30 || task == T_CAPTURE || reward_here())
		return false;
	const int reach = hunter ? P.gank_r_hunter : P.gank_r;
	const Enemy* best = nullptr;
	int bd = BIG;
	for (const auto& e : W.enemies)
	{
		if (!e.visible || !e.alive || e.tributing || W.enemy_spawn.is_set(e.pos) || static_cast<int>(e.gems) < P.gank_bag)
			continue; // a tributing carrier is an OPPORTUNITY alert (respond_to_alert)
		const int d = cheb(e.pos, pos);
		if (d > reach || d < 2)
			continue;
		bool alone = true;
		for (const auto& o : W.enemies)
			alone = alone && (&o == &e || !o.visible || !o.alive || cheb(o.pos, e.pos) > 6);
		const float ours8 = 8.f * (str + focus * best_mod(kit) / 8.f) + burst_vs(e); // our damage over 8 rounds plus a spell
		if (!alone || e.hp + e.shield > ours8)
			continue; // a loaded Prism (3.1: +1.5 focus per gem) usually fails here: its live stats are in e.hp / burst_vs
		if (d < bd)
			bd = d, best = &e;
	}
	if (!best)
		return false;
	int at = -1;
	vec2 goal_tile = predict_intercept(*best, at);
	if (goal_tile.x < 0)
		goal_tile = best->pos; // no cut-off within gank_steps: chase directly (the existing fight / flee logic takes over in range)
	task = T_FIGHT;
	bc::bitboard goal;
	goal.draw_chebyshev(goal_tile, static_cast<float>(kit.attack_range));
	goal &= ~W.walls;
	return step(goal, true, true);
}

// T10 c: hold their bank altar with a lock. use_locks() (brain.cpp:1734) places the lock once we stand within 2 of an enemy-side
// altar without one, and again whenever an enemy starts a tribute there; five hits to clear it is five enemy turns.
bool Brain::guard_altar()
{
	if (!P.guard_mode || !PRESET[static_cast<std::size_t>(plan)].guard_altar || !am_guard())
		return false;
	auto& W = world();
	if (hp < 0.5f * max_hp || static_cast<int>(gems) >= 30 || task == T_CAPTURE || reward_here())
		return false;
	std::uint32_t locks = 0;
	try
	{
		locks = bc::self().consumables()[bc::consumable_type::altar_lock].count();
	}
	catch (...)
	{
		return false;
	}
	if (locks == 0)
		return false;
	// Their altar: the one they have banked at most often; before any sighting, the one nearest their spawn on foot.
	int best = -1, bh = -1, bd = BIG;
	for (int a = 0; a < static_cast<int>(W.altars.size()) && a < static_cast<int>(altar_bank_hits.size()); ++a)
	{
		const int h = altar_bank_hits[static_cast<std::size_t>(a)];
		const int d = W.dist_away(W.altars[static_cast<std::size_t>(a)]);
		if (d >= BIG)
			continue;
		if (h > bh || (h == bh && d < bd))
			bh = h, bd = d, best = a;
	}
	if (best < 0)
		return false;
	const vec2 at = W.altars[static_cast<std::size_t>(best)];
	bool locked = false;
	try
	{
		locked = bc::vision::has_altar_lock(at);
	}
	catch (...)
	{
	}
	if (locked && cheb(at, pos) <= 2)
		return false; // the lock stands: farm nearby until they clear it (deny_bonus keeps us on their half)
	bc::bitboard goal;
	goal.draw_chebyshev(at, 2.f);
	goal &= ~W.walls;
	bc::bitboard bush = goal & bc::map::bushes();
	try
	{
		bush &= ~bc::vision::wards(team::enemy); // [VERIFY] vision::wards(team) as a bitboard of enemy ward tiles; if it returns positions, clear each; if absent, skip
	}
	catch (...)
	{
	}
	if (!bush.is_empty())
		goal = bush;
	task = T_FIGHT;
	if (goal.is_set(pos))
		return true; // in position
	return step(goal, true, true);
}
```

5. Cascade (`turn()`, lines 806–811): after `respond_to_alert()` and before the `mono_fort` line:
```cpp
	if (!acted && (acted = hunt_carrier()))
		dbg_path = 10;
	if (!acted && (acted = guard_altar()))
		dbg_path = 11;
```

6. `respond_to_alert()`: first rename its local `const bool opp` (line 3749) to `const bool is_opp` (and its three uses in that function) so it cannot be confused with anything else; then (line 3757, after `const int d = cheb(C.alert_pos, pos);` and its range test), before `task = T_FIGHT;`:
```cpp
	if (is_opp && P.opp_reach)
	{
		// T10 b: only tributes we reach before they land. Visible: the engine's remaining channel time; unseen: an assumed bag minus the alert's age.
		int left = -1;
		for (const auto& e : world().enemies)
			if (e.alive && e.visible && e.tributing && cheb(e.pos, C.alert_pos) <= 1)
			{
				left = static_cast<int>((e.gems + 9) / 10) - (round - C.alert_round);
				try
				{
					if (e.ch)
						left = static_cast<int>(e.ch->remaining_channel_time()); // [VERIFY] champion::remaining_channel_time(); on absence keep the estimate
				}
				catch (...)
				{
				}
			}
		if (left < 0)
			left = P.opp_unseen_ticks - (round - C.alert_round);
		if (d - kit.attack_range > left + 1)
			return false;
	}
```

**Acceptance criteria.**
- All knobs 0: identical logs to v8.
- `predict_intercept` unit replay: carrier at 10 tiles walking to an altar whose path passes 4 tiles from us returns a tile on that path with `at_step ≤ 5`; a carrier walking away returns `{-1,-1}`.
- `gank_mode = 1`: a visible lone 25-gem carrier within 8 is chased (`dbg_path == 10`) only when `e.hp + shield ≤ ours8`; a loaded enemy Prism (focus > 150 live) is not chased by a body whose `ours8` is below its health.
- `guard_mode = 1`, forced `PL_DENY_ALTAR`: the lowest-index living body (when it holds a lock) walks to the enemy's most-used altar (or the one nearest their spawn), stands in a bush within 2 if one exists, and `use_locks()` places the lock on arrival; after an enemy clears it the guard re-locks if it has another lock.
- `opp_reach = 1`: an OPPORTUNITY 15 tiles away with 3 ticks left is ignored; one 5 tiles away with 3 ticks left is answered by a melee body (5 − 1 = 4 ≤ 3 + 1), one 6 tiles away is not.

**Tests.** A/B: `gank_mode = 1` alone; `opp_reach = 1` alone; `guard_mode = 1` with `plan_mode = 1` (the DENY/ENDGAME plans must be live) on the proxy set and on a proxy that banks big bags (≥ 60) regularly; ≥ 300 games each. Metric besides win rate: enemy gems banked in the last 200 rounds of games we were losing (must fall).

**Rollback.** The three knobs at 0.

---

## T11 — Non-stationary stance bandit

**Goal.** The stance bandit (`learn.cpp:58–160`) cannot explore (`ucb_c = 0`, `prior_pull = 0`) and never forgets: against a switching opponent it keeps a stale lesson for the rest of the game. Add a discount of old values, a short exploration bonus only while the opponent model says the world changed, and a reset with shorter windows on an archetype switch (Millington §6.2.4, §7.7).

**Files.** `learn.h`, `learn.cpp`, `brain.cpp` (`turn`), `params.h`.

**Exact changes.**

1. `params.h`:
```cpp
	// T11 non-stationary stance bandit
	float bandit_discount = 0.f;	// > 0: at every window close q *= (1 - bandit_discount) before the update (0.2: a window from 10 windows ago weighs 10%)
	float bandit_explore = 0.f;	// > 0: UCB exploration bonus added to ucb_c while the opponent model changed within 2 windows (0.3)
```
   (`bandit_reset` was added in T05.)

2. `learn.h`: `int short_windows = 0;` and the `tick` signature → `void tick(int round, bool leader, bool me_alive, bool opp_changed = false);`. Replace the T05 stub of `reset_stance_values()`:
```cpp
void Learner::reset_stance_values()
{
	q = { P.q0_spread, P.q0_grouped, P.q0_push };
	plays = {};
	short_windows = 4; // four half-length windows: learn the new opponent fast
	window_start = world().round;
	ours0 = static_cast<int>(bc::global_submitted_gems(team::ally));
	theirs0 = static_cast<int>(bc::global_submitted_gems(team::enemy));
	ally_deaths0 = ally_deaths, enemy_deaths0 = enemy_deaths, our_half0 = ally_deaths_our_half;
}
```

3. `learn.cpp` `Learner::tick`:
   - `if (round - window_start < P.learn_window) return;` → `if (round - window_start < (short_windows > 0 ? std::max(10, P.learn_window / 2) : P.learn_window)) return;`
   - directly before `q[si] += P.learn_rate * (r - q[si]);`: `if (P.bandit_discount > 0.f) for (auto& v : q) v *= 1.f - P.bandit_discount;`
   - the UCB line: `pref[s] += P.ucb_c * std::sqrt(…)` → `pref[s] += (P.ucb_c + (opp_changed ? P.bandit_explore : 0.f)) * std::sqrt(…)`
   - at the end of the window-close block (after `our_half0 = ally_deaths_our_half;`): `if (short_windows > 0) --short_windows;`

4. `brain.cpp`: both calls `L.tick(round, W.my_index == 0, true)` (line 710) and `learner().tick(round, W.my_index == 0, false)` (line 671) get a fourth argument `P.plan_mode && W.my_index == 0 && omodel.changed_recently(round)`.

**Acceptance criteria.**
- All three knobs 0 and `plan_mode = 0`: stance sequence identical to v8 on a replay.
- `bandit_discount = 0.2`: with a constant reward r the played value converges geometrically to `lr·r / (1 − (1−δ)(1−lr))` = 0.83 r for δ = 0.2, lr = 0.5 (the discount runs before the update, so the fixed point sits below r — intended: old evidence is worth less); the unplayed values decay toward 0 by ×0.8 per window.
- `bandit_reset = 1` + `plan_mode = 1`: on the window where `OPP_TRACE` reports a switch, `LEARN_TRACE` (add a one-line print of q, plays, window length at each close) shows q at the priors and four windows of 20 rounds.
- `bandit_explore = 0.3`: within 2 windows of a switch the less-played stances get a positive UCB term; afterwards none.

**Tests.** A/B of `bandit_discount = 0.2, bandit_explore = 0.3, bandit_reset = 1` with `plan_mode = 1` against the switching proxies and the stationary proxy set (the October note: `ucb_c = 0.3` cost 2 points against stationary proxies — the model-gated exploration must not).

**Rollback.** The three knobs at 0.

---

## T12 — Ward placement by information gain

**Goal.** `place_ward()` (`brain.cpp:1781–1853`) puts the ward 2 tiles toward the enemy spawn every 10 rounds unless a bush is in reach on lone-monolith maps. Choose instead, among 8 candidate tiles at distance 2, the one whose ward vision adds the most tiles we do not already see, weighted toward bushes, the midline and (T08) enemy-controlled cells. Bush-ambush teams ("48% of our champion deaths had a hitter in a bush") are revealed where it matters, and vision sits where invasions come from.

**Files.** `brain.cpp` (`place_ward`), `params.h`. Depends on T04 (`v9_fuel_floor`) and T08 (`infl.security`, `P.infl_mode`; the term is 0 while `infl_mode = 0`).

**Exact changes.**

1. `params.h`:
```cpp
	// T12 ward placement by information gain
	int ward_gain = 0;		   // 1: among 8 candidate tiles at distance 2, the ward goes where its vision adds the most unseen value
	int ward_range = 6;		   // ward vision radius (GameRules: 6) for the fallback when the SDK cannot compute a hypothetical ward's vision
```

2. `brain.cpp` `place_ward()`: after the bush block (the `if (bush.x >= 0) { … place at the bush … }` block that ends at line 1831) and **before** `const vec2 dir = sgn_step(pos, W.enemy_spawn_c);` (line 1832), insert:
```cpp
	if (P.ward_gain && bush.x < 0 && bc::fuel_remaining() > static_cast<decltype(bc::fuel_remaining())>(P.v9_fuel_floor))
	{
		// T12: information gain. Eight candidates two tiles out; each scores the tiles its ward would see that we do not see now,
		// bushes x3, the midline x4, enemy-controlled cells (T08) x3. Eight host calls per ward at most.
		static const vec2 dirs[8] = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 }, { 1, 1 }, { 1, -1 }, { -1, 1 }, { -1, -1 } };
		const auto& B = bc::map::bushes();
		int best_v = -1;
		vec2 best{ -1, -1 };
		for (const vec2 d : dirs)
		{
			const vec2 c = pos + d * 2;
			if (!bc::map::is_in_bounds(c) || W.walls.is_set(c) || W.camp_occ.is_set(c))
				continue;
			bc::bitboard seen;
			bool ok = false;
			try
			{
				seen = bc::ward::visible_tiles_from(c); // [VERIFY] hypothetical ward vision (shadowcast) from a tile; name per BotAPICpp.md
				ok = true;
			}
			catch (...)
			{
			}
			if (!ok)
			{
				seen.draw_chebyshev(c, static_cast<float>(P.ward_range));
				seen &= ~W.walls; // fallback: a plain radius (walls block nothing here; the gain is approximate)
			}
			int v = 0;
			for (int y = -P.ward_range; y <= P.ward_range; ++y)
				for (int x = -P.ward_range; x <= P.ward_range; ++x)
				{
					const vec2 t = c + vec2{ x, y };
					if (!bc::map::is_in_bounds(t) || !seen.is_set(t) || W.vis.is_set(t))
						continue;
					const int dh = W.dist_home(t), da = W.dist_away(t);
					const bool border = dh < BIG && da < BIG && std::abs(dh - da) <= 6;
					v += 1 + (B.is_set(t) ? 2 : 0) + (border ? 3 : 0) + ((P.infl_mode && infl.security(t) < 0.f) ? 2 : 0);
				}
			if (v > best_v)
				best_v = v, best = c;
		}
		if (best.x >= 0)
		{
			try
			{
				if (bc::self().place_ward(best))
				{
					ward_round = round;
					ward_pos = best;
					return;
				}
			}
			catch (...)
			{
			}
		}
	}
```
   (`W.vis` is the visible-tiles bitboard filled by `perceive`; the existing fallback candidates after this block stay as they are.)

**Acceptance criteria.**
- `ward_gain = 0`: identical ward tiles to v8.
- `ward_gain = 1`: in a replay next to a bush cluster on the midline the chosen tile's `v` is the maximum of the 8 (print the 8 values once under `LEGEND_TRACE`); the ward is never placed on a wall / camp tile; fuel per placement ≤ 15,000 (8 host calls + 8 × 169 tile checks); at most one placement per 10 rounds as before.

**Tests.** A/B `ward_gain = 1` vs baseline (≥ 300 games) and vs a bush-ambush proxy (deaths with an unseen attacker — `learner().ally_deaths_blind` — must fall).

**Rollback.** `ward_gain = 0`.

---
## T13 — Robustness: watchdog fallback, guaranteed draft pick, exception report

**Goal.** `main.cpp` swallows every exception (`catch (...) {}`) and 30 more `catch (...)` sit inside `brain.cpp`: a recurring throw (a new SDK behaviour, an odd map) idles a champion every turn for the whole game with no report. Count failures, and after `P.watchdog` consecutive failed turns run a minimal safe turn from raw reads; never leave a draft slot to the random fallback. *No A/B needed.*

**Files.** `main.cpp`, `brain.h`, `brain.cpp`, `draft.cpp`, `params.h`.

**Exact changes.**

1. `params.h`:
```cpp
	int watchdog = 3;		   // T13: after this many consecutive failed turns (an exception escaped Brain::turn) run safe_fallback(); 0 = v8 (idle silently)
```

2. `main.cpp`:
```cpp
// Entry point: dispatch draft and gameplay; a failed turn is swallowed and still yields; a run of failed turns degrades to a safe turn (T13).
#include "brain.h"
#include "draft.h"
#include "params.h"
#include <cstdio>

int main()
{
	int fails = 0;
	while (true)
	{
		try
		{
			if (bc::is_draft())
				play_draft();
			else
				brain().turn();
			fails = 0;
		}
		catch (...)
		{
			++fails;
#ifdef LEGEND_TRACE
			debug_block({ std::printf("EXC r=%u fails=%d\n", bc::round_number(), fails); });
#endif
			if (P.watchdog > 0 && fails >= P.watchdog && !bc::is_draft())
			{
				try
				{
					brain().safe_fallback();
				}
				catch (...)
				{
				}
			}
		}
#ifdef LEGEND_TRACE
		debug_block({
			const auto left = bc::fuel_remaining();
			if (!bc::is_draft() && left < 15000)
				std::printf("FUEL low r=%u left=%llu\n", bc::round_number(), static_cast<unsigned long long>(left));
		});
#endif
		bc::end_turn();
	}
}
```

3. `brain.h`: `void safe_fallback();` in the **`public:`** section of `class Brain`, next to `void turn();` (`brain.h:35`) — every other method is private and `main.cpp` calls this one. `brain.cpp` (place after `read_self`):
```cpp
// T13: a minimal turn from raw reads, used only after P.watchdog consecutive failed turns. Channeling: wait. Gems next to an
// altar: submit. Hurt: recall. Otherwise one step toward our spawn. Nothing here touches World or Nav state that may be broken.
void Brain::safe_fallback()
{
	bc::detail::champion_info i{};
	if (bc::detail::sdk_champion(self, &i) != 0 || !flag(i.state, bc::champion_state::alive))
		return;
	if (flag(i.state, bc::champion_state::recalling) || flag(i.state, bc::champion_state::submitting_gems) || flag(i.state, bc::champion_state::teleporting))
		return;
	const vec2 p{ i.x, i.y };
	std::uint32_t g = 0;
	bc::detail::sdk_champion_gems(self, &g);
	if (g > 0 && inited)
	{
		for (const vec2 a : world().altars)
			if (cheb(a, p) <= 1)
			{
				try
				{
					bc::self().submit_gems(a);
					return;
				}
				catch (...)
				{
				}
			}
	}
	if (i.health < 0.5f * i.max_health)
	{
		try
		{
			bc::self().recall();
			return;
		}
		catch (...)
		{
		}
	}
	if (inited)
	{
		try
		{
			bc::self().move_towards(world().ally_spawn_c);
		}
		catch (...)
		{
		}
	}
}
```

4. `draft.cpp` `play_draft()`: hoist the `fallback[]` list (line 594) above `if (!found)`, and replace the final `bc::draft::pick(pick);` (line 609) with
```cpp
	bool picked = false;
	try
	{
		bc::draft::pick(pick);
		picked = true;
	}
	catch (...)
	{
	}
	if (!picked)
		for (auto f : fallback)
			if (std::find(mine.begin(), mine.end(), f) == mine.end())
			{
				try
				{
					bc::draft::pick(f);
					break;
				}
				catch (...)
				{
				}
			}
```

**Acceptance criteria.**
- Inject a `throw 1;` at the top of `Brain::turn()` under a temporary `#ifdef FAULT_TEST`: with `watchdog = 3` the champion, from its 3rd turn, submits when next to an altar with gems, recalls when below 50%, otherwise walks home; `EXC` lines appear under `LEGEND_TRACE`. With `watchdog = 0` it idles (v8).
- Inject a throw in `bc::draft::pick` (wrap it in a temporary test shim): the draft still makes a legal pick every round.
- Without faults, logs are identical to v8.

---

## T14 — Small fixes: risky-bank herding, held spells after a flash sighting, seeded tie-breaks, Prism bag rule, dead knobs

**Files.** `brain.cpp` (`build_danger`, `tribute`, `group_score`, `place_ward`, `update_mode`, `init`), `brain.h`, `params.h`.

### a) Risky-bank herding (exploit: an enemy that shows itself near our camps every ~15 rounds makes every farmer with 10+ gems walk to an altar)
- `params.h`: `int risky_persist = 0; // T14a: the "risky" bank (tribute_risky) needs an enemy within 9 for this many consecutive rounds (or health < 60%); 0 = v8 (one sighting)`
- `brain.h`: `int enemy_near_rounds = 0;`
- `build_danger()`, at the end of the enemy loop (after line 1229): `enemy_near_rounds = enemy_near_field ? enemy_near_rounds + 1 : 0;`
- `tribute()` line 3641: `const bool risky = enemy_near_field && static_cast<int>(gems) >= P.tribute_risky;` → `const bool risky = enemy_near_field && static_cast<int>(gems) >= P.tribute_risky && (P.risky_persist <= 0 || enemy_near_rounds >= P.risky_persist || hp < 0.6f * max_hp);`
- A/B `risky_persist = 2`.

### b) Held spells after a flash sighting (exploit: one sighting at 9 tiles mutes camp casts for up to 4 rounds)
- `params.h`: `int near_age_cap = 0; // T14b: build_danger: a sighting's age shortens enemy_near_d by at most this many tiles (the camp-cast hold hold_spell_dist reads it); 0 = v8 (unbounded)`
- `build_danger()` line 1228: `enemy_near_d = std::min(enemy_near_d, std::max(0, ed - age));` → `enemy_near_d = std::min(enemy_near_d, std::max(0, ed - (P.near_age_cap > 0 ? std::min(age, P.near_age_cap) : age)));`
- A/B `near_age_cap = 3`.

### c) Seeded tie-breaks (exploit: a replayed opponent pre-positions for our deterministic first targets and ward tiles)
- `params.h`: `float score_jitter = 0.f; // T14c: group_score x (1 ± score_jitter) by a per-game hash of (group, 50-round epoch); 0 = v8 (deterministic)`
- `brain.h`: `std::uint32_t game_seed = 0; static std::uint32_t mix32(std::uint32_t x) { x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16; return x; }`
- `init()`, before T07's draft-memory block: `game_seed = mix32(static_cast<std::uint32_t>(bc::map::width()) * 73856093U ^ static_cast<std::uint32_t>(bc::map::height()) * 19349663U ^ static_cast<std::uint32_t>(W.allies.size() + 7 * W.enemies.size()));` — T07's reader then folds the six enemy-pick bytes in (the loop shown in T07 step 4), so the seed differs per opponent draft; it is the same on every body of a team (the index is deliberately left out), so ward and target choices vary per game, not per body.
- `group_score()`, next to T07's zone bonus (before the `#ifdef XM_TRACE` block at line 4706): `if (P.score_jitter > 0.f) value *= 1.f + P.score_jitter * (static_cast<float>(mix32(game_seed ^ static_cast<std::uint32_t>(g.id) * 2654435761U ^ static_cast<std::uint32_t>(round / 50) * 40503U) % 2001U) / 1000.f - 1.f);`
- `place_ward()` fallback candidates (line 1833 `const vec2 cands[] = …`): start the loop at index `mix32(game_seed ^ static_cast<std::uint32_t>(round)) % 4` and wrap around (same 4 tiles, rotated order) — gated by `P.score_jitter > 0.f`.
- A/B `score_jitter = 0.02` (must be neutral vs the proxies; its value is against replay-based pre-positioning, which no proxy does).

### d) Prism bag rule (3.1: +1.5 focus per carried gem)
- `params.h`: `float prism_bank_mult = 1.f; // T14d: a Prism's bank threshold x this while no enemy is near (enemy_near_d > 12) and we are not losing the race: the bag is power (3.1 passive); capped at 55 gems`
- `update_mode()`, at the very end (after the Cassi / Issac `pair_caution` block): 
```cpp
	if (P.prism_bank_mult > 1.f && type == CT::prism && !enemy_near && enemy_near_d > 12 && race_state != 2)
		tribute_min = std::min(55, static_cast<int>(static_cast<float>(tribute_min) * P.prism_bank_mult)); // T14d: a loaded Prism hits harder (3.1)
```
   (`build_danger()` runs before `update_mode()` in `turn()`, so `enemy_near` / `enemy_near_d` are current.)
- A/B `prism_bank_mult = 1.5` on objective maps (where Prism is drafted) and on the whole set.

### e) Dead knobs
- Delete `join_bonus` (`params.h:17`) and `o2_ring_melee` (`params.h:537`) after confirming with `grep -n "join_bonus\|o2_ring_melee" *.cpp *.h` that nothing reads them. Training builds (`LEGEND_RUNTIME_PARAMS`, a generated `params_rt.cpp`) must drop the two fields too — the one exception to rule 0.2-1. `gank_bag` (`params.h:591`) is read by T10 — update its comment. The `draft_model` / `draft_table.h` path stays (inert, documented).

**Acceptance criteria.** All knobs at their v8 values → identical logs. Each knob: the described effect visible in a `LEGEND_TRACE` replay (a: a 1-round sighting no longer sets `risky`; b: `enemy_near_d` ≥ `ed − 3`; c: two games with different enemy drafts on the same map pick different first wards; d: a Prism with no enemy within 12 shows `tribute_min` × 1.5, ≤ 55).

**Tests.** A/B per knob (a, b, d ≥ 300 games; c neutrality check ≥ 300 games).

---

## T15 — Testing workflow, model fitting, ml2 re-fit on 3.1, pre-submission checklist

### 15.1 The ledger
Keep `LEDGER.md` next to `src/`: one row per experiment — date, branch, knob values, opponent set, games, win rate with 95% CI, deaths / kills / gems per game, worst-turn fuel, decision. Every A/B in this file lands there before its branch is merged. `params.h` comments quote the ledger row (the existing style: "A/B: 56.2 vs 55.4").

### 15.2 A/B protocol (Appendix A has the script)
1. **Builds.** Baseline = the last merged build; candidate = baseline + the knob(s) under test. Both compiled against the **3.1** SDK.
2. **Opponent set.** (i) the baseline itself (mirror); (ii) the proxy set — builds of GOD with forced parameter profiles (see 15.3 for the switcher hook): *farmer* (`enemy_half_penalty 40, fight_margin 2.0, deny_bonus 0`), *invader* (`enemy_half_penalty 0, deny_bonus 2.0, fight_margin 0.9, race_mode 0`), *deathball* (`style 1`, the existing team-style switch at `params.h:396`, plus the invader profile), *altar-denier* (invader profile; add a temporary hook that sends the lowest index to our spawn-nearest altar with a lock from round 150), *bush-ambush* (`ward_bush_maps 0`, `hold_spells_near_enemies 1`, invader profile, `engage_angle` off), *ring* (forced draft `LEGEND_DRAFT` = Prism, Tavi, Stellar with `obj_plan` on), *switcher* (farmer until round 300, invader after; and the reverse); (iii) any external bots available (ladder replays' authors' bots if provided).
3. **Maps.** The official maps + the 20 ladder maps + 20 generated (sizes 30×80 to 100×100, team sizes 3–5), both sides each.
4. **Size.** ≥ 300 games per opponent set for a knob (≥ 600 for a group of knobs); the Wilson 95% interval must exclude a loss of more than 1.5 points before a change ships.
5. **Metrics** (all from the `LEGEND_TRACE` `T` lines and the end-of-game summary): win rate; banked gems at end (both); our deaths and kills; gems lost in bags on death; rounds to 1,000 when winning; worst turn fuel; exceptions (`EXC` lines, T13); for T05: archetype time-to-detect and false switches (`OPP` lines); for T10: enemy gems banked in the last 200 rounds of lost games.
6. **Decision.** Ship if win rate ≥ baseline − 1.5 on every set **and** ≥ +2 on at least one, no new exceptions, worst-turn fuel < 80,000. Otherwise bisect (for groups) or drop.

### 15.3 Draft tournament for 3.1 (settles T02)
1. Build GOD with `LEGEND_DRAFT` forced compositions (the existing hook, `draft.cpp:537–551`): the 8 candidates = the 6 `COMPS` rows + {Ren, Varg, Ryth(+Stellar, +Tavi)} + {Ren, Tavi, Ryth(+Varg, +C&I)} at sizes 3, 4, 5.
2. Round robin on ≥ 40 maps × 2 sides (≥ 2,500 games, as the 17 October run). Record the matrix.
3. Set the T02 priors so that `pd_score` reproduces the tournament's ranking when the enemy is unknown: a prior = mean win rate of the drafts containing the champion, rescaled so Ren's (or the best champion's) is 1.0. Set `pd_counter_tank`, `pd_counter_hor` from the matrix rows against bruiser-heavy drafts; `pd_hor3_bonus` from the size-3 sub-matrix.
4. Re-run T02's acceptance, then the A/B of the new draft vs the v8 draft.

**Switcher hook** (temporary, for proxies only, under `#ifdef SWITCH_AT`): at the end of `update_mode()`, `if (round >= SWITCH_AT) { enemy_half_penalty *= 0.05f; deny_bonus += 1.5f; fight_margin = std::min(fight_margin, 0.95f); }` (farmer → invader) and the mirror `#ifdef SWITCH_BACK_AT` (invader → farmer). Never in a submitted build.

### 15.4 Fitting the opponent-model table (T05)
1. Label games by opponent profile (the proxies of 15.2 are labelled by construction; ladder replays by hand: farmer / invader / deathball / objective / altar / ambush / rusher / scaler).
2. From the `OPP` trace lines (extend them to print the 9 window attributes as 0/1), count per archetype `n_a` windows and `c_{a,k}` windows with attribute k = 1.
3. `PA[a][k] = (c_{a,k} + 1) / (n_a + 2)` (Laplace); `PRIOR[a] = (n_games_a + 1) / (N + A_COUNT)`.
4. Replace the tables in `opponent.h`; re-run T05's acceptance (detection within 60 rounds, ≤ 1 false switch per game) and the T06 A/B.

### 15.5 Re-fitting the ml2 danger model on 3.1 games
1. Under a temporary `#ifdef ML2_DUMP`, print the 58 features of every evaluation (`brain.cpp:2622 ml2_features(mf)`) with the round and body id; label each evaluation 1 if the body died within 8 rounds.
2. ≥ 300 games against the proxy set on the 3.1 SDK (≥ 100k evaluations).
3. Fit a logistic regression (the repository's `tools/ml/ml2_train.py` if available — referenced at `brain.cpp:2082`; otherwise scikit-learn, L2, class-balanced) and export `ML2_W_DIE8` / `ML2_B_DIE8` into `ml2_model.h`; if `ml2_gb` won in T03-C, export the trees the same way.
4. Acceptance: held-out AUC ≥ 0.80 (3.0 values: 0.806 logistic, 0.829 trees); calibration plot within ±0.05 in the 0.1–0.4 range (the veto operates at 0.2); then the A/B of the new weights vs the old.
5. Until re-fitted, keep `ml2_adapt = 0.02` (T03-C) so the intercept re-centres in-match.

### 15.6 Fuel profiling
Under `LEGEND_TRACE`, for each new module wrap the call in `const auto f0 = bc::fuel_remaining();` … `std::printf("FUEL mod=%s cost=%llu\n", …)` on 100×100 maps, team size 5, 50 games: record the mean and the worst turn in the ledger; the v9 total must stay under 2,000 mean and 15,000 worst, and the whole turn under 80,000 worst. Appendix B has the budget.

### 15.7 Pre-submission checklist
- [ ] Built against the 3.1 SDK, warning-clean, both `SDK_HAS_HOR` variants compile.
- [ ] No `LEGEND_TRACE`, `OPP_TRACE`, `FIGHT_TRACE`, `FAULT_TEST`, `SWITCH_AT`, `PLAN_FORCE`, `ML2_DUMP`, `LEGEND_DRAFT` defined.
- [ ] `alert_refresh = 0` (T04 static_assert), `watchdog = 3` (T13).
- [ ] Every v9 knob at its ledger-approved value; every knob that lost its A/B at 0; the ledger row quoted in its comment.
- [ ] T02 priors replaced by the tournament's values; T05 tables by the fitted ones (or the hand-set ones if no labelled data: say so in the ledger).
- [ ] 50 games on the largest official map with team size 5: zero `EXC`, worst-turn fuel < 80,000, no `FUEL low`.
- [ ] 20 games each vs the switcher proxies: detection within 60 rounds in ≥ 80%.
- [ ] A final 300-game mirror of the submission build vs the previous submission: ≥ 50% − 1.5.
- [ ] `src/` zipped exactly as the platform expects (same layout as `god.zip`).

---

## Appendix A — A/B script

```python
#!/usr/bin/env python3
"""ab.py: run candidate vs baseline (and vs proxies) over the map set, both sides, and report Wilson intervals.
Usage: python3 ab.py --engine <runner> --cand build/cand --base build/base --maps maps/*.txt --games 300 [--proxy build/farmer ...]
The runner is the CAMBC match tool; it must print the winner and the final banked gems. Adapt run_one() to its CLI."""
import argparse, itertools, math, random, subprocess, sys, re

def wilson(w, n, z=1.96):
    if n == 0: return (0.0, 0.0, 0.0)
    p = w / n; d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (p, c - h, c + h)

def run_one(engine, bot_a, bot_b, map_path, seed):
    out = subprocess.run([engine, '--map', map_path, '--a', bot_a, '--b', bot_b, '--seed', str(seed)],
                         capture_output=True, text=True, timeout=1800).stdout
    m = re.search(r'winner=(A|B)', out)          # adapt to the runner's output
    g = re.search(r'gems=(\d+)/(\d+)', out)
    return (m.group(1) if m else None, g.groups() if g else None, out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', required=True); ap.add_argument('--cand', required=True); ap.add_argument('--base', required=True)
    ap.add_argument('--maps', nargs='+', required=True); ap.add_argument('--games', type=int, default=300)
    ap.add_argument('--proxy', nargs='*', default=[]); ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    opponents = [('baseline', a.base)] + [(p.split('/')[-1], p) for p in a.proxy]
    for name, opp in opponents:
        wins = n = 0; exc = 0
        for i in range(a.games):
            mp = a.maps[i % len(a.maps)]
            side_a = (i // len(a.maps)) % 2 == 0           # alternate sides per pass over the map set
            bot_a, bot_b = (a.cand, opp) if side_a else (opp, a.cand)
            w, gems, out = run_one(a.engine, bot_a, bot_b, mp, rng.randrange(1 << 30))
            if w is None: continue
            n += 1; wins += (w == 'A') == side_a
            exc += out.count('EXC r=')
        p, lo, hi = wilson(wins, n)
        verdict = 'SHIP-OK' if lo >= 0.485 else ('LOSS' if hi < 0.5 else 'INCONCLUSIVE')
        print(f'{name:14s} n={n:4d} win={100*p:5.1f}%  95%CI=[{100*lo:4.1f},{100*hi:4.1f}]  EXC={exc}  {verdict}')

if __name__ == '__main__':
    main()
```
Decision rule (15.2-6): ship only if every row's lower bound ≥ 48.5% and at least one row's point estimate ≥ 52%.

## Appendix B — Fuel budget for the new modules (per turn, 100×100, team size 5)

| Module | When | Budget (mean / worst) | Guard |
|---|---|---|---|
| T04 sighting post | every turn | 50 / 100 | – |
| T05 `opp_observe` | every turn, body 0 | 200 / 500 | – |
| T06 preset apply | every turn | 20 / 20 | – |
| T07 zone bonus | per group scored | 5 / 5 | – |
| T08 `build_influence` | every 4 rounds | 1,500 (avg) / 10,000 | `v9_fuel_floor` |
| T09 buffs read | per visible unit | 2 host calls each | `fm_buffs` |
| T10 `predict_intercept` | only with a carrier in sight | 0 / 3,000 | `v9_fuel_floor` |
| T12 ward gain | per placement (≤ 1 / 10 rounds) | 1,200 (avg) / 15,000 | `v9_fuel_floor` |
| **Total v9** | | **≤ 2,000 mean / ≤ 20,000 worst** | whole turn < 80,000 worst |

## Appendix C — Summary of new and changed `params.h` knobs

| Knob | Task | v8-equivalent | Recommended after A/B (provisional) |
|---|---|---|---|
| `fix_my_dash` | T01 | 0 | **1** (default ON) |
| `pd_*_prior`, `pd_hor3_bonus`, `pd_hor3_pair_pen`, `pd_counter_tank`, `pd_caster_any`, `pd_obj_ring_range`, `pd_first_default`; `pd_hor_prior`, `pd_counter_hor`, `pd_gold_vesper` | T02 | old literals | tournament values (T15.3) |
| `fm_mode`, `hor_threat`, `mi_learn_burst`, `sup_mode`, `chan_keep`, `finish_race`, `mi_endgame_bank`, `ml2_adapt`, `ml2_gb`, `threat_map`, `mono_team`, `tail_stat` | T03 | 0/1/… | 7, 3, 1, 7, 2, 120, 100, 0.02, 1 (fuel), 1 (until T08), 1, 1 |
| `sighting_mode`, `v9_fuel_floor` | T04 | 0 / – | 1, 30000 |
| `plan_mode`, `opp_window`, `opp_hysteresis`, `opp_seed`, `opp_early_round`, `opp_scale_round`, `plan_endgame_at`, `plan_deny_at`, `plan_deny_lead`, `plan_hunt_farmer`, `bandit_reset` | T05 | 0 | 1, 20, 0.5, 1.0, 80, 300, 850, 850, 60, 1, 1 |
| `draft_mem`, `zone_bonus`, `zone_until` | T07 | 0 | 1, 0.10, 150 |
| `infl_mode`, `infl_every`, `infl_memory`, `infl_radius`, `infl_max_src`, `infl_scale`, `infl_w`, `infl_altar_w`, `infl_sight_unit`, `infl_unseen_ally` | T08 | 0 | 3 (7 with T12), 4, 40, 3, 8, 60000, 20, 8, 100000, 60000 |
| `fm_buffs`, `fm_hidden`, `farm_ema` | T09 | 0 | 3, 0.3, 0.05 |
| `gank_mode`, `gank_r`, `gank_r_hunter`, `gank_steps`, `opp_reach`, `opp_unseen_ticks`, `guard_mode` | T10 | 0 | 1, 8, 14, 8, 1, 8, 1 |
| `bandit_discount`, `bandit_explore` | T11 | 0 | 0.2, 0.3 |
| `ward_gain`, `ward_range` | T12 | 0 | 1, 6 |
| `watchdog` | T13 | 0 | **3** (default ON) |
| `risky_persist`, `near_age_cap`, `score_jitter`, `prism_bank_mult` | T14 | 0 / 0 / 0 / 1 | 2, 3, 0.02, 1.5 |

*End of specification.*
