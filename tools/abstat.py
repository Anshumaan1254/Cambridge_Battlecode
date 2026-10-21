#!/usr/bin/env python3
"""tools/abstat.py BOT OPP [--pool FILE] [--by-dir] [--ledger DIR]

Head-to-head statistics of BOT vs OPP from the ledger (rows on BOT's and OPP's current source hashes only):
- games, wins, win rate with a 95% Wilson interval;
- per map, both sides played: maps won from both sides (2-0), split (1-1), lost from both sides (0-2), and a two-sided
  sign test on 2-0 vs 0-2. The paired count cancels the side advantage (on many maps the side decides a mirror game:
  1-1 maps carry no information about which bot is better);
- --pool FILE: only the maps listed (comma- or newline-separated paths, as passed to ledger.py --maps);
- --by-dir: the same per map folder.
A bot is "clearly better" when the 95% interval of its win rate lies above 50% and the sign test is significant.
"""
import glob, json, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wilson(w, n, z=1.96):
	if n == 0:
		return 0.0, 0.0
	p = w / n
	d = 1 + z * z / n
	c = (p + z * z / (2 * n)) / d
	h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
	return c - h, c + h


def sign_p(a, b):
	# two-sided exact binomial test of a successes in a + b trials at p = 0.5
	n = a + b
	if n == 0:
		return 1.0
	k = min(a, b)
	s = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
	return min(1.0, 2 * s)


def latest_ledger():
	# the ledger of the installed engine (tools/ledger.py's rule), else the newest per-version folder
	try:
		sys.path.insert(0, os.path.join(ROOT, 'tools'))
		import ledger
		return ledger.LEDGER
	except Exception:
		ds = glob.glob(os.path.join(ROOT, 'experiments/results/ledger_v3_0_*'))
		key = lambda d: tuple(int(x) for x in re.findall(r'\d+', os.path.basename(d)))
		return max(ds, key=key) if ds else os.path.join(ROOT, 'experiments/results/ledger_v3')


def rows(ledger, bot, opp):
	f = os.path.join(ledger, f'{bot}_vs_{opp}.jsonl')
	if not os.path.exists(f):
		return []
	rs = [json.loads(l) for l in open(f) if l.strip()]
	if not rs:
		return []
	bh, oh = rs[-1].get('bot_hash'), rs[-1].get('opp_hash')
	out = {}
	for r in rs:
		if r.get('bot_hash') == bh and r.get('opp_hash') == oh:
			out[(r['map'], r['side'])] = r
	return list(out.values())


def summary(rs, label):
	n = len(rs)
	w = sum(1 for r in rs if r.get('win'))
	lo, hi = wilson(w, n)
	by = {}
	for r in rs:
		by.setdefault(r['map'], []).append(r)
	two = sum(1 for v in by.values() if len(v) == 2 and all(r.get('win') for r in v))
	zero = sum(1 for v in by.values() if len(v) == 2 and not any(r.get('win') for r in v))
	split = sum(1 for v in by.values() if len(v) == 2) - two - zero
	dpm = sum(r['deaths'][0] for r in rs), sum(r['deaths'][1] for r in rs)
	print(f'{label:28s} {w:4d}/{n:<4d} {w / max(1, n):6.3f}  95% [{lo:.3f}, {hi:.3f}]  maps 2-0 {two:3d}  1-1 {split:3d}  0-2 {zero:3d}  '
		f'sign p {sign_p(two, zero):.4f}  deaths {dpm[0]}-{dpm[1]}')


def main():
	a = sys.argv[1:]
	opt = lambda k, d: (a.pop(a.index(k) + 1), a.remove(k))[0] if k in a else d
	pool = opt('--pool', None)
	ledger = opt('--ledger', latest_ledger())
	by_dir = '--by-dir' in a
	if by_dir:
		a.remove('--by-dir')
	bot, opp = a[0], a[1]
	rs = rows(ledger, bot, opp)
	if pool:
		names = [m.strip() for m in open(pool).read().replace('\n', ',').split(',') if m.strip()]
		stems = {os.path.splitext(os.path.basename(m))[0]: m for m in names}
		rs = [r for r in rs if r['map'] in stems]
		where = {r['map']: os.path.dirname(stems[r['map']]) for r in rs}
	else:
		where = {}
		for m in glob.glob(os.path.join(ROOT, 'maps', '**', '*.map26a'), recursive=True):
			where.setdefault(os.path.splitext(os.path.basename(m))[0], os.path.relpath(os.path.dirname(m), ROOT))
	summary(rs, f'{bot} vs {opp}')
	if by_dir:
		dirs = {}
		for r in rs:
			dirs.setdefault(where.get(r['map'], '?'), []).append(r)
		for d in sorted(dirs):
			summary(dirs[d], '  ' + d)


if __name__ == '__main__':
	main()
