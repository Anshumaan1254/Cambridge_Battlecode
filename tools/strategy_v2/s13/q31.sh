#!/bin/bash
# patch 3.0 draft screen on the GOD code (_g2): forced compositions vs legend_m15 (_mlkc40), Mite and ifish proxies, official 17
cd /home/user/Cambridge_Battlecode
for b in _gd0 _gdh1 _gdh2 _gdh3 _gdw _gdh4; do
  for o in _mlkc40 _mite _ifish; do python3 tools/ledger.py run $b $o --maps 'maps/comp/*.map26a' --jobs 2 > /dev/null 2>&1; done
  echo "done $b $(date +%H:%M:%S)"
done
