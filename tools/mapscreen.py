#!/usr/bin/env python3
"""Per-map A/B of a variant against its base over the same opponents (current-hash ledger rows, both sides).

  python3 tools/mapscreen.py BASE VAR --opps _mite,_ifish,... [--maps collision,contest,...] [--top _mite,_ifish,_px9]

For every map: wins of VAR and BASE out of the games both have (same opponent, same side), the difference, and the same
counted over --top (the top-team proxies) alone. Used for per-map draft screens: a draft change only changes games on the
maps where it applies, so one variant with the new table on every map screens all maps at once.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('base')
ap.add_argument('var')
ap.add_argument('--opps', required=True)
ap.add_argument('--maps', default='')
ap.add_argument('--top', default='_mite,_ifish,_px9')
a = ap.parse_args()
opps = a.opps.split(',')
top = set(a.top.split(',')) if a.top else set()
want = set(a.maps.split(',')) if a.maps else None

per = {}  # map -> [var wins, base wins, games, var top wins, base top wins, top games]
missing = []
for o in opps:
	rb, rv = ledger.current_rows(a.base, o), ledger.current_rows(a.var, o)
	if not rb or not rv:
		missing.append(o)
		continue
	for k, r in rv.items():
		if k not in rb or (want and k[0] not in want):
			continue
		p = per.setdefault(k[0], [0, 0, 0, 0, 0, 0])
		p[0] += r['win']; p[1] += rb[k]['win']; p[2] += 1
		if o in top:
			p[3] += r['win']; p[4] += rb[k]['win']; p[5] += 1
print(f'{"map":14s} {a.var:>8s} {a.base:>8s} games  diff | top: {a.var:>6s} {a.base:>6s} games')
tot = [0] * 6
for m in sorted(per):
	p = per[m]
	tot = [x + y for x, y in zip(tot, p)]
	print(f'{m:14s} {p[0]:8d} {p[1]:8d} {p[2]:5d} {p[0] - p[1]:+5d} | {p[3]:11d} {p[4]:6d} {p[5]:5d}')
print(f'{"all":14s} {tot[0]:8d} {tot[1]:8d} {tot[2]:5d} {tot[0] - tot[1]:+5d} | {tot[3]:11d} {tot[4]:6d} {tot[5]:5d}')
if missing:
	print('no rows yet for:', ','.join(missing))
