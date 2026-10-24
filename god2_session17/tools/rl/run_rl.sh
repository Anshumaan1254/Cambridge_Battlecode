#!/usr/bin/env bash
# One-shot launcher for the RL trainer (Linux). Run from the unzipped folder:
#   ./run_rl.sh                    full training, 3.5 hours, in the background (survives closing the terminal)
#   ./run_rl.sh 5                  full training for 5 hours
#   ./run_rl.sh smoke              20-30 minute end-to-end check (foreground)
#   ./run_rl.sh resume rl_results/<run> [HOURS]   continue a stopped run
#   ./run_rl.sh 3.5 --fg           run in the foreground instead
# Extra options after the first argument go to tools/rl/train_rl.py (e.g. --workers 12).
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

MODE="${1:-3.5}"
[ $# -gt 0 ] && shift || true

say() { printf '\n== %s\n' "$*"; }

say "checking Python"
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "python3 not found. Install it first, e.g.: sudo apt install -y python3 python3-venv python3-pip"; exit 1
fi
"$PY" - <<'EOF'
import sys
if sys.version_info < (3, 8):
    sys.exit(f"Python 3.8+ needed, found {sys.version.split()[0]}")
print("Python", sys.version.split()[0])
EOF
[ "$(uname -s)" = "Linux" ] || echo "note: built for Linux; continuing on $(uname -s)"

say "installing cambc 3.0.5 (the project's SDK version)"
if [ ! -d .venv ]; then
  if ! "$PY" -m venv .venv 2>/dev/null; then
    echo "python3-venv is missing; installing cambc for the user instead (sudo apt install -y python3-venv avoids this)"
  fi
fi
if [ -f .venv/bin/activate ]; then . .venv/bin/activate; PY=python
elif [ -f .venv/Scripts/activate ]; then . .venv/Scripts/activate; PY=python
else export PATH="$HOME/.local/bin:$PATH"; PIPUSER="--user"; fi
if ! "$PY" -m pip show cambc 2>/dev/null | grep -q '^Version: 3.0.5$'; then
  "$PY" -m pip install --quiet --upgrade pip ${PIPUSER:-} || true
  "$PY" -m pip install --quiet ${PIPUSER:-} "cambc==3.0.5"
fi
command -v cambc >/dev/null || { echo "cambc is not on PATH after the install"; exit 1; }
cambc --version

if [ ! -f cmake/CMakeLists.txt ] || [ ! -d sdk/cpp ]; then
  say "restoring the SDK / CMake project files"
  cambc init --yes .
fi

say "machine"
echo "CPU threads: $(nproc 2>/dev/null || echo '?'); memory: $(free -g 2>/dev/null | awk '/Mem:/ {print $7 " GB available of " $2}' || echo '?')"
echo "the first bot build downloads cambc's compiler toolchain (cmake, ninja, wasi-sdk): internet needed once"

FG=0
ARGS=()
for x in "$@"; do if [ "$x" = "--fg" ]; then FG=1; else ARGS+=("$x"); fi; done

case "$MODE" in
  smoke)
    say "smoke test (foreground)"
    exec "$PY" tools/rl/train_rl.py --smoke "${ARGS[@]+"${ARGS[@]}"}" ;;
  resume)
    RUN="${ARGS[0]:?usage: ./run_rl.sh resume rl_results/<run> [HOURS]}"
    HOURS="${ARGS[1]:-2}"
    CMD=("$PY" tools/rl/train_rl.py --resume "$RUN" --hours "$HOURS" "${ARGS[@]:2}") ;;
  *)
    CMD=("$PY" tools/rl/train_rl.py --hours "$MODE" "${ARGS[@]+"${ARGS[@]}"}") ;;
esac

if [ "$FG" = 1 ]; then
  say "training in the foreground: ${CMD[*]}"
  exec "${CMD[@]}"
fi
say "training in the background: ${CMD[*]}"
nohup "${CMD[@]}" > rl_run.log 2>&1 &
echo $! > rl_run.pid
sleep 2
echo "started, PID $(cat rl_run.pid)"
echo "  watch:   tail -f rl_run.log"
echo "  stop:    ./stop_rl.sh        (graceful: still writes the results; run it twice to exit at once)"
echo "  results: rl_results/<run>/report.md and the archive rl_results_<run>.tar.gz in this folder"
