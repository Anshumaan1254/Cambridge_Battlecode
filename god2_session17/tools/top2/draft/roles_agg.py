#!/usr/bin/env python3
"""Aggregate tools/top2/draft/roles.mjs output: per study team and champion, the role profile (share of the team's banked gems,
captured gems, captured gold, champion damage done / taken, camp damage, kills, deaths, stuns; mean / max bag, final max HP),
plus the same champions in the hands of their opponents, and per-game win / loss splits. Duplicate games (same map, final round,
scores, outcome) are counted once per team.
  python tools/top2/draft/roles_agg.py ROLES.jsonl [--team pbg] [--split]"""
import collections, json, sys

TYPES = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']
ABBR = {'Ryth': 'Ry', 'VesperVale': 'Ve', 'Vendetta': 'Vd', 'Cassi': 'Cas', 'Issac': 'Iss', 'Stellar': 'St', 'Prism': 'Pr', 'Marcella': 'Ma',
	'Willow': 'Wi', 'Ren': 'Re', 'Varg': 'Va', 'Tavi': 'Ta', 'HeartOfRuin': 'Ho'}
SH = ['banked', 'capG', 'capGold', 'dDone', 'dTaken', 'campDmg', 'kills', 'deaths', 'stunDone', 'bagLost']


def load(path):
	seen = set()
	out = []
	for line in open(path, encoding='utf-8'):
		r = json.loads(line)
		if (r['key'], r['sig']) in seen:
			continue
		seen.add((r['key'], r['sig']))
		out.append(r)
	return out


def profile(rows, team_sel, filt=lambda r: True):
	"""team_sel(r) -> team index (0/1) whose bodies we profile. Returns per type: n games, means, shares."""
	acc = collections.defaultdict(lambda: collections.defaultdict(float))
	n = collections.Counter()
	for r in rows:
		if not filt(r):
			continue
		t = team_sel(r)
		bs = [b for b in r['bodies'] if b['team'] == t]
		tot = {k: sum(b[k] for b in bs) for k in SH}
		for b in bs:
			ty = b['type']
			n[ty] += 1
			a = acc[ty]
			for k in SH:
				a[k] += b[k]
				a['sh_' + k] += b[k] / tot[k] if tot[k] else 0
			for k in ('meanBag', 'maxBag', 'maxHp', 'nBank', 'recalls', 'locks', 'alive', 'healDone', 'gold'):
				a[k] += b[k]
			a['fair'] += 1 / len(bs)
	return n, acc


def show(n, acc, title):
	print(title)
	print('  champ  n   | bank%  capG%  gold%  dmgDone% dmgTaken% camp%  kills% deaths% | bank/g capG/g kills/g deaths/g bagLost/g '
		'meanBag maxBag maxHp stuns/g locks/g | fair%')
	for ty in sorted(n, key=lambda t: -acc[t]['sh_banked'] / n[t]):
		a, k = acc[ty], n[ty]
		print(f"  {ABBR[ty]:4s} {k:4d} | {100 * a['sh_banked'] / k:5.0f}  {100 * a['sh_capG'] / k:5.0f}  {100 * a['sh_capGold'] / k:5.0f}  "
			f"{100 * a['sh_dDone'] / k:7.0f}  {100 * a['sh_dTaken'] / k:8.0f}  {100 * a['sh_campDmg'] / k:5.0f}  {100 * a['sh_kills'] / k:6.0f} "
			f"{100 * a['sh_deaths'] / k:6.0f} | {a['banked'] / k:6.0f} {a['capG'] / k:6.0f} {a['kills'] / k:7.1f} {a['deaths'] / k:7.1f} "
			f"{a['bagLost'] / k:8.0f} {a['meanBag'] / k:8.1f} {a['maxBag'] / k:6.0f} {a['maxHp'] / k:5.0f} {a['stunDone'] / k:6.1f} "
			f"{a['locks'] / k:6.1f} | {100 * a['fair'] / k:4.0f}")


def main():
	a = sys.argv[1:]
	path = a[0]
	opt = lambda k, d: a[a.index(k) + 1] if k in a else d
	only = opt('--team', None)
	rows = load(path)
	keys = sorted(set(r['key'] for r in rows))
	for key in keys:
		if only and key != only:
			continue
		rs = [r for r in rows if r['key'] == key]
		w = sum(r['win'] for r in rs)
		n, acc = profile(rs, lambda r: r['studyTeam'])
		show(n, acc, f'\n=== {key}: {len(rs)} unique games, won {w}')
		if '--split' in a:
			n, acc = profile(rs, lambda r: r['studyTeam'], lambda r: r['win'] == 1)
			show(n, acc, f'  -- {key} wins')
			n, acc = profile(rs, lambda r: r['studyTeam'], lambda r: r['win'] == 0)
			show(n, acc, f'  -- {key} losses')
		n, acc = profile(rs, lambda r: 1 - r['studyTeam'])
		show(n, acc, f'  -- opponents of {key}')


if __name__ == '__main__':
	main()
