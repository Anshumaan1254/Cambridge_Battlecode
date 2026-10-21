#!/usr/bin/env python3
"""tools/tracecount.py BOT OPP[,OPP...] PATTERN [--pool FILE | --maps GLOBS] [--jobs N]

Plays BOT (a trace build: EXC_TRACE, OPP_TRACE, LEGEND_TRACE ...) against each OPP on every map, both sides, in debug mode (the
platform's --release mode drops the teams' stdout), and counts BOT's stdout lines matching the regex PATTERN: games with at least one
match, total matches, and the 8 most common matched texts (digits masked). Example (GOD_Improvement_Plan INF-4, exceptions):
  SRC=bots/_x_v10 tools/variant.sh _yexc pd_stat=3 pocket_fix=3 --define EXC_TRACE
  python3 tools/tracecount.py _yexc _v8k1,_pws 'EXC r=' --pool experiments/pools/train156.csv
"""
import collections, glob, os, re, subprocess, sys, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def one(job):
	bot, opp, m, side, tmp, pat = job
	out = os.path.join(tmp, f'{opp}_{os.path.basename(m)}_{side}')
	os.makedirs(out, exist_ok=True)
	a, b = (bot, opp) if side == 'A' else (opp, bot)
	subprocess.run(['cambc', 'run', a, b, '--map', m, '-o', out], cwd=ROOT, capture_output=True, text=True)
	reps = sorted(glob.glob(os.path.join(out, '*.repl26a')))
	if not reps:
		return opp, m, side, None
	t = zipfile.ZipFile(reps[-1]).read(f'team-{side.lower()}.stdout').decode(errors='replace').replace('\x00', '')
	return opp, m, side, [l.strip() for l in t.split('\n') if re.search(pat, l)]


def main():
	a = sys.argv[1:]
	opt = lambda k, d: (a.pop(a.index(k) + 1), a.remove(k))[0] if k in a else d
	globs = opt('--maps', None)
	pool = opt('--pool', None)
	jobs = int(opt('--jobs', '4'))
	bot, opps, pat = a[0], a[1].split(','), a[2]
	if pool:
		maps = [m.strip() for m in open(pool).read().replace('\n', ',').split(',') if m.strip()]
	else:
		maps = sorted(set(sum((glob.glob(g) for g in (globs or 'maps/comp/*.map26a').split(',')), [])))
	maps = [m if os.path.isabs(m) else os.path.join(ROOT, m) for m in maps]
	for b in [bot] + opps:  # build once before the pool: parallel first games of a fresh bot built it concurrently and 2 of 126 failed
		subprocess.run(['cambc', 'build', b], cwd=ROOT, capture_output=True, text=True)
	tmp = tempfile.mkdtemp(prefix='tracecount_')
	res = collections.defaultdict(list)
	with ThreadPoolExecutor(jobs) as ex:
		for opp, m, side, lines in ex.map(one, [(bot, o, m, s, tmp, pat) for o in opps for m in maps for s in 'AB']):
			res[opp].append((m, side, lines))
	for o in opps:
		g = res[o]
		ok = [x for x in g if x[2] is not None]
		hit = [x for x in ok if x[2]]
		c = collections.Counter(re.sub(r'\d+', '#', l) for x in ok for l in x[2])
		print(f'{bot} vs {o}: {len(ok)} games ({len(g) - len(ok)} failed to run), {len(hit)} with a match, {sum(c.values())} matches')
		for k, v in c.most_common(8):
			print(f'  {v:6d}  {k[:150]}')


if __name__ == '__main__':
	main()
