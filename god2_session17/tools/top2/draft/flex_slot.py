#!/usr/bin/env python3
"""Value of the flex picks on top of a fixed core, rating-adjusted: for team-drafts containing the core (e.g. Vesper + Vendetta +
Marcella + HoR on 5-champion maps), the remaining pick(s) vs wins and the rating expectation (k fitted per team size on the same data).
  python tools/top2/draft/flex_slot.py [--which wr|all] [--since ISO] [--dedup]"""
import collections, math, sys
import numpy as np
import statsmodels.api as sm
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import common as C

CORES = [(5, {1, 2, 6, 11}), (5, {1, 6, 11}), (5, {1, 11}), (4, {1, 6, 11}), (4, {1, 11}), (3, {1, 11}), (3, {1})]


def main():
	a = sys.argv[1:]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	which = opt('--which', 'wr')
	since = opt('--since', '2026-10-23T09:00')
	R = C.ratings()
	ms = [m for m in C.matches(which, since=since) if m['a'] in R and m['b'] in R]
	if '--dedup' in a:
		g = {}
		for m in ms:
			g[(m['a'], m['b'], m['map'], tuple(m['da']), tuple(m['db']))] = m
		ms = list(g.values())
	print(f'{len(ms)} games ({which} since {since}{", dedup" if "--dedup" in a else ""})')
	ks = {}
	for size in (3, 4, 5):
		L = [m for m in ms if len(m['da']) == size]
		rd = np.array([(R[m['a']]['rating'] - R[m['b']]['rating']) / 100 for m in L])
		y = np.array([m['awin'] for m in L], float)
		ks[size] = sm.Logit(y, sm.add_constant(rd)).fit(disp=0).params[1]
	for size, core in CORES:
		k = ks[size]
		rec = collections.defaultdict(lambda: [0, 0, 0.0])
		for m in ms:
			if len(m['da']) != size:
				continue
			pa = 1 / (1 + math.exp(-k * (R[m['a']]['rating'] - R[m['b']]['rating']) / 100))
			for d, w, p in ((m['da'], m['awin'], pa), (m['db'], 1 - m['awin'], 1 - pa)):
				s = set(d)
				if core <= s:
					rest = '/'.join(C.AB[x] for x in sorted(s - core)) or '-'
					rec[rest][0] += 1
					rec[rest][1] += w
					rec[rest][2] += p
		cs = '/'.join(C.AB[x] for x in sorted(core))
		print(f'\nsize {size}, core {cs} (k {k:.2f}): + flex -> team-games, wins, expected, excess, z')
		for rest, (n, w, e) in sorted(rec.items(), key=lambda kv: -kv[1][0])[:9]:
			se = math.sqrt(max(e * (1 - e / n), 1e-9))
			print(f'   +{rest:10s} {n:5d} {w:5d} {e:7.1f} {w - e:+6.1f}  z {(w - e) / se:+.1f}')


if __name__ == '__main__':
	main()
