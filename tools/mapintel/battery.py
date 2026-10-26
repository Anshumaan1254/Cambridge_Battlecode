#!/usr/bin/env python3
"""Simulation batteries of MAPAnalysis.md 5.5 for ANY bot (the user's new bot; nothing here assumes a bot from bots/). SIMULATED labels.

    python3 tools/mapintel/battery.py --bot NAME [--from SRC] [--opps self,idle,starter] [--maps 'maps/s3/*.map26a'] [--jobs N]
                                      [--rosters tools/mapintel/data/battery_rosters.json] [--per-map 8] [--skip-outcome]
                                      [--skip-roster] [--no-replays] [--quick] [--work mapintel_work/battery] [--out-dir .]

Patch 2.0.0: cambc 4.0.0 (engine 2.0.0); the default maps are the 70 of maps/s3 (the sprint-3 pool: the 40 official maps + 30 new).
Batteries (every game both sides, release mode as on the platform, through tools/ledger.py run ... --keep):
  * outcome: NAME (its own draft) against each opponent of --opps on every map: wins, gem margin, deaths, pace, tiebreak share.
    Opponent tokens: 'self' (NAME against itself), 'idle' (tools/mapintel/cpp/idle: drafts, never acts: NAME's unopposed pace),
    'starter' (the cambc 4.0.0 starter bot from a scratch `cambc init`), or the name of any bot folder in bots/.
  * roster: both teams' rosters forced. Per map the C = --per-map candidate rosters of --rosters (LEARNED: what strong teams drafted on
    that map; COMPUTED: balanced over kit classes, the only kind on the 30 new maps; tools/mapintel/battery_rosters.py), every pair
    (i < j) of candidates against each other with NAME playing both teams: roster i vs roster j on every map and both sides (8 per map:
    28 pairs x 70 maps x 2 sides = 3,920 games). The rosters are forced by the bot under test: its
    draft must call mapintel::forced_pick() (tools/mapintel/cpp/mapintel/force_roster.h; README); the script writes mi_roster.h beside
    that header in one copy of the bot per roster slot (bots/_mib_<NAME>_r<k>) and checks in every kept game that the engine's drafts
    equal the forced rosters (it stops with an error if they do not).
Output: one archive OUT_DIR/mapintel_battery_<NAME>_<UTC stamp>.tar.gz (ledger rows, compact statistics, replays unless --no-replays,
the rosters used, meta). Upload that file. A cut run resumes: the ledger skips games already played on the same sources."""
import argparse, filecmp, glob, json, os, platform, re, shutil, subprocess, sys, tarfile, tempfile, time, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import PICK_NAMES, BODY_NAMES, pick_bodies  # noqa: E402

CAMBC = "4.0.0"  # the CLI of patch 2.0.0 (engine 2.0.0): the platform's engine
QUICK = ("00elkring", "01hooks", "02arena")  # --quick: two maps of the old pool and one new one (02arena: 30 x 30, 3 a side)


def die(msg):
	sys.stderr.write("ERROR: " + msg + "\n")
	sys.exit(1)


def run(cmd, env=None, cwd=ROOT):
	return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)


def build(name):
	r = run(["cambc", "build", name, "--release"])
	if r.returncode != 0:
		die(f"build of bots/{name} failed:\n{(r.stdout + r.stderr)[-3000:]}")


def copy_bot(src, dst):
	d = os.path.join(ROOT, "bots", dst)
	shutil.rmtree(os.path.join(d, "src"), ignore_errors=True)
	os.makedirs(d, exist_ok=True)
	shutil.copytree(os.path.join(ROOT, "bots", src, "src"), os.path.join(d, "src"))
	return d


def same_tree(a, b):
	"""True when folders a and b hold the same files with the same bytes."""
	def files(d):
		return {os.path.relpath(os.path.join(r, f), d) for r, _, fs in os.walk(d) for f in fs}
	if not os.path.isdir(b):
		return False
	fa = files(a)
	return fa == files(b) and all(filecmp.cmp(os.path.join(a, f), os.path.join(b, f), shallow=False) for f in fa)


def bodynorm(s):
	return re.sub(r"[^a-z]", "", s.lower())


def ledger_run(bot, opp, maps_glob, jobs, keep, env):
	cmd = [sys.executable, os.path.join(ROOT, "tools", "ledger.py"), "run", bot, opp, "--maps", maps_glob, "--jobs", str(jobs), "--release"]
	if keep:
		cmd += ["--keep", keep]
	r = run(cmd, env=env)
	last = (r.stdout.strip().splitlines() or [""])[-1]
	print(f"   {last}", flush=True)
	m = re.search(r"(\d+) of (\d+) games on the current code", last)
	if r.returncode != 0 or not m or int(m.group(1)) == 0:
		die(f"ledger run {bot} vs {opp} produced no games:\n{(r.stdout + r.stderr)[-3000:]}")
	return int(m.group(1)), int(m.group(2))


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("--bot", required=True)
	ap.add_argument("--from", dest="from_bot", default="", help="first make bots/BOT a battery-ready copy of bots/FROM (prepare_bot.py)")
	ap.add_argument("--opps", default="self,idle,starter")
	ap.add_argument("--maps", default="maps/s3/*.map26a", help="comma list of globs (repository-relative); default: the 70-map pool")
	ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
	ap.add_argument("--rosters", default="tools/mapintel/data/battery_rosters.json")
	ap.add_argument("--per-map", type=int, default=8)
	ap.add_argument("--skip-outcome", action="store_true")
	ap.add_argument("--skip-roster", action="store_true")
	ap.add_argument("--no-replays", action="store_true")
	ap.add_argument("--quick", action="store_true", help="function test: 3 maps (2 old, 1 new), 2 roster slots, opponents idle only")
	ap.add_argument("--work", default=os.path.join(ROOT, "mapintel_work", "battery"), help="work folder (resumable; one per cambc version)")
	ap.add_argument("--out-dir", default=ROOT)
	ap.add_argument("--split-mb", type=float, default=20.0, help="also cut the archive into parts of this size for uploading (0 = no parts)")
	a = ap.parse_args()
	t0 = time.time()
	if a.from_bot:
		r = run([sys.executable, os.path.join(ROOT, "tools/mapintel/prepare_bot.py"), a.from_bot, a.bot])
		if r.returncode != 0:
			die(r.stdout + r.stderr)
		print(r.stdout.strip())
	if " " in ROOT:
		die(f"the repository path has a space ({ROOT}); cambc run-batch manifests split on spaces: clone it into a path without spaces")
	if not os.path.isdir(os.path.join(ROOT, "bots", a.bot, "src")):
		die(f"bots/{a.bot}/src does not exist")
	r = run(["cambc", "--version"])
	ver = r.stdout.strip().split()[-1] if r.stdout.strip() else "?"
	print(f"cambc {ver}; {os.cpu_count()} CPUs, {a.jobs} jobs; {platform.platform()}")
	if ver != CAMBC:
		print(f"WARNING: cambc {ver} (expected {CAMBC}, the platform's engine: pip install cambc=={CAMBC})")
	maps = sorted({m for g in a.maps.split(",") if g for m in glob.glob(os.path.join(ROOT, g)) if not os.path.basename(m).startswith("zz_")})
	if a.quick:
		maps = [m for m in maps if os.path.splitext(os.path.basename(m))[0] in QUICK] or maps[:3]
		a.per_map = min(a.per_map, 2)
		a.opps = "idle"
	if not maps:
		die(f"no maps match {a.maps}")
	work = os.path.abspath(a.work)
	# the ledger reuses games by the bots' source hashes only: a work folder of another cambc (engine) is moved aside, never reused
	mark = os.path.join(work, "cambc.txt")
	old = open(mark).read().strip() if os.path.exists(mark) else "3.0.5 or older" if os.path.isdir(os.path.join(work, "ledger")) else ver
	if old != ver:
		aside = work + "_cambc_" + re.sub(r"[^0-9A-Za-z]+", "_", old).strip("_") + time.strftime("_%Y%m%d_%H%M%S")
		os.rename(work, aside)
		print(f"   {work} held games of cambc {old}: moved to {aside}")
	os.makedirs(work, exist_ok=True)
	open(mark, "w").write(ver + "\n")
	maps_glob = ",".join(os.path.relpath(m, ROOT).replace(os.sep, "/") for m in maps)
	env = dict(os.environ, LEDGER_DIR=os.path.join(work, "ledger"), PYTHONIOENCODING="utf-8")
	keep = stats_keep = os.path.join(work, "keep")  # compact statistics always (roster check); replays archived unless --no-replays
	print(f"maps: {len(maps)}")

	# SDK / cmake glue and the starter bot from a scratch cambc init (the repository's sdk/ and cmake/ are git-ignored)
	init = tempfile.mkdtemp(prefix="mi_init_")
	run(["cambc", "init", "--yes", "."], cwd=init)
	for d in ("sdk", "cmake"):
		if os.path.isdir(os.path.join(init, d)):
			if not same_tree(os.path.join(init, d), os.path.join(ROOT, d)):  # replace only when different (a running build keeps its files)
				shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)
				shutil.copytree(os.path.join(init, d), os.path.join(ROOT, d))
				print(f"   {d}/ replaced by cambc {ver}'s")
		elif not os.path.isdir(os.path.join(ROOT, d)):
			die(f"`cambc init` wrote no {d}/ and the repository has none (network?)")
	pm, pool = os.path.join(init, "maps"), os.path.join(ROOT, "maps", "s3")
	plat = sorted(f for f in os.listdir(pm) if f.endswith(".map26a")) if os.path.isdir(pm) else []
	if plat and os.path.isdir(pool):  # `cambc init` downloads the platform's current pool: is maps/s3 still that pool?
		new = [f for f in plat if not os.path.exists(os.path.join(pool, f)) or not filecmp.cmp(os.path.join(pm, f), os.path.join(pool, f), shallow=False)]
		gone = sorted(f for f in os.listdir(pool) if f.endswith(".map26a") and f not in plat)
		if new or gone:
			print(f"WARNING: the platform's map pool ({len(plat)} maps) differs from maps/s3: new or changed {new or '-'}, gone {gone or '-'}"
				  " (git pull; or say so when you upload the archive)")
		else:
			print(f"   the platform's map pool = maps/s3 ({len(plat)} maps)")
	build(a.bot)
	print(f"1. bots/{a.bot} builds (release)")
	meta = {"bot": a.bot, "cambc": ver, "cpus": os.cpu_count(), "jobs": a.jobs, "platform": platform.platform(), "args": vars(a), "maps": len(maps),
			"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cells": []}
	sys.path.insert(0, os.path.join(ROOT, "tools"))
	import ledger  # noqa: E402
	meta["bot_hash"] = ledger.src_hash(a.bot)

	# 2. outcome battery
	if not a.skip_outcome:
		for tok in [t for t in a.opps.split(",") if t]:
			if tok == "self":
				opp = a.bot
			elif tok == "idle":
				opp = "_mi_idle"
				os.makedirs(os.path.join(ROOT, "bots", opp, "src"), exist_ok=True)
				shutil.copy(os.path.join(ROOT, "tools/mapintel/cpp/idle/main.cpp"), os.path.join(ROOT, "bots", opp, "src", "main.cpp"))
			elif tok == "starter":
				st = os.path.join(init, "bots", "starter-cpp", "src")
				if not os.path.isdir(st):
					print("   WARNING: no starter bot from cambc init; opponent 'starter' skipped")
					continue
				opp = "_mi_starter"
				shutil.rmtree(os.path.join(ROOT, "bots", opp, "src"), ignore_errors=True)
				shutil.copytree(st, os.path.join(ROOT, "bots", opp, "src"))
			else:
				opp = tok
				if not os.path.isdir(os.path.join(ROOT, "bots", opp, "src")):
					die(f"opponent bots/{opp} does not exist")
			build(opp)
			n, tot = ledger_run(a.bot, opp, maps_glob, a.jobs, keep, env)
			meta["cells"].append({"battery": "outcome", "bot": a.bot, "opp": opp, "games": n, "of": tot})
		print(f"2. outcome battery done ({time.time() - t0:.0f} s)")

	# 3. roster battery: both rosters forced by the bot under test
	if not a.skip_roster:
		R = json.load(open(os.path.join(ROOT, a.rosters)))
		names = [os.path.splitext(os.path.basename(m))[0] for m in maps]
		miss = [n for n in names if n not in R["maps"]]
		if miss:
			die(f"maps not in {a.rosters}: {', '.join(miss)} (regenerate it with tools/mapintel/battery_rosters.py)")
		C = min(a.per_map, min(len(R["maps"][n]["rosters"]) for n in names))
		hdr = None
		for d, _, fs in os.walk(os.path.join(ROOT, "bots", a.bot, "src")):
			if "force_roster.h" in fs:
				hdr = os.path.relpath(d, os.path.join(ROOT, "bots", a.bot, "src"))
		if hdr is None:
			die(f"bots/{a.bot}/src has no mapintel/force_roster.h: copy tools/mapintel/cpp/mapintel/ into its src/ and call "
				"mapintel::forced_pick() at the top of its draft turn (tools/mapintel/README.md)")
		var = []
		for k in range(C):
			v = f"_mib_{a.bot}_r{k}"
			d = copy_bot(a.bot, v)
			lines = []
			for n in names:
				e = R["maps"][n]
				picks = e["rosters"][k]["picks"]
				lines.append(f"\t{{ 0x{e['fingerprint']}ull, {len(picks)}, {{ {', '.join(map(str, picks + [0] * (5 - len(picks))))} }} }}, /* {n}: "
							 + ", ".join(PICK_NAMES[p] for p in picks) + f" ({e['rosters'][k]['origin']}) */")  # no // comment: it would swallow the \\ continuation
			open(os.path.join(d, "src", hdr, "mi_roster.h"), "w").write(
				f"// generated by tools/mapintel/battery.py: roster slot {k} of {a.rosters}\n#define MI_ROSTER_ENTRIES \\\n"
				+ " \\\n".join(lines) + "\n")
			build(v)
			var.append(v)
		def check(i, j):
			"""Every kept game of the pair: the engine's drafts (statistics 'roster') equal the forced rosters of both teams."""
			cell = os.path.join(keep, f"{var[i]}_vs_{var[j]}")
			nchk = 0
			for st in sorted(glob.glob(os.path.join(cell, "*_[AB].json"))):
				n, side = os.path.basename(st)[:-7], os.path.basename(st)[-6]
				d = json.load(open(st))
				for team, k in (("teamA", i if side == "A" else j), ("teamB", j if side == "A" else i)):
					want = sorted(bodynorm(BODY_NAMES[b]) for p in R["maps"][n]["rosters"][k]["picks"] for b in pick_bodies(p))
					got = sorted(bodynorm(c["name"]) for c in d["roster"]["champions"] if c["team"] == team)
					if want != got:
						die(f"roster check on {n} side {side}: {team} drafted {got}, the forced roster is {want}: bots/{a.bot} does not "
							"call mapintel::forced_pick() first in its draft turn (tools/mapintel/README.md)")
				nchk += 1
			if nchk == 0:
				die(f"roster check: no statistics kept for {var[i]} vs {var[j]}")
			return nchk

		for i in range(C):
			for j in range(i + 1, C):
				n, tot = ledger_run(var[i], var[j], maps_glob, a.jobs, stats_keep, env)
				nchk = check(i, j)
				meta["cells"].append({"battery": "roster", "bot": var[i], "opp": var[j], "slot_a": i, "slot_b": j, "games": n, "of": tot})
				if i == 0 and j == 1:
					print(f"3. roster check passed on {nchk} games: the engine's drafts equal the forced rosters", flush=True)
		print(f"3. roster battery done: {C * (C - 1) // 2} pairs ({time.time() - t0:.0f} s)")
		shutil.copy(os.path.join(ROOT, a.rosters), os.path.join(work, "rosters.json"))

	# 4. archive
	meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
	meta["seconds"] = round(time.time() - t0)
	json.dump(meta, open(os.path.join(work, "meta.json"), "w"), indent=1)
	# games.csv for draft_learn.py --battery (rosters from the kept statistics)
	if os.path.isdir(keep) and os.path.abspath(keep) == os.path.abspath(os.path.join(work, "keep")):
		r = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools/mapintel/battery_games.py"), work, "--out", os.path.join(work, "games.csv")],
						   capture_output=True, text=True)
		print("   " + (r.stdout.strip() or r.stderr.strip()[-300:]), flush=True)
	stamp = time.strftime("%Y%m%d_%H%M", time.gmtime())
	arc = os.path.join(a.out_dir, f"mapintel_battery_{a.bot}_{stamp}.tar.gz")
	nrep = 0
	with tarfile.open(arc, "w:gz") as tf:
		tf.add(os.path.join(work, "meta.json"), arcname="battery/meta.json")
		if os.path.exists(os.path.join(work, "rosters.json")):
			tf.add(os.path.join(work, "rosters.json"), arcname="battery/rosters.json")
		tf.add(os.path.join(work, "ledger"), arcname="battery/ledger")
		if os.path.exists(os.path.join(work, "games.csv")):
			tf.add(os.path.join(work, "games.csv"), arcname="battery/games.csv")
		if os.path.isdir(keep):
			for cell in sorted(os.listdir(keep)):
				for f in sorted(glob.glob(os.path.join(keep, cell, "*"))):
					base = os.path.basename(f)
					if base.endswith(".json"):
						tf.add(f, arcname=f"battery/keep/{cell}/{base}")
					elif base.endswith(".repl26a") and not a.no_replays:
						try:  # the run bundle holds the replay plus the bots' logs: archive the replay only
							with zipfile.ZipFile(f) as z:
								inner = next(x for x in z.namelist() if x.endswith("replay.repl26a"))
								data = z.read(inner)
						except (zipfile.BadZipFile, StopIteration):
							data = open(f, "rb").read()
						p = os.path.join(work, "_tmp.repl26a")
						open(p, "wb").write(data)
						tf.add(p, arcname=f"battery/keep/{cell}/{base}")
						nrep += 1
	if os.path.exists(os.path.join(work, "_tmp.repl26a")):
		os.remove(os.path.join(work, "_tmp.repl26a"))
	shutil.rmtree(init, ignore_errors=True)
	games = sum(c["games"] for c in meta["cells"])
	if games == 0:
		die("no games were played")
	print(f"4. ARCHIVE {arc}  {os.path.getsize(arc) / 1e6:.1f} MB  ({games} games, {nrep} replays, {meta['seconds']} s)")
	if a.split_mb and os.path.getsize(arc) / 1e6 > a.split_mb:
		from ladder_fetch import split_file
		parts = split_file(arc, a.split_mb)
		print(f"   too big for one upload: cut into {len(parts)} parts (upload all of them):")
		for p in parts:
			print(f"   {p}  {os.path.getsize(p) / 1e6:.1f} MB")
	else:
		print("Upload this one file in the chat.")


if __name__ == "__main__":
	main()
