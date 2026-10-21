#!/usr/bin/env python3
"""tools/draftmodel/dataset.py OUT.jsonl [--pool POOL.csv] KEEP_DIR...

One row per kept game (tools/ledger.py --keep): map, our side, both rosters (pick names in pick order), win. The input of the
draft-value fit (tools/draftmodel/fit.py). --pool keeps only the maps of that pool (the fit must never see the held-out half)."""
import glob, json, os, sys

NAME = {'Cassi': 'C&I', 'Issac': 'C&I'}


def picks(d, team):
	seen, out = set(), []
	for c in sorted(d['roster']['champions'], key=lambda c: c['draftPick']):
		if c['team'] != team or c['draftPick'] in seen:
			continue
		seen.add(c['draftPick'])
		out.append(NAME.get(c['name'], c['name']))
	return out


def main():
	a = sys.argv[1:]
	pool = None
	if '--pool' in a:
		i = a.index('--pool')
		pool = {os.path.splitext(os.path.basename(m.strip()))[0] for m in open(a[i + 1]).read().replace('\n', ',').split(',') if m.strip()}
		del a[i:i + 2]
	out = open(a[0], 'w')
	n = 0
	for kd in a[1:]:
		cell = os.path.basename(kd.rstrip('/'))
		for f in sorted(glob.glob(os.path.join(kd, '*.json'))):
			d = json.load(open(f))
			m, side = os.path.basename(f)[:-5].rsplit('_', 1)
			if pool is not None and m not in pool:
				continue
			us, them = ('teamA', 'teamB') if side == 'A' else ('teamB', 'teamA')
			out.write(json.dumps({'cell': cell, 'map': m, 'side': side, 'ours': picks(d, us), 'theirs': picks(d, them),
				'win': d['match']['outcome'] == us, 'rounds': d['match'].get('rounds')}) + '\n')
			n += 1
	print(n, 'games')


if __name__ == '__main__':
	main()
