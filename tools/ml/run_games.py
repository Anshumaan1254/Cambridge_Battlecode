#!/usr/bin/env python3
"""Run a chosen list of single-side games (bench.py always plays both sides of every map).

usage: run_games.py OUTDIR BOT_A BOT_B SIDE MAP [MAP ...]   (SIDE = A, B or alt: alternate by map order)
Writes OUTDIR/NAME_SIDE.json and NAME_SIDE.repl26a with bench.py's naming (BOT_A is team A in NAME_A.*), so
benchsum.py and parse_logs.py read them the same way. Runs one game at a time (--jobs 1) and skips games whose
statistics file already exists (matches are deterministic: never repeat an identical game).
"""
import os, subprocess, sys


def main():
	out, a, b, side = sys.argv[1:5]
	maps = sys.argv[5:]
	os.makedirs(out, exist_ok=True)
	manifest = os.path.join(out, f'manifest_{os.getpid()}.txt')
	n = 0
	with open(manifest, 'w') as f:
		for i, m in enumerate(sorted(maps)):
			name = os.path.splitext(os.path.basename(m))[0]
			s = side if side in ('A', 'B') else ('A' if i % 2 == 0 else 'B')
			x, y = (a, b) if s == 'A' else (b, a)
			st = os.path.abspath(os.path.join(out, f'{name}_{s}.json'))
			rp = os.path.abspath(os.path.join(out, f'{name}_{s}.repl26a'))
			if os.path.exists(st):
				continue
			f.write(f'{os.path.abspath(os.path.join("bots", x))} {os.path.abspath(os.path.join("bots", y))} {os.path.abspath(m)} {rp} --statistics {st} --json\n')
			n += 1
	print(f'{n} games to run', flush=True)
	if n:
		subprocess.run(['cambc', 'build', a], check=True, capture_output=True)
		subprocess.run(['cambc', 'build', b], check=True, capture_output=True)
		p = subprocess.run(['cambc', 'run-batch', manifest, '--jobs', '1', '--color', 'never'], capture_output=True, text=True)
		if p.returncode != 0:
			sys.stderr.write(p.stderr[-2000:])


if __name__ == '__main__':
	main()
