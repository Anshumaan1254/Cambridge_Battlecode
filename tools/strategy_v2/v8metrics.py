#!/usr/bin/env python3
"""v8metrics.py DECODED.json [...]: per team: deaths, lone deaths (no living ally within 6 the round before), gems lost on deaths,
banks (count, gems), deaths on the team's own half (nearer its spawn than the enemy's), score. Decode first:
node tools/replay/decode.mjs REPLAY --out X.json. Champion rows: rounds[].ch = [id, team, type, x, y, hp, max_hp, alive, gems, ...]."""
import json, sys, collections

cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def metrics(path):
	d = json.load(open(path))
	R = {r['r']: r for r in d['rounds']}
	first = d['rounds'][0]['ch']
	spawn = {}
	for t in (0, 1):
		ps = [(c[3], c[4]) for c in first if c[1] == t]
		spawn[t] = (sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps))
	out = {t: collections.Counter() for t in (0, 1)}
	for e in d['events']:
		k = e.get('k')
		if k == 'Death':
			t = e['team']
			o = out[t]
			o['deaths'] += 1
			o['bag_lost'] += e.get('bag', 0) or 0
			prev = R.get(e['r'] - 1)
			if prev and not any(c[1] == t and c[7] and c[0] != e['who'] and cheb((c[3], c[4]), e['at']) <= 6 for c in prev['ch']):
				o['alone'] += 1
			at = e['at']
			if cheb(at, spawn[t]) < cheb(at, spawn[1 - t]):
				o['own_half'] += 1
		elif k == 'Banked':
			out[e['team']]['banks'] += 1
			out[e['team']]['banked'] += e.get('gems', 0) or 0
	return out, d['meta']


if __name__ == '__main__':
	tot = {t: collections.Counter() for t in (0, 1)}
	for p in sys.argv[1:]:
		o, meta = metrics(p)
		for t in (0, 1):
			tot[t].update(o[t])
		print(p.split('/')[-1][:40].ljust(40), ' | '.join(f"T{t}: d {o[t]['deaths']} alone {o[t]['alone']} own {o[t]['own_half']} lost {o[t]['bag_lost']} banks {o[t]['banks']}" for t in (0, 1)))
	if len(sys.argv) > 2:
		print('total'.ljust(40), ' | '.join(f"T{t}: d {tot[t]['deaths']} alone {tot[t]['alone']} own {tot[t]['own_half']} lost {tot[t]['bag_lost']} banks {tot[t]['banks']}" for t in (0, 1)))
