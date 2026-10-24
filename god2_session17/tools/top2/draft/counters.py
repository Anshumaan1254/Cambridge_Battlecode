#!/usr/bin/env python3
"""Counter-picks against an archetype on the whole ladder, rating-adjusted: among games where exactly one side's draft matches the
archetype (e.g. contains Prism), the other side's champion picks vs the result, with the rating logit as an offset
(k fitted on all games of the same data). Also how well the archetype side's first pick predicts its full comp.
  python tools/top2/draft/counters.py --arch prism|ifish|vevdho [--which wr|all] [--since ISO] [--dedup]"""
import collections, math, sys
import numpy as np
import statsmodels.api as sm
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import common as C

ARCH = {
	'prism': lambda d: 5 in d,
	'prismbank': lambda d: 5 in d and 1 in d and 6 in d,
	'ifish': lambda d: {1, 2, 11} <= set(d) and (3 in d or len(d) == 3),
	'vevdho': lambda d: {1, 2, 11} <= set(d),
}


def main():
	a = sys.argv[1:]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	arch = opt('--arch', 'prism')
	which = opt('--which', 'wr')
	since = opt('--since', '2026-10-23T09:00')
	R = C.ratings()
	ms = [m for m in C.matches(which, since=since) if m['a'] in R and m['b'] in R]
	if '--dedup' in a:
		g = {}
		for m in ms:
			g[(m['a'], m['b'], m['map'], tuple(m['da']), tuple(m['db']))] = m
		ms = list(g.values())
	rd = np.array([(R[m['a']]['rating'] - R[m['b']]['rating']) / 100 for m in ms])
	y = np.array([m['awin'] for m in ms], float)
	k = sm.Logit(y, sm.add_constant(rd)).fit(disp=0).params[1]
	f = ARCH[arch]
	rows = []
	for m in ms:
		fa, fb = f(m['da']), f(m['db'])
		if fa == fb:
			continue
		if fa:
			arch_d, other, ow, d = m['da'], m['db'], 1 - m['awin'], (R[m['b']]['rating'] - R[m['a']]['rating']) / 100
			an, on = m['an'], m['bn']
		else:
			arch_d, other, ow, d = m['db'], m['da'], m['awin'], (R[m['a']]['rating'] - R[m['b']]['rating']) / 100
			an, on = m['bn'], m['an']
		rows.append(dict(arch=arch_d, other=other, ow=ow, off=k * d, an=an, on=on, size=len(arch_d), map=m['map']))
	n = len(rows)
	ow = sum(r['ow'] for r in rows)
	exp = sum(1 / (1 + math.exp(-r['off'])) for r in rows)
	print(f'{arch}: {n} games where exactly one side matches ({which} since {since}); k {k:.3f}; non-archetype side won {ow} ({ow / n:.3f}), '
		f'expected {exp:.1f} ({exp / n:.3f}); archetype teams: {collections.Counter(r["an"] for r in rows).most_common(5)}')
	y = np.array([r['ow'] for r in rows], float)
	off = np.array([r['off'] for r in rows])
	print('non-archetype side champion: n with, wins, expected | logit effect (offset rating) +- se')
	for x in range(12):
		has = np.array([int(x in r['other']) for r in rows])
		if has.sum() < 10 or has.sum() > n - 10:
			continue
		res = sm.GLM(y, np.column_stack([np.ones(n), has]), family=sm.families.Binomial(), offset=off).fit()
		w = sum(r['ow'] for r, h in zip(rows, has) if h)
		e = sum(1 / (1 + math.exp(-r['off'])) for r, h in zip(rows, has) if h)
		print(f'  {C.NAMES[x]:9s} {int(has.sum()):5d} {w:5.0f} {e:7.1f} | {res.params[1]:+.2f} +- {res.bse[1]:.2f} (z {res.params[1] / res.bse[1]:+.1f})')
	for size in (3, 4, 5):
		L = [r for r in rows if r['size'] == size]
		if L:
			w = sum(r['ow'] for r in L)
			e = sum(1 / (1 + math.exp(-r['off'])) for r in L)
			print(f'  size {size}: {len(L)} games, non-archetype side won {w} vs expected {e:.1f} ({w - e:+.1f})')
	# first-pick predictiveness on the whole data
	if '--firstpick' in a:
		print('\nfirst pick -> P(comp contains X) over all team-drafts:')
		fp = collections.defaultdict(collections.Counter)
		nn = collections.Counter()
		for m in ms:
			for d in (m['da'], m['db']):
				nn[d[0]] += 1
				for x in set(d):
					fp[d[0]][x] += 1
		for p1, c in sorted(fp.items(), key=lambda kv: -nn[kv[0]]):
			print(f'  p1 {C.NAMES[p1]:9s} n {nn[p1]:5d}: ' + ', '.join(f'{C.AB[x]} {v / nn[p1]:.2f}' for x, v in c.most_common() if x != p1))


if __name__ == '__main__':
	main()
