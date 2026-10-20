#!/usr/bin/env python3
"""tools/v8sum.py [--opps A,B,...] BOT...: wins of 42 per opponent from the current engine's ledger (current source hashes only), the sum over the
opponents every listed bot has complete, and the difference to the first bot (the reference, e.g. _g8s = GOD v7)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger

a = sys.argv[1:]
opps = '_g8s,_g4,_pws,_pw,_pc,_m15,_mite,_ifish,_px9,idle'.split(',')
if '--opps' in a:
	i = a.index('--opps'); opps = a[i + 1].split(','); del a[i:i + 2]
bots = a
cell = {}
for b in bots:
	for o in opps:
		if o == b:
			continue
		rows = ledger.current_rows(b, o)
		if len(rows) >= 42:
			cell[(b, o)] = sum(r['win'] for r in rows.values())
common = [o for o in opps if all((b, o) in cell for b in bots if b != o)]
print('bot'.ljust(10) + ''.join(o[:7].rjust(8) for o in opps) + '   sum(common)  diff')
ref = None
for b in bots:
	tot = sum(cell.get((b, o), 0) for o in common if o != b)
	if ref is None:
		ref = tot
	print(b.ljust(10) + ''.join((str(cell[(b, o)]) if (b, o) in cell else '-').rjust(8) for o in opps) + f'   {tot:4d}        {tot - ref:+d}')
print('common:', ','.join(common))
