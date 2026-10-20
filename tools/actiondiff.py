#!/usr/bin/env python3
"""tools/actiondiff.py REF NEW OPP [--maps GLOB] [--jobs N] [--rounds R]

The "all new switches off => same play" check, stronger than identical game results: plays REF vs OPP and NEW vs OPP on every map,
both sides, and compares (1) every replay event of both teams (moves, attacks, casts, priorities, wards, shops, recalls, tributes,
deaths, captures, in order) and (2) when both bots were built with -D SM_TRACE, the 8 shared-memory bytes our team wrote after every
turn (main.cpp prints them inside debug_block, so the trace costs no fuel and changes nothing). Reports the first difference per game.
Build the two bots first, e.g. SRC=bots/god tools/variant.sh _ad_new --define "SM_TRACE 1" (and the same for the reference).
"""
import glob, json, os, subprocess, sys, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(a, b, m, out, rounds):
	cmd = ['cambc', 'run', a, b, '--map', m, '-o', out]
	if rounds:
		cmd += ['--rounds', str(rounds)]
	subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
	reps = sorted(glob.glob(os.path.join(out, '*.repl26a')))
	return reps[-1] if reps else None


def events(rep):
	js = rep + '.json'
	subprocess.run(['node', os.path.join(ROOT, 'tools/replay/decode.mjs'), rep, '--out', js], capture_output=True)
	d = json.load(open(js))
	return d['events'], d['meta']


def sm_lines(rep, side):
	try:
		t = zipfile.ZipFile(rep).read(f'team-{side.lower()}.stdout').decode(errors='replace')
	except (KeyError, zipfile.BadZipFile):
		return []
	return [l.strip() for l in t.replace('\x00', '').split('\n') if l.strip().startswith('SM ')]


def one(job):
	ref, new, opp, m, side, tmp, rounds = job
	res = {}
	for tag, bot in (('ref', ref), ('new', new)):
		out = os.path.join(tmp, f'{tag}_{os.path.basename(m)}_{side}')
		os.makedirs(out, exist_ok=True)
		rep = run(bot, opp, m, out, rounds) if side == 'A' else run(opp, bot, m, out, rounds)
		if not rep:
			return m, side, 'no replay'
		ev, meta = events(rep)
		res[tag] = (ev, sm_lines(rep, side), meta)
	(ea, sa, ma), (eb, sb, mb) = res['ref'], res['new']
	if ma.get('drafts') != mb.get('drafts'):
		return m, side, f"drafts differ: {ma.get('drafts')} vs {mb.get('drafts')}"
	for i, (x, y) in enumerate(zip(ea, eb)):
		if x != y:
			return m, side, f'event {i} differs: {x} vs {y}'
	if len(ea) != len(eb):
		return m, side, f'event count {len(ea)} vs {len(eb)}'
	if sa or sb:
		for i, (x, y) in enumerate(zip(sa, sb)):
			if x != y:
				return m, side, f'shared memory line {i} differs: {x} | {y}'
		if len(sa) != len(sb):
			return m, side, f'shared-memory line count {len(sa)} vs {len(sb)}'
	return m, side, f'identical ({len(ea)} events, {len(sa)} shared-memory dumps)'


def main():
	a = sys.argv[1:]
	opt = lambda k, d: (a.pop(a.index(k) + 1), a.remove(k))[0] if k in a else d
	maps = opt('--maps', 'maps/comp30/*.map26a')
	jobs = int(opt('--jobs', '4'))
	rounds = opt('--rounds', None)
	ref, new, opp = a[:3]
	ms = sorted(m for p in maps.split(',') for m in glob.glob(os.path.join(ROOT, p)))
	for b in dict.fromkeys((ref, new, opp)):  # build once up front: parallel `cambc run`s would race on the same build directory
		subprocess.run(['cambc', 'build', b], cwd=ROOT, capture_output=True)
	tmp = tempfile.mkdtemp(prefix='actiondiff_')
	work = [(ref, new, opp, m, s, tmp, rounds) for m in ms for s in 'AB']
	bad = 0
	with ThreadPoolExecutor(jobs) as ex:
		for m, side, msg in ex.map(one, work):
			ok = msg.startswith('identical')
			bad += not ok
			print(f'{os.path.basename(m):34s} {side}  {msg}')
	print(f'{len(work) - bad} of {len(work)} games identical ({ref} vs {new}, opponent {opp})')
	sys.exit(1 if bad else 0)


if __name__ == '__main__':
	main()
