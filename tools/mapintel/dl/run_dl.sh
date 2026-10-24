#!/usr/bin/env bash
# Step 7 (MAPAnalysis.md 5.7): the deep-learning run on YOUR machine's GPU. Linux, macOS, Windows Git Bash / MSYS.
#   git pull --no-rebase origin main
#   bash tools/mapintel/dl/run_dl.sh --quick       # 5-minute function test first (a few epochs: not a result)
#   bash tools/mapintel/dl/run_dl.sh               # the real run: every task, 3 seeds (about 20-60 minutes on an RTX-class GPU)
# Options (passed to dl_train.py): --tasks t1a,t1b,t2,t3  --seeds N  --hidden H  --device cuda|cpu|mps
#   --cpu      install the CPU build of torch instead of the CUDA 12.8 one (no NVIDIA GPU; the real run then takes hours)
# Needs only Python 3.9+ and the internet (pip): a virtual environment mapintel_work/dlvenv gets numpy and torch.
# Input: experiments/results/mapintel/dl_data/dataset.npz (committed). Writes mapintel_dl_<UTC stamp>.tar.gz in the repository root
# (split into .part01, .part02, ... when over 20 MB): upload that file (or every part). Nothing else is changed in the repository.
set -e
cd "$(dirname "$0")/../../.."
CPU=0
ARGS=()
for a in "$@"; do
	if [ "$a" = "--cpu" ]; then CPU=1; else ARGS+=("$a"); fi
done
PY=""
for c in python3 python "py -3"; do
	if $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" > /dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "ERROR: no Python 3.9+ found (python3 / python / py -3)" >&2; exit 1; }
[ -f experiments/results/mapintel/dl_data/dataset.npz ] || { echo "ERROR: experiments/results/mapintel/dl_data/dataset.npz is missing: git pull" >&2; exit 1; }
VENV=mapintel_work/dlvenv
if [ ! -d "$VENV" ]; then
	echo "creating $VENV"
	mkdir -p mapintel_work
	$PY -m venv "$VENV" || { echo "ERROR: python -m venv failed (Debian / Ubuntu: sudo apt install python3-venv)" >&2; exit 1; }
fi
if [ -x "$VENV/Scripts/python.exe" ]; then VPY="$VENV/Scripts/python.exe"; else VPY="$VENV/bin/python"; fi
[ -x "$VPY" ] || { echo "ERROR: no python in $VENV" >&2; exit 1; }
if ! "$VPY" -c "import numpy, torch" > /dev/null 2>&1; then
	echo "installing numpy and torch into $VENV (torch is 1-3 GB with CUDA: this takes a while once)"
	"$VPY" -m pip install -q --upgrade pip
	"$VPY" -m pip install -q numpy || { echo "ERROR: pip install numpy failed" >&2; exit 1; }
	if [ "$CPU" = 1 ]; then
		"$VPY" -m pip install -q torch --index-url https://download.pytorch.org/whl/cpu || { echo "ERROR: pip install torch (CPU) failed" >&2; exit 1; }
	elif [ "$(uname -s)" = "Darwin" ]; then
		"$VPY" -m pip install -q torch || { echo "ERROR: pip install torch failed" >&2; exit 1; }
	else
		# CUDA 12.8 wheels: the build that supports RTX 50-series (Blackwell) cards; older NVIDIA cards run it too
		"$VPY" -m pip install -q torch --index-url https://download.pytorch.org/whl/cu128 || { echo "ERROR: pip install torch (CUDA 12.8) failed; try --cpu" >&2; exit 1; }
	fi
fi
"$VPY" -c "import torch; print('torch', torch.__version__, '| CUDA available:', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no GPU: the run uses the CPU')"
if [ "$CPU" = 0 ] && [ "$(uname -s)" != "Darwin" ] && ! "$VPY" -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)"; then
	echo "WARNING: torch sees no CUDA GPU (driver missing or too old for CUDA 12.8?). The run continues on the CPU and will be slow." >&2
	echo "         Check 'nvidia-smi' (driver 570 or newer for CUDA 12.8), or stop with Ctrl-C and rerun with --cpu --quick to test." >&2
fi
STAMP=$(date -u +%Y%m%d_%H%M)
OUT=mapintel_work/dl_model_$STAMP
export PYTHONIOENCODING=utf-8
"$VPY" -I tools/mapintel/dl/dl_train.py --out "$OUT" --archive "mapintel_dl_$STAMP.tar.gz" ${ARGS[@]+"${ARGS[@]}"}
echo
echo "done: upload mapintel_dl_$STAMP.tar.gz (or all its .partNN files) in the chat. The report is $OUT/report.md."
