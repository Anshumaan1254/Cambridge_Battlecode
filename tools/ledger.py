#!/usr/bin/env python3
"""Resumable per-game results ledger for A/B panels (survives session limits and container restarts).

Every finished game is one JSON line in experiments/results/ledger/<BOT>_vs_<OPP>.jsonl, keyed by
(map, side, release) and by the SOURCE HASH of both bots, so a result is only reused for the exact code it was played
with (a rebuilt bot never inherits old results). Replays and full statistics stay in /tmp (large) and are not committed.

  python3 tools/ledger.py run BOT OPP --maps 'maps/comp/*.map26a' [--jobs 2] [--chunk 8]
      plays only the missing games, in chunks of --chunk maps (a session cut loses at most one chunk), appending each
      chunk's rows as soon as it finishes. Re-running after an interruption resumes where it stopped.
  python3 tools/ledger.py import DIR [--bot BOT --opp OPP]
      imports a bench.py --out directory (or one run inside it) that was finished before the ledger existed.
      Refuses runs older than the bot's last build (their code is not the code now in bots/).
  python3 tools/ledger.py status BOT OPP --maps GLOB     # done / missing games and the win rate of complete cells
  python3 tools/ledger.py table BOT --opps _rm,_ST,... --maps GLOB   # one line per opponent

The row fields are the bench.py summary: win, rounds, gems and deaths and gold for both teams, faults.
"""
import argparse, glob, hashlib, json, os, shutil, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench import load_stats  # noqa: E402  (the same parser the panels use)

def _engine_version():
	try:
		return subprocess.run(['cambc', '--version'], capture_output=True, text=True).stdout.split()[-1]
	except (OSError, IndexError):
		return '2'


ENGINE = _engine_version()


def _engine_ledger():
	"""Results depend on the engine as much as on the bots: each engine gets its own ledger directory, so no game played on another
	engine is reused (the rows are keyed by bot sources only). 2.x -> ledger/, 3.0.1 -> ledger_v3/ (patch 3.0), any later engine ->
	ledger_v<full version> (3.0.2 = the Heart of Ruin hotfix, same SDK headers as 3.0.1: a major-version key reused 3.0.1 rows). LEDGER_DIR overrides."""
	if os.environ.get('LEDGER_DIR'):
		return os.environ['LEDGER_DIR']
	try:
		major = int(ENGINE.split('.')[0])
	except ValueError:
		major = 2
	sub = 'ledger' if major < 3 else 'ledger_v3' if ENGINE == '3.0.1' else 'ledger_v' + ENGINE.replace('.', '_')
	return os.path.join(ROOT, 'experiments', 'results', sub)


LEDGER = _engine_ledger()
RUNS = os.path.join('/tmp', 'ledger_runs')


def src_hash(bot):
	"""Hash of the bot's sources (what the wasm was built from). A different hash = different code = no reuse."""
	h = hashlib.sha1()
	for f in sorted(glob.glob(os.path.join(ROOT, 'bots', bot, 'src', '*'))):
		h.update(os.path.basename(f).encode())
		h.update(open(f, 'rb').read())
	return h.hexdigest()[:12]


def built_mtime(bot):
	w = os.path.join(ROOT, 'bots', bot, '.cambc', 'build', 'bot-injected.wasm')
	return os.path.getmtime(w) if os.path.exists(w) else 0.0


def ledger_file(bot, opp):
	os.makedirs(LEDGER, exist_ok=True)
	return os.path.join(LEDGER, f'{bot}_vs_{opp}.jsonl')


def read_rows(bot, opp):
	path = ledger_file(bot, opp)
	if not os.path.exists(path):
		return []
	return [json.loads(line) for line in open(path) if line.strip()]


def current_rows(bot, opp, release=False):
	"""Latest row per (map, side) that was played with the sources now in bots/ (older builds never count)."""
	hb, ho = src_hash(bot), src_hash(opp)
	latest = {}
	for r in read_rows(bot, opp):
		if r['bot_hash'] == hb and r['opp_hash'] == ho and r['release'] == release:
			latest[(r['map'], r['side'])] = r
	return latest


def done_keys(bot, opp, release=False):
	return set(current_rows(bot, opp, release))


def row_from_stats(bot, opp, map_name, side, path, release, when):
	s = load_stats(path)
	us, them = ('teamA', 'teamB') if side == 'A' else ('teamB', 'teamA')
	return {'bot': bot, 'opp': opp, 'bot_hash': src_hash(bot), 'opp_hash': src_hash(opp), 'map': map_name, 'side': side,
			'release': release, 'win': s['outcome'] == us, 'loss': s['outcome'] == them, 'rounds': s['rounds'],
			'gems': [s['gems'][us], s['gems'][them]], 'deaths': [s['per'][us]['deaths'], s['per'][them]['deaths']],
			'kills': [s['per'][us]['kills'], s['per'][them]['kills']], 'gold': [s['per'][us]['gold'], s['per'][them]['gold']],
			'faults': int(s['faults'].get(us, 0)), 'when': when, 'engine': ENGINE}


def append(bot, opp, rows):
	with open(ledger_file(bot, opp), 'a') as f:
		for r in rows:
			f.write(json.dumps(r) + '\n')


def maps_of(glob_pat):
	return sorted({m for p in glob_pat.split(',') for m in glob.glob(os.path.join(ROOT, p))
				   if not os.path.basename(m).startswith('zz_')})


def cmd_run(a):
	for b in (a.bot, a.opp):
		if not os.path.isdir(os.path.join(ROOT, 'bots', b)):
			sys.exit(f'bots/{b} does not exist')
		r = subprocess.run(['cambc', 'build', b] + (['--release'] if a.release else []), cwd=ROOT, capture_output=True, text=True)
		if r.returncode != 0:
			sys.exit(f'build {b} failed:\n{r.stdout[-2000:]}{r.stderr[-2000:]}')
	maps = maps_of(a.maps)
	# Rows are keyed by the map's file name only: a copy with the same name in another folder would reuse the other
	# map's games (session 13: maps/comp30/ambush reused maps/comp/ambush rows). Refuse such pools.
	stems = {os.path.splitext(os.path.basename(m))[0] for m in maps}
	def copies(s):
		return {open(f, 'rb').read() for f in glob.glob(os.path.join(ROOT, 'maps', '**', s + '.map26a'), recursive=True)}
	clash = sorted(s for s in stems if len(copies(s)) > 1)  # identical copies (maps/var17 vs maps/ct) are harmless
	if clash:
		sys.exit(f'map names used by more than one file under maps/ (rows would mix): {", ".join(clash)}; rename the copies')
	done = done_keys(a.bot, a.opp, a.release)
	todo = [(m, s) for m in maps for s in 'AB' if (os.path.splitext(os.path.basename(m))[0], s) not in done]
	print(f'{a.bot} vs {a.opp}: {len(maps) * 2 - len(todo)} of {len(maps) * 2} games already in the ledger, {len(todo)} to play', flush=True)
	by_map = {}
	for m, s in todo:
		by_map.setdefault(m, []).append(s)
	items = list(by_map.items())
	for c in range(0, len(items), a.chunk):
		chunk = items[c:c + a.chunk]
		run_dir = os.path.join(RUNS, f'{a.bot}_vs_{a.opp}_{int(time.time() * 1000)}')
		os.makedirs(run_dir)
		manifest = os.path.join(run_dir, 'manifest.txt')
		meta = []
		with open(manifest, 'w') as f:
			for m, sides in chunk:
				mn = os.path.splitext(os.path.basename(m))[0]
				for s in sides:
					a_, b_ = (a.bot, a.opp) if s == 'A' else (a.opp, a.bot)
					st = os.path.join(run_dir, f'{mn}_{s}.json')
					rp = os.path.join(run_dir, f'{mn}_{s}.repl26a')
					f.write(f'{ROOT}/bots/{a_} {ROOT}/bots/{b_} {m} {rp} --statistics {st} --json\n')
					meta.append((mn, s, st))
		cmd = ['cambc', 'run-batch', manifest, '--jobs', str(a.jobs), '--color', 'never'] + (['--release'] if a.release else [])
		subprocess.run(cmd, capture_output=True, text=True)
		when = time.strftime('%Y-%m-%dT%H:%M:%S')
		rows = []
		for mn, s, st in meta:
			if os.path.exists(st):
				try:
					rows.append(row_from_stats(a.bot, a.opp, mn, s, st, a.release, when))
				except (ValueError, KeyError, OSError):
					pass
		append(a.bot, a.opp, rows)
		if a.keep:
			# --keep DIR: the replays (~50 KB each) and a compact copy of each statistics file (no timelines / events /
			# heatmaps, ~10 KB) under DIR/<bot>_vs_<opp>/, for tracing the games later (the run directory is deleted below).
			kd = os.path.join(a.keep, f'{a.bot}_vs_{a.opp}')
			os.makedirs(kd, exist_ok=True)
			for mn, s, st in meta:
				rp = st[:-5] + '.repl26a'
				if os.path.exists(rp):
					shutil.copy(rp, os.path.join(kd, f'{mn}_{s}.repl26a'))
				if os.path.exists(st):
					try:
						d = json.load(open(st))
						json.dump({k: d[k] for k in ('match', 'teams', 'champions', 'roster', 'diagnostics') if k in d}, open(os.path.join(kd, f'{mn}_{s}.json'), 'w'))
					except (ValueError, OSError):
						pass
		missing = len(meta) - len(rows)
		print(f'  chunk {c // a.chunk + 1}/{(len(items) + a.chunk - 1) // a.chunk}: {len(rows)} games saved'
			+ (f', {missing} without statistics (not saved; they will be retried)' if missing else ''), flush=True)
		shutil.rmtree(run_dir, ignore_errors=True)
	cmd_status(a)


def cmd_import(a):
	paths = [a.dir] if os.path.exists(os.path.join(a.dir, 'manifest.txt')) else \
		sorted(d for d in glob.glob(os.path.join(a.dir, '*')) if os.path.exists(os.path.join(d, 'manifest.txt')))
	for d in paths:
		name = os.path.basename(d)
		if '_vs_' not in name:
			continue
		bot, rest = name.split('_vs_', 1)
		opp = rest.rsplit('_', 1)[0]
		if a.bot and (bot, opp) != (a.bot, a.opp):
			continue
		stamp = float(name.rsplit('_', 1)[1])  # bench.py names runs <a>_vs_<b>_<unix seconds>
		if built_mtime(bot) > stamp:
			print(f'skip {name}: bots/{bot} was rebuilt after this run (its results are for older code)')
			continue
		rows = []
		for st in sorted(glob.glob(os.path.join(d, '*_[AB].json'))):
			mn, s = os.path.basename(st)[:-7], os.path.basename(st)[-6]
			try:
				rows.append(row_from_stats(bot, opp, mn, s, st, False, time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(stamp))))
			except (ValueError, KeyError, OSError):
				pass
		have = done_keys(bot, opp)
		rows = [r for r in rows if (r['map'], r['side']) not in have]
		append(bot, opp, rows)
		print(f'{name}: imported {len(rows)} games for {bot} vs {opp}')


def cmd_status(a):
	maps = maps_of(a.maps)
	n = len(maps) * 2
	seen = {k: r for k, r in current_rows(a.bot, a.opp, a.release).items() if k[0] in {os.path.splitext(os.path.basename(m))[0] for m in maps}}
	w = sum(1 for r in seen.values() if r['win'])
	print(f'{a.bot} vs {a.opp}: {len(seen)} of {n} games on the current code, win {w}/{len(seen)}'
		+ (f' = {100 * w / max(1, len(seen)):.1f}%' if seen else '') + ('  (complete)' if len(seen) == n else '  (incomplete)'))


def cmd_table(a):
	maps = maps_of(a.maps)
	names = {os.path.splitext(os.path.basename(m))[0] for m in maps}
	for opp in a.opps.split(','):
		if not opp:
			continue
		seen = {k: r for k, r in current_rows(a.bot, opp, a.release).items() if k[0] in names}
		n = len(maps) * 2
		w = sum(1 for r in seen.values() if r['win'])
		deaths = [sum(r['deaths'][0] for r in seen.values()), sum(r['deaths'][1] for r in seen.values())]
		status = 'complete' if len(seen) == n else f'{len(seen)}/{n}'
		print(f'{a.bot} vs {opp:8s} win {100 * w / max(1, len(seen)):5.1f}%  ({w}/{len(seen)})  deaths {deaths[0]}-{deaths[1]}  {status}')


def main():
	ap = argparse.ArgumentParser()
	sub = ap.add_subparsers(dest='cmd', required=True)
	r = sub.add_parser('run'); r.add_argument('bot'); r.add_argument('opp')
	r.add_argument('--maps', default='maps/comp/*.map26a'); r.add_argument('--jobs', type=int, default=2)
	r.add_argument('--chunk', type=int, default=8); r.add_argument('--release', action='store_true')
	r.add_argument('--keep', default=None, help='keep replays and compact statistics under this directory')
	r.set_defaults(fn=cmd_run)
	i = sub.add_parser('import'); i.add_argument('dir'); i.add_argument('--bot'); i.add_argument('--opp')
	i.set_defaults(fn=cmd_import)
	st = sub.add_parser('status'); st.add_argument('bot'); st.add_argument('opp')
	st.add_argument('--maps', default='maps/comp/*.map26a'); st.add_argument('--release', action='store_true')
	st.set_defaults(fn=cmd_status)
	t = sub.add_parser('table'); t.add_argument('bot'); t.add_argument('--opps', required=True)
	t.add_argument('--maps', default='maps/comp/*.map26a'); t.add_argument('--release', action='store_true')
	t.set_defaults(fn=cmd_table)
	a = ap.parse_args()
	a.fn(a)


if __name__ == '__main__':
	main()
