# x_ct: contest plan (agent `ct`, session 11/S7R workflow `contest-and-neutral`)

Baseline `_m10` (= `_m8` play). Copy `bots/_x_ct` (= `_m10` + `mono_*` code, diff in `x_ct.patch`), variants `_ct0`..`_ct5` (params of the copy).
Test maps `maps/ct/` (contest_sw, contest_tr, contest_swtr = geometry variants; pert_s1..6 = perturbed copies). Helper scripts of the previous
agent: /tmp/ct/ (cell.sh, pools.sh, sum.py, mono.mjs); lost with the container, not needed.
Contest pool CT4 = `maps/comp/contest.map26a,maps/ct/*.map26a` (10 maps = 20 games); GM = gold_mono_* of gold, gold2 (12 maps).

## State at takeover (20:30)
- `_ct0` = detector only (identical to `_m10`). `_ct1` mono_open_rounds 150: vs `_m8` 25.0 on CT4 (bad), vs `_mite` 45, `_ifish` 45.
- `_ct2..5` cells were being run by /tmp/ct/run1.sh (CT4 vs `_mite _ifish _px9 _m8`).

## Plan
1. Understand how contest is lost/won (replays of `_m10` vs `_mite`/`_snk`/`_ifish` on contest, both sides).
2. Build a plan gated by `World::mono_mode`: no feeding in the opening, Treasure/gold for the tiebreak, spawn-camp avoidance, monolith with the whole team.
3. Inertness check on the 88 distinct games vs `_m10`.

## Results log
(see below; updated after every result)

### 20:30-21:10 findings
- Proxy of the ladder killer: `_snk` (sneaky-bush draft Tavi, Willow, Stellar, Ren, Prism). `_ct0` (= `_m10` play) vs `_snk` on CT4 (contest + maps/ct, 20 games): **30%**
  (contest: 8-90 deaths, 2860 vs 16154 gold). Games are bimodal: whoever wins the first centre clash (r30-60, altars at (24,24)) snowballs
  (1000-0 with deaths 16-41, or 0-0 with 8-90). Both teams walk to the centre gold triples at r20-40; our bodies arrive one by one.
- Monolith kill speed: a mature team of 5-6 does 600 HP/round (20000 HP in ~35 rounds), an early one ~120/round.
  A body on spawn heals 100% per round: `_cf100000` (probe: hold everyone on spawn all game) = 0 deaths, 0 kills, 0 gems, snk earns 17.4k gold
  (the proxy never sieges an empty spawn): turtling alone loses the gold tiebreak. When snk follows 3 bodies to our spawn it dies there (w1 game 1000-0).
- CT4 results (20 games per cell, win %): snk / mite / ifish / px9 / m8 / fA
  `_ct0` 30/60/50/50/50/75; `_ct1` (skip enemy half to r150) mite 45 ifish 45 px9 50 m8 25; `_ct2` (to r300) 35/20/35/20: **passivity loses**;
  **`_ct3` (GROUPED stance to r150) 75/55/60/55/65/85**; **`_cw1` (GROUPED to r300) 70/55/70/55/65/90**; `_ct4` (mono_build 3) mite 45 ifish 60 px9 55 m8 45;
  `_ct5` (mono_obj) mite 55 ifish 55 px9 45 m8 45.
- New code in `bots/_x_ct2` (= `_x_ct` + probes, all behind mono_* switches): `mono_fort`/`mono_fort_until` (probe), `mono_group_w/_r` (stronger cohesion
  penalty during mono_grouped_until), `mono_rg*` (regroup: outnumbered by >= 3 -> team goes home to spawn for mono_rg_hold rounds).
  `_rg1`: bodies do gather on spawn r40-60, but leave together after 30 rounds into the waiting pack: 90 deaths still.
- Bigger pool: `maps/ct2/pert_s7..s30` (24 more perturbed copies of contest, `--keep` team A spawn) -> CT34 = contest + maps/ct + maps/ct2 (34 maps, 68 games).
