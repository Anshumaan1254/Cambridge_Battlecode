#!/usr/bin/env bash
# Simulation batteries for YOUR bot (tools/mapintel/battery.py: outcome battery + roster battery with both rosters forced).
# Linux, macOS, Windows Git Bash / MSYS. Patch 2.0.0: cambc 4.0.0 (installed when another version is on PATH), the 70 maps of maps/s3.
#   git pull --no-rebase origin main
#   bash tools/mapintel/run_battery.sh --bot NAME            # bots/NAME: your bot, with tools/mapintel/cpp/mapintel/ in its src/
#   bash tools/mapintel/run_battery.sh --bot NAME --quick    # function test first (3 maps, 2 roster slots, idle opponent)
#   bash tools/mapintel/run_battery.sh --from god18 --bot _mi_v18   # bots/_mi_v18 = a battery-ready copy of bots/god18 (prepare_bot.py)
# Writes mapintel_battery_<NAME>_<UTC stamp>.tar.gz in the repository root: upload that file. A cut run resumes.
set -e
cd "$(dirname "$0")/../.."
CAMBC_VERSION=4.0.0
PY=""
for c in python3 python "py -3"; do
	if $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" > /dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "ERROR: no Python 3.8+ found (python3 / python / py -3)" >&2; exit 1; }
if [ "$(cambc --version 2>/dev/null | awk '{print $NF}')" != "$CAMBC_VERSION" ]; then
	echo "installing cambc $CAMBC_VERSION (the engine of the games must be the platform's: engine 2.0.0)"
	$PY -m pip install -q "cambc==$CAMBC_VERSION" || { echo "ERROR: pip install cambc==$CAMBC_VERSION failed" >&2; exit 1; }
fi
command -v cambc > /dev/null 2>&1 || { echo "ERROR: cambc is not on PATH after pip install (open a new terminal)" >&2; exit 1; }
export PYTHONIOENCODING=utf-8
exec $PY tools/mapintel/battery.py "$@"
