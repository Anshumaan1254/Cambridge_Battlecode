#!/bin/bash
# wait until 13:34Z (or every game decoded and processed), then rerun every summary into out/
cd /home/claude/cambridge_battlecode/experiments/deep_research_nov3/v95
while [ "$(date -u +%H%M)" -lt 1334 ]; do
  nd=$(ls dec | wc -l); ng=$(ls out/g | wc -l)
  [ "$nd" -ge 225 ] && [ "$ng" -ge 225 ] && break
  python3 -c "import time; time.sleep(20)"
done
nice -n 19 python3 -I aggregate.py > out/summary.txt 2>&1
nice -n 19 python3 -I obj_v95.py > out/obj.txt 2>&1
nice -n 19 python3 -I bags.py > out/bags.txt 2>&1
nice -n 19 python3 -I wards.py > out/wards.txt 2>&1
echo "FINAL $(date -u +%T) dec $(ls dec | wc -l) g $(ls out/g | wc -l)"
