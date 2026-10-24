# god2: session 17 work (Oct 23-24 2026)

Everything from the "god2" task is in this folder and only here: the bots, the study of the strongest teams, every ladder
measurement, and the tools. Nothing outside this folder was changed by this commit.

**The task (the user's words, condensed):** build a new bot on top of `god.zip` (our best bot, rank 15 before the 3.0.4 patches and
the new maps). Study prism best girl (#1) and Intercontinental Fish (#2), then also Claudus Maximus and every top-50 team with a
win rate above 65%: their drafts, strategy, items and situational play. Take their strengths, remove their weaknesses and exploit
them. Judge only with real unranked games through the CLI on all 40 maps and both sides, and prove the new bot is not worse than
`god.zip` by playing both against these teams.

## Where it stands

| sweep (40 maps x 2 sides x pbg / IFish / Claudus Maximus = 240 games) | bot | W-L | our banked gems | their banked | deaths us |
|---|---|---|---|---|---|
| S0 | `bots/g8` = god.zip unchanged (platform version 55) | **13-227** | 324 | 1,025 | 14.9 |
| G2A | `bots/god2_load` (version 57): role-slot draft + health builds | **12-228** | 319 | 1,031 | 12.3-13.0 |
| G2B | `bots/god2b` (version 58): + bank / deny / fight / mid modules, in-bot 16-variant A/B | **12-228** | 314 | 1,020 | 14.9 |

- **No version is better than god.zip against the top three yet**, so nothing was pushed as "the new best bot". The opponents did not
  change bots during the sweeps (their drafts were identical in 240 of 240 paired games).
- **Module effects from G2B** (`results/G2B_module_effects.txt`). This is a joint least-squares fit on per-cell deltas against the
  mean of G2A and S0. The noise level is about +-39 gems of margin.

  | module | effect on gem margin | on wins | on deaths |
  |---|---|---|---|
  | mid | **-116** | -6 pts | **+2.4** |
  | fight v1 | **-75** | **-9 pts** | +1.0 |
  | bank | +27 | -1 | +0.3 |
  | deny | -28 | -5 | +1.1 |

  Mid and fight v1 are harmful. Bank and deny are within noise.
- **Next round, ready in `bots/god2b` with defaults that reproduce version 58:**
  - load + bank (the base);
  - the **walk budget**, the best local result of the session: 47/80 against god2_load, with no cost to unopposed pace;
  - **calm**, which replaces fight v1: no chasing beyond reach, no pre-emptive flee, a rally gate, and commit off;
  - deny;
  - mid off.

  The A/B is configured with `g2ab_mods 0x4210`, `g2ab_salt 17` (a fresh map split), `g2m_on 0`, `g2f_calm 1`, `g2f_commit 0` and
  `g2w_walk 0.5`. The next step is to submit it, sweep it, and run the analysis below.

## Why we lose (measured; `findings/top2/gap_g8.md`)

- **The gap is farming, not stolen bags.** We capture about 420 camp gems a game; each top team captures 1,050-1,090. Net bag
  transfers on kills are only +-50 gems.
  - Split of the gap: farm share of alive time 41%, camp damage per farm round 31% (items, from 2.6x the gold), dead time 14%,
    target value 13%.
  - The middle band holds 73% of the gap: 126 vs 594 gems a game.
- **Contact reflex.** With an enemy within 8, which is 30-38% of our alive time, we farm 3-6% of rounds and walk 76-82%. They farm
  15.9%, even when we are locally stronger.
  - Per body per game we walk 144-217 rounds toward fights; they walk 58-89.
  - Debug traces of where those steps come from: combat() fights 30%, teammates' rally calls 27%, flee steps 22%, farm 13%.
- **The health builds (G2A) traded camp damage for survival.** Deaths fell by 1.9 a game, but camp damage per round fell 10%, and
  more HP made bodies chase more (+16 rounds of fight-walking). The net effect was zero.
- **Weak spots of the top teams** (`findings/top2/an_weak.md`, `an_playbooks.md`):
  - pbg loses 18 of 45 sampled losses holding an unbanked 200+ Prism bag. It never locks altars.
  - IFish and Claudus Maximus lose to fight snowballs.
  - All of them are weakest on 3-champion maps (pbg 42%, IFish 44%).
- **What all six strong teams share:**
  - less walking (the strongest behavioural predictor);
  - middle presence;
  - three or more bodies together through r100-600;
  - the first middle capture and the first kill;
  - gold turned into max HP at every spawn visit;
  - banking at middle altars.

## Folder map

| path | what |
|---|---|
| `AGENTS_snapshot.md` | the live handoff file at push time (task, rules, every finding and submission) |
| `docs/god2_plan.md` | the phase plan (baseline, study, modules behind switches, ladder loop, final proof) |
| `bots/g8` | god.zip, byte-identical to git 28d7340 (GOD v8 + opponent model) |
| `bots/g8h` | g8 + hygiene ports (fuel-out cuts, pocket / stuck fixes, recall-spam filter); fuel-outs 16.6 -> 1.9 a game |
| `bots/god2` | frozen copy of g8h, the base every module was built on |
| `bots/god2_load` | role-slot draft from engine designs (Vesper / HoR / Vendetta / Marcella / Ryth by team size) + health-weighted builds |
| `bots/god2_bank`, `god2_deny`, `god2_fight` | the module copies (bank often + recall gate; lock / stun denial of big tributes + carrier value; fight rules) |
| `bots/god2b` | load + all modules merged (`tools/top2/merge_modules.py`), in-bot A/B (`g2ab.h/.cpp`), mid port, calm, walk budget, contact trace |
| `bots/god2_mid`, `god2_obj` | unfinished wave-2 agent copies (not tested) |
| `bots/agent_copies/` | intermediate agent copies (review copy, trace builds) |
| `bots/test_variants/` | `params.h` of every local test variant (sources = god2b at that time) |
| `bots/bb4` | session 16's bb4 bot (roles, archetype draft, call register), never pushed before |
| `findings/top2/` | the study: an_draft, an_opening, an_economy, an_items, an_fights, an_weak, an_playbooks, gap_g8, g8h_port, patches |
| `findings/live/` | session 16 analyses (an_fights / powers / resources / strategy), sweep sets (setF_top3.json ...), win-rate scan, group and match ids |
| `results/` | paired tables (S0 vs G2A / G2B, G2A vs G2B), G2B module effects, G2A placebo check, local benches |
| `tools/top2/` | study and analysis scripts: gap pipeline, `g2_effects.py` (A/B outcome effects), `g2_mech.py` (mechanism metrics per bit), `pathtrace.py`, `merge_modules.py` |
| `tools/live/` | the platform tooling added or changed in sessions 16-17 (`finish_sweep.py`, `dl_replays.py`, `top_winrates.py`, `timebudget.mjs`, `walks.mjs` ...) |
| `tools/rl/` | the stdlib RL / ES trainer package for a Linux machine |

## Reproduce

These tools expect the repository layout (`bots/`, `tools/`, `experiments/`). Copy a bot folder to `bots/<name>` and the tools to
`tools/` first.

```
cambc build god2b --release
cambc submit god2b -n "note <= 80 chars"
python tools/live/queue_groups.py G2C --set experiments/live/setF_top3.json      # 48 groups (quota 50 per rolling hour)
python tools/live/finish_sweep.py G2C --since <ISO>                              # waits, fetches summaries and replays
python tools/top2/g2_effects.py G2C 16 --ref G2A,S0 --salt 17                    # module effects on outcomes
python tools/top2/g2_mech.py <replay dir> 16 --ref <G2A replay dir> --salt 17    # mechanism metrics per module
python tools/live/paired.py S0 G2C                                               # paired vs god.zip
```
