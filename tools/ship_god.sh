#!/bin/bash
# Ship a measured candidate as the GOD submission: copy its sources into bots/god, rebuild, verify the wasm is byte-identical to
# the candidate's (the ledger rows were played with that wasm), bundle submissions/god.zip and the history copy.
#   tools/ship_god.sh CANDIDATE VERSION      e.g. tools/ship_god.sh _g6m v6
set -e
cd "$(dirname "$0")/.."
cand=$1; ver=$2
[ -d "bots/$cand/src" ] || { echo "no bots/$cand/src"; exit 1; }
cp bots/$cand/src/*.cpp bots/$cand/src/*.h bots/god/src/
rm -rf bots/god/.cambc bots/god/compile_commands.json && cambc build god > /dev/null # clean build: a stale build dir gave a different wasm from identical sources (session 14)
a=$(sha256sum bots/$cand/.cambc/build/bot.wasm | cut -c1-16); b=$(sha256sum bots/god/.cambc/build/bot.wasm | cut -c1-16)
[ "$a" = "$b" ] || { echo "wasm differs: $cand $a god $b"; exit 1; }
rm -f submissions/god.zip && cambc bundle god --output submissions/god.zip > /dev/null
cp submissions/god.zip submissions/history/god_${ver}_$(date -u +%Y%m%d).zip
python3 - <<PY
import hashlib,glob
h=hashlib.sha256()
for f in sorted(glob.glob('bots/god/src/*')): h.update(open(f,'rb').read())
print('source hash', h.hexdigest()[:12])
PY
echo "zip sha256 $(sha256sum submissions/god.zip | cut -c1-16) wasm $b"
