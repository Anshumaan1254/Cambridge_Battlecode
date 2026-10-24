#!/usr/bin/env python3
"""Who kills the gem carriers? From tools/top2/draft/roles.mjs output (deathBags = [round, bag, killer]) per study team: deaths of
the study team's bodies carrying >= MIN gems (victim type, bag, killer champion type), the gems stolen per killer type, and the same
for the opponents' carriers killed by the study team. Duplicate games counted once per team.
  python tools/top2/draft/carrier_kills.py ROLES.jsonl [--min 30]"""
import collections, json, sys

AB = {'Ryth': 'Ry', 'VesperVale': 'Ve', 'Vendetta': 'Vd', 'Cassi': 'Cas', 'Issac': 'Iss', 'Stellar': 'St', 'Prism': 'Pr', 'Marcella': 'Ma',
	'Willow': 'Wi', 'Ren': 'Re', 'Varg': 'Va', 'Tavi': 'Ta', 'HeartOfRuin': 'Ho'}


def main():
	a = sys.argv[1:]
	path = a[0]
	mn = int(a[a.index('--min') + 1]) if '--min' in a else 30
	seen = set()
	rows = []
	for line in open(path, encoding='utf-8'):
		r = json.loads(line)
		if (r['key'], r['sig']) in seen:
			continue
		seen.add((r['key'], r['sig']))
		rows.append(r)
	for key in sorted(set(r['key'] for r in rows)):
		rs = [r for r in rows if r['key'] == key]
		lost = collections.defaultdict(lambda: [0, 0, collections.Counter(), collections.Counter()])  # victim type -> deaths, gems, killer types count, killer gems
		won = collections.defaultdict(lambda: [0, 0, collections.Counter(), collections.Counter()])
		big = []
		for r in rs:
			B = {b['i']: b for b in r['bodies']}
			for b in r['bodies']:
				for rd, bag, by in b['deathBags']:
					if bag < mn:
						continue
					kt = AB[B[by]['type']] if isinstance(by, int) and by in B else 'camp/none'
					tgt = lost if b['team'] == r['studyTeam'] else won
					e = tgt[AB[b['type']]]
					e[0] += 1
					e[1] += bag
					e[2][kt] += 1
					e[3][kt] += bag
					if b['team'] == r['studyTeam'] and bag >= 100:
						big.append((r['file'], rd, AB[b['type']], bag, kt, 'W' if r['win'] else 'L'))
		print(f'\n=== {key}: {len(rs)} unique games; carrier deaths with bag >= {mn}')
		print('  study team carriers killed: victim deaths gems | killer types (gems)')
		for v, (n, g, kc, kg) in sorted(lost.items(), key=lambda kv: -kv[1][1]):
			print(f'    {v:4s} {n:3d} {g:5d} | ' + ', '.join(f'{k} {c} ({kg[k]})' for k, c in kc.most_common()))
		print('  opponent carriers killed by the study team: victim deaths gems | killer types (gems)')
		for v, (n, g, kc, kg) in sorted(won.items(), key=lambda kv: -kv[1][1]):
			print(f'    {v:4s} {n:3d} {g:5d} | ' + ', '.join(f'{k} {c} ({kg[k]})' for k, c in kc.most_common()))
		print('  study-team deaths with bag >= 100 (file, round, victim, bag, killer, game result):')
		for x in sorted(big, key=lambda x: -x[3])[:12]:
			print('    ', x)


if __name__ == '__main__':
	main()
