#!/bin/bash
# usage: tools/probe5_run.sh NAME ROUNDS   (bot bots/_x_probe, map maps/probe5/p5.map26a; scenario from bots/_x_probe/src/scen_body.h)
# Builds, runs one game, unpacks logs to /tmp/probe5/NAME/ (team-a.stdout, team-b.stdout, replay.repl26a) and decodes the replay to events.json.
set -e
cd "$(dirname "$0")/.."
name=$1; rounds=${2:-100}; map=${MAP:-maps/probe5/p5.map26a}
cambc build _x_probe > /tmp/probe5/build.log 2>&1 || { cat /tmp/probe5/build.log | grep -E "error" ; exit 1; }
rm -rf /tmp/probe5/$name; mkdir -p /tmp/probe5/$name/z
cambc run _x_probe _x_probe --map $map --rounds $rounds -o /tmp/probe5/$name/z > /tmp/probe5/$name/run.log 2>&1 || true
(cd /tmp/probe5/$name && unzip -oq z/*.repl26a && rm -rf z)
node tools/replay/decode.mjs /tmp/probe5/$name/replay.repl26a --out /tmp/probe5/$name/decoded.json 2>/dev/null || true
tail -3 /tmp/probe5/$name/run.log | grep -v agent
