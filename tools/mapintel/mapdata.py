#!/usr/bin/env python3
"""Load a map as the engine shows it to a bot (the runtime dump of tools/mapintel/dump_maps.py) into numpy arrays. COMPUTED.

    from mapdata import load;  M = load("00elkring")      # experiments/results/mapintel/dump/00elkring.txt (+ .los.txt, .vis.txt)

Arrays are indexed [y, x] (x = column, y = row; the SDK's vec2 north is +y). Bitboards come from export_linear_buffer(): packed row-major,
least significant bit first, bit i = y * W + x (checked on the rules-probe map, where every tile is known). Team 0 = team A = the dump's
'ally' view, team 1 = team B.

Fields: name, W, H, sym (0 horizontal, 1 vertical, 2 rotational180), team_size, fingerprint, walls, holes, bushes, altars (bool [H, W]),
spawn[2] (bool [H, W]), altar_tiles (list of (x, y)), groups (list of dict: id, gems, gold, respawn, camps [(type, x, y)]), camp_list
(sorted (type, x, y), the fingerprint's order), camp_group (dict (x, y) -> group id), los (dict (x, y) -> set of camp tiles (x, y) visible
from there, for every standing tile within Chebyshev 5 of a camp), vis (dict (x, y) -> bool [H, W] engine vision of the sample tiles)."""
import os
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DUMP = os.path.join(ROOT, "experiments/results/mapintel/dump")
CAMP_TYPES = ["wolf", "elk", "gem_cluster", "gold_cluster", "monolith", "golem"]


def bits(hexs, W, H):
	b = np.frombuffer(bytes.fromhex(hexs), dtype=np.uint8)
	flat = np.unpackbits(b, bitorder="little")[: W * H]
	return flat.reshape(H, W).astype(bool)


class Map:
	pass


def load(name, dump=DUMP):
	M = Map()
	M.name = name
	M.groups, M.spawn_box = [], {}
	for line in open(os.path.join(dump, name + ".txt")):
		t = line.split()
		if t[:2] == ["MI", "fp"]:
			M.fingerprint, M.team_size, M.W, M.H, M.sym = t[2], int(t[4]), int(t[6]), int(t[8]), int(t[10])
		elif t[:2] == ["MI", "spawn"]:
			M.spawn_box[t[2]] = tuple(int(v) for v in t[3:8])
		elif t[:2] == ["MI", "bb"]:
			setattr(M, t[2], bits(t[3], M.W, M.H))
		elif t[:2] == ["MI", "G"]:
			head, *mem = line.strip().split(" | ")
			h = head.split()
			M.groups.append({"id": int(h[2]), "gems": int(h[4]), "gold": int(h[6]), "respawn": int(h[8]),
							 "camps": [tuple(int(v) for v in m.split()) for m in mem]})
	M.spawn = []
	for side in ("ally", "enemy"):  # the boxes are inclusive; the SDK fills its spawn bitboards from the engine's bounding box
		x0, y0, x1, y1, n = M.spawn_box[side]
		s = np.zeros((M.H, M.W), bool)
		s[y0:y1 + 1, x0:x1 + 1] = True
		if s.sum() != n:
			raise SystemExit(f"{name}: spawn {side} box {M.spawn_box[side]} has {s.sum()} tiles, the engine says {n}")
		M.spawn.append(s)
	M.altar_tiles = [(int(x), int(y)) for y, x in zip(*np.nonzero(M.altars))]
	M.camp_group = {(c[1], c[2]): g["id"] for g in M.groups for c in g["camps"]}
	M.camp_type = {(c[1], c[2]): c[0] for g in M.groups for c in g["camps"]}
	M.camp_list = sorted((c[0], c[1], c[2]) for g in M.groups for c in g["camps"])
	M.camps = np.zeros((M.H, M.W), bool)
	for _, x, y in M.camp_list:
		M.camps[y, x] = True
	M.los = {}
	p = os.path.join(dump, name + ".los.txt")
	if os.path.exists(p):
		for line in open(p):
			t = line.split()
			if t[:2] == ["MI", "los"]:
				M.los[(int(t[2]), int(t[3]))] = {(M.camp_list[int(i)][1], M.camp_list[int(i)][2]) for i in t[4:]}
	M.vis = {}
	p = os.path.join(dump, name + ".vis.txt")
	if os.path.exists(p):
		for line in open(p):
			t = line.split()
			if t[:2] == ["MI", "vis"]:
				M.vis[(int(t[2]), int(t[3]))] = bits(t[4], M.W, M.H)
	return M


def official_names():
	return sorted(f[:-4] for f in os.listdir(DUMP) if f.endswith(".txt") and f.count(".") == 1 and f != "fingerprints.txt")


if __name__ == "__main__":
	import sys
	M = load(sys.argv[1] if len(sys.argv) > 1 else "00elkring", sys.argv[2] if len(sys.argv) > 2 else DUMP)
	ch = {}
	for y in range(M.H - 1, -1, -1):  # north up
		row = ""
		for x in range(M.W):
			c = "#" if M.walls[y, x] else "o" if M.holes[y, x] else "A" if M.altars[y, x] else "a" if M.spawn[0][y, x] else "b" if M.spawn[1][y, x] else "."
			if (x, y) in M.camp_type:
				c = "wegGMK"[M.camp_type[(x, y)]]
			elif M.bushes[y, x] and c == ".":
				c = ","
			row += c
		print(row)
	print(M.name, M.W, M.H, "sym", M.sym, "team", M.team_size, "groups", len(M.groups), "altars", M.altar_tiles, "los tiles", len(M.los), "vis", len(M.vis))
