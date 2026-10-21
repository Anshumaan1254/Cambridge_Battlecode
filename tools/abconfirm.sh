#!/bin/bash
# tools/abconfirm.sh CAND [OPP=_v8k1] [KEEP_DIR]
# The A/B protocol of experiments/pools/README.md: CAND vs OPP on the held-out half (test152) and then on all 308 distinct maps,
# both sides (the train half's rows are reused when they exist on CAND's current code). Prints the cell of each pool (win rate,
# 95% Wilson interval, maps 2-0 / 1-1 / 0-2, sign test) and the full pool by map folder.
set -e
cd "$(dirname "$0")/.."
C=$1 O=${2:-_v8k1} K=${3:-}
KEEP=${K:+--keep $K}
for pool in test152 train156; do
	python3 tools/ledger.py run $C $O --maps "$(cat experiments/pools/$pool.csv)" --jobs 4 --chunk 16 $KEEP | tail -1
done
for pool in test152 train156 all308; do
	echo "== $pool"
	python3 tools/abstat.py $C $O --pool experiments/pools/$pool.csv
done
python3 tools/abstat.py $C $O --pool experiments/pools/all308.csv --by-dir | tail -n +2
