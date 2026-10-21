#!/usr/bin/env python3
"""tools/draftmodel/subfit.py [--ledger DIR] [--pool FILE] VARIANT:FROM:TO ...

Champion values from substitution screens (variants built with pd_sub_from / pd_sub_to, played vs the same opponent): each
screen "TO in place of FROM" gives the log-odds of its win rate, read as v(TO) - v(FROM); a weighted least-squares fit (weight =
games x p x (1 - p), the inverse variance of the log-odds) gives one value per champion, the first FROM anchored at 0. The
values are what the screens say, nothing else: a substitution also changes the team around the slot."""
import json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import abstat  # noqa: E402


def main():
	a = sys.argv[1:]
	opt = lambda k, d: (a.pop(a.index(k) + 1), a.remove(k))[0] if k in a else d
	ledger = opt('--ledger', abstat.latest_ledger())
	pool = opt('--pool', None)
	opp = opt('--opp', '_v8k1')
	names = []
	obs = []
	stems = None
	if pool:
		stems = {os.path.splitext(os.path.basename(m.strip()))[0] for m in open(pool).read().replace('\n', ',').split(',') if m.strip()}
	for spec in a:
		v, f, t = spec.split(':')
		rs = abstat.rows(ledger, v, opp)
		if stems:
			rs = [r for r in rs if r['map'] in stems]
		n = len(rs)
		w = sum(1 for r in rs if r.get('win'))
		if n == 0:
			print(f'{v}: no rows')
			continue
		p = min(max(w / n, 0.5 / n), 1 - 0.5 / n)
		obs.append((f, t, math.log(p / (1 - p)), n * p * (1 - p), v, w, n))
		for x in (f, t):
			if x not in names:
				names.append(x)
	k = len(names)
	idx = {x: i for i, x in enumerate(names)}
	# normal equations with v[names[0]] = 0
	import itertools
	A = [[0.0] * k for _ in range(k)]
	b = [0.0] * k
	for f, t, y, wt, *_ in obs:
		row = [0.0] * k
		row[idx[t]] += 1
		row[idx[f]] -= 1
		for i, j in itertools.product(range(k), range(k)):
			A[i][j] += wt * row[i] * row[j]
		for i in range(k):
			b[i] += wt * row[i] * y
	A[0] = [1.0] + [0.0] * (k - 1)
	b[0] = 0.0
	# Gaussian elimination
	M = [A[i] + [b[i]] for i in range(k)]
	for c in range(k):
		pr = max(range(c, k), key=lambda r: abs(M[r][c]))
		if abs(M[pr][c]) < 1e-12:
			continue
		M[c], M[pr] = M[pr], M[c]
		for r in range(k):
			if r != c and M[r][c]:
				fct = M[r][c] / M[c][c]
				M[r] = [x - fct * y for x, y in zip(M[r], M[c])]
	vals = {names[i]: (M[i][k] / M[i][i] if abs(M[i][i]) > 1e-12 else float('nan')) for i in range(k)}
	for f, t, y, wt, v, w, n in obs:
		print(f'{v:10s} {t:>9s} for {f:9s} {w:4d}/{n:<4d} log-odds {y:+.3f}  fit {vals[t] - vals[f]:+.3f}')
	print('values (log-odds vs the anchor):')
	for x, val in sorted(vals.items(), key=lambda z: -z[1]):
		print(f'  {x:10s} {val:+.3f}')


if __name__ == '__main__':
	main()
