#!/usr/bin/env bash
# Run pb_extract.mjs over every study team's dumps (3 workers) -> C:/battlecode/cache/top2_playbooks/pb_<key>.jsonl
cd /c/battlecode/Cambridge_Battlecode
for k in pbg ifish cm pantheon coo nyx; do
  python tools/live/par.py 3 C:/battlecode/cache/top2_playbooks/pb_$k.jsonl tools/top2/playbooks/pb_extract.mjs -- C:/battlecode/cache/t2dump/$k/*.json.gz
done
