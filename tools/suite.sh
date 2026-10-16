#!/bin/bash
# usage: tools/suite.sh [BOT] [OPPONENT ...]   (default: legend vs the standard sparring set)
# Runs tools/bench.py for each opponent on every map, both sides, and prints one summary line each.
bot=${1:-legend}; shift || true
opps=${@:-"starter-cpp _v1 _v1aggro _v1passive _deathball"}
for o in $opps; do
  python3 tools/bench.py $bot $o --jobs ${JOBS:-4} --quiet 2>&1 | tail -1
done
