#!/bin/bash
# tools/finalcheck.sh CAND [REF=_m1p3] [KEEP_DIR]
# Release checks of a GOD candidate on the installed engine (GOD_Improvement_Plan REL-1 / REL-2, doc 18):
#  1. vs v8 (_v8k1): held-out test152, train156, all308 (abconfirm.sh);
#  2. head-to-head vs REF (the previous best) on all308;
#  3. the 8 third-party proxies on the 21-map pool (42 games each) and the post-patch pool (adapted drafts _k_fit, _k_ci, _q_s2v
#     and the personas _pn*, 21-map pool), side by side with REF;
#  4. unopposed pace (vs idle, 21-map pool);
#  5. platform-mode faults and lost turns on six heavy maps (fueltrace.py --release) vs _v8k1, _pws, _q_s2v.
set -e
cd "$(dirname "$0")/.."
C=$1 R=${2:-_m1p3} K=${3:-}
KEEP=${K:+--keep $K}
M21='maps/comp30/*.map26a,maps/nyx_new/*.map26a,maps/loss_oct20/*.map26a'
M6='maps/comp30/corners_v3.map26a,maps/comp30/contest_v3.map26a,maps/nyx_new/nx31x31_R_c4_9e9a40.map26a,maps/nyx_new/nx60x60_R_c5_0cdefa.map26a,maps/nyx_new/nx100x100_R_c5_bbb066.map26a,maps/loss_oct20/ls50x50_R_c5_56fe6f.map26a'
echo "== 1. vs v8"
tools/abconfirm.sh $C _v8k1 $K
echo "== 2. head-to-head vs $R (all308)"
python3 tools/ledger.py run $C $R --maps "$(cat experiments/pools/all308.csv)" --jobs 4 --chunk 16 $KEEP | tail -1
python3 tools/abstat.py $C $R --pool experiments/pools/all308.csv
python3 tools/abmargin.py $C $R --pool experiments/pools/all308.csv
echo "== 3. third parties and the post-patch pool (21 maps, 42 games each)"
OPPS="_pws _pw _pc _g4 _m15 _mite _ifish _px9 _k_fit _k_ci _q_s2v _pnF _pnI _pnD _pnO _pnA _pnL _pnV _pnS"
for b in $C $R; do for o in $OPPS idle; do python3 tools/ledger.py run $b $o --maps "$M21" --jobs 4 | tail -1; done; done
python3 tools/v8sum.py --opps $(echo $OPPS | tr ' ' ',') $R $C
python3 tools/ledger_pace.py $R $C 2>/dev/null | tail -3 || true
echo "== 5. faults and lost turns (platform mode)"
python3 tools/fueltrace.py $C _v8k1 _pws _q_s2v --maps "$M6" --jobs 4 --release
