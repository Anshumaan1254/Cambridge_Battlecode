#!/usr/bin/env python3
"""Exact-composition matchups on the ladder, rating-adjusted. For each team size, the most common comp sets, their overall record and
excess wins over the rating expectation (p0 = sigmoid(k * rating diff / 100), k fitted per size on the same data), and the
comp-vs-comp matrix (wins-losses and excess) for the frequent ones. Also the favourite's win rate per size and per map.
  python tools/top2/draft/comp_matrix.py [--which wr|all] [--since ISO] [--top N] [--dedup]"""
import collections, math, sys
import numpy as np
import statsmodels.api as sm
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import common as C


def sig(x):
	return 1 / (1 + math.exp(-x))


def main():
	a = sys.argv[1:]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	which = opt('--which', 'wr')
	since = opt('--since', '2026-10-23T09:00')
	top = int(opt('--top', '8'))
	R = C.ratings()
	ms = [m for m in C.matches(which, since=since) if m['a'] in R and m['b'] in R]
	if '--dedup' in a:
		# identical (teams, sides, map, drafts) within the window are deterministic replays of each other: keep one per key (majority result)
		g = collections.defaultdict(list)
		for m in ms:
			g[(m['a'], m['b'], m['map'], tuple(m['da']), tuple(m['db']))].append(m)
		ms = []
		for k, L in g.items():
			m = dict(L[0])
			m['awin'] = 1 if sum(x['awin'] for x in L) * 2 >= len(L) else 0
			ms.append(m)
	print(f'{len(ms)} games ({which} since {since}{", dedup" if "--dedup" in a else ""})')
	# favourite win rate and rating slope by size and map
	print('\nrating predictiveness by team size: games, favourite win rate (|diff| >= 50), logit slope per 100 +- se')
	ks = {}
	for size in (3, 4, 5):
		L = [m for m in ms if len(m['da']) == size]
		rd = np.array([(R[m['a']]['rating'] - R[m['b']]['rating']) / 100 for m in L])
		y = np.array([m['awin'] for m in L], float)
		res = sm.Logit(y, sm.add_constant(rd)).fit(disp=0)
		ks[size] = res.params[1]
		fav = [(m['awin'] if R[m['a']]['rating'] > R[m['b']]['rating'] else 1 - m['awin']) for m in L if abs(R[m['a']]['rating'] - R[m['b']]['rating']) >= 50]
		big = [(m['awin'] if R[m['a']]['rating'] > R[m['b']]['rating'] else 1 - m['awin']) for m in L if abs(R[m['a']]['rating'] - R[m['b']]['rating']) >= 150]
		print(f'  size {size}: {len(L):5d} games; favourite (>=50) wins {np.mean(fav):.3f} (n {len(fav)}); (>=150) {np.mean(big):.3f} (n {len(big)}); '
			f'slope {res.params[1]:+.3f} +- {res.bse[1]:.3f}')
	print('\nper map: games, favourite (>= 100 diff) win rate, n')
	pm = []
	for mp in sorted(set(m['map'] for m in ms)):
		L = [m for m in ms if m['map'] == mp and abs(R[m['a']]['rating'] - R[m['b']]['rating']) >= 100]
		if len(L) < 10:
			continue
		fav = np.mean([(m['awin'] if R[m['a']]['rating'] > R[m['b']]['rating'] else 1 - m['awin']) for m in L])
		pm.append((fav, mp, len(L), len(next(x for x in ms if x['map'] == mp)['da'])))
	for fav, mp, n, s in sorted(pm):
		print(f'  {mp:22s} size {s} favourite wins {fav:.3f} (n {n})')
	# comps
	for size in (3, 4, 5):
		L = [m for m in ms if len(m['da']) == size]
		k = ks[size]
		cnt = collections.Counter()
		for m in L:
			cnt[C.comp_set(m['da'])] += 1
			cnt[C.comp_set(m['db'])] += 1
		common = [c for c, _ in cnt.most_common(top)]
		print(f'\n=== size {size}: {len(L)} games; slope {k:.3f}; most common comps (team-games, wins, expected, excess):')
		rec = collections.defaultdict(lambda: [0, 0.0, 0.0])
		mat = collections.defaultdict(lambda: [0, 0, 0.0])
		for m in L:
			ca, cb = C.comp_set(m['da']), C.comp_set(m['db'])
			pa = sig(k * (R[m['a']]['rating'] - R[m['b']]['rating']) / 100)
			for c, w, p in ((ca, m['awin'], pa), (cb, 1 - m['awin'], 1 - pa)):
				rec[c][0] += 1
				rec[c][1] += w
				rec[c][2] += p
			if ca != cb:
				mat[(ca, cb)][0] += 1
				mat[(ca, cb)][1] += m['awin']
				mat[(ca, cb)][2] += pa
				mat[(cb, ca)][0] += 1
				mat[(cb, ca)][1] += 1 - m['awin']
				mat[(cb, ca)][2] += 1 - pa
		for c in common:
			n, w, e = rec[c]
			se = math.sqrt(max(e * (1 - e / n), 1e-9))
			print(f'  {c:20s} {n:5d} {w:6.0f} {e:7.1f} {w - e:+6.1f} (z {(w - e) / se:+.1f})')
		print('  matrix (row vs col: W-L, excess):')
		print('  ' + ' ' * 20 + ''.join(f'{c[:14]:>16s}' for c in common))
		for r in common:
			cells = []
			for c in common:
				if r == c:
					cells.append(f'{"-":>16s}')
				else:
					n, w, e = mat[(r, c)]
					cells.append(f'{w:>4d}-{n - w:<3d}{w - e:+5.1f}  ' if n else f'{"":>16s}')
			print(f'  {r:20s}' + ''.join(cells))


if __name__ == '__main__':
	main()
