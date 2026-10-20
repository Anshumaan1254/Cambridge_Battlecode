# GOD v8: the structured plan (from the Oct 20 review `GOD_IMPROVEMENT_PLAN.md`)

Baseline: GOD v7 (`bots/god`, `submissions/god.zip` sha256 16c5907a…). Engine: **cambc 3.0.2** (the Heart of Ruin hotfix: focus per shard
15 -> 12, strength per shard 5 -> 4; SDK headers identical to 3.0.1). Working copy: `bots/_x_v8` (= `bots/god` + every v8 switch, all
off = v7 play); patch `experiments/wip/x_v8.patch`. Every change is a switch in `params.h`; a control with every switch off must replay
v7's games; a candidate ships only when it is at least level with v7 head-to-head and better on the cells that look like the top teams.

## Phases (each phase = build, control check, cells, keep or park, checkpoint in AGENTS.md)

| Phase | Items (review ids) | Switches | Cells | Exit rule |
|---|---|---|---|---|
| 0. Engine | P0-0: cambc 3.0.2, per-version ledger (`ledger_v3_0_2`, rows carry `engine`), v7 re-baseline | none | `_g8s` vs `_g4 _pws _pw _pc _m15 idle _mite _ifish _px9`; non-HoR games must replay the 3.0.1 rows | baseline table in AGENTS |
| 1. Heart of Ruin | P0-1 a-d: strike in contact (B2), the shield waits for the strike (B3), strike-dash hold radius (B4), dash onto camp packs (B5) | `hor_strike` 2, `hor_shield_hp`, `strike_dash_hold`, `hor_camp` | variants vs `_g4 _pws _pw _pc _m15 idle`; HOR_TRACE strike counts | keep what wins the HoR cells without a pace loss |
| 1b. HoR draft and build on 3.0.2 | P0-1 e-f: `pd_hor3` 0/1, `pd_hor_prior` 0.2/0.4, `pd_counter_hor` 0/0.4/0.8; HoR health tail | existing priors; `hor_build` | same panel + post-hotfix proxy | priors / enemy-pick terms only, nothing forced |
| 2. Engine values, hygiene | P0-2: engine constants for lock hits, ward cooldown, capture time, kill gold (B13, ISSUES #3/#24/#26); proxy recipes in `setup_session.sh`; official map names | `eng_consts` | `_g4`, `_pw` | level or better |
| 3. Learners | P0-3: `learn_stance` 0, `learn_pain` 0 alone | existing | `_g4`, `_pw`, `idle` | remove what is worth nothing (frees fuel and bits) |
| 4. Support-aware fights | P0-4 (B10, B11): allies weighted by arrival before our fighter dies, low-health floor, retreat toward help, danger-model threshold raised by real support | `sup_mode`, `sup_low_hp`, `sup_ml2_bonus` | full panel; lone deaths, deaths on our half | the biggest loss pattern: lone deaths / one-by-one retreats |
| 5. Shared memory v2 | P0-5 (B9): per-body state (FARM / WAIT / FIGHT / OUT), alert priority (OPPORTUNITY > ESCORT > RALLY), team bag sum | `comms_v2` | full panel | enables unseen helpers in phase 4 and escorts |
| 6. Bag escort | P0-6 (B15): a big bag at a contested altar waits for 2 escorts or a quiet altar; ESCORT alert; keep the channel while escorted | `escort_bag` | contest_v3, nx61x61 per map; gems lost on deaths, banks | fewer bags lost |
| 7. Blowout maps | P0-7: nx31x31_c4, contest_v3, nx61x61: traces, `aoe_reach5` 1/3, `mono_mode` check | `aoe_reach5` | per map, both sides vs `_pws _pw _g4` | findings in docs |
| 8. P1 | threat map (P1-1), death-cause learning (P1-2), passives in the fight model (P1-3: HoR passive, shields, our Ren's retaliation, real camp range in `combat()`), narrow enemy-HoR threat (P1-4), map-derived `gold_value` (P1-6), builds from engine growth (P1-7) | one switch each | full panel | as above |
| 9. Ship | v8 = v7 + every kept switch; both-SDK build; `tools/ship_god.sh CAND v8`; BUILDS, README, AGENTS | | `_mite _ifish _px9` before shipping | push the zip first |

Order rationale: phase 0 blocks every measurement (the ledger reused 3.0.1 rows); phase 1 is small and measured on the cells the hotfix
changed; phases 4-6 attack the largest measured loss (fights with bodies alone, bags lost); P1 replaces pieces that phase 4 makes
obsolete (pain map), so it waits for its results.

## Measurement notes
- Only games with Heart of Ruin on our side change in phase 1 (the four 3-champion maps, and counter-picks): most of each 42-game cell is
  identical to v7's, so the signal is the changed games; read them per map (`tools/ledger_maps.py OPP BOT...`).
- Pool: `maps/comp30` + `maps/nyx_new` + `maps/loss_oct20` = the 21 official maps (tile-identical), both sides = 42 games.
- Rows: `experiments/results/ledger_v3_0_2/` (cambc 3.0.2). 3.0.1 rows stay in `ledger_v3/`.

## Progress log (newest last; numbers are wins of 42)
- 3.0.2 baseline of v7 (`_g8s`; 3.0.1 in brackets): `_g4` 31 (31), `_pws` 25 (26), `_pw` 31 (35), `_pc` 36 (39), `_m15` 28 (29), `_mite` 40, `_ifish` 39,
  idle 42 (pace 1045.5; 1044.1). Check: vs `_g4`, `_m15`, idle the 34 games without Heart of Ruin replay the 3.0.1 rows exactly; only the 8
  games on the four 3-champion maps (our HoR draft) changed. vs the HoR proxies every game changed (their HoR is in every draft).
- Phase 4 code in `bots/_x_v8`: `sup_mode` bits 1 / 2 / 4 / 8 (weighted helpers, backup from helpers only, step toward help, danger-model
  threshold + support); variants `_v8p1`, `_v8p9`, `_v8p13`, `_v8p15` (HoR switches off) queued (`q32.sh`) after the HoR variants (`q31.sh`).
