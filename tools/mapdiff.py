#!/usr/bin/env python3
"""tools/mapdiff.py BOT BASE OPP[,OPP...] MAP[,MAP...]: wins of BOT and BASE vs each opponent on chosen maps (current-hash
ledger rows, both sides). For changes that only act on some maps: the other maps' games are the same code."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import ledger
bot, base, opps, maps = sys.argv[1], sys.argv[2], sys.argv[3].split(','), sys.argv[4].split(',')
tot = {bot: [0, 0], base: [0, 0]}
for o in opps:
	line = []
	for b in (bot, base):
		rs = [r for r in ledger.current_rows(b, o).values() if r['map'] in maps]
		w = sum(r['win'] for r in rs)
		tot[b][0] += w; tot[b][1] += len(rs)
		line.append(f"{b} {w}/{len(rs)} " + ' '.join(f"{r['map'][:6]}{r['side']}{'W' if r['win'] else 'L'}" for r in sorted(rs, key=lambda r: (r['map'], r['side']))))
	print(f'vs {o}: ' + ' | '.join(line))
print('total', {b: f'{w}/{n} = {100 * w / max(1, n):.1f}%' for b, (w, n) in tot.items()})
