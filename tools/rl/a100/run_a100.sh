#!/usr/bin/env bash
# One-command RL training of bots/legend on a Lightning AI A100 studio (or any Linux machine with many cores).
#
#   git clone -b ccr-a858cd03-q87cpi https://github.com/Akshayg005/Cambridge_Battlecode.git && cd Cambridge_Battlecode
#   bash tools/rl/a100/run_a100.sh                 # 2.5 h of training + tournament, then validation and the archive
#   bash tools/rl/a100/run_a100.sh --hours 3       # longer
#   bash tools/rl/a100/run_a100.sh --resume        # continue after an interruption (keeps tune_out/a100/)
#   bash tools/rl/a100/run_a100.sh --skip-setup    # opponents already built
#
# What it does: prerequisites, SDK, every opponent (our frozen builds, the sparring panel and the four ladder-team
# archetypes _eA.._eD from tools/make_archetypes.sh), smoke test, the trainer (tools/rl/a100/es_a100.py: evolution
# strategies over params.h with a GPU-trained surrogate and a final tournament), a validation bench of the winner on
# the 17 official maps, and rl_a100_results_<date>_<commit>.tar.gz in the repo root: send that file back.
# The games run on the CPUs (all cores are used); the GPU trains the surrogate model. Everything is resumable.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$ROOT"
HOURS=2.5
JOBS=""
RESUME=0
SKIP_SETUP=0
EXTRA=()
CAMBC_VERSION="2.2.5"
while [ $# -gt 0 ]; do
	case "$1" in
		--hours) HOURS=$2; shift 2 ;;
		--jobs) JOBS=$2; shift 2 ;;
		--resume) RESUME=1; EXTRA+=(--resume); shift ;;
		--skip-setup) SKIP_SETUP=1; shift ;;
		--pop) EXTRA+=(--pop "$2"); shift 2 ;;
		-h|--help) sed -n 2,16p "$0"; exit 0 ;;
		*) echo "unknown option $1 (see --help)" >&2; exit 1 ;;
	esac
done
export PATH="$HOME/.local/bin:$PATH"
[ -n "$JOBS" ] || JOBS=$(nproc)
OUT=tune_out/a100
mkdir -p "$OUT"
LOG="$OUT/console.txt"
say() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

if [ "$SKIP_SETUP" = 0 ]; then
	say "step 1/6: prerequisites"
	command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
	python3 -c "import numpy" 2>/dev/null || python3 -m pip install --user numpy
	if ! python3 -c "import torch" 2>/dev/null; then
		say "torch not found: installing it (the surrogate falls back to a CPU ridge model if this fails)"
		python3 -m pip install --user torch || say "torch install failed: continuing with the ridge surrogate"
	fi
	python3 -c "import torch;print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')" 2>/dev/null | tee -a "$LOG" || true
	command -v cambc >/dev/null || python3 -m pip install --user "cambc==$CAMBC_VERSION"
	have=$(cambc --version | awk '{print $2}')
	[ "$have" = "$CAMBC_VERSION" ] || say "warning: cambc $have installed, the bot is verified on $CAMBC_VERSION (pip install --user cambc==$CAMBC_VERSION)"

	say "step 2/6: SDK and maps"
	[ -f sdk/cpp/cambc.h ] || (echo cpp | cambc init . --yes) || true
	[ -f sdk/cpp/cambc.h ] || { echo "cambc init did not create sdk/cpp; run 'cambc init .' and choose C++" >&2; exit 1; }
	cambc maps pull 2>&1 | tail -2 || say "maps pull failed (offline?): the committed maps are used"
	[ "$(git rev-parse --is-shallow-repository)" = "true" ] && git fetch --unshallow origin 2>&1 | tail -1 || true

	say "step 3/6: opponents (sparring panel, frozen builds, ladder archetypes, self)"
	tools/make_sparring.sh
	tools/snapshot.sh _L0 25bed8d
	for z in es2:legend_es2_20261017 c3:legend_c3_20261017 ST:legend_st_20261017 rm:legend_rm_20261018; do
		n=_${z%%:*}; f=submissions/history/${z#*:}.zip
		rm -rf "bots/$n" && mkdir -p "bots/$n" && (cd "bots/$n" && python3 -c "import zipfile,sys;zipfile.ZipFile(sys.argv[1]).extractall('.')" "../../$f") && cp bots/legend/.gitignore "bots/$n/"
	done
	tools/make_archetypes.sh
	rm -rf bots/_self && mkdir -p bots/_self && cp -r bots/legend/src bots/_self/ && cp bots/legend/.gitignore bots/_self/
	say "         release builds of every opponent ($JOBS cores)"
	opps="_base _v6 _r2 _hunt _hunt2 _devci _L0 _es2 _c3 _ST _rm _eA _eB _eC _eD _self idle legend"
	printf '%s\n' $opps | xargs -P "$(( JOBS / 2 > 0 ? JOBS / 2 : 1 ))" -I{} sh -c 'cambc build {} --release >/dev/null 2>&1 || echo "build {} failed"'

	say "step 4/6: smoke test"
	mkdir -p "$OUT/smoke"
	t0=$(date +%s)
	cambc run legend _eA --map maps/comp/rows.map26a --rounds 300 -o "$OUT/smoke" >"$OUT/smoke/run.txt" 2>&1 || { cat "$OUT/smoke/run.txt"; echo "smoke game failed" >&2; exit 1; }
	say "         smoke game ok ($(( $(date +%s) - t0 ))s for 300 rounds)"
fi

COMMIT=$(git rev-parse --short HEAD)
{
	echo "commit $COMMIT branch $(git rev-parse --abbrev-ref HEAD) (uncommitted in bots/legend/src: $(git status --porcelain -- bots/legend/src | wc -l))"
	cambc --version
	echo "host $(uname -a)"
	echo "cpus $(nproc), jobs $JOBS, mem $(free -g 2>/dev/null | awk '/Mem/{print $2" GB"}')"
	nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "no nvidia-smi"
	echo "hours $HOURS resume $RESUME extra ${EXTRA[*]:-}"
	echo "started $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} > "$OUT/meta.txt"
cat "$OUT/meta.txt" | tee -a "$LOG"

say "step 5/6: training ($HOURS h incl. the final tournament; progress: tail -f $OUT/log.txt)"
python3 tools/rl/a100/es_a100.py --hours "$HOURS" --jobs "$JOBS" "${EXTRA[@]}" 2>&1 | tee -a "$LOG"

say "step 6/6: validation of best_params.json on the 17 official maps, both sides"
[ -f "$OUT/best_params.json" ] || { echo "no $OUT/best_params.json: the run did not reach the tournament" >&2; exit 1; }
rm -rf bots/_a100_best && mkdir -p bots/_a100_best && cp -r bots/legend/src bots/_a100_best/ && cp bots/legend/.gitignore bots/_a100_best/
python3 tools/rl/apply_params.py "$OUT/best_params.json" --bot _a100_best | tail -3
cambc build _a100_best --release >/dev/null
VAL="$OUT/validation.txt"
: > "$VAL"
for o in _eA _eB _eC _eD _ST _rm _self; do
	python3 tools/bench.py _a100_best "$o" --maps 'maps/comp/*.map26a' --jobs "$JOBS" --out "$OUT/validate" --quiet --release 2>>"$LOG" | grep '^==' | tee -a "$VAL" || true
done
python3 tools/bench.py _a100_best idle --maps 'maps/comp/*.map26a' --jobs "$JOBS" --out "$OUT/validate" --quiet --release 2>>"$LOG" | grep '^==' | tee -a "$VAL" || true
rm -rf "$OUT/validate"

echo "finished $(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$OUT/meta.txt"
ARCHIVE="rl_a100_results_$(date '+%Y%m%d_%H%M')_$COMMIT.tar.gz"
files=""
for f in meta.txt console.txt log.txt history.json state.json dataset.npz tournament.json best_params.json best_meta.json latest_params.json surrogate_report.txt validation.txt; do
	[ -f "$OUT/$f" ] && files="$files $OUT/$f"
done
new_maps=$(git ls-files --others --exclude-standard -- 'maps/*.map26a' 2>/dev/null || true)
# shellcheck disable=SC2086
tar czf "$ARCHIVE" $files $new_maps
say "done. Send back: $ROOT/$ARCHIVE"
cat "$VAL"
