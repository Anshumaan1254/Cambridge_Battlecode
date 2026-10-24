# TEAMPLAN.md: team play, navigation and the draft-memory layout for the user's new bot (session 18c, from Oct 24 2026)

This file records one strand of work running next to the map analysis (`MAPAnalysis.md`):
- how the team's bodies share the farming, the gold and the gems;
- when they fight;
- how roles change during a game;
- how the 8 live bytes and the 1,024 bytes of draft memory are used;
- navigation under the fuel limit.

**Who works where**:
- **This work**: `TEAMPLAN.md`, `tools/teamplan/` (Python), `tools/teamplan/cpp/teamplan/` (header-only C++), `docs/DRAFT_MEMORY.md` (the
  final draft-memory layout), and a git-ignored GOD v10 test copy built by a script. It does not edit the map-analysis files.
- **The other Claude**: the map-analysis work (`MAPAnalysis.md`, `tools/mapintel/`).
- **The handoff**: at the end of this work, the other Claude gets a prompt to implement the final draft-memory state in its library.

---

## 1. The user's requests (Oct 24, quoted) and decisions

### 1.1 Draft memory
"now as that runs i want to think of different ways of using the draft memory of 1024B tell me about that"

### 1.2 Farming, gold, roles, role swaps; argue against every idea; modular
"For the ideas ranked by expected value should we let a body farm and would it cause some different altercation like if our farms bots
would also get gold which would help them buy more emblem and hence can engage enemy to slow them down while the other body also farms to
get the gold and gems or we can make it such that farm bodies let the frontliner take gold with them to upgrade also if a frontliner is
lagging we can switch jobs to test the other option out using some method as well (We have tinyml in mind but you are open to counter
with some other technique) also if you think this is not give counter points so that we can confirm also do this for each suggestion as
well counter it yourself if it is still effective compared to its counterparts then implement it also whenever possible make modular and
changes that are open for further patchnotes and maps"

### 1.3 Who builds, and on which bot
Two answers to my questions:
- "Who should build the parts that survived the pro/con review?" → **"Me, in the repo"**. This lifts the user's earlier "don't write in
  repo" for this work.
- "Which bot should the test games use before your new bot exists?" → **"do both offline and v10"**.

### 1.4 Postmortems
The uploaded `postmortem-2023-gone-fishin.pdf`: "see the uploaded postmortem for the ideas and strategy improvement and other postmortem
too on thios website https://battlecode.org/past.html".

### 1.5 Navigation
The user pasted a postmortem excerpt on "4.1.1 Unrolled BFS / 4.1.2 Bug Nav / 4.1.3 BugBFS": "think about this in map analysuis and other
appropriate location too".

### 1.6 Tiebreak (clarification)
"I meant whenever you sense a tiebreaker than only we will submit the gems at last else we will also be racing for finishing".

### 1.7 Documentation and handoff
"note evrything in the md filkes" and "after this completes give me a prompt to be givcen to other claude rto implement the final memory
stafe".

### 1.8 Standing rules (unchanged)
- **Git**:
  - commit and push to `main` at every step;
  - `git pull --no-rebase origin main` before every push;
  - never force-push; no pull request;
  - end commit messages with the session's attribution lines.
- **No hardcoding**: no champion names or map identities in logic. Champions are read from the engine (designs, `passive_type`, SDK
  constants). The exact-match map table is the only approved exception (map analysis).
- **No shipping**: `bots/god` and `submissions/` are not edited and no bot is shipped. Test bots are git-ignored copies built by scripts.
- **Process and data safety**:
  - never `pkill -f` / `killall`: kill by PID;
  - never handle the user's credentials;
  - never use or commit the personal PDFs from session 13;
  - map names stay unique under `maps/`.
- **Subagents**: few; Fable for the main / heavy tasks, Opus below that, then Sonnet, Haiku only for the smallest; the core reasoning
  is done here.
- **Pace**: report after each step and keep going; the user answers slowly.

---

## 2. Facts this work relies on (rules `docs/sprint/v3_0_4/GameRules.md`, SDK 3.0.5 `sdk/cpp/cambc.h`)

**Capture**:
- After every camp of a group dies, the team holding a spawn tile of the group uncontested for 5 rounds captures it.
- **The reward is split evenly among the allies present when it finishes; the lowest ID gets the remainder. More allies do not speed
  it up.** So one body can capture while the others move on.

**Death and bags**:
- **A champion killed by an enemy gives the killer all its carried gems + 100 gold.** A camp kill destroys the carried gems.
- **Gold is never lost**: dead champions keep it and can still shop.
- Respawn takes 60 rounds. Cassi and Issac die together and give one kill reward.

**Income passives** (readable: `champion.passive()` → `passive_type`, and SDK constants):
- `bonus_gold` (Vesper Vale, `vesper_vale_bonus_gold_percent` 33; Treasure adds 20 points);
- `stun_immunity` (Marcella, also `marcella_tribute_gold_per_gem` 2);
- `gem_focus` (Prism, `prism_focus_per_gem` 1.5).
- The other passives: `splash_attack`, `health_strength`, `reset_cooldowns_on_kill`, `retaliation`, `missing_health_damage`,
  `remote_shop`.

**What a body can read**:
- **only its own gold** (`gold_count` requires self);
- an ally's or enemy's items and carried gems only while it is in sight;
- vision is not shared between allies;
- **both teams' tributed totals** (`global_submitted_gems(team)`); gold earned and kills are not exposed.

**Tribute**:
- It lasts max(1, ceil(bag / 10)) of the owner's turn ends.
- It is cancelled by a stun, a death or an altar lock (5 hits); damage does not cancel it.
- Several tributes run in parallel at one altar.
- At round 2000: tributed gems first, then gold earned, then kills; then team B.

**Draft**:
- One pick round per team-size slot (3-5 rounds); **both teams pick at the same time**. Our pick in round k sees the enemy's picks of
  rounds 1..k-1, so **our draft never sees the enemy's last pick**.
- A draft bot that crashes or runs out of fuel without picking gets random picks for the remaining rounds. So: pick first, then
  compute.

**Draft memory**:
- 1,024 bytes, written only by the draft bot, only during the draft. After that it is frozen ("Draft memory is read-only after the
  draft", SDK error 20). The enemy cannot read it.
- **A write always starts at offset 0. A shorter write leaves the later bytes unchanged; the last write wins.**
- Each champion process reads a snapshot of all 1,024 bytes once at its own startup.
- The draft bot keeps its RAM between draft turns (the mapintel test bot keeps its state across turns 1-3).

**Fuel**:
- 1,000,000 on the first draft turn, 100,000 on later draft turns, 200,000 on a champion's first turn, 100,000 on every other turn.
- Measured by the map analysis (MAPAnalysis 7.2):
  - a simple wasm loop costs about 50-75 fuel per step;
  - a host distance field 1.3-31k (13-19k for a full map), a field `get` about 68;
  - zero-filled buffers about 1.2 fuel per byte; stdout about 90 fuel per byte;
  - fixed-size (unrolled) templates cut a model from 48k to 22k.

**Live team memory**: 8 bytes, readable and writable all game.

**Turn order (measured in step 2 on a decoded top-team replay, rounds 30-400)**:
- **Champion turns alternate between the teams, one body at a time** (A, B, A, B, ...). In 333 of 371 rounds the sequence alternated
  exactly; the rest had a dead or absent body, so the larger team's last bodies acted back to back.
- **The starting team swaps every round**, and within a team higher priority acts first.
- **Consequence**: for two opposing bodies of equal rank, the order flips every round, so each gets two actions in a row relative to the
  other at every second round boundary. Example: A_k acts at the end of its pair in round r (B started) and at the start of its pair in
  r+1 (A starts).
- **Stepping into an enemy's reach is safe only when we act again before it does.** That is the "do not enter range first" rule of
  smite / Don't @ Me / Just Woke Up, and it is computable from the round parity, our team and the two bodies' ranks.

---

## 3. Evidence: 599 current-patch top-team games

**Source**: the decoded summaries `experiments/results/mapintel/ladder_20261024/*.json` (Oct 24 ladder download, engine 1.0.3, mostly
strong vs strong). They were measured in memory on Oct 24; the script lands in step 2 as `tools/teamplan/ladder_roles.py`.

**Who captures** (share of all capture gold / gems; gold per capture includes the gold passives):
| Champion | Captures | Gold share | Gem share | Gold per capture | Gems per capture |
|---|---|---|---|---|---|
| Vesper Vale | 11,309 | 32.1% | 26.2% | 165.3 | 22.8 |
| Marcella | 9,454 | 20.8% | 22.6% | 128.3 | 23.5 |
| Heart of Ruin | 8,197 | 14.7% | 16.4% | 104.2 | 19.7 |
| Vendetta | 6,762 | 13.5% | 13.7% | 115.9 | 20.0 |
| Ryth | 5,006 | 9.6% | 10.2% | 112.0 | 20.1 |
| Prism | 2,096 | 3.4% | 4.4% | 95.4 | 20.5 |
| Tavi | 1,732 | 2.3% | 2.7% | 78.2 | 15.5 |
| others (Varg, Issac, Willow, Cassi, Stellar, Ren) | 2,039 | 3.6% | 3.8% | | |

**Kills and gold sources** (per game played by that champion):
| Champion | Games | Kills | Gems its kills took | Capture gold | Kill gold as a share of its gold |
|---|---|---|---|---|---|
| Vesper Vale | 1,084 | 1.76 | 20.5 | 1,725 | 0.12 |
| Marcella | 989 | 1.71 | 17.2 | 1,226 | 0.12 |
| Heart of Ruin | 947 | 1.48 | 13.8 | 902 | 0.14 |
| Ryth | 748 | 2.31 | 19.7 | 750 | 0.24 |
| Vendetta | 724 | 1.68 | 18.0 | 1,083 | 0.13 |
| Prism | 208 | 2.16 | 19.9 | 962 | 0.18 |

**Team-level**:
- **Captures are solo**: 43,850 capture events, 5.4% shared by two or more bodies, 1.06 bodies per capture on average.
- **Bags at death**:
  - 10,312 deaths: 90% to champions, 10% to camps;
  - mean bag at death 10.1 (median 0); 35.5 when not empty;
  - Prism dies with the biggest bags (mean 26.7; 28.7% of its deaths carry 20+), then Vesper 12.0, Marcella 11.4, Heart of Ruin 9.9.
- **The bag swing**: winners take **102 gems** a game from enemy bags and lose **57**; losers take **50** and lose **116**. About 110
  gems, a ninth of the win target.
- **Gold concentration**:
  - the top body holds 47% of a team's capture gold (winners 0.467, losers 0.484);
  - melee bodies get 60% (winners) vs 65% (losers).
- **How games end**:
  - 583 of 599 by gems (median round 1,064, mean 1,117);
  - **16 (2.7%) reach the round-2000 tiebreak**;
  - 56 (9.3%) are close races (the loser has 900+ tributed).

**Data caveat, resolved in step 2**:
- **The decoder recorded a capture only when the bag grew** (`tools/replay/decode.mjs`, `CaptureGems`), so gold-only groups (200 of the
  836 official groups, 11% of group gold) were missing from the summaries.
- The decoder now has an opt-in `goldCaptures` option (`--gold-captures`) that adds `CaptureGold` events. It is off by default, so the
  20 existing readers of `CaptureGems` see no change.
- **On the 25 committed raw top-team replays** (`experiments/ladder_oct24/raw/`; `tools/teamplan/capture_rows.mjs` →
  `experiments/results/teamplan/caprows_raw25.jsonl`):
  - 500 of 2,480 captures (20%) are gold-only, 9.4% of all capture gold;
  - **front bodies take relatively more of them**: gold-only captures are 16% of Heart of Ruin's capture gold, 26% of Ryth's, 15% of
    Varg's, but only 7.3% of Vesper Vale's and 5.0% of Marcella's;
  - Vesper Vale still collects the most capture gold (36.8% in these games).
  - So the top teams do something close to U3': the gem-free groups lean to the front bodies, the gem groups to the carries.
- Full tables: `experiments/results/teamplan/roles_ladder.md` (`tools/teamplan/ladder_roles.py`).

---

## 4. Every idea, argued for and against, with the verdict

| # | Idea | For | Against | Alternatives | Verdict |
|---|---|---|---|---|---|
| U1 | Every body farms | top teams do; kill gold is only 12-24% of income | spread bodies get picked off; their bags feed the enemy | a non-farming front body (it would earn about 150-230 gold a game from kills instead of about 900) | **build**, together with the bag rules (U2') |
| U2 | Farmers with gold and emblems engage the enemy to slow them | a kill pays 100 gold + the victim's bag; the middle band is where our farming gap is | engaging with a full bag gifts it; death = 60 rounds out; emblems alone do not win fights | always farm; always fight | **build U2', bag rules**: fight with an empty bag; bank before a fight when the bag is big; hunt visible big enemy bags only with local numbers. Fight together: Cout for Clout's 47-vs-50 ablation lost 90% |
| U3 | Farm bodies let the frontliner take the gold | gold is never lost on death; emblems help the front win | top teams do the opposite (most gold to the gold-bonus body, 1.33-1.53x); the capturer also gets the gems, so a front body capturing gem groups carries a bag into fights | the greedy nearest capturer; a fixed gold rank by name | **replace by U3', the risk-matched capturer**. Per group, the capturer maximises gold x (1 + bonus) x w_gold(body) + gems x P(bank safely) − carry risk − time. That sends gem-free groups to exposed bodies and gem groups to safe ones; the others move on. Engine-derived, no names |
| U4 | Swap jobs when a frontliner lags, tested in game (TinyML suggested) | adapts when a game goes off plan | roles are kit-bound (a ranged caster cannot hold the front); a swap costs walking; trying the other option inside one game is no experiment; allies' gold is unreadable | fixed roles; threshold rules; an expected-value check; TinyML; an in-game bandit | **build U4', an expected-value check** with hysteresis (every N rounds, compare the current assignment with precomputed variants); the variant cursor sits in the live bytes. **TinyML only if that check fails in batteries**: no top Battlecode team reports ML tuning paying off (section 7) |
| D1 | Group ownership map (who farms what) | stops two bodies chasing one group; frees live bytes | rigid plans break on contact, deaths, respawn timing | live claims only; zones | **build as a soft owner bonus** + the capturer rule + variants (a body dead, roles swapped). smite (2019 winner) assigned resources centrally from one shared deterministic table |
| D2 | A codebook that makes the 8 live bytes say more | indices into draft tables (smite, 4 Musketeers) | rigid; fails if the memory is invalid | a fixed live protocol | **build, small**: variant cursor, rally tiles, zones, a progress code per body |
| D3 | Per-body briefing in draft memory | role, opening, build against the enemy | bodies can derive much themselves | the team plan only | **build only what a body cannot cheaply derive**: the plan-1 route, the build against the enemy picks, thresholds |
| D4 | Contingency tables | covers what the draft cannot know | the enemy's last pick changes little | adapt in game | **build small**: the enemy's last pick (builds, danger); deaths as ownership variants; early contact through the cursor |
| D5 | A static next-target table | zero cost in game | the best next group depends on live state | the model on a candidate list | **dropped**; θ(map) kept |
| D6 | Enemy model from their picks | anticipation | predictions fit top teams, weaker teams differ | none | **build as a soft input**: their predicted first targets, bank altars, likely big-bag carriers (by passive / kit) |
| D7 | Navigation aids | mazes, islands, camp-blocked altars | known maps carry them in the binary | in-bot search | **for unknown maps only** (the NAV block, section 6) |
| D8 | A debug block | replay analysis | bytes | stdout | **while developing** |
| P1 | Kill value = kill odds x (enemy bag + 100 gold + 60 rounds of absence) (Don't @ Me, food, SPAARK) | bags decide about 110 gems a game | chasing into their half | none | **build** as a target-score term, gated by our own bag |
| P2 | Live comms as indices into shared tables, one owner per field, everything expires (smite, 4 Musketeers, Lorem Ipsum, food) | no write races; stale data cannot mislead | 64 bits is tight | a free-form protocol | **build the spec** (`live.h`) |
| P3 | Precompute with full information; coordinate by identical computation instead of messages (XSquare 2020, smite) | the draft sees everything with 10x fuel | none | none | **the basis of the draft-memory layout** |
| P4 | "Do not enter range first"; exploit turn order (smite, Don't @ Me, Just Woke Up) | the opener wins fights | an enemy's rank inside its team is not observable (only estimated) | none | **build as `timing.h` + switch `tp_timing`**: the probe found the double move (section 2); step into reach only when we act again before that enemy |
| P5 | Score every candidate action in one currency (Cout for Clout +100 rating; Generalized Stroke's Theorem; SPAARK) | strong evidence | fuel; that is the new bot's combat code | v10's combat heuristics | **next batch (micro)**, after this one |
| P6 | Guess area casts into unseen tiles (Gone Fishin', 4 Musketeers; area spells need no sight, engine probe) | free damage | wastes an 8-round cooldown | none | **test** as a switch |
| P7 | Static guards, extra comms units, rushes | | failed for them too | | **not built** |
| T | **Tiebreak mode** (1.6) | section 5 | section 5 | section 5 | **build, risk-capped** (section 5) |

---

## 5. Tiebreak mode (the user's idea, 1.6), argued for and against

**For holding the gems until the end**:
1. **It hides our score.** Both teams can read each other's tributed total, so a bot that reacts to the score (as our own old
   `race_mode` did) misjudges who is ahead.
2. **Fewer altar trips mid-game**, so more farming time.
3. **Prism gains 1.5 focus per carried gem.**

**Against**:
1. **Every carried gem can be taken.** Winners take 102 gems a game from enemy bags, and our bags are visible to enemies in sight, so
   we become targets.
2. **One long tribute at the end can be denied.** A 300-gem bag needs 30 turns, and one stun, death or altar lock wipes it.
3. **Sensing a tiebreak can be wrong.** If the enemy reaches 1,000 first, gems in our bags count for nothing.
4. **It rarely matters**: 2.7% of top-team games reach round 2000.

**Verdict: build `tiebreak.h`, risk-capped.**
1. **Detect the tiebreak.**
   - The draft flags tiebreak-prone maps: the unopposed pace is near or over 2,000 rounds (map analysis), or there are too few gems.
   - In the game, both teams' projected finishes lie beyond round 2000 by a margin. Their rate comes from
     `global_submitted_gems(enemy)`; ours includes the team's carried bags. Hysteresis keeps the mode from flickering.
2. **In tiebreak mode, defer only within a risk cap.** A bag may grow while its holder is far from enemies, and is banked as soon as an
   enemy can reach it. The cap comes from a decaying danger score.
3. **The final tribute window.** Each carrier starts for a safe altar at round 2000 − (walk + ceil(bag / 10) + margin). Several altars
   and parallel tributes are used, so nothing is carried at round 2000.
4. **Denial in the last window**: lock enemy altars, stun enemy tributes, hunt big bags.
5. **Outside tiebreak mode, race to finish**: bank now whenever the bag wins the game (counting the team's other bags).

The information-hiding effect is measured on the GOD v10 test copy (against v10's own score-reading logic). That is v10-specific, so it
is reported, not assumed for the ladder.

---

## 6. Navigation (the user's BugBFS excerpt, 1.5), mapped to CAMBC

**How CAMBC differs from MIT Battlecode**:
- CAMBC gives **exact host-computed BFS distance fields** with custom walls and roots (`distance_field::compute(walls, roots, visited,
  max)`, `compute_to`), at 1.3-31k fuel per field.
- A wasm loop costs about 50-75 fuel per step, so a full BFS written in wasm would cost hundreds of thousands.
- Unrolling pays here too (mapintel: 48k → 22k for a model).
- **So the global path problem is solved by the host. What remains is dynamic**: allies and enemies blocking tiles, living camps, danger
  zones, dash and crystal moves, oscillation between targets, and fuel spikes on big maps.

| BugBFS part | In CAMBC | Against | Verdict |
|---|---|---|---|
| Unrolled global BFS | not needed: host fields are exact and cheaper | none | **no** |
| Unrolled **local** BFS | a 5x5 / 7x7 window around the body, unrolled, treating units (allies, enemies, living camps) as walls, scored by the global field at its edge (Om Nom 2025: push a waypoint ahead, BFS back from it) | code size; v10 already detours danger | **build in `nav.h`**, fuel measured first |
| Bug nav fallback | only for moving blockers: units as obstacles for about 5 turns (3MiceWalkIntoABar 2026) | adds loops | **last resort only** |
| Progress monitor (BFS → bug when no progress; Generalized Stroke's Theorem 2026) | if the field distance has not dropped for k turns: recompute the field with units as walls, sidestep, or yield by priority | v10 has `stall_guard`, `pocket_fix` | **build in `nav.h`** |
| Loop prevention ("turn locations" + reverse); target-switch hysteresis (XSquare: switch only when the new target is closer than the best distance reached so far) | the same | none | **build in `nav.h`** |
| **Static hazards (map analysis)** | per map: chokepoints (articulation points), dash-only pockets, dead ends, hole lines a dash can cross, crystal shortcuts, and the "field anchors" worth caching (spawn, bank altars, top groups) with their fuel | congestion is dynamic; static chokepoints are a proxy | **for the other Claude**: the catalog, the table and a NAV draft-memory block (MAPAnalysis 1.9) |

**Measured in step 2** (`tools/teamplan/probe_nav.py`, release mode as on the platform; probe bot
`tools/teamplan/cpp/probe_nav/main.cpp`; fuel per call; `experiments/results/teamplan/nav_fuel_table.md`):
| Map | Size | Walls export | Full field | Field limited to 3 | Field to one target | 49 `get`s | Walls + 10 unit tiles | Full field with units | 7x7 BFS in wasm, looped | 7x7 BFS in wasm, unrolled |
|---|---|---|---|---|---|---|---|---|---|---|
| big-world | 100x100 | 1,889 | 30,843 | 3,535 | 28,048 | 2,667 | 1,281 | 30,211 | turn ran out | 10,783 |
| ambush | 100x100 | 1,889 | 25,858 | 3,535 | 25,090 | 2,667 | 1,281 | 25,479 | turn ran out | 10,783 |
| islands | 60x60 | 879 | 5,863 | 1,345 | 5,946 | 2,667 | 1,176 | 5,441 | 17,460 | 10,783 |
| lanes | 90x30 | 735 | 5,463 | 1,041 | 5,455 | 2,667 | 1,160 | 5,073 | 17,460 | 10,783 |
| gold-rush | 31x31 | 492 | 1,725 | 433 | 1,858 | 2,450 | 1,147 | 1,393 | 12,473 | 7,465 |

**Conclusion (this revises the BugBFS row above)**:
- **The unrolled local BFS does not pay in CAMBC.** The host's field limited to radius 3, over the walls plus the unit tiles, costs
  1.2k + 0.4-3.5k. That is exact and cheaper than the same search written in wasm (10.8k unrolled, 17.5k looped).
- **Unrolling still pays for any loop that must run in wasm** (a 38% cut here).
- **Full fields cost up to 31k on 100x100 maps** (a third of a turn), so global fields are cached and never recomputed per turn.
- **`nav.h` therefore uses**:
  - cached global fields (the field anchors);
  - for local detours, a radius-3 to radius-5 host field over walls + units;
  - reads of only the neighbours it needs (a `get` costs about 55).

---

## 7. Postmortem synthesis (Oct 24; 17 documents, 16 readable)

Sources:
- the user's upload: Gone Fishin' 2023 (2nd);
- a research agent (Opus, read-only) read the others listed at https://battlecode.org/past.html.

**Gone Fishin' (2023, 2nd), read here**:
- **A bit budget for the 64 x 16-bit shared array** (821 of 1,024 bits): HQ locations, symmetry bits, congestion flags, unit counts,
  the 5 closest wells per resource, 10 enemy reports each with a 2-bit round stamp, island states.
- **Congestion control**: stop producing when HQs are crowded; mine at a well's capacity minus one.
- **Wells marked dangerous** when enemies are seen there, with a decay.
- **Micro is worth 30-50% of win rate vs 5% for macro**:
  - always kite back after attacking;
  - chase only when nothing else is attackable or the team is 2+ stronger;
  - target what can be one-shot first;
  - regroup toward the ally nearest the enemy with the most health, low-health units behind;
  - guess attacks into clouds at reported or last-seen positions;
  - spawn order sets the formation.
- **Stack-based bug nav** with left / right simulation, randomness (allies as walls 75% of the time) against loops, no wall-hugging.
- **Center-island play won normal maps but lost a strange final map**: map-specific bets are fragile.

**Documents read by the research agent** (one line each; lessons in brief):
- **A Guide to Battlecode (XSquare)**:
  - test against old versions on many maps and both sides (turn order, seeds and loop orders bias sides);
  - change one thing at a time, on maps that stress it;
  - prefer independent per-unit behaviour over coordination; optimise compute late;
  - switch target only if the new one is closer than your best distance to the current one (stops navigation loops);
  - spend leftover budget on multi-turn work.
- **Generalized Stroke's Theorem (2026, 2nd)**:
  - micro scored all 9 tiles; every fighter broadcast its HP and the nearest enemy's (over budget in big fights, "worthy tradeoff");
  - scored every move + action combination;
  - BFS with a hand-off to bug nav when BFS stops making progress; a cheap reachability check stopped units fighting through walls;
  - copied macro from stronger scrim partners; more time reviewing scrims than writing code.
- **food (2026, 9th-12th, solo rookie)**:
  - heartbeat bit toggled every turn, silent units' slots cleared;
  - broadcasting enemy positions "greatly improved" micro;
  - tiles an enemy can hit next turn penalised, finishing blows weighted up, caution halved when outnumbering 2:1;
  - a fixed unit minimum that ignored map size hurt small maps;
  - accepting any gain against your own old bot overfits: build 3-5 maps per behaviour.
- **3MiceWalkIntoABar (2026, finalist)**:
  - a few days away dropped them from top 10 to about 60th;
  - a distributed runner (300-500 games in 5-15 minutes) bisected regressions: bug fixes took them from under 50% to about 70% vs
    their benchmark, and merges then needed a 95% interval gain;
  - units treated as obstacles for 5 ticks cut congestion; a timer pulled idle units out of combat;
  - weak micro capped them.
- **Lorem Ipsum (2026, 13th-16th)**:
  - 14 bits per king (location, low-HP flag, alive toggle); sightings expired by type;
  - memory-based attacks won over 85% locally (less online);
  - dropping specialist scouts / soldiers (caught 1v3) improved survival; a bigger carry cap gave significant gains;
  - hidden coupling: cutting broadcasts broke half the bot;
  - an AI-written tuner never worked.
- **Just Woke Up (2025, 1st)**:
  - 57 versions in 25 days; A/B on every map; auto-scrims vs the top ~20; watched the losses;
  - shipped defense towers though self-play A/B was flat or negative, and credit them with the title;
  - kiting static targets gave 2 hits per hit taken; entering range together on even turns;
  - expensive scans stop when the budget runs low.
- **confused (2025, 2nd)**:
  - almost no bytecode work; strategy from replay analysis;
  - copying a rival's trick gave 70%+;
  - lost the final to exploration biased to the centre.
- **Om Nom (2025, 3rd)**:
  - every new unit overran its first-turn budget: the fix gave a "substantial" gain;
  - ending an unconditional retreat rule made towers die "with much higher odds";
  - "Optimal Bug" (bug waypoint + BFS back) handles clogging;
  - dropped a copied rush (high variance).
- **SPAARK (2025, high-school 1st)**:
  - micro scored in one currency from raw constants (competitive with top teams); evaluate attack-then-move and move-then-attack;
  - "retreat only near a refill point" beat their old bots by far;
  - last-minute changes cost them in 2023-2024; a test script caught a bug minutes before the 2025 deadline.
- **Cout for Clout (2024, high-school 1st)**:
  - ablation: 47 units vs 50 lost 90%, so static guards went;
  - fully aggressive micro +130 rating; XSquare-style per-direction micro took them past 2000;
  - rally to combat points (Lanchester); step back if the ally behind is healthier.
- **David Teather (2024, 13th)**:
  - half of the features scrapped; 818 scrim games;
  - standoffs where both sides judged themselves weaker idled both armies;
  - poor pathing lost sprint games.
- **4 Musketeers (2023, 3rd)**:
  - 7-bit map sectors instead of 12-bit locations; local stores uploaded in range; batched writes;
  - combat sectors expired after 100 rounds; claims + timeouts stopped oscillation;
  - retreat when outnumbered or at critical HP; blind shots into clouds landed;
  - lost to the 16th seed after a first-turn budget overrun on an unusual map.
- **Don't @ Me (2023, finalist)**:
  - target score = type value + damage + missing HP / 2 + 100 if it kills;
  - kite whenever possible (best when moving first); double-buffered commands by round parity;
  - general code beat the 8th seed on new maps.
- **5 Musketeers (2022, 7th)**:
  - a turn order that survives base deaths: +4 ranks;
  - enemies tracked as running-average clusters (no oscillating distress calls);
  - a heal cap + timeout; a spreadsheet of every version vs every other on every map.
- **Java Best Waifu (XSquare, 2020, 1st)**:
  - spare early budget computed a base plan broadcast as a bitmask over a fixed tile order;
  - a "desperation index" relaxed rules after waiting;
  - all-in attacks synchronised at fixed rounds with no comms;
  - "sophisticated coordination … always flops".
- **smite (2019, 1st)**:
  - every unit computed the same resource-cluster list, so messages used 5-bit indices;
  - castles assigned miners centrally;
  - "first to move into range dies";
  - an untested last-hour rush caused nearly all their seeding losses.
- **Not readable**: Baby Ducks (2021, 1st), http://web.mit.edu/agrebe/www/battlecode/21/index.html (the proxy only tunnels HTTPS; the
  https URL returns HTTP 500).

**The 15 most transferable lessons (with the teams that support them)**:
1. **Score every candidate action in one currency** (Generalized Stroke's Theorem, food, Om Nom, SPAARK, Cout for Clout, XSquare). In
   CAMBC: {stay, 8 moves} x {attack, ability, none} in gem-equivalent units; ranged champions weigh moving against attacking.
2. **Do not enter range first; use turn order** (smite, Don't @ Me, Just Woke Up, Cout for Clout, XSquare). → P4 (probe first).
3. **Go for kills; deny resources** (Don't @ Me, food, SPAARK, Just Woke Up, smite, 4 Musketeers). In CAMBC, the killer takes the whole
   bag: chip damage first, then a chosen finisher (by priority) who is safe to bank.
4. **Retreat and return rules are high-leverage settings** (Om Nom, SPAARK, Lorem Ipsum, food, 4 Musketeers). → bag rules; recall only
   when no enemy can reach within 5 turns.
5. **Fight together; avoid standoffs** (Cout for Clout, Don't @ Me, 4 Musketeers, Lorem Ipsum, food, Teather). A lone body carrying gems
   is the worst state.
6. **Comms as indices into shared tables, message headers, one owner per field** (smite, 4 Musketeers, Just Woke Up, SPAARK, Generalized
   Stroke's Theorem, Lorem Ipsum, 5 Musketeers). → `live.h`.
7. **Every shared value expires** (food, Lorem Ipsum, 4 Musketeers, Don't @ Me): 2-3-bit stamps or toggles; dead or fuel-starved bodies'
   fields expire.
8. **Precompute with full information; coordinate by identical deterministic computation** (XSquare 2020, smite, 4 Musketeers). → the
   draft memory.
9. **Protect the compute budget, the first turn above all** (Om Nom, 4 Musketeers, Just Woke Up): cache fields, take a safe default
   action first, check fuel before optional work.
10. **Cheap reliable pathing with a fallback and target hysteresis** (Generalized Stroke's Theorem, Om Nom, confused, 4 Musketeers,
    XSquare, 3MiceWalkIntoABar). → `nav.h`.
11. **Adapt to map features; never hardcode maps** (Don't @ Me, XSquare, food, 4 Musketeers, Just Woke Up, confused, Om Nom).
12. **Test statistically against varied opponents** (XSquare, Just Woke Up, 3MiceWalkIntoABar, 5 Musketeers, SPAARK), with diverse
    sparring bots: a rusher, a farmer, a ganker.
13. **Watch replays and copy top teams, understanding what you copy** (Generalized Stroke's Theorem, confused, Cout for Clout, Om Nom).
14. **Freeze before deadlines; document hidden dependencies** (smite, SPAARK, Lorem Ipsum): every reader of the live bytes is listed.
15. **Script the endgame** (5 Musketeers, smite, food). → section 5.

**What did not pay off for them**:
- automated / ML tuning (only Lorem Ipsum tried, it failed; no top team reports ML, RL or genetic tuning);
- specialist lone roles; static guards; extra comms units;
- rushes by finals time (high variance).
- Heavy bytecode hacking was optional (confused, Generalized Stroke's Theorem, Just Woke Up), though templated unrolling helped Om Nom.

---

## 8. Draft memory: how it is used now, and the final layout

**Now**:
| Bytes | Owner | Content |
|---|---|---|
| 0-3 | GOD v10 | 4 bytes `B7 ..` (its optional 0xC8 plan layout is off) |
| 4-511 | free | the mapintel test bot borrows 8-511 for test prints only |
| 512-863 | mapintel (`tools/mapintel/cpp/mapintel/dmem.h`, 352 bytes, magic 0xA7, version 1) | fingerprint, flags (known map, bank access per team, tiebreak mode), archetype, team size, per group: bank altar and both teams' walk; 16 contested groups with both ETAs; 8 plan-4 thresholds; plan 1 (6 bodies x 4 targets with arrival rounds); checksum |
| 864-1023 | free | 160 bytes |

**The rule for what goes in**:
- **Static knowledge about a map goes in the binary** (the table, model weights).
- **The draft memory carries what only the draft can produce cheaply**:
  1. results too expensive for a champion's 200k first turn;
  2. decisions that depend on this game (our roster, the enemy's picks, our side);
  3. one consistent team decision.
- Data is stored in the form a champion reads it (fixed offsets, direct indexing; no decode loops).

**The final layout**: `docs/DRAFT_MEMORY.md` (step 7).
- A header with a table of contents at offset 4, and checksummed blocks: TEAM, OWN, BODY, CONT, CODEBOOK, ENEMY, NAV, DEBUG; the mapintel
  block stays at 512.
- **Write rules**: pick first, then compute; one RAM image rewritten whole; a valid minimal plan written early, then improved.
- Fuel per block measured.

The v10 test copy carries a prototype. **The other Claude implements the final state in its library** (the handoff prompt, step 8).

---

## 9. The build plan

**Folders**: `tools/teamplan/` (Python: analyses, twins, tests, battery scripts) and `tools/teamplan/cpp/teamplan/` (header-only C++).

**Modules**. Each has a Python twin, an engine test and measured fuel. Inputs come from engine designs, `passive_type` and SDK constants.
Weights live in one versioned parameter set.
| Module | Content |
|---|---|
| `kit.h` | kit features + passive / constant; role scores (front, carry, farmer, banker); swap eligibility |
| `capture.h` | the risk-matched capturer (U3'); one body captures; danger with decay feeds P(bank) |
| `bag.h` | bank-before-fight, fight-empty, hunt-big-bags, "bank now if it wins" (U2') |
| `tiebreak.h` | tiebreak detection, the risk cap for deferring, the final tribute window, end-window denial (section 5) |
| `focus.h` | the kill-value target term (P1) |
| `timing.h` | turn-order helper: who acts next between two opposing bodies (round parity, team, ranks); the "step in only when we act again first" gate (P4) |
| `assign.h` | soft ownership + variants (D1) |
| `swap.h` | the expected-value swap check, hysteresis, cursor; a TinyML slot left at zero (U4') |
| `nav.h` | the unrolled local window, progress monitor, loop guard, target hysteresis, field cache (section 6) |
| `live.h` | the 64-bit live protocol spec + codec for the user's bot (P2, D2) |

**The GOD v10 test copy** (git-ignored `bots/_tp_v10`): `tools/teamplan/prepare_v10.py` + `tools/teamplan/v10_adapter.patch` on a copy of
`bots/god`.
- Switches `tp_*`; all off = v10's games exactly, checked by `tools/samegames.py`.
- The v10 test uses the live bits v10 leaves free with its defaults (bit 7 of bytes 2-5).

**Batteries**:
- 40 official maps x 2 sides per cell; each switch alone, then combined.
- Two opponent families: GOD v10, and a v10 copy forced to play the strong teams' roster per map.
- Stats: `tools/abstat.py`, `tools/abmargin.py`. Numbers are labelled SIMULATED (v10). A switch is kept only if it holds against both
  families.

**Order**:
1. this file + MAPAnalysis 1.9 + AGENTS pointer;
2. probes and offline checks;
3. modules + twins + engine tests;
4. the v10 test copy;
5. batteries;
6. TinyML only if needed;
7. `docs/DRAFT_MEMORY.md` final, `tools/teamplan/README.md`, ISSUES, results;
8. the handoff prompt for the other Claude.

---

## 10. Checkpoints (newest last; UTC)
- **12:22**: this file written (step 1). Research done read-only before it:
  - the rules and SDK facts (section 2);
  - 599 top-team games measured (section 3);
  - the pro/con review (section 4);
  - tiebreak mode (section 5);
  - navigation (section 6);
  - 17 postmortems (section 7).

  Next: step 2 (probes: the turn order, gold-only captures, role tables, fuel of a host field vs an unrolled window, the offline capturer
  comparison).
- **12:30**: step 2, probes and offline checks (commit after this line).
  - **Turn order**: alternation one body at a time, the starting team swaps each round. The double move exists, so `timing.h` was added
    (section 2, P4).
  - **Gold-only captures**: the decoder dropped them. It now has the opt-in `--gold-captures`. 20% of captures are gold-only, and front
    bodies take relatively more of them (section 3).
  - **Role tables**: `experiments/results/teamplan/roles_ladder.md` (+ .json), with a death hazard per champion.
  - **Navigation fuel**: the host field limited to radius 3 beats an unrolled wasm BFS (section 6), so `nav.h` uses host fields.
  - **Deferred to step 3**: the check of the risk-matched capturer against the top teams' choices. It needs the Python twin of
    `capture.h` and the 25 raw replays' positions (who else could have captured each reward).
- **13:55**: step 3, the modules (commit after this line).
  - **Written**: `tools/teamplan/cpp/teamplan/` = `params.h` (one versioned set, every value labelled), `kit.h`, `sdk_bridge.h` (the only
    header with the SDK), `capture.h`, `bag.h`, `focus.h`, `timing.h`, `tiebreak.h`, `assign.h`, `swap.h`, `live.h`, `nav.h`, `nav_sdk.h`;
    Python twins in `tools/teamplan/tp/`; the engine designs in `experiments/results/teamplan/designs_3_0_5.txt` (exact bits, written by
    the test); the kit table `tools/teamplan/kit_table.py`.
  - **Engine test** (`tools/teamplan/test_teamplan.py`, test bot `tools/teamplan/cpp/test/main.cpp`): **2,080 results equal the twins bit for
    bit** on the 40 official maps x 2 teams. Fuel (worst call): all 13 kits 20k (draft), capturer choice 1k, ownership plan 54k on the
    largest group lists (so it belongs in the draft and in draft memory, not in a champion turn), local detour 9k median / 17k max.
  - **Found on the way**: the first ownership greedy cost 39k for 12 groups (replaced by list scheduling); fused monolith groups pay more
    than 255 gems (448); **a visible enemy's priority is readable** (`prev_priority()`, so `timing.h` can use the real rank), its team is
    `cambc::detail::sdk_my_team()`; ties inside a team act in body-type order (all priorities 0); vision is not shared (an ally out of
    sight cannot be read); the enhanced attack reset stuns (rules text; counted in `stun`).
- **14:25**: step 4, the GOD v10 test copy (commit after this line).
  - **v10 almost never shares a capture**: 10 mirror games, 1.1% of capture events had two or more bodies (1.01 bodies per capture;
    the top teams 5.5%). So the capture rule (one body captures, the others move on) has nothing to save in v10 and is not in its
    batteries; in v10 the useful part is who goes to which group (`tp_own`). The rule stays in the library for a bot that sends several
    bodies to one group.
  - **v10 already has three of the planned rules**: the turn-order fact (`update_priority`), the endgame bank window and "bank now if it
    wins" (`tribute()`, `win_bank` + `team_bank`). The new parts are below.
  - **The copy**: `python3 -I tools/teamplan/prepare_v10.py [--name N] [KEY=VALUE ...]` = `bots/god/src` + `tools/teamplan/cpp/teamplan` +
    `tools/teamplan/v10_adapter.patch` (`tp_adapter.h/.cpp` and guarded hooks). Five switches, all 0 by default:
    - `tp_focus`: the fight target's value = kill value (its bag + kill gold + the farming lost while dead) over its health, in place of
      v10's constant 60 (+60 for the pair) + bag;
    - `tp_bag`: the proactive fight bar rises with our bag (x (1 + bag / 60));
    - `tp_timing`: the ranged edge hold and the melee approach step into an enemy's reach only when we act again before it (priorities of
      the bodies in sight, both rounds);
    - `tp_tiebreak` (+ `tp_tb_cap`): in tiebreak mode a bag up to the cap is kept while no enemy is near; v10's endgame rule banks it;
    - `tp_own` (+ `tp_own_bonus`): the draft writes the OWN block (draft memory offset 8: magic, version, bodies, groups, body types,
      one owner per group, checksum) after each pick; a body's own groups score x 1.25.
  - **Control**: all switches 0 plays v10's games: **80 of 80 identical** (winner, rounds, gems, deaths, gold; `tools/samegames.py ...
    --release`, a flag added for release-mode rows).
  - **Family 2 opponent**: `tools/teamplan/make_forced_v10.py` = v10 forced to the strong teams' roster of each map (roster slot 0 of
    `tools/mapintel/data/battery_rosters.json`, via mapintel's `force_roster.h`): the forced roster is played in 80 of 80 games; **v10's
    own draft wins 37 of 80 (46.2%) against it**.
  - Running: `tools/teamplan/batteries.py` (7 variants x 2 families x 80 games).
- **14:55**: offline check of the capturer rule (task 20; commit after this line).
  - **What was checked**: does the risk-matched capturer pick the body the top teams picked? The data: 25 raw replays,
    `tools/teamplan/capture_ctx.mjs` (state N rounds before each capture) and `tools/teamplan/capture_check.py`.
  - **Three rounds before the capture began** (1,166 captures with two or more bodies within 3; agreement, with chance at 41%):
    - the highest gold multiplier: 65%;
    - the nearest: 61%;
    - the risk-matched rule: 42%;
    - the lowest bag: 46%;
    - the front or back kit: 44-45%.
  - **Five rounds before**: nearest 92% (the capturer is already on the tile, so that number is an artefact). **Twelve rounds before**:
    gold multiplier 54%, nearest 46%, the rule 38%.
  - **The rule fails** on two counts:
    - its diminishing gold value per item (ASSUMED) points to the poorest body, and the top teams do not do that: without it the rule
      reaches 54-58%;
    - its gem-risk part does not explain their choices.
  - **Verdict, by the user's "keep what wins against its counterparts" rule**: `capture.h` now defaults to the LEARNED pattern
    (`capture_mode` 1: the gold-bonus body, then the nearest). The risk-matched gain is kept as mode 0, and `items_half` is 0 (off).
    The engine test still passes (both modes, 2,080 results bit-equal).
  - **The answer to "should the frontliner take the gold"**: the strong teams give a shared reward to the gold-bonus body when it is near,
    else to the nearest body; front bodies take relatively more gold-only groups because they stand at them (TEAMPLAN.md 3).
  - Outputs: `experiments/results/teamplan/capture_check_lag*.txt`.
