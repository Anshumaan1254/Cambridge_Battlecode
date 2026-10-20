#!/usr/bin/env python3
"""pace.py BOT... [--pool comp|gen2|pad17|all] [--maps]: unopposed pace per pool from ledger cells vs idle (latest hash)."""
import glob, json, os, sys
ROOT = '/home/user/Cambridge_Battlecode'
pools = {k: {os.path.basename(p)[:-7] for p in glob.glob(f'{ROOT}/maps/{k}/*.map26a')} for k in ('comp', 'gen2', 'pad17')}
bots = [a for a in sys.argv[1:] if not a.startswith('--')]
per = {}
for b in bots:
	rows = [json.loads(l) for l in open(f'{ROOT}/experiments/results/ledger/{b}_vs_idle.jsonl') if l.strip()]
	sys.path.insert(0, f'{ROOT}/tools'); import ledger
	h = ledger.src_hash(b)
	lat = {(r['map'], r['side']): r for r in rows if r['bot_hash'] == h}
	m = {}
	for (mp, side), r in lat.items():
		m.setdefault(mp, []).append(r['rounds'] if r['win'] else 2000)
	per[b] = {k: sum(v) / len(v) for k, v in m.items()}
line = 'pool    ' + ''.join(b[:10].rjust(11) for b in bots)
print(line)
for k, s in pools.items():
	vals = []
	for b in bots:
		c = [v for mp, v in per[b].items() if mp in s]
		vals.append(f"{sum(c)/len(c):7.1f}({len(c):2d})" if c else '      -    ')
	print(k.ljust(8) + ''.join(v.rjust(11) for v in vals))
if '--maps' in sys.argv:
	maps = sorted(set().union(*[set(p) for p in per.values()]))
	for mp in maps:
		print(mp[:22].ljust(23) + ''.join(f"{per[b].get(mp, float('nan')):10.0f}" for b in bots) + ('' if len(bots) < 2 else f"  {per[bots[1]].get(mp, float('nan')) - per[bots[0]].get(mp, float('nan')):+6.0f}"))
