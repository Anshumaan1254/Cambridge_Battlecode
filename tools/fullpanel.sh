#!/bin/bash
# Full panel of one bot: every opponent, the 56-map pool + the 50 held-out maps (gold, gold2, obj) = 212 games each.
#   tools/fullpanel.sh BOT [OUT_DIR] [OPPONENTS...]     (default opponents: _L0 _es2 _r2 _v6 _c3 _ST)
# Summary: python3 tools/sum.py OUT_DIR   (one line per opponent; comp = the 17 official maps)
cd "$(dirname "$0")/.."
bot=$1; out=${2:-/tmp/fullpanel/$1}; shift; shift
opps=${@:-_L0 _es2 _r2 _v6 _c3 _ST}
for o in $opps; do
	[ "$o" = "$bot" ] && continue
	python3 tools/bench.py $bot $o --maps 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a,maps/gold/*.map26a,maps/gold2/*.map26a,maps/obj/*.map26a' --jobs ${PANEL_JOBS:-3} --out $out --quiet
done
