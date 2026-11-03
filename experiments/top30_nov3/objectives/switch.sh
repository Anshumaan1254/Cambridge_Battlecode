#!/bin/bash
cd /home/claude/cambridge_battlecode/experiments/top30_nov3/objectives
while ! grep -q "^me .* to do" out_extract.log; do sleep 10; done
pkill -f "extract_obj.py all" ; sleep 1
nohup nice -n 19 python3 extract_obj.py me --jobs 1 --reverse > out_extract_me2.log 2>&1 &
echo switched $(date -u +%H:%M)
