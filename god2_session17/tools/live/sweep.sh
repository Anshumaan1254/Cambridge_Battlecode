#!/usr/bin/env bash
# Pace sweep: tools/live/sweep.sh BASE "name:key=val key2=val2" ...   (variants of bots/BASE; pace tag = sw_<name>)
cd "$(dirname "$0")/../.." || exit 1
export PYTHONIOENCODING=utf-8
base=$1; shift
for spec in "$@"; do
  name=${spec%%:*}; kv=${spec#*:}
  SRC=bots/$base bash tools/variant.sh _sw_$name $kv >/dev/null || { echo "variant $name failed"; continue; }
  cambc build _sw_$name 2>&1 | grep -q "built" || { echo "build $name failed"; continue; }
  python tools/live/pace.py _sw_$name --tag sw_$name | tail -1
done
echo SWEEP_DONE
