#!/bin/bash
# usage: dl_decode.sh IDFILE ; downloads, decodes, copies map json (idempotent)
cd /home/claude/cambridge_battlecode/experiments/deep_research_nov3/v95
while read id map; do
  [ -s dec/$id.json ] && continue
  [ -s replays/$id.repl26a ] || timeout 120 cambc matches download $id -o replays/$id.repl26a >/dev/null 2>>dl.err
  [ -s replays/$id.repl26a ] || { echo "DLFAIL $id" >> dl.err; continue; }
  timeout 300 node /home/claude/cambridge_battlecode/tools/replay/decode.mjs replays/$id.repl26a --gold-captures --out dec/$id.json 2>>dec.err || echo "DECFAIL $id" >> dec.err
  [ -f /home/claude/data/mapjson_pool/$map.json ] && cp /home/claude/data/mapjson_pool/$map.json mj/$id.json
done < $1
echo DONE $1 $(date -u +%H:%M:%S) >> progress.log
