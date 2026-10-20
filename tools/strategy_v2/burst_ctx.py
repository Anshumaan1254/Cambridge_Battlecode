#!/usr/bin/env python3
"""Burst deaths (>= 60% health 3 rounds before death) in decoded ladder games: numbers near the victim at r-3, who closed in,
spells landed, our team's damage back. usage: python3 -I tools/strategy_v2/burst_ctx.py DMG_DIR INDEX_JSON [--team us|them] [--skip contest]"""
import collections, glob, json, os, sys


def cheb(a, b):
	return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


a = sys.argv[1:]
team_sel, skip = 'us', []
if '--team' in a:
	i = a.index('--team'); team_sel = a[i + 1]; del a[i:i + 2]
if '--skip' in a:
	i = a.index('--skip'); skip = a[i + 1].split(','); del a[i:i + 2]
ddir, idxp = a
idx = {r['group'] + '_' + r['nn']: r for r in json.load(open(idxp))}
C = collections.Counter()
H = collections.defaultdict(list)
n = 0
for f in sorted(glob.glob(os.path.join(ddir, '*.json'))):
	name = os.path.basename(f)[:-5]
	if name.split('_')[-1] in skip:
		continue
	us = 0 if idx[name[:11]]['side'] == 'A' else 1
	want = us if team_sel == 'us' else 1 - us
	d = json.load(open(f))
	R = {x['r']: {c[0]: c for c in x['ch']} for x in d['rounds']}
	team = {c[0]: c[1] for c in d['rounds'][0]['ch']}
	types = {b['index']: b['type'] for b in d['meta']['bodies']}
	spawn = {c[0]: (c[3], c[4]) for c in d['rounds'][0]['ch']}
	dmg = collections.defaultdict(list)
	for row in d['dmg']:
		dmg[row[0]].append(row)
	for r in sorted(R):
		if r - 6 not in R or r - 1 not in R:
			continue
		for b, c in R[r].items():
			if team[b] != want or c[7] or not R[r - 1][b][7]:
				continue
			p3 = R[r - 3].get(b)
			if not p3 or not p3[7] or p3[5] < 0.6 * p3[6]:
				continue
			n += 1
			me3 = (p3[3], p3[4])
			en = [x for k, x in R[r - 3].items() if team[k] != want and x[7]]
			al = [x for k, x in R[r - 3].items() if team[k] == want and x[7] and k != b]
			ne = min((cheb(me3, (x[3], x[4])) for x in en), default=99)
			e5 = sum(cheb(me3, (x[3], x[4])) <= 5 for x in en)
			a5 = sum(cheb(me3, (x[3], x[4])) <= 5 for x in al)
			C['enemies5>allies5+1'] += e5 > a5 + 1
			C[f'nearest_enemy_r-3={min(ne, 7)}'] += 1
			# who moved: our distance change to the nearest enemy from r-6 to r-3
			p6 = R[r - 6].get(b)
			if p6 and p6[7]:
				d6 = min((cheb((p6[3], p6[4]), (x[3], x[4])) for k, x in R[r - 6].items() if team[k] != want and x[7]), default=99)
				dh6, dh3 = cheb((p6[3], p6[4]), spawn[b]), cheb(me3, spawn[b])
				C['we_moved_away_from_home'] += dh3 > dh6
				C['gap_closed_3+'] += d6 - ne >= 3
			hits = [row for k in range(0, 4) for row in dmg[r - k] if row[5] == 'c' and row[6] == b and row[2] == 'c']
			spells = sum(row[1] == 'Cast ability' for row in hits)
			C['spell_hits>=2'] += spells >= 2
			H['dmg_spell_share'].append(sum(-row[7] for row in hits if row[1] == 'Cast ability') / max(1, sum(-row[7] for row in hits)))
			back = sum(-row[7] for k in range(0, 4) for row in dmg[r - k] if row[2] == 'c' and row[3] == b and row[5] == 'c')
			C['dealt_back_0'] += back == 0
			C[f'type:{types[b]}'] += 1
print(team_sel, 'burst deaths', n)
for k, v in sorted(C.items()):
	print(f'  {k:28s} {v:4d} {100 * v / max(1, n):5.1f}%')
for k, v in H.items():
	print(f'  mean {k}: {sum(v) / max(1, len(v)):.2f}')
