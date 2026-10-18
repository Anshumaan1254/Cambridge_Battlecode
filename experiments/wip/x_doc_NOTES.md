# x_doc: fight doctrine A4-A7/A9 on legend_m4 (agent `doctrine`, session 8)

Baseline `bots/_m4` (= shipped `legend_m4`, read-only). Copy `bots/_x_doc` (every switch default off = `_m4`);
variants `bots/_xd*`. Patch: `experiments/wip/x_doc.patch` (`cd bots && diff -ruN _m4/src _x_doc/src`).
Rebuild: `SRC=bots/_m4 tools/variant.sh _x_doc && (cd bots/_x_doc && patch -p1 --no-backup-if-mismatch < ../../experiments/wip/x_doc.patch)`,
then `SRC=bots/_x_doc tools/variant.sh _xdN key=val ...`.

## Switches (params.h, end of the struct; all 0 = `_m4`)
- `camp_in_fight` (A5, port of `x_side`): awake camps within 3 hit the nearest champion; 3 = a camp whose nearest body is an
  enemy adds its strength to our DPS, 2 = one hitting us / a counted ally adds to theirs (and to `incoming` when it is us), 1 = both.
- `burst_exit` + `burst_exit_k` 1.1 (A7): in reach, fight not killable, escape possible: drop the fight when our health
  <= k x the sum over enemies in reach of (basic attack + best ready cast). The flee branch then runs (stun chaser, step home).
- `spread_vs_splash` (A4): with a visible enemy Varg within 4 or an enemy with a ready area spell within 5, `clump` = tiles
  next to visible allies within 3; `step_field` ranks those one level below enemy reach (soft, via `g_soft_avoid` in nav.h);
  engage() goal rings drop them when another ring tile is free.
- `pair_space` (A9): Cassi's engage ring keeps 2-3 from a visible Issac (never adjacent) when such a tile is free.
- `support_v2` (A3): an ally seen recalling/banking/teleporting this round is not fight support (`Ally::channeling`, world.cpp).
- `engage_angle`: engage() walks to a ring tile outside the next-turn reach of the target's other visible enemies when one exists.
- `strike_first` (bits) + `strike_hold` 2 (A6): bit 2 = a ranged body without dash or a spell for this distance does not walk
  into range in a proactive fight (the walk spends its attack): hold, at most strike_hold rounds. Bit 1: a proactive fight (not in reach, target not killable) with no ready spell/reset
  and one coming ready within strike_hold rounds: hold (no move) for at most strike_hold rounds.

## Results (ledger; distinct maps only)
Control `_xd0` (= `_x_doc`, all off) vs `_m4` official 17: 50.0, deaths 318-318 (identical games).

| Variant | vs `_m4` official 34 (deaths) | vs `_fA` official 34 |
|---|---|---|
| `_m4` reference | - | 64.7 (409-348) |
| `_xd5` camp_in_fight 3 | **58.8** (299-329) | 70.6 (398-365) |
| `_xd7` burst_exit 1 (k 1.1) | 52.9 (339-333) | 58.8 (410-356) |
| `_xd4` spread_vs_splash 1 | **61.8** (291-348) | 70.6 (377-437) |
| `_xd9` pair_space 1 | 47.1 (343-380) | **73.5** (324-402) |
| `_xd6` strike_first 1 | 44.1 (336-334) | 67.6 (359-395) |
| `_xd6b` strike_first 2 (ranged hold) | 52.9 (333-258) | 61.8 (395-367) |
| `_xd5a` camp_in_fight 1 (both halves) | 44.1 (296-296) | 64.7 (453-390) |
| `_xd7b` burst_exit 1, k 1.5 | 52.9 (361-344) | 52.9 (436-352) |
| `_xd7c` burst_exit 2 (no chaser) | 52.9 (339-333, = `_xd7`) | 58.8 (421-349) |
| `_xd4b` spread_vs_splash 2 | 55.9 (318-360) | 61.8 (441-378) |
| `_xd9b` pair_space 2 | 41.2 (361-296) | 70.6 (368-391) |

88 distinct games (`maps/*.map26a` + `maps/comp`; all / official / deaths):
| Variant | vs `_m4` | vs `_fA` | vs `_ST` |
|---|---|---|---|
| `_xd5` camp_in_fight 3 | **56.8 / 58.8** (545-616) | | |
| `_xd4` spread_vs_splash 1 | 45.5 / 61.8 (584-581) | | |
| `_xd9` pair_space 1 | 52.3 / 47.1 (591-655) | | |
| `_xdC3` cif 3 + spread 1 + pair_space 1 | 47.7 / 44.1 (639-589) | | |

## Diagnosis notes
- Sparring replays `_m4` vs `_fA` (eight, collision, swirl; `tools/strategy_v2/run_all.py`): hit-nobody-back 68% vs 63%
  (the archetype does not reproduce the top teams' 55%); death incidents: burst (above 60% 4 rounds before) 50% vs 39%,
  Varg splash on victim + ally 12% vs 6%; our killers Ren 13 of 45.
- Ladder replays (17 games of `legend_st`, `experiments/ladder_oct18`, same tool): fights deaths 183-34, damage 0.35;
  "they hit first" fights 89 with deaths 110-13; hit-nobody-back 75% vs 50%; our walking-while-hit rounds: enemy within 4
  and moved toward 153, enemy in attack range and moved away 140; death incidents: burst 53% (them 31%), Varg splash on
  victim + ally 8% (them 0%), camp damage in the last 5 rounds 6% (them 20%: they die to camps + us more than we do).
- Sparring (`_m4` vs `_fA`) does not reproduce the ladder gap (hit-nobody-back 68/63, damage ratio 0.88): every A/B below
  is against our own code family, where rules aimed at the top teams' burst move results by noise-level amounts.
