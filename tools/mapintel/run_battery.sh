#!/usr/bin/env bash
# Simulation batteries for YOUR bot (tools/mapintel/battery.py: outcome battery + roster battery with both rosters forced).
# Linux, macOS, Windows Git Bash / MSYS.
#   git pull --no-rebase origin main
#   bash tools/mapintel/run_battery.sh --bot NAME            # bots/NAME: your bot, with tools/mapintel/cpp/mapintel/ in its src/
#   bash tools/mapintel/run_battery.sh --bot NAME --quick    # 1-minute function test first (3 maps, 2 roster slots)
# Writes mapintel_battery_<NAME>_<UTC stamp>.tar.gz in the repository root: upload that file. A cut run resumes.
set -e
cd "$(dirname "$0")/../.."
PY=""
for c in python3 python "py -3"; do
	if $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" > /dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "ERROR: no Python 3.8+ found (python3 / python / py -3)" >&2; exit 1; }
if [ "$(cambc --version 2>/dev/null | awk '{print $NF}')" != "3.0.5" ]; then
	echo "installing cambc 3.0.5"
	$PY -m pip install -q cambc==3.0.5 || { echo "ERROR: pip install cambc==3.0.5 failed" >&2; exit 1; }
fi
command -v cambc > /dev/null 2>&1 || { echo "ERROR: cambc is not on PATH after pip install" >&2; exit 1; }
export PYTHONIOENCODING=utf-8
exec $PY tools/mapintel/battery.py "$@"
