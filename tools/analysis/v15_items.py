#!/usr/bin/env python3
"""GOD v15: items per body from decoded replays (tools/top2/gap/deccache.mjs .json.gz): at checkpoints, shard equivalents, the stat
split (strength / focus / health points), completed emblems with a passive (unique families), loose shards, gold held; per champion type.
    python3 -I tools/analysis/v15_items.py DEC.json.gz... [--ours 0]"""
import collections, gzip, json, sys
FAM = 'MPDTJHB'
NAME = {'M': 'Monster', 'P': 'Power', 'D': 'Durability', 'T': 'Treasure', 'J': 'Jungle', 'H': 'Home', 'B': 'Bruiser'}
ST = 'sfh'
ours = int(sys.argv[sys.argv.index('--ours') + 1]) if '--ours' in sys.argv else 0
files = [a for a in sys.argv[1:] if a.endswith('.gz')]
CP = [300, 600, 1000]
agg = collections.defaultdict(list)
types = collections.defaultdict(lambda: collections.defaultdict(list))
for f in files:
	d = json.loads(gzip.open(f).read())
	B = d['meta']['bodies']
	FR = d['meta']['finalRound']
	byr = {r['r']: r for r in d['rounds'] if r}
	for cp in CP + ['end']:
		r = FR if cp == 'end' else cp
		if r > FR:
			continue
		s = byr.get(r)
		if not s:
			continue
		for c in s['ch']:
			side = 'us' if c[1] == ours else 'them'
			items = c[11] if len(c) > 11 else []
			pts = {'s': 0, 'f': 0, 'h': 0}
			se = 0
			passives = set()
			emblems = []
			loose = 0
			for k, q in items:
				fam, st, emb = FAM[k // 6], ST[(k // 2) % 3], k % 2
				if not emb:
					pts[st] += q; se += q; loose += q
					continue
				se += 5 * q
				emblems += [NAME[fam] + '-' + st] * q
				if fam == 'P':
					pts[st] += 6 * q
				elif fam == 'B':
					pts[st] += 5 * q
					for o in 'sfh':
						if o != st:
							pts[o] += q
				else:
					pts[st] += 5 * q
					passives.add(fam)
			tot = max(1, sum(pts.values()))
			key = f'{side} r{cp}'
			agg[key + ' se'].append(se)
			agg[key + ' hp share'].append(pts['h'] / tot if se else 0)
			agg[key + ' str share'].append(pts['s'] / tot if se else 0)
			agg[key + ' passives'].append(len(passives))
			agg[key + ' loose shards'].append(loose)
			agg[key + ' gold held'].append(c[9])
			if cp == 'end':
				ty = B[c[0]]['type'] if isinstance(B[c[0]], dict) and 'type' in B[c[0]] else c[2]
				types[side][ty].append((se, round(pts['h'] / tot, 2) if se else 0, ''.join(sorted(passives))))
for k in sorted(agg):
	v = agg[k]
	print(f'  {k:28s} {sum(v) / len(v):8.2f}')
for side in ('us', 'them'):
	print(side, 'at the end, per champion: (shard equivalents, health share, passives)')
	for ty, v in sorted(types[side].items(), key=lambda kv: -len(kv[1])):
		se = sum(x[0] for x in v) / len(v); hs = sum(x[1] for x in v) / len(v)
		pc = collections.Counter(x[2] for x in v).most_common(3)
		print(f'    {str(ty):14s} n {len(v):3d}  se {se:5.1f}  hp share {hs:.2f}  passives {pc}')
