#!/usr/bin/env python3
"""tools/cell.py BOT OPP [--maps]: current-hash ledger rows: all / official win %, deaths, and per official map (A,B)."""
import sys, os, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import ledger
bot, opp = sys.argv[1], sys.argv[2]
rows = list(ledger.current_rows(bot, opp).values())
comp = set(os.path.basename(p)[:-7] for p in glob.glob(os.path.join(ledger.ROOT, 'maps', 'comp', '*.map26a')))
c = [r for r in rows if r['map'] in comp]
pct = lambda rs: 100 * sum(r['win'] for r in rs) / max(1, len(rs))
print(f"{bot} vs {opp}: {len(rows)} games {pct(rows):.1f} / official {len(c)} {pct(c):.1f}  deaths {sum(r['deaths'][0] for r in rows)}-{sum(r['deaths'][1] for r in rows)}  faults {sum(r['faults'] for r in rows)}")
if '--maps' in sys.argv:
    for m in sorted(comp):
        rs = sorted([r for r in c if r['map'] == m], key=lambda r: r['side'])
        print('  ', m.ljust(12), '  '.join(f"{r['side']}:{'W' if r['win'] else 'L'} {r['gems'][0]}-{r['gems'][1]} r{r['rounds']} d{r['deaths'][0]}-{r['deaths'][1]}" for r in rs))
