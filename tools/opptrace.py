#!/usr/bin/env python3
"""tools/opptrace.py BOT OPP [--maps GLOBS|--pool FILE] [--jobs N] [--out FILE] [--release]

Plan timelines of the v9 opponent model (opp9.cpp, P.opp_plan). BOT must be built with -D OPP_TRACE (one line per 30-round window:
"OPP r=<round> plan=<name> contact=... run=... cusum=... bal=... home=... losses=... their=.../r ours=.../r bag=... divers=...").
Plays BOT vs OPP on every map, both sides, reads BOT's team stdout from the replay and prints per opponent:
- games, share of games that ever left FARM (the false-alarm rate against a mirror farmer), share of windows per plan,
  first round a counter plan was entered (median), plan changes per game;
- with --out, one JSON line per game (map, side, win, rounds, the window rows).
"""
import glob, json, os, re, statistics, subprocess, sys, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINE = re.compile(r'OPP r=(\d+) plan=(\w+) (.*)')


def parse(t):
	rows = []
	for l in t.split('\n'):
		m = LINE.search(l)
		if not m:
			continue
		r = {'round': int(m.group(1)), 'plan': m.group(2)}
		for kv in m.group(3).split():
			k, _, v = kv.partition('=')
			v = v.split('/')[0]
			try:
				r[k] = float(v)
			except ValueError:
				pass
		rows.append(r)
	return rows


def one(job):
	bot, opp, m, side, tmp, rel = job
	out = os.path.join(tmp, f'{os.path.basename(m)}_{side}')
	os.makedirs(out, exist_ok=True)
	a, b = (bot, opp) if side == 'A' else (opp, bot)
	cmd = ['cambc', 'run', a, b, '--map', m, '-o', out] + (['--release'] if rel else [])
	subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
	reps = sorted(glob.glob(os.path.join(out, '*.repl26a')))
	if not reps:
		return None
	z = zipfile.ZipFile(reps[-1])
	t = z.read(f'team-{side.lower()}.stdout').decode(errors='replace').replace('\x00', '')
	win = None
	try:
		meta = json.loads(z.read('match.json')) if 'match.json' in z.namelist() else None
		if meta:
			win = meta.get('winner') == ('teamA' if side == 'A' else 'teamB')
	except Exception:
		pass
	return {'map': os.path.splitext(os.path.basename(m))[0], 'side': side, 'opp': opp, 'win': win, 'rows': parse(t)}


def main():
	a = sys.argv[1:]
	opt = lambda k, d: (a.pop(a.index(k) + 1), a.remove(k))[0] if k in a else d
	globs = opt('--maps', None)
	pool = opt('--pool', None)
	jobs = int(opt('--jobs', '4'))
	outf = opt('--out', None)
	rel = '--release' in a
	if rel:
		a.remove('--release')
	bot, opps = a[0], a[1].split(',')
	if pool:
		maps = [m.strip() for m in open(pool).read().replace('\n', ',').split(',') if m.strip()]
	else:
		maps = sorted(set(sum((glob.glob(g) for g in (globs or 'maps/comp/*.map26a').split(',')), [])))
	maps = [m if os.path.isabs(m) else os.path.join(ROOT, m) for m in maps]
	tmp = tempfile.mkdtemp(prefix='opptrace_')
	res = []
	with ThreadPoolExecutor(jobs) as ex:
		for r in ex.map(one, [(bot, o, m, s, os.path.join(tmp, o), rel) for o in opps for m in maps for s in 'AB']):
			if r:
				res.append(r)
	if outf:
		with open(outf, 'a') as f:
			for r in res:
				f.write(json.dumps(r) + '\n')
	for o in opps:
		g = [r for r in res if r['opp'] == o]
		if not g:
			continue
		left = [r for r in g if any(w['plan'] != 'FARM' for w in r['rows'])]
		win = {}
		n = 0
		firsts, changes = [], []
		for r in g:
			prev = 'FARM'
			c = 0
			for w in r['rows']:
				win[w['plan']] = win.get(w['plan'], 0) + 1
				n += 1
				if w['plan'] != prev:
					c += 1
				prev = w['plan']
			changes.append(c)
			f = [w['round'] for w in r['rows'] if w['plan'] != 'FARM']
			if f:
				firsts.append(f[0])
		share = ' '.join(f'{k} {v / max(1, n):.2f}' for k, v in sorted(win.items(), key=lambda x: -x[1]))
		med = statistics.median(firsts) if firsts else '-'
		print(f'{bot} vs {o}: {len(g)} games, left FARM in {len(left)} ({len(left) / len(g):.0%}), first counter plan r{med}, '
			f'changes/game {statistics.mean(changes):.1f}; windows: {share}')


if __name__ == '__main__':
	main()
