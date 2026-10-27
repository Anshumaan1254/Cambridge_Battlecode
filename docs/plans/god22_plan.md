# Plan: GOD v22 — study IC and Mite, fight as a team (never alone), lure and farm, fix draft, Ryth and wards (base = live v75)

## Context

- **Live bot:** v75 "GPTA" = `god__3_.zip`, byte-identical to `submissions/god18.zip` (sha256 bc6abe19…) = **GOD v18**, the same code as v74.
  `bots/god18` = that code plus `g18_rich`, which is off by default.
  You chose v75 as the base.
- **Where we stand:**
  - Ranked play hovers around 50% at about rank 49.
  - Against the top three on all 70 maps: IC 7/70, Mite 5/70, Trzy Kwaterki 7/70 (doc 29).
  - The top teams take about twice our captures and die about half as often (Mite 4.9 deaths a game vs our 10.2), and make their first capture 70–130 rounds earlier.
- **What you see in games:**
  - Champions roam without purpose.
  - Fights split: half walk on, half die.
  - **Champions go alone into fights against enemy champions.**
  - No tank-front or support roles.
  - Ryth gets stuck.
  - Wards are placed randomly.
  - The draft may be stale.
  - You want Mite's lure-and-farm play and IC's strengths studied and adopted in our own form.
- **Causes already found in the code** (god18 `brain.cpp`):
  - **Fight odds from one body's own sight only.** combat() 3412-3458 adds allies only if this body sees them; vision is not shared between champions (rules).
  - **Retreats cascade.** Allies seen walking away are dropped as support (3423-3429), so one leaver lowers everyone's odds.
  - **Lone bodies take fights.** Single responders answer a rally alone (`respond_to_alert`, one slot); alert walks step toward the enemy 78% of the time; `fz_chase` chases.
  - **Busy bodies don't help.** Bank, home and shop trips run before a rally (cascade 1145-1180).
  - **No roles.** Every body uses the same target formula (3555-3586).
  - **Little team talk.** Shared memory is 8 bytes (an engine limit). `set_priority` is an int32 that allies who see each other can read (`query_priority`); Mite uses it for messages, and we never read it.
- **Ryth stuck, likely causes:**
  1. Moves fail and are not retried. The rules say a move into a hidden occupant returns false, keeps the move allowance and should be retried on another tile. Our nav retries the same blocked route every turn (nav.cpp 391-413). Ward tiles are also invisible to pathing.
  2. Fuel runs low on big maps, so `step_to` returns no move (nav.cpp 525).
  3. Stun casts use up the move (4021, 4308).
  4. Deliberate holds.
  5. The bait-recall cancel can fail and leave the body in a channel (1073-1106).
  `unstick()` ignores spell casts and never checks fight or wait states.
- **Two copies of the repo have diverged.**
  - GitHub `main` (`d791fdd`) has 92 commits this PC lacks: GOD v19–v21; doc 28 (IC ranked study); doc 29 (top 3, 70 v20-vs-Mite and v20-vs-IC games, 580 ranked games each for IC, Mite and Trzy Kwaterki); the pack code `g20_pack`.
  - This PC has 3 unpushed commits and 79 untracked files.
  - Both sides have a `bots/god19`, with different code.
- **Hard truths from earlier sessions:**
  - Local proxies and mirror tests mislead, and local results don't carry over to other opponents.
  - Pack, squad and deathball play, and vetoes on back-and-forth steps, lost locally.
  - So every change ships behind a switch and is measured alone, and the ladder decides.
- **Rules:**
  - I never submit or activate a bot. I build the zip and you upload it.
  - Unranked groups with the live bot are allowed (about 50 groups an hour).
  - No per-map tables or fixed drafts: rules come from map features at runtime.
  - Keep AGENTS.md short.
- **Test panel (your choice):** v75 (`gpta75`), v17 (`god17`) and the IC clone.

## Phase 0 — Sync, base, housekeeping (first, about 1 h)

1. **Merge GitHub.**
   - Commit this PC's session-22 results.
   - `git mv bots/god19 bots/god19pc`.
   - `git pull` (merge, never force), then resolve AGENTS.md and the ledger CSVs by hand.
   - Push the merge. This is data and docs only; nothing goes live.
2. **Base bot.**
   - Extract `god__3_.zip` to `bots/gpta75`.
   - Create `bots/god22` from `bots/god18`.
   - All new code goes behind `g22_*` switches in `params.h`.
   - **Null check:** `tools/abbench.py god22 gpta75` gives 70/140 with identical rows.
3. **Housekeeping.**
   - Prune AGENTS.md: move §S15 and older to `docs/history/AGENTS_ARCHIVE_S1-S15_20261021.md`.
   - Mark "`submissions activate`" as your step.
   - Update my memory: the test panel is now v75 + v17 + the IC clone.
   - IC clone: `_icc2` from the merge, otherwise `_px_ic` (`tools/ic/make_team_proxy.py`).

## Phase 1 — Rules and Bot API audit (the files you attached; about 2 h)

1. **Save the files.**
   - Save both to `docs/sprint/GameRules_20261027.md` and `docs/sprint/BotAPICpp_20261027.md`.
   - Diff them against the Oct 20 copies in `docs/sprint/`, `docs/ENGINE_FACTS.md`, `docs/patch_notes/week4_20261026.txt` and `sdk/cpp/cambc.h`.
   - Run `tools/sdk_apidiff.py` for API names.
2. **Already checked:**
   - No newer engine exists: `cambc` 4.0.0 is the latest release, platform engine 2.0.0.
   - All 13 champion changes and both emblem changes from week 4 match the new rules.
   - The bot reads champion and camp stats from the engine at runtime.
   - Wards are permanent: one active per champion, placement within 2, vision 6, recharge 10. So holding a ward is correct; the earlier "stale `ward_pos`" worry is dropped.
3. **Things the rules show that we may not handle. Verify each with the probe bots (`bots/probe-rules`, `tools/probe`) and fix or record it:**
   - **Draft fuel.** The first draft turn now gets **100×** fuel. ENGINE_FACTS still says 1M (10×). Use the extra fuel for map analysis written into the 1,024-byte draft memory, which all bodies can read.
   - **Hidden occupants.** A move or dash that returns false on a hidden occupant should be retried on another tile in the same turn (likely the Ryth fix).
   - **Camps destroy carried gems.** Never tank camps while carrying gems. Monsters don't chase and attack the nearest champion, so a lure path past an awake camp may hurt the chaser.
   - **Turn order.** Dead champions get shop turns. The team that moves first alternates each round, which matters for the last tribute race.
   - **Tiebreak.** Tributed gems, then lifetime gold earned, then kills, then team B. Check that the endgame logic uses this.
   - **Champion passives to check in our code:**
     - Vendetta's cooldown reset also triggers on camp kills.
     - Tavi can sell for full value and buy shards in the field; we never call `sell()`, and Mite sells 6.8 items a game.
     - Marcella gets 2 gold per gem tributed.
     - Prism gets 1.5 Focus per carried gem.
     - Ryth gets Strength from bonus health (not modelled, ISSUES).
     - Heart of Ruin gets bonus damage from missing health.
   - **A doc inconsistency.** The Stellar example says 85 Focus but the table says 70. The engine value is what counts.
4. **Useful API functions the live bot never calls** (0 uses in `bots/god18/src`). Each is assigned to a later phase:
   - **`ability::damage_amount(target)`, `heal_amount`, `shield_amount`:** exact damage after mitigation and shields. Fight odds (Phase 8).
   - **`unit::buffs()`, `champion::restrictions()`:** an enemy stunned (can't act) or shielded. Engage windows (Phase 8).
   - **`has_completed_turn()`:** has the enemy already acted this round? Safe step-ins (Phase 8).
   - **`item_count()` on visible enemies:** their real build, for odds (Phase 8).
   - **`remaining_channel_time()`:** punish enemy recalls and tributes, and tell fake recalls from real ones (Phase 8).
   - **`query_priority()`:** read allies' fight messages (Phase 8).
   - **`ward::visible_tiles_from()`, `ward_placement_tiles()`, `vision::visible_tiles()`, `shadow_cast`:** exact coverage-maximising wards (Phase 7).
   - **`move_absolute`, `bitboard::reachable_tiles`, `distance_field::next_moves_from`:** retry moves and pick alternative steps (Phase 6).
   - **`sell()`:** Tavi builds (Phase 5).
   - **`vision::altar_locks` / `altar_lock_at`:** lock hits left (Phase 9).
   - **`debug::draw_dot` / `draw_line`:** role, target and lure overlays in local replays, so you can watch decisions (Phase 10). They cost no fuel inside `debug_block` and are skipped on the platform.
- **Output:** `docs/strategy_v2/30_RULES_API_AUDIT.md`, plus updates to ENGINE_FACTS.

## Phase 2 — All 70 maps: features, archetypes, base strategy (about 3 h)

- Run `tools/mapintel/catalog.py --maps all` (today it covers only the 40 old maps).
- Run `archetypes.py --kmax 8 --boot 300` on `maps/s3` (= the platform pool).
- Reuse the runtime dump `experiments/results/mapintel/dump/`.
- Add per map:
  - spawn-to-spawn path length;
  - gems in our half, the middle and their half;
  - the richest middle group and its distance from each spawn;
  - choke points;
  - bush clusters on approach paths;
  - spawn-to-contest healing distance;
  - **lure corridors**: paths from the middle back to our spawn, noting camps on the way.
- Name the clusters by feature. For each archetype, write the base plan:
  - farm and contest split;
  - which groups to take first (IC's opening targets, from Phase 3);
  - wards;
  - draft lean;
  - banking.
  These become runtime rules keyed on features, partly computed in the draft turn with the 100× fuel.
- **Output:** `docs/strategy_v2/31_MAPS_BASE_STRATEGY.md`, plus `maps/catalog/` for all 70 maps.

## Phase 3 — IC and Mite on every map (queue first; about 6 h, mostly game time)

1. **Queue 28 groups with live v75:**
   - 14 against **IC** (`1890540d-1ffc-4847-adbf-d0d08772f268`);
   - 14 against **Mite** (`ee83f5e5-bcad-4923-86b4-b79ea6083d2e`).
   - 70 maps each, sides alternating so each run covers both sides with doc 29's v20 runs.
   - Use a small `tools/top_groups.py` built from the `create` call in `tools/paired_groups.py`; it logs to `experiments/top2_oct27/groups.jsonl`.
   - These 140 games are also the **baseline** for the final ladder comparison.
2. **Replays.**
   - Download and decode (`experiments/ladder_oct26_v74/fetch_dec.py`, `tools/replay/decode.mjs`).
   - Add doc 29's 140 v20 games, the 65 decoded Mite games in `ladder_oct26_top/dec/`, the IC games in `experiments/ic_oct26_v18/`, and about 60 ranked games each of IC and Mite against top-10 teams.
3. **IC: what it does and why it works.** Reuse `ladder_oct26_top/teamstats.py`, `banks.py`, `focus*.py`, `top3_oct27/econ.py`, `osc.py` and `steal.py`.
   - **Opening:** routes, which groups first and when, and the whole team on the richest middle group (corridors' 58-gem centre at r36 vs our r150).
   - **Pack farming:** team spread over time, how bodies split and rejoin.
   - **How a fight starts:** how many IC bodies are within reach when the first hit lands, against how many of ours.
   - **When it fights or leaves:** focus fire (same target, same round), how it reacts to our moves, how it punishes a body of ours that is alone.
   - **Builds and banking.**
4. **Mite: the lure** (new `experiments/top2_oct27/lure.py`).
   - **Episodes:** a Mite body near ours moves toward Mite's spawn for 3+ rounds while ours follows.
   - **Who lures:** which champion, at what hp, and the gap it keeps.
   - **Who gets lured:** test your "slow and strong" idea with `base_stats().base_move_speed`, dash and kit.
   - **What it costs us:** how long each episode lasts and how it ends, our lost body-rounds, and the gems Mite's other bodies take meanwhile.
   - **Healing:** at spawn, and whether the lurer comes back.
   - **The rest of Mite's game:** the farm and bank cycle, Treasure opening, item selling (Tavi), the recall bait, its `set_priority` messages, and farming on contact.
5. **Our mistakes in these 140 games.** Each is tagged with a replay id and round so you can watch it:
   - solo fights;
   - split fights;
   - chases;
   - deaths while carrying;
   - captures lost;
   - idle and roaming time.
- **Output:** `docs/strategy_v2/32_IC_MITE_STUDY.md`, with numbers, watchable examples and a spec for our own versions. They are principles, not copies.

## Phase 4 — Deep "why we lose" analysis (about 3 h, alongside Phase 3)

- **Data:**
  - our v18 games since Oct 26 (ranked and unranked, `fetch_me.py`, mapped to the live version by time);
  - the Phase 3 games;
  - `experiments/top3_oct27/ranked_us.jsonl`.
- **Gem-gap ledger per game** (new `experiments/top2_oct27/gapledger.py`). Every 10 rounds, split the change in the gem gap into:
  - captures lost to contest or steal;
  - **deaths**: gems dropped, respawn time lost, and the farm time the enemy gets;
  - idle or roaming body-rounds;
  - slow bank trips;
  - opening delay;
  - camp damage never captured.
  Sum by cause across games, so the biggest causes rank first.
- **Each death is classified** (`tools/analysis/death_ctx.mjs` plus new rules):
  - **solo engagement**: we hit first or walked in with no ally within reach, against 1+ enemies;
  - outnumbered;
  - chased while fleeing;
  - burst at high hp;
  - camp kill;
  - carrying gems;
  - near our spawn.
  Record the killer types and what the nearest ally was doing.
- **Your complaints, measured:**
  - **Roaming:** no hit, capture, bank or fight, and no progress, over 10 rounds.
  - **Split fights:** an ally walks away while another fights.
  - **Fight composition.**
  Use `coord.py`, extending `tools/analysis/coord_audit.mjs --split`.
- **Compare every number with IC and Mite in the same games**, so we fix gaps, not habits they share.
- **Find the cause in code** for the top patterns: local reruns on the same map with `G17_TRACE`.
- **Output:** a section in doc 32 that ranks the causes, gives counts and examples, and names the code path and the fix phase for each.

## Phase 5 — Draft engine against patch 2.0.0 (about 2 h)

- **Stale numbers:**
  - Replace hardcoded costs and cooldowns with SDK values: `item_type::cost()`, `consumable_type::cost()`, `max_cooldown`; brain.cpp 1922-1940, 4602, 6582, 6946 and the 8-round divisions.
  - Replace name-based `is_caster` / `is_front` (draft.cpp 380/386) with kit checks.
  - Retire or refit the 3.0.4-era COMPS, team pick tables and `PD_STAT_REF` (draft.cpp 90-97, 276-303, 628).
- **Data model:**
  - Fit a logistic draft-value model on about 6,000 post-patch ranked games (`experiments/top3_oct27/ranked_*.jsonl`).
  - It has team-strength terms, champion and pair terms, and map-archetype interactions.
  - Refit `pd_w_*` from it, and add the missing pair term (draft.cpp 781 ignores the team).
- **Change picks only where the model and a forced-roster local test agree.** Drafts are not the main gap.
- **Builds:**
  - new emblems (Tribute, Capture, Prospector, Hunter, Skirmish, Greed, Collectors), one switch each;
  - Tavi field buys and `sell()`;
  - passives from Phase 1.
- Use the 100× draft fuel for deeper map planning and write it to draft memory.

## Phase 6 — Ryth stuck and movement failures (about 2 h)

- **Find:**
  - Run `tools/analysis/stuck.mjs --worst 30` on our decoded games.
  - Filter to Ryth (and other bodies) alive, off spawn and shop, with no move and no action for 5+ rounds.
  - Record the map, round, hp, nearby units and ability state.
- **Reproduce** on the same map and side with `tools/fueltrace.py` and the IDLE trace (brain.cpp 1219).
  - Fuel: the turn ends below the `step_to` or field floors.
  - Logic: a hold or a failed move.
- **Fixes:**
  - On a false move or dash, mark that tile blocked for the round and retry the next best step (`next_moves_from`, `move_absolute`).
  - Treat ward tiles as blocked in the fallback search.
  - Add a budget guard or path cache for big maps.
  - Don't stun instead of moving when fleeing.
  - Make sure the bait cancel can't leave the body in a channel.
  - Extend `unstick()` to count casts and cover fight and wait states.
- **Gate:** the replay cases no longer occur in reruns, and the panel is no worse.

## Phase 7 — Wards for coverage, near grass (about 2 h)

- **Candidates:** `ward_placement_tiles()` instead of the hardcoded 2-tile bush ring.
- **Gain per tile:** `ward::visible_tiles_from(tile)` minus what we already see (`vision::visible_tiles()`).
- **Weights:**
  - enemy approach paths to our farm groups;
  - contested middle groups;
  - grass/bush tiles where enemies hide (and the rule that bushes block sight from outside);
  - a bonus for standing in or next to grass;
  - a penalty for blocking our own paths.
- **Move the ward** only when the new tile's gain beats the current one by a margin.
- **Measure before and after:**
  - share of the contested area seen;
  - **surprise contacts**: an enemy within 4 tiles that we didn't see last turn;
  - wards on or next to a bush (36% today).
- Switch: `g22_ward`.

## Phase 8 — Team fights: never alone, one decision per fight, roles (main work, about 8 h)

1. **Never fight alone.** A new engagement gate in combat() and in rally / alert responses (`g22_solo`).
   - A body may start or walk into a fight with enemy champions only if allies who will be in reach within k rounds make the fight a predicted win by a margin.
   - "Predicted win" uses `damage_amount(target)`, enemy hp, shields and stuns (`buffs()`), and enemy items (`item_count()`).
   - Exceptions, each with a measured threshold:
     - a sure kill before the enemy can answer (a lone weak enemy, a stunned enemy, or one channelling a recall or tribute, from `remaining_channel_time()`);
     - defending a capture that is about to finish.
   - Otherwise the body does not go. It keeps farming, waits for the group, or backs off.
   - Lone rally responders and chases (`fz_chase`, alert walks) obey the same gate.
2. **The fight message through the priority channel.**
   - Priority keeps the turn order in the high bits; the fighter ordering at brain.cpp 4423-4451 is kept.
   - The low 16 bits carry the commit flag, role, focus target and hold timer.
   - Allies read it with `query_priority(true)`.
3. **One decision per fight cluster.**
   - Our bodies near the same enemy group decide together with the odds of all committed allies.
   - An ally that holds the commit flag never lowers the others' odds by stepping away to position.
   - The decision holds for K rounds (no A-B-A).
   - Committed bodies skip bank, home and shop trips until the fight resolves.
   - Bodies outside the cluster keep farming.
4. **Roles in a committed fight**, from engine stats at runtime:
   - **Tank** (highest effective hp, melee) goes in first and holds the front.
   - **Ranged** stay at max range behind the tank.
   - **Burst** waits until the enemy is on the tank, then all hit the posted focus target (lowest effective hp, killable soonest).
   - **Flankers** (4+ bodies) cut the enemy's way home.
   - `has_completed_turn()` times step-ins after the enemy has acted.
5. **Disengage together.** An outmatched cluster leaves as one, along a lure corridor toward our spawn (healing). If enemies follow into our spawn zone, we fight there (`g21_fort` code from the merge).
6. **Pack farming as an option** (IC's strength, `g20_pack` from the merge).
   - Port it behind a switch: the team, or a strong sub-group, takes rich middle groups together, so a fight there is always a group fight.
   - Parameters come from Phase 3's IC numbers.
- Switches: `g22_solo`, `g22_fight`, `g22_roles`, `g22_focus`, `g22_flank`, `g22_pack`. Each is measured alone, then in combinations.

## Phase 9 — Lure and farm (Mite-inspired; about 4 h)

- **Roles per game phase:**
  - 1–2 **lurers**: faster by `base_move_speed` or dash, survivable, ranged or stun.
  - The rest **farm and bank**, and steer away from enemies known through vision, wards and the alert slot.
- **Lure targets:**
  - The target is an enemy slower than the lurer that would beat our farmers.
  - The lurer stays just outside its reach (`attack_range`, `ability_dash.range`) and backs toward our spawn to heal.
  - It drops the lure when the target gives up.
  - Optionally it routes past awake camps, since monsters hit the nearest champion.
- **Settings** come from Phase 3's Mite numbers. **Archetype gates** come from Phase 2.
- **Altar locks:** check where we lose tribute races (`altar_locks`, lock hits left); Mite and Trzy Kwaterki place 3–4 a game, we place 1.
- Switch: `g22_lure`.

## Phase 10 — Test, pick, measure (after every phase from 5 to 9)

1. **Local (deterministic):** for each switch and combination, run `tools/abbench.py` with 140 games on `maps/s3` against each of:
   - `gpta75`;
   - `god17`;
   - the IC clone.
   Then the held-out pools `gen2`, `gold3` and `var17`, scored with `tools/abstat.py` / `abmargin.py`.
2. **Keep rule:**
   - Level (within ±50 gems, doc 29's noise floor) or better against every panel bot on every pool.
   - Better on at least one with a confidence interval above 0.
   - 0 faults in 400+ games.
3. **Behaviour checks** on local replays, with Phase 4's scripts:
   - solo engagements;
   - split fights;
   - roaming;
   - deaths with allies near;
   - Ryth stuck episodes;
   - ward coverage.
   The `debug::draw_*` overlays let you watch roles, focus targets and lures in the local viewer.
4. **The ladder decides.**
   - After you upload, I re-queue the same 28 IC and Mite groups (same maps and sides).
   - That gives a map-by-map comparison against the Phase 3 baseline.
   - If it is worse, you re-activate v75.

## Phase 11 — Deliver

- `submissions/god22.zip`, a BUILDS.md row, and `docs/strategy_v2/33_GOD_V22.md`.
- AGENTS.md updated at each step; commit and push.
- I tell you the zip path and the measured results. **No submit or activate.**
- If nothing passes the keep rule, I say so plainly and offer the best candidate only as an option.

## Order

Phase 0 runs first. Queue the 28 groups (Phase 3.1) next, because the games take time to play. Then Phases 1, 2 and 4 run while the games play; then 3's analysis; then 5, 6 and 7; then 8; then 9. Phase 10 runs after each of Phases 5–9, then Phase 11. Total: about 3–4 working days.

## Critical files

- `bots/god22/src/`:
  - `brain.cpp`: combat 3325, engage 4140, safety 4617, `respond_to_alert` 5399, wards 2732-3054, unstick 1727, cascade 1145, priority 4423;
  - `draft.cpp`;
  - `comms.cpp/.h`;
  - `nav.cpp` (move 391-413, `step_to` 525);
  - `params.h`;
  - `common.h` (`kit_of`).
- **Tools reused:**
  - `tools/abbench.py`, `tools/mkvariant.py` (pass `--src bots/god22`), `tools/paired_groups.py`, `tools/abstat.py`, `tools/sdk_apidiff.py`, `tools/fueltrace.py`;
  - `tools/replay/decode.mjs`;
  - `tools/analysis/{stuck,death_ctx,coord_audit}.mjs`;
  - `experiments/ladder_oct26_v74/fetch_dec.py`, `mk_sides.py`;
  - `experiments/ladder_oct26_top/*.py`, `experiments/top3_oct27/*.py`;
  - `tools/mapintel/catalog.py`, `archetypes.py`;
  - `bots/probe-rules`.

## Verification

- **Null check:** god22 with all switches off gives rows identical to `gpta75`.
- **Probe-bot runs** confirm each Phase 1 rule finding (draft fuel, hidden-blocker retry, ward behaviour).
- **Every candidate:** abbench rows against v75, v17 and the IC clone on `s3`, `gen2`, `gold3` and `var17`, with margins and confidence intervals in the doc.
- **Behaviour metrics before and after:** solo fights, split fights, roaming, stuck episodes, ward coverage.
- **Ladder:** after your upload, the 28 IC and Mite paired groups compared map by map against the Phase 3 baseline.
