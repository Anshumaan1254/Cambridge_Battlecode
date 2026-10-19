#!/usr/bin/env python3
"""Decode ladder replay folders for the fight / danger model (agent ml2, session 13).

usage: python3 tools/ml/ml2_decode.py OUT_DIR SET=REPLAY_DIR [SET=REPLAY_DIR ...]

For every .repl26a in REPLAY_DIR writes OUT_DIR/SET/<stem>.json (decode_dmg.mjs, per-step damage) and adds the map
grid to OUT_DIR/SET/mapgeo.json (mapinfo.mjs dump: walls #, holes o, bushes ", altars A, spawns S). Already decoded
games are skipped, so the script can be re-run after a cut. No analysis tables (see tools/strategy_v2/run_all.py).
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'strategy_v2'))
from run_all import map_dump, official_maps, parse_dump  # noqa: E402

DECODE = os.path.join(ROOT, 'tools', 'strategy_v2', 'decode_dmg.mjs')


def main():
	out = os.path.abspath(sys.argv[1])
	off = official_maps()
	for spec in sys.argv[2:]:
		name, src = spec.split('=', 1)
		od = os.path.join(out, name)
		os.makedirs(od, exist_ok=True)
		gp = os.path.join(od, 'mapgeo.json')
		geo = json.load(open(gp)) if os.path.exists(gp) else {}
		for f in sorted(os.listdir(src)):
			if not f.endswith('.repl26a'):
				continue
			path = os.path.join(src, f)
			label = f[:-8]
			dump = map_dump(path)
			h = hashlib.md5('\n'.join(dump.splitlines()[1:]).encode()).hexdigest()
			mp = off.get(h, 'unknown')
			stem = label if label.endswith(mp) else f'{label}_{mp}'
			geo[stem] = parse_dump(dump)
			geo[stem]['file'] = os.path.relpath(path, ROOT)
			target = os.path.join(od, stem + '.json')
			if not os.path.exists(target):
				subprocess.run(['node', DECODE, path, '--out', target, '--rollovers'], check=True)
				print('decoded', name, stem, flush=True)
			json.dump(geo, open(gp, 'w'))


if __name__ == '__main__':
	main()
