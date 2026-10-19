#!/usr/bin/env python3
"""tools/samegames.py BOT BASE OPP[,OPP...]: how many current-hash ledger games of BOT and BASE against each opponent are identical
(same map, side, winner, rounds and gems), and the win counts of both on the shared games. A control (switches off) should show all."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import ledger
bot, base = sys.argv[1], sys.argv[2]
for o in sys.argv[3].split(','):
	a, b = ledger.current_rows(bot, o), ledger.current_rows(base, o)
	keys = sorted(set(a) & set(b))
	same = sum(a[k]['win'] == b[k]['win'] and a[k]['rounds'] == b[k]['rounds'] and a[k]['gems'] == b[k]['gems'] for k in keys)
	print(f'vs {o}: {same}/{len(keys)} identical; wins {bot} {sum(a[k]["win"] for k in keys)}, {base} {sum(b[k]["win"] for k in keys)}')
