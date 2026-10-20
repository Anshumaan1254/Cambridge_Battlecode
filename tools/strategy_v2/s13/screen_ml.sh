#!/bin/bash
# screen_ml.sh VARIANT... : official 34 vs _mlkc40 (new base) and the 5 proxies, through the ledger (resumable)
cd /home/user/Cambridge_Battlecode
for b in "$@"; do
  for o in _mlkc40 _mite _ifish _px9 _snk _fA; do
    python3 tools/ledger.py run $b $o --maps 'maps/comp/*.map26a' --jobs 2 > /dev/null 2>&1
  done
  echo "done $b $(date +%H:%M:%S)"
done
