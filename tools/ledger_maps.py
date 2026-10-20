#!/usr/bin/env python3
"""Per-map wins of several bots against one opponent from the ledger (both sides: 2 games per map).
usage: python3 tools/ledger_maps.py OPP BOT [BOT ...] [--dir DIR]   (default: the current engine's ledger)"""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import ledger
a = sys.argv[1:]
d = a[a.index('--dir') + 1] if '--dir' in a else ledger.LEDGER
if '--dir' in a:
    i = a.index('--dir'); del a[i:i + 2]
opp, bots = a[0], a[1:]
table = {}
maps = set()
for b in bots:
    f = os.path.join(d, f'{b}_vs_{opp}.jsonl')
    w = collections.defaultdict(lambda: [0, 0, 0, 0])  # wins, games, our gems, their gems
    if os.path.exists(f):
        for line in open(f):
            r = json.loads(line)
            m = os.path.basename(r.get('map', '?')).replace('.map26a', '')
            maps.add(m)
            w[m][0] += int(bool(r.get('win'))); w[m][1] += 1
            g = r.get('gems') or [0, 0]
            w[m][2] += g[0]; w[m][3] += g[1]
    table[b] = w
print(f"{'map':28s} " + ' '.join(f'{b:>9s}' for b in bots))
for m in sorted(maps):
    print(f"{m[:28]:28s} " + ' '.join(f"{table[b][m][0]}/{table[b][m][1]}".rjust(9) if m in table[b] else ' ' * 9 for b in bots))
print(f"{'total':28s} " + ' '.join(f"{sum(v[0] for v in table[b].values())}/{sum(v[1] for v in table[b].values())}".rjust(9) for b in bots))
