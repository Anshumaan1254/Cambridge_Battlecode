#!/usr/bin/env python3
"""tools/screensum.py [--maps GLOBS] BOT... : wins per opponent (current-hash ledger rows), pooled over the proxies, plus the
head-to-head vs the baseline. Default proxies _mite,_ifish,_px9,_snk,_fA, baseline _pg3 (legend_m14), pool = the 17 official maps."""
import fnmatch, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import ledger
args = sys.argv[1:]
globs = 'maps/comp/*.map26a'
if args and args[0] == '--maps':
	globs, args = args[1], args[2:]
opps = os.environ.get('OPPS', '_mite,_ifish,_px9,_snk,_fA').split(',')
base = os.environ.get('BASE', '_pg3')
names = set()
for g in globs.split(','):
	names |= {os.path.basename(p)[:-7] for p in glob.glob(g)}
print(f"{'bot':10s} " + ' '.join(f'{o:>9s}' for o in opps) + f" | {'pooled':>14s} | h2h vs {base}")
for b in args:
	cells, tw, tn = [], 0, 0
	for o in opps:
		rs = [r for r in ledger.current_rows(b, o).values() if r['map'] in names]
		w = sum(r['win'] for r in rs); tw += w; tn += len(rs)
		cells.append(f'{w:3d}/{len(rs):<3d}  ' if rs else '      -  ')
	h = [r for r in ledger.current_rows(b, base).values() if r['map'] in names] if b != base else []
	hs = f"{sum(r['win'] for r in h)}/{len(h)}" if h else '-'
	print(f'{b:10s} ' + ' '.join(cells) + f' | {tw:4d}/{tn:<4d} {100 * tw / max(1, tn):5.1f} | {hs}')
