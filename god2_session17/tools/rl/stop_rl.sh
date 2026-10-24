#!/usr/bin/env bash
# Stop the background RL run started by ./run_rl.sh. First call: no new generations, the championship and the results
# are still written (a few minutes). Second call: exit at once (resume later with ./run_rl.sh resume rl_results/<run>).
cd "$(dirname "$(readlink -f "$0")")"
[ -f rl_run.pid ] || { echo "no rl_run.pid here: nothing started by ./run_rl.sh"; exit 1; }
PID="$(cat rl_run.pid)"
if kill -0 "$PID" 2>/dev/null; then
  kill -TERM "$PID" && echo "sent stop to $PID; follow the finish with: tail -f rl_run.log"
else
  echo "process $PID is not running (already finished?)"
fi
