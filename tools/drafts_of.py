#!/usr/bin/env python3
"""tools/drafts_of.py KEEP_DIR [--list] [--by-size]

Drafts of the games kept by `tools/ledger.py run ... --keep DIR` (DIR/<bot>_vs_<opp>/<map>_<side>.json): our roster and theirs per
game, and the head-to-head split into the maps where our roster differs from the opponent's (on those the two bots played different
champions) and the maps where it does not (there a draft-only variant plays the opponent's own games: every such map splits 1-1).
--list prints one line per game; --by-size splits by team size (champion picks per side).
"""
import glob, json, math, os, sys


def wilson(w, n, z=1.96):
	if n == 0:
		return 0.0, 0.0
	p = w / n
	d = 1 + z * z / n
	c = (p + z * z / (2 * n)) / d
	h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
	return c - h, c + h


def sign_p(a, b):
	n = a + b
	if n == 0:
		return 1.0
	k = min(a, b)
	return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def picks(d, team):
	# one entry per draft pick (Cassi and Issac share a pick)
	seen, out = set(), []
	for c in sorted(d['roster']['champions'], key=lambda c: c['draftPick']):
		if c['team'] != team or c['draftPick'] in seen:
			continue
		seen.add(c['draftPick'])
		out.append('C&I' if c['name'] in ('Cassi', 'Issac') else c['name'])
	return out


def main():
	a = sys.argv[1:]
	show = '--list' in a
	by_size = '--by-size' in a
	a = [x for x in a if not x.startswith('--')]
	games = []
	for f in sorted(glob.glob(os.path.join(a[0], '*.json'))):
		d = json.load(open(f))
		base = os.path.basename(f)[:-5]
		m, side = base.rsplit('_', 1)
		us, them = ('teamA', 'teamB') if side == 'A' else ('teamB', 'teamA')
		mine, theirs = picks(d, us), picks(d, them)
		win = d['match']['outcome'] == us
		games.append((m, side, mine, theirs, win))
		if show:
			print(f'{m:34s} {side} {"W" if win else "L"}  {",".join(mine):42s} vs {",".join(theirs)}')
	groups = {'all': games}
	if by_size:
		for g in games:
			groups.setdefault(f'size {len(g[2])}', []).append(g)
	for label, gs in groups.items():
		by = {}
		for g in gs:
			by.setdefault(g[0], []).append(g)
		for kind in ('differs', 'same'):
			sel = [v for v in by.values() if len(v) == 2 and (any(sorted(x[2]) != sorted(x[3]) for x in v) == (kind == 'differs'))]
			n = sum(len(v) for v in sel)
			w = sum(x[4] for v in sel for x in v)
			two = sum(all(x[4] for x in v) for v in sel)
			zero = sum(not any(x[4] for x in v) for v in sel)
			lo, hi = wilson(w, n)
			print(f'{label:8s} roster {kind:7s}: maps {len(sel):3d}  games {w:4d}/{n:<4d} {w / max(1, n):.3f} [{lo:.3f}, {hi:.3f}]  2-0 {two:3d}  1-1 {len(sel) - two - zero:3d}  0-2 {zero:3d}  sign p {sign_p(two, zero):.4f}')


if __name__ == '__main__':
	main()
