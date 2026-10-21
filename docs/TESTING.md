# Testing the 3.0.4 GOD (dynamic draft): commands that reproduce every number in docs/strategy_v2/17_PATCH_3_0_4.md

Engine cambc 3.0.4 (`tools/setup_session.sh` installs it; rows land in `experiments/results/ledger_v3_0_4/`). v8 = `_v8k1` (GOD v8 as
shipped). Pools: `experiments/pools/` (all308, train156, test152; `README.md` there).

```bash
# 1. the engine's champion numbers (3.0.2 vs 3.0.4)
mkdir -p bots/_probe304/src && cp tools/probe/champion_stats_main.cpp bots/_probe304/src/main.cpp
cambc run _probe304 idle --map maps/comp30/corners_v3.map26a --rounds 2 -o /tmp/probe      # team-a.stdout inside the replay bundle

# 2. substitution screens (v8's draft with one champion swapped; draft ids in params.h pd_sub_from)
SRC=bots/god tools/variant.sh _q_s2v pd_sub_from=4 pd_sub_to=1                              # Vesper wherever v8 drafts Stellar
python3 tools/ledger.py run _q_s2v _v8k1 --maps "$(cat experiments/pools/train156.csv)" --jobs 4 --keep KEEP
python3 tools/abstat.py _q_s2v _v8k1 --pool experiments/pools/train156.csv
python3 tools/drafts_of.py KEEP/_q_s2v_vs__v8k1 --by-size                                   # maps where our roster differs, by team size

# 3. the draft-value model: dataset from kept games, map features, fit, export
python3 tools/draftmodel/dataset.py GAMES.jsonl KEEP/_q_*_vs__v8k1 KEEP/_r_*_vs__v8k1 KEEP/_k_*_vs__v8k1
SRC=bots/god tools/variant.sh _feat --define "LEGEND_FEATURES 1"                            # FEAT lines: one 1-round game per map
python3 tools/draftmodel/fit.py GAMES.jsonl experiments/results/probe_v3_0_4/champions_engine_3_0_4.txt MAPFEAT.json --l2 1
python3 tools/draftmodel/fit2.py GAMES.jsonl experiments/results/probe_v3_0_4/champions_engine_3_0_4.txt MAPFEAT.json --export

# 4. the dynamic draft, its drafts, its fuel, its A/B
SRC=bots/god tools/variant.sh _m1 pd_stat=3
tools/draftcheck.sh _m1 _v8k1 'maps/comp30/*.map26a'                                        # both drafts from 1-round games
SRC=bots/god tools/variant.sh _dfm pd_stat=3 --define "DRAFT_FUEL 1"                        # fuel of every draft turn (DFUEL lines)
tools/abconfirm.sh _m1 _v8k1 KEEP                                                           # test152, train156, all308 + by folder
python3 tools/v8sum.py --opps _pws,_pw,_pc,_g4,_m15,_mite,_ifish,_px9 _v8k1 _m1             # third parties (21-map pool)
python3 tools/fueltrace.py _m1 _v8k1 _pws --maps "$M6" --jobs 4 --release                   # faults, lost turns (platform mode)
```

# Testing the GOD upgrade: commands that reproduce every number in docs/CHANGES.md

Run from the repository root after `tools/setup_session.sh` (cambc 3.0.2, the wasm toolchain, and the sparring bots it rebuilds and
checks by source hash: `_v8k1` = GOD v8, `_g4` = GOD v2, `_pw`, `_pws`, ...). Variants are copies of `bots/god` with switches set:
`SRC=bots/god tools/variant.sh NAME key=value ... [--define "MACRO 1"]`. Every game result goes through `tools/ledger.py` (rows keyed by
both bots' source hashes, per engine version: `experiments/results/ledger_v3_0_2/`), so a cut run resumes and old rows never count for
changed code.

```bash
POOL='maps/comp30/*.map26a,maps/nyx_new/*.map26a,maps/loss_oct20/*.map26a'     # the 21 official patch-3.0 maps (42 games per cell)
M6='maps/comp30/corners_v3.map26a,maps/comp30/contest_v3.map26a,maps/nyx_new/nx31x31_R_c4_9e9a40.map26a,maps/nyx_new/nx60x60_R_c5_0cdefa.map26a,maps/nyx_new/nx100x100_R_c5_bbb066.map26a,maps/loss_oct20/ls50x50_R_c5_56fe6f.map26a'
```

## 1. All new switches off = GOD v8 (same events, same shared-memory bytes)

```bash
mkdir -p bots/_v8ref && git archive e593c58 bots/god/src | tar -x --strip-components=2 -C bots/_v8ref   # v8 + the SM_TRACE dump
SRC=bots/_v8ref tools/variant.sh _ad_ref --define "SM_TRACE 1"
SRC=bots/god tools/variant.sh _ad_new --define "SM_TRACE 1"
python3 tools/actiondiff.py _ad_ref _ad_new _pws --maps "$M6" --jobs 4    # expect "identical (N events, M shared-memory dumps)" x 12
```

`SM_TRACE` prints the 8 shared bytes after every turn inside `debug_block` (no fuel), so the trace itself changes nothing.

## 2. Both SDKs build

- 3.0.2 (Heart of Ruin, Golem): `cambc build god`.
- 2.2.5 (no Heart of Ruin, no Golem, no `ward::owner()`): in a scratch directory, `pip download cambc==2.2.5 --no-deps`, unpack the wheel,
  run its `cambc-2.2.5.data/scripts/cambc init --yes .` (fetches the old SDK), copy `bots/god/src` to `bots/chk/src` there and
  `cambc build chk` with that CLI first on `PATH`. Do the same for a variant's `src` to check a configuration (the switches are
  `constexpr`, so each configuration compiles different code).

## 3. Opponent-model calibration (F1)

```bash
SRC=bots/god tools/variant.sh _omT opp_model=1 om_act=0 --define "OPP_TRACE 1"           # classify and trace only
for s in 1:_pxF 2:_pxI 3:_pxD 4:_pxO 5:_pxA 6:_pxL; do SRC=bots/god tools/variant.sh ${s#*:} pxs_style=${s%%:*}; done
# styles: 1 farmer, 2 invader, 3 deathball, 4 objective, 5 ambush, 6 altar denier
OUT=experiments/results/om/traces_train_v1.jsonl
for p in "_pxF farmer" "_pxI invader" "_pxD deathball" "_pxO objective" "_pxA ambush" "_pxL altar" "_v8k1 none"; do set -- $p
  python3 tools/omtrace.py _omT $1 $2 --maps 'maps/comp30/*.map26a' --jobs 4 --out $OUT; done
OUT=experiments/results/om/traces_test_v1.jsonl
for p in "_pxF farmer" "_pxI invader" "_pxD deathball" "_pxO objective" "_pxA ambush" "_pxL altar" "_v8k1 none"; do set -- $p
  python3 tools/omtrace.py _omT $1 $2 --maps 'maps/nyx_new/*.map26a,maps/loss_oct20/*.map26a' --jobs 3 --out $OUT; done
```

Fit and export (reproduces `bots/god/src/om_model.h` byte for byte; train accuracy 0.799, held-out 0.697):

```bash
python3 tools/omfit.py --lambda 0.8 --classes none,raider --merge invader:raider,deathball:raider --export bots/god/src/om_model.h
```

Decision replay with the exported weights and the bot's hysteresis (65% of raider windows in the INVADER plan, 31% of the others):

```bash
python3 tools/omreport.py experiments/results/om/traces_test_v1.jsonl            # --on 0.6 --off 0.4 --min 3 --start 100 by default
```

Switching proxies (style changes at rounds 300 / 500 / 800, for the detection delay; built, traces not collected):
`SRC=bots/god tools/variant.sh _pxS3 pxs_style=1 pxs_style2=2 pxs_switch=300` (`_pxS5`: 2 -> 1 at 500, `_pxS8`: 1 -> 3 at 800, `_pxSM`: 1 -> 3
at 300 -> 1 at 800 with `pxs_style3=1 pxs_switch2=800`), then
`python3 tools/omtrace.py _omT _pxS3 farmer --switch 300:invader --maps "$POOL" --out experiments/results/om/traces_switch_v1.jsonl` and
`python3 tools/omreport.py experiments/results/om/traces_switch_v1.jsonl` (prints rounds to detect each switch).

## 4. Local strength cells (measured before the branch-pair rule; F3-F6)

```bash
SRC=bots/god tools/variant.sh _u_cf chain_farm=1
SRC=bots/god tools/variant.sh _u_an anchors=3 handoff=1
SRC=bots/god tools/variant.sh _u_dm dm_plan=1 ward_plan=1
SRC=bots/god tools/variant.sh _u_gk gank=1
SRC=bots/god tools/variant.sh _u_da deny_altar=1
for v in _u_cf _u_an _u_dm _u_gk _u_da; do for o in _v8k1 _pws _pw _g4; do
  python3 tools/ledger.py run $v $o --maps "$POOL" --jobs 4; done; done
python3 tools/v8sum.py --opps _v8k1,_pws,_pw,_g4 _v8k1 _u_cf _u_an _u_dm _u_gk _u_da
```

The rows behind docs/CHANGES.md were played with the sources of commit 85cf08f; rebuilt variants carry new source hashes and are played
again by `ledger.py` (the old rows stay in the ledger under the old hashes).

## 5. Fuel and function (what the branch pairs are checked with)

```bash
SRC=bots/god tools/variant.sh _ft_off --define "FUEL_TRACE 1"
SRC=bots/god tools/variant.sh _ft_on opp_model=1 om_learned=1 --define "FUEL_TRACE 1"
python3 tools/fueltrace.py _ft_on _v8k1 _pxI _pws --maps "$M6" --jobs 4
python3 tools/fueltrace.py _ft_off _v8k1 _pxI _pws --maps "$M6" --jobs 4
```

Per opponent: games finished, wins (information only), bot faults (engine diagnostics), our lost turns after round 3 (turn rollovers;
rounds 1-3 are the heavy opening turns), the opponent's, the mean fuel left at the end of our turns and the share below 10k, and the
opponent model's fuel per body-turn (mean, median, p99, max; `OMF` lines, printed by `Brain::om_tick_traced()`). The per-body split in
docs/CHANGES.md comes from the same `OMF r=<round> i=<body> <fuel>` lines in each replay's team stdout (`team-a.stdout` / `team-b.stdout`
inside the `.repl26a` zip; strip NUL bytes).

A branch's own zip is checked as on the platform: unzip `submissions/god.zip` into `bots/<name>/` (it holds `src/` only), then
`python3 tools/fueltrace.py <name> _v8k1 _pws _pxI --maps "$M6" --release` (no trace lines in release mode; faults and lost turns still count).
