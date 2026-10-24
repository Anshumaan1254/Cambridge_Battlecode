# Plan: god2 = god.zip rebuilt with what the strongest teams do (and without their weaknesses)

## Context
- `Downloads/god.zip` (the user's best bot, rank ~15 on patch 3.0.2 + old maps) is **byte-identical to git 28d7340** (GOD v8 +
  opponent model). Restored as `bots/g8`; builds on cambc 3.0.5 (warnings only). Every later lineage (v10-v12, bb4, v49-v54) was
  worse on the ladder; we are rank 55 (1862).
- Task (user, Oct 23): build on god.zip (drastic changes allowed, never worse); learn the strategy, decisions, play style and
  situational behaviour of **prism best girl** (#1, 2269), **Intercontinental Fish** (#2, 2235), **Claudus Maximus** (#19,
  2012 after only 92 games) and **every top-50 team with > 65% recent win rate**; adopt the principles (not blind copies),
  remove their weaknesses (draft, strategy, items), exploit their shortcomings. Judge ONLY with real unranked games via the CLI
  on all 40 maps x both sides (no proxies; their bots react to ours). Prove god2 >= god.zip by playing BOTH vs these teams.

## Evidence so far (lists to 14:40 UTC Oct 23, 1,600+ summaries, ~350 cached replays)
- **prism best girl (67% since 07:00, 158-77)**: Prism first everywhere (Prism/Vesp/Marc + Ryth/HoR/Vend; 3-a-side Prism/Vesp/HoR).
  Prism = gem bank (+1.5 focus per carried gem): carries 240-300+ gems, banks once late (260-380); tank items (Durability /
  Monster / Jungle health, never Treasure, never altar locks), max HP 2,094 vs 1,758; 16-17 banks/game; middle share 0.55,
  re-hits respawning middle groups after 14.5 rounds; deaths 7-8 vs 11-12; golems 2.3/game; ~140 wards (bushes, middle band).
  Weak: slow early economy (28 banked by r200 vs 58), farm maps vs fast 3-champion farmers (the_farm 1-4, fracture 2-5,
  concentrated_wealth 2-5, big_world 2-4, collision 2-4), Prism dying with the bag.
- **Intercontinental Fish (59%, 138-97)**: Vesper first (Vesp/Vend/HoR/C&I/Ryth|Varg); 6-body blob to ~r100 then split; Vesper
  hyper-carry (Treasure-Str > Bruiser-Str > Durability-Hp > Power-Str forever; 46% of team gold); 21-28 small banks (first r110)
  at altars ~8 tiles from the capture; middle share 0.62, re-hits middle groups after 8.5 rounds; ~5 altar locks + 5 crystals.
  Weak: aggressive (13.4 deaths, lower max HP) -> death spirals vs tankier teams that win the first central fight (boss_battle
  2-11, fracture 1-10, split 2-6, lost_world 2-5, collision 2-5); loses pure farming races (rows).
- **Our record**: vs IFish 7% (12-163), vs prism best girl v2 1-69. They: 2x our gold by r100, middle share 0.8 vs 0.18,
  deaths 5-6 vs 12.8, banks 21-28 vs 9-10, first kill 77-83%. Our bodies loop/A-B-A 2-3x more.
- **g8 locally vs v54**: 26/80, gems 539-804, deaths 16.2-8.8, **13 fuel-outs/game** (bug to fix first); 0 faults.

## Phase 0 - Baseline (running)
1. `bots/g8` submitted unchanged as version 55 (14:57 UTC). Live check: `tools/live/wait_draft.py 8` (Ren = g8's signature).
2. Sweep **S0** = `experiments/live/setF_top2.json` (32 groups: 40 maps x 2 sides x {prism best girl, IFish}) + Claudus Maximus
   (16 groups) + other > 65% teams if quota allows: `tools/live/queue_groups.py S0 --set ...`, `groups.py pull S0`,
   `summ.py fetch`, replays via `tools/live/dl_replays.py`. S0 = the bar every candidate must beat (paired by opponent/map/side).

## Phase 1 - Study (Workflow, analysts in parallel, then adversarial verify, then synthesis)
Data: per study team ~3 newest ranked games per map (`tools/live/dl_replays.py --per-map 3`, current versions only, version =
draft fingerprint per map) + compact summaries (`summ.py fetch`) + our S0 games vs them. Win-rate scan:
`tools/live/top_winrates.py --top 50` -> `experiments/live/top_winrates.json`.
Analysts (each: numbers + replay references, `experiments/top2/an_<dim>.md`): (1) draft as a function of map features;
(2) opening r1-300 (routes, grouping, first captures/banks, first fight); (3) economy (farm cycles, middle, re-hit timing, bank
cadence, golems/monoliths); (4) items and ability use (build orders, combos, Prism tribute, Vesper carry); (5) **situation ->
action tables** (enemy appears while farming, ally attacked, big bag, low HP, outnumbered, carrier at altar, after a won/lost
fight); (6) weaknesses and exploits (their losses, death causes, predictable routes/timings, tribute windows); (7) Claudus
Maximus + > 65% teams profiles; (8) how g8 loses to them (S0). Verify: independent agents re-measure each key claim on other
replays (refute by default). Synthesis: `experiments/top2/STRATEGY.md` = ranked list of mechanisms to build, each with the
measured gap, the runtime rule (no per-map tables, no fixed drafts), expected effect and its ladder test.

## Phase 2 - Build god2 on g8 (every change behind a params.h switch, all off = g8 exactly)
Order (cheap and certain first; the study re-ranks B-E):
- A. **Hygiene**: fuel-outs on the new maps (init fuel cuts f0c0c9c, hop fuel guards ff8514f), stuck fixes (pocket_fix 14f1bc8 +
  pocket_guard, capture-deadlock timeout cfe377c, osc_fix A-B-A/detour/no-progress 9618135), watchdog on, real_channel.
- B. **Draft**: replace v8's stale 3.0.2 priors (Ren-first, Stellar) with engine-stat values + composition principles learned
  from the top teams (a bank/sustain anchor, a ranged carry, frontline/burst), chosen by map features at runtime.
- C. **Economy**: early tempo (IFish: group on the nearest high-value groups, bank small and early), then the carrier mode
  (prism best girl: the tankiest gold/gem-scaling body carries, banks big when safe, escorted); middle control and fast re-hits
  of respawning middle groups; golems with 3-4 bodies; carry roles get Treasure, the rest tank items (from the study).
- D. **Fights**: win the first central fight with a health lead or stay out (fight discipline from IFish's losses), strike
  first, focus fire, no re-engaging after a lost fight, recall-punish, protect the carrier.
- E. **Exploits**: target the enemy carrier (Prism with a 300-gem bag, Vesper with 46% of their gold); cancel big tributes
  (stun/lock if the rules allow - verify in GameRules first); out-farm prism best girl's slow opening; tank up vs IFish.
- Port `strat.h/.cpp` (ab_variants / ab_b0..b3 / ab_nomask) so one submission can screen 2-4 switches.

## Phase 3 - Ladder loop (only real games vs the study teams)
Per candidate: build -> local gate (40 maps x 2 vs g8: 0 faults, fuel-outs <= g8, no long stands; NOT a strength judge) ->
submit -> sweep (setF + Claudus; <= 48 groups/hour quota) -> `tools/live/paired.py S0 <label>` (wins, flips, gem margin, deaths,
per opponent/map) -> keep a switch only if flips and gem margin improve -> next. Watch for opponent resubmits (draft fingerprints
in their ranked lists); re-baseline if one changes. Record every step in AGENTS.md.

## Phase 4 - Final proof and ship
Back-to-back sweeps of g8 (S0') and final god2 (SF) on all 40 maps x 2 sides vs prism best girl, IFish, Claudus Maximus;
report per team/map. Ship god2 only if SF > S0' overall and not worse per opponent; push to GitHub only then.

## Verification
- Local: `cambc build <bot> --release`; `tools/live/localbench.py <bot> g8` (faults, fuel-outs, stands via longstand.mjs).
- Ladder: `tools/live/paired.py` per sweep; `top_winrates.py` for ranked rating trend; replays narrated with narrate.mjs.
