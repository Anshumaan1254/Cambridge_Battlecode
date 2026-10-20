#!/usr/bin/env python3
"""tools/fueltrace.py BOT OPP [OPP...] [--maps GLOB] [--jobs N] [--out DIR] [--release]

Functional and fuel check of one bot (no strength verdict): plays BOT vs each OPP on every map, both sides, and reports per opponent
- games finished, bot faults (engine diagnostics), turn rollovers of our team (lost turns; rounds 1-3 are the heavy opening turns),
- with a FUEL_TRACE build (SRC=bots/X tools/variant.sh NAME --define "FUEL_TRACE 1"): fuel left at the end of our turns (FL lines) and
  the fuel spent by the opponent model's per-turn code (OMF lines: Brain::om_tick_traced): mean, median, p99, max per body-turn.
--release runs as on the platform (debug_block skipped: no trace lines, faults / rollovers still counted).
"""
import glob, json, os, re, subprocess, sys, time, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pct(v, q):
	if not v:
		return 0
	v = sorted(v)
	return v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))]


def our_stdout(rep, side):
	try:
		return zipfile.ZipFile(rep).read(f'team-{side.lower()}.stdout').decode(errors='replace').replace('\x00', '')
	except (KeyError, zipfile.BadZipFile, FileNotFoundError):
		return ''


def rollovers(reps):
	# tools/analysis/rollovers.mjs: one line per replay, "rollovers A=n (rounds 1-3: k) B=m (rounds 1-3: j)"
	out = {}
	for i in range(0, len(reps), 16):
		chunk = reps[i:i + 16]
		p = subprocess.run(['node', os.path.join(ROOT, 'tools/analysis/rollovers.mjs')] + chunk, capture_output=True, text=True, cwd=ROOT)
		for line, rep in zip(p.stdout.strip().split('\n'), chunk):
			m = re.search(r'A=(\d+) \(rounds 1-3: (\d+)\) B=(\d+) \(rounds 1-3: (\d+)\)', line)
			if m:
				out[rep] = tuple(int(x) for x in m.groups())
	return out


def main():
	a = sys.argv[1:]
	opt = lambda k, d: (a.pop(a.index(k) + 1), a.remove(k))[0] if k in a else d
	maps = opt('--maps', 'maps/comp30/*.map26a')
	jobs = int(opt('--jobs', '4'))
	out = opt('--out', os.path.join('/tmp', 'fueltrace'))
	release = '--release' in a
	if release:
		a.remove('--release')
	bot, opps = a[0], a[1:]
	ms = sorted(m for p in maps.split(',') for m in glob.glob(os.path.join(ROOT, p)))
	for b in dict.fromkeys([bot] + opps):
		r = subprocess.run(['cambc', 'build', b], cwd=ROOT, capture_output=True, text=True)
		if r.returncode != 0:
			sys.exit(f'build of {b} failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}')
	run = os.path.join(out, f'{bot}_{int(time.time())}')
	os.makedirs(run, exist_ok=True)
	games = []
	man = os.path.join(run, 'manifest.txt')
	with open(man, 'w') as f:
		for o in opps:
			for m in ms:
				n = os.path.splitext(os.path.basename(m))[0]
				for side, (x, y) in (('A', (bot, o)), ('B', (o, bot))):
					st, rp = os.path.join(run, f'{o}_{n}_{side}.json'), os.path.join(run, f'{o}_{n}_{side}.repl26a')
					f.write(f'{ROOT}/bots/{x} {ROOT}/bots/{y} {m} {rp} --statistics {st} --json\n')
					games.append((o, n, side, st, rp))
	cmd = ['cambc', 'run-batch', man, '--jobs', str(jobs), '--color', 'never'] + (['--release'] if release else [])
	t0 = time.time()
	subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
	ro = rollovers([g[4] for g in games if os.path.exists(g[4])])
	print(f'{bot}: {len(games)} games in {time.time() - t0:.0f}s ({"release" if release else "debug_block on"}), output {run}')
	print(f'{"opponent":10s} {"done":>5s} {"wins":>5s} {"faults":>6s} {"lost turns r>3":>15s} {"r1-3":>5s} {"opp lost r>3":>13s} {"FL mean":>8s} {"FL<10k":>7s} {"OMF mean":>9s} {"p50":>6s} {"p99":>6s} {"max":>6s}')
	for o in opps:
		done = wins = faults = lost = lost0 = olost = 0
		fl, omf = [], []
		for (oo, n, side, st, rp) in games:
			if oo != o or not os.path.exists(st):
				continue
			d = json.load(open(st))
			done += 1
			us = 'teamA' if side == 'A' else 'teamB'
			faults += int(d.get('diagnostics', {}).get('botFaults', {}).get(us, 0))
			wins += d['match']['outcome'] == us
			if rp in ro:
				aa, a0, bb, b0 = ro[rp]
				mine, mine0, theirs, theirs0 = (aa, a0, bb, b0) if side == 'A' else (bb, b0, aa, a0)
				lost += mine - mine0
				lost0 += mine0
				olost += theirs - theirs0
			for line in our_stdout(rp, side).split('\n'):
				if line.startswith('FL '):
					fl.append(int(line.split()[2]))
				elif line.startswith('OMF '):
					omf.append(int(line.split()[3]))
		flm = f'{sum(fl) / len(fl):8.0f}' if fl else '       -'
		fll = f'{sum(x < 10000 for x in fl) / len(fl):7.3f}' if fl else '      -'
		om = f'{sum(omf) / len(omf):9.0f} {pct(omf, 0.5):6d} {pct(omf, 0.99):6d} {max(omf):6d}' if omf else '        -      -      -      -'
		print(f'{o:10s} {done:5d} {wins:5d} {faults:6d} {lost:15d} {lost0:5d} {olost:13d} {flm} {fll} {om}')


if __name__ == '__main__':
	main()
