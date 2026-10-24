#!/usr/bin/env bash
# Fetch recent ranked match lists for the top N teams of experiments/live/top40.tsv.
# Usage: tools/live/fetch_top.sh [N=20] [MAX=300]
N=${1:-20}; MAX=${2:-300}
cd "$(dirname "$0")/../.." || exit 1
export PYTHONIOENCODING=utf-8
mkdir -p experiments/live/lists
head -n "$N" experiments/live/top40.tsv | while IFS=$'\t' read -r rank id name rating; do
  python tools/live/fetch_matches.py --team "$id" --kind ranked --max "$MAX" --out "experiments/live/lists/r$(printf %02d "$rank")_${id:0:8}.jsonl" | sed "s/^/[$rank $name] /"
  sleep 1
done
echo ALL_DONE
