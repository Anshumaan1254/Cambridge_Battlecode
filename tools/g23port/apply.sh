#!/bin/bash
# Rebase the GOD v23 modules (g23.cpp + hooks) onto another v84-lineage bot:  tools/g23port/apply.sh <base_bot_dir_name> <new_bot_dir_name>
# Copies bots/<base>/src to bots/<new>/src, copies g23.cpp, applies the three hook patches with fuzz; prints rejects to fix by hand.
set -e
cd "$(dirname "$0")/../.."
BASE=$1; NEW=$2
rm -rf bots/$NEW && mkdir -p bots/$NEW && cp -r bots/$BASE/src bots/$NEW/src
cp tools/g23port/g23.cpp bots/$NEW/src/g23.cpp
cd bots/$NEW/src
for f in brain.cpp brain.h params.h comms.cpp nav.cpp nav.h; do
  sed "s#god84/src/$f#$f#; s#god85/src/$f#$f#" ../../../tools/g23port/$f.patch | patch --fuzz=3 -p0 $f || echo "REJECTS in $f: see $f.rej"
done
