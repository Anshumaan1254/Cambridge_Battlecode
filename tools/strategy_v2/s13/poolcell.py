#!/usr/bin/env python3
"""poolcell.py BOT OPP... --pool DIR [--pool DIR] [--maps]: wins of BOT vs each OPP per map pool, from the per-engine ledger
(rows on the current source hash of both bots). vs idle it also prints the mean round of the finish (unopposed pace)."""
import glob, json, os, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import ledger
args = sys.argv[1:]
pools = [args[i + 1] for i, a in enumerate(args) if a == '--pool']
names = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] != '--pool')]
bot, opps = names[0], names[1:]
D = os.environ.get('LEDGER_DIR') or ledger.LEDGER
hb = ledger.src_hash(bot)
for opp in opps:
	ho = ledger.src_hash(opp)
	f = os.path.join(D, f'{bot}_vs_{opp}.jsonl')
	rows = [json.loads(l) for l in open(f)] if os.path.exists(f) else []
	for pool in pools:
		maps = {os.path.splitext(os.path.basename(m))[0] for m in glob.glob(os.path.join(pool, '*.map26a'))}
		sel = {}
		for r in rows:
			if r['map'] in maps and r['bot_hash'] == hb and r['opp_hash'] == ho: sel[(r['map'], r['side'])] = r
		w = sum(1 for r in sel.values() if r['win'])
		dth = [sum(r['deaths'][0 if r['side'] == 'A' else 1] for r in sel.values()), sum(r['deaths'][1 if r['side'] == 'A' else 0] for r in sel.values())]
		extra = f"  pace {sum(r['rounds'] for r in sel.values()) / max(1, len(sel)):.0f}" if opp == 'idle' else f'  deaths {dth[0]}-{dth[1]}'
		print(f'{bot:8s} vs {opp:8s} {pool:16s} {w:3d}/{len(sel):3d}{extra}')
		if '--maps' in args:
			per = collections.defaultdict(list)
			for (m, s), r in sorted(sel.items()):
				g = r['gems'] if s == 'A' else r['gems'][::-1]
				per[m].append(f"{s}:{'W' if r['win'] else 'l'} {g[0]}-{g[1]} r{r['rounds']}")
			for m, v in per.items(): print('     ', m.ljust(24), '  '.join(v))
