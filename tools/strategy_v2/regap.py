#!/usr/bin/env python3
"""Camp re-engagement after respawn, and the first touch of each group (session 12, doc 12).

usage: python3 -I tools/strategy_v2/regap.py OUT_DIR ic|local [--maps]

OUT_DIR is an analyze.py output dir (run_all.py writes OUT/out/). 'ic' labels the sides with ictab.py (the Stellar-first
team of the Oct 19 INTERWIN games = IC); 'local' takes team 0 as ours (kpi_local.sh runs). For consecutive kills of one
group the gap is next attack start - previous kill round; minus the group's smallest gap (about its respawn time) it is
the time the respawned camp stood unattacked. Contest and stampede are left out (objective plans).
"""
import collections
import csv
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ictab  # noqa: E402


def main():
	if len(sys.argv) < 3:
		sys.exit(__doc__)
	d, who, per_map = sys.argv[1], sys.argv[2], '--maps' in sys.argv
	games = {g['match']: g for g in ictab.games(os.path.join(d, 'team.csv'))} if who == 'ic' else None
	kills = collections.defaultdict(list)
	for r in csv.DictReader(open(os.path.join(d, 'group_kills.csv'))):
		if r['match'].split('_', 1)[1].split('_')[-1] in ('contest', 'stampede'):
			continue
		kills[(r['match'], r['group'])].append((int(r['r']), int(r['start']), int(r['killer']), r['side_for_killer']))
	idle = collections.defaultdict(list)
	first = collections.defaultdict(list)
	for (m, g), ks in kills.items():
		if who == 'ic':
			if m not in games:
				continue
			me = games[m]['ic']
		else:
			me = 0
		lab = (lambda k: 'IC' if k == me else 'OPP') if who == 'ic' else (lambda k: 'US' if k == 0 else 'OPP')
		mp = m.split('_', 1)[1].split('_')[-1] if per_map else 'all'
		ks.sort()
		for t in (0, 1):
			mine = [k for k in ks if k[2] == t]
			if mine:
				first[(lab(t), mp)].append(mine[0][1])
		gaps = [ks[i + 1][1] - ks[i][0] for i in range(len(ks) - 1)]
		if not gaps:
			continue
		mn = min(gaps)
		for i in range(len(ks) - 1):
			idle[(lab(ks[i + 1][2]), mp, ks[i + 1][3])].append(gaps[i] - mn)
	print('| team | map | side | re-kills | idle after respawn mean | p50 | p75 | share <= 5 |')
	print('|---|---|---|---|---|---|---|---|')
	for k, v in sorted(idle.items()):
		v.sort()
		print(f'| {k[0]} | {k[1]} | {k[2]} | {len(v)} | {st.mean(v):.1f} | {v[len(v) // 2]} | {v[3 * len(v) // 4]} | {sum(x <= 5 for x in v) / len(v):.2f} |')
	print('\n| team | map | groups | first touch median |\n|---|---|---|---|')
	for k, v in sorted(first.items()):
		print(f'| {k[0]} | {k[1]} | {len(v)} | {sorted(v)[len(v) // 2]} |')


if __name__ == '__main__':
	main()
