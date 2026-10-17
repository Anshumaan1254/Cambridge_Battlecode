# AGENTS.md: handoff context for AI agents (and humans)

Read this first. It records what has been done on this bot, what was measured, what failed, what is
running or unfinished, and what to do next, so a new agent can continue without the original chat.

- Last updated: 2026-10-17, ~08:45 UTC. Branch `claude/laughing-curie-3rq6hu` (do not open a PR unless the user asks).
- Competition: Cambridge Battlecode 2026a (CAMBC), 12 Oct to 18 Nov 2026. C++ bot compiled to wasm.
- The submitted bot cannot be changed after submission and keeps nothing between matches. All "learning"
  is either offline (training parameters before submission) or in-match (adapting inside one game).

---

## 0. Status right now (read this if nothing else)

| Item | State |
|---|---|
| Bot | `bots/legend/src` (C++). Ready-to-upload bundle: `submissions/legend.zip` (rebuild after every change, section 3) |
| Current legend | = `_r2` (fuel fixes, review fixes, reworked learner) + exploration off + refreshed draft values + **the economy patch** (`experiments/patches/x_econ.patch`, merged Oct 17). Build log with every submitted zip: `submissions/BUILDS.md`; older zips in `submissions/history/` |
| Strength (45-map panel, 90 games per cell) | economy patch on `_r2`: 60% head-to-head vs `_r2`, panel mean 79.1% (vs `_r2` 77.6%). Promoted legend vs `_v6` (12 ladder maps): 17/24, 0 faults, 1.8 lost turns per game. Full numbers in section 5 |
| In flight | (1) Full-panel A/B of two finished prototypes, economy and spells, saved as patches in `experiments/patches/` (section 6). (2) A workflow building three more prototypes: decision maths, routes, ML fight model (local only, `bots/_x_math`, `bots/_x_route`, `bots/_x_ml`). (3) The parameter trainer (ES) has to be re-run on the final code (it died after 4 of 10 generations when the container restarted) |
| Next | Merge the prototypes that win, re-run ES, re-validate, rebuild the zip, update README/STRATEGY tables, commit, push (section 8) |

---

## 1. What the user asked for (all requests in this chat)

1. Learn the repo and keep looking for improvements. "We are winning, but when losing we lose by a little,
   rarely by a big margin." Problems the user named:
   - we do not use **recall** and lose too much time walking;
   - the **draft** does not pick strategic champions: analyse each map, then pick for it;
   - in fights there is **no backup**: everyone goes out, we all die and are locked out for a long time.
2. Make the learning better: **reinforcement learning** with a **reward/punishment** system that learns
   from mistakes, keeping in mind that the submitted bot cannot be updated.
3. Use the strategy plan (`CAMBC_2026a_Strategy_Plan_1.md`, uploaded by the user, not in the repo), other
   people's views, and the uploaded match results (4 zip match groups, 24 ladder losses). Analyse our moves
   and the enemies' moves, find out why we lost, and fix it. Search the internet for better strategies.
4. (Second message) **Use gold**: shards, emblems, "upgrade abilities". **Check the maths** in decisions.
   Use **decision trees, XGBoost, RL soft updates, epsilon-greedy, content-based filtering**, deep learning
   or RL concepts **only if they make the bot better**. Choose **optimal paths**, and work out **when to
   optimally use powers** and items.
5. (Third message) Write this context file and push it, top priority.

---

## 2. Game and engine essentials (full evidence in `docs/ENGINE_FACTS.md`)

- First team to 1000 banked gems wins (round limit 2000). Champions farm camp groups (wolf, elk, gem and
  gold clusters, monolith), capture rewards (gems + gold), carry gems and **tribute** (bank) them at an
  altar. A tribute takes max(1, ceil(gems/10)) turns; damage does not cancel it, a stun or death does.
- **Recall**: 5 turn ends; *any* damage cancels it. Health is restored only after a turn ends on spawn.
  Recall while capturing: step on the reward tile in round T, start the recall at T+1 or later, and the
  reward lands with the teleport.
- **Respawn** takes 60 rounds. Cassi & Issac are one pick but two bodies, and they die together.
- **Turn order**: camps act first; team A leads odd rounds, team B even rounds. Within a team, higher
  `set_priority` acts first (it applies from the next round).
- **Fuel**: 100k per turn (200k on a champion's first turn, 1M on the first draft turn). A turn that runs out
  **continues in the next round, so that champion loses a whole round** (counted as "Turn rollover" in
  replays). Host calls (distance-field get, `bitboard::is_set`) cost ~50-60 fuel each; a full distance
  field costs 13-19k. **Bitboard exports are bit-packed** (LSB first); distance-field exports are uint16 per tile.
- **Shared memory**: 8 bytes for the whole team (bytes 0-5 hold claims plus 2 stance bits, bytes 6-7 one
  team alert). Draft memory is 1024 bytes.
- **Items**:
  - Every shard costs 30 gold and adds 1 point of its stat (growth per point: health +100, or +71/+75/+95
    for some champions; strength +5 (+4); focus +10 (Cassi +15)). Five shards of one family combine
    automatically into an emblem.
  - Emblem bonuses: Monster +10% camp damage, Jungle −30% camp damage taken, Durability −10% damage taken,
    Treasure +20% gold, Home faster recall. These passives do not stack within a family.
  - Power emblem = 6 points of one stat. Bruiser emblem = 5 points + 1 of each other stat.
  - Shopping only on spawn or while dead (Tavi anywhere). Consumables: teleport crystal (hops up to
    Chebyshev 3 over walls and holes), altar lock, ward.
  - **No item upgrades abilities directly**: focus is the ability stat (spell = modifier × focus, Ren's
    retaliation = 0.2 × focus per hit, Varg's shield = 2.5 × focus). Cooldowns are fixed at 8 rounds.
- Matches are **deterministic** for fixed bots and map: never repeat a game; variance comes only from
  more maps and opponents.

---

## 3. Repo map and how to run things

```bash
pip install cambc && cambc init .              # SDK into sdk/ (git-ignored); choose C++
tools/make_sparring.sh                         # recreate the git-ignored sparring panel (bots/_*), verified identical
cambc build legend
python3 tools/bench.py legend _v6 --maps 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a'   # 90 games, ~40 s on 4 CPUs
tools/panel.sh legend 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' _v6 _hunt _hunt2 _devci _base
rm -f submissions/legend.zip && cambc bundle legend --output submissions/legend.zip                # submission bundle
```

| Path | What |
|---|---|
| `bots/legend/src/` | the bot: `brain.*` decisions, `world.*` perception/memory, `nav.*` distance fields and stepping, `comms.*` shared memory, `learn.*` in-match learners, `draft.cpp` composition choice, `params.h` every tunable |
| `bots/_*` | **git-ignored** local bots: sparring opponents, prototypes, variants. Recreate the panel with `tools/make_sparring.sh` |
| `experiments/patches/` | the finished prototypes as patches against `_r2` (apply on legend: `cd bots/X && patch -p1 < ../../experiments/patches/x_econ.patch`) |
| `maps/*.map26a` | 27 generated maps. `maps/ladder/`: 12 real ladder maps rebuilt from replays. `maps/comp/`: 6 official maps (SDK 2.1.6 pool, from the public Tarot Club repo; the other 3 official maps duplicate ladder ones) |
| `tools/bench.py`, `tools/panel.sh` | A-vs-B on every map, both sides, in parallel; one summary line per opponent |
| `tools/variant.sh`, `tools/snapshot.sh` | build a param/define variant (`SRC=bots/X tools/variant.sh NAME key=val --define "M v"`); freeze a past commit as a bot |
| `tools/replay/decode.mjs` | replay decoder using the engine's own wasm: per-round state + events (`{rollovers: true}` keeps fuel rollovers); `report.py`, `extract_map.mjs`, `mapinfo.mjs`, `mapfeatures.mjs` |
| `tools/rl/es_train.py` | offline RL: evolution strategies over `tools/rl/space.json` (29 params), shaped reward, uses bots/legend's params.h as the start |
| `tools/draft_tournament.py`, `tools/draft_model.py` | composition round robin (per-map wins and gem margins); nearest-map draft model with leave-one-map-out validation (`--vs` scores against a chosen field) |
| `tools/analysis/` | item-value model (`item_value.py`), spell usage (`spell_usage.mjs`), decision-formula audit (`xm_audit.mjs`), bag/recall risk (`xm_econ.mjs`), route time use (`route_stats.mjs`) |
| `docs/` | `STRATEGY.md`, `ENGINE_FACTS.md`, `HLD.md` (architecture), `LEARNING.md` (RL), `FEEDBACK_LOOP.md` (ladder replay loop) |

**Sparring panel** (all from `tools/make_sparring.sh`):
- `_base`: old v5, what was on the ladder.
- `_v6`: commit 58c2fe4.
- `_r2`: commit 4a3920d.
- `_hunt`, `_hunt2`, `_devci`: aggressive archetypes on the 58c2fe4 code, using the drafts of the top ladder teams.
- Also available: `starter-cpp`, and `idle` (never moves; used to measure unopposed pace).
- `_r1` (review fixes without the fuel fixes) was a local intermediate and cannot be recreated exactly.

**Gotchas that cost us time:**
- **Never use `pkill -f` / `pgrep -f` / `killall` with patterns**: they matched and killed the agent's own shell
  several times. To wait for a background job, wait on that script's own PID
  (`ps -eo pid,args | grep "[s]cratch/x.sh" | grep -v "bash -c"`). The shell that launched it lingers, so
  pattern-waiting deadlocked once.
- Launch long jobs from a script file with `nohup script > log 2>&1 &`; container restarts kill them
  (the ES run died this way).
- **Noise**: one 90-game result has a standard deviation of about ±5 points, so judge changes on the
  average over 5-6 opponents, and treat gaps under ~4 points as noise. Identical code differing only in fuel
  use can move a result by ~3 points.
- `cambc` toolchain download failed TLS once: wasi-sdk-33, cmake-3.31.8 and ninja-1.12.1 were fetched
  manually into `/root/.cache/cambc/` with `--cacert /root/.ccr/ca-bundle.crt`.
- The platform API (`2026a.battlecode.co.uk`) is blocked from the cloud container; the user must download
  ladder replays and match JSON themselves.
- Building and running other teams' bot code (the Tarot Club clones of the top teams) was blocked by the
  permission classifier as untrusted code; only their map files were used. The user can allow it if wanted.
- With 4 CPUs a Workflow runs only 2 agents at a time, and the account's session limit has cut workflows
  twice. Keep workflows small, and save findings to files as you go.

---

## 4. What has been implemented (chronological, with evidence)

**Commit 58c2fe4: first rewrite, built from 24 decoded ladder losses** (we had lost 17 of 20 scrims).
- **Farming of big packs.**
  - The camp score now counts Varg's splash, area spells, Ren's retaliation, allies, up to 5 heal trips,
    and lets a second body join heavy packs.
  - The 3-wolf-pack ladder map went from losing 132-1012 to the starter bot to winning.
- **Recall loop.**
  - Recall while capturing (the reward lands with the teleport), after banking far away, to shop, and to
    bank at the altar next to spawn.
  - Never recall when an enemy seen in the last 2 rounds is within 7 tiles; cancel when a threat closes in.
  - Unopposed pace improved from 574 to 500 rounds.
- **Fights (`combat()`).**
  - Advantage = (our HP / their DPS) / (their HP / our DPS), counting allies' spells.
  - Escape feasibility: fight back against chasers we cannot outrun; stun the chaser; melee champions
    swing after their step.
  - Never trade with enemies healing on their spawn.
  - Backup counting; early retreat when isolated; a higher fight bar with half the team dead.
  - Respawn escort: when down 2+ bodies, wait on spawn for the next ally instead of walking out alone.
- **Turn order:** dynamic `set_priority` (fighters act first).
- **Draft:**
  - Ren, Stellar, Cassi & Issac, Ryth, Varg ("meta"), chosen from a 780-game composition tournament;
  - the same draft the strongest ladder team uses.
- **Builds.**
  - Durability/Jungle health, then Monster, Treasure, Power.
  - Won 65% head-to-head against the old builds.
- **Crystal shortcuts** over hole mazes, and island camps.
- **Learning** (`docs/LEARNING.md`):
  - offline: ES trainer;
  - in-match: team stance bandit (SPREAD / GROUPED / PUSH), pain map of where we died, per-champion
    fight calibration.

**Commit 4a3920d: lost turns, review fixes, learner rework.**
- **Fuel.**
  - On the 98x99, 48-group map the team lost **566 of ~2,700 champion turns** to fuel rollovers; now **12**
    (just the two heavy opening turns per body).
  - Causes fixed:
    - emblem checks that recounted the build for every group, every turn;
    - all groups scored every turn: the loop now scores the current and nearby groups first, under a
      fuel floor;
    - the hop scan read bit-packed exports as bytes and checked fuel only per row: it now reads bits,
      resumes per tile, stops after a pause, and is skipped when no hop can pay;
    - splash clusters recomputed every turn: now only when a camp dies or respawns;
    - the pain map decayed every turn: now lazily, every 8 rounds.
- **Review fixes:**
  - the respawn escort now waits: allies that died while this body was dead get their real death round;
  - a dead group's reward is captured before any home or shop trip;
  - when the altar is unsafe, banking via recall and the spawn altar is tried before giving up;
  - a cancelled tribute is not restarted in the same turn;
  - a nearer claimer captures a reward even when a lower-index ally also claims it;
  - DANGER alerts no longer overwrite RALLY or OPPORTUNITY;
  - champions hold on spawn instead of bouncing on and off it;
  - the spawn-heal bonus counts only for fights on spawn;
  - capture-recall starts in the right round;
  - failed hops are dropped.
- **Ablation (leave-one-out, 78 games × 4 opponents):** priority alternation (double turns) and the
  "shielded camp" retreat rule each cost 7-17 points and are off by default. Rest-on-spawn is worth up to 17
  points; it stays, with sticky tributes and the claim tie-break.
- **Stance learner:**
  - rewards in gem units: kill +25, death −45, banks smoothed over two windows;
  - soft (EMA) update;
  - UCB exploration and a pull back to priors (both now off, see below);
  - death locations only from fresh sightings.
- **Draft model hook:**
  - `draft.cpp` reads an optional `draft_table.h` produced by `tools/draft_model.py`;
  - without it (the current state) the draft is unchanged.

**Commit aece821: draft values** from an 8-draft × 45-map tournament (2,520 games, section 5). At team size 4,
Varg as the 4th pick now beats Ryth.

**Commit 564785f: stance exploration off** (measured −2 points; section 5).

**Analysis tools** (commits 5cf8001 to e751b1b): `tools/analysis/*` (see section 3).

---

## 5. Measured results (latest first)

All on the 45-map pool (27 generated + 12 ladder + 6 official), both sides: 90 games per cell, win rate %.

**Round 3 (stance-learner A/B on `_r2`):**

| Bot | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | `_r1` | Mean |
|---|---|---|---|---|---|---|---|
| `_r2` (learner, UCB 0.3) | 74.4 | 88.9 | 94.4 | 63.3 | 87.8 | 56.7 | 77.6 |
| learner off | 78.9 | 82.2 | 93.3 | 66.7 | 93.3 | 62.2 | 79.4 |
| learner, no exploration (**now default**) | 77.8 | 90.0 | 96.7 | 66.7 | 86.7 | 62.2 | **80.0** |

**Round 2 (review fixes and retreat threshold):**

| Bot | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | Mean |
|---|---|---|---|---|---|---|
| `_m1` (before the review fixes) | 48.9 | 87.8 | 72.2 | 45.6 | 83.3 | 67.6 |
| `_c1` (`_m1` + the 2 harmful toggles off) | 54.4 | 83.3 | 85.6 | 50.0 | 82.2 | 71.1 |
| `_r1` (+ review fixes) | 60.0 | 86.7 | 90.0 | 64.4 | 83.3 | 76.9 |
| `_r1` + `retreat_hp` 0.40 | 64.4 | 82.2 | 88.9 | 67.8 | 83.3 | 77.3 |
| `_r1` + `retreat_hp` 0.50 | 67.8 | 85.6 | 84.4 | 65.6 | 84.4 | 77.6 (noise; left to ES, range up to 0.55) |
| `_r1` without the claim tie-break | 65.6 | 87.8 | 86.7 | 60.0 | 81.1 | 76.2 (noise; kept) |

**Draft tournament** (8 drafts, same code, mean win rate vs the field):

| Draft | Mean | Worst |
|---|---|---|
| `metaV` (Ren, Stellar, C&I, Varg, Ryth) | 0.590 | 0.489 |
| `meta` (Ren, Stellar, C&I, Ryth, Varg) | 0.581 | 0.500 |
| `vci` (Vendetta, C&I, Varg, Stellar, Ren) | 0.565 | 0.500 |
| `civr`, `ryt`, `tav` | 0.49-0.52 | |
| `ven2` (Tarot's Vendetta/C&I/Varg/Tavi/Vesper) | 0.421 | |
| `wil` (Willow-based) | 0.321 | |

- The **nearest-map draft model** (content-based: "maps like this one") beat the team-size choice by +2 to
  +4 points in leave-one-map-out validation against the whole field.
- Against only the strong drafts it gave no gain. With ~6 games per map per draft, per-map differences are
  noise: `meta` and `metaV` are identical at team size 5, yet scored 0.500 vs 0.467.
- So it is **not shipped**; the hook and the tool are ready for when more real maps and replays exist.

**Round 4 (prototypes vs the panel; same learner setting as `_r2`):**

| Bot | vs `_r2` | `_v6` | `_hunt` | `_hunt2` | `_devci` | `_base` | `_r1` | Mean (excluding `_r2`) |
|---|---|---|---|---|---|---|---|---|
| `_r2` (round 3) | — | 74.4 | 88.9 | 94.4 | 63.3 | 87.8 | 56.7 | 77.6 |
| `_x_econ` (economy patch) | **60.0** | 74.4 | 90.0 | 92.2 | 73.3 | 83.3 | 61.1 | **79.1** |
| `_x_spell` (spells patch) | running | | | | | | | |
| `_x_combo` (econ + spells) | queued | | | | | | | |

**Earlier (39-map pool, the first rewrite):**
- The old bot (v5) won 88% vs the starter bot, 42% vs `_hunt`, 28% vs `_hunt2` and 14% vs `_devci`.
- The rewrite won 100%, 87%, 82% and 55% respectively.
- Unopposed pace: 574 → 500 rounds.

---

## 6. Analyses and findings (what the data said)

**Why we lost on the ladder** (24 decoded replays; `docs/STRATEGY.md` §1):
- Death cascades: 12.2 deaths per match vs their 4.0. Half came with no ally within 6 tiles; many came
  while fleeing same-speed chasers.
- Big packs went unfarmed.
- They recall as transport (at 58-73% HP, 22-49 times per game); we recalled only in emergencies.
- They act first in fights (`set_priority`).
- Every top team drafts Cassi & Issac.
- Spawns that touch caused a stalemate.
- Our HP builds were too low (they reach 1800-2000 HP).
- One opponent (group 8694af79) is the ladder team "ifish" (draft Ren, Stellar, C&I, Ryth, Varg).

**Web research** (public repos; the best source was Tarot Club, github.com/FHL-08/Tarot-Club-Cambc2026,
cloned read-only to `/home/user/fhl-08/tarot-club-cambc2026` in this container):
- **Top teams' habits:** ~220 casts per game; recall at ~0.46 HP and never under threat; camp parking
  (wait on a cleared camp until it respawns); spend all gold; a grouped opening, then split the map into
  sectors; a disable-chain to focus fire.
- **What failed for Tarot:**
  - pulling allies into a teammate's fight cost 17 to 401 gem margin;
  - forcing the whole team onto one camp won only 3 of 18 games;
  - a full kill-race rewrite won 0 of 18.
- **Deep RL** at Lux-AI scale cannot fit in 100k fuel. Feasible instead: SPSA/ES parameter tuning, and
  tiny MLP gates trained to imitate replays.

**Economy** (`_x_econ` agent; `tools/analysis/item_value.py`):
- Gold is not wasted: 91-97% is spent, and gold held away from spawn is small (12-45 per champion).
- What was wrong:
  - **no Bruiser** emblems (7 stat points vs Power's 6, at the same 150 gold);
  - the rich champions' build lists **ran out** (Ren once had 948 gold unspent);
  - Cassi & Issac are gold-poor (~580 gold per game) yet bought damage first, while dying together
    6 times a game;
  - Treasure came too late.
- The prototype fixes all four, and counts Monster's +10% in the kill-time estimate:
  - its own tests: 21/24 vs `_v6` (`_r2`: 17/24), 20% fewer deaths, +15% gold;
  - full panel so far: 60% head-to-head vs `_r2`;
  - its weak spot is pure farming races, ~20 rounds slower.

**Abilities** (`_x_spell` agent; `tools/analysis/spell_usage.mjs`):
- Spells are ready on 66-84% of turns but used on only 21-40%, mostly because there is no target in range
  or the champion is walking (damage spells cannot be cast in a turn that walks).
- Three fixable losses:
  1. Ryth's area stun was never cast from range: 5.6 stuns per game on champions despite ~36 fight turns
     with it ready.
  2. Fleeing champions never stunned a chaser that would hit them anyway.
  3. Spells on camps were held whenever an enemy was within 9 tiles, but a fight followed within the
     cooldown only 13% of the time at 7-9 tiles (51-63% at 5-6).
- Already fine: attack resets, Varg's shield timing, stun timing relative to the target's turn, wards,
  altar locks, crystals.
- Prototype: 55.6% vs `_r2` over 36 games, 13% fewer deaths, Ryth's champion stuns ×3; full panel pending.

**Maths of decisions** (`docs/STRATEGY.md` §3-4):
- The decisions are explicit models:
  - camp value per round = (gems + 0.22 × gold) / (travel + wait + kill time + 6 capture rounds + heal trips);
  - kill time from real DPS (splash, spells, retaliation);
  - damage taken from the nearest-champion rule and emblems;
  - fight advantage in the Lanchester style (HP over enemy DPS, counting allies and stuns).
- A calibration audit against replays (predicted vs actual kill time, damage, fight outcomes) was being
  built when the session limit hit (`tools/analysis/xm_audit.mjs`); it is being re-run now.

**Learning (RL)**:
- In-match stance learner: neutral (±2 points); exploration hurts (a game has only ~25 decision windows).
- Offline ES: the main learning path. Each generation samples 8 maps, so its "mean reward" moves with the
  map sample; judge it only on a fixed panel after training.

---

## 7. Unimplemented / open work (by priority)

1. **Decide on the prototypes**:
   - finish the econ, spell and combined panels;
   - merge the winners into `bots/_dev` and `bots/legend` (patches in `experiments/patches/`);
   - re-run the 6-opponent panel; keep a change only if the 5-6-opponent mean improves by more than ~3
     points, or the gem margin improves clearly with no regression.
2. **Maths, route and ML prototypes**: a Workflow is building them now (`bots/_x_math`, `bots/_x_route`,
   `bots/_x_ml`, local only). The workflow script is
   `.../workflows/scripts/legend-decision-upgrade-*.js` in the session dir; if it is lost, the brief for each
   is below.
   - *Maths*: log each formula's predictions (kill time, damage taken, trips, fight advantage) and compare
     with the replay outcome; refit the coefficients; fix unit errors; consider Lanchester N² for
     multi-body fights.
   - *Route*: measure time shares (walk, farm, capture, wait, bank, home); then two-step lookahead (pick a
     group by its value plus the best follow-up), team assignment of groups to avoid duplicate walks, wait
     on camps that respawn soon, danger-weighted paths. Must stay under the fuel budget.
   - *ML*:
     - log the `combat()` features and the decision taken;
     - label outcomes from replays (death within 12 rounds, kill within 12 rounds);
     - compare the current formula with logistic regression, a decision tree, gradient-boosted trees
       (XGBoost if installable, or sklearn) and a tiny MLP, by AUC with a game-level split;
     - export the winner to C++ (if/else trees or constexpr weights, < 3k fuel per call) only if it
       clearly wins.
3. **Re-run ES on the final code**:
   ```bash
   python3 tools/rl/es_train.py --space tools/rl/space.json --opponents _v6,_hunt,_hunt2,_devci,_r2 \
     --maps 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' --gens 10 --pop 4 --maps-per-gen 8 --jobs 4
   ```
   Then `tools/rl/apply_params.py tune_out/es/best_params.json` on a copy, validate on the panel, and keep
   the result only if it wins. ES reads its starting values from `bots/legend/src/params.h`.
4. **Ship**: sync `bots/_dev/src` into `bots/legend/src`; rebuild `submissions/legend.zip`; update the
   results tables in `README.md` and `docs/STRATEGY.md`; commit and push.
5. **Ideas not yet tried** (from research and analysis):
   - camp parking (hold a cleared camp until it respawns);
   - a grouped opening then map sectors (note: our earlier "deathball" opening lost);
   - a shared focus-fire target in comms (shared memory is full: it needs a redesign);
   - altar locks on enemy-side altars;
   - capture-overlap tribute (start a 1-tick tribute next to an altar as a capture lands);
   - the Home emblem for recall-heavy play;
   - sending captures to gold-poor champions;
   - imitation gates trained on top-team replays.
6. **Feedback loop with the real ladder**: the user downloads new ladder replays, then decode them, extract
   new maps into `maps/ladder/`, re-run the draft tournament and ES (`docs/FEEDBACK_LOOP.md`). Our sparring
   bots are archetypes of our own code, so real teams will differ.

---

## 8. Setbacks and things that did not work (do not repeat blindly)

| Idea | Result | Where |
|---|---|---|
| Priority alternation for double turns (+/-1000) | −8 to −17 points head-to-head | `prio_alternate = 0` |
| Retreat counting only "unshielded" camps | −10 points (champions stayed out at lower HP) | `safety_v2 = 0` |
| Pair plans (wait for a partner on heavy packs) | 24 rounds slower unopposed, no win-rate gain | `pair_plans = 0` |
| Early deathball opening | lost to spread farming | `deathball_until = 0` |
| First untuned online learners | −10 points until the combat model was fixed | — |
| UCB exploration in the stance bandit | −2 points over 540 games | `ucb_c = 0` |
| Nearest-map draft model | no gain against strong drafts (noise) | no table shipped |
| Treasure-first builds for Ren/Stellar | worse than Treasure second (19/24 vs 21/24) | `rich_treasure_first = 0` in the econ patch |
| Hop scan v1 | read bit-packed exports as bytes and overran fuel (bodies lost 13-14 of their first 40 turns) | fixed in 4a3920d |
| Process handling | `pkill -f` killed our shell; a pattern-based wait deadlocked; container restarts killed ES at generation 4; session limits cut two workflows | see the gotchas in §3 |

---

## 9. What we are thinking right now (next actions, in order)

1. Read the round-4/5 panels:
   - if the econ + spells combination beats `_r2` on the mean, merge both into `_dev`;
   - otherwise merge only the one that wins.
2. When the maths/route/ML workflow returns, A/B each prototype in the same way, and merge the winners
   (the ML fight model only if it beats the formula offline *and* in games).
3. Sync to `legend`, re-run ES on the final code (fixed panel, 10 generations), validate, bake in the parameters.
4. Final panel (including `starter-cpp` and `idle` pace), rebuild the zip, update README/STRATEGY/LEARNING,
   commit, push, report to the user.

---

## 10. Conventions

- Commit messages end with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01HwDbgTPDFYPU6J7emgx9Ev
  ```
  Push with `git push -u origin claude/laughing-curie-3rq6hu`. No PR unless asked.
- Code style:
  - tabs;
  - comments explain *why*, with the measured evidence;
  - every tunable lives in `params.h` with a comment;
  - every engine action is wrapped in try/catch;
  - every new loop is checked for fuel cost (count rollovers with `decode(..., {rollovers: true})` on
    `maps/gen16_98x99_V_c5.map26a`).
- Every behaviour change gets a switch in `params.h` and an A/B on the panel before it becomes the default.
  Record the result in the param's comment and in `docs/STRATEGY.md` §7.
- Work on copies (`bots/_dev`, `bots/_x_*`) and benchmark frozen copies; never rebuild a bot a running
  benchmark uses.
