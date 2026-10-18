# x_contest: lone-monolith maps (agent `contest`, session 7, work in progress)

Bot copy `bots/_x_contest` (from `_m4`); patch `experiments/wip/x_contest.patch` (vs `_m4`). Variants `_xc*`, `_xm*`, `_xg*`, `_xp*` (all params of the copy).
Status: in progress. Everything below is behind `mono_*` switches (all default off) gated by the detector `World::mono_mode`.

## Findings so far
- Detector (`mono_plan`, `mono_share` 0.9): share of the map's gem rate (gems / respawn) held by single-camp monoliths. On the 107 maps of every pool
  it is on for `contest`, `lad_50x50_R_c5_65bb75` (identical copy) and the 12 `gold_mono_*` (gold, gold2), and for nothing else
  (`gold_monoelk*` 0.53-0.69, `gold_monowolf` 0.71, controls 0.39, generated maps <= 0.26 are below 0.9).
- contest is decided in the first 100 rounds: in 16 games of `_m4` vs `_ST`/`_m2` (4 geometry variants x 2 sides) 11 had one team wiped by r200, and the
  final deaths are 50-65 vs 10-15 for whoever lost the opening (snowball, the loser feeds bodies to a spawn-camping winner).
  Ledger rows: tools/ledger.py keys, see below.
