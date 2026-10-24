#!/usr/bin/env python3
"""Is a team's pick i a fixed function of the map, or does it react to the side or to the opponent's earlier picks
(picks are simultaneous per slot, revealed as they go, so pick i can see the opponent's picks 1..i-1)?
For each study team and pick slot: purity = share of games whose pick equals the modal pick of its key, over keys seen >= 2 times,
for key = map | map+side | map+opponent picks 1..i-1 (as a set) | map + opponent's same-slot-earlier pick of a given champion.
Also lists, for slots that vary within a map, the opponent picks seen before the slot vs the chosen pick.
  python tools/top2/draft/reactivity.py [--since ISO] [--team key]"""
import collections, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import common as C


def purity(rows, keyf, slot):
	g = collections.defaultdict(collections.Counter)
	for r in rows:
		if slot < len(r['me']):
			g[keyf(r)][r['me'][slot]] += 1
	n = k = 0
	for key, c in g.items():
		t = sum(c.values())
		if t < 2:
			continue
		n += t
		k += c.most_common(1)[0][1]
	return k, n


def main():
	a = sys.argv[1:]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	since = opt('--since', '2026-10-23T09:50')
	only = opt('--team', None)
	ms = C.matches('all', since=since)
	for key, pre in C.STUDY.items():
		if only and key != only:
			continue
		rows = []
		for m in ms:
			if m['a'].startswith(pre):
				rows.append(dict(m, side='a', me=m['da'], op=m['db'], win=m['awin']))
			elif m['b'].startswith(pre):
				rows.append(dict(m, side='b', me=m['db'], op=m['da'], win=1 - m['awin']))
		print('=' * 90)
		print(f'{key}: {len(rows)} games since {since}')
		for s in range(5):
			k1, n1 = purity(rows, lambda r: r['map'], s)
			if n1 == 0:
				continue
			k2, n2 = purity(rows, lambda r: (r['map'], r['side']), s)
			k3, n3 = purity(rows, lambda r: (r['map'], tuple(sorted(r['op'][:s]))), s)
			k4, n4 = purity(rows, lambda r: (r['map'], tuple(r['op'][:s])), s)
			print(f'  slot {s + 1}: purity map {k1}/{n1}={k1 / n1:.2f} | map+side {k2}/{n2}={k2 / max(1, n2):.2f} | '
				f'map+opp-earlier-set {k3}/{n3}={k3 / max(1, n3):.2f} | map+opp-earlier-seq {k4}/{n4}={k4 / max(1, n4):.2f}')
		# within-map variation detail: which slots vary; show (opp earlier picks) -> my pick
		bymap = collections.defaultdict(list)
		for r in rows:
			bymap[r['map']].append(r)
		var = collections.defaultdict(list)
		for mp, rs in bymap.items():
			for s in range(5):
				ps = set(r['me'][s] for r in rs if s < len(r['me']))
				if len(ps) > 1:
					for r in rs:
						var[s].append((mp, tuple(r['op'][:s]), r['me'][s], r['side']))
		for s, lst in sorted(var.items()):
			# does a specific opponent earlier pick predict the choice?
			by_opp = collections.defaultdict(collections.Counter)
			for mp, opp, pick, side in lst:
				for x in range(12):
					by_opp[(x, x in opp)][pick] += 1
			print(f'  slot {s + 1} varies on {len(set(m for m, *_ in lst))} maps ({len(lst)} games); choice by opponent earlier pick present/absent:')
			lines = []
			for x in range(12):
				yes, no = by_opp[(x, True)], by_opp[(x, False)]
				if sum(yes.values()) >= 3 and sum(no.values()) >= 3:
					fy = {C.AB[p]: round(v / sum(yes.values()), 2) for p, v in yes.most_common()}
					fn = {C.AB[p]: round(v / sum(no.values()), 2) for p, v in no.most_common()}
					lines.append(f'    opp has {C.NAMES[x]:9s} before slot: n={sum(yes.values()):3d} {fy} | absent n={sum(no.values()):3d} {fn}')
			print('\n'.join(lines))


if __name__ == '__main__':
	main()
