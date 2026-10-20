#!/usr/bin/env python3
"""Decode ladder replay folders for the fight / danger model (agent ml2, session 13; ml4, session 14).

usage: python3 tools/ml/ml2_decode.py OUT_DIR SET=REPLAY_DIR [SET=REPLAY_DIR ...]

For every .repl26a in REPLAY_DIR writes OUT_DIR/SET/<stem>.json (decode_dmg.mjs, per-step damage) and adds the map
grid to OUT_DIR/SET/mapgeo.json (mapinfo.mjs dump: walls #, holes o, bushes ", altars A, spawns S). Already decoded
games are skipped, so the script can be re-run after a cut. No analysis tables (see tools/strategy_v2/run_all.py).
The map name (geo 'map') is looked up by the grid hash in maps/comp (old official files), maps/comp30 (patch-3.0
official files, *_v3), maps/nyx_new (the patch-3.0 maps of the Nyx games) and maps/loss_oct20; 'unknown' otherwise. The decoder picks
the newest engine in the cambc asset cache that accepts the replay (v1_0_0 for patch 3.0, v0_0_3 for the Oct 18-19 games).
"""
import glob
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'strategy_v2'))
from run_all import map_dump as _map_dump, parse_dump  # noqa: E402

DECODE = os.path.join(ROOT, 'tools', 'strategy_v2', 'decode_dmg.mjs')
MAP_DIRS = ('comp', 'comp30', 'nyx_new', 'loss_oct20')


def engine_wasms():
	"""The engines in the cambc asset cache, newest first (the same order as tools/replay/decode.mjs)."""
	root = os.environ.get('CAMBC_CACHE') or os.path.join(os.environ.get('HOME', '/root'), '.cache', 'cambc', 'assets')
	found = glob.glob(os.path.join(root, '*', 'visualiser', 'assets', 'v*_*_*-*.wasm')) + glob.glob(os.path.join(root, '*', 'mapeditor', 'assets', 'v*_*_*-*.wasm'))
	return sorted(found, key=lambda f: os.path.basename(f), reverse=True)


def map_dump(path):
	"""mapinfo.mjs picks the newest engine only; an older replay (patch 2.2.5) needs the engine of its format: retry down the list."""
	try:
		return _map_dump(path)
	except subprocess.CalledProcessError:
		pass
	for w in engine_wasms():
		try:
			return subprocess.run(['node', os.path.join(ROOT, 'tools', 'replay', 'mapinfo.mjs'), path], capture_output=True, text=True, check=True,
								  env=dict(os.environ, CAMBC_ENGINE_WASM=w)).stdout
		except subprocess.CalledProcessError:
			continue
	raise RuntimeError(f'no engine in the cambc asset cache decodes {path}')


def known_maps():
	res = {}
	for sub in MAP_DIRS:
		for f in sorted(glob.glob(os.path.join(ROOT, 'maps', sub, '*.map26a'))):
			lines = map_dump(f).splitlines()
			res.setdefault(hashlib.md5('\n'.join(lines[1:]).encode()).hexdigest(), os.path.basename(f)[:-7])
	return res


def main():
	out = os.path.abspath(sys.argv[1])
	off = known_maps()
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
			rel = os.path.relpath(path, ROOT)
			for old_stem in [k for k, v in geo.items() if v.get('file') == rel and k != stem]:
				del geo[old_stem]  # the same replay under an older name (a map dir added later): one entry per game
				old_json = os.path.join(od, old_stem + '.json')
				if os.path.exists(old_json):
					os.remove(old_json)
			geo[stem] = parse_dump(dump)
			geo[stem]['file'] = os.path.relpath(path, ROOT)
			geo[stem]['map'] = mp
			target = os.path.join(od, stem + '.json')
			if not os.path.exists(target):
				subprocess.run(['node', DECODE, path, '--out', target, '--rollovers'], check=True)
				print('decoded', name, stem, flush=True)
			json.dump(geo, open(gp, 'w'))


if __name__ == '__main__':
	main()
