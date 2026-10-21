# GOD v9: adaptive layer (companion code to "The GOD Bot: Complete Guide")

GOD v8 plus an opponent model and team plan (chapter 17 of the guide), and a few fixes (chapter 16).
**Every new switch defaults to v8 behaviour**, so this source plays exactly like v8 until you turn a switch on.

Status: compile-checked against `stub/cambc.h` (declarations written from BotAPICpp.md) with the same warnings as v8;
the opponent model was run as real C++ on scripted scenarios (below). It has **not** been run in a real match:
no engine was available. Follow the A/B order in chapter 20 before submitting anything.

## Contents

| Path | What |
|---|---|
| `src/` | The full v9 bot (v8 + changes), 10,052 lines. Drop-in replacement for the bot's source folder. |
| `src/opp.h`, `src/opp.cpp` | New: plans, presets, `OppModel` (evidence, indices, decision list, fast paths). |
| `test/test_opp.cpp` | Scenario tests A-J and false-alarm runs; links the real `opp.cpp` with small fakes. |
| `stub/cambc.h` | Declarations-only SDK stub for compile checks without the engine. Never ship it. |
| `v9.patch` | Unified diff against v8: +576 / -20 lines in 9 files. |

## Switches (src/params.h, end of `struct Params`)

| Switch | Default | First test value | Purpose |
|---|---|---|---|
| `opp_plan` | 0 | 1 | Run the opponent model, broadcast the plan, apply its preset (needs `alert_refresh = 0`, the v8 default) |
| `opp_presets` | 1 | 0 for the dry run, then 1 | 0 = plan computed and traced but not applied |
| `contact_bit` | 1 | 1 | Bodies share "enemy deep in our half" through bit 7 of shared byte 2 |
| `enemy_comp_init` | 0 | 1 | Enemy champion types and kits from round 1 |
| `safety_range` | 0 | 1 | `safety()` counts camps at their real range (elk/golem 4, monolith 5) instead of 3 |
| `watchdog` | 0 | 3 | Minimal fallback turn after 3 consecutive exceptions |
| `ring_reach` | 0 | 1 | Objective ring: area reach = range + radius, blast aimed next to the camp |
| `tavi_str` | 0 | 1 | Tavi builds strength instead of focus (her whole default style-2 list; proxy styles 3/4/10/12 unchanged) |
| `spar_from`, `spar_to`, `spar_half`, `spar_deny`, `spar_fight`, `spar_db` | inactive | see guide 20.1 | Sparring personas for A/B opponents only. Never submit with these set. |

Model tunables: `opp_window 30`, `opp_ema 0.5`, `opp_dwell 2`, `opp_contact_hi 0.35`, `opp_consec 2`,
`opp_contact_stay 0.20`, `opp_contact_lo 0.10`, `opp_depth 0.8`, `opp_cusum_k 0.2`, `opp_cusum_h 0.8`,
`opp_home_deaths 2`, `opp_punish_bal 0.5`, `opp_loss_n 2`, `opp_loss_h 100`, `opp_race_margin 60`, `opp_race_from 150`,
`opp_rate_ema 0.3`, `opp_even_bal -0.25`, `opp_deny_at 850`, `opp_dive_prior 0.15`.

Submitted builds use the `constexpr` defaults, so change a default in `params.h` to enable a switch.
The training build (`LEGEND_RUNTIME_PARAMS`) reads the generated parameter file as before.

## Commands (from this folder)

```sh
# compile check without the engine
for f in src/*.cpp; do g++ -std=c++20 -fsyntax-only -Wall -Wextra -Istub "$f"; done

# scenario tests of the opponent model
g++ -std=c++20 -O1 -Istub -Isrc test/test_opp.cpp src/opp.cpp -o test_opp && ./test_opp

# plan traces in a real test build: add -DOPP_TRACE (one line per 30-round window)
```

## Test output

```
params: window 30 ema 0.50 hi 0.35 consec 2 home_deaths 2 race_margin 60 deny_at 850
A even farmer         : r2:FARM
B faster farmer       : r2:FARM r152:HUNT r880:DENY  (theirs 1400 ours 875)
C invader from r400   : r2:FARM r436:DEFEND
D presence-only invade: r2:FARM r482:DEFEND
E lost team fights    : r2:FARM r337:EVADE r422:FARM
F invader then passive: r2:FARM r62:DEFEND r662:FARM
G invasion we win     : r2:FARM r392:PUNISH
H faster, trades lost : r2:FARM r152:RACE r880:DENY
J mid-match switcher  : r2:FARM r436:DEFEND r752:FARM r782:HUNT r1040:DENY  (theirs 1310 ours 1010)
I false alarms share 0.08: 15 of 200 games left FARM at least once
I false alarms share 0.12: 44 of 200 games left FARM at least once
```

## Suggested order (guide chapter 20.5)

1. Dry run: `opp_plan = 1`, `opp_presets = 0`, build with `-DOPP_TRACE`; check false alarms vs mirror farmers (< 10% of games) and detection vs the sparring personas.
2. `safety_range = 1`, `watchdog = 3` (must not lose).
3. `enemy_comp_init = 1`.
4. `opp_plan = 1` with presets: normal pool (must not lose) and switcher pool (should gain).
5. Tune each preset against the opponent type it counters.
6. `ring_reach` on objective maps with a ring composition; `tavi_str` on Tavi drafts.
