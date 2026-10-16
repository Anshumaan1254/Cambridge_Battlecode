#!/bin/bash
# usage: tools/snapshot.sh NAME [GIT_REF]   -> bots/NAME = bots/legend at GIT_REF (default HEAD)
set -e
name=$1; ref=${2:-HEAD}
rm -rf bots/$name && mkdir -p bots/$name/src
git archive "$ref" bots/legend/src | tar -x --strip-components=3 -C bots/$name/src
cp bots/legend/.gitignore bots/$name/
echo "bots/$name = legend@$(git rev-parse --short $ref)"
