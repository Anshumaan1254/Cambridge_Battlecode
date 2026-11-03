#!/bin/bash
# decode downloaded replays until the downloader is done and nothing is left
cd /home/claude/cambridge_battlecode/experiments/deep_research_nov3/v95
while true; do
  n=0
  while read id map; do
    if [ -s replays/$id.repl26a ] && [ ! -s dec/$id.json ]; then
      timeout 300 node /home/claude/cambridge_battlecode/tools/replay/decode.mjs replays/$id.repl26a --gold-captures --out dec/$id.json 2>>dec.err || echo "DECFAIL $id" >> dec.err
      n=$((n+1))
    fi
    if [ -s dec/$id.json ] && [ ! -s mj/$id.json ] && [ -f /home/claude/data/mapjson_pool/$map.json ]; then
      cp /home/claude/data/mapjson_pool/$map.json mj/$id.json
    fi
  done < ids_all.txt
  if grep -q DLDONE dl_progress.log 2>/dev/null && [ $n -eq 0 ]; then echo DECDONE >> dl_progress.log; break; fi
  sleep 10
done
