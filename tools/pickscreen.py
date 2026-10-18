#!/usr/bin/env python3
"""tools/pickscreen.py BASE VAR[,VAR...] GROUP=OPP,OPP [GROUP=...] [--size N]: wins of draft variants and their base on the maps
of one team size (default 5), per opponent group (current-hash ledger rows, both sides). Used for the counter-pick screen: the
groups are opponents whose first picks look alike to our last draft round."""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import ledger
args = [a for a in sys.argv[1:] if not a.startswith('--')]
size = int(sys.argv[sys.argv.index('--size') + 1]) if '--size' in sys.argv else 5
base, variants = args[0], args[1].split(',')
groups = [(g.split('=')[0], g.split('=')[1].split(',')) for g in args[2:] if '=' in g]
def size_of(m):
	import re
	x = re.search(r'_c(\d)', m)
	if x: return int(x.group(1))
	p = os.path.join(ledger.ROOT, 'maps', 'comp', m + '.map26a')
	if os.path.exists(p):
		import subprocess
		out = subprocess.run(['node', os.path.join(ledger.ROOT, 'tools', 'replay', 'mapinfo.mjs'), p], capture_output=True, text=True).stdout
		x = re.search(r'champs (\d)', out)
		return int(x.group(1)) if x else 0
	return 0
cache = {}
def ok(m):
	if m not in cache: cache[m] = size_of(m) == size
	return cache[m]
print(f'{"group":10s}' + ''.join(f'{b:>12s}' for b in [base] + variants))
for name, opps in groups:
	line = f'{name:10s}'
	for b in [base] + variants:
		w = n = 0
		for o in opps:
			if o == b: continue
			for r in ledger.current_rows(b, o).values():
				if ok(r['map']): w += r['win']; n += 1
		line += f'{f"{w}/{n} {100*w/max(1,n):.0f}%":>12s}'
	print(line)
