#!/bin/bash
# Download + decode the replays listed in v88_bugs/to_download.txt (read-only CLI), same as map_fail/download_decode.sh.
cd /home/claude/cambridge_battlecode/experiments/ladder_nov2
for id in $(cat v88_bugs/to_download.txt); do
  [ -s replays/$id.repl26a ] || timeout 120 cambc matches download $id -o replays/$id.repl26a >/dev/null 2>&1 || echo "DL FAIL $id"
  [ -s dec/$id.json ] || nice -n 19 node ../../tools/replay/decode.mjs replays/$id.repl26a --gold-captures --out dec/$id.json 2>/dev/null || echo "DEC FAIL $id"
  m=$(grep -m1 "\"matchId\": \"$id\"" matches_me.jsonl | python3 -c "import json,sys;print(json.loads(sys.stdin.read())['map'])")
  [ -s mj/$id.json ] || cp /home/claude/data/mapjson_pool/$m.json mj/$id.json
  echo "OK $id $(date +%T)"
done
echo DONE
