#!/usr/bin/env python3
"""The NAV draft-memory block's static navigation hazards (docs/DRAFT_MEMORY.md 5.7): the Python twin of
tools/mapintel/cpp/mapintel/hazards.h (definitions in its header comment; bit-equal, checked by tools/mapintel/test_dmem2.py). COMPUTED.

    python3 -I tools/mapintel/hazards.py [--write-catalog] [--maps 00lanes,...]

prints per official map and team the counts, and with --write-catalog stores the blocks in maps/catalog/<map>.json ("nav": {team: hex})
for export_headers.py's known_maps.h."""
import argparse, json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compact as CP  # noqa: E402
import mapdata  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
NAV_SIZE, NAV_CHOKE, NAV_POCKET, NAV_HOLE, NAV_ANCHOR, NAV_GROUP_PATHS = 64, 8, 4, 8, 8, 3
NAV_HOLE_CAND, NAV_POCKET_CAND, NAV_HOLE_MIN_SAVING, NAV_POCKET_SPACING = 128, 256, 3, 5
NAV_PART_POCKET, NAV_PART_HOLE, NAV_SRC_DRAFT, NAV_SRC_TABLE = 16, 32, 1, 2
NAV_ALL_PARTS = 1 | 2 | 4 | 8 | NAV_PART_POCKET | NAV_PART_HOLE
DX = [0, 1, 1, 1, 0, -1, -1, -1]
DY = [-1, -1, 0, 1, 1, 1, 0, -1]


def nb(A, dx, dy):
	"""out[y, x] = A[y + dy, x + dx], False outside the map."""
	H, W = A.shape
	out = np.zeros_like(A)
	ys, ye = max(0, -dy), min(H, H - dy)
	xs, xe = max(0, -dx), min(W, W - dx)
	out[ys:ye, xs:xe] = A[ys + dy:ye + dy, xs + dx:xe + dx]
	return out


def dilate(A, r):
	B = A.copy()
	for _ in range(r):
		B = B | nb(B, 1, 0) | nb(B, -1, 0)
		B = B | nb(B, 0, 1) | nb(B, 0, -1)
	return B


def cut_tiles(P):
	n = [nb(P, DX[k], DY[k]) for k in range(8)]
	terms = [n[k] & ~n[(k + 6) & 7] for k in (0, 2, 4, 6)]
	terms += [n[k] & ~(n[k - 1] | n[(k + 1) & 7]) for k in (1, 3, 5, 7)]
	cnt = sum(t.astype(np.int32) for t in terms)
	return (cnt >= 2) & P


def tiles(mask):
	"""Set tiles in tile order (y * W + x ascending)."""
	ys, xs = np.nonzero(mask)
	return [(int(x), int(y)) for y, x in zip(ys, xs)]


def nav_block(M, team, anchor_groups, altars, parts=NAV_ALL_PARTS, C=None):
	"""The 64-byte NAV block for `team` (bytes 0-60; byte 61 = NAV_SRC_DRAFT). anchor_groups: up to 4 group indices; altars: up to 3
	altar indices (the bank order); parts: which parts the C++ computed (its byte 60), so a fuel-limited draft is reproduced."""
	C = C or CP.Compact(M, team)
	W, H = M.W, M.H
	P = C.C[team]
	f = C.fc[team]
	b = bytearray(NAV_SIZE)
	for k in range(28):
		b[2 * k] = b[2 * k + 1] = 0xFF
	put = lambda k, v: (b.__setitem__(2 * k, v & 0xFF), b.__setitem__(2 * k + 1, (v >> 8) & 0xFF))  # noqa: E731
	cut = cut_tiles(P)
	choke = []

	def trace(start):
		cur = start
		x, y = start % W, start // W
		prev = False
		for _ in range(W * H + 1):
			d = int(f[y, x])
			if d < 0:
				return None
			c = bool(cut[y, x])
			if c and not prev and len(choke) < NAV_CHOKE and cur not in choke:
				choke.append(cur)
			prev = c
			if d == 0:
				return cur
			nxt = None
			for k in range(8):
				nx, ny = x + DX[k], y + DY[k]
				if 0 <= nx < W and 0 <= ny < H and int(f[ny, nx]) == d - 1:
					nxt = (nx, ny)
					break
			if nxt is None:
				return None
			x, y = nxt
			cur = y * W + x
		return None

	got = 0
	spawn_end = None
	start, bd = None, None
	for (sy, sx) in sorted(zip(*np.nonzero(M.spawn[1 - team])), key=lambda t: t[0] * W + t[1]):
		for k in range(8):
			nx, ny = int(sx) + DX[k], int(sy) + DY[k]
			if 0 <= nx < W and 0 <= ny < H and f[ny, nx] >= 0:
				i, v = ny * W + nx, int(f[ny, nx])
				if bd is None or v < bd or (v == bd and i < start):
					bd, start = v, i
	if start is None:
		got |= 1
	elif parts & 1:
		spawn_end = trace(start)
		got |= 1
	for p in range(NAV_GROUP_PATHS):
		g = anchor_groups[p] if p < len(anchor_groups) else None
		t = C.near_tile(g) if g is not None and g >= 0 else -1
		if t < 0 or f[t // W, t % W] < 0:
			got |= 2 << p
			continue
		if not parts & (2 << p):
			continue
		trace(t)
		got |= 2 << p
	for i, t in enumerate(choke):
		put(i, t)
	reach = f >= 0
	npocket = 0
	if parts & NAV_PART_POCKET:
		pocket = P & ~reach
		entry = dilate(reach, 2) & pocket
		near = dilate(M.camps & pocket, 3)
		kept = []
		for e in (entry & near, entry & ~near):
			for (x, y) in tiles(e)[:NAV_POCKET_CAND]:
				if len(kept) >= NAV_POCKET:
					break
				if all(max(abs(x - kx), abs(y - ky)) >= NAV_POCKET_SPACING for kx, ky in kept):
					kept.append((x, y))
					put(8 + len(kept) - 1, y * W + x)
		npocket = len(kept)
		got |= NAV_PART_POCKET
	nhole = 0
	if parts & NAV_PART_HOLE:
		O = [(1, 0), (0, 1), (1, 1), (1, -1)]
		anyl = np.zeros_like(P)
		for ox, oy in O:
			anyl |= M.holes & nb(P, ox, oy) & nb(P, -ox, -oy)
		cand = []
		for (x, y) in tiles(anyl)[:NAV_HOLE_CAND]:
			best = -1
			for ox, oy in O:
				ax, ay, bx, by = x + ox, y + oy, x - ox, y - oy
				if not (0 <= ax < W and 0 <= ay < H and 0 <= bx < W and 0 <= by < H) or not (P[ay, ax] and P[by, bx]):
					continue
				fa, fb = int(f[ay, ax]), int(f[by, bx])
				if fa >= 0 and fb >= 0:
					sv = abs(fa - fb)
				elif fa >= 0 or fb >= 0:
					sv = 255
				else:
					continue
				best = max(best, min(sv, 255))
			if best >= NAV_HOLE_MIN_SAVING:
				cand.append((best, y * W + x))
		cand.sort(key=lambda t: (-t[0], t[1]))
		for i, (_, t) in enumerate(cand[:NAV_HOLE]):
			put(12 + i, t)
		nhole = min(len(cand), NAV_HOLE)
		got |= NAV_PART_HOLE
	anchors = []
	sp = spawn_end
	if sp is None:
		ts = [int(y) * W + int(x) for y, x in zip(*np.nonzero(M.spawn[team]))]
		sp = min(ts) if ts else None
	if sp is not None:
		anchors.append(sp)
	for a in list(altars)[:3]:
		if a is not None and 0 <= a < len(M.altar_tiles):
			ax, ay = M.altar_tiles[a]
			anchors.append(ay * W + ax)
	for g in list(anchor_groups)[:4]:
		if len(anchors) >= NAV_ANCHOR:
			break
		t = C.near_tile(g) if g is not None and g >= 0 else -1
		if t >= 0:
			anchors.append(t)
	for i, t in enumerate(anchors):
		put(20 + i, t)
	b[56], b[57], b[58], b[59], b[60], b[61] = len(choke), npocket, nhole, len(anchors), got, NAV_SRC_DRAFT
	return bytes(b)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--maps", default="")
	ap.add_argument("--write-catalog", action="store_true")
	a = ap.parse_args()
	import dmem2 as D2
	names = a.maps.split(",") if a.maps else mapdata.official_names()
	for n in names:
		M = mapdata.load(n)
		out = {}
		for team in (0, 1):
			C = CP.Compact(M, team)
			blk = nav_block(M, team, D2.nav_anchor_groups_py(M, team, C), D2.bank_order_py(C)[:3], C=C)
			out[str(team)] = blk.hex()
			print(f"{n:28s} team {team}: choke {blk[56]} pocket {blk[57]} hole {blk[58]} anchor {blk[59]} parts {blk[60]}")
		if a.write_catalog:
			p = os.path.join(ROOT, "maps/catalog", n + ".json")
			cat = json.load(open(p))
			cat["nav"] = out
			json.dump(cat, open(p, "w"), indent=1)


if __name__ == "__main__":
	main()
