#!/bin/bash
# tools/draftcheck.sh BOT OPP 'MAP_GLOBS' : BOT (side A) vs OPP on each map for 1 round; prints both drafts per map (no result).
set -e
cd "$(dirname "$0")/.."
BOT=$1 OPP=$2 MAPS=$3
OUT=$(mktemp -d)
cambc build $BOT > /dev/null && cambc build $OPP > /dev/null
for p in ${MAPS//,/ }; do for m in $p; do n=$(basename $m .map26a); echo "$PWD/bots/$BOT $PWD/bots/$OPP $PWD/$m $OUT/$n.repl26a"; done; done > $OUT/manifest.txt
cambc run-batch $OUT/manifest.txt --jobs 4 --rounds 1 --color never > /dev/null 2>&1 || true
node tools/draftcheck.mjs $(find $OUT -name '*.repl26a' -size +0 | sort)
rm -rf $OUT
