#!/usr/bin/env python3
"""Gem race audit of bench.py run directories: where each team's gems came from and where they went.
   python3 tools/analysis/gem_race.py [--comp] [--lost] [--games] DIR...
Per game (side A = first bot of the run name is team A): gems collected (camp rewards), banked, lost (collected -
banked - still carried: died with them), earned gold, monster damage, kills, and the round each team reached
250/500/750 banked. Summary per run directory over the selected games. --comp: official maps only; --lost: only
games our bot lost; --games: one line per game."""
import glob, json, os, sys

COMP = {os.path.splitext(os.path.basename(m))[0] for m in glob.glob(os.path.join(os.path.dirname(__file__), '..', '..', 'maps', 'comp', '*.map26a'))}

def team_metrics(d, team):
	m = {'col': 0, 'sub': 0, 'carry': 0, 'gold': 0, 'mdmg': 0, 'kills': 0, 'deaths': 0}
	for c in d['champions']:
		if c['team'] != team:
			continue
		x = c['metrics']
		m['col'] += int(float(x['collectedGems'])); m['sub'] += int(float(x['submittedGems'])); m['carry'] += int(float(x['gems']))
		m['gold'] += int(float(x['earnedGold'])); m['mdmg'] += int(float(x['monsterDamageDone']))
		m['kills'] += int(float(x['kills'])); m['deaths'] += int(float(x['deaths']))
	m['lost'] = m['col'] - m['sub'] - m['carry']
	return m

def reach(d, team, marks=(250, 500, 750)):
	out = []
	for t in d['teamTimelines']:
		if t['metric'] != 'submittedGems' or t['owner'] != team:
			continue
		r, vals = 0, []
		for run in t['runs']:
			vals.append((r, int(float(run['value'])))); r += int(run['duration'])
		for mk in marks:
			out.append(next((rr for rr, v in vals if v >= mk), None))
	return out

def main():
	args = [a for a in sys.argv[1:] if not a.startswith('--')]
	comp, lost_only, games = '--comp' in sys.argv, '--lost' in sys.argv, '--games' in sys.argv
	dirs = []
	for p in args:
		dirs += [p] if os.path.exists(os.path.join(p, 'manifest.txt')) else sorted(d for d in glob.glob(os.path.join(p, '*')) if os.path.exists(os.path.join(d, 'manifest.txt')))
	for d in dirs:
		agg = {'n': 0, 'w': 0}
		su, st = {}, {}
		for f in sorted(glob.glob(os.path.join(d, '*_[AB].json'))):
			name, side = os.path.basename(f)[:-7], os.path.basename(f)[-6]
			if comp and name not in COMP:
				continue
			j = json.load(open(f))
			us, them = ('teamA', 'teamB') if side == 'A' else ('teamB', 'teamA')
			won = j['match']['outcome'] == us
			if lost_only and won:
				continue
			mu, mt = team_metrics(j, us), team_metrics(j, them)
			agg['n'] += 1; agg['w'] += won
			for k in mu:
				su[k] = su.get(k, 0) + mu[k]; st[k] = st.get(k, 0) + mt[k]
			if games:
				ru, rt = reach(j, us), reach(j, them)
				print(f"  {name:22s} {side} {'W' if won else 'L'} r{j['match']['roundsCompleted']:4d} banked {mu['sub']:4d}-{mt['sub']:4d} collected {mu['col']:4d}-{mt['col']:4d} "
					  f"lost {mu['lost']:3d}-{mt['lost']:3d} gold {mu['gold']:5d}-{mt['gold']:5d} kills {mu['kills']:2d}-{mt['kills']:2d} mdmg {mu['mdmg'] // 1000:4d}k-{mt['mdmg'] // 1000:4d}k "
					  f"250/500/750 at {ru} vs {rt}")
		n = max(1, agg['n'])
		tag = os.path.basename(d.rstrip('/')).rsplit('_', 1)[0]
		print(f"{tag:26s} games {agg['n']:3d} won {agg['w']:3d} | per game: collected {su.get('col', 0) / n:5.0f}-{st.get('col', 0) / n:5.0f} banked {su.get('sub', 0) / n:5.0f}-{st.get('sub', 0) / n:5.0f} "
			  f"lost {su.get('lost', 0) / n:4.0f}-{st.get('lost', 0) / n:4.0f} gold {su.get('gold', 0) / n:5.0f}-{st.get('gold', 0) / n:5.0f} kills {su.get('kills', 0) / n:4.1f}-{st.get('kills', 0) / n:4.1f} "
			  f"mdmg {su.get('mdmg', 0) / n / 1000:5.0f}k-{st.get('mdmg', 0) / n / 1000:5.0f}k")

if __name__ == '__main__':
	main()
