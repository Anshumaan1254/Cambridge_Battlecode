#!/usr/bin/env python3
"""Per-map table: features + each study team's modal draft (pick order) in the window, and a rule search per team/champion:
for every (team, champion) pick that is not constant across maps, the single map-feature threshold (and best 2-feature AND)
that separates maps where the team takes it from maps where it does not (accuracy over maps).
  python tools/top2/draft/map_table.py [--since ISO] [--md]   (--md prints the markdown table used in the report)"""
import collections, itertools, json, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import common as C

FEATS = ['size', 'area', 'W', 'H', 'spawnEuclid', 's2s', 'wall', 'bush', 'hole', 'gems', 'gold', 'gemrate', 'goldrate', 'heavyGemShare',
	'monoGemShare', 'golemGemShare', 'freeGemShare', 'campHP', 'groups', 'mon_groups', 'free_groups', 'n_wolf', 'n_elk', 'n_gem', 'n_gold',
	'n_monolith', 'n_golem', 'midShare', 'altars', 'mincut']


# newest stable draft version per team (tools/top2/draft/team_drafts.py hourly shares; pantheon changed at Oct 23 12:00)
CURRENT = {'pbg': '2026-10-22T18:00', 'ifish': '2026-10-22T08:00', 'pantheon': '2026-10-23T12:00', 'coo': '2026-10-23T09:50',
	'cm': '2026-10-23T09:50', 'nyx': '2026-10-23T09:50'}


def modal_drafts(since):
	allm = C.matches('all', since='2026-10-22T07:00')
	out = collections.defaultdict(dict)
	for key, pre in C.STUDY.items():
		ms = [m for m in allm if m['t'] >= (CURRENT[key] if since == 'current' else since)]
		by = collections.defaultdict(collections.Counter)
		for m in ms:
			if m['a'].startswith(pre):
				by[m['map']][tuple(m['da'])] += 1
			elif m['b'].startswith(pre):
				by[m['map']][tuple(m['db'])] += 1
		for mp, c in by.items():
			out[mp][key] = (list(c.most_common(1)[0][0]), sum(c.values()), c.most_common(1)[0][1])
	return out


def rule_search(F, maps, label):
	"""label: map -> 0/1. Best single threshold rule and best AND of two thresholds; returns list of (acc, text)."""
	best = []
	for f in FEATS:
		vals = sorted(set(F[m][f] for m in maps if F[m].get(f) is not None))
		for i in range(len(vals) - 1):
			th = (vals[i] + vals[i + 1]) / 2
			for sgn in ('>', '<'):
				pred = {m: (F[m][f] > th) if sgn == '>' else (F[m][f] < th) for m in maps}
				acc = sum(pred[m] == label[m] for m in maps)
				best.append((acc, f'{f} {sgn} {th:g}', pred))
	best.sort(key=lambda x: -x[0])
	singles = best[:400]
	pairs = []
	for (a1, t1, p1), (a2, t2, p2) in itertools.combinations(singles[:120], 2):
		pr = {m: p1[m] and p2[m] for m in maps}
		acc = sum(pr[m] == label[m] for m in maps)
		pairs.append((acc, f'{t1} AND {t2}'))
		pr = {m: p1[m] or p2[m] for m in maps}
		acc = sum(pr[m] == label[m] for m in maps)
		pairs.append((acc, f'{t1} OR {t2}'))
	pairs.sort(key=lambda x: -x[0])
	return [(a, t) for a, t, _ in singles[:3]], pairs[:3]


def main():
	a = sys.argv[1:]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	since = opt('--since', 'current')
	F = C.mapfeat()
	D = modal_drafts(since)
	maps = sorted(F)
	if '--md' in a:
		print('| map | size | W x H | spawn d | hole | bush | wall | gems | heavy | mono | ' + ' | '.join(C.STUDY) + ' |')
		print('|' + '---|' * (10 + len(C.STUDY)))
		for mp in sorted(maps, key=lambda m: (F[m]['size'], m)):
			f = F[mp]
			cells = []
			for k in C.STUDY:
				if k in D[mp]:
					d, n, nm = D[mp][k]
					cells.append(C.comp_str(d) + ('' if nm == n else f' ({nm}/{n})'))
				else:
					cells.append('-')
			print(f"| {mp} | {f['size']} | {f['W']}x{f['H']} | {f['spawnEuclid']} | {f['hole']:.2f} | {f['bush']:.2f} | {f['wall']:.2f} | "
				f"{f['gems']} | {f['heavyGemShare']:.2f} | {f['monoGemShare']:.2f} | " + ' | '.join(cells) + ' |')
		return
	for key in C.STUDY:
		print('=' * 90)
		print(key)
		for size in (3, 4, 5):
			ms = [m for m in maps if F[m]['size'] == size and key in D[m]]
			sets = collections.Counter(C.comp_set(D[m][key][0]) for m in ms)
			print(f'  size {size}: {dict(sets)}')
		# per champion: in which maps taken (considering only maps of size >= 4 where variation exists)
		for ch in range(12):
			for size in (3, 4, 5):
				ms = [m for m in maps if F[m]['size'] == size and key in D[m]]
				if not ms:
					continue
				lab = {m: ch in D[m][key][0] for m in ms}
				k = sum(lab.values())
				if 0 < k < len(ms):
					s, p = rule_search(F, ms, lab)
					yes = [m for m in ms if lab[m]]
					print(f'  {C.NAMES[ch]} on size {size}: taken on {k}/{len(ms)} maps: {", ".join(yes)}')
					print('     best single: ' + ' | '.join(f'{t} ({a}/{len(ms)})' for a, t in s))
					print('     best pair:   ' + ' | '.join(f'{t} ({a}/{len(ms)})' for a, t in p))
		# pick order variants: slot of Vesper etc
		for ch in range(12):
			pos = collections.Counter()
			for m in maps:
				if key in D[m] and ch in D[m][key][0]:
					pos[D[m][key][0].index(ch) + 1] += 1
			if len(pos) > 1:
				ms = [m for m in maps if key in D[m] and ch in D[m][key][0]]
				first = pos.most_common(1)[0][0]
				lab = {m: D[m][key][0].index(ch) + 1 == first for m in ms}
				s, p = rule_search(F, ms, lab)
				other = [f'{m}:p{D[m][key][0].index(ch) + 1}' for m in ms if not lab[m]]
				print(f'  {C.NAMES[ch]} slot: {dict(pos)}; not p{first} on {", ".join(other)}')
				print('     best single: ' + ' | '.join(f'{t} ({a}/{len(ms)})' for a, t in s))


if __name__ == '__main__':
	main()
