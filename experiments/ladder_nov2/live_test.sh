#!/bin/bash
# live_test.sh BOT NOTE PLAN [MAXGROUPS]
# The user's free-hand rule (Nov 3, 22:00 IST): a candidate may go live. Upload BOT (the platform makes the newest build live by
# itself), wait until it is the active version plus 2 minutes (so the new build, not the previous one, plays), wait for free
# match-group quota, queue the paired groups of PLAN, wait until they finish, print three_way.py's comparison.
set -u
cd /home/claude/cambridge_battlecode
BOT=$1; NOTE=$2; PLAN=$3; MAX=${4:-47}
ver() { cambc submissions list --json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print((d.get('active') or {}).get('version'), (d.get('submissions') or [{}])[0].get('version'), (d.get('submissions') or [{}])[0].get('status'))"; }
before=$(ver | awk '{print $2}')
for try in 1 2 3; do
  out=$(cambc submit "$BOT" -n "$NOTE" 2>&1); echo "$(date -u +%H:%M:%S) submit: $(echo "$out" | tail -1)"
  echo "$out" | grep -q "Submitted bot version" && break
  sleep 20
done
new=$(echo "$out" | grep -oE "version [0-9]+" | awk '{print $2}')
[ -z "$new" ] && { echo "upload failed"; exit 1; }
for i in $(seq 1 90); do
  set -- $(ver); [ "$1" = "$new" ] && break
  [ "$3" != "queued" ] && [ "$3" != "building" ] && [ "$3" != "active" ] && [ "$2" = "$new" ] && echo "  status $3"
  sleep 10
done
echo "$(date -u +%H:%M:%S) v$new active"; sleep 120
for i in $(seq 1 60); do
  free=$(cambc match-groups quota --json 2>/dev/null | python3 -c "import json,sys; q=json.load(sys.stdin)['quota']; print(q['limit']-q['used'])")
  [ "${free:-0}" -ge "$MAX" ] && break; sleep 30
done
echo "$(date -u +%H:%M:%S) quota free $free"
python3 experiments/ladder_nov2/ladder_loop.py paired-run --plan "$PLAN" --max "$MAX" --execute --force 2>&1 | grep -cE "^\s*queued" | sed 's/^/queued groups: /'
for i in $(seq 1 60); do
  r=$(timeout 300 python3 experiments/ladder_nov2/three_way.py "$PLAN" 2>&1 | tail -14)
  echo "$r" | grep -q "(0 pending)" && break; sleep 30
done
echo "$(date -u +%H:%M:%S) v$new results:"; echo "$r"
