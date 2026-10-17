#!/bin/bash
# usage: tools/panel.sh BOT [MAPS_GLOB] [OPPONENTS...]
# One summary line per opponent (all maps, both sides). Default opponents: the sparring panel.
# PANEL_JOBS=N limits parallel games (default: all CPUs); PANEL_OUT=DIR keeps the replays and statistics.
bot=$1; maps=${2:-'maps/ladder/*.map26a'}; shift 2 2>/dev/null
opps=${@:-"_base starter-cpp _rush _aggro _cibase"}
out=${PANEL_OUT:-/tmp/panel_out}
jobs=${PANEL_JOBS:+--jobs $PANEL_JOBS}
for o in $opps; do
  python3 tools/bench.py $bot $o --maps "$maps" --out $out $jobs --quiet | grep '^=='
done
