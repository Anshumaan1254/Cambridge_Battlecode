#!/bin/bash
while kill -0 25555 2>/dev/null; do sleep 15; done
cd /home/user/Cambridge_Battlecode
for b in _g4fm _g4ml5 _g4ml3 _g4tm30; do for o in _g4 _mlkc40 _mite _ifish _px9 _snk _fA; do python3 tools/ledger.py run $b $o --maps 'maps/comp/*.map26a' --jobs 4 > /dev/null 2>&1; done; python3 tools/ledger.py run $b _g4 --maps 'maps/p30/*.map26a' --jobs 4 > /dev/null 2>&1; echo "done $b $(date +%H:%M:%S)"; done
