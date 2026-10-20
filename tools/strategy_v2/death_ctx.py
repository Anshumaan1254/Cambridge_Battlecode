#!/usr/bin/env python3
"""Context of every death in decoded ladder games (session 13): what the body was doing in the rounds before it died.

usage: python3 -I tools/strategy_v2/death_ctx.py DMG_DIR INDEX_JSON [--team us|them] [--skip contest] [--list]
INDEX_JSON: experiments/ladder_oct19b/index.json (gives our side per game). Categories (first match wins):
  camp      the killing blow came from a camp
  pair      Cassi/Issac killed with its partner the same round, the partner took the killing blow (count once: the trigger)
  low_out   below 35% health 6 rounds before death with an enemy champion within 6 (stayed out low)
  burst     at or above 60% health 3 rounds before death
  fleeing   walked toward home over the last 4 rounds (distance to spawn fell by 2+)
  diving    walked away from home over the last 4 rounds (distance rose by 2+)
  standing  otherwise
Also: fought back (dealt champion damage in the last 6 rounds), enemy hitters in the last 3 rounds, camp damage taken.
"""
import collections, glob, json, os, sys


def cheb(a, b):
	return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
	a = sys.argv[1:]
	team_sel = 'us'
	skip = []
	lst = False
	if '--team' in a:
		i = a.index('--team'); team_sel = a[i + 1]; del a[i:i + 2]
	if '--skip' in a:
		i = a.index('--skip'); skip = a[i + 1].split(','); del a[i:i + 2]
	if '--list' in a:
		a.remove('--list'); lst = True
	ddir, idxp = a
	idx = {r['group'] + '_' + r['nn']: r for r in json.load(open(idxp))}
	cat = collections.Counter()
	extra = collections.Counter()
	per_map = collections.defaultdict(collections.Counter)
	n = 0
	for f in sorted(glob.glob(os.path.join(ddir, '*.json'))):
		name = os.path.basename(f)[:-5]
		mp = name.split('_')[-1]
		if mp in skip:
			continue
		r0 = idx[name[:11]]
		us = 0 if r0['side'] == 'A' else 1
		want = us if team_sel == 'us' else 1 - us
		d = json.load(open(f))
		R = {x['r']: x for x in d['rounds']}
		spawn = {}
		for c in d['rounds'][0]['ch']:
			spawn[c[0]] = (c[3], c[4])
		team = {c[0]: c[1] for c in d['rounds'][0]['ch']}
		types = {b['index']: b['type'] for b in d['meta']['bodies']}
		dmg_by_round = collections.defaultdict(list)
		for row in d['dmg']:
			dmg_by_round[row[0]].append(row)
		for e in d['events']:
			if e['k'] != 'Death' or e.get('team') is None:
				continue
		# deaths: a body alive at r-1 and dead at r
		rounds = sorted(R)
		for i in range(1, len(rounds)):
			r = rounds[i]
			prev = {c[0]: c for c in R[rounds[i - 1]]['ch']}
			for c in R[r]['ch']:
				b = c[0]
				if team[b] != want or c[7] or not prev.get(b) or not prev[b][7]:
					continue
				n += 1
				hist = [R.get(r - k) for k in range(1, 7)]
				ch_at = lambda rr, bb: next((x for x in rr['ch'] if x[0] == bb), None) if rr else None
				killer = None
				for row in dmg_by_round[r]:
					if row[5] == 'c' and row[6] == b and row[8] == 0:
						killer = row
				t = types[b]
				partner = {'Cassi': 'Issac', 'Issac': 'Cassi'}.get(t)
				pidx = next((x for x in team if team[x] == want and types[x] == partner), None) if partner else None
				hp6 = ch_at(hist[5], b); hp3 = ch_at(hist[2], b)
				enemies6 = 99
				if hp6:
					for x in hist[5]['ch']:
						if team[x[0]] != want and x[7]:
							enemies6 = min(enemies6, cheb((x[3], x[4]), (hp6[3], hp6[4])))
				fought = any(row[2] == 'c' and row[3] == b and row[5] == 'c' for k in range(0, 7) for row in dmg_by_round[r - k])
				hitters = set(row[3] for k in range(0, 4) for row in dmg_by_round[r - k] if row[5] == 'c' and row[6] == b and row[2] == 'c')
				campdmg = -sum(row[7] for k in range(0, 7) for row in dmg_by_round[r - k] if row[5] == 'c' and row[6] == b and row[2] == 'm')
				p4 = ch_at(hist[3], b); p1 = ch_at(hist[0], b)
				dh = (cheb((p1[3], p1[4]), spawn[b]) - cheb((p4[3], p4[4]), spawn[b])) if p4 and p1 and p4[7] and p1[7] else 0
				if killer and killer[2] == 'm':
					k = 'camp'
				elif pidx is not None and any(row[6] == pidx and row[8] == 0 and row[5] == 'c' for row in dmg_by_round[r]) and not (killer and killer[2] == 'c'):
					k = 'pair_follow'
				elif hp6 and hp6[5] < 0.35 * hp6[6] and enemies6 <= 6:
					k = 'low_out'
				elif hp3 and hp3[5] >= 0.6 * hp3[6]:
					k = 'burst'
				elif dh <= -2:
					k = 'fleeing'
				elif dh >= 2:
					k = 'diving'
				else:
					k = 'standing'
				cat[k] += 1
				per_map[mp][k] += 1
				extra['fought_back'] += fought
				extra['hitters>=2'] += len(hitters) >= 2
				extra['camp_dmg>200'] += campdmg > 200
				if lst:
					print(f'{name} r{r} {t:8s} {k:11s} hp6={hp6[5] if hp6 else -1}/{hp6[6] if hp6 else -1} enemy6={enemies6} fought={int(fought)} hitters={len(hitters)} campdmg={campdmg} dh={dh}')
	print(f'{team_sel}: {n} deaths')
	for k, v in cat.most_common():
		print(f'  {k:12s} {v:4d} {100 * v / max(1, n):5.1f}%')
	for k, v in extra.items():
		print(f'  [{k}] {v} ({100 * v / max(1, n):.1f}%)')
	print('per map:', {m: dict(c) for m, c in sorted(per_map.items())})


if __name__ == '__main__':
	main()
