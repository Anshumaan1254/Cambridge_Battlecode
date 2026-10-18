# 03. Implementation spec

How to build Strategy v2 inside the existing `legend` code. The infrastructure (`world.*` perception and memory,
`nav.*` distance fields, `comms.*`, fuel guards) stays. The decision rules change.

House rules (same as the repo's): every change gets a switch in `params.h` with its measured result in the comment;
work on a copy (`bots/_x_*`), never on `bots/legend` while a test uses it; every engine call stays in try/catch;
every new loop gets a fuel check (`bc::fuel_remaining()`).

Line numbers refer to `bots/legend/src` at commit `fcf0820` (this branch); function names are the stable anchors.

---

## 0. Order of work

| Step | Part | Where | Switches | Status |
|---|---|---|---|---|
| 1 | A1 hit first, A2 commit (x_exec) | `brain.cpp` `combat()`, `engage()` | `exec_hit_first`, `exec_flee_hit`, `fight_commit` | **patch ready and tested** (05 section 5): `experiments/wip/x_exec.patch` |
| 2 | A3 real helpers | `combat()`, `world.h` `Ally` | `support_v2` | spec below |
| 3 | A5 camps in the fight estimate | `combat()` | `camp_in_fight` | idea exists in `experiments/wip/x_side.patch` |
| 4 | A7 leave before the finisher | `combat()` | `burst_exit` | spec below |
| 5 | A4 spacing | `build_danger()`, `step()` | `spread_vs_splash` | spec below |
| 6 | A6 strike first | `combat()`, `engage()`, `update_priority()` | `strike_first` | spec below |
| 7 | A9 pair rules | `combat()`, `safety()`, `comms` | `pair_v2` | spec below (needs comms v2) |
| 8 | Comms v2 layout | `comms.*` | `comms_v2` | spec below |
| 9 | Part C draft planner + draft memory | `draft.cpp`, `world.cpp` | `plan_v2` | prototype `tools/strategy_v2/map_plan.py` |
| 10 | Zone farming | `farm()`, `group_score()` | `zone_farm` | spec below |
| 11 | Part D playbooks | `update_mode()`, `farm()`, `tribute()` | `field_mode`, `contest_mode` | spec below |
| 12 | Part B builds, collector, draft | `build_for()`, `group_score()` (ST_REWARD), `draft.cpp` | `build_style 5`, `collector_rank`, `draft_v2` | spec below |
| 13 | Look-ahead fight search | new `sim.cpp` | `fight_sim` | spec below |

Ship rule for each step: 05 section 4.

---

## 1. Part A: fight doctrine

### A1 + A2 (ready)

`experiments/wip/x_exec.patch` adds to `params.h`:

```cpp
int exec_hit_first = 1;           // engage(): target out of reach but another enemy in reach -> hit that one now
int exec_flee_hit = 1;            // fleeing melee swings at an adjacent enemy before the step
int fight_commit = 1;             // keep fighting next turn unless adv < fight_commit_margin or hp < fight_commit_hp
float fight_commit_margin = 0.7f;
float fight_commit_hp = 0.3f;
```

and to `brain.cpp`: `Brain::best_in_reach()` (best enemy within basic-attack range, skipping enemies healing on
their spawn and a Ren whose retaliation would kill us), a call at the top of `engage()` (ranged: cast + attack +
reset, then return; melee: attack, then fall through to the step), a call before the step in the flee branch of
`combat()`, and the commitment check before the `win_bank` veto. Apply with
`cd bots/X && patch -p1 < ../../experiments/wip/x_exec.patch`.

Ablation (82 distinct games each against `legend`): full patch 54.9% (deaths 611 vs 810); without commitment 48.8%;
without hit-first 52.4%; without flee-hit 52.4%. The three parts work together; ship all three.

### A3: real helpers (`support_v2`)

Today `combat()` counts every visible ally within 6 that passes `can_support()` (health above `retreat_hp`, within
`support_reach` of some enemy). Add two conditions and drop hidden allies from the immediate estimate:

```cpp
// world.h, struct Ally: add
std::int32_t state = 0;
bool channeling = false; // recalling or banking (cannot fight)
// world.cpp perceive(): when the ally is visible, from the sdk_champion record
a.state = info.state;
a.channeling = flag(info.state, bc::champion_state::recalling) || flag(info.state, bc::champion_state::submitting_gems);

// brain.cpp
bool Brain::can_support(const Ally& a, const std::vector<Enemy*>& E) const
{
	if (a.hp < P.retreat_hp * a.max_hp || (P.support_v2 && a.channeling))
		return false;
	// can hit an enemy within two turns: melee walks twice and swings (3, or 5 with a dash), ranged walks once,
	// then attacks at 3 or casts at 4 (5)
	const int reach = a.kit.ranged ? 5 : (a.kit.dash >= 0 ? 5 : 3);
	for (const auto* e : E)
		if (cheb(a.pos, e->pos) <= (P.support_v2 ? reach : P.support_reach)) // support_reach is 6 today
			return true;
	return false;
}
```

Also in `combat()`, the `backup` count adds hidden allies whose claimed group is within `backup_radius`. With
`support_v2`, use them only for the `isolated` flag, never in `our_hp` / `our_dps` (they already are not, keep it so).

### A4: spread against splash and area spells (`spread_vs_splash`)

New per-turn bitboard `clump` in `build_danger()`:

```cpp
// active when a visible enemy Varg is within 3, or an enemy with a ready area spell (Stellar slot 1, Prism slot 1,
// Ryth slot 0) is within 5
clump.clear();
if (splash_threat)
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 4)
			clump.draw_chebyshev(a.pos, 1.f);
```

Use it two ways:

1. In `step()` / `step_field()` (nav.cpp ~290): add `clump` to the danger penalty (the same key used for `danger`,
   one level lower than enemy reach). A tile next to an ally is then chosen only when no other improving tile exists.
2. In `engage()` for melee: the goal ring around the target excludes tiles in `clump` when any other ring tile is free.

Cassi and Issac: Cassi's goal when Issac is in a fight is the ring at distance 2-3 from Issac (not 1), on the side
away from the enemy.

### A5: camps in the fight estimate (`camp_in_fight`)

`experiments/wip/x_side.patch` has a working version (`camp_in_fight=3`: a camp whose nearest champion is an enemy
adds its strength to our side). Extend it both ways:

```cpp
for (const auto& g : W.groups)
	if (g.st == ST_ALIVE && g.awake && !g.harmless)
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (g.hp[i] <= 0) continue;
			const vec2 c = g.camps[i].pos;
			if (cheb(c, pos) > 6) continue;
			const int d_us = nearest_ally_or_self_dist(c), d_them = nearest_visible_enemy_dist(c);
			if (std::min(d_us, d_them) > 3) continue;          // it hits nobody
			if (d_us <= d_them) their_dps += g.camps[i].str;     // it hits us: counts for them
			else                our_dps   += g.camps[i].str;     // it hits them
		}
```

Ties go to the champion that acts first in the round (ENGINE_FACTS), so count ties against us. Also: if we stand
inside an awake camp's range and the fight is not clearly won, the first step goes out of `camp_danger`.

### A6: strike first (`strike_first`)

Engage plan when `fight` is true but nobody can hit yet (nearest enemy farther than our reach):

1. If our team opener is not ready (no ready stun among the visible allies in the fight and our own burst on
   cooldown for 1-2 more rounds) and no enemy can reach us next turn: hold at distance `reach_of(enemy) + 1`
   (outside their reach) for at most 2 rounds.
2. When ready: the stunner (Ren, Ryth, Tavi, Cassi, Prism) sets the highest priority (`prio_fight + 3`) this round,
   so next round it acts first; it stuns the focus target; the rest act after it.

Priority applies from the next round, so the decision has to be made one round ahead: compute `engage_next` (an
enemy will be within our reach + 1 next round) and set the priority then.

### A7: leave before the finisher (`burst_exit`)

```cpp
float burst_next = 0; // what the enemies that can reach us next turn can deal in one turn
for (auto* e : E)
	if (cheb(e->pos, pos) <= reach_of(*e))
		burst_next += e->str + e->burst(); // one basic attack + the best ready cast (one cast per turn:
		                                   // a reset swing or a spell; Enemy::burst() already takes the max)
if (P.burst_exit && hp <= P.burst_exit_k * burst_next && !killable)
	fight = false; // and if in reach: the flee branch below (stun the chaser if possible, then step out)
```

`burst_exit_k` starts at 1.1. This is the rule that stops the "burst from 60% health" deaths (40% of ours). Splash
does not add to the damage on one body (a Varg swing hits each body once, as target or as splash), so it belongs
in the spacing rule (A4), not here.

### A8: fight where we are strong

Add a power index to `update_mode()`: `pi_us` = sum over our living champions of (str + focus x best_mod / 8), read
from allies when visible (else last seen), `pi_them` = the same over enemies seen in the last 40 rounds. When
`pi_them > 1.2 x pi_us`: `fight_margin += 0.3`, `enemy_half_penalty x 2`, no enemy-half farming. When
`pi_us > 1.2 x pi_them`: `fight_margin -= 0.2` and contest neutral groups.

### A9: Cassi & Issac (`pair_v2`)

1. Each body of the pair writes a pair-danger bit (comms v2, byte 6 bit 7 for the pair) when its health is below 40%
   or 2+ enemies are within 4 of it.
2. Either body reading the bit treats the fight as `reserve` (only sure fights) and moves toward the other's last
   claimed group / the spawn.
3. Issac does not dash into a fight unless Cassi is visible within 4 and `adv >= fight_margin`.
4. Banking: when the pair carries 40+ gems together, bank before optional fights (`bag_caution` applies to the sum).

### Later: look-ahead fight search (`fight_sim`)

Replace the single `adv` number with a 2-3 turn simulation of the local fight (bodies within 8, at most 10 units).
Engine rules are deterministic and known: turn order (camps first, teams alternate, priority inside a team), damage
= strength or focus x modifier, Durability -10%, stuns remove the next turn, splash radius 1, camps hit the nearest.
Options to compare for this champion: attack target t (each visible enemy in reach), cast spell s on t, step to
each of the 8 tiles then act, retreat. Enemy policy: "hit the lowest health champion in reach, cast every ready
spell". Value = (enemy health lost + 1,500 x enemy bodies killed) - (ours, same) after 3 turns. Fuel: one simulated
turn is ~10 units x a few checks; 30 options x 3 turns x 10 units ~ 1,000 steps, well under 10k fuel in C++.
Build it as `sim.cpp`, compare against the formula on replay fights first (04 section 6).

---

## 2. Comms v2 (8 bytes)

Today: bytes 0-5 = claim per body (7 bits, or 6 bits + 1 bag-sum bit), bit 7 of bytes 0-1 = stance (the stance
learner measured neutral), bytes 6-7 = one alert (14-bit tile + 2-bit kind).

Proposed (`comms_v2`):

| Bytes | Bits | Content |
|---|---|---|
| 0-5 (one per body) | 0-5 | claimed group id + 1 (0 = none; 62 groups max, same as `team_bank` mode today) |
| | 6 | team bag-sum bit (as today) |
| | 7 | **engaged**: this body is fighting this round (others count it as a real helper if they see it, and know a fight is on even if they do not) |
| 6 | 0-3 | **focus target**: enemy body index + 1 (0 = none) |
| | 4-6 | round stamp (round mod 8) of the focus post, so stale targets expire |
| | 7 | **pair danger** (Cassi or Issac, A9) |
| 7 | 0-5 | **rally group**: group id + 1 of the fight's nearest camp group, as a coarse position (0 = none) |
| | 6-7 | alert kind (none, danger, rally, opportunity) |

The stance bits go (the learner is neutral; keep `learn_stance = 0`). The 14-bit alert tile becomes a group id: a
fight is always near some camp group, and every body knows every group's centre. Bodies that see the focus target
hit it; bodies that do not, walk to the rally group if they are within 12 and healthy.

With the zone plan (section 3), claims could shrink to 4 bits (position in the zone circuit), which would free 12
more bits; not needed for the layout above.

---

## 3. Part C: the draft-time plan

### 3.1 What the draft computes (`draft.cpp`, first draft turn, 1,000,000 fuel)

1. `home` and `away` distance fields (two `bc::distance_field::compute` calls: 13-19k fuel each on 100x100).
2. Camp groups from `bc::map::camp_groups()` (~25k, once). For each: gems, gold, respawn, health, strength, number
   of camps, attackers, tiles; walking distance from both spawns (min over adjacent tiles); side (home if
   `d_home < d_away - 3`, enemy if the reverse, else neutral); nearest altar and its distance.
3. Group-to-group walking distances for the home + neutral groups: one field per group (~15k each). On the 17
   official maps that is at most 27 groups (lanes) -> ~400k. If the budget is short, fall back to Chebyshev distance x 1.3
   (good enough for zoning; the circuits are re-walked in game anyway).
4. Zones: weighted k-medoids (PAM swaps) on that matrix, k = number of farming units (picks; Cassi & Issac = one
   unit), weight = group value rate (gems + 0.22 x gold) / (respawn + 5 + health / 150). 50 swap passes at most.
5. Assignment: all permutations of units to zones (k <= 5: 120), score = sum over the zone's groups of
   value / (kill rounds for this unit + 6 + heal-trip cost). Kill rounds use base stats with Varg splash (x0.85 per
   extra camp up to 3), area spells and Ren's retaliation; see `fit()` in `map_plan.py`.
6. Circuits: nearest-neighbour order from the spawn through each zone.
7. Map type flags (section 5) and objective groups (health >= 6,000 and 40%+ of the gems).
8. Ward tiles: for each zone, the bush tiles within 4 of its groups that are closest to the enemy side (up to 2).

The picks are made one per draft turn, so steps 3-8 can also be spread over the later draft turns (100k each) if
the first turn runs short. Never print in the draft (a verbose dump once ran out of fuel and the engine picked at
random).

### 3.2 Draft memory layout (`plan_v2`, version 3)

| Offset | Size | Content |
|---|---|---|
| 0 | 1 | magic `0xB8` |
| 1 | 1 | version `3` |
| 2 | 1 | team size (picks) |
| 3 | 1 | chosen composition id |
| 4 | 1 | map type flags: bit0 rich home, bit1 contest, bit2 objective, bit3 field, bit4 spawns touch |
| 5 | 1 | number of groups G (in `bc::map::camp_groups()` order) |
| 6 | 1 | number of zones K |
| 7 | 1 | reserved |
| 8 | G | per group: bits 0-3 zone id (15 = no zone / enemy side), bits 4-5 side (0 home, 1 neutral, 2 enemy), bit 6 objective, bit 7 hub |
| 8+G | G | per group: walking distance from our spawn (capped at 255) |
| 8+2G | G | per group: walking distance from the enemy spawn (capped at 255) |
| 8+3G | 5 | zone owner per draft slot (0xFF = none) |
| 13+3G | K x (1 + 8) | per zone: circuit length, then up to 8 group ids in order |
| ... | K | per zone: nearest altar index |
| ... | 2 x 8 | up to 8 ward tiles (x, y) |
| ... | 4 | objective group ids (0xFF = none) |

Worst case (70 groups, 5 zones): 8 + 210 + 5 + 45 + 5 + 16 + 4 = 293 bytes of 1,024. On the 17 official maps the
prototype needs 20-70 bytes without the distance tables.

Champion slot mapping: the draft knows the order it picked in; slot = pick index, and Cassi and Issac share their
pick's slot. Each champion finds its slot by its type in `bc::draft::current_draft(team::ally)`.

### 3.3 Reading it (`world.cpp`)

In `World::init_static()`: if `draft_memory[0] == 0xB8 && draft_memory[1] == 3`, read the group table and the
distances instead of recomputing them, and skip the work that only served those numbers. Keep a full fallback
(today's code) when the magic is missing (a draft that crashed or ran out of fuel picks at random and writes
nothing).

### 3.4 Farming by zone (`zone_farm`)

In `farm()` / `group_score()`:

```cpp
const int my_zone = plan.zone_of_slot[my_slot];
const int gz = plan.zone_of_group[g.id];
float zone_mult = 1.f;
if (P.zone_farm && my_zone >= 0)
{
	if (gz == my_zone)              zone_mult = P.zone_own_bonus;    // 1.4
	else if (gz == 15)              zone_mult = P.zone_enemy_mult;   // 0.6 (enemy side)
	else if (zone_owner_alive(gz))  zone_mult = P.zone_other_mult;   // 0.5 (an ally's zone, while it is alive)
}
return zone_mult * value / std::max(1.f, time);
```

The current group-score machinery (kill time, damage taken, trips, claims, threat) stays; zones only re-weight it,
so a champion still helps a neighbour when its own zone is empty or respawning far ahead. Two more changes in the
same switch:

- **Respawn timing:** a group in our zone that respawns within `travel + 4` rounds scores as alive (wait at the edge,
  not on its tiles).
- **One-visit kills:** `max_trips` becomes 1 outside objective groups and outside our own zone (a group another
  team can finish is not worth chipping across heal trips).

### 3.5 Collector rank (`collector_rank`, Part B2)

In `group_score()`, case `ST_REWARD`, the rule "a lower-index claimer captures" becomes "the claimer with the best
collector rank captures":

```cpp
int collector_rank(CT t) { // farming damage gained per gold
	switch (t) { case CT::varg: return 0; case CT::issac: return 1; case CT::stellar: return 2;
	             case CT::ryth: return 3; case CT::vendetta: return 3; case CT::cassi: return 4; case CT::tavi: return 4;
	             default: return 5; } // Ren, Prism, Marcella, Willow, Vesper
}
```

Ties by index. After the kill, the non-collectors leave the group's tiles at once (they go to their next target), so
the reward is not split. Cassi and Issac: Issac collects for the pair unless Varg is there.

---

## 4. Part B: builds and draft

### 4.1 `build_style 5` (damage builds)

In `build_for()` (brain.cpp ~35), a new branch:

```cpp
if (P.build_style == 5)
{
	switch (t)
	{
	case CT::varg:    rep(v, I::monster_shard_of_strength, 5); rep(v, I::durability_shard_of_health, 5); break;
	case CT::issac:   rep(v, I::power_shard_of_strength, 5);   rep(v, I::durability_shard_of_health, 5); break;
	case CT::cassi:   rep(v, I::bruiser_shard_of_health, 5); break;
	case CT::stellar: case CT::prism:
	                  rep(v, I::power_shard_of_focus, 5);      rep(v, I::durability_shard_of_health, 5); break;
	case CT::ryth:    rep(v, I::durability_shard_of_health, 5); rep(v, I::bruiser_shard_of_health, 5); break;
	case CT::ren:     rep(v, I::durability_shard_of_health, 5); rep(v, I::bruiser_shard_of_health, 5); break;
	case CT::tavi:    rep(v, I::treasure_shard_of_focus, 5);   rep(v, I::durability_shard_of_focus, 5); break;
	default:          rep(v, I::durability_shard_of_health, 5); break;
	}
	const bool focus = t == CT::ren || t == CT::stellar || t == CT::cassi || t == CT::prism || t == CT::tavi || t == CT::willow;
	rep(v, focus ? I::power_shard_of_focus : I::power_shard_of_strength, 300);
	return v;
}
```

The planner must know the new numbers: `incoming_on()` / `jungle_done()` assume Jungle on some kits; with style 5
nobody has Jungle, so the kill-time and trip estimates change by themselves (they read real health and stats). Check
`build_style 4`'s failure (no health at all: contest never finished, stampede +470 rounds): style 5 keeps one health
emblem per champion, which the top teams show is enough.

Field maps (Part D): for the two farmers with the most recalls, replace the second emblem by a Home emblem in the
damage stat (`home_shard_of_strength` / `home_shard_of_focus`), and set `has_home` so the capture-recall timing uses 3
turns (brain.cpp ~3050 already handles it).

### 4.2 `draft_v2`

Add to `COMPS` in `draft.cpp`:

```cpp
{ "top",  { D::varg, D::stellar, D::cassi_and_issac, D::ryth, D::ren  }, { 0.60, 0.60, 0.60 } },
{ "topT", { D::varg, D::stellar, D::cassi_and_issac, D::ryth, D::tavi }, { 0.59, 0.59, 0.59 } },
```

(raise `std::array<Comp, 6> COMPS` to 8) and choose with the map type: objective or field -> `topT`, else `top`. The values are placeholders until a
tournament against the top-style bot (05) gives real ones. Read the enemy's revealed picks before each pick
(`bc::draft::current_draft(team::enemy)`) and store them in draft memory byte 7 as flags (enemy has Varg, enemy has
3+ stunners) for the spacing rule.

---

## 5. Part D: map types

Computed in the draft (section 3.1 step 7), stored in byte 4.

| Flag | Test (from the plan) | Effect in game |
|---|---|---|
| rich home | home gem rate x 450 >= 1,000 | `enemy_half_penalty x 1.5`; neutral groups only when `pi_us > pi_them` |
| contest | not rich home | `contest_mode`: two bodies per neutral group (join rule relaxed: `max_join = 2` there), wards on the zone's ward tiles, `deny_capture_mult x 1.5` |
| objective | heavy groups hold 40%+ of the gems | keep `obj_plan`; for a lone monolith (contest map) a team plan: gather 4+ bodies with full health at round ~500 or when the team's summed damage stat passes 600, kill, collector = best converter, then defend its respawn (150 rounds) |
| field | mean home-group distance >= 30 | `field_mode`: no walks home to bank (bank at the zone's altar), recall only for health below 50% or 150+ gold, Home emblem for farmers |
| spawns touch | spawn regions within 3 tiles | never trade on their spawn (exists), keep one body home as a guard |

---

## 6. Fuel

| Item | Cost | When |
|---|---|---|
| Draft planner (fields, groups, distance matrix, k-medoids, assignment) | ~400-700k on 100x100 maps | first draft turn (1M) |
| Reading the draft memory in `init_static()` | under 5k | first turn (200k), replaces ~25k+ of today's work |
| A3-A7 checks in `combat()` | under 3k a turn (visible units only) | every turn with enemies in sight |
| `clump` bitboard (A4) | under 1k | only with a splash/area threat in sight |
| Fight look-ahead (later) | target under 10k | only when an enemy is within 8 |

Check rollovers after each step with `decode(..., { rollovers: true })` on `maps/gen16_98x99_V_c5.map26a`
(the repo's standard) and on ambush.

---

## 7. Telemetry for the KPIs

The KPIs in 05 can be computed from replays alone (`tools/strategy_v2/analyze.py`), so no debug output is needed in
the submitted bot. For local work, add one `LEGEND_TRACE` line per fight decision:

```
FD r=<round> ch=<type> adv=<adv> fight=<0/1> commit=<0/1> burst_next=<..> hp=<..> camps_us=<..> camps_them=<..> clump=<n>
```

and compare predicted `adv` with the replay outcome of the same fight (04 section 6).
