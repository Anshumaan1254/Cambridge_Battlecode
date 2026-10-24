#!/usr/bin/env bash
# Step 7 (MAPAnalysis.md 5.7): the deep-learning run on YOUR NVIDIA GPU (e.g. an RTX 5070 laptop GPU). Windows Git Bash / MSYS, Linux.
#   git pull --no-rebase origin main
#   bash tools/mapintel/dl/run_dl.sh --quick       # ~5-minute function test on the GPU (a few epochs: not a result)
#   bash tools/mapintel/dl/run_dl.sh               # the real run: every task, 3 seeds, on the GPU
# Options (passed to dl_train.py): --tasks t1a,t1b,t2,t3  --seeds N  --hidden H
#   --cpu      no GPU: CPU torch instead (the real run then takes many hours); macOS always uses this path (no CUDA)
# Python: the script picks python3 / python / py -3.12 / py -3.13 / py -3.11 / py -3; force one with PYTHON="py -3.12" bash ...
# Needs Python 3.10-3.13 (64-bit), an NVIDIA driver 570 or newer (RTX 50-series need it), about 6 GB of free disk for torch, internet.
# A virtual environment mapintel_work/dlvenv gets numpy and a CUDA build of torch (CUDA 12.8, else 12.9, else 13.0: all have RTX 50
# kernels); the script runs a small computation on the GPU and stops with an error if the GPU does not work, instead of using the CPU.
# Input: experiments/results/mapintel/dl_data/dataset.npz (committed). Output: mapintel_dl_<UTC stamp>.tar.gz in the repository root
# (.part01, .part02 ... when over 20 MB): upload it. Nothing else in the repository changes.
set -e
cd "$(dirname "$0")/../../.."
CPU=0
DEV=0
ARGS=()
for a in "$@"; do
	case "$a" in
		--cpu) CPU=1 ;;
		--device|--device=*) DEV=1; ARGS+=("$a") ;;
		*) ARGS+=("$a") ;;
	esac
done
[ "$(uname -s)" = "Darwin" ] && CPU=1
PY=""
for c in "${PYTHON:-}" python3 python "py -3.12" "py -3.13" "py -3.11" "py -3"; do
	[ -n "$c" ] || continue
	if $c -c "import sys, struct; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) and struct.calcsize('P') == 8 else 1)" > /dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
	echo "ERROR: no 64-bit Python 3.10-3.13 found (tried \$PYTHON, python3, python, py -3.12, py -3.13, py -3.11, py -3)." >&2
	echo "       Install Python 3.12 from python.org (tick 'Add python.exe to PATH'), or run: PYTHON=\"py -3.12\" bash $0 $*" >&2
	exit 1
fi
echo "python: $PY ($($PY -c 'import sys; print(sys.version.split()[0])'))"
[ -f experiments/results/mapintel/dl_data/dataset.npz ] || { echo "ERROR: experiments/results/mapintel/dl_data/dataset.npz is missing: git pull" >&2; exit 1; }
if [ "$CPU" = 0 ]; then
	if command -v nvidia-smi > /dev/null 2>&1; then
		nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || true
	else
		echo "WARNING: nvidia-smi not found on PATH (it is usually in C:\\Windows\\System32 with the NVIDIA driver); continuing" >&2
	fi
fi
VENV=mapintel_work/dlvenv
if [ ! -d "$VENV" ]; then
	echo "creating $VENV"
	mkdir -p mapintel_work
	$PY -m venv "$VENV" || { echo "ERROR: python -m venv failed (Debian / Ubuntu: sudo apt install python3-venv)" >&2; exit 1; }
fi
if [ -x "$VENV/Scripts/python.exe" ]; then VPY="$VENV/Scripts/python.exe"; else VPY="$VENV/bin/python"; fi
[ -x "$VPY" ] || { echo "ERROR: no python in $VENV (delete the folder $VENV and rerun)" >&2; exit 1; }
"$VPY" -c "import numpy" > /dev/null 2>&1 || {
	echo "installing numpy into $VENV"
	"$VPY" -m pip install -q --upgrade pip
	"$VPY" -m pip install -q numpy || { echo "ERROR: pip install numpy failed" >&2; exit 1; }
}
gpu_ok() {
	"$VPY" -c "import sys, torch; ok = torch.cuda.is_available() and float((torch.ones(256, device='cuda') @ torch.ones(256, device='cuda')).item()) == 256.0; sys.exit(0 if ok else 1)" > /dev/null 2>&1
}
if [ "$CPU" = 1 ]; then
	"$VPY" -c "import torch" > /dev/null 2>&1 || {
		echo "installing torch (CPU build)"
		if [ "$(uname -s)" = "Darwin" ]; then "$VPY" -m pip install -q torch; else "$VPY" -m pip install -q torch --index-url https://download.pytorch.org/whl/cpu; fi
	} || { echo "ERROR: pip install torch failed" >&2; exit 1; }
elif ! gpu_ok; then
	# no torch yet, or a CPU-only torch, or one without RTX 50 kernels: install a CUDA build (about 2.5-3 GB download, once)
	for cu in cu128 cu129 cu130; do
		echo "installing torch for CUDA (${cu}): about 3 GB, once"
		"$VPY" -m pip uninstall -y -q torch > /dev/null 2>&1 || true
		if "$VPY" -m pip install -q torch --index-url "https://download.pytorch.org/whl/${cu}" && gpu_ok; then break; fi
		echo "  torch from ${cu} does not run on this GPU / driver; trying the next CUDA version" >&2
	done
	if ! gpu_ok; then
		"$VPY" -c "import torch; print('torch', torch.__version__, 'CUDA', torch.version.cuda, 'available', torch.cuda.is_available())" 2>&1 || true
		echo "ERROR: torch cannot use the NVIDIA GPU. Check: (1) nvidia-smi works and shows driver 570 or newer (update the driver from" >&2
		echo "       nvidia.com: GeForce Game Ready / Studio driver for the RTX 5070 Laptop GPU); (2) on a laptop, plug in the charger and set" >&2
		echo "       Windows Graphics settings / NVIDIA Control Panel to 'High performance' for python.exe; (3) delete $VENV and rerun." >&2
		echo "       Or run without the GPU (slow): bash $0 --cpu ${ARGS[*]}" >&2
		exit 1
	fi
fi
"$VPY" -c "import torch; g = torch.cuda.is_available(); print('torch', torch.__version__, '| CUDA', torch.version.cuda, '|', (torch.cuda.get_device_name(0) + ', %.1f GB' % (torch.cuda.get_device_properties(0).total_memory / 2 ** 30)) if g else 'CPU')"
[ "$CPU" = 0 ] && [ "$DEV" = 0 ] && ARGS+=("--device" "cuda")
STAMP=$(date -u +%Y%m%d_%H%M)
OUT=mapintel_work/dl_model_$STAMP
export PYTHONIOENCODING=utf-8
"$VPY" -I tools/mapintel/dl/dl_train.py --out "$OUT" --archive "mapintel_dl_$STAMP.tar.gz" ${ARGS[@]+"${ARGS[@]}"}
echo
echo "done: upload mapintel_dl_$STAMP.tar.gz (or all its .partNN files) in the chat. The report is $OUT/report.md."
