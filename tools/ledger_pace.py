#!/usr/bin/env python3
"""Unopposed pace from ledger cells vs idle: round at which the bot banks 1000 gems (a game not won counts 2000), mean of both sides.
  python3 tools/ledger_pace.py BOT... [--maps]       (cells experiments/results/ledger/BOT_vs_idle.jsonl, latest bot hash)
Fill a cell first: python3 tools/ledger.py run BOT idle --maps 'maps/comp/*.map26a' --jobs 2"""
import glob, json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger import LEDGER as LEDGER_DIR  # per-engine ledger directory
COMP = {os.path.basename(p)[:-7] for p in glob.glob(os.path.join(ROOT, 'maps/comp/*.map26a'))}
bots = [a for a in sys.argv[1:] if not a.startswith('--')]
per = {}
for b in bots:
	f = os.path.join(LEDGER_DIR, f'{b}_vs_idle.jsonl')
	rows = [json.loads(l) for l in open(f) if l.strip()]
	h = rows[-1]['bot_hash']
	lat = {(r['map'], r['side']): r for r in rows if r['bot_hash'] == h}
	m = {}
	for (mp, side), r in lat.items():
		m.setdefault(mp, []).append(r['rounds'] if r['win'] else 2000)
	per[b] = {k: sum(v) / len(v) for k, v in m.items()}
	c = [v for k, v in per[b].items() if k in COMP]
	print(f"{b:10s} official {sum(c)/max(1,len(c)):6.1f} ({len(c)} maps)  all {sum(per[b].values())/len(per[b]):6.1f} ({len(per[b])} maps)")
if '--maps' in sys.argv:
	maps = sorted(set().union(*[set(p) for p in per.values()]))
	print('map'.ljust(28) + ''.join(b[:9].rjust(10) for b in bots))
	for mp in maps:
		if mp in COMP:
			print(mp.ljust(28) + ''.join(f"{per[b].get(mp, float('nan')):10.0f}" for b in bots))
