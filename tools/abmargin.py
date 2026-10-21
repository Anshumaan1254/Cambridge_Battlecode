#!/usr/bin/env python3
"""tools/abmargin.py BOT OPP [--pool FILE] [--base BASE] [--boot N]

Gem-margin statistics from the ledger (current source hashes only; GOD_Improvement_Plan INF-2 / §8.4).
- BOT OPP: the head-to-head margin (our banked gems minus theirs at the end) averaged per map over both sides (the side advantage
  cancels), with a bootstrap 95% interval over maps, plus the win rate.
- --base BASE: the PAIRED design: BOT vs OPP and BASE vs OPP on the same map and side; per pair the margin difference
  (BOT's minus BASE's), mean with a bootstrap 95% interval over maps. "superior": the interval's lower bound > 0; "non-inferior": lower
  bound >= -10 gems (plan §8.4).
"""
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger


def margin(r):
	# final banked gems, ours minus theirs (a game won on gems ends at the winner's 1,000+; at round 2,000 the banked totals stand)
	g = r['gems']
	return g[0] - g[1]


def boot(vals, n, seed=7):
	if not vals:
		return 0.0, 0.0, 0.0
	rnd = random.Random(seed)
	m = sum(vals) / len(vals)
	bs = sorted(sum(rnd.choice(vals) for _ in vals) / len(vals) for _ in range(n))
	return m, bs[int(0.025 * n)], bs[int(0.975 * n) - 1]


def main():
	a = sys.argv[1:]
	opt = lambda k, d: (a.pop(a.index(k) + 1), a.remove(k))[0] if k in a else d
	pool = opt('--pool', None)
	base = opt('--base', None)
	n = int(opt('--boot', '2000'))
	bot, opp = a[0], a[1]
	keep = None
	if pool:
		keep = {os.path.splitext(os.path.basename(m.strip()))[0] for m in open(pool).read().replace('\n', ',').split(',') if m.strip()}
	r = ledger.current_rows(bot, opp)
	if keep is not None:
		r = {k: v for k, v in r.items() if k[0] in keep}
	if base is None:
		per = {}
		for (m, s), v in r.items():
			per.setdefault(m, []).append(margin(v))
		vals = [sum(x) / len(x) for x in per.values() if len(x) == 2]
		mu, lo, hi = boot(vals, n)
		w = sum(v['win'] for v in r.values())
		print(f'{bot} vs {opp}: {len(vals)} maps, wins {w}/{len(r)}, mean margin per map {mu:+.1f} gems, 95% [{lo:+.1f}, {hi:+.1f}]')
		return
	b = ledger.current_rows(base, opp)
	per = {}
	for k, v in r.items():
		if k in b:
			per.setdefault(k[0], []).append(margin(v) - margin(b[k]))
	vals = [sum(x) / len(x) for x in per.values()]
	mu, lo, hi = boot(vals, n)
	same = sum(1 for k, v in r.items() if k in b and v['gems'] == b[k]['gems'] and v['rounds'] == b[k]['rounds'])
	wb = sum(r[k]['win'] for k in r if k in b)
	wa = sum(b[k]['win'] for k in r if k in b)
	verdict = 'superior' if lo > 0 else 'non-inferior' if lo >= -10 else 'not shown non-inferior'
	print(f'{bot} vs {base} (paired, both vs {opp}): {len(vals)} maps, {sum(len(x) for x in per.values())} pairs ({same} identical), '
		f'wins {wb} vs {wa}; margin difference per map {mu:+.1f} gems, 95% [{lo:+.1f}, {hi:+.1f}]: {verdict}')


if __name__ == '__main__':
	main()
