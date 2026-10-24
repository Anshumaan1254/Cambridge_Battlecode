#!/usr/bin/env python3
"""What beats a study team's draft? For every ranked game of team T (since its current draft went live), the opponent's composition
vs the result, against the rating expectation p0 = sigmoid(k * (r_opp - r_T) / 100) (k from the top-50 fit, default 0.72).
Prints: per opponent champion (present / absent): games, opponent wins, expected wins, excess = actual - expected, and a logit
with the rating logit as offset; per opponent comp archetype; per map size; and the head-to-head matrix between the study teams.
  python tools/top2/draft/vs_team.py --team pbg [--since ISO] [--k 0.72]
  python tools/top2/draft/vs_team.py --h2h [--since ISO]"""
import collections, math, sys
import numpy as np
import statsmodels.api as sm
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import common as C


def sig(x):
	return 1 / (1 + math.exp(-x))


def archetype(d):
	s = set(d)
	if 5 in s and 1 in s:
		base = 'Prism+Vesper'
	elif 5 in s:
		base = 'Prism(no Ve)'
	elif {1, 2, 11} <= s:
		base = 'Ve+Vd+HoR'
	elif {1, 11} <= s:
		base = 'Ve+HoR(no Vd)'
	elif 1 in s:
		base = 'Ve(no HoR)'
	else:
		base = 'no Vesper/Prism'
	return base


def rows_for(team_pre, ms):
	out = []
	for m in ms:
		if m['a'].startswith(team_pre):
			out.append(dict(m, me=m['da'], op=m['db'], opid=m['b'], opn=m['bn'], win=m['awin'], side='a'))
		elif m['b'].startswith(team_pre):
			out.append(dict(m, me=m['db'], op=m['da'], opid=m['a'], opn=m['an'], win=1 - m['awin'], side='b'))
	return out


def main():
	a = sys.argv[1:]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	since = opt('--since', '2026-10-23T09:50')
	k = float(opt('--k', '0.72'))
	R = C.ratings()
	ms = C.matches('all', since=since)
	if '--h2h' in a:
		keys = list(C.STUDY)
		print(f'head-to-head among study teams since {since} (row team wins - losses; drafts per game listed below)')
		print('row\\col ' + ' '.join(f'{x:>9s}' for x in keys))
		det = []
		for k1 in keys:
			cells = []
			for k2 in keys:
				if k1 == k2:
					cells.append(f'{"-":>9s}')
					continue
				rs = [r for r in rows_for(C.STUDY[k1], ms) if r['opid'].startswith(C.STUDY[k2])]
				w = sum(r['win'] for r in rs)
				cells.append(f'{w:>4d}-{len(rs) - w:<4d}')
				if k1 < k2:
					det += [(k1, k2, r) for r in rs]
			print(f'{k1:8s}' + ' '.join(cells))
		print()
		for k1, k2, r in sorted(det, key=lambda x: (x[0], x[1], x[2]['t'])):
			print(f"  {k1:8s} {C.comp_str(r['me']):18s} vs {k2:8s} {C.comp_str(r['op']):18s} {r['map']:22s} {'W' if r['win'] else 'L'} "
				f"{r['t'][5:16]} {r['id'][:8]}")
		return
	key = opt('--team', 'pbg')
	pre = C.STUDY[key]
	rows = [r for r in rows_for(pre, ms) if r['opid'] in R]
	rT = R[next(t for t in R if t.startswith(pre))]['rating']
	for r in rows:
		r['p0'] = sig(k * (R[r['opid']]['rating'] - rT) / 100)   # opponent's expected win prob
		r['ow'] = 1 - r['win']
	n = len(rows)
	ow = sum(r['ow'] for r in rows)
	e = sum(r['p0'] for r in rows)
	print(f'{key}: {n} games since {since}; opponents won {ow} ({ow / n:.3f}), rating-expected {e:.1f} ({e / n:.3f}); rating {rT:.0f}')
	# per opponent champion presence
	print('\nopponent champion present: games, opp wins, expected, excess | absent: games, wins, expected, excess | offset-logit coef +- se')
	off = np.array([math.log(r['p0'] / (1 - r['p0'])) for r in rows])
	y = np.array([r['ow'] for r in rows], float)
	for x in range(12):
		pres = [r for r in rows if x in r['op']]
		absn = [r for r in rows if x not in r['op']]
		if len(pres) < 5 or len(absn) < 5:
			continue
		f = lambda L: (len(L), sum(r['ow'] for r in L), sum(r['p0'] for r in L))
		n1, w1, e1 = f(pres)
		n2, w2, e2 = f(absn)
		X = np.column_stack([np.ones(n), [int(x in r['op']) for r in rows]])
		try:
			res = sm.GLM(y, X, family=sm.families.Binomial(), offset=off).fit()
			coef = f'{res.params[1]:+.2f}+-{res.bse[1]:.2f}'
		except Exception:
			coef = 'n/a'
		print(f'  {C.NAMES[x]:9s} {n1:4d} {w1:4d} {e1:6.1f} {w1 - e1:+6.1f} | {n2:4d} {w2:4d} {e2:6.1f} {w2 - e2:+6.1f} | {coef}')
	# archetypes
	print('\nopponent archetype: games, opp wins, expected, excess, opponents (top 4)')
	arch = collections.defaultdict(list)
	for r in rows:
		arch[archetype(r['op'])].append(r)
	for kk, L in sorted(arch.items(), key=lambda kv: -len(kv[1])):
		w = sum(r['ow'] for r in L)
		ex = sum(r['p0'] for r in L)
		tops = collections.Counter(r['opn'] for r in L).most_common(4)
		print(f'  {kk:16s} {len(L):4d} {w:4d} {ex:6.1f} {w - ex:+6.1f}  {tops}')
	# by size
	print('\nby team size: games, opp wins, expected, excess')
	for s in (3, 4, 5):
		L = [r for r in rows if len(r['me']) == s]
		if L:
			w = sum(r['ow'] for r in L)
			ex = sum(r['p0'] for r in L)
			print(f'  size {s}: {len(L):4d} {w:4d} {ex:6.1f} {w - ex:+6.1f}')
	# opponents that beat T most relative to rating
	print('\nopponents (>= 4 games): games, opp wins, expected, excess, their modal comp(s)')
	byo = collections.defaultdict(list)
	for r in rows:
		byo[r['opn']].append(r)
	for o, L in sorted(byo.items(), key=lambda kv: -(sum(r['ow'] for r in kv[1]) - sum(r['p0'] for r in kv[1]))):
		if len(L) < 4:
			continue
		w = sum(r['ow'] for r in L)
		ex = sum(r['p0'] for r in L)
		comps = collections.Counter(C.comp_set(r['op']) for r in L).most_common(2)
		print(f'  {o[:26]:26s} {len(L):3d} {w:3d} {ex:5.1f} {w - ex:+5.1f}  {comps}')


if __name__ == '__main__':
	main()
