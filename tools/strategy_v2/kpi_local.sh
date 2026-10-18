#!/bin/bash
# Ladder-style KPIs of a local match-up: plays BOT vs OPP on the 17 official maps (side A = BOT; the B games too, for the
# win count), decodes BOT's side-A replays and writes report.md, micro.md (distance bands, hit ranges, openers) and
# teamsum.md (per-champion farming) into OUT. Compare with experiments/ladder_top3/ and experiments/ladder_m5/.
#   tools/strategy_v2/kpi_local.sh BOT OPP OUT [JOBS]
set -e
cd "$(dirname "$0")/../.."
bot=$1; opp=$2; out=$3; jobs=${4:-2}
[ -n "$out" ] || { echo "usage: $0 BOT OPP OUT [JOBS]"; exit 1; }
mkdir -p "$out/games" "$out/sideA"
python3 tools/bench.py "$bot" "$opp" --maps 'maps/comp/*.map26a' --jobs "$jobs" --out "$out/games" --quiet | tail -1
run=$(ls -d "$out"/games/*/ | tail -1)
cp "$run"/*_A.repl26a "$out/sideA/"
python3 tools/strategy_v2/run_all.py "$out/an" "$out/sideA" > "$out/run_all.log" 2>&1
cp "$out/an/report.md" "$out/report.md"
python3 -I tools/strategy_v2/micro.py --skip contest "$out/an/dmg=*:$bot:$opp" > "$out/micro.md"
python3 -I tools/strategy_v2/teamsum.py --skip contest "$out/an/out=*:$bot:$opp" > "$out/teamsum.md"
grep -A3 "^| KPI" "$out/report.md" | head -2 > /dev/null
echo "== $bot vs $opp: $out/{report,micro,teamsum}.md"
sed -n '/^## KPIs/,$p' "$out/report.md"
