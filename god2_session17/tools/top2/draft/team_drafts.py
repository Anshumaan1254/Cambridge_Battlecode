#!/usr/bin/env python3
"""Per study team: draft per map over time (all ranked lists since engine 1.0.3, Oct 22 07:00), modal draft per map in the newest
window, how deterministic it is (share of games equal to the map's modal draft), pick order, and what explains deviations
(side, opponent's earlier picks). Prints a text report.
  python tools/top2/draft/team_drafts.py [--since ISO] [--window-start ISO] [--team pbg]"""
import collections, json, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import common as C


def main():
	a = sys.argv[1:]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	since = opt('--since', '2026-10-22T07:00')
	wstart = opt('--window-start', '2026-10-23T09:50')
	only = opt('--team', None)
	ms = C.matches('all', since=since)
	for key, pre in C.STUDY.items():
		if only and key != only:
			continue
		rows = []
		for m in ms:
			if m['a'].startswith(pre):
				rows.append(dict(m, side='a', me=m['da'], op=m['db'], win=m['awin'], opn=m['bn']))
			elif m['b'].startswith(pre):
				rows.append(dict(m, side='b', me=m['db'], op=m['da'], win=1 - m['awin'], opn=m['an']))
		print('=' * 100)
		print(f'{key} ({C.STUDY_NAME[key]}): {len(rows)} ranked games since {since}; {sum(r["t"] >= wstart for r in rows)} in window >= {wstart}')
		# change points: per map, sequence of distinct drafts over time
		bymap = collections.defaultdict(list)
		for r in rows:
			bymap[r['map']].append(r)
		# time buckets (2 h) x share of games whose draft == newest-window modal draft of that map
		modal = {}
		for mp, rs in bymap.items():
			w = [tuple(r['me']) for r in rs if r['t'] >= wstart] or [tuple(r['me']) for r in rs]
			modal[mp] = collections.Counter(w).most_common(1)[0][0]
		buck = collections.defaultdict(lambda: [0, 0])
		for r in rows:
			b = r['t'][:13]
			buck[b][1] += 1
			buck[b][0] += tuple(r['me']) == modal[r['map']]
		print('  hour: share of games equal to the newest modal draft of the map (shows when the draft changed)')
		print('   ', ' '.join(f'{b[5:13]}:{v[0]}/{v[1]}' for b, v in sorted(buck.items())))
		# newest window: per map modal + deviations
		print('  per map (window): modal draft [pick order] n_modal/n | deviations (side, opponent draft)')
		det_n = det_k = 0
		for mp in sorted(bymap):
			rs = [r for r in bymap[mp] if r['t'] >= wstart]
			if not rs:
				continue
			c = collections.Counter(tuple(r['me']) for r in rs)
			md, k = c.most_common(1)[0]
			det_n += len(rs)
			det_k += k
			wins = sum(r['win'] for r in rs)
			dev = [r for r in rs if tuple(r['me']) != md]
			devs = '; '.join(f"{C.comp_str(r['me'])} ({r['side']}, vs {C.comp_str(r['op'])})" for r in dev[:4])
			print(f"   {mp:22s} {C.comp_str(md):18s} {k}/{len(rs)} W{wins}/{len(rs)} side a {sum(r['side']=='a' for r in rs)} | {devs}")
		print(f'  window determinism: {det_k}/{det_n} = {det_k / max(1, det_n):.2f} of games use the map modal draft')
		# set-level determinism (same champions, any order)
		cnt = collections.Counter()
		for r in rows:
			if r['t'] >= wstart:
				for x in r['me']:
					cnt[x] += 1
		nw = sum(1 for r in rows if r['t'] >= wstart)
		print('  pick rate (window):', ', '.join(f'{C.NAMES[x]} {v / nw:.2f}' for x, v in cnt.most_common()))
		# pick position
		pos = collections.defaultdict(collections.Counter)
		for r in rows:
			if r['t'] >= wstart:
				for i, x in enumerate(r['me']):
					pos[x][i] += 1
		print('  pick position (window): ' + '; '.join(f'{C.NAMES[x]} ' + ','.join(f'p{i + 1}:{pos[x][i]}' for i in sorted(pos[x])) for x, _ in cnt.most_common()))


if __name__ == '__main__':
	main()
