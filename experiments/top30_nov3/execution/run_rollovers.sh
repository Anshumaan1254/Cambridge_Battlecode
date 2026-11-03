#!/bin/bash
# runs rollovers.mjs over out/roll_files.txt in chunks of 20, skipping keys already in out/rollovers.jsonl
cd /home/claude/cambridge_battlecode/experiments/top30_nov3/execution
touch out/rollovers.jsonl
python3 - <<'PY' > out/roll_todo.txt
import json, os
done={json.loads(l)['key'] for l in open('out/rollovers.jsonl')}
for f in open('out/roll_files.txt'):
    f=f.strip()
    if os.path.basename(f)[:-8] not in done and os.path.exists(f): print(f)
PY
split -l 20 out/roll_todo.txt out/roll_chunk_
for c in out/roll_chunk_*; do nice -n 19 node rollovers.mjs out/rollovers.jsonl $(cat $c); rm -f $c; done
echo ROLL_DONE
