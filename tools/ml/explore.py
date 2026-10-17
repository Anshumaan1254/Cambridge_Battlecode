#!/usr/bin/env python3
"""Randomised-boldness analysis of XML_EXPLORE data (a contextual-bandit / off-policy view of combat()).

usage: explore.py EXPLORE.csv [--by col:edges ...]

The exploration bot multiplies the formula's advantage by exp(u), u ~ Uniform(-0.7, 0.7), drawn once per
encounter (a new encounter after 6 quiet rounds) and logged (u = log(adv / adv_f)). Because u is random and
drawn before the encounter's first decision, the state at the encounter start is independent of u, so the
slope of an outcome on u is an unbiased estimate of what "be bolder than the formula" does in that context.

Encounter outcomes (max over its rows, each row looking 12 rounds ahead):
  D = this body died, K = an enemy within 6 died, A = another ally within 6 died
  R = 25*K - 45*D - 45*A + (gems on killed enemies) - (gems we dropped)   [the stance learner's gem prices]
Prints the slope of each outcome on u (per +1 log-unit of boldness, ~2.7x the advantage) with a game-level
bootstrap interval, overall and by context bins.
"""
import argparse
import numpy as np
import pandas as pd


def encounters(df):
	df = df.copy()
	df['u'] = np.log(df.adv.clip(lower=1e-6) / df.adv_f.clip(lower=1e-6))
	df['fightrow'] = (df.dec == 1).astype(int)
	g = df.groupby(['game', 'body', 'enc'], sort=False)
	first = g.head(1).set_index(['game', 'body', 'enc'])
	agg = g.agg(D=('die', 'max'), K=('kill', 'max'), A=('adie', 'max'), bag=('bag', 'max'), ebag=('ebag', 'max'),
				rows=('die', 'size'), fight_share=('fightrow', 'mean'), hploss=('hploss', 'max'))
	e = first.join(agg, rsuffix='_enc')
	e['R'] = 25 * e.K - 45 * e.D - 45 * e.A + e.ebag - e.bag
	return e.reset_index()


def slope(x, y):
	x = x - x.mean()
	v = (x * x).sum()
	return float((x * (y - y.mean())).sum() / v) if v > 0 else float('nan')


def boot(e, col, n=300, seed=0):
	rng = np.random.default_rng(seed)
	games = e.game.unique()
	idx = {g: np.where(e.game.values == g)[0] for g in games}
	s = []
	for _ in range(n):
		ii = np.concatenate([idx[games[k]] for k in rng.integers(0, len(games), len(games))])
		s.append(slope(e.u.values[ii], e[col].values[ii]))
	return np.nanpercentile(s, 2.5), np.nanpercentile(s, 97.5)


def report(e, label):
	parts = []
	for col in ('D', 'K', 'A', 'R', 'fight_share'):
		b = slope(e.u.values, e[col].values.astype(float))
		lo, hi = boot(e, col)
		parts.append(f'{col} {b:+.3f} [{lo:+.3f},{hi:+.3f}]')
	means = f'D {e.D.mean():.2f} K {e.K.mean():.2f} A {e.A.mean():.2f} R {e.R.mean():+.1f}'
	print(f'{label:34s} n={len(e):5d}  mean {means}  | slope on u: ' + '  '.join(parts))


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('data', nargs='+')
	ap.add_argument('--by', action='append', default=[])
	args = ap.parse_args()
	df = pd.concat([pd.read_csv(p) for p in args.data], ignore_index=True)
	e = encounters(df)
	e['log_adv'] = np.log(e.adv_f.clip(lower=1e-3))
	e['isolated'] = (e.backup == 0).astype(int)
	e['hp_frac'] = e.hp / e.max_hp
	print(f'{len(df)} rows, {e.game.nunique()} games, {len(e)} encounters; u range [{e.u.min():.2f}, {e.u.max():.2f}]')
	report(e, 'all encounters')
	default = ['log_adv:-9,-0.7,-0.2,0.2,0.7,9', 'in_reach:-1,0.5,2', 'isolated:-1,0.5,2', 'killable:-1,0.5,2', 'hp_frac:0,0.4,0.7,1.01',
			   'nE:0,1.5,2.5,9', 'allies_near:-1,0.5,1.5,9']
	for spec in args.by or default:
		col, edges = spec.split(':')
		edges = [float(x) for x in edges.split(',')]
		for lo, hi in zip(edges, edges[1:]):
			sub = e[(e[col] >= lo) & (e[col] < hi)]
			if len(sub) >= 40:
				report(sub, f'{col} in [{lo:g},{hi:g})')


if __name__ == '__main__':
	main()
