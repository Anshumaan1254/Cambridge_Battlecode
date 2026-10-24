#!/usr/bin/env bash
# Current-patch ladder data for tools/mapintel (the user's machine; Linux, macOS, Windows Git Bash / MSYS).
#   git pull --no-rebase origin main
#   pip install cambc==3.0.5
#   cambc login                          # once, by the user (never scripted)
#   bash tools/mapintel/fetch_ladder.sh  # options are passed to tools/mapintel/ladder_fetch.py (see its --help)
# Writes mapintel_ladder_<UTC stamp>.tar.gz in the repository root: upload that file. A cut run resumes (lists merge, replays skip).
set -e
cd "$(dirname "$0")/../.."
PY=""
for c in python3 python "py -3"; do
	if $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" > /dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "ERROR: no Python 3.8+ found (python3 / python / py -3)" >&2; exit 1; }
command -v cambc > /dev/null 2>&1 || { echo "ERROR: cambc is not on PATH (pip install cambc==3.0.5)" >&2; exit 1; }
export PYTHONIOENCODING=utf-8
exec $PY tools/mapintel/ladder_fetch.py "$@"
