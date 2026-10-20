#!/usr/bin/env python3
"""tools/omtrace.py BOT OPP LABEL [--maps GLOB] [--jobs N] [--out FILE] [--switch "R:LABEL,R:LABEL"]

Opponent-model calibration and evaluation data. Plays BOT (built with -D OPP_TRACE and opp_model 1) against OPP on every map, both sides,
and appends one JSON line per classification window to FILE (default experiments/results/om/traces.jsonl): the window's signals, the
model's evidence / scores / archetype, the game (map, side, opponent) and the TRUE label of the opponent's style in that window (LABEL,
or for a switching proxy the label of the style active at that round, --switch "300:invader,800:deathball").
Also one JSON line per game with the result (win, rounds, gems). tools/omreport.py turns the file into the confusion matrix and the
rounds-to-detect table.
"""
import glob, json, os, re, subprocess, sys, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OM = re.compile(r'OM r=(\d+) (.*) ev=([^ ]*) s=([^ ]*) arc=(\w+) plan=(\d+)')


def parse(line):
	m = OM.search(line)
	if not m:
		return None
	r = {'round': int(m.group(1))}
	for kv in m.group(2).split():
		k, _, v = kv.partition('=')
		if k == 'ward':
			a = v.split('/')
			r['ward_home'], r['ward_altar'], r['ward_bush'] = map(int, a)
		elif k == 'cus':
			a = v.split('/')
			r['cus_pos'], r['cus_neg'] = map(float, a)
		else:
			try:
				r[k] = int(v)
			except ValueError:
				r[k] = float(v)
	r['ev'] = [float(x) for x in m.group(3).strip(',').split(',') if x]
	r['s'] = [float(x) for x in m.group(4).strip(',').split(',') if x]
	r['arc'], r['plan'] = m.group(5), int(m.group(6))
	return r


def label_at(base, switches, rnd):
	lab = base
	for r, l in switches:
		if rnd > r:  # a window ending at round r covers rounds r-20..r-1
			lab = l
	return lab


def one(job):
	bot, opp, m, side, tmp = job
	out = os.path.join(tmp, f'{os.path.basename(m)}_{side}')
	os.makedirs(out, exist_ok=True)
	a, b = (bot, opp) if side == 'A' else (opp, bot)
	res = subprocess.run(['cambc', 'run', a, b, '--map', m, '-o', out], cwd=ROOT, capture_output=True, text=True)
	reps = sorted(glob.glob(os.path.join(out, '*.repl26a')))
	if not reps:
		return m, side, [], None
	t = zipfile.ZipFile(reps[-1]).read(f'team-{side.lower()}.stdout').decode(errors='replace').replace('\x00', '')
	rows = [p for p in (parse(l) for l in t.split('\n')) if p]
	# result line: "  A    bot   gems ..." from the cambc table
	gems = {}
	for l in res.stdout.split('\n'):
		mm = re.match(r'\s+([AB])\s+(\S+)\s+(\d+)', l)
		if mm:
			gems[mm.group(1)] = int(mm.group(3))
	win = None
	if 'A' in gems and 'B' in gems:
		us, them = (gems['A'], gems['B']) if side == 'A' else (gems['B'], gems['A'])
		win = us > them
	return m, side, rows, {'gems_us': gems.get(side), 'gems_them': gems.get('B' if side == 'A' else 'A'), 'win': win}


def main():
	a = sys.argv[1:]
	opt = lambda k, d: (a.pop(a.index(k) + 1), a.remove(k))[0] if k in a else d
	maps = opt('--maps', 'maps/comp30/*.map26a')
	jobs = int(opt('--jobs', '4'))
	out = opt('--out', os.path.join(ROOT, 'experiments/results/om/traces.jsonl'))
	sw = opt('--switch', '')
	switches = sorted((int(x.split(':')[0]), x.split(':')[1]) for x in sw.split(',') if x)
	bot, opp, label = a[:3]
	for x in dict.fromkeys((bot, opp)):
		subprocess.run(['cambc', 'build', x], cwd=ROOT, capture_output=True)
	ms = sorted(m for p in maps.split(',') for m in glob.glob(os.path.join(ROOT, p)))
	tmp = tempfile.mkdtemp(prefix='omtrace_')
	os.makedirs(os.path.dirname(out), exist_ok=True)
	n = 0
	with ThreadPoolExecutor(jobs) as ex, open(out, 'a') as f:
		for m, side, rows, res in ex.map(one, [(bot, opp, m, s, tmp) for m in ms for s in 'AB']):
			mp = os.path.basename(m).replace('.map26a', '')
			for r in rows:
				r.update({'map': mp, 'side': side, 'bot': bot, 'opp': opp, 'label': label_at(label, switches, r['round'])})
				f.write(json.dumps(r) + '\n')
			f.write(json.dumps({'game': True, 'map': mp, 'side': side, 'bot': bot, 'opp': opp, 'label': label, 'switches': switches, **(res or {})}) + '\n')
			n += 1
			print(f'{mp:28s} {side}  windows {len(rows):3d}  {res}', flush=True)
	print(f'{n} games -> {out}')


if __name__ == '__main__':
	main()
