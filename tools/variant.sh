#!/bin/bash
# usage: tools/variant.sh NAME [KEY=VALUE ...] [--define MACRO]...
# Copies bots/legend to bots/NAME, overriding Params fields (params.h defaults) and adding #defines.
set -e
name=$1; shift
src=${SRC:-bots/legend}
rm -rf bots/$name && mkdir -p bots/$name && cp -r $src/src bots/$name/ && cp bots/legend/.gitignore bots/$name/
defs=""
while [ $# -gt 0 ]; do
  if [ "$1" = "--define" ]; then defs="$defs#define $2\n"; shift 2; continue; fi
  key=${1%%=*}; val=${1#*=}
  if ! grep -q "^\s*[a-z]* $key = " bots/$name/src/params.h; then echo "unknown param $key" >&2; exit 1; fi
  sed -i -E "s/^(\s*[a-z]+ $key = )[^;]*;/\1$val;/" bots/$name/src/params.h
  shift
done
if [ -n "$defs" ]; then printf "$defs" | cat - bots/$name/src/params.h > bots/$name/src/params.tmp && mv bots/$name/src/params.tmp bots/$name/src/params.h; fi
echo "bots/$name ready"
