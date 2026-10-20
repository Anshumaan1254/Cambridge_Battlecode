# Sprint documents (GameRules.md, BotAPICpp.md): what they say, and what it means for our bots

The user uploaded these two files on 20 Oct 2026 as "the new documents for this sprint" (copies next to this file). This note compares
them with the patch-3.0 notes (`docs/patch_notes/week2_20261020.txt`), the two engines on PyPI (cambc 2.2.5 and 3.0.1; 3.0.1 is the
newest) and our two bots (`legend_m15` = `submissions/legend.zip`, GOD v5 = `submissions/god.zip`).

## 1. Which game do the documents describe?

**GameRules.md describes the game before patch 3.0** (every number below is the pre-patch value; the patch-3.0 value is in brackets):

| Item | Sprint docs | Patch 3.0 (cambc 3.0.x) |
|---|---|---|
| Champions | 11 picks (no Heart of Ruin) | 12 (Heart of Ruin added) |
| Camps | wolf, elk, gem cluster, gold cluster, monolith | + Golem (5,000 hp, 120 str, range 4, 36 gems, 160 gold, 80 rounds) |
| Wolf gems / gold | 22 / 90 | 4 / 40 |
| Elk gems / gold / range | 36 / 160 / 3 | 15 / 90 / 4 |
| Gem cluster hp / gems | 500 / 24 | 120 / 7 |
| Gold cluster hp / gold | 500 / 35 | 120 / 20 |
| Monolith range | 3 ("all monsters have attack range 3") | 5 |
| Kill gold | 50 | 100 |
| Ward | relocate every round | 10-round cooldown |
| Altar lock | 3 basic attacks | 5 |
| Cassi hp / growth hp, str, focus | 700 / 71.25, 3.5, 15 | 600 / 65, 3, 13 |
| Issac growth hp / str | 95 / 4.75 | 80 / 3 |
| Stellar focus / str / focus growth | 100 / 35 / 10 | 85 / 30 / 9 |
| Varg str, Ren str (focus growth), Ryth str | 50, 40 (10), 50 | 40, 35 (9), 45 |
| Marcella | stun immunity only; focus 50 (+10) | + 2 gold per gem tributed; focus 60 (+15) |
| Willow str / focus | 45 / 105 | 55 / 120 |
| Vesper gold bonus / str | 20% / 45 | 33% / 50 |
| Vendetta str growth | 5 | 6 |
| Prism focus per gem / growth hp, str, focus | 0.2 / 75, 3.5, 10 | 1.0 / 60, 2.5, 8 |
| Tavi stun damage / str | 2.2 x focus / 35 | 1.4 x focus / 45 |

**BotAPICpp.md is mixed**: its function list matches the 3.0 SDK (it has `vision::awake_camp_tiles` / `asleep_camp_tiles`, which only
3.0.x has, and no `dash_range`, which 3.0 removed), but its enums and structs are the pre-patch ones: `champion_draft` and
`champion_type` without `heart_of_ruin`, `camp_type` without `golem`, `ability_dash` with only `range` (3.0.x adds `modifier` and
`radius` for Heart of Ruin's damaging dash), no `marcella_tribute_gold_per_gem` / `heart_of_ruin_*` constants. Checked with
`tools/sdk_apidiff.py` (every documented name searched in both SDK headers; 3.0.0 has Heart of Ruin and Golem too).

So either the handbook pages were not updated for patch 3.0 (the ladder games of 20 Oct, `experiments/nyx_oct20`, `experiments/losses_oct20`,
were played on 3.0 with Heart of Ruin in the drafts), or the sprint runs the old balance on a newer SDK. **We cannot tell which from here**
(`cambc maps pull` and the platform are blocked in this container), so the submission must work under both.

## 2. Rules the documents state that our code relies on (all already handled)

- Tiebreak: tributed gems, then lifetime gold earned, then kills, then Team B. Draft: 3-5 picks, simultaneous, one of each per team (the
  opponent may pick the same); a missed pick is filled at random; 10x fuel on the first draft turn, 2x on the first game turn.
- Draft memory (1,024 bytes) is written in the draft and read-only in the game: **our bots do not use it** (each body re-reads the map at
  game start; the draft's analysis is recomputed, see `docs/BOT_PLAN.md`).
- Capture: one spawn tile of the dead group, uncontested, 5-round timer, reset when empty or contested; rewards split between allies present
  (lowest id gets the remainder); **an occupied spawn tile delays the whole group's respawn** (ENGINE_FACTS: we never wait on a respawning tile).
- Camps wake on damage and sleep after 2 rounds without a champion in range; they hit the nearest champion, see through bushes, do not chase.
- Tribute: max(1, ceil(gems / 10)) owner turn ends, completes at the next turn start, tributes the whole bag; captures resolve before channels.
  Damage does not stop it; stun, death or an altar lock does. A tribute at a locked altar becomes attacks on the lock.
- Recall: 5 turn ends (3 with Home), any damage or stun cancels it, heal only after staying on spawn to the end of the arrival turn.
- Teleport crystal: range 3, 3-turn channel, damage does not stop it, stun and death do; it cannot be cancelled.
- A move onto a tile with a hidden bush occupant returns false and keeps the move allowance: `nav.cpp` already tries the next candidate.

## 3. What this means for our bots

| | legend_m15 (`submissions/legend.zip`) | GOD v5 (`submissions/god.zip`) |
|---|---|---|
| Compiles with the documented API (= SDK 2.2.5 enums) | yes | **no**: `heart_of_ruin` (16 uses), `camp_type::golem` (1), `ability_dash::modifier / radius` (2) |
| Compiles with SDK 3.0.1 | yes | yes |
| Tuned for | the old balance (Oct 19 ladder, danger model trained on it) | patch 3.0 (gold_value 0.33, burst_retreat 1.2, Heart of Ruin draft at 3 champions) |

- **`bots/_god_c` = GOD v5 + `experiments/wip/x_sdkcompat.patch`**: `common.h` names Heart of Ruin, Golem and the dash fields through
  `requires`-expressions (`SDK_HAS_HOR`, `CT_HOR`, `D_HOR`, `CAMP_GOLEM`), the draft's pick order and the `pd_hor3` rule use Heart of Ruin
  only when the SDK has it. **On SDK 3.0.1 its wasm is byte-identical to GOD v5's** (sha256 47cd9ae8…), and it compiles on 2.2.5.
- Measured under the documents' rules (cambc 2.2.5 engine, the original 17 official maps `maps/comp`, both sides, 34 games per cell):
  see §4.
- Hardcoded rule numbers found while checking (now in ISSUES.md): `brain.cpp` adds 6 steps for an enemy-locked altar ("three hits"; patch 3.0 is
  5 hits: `bc::constants::altar_lock_hits` exists); the ward rhythm is a fixed 10 rounds (fine under both: the old rules allow more often).
  Everything else is read from the engine at runtime: camp gems, gold, health, strength, respawn and (GOD) attack range; champion stats and
  ability kits; capture, recall, respawn and crystal times.

## 4. Measured (cambc 2.2.5 = the documents' rules)

(filled in below as the cells finish)
