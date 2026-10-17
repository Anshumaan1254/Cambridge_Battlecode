#!/bin/bash
# usage: tools/panel.sh BOT [MAPS_GLOB] [OPPONENTS...]
# One summary line per opponent (all maps, both sides). Default opponents: the sparring panel.
bot=$1; maps=${2:-'maps/ladder/*.map26a'}; shift 2 2>/dev/null
opps=${@:-"_base starter-cpp _rush _aggro _cibase"}
out=${PANEL_OUT:-/tmp/panel_out}
for o in $opps; do
  python3 tools/bench.py $bot $o --maps "$maps" --out $out --quiet | grep '^=='
done
