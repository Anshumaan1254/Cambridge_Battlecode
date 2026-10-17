#!/usr/bin/env bash
# Offline reinforcement learning (evolution strategies) for bots/legend, to run on your own machine.
#
# One command does everything: prerequisites, SDK, sparring opponents, a frozen copy of the current bot as a
# self-play opponent, the ES training run (tools/rl/es_train.py), a validation panel of the learned parameters,
# and a results archive to send back (rl_results_<date>_<commit>.tar.gz in the repo root).
#
#   git pull                                    # train the latest pushed bot
#   tools/rl/train_local.sh                     # defaults: 16 generations, 4 antithetic pairs, all CPUs
#   tools/rl/train_local.sh --gens 24 --jobs 6  # longer run, leave 2 cores free
#   tools/rl/train_local.sh --resume            # continue an interrupted run (keeps tune_out/es/history.json)
#   tools/rl/train_local.sh --validate-only     # only re-run the validation panel and re-pack the results
#
# Runs on Linux and macOS (on Windows use WSL). Needs git, python3 (numpy is installed if missing) and network
# access for `pip install cambc` and the first `cambc build` (it downloads the wasm toolchain once).
# Safe to stop with Ctrl-C and restart with --resume: every finished generation is saved.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"

GENS=16
POP=4
MPG=8
JOBS=""
RESUME=0
VALIDATE_ONLY=0
SKIP_SETUP=0
OPPS="_v6,_hunt,_hunt2,_devci,_r2,_self"
MAPS="maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a,maps/gold/*.map26a"
CAMBC_VERSION="2.2.5"

while [ $# -gt 0 ]; do
	case "$1" in
		--gens) GENS=$2; shift 2 ;;
		--pop) POP=$2; shift 2 ;;
		--maps-per-gen) MPG=$2; shift 2 ;;
		--jobs) JOBS=$2; shift 2 ;;
		--opponents) OPPS=$2; shift 2 ;;
		--maps) MAPS=$2; shift 2 ;;
		--resume) RESUME=1; shift ;;
		--validate-only) VALIDATE_ONLY=1; shift ;;
		--skip-setup) SKIP_SETUP=1; shift ;;
		-h|--help) sed -n 2,17p "$0"; exit 0 ;;
		*) echo "unknown option $1 (see --help)" >&2; exit 1 ;;
	esac
done

# pip --user installs scripts in ~/.local/bin (Linux) or ~/Library/Python/<version>/bin (macOS).
export PATH="$HOME/.local/bin:$(python3 -m site --user-base 2>/dev/null)/bin:$PATH"

if [ -z "$JOBS" ]; then
	JOBS=$( (nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4) | head -1)
fi
OUT=tune_out/es
mkdir -p "$OUT"
LOG="$OUT/console.txt"
say() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

# ---------------------------------------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------------------------------------
if [ "$SKIP_SETUP" = 0 ]; then
	say "step 1/7: prerequisites"
	command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
	command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
	python3 -c "import numpy" 2>/dev/null || python3 -m pip install --user numpy
	if ! command -v cambc >/dev/null; then
		python3 -m pip install --user "cambc==$CAMBC_VERSION"
	fi
	have=$(cambc --version | awk '{print $2}')
	if [ "$have" != "$CAMBC_VERSION" ]; then
		say "warning: cambc $have installed, the bot was last verified on $CAMBC_VERSION (pip install --user cambc==$CAMBC_VERSION to match)"
	fi

	# -----------------------------------------------------------------------------------------------------
	# 2. SDK and the current official maps
	# -----------------------------------------------------------------------------------------------------
	say "step 2/7: SDK (cambc init) and official maps"
	if [ ! -f sdk/cpp/cambc.h ]; then
		echo cpp | cambc init . --yes || true
	fi
	[ -f sdk/cpp/cambc.h ] || { echo "cambc init did not create sdk/cpp; run 'cambc init .' and choose C++" >&2; exit 1; }
	# The official pool is downloaded into maps/ (maps the repo does not have yet are packed into the results,
	# so the next round of work can test on them). Offline is fine: training then uses the committed maps.
	cambc maps pull 2>&1 | tail -2 || say "maps pull failed (offline?): training on the committed maps only"

	# -----------------------------------------------------------------------------------------------------
	# 3. Opponents: the sparring panel, plus a frozen copy of the bot being trained (self-play)
	# -----------------------------------------------------------------------------------------------------
	say "step 3/7: sparring opponents"
	tools/make_sparring.sh
	rm -rf bots/_self && mkdir -p bots/_self && cp -r bots/legend/src bots/_self/ && cp bots/legend/.gitignore bots/_self/
	cambc build _self >/dev/null
	say "built _self (frozen copy of bots/legend)"

	# -----------------------------------------------------------------------------------------------------
	# 4. Build and smoke-test the bot
	# -----------------------------------------------------------------------------------------------------
	say "step 4/7: build and smoke test"
	cambc build legend >/dev/null
	smoke_map=$(ls maps/ladder/*.map26a | head -1)
	mkdir -p "$OUT/smoke"
	t0=$(date +%s)
	cambc run legend _v6 --map "$smoke_map" --rounds 300 -o "$OUT/smoke" >"$OUT/smoke/run.txt" 2>&1 || { cat "$OUT/smoke/run.txt"; echo "smoke game failed" >&2; exit 1; }
	say "smoke game ok ($(( $(date +%s) - t0 ))s for 300 rounds)"
fi

COMMIT=$(git rev-parse --short HEAD)
DIRTY=$(git status --porcelain -- bots/legend/src | wc -l | tr -d ' ')
{
	echo "commit $COMMIT (uncommitted files in bots/legend/src: $DIRTY)"
	echo "branch $(git rev-parse --abbrev-ref HEAD)"
	echo "$(cambc --version 2>/dev/null)"
	echo "host $(uname -a)"
	echo "cpus $JOBS"
	echo "args gens=$GENS pop=$POP maps_per_gen=$MPG opponents=$OPPS maps=$MAPS resume=$RESUME"
	echo "started $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} > "$OUT/meta.txt"

# -------------------------------------------------------------------------------------------------------------
# 5. Training
# -------------------------------------------------------------------------------------------------------------
if [ "$VALIDATE_ONLY" = 0 ]; then
	n_maps=$(python3 -c "import glob,os,sys;print(len({m for p in sys.argv[1].split(',') for m in glob.glob(p) if not os.path.basename(m).startswith('zz_')}))" "$MAPS")
	n_opp=$(echo "$OPPS" | tr ',' '\n' | grep -c .)
	games=$(( (2 * POP + 1) * MPG * n_opp * 2 ))
	say "step 5/7: ES training, $GENS generations x $games games ($n_maps maps in the pool, $n_opp opponents, $JOBS parallel games)"
	say "         progress: tail -f $OUT/log.txt   (one line per generation; ~1-3 s per game per core)"
	extra=""
	[ "$RESUME" = 1 ] && extra="--resume"
	if [ "$RESUME" = 0 ] && [ -f "$OUT/history.json" ]; then
		stamp=$(date '+%Y%m%d_%H%M%S')
		mkdir -p "$OUT/previous_$stamp"
		mv "$OUT"/history.json "$OUT"/best_params.json "$OUT"/best_meta.json "$OUT"/latest_params.json "$OUT"/log.txt "$OUT/previous_$stamp/" 2>/dev/null || true
		say "previous run moved to $OUT/previous_$stamp (use --resume to continue it instead)"
	fi
	python3 tools/rl/es_train.py --space tools/rl/space.json --opponents "$OPPS" --maps "$MAPS" \
		--gens "$GENS" --pop "$POP" --maps-per-gen "$MPG" --jobs "$JOBS" $extra 2>&1 | tee -a "$LOG"
fi

# -------------------------------------------------------------------------------------------------------------
# 6. Validation: the learned parameters vs the untrained bot and the panel, on every map, both sides.
#    Each ES generation sees only 8 maps, so its reward moves with the sample; this fixed panel is what counts.
# -------------------------------------------------------------------------------------------------------------
[ -f "$OUT/best_params.json" ] || { echo "no $OUT/best_params.json: training did not finish a generation" >&2; exit 1; }
# Only best_params.json (the evaluated vector with the highest training reward) is validated here. latest_params.json
# (the final updated theta, never played in training) is not: validating it too would double this step (2-7 min more).
# To check it by hand: cp -r bots/legend bots/_es_latest && python3 tools/rl/apply_params.py $OUT/latest_params.json --bot _es_latest
say "step 6/7: validation panel of best_params.json (this takes a while: 90+ games per opponent)"
rm -rf bots/_es_best && mkdir -p bots/_es_best && cp -r bots/legend/src bots/_es_best/ && cp bots/legend/.gitignore bots/_es_best/
python3 - "$OUT/best_params.json" bots/_es_best/src/params.h <<'EOF'
import json, re, sys
vals = json.load(open(sys.argv[1])); path = sys.argv[2]; src = open(path).read()
for k, v in vals.items():
    src, n = re.subn(r'^(\s*\w+ ' + re.escape(k) + r' = )[^;]*;', lambda m: m.group(1) + str(v) + ';', src, flags=re.M)
    if n != 1:
        print(f'skip {k}: not in params.h')
open(path, 'w').write(src)
EOF
cambc build _es_best >/dev/null
VAL="$OUT/validation.txt"
: > "$VAL"
for o in $(echo "$OPPS" | tr ',' ' '); do
	python3 tools/bench.py _es_best "$o" --maps "$MAPS" --jobs "$JOBS" --out "$OUT/validate" --quiet --release 2>>"$LOG" | grep '^==' | tee -a "$VAL" || true
done
rm -rf "$OUT/validate"

# -------------------------------------------------------------------------------------------------------------
# 7. Results archive: send this file back
# -------------------------------------------------------------------------------------------------------------
echo "finished $(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$OUT/meta.txt"
new_maps=$(git ls-files --others --exclude-standard -- 'maps/*.map26a' 2>/dev/null || true)
ARCHIVE="rl_results_$(date '+%Y%m%d_%H%M')_$COMMIT.tar.gz"
files="$OUT/meta.txt $OUT/console.txt $OUT/validation.txt"
for f in log.txt history.json best_params.json best_meta.json latest_params.json; do [ -f "$OUT/$f" ] && files="$files $OUT/$f"; done
# shellcheck disable=SC2086
tar czf "$ARCHIVE" $files $new_maps
say "step 7/7: done. Send back: $ROOT/$ARCHIVE"
[ -n "$new_maps" ] && say "         (it also contains $(echo "$new_maps" | wc -l | tr -d ' ') official maps the repo does not have yet)"
cat "$VAL"
