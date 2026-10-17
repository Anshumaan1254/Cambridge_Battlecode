#!/bin/bash
# usage: tools/variant.sh NAME [KEY=VALUE ...] [--define MACRO]...
# Copies bots/legend to bots/NAME, overriding Params fields (params.h defaults) and adding #defines.
# Portable (Linux and macOS): the substitution is done in python3, not GNU `sed -i`.
set -e
name=$1; shift
src=${SRC:-bots/legend}
rm -rf bots/$name && mkdir -p bots/$name && cp -r $src/src bots/$name/ && cp bots/legend/.gitignore bots/$name/
defs=""
while [ $# -gt 0 ]; do
  if [ "$1" = "--define" ]; then defs="$defs#define $2\n"; shift 2; continue; fi
  key=${1%%=*}; val=${1#*=}
  python3 - "bots/$name/src/params.h" "$key" "$val" <<'EOF'
import re, sys
path, key, val = sys.argv[1:]
src = open(path).read()
src, n = re.subn(r'^(\s*[a-z]+ ' + re.escape(key) + r' = )[^;]*;', lambda m: m.group(1) + val + ';', src, flags=re.M)
if n != 1:
    sys.exit(f'unknown param {key}')
open(path, 'w').write(src)
EOF
  shift
done
if [ -n "$defs" ]; then printf "%b" "$defs" | cat - bots/$name/src/params.h > bots/$name/src/params.tmp && mv bots/$name/src/params.tmp bots/$name/src/params.h; fi
echo "bots/$name ready"
