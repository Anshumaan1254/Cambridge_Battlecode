#!/usr/bin/env python3
"""First contacts in decoded ladder games: a body whose nearest enemy champion comes within 5 after 5+ rounds with none
within 7. Who closed the gap that round (our step, theirs, both), who hit first within the next 3 rounds, and the champion
damage both sides dealt in those 3 rounds. usage: python3 -I tools/strategy_v2/contact.py DMG_DIR INDEX_JSON [--skip contest]"""
import collections, glob, json, os, sys


def cheb(a, b):
	return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


a = sys.argv[1:]
skip = []
if '--skip' in a:
	i = a.index('--skip'); skip = a[i + 1].split(','); del a[i:i + 2]
ddir, idxp = a
idx = {r['group'] + '_' + r['nn']: r for r in json.load(open(idxp))}
C = {'us': collections.Counter(), 'them': collections.Counter()}
D = {'us': collections.Counter(), 'them': collections.Counter()}
for f in sorted(glob.glob(os.path.join(ddir, '*.json'))):
	name = os.path.basename(f)[:-5]
	if name.split('_')[-1] in skip:
		continue
	us = 0 if idx[name[:11]]['side'] == 'A' else 1
	d = json.load(open(f))
	R = {x['r']: {c[0]: c for c in x['ch']} for x in d['rounds']}
	team = {c[0]: c[1] for c in d['rounds'][0]['ch']}
	dmg = collections.defaultdict(list)
	for row in d['dmg']:
		if row[2] == 'c' and row[5] == 'c' and row[7] < 0 and team[row[3]] != team[row[6]]:
			dmg[row[0]].append(row)
	last_near = {}
	rounds = sorted(R)
	for r in rounds[1:]:
		if r - 1 not in R:
			continue
		for b, c in R[r].items():
			if not c[7]:
				continue
			side = 'us' if team[b] == us else 'them'
			en = [x for k, x in R[r].items() if team[k] != team[b] and x[7]]
			if not en:
				continue
			e = min(en, key=lambda x: cheb((c[3], c[4]), (x[3], x[4])))
			dnow = cheb((c[3], c[4]), (e[3], e[4]))
			if dnow <= 7:
				prev_quiet = r - last_near.get(b, -100) > 5
				last_near[b] = r
				if not prev_quiet or dnow > 5:
					continue
				p = R[r - 1].get(b); pe = R[r - 1].get(e[0])
				if not p or not pe or not p[7] or not pe[7]:
					continue
				we_moved = cheb((p[3], p[4]), (pe[3], pe[4])) > cheb((c[3], c[4]), (pe[3], pe[4]))
				they_moved = cheb((p[3], p[4]), (pe[3], pe[4])) > cheb((p[3], p[4]), (e[3], e[4]))
				C[side]['contacts'] += 1
				C[side]['closer:' + ('both' if we_moved and they_moved else 'me' if we_moved else 'them' if they_moved else 'none')] += 1
				# first hit among the two teams' champions within 4 tiles of either, next 3 rounds
				first = None; dm = collections.Counter()
				for k in range(0, 4):
					for row in dmg.get(r + k, []):
						ta = team[row[3]]
						near = cheb((row[9], row[10]), (c[3], c[4])) <= 6
						if not near:
							continue
						who = 'me' if ta == team[b] else 'them'
						if first is None:
							first = who
						dm[who] += -row[7]
				C[side]['first_hit:' + (first or 'none')] += 1
				D[side]['dealt'] += dm['me']; D[side]['taken'] += dm['them']
for s in C:
	n = C[s]['contacts']
	print(s, n, ' '.join(f'{k}={v} ({100 * v / max(1, n):.0f}%)' for k, v in sorted(C[s].items()) if k != 'contacts'),
		  f"| 4-round champ dmg dealt/taken per contact {D[s]['dealt'] / max(1, n):.0f}/{D[s]['taken'] / max(1, n):.0f}")
