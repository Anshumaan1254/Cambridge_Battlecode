#!/usr/bin/env python3
"""Ledger cells without rebuilding bots: win % all maps / official 17 (maps/comp), deaths, per-map losses.
  python3 tools/ledger_sum.py [--maps] [--hash H] BOT_vs_OPP ...     (names of experiments/results/ledger/*.jsonl, or 'BOT' for all its cells)
Uses the latest row per (map, side) for the given bot hash (default: the most recent hash in the file)."""
import glob, json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
COMP = {os.path.basename(p)[:-7] for p in glob.glob(os.path.join(ROOT, 'maps/comp/*.map26a'))}
args = sys.argv[1:]
per_map = '--maps' in args
args = [a for a in args if a != '--maps']
want_hash = None
if '--hash' in args:
	i = args.index('--hash'); want_hash = args[i + 1]; del args[i:i + 2]
files = []
for a in args:
	f = os.path.join(ROOT, 'experiments/results/ledger', a + '.jsonl')
	files += [f] if os.path.exists(f) else sorted(glob.glob(os.path.join(ROOT, 'experiments/results/ledger', a + '_vs_*.jsonl')))
def wr(rs):
	return 100 * sum(r['win'] + 0.5 * (not r['win'] and not r['loss']) for r in rs) / max(1, len(rs))
for f in files:
	rows = [json.loads(l) for l in open(f) if l.strip()]
	if not rows: continue
	h = want_hash or rows[-1]['bot_hash']
	oh = [r['opp_hash'] for r in rows if r['bot_hash'] == h][-1]
	lat = {}
	for r in rows:
		if r['bot_hash'] == h and r['opp_hash'] == oh: lat[(r['map'], r['side'])] = r
	rs = list(lat.values()); c = [r for r in rs if r['map'] in COMP]
	d = [sum(r['deaths'][i] for r in rs) for i in (0, 1)]
	print(f"{os.path.basename(f)[:-6]:16s} {len(rs):3d} games  {wr(rs):5.1f}  official {wr(c):5.1f} ({len(c)})  deaths {d[0]}-{d[1]}  faults {sum(r['faults'] for r in rs)}")
	if per_map:
		lost = sorted(f"{r['map']}/{r['side']}" for r in rs if not r['win'])
		print('   not won:', ' '.join(lost))
