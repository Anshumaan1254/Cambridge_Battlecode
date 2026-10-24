#!/usr/bin/env python3
"""tools/mapintel/official_summary.py [MAPDIR] [GROUPS_TXT] [OUT_CSV]

First per-map table of the official pool (session 18, Oct 24). Inputs:
  - MAPDIR (default maps/official): the .map26a files; size, symmetry, team size, spawn and altars come from tools/replay/mapinfo.mjs
    (the engine's own map loader);
  - GROUPS_TXT (default experiments/results/mapintel/groups_runtime_official40.txt): the runtime camp groups as a bot sees them
    (tools/probe/groups_probe_main.cpp). A map file stores one copy of each mirrored camp; the runtime list has both sides.
Output: one CSV row per map (default maps/official/summary.csv). Group side: a group belongs to team A's half when its first camp is
nearer team A's spawn centre than team B's (Chebyshev), 'mid' when the two distances are within 2.
"""
import collections, csv, json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
mapdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'maps', 'official')
gtxt = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'experiments', 'results', 'mapintel', 'groups_runtime_official40.txt')
out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(mapdir, 'summary.csv')


def groups_by_map(path):
	res, cur = {}, None
	for line in open(path):
		line = line.strip()
		if line.startswith('MAP '):
			cur = line[4:]
			res[cur] = {}
		elif line.startswith('G ') and cur:
			# every body prints the list: keep the first complete copy of each group index
			m = re.match(r'G (\d+) gems (\d+) gold (\d+) respawn (-?\d+) n (\d+)(.*)', line)
			if not m:
				continue
			camps = [(t, int(x), int(y)) for t, x, y in re.findall(r'\| (\w+) (\d+),(\d+)', m.group(6))]
			if len(camps) != int(m.group(5)):
				continue
			res[cur].setdefault(int(m.group(1)), dict(gems=int(m.group(2)), gold=int(m.group(3)), respawn=int(m.group(4)), camps=camps))
	return {k: [v[i] for i in sorted(v)] for k, v in res.items()}


def mapinfo(path):
	txt = subprocess.run(['node', os.path.join(ROOT, 'tools', 'replay', 'mapinfo.mjs'), path], capture_output=True, text=True).stdout
	head = txt.splitlines()[0]
	m = re.search(r'(\d+)x(\d+) sym (\S+).*champs (\d+) spawnA (\d+),(\d+),(\d+),(\d+)', head)
	w, h, sym, champs = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
	sa = tuple(int(m.group(i)) for i in range(5, 9))
	grid = [l[4:] if len(l) > 4 else '' for l in txt.splitlines()[1:]]
	altars = [(x, y) for y, row in enumerate(grid) for x, ch in enumerate(row) if ch == 'A']
	walls = sum(row.count('#') for row in grid)
	holes = sum(row.count('o') for row in grid)
	bushes = sum(row.count('"') for row in grid)
	return dict(w=w, h=h, sym=sym, champs=champs, spawnA=sa, altars=altars, walls=walls, holes=holes, bushes=bushes)


def mirror(sym, w, h, x, y):
	if sym.startswith('H'):
		return w - 1 - x, y
	if sym.startswith('V'):
		return x, h - 1 - y
	return w - 1 - x, h - 1 - y


def main():
	G = groups_by_map(gtxt)
	rows = []
	for f in sorted(os.listdir(mapdir)):
		if not f.endswith('.map26a'):
			continue
		name = f[:-7]
		mi = mapinfo(os.path.join(mapdir, f))
		x0, y0, x1, y1 = mi['spawnA']
		ca = ((x0 + x1) / 2, (y0 + y1) / 2)
		cb = mirror(mi['sym'], mi['w'], mi['h'], *ca)
		types = collections.Counter()
		side = collections.Counter()
		gems = collections.Counter()
		gold = collections.Counter()
		for g in G.get(name, []):
			for t, _, _ in g['camps']:
				types[t] += 1
			_, gx, gy = g['camps'][0]
			da = max(abs(gx - ca[0]), abs(gy - ca[1]))
			db = max(abs(gx - cb[0]), abs(gy - cb[1]))
			s = 'mid' if abs(da - db) <= 2 else ('A' if da < db else 'B')
			side[s] += 1
			gems[s] += g['gems']
			gold[s] += g['gold']
		rows.append(dict(map=name, w=mi['w'], h=mi['h'], sym=mi['sym'], champs=mi['champs'], groups=len(G.get(name, [])),
			groups_A=side['A'], groups_mid=side['mid'], groups_B=side['B'], gems_total=sum(gems.values()), gold_total=sum(gold.values()),
			gems_mid=gems['mid'], gold_mid=gold['mid'], wolf=types['wolf'], elk=types['elk'], gem_cluster=types['gem_cluster'],
			gold_cluster=types['gold_cluster'], monolith=types['monolith'], golem=types['golem'], altars=len(mi['altars']),
			walls=mi['walls'], holes=mi['holes'], bushes=mi['bushes'], spawnA=json.dumps(mi['spawnA']), altar_tiles=json.dumps(mi['altars'])))
	with open(out, 'w', newline='') as fh:
		wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
		wr.writeheader()
		wr.writerows(rows)
	print(f'{len(rows)} maps -> {out}')


if __name__ == '__main__':
	main()
