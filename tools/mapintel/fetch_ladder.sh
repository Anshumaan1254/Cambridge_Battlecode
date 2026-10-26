#!/usr/bin/env bash
# Current-patch ladder data for tools/mapintel (the user's machine; Linux, macOS, Windows Git Bash / MSYS).
#   git pull --no-rebase origin main
#   pip install cambc==4.0.0             # patch 2.0.0 (the script installs it when cambc is missing or older)
#   cambc login                          # once, by the user (never scripted)
#   bash tools/mapintel/fetch_ladder.sh  # options are passed to tools/mapintel/ladder_fetch.py (see its --help)
# Keeps both teams on engine >= 2.0.0, on the 70 maps of maps/s3. Writes mapintel_ladder_<UTC stamp>.tar.gz in the repository root
# (.part00, .part01 ... when over 20 MB): upload that file (or all its parts). A cut run resumes (lists merge, replays skip).
set -e
cd "$(dirname "$0")/../.."
CAMBC_VERSION=4.0.0
PY=""
for c in python3 python "py -3"; do
	if $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" > /dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "ERROR: no Python 3.8+ found (python3 / python / py -3)" >&2; exit 1; }
VER="$(cambc --version 2>/dev/null | awk '{print $NF}')"
if ! $PY -c "import sys; v = tuple(int(x) for x in sys.argv[1].split('.')); sys.exit(0 if v >= tuple(int(x) for x in sys.argv[2].split('.')) else 1)" "${VER:-0}" "$CAMBC_VERSION" > /dev/null 2>&1; then
	echo "cambc ${VER:-missing}: installing cambc $CAMBC_VERSION"
	$PY -m pip install -q "cambc==$CAMBC_VERSION" || { echo "ERROR: pip install cambc==$CAMBC_VERSION failed" >&2; exit 1; }
fi
command -v cambc > /dev/null 2>&1 || { echo "ERROR: cambc is not on PATH (pip install cambc==$CAMBC_VERSION; then open a new terminal)" >&2; exit 1; }
export PYTHONIOENCODING=utf-8
exec $PY tools/mapintel/ladder_fetch.py "$@"
