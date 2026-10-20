#!/bin/bash
# Baseline of GOD v2 (bots/god) and legend_m15 on the patch-3.0 maps taken from the Nyx replays
cd /home/user/Cambridge_Battlecode
M='maps/nyx_new/*.map26a,maps/comp30/*.map26a'
for B in god _mlkc40; do for O in _mite _ifish _px9; do python3 tools/ledger.py run $B $O --maps "$M" --jobs 4; done; done
python3 tools/ledger.py run god _mlkc40 --maps "$M" --jobs 4
python3 tools/ledger.py run god idle --maps "$M" --jobs 4
