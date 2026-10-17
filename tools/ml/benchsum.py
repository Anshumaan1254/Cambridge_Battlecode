#!/usr/bin/env python3
"""Summarise bench.py output directories (BOT_A is team A in NAME_A.json, team B in NAME_B.json).

usage: benchsum.py DIR [DIR ...] [--maps substr,substr] [--pair BASEDIR]
Prints win rate, gem totals, deaths and kills for BOT_A. With --pair, also compares game by game with a
baseline directory over the same (map, side) games: the paired gem-margin difference and its standard error
(a paired test is much more sensitive than two independent win rates on 24 games).
"""
import glob, json, math, os, sys


def load(path):
	with open(path) as f:
		d = json.load(f)
	gems = {t['team']: int(t['submittedGems']) for t in d['teams']}
	per = {'teamA': [0, 0], 'teamB': [0, 0]}
	for c in d['champions']:
		m = c['metrics']
		per[c['team']][0] += int(m['deaths'])
		per[c['team']][1] += int(m['kills'])
	return d['match']['outcome'], d['match']['roundsCompleted'], gems, per


def games(dirname, maps=None):
	out = {}
	for st in sorted(glob.glob(os.path.join(dirname, '*_[AB].json'))):
		base = os.path.basename(st)[:-5]
		name, side = base[:-2], base[-1]
		if maps and not any(m in name for m in maps):
			continue
		oc, rounds, gems, per = load(st)
		us, them = ('teamA', 'teamB') if side == 'A' else ('teamB', 'teamA')
		out[(name, side)] = {
			'win': oc == us, 'loss': oc == them, 'rounds': rounds, 'us': gems[us], 'them': gems[them],
			'deaths': per[us][0], 'kills': per[us][1], 'their_deaths': per[them][0],
		}
	return out


def summary(g):
	n = len(g)
	w = sum(x['win'] for x in g.values())
	return (f"{w}/{n} wins ({100.0 * w / max(1, n):.1f}%)  gems {sum(x['us'] for x in g.values())}-{sum(x['them'] for x in g.values())}"
			f"  deaths {sum(x['deaths'] for x in g.values())}-{sum(x['their_deaths'] for x in g.values())}  kills {sum(x['kills'] for x in g.values())}")


def main():
	args = sys.argv[1:]
	maps = None
	pair = None
	if '--maps' in args:
		i = args.index('--maps'); maps = args[i + 1].split(','); del args[i:i + 2]
	if '--pair' in args:
		i = args.index('--pair'); pair = args[i + 1]; del args[i:i + 2]
	for d in args:
		g = games(d, maps)
		print(f'{os.path.basename(d.rstrip("/"))}: {summary(g)}')
		if pair:
			b = games(pair, maps)
			keys = sorted(set(g) & set(b))
			diffs = [(g[k]['us'] - g[k]['them']) - (b[k]['us'] - b[k]['them']) for k in keys]
			dd = [g[k]['deaths'] - b[k]['deaths'] for k in keys]
			n = len(diffs)
			if n:
				mean = sum(diffs) / n
				sd = math.sqrt(sum((x - mean) ** 2 for x in diffs) / max(1, n - 1))
				flips = sum(1 for k in keys if g[k]['win'] != b[k]['win'])
				print(f'  vs baseline {os.path.basename(pair.rstrip("/"))} on {n} common games: baseline {summary({k: b[k] for k in keys})}')
				print(f'  paired gem margin diff {mean:+.1f} +- {sd / math.sqrt(n):.1f} (s.e.), deaths diff {sum(dd) / n:+.2f}/game, '
					  f'identical games {sum(1 for x in diffs if x == 0)}, result flips {flips} '
					  f'(+{sum(1 for k in keys if g[k]["win"] and not b[k]["win"])} / -{sum(1 for k in keys if b[k]["win"] and not g[k]["win"])})')


if __name__ == '__main__':
	main()
