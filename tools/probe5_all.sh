#!/bin/bash
# Re-runs every Session 5 engine probe (experiments/wip/x_probe/*) one game at a time and prints the key log lines.
# usage: tools/probe5_all.sh [s1 s1b s2 s2c s3 s5 s6 s6b]   (default: all). Output: /tmp/probe5/<name>/{team-a,team-b}.stdout, decoded.json
set -e
cd "$(dirname "$0")/.."
D=experiments/wip/x_probe; B=bots/_x_probe/src
mkdir -p bots/_x_probe/src /tmp/probe5; cp bots/probe-rules/.gitignore bots/_x_probe/ 2>/dev/null || true
[ -f maps/probe5/p5.map26a ] || node tools/mapgen/probe5map.mjs
[ -f maps/probe5/p6.map26a ] || node tools/mapgen/probe5map_big.mjs
DR='bc::champion_draft::vendetta, bc::champion_draft::tavi, bc::champion_draft::ryth, bc::champion_draft::stellar, bc::champion_draft::vesper_vale'
DR3='bc::champion_draft::vendetta, bc::champion_draft::ryth, bc::champion_draft::tavi, bc::champion_draft::stellar, bc::champion_draft::vesper_vale'
DR6='bc::champion_draft::vendetta, bc::champion_draft::ryth, bc::champion_draft::vesper_vale, bc::champion_draft::tavi, bc::champion_draft::stellar'
run() { # name body.h rounds draft "defines" map
	cp $D/main.cpp $B/main.cpp; cp $D/$2 $B/scen_body.h
	printf '%b\n#define SCEN 1\n#define SCEN_DRAFT %s\n' "$5" "$4" > $B/scen.h
	MAP=$6 tools/probe5_run.sh $1 $3 | tail -1
}
want=${*:-s1 s1b s2 s2c s3 s5 s6 s6b}
for n in $want; do case $n in
 s1)  run s1  s1_stun.h 90 "$DR" "" maps/probe5/p5.map26a ;;
 s1b) run s1b s1_stun.h 75 "$DR" "#define S1_ATTACK 1" maps/probe5/p5.map26a ;;
 s2)  run s2  s2_lock.h 75 "$DR" "" maps/probe5/p5.map26a ;;
 s2c) run s2c s2_lock.h 75 "$DR" "#define S2C 1" maps/probe5/p5.map26a ;;
 s3)  run s3  s3_concurrent.h 90 "$DR3" "" maps/probe5/p5.map26a ;;
 s5)  run s5  s5_home.h 140 "$DR3" "" maps/probe5/p5.map26a ;;
 s6)  run s6  s6_race.h 330 "$DR6" "#define MAPW 31" maps/probe5/p6.map26a ;;
 s6b) run s6b s6_race.h 330 "$DR6" "#define MAPW 31\n#define BD 1" maps/probe5/p6.map26a ;;
esac; done
