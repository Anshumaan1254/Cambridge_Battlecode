#!/usr/bin/env python3
"""Pooled proxy cells with deaths (agent ml2, session 13): tools/ml/ml2_sum.py [--maps GLOBS] BOT...

Per bot: wins, our deaths and their deaths pooled over the proxies (env OPPS, default _mite,_ifish,_px9,_snk,_fA) on the current-hash
ledger rows of the map pool (default the 17 official maps), the head-to-head vs BASE (default _ch2) with its deaths, and how many of the
proxy games are identical to BASE's (same map, side, winner, rounds, gems)."""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import ledger  # noqa: E402

args = sys.argv[1:]
globs = 'maps/comp/*.map26a'
if args and args[0] == '--maps':
	globs, args = args[1], args[2:]
opps = os.environ.get('OPPS', '_mite,_ifish,_px9,_snk,_fA').split(',')
base = os.environ.get('BASE', '_ch2')
names = set()
for g in globs.split(','):
	names |= {os.path.basename(p)[:-7] for p in glob.glob(g)}
print(f"{'bot':10s} {'pooled':>14s} {'deaths us-them':>15s} {'same as base':>13s} | h2h vs {base} (deaths)")
for b in args:
	w = n = du = dt = same = shared = 0
	for o in opps:
		rs = {k: r for k, r in ledger.current_rows(b, o).items() if r['map'] in names}
		bs = {k: r for k, r in ledger.current_rows(base, o).items() if r['map'] in names}
		for k, r in rs.items():
			w += r['win']; n += 1
			du += r['deaths'][0]; dt += r['deaths'][1]
			if k in bs:
				shared += 1
				q = bs[k]
				same += r['win'] == q['win'] and r['rounds'] == q['rounds'] and r['gems'] == q['gems']
	h = [r for r in ledger.current_rows(b, base).values() if r['map'] in names] if b != base else []
	hs = f"{sum(r['win'] for r in h)}/{len(h)} ({sum(r['deaths'][0] for r in h)}-{sum(r['deaths'][1] for r in h)})" if h else '-'
	print(f'{b:10s} {w:4d}/{n:<4d} {100 * w / max(1, n):5.1f} {du:7d}-{dt:<7d} {same:5d}/{shared:<5d}  | {hs}')
